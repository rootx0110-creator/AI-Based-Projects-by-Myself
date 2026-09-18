"""Misconfiguration detection suite.

Each detector is a pure function over the parsed rule-list (+ optional NAT
rules) returning :class:`Finding` entries. Deterministic order is guaranteed
by sorting before returning.

Pipeline (order matters for finding IDs):
   1. shadow     – earlier superset rule shadows a later same-action rule
   2. override   – earlier ALLOW covers a later DENY (security gap)
   3. duplicate  – exact duplicate of an earlier rule
   4. permissive – any/any allow, world→sensitive exposure
   5. ordering   – specific-before-general adjacency advisory
   6. cidr       – invalid / over-wide network notation
   7. mismatch   – port/protocol inconsistencies + NAT target gaps
   8. norelog    – allow rules without logging
   9. default-deny – missing final catch-all
  10. informational
"""

from __future__ import annotations

from typing import List, Optional

from .iprange import (
    covers, has_sensitive, is_any, overlaps, port_covers, ports_any,
)
from .rule import (
    Action, Direction, Finding, FirewallRule, NatRule, RuleType,
    SENSITIVE_PORTS, Severity, finding_id,
)

PROTO_PORTS = {  # protocol families that legitimately carry L4 ports
    "tcp": {"tcp"},
    "udp": {"udp"},
    "icmp": {"icmp", "icmp6"},
}
ICMP_PROTOS = {"icmp", "icmp6"}
TUNNEL_PROTOS = {"gre", "esp", "ah", "sctp", "ipip", "ipv6", "ip"}


def _proto_ok_port_carry(proto: str) -> bool:
    """protocol that *does not* carry ports: icmp/icmp6 and tunnels."""
    return proto not in ICMP_PROTOS and proto not in TUNNEL_PROTOS and proto != "any"


def _rule_key(r: FirewallRule) -> tuple:
    return (r.action.value, r.direction.value, r.protocol)


def scan(rules: List[FirewallRule],
         nat_rules: Optional[List[NatRule]] = None) -> List[Finding]:
    findings: List[Finding] = []
    nat_rules = nat_rules or []

    findings += _shadow_and_override(rules)
    findings += _duplicate(rules)
    findings += _permissive(rules)
    findings += _ordering(rules)
    findings += _cidr(rules)
    findings += _mismatch(rules, nat_rules)
    findings += _no_log(rules)
    findings += _default_deny(rules)
    findings += _informational(rules)

    findings.sort(key=lambda f: (f.severity.rank, f.category, f.rule_ids))
    for i, f in enumerate(findings, 1):
        f.id = finding_id(i)
    return findings


# --------------------------------------------------------------------------
# 1 + 2: shadowing & ordering override
# --------------------------------------------------------------------------

def _shadow_and_override(rules: List[FirewallRule]) -> List[Finding]:
    findings: List[Finding] = []
    active = list(rules)  # preserves order
    n = len(active)
    for i in range(n):
        ri = active[i]
        for j in range(i + 1, n):
            rj = active[j]
            if not _covers_rule(ri, rj):
                continue
            if ri.action.value == rj.action.value:
                if ri.rule_type == RuleType.DEFAULT_DENY:
                    continue
                findings.append(Finding(
                    id="",
                    category="shadowed",
                    severity=Severity.HIGH,
                    title=f"Rule {rj.rule_id} is shadowed by {ri.rule_id}",
                    detail=(f"'{ri.rule_id}' (line {ri.line_no}, {ri.raw}) "
                            f"matches at least the same traffic as '{rj.rule_id}' "
                            f"(line {rj.line_no}) with the same action {rj.action.value}. "
                            f"The later rule will never be reached."),
                    recommendation=(
                        f"Remove or reorder {rj.rule_id}; merge its intent into {ri.rule_id} "
                        f"if it is not redundant."),
                    rule_ids=[ri.rule_id, rj.rule_id],
                    line_nos=[ri.line_no, rj.line_no],
                    confidence=0.92,
                ))
            else:
                # opposite actions: ALLOW before covering DENY is a splice risk
                if ri.action.is_allow and rj.action.is_deny:
                    findings.append(Finding(
                        id="",
                        category="override",
                        severity=Severity.CRITICAL,
                        title=f"ALLOW {ri.rule_id} overrides DENY {rj.rule_id}",
                        detail=(f"'{ri.rule_id}' (ALLOW, line {ri.line_no}) covers the "
                                f"traffic the later DENY '{rj.rule_id}' (line {rj.line_no}) "
                                f"intends to block; the DENY is ineffective."),
                        recommendation=(
                            "Reorder so the DENY precedes the ALLOW, or scope the ALLOW "
                            "to exclude what must remain blocked."),
                        rule_ids=[ri.rule_id, rj.rule_id],
                        line_nos=[ri.line_no, rj.line_no],
                        confidence=0.85,
                    ))
    return findings


