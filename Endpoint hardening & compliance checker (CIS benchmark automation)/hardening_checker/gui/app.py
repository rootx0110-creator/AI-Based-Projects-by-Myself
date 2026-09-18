"""QApplication bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .theme import qss


def _asset(name: str) -> Path:
    """Resolve an asset bundled with the app (works for source & frozen exe)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "assets" / name


def run_gui() -> int:
    """Create the app, apply theme, and show the main window."""
    app = QApplication(sys.argv)
    app.setApplicationName("Endpoint Hardening & Compliance Checker")
    app.setStyle("Fusion")
    app.setStyleSheet(qss())
    icon_file = _asset("icon.png")
    if icon_file.is_file():
        app.setWindowIcon(QIcon(str(icon_file)))
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    win = MainWindow()
    win.show()
    return app.exec()


__all__ = ["run_gui"]
