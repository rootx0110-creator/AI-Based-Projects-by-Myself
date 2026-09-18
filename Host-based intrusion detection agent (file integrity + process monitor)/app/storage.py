import os
import sqlite3
import threading
import time


class Storage:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def close(self):
        with self._lock:
            self._conn.close()

    def _init(self):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS files_baseline (
                    path      TEXT NOT NULL,
                    rel_path  TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    size      INTEGER NOT NULL,
                    mtime     REAL,
                    added_at  REAL,
                    PRIMARY KEY (path, rel_path)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_baseline (
                    key      TEXT PRIMARY KEY,
                    name     TEXT,
                    exe      TEXT,
                    first_seen REAL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts       REAL NOT NULL,
                    severity INTEGER NOT NULL,
                    source   TEXT NOT NULL,
                    title    TEXT NOT NULL,
                    detail   TEXT,
                    status   TEXT NOT NULL DEFAULT 'open'
                )
                """
            )
            self._conn.commit()

    # ---------- FIM baseline helpers ----------
    def clear_baseline(self, path):
        with self._lock:
            self._conn.execute("DELETE FROM files_baseline WHERE path = ?", (path,))
            self._conn.commit()

    def upsert_file(self, path, rel_path, file_hash, size, mtime):
        with self._lock:
            self._conn.execute(
                """INSERT INTO files_baseline (path, rel_path, file_hash, size, mtime, added_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(path, rel_path) DO UPDATE SET
                       file_hash = excluded.file_hash,
                       size = excluded.size,
                       mtime = excluded.mtime""",
                (path, rel_path, file_hash, size, mtime, time.time()),
            )
            self._conn.commit()

    def baseline_files(self, path):
        with self._lock:
            cur = self._conn.execute(
                "SELECT rel_path, file_hash, size, mtime FROM files_baseline WHERE path = ?",
                (path,),
            )
            return [dict(r) for r in cur.fetchall()]

    def baseline_file_count(self, path=None):
        with self._lock:
            if path:
                cur = self._conn.execute(
                    "SELECT COUNT(*) AS n FROM files_baseline WHERE path = ?", (path,)
                )
            else:
                cur = self._conn.execute("SELECT COUNT(*) AS n FROM files_baseline")
            return cur.fetchone()["n"]

    # ---------- Process baseline helpers ----------
    def save_process_snapshot(self, rows):
        with self._lock:
            self._conn.execute("DELETE FROM process_baseline")
            self._conn.executemany(
                "INSERT OR REPLACE INTO process_baseline (key, name, exe, first_seen) VALUES (?, ?, ?, ?)",
                [(r["key"], r["name"], r["exe"], time.time()) for r in rows],
            )
            self._conn.commit()

    def process_keys(self):
        with self._lock:
            cur = self._conn.execute("SELECT key, name, exe FROM process_baseline")
            return [dict(r) for r in cur.fetchall()]

    # ---------- Alerts ----------
    def add_alert(self, ts, severity, source, title, detail):
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO alerts (ts, severity, source, title, detail, status) VALUES (?, ?, ?, ?, ?, 'open')",
                (ts, severity, source, title, detail),
            )
            self._conn.commit()
            return cur.lastrowid

    def alerts(self, min_severity=1, source=None, limit=500):
        with self._lock:
            q = "SELECT * FROM alerts WHERE severity >= ?"
            args = [min_severity]
            if source:
                q += " AND source = ?"
                args.append(source)
            q += " ORDER BY id DESC LIMIT ?"
            args.append(limit)
            cur = self._conn.execute(q, args)
            return [dict(r) for r in cur.fetchall()]

    def ack_alert(self, alert_id):
        with self._lock:
            self._conn.execute(
                "UPDATE alerts SET status = 'acked' WHERE id = ?", (alert_id,)
            )
            self._conn.commit()

    def clear_alerts(self, source=None):
        with self._lock:
            if source:
                self._conn.execute("DELETE FROM alerts WHERE source = ?", (source,))
            else:
                self._conn.execute("DELETE FROM alerts")
            self._conn.commit()

    def alert_counts(self):
        with self._lock:
            cur = self._conn.execute(
                """SELECT severity, COUNT(*) AS n, SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) AS open_n
                   FROM alerts GROUP BY severity"""
            )
            return {r["severity"]: {"n": r["n"], "open": r["open_n"] or 0} for r in cur.fetchall()}