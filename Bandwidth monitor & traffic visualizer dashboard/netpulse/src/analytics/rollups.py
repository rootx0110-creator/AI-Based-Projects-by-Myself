"""Time-bucket rollups (hour/day/month) computed from raw samples.

Rollups run on a timer (default: every 5 min for the current hour) and are
also recomputed on demand for the History tab.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from storage.database import Database

log = logging.getLogger(__name__)


@dataclass
class RollupBucket:
    """Aggregated traffic for one time bucket."""

    bucket_ts: int  # unix ms at bucket start
    granularity: str  # 'hour' | 'day' | 'month'
    bytes_sent: int = 0
    bytes_recv: int = 0
    peak_down_bps: int = 0
    peak_up_bps: int = 0


def bucket_start_ms(ts: float, granularity: str) -> int:
    """Return the unix-ms start of the hour/day/month bucket containing ts."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    if granularity == "hour":
        start = dt.replace(minute=0, second=0, microsecond=0)
    elif granularity == "day":
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "month":
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"unknown granularity: {granularity}")
    return int(start.timestamp() * 1000)


def compute_rollups(db: Database, since_ms: int, until_ms: int, granularity: str = "hour") -> list[RollupBucket]:
    """Aggregate raw samples into RollupBuckets (pure read; no writes)."""
    acc: dict[int, RollupBucket] = {}
    for row in db.series_for_range(since_ms, until_ms):
        start = bucket_start_ms(row["ts"] / 1000.0, granularity)
        bucket = acc.setdefault(
            start,
            RollupBucket(bucket_ts=start, granularity=granularity),
        )
        bucket.bytes_sent += int(row["bytes_sent"])
        bucket.bytes_recv += int(row["bytes_recv"])
        # peak: per-sample rate estimated over the flush window (~10s)
        est_down = int(int(row["bytes_recv"]) * 8 / 10)
        est_up = int(int(row["bytes_sent"]) * 8 / 10)
        bucket.peak_down_bps = max(bucket.peak_down_bps, est_down)
        bucket.peak_up_bps = max(bucket.peak_up_bps, est_up)
    return [acc[k] for k in sorted(acc)]


def refresh_current_hour(db: Database) -> int:
    """Recompute + upsert the current hour's rollup; returns buckets written."""
    now = time.time()
    start = bucket_start_ms(now, "hour")
    buckets = compute_rollups(db, start, int(now * 1000), "hour")
    for b in buckets:
        db.upsert_rollup(b.bucket_ts, b.granularity, b.bytes_sent, b.bytes_recv, b.peak_down_bps, b.peak_up_bps)
    return len(buckets)


def hourly_heatmap(db: Database, hours: int = 24) -> list[tuple[int, int]]:
    """Return [(hour_local, bytes_total)] for the last *hours* hours."""
    now = time.time()
    since = int((now - hours * 3600) * 1000)
    totals: dict[int, int] = defaultdict(int)
    for row in db.series_for_range(since, int(now * 1000)):
        hour_local = datetime.fromtimestamp(row["ts"] / 1000).hour
        totals[hour_local] += int(row["bytes_recv"]) + int(row["bytes_sent"])
    return sorted(totals.items())
