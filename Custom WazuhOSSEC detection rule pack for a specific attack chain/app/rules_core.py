"""Rule pack core: data model, statistics, persistence, XML export."""
from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET

# ----------------------------------------------------------------------------
# Attack chain stages (ordered kill chain) with MITRE ATT&CK tactic mapping
# ----------------------------------------------------------------------------
STAGES = [
    {"key": "recon",              "name": "Reconnaissance",          "tactic": "TA0043", "desc": "Probing the target web estate."},
    {"key": "initial",            "name": "Initial Access",          "tactic": "TA0001", "desc": "Gaining an initial foothold via the web app."},
    {"key": "execution",          "name": "Execution",               "tactic": "TA0002", "desc": "Running code on the compromised host."},
    {"key": "persistence",        "name": "Persistence",             "tactic": "TA0003", "desc": "Maintaining access across restarts."},
    {"key": "priv_esc",           "name": "Privilege Escalation",    "tactic": "TA0004", "desc": "Gaining higher-level permissions."},
    {"key": "defense_evasion",    "name": "Defense Evasion",         "tactic": "TA0005", "desc": "Evading or disabling security controls."},
    {"key": "cred_access",        "name": "Credential Access",       "tactic": "TA0006", "desc": "Stealing credentials from the host."},
    {"key": "discovery",          "name": "Discovery",               "tactic": "TA0007", "desc": "Enumerating host and domain resources."},
    {"key": "lateral_move",       "name": "Lateral Movement",        "tactic": "TA0008", "desc": "Moving to other hosts on the network."},
    {"key": "c2",                 "name": "Command & Control",       "tactic": "TA0011", "desc": "Beaconing back to the attacker."},
    {"key": "exfil",              "name": "Exfiltration",            "tactic": "TA0010", "desc": "Transferring data off the estate."},
]
STAGE_BY_KEY = {s["key"]: s for s in STAGES}

SEVERITY_BUCKETS = [
    {"name": "Low",      "lo": 1,  "hi": 4,  "color": "#7f8c8d"},
    {"name": "Medium",   "lo": 5,  "hi": 7,  "color": "#f39c12"},
    {"name": "High",     "lo": 8,  "hi": 11, "color": "#e67e22"},
    {"name": "Critical", "lo": 12, "hi": 16, "color": "#e74c3c"},
]

LOG_SOURCES = [
    "apache_access", "windows_security", "sysmon", "syscheck", "syslog",
    "audit", "firewall", "custom",
]


def severity_bucket(level: int) -> dict | None:
    for b in SEVERITY_BUCKETS:
        if b["lo"] <= level <= b["hi"]:
            return b
    return None


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
class Rule(dict):
    """A single wazuh/osssec rule. Built on a dict for simple JSON persistence."""

    @property
    def rid(self) -> str:
        return str(self.get("id", "")).zfill(6)

    @property
    def level(self) -> int:
        return int(self.get("level", 3))

    @property
    def stage(self) -> str:
        return self.get("stage", "execution")

    @property
    def stage_name(self) -> str:
        return STAGE_BY_KEY.get(self.stage, {}).get("name", self.stage)


def build_rule(rid: int, level: int, stage: str, mitre: str, source: str,
               description: str, xml: str, group: str = "local",
               tags: list | None = None, created_by: str = "builder",
               enabled: bool = True) -> Rule:
    rule = Rule(
        id=rid, level=level, stage=stage, mitre=mitre,
        log_source=source, description=description, xml=xml,
        group=group, tags=tags or [], enabled=enabled,
        created_by=created_by,
    )
    return rule


