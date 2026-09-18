"""Central constants for SeaSim.

Single source of truth for app identity, data locations, rate limits,
and safety caps. Everything else imports from here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "SeaSim"
APP_TITLE = "SeaSim - Social Engineering Awareness Simulator"
APP_VERSION = "1.0.0"
ORG_DEFAULT = "Your Organization"

# ---------------------------------------------------------------------------
# Data location: everything lives under %LOCALAPPDATA%/SeaSim on Windows so
# the packaged exe never writes next to itself (Program Files is read-only).
# Override with SEASIM_DATA_DIR for portable/dev use.
# ---------------------------------------------------------------------------


def _data_root() -> Path:
    override = os.environ.get("SEASIM_DATA_DIR", "").strip()
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "SeaSim"
    return Path.home() / ".seasim"


DATA_DIR: Path = _data_root()
DATA_FILE: Path = DATA_DIR / "seasim_data.json"
LOG_FILE: Path = DATA_DIR / "seasim.log"

# ---------------------------------------------------------------------------
# Safety envelope (see seasim/safety.py)
# ---------------------------------------------------------------------------

MAX_RECIPIENTS = 500          # hard cap per launch
WARN_RECIPIENTS = 100         # confirmation threshold (Step 6 of wizard)
RATE_PER_MINUTE = 60          # scheduler batch ceiling
DELIVERY_RUN_SECONDS = 30     # one simulated send window per run
MAX_CAMPAIGNS = 200           # store housekeeping cap

# ---------------------------------------------------------------------------
# Local mailer (stub SMTP on localhost:8025 - never a real relay)
# ---------------------------------------------------------------------------

SMTP_HOST = "127.0.0.1"
SMTP_PORT = 8025
SMTP_SENDER = "security-awareness@seasim.local"
SMTP_FROM_NAME = "Security Awareness"

# ---------------------------------------------------------------------------
# UI metrics
# ---------------------------------------------------------------------------

WINDOW_MIN_W = 1080
WINDOW_MIN_H = 680
WINDOW_DEFAULT_W = 1280
WINDOW_DEFAULT_H = 800
SIDEBAR_W = 216
