"""Scapy-based backend: sends ARP requests and reads the replies.

This is the most direct and reliable approach. It sends one broadcast ARP
request per target and matches replies by sender address.

Requirements:
* ``scapy`` installed (``pip install arpscan[scapy]``)
* Raw-packet privileges: root on Linux/macOS, Administrator + Npcap on
  Windows. Without them scapy raises at send time; the scanner catches that
  and can fall back to the ``system`` backend.
"""

from __future__ import annotations

from typing import List

from ..models import Host
from .base import BackendError, ScannerBackend


class ScapyBackend(ScannerBackend):
    name = "scapy"

    def __init__(self) -> None:
        # Import lazily so the package can be imported without scapy.
        try:
            from scapy.all import ARP, Ether, srp  # noqa: F401
        except ImportError as exc:  # pragma: no cover - env dependent
            raise BackendError(
                "scapy is not installed; run 'pip install arpscan[scapy]' "
                "or use the 'system' backend"
            ) from exc
        self._arp = ARP
        self._ether = Ether
        self._srp = srp

    def scan(
        self,
        targets: List[str],
        timeout: float = 2.0,
        retries: int = 1,
    ) -> List[Host]:
        hosts: List[Host] = []
        try:
            # Send one broadcast ARP request per target in a single srp call:
            # srp waits ``timeout`` once for all replies, instead of waiting
            # the full timeout per IP (which would make a /24 take ~254x
            # longer).
            packets = [
                self._ether(dst="ff:ff:ff:ff:ff:ff") / self._arp(pdst=ip)
                for ip in targets
            ]
            # ``retry`` is the stable scapy kwarg for re-sending unanswered
            # probes (older docs called it ``retries``).
            answered, _ = self._srp(
                packets, timeout=timeout, retry=retries, verbose=False
            )
            for _sent, received in answered:
                hosts.append(
                    Host(ip=received.psrc, mac=received.hwsrc.lower())
                )
        except PermissionError as exc:  # pragma: no cover - OS dependent
            raise BackendError(
                "scapy needs raw-packet privileges: run as root/admin "
                "(and install Npcap on Windows)"
            ) from exc
        except Exception as exc:  # pragma: no cover - OS/version dependent
            # Any scapy failure at runtime (missing Npcap, driver issues,
            # API changes) means this backend cannot run; let the CLI's auto
            # path fall back to the system backend.
            raise BackendError(f"scapy backend failed: {exc}") from exc
        return hosts