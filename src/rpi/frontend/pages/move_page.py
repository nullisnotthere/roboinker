import math
import time
from functools import partial
import re

from typing import Mapping, Generator

import pygame
import pygame_gui

from pygame import Rect, Surface, Vector2, Color, Event, Font
from pygame_gui import UIManager
from pygame_gui.elements import UILabel, UITextEntryLine  # For typing

from src.rpi.frontend.pages.page import Page
from src.rpi.frontend.constants import WIN_WIDTH, WIN_HEIGHT
from src.rpi.frontend.arm_visualiser import (rotate_line, draw_arm_side_view,
                                             ZERO_ANGLES,
                                             WHITE, RED, GREEN, BLUE, YELLOW,
                                             ORANGE)

from src.rpi.backend.ik.ik import (
    get_real_angles,
    get_nearest_valid_point,
    steps_to_deg
)
from src.rpi.backend.serial_com.arduino_serial import ArduinoSerial
from src.rpi.backend.constants import (
    ARM_LEN_1,
    ARM_LEN_2,
    BASE_HEIGHT,
    PEN_ARM_LEN,
    PEN_LEN,
    BASE_SCREEN_OFFSET,
    DRAG_ARM_HITBOX_SIZE,
    ANGLES_FILE_PATH
)


class MovePage(Page):
    """Page for moving the arm manually."""
    def __init__(self, surface: Surface, ui_manager: UIManager, font: Font,
                 arduino_ser: ArduinoSerial):
        super().__init__(
            tab_title="Move Arm",
            tab_object_id="#move_tab",
            surface=surface,
            ui_manager=ui_manager
        )
        self._font = font

        self._arm_drag_enable = False       # Dragging the arm GUI?
        self._drag_arm_hitbox = None        # Hitbox for arm GUI tip
        self._y_angle_drag_enable = False   # Dragging the Y rotator GUI?
        self._y_angle_hitbox = None         # Hitbox for Y rotator tip

        self._is_moving = False

        self._motor_angles: dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0}
        self._chunks_gen: Generator[str] | None = None
        self._preview_started = False

        self._arduino_ser = arduino_ser
        self._arduino_ser.send_data(
            "ASK READY",
            {"READY": lambda: print("We're ready!")}
        )

        # Initialise the UI elements
        self._top_frame = pygame_gui.elements.UIPanel(
            relative_rect=Rect((0, 0), (600, 650)),
            starting_height=450,
            manager=ui_manager,
            container=self._main_frame
        )
        self._bottom_frame = pygame_gui.elements.UIPanel(
            relative_rect=Rect((0, 650), (600, 330)),
            manager=ui_manager,
            starting_height=500,
            container=self._main_frame
        )
        self._stop_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((10, 10), (90, 50)),
            manager=ui_manager,
            text="STOP",
            container=self._top_frame,
            command=self._stop
        )
        self._position_labels: dict[str, UILabel] = {
            key: pygame_gui.elements.UILabel(
                relative_rect=Rect((10, 55 + 20 * i), (150, 50)),
                manager=ui_manager,
                text=f"Position {key}: 0",
                container=self._top_frame,
                anchors={"left": "left"}
            ) for i, key in enumerate("xyz")
        }

        # Angle labels and entries
        self._angle_elements: dict[str, dict[
            str, UILabel | UITextEntryLine]] = {
            key: {
                "label": pygame_gui.elements.UILabel(
                    relative_rect=Rect((-40, 50 + 30 * i), (200, 26)),
                    manager=ui_manager,
                    text=f"{key} angle:",
                    container=self._bottom_frame
                ),
                "entry": pygame_gui.elements.UITextEntryLine(
                    relative_rect=Rect((100, 50 + 30 * i), (200, 26)),
                    manager=ui_manager,
                    container=self._bottom_frame
                )
            } for i, key in enumerate("xyza")
        }
        self._view_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((30, 185), (90, 50)),
            manager=ui_manager,
            text="View",
            container=self._bottom_frame,
            command=self._view
        )
        self._read_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((30, 235), (90, 30)),
            manager=ui_manager,
            text="Read",
            container=self._bottom_frame,
            # TODO: command send read angles request to Arduino
            # requires c code
        )
        self._reset_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((120, 185), (90, 50)),
            manager=ui_manager,
            text="Reset",
            container=self._bottom_frame,
            command=self._reset
        )
        self._set_origin_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((120, 235), (90, 30)),
            manager=ui_manager,
            text="Set Origin",
            container=self._bottom_frame,
            command=partial(self._arduino_ser.send_data, "^SET ORIGIN")
        )
        self._go_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((210, 185), (90, 50)),
            manager=ui_manager,
            text="Go",
            container=self._bottom_frame,
            command=self._go
        )
        self._go_inverse_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((210, 235), (90, 30)),
            manager=ui_manager,
            text="Go Inverse",
            container=self._bottom_frame,
            command=self._go_inverse
        )
        self._preview_motctl_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((30, 270), (270, 30)),
            manager=ui_manager,
            text="Preview MOTCTL",
            container=self._bottom_frame,
            command=self._preview_motctl
        )

    def _get_chunks_generator(self) -> Generator:
        # Returns a generator of chunks from the motctl file lines.
        with open("data/output.motctl", "r", encoding="utf-8") as f:
            content = f.read()
            chunks = list(filter(lambda x: bool(x.strip()), re.split(
                r"(^&\d+\n)",  # Of the form '&12345'
                content,
                flags=re.MULTILINE
            )))

            print("chunks: ", chunks)  # TODO REMOVE
            yield from chunks

    def _preview_motctl(self):
        # When user clicks preview button
        if self._preview_started:
            print("Could not start preview. Preview already started.")
            return

        self._chunks_gen = self._get_chunks_generator()
        for chunk in self._chunks_gen:
            for line in chunk.splitlines():
                if line[0] != "@":
                    continue

                angles = [steps_to_deg(int(a)) for a in line[1::].split(" ")]
                angles = dict(zip(list("xyza"), angles))
                print(angles)
                self._update_angles(angles)
                time.sleep(0.2)

        return
        self._preview_started = True
        self._send_next_chunk()

    def _send_next_chunk(self):
        # Send the next chunk and begin waiting for the end response.
        if self._chunks_gen is None:
            print("No more chunks to send.")
            return

        try:
            self._arduino_ser.send_data(
                data=next(self._chunks_gen),
                response_map={
                    "NEXT CHUNK": self._send_next_chunk,
                    "MEMORY ALLOCATED": self._send_next_chunk,
                    "DONE": self._stop,
                }
            )
        except StopIteration:
            print("No more chunks to send.")

    def _go(self):
        self._is_moving = True
        self._arduino_ser.send_angles(self._motor_angles)

    def _go_inverse(self):
        self._is_moving = True
        self._arduino_ser.send_angles(self._motor_angles, invert=True)

    def _stop(self):
        self._is_moving = False
        self._chunks_gen = None
        self._arduino_ser.stop_all_motors()

    def _view(self) -> None:
        # Sets the arm's angles to the value in the entries and updates
        # the visualisation.
        # Read entries
        new_angles = {}
        for angle_key, ui_element in self._angle_elements.items():
            entry = ui_element["entry"]
            try:
                entry_value = float(entry.get_text())
                new_angles[angle_key] = entry_value
            except ValueError:
                # If the entry text is invalid reset it to match the arm's
                # angle for that axis
                angle_value = self._motor_angles.get(angle_key)
                entry.set_text(str(angle_value))
        self._update_angles(new_angles)  # Update angles

    def _reset(self) -> None:
        # Reset arm position to origin. Sets the arm's angles to zero.
        self._update_angles(ZERO_ANGLES)

    def _update_angles(self, angles: dict[str, float]) -> None:
        # Updates the arm's angles and sets the entry texts to match.
        self._motor_angles.update(angles)

        # Update the entry UI elements
        for angle_key, ui_element in self._angle_elements.items():
            entry = ui_element["entry"]
            angle_value = self._motor_angles.get(angle_key)
            entry.set_text(str(angle_value))

    def handle_event(self, event: Event):
        """Handle a pygame event."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check if mouse is within the pen tip hitbox
            if self._drag_arm_hitbox.collidepoint(pygame.mouse.get_pos()):
                self._arm_drag_enable = True
            elif self._y_angle_hitbox.collidepoint(pygame.mouse.get_pos()):
                self._y_angle_drag_enable = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self._arm_drag_enable = False
            self._y_angle_drag_enable = False

    def update(self, time_delta: float):
        """Update called each frame."""
        pen_tip = draw_arm_side_view(
            self.surface,
            ARM_LEN_1,
            ARM_LEN_2,
            BASE_HEIGHT,
            PEN_ARM_LEN,
            PEN_LEN,
            -self._motor_angles["z"],  # This has to be negative
            self._motor_angles["x"],
            self._motor_angles["a"],
            WIN_WIDTH,
            WIN_HEIGHT,
            BASE_SCREEN_OFFSET,
            self._font
        )

        self._drag_arm_hitbox = _get_mouse_hitbox(
            pen_tip,
            DRAG_ARM_HITBOX_SIZE,
            self.surface
        )

        y_angle_origin = Vector2(450, 850)

        # Pygame dragging UI events
        if self._arm_drag_enable:
            world_x, world_z = _screen_to_world_coords(*pygame.mouse.get_pos())
            world_z -= BASE_HEIGHT
            world_z += PEN_LEN

            positions = {"x": world_x, "y": 0, "z": world_z}
            for pos_key, label in self._position_labels.items():
                label.set_text(f"Position {pos_key}: {positions[pos_key]}")

            # Retrieve and validate angles
            world_x, _, world_z = get_nearest_valid_point(
                world_x, 0, world_z,
                BASE_HEIGHT, ARM_LEN_1, ARM_LEN_2
            )
            new_angles = get_real_angles(
                world_x, 0, world_z, BASE_HEIGHT, ARM_LEN_1, ARM_LEN_2
            )

            if new_angles:
                # Store new angles in correct xyz format with offsets
                new_angles.update({"y": self._motor_angles["y"]})
                self._update_angles(new_angles)

        # If user is dragging the Y angle handle
        elif self._y_angle_drag_enable:
            # Calculate and update new Y angle
            mouse_pos = pygame.mouse.get_pos()
            relative_pos = mouse_pos - y_angle_origin
            y_angle = math.degrees(math.atan2(relative_pos.y, relative_pos.x))
            self._update_angles({"y": round(y_angle + 90, 2)})  # Offset 90 deg

        # Y angle UI
        pygame.draw.circle(self.surface, WHITE, y_angle_origin, 120, 3)
        pygame.draw.line(self.surface, WHITE, y_angle_origin, (450, 730), 3)

        y_line_end = Vector2(450, 730)

        y_angle_origin, y_line_end = rotate_line(
            (450, 850), (450, 730), self._motor_angles["y"]
        )
        self._y_angle_hitbox = _get_mouse_hitbox(y_line_end, 50, self.surface)
        pygame.draw.line(self.surface, GREEN, y_angle_origin, y_line_end, 7)
        pygame.draw.circle(self.surface, ORANGE, y_line_end, 10)


def _screen_to_world_coords(screen_x: int, screen_y: int):
    """Convert screen (x, y) coordinates to world (x, z) coordinates.
    X is forward, Z is upward."""
    world_x = screen_x - WIN_WIDTH // 2 - BASE_SCREEN_OFFSET.x + PEN_ARM_LEN
    world_z = WIN_HEIGHT - screen_y - BASE_SCREEN_OFFSET.y + PEN_LEN
    return world_x, world_z


def _get_mouse_hitbox(
        pos: Vector2,
        size: int = 20,
        draw_surf: pygame.Surface | None = None):
    """Returns the mouse rectangle around a position given a position
    and a size. Essentially a hitbox calculator."""
    mouse_rect = pygame.Rect(
        pos.x - size // 2,
        pos.y - size // 2,
        size,
        size
    )
    if draw_surf:
        pygame.draw.rect(draw_surf, Color("#666666"), mouse_rect, 1)

    return mouse_rect

