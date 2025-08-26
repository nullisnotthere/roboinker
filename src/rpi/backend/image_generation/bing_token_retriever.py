#!/usr/bin/env python3


import time
import random
import os
import json
from json.decoder import JSONDecodeError
import requests

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException,
                                        NoSuchWindowException,
                                        WebDriverException,
                                        StaleElementReferenceException)
from fake_useragent import UserAgent


# Ensure Bing username and password are set in .env
EMAIL = os.getenv("BING_EMAIL")
if EMAIL is None:
    raise RuntimeError("Missing required environment variable: BING_EMAIL")

USERNAME = os.getenv("BING_USERNAME")
if USERNAME is None:
    raise RuntimeError("Missing required environment variable: BING_USERNAME")

PASSWORD = os.getenv("BING_PASSWORD")
if PASSWORD is None:
    raise RuntimeError("Missing required environment variable: BING_PASSWORD")


LOGIN_URL = (
    "https://login.live.com/"
)
SPAWN_TOKEN_URL = (
    "https://www.bing.com/fd/auth/signin?action=interactive&provider="
    "windows_live_id&return_url=https%3a%2f%2fwww.bing.com%2fimages%2fcreate"
    "%3fcsude%3d1%26caption%3d%25QUERY%25&cobrandid=03f1ec5e-1843-43e5-a2f6-"
    "e60ab27f6b91&noaadredir=1&FORM=GENUS1"
)
AI_CREATE_URL = "https://www.bing.com/images/create?"

TOKEN_FILE = "src/rpi/backend/image_generation/bing_token.json"

ELEMENTS = {
    "username": '//*[@id="usernameEntry"]',
    "email": '//*[@id="i0116"]',
    "password": '//*[@id="passwordEntry"]',
    "other_ways_to_sign_in": '/html/body/div[1]/div/div/div/div/div[1]/div/div/div/div/div[2]/div/span/div/span',
    "skip_for_now": '/html/body/div[2]/div/div/div/div/div[1]/div/form[2]/div[2]/div/div[2]/div/h1',
    "create_image_entry": '//*[@id="sb_form_q"]',
}


def _rand_sleep(low, high):
    """Sleep for a random amount of time between low and high"""
    time.sleep(random.uniform(low, high))


def _submit_to_entry(entry, key_string, sleep_low=1, sleep_high=2):
    """Sends a string of keys followed by a random sleep between low and high,
    then sends ENTER key."""
    entry.clear()
    entry.send_keys(key_string)
    _rand_sleep(sleep_low, sleep_high)
    entry.send_keys(Keys.ENTER)


def _send_key_to_page(driver, wait, key, repeat=1,
                      time_btw_min=.7, time_btw_max=1.3):
    """Sends ESC followed by TAB followed by ENTER. Number of TABS can be
    changed with tab_count param. This essentially acts as an element selector
    on the page."""
    _rand_sleep(time_btw_min, time_btw_max)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    body = driver.find_element(By.TAG_NAME, "body")

    for _ in range(repeat):
        body.send_keys(key)


def _try_find_element(driver, *xpaths) -> WebElement | None:
    # Tries to find any element given various xpaths. Returns the first hit.
    try:
        for xpath in xpaths:
            element = driver.find_element(By.XPATH, xpath)
            if element is not None:
                return element
        return None
    except NoSuchElementException:
        return None


