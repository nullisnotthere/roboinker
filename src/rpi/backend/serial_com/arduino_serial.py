from functools import partial
from typing import Callable, Mapping

import os
import time
import threading
from dotenv import load_dotenv

import serial

from src.rpi.backend.ik.ik import deg_to_steps


load_dotenv()

SERIAL_PORT = os.getenv("ARDUINO_PORT")
if SERIAL_PORT is None:
    raise RuntimeError("Missing required environment variable: "
                       "ARDUINO_PORT")

# Some ugly ahh .env validation
try:
    BAUDRATE = os.getenv("ARDUINO_BAUDRATE")
    if BAUDRATE is None:
        raise RuntimeError("Missing required environment variable: "
                           "ARDUINO_BAUDRATE")
    BAUDRATE = int(BAUDRATE)
except ValueError as exc:
    raise ValueError("Invalid required environment variable: "
                     "ARDUINO_BAUDRATE (must be of type 'int')") from exc


class ArduinoSerial:
    """Class to encapsulate Arduino serial connection handling."""
    AXES = ("x", "y", "z", "a")
    MAX_SPEED = 300  # Steps/sec

    def __init__(self, port: str = SERIAL_PORT, baudrate: int = BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self._target_responses: list = []
        self._allow_thread_loops = True
        self._thread: threading.Thread | None = None

        try:
            self.arduino_ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1
            )
            time.sleep(2)  # Wait for Arduino to initialise
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self.arduino_ser = None

    def is_listening(self) -> bool:
        """Check if the Arduino is currently listening to something or not."""
        return len(self._target_responses) > 0

    def start_listening_for(self,
                            response_map: Mapping[str, Callable | None],
                            default_callback: Callable | None = None):
        """
        Start listening for given responses in a separate thread.
        When a response in the response map is received, its corresponding
        callback is executed. Use '*' as response key to handle any response.
        """
        print("Listening? ", self.is_listening())
        if self.is_listening():
            print("Can not start listening. Already listening for: "
                  f"{','.join(self._target_responses)}")
            return

        print(f"Arduino is now listening for: {response_map.keys()}")
        target_partial = partial(self._listen_serial, response_map)
        self._thread = threading.Thread(target=target_partial, daemon=True)
        self._thread.start()

    def _listen_serial(self, response_map: Mapping[str, Callable | None]):
        # Listens for a response in the response map, calls relevant callback
        # when received.
        self._target_responses = list(response_map.keys())

        if not self._allow_thread_loops:
            print("Warning: A serial connected was closed. "
                  "Thread looping has been prevented.")

        while self._allow_thread_loops:
            time.sleep(2)
            response = self.arduino_ser.readline().decode().strip()
            response_received = False

            # Catching unhandled responses
            if response not in response_map.keys():
                if response:
                    print(f"Received unhandled response: '{response}'")
                # Maybe dont give up if we receive an unhandled response?
                #self._target_responses.clear()
                #return

            for target, callback in response_map.items():
                if not response:
                    continue

                # '*' means any response
                if target == "*":
                    response_received = True

                # If the received response is the targetted response
                elif response == target:
                    response_received = True

                if not response_received:
                    continue

                print(f"!!!Received response: '{response}'!!!")
                print(f"\tTarget response: '{target}'")
                print(f"\tExecuting callback '{callback.__name__}'")
                self._target_responses.clear()
                if callable(callback):  # Can be 'None'
                    callback()
                return
            '''
            print("No valid response received from Arduino. "
                  f"listening for: '{",".join(self._target_responses.keys())}'")
            '''

    def _parse_last_response(self, silent=False) -> str | None:
        # Read the last line of Arduino's Serial output.
        # silent determines whether or not this method prints the output to
        # the console.
        full_response = self.arduino_ser.readline().decode().strip()
        if not silent:
            print(f"Full response from Arduino: {full_response}")

        # Split and validate response
        split_response = full_response.split("#")
        if len(split_response) > 2:  # Must have two '#'s
            response_data = split_response[1]
            return response_data

        if not silent:
            print("Arduino's response was invalid. "
                  "May contain less than two #'s.")
        return None

    def request_angles(self) -> str | None:
        """Request the angle data from the Arduino."""
        return self.send_data("READ ANGLES")

    def print_response(self):
        """Prints last Arduino response."""
        full_response = self.arduino_ser.readline().decode().strip()
        print(f"Unhandled response from Arduino: '{full_response}'")

    def send_data(self,
                  data,
                  response_map: Mapping[str, Callable] | None = None
                  ) -> str | None:
        return
        """
        Sends raw string MOTCTL formatted data to Arduino via serial.
        Pass a response map to handle certain responses from the Arduino.
        """
        if not (self.arduino_ser and self.arduino_ser.is_open):
            print("Error sending Serial data to Arduino.")

        self.start_listening_for(response_map if response_map else {})

        # Ensure last line delimeter is present!!!
        if len(data) > 0 and data[-1] != "\n":
            data += "\n"

        # Send data
        print(f"Sending data: '{data}'")
        time.sleep(2)
        self.arduino_ser.write(data.encode())

    def send_angles(self, angles_data: dict[str, float], invert=False):
        """Sends the stored motor angles to the Arduino."""
        direction = -1 if invert else 1
        x = deg_to_steps(angles_data["x"] * direction)
        y = deg_to_steps(angles_data["y"] * direction)
        z = deg_to_steps(angles_data["z"] * direction)
        a = deg_to_steps(angles_data["a"] * direction)

        cmd = f"^@{x} {y} {z} {a}"
        print(f"sending angles cmd: {cmd}")

        self.send_data(cmd)

    def close_serial(self):
        """Close serial connection on exit."""
        self._allow_thread_loops = False  # Stop the thread loops cleanly
        if self.serial:
            self.serial.close()

