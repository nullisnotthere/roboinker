"""
Handles prompt processing and filtering to convert spoken text strings
to a clean,
structured prompt for Dream AI (https://dream.ai/)
"""

MAX_LENGTH = 350  # 350 character limit set by Dream AI free plan
PROMPT_PREFIX_PARAMS = (
    "A simple",
)
PROMPT_SUFFIX_PARAMS = (
    "illustration",
    "in black shapes",
    "pure plain white background",
#    "large area shapes",
#    "no shading",
#    "no gradients",
#    "no highlights",
#    "no outlines",
#    "no detail",
)


def filter_prompt(prompt_phrase: str) -> str:
    """Filters prompt phrase and returns a clean Perchance prompt.
    350 characters maximum limit."""

    prefix = ", ".join(PROMPT_PREFIX_PARAMS)
    suffix = ", ".join(PROMPT_SUFFIX_PARAMS)
    final = " ".join([prefix, prompt_phrase, suffix])

    if len(final) > MAX_LENGTH:
        print(
            f"WARNING!!! Prompt is too long: {len(final)} char/{MAX_LENGTH}. "
            "Prompt will be trimmed as a result of this. Image may not be "
            "generated as expected."
        )

    return final[:MAX_LENGTH]


def get_max_user_prompt_len() -> int:
    """Returns max length of the user's prompt. Max character limit set
    by Dream AI minus our prompt prefix and suffix lengths."""
    raise NotImplementedError
