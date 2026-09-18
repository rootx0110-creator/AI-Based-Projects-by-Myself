"""Backend model + per-server metrics."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto

class BackendState(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    DRAINING = auto()
    DISABLED = auto()

@dataclass
class Backend:
    """Represents a single upstream backend server."""
    id: str
    host: str
    port: int
    weight: float = 1.0
    state: BackendState = BackendState.HEALTHY
    failed_checks: int = 0
    ok_checks: int = 0
    drain: bool = False
    disable: bool = False
    latency_ms: float = 0.0
    error_rate: float = 0.0
    circuit_open: bool = False
    circuit_half_open: bool = False
    last_check_ts: float = 0.0
