"""Passive health checker: observe 5xx rate, timeouts, connection errors."""

from collections import deque
from src.lb.backend import Backend

class PassiveChecker:
    """Track recent responses per backend to infer degradation."""

    def __init__(self, window_size: int = 100, error_threshold: float = 0.05, latency_warn_ms: float = 500.0) -> None:
        self.window_size = window_size
        self.error_threshold = error_threshold
        self.latency_warn_ms = latency_warn_ms
        self._recent: dict[str, deque] = {}

    def record(self, backend_id: str, ok: bool, latency_ms: float) -> None:
        if backend_id not in self._recent:
            self._recent[backend_id] = deque(maxlen=self.window_size)
        self._recent[backend_id].append((ok, latency_ms))

    def get_error_rate(self, backend_id: str) -> float:
        q = self._recent.get(backend_id)
        if not q or len(q) == 0:
            return 0.0
        errors = sum(1 for ok, _ in q if not ok)
        return errors / len(q)

    def get_avg_latency(self, backend_id: str) -> float:
        q = self._recent.get(backend_id)
        if not q or len(q) == 0:
            return 0.0
        return sum(lat for _, lat in q) / len(q)
