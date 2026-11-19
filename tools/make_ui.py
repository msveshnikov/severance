"""UI images drawn in code: app icon (+ Android adaptive layers, .ico), boot splash, CRT digit atlas,
soft blob shadow, glow dot.  python tools/make_ui.py"""
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UI = os.path.join(ROOT, "assets", "ui")
FONT_MONO = os.path.join(ROOT, "assets", "fonts", "DejaVuSansMono-Bold.ttf")
FONT_UI = os.path.join(ROOT, "assets", "fonts", "Rubik-Variable.ttf")
BG = (11, 21, 18)
LUMON = (156, 195, 230)
NAVY = (31, 58, 95)


def globe(d, cx, cy, r, col, w):
    for k in (1.0, 0.76, 0.52):
        d.ellipse((cx - r * k, cy - r * k, cx + r * k, cy + r * k), outline=col, width=w)
    for k in (0.33, 0.66):
        d.ellipse((cx - r * k, cy - r, cx + r * k, cy + r), outline=col, width=max(1, w * 2 // 3))
    d.line((cx - r, cy, cx + r, cy), fill=col, width=max(1, w * 2 // 3))


def icon(size=1024):
    im = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(im)
    # soft radial vignette in Lumon navy
    y, x = np.mgrid[0:size, 0:size]
    r = np.hypot(x - size / 2, y - size / 2) / (size / 2)
    a = np.clip(1 - r, 0, 1) ** 1.5
    arr = np.array(im).astype(np.float32)
    arr = arr * (1 - a[..., None] * 0.8) + np.array(NAVY, np.float32) * a[..., None] * 0.8
    im = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(im)
    globe(d, size / 2, size * 0.46, size * 0.3, LUMON, max(3, size // 60))
    f = ImageFont.truetype(FONT_MONO, int(size * 0.11))
    t = "LUMON"
    w = d.textlength(t, font=f)
    d.text(((size - w) / 2, size * 0.8), t, font=f, fill=(233, 236, 230))
    return im


def main():
    os.makedirs(UI, exist_ok=True)
    ic = icon(1024)
    ic.save(os.path.join(UI, "icon.png"))
    ic.resize((192, 192), Image.LANCZOS).save(os.path.join(UI, "icon_192.png"))
    ic.resize((256, 256), Image.LANCZOS).save(os.path.join(UI, "icon.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    # adaptive icon: background = flat colour, foreground = globe in the safe zone
    Image.new("RGB", (432, 432), BG).save(os.path.join(UI, "adaptive_bg_432.png"))
    fg = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    globe(d, 216, 206, 92, LUMON + (255,), 6)
    f = ImageFont.truetype(FONT_MONO, 34)
    w = d.textlength("LUMON", font=f)
    d.text(((432 - w) / 2, 300), "LUMON", font=f, fill=(233, 236, 230, 255))
    fg.save(os.path.join(UI, "adaptive_fg_432.png"))
    # splash
    sp = Image.new("RGBA", (640, 360), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    globe(d, 320, 140, 80, LUMON + (255,), 4)
    f = ImageFont.truetype(FONT_MONO, 40)
    w = d.textlength("SEVERANCE", font=f)
    d.text(((640 - w) / 2, 250), "SEVERANCE", font=f, fill=(233, 236, 230, 255))
    sp.save(os.path.join(UI, "splash.png"))
    # CRT digits atlas (white, used by the terminal screen shader and the MDR minigame)
    f = ImageFont.truetype(FONT_MONO, 80)
    at = Image.new("RGBA", (640, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(at)
    for k in range(10):
        s = str(k)
        w = d.textlength(s, font=f)
        d.text((k * 64 + (64 - w) / 2, 2), s, font=f, fill=(255, 255, 255, 255))
    at.save(os.path.join(UI, "digits.png"))
    # blob shadow
    n = 128
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(x - n / 2 + 0.5, y - n / 2 + 0.5) / (n / 2)
    a = np.clip(1 - r, 0, 1) ** 1.6
    img = np.zeros((n, n, 4), np.uint8)
    img[..., 3] = (a * 200).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(UI, "blob.png"))
    # glow dot (particles, sparkles)
    a = np.clip(1 - r, 0, 1) ** 2.2
    img = np.zeros((n, n, 4), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (a * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(UI, "glow.png"))
    print("DONE")


if __name__ == "__main__":
    main()
