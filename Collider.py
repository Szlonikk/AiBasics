
import pygame
from Settings import WIDTH, HEIGHT

class Collider:
    def __init__(self, x: float, y: float, radius: float):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = float(radius)

    def move(self, offset: pygame.math.Vector2):
        self.pos += offset

    def overlaps(self, other: "Collider") -> bool:
        return self.pos.distance_to(other.pos) < self.radius + other.radius

    def resolveOverlap(self, other, static=False):
        delta = other.pos - self.pos
        dist = delta.length()
        if dist == 0:
            delta = pygame.math.Vector2(0.001, 0)
            dist = 0.001
        overlap = self.radius + other.radius - dist
        direction = delta.normalize()
        if static:
            self.pos -= direction * overlap
        else:
            self.pos -= direction * (overlap * 0.5)
            other.pos += direction * (overlap * 0.5)

    def keepInsideScreen(self):
        hit_left = hit_right = hit_top = hit_bottom = False
        if self.pos.x - self.radius < 0:
            self.pos.x = self.radius
            hit_left = True
        if self.pos.x + self.radius > WIDTH:
            self.pos.x = WIDTH - self.radius
            hit_right = True
        if self.pos.y - self.radius < 0:
            self.pos.y = self.radius
            hit_top = True
        if self.pos.y + self.radius > HEIGHT:
            self.pos.y = HEIGHT - self.radius
            hit_bottom = True
        return hit_left, hit_right, hit_top, hit_bottom