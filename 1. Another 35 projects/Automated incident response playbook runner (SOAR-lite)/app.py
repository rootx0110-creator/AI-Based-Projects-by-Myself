"""SOAR-Lite Flask application.

Run:  python app.py
Then: http://127.0.0.1:5000
"""

import json
import os
import sys
import webbrowser
import threading

from flask import Flask, abort, jsonify, render_template, request, send_file

from soar_lite.defaults import (DATA_DIR, PLAYBOOK_DIR, SEVERITIES, INCIDENT_TYPES,
                               ANALYSTS, INTEGRATION_META, BASE_DIR)
from soar_lite.engine import ExecutionEngine
from soar_lite.incident import IncidentService, parse_ioc_line
from soar_lite.metrics import dashboard_snapshot
from soar_lite.playbook import PlaybookService, resolve_templates
from soar_lite import report as report_mod
from soar_lite import seed as seed_mod
from soar_lite.storage import Store, utcnow

store = Store(DATA_DIR)

pb_service = PlaybookService(PLAYBOOK_DIR)
inc_service = IncidentService(store)
engine = ExecutionEngine(store, pb_service, inc_service)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))

if not seed_mod.has_seeded(DATA_DIR):
    seed_mod.seed(store, pb_service, inc_service, engine)
else:
    store.recover()


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def _public_incident(inc):
    d = dict(inc)
    d["iocs"] = inc_service.iocs_for(inc)
    d["executions"] = [{
        "id": e["id"], "playbook_id": e.get("playbook_id"), "playbook_name": e.get("playbook_name"),
        "status": e["status"], "created_at": e.get("created_at"), "finished_at": e.get("finished_at"),
        "step_count": len(e.get("steps") or []),
    } for e in engine.list_for_incident(inc["id"])]
    return d


def _payload():
    return request.get_json(silent=True) or {}


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
@app.route("/")
def page_dashboard():
    return render_template("index.html", active="dashboard", inc_types=INCIDENT_TYPES)


@app.route("/incidents")
def page_incidents():
    return render_template("incidents.html", active="incidents", inc_types=INCIDENT_TYPES,
                           severities=SEVERITIES, analysts=ANALYSTS)


@app.route("/incidents/<inc_id>")
def page_incident(inc_id):
    inc = inc_service.get(inc_id)
    if not inc:
        abort(404)
    return render_template("incident_detail.html", active="incidents", inc_id=inc_id,
                           inc_types=INCIDENT_TYPES, severities=SEVERITIES, analysts=ANALYSTS)


@app.route("/playbooks")
def page_playbooks():
    return render_template("playbooks.html", active="playbooks")


@app.route("/playbooks/<pb_id>")
def page_playbook(pb_id):
    return render_template("playbook_detail.html", active="playbooks", pb_id=pb_id)


@app.route("/executions")
def page_executions():
    return render_template("executions.html", active="executions")


@app.route("/settings")
def page_settings():
    return render_template("settings.html", active="settings")


# ---------------------------------------------------------------------------
# dashboard / metrics
# ---------------------------------------------------------------------------
@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(dashboard_snapshot(store, engine, engine.bus, inc_service))


# ---------------------------------------------------------------------------
# incidents
# ---------------------------------------------------------------------------
@app.route("/api/incidents", methods=["GET"])
def api_incidents():
    return jsonify({
        "incidents": [_public_incident(i) for i in inc_service.list()],
        "filters": {"types": INCIDENT_TYPES, "severities": SEVERITIES, "analysts": ANALYSTS},
    })


@app.route("/api/incidents", methods=["POST"])
def api_create_incident():
    data = _payload()
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    if data.get("ioc_text"):
        parsed = []
        for line in data.get("ioc_text", "").splitlines():
            parsed.append(parse_ioc_line(line))
        data["iocs"] = [p for p in parsed if p]
    inc = inc_service.create(data)
    return jsonify(_public_incident(inc)), 201


@app.route("/api/incidents/<inc_id>", methods=["GET"])
def api_incident(inc_id):
    inc = inc_service.get(inc_id)
    if not inc:
        abort(404)
    return jsonify(_public_incident(inc))


@app.route("/api/incidents/<inc_id>", methods=["PATCH"])
def api_update_incident(inc_id):
    inc = inc_service.update(inc_id, _payload())
    if not inc:
        abort(404)
    return jsonify(_public_incident(inc))


@app.route("/api/incidents/<inc_id>/phase", methods=["POST"])
def api_set_phase(inc_id):
    phase = _payload().get("phase")
    inc = inc_service.set_phase(inc_id, phase)
    if not inc:
        abort(404)
    return jsonify(_public_incident(inc))


@app.route("/api/incidents/<inc_id>/notes", methods=["POST"])
def api_add_note(inc_id):
    inc = inc_service.add_note(inc_id, _payload().get("text", ""), _payload().get("by", "analyst"))
    if not inc:
        abort(404)
    return jsonify(_public_incident(inc))


@app.route("/api/incidents/<inc_id>/iocs", methods=["POST"])
def api_add_ioc(inc_id):
    inc = inc_service.get(inc_id)
    if not inc:
        abort(404)
    ioc = inc_service.add_ioc(_payload())
    if ioc:
        inc["ioc_ids"] = list(dict.fromkeys((inc.get("ioc_ids") or []) + [ioc["id"]]))
        inc["risk_score"] = inc_service._recompute(inc)
        inc_service._persist_incident(inc)
    return jsonify(_public_incident(inc_service.get(inc_id)))