def _covers_rule(a: FirewallRule, b: FirewallRule) -> bool:
    """True if rule a (earlier) matches a superset of the packets of b.

    Superset semantics:
      protocol: a must equal b or be 'any' (a 'tcp' does NOT cover b 'any').
      direction: a must equal b or be INOUT (an 'in' rule does NOT cover 'any').
      ports:    a-ANY covers anything; a restricted does not cover b-ANY.
      networks: a must cover every range of b.
    """
    if a.enabled and not b.enabled:
        return False
    if not a.enabled:
        return False
    # protocol
    if a.protocol != b.protocol and a.protocol != "any":
        return False
    # direction
    if a.direction != b.direction and a.direction != Direction.INOUT:
        return False
    # ports: only relevant when protocols carry ports
    if not port_check(a.src_port_intervals, b.src_port_intervals):
        return False
    if not port_check(a.dst_port_intervals, b.dst_port_intervals):
        return False
    # networks
    if not covers(a.src_nets or [], b.src_nets or []):
        return False
    if not covers(a.dst_nets or [], b.dst_nets or []):
        return False
    return True


def port_check(a_iv, b_iv) -> bool:
    if not a_iv and b_iv:
        return True  # a has ANY ports
    if a_iv and not b_iv:
        return False  # a restricted, b any → a doesn't cover b
    return port_covers(a_iv, b_iv)


# --------------------------------------------------------------------------
# 3: duplicates
# --------------------------------------------------------------------------

def _duplicate(rules: List[FirewallRule]) -> List[Finding]:
    findings: List[Finding] = []
    n = len(rules)
    seen: dict = {}
    for i in range(n):
        r = rules[i]
        key = (r.action.value, r.direction.value, r.protocol, r.src_ip,
               r.src_port, r.dst_ip, r.dst_port)
        exists = seen.setdefault(key, [])
        if exists:
            prev = exists[0]
            findings.append(Finding(
                id="",
                category="duplicate",
                severity=Severity.MEDIUM,
                title=f"Duplicate rule {r.rule_id} equals {prev.rule_id}",
                detail=(f"'{r.rule_id}' (line {r.line_no}) is identical to earlier "
                        f"'{prev.rule_id}' (line {prev.line_no}). Dead weight that "
                        f"drifts out of sync when edited."),
                recommendation="Delete the later copy; keep the earliest as canonical.",
                rule_ids=[prev.rule_id, r.rule_id],
                line_nos=[prev.line_no, r.line_no],
                confidence=0.98,
            ))
        exists.append(r)
    return findings


# --------------------------------------------------------------------------
# 4: permissive
# --------------------------------------------------------------------------

def _permissive(rules: List[FirewallRule]) -> List[Finding]:
    findings: List[Finding] = []
    for r in rules:
        if not r.enabled or r.action.is_deny or r.rule_type == RuleType.DEFAULT_DENY:
            continue
        src_any = bool(r.src_nets) and is_any(r.src_nets)
        dst_any = bool(r.dst_nets) and is_any(r.dst_nets)
        if src_any and dst_any:
            findings.append(Finding(
                id="",
                category="permissive",
                severity=Severity.CRITICAL,
                title=f"{r.rule_id}: any->any ALLOW (world-open)",
                detail=(f"{r.rule_id} permits {r.protocol} from ANY source to ANY "
                        f"destination{f' on {r.dst_port}' if r.dst_port != 'ANY' else ''}."),
                recommendation="Replace with the narrowest required src/dst/port tuple.",
                rule_ids=[r.rule_id], line_nos=[r.line_no], confidence=0.99,
            ))
            continue
        if src_any or dst_any:
            # world→internal sensitive exposure
            if r.direction in (Direction.IN, Direction.INOUT):
                if r.dst_nets and not is_any(r.dst_nets) and dst_any:
                    pass
                if r.dst_port_intervals and has_sensitive(r.dst_port_intervals,
                                                          SENSITIVE_PORTS):
                    findings.append(Finding(
                        id="",
                        category="permissive",
                        severity=Severity.HIGH,
                        title=f"{r.rule_id}: exposed service on sensitive port "
                              f"{r.dst_port}",
                        detail=(f"Inbound ALLOW toward {r.dst_ip}:{r.dst_port} from "
                                f"{'ANY' if src_any else r.src_ip}."),
                        recommendation="Restrict the source and consider a VPN/bastion.",
                        rule_ids=[r.rule_id], line_nos=[r.line_no], confidence=0.9,
                    ))
    return findings


