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
    
    def _update(self, dt: float, mouse_pos):
        dx = mouse_pos[0] - self.collider.pos[0]
        dy = mouse_pos[1] - self.collider.pos[1]
        self.angle = math.degrees(math.atan2(dy, dx))

    def update(self, dt: float):
        self._update(dt,pygame.mouse.get_pos())


    
    def draw(self, surface: pygame.Surface):
        # obliczamy wierzchołki trójkąta opisanego na okręgu collidera
        cx, cy = self.collider.pos
        r = self.collider.radius

        a = math.radians(self.angle)
        points = []
        for i in range(3):
            angle_i = a + i * (2 * math.pi / 3)
            x = cx + math.cos(angle_i) * r
            y = cy + math.sin(angle_i) * r
            points.append((x, y))
        pygame.draw.polygon(surface, (50, 50, 200), points)
