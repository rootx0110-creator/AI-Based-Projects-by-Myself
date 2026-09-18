"""Traffic pattern generators for RPS shaping."""

from typing import Callable
from src.core.clock import Clock

def constant(rps: float) -> Callable[[float], float]:
    """Always return rps."""
    return lambda t: rps

def ramp_up(initial: float, target: float, duration_s: float) -> Callable[[float], float]:
    """Linearly ramp from initial to target over duration_s, then hold target."""
    def f(t):
        if t <= duration_s:
            return initial + (target - initial) * (t / duration_s)
        return target
    return f

def spike(base: float, peak: float, interval_s: float = 10.0, width_s: float = 1.0) -> Callable[[float], float]:
    """Periodic spikes on top of base load."""
    def f(t):
        phase = t % interval_s
        if phase < width_s:
            return peak
        return base
    return f

def sine_wave(min_rps: float, max_rps: float, period_s: float = 20.0) -> Callable[[float], float]:
    """Smooth sinusoidal RPS variation."""
    import math
    def f(t):
        return min_rps + (max_rps - min_rps) * (0.5 + 0.5 * math.sin(2 * math.pi * t / period_s))
    return f

def burst_pattern(
    base: float,
    bursts: list[tuple[float, float, float]],  # (start_s, duration_s, rps)
) -> Callable[[float], float]:
    """Apply instantaneous bursts at given offsets."""
    def f(t):
        for start_s, dur_s, rps in bursts:
            if start_s <= t < start_s + dur_s:
                return rps
        return base
    return f