class RulePack:
    """A set of rules plus packaging/serialization/validation logic."""

    def __init__(self, name: str = "Web-Kill-Chain Detection Pack",
                 version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.rules: list[Rule] = []
        self._next_id = 100000

    # -- serialization -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "rules": [dict(r) for r in self.rules],
            "next_id": self._next_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RulePack":
        pack = cls(data.get("name", "Web-Kill-Chain Detection Pack"),
                   data.get("version", "1.0.0"))
        pack.rules = [Rule(r) for r in data.get("rules", [])]
        pack._next_id = int(data.get("next_id", 100000))
        for r in pack.rules:
            pack._next_id = max(pack._next_id, int(r["id"]) + 1)
        return pack

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "RulePack":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # -- mutation ------------------------------------------------------------
    def add(self, rule: Rule) -> None:
        self.rules.append(rule)
        self._next_id = max(self._next_id, int(rule["id"]) + 1)

    def update(self, rule: Rule) -> bool:
        for i, r in enumerate(self.rules):
            if int(r["id"]) == int(rule["id"]):
                self.rules[i] = rule
                return True
        return False

    def remove(self, rid: int) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if int(r["id"]) != rid]
        return len(self.rules) != before

    def get(self, rid: int) -> Rule | None:
        for r in self.rules:
            if int(r["id"]) == rid:
                return r
        return None

    def allocate_id(self) -> int:
        while self.get(self._next_id):
            self._next_id += 1
        return self._next_id

    def enabled(self) -> list[Rule]:
        return [r for r in self.rules if r.get("enabled", True)]

    # ported library rules are foreign and keep their source ids
    def load_library(self, rules: list[Rule]) -> None:
        for r in rules:
            if not self.get(int(r["id"])):
                self.add(r)

    # -- statistics ----------------------------------------------------------
    def count_by_stage(self) -> dict[str, int]:
        out = {s["key"]: 0 for s in STAGES}
        for r in self.rules:
            if r.get("enabled", True):
                out[r["stage"]] = out.get(r["stage"], 0) + 1
        return out

    def count_by_severity(self) -> dict[str, int]:
        out = {b["name"]: 0 for b in SEVERITY_BUCKETS}
        for r in self.rules:
            if r.get("enabled", True):
                b = severity_bucket(r.level)
                if b:
                    out[b["name"]] += 1
        return out

    @property
    def total(self) -> int:
        return len(self.enabled())

    @property
    def avg_level(self) -> float:
        rs = self.enabled()
        return round(sum(r.level for r in rs) / len(rs), 1) if rs else 0.0

    @property
    def stages_covered(self) -> int:
        return sum(1 for v in self.count_by_stage().values() if v > 0)

    # -- validation ----------------------------------------------------------
    def validate(self) -> list[str]:
        issues: list[str] = []
        ids = {}
        for r in self.rules:
            if not r.get("enabled", True):
                continue
            rid = int(r["id"])
            if rid in ids:
                issues.append(f"Duplicate rule id {rid:06d}.")
            ids[rid] = r
            lvl = r.level
            if not (0 <= lvl <= 16):
                issues.append(f"Rule {rid:06d}: level {lvl} out of range 0-16.")
            if not r.get("description"):
                issues.append(f"Rule {rid:06d}: missing description.")
            if not r.get("stage"):
                issues.append(f"Rule {rid:06d}: missing stage.")
            try:
                ET.fromstring(r["xml"])
            except ET.ParseError as exc:
                issues.append(f"Rule {rid:06d}: XML is not well-formed ({exc}).")
        return issues

    # -- xml export ----------------------------------------------------------
    def render_xml_block(self, ind="  ") -> str:
        # scan for parents so we can order children after their if_sid parent
        lines = [f'<group name="{self.name.lower().replace(" ", "_")},">']
        by_parent: dict[str, list[Rule]] = {}
        roots: list[Rule] = []
        for r in self.enabled():
            sid_text = _extract_if_sid(r["xml"])
            by_parent.setdefault(sid_text, []).append(r)
            if not sid_text:
                roots.append(r)
        # simplest deterministic approach: emit roots, then remaining rules by id
        emitted = set()

        def emit(rule: Rule, depth: int) -> None:
            if int(rule["id"]) in emitted:
                return
            emitted.add(int(rule["id"]))
            for line in rule["xml"].splitlines():
                lines.append(ind * (depth + 1) + line)
            for child in sorted(by_parent.get(str(int(rule["id"])), []),
                                key=lambda x: int(x["id"])):
                emit(child, depth + 1)

        for r in sorted(roots, key=lambda x: int(x["id"])):
            emit(r, 0)
        for k in sorted(by_parent, key=lambda x: int(x) if x.isdigit() else 0):
            if k.isdigit() and not int(k) in emitted:
                for r in sorted(by_parent[k], key=lambda x: int(x["id"])):
                    emit(r, 0)
        lines.append('</group>')
        return "\n".join(lines)

    def export_xml(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write('<!-- packed by RulePackStudio - deploy under /var/ossec/etc/rules/ -->\n')
            f.write(self.render_xml_block())
            f.write('\n')

    # -- json pack export ----------------------------------------------------
    def export_json(self, path: str) -> None:
        self.save(path)

    def merge(self, other: "RulePack") -> int:
        added = 0
        for r in other.rules:
            if not self.get(int(r["id"])):
                self.add(r)
                added += 1
        return added


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _extract_if_sid(xml: str) -> str:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return ""
    return (root.get("if_sid") or "").strip()


def data_dir() -> str:
    """Runtime data folder lives next to the exe (or cwd in dev)."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(base, "data")
    os.makedirs(d, exist_ok=True)
    return d


def default_data_paths() -> tuple[str, str, str]:
    d = data_dir()
    return (
        os.path.join(d, "rulepack.json"),
        os.path.join(d, "exports"),
        os.path.join(d, "local_rules.xml"),
    )


def esc(s: str) -> str:
    """XML.escape alias kept independent of html module deprecation churn."""
    return ET.escape(s) if hasattr(ET, "escape") else s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def toxml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


# Builder XML rendering --------------------------------------------------------
def render_builder_xml(rid: int, level: int, description: str, group: str,
                       decoder: str = "", pattern_kind: str = "match",
                       pattern: str = "", field: str = "", value: str = "",
                       parent_id: str = "", mitre: str = "") -> str:
    parts = [f'<rule id="{rid}" level="{level}">']
    if parent_id:
        parts.append(f'  <if_sid>{parent_id}</if_sid>')
    if decoder:
        parts.append(f'  <decoded_as>{toxml_escape(decoder)}</decoded_as>')
    if pattern_kind == "match" and pattern:
        parts.append(f'  <match>{toxml_escape(pattern)}</match>')
    elif pattern_kind == "regex" and pattern:
        parts.append(f'  <regex>{toxml_escape(pattern)}</regex>')
    elif pattern_kind == "field" and field and value:
        parts.append(f'  <field name="{toxml_escape(field)}">{toxml_escape(value)}</field>')
    parts.append(f'  <description>{toxml_escape(description)}</description>')
    g = group if group else "local"
    parts.append(f'  <group>{toxml_escape(g)}</group>')
    parts.append('</rule>')
    return "\n".join(parts)