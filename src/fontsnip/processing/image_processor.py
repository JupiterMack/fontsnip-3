# src/fontsnip/processing/image_processor.py

"""
Implements the image processing pipeline for FontSnip.

This module contains functions to prepare a captured screen image for Optical
Character Recognition (OCR). The pipeline is designed to enhance text clarity
and produce a clean, binarized image from a raw screen capture.
"""

import cv2
import numpy as np

# --- Constants for Processing ---
# Upscaling factor to improve OCR accuracy on small text. 2x or 3x is a good range.
UPSCALE_FACTOR = 2
# Block size for adaptive thresholding. It's the size of a pixel neighborhood
# that is used to calculate a threshold value for the pixel. Must be an odd number.
ADAPTIVE_THRESH_BLOCK_SIZE = 11
# A constant subtracted from the mean or weighted mean. Fine-tunes the threshold.
ADAPTIVE_THRESH_C = 5


def process_image_for_ocr(raw_image: np.ndarray) -> np.ndarray:
    """
    Processes a raw image from a screen capture for OCR.

    The pipeline consists of the following steps:
    1. Convert the raw BGRA image from MSS to a BGR image for OpenCV.
    2. Upscale the image to improve clarity of small fonts.
    3. Convert the image to grayscale.
    4. Apply adaptive thresholding to create a clean black-and-white image.

    Args:
        raw_image: A NumPy array representing the captured image,
                   typically in BGRA format from the 'mss' library.

    Returns:
        A processed, binarized NumPy array (OpenCV image) ready for OCR.
        The output image has white text on a black background.
    """
    if raw_image is None or raw_image.size == 0:
        raise ValueError("Input image is empty.")

    # 1. Convert BGRA to BGR
    # The 'mss' library captures in BGRA format. OpenCV works best with BGR.
    # We discard the alpha channel as it's not needed for OCR.
    if raw_image.shape[2] == 4:
        bgr_image = cv2.cvtColor(raw_image, cv2.COLOR_BGRA2BGR)
    else:
        bgr_image = raw_image

    # 2. Upscale the image
    # Resizing with cubic interpolation is effective for preserving text features.
    height, width, _ = bgr_image.shape
    upscaled_image = cv2.resize(
        bgr_image,
        (width * UPSCALE_FACTOR, height * UPSCALE_FACTOR),
        interpolation=cv2.INTER_CUBIC
    )

    # 3. Convert to Grayscale
    gray_image = cv2.cvtColor(upscaled_image, cv2.COLOR_BGR2GRAY)

    # Optional: Denoising - can be useful for noisy sources but adds overhead.
    # Can be enabled if OCR results are poor due to image noise.
    # gray_image = cv2.fastNlMeansDenoising(gray_image, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 4. Binarize with Adaptive Thresholding
    # This is crucial for handling varying background colors and lighting.
    # It calculates a different threshold for different regions of the image.
    # cv2.THRESH_BINARY_INV inverts the colors (text becomes white, background black),
    # which is a common format for contour detection and feature extraction later.
    binarized_image = cv2.adaptiveThreshold(
        gray_image,
        255,  # Max value to assign to pixels
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,  # Invert so text is white on a black background
        ADAPTIVE_THRESH_BLOCK_SIZE,
        ADAPTIVE_THRESH_C
    )

    return binarized_image


# Example usage for testing purposes
if __name__ == '__main__':
    # This block allows for direct testing of the image processor.
    # To run, you would need a sample image file (e.g., 'sample_capture.png').
    try:
        # Create a dummy image for demonstration if no file is available
        # This simulates a 200x100 pixel capture with gray text on a light gray background
        print("Creating a dummy test image...")
        dummy_w, dummy_h = 200, 100
        # Simulate a light gray background (BGRA format)
        dummy_bgra_image = np.full((dummy_h, dummy_w, 4), (220, 220, 220, 255), dtype=np.uint8)
        # Add some darker gray "text"
        cv2.putText(dummy_bgra_image, "Test Text 123", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100, 255), 2)
        print(f"Dummy image created with shape: {dummy_bgra_image.shape}")

        # Process the dummy image
        processed_image = process_image_for_ocr(dummy_bgra_image)
        print(f"Image processed successfully. Output shape: {processed_image.shape}")

        # Display the results for visual verification
        cv2.imshow("Original (Simulated BGRA)", dummy_bgra_image)
        cv2.imshow("Processed (Binarized)", processed_image)

        print("\nDisplaying images. Press any key to close the windows.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    except ImportError:
        print("OpenCV or NumPy is not installed. Cannot run the test.")
    except Exception as e:
        print(f"An error occurred during the test run: {e}")
```