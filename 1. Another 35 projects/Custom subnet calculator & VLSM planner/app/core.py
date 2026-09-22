"""Core networking logic for SubnetPlanner.

Pure-Python, zero dependencies.  Everything the GUI and reports need to know
about IPv4 subnetting lives here so it stays unit-testable headless.

Public API:
    ip_to_int / int_to_ip / validate_ip / validate_prefix
    parse_cidr / mask_to_prefix / prefix_to_mask / prefix_to_wildcard
    ip_class / class_default_prefix
    calculate_subnet
    prefix_from_subnets / prefix_from_hosts
    derive_subnets
    vlsm_plan (+ VlsmSegment / VlsmResult / PlanOverflowError)
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import List, Optional


class PlanOverflowError(ValueError):
    """Raised when a VLSM plan's total demand exceeds the base network."""

    def __init__(self, message: str, deficit: int = 0):
        super().__init__(message)
        self.deficit = deficit


# --------------------------------------------------------------------------
# Low-level helpers
# --------------------------------------------------------------------------

def ip_to_int(ip: str) -> int:
    """Convert a dotted-quad IPv4 string to its unsigned 32-bit integer."""
    return int(ipaddress.IPv4Address(ip.strip()))


def int_to_ip(value: int) -> str:
    """Convert an unsigned 32-bit integer back to dotted-quad notation."""
    return str(ipaddress.IPv4Address(value))


def validate_ip(ip: str) -> bool:
    try:
        ip_to_int(ip)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def validate_prefix(prefix: int) -> bool:
    return isinstance(prefix, int) and 0 <= prefix <= 32


def parse_cidr(cidr: str):
    """Parse 'a.b.c.d/xx' (or a bare IP) -> (ip_int, prefix)."""
    cidr = cidr.strip()
    host_part, _, pfx = cidr.partition("/")
    ip = ip_to_int(host_part)
    if pfx:
        prefix = int(pfx)
    else:
        prefix = 32  # a single host by default
    if not validate_prefix(prefix):
        raise ValueError(f"Invalid prefix /{prefix} — must be 0..32")
    return ip, prefix


def mask_to_prefix(mask: str) -> int:
    """Convert a dotted subnet mask ('255.255.255.0') to a prefix length."""
    m = ip_to_int(mask)
    # Inverted mask must be a run of low consecutive ones (or zero).
    inv = (~m) & 0xFFFFFFFF
    if inv and (inv + 1) & inv:
        raise ValueError(f"{mask} is not a valid consecutive subnet mask")
    return bin(m).count("1")


def prefix_to_mask(prefix: int) -> str:
    if not validate_prefix(prefix):
        raise ValueError(f"Invalid prefix /{prefix}")
    return int_to_ip(((1 << prefix) - 1) << (32 - prefix) if prefix else 0)


def prefix_to_wildcard(prefix: int) -> str:
    if not validate_prefix(prefix):
        raise ValueError(f"Invalid prefix /{prefix}")
    return int_to_ip(((1 << (32 - prefix)) - 1) if prefix < 32 else 0)


def prefix_to_binary(prefix: int) -> str:
    """Binary string of the mask, e.g. /24 -> 11111111111111111111111100000000."""
    return "1" * prefix + "0" * (32 - prefix)


def ip_class(ip_int: int) -> dict:
    """Classful classification of the *first octet* of an address."""
    first = ip_int >> 24
    if 0 <= first <= 127:
        letter, default_pfx = "A", 8
    elif 128 <= first <= 191:
        letter, default_pfx = "B", 16
    elif 192 <= first <= 223:
        letter, default_pfx = "C", 24
    elif 224 <= first <= 239:
        letter, default_pfx = "D", 32
    else:
        letter, default_pfx = "E", 32
    return {"class": letter, "default_prefix": default_pfx}


# --------------------------------------------------------------------------
# Public subnet builder
# --------------------------------------------------------------------------

def _usable_hosts(total_addrs: int, prefix: int) -> int:
    if prefix == 31:
        return total_addrs  # RFC 3021 point-to-point: 2 usable
    if prefix == 32:
        return total_addrs  # single host
    return total_addrs - 2


