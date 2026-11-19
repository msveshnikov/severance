"""Task 1: every prop of the Lumon floors, one glTF each.
blender -b --factory-startup -P build_props.py -- [--no-render] [--only terminal,desk_pod]
Writes assets/props/<name>.gltf (+ .bin), assets/props/props_info.json (footprints), renders/props/*.png

Conventions: 1 unit = 1 m, the front faces Blender -Y, pivot = centre of the base on the ground.
Wall-mounted props (paintings, clocks, signs): pivot on the wall plane, at the centre of the canvas (the world
builder lifts them to the plan's z). Nodes the game drives: EMIT_screen (terminal/monitor screens get a shader),
INT_lever (OTC lever, pivot at its axle), INT_door_L/R (sliding doors), INT_lid, ANIM_*.
"""
import bpy
import sys
import os
import math
import json

sys.path.insert(0, os.path.dirname(__file__))
from lib_geo import *  # noqa
import lib_render as R
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NO_RENDER = "--no-render" in ARGS
ONLY = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None

D = math.radians
PROPS = {}
INFO = {}


def prop(name, block=True, mounted=False, pad=0.0):
    def deco(fn):
        PROPS[name] = (fn, dict(block=block, mounted=mounted, pad=pad))
        return fn
    return deco


def fit_uv(ob):
    """Planar UV over the object's bounds on its dominant face axis (for canvases and screens)."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    xs = [v.co for v in me.vertices]
    mn = Vector((min(c.x for c in xs), min(c.y for c in xs), min(c.z for c in xs)))
    mx = Vector((max(c.x for c in xs), max(c.y for c in xs), max(c.z for c in xs)))
    ext = mx - mn
    for p in me.polygons:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ext.y < ext.x and ext.y < ext.z:      # faces -Y
                u = (co.x - mn.x) / max(ext.x, 1e-6)
                v = (co.z - mn.z) / max(ext.z, 1e-6)
            elif ext.x < ext.z:                       # faces X
                u = (co.y - mn.y) / max(ext.y, 1e-6)
                v = (co.z - mn.z) / max(ext.z, 1e-6)
            else:                                     # faces Z
                u = (co.x - mn.x) / max(ext.x, 1e-6)
                v = (co.y - mn.y) / max(ext.y, 1e-6)
            uv[li].uv = (u, v)


def B(name, size, loc, m, bevel=0.0, rot=None):
    return box(name, size, loc, m, bevel=bevel, rot=rot)


# ============================================================================ MDR
@prop("desk_pod")
def desk_pod():
    o = []
    top = mat("desk_top", "#eef0ea", rough=0.4)
    edge = mat("desk_edge", "#c9cdc6", rough=0.5)
    # four desks around the centre (N, E, S, W), each 1.4 wide, from r=0.75 to r=1.55
    for k in range(4):
        a = k * math.pi / 2
        r = 1.15
        cx, cy = math.sin(a) * r, -math.cos(a) * r
        w, d = (1.4, 0.8) if k % 2 == 0 else (0.8, 1.4)
        o.append(B("top%d" % k, (w, d, 0.04), (cx, cy, 0.70), top, bevel=0.012))
        o.append(B("apron%d" % k, (w - 0.06, d - 0.06, 0.08), (cx, cy, 0.62), edge))
        # pedestal drawers under the outer side + a slim leg
        px, py = math.sin(a) * 1.25, -math.cos(a) * 1.25
        off = Vector((math.cos(a), math.sin(a), 0)) * 0.42
        o.append(B("ped%d" % k, (0.38 if k % 2 == 0 else 0.5, 0.5 if k % 2 == 0 else 0.38, 0.62),
                   (px + off.x, py + off.y, 0.0), edge, bevel=0.01))
        o.append(B("leg%d" % k, (0.05, 0.05, 0.62), (px - off.x, py - off.y, 0.0), mat("steel", "steel_brushed")))
    # the green fabric X partitions (four arms from the centre on the diagonals)
    g = mat("divider_green", "#6f9a78", rough=0.85)
    frame = mat("divider_frame", "#d9dcd5", rough=0.5)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        L = 1.95
        cx, cy = math.cos(a) * L / 2, math.sin(a) * L / 2
        o.append(B("part%d" % k, (L, 0.06, 1.18), (cx, cy, 0.0), g, bevel=0.015, rot=(0, 0, a)))
        o.append(B("pcap%d" % k, (L + 0.02, 0.08, 0.035), (cx, cy, 1.18), frame, bevel=0.01, rot=(0, 0, a)))
    o.append(cyl("hub", 0.09, 1.24, (0, 0, 0), frame, n=12))
    return o


@prop("terminal", block=False)
def terminal():
    """The Lumon refinement terminal: a squat cream CRT with a recessed screen, keyboard and trackball."""
    o = []
    shell = mat("crt_shell", "#e4dfcf", rough=0.45)
    dark = mat("crt_bezel", "#2b302d", rough=0.5)
    o.append(B("body", (0.42, 0.36, 0.30), (0, 0.06, 0.04), shell, bevel=0.035))
    o.append(B("hood", (0.36, 0.22, 0.24), (0, 0.24, 0.07), shell, bevel=0.03))
    o.append(B("bezel", (0.36, 0.02, 0.25), (0, -0.115, 0.075), dark, bevel=0.01))
    scr = B("EMIT_screen", (0.31, 0.01, 0.205), (0, -0.127, 0.097), mat("EMIT_screen", "#0d2a24"), bevel=0.0)
    o.append(scr)
    o.append(B("foot", (0.3, 0.3, 0.04), (0, 0.06, 0.0), shell, bevel=0.012))
    o.append(B("badge", (0.06, 0.005, 0.015), (0.13, -0.122, 0.055), mat("brass", "brass", metal=0.8)))
    # keyboard + trackball
    o.append(B("kbd", (0.36, 0.13, 0.03), (-0.02, -0.27, 0.0), shell, bevel=0.012))
    keys = mat("crt_keys", "#cfc9b6")
    for r in range(3):
        o.append(B("keys%d" % r, (0.32, 0.025, 0.012), (-0.02, -0.235 - r * 0.033, 0.03), keys, bevel=0.004))
    o.append(B("tbbase", (0.1, 0.1, 0.03), (0.21, -0.27, 0.0), shell, bevel=0.012))
    o.append(sphere("ball", 0.032, (0.21, -0.27, 0.04), mat("trackball", "#3a6fa8", rough=0.2), seg=12, rings=8))
    return o


@prop("chair_office", pad=-0.1)
def chair_office():
    o = []
    seat = mat("chair_fabric", "#3d4a44", rough=0.9)
    st = mat("steel", "steel_brushed")
    o.append(B("seat", (0.46, 0.44, 0.08), (0, 0, 0.44), seat, bevel=0.03))
    o.append(B("back", (0.42, 0.07, 0.42), (0, 0.22, 0.55), seat, bevel=0.03, rot=(D(-8), 0, 0)))
    o.append(cyl("post", 0.025, 0.4, (0, 0, 0.06), st, n=8))
    for k in range(5):
        a = k * 2 * math.pi / 5
        o.append(B("leg%d" % k, (0.04, 0.27, 0.03), (math.sin(a) * 0.12, -math.cos(a) * 0.12, 0.05), st,
                   rot=(0, 0, -a)))
        o.append(sphere("wheel%d" % k, 0.025, (math.sin(a) * 0.25, -math.cos(a) * 0.25, 0.025), "black", seg=8, rings=6))
    for sx in (-1, 1):
        o.append(B("arm%d" % sx, (0.04, 0.3, 0.03), (sx * 0.24, 0.02, 0.66), "black", bevel=0.01))
        o.append(B("armp%d" % sx, (0.03, 0.03, 0.18), (sx * 0.24, 0.06, 0.48), st))
    return o


@prop("filing_cabinet")
def filing_cabinet():
    o = []
    m = mat("cabinet_green", "#8fa594", rough=0.5, metal=0.2)
    o.append(B("body", (0.46, 0.6, 1.3), (0, 0, 0), m, bevel=0.012))
    for k in range(4):
        z = 0.08 + k * 0.31
        o.append(B("drawer%d" % k, (0.42, 0.02, 0.27), (0, -0.305, z), mat("cabinet_face", "#9fb4a3", rough=0.45)))
        o.append(B("handle%d" % k, (0.14, 0.03, 0.025), (0, -0.325, z + 0.2), mat("steel", "steel_brushed")))
        o.append(B("label%d" % k, (0.08, 0.01, 0.04), (0, -0.317, z + 0.12), "paper"))
    return o


@prop("water_cooler")
def water_cooler():
    o = [B("base", (0.34, 0.34, 0.95), (0, 0, 0), mat("plastic_white", "#eef0ea", rough=0.45), bevel=0.03)]
    o.append(cyl("bottle", 0.15, 0.42, (0, 0, 0.95), mat("water_blue", "#7fbfe0", rough=0.05), n=16))
    o.append(B("tapr", (0.04, 0.05, 0.05), (0.06, -0.18, 0.7), "red_mark"))
    o.append(B("tapb", (0.04, 0.05, 0.05), (-0.06, -0.18, 0.7), mat("tap_blue", "#3a6fa8")))
    return o


@prop("plant_tall")
def plant_tall():
    o = [cyl("pot", 0.2, 0.42, (0, 0, 0), mat("pot_white", "#e8e8e2", rough=0.4), n=16, r2=0.16)]
    o.append(cyl("soil", 0.18, 0.02, (0, 0, 0.41), mat("soil", "#3a2b20"), n=12))
    r = rnd(4)
    for k in range(9):
        a = k * 2.4
        h = 0.9 + r.random() * 0.5
        lean = 0.12 + r.random() * 0.18
        top = (math.cos(a) * lean, math.sin(a) * lean, 0.42 + h)
        o.append(tube_path("stem%d" % k, [(0, 0, 0.42), (top[0] * 0.4, top[1] * 0.4, 0.42 + h * 0.6), top], 0.012,
                           "leaf2", n=5))
        o.append(sphere("leaf%d" % k, 0.13, top, "leaf" if k % 2 else "leaf2", scale=(1.0, 0.45, 0.28), seg=8, rings=5))
    return o


@prop("plant_small")
def plant_small():
    o = [cyl("pot", 0.15, 0.3, (0, 0, 0), mat("pot_terra", "#b8714f", rough=0.7), n=14, r2=0.12)]
    for k in range(6):
        a = k * 1.05
        o.append(sphere("bush%d" % k, 0.13, (math.cos(a) * 0.08, math.sin(a) * 0.08, 0.42 + (k % 2) * 0.08),
                        "leaf" if k % 2 else "leaf2", seg=8, rings=6))
    return o


@prop("coat_rack")
def coat_rack():
    w = mat("darkwood", "darkwood")
    o = [cyl("pole", 0.025, 1.75, (0, 0, 0), w, n=8), cyl("base", 0.2, 0.04, (0, 0, 0), w, n=12)]
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        o.append(tube_path("hook%d" % k, [(0, 0, 1.6), (math.cos(a) * 0.15, math.sin(a) * 0.15, 1.7)], 0.015, w, n=5))
    o.append(B("coat", (0.36, 0.14, 0.7), (0.0, 0.12, 0.85), mat("coat_grey", "#5b6168"), bevel=0.05))
    return o


@prop("trash_bin", block=False)
def trash_bin():
    return [cyl("bin", 0.15, 0.36, (0, 0, 0), mat("steel", "steel_brushed"), n=14, r2=0.17)]


@prop("board_quota", block=False, mounted=True)
def board_quota():
    """Wall board with the quarterly quota chart (Godot fills the % on a Label3D)."""
    o = [B("board", (1.6, 0.04, 1.0), (0, 0.0, -0.5), mat("board_white", "#f4f4ee", rough=0.3), bevel=0.01)]
    o.append(B("frame", (1.66, 0.03, 1.06), (0, 0.01, -0.53), "frame_dark", bevel=0.01))
    for k in range(5):
        h = 0.15 + k * 0.12
        o.append(B("bar%d" % k, (0.18, 0.01, h), (-0.55 + k * 0.27, -0.025, -0.4), mat("bar_green", "#5f8c6a")))
    o.append(B("title", (1.2, 0.01, 0.08), (0, -0.025, 0.32), mat("title_blue", "#1f3a5f")))
    return o


@prop("wall_clock", block=False, mounted=True)
def wall_clock():
    o = [cyl("face", 0.2, 0.04, (0, 0, 0), mat("clock_face", "#f6f4ee"), n=24, rot=(D(90), 0, 0))]
    o.append(torus("rim", 0.2, 0.02, (0, -0.04, 0), mat("frame_dark", "dark"), rot=(D(90), 0, 0)))
    o.append(B("hand1", (0.012, 0.005, 0.15), (0, -0.045, 0), "black", rot=(0, D(-30), 0)))
    o.append(B("hand2", (0.016, 0.005, 0.1), (0, -0.045, 0), "black", rot=(0, D(70), 0)))
    for o_ in o:
        o_.location.y -= 0.0
    return o


def painting(img, w=1.2, frame=True):
    o = []
    h = w * 896 / 1200
    can = B("CANVAS", (w, 0.03, h), (0, -0.015, -h / 2), mat("art_" + img, "#ffffff", tex=img + ".jpg", rough=0.6))
    o.append(can)
    o.append(B("back", (w - 0.04, 0.03, h - 0.04), (0, 0.0, -h / 2 + 0.02), "frame_dark"))
    if frame:
        lamp = mat("EMIT_lamp", "#fff4d6")
        o.append(B("lamp", (0.4, 0.06, 0.04), (0, -0.12, h / 2 + 0.06), mat("brass", "brass", metal=0.8), bevel=0.01))
        o.append(B("lamparm", (0.03, 0.12, 0.03), (0, -0.06, h / 2 + 0.06), mat("brass", "brass", metal=0.8)))
    return o


def _painting_prop(nm, img, w):
    @prop(nm, block=False, mounted=True)
    def f():
        return painting(img, w)
    return f


_painting_prop("painting_kier", "art_wax_kier", 1.1)
_painting_prop("painting_tempers", "art_four_tempers", 1.5)
_painting_prop("painting_young_kier", "art_young_kier", 1.1)
_painting_prop("painting_massacre", "art_mdr_massacre", 1.3)
_painting_prop("painting_barbarity", "art_ricken_book", 1.1)
_painting_prop("painting_landscape", "art_petey_map", 1.2)


@prop("sign_compliance", block=False, mounted=True)
def sign_compliance():
    return [B("plate", (0.9, 0.03, 0.5), (0, -0.015, -0.25), mat("plate_navy", "#1f3a5f", rough=0.4), bevel=0.01),
            B("trim", (0.8, 0.01, 0.4), (0, -0.032, -0.2), mat("plate_line", "#c9a24a", metal=0.6))]


@prop("lumon_logo", block=False, mounted=True)
def lumon_logo():
    """The Lumon globe: concentric rings on a navy disc + a long nameplate."""
    o = []
    navy = mat("logo_navy", "#1f3a5f", rough=0.4)
    lt = mat("logo_light", "#9cc3e6", rough=0.3, emit="#9cc3e6", emit_strength=0.4)
    o.append(cyl("disc", 0.55, 0.04, (0, 0, 0.75), navy, n=40, rot=(D(90), 0, 0)))
    for k, s in enumerate((0.5, 0.38, 0.26)):
        o.append(torus("ring%d" % k, s, 0.018, (0, -0.045, 0.75), lt, n=32, rot=(D(90), 0, 0)))
    for k in range(3):
        o.append(torus("mer%d" % k, 0.5, 0.012, (0, -0.045, 0.75), lt, n=32,
                       rot=(D(90), D(-60 + k * 60), 0)))
    o.append(B("plate", (2.4, 0.04, 0.28), (0, -0.02, -0.05), navy, bevel=0.01))
    return o


# ============================================================================ break room / offices
@prop("break_table")
def break_table():
    w = mat("table_white", "#e9ebe6", rough=0.35)
    return [B("top", (0.9, 0.7, 0.04), (0, 0, 0.72), w, bevel=0.01),
            cyl("leg", 0.04, 0.72, (0, 0, 0), mat("steel", "steel_brushed"), n=10),
            cyl("foot", 0.25, 0.03, (0, 0, 0), mat("steel", "steel_brushed"), n=16)]


@prop("chair_simple", pad=-0.1)
def chair_simple():
    m = mat("chair_shell", "#c9cec8", rough=0.45)
    st = mat("steel", "steel_brushed")
    o = [B("seat", (0.44, 0.42, 0.05), (0, 0, 0.44), m, bevel=0.02),
         B("back", (0.42, 0.04, 0.4), (0, 0.2, 0.5), m, bevel=0.02, rot=(D(-6), 0, 0))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(B("leg%d%d" % (sx, sy), (0.03, 0.03, 0.44), (sx * 0.19, sy * 0.18, 0), st))
    return o


@prop("exec_desk")
def exec_desk():
    w = mat("wood", "#ffffff", tex="wood", tile=1.2)
    o = [B("top", (1.7, 0.85, 0.05), (0, 0, 0.73), w, bevel=0.015)]
    for sx in (-1, 1):
        o.append(B("ped%d" % sx, (0.45, 0.75, 0.73), (sx * 0.6, 0, 0), w, bevel=0.01))
        for k in range(3):
            o.append(B("dr%d%d" % (sx, k), (0.18, 0.02, 0.025), (sx * 0.6, -0.385, 0.15 + k * 0.22),
                       mat("brass", "brass", metal=0.8)))
    o.append(B("modesty", (0.8, 0.03, 0.5), (0, -0.3, 0.2), w))
    # green banker's lamp + phone + papers
    o.append(cyl("lampbase", 0.07, 0.03, (0.55, 0.15, 0.78), mat("brass", "brass", metal=0.8), n=12))
    o.append(cyl("lampst", 0.012, 0.28, (0.55, 0.15, 0.8), mat("brass", "brass", metal=0.8), n=6))
    o.append(B("shade", (0.3, 0.12, 0.07), (0.55, 0.12, 1.06), mat("shade_green", "#2f6b47", rough=0.3), bevel=0.03))
    o.append(B("phone", (0.2, 0.18, 0.07), (-0.5, 0.1, 0.78), "black", bevel=0.02))
    o.append(B("papers", (0.3, 0.22, 0.02), (-0.05, -0.05, 0.78), "paper", rot=(0, 0, D(8))))
    return o


@prop("chair_exec", pad=-0.1)
def chair_exec():
    l = mat("leather", "#3b2a22", rough=0.55)
    o = [B("seat", (0.56, 0.52, 0.12), (0, 0, 0.4), l, bevel=0.05),
         B("back", (0.54, 0.12, 0.72), (0, 0.24, 0.48), l, bevel=0.05, rot=(D(-8), 0, 0)),
         cyl("post", 0.03, 0.36, (0, 0, 0.05), mat("steel", "steel_brushed"), n=8),
         cyl("base", 0.3, 0.05, (0, 0, 0), mat("steel", "steel_brushed"), n=5)]
    return o


@prop("bookshelf")
def bookshelf():
    w = mat("darkwood", "darkwood")
    o = [B("back", (1.4, 0.04, 2.0), (0, 0.16, 0), w)]
    for sx in (-1, 1):
        o.append(B("side%d" % sx, (0.04, 0.36, 2.0), (sx * 0.68, 0, 0), w))
    r = rnd(9)
    cols = ["#7a2e2e", "#2e4a7a", "#3d6b45", "#b08a3a", "#5a3a6a", "#d8d2c0", "#26303a"]
    for k in range(5):
        z = 0.02 + k * 0.4
        o.append(B("shelf%d" % k, (1.32, 0.34, 0.03), (0, 0, z), w))
        x = -0.62
        while x < 0.58:
            bw = 0.035 + r.random() * 0.04
            bh = 0.24 + r.random() * 0.1
            o.append(B("book%d_%d" % (k, int(x * 100)), (bw, 0.24, bh), (x + bw / 2, 0.0, z + 0.03),
                       mat("book_" + cols[int(r.random() * len(cols))].lstrip("#"),
                           cols[int(r.random() * len(cols))])))
            x += bw + 0.004
    return o


@prop("couch")
def couch():
    f = mat("fabric_green", "#3f6a4c", rough=0.95)
    o = [B("base", (1.9, 0.85, 0.42), (0, 0, 0.08), f, bevel=0.06),
         B("back", (1.9, 0.22, 0.45), (0, 0.32, 0.45), f, bevel=0.07)]
    for sx in (-1, 1):
        o.append(B("arm%d" % sx, (0.2, 0.85, 0.3), (sx * 0.86, 0, 0.42), f, bevel=0.07))
    for sx in (-0.45, 0.45):
        o.append(B("cush%f" % sx, (0.86, 0.66, 0.12), (sx, -0.06, 0.48), f, bevel=0.05))
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(B("ft%d%d" % (sx, sy), (0.06, 0.06, 0.08), (sx * 0.85, sy * 0.35, 0), "darkwood"))
    return o


@prop("armchair")
def armchair():
    up = mat("fabric_cream", "#d8ccb0", rough=0.95)
    w = mat("wood", "#ffffff", tex="wood", tile=1.2)
    o = [B("seat", (0.72, 0.7, 0.16), (0, 0, 0.32), up, bevel=0.05),
         B("back", (0.72, 0.16, 0.62), (0, 0.29, 0.42), up, bevel=0.06, rot=(D(-6), 0, 0))]
    for sx in (-1, 1):
        o.append(B("arm%d" % sx, (0.1, 0.7, 0.08), (sx * 0.38, 0.0, 0.58), w, bevel=0.02))
        o.append(B("armp%d" % sx, (0.06, 0.06, 0.26), (sx * 0.38, -0.3, 0.32), w))
        for sy in (-1, 1):
            o.append(B("leg%d%d" % (sx, sy), (0.06, 0.06, 0.32), (sx * 0.32, sy * 0.3, 0), w))
    return o


@prop("side_table")
def side_table():
    w = mat("wood", "#ffffff", tex="wood", tile=1.2)
    o = [cyl("top", 0.28, 0.04, (0, 0, 0.55), w, n=20), cyl("leg", 0.04, 0.55, (0, 0, 0), w, n=8),
         cyl("foot", 0.2, 0.03, (0, 0, 0), w, n=14)]
    o.append(cyl("cup", 0.04, 0.08, (0.08, 0.02, 0.59), "plastic_white", n=10))
    o.append(B("cards", (0.14, 0.1, 0.02), (-0.07, -0.05, 0.59), "paper", rot=(0, 0, D(12))))
    return o


@prop("floor_lamp", block=False)
def floor_lamp():
    return [cyl("base", 0.17, 0.03, (0, 0, 0), mat("brass", "brass", metal=0.8), n=16),
            cyl("pole", 0.015, 1.45, (0, 0, 0.03), mat("brass", "brass", metal=0.8), n=6),
            cyl("shade", 0.22, 0.3, (0, 0, 1.4), mat("EMIT_lamp", "#fff4d6"), n=18, r2=0.14, cap=False)]


@prop("rug", block=False)
def rug():
    o = [B("rug", (2.6, 1.8, 0.012), (0, 0, 0), mat("rug_red", "#7a3b2e", rough=1.0))]
    o.append(B("rug_in", (2.2, 1.4, 0.014), (0, 0, 0), mat("rug_cream", "#c9b58f", rough=1.0)))
    o.append(B("rug_c", (1.6, 0.8, 0.016), (0, 0, 0), mat("rug_red", "#7a3b2e", rough=1.0)))
    return o


# ============================================================================ Perpetual Wing
@prop("pedestal")
def pedestal():
    m = mat("marble_ped", "#d9d4c9", rough=0.3)
    return [B("base", (1.0, 1.0, 0.12), (0, 0, 0), m, bevel=0.02), B("mid", (0.85, 0.85, 0.28), (0, 0, 0.12), m),
            B("top", (0.95, 0.95, 0.06), (0, 0, 0.4), m, bevel=0.02),
            B("plaque", (0.36, 0.02, 0.12), (0, -0.43, 0.18), mat("brass", "brass", metal=0.8))]


@prop("rope_line", block=True)
def rope_line():
    o = []
    br = mat("brass", "brass", metal=0.8)
    red = mat("velvet", "#8a1c24", rough=0.8)
    xs = [-4.6, -1.8, 1.8, 4.6]
    for k, x in enumerate(xs):
        o.append(cyl("post%d" % k, 0.035, 0.9, (x, 0, 0.04), br, n=8))
        o.append(cyl("pbase%d" % k, 0.14, 0.04, (x, 0, 0), br, n=14))
        o.append(sphere("pball%d" % k, 0.05, (x, 0, 0.95), br, seg=8, rings=6))
    for k in range(len(xs) - 1):
        a, b = xs[k], xs[k + 1]
        pts = [(a + (b - a) * t, 0, 0.88 - 0.18 * math.sin(math.pi * t)) for t in [i / 8 for i in range(9)]]
        o.append(tube_path("rope%d" % k, pts, 0.022, red, n=6))
    return o


@prop("display_case")
def display_case():
    w = mat("darkwood", "darkwood")
    o = [B("base", (1.0, 0.6, 0.9), (0, 0, 0), w, bevel=0.02),
         B("glass", (0.94, 0.54, 0.4), (0, 0, 0.9), mat("glass", "#a9d6e0", rough=0.05, alpha=0.35)),
         B("lid", (1.0, 0.6, 0.03), (0, 0, 1.3), w)]
    # Kier's spectacles and a hairbrush on velvet
    o.append(B("velvet", (0.9, 0.5, 0.02), (0, 0, 0.9), mat("velvet", "#8a1c24", rough=0.8)))
    for sx in (-1, 1):
        o.append(torus("spec%d" % sx, 0.045, 0.006, (sx * 0.06 - 0.15, 0, 0.93), mat("brass", "brass", metal=0.8)))
    o.append(B("brush", (0.2, 0.06, 0.03), (0.2, 0.05, 0.92), w))
    return o


@prop("bench")
def bench():
    w = mat("wood", "#ffffff", tex="wood", tile=1.2)
    o = [B("seat", (1.6, 0.45, 0.06), (0, 0, 0.42), w, bevel=0.015)]
    for sx in (-1, 1):
        o.append(B("leg%d" % sx, (0.06, 0.4, 0.42), (sx * 0.7, 0, 0), mat("steel", "steel_brushed")))
    return o


# ============================================================================ restroom / orientation
@prop("stall_row")
def stall_row():
    """Three stalls against the wall; the middle door stands ajar (the book hides there)."""
    o = []
    p = mat("stall_panel", "#b7c4c1", rough=0.4)
    for k in range(4):
        x = -2.1 + k * 1.4
        o.append(B("wall%d" % k, (0.05, 1.4, 1.8), (x, 0.7, 0.15), p, bevel=0.01))
    for k in range(3):
        x = -1.4 + k * 1.4
        door = B("door%d" % k, (1.25, 0.04, 1.75), (x, 0.0, 0.15), p, bevel=0.01,
                 rot=(0, 0, D(-35) if k == 2 else 0))
        o.append(door)
        o.append(cyl("bowl%d" % k, 0.2, 0.42, (x, 1.05, 0), "plastic_white", n=14, r2=0.17))
        o.append(B("tank%d" % k, (0.4, 0.18, 0.35), (x, 1.32, 0.42), "plastic_white", bevel=0.03))
    return o


@prop("sink_counter")
def sink_counter():
    o = [B("counter", (0.55, 2.2, 0.85), (0, 0, 0), mat("counter_grey", "#9ea7a6", rough=0.35), bevel=0.01)]
    for k in (-0.6, 0.6):
        o.append(cyl("basin%f" % k, 0.18, 0.04, (0.02, k, 0.85), "plastic_white", n=16))
        o.append(cyl("tap%f" % k, 0.015, 0.2, (0.2, k, 0.85), mat("steel", "steel_brushed"), n=6))
    o.append(B("mirror", (0.03, 2.0, 0.8), (0.27, 0, 1.15), mat("mirror", "#c9dde6", rough=0.05, metal=0.8)))
    return o


@prop("conf_table")
def conf_table():
    w = mat("wood", "#ffffff", tex="wood", tile=1.2)
    o = [B("top", (3.2, 1.2, 0.06), (0, 0, 0.72), w, bevel=0.02)]
    for sx in (-1, 1):
        o.append(B("leg%d" % sx, (0.12, 0.9, 0.72), (sx * 1.3, 0, 0), w))
    return o


# ============================================================================ O&D
@prop("printer3d")
def printer3d():
    """O&D's fabrication printer: a cabinet with a glass hood, a print head and a temperature dial."""
    o = []
    body = mat("printer_body", "#d7d2c2", rough=0.45)
    o.append(B("cab", (1.3, 0.8, 0.8), (0, 0, 0), body, bevel=0.03))
    o.append(B("hood", (1.2, 0.7, 0.62), (0, 0, 0.8), mat("glass", "#a9d6e0", rough=0.05, alpha=0.35)))
    o.append(B("roof", (1.3, 0.8, 0.06), (0, 0, 1.42), body, bevel=0.02))
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(B("post%d%d" % (sx, sy), (0.05, 0.05, 0.62), (sx * 0.62, sy * 0.37, 0.8), "metal"))
    o.append(B("rail", (1.1, 0.04, 0.04), (0, 0, 1.3), mat("steel", "steel_brushed")))
    o.append(B("ANIM_head", (0.14, 0.14, 0.14), (0, 0, 1.16), mat("head_orange", "#e07a30"), bevel=0.02))
    o.append(B("bed", (0.9, 0.5, 0.03), (0, 0, 0.82), "metal"))
    o.append(B("EMIT_screen", (0.32, 0.02, 0.2), (0.35, -0.405, 0.45), mat("EMIT_screen", "#0d2a24")))
    o.append(cyl("dial", 0.08, 0.04, (-0.3, -0.42, 0.5), "red_mark", n=16, rot=(D(90), 0, 0)))
    return o


