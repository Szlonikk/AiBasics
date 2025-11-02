from Obstacles import Obstacles
from Zombie import Zombie
from Player import Player 
import pygame
from Settings import COLOR_RAY

class ShooterManager:

    def __init__(self, obstacles: list[Obstacles], zombies: list, player: Player):
        self.objects = [*obstacles, *zombies]
        self.player = player
        self.draw_ray = False

    def update(self, dt: float):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.shoot()

    def draw(self, surface: pygame.Surface, length: float):
        print('guwno')
        pygame.draw.rect(surface, COLOR_RAY, pygame.Rect(self.player.collider.pos, (length, 5.0)))

    def shoot(self):
        self.draw_ray = True
        pygame.time.set_timer(pygame.USEREVENT, 3000)