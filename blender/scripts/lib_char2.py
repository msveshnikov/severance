"""Semi-realistic humans for Severance: Lumon Office (v2).
Adult proportions (~7.3 heads, 1.76 m), small natural eyes, sculpted hair, tailored clothes with lapels, collars,
cuffs and buttons, hands with fingers. Same bone names and Poser API as lib_char, so the animation library works
unchanged (only the sitting hip offset differs). Rigid-segment skinning: each part follows one bone; joints are
hidden by overlapping spheres. Character faces -Y; its left is +X.
"""
import bpy
import math
from mathutils import Vector, Quaternion
from lib_geo import box, cyl, sphere, torus, tube_path, prism, mat
import lib_char as L1

FPS = 24
# ------------------------------------------------------------------ skeleton (armature space, rest)
SK = {
    "root": ((0, 0, 0), (0, 0, 0.12), None),
    "hips": ((0, 0, 0.96), (0, 0, 1.08), "root"),
    "spine": ((0, 0, 1.08), (0, 0, 1.24), "hips"),
    "chest": ((0, 0, 1.24), (0, 0, 1.44), "spine"),
    "neck": ((0, 0, 1.44), (0, 0, 1.53), "chest"),
    "head": ((0, 0, 1.53), (0, 0, 1.79), "neck"),
}
for s, sx in (("L", 1), ("R", -1)):
    SK.update({
        "clavicle_" + s: ((sx * 0.03, 0, 1.41), (sx * 0.16, 0, 1.42), "chest"),
        "upper_arm_" + s: ((sx * 0.185, 0, 1.40), (sx * 0.245, 0.01, 1.12), "clavicle_" + s),
        "forearm_" + s: ((sx * 0.245, 0.01, 1.12), (sx * 0.285, -0.01, 0.865), "upper_arm_" + s),
        "hand_" + s: ((sx * 0.285, -0.01, 0.865), (sx * 0.30, -0.02, 0.76), "forearm_" + s),
        "thigh_" + s: ((sx * 0.092, 0, 0.95), (sx * 0.092, 0, 0.52), "hips"),
        "shin_" + s: ((sx * 0.092, 0, 0.52), (sx * 0.092, 0.01, 0.09), "thigh_" + s),
        "foot_" + s: ((sx * 0.092, 0.01, 0.09), (sx * 0.092, -0.15, 0.025), "shin_" + s),
    })
ORDER = L1.ORDER
HEAD_C = Vector((0, 0, 1.635))     # head ellipsoid centre
HEAD_R = 0.104
FACE_Y = -0.098                     # front of the face
SIT_HIPS = Vector((0, 0.05, -0.43))


def V(t):
    return Vector(t)


def build_armature(name, coll):
    arm = bpy.data.armatures.new(name + "_rig")
    ob = bpy.data.objects.new(name + "_rig", arm)
    coll.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for bn in ORDER:
        h, t, p = SK[bn]
        eb = arm.edit_bones.new(bn)
        eb.head, eb.tail = V(h), V(t)
        eb.roll = 0
        if p:
            eb.parent = arm.edit_bones[p]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in ob.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return ob


Body = L1.Body
Poser = L1.Poser
Q = L1.Q


def M(name, col, rough=0.75, metal=0.0):
    return mat(name + "_" + col.lstrip("#"), col, rough=rough, metal=metal)


def skin(c):
    return mat("skin2_" + c.lstrip("#"), c, rough=0.62)


