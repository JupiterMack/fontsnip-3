# src/fontsnip/ui/capture_overlay.py

"""
Defines the full-screen, semi-transparent overlay for screen capture.

This module contains the CaptureOverlay class, a PyQt6 QWidget that facilitates
the screen capture process. It handles mouse events to allow the user to draw
a selection rectangle and emits a signal with the final coordinates upon
completion.
"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QCursor, QScreen


class CaptureOverlay(QWidget):
    """
    A full-screen, semi-transparent overlay widget for selecting a screen region.

    This widget covers the entire screen, provides a crosshair cursor, and allows
    the user to drag a rectangle. When the mouse button is released, it emits a
    'region_selected' signal containing the QRect of the selected area and then
    hides itself.
    """

    # Signal emitted when a region is successfully selected.
    # The payload is a QRect object representing the selected area.
    region_selected = pyqtSignal(QRect)

    def __init__(self, parent=None):
        """
        Initializes the CaptureOverlay widget.
        """
        super().__init__(parent)

        # --- State Variables ---
        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False

        # --- Window Configuration ---
        # Get the geometry of the primary screen
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen_geometry = primary_screen.geometry()
            self.setGeometry(screen_geometry)
        else:
            # Fallback for systems without a primary screen concept
            self.showFullScreen()

        # Set window flags for a borderless, stay-on-top overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Set the cursor to a crosshair to indicate capture mode
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def paintEvent(self, event):
        """
        Handles the painting of the widget.

        Draws the semi-transparent overlay and the selection rectangle.
        """
        painter = QPainter(self)

        # 1. Draw the semi-transparent background overlay
        overlay_color = QColor(0, 0, 0, 100)  # Black with ~40% opacity
        painter.fillRect(self.rect(), QBrush(overlay_color))

        # 2. If a selection is in progress, draw the selection area
        if self.is_selecting:
            # Define the selection rectangle based on current start/end points
            selection_rect = QRect(self.begin, self.end).normalized()

            # 3. Clear the area inside the selection rectangle
            # This makes the selected area non-transparent, showing the screen below
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection_rect, Qt.BrushStyle.SolidPattern)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # 4. Draw a border around the selection rectangle for clarity
            pen = QPen(QColor(255, 255, 255, 220), 1, Qt.PenStyle.SolidLine) # White, 1px border
            painter.setPen(pen)
            painter.drawRect(selection_rect)

    def mousePressEvent(self, event):
        """
        Handles the start of a mouse drag (selection start).
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = True
            self.begin = event.position().toPoint()
            self.end = self.begin  # Initialize end point
            self.update()  # Trigger a repaint

    def mouseMoveEvent(self, event):
        """
        Handles mouse movement during a drag (updates selection).
        """
        if self.is_selecting:
            self.end = event.position().toPoint()
            self.update()  # Trigger a repaint to show live feedback

    def mouseReleaseEvent(self, event):
        """
        Handles the end of a mouse drag (selection finalized).
        """
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False

            # Finalize the rectangle, ensuring it has a non-zero area
            selection_rect = QRect(self.begin, self.end).normalized()

            # Hide the overlay immediately to return control to the user
            self.hide()

            # Only emit the signal if a valid rectangle was drawn
            if selection_rect.width() > 0 and selection_rect.height() > 0:
                self.region_selected.emit(selection_rect)

            # Reset cursor to default
            QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
            QApplication.restoreOverrideCursor()

    def keyPressEvent(self, event):
        """
        Allows the user to cancel the capture operation with the Escape key.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.is_selecting = False
            self.hide()
            # Reset cursor to default
            QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
            QApplication.restoreOverrideCursor()

    def showEvent(self, event):
        """
        Ensures the cursor is set correctly every time the widget is shown.
        """
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        super().showEvent(event)


if __name__ == '__main__':
    import sys

    def on_region_selected(rect):
        """A simple slot to test the signal."""
        print(f"Region selected: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
        # In a real application, this would trigger the next state
        app.quit()

    app = QApplication(sys.argv)

    # Create and show the capture overlay
    overlay = CaptureOverlay()
    overlay.region_selected.connect(on_region_selected)
    overlay.show()

    sys.exit(app.exec())
```