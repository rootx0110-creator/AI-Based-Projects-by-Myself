"""Wireless Network Auditor - Flask web application."""

import logging
import os
import socket
import sys
import threading
import traceback
import webbrowser
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, send_file, session

from config import Config, FROZEN, log
from database import db
from capture import scanner, handshake, deauth, analyzer, interfaces
from reports import generator

Config.ensure_dirs()
db.init_db(Config.DB_PATH)

app = Flask(__name__,
            template_folder=Config.TEMPLATE_DIR,
            static_folder=Config.STATIC_DIR)
app.secret_key = Config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

if FROZEN:
    # Windowed exes have no console: keep every output visible in auditor.log.
    try:
        _log_fh = open(os.path.join(Config.DATA_DIR, "auditor.log"), "a", encoding="utf-8")
        sys.stdout = _log_fh
        sys.stderr = _log_fh
    except Exception:
        pass


def _thread_excepthook(args):
    try:
        log("THREAD EXC: " + "".join(
            traceback.format_exception(args.exc_type, args.exc_value,
                                       args.exc_traceback)))
    except Exception:
        pass


threading.excepthook = _thread_excepthook

_fh = logging.FileHandler(os.path.join(Config.DATA_DIR, "auditor.log"), encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
app.logger.addHandler(_fh)
app.logger.setLevel(logging.DEBUG)
for _lg in (logging.getLogger("werkzeug"),):
    _lg.addHandler(_fh)
    _lg.setLevel(logging.INFO)

_START_T = datetime.now(timezone.utc).timestamp()


@app.errorhandler(500)
def _handle_500(e):
    app.logger.exception("500 Internal Server Error")
    return jsonify({"ok": False, "detail": str(e)}), 500


@app.errorhandler(404)
def _handle_404(e):
    return jsonify({"ok": False, "detail": "Not found"}), 404


def _now():
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Persist a finished capture (called once per session from the status poll).
# --------------------------------------------------------------------------
def _maybe_persist(status):
    if (status.get("terminal") and status.get("session_id") is None
            and status.get("started_at")):
        started = status["started_at"]
        started_dt = datetime.fromisoformat(started)
        ended = _now()
        ended_dt = datetime.fromisoformat(ended)
        duration = max(0.0, (ended_dt - started_dt).total_seconds())
        sid = db.create_session(
            Config.DB_PATH, started=started,
            ssid=status.get("ssid"), bssid=status.get("bssid"),
            channel=status.get("channel"), seed=status.get("seed"))
        st = "COMPLETE" if status.get("state") == handshake.STATE_COMPLETE else (
            "PARTIAL" if status.get("eapol_messages", 0) >= 1 else "ABORTED")
        db.finish_session(
            Config.DB_PATH, sid, ended, duration,
            status.get("packets") or 0, status.get("eapol_messages") or 0,
            st, status.get("deauth_sent") or 0)
        if status.get("bssid"):
            db.bump_capture_count(Config.DB_PATH, status["bssid"])
        handshake._set(session_id=sid)
        return sid
    return status.get("session_id")


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
class PageName:
    DASHBOARD = "dashboard"
    SCANNER = "scanner"
    CAPTURE = "capture"
    REPORTS = "reports"


@app.route("/")
def index():
    return render_template("index.html", engine=Config.ENGINE, page=PageName.DASHBOARD)


@app.route("/scanner")
def scanner_page():
    return render_template("scanner.html", engine=Config.ENGINE, page=PageName.SCANNER)


@app.route("/capture")
def capture_page():
    from flask import json as fj
    last = session.get("last_target")
    return render_template("capture.html", engine=Config.ENGINE,
                           page=PageName.CAPTURE, last_target=fj.dumps(last or {}))


@app.route("/reports")
def reports_page():
    return render_template("reports.html", engine=Config.ENGINE, page=PageName.REPORTS)


# --------------------------------------------------------------------------
# Scanner API
# --------------------------------------------------------------------------
@app.post("/api/scan")
def api_scan():
    try:
        nets = scanner.scan()
    except Exception as exc:
        app.logger.exception("scanner.scan() failed")
        return jsonify({"ok": False, "detail": f"Scan failed: {exc}"}), 500
    try:
        for n in nets:
            db.upsert_network(Config.DB_PATH, n)
    except Exception as exc:
        app.logger.exception("db.upsert_network() failed")
    try:
        session["scan_count"] = session.get("scan_count", 0) + 1
    except Exception:
        pass
    return jsonify({"ok": True, "count": len(nets), "networks": nets})


@app.get("/api/networks")
def api_networks():
    nets = scanner.last_scan().get("networks")
    saved = db.list_networks(Config.DB_PATH)
    if not nets:
        ens = [{
            "ssid": n["ssid"], "bssid": n["bssid"], "channel": n["channel"],
            "signal_dbm": n["signal_dbm"], "encryption": n["encryption"],
            "clients": n["clients"], "capture_count": n.get("capture_count", 0),
        } for n in saved]
        return jsonify({"ok": True, "from_cache": False, "networks": ens,
                        "last_scan_at": None})
    return jsonify({"ok": True, "from_cache": True, "networks": nets,
                    "last_scan_at": scanner.last_scan().get("last_scan_at")})


@app.post("/api/select")
def api_select():
    body = request.get_json(silent=True) or {}
    session["last_target"] = {
        "ssid": body.get("ssid"),
        "bssid": body.get("bssid"),
        "channel": body.get("channel"),
        "encryption": body.get("encryption", ""),
        "signal_dbm": body.get("signal_dbm"),
    }
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Capture API
# --------------------------------------------------------------------------
@app.post("/api/capture/start")
def api_capture_start():
    body = request.get_json(silent=True) or {}
    ssid = body.get("ssid") or "LAB-AP-2.4G"
    bssid = body.get("bssid")
    channel = body.get("channel")
    deauth_mode = bool(body.get("deauth"))
    if not bssid:
        return jsonify({"ok": False, "detail": "Missing bssid"}), 400
    st = handshake.start_capture(ssid, bssid, channel or 1, deauth=deauth_mode)
    session["last_target"] = {"ssid": ssid, "bssid": bssid,
                              "channel": channel, "deauth": deauth_mode}
    return jsonify({"ok": True, "status": st})


@app.post("/api/capture/stop")
def api_capture_stop():
    was = handshake.stop()
    st = handshake.status()
    return jsonify({"ok": True, "status": was, "final": st})


@app.get("/api/capture/status")
def api_capture_status():
    st = handshake.status()
    _maybe_persist(st)
    st = handshake.status()
    return jsonify(st)


@app.post("/api/deauth")
def api_deauth():
    body = request.get_json(silent=True) or {}
    bssid = body.get("bssid") or (handshake.status().get("bssid"))
    if not bssid:
        return jsonify({"ok": False, "detail": "No target BSSID."}), 400
    result = deauth.send_deauth(bssid, body.get("count", 5))
    return jsonify(result)


@app.get("/api/capture/clear")
def api_capture_clear():
    from flask import json as fj
    handshake.reset()
    session.pop("last_target", None)
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Reports API
# --------------------------------------------------------------------------
@app.post("/api/reports/generate")
def api_reports_generate():
    body = request.get_json(silent=True) or {}
    sid = body.get("session_id")
    if not sid:
        active = handshake.status()
        _maybe_persist(active)
        sid = handshake.status().get("session_id")
    if not sid:
        return jsonify({"ok": False, "detail": "No completed session to report."}), 400
    sess = db.get_session(Config.DB_PATH, sid)
    if not sess:
        return jsonify({"ok": False, "detail": "Session not found."}), 404
    net = db.network_by_bssid(Config.DB_PATH, sess["bssid"]) if sess["bssid"] else None
    extra = {"networks_in_range": db.stats(Config.DB_PATH)["networks"]}
    rid, file_path, _data = generator.generate(sess, net, extra)
    return jsonify({"ok": True, "report_id": rid, "file_name": os.path.basename(file_path),
                    "score": _data["analysis"]["score"]})


@app.get("/api/reports")
def api_reports():
    return jsonify({"ok": True, "reports": db.list_reports(Config.DB_PATH)})


@app.get("/reports/<int:report_id>/html")
def api_report_html(report_id):
    rep = db.get_report(Config.DB_PATH, report_id)
    if not rep:
        return jsonify({"ok": False, "detail": "Report not found."}), 404
    path = os.path.join(Config.OUT_DIR, rep["file_name"])
    if not os.path.exists(path):
        return jsonify({"ok": False, "detail": "Report file missing on disk."}), 404
    return send_file(path, mimetype="text/html")


@app.get("/api/reports/<int:report_id>/download")
def api_report_download(report_id):
    rep = db.get_report(Config.DB_PATH, report_id)
    if not rep:
        return jsonify({"ok": False, "detail": "Report not found."}), 404
    path = os.path.join(Config.OUT_DIR, rep["file_name"])
    if not os.path.exists(path):
        return jsonify({"ok": False, "detail": "Report file missing on disk."}), 404
    return send_file(path, as_attachment=True, download_name=rep["file_name"],
                     mimetype="text/html")


@app.post("/api/reports/<int:report_id>/delete")
def api_report_delete(report_id):
    fname = db.delete_report(Config.DB_PATH, report_id)
    if fname:
        path = os.path.join(Config.OUT_DIR, fname)
        if os.path.exists(path):
            os.remove(path)
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# System / misc API
# --------------------------------------------------------------------------
@app.get("/api/system")
def api_system():
    st = handshake.status()
    ifaces = interfaces.list_interfaces()
    current = interfaces.current_iface()
    live = Config.ENGINE == "live"
    adapter_ok = True
    if live:
        if current:
            adapter_ok = current in {i["name"] for i in ifaces}
        else:
            adapter_ok = False
    return jsonify({
        "engine": Config.ENGINE,
        "version": Config.VERSION,
        "npcap": interfaces.npcap_available(),
        "aircrack": interfaces.aircrack_available(),
        "adapter": "simulated" if not live else current,
        "adapter_ok": adapter_ok,
        "interfaces": [i for i in ifaces if i.get("is_wifi")],
        "ifaces_total": len(ifaces),
        "uptime_s": round((datetime.now(timezone.utc).timestamp() - _START_T), 1),
        "capture_active": st["running"],
        "state": st["state"],
    })


@app.get("/api/system/interfaces")
def api_system_interfaces():
    ifaces = interfaces.list_interfaces()
    return jsonify({
        "ok": True,
        "current": interfaces.current_iface(),
        "npcap": interfaces.npcap_available(),
        "aircrack": interfaces.aircrack_available(),
        "interfaces": ifaces,
    })


@app.post("/api/system/iface")
def api_system_set_iface():
    body = request.get_json(silent=True) or {}
    name = (body.get("iface") or "").strip()
    if not name:
        return jsonify({"ok": False, "detail": "Missing iface name."}), 400
    ifaces = interfaces.list_interfaces()
    if name not in {i["name"] for i in ifaces}:
        return jsonify({"ok": False, "detail": f"Interface '{name}' not found."}), 400
    interfaces.set_iface(name)
    return jsonify({"ok": True, "iface": name})


@app.get("/api/stats")
def api_stats():
    return jsonify({"ok": True, "stats": db.stats(Config.DB_PATH)})


@app.get("/api/sessions")
def api_sessions():
    return jsonify({"ok": True, "sessions": db.list_sessions(Config.DB_PATH)})


# --------------------------------------------------------------------------
def _pick_free_port(host, start):
    for port in range(start, start + 20):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((host, port))
            s.close()
            return port
        except OSError:
            s.close()
    return start


def _running_auditor(url, timeout=2.0):
    """Returns the version string if a WirelessNetworkAuditor serves `url`, else None."""
    try:
        import json as _json
        import urllib.request
        with urllib.request.urlopen(url + "/api/system", timeout=timeout) as r:
            if r.status == 200:
                return _json.loads(r.read().decode("utf-8")).get("version")
    except Exception:
        pass
    return None


if __name__ == "__main__":
    import traceback

    def _excepthook(et, ev, tb):
        log("UNCAUGHT: " + "".join(traceback.format_exception(et, ev, tb)))

    sys.excepthook = _excepthook
    try:
        Config.ensure_dirs()
        db.init_db(Config.DB_PATH)
        host = Config.HOST
        port = _pick_free_port(host, Config.PORT)
        default_url = f"http://{host}:{Config.PORT}"
        if port != Config.PORT:
            running_v = _running_auditor(default_url)
            if running_v == Config.VERSION:
                # An up-to-date instance already serves the default port.
                webbrowser.open(default_url)
                log(f"Instance v{running_v} already running at {default_url} - opening it and exiting.")
                sys.exit(0)
            log(f"Port {Config.PORT} busy (running version {running_v or 'unknown'}) - this instance uses port {port}.")
        url = f"http://{host}:{port}"
        if FROZEN:
            threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        log("=" * 62)
        log(f"  {Config.APP_NAME} v{Config.VERSION}")
        log(f"  Engine : {Config.ENGINE}  ({'real capture' if Config.ENGINE == 'live' else 'simulation - safe demo'})")
        log(f"  URL    : {url}")
        log("  ONLY use this against your OWN lab access point.")
        log("=" * 62)
        app.run(host=host, port=port, debug=False)
    except Exception:
        _excepthook(*sys.exc_info())
        log("Server exited with an error - see lines above.")