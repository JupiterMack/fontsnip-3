# src/fontsnip/capture/screen_capture.py

"""
Utility module for screen capturing using the 'mss' library.

This module provides a high-performance function to capture a specified
area of the screen and return it as a NumPy array, ready for processing
with OpenCV.
"""

import mss
import numpy as np
from typing import Tuple


def capture_screen_area(bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """
    Captures a specific area of the screen defined by a bounding box.

    Uses the 'mss' library for fast screen grabbing and returns the image
    data as a NumPy array in BGR format, suitable for OpenCV.

    Args:
        bbox: A tuple containing the bounding box coordinates and dimensions
              in the format (x, y, width, height).

    Returns:
        A NumPy array representing the captured image in BGR color format.
        Returns an empty array if the width or height is zero or negative,
        or if the capture fails.
    """
    x, y, w, h = bbox

    # Ensure the bounding box has a valid, positive area.
    if w <= 0 or h <= 0:
        # Return an empty array for an invalid capture area.
        # This can be handled gracefully by downstream processing.
        return np.array([], dtype=np.uint8)

    try:
        # Define the monitor area to capture. mss uses a dictionary format.
        monitor = {"top": y, "left": x, "width": w, "height": h}

        # Use a context manager to handle the mss object, ensuring cleanup.
        with mss.mss() as sct:
            # Grab the data from the screen for the specified monitor area.
            sct_img = sct.grab(monitor)

            # Convert the mss.screenshot.ScreenShot object to a NumPy array.
            # The raw format from mss is BGRA (Blue, Green, Red, Alpha).
            img_bgra = np.array(sct_img)

            # Convert BGRA to BGR for OpenCV compatibility by dropping the alpha channel.
            # The image processing pipeline expects a 3-channel BGR image.
            img_bgr = img_bgra[:, :, :3]

            return img_bgr
    except mss.exception.ScreenShotError as e:
        print(f"Error during screen capture: {e}")
        # Return an empty array on capture failure.
        return np.array([], dtype=np.uint8)


# This block allows for direct testing of the capture functionality.
if __name__ == '__main__':
    import cv2
    import time

    print("This script is a module and is not intended to be run directly.")
    print("However, a simple test will be performed in 3 seconds...")
    print("A 400x300 area from the screen coordinate (100, 100) will be captured.")
    time.sleep(3)

    try:
        # Define a test bounding box
        test_bbox = (100, 100, 400, 300)

        # Capture the screen area
        start_time = time.time()
        captured_image = capture_screen_area(test_bbox)
        end_time = time.time()

        print(f"Capture took {end_time - start_time:.4f} seconds.")

        if captured_image.size > 0:
            print(f"Capture successful. Image shape: {captured_image.shape}")
            print(f"Image dtype: {captured_image.dtype}")

            # Display the captured image using OpenCV for verification
            cv2.imshow("Test Capture", captured_image)
            print("Press any key in the 'Test Capture' window to close it.")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("Capture failed or returned an empty image. "
                  "This could be due to an invalid bounding box or a display error.")

    except ImportError:
        print("OpenCV (cv2) is required to run this test but is not installed.")
        print("Please install it using: pip install opencv-python")
    except Exception as e:
        print(f"An unexpected error occurred during the test: {e}")
```