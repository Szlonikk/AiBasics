
import pygame
import random
from Obstacles import Obstacles
from Player import Player
from Settings import (
    WIDTH, HEIGHT, FPS,
    ZOMBIE_RADIUS, ZOMBIE_COUNT, COLOR_BG
)
from Zombie import Zombie
from Steering import line_intersects_circle

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

        self.player_hp = 3

    def _spawn_zombies(self, count: int):
        zombies = []
        tries = 0
        while len(zombies) < count and tries < count * 50:
            tries += 1
            x = random.randint(60, WIDTH - 60)
            y = random.randint(60, HEIGHT - 60)
            c = Zombie(x, y, ZOMBIE_RADIUS)
            # avoid spawning overlapping obstacles or player
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
        # Update dynamic entities
        for obj in self.gameObjects:
            if hasattr(obj, "update"):
                if isinstance(obj, Zombie):
                    obj.update(dt, self.player.collider, self.gameObjects)
                else:
                    obj.update(dt)

        # Player beam hit detection (if a shot happened this frame)
        if self.player.last_shot_segment:
            a, b = self.player.last_shot_segment
            alive = []
            for z in self.zombies:
                if line_intersects_circle(a, b, z.collider.pos, z.collider.radius):
                    # instant kill
                    continue
                alive.append(z)
            if len(alive) != len(self.zombies):
                # refresh object list after removals
                self.zombies = alive
                self.gameObjects = [*self.obstacles, self.player, *self.zombies]

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
        text = font.render(f"HP: {self.player_hp}   Zombies: {len(self.zombies)}   LMB: beam", True, (230,230,230))
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

        # keep inside bounds
        for obj in gameObjects:
            if hasattr(obj, "collider") and obj.__class__.__name__ != "Obstacles":
                obj.collider.keepInsideScreen()