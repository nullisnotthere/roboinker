"""
Module to handle visualisation of the arm configuration.
"""

import math
import pygame
from pygame import Vector2, Surface, Color, Font

# Colours
GREY = "#565958"
RED = "#ea0c04"
GREEN = "#33bf2b"
BLUE = "#4da0f9"
YELLOW = "#f9f50c"
ORANGE = "#f7a013"
WHITE = "#ffffff"
TEXT_COLOUR = "#666666"

ZERO_ANGLES: dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0, "a": 0.0}


def rotate_line(start, end, angle) -> tuple[Vector2, Vector2]:
    """Transforms start and end coordinates according to angle of rotation."""

    angle_rad = math.radians(angle)
    x1, y1 = start
    x2, y2 = end

    # Convert end to relative coordinates
    rel_x, rel_y = x2 - x1, y2 - y1

    # Rotate using 2D rotation matrix
    new_x = rel_x * math.cos(angle_rad) - rel_y * math.sin(angle_rad)
    new_y = rel_x * math.sin(angle_rad) + rel_y * math.cos(angle_rad)

    # Convert back to absolute coordinates
    return Vector2(x1, y1), Vector2(x1 + new_x, y1 + new_y)


# flake8: noqa
# pylint: disable=too-many-locals,too-many-positional-arguments,too-many-arguments
def draw_arm_side_view(screen: Surface,
                       arm1_len: int,
                       arm2_len: int,
                       base_height: int,
                       pen_arm_len: int,
                       pen_len: int,
                       az: float,
                       ax: float,
                       aa: float,
                       screen_width: int,
                       screen_height: int,
                       base_screen_offset: Vector2,
                       font: Font):
    """Draw visual representation of the arm configuration's side view.
    Returns the Vector2 coordinates of the pen tip."""

    # Base line
    base_start = Vector2(
        screen_width // 2 + base_screen_offset.x,
        screen_height - base_screen_offset.y
    )
    base_end = Vector2(base_start.x, base_start.y - base_height)
    pygame.draw.line(screen, GREEN, base_start, base_end, 10)
    pygame.draw.circle(screen, GREEN, base_end, 10)

    base_height_label = font.render(f"{base_height}mm", True, TEXT_COLOUR)
    screen.blit(base_height_label, (base_start + base_end) / 2 + (20, 0))

    # Ground plane line
    ground_start = Vector2(0, base_start.y)
    ground_end = Vector2(screen_width, base_start.y)
    pygame.draw.line(
        screen, GREY, ground_start, ground_end, 3
    )

    # Paper area line
    paper_start = Vector2(base_start.x - 190, base_start.y)
    paper_end = Vector2(paper_start.x - 210, base_start.y)

    pygame.draw.line(
        screen, WHITE, paper_start, paper_end, 5
    )

    # First arm
    arm1_start = base_end
    arm1_end = Vector2(base_end.x, base_end.y - arm1_len)
    arm1_start, arm1_end = rotate_line(arm1_start, arm1_end, az)
    pygame.draw.line(screen, BLUE, arm1_start, arm1_end, 8)
    pygame.draw.circle(screen, BLUE, arm1_end, 10)

    arm1_len_label = font.render(f"{arm1_len}mm", True, TEXT_COLOUR)
    screen.blit(arm1_len_label, (arm1_start + arm1_end) / 2 + (20, -20))

    # Second arm
    arm2_start = arm1_end
    arm2_end = Vector2(arm1_end.x, arm1_end.y - arm2_len)
    arm2_start, arm2_end = rotate_line(arm2_start, arm2_end, az + ax)
    pygame.draw.line(screen, RED, arm2_start, arm2_end, 6)
    pygame.draw.circle(screen, RED, arm2_end, 10)

    arm2_len_label = font.render(f"{arm2_len}mm", True, TEXT_COLOUR)
    screen.blit(arm2_len_label, (arm2_start + arm2_end) / 2 + (17, 0))

    # Pen arm (horizontal)
    pen_arm_start = arm2_end
    pen_angle = az + ax - aa + 270  # Magic pen angle compensation value
    pen_arm_end = Vector2(arm2_end.x, arm2_end.y - pen_arm_len)
    pen_arm_start, pen_arm_end = rotate_line(
        pen_arm_start, pen_arm_end, pen_angle
    )
    pygame.draw.line(
        screen, YELLOW, pen_arm_start, pen_arm_end, 6
    )
    pygame.draw.circle(
        screen, YELLOW, pen_arm_end, 10
    )

    pen_arm_len_label = font.render(f"{pen_arm_len}mm", True, TEXT_COLOUR)
    screen.blit(pen_arm_len_label, (pen_arm_start + pen_arm_end) / 2 - (40, 30))

    # Pen (vertical)
    pen_start = pen_arm_end
    pen_end = Vector2(pen_arm_end.x, pen_arm_end.y - pen_len + 20)
    pen_start, pen_end = rotate_line(pen_start, pen_end, pen_angle - 90)
    pygame.draw.line(screen, ORANGE, pen_start, pen_end, 6)
    pygame.draw.polygon(
        screen,
        ORANGE,
        [
            (pen_end.x - 5, pen_end.y),
            (pen_end.x + 5, pen_end.y),
            (pen_end.x, pen_end.y + 20),
        ]
    )

    pen_len_label = font.render(f"{pen_len}mm", True, TEXT_COLOUR)
    screen.blit(pen_len_label, (pen_start + pen_end) / 2 + (20, 0))

    return Vector2(pen_end.x, pen_end.y + 20)