@app.route("/api/incidents/<inc_id>/playbook", methods=["POST"])
def api_attach_playbook(inc_id):
    data = _payload()
    pb_id = data.get("playbook_id")
    inc = inc_service.assign_playbook(inc_id, pb_id, by="analyst")
    if not inc:
        abort(404)
    if data.get("run"):
        execution, err = engine.start(inc, pb_id, ioc_id=data.get("ioc_id"))
        if err:
            return jsonify({"error": err}), 400
        return jsonify({"execution": execution["id"]})
    return jsonify(_public_incident(inc))


# ---------------------------------------------------------------------------
# playbooks
# ---------------------------------------------------------------------------
@app.route("/api/playbooks", methods=["GET"])
def api_playbooks():
    plist = [pb.to_dict() for pb in pb_service.load_all(force=True)]
    if request.args.get("include_steps") == "1":
        return jsonify({"playbooks": plist})
    for p in plist:
        p["steps"] = None
    return jsonify({"playbooks": plist})


@app.route("/api/playbooks/<pb_id>", methods=["GET"])
def api_playbook(pb_id):
    pb = pb_service.get(pb_id)
    if not pb:
        abort(404)
    return jsonify(pb.to_dict())


@app.route("/api/playbooks/<pb_id>/preview", methods=["POST"])
def api_playbook_preview(pb_id):
    """Preview resolved params for a given incident context."""
    pb = pb_service.get(pb_id)
    if not pb:
        abort(404)
    inc_id = _payload().get("incident_id")
    inc = inc_service.get(inc_id) if inc_id else None
    previews = []
    for s in pb.steps:
        if s.get("kind") == "integration":
            previews.append({"pb_step_id": s["id"], "label": s.get("label"),
                             "action": s.get("action"),
                             "params": resolve_templates(s.get("params") or {},
                                                         {"incident": inc or {}, "ioc": {}})})
    return jsonify({"previews": previews})


# ---------------------------------------------------------------------------
# executions
# ---------------------------------------------------------------------------
@app.route("/api/executions", methods=["GET"])
def api_executions():
    return jsonify({"executions": engine.list()})


@app.route("/api/executions/<exec_id>", methods=["GET"])
def api_execution(exec_id):
    ex = engine.get(exec_id)
    if not ex:
        abort(404)
    inc = inc_service.get(ex["incident_id"])
    out = dict(ex)
    out["incident"] = _public_incident(inc) if inc else None
    return jsonify(out)


@app.route("/api/executions/<exec_id>/cancel", methods=["POST"])
def api_cancel_execution(exec_id):
    return jsonify({"cancelled": engine.cancel(exec_id)})


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------
@app.route("/api/incidents/<inc_id>/report", methods=["POST"])
def api_generate_report(inc_id):
    inc = inc_service.get(inc_id)
    if not inc:
        abort(404)
    executions = engine.list_for_incident(inc_id)
    iocs = inc_service.iocs_for(inc)
    path, html = report_mod.render_to_file(store, inc, executions, iocs, pb_service)
    return jsonify({"download_url": f"/reports/{os.path.basename(path)}", "file": os.path.basename(path)})


@app.route("/reports/<path:fname>")
def api_download_report(fname):
    safe = os.path.basename(fname)
    path = os.path.join(store.report_cache, safe)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=safe,
                     mimetype="text/html")


# ---------------------------------------------------------------------------
# settings / admin
# ---------------------------------------------------------------------------
@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify({"settings": store.get("settings"), "integration_meta": INTEGRATION_META})


@app.route("/api/settings", methods=["PUT"])
def api_put_settings():
    data = _payload()
    settings = store.get("settings")
    if "risk_weights" in data:
        settings["risk_weights"] = {**settings.get("risk_weights", {}), **data["risk_weights"]}
    if "instance" in data:
        settings["instance"] = {**settings.get("instance", {}), **data["instance"]}
    if "integrations" in data:
        for key, cfg in data["integrations"].items():
            settings.setdefault("integrations", {})[key] = {**settings["integrations"].get(key, {}), **cfg}
    store.update("settings", settings)
    return jsonify({"settings": settings})


@app.route("/api/admin/reset", methods=["POST"])
def api_reset():
    backup = store.reset(lambda: seed_mod.seed(store, pb_service, inc_service, engine))
    return jsonify({"ok": True, "backup": backup})


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "time": utcnow(),
                    "integrations": engine.bus.health()})


# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found"}), 404
    return render_template("index.html", active=""), 404


if __name__ == "__main__":
    import socket

    def pick_port(preferred):
        preferred = int(preferred)
        for port in range(preferred, preferred + 12):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        return preferred

    port = pick_port(os.environ.get("SOAR_PORT", "5000"))
    url = f"http://127.0.0.1:{port}"
    print("\n  SOAR-Lite - Automated Incident Response Playbook Runner\n"
          f"  -> {url}\n")
    if os.environ.get("SOAR_OPEN_BROWSER", "1") != "0":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port,
            debug=os.environ.get("SOAR_DEBUG") == "1", use_reloader=False)