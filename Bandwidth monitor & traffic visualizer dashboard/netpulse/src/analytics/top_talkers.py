"""Top talkers: rank processes/hosts by traffic over a time range."""
from __future__ import annotations

from typing import NamedTuple

from storage.database import Database


class TalkerRow(NamedTuple):
    """One ranked talker."""

    name: str
    total_bytes: int
    recv_bytes: int
    sent_bytes: int


def top_talkers(db: Database, since_ms: int, until_ms: int, n: int = 10) -> list[TalkerRow]:
    """Top-N processes by total bytes in a range (from process_samples)."""
    rows = db.top_talkers(since_ms, until_ms, n=n)
    return [
        TalkerRow(
            name=r["process_name"],
            total_bytes=int(r["total"]),
            recv_bytes=int(r["recv"]),
            sent_bytes=int(r["total"]) - int(r["recv"]),
        )
        for r in rows
    ]
