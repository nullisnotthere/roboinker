"""
Contains various integer values stored as an enum corresponding to the
Dream AI's image generation art styles.
"""

from enum import Enum


class ArtStyle(Enum):
    """Enum for all available dream.ai art styles."""
    DREAMLAND_V3 = 115
    COMIC = 45
    COMIC_V3 = 127
    LOGO_V3 = 132
    FLAT_V3 = 150
    ROBOTS_V3 = 145
    CARTOON_V3 = 159
    SIMPLE_DESIGN_V2 = 110
