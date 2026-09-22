"""Entry point for the Mobile Device Forensic Workflow app."""
from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime


def _startup_log() -> str:
    """Log file path next to the exe (works frozen and from source)."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "data", "startup_error.log")


def _log_exc(stage: str) -> None:
    """Append an exception to data/startup_error.log so failures are visible
    even in a --windowed (console-less) build."""
    path = _startup_log()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {stage}\n")
            fh.write(traceback.format_exc())
    except OSError:
        pass


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        from mfw import APP_NAME, APP_VERSION
        from mfw.main_window import MainWindow
        from mfw.theme import apply_style

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        apply_style(app)

        def excepthook(etype, value, tb) -> None:  # keep GUI alive on errors
            text = "".join(traceback.format_exception(etype, value, tb))
            sys.stderr.write(text)
            _log_exc("runtime exception")
            QMessageBox.critical(None, "Unexpected error", text[-2000:])

        sys.excepthook = excepthook

        win = MainWindow()
        win.show()
        return app.exec()
    except Exception:
        _log_exc("startup failure")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