def calculate_subnet(ip, prefix: int) -> dict:
    """Fully describe one subnet.  `ip` may be dotted-quad str or an int."""
    if isinstance(ip, str):
        ip_int = ip_to_int(ip)
    else:
        ip_int = int(ip)
    if not validate_prefix(prefix):
        raise ValueError(f"Invalid prefix /{prefix}")

    mask_int = ((1 << prefix) - 1) << (32 - prefix) if prefix else 0
    host_bits = 32 - prefix
    total = (1 << host_bits) if host_bits < 32 else 1 << 31  # avoid shift==32
    if prefix == 0:
        total = 1 << 32  # 0.0.0.0/0 is the whole space; represent as 2**32
    network = ip_int & mask_int
    broadcast = network | ((1 << host_bits) - 1) if host_bits else network
    first_usable = network + 1 if prefix <= 30 else network
    last_usable = broadcast - 1 if prefix <= 30 else broadcast
    usable = _usable_hosts(total, prefix)

    cls = ip_class(ip_int)
    class_default = cls["default_prefix"]
    if class_default <= prefix and cls["class"] in ("A", "B", "C"):
        borrowed = prefix - class_default
        subnets_in_class = 1 << borrowed if borrowed else 1
    else:
        borrowed = None
        subnets_in_class = None

    return {
        "ip_input": int_to_ip(ip_int),
        "prefix": prefix,
        "network": int_to_ip(network),
        "broadcast": int_to_ip(broadcast),
        "first_usable": int_to_ip(first_usable),
        "last_usable": int_to_ip(last_usable),
        "mask": int_to_ip(mask_int),
        "mask_binary": prefix_to_binary(prefix),
        "wildcard": prefix_to_wildcard(prefix),
        "total_addresses": total,
        "usable_hosts": usable,
        "host_bits": host_bits,
        "network_bits": prefix,
        "ip_binary": f"{ip_int:032b}",
        "class": cls["class"],
        "class_default_prefix": class_default,
        "borrowed_bits": borrowed,
        "subnets_in_class": subnets_in_class,
        "is_subnet_of_classful": class_default <= prefix,
    }


def prefix_from_subnets(count: int) -> Optional[int]:
    """Given a desired number of equal subnets, return the *host-bit* count.

    E.g. prefix +3 for 8 subnets -> derive later via prefix+? — this returns
    the number of subnet bits to *add*; caller decides base.
    """
    n = count
    if n < 1:
        raise ValueError("Number of subnets must be >= 1")
    bits = 0
    power = 1
    while power < n:
        power <<= 1
        bits += 1
    return bits  # borrow bits


def prefix_from_hosts(hosts: int) -> int:
    """Smallest prefix that yields at least `hosts` usable addresses (per /X)."""
    if hosts < 1:
        raise ValueError("Required hosts must be >= 1")
    total_needed = hosts + 2  # network + broadcast
    bits = 32
    block = 1
    while block < total_needed and bits > 0:
        block <<= 1
        bits -= 1
    return bits


def derive_subnets(ip, base_prefix: int, count: int = None,
                   max_rows: int = 256) -> dict:
    """List the equal-size subnets created by borrowing bits.

    The subnets start at the *classful* network of `ip` and are sliced at
    `base_prefix`; the number is 2^(base_prefix − classful_default).  For
    /31 and /32 only the single subnet containing `ip` is described.

    Returns {"prefix", "subnets": [...], "truncated", "total"}.
    """
    net = calculate_subnet(ip, base_prefix)
    mask_int = ((1 << base_prefix) - 1) << (32 - base_prefix) if base_prefix else 0
    cls = ip_class(ip_to_int(ip) if isinstance(ip, str) else ip)

    if base_prefix in (31, 32):
        start = (ip_to_int(ip) if isinstance(ip, str) else ip) & mask_int
        block = 2 if base_prefix == 31 else 1
        total = 1
        first = int_to_ip(start) if base_prefix == 31 else int_to_ip(start)
        last = int_to_ip(start + block - 1)
        broadcast = int_to_ip(start + block - 1) if base_prefix == 31 else int_to_ip(start)
        usable = _usable_hosts(block, base_prefix)
        return {"prefix": base_prefix,
                "subnets": [{
                    "index": 0, "network": int_to_ip(start),
                    "first": first, "last": last,
                    "broadcast": broadcast, "mask": net["mask"],
                    "usable": usable}],
                "truncated": False, "total": 1}

    default = cls["default_prefix"]
    if base_prefix <= default:
        total = 1
        start = net["network"]
    else:
        total = 1 << (base_prefix - default)
        class_net = (ip_to_int(ip) if isinstance(ip, str) else ip) \
            & (((1 << default) - 1) << (32 - default)) if default else 0
        start = class_net if default else 0

    block = (1 << (32 - base_prefix)) if base_prefix else (1 << 32)
    rows = []
    for i in range(total):
        if len(rows) >= max_rows:
            break
        n = start + i * block
        rows.append({
            "index": i,
            "network": int_to_ip(n),
            "first": int_to_ip(n + 1),
            "last": int_to_ip(n + block - 2),
            "broadcast": int_to_ip(n + block - 1),
            "mask": net["mask"],
            "usable": net["usable_hosts"],
        })
    return {"prefix": base_prefix, "subnets": rows,
            "truncated": len(rows) < total, "total": total}


# --------------------------------------------------------------------------
# VLSM
# --------------------------------------------------------------------------

@dataclass
class VlsmSegment:
    name: str
    required_hosts: int

    def to_dict(self) -> dict:
        return {"name": self.name, "required_hosts": self.required_hosts}


