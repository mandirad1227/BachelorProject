# Imports
import pygame
from pygame import draw

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Digital Shadow")

#colours
WHITE = (255,255,255)

def robot(start_pos: int, radius=10):
    draw.circle(screen, WHITE, start_pos, radius, width=1)



def main():
    run = True
    while run:

        screen.fill((0,0,0))

        # create rectangle example
        # draw.rect(screen, WHITE, (250, 150, 100, 100), width=1)

        # create line example
        # draw.line(screen, WHITE, (250,200), (350, 200), width=1)

        robot((300,200))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
        
        pygame.display.flip()

main()