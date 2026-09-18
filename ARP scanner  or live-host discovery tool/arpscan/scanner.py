"""Scanner orchestrator: expands targets, runs a backend, normalizes results.

The orchestrator owns everything that is testable without a live network:
target expansion, de-duplication, IP-sorted ordering, and vendor enrichment.
Backends stay thin I/O wrappers around the probe itself.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .backends import BackendError, ScapyBackend, ScannerBackend, SystemBackend
from .models import Host
from .network import expand_targets
from .vendor import lookup_vendor


def _ip_sort_key(host: Host):
    return tuple(int(octet) for octet in host.ip.split("."))


class Scanner:
    """High-level scan entry point."""

    def __init__(
        self,
        backend: ScannerBackend,
        vendor_db: Optional[Dict[str, str]] = None,
        do_vendor: bool = True,
    ) -> None:
        self.backend = backend
        self.vendor_db = vendor_db
        self.do_vendor = do_vendor

    def scan(
        self,
        targets: Sequence[str],
        timeout: float = 2.0,
        retries: int = 1,
    ) -> List[Host]:
        """Scan the given targets and return live hosts, sorted by IP."""
        ips = expand_targets(targets)
        if not ips:
            return []
        raw = self.backend.scan(
            [str(ip) for ip in ips], timeout=timeout, retries=retries
        )
        hosts = self._normalize(raw)
        if self.do_vendor:
            hosts = self._enrich_vendors(hosts)
        return hosts

    @staticmethod
    def _normalize(raw: List[Host]) -> List[Host]:
        """De-duplicate by IP, keep the first MAC seen, sort by IP."""
        seen: Dict[str, Host] = {}
        for host in raw:
            seen.setdefault(host.ip, host)
        return sorted(seen.values(), key=_ip_sort_key)

    def _enrich_vendors(self, hosts: List[Host]) -> List[Host]:
        return [
            Host(
                ip=host.ip,
                mac=host.mac,
                vendor=lookup_vendor(host.mac, self.vendor_db),
            )
            for host in hosts
        ]


def select_backend(name: str) -> ScannerBackend:
    """Instantiate the requested backend.

    ``auto`` prefers scapy (most reliable ARP probe) and falls back to the
    system backend when scapy is missing. Note that a permission failure at
    scan time (e.g. non-root Linux) is only caught by the CLI when it chose
    ``auto``, since construction alone cannot detect it.
    """
    if name == "scapy":
        return ScapyBackend()
    if name == "system":
        return SystemBackend()
    try:
        return ScapyBackend()
    except BackendError:
        return SystemBackend()