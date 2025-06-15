# src/fontsnip/utils/clipboard.py

"""
A simple wrapper module for the 'pyperclip' library.

This module provides a single, robust function to copy a given string
(e.g., the top matched font name) to the system clipboard. It handles
potential errors if a clipboard mechanism is not available on the system.
"""

import logging
import pyperclip

# Configure a logger for this module
logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> None:
    """
    Copies the given text to the system clipboard.

    This function acts as a simple, robust wrapper around pyperclip.copy().
    It logs success or failure of the operation.

    Args:
        text: The string to be copied to the clipboard.

    Returns:
        None.
    """
    if not isinstance(text, str) or not text:
        logger.warning("Attempted to copy an empty or invalid string to clipboard.")
        return

    try:
        pyperclip.copy(text)
        logger.info(f"Successfully copied '{text}' to the system clipboard.")
    except pyperclip.PyperclipException as e:
        # This can happen on systems without a clipboard mechanism (e.g., headless servers)
        # or if the necessary copy/paste commands (xclip/xsel on Linux) are not installed.
        logger.error(f"Failed to copy text to clipboard. pyperclip error: {e}")
        # In a GUI application, one might show a non-intrusive error notification here.
        # For now, logging the error is sufficient for backend debugging.
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred during clipboard operation: {e}")