@prop("drafting_table")
def drafting_table():
    w = mat("wood_light", "#ffffff", tex="wood_light", tile=1.2)
    o = [B("board", (1.1, 0.8, 0.04), (0, 0, 0.9), w, bevel=0.01, rot=(D(18), 0, 0))]
    for sx in (-1, 1):
        o.append(B("leg%d" % sx, (0.05, 0.6, 0.9), (sx * 0.48, 0.05, 0), "metal"))
    o.append(B("sheet", (0.7, 0.5, 0.01), (0, -0.02, 0.95), "paper", rot=(D(18), 0, 0)))
    o.append(B("ruler", (0.8, 0.04, 0.01), (0, -0.2, 0.9), mat("ruler", "#c9a24a"), rot=(D(18), 0, 0)))
    o.append(B("stool", (0.35, 0.35, 0.6), (0.0, -0.75, 0), mat("stool", "#5f8c6a"), bevel=0.05))
    return o


@prop("shelf_art")
def shelf_art():
    w = mat("wood_light", "#ffffff", tex="wood_light", tile=1.2)
    o = [B("back", (2.0, 0.04, 1.6), (0, 0.2, 0), w)]
    for k in range(3):
        o.append(B("sh%d" % k, (2.0, 0.4, 0.04), (0, 0, 0.2 + k * 0.6), w))
    r = rnd(3)
    for k in range(3):
        for j in range(4):
            x = -0.75 + j * 0.5
            c = ["#c9a24a", "#5f8c6a", "#b3262b", "#e9ece6", "#1f3a5f"][int(r.random() * 5)]
            if (j + k) % 2:
                o.append(sphere("orb%d%d" % (k, j), 0.1, (x, 0, 0.34 + k * 0.6), mat("art_" + c.lstrip("#"), c), seg=10,
                                rings=8))
            else:
                o.append(B("bust%d%d" % (k, j), (0.14, 0.14, 0.22), (x, 0, 0.24 + k * 0.6),
                           mat("art_" + c.lstrip("#"), c), bevel=0.03))
    return o


