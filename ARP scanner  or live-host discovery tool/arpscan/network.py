"""Target expansion: turn CLI target strings into concrete IPv4 addresses.

Accepted forms (comma or whitespace separated):

* CIDR block:      ``192.168.1.0/24``
* IP range:        ``192.168.1.10-192.168.1.50`` or ``192.168.1.10-50``
* Single address:  ``192.168.1.1``
* Mixed:           ``192.168.1.0/28, 10.0.0.5``
"""

from __future__ import annotations

import ipaddress
import re
from typing import List, Sequence

_RANGE_RE = re.compile(
    r"^\s*(\d{1,3}(?:\.\d{1,3}){3})\s*-\s*(\d{1,3}(?:\.\d{1,3}){3}|[0-9]{1,3})\s*$"
)


def expand_target(target: str) -> List[ipaddress.IPv4Address]:
    """Expand a single target string into a list of IPv4 addresses."""
    target = target.strip()
    if not target:
        return []

    # CIDR block, e.g. "192.168.1.0/24"
    if "/" in target:
        network = ipaddress.IPv4Network(target, strict=False)
        return list(network.hosts())

    # Range, e.g. "192.168.1.10-192.168.1.50" or "192.168.1.10-50"
    m = _RANGE_RE.match(target)
    if m:
        start_ip = ipaddress.IPv4Address(m.group(1))
        end_raw = m.group(2)
        if "." in end_raw:
            end_ip = ipaddress.IPv4Address(end_raw)
        else:
            # Last octet shorthand: start network portion + end octet
            start_octets = str(start_ip).split(".")
            end_ip = ipaddress.IPv4Address(".".join(start_octets[:3] + [end_raw]))
        if end_ip < start_ip:
            raise ValueError(f"range end {end_ip} is before start {start_ip}")
        # Cap the range size to avoid accidentally expanding /0-style monsters.
        size = int(end_ip) - int(start_ip) + 1
        if size > 65536:
            raise ValueError(
                f"range {target} expands to {size} addresses (max 65536)"
            )
        return [ipaddress.IPv4Address(int(start_ip) + i) for i in range(size)]

    # Single address
    return [ipaddress.IPv4Address(target)]


def expand_targets(targets: Sequence[str]) -> List[ipaddress.IPv4Address]:
    """Expand many target strings, preserving order and de-duplicating."""
    seen = set()
    out: List[ipaddress.IPv4Address] = []
    for raw in targets:
        for part in re.split(r"[,\s]+", raw):
            for addr in expand_target(part):
                if addr not in seen:
                    seen.add(addr)
                    out.append(addr)
    return out