"""core/stats.py — live statistics aggregation (layer L3)."""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field

from core.packets import Packet

__all__ = ["ProtocolStats"]


@dataclass
class ProtocolStats:
    """O(1)-update counters fed by every packet that enters the table."""
    by_protocol: Counter = field(default_factory=Counter)
    by_endpoint: Counter = field(default_factory=Counter)       # bytes per IP
    pkts_per_endpoint: Counter = field(default_factory=Counter)
    by_conversation: Counter = field(default_factory=Counter)   # bytes per convo
    per_second: deque = field(default_factory=lambda: deque(maxlen=120))
    _last_second: int = -1
    total_packets: int = 0
    total_bytes: int = 0

    def add(self, pkt: Packet) -> None:
        self.by_protocol[pkt.protocol] += 1
        self.by_endpoint[pkt.src_ip] += pkt.length
        self.by_endpoint[pkt.dst_ip] += pkt.length
        self.pkts_per_endpoint[pkt.src_ip] += 1
        self.pkts_per_endpoint[pkt.dst_ip] += 1
        if pkt.conversation:
            self.by_conversation[pkt.conversation] += pkt.length
        sec = int(pkt.timestamp)
        if sec != self._last_second:
            self._last_second = sec
            self.per_second.append((sec, 0))
        if self.per_second:
            s, n = self.per_second[-1]
            self.per_second[-1] = (s, n + 1)
        self.total_packets += 1
        self.total_bytes += pkt.length

    def reset(self) -> None:
        self.by_protocol.clear()
        self.by_endpoint.clear()
        self.pkts_per_endpoint.clear()
        self.by_conversation.clear()
        self.per_second.clear()
        self._last_second = -1
        self.total_packets = self.total_bytes = 0

    # ------------------------------------------------------------ helpers
    def top_talkers(self, n: int = 10) -> list[tuple[str, int, int]]:
        """[(ip, packets, bytes)] sorted by bytes desc."""
        return [(ip, self.pkts_per_endpoint[ip], b)
                for ip, b in self.by_endpoint.most_common(n)]

    def top_conversations(self, n: int = 10) -> list[tuple[str, int]]:
        return self.by_conversation.most_common(n)

    def protocol_counts(self) -> list[tuple[str, int]]:
        return self.by_protocol.most_common()

    def pps(self) -> float:
        """Packets-per-second averaged over the recent window."""
        if len(self.per_second) < 2:
            return 0.0
        total = sum(n for _s, n in list(self.per_second)[1:-1])
        return total / max(1, len(self.per_second) - 2)

    def summary(self) -> dict:
        return {
            "total_packets": self.total_packets,
            "total_bytes": self.total_bytes,
            "by_protocol": dict(self.by_protocol),
            "top_talkers": [
                {"ip": ip, "packets": p, "bytes": b}
                for ip, p, b in self.top_talkers(10)
            ],
            "top_conversations": [
                {"conversation": c, "bytes": b}
                for c, b in self.top_conversations(10)
            ],
        }
