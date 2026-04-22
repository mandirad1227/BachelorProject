import pygame
import sys
import math

pygame.init()

WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("L-shaped Conveyor Belts")

clock = pygame.time.Clock()

# OKI DEnne flytter mer til midten bruk denne for å få den i i midten. 
belt_vertical = pygame.Rect(300, 140, 60, 260)
belt_horizontal = pygame.Rect(300, 340, 320, 60)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 0, 0))  # endre til kanskje litt mer lysere svart hør med sander?

    # Conveyor belts
    pygame.draw.rect(screen, (80, 80, 80), belt_vertical)
    pygame.draw.rect(screen, (80, 80, 80), belt_horizontal)

    # Kantlinjer
    pygame.draw.rect(screen, (160, 160, 160), belt_vertical, 3)
    pygame.draw.rect(screen, (160, 160, 160), belt_horizontal, 3)

    # Stripene mine vertikalt
    for y in range(belt_vertical.top + 15, belt_vertical.bottom, 25):
        pygame.draw.line(
            screen,
            (200, 200, 200),
            (belt_vertical.left + 5, y),
            (belt_vertical.right - 5, y),
            3
        )

    # Stripene mine horisontalt
    for x in range(belt_horizontal.left + 15, belt_horizontal.right, 25):
        pygame.draw.line(
            screen,
            (200, 200, 200),
            (x, belt_horizontal.top + 5),
            (x, belt_horizontal.bottom - 5),
            3
        )

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()


#  python3 main.py   
#  cd ~/Desktop/pygame_test
# kilder legg til kilder her youtube, reddit og alt.
