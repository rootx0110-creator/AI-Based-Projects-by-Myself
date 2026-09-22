"""Beacon schedule simulation with jitter.

Emulates how C2 agents repeatedly check in and how a detection analyst
evaluates the regularity of those intervals.
"""
from __future__ import annotations

import math
import random


class BeaconSchedule:
    """A sequence of synthetic beacon timestamps (seconds since epoch)."""

    def __init__(
        self,
        interval: float = 60.0,
        jitter_pct: float = 0.0,
        count: int = 20,
        seed: int = 42,
        start: float = 1_700_000_000.0,
    ) -> None:
        self.interval = interval
        self.jitter_pct = jitter_pct
        self.count = count
        self.seed = seed
        self.start = start
        self._times: list[float] | None = None

    def generate(self) -> list[float]:
        rand = random.Random(self.seed)
        jitter_abs = (self.jitter_pct / 100.0) * self.interval
        times: list[float] = []
        t = self.start
        for _ in range(self.count):
            times.append(round(t, 3))
            t += self.interval + rand.uniform(-jitter_abs, jitter_abs)
        self._times = times
        return times

    def intervals(self) -> list[float]:
        times = self.generate()
        return [round(b - a, 3) for a, b in zip(times, times[1:])]

    def stats(self) -> dict:
        diffs = self.intervals()
        mean = sum(diffs) / len(diffs)
        variance = sum((d - mean) ** 2 for d in diffs) / len(diffs)
        std = math.sqrt(variance)
        return {
            "count": self.count,
            "interval_target": self.interval,
            "jitter_pct_requested": self.jitter_pct,
            "interval_mean": round(mean, 3),
            "interval_std": round(std, 3),
            "coefficient_of_variation": round(std / mean, 4) if mean else 0.0,
            "min": round(min(diffs), 3),
            "max": round(max(diffs), 3),
        }


class BeaconSimulator:
    """Produce human-readable beacon timeline plus stability verdict."""

    @staticmethod
    def transcribe(times: list[float]) -> list[dict]:
        rows = []
        for idx, t in enumerate(times):
            rows.append(
                {
                    "beacon": idx + 1,
                    "timestamp": t,
                    "utc": BeaconSimulator._ts_to_utc(t),
                }
            )
        return rows

    @staticmethod
    def verdict(stats: dict) -> dict:
        std = stats["interval_std"]
        mean = stats["interval_mean"]
        cv = std / mean if mean else 0.0
        if cv < 0.05:
            severity = "HIGH"
            label = "Highly mechanically regular - classic fixed-interval beacon"
        elif cv < 0.25:
            severity = "MEDIUM"
            label = "Mostly regular - intermittent jitter; worth deeper review"
        elif cv < 0.6:
            severity = "LOW"
            label = "Jittered / human-affected schedule; harder to attribute"
        else:
            severity = "INFO"
            label = "Irregular traffic; beacon-like behaviour not clearly present"
        return {"severity": severity, "label": label, "cv": round(cv, 4)}

    @staticmethod
    def _ts_to_utc(ts: float) -> str:
        import datetime as dt

        return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )