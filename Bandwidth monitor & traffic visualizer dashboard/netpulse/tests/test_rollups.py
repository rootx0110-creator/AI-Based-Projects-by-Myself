"""Tests for rollup bucketing with a temp SQLite DB."""
from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timezone

from analytics.rollups import bucket_start_ms, compute_rollups, hourly_heatmap
from storage.database import Database, SampleRow


def _tmp_db() -> Database:
    path = os.path.join(tempfile.mkdtemp(), "test.db")
    db = Database(path=path)
    db.open()
    return db


def test_bucket_start_hour() -> None:
    ts = datetime(2026, 9, 12, 15, 42, 10, tzinfo=timezone.utc).timestamp()
    start = datetime.fromtimestamp(bucket_start_ms(ts, "hour") / 1000, tz=timezone.utc)
    assert (start.minute, start.second) == (0, 0)
    assert start.hour == 15


def test_bucket_start_month() -> None:
    ts = datetime(2026, 9, 12, 15, 0, 0, tzinfo=timezone.utc).timestamp()
    start = datetime.fromtimestamp(bucket_start_ms(ts, "month") / 1000, tz=timezone.utc)
    assert (start.month, start.day) == (9, 1)


def test_compute_rollups_aggregates() -> None:
    db = _tmp_db()
    try:
        base = int(time.time() * 1000) - 3600_000
        for i in range(5):
            db.enqueue_sample(SampleRow(ts_ms=base + i * 1000, iface="eth0", bytes_sent=100, bytes_recv=200))
        db._drain()  # flush immediately (writer thread not needed in test)
        buckets = compute_rollups(db, base - 1000, base + 10_000, "hour")
        assert len(buckets) == 1
        assert buckets[0].bytes_sent == 500
        assert buckets[0].bytes_recv == 1000
    finally:
        db.close()


def test_hourly_heatmap_buckets() -> None:
    db = _tmp_db()
    try:
        now = time.time()
        db.enqueue_sample(SampleRow(ts_ms=int(now * 1000), iface="eth0", bytes_sent=10, bytes_recv=20))
        db._drain()
        data = hourly_heatmap(db, hours=24)
        assert data and data[-1][1] >= 30
    finally:
        db.close()
