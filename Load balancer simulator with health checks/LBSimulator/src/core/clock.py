"""Monotonic and wall clock helpers for deterministic timing."""

import time
from typing import Callable

class Clock:
    """Dual clock: monotonic for intervals, wall for timestamps."""

    _mono = time.perf_counter
    _wall = time.time

    @classmethod
    def monotonic(cls) -> float:
        """Return monotonic time in seconds."""
        return cls._mono()

    @classmethod
    def wall(cls) -> float:
        """Return wall-clock time as Unix timestamp."""
        return cls._wall()

    @classmethod
    def elapsed(cls, start: float) -> float:
        """Seconds since `start` (monotonic)."""
        return cls.monotonic() - start

    @classmethod
    def now_iso(cls) -> str:
        """ISO timestamp from wall clock."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
