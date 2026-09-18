"""Circuit breaker per backend (closed / open / half-open)."""

from enum import Enum, auto
from src.lb.backend import Backend

class CBState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()

class CircuitBreaker:
    """Per-backend circuit breaker with rolling window."""

    def __init__(
        self,
        failure_threshold: float = 0.5,
        success_threshold: int = 3,
        cooldown_ms: float = 5000.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.cooldown_ms = cooldown_ms
        self._state: dict[str, CBState] = {}
        self._failures: dict[str, int] = {}
        self._successes: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def on_request(self, backend: Backend) -> bool:
        """Return True if request is allowed through."""
        bid = backend.id
        state = self._state.get(bid, CBState.CLOSED)
        if state == CBState.OPEN:
            import time
            if time.monotonic() - self._opened_at.get(bid, 0) > self.cooldown_ms:
                self._state[bid] = CBState.HALF_OPEN
                return True
            return False
        return True

    def on_response(self, backend: Backend, ok: bool) -> None:
        bid = backend.id
        if not ok:
            self._failures[bid] = self._failures.get(bid, 0) + 1
            if self._failures[bid] > self.failure_threshold * 10:
                self._state[bid] = CBState.OPEN
                self._opened_at[bid] = __import__("time").monotonic()
        else:
            self._successes[bid] = self._successes.get(bid, 0) + 1
            if self._state.get(bid) == CBState.HALF_OPEN and self._successes[bid] >= self.success_threshold:
                self._state[bid] = CBState.CLOSED
                self._failures[bid] = 0
                self._successes[bid] = 0