# --------------------------------------------------------------------------
# 5: ordering advisory
# --------------------------------------------------------------------------

def _ordering(rules: List[FirewallRule]) -> List[Finding]:
    """Advisory (INFO): a general same-action permit precedes specific permits.

    The shadow detector raises HIGH for such cases when full coverage holds;
    here we only raise a lighter advisory for adjacency where the earlier rule
    is a broad permit and a later specific permit of the same action follows.
    """
    findings: List[Finding] = []
    n = len(rules)
    for i in range(n):
        ri = rules[i]
        if not (ri.action.is_allow and ri.enabled):
            continue
        if ri.src_ip != "ANY" or ri.dst_ip != "ANY":
            continue
        for j in range(i + 1, min(i + 5, n)):
            rj = rules[j]
            if rj.action.is_allow and rj.enabled \
                    and (rj.src_ip != "ANY" or rj.dst_ip != "ANY") \
                    and ri.protocol == rj.protocol \
                    and _covers_rule(ri, rj):
                findings.append(Finding(
                    id="",
                    category="ordering",
                    severity=Severity.INFO,
                    title=f"Broad permit {ri.rule_id} precedes specific {rj.rule_id}",
                    detail=(f"{ri.rule_id} ({ri.raw[:60]}) already matches {rj.rule_id}'s "
                            f"traffic; the later-specific ordering is confusing to "
                            f"maintain and can mask intent."),
                    recommendation="Reorder specific permits before broad ones.",
                    rule_ids=[ri.rule_id, rj.rule_id],
                    line_nos=[ri.line_no, rj.line_no], confidence=0.75,
                ))
                break
    return findings


# --------------------------------------------------------------------------
# 6: cidr / notation
# --------------------------------------------------------------------------

def _cidr(rules: List[FirewallRule]) -> List[Finding]:
    findings: List[Finding] = []
    for r in rules:
        for label, token in (("source", r.src_ip), ("destination", r.dst_ip)):
            if token == "ANY":
                continue
            if "/" in token:
                host, prefix = token.rsplit("/", 1)
                try:
                    plen = int(prefix)
                except ValueError:
                    _cidr_finding(findings, r, label, token, "non-numeric prefix")
                    continue
                max_plen = 128 if ":" in host else 32
                if plen < 0 or plen > max_plen:
                    _cidr_finding(findings, r, label, token,
                                  f"prefix /{plen} outside 0..{max_plen}")
    return findings


def _cidr_finding(findings: List[Finding], r: FirewallRule, label: str,
                  token: str, why: str) -> None:
    findings.append(Finding(
        id="",
        category="cidr",
        severity=Severity.MEDIUM,
        title=f"{r.rule_id}: invalid {label} network '{token}'",
        detail=f"({why}). Rule may not match the intended traffic.",
        recommendation=f"Fix the {label} to valid CIDR (e.g. '10.0.0.0/24') or a host.",
        rule_ids=[r.rule_id], line_nos=[r.line_no], confidence=0.95,
    ))


# --------------------------------------------------------------------------
# 7: port/protocol & NAT mismatches
# --------------------------------------------------------------------------

def _mismatch(rules: List[FirewallRule],
              nat_rules: List[NatRule]) -> List[Finding]:
    findings: List[Finding] = []
    for r in rules:
        if r.protocol in ICMP_PROTOS and (r.dst_port != "ANY" or r.src_port != "ANY"):
            findings.append(Finding(
                id="",
                category="mismatch",
                severity=Severity.LOW,
                title=f"{r.rule_id}: ports on an ICMP rule",
                detail="ICMP carries no TCP/UDP ports; the port spec is meaningless.",
                recommendation="Remove the port clauses or use a TCP/UDP rule.",
                rule_ids=[r.rule_id], line_nos=[r.line_no], confidence=0.9,
            ))
            continue
        if r.protocol != "any" and not _proto_ok_port_carry(r.protocol):
            if r.dst_port != "ANY" or r.src_port != "ANY":
                findings.append(Finding(
                    id="",
                    category="mismatch",
                    severity=Severity.LOW,
                    title=f"{r.rule_id}: ports on tunnel/protocol rule",
                    detail=f"Protocol '{r.protocol}' does not carry L4 ports.",
                    recommendation="Use TCP/UDP rules for port scoping.",
                    rule_ids=[r.rule_id], line_nos=[r.line_no], confidence=0.85,
                ))
    _nat_checks(findings, rules, nat_rules)
    return findings


