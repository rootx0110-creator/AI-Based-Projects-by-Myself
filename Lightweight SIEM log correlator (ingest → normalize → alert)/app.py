"""Lightweight SIEM Log Correlator — Flask web application.

Pipeline: Ingest → Normalize → Correlate → Alert, served through a clean
JSON API, with a single-page UI and one-click HTML report export.
"""
import argparse
import io
import json
import os
import sys
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request, send_file, Response

from correlator.normalizer import normalize
from correlator.correlator import RuleEngine
from correlator.alerter import AlertManager
from correlator.store import Store
from correlator.samples import generate_series
from correlator import ingest as ingest_mod

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_PATH = os.path.join(BASE_DIR, "state.json")

app = Flask(__name__)
store = Store(SNAPSHOT_PATH)
engine = RuleEngine()
alerts = AlertManager(store)


# ---------------------------------------------------------------------------
#  API
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat() + "Z"})


@app.route("/api/summary")
def summary():
    totals = dict(store.stats)
    totals["ingest_rate"] = _ingest_rate()
    return jsonify(totals)


@app.route("/api/overview")
def overview():
    data = store.to_dict()
    return jsonify(data)


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    body = request.get_data(as_text=True)
    if not body:
        return jsonify({"error": "empty payload"}), 400
    return jsonify(_process_payload(body))


@app.route("/api/ingest/file", methods=["POST"])
def api_ingest_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "no file uploaded"}), 400
    content = file.read().decode("utf-8", errors="replace")
    return jsonify(_process_payload(content))


@app.route("/api/ingest/json", methods=["POST"])
def api_ingest_json():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "expected JSON object"}), 400
    line = json.dumps(data)
    return jsonify(_process_payload(line))


@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json(silent=True) or {}
    seconds = int(body.get("seconds", 60))
    density = float(body.get("density", 1.5))
    seed = body.get("seed")
    lines = generate_series(seconds=seconds, lines_per_second=density, seed=seed)
    return jsonify(_process_payload("\n".join(lines)))


@app.route("/api/logs")
def api_logs():
    limit = int(request.args.get("limit", 200))
    return jsonify(store.logs[-limit:][::-1])


@app.route("/api/events")
def api_events():
    limit = int(request.args.get("limit", 300))
    return jsonify(store.events[-limit:][::-1])


@app.route("/api/correlations")
def api_correlations():
    limit = int(request.args.get("limit", 100))
    return jsonify(store.correlations[-limit:][::-1])


@app.route("/api/alerts")
def api_alerts():
    limit = int(request.args.get("limit", 200))
    status = request.args.get("status")
    items = store.alerts
    if status:
        items = [a for a in items if a.get("status") == status]
    return jsonify(items[-limit:][::-1])


@app.route("/api/alerts/<int:alert_id>/ack", methods=["POST"])
def api_alert_ack(alert_id):
    a = alerts.ack(alert_id)
    if not a:
        return jsonify({"error": "not found"}), 404
    store.save()
    return jsonify(a)


@app.route("/api/alerts/<int:alert_id>/close", methods=["POST"])
def api_alert_close(alert_id):
    a = alerts.close(alert_id)
    if not a:
        return jsonify({"error": "not found"}), 404
    store.save()
    return jsonify(a)


@app.route("/api/rules")
def api_rules():
    return jsonify(engine.rules)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    store.reset()
    store.save()
    return jsonify({"ok": True})


@app.route("/api/state/save", methods=["POST"])
def api_state_save():
    store.save()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
