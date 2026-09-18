"""System tray integration with status summary."""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap

class SystemTray:
    def __init__(self, parent=None) -> None:
        self._tray = QSystemTrayIcon(parent)
        self._tray.setIcon(QIcon("assets/icon.ico") if __import__("os").path.exists("assets/icon.ico") else QIcon())
        self._menu = QMenu()

        self._status = self._menu.addAction("Status: Running")
        self._status.setDisabled(True)
        self._menu.addSeparator()
        self._show = self._menu.addAction("Show Window")
        self._show.triggered.connect(self._show_window)
        self._menu.addSeparator()
        self._quit = self._menu.addAction("Quit")
        self._quit.triggered.connect(QApplication.quit)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    def show(self):
        self._tray.show()

    def update_status(self, text: str):
        self._status.setText(f"Status: {text}")

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        if self._tray.parent():
            self._tray.parent().show()
            self._tray.parent().raise_()
