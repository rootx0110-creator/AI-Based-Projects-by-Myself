"""In-memory metrics store: latest snapshot + ring buffers for the GUI.

The GUI never touches psutil directly; it reads from here (fast, lock-guarded)
and repaints from ring-buffer windows at ~10 FPS.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from capture.interface_sampler import Sample
from capture.ring_buffer import RingBuffer


@dataclass
class StatsStore:
    """Thread-safe latest-state + history holder."""

    buffer: RingBuffer = field(default_factory=lambda: RingBuffer.create(capacity=8192))
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _last: Sample | None = None
    _proc_snapshot: dict[int, Any] = field(default_factory=dict)

    def push_sample(self, sample: Sample) -> None:
        """Record one interface sample (called from the sampler thread)."""
        with self._lock:
            self._last = sample
            self.buffer.append("download", sample.ts, sample.total_down)
            self.buffer.append("upload", sample.ts, sample.total_up)
            for name, iface in sample.per_iface.items():
                self.buffer.append(f"iface:{name}", sample.ts, iface.down_bps + iface.up_bps)

    def push_processes(self, procs: dict[int, Any]) -> None:
        """Record one process-mapping snapshot (mapper thread)."""
        with self._lock:
            self._proc_snapshot = procs

    def last_sample(self) -> Sample | None:
        """Latest Sample or None."""
        with self._lock:
            return self._last

    def process_snapshot(self) -> dict[int, Any]:
        """Latest {pid: ProcessInfo} mapping."""
        with self._lock:
            return dict(self._proc_snapshot)

    def window(self, series: str, seconds: float) -> tuple[Any, Any]:
        """Ring-buffer window (times, values) for a series."""
        return self.buffer.window(series, seconds)

    def last_value(self, series: str) -> float:
        """Most recent value for a series."""
        return self.buffer.last(series)

    def uptime(self) -> float:
        """Seconds since store creation (info label)."""
        return time.time() - _START


_START = time.time()
