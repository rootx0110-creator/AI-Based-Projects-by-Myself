# app.py
# XSS Payload Tester - local web UI for testing XSS payloads against your own lab web app.
# Authorized-use only: point this only at resources you own or have permission to test.

import os
import sys
import webbrowser
import threading
from datetime import datetime
from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file, abort

from engine import run_test
from payloads import payload_catalog
from report import build_html_report

APP_VERSION = "1.0.0"

here = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(here, "templates"),
            static_folder=os.path.join(here, "static"))

# Small in-memory history so users can re-download the last report by token.
_last_report = {"token": None, "html": None}
_lock = threading.Lock()


def _run_id():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


@app.route("/")
def index():
    return render_template("index.html", version=APP_VERSION)


@app.route("/api/version")
def api_version():
    return jsonify({"version": APP_VERSION, "name": "XSS Payload Tester"})


@app.route("/api/payloads")
def api_payloads():
    return jsonify(payload_catalog())


@app.route("/api/test", methods=["POST"])
def api_test():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "A target URL is required."}), 400
    try:
        run = run_test(data)
    except Exception as exc:  # surface engine errors to the user
        return jsonify({"error": "%s: %s" % (type(exc).__name__, str(exc)[:300])}), 500
    run["run_id"] = _run_id()
    run["app_version"] = APP_VERSION
    return jsonify(run)


@app.route("/api/report", methods=["POST"])
def api_report():
    """Generate and download an HTML report from a completed run payload."""
    data = request.get_json(silent=True) or {}
    run = data.get("run")
    if not run or not isinstance(run, dict):
        return jsonify({"error": "No run data supplied."}), 400
    try:
        html = build_html_report(run, app_version=run.get("app_version", APP_VERSION))
    except Exception as exc:
        return jsonify({"error": "Report generation failed: %s" % exc}), 500

    token = _run_id()
    with _lock:
        _last_report.update(token=token, html=html)

    filename = "xss-report-%s.html" % run.get("run_id", token)
    return send_file(
        BytesIO(html.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/report/<token>")
def api_report_get(token):
    """Re-download the last generated report by token."""
    with _lock:
        if _last_report.get("token") == token and _last_report.get("html"):
            return send_file(
                BytesIO(_last_report["html"].encode("utf-8")),
                mimetype="text/html",
                as_attachment=True,
                download_name="xss-report-%s.html" % token,
            )
    abort(404)


def open_browser_later(url, delay=1.2):
    threading.Timer(delay, lambda: webbrowser.open(url)).start()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="XSS Payload Tester (lab use only)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    args = parser.parse_args()

    url = "http://%s:%d" % (args.host, args.port)
    print("=" * 62)
    print("  XSS Payload Tester  v%s" % APP_VERSION)
    print("  Authorized-use only. Test resources you own or are allowed to scan.")
    print("  UI: %s" % url)
    print("=" * 62)

    if not args.no_browser:
        # skip auto-open when packaged as a frozen exe inside a console
        if not getattr(sys, "frozen", False):
            open_browser_later(url)

    # Allow running from interpreted file, not just __main__
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()