"""Artifact parsers: Android .ab container, SQLite databases, package lists.

All parsing happens on copies inside the case folder; databases are opened
read-only. Parsers return lists of dicts.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tarfile
import zlib

AB_MAGIC = b"ANDROID BACKUP"


def unpack_ab(ab_path: str, out_dir: str) -> tuple[bool, str]:
    """Decompress an Android backup (.ab) into out_dir via zlib + tar."""
    try:
        with open(ab_path, "rb") as fh:
            header = fh.read(1024)
            if not header.startswith(AB_MAGIC):
                return False, "not an Android backup file (bad magic)"
            lines = header.split(b"\n", 4)
            # 0 magic, 1 version, 2 compression flag, 3 encryption, 4 payload start
            if len(lines) < 5:
                return False, "malformed .ab header"
            payload_start = sum(len(l) + 1 for l in lines[:4])
            fh.seek(payload_start)
            compressed = fh.read()
        raw = zlib.decompress(compressed)
        os.makedirs(out_dir, exist_ok=True)
        tar_path = os.path.join(out_dir, "backup.tar")
        with open(tar_path, "wb") as tf:
            tf.write(raw)
        with tarfile.open(tar_path, "r:") as tar:
            tar.extractall(out_dir, filter="data")
        os.remove(tar_path)
        return True, "backup unpacked"
    except zlib.error as exc:
        return False, f"zlib error (encrypted or corrupt backup?): {exc}"
    except (OSError, tarfile.TarError) as exc:
        return False, f"unpack failed: {exc}"


def find_file(root: str, name: str) -> str | None:
    for dirpath, _dirnames, filenames in os.walk(root):
        if name in filenames:
            return os.path.join(dirpath, name)
    return None


def _open_ro(path: str) -> sqlite3.Connection:
    uri = "file:" + path.replace("\\", "/").replace("?", "%3f").replace("#", "%23") + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict]:
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except sqlite3.Error:
        return []


def parse_calls(contacts_db: str) -> list[dict]:
    conn = _open_ro(contacts_db)
    try:
        rows = _rows(conn, """
            SELECT number, date, duration, type, new
            FROM calls ORDER BY date DESC LIMIT 5000
        """)
    finally:
        conn.close()
    type_map = {1: "Incoming", 2: "Outgoing", 3: "Missed", 4: "Voicemail",
                5: "Rejected", 6: "Blocked", 7: "Answered externally"}
    for r in rows:
        try:
            ts = int(r.get("date") or 0)
            r["datetime"] = (
                __import__("datetime").datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
                if ts > 10_000_000_000 else
                __import__("datetime").datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            )
        except (ValueError, OverflowError, OSError):
            r["datetime"] = str(r.get("date"))
        r["call_type"] = type_map.get(r.get("type"), str(r.get("type")))
        r["duration_s"] = r.get("duration")
    return rows


def parse_sms(mmssms_db: str) -> list[dict]:
    conn = _open_ro(mmssms_db)
    try:
        rows = _rows(conn, """
            SELECT address, person, date, body, type
            FROM sms ORDER BY date DESC LIMIT 5000
        """)
    finally:
        conn.close()
    type_map = {1: "Received", 2: "Sent", 3: "Draft", 4: "Outbox", 5: "Failed", 6: "Queued"}
    for r in rows:
        try:
            ts = int(r.get("date") or 0)
            r["datetime"] = (
                __import__("datetime").datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
                if ts > 10_000_000_000 else
                __import__("datetime").datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            )
        except (ValueError, OverflowError, OSError):
            r["datetime"] = str(r.get("date"))
        r["sms_type"] = type_map.get(r.get("type"), str(r.get("type")))
    return rows


def parse_contacts(contacts_db: str) -> list[dict]:
    conn = _open_ro(contacts_db)
    try:
        rows = _rows(conn, """
            SELECT c.display_name AS name,
                   d.data1       AS phone,
                   m.mimetype    AS mimetype
            FROM contacts_view c
            LEFT JOIN raw_contacts rc ON rc.contact_id = c._id
            LEFT JOIN data d ON d.raw_contact_id = rc._id
            LEFT JOIN mimetypes m ON m._id = d.mimetype_id
            ORDER BY c.display_name LIMIT 5000
        """)
    except sqlite3.Error:
        rows = _rows(conn, """
            SELECT display_name AS name, data1 AS phone
            FROM data_view ORDER BY display_name LIMIT 5000
        """)
    finally:
        conn.close()
    seen: set[tuple] = set()
    out: list[dict] = []
    for r in rows:
        key = (r.get("name"), r.get("phone"))
        if key in seen or not any(key):
            continue
        seen.add(key)
        out.append({"name": r.get("name") or "", "phone": r.get("phone") or ""})
    return out


def parse_packages(text: str) -> list[dict]:
    apps = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            apps.append({"package": line.split("package:", 1)[1].strip(), "kind": "app"})
    return apps


def parse_artifacts(extract_dir: str, package_text: str | None = None) -> dict[str, list[dict]]:
    """Parse whatever is available in an extracted backup dir (+ optional pkg list)."""
    artifacts: dict[str, list[dict]] = {"calls": [], "sms": [], "contacts": [], "apps": []}
    contacts_db = find_file(extract_dir, "contacts2.db")
    mmssms_db = find_file(extract_dir, "mmssms.db")
    if contacts_db:
        try:
            artifacts["calls"] = parse_calls(contacts_db)
            artifacts["contacts"] = parse_contacts(contacts_db)
        except sqlite3.Error:
            pass
    if mmssms_db:
        try:
            artifacts["sms"] = parse_sms(mmssms_db)
        except sqlite3.Error:
            pass
    if package_text:
        artifacts["apps"] = parse_packages(package_text)
    return artifacts


def save_artifacts(case_dir: str, artifacts: dict[str, list[dict]]) -> str:
    path = os.path.join(case_dir, "extracted", "artifacts.json")
    merged: dict[str, list[dict]] = {"calls": [], "sms": [], "contacts": [], "apps": []}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                merged = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    for key, rows in artifacts.items():
        merged.setdefault(key, []).extend(rows)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=1)
    return path
