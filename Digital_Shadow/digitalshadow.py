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
class Robot:
    def __init__(self, start_pos, radius=10):
        self.start_pos = start_pos
        self.radius = radius
        self.angle = 0
        

    def draw_robot(self, angle=0): # Angle 0 = straight up, Rotates clockwise
        self.angle = angle
        angle += 270 # To compensate that makes 0 be up
        angle_rad = angle * (math.pi / 180) # Converts the degrees to radians

        vector_y = math.sin(angle_rad) * (self.radius + 2.5)
        vector_x = math.cos(angle_rad) * (self.radius + 2.5)
        end_pos = (self.start_pos[0]+vector_x, self.start_pos[1]+vector_y)

        draw.circle(screen, WHITE, self.start_pos, self.radius, width=1)
        draw.line(screen, WHITE, self.start_pos, end_pos, width=1)
 
    def get_robot_facing(): #WIP
        # Fill with logic to get current facing of robot
        return

def main():
    run = True

    # Initializing objects
    robot1 = Robot((300,200)) # Initializing Robot object

    while run:

        screen.fill((0,0,0))

        # create rectangle example
        # draw.rect(screen, WHITE, (250, 150, 100, 100), width=1)

        # create line example
        # draw.line(screen, WHITE, start_pos=(250,200), end_pos=(350, 200), width=1)

        
        robot1.draw_robot(angle=0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
        
        pygame.display.flip()

main()