@prop("sculpture")
def sculpture():
    m = mat("marble_ped", "#d9d4c9", rough=0.3)
    o = [B("plinth", (0.6, 0.6, 0.9), (0, 0, 0), m, bevel=0.02)]
    # an abstract Kier head: stacked spheres
    o.append(sphere("bust", 0.22, (0, 0, 1.12), mat("bronze", "#8a6a3a", metal=0.7, rough=0.35), scale=(1, 0.9, 1.2)))
    o.append(B("shoulders", (0.5, 0.25, 0.2), (0, 0, 0.9), mat("bronze", "#8a6a3a", metal=0.7, rough=0.35), bevel=0.08))
    return o


# ============================================================================ security / kitchen
@prop("monitor_wall")
def monitor_wall():
    """3x3 CCTV monitors in a steel frame (each screen is EMIT_screen_<n> for the camera feed shader)."""
    o = [B("frame", (3.2, 0.45, 2.1), (0, 0.25, 0.0), mat("monitor_frame", "#3a3f42", rough=0.5), bevel=0.02)]
    for r in range(3):
        for c in range(3):
            x = -1.0 + c * 1.0
            z = 0.25 + r * 0.62
            o.append(B("bez%d%d" % (r, c), (0.92, 0.06, 0.56), (x, 0.0, z), mat("crt_bezel", "#2b302d"), bevel=0.02))
            o.append(B("EMIT_screen_%d" % (r * 3 + c), (0.8, 0.01, 0.46), (x, -0.035, z + 0.05),
                       mat("EMIT_screen_blue", "#0d1a2a")))
    return o


