import pygame
from Collider import Collider
import math
from Settings import PLAYER_START_POS_X, PLAYER_START_POS_Y, PLAYER_RADIUS, PLAYER_SPEED, COLOR_PLAYER

class Player:
    def __init__(self):
        self.collider=Collider(PLAYER_START_POS_X, PLAYER_START_POS_Y, PLAYER_RADIUS)
        self.angle = -90
    
    def update(self, dt: float):
        self.rotatePlayer(pygame.mouse.get_pos())
        self.move(dt)
        
    def rotatePlayer(self, mousePos):
        dx = mousePos[0] - self.collider.pos[0]
        dy = mousePos[1] - self.collider.pos[1]
        self.angle = math.degrees(math.atan2(dy, dx))

    
    def move(self, dt: float):
        keys = pygame.key.get_pressed()
        direction = pygame.math.Vector2(0, 0)
        if keys[pygame.K_w]:
            direction.y -= 1
        if keys[pygame.K_s]:
            direction.y += 1
        if keys[pygame.K_a]:
            direction.x -= 1
        if keys[pygame.K_d]:
            direction.x += 1
        if direction.length_squared() > 0:
            direction = direction.normalize()
        self.collider.pos += direction * PLAYER_SPEED * dt


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

        pygame.draw.polygon(surface, COLOR_PLAYER, points)