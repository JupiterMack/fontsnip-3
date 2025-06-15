# scripts/build_font_database.py

"""
Standalone script to pre-compute the font feature database for FontSnip.

This script performs the following actions:
1.  Scans standard system directories to find all installed .ttf and .otf font files.
2.  For each font, it renders a predefined set of characters ('a'-'z', 'A'-'Z', '0'-'9')
    into memory using the Pillow library.
3.  Each rendered character image is processed through a feature extraction pipeline,
    which is designed to be identical to the one used on user-captured images in the
    main application.
4.  The features extracted include aspect ratio, pixel density, normalized centroid,
    and the number of holes (contours).
5.  The feature vectors for all characters of a single font are averaged to create a
    single, representative "fingerprint" vector for that font.
6.  The final database, a dictionary mapping font file names to their feature vectors,
    is saved to a pickle file ('data/font_features.pkl').

This pre-computation step is crucial for the performance of the main application,
as it avoids costly on-the-fly processing of the entire font library.
"""

import os
import platform
import pickle
import string
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# --- Constants ---

# The set of characters to render for each font to generate its feature vector.
CHARSET = string.ascii_letters + string.digits

# Font size in points to use for rendering the characters.
# This should be a reasonably high resolution to get good feature details.
FONT_SIZE = 48

# The canvas size for rendering each character. The character will be centered.
CANVAS_SIZE = (64, 64)

# Define the output directory and file path relative to this script's location.
# The script is in 'scripts/', so we go up one level to the project root, then to 'data/'.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "font_features.pkl"


def get_system_fonts():
    """
    Finds and returns a list of .ttf and .otf font file paths on the system.
    """
    font_paths = []
    system = platform.system()
    
    if system == "Windows":
        font_dirs = [Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"]
    elif system == "Darwin":  # macOS
        font_dirs = [
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library/Fonts",
        ]
    else:  # Linux
        font_dirs = [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local/share/fonts"
        ]

    print("Scanning for fonts in the following directories:")
    for directory in font_dirs:
        print(f"- {directory}")
        if directory.exists():
            for ext in ("*.ttf", "*.otf"):
                font_paths.extend(directory.rglob(ext))
    
    # Remove duplicates that might arise from symlinks or multiple search paths
    unique_font_paths = sorted(list(set(font_paths)))
    print(f"Found {len(unique_font_paths)} unique font files.")
    return unique_font_paths


def render_char(font_path, char, font_size, canvas_size):
    """
    Renders a single character using a given font onto a standardized canvas.

    Args:
        font_path (Path): Path to the .ttf or .otf font file.
        char (str): The single character to render.
        font_size (int): The font size in points.
        canvas_size (tuple): The (width, height) of the output image.

    Returns:
        np.ndarray: A grayscale NumPy array of the rendered character, or None if rendering fails.
    """
    try:
        font = ImageFont.truetype(str(font_path), font_size)
    except (IOError, OSError):
        # Pillow can't open or read the font file (it might be corrupt or unsupported)
        return None

    # Use textbbox to get the precise bounding box of the glyph
    try:
        bbox = font.getbbox(char)
    except (TypeError, ValueError):
        # Some fonts might fail on specific characters
        return None
        
    x0, y0, x1, y1 = bbox
    text_width = x1 - x0
    text_height = y1 - y0

    if text_width <= 0 or text_height <= 0:
        return None  # Character has no visible glyph in this font

    # Create an image that fits the character glyph perfectly
    char_img = Image.new("L", (text_width, text_height), 0)
    draw = ImageDraw.Draw(char_img)
    # Draw the character, offsetting it by its own bounding box's top-left corner
    draw.text((-x0, -y0), char, font=font, fill=255)

    # Create the final fixed-size canvas and paste the character image in the center
    canvas = Image.new("L", canvas_size, 0)
    paste_x = (canvas_size[0] - text_width) // 2
    paste_y = (canvas_size[1] - text_height) // 2
    canvas.paste(char_img, (paste_x, paste_y))

    # Convert to NumPy array for OpenCV processing
    return np.array(canvas)


def extract_features(glyph_img):
    """
    Computes a feature vector for a single character glyph image.
    This pipeline MUST be identical to the one used in the main application.

    Args:
        glyph_img (np.ndarray): A grayscale image containing a single, centered character.

    Returns:
        np.ndarray: A 1D NumPy array representing the feature vector, or None on failure.
    """
    # The input image is already binarized from the rendering step (0 or 255)
    
    # Find contours and the full hierarchy
    contours, hierarchy = cv2.findContours(
        glyph_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours or hierarchy is None:
        return None

    # Find the main outer contour (the one with no parent: hierarchy[...][3] == -1)
    try:
        outer_contour_idx = next(i for i, h in enumerate(hierarchy[0]) if h[3] == -1)
        outer_contour = contours[outer_contour_idx]
    except StopIteration:
        # This can happen if the glyph is empty or malformed.
        return None

    # 1. Aspect Ratio from the bounding box of the outer contour
    x, y, w, h = cv2.boundingRect(outer_contour)
    if h == 0 or w == 0:
        return None
    aspect_ratio = w / h

    # 2. Pixel Density within the bounding box
    roi = glyph_img[y:y+h, x:x+w]
    pixel_density = np.sum(roi > 0) / roi.size

    # 3. Normalized Centroid Location
    M = cv2.moments(outer_contour)
    if M["m00"] == 0:
        return None
    # Calculate centroid and normalize it relative to the bounding box's top-left corner
    cx = (M["m10"] / M["m00"] - x) / w
    cy = (M["m01"] / M["m00"] - y) / h

    # 4. Number of Holes
    # A hole is any contour whose direct parent is the main outer contour.
    num_holes = np.sum(hierarchy[0, :, 3] == outer_contour_idx)

    return np.array([aspect_ratio, pixel_density, cx, cy, num_holes], dtype=np.float32)


def main():
    """
    Main function to drive the database creation process.
    """
    print("Starting FontSnip database build process...")
    
    # Ensure the output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Database will be saved to: {OUTPUT_FILE}")

    font_paths = get_system_fonts()
    font_database = {}

    # Use tqdm for a progress bar as this can be a lengthy process
    for font_path in tqdm(font_paths, desc="Processing fonts"):
        char_features_list = []
        
        for char in CHARSET:
            # 1. Render character to a standardized canvas
            glyph_img = render_char(font_path, char, FONT_SIZE, CANVAS_SIZE)
            if glyph_img is None:
                continue

            # 2. Extract features from the rendered image
            features = extract_features(glyph_img)
            if features is not None:
                char_features_list.append(features)

        # 3. If we have features, compute the average vector for the font
        if char_features_list:
            # Convert list of arrays to a 2D numpy array and calculate the mean column-wise
            mean_vector = np.mean(np.array(char_features_list), axis=0)
            font_database[font_path.name] = mean_vector

    # 4. Save the completed database to a file
    if not font_database:
        print("\nWarning: No fonts were processed. The database is empty.")
        return

    print(f"\nSuccessfully processed {len(font_database)} fonts.")
    print(f"Saving database with {len(font_database)} entries...")
    
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump(font_database, f)

    print("Font database build complete!")
    print(f"Feature vector dimension: {len(next(iter(font_database.values())))}")


if __name__ == "__main__":
    main()
```