@prop("security_desk")
def security_desk():
    m = mat("sec_desk", "#5a6266", rough=0.5)
    o = [B("desk", (2.6, 0.8, 0.74), (0, 0, 0), m, bevel=0.02),
         B("top", (2.7, 0.9, 0.04), (0, 0, 0.74), mat("desk_top", "#eef0ea", rough=0.4), bevel=0.01)]
    o.append(B("console", (1.2, 0.3, 0.08), (0, 0.15, 0.78), "black", bevel=0.02))
    for k in range(8):
        o.append(B("btn%d" % k, (0.06, 0.06, 0.02), (-0.45 + k * 0.13, 0.12, 0.86),
                   mat("EMIT_green" if k % 3 else "EMIT_red", "#103a1a")))
    o.append(B("mic", (0.03, 0.03, 0.25), (0.8, 0.1, 0.78), "metal"))
    return o


@prop("lockers")
def lockers():
    m = mat("locker", "#6f7d86", rough=0.45, metal=0.3)
    o = []
    for k in range(4):
        x = -0.9 + k * 0.6
        o.append(B("lk%d" % k, (0.58, 0.5, 1.9), (x, 0, 0), m, bevel=0.01))
        for j in range(3):
            o.append(B("vent%d%d" % (k, j), (0.3, 0.01, 0.02), (x, -0.255, 1.6 + j * 0.05), "black"))
        o.append(B("hdl%d" % k, (0.03, 0.03, 0.12), (x + 0.2, -0.26, 1.0), mat("steel", "steel_brushed")))
    return o


