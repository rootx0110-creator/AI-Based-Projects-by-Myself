"""Pure parsers for OS ARP-table text output.

These functions are deliberately free of I/O and platform logic so they can be
unit-tested with sample text. The ``system`` backend collects the raw output
(e.g. ``arp -a`` / ``ip neigh show``) and hands it to these parsers.

Supported sources:

* ``windows``: ``arp -a``  (dash-separated MACs, header rows to skip)
* ``linux-ip``: ``ip neigh show``  (colon-separated MACs)
* ``posix-arp``: ``arp -a`` as emitted on Linux/macOS (``? (ip) at mac ...``)
"""

from __future__ import annotations

import re
from typing import Dict

IP_RE = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
MAC_RE = r"[0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5}"

# "  192.168.1.1           a4-2b-b0-93-1c-2d     dynamic"
_WINDOWS_RE = re.compile(
    rf"^\s*({IP_RE})\s+({MAC_RE})\s+\S+", re.IGNORECASE | re.MULTILINE
)
# "192.168.1.1 dev eth0 lladdr a4:2b:b0:93:1c:2d REACHABLE"
_LINUX_IP_RE = re.compile(
    rf"^\s*({IP_RE})\s+dev\s+\S+\s+lladdr\s+({MAC_RE})\b",
    re.IGNORECASE | re.MULTILINE,
)
# "? (192.168.1.1) at a4:2b:b0:93:1c:2d on en0 ifscope [ethernet]"
_POSIX_ARP_RE = re.compile(
    rf"^\s*\S+\s+\(({IP_RE})\)\s+at\s+({MAC_RE})\b",
    re.IGNORECASE | re.MULTILINE,
)

# MACs that are not a real host: broadcast, all-zeros, multicast.
_BOGUS_MACS = {"ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00"}
_MULTICAST_MAC_PREFIX = "01:00:5e"


def normalize_mac(mac: str) -> str:
    """Return a canonical lowercase ``aa:bb:cc:dd:ee:ff`` MAC string."""
    digits = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
    return ":".join(digits[i : i + 2] for i in range(0, 12, 2))


def _keep(ip: str, mac: str) -> bool:
    mac_norm = normalize_mac(mac)
    if mac_norm in _BOGUS_MACS or mac_norm.startswith(_MULTICAST_MAC_PREFIX):
        return False
    # Skip multicast/reserved IPv4 ranges that some OSes list.
    first_octet = int(ip.split(".")[0])
    if 224 <= first_octet <= 239:
        return False
    return True


def parse_arp_output(text: str, family: str) -> Dict[str, str]:
    """Parse raw ARP-table text into ``{ip: mac}`` (canonical MAC form)."""
    if family == "windows":
        regex = _WINDOWS_RE
    elif family == "linux-ip":
        regex = _LINUX_IP_RE
    elif family == "posix-arp":
        regex = _POSIX_ARP_RE
    else:
        raise ValueError(f"unknown ARP output family: {family!r}")

    result: Dict[str, str] = {}
    for match in regex.finditer(text):
        ip, mac = match.group(1), match.group(2)
        if _keep(ip, mac):
            result[ip] = normalize_mac(mac)
    return result