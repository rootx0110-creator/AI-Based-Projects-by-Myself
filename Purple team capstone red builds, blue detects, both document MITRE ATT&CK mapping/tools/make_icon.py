"""Generates assets/purpleteam.ico from a mini purple-shield drawing (Pillow).

Usage:  python tools/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "assets" / "purpleteam.ico"

SIZE = 256


def _font(size: int):
    for cand in ("C:\\Windows\\Fonts\\arialbd.ttf", "C:\\Windows\\Fonts\\segoeuib.ttf"):
        p = Path(cand)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                pass
    return ImageFont.load_default()


def build() -> Path:
    img = Image.new("RGBA", (SIZE, SIZE), (15, 20, 32, 255))
    d = ImageDraw.Draw(img)

    # dark rounded backdrop
    d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=44, fill=(23, 30, 46, 255),
                        outline=(122, 162, 255, 255), width=3)

    # shield
    d.polygon([(128, 40), (212, 72), (212, 138), (128, 220), (44, 138), (44, 72)],
              fill=(26, 36, 58, 255), outline=(122, 162, 255, 255), width=3)

    # red slash + blue slash meeting in the middle (purple team)
    d.line([(72, 84), (172, 168)], fill=(255, 107, 129, 255), width=14)
    d.line([(184, 84), (84, 168)], fill=(79, 195, 247, 255), width=14)

    # MITRE-ish dot in the core
    cx, cy = 128, 142
    r = 12
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(179, 136, 255, 255))

    f = _font(26)
    d.text((128, 216), "ATT&CK", font=f, fill=(223, 230, 243, 255), anchor="ma")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("wrote", OUT)
    return OUT


if __name__ == "__main__":
    build()