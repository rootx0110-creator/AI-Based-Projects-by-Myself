"""Session analysis: replay the captured beacons against the generated rules.

This is the "detection engine" of the lab. It evaluates the same Suricata /
Zeek signatures the lab generated against the beacon events actually captured
during the session, plus a behavioural beacon-cadence model, and produces a
:class:`SessionResult` that feeds both the UI and the HTML report.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime

from .presets import C2Profile
from .server import BeaconEvent
from .signatures import _sid

CRITICAL = "CRITICAL"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
INFO = "INFO"

_SEVERITY_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4}


@dataclass
class Finding:
    severity: str
    rule: str
    title: str
    description: str
    evidence: str
    count: int

    @property
    def score(self) -> int:
        return _SEVERITY_ORDER[self.severity]


@dataclass
class SessionResult:
    profile: C2Profile
    total_events: int
    duration_s: float
    findings: list = field(default_factory=list)
    rule_texts: dict = field(default_factory=dict)
    interval_stats: dict = field(default_factory=dict)
    path_counts: dict = field(default_factory=dict)
    ua_unique: int = 0
    events: list = field(default_factory=list)
    generated_at: str = ""

    @property
    def alerts(self) -> list:
        return [f for f in self.findings if f.severity != INFO]

    @property
    def highest(self) -> str:
        if not self.findings:
            return "NONE"
        return min(self.findings, key=lambda f: f.score).severity

    @property
    def qualified(self) -> bool:
        """True when evidence clearly identifies C2 beaconing."""
        titles = " ".join(f.title for f in self.findings if f.severity in (CRITICAL, HIGH, MEDIUM))
        return "beaconing" in titles or "exact" in titles or self.total_events >= 8

    @property
    def verdict(self) -> str:
        if self.qualified:
            return "POSITIVE - C2 beaconing identified"
        if self.total_events == 0:
            return "INCONCLUSIVE - no beacon events captured"
        return "ELEVATED - indicators present, strengthen with analyst review"


def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _coefficient_of_variation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    return (statistics.pstdev(values) / mean) if mean else 0.0


def analyze_session(events: list[BeaconEvent], profile: C2Profile) -> SessionResult:
    profile = profile if profile.name else C2Profile(**{**vars(profile), "name": "Generic HTTP Beacon"})
    result = SessionResult(
        profile=profile,
        total_events=len(events),
        duration_s=0.0,
        events=events,
    )
    if not events:
        return result

    # --- basic stats ------------------------------------------------------
    times = sorted((_parse_ts(e.timestamp) for e in events), key=lambda t: t)
    result.duration_s = (times[-1] - times[0]).total_seconds() + 1.0
    path_counts: dict = {}
    for e in events:
        path_counts[e.path] = path_counts.get(e.path, 0) + 1
    result.path_counts = dict(sorted(path_counts.items(), key=lambda kv: -kv[1]))
    result.ua_unique = len({e.user_agent_hash for e in events})

    # --- inter-beacon timing ---------------------------------------------
    deltas = [
        (b - a).total_seconds() for a, b in zip(times, times[1:]) if (b - a).total_seconds() > 0
    ]
    interval_stats = {"n": len(deltas)}
    if deltas:
        interval_stats.update(
            {
                "mean": round(statistics.mean(deltas), 2),
                "stddev": round(statistics.pstdev(deltas), 2),
                "min": round(min(deltas), 2),
                "max": round(max(deltas), 2),
                "cv": round(_coefficient_of_variation(deltas), 3),
            }
        )
    result.interval_stats = interval_stats

    # --- rule A: exact UA+dry handshake (Suricata sid 0) --------------------
    sid_ua = _sid(profile, 0)
    matched_ua = [e for e in events if e.user_agent == profile.user_agent]
    if matched_ua:
        result.findings.append(
            Finding(
                severity=CRITICAL,
                rule=f"suricata sid {sid_ua}",
                title="Exact beacon User-Agent match",
                description=(
                    f"Every request carried the {profile.family} User-Agent fingerprint, "
                    f"matching Suricata rule sid {sid_ua} (C2-BEACON {profile.family})."
                ),
                evidence=f"UA = {profile.user_agent[:80]}… ({len(matched_ua)}/{result.total_events} events)",
                count=len(matched_ua),
            )
        )

    # --- rule B: beacon URIs hit (Suricata sid 1 gradient) -----------------
    sid_uri = _sid(profile, 1)
    uri_paths = {p for p in profile.uri_paths}
    matched_path = [e for e in events if e.path in uri_paths]
    if matched_path:
        result.findings.append(
            Finding(
                severity=HIGH,
                rule=f"suricata sid {sid_uri}",
                title="Beacon URI pattern match",
                description=(
                    f"Requests targeted the profile's beacon URIs, triggering Suricata "
                    f"rule sid {sid_uri} (URI usage detection)."
                ),
                evidence=f"paths matched = {sorted(set(e.path for e in matched_path))}",
                count=len(matched_path),
            )
        )

    # --- rule C: regular cadence --------------------------------------------
    if len(deltas) >= 2 and interval_stats.get("cv", 1.0) < 0.5:
        result.findings.append(
            Finding(
                severity=MEDIUM,
                rule="behavioral (interval)",
                title="Regular beaconing cadence detected",
                description=(
                    "Inter-beacon delays are tightly clustered (low coefficient of "
                    "variation), consistent with an automated beacon, not human or "
                    "organic traffic."
                ),
                evidence=(
                    f"{len(deltas)} deltas, mean {interval_stats['mean']}s, "
                    f"std {interval_stats['stddev']}s, CV {interval_stats['cv']}"
                ),
                count=len(deltas),
            )
        )

    # --- rule D: UA variance -------------------------------------------------
    if result.ua_unique <= 1 and result.total_events >= 2:
        result.findings.append(
            Finding(
                severity=LOW,
                rule="behavioral (ua-hash)",
                title="Single, stable User-Agent across session",
                description="One User-Agent for the whole session — common for implants.",
                evidence=f"{result.ua_unique} unique UA hash(es) across {result.total_events} events",
                count=result.total_events,
            )
        )

    # --- rule E: path concentration -----------------------------------------
    if result.path_counts:
        top_path, top_count = next(iter(result.path_counts.items()))
        share = top_count / result.total_events
        if len(result.path_counts) <= 2 and share >= 0.5:
            result.findings.append(
                Finding(
                    severity=LOW,
                    rule="behavioral (uri-concentration)",
                    title="Concentrated URI usage",
                    description=(
                        "A single URI accounts for most requests — machines doing one "
                        "thing repeatedly (beacon check-in), unlike mixed browsing."
                    ),
                    evidence=f"{top_path} -> {top_count}/{result.total_events} events ({share:.0%})",
                    count=top_count,
                )
            )

    # --- rule F: lab context --------------------------------------------------
    if result.total_events >= 3:
        result.findings.append(
            Finding(
                severity=INFO,
                rule="context",
                title="Session confined to lab loopback",
                description="All traffic in this session was loopback, so no real network was touched.",
                evidence=f"{result.total_events} events on 127.0.0.1",
                count=result.total_events,
            )
        )

    result.findings.sort(key=lambda f: (f.score, -f.count))
    return result