"""High-accuracy fixed-size ring buffer for live time-series data.

Stores (timestamp, value) pairs inside a preallocated numpy array with
``remaining()``-safe numpy searchsorted reads. Used for the rolling 60s live
graphs; unbounded memory growth is impossible by design.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class RingSeries:
    """A single named series (e.g. 'download') inside the ring buffer."""

    name: str
    capacity: int
    times: np.ndarray  # float64 unix seconds
    values: np.ndarray  # float64 (bytes/sec or raw counter)
    _head: int = 0  # next write index
    _count: int = 0

    @staticmethod
    def create(name: str, capacity: int) -> "RingSeries":
        """Allocate a series with capacity slots."""
        return RingSeries(
            name=name,
            capacity=capacity,
            times=np.full(capacity, np.nan, dtype=np.float64),
            values=np.full(capacity, np.nan, dtype=np.float64),
        )

    def append(self, ts: float, value: float) -> None:
        """Append one sample (overwrites the oldest when full)."""
        self.times[self._head] = ts
        self.values[self._head] = value
        self._head = (self._head + 1) % self.capacity
        if self._count < self.capacity:
            self._count += 1

    def window(self, seconds: float, now: float | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Return (times, values) for the window (now - seconds, now], oldest-first.

        Correctly unrolls the ring after it wraps (logical order is
        [head..capacity) + [0..head) once full).
        """
        if self._count == 0:
            return np.empty(0), np.empty(0)
        now = time.time() if now is None else now
        cutoff = now - seconds
        if self._count < self.capacity:
            times = self.times[: self._count]
            values = self.values[: self._count]
        else:
            times = np.concatenate((self.times[self._head :], self.times[: self._head]))
            values = np.concatenate((self.values[self._head :], self.values[: self._head]))
        mask = times > cutoff
        return times[mask], values[mask]


@dataclass
class RingBuffer:
    """Fixed-size multi-series ring buffer for live traffic data.

    One RingSeries per metric: download, upload, plus one per interface.
    """

    capacity: int
    series: dict[str, RingSeries] = field(default_factory=dict)
    _last_values: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def create(capacity: int = 4096) -> "RingBuffer":
        """Create a buffer pre-seeded with the global down/up series."""
        rb = RingBuffer(capacity=capacity)
        rb.series["download"] = RingSeries.create("download", capacity)
        rb.series["upload"] = RingSeries.create("upload", capacity)
        return rb

    def ensure_series(self, name: str) -> RingSeries:
        """Get or create a series by name (used for per-interface series)."""
        if name not in self.series:
            self.series[name] = RingSeries.create(name, self.capacity)
        return self.series[name]

    def append(self, name: str, ts: float | None = None, value: float = 0.0) -> None:
        """Append a value to a named series at optional timestamp."""
        self.ensure_series(name).append(time.time() if ts is None else ts, value)

    def window(self, name: str, seconds: float) -> tuple[np.ndarray, np.ndarray]:
        """Return (times, values) arrays for the recent window of a series."""
        series = self.series.get(name)
        if series is None:
            return np.empty(0), np.empty(0)
        return series.window(seconds)

    def last(self, name: str) -> float:
        """Most recent value of a series (0 when missing)."""
        series = self.series.get(name)
        if series is None or series._count == 0:
            return 0.0
        idx = (series._head - 1) % series.capacity
        v = series.values[idx]
        return 0.0 if np.isnan(v) else float(v)

    def count(self, name: str) -> int:
        """Number of stored samples in a series."""
        s = self.series.get(name)
        return 0 if s is None else s._count

    def prune(self, seconds: float) -> None:
        """Convenience no-op — capacity-bounded, nothing to prune."""
        return None


def deque_ring(maxlen: int) -> deque:
    """Simple bounded deque for scalar histories (sparklines etc.)."""
    return deque(maxlen=maxlen)
