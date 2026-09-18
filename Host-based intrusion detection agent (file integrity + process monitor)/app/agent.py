import os
import threading
import time

from .alerts import AlertBus
from .config import load_config, save_config, DB_PATH
from .fim import FIMEngine
from .process_monitor import ProcessEngine, snapshot as process_snapshot
from .storage import Storage


class HIDSAgent:
    """Background agent tying FIM, process monitor and alerts together.

    Runs a single daemon worker thread that scans watched directories and
    snapshots running processes on their own independent intervals, raising
    alerts on drift.
    """

    def __init__(self):
        self.config = load_config()
        self.storage = Storage(DB_PATH)
        self.alerts = AlertBus(self.storage)
        self.fim = FIMEngine(self.storage, self.config)
        self.procs = ProcessEngine(self.storage, self.config)

        self.running = False
        self._thread = None
        self.paused = False

        # Live status shared with the UI (GIL makes this safe enough).
        self.last_scan = {"time": None, "ok": False, "changed": 0}
        self.last_snapshot = {"time": None, "count": 0, "new": 0}
        self.progress = {"state": "idle", "processed": 0, "total": 0, "label": ""}

        self._manual_fim = threading.Event()
        self._manual_proc = threading.Event()
        self._hog_state = {}
        self._known_new = set()
        self._last_fim = None
        self._last_proc = None
        self._lock = threading.RLock()

    # ---------------- lifecycle ----------------
    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="hids-worker")
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def toggle_pause(self):
        with self._lock:
            self.paused = not self.paused
        return self.paused

    # ---------------- public controls ----------------
    def request_fim_scan(self):
        self._manual_fim.set()

    def request_proc_snapshot(self):
        self._manual_proc.set()

    def reset_process_state(self):
        """Forget de-dup memory after the user manually rebuilds the whitelist."""
        with self._lock:
            self._hog_state.clear()
            self._known_new.clear()

    def reload_settings(self):
        cfg = load_config()
        with self._lock:
            self.config.clear()
            self.config.update(cfg)

    def save_settings(self, cfg):
        save_config(cfg)
        with self._lock:
            # Mutate the shared dict in place so FIM/ProcessEngine pick it up.
            self.config.clear()
            self.config.update(cfg)
            self._hog_state.clear()

    # ---------------- worker ----------------
    def _worker(self):
        first = True
        while self.running:
            try:
                if not self.paused:
                    if self.config.get("fim_enabled", True):
                        if first or self._fim_due() or self._manual_fim.is_set():
                            self._run_fim_pass(first)
                    if self.config.get("process_enabled", True):
                        if first or self._proc_due() or self._manual_proc.is_set():
                            self._run_proc_pass(first)
                first = False
            except Exception as exc:  # keep the loop alive
                self.alerts.notify(1, "agent", "Agent error", str(exc))

            # Manual events for disabled modules must be dropped or the loop
            # monitors them forever (busy-spin guard).
            if not self.config.get("fim_enabled", True):
                self._manual_fim.clear()
            if not self.config.get("process_enabled", True):
                self._manual_proc.clear()

            self._sleep_cycle()

    def _fim_due(self):
        last = self._last_fim or 0
        return (time.time() - last) >= self.config.get("scan_interval_sec", 300)

    def _proc_due(self):
        last = self._last_proc or 0
        return (time.time() - last) >= self.config.get("process_interval_sec", 60)

    def _sleep_cycle(self):
        now = time.time()
        due = []
        if self.config.get("fim_enabled", True):
            due.append(self.config.get("scan_interval_sec", 300) - (now - (self._last_fim or 0)))
        if self.config.get("process_enabled", True):
            due.append(self.config.get("process_interval_sec", 60) - (now - (self._last_proc or 0)))
        wait = max(min(due) if due else 30, 0.5)
        deadline = time.time() + min(wait, 3.0)
        while self.running and time.time() < deadline:
            if self._manual_fim.is_set() or self._manual_proc.is_set():
                return
            time.sleep(0.2)

    # ---------------- FIM pass ----------------
    def _run_fim_pass(self, first):
        self._manual_fim.clear()
        dirs = [d for d in self.config.get("fim_watch_dirs", []) if d and os.path.isdir(d)]
        if not dirs:
            if first:
                self.last_scan["time"] = time.time()
            return
        changed_total = 0
        for d in dirs:
            if self.storage.baseline_file_count(d) == 0:
                self._build_baseline(d, first)
            else:
                changed_total += self._scan(d)

        self._last_fim = time.time()
        self.last_scan["time"] = time.time()
        self.last_scan["ok"] = True
        self.last_scan["changed"] = changed_total
        self.progress.update(state="idle", processed=0, total=0, label="idle")

    def _build_baseline(self, d, first):
        self.progress.update(state="baseline", processed=0, total=0, label=f"Baseline: {d}")
        def cb(processed, total, curr):
            self.progress.update(state="baseline", processed=processed, total=total,
                                 label=os.path.basename(curr) if curr else "")
            return False
        res = self.fim.build_baseline(d, progress_cb=cb)
        sev = 1 if first else 2
        self.alerts.notify(sev, "fim", "Baseline created",
                           f"{d} -> {res.total} files hashed"
                           + (f", {res.skipped} skipped" if res.skipped else ""))

    def _scan(self, d):
        self.progress.update(state="scan", processed=0, total=0, label=f"Scanning: {d}")
        def cb(processed, total, curr):
            self.progress.update(state="scan", processed=processed, total=total,
                                 label=os.path.basename(curr) if curr else "")
            return False
        res = self.fim.scan(d, progress_cb=cb)

        for rel in res.added:
            self.alerts.notify(2, "fim", "File added", f"{d}\\{rel}")
        for rel in res.modified:
            self.alerts.notify(2, "fim", "File modified", f"{d}\\{rel}")
        for rel in res.removed:
            self.alerts.notify(3, "fim", "File removed", f"{d}\\{rel}")
        if res.changed:
            self.alerts.notify(
                1, "fim",
                "Scan summary",
                f"{d}: {len(res.added)} added, {len(res.modified)} modified, "
                f"{len(res.removed)} removed, {res.unchanged} unchanged",
            )
        return res.changed

    # ---------------- process pass ----------------
    def _run_proc_pass(self, first):
        self._manual_proc.clear()
        rows = process_snapshot()

        new_alerts = 0
        if not first:
            new = self.procs.new_processes(rows)
            for r in new:
                if r["key"] in self._known_new:
                    continue
                self._known_new.add(r["key"])
                detail = r["exe"] or f"pid {r['pid']}, {r['name']}, user {r['user']}"
                self.alerts.notify(2, "process", "New process detected", detail)
                new_alerts += 1

            current_hogs = set()
            for r, kind, val in self.procs.resource_hogs(rows):
                mark = (r["pid"], kind)
                current_hogs.add(mark)
                if mark in self._hog_state:
                    continue
                title = "High CPU usage" if kind == "cpu" else "High memory usage"
                unit = "%" if kind == "cpu" else " MB"
                self.alerts.notify(2, "process", title,
                                   f"{r['name']} (pid {r['pid']}): {val}{unit}")
            self._hog_state = {m: True for m in current_hogs}

        # Whitelist re-learns every pass when auto-learn is on; otherwise it stays
        # static until the user rebuilds it from the Processes screen.
        if first or self.config.get("auto_whitelist_processes", True):
            self.procs.update_whitelist(rows)

        self._last_proc = time.time()
        self.last_snapshot["time"] = time.time()
        self.last_snapshot["count"] = len(rows)
        self.last_snapshot["new"] = new_alerts

    # ---------------- queries for UI ----------------
    def watch_dirs(self):
        return self.config.get("fim_watch_dirs", [])

    def add_watch_dir(self, path):
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            raise ValueError("Directory does not exist")
        dirs = self.watch_dirs()
        flat = {os.path.normcase(p) for p in dirs}
        if os.path.normcase(path) in flat:
            return False
        with self._lock:
            self.config["fim_watch_dirs"] = dirs + [path]
            save_config(self.config)
        return True

    def remove_watch_dir(self, path):
        dirs = self.watch_dirs()
        kept = [d for d in dirs if os.path.normcase(d) != os.path.normcase(path)]
        changed = len(kept) != len(dirs)
        if changed:
            with self._lock:
                self.config["fim_watch_dirs"] = kept
                save_config(self.config)
                self.storage.clear_baseline(path)
        return changed