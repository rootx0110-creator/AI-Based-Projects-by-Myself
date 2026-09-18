"""Generate the VaultGuard application icon (app.ico) using Pillow."""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "app.ico")


def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def make_icon(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256.0

    def P(x, y):
        return int(x * s), int(y * s)

    # rounded-square background, purple->indigo vertical gradient
    for y in range(size):
        t = y / size
        d.line([(0, y), (size, y)], fill=lerp((124, 92, 255), (76, 54, 184), t) + (255,))
    # clip to rounded rect via mask
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(52 * s), fill=255)
    rect = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rect.paste(img, (0, 0), mask)
    img = rect
    d = ImageDraw.Draw(img)

    # subtle top-light sheen
    sheen = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    for y in range(int(30 * s)):
        t = y / (30 * s)
        sd.line([(0, y), (size, y)], fill=(255, 255, 255, int(40 * (1 - t))))
    img = Image.alpha_composite(img, sheen)
    d = ImageDraw.Draw(img)

    # padlock body (white), rounded rect
    x0, y0 = P(78, 138)
    x1, y1 = P(178, 202)
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(16 * s), fill=(255, 255, 255, 255))

    # shackle: arc around top
    bw = int(34 * s)
    d.arc([P(88, 70), P(168, 150)], start=180, end=360, fill=(255, 255, 255, 255), width=bw)
    d.arc([P(122, 104), P(134, 116)], start=0, end=360, fill=(124, 92, 255, 255))

    # keyhole on the padlock body
    cx, cy = P(128, 172)
    r = int(16 * s)
    d.ellipse([cx - r, cy - r - 2, cx + r, cy + r - 2], fill=(34, 211, 238, 255))
    d.polygon([(cx - r, cy), (cx + r, cy), (cx, cy + r + 8)], fill=(34, 211, 238, 255))

    # subtle outline for depth
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(16 * s), outline=(0, 0, 0, 40), width=max(1, int(2 * s)))
    return img


def main():
    base = make_icon(256)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [base.resize((s, s), Image.LANCZOS) for s in sizes]
    imgs[-1] = base
    base.save(OUT, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()