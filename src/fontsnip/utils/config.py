# src/fontsnip/utils/config.py

"""
Manages application configuration settings.

This module provides a ConfigManager class that handles loading settings from a
JSON file, providing default values, and saving changes. This allows for
persistent, user-configurable settings like the global hotkey.
"""

import json
import logging
import sys
from pathlib import Path

# Constants
APP_NAME = "fontsnip"
CONFIG_FILE_NAME = "config.json"
DATABASE_FILE_NAME = "font_features.pkl"

# Default settings for the application
DEFAULT_CONFIG = {
    "hotkey": "<ctrl>+<alt>+s",
    "ocr_confidence_threshold": 60,
    "image_upscale_factor": 2.0,
    "results_display_duration_ms": 5000,
    "top_n_results": 3,
}

# Set up a logger for this module
logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """
    Determines the appropriate application configuration directory based on the OS.

    This ensures that user-specific data like config and the font database are
    stored in standard locations.

    Returns:
        Path: The absolute path to the configuration directory.
    """
    if sys.platform == "win32":
        # Windows: %APPDATA%/fontsnip
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/fontsnip
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        # Linux/other: ~/.config/fontsnip
        return Path.home() / ".config" / APP_NAME


class ConfigManager:
    """
    Handles loading, accessing, and saving application configuration.

    This class provides a centralized way to manage settings, ensuring that
    they are loaded from a file on startup and saved when changed. It gracefully
    handles cases where the config file is missing or corrupted.
    """

    def __init__(self):
        """
        Initializes the ConfigManager, determines the config path, and loads the
        configuration.
        """
        self.config_dir = get_config_dir()
        self.config_path = self.config_dir / CONFIG_FILE_NAME
        self.database_path = self.config_dir / DATABASE_FILE_NAME
        self.config = {}
        self.load_config()

    def load_config(self):
        """
        Loads configuration from the JSON file. If the file doesn't exist or is
        invalid, it creates one with default settings.
        """
        # Start with defaults, then override with user's config
        self.config = DEFAULT_CONFIG.copy()

        if not self.config_path.exists():
            logger.info(f"Config file not found. Creating default config at: {self.config_path}")
            self.save_config()  # This saves the default config
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            # Merge user config into defaults to ensure all keys exist
            self.config.update(user_config)
            logger.info(f"Successfully loaded configuration from {self.config_path}")
        except json.JSONDecodeError:
            logger.error(
                f"Could not decode JSON from {self.config_path}. "
                "Using default configuration. The corrupted file will be overwritten on next save."
            )
            # The config is already set to defaults, so we just log the error.
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading config: {e}. Using defaults.")

    def save_config(self):
        """
        Saves the current configuration to the JSON file.
        """
        try:
            # Ensure the directory exists before trying to write the file
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, sort_keys=True)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_path}: {e}")

    def get(self, key: str, default=None):
        """
        Retrieves a configuration value.

        Args:
            key (str): The configuration key to retrieve.
            default: The value to return if the key is not found.

        Returns:
            The value associated with the key, or the default value.
        """
        return self.config.get(key, default)

    def set(self, key: str, value):
        """
        Sets a configuration value and saves the configuration to the file.

        Args:
            key (str): The configuration key to set.
            value: The new value for the key.
        """
        self.config[key] = value
        self.save_config()


# Create a single, shared instance of the ConfigManager.
# Other modules can import this instance directly to access configuration.
# e.g., from fontsnip.utils.config import config_manager
config_manager = ConfigManager()
```