"""Power of Two Choices (P2C) algorithm.

Probe two random backends, pick the one with fewer "score" (latency + jitter).
"""

import random as _random

class PowerOfTwoChoices:
    """Pick two random backends, choose the better one."""

    name = "Power of Two Choices (P2C)"

    def __init__(self) -> None:
        self._rng = _random.Random()

    def _score(self, backend) -> float:
        lat = getattr(backend, "latency_ms", 0.0) or 0.0
        err = getattr(backend, "error_rate", 0.0) or 0.0
        return lat * (1 + 5 * err)

    def pick(self, request, candidates, metrics):
        if not candidates:
            raise RuntimeError("empty candidate set")
        a, b = _random.sample(candidates, min(2, len(candidates)))
        return a if self._score(a) <= self._score(b) else b

    def on_response(self, backend, rtt_ms, ok):
        backend.latency_ms = rtt_ms

    def snapshot(self):
        return {}
