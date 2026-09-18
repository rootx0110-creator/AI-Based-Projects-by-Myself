"""Generates assets/icon.ico (multi-size Windows icon) without external tools.

Run once:  python make_icon.py
Draws a rounded-square badge with a stylized "proxy node" glyph.
"""

from __future__ import annotations

import struct
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None
    ImageDraw = None


def draw_icon(size: int) -> "Image.Image":
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size

    # Background rounded square with vertical gradient (deep blue -> indigo)
    radius = int(s * 0.22)
    top = (79, 140, 255)
    bottom = (59, 65, 190)
    grad = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(grad)
    for y in range(s):
        t = y / max(s - 1, 1)
        gd.line([(0, y), (s, y)], fill=(
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
            255,
        ))
    mask = Image.new("L", (s, s), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # Glyph: two arrows passing through a central node (proxy motif)
    fg = (255, 255, 255, 255)
    dim = (220, 232, 255, 210)
    lw = max(int(s * 0.065), 2)
    cx = s * 0.5

    # central node
    node_r = s * 0.14
    d.ellipse([cx - node_r, s * 0.5 - node_r, cx + node_r, s * 0.5 + node_r],
              fill=fg)

    # left -> center -> right horizontal pipes with arrowheads
    y = s * 0.5
    gap = node_r + s * 0.05
    # left segment
    d.line([s * 0.12, y, cx - gap, y], fill=dim, width=lw)
    # right segment
    d.line([cx + gap, y, s * 0.88, y], fill=fg, width=lw)
    # arrowhead pointing right
    ah = s * 0.09
    d.polygon([(s * 0.88, y), (s * 0.88 - ah, y - ah * 0.8),
               (s * 0.88 - ah, y + ah * 0.8)], fill=fg)
    # arrowhead pointing left (dim)
    d.polygon([(s * 0.12, y), (s * 0.12 + ah, y - ah * 0.8),
               (s * 0.12 + ah, y + ah * 0.8)], fill=dim)

    # small dots top/bottom (traffic)
    dot = s * 0.045
    for (px, py) in ((cx, s * 0.2), (cx, s * 0.8)):
        d.ellipse([px - dot, py - dot, px + dot, py + dot], fill=dim)

    return img


def main() -> None:
    if Image is None:
        print("Pillow not installed; skipping icon generation.")
        return
    out_dir = Path(__file__).parent / "assets"
    out_dir.mkdir(exist_ok=True)

    sizes = (16, 24, 32, 48, 64, 128, 256)
    base = draw_icon(256)
    base.save(out_dir / "icon.png")

    ico_path = out_dir / "icon.ico"
    base.save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"wrote {ico_path}")


if __name__ == "__main__":
    main()
