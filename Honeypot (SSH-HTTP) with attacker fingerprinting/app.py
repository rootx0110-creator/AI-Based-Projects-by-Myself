import json
import os
import socket
import threading
import time
import logging
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request, Response, send_from_directory
from flask import send_file
import io

from honeypot import database
from honeypot.ssh_honeypot import SSHListener
from honeypot.http_honeypot import HTTPServer
from honeypot.fingerprint import analyze_request, classify_event
from honeypot.report import generate_html_report, generate_json_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

server_state = {
    "ssh": {"running": False, "port": 2222, "started_at": None},
    "http": {"running": False, "port": 8080, "started_at": None},
    "db_initialized": False,
}


def handle_event(event_data, fp_result=None):
    """Process incoming honeypot event and persist to DB."""
    fp_hash = event_data.get("fingerprint_hash") or (fp_result or {}).get("fingerprint_hash")
    if not fp_hash:
        fp_analyzed = analyze_request(
            event_data.get("src_ip", "0.0.0.0"),
            user_agent=event_data.get("user_agent", ""),
            headers=event_data.get("headers", {}),
            ssh_version=event_data.get("ssh_version", ""),
        )
        fp_hash = fp_analyzed["fingerprint_hash"]
        fp_result = fp_analyzed

    risk_delta, tags = classify_event(
        event_data.get("event_type", ""),
        event_data.get("username"),
        event_data.get("password"),
        event_data.get("path"),
    )
    if fp_result:
        risk_delta += fp_result.get("risk_score", 0) * 0.3

    database.upsert_attacker(fp_hash, risk_delta)
    event_data["fingerprint_hash"] = fp_hash
    event_data["risk_score"] = round(risk_delta + (fp_result or {}).get("risk_score", 0) * 0.3, 2)

    event_id = database.insert_event(event_data)

    if fp_result and fp_result.get("tool_matches"):
        database.add_threat_intel(fp_hash, fp_result["tool_matches"])

    return event_id


def start_honeypots():
    if not server_state["db_initialized"]:
        database.init_db()
        server_state["db_initialized"] = True

    if not server_state["ssh"]["running"]:
        try:
            from honeypot.ssh_honeypot import SSHListener
            ssh = SSHListener(host="0.0.0.0", port=2222, on_event=handle_event)
            ssh.start()
            server_state["ssh"] = {"running": True, "port": 2222, "started_at": time.time()}
            logger.info("SSH honeypot started on 0.0.0.0:2222")
        except Exception as e:
            logger.error(f"SSH honeypot failed: {e}")

    if not server_state["http"]["running"]:
        try:
            http = HTTPServer(host="0.0.0.0", port=8080, on_event=handle_event)
            http.start()
            server_state["http"] = {"running": True, "port": 8080, "started_at": time.time()}
            logger.info("HTTP honeypot started on 0.0.0.0:8080")
        except Exception as e:
            logger.error(f"HTTP honeypot failed: {e}")


def stop_honeypots():
    server_state["ssh"]["running"] = False
    server_state["http"]["running"] = False
    logger.info("Honeypots stopped")


# ---------- Routes ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(server_state)


@app.route("/api/start", methods=["POST"])
def api_start():
    start_honeypots()
    return jsonify({"success": True, "state": server_state})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop_honeypots()
    return jsonify({"success": True, "state": server_state})


@app.route("/api/dashboard")
def api_dashboard():
    stats = database.get_dashboard_stats()
    stats["server_state"] = server_state
    stats["top_attackers"] = database.get_top_attackers(10)
    stats["top_ips"] = database.get_top_ips(10)
    stats["timeline"] = database.get_events_timeline(24)
    stats["protocol_stats"] = database.get_protocol_stats()
    stats["geo_stats"] = database.get_geo_stats()
    return jsonify(stats)


@app.route("/api/events")
def api_events():
    protocol = request.args.get("protocol")
    src_ip = request.args.get("src_ip")
    event_type = request.args.get("event_type")
    limit = int(request.args.get("limit", 200))
    offset = int(request.args.get("offset", 0))
    events = database.get_events(limit=limit, offset=offset, protocol=protocol,
                                 src_ip=src_ip, event_type=event_type)
    for e in events:
        e["headers"] = json.loads(e.get("headers") or "{}")
    return jsonify(events)


@app.route("/api/attackers")
def api_attackers():
    limit = int(request.args.get("limit", 100))
    attackers = database.get_attackers(limit=limit)
    for a in attackers:
        try:
            a["tags"] = json.loads(a.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            a["tags"] = []
    return jsonify(attackers)


@app.route("/api/attackers/<fp_hash>")
def api_attacker_details(fp_hash):
    with database.get_conn() as conn:
        attacker = conn.execute(
            "SELECT * FROM attackers WHERE fingerprint_hash = ?", (fp_hash,)
        ).fetchone()
        if not attacker:
            return jsonify({"error": "not found"}), 404
        events = conn.execute(
            "SELECT * FROM events WHERE fingerprint_hash = ? ORDER BY timestamp DESC LIMIT 100",
            (fp_hash,)
        ).fetchall()
        threat = conn.execute(
            "SELECT * FROM threat_intel WHERE fingerprint_hash = ?", (fp_hash,)
        ).fetchone()
        return jsonify({
            "attacker": dict(attacker),
            "events": [dict(e) for e in events],
            "threat_intel": dict(threat) if threat else None,
        })


@app.route("/api/attackers/<fp_hash>/events")
def api_attacker_events(fp_hash):
    events = database.get_events(limit=200, src_ip="")
    filtered = [e for e in events if e.get("fingerprint_hash") == fp_hash]
    for e in filtered:
        e["headers"] = json.loads(e.get("headers") or "{}")
    return jsonify(filtered)


@app.route("/api/top/usernames")
def api_top_usernames():
    return jsonify(database.get_usernames_tried())


@app.route("/api/top/passwords")
def api_top_passwords():
    return jsonify(database.get_passwords_tried())


@app.route("/api/report/html")
def api_report_html():
    data = database.export_report_data()
    html = generate_html_report(data, datetime.utcnow().isoformat())
    return Response(
        html,
        mimetype="text/html",
        headers={
            "Content-Disposition": "attachment; filename=honeypot_report.html"
        },
    )


@app.route("/api/report/json")
def api_report_json():
    data = database.export_report_data()
    filename = f"honeypot_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        json.dumps(data, indent=2, default=str),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    database.init_db()
    server_state["db_initialized"] = True
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)