"""Tileable textures for the Lumon severed floor, painted with numpy (no downloads).
python tools/make_textures.py  ->  assets/textures/*.png

Floors tile in metres set by the Blender material (MAT_TILE). Walls use u = metres along the wall / tile and
v = height / 2.7 m, so every wall texture carries its own baseboard and top trim.
"""
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "assets", "textures")
N = 512
rng = np.random.default_rng(7)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def noise(n=N, scale=8, octaves=4, seed=0):
    """Tileable value noise in [0,1]."""
    r = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = scale * (2 ** o)
        g = r.random((s, s)).astype(np.float32)
        # bilinear upsample with wrap
        x = np.linspace(0, s, n, endpoint=False)
        x0 = np.floor(x).astype(int)
        fx = (x - x0)[None, :]
        fy = (x - x0)[:, None]
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)
        x1 = (x0 + 1) % s
        a = g[np.ix_(x0, x0)]
        b = g[np.ix_(x0, x1)]
        c = g[np.ix_(x1, x0)]
        d = g[np.ix_(x1, x1)]
        v = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
        out += v * amp
        tot += amp
        amp *= 0.5
    return out / tot


def grain(n=N, seed=1):
    return np.random.default_rng(seed).random((n, n)).astype(np.float32)


def save(name, rgb):
    os.makedirs(OUT, exist_ok=True)
    a = np.clip(rgb, 0, 255).astype(np.uint8)
    Image.fromarray(a, "RGB").save(os.path.join(OUT, name + ".png"))
    print("tex", name)


def colorize(t, c0, c1):
    t = t[..., None]
    return hexc(c0) * (1 - t) + hexc(c1) * t


