import sqlite3
import hashlib
import json
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "honeypot.db")


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS attackers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint_hash TEXT UNIQUE,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            total_attacks INTEGER DEFAULT 1,
            risk_score REAL DEFAULT 0.0,
            tags TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            protocol TEXT NOT NULL,
            src_ip TEXT NOT NULL,
            src_port INTEGER,
            dst_port INTEGER,
            event_type TEXT NOT NULL,
            username TEXT,
            password TEXT,
            user_agent TEXT,
            headers TEXT DEFAULT '{}',
            raw_data TEXT,
            fingerprint_hash TEXT,
            risk_score REAL DEFAULT 0.0,
            geo_country TEXT,
            geo_city TEXT,
            geo_latitude REAL,
            geo_longitude REAL,
            asn TEXT,
            isp TEXT,
            FOREIGN KEY (fingerprint_hash) REFERENCES attackers(fingerprint_hash)
        );

        CREATE TABLE IF NOT EXISTS http_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            method TEXT,
            path TEXT,
            query_string TEXT,
            http_version TEXT,
            request_headers TEXT DEFAULT '{}',
            request_body TEXT,
            response_code INTEGER,
            FOREIGN KEY (event_id) REFERENCES events(id)
        );

        CREATE TABLE IF NOT EXISTS ssh_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            client_version TEXT,
            auth_method TEXT,
            commands TEXT DEFAULT '[]',
            session_duration REAL,
            FOREIGN KEY (event_id) REFERENCES events(id)
        );

        CREATE TABLE IF NOT EXISTS threat_intel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint_hash TEXT UNIQUE,
            known_as TEXT,
            malware_families TEXT DEFAULT '[]',
            first_reported TEXT,
            last_active TEXT,
            confidence REAL DEFAULT 0.0
        );

        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_src_ip ON events(src_ip);
        CREATE INDEX IF NOT EXISTS idx_events_protocol ON events(protocol);
        CREATE INDEX IF NOT EXISTS idx_events_fingerprint ON events(fingerprint_hash);
        CREATE INDEX IF NOT EXISTS idx_attackers_hash ON attackers(fingerprint_hash);
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def generate_fingerprint_hash(src_ip, user_agent="", headers=None, extra=""):
    raw = f"{src_ip}|{user_agent}|{json.dumps(headers or {}, sort_keys=True)}|{extra}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def insert_event(event: dict):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO events (timestamp, protocol, src_ip, src_port, dst_port,
                event_type, username, password, user_agent, headers, raw_data,
                fingerprint_hash, risk_score, geo_country, geo_city, geo_latitude,
                geo_longitude, asn, isp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("timestamp", datetime.utcnow().isoformat()),
            event["protocol"], event["src_ip"],
            event.get("src_port"), event.get("dst_port"),
            event["event_type"],
            event.get("username"), event.get("password"),
            event.get("user_agent"), json.dumps(event.get("headers", {})),
            event.get("raw_data"), event.get("fingerprint_hash"),
            event.get("risk_score", 0.0),
            event.get("geo_country"), event.get("geo_city"),
            event.get("geo_latitude"), event.get("geo_longitude"),
            event.get("asn"), event.get("isp"),
        ))
        return cur.lastrowid


def upsert_attacker(fingerprint_hash: str, risk_score_delta: float = 1.0):
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        existing = conn.execute(
            "SELECT * FROM attackers WHERE fingerprint_hash = ?", (fingerprint_hash,)
        ).fetchone()
        if existing:
            new_risk = min(100.0, existing["risk_score"] + risk_score_delta)
            conn.execute("""
                UPDATE attackers SET last_seen = ?, total_attacks = total_attacks + 1,
                    risk_score = ?
                WHERE fingerprint_hash = ?
            """, (now, new_risk, fingerprint_hash))
        else:
            conn.execute("""
                INSERT INTO attackers (fingerprint_hash, first_seen, last_seen, risk_score)
                VALUES (?, ?, ?, ?)
            """, (fingerprint_hash, now, now, risk_score_delta))


def get_attackers(limit=100, offset=0):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM attackers ORDER BY risk_score DESC, last_seen DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]


def get_events(limit=200, offset=0, protocol=None, src_ip=None, event_type=None):
    with get_conn() as conn:
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        if protocol:
            query += " AND protocol = ?"
            params.append(protocol)
        if src_ip:
            query += " AND src_ip = ?"
            params.append(src_ip)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_event_count(protocol=None, since=None):
    with get_conn() as conn:
        query = "SELECT COUNT(*) as cnt FROM events WHERE 1=1"
        params = []
        if protocol:
            query += " AND protocol = ?"
            params.append(protocol)
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        return conn.execute(query, params).fetchone()["cnt"]


