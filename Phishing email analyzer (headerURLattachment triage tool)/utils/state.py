import json
import os
import uuid
from datetime import datetime, timezone

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "app_state.json")
REPORTS_DIR = os.path.join(APP_DIR, "reports")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)


class StateManager:
    def __init__(self, path: str = None):
        ensure_dirs()
        self.path = path or STATE_FILE
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"theme": "dark", "history": [], "max_history": 10}

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, default=str)
        except OSError:
            pass

    # theme --------------------------------------------------------- #
    @property
    def theme(self) -> str:
        return self.data.get("theme", "dark")

    def set_theme(self, theme: str):
        self.data["theme"] = theme
        self.save()

    # history ------------------------------------------------------- #
    def add_history(self, entry: dict):
        entry["id"] = entry.get("id") or uuid.uuid4().hex[:8]
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        history = self.data.setdefault("history", [])
        history.insert(0, entry)
        max_h = self.data.get("max_history", 10)
        del history[max_h:]
        self.save()

    @property
    def history(self) -> list:
        return self.data.get("history", [])