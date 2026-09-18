"""Custom DSP / gradient helpers used by the risk gauge."""
import math


def ease_out_cubic(t: float) -> float:
    """Ease-out cubic easing for smooth gauge animation."""
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return 1 - (1 - t) ** 3


def lerp(a, b, t: float):
    return a + (b - a) * t


def color_lerp(c1, c2, t: float) -> str:
    """Blend two hex colors."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r, g, b = int(lerp(r1, r2, t)), int(lerp(g1, g2, t)), int(lerp(b1, b2, t))
    return f"#{r:02x}{g:02x}{b:02x}"


def mix_with_bg(hex_color: str, bg: str, alpha: float) -> str:
    c = hex_color.lstrip("#")
    b = bg.lstrip("#")
    r = int(lerp(int(b[0:2], 16), int(c[0:2], 16), alpha))
    g = int(lerp(int(b[2:4], 16), int(c[2:4], 16), alpha))
    bl = int(lerp(int(b[4:6], 16), int(c[4:6], 16), alpha))
    return f"#{r:02x}{g:02x}{bl:02x}"