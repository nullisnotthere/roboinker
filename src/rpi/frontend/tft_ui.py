#!/usr/bin/env python3

"""
The user interface to be displayed on the TFT display connected to the
Raspberry PI.
"""

import src.rpi.backend.env_loader

import pygame
import pygame_gui

from src.rpi.backend.serial_com.arduino_serial import ArduinoSerial

from src.rpi.frontend.pages.visualiser_page import VisualiserPage
from src.rpi.frontend.pages.voice_page import VoicePage
from src.rpi.frontend.pages.move_page import MovePage
from src.rpi.frontend.pages.image_page import ImagePage
from src.rpi.frontend.constants import WIN_SIZE

# Window settings
BG_COLOUR = pygame.Color("White")
FPS = 60
DRAW_SPEED_MULTIPLIER = 50  # Draw speed = FPS * this value

# Directories
ANGLES_FILE_PATH = "data/output.motctl"

# Robotic arm configuration
BASE = 65
ARM1 = ARM2 = 250
PEN_OFFSET = 30
PEN_UP_OFFSET = 5  # This much higher when pen is up

# The value to change the detail level by when too high/low
DETAIL_LEVEL_ADAPT = 0.1
CONTOURS_COUNT_MAX = 50
CONTOURS_COUNT_MIN = 15


def main() -> None:
    """Main function"""

    # Create Arduino serial connection
    arduino_ser = ArduinoSerial()

    # Init Pygame
    pygame.init()
    pygame.display.set_caption("RoboInker GUI")
    debug_font = pygame.sysfont.SysFont("Monospace", 16, bold=True)
    screen = pygame.display.set_mode(WIN_SIZE)
    clock = pygame.time.Clock()
    running = True

    # Init Pygame GUI
    ui_manager = pygame_gui.UIManager(WIN_SIZE)

    # UI elements
    tab_container = pygame_gui.elements.UITabContainer(
        relative_rect=pygame.Rect((0, 0), (600, 1024)),
        manager=ui_manager
    )

    # Initialise pages
    voice_page = VoicePage(screen, ui_manager)
    image_page = ImagePage(
        screen,
        ui_manager,
        get_prompt_callback=voice_page.get_prompt
    )
    visualiser_page = VisualiserPage(
        screen,
        ui_manager,
        debug_font,
        arduino_ser,
        get_contours_callback=image_page.get_contours
    )
    move_page = MovePage(screen, ui_manager, debug_font, arduino_ser)

    # Define the pages using dict comprehension for id: obj pairs
    pages = {
        page_obj.tab_object_id: page_obj
        for page_obj in (
            voice_page,
            image_page,
            visualiser_page,
            move_page
        )
    }
    active_page = pages["#move_tab"]  # Open to this page initially
    #active_page = list(pages.values())[0]

    for page_id, page in pages.items():
        tab_container.add_tab(page.tab_title, page_id)
        page.hide()
    active_page.show()

    while running:
        time_delta = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Pass events to GUI manager
            ui_manager.process_events(event)
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                # Tab button clicked
                if event.ui_element.parent_element is tab_container:
                    # Change to the clicked tab
                    tab_object_id = event.ui_element.object_ids[-1]
                    active_page.hide()
                    active_page = pages[tab_object_id]
                    active_page.show()
            active_page.handle_event(event)

        # Update UI
        ui_manager.update(time_delta)

        # Drawing
        screen.fill("#161821")
        ui_manager.draw_ui(screen)

        # Update active page
        active_page.update(time_delta)

        # Update pygame display
        pygame.display.update()

    # Gracefully quit all pages
    for page in pages.values():
        page.quit()

    # Quit
    pygame.quit()


if __name__ == "__main__":
    main()

