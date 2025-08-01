from typing import Callable

import os
import pygame
import pygame_gui
import cv2
import time

from pygame import Rect, Surface
from pygame_gui import UIManager
from cv2.typing import MatLike
from src.rpi.frontend.pages.page import Page
from src.rpi.backend.image_generation.image_generator import generate_images
from src.rpi.backend.image_generation.bing_token_retriever import get_token
from src.rpi.backend.image_processing import image_processing as img_proc
from src.rpi.backend.constants import (DETAIL_LEVEL_ADAPT,
                                       CONTOURS_COUNT_MIN,
                                       CONTOURS_COUNT_MAX,
                                       ANGLES_FILE_PATH,
                                       ARM_LEN_1,
                                       ARM_LEN_2,
                                       BASE_HEIGHT,
                                       PEN_ARM_LEN,
                                       PEN_LEN,
                                       BASE_SCREEN_OFFSET,
                                       DRAG_ARM_HITBOX_SIZE)


# Ensure API key environment variables exist
BING_IMAGE_GEN_API_KEY = os.getenv("BING_IMAGE_GEN_API_KEY")
if BING_IMAGE_GEN_API_KEY is None:
    raise RuntimeError("Missing required environment variable: "
                       "BING_IMAGE_GEN_API_KEY")


class ImagePage(Page):
    """Page to display generated image options."""
    def __init__(
            self,
            surface: Surface,
            ui_manager: UIManager,
            get_prompt_callback: Callable):
        super().__init__(
            tab_title="Generated Images",
            tab_object_id="#images_tab",
            surface=surface,
            ui_manager=ui_manager
        )
        self._prompt = "Empty"  # Default prompt
        self._images: list[MatLike] = []
        self._image_surfaces: list[Surface] = []
        self._image_preview_index = 0

        # Callback to the voice page for getting the final prompt
        self._get_prompt_callback = get_prompt_callback

        # Initialise the Bing token
        self._token = get_token()

        self._generate_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((70, 600), (120, 50)),
            manager=ui_manager,
            text="Generate",
            container=self._main_frame,
            command=self._generate_images
        )
        self._gen_contours_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((410, 600), (120, 50)),
            manager=ui_manager,
            text="Make contours",
            container=self._main_frame,
            command=self._generate_contours
        )
        self._gen_contours_button.disable()

        self.test_image = pygame.image.load("images/panda.jpg") # TODO REMOVE
        self._image_preview = pygame_gui.elements.UIImage(
            relative_rect=Rect((50, 80), (500, 500)),
            image_surface=self.test_image,
            manager=ui_manager,
            container=self._main_frame,
        )
        self._previous_preview_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((250, 585), (50, 25)),
            manager=ui_manager,
            text="<",
            container=self._main_frame,
            command=self._previous_image_preview
        )
        self._next_preview_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((300, 585), (50, 25)),
            manager=ui_manager,
            text=">",
            container=self._main_frame,
            command=self._next_image_preview
        )
        self._file_text = pygame_gui.elements.UITextBox(
            relative_rect=Rect((50, 670), (500, 280)),
            manager=ui_manager,
            html_text="<i>MOTCTL output here</i>",
            container=self._main_frame,
        )

    def _generate_contours(self):
        # Check that the extraction was successful
        current_image = self._images[self._image_preview_index]

        # Iteratively extract and refine contours from the image
        contours = img_proc.extract_and_refine_contour_count(
            current_image,
            DETAIL_LEVEL_ADAPT,
            CONTOURS_COUNT_MIN,
            CONTOURS_COUNT_MAX,
            ARM_LEN_1 + ARM_LEN_2
        )

        # Sort the contours to reduce pen movement distances
        contours = img_proc.sort_contours(contours)

        # Calculate the image's optimal dimensions based on the arm's
        # maximum arc
        img_width, img_height = img_proc.calculate_image_new_dimen(
            current_image, ARM_LEN_1 + ARM_LEN_2
        )

        print(f"NEW IMAGE DIMENSIONS WxH: {img_width}x{img_height}mm")

        # Save the motor angles to a .motctl file
        img_proc.save_motor_angles(
            contours,
            BASE_HEIGHT, ARM_LEN_1, ARM_LEN_2,
            offset=(-320, -img_width // 2, PEN_LEN),  # xyz
            pen_up_offset=PEN_LEN,
            output_file=ANGLES_FILE_PATH
        )

        with open(ANGLES_FILE_PATH, "r", encoding="utf-8") as f:
            self._file_text.set_text(f.read())

    def _generate_images(self) -> None:
        # Generates image URLs from the final prompt and store in the
        # images list.
        self._prompt = self._get_prompt_callback()
        if self._token is None:
            print("Error: You need a valid token to generate images.")
            return

        imgs = generate_images(self._prompt, self._token)
        if not imgs:
            print("No images were generated.")
            return
        for img in imgs:
            if img is None:
                continue
            # Get a pygame surface for the image preview UI
            img_surface = pygame.surfarray.make_surface(
                cv2.cvtColor(img, cv2.COLOR_BGR2RGB).swapaxes(0, 1)
            )
            # Store the image and its pygame surface
            self._images.append(img)
            self._image_surfaces.append(img_surface)

        if self._images:
            # Set the preview to the first new image
            self._image_preview_index = len(self._image_surfaces) - len(imgs)
            self._update_image_preview()
            # Allow user to now generate the contours
            self._gen_contours_button.enable()

    def _next_image_preview(self):
        # Loop back to first image if on last image
        if self._image_preview_index >= len(self._image_surfaces) - 1:
            self._image_preview_index = -1

        # Goes to the next image in the surfaces
        self._image_preview_index += 1
        self._update_image_preview()

    def _previous_image_preview(self):
        # Loop back to last image if on first image
        if self._image_preview_index < 1:
            self._image_preview_index = len(self._image_surfaces)

        # Goes to the previous image in the surfaces
        self._image_preview_index -= 1
        self._update_image_preview()

    def _update_image_preview(self):
        # Update the preview
        if len(self._image_surfaces) > 0:
            self._image_preview.set_image(
                self._image_surfaces[self._image_preview_index]
            )

    def get_contours(self):
        """Returns the extracted contours from the selected generated image
        that is currently being previewed."""
        # TODO

    def update(self, time_delta: float):
        """Update called each frame."""
        # Check that images generate successfully
