import asyncio
import cv2
import numpy as np
import perchance
from PIL import Image


async def main():
    """Main"""
    print('Initializing...')

    gen = perchance.ImageGenerator()
    # refresh generator so it will take less
    # time to generate the first response
    await gen.refresh()

    while True:
        prompt = input("Prompt: ")
        print("Generating...")

        async with await gen.image(prompt) as res:
            # download image as a bytes-like object
            raw = await res.download()
            # open the image with Pillow
            img = Image.open(raw)

            opencv_image = np.array(img)
            gray_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)

        _, binary_image = cv2.threshold(
            gray_image, 127, 255, cv2.THRESH_BINARY
        )

        contours, _ = cv2.findContours(
            binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        cv2.drawContours(opencv_image, contours, -1, (0, 255, 0), 3)

        result_image = Image.fromarray(opencv_image)
        result_image.show()
        del result_image


if __name__ == '__main__':
    asyncio.run(main())
