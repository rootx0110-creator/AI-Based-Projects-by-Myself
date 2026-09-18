import os
import sqlite3

import config
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS feeds (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    url           TEXT NOT NULL,
    format        TEXT NOT NULL DEFAULT 'TXT',
    ioc_types     TEXT NOT NULL DEFAULT 'IP',
    reputation    REAL NOT NULL DEFAULT 0.7,
    enabled       INTEGER NOT NULL DEFAULT 1,
    auto_ingest   INTEGER NOT NULL DEFAULT 1,
    last_status   TEXT,
    last_check_at TEXT,
    last_updated  TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS iocs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    value         TEXT NOT NULL,
    type          TEXT NOT NULL,
    source_feed   TEXT,
    feed_id       INTEGER,
    confidence    REAL NOT NULL DEFAULT 0.5,
    severity      TEXT NOT NULL DEFAULT 'medium',
    tags          TEXT,
    first_seen    TEXT DEFAULT (datetime('now')),
    last_seen     TEXT NOT NULL,
    blocklisted   INTEGER NOT NULL DEFAULT 0,
    notes         TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ioc_unique ON iocs (value, type);
CREATE INDEX IF NOT EXISTS idx_ioc_type ON iocs (type);
CREATE INDEX IF NOT EXISTS idx_ioc_blocklisted ON iocs (blocklisted);
CREATE INDEX IF NOT EXISTS idx_ioc_seen ON iocs (last_seen);

CREATE TABLE IF NOT EXISTS ingest_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id     INTEGER,
    feed_name   TEXT,
    status      TEXT NOT NULL,
    message     TEXT,
    new_iocs    INTEGER NOT NULL DEFAULT 0,
    total_iocs  INTEGER NOT NULL DEFAULT 0,
    fetched_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS blocklist_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at    TEXT NOT NULL,
    ioc_count       INTEGER NOT NULL DEFAULT 0,
    ip_count        INTEGER NOT NULL DEFAULT 0,
    domain_count    INTEGER NOT NULL DEFAULT 0,
    url_count       INTEGER NOT NULL DEFAULT 0,
    hash_count      INTEGER NOT NULL DEFAULT 0,
    blocklist_path  TEXT,
    format          TEXT,
    threshold_conf  REAL,
    auto_added      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR IGNORE INTO settings (key, value) VALUES
    ('min_confidence', '0.5'),
    ('auto_blocklist', '1'),
    ('expiry_days', '90'),
    ('last_autogen', '');
"""


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def seed_feeds():
    from config import SEED_FEEDS

    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM feeds").fetchone()["c"]
    if count == 0:
        for f in SEED_FEEDS:
            conn.execute(
                "INSERT INTO feeds (name, url, format, ioc_types, reputation, enabled, auto_ingest) "
                "VALUES (?, ?, ?, ?, ?, 1, 1)",
                (f["name"], f["url"], f["format"], ",".join(f["ioc_types"]), f["reputation"]),
            )
        conn.commit()
    conn.close()


def sync_seed_feeds():
    """Repair the seed feed set on the live DB.

    - Removes feed entries whose service went offline (dead list).
    - Adds any seed feed not yet present.
    - Refreshes url/format/types/reputation for seed feeds that already exist
      (keeps URLhaus pointed at the fast text endpoint, etc.). Custom feeds
      added by the user are left untouched.
    """
    from config import SEED_FEEDS

    DEAD_FEEDS = ("Abuse.ch ZeuS Tracker", "CINS Score")
    conn = get_connection()
    for name in DEAD_FEEDS:
        conn.execute("DELETE FROM feeds WHERE name = ?", (name,))
    for f in SEED_FEEDS:
        ioc_types = ",".join(f["ioc_types"])
        row = conn.execute("SELECT id FROM feeds WHERE name = ?", (f["name"],)).fetchone()
        if row:
            conn.execute(
                "UPDATE feeds SET url = ?, format = ?, ioc_types = ?, reputation = ? WHERE id = ?",
                (f["url"], f["format"], ioc_types, f["reputation"], row["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO feeds (name, url, format, ioc_types, reputation, enabled, auto_ingest) "
                "VALUES (?, ?, ?, ?, ?, 1, 1)",
                (f["name"], f["url"], f["format"], ioc_types, f["reputation"]),
            )
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()