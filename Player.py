import pygame
from Collider import Collider
import math
START_POS_X=50
START_POS_Y=900
PLAYER_RADIUS=30

class Player:
    def __init__(self):
        self.collider=Collider(START_POS_X, START_POS_Y, PLAYER_RADIUS)
        self.angle = -90
    
    def update(self, dt: float):
        self.rotatePlayer(pygame.mouse.get_pos())
        
        
    def rotatePlayer(self, mousePos):
        dx = mousePos[0] - self.collider.pos[0]
        dy = mousePos[1] - self.collider.pos[1]
        self.angle = math.degrees(math.atan2(dy, dx))

    def draw(self, surface: pygame.Surface):
        cx, cy = self.collider.pos
        r = self.collider.radius
        a = math.radians(self.angle)
        direction = pygame.math.Vector2(math.cos(a), math.sin(a))
        front = direction * r
        left = direction.rotate(140) * (r * 0.6)
        right = direction.rotate(-140) * (r * 0.6)

        points = [
            (cx + front.x, cy + front.y),
            (cx + left.x, cy + left.y),
            (cx + right.x, cy + right.y),
        ]

        pygame.draw.polygon(surface, (50, 50, 200), points)