"""Generate assets/icon.ico using Pillow (no PySide dependency at build time)."""
from PIL import Image, ImageDraw

SIZE = 256


def build_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * 0.035)
    # outer rounded plate
    d.rounded_rectangle([2, 2, size - 3, size - 3], radius=int(size * 0.22),
                        fill=(15, 27, 43, 255))
    # ring - magnifier/shield ring
    m = int(size * 0.09)
    margin = int(size * 0.14)
    d.ellipse([margin, margin, size - margin, size - margin],
              outline=(45, 212, 191, 255), width=int(size * 0.035))
    # inner ring accent
    d2 = margin + int(size * 0.06)
    d.ellipse([d2, d2, size - d2, size - d2],
              outline=(56, 189, 248, 255), width=int(size * 0.018))
    # check mark
    w = int(size * 0.045)
    d.line([size * 0.34, size * 0.48, size * 0.44, size * 0.60],
           fill=(45, 212, 191, 255), width=w)
    d.line([size * 0.44, size * 0.60, size * 0.68, size * 0.36],
           fill=(45, 212, 191, 255), width=w)
    d.line([size * 0.68, size * 0.36, size * 0.68, size * 0.36],
           fill=(45, 212, 191, 255), width=w)
    return img


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [build_icon(s) for s in sizes]
    imgs[-1].save(str(__import__("pathlib").Path(__file__).parent / "icon.ico"),
                  format="ICO", sizes=[(s, s) for s in sizes],
                  append_images=imgs[:-1])


if __name__ == "__main__":
    main()