# ------------------------------------------------------------------ face
def face(B, sk, spec):
    hair_c = spec.get("hair_c", "#3a2a20")
    brow = M("brow", spec.get("brow_c", hair_c), 0.9)
    white = mat("eye_white2", "#eeeae4", rough=0.35)
    iris = M("iris", spec.get("eyes", "#4a3a2a"), 0.3)
    dark = mat("eye_dark2", "#1c1612", rough=0.4)
    lip = M("lip", spec.get("lip", "#b9786a"), 0.5)
    zc = HEAD_C.z
    ey = zc + 0.012          # eye line
    for sx in (-1, 1):
        x = sx * 0.036
        B.add(sphere("eyew%d" % sx, 0.0135, (x, FACE_Y + 0.006, ey), white, seg=10, rings=8, scale=(1.25, 0.6, 0.85)),
              "head")
        B.add(sphere("iris%d" % sx, 0.0072, (x, FACE_Y - 0.0005, ey), iris, seg=8, rings=6, scale=(1, 0.5, 1)), "head")
        B.add(sphere("pupil%d" % sx, 0.0036, (x, FACE_Y - 0.0035, ey), dark, seg=6, rings=4, scale=(1, 0.5, 1)), "head")
        # upper lid / lash line
        B.add(box("lid%d" % sx, (0.03, 0.006, 0.0045), (x, FACE_Y + 0.0025, ey + 0.0085), dark,
                  rot=(0, math.radians(sx * -6), 0)), "head")
        # brow
        bt = spec.get("brow_t", 0.006)
        B.add(box("brow%d" % sx, (0.034, 0.008, bt), (x + sx * 0.002, FACE_Y + 0.001, ey + 0.026), brow,
                  rot=(0, math.radians(sx * spec.get("brow_tilt", -7)), 0)), "head")
    # nose: bridge + tip + nostril wings
    B.add(sphere("nosebr", 0.011, (0, FACE_Y - 0.004, ey - 0.012), sk, seg=8, rings=6, scale=(0.9, 1.0, 2.2)), "head")
    B.add(sphere("nosetip", 0.0115, (0, FACE_Y - 0.009, zc - 0.026), sk, seg=10, rings=8, scale=(1.15, 1.0, 0.95)),
          "head")
    for sx in (-1, 1):
        B.add(sphere("nostril%d" % sx, 0.008, (sx * 0.011, FACE_Y - 0.004, zc - 0.033), sk, seg=8, rings=6), "head")
    # mouth: two lips
    my = zc - 0.058
    B.add(sphere("lipup", 0.018, (0, FACE_Y + 0.0, my + 0.004), lip, seg=10, rings=6, scale=(1.5, 0.35, 0.32)), "head")
    B.add(sphere("liplo", 0.017, (0, FACE_Y + 0.001, my - 0.004), lip, seg=10, rings=6, scale=(1.35, 0.4, 0.4)), "head")
    B.add(box("mouthline", (0.034, 0.004, 0.0018), (0, FACE_Y - 0.005, my), mat("mouth2", "#5a2e2a")), "head")
    # chin + jaw
    B.add(sphere("chin", 0.026, (0, FACE_Y + 0.026, zc - 0.084), sk, seg=12, rings=8,
                 scale=(1.15 * spec.get("jaw", 1.0), 0.8, 0.75)), "head")
    # ears
    for sx in (-1, 1):
        B.add(sphere("ear%d" % sx, 0.022, (sx * 0.098, 0.008, zc + 0.0), sk, seg=10, rings=8, scale=(0.35, 0.75, 1.2)),
              "head")
    if spec.get("mustache"):
        mm = M("hair", spec["mustache"], 0.9)
        B.add(sphere("must", 0.022, (0, FACE_Y - 0.004, my + 0.014), mm, seg=10, rings=6,
                     scale=(1.6 if spec.get("must_w", 1) else 1, 0.45, 0.42)), "head")
    if spec.get("beard"):
        bm = M("hair", spec["beard"], 0.9)
        B.add(sphere("beard", 0.06, (0, FACE_Y + 0.03, zc - 0.07), bm, seg=12, rings=8, scale=(1.25, 0.75, 1.0)), "head")
    if spec.get("stubble"):
        sm = M("stubble", spec["stubble"], 0.95)
        B.add(sphere("stub", 0.062, (0, FACE_Y + 0.045, zc - 0.062), sm, seg=14, rings=8, scale=(1.18, 0.82, 0.78)),
              "head")
    if spec.get("glasses"):
        gm = mat("glasses2", spec.get("glasses_c", "#2b2b30"), rough=0.3, metal=0.4)
        for sx in (-1, 1):
            B.add(torus("gl%d" % sx, 0.019, 0.0024, (sx * 0.037, FACE_Y - 0.008, ey), gm, n=16, nr=5,
                        rot=(math.radians(90), 0, 0)), "head")
            B.add(box("temple%d" % sx, (0.003, 0.1, 0.003), (sx * 0.06, FACE_Y + 0.045, ey + 0.002), gm), "head")
        B.add(box("bridge", (0.018, 0.003, 0.003), (0, FACE_Y - 0.008, ey + 0.004), gm), "head")


