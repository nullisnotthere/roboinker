#!/usr/bin/env python3

import time
import re
import random

from urllib.parse import urljoin

import requests
import numpy as np
import cv2

from cv2.typing import MatLike
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

BING_URL = "https://www.bing.com"


def generate_images(prompt: str, u_token: str) -> list[MatLike] | None:
    """Generates images using Bing AI and returns a list of OpenCV images."""

    ua = UserAgent()
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.bing.com',
        'DNT': '1',
        'Sec-GPC': '1',
        'Alt-Used': 'www.bing.com',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i',
    }

    cookies = {
        '_C_Auth': '',
        '_IDET': 'MIExp=0',
        '_U': u_token,
    }

    data = {
        'q': prompt,
        'qs': 'ds'
    }

    # First response gets us the endpoint URL
    response = requests.post(
        f'https://www.bing.com/images/create?q={prompt}&rt=3',
        cookies=cookies,
        headers=headers,
        data=data,
        timeout=10
    )
    response.raise_for_status()

    # Parse for endpoint URL
    endpoint = ""
    soup = BeautifulSoup(response.text, 'html.parser')

    # Guard clauses
    results_div = soup.find("div", id="gir")
    if not results_div:
        print("No results div found.")
        return None

    data_c = str(results_div.get("data-c", ""))
    if not data_c:
        print("Failed to find results endpoint. It is likely that the prompt "
              "has been blocked by Bing's content policy.")
        return None

    regex_match = re.match(r"^.*?(?=\?q\=)", data_c)
    if not regex_match:
        print(f"Failed to match regex in data-c element: {data_c}.")
        return None

    endpoint = regex_match.group(0)
    url = urljoin(BING_URL, endpoint)

    images = _get_images(url, cookies, headers)
    return images


def _get_images(
        endpoint_url: str,
        cookies,
        headers,
        tries=20,
        delay=3) -> list[MatLike] | None:
    # Tries to get a list of OpenCV images from the Bing endpoint URL

    img_urls = []
    for i in range(tries):
        print(f"Trying to get images from generation endpoint {endpoint_url}."
              f" Try #{i + 1}...")
        time.sleep(delay)

        response = requests.post(
            endpoint_url,
            cookies=cookies,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        # Parse for image URLs
        soup = BeautifulSoup(response.text, 'html.parser')
        img_elems = soup.find_all(class_=["image-row-img", "bceimg", "mimg"])

        if not img_elems:
            print("No images found this time.")
            continue

        # Store the image URLs found on the img elements in a list
        img_urls = []
        for img_elem in img_elems:
            src = img_elem.get("src")

            if src is None:
                print("Could not find data-src attribute.")
                continue

            # Take the key URL component and adjust to 1024x1024 px resolution
            url_match = re.match(r"^.*?\?", str(src))
            if url_match:
                url = url_match.group(0) + "w=1024&h=1024"
                img_urls.append(url)
        break

    if not img_urls:
        print("No images were found.")
        return None

    # Collect images on the endpoint page as OpenCV images
    cv_images: list[MatLike] | None = []
    for img_url in img_urls:
        cv_image = _extract_image(img_url)
        if cv_image is None:
            # This error is already debug logged in the _extract_image function
            continue
        cv_images.append(cv_image)

    return cv_images


def _extract_image(image_url: str) -> MatLike | None:
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

