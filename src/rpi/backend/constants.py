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
PEN_ARM_LEN = 120       # Horizontal pen offset
PEN_LEN = 100           # Vertical pen offset
PEN_UP_DISTANCE = 50    # How high above paper when pen is up

# The value to change the detail level by when too high/low
DETAIL_LEVEL_ADAPT = 0.05
CONTOURS_COUNT_MAX = 50
CONTOURS_COUNT_MIN = 15
