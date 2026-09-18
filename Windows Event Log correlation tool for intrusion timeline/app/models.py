"""Core data models for the event log correlation tool.

Contains EventRecord (one parsed Windows event), Alert (one detection),
Rule metadata, plus the Severity and Phase enums used across modules.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class Severity(enum.IntEnum):
    """Detection severity levels (ordinal = weight for scoring)."""

    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_name(cls, name: str) -> "Severity":
        try:
            return cls[str(name.strip().upper())]
        except KeyError:
            return cls.INFO

    @property
    def label(self) -> str:
        return self.name.title()

    @property
    def color(self) -> str:
        return {
            self.INFO: "#64748b",
            self.LOW: "#22c55e",
            self.MEDIUM: "#f59e0b",
            self.HIGH: "#f97316",
            self.CRITICAL: "#ef4444",
        }.get(self, "#64748b")


class Phase(enum.Enum):
    """Kill-chain phase assigned to events."""

    RECON = "Reconnaissance"
    INITIAL_ACCESS = "Initial Access"
    EXECUTION = "Execution"
    PERSISTENCE = "Persistence"
    PRIV_ESCALATION = "Privilege Escalation"
    CREDENTIAL_ACCESS = "Credential Access"
    DEFENSE_EVASION = "Defense Evasion"
    LATERAL_MOVEMENT = "Lateral Movement"
    EXFILTRATION = "Exfiltration"
    IMPACT = "Impact"
    UNKNOWN = "Unknown"

    @property
    def color(self) -> str:
        return {
            self.RECON: "#38bdf8",
            self.INITIAL_ACCESS: "#818cf8",
            self.EXECUTION: "#a78bfa",
            self.PERSISTENCE: "#fbbf24",
            self.PRIV_ESCALATION: "#fb923c",
            self.CREDENTIAL_ACCESS: "#f472b6",
            self.DEFENSE_EVASION: "#f87171",
            self.LATERAL_MOVEMENT: "#4ade80",
            self.EXFILTRATION: "#2dd4bf",
            self.IMPACT: "#ef4444",
            self.UNKNOWN: "#64748b",
        }.get(self, "#64748b")


@dataclass
class EventRecord:
    """A single parsed Windows Event Log record."""

    record_id: int
    event_id: int
    timestamp: datetime          # UTC
    channel: str
    computer: str
    provider: str
    level: int
    data: Dict[str, str] = field(default_factory=dict)
    raw: str = ""
    phase: Phase = Phase.UNKNOWN
    alert_ids: List[int] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    def get(self, *names: str) -> str:
        """Return first non-empty data value among the given field names."""
        for n in names:
            v = self.data.get(n)
            if v:
                return v
        return ""

    @property
    def subject_user(self) -> str:
        return self.get("SubjectUserName", "SubjectUserNameSid", "TargetUserName")

    @property
    def target_user(self) -> str:
        return self.get("TargetUserName", "SubjectUserName")

    @property
    def source_ip(self) -> str:
        return self.get("SourceNetworkAddress", "IpAddress", "ClientAddress", "RemoteHost")

    @property
    def target_host(self) -> str:
        return self.get("TargetServerName", "TargetComputer", "WorkstationName", "Computer")

    @property
    def process(self) -> str:
        return self.get("NewProcessName", "ProcessName", "Image", "CallerProcessName")

    @property
    def command_line(self) -> str:
        return self.get("CommandLine", "NewProcessCommandLine", "Command")

    @property
    def logon_type(self) -> str:
        return self.get("LogonType")

    @property
    def object_name(self) -> str:
        return self.get("ObjectName", "ObjectType")

    @property
    def is_remote(self) -> bool:
        t = self.logon_type
        return t in ("3", "8", "9", "10") or bool(self.source_ip)

    def time_local(self) -> datetime:
        return self.timestamp.astimezone()

    def summary(self) -> str:
        """One-line human readable summary used in tables/report."""
        parts = [f"EventID {self.event_id}", f"{self.channel}"]
        if self.subject_user:
            parts.append(f"user={self.subject_user}")
        if self.source_ip:
            parts.append(f"ip={self.source_ip}")
        if self.process:
            parts.append(f"proc={self.process}")
        if self.object_name:
            obj = self.object_name
            parts.append(f"obj={obj[:80]}")
        if self.command_line:
            cmd = self.command_line.strip()
            if len(cmd) > 90:
                cmd = cmd[:87] + "..."
            parts.append(f"cmd={cmd}")
        return " | ".join(parts)


@dataclass
class Alert:
    """A single detection produced by a Rule."""

    id: int
    rule_id: str
    name: str
    tactic: str
    technique: str
    severity: Severity
    description: str
    summary: str                          # human readable key finding text
    events: List[EventRecord] = field(default_factory=list)
    chain: Optional["IncidentChain"] = None

    @property
    def start(self) -> Optional[datetime]:
        if not self.events:
            return None
        return min(e.timestamp for e in self.events)

    @property
    def end(self) -> Optional[datetime]:
        if not self.events:
            return None
        return max(e.timestamp for e in self.events)

    @property
    def span_seconds(self) -> float:
        if not self.events:
            return 0.0
        return (self.end - self.start).total_seconds()


@dataclass
class IncidentChain:
    """A multi-stage intrusion built from related alerts."""

    id: int
    key: str                               # grouping value (user / ip / host)
    alerts: List[Alert] = field(default_factory=list)

    def stages_sorted(self) -> List[Alert]:
        return sorted(
            (a for a in self.alerts if a.start),
            key=lambda a: (a.start, a.severity),
        )

    def score(self) -> int:
        return sum(a.severity.value for a in self.alerts)

    @property
    def start(self) -> Optional[datetime]:
        stages = self.stages_sorted()
        return stages[0].start if stages else None

    @property
    def end(self) -> Optional[datetime]:
        stages = self.stages_sorted()
        return stages[-1].end if stages else None

    @property
    def tactic_path(self) -> str:
        seen = []
        for a in self.stages_sorted():
            if a.tactic not in seen:
                seen.append(a.tactic)
        return " -> ".join(seen)


@dataclass
class Rule:
    """Detection rule: metadata + an evaluator callable.

    Evaluator signature:  evaluate(ctx: RuleContext) -> List[dict]
    where each returned dict has keys: 'events', 'summary' (optional).
    """

    rule_id: str
    name: str
    tactic: str
    technique: str
    severity: Severity
    description: str
    evaluate: Any

    @classmethod
    def make(
        cls,
        rule_id: str,
        name: str,
        tactic: str,
        technique: str,
        severity: Severity,
        description: str,
        evaluate: Any,
    ) -> "Rule":
        return cls(rule_id, name, tactic, technique, severity, description, evaluate)


@dataclass
class AnalysisResult:
    """Everything the correlation engine produced for one run."""

    events: List[EventRecord]
    alerts: List[Alert]
    chains: List[IncidentChain]
    chrono: List[EventRecord] = field(default_factory=list)

    def by_severity(self, sev: Severity) -> int:
        return sum(1 for a in self.alerts if a.severity == sev)