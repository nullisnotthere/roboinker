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

from src.rpi.backend.ik import ik_visualiser
from src.rpi.backend.prompt_processing import prompt_processing as prompt_proc
from src.rpi.backend.voice_processing.voice_processing import VoiceProcessor
from src.rpi.backend.image_processing import image_processing as img_proc
from src.rpi.backend.image_generation.dream_api_wrapper import generate_image, ImageResponse
from src.rpi.backend.image_generation.art_styles import ArtStyle


WIDTH, HEIGHT = 1000, 700
FPS = 3000
BG_COLOUR = pygame.Color("White")
DIR = os.path.dirname(os.path.abspath(__file__))
ANGLES_FILE = os.path.join(DIR, "..", "..", "data/output.angles")

BASE = 65
ARM1 = ARM2 = 250
PEN_OFFSET = 30

# The value to increase the detail level by when contour count is too low
DETAIL_LEVEL_INCREMENT = 0.1
CONTOURS_COUNT_UPPER = 50
CONTOURS_COUNT_LOWER = 15


def get_prompt_from_voice():
    """Get a text prompt from a voice command."""
    full_text = ""

    try:
        vp = VoiceProcessor()
        vp.start_listening()

        while True:
            result = vp.process_voice()
            print(result)

            text = result.get("text")
            if text:
                full_text += text + ". "

    except KeyboardInterrupt:
        print("\nDone")
    finally:
        vp.stop_listening()

    return full_text


def gen_image_and_save_angles():
    """Prompt user for input, get the image based on the prompt, process
    the image, and save the motor angles to the ouput angles file."""

    prompt_from_voice = get_prompt_from_voice()
    essence = prompt_proc.extract_essential_phrase(prompt_from_voice)
    prompt = prompt_proc.add_image_gen_params(essence)
    print(f"{prompt=}")

    img_response: ImageResponse = generate_image(prompt, ArtStyle.DREAMLAND_V3)
    print(
        f"Image generation "
        f"{"failed" if img_response.cv_image is None else "completed"}\n"
        f"Status: {img_response.status.name}\n"
        f"Message: {img_response.message}"
    )
    if img_response.cv_image is None:
        return

    img = img_response.cv_image
    cv2.imshow("Image from Dream AI", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print('Getting contours...')
    contours = ()
    detail_level = img_proc.get_image_detail_level(img, 1_000, 50_000)

    # Itervatively adapt the contour detail if the resulting contour
    # count is too high/too low
    while True:
        contours = img_proc.extract_contours(
            img,
            arm_max_length=ARM1 + ARM2,
            detail_level=detail_level
        )
        print(f"Contour count: {len(contours)}")

        new_detail_level = detail_level
        if len(contours) > CONTOURS_COUNT_UPPER:
            new_detail_level -= DETAIL_LEVEL_INCREMENT
        elif len(contours) < CONTOURS_COUNT_LOWER:
            new_detail_level += DETAIL_LEVEL_INCREMENT

        # If the countour count is within bounds or if the detail is at
        # an extremity, then do not recalculate contours
        if new_detail_level == detail_level or not 0 <= new_detail_level >= 1:
            break

        # Update to the new detail level and recalculate contours
        # in the next loop iteration
        detail_level = new_detail_level
        print(f"Number of countours is out of bounds: {len(contours)}.\n"
              f"Retrying with new detail level: {detail_level:.2f}")
        time.sleep(0.5)  # Short pause for debugging

    print('Sorting contours')
    contours = img_proc.sort_contours(contours)

    print("Getting optimal dimensions")
    img_w, _ = img_proc.get_image_new_dimen(img, ARM1 + ARM2)

    print('Saving motor angles')
    img_proc.save_motor_angles(
        contours,
        BASE, ARM1, ARM2,
        offset=(0, -img_w, PEN_OFFSET + BASE),
        output_file=ANGLES_FILE
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

    gen_image_and_save_angles()

    start_time = time.time()
    draw_from_file(screen, points_surface, ANGLES_FILE)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Done. Took {elapsed_time:.2f} seconds.")

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
