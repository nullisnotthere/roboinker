#!/usr/bin/env python3

"""
This API Wrapper interacts with Dream by WOMBO to generate images from the web
and retreive them as PIL Images.

Sources:
https://github.com/krisskad/DreamAI?tab=readme-ov-file
https://dream.ai/create
"""

from io import BytesIO

import os
import time
import json
import requests

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

HEADERS_FILE = os.path.join(MODULE_DIR, "headers.json")  # headers template
DOT_ENV_PATH = os.path.join(MODULE_DIR, ".env")
READ_VTOKEN_SCRIPT = os.path.join(MODULE_DIR, "read_validation_token.js")

DREAM_LOGIN_URL = "https://dream.ai/profile"
SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/"
GENERATE_IMAGE_URL = "https://paint.api.wombo.ai/api/v2/tasks"

USER_AGENT = (
    "user-agent=Mozilla/5.0 (X11; Linux x86_64; rv:135.0) "
    "Gecko/20100101 Firefox/135.0"
)

# Email, password, login button element XPaths
EMAIL_INPUT_XPATH = (
    "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[1]/div[1]/input"
)
PASSWORD_INPUT_XPATH = (
    "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[1]/div[2]/input"
)
LOGIN_BTN_XPATH = (
    "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[2]/div[2]/button"
)


def _get_new_auth_token() -> str | None:
    # Function to refresh the authorization token via web requests to dream.ai

    api_key = os.getenv("API_KEY")
    refresh_url = f"{SIGN_IN_URL}accounts:signInWithPassword?key={api_key}"

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


def _get_new_validation_token(tries=3) -> str | None:
    # Get the validation token via dream.ai with selenium webdriver
    # and read_validation_token.js script injection into console
    # NOTE: The validation token can NOT be accessed via web requests.

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

    # Wrapped in try...finally to ensure the driver is closed if program
    # reaches an exception
    try:
        print('Launching webdriver...')

        # Navigate to the login page
        driver.get(DREAM_LOGIN_URL)

        # Fill in the login credentials
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD")

        if not (email and password):
            raise ValueError(
                "Failed to retrieve email and password from dotenv."
            )

        # Enter email and password, then click login button
        email_input = driver.find_element(By.XPATH, EMAIL_INPUT_XPATH)
        email_input.send_keys(email)
        time.sleep(1)

        password_input = driver.find_element(By.XPATH, PASSWORD_INPUT_XPATH)
        password_input.send_keys(password)
        time.sleep(1)

        button = driver.find_element(By.XPATH, LOGIN_BTN_XPATH)
        button.click()
        time.sleep(6)
        driver.save_screenshot("login.png")

        # Retry if the code fails to retrieve the token
        for t in range(1, tries + 1):
            time.sleep(6)  # Delay to allow page to load

            driver.save_screenshot(f"ss_{t}.png")

            # Execute JavaScript code to fetch the validation token
            with open(READ_VTOKEN_SCRIPT, "r", encoding="utf-8") as script:
                new_validation_token = driver.execute_script(script.read())
                print(new_validation_token)

                if new_validation_token:
                    break

                if t < tries:
                    print("Failed to read token. Retrying...")
                else:
                    raise RuntimeError(
                        "Failed to retrieve validation token "
                        f"after {tries} tries."
                    )

        # Print the token for debugging and store the token in .env
        print("\nNew validation token:", new_validation_token)
        os.environ["VALIDATION_TOKEN"] = new_validation_token
        set_key(DOT_ENV_PATH, "VALIDATION_TOKEN", new_validation_token)

    finally:
        driver.quit()

    return new_validation_token


