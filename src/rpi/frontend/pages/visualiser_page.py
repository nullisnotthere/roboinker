from typing import Callable

import time
import pygame
import pygame_gui

from pygame import Rect, Surface, Font
from pygame_gui import UIManager

from src.rpi.frontend.constants import WIN_RECT
from src.rpi.frontend.pages.page import Page
from src.rpi.backend.serial_com.arduino_serial import ArduinoSerial


class VisualiserPage(Page):
    """Visualiser page that shows the drawing process."""
    def __init__(self, surface: Surface, ui_manager: UIManager, font: Font,
                 arduino_ser: ArduinoSerial,
                 get_contours_callback: Callable):
        super().__init__(
            tab_title="Visualiser",
            tab_object_id="#visualiser_tab",
            surface=surface,
            ui_manager=ui_manager
        )
        self._font = font
        self._arduino_ser = arduino_ser

        self._last_read_time = 0
        self._is_moving = False

        # Callback to the image page for getting the extracted contours
        self._get_contours_callback = get_contours_callback

        self._top_frame = pygame_gui.elements.UIPanel(
            relative_rect=Rect((0, 0), (600, 450)),
            starting_height=450,
            manager=ui_manager,
            container=self._main_frame
        )

        self._bottom_frame = pygame_gui.elements.UIPanel(
            relative_rect=Rect((0, 450), (600, 500)),
            manager=ui_manager,
            starting_height=500,
            container=self._main_frame
        )

        self._start_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((10, 10), (90, 50)),
            manager=ui_manager,
            text="Start",
            container=self._top_frame,
            command=self._start
        )

    def _start(self):
        """Start moving the arm and visualising the motor positions."""

    def update(self, time_delta: float):
        """Update called each frame."""

        # Read responses from Arduino
        current_time = time.time()
        if self._is_moving and (
                current_time - self._last_read_time >= READ_RESPONSE_COOLDOWN):
            response = self._arduino_ser.request_reached()
            print("LOOP REACHED REQUEST RESULT:", response)
            self._last_read_time = current_time
            if response != "FALSE":
                self._is_moving = False


