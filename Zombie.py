from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import math
from typing import List, Optional, Tuple
import pygame
import random
from Collider import Collider
from Player import Player
from Steering import (
    Vec2, seek, separation, wander,
    obstacle_avoidance, wall_avoidance, alignment, cohesion, pursuit, hide
)
from Settings import (
    ZOMBIE_RADIUS, ZOMBIE_MAX_SPEED, ZOMBIE_MAX_FORCE, ZOMBIE_THREAT_RADIUS,
    ZOMBIE_WANDER_WEIGHT, ZOMBIE_SEPARATION_WEIGHT,
    ZOMBIE_OBS_AVOID_WEIGHT, ZOMBIE_WALL_AVOID_WEIGHT,
    ZOMBIE_HIDE_WEIGHT, ZOMBIE_SEEK_WEIGHT,
    ZOMBIE_GROUP_RADIUS, ZOMBIE_GROUP_MIN, ZOMBIE_GROUP_LOCK_TIME,
    COLOR_ZOMBIE_IDLE, COLOR_ZOMBIE_ATTACK, COLOR_ZOMBIE_GROUPING
)

class ZState(Enum):
    WANDER = auto()
    PURSUE = auto()
    HIDE = auto()

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
        self.state = ZState.WANDER
        self._wander_target = Vec2(random.uniform(-1,1), random.uniform(-1,1))
        self._wander_target.scale_to_length(1.0)
        self._attack_group: Optional[AttackGroup] = None
        self._group_lock_timer = 0.0
        self.tagged = False
        self.separation_on = False
        self.alignment_on= False
        self.cohesion_on = False
        self.obstacle_avoidance_on = False
        self.wander_on = True
        self.pursue_on = False
        self.seek_on = False
        self.hide_on = False


    def color(self):
        if self.state == ZState.PURSUE:
            return COLOR_ZOMBIE_ATTACK
        if self._group_lock_timer > 0:
            return COLOR_ZOMBIE_GROUPING
        return COLOR_ZOMBIE_IDLE

    def tag(self):
        self.tagged = True
    
    def untag(self):
        self.tagged = False

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

    def _zombie_neighbours(self, all_entities: List) -> List[Zombie]:
        cols = []
        for e in all_entities:
            if isinstance(e, Zombie) and e is not self:
                cols.append(e)
        return cols

    def _obstacle_colliders(self, all_entities: List) -> List[Collider]:
        cols = []
        for e in all_entities:
            if hasattr(e, "collider") and not isinstance(e, Zombie) and e is not self:
                if e.__class__.__name__ == "Obstacles":
                    cols.append(e.collider)
        return cols

    def tag_neighbours(self, entities: List['Zombie'], radius: float):
        for entity in entities:
            entity.untag()
            to = entity.collider.pos - self.collider.pos
            range = radius + entity.collider.radius
            if entity is not self and to.length_squared() < range * range:
                entity.tag()
        
    def update(self, dt: float, player: Player, allEntities: List):
        player_pos = player.collider.pos

        neighbours = self._zombie_neighbours(allEntities)

        if self.separation_on or self.alignment_on or self.cohesion_on:
            self.tag_neighbours(neighbours, ZOMBIE_GROUP_RADIUS)

        obstacles = self._obstacle_colliders(allEntities)
        force = Vec2()
        speed = self.vel.length()
        
        if self.separation_on:
            separation_force = separation(self, neighbours)
            force += separation_force * ZOMBIE_SEPARATION_WEIGHT
        if self.alignment_on:
            alignment_force = alignment(self, neighbours)
            force += alignment_force
        if self.cohesion_on:
            cohsesion_force = cohesion(self, ZOMBIE_MAX_SPEED, neighbours)
            force += cohsesion_force
        if self.obstacle_avoidance_on:
            obs_force = obstacle_avoidance(self.collider, self.vel, speed, ZOMBIE_MAX_SPEED, obstacles)
            force += obs_force * ZOMBIE_OBS_AVOID_WEIGHT
        if self.wander_on:
            forward = self.vel if self.vel.length_squared() > 0 else Vec2(1, 0)
            wander_target, self._wander_target = wander(forward, self._wander_target)
            wander_force = wander_target * ZOMBIE_WANDER_WEIGHT
            force += wander_force
        if self.pursue_on:
            player_heading = Vec2(0,0)
            heading = Vec2(0,0)
            if player.vel.length() > 0.0:
                player_heading = player.vel.normalize()
            if self.vel.length() > 0.0:
                heading = self.vel.normalize()
            pursue_force = pursuit(self.collider.pos, heading, player_pos, player_heading, player.vel, player.vel.length(), ZOMBIE_MAX_SPEED, self.vel)
            force += pursue_force
        if self.seek_on:
            seek_force = seek(self.collider.pos, player_pos, ZOMBIE_MAX_SPEED, self.vel)
            force += seek_force
        if self.hide_on:
            force += hide(
                position = self.collider.pos,
                max_speed = ZOMBIE_MAX_SPEED,
                velocity = self.vel,
                target_pos = player_pos,     # the shooter / laser origin
                target_vel = Vec2(0, 0),     # player not moving fast enough to matter
                obstacles = obstacles
            )

        wall_force = wall_avoidance(self.collider, self.vel) * ZOMBIE_WALL_AVOID_WEIGHT
        force += wall_force

        self._apply_force(force, dt)


    def update_behavior(self, player: Player):
        # Distance to player
        dist_sq = (player.collider.pos - self.collider.pos).length_squared()

        # Beam direction
        beam_dir = Vec2(math.cos(player.angle_deg), math.sin(player.angle_deg)).normalize()

        # Behavior switching thresholds
        trigger_dist = 200       # zombie detects player
        lose_dist = 260          # zombie goes back to wandering

        # --- State Machine ---

        if self.state == ZState.WANDER:
            if dist_sq < trigger_dist * trigger_dist:
                self.become_pursuer()

        elif self.state == ZState.PURSUE:
            if self.laser_threatened(self.collider.pos, player.collider.pos, beam_dir, ZOMBIE_THREAT_RADIUS):
                self.become_hider()
            if dist_sq > lose_dist * lose_dist:
                self.become_wanderer()
 
        elif self.state == ZState.HIDE:
            if not self.laser_threatened(self.collider.pos, player.collider.pos, beam_dir, ZOMBIE_THREAT_RADIUS):
                self.become_pursuer()

    def become_pursuer(self):
        self.state = ZState.PURSUE

        # Turn OFF unrelated behaviors
        self.wander_on = False
        self.separation_on = False
        self.alignment_on = False
        self.cohesion_on = False
        self.hide_on = False

        # Turn ON pursuit
        self.pursue_on = True

        print("Zombie now pursuing!")

    def become_wanderer(self):
        self.state = ZState.WANDER

        # Turn OFF pursuit
        self.pursue_on = False

        # Turn ON wandering
        self.wander_on = True

        # Turn ON flocking
        self.separation_on = True
        self.alignment_on = True
        self.cohesion_on = True

        print("Zombie now wandering again.")

    def become_hider(self):
        self.state = ZState.HIDE

        # Turn OFF pursuit
        self.pursue_on = False
        
        # Turn ON separation
        self.separation_on = True

        # Turn ON hide
        self.hide_on = True


    def laser_threatened(self, zombie_pos: Vec2, beam_start: Vec2, beam_dir: Vec2, threat_radius: float) -> bool:
        to_zombie = zombie_pos - beam_start
        perpendicular = abs(to_zombie.cross(beam_dir))
        return perpendicular < threat_radius
    
    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.color(), self.collider.pos, int(self.collider.radius))
