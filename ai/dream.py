#!/usr/bin/env python3

"""
Sources:
https://github.com/krisskad/DreamAI?tab=readme-ov-file
https://dream.ai/create
"""

from typing import Sequence
from io import BytesIO

import os
import time
import math
import json
import requests
import cv2
import numpy as np

from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

from dotenv import load_dotenv, set_key
from .art_styles import ArtStyle


load_dotenv()

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
HEADERS_FILE = os.path.join(MODULE_DIR, "headers.json")
DOT_ENV_PATH = os.path.join(MODULE_DIR, ".env")
READ_VTOKEN_SCRIPT = os.path.join(MODULE_DIR, "read_validation_token.js")
COOKIES_FILE = os.path.join(MODULE_DIR, "cookies.json")

SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/"
API_KEY = "AIzaSyDCvp5MTJLUdtBYEKYWXJrlLzu1zuKM6Xw"
USER_AGENT = "user-agent=Mozilla/5.0 (X11; Linux x86_64; rv:135.0) \
        Gecko/20100101 Firefox/135.0"

EMAIL_INPUT_XPATH = "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[1]\
        /div[1]/input"
PASSWORD_INPUT_XPATH = "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[1]\
        /div[2]/input"
LOGIN_BTN_XPATH = "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[2]\
        /div[2]/button"


# Function to refresh the token
def _get_new_auth_token() -> str | None:
    refresh_url = f"{SIGN_IN_URL}accounts:signInWithPassword?key={API_KEY}"

    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "email": os.getenv("EMAIL"),
        "password": os.getenv("PASSWORD"),
        "returnSecureToken": True
    }

    response = requests.post(
        refresh_url,
        headers=headers,
        json=data,
        timeout=60
    )

    # Check if the response is valid
    if response.status_code == 200:
        # Parse the JSON response
        response_data = response.json()
        new_auth_token = response_data.get("idToken")

        if new_auth_token:
            print(f"New auth token: {new_auth_token}")
            os.environ["AUTHORIZATION_TOKEN"] = new_auth_token
            set_key(DOT_ENV_PATH, "AUTHORIZATION_TOKEN", new_auth_token)

            return new_auth_token

    print(
        "Failed to retrieve auth token."
        f"Status code: {response.status_code}."
        f"Response: {response.text}"
    )

    return None

# store auth & validation token TODO


def _get_new_validation_token(tries=3) -> str | None:
    # Set up the driver
    firefox_options = Options()
    firefox_options.headless = True  # Set headless mode
    firefox_options.add_argument('--disable-extensions')
    firefox_options.add_argument('--disable-gpu')
    firefox_options.add_argument('--no-sandbox')
    firefox_options.add_argument('--headless')
    firefox_options.add_argument(USER_AGENT)

    # Setup the path to the GeckoDriver
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=firefox_options)

    try:
        print('Launching webdriver...')

        # Navigate to the login page
        driver.get("https://dream.ai/profile")

        # Fill in the login credentials
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD")

        if not (email and password):
            raise ValueError(
                "Failed to retrieve email and password from dotenv."
            )

        # Enter email & password, then click login button
        email_input = driver.find_element(By.XPATH, EMAIL_INPUT_XPATH)
        email_input.send_keys(email)

        password_input = driver.find_element(By.XPATH, PASSWORD_INPUT_XPATH)
        password_input.send_keys(password)

        button = driver.find_element(By.XPATH, LOGIN_BTN_XPATH)
        button.click()

        for t in range(1, tries + 1):
            time.sleep(6)  # Delay to allow page to load

            # Execute JavaScript code to fetch the validation token
            with open(READ_VTOKEN_SCRIPT, "r", encoding="utf-8") as script:
                new_validation_token = driver.execute_script(script.read())

                if new_validation_token:
                    break
                if t < tries:
                    print("Failed to read token. Retrying...")
                else:
                    raise RuntimeError("Failed to retrieve validation token.")

        # Print the token for debugging
        print("\n New validation token:", new_validation_token)
        os.environ["VALIDATION_TOKEN"] = new_validation_token
        set_key(DOT_ENV_PATH, "VALIDATION_TOKEN", new_validation_token)

    finally:
        driver.quit()

    return new_validation_token


