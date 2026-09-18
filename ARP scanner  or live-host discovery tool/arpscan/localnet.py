"""Local network auto-detection for ``--auto``.

Runs the platform's interface tooling and extracts the first usable IPv4
network. Parsers are pure so they can be unit-tested; the ``detect`` function
does the subprocess work.

Supported sources:

* Windows: ``ipconfig``
* Linux:   ``ip -o -4 addr show`` (falls back to ``ifconfig``)
* macOS:   ``ifconfig`` (``ip`` may not exist)
"""

from __future__ import annotations

import ipaddress
import re
import subprocess
import sys
from typing import List, Optional, Tuple

_IPV4_RE = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"

# Windows ipconfig: blocks headed by a column-0 line ending in ':'
_IPCONFIG_BLOCK_SPLIT = re.compile(r"^[^\s].*:$", re.M)
_IPCONFIG_IP = re.compile(r"IPv4 Address[^:]*:\s*(" + _IPV4_RE + r")")
_IPCONFIG_MASK = re.compile(r"Subnet Mask[^:]*:\s*(" + _IPV4_RE + r")")

# Linux: "inet 192.168.1.5/24 brd ..."
_IP_ADDR = re.compile(r"\binet\s+(" + _IPV4_RE + r")/(\d{1,2})")

# ifconfig (macOS/Linux fallback): "inet 192.168.1.5 netmask 0xffffff00 ..."
_IFCONFIG = re.compile(
    r"\binet\s+(" + _IPV4_RE + r")\s+netmask\s+(0x[0-9a-fA-F]{8})\b"
)

_LOOPBACK_NET = ipaddress.IPv4Network("127.0.0.0/8")


def _mask_to_prefix(mask: str) -> int:
    """Count leading-1 bits of a dotted-decimal netmask."""
    if "." in mask:
        return sum(bin(int(octet)).count("1") for octet in mask.split("."))
    return bin(int(mask)).count("1")


def _hex_mask_to_prefix(hex_mask: str) -> int:
    return bin(int(hex_mask, 16)).count("1")


def parse_ipconfig(text: str) -> List[Tuple[str, int]]:
    """Return ``(ip, prefixlen)`` pairs from Windows ``ipconfig`` output."""
    pairs: List[Tuple[str, int]] = []
    blocks = _IPCONFIG_BLOCK_SPLIT.split(text)
    for block in blocks[1:]:
        ip_m = _IPCONFIG_IP.search(block)
        mask_m = _IPCONFIG_MASK.search(block)
        if ip_m and mask_m:
            pairs.append((ip_m.group(1), _mask_to_prefix(mask_m.group(1))))
    return pairs


def parse_ip_addr(text: str) -> List[Tuple[str, int]]:
    """Return ``(ip, prefixlen)`` pairs from ``ip -o -4 addr show`` output."""
    return [
        (m.group(1), int(m.group(2)))
        for m in _IP_ADDR.finditer(text)
    ]


def parse_ifconfig(text: str) -> List[Tuple[str, int]]:
    """Return ``(ip, prefixlen)`` pairs from ``ifconfig`` output."""
    return [
        (m.group(1), _hex_mask_to_prefix(m.group(2)))
        for m in _IFCONFIG.finditer(text)
    ]


def _run(cmd: List[str]) -> Optional[str]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout


def _networks_from_pairs(pairs: List[Tuple[str, int]]) -> List[ipaddress.IPv4Network]:
    networks: List[ipaddress.IPv4Network] = []
    for ip, prefix in pairs:
        try:
            network = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
        except ValueError:
            continue
        if network.is_loopback:
            continue
        networks.append(network)
    return networks


def detect_local_networks() -> List[ipaddress.IPv4Network]:
    """Detect the machine's local IPv4 networks (first non-loopback wins per
    interface; may return several networks, e.g. with multiple NICs)."""
    if sys.platform == "win32":
        out = _run(["ipconfig"])
        if out is not None:
            return _networks_from_pairs(parse_ipconfig(out))
        return []
    if sys.platform == "darwin":
        out = _run(["ifconfig"])
        if out is not None:
            return _networks_from_pairs(parse_ifconfig(out))
        return []
    # Linux and other POSIX: prefer `ip`, fall back to `ifconfig`.
    out = _run(["ip", "-o", "-4", "addr", "show"])
    if out is not None:
        return _networks_from_pairs(parse_ip_addr(out))
    out = _run(["ifconfig"])
    if out is not None:
        return _networks_from_pairs(parse_ifconfig(out))
    return []