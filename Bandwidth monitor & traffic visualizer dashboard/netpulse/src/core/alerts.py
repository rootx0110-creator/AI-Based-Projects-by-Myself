"""Alert engine: speed-threshold and new-connection alerts (quota in analytics.quota).

All decisions happen here; the GUI (toast) and tray (balloon) subscribe to the
event bus signals. Deduping keeps alerts from spamming every tick.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Callable

log = logging.getLogger(__name__)


class AlertEngine:
    """Evaluates alert rules against incoming samples and emits via callbacks."""

    def __init__(
        self,
        speed_threshold_mbps: float = 50.0,
        speed_window_seconds: float = 10.0,
        watched_processes: list[str] | None = None,
    ) -> None:
        self.speed_threshold_mbps = speed_threshold_mbps
        self.speed_window_seconds = speed_window_seconds
        self.watched = {w.lower() for w in (watched_processes or [])}
        self._recent: deque[tuple[float, float]] = deque()  # (ts, mbps)
        self._last_speed_alert = 0.0
        self._seen_remotes: dict[str, set[str]] = {}
        self._lock = threading.Lock()
        self.on_speed_alert: Callable[[float, str], None] | None = None
        self.on_new_connection: Callable[[str, str], None] | None = None

    # -- speed -----------------------------------------------------------

    def check_speed(self, ts: float, down_mbps: float) -> None:
        """Track recent speeds and fire a sustained-threshold alert."""
        with self._lock:
            self._recent.append((ts, down_mbps))
            cutoff = ts - self.speed_window_seconds
            while self._recent and self._recent[0][0] < cutoff:
                self._recent.popleft()
            sustained = len(self._recent) >= 3 and all(m >= self.speed_threshold_mbps for _, m in self._recent)
        if sustained and ts - self._last_speed_alert > self.speed_window_seconds:
            self._last_speed_alert = ts
            if self.on_speed_alert:
                try:
                    self.on_speed_alert(
                        down_mbps * 1e6,
                        f"Download sustained above {self.speed_threshold_mbps:.0f} Mbps for {self.speed_window_seconds:.0f}s",
                    )
                except Exception:
                    log.exception("speed alert callback failed")

    # -- watched processes -------------------------------------------------

    def check_processes(self, procs: dict) -> None:
        """Detect brand-new remote connections for watched process names."""
        for info in procs.values():
            name = (getattr(info, "name", "") or "").lower()
            if name not in self.watched:
                continue
            for conn in getattr(info, "new_connections", []):
                remote = getattr(conn, "remote", "-")
                with self._lock:
                    seen = self._seen_remotes.setdefault(name, set())
                    if remote in seen:
                        continue
                    seen.add(remote)
                if self.on_new_connection:
                    try:
                        self.on_new_connection(info.name, remote)
                    except Exception:
                        log.exception("new-connection callback failed")

    def reconfigure(
        self,
        speed_threshold_mbps: float | None = None,
        speed_window_seconds: float | None = None,
        watched_processes: list[str] | None = None,
    ) -> None:
        """Update rules at runtime (Settings tab)."""
        if speed_threshold_mbps is not None:
            self.speed_threshold_mbps = speed_threshold_mbps
        if speed_window_seconds is not None:
            self.speed_window_seconds = speed_window_seconds
        if watched_processes is not None:
            self.watched = {w.lower() for w in watched_processes}
            self._seen_remotes.clear()
