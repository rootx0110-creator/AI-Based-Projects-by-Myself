"""Network unit conversions (bytes/sec <-> bits/sec <-> Mbps)."""
from __future__ import annotations

BPS_PER_MBPS = 1_000_000.0


def bytes_to_bps(bytes_per_sec: float) -> float:
    """Convert bytes per second to bits per second."""
    return bytes_per_sec * 8.0


def bps_to_mbps(bps: float) -> float:
    """Convert bits per second to megabits per second."""
    return bps / BPS_PER_MBPS


def bytes_per_sec_to_mbps(bytes_per_sec: float) -> float:
    """Convert bytes/sec directly to megabits/sec."""
    return bps_to_mbps(bytes_to_bps(bytes_per_sec))


def bytes_to_megabytes(b: float) -> float:
    """Convert bytes to megabytes (decimal)."""
    return b / 1_000_000.0


def bytes_to_gigabytes(b: float) -> float:
    """Convert bytes to gigabytes (decimal)."""
    return b / 1_000_000_000.0


def mbps_to_bytes_per_sec(mbps: float) -> float:
    """Convert megabits per second to bytes per second."""
    return mbps * BPS_PER_MBPS / 8.0
