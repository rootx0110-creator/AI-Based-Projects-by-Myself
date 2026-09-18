"""Human-readable formatting helpers."""
from __future__ import annotations


def fmt_speed(bps: float) -> str:
    """Format bits-per-second as 'x.xx Mbps' / 'x.x Gbps' / 'x.x Kbps'."""
    if bps >= 1e9:
        return f"{bps / 1e9:.2f} Gbps"
    if bps >= 1e6:
        return f"{bps / 1e6:.2f} Mbps"
    if bps >= 1e3:
        return f"{bps / 1e3:.1f} Kbps"
    return f"{max(bps, 0):.0f} bps"


def fmt_bytes(b: float) -> str:
    """Format a byte count as B / KB / MB / GB / TB (decimal)."""
    value = float(max(b, 0))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1000 or unit == "TB":
            return f"{value:,.0f} {unit}" if unit == "B" else f"{value:,.2f} {unit}"
        value /= 1000
    return f"{value:,.2f} TB"


def fmt_duration(seconds: float) -> str:
    """Format seconds as '1h 02m', '3m 04s' or '12s'."""
    seconds = int(max(seconds, 0))
    if seconds >= 3600:
        return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds}s"


def fmt_pct(p: float) -> str:
    """Format 0..1 fraction as a percentage string."""
    return f"{p * 100:.0f}%"
