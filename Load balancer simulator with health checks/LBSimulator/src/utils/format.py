"""Formatting utilities for display."""

def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def fmt_latency(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.1f}ms"
    return f"{ms/1000:.2f}s"

def fmt_rate(rps: float) -> str:
    return f"{rps:,.1f} req/s"

def fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"
