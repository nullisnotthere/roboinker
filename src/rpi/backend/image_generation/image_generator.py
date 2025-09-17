#!/usr/bin/env python3

import requests
import numpy as np
import cv2

from cv2.typing import MatLike
from src.rpi.backend.image_generation.bingart import BingArt, AuthCookieError
from src.rpi.backend.image_generation.bing_token_retriever import (
    get_token,
    retrieve_new_cookie
)

BING_URL = "https://www.bing.com"


def generate_images(prompt: str, u_token: str | None) -> list[MatLike] | None:
    """
    Generates images using Bing AI and returns a list of OpenCV images.
    Source: https://github.com/DedInc/bingart/tree/main
    """

    while True:
        try:
            bing_art = BingArt(auth_cookie_U=u_token)
            results = bing_art.generate_images(prompt)

            # Return the extracted OpenCV images
            cv_images = []
            images = results.get("images")

            if images is None:
                return None

            # Extact URLs from BingAI data
            urls = {img.get("url") for img in images if img.get("url")}
            for url in urls:
                # Get the images at those URLs
                cv_img = _extract_image(url)
                if cv_img is None:
                    continue
                cv_images.append(cv_img)
            return cv_images
        except AuthCookieError:
            print(
                "AuthCookieError! You may be rate limited or there is "
                "an internal server error."
            )
            u_token = retrieve_new_cookie()
            if u_token is None:
                print("Failed to retrieve new cookie.")
                return None
        finally:
            bing_art.close_session()


def _extract_image(image_url) -> MatLike | None:
    # Extracts an image from a given image URL in OpenCV format.

    # Try to download image from final URL
    try:
        print(f"Extracting image at url {image_url}")
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except (requests.exceptions.RequestException,
            requests.exceptions.HTTPError) as req_err:
        print(f"Failed to download image: {req_err}")
        return None

    # Try to open the image and return OpenCV image
    try:
        image_bytes = np.frombuffer(response.content, np.uint8)
        cv_image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        print("Successfully retreived image data.")
        return cv_image
    except (IOError, ValueError) as img_err:
        print(f"Failed to convert response content to OpenCV image. {img_err}")
        return None
