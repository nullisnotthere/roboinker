#!/usr/bin/env python3

# pylint: disable=E0611
import sys
import time
import serial
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt6.QtQml import QQmlApplicationEngine

MAIN_QML_PATH = "src/rpi/frontend/main.qml"


# pylint: disable=too-few-public-methods
class Backend(QObject):
    """Handles backend processes of PyQML declarations."""

    AXES = ("x", "y", "z", "a")
    SERIAL_PORT = "/dev/ttyUSB0"
    BAUD_RATE = 9600

    def __init__(self):
        super().__init__()

        # Initialise Arduino serial
        try:
            self.arduino_ser = serial.Serial(
                self.SERIAL_PORT,
                self.BAUD_RATE,
                timeout=1
            )
            time.sleep(2)  # Wait for Arduino to initialise
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self.arduino_ser = None
        self.motor_speeds: dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0}

    @pyqtSlot(str, float)
    def update_axis(self, axis: str, speed: float):
        """Method to handle UI axis slider updates."""

        self.motor_speeds[axis] = speed
        print(f"Axis {axis.upper()} speed changed to {speed:.2f}")

    @pyqtSlot()
    def send_serial(self):
        """Send the updated motor values to the Arduino via Serial port."""
        if self.arduino_ser and self.arduino_ser.is_open:
            data = "SET SPEEDS$"
            data += "".join([
                f"{axis}:{speed}," for axis, speed in self.motor_speeds.items()
            ]) + "\n"
            self.arduino_ser.write(data.encode())  # Send data
            time.sleep(0.1)  # Short delay before reading response

            # Read response
            response = self.arduino_ser.readline().decode().strip()
            print(f"Response: {response}")
        else:
            print("Error sending Serial data to Arduino.")

    def close_serial(self):
        """Close serial connection on exit."""
        if self.serial:
            self.serial.close()

    @pyqtSlot()
    def stop_all_motors(self):
        """Sets all motors' speeds to zero."""
        for axis in self.AXES:
            self.update_axis(axis, 0)
        self.send_serial()


def main():
    """Main function."""

    # Initialise QML application
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Attach backend processes to frontend QML
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(MAIN_QML_PATH)

    # Exit
    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
