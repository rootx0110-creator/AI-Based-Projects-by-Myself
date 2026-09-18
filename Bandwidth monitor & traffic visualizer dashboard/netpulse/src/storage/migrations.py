"""Database migration framework (schema_version table + ordered steps).

The v1 schema ships in database.py; migrations.py provides the forward-only
mechanism used when the schema evolves (add tables, backfill rollups, ...).
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Callable

log = logging.getLogger(__name__)

# Ordered list of (version, migration fn(conn)). Version N means the schema
# reached the state *after* applying step N. Keep append-only.
MIGRATIONS: list[tuple[int, Callable[[sqlite3.Connection], None]]] = []


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    """Create the schema_version bookkeeping table if missing."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (0)")


def run_migrations(conn: sqlite3.Connection, target: int | None = None) -> int:
    """Apply all pending migrations up to target (default: latest).

    Returns the final schema version.
    """
    _ensure_version_table(conn)
    current = int(conn.execute("SELECT version FROM schema_version").fetchone()[0])
    final = current
    for version, fn in sorted(MIGRATIONS):
        if version <= current or (target is not None and version > target):
            continue
        log.info("applying migration v%d", version)
        fn(conn)
        conn.execute("UPDATE schema_version SET version = ?", (version,))
        final = version
    conn.commit()
    return final


def current_version(conn: sqlite3.Connection) -> int:
    """Read the current schema version (0 for a fresh database)."""
    _ensure_version_table(conn)
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    return int(row[0])
