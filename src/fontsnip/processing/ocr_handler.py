# src/fontsnip/processing/ocr_handler.py

"""
A wrapper module for the 'easyocr' library.

This module provides functionality to perform Optical Character Recognition (OCR)
on a preprocessed image. It initializes the OCR reader and contains a function
to extract high-confidence character data, including their bounding boxes.
"""

import logging
from typing import List, Tuple

import easyocr
import numpy as np

# --- Module-level Globals ---

# Lazy initialization of the reader. This can be slow, so we do it once.
# We specify 'en' for English. The model is downloaded automatically on first run.
# gpu=False is a safe default for cross-platform compatibility.
# For better performance, users with a supported GPU could set this to True.
_OCR_READER: easyocr.Reader | None = None

# Confidence threshold for filtering OCR results.
# Results below this value will be discarded.
# Set to a relatively low value because we are interested in the glyph shape,
# even if the character itself is not perfectly identified. The feature
# extractor will work on the image, not the recognized text.
MIN_CONFIDENCE = 0.4  # 40% confidence

# --- Type Definitions ---

# A single character result: (bounding_box, character_text)
# Bounding box is (x, y, w, h)
CharacterData = Tuple[Tuple[int, int, int, int], str]


# --- Functions ---

def _get_ocr_reader() -> easyocr.Reader:
    """
    Lazily initializes and returns the singleton easyocr.Reader instance.

    This avoids a slow startup time for the main application.
    """
    global _OCR_READER
    if _OCR_READER is None:
        logging.info("Initializing easyocr.Reader for the first time...")
        try:
            _OCR_READER = easyocr.Reader(['en'], gpu=False)
            logging.info("easyocr.Reader initialized successfully.")
        except Exception as e:
            logging.error(f"Fatal error during easyocr.Reader initialization: {e}")
            # Re-raise to indicate a critical failure that should stop the process
            raise
    return _OCR_READER


def perform_ocr(image: np.ndarray) -> List[CharacterData]:
    """
    Performs OCR on a preprocessed image and returns high-confidence characters.

    This function takes a binarized image, runs it through easyocr to detect
    words, and then breaks down the words into individual characters, estimating
    the bounding box for each one. This estimation is necessary because easyocr
    natively returns bounding boxes for words or lines, not individual characters.

    Args:
        image: A preprocessed image (preferably binarized, white text on
               black background) as a NumPy array.

    Returns:
        A list of tuples, where each tuple contains:
        - An estimated bounding box (x, y, w, h) for a single character.
        - The recognized character as a string.
    """
    if image is None or image.size == 0:
        logging.warning("perform_ocr called with an empty image.")
        return []

    try:
        reader = _get_ocr_reader()
    except Exception as e:
        logging.error(f"Could not get OCR reader, aborting OCR. Error: {e}")
        return []

    # easyocr's readtext works best on images with a certain pixel height.
    # The image_processor should have already upscaled it.
    # The `paragraph=False` option treats each line of text as a separate block.
    # `detail=1` ensures we get bounding boxes and confidence scores.
    try:
        # The result is a list of (bbox, text, confidence)
        results = reader.readtext(image, detail=1, paragraph=False)
    except Exception as e:
        logging.error(f"An error occurred during easyocr.readtext: {e}")
        return []

    all_characters: List[CharacterData] = []
    for (bbox, text, confidence) in results:
        if confidence < MIN_CONFIDENCE:
            logging.debug(f"Discarding OCR result with low confidence: '{text}' ({confidence:.2f})")
            continue

        if not text or not text.strip():
            continue

        # The bounding box from easyocr is a list of four points: [top-left, top-right, bottom-right, bottom-left]
        # We need to convert it to a standard (x, y, w, h) format.
        top_left = bbox[0]
        bottom_right = bbox[2]

        # Ensure coordinates are integers
        x = int(top_left[0])
        y = int(top_left[1])
        w = int(bottom_right[0] - top_left[0])
        h = int(bottom_right[1] - top_left[1])

        if w <= 0 or h <= 0 or len(text) == 0:
            continue

        # Estimate bounding box for each character in the recognized text.
        # This is a simplification, assuming monospace distribution within the word box.
        char_width_estimate = w / len(text)
        for i, char in enumerate(text):
            # We only care about alphanumeric characters for font matching
            if not char.isalnum():
                continue

            char_x = int(x + i * char_width_estimate)
            char_w = int(char_width_estimate)

            # Ensure the character box has a valid width
            if char_w <= 0:
                continue

            # Create a new bounding box for this character
            char_bbox = (char_x, y, char_w, h)

            # Add the character and its estimated box to our list
            all_characters.append((char_bbox, char))

    logging.info(f"OCR complete. Found {len(all_characters)} valid characters from {len(results)} text blocks.")
    return all_characters
```