# ------------------------------------------------------------------ hair styles (separate callables)
def _hm(c):
    return M("hair2", c, 0.85)


def hair_short_part(c):
    """Neat short cut with a side part and a bit of volume on top."""
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.07, HEAD_C + V((0, 0.012, 0.03)), m, seg=20, rings=12, scale=(1.0, 1.05, 0.88)), "head")
        B.add(sphere("htop", 0.065, HEAD_C + V((0.022, -0.035, 0.088)), m, seg=12, rings=8, scale=(1.5, 1.0, 0.55)), "head")
        B.add(sphere("hback", 0.09, HEAD_C + V((0, 0.045, -0.02)), m, seg=12, rings=8, scale=(1.08, 0.75, 0.9)), "head")
        for sx in (-1, 1):
            B.add(sphere("hside%d" % sx, 0.04, HEAD_C + V((sx * 0.088, 0.012, 0.0)), m, seg=10, rings=8,
                         scale=(0.45, 1.1, 1.0)), "head")
    return f


def hair_slick(c):
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.04, HEAD_C + V((0, 0.018, 0.035)), m, seg=20, rings=12, scale=(1.0, 1.03, 0.8)), "head")
        B.add(sphere("hback", 0.088, HEAD_C + V((0, 0.05, -0.015)), m, seg=12, rings=8, scale=(1.06, 0.7, 0.85)), "head")
    return f


def hair_wavy(c):
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.08, HEAD_C + V((0, 0.022, 0.045)), m, seg=20, rings=12, scale=(1.03, 1.04, 0.84)), "head")
        for k in range(7):
            a = -1.1 + k * 0.37
            B.add(sphere("wave%d" % k, 0.032, HEAD_C + V((math.sin(a) * 0.07, -0.045 + abs(math.sin(a)) * 0.05, 0.092 + 0.01 * (k % 2))),
                         m, seg=10, rings=6, scale=(1.0, 1.1, 0.7)), "head")
        B.add(sphere("hback", 0.095, HEAD_C + V((0, 0.05, -0.02)), m, seg=12, rings=8, scale=(1.1, 0.75, 0.95)), "head")
    return f


def hair_combed_back(c):
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.06, HEAD_C + V((0, 0.025, 0.035)), m, seg=20, rings=12, scale=(1.0, 1.06, 0.85)), "head")
        B.add(sphere("hpomp", 0.06, HEAD_C + V((0, -0.045, 0.08)), m, seg=12, rings=8, scale=(1.4, 0.9, 0.55)), "head")
        B.add(sphere("hback", 0.09, HEAD_C + V((0, 0.055, -0.03)), m, seg=12, rings=8, scale=(1.08, 0.72, 0.92)), "head")
    return f


def hair_bald_sides(c):
    def f(B):
        m = _hm(c)
        for sx in (-1, 1):
            B.add(sphere("side%d" % sx, 0.05, HEAD_C + V((sx * 0.085, 0.03, -0.012)), m, seg=10, rings=8,
                         scale=(0.5, 1.15, 0.85)), "head")
        B.add(sphere("back", 0.075, HEAD_C + V((0, 0.07, -0.02)), m, seg=10, rings=8, scale=(1.3, 0.55, 0.85)), "head")
    return f


def hair_ponytail(c):
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.07, HEAD_C + V((0, 0.012, 0.028)), m, seg=20, rings=12, scale=(1.02, 1.05, 0.9)), "head")
        for sx in (-1, 1):
            B.add(sphere("hframe%d" % sx, 0.04, HEAD_C + V((sx * 0.078, -0.045, 0.01)), m, seg=10, rings=8,
                         scale=(0.5, 0.7, 1.35)), "head")
        B.add(sphere("tie", 0.025, HEAD_C + V((0, 0.105, 0.02)), m, seg=10, rings=8), "head")
        pts = [HEAD_C + V((0, 0.115, 0.02)), HEAD_C + V((0, 0.15, -0.04)), HEAD_C + V((0, 0.155, -0.13)),
               HEAD_C + V((0, 0.14, -0.21))]
        for i in range(len(pts) - 1):
            r = 0.04 - i * 0.008
            B.add(sphere("tail%d" % i, r, (pts[i] + pts[i + 1]) / 2, m, seg=10, rings=8, scale=(0.95, 0.9, 1.7)), "head")
    return f


