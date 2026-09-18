"""Small human-readable formatting helpers (GUI + logs)."""

from __future__ import annotations

import datetime as _dt


def fmt_bytes(n: float) -> str:
    n = float(max(n, 0))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1024.0
    return f"{n:,.1f} TB"


def fmt_rate(bytes_per_second: float) -> str:
    return f"{fmt_bytes(bytes_per_second)}/s"


def fmt_uptime(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def fmt_clock() -> str:
    return _dt.datetime.now().strftime("%H:%M:%S")
