"""Load balancing algorithms — registry + factory."""

from src.lb.algorithms.base import Algorithm
from src.lb.algorithms.round_robin import RoundRobin
from src.lb.algorithms.weighted_rr import WeightedRoundRobin
from src.lb.algorithms.least_conn import LeastConnections
from src.lb.algorithms.least_rt import LeastResponseTime
from src.lb.algorithms.ip_hash import IpHash
from src.lb.algorithms.random import RandomChoice
from src.lb.algorithms.p2c import PowerOfTwoChoices
from src.lb.algorithms.consistent_hash import ConsistentHashRing

_REGISTRY: dict[str, type] = {
    "Round Robin": RoundRobin,
    "Weighted Round Robin": WeightedRoundRobin,
    "Least Connections": LeastConnections,
    "Least Response Time": LeastResponseTime,
    "IP Hash (Sticky)": IpHash,
    "Random": RandomChoice,
    "Power of Two Choices (P2C)": PowerOfTwoChoices,
    "Consistent Hashing": ConsistentHashRing,
}

def list_algorithms() -> list[str]:
    return list(_REGISTRY.keys())

def create_algorithm(name: str) -> Algorithm:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown algorithm: {name}")
    return cls()
