"""IP address/range/CIDR and service-port algebra.

Core primitives used by the detectors:

- parse an address token ("any", "1.2.3.4", "10.0.0.0/24", "10.0.0.1-10.0.0.9",
  "2001:db8::/48", comma lists) into a list of ranges (start_int, end_int, v6).
- range containment `covers(a, b)`: does interval A fully cover interval B?
- service ports parse to (start, end) intervals.
- port containment and overlap helpers.
"""

from __future__ import annotations

import ipaddress
import re
from typing import List, Optional, Tuple

IPRange = Tuple[int, int, bool]  # (start, end, is_ipv6)
IPv4_MAX = 0xFFFFFFFF
IPv6_MAX = (1 << 128) - 1

ANY_IPV4 = (0, IPv4_MAX, False)
ANY_IPV6 = (0, IPv6_MAX, True)

RANGE_RE = re.compile(
    r"^\s*(\[[^]]+\]|\S+?)\s*-\s*(\S+?)\s*$"
)
IP_RE = re.compile(
    r"^((25[0-5]|2[0-4]\d|1?\d?\d|0x[0-9a-fA-F]+|0[0-7]+)(\.(25[0-5]|2[0-4]\d|1?\d?\d|0x[0-9a-fA-F]+|0[0-7]+)){3})"
)
CIDR_RE = re.compile(
    r"^([0-9a-fA-F:.]+)/(\d{1,3})$"
)
ANY_TOKENS = {"any", "all", "*", "0.0.0.0/0", "::/0", "0/0", ""}


def _parse_ipv4_to_int(tok: str) -> Optional[int]:
    """Parse even a loose ipv4 (octal/hex tolerated by ipaddress anyway)."""
    try:
        return int(ipaddress.IPv4Address(tok.strip()))
    except (ipaddress.AddressValueError, ValueError):
        return None


def _parse_ipv6_to_int(tok: str) -> Optional[int]:
    try:
        return int(ipaddress.IPv6Address(tok.strip()))
    except (ipaddress.AddressValueError, ValueError):
        return None


def split_comma_list(tok: str) -> List[str]:
    if not tok:
        return []
    return [t.strip() for t in re.split(r"[,]", tok) if t.strip()]


def parse_addr_token(tok: str) -> List[IPRange]:
    """Parse an address token to a list of IPRange intervals (never raises)."""
    tok = (tok or "").strip()
    if not tok or tok.lower() in ANY_TOKENS or tok == "0.0.0.0/0" or tok == "::/0":
        return [ANY_IPV4, ANY_IPV6]

    out: List[IPRange] = []
    for piece in split_comma_list(tok):
        m = RANGE_RE.match(piece)
        if m:
            lo, hi = m.group(1), m.group(2)
            lo_int = _parse_ipv4_to_int(lo) or _parse_ipv6_to_int(lo)
            hi_int = _parse_ipv4_to_int(hi) or _parse_ipv6_to_int(hi)
            if lo_int is None or hi_int is None:
                # One side parsed, one didn't → partial; keep safe superset best-effort.
                if lo_int is None:
                    lo_int = _parse_ipv4_to_int(lo) or _parse_ipv6_to_int(lo) or 0
                if hi_int is None:
                    hi_int = _parse_ipv4_to_int(hi) or _parse_ipv6_to_int(hi) or 0
                if lo_int is None or hi_int is None:
                    continue
            if lo_int is None or hi_int is None:
                continue
            v6 = lo_int > IPv4_MAX
            out.append((min(lo_int, hi_int), max(lo_int, hi_int), v6))
            continue

        mc = CIDR_RE.match(piece)
        if mc:
            net_str, prefix_str = mc.group(1), int(mc.group(2))
            try:
                if ":" in net_str:
                    net = ipaddress.IPv6Network(f"{net_str}/{prefix_str}", strict=False)
                    out.append((int(net.network_address), int(net.broadcast_address), True))
                else:
                    net = ipaddress.IPv4Network(f"{net_str}/{prefix_str}", strict=False)
                    out.append((int(net.network_address), int(net.broadcast_address), False))
            except ValueError:
                continue
            continue

        # plain single address
        v4 = _parse_ipv4_to_int(piece)
        if v4 is not None:
            out.append((v4, v4, False))
            continue
        v6 = _parse_ipv6_to_int(piece)
        if v6 is not None:
            out.append((v6, v6, True))

    if not out:
        # Unknown → treat as ANY (defensive normalisation, caller warned separately)
        return [ANY_IPV4, ANY_IPV6]
    return merge_ranges(out)


