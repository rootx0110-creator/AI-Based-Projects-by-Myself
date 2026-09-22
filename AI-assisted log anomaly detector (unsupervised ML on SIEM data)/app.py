"""Flask web application - AI-assisted log anomaly detector.

Endpoints:
    GET  /            the dashboard UI
    POST /api/analyze analyze an uploaded log file (or the bundled sample)
    POST /api/report  download the last analysis as a standalone HTML report
    GET  /api/sample  download the synthetic SIEM sample feed (CSV)
    GET  /api/health  liveness probe

Run:
    python app.py            -> http://127.0.0.1:8600
"""

import io
import json
import os
import time
from collections import Counter

from flask import (Flask, Response, jsonify, render_template, request)

from loganomaly.ingestion import parse_bytes, normalize, CANONICAL
from loganomaly.features import build_feature_matrix
from loganomaly.scoring import run_detection
from loganomaly.report import build_html
from loganomaly.sample_data import generate

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)


class AppState:
    """In-memory store of the most recent analysis (single-user tool)."""

    def __init__(self):
        self.events = []
        self.summary = {}
        self.explains = {}
        self.incidents = []
        self.model_info = []
        self.params = {}
        self.timings = {}
        self.labels = []
        self.scores = []


STATE = AppState()


def _creds():
    return {
        "accent": "#d9a441", "navy": "#10192c", "teal": "#2fa1a1",
        "cream": "#e9dfcf", "cards": "#172033",
    }


@app.get("/")
def index():
    return render_template("index.html", **{**_creds(), "title": "SentinelForge — AI-assisted log anomaly detector"})


@app.get("/api/health")
def health():
    return jsonify(ok=True, version="1.0.0")


@app.get("/api/sample")
def sample_download():
    rows = generate(1500, seed=42)
    from loganomaly.sample_data import write_csv
    buf = io.StringIO()
    # write_csv expects a path; stream a CSV inline instead
    import csv
    keys = ["timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "user",
            "host", "event_type", "severity", "bytes_in", "bytes_out", "message"]
    w = csv.DictWriter(buf, fieldnames=keys)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in keys})
    return Response(buf.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=sample_siem_events.csv"})


@app.post("/api/analyze")
def analyze():
    t0 = time.time()
    form = request.form
    params = {
        "contamination": _float(form.get("contamination", "0.05"), 0.05),
        "models": form.get("models", "if,ae") or "if,ae",
    }
    use_sample = form.get("sample") == "1"
    file = request.files.get("file")

    if use_sample or file is None:
        rows = generate(1500, seed=42)
        events = [normalize(r) for r in rows]
        fmt = "Synthetic CSV (bundled sample)"
        params["format"] = fmt
        skipped = 0
    else:
        data = file.read()
        events, fmt, skipped = parse_bytes(data, file.filename or "")
        params["format"] = fmt

    if not events:
        return jsonify(error="No parseable events found in the uploaded file."), 400

    t_ingest = time.time() - t0
    t1 = time.time()
    X, names, meta = build_feature_matrix(events)
    res = run_detection(events, X, names, meta,
                        selection=params["models"],
                        contamination=params["contamination"])
    t_ml = time.time() - t1
    total = time.time() - t0

    scores = [round(float(s), 3) for s in res["scores"]]
    labels = [int(l) for l in res["labels"]]
    summary = _summarize(events, res, scores, labels, len(names))
    summary.update({
        "events": len(events),
        "flagged": int(sum(labels)),
        "rate": 100.0 * sum(labels) / max(1, len(labels)),
        "incidents": len(res["incidents"]),
        "features": len(names),
        "models": len(res["models"]),
        "format": fmt,
        "skipped": skipped,
    })

    STATE.events = events
    STATE.summary = summary
    STATE.explains = res["explains"]
    STATE.incidents = res["incidents"]
    STATE.model_info = res["models"]
    STATE.labels = labels
    STATE.scores = scores
    STATE.params = params
    STATE.timings = {"ingest": t_ingest, "ml": t_ml, "total": total}

    payload = {
        "ok": True,
        "summary": summary,
        "incidents": _public_incidents(res["incidents"], events),
        "models": [
            {"key": m["key"], "name": m["name"], "flagged": m["flagged"]}
            for m in res["models"]
        ],
        "anomalies": _top_flagged(events, scores, labels, res["explains"], 30),
        "timings": STATE.timings,
        "has_report": True,
    }
    return jsonify(payload)


@app.post("/api/report")
def report_download():
    if not STATE.events:
        return jsonify(error="No analysis available yet. Run a detection first."), 400
    html = build_html(
        STATE.summary, STATE.events, STATE.explains, STATE.incidents,
        STATE.model_info, STATE.params, STATE.timings,
        doc_title="AI-assisted log anomaly detector")
    fname = f"anomaly_report_{time.strftime('%Y%m%d_%H%M%S')}.html"
    return Response(html, mimetype="text/html", headers={
        "Content-Disposition": f"attachment; filename={fname}"})


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _float(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _summarize(events, res, scores, labels, n_features):
    sev = Counter()
    etype = Counter()
    for e in events:
        sev[e.get("severity")] += 1
        etype[e.get("event_type") or "unknown"] += 1
    level = "normal"
    if sum(labels):
        level = "attention"
        if max(scores) >= 1.2:
            level = "critical"
    return {
        "sev_dist": sorted(sev.items(), key=lambda kv: -(kv[0] if kv[0] else 0))[:8],
        "etype_dist": etype.most_common(12),
        "level": level,
        "all_scores": scores,
        "labels": labels,
    }


def _public_incidents(incidents, events):
    out = []
    for c in incidents:
        e = events[c["top_event"]]
        srcs = sorted(c["src_ips"])[:3]
        out.append({
            "key": c["key"],
            "size": c["size"],
            "max_score": c["max_score"],
            "mean_score": c["mean_score"],
            "severity": c["severity"],
            "flagged": c["flagged"],
            "users": ", ".join(sorted(c["users"])) or "-",
            "src_ips": srcs,
            "more_srcs": max(0, len(c["src_ips"]) - len(srcs)),
            "event_type": next(iter(c["event_types"]), "-"),
            "top_event": {
                "ts": (e.get("timestamp") or "")[:19],
                "src_ip": e.get("src_ip"),
                "dst_ip": e.get("dst_ip"),
                "user": e.get("user"),
                "message": (e.get("message") or "")[:120],
            },
        })
    return out


def _top_flagged(events, scores, labels, explains, k=30):
    idx = [i for i in range(len(events)) if labels[i]]
    idx.sort(key=lambda i: scores[i], reverse=True)
    out = []
    for i in idx[:k]:
        e = events[i]
        out.append({
            "idx": i,
            "score": scores[i],
            "sev": e.get("severity"),
            "ts": (e.get("timestamp") or "")[:19],
            "event_type": e.get("event_type"),
            "src_ip": e.get("src_ip"),
            "dst_ip": e.get("dst_ip"),
            "src_port": e.get("src_port"),
            "dst_port": e.get("dst_port"),
            "user": e.get("user"),
            "message": (e.get("message") or "")[:140],
            "why": [
                {"feature": f["feature"], "reason": f["reason"],
                 "weight": f["weight"]}
                for f in explains.get(int(i), [])[:4]
            ],
        })
    return out


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8600, debug=False, threaded=True)