def hair_bob(c):
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.09, HEAD_C + V((0, 0.02, 0.04)), m, seg=20, rings=12, scale=(1.05, 1.05, 0.86)), "head")
        for sx in (-1, 1):
            B.add(sphere("bobs%d" % sx, 0.055, HEAD_C + V((sx * 0.085, 0.01, -0.055)), m, seg=12, rings=8,
                         scale=(0.55, 1.15, 1.25)), "head")
        B.add(sphere("bobb", 0.1, HEAD_C + V((0, 0.06, -0.05)), m, seg=12, rings=8, scale=(1.05, 0.65, 0.95)), "head")
        B.add(sphere("fringe", 0.05, HEAD_C + V((0.025, -0.07, 0.082)), m, seg=12, rings=8, scale=(1.6, 0.6, 0.42)), "head")
    return f


def hair_bun(c, low=False):
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.06, HEAD_C + V((0, 0.015, 0.03)), m, seg=20, rings=12, scale=(1.0, 1.05, 0.88)), "head")
        z = -0.04 if low else 0.07
        B.add(sphere("bun", 0.045, HEAD_C + V((0, 0.105, z)), m, seg=12, rings=8), "head")
    return f


def hair_long(c):
    def f(B):
        m = _hm(c)
        B.add(sphere("hcap", HEAD_R * 1.08, HEAD_C + V((0, 0.012, 0.028)), m, seg=20, rings=12, scale=(1.03, 1.05, 0.9)), "head")
        B.add(sphere("hlong", 0.1, HEAD_C + V((0, 0.06, -0.12)), m, seg=12, rings=8, scale=(1.15, 0.55, 1.45)), "head")
        for sx in (-1, 1):
            B.add(sphere("hl%d" % sx, 0.045, HEAD_C + V((sx * 0.085, 0.02, -0.08)), m, seg=10, rings=8,
                         scale=(0.6, 1.0, 1.7)), "head")
    return f


