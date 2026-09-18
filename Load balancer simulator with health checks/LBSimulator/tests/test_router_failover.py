"""Tests for router failover behavior."""

import sys; sys.path.insert(0, '.'); from src.lb.pool import Pool
from src.lb.backend import Backend, BackendState
from src.lb.router import Router, RequestContext, MetricsView

def test_failover_on_backend_removal():
    pool = Pool()
    pool.add(Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY))
    pool.add(Backend(id="s2", host="127.0.0.1", port=12001, state=BackendState.HEALTHY))
    router = Router(pool)

    ctx = RequestContext(client_ip="10.0.0.1")
    metrics = MetricsView()
    backend, rationale = router.pick(ctx, metrics)
    assert backend.id in ("s1", "s2")

    pool.get("s1").state = BackendState.UNHEALTHY
    backend2, rationale2 = router.pick(ctx, metrics)
    assert backend2.id == "s2"

def test_no_backends_raises():
    pool = Pool()
    router = Router(pool)
    ctx = RequestContext()
    metrics = MetricsView()
    try:
        router.pick(ctx, metrics)
        assert False, "Should have raised"
    except RuntimeError:
        pass

def test_algorithm_switch_affects_routing():
    pool = Pool()
    pool.add(Backend(id="s1", host="127.0.0.1", port=12000, state=BackendState.HEALTHY))
    pool.add(Backend(id="s2", host="127.0.0.1", port=12001, state=BackendState.HEALTHY))
    router = Router(pool)
    router.set_algorithm("Random")
    ctx = RequestContext()
    m = MetricsView()
    first = router.pick(ctx, m)[0].id
    second = router.pick(ctx, m)[0].id
    assert first in ("s1", "s2")
    assert second in ("s1", "s2")
