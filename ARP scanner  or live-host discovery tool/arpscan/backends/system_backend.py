"""System backend: ping sweep + read the OS ARP table.

This backend has zero third-party dependencies. Strategy:

1. Ping every target concurrently (this causes the OS to populate its ARP
   cache with MAC addresses of hosts that answer).
2. Dump the OS ARP table (``arp -a`` on Windows/macOS, ``ip neigh show`` on
   Linux).
3. Parse it and keep only entries whose IP was in our target list.

Caveats:
* Only sees hosts in the local L2 segment (ARP is not routable).
* Depends on the OS ARP cache, which expires dynamic entries (~2 min on
  Windows). Hosts that drop their reply are only detected if they answer ping.
* Some OSes firewalled against ICMP may still answer ARP (which is why the
  scapy backend is more complete); conversely a host answering ping but not
  ARP is invisible here.
"""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from ..arp_parse import parse_arp_output
from ..models import Host
from .base import BackendError, ScannerBackend

_MAX_CONCURRENT_PINGS = 64

_PING_SPECS = {
    # command args are appended with the target IP
    "win32": (["ping", "-n", "1", "-w"], "ms"),   # -w timeout in ms
    "linux": (["ping", "-c", "1", "-W"], "s"),    # -W timeout in seconds
    "darwin": (["ping", "-c", "1", "-W"], "ms"),  # -W timeout in ms on macOS
}


def _ping_one(ip: str, timeout: float) -> bool:
    spec = _PING_SPECS.get(sys.platform, _PING_SPECS["linux"])
    args, unit = spec
    if unit == "ms":
        wait = str(int(max(timeout, 0.1) * 1000))
    else:
        wait = str(int(max(timeout, 1)))
    cmd = args + [wait, ip]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def ping_sweep(targets: List[str], timeout: float) -> None:
    """Ping all targets concurrently to warm the OS ARP cache."""
    with ThreadPoolExecutor(max_workers=_MAX_CONCURRENT_PINGS) as pool:
        list(pool.map(lambda ip: _ping_one(ip, timeout), targets))


def read_arp_table() -> Dict[str, str]:
    """Return ``{ip: mac}`` from the OS ARP table, in canonical MAC form."""
    if sys.platform == "win32":
        out = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, timeout=10, check=False
        )
        return parse_arp_output(out.stdout or "", family="windows")

    if sys.platform == "darwin":
        out = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, timeout=10, check=False
        )
        return parse_arp_output(out.stdout or "", family="posix-arp")

    # Linux: `ip neigh` is the modern, reliable source.
    try:
        out = subprocess.run(
            ["ip", "neigh", "show"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if out.returncode == 0:
            return parse_arp_output(out.stdout or "", family="linux-ip")
    except OSError:
        pass
    out = subprocess.run(
        ["arp", "-a"], capture_output=True, text=True, timeout=10, check=False
    )
    return parse_arp_output(out.stdout or "", family="posix-arp")


class SystemBackend(ScannerBackend):
    name = "system"

    def scan(
        self,
        targets: List[str],
        timeout: float = 2.0,
        retries: int = 1,
    ) -> List[Host]:
        if not targets:
            return []
        target_set = set(targets)
        try:
            ping_sweep(targets, timeout)
            table = read_arp_table()
        except OSError as exc:
            raise BackendError(
                "system backend failed (is 'ping'/'arp'/'ip' available?): "
                f"{exc}"
            ) from exc
        return [
            Host(ip=ip, mac=mac)
            for ip, mac in table.items()
            if ip in target_set
        ]