import asyncio

from typing import Sequence
import cv2
import numpy as np
import perchance

from PIL import Image


def get_prompt(prompt_phrase: str):
    """Filters prompt phrase and returns a clean Perchance prompt."""
    # TODO
    return prompt_phrase


def get_contours(img: Image.Image) -> Sequence[np.ndarray]:
    """Generates"""
    opencv_image = np.array(img)

    gray_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)

    _, binary_image = cv2.threshold(
        gray_image, 127, 255, cv2.THRESH_BINARY
    )

    contours, _ = cv2.findContours(
        binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    return contours


async def main() -> None:
    """Main function"""

    gen = perchance.ImageGenerator()
    print("Initializing...")

    await gen.refresh()

    while True:
        prompt = input("Prompt: ")

        clean_prompt = get_prompt(prompt)

        print("Generating...")
        async with await gen.image(clean_prompt) as res:
            raw = await res.download()
            img = Image.open(raw)

        contours = get_contours(img)

        opencv_image = np.array(img)
        result_image = Image.fromarray(opencv_image)
        result_image.show()
        cv2.drawContours(opencv_image, contours, -1, (0, 255, 0), 3)

        del result_image


if __name__ == '__main__':
    asyncio.run(main())
