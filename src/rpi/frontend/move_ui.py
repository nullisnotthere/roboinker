#!/usr/bin/env python3

"""
Move the robot arm visual representation and update the physical arm to
mirror the inputted motor angles.

Controls:
    Drag the pen tip for X/Z movement, arrow keys change the Y rotation.
    R to reset the position of the arm (vertical up)
    Space to send the data to the Arduino via serial connection.
"""

import sys
import pygame
from pygame import Vector2, Color
from src.rpi.frontend.arm_visualiser import rotate_line, draw_arm_side_view
from src.rpi.backend.ik.ik import get_angles
from src.rpi.backend.serial_com.arduino_serial import ArduinoSerial


# pylint: disable=too-many-branches
def main() -> None:
    """Main function."""

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("RoboInker control")

    move_enable = False
    default_angles: dict[str, float] = {"x": -180, "y": -180, "z": -90, "a": -180}
    angles = {}
    angles.update({"x": 0, "y": 0, "z": 0, "a": 0})

    # Initialise Arduino serial connection
    arduino_ser = ArduinoSerial("/dev/ttyUSB0", 9600)
    arduino_ser.send_ready()  # Ready Arduino and ensure synced response output

    while True:
        if move_enable:
            screen.fill((0, 0, 0))
            world_x, world_z = screen_to_world_coords(*pygame.mouse.get_pos())

            # Retrieve and validate angles
            try:
                # Angles XYZ assigned to ang base, ang arm1, ang arm2 (YZX)
                new_angles = get_angles(
                    world_x, 0, world_z, BASE_HEIGHT, ARM_LEN_1, ARM_LEN_2
                )
            except ZeroDivisionError:
                new_angles = None

            if new_angles:
                # Store new angles in correct xyz format
                angles.update(
                    {
                        "x": round(new_angles[2] + default_angles["x"], 2),
                        "y": round(new_angles[0] + default_angles["y"], 2),
                        "z": round(new_angles[1] + default_angles["z"], 2),
                        "a": round(new_angles[2] + new_angles[1] - 270, 2)  # x + z - 270
                    }
                )
                print(angles)

        last_mouse_rect = get_mouse_rect(
            draw_arm_side_view(screen, angles["z"], angles["x"], angles["a"]),
            DRAG_ARM_HITBOX_SIZE,
            screen,
        )

        # Pygame event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if last_mouse_rect.collidepoint(pygame.mouse.get_pos()):
                    move_enable = True
            elif event.type == pygame.MOUSEBUTTONUP:
                move_enable = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    angles["y"] -= 1
                elif event.key == pygame.K_RIGHT:
                    angles["y"] += 1
                elif event.key == pygame.K_r:
                    # Reset all to zero
                    angles.update({"x": 0, "y": 0, "z": 0, "a": 0})
                    screen.fill((0, 0, 0))
                elif event.key == pygame.K_RETURN:
                    ax = angles["x"]
                    ay = angles["y"]
                    az = angles["z"]
                    aa = angles["a"]

                    arduino_ser.update_axis_angle("x", ax)
                    arduino_ser.update_axis_angle("y", ay)
                    arduino_ser.update_axis_angle("z", -az)
                    arduino_ser.update_axis_angle("a", aa)
                    arduino_ser.send_angles()

                # E-stop
                elif event.key == pygame.K_SPACE:
                    arduino_ser.stop_all_motors()

        pygame.display.update()


if __name__ == "__main__":
    main()
