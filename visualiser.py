#!/usr/bin/env python3

import math
import random
import numpy as np
import cv2
import pygame
from ik import ik_visualiser
import ai.dream as img_gen
from ai.art_styles import ArtStyle


WIDTH, HEIGHT = 1000, 700
FPS = 300
BG_COLOUR = pygame.Color("White")

BASE = 65
ARM1 = ARM2 = 250
PEN_OFFSET = 30


# pylint: disable=too-many-locals
def main() -> None:
    """Main function"""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Robotic Arm Visualizer")

    points_surface = pygame.Surface(screen.get_size())
    points_surface.fill(BG_COLOUR)

    clock = pygame.time.Clock()
    running = True

    # FLow
    prompt = input("Enter prompt: ")
    prompt = img_gen.get_prompt(prompt)
    print(f"{prompt=}")
    img = img_gen.generate_image(prompt, ArtStyle.COMIC_V3)
    img.show()

    if img is None:
        raise RuntimeError("Failed to retreive image.")

    contours = img_gen.get_contours(img, arm_max_length=ARM1 + ARM2)

    '''
    white_bg = np.ones_like(img) * 255
    cv2.drawContours(white_bg, contours, -1, (0, 0, 0), 1)
    cv2.imshow("Contours only", white_bg)

    while True:
        key = cv2.waitKey(0)
        if key == ord('q'):
            cv2.destroyAllWindows()
            break
    '''

    print("Drawing...")
    prev_point = ()

    # Events
    for contour in contours:
        cnt_colour = tuple(random.randint(0, 100) for _ in range(3))
        for point_index, point in enumerate(contour):
            if not running:
                break

            screen.fill(BG_COLOUR)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

            if not isinstance(point, np.ndarray):
                raise ValueError("Point must be of type np.ndarray.")

            # DRAW POINT
            screen_x, screen_y = point[0] + (WIDTH // 2, HEIGHT - BASE)
            target_x, target_y = -screen_y + HEIGHT, screen_x - WIDTH // 2

            if prev_point and point_index > 0:
                pygame.draw.line(
                    points_surface,
                    cnt_colour,
                    (prev_point),
                    (screen_x, screen_y),
                    1
                )

            screen.blit(points_surface, (0, 0))
            prev_point = (screen_x, screen_y)

            angles = ik_visualiser.draw_arms(
                target_x, target_y, 0,  # x, y, z
                BASE, ARM1, ARM2, PEN_OFFSET,
                screen
            )
            if angles is None:
                pass

            pygame.display.flip()
            # clock.tick(FPS)

    print("DONE!")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()


if __name__ == "__main__":
    main()
