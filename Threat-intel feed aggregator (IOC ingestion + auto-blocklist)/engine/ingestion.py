import config
from database import get_connection, get_setting, set_setting
from engine import blocklist as bl
from engine import fetcher, parser
from engine.extractor import dedupe, normalize_ioc, severity_from_confidence

FORMAT_TYPES = {"IP", "DOMAIN", "URL", "HASH", "EMAIL"}


def normalize_type_label(label):
    label = (label or "").strip().upper()
    for t in FORMAT_TYPES:
        if t in label:
            return t
    return "HASH" if label in ("MD5", "SHA1", "SHA256", "SHA512") else None


def process_feed(feed, raw_text):
    """Run a feed's raw text through parsing + extraction, upsert IOCs."""
    feed_types = [t.strip().upper() for t in (feed["ioc_types"] or "").split(",") if t.strip()]
    fmt = (feed["format"] or "TXT").upper()
    raw_feed_id = feed.get("id")

    filters = set(feed_types) if feed_types else None

    items = parser.parse_by_format(raw_text, fmt, filters=filters)

    # Normalize + classify each candidate
    typed = []
    for value, hint_type in items:
        value = str(value).strip()
        if not value:
            continue
        if "://" in value or value.startswith("www."):
            v = value if "://" in value else "http://" + value
            typed.append((normalize_ioc(v, "URL"), "URL"))
            continue
        from engine.extractor import ioc_type_of

        t = ioc_type_of(value)
        if t == "IP":
            typed.append((normalize_ioc(value, "IP"), "IP"))
        elif t == "DOMAIN":
            typed.append((normalize_ioc(value, "DOMAIN"), "DOMAIN"))
        elif t == "HASH":
            typed.append((normalize_ioc(value, "HASH"), "HASH"))
        elif t == "URL":
            typed.append((normalize_ioc(value, "URL"), "URL"))
        elif t == "EMAIL":
            typed.append((normalize_ioc(value, "EMAIL"), "EMAIL"))

    typed = dedupe(typed)

    # Drop items whose type isn't in requested filter
    if filters:
        typed = [(v, t) for v, t in typed if t in filters]

    reputation = float(feed.get("reputation") or 0.7)
    new_count = 0
    conn = get_connection()
    for value, typ in typed:
        confidence = round(min(1.0, reputation), 2)
        severity = severity_from_confidence(confidence)
        exists = conn.execute(
            "SELECT id, last_seen, confidence FROM iocs WHERE value = ? AND type = ?",
            (value, typ),
        ).fetchone()
        if exists:
            cur_conf = max(confidence, exists["confidence"])
            cur_sev = severity_from_confidence(cur_conf)
            conn.execute(
                "UPDATE iocs SET last_seen = datetime('now'), confidence = ?, severity = ?, "
                "source_feed = ?, feed_id = COALESCE(feed_id, ?) WHERE id = ?",
                (cur_conf, cur_sev, feed["name"], raw_feed_id, exists["id"]),
            )
        else:
            new_count += 1
            conn.execute(
                """INSERT INTO iocs (value, type, source_feed, feed_id, confidence, severity, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                (value, typ, feed["name"], raw_feed_id, confidence, severity),
            )
    conn.commit()
    conn.close()
    return typed, new_count


def run_ingest(feed_id=None):
    """Ingest one feed (by id) or all enabled feeds. Returns per-feed results."""
    conn = get_connection()
    if feed_id:
        feeds = conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,)).fetchall()
    else:
        feeds = conn.execute("SELECT * FROM feeds WHERE enabled = 1 AND auto_ingest = 1").fetchall()
    rows = [dict(r) for r in feeds]
    conn.close()

    results = []
    for feed in rows:
        log_conn = get_connection()
        try:
            raw = fetcher.fetch_text(feed["url"])
            typed, new_count = process_feed(feed, raw)
            total = len(typed)
            status = "success"
            message = ""
            log_conn.execute(
                "UPDATE feeds SET last_status = 'success', last_check_at = datetime('now'), last_updated = datetime('now') WHERE id = ?",
                (feed["id"],),
            )
            log_conn.execute(
                "INSERT INTO ingest_log (feed_id, feed_name, status, message, new_iocs, total_iocs, fetched_at) "
                "VALUES (?, ?, 'success', ?, ?, ?, datetime('now'))",
                (feed["id"], feed["name"], f"{new_count} new", new_count, total),
            )
            log_conn.commit()
            results.append({"feed": feed["name"], "status": "success", "new": new_count, "total": total})
        except Exception as exc:
            log_conn.execute(
                "UPDATE feeds SET last_status = ?, last_check_at = datetime('now') WHERE id = ?",
                (str(exc)[:200], feed["id"]),
            )
            log_conn.execute(
                "INSERT INTO ingest_log (feed_id, feed_name, status, message, new_iocs, total_iocs, fetched_at) "
                "VALUES (?, ?, 'error', ?, 0, 0, datetime('now'))",
                (feed["id"], feed["name"], str(exc)[:400]),
            )
            log_conn.commit()
            results.append({"feed": feed["name"], "status": "error", "new": 0, "total": 0, "error": str(exc)[:200]})
        finally:
            log_conn.close()

    # Auto-blocklist generation if enabled
    autogen = get_setting("auto_blocklist", "1") == "1"
    if autogen and results and any(r["status"] == "success" for r in results):
        threshold = float(get_setting("min_confidence", "0.5"))
        try:
            bl.generate_blocklist(threshold_conf=threshold, fmt="pf")
            set_setting("last_autogen", datetime_now_iso())
        except Exception:
            pass
    return results


def datetime_now_iso():
    from datetime import datetime

    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")