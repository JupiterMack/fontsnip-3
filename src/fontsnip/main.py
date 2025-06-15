#!/usr/bin/env python3
# src/fontsnip/main.py

"""
Main entry point for the FontSnip application.

This script initializes the QApplication, sets up the system tray icon,
registers the global hotkey listener, and starts the application event loop.
It orchestrates the overall application lifecycle.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from pynput import keyboard

# Assuming a modular structure where these components exist.
# The StateMachine is the core logic handler.
from fontsnip.app_logic.state_machine import StateMachine
# The SystemTray provides the user interface for quitting the app.
# This class would be defined in a separate gui module.
from fontsnip.gui.system_tray import SystemTray
# A utility for loading resources like icons.
from fontsnip.utils.resource_loader import resource_path

# --- Application Configuration ---
# In a real application, this would be loaded from a config file (e.g., config.ini or settings.json)
# For now, we hardcode the default hotkey.
HOTKEY_COMBINATION = '<ctrl>+<alt>+s'
LOG_LEVEL = logging.INFO


def setup_logging():
    """Configures basic logging for the application."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
    )
    # Reduce verbosity from libraries that use logging
    logging.getLogger("pynput").setLevel(logging.WARNING)
    logging.info("FontSnip application starting...")


def main():
    """Main execution function for FontSnip."""
    setup_logging()

    # 1. Initialize the QApplication
    # This is the core object for any PyQt6 application.
    app = QApplication(sys.argv)

    # Set an application icon. This might show up in task switchers.
    # The SystemTray icon is set separately.
    # app.setWindowIcon(QIcon(resource_path('icons/app_icon.png')))

    # 2. Prevent the app from quitting when the last window is closed.
    # This is crucial for a system tray application that should run in the background.
    app.setQuitOnLastWindowClosed(False)

    # 3. Initialize the core application logic state machine.
    # The state machine handles the entire capture -> process -> display workflow.
    try:
        state_machine = StateMachine()
    except Exception as e:
        logging.error(f"Failed to initialize the State Machine: {e}", exc_info=True)
        logging.error("This may be due to a missing font database or OCR model.")
        logging.error("Please run 'scripts/build_font_database.py' and ensure EasyOCR models are downloaded.")
        # In a real app, a user-friendly dialog would be shown here.
        sys.exit(1)


    # 4. Define the callback function for the global hotkey.
    def on_hotkey_activate():
        """
        This function is executed when the user presses the registered hotkey.
        It triggers the state machine to begin the screen capture process.
        """
        logging.info(f"Hotkey '{HOTKEY_COMBINATION}' activated. Starting capture sequence.")
        state_machine.start_capture_sequence()

    # 5. Set up the global hotkey listener.
    # pynput's GlobalHotKeys runs in its own thread, listening for key combinations
    # system-wide without blocking our main application event loop.
    hotkey_listener = keyboard.GlobalHotKeys({
        HOTKEY_COMBINATION: on_hotkey_activate
    })

    # 6. Create and show the System Tray Icon.
    # This is the primary UI for the user to interact with the running application,
    # mainly to quit it. It needs a reference to the app to call app.quit().
    try:
        tray_icon = SystemTray(app)
        tray_icon.show()
        logging.info(f"System tray icon created. Listening for hotkey: {HOTKEY_COMBINATION}")
    except Exception as e:
        logging.error(f"Failed to create system tray icon: {e}", exc_info=True)
        sys.exit(1)


    # 7. Start the listener and the application event loop.
    try:
        hotkey_listener.start()
        logging.info("Global hotkey listener started successfully.")

        # Start the Qt event loop. This call is blocking and will only return
        # when the application is quit (e.g., via the tray icon's quit action).
        exit_code = app.exec()
        sys.exit(exit_code)

    except Exception as e:
        logging.error(f"An unhandled exception occurred in the main loop: {e}", exc_info=True)

    finally:
        # 8. Graceful shutdown.
        # Ensure the hotkey listener thread is stopped when the application exits.
        if hotkey_listener.is_alive():
            hotkey_listener.stop()
            logging.info("Global hotkey listener stopped.")
        logging.info("FontSnip application has shut down.")


if __name__ == '__main__':
    main()
```