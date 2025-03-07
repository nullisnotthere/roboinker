"""
Handles prompt processing and filtering to convert spoken text strings
to a clean,
structured prompt for Dream AI (https://dream.ai/)
"""

import os
import time
import re

from dotenv import load_dotenv
from requests.exceptions import HTTPError
from src.rpi.backend.prompt_processing.deep_ai_wrapper import api as deep_api


load_dotenv()

MAX_LENGTH = 350  # 350 character limit set by Dream AI free plan
PROMPT_PREFIX = "A simple"
PROMPT_SUFFIX = (
    "illustration in black shape forms "
    "on a pure plain white background. "
    "Minimal and simplistic. "
    "No small details."
)

DEEP_AI_EXTRACTION_PREFIX = (
    "You are now a natural language processing robot. "
    "I will give you a prompt phrase that is to later be fed "
    "into an image generation AI that will produce an image that "
    "is to be drawn by a drawing robot. Your job is to parse "
    "this prompt phrase, simplify it and extract the keywords. "
    "From this you must construct a new, simple, effective prompt "
    "that encapsulates the essence of the original prompt as a "
    "straightforward new prompt. If there are negated, or later "
    "altered terms or phrases, exclude them from the final prompt. "
    "You must be methodical and precise for this operation. "
    "For example; Original prompt: Draw me a scene of uhm, "
    "a knight holding a spear... hm, actually no, not a spear... "
    "maybe a broadsword instead. Oh and make him riding a horse. "
    "New prompt: Knight holding sword riding horse. "
    "Notice how the users mind changed after suggesting the spear, "
    "so it is excluded from the final prompt and the new object (sword) "
    "in included. Use this as a guide when you parse my following prompts. "
    "Only return back the new prompt text, do not include a prefix like "
    "new prompt: or anything similar. If there is no prompt provided, or the "
    "prompt is utterly unintelligible, please only return the word EMPTY. "
    "Here is the prompt for you to parse: "
)
DEEP_AI_API_KEY = os.getenv("DEEP_AI_API_KEY")


def _force_clean_text(text: str) -> str:
    # Strips and converts text to only use the allowed characters to
    # ensure compatibility with Deep AI.
    allowed_chars = r",\.-;:=+/*&^%$#@!()\[\]{}<> "
    escaped_chars = "\\".join(allowed_chars)
    filtered_text = re.sub(
        f"[^{escaped_chars}1-9a-z]",
        "",
        text.lower().strip()
    )
    return filtered_text


def extract_essential_phrase(prompt: str, retries=3, delay=2) -> str:
    """Using Deep AI via an API wrapper, this function extracts the 'essence'
    of the user's prompt, ensuring a minimal and effective prompt
    simplification."""

    print(f"{_force_clean_text(prompt)=}")

    # Pre-defined chat message history
    messages = [
        {
            "role": "user",

            "content": _force_clean_text(DEEP_AI_EXTRACTION_PREFIX)
        },
        {
            "role": "assistant",
            "content": "EMPTY"
        },
        {
            "role": "user",
            "content": f"Prompt: {_force_clean_text(prompt)}"
        }
    ]

    for t in range(retries + 1):
        try:
            # Ensure API key exists in .env
            if not DEEP_AI_API_KEY:
                raise RuntimeError(
                    "Could not retreive Deep AI API key environment variable."
                )

            response = next(deep_api.chat(DEEP_AI_API_KEY, messages))
            if response is not None:
                return response

        except (HTTPError, StopIteration) as e:
            print(
                "An error occured when trying to extract essential phrase "
                f"via Deep AI API wrapper: {e}. The prompt has been returned "
                "as the essential phrase. "
            )
            if t <= retries:
                print(f"Retrying... ({t + 1})")
            time.sleep(delay)

        finally:
            # This always gets called,
            # but does not affect the successful response return
            response = prompt

    print(f"Deep AI API connection failed after {retries} retries.")
    return response


def add_image_gen_params(prompt: str) -> str:
    """Adds the image generation parameters to ensure the result image can be
    easily simplified into contours."""

    final = " ".join([PROMPT_PREFIX, prompt, PROMPT_SUFFIX])

    # Prompt phrase is too long
    if len(final) > MAX_LENGTH:
        print(
            f"WARNING!!! Prompt is too long: {len(final)}/{MAX_LENGTH} char. "
            "Prompt will be trimmed as a result of this. Image may not be "
            "generated as expected."
        )

    return final[:MAX_LENGTH]


def get_max_user_prompt_len() -> int:
    """Returns max length of the user's prompt. Max character limit set
    by Dream AI minus our prompt prefix and suffix lengths."""
    raise NotImplementedError