# ----------------------------------------------------------------------------- floors
def carpet(name, c0, c1, seed, pattern=None):
    t = noise(scale=6, octaves=3, seed=seed) * 0.35 + grain(seed=seed + 1) * 0.45 + 0.1
    fib = np.array(Image.fromarray((grain(seed=seed + 2) * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
    t = t * 0.7 + fib * 0.3
    rgb = colorize(t, c0, c1)
    if pattern == "dots":  # small woven diamonds every 1/8 tile
        yy, xx = np.mgrid[0:N, 0:N]
        k = N // 8
        d = (np.abs((xx % k) - k / 2) + np.abs((yy % k) - k / 2)) < k * 0.12
        rgb[d] = rgb[d] * 0.82
    if pattern == "rows":
        yy = np.mgrid[0:N, 0:N][0]
        rgb *= (0.94 + 0.06 * (np.sin(yy / N * 2 * np.pi * 16) > 0))[..., None]
    save(name, rgb)


def vinyl_tiles(name, c0, c1, line, tiles=2, seed=3, speck=True):
    """Floor tiles: `tiles` x `tiles` per texture with thin grout lines and faint marbling."""
    t = noise(scale=4, octaves=4, seed=seed) * 0.5 + 0.25
    rgb = colorize(t, c0, c1)
    if speck:
        g = grain(seed=seed + 5)
        rgb[g > 0.985] *= 0.82
    yy, xx = np.mgrid[0:N, 0:N]
    k = N // tiles
    lw = max(2, N // 256)
    m = ((xx % k) < lw) | ((yy % k) < lw)
    rgb[m] = hexc(line)
    # each tile a slightly different tone
    tid = (xx // k) * 7 + (yy // k) * 13
    rgb *= (0.97 + 0.03 * np.sin(tid * 1.7))[..., None]
    save(name, rgb)


def wood(name, c0, c1, planks=4, seed=11, vertical=False):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    if vertical:
        xx, yy = yy, xx
    k = N / planks
    pid = np.floor(yy / k)
    off = (np.sin(pid * 12.9898) * 43758.5453) % 1.0
    n = noise(scale=4, octaves=3, seed=seed)
    ring = np.sin((xx / N * 6 + n * 3 + off * 10) * np.pi * 2 + yy / N * 3) * 0.5 + 0.5
    t = ring * 0.35 + noise(scale=16, octaves=2, seed=seed + 1) * 0.3 + off[..., ] * 0.25
    rgb = colorize(np.clip(t, 0, 1), c0, c1)
    edge = (yy % k) < 2
    rgb[edge] *= 0.55
    # butt joints
    j = ((xx + off * N) % (N * 0.999)) < 2
    rgb[j] *= 0.6
    if vertical:
        rgb = np.transpose(rgb, (1, 0, 2))
    save(name, rgb)


def concrete(name, c0, c1, seed=21, joints=True):
    t = noise(scale=5, octaves=5, seed=seed)
    rgb = colorize(t, c0, c1)
    g = grain(seed=seed + 2)
    rgb *= (0.95 + 0.08 * g)[..., None]
    if joints:
        yy, xx = np.mgrid[0:N, 0:N]
        m = (xx < 2) | (yy < 2)
        rgb[m] *= 0.7
    save(name, rgb)


def grass(name, seed=31):
    t = noise(scale=8, octaves=4, seed=seed)
    g = grain(seed=seed + 1)
    blades = np.array(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))).astype(
        np.float32) / 255
    rgb = colorize(np.clip(t * 0.6 + blades * 0.6 - 0.1, 0, 1), "#3f7a33", "#8cc761")
    save(name, rgb)


def hay(name, seed=41):
    img = np.zeros((N, N), np.float32)
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N]
    for _ in range(900):
        x0, y0 = r.integers(0, N, 2)
        ang = r.uniform(0, np.pi)
        L = r.uniform(20, 80)
        for s in np.linspace(0, L, int(L)):
            x = int(x0 + np.cos(ang) * s) % N
            y = int(y0 + np.sin(ang) * s) % N
            img[y, x] += 1
    img = np.array(Image.fromarray(np.clip(img * 80, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)))
    t = np.clip(img.astype(np.float32) / 255 + noise(scale=4, seed=seed) * 0.4, 0, 1)
    save(name, colorize(t, "#9a7a35", "#ead48a"))


# ----------------------------------------------------------------------------- walls (v = height)
def wall(name, base, panel_line, board, board_h=0.12, top_trim=None, seams=2, seed=51, wood_panel=None,
         tiles=None, wainscot=None):
    """u: along the wall (texture = 2.4 m), v: 0 at the top, 1 at the floor (image rows)."""
    H = 2.7
    rows = np.linspace(0, H, N, endpoint=False)[::-1][:, None] * np.ones((1, N))  # metres above floor per row
    t = noise(scale=3, octaves=3, seed=seed) * 0.6 + 0.2
    rgb = colorize(t, base, base) * (0.985 + 0.03 * t)[..., None]
    xx = np.mgrid[0:N, 0:N][1]
    if wood_panel:
        n = noise(scale=6, octaves=3, seed=seed + 3)
        ring = np.sin((n * 8 + xx / N * 40)) * 0.5 + 0.5
        rgb = colorize(ring * 0.5 + n * 0.5, wood_panel[0], wood_panel[1])
        seams = 6
    if tiles:
        k = N // tiles
        m = ((xx % k) < 2) | ((np.mgrid[0:N, 0:N][0] % k) < 2)
        rgb[m] = hexc(panel_line)
    elif seams:
        k = N // seams
        m = (xx % k) < 2
        rgb[m] = rgb[m] * 0.8 + hexc(panel_line) * 0.2
        m2 = ((xx % k) >= 2) & ((xx % k) < 4)
        rgb[m2] = rgb[m2] * 0.93 + 255 * 0.07
    if wainscot:
        wh, wc = wainscot
        m = rows < wh
        rgb[m] = rgb[m] * 0.25 + hexc(wc) * 0.75
        rgb[(rows >= wh) & (rows < wh + 0.03)] = hexc(board) * 0.9
    # soft dirt / ambient shading near the floor
    shade = np.clip(rows / 0.6, 0, 1) * 0.12 + 0.88
    rgb *= shade[..., None]
    rgb[rows < board_h] = hexc(board) * (0.95 + 0.05 * t[rows < board_h])[..., None]
    rgb[(rows >= board_h) & (rows < board_h + 0.015)] = hexc(board) * 1.2
    if top_trim:
        rgb[rows > H - 0.06] = hexc(top_trim)
    save(name, rgb)


def main():
    # floors
    carpet("carpet_green", "#2f5a3d", "#4f8a5e", 1, pattern="dots")       # MDR
    carpet("carpet_teal", "#1d3c44", "#2f5f69", 2, pattern="rows")         # Perpetual Wing
    carpet("carpet_warm", "#6b4a35", "#8f6a4a", 3)                          # Wellness
    carpet("carpet_grey", "#5f6466", "#80878a", 4, pattern="dots")         # orientation / offices
    carpet("carpet_ochre", "#7a6a45", "#a39060", 5, pattern="rows")        # O&D
    carpet("carpet_blue", "#2b3a5a", "#3f5480", 6)                          # Cobel's office
    carpet("carpet_red", "#5a1f22", "#7c2e2f", 7, pattern="dots")          # testing floor lobby
    vinyl_tiles("hall_floor", "#d9ddd6", "#eceee8", "#b9beb6", tiles=2, seed=3)
    vinyl_tiles("tiles_small", "#e8ecec", "#f6f8f8", "#b5c0c2", tiles=8, seed=4, speck=False)
    vinyl_tiles("tiles_check", "#cfd6d2", "#e5ebe7", "#9aa59f", tiles=4, seed=5)
    vinyl_tiles("marble", "#e4e2dc", "#f4f2ec", "#c9c5bc", tiles=1, seed=6)
    vinyl_tiles("testing_floor", "#3b3f42", "#50555a", "#2a2d30", tiles=2, seed=8)
    wood("wood_floor", "#6a4429", "#93633b", planks=6)
    wood("wood", "#8a5a37", "#b07c4f", planks=3, seed=12)
    wood("wood_light", "#b89a72", "#d8bf98", planks=3, seed=13)
    concrete("concrete", "#55595c", "#74787a")
    grass("grass")
    hay("hay")
    # walls
    wall("wall_white", "#e8ebe6", "#b9c1bb", "#5d7a6a", top_trim="#d6dad4")
    wall("wall_hall", "#eef0eb", "#c3c9c2", "#7b8a80", top_trim="#dfe2dc", seams=4)
    wall("wall_cream", "#e7dcc5", "#b9a98a", "#5a3a2a", top_trim="#c9b48c", wainscot=(0.95, "#6e4a33"))
    wall("wall_wood", "#7a5235", "#4a2f1f", "#3a2418", wood_panel=("#6a4429", "#a0703f"), top_trim="#4a2f1f")
    wall("wall_grey", "#a9adaa", "#7d827f", "#3d4240", top_trim="#8d918e")
    wall("wall_tile", "#e9eeee", "#c4cccd", "#8a9698", tiles=12)
    wall("wall_testing", "#5a5e60", "#3d4143", "#2a2d2f", top_trim="#454a4c", seams=4)
    wall("wall_green", "#cfdccf", "#9db09e", "#3e5a48", top_trim="#b9c9ba")
    wall("wall_cabin", "#8c6a48", "#5a4128", "#3a2818", wood_panel=("#7a5434", "#b08050"), top_trim="#5a4128")
    print("DONE")


if __name__ == "__main__":
    main()
