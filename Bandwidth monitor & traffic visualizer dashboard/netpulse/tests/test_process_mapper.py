"""Tests for ProcessInfo/ConnInfo and mapper helpers."""
from __future__ import annotations

from capture.process_mapper import ConnInfo, ProcessInfo, ProcessMapper, _is_local


def test_conn_remote_format() -> None:
    c = ConnInfo(laddr="192.168.1.5", lport=44444, raddr="1.2.3.4", rport=443, status="ESTABLISHED", proto="TCP")
    assert c.remote == "1.2.3.4:443"


def test_conn_remote_unconnected() -> None:
    c = ConnInfo(laddr="192.168.1.5", lport=44444, raddr="", rport=0, status="LISTEN", proto="TCP")
    assert c.remote == "-"


def test_process_total_rate() -> None:
    p = ProcessInfo(pid=1, name="a.exe", rate_down=100.0, rate_up=50.0)
    assert p.total_rate == 150.0


def test_is_local() -> None:
    assert _is_local("127.0.0.1")
    assert _is_local("::1")
    assert _is_local("169.254.1.2")
    assert not _is_local("8.8.8.8")


def test_scale_rates_proportional() -> None:
    m = ProcessMapper(interval_ms=1000)
    a = ProcessInfo(pid=1, name="a.exe")
    b = ProcessInfo(pid=2, name="b.exe")
    # simulate provisional shares from _estimate_rates
    m.processes = {1: a, 2: b}
    a.rate_down, b.rate_down = 0.75, 0.25  # shares
    out = m.scale_rates(total_down=100.0, total_up=0.0)
    assert out[1].rate_down == 75.0
    assert out[2].rate_down == 25.0


def test_top_orders_by_rate() -> None:
    m = ProcessMapper(interval_ms=1000)
    a = ProcessInfo(pid=1, name="a.exe", rate_down=10)
    b = ProcessInfo(pid=2, name="b.exe", rate_down=90)
    m.processes = {1: a, 2: b}
    top = m.top(n=1)
    assert top[0].name == "b.exe"
