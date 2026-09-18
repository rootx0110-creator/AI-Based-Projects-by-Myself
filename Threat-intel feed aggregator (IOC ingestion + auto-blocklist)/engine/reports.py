import csv
import io
import json
import os
import time

import config
from database import get_connection


def query_iocs(types=None, severity=None, feed_id=None, search=None, blocklisted=None, limit=5000):
    conn = get_connection()
    sql = "SELECT value, type, source_feed, confidence, severity, tags, first_seen, last_seen, blocklisted FROM iocs WHERE 1=1"
    params = []
    if types:
        placeholders = ",".join("?" for _ in types)
        sql += f" AND type IN ({placeholders})"
        params.extend(types)
    if severity:
        sql += " AND severity = ?"
        params.append(severity)
    if feed_id:
        sql += " AND feed_id = ?"
        params.append(feed_id)
    if search:
        sql += " AND value LIKE ?"
        params.append(f"%{search}%")
    if blocklisted is not None:
        sql += " AND blocklisted = ?"
        params.append(1 if blocklisted else 0)
    sql += " ORDER BY confidence DESC, last_seen DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_report(fmt="csv", **filters):
    """Generate a threat-intel report and store to reports/. Returns file info."""
    rows = query_iocs(**filters)
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d%H%M%S")
    fname = f"threat_report_{fmt}_{ts}.{fmt}"
    path = os.path.join(config.REPORT_DIR, fname)

    if fmt == "csv":
        _write_csv(path, rows)
    elif fmt == "json":
        payload = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(rows),
            "iocs": rows,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    else:  # txt
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"Threat Intelligence Report - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            fh.write("=" * 50 + "\n")
            fh.write(f"Total IOC count: {len(rows)}\n\n")
            for r in rows:
                fh.write(
                    f"[{r['type']}] {r['value']} | conf={r['confidence']:.2f} | "
                    f"sev={r['severity']} | feed={r['source_feed']} | seen={r['last_seen']}\n"
                )

    return {"path": path, "filename": fname, "format": fmt, "rows": len(rows)}


def _write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        if rows:
            fieldnames = list(rows[0].keys())
        else:
            fieldnames = ["value", "type", "source_feed", "confidence", "severity", "tags", "first_seen", "last_seen", "blocklisted"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) c FROM iocs").fetchone()["c"]
    by_type = {
        r["type"]: r["c"]
        for r in conn.execute("SELECT type, COUNT(*) c FROM iocs GROUP BY type").fetchall()
    }
    blocklisted = conn.execute("SELECT COUNT(*) c FROM iocs WHERE blocklisted = 1").fetchone()["c"]
    severity = {
        r["severity"]: r["c"]
        for r in conn.execute("SELECT severity, COUNT(*) c FROM iocs GROUP BY severity").fetchall()
    }
    feed_count = conn.execute("SELECT COUNT(*) c FROM feeds").fetchone()["c"]
    conn.close()
    return {
        "total": total,
        "by_type": by_type,
        "blocklisted": blocklisted,
        "severity": severity,
        "feed_count": feed_count,
    }