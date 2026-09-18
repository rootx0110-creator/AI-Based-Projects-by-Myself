from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# rounded-square shield background, dark navy
d.rounded_rectangle([16, 16, 240, 240], radius=56, fill="#161d2e", outline="#2f81f7", width=6)
# shield body (accent blue)
d.polygon([(128, 40), (208, 72), (208, 140), (128, 216), (48, 140), (48, 72)], fill="#2f81f7")
# inner shield highlight
d.polygon([(128, 62), (190, 87), (190, 135), (128, 196), (66, 135), (66, 87)], fill="#0d1117")
# check mark (ok) in green
d.line([(96, 132), (116, 152), (164, 104)], fill="#3fb950", width=18, joint="curve")
# small fingerprint dot
d.ellipse([104, 160, 152, 208], fill="#e6edf3")

img.save("assets/icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save("assets/icon.png")
print("icons written")