"""Small shared helpers (kept dependency-free)."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> str:
    """Current UTC time as a compact ISO-ish string used in logs/reports."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def human_seconds(value: float) -> str:
    if value >= 3600:
        return f"{value / 3600:.1f} h"
    if value >= 60:
        return f"{value / 60:.1f} min"
    return f"{value:.0f} s"