def get_top_attackers(limit=10):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT a.*, COUNT(e.id) as event_count
            FROM attackers a
            LEFT JOIN events e ON a.fingerprint_hash = e.fingerprint_hash
            GROUP BY a.fingerprint_hash
            ORDER BY a.risk_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_top_ips(limit=10):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT src_ip, COUNT(*) as attempts,
                MIN(timestamp) as first_seen, MAX(timestamp) as last_seen,
                GROUP_CONCAT(DISTINCT protocol) as protocols
            FROM events
            GROUP BY src_ip
            ORDER BY attempts DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_events_timeline(hours=24):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                protocol, COUNT(*) as count
            FROM events
            WHERE timestamp >= datetime('now', ? || ' hours')
            GROUP BY hour, protocol
            ORDER BY hour
        """, (str(-hours),)).fetchall()
        return [dict(r) for r in rows]


def get_protocol_stats():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT protocol, event_type, COUNT(*) as count
            FROM events
            GROUP BY protocol, event_type
            ORDER BY count DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_geo_stats():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT geo_country, COUNT(DISTINCT src_ip) as unique_ips, COUNT(*) as total
            FROM events
            WHERE geo_country IS NOT NULL AND geo_country != ''
            GROUP BY geo_country
            ORDER BY total DESC
            LIMIT 20
        """).fetchall()
        return [dict(r) for r in rows]


def get_usernames_tried():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT username, COUNT(*) as attempts
            FROM events
            WHERE username IS NOT NULL AND username != ''
            GROUP BY username
            ORDER BY attempts DESC
            LIMIT 50
        """).fetchall()
        return [dict(r) for r in rows]


def get_passwords_tried():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT password, COUNT(*) as attempts
            FROM events
            WHERE password IS NOT NULL AND password != ''
            GROUP BY password
            ORDER BY attempts DESC
            LIMIT 50
        """).fetchall()
        return [dict(r) for r in rows]


def get_dashboard_stats():
    with get_conn() as conn:
        total_events = conn.execute("SELECT COUNT(*) as cnt FROM events").fetchone()["cnt"]
        total_attackers = conn.execute("SELECT COUNT(*) as cnt FROM attackers").fetchone()["cnt"]
        total_ssh = conn.execute("SELECT COUNT(*) as cnt FROM events WHERE protocol='ssh'").fetchone()["cnt"]
        total_http = conn.execute("SELECT COUNT(*) as cnt FROM events WHERE protocol='http'").fetchone()["cnt"]
        unique_ips = conn.execute("SELECT COUNT(DISTINCT src_ip) as cnt FROM events").fetchone()["cnt"]
        high_risk = conn.execute("SELECT COUNT(*) as cnt FROM attackers WHERE risk_score >= 50").fetchone()["cnt"]
        today = conn.execute(
            "SELECT COUNT(*) as cnt FROM events WHERE timestamp >= date('now')"
        ).fetchone()["cnt"]
        return {
            "total_events": total_events,
            "total_attackers": total_attackers,
            "total_ssh": total_ssh,
            "total_http": total_http,
            "unique_ips": unique_ips,
            "high_risk_attackers": high_risk,
            "today_events": today,
        }


def insert_http_request(data: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO http_requests (event_id, method, path, query_string,
                http_version, request_headers, request_body, response_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("event_id"), data.get("method"), data.get("path"),
            data.get("query_string"), data.get("http_version"),
            json.dumps(data.get("request_headers", {})),
            data.get("request_body"), data.get("response_code"),
        ))


def insert_ssh_session(data: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO ssh_sessions (event_id, client_version, auth_method,
                commands, session_duration)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("event_id"), data.get("client_version"),
            data.get("auth_method"), json.dumps(data.get("commands", [])),
            data.get("session_duration"),
        ))


def add_threat_intel(fingerprint_hash: str, tool_matches: list, confidence: float = 0.5):
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        existing = conn.execute(
            "SELECT * FROM threat_intel WHERE fingerprint_hash = ?", (fingerprint_hash,)
        ).fetchone()
        if existing:
            existing_tools = json.loads(existing["malware_families"] or "[]")
            merged = list(set(existing_tools + tool_matches))
            conn.execute("""
                UPDATE threat_intel SET known_as = ?, malware_families = ?,
                    last_active = ?, confidence = MIN(1.0, confidence + ?)
                WHERE fingerprint_hash = ?
            """, (", ".join(merged[:3]) or None, json.dumps(merged),
                  now, 0.1, fingerprint_hash))
        else:
            conn.execute("""
                INSERT INTO threat_intel (fingerprint_hash, known_as, malware_families,
                    first_reported, last_active, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (fingerprint_hash, ", ".join(tool_matches[:3]), json.dumps(tool_matches),
                  now, now, confidence))


def export_report_data():
    """Export all data for HTML report generation."""
    with get_conn() as conn:
        return {
            "stats": get_dashboard_stats(),
            "attackers": [dict(r) for r in conn.execute(
                "SELECT * FROM attackers ORDER BY risk_score DESC"
            ).fetchall()],
            "events": [dict(r) for r in conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT 1000"
            ).fetchall()],
            "top_ips": get_top_ips(20),
            "top_usernames": get_usernames_tried(),
            "top_passwords": get_passwords_tried(),
            "geo_stats": get_geo_stats(),
            "protocol_stats": get_protocol_stats(),
            "timeline": get_events_timeline(72),
        }
