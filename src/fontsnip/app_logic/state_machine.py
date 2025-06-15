# src/fontsnip/app_logic/state_machine.py

"""
Defines and manages the core application state machine.

This module is the central orchestrator of the FontSnip application. It handles
the workflow transitions: Idle -> Capture -> Processing -> Display. It is
triggered by the global hotkey listener, orchestrates calls to the capture UI,
image processing pipeline, and font matching logic, and finally triggers the
display of the results.
"""

import logging
import pickle
from enum import Enum, auto
from pathlib import Path

import numpy as np
import pyperclip
from PyQt6.QtCore import QObject, pyqtSignal, QThread

# Assuming other project modules are structured as follows.
# These imports will be resolved when the application is run as a package.
from fontsnip.image_processing.pipeline import ImageProcessor
from fontsnip.font_matching.matcher import FontMatcher
from fontsnip.ui.capture_overlay import CaptureOverlay
from fontsnip.ui.results_window import ResultsWindow
from fontsnip.utils.config import get_config
from fontsnip.utils.singleton import Singleton

# Configure logging for this module
logger = logging.getLogger(__name__)


class AppState(Enum):
    """Enumeration for the application's possible states."""
    IDLE = auto()
    CAPTURING = auto()
    PROCESSING = auto()
    DISPLAYING_RESULTS = auto()


class ProcessingWorker(QObject):
    """
    A QObject worker for offloading heavy processing to a separate thread.

    This prevents the GUI from freezing during image processing and font matching.
    It takes the captured image and the font database, performs the necessary
    computations, and emits signals with the results or any errors.
    """
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, image_array: np.ndarray, font_database: dict):
        super().__init__()
        self._image_array = image_array
        self._font_database = font_database
        self._image_processor = ImageProcessor()
        self._font_matcher = FontMatcher()

    def run(self):
        """The main processing task to be executed in the thread."""
        try:
            logger.info("Worker: Starting image processing...")
            # Step 1: Process image to get character data
            char_data = self._image_processor.process_image(self._image_array)

            if not char_data:
                logger.warning("Worker: No characters with sufficient confidence found by OCR.")
                self.finished.emit([])  # Emit empty list for no results
                return

            logger.info(f"Worker: Found {len(char_data)} valid characters. Starting font matching...")
            # Step 2: Match features against the database
            top_matches = self._font_matcher.find_best_matches(char_data, self._font_database)

            if not top_matches:
                logger.warning("Worker: Could not find any font matches.")
                self.finished.emit([])
                return

            logger.info(f"Worker: Found top matches: {[match[0] for match in top_matches]}")
            self.finished.emit(top_matches)

        except Exception as e:
            logger.exception("An error occurred during processing in the worker thread.")
            self.error.emit(f"Processing failed: {e}")


class StateMachine(QObject, metaclass=Singleton):
    """
    Manages the application's state and orchestrates the workflow.

    This class is a Singleton QObject, ensuring a single, consistent state
    manager throughout the application's lifecycle. It connects UI events to
    backend logic and manages the transitions between states.
    """
    # Signal to notify the main application to show an error message
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = AppState.IDLE
        self._config = get_config()
        self._font_database = self._load_font_database()

        if not self._font_database:
            # If the database fails to load, the app is non-functional.
            # The error is logged, and the state machine will refuse to start capture.
            return

        # UI Components
        self._capture_overlay = CaptureOverlay()
        self._results_window = ResultsWindow()

        # Worker thread management
        self._worker_thread = None
        self._worker = None

        # Connect UI signals to state machine slots
        self._capture_overlay.image_captured.connect(self._on_image_captured)
        self._capture_overlay.capture_cancelled.connect(self._return_to_idle)
        self._results_window.closed.connect(self._return_to_idle)

        logger.info("State machine initialized and ready.")

    def _load_font_database(self) -> dict | None:
        """Loads the pre-computed font feature database from a pickle file."""
        db_path_str = self._config.get('database', 'path', fallback='data/font_features.pkl')
        db_path = Path(db_path_str)

        if not db_path.exists():
            error_msg = f"Font database not found at '{db_path}'. Please run the build script."
            logger.critical(error_msg)
            self.error_occurred.emit(error_msg)
            return None
        try:
            with open(db_path, 'rb') as f:
                database = pickle.load(f)
            logger.info(f"Successfully loaded font database with {len(database)} fonts.")
            return database
        except (pickle.UnpicklingError, EOFError, FileNotFoundError) as e:
            error_msg = f"Failed to load or parse font database '{db_path}': {e}"
            logger.critical(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return None

    def _set_state(self, new_state: AppState):
        """Sets and logs the application state."""
        if self._state != new_state:
            logger.info(f"State transition: {self._state.name} -> {new_state.name}")
            self._state = new_state

    def start_capture(self):
        """
        Entry point for the workflow, triggered by the global hotkey.
        """
        if self._state != AppState.IDLE:
            logger.warning(f"Capture attempted while in non-idle state: {self._state.name}")
            return

        if not self._font_database:
            logger.error("Cannot start capture: font database is not loaded.")
            self.error_occurred.emit("Font database is missing. Cannot proceed.")
            return

        self._set_state(AppState.CAPTURING)
        self._capture_overlay.start_capture()

    def _on_image_captured(self, image_array: np.ndarray):
        """
        Handles the captured image data from the overlay.
        Spawns a worker thread to process the image.
        """
        if self._state != AppState.CAPTURING:
            return

        self._set_state(AppState.PROCESSING)

        # Offload processing to a worker thread to keep the GUI responsive
        self._worker_thread = QThread()
        self._worker = ProcessingWorker(image_array, self._font_database)
        self._worker.moveToThread(self._worker_thread)

        # Connect worker signals to handler slots
        self._worker.finished.connect(self._on_processing_finished)
        self._worker.error.connect(self._on_processing_error)

        # Clean up the thread once the worker is done
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        # Start the processing
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()
        logger.info("Handed off image to processing worker thread.")

    def _on_processing_finished(self, matches: list):
        """
        Handles the results from the processing worker.
        """
        self._set_state(AppState.DISPLAYING_RESULTS)

        if not matches:
            # In a real app, you might show a "No fonts found" notification
            logger.info("Processing finished, but no matches were found.")
            self._return_to_idle()
            return

        top_match_name = matches[0][0]
        logger.info(f"Top match found: {top_match_name}. Copying to clipboard.")

        try:
            pyperclip.copy(top_match_name)
            logger.info("Copied font name to clipboard.")
        except pyperclip.PyperclipException as e:
            error_msg = f"Could not copy to clipboard: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

        self._results_window.display_results(matches)

    def _on_processing_error(self, error_message: str):
        """Handles errors emitted from the worker thread."""
        logger.error(f"Received error from worker: {error_message}")
        self.error_occurred.emit(error_message)
        self._return_to_idle()

    def _return_to_idle(self):
        """Resets the application state to IDLE."""
        # Ensure UI elements that might be open are closed
        if self._capture_overlay.isVisible():
            self._capture_overlay.close()
        if self._results_window.isVisible():
            self._results_window.close()

        # Clean up any lingering worker threads if cancellation happened mid-process
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            self._worker_thread.wait() # Wait for it to terminate cleanly
        self._worker_thread = None
        self._worker = None

        self._set_state(AppState.IDLE)