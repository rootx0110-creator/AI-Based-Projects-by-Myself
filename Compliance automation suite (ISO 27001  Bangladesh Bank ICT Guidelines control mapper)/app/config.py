"""Application configuration."""

import os
import sys

APP_NAME = "Compliance Automation Suite"
APP_VERSION = "1.0.0"

# When frozen by PyInstaller, resource files live in sys._MEIPASS
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ComplianceSuite")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

STATE_FILE = os.path.join(DATA_DIR, "state.json")
DB_FILE = os.path.join(DATA_DIR, "compliance_data.json")
