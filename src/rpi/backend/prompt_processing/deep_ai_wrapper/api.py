"""
Source: https://github.com/5eroo/DeepAI-Wrapper
"""

import secrets
import requests
import fake_useragent

from requests_toolbelt.multipart.encoder import MultipartEncoder
from requests.exceptions import ReadTimeout, ConnectTimeout

from .key import get_random_str
from .api_typing import Messages, CompletionsGenerator

# (Thats a funny url. I wonder who'd fall for that)
URL = "https://api.deepai.org/hacking_is_a_serious_crime"


def chat(
        api_key: str,
        messages: Messages) -> CompletionsGenerator:
    """
    This function sends a chat request to the API

    :param api_key: an API key to send in the request.
    :param messages: a list of messages to send.
        Format: [
                    {
                        "role": "<assistant or user>",
                        "content": "<message contents>"
                    },
                    ...
                ] (OpenAI format)

    :return: a generator that yields the response from the API.
             Each response is a string.
    """

    # Make a fake user agent
    user_agent: str = fake_useragent.UserAgent().random
    print(f"Created fake user-agent: {user_agent}")

    # Make a random string
    random_str: str = get_random_str()
    print(f"Created random string: {random_str}")

    # Set up headers
    headers = {
        "Host": "api.deepai.org",
        "User-Agent": f"{user_agent}",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Length": f"{secrets.randbelow(1000)}",
        "Origin": "https://deepai.org",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Cookie": "user_sees_ads=false",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Priority": "u=0",
        "TE": "trailers"
    }

    # cookies (optional, ig)
    cookies = {
        "user_sees_ads": "false"
    }

    # We need to convert the messages to a string for the MultiPartEncoder
    # Refuses to work without double quotes
    _messages_s: str = str(messages).replace("'", '"')

    # Create the MultiPartEncoder object
    _encoder = MultipartEncoder(
        fields={
            "chat_style": "chat",  # This is constant
            "chatHistory": _messages_s,
            "model": "standard"
        }
    )

    # Set headers to fit content type
    # Use api-key if provided
    headers.update(
        {
            "Content-Type": _encoder.content_type,
            "api-key": api_key
        }
    )

    # Send the request
    success = False
    while not success:
        try:
            response = requests.post(
                URL,
                headers=headers,
                cookies=cookies,
                data=_encoder,
                stream=True,
                timeout=45
            )

            # Raise an exception if the status code is not 200
            response.raise_for_status()
            success = True
        except (
                ConnectionError,
                ReadTimeout,
                ConnectTimeout,
                requests.exceptions.ConnectionError) as req_err:

            print(
                f"Deep AI prompt filtering response failed at '{URL}'\n"
                f"{req_err}"
            )

    print(f"Sent request to {URL} with code {response.status_code}")

    # Iterate over the response
    for line in response.iter_lines():
        yield line.decode('utf-8')
