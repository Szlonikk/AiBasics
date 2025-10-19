from Collider import Collider
from typing import List
from Settings import ZOMBIE_RADIUS, COLOR_ZOMBIE, COLOR_ZOMBIE_GROUPING
import pygame

class Zombies:

    def __init__(self,x: float, y:float, radius: float):
        self.collider=Collider(x,y,radius)

    def update(self, dt:float):
        print("Zombie update")

    def draw(self,surface: pygame.Surface):
        pygame.draw.circle(surface, COLOR_ZOMBIE, self.collider.pos, self.collider.radius)

    @staticmethod
    def generateZombies() -> List["Zombies"]:
        fixed_positions = [
            (50, 50),
            (200, 200)
        ]

        zombies: List[Zombies] = [
            Zombies(x, y, ZOMBIE_RADIUS) for (x, y) in fixed_positions
        ]
        return zombies