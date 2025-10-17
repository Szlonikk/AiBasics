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
        self.obstacles = Obstacles.generateObstacles()
        self.gameObjects = self.obstacles  # add here rest of the objects
    
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
    
    def update(self, dt: float):
        for obj in self.gameObjects:
            if hasattr(obj, "update"):
                obj.update(dt)
        self.resolveAllCollisions(self.gameObjects)
 

    def draw(self):
        self.screen.fill((20, 20, 20))
        for obj in self.gameObjects:
            if hasattr(obj, "draw"):
                obj.draw(self.screen)
        pygame.display.flip()


    def resolveAllCollisions(self, gameObjects):
        for i in range(len(gameObjects)):
            for j in range(i + 1, len(gameObjects)):
                c1 = gameObjects[i].collider
                c2 = gameObjects[j].collider
                if c1.overlaps(c2):
                    c1.resolve_overlap(c2)