# ------------------------------------------------------------------ body
def human(name, coll, spec):
    rig = build_armature(name, coll)
    B = Body(name, coll)
    sk = skin(spec.get("skin", "#e8b894"))
    top_c = spec.get("top_c", "#3d4249")
    top = M("cloth2", top_c, 0.8)
    shirt = M("shirt2", spec.get("shirt", "#f1f1ec"), 0.7)
    pants = M("pants2", spec.get("pants", "#3d4249"), 0.8)
    shoes = M("shoe2", spec.get("shoes", "#1d1f22"), 0.35)
    sole = mat("sole2", "#141416", rough=0.7)
    belly = spec.get("belly", 0.0)
    fem = spec.get("female", False)
    kind = spec.get("top", "suit")      # suit | shirt | blouse | dress | coat | labcoat
    sh_w = 0.95 if fem else 1.0

    # ---- torso
    pel_m = M("skirt2", spec["skirt"], 0.75) if spec.get("skirt") else (top if kind == "dress" else pants)
    B.add(sphere("pelvis", 0.155, (0, 0, 0.975), pel_m, seg=18, rings=10, scale=(1.08 if fem else 1.0, 0.75, 0.66)), "hips")
    B.add(sphere("abdomen", 0.14 + belly, (0, belly * 0.5, 1.13), top, seg=18, rings=10,
                 scale=(0.95 if fem else 1.0, 0.72 + belly, 0.95)), "spine")
    B.add(sphere("chest", 0.168, (0, 0.0, 1.32), top, seg=24, rings=14, scale=(1.08 * sh_w, 0.64, 0.92)), "chest")
    B.add(sphere("yoke", 0.15, (0, 0.008, 1.405), top, seg=20, rings=12, scale=(1.2 * sh_w, 0.6, 0.48)), "chest")
    for s, sx in (("L", 1), ("R", -1)):
        B.add(sphere("shoulder" + s, 0.046, (sx * 0.15 * sh_w, 0.0, 1.415), top, seg=14, rings=10, scale=(1.2, 1, 0.7)),
              "clavicle_" + s)
    # neck
    B.capsule("neck", (0, 0.008, 1.42), (0, 0.004, 1.56), 0.05 if fem else 0.058, 0.048, sk, "neck", caps=False)
    # head
    B.add(sphere("head", HEAD_R, HEAD_C, sk, seg=24, rings=16, scale=(0.9, 0.98, 1.16)), "head")
    B.add(sphere("jaw", 0.072, HEAD_C + V((0, -0.012, -0.045)), sk, seg=20, rings=12,
                 scale=(0.98 * spec.get("jaw", 1.0), 0.95, 0.85)), "head")
    face(B, sk, spec)

    # ---- clothing layers on the torso
    if kind in ("suit", "coat"):
        jacket = top
        # open front: shirt V, tie, lapels, buttons, pockets, hem
        B.add(prism("shirtv", [(-0.042, 0.2), (0.042, 0.2), (0, 0)], 0.008, (0, -0.105, 1.255), shirt, axis="Y"), "chest")
        if spec.get("tie"):
            tm = M("tie2", spec["tie"], 0.45)
            B.add(prism("tieknot", [(-0.012, 0), (0.012, 0), (0.008, -0.02), (-0.008, -0.02)], 0.012,
                        (0, -0.104, 1.445), tm, axis="Y"), "chest")
            B.add(prism("tie", [(-0.008, 0), (0.008, 0), (0.02, -0.19), (0, -0.21), (-0.02, -0.19)], 0.008,
                        (0, -0.108, 1.425), tm, axis="Y"), "chest")
        lap = M("lapel2", spec.get("lapel", top_c), 0.75)
        for sx in (-1, 1):
            B.add(prism("lapel%d" % sx, [(0, 0.17), (sx * 0.055, 0.16), (sx * 0.035, 0.04), (0, -0.02)], 0.012,
                        (sx * 0.004, -0.104, 1.255), lap, axis="Y"), "chest")
        btn = mat("btn2", "#1a1a1c", rough=0.3)
        for k in range(2):
            B.add(sphere("btn%d" % k, 0.0075, (0.0, -0.112 - belly * 0.7, 1.19 - k * 0.075), btn, seg=6, rings=4), "spine")
        for sx in (-1, 1):
            B.add(box("pocket%d" % sx, (0.075, 0.008, 0.012), (sx * 0.085, -0.108 - belly * 0.6, 1.07), jacket), "spine")
        B.add(box("breastpk", (0.06, 0.006, 0.01), (0.085, -0.115, 1.33), jacket), "chest")
        hem_len = 0.55 if kind == "coat" else 0.2
        B.add(cyl("hem", 0.158 + belly * 0.8, hem_len, (0, belly * 0.4, 1.02 - hem_len + 0.06), jacket, n=20,
                  r2=0.15 + belly * 0.8), "hips")
    elif kind in ("shirt", "blouse"):
        B.add(prism("placket", [(-0.007, 0.0), (0.007, 0.0), (0.007, -0.3), (-0.007, -0.3)], 0.006,
                    (0, -0.106 - belly * 0.5, 1.43), M("placket", spec.get("top_c"), 0.75), axis="Y"), "chest")
        for k in range(4):
            B.add(sphere("sbtn%d" % k, 0.005, (0, -0.118 - belly * 0.5, 1.37 - k * 0.07), mat("sbtn", "#e8e6df"), seg=6,
                         rings=4), "chest" if k < 2 else "spine")
        if spec.get("tie"):
            tm = M("tie2", spec["tie"], 0.45)
            B.add(prism("tie", [(-0.008, 0), (0.008, 0), (0.022, -0.2), (0, -0.22), (-0.022, -0.2)], 0.008,
                        (0, -0.112 - belly * 0.3, 1.44), tm, axis="Y"), "chest")
        B.add(torus("belt", 0.15 + belly * 0.7, 0.012, (0, belly * 0.3, 1.0), mat("belt2", "#1c1a18", rough=0.4)), "hips")
        B.add(box("buckle", (0.03, 0.006, 0.022), (0, -0.157 - belly * 0.6, 0.99), mat("buckle", "#b8b2a0", metal=0.7, rough=0.3)), "hips")
    elif kind == "dress":
        B.add(torus("waist", 0.13, 0.01, (0, 0, 1.07), M("sash", spec.get("sash", top_c), 0.6)), "spine")
    elif kind == "labcoat":
        B.add(prism("shirtv", [(-0.045, 0.15), (0.045, 0.15), (0, 0)], 0.008, (0, -0.118, 1.26), shirt, axis="Y"), "chest")
        B.add(cyl("coathem", 0.165, 0.6, (0, 0, 0.45), top, n=20, r2=0.15), "hips")
        for sx in (-1, 1):
            B.add(box("cpocket%d" % sx, (0.08, 0.008, 0.07), (sx * 0.09, -0.16, 0.86), top), "hips")
    # collar
    if kind in ("suit", "shirt", "labcoat", "coat"):
        cm = shirt if kind != "shirt" else top
        B.add(torus("collar", 0.058, 0.012, (0, -0.006, 1.465), cm, n=20, nr=6, rot=(math.radians(-14), 0, 0)), "chest")
    if kind == "blouse":
        B.add(torus("bcollar", 0.058, 0.012, (0, -0.006, 1.46), top), "chest")

    # ---- arms
    sleeve = top if spec.get("sleeves", "long") != "none" else sk
    short = spec.get("sleeves", "long") == "short"
    for s, sx in (("L", 1), ("R", -1)):
        ua0, ua1 = V(SK["upper_arm_" + s][0]), V(SK["upper_arm_" + s][1])
        fa0, fa1 = V(SK["forearm_" + s][0]), V(SK["forearm_" + s][1])
        B.capsule("uarm" + s, ua0, ua1, 0.05, 0.043, sleeve, "upper_arm_" + s)
        B.capsule("farm" + s, fa0, fa1, 0.042 if not short else 0.036, 0.034, sk if short else sleeve, "forearm_" + s)
        if short:
            B.add(sphere("elbow" + s, 0.04, ua1, sk, seg=10, rings=8), "forearm_" + s)
        else:
            cuff = shirt if kind in ("suit", "coat") else sleeve
            B.add(cyl("cuff" + s, 0.037, 0.035, fa1 + V((0, 0, 0.012)), cuff, n=12), "forearm_" + s)
        # hand: palm + four fingers + thumb
        h0, h1 = V(SK["hand_" + s][0]), V(SK["hand_" + s][1])
        hm = sk
        B.add(sphere("palm" + s, 0.038, h0 + (h1 - h0) * 0.35, hm, seg=10, rings=8, scale=(0.55, 0.95, 1.05)), "hand_" + s)
        for k in range(4):
            off = V((sx * 0.004, -0.024 + k * 0.015, 0))
            tip = h0 + (h1 - h0) * 1.05 + off + V((sx * 0.004, 0, 0.0))
            B.add(tube_path("fing%s%d" % (s, k), [h0 + (h1 - h0) * 0.55 + off, tip], 0.0085 - (0.0012 if k == 3 else 0), hm, n=6),
                  "hand_" + s)
        B.add(tube_path("thumb" + s, [h0 + (h1 - h0) * 0.25 + V((0, -0.03, 0)), h0 + (h1 - h0) * 0.6 + V((-sx * 0.004, -0.05, 0))],
                        0.01, hm, n=6), "hand_" + s)

    # ---- legs
    skirt = spec.get("skirt")
    for s, sx in (("L", 1), ("R", -1)):
        t0, t1 = V(SK["thigh_" + s][0]), V(SK["thigh_" + s][1])
        s0 = V(SK["shin_" + s][0])
        leg_m = pants
        B.capsule("thigh" + s, t0, t1, 0.072 if not fem else 0.068, 0.055, leg_m, "thigh_" + s)
        B.capsule("shin" + s, s0, (sx * 0.092, 0.012, 0.12), 0.052, 0.04, leg_m, "shin_" + s)
        if not skirt and not spec.get("bare_legs"):
            B.add(cyl("pcuff" + s, 0.048, 0.06, (sx * 0.092, 0.012, 0.085), pants, n=14), "shin_" + s)
        # shoe: rounded toe box + heel + sole
        f0 = V(SK["foot_" + s][0])
        heel = spec.get("heels", False)
        B.add(sphere("shoe" + s, 0.048, (sx * 0.092, -0.05, 0.045), shoes, seg=14, rings=8, scale=(0.82, 2.0, 0.7)), "foot_" + s)
        B.add(sphere("heelc" + s, 0.045, (sx * 0.092, 0.03, 0.055), shoes, seg=12, rings=8, scale=(0.9, 0.9, 0.9)), "foot_" + s)
        B.add(box("sole" + s, (0.085, 0.26, 0.018), (sx * 0.092, -0.045, 0.0), sole, bevel=0.008), "foot_" + s)
        if heel:
            B.add(box("heel" + s, (0.03, 0.03, 0.04), (sx * 0.092, 0.06, 0.0), sole), "foot_" + s)
    if skirt:
        sm = M("skirt2", skirt, 0.75)
        B.add(cyl("skirt", 0.165, 0.46, (0, 0.0, 0.5), sm, n=24, r2=0.15), "hips")
        B.add(torus("skirtw", 0.148, 0.012, (0, 0, 0.96), sm), "hips")
    if kind == "dress":
        dm = top
        B.add(cyl("dressk", 0.18, 0.5, (0, 0, 0.48), dm, n=24, r2=0.152), "hips")
    for fn in spec.get("extras", []):
        fn(B)
    meshes = B.finish(rig)
    return rig, meshes


