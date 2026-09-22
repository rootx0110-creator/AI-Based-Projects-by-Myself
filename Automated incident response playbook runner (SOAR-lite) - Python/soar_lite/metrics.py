"""Dashboard/aggregation helpers."""

import time

from .defaults import LIFECYCLE_ORDER, SEVERITIES


def dashboard_snapshot(store, execution_engine, integration_bus, incident_service):
    incidents = incident_service.list()
    executions = execution_engine.list()
    iocs = store.get("iocs")

    now = time.time()

    open_incidents = [i for i in incidents if i.get("status") not in ("closed", "recovered")]
    critical = [i for i in incidents if i.get("severity") == "critical"]
    high = [i for i in incidents if i.get("severity") == "high"]

    live = [e for e in executions if e.get("status") in ("queued", "running")]
    done = [e for e in executions if e.get("status") in ("completed", "completed_with_errors", "failed")]
    success = [e for e in done if e.get("status") in ("completed", "completed_with_errors")]

    active_analysts = {i.get("analyst") for i in open_incidents if i.get("analyst") and i.get("analyst") != "Unassigned"}

    total_latency = sum((e.get("steps") or []) and sum(
        (s.get("latency_ms") or 0) for s in e.get("steps") or []) for e in executions)

    avg_score = sum((i.get("risk_score") or 0) for i in incidents) / len(incidents) if incidents else 0

    by_type = {}
    for i in incidents:
        by_type[i.get("type", "other")] = by_type.get(i.get("type", "other"), 0) + 1

    by_sev = {s: sum(1 for i in incidents if i.get("severity") == s) for s in SEVERITIES}

    by_phase = {p: sum(1 for i in incidents if i.get("phase") == p) for p in LIFECYCLE_ORDER}

    threats = [i for i in iocs if i.get("threat_verdict") in ("malicious", "ransomware", "suspicious")]

    return {
        "totals": {
            "incidents": len(incidents),
            "open": len(open_incidents),
            "critical": len(critical),
            "high": len(high),
            "iocs": len(iocs),
            "threat_iocs": len(threats),
            "executions": len(executions),
            "running": len(live),
            "completed": len(success),
            "failed": len(done) - len(success),
            "analysts_active": len(active_analysts),
            "avg_risk": round(avg_score, 1),
        },
        "by_type": by_type,
        "by_sev": by_sev,
        "by_phase": by_phase,
        "live_runs": [
            {"id": e["id"], "incident_id": e.get("incident_id"), "ref_no": e.get("ref_no"), "playbook": e.get("playbook_name"),
             "status": e["status"], "run_time_seconds": elapsed_since(e.get("created_at"))}
            for e in live
        ],
        "integrations": integration_bus.health(),
    }


def elapsed_since(ts):
    try:
        import datetime
        t = datetime.datetime.strptime(str(ts), "%Y-%m-%dT%H:%M:%SZ")
        return max(0, round((datetime.datetime.utcnow() - t).total_seconds()))
    except Exception:
        return 0