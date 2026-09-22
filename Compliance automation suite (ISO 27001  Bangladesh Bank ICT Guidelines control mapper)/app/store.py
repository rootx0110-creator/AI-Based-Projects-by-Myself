"""JSON-file backed persistence store."""

import datetime
import json
import os
import threading

from . import config

_LOCK = threading.Lock()

_EMPTY = {
    "organization": "",
    "updated_at": None,
    "entries": {},      # "<framework>::<control_id>" -> {status, owner, notes, evidence, updated}
    "findings": [],     # gap-analysis findings
    "audit_log": [],    # audit trail
}


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def load_all():
    """Load the full state document (with defaults)."""
    if not os.path.exists(config.DB_FILE):
        return json.loads(json.dumps(_EMPTY))
    try:
        with open(config.DB_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        # Corrupt file: keep a backup and start clean rather than crash
        try:
            os.replace(config.DB_FILE, config.DB_FILE + ".bak")
        except OSError:
            pass
        return json.loads(json.dumps(_EMPTY))
    for key, value in _EMPTY.items():
        data.setdefault(key, json.loads(json.dumps(value)))
    return data


def save_all(data):
    """Persist the full state document atomically."""
    data["updated_at"] = _now()
    with _LOCK:
        tmp = config.DB_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, config.DB_FILE)


def set_status(framework, control_id, status, owner=None, notes=None, evidence=None):
    data = load_all()
    key = f"{framework}::{control_id}"
    entries = data["entries"]
    if key not in entries:
        entries[key] = {}
    entry = entries[key]
    if status is not None:
        entry["status"] = status
    if owner is not None:
        entry["owner"] = owner
    if notes is not None:
        entry["notes"] = notes
    if evidence is not None:
        entry["evidence"] = evidence
    entry["updated"] = _now()
    data["audit_log"].append({
        "ts": _now(),
        "action": "update_control",
        "detail": f"{framework}:{control_id} -> {entry.get('status')}",
    })
    # keep the audit log bounded
    if len(data["audit_log"]) > 500:
        data["audit_log"] = data["audit_log"][-500:]
    save_all(data)
    return entry


def bulk_set_status(framework, control_ids, status):
    data = load_all()
    now = _now()
    for cid in control_ids:
        key = f"{framework}::{cid}"
        data["entries"].setdefault(key, {})
        data["entries"][key]["status"] = status
        data["entries"][key]["updated"] = now
    data["audit_log"].append({
        "ts": now,
        "action": "bulk_update",
        "detail": f"{framework}: {len(control_ids)} controls -> {status}",
    })
    save_all(data)


def set_organization(name):
    data = load_all()
    data["organization"] = name
    data["audit_log"].append({"ts": _now(), "action": "set_organization", "detail": name})
    save_all(data)


def set_findings(findings):
    data = load_all()
    data["findings"] = findings
    data["audit_log"].append({
        "ts": _now(),
        "action": "save_findings",
        "detail": f"{len(findings)} findings saved",
    })
    save_all(data)


def append_audit(action, detail):
    data = load_all()
    data["audit_log"].append({"ts": _now(), "action": action, "detail": detail})
    save_all(data)