@prop("keycard_box", block=False)
def keycard_box():
    o = [B("tray", (0.24, 0.16, 0.03), (0, 0, 0), "black", bevel=0.005)]
    o.append(B("INT_card", (0.086, 0.054, 0.006), (0, 0, 0.03), mat("card_red", "#b3262b", rough=0.3)))
    o.append(B("stripe", (0.086, 0.012, 0.007), (0, 0.012, 0.031), "black"))
    return o


@prop("kitchen_counter")
def kitchen_counter():
    m = mat("counter_base", "#c9cec8", rough=0.45)
    o = [B("base", (5.0, 0.62, 0.88), (0, 0, 0), m, bevel=0.01),
         B("top", (5.05, 0.66, 0.04), (0, 0, 0.88), mat("counter_top", "#3d4245", rough=0.3))]
    for k in range(6):
        o.append(B("door%d" % k, (0.78, 0.02, 0.7), (-2.08 + k * 0.83, -0.32, 0.08), m, bevel=0.005))
    o.append(cyl("sink", 0.2, 0.03, (1.3, 0, 0.9), mat("steel", "steel_brushed"), n=16))
    return o


@prop("coffee_machine", block=False)
def coffee_machine():
    o = [B("body", (0.32, 0.36, 0.42), (0, 0, 0), "black", bevel=0.03)]
    o.append(cyl("pot", 0.08, 0.14, (0, -0.1, 0.02), mat("glass", "#a9d6e0", rough=0.05, alpha=0.35), n=12))
    o.append(B("EMIT_red", (0.04, 0.01, 0.02), (0.1, -0.185, 0.33), mat("EMIT_red", "#5a1010")))
    return o


