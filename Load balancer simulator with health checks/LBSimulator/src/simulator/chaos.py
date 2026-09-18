"""Chaos engineering panel — fault injection at runtime."""

import asyncio
import random as _random
from src.lb.backend import Backend, BackendState

class ChaosEngine:
    """Inject faults into backends on demand or by schedule."""

    def __init__(self) -> None:
        self._actions: list[dict] = []
        self._rng = _random.Random()

    def kill(self, backend: Backend, duration_s: float = 30.0) -> dict:
        """Simulate backend crash (make it fail active checks)."""
        action = {"type": "kill", "backend": backend.id, "duration": duration_s}
        self._actions.append(action)
        backend.disable = True
        return action

    def add_latency(self, backend: Backend, ms: float) -> dict:
        backend.latency_ms = ms
        return {"type": "latency", "backend": backend.id, "ms": ms}

    def drop_packets(self, backend: Backend, fraction: float = 0.2) -> dict:
        return {"type": "drop", "backend": backend.id, "fraction": fraction}

    def return_500s(self, backend: Backend, fraction: float = 1.0) -> dict:
        backend.error_rate = fraction
        return {"type": "500", "backend": backend.id, "fraction": fraction}

    def random_chaos(self, backends, interval_s: float = 8.0, duration_s: float = 15.0) -> asyncio.Task:
        """Periodically pick random fault injections."""

        async def _loop():
            while True:
                await asyncio.sleep(interval_s)
                if backends:
                    target = self._rng.choice(backends)
                    action = self._rng.choice(["kill", "add_latency", "return_500s"])
                    if action == "kill":
                        self.kill(target, duration_s)
                    elif action == "add_latency":
                        self.add_latency(target, self._rng.randint(200, 1500))
                    elif action == "return_500s":
                        self.return_500s(target, self._rng.uniform(0.3, 1.0))
        return asyncio.create_task(_loop())
