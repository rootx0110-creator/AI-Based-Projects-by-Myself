"""SQLite persistence layer. Table layout documented in memory.md."""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS networks (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ssid           TEXT NOT NULL,
  bssid          TEXT NOT NULL UNIQUE,
  channel        INTEGER,
  signal_dbm     INTEGER,
  encryption     TEXT,
  clients        INTEGER,
  first_seen     TEXT,
  last_seen      TEXT,
  capture_count  INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ssid           TEXT,
  bssid          TEXT,
  channel        INTEGER,
  started_at     TEXT,
  ended_at       TEXT,
  duration_s     REAL,
  packets        INTEGER,
  eapol_messages INTEGER,
  status         TEXT,
  deauth_used    INTEGER DEFAULT 0,
  seed           TEXT
);
CREATE TABLE IF NOT EXISTS reports (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   INTEGER,
  ssid         TEXT,
  bssid        TEXT,
  title        TEXT,
  generated_at TEXT,
  score        INTEGER,
  file_name    TEXT
);
"""


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with closing(connect(db_path)) as conn, conn:
        conn.executescript(SCHEMA)


def _rows(conn, query, args=()):
    cur = conn.execute(query, args)
    return [dict(r) for r in cur.fetchall()]


# ---- networks ------------------------------------------------------------

def upsert_network(db_path, net):
    now = utcnow()
    with closing(connect(db_path)) as conn, conn:
        conn.execute(
            """INSERT INTO networks
               (ssid, bssid, channel, signal_dbm, encryption, clients,
                first_seen, last_seen)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(bssid) DO UPDATE SET
                 ssid=excluded.ssid,
                 channel=excluded.channel,
                 signal_dbm=excluded.signal_dbm,
                 encryption=excluded.encryption,
                 clients=excluded.clients,
                 last_seen=excluded.last_seen""",
            (net["ssid"], net["bssid"], net["channel"], net["signal_dbm"],
             net["encryption"], net.get("clients", 0), now, now),
        )


def bump_capture_count(db_path, bssid):
    with closing(connect(db_path)) as conn, conn:
        conn.execute(
            "UPDATE networks SET capture_count = capture_count + 1 "
            "WHERE bssid = ?", (bssid,))


def list_networks(db_path):
    with closing(connect(db_path)) as conn:
        return _rows(conn, "SELECT * FROM networks ORDER BY capture_count DESC, signal_dbm DESC")


def network_by_bssid(db_path, bssid):
    with closing(connect(db_path)) as conn:
        rows = _rows(conn, "SELECT * FROM networks WHERE bssid = ?", (bssid,))
        return rows[0] if rows else None


# ---- sessions -------------------------------------------------------------

def create_session(db_path, started=None, **fields):
    started = started or utcnow()
    with closing(connect(db_path)) as conn, conn:
        cur = conn.execute(
            """INSERT INTO sessions
               (ssid, bssid, channel, started_at, seed)
               VALUES (?,?,?,?,?)""",
            (fields.get("ssid"), fields.get("bssid"),
             fields.get("channel"), started, fields.get("seed")))
        return cur.lastrowid


def finish_session(db_path, session_id, ended_at, duration_s, packets,
                   eapol_messages, status, deauth_used):
    with closing(connect(db_path)) as conn, conn:
        conn.execute(
            """UPDATE sessions SET
                 ended_at=?, duration_s=?, packets=?, eapol_messages=?,
                 status=?, deauth_used=? WHERE id=?""",
            (ended_at, duration_s, packets, eapol_messages, status,
             deauth_used, session_id))


def list_sessions(db_path, limit=50):
    with closing(connect(db_path)) as conn:
        return _rows(
            conn,
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,))


def get_session(db_path, session_id):
    with closing(connect(db_path)) as conn:
        rows = _rows(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,))
        return rows[0] if rows else None


def stats(db_path):
    with closing(connect(db_path)) as conn:
        out = {}
        out["networks"] = _rows(conn, "SELECT COUNT(*) AS c FROM networks")[0]["c"]
        out["networks_wpawpa2"] = _rows(
            conn, "SELECT COUNT(*) AS c FROM networks WHERE encryption LIKE '%WPA%'")[0]["c"]
        out["sessions"] = _rows(conn, "SELECT COUNT(*) AS c FROM sessions")[0]["c"]
        out["captures"] = _rows(
            conn, "SELECT COUNT(*) AS c FROM sessions WHERE status IN ('COMPLETE','PARTIAL')")[0]["c"]
        out["handshakes"] = _rows(
            conn, "SELECT COUNT(*) AS c FROM sessions WHERE status = 'COMPLETE'")[0]["c"]
        out["reports"] = _rows(conn, "SELECT COUNT(*) AS c FROM reports")[0]["c"]
        out["deauth_total"] = _rows(
            conn, "SELECT COALESCE(SUM(deauth_used),0) AS c FROM sessions")[0]["c"]
        out["last_session"] = _rows(
            conn, "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1")
        out["last_session"] = out["last_session"][0] if out["last_session"] else None
        return out


def recent_sessions(db_path, limit=6):
    return list_sessions(db_path, limit=limit)


# ---- reports ----------------------------------------------------------------

def create_report(db_path, session_id, ssid, bssid, title, score, file_name):
    with closing(connect(db_path)) as conn, conn:
        cur = conn.execute(
            """INSERT INTO reports
               (session_id, ssid, bssid, title, generated_at, score, file_name)
               VALUES (?,?,?,?,?,?,?)""",
            (session_id, ssid, bssid, title, utcnow(), score, file_name))
        return cur.lastrowid


def list_reports(db_path):
    with closing(connect(db_path)) as conn:
        return _rows(conn, "SELECT * FROM reports ORDER BY generated_at DESC")


def get_report(db_path, report_id):
    with closing(connect(db_path)) as conn:
        rows = _rows(conn, "SELECT * FROM reports WHERE id = ?", (report_id,))
        return rows[0] if rows else None


def delete_report(db_path, report_id):
    with closing(connect(db_path)) as conn, conn:
        row = _rows(conn, "SELECT file_name FROM reports WHERE id = ?", (report_id,))
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        return row[0]["file_name"] if row else None


def init_module():
    return True