#  Report export — standalone HTML
# ---------------------------------------------------------------------------
@app.route("/api/report")
def api_report():
    data = store.to_dict()
    html = build_report(data)
    filename = (
        f"siem-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.html"
    )
    return Response(
        html,
        mimetype="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


def _ingest_rate():
    """Events normalized in the last 60 seconds."""
    cutoff = datetime.utcnow() - timedelta(seconds=60)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    n = 0
    for ev in store.events:
        ts = str(ev.get("timestamp", ""))
        if ts and ts >= cutoff_iso:
            n += 1
        else:
            continue
    return n


def _process_payload(payload):
    """Run raw text through the full pipeline; returns summary dict."""
    ok = 0
    failed = 0
    new_alerts = 0
    new_correlations = 0
    last_event = None
    for raw in ingest_mod.iter_lines(payload):
        rec = store.add_raw(raw)
        ev = normalize(raw, ingest_id=rec["ingest_id"])
        if ev is None:
            store.mark_failed()
            failed += 1
            continue
        store.add_event(ev)
        ok += 1
        for corr in engine.evaluate(ev):
            store.add_correlation(corr)
            new_correlations += 1
            alert = alerts.new_alert(corr)
            if alert:
                new_alerts += 1
    store.save()
    return {
        "status": "ok",
        "raw": ok + failed,
        "normalized": ok,
        "failed": failed,
        "correlations": new_correlations,
        "alerts": new_alerts,
    }


# ---------------------------------------------------------------------------
#  Report renderer (inline CSS, fully self-contained)
# ---------------------------------------------------------------------------
def build_report(data):
    stats = data["stats"]
    events = data["events"]
    alerts_items = data["alerts"]
    correlations = data["correlations"]
    hour = data.get("hourly", {})
    per_source = data.get("events_per_source", {})
    per_type = data.get("events_per_type", {})
    severity = data.get("severity_counts", {})
    tops = data.get("top_sources", {})

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    sev_order = ["info", "low", "medium", "high", "critical"]
    sev_html = "".join(
        f"<span class='pill pill-{s}'>{s} ({severity.get(s, 0)})</span>"
        for s in sev_order if severity.get(s, 0)
    )

    chart = _hourly_bars(hour)
    src_chart = _top_bars(tops, "Source IP")
    type_chart = _top_bars(per_type, "Event type")

    recent_alerts = alerts_items[-25:][::-1]
    alert_rows = "\n".join(
        _alert_row(a) for a in recent_alerts
    ) or "<tr><td colspan='7' class='empty'>No alerts yet</td></tr>"

    open_alerts = sum(1 for a in alerts_items if a.get("status") == "open")

    sev_bar = _severity_bar(severity)

    # insights
    insight = _build_insight(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SIEM Correlation Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          background: #0d1117; color: #e6edf3; padding: 28px; }}
  .wrap {{ max-width: 980px; margin: 0 auto; }}
  header {{ border-bottom: 1px solid #21262d; padding-bottom: 16px; margin-bottom: 20px; }}
  h1 {{ font-size: 22px; letter-spacing: .5px; }}
  h1 .accent {{ color: #58a6ff; }}
  .sub {{ color: #8b949e; font-size: 12px; margin-top: 4px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(140px,1fr));
          gap: 12px; margin: 18px 0; }}
  .kpi {{ background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 14px; }}
  .kpi .v {{ font-size: 26px; font-weight: 700; color: #58a6ff; }}
  .kpi .l {{ color: #8b949e; font-size: 12px; margin-top: 4px; text-transform: uppercase; }}
  .card {{ background: #161b22; border: 1px solid #21262d; border-radius: 10px;
          padding: 16px; margin-bottom: 16px; }}
  .card h2 {{ font-size: 14px; color: #58a6ff; margin-bottom: 12px; text-transform: uppercase;
              letter-spacing: 1px; }}
  .bar {{ height: 14px; background: #21262d; border-radius: 7px; overflow: hidden; margin: 4px 0 8px; }}
  .bar > div {{ height: 100%; background: linear-gradient(90deg,#1f6feb,#58a6ff); }}
  .bar-label {{ display:flex; justify-content:space-between; font-size:12px; color:#8b949e; }}
  .bars .row {{ margin: 8px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ text-align: left; color: #8b949e; text-transform: uppercase; font-size: 11px;
       letter-spacing: .5px; padding: 8px; border-bottom: 1px solid #21262d; }}
  td {{ padding: 8px; border-bottom: 1px solid #1c2025; vertical-align: top; }}
  tr:hover td {{ background: #1c2128; }}
  .pill {{ padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight:600; }}
  .pill-info {{ background:#21262d; color:#8b949e; }}
  .pill-low {{ background:#1f7a3d; color:#b8e3c4; }}
  .pill-medium {{ background:#9e6a03; color:#f0d9a6; }}
  .pill-high {{ background:#b35900; color:#ffd9b3; }}
  .pill-critical {{ background:#a5384a; color:#ffc4cc; }}
  .pill-open {{ background:#a5384a; color:#fff; }}
  .pill-acknowledged {{ background:#9e6a03; color:#fff; }}
  .pill-closed {{ background:#21262d; color:#8b949e; }}
  footer {{ color:#484f58; font-size:11px; text-align:center; margin-top:24px; }}
  .empty {{ text-align:center; color:#8b949e; padding:20px; }}
  .sev-legend {{ margin: 8px 0; display:flex; gap:8px; flex-wrap: wrap; }}
  .insight {{ background:#10151d; border-left:3px solid #58a6ff; border-radius:6px; padding:12px 14px;
             font-size:13px; color:#c9d1d9; line-height:1.6; }}
  .insight b {{ color:#58a6ff; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1><span class="accent">SIEM</span> Correlation Report</h1>
    <div class="sub">Generated {now} &middot; Lightweight Log Correlator &middot; Ingest &rarr; Normalize &rarr; Correlate &rarr; Alert</div>
  </header>

  <div class="kpis">
    <div class="kpi"><div class="v">{stats.get('ingested_raw',0)}</div><div class="l">Raw Logs</div></div>
    <div class="kpi"><div class="v">{stats.get('normalized',0)}</div><div class="l">Events</div></div>
    <div class="kpi"><div class="v">{stats.get('failed',0)}</div><div class="l">Failed Parse</div></div>
    <div class="kpi"><div class="v">{stats.get('correlations',0)}</div><div class="l">Correlations</div></div>
    <div class="kpi"><div class="v">{stats.get('alerts',0)}</div><div class="l">Alerts</div></div>
    <div class="kpi"><div class="v" style="color:{'#f85149' if open_alerts else '#58a6ff'}">{open_alerts}</div><div class="l">Open Alerts</div></div>
  </div>

  <div class="card">
    <h2>Event Severity</h2>
    <div class="sev-legend">{sev_html}</div>
    {sev_bar}
  </div>

  <div class="card">
    <h2>Event Volume over Time (hourly)</h2>
    {chart}
  </div>

  <div class="card">
    <h2>Top Sources &amp; Top Event Types</h2>
    <div class="bars">
      {src_chart}
      {type_chart}
    </div>
  </div>

  <div class="card">
    <h2>Analyst Insight</h2>
    <div class="insight">{insight}</div>
  </div>

  <div class="card">
    <h2>Latest Alerts</h2>
    <table>
      <thead><tr>
        <th>ID</th><th>Title</th><th>Severity</th><th>Risk</th><th>Count</th>
        <th>Actor</th><th>Status</th><th>Generated</th>
      </tr></thead>
      <tbody>{alert_rows}</tbody>
    </table>
  </div>

  <footer>Lightweight SIEM Log Correlator &middot; {now}</footer>
</div>
</body>
</html>"""


def _hourly_bars(hour):
    if not hour:
        return "<div class='empty'>No data yet</div>"
    items = list(hour.items())[-14:]
    mx = max(items, key=lambda kv: kv[1])[1] or 1
    rows = []
    for k, v in items:
        pct = int(v / mx * 100)
        label = k[5:13].replace(":", "h")
        rows.append(
            f"<div class='row'><div class='bar-label'><span>{label}</span>"
            f"<span>{v}</span></div><div class='bar'><div style='width:{pct}%'></div></div></div>"
        )
    return "".join(rows)


def _top_bars(counter, label):
    if not counter:
        return f"<div class='empty'>No {label} data</div>"
    items = list(counter.items())[:8]
    mx = max(items, key=lambda kv: kv[1])[1] or 1
    rows = []
    for k, v in items:
        pct = int(v / mx * 100)
        rows.append(
            f"<div class='row'><div class='bar-label'><span>{k}</span>"
            f"<span>{v}</span></div><div class='bar'><div style='width:{pct}%'></div></div></div>"
        )
    return "".join(rows)


def _severity_bar(severity):
    total = sum(severity.values()) or 1
    colors = {
        "info": "#21262d", "low": "#1f7a3d", "medium": "#9e6a03",
        "high": "#b35900", "critical": "#a5384a",
    }
    segs = []
    for s in ["info", "low", "medium", "high", "critical"]:
        v = severity.get(s, 0)
        if not v:
            continue
        segs.append(f"<div style='flex:1;height:16px;background:{colors[s]};max-width:{v/total*100}%'></div>")
    if not segs:
        return "<div class='empty'>No events yet</div>"
    return f"<div style='display:flex;gap:2px;border-radius:8px;overflow:hidden'>{''.join(segs)}</div>"


def _alert_row(a):
    sev = a.get("severity", "info")
    status = a.get("status", "open")
    actor = a.get("grouped_value") or a.get("actor") or "—"
    return (
        f"<tr><td>#{a.get('id')}</td>"
        f"<td>{a.get('title','')}</td>"
        f"<td><span class='pill pill-{sev}'>{sev}</span></td>"
        f"<td>{a.get('risk',0)}</td>"
        f"<td>{a.get('count',0)}</td>"
        f"<td>{actor}</td>"
        f"<td><span class='pill pill-{status}'>{status}</span></td>"
        f"<td>{str(a.get('generated_at',''))[:19]}</td></tr>"
    )


def _build_insight(data):
    stats = data["stats"]
    alerts_items = data["alerts"]
    tops = data.get("top_sources", {})
    sev = data.get("severity_counts", {})
    parts = []
    if stats.get("normalized", 0) == 0:
        return "<b>No events ingested yet.</b> Ingest logs via the API, file upload, or sample generator to see insights."
    parts.append(f"<b>{stats.get('normalized')}</b> normalized events across this reporting window.")
    if tops:
        top_ip, top_n = list(tops.items())[0]
        parts.append(f"Busiest source IP is <b>{top_ip}</b> with {top_n} events.")
    if sev.get("critical") or sev.get("high"):
        parts.append(f"<b>{sev.get('critical',0)+sev.get('high',0)}</b> high/critical severity events require review.")
    open_a = sum(1 for a in alerts_items if a.get("status") == "open")
    if open_a:
        parts.append(f"<b>{open_a}</b> alerts remain open and need triage.")
    else:
        parts.append("No open alerts — dashboard is clear.")
    ratio = stats.get("normalized", 0) / max(1, stats.get("ingested_raw", 0)) * 100
    parts.append(f"Normalization success rate is <b>{ratio:.1f}%</b>.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lightweight SIEM Log Correlator")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", default=5000, type=int, help="bind port")
    parser.add_argument("--debug", action="store_true", help="enable Flask debug")
    args = parser.parse_args()

    print("=" * 58)
    print("  Lightweight SIEM Log Correlator")
    print("  Ingest -> Normalize -> Correlate -> Alert")
    print("=" * 58)
    print(f"  Dashboard : http://{args.host}:{args.port}/")
    print(f"  Snapshot  : {SNAPSHOT_PATH}")
    print("=" * 58)
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)