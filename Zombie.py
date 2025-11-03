
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple
import pygame
import random
from Collider import Collider
from Steering import (
    Vec2, seek, flee, separation, wander,
    obstacle_avoidance, wall_avoidance
)
from Settings import (
    ZOMBIE_RADIUS, ZOMBIE_MAX_SPEED, ZOMBIE_MAX_FORCE,
    ZOMBIE_WANDER_WEIGHT, ZOMBIE_SEPARATION_WEIGHT,
    ZOMBIE_OBS_AVOID_WEIGHT, ZOMBIE_WALL_AVOID_WEIGHT,
    ZOMBIE_HIDE_WEIGHT, ZOMBIE_SEEK_WEIGHT,
    ZOMBIE_GROUP_RADIUS, ZOMBIE_GROUP_MIN, ZOMBIE_GROUP_LOCK_TIME,
    COLOR_ZOMBIE_IDLE, COLOR_ZOMBIE_ATTACK, COLOR_ZOMBIE_GROUPING
)

class ZState(Enum):
    HIDE_WANDER = auto()
    ATTACK = auto()

@dataclass
class AttackGroup:
    id: int
    members: List["Zombie"]
    anchor_pos: Vec2  # where the group formed (for debug/locking)

class Zombie:
    _next_group_id = 1

    def __init__(self, x: float, y: float, radius: float):
        self.collider = Collider(x, y, radius)
        self.vel = Vec2(0, 0)
        self.state = ZState.HIDE_WANDER
        self._wander_target = Vec2(random.uniform(-1,1), random.uniform(-1,1))
        self._wander_target.scale_to_length(1.0)
        self._attack_group: Optional[AttackGroup] = None
        self._group_lock_timer = 0.0

    def color(self):
        if self.state == ZState.ATTACK:
            return COLOR_ZOMBIE_ATTACK
        # briefly tint to grouping color while forming
        if self._group_lock_timer > 0:
            return COLOR_ZOMBIE_GROUPING
        return COLOR_ZOMBIE_IDLE

    def _steer(self, desired: Vec2) -> Vec2:
        force = desired - self.vel
        if force.length_squared() > 0:
            force = force if force.length() <= ZOMBIE_MAX_FORCE else force.normalize() * ZOMBIE_MAX_FORCE
        return force

    def _apply_force(self, force: Vec2, dt: float):
        self.vel += force * dt
        if self.vel.length() > ZOMBIE_MAX_SPEED:
            self.vel.scale_to_length(ZOMBIE_MAX_SPEED)
        self.collider.pos += self.vel * dt
        # bounce/snap off walls
        hits = self.collider.keepInsideScreen()
        # reflect on hit axis (simple bounce)
        if any(hits):
            if hits[0] or hits[1]:
                self.vel.x *= -0.7
            if hits[2] or hits[3]:
                self.vel.y *= -0.7

    def _nearby_zombie_colliders(self, all_entities: List) -> List[Collider]:
        cols = []
        for e in all_entities:
            if isinstance(e, Zombie) and e is not self:
                cols.append(e.collider)
        return cols

    def _obstacle_colliders(self, all_entities: List) -> List[Collider]:
        cols = []
        for e in all_entities:
            if hasattr(e, "collider") and not isinstance(e, Zombie) and e is not self:
                if e.__class__.__name__ == "Obstacles":
                    cols.append(e.collider)
        return cols

    def _hide_from(self, player_pos: Vec2, obstacles: List[Collider]) -> Vec2:
        # pick the obstacle that gives best cover (most opposite to player and closest)
        best_spot = None
        best_score = 1e9
        desired = Vec2()
        for o in obstacles:
            away = (o.pos - player_pos)
            if away.length_squared() == 0:
                continue
            away = away.normalize()
            # spot just behind obstacle relative to player
            spot = o.pos + away * (o.radius + self.collider.radius + 10.0)
            # cost: distance to spot
            cost = self.collider.pos.distance_to(spot)
            if cost < best_score:
                best_score = cost
                best_spot = spot
        if best_spot is not None:
            desired = seek(self.collider.pos, best_spot, ZOMBIE_MAX_SPEED)
        return desired

    def _try_form_group(self, all_entities: List["Zombie"], player_pos=None):
        # dynamiczny próg zależny od odległości gracza
        if player_pos is None:
            return None

        dist = self.collider.pos.distance_to(player_pos)

        # mapujemy dystans -> wymagany rozmiar grupy
        # blisko = mała grupa; daleko = duża grupa
        # min=2, max=ZOMBIE_GROUP_MIN * 2 (np. 16)
        min_group = 2
        max_group = ZOMBIE_GROUP_MIN * 2  
        max_dist = 800.0  # przy >800 traktujemy jak max dystans

        t = min(dist / max_dist, 1.0)  # 0 blisko, 1 daleko

        required = int(min_group + (max_group - min_group) * t)
        required = max(min_group, min(required, max_group))

        # sprawdzamy sąsiadów w pobliżu
        nearby: List[Zombie] = []
        for e in all_entities:
            if isinstance(e, Zombie) and e is not self and e.state == ZState.HIDE_WANDER:
                if self.collider.pos.distance_to(e.collider.pos) <= ZOMBIE_GROUP_RADIUS:
                    nearby.append(e)

        # czy przekraczamy dynamiczny próg?
        if len(nearby) + 1 >= required:
            group = AttackGroup(Zombie._next_group_id, [self] + nearby, self.collider.pos.copy())
            Zombie._next_group_id += 1

            for m in group.members:
                m.state = ZState.ATTACK
                m._attack_group = group
                m._group_lock_timer = ZOMBIE_GROUP_LOCK_TIME
            return group

        return None


    def update(self, dt: float, playerCollider: Collider, allEntities: List):
        player_pos = playerCollider.pos

        # decay lock timer
        if self._group_lock_timer > 0:
            self._group_lock_timer = max(0.0, self._group_lock_timer - dt)

        obstacles = self._obstacle_colliders(allEntities)
        others = self._nearby_zombie_colliders(allEntities)

        force = Vec2()

        if self.state == ZState.HIDE_WANDER:
            # compose forces: hide, wander, separation, obstacle/wall avoid
            hide_force = self._hide_from(player_pos, obstacles) * ZOMBIE_HIDE_WEIGHT
            # wander
            forward = self.vel if self.vel.length_squared() > 0 else Vec2(1, 0)
            wander_target, self._wander_target = wander(forward, self._wander_target)
            wander_force = wander_target * ZOMBIE_WANDER_WEIGHT
            # separation
            sep_force = separation(self.collider, others) * ZOMBIE_SEPARATION_WEIGHT
            # avoids
            obs_force = obstacle_avoidance(self.collider, self.vel, obstacles) * ZOMBIE_OBS_AVOID_WEIGHT
            wall_force = wall_avoidance(self.collider, self.vel) * ZOMBIE_WALL_AVOID_WEIGHT

            force = hide_force + wander_force + sep_force + obs_force + wall_force
            force = self._steer(self.vel + force)

            # ↑ Skłonność do ryzyka — częstsze wyjścia zza przeszkód
            # Szansa zależna od prędkości i trochę od chaosu AI (losowość)
            peek_chance = 0.10 + (self.vel.length() / ZOMBIE_MAX_SPEED) * 0.05  # baza 3%, rośnie gdy zombie już się rusza

            if random.random() < peek_chance:
                # czasem zmniejszamy motywację do chowania
                    force -= hide_force * random.uniform(0.4, 0.8)

                # czasem wręcz ignorujemy hide — agresywna ciekawość
            if random.random() < 0.3:  # 30% z peeków
                    force += (wander_target * 1.2)  # mocniej naprzód

            # attempt forming group (but don't recruit while a different group nearby is attacking)
            self._try_form_group(allEntities, player_pos)   

        elif self.state == ZState.ATTACK:
            # Seek the player, but still avoid obstacles/walls
            seek_force = seek(self.collider.pos, player_pos, ZOMBIE_MAX_SPEED) * ZOMBIE_SEEK_WEIGHT
            obs_force = obstacle_avoidance(self.collider, self.vel, obstacles) * ZOMBIE_OBS_AVOID_WEIGHT
            wall_force = wall_avoidance(self.collider, self.vel) * ZOMBIE_WALL_AVOID_WEIGHT
            sep_force = separation(self.collider, others) * (ZOMBIE_SEPARATION_WEIGHT * 0.5)  # keep spacing a bit

            force = seek_force + obs_force + wall_force + sep_force
            force = self._steer(force)

            # IMPORTANT: prevent chain reaction — do not recruit new members after lock expires.
            # We simply never call _try_form_group() in ATTACK.
            # Moreover, while lock timer > 0 we ignore new nearby wanderers (no-op here).

        self._apply_force(force, dt)

    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.color(), self.collider.pos, int(self.collider.radius))