@prop("fridge")
def fridge():
    m = mat("fridge", "#e3e6e1", rough=0.35)
    return [B("body", (0.75, 0.7, 1.85), (0, 0, 0), m, bevel=0.04),
            B("hdl", (0.04, 0.05, 0.5), (0.28, -0.37, 0.9), mat("steel", "steel_brushed")),
            B("split", (0.72, 0.01, 0.02), (0, -0.355, 1.25), "black")]


@prop("kitchen_table")
def kitchen_table():
    return [B("top", (1.2, 0.8, 0.04), (0, 0, 0.72), mat("table_white", "#e9ebe6", rough=0.35), bevel=0.01),
            cyl("leg", 0.05, 0.72, (0, 0, 0), mat("steel", "steel_brushed"), n=10),
            cyl("foot", 0.3, 0.03, (0, 0, 0), mat("steel", "steel_brushed"), n=16)]


@prop("vending")
def vending():
    o = [B("body", (0.9, 0.8, 1.9), (0, 0, 0), mat("vend", "#1f3a5f", rough=0.4), bevel=0.02),
         B("window", (0.6, 0.02, 1.2), (-0.1, -0.405, 0.55), mat("glass", "#a9d6e0", rough=0.05, alpha=0.35))]
    for r in range(5):
        for c in range(4):
            col = ["#c9a24a", "#b3262b", "#5f8c6a", "#e9ece6"][(r + c) % 4]
            o.append(B("snack%d%d" % (r, c), (0.1, 0.1, 0.15), (-0.32 + c * 0.15, -0.32, 0.6 + r * 0.23),
                       mat("snack_" + col.lstrip("#"), col)))
    o.append(B("EMIT_screen", (0.16, 0.01, 0.1), (0.3, -0.41, 1.3), mat("EMIT_screen", "#0d2a24")))
    return o


@prop("water_fountain")
def water_fountain():
    return [B("basin", (0.45, 0.35, 0.25), (0, 0, 0.75), mat("steel", "steel_brushed"), bevel=0.04),
            B("post", (0.2, 0.15, 0.75), (0, 0.08, 0), mat("steel", "steel_brushed"))]


@prop("fire_ext", block=False)
def fire_ext():
    return [cyl("tank", 0.08, 0.45, (0, -0.1, 0.25), "red_mark", n=12),
            B("bracket", (0.2, 0.05, 0.3), (0, -0.02, 0.35), "metal")]


# ============================================================================ lobby / elevators
def elevator_doors(red=False):
    o = []
    frame = mat("elev_frame", "#cfd4d6", rough=0.3, metal=0.5)
    o.append(B("frame", (2.0, 0.25, 2.55), (0, 0.12, 0), frame, bevel=0.02))
    o.append(B("recess", (1.5, 0.05, 2.25), (0, -0.01, 0.0), "black"))
    st = mat("steel", "steel_brushed")
    o.append(B("INT_door_L", (0.73, 0.05, 2.2), (-0.37, -0.03, 0.02), st, bevel=0.005))
    o.append(B("INT_door_R", (0.73, 0.05, 2.2), (0.37, -0.03, 0.02), st, bevel=0.005))
    o.append(B("indicator", (0.4, 0.04, 0.12), (0, -0.02, 2.35), "black", bevel=0.01))
    o.append(B("EMIT_arrow", (0.1, 0.01, 0.06), (0, -0.045, 2.38), mat("EMIT_red" if red else "EMIT_green", "#103a1a")))
    o.append(B("callbox", (0.12, 0.04, 0.22), (0.95, -0.04, 1.05), st, bevel=0.01))
    o.append(B("EMIT_call", (0.05, 0.01, 0.05), (0.95, -0.062, 1.1), mat("EMIT_lamp", "#fff4d6")))
    if red:
        o.append(B("stripe", (2.05, 0.03, 0.16), (0, -0.02, 2.5), "red_mark"))
        o.append(B("stripe2", (0.16, 0.03, 2.5), (-0.95, -0.02, 0), "red_mark"))
        o.append(B("stripe3", (0.16, 0.03, 2.5), (0.95, -0.02, 0), "red_mark"))
        o.append(B("reader", (0.14, 0.05, 0.2), (-1.12, -0.04, 1.0), "black", bevel=0.01))
        o.append(B("EMIT_reader", (0.08, 0.01, 0.03), (-1.12, -0.07, 1.12), mat("EMIT_red", "#5a1010")))
    return o


@prop("elevator", block=True)
def elevator():
    return elevator_doors(False)


@prop("red_elevator", block=True)
def red_elevator():
    return elevator_doors(True)


