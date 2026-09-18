"""System tray icon: mini-speed tooltip, quick actions, balloon alerts."""
from __future__ import annotations

import os

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from utils.format import fmt_speed
from utils.paths import resource_path


class TrayIcon(QSystemTrayIcon):
    """Tray icon with context menu and balloon notifications."""

    def __init__(self, main_window) -> None:  # type: ignore[no-untyped-def]
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        super().__init__(icon, main_window)
        self.main_window = main_window
        self.setToolTip("NetPulse — starting…")

        menu = QMenu()
        self.show_action = QAction("Show / Hide dashboard", menu)
        self.show_action.triggered.connect(self._toggle_main)
        self.hud_action = QAction("Toggle HUD", menu)
        self.hud_action.triggered.connect(self._toggle_hud)
        quit_action = QAction("Quit NetPulse", menu)
        quit_action.triggered.connect(self._quit)

        menu.addAction(self.show_action)
        menu.addAction(self.hud_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _toggle_main(self) -> None:
        """Show or hide the main window."""
        win = self.main_window
        if win.isVisible() and not win.isMinimized():
            win.hide()
        else:
            win.showNormal()
            win.activateWindow()

    def _toggle_hud(self) -> None:
        """Toggle the floating HUD via the main window."""
        if hasattr(self.main_window, "toggle_hud"):
            self.main_window.toggle_hud()

    def _quit(self) -> None:
        """Quit the application cleanly."""
        if hasattr(self.main_window, "request_quit"):
            self.main_window.request_quit()

    def _on_activated(self, reason) -> None:  # type: ignore[no-untyped-def]
        """Left-click toggles the dashboard."""
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_main()

    def update_speed(self, down_mbps: float, up_mbps: float) -> None:
        """Refresh the tooltip mini-speed text."""
        self.setToolTip(f"NetPulse  ↓ {fmt_speed(down_mbps * 1e6)}  ↑ {fmt_speed(up_mbps * 1e6)}")

    def balloon(self, title: str, body: str, icon_type=QSystemTrayIcon.Information) -> None:
        """Show a tray balloon (used when toasts are suppressed)."""
        self.showMessage(title, body, icon_type, 4000)
