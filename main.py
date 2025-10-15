import objects
import pygame

# --- Settings ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# --- Initialize Pygame ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AiBasics")
clock = pygame.time.Clock()

# --- Main Game Loop ---
running = True
while running:
    screen.fill((20, 20, 30))  # Dark background

    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Draw Obstacles
    for polygon in objects.obstacles:
        pygame.draw.polygon(screen, (60, 180, 180), polygon)
        pygame.draw.polygon(screen, (255, 255, 255), polygon, 2)  # outline

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