def _nat_checks(findings: List[Finding], rules: List[FirewallRule],
                nat_rules: List[NatRule]) -> None:
    if not nat_rules:
        return
    for nat in nat_rules:
        if nat.outside_port not in ("ANY", ""):
            target_found = False
            for r in rules:
                if r.action.is_deny:
                    continue
                if not r.dst_port_intervals or ports_any(r.dst_port_intervals):
                    continue
                if overlaps(r.dst_nets or [], parse_net(nat.outside)):
                    pass
                if nat.proto in ("any", r.protocol) or r.protocol == "any":
                    if _port_contains(r.dst_port_intervals, nat.outside_port):
                        # also need dst family match
                        target_found = True
                        break
            if not target_found:
                findings.append(Finding(
                    id="",
                    category="nat",
                    severity=Severity.MEDIUM,
                    title=f"NAT {nat.nat_id}: no matching permit for {nat.outside_port}",
                    detail=(f"NAT maps {nat.outside}:{nat.outside_port} -> {nat.translated} "
                            f"but no ALLOW rule opens that service."),
                    recommendation=(
                        "Add an access-list permit or align the NAT service port."),
                    rule_ids=[nat.nat_id], line_nos=[nat.line_no], confidence=0.7,
                ))


def parse_net(tok: str):
    from .iprange import parse_addr_token
    return parse_addr_token(tok)


def _port_contains(intervals, port_spec) -> bool:
    from .iprange import parse_ports, port_covers
    p = parse_ports(port_spec)
    if not p:
        return True
    return port_covers(intervals, p) if intervals else True


# --------------------------------------------------------------------------
# 8: logging discipline
# --------------------------------------------------------------------------

def _no_log(rules: List[FirewallRule]) -> List[Finding]:
    findings: List[Finding] = []
    allow_count = sum(1 for r in rules if r.action.is_allow and r.enabled)
    if allow_count == 0:
        return findings
    for r in rules:
        if r.action.is_allow and r.enabled and r.rule_type != RuleType.DEFAULT_DENY \
                and not r.log:
            findings.append(Finding(
                id="",
                category="norelog",
                severity=Severity.LOW,
                title=f"{r.rule_id}: ALLOW rule does not log traffic",
                detail=("Permits containing {raw} have no logging; forensic value "
                        "of the firewall is diminished.").format(raw=r.raw[:80] or r.rule_id),
                recommendation="Enable logging on this ALLOW rule.",
                rule_ids=[r.rule_id], line_nos=[r.line_no], confidence=0.8,
            ))
    return findings


# --------------------------------------------------------------------------
# 9: default deny
# --------------------------------------------------------------------------

def _default_deny(rules: List[FirewallRule]) -> List[Finding]:
    findings: List[Finding] = []
    has_dd = any(r.rule_type == RuleType.DEFAULT_DENY for r in rules)
    main = [r for r in rules if r.rule_type != RuleType.DEFAULT_DENY]
    if not has_dd and main:
        last = main[-1]
        if not last.action.is_deny:
            findings.append(Finding(
                id="",
                category="default-deny",
                severity=Severity.HIGH,
                title="No default-deny (catch-all) rule at the end",
                detail=(f"The last rule is {last.rule_id} {last.action.value} "
                        f"({last.raw or last.description}). Traffic matching nothing "
                        f"falls through permissively."),
                recommendation="Add a final DENY/REJECT any->any rule, or set the "
                              "implicit policy to DROP.",
                rule_ids=[last.rule_id], line_nos=[last.line_no], confidence=0.8,
            ))
    return findings


# --------------------------------------------------------------------------
# 10: informational
# --------------------------------------------------------------------------

def _informational(rules: List[FirewallRule]) -> List[Finding]:
    findings: List[Finding] = []
    total = len([r for r in rules if r.rule_type != RuleType.DEFAULT_DENY])
    if total == 0:
        return findings
    disabled = [r for r in rules if not r.enabled]
    if disabled:
        findings.append(Finding(
            id="",
            category="informational",
            severity=Severity.INFO,
            title=f"{len(disabled)} disabled rule(s) present",
            detail=("Rules that are disabled still shadow in some dashboards; audit "
                    "regularly."),
            recommendation="Enable, edit or remove disabled rules.",
            rule_ids=[r.rule_id for r in disabled[:10]],
            line_nos=[r.line_no for r in disabled], confidence=0.7,
        ))
    return findings