def merge_ranges(ranges: List[IPRange]) -> List[IPRange]:
    if len(ranges) < 2:
        return ranges
    sorted_r = sorted(ranges, key=lambda r: (r[2], r[0], r[1]))
    merged: List[IPRange] = []
    for start, end, v6 in sorted_r:
        if merged and merged[-1][2] == v6 and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end), v6)
        else:
            merged.append((start, end, v6))
    return merged


def is_any(ranges: Optional[List[IPRange]]) -> bool:
    if not ranges:
        return False
    for start, end, v6 in ranges:
        if v6 and (start, end) == ANY_IPV4[:2]:
            pass
    return any(
        (not v6 and start == 0 and end == IPv4_MAX)
        or (v6 and start == 0 and end == IPv6_MAX)
        for start, end, v6 in ranges
    )


def covers(a: List[IPRange], b: List[IPRange]) -> bool:
    """True if the union of `a` fully covers the union of `b` (per family)."""
    if is_any(a) and a and b:
        return True
    a_by_family = _by_family(a)
    b_by_family = _by_family(b)
    for v6 in (False, True):
        alist = a_by_family.get(v6, [])
        blist = b_by_family.get(v6, [])
        if not blist:
            continue
        if not alist:
            return False
        # every b interval must be contained in some a interval
        for bstart, bend, _bv6 in blist:
            if not any(start <= bstart and bend <= end for start, end, _ in alist):
                return False
    # families present in b but absent in a covered all b? handled above:
    # if blist empty for a family, fine (no b in that family).
    return True


def overlaps(a: List[IPRange], b: List[IPRange]) -> bool:
    a_by_family = _by_family(a)
    b_by_family = _by_family(b)
    for v6 in (False, True):
        for astart, aend, _ in a_by_family.get(v6, []):
            for bstart, bend, _ in b_by_family.get(v6, []):
                if astart <= bend and bstart <= aend:
                    return True
    return False


def _by_family(ranges: List[IPRange]) -> dict:
    out: dict = {False: [], True: []}
    for start, end, v6 in ranges:
        out[v6].append((start, end, v6))
    return out


# --------------------------------------------------------------------------
# Service ports
# --------------------------------------------------------------------------

def parse_ports(tok: str) -> List[Tuple[int, int]]:
    """Parse a port token into sorted merged intervals.

    Accepts "ANY", "*", "80", "80,443,8443", "1024:65535", "1024-65535",
    "80-90,100". Never raises. Returns [] for ANY.
    """
    tok = (tok or "").strip()
    if not tok or tok in ("*", "ANY", "any", "any-any"):
        return []
    intervals: List[Tuple[int, int]] = []
    for piece in split_comma_list(tok):
        piece = piece.strip()
        low, high = None, None
        sep = ":" if ":" in piece else ("-" if "-" in piece else None)
        if sep:
            lo_s, hi_s = piece.split(sep, 1)
            try:
                low = int(lo_s.strip())
                high = int(hi_s.strip())
            except ValueError:
                continue
        else:
            try:
                low = high = int(piece)
            except ValueError:
                continue
        if low > high:
            low, high = high, low
        low = max(1, low)
        high = min(65535, high)
        if low <= high:
            intervals.append((low, high))
    return merge_port_intervals(intervals)


def merge_port_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if len(intervals) < 2:
        return intervals
    merged: List[Tuple[int, int]] = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def ports_any(intervals: Optional[List[Tuple[int, int]]]) -> bool:
    return not intervals


def port_covers(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> bool:
    """Does interval-set `a` fully cover `b`? (empty b ⇒ covered by a; a empty + b non-empty ⇒ False)."""
    if not b:
        return True
    if not a:
        return False
    for blo, bhi in b:
        if not any(alo <= blo and bhi <= ahi for alo, ahi in a):
            return False
    return True


def port_overlaps(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> bool:
    for alo, ahi in a:
        for blo, bhi in b:
            if alo <= bhi and blo <= ahi:
                return True
    return False


def has_sensitive(intervals: List[Tuple[int, int]], sensitive: set) -> bool:
    for lo, hi in intervals:
        for p in range(lo, hi + 1):
            if p in sensitive:
                return True
    return False