"""
Handles image processing.
Functions to threshold and filter image contours from an AI-generated image.
"""

import math
import cv2
import numpy as np
from scipy.interpolate import splprep, splev
from scipy.spatial import distance

from src.rpi.backend.ik.ik import get_real_angles, deg_to_steps


# Wide is used for high contrast, narrow is for low contrast
EDGE_DET_THRESH_WIDE = (100, 200)
EDGE_DET_THRESH_NARROW = (120, 130)

# Wide is used for low detail narrow is for high detail
LINSCAPE_THRESH_WIDE = (0.0, 1.0)
LINSCAPE_THRESH_NARROW = (0.05, 0.95)

# First tuple value is to be used for low detail, second is for high detail
MIN_CONT_PTS_IGNORE_RANGE = (2, 12)
MIN_CONT_PTS_SMOOTH_RANGE = (70, 30)
EPSILON_RANGE = (0.05, 0.5)
SMOOTHNESS_RANGE = (10, 90)


def calculate_image_new_dimen(cv_img, arm_max_length) -> tuple[int, int]:
    """Returns the new width and height for an image given an arm maximum
    extension. This is the optimal image area within the arm's semicirclular
    arc while maintaining the image's aspect ratio. The aspect ratio is
    fixed by the Dream AI free plan, so we must compromise."""
    img_h, img_w = cv_img.shape[:2]  # Height first, then width
    new_w, new_h = map(int, _max_rect_from_semi(img_w, img_h, arm_max_length))
    return new_w, new_h


def extract_contours(
        opencv_image,
        arm_max_length,
        initial_detail_level: float | None = None):
    """Filter image and extract simplified and smooth contours using RDP and
    B-splines."""

    # Calculate image contrast
    constrast = _normalized_histogram_contrast(opencv_image)

    # Convert the image to grayscale
    img = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)

    # First rotation (make landscape) for optimal semicircle coverage
    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Resize image based on arm_max_length
    img = cv2.resize(img, calculate_image_new_dimen(img, arm_max_length))

    # This second rotation compensates for the screen Y coord corresponding to
    # the arm's X coord. IMPORTANT!!!
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    # Edge detection
    edge_det_threshold = _interpolate_threshold(
        EDGE_DET_THRESH_NARROW,
        EDGE_DET_THRESH_WIDE,
        k=constrast
    )
    edges = cv2.Canny(img, *edge_det_threshold)

    # Compute detail level (between 0 and 1)
    if initial_detail_level is None:
        detail_level = calculate_image_detail_level(
            edges,
            min_variance=1_000,
            max_variance=50_000
        )
    elif not 0 <= initial_detail_level <= 1:
        detail_level: float = np.clip(initial_detail_level, 0, 1)
    else:
        detail_level = initial_detail_level

    min_cont_points_ignore = _interpolate_value(
        MIN_CONT_PTS_IGNORE_RANGE,
        k=detail_level,
    )
    min_cont_points_smooth = _interpolate_value(
        MIN_CONT_PTS_SMOOTH_RANGE,
        k=detail_level,
    )
    linscape_threshold = _interpolate_threshold(
        LINSCAPE_THRESH_NARROW,
        LINSCAPE_THRESH_WIDE,
        k=detail_level
    )
    epsilon = _interpolate_value(EPSILON_RANGE, k=detail_level)
    smoothness = _interpolate_value(SMOOTHNESS_RANGE, k=detail_level)

    # Find contours
    contours, _ = cv2.findContours(
        image=edges,
        mode=cv2.RETR_EXTERNAL,
        method=cv2.CHAIN_APPROX_SIMPLE
    )

    # Debug
    print(f"Contours extracted. Contour count: {len(contours)}")
    print(f'''
        {constrast=}
        {min_cont_points_ignore=}
        {min_cont_points_smooth=}
        {linscape_threshold=}
        {epsilon=}
        {smoothness=}
        {detail_level=}
    ''')

    return _get_smoothed_contours(
        contours,
        int(min_cont_points_ignore),
        int(min_cont_points_smooth),
        linscape_threshold,
        epsilon,
        smoothness
    )


def sort_contours(contours):
    """Sort contours to minimize pen travel (greedy nearest neighbor)."""
    if not contours:
        return []

    sorted_contours = [contours.pop(0)]  # Start with first contour
    contour_index = 0

    while contours:
        last_point = sorted_contours[-1][-1]  # Last point of last contour
        # Find the closest next contour
        next_index = min(
            range(len(contours)),
            key=lambda i: distance.euclidean(last_point, contours[i][0])
        )
        sorted_contours.append(contours.pop(next_index))
        contour_index += 1

    return sorted_contours


