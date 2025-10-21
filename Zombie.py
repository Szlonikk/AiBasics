from Collider import Collider
from typing import List
from Settings import ZOMBIE_RADIUS, COLOR_ZOMBIE, COLOR_ZOMBIE_GROUPING
import pygame
 

class Zombie:

    def __init__(self,x: float, y:float, radius: float):
        self.collider=Collider(x,y,radius)
        self.detectedPlayerPosition = None
        

    def update(self, dt: float, playerCollider: Collider, allEntities: List):
        print("Zombie update")
        self.detectedPlayerPosition = playerCollider
        
        # Check for other zombies within 50 pixel radius
        nearbyZombies = []
        for entity in allEntities:
            if isinstance(entity, Zombie) and entity != self:
                distance = self.collider.pos.distance_to(entity.collider.pos)
                if distance <= 50:
                    nearbyZombies.append(entity)
        
        print(f"Found {len(nearbyZombies)} zombies within 50 pixels")
        print(f"Player's location: {self.detectedPlayerPosition.pos.x}, {self.detectedPlayerPosition.pos.y}")
        return nearbyZombies


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