"""SQLite storage: schema creation, batched writes and query helpers.

A dedicated writer thread owns the connection; producers enqueue rows and the
writer batches INSERTs every *flush_seconds* to avoid disk thrash. WAL mode
keeps reads (History tab) non-blocking.
"""
from __future__ import annotations

import logging
import queue
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from utils.paths import db_path

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,           -- unix ms
    iface       TEXT NOT NULL,
    bytes_sent  INTEGER NOT NULL,
    bytes_recv  INTEGER NOT NULL,
    pkts_sent   INTEGER NOT NULL DEFAULT 0,
    pkts_recv   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts);
CREATE INDEX IF NOT EXISTS idx_samples_iface_ts ON samples(iface, ts);

CREATE TABLE IF NOT EXISTS process_samples (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           INTEGER NOT NULL,
    pid          INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    bytes_sent   INTEGER NOT NULL,
    bytes_recv   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_process_samples_ts ON process_samples(ts);

CREATE TABLE IF NOT EXISTS rollups (
    bucket_ts     INTEGER NOT NULL,         -- start of bucket (unix ms)
    granularity   TEXT NOT NULL,            -- 'hour' | 'day' | 'month'
    bytes_sent    INTEGER NOT NULL,
    bytes_recv    INTEGER NOT NULL,
    peak_down_bps INTEGER NOT NULL DEFAULT 0,
    peak_up_bps   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (bucket_ts, granularity)
);

CREATE TABLE IF NOT EXISTS quotas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    period        TEXT NOT NULL,            -- 'daily' | 'monthly'
    limit_bytes   INTEGER NOT NULL,
    current_bytes INTEGER NOT NULL DEFAULT 0,
    last_reset    INTEGER NOT NULL
);
"""


@dataclass
class SampleRow:
    """One row for the samples table (per interface, per flush window)."""

    ts_ms: int
    iface: str
    bytes_sent: int
    bytes_recv: int
    pkts_sent: int = 0
    pkts_recv: int = 0


@dataclass
class ProcessRow:
    """One row for the process_samples table."""

    ts_ms: int
    pid: int
    process_name: str
    bytes_sent: int
    bytes_recv: int


@dataclass
class Database:
    """Thread-safe SQLite wrapper with a background batch writer."""

    path: str
    flush_seconds: float = 10.0
    _conn: sqlite3.Connection | None = field(default=None, repr=False)
    _queue: "queue.Queue[tuple[str, tuple]]" = field(default_factory=queue.Queue, repr=False)
    _stop = threading.Event()
    _thread: threading.Thread | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Open the connection and start the writer thread."""
        self._stop = threading.Event()

    # -- lifecycle ------------------------------------------------------

    def open(self) -> None:
        """Open the DB, create the schema and start the writer thread."""
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._stop.clear()
        self._thread = threading.Thread(target=self._writer_loop, name="db-writer", daemon=True)
        self._thread.start()
        log.info("database open at %s", self.path)

    def close(self) -> None:
        """Flush pending rows, stop the writer and close the connection."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        if self._conn is not None:
            self._drain()
            try:
                self._conn.commit()
                self._conn.close()
            except Exception as exc:
                log.error("error closing db: %s", exc)
            self._conn = None

    # -- enqueue API (producer side, any thread) -------------------------

    def enqueue_sample(self, row: SampleRow) -> None:
        """Queue one interface sample row for the next flush."""
        self._queue.put(
            (
                "INSERT INTO samples (ts, iface, bytes_sent, bytes_recv, pkts_sent, pkts_recv) VALUES (?,?,?,?,?,?)",
                (row.ts_ms, row.iface, row.bytes_sent, row.bytes_recv, row.pkts_sent, row.pkts_recv),
            )
        )

    def enqueue_process_sample(self, row: ProcessRow) -> None:
        """Queue one per-process sample row for the next flush."""
        self._queue.put(
            (
                "INSERT INTO process_samples (ts, pid, process_name, bytes_sent, bytes_recv) VALUES (?,?,?,?,?)",
                (row.ts_ms, row.pid, row.process_name, row.bytes_sent, row.bytes_recv),
            )
        )

    def _drain(self) -> int:
        """Write all queued rows in a single transaction; return row count."""
        if self._conn is None:
            return 0
        written = 0
        batch: list[tuple[str, tuple]] = []
        while True:
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if not batch:
            return 0
        try:
            for sql, params in batch:
                self._conn.execute(sql, params)
                written += 1
            self._conn.commit()
        except sqlite3.Error as exc:
            log.error("db write failed (%d rows lost): %s", len(batch), exc)
        return written

    def _writer_loop(self) -> None:
        """Background loop: flush the queue every flush_seconds."""
        while not self._stop.wait(self.flush_seconds):
            try:
                self._drain()
            except Exception:
                log.exception("db flush failed")

    # -- read helpers (run on caller thread; WAL allows concurrent read) --

    def _query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Run a read-only query with row factory."""
        if self._conn is None:
            return []
        try:
            self._conn.row_factory = sqlite3.Row
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            return rows
        except sqlite3.Error as exc:
            log.error("db query failed: %s -- %s", sql, exc)
            return []

    def interfaces(self) -> list[str]:
        """Distinct interface names present in the samples table."""
        rows = self._query("SELECT DISTINCT iface FROM samples ORDER BY iface")
        return [r["iface"] for r in rows]

    def totals_for_range(self, since_ms: int, until_ms: int, iface: str | None = None) -> tuple[int, int]:
        """(bytes_sent, bytes_recv) totals over a time range."""
        if iface:
            rows = self._query(
                "SELECT COALESCE(SUM(bytes_sent),0) AS s, COALESCE(SUM(bytes_recv),0) AS r "
                "FROM samples WHERE ts BETWEEN ? AND ? AND iface = ?",
                (since_ms, until_ms, iface),
            )
        else:
            rows = self._query(
                "SELECT COALESCE(SUM(bytes_sent),0) AS s, COALESCE(SUM(bytes_recv),0) AS r "
                "FROM samples WHERE ts BETWEEN ? AND ?",
                (since_ms, until_ms),
            )
        return int(rows[0]["s"]), int(rows[0]["r"]) if rows else (0, 0)

    def series_for_range(self, since_ms: int, until_ms: int, iface: str | None = None) -> list[sqlite3.Row]:
        """Raw samples over a range for the History charts."""
        if iface:
            return self._query(
                "SELECT ts, bytes_sent, bytes_recv FROM samples WHERE ts BETWEEN ? AND ? AND iface = ? ORDER BY ts",
                (since_ms, until_ms, iface),
            )
        return self._query(
            "SELECT ts, bytes_sent, bytes_recv FROM samples WHERE ts BETWEEN ? AND ? ORDER BY ts",
            (since_ms, until_ms),
        )

    def top_talkers(self, since_ms: int, until_ms: int, n: int = 10) -> list[sqlite3.Row]:
        """Top-N processes by total bytes over a range."""
        return self._query(
            "SELECT process_name, SUM(bytes_sent + bytes_recv) AS total, SUM(bytes_recv) AS recv "
            "FROM process_samples WHERE ts BETWEEN ? AND ? GROUP BY process_name "
            "ORDER BY total DESC LIMIT ?",
            (since_ms, until_ms, n),
        )

    def rollups(self, granularity: str, since_ms: int, until_ms: int) -> list[sqlite3.Row]:
        """Stored rollup buckets for a granularity in a range."""
        return self._query(
            "SELECT bucket_ts, bytes_sent, bytes_recv, peak_down_bps, peak_up_bps "
            "FROM rollups WHERE granularity = ? AND bucket_ts BETWEEN ? AND ? ORDER BY bucket_ts",
            (granularity, since_ms, until_ms),
        )

    def upsert_rollup(
        self,
        bucket_ts: int,
        granularity: str,
        bytes_sent: int,
        bytes_recv: int,
        peak_down: int,
        peak_up: int,
    ) -> None:
        """Insert-or-merge a rollup bucket (runs synchronously, caller thread)."""
        if self._conn is None:
            return
        try:
            self._conn.execute(
                "INSERT INTO rollups (bucket_ts, granularity, bytes_sent, bytes_recv, peak_down_bps, peak_up_bps) "
                "VALUES (?,?,?,?,?,?) ON CONFLICT(bucket_ts, granularity) DO UPDATE SET "
                "bytes_sent = bytes_sent + excluded.bytes_sent, "
                "bytes_recv = bytes_recv + excluded.bytes_recv, "
                "peak_down_bps = MAX(peak_down_bps, excluded.peak_down_bps), "
                "peak_up_bps = MAX(peak_up_bps, excluded.peak_up_bps)",
                (bucket_ts, granularity, bytes_sent, bytes_recv, peak_down, peak_up),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log.error("rollup upsert failed: %s", exc)

    def purge_older_than(self, ts_ms: int) -> int:
        """Delete samples older than ts_ms; return rows removed."""
        if self._conn is None:
            return 0
        try:
            cur = self._conn.execute("DELETE FROM samples WHERE ts < ?", (ts_ms,))
            cur2 = self._conn.execute("DELETE FROM process_samples WHERE ts < ?", (ts_ms,))
            self._conn.commit()
            return cur.rowcount + cur2.rowcount
        except sqlite3.Error as exc:
            log.error("purge failed: %s", exc)
            return 0

    def vacuum(self) -> None:
        """Compact the database file."""
        try:
            if self._conn is not None:
                self._conn.execute("VACUUM")
        except sqlite3.Error as exc:
            log.error("vacuum failed: %s", exc)


def utc_ms(ts: float | None = None) -> int:
    """Unix seconds -> unix milliseconds (default: now)."""
    return int((ts if ts is not None else time.time()) * 1000)