# ------------------------------------------------------------------ accessories
def lanyard(c="#1f3a5f"):
    def f(B):
        m = M("lanyard2", c, 0.6)
        for sx in (-1, 1):
            B.add(tube_path("lan%d" % sx, [(sx * 0.058, -0.02, 1.46), (sx * 0.045, -0.105, 1.37), (sx * 0.012, -0.126, 1.25)],
                            0.004, m, n=5), "chest")
        B.add(box("badge", (0.045, 0.004, 0.062), (0.0, -0.133, 1.19), mat("badge2", "#f6f6f0", rough=0.3)), "chest")
        B.add(box("badgeb", (0.04, 0.002, 0.012), (0.0, -0.136, 1.215), mat("badge_blue2", "#1f3a5f")), "chest")
        B.add(box("badgep", (0.016, 0.002, 0.018), (-0.008, -0.136, 1.185), mat("badgephoto", "#9aa4ad")), "chest")
    return f


def apron(c):
    def f(B):
        m = M("apron2", c, 0.85)
        B.add(box("bib", (0.19, 0.008, 0.2), (0, -0.112, 1.2), m), "chest")
        B.add(box("aprsk", (0.3, 0.008, 0.42), (0, -0.128, 0.6), m), "hips")
        B.add(torus("aprstr", 0.145, 0.008, (0, 0, 1.06), m), "spine")
        for sx in (-1, 1):
            B.add(tube_path("aprn%d" % sx, [(sx * 0.08, -0.11, 1.4), (sx * 0.06, -0.01, 1.45)], 0.006, m, n=5), "chest")
    return f


