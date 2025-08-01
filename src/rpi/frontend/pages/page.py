import pygame_gui

from pygame import Rect, Surface, Event
from pygame_gui import UIManager


class Page:
    """A generic page that can be extended for more complex GUIs."""
    def __init__(
            self,
            tab_title: str,
            tab_object_id: str,
            surface: Surface,
            ui_manager: UIManager):
        self.tab_object_id = tab_object_id  # Used for the tab title object id
        self.tab_title = tab_title
        self.surface = surface
        self.ui_manager = ui_manager

        # Init all UI elements here
        self._main_frame = pygame_gui.elements.UIPanel(
            relative_rect=Rect((0, 34), (600, 990)),
            starting_height=990,
            manager=self.ui_manager,
            visible=False
        )

        self.hide()

    def show(self):
        """Show the page."""
        self._main_frame.show()

    def hide(self):
        """Hide the page."""
        self._main_frame.hide()

    def handle_event(self, event: Event):
        """Handle a pygame event."""

    def update(self, time_delta: float):
        """Update called each frame."""

    def quit(self):
        """Graceful exit."""
