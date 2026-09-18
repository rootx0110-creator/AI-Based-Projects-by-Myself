"""Tests for circuit breaker."""

import sys; sys.path.insert(0, '.'); from src.lb.backend import Backend
from src.lb.health.circuit_breaker import CircuitBreaker

def test_closed_by_default():
    cb = CircuitBreaker()
    b = Backend(id="s1", host="127.0.0.1", port=12000)
    assert cb.on_request(b) is True

def test_open_after_failures():
    cb = CircuitBreaker(failure_threshold=0.5, success_threshold=3, cooldown_ms=1000)
    b = Backend(id="s1", host="127.0.0.1", port=12000)
    for _ in range(6):
        cb.on_response(b, ok=False)
    assert cb.on_request(b) is False

def test_half_open_after_cooldown():
    cb = CircuitBreaker(failure_threshold=5, success_threshold=3, cooldown_ms=100)
    b = Backend(id="s1", host="127.0.0.1", port=12000)
    for _ in range(6):
        cb.on_response(b, ok=False)
    import time; time.sleep(0.15)
    assert cb.on_request(b) is True  # half-open, one probe allowed

def test_closed_after_success_in_half_open():
    cb = CircuitBreaker(failure_threshold=5, success_threshold=2, cooldown_ms=100)
    b = Backend(id="s1", host="127.0.0.1", port=12000)
    for _ in range(6):
        cb.on_response(b, ok=False)
    import time; time.sleep(0.15)
    cb.on_request(b)  # allow probe
    cb.on_response(b, ok=True)
    cb.on_response(b, ok=True)
    assert cb.on_request(b) is True