def _load_headers() -> dict[str, str]:
    try:
        with open(HEADERS_FILE, "r", encoding="utf-8") as f:
            try:
                headers = json.load(f)
            except json.JSONDecodeError:
                print("Could not decode headers.json.")
    except FileNotFoundError:
        print("Could not open headers file (JSON).")

    auth_token = os.getenv("AUTHORIZATION_TOKEN")
    validation_token = os.getenv("VALIDATION_TOKEN")

    if not auth_token or not validation_token:
        raise ValueError("Missing required environment variables.")

    headers.update(
        {
            "Authorization": "bearer " + auth_token,
            "x-validation-token": validation_token
        }
    )
    return headers


def get_prompt(prompt_phrase: str):
    """Filters prompt phrase and returns a clean Perchance prompt."""
    suffix = ", ".join([
        " simple illustration",
        "flat style in black ink on pure white background",
        "fits full frame",
    ])
    return prompt_phrase + suffix


def get_contours(
        img: Image.Image,
        arm_max_length: float,
        up_is_positive: bool = False) -> Sequence[np.ndarray]:
    """Returns contours from a given image."""

    opencv_image = np.array(img)
    opencv_image = cv2.rotate(opencv_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    opencv_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)

    # Resize to the optimal area within semi circle, keeping the aspect ratio
    img_h, img_w = opencv_image.shape[:2]  # Height first, then width
    w, h = tuple(
        map(int, _max_rect_from_semi(img_w, img_h, arm_max_length))
    )
    opencv_image = cv2.resize(opencv_image, (w, h))

    edges = cv2.Canny(opencv_image, 50, 150, L2gradient=True)  # Edge detection

    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # NOTE: In the final version this may have to be `+h` and float divide (/)
    # Tweak as required
    if isinstance(w, int):
        off_x, off_y = -w // 2, h if up_is_positive else -h
    else:
        off_x, off_y = -w / 2, h if up_is_positive else -h
    contours = [cnt + np.array([off_x, off_y]) for cnt in contours]

    return contours


def _check_task_status(task_id):
    """Check if current request is compeleted."""
    headers = _load_headers()

    response = requests.get(
        f"https://paint.api.wombo.ai/api/v2/tasks/{task_id}",
        headers=headers,
        timeout=60
    )
    if response.status_code == 200:
        return response.json()
    raise RuntimeError(f"Error checking task status: {response.json()}")


def _max_rect_from_semi(
        width: float,
        height: float,
        radius: float) -> tuple[float, float]:

    w = radius / math.sqrt((height / width) ** 2 + (1 / 4))
    h = math.sqrt(radius ** 2 - (w ** 2) / 4)
    return w, h


def generate_image(prompt: str, style_id: ArtStyle, retries: int = 3
                   ) -> Image.Image | None:
    """Returns a PIL Image based on a given prompt via Dream AI wrapper."""
    while True:
        headers: dict[str, str] = _load_headers()

        data = {
            "is_premium": False,
            "input_spec": {
                "aspect_ratio": "old_vertical_ratio",
                "display_freq": 10,
                "prompt": prompt,
                "style": style_id.value
            }
        }

        print("Posting response...")
        gen_response = requests.post(
            "https://paint.api.wombo.ai/api/v2/tasks",
            headers=headers, data=json.dumps(data),
            timeout=60,
        )
        time.sleep(5)

        # Extract task ID
        task_id = gen_response.json().get("id")
        task_detail = gen_response.json().get("detail")

        if not task_id:
            print("Task ID missing in response.\n", gen_response.json())

            if task_detail in ("Invalid token", "Token expired"):
                print("Invalid or expired tokens detected. Updating...")
                _get_new_auth_token()
                _get_new_validation_token()
                continue
            return None
        break

    # Poll for task completion
    success = False
    for _ in range(retries):
        task_status = _check_task_status(task_id)
        print(f"Current task status: {task_status.get("state")}")

        if task_status.get("state") == "completed":
            image_url = task_status.get("result", {}).get("final")
            if image_url:
                success = True
                break
            print("No 'final' URL in the response.")
            break

        if task_status.get("state") == "failed":
            print("Task failed.")
            break

        print("Task is still pending. Waiting...")

        # Wait for a while before checking again
        time.sleep(3)

    if not success:
        raise RuntimeError(f"Failed to retreive image after {retries} tries.")

    try:
        print(f"Getting image at url {image_url}")
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except requests.exceptions.RequestException as req_err:
        print(f"Failed to download image: {req_err}")
        return None

    try:
        pil_image = Image.open(BytesIO(response.content))
        return pil_image
    except (IOError, ValueError) as img_err:
        print(f"Failed to open image: {img_err}")
        return None
