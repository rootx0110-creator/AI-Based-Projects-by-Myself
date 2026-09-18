"""Dataclasses describing rules, results, and compliance reports."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class Severity(str, enum.Enum):
    """Severity of a rule, aligned with CIS style levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def label(self) -> str:
        return self.value.capitalize()

    @property
    def weight(self) -> int:
        return SEVERITY_WEIGHTS[self]


SEVERITY_WEIGHTS: dict[Severity, int] = {
    Severity.CRITICAL: 10,
    Severity.HIGH: 6,
    Severity.MEDIUM: 3,
    Severity.LOW: 1,
    Severity.INFO: 0,
}


class ResultStatus(str, enum.Enum):
    """Outcome of evaluating a single rule."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"
    SKIPPED = "skipped"
    MANUAL = "manual"


class Profile(str, enum.Enum):
    """CIS benchmark profiles (Level 1 / Level 2)."""

    L1 = "level_1"
    L2 = "level_2"


@dataclass
class ExpectedValue:
    """A normalized expectation for registry / file / command comparisons."""

    kind: str  # "exact" | "regex" | "min" | "max" | "one_of" | "not_contains"
    value: Any = None
    options: list[Any] = field(default_factory=list)
    flags: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "options": self.options}


@dataclass
class Evidence:
    """Raw data captured while evaluating a rule (for the report appendix)."""

    source: str = ""
    detail: str = ""
    raw: str = ""
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "detail": self.detail,
            "raw": self.raw[:2000],
            "truncated": self.truncated or len(self.raw) > 2000,
        }


@dataclass
class Remediation:
    """Human readable guidance for fixing a failed rule."""

    summary: str = ""
    steps: list[str] = field(default_factory=list)
    script: str = ""
    script_shell: str = ""  # "powershell" | "bash" | "cmd" | ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "steps": self.steps,
            "script": self.script,
            "script_shell": self.script_shell,
        }


@dataclass
class Rule:
    """A single benchmark rule (a CIS recommendation equivalent)."""

    rule_id: str
    title: str
    description: str
    severity: Severity
    profile: Profile
    category: str
    check_spec: dict[str, Any]
    remediation: Remediation = field(default_factory=Remediation)
    rationale: str = ""
    refs: list[str] = field(default_factory=list)
    requires_admin: bool = False
    manual: bool = False
    platforms: tuple[str, ...] = ("windows",)
    tags: list[str] = field(default_factory=list)
    audit_hint: str = ""  # UI hint shown in the "Why" popover.

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity.value,
            "profile": self.profile.value,
            "category": self.category,
            "manual": self.manual,
            "requires_admin": self.requires_admin,
        }


@dataclass
class CheckResult:
    """Outcome of evaluating one rule on one endpoint."""

    rule: Rule
    status: ResultStatus = ResultStatus.SKIPPED
    message: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    observed: Any = None
    expected: Any = None
    duration_ms: float = 0.0
    timestamp: str = ""

    @property
    def rule_id(self) -> str:
        return self.rule.rule_id

    @property
    def severity(self) -> Severity:
        return self.rule.severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule.rule_id,
            "title": self.rule.title,
            "status": self.status.value,
            "severity": self.rule.severity.value,
            "profile": self.rule.profile.value,
            "category": self.rule.category,
            "message": self.message,
            "observed": _safe(self.observed),
            "expected": _safe(self.expected),
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class PlatformInfo:
    """Identity of the machine being audited."""

    system: str = ""            # "Windows" | "Linux" | "Darwin"
    os_name: str = ""           # friendly name
    os_version: str = ""
    build: str = ""
    arch: str = ""
    hostname: str = ""
    ip_addresses: list[str] = field(default_factory=list)
    is_admin: bool = False
    domain_joined: bool = False
    boot_time: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "build": self.build,
            "arch": self.arch,
            "hostname": self.hostname,
            "ip_addresses": self.ip_addresses,
            "is_admin": self.is_admin,
            "domain_joined": self.domain_joined,
            "boot_time": self.boot_time,
            "extra": self.extra,
        }


@dataclass
class ScanSummary:
    """Aggregated statistics for a scan."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    not_applicable: int = 0
    skipped: int = 0
    manual: int = 0

    def recompute(self, results: list["CheckResult"]) -> None:
        self.total = len(results)
        self.passed = sum(1 for r in results if r.status is ResultStatus.PASS)
        self.failed = sum(1 for r in results if r.status is ResultStatus.FAIL)
        self.errors = sum(1 for r in results if r.status is ResultStatus.ERROR)
        self.not_applicable = sum(
            1 for r in results if r.status is ResultStatus.NOT_APPLICABLE
        )
        self.skipped = sum(1 for r in results if r.status is ResultStatus.SKIPPED)
        self.manual = sum(1 for r in results if r.status is ResultStatus.MANUAL)


@dataclass
class ScanReport:
    """Top level container for one completed scan."""

    scan_id: str
    started_at: str
    finished_at: str
    profile: str
    platform: PlatformInfo
    results: list[CheckResult]
    summary: ScanSummary
    score: float = 0.0
    grade: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "profile": self.profile,
            "platform": self.platform.to_dict(),
            "summary": vars(self.summary).copy(),
            "score": round(self.score, 1),
            "grade": self.grade,
            "results": [r.to_dict() for r in self.results],
        }


def _safe(value: Any) -> Any:
    """Make values JSON/JSONL friendly (truncate long blobs, drop secrets)."""
    text = str(value)
    if len(text) > 2000:
        return text[:2000] + "…[truncated]"
    return value
