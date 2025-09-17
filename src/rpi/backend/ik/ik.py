"""
Inverse kinematics mathematics for a 2-DOF robotic arm.

Contains a function to show the graphed visualisation of the arm given
a desired target point.

Sources: https://github.com/vishwas1101/Inverse-Kinematic-Robot-Arm/blob/
        master/InverseKinematics/IK_Simulation.py
"""

import math
import matplotlib.pyplot as plt


#  pylint: disable=too-many-locals
def _get_point(x, y, z, base, arm1, arm2, alpha):
    """Calculate the intermediate joint position of the robotic arm."""
    e = (x**2 + y**2 + z**2 - base**2 + arm1**2 - arm2**2) / 2

    if x == 0 and y == 0:
        return 0, 0, base  # Default values for edge case

    tan_alpha = math.tan(math.radians(alpha))
    denom = (x + y * tan_alpha) ** 2
    a1 = (((z - base) ** 2) * (1 + tan_alpha ** 2)) / denom + 1
    b1 = 2 * ((e * (z - base) * (1 + tan_alpha ** 2)) / denom + base)
    c1 = (e ** 2) * (1 + tan_alpha ** 2) / denom + base ** 2 - arm1 ** 2

    discriminant = b1 ** 2 - 4 * a1 * c1
    if discriminant < 0:
        return None  # No real solution

    c = (b1 + math.sqrt(discriminant)) / (2 * a1)
    a = (e - c * (z - base)) / (x + y * tan_alpha)
    b = a * tan_alpha

    return a, b, c


def get_nearest_valid_point(x, y, z, base, arm1, arm2):
    """Returns the coordinates of the nearest point within the sphere
    defined by the arm lengths. If the point is already within the sphere
    the original point is returned."""
    if check_point_in_bounds(x, y, z, base, arm1, arm2):
        return x, y, z

    radius = arm1 + arm2
    dx, dy, dz = x, y, z - base
    length = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

    # Handle exact center point
    if length == 0:
        return (0, 0, base + radius)

    # Calculate unit vector
    dx /= length
    dy /= length
    dz /= length

    # Scale direction by radius
    nearest_x = dx * radius
    nearest_y = dy * radius
    nearest_z = dz * radius + base

    return (nearest_x, nearest_y, nearest_z)


def check_point_in_bounds(x, y, z, base, arm1, arm2) -> bool:
    """Check whether a point can be reached by the arm given the
    configuration."""
    radius = arm1 + arm2
    distance = math.sqrt(x ** 2 + y ** 2 + (z - base) ** 2)
    return distance <= radius


def get_ik_angles(x, y, z, base, arm1, arm2):
    """Calculate joint angles (base angle, angle of arm 1, angle of arm 2)
    required to reach the target point."""
    d = math.sqrt(x**2 + y**2 + (z - base) ** 2)

    if d > arm1 + arm2:
        return None  # Target out of reach

    alpha = math.degrees(math.atan2(y, x))
    theta1 = math.asin((z - base) / d)
    theta2 = math.acos((arm1**2 + d**2 - arm2**2) / (2 * arm1 * d))
    beta = math.degrees(theta1 + theta2)
    gamma = math.degrees(
        math.acos((arm1**2 + arm2**2 - d**2) / (2 * arm1 * arm2))
    )

    # Base angle, angle of arm 1, angle of arm 2
    return alpha, beta, gamma


def get_real_angles(px, py, pz, base, arm1, arm2,
                    decimals=2) -> dict[str, float] | None:
    """Takes in points for X, Y, Z and returns the angles for the motors on
    the robotic arm. Adjusts for relevant offsets in real life and returns
    a dictionary of the form X, Y, Z, A."""
    ik_angles = get_ik_angles(px, py, pz, base, arm1, arm2)

    # Return None if the angles are invalid
    if ik_angles is None:
        return None

    ang_base, ang_arm1, ang_arm2 = ik_angles

    # Minor corrections to y because IDFK
    y = ang_base - 180
    if y <= -180:
        y = -(y + 360)

    return {
        "x": round(ang_arm2 - 180, decimals),
        "y": round(y, decimals),
        "z": round(-ang_arm1 + 90, decimals),
        "a": round(ang_arm2 + ang_arm1 - 270, decimals)
    }


def plot_arm(base, arm1, arm2, x, y, z):
    """Plot the robotic arm configuration."""
    angles = get_ik_angles(x, y, z, base, arm1, arm2)
    if not angles:
        print("The point can't be reached.")
        return

    ang_base, ang_arm1, ang_arm2 = angles

    point = _get_point(x, y, z, base, arm1, arm2, ang_base)
    if point is None:
        raise ValueError(f"Invalid point: {point}")

    joint_x, _, joint_z = point
    if not joint_x:
        print("Invalid joint position.")
        return

    print(f"Angle of Base: {ang_base:.2f}°")
    print(f"Angle of Arm1: {ang_arm1:.2f}°")
    print(f"Angle of Arm2: {ang_arm2:.2f}°")

    vec_x = [0, 0, joint_x, x]
    vec_z = [0, base, joint_z, z]

    plt.figure(figsize=(6, 6))
    plt.plot(vec_x, vec_z, marker='o', linestyle='-', color='b', markersize=8)
    plt.xlim(-max(arm1 + arm2, abs(x)), max(arm1 + arm2, abs(x)))
    plt.ylim(0, max(arm1 + arm2, abs(z) + base))
    plt.xlabel("X-Axis")
    plt.ylabel("Z-Axis")
    plt.title("Robotic Arm Configuration")
    plt.grid()
    plt.show()


def deg_to_steps(
        angle: float,
        steps_per_rev: float = 200,
        gear_ratio: float = 256.0 / 9.0) -> int:
    """Converts degrees to NEMA 17 motor steps."""
    deg_per_step = 360.0 / steps_per_rev
    return round((angle / deg_per_step) * gear_ratio)


def steps_to_deg(
        steps: int,
        steps_per_rev: float = 200,
        gear_ratio: float = 256.0 / 9.0) -> float:
    """Converts NEMA 17 motor steps to degrees."""
    deg_per_step = 360.0 / steps_per_rev
    return steps * deg_per_step / gear_ratio

