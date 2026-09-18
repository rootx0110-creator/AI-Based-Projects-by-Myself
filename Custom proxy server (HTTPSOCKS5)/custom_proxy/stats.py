"""Thread-safe traffic statistics with a rolling rate history."""

from __future__ import annotations

import collections
import threading
import time

from .constants import HISTORY_SECONDS, STATS_INTERVAL


class Stats:
    """All mutations happen on the proxy loop thread; snapshot() is safe from any thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_locked()

    def _reset_locked(self) -> None:
        self.requests = 0
        self.errors = 0
        self.active = 0
        self.total_opened = 0
        self.bytes_in = 0
        self.bytes_out = 0
        self._prev_in = 0
        self._prev_out = 0
        self.rate_in = 0.0
        self.rate_out = 0.0
        self.history: collections.deque = collections.deque(maxlen=HISTORY_SECONDS)
        self.started_at: float | None = None

    def reset(self) -> None:
        with self._lock:
            self._reset_locked()

    def mark_started(self) -> None:
        with self._lock:
            self.started_at = time.monotonic()

    # ------------------------------------------------------------- counters
    def conn_opened(self) -> None:
        with self._lock:
            self.active += 1
            self.total_opened += 1

    def conn_closed(self) -> None:
        with self._lock:
            self.active = max(0, self.active - 1)

    def add_traffic(self, n_in: int, n_out: int) -> None:
        with self._lock:
            self.bytes_in += n_in
            self.bytes_out += n_out

    def add_request(self) -> None:
        with self._lock:
            self.requests += 1

    def add_error(self) -> None:
        with self._lock:
            self.errors += 1

    # ------------------------------------------------------------- sampling
    def sample(self) -> None:
        with self._lock:
            self.rate_in = (self.bytes_in - self._prev_in) / STATS_INTERVAL
            self.rate_out = (self.bytes_out - self._prev_out) / STATS_INTERVAL
            self._prev_in = self.bytes_in
            self._prev_out = self.bytes_out
            self.history.append((self.rate_in / 1024.0, self.rate_out / 1024.0))

    def snapshot(self) -> dict:
        with self._lock:
            uptime = (time.monotonic() - self.started_at) if self.started_at else 0.0
            return {
                "requests": self.requests,
                "active": self.active,
                "total_opened": self.total_opened,
                "errors": self.errors,
                "bytes_in": self.bytes_in,
                "bytes_out": self.bytes_out,
                "rate_in": self.rate_in,
                "rate_out": self.rate_out,
                "uptime": uptime,
                "history": tuple(self.history),
            }
