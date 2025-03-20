#!/usr/bin/env python3

"""
This API Wrapper interacts with 'Dream by WOMBO' to generate images from the
web and retreive them as OpenCV images.

Sources:
https://github.com/krisskad/DreamAI
https://dream.ai/create
"""

from dataclasses import dataclass
from enum import Enum

import os
import time
import json
import requests
from requests.exceptions import ReadTimeout, ConnectTimeout
import numpy as np
import cv2
import fake_useragent
from cv2.typing import MatLike
from dotenv import load_dotenv, set_key
from .art_styles import ArtStyle


load_dotenv()

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

HEADERS_FILE = os.path.join(MODULE_DIR, "headers.json")  # Headers template
DOT_ENV_PATH = os.path.join(MODULE_DIR, ".env")

DREAM_LOGIN_URL = "https://dream.ai/profile"
SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/"
GENERATE_IMAGE_URL = "https://paint.api.wombo.ai/api/v2/tasks"


class ResponseStatus(Enum):
    """Enum to declare different response statuses. One of these
    will be included in the final image response."""
    FAILURE = 0
    SUCCESS = 1
    NSFW = 2


@dataclass
class ImageResponse:
    """Dataclass to encapsulate the image returned by the response
    and the response status and message from the generation. This
    will be returned after the request and generation processes."""
    cv_image: MatLike | None
    status: ResponseStatus
    message: str


def _get_new_auth_token() -> str | None:
    # Function to refresh the authorization token via web requests to dream.ai

    api_key = os.getenv("DREAM_AI_API_KEY")
    refresh_url = f"{SIGN_IN_URL}accounts:signInWithPassword?key={api_key}"

    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "email": os.getenv("DREAM_AI_EMAIL"),
        "password": os.getenv("DREAM_AI_PASSWORD"),
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
            os.environ["DREAM_AI_AUTH_TOKEN"] = new_auth_token
            set_key(DOT_ENV_PATH, "DREAM_AI_AUTH_TOKEN", new_auth_token)

            return new_auth_token

    print(
        "Failed to retrieve auth token."
        f"Status code: {response.status_code}."
        f"Response: {response.text}"
    )

    return None


def _load_headers() -> dict[str, str]:
    # Retreive the headers from headers.json and fill in the sensitive
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

    # Update with sensitive auth data from .env
    auth_token = os.getenv("DREAM_AI_AUTH_TOKEN")

    if not auth_token:
        raise ValueError("Missing required environment variables.")

    # Create random, fake user agent to store in header
    user_agent: str = fake_useragent.UserAgent().random
    headers.update(
        {
            "User-Agent": f"{user_agent}",
            "Authorization": f"bearer {auth_token}"
        }
    )
    return headers


def _check_task_status(task_id: str, timeout: float) -> dict | None:
    # Checks if the current request is complete
    # This is used when generating the image. We do not know how long it will
    # take to finish generation, so we must have a way to ensure the status
    # of the request.

    headers = _load_headers()

    try:
        response = requests.get(
            f"{GENERATE_IMAGE_URL}/{task_id}",
            headers=headers,
            timeout=timeout
        )
        if response.status_code == 200:
            return response.json()
    except (
            ConnectionError,
            ReadTimeout,
            ConnectTimeout,
            requests.exceptions.ConnectionError) as req_err:
        # Returns None on failure to connect or time out
        print(
            f"Task status check failed at '{GENERATE_IMAGE_URL}'\n"
            f"{req_err}"
        )
        return None

    print(f"Error checking task status: {response.json()}")
    return None  # Response failed


def _poll_for_gen_rq_task_id(data: dict, retries: int = 3) -> str | None:
    # Poll for successful generation request
    # If successful, return the task ID, otherwise return None

    for _ in range(retries):
        print("Posting response...")
        headers = _load_headers()

        try:
            gen_response = requests.post(
                GENERATE_IMAGE_URL,
                headers=headers,
                data=json.dumps(data),
                timeout=30,
            )
            time.sleep(5)
        except (
                ConnectionError,
                ReadTimeout,
                ConnectTimeout,
                requests.exceptions.ConnectionError) as req_err:
            # Returns None on failure to connect or time out
            print(
                f"Generation response failed at '{GENERATE_IMAGE_URL}'\n"
                f"{req_err}"
            )
            return None

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
            print("Invalid or expired token detected. Updating...")

            # Refresh and store new token
            _get_new_auth_token()
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
        task_status = _check_task_status(task_id, timeout=30)

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
                   ) -> ImageResponse:
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
        return ImageResponse(
            None,
            ResponseStatus.FAILURE,
            "Could not retreive generation request task ID. Null ID."
        )
    if gen_request_id == "00000000-0000-0000-0000-000000000000":
        return ImageResponse(
            None,
            ResponseStatus.NSFW,
            "Could not generate possibly NSFW content."
        )

    image_url = _poll_for_img_url(
        gen_request_id,
        retries=retries
    )

    if image_url is None:
        return ImageResponse(
            None,
            ResponseStatus.FAILURE,
            f"Failed to retreive image after {retries} tries."
        )

    # Try to download image from final URL
    try:
        print(f"Getting image at url {image_url}")
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except requests.exceptions.RequestException as req_err:
        return ImageResponse(
            None,
            ResponseStatus.FAILURE,
            f"Failed to download image: {req_err}"
        )

    # Try to open the image and return OpenCV image
    try:
        image_bytes = np.frombuffer(response.content, np.uint8)
        cv_image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        return ImageResponse(
            cv_image,
            ResponseStatus.SUCCESS,
            "Successfully retreived image data."
        )
    except (IOError, ValueError) as img_err:
        print(f"Failed to open image: {img_err}")
        return ImageResponse(
            None,
            ResponseStatus.FAILURE,
            f"Failed to convert response content to OpenCV image. {img_err}"
        )
