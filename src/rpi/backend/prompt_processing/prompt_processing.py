"""
Handles prompt processing and filtering to convert spoken text strings
to a clean, structured prompt for Dream AI (https://dream.ai/)

Sources:
    ai4free (https://github.com/SreejanPersonal/ai4free-wrapper)
"""

import os
import time
import re

from dotenv import load_dotenv
from requests.exceptions import HTTPError
from webscout.AIbase import Provider


load_dotenv()

MAX_LENGTH = 350  # 350 character limit set by Dream AI free plan
PROMPT_PREFIX = "A simple"
PROMPT_SUFFIX = (
    "illustration in black shape forms "
    "on a pure plain white background. "
    "Minimal and simplistic. "
    "No small details."
)

# Quote characters can not be used as they break the Deep AI request
AI_EXTRACTION_PREFIX = (
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
    "is included. Also, avoid including prefix phrases like 'picture of...' "
    "or 'an image showing...'. Please use this as a guide when you parse "
    "my following prompts. Only return back the new prompt text, do not "
    "include a prefix like 'new prompt:' or anything similar. If there is "
    "no prompt provided, or the prompt is utterly unintelligible, please "
    "only return the word 'EMPTY'. "
    "Here is the prompt for you to parse: "
)


def _force_clean_text(text: str) -> str:
    # Strips and converts text to only use the allowed characters to
    # ensure compatibility with certain AI APIs.
    allowed_chars = r",\.-;:=+/*&^%$#@!()\[\]{}<> "
    escaped_chars = "\\".join(allowed_chars)
    filtered_text = re.sub(
        f"[^{escaped_chars}1-9a-z]",
        "",
        text.lower().strip()
    )
    return filtered_text


def extract_essential_phrase(
        ai: Provider,
        prompt: str,
        retries=3,
        delay=2) -> str:
    """Using AI via an API wrapper, this function extracts the 'essence'
    of the user's prompt, ensuring a minimal and effective prompt
    simplification."""

    prompt = _force_clean_text(AI_EXTRACTION_PREFIX + prompt)
    print(f"{prompt=}")

    for t in range(retries + 1):  # Keep retrying
        try:
            response = ai.chat(prompt)

            print(f"\nResponse from prompt AI: {response}\n")
            return response
        except HTTPError as e:
            print(f"An error occured when trying to extract essential phrase "
                  f"using KOBOLD AI: {e}\nRetrying...")

            # Retry debug and delay before retrying
            if t <= retries:
                print(f"Retrying... ({t + 1})")
            time.sleep(delay)
        finally:
            response = prompt

    print(f"Prompt extraction AI API connection failed after {retries} "
          f"retries.")
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
