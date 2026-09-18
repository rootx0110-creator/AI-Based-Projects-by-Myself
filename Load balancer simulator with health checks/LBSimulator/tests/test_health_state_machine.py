"""Tests for health state machine."""

import sys; sys.path.insert(0, '.'); from src.lb.backend import Backend, BackendState
from src.lb.health.state_machine import HealthStateMachine

def test_healthy_initial():
    sm = HealthStateMachine()
    b = Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY)
    next_state = sm.update(b)
    assert next_state == BackendState.HEALTHY

def test_degraded_on_failures():
    sm = HealthStateMachine(degraded_threshold=3, unhealthy_threshold=5)
    b = Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY)
    for _ in range(3):
        b.failed_checks += 1
    next_state = sm.update(b)
    assert next_state == BackendState.DEGRADED

def test_unhealthy_on_many_failures():
    sm = HealthStateMachine(unhealthy_threshold=5)
    b = Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY)
    for _ in range(5):
        b.failed_checks += 1
    next_state = sm.update(b)
    assert next_state == BackendState.UNHEALTHY

def test_recovery_to_healthy():
    sm = HealthStateMachine(recovery_threshold=3)
    b = Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.DEGRADED, ok_checks=2)
    b.ok_checks += 1
    next_state = sm.update(b)
    assert next_state == BackendState.HEALTHY

def test_disabled_manual():
    sm = HealthStateMachine()
    b = Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY, disable=True)
    next_state = sm.update(b)
    assert next_state == BackendState.DISABLED

def test_draining_then_disabled():
    sm = HealthStateMachine()
    b = Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY, drain=True)
    # Set _active_conns attribute manually since it's not a dataclass field
    b._active_conns = 0
    next_state = sm.update(b)
    assert next_state == BackendState.DISABLED
