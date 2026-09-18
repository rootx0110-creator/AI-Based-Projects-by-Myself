"""FRAMC — Firewall Rule Auditor & Misconfiguration Checker — HTTP API.

Endpoints:
    GET  /                    SPA
    GET  /api/formats         supported vendor formats
    POST /api/analyze         {format, name, content} → report
    GET  /api/export?kind=    json | rules-csv | findings-csv (last report)
"""

from __future__ import annotations

import os
import threading

from flask import Flask, jsonify, request, Response, send_from_directory
from flask import abort

from .engine import FORMATS, audit

MAX_CONTENT = 2 * 1024 * 1024  # 2 MB

app = Flask(
    __name__,
    static_folder=None,
    static_url_path=None,
)

_lock = threading.Lock()
_last_report: dict = {}


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@app.get("/api/formats")
def api_formats():
    return jsonify({"ok": True, "data": {
        "formats": [{"id": k, "name": v} for k, v in FORMATS.items()],
    }, "error": None})


@app.post("/api/analyze")
def api_analyze():
    payload = request.get_json(silent=True) or {}
    fmt = payload.get("format") or "iptables"
    name = (payload.get("name") or "configuration").strip() or "configuration"
    content = payload.get("content") or ""

    if len(content) > MAX_CONTENT:
        abort(413, "Configuration content exceeds the 2 MB limit.")
    if not content.strip():
        return jsonify({"ok": False, "data": None,
                        "error": "content is empty"}), 400
    if fmt not in FORMATS:
        return jsonify({"ok": False, "data": None,
                        "error": f"unknown format '{fmt}'"}), 400

    try:
        report = audit(fmt, content, name=name)
    except Exception as exc:  # defensive — never leak internals
        app.logger.exception("analysis failed")
        return jsonify({"ok": False, "data": None,
                        "error": f"analysis failed: {exc.__class__.__name__}"}), 500

    global _last_report
    with _lock:
        _last_report = report

    return jsonify({"ok": True, "data": report, "error": None})


@app.get("/api/export")
def api_export():
    kind = request.args.get("kind", "json")
    with _lock:
        report = dict(_last_report)
    if not report:
        return jsonify({"ok": False, "data": None,
                        "error": "run an analysis first"}), 404

    if kind == "json":
        import json as _json
        body = _json.dumps(report, indent=2)
        return _text(body, "report.json", "application/json")
    if kind == "rules-csv":
        from .engine.scoring import export_csv
        return _text(export_csv(report), "rules.csv", "text/csv")
    if kind == "findings-csv":
        from .engine.scoring import export_findings_csv
        return _text(export_findings_csv(report), "findings.csv", "text/csv")
    return jsonify({"ok": False, "error": "unknown export kind"}), 400


def _text(body: str, filename: str, mimetype: str) -> Response:
    resp = Response(body)
    resp.headers["Content-Type"] = mimetype
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# --------------------------------------------------------------------------
# static SPA
# --------------------------------------------------------------------------

_FRONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "frontend")
_SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "samples")


@app.get("/")
def spa_index():
    return send_from_directory(_FRONT, "index.html")


@app.get("/<path:filename>")
def spa_static(filename):
    # samples are served from the repository root "samples/" folder
    if filename.startswith("samples/"):
        try:
            return send_from_directory(_SAMPLES, filename[len("samples/"):])
        except FileNotFoundError:
            abort(404)
    try:
        return send_from_directory(_FRONT, filename)
    except FileNotFoundError:
        abort(404)


@app.after_request
def add_security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self'",
    )
    return resp


def create_app() -> Flask:
    return app