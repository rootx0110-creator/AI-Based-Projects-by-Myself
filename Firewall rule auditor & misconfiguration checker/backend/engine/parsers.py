"""Vendor firewall configuration parsers.

Every parser returns a :class:`ParseResult` (rules, nat_rules, warnings).
Parsers never raise; malformed lines degrade to warnings.

Supported formats (id -> display name):
    iptables, cisco-asa, fortigate, pfsense, windows, paloalto, plain
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .iprange import parse_addr_token, parse_ports, is_any
from .rule import (
    Action, Direction, FirewallRule, NatRule, RuleType, rule_id_at,
)

ANY = "ANY"


@dataclass
class ParseResult:
    rules: List[FirewallRule] = field(default_factory=list)
    nat_rules: List[NatRule] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


FORMATS = {
    "iptables": "iptables / iptables-save",
    "cisco-asa": "Cisco ASA (access-list)",
    "fortigate": "FortiGate (config firewall)",
    "pfsense": "pfSense config.xml",
    "windows": "Windows advfirewall / netsh",
    "paloalto": "Palo Alto (set security policy)",
    "plain": "Plain tabular rules",
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _norm_proto(tok: str) -> str:
    t = (tok or "").strip().lower()
    if not t or t in ("any", "all", "*", "ip", "0"):
        return "any"
    return t


def _canonical_ip(tok: str) -> Tuple[str, Optional[list]]:
    """Return canonical display string + parsed ranges."""
    t = (tok or "").strip()
    if not t or t.lower() in ("any", "all", "*", "0.0.0.0/0", "::/0", "0/0"):
        return ANY, [parse_addr_token("any")[0], parse_addr_token("any")[1]]
    ranges = parse_addr_token(t)
    if is_any(ranges):
        return ANY, [parse_addr_token("any")[0], parse_addr_token("any")[1]]
    # rebuild canonical display from the original token (already canonical-ish)
    return t, ranges


def _canonical_port(tok: str) -> Tuple[str, Optional[list]]:
    t = (tok or "").strip()
    if not t or t in ("*", "any", "ANY", "any-any", "all"):
        return ANY, []
    t = t.strip("[]")
    if ":" in t and "-" not in t:
        pass
    intervals = parse_ports(t)
    return t if t else ANY, intervals


def _finish_rule(pos: int, line_no: int, *,
                 action: Action, raw: str = "",
                 protocol: str = "any",
                 src: str = ANY, sport: str = ANY,
                 dst: str = ANY, dport: str = ANY,
                 direction: Direction = Direction.INOUT,
                 interface: Optional[str] = None,
                 log: bool = False, chain: Optional[str] = None,
                 rule_type: RuleType = RuleType.NORMAL,
                 description: str = "") -> FirewallRule:
    src_d, src_ranges = _canonical_ip(src)
    dst_d, dst_ranges = _canonical_ip(dst)
    sport_d, sport_int = _canonical_port(sport)
    dport_d, dport_int = _canonical_port(dport)
    rule = FirewallRule(
        rule_id=rule_id_at(pos),
        line_no=line_no,
        position=pos,
        action=action,
        direction=direction,
        protocol=_norm_proto(protocol),
        src_ip=src_d,
        src_port=sport_d,
        dst_ip=dst_d,
        dst_port=dport_d,
        interface=interface,
        log=log,
        raw=raw,
        chain=chain,
        rule_type=rule_type,
        description=description,
    )
    rule.src_nets = src_ranges
    rule.dst_nets = dst_ranges
    rule.src_port_intervals = sport_int
    rule.dst_port_intervals = dport_int
    rule.protocol_any = rule.protocol == "any"
    return rule


# --------------------------------------------------------------------------
# iptables
# --------------------------------------------------------------------------

def parse_iptables(text: str, warnings: List[str]) -> ParseResult:
    result = ParseResult(warnings=warnings)
    pos = 0
    current_chain: Optional[str] = None
    current_policy_deny = False
    default_policy_seen = False

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        m_chain = re.match(r"^:([A-Za-z0-9_]+)\s+(\S+)", line)
        if m_chain:
            current_chain = m_chain.group(1)
            default_policy_seen = True
            policy = m_chain.group(2).upper()
            current_policy_deny = policy in ("DROP", "REJECT")
            # synthesize a DEFAULT_DENY marker rule so detectors see the tail
            if current_policy_deny:
                r = _finish_rule(
                    pos, line_no,
                    action=Action.DROP if policy == "DROP" else Action.REJECT,
                    raw=raw, chain=current_chain,
                    rule_type=RuleType.DEFAULT_DENY,
                    description="chain policy default deny",
                )
                result.rules.append(r)
                pos += 1
            continue
        if line.startswith("*") or line.startswith("COMMIT"):
            continue
        m_rule = re.match(r"^\-A\s+(\S+)\s+(.*)$", line)
        if not m_rule:
            m_rule = re.match(r"^\-(I|D|R)\s+(\S+)\s+(.*)$", line)
            if m_rule:
                continue  # skip -I/-D/-R editing style, no definitive ordering
        if m_rule:
            chain = m_rule.group(1)
            body = m_rule.group(2)
            r = _iptables_body(body, pos, line_no, raw, chain)
            if r:
                result.rules.append(r)
                pos += 1
            else:
                warnings.append(f"line {line_no}: unparsable iptables rule")
            continue
        # minimal -L style:  target prot opt source destination
        m_l = re.match(
            r"^(\S+)\s+(tcp|udp|icmp|icmp6|ip|all|any)\s+--\s+"
            r"(\S+)\s+(\S+)\s+(.*)$", line)
        if m_l:
            action = _action_from_target(m_l.group(1))
            r = _finish_rule(
                pos, line_no, action=action,
                protocol=_norm_proto(m_l.group(2)),
                src=m_l.group(3), dst=m_l.group(4),
                raw=raw, chain=current_chain,
                description=m_l.group(5).strip(),
            )
            result.rules.append(r)
            pos += 1

    if not default_policy_seen and text.strip():
        r = _finish_rule(
            pos, len(text.splitlines()) + 1,
            action=Action.DROP, raw="<implicit no-match>",
            rule_type=RuleType.DEFAULT_DENY,
            description="implicit default-deny (no -P policy found)",
        )
        result.rules.append(r)
        pos += 1
    return result


def _action_from_target(target: str) -> Action:
    t = target.upper()
    if t in ("ACCEPT", "ALLOW"):
        return Action.ALLOW
    if t in ("DROP", "REJECT", "DENY", "REJECT:", "DROP;RETURN"):
        return Action.DROP if t != "REJECT" else Action.REJECT
    return Action.ALLOW  # counters/unknown target treated as permit pasted


def _iptables_body(body: str, pos: int, line_no: int, raw: str,
                   chain: str) -> Optional[FirewallRule]:
    mm = {
        "proto": re.search(r"-p\s+(\S+)", body),
        "sport": re.search(r"--sport\s+(\S+)", body),
        "dport": re.search(r"--dport\s+(\S+)", body),
        "src": re.search(r"-s\s+(\S+)", body),
        "dst": re.search(r"-d\s+(\S+)", body),
        "iface_in": re.search(r"-i\s+(\S+)", body),
        "iface_out": re.search(r"-o\s+(\S+)", body),
        "jump": re.search(r"-j\s+(\S+)", body),
        "log": re.search(r"--log-prefix\s+[\"']?([^\"']+)[\"']?", body),
        "comment": re.search(r"-m\s+comment\s+--comment\s+[\"']([^\"']+)[\"']", body),
    }
    proto = mm["proto"].group(1) if mm["proto"] else "any"
    if proto.lower() == "icmpv6":
        proto = "icmp6"
    src = mm["src"].group(1) if mm["src"] else ANY
    dst = mm["dst"].group(1) if mm["dst"] else ANY
    sport = mm["sport"].group(1) if mm["sport"] else ANY
    dport = mm["dport"].group(1) if mm["dport"] else ANY
    jump = mm["jump"].group(1) if mm["jump"] else "ACCEPT"
    if jump.upper() in ("LOG",):
        return None
    action = _action_from_target(jump)
    is_nat = chain and chain.upper() in ("POSTROUTING", "PREROUTING", "DNAT",
                                          "SNAT", "NAT", "MASQUERADE")
    if is_nat:
        return None  # nat handled separately below (best-effort parse)
    direction = Direction.IN if chain and chain.upper() == "INPUT" else (
        Direction.OUT if chain and chain.upper() == "OUTPUT" else Direction.INOUT)
    log = bool(mm["log"])
    desc = ""
    if mm["comment"]:
        desc = mm["comment"].group(1)
    elif mm["log"]:
        desc = f"log: {mm['log'].group(1)}"
    return _finish_rule(
        pos, line_no, action=action, protocol=proto, src=src, sport=sport,
        dst=dst, dport=dport, direction=direction,
        interface=mm["iface_in"].group(1) if mm["iface_in"] else None,
        log=log, chain=chain,
        description=desc,
    )


# --------------------------------------------------------------------------
# Cisco ASA
# --------------------------------------------------------------------------

ASA_ACL_RE = re.compile(
    r"^\s*access-list\s+(\S+)\s+(extended\s+|)(permit|deny)\s+(.*)$",
    re.IGNORECASE)


def parse_cisco_asa(text: str, warnings: List[str]) -> ParseResult:
    result = ParseResult(warnings=warnings)
    pos = 0
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("!") or line.startswith("#"):
            continue
        m_acl = re.match(
            r"^\s*access-list\s+(\S+)\s+(extended\s+)?(permit|deny)\s+(.+)$",
            line, re.IGNORECASE)
        if not m_acl:
            continue
        acl, _, action_str, rest = m_acl.group(1), m_acl.group(2), \
            m_acl.group(3), m_acl.group(4)
        parts = _split_asa(rest)
        r = _asa_rule(parts, acl, action_str, line_no, pos, raw)
        if r:
            result.rules.append(r)
            pos += 1
        else:
            warnings.append(f"line {line_no}: unparsable ASA object")
    return result


def _split_asa(rest: str) -> List[str]:
    out: List[str] = []
    buf = ""
    for ch in rest:
        if ch == " " and buf:
            out.append(buf)
            buf = ""
        else:
            buf += ch
    if buf:
        out.append(buf)
    return out


def _asa_rule(parts: List[str], acl: str, action_str: str,
              line_no: int, pos: int, raw: str) -> Optional[FirewallRule]:
    action = Action.ALLOW if action_str.lower() == "permit" else Action.DENY
    proto = "any"
    src = ANY
    sport = ANY
    dst = ANY
    dport = ANY
    i = 0
    if not parts:
        return None
    tok0 = parts[0].rstrip(",").upper()
    # strip object names like "object network FOO" when object-id not resolvable
    if tok0 in ("TCP", "UDP", "ICMP", "ICMP6", "GRE", "ESP", "AH", "SCTP", "IP", "ANY", "IPV6", "IPV4"):
        proto = tok0.lower()
        i = 1
    elif tok0 in ("OBJECT", "NETWORK") or "." not in parts[0] and ":" not in parts[0]:
        # could be "object-group" etc; just skip to first ip-ish token
        pass

    # find source position by scanning for first token containing '.' or ':'
    src_idx = -1
    for idx, t in enumerate(parts):
        tt = t.rstrip(",")
        base = tt.split("/")[0].strip("[]")
        if base == "any" or "/" in tt or "." in base or ":" in base:
            src_idx = idx
            break
    if src_idx == -1:
        return None
    src_raw = parts[src_idx].rstrip(",")
    # next token might be eq/neq/range/lt/gt port spec or the destination
    j = src_idx + 1
    if j < len(parts):
        op = parts[j].rstrip(",").lower()
        if op in ("eq", "neq", "lt", "gt", "range") and j + 1 < len(parts):
            if op == "range" and j + 2 < len(parts):
                sport = f"{parts[j+1]}:{parts[j+2]}"
                j += 3
            else:
                sport = parts[j + 1].rstrip(",")
                j += 2
    # destination = next token
    while j < len(parts):
        t = parts[j].rstrip(",")
        base = t.split("/")[0].strip("[]")
        if base == "any" or "/" in t or "." in base or ":" in base:
            dst = t
            k = j + 1
            if k < len(parts):
                op = parts[k].rstrip(",").lower()
                if op in ("eq", "neq", "lt", "gt", "range") and k + 1 < len(parts):
                    if op == "range" and k + 2 < len(parts):
                        dport = f"{parts[k+1]}:{parts[k+2]}"
                    else:
                        dport = parts[k + 1].rstrip(",")
            break
        j += 1
    if not dst:
        return None
    return _finish_rule(
        pos, line_no, action=action, protocol=proto,
        src=src_raw, sport=sport, dst=dst, dport=dport,
        direction=Direction.IN, chain=acl, description=f"ASA ACL {acl}",
    )


# --------------------------------------------------------------------------
# FortiGate
# --------------------------------------------------------------------------

def parse_fortigate(text: str, warnings: List[str]) -> ParseResult:
    result = ParseResult(warnings=warnings)
    addresses: dict = {}

    def _resolve(obj: str) -> str:
        obj = obj.strip().strip('"')
        if obj in addresses:
            return addresses[obj]
        return obj

    # pass 1: collect address objects (config firewall address)
    cur_edit = None
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        m_edit = re.match(r"^edit\s+[\"']?([^\"']+)", line)
        if m_edit:
            cur_edit = m_edit.group(1)
            continue
        m_subnet = re.search(r"set\s+subnet\s+(\S+)\s+(\S+)", line)
        if m_subnet and cur_edit:
            host = m_subnet.group(1)
            mask_or_prefix = m_subnet.group(2)
            addresses[cur_edit] = _host_with_prefix(host, mask_or_prefix)
        m_type = re.search(r"set\s+type\s+(\S+)", line)
        if m_type and cur_edit and cur_edit not in addresses:
            addresses[cur_edit] = _comm_service_port(m_type.group(1))

    pos = 0
    in_policy = False
    current: dict = {}
    policy_key = None
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("config firewall policy") or line.startswith("edit 0"):
            in_policy = True
            continue
        if in_policy and line.startswith("config") and "firewall" in line:
            in_policy = False
            continue
        if in_policy and line.startswith("edit "):
            current = {}
            continue
        if in_policy and line.startswith("next"):
            if current:
                r = _forti_rule(current, addresses, line_no, pos, raw)
                if r:
                    result.rules.append(r)
                    pos += 1
            current = {}
            continue
        if in_policy and line.startswith("set "):
            m = re.match(r"^set\s+(\S+)\s+(.+)$", line)
            if m:
                key = m.group(1)
                val = m.group(2).strip().strip('"')
                if key in ("srcaddr", "dstaddr", "service", "srcintf", "dstintf"):
                    val = val.split()[0]  # first name; multi handled loosely
                if key == "action" and current.get("action") is None:
                    current["action"] = val
                else:
                    # first wins for repeated keys (status/action ordering safe)
                    current.setdefault(key, val)
    return result


def _forti_rule(cur: dict, addresses: dict, line_no: int, pos: int,
                raw: str) -> Optional[FirewallRule]:

    def resolve(obj: str) -> str:
        obj = obj.strip().strip('"')
        if obj in addresses:
            return addresses[obj]
        return obj

    status = cur.get("status", "enable").lower()
    if status in ("disable", "disabled"):
        return None
    action_s = cur.get("action", "accept").lower()
    if action_s in ("accept", "permit", "allow"):
        action = Action.ALLOW
    elif action_s in ("deny", "drop"):
        action = Action.DENY
    else:
        action = Action.ALLOW
    proto = _norm_proto(cur.get("protocol", "any"))
    src = resolve(cur.get("srcaddr", "any"))
    dst = resolve(cur.get("dstaddr", "any"))
    srci = cur.get("srcintf", "any")
    dsti = cur.get("dstintf", "any")
    service = cur.get("service", "any")
    sport, dport = ANY, ANY
    if service and service.lower() != "any":
        dport = _service_to_port(service)
    desc = cur.get("comments", "")
    logtraffic = cur.get("logtraffic", "").lower()
    return _finish_rule(
        pos, line_no, action=action, protocol=proto, src=src, dst=dst,
        sport=sport, dport=dport,
        direction=Direction.IN if dsti in ("wan", "external", "internet")
        else Direction.INOUT,
        interface=srci if srci and srci != "any" else dsti,
        log=logtraffic not in ("", "disable", "disabled", "none"),
        chain="fw.policy",
        description=desc,
    )


_COMMON_SERVICES = {
    "http": "80", "https": "443", "ssh": "22", "telnet": "23", "ftp": "21",
    "dns": "53", "smtp": "25", "pop3": "110", "imap": "143", "rdp": "3389",
    "mysql": "3306", "postgresql": "5432", "ntp": "123", "snmp": "161",
    "syslog": "514", "icmp": "1:65535", "ping": "1:65535", "any": "any",
    "ipsec": "500", "smb": "445", "iscsi": "3260", "mssql": "1433",
    "oracle": "1521",
}


def _service_to_port(service: str) -> str:
    key = service.lower().strip()
    return _COMMON_SERVICES.get(key, key)


def _comm_service_port(name: str) -> str:
    key = name.lower().strip()
    return _COMMON_SERVICES.get(key, key)


def _mask_to_prefix(mask: str) -> Optional[int]:
    """Convert '255.255.255.0' to 24. Returns None for /N prefixes or bad input."""
    if mask.isdigit():
        return int(mask) if 0 <= int(mask) <= 32 else None
    try:
        octets = [int(o) for o in mask.split(".")]
    except ValueError:
        return None
    if len(octets) != 4 or any(o not in range(256) for o in octets):
        return None
    bits = 0
    for octet in octets:
        s = f"{octet:08b}"
        if "01" in s:
            return None  # non-contiguous mask
        bits += s.count("1")
    return bits


def _host_with_prefix(host: str, mask_or_prefix: str) -> str:
    p = _mask_to_prefix(mask_or_prefix)
    if p is not None:
        return f"{host}/{p}"
    return f"{host}/{mask_or_prefix}"


# --------------------------------------------------------------------------
# pfSense config.xml
# --------------------------------------------------------------------------

PF_RULE_RE = re.compile(
    r"<rule>\s*(.*?)</rule>", re.DOTALL | re.IGNORECASE)


def parse_pfsense(text: str, warnings: List[str]) -> ParseResult:
    result = ParseResult(warnings=warnings)
    pos = 0
    for m in PF_RULE_RE.finditer(text):
        block = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        action_s = _xml_val(block, "action")
        if action_s in ("pass", "allow", "permit"):
            action = Action.ALLOW
        elif action_s in ("block", "blockdrop", "reject"):
            action = Action.DROP
        elif action_s in ("reject",):
            action = Action.REJECT
        else:
            action = Action.ALLOW
        direction_s = _xml_val(block, "direction").lower() or "any"
        direction = {
            "in": Direction.IN, "out": Direction.OUT,
            "any": Direction.INOUT,
        }.get(direction_s, Direction.INOUT)
        proto = _norm_proto(_xml_val(block, "protocol"))
        src = _pf_addr(block, "source")
        dst = _pf_addr(block, "destination")
        sport = _xml_val(block, "sourceport")
        dport = _xml_val(block, "destinationport")
        if not sport:
            sport = ANY
        if not dport:
            dport = ANY
        desc = _xml_val(block, "description")
        log = _xml_val(block, "log").lower() in ("true", "1", "yes", "log")
        iface = _xml_val(block, "interface")
        r = _finish_rule(
            pos, line_no, action=action, protocol=proto, src=src, sport=sport,
            dst=dst, dport=dport, direction=direction,
            interface=iface or None, log=log, chain="pfsense",
            description=desc,
        )
        result.rules.append(r)
        pos += 1
    return result


def _xml_val(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    return m.group(1).strip()


def _pf_addr(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.DOTALL | re.IGNORECASE)
    if not m:
        return "any"
    sub = m.group(1)
    address = _xml_val(sub, "address")
    cidr = _xml_val(sub, "network")
    if cidr:
        if "/" in cidr:
            return cidr
        return f"{address or '0.0.0.0'}/{cidr}"
    if address:
        return address
    ntype = _xml_val(sub, "type")
    return "any" if ntype in ("any", "") else ntype


# --------------------------------------------------------------------------
# Windows advfirewall / netsh
# --------------------------------------------------------------------------

WINDOWS_RULE_RE = re.compile(
    r"^(?:Rule|Name|DisplayName)?[^\n]*?\bset\s+profile\s+|\bbegin rule\b",
    re.IGNORECASE)


def parse_windows(text: str, warnings: List[str]) -> ParseResult:
    result = ParseResult(warnings=warnings)
    pos = 0
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()
        i += 1

        # new rule starts at "begin rule"
        if re.match(r"^begin\s+rule", line, re.IGNORECASE):
            block: List[str] = []
            while i < n and not re.match(r"^end\s+rule", lines[i].strip(),
                                         re.IGNORECASE):
                block.append(lines[i].strip())
                i += 1
            i += 1  # consume end rule
            rule = _windows_rule(block, pos, raw_line)
            if rule:
                result.rules.append(rule)
                pos += 1
            continue

        # alternate flat 'netsh advfirewall firewall add rule' form already
        # collected per-line
        if line.startswith("add rule") or re.match(r"^[\w ]*add rule", line):
            r = _windows_flat(line, pos, i - 1, raw_line)
            if r:
                result.rules.append(r)
                pos += 1
            continue

    return result


def _windows_flat(line: str, pos: int, line_no: int,
                  raw: str) -> Optional[FirewallRule]:
    # netsh advfirewall firewall add rule name=X dir=in action=allow enable=yes
    # profile=any localip=... remoteip=... localport=443 protocol=TCP
    def gv(key: str) -> str:
        m = re.search(rf"{key}\s*=\s*([^\s,]+)", line, re.IGNORECASE)
        if not m:
            return ""
        return m.group(1).strip('"')

    name = gv("name")
    direction = gv("dir").lower()
    action_s = gv("action").lower()
    action = Action.ALLOW if action_s in ("allow", "permit") else Action.DENY
    proto = _norm_proto(gv("protocol"))
    remote = gv("remoteip") or ANY
    local = gv("localip") or ANY
    rport = gv("remoteport")
    lport = gv("localport")
    enable = gv("enable")
    if enable.lower() in ("no", "false", "0"):
        return None
    return _finish_rule(
        pos, line_no,
        action=action, protocol=proto,
        src=("ANY" if remote == "any" else remote),
        sport=rport or ANY,
        dst=("ANY" if local == "any" else local),
        dport=lport or ANY,
        direction=Direction.IN if direction == "in"
        else Direction.OUT if direction == "out" else Direction.INOUT,
        chain="advfirewall",
        description=name,
    )


def _windows_rule(block: List[str], pos: int, raw: str) -> Optional[FirewallRule]:
    vals: dict = {}
    for b in block:
        m = re.match(r"^([A-Za-z]+)\s*(?:=|)\s*(.+)$", b)
        if m:
            vals[m.group(1).lower()] = m.group(2).strip()

    def wk(*keys, default: str = "") -> str:
        for k in keys:
            if vals.get(k):
                return vals[k]
        return default

    action = wk("action", default="allow").lower()
    if action in ("allow", "permit"):
        action_a = Action.ALLOW
    else:
        action_a = Action.DENY
    if wk("enabled", "enable", default="yes").lower() in ("no", "false", "0"):
        return None
    proto = _norm_proto(wk("protocol", default="any"))
    rports = wk("rports", "rport", "remoteport", "rportslist", default="any")
    lports = wk("lports", "lport", "localport", "lportslist", default="any")
    raddrs = wk("raddresses", "raddr", "remoteaddr", "remoteip", "raccept",
                default="any")
    laddrs = wk("laddresses", "laddr", "localaddr", "localip", default="any")
    direction = wk("dir", "direction", "interface", default="both").lower()
    name = wk("name", "displayname", "group")
    if not name:
        name = ""
    return _finish_rule(
        pos, 0, action=action_a, protocol=proto,
        src=raddrs, sport=rports, dst=laddrs, dport=lports,
        direction=Direction.IN if direction in ("in", "inbound")
        else Direction.OUT if direction in ("out", "outbound")
        else Direction.INOUT,
        chain="advfirewall", description=name,
    )


# --------------------------------------------------------------------------
# Palo Alto (set security policy)
# --------------------------------------------------------------------------

def parse_paloalto(text: str, warnings: List[str]) -> ParseResult:
    result = ParseResult(warnings=warnings)
    rules: dict = {}
    order: List[str] = []

    # A PA security rule stanza can be a single set line or split per field:
    #   set rulebase security rules NAME from LAN to WAN source corp_lan ...
    #   set rulebase security rules NAME from "LAN"
    #   set rulebase security rules NAME source member "corp_lan"
    cmd_re = re.compile(
        r"^\s*set\s+rulebase\s+security\s+rules\s+([^\s]+)(?:\s+(.*))?$")
    field_re = re.compile(
        r"\b(from|to|source|destination|user|application|service|action|"
        r"log-start|log-end)\b\s+([^\n]+?)(?=\s+\b(?:from|to|source|"
        r"destination|user|application|service|action|log-start|log-end)\b|$)")

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        m = cmd_re.match(line)
        if not m:
            continue
        name = m.group(1)
        rest = m.group(2) or ""
        if name not in rules:
            rules[name] = {}
            order.append(name)
        for fm in field_re.finditer(rest):
            key = fm.group(1)
            val = fm.group(2).strip().strip('"')
            if key == "action":
                rules[name]["action"] = val
            elif key in ("from", "to", "source", "destination",
                         "application", "service"):
                rules[name].setdefault(key, val)
            elif key in ("log-start", "log-end"):
                rules[name].setdefault("log-end", val)

    pos = 0
    for name in order:
        cur = rules[name]
        action_s = cur.get("action", "allow").lower()
        if action_s in ("allow", "permit", "accept"):
            action = Action.ALLOW
        elif action_s in ("deny", "drop"):
            action = Action.DENY
        else:
            action = Action.ALLOW
        src = _pa_member(cur.get("source", "any"))
        dst = _pa_member(cur.get("destination", "any"))
        service = _pa_member(cur.get("service", "any"))
        app = _pa_member(cur.get("application", "any"))
        proto = "any"
        dport = service if service and service != "any" else ANY
        vfrom = _pa_member(cur.get("from", "any"))
        vto = _pa_member(cur.get("to", "any"))
        r = _finish_rule(
            pos, 0, action=action, protocol=proto, src=src, dst=dst,
            dport=dport, direction=Direction.IN,
            interface=vfrom if vfrom != "any" else (vto if vto != "any" else None),
            log=cur.get("log-end", "") not in ("", "disable", "false", "no"),
            chain=f"sec.{name}", description=name,
        )
        result.rules.append(r)
        pos += 1
    return result


def _pa_member(val: str) -> str:
    """Extract the first real member name from a PA value token."""
    val = (val or "").strip().strip('"')
    if val.lower().startswith("member"):
        val = val[len("member"):].strip()
        val = val.strip('"')
    vals = [v.strip().strip('"') for v in val.split() if v.strip()]
    return vals[0] if vals else "any"


# --------------------------------------------------------------------------
# Plain tabular
# --------------------------------------------------------------------------

def parse_plain(text: str, warnings: List[str]) -> ParseResult:
    result = ParseResult(warnings=warnings)
    pos = 0
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.replace("|", ",").split(",")]
        if len(cells) < 3:
            warnings.append(f"line {line_no}: table rule needs "
                            f"action,proto,src,dst (got {len(cells)})")
            continue
        action_s = cells[0].lower()
        if action_s in ("allow", "permit", "accept"):
            action = Action.ALLOW
        elif action_s in ("deny",):
            action = Action.DENY
        elif action_s in ("drop",):
            action = Action.DROP
        elif action_s in ("reject", "reject with"):
            action = Action.REJECT
        else:
            action = Action.ALLOW
        proto = _norm_proto(cells[1])
        src = cells[2]
        if len(cells) > 3:
            dst = cells[3]
        else:
            dst = ANY
        sport = cells[4] if len(cells) > 4 and cells[4] else ANY
        dport = cells[5] if len(cells) > 5 and cells[5] else ANY
        desc = cells[6] if len(cells) > 6 else ""
        r = _finish_rule(
            pos, line_no, action=action, protocol=proto, src=src, sport=sport,
            dst=dst, dport=dport, chain="plain", description=desc.strip(),
            raw=line,
        )
        result.rules.append(r)
        pos += 1
    return result


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

PARSERS = {
    "iptables": parse_iptables,
    "cisco-asa": parse_cisco_asa,
    "fortigate": parse_fortigate,
    "pfsense": parse_pfsense,
    "windows": parse_windows,
    "paloalto": parse_paloalto,
    "plain": parse_plain,
}


def parse(fmt: str, text: str) -> ParseResult:
    """Parse `text` in vendor format `fmt`.

    Deduplicates default-deny chain-policy rules that guaranteed presence
    after normalization.
    """
    parser = PARSERS.get(fmt or "plain")
    if parser is None:
        parser = PARSERS["plain"]
    warnings: List[str] = []
    res = parser(text, warnings)

    # remove duplicate synthesized default-deny for same chain (keep first)
    seen_chains: set = set()
    kept: List[FirewallRule] = []
    for r in res.rules:
        if r.rule_type == RuleType.DEFAULT_DENY and r.chain:
            key = (r.chain, r.action.value)
            if key in seen_chains:
                continue
            seen_chains.add(key)
        kept.append(r)
    res.rules = kept
    return res