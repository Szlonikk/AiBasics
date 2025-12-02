import pygame
import random
from Obstacles import Obstacles
from Player import Player
from Settings import (
    WIDTH, HEIGHT, FPS,
    ZOMBIE_RADIUS, ZOMBIE_COUNT, COLOR_BG
)
from Zombie import Zombie

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Zombie Steering – hide/wander/attack")
        self.clock = pygame.time.Clock()
        self.running = True

        # World
        self.obstacles = Obstacles.generateObstacles()
        self.player = Player()
        self.zombies = self._spawn_zombies(ZOMBIE_COUNT)

        self.gameObjects = [*self.obstacles, self.player, *self.zombies]

        self.player_hp = 300

    def _spawn_zombies(self, count: int):
        zombies = []
        tries = 0
        while len(zombies) < count and tries < count * 80:
            tries += 1
            x = random.randint(60, WIDTH - 60)
            y = random.randint(60, HEIGHT - 60)
            c = Zombie(x, y, ZOMBIE_RADIUS)
            ok = True
            for o in self.obstacles:
                if c.collider.overlaps(o.collider):
                    ok = False
                    break
            if ok and c.collider.pos.distance_to(self.player.collider.pos) < 140:
                ok = False
            if ok:
                zombies.append(c)
        if len(zombies) < count:
            print(f"Spawned only {len(zombies)} zombies after {tries} tries.")
        return zombies

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.running = False
            self.update(dt)
            self.draw()
        pygame.quit()

    def update(self, dt: float):
        for obj in self.gameObjects:
            if hasattr(obj, "update"):
                if isinstance(obj, Zombie):
                    obj.update_behavior(self.player, self.gameObjects, dt)
                    obj.update(dt, self.player, self.gameObjects)
                else:
                    obj.update(dt)

        if self.player.last_shot_segment:
            a, b = self.player.last_shot_segment
            hit_dist = float('inf')
            hit_obj = None
            hit_point = None

            # check zombies
            for z in self.zombies:
                p = ray_circle_hit_point(a, b, z.collider.pos, z.collider.radius)
                if p is not None:
                    d = a.distance_to(p)
                    if d < hit_dist:
                        hit_dist = d
                        hit_obj = z
                        hit_point = p

            # check obstacles
            for o in self.obstacles:
                p = ray_circle_hit_point(a, b, o.collider.pos, o.collider.radius)
                if p is not None:
                    d = a.distance_to(p)
                    if d < hit_dist:
                        hit_dist = d
                        hit_obj = o
                        hit_point = p

            if hit_obj:
                # shorten beam exactly to hit edge
                self.player.last_shot_segment = (a, hit_point)

                # kill zombie if hit
                if isinstance(hit_obj, Zombie):
                    self.zombies.remove(hit_obj)
                    self.gameObjects.remove(hit_obj)

        # Resolve interpenetrations (basic)
        self.resolveAllCollisions(self.gameObjects)

        # Melee damage: zombie touching player
        for z in list(self.zombies):
            if z.collider.overlaps(self.player.collider):
                self.player_hp -= 1
                self.zombies.remove(z)
                self.gameObjects.remove(z)
                if self.player_hp <= 0:
                    print("Player down! (hp <= 0)")
                    self.running = False
                    break

    def draw(self):
        self.screen.fill(COLOR_BG)
        for obj in self.gameObjects:
            if hasattr(obj, "draw"):
                obj.draw(self.screen)

        # UI
        self._draw_ui()

        pygame.display.flip()

    def _draw_ui(self):
        font = pygame.font.SysFont(None, 22)
        text = font.render(
            f"HP: {self.player_hp}   Zombies: {len(self.zombies)}   LMB: beam",
            True,
            (230, 230, 230)
        )
        self.screen.blit(text, (10, 10))

    def resolveAllCollisions(self, gameObjects):
        # Obstacles are static circles; everything else has circle colliders too.
        for i in range(len(gameObjects)):
            for j in range(i + 1, len(gameObjects)):
                if not hasattr(gameObjects[i], "collider") or not hasattr(gameObjects[j], "collider"):
                    continue
                c1 = gameObjects[i].collider
                c2 = gameObjects[j].collider
                if c1.overlaps(c2):
                    # Obstacles resolve as static
                    if gameObjects[i].__class__.__name__ == "Obstacles":
                        c2.resolveOverlap(c1, static=True)
                    elif gameObjects[j].__class__.__name__ == "Obstacles":
                        c1.resolveOverlap(c2, static=True)
                    else:
                        c1.resolveOverlap(c2, static=False)

def ray_circle_hit_point(ray_start, ray_end, circle_center, radius):
    # Ray parametric form: P = A + t*(B-A)
    # Solve intersection with circle
    d = ray_end - ray_start
    f = ray_start - circle_center

    a = d.dot(d)
    b = 2 * f.dot(d)
    c = f.dot(f) - radius*radius

    disc = b*b - 4*a*c
    if disc < 0:
        return None  # no hit

    disc = disc**0.5
    t1 = (-b - disc) / (2*a)
    t2 = (-b + disc) / (2*a)

    # We want the first hit along the ray in [0,1]
    ts = []
    if 0 <= t1 <= 1:
        ts.append(t1)
    if 0 <= t2 <= 1:
        ts.append(t2)

    if not ts:
        return None

    t = min(ts)
    return ray_start + d * t