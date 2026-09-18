import os

from flask import Flask, jsonify, render_template, request, send_file

import config
import database
from database import get_connection, get_setting, set_setting, init_db, seed_feeds, sync_seed_feeds
from engine import blocklist as bl
from engine import reports as rep
from engine.ingestion import run_ingest

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
init_db()
seed_feeds()
sync_seed_feeds()


def _conn():
    return get_connection()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/feeds")
def feeds_page():
    return render_template("feeds.html")


@app.route("/iocs")
def iocs_page():
    return render_template("iocs.html")


@app.route("/blocklist")
def blocklist_page():
    return render_template("blocklist.html")


@app.route("/reports")
def reports_page():
    return render_template("reports.html")


@app.route("/settings")
def settings_page():
    return render_template("settings.html")


# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------
@app.route("/api/stats")
def api_stats():
    return jsonify(rep.stats())


@app.route("/api/ingest-history")
def api_ingest_history():
    conn = _conn()
    rows = conn.execute(
        "SELECT feed_name, status, new_iocs, total_iocs, fetched_at FROM ingest_log ORDER BY id DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/feeds/status")
def api_feed_status():
    conn = _conn()
    rows = conn.execute("SELECT name, last_status, last_check_at, last_updated FROM feeds").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/trend")
def api_trend():
    conn = _conn()
    rows = conn.execute(
        """SELECT substr(first_seen, 1, 10) d, COUNT(*) c FROM iocs
           WHERE first_seen >= date('now', '-14 days')
           GROUP BY d ORDER BY d"""
    ).fetchall()
    conn.close()
    return jsonify([{"date": r["d"], "count": r["c"]} for r in rows])


# ---------------------------------------------------------------------------
# Feeds API
# ---------------------------------------------------------------------------
@app.route("/api/feeds")
def api_feeds_list():
    conn = _conn()
    rows = conn.execute("SELECT * FROM feeds ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/feeds", methods=["POST"])
def api_feeds_add():
    data = request.get_json(silent=True) or request.form
    name = data.get("name", "").strip()
    url = data.get("url", "").strip()
    fmt = data.get("format", "TXT").upper()
    ioc_types = data.get("ioc_types", "IP")
    reputation = float(data.get("reputation") or 0.7)
    if not name or not url:
        return jsonify({"error": "Name and URL required"}), 400
    conn = _conn()
    conn.execute(
        "INSERT INTO feeds (name, url, format, ioc_types, reputation, enabled, auto_ingest) "
        "VALUES (?, ?, ?, ?, ?, 1, 1)",
        (name, url, fmt, ioc_types, reputation),
    )
    conn.commit()
    fid = conn.execute("SELECT id FROM feeds WHERE name = ? AND url = ?", (name, url)).fetchone()["id"]
    feed = dict(conn.execute("SELECT * FROM feeds WHERE id = ?", (fid,)).fetchone())
    conn.close()
    return jsonify(feed), 201


@app.route("/api/feeds/<int:fid>", methods=["PUT"])
def api_feeds_update(fid):
    data = request.get_json(silent=True) or request.form
    conn = _conn()
    fields = ["name", "url", "format", "ioc_types", "reputation", "enabled", "auto_ingest"]
    for f in fields:
        if f in data and data[f] is not None:
            conn.execute(f"UPDATE feeds SET {f} = ? WHERE id = ?", (data[f], fid))
    conn.commit()
    row = conn.execute("SELECT * FROM feeds WHERE id = ?", (fid,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})


