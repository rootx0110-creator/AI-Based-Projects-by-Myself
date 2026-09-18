"""Thread-safe JSON persistence for SeaSim.

One JSON file on disk (see constants.DATA_FILE). Writes are atomic
(tmp file + os.replace) and debounced so bulk UI operations do not
hammer the disk. A background autosave timer flushes pending changes.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List

from seasim.constants import DATA_FILE
from seasim.engine.models import (
    AppSettings, Campaign, CampaignEvent, EmailTemplate, Participant,
)


class Store:
    """Holds all application state and persists it as one JSON document."""

    SCHEMA = 2

    def __init__(self, path: Path = DATA_FILE) -> None:
        self.path = Path(path)
        self.lock = threading.RLock()

        self.participants: Dict[str, Participant] = {}
        self.templates: Dict[str, EmailTemplate] = {}
        self.campaigns: Dict[str, Campaign] = {}
        self.events: Dict[str, CampaignEvent] = {}
        self.settings = AppSettings()
        self.schema_version: int = self.SCHEMA
        self.created: str = ""
        self.updated_at: str = ""

        self._dirty = False
        self._last_save = 0.0
        self._listeners: List[Callable[[str], None]] = []
        self.load()

    # -- listeners ---------------------------------------------------------

    def add_listener(self, cb: Callable[[str], None]) -> None:
        """Register callback(change: str) fired after any data mutation."""
        self._listeners.append(cb)

    def _notify(self, change: str = "data") -> None:
        for cb in list(self._listeners):
            try:
                cb(change)
            except Exception:
                pass

    # -- persistence ---------------------------------------------------------

    def load(self) -> None:
        with self.lock:
            if not self.path.exists():
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                # Corrupt file: keep a backup aside, start clean.
                try:
                    self.path.rename(self.path.with_suffix(".corrupt.bak"))
                except OSError:
                    pass
                return
            self.schema_version = int(raw.get("schema_version", 1))
            self.created = raw.get("created", "")
            self.updated_at = raw.get("updated_at", "")
            self.participants = {
                k: Participant.from_dict(v)
                for k, v in raw.get("participants", {}).items()
            }
            self.templates = {
                k: EmailTemplate.from_dict(v)
                for k, v in raw.get("templates", {}).items()
            }
            self.campaigns = {
                k: Campaign.from_dict(v)
                for k, v in raw.get("campaigns", {}).items()
            }
            self.events = {
                k: CampaignEvent.from_dict(v)
                for k, v in raw.get("events", {}).items()
            }
            self.settings = AppSettings.from_dict(raw.get("settings", {}))

    def mark_dirty(self) -> None:
        with self.lock:
            self._dirty = True

    def save(self, force: bool = False) -> None:
        """Write to disk if dirty (or forced). Cheap when already clean."""
        with self.lock:
            now = time.time()
            if not force and (not self._dirty or now - self._last_save < 0.5):
                return
            self._dirty = False
            self._last_save = now

            doc = self._to_doc()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(f".tmp-{uuid.uuid4().hex[:8]}")
            tmp.write_text(
                json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8",
            )
            os.replace(tmp, self.path)          # atomic on Windows

    def autosave_tick(self) -> None:
        """Called periodically by the app loop."""
        self.save(force=False)

    def _to_doc(self) -> Dict[str, Any]:
        from seasim.engine.models import now_iso

        self.updated_at = now_iso()
        return {
            "schema_version": self.schema_version,
            "created": self.created or self.updated_at,
            "updated_at": self.updated_at,
            "settings": self.settings.to_dict(),
            "participants": {k: p.to_dict() for k, p in self.participants.items()},
            "templates": {k: t.to_dict() for k, t in self.templates.items()},
            "campaigns": {k: c.to_dict() for k, c in self.campaigns.items()},
            "events": {k: e.to_dict() for k, e in self.events.items()},
        }

    # -- import / export (full JSON documents) ------------------------------

    def export_json(self) -> str:
        with self.lock:
            return json.dumps(self._to_doc(), indent=2, ensure_ascii=False)

    def import_json(self, text: str) -> int:
        """Replace state from a JSON document. Returns item count loaded."""
        raw = json.loads(text)
        if not isinstance(raw, dict) or "participants" not in raw:
            raise ValueError("Not a SeaSim export file.")
        with self.lock:
            self.schema_version = int(raw.get("schema_version", 1))
            self.created = raw.get("created", "")
            self.settings = AppSettings.from_dict(raw.get("settings", {}))
            self.participants = {
                k: Participant.from_dict(v)
                for k, v in raw.get("participants", {}).items()
            }
            self.templates = {
                k: EmailTemplate.from_dict(v)
                for k, v in raw.get("templates", {}).items()
            }
            self.campaigns = {
                k: Campaign.from_dict(v)
                for k, v in raw.get("campaigns", {}).items()
            }
            self.events = {
                k: CampaignEvent.from_dict(v)
                for k, v in raw.get("events", {}).items()
            }
            n = (len(self.participants) + len(self.templates)
                 + len(self.campaigns) + len(self.events))
        self.save(force=True)
        self._notify("reset")
        return n

    # -- helpers -------------------------------------------------------------

    def reset_all(self) -> None:
        """Wipe all data (keeps builtin templates re-seeded by caller)."""
        with self.lock:
            self.participants.clear()
            self.campaigns.clear()
            self.events.clear()
            self.settings = AppSettings()
        self.save(force=True)
        self._notify("reset")

    def participants_sorted(self) -> List[Participant]:
        with self.lock:
            return sorted(self.participants.values(), key=lambda p: p.name.lower())

    def campaigns_sorted(self) -> List[Campaign]:
        with self.lock:
            return sorted(self.campaigns.values(),
                          key=lambda c: c.created, reverse=True)

    def events_for(self, campaign_id: str) -> List[CampaignEvent]:
        with self.lock:
            return [e for e in self.events.values()
                    if e.campaign_id == campaign_id]
