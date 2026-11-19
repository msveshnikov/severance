"""Google Play graphics: 512 icon, 1024x500 feature graphics (en/ru) and phone screenshots from the game's own
screenshot tour.  python tools/play_store.py   (after: godot --path . --resolution 1920x1080 -- --autotest)
-> renders/play/
"""
import os
import glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "renders", "play")
GAME = os.path.join(ROOT, "renders", "game")
MONO = os.path.join(ROOT, "assets", "fonts", "DejaVuSansMono-Bold.ttf")
UI = os.path.join(ROOT, "assets", "fonts", "Rubik-Variable.ttf")
SHOTS = ["d01_mg", "02_hall", "d06_stealth", "d13_a", "d15_a", "d17_dance", "d08_mg", "91_map"]


def feature(bg_name, title, sub, out):
    src = Image.open(os.path.join(GAME, bg_name + ".png")).convert("RGB")
    w, h = src.size
    crop = src.crop((int(w * 0.1), int(h * 0.12), int(w * 0.9), int(h * 0.12 + w * 0.8 * 500 / 1024)))
    im = crop.resize((1024, 500), Image.LANCZOS)
    shade = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(shade)
    for x in range(1024):
        a = int(max(0, 230 - x * 0.42))
        d.line([(x, 0), (x, 500)], fill=(8, 18, 16, a))
    im = Image.alpha_composite(im.convert("RGBA"), shade)
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(MONO, 74)
    f2 = ImageFont.truetype(MONO, 30)
    d.text((48, 170), title, font=f1, fill=(236, 242, 238), stroke_width=4, stroke_fill=(6, 16, 14))
    d.text((52, 262), sub, font=f2, fill=(115, 242, 210), stroke_width=3, stroke_fill=(6, 16, 14))
    # Lumon globe
    cx, cy, r = 96, 100, 44
    for k in (1.0, 0.72, 0.45):
        d.ellipse((cx - r * k, cy - r * k, cx + r * k, cy + r * k), outline=(156, 195, 230), width=3)
    d.line((cx - r, cy, cx + r, cy), fill=(156, 195, 230), width=2)
    im.convert("RGB").save(os.path.join(OUT, out))
    print("feature", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    Image.open(os.path.join(ROOT, "assets", "ui", "icon.png")).resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "icon_512.png"))
    feature("02_hall", "SEVERANCE", "LUMON OFFICE · ISOMETRIC ADVENTURE", "feature_en.png")
    feature("02_hall", "РАЗДЕЛЕНИЕ", "ОФИС LUMON · ИЗОМЕТРИЧЕСКОЕ ПРИКЛЮЧЕНИЕ", "feature_ru.png")
    k = 0
    for s in SHOTS:
        p = os.path.join(GAME, s + ".png")
        if os.path.exists(p):
            k += 1
            Image.open(p).convert("RGB").save(os.path.join(OUT, "shot_%d.jpg" % k), quality=92)
    print("screens", k)


if __name__ == "__main__":
    main()
