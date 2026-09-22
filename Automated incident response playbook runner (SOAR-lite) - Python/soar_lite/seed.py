"""First-run demo data seeder.

Creates a believable SOC state: incidents in various lifecycle phases, attached
IOCs, completed execution history, plus one live run that keeps animating on
the dashboard after first launch.
"""

import os
import time

from .defaults import COMMON_INCIDENT_CONTEXT, IOC_SAMPLES, PLAYBOOK_BY_TYPE
from .incident import IncidentService
from .storage import utcnow

SEED_MARKER = ".seed_marker"


def has_seeded(data_dir):
    return os.path.exists(os.path.join(data_dir, SEED_MARKER))


def mark_seeded(data_dir):
    with open(os.path.join(data_dir, SEED_MARKER), "w", encoding="utf-8") as fh:
        fh.write(utcnow())


def seed(store, pb_service, incident_service, engine):
    """Populate demo incidents + executions. Returns list of incident ids."""
    store.recover()
    created = []

    specs = [
        {"title": "Ransomware encryption wave on finance workstations",
         "type": "ransomware", "severity": "critical", "analyst": "K. Tanaka",
         "source": "EDR Detection", "impacted_asset": "FIN-WS-011",
         "tags": ["ransomware", "encryption", "t1486"],
         "context": COMMON_INCIDENT_CONTEXT["ransomware"]},
        {"title": "Malicious URL sowed via phishing campaign to 38 mailboxes",
         "type": "phishing", "severity": "high", "analyst": "A. Reyes",
         "source": "User Report", "impacted_asset": "MAIL-GW-SECONDARY",
         "tags": ["phishing", "credential-theft"],
         "context": COMMON_INCIDENT_CONTEXT["phishing"]},
        {"title": "Impossible travel detected for VPN + O365 account",
         "type": "unauthorized_access", "severity": "high", "analyst": "M. Okafor",
         "source": "Identity Provider", "impacted_asset": "VPN-EDGE-FW2",
         "tags": ["atop", "mfa"],
         "context": COMMON_INCIDENT_CONTEXT["unauthorized_access"]},
        {"title": "Trojan beacon observed from HR workstation",
         "type": "malware", "severity": "medium", "analyst": "S. Lindqvist",
         "source": "EDR Detection", "impacted_asset": "HR-WS-024",
         "tags": ["trojan", "c2"],
         "context": COMMON_INCIDENT_CONTEXT["malware"]},
        {"title": "Volumetric DDoS against retail frontend edge",
         "type": "ddos", "severity": "medium", "analyst": "J. Moreau",
         "source": "WAF Alert", "impacted_asset": "WEB-01-GATEWAY",
         "tags": ["availability", "ddos"],
         "context": COMMON_INCIDENT_CONTEXT["ddos"]},
    ]

    for i, spec in enumerate(specs):
        iocs = IOC_SAMPLES.get(spec["type"], [])
        inc = incident_service.create({
            "title": spec["title"], "type": spec["type"], "severity": spec["severity"],
            "analyst": spec["analyst"], "source": spec["source"],
            "impacted_asset": spec["impacted_asset"], "tags": spec["tags"],
            "context": spec["context"],
            "description": f"Demo incident via seeder: {spec['title']}.",
            "iocs": [{"type": t, "value": v, "source": "seed"} for t, v in iocs],
        })
        pb_id = PLAYBOOK_BY_TYPE.get(inc["type"]) or "pb_malware"
        incident_service.assign_playbook(inc["id"], pb_id, by="seeder")
        created.append(inc)

    # one completed synthetic run on the account-compromise incident
    _run_synthetic(store, incident_service, engine, created[2])

    # stage lifecycle phases (live phishing run stays contained on its own)
    incident_service.set_phase(created[0]["id"], "contained")
    incident_service.set_phase(created[2]["id"], "recovered")
    incident_service.set_phase(created[3]["id"], "recovered")

    # start a LIVE run on the phishing incident so the dashboard animates
    live = created[1]
    engine.start(live, PLAYBOOK_BY_TYPE.get(live["type"]) or "pb_phishing",
                 ioc_id=(live.get("ioc_ids") or [None])[0])

    incident_service.store.update(
        "incidents",
        sorted(incident_service.store.get("incidents"),
               key=lambda i: i.get("created_at", ""), reverse=True))
    mark_seeded(store.data_dir)
    return created


def _run_synthetic(store, incident_service, engine, incident):
    """Run a playbook to completion, waiting for the worker to finish."""
    exec_, err = engine.start(incident, incident.get("playbook_id"),
                              ioc_id=(incident.get("ioc_ids") or [None])[0])
    if not exec_:
        return
    deadline = time.time() + 30
    while time.time() < deadline:
        execution = engine.get(exec_["id"])
        if execution and execution["status"] not in ("queued", "running"):
            break
        time.sleep(0.5)
    execution = engine.get(exec_["id"])
    if execution and execution["status"] not in ("completed", "completed_with_errors", "failed", "cancelled"):
        steps = execution.get("steps") or []
        for s in steps:
            if s["status"] in ("pending", "running"):
                s.update({"status": "skipped", "finished_at": utcnow(),
                          "output": s.get("output") or {"note": "seed timeout"}})
        execution["status"] = "completed"
        execution["finished_at"] = utcnow()
        store.update("executions", store.get("executions"))