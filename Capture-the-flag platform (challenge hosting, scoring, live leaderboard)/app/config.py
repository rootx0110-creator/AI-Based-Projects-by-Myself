"""Central configuration for the CTF platform."""
import os
import sys


def _base_dir() -> str:
    """Directory where runtime files live.

    - Frozen EXE (PyInstaller --onefile): the folder containing the EXE,
      so data/ persists between runs (sys._MEIPASS is a read-only temp dir).
    - Normal Python: the project root.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _base_dir()

# Runtime data directory (in _MEIPASS bundles this would be read-only, so keep data outside)
DATA_DIR = os.environ.get("CTF_DATA_DIR") or os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "ctf_db.json")

SECRET_KEY = os.environ.get("CTF_SECRET_KEY", "ctf-platform-dev-secret-change-me")

HOST = os.environ.get("CTF_HOST", "127.0.0.1")
PORT = int(os.environ.get("CTF_PORT", "5000"))
DEBUG = os.environ.get("CTF_DEBUG", "0") == "1"

# Scoring rules
DYNAMIC_SLOPE = 100        # points lost per solve beyond the first (dynamic scoring)
DYNAMIC_MINIMUM = 50       # floor value for dynamic challenges
MAX_SUBMISSIONS = 0        # 0 = unlimited attempts per challenge
HIDE_SOLVES_UNTIL_END = False

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # change after first login; stored hashed in DB
