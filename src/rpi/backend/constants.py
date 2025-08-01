"""Backend constants used across the code."""

import os
import pathlib
from pygame import Vector2

# Directories
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ANGLES_FILE_PATH = os.path.join(THIS_DIR, "..", "..", "..", "data/output.motctl")

# Robotic arm configuration

# Dimension lengths (mm)
ARM_LEN_1 = 180
ARM_LEN_2 = 180
BASE_HEIGHT = 170
PEN_ARM_LEN = 120   # Horizontal pen offset
PEN_LEN = 100       # Vertical pen offset

BASE_SCREEN_OFFSET = Vector2(200, 350)

DRAG_ARM_HITBOX_SIZE = 100  # Hitbox size in px for dragging arm

# The value to change the detail level by when too high/low
DETAIL_LEVEL_ADAPT = 0.1
CONTOURS_COUNT_MAX = 50
CONTOURS_COUNT_MIN = 15
