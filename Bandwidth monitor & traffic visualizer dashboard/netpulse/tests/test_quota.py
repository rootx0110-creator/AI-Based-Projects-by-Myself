"""Tests for quota evaluation and alert dedupe."""
from __future__ import annotations

import time

from analytics.quota import QuotaLevel, QuotaTracker


def test_levels_progression() -> None:
    q = QuotaTracker("plan", "monthly", limit_bytes=100)
    assert q.evaluate(10).level == QuotaLevel.OK
    assert q.evaluate(85).level == QuotaLevel.WARN
    assert q.evaluate(97).level == QuotaLevel.CRIT
    assert q.evaluate(120).level == QuotaLevel.EXCEEDED


def test_zero_limit_is_ok() -> None:
    q = QuotaTracker("plan", "monthly", limit_bytes=0)
    assert q.evaluate(1000).level == QuotaLevel.OK


def test_should_alert_fires_once_per_level() -> None:
    q = QuotaTracker("plan", "monthly", limit_bytes=100)
    s = q.evaluate(90)
    assert q.should_alert(s) is True
    assert q.should_alert(q.evaluate(92)) is False  # same level, no repeat
    assert q.should_alert(q.evaluate(99)) is True  # CRIT fires
    q.reset_window()
    assert q.should_alert(q.evaluate(99)) is True  # window reset re-fires


def test_remaining_bytes() -> None:
    q = QuotaTracker("plan", "monthly", limit_bytes=100)
    state = q.evaluate(30)
    assert state.remaining_bytes == 70
    state = q.evaluate(130)
    assert state.remaining_bytes == 0


def test_window_start_daily() -> None:
    start = QuotaTracker.window_start_ts("daily", now=time.time())
    lt = time.localtime(start)
    assert (lt.tm_hour, lt.tm_min, lt.tm_sec) == (0, 0, 0)


def test_window_start_monthly() -> None:
    start = QuotaTracker.window_start_ts("monthly", now=time.time())
    lt = time.localtime(start)
    assert (lt.tm_mday, lt.tm_hour) == (1, 0)
