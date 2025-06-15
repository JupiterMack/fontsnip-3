# src/fontsnip/matching/feature_extractor.py

"""
Core logic for extracting font 'fingerprints' from character images.

This module provides functions to compute a feature vector from a single
character's bitmap image. The extracted features are designed to be
invariant to scale and translation, allowing for robust comparison between
characters captured from the screen and those rendered from font files.

The features include:
- Aspect Ratio
- Pixel Density
- Normalized Centroid Location
- Contour Analysis (Number of Holes, Normalized Perimeter, Normalized Area)
"""

import cv2
import numpy as np

# The number of features this extractor generates.
# This is useful for initializing arrays and for sanity checks.
# 1. Aspect Ratio
# 2. Pixel Density
# 3. Normalized Centroid X
# 4. Normalized Centroid Y
# 5. Number of Holes
# 6. Normalized Perimeter
# 7. Normalized Area
FEATURE_VECTOR_SIZE = 7


def extract_features(char_image: np.ndarray) -> np.ndarray:
    """
    Computes a feature vector for a single character image.

    The input image is expected to be a binarized, single-channel NumPy array
    where the character is white (255) and the background is black (0).

    Args:
        char_image: A 2D NumPy array representing the binarized character.

    Returns:
        A 1D NumPy array of size FEATURE_VECTOR_SIZE containing the
        extracted features. Returns a zero vector if the image is invalid.
    """
    # Ensure the image is a 2D array and has some content
    if char_image is None or char_image.ndim != 2 or char_image.size == 0:
        return np.zeros(FEATURE_VECTOR_SIZE, dtype=np.float32)

    h, w = char_image.shape
    if h == 0 or w == 0:
        return np.zeros(FEATURE_VECTOR_SIZE, dtype=np.float32)

    # --- Feature 1: Aspect Ratio ---
    aspect_ratio = w / h

    # --- Feature 2: Pixel Density ---
    # The ratio of foreground pixels to the total number of pixels.
    total_pixels = h * w
    white_pixels = cv2.countNonZero(char_image)
    pixel_density = white_pixels / total_pixels if total_pixels > 0 else 0.0

    # --- Features 3 & 4: Normalized Centroid ---
    # The center of mass of the glyph, normalized to be in [0, 1].
    moments = cv2.moments(char_image)
    norm_centroid_x = 0.0
    norm_centroid_y = 0.0
    if moments["m00"] != 0:
        center_x = moments["m10"] / moments["m00"]
        center_y = moments["m01"] / moments["m00"]
        norm_centroid_x = center_x / w
        norm_centroid_y = center_y / h

    # --- Contour-based Features ---
    # To ensure contours at the edge are found correctly, we add a small border.
    # The input image is assumed to be uint8.
    padded_image = cv2.copyMakeBorder(char_image, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    
    # Find all contours and their hierarchy. RETR_TREE is crucial for hole detection.
    contours, hierarchy = cv2.findContours(
        padded_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    num_holes = 0
    total_perimeter = 0.0
    total_area = 0.0

    if hierarchy is not None and len(hierarchy) > 0:
        # --- Feature 5: Number of Holes ---
        # A hole is a contour that has a parent in the hierarchy.
        # The hierarchy is a list of [Next, Previous, First_Child, Parent].
        # We iterate through all contours and check if their parent index is not -1.
        for i in range(len(contours)):
            if hierarchy[0][i][3] != -1:  # has a parent
                num_holes += 1

        # --- Features 6 & 7: Normalized Perimeter and Area ---
        # We consider only the external contours for these measurements to avoid
        # double-counting areas/perimeters from holes.
        # An external contour is one with no parent (parent index is -1).
        for i, contour in enumerate(contours):
            if hierarchy[0][i][3] == -1: # is an external contour
                total_perimeter += cv2.arcLength(contour, True)
                total_area += cv2.contourArea(contour)

    # Normalize perimeter by image diagonal and area by total image area
    # to make them scale-invariant.
    diagonal = np.sqrt(h**2 + w**2)
    norm_perimeter = total_perimeter / diagonal if diagonal > 0 else 0.0
    norm_area = total_area / total_pixels if total_pixels > 0 else 0.0

    # Assemble the final feature vector
    feature_vector = np.array([
        aspect_ratio,
        pixel_density,
        norm_centroid_x,
        norm_centroid_y,
        float(num_holes),
        norm_perimeter,
        norm_area
    ], dtype=np.float32)

    # Sanity check for NaN or Inf values
    feature_vector[np.isnan(feature_vector)] = 0.0
    feature_vector[np.isinf(feature_vector)] = 0.0

    return feature_vector


if __name__ == '__main__':
    # --- Test Suite ---
    # This block demonstrates the feature extractor with sample character images.

    def create_test_image(char: str, font_size: int = 60) -> np.ndarray:
        """Creates a binarized image of a character for testing."""
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a blank image
        img_size = (font_size, font_size)
        image = Image.new("L", img_size, "black")  # "L" for grayscale
        draw = ImageDraw.Draw(image)

        # Use a common system font for reproducibility if possible
        try:
            font = ImageFont.truetype("arial.ttf", font_size - 10)
        except IOError:
            font = ImageFont.load_default()

        # Draw the character
        bbox = draw.textbbox((0, 0), char, font=font)
        # Center the character
        x = (img_size[0] - (bbox[2] - bbox[0])) / 2
        y = (img_size[1] - (bbox[3] - bbox[1])) / 2
        draw.text((x, y), char, font=font, fill="white")

        # Convert to NumPy array and binarize
        np_image = np.array(image)
        _, binarized_image = cv2.threshold(np_image, 127, 255, cv2.THRESH_BINARY)
        
        # Crop to bounding box of the character
        x, y, w, h = cv2.boundingRect(binarized_image)
        return binarized_image[y:y+h, x:x+w]

    print("--- FontSnip Feature Extractor Test ---")

    # Test Case 1: Character 'T' (no holes)
    img_T = create_test_image('T')
    features_T = extract_features(img_T)
    print(f"\nCharacter: 'T'")
    print(f"Feature Vector (size {len(features_T)}):")
    print(features_T)
    assert features_T[4] == 0.0, "Test Failed: 'T' should have 0 holes."
    print("Test Passed: 'T' has 0 holes.")

    # Test Case 2: Character 'o' (one hole)
    img_o = create_test_image('o')
    features_o = extract_features(img_o)
    print(f"\nCharacter: 'o'")
    print(f"Feature Vector (size {len(features_o)}):")
    print(features_o)
    assert features_o[4] == 1.0, "Test Failed: 'o' should have 1 hole."
    print("Test Passed: 'o' has 1 hole.")

    # Test Case 3: Character 'B' (two holes)
    img_B = create_test_image('B')
    features_B = extract_features(img_B)
    print(f"\nCharacter: 'B'")
    print(f"Feature Vector (size {len(features_B)}):")
    print(features_B)
    assert features_B[4] == 2.0, "Test Failed: 'B' should have 2 holes."
    print("Test Passed: 'B' has 2 holes.")

    # Test Case 4: Empty Image
    img_empty = np.zeros((50, 50), dtype=np.uint8)
    features_empty = extract_features(img_empty)
    print(f"\nEmpty Image")
    print(f"Feature Vector (size {len(features_empty)}):")
    print(features_empty)
    assert np.all(features_empty == 0), "Test Failed: Empty image should have a zero vector."
    print("Test Passed: Empty image handled correctly.")
    
    # Test Case 5: Null Image
    features_null = extract_features(None)
    print(f"\nNull Image")
    print(f"Feature Vector (size {len(features_null)}):")
    print(features_null)
    assert np.all(features_null == 0), "Test Failed: Null image should have a zero vector."
    print("Test Passed: Null image handled correctly.")

    print("\n--- All tests completed. ---")
```