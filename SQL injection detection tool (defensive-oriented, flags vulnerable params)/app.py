"""SQLInspect - defensive SQL injection detection tool (web UI).

Run:
    python app.py            # http://127.0.0.1:5000
"""

import io
import json
import threading
import uuid
import webbrowser
import os

from flask import (Flask, jsonify, render_template, request,
                   send_file, session, abort)

from core.analyzer import run_scan
from reports.generator import ReportGenerator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "reports", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "sql-inspect-local-only-#0xS3Cr3t"  # local tool; not for prod

STORE = {}


def _store_result(payload):
    rid = uuid.uuid4().hex[:12]
    STORE[rid] = payload
    summary = payload["summary"]
    session.setdefault("history", []).append({
        "id": rid,
        "scanned_at": summary["scanned_at"],
        "mode": summary["mode"],
        "targets": summary["targets"],
        "params": summary["total_params"],
        "overall_risk": summary["overall_risk"],
        "overall_score": summary["overall_score"],
        "live": summary["live"],
    })
    if len(session["history"]) > 50:
        session["history"] = session["history"][-50:]
    return rid


def _get_or_404(rid):
    payload = STORE.get(rid)
    if not payload:
        abort(404, "Report not found")
    return payload


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", history=session.get("history", []))


@app.route("/report/<rid>")
def report_page(rid):
    payload = _get_or_404(rid)
    return render_template("report.html", rid=rid, data=payload)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.route("/api/scan", methods=["POST"])
def api_scan():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "url")
    data = body.get("data", "")
    live = body.get("live", {}) or {}
    if live.get("enabled") and not live.get("consent"):
        return jsonify({"error": "Live probing requires the authorization checkbox to be enabled."}), 400

    try:
        result = run_scan(data, mode=mode, live_settings={
            "enabled": bool(live.get("enabled")),
            "timeout": float(live.get("timeout", 8)),
            "delay_ms": int(live.get("delay_ms", 0)),
            "consent": bool(live.get("consent")),
        })
    except Exception as exc:
        return jsonify({"error": "Scan failed: %s" % exc}), 400

    rid = _store_result(result)
    result["id"] = rid
    return jsonify(result)


@app.route("/api/history")
def api_history():
    return jsonify(session.get("history", []))


@app.route("/api/report/<rid>/download/<fmt>")
def api_download(rid, fmt):
    payload = _get_or_404(rid)
    gen = ReportGenerator(payload)
    if fmt == "pdf":
        data, fname = gen.pdf_bytes(), gen.filename("pdf")
        mimetype = "application/pdf"
    elif fmt == "csv":
        data, fname = gen.csv_bytes(), gen.filename("csv")
        mimetype = "text/csv"
    elif fmt == "json":
        data, fname = json.dumps(payload, indent=2).encode("utf-8"), gen.filename("json")
        mimetype = "application/json"
    elif fmt == "html":
        data, fname = gen.standalone_html().encode("utf-8"), gen.filename("html")
        mimetype = "text/html"
    else:
        abort(404, "Unknown format")

    return send_file(
        io.BytesIO(data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=fname,
    )


@app.route("/api/demo")
def api_demo():
    """Built-in demo input for trying the tool instantly."""
    return jsonify({
        "mode": "url",
        "data": ("http://shop.local/products.php?category=Books&id=1%20UNION%20ALL%20SELECT"
                 "%20NULL,user(),3--%20&sort=price"),
    })


if __name__ == "__main__":
    print("=" * 64)
    print("  SQLInspect  |  defensive SQL injection detection")
    print("  UI        :  http://127.0.0.1:5000")
    if os.environ.get("SQLINSPECT_NO_BROWSER") != "1":
        threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    print("=" * 64)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)