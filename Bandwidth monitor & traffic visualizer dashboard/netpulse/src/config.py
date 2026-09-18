"""Configuration load/save with defaults, deep-merge and atomic writes.

Config lives at %APPDATA%/NetPulse/config.json.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from typing import Any

from utils.paths import config_path

log = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "sample_interval_ms": 500,          # 100..1000, interface polling period
    "process_interval_ms": 2000,        # per-process scan period
    "db_flush_seconds": 10,             # batched DB write period
    "history_window_seconds": 60,       # rolling window of live graphs
    "theme": "dark",                    # 'dark' | 'light'
    "speed_alert_threshold_mbps": 50.0,
    "speed_alert_window_seconds": 10,
    "new_conn_alert_processes": [],     # process names (lowercase) to watch
    "quota": {
        "enabled": False,
        "name": "Monthly plan",
        "period": "monthly",            # 'daily' | 'monthly'
        "limit_bytes": 100 * 1000 * 1000 * 1000,
    },
    "warn_levels": [0.8, 0.95, 1.0],
    "hud": {
        "enabled": False,
        "x": 120,
        "y": 120,
        "opacity": 0.85,
        "always_on_top": True,
    },
    "minimize_to_tray": True,
    "excluded_interfaces": [],          # e.g. ['Loopback Pseudo-Interface 1']
}

_lock = threading.Lock()


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a deep merge of override into base (override wins, dicts merge)."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class Config:
    """Thread-safe JSON config with defaults and atomic persistence."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    # -- persistence ---------------------------------------------------

    def load(self) -> None:
        """Load config from disk, merging over defaults (missing keys filled)."""
        with _lock:
            data = dict(DEFAULTS)
            path = config_path()
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        data = deep_merge(data, loaded)
                except Exception as exc:
                    log.error("Failed to read config %s: %s", path, exc)
            self._data = data

    def save(self) -> None:
        """Atomically write config to disk (tmp file + replace)."""
        with _lock:
            path = config_path()
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(self._data, fh, indent=2)
                os.replace(tmp, path)
            except Exception as exc:
                log.error("Failed to save config %s: %s", path, exc)

    # -- accessors -----------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level config value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a top-level config value (call save() to persist)."""
        self._data[key] = value

    @property
    def data(self) -> dict[str, Any]:
        """Read-only view of the whole config dict."""
        return dict(self._data)

    # convenience properties -------------------------------------------

    @property
    def sample_interval_ms(self) -> int:
        """Interface sampling interval in ms, clamped to 100..1000."""
        try:
            value = int(self._data.get("sample_interval_ms", 500))
        except (TypeError, ValueError):
            value = 500
        return max(100, min(1000, value))

    @property
    def theme(self) -> str:
        """Current theme name ('dark' or 'light')."""
        return str(self._data.get("theme", "dark"))

    @theme.setter
    def theme(self, value: str) -> None:
        """Set theme name."""
        self._data["theme"] = value