@app.route("/api/feeds/<int:fid>", methods=["DELETE"])
def api_feeds_delete(fid):
    conn = _conn()
    row = conn.execute("SELECT * FROM feeds WHERE id = ?", (fid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404
    conn.execute("DELETE FROM feeds WHERE id = ?", (fid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/feeds/<int:fid>/ingest", methods=["POST"])
def api_feed_ingest(fid):
    results = run_ingest(feed_id=fid)
    return jsonify({"results": results})


@app.route("/api/ingest-all", methods=["POST"])
def api_ingest_all():
    results = run_ingest()
    return jsonify({"results": results})


# ---------------------------------------------------------------------------
# IOCs API
# ---------------------------------------------------------------------------
@app.route("/api/iocs")
def api_iocs():
    types = request.args.get("type")
    severity = request.args.get("severity")
    feed_id = request.args.get("feed_id")
    search = request.args.get("q")
    blocklisted = request.args.get("blocklisted")
    types_list = types.split(",") if types else None
    block_flag = None
    if blocklisted is not None:
        block_flag = blocklisted.lower() in ("1", "true", "yes")
    rows = rep.query_iocs(
        types=types_list,
        severity=severity or None,
        feed_id=int(feed_id) if feed_id else None,
        search=search or None,
        blocklisted=block_flag,
    )
    return jsonify(rows)


@app.route("/api/iocs/<int:iid>", methods=["PATCH"])
def api_ioc_update(iid):
    data = request.get_json(silent=True) or request.form
    conn = _conn()
    row = conn.execute("SELECT * FROM iocs WHERE id = ?", (iid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404
    if "blocklisted" in data:
        conn.execute("UPDATE iocs SET blocklisted = ? WHERE id = ?", (1 if data["blocklisted"] else 0, iid))
    if "notes" in data:
        conn.execute("UPDATE iocs SET notes = ? WHERE id = ?", (data["notes"], iid))
    if "severity" in data:
        conn.execute("UPDATE iocs SET severity = ? WHERE id = ?", (data["severity"], iid))
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM iocs WHERE id = ?", (iid,)).fetchone())
    conn.close()
    return jsonify(updated)


# ---------------------------------------------------------------------------
# Blocklist API
# ---------------------------------------------------------------------------
@app.route("/api/blocklist/generate", methods=["POST"])
def api_blocklist_generate():
    data = request.get_json(silent=True) or request.form
    threshold = float(data.get("threshold_conf") or get_setting("min_confidence", "0.5"))
    fmt = data.get("format", "pf")
    types = data.get("types")
    type_list = types.split(",") if types else None
    result = bl.generate_blocklist(threshold_conf=threshold, fmt=fmt, types=type_list)
    return jsonify(result)


@app.route("/api/blocklist/runs")
def api_blocklist_runs():
    conn = _conn()
    rows = conn.execute("SELECT * FROM blocklist_runs ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/blocklist/download/<path:fname>")
def api_blocklist_download(fname):
    safe = os.path.basename(fname)
    path = os.path.join(config.REPORT_DIR, safe)
    if not os.path.isfile(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path, as_attachment=True, download_name=safe)


@app.route("/api/blocklist/<int:rid>/refresh", methods=["POST"])
def api_blocklist_refresh(rid):
    conn = _conn()
    row = conn.execute("SELECT * FROM blocklist_runs WHERE id = ?", (rid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    result = bl.generate_blocklist(threshold_conf=row["threshold_conf"], fmt=row["format"])
    return jsonify(result)


# ---------------------------------------------------------------------------
# Reports API
# ---------------------------------------------------------------------------
@app.route("/api/reports/generate", methods=["POST"])
def api_reports_generate():
    data = request.get_json(silent=True) or request.form
    fmt = data.get("format", "csv")
    types = data.get("type")
    severity = data.get("severity")
    feed_id = data.get("feed_id")
    search = data.get("q")
    types_list = types.split(",") if types else None
    result = rep.generate_report(
        fmt=fmt,
        types=types_list,
        severity=severity or None,
        feed_id=int(feed_id) if feed_id else None,
        search=search or None,
    )
    return jsonify(result)


@app.route("/api/reports/list")
def api_reports_list():
    items = []
    if os.path.isdir(config.REPORT_DIR):
        for f in sorted(os.listdir(config.REPORT_DIR), reverse=True):
            path = os.path.join(config.REPORT_DIR, f)
            if os.path.isfile(path):
                items.append({"name": f, "size": os.path.getsize(path), "mtime": os.path.getmtime(path)})
    return jsonify(items)


@app.route("/api/reports/download/<path:fname>")
def api_reports_download(fname):
    safe = os.path.basename(fname)
    path = os.path.join(config.REPORT_DIR, safe)
    if not os.path.isfile(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path, as_attachment=True, download_name=safe)


# ---------------------------------------------------------------------------
# Settings API
# ---------------------------------------------------------------------------
@app.route("/api/settings")
def api_settings():
    return jsonify(
        {
            "min_confidence": get_setting("min_confidence", "0.5"),
            "auto_blocklist": get_setting("auto_blocklist", "1"),
            "expiry_days": get_setting("expiry_days", "90"),
            "last_autogen": get_setting("last_autogen", ""),
        }
    )


@app.route("/api/settings", methods=["POST"])
def api_settings_update():
    data = request.get_json(silent=True) or request.form
    for k, v in data.items():
        if k in ("min_confidence", "auto_blocklist", "expiry_days", "last_autogen"):
            set_setting(k, v)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5100))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print("=" * 60)
    print("  Threat Intel Feed Aggregator  |  http://127.0.0.1:%d" % port)
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)