"""Path helpers for locating bundled resources and the per-user app-data directory.

Works both from source (src/main.py) and from the PyInstaller onefile bundle.
"""
from __future__ import annotations

import os
import sys

APP_NAME = "NetPulse"


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> str:
    """Directory containing the executable (or main.py when running from source)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(rel: str) -> str:
    """Absolute path to a bundled resource (works inside the PyInstaller bundle)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, rel)
    # From source: src/utils/paths.py -> project root is three levels up.
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, rel)


def appdata_dir() -> str:
    """Per-user config/data directory: %APPDATA%/NetPulse (created on demand)."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    """Path of the JSON config file."""
    return os.path.join(appdata_dir(), "config.json")


def log_dir() -> str:
    """Directory for rotating log files (created on demand)."""
    path = os.path.join(appdata_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def db_path() -> str:
    """Path of the SQLite database file."""
    return os.path.join(appdata_dir(), "netpulse.db")


def single_instance_lock_path() -> str:
    """Path of the single-instance lock file."""
    return os.path.join(appdata_dir(), "netpulse.lock")
