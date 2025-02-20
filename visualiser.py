#!/usr/bin/env python3

"""
Class for visualisation of the software process.

Demonstrates prompt to image, image processing, inverse kinematics, and
robotic arm movement.
"""

import time
import numpy as np
import pygame
from ik import ik_visualiser

from image_processing import image_processing as im_proc
from prompt_processing import filter_prompt
from image_generation.dream_api_wrapper import generate_image
from image_generation.art_styles import ArtStyle


WIDTH, HEIGHT = 1000, 700
FPS = 3000
BG_COLOUR = pygame.Color("White")

BASE = 65
ARM1 = ARM2 = 250
PEN_OFFSET = 30


# pylint: disable=too-many-locals
def main() -> None:
    """Main function"""
    start_time = time.time()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Robotic Arm Visualizer")

    points_surface = pygame.Surface(screen.get_size())
    points_surface.fill(BG_COLOUR)

    clock = pygame.time.Clock()
    running = True

    prompt = filter_prompt(input("Enter prompt: "))
    print(f"{prompt=}")

    img = generate_image(prompt, ArtStyle.DREAMLAND_V3)
    img.show()
    opencv_image = np.array(img)

    # TODO: handle nsfw rejection
    # TODO: retry with higher detail if contour count less than min number

    print('Getting contours...')

    contours = im_proc.extract_contours(
        opencv_image,
        arm_max_length=ARM1 + ARM2,
    )

    print('Sorting contours')
    contours = im_proc.sort_contours(contours)

    print("Getting optimal dimensions")
    img_w, _ = im_proc.get_image_new_dimen(opencv_image, ARM1 + ARM2)

    print('Saving motor angles')
    im_proc.save_motor_angles(
        contours,
        BASE, ARM1, ARM2,
        offset=(0, -img_w, PEN_OFFSET + BASE),
        output_file="output.angles"
    )

    print("Drawing...")

    prev_point = ()
    screen.fill(BG_COLOUR)

    is_pen_down = False

    with open("output.angles", "r", encoding="utf-8") as f:
        for line in f.readlines():
            if not running:
                break

            line = line.strip()

            has_params = ":" in line
            cmd = line.split(":")[0] if has_params else line
            params = line.split(":")[1].split(",") if has_params else None

            angles = None
            match cmd:
                case "NO ANGLES":
                    continue
                case "ANGLES" if params:
                    angles = tuple(map(float, params))
                case "PEN UP":
                    is_pen_down = False
                case "PEN DOWN":
                    is_pen_down = True
                case _:
                    print(f"Unknown command: '{cmd}'. Skipping.")
                    continue

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

            # Validate angles
            if angles is None:
                continue
            if not isinstance(angles, tuple):
                continue
            if not all(isinstance(a, float) for a in angles):
                continue
            if len(angles) != 3:
                continue

            pen_point = ik_visualiser.draw_arms(
                angles, BASE, ARM1, ARM2, PEN_OFFSET, screen
            )

            # Draw straight line between points
            if prev_point and is_pen_down:
                pygame.draw.line(
                    points_surface,
                    (100, 100, 100),
                    prev_point,
                    pen_point if pen_point else (0, 0),
                    2
                )

            screen.blit(points_surface, (0, 0))
            prev_point = pen_point

            ik_visualiser.draw_arms(
                angles, BASE, ARM1, ARM2, PEN_OFFSET, screen
            )

            pygame.display.flip()
            clock.tick(FPS)

    end_time = time.time()
    print(f"Done. Took {end_time - start_time} seconds.")

    while running:
        screen.fill(BG_COLOUR)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        screen.blit(points_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
