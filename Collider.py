import pygame
import math
from Settings import WIDTH, HEIGHT
class Collider:
    def __init__(self, x: float, y: float, radius: float):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = radius

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
            self.pos -= direction * (overlap / 2)
            other.pos += direction * (overlap / 2)

    def keepInsideScreen(self):
        if self.pos.x - self.radius < 0:
            self.pos.x = self.radius
        if self.pos.x + self.radius > WIDTH:
            self.pos.x = WIDTH - self.radius
        if self.pos.y - self.radius < 0:
            self.pos.y = self.radius
        if self.pos.y + self.radius > HEIGHT:
            self.pos.y = HEIGHT - self.radius
