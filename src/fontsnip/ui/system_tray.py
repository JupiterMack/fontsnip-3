# src/fontsnip/ui/system_tray.py

"""
Implements the system tray icon for the FontSnip application.

This module provides the SystemTrayIcon class, which creates and manages the
application's icon in the system tray. It includes a context menu for
accessing settings and quitting the application.
"""

import sys
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMessageBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QCoreApplication

# A placeholder for the icon path. In a real application, this would be
# handled by a resource system (e.g., Qt's .qrc) or a robust path resolver.
# For now, we assume an 'assets' folder exists at the project root.
ICON_PATH = "assets/icon.png"


class SystemTrayIcon(QSystemTrayIcon):
    """
    Manages the application's system tray icon and its context menu.

    Inherits from QSystemTrayIcon to provide native system tray integration.
    The main application logic (hotkey listening, state machine) is expected
    to run independently. This class provides the user-facing controls for
    quitting and accessing settings.
    """

    def __init__(self, parent=None):
        """
        Initializes the system tray icon and its context menu.
        """
        super().__init__(parent)

        # 1. Set Icon and Tooltip
        self._set_icon()
        self.setToolTip("FontSnip - Press Hotkey to Capture")
        self.setVisible(True)

        # 2. Create Context Menu
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

    def _set_icon(self):
        """
        Loads the application icon from the specified path.
        Provides a fallback if the icon cannot be loaded.
        """
        try:
            icon = QIcon(ICON_PATH)
            if icon.isNull():
                print(f"Warning: Could not load icon from '{ICON_PATH}'. "
                      "Ensure the file exists and the application is run from the project root.", file=sys.stderr)
                # Fallback to a standard Qt icon if the custom one fails
                self.setIcon(QApplication.style().standardIcon(QApplication.Style.SP_ComputerIcon))
            else:
                self.setIcon(icon)
        except Exception as e:
            print(f"Error loading icon: {e}", file=sys.stderr)
            self.setIcon(QApplication.style().standardIcon(QApplication.Style.SP_ComputerIcon))

    def _create_actions(self):
        """
        Creates the QAction objects for the context menu and connects them.
        """
        # Settings Action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)

        # Quit Action
        quit_action = QAction("Quit FontSnip", self)
        quit_action.triggered.connect(self.quit_application)

        # Add actions to the menu
        self.menu.addAction(settings_action)
        self.menu.addSeparator()
        self.menu.addAction(quit_action)

    def show_settings(self):
        """
        Placeholder function for showing a settings dialog.
        In a full application, this would open a new QDialog or QWidget
        for configuring settings like the hotkey.
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText("Settings")
        msg_box.setInformativeText("Settings configuration is not yet implemented.")
        msg_box.setWindowTitle("FontSnip Settings")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        # Ensure the message box appears on top of other windows
        msg_box.setWindowFlags(msg_box.windowFlags() | QCoreApplication.Qt.WindowType.WindowStaysOnTopHint)
        msg_box.exec()

    def quit_application(self):
        """
        Safely quits the entire application by exiting the event loop.
        """
        print("Quitting FontSnip via system tray.")
        # QCoreApplication.quit() is the standard, thread-safe way to
        # tell the application's event loop to exit.
        QCoreApplication.instance().quit()
```