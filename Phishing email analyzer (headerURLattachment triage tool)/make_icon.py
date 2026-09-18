import os
from PIL import Image, ImageDraw, ImageFilter

os.makedirs("assets", exist_ok=True)
SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# gradient-ish background disc (deep blue)
d.ellipse([6, 6, SIZE - 6, SIZE - 6], fill=(14, 34, 64, 255))
for i in range(12):
    shrink = i * 8
    c = (18 + i * 2, 42 + i * 3, 96 + i * 2)
    d.ellipse([10 + shrink, 10 + shrink, SIZE - 10 - shrink, SIZE - 10 - shrink],
              fill=(c[0], c[1], c[2], 255))

# shield body
shield = [(SIZE // 2, 40), (198, 74), (198, 140), (SIZE // 2, 220), (58, 140), (58, 74)]
d.polygon(shield, fill=(56, 189, 248, 255))
d.polygon([(SIZE // 2, 52), (188, 82), (188, 138), (SIZE // 2, 210), (68, 138), (68, 82)],
          fill=(11, 18, 32, 255))

# inner glow shield
d.polygon([(SIZE // 2, 62), (180, 90), (180, 136), (SIZE // 2, 200), (76, 136), (76, 90)],
          fill=(15, 26, 46, 255))

# exclamation triangle
tri = [(SIZE // 2, 84), (148, 170), (SIZE // 2 + 4, 170)]
d.polygon(tri, outline=(245, 158, 11, 255), width=0)
d.polygon(tri, fill=None)
d.polygon([(SIZE // 2, 86), (140, 164), (SIZE // 2 + 4, 164)], fill=(38, 65, 100, 255))
d.polygon([(SIZE // 2, 86), (140, 164), (SIZE // 2 + 4, 164)],
          outline=(72, 187, 248, 255))

# exclamation mark
d.rounded_rectangle([SIZE // 2 - 6, 100, SIZE // 2 + 6, 136], 3, fill=(255, 255, 255, 220))
d.ellipse([SIZE // 2 - 6, 144, SIZE // 2 + 6, 156], fill=(255, 255, 255, 220))

# soft shadow highlight
glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([28, 28, SIZE - 28, SIZE - 28], fill=(255, 255, 255, 18))
img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(2)))

img.save("assets/icon.png")
img.save("assets/icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon generated:", os.path.abspath("assets/icon.ico"))