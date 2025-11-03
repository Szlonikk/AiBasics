
from typing import List
from Collider import Collider
import pygame
from Settings import COLOR_OBSTACLES, OBSTACLE_LIST

class Obstacles:
    def __init__(self, x: float, y: float, radius: float):
        self.collider = Collider(x, y, radius)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, COLOR_OBSTACLES, self.collider.pos, int(self.collider.radius))

    @staticmethod
    def generateObstacles() -> List["Obstacles"]:
        return [Obstacles(x, y, r) for (x, y, r) in OBSTACLE_LIST]