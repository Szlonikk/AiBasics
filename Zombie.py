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
    COLOR_ZOMBIE_IDLE, COLOR_ZOMBIE_ATTACK, COLOR_ZOMBIE_GROUPING,
    ZOMBIE_MAX_HIDE_DISTANCE
)


class ZState(Enum):
    WANDER = auto()
    PURSUE = auto()
    HIDE = auto()


@dataclass
class AttackGroup:
    id: int
    members: List["Zombie"]
    anchor_pos: Vec2  # miejsce utworzenia grupy (debug)


class Zombie:
    _next_group_id = 1
    _attack_groups: List[AttackGroup] = []   # wszystkie grupy ataku

    def __init__(self, x: float, y: float, radius: float):
        self.collider = Collider(x, y, radius)
        self.vel = Vec2(0, 0)
        self.state = ZState.WANDER

        self._wander_target = Vec2(random.uniform(-1, 1), random.uniform(-1, 1))
        self._wander_target.scale_to_length(1.0)

        self._attack_group: Optional[AttackGroup] = None
        self._group_lock_timer = 0.0

        self.tagged = False

        # przełączniki zachowań
        self.separation_on = False
        self.alignment_on = False
        self.cohesion_on = False
        self.obstacle_avoidance_on = False
        self.wander_on = True
        self.pursue_on = False
        self.seek_on = False
        self.hide_on = False

        self._state_timer = 0.0

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

        # odbijanie od krawędzi ekranu
        hits = self.collider.keepInsideScreen()
        if any(hits):
            if hits[0] or hits[1]:
                self.vel.x *= -0.7
            if hits[2] or hits[3]:
                self.vel.y *= -0.7

    def _zombie_neighbours(self, all_entities: List) -> List["Zombie"]:
        cols: List[Zombie] = []
        for e in all_entities:
            if isinstance(e, Zombie) and e is not self:
                cols.append(e)
        return cols

    def _obstacle_colliders(self, all_entities: List) -> List[Collider]:
        cols: List[Collider] = []
        for e in all_entities:
            if hasattr(e, "collider") and not isinstance(e, Zombie) and e is not self:
                if e.__class__.__name__ == "Obstacles":
                    cols.append(e.collider)
        return cols

    def tag_neighbours(self, entities: List['Zombie'], radius: float):
        for entity in entities:
            entity.untag()
            to = entity.collider.pos - self.collider.pos
            r = radius + entity.collider.radius
            if entity is not self and to.length_squared() < r * r:
                entity.tag()

    def update(self, dt: float, player: Player, allEntities: List):
        player_pos = player.collider.pos

        neighbours = self._zombie_neighbours(allEntities)

        if self.separation_on or self.alignment_on or self.cohesion_on:
            self.tag_neighbours(neighbours, ZOMBIE_GROUP_RADIUS)

        obstacles = self._obstacle_colliders(allEntities)
        force = Vec2()
        speed = self.vel.length()

        # --- FLOCKING / SEPARACJA ---
        if self.separation_on:
            separation_force = separation(self, neighbours)
            force += separation_force * ZOMBIE_SEPARATION_WEIGHT

        if self.alignment_on:
            alignment_force = alignment(self, neighbours)
            force += alignment_force

        if self.cohesion_on:
            cohesion_force = cohesion(self, ZOMBIE_MAX_SPEED, neighbours)
            force += cohesion_force

        # --- UNIKANIE PRZESZKÓD ---
        if self.obstacle_avoidance_on:
            obs_force = obstacle_avoidance(self.collider, self.vel, speed, ZOMBIE_MAX_SPEED, obstacles)
            # w pościgu mniej bohatersko unikają przeszkód
            obs_weight = ZOMBIE_OBS_AVOID_WEIGHT * (0.3 if self.state == ZState.PURSUE else 1.0)
            force += obs_force * obs_weight

        # --- WANDER ---
        if self.wander_on:
            forward = self.vel if self.vel.length_squared() > 0 else Vec2(1, 0)
            wander_target, self._wander_target = wander(forward, self._wander_target)
            wander_force = wander_target * ZOMBIE_WANDER_WEIGHT
            force += wander_force

        # --- POŚCIG ---
        if self.pursue_on:
            player_heading = Vec2(0, 0)
            heading = Vec2(0, 0)
            if player.vel.length() > 0.0:
                player_heading = player.vel.normalize()
            if self.vel.length() > 0.0:
                heading = self.vel.normalize()

            pursue_force = pursuit(
                self.collider.pos,
                heading,
                player_pos,
                player_heading,
                player.vel,
                player.vel.length(),
                ZOMBIE_MAX_SPEED,
                self.vel
            )
            force += pursue_force

        # --- SEEK (jeśli gdzieś używasz) ---
        if self.seek_on:
            seek_force = seek(self.collider.pos, player_pos, ZOMBIE_MAX_SPEED, self.vel)
            force += seek_force

        # --- HIDE: mocne tylko blisko gracza ---
        if self.hide_on:
            dist = (player_pos - self.collider.pos).length()
            # t = 1 przy graczu, 0 przy ZOMBIE_MAX_HIDE_DISTANCE i dalej
            t = max(0.0, min(1.0, (ZOMBIE_MAX_HIDE_DISTANCE - dist) / ZOMBIE_MAX_HIDE_DISTANCE))
            if t > 0.0:
                hide_force = hide(
                    position=self.collider.pos,
                    max_speed=ZOMBIE_MAX_SPEED,
                    velocity=self.vel,
                    target_pos=player_pos,
                    target_vel=Vec2(0, 0),
                    obstacles=obstacles
                )
                force += hide_force * (ZOMBIE_HIDE_WEIGHT * t)

        # --- LEKKI "MAGNES" NA GRACZA W WANDER ---
        if self.state == ZState.WANDER:
            center_seek = seek(self.collider.pos, player_pos, ZOMBIE_MAX_SPEED, self.vel)
            force += center_seek * 0.08   # jak za słabe/mocne, kręcisz tą wartością
