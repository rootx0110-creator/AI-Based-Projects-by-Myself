"""Request routing — picks a backend and explains why."""

from typing import Optional
from src.lb.backend import Backend
from src.lb.pool import Pool
from src.lb.algorithms import create_algorithm, list_algorithms

class RequestContext:
    """Context for a single proxied request."""

    def __init__(self, client_ip: str = "127.0.0.1", path: str = "/") -> None:
        self.client_ip = client_ip
        self.path = path

class MetricsView:
    """Read-only view of current metrics (for algorithm snapshot)."""

    def __init__(self, rps: float = 0.0, active_conns: int = 0, error_pct: float = 0.0) -> None:
        self.rps = rps
        self.active_conns = active_conns
        self.error_pct = error_pct

class Router:
    """Router: selects a backend using the active algorithm and emits rationale."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool
        self._algorithm_name = "Round Robin"
        self._algorithm = create_algorithm(self._algorithm_name)

    def set_algorithm(self, name: str) -> None:
        if name not in list_algorithms():
            raise ValueError(f"Unknown algorithm: {name}")
        self._algorithm_name = name
        self._algorithm = create_algorithm(name)

    def algorithm_name(self) -> str:
        return self._algorithm_name

    def pick(self, ctx: RequestContext, metrics: MetricsView) -> tuple[Backend, str]:
        """Return (backend, rationale_string)."""
        candidates = self._pool.active()
        if not candidates:
            raise RuntimeError("No eligible backends in pool")
        try:
            chosen = self._algorithm.pick(ctx, candidates, metrics)
        except RuntimeError:
            raise RuntimeError("Algorithm picked no backend")
        rationale = self._explain(chosen, ctx)
        return chosen, rationale

    def _explain(self, backend: Backend, ctx: RequestContext) -> str:
        algo = self._algorithm_name
        methods = {
            "Round Robin": f"Round Robin: backend #{self._algorithm.snapshot().get('index', 0)} in cycle",
            "Weighted Round Robin": f"Weighted RR: weight={backend.weight} gives higher share",
            "Least Connections": f"Least Connections: {getattr(backend, '_active_conns', 0)} active",
            "Least Response Time": f"Least RT: latency≈{backend.latency_ms:.1f}ms",
            "IP Hash (Sticky)": "IP Hash: same IP always routes here (sticky)",
            "Random": "Random: uniformly chosen",
            "Power of Two Choices (P2C)": "P2C: best of two random probes",
            "Consistent Hashing": "Consistent Hash: ring lookup",
        }
        return f"{methods.get(algo, algo)} → backend '{backend.id}'"

    def on_response(self, backend: Backend, rtt_ms: float, ok: bool) -> None:
        try:
            self._algorithm.on_response(backend, rtt_ms, ok)
        except Exception as e:
            pass
