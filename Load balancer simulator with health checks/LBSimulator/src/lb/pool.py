"""Backend pool registry — holds and manages the set of backends."""

from typing import Dict, List, Optional
from src.lb.backend import Backend, BackendState

class Pool:
    """Registry of backends with fast lookup and state filtering."""

    def __init__(self) -> None:
        self._backends: Dict[str, Backend] = {}

    def add(self, backend: Backend) -> None:
        self._backends[backend.id] = backend

    def remove(self, backend_id: str) -> Optional[Backend]:
        return self._backends.pop(backend_id, None)

    def get(self, backend_id: str) -> Optional[Backend]:
        return self._backends.get(backend_id)

    def list(self) -> List[Backend]:
        return list(self._backends.values())

    def active(self) -> List[Backend]:
        """Backends eligible for routing (HEALTHY/DEGRADED)."""
        return [
            b for b in self._backends.values()
            if b.state in (BackendState.HEALTHY, BackendState.DEGRADED)
            and not b.drain and not b.disable
        ]

    def healthy_count(self) -> int:
        return sum(1 for b in self._backends.values() if b.state == BackendState.HEALTHY)

    def total_count(self) -> int:
        return len(self._backends)
