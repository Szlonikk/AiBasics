import math

class Collider:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def overlaps(self, other):
        dist = math.hypot(self.x - other.x, self.y - other.y)
        return dist < self.radius + other.radius

    def resolveOverlap(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 0.001
        overlap = self.radius + other.radius - dist
        nx, ny = dx / dist, dy / dist
        self.x -= nx * overlap / 2
        self.y -= ny * overlap / 2
        other.x += nx * overlap / 2
        other.y += ny * overlap / 2

