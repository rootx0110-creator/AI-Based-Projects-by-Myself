"""Quota tracking: usage windows, warn levels and reset logic."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger(__name__)


class QuotaLevel(Enum):
    """Severity of the current quota state."""

    OK = "ok"
    WARN = "warn"  # >= 80%
    CRIT = "crit"  # >= 95%
    EXCEEDED = "exceeded"  # >= 100%


@dataclass
class QuotaState:
    """Snapshot of a quota at a point in time."""

    name: str
    period: str  # 'daily' | 'monthly'
    limit_bytes: int
    used_bytes: int
    level: QuotaLevel
    warn_levels: tuple[float, ...] = (0.8, 0.95, 1.0)

    @property
    def ratio(self) -> float:
        """Used/limit fraction (0 when the limit is 0)."""
        return self.used_bytes / self.limit_bytes if self.limit_bytes else 0.0

    @property
    def remaining_bytes(self) -> int:
        """Bytes left before the limit (0 when exceeded)."""
        return max(0, self.limit_bytes - self.used_bytes)


class QuotaTracker:
    """Tracks a single daily or monthly byte quota from DB totals."""

    def __init__(self, name: str, period: str, limit_bytes: int, warn_levels: tuple[float, ...] = (0.8, 0.95, 1.0)) -> None:
        self.name = name
        self.period = period if period in ("daily", "monthly") else "monthly"
        self.limit_bytes = int(limit_bytes)
        self.warn_levels = warn_levels
        self.fired_levels: set[float] = set()
        self.last_reset = time.time()

    def reset_window(self) -> None:
        """Clear fired alerts and mark the window start (call at rollover)."""
        self.fired_levels.clear()
        self.last_reset = time.time()

    def evaluate(self, used_bytes: int) -> QuotaState:
        """Classify current usage and remember which warn levels have fired."""
        ratio = used_bytes / self.limit_bytes if self.limit_bytes else 0.0
        level = QuotaLevel.OK
        for threshold in sorted(self.warn_levels):
            if ratio >= threshold:
                if threshold >= 1.0:
                    level = QuotaLevel.EXCEEDED
                elif threshold >= 0.95:
                    level = QuotaLevel.CRIT
                else:
                    level = QuotaLevel.WARN
        return QuotaState(
            name=self.name,
            period=self.period,
            limit_bytes=self.limit_bytes,
            used_bytes=used_bytes,
            level=level,
            warn_levels=self.warn_levels,
        )

    def should_alert(self, state: QuotaState) -> bool:
        """True once per warn level per window (no alert spam)."""
        thresholds = sorted(self.warn_levels)
        for threshold, lvl in zip(thresholds, (QuotaLevel.WARN, QuotaLevel.CRIT, QuotaLevel.EXCEEDED)):
            if state.level == lvl and threshold not in self.fired_levels:
                self.fired_levels.add(threshold)
                return True
        return False

    @staticmethod
    def window_start_ts(period: str, now: float | None = None) -> float:
        """Start timestamp of the current daily/monthly window (local time)."""
        now = time.time() if now is None else now
        lt = time.localtime(now)
        if period == "daily":
            start = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
        else:
            start = time.mktime((lt.tm_year, lt.tm_mon, 1, 0, 0, 0, 0, 0, -1))
        return start
