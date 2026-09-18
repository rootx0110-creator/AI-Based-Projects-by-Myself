"""Canonical domain models for firewall rules, findings and reports."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional


class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def rank(self) -> int:
        return {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }[self]


SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 18.0,
    Severity.HIGH: 10.0,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 2.0,
    Severity.INFO: 0.5,
}


class Action(str, enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DROP = "DROP"
    REJECT = "REJECT"

    @property
    def is_deny(self) -> bool:
        return self in (Action.DENY, Action.DROP, Action.REJECT)

    @property
    def is_allow(self) -> bool:
        return self == Action.ALLOW


class Direction(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    INOUT = "INOUT"


class RuleType(str, enum.Enum):
    NORMAL = "NORMAL"
    NAT = "NAT"
    DEFAULT_DENY = "DEFAULT_DENY"


SENSITIVE_PORTS = {
    22, 23, 21, 3389, 1433, 1434, 3306, 5432, 27017, 6379, 11211, 5900,
    9200, 9300, 5985, 5986, 445, 139, 135, 993, 995, 25, 110, 143,
}


@dataclass
class FirewallRule:
    """A single normalized filter rule.

    Fields marked "canonical" are guaranteed normalized by normalized_rule().
    """

    rule_id: str
    line_no: int
    position: int
    action: Action
    direction: Direction = Direction.INOUT
    protocol: str = "any"
    src_ip: str = "ANY"
    src_port: str = "ANY"
    dst_ip: str = "ANY"
    dst_port: str = "ANY"
    interface: Optional[str] = None
    log: bool = False
    enabled: bool = True
    description: str = ""
    raw: str = ""
    chain: Optional[str] = None
    rule_type: RuleType = RuleType.NORMAL

    # Canonical / derived fields (filled by normalizer)
    src_nets: Optional[list] = None      # list of (start_int, end_int, is_v6)
    dst_nets: Optional[list] = None
    src_port_intervals: Optional[list] = None
    dst_port_intervals: Optional[list] = None
    protocol_any: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.rule_id,
            "line": self.line_no,
            "position": self.position,
            "action": self.action.value,
            "direction": self.direction.value,
            "protocol": self.protocol,
            "src_ip": self.src_ip,
            "src_port": self.src_port,
            "dst_ip": self.dst_ip,
            "dst_port": self.dst_port,
            "interface": self.interface,
            "log": self.log,
            "enabled": self.enabled,
            "description": self.description,
            "chain": self.chain,
            "rule_type": self.rule_type.value,
            "raw": self.raw,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"<Rule {self.rule_id} {self.action.value} "
                f"{self.protocol} {self.src_ip}:{self.src_port} -> "
                f"{self.dst_ip}:{self.dst_port}")


@dataclass
class NatRule:
    """Representation of a NAT/PAT mapping (tolerates variance by keeping raw)."""

    nat_id: str
    line_no: int
    position: int
    proto: str = "any"
    inside: str = "ANY"          # original (pre-NAT) source, e.g. lan ip
    inside_port: str = "ANY"
    outside: str = "ANY"         # external destination attractor
    outside_port: str = "ANY"    # the public port
    translated: str = ""         # real target ip/port (internal)
    raw: str = ""
    nat_type: str = "destination"  # destination | source | static

    def to_dict(self) -> dict:
        return {
            "id": self.nat_id,
            "line": self.line_no,
            "type": self.nat_type,
            "proto": self.proto,
            "inside": self.inside,
            "inside_port": self.inside_port,
            "outside": self.outside,
            "outside_port": self.outside_port,
            "translated": self.translated,
            "raw": self.raw,
        }


@dataclass
class Finding:
    id: str
    category: str
    severity: Severity
    title: str
    detail: str
    recommendation: str
    rule_ids: List[str] = field(default_factory=list)
    line_nos: List[int] = field(default_factory=list)
    confidence: float = 0.9

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity.value,
            "severity_rank": self.severity.rank,
            "title": self.title,
            "detail": self.detail,
            "recommendation": self.recommendation,
            "rule_ids": self.rule_ids,
            "line_nos": self.line_nos,
            "confidence": self.confidence,
        }


def finding_id(seq: int) -> str:
    return f"F{seq:03d}"


def rule_id_at(position: int) -> str:
    return f"R{position + 1:03d}"