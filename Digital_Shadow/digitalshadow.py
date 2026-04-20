# Imports
import pygame
from pygame import draw
import math


#Initialization of pygame
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Digital Shadow")

#colours
WHITE = (255,255,255)

#Simulation Objects
def robot(start_pos, radius=10, angle=0): # Angle 0 = straight right
    vector_y = math.sin(angle) * (radius + 2.5)
    vector_x = math.cos(angle) * (radius + 2.5)
    end_pos = (start_pos[0]+vector_x, start_pos[1]+vector_y)

    draw.circle(screen, WHITE, start_pos, radius, width=1)
    draw.line(screen, WHITE, start_pos, end_pos, width=1)
 


def main():
    run = True
    while run:

        screen.fill((0,0,0))

        # create rectangle example
        # draw.rect(screen, WHITE, (250, 150, 100, 100), width=1)

        # create line example
        # draw.line(screen, WHITE, start_pos=(250,200), end_pos=(350, 200), width=1)

        robot((300,200))


        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
        
        pygame.display.flip()

main()