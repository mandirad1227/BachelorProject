# Imports
import pygame
from pygame import draw
import sys
import math

pygame.init()

WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("L-shaped Conveyor Belts")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)

# Sander sin del
#colours
WHITE = (255,255,255)

# OKI DEnne flytter mer til midten bruk denne for å få den i i midten. 
belt_vertical = pygame.Rect(300, 140, 60, 260)
belt_horizontal = pygame.Rect(300, 340, 320, 60)

sensor = pygame.Rect(280, 310, 20, 30) 

# velg hvor dem skal være søppelkasse
bin_top = pygame.Rect(625, 370, 35, 28)  
bin_bottom = pygame.Rect(260, 370, 35, 28)  

animation_offset = 0  # animasjon 1


# Sander sin del
def robot(start_pos: int, radius=10):
    draw.circle(screen, WHITE, start_pos, radius, width=1)
 


def draw_trash_bin(rect, lid_color):  # ny funksjon prøv den
    pygame.draw.rect(screen, (120, 120, 120), rect) 
    pygame.draw.rect(screen, (255, 255, 255), rect, 2)  

    lid = pygame.Rect(rect.left - 3, rect.top - 5, rect.width + 6, 5)  
    pygame.draw.rect(screen, (150, 150, 150), lid)  # ENDRET - grått lokk
    pygame.draw.rect(screen, (255, 255, 255), lid, 2)  #

    pygame.draw.rect(screen, lid_color, (rect.left + 4, rect.top + 5, rect.width - 8, 6))  
    pygame.draw.line(screen, (80, 80, 80), (rect.left + 10, rect.top + 12), (rect.left + 10, rect.bottom - 4), 2)  
    pygame.draw.line(screen, (80, 80, 80), (rect.right - 10, rect.top + 12), (rect.right - 10, rect.bottom - 4), 2)  


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    animation_offset += 1  # animasjon 2
    if animation_offset >= 25:  # animasjon 3
        animation_offset = 0  # animasjon 4

    screen.fill((0, 0, 0))  # endre til kanskje litt mer lysere svart hør med sander?

    # Conveyor belts
    pygame.draw.rect(screen, (80, 80, 80), belt_vertical)
    pygame.draw.rect(screen, (80, 80, 80), belt_horizontal)

     # sensor
    pygame.draw.rect(screen, (255, 255, 0), sensor)
    pygame.draw.rect(screen, (255, 255, 255), sensor, 2)

    # bins
    draw_trash_bin(bin_top, (255, 60, 60))  
    draw_trash_bin(bin_bottom, (0, 100, 255))  

    # Sander sin del
    robot((430, 250))

    # Kantlinjer
    pygame.draw.rect(screen, (160, 160, 160), belt_vertical, 3)
    pygame.draw.rect(screen, (160, 160, 160), belt_horizontal, 3)

    # Stripene mine vertikalt
    for y in range(belt_vertical.top + 15 + animation_offset - 25, belt_horizontal.top - 5, 25):  # animasjon 5
        pygame.draw.line(
            screen,
            (200, 200, 200),
            (belt_vertical.left + 5, y),
            (belt_vertical.right - 5, y),
            3
        )

    # Stripene mine horisontalt
    for x in range(belt_horizontal.left + 15 + animation_offset - 25, belt_horizontal.right, 25):  # animasjon 6
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