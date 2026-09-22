"""Incident + IOC services."""

import re
import uuid

from .risk import score_incident
from .storage import utcnow

_UID = lambda p: f"{p}_{uuid.uuid4().hex[:8]}"


def new_id(prefix):
    return _UID(prefix)


class IncidentService:
    def __init__(self, store):
        self.store = store

    # ------------------------------------------------------------------ list
    def list(self):
        return sorted(self.store.get("incidents"),
                      key=lambda i: i.get("created_at", ""), reverse=True)

    def get(self, inc_id):
        return self.store.find("incidents", inc_id)

    # ------------------------------------------------------------------ CRUD
    def create(self, payload):
        now = utcnow()
        seq = self.store.seq_no("inc")
        year = now[:4]
        incident = {
            "id": new_id("inc"),
            "ref_no": f"INC-{year}-{seq:04d}",
            "title": payload.get("title") or "Untitled incident",
            "description": payload.get("description", ""),
            "type": payload.get("type", "other"),
            "severity": payload.get("severity", "medium"),
            "status": "open",
            "phase": "open",
            "analyst": payload.get("analyst", "Unassigned"),
            "source": payload.get("source", "Manual"),
            "channel": payload.get("channel", "Portal"),
            "tags": payload.get("tags") or [],
            "context": payload.get("context") or {},
            "impacted_asset": payload.get("impacted_asset", ""),
            "playbook_id": payload.get("playbook_id"),
            "risk_score": 0,
            "ioc_ids": [],
            "notes": [{ "ts": now, "by": "system",
                        "text": f"Incident {incident_ref(payload, seq, now)} logged into triage queue."}],
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
        }
        incident["ref_no"] = f"INC-{year}-{seq:04d}"

        def add(coll):
            coll.append(incident)
            return True, coll
        self.store.mutate("incidents", add)

        # attach any supplied IOCs
        ioc_ids = []
        for ioc in payload.get("iocs") or []:
            rec = self.add_ioc(ioc)
            if rec:
                ioc_ids.append(rec["id"])
        if ioc_ids:
            self._set_iocs(incident["id"], ioc_ids)

        incident["risk_score"] = self._recompute(incident)
        return incident

    def update(self, inc_id, patch):
        incident = self.get(inc_id)
        if not incident:
            return None
        allowed = {"title", "description", "type", "severity", "analyst", "source",
                   "channel", "tags", "context", "impacted_asset"}
        for k in allowed:
            if k in patch:
                incident[k] = patch[k]
        for note in patch.get("notes") or []:
            incident.setdefault("notes", []).append({
                "ts": utcnow(), "by": note.get("by", "analyst"), "text": note.get("text", "")})
        incident["updated_at"] = utcnow()
        incident["risk_score"] = self._recompute(incident)
        self._persist_incident(incident)
        return incident

    def set_phase(self, inc_id, phase):
        incident = self.get(inc_id)
        if not incident:
            return None
        incident["phase"] = phase
        incident["status"] = phase
        if phase == "closed":
            incident["closed_at"] = utcnow()
        elif incident.get("closed_at"):
            incident["closed_at"] = None
        incident["updated_at"] = utcnow()
        self._persist_incident(incident)
        return incident

    def assign_playbook(self, inc_id, pb_id, by="analyst"):
        incident = self.get(inc_id)
        if not incident:
            return None
        incident["playbook_id"] = pb_id
        incident.setdefault("notes", []).append({
            "ts": utcnow(), "by": by,
            "text": f"Playbook {pb_id} attached by {by}."})
        incident["updated_at"] = utcnow()
        self._persist_incident(incident)
        return incident

    def add_note(self, inc_id, text, by="analyst"):
        incident = self.get(inc_id)
        if not incident:
            return None
        incident.setdefault("notes", []).append({"ts": utcnow(), "by": by, "text": text})
        incident["updated_at"] = utcnow()
        self._persist_incident(incident)
        return incident

    # ------------------------------------------------------------------ IOCs
    def add_ioc(self, data):
        iocs = self.store.get("iocs")
        ioc_type = data.get("type", "other")
        value = data.get("value", "").strip()
        if not value:
            return None
        existing = next((i for i in iocs
                         if i.get("type") == ioc_type and i.get("value") == value), None)
        if existing:
            existing["occurrences"] = existing.get("occurrences", 1) + 1
            return existing
        ioc = {
            "id": new_id("ioc"),
            "type": ioc_type,
            "value": value,
            "source": data.get("source", "manual"),
            "first_seen": utcnow(),
            "reputation_score": None,
            "threat_verdict": None,
            "occurrences": 1,
        }
        self.store.update("iocs", iocs + [ioc])
        return ioc

    def set_ioc_verdict(self, ioc_id, verdict, score=None):
        doc = self.store.get("iocs")
        for i in doc:
            if i["id"] == ioc_id:
                i["threat_verdict"] = verdict
                if score is not None:
                    i["reputation_score"] = score
                break
        self.store.update("iocs", doc)

    def iocs_for(self, inc):
        ids = set(inc.get("ioc_ids") or [])
        return [i for i in self.store.get("iocs") if i["id"] in ids]

    def _set_iocs(self, inc_id, ioc_ids):
        incident = self.get(inc_id)
        if not incident:
            return
        incident["ioc_ids"] = list(dict.fromkeys((incident.get("ioc_ids") or []) + ioc_ids))
        incident["risk_score"] = self._recompute(incident)
        self._persist_incident(incident)

    # ------------------------------------------------------------------ misc
    def _recompute(self, incident):
        return score_incident(incident, self.iocs_for(incident), self.store.get("settings"))

    def _persist_incident(self, incident):
        def fn(coll):
            for idx, item in enumerate(coll):
                if item["id"] == incident["id"]:
                    coll[idx] = incident
                    return True, coll
            return False, coll
        self.store.mutate("incidents", fn)


def incident_ref(payload, seq, now):
    return f"INC-{now[:4]}-{seq:04d}"


# convenience for parsing plain-text IOC lines like "ip 1.2.3.4" / "domain evil.com"
def parse_ioc_line(line):
    line = line.strip()
    if not line:
        return None
    parts = line.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in {"ip", "domain", "hash", "url", "email",
                                                "sha256", "md5", "file", "user"}:
        kind = "hash" if parts[0].lower() in {"sha256", "md5"} else parts[0].lower()
        return {"type": kind, "value": parts[1]}
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", line):
        return {"type": "ip", "value": line}
    if re.match(r"^[a-f0-9]{32,128}$", line, re.I):
        return {"type": "hash", "value": line}
    if "://" in line:
        return {"type": "url", "value": line}
    if "." in line and " " not in line:
        return {"type": "domain", "value": line}
    if "@" in line:
        return {"type": "email", "value": line}
    return {"type": "other", "value": line}