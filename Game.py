import pygame
from Obstacles import Obstacles
WIDTH = 1024
HEIGHT = 1024
FPS = 60

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Zombie Survival")
        self.clock = pygame.time.Clock()
        self.running = True

        #World
        self.obstacles=Obstacles.generateObstacles
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.running = False    
            self.update(dt)
            self.draw()
        pygame.quit()
    
    # =============== TODO =============
    def update(self, dt: float):
        print(123) 

    # =============== TODO =============
    def draw(self):
        print(123)
