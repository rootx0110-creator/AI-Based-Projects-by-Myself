"""Generate assets/icon.ico + assets/logo.png + process icon placeholders.

Run:  python scripts/generate_assets.py
Uses Pillow; deterministic design (no random) so rebuilds are reproducible.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")

BG = (15, 20, 32, 255)  # #0f1420
ACCENT = (79, 140, 255)  # #4f8cff
ACCENT2 = (34, 211, 166)  # #22d3a6


def draw_logo(size: int) -> Image.Image:
    """Draw the NetPulse mark: rounded square, pulse line, up arrow glyph."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size // 16

    # rounded background
    d.rounded_rectangle([m, m, size - m, size - m], radius=size // 5, fill=BG)

    # pulse polyline across the middle
    points = []
    n = 7
    xs = [m + size * i / (n - 1) for i in range(n)]
    ys = [0.62, 0.62, 0.35, 0.75, 0.45, 0.62, 0.62]
    for x, y in zip(xs, ys):
        points.append((x, size * y))
    lw = max(2, size // 14)
    d.line(points, fill=ACCENT, width=lw, joint="curve")

    # arrow head on the rising segment (2/3 up)
    ax, ay = xs[2], size * 0.35
    ah = size // 8
    d.polygon([(ax, ay - ah), (ax - ah * 0.8, ay + ah * 0.3), (ax + ah * 0.8, ay + ah * 0.3)], fill=ACCENT2)

    # base bar
    d.rounded_rectangle([size * 0.25, size * 0.78, size * 0.75, size * 0.84], radius=size // 32, fill=ACCENT2)
    return img


def main() -> None:
    """Write icon.ico (multi-size), logo.png and process icon placeholders."""
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(os.path.join(ASSETS, "process_icons"), exist_ok=True)

    logo = draw_logo(256)
    logo.save(os.path.join(ASSETS, "logo.png"))

    # Multi-resolution Windows icon
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    logo.save(os.path.join(ASSETS, "icon.ico"), sizes=icon_sizes)

    # A couple of generic process icon placeholders
    for name, color in (("default.png", (154, 167, 192)), ("browser.png", (79, 140, 255))):
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([4, 4, 28, 28], outline=color + (255,), width=3)
        img.save(os.path.join(ASSETS, "process_icons", name))

    print("assets written to", ASSETS)


if __name__ == "__main__":
    main()
