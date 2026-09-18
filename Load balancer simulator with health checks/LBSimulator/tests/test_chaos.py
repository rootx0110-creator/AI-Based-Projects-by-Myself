"""Tests for chaos engine."""

import sys; sys.path.insert(0, '.'); from src.lb.backend import Backend, BackendState
from src.simulator.chaos import ChaosEngine

def test_kill_backend():
    chaos = ChaosEngine()
    b = Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY)
    action = chaos.kill(b, duration_s=30)
    assert b.disable is True
    assert action["type"] == "kill"
    assert action["backend"] == "s1"

def test_add_latency():
    chaos = ChaosEngine()
    b = Backend(id="s1", host="127.0.0.1", port=12000)
    action = chaos.add_latency(b, ms=500)
    assert b.latency_ms == 500.0
    assert action["type"] == "latency"

def test_return_500s():
    chaos = ChaosEngine()
    b = Backend(id="s1", host="127.0.0.1", port=12000)
    action = chaos.return_500s(b, fraction=0.8)
    assert b.error_rate == 0.8
    assert action["type"] == "500"

def test_drop_packets():
    chaos = ChaosEngine()
    b = Backend(id="s1", host="127.0.0.1", port=12000)
    action = chaos.drop_packets(b, fraction=0.3)
    assert action["type"] == "drop"
    assert action["fraction"] == 0.3
