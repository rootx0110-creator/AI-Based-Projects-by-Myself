"""PhishGuard - LLM-Powered Phishing Email Classifier.

Flask web application entry point. Run with:  python app.py
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request, send_file, make_response

from classifier import llm, service, __version__

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)


def resource_path(rel: str) -> str:
    if FROZEN:
        base = getattr(sys, "_MEIPASS", BASE_DIR)
    else:
        base = BASE_DIR
    return os.path.join(base, rel)


app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB per scan


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    return jsonify(service.health())


@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json(silent=True) or {}
    body = data.get("email") or data.get("body") or ""
    if not body.strip():
        return jsonify({"error": "No email content provided."}), 400
    if len(body) > app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"error": "Email is too large (max 1 MB)."}), 413

    result = service.scan_email(
        raw=body,
        subject=data.get("subject"),
        sender=data.get("sender"),
        recipient=data.get("recipient"),
        use_llm=data.get("use_llm"),
    )
    return jsonify(result)


@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    s = llm.load_settings()
    s.pop("api_key", None)
    return jsonify({"llm": s})


@app.route("/api/settings", methods=["POST"])
def api_settings_set():
    data = request.get_json(silent=True) or {}
    s = llm.save_settings(data.get("llm") or {})
    s.pop("api_key", None)
    return jsonify({"llm": s, "ok": True})


@app.route("/api/report/<analysis_id>")
def api_report(analysis_id: str):
    payload = service.store.get(analysis_id)
    if payload is None:
        return jsonify({"error": "Scan not found."}), 404

    from report.render import render_scan

    doc, tag = render_scan(payload)
    fname = f"PhishGuard_{analysis_id}_{tag.lower()}.html"
    response = make_response(doc)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{fname}"'
    return response


@app.route("/api/recent")
def api_recent():
    return jsonify({"scans": service.store.recent()})


def _open_browser():
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "127.0.0.1")
    print("=" * 60)
    print("  PhishGuard - LLM-Powered Phishing Email Classifier")
    print(f"  Running at http://{host}:{port}")
    print("  Ctrl+C to stop.")
    print("=" * 60)
    threading.Timer(1.0, _open_browser).start()
    app.run(host=host, port=port, debug=False, threaded=True)