"""Optional deep-packet sniffer (scapy/pcap), disabled by default.

psutil's counter approach cannot attribute traffic to protocols or remote
hosts without elevated capture. This module offers an optional scapy-based
backend that is only started when the user enables it in Settings and the
process runs elevated. All methods fail soft so the app works without scapy.
"""
from __future__ import annotations

import logging
import threading

log = logging.getLogger(__name__)

try:  # optional dependency
    from scapy.all import sniff as _scapy_sniff  # type: ignore[import-not-found]

    HAS_SCAPY = True
except Exception:  # ImportError or Npcap missing
    HAS_SCAPY = False


class Sniffer:
    """Optional scapy capture backend for protocol/host attribution.

    Counting packets (not bytes) is a deliberate simplification: the PS1
    marks this as optional and pkt lengths are available via pktlen but the
    demo scope keeps the engine minimal.
    """

    def __init__(self) -> None:
        self.protocol_counts: dict[str, int] = {"TCP": 0, "UDP": 0, "ICMP": 0, "other": 0}
        self.host_counts: dict[str, int] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        """True when scapy + Npcap are installed."""
        return HAS_SCAPY

    def start(self, iface: str | None = None) -> bool:
        """Start capture on a background thread; False when unavailable."""
        if not HAS_SCAPY or self._thread:
            return False
        self._stop.clear()

        def _run() -> None:
            """Blocking scapy loop."""
            try:
                _scapy_sniff(
                    iface=iface,
                    filter="ip",
                    prn=self._on_pkt,
                    store=False,
                    stop_filter=lambda _p: self._stop.is_set(),
                )
            except Exception as exc:
                log.warning("sniffer stopped: %s", exc)

        self._thread = threading.Thread(target=_run, name="sniffer", daemon=True)
        self._thread.start()
        return True

    def _on_pkt(self, pkt: object) -> None:
        """Accumulate protocol and host counters for one packet."""
        try:
            proto = "other"
            if pkt.haslayer("TCP"):
                proto = "TCP"
            elif pkt.haslayer("UDP"):
                proto = "UDP"
            elif pkt.haslayer("ICMP"):
                proto = "ICMP"
            self.protocol_counts[proto] = self.protocol_counts.get(proto, 0) + 1
            ip_layer = pkt.getlayer("IP")
            if ip_layer is not None:
                src = getattr(ip_layer, "src", "")
                dst = getattr(ip_layer, "dst", "")
                for h in (src, dst):
                    if h and not h.startswith("127."):
                        self.host_counts[h] = self.host_counts.get(h, 0) + 1
        except Exception:
            pass

    def stop(self) -> None:
        """Stop capture."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None

    def reset(self) -> None:
        """Zero all counters."""
        self.protocol_counts = {"TCP": 0, "UDP": 0, "ICMP": 0, "other": 0}
        self.host_counts = {}
