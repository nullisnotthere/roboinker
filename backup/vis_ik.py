#!/usr/bin/env python3

import math
import pygame
from pygame import Vector2
import ik


def rotate_line(start, end, angle) -> tuple[Vector2, Vector2]:
    """Rotate a line around its start point by the given angle (in degrees)."""
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
def draw_arm(x, y, z,
             base: float, arm1: float, arm2: float, pen_offset: float,
             screen: pygame.Surface
             ) -> tuple[float, float, float, float] | None:
    """ Draw the arm to the screen given the desired point """
    screen.fill((0, 0, 0))  # Clear screen

    z += pen_offset
    angles = ik.get_angles(x, y, z, base, arm1, arm2)
    if not angles:
        print("no angles")
        return None

    _, ang_arm1, ang_arm2 = angles  # _ assigned to angle_base

    base_screen = Vector2(screen.get_width() // 2, screen.get_height() - base)

    # First arm
    a1_start = Vector2(base_screen)
    a1_end = Vector2(base_screen.x + arm1, base_screen.y)
    ang1 = -ang_arm1
    a1_start, a1_end = rotate_line(a1_start, a1_end, ang1)

    # Second arm
    a2_start = a1_end
    a2_end = Vector2(a1_end.x + arm2, a1_end.y)
    ang2 = -(ang_arm2 + ang_arm1) + 180
    a2_start, a2_end = rotate_line(a2_start, a2_end, ang2)

    # Pen
    pen_start = a2_end
    pen_end = Vector2(a2_end.x + pen_offset, a2_end.y)
    compensation = -(ang_arm1 + ang_arm2) - 90
    pen_ang = -(ang_arm1 + ang_arm2) - compensation
    pen_start, pen_end = rotate_line(pen_start, pen_end, pen_ang)

    pygame.draw.line(screen, pygame.Color('red'), a1_start, a1_end, 5)
    pygame.draw.line(screen, pygame.Color('blue'), a2_start, a2_end, 5)
    pygame.draw.line(screen, pygame.Color('yellow'), pen_start, pen_end, 5)

    return angles + (pen_ang,)


WIDTH, HEIGHT = 800, 600

BASE = 10
ARM1 = 200
ARM2 = 200
PEN_OFFSET = 30


def main() -> None:
    """Main"""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Robotic Arm Visualizer")
    clock = pygame.time.Clock()
    last_mouse = ()

    running = True

    while running:
        screen.fill(pygame.Color('Black'))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos == last_mouse:
            continue

        screen_x, screen_y = mouse_pos
        target_x, target_z = screen_x - WIDTH // 2, -screen_y + HEIGHT
        angles = draw_arm(target_x, 0, target_z,
                          BASE, ARM1, ARM2, PEN_OFFSET, screen)
        if not angles:
            continue

        print('\t'.join([f"{angle:.2f}" for angle in angles]))

        flipped = angles[0] == 180
        flipped_surface = pygame.transform.flip(screen, flipped, False)
        screen.blit(flipped_surface, (0, 0))

        last_mouse = mouse_pos

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