# --- HIDE: aktywne ukrywanie ZA PRZESZKODĄ ---
        if self.state == ZState.HIDE:

            best_ob = None
            best_dist = 999999

            # znajdź przeszkodę w "linii wzroku"
            for ob in obstacles:
                to_ob = ob.pos - player_pos
                to_z  = self.collider.pos - player_pos

                # obiekt musi być mniej więcej pomiędzy graczem a zombie
                if to_ob.length() < to_z.length() + 50:
                    d = (ob.pos - self.collider.pos).length()
                    if d < best_dist:
                        best_dist = d
                        best_ob = ob

            if best_ob:
                # kierunek od przeszkody w stronę odwrotną do gracza
                away = (best_ob.pos - player_pos).normalize()

                # punkt ukrycia ZA przeszkodą
                hide_point = best_ob.pos + away * (best_ob.radius + 20)

                hide_force = seek(self.collider.pos, hide_point, ZOMBIE_MAX_SPEED, self.vel)
                force += hide_force * ZOMBIE_HIDE_WEIGHT

            else:
                # brak przeszkód → uciekaj od gracza
                flee_dir = (self.collider.pos - player_pos).normalize()
                flee_target = self.collider.pos + flee_dir * 100
                flee_force = seek(self.collider.pos, flee_target, ZOMBIE_MAX_SPEED, self.vel)
                force += flee_force * (ZOMBIE_HIDE_WEIGHT * 0.6)

        # --- UNIKANIE ŚCIAN: słabsze w pościgu ---
        wall_weight = ZOMBIE_WALL_AVOID_WEIGHT * (0.3 if self.state == ZState.PURSUE else 1.0)
        wall_force = wall_avoidance(self.collider, self.vel) * wall_weight
        force += wall_force

        # zastosuj siłę
        self._apply_force(force, dt)

        # zmniejszanie czasu "lock" grupy (np. do efektu koloru)
        if self._group_lock_timer > 0.0:
            self._group_lock_timer = max(0.0, self._group_lock_timer - dt)



    # ---------- LOGIKA GRUPOWANIA ----------

    def _nearby_free_zombies_for_group(self, allEntities: List) -> List["Zombie"]:
        """
        Zwraca zombie w zasięgu grupowania, które:
        - nie są nami,
        - nie należą jeszcze do żadnej grupy (_attack_group is None).
        """
        candidates: List[Zombie] = []
        r2 = ZOMBIE_GROUP_RADIUS * ZOMBIE_GROUP_RADIUS

        for e in allEntities:
            if not isinstance(e, Zombie):
                continue
            if e is self:
                continue
            if e._attack_group is not None:
                # już w jakiejś grupie – nie dołączamy
                continue

            if (e.collider.pos - self.collider.pos).length_squared() <= r2:
                candidates.append(e)

        return candidates

    def _required_group_size(self, player: Player) -> int:
        """
        Im bliżej gracza, tym mniejsza wymagana grupa.
        Im dalej od gracza, tym większa wymagana grupa.
        """
        dist = (player.collider.pos - self.collider.pos).length()

        # dystanse progowe – możesz sobie potem dostroić
        close_dist = 80.0     # bardzo blisko gracza
        far_dist = 500.0      # dość daleko od gracza

        min_size = ZOMBIE_GROUP_MIN                # minimalna grupa przy gracz-u
        max_size = max(ZOMBIE_GROUP_MIN, ZOMBIE_GROUP_MIN * 3)  # maksymalna grupa daleko

        if dist <= close_dist:
            return min_size
        if dist >= far_dist:
            return max_size

        # interpolacja liniowa między min_size a max_size
        t = (dist - close_dist) / (far_dist - close_dist)  # 0..1
        size_f = min_size + t * (max_size - min_size)
        size_i = int(round(size_f))

        return max(min_size, min(max_size, size_i))

    def _try_form_attack_group(self, player: Player, allEntities: List):
        """
        Próbuje utworzyć nową grupę ataku, jeśli:
        - ten zombie nie ma jeszcze grupy,
        - w pobliżu jest wystarczająco dużo innych wolnych zombie (dynamicznie liczone).
        Po utworzeniu grupy:
        - skład jest zamrożony (nie dodajemy nowych),
        - wszystkie zombie z grupy przechodzą do stanu PURSUE.
        """
        if self._attack_group is not None:
            return False # już w grupie

        neighbours = self._nearby_free_zombies_for_group(allEntities)

        required_size = self._required_group_size(player)

        # czy mamy wystarczającą liczbę zombie do grupy?
        if len(neighbours) + 1 < required_size:
            return False

        # członkowie grupy: my + sąsiedzi (bierzemy tylko tyle, ile trzeba)
        members: List[Zombie] = [self] + neighbours[: required_size - 1]

        # anchor_pos = środek masy grupy (bardziej debug/estetyka)
        avg_pos = Vec2(0, 0)
        for z in members:
            avg_pos += z.collider.pos
        if len(members) > 0:
            avg_pos.x /= len(members)
            avg_pos.y /= len(members)

        group = AttackGroup(
            id=Zombie._next_group_id,
            members=members,
            anchor_pos=avg_pos
        )
        Zombie._next_group_id += 1
        Zombie._attack_groups.append(group)

        # przypisz grupę każdemu zombie i włącz atak
        for z in members:
            z._attack_group = group
            z._group_lock_timer = ZOMBIE_GROUP_LOCK_TIME
            z.become_pursuer()   # od razu przechodzą do ataku
        return True

    # ---------- ZMIENIONA MASZYNA STANÓW ----------

    def update_behavior(self, player: Player, allEntities: List, dt):
        # odległość do gracza
        dist_sq = (player.collider.pos - self.collider.pos).length_squared()

        # kierunek "lasera" – zostawiamy na przyszłość
        beam_dir = Vec2(math.cos(player.angle_deg), math.sin(player.angle_deg)).normalize()

        # dystans, przy którym zombie w ogóle zaczynają myśleć o ataku / grupie
        trigger_dist = 200

        # 1. Jeśli już ścigamy, NIE zmieniamy stanu nigdy
        if self.state == ZState.PURSUE:
            return

        # 2. Jeśli mamy grupę, ale z jakiegoś powodu nie jesteśmy jeszcze w PURSUE,
        #    to wymuś atak (skład grupy jest już zamrożony)
        if self._attack_group is not None and self.state != ZState.PURSUE:
            self.become_pursuer()
            return

        # 3. Zombie, które nie są w grupie, nie mogą atakować solo.
        #    Mogą tylko wałęsać się (WANDER) / ewentualnie korzystać z flockingu.

        # Gracz musi być w zasięgu "wykrycia", żeby w ogóle próbować tworzyć grupę
        if dist_sq < trigger_dist * trigger_dist:
            # Spróbuj utworzyć grupę (wymagana liczebność zależy od dystansu do gracza)
            did_form_group = self._try_form_attack_group(player, allEntities)

            # Jezeli nie udało się utworzyć grupy, sprawdź czy liczba zombie na mapie
            # jest mniejsza niż ZOMBIE_GROUP_MIN * 3, jeśli tak to nie twórz grupy i
            # przejdź do stanu PURSUE
            if not did_form_group:
                zombie_count = sum(1 for ent in allEntities if isinstance(ent, Zombie))
                if zombie_count < ZOMBIE_GROUP_MIN * 3:
                    self.become_pursuer()

        # Jeśli grupa się nie utworzyła – zostajemy w dotychczasowym stanie
        # (najczęściej WANDER + flocking)
        self._state_timer += dt  # zakładam że dt masz w player; jeśli nie, podaj dt
        if self._state_timer >= 3.0:
            self._state_timer = 0.0
            if self.state == ZState.WANDER:
                self.become_hider()
            elif self.state == ZState.HIDE:
                self.become_wanderer()

    # ---------- STANY POMOCNICZE ----------

    def become_pursuer(self):
        self.state = ZState.PURSUE

        # Wyłącz inne zachowania
        self.wander_on = False
        self.separation_on = False
        self.alignment_on = False
        self.cohesion_on = False
        self.hide_on = False

        # Włącz pościg
        self.pursue_on = True

        print(f"Zombie {id(self)} now pursuing (group: {self._attack_group.id if self._attack_group else 'solo'})!")

    def become_wanderer(self):
        # UWAGA: w obecnej logice nie wywołujemy tego po wejściu w PURSUE,
        # ale zostawiamy funkcję na przyszłość.
        self.state = ZState.WANDER

        # Wyłącz pościg
        self.pursue_on = False

        # Włącz włóczęgę
        self.wander_on = True

        # Włącz flocking
        self.separation_on = False
        self.alignment_on = False
        self.cohesion_on = False

        print("Zombie now wandering again.")

    def become_hider(self):
        # w tej wersji logiki nie korzystamy z HIDE, ale zostawiamy na przyszłość
        self.state = ZState.HIDE

        # Wyłącz pościg
        self.pursue_on = False

        # Włącz separation
        self.separation_on = True

        # Włącz chowanie
        self.hide_on = True
        self.separation_on = False
        self.alignment_on = False
        self.cohesion_on = False
        print('HIDER')

    def laser_threatened(self, zombie_pos: Vec2, beam_start: Vec2, beam_dir: Vec2, threat_radius: float) -> bool:
        to_zombie = zombie_pos - beam_start
        perpendicular = abs(to_zombie.cross(beam_dir))
        return perpendicular < threat_radius

    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.color(), self.collider.pos, int(self.collider.radius))