def _load_headers() -> dict[str, str]:
    # Retreive the headers from headers.json and fill with in the sensitive
    # auth data stored in .env
    # Raises a ValueError if .env environment variables can not be found

    # Get non-sensitive json data from the headers file
    try:
        with open(HEADERS_FILE, "r", encoding="utf-8") as f:
            try:
                headers = json.load(f)
            except json.JSONDecodeError:
                print("Could not decode headers.json.")
    except FileNotFoundError:
        print(f"Could not open headers file: {HEADERS_FILE}")

    # Update with sensitive auth data
    auth_token = os.getenv("AUTHORIZATION_TOKEN")
    #validation_token = os.getenv("VALIDATION_TOKEN")

    if not auth_token: #or not validation_token:
        raise ValueError("Missing required environment variables.")

    headers.update(
        {
            "Authorization": "bearer " + auth_token,
            #"x-validation-token": validation_token
        }
    )
    return headers


def _check_task_status(task_id: str, timeout: float) -> dict | None:
    # Checks if the current request is complete
    # This is used when generating the image. We do not know how long it will
    # take so we must have a way to ensure the status of the request.

    headers = _load_headers()

    response = requests.get(
        f"{GENERATE_IMAGE_URL}/{task_id}",
        headers=headers,
        timeout=timeout
    )
    if response.status_code == 200:
        return response.json()

    print(f"Error checking task status: {response.json()}")
    return None  # Response failed


def _poll_for_gen_rq_task_id(data: dict) -> str | None:
    # Poll for successful generation request
    # If successful, return the task ID, otherwise return None

    while True:
        print("Posting response...")
        headers = _load_headers()

        gen_response = requests.post(
            GENERATE_IMAGE_URL,
            headers=headers,
            data=json.dumps(data),
            timeout=60,
        )
        time.sleep(5)

        # Extract task ID and detail from the response
        task_id = gen_response.json().get("id")
        task_detail = gen_response.json().get("detail")

        # If the request goes through
        if task_id:
            print(
                f"Successful response from {GENERATE_IMAGE_URL}. "
                f"Task ID: {task_id}"
            )
            return task_id

        # If the request fails
        print("Task ID missing in response.\n", gen_response.json())

        if task_detail in ("Invalid token", "Token expired"):
            print("Invalid or expired tokens detected. Updating...")

            # Refresh and store new tokens
            _get_new_auth_token()
            #_get_new_validation_token()

            continue

        print(
            f"Unexpected detail in response: {task_detail}."
            "Generation failed."
        )
        return None


def _poll_for_img_url(task_id: str, retries: int = 3) -> str | None:
    # Poll for generation task successful response.
    # If successful return the image 'final' URL otherwise None

    for _ in range(retries):
        task_status = _check_task_status(task_id, timeout=20)

        if state := task_status.get("state") is None:
            print("Failed to check task status.")
            break

        print(f"Current task status: {task_status.get("state")}")

        # Handle the task's status
        match state := task_status.get("state"):
            case "completed":
                image_url = task_status.get("result", {}).get("final")
                if image_url:
                    return image_url
                print("No 'final' URL in the response.")
                break
            case "failed":
                print("Task failed.")
                break
            case "pending":
                print("Task is still pending. Waiting...")
            case _:
                print(f"Unknown state: {state}")
                break

        # Wait for a while before checking again
        time.sleep(3)
    return None


def generate_image(prompt: str, style_id: ArtStyle, retries: int = 3
                   ) -> Image.Image | None:
    """Returns a PIL Image based on a given prompt via Dream AI."""

    data = {
        "is_premium": False,
        "input_spec": {
            "aspect_ratio": "old_vertical_ratio",
            "display_freq": 10,
            "prompt": prompt,
            "style": style_id.value
        }
    }

    gen_request_id = _poll_for_gen_rq_task_id(
        data=data
    )

    if gen_request_id is None:
        return None

    image_url = _poll_for_img_url(
        gen_request_id,
        retries=retries
    )

    if image_url is None:
        print(f"Failed to retreive image after {retries} tries.")
        return None

    # Try to download image from 'final' URL
    try:
        print(f"Getting image at url {image_url}")
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except requests.exceptions.RequestException as req_err:
        print(f"Failed to download image: {req_err}")
        return None

    # Try to open the image and return PIL Image
    try:
        pil_image = Image.open(BytesIO(response.content))
        return pil_image
    except (IOError, ValueError) as img_err:
        print(f"Failed to open image: {img_err}")
        return None
