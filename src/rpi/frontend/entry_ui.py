#!/usr/bin/env python3
import tkinter as tk
from functools import partial
from src.rpi.backend.serial_com.arduino_serial import ArduinoSerial


def validate_f(data: str) -> float:
    """Validates string input data as a float."""
    if not data:
        return 0
    try:
        valid_data = float(data)
        return valid_data
    except ValueError:
        return 0


def send_angle_data(
        arduino_ser: ArduinoSerial,
        x_angle_entry,
        y_angle_entry,
        z_angle_entry,
        a_angle_entry):
    """Sends angle data to Arduino"""
    x = validate_f(x_angle_entry.get())
    y = validate_f(y_angle_entry.get())
    z = validate_f(z_angle_entry.get())
    a = validate_f(a_angle_entry.get())

    print(f"Sending angle data: x={x}, y={y}, z={z}, a={a}")

    arduino_ser.update_axis_angle("x", x)
    arduino_ser.update_axis_angle("y", y)
    arduino_ser.update_axis_angle("z", z)
    arduino_ser.update_axis_angle("a", a)
    arduino_ser.send_angles()


def stop_all_motors(arduino_ser: ArduinoSerial):
    """Stops motors"""
    print("Stopping all motors")
    arduino_ser.stop_all_motors()


# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
def main():
    """Main"""
    root = tk.Tk()
    root.title("Motor Control UI")
    root.geometry("600x1024")
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=1)
    root.grid_rowconfigure(3, weight=1)
    root.grid_rowconfigure(4, weight=1)
    root.grid_rowconfigure(5, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    frame = tk.Frame(root)
    frame.pack(expand=True)

    x_angle_label = tk.Label(frame, text="X Angle (negative is left)")
    x_angle_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
    x_angle_entry = tk.Entry(frame)
    x_angle_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

    y_angle_label = tk.Label(frame, text="Y Angle")
    y_angle_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
    y_angle_entry = tk.Entry(frame)
    y_angle_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

    z_angle_label = tk.Label(frame, text="Z Angle")
    z_angle_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)
    z_angle_entry = tk.Entry(frame)
    z_angle_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=5)

    a_angle_label = tk.Label(frame, text="A Angle")
    a_angle_label.grid(row=6, column=0, sticky="w", padx=10, pady=5)
    a_angle_entry = tk.Entry(frame)
    a_angle_entry.grid(row=6, column=1, sticky="ew", padx=10, pady=5)

    # Initialise Arduino Uno serial object
    arduino_ser = ArduinoSerial()

    # Command partials

    send_angle_data_par = partial(
        send_angle_data,
        arduino_ser,
        x_angle_entry,
        y_angle_entry,
        z_angle_entry,
        a_angle_entry,
    )

    stop_all_motors_par = partial(stop_all_motors, arduino_ser)

    # Send data buttons
    send_angle_button = tk.Button(
        root, text="Send Angle Data", command=send_angle_data_par
    )
    send_angle_button.pack(
        anchor="s", pady=10
    )

    stop_button = tk.Button(
        root, text="STOP ALL MOTORS", command=stop_all_motors_par
    )
    stop_button.pack(
        anchor="s", padx=10, pady=10
    )

    root.mainloop()


if __name__ == "__main__":
    main()
