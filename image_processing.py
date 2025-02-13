"""
Handles image processing.
Method to threshold and filter image contours from AI-generated image.
"""


import math
from typing import Sequence
import numpy as np
import cv2
from PIL import Image


def _max_rect_from_semi(
        width: float,
        height: float,
        radius: float) -> tuple[float, float]:
    # Calculates the new width and height required to fit a semicircle of
    # given radius while maintaining aspect ratio.

    w = radius / math.sqrt((height / width) ** 2 + (1 / 4))
    h = math.sqrt(radius ** 2 - (w ** 2) / 4)
    return w, h


def get_contours(
        img: Image.Image,
        arm_max_length: float,
        up_is_positive: bool = False) -> Sequence[np.ndarray]:
    """Returns contours from a given image."""

    opencv_image = np.array(img)
    opencv_image = cv2.rotate(opencv_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    opencv_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)

    img_h, img_w = opencv_image.shape[:2]  # Height first, then width
    w, h = tuple(
        map(int, _max_rect_from_semi(img_w, img_h, arm_max_length))
    )
    opencv_image = cv2.resize(opencv_image, (w, h))

    edges = cv2.Canny(opencv_image, 50, 150, L2gradient=True)  # Edge detection

    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Handle int vs float accordingly
    if isinstance(w, int):
        off_x, off_y = -w // 2, h if up_is_positive else -h
    else:
        off_x, off_y = -w / 2, h if up_is_positive else -h
    contours = [cnt + np.array([off_x, off_y]) for cnt in contours]

    return contours
