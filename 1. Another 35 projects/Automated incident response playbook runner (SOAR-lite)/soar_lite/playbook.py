"""Playbook loading, validation and template resolution."""

import json
import os
import re

from .defaults import PLAYBOOK_DIR

VALID_KINDS = {"title", "task", "integration", "condition", "delay"}
VALID_OPS = {"eq", "neq", "contains", "regex", "exists", "gt"}
VALID_ACTIONS = {
    "siem.query", "ti.url_reputation", "ti.ip_reputation", "ti.hash_reputation",
    "sandbox.submit", "edr.isolate_endpoint", "edr.kill_process", "edr.quarantine_file",
    "fw.block_ip", "dns.sinkhole", "dns.query_burst", "mail.trace", "mail.quarantine",
    "ticketing.update", "ticketing.create", "iam.revoke_sessions", "dcdn.scrub",
    "waf.rate_limit",
}

_TMPL = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


class Playbook:
    def __init__(self, raw):
        self.raw = raw
        self.id = raw["id"]
        self.name = raw["name"]
        self.description = raw.get("description", "")
        self.triggers = raw.get("triggers", [])
        self.mitre = raw.get("mitre", [])
        self.steps = raw.get("steps", [])
        self.step_ids = [s["id"] for s in self.steps]

    def step(self, step_id):
        for s in self.steps:
            if s["id"] == step_id:
                return s
        return None

    def first_step(self):
        return self.steps[0] if self.steps else None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "triggers": self.triggers,
            "mitre": self.mitre,
            "version": self.raw.get("version", "1.0"),
            "estimated_minutes": self.raw.get("estimated_minutes", 0),
            "step_count": len(self.steps),
            "steps": self.steps,
        }


class PlaybookService:
    def __init__(self, directory=None):
        self.directory = directory or PLAYBOOK_DIR
        self._cache = {}

    def load_all(self, force=False):
        if self._cache and not force:
            return list(self._cache.values())
        pick = {}
        if os.path.isdir(self.directory):
            for fn in sorted(os.listdir(self.directory)):
                if fn.endswith(".json"):
                    path = os.path.join(self.directory, fn)
                    try:
                        with open(path, "r", encoding="utf-8") as fh:
                            raw = json.load(fh)
                        pb = Playbook(raw)
                        self.validate(pb)
                        pick[raw["id"]] = pb
                    except Exception as exc:
                        print(f"[playbooks] skipping {fn}: {exc}")
        self._cache = pick
        return list(pick.values())

    def get(self, pb_id, force=False):
        self.load_all(force=force)
        return self._cache.get(pb_id)

    def suggest(self, incident_type):
        """Return a playbook id matching the incident type (first trig match)."""
        for pb in self.load_all():
            for trig in pb.triggers:
                if trig == incident_type or trig in incident_type or incident_type in trig:
                    return pb.id
        return None

    # ------------------------------------------------------------------
    def validate(self, pb, raise_on_error=True):
        errors = []
        ids = set()
        for step in pb.steps:
            if not step.get("id"):
                errors.append(f"step missing id: {step}")
            else:
                ids.add(step["id"])
            if step.get("kind") not in VALID_KINDS:
                errors.append(f"{step.get('id')}: bad kind {step.get('kind')}")
            if step.get("kind") == "integration" and step.get("action") not in VALID_ACTIONS:
                errors.append(f"{step.get('id')}: unknown action {step.get('action')}")
            if step.get("kind") == "condition":
                t = step.get("test") or {}
                if t.get("op") not in VALID_OPS:
                    errors.append(f"{step.get('id')}: bad condition op {t.get('op')}")
        for step in pb.steps:
            for ref in (step.get("then"), step.get("else"), step.get("goto"), step.get("next")):
                if ref and ref not in ids:
                    errors.append(f"{step.get('id')}: dangling ref {ref}")
            branches = step.get("on") or []
            if isinstance(branches, str):
                branches = []
            for item in branches:
                if item.get("next") and item["next"] not in ids:
                    errors.append(f"{step.get('id')}: dangling on/branch ref {item.get('next')}")
        if raise_on_error and errors:
            raise ValueError(f"playbook {pb.id}: " + "; ".join(errors))
        return errors


# --------------------------------------------------------------------------
# template resolution
# --------------------------------------------------------------------------
def resolve_templates(value, context):
    """Recursively resolve {{path.to.key}} references inside value."""
    if isinstance(value, str):
        def repl(m):
            return deep_get(context, m.group(1)) or ""
        return _TMPL.sub(repl, value)
    if isinstance(value, dict):
        return {k: resolve_templates(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_templates(v, context) for v in value]
    return value


def deep_get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
        if cur is None:
            return None
    return cur