@dataclass
class VlsmAllocation:
    name: str
    required_hosts: int
    prefix: int
    block_size: int
    network: str
    first: str
    last: str
    broadcast: str
    mask: str
    usable: int
    order: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class VlsmResult:
    base_network: str
    base_prefix: int
    base_mask: str
    base_capacity: int
    total_required: int
    used: int
    utilization_pct: float
    overflow: bool
    deficit: int
    allocations: List[VlsmAllocation]
    messages: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "base_network": self.base_network,
            "base_prefix": self.base_prefix,
            "base_mask": self.base_mask,
            "base_capacity": self.base_capacity,
            "total_required": self.total_required,
            "used": self.used,
            "utilization_pct": round(self.utilization_pct, 2),
            "overflow": self.overflow,
            "deficit": self.deficit,
            "allocations": [a.to_dict() for a in self.allocations],
            "messages": self.messages,
        }


def _next_power_of_two(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def vlsm_plan(base_ip, base_prefix: int, segments,
              raise_on_overflow: bool = True) -> VlsmResult:
    """Allocate VLSM subnets, largest demand first.

    `segments` is an iterable of items with `.name` and `.required_hosts`
    (VlsmSegment or dicts).

    When demand exceeds capacity: if `raise_on_overflow` is True a
    `PlanOverflowError` is raised; otherwise the result is returned with
    `overflow = True`, `deficit` set, and `allocations` holding only the
    segments that fit (callers decide how to present that).
    """
    if not validate_prefix(base_prefix):
        raise ValueError(f"Invalid base prefix /{base_prefix}")
    if base_prefix >= 30:
        raise ValueError("A VLSM base network must be /29 or shorter")

    norm = []
    for i, seg in enumerate(segments or []):
        if isinstance(seg, VlsmSegment):
            name, req = seg.name, seg.required_hosts
        elif isinstance(seg, dict):
            name = str(seg.get("name", ""))
            req = int(seg.get("required_hosts", seg.get("hosts", 0)))
        else:
            name = str(getattr(seg, "name", ""))
            req = int(getattr(seg, "required_hosts", 0))
        if req < 1:
            raise ValueError(f"Segment '{name or i+1}' must need at least 1 host")
        norm.append(VlsmSegment(name or f"Segment {i+1}", req))

    net = calculate_subnet(base_ip, base_prefix)
    start = ip_to_int(net["network"])
    capacity = net["total_addresses"]

    ordered = sorted(norm, key=lambda s: s.required_hosts, reverse=True)
    allocations: List[VlsmAllocation] = []
    cursor = start
    used = 0
    messages: List[str] = []
    overflow = False
    deficit = 0

    for order, seg in enumerate(ordered, start=1):
        block = _next_power_of_two(seg.required_hosts + 2)
        pfx = 32 - block.bit_length() + 1  # log2

        if cursor + block - 1 > start + capacity - 1:
            overflow = True
            deficit += block
            messages.append(
                f"Segment '{seg.name}' (needs {seg.required_hosts} hosts) does not fit — "
                f"would require a {block}-address block.")
            continue

        n = cursor
        a = VlsmAllocation(
            name=seg.name,
            required_hosts=seg.required_hosts,
            prefix=pfx,
            block_size=block,
            network=int_to_ip(n),
            first=int_to_ip(n + 1) if pfx <= 30 else int_to_ip(n),
            last=int_to_ip(n + block - 2) if pfx <= 30 else int_to_ip(n + block - 1),
            broadcast=int_to_ip(n + block - 1) if pfx <= 30 else int_to_ip(n),
            mask=prefix_to_mask(pfx),
            usable=_usable_hosts(block, pfx),
            order=order,
        )
        allocations.append(a)
        cursor += block
        used += block

    if overflow:
        total_wanted = sum(s.required_hosts + 2 for s in norm)  # ~ demand
        if raise_on_overflow:
            raise PlanOverflowError(
                "Base network capacity exceeded by VLSM demand.",
                deficit=deficit)
        # Partial result: keep what fit, surface the deficit.
        total_required = sum(a.required_hosts for a in allocations)
        used_sum = sum(a.block_size for a in allocations)
        utilization = (used_sum / capacity * 100.0) if capacity else 0.0
        allocations.sort(key=lambda x: ip_to_int(x.network))
        return VlsmResult(
            base_network=net["network"],
            base_prefix=base_prefix,
            base_mask=net["mask"],
            base_capacity=capacity,
            total_required=total_required,
            used=used_sum,
            utilization_pct=utilization,
            overflow=True,
            deficit=deficit,
            allocations=allocations,
            messages=messages,
        )

    total_required = sum(s.required_hosts for s in norm)
    utilization = (used / capacity * 100.0) if capacity else 0.0
    allocations.sort(key=lambda x: ip_to_int(x.network))

    return VlsmResult(
        base_network=net["network"],
        base_prefix=base_prefix,
        base_mask=net["mask"],
        base_capacity=capacity,
        total_required=total_required,
        used=used,
        utilization_pct=utilization,
        overflow=False,
        deficit=0,
        allocations=allocations,
        messages=messages,
    )