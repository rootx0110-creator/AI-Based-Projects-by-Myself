"""Tests for the ring buffer and interface sampler helpers."""
from __future__ import annotations

from capture.ring_buffer import RingBuffer, RingSeries
from capture.interface_sampler import InterfaceSample, Sample, _is_loopback


def test_ring_series_overwrites_oldest() -> None:
    s = RingSeries.create("t", capacity=4)
    for i in range(10):
        s.append(float(i), float(i))
    times, values = s.window(1000.0, now=100.0)
    assert len(times) == 4
    assert list(values) == [6.0, 7.0, 8.0, 9.0]


def test_ring_series_window_filters_by_time() -> None:
    s = RingSeries.create("t", capacity=100)
    for i in range(50):
        s.append(float(i), float(i))  # ts 0..49
    times, values = s.window(10.0, now=49.0)
    assert len(values) == 10
    assert values[0] == 40.0 and values[-1] == 49.0


def test_ring_buffer_named_series() -> None:
    rb = RingBuffer.create(capacity=16)
    rb.append("download", 1.0, 100.0)
    rb.append("upload", 1.0, 50.0)
    rb.append("iface:eth0", 1.0, 10.0)
    assert rb.last("download") == 100.0
    assert rb.last("upload") == 50.0
    assert rb.last("iface:eth0") == 10.0
    assert rb.last("missing") == 0.0
    assert rb.count("download") == 1


def test_sample_properties() -> None:
    s = Sample(ts=1.0, total_down=1_000_000, total_up=250_000)
    assert s.total_down_mbps == 8.0
    assert s.total_up_mbps == 2.0


def test_interface_sample_mbps() -> None:
    i = InterfaceSample(name="eth", down_bps=1_000_000, up_bps=500_000, link_bps=100_000_000)
    assert i.down_mbps == 8.0
    assert i.up_mbps == 4.0


def test_loopback_detection() -> None:
    assert _is_loopback("Loopback Pseudo-Interface 1")
    assert _is_loopback("lo")
    assert not _is_loopback("Ethernet 2")
