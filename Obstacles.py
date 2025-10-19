from typing import List
from Collider import Collider
import pygame
from Settings import COLOR_OBSTACLES
class Obstacles:

    def __init__(self, x: float, y: float, radius: float):
        self.collider = Collider(x, y, radius)

    def update(self, dt: float):
        print("update obstacle:", dt)

    def draw(self,surface: pygame.Surface):
        pygame.draw.circle(surface, COLOR_OBSTACLES, self.collider.pos, self.collider.radius)


    @staticmethod
    def generateObstacles() -> List["Obstacles"]:
        fixed_positions = [
            (150, 150, 70),
            (400, 200, 50),
            (650, 300, 50),
            (300, 450, 60),
            (550, 500, 85),
            (1000,800, 200),
            (400,700, 150),
            (800,100,100)
        ]

        obstacles: List[Obstacles] = [
            Obstacles(x, y, radius) for (x, y, radius) in fixed_positions
        ]
        return obstacles

