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
import ai4free
from dotenv import load_dotenv

from src.rpi.backend.ik import ik_visualiser
from src.rpi.backend.prompt_processing import prompt_processing as prompt_proc
from src.rpi.backend.voice_processing import voice_processing as voice_proc
from src.rpi.backend.image_processing import image_processing as img_proc
from src.rpi.backend.image_generation.bing_image_gen import BingImageCreator
from src.rpi.backend.image_generation.bing_token_retriever import get_token
from src.rpi.backend.image_generation.image_extractor import extract_image

load_dotenv()

# Ensure API key environment variables exist
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY is None:
    raise RuntimeError("Missing required environment variable: GROQ_API_KEY")

BING_IMAGE_GEN_API_KEY = os.getenv("BING_IMAGE_GEN_API_KEY")
if BING_IMAGE_GEN_API_KEY is None:
    raise RuntimeError("Missing required environment variable: "
                       "BING_IMAGE_GEN_API_KEY")

# Window settings
WIDTH, HEIGHT = 1000, 700
BG_COLOUR = pygame.Color("White")
FPS = 3000

# Directories
DIR = os.path.dirname(os.path.abspath(__file__))
ANGLES_FILE_PATH = os.path.join(DIR, "..", "..", "data/output.motctl")

# Robotic arm configuration

# The value to change the detail level by when too high/low
DETAIL_LEVEL_ADAPT = 0.1
CONTOURS_COUNT_MAX = 50
CONTOURS_COUNT_MIN = 15


def draw_from_file(
        screen: pygame.Surface,
        points_surface: pygame.Surface,
        file_path: str) ->  None:
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

            # Parse line
            line = line.strip()
            has_params = line[-1] != "$"
            cmd = line.split("$")[0]
            params = line.split("$")[1].split(",") if has_params else None
            pairs = dict(p.split(":") for p in (params if params else []))
            angles = None

            # Parse each command accordingly
            match cmd:
                case "NO ANGLES":
                    continue
                case "SET ANGLES" if params:
                    angles = tuple(map(float, pairs.values()))
                case "SET SPEEDS" if params:
                    speeds = tuple(map(float, params.values()))
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
                angles, BASE, ARM1, ARM2, PEN_OFFSET, screen, only_return=True
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


def get_prompt_from_voice(vp: voice_proc.VoiceProcessor) -> str:
    """Get text from a voice prompt via the microphone."""
    full_text = ""

    try:
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


def main() -> None:
    """Main function."""
    # Init PyGame window
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Robotic Arm Visualizer")
    points_surface = pygame.Surface(screen.get_size())
    running = True

    ######################
    # GENERATION PROCESS #
    ######################

    # Create an instance of the voice processor
    voice_processor = voice_proc.VoiceProcessor()

    # Get the prompt from voice input
    prompt_from_voice = get_prompt_from_voice(voice_processor)

    # Create an instance of the prompt AI
    prompt_ai = ai4free.GROQ(
        api_key=GROQ_API_KEY,  # pyright: ignore
        model="meta-llama/llama-4-scout-17b-16e-instruct"
    )

    # Extract the essence of the voice prompt
    essence = prompt_proc.extract_essential_phrase(
        ai=prompt_ai,
        prompt=prompt_from_voice
    )

    # Add the image generation parameters to the prompt essence
    prompt = prompt_proc.add_image_gen_params(essence)

    # Initialise the image generator (Bing)
    token = get_token()
    print(token)
    image_generator = BingImageCreator(cookies=[token])

    # Generate image URLs from the final prompt
    images = image_generator.generate_images_sync(
        prompt=prompt,
        model="dall-e-3"
    )

    # Check that images generate successfully
    if not images:
        print("Failed to generate images. Token may be expired, refreshing.")
        return

    # Extract the final images from the URLs
    img = extract_image(images[0])

    # Check that the extraction was successful
    if img is None:
        print("Failed to extract image.")
        return

    # Iteratively extract and refine contours from the image
    contours = img_proc.extract_and_refine_contour_count(
        img,
        DETAIL_LEVEL_ADAPT,
        CONTOURS_COUNT_MIN,
        CONTOURS_COUNT_MAX,
        ARM1 + ARM2
    )

    # Sort the contours to reduce pen movement distances
    contours = img_proc.sort_contours(contours)

    # Calculate the image's optimal dimensions based on the arm's maximum arc
    img_w, _ = img_proc.calculate_image_new_dimen(img, ARM1 + ARM2)

    # Save the motor angles to a .motctl file
    img_proc.save_motor_angles(
        contours,
        BASE, ARM1, ARM2,
        offset=(0, -img_w, PEN_OFFSET + BASE),
        pen_up_offset=PEN_UP_OFFSET,
        output_file=ANGLES_FILE_PATH
    )

    # Show the image
    cv2.imshow("Image from AI", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Read, interpret, and draw the saved motor angles to visualise the image
    draw_from_file(screen, points_surface, ANGLES_FILE_PATH)

    # Show visualiser until the user quits
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
