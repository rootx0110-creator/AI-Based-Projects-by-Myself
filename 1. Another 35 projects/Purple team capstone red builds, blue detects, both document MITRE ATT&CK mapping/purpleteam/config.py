"""Path and runtime configuration.

Important: when launched as a PyInstaller one-file executable, ``sys.frozen``
is set and all writes must go to a *writable* location. We prefer the folder
next to the executable; if that is not writable we fall back to the user's
local app-data folder so report download and lab sandbox always work.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from . import APP_NAME, APP_SLUG


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """Directory the app is running from (exe dir or source dir)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _base_dir() -> Path:
    if is_frozen():
        bundled = Path(sys.executable).resolve().parent
        try:
            probe = bundled / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return bundled
        except OSError:
            pass
        return Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / APP_SLUG
    return bundle_root()


BASE_DIR = _base_dir()
"""Root the tool writes its data to (exe dir, or LocalAppData when not writable)."""

OUTPUTS_DIR = BASE_DIR / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
LAB_TARGET_DIR = OUTPUTS_DIR / "lab_target"
SESSION_FILE = OUTPUTS_DIR / "last_session.json"

RESOURCE_DIR = bundle_root() / "assets"
DOCS_DIR = bundle_root() / "docs"

FILE_INDEX = LAB_TARGET_DIR / ".purpleteam_index.json"
"""Sidecar index that makes the scan engine fast and deterministic."""

MAX_EXFIL_BYTES = 4096
EXFIL_LISTEN_PORT = ("127.0.0.1", 0)  # ephemeral local port, bind below


def ensure_dirs() -> None:
    for p in (OUTPUTS_DIR, REPORTS_DIR, LAB_TARGET_DIR):
        p.mkdir(parents=True, exist_ok=True)


def default_icon() -> Path:
    for cand in (RESOURCE_DIR / "purpleteam.ico", bundle_root() / "purpleteam.ico"):
        if cand.exists():
            return cand
    return RESOURCE_DIR / "purpleteam.ico"