def cardigan(c):
    def f(B):
        m = M("cardi2", c, 0.95)
        for sx in (-1, 1):
            B.add(prism("cardi%d" % sx, [(0, 0.2), (sx * 0.075, 0.2), (sx * 0.08, -0.12), (sx * 0.02, -0.12)], 0.012,
                        (sx * 0.02, -0.122, 1.2), m, axis="Y"), "chest")
    return f


def headset(B):
    m = mat("headset2", "#1b1b1e", rough=0.4)
    B.add(torus("hs", 0.11, 0.006, HEAD_C + V((0, 0.0, 0.0)), m, n=24, nr=6, rot=(math.radians(90), 0, 0)), "head")
    B.add(sphere("hsear", 0.026, HEAD_C + V((-0.1, 0, -0.005)), m, seg=10, rings=6, scale=(0.6, 1, 1)), "head")
    B.add(tube_path("mic", [HEAD_C + V((-0.1, -0.01, -0.02)), HEAD_C + V((-0.06, -0.09, -0.06))], 0.004, m, n=5), "head")


def cane(B):
    w = mat("darkwood", "darkwood")
    p = V(SK["hand_R"][1])
    B.add(tube_path("cane", [(p.x, p.y - 0.03, 0.0), (p.x, p.y - 0.02, p.z + 0.04)], 0.012, w, n=6), "hand_R")
    B.add(sphere("knob", 0.022, (p.x, p.y - 0.02, p.z + 0.05), mat("brass", "brass", metal=0.8), seg=8, rings=6), "hand_R")


def vest(c):
    def f(B):
        m = M("vest2", c, 0.8)
        B.add(sphere("vest", 0.17, (0, -0.005, 1.3), m, seg=18, rings=10, scale=(1.08, 0.66, 0.9)), "chest")
    return f


def pocket_square(c="#f1f1ec"):
    def f(B):
        B.add(prism("psq", [(-0.012, 0), (0.012, 0), (0.0, 0.02)], 0.005, (0.085, -0.117, 1.335), M("psq", c, 0.6), axis="Y"),
              "chest")
    return f
