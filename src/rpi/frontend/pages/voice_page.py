import os
import re
import pygame
import pygame_gui
import ai4free

from dotenv import load_dotenv
from pygame import Rect, Surface
from pygame_gui import UIManager

from src.rpi.frontend.pages.page import Page
from src.rpi.backend.voice_processing.voice_processing import VoiceProcessor
from src.rpi.backend.prompt_processing import prompt_processing as prompt_proc


load_dotenv()

# Ensure API key environment variables exist
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY is None:
    raise RuntimeError("Missing required environment variable: GROQ_API_KEY")


class VoicePage(Page):
    """Page to record and visualise live voice prompt text."""
    def __init__(
            self,
            surface: Surface,
            ui_manager: UIManager):
        super().__init__(
            tab_title="Voice Prompt",
            tab_object_id="#voice_tab",
            surface=surface,
            ui_manager=ui_manager
        )

        self._listening = False
        self._vp = VoiceProcessor(samplerate=50000)
        self._full_voice = ""
        self._processing_voice = ""
        self._prompt = None

        # Create an instance of the prompt AI
        self._prompt_ai = ai4free.GROQ(
            api_key=GROQ_API_KEY,  # pyright: ignore
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )

        self._main_frame = pygame_gui.elements.UIPanel(
            relative_rect=Rect((25, 225), (550, 550)),
            starting_height=700,
            manager=ui_manager
        )

        self._speak_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((10, 10), (100, 50)),
            manager=ui_manager,
            text="Speak",
            container=self._main_frame,
            command=self._start_listening
        )

        self._done_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((120, 10), (100, 50)),
            manager=ui_manager,
            text="Done",
            container=self._main_frame,
            command=self._done
        )

        self._voice_text_box = pygame_gui.elements.UITextEntryBox(
            relative_rect=Rect((25, 100), (500, 200)),
            manager=ui_manager,
            placeholder_text="Press Speak or start typing to begin...",
            container=self._main_frame
        )
        self._essence_text_box = pygame_gui.elements.UITextBox(
            relative_rect=Rect((25, 320), (500, 200)),
            manager=ui_manager,
            html_text="<i>Press Done...</i>",
            container=self._main_frame
        )

    def _start_listening(self):
        self._full_voice = ""
        self._vp.start_listening()
        self._listening = True
        self._speak_button.disable()
        self._essence_text_box.set_text("")

    def _stop_listening(self):
        self._full_voice = ""
        self._vp.stop_listening()
        self._listening = False
        self._speak_button.enable()

    def get_prompt(self) -> str:
        """Get the prompt currently stored in the voice page."""
        if self._prompt:
            return self._prompt
        return prompt_proc.add_image_gen_params("Empty")

    def _done(self):
        # Finishes the speech-to-text process and sends the text to an AI
        # to extract essence.
        self._stop_listening()

        # If the user recorded voice audio, use that as the prompt.
        # If the user edited the text box, use that instead.
        if self._full_voice:
            print(f"Voice recorded using voice prompt: {self._full_voice}")
            raw_prompt = self._full_voice
        else:
            raw_prompt = self._voice_text_box.get_text()

        # Extract the essence of the voice prompt
        # 'prompt' argument is the prompt for the text parsing AI
        essence = prompt_proc.extract_essential_phrase(
            ai=self._prompt_ai,
            prompt=raw_prompt
        )

        # Show in the text box
        self._essence_text_box.set_text(self._puntuate_text(essence))

        # Add the image generation parameters to the prompt essence
        self._prompt = prompt_proc.add_image_gen_params(essence)

    @staticmethod
    def _puntuate_text(text):
        # Replaces 'i' with 'I' and capitalises all sentences.
        if text == "":
            return ""

        fixed_text = ""

        parts = re.split(r"([,.!?])", text.strip())
        parts = [p.strip().capitalize() for p in parts if p.strip()]
        fixed_text = "".join(parts)

        fixed_text = fixed_text.replace(" i ", " I ")
        fixed_text = fixed_text.replace(" i'm ", " I'm ")
        fixed_text = fixed_text.replace(".", ". ")

        return fixed_text.strip()

    def update(self, time_delta: float):
        """Update called each frame."""

        if self._listening:
            result = self._vp.process_voice()

            partial_phrase = result.get("partial")
            finished_phrase = result.get("text")

            if partial_phrase and not finished_phrase:
                self._processing_voice = self._full_voice + partial_phrase

            if finished_phrase:
                self._full_voice += finished_phrase + ". "
                self._processing_voice = ""

            print(self._full_voice)

            if self._processing_voice:
                text = self._processing_voice
            else:
                text = self._full_voice
            self._voice_text_box.set_text(self._puntuate_text(text))

            pygame.draw.circle(self.surface, "#bbfe10", (320, 260), 10)
        else:
            pygame.draw.circle(self.surface, "#ea2c09", (320, 260), 10)

    def quit(self):
        """Graceful exit."""
        self._vp.stop_listening()
