# src/fontsnip/ui/results_window.py

"""
Defines a small, temporary window to display the font matching results.

This module contains the ResultsWindow class, a non-intrusive PyQt6 QWidget
that appears near the captured area, shows the top font matches, and
disappears automatically after a few seconds.
"""

import sys
from typing import List, Tuple

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel


class ResultsWindow(QWidget):
    """
    A small, temporary pop-up window to display font identification results.

    This window is designed to be frameless, stay on top of other applications,
    and automatically close after a set duration. It displays the top match
    prominently and lists other likely candidates.

    Attributes:
        CLOSE_DELAY (int): Time in milliseconds before the window auto-closes.
    """
    CLOSE_DELAY = 4000  # 4 seconds

    def __init__(self, top_matches: List[str], position: QPoint, parent: QWidget = None):
        """
        Initializes the results window.

        Args:
            top_matches (List[str]): A list of font name strings, with the best
                                     match at index 0.
            position (QPoint): The screen coordinates (top-left) where the
                               window should appear.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        if not top_matches:
            # Don't show a window if there are no results
            return

        self.top_matches = top_matches
        self._init_window_properties()
        self._init_ui()

        # Adjust position to ensure it's fully on screen if possible
        self.move(self._get_adjusted_position(position))

        # Automatically close the window after a delay
        QTimer.singleShot(self.CLOSE_DELAY, self.close)

    def _init_window_properties(self):
        """Sets the window flags and attributes for a non-intrusive popup."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |       # No title bar or border
            Qt.WindowType.WindowStaysOnTopHint |      # Always on top
            Qt.WindowType.ToolTip                     # Behaves like a tooltip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def _init_ui(self):
        """Creates and arranges the widgets within the window."""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(4)

        # --- Top Match Label ---
        # This is the most likely font, which was also copied to the clipboard.
        top_match_text = f"Copied: {self.top_matches[0]}"
        top_match_label = QLabel(top_match_text)
        top_match_label.setObjectName("TopMatchLabel")
        layout.addWidget(top_match_label)

        # --- Other Suggestions ---
        if len(self.top_matches) > 1:
            suggestions_title = QLabel("Other suggestions:")
            suggestions_title.setObjectName("SuggestionsTitleLabel")
            layout.addWidget(suggestions_title)

            for match in self.top_matches[1:3]:  # Show up to 2 other suggestions
                suggestion_label = QLabel(match)
                layout.addWidget(suggestion_label)

        self.setLayout(layout)
        self._apply_stylesheet()

    def _apply_stylesheet(self):
        """Applies CSS styles for a modern, clean look."""
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(35, 35, 35, 235);
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 6px;
                font-family: sans-serif;
            }
            QLabel#TopMatchLabel {
                font-size: 16px;
                font-weight: bold;
                color: #87CEEB; /* Sky Blue */
                padding-bottom: 5px;
                border: none;
            }
            QLabel#SuggestionsTitleLabel {
                font-size: 11px;
                color: #AAAAAA;
                font-style: italic;
                padding-top: 5px;
                border: none;
            }
            QLabel {
                font-size: 13px;
                color: #DDDDDD;
                border: none;
            }
        """)

    def _get_adjusted_position(self, position: QPoint) -> QPoint:
        """
        Adjusts the window position to keep it from rendering off-screen.

        Args:
            position (QPoint): The desired initial position.

        Returns:
            QPoint: The adjusted position.
        """
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_size = self.sizeHint()

        x = position.x()
        y = position.y()

        # Adjust if it goes off the right edge
        if x + window_size.width() > screen_geometry.right():
            x = screen_geometry.right() - window_size.width()

        # Adjust if it goes off the bottom edge
        if y + window_size.height() > screen_geometry.bottom():
            y = position.y() - window_size.height() - 10 # Place above original spot

        # Ensure it's not off the left or top edge
        x = max(x, screen_geometry.left())
        y = max(y, screen_geometry.top())

        return QPoint(x, y)


if __name__ == '__main__':
    # This block allows for standalone testing of the ResultsWindow UI component.
    app = QApplication(sys.argv)

    # --- Test Case 1: Three matches ---
    dummy_matches_1 = ["Arial", "Helvetica", "Roboto"]
    # Position it near the center of the screen for the test
    screen_rect = app.primaryScreen().geometry()
    pos1 = QPoint(screen_rect.center().x() - 100, screen_rect.center().y() - 100)
    results_window_1 = ResultsWindow(top_matches=dummy_matches_1, position=pos1)
    results_window_1.show()

    # --- Test Case 2: One match ---
    dummy_matches_2 = ["Courier New"]
    pos2 = QPoint(screen_rect.center().x() + 100, screen_rect.center().y())
    results_window_2 = ResultsWindow(top_matches=dummy_matches_2, position=pos2)
    results_window_2.show()
    
    # --- Test Case 3: No matches (should not appear) ---
    dummy_matches_3 = []
    pos3 = QPoint(100, 100)
    results_window_3 = ResultsWindow(top_matches=dummy_matches_3, position=pos3)
    results_window_3.show() # This should do nothing

    print("Displaying test windows. They will close automatically.")
    
    # Although the windows close on a timer, we need an event loop
    # for them to be processed and rendered correctly. We'll exit it
    # after the windows have had time to close.
    main_timer = QTimer()
    main_timer.singleShot(ResultsWindow.CLOSE_DELAY + 500, app.quit)
    
    sys.exit(app.exec())
```