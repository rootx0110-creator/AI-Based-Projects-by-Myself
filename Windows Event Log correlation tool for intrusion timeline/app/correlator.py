"""Correlation engine: runs MITRE rules over events, builds alerts,
assigns kill-chain phases and groups related alerts into incident chains.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Optional

from .models import (Alert, AnalysisResult, EventRecord, IncidentChain,
                     Phase, Rule, Severity)
from .parser import ParseCanceled
from .rules import RuleContext, build_rules

# Map of event IDs that are strongly associated with a kill-chain phase.
# Used to tag events so the raw timeline has sensible phase colors.
_PHASE_BY_EVENT: dict = {
    4625: Phase.RECON, 4771: Phase.RECON,
    4740: Phase.INITIAL_ACCESS,
    4624: Phase.INITIAL_ACCESS, 4627: Phase.INITIAL_ACCESS,
    4648: Phase.LATERAL_MOVEMENT, 4778: Phase.LATERAL_MOVEMENT,
    4779: Phase.LATERAL_MOVEMENT,
    5145: Phase.LATERAL_MOVEMENT, 5143: Phase.LATERAL_MOVEMENT,
    4688: Phase.EXECUTION, 4104: Phase.EXECUTION,
    4698: Phase.PERSISTENCE, 4700: Phase.PERSISTENCE, 4702: Phase.PERSISTENCE,
    4697: Phase.PERSISTENCE, 7045: Phase.PERSISTENCE,
    4657: Phase.PERSISTENCE, 4663: Phase.CREDENTIAL_ACCESS,
    4656: Phase.CREDENTIAL_ACCESS,
    4672: Phase.PRIV_ESCALATION, 4673: Phase.PRIV_ESCALATION,
    4674: Phase.PRIV_ESCALATION,
    4768: Phase.CREDENTIAL_ACCESS, 4769: Phase.CREDENTIAL_ACCESS,
    4662: Phase.CREDENTIAL_ACCESS, 5379: Phase.CREDENTIAL_ACCESS,
    5381: Phase.CREDENTIAL_ACCESS, 5382: Phase.CREDENTIAL_ACCESS,
    4798: Phase.RECON, 4799: Phase.RECON,
    5140: Phase.RECON, 5156: Phase.EXFILTRATION,
    1102: Phase.DEFENSE_EVASION,
}


def _phase_for_tactic(tactic: str) -> Phase:
    mapping = {
        "Reconnaissance": Phase.RECON,
        "Discovery": Phase.RECON,
        "Initial Access": Phase.INITIAL_ACCESS,
        "Execution": Phase.EXECUTION,
        "Persistence": Phase.PERSISTENCE,
        "Privilege Escalation": Phase.PRIV_ESCALATION,
        "Credential Access": Phase.CREDENTIAL_ACCESS,
        "Lateral Movement": Phase.LATERAL_MOVEMENT,
        "Defense Evasion": Phase.DEFENSE_EVASION,
        "Command and Control": Phase.DEFENSE_EVASION,
        "Exfiltration": Phase.EXFILTRATION,
        "Impact": Phase.IMPACT,
    }
    return mapping.get(tactic, Phase.UNKNOWN)


def _tag_phases(events: List[EventRecord], alerts: List[Alert]) -> None:
    for e in events:
        e.phase = _PHASE_BY_EVENT.get(e.event_id, e.phase)
    for a in alerts:
        phase = _phase_for_tactic(a.tactic)
        for e in a.events:
            e.phase = phase
            if a.id not in e.alert_ids:
                e.alert_ids.append(a.id)


def _chain_key(alert: Alert) -> str:
    """Best-effort grouping key: source IP > subject user > target host."""
    for e in alert.events:
        ip = e.source_ip
        if ip and ip not in ("-", "::1", "?") and not ip.startswith("127."):
            return "ip:" + ip.lower()
    users = {e.subject_user or e.target_user for e in alert.events}
    users.discard("")
    if users:
        return "user:" + sorted(users)[0].lower()
    hosts = {e.target_host for e in alert.events}
    hosts.discard("")
    if hosts:
        return "host:" + sorted(hosts)[0].lower()
    comps = {e.computer for e in alert.events if e.computer}
    if comps:
        return "host:" + sorted(comps)[0].lower()
    return "host:unknown"


def _alert_start(a: Alert) -> datetime:
    st = a.start
    if st is not None:
        return st
    return datetime.fromtimestamp(0)


class Correlator:
    def __init__(self, events: List[EventRecord], rules: Optional[List[Rule]] = None):
        self.ctx = RuleContext(events)
        self.rules = rules or build_rules()
        self.events = events
        self.alerts: List[Alert] = []
        self.chains: List[IncidentChain] = []
        self._next_id = 1

    def run(
        self,
        progress: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> AnalysisResult:
        total = len(self.rules)
        for i, rule in enumerate(self.rules):
            if cancel_check is not None and cancel_check():
                raise ParseCanceled("Analysis canceled by user.")
            for match in rule.evaluate(self.ctx):
                alert = Alert(
                    id=self._next_id,
                    rule_id=rule.rule_id,
                    name=rule.name,
                    tactic=rule.tactic,
                    technique=rule.technique,
                    severity=rule.severity,
                    description=rule.description,
                    summary=match.get("summary", ""),
                    events=match.get("events", []),
                )
                self._next_id += 1
                self.alerts.append(alert)
            if progress is not None:
                progress(i + 1, total)

        self.alerts.sort(key=_alert_start)
        self._dedupe()
        _tag_phases(self.events, self.alerts)
        self._build_chains()

        chrono = sorted(self.events, key=lambda e: e.timestamp)
        return AnalysisResult(
            events=self.events, alerts=self.alerts, chains=self.chains, chrono=chrono
        )

    def _dedupe(self) -> None:
        """Drop alerts that duplicate an earlier one (same rule + same first
        event record)."""
        seen = set()
        keep: List[Alert] = []
        for a in self.alerts:
            first = a.events[0].record_id if a.events else None
            key = (a.rule_id, first)
            if key in seen:
                continue
            seen.add(key)
            keep.append(a)
        self.alerts = keep

    def _build_chains(self) -> None:
        """Group alerts sharing a grouping key into incident chains when they
        are adjacent within CHAIN_ADJ (45 minutes)."""
        self.chains = []
        groups: List[List[Alert]] = []
        key_of: List[str] = []

        for a in sorted(self.alerts, key=_alert_start):
            key = _chain_key(a)
            placed = False
            for gi, group in enumerate(groups):
                if key_of[gi] != key:
                    continue
                last = group[-1]
                last_end = last.end if last.end else last.start
                if last_end is not None and a.start is not None:
                    if (a.start - last_end).total_seconds() <= 45 * 60:
                        group.append(a)
                        placed = True
                        break
            if not placed:
                groups.append([a])
                key_of.append(key)

        cid = 1
        for group, key in zip(groups, key_of):
            chain = IncidentChain(id=cid, key=key, alerts=group)
            for a in group:
                a.chain = chain
            self.chains.append(chain)
            cid += 1

        self.chains.sort(key=lambda c: c.score(), reverse=True)