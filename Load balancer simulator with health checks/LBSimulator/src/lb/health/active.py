"""Active health checker: periodic GET /health probes."""

from typing import Optional
from src.core.clock import Clock
from ..backend import Backend, BackendState

class ActiveChecker:
    """Periodically probe backends' /health endpoint."""

    def __init__(
        self,
        interval_s: float = 5.0,
        timeout_s: float = 2.0,
        healthy_threshold: int = 2,
        unhealthy_threshold: int = 3,
    ) -> None:
        self.interval_s = interval_s
        self.timeout_s = timeout_s
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self._last_probe: float = 0.0

    def should_probe(self, now: float = None) -> bool:
        if now is None:
            now = Clock.monotonic()
        return (now - self._last_probe) >= self.interval_s

    def record_probe(self, backend: Backend, success: bool, latency_ms: float = 0.0) -> None:
        backend.last_check_ts = Clock.wall()
        if success:
            backend.ok_checks += 1
            backend.failed_checks = max(0, backend.failed_checks - 1)
        else:
            backend.failed_checks += 1
            backend.ok_checks = max(0, backend.ok_checks - 1)
