"""Posture & rule-risk scoring and audit report assembly."""

from __future__ import annotations

import datetime as _dt
import io
import json
import csv
from typing import Dict, List, Optional

from .iprange import is_any
from .rule import (
    Action, FirewallRule, Finding, NatRule, RuleType, SEVERITY_WEIGHTS,
    SENSITIVE_PORTS, Severity,
)

POSTURE_WEIGHTS = {
    Severity.CRITICAL: 18.0,
    Severity.HIGH: 10.0,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 2.0,
    Severity.INFO: 0.5,
}

GRADE_BANDS = [
    (85, 100, "A", "Excellent"),
    (70, 84, "B", "Good"),
    (55, 69, "C", "Acceptable"),
    (40, 54, "D", "Poor"),
    (0, 39, "F", "Critical"),
]


def grade_for(score: float) -> tuple:
    for lo, hi, letter, label in GRADE_BANDS:
        if lo <= int(score) <= hi:
            return letter, label
    return "F", "Critical"


def rule_risk(r: FirewallRule, findings_attached: Optional[List[Finding]] = None) -> int:
    """0–100 heuristic risk of a single rule (higher = riskier to keep)."""
    score = 10
    findings_attached = findings_attached or []
    src_any = bool(r.src_nets) and is_any(r.src_nets)
    dst_any = bool(r.dst_nets) and is_any(r.dst_nets)

    if r.action.is_allow:
        if src_any and dst_any:
            score += 45
        elif src_any or dst_any:
            score += 25
        if r.dst_port_intervals:
            for lo, hi in r.dst_port_intervals:
                for p in range(lo, hi + 1):
                    if p in SENSITIVE_PORTS:
                        score += 15
                        break
                else:
                    continue
                break
        if r.direction.value == "IN":
            score += 10
        if r.protocol == "any":
            score += 5
    else:
        score -= 30  # good hygiene reward

    for f in findings_attached:
        if f.severity == Severity.CRITICAL:
            score += 40
        elif f.severity == Severity.HIGH:
            score += 20
        elif f.severity == Severity.MEDIUM:
            score += 5

    return max(0, min(100, score))


def posture_score(rules: List[FirewallRule],
                  findings: List[Finding]) -> Dict:
    by_sev: Dict[str, int] = {}
    for f in findings:
        by_sev[f.severity.value] = by_sev.get(f.severity.value, 0) + 1
    score = 100.0
    for sev, weight in POSTURE_WEIGHTS.items():
        score -= weight * by_sev.get(sev.value, 0)
    if any(r.rule_type == RuleType.DEFAULT_DENY for r in rules):
        score += 5
    allows = [r for r in rules if r.action.is_allow and r.enabled]
    if allows and all(r.log for r in allows):
        score += 3
    score = max(0.0, min(100.0, score))
    grade, label = grade_for(score)
    return {
        "score": round(score, 1),
        "grade": grade,
        "label": label,
        "by_severity": by_sev,
        "severity_weights": {k.value: v for k, v in SEVERITY_WEIGHTS.items()},
    }


def summary_of(rules: List[FirewallRule]) -> Dict:
    by_action: Dict[str, int] = {}
    by_proto: Dict[str, int] = {}
    by_direction: Dict[str, int] = {}
    for r in rules:
        if r.rule_type == RuleType.DEFAULT_DENY:
            continue
        by_action[r.action.value] = by_action.get(r.action.value, 0) + 1
        by_proto.setdefault(r.protocol, 0)
        by_proto[r.protocol] += 1
        by_direction[r.direction.value] = by_direction.get(r.direction.value, 0) + 1
    return {
        "total": len([r for r in rules if r.rule_type != RuleType.DEFAULT_DENY]),
        "by_action": by_action,
        "by_protocol": by_proto,
        "by_direction": by_direction,
        "allow_count": sum(1 for r in rules
                           if r.action.is_allow and r.rule_type != RuleType.DEFAULT_DENY),
        "deny_count": sum(1 for r in rules
                          if r.action.is_deny and r.rule_type != RuleType.DEFAULT_DENY),
        "enabled": sum(1 for r in rules
                       if r.enabled and r.rule_type != RuleType.DEFAULT_DENY),
    }


def attach_risks(rules: List[FirewallRule],
                 findings: List[Finding]) -> List[Dict]:
    by_rule: Dict[str, List[Finding]] = {}
    for f in findings:
        for rid in f.rule_ids:
            by_rule.setdefault(rid, []).append(f)

    out = []
    for r in rules:
        d = r.to_dict()
        attached = by_rule.get(r.rule_id, [])
        worst = max((f.severity.rank for f in attached), default=0)
        d["risk"] = rule_risk(r, attached)
        d["worst_severity"] = {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM",
                               2: "LOW", 1: "INFO", 0: "NONE"}[worst]
        d["finding_count"] = len(attached)
        # per-level counts
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in attached:
            counts[f.severity.value] += 1
        d["findings"] = counts
        out.append(d)
    return out


def export_csv(report: Dict) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["id", "line", "action", "direction", "protocol", "src_ip",
                    "src_port", "dst_ip", "dst_port", "interface", "log",
                    "risk", "worst_severity", "description", "raw"],
    )
    writer.writeheader()
    for r in report.get("rules", []):
        writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
    return buf.getvalue()


def export_findings_csv(report: Dict) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["id", "severity", "category", "title", "detail",
                    "recommendation", "rule_ids", "line_nos", "confidence"],
    )
    writer.writeheader()
    for f in report.get("findings", []):
        row = {
            "id": f.get("id", ""),
            "severity": f.get("severity", ""),
            "category": f.get("category", ""),
            "title": f.get("title", ""),
            "detail": f.get("detail", ""),
            "recommendation": f.get("recommendation", ""),
            "rule_ids": ";".join(f.get("rule_ids", [])),
            "line_nos": ";".join(str(x) for x in f.get("line_nos", [])),
            "confidence": f.get("confidence", ""),
        }
        writer.writerow(row)
    return buf.getvalue()


def build_report(*, name: str, fmt: str, rules: List[FirewallRule],
                 nat_rules: List[NatRule], findings: List[Finding],
                 warnings: List[str]) -> Dict:
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    posture = posture_score(rules, findings)
    summary = summary_of(rules)
    rule_rows = attach_risks(rules, findings)
    finding_rows = [f.to_dict() for f in findings]
    nat_rows = [n.to_dict() for n in nat_rules]
    return {
        "name": name,
        "format": fmt,
        "generated_at": now,
        "meta": {
            "name": name,
            "format": fmt,
            "warnings": warnings,
            "rule_count": len(rule_rows),
            "nat_count": len(nat_rows),
            "finding_count": len(finding_rows),
        },
        "summary": summary,
        "posture": posture,
        "rules": rule_rows,
        "nats": nat_rows,
        "findings": finding_rows,
    }


def report_json(report: Dict) -> str:
    return json.dumps(report, indent=2)