@prop("door_lock", block=False)
def door_lock():
    """Sliding steel panel for a locked doorway (width 2 m; scaled in Godot) + keycard reader."""
    st = mat("door_panel", "#9aa4ad", rough=0.35, metal=0.5)
    return [B("INT_door_L", (1.0, 0.12, 2.3), (-0.5, 0, 0), st, bevel=0.01),
            B("INT_door_R", (1.0, 0.12, 2.3), (0.5, 0, 0), st, bevel=0.01),
            B("win_L", (0.3, 0.13, 0.5), (-0.5, 0, 1.4), "black"), B("win_R", (0.3, 0.13, 0.5), (0.5, 0, 1.4), "black")]


# ============================================================================ waffle room
@prop("waffle_table")
def waffle_table():
    w = mat("darkwood", "darkwood")
    o = [B("top", (1.6, 0.9, 0.06), (0, 0, 0.72), w, bevel=0.02)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(B("leg%d%d" % (sx, sy), (0.08, 0.08, 0.72), (sx * 0.7, sy * 0.36, 0), w))
    wf = mat("waffle", "#d9a04a", rough=0.7)
    for k in range(7):
        o.append(B("waffle%d" % k, (0.3, 0.3, 0.035), (0, 0, 0.78 + k * 0.04), wf, bevel=0.01, rot=(0, 0, D(k * 9))))
    o.append(B("plate", (0.4, 0.4, 0.02), (0, 0, 0.78), "plastic_white", bevel=0.01))
    o.append(cyl("syrup", 0.05, 0.18, (0.4, 0.1, 0.78), mat("syrup", "#8a4a1a", rough=0.2), n=10))
    o.append(B("cream", (0.15, 0.15, 0.1), (-0.4, -0.1, 0.78), "plastic_white", bevel=0.04))
    o.append(cyl("berry", 0.04, 0.03, (-0.45, 0.15, 0.78), "red_mark", n=8))
    return o


@prop("cabin_bed")
def cabin_bed():
    w = mat("darkwood", "darkwood")
    return [B("frame", (1.2, 2.0, 0.35), (0, 0, 0), w, bevel=0.02),
            B("matt", (1.1, 1.9, 0.2), (0, 0, 0.35), mat("sheet", "#efe8d8"), bevel=0.06),
            B("quilt", (1.12, 1.2, 0.08), (0, -0.35, 0.52), mat("quilt", "#7a2e2e"), bevel=0.04),
            B("head", (1.2, 0.08, 0.9), (0, 0.98, 0), w, bevel=0.02),
            B("pillow", (0.6, 0.35, 0.12), (0, 0.7, 0.55), mat("sheet", "#efe8d8"), bevel=0.05)]


@prop("fireplace")
def fireplace():
    st = mat("hearth_stone", "#8a8178", rough=0.9)
    o = [B("body", (1.8, 0.5, 1.3), (0, 0.15, 0), st, bevel=0.03),
         B("hole", (1.0, 0.1, 0.75), (0, -0.12, 0.08), "black"),
         B("mantel", (2.0, 0.6, 0.1), (0, 0.1, 1.3), "darkwood")]
    for k in range(3):
        o.append(cyl("log%d" % k, 0.07, 0.6, (-0.2 + k * 0.2, -0.05, 0.15), mat("log", "#5a3a22"), n=8,
                     rot=(0, D(90), D(20 * k))))
    o.append(sphere("ANIM_fire", 0.22, (0, -0.1, 0.3), mat("EMIT_fire", "#ff8a30"), scale=(1.4, 0.6, 1.2), seg=10, rings=8))
    return o


@prop("candles", block=False)
def candles():
    o = [cyl("holder", 0.1, 0.05, (0, 0, 0), mat("brass", "brass", metal=0.8), n=12)]
    for k in range(3):
        x = -0.06 + k * 0.06
        h = 0.18 + k * 0.05
        o.append(cyl("c%d" % k, 0.022, h, (x, 0, 0.05), mat("wax", "#f2ead8"), n=8))
        o.append(sphere("f%d" % k, 0.014, (x, 0, 0.07 + h), mat("EMIT_fire", "#ff8a30"), scale=(1, 1, 1.8), seg=6, rings=4))
    return o


# ============================================================================ testing floor
@prop("goat_fence", block=False)
def goat_fence():
    """Low wooden pen 9 x 6 m with a gate gap on the south side (Godot blocks cells along it)."""
    w = mat("fence_wood", "#c9b48c", rough=0.9)
    o = []
    W, H = 9.0, 6.0
    segs = [((-W / 2, -H / 2), (-1.0, -H / 2)), ((1.0, -H / 2), (W / 2, -H / 2)), ((W / 2, -H / 2), (W / 2, H / 2)),
            ((W / 2, H / 2), (-W / 2, H / 2)), ((-W / 2, H / 2), (-W / 2, -H / 2))]
    # Blender: plan y south = -Y; the gate is on the south side -> Blender y = -H/2 flipped below
    for k, ((x0, y0), (x1, y1)) in enumerate(segs):
        y0, y1 = -y0 * -1, -y1 * -1
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / 1.2))
        for i in range(n + 1):
            t = i / n
            o.append(B("post%d_%d" % (k, i), (0.08, 0.08, 0.8), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0), w))
        a = math.atan2(y1 - y0, x1 - x0)
        for z in (0.35, 0.65):
            o.append(B("rail%d_%f" % (k, z), (L, 0.05, 0.08), ((x0 + x1) / 2, (y0 + y1) / 2, z), w, rot=(0, 0, a)))
    return o


@prop("hay_bale")
def hay_bale():
    return [B("bale", (1.0, 0.55, 0.45), (0, 0, 0), mat("hay", "#ffffff", tex="hay", tile=0.8), bevel=0.05),
            B("tie1", (0.02, 0.57, 0.47), (-0.25, 0, 0), mat("twine", "#7a5a2a")),
            B("tie2", (0.02, 0.57, 0.47), (0.25, 0, 0), mat("twine", "#7a5a2a"))]


@prop("trough")
def trough():
    w = mat("fence_wood", "#c9b48c", rough=0.9)
    return [B("box", (1.6, 0.5, 0.4), (0, 0, 0), w, bevel=0.02),
            B("milk", (1.45, 0.38, 0.05), (0, 0, 0.32), mat("milk", "#f6f3ea", rough=0.2))]


@prop("tree_small")
def tree_small():
    o = [cyl("trunk", 0.1, 1.4, (0, 0, 0), mat("bark", "#6a4a32"), n=10, r2=0.07)]
    for k, (x, y, z, r) in enumerate([(0, 0, 1.7, 0.55), (0.3, 0.1, 1.5, 0.4), (-0.3, -0.1, 1.55, 0.42),
                                      (0.05, -0.25, 1.95, 0.38)]):
        o.append(sphere("crown%d" % k, r, (x, y, z), "leaf" if k % 2 else "leaf2", seg=10, rings=8))
    return o


