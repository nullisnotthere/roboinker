#!/usr/bin/env python3

"""
Class for visualisation of the software process.

Demonstrates prompt to image, image processing, inverse kinematics, and
robotic arm movement.
"""

import os
import time
import pygame
import cv2
from ik import ik_visualiser

from image_processing import image_processing as im_proc
from image_generation.prompt_processing import filter_prompt
from image_generation.dream_api_wrapper import generate_image
from image_generation.art_styles import ArtStyle


WIDTH, HEIGHT = 1000, 700
FPS = 3000
BG_COLOUR = pygame.Color("White")
DIR = os.path.dirname(os.path.abspath(__file__))
ANGLES_FILE = os.path.join(DIR, "output.angles")

BASE = 65
ARM1 = ARM2 = 250
PEN_OFFSET = 30


def gen_image_and_save_angles():
    """Prompt user for input, get the image based on the prompt, process
    the image, and save the motor angles to the ouput angles file."""

    prompt = filter_prompt(input("Enter prompt: "))
    print(f"{prompt=}")

    img = generate_image(prompt, ArtStyle.DREAMLAND_V3)
    if img is not None:
        cv2.imshow("Image", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # TODO: handle nsfw rejection
    # TODO: retry with higher detail if contour count less than min number
    # TODO: handle `requests.exceptions.ReadTimeout: HTTPSConnectionPool(
    #       host='paint.api.wombo.ai', port=443): Read timed out.
    #       (read timeout=20)`

    print('Getting contours...')
    contours = im_proc.extract_contours(img, arm_max_length=ARM1 + ARM2)

    print('Sorting contours')
    contours = im_proc.sort_contours(contours)

    print("Getting optimal dimensions")
    img_w, _ = im_proc.get_image_new_dimen(img, ARM1 + ARM2)

    print('Saving motor angles')
    im_proc.save_motor_angles(
        contours,
        BASE, ARM1, ARM2,
        offset=(0, -img_w, PEN_OFFSET + BASE),
        output_file="output.angles"
    )


def draw_from_file(
        screen: pygame.Surface,
        points_surface: pygame.Surface,
        file_path: str):
    """Draws a visualisation of the robotic arm's movement and draw path
    based on the angles defined in the angles file."""

    print("Drawing...")
    clock = pygame.time.Clock()
    is_pen_down: bool = False
    drawing: bool = True
    prev_point = ()

    # Clear background
    screen.fill(BG_COLOUR)
    points_surface.fill(BG_COLOUR)

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f.readlines():
            if not drawing:
                break

            line = line.strip()
            has_params = ":" in line
            cmd = line.split(":")[0] if has_params else line
            params = line.split(":")[1].split(",") if has_params else None
            angles = None

            # Parse the output angles file
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

            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    drawing = False
                    break

            # Validate angles, must be tuple of 3 floats
            if angles is None:
                continue
            if not isinstance(angles, tuple):
                continue
            if not all(isinstance(a, float) for a in angles):
                continue
            if len(angles) != 3:
                continue

            # Store the pen tip position without drawing the arms
            pen_point = ik_visualiser.draw_arms(
                angles, BASE, ARM1, ARM2, PEN_OFFSET, screen, return_only=True
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

            # Draw the arm configuration (top and side view)
            ik_visualiser.draw_arms(
                angles, BASE, ARM1, ARM2, PEN_OFFSET, screen
            )

            pygame.display.flip()
            clock.tick(FPS)


def main() -> None:
    """Main function."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Robotic Arm Visualizer")

    points_surface = pygame.Surface(screen.get_size())
    running = True

    start_time = time.time()
    gen_image_and_save_angles()
    draw_from_file(screen, points_surface, ANGLES_FILE)
    end_time = time.time()

    print(f"Done. Took {end_time - start_time} seconds.")

    # Show image until user quits
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
