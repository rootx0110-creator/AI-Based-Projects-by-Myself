"""Simulated C2 agent (beacon client).

A daemon thread that emits HTTP beacons toward the local :class:`C2Server`
using the fingerprint of the selected profile (User-Agent, method, URI).
Interval and jitter are applied the way commodity beacons do: the client
sleeps for an interval drawn from ``interval * (1 ± jitter)``.

Beacone latency (round-trip) is measured and stored on the event so the
detection layer can reason about connection patterns.

Nothing here is malicious in itself; every request targets the loopback
interface and carries no payload beyond the synthetic tasking response.
"""

from __future__ import annotations

import random
import statistics
import threading
import time

import requests

from .presets import C2Profile, BEACONS
from .server import C2Server


class BeaconClient:
    """Threaded agent simulator."""

    def __init__(
        self,
        server: "C2Server",
        profile: C2Profile,
        interval: int,
        jitter: float,
        duration: int,
    ):
        self.server = server
        self.profile = profile
        self.interval = max(1, int(interval))
        self.jitter = max(0.0, float(jitter))
        self.duration = max(1, int(duration))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.sent = 0
        self.latencies: list[float] = []

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _next_delay(self) -> float:
        base = float(self.interval)
        jitter = (random.random() * 2.0 - 1.0) * (self.jitter / 100.0) * base
        return max(0.4, base + jitter)

    def _beacon(self) -> None:
        path = random.choice(self.profile.uri_paths)
        method = random.choice(self.profile.methods)
        url = f"http://{self.server.host}:{self.server.port}{path}"
        session = requests.Session()
        headers = {
            "User-Agent": self.profile.user_agent,
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        try:
            started = time.perf_counter()
            if method == "POST":
                session.post(url, data=b"\x00" * 64, headers=headers, timeout=5.0)
            else:
                session.get(url, headers=headers, timeout=5.0)
            latency = (time.perf_counter() - started) * 1000.0
            self.latencies.append(latency)
            # The listener stores each event before answering; annotate the
            # in-store copy (the GUI later drains the same objects).
            snapshot = self.server.snapshot()
            if snapshot:
                snapshot[-1].latency_ms = round(latency, 2)
            self.sent += 1
        except requests.RequestException:
            pass

    def run_loop(self) -> None:
        deadline = time.monotonic() + self.duration
        while not self._stop.is_set():
            if self.server is None or not self.server.running:
                break
            self._beacon()
            if time.monotonic() >= deadline:
                break
            self._stop.wait(self._next_delay())

    def start(self) -> None:
        if self.running:
            return
        self.sent = 0
        self.latencies.clear()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self.run_loop, name="beacon-agent", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=8.0)
        self._thread = None

    def latency_stats(self) -> dict:
        if not self.latencies:
            return {"n": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "p95": 0.0}
        data = sorted(self.latencies)
        p95 = statistics.quantiles(data, n=20)[-1] if len(data) >= 20 else data[-1]
        return {
            "n": len(data),
            "min": round(data[0], 2),
            "max": round(data[-1], 2),
            "mean": round(statistics.mean(data), 2),
            "p95": round(p95, 2),
        }