def _retrieve_new_cookie() -> str | None:
    # Gets a new token from Microsoft by emulating a browser and
    # reading the cookies. I checked TOS this is all good :)
    print("Getting new token cookie...")

    # Create fake user agent and add to Firefox profile
    ua = UserAgent()
    user_agent = ua.random
    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", user_agent)
    profile.set_preference("dom.disable_beforeunload", True)

    # Add profile to options and specify headless browsing mode
    options = Options()
    options.profile = profile  # Add the profile to the webdriver

    # These options prevent Microsoft's fingerprint popup as its external
    # to the web page and can not be closed with Selenium.
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference(
        "security.insecure_field_warning.contextual.enabled",
        False
    )
    options.set_preference("signon.autofillForms", False)
    options.set_preference("dom.prompt.testing", True)
    options.set_preference("dom.prompt.testing.allow", True)

    # Don't show the browser GUI
    #options.add_argument("--headless")

    # Initialise driver
    driver = webdriver.Firefox(options=options)

    # Initialise waiting for the driver
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(LOGIN_URL)

        for _ in range(10):
            _rand_sleep(1, 2)  # Short sleep for loading and stuff

            # Skip for now button
            if _try_find_element(driver, ELEMENTS.get("skip_for_now")):
                # FIXME: This might not always work. Very hard to test!
                print("Skip for now found")
                _send_key_to_page(driver, wait, Keys.ESCAPE, 1, 2, 3)
                _send_key_to_page(driver, wait, Keys.TAB, 1, 2, 3)
                _send_key_to_page(driver, wait, Keys.ENTER, 3, 2, 3)
                break

            # Username/email
            if (elem := _try_find_element(driver, ELEMENTS.get("username"),
                                          ELEMENTS.get("email"))):
                print("Submitting to username/email entry")
                _submit_to_entry(elem, EMAIL)
                time.sleep(1)
                continue

            # Password
            if elem := _try_find_element(driver, ELEMENTS.get("password")):
                print("Submitting to password entry")
                _submit_to_entry(elem, PASSWORD)
                break

            # Other ways to sign in/Sign in with password
            if elem := _try_find_element(driver, ELEMENTS.get(
                                         "other_ways_to_sign_in")):
                print("Clicking 'other ways to sign in'")
                elem.click()

                # Select the 'sign in by password' option
                _send_key_to_page(driver, wait, Keys.TAB, 1, 1.5, 2.5)
                _send_key_to_page(driver, wait, Keys.ENTER)
                continue

        # Click no to 'stay signed in?' popup
        time.sleep(1)
        _send_key_to_page(driver, wait, Keys.TAB, 2, 1, 2)
        _send_key_to_page(driver, wait, Keys.ENTER)

        # Wait for log in to finish loading
        time.sleep(1)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Go to the end point that actually spawns the _U token
        driver.get(SPAWN_TOKEN_URL)

        # Wait for the end point to finish loading and read the token cookie
        wait.until(EC.presence_of_element_located(
            (By.XPATH, ELEMENTS["create_image_entry"]))
        )
        u_cookie = driver.get_cookie("_U")

    except TimeoutException:
        print("Web driver timed out.")
        return None
    except (NoSuchWindowException, WebDriverException,
            KeyboardInterrupt, StaleElementReferenceException) as e:
        print(f"Error. Web driver closed unexpectedly: {e}")
        return None
    finally:
        driver.quit()  # Quit webdriver

    # Debug output
    if u_cookie is None:
        print("Failed to retreive _U token. No such cookie found.")
        return None

    _save_cookie(u_cookie)  # Save to file

    # Read from the newly saved file
    return get_token(generate_if_invalid=False)


def _save_cookie(cookie) -> None:
    # Write the cookie to the JSON file
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(cookie, f, indent=4)


def _check_token_is_valid(token: str) -> bool:
    """A function to check if a _U cookie's token is valid."""
    ua = UserAgent()
    headers = {"User-Agent": ua.random}
    cookies = {"_U": token}

    response = requests.get(
        "https://www.bing.com/images/create/test/",
        headers=headers,
        cookies=cookies,
        timeout=10
    )

    # If the user name appears in the cookies then the token is valid
    wls = response.cookies.get_dict().get("WLS")
    if not (USERNAME and wls):
        return False
    return USERNAME in wls


def get_token(generate_if_invalid=True) -> str | None:
    """Gets the _U token from the JSON file. If expired, a new one can be
    generated, retreived, saved, and returned."""

    # Read token from JSON file
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        try:
            u_cookie = json.load(f)
        except JSONDecodeError:
            print("Could not decode JSON in token file.")
            if generate_if_invalid:
                return _retrieve_new_cookie()

        token = u_cookie.get("value")
        expiry_epoch = u_cookie.get("expiry")

        # If the JSON data is incomplete
        if (not (token and expiry_epoch)) and generate_if_invalid:
            return _retrieve_new_cookie()

        time_left = expiry_epoch - time.time()

        if generate_if_invalid:
            if time_left <= 0:
                print("_U token expired!")
                return _retrieve_new_cookie()
            if not _check_token_is_valid(token):
                print("_U token is invalid!")
                return _retrieve_new_cookie()

        formatted_time = time.strftime(
            "%d days %H hours %M mins %S sec",
            time.gmtime(time_left)
        )
        print(f"Successfully retreived _U token. Expires in {formatted_time}")

        # Return the _U token
        return token
