"""
Simple visualiser for inverse kinematics mathematics.
Shows side and top views along with respective bounding arcs for arm maximum
extensions.
"""

import math
import pygame
from pygame import Vector2


def _rotate_line(start, end, angle) -> tuple[Vector2, Vector2]:
    # Transforms start and end coordinates according to angle of rotation

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


# pylint: disable=too-many-locals
def draw_arms(angles: tuple[float, float, float] | None,
              base: float,
              arm1: float,
              arm2: float,
              pen_offset: float,
              screen: pygame.Surface,
              only_return: bool = False) -> Vector2 | None:
    """Draw the arm to the screen given the desired point"""

    if not angles:
        print(f"NO ANGLES TO DRAW! {angles=}")
        return None

    ang_base, ang_arm1, ang_arm2 = angles[1], angles[2], angles[0]
    ang_base = 90 - ang_base

    base_screen = Vector2(screen.get_width() // 2, screen.get_height() - base)

    # First arm (side view)
    ang1 = -ang_arm1
    a1_start = Vector2(base_screen)
    a1_end = Vector2(base_screen.x + arm1, base_screen.y)
    a1_start, a1_end = _rotate_line(a1_start, a1_end, ang1)

    # First arm (top view)
    tv_a1_len = math.sqrt(arm1 ** 2 - Vector2(a1_end - a1_start).y ** 2)
    if ang_arm1 > 90:
        tv_a1_len *= -1
    tv_a1_start = Vector2(base_screen)
    tv_a1_end = Vector2(base_screen.x + tv_a1_len, base_screen.y)
    tv_a1_start, tv_a1_end = _rotate_line(tv_a1_start, tv_a1_end, -ang_base)

    # Second arm (side view)
    a2_start = a1_end
    a2_end = Vector2(a1_end.x + arm2, a1_end.y)
    ang2 = -(ang_arm2 + ang_arm1) + 180
    a2_start, a2_end = _rotate_line(a2_start, a2_end, ang2)

    # Second arm (top view)
    a2_tv_len = math.sqrt(arm2 ** 2 - Vector2(a2_end - a2_start).y ** 2)
    a2_tv_start = tv_a1_end
    a2_tv_end = Vector2(tv_a1_end.x + a2_tv_len, tv_a1_end.y)
    a2_tv_start, a2_tv_end = _rotate_line(a2_tv_start, a2_tv_end, -ang_base)

    if only_return:
        return a2_tv_end  # Return the pen tip's end position

    # Pen
    pen_start = a2_end
    pen_end = Vector2(a2_end.x + pen_offset, a2_end.y)
    compensation = -(ang_arm1 + ang_arm2) - 90
    ang_pen = -(ang_arm1 + ang_arm2) - compensation
    pen_start, pen_end = _rotate_line(pen_start, pen_end, ang_pen)

    # Draw side
    pygame.draw.line(screen, pygame.Color("darkred"), a1_start, a1_end, 5)
    pygame.draw.line(screen, pygame.Color("darkblue"), a2_start, a2_end, 5)
    pygame.draw.line(screen, pygame.Color("purple"), pen_start, pen_end, 5)

    sv_arc_center = Vector2(base_screen.x, base_screen.y + pen_offset)
    sv_arc_radius = arm1 + arm2
    pygame.draw.circle(
        screen, (230, 230, 230), sv_arc_center, sv_arc_radius, 5
    )

    # Draw top
    pygame.draw.line(screen, pygame.Color("red"), tv_a1_start, tv_a1_end, 8)
    pygame.draw.line(screen, pygame.Color("blue"), a2_tv_start, a2_tv_end, 5)
    pygame.draw.circle(screen, pygame.Color("magenta"), a2_tv_end, 7)

    tv_arc_radius = arm1 + arm2
    pygame.draw.circle(screen, (200, 200, 200), base_screen, tv_arc_radius, 5)

    # Draw ground line
    ground_y = screen.get_height() - base
    pygame.draw.line(
        screen,
        pygame.Color(20, 20, 20),
        (0, ground_y),                      # start
        (screen.get_width(), ground_y),     # end
        5
    )

    return a2_tv_end  # Return the pen tip's end position
