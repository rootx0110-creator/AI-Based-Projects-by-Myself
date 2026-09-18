"""Metrics: counters, sliding histograms, percentile estimation."""

from collections import deque
import math
from typing import List

class SlidingHistogram:
    """Tracks latency samples with sliding window for percentile computation."""

    def __init__(self, window_size: int = 500) -> None:
        self._window = deque(maxlen=window_size)

    def add(self, value_ms: float) -> None:
        if value_ms >= 0:
            self._window.append(value_ms)

    def percentile(self, p: float) -> float:
        if not self._window:
            return 0.0
        data = sorted(self._window)
        idx = int(math.ceil(p / 100.0 * len(data))) - 1
        idx = max(0, min(idx, len(data) - 1))
        return data[idx]

    def avg(self) -> float:
        if not self._window:
            return 0.0
        return sum(self._window) / len(self._window)

    def count(self) -> int:
        return len(self._window)

    def clear(self) -> None:
        self._window.clear()