def save_motor_angles(
        contours,
        base, arm1, arm2, offset, pen_up_offset,
        output_file="output.motctl",
        scale=1.0) -> None:
    """
    Converts contours to motor angles to be interpreted by the robot arm's
    firmware.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        chunks = []
        chunk_lines = []
        for contour_index, contour in enumerate(contours):
            # Each chunk is ~10k characters
            for point_index, point in enumerate(contour):
                # When reading the first point of the contour, we must put
                # the pen up first before moving it into position
                is_pen_up = bool(point_index == 0)

                px = (point[0] + offset[0]) * scale
                py = (point[1] + offset[1]) * scale
                pz = (offset[2] + (pen_up_offset if is_pen_up else 0)) * scale

                angles = get_real_angles(px, py, pz, base, arm1, arm2)
                if angles:
                    print(angles["y"])
                    ax = deg_to_steps(angles["x"])
                    ay = deg_to_steps(angles["y"])
                    az = deg_to_steps(angles["z"])
                    aa = deg_to_steps(angles["a"])
                    line = f"@{ax} {ay} {az} {aa}"
                else:
                    line = "NO ANGLES"

                # If we exceed 10k characters or we're on the last line
                char_count = len("\n".join(chunk_lines))

                """
                print(contour_index == len(contours) - 1)
                print(point_index == len(contour) - 1)
                """

                if (char_count + len(line) > 10_000
                        or (contour_index == len(contours) - 1
                            and point_index == len(contour) - 1)):
                    # Mark memory, start, end
                    chunk_lines.insert(0, "START CHUNK")
                    chunk_lines.append("END CHUNK$")

                    mem_value = len("\n".join(chunk_lines)) + 1
                    chunk_lines.insert(0, f"&{mem_value}")

                    # Add current chunk lines buffer to the list of chunks
                    chunks.append(chunk_lines.copy())

                    print(chunk_lines)
                    print(chunks)

                    # Reset the buffer for the current line
                    chunk_lines.clear()
                else:
                    chunk_lines.append(line)

        all_lines = [line + "\n" for chunk in chunks for line in chunk]
        f.writelines(all_lines)


def extract_and_refine_contour_count(
        cv_image,
        detail_level_adaptation_step: float,
        min_contour_count: int,
        max_contour_count: int,
        arm_max_length):
    """
    Iteratively adapt the contour detail and recalculate contours if the
    resultant contour count is too high or too low.
    """

    detail_level = calculate_image_detail_level(cv_image, 1_000, 50_000)

    while True:
        contours = extract_contours(
            cv_image,
            arm_max_length=arm_max_length,
            initial_detail_level=detail_level
        )
        new_detail_level = detail_level
        if len(contours) > max_contour_count:
            new_detail_level -= detail_level_adaptation_step
        elif len(contours) < min_contour_count:
            new_detail_level += detail_level_adaptation_step

        # If the countour count is within bounds or if the detail is at
        # an extremity, then do not recalculate contours as we cannot
        # further tweak the detail level.
        if new_detail_level == detail_level or not 0 <= new_detail_level >= 1:
            break

        # Update to the new detail level and recalculate contours
        # in the next loop iteration
        detail_level = new_detail_level
        print(f"Number of countours is out of bounds: {len(contours)}.\n"
              f"Refining with new detail level: {detail_level:.2f}")

    return contours


def calculate_image_detail_level(
        cv_image,
        min_variance=0,
        max_variance=50_000) -> float:
    """Get the detail level of a given image by calculating
    laplacian variance. Max ~50,000"""
    laplacian = cv2.Laplacian(cv_image, cv2.CV_64F)
    variance = laplacian.var()
    print(f"Variance: {variance}")

    # Normalize the variance between 0 and 1
    normalized_var = (variance - min_variance) / (max_variance - min_variance)

    # Clamp the value to the range [0, 1]
    normalized_var = np.clip(normalized_var, 0, 1)
    return normalized_var


def _max_rect_from_semi(
        width: float,
        height: float,
        radius: float) -> tuple[float, float]:
    # Calculates the new width and height required to fit a semicircle of
    # given radius while maintaining aspect ratio.
    w = radius / math.sqrt((height / width) ** 2 + (1 / 4))
    h = math.sqrt(radius ** 2 - (w ** 2) / 4)
    return w, h


def _perpendicular_distance(point, line_start, line_end):
    # Function for calculating the perpendicular distance from a
    # point to a line.
    line_start = np.array(line_start)
    line_end = np.array(line_end)
    point = np.array(point)

    num = abs(
        (line_end[1] - line_start[1]) * point[0]
        - (line_end[0] - line_start[0]) * point[1]
        + line_end[0] * line_start[1]
        - line_end[1] * line_start[0]
    )

    den = np.sqrt(
        (line_end[1] - line_start[1]) ** 2
        + (line_end[0] - line_start[0]) ** 2
    )

    return num / den if den != 0 else 0  # Avoid division by zero


def _rdp(points, epsilon=1.0):
    # Simplify contour using the Ramer-Douglas-Peucker algorithm.
    if len(points) < 3:  # No need to simplify if there are only two points
        return points

    def rdp_recursive(points, epsilon):
        if len(points) < 3:
            return points

        distances = [
            _perpendicular_distance(point, points[0], points[-1])
            for point in points[1:-1]
        ]
        max_distance = max(distances, default=0)  # Get max distance safely
        index = distances.index(max_distance) + 1  # Shift index due to slicing

        if max_distance > epsilon:
            left = rdp_recursive(points[:index + 1], epsilon)
            right = rdp_recursive(points[index:], epsilon)
            return left[:-1] + right
        return [points[0], points[-1]]

    return np.array(rdp_recursive(list(points), epsilon))


def _interpolate_threshold(
        t_narrow: tuple[float, float],
        t_wide: tuple[float, float],
        k: float,
        as_int: bool = False):
    # Get a new threshold value given a scalar multiple (k) between 0 and 1.
    # The closer to 1, the closer to the wide threshold.
    k = max(0.0, min(1.0, k))  # Clamp k to [0, 1]
    t_new_min = t_wide[0] + k * (t_narrow[0] - t_wide[0])
    t_new_max = t_wide[1] + k * (t_narrow[1] - t_wide[1])

    if as_int:
        return (int(t_new_min), int(t_new_max))
    return (t_new_min, t_new_max)


def _interpolate_value(
        threshold: tuple[float, float],
        k: float):
    # Returns the value interpolated within the threshold given a
    # scalar multiple (k) between 0 and 1.
    k = max(0.0, min(1.0, k))  # Clamp k to [0, 1]
    return threshold[0] + (threshold[1] - threshold[0]) * k


def _calculate_smooth_pwr(contour):
    # Calculates the smoothing exponent.
    # Returns 1 if mostly straight, 3 if curvy.

    if len(contour) < 5:
        return 1  # Too small, assume linear

    # Measure linearity (RDP simplification)
    simplified_contour = _rdp(contour, epsilon=2.0)
    original_length = np.sum(np.linalg.norm(np.diff(contour, axis=0), axis=1))
    simplified_length = np.sum(
        np.linalg.norm(np.diff(simplified_contour, axis=0), axis=1)
    )

    # Closer to 1 = More straight
    linearity_score = simplified_length / original_length

    # Measure curvature
    x = np.linspace(0, 1, len(contour))
    y = contour[:, 1]
    poly_coeffs = np.polyfit(x, y, 2)  # Quadratic fit (ax^2 + bx + c)
    curvature = abs(poly_coeffs[0])  # The 'a' coeff represents curve strength

    if linearity_score > 0.95 and curvature < 0.005:
        return 1  # Mostly straight, use linear smoothing
    return 3  # Mostly curved, use cubic smoothing


def _dedupe_contour(contour):
    """Remove duplicate points from a (n, 2) contour array."""
    # Use np.unique with axis=0 to remove duplicate rows
    _, idx = np.unique(contour, axis=0, return_index=True)
    return contour[np.sort(idx)]


def _get_smoothed_contours(
        contours,
        min_cont_points_ignore: int,
        min_cont_points_smooth: int,
        linscape_threshold: tuple[float, float],
        epsilon: float,
        smoothness: float):

    smoothed_contours = []
    for contour in contours:
        # Flatten the contour into a 2D array (n, 2)
        contour = contour.squeeze()

        if len(contour) <= min_cont_points_ignore:
            continue  # Ignore small contours

        # Simplify the contour using RDP
        simplified_contour = _rdp(contour, epsilon=epsilon)

        # Smoothing exponent is either 1 or 3. Linear for straighter contours,
        # cubic for curvier contours.
        smooth_pwr = _calculate_smooth_pwr(contour)

        # Apply B-spline for smoothing if the contour has enough points
        if len(simplified_contour) >= min_cont_points_smooth:
            # Calculate splines (k=power for smoothing)
            tck = splprep(simplified_contour.T, s=smoothness, k=smooth_pwr)[0]
            smooth_contour = np.array(
                splev(
                    np.linspace(*linscape_threshold, len(simplified_contour)),
                    tck
                )
            ).T
            smooth_contour = _dedupe_contour(smooth_contour)
            smoothed_contours.append(smooth_contour)
        else:
            smoothed_contours.append(simplified_contour)

    return smoothed_contours


def _normalized_histogram_contrast(cv_image) -> float:
    # Calculate and return a contrast value between 0 and 1 using
    # histogram method.
    hist = cv2.calcHist([cv_image], [0], None, [256], [0, 256])
    hist_norm = hist.ravel() / hist.sum()

    entropy = -np.sum(hist_norm * np.log2(hist_norm + 1e-7))  # Shannon entropy
    contrast_normalized = entropy / 8  # Max entropy for 8-bit images is 8

    return contrast_normalized
