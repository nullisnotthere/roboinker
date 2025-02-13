"""
Handles prompt processing and filtering to convert spoken text strings
to a clean, structured prompt for Dream AI (https://dream.ai/)
"""


def filter_prompt(prompt_phrase: str) -> str:
    """Filters prompt phrase and returns a clean Perchance prompt."""

    suffix = ", ".join([
        " simple illustration",
        "flat style in black ink on pure white background",
        "fits full frame",
    ])
    return prompt_phrase + suffix
