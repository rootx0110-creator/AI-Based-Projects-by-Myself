"""Health state machine: HEALTHY → DEGRADED → UNHEALTHY transitions."""

from src.lb.backend import Backend, BackendState

class HealthStateMachine:
    """Transitions backend states based on probe results."""

    def __init__(
        self,
        degraded_threshold: int = 3,
        unhealthy_threshold: int = 5,
        recovery_threshold: int = 3,
    ) -> None:
        self.degraded_threshold = degraded_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.recovery_threshold = recovery_threshold

    def update(self, backend: Backend) -> BackendState:
        """Return next state based on counters."""
        failed = backend.failed_checks
        ok = backend.ok_checks

        if backend.disable:
            return BackendState.DISABLED
        if backend.drain:
            active = getattr(backend, "_active_conns", 0) or 0
            if active:
                return BackendState.DRAINING
            return BackendState.DISABLED

        if failed >= self.unhealthy_threshold:
            return BackendState.UNHEALTHY
        if failed >= self.degraded_threshold:
            return BackendState.DEGRADED
        if ok >= self.recovery_threshold and backend.state != BackendState.HEALTHY:
            return BackendState.HEALTHY
        return backend.state
