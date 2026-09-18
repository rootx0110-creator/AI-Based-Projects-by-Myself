import os
import sys

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FROZEN = bool(getattr(sys, "frozen", False))

# Read-only app assets (templates/static) live in the PyInstaller bundle.
APP_ROOT = getattr(sys, "_MEIPASS", _BASE_DIR) if FROZEN else _BASE_DIR


def _data_root():
    """Writable folder for database/captures/reports.

    - Source mode: the project folder.
    - Frozen (exe): the folder next to the exe, falling back to %APPDATA% if the
      exe folder is not writable (e.g. installed under Program Files).
    """
    if not FROZEN:
        return _BASE_DIR
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    probe = os.path.join(exe_dir, ".auditor_write_test")
    try:
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("")
        os.remove(probe)
        return exe_dir
    except OSError:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "WirelessNetworkAuditor")


def _get(name, default):
    return os.environ.get(name, default)


class Config:
    DATA_DIR = _data_root()
    HOST = _get("AUDITOR_HOST", "127.0.0.1")
    PORT = int(_get("AUDITOR_PORT", "5001"))
    ENGINE = _get("AUDITOR_ENGINE", "simulation").lower()
    IFACE = _get("AUDITOR_IFACE", "wlan0")
    DB_PATH = os.path.join(DATA_DIR, _get("AUDITOR_DB", "database/settings.db"))
    CAPTURE_DIR = os.path.join(DATA_DIR, _get("AUDITOR_CAPTURE_DIR", "captures"))
    OUT_DIR = os.path.join(DATA_DIR, _get("AUDITOR_OUT_DIR", "reports/out"))
    TEMPLATE_DIR = os.path.join(APP_ROOT, "templates")
    STATIC_DIR = os.path.join(APP_ROOT, "static")
    SECRET_KEY = _get("AUDITOR_SECRET", "auditor-lab-secret-key-change-me")
    APP_NAME = "Wireless Network Auditor"
    VERSION = "1.0.0"

    @staticmethod
    def ensure_dirs():
        for d in (Config.CAPTURE_DIR, Config.OUT_DIR,
                  os.path.dirname(Config.DB_PATH)):
            os.makedirs(d, exist_ok=True)


def log(msg):
    """Print safe to call under PyInstaller --windowed (stdout may be None).
    Also appends to <DATA_DIR>/auditor.log so the exe produces a trace."""
    try:
        print(msg)
    except Exception:
        pass
    try:
        path = os.path.join(Config.DATA_DIR, "auditor.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(str(msg) + "\n")
    except Exception:
        pass