"""Blue team side: detect the artifacts the red side built.

Each rule inspects artifact records produced in ``outputs/lab_target`` and
emits zero or more findings. Findings carry the MITRE technique they map to,
so one rule can surface several techniques (e.g. the tool-drop rule sees both
T1105 ingress and T1036.005 masquerading).

Findings also carry a *fidelity* grade so the report can separate:

* ``high``   - a dedicated signature/data source fired
* ``low``    - only a generic catch-all pattern saw the artifact
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .mitre import RULE_BY_ID
from .util import load_json, now_iso

SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}

GENERIC_RULE = "RULE-CHANGE"


assert GENERIC_RULE in RULE_BY_ID, "GENERIC_RULE must exist in the mitre registry"


@dataclass
class Finding:
    rule_id: str
    rule_name: str
    data_source: str
    technique_id: str
    technique_name: str
    file: str
    ts: str
    event: str
    sev: str
    fidelity: str
    meta: dict

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "data_source": self.data_source,
            "technique_id": self.technique_id,
            "technique_name": self.technique_name,
            "file": self.file,
            "ts": self.ts,
            "event": self.event,
            "severity": self.sev,
            "fidelity": self.fidelity,
            "meta": self.meta,
        }


@dataclass
class BlueContext:
    lab_root: Path
    run_id: str
    ts: str = ""

    def artifacts(self) -> list[dict]:
        idx = self.lab_root / ".purpleteam_index.json"
        return load_json(idx, [])

    def finding(self, artifact: dict, rule_id: str, sev: str, fidelity: str,
                event: str | None = None, technique_id: str | None = None,
                meta: dict | None = None) -> Finding:
        return Finding(
            rule_id=rule_id,
            rule_name=RULE_NAMES.get(rule_id, rule_id),
            data_source=RULE_SOURCES.get(rule_id, ""),
            technique_id=technique_id or artifact.get("technique_id", ""),
            technique_name=artifact.get("technique_name", ""),
            file=artifact.get("file", "-"),
            ts=artifact.get("ts", now_iso()),
            event=event or artifact.get("event", ""),
            sev=sev,
            fidelity=fidelity,
            meta=meta or {},
        )


RULE_NAMES = {r.id: r.name for r in RULE_BY_ID.values()}
RULE_SOURCES = {r.id: r.data_source for r in RULE_BY_ID.values()}

_CATCH_ALL_CATEGORIES = {"sched_task", "phishing", "autostart", "tool_drop", "masquerade"}


def _exact_ids(artifacts: list[dict], *cats: str) -> list[dict]:
    return [a for a in artifacts if a.get("category") in cats]


def _rule_schtask(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "sched_task"):
        if a["technique_id"] != "T1053.005":
            continue
        out.append(ctx.finding(a, "RULE-SCHTASK", "high", "high",
                               f"Scheduled-task creation signal: {a.get('extras',{}).get('task')}"))
    return out


def _rule_attachment(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "phishing"):
        ext = a.get("extras", {}).get("extension", "")
        if ext and ext.lower() in {".docm", ".docx", ".xlsm", ".zip", ".js", ".lnk", ".hta"}:
            out.append(ctx.finding(a, "RULE-DL-ATTACHMENT", "high", "high",
                                   f"Dangerous lure file type {ext} in Downloads"))
    return out


def _rule_autostart(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "autostart"):
        out.append(ctx.finding(a, "RULE-AUTOSTART", "high", "high",
                               "Logon autostart persistence value/shortcut modified"))
    return out


def _rule_ps_obfuscation(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "powershell"):
        ex = a.get("extras", {})
        if ex.get("base64_body") or ex.get("char_math"):
            out.append(ctx.finding(
                a, "RULE-PS-OBFUSC", "high", "high",
                "Obfuscated PowerShell detected (base64/char-char math script block)",
                meta={"line_snippet": ex.get("ps_line", "")[:180]}))
        elif ex.get("ps_line_true"):
            out.append(ctx.finding(a, "RULE-PS-OBFUSC", "medium", "high",
                                   "PowerShell execution observed with encoded-style args"))
    return out


def _rule_discovery(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "discovery"):
        out.append(ctx.finding(a, "RULE-DISCOVERY", "medium", "high",
                               "System discovery burst (hostinfo/sweep) detected"))
    return out


def _rule_tool_drop(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "tool_drop", "masquerade"):
        ex = a.get("extras", {})
        if a["technique_id"] == "T1036.005" or a.get("category") == "masquerade":
            out.append(ctx.finding(a, "RULE-TOOL-DROP", "high", "high",
                                   f"Masqueraded/known-PE appearance: {ex.get('spoof')}",
                                   meta={"renamed_from": ex.get("renamed_from")}))
        else:
            out.append(ctx.finding(a, "RULE-TOOL-DROP", "high", "high",
                                   f"Unexpected tool drop: {ex.get('tool')}"))
    return out


def _rule_exfil(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "exfil"):
        ex = a.get("extras", {})
        ent = float(ex.get("entropy", 0) or 0)
        b64r = float(ex.get("b64ratio", 0) or 0)
        port = int(ex.get("port", 0) or 0)
        if ent >= 5.5 and b64r >= 0.8:
            out.append(ctx.finding(
                a, "RULE-EXFIL", "high", "high",
                f"High-entropy ({ent}) base64 ({b64r:.0%}) outbound burst on local port {port}",
                meta={"port": port, "bytes": ex.get("bytes")}))
        elif ent >= 4.0:
            out.append(ctx.finding(a, "RULE-EXFIL", "medium", "medium",
                                   f"Moderate-entropy upload on port {port} - correlate"))
    return out


def _rule_api_call(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in _exact_ids(ctx.artifacts(), "api"):
        chain = a.get("extras", {}).get("api_chain", "")
        if "CreateThread" in chain:
            out.append(ctx.finding(a, "RULE-API-CALL", "high", "high",
                                   "Native API create->alloc->write->thread execution chain"))
    return out


def _rule_change(ctx: BlueContext) -> list[Finding]:
    out = []
    for a in ctx.artifacts():
        if a.get("category") not in _CATCH_ALL_CATEGORIES:
            continue
        out.append(ctx.finding(a, GENERIC_RULE, "low", "low",
                               "Recent high-sensitivity file activity (catch-all lens)",
                               meta={"pattern": "new-file in sensitive dir"}))
    return out


RULE_FUNCS: dict[str, Callable[[BlueContext], list[Finding]]] = {
    "RULE-SCHTASK": _rule_schtask,
    "RULE-DL-ATTACHMENT": _rule_attachment,
    "RULE-AUTOSTART": _rule_autostart,
    "RULE-PS-OBFUSC": _rule_ps_obfuscation,
    "RULE-DISCOVERY": _rule_discovery,
    "RULE-TOOL-DROP": _rule_tool_drop,
    "RULE-EXFIL": _rule_exfil,
    "RULE-API-CALL": _rule_api_call,
    GENERIC_RULE: _rule_change,
}


def run_detections(lab_root: Path, run_id: str) -> list[dict]:
    ctx = BlueContext(lab_root=lab_root, run_id=run_id, ts=now_iso())
    findings: list[Finding] = []
    for rule_id, fn in RULE_FUNCS.items():
        findings.extend(fn(ctx))
    seen: set[tuple[str, str, str]] = set()
    deduped: list[Finding] = []
    for f in findings:
        key = (f.rule_id, f.technique_id, f.file)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)
    deduped.sort(key=lambda f: (SEVERITY_RANK.get(f.sev, 0), f.ts), reverse=True)
    return [f.as_dict() for f in deduped]