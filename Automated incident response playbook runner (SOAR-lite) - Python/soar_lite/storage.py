"""Threaded atomic JSON storage for SOAR-Lite.

Design notes
------------
* Every collection is one JSON document on disk.
* Writes are atomic (tmp file + os.replace) so a crash can never leave a
  half-written document.
* Each collection has its own RLock; engine workers and the API layer share a
  single Store instance so reads are consistent with in-flight runs.
"""

import json
import os
import shutil
import threading
import time


class Store:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.report_cache = os.path.join(data_dir, "report_cache")
        self.backup_dir = os.path.join(data_dir, "backups")
        for d in (data_dir, self.report_cache, self.backup_dir):
            os.makedirs(d, exist_ok=True)

        self._locks = {}
        self.collections = {"incidents": [], "executions": [], "iocs": [], "settings": {}}
        self._load_all()

    # ---------------------------------------------------------- low level
    def _lock(self, name):
        if name not in self._locks:
            self._locks[name] = threading.RLock()
        return self._locks[name]

    def _path(self, name):
        return os.path.join(self.data_dir, f"{name}.json")

    def _load_all(self):
        for name, default in self.collections.items():
            self.collections[name] = self._read_json(name, default)

    def _read_json(self, name, default):
        path = self._path(name)
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return default

    def _write_json(self, name, data):
        path = self._path(name)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    # ---------------------------------------------------------- accessors
    def get(self, name):
        with self._lock(name):
            return self.collections[name]

    def update(self, name, new_value):
        with self._lock(name):
            self.collections[name] = new_value
            self._write_json(name, new_value)

    def mutate(self, name, fn):
        """Atomically apply fn(collection) -> new collection, then persist."""
        with self._lock(name):
            coll = self.collections[name]
            changed, new_coll = fn(coll)
            if changed:
                self.collections[name] = new_coll
                self._write_json(name, new_coll)
            return new_coll

    def find(self, name, predicate_or_id):
        coll = self.get(name)
        if isinstance(predicate_or_id, str) or isinstance(predicate_or_id, int):
            target = str(predicate_or_id)
            for item in coll:
                if str(item.get("id")) == target:
                    return item
            return None
        for item in coll:
            if predicate_or_id(item):
                return item
        return None

    # ---------------------------------------------------------- recovery
    def recover(self):
        """Mark interrupted executions as failed so the queue is never stuck."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        def fix(coll):
            changed = False
            for ex in coll:
                if ex.get("status") in ("queued", "running"):
                    ex["status"] = "failed"
                    ex["finished_at"] = now
                    ex["was_interrupted"] = True
                    ex.setdefault("notes", []).append({
                        "ts": now, "by": "system",
                        "text": "Execution interrupted by restart; marked failed on recovery.",
                    })
                    changed = True
            return changed, coll

        self.mutate("executions", fix)

    # ---------------------------------------------------------- reset
    def reset(self, reseed_fn=None):
        """Backup current data, start fresh, optionally re-seed."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = os.path.join(self.backup_dir, stamp)
        os.makedirs(dest, exist_ok=True)
        for name in self.collections:
            src = self._path(name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dest, f"{name}.json"))
        for name, default in self.collections.items():
            self.update(name, default)
        if reseed_fn:
            reseed_fn()
        return dest

    # ---------------------------------------------------------- util
    def seq_no(self, prefix):
        """Return a human sequence number e.g. 12 for INC-2026-0012."""
        with self._lock("_seq"):
            key = "_seq"
            path = os.path.join(self.data_dir, ".seq.json")
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    seq = json.load(fh)
            except Exception:
                seq = {}
            nxt = seq.get(prefix, 0) + 1
            seq[prefix] = nxt
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(seq, fh)
            return nxt


def utcnow():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())