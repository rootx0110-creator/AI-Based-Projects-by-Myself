"""Generate assets/c2lab.ico (used by the PyInstaller build).

Run: python tools/make_icon.py

The ICO file is written directly (PNG-compressed frames), which is more
reliable across Pillow versions than relying on the ICO plugin's
multi-size handling.
"""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size // 6
    d.rounded_rectangle([m, m, size - m, size - m], radius=size // 5, fill=(15, 42, 67, 255))
    d.ellipse([size * 0.24, size * 0.24, size * 0.76, size * 0.76], fill=(37, 99, 235, 255))
    d.ellipse([size * 0.32, size * 0.32, size * 0.68, size * 0.68], fill=(255, 255, 255, 255))
    try:
        font = ImageFont.load_default(size=int(size * 0.30))
    except (TypeError, ValueError):
        font = ImageFont.load_default()
    text = "C2"
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - w) / 2, (size - h) / 2 - bbox[1]), text, font=font, fill=(15, 42, 67, 255))
    return img


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_ico(images: list[Image.Image]) -> bytes:
    payloads = [_png_bytes(im) for im in images]
    count = len(payloads)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = b""
    body = b""
    for png, size in zip(payloads, SIZES):
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset
        )
        body += png
        offset += len(png)
    return header + entries + body


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icons = [draw_icon(s) for s in SIZES]
    target = ASSETS / "c2lab.ico"
    target.write_bytes(build_ico(icons))
    print(f"wrote {target} ({target.stat().st_size} bytes, {len(SIZES)} sizes)")


if __name__ == "__main__":
    main()