
import pygame
import math
from Collider import Collider
from Settings import (
    PLAYER_START_POS_X, PLAYER_START_POS_Y, PLAYER_RADIUS, PLAYER_SPEED,
    COLOR_PLAYER, COLOR_PLAYER_BEAM, PLAYER_BEAM_COOLDOWN, PLAYER_BEAM_THICKNESS,
    WIDTH, HEIGHT
)

class Player:
    def __init__(self):
        self.collider = Collider(PLAYER_START_POS_X, PLAYER_START_POS_Y, PLAYER_RADIUS)
        self.angle_deg = -90.0
        self._beam_timer = 0.0
        self.is_firing = False
        self.last_shot_segment = None  # (start, end) for this frame

    def update(self, dt: float):
        self.rotate_towards(pygame.mouse.get_pos())
        self.move(dt)
        self.is_firing = pygame.mouse.get_pressed()[0]
        self._beam_timer -= dt
        self.last_shot_segment = None
        if self.is_firing and self._beam_timer <= 0:
            self._beam_timer = PLAYER_BEAM_COOLDOWN
            self.last_shot_segment = self._compute_beam_segment()

    def rotate_towards(self, mouse_pos):
        dx = mouse_pos[0] - self.collider.pos.x
        dy = mouse_pos[1] - self.collider.pos.y
        self.angle_deg = math.degrees(math.atan2(dy, dx))

    def move(self, dt: float):
        keys = pygame.key.get_pressed()
        direction = pygame.math.Vector2(
            (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0),
            (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0),
        )
        if direction.length_squared() > 0:
            direction = direction.normalize()
        self.collider.pos += direction * PLAYER_SPEED * dt
        self.collider.keepInsideScreen()

    def _compute_beam_segment(self):
        # infinite range: extend to screen edge in look direction
        a = self.collider.pos.copy()
        ang = math.radians(self.angle_deg)
        dirv = pygame.math.Vector2(math.cos(ang), math.sin(ang))
        # Extend to far edge
        # pick a large multiplier, then clamp to screen bounds via parametric intersection
        far = a + dirv * max(WIDTH, HEIGHT) * 2.0
        return (a, far)

    def draw(self, surface: pygame.Surface):
        # Triangle indicating facing
        cx, cy = self.collider.pos
        r = self.collider.radius
        a = math.radians(self.angle_deg)
        dirv = pygame.math.Vector2(math.cos(a), math.sin(a))
        front = dirv * r
        left = dirv.rotate(140) * (r * 0.6)
        right = dirv.rotate(-140) * (r * 0.6)

        points = [
            (cx + front.x, cy + front.y),
            (cx + left.x, cy + left.y),
            (cx + right.x, cy + right.y),
        ]
        pygame.draw.polygon(surface, COLOR_PLAYER, points)

        # Draw beam if fired this frame
        if self.last_shot_segment:
            pygame.draw.line(surface, COLOR_PLAYER_BEAM,
                             self.last_shot_segment[0],
                             self.last_shot_segment[1],
                             PLAYER_BEAM_THICKNESS)