"""Tests for load balancing algorithms."""

import sys; sys.path.insert(0, '.'); from src.lb.algorithms import create_algorithm, list_algorithms
from src.lb.backend import Backend

def make_backend(idx, weight=1.0, latency_ms=0.0):
    return Backend(id=f"s{idx}", host="127.0.0.1", port=12000 + idx, weight=weight, latency_ms=latency_ms)

def test_list_algorithms():
    names = list_algorithms()
    assert len(names) == 8
    assert "Round Robin" in names

def test_round_robin():
    algo = create_algorithm("Round Robin")
    backends = [make_backend(1), make_backend(2), make_backend(3)]
    picked = [algo.pick(None, backends, None).id for _ in range(6)]
    assert picked == ["s1", "s2", "s3", "s1", "s2", "s3"]

def test_weighted_rr():
    algo = create_algorithm("Weighted Round Robin")
    backends = [make_backend(1, weight=1.0), make_backend(2, weight=3.0)]
    picked = [algo.pick(None, backends, None).id for _ in range(4)]
    assert picked.count("s2") > picked.count("s1")

def test_least_conn():
    algo = create_algorithm("Least Connections")
    a = make_backend(1); a._active_conns = 5
    b = make_backend(2); b._active_conns = 2
    c = make_backend(3); c._active_conns = 10
    chosen = algo.pick(None, [a, b, c], None)
    assert chosen.id == "s2"

def test_least_rt():
    algo = create_algorithm("Least Response Time")
    a = make_backend(1, latency_ms=50.0)
    b = make_backend(2, latency_ms=10.0)
    c = make_backend(3, latency_ms=100.0)
    chosen = algo.pick(None, [a, b, c], None)
    assert chosen.id == "s2"

def test_ip_hash():
    algo = create_algorithm("IP Hash (Sticky)")
    backends = [make_backend(1), make_backend(2), make_backend(3)]
    ctx = type("Ctx", (), {"client_ip": "10.0.0.1"})()
    first = algo.pick(ctx, backends, None)
    second = algo.pick(ctx, backends, None)
    assert first.id == second.id  # same IP => same backend

def test_random():
    algo = create_algorithm("Random")
    backends = [make_backend(1), make_backend(2), make_backend(3)]
    picked = set(algo.pick(None, backends, None).id for _ in range(20))
    assert len(picked) >= 2  # not always same

def test_p2c():
    algo = create_algorithm("Power of Two Choices (P2C)")
    a = make_backend(1, latency_ms=50.0)
    b = make_backend(2, latency_ms=10.0)
    c = make_backend(3, latency_ms=100.0)
    chosen = algo.pick(None, [a, b, c], None)
    assert chosen.id in ("s1", "s2", "s3")  # P2C picks best of two random probes

def test_consistent_hash():
    algo = create_algorithm("Consistent Hashing")
    backends = [make_backend(1), make_backend(2), make_backend(3)]
    algo.rebuild(backends)
    first = algo.lookup("client-a")
    second = algo.lookup("client-a")
    assert first == second