@prop("milk_crate")
def milk_crate():
    o = [B("crate", (0.5, 0.36, 0.3), (0, 0, 0), mat("crate_blue", "#3a6fa8"), bevel=0.02)]
    for k in range(6):
        x = -0.16 + (k % 3) * 0.16
        y = -0.08 + (k // 3) * 0.16
        o.append(cyl("bottle%d" % k, 0.045, 0.2, (x, y, 0.2), mat("milk", "#f6f3ea", rough=0.2), n=10))
        o.append(cyl("nipple%d" % k, 0.025, 0.05, (x, y, 0.4), mat("rubber", "#d98a5a"), n=8))
    return o


@prop("tent")
def tent():
    """The white testing tent with a cot inside (the flap faces south)."""
    c = mat("tent_cloth", "#eeeeea", rough=0.95)
    o = [pyramid("tent", 3.6, 3.6, 2.4, m=c), cyl("pole", 0.03, 2.5, (0, 0, 0), "metal", n=6)]
    o.append(prism("flap", [(-0.5, 0), (0.5, 0), (0, 1.5)], 0.02, (0, -1.82, 0), mat("tent_dark", "#2a2d30"), axis="Y"))
    return o


@prop("lab_bench")
def lab_bench():
    o = [B("bench", (2.0, 0.7, 0.9), (0, 0, 0), mat("lab_white", "#eef0ea", rough=0.35), bevel=0.01)]
    for k in range(4):
        o.append(cyl("flask%d" % k, 0.05, 0.18, (-0.6 + k * 0.4, 0, 0.9), mat("glass", "#a9d6e0", rough=0.05, alpha=0.35),
                     n=10, r2=0.02))
    o.append(B("EMIT_screen", (0.4, 0.02, 0.28), (0.6, 0.2, 1.05), mat("EMIT_screen", "#0d2a24")))
    return o


@prop("server_rack")
def server_rack():
    o = [B("rack", (0.7, 0.8, 2.0), (0, 0, 0), mat("rack", "#2b2f33", rough=0.5), bevel=0.01)]
    for k in range(8):
        o.append(B("unit%d" % k, (0.62, 0.02, 0.16), (0, -0.405, 0.2 + k * 0.22), "black"))
        o.append(B("led%d" % k, (0.03, 0.01, 0.03), (0.22, -0.42, 0.26 + k * 0.22),
                   mat("EMIT_green" if k % 3 else "EMIT_red", "#103a1a")))
    return o


@prop("cryo_pod")
def cryo_pod():
    o = [cyl("base", 0.5, 0.25, (0, 0, 0), mat("pod_white", "#e3e8ea", rough=0.3), n=20),
         cyl("glass", 0.42, 1.8, (0, 0, 0.25), mat("EMIT_cryo", "#1a3a4a"), n=20),
         cyl("cap", 0.5, 0.25, (0, 0, 2.05), mat("pod_white", "#e3e8ea", rough=0.3), n=20),
         B("label", (0.3, 0.02, 0.1), (0, -0.5, 0.12), "black")]
    return o


@prop("cryo_console")
def cryo_console():
    o = [B("desk", (0.6, 1.4, 0.95), (0, 0, 0), mat("sec_desk", "#5a6266", rough=0.5), bevel=0.02),
         B("EMIT_screen", (0.02, 0.9, 0.5), (0.32, 0, 1.0), mat("EMIT_screen_blue", "#0d1a2a")),
         B("keypad", (0.2, 0.3, 0.04), (0.15, 0.4, 0.95), "black", bevel=0.01)]
    return o


@prop("otc_switch")
def otc_switch():
    """Wall cabinet with a big red lever; INT_lever pivots at its axle (rotates about X)."""
    o = [B("box", (0.8, 0.3, 1.0), (0, 0.0, 0.8), mat("otc_box", "#c9cec8", rough=0.4), bevel=0.02),
         B("stripe", (0.82, 0.31, 0.08), (0, 0.0, 1.62), "red_mark"),
         B("slot", (0.08, 0.02, 0.6), (0, -0.155, 1.0), "black")]
    lever = cyl("INT_lever", 0.035, 0.45, (0, -0.2, 1.3), mat("steel", "steel_brushed"), n=8)
    o.append(lever)
    o.append(sphere("knob", 0.07, (0, -0.2, 1.75), "red_mark", seg=10, rings=8))
    o.append(B("EMIT_red", (0.1, 0.01, 0.05), (0.28, -0.155, 1.55), mat("EMIT_red", "#5a1010")))
    return o


# ============================================================================ pickups (small, Godot spins them)
@prop("map_piece", block=False)
def map_piece():
    return [B("paper", (0.3, 0.22, 0.01), (0, 0, 0.01), mat("art_art_petey_map", "#ffffff", tex="art_petey_map.jpg"),
              rot=(0, 0, D(10)))]


@prop("book", block=False)
def book():
    return [B("cover", (0.16, 0.23, 0.04), (0, 0, 0), mat("book_orange", "#d0602a"), bevel=0.005),
            B("pages", (0.15, 0.22, 0.032), (0.006, 0, 0.004), "paper")]


# ============================================================================ build
def build_one(name):
    fn, meta = PROPS[name]
    reset()
    std_mats()
    coll = collection(name)
    objs = fn()
    for ob in objs:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
    keep = [o for o in objs if o.name in ("CANVAS",) or o.name.startswith(("EMIT_", "INT_", "ANIM_"))]
    root = finish_asset(objs, name, coll, keep_separate=keep)
    for o in keep:
        if o.name == "CANVAS" or o.name.startswith("EMIT_screen"):
            fit_uv(o)
    bpy.context.view_layer.update()
    mn, mx = R.bbox([c for c in root.children_recursive if c.type == "MESH"])
    INFO[name] = dict(min=[round(mn.x, 3), round(-mx.y, 3), round(mn.z, 3)],  # plan coords: y south = -Blender y
                      max=[round(mx.x, 3), round(-mn.y, 3), round(mx.z, 3)], **meta)
    export_gltf(root, os.path.join(ASSETS, "props", name + ".gltf"))
    if not NO_RENDER:
        R.setup_render((300, 300))
        R.world("#cfd4d2", 1.0)
        R.sun(energy=3.0, rot=(50, 0, 30))
        R.ground_plane(color="#b9bdb8")
        if meta["mounted"]:
            R.camera(loc=(1.2, -3.2, 0.3), target=(0, 0, -0.2 if name.startswith(("painting", "sign")) else 0.6),
                     lens=40)
            R.frame_objects([c for c in root.children_recursive if c.type == "MESH"], yaw=-20, pitch=10, lens=50)
        else:
            R.frame_objects([c for c in root.children_recursive if c.type == "MESH"], yaw=-35, pitch=30, lens=50)
        R.render(os.path.join(RENDERS, "props", name + ".png"))


def main():
    names = [n for n in PROPS if not ONLY or n in ONLY]
    info_path = os.path.join(ASSETS, "props", "props_info.json")
    if os.path.exists(info_path):
        INFO.update(json.load(open(info_path)))
    for n in names:
        build_one(n)
        print("built", n)
    os.makedirs(os.path.dirname(info_path), exist_ok=True)
    json.dump(INFO, open(info_path, "w"), indent=1, sort_keys=True)
    print("DONE", len(names))


if __name__ == "__main__":
    main()
