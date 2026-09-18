"""Per-interface traffic sampling built on psutil net_io_counters.

Every tick: read counters, diff against the previous tick, convert to
bytes/sec and push into the ring buffer. A PDH fallback rescues interfaces
whose psutil counters appear frozen (seen with some VPN adapters).
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

import psutil

from utils import platform_win
from capture.ring_buffer import RingBuffer

log = logging.getLogger(__name__)


@dataclass
class InterfaceSample:
    """One per-interface throughput sample, in bytes/sec."""

    name: str
    down_bps: float = 0.0  # bytes/sec received
    up_bps: float = 0.0  # bytes/sec sent
    link_bps: int = 0  # link speed bits/sec, 0 unknown
    is_up: bool = True

    @property
    def down_mbps(self) -> float:
        """Download speed in megabits/sec."""
        return self.down_bps * 8.0 / 1e6

    @property
    def up_mbps(self) -> float:
        """Upload speed in megabits/sec."""
        return self.up_bps * 8.0 / 1e6


@dataclass
class Sample:
    """An aggregate sample across all non-excluded interfaces."""

    ts: float
    total_down: float = 0.0  # bytes/sec
    total_up: float = 0.0  # bytes/sec
    per_iface: dict[str, InterfaceSample] = field(default_factory=dict)

    @property
    def total_down_mbps(self) -> float:
        """Aggregate download in megabits/sec."""
        return self.total_down * 8.0 / 1e6

    @property
    def total_up_mbps(self) -> float:
        """Aggregate upload in megabits/sec."""
        return self.total_up * 8.0 / 1e6


class InterfaceSampler:
    """Polls psutil counters on a background thread and emits Sample objects.

    Callbacks run on the sampler thread — GUI consumers must marshal results
    onto the Qt main thread themselves (signals do this automatically).
    """

    def __init__(self, interval_ms: int = 500, excluded: list[str] | None = None) -> None:
        self.interval = max(0.05, interval_ms / 1000.0)
        self.excluded = set(excluded or [])
        self._prev: dict[str, tuple[int, int, float]] = {}  # name -> (sent, recv, ts)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.buffer = RingBuffer.create(capacity=8192)
        self.on_sample = None  # Optional[Callable[[Sample], None]]
        self._last_sample: Sample | None = None

    # -- lifecycle ------------------------------------------------------

    def start(self) -> None:
        """Start the background sampling thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="sampler", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Stop the sampling thread and wait for it to exit."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    # -- sampling -------------------------------------------------------

    def _run(self) -> None:
        """Thread loop: sample, notify, sleep until next tick."""
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                sample = self.sample_once()
            except Exception as exc:
                log.exception("sampler tick failed: %s", exc)
                sample = None
            if sample is not None and self.on_sample:
                try:
                    self.on_sample(sample)
                except Exception:
                    log.exception("sampler callback failed")
            delay = max(0.01, self.interval - (time.monotonic() - started))
            self._stop.wait(delay)

    def sample_once(self) -> Sample | None:
        """Take exactly one sample now (also used by tests and demo mode)."""
        try:
            raw = psutil.net_io_counters(pernic=True, nowrap=True)
        except Exception as exc:
            log.error("psutil.net_io_counters failed: %s", exc)
            return None

        now = time.time()
        sample = Sample(ts=now)
        with self._lock:
            for name, counters in raw.items():
                if name in self.excluded or _is_loopback(name):
                    continue
                prev = self._prev.get(name)
                self._prev[name] = (counters.bytes_sent, counters.bytes_recv, now)
                if prev is None or now <= prev[2]:
                    down = up = 0.0  # first tick: no delta yet
                else:
                    dt = now - prev[2]
                    down = max(0, counters.bytes_recv - prev[1]) / dt
                    up = max(0, counters.bytes_sent - prev[0]) / dt
                ifdown = psutil.net_if_stats()
                is_up = ifdown.get(name).isup if name in ifdown else True
                link = platform_win.link_speed_bps(name) if platform_win.IS_WINDOWS else 0
                if link == 0:
                    link = getattr(counters, "speed", 0) or 0
                iface = InterfaceSample(
                    name=name,
                    down_bps=down,
                    up_bps=up,
                    link_bps=int(link),
                    is_up=bool(is_up),
                )
                sample.per_iface[name] = iface
                sample.total_down += down
                sample.total_up += up
                self.buffer.append("download", now, down)
                self.buffer.append("upload", now, up)
                self.buffer.append(f"iface:{name}", now, down + up)

        # PDH rescue for frozen psutil counters (rare, VPN adapters).
        if sample.total_down == 0 and sample.total_up == 0 and platform_win.IS_WINDOWS:
            for name in list(sample.per_iface):
                pdh = platform_win.pdh_bytes_per_sec(name)
                if pdh and (pdh[0] or pdh[1]):
                    iface = sample.per_iface[name]
                    iface.up_bps, iface.down_bps = float(pdh[0]), float(pdh[1])
                    sample.total_down += iface.down_bps
                    sample.total_up += iface.up_bps
                    log.debug("PDH rescue applied for %s", name)

        self._last_sample = sample
        return sample

    @property
    def last_sample(self) -> Sample | None:
        """The most recent Sample, or None before the first tick."""
        return self._last_sample


def _is_loopback(name: str) -> bool:
    """Heuristic: does this interface name look like loopback?"""
    lowered = name.lower()
    return "loopback" in lowered or lowered in ("lo", "lo0")


def list_interfaces() -> list[dict[str, object]]:
    """Enumerate interfaces with up/down state and link speed for the GUI."""
    out: list[dict[str, object]] = []
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
    except Exception as exc:
        log.error("interface enumeration failed: %s", exc)
        return out
    for name, st in stats.items():
        if _is_loopback(name):
            continue
        ips: list[str] = []
        for addr in addrs.get(name, []):
            ip = getattr(addr, "address", "")
            if ip and ":" not in str(ip):
                ips.append(str(ip))
        link = platform_win.link_speed_bps(name) if platform_win.IS_WINDOWS else 0
        out.append(
            {
                "name": name,
                "is_up": bool(st.isup),
                "speed_mbps": (link / 1e6) if link else 0.0,
                "mtu": int(getattr(st, "mtu", 0) or 0),
                "ips": ips,
            }
        )
    return out
