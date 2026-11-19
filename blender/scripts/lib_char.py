"""Stylised humans for Severance: Lumon Office: one shared 20-bone skeleton, rigid-segment skinning
(each body part weighted 100% to one bone, joints hidden by overlapping spheres), procedural animations.

Pose convention: every joint rotation is given in ARMATURE axes, relative to its parent as if the parent
were at rest (q_B). Bone world delta D_B = D_parent * q_B; pose quaternion = Rrest^-1 * q_B * Rrest.
Character faces -Y; its left side is +X. 1 unit = 1 m. Rotation about +X with a positive angle swings a
downward limb BACKWARD (+Y); negative = forward.
"""
import bpy
import math
from mathutils import Vector, Quaternion, Matrix
from lib_geo import box, cyl, sphere, torus, tube_path, prism, mat, hexrgb, MATS, empty

FPS = 24

# ------------------------------------------------------------------ skeleton (rest, armature space)
# name: (head, tail, parent)
SK = {
    "root": ((0, 0, 0), (0, 0, 0.12), None),
    "hips": ((0, 0, 0.70), (0, 0, 0.84), "root"),
    "spine": ((0, 0, 0.84), (0, 0, 0.99), "hips"),
    "chest": ((0, 0, 0.99), (0, 0, 1.20), "spine"),
    "neck": ((0, 0, 1.20), (0, 0, 1.28), "chest"),
    "head": ((0, 0, 1.28), (0, 0, 1.70), "neck"),
}
for s, sx in (("L", 1), ("R", -1)):
    SK.update({
        "clavicle_" + s: ((sx * 0.04, 0, 1.17), (sx * 0.17, 0, 1.17), "chest"),
        "upper_arm_" + s: ((sx * 0.19, 0, 1.15), (sx * 0.30, 0, 0.92), "clavicle_" + s),
        "forearm_" + s: ((sx * 0.30, 0, 0.92), (sx * 0.38, 0, 0.71), "upper_arm_" + s),
        "hand_" + s: ((sx * 0.38, 0, 0.71), (sx * 0.41, 0, 0.61), "forearm_" + s),
        "thigh_" + s: ((sx * 0.10, 0, 0.70), (sx * 0.10, 0, 0.40), "hips"),
        "shin_" + s: ((sx * 0.10, 0, 0.40), (sx * 0.10, 0, 0.09), "thigh_" + s),
        "foot_" + s: ((sx * 0.10, 0, 0.09), (sx * 0.10, -0.15, 0.03), "shin_" + s),
    })
ORDER = ["root", "hips", "spine", "chest", "neck", "head"] + [
    b + "_" + s for s in ("L", "R") for b in ("clavicle", "upper_arm", "forearm", "hand", "thigh", "shin", "foot")]

THIGH_LEN = 0.30
SHIN_LEN = 0.31
UPPER_LEN = math.hypot(0.11, 0.23)
FORE_LEN = math.hypot(0.08, 0.21)


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


# ------------------------------------------------------------------ body building
class Body:
    """Collects mesh parts with the bone they follow; at the end joins them and binds to the rig."""

    def __init__(self, name, coll):
        self.name, self.coll = name, coll
        self.parts = []  # (obj, bone, separate_name or None)

    def add(self, ob, bone, separate=None):
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        self.coll.objects.link(ob)
        self.parts.append((ob, bone, separate))
        return ob

    # limb capsule between two armature-space points
    def capsule(self, nm, a, b, r1, r2, m, bone, n=12, caps=True):
        a, b = V(a), V(b)
        d = b - a
        L = d.length
        ob = cyl(nm, r1, L, (0, 0, 0), m, n=n, r2=r2)
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = q
        ob.location = a
        self.add(ob, bone)
        if caps:
            self.add(sphere(nm + "_ca", r1, a, m, seg=n, rings=8), bone)
            self.add(sphere(nm + "_cb", r2, b, m, seg=n, rings=8), bone)
        return ob

    def finish(self, rig):
        from lib_geo import apply_xform, join, world_uv
        groups = {}
        separate = []
        for ob, bone, sep in self.parts:
            apply_xform(ob)
            ob.vertex_groups.clear()
            vg = ob.vertex_groups.new(name=bone)
            vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
            if sep:
                separate.append((ob, sep))
            else:
                groups.setdefault("body", []).append(ob)
        out = []
        body = join(groups["body"], self.name + "_body")
        out.append(body)
        # separate parts: join per separate-name (ACC_*, HELD_*)
        bysep = {}
        for ob, sep in separate:
            bysep.setdefault(sep, []).append(ob)
        for sep, obs in bysep.items():
            out.append(join(obs, sep))
        for ob in out:
            ob.parent = rig
            mod = ob.modifiers.new("Armature", "ARMATURE")
            mod.object = rig
            world_uv(ob)
        return out


def skin(c):
    return mat("skin_" + c.lstrip("#"), c, rough=0.7)


def face(B, skin_m, x0=0.0, y_face=-0.205, zc=1.47, scale=1.0, brows="#4a2f22", mustache=None, glasses=False,
         expression="smile"):
    """Big cartoon eyes, nose, mouth on the head sphere front (-Y)."""
    s = scale
    white = mat("eye_white", "#ffffff", rough=0.3)
    pupil = mat("eye_pupil", "#2b2320", rough=0.2)
    for sx in (-1, 1):
        B.add(sphere("eye%d" % sx, 0.05 * s, (sx * 0.075 * s, y_face + 0.025, zc + 0.045 * s), white, seg=10, rings=8,
                     scale=(1, 0.55, 1.3)), "head")
        B.add(sphere("pup%d" % sx, 0.029 * s, (sx * 0.072 * s, y_face - 0.0, zc + 0.04 * s), pupil, seg=8, rings=6,
                     scale=(1, 0.5, 1.25)), "head")
        B.add(sphere("hl%d" % sx, 0.008 * s, (sx * 0.063 * s, y_face - 0.008, zc + 0.062 * s), white, seg=6, rings=4),
              "head")
        bz = zc + 0.125 * s + (0.0 if expression != "angry" else -0.01)
        br = box("brow%d" % sx, (0.07 * s, 0.02, 0.018 * s), (sx * 0.075 * s, y_face + 0.0, bz), mat("hair_" + brows.lstrip("#"),
                                                                                                    brows),
                 rot=(0, math.radians(sx * (12 if expression == "angry" else -6)), 0))
        B.add(br, "head")
        B.add(sphere("cheek%d" % sx, 0.03 * s, (sx * 0.12 * s, y_face + 0.025, zc - 0.045 * s), mat("cheek", "#e8aa96"),
                     seg=8, rings=6, scale=(1, 0.4, 0.7)), "head")
    B.add(sphere("nose", 0.035 * s, (0, y_face - 0.02, zc - 0.02 * s), skin_m, seg=10, rings=8, scale=(1, 0.9, 0.9)),
          "head")
    mouth_m = mat("mouth", "#7a2a2a")
    if expression == "angry":
        B.add(box("mouth", (0.08 * s, 0.02, 0.015 * s), (0, y_face + 0.02, zc - 0.09 * s), mouth_m), "head")
    else:
        pts = [(math.cos(a) * 0.04 * s, y_face + 0.022 - 0.008 * math.sin(a), zc - 0.075 * s + math.sin(a) * 0.022 * s)
               for a in [math.pi * (1 + k / 8) for k in range(9)]]
        B.add(tube_path("mouth", pts, 0.008 * s, mouth_m, n=6), "head")
    if mustache:
        mm = mat("hair_" + mustache.lstrip("#"), mustache)
        for sx in (-1, 1):
            B.add(sphere("must%d" % sx, 0.05 * s, (sx * 0.04 * s, y_face - 0.005, zc - 0.05 * s), mm, seg=8, rings=6,
                         scale=(1.3, 0.6, 0.55)), "head")
    if glasses:
        gm = mat("glasses", "#2b2b30")
        for sx in (-1, 1):
            B.add(torus("gl%d" % sx, 0.045 * s, 0.008, (sx * 0.075 * s, y_face - 0.03, zc + 0.03 * s), gm,
                        rot=(math.radians(90), 0, 0)), "head")


def human(name, coll, spec):
    """Build a cartoon human from a spec dict. Returns (rig, mesh objects).
    spec keys: skin, height_scale (applied at the end via armature scale), belly, jacket, jacket_m, pants, shoes,
    hair (callable or None), hat, top ('jacket'|'hoodie'|'shirt'|'robe'|'uniform'|'cardigan'|'tshirt'), extras."""
    rig = build_armature(name, coll)
    B = Body(name, coll)
    sk = skin(spec.get("skin", "#f2c39b"))
    top = spec.get("top_m") or mat("cloth_" + spec.get("top_c", "turq").lstrip("#"), spec.get("top_c", "turq"))
    pants = mat("cloth_" + spec.get("pants", "#5a4436").lstrip("#"), spec.get("pants", "#5a4436"))
    shoes = mat("cloth_" + spec.get("shoes", "#c8763a").lstrip("#"), spec.get("shoes", "#c8763a"))
    sole = mat("sole_" + spec.get("sole", "#1d1f22").lstrip("#"), spec.get("sole", "#1d1f22"))
    belly = spec.get("belly", 0.0)

    # torso: hips (pelvis), belly (spine), chest
    pel_m = mat("skirt", spec["skirt"]) if spec.get("skirt") else pants
    B.add(sphere("pelvis", 0.17, (0, 0, 0.76), pel_m, scale=(1.0, 0.8, 0.7)), "hips")
    B.add(sphere("belly", 0.17 + belly, (0, belly * 0.4, 0.92), top, scale=(1.0, 0.85, 0.95)), "spine")
    B.add(sphere("chest", 0.19 + belly * 0.4, (0, 0, 1.08), top, scale=(1.0, 0.75, 0.85)), "chest")
    if spec.get("top") in ("jacket", None):
        # reflective stripes around the chest
        refl = mat("reflective", "#d8e3e6", rough=0.3)
        for z in (1.02,):
            B.add(torus("stripe", 0.172 + belly * 0.4, 0.012, (0, 0, z), refl), "chest")
        # zipper
        B.add(box("zip", (0.012, 0.01, 0.3), (0, -0.165 - belly * 0.25, 0.88), mat("zip", "#d9d9d9")), "chest")
        B.add(torus("collar", 0.075, 0.03, (0, 0.0, 1.19), top), "chest")
    if spec.get("top") == "hoodie":
        B.add(torus("hood", 0.11, 0.05, (0, 0.04, 1.2), top, rot=(math.radians(15), 0, 0)), "chest")
        B.add(box("pocket", (0.2, 0.02, 0.08), (0, -0.15 - belly * 0.3, 0.9), top, bevel=0.01), "spine")
    if spec.get("top") == "shirt":
        B.add(prism("tie", [(-0.025, 0), (0.025, 0), (0.035, -0.22), (0, -0.26), (-0.035, -0.22)], 0.01,
                    (0, -0.17, 1.18), mat("tie", spec.get("tie", "coral")), axis="Y",
                    rot=(0, 0, 0)), "chest")
    if spec.get("top") == "uniform":
        B.add(box("belt", (0.36, 0.3, 0.05), (0, 0, 0.8), mat("belt", "#2b2b30")), "hips")
        B.add(cyl("badge", 0.025, 0.01, (0.08, -0.15, 1.12), mat("gold", "#e2b23c", metal=0.6, rough=0.4), n=6,
                  rot=(math.radians(90), 0, 0)), "chest")
    if spec.get("top") == "cook":
        for k in range(3):
            B.add(sphere("btn%d" % k, 0.012, (0.05, -0.17, 1.12 - k * 0.08), mat("btn", "#d9d9d9"), seg=6, rings=4),
                  "chest")
    # neck
    B.capsule("neck", (0, 0, 1.17), (0, 0, 1.3), 0.055, 0.055, sk, "neck", caps=False)

    # head
    hs = spec.get("head_scale", 1.0)
    B.add(sphere("head", 0.21 * hs, (0, 0, 1.47), sk, seg=20, rings=14, scale=(1.0, 0.95, 1.05)), "head")
    for sx in (-1, 1):
        B.add(sphere("ear%d" % sx, 0.045, (sx * 0.205 * hs, 0.01, 1.46), sk, seg=8, rings=6, scale=(0.5, 0.8, 1)), "head")
    face(B, sk, scale=hs, brows=spec.get("hair_c", "#4a2f22"), mustache=spec.get("mustache"),
         glasses=spec.get("glasses", False), expression=spec.get("expression", "smile"))

    # arms: sleeves + hands (mitten with thumb)
    sleeve = top if spec.get("sleeves", True) else sk
    for s, sx in (("L", 1), ("R", -1)):
        B.capsule("uarm" + s, SK["upper_arm_" + s][0], SK["upper_arm_" + s][1], 0.06, 0.052, sleeve, "upper_arm_" + s)
        B.capsule("farm" + s, SK["forearm_" + s][0], SK["forearm_" + s][1], 0.052, 0.047, sleeve, "forearm_" + s)
        if spec.get("cuffs"):
            B.add(torus("cuff" + s, 0.048, 0.014, SK["forearm_" + s][1], mat("reflective", "#d8e3e6"),
                        rot=(0, math.radians(sx * 20), 0)), "forearm_" + s)
        hp = V(SK["hand_" + s][0]) + (V(SK["hand_" + s][1]) - V(SK["hand_" + s][0])) * 0.45
        hand_m = mat("glove", spec["gloves"]) if spec.get("gloves") else sk
        B.add(sphere("hand" + s, 0.055, hp, hand_m, seg=10, rings=8, scale=(0.75, 0.95, 1.15)), "hand_" + s)
        B.add(sphere("thumb" + s, 0.022, hp + Vector((0, -0.045, 0.02)), hand_m, seg=6, rings=5, scale=(1, 1, 1.4)),
              "hand_" + s)
        B.add(sphere("shoulder" + s, 0.07, SK["upper_arm_" + s][0], sleeve, seg=10, rings=8), "clavicle_" + s)

    # legs
    robe = spec.get("top") == "robe"
    for s, sx in (("L", 1), ("R", -1)):
        B.capsule("thigh" + s, SK["thigh_" + s][0], SK["thigh_" + s][1], 0.085, 0.07, pants, "thigh_" + s)
        shin_m = sk if spec.get("shorts") else pants
        B.capsule("shin" + s, SK["shin_" + s][0], (sx * 0.10, 0, 0.12), 0.07, 0.06, shin_m, "shin_" + s)
        if spec.get("shorts"):
            B.add(cyl("shortcuff" + s, 0.09, 0.08, (sx * 0.10, 0, 0.38), pants, n=12), "thigh_" + s)
        elif spec.get("pant_cuff", True):
            B.add(cyl("pcuff" + s, 0.066, 0.05, (sx * 0.10, 0, 0.1), pants, n=12), "shin_" + s)
        # sneaker
        B.add(sphere("shoe" + s, 0.075, (sx * 0.10, -0.05, 0.055), shoes, seg=12, rings=8, scale=(0.9, 1.6, 0.75)),
              "foot_" + s)
        B.add(box("sole" + s, (0.13, 0.26, 0.025), (sx * 0.10, -0.05, 0.0), sole, bevel=0.01), "foot_" + s)
    if robe:
        rm = top
        B.add(cyl("robe", 0.22 + belly, 0.55, (0, 0, 0.3), rm, n=16, r2=0.19 + belly), "hips")
        B.add(torus("robebelt", 0.19 + belly * 0.8, 0.02, (0, 0, 0.86), mat("robebelt", "#8a5b3a")), "spine")
    if spec.get("skirt"):
        B.add(cyl("skirt", 0.25, 0.42, (0, 0, 0.36), mat("skirt", spec["skirt"]), n=16, r2=0.17), "hips")
    for fn in spec.get("extras", []):
        fn(B)
    meshes = B.finish(rig)
    return rig, meshes


# ------------------------------------------------------------------ accessories (separate ACC_/HELD_ meshes)
def hair_short(c, sep="ACC_hair_short"):
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        B.add(sphere("hs", 0.218, (0, 0.045, 1.565), m, seg=16, rings=10, scale=(1.03, 1.0, 0.8)), "head", sep)
        B.add(sphere("hsf", 0.08, (0.06, -0.13, 1.64), m, seg=8, rings=6, scale=(1.6, 0.8, 0.6)), "head", sep)
    return f


def hair_ponytail(c, sep="ACC_hair_ponytail"):
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        B.add(sphere("hp", 0.22, (0, 0.045, 1.565), m, seg=16, rings=10, scale=(1.03, 1.0, 0.8)), "head", sep)
        B.add(sphere("hpt", 0.07, (0, 0.21, 1.5), m, seg=10, rings=8, scale=(0.9, 1.0, 1.5)), "head", sep)
        B.add(sphere("hpt2", 0.055, (0, 0.24, 1.38), m, seg=10, rings=8, scale=(0.9, 1.0, 1.6)), "head", sep)
    return f


def hair_curly(c, sep="ACC_hair_curly"):
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        for k in range(11):
            a = k * 2 * math.pi / 11
            B.add(sphere("hc%d" % k, 0.085, (math.cos(a) * 0.17, 0.03 + math.sin(a) * 0.15, 1.58 + 0.03 * math.sin(3 * a)),
                         m, seg=8, rings=6), "head", sep)
        B.add(sphere("hct", 0.18, (0, 0.03, 1.62), m, seg=12, rings=8, scale=(1, 1, 0.7)), "head", sep)
    return f


def hair_bun(c, sep="ACC_hair_bun"):
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        B.add(sphere("hb", 0.22, (0, 0.045, 1.565), m, seg=16, rings=10, scale=(1.03, 1.0, 0.8)), "head", sep)
        B.add(sphere("hbb", 0.09, (0, 0.06, 1.72), m, seg=10, rings=8), "head", sep)
    return f


def cap(c, sep="ACC_cap"):
    def f(B):
        m = mat("cap_" + c.lstrip("#"), c)
        B.add(sphere("cp", 0.225, (0, 0.02, 1.6), m, seg=16, rings=10, scale=(1.0, 1.0, 0.62)), "head", sep)
        B.add(cyl("cpv", 0.14, 0.02, (0, -0.2, 1.615), m, n=16, rot=(math.radians(-8), 0, 0)), "head", sep)
        B.add(sphere("cpb", 0.02, (0, 0.02, 1.74), m, seg=6, rings=4), "head", sep)
    return f


def helmet_bike(sep="ACC_helmet_bike"):
    def f(B):
        m = mat("helmet_bike", "#f6c945", rough=0.4)
        B.add(sphere("hb", 0.235, (0, 0.01, 1.6), m, seg=16, rings=10, scale=(1.0, 1.15, 0.66)), "head", sep)
        for k in range(3):
            B.add(box("hbv%d" % k, (0.03, 0.3, 0.03), (-0.07 + k * 0.07, 0.02, 1.72), "black"), "head", sep)
    return f


def helmet_half(sep="ACC_helmet_half"):
    def f(B):
        m = mat("helmet_half", "#33302e", rough=0.3)
        B.add(sphere("hh", 0.235, (0, 0.01, 1.6), m, seg=16, rings=10, scale=(1.0, 1.0, 0.7)), "head", sep)
        B.add(torus("hhr", 0.2, 0.02, (0, 0.01, 1.53), mat("helmet_rim", "#22b8b0")), "head", sep)
    return f


def helmet_retro(sep="ACC_helmet_retro"):
    def f(B):
        m = mat("helmet_retro", "#ef6a5b", rough=0.3)
        B.add(sphere("hr", 0.24, (0, 0.01, 1.6), m, seg=16, rings=10, scale=(1.0, 1.0, 0.72)), "head", sep)
        B.add(box("hrs", (0.05, 0.42, 0.03), (0, 0.0, 1.75), mat("paint_white", "white")), "head", sep)
        B.add(torus("goggle", 0.05, 0.015, (0.07, -0.2, 1.62), "black", rot=(math.radians(90), 0, 0)), "head", sep)
        B.add(torus("goggle2", 0.05, 0.015, (-0.07, -0.2, 1.62), "black", rot=(math.radians(90), 0, 0)), "head", sep)
    return f


def delivery_bag(sep="ACC_bag", c="turq", worn=False):
    def f(B):
        m = mat("bag_" + c, c, rough=0.5)
        y = 0.27
        B.add(box("bag", (0.42, 0.34, 0.46), (0, y, 0.84), m, bevel=0.05, seg=2), "chest", sep)
        B.add(box("baglid", (0.44, 0.36, 0.05), (0, y, 1.3), m, bevel=0.02), "chest", sep)
        B.add(box("bagstripe", (0.43, 0.35, 0.03), (0, y, 1.0), mat("reflective", "#d8e3e6")), "chest", sep)
        # cartoon cloche icon on the back
        icon = mat("bag_icon", "#fff6e6")
        B.add(sphere("icon", 0.07, (0, y + 0.172, 1.1), icon, seg=10, rings=6, scale=(1, 0.2, 0.7)), "chest", sep)
        B.add(box("iconbase", (0.17, 0.01, 0.015), (0, y + 0.175, 1.06), icon), "chest", sep)
        for k in range(3):
            B.add(sphere("steam%d" % k, 0.015, (-0.03 + k * 0.03, y + 0.175, 1.2 + (k % 2) * 0.02), icon, seg=6, rings=4),
                  "chest", sep)
        for sx in (-1, 1):
            B.add(tube_path("strap%d" % sx, [(sx * 0.1, 0.1, 1.2), (sx * 0.12, -0.12, 1.17), (sx * 0.13, -0.16, 0.95),
                                             (sx * 0.12, 0.08, 0.86)], 0.02, "black", n=6), "chest", sep)
        if worn:
            for k in range(3):
                B.add(cyl("patch%d" % k, 0.04, 0.01, (-0.12 + k * 0.1, y + 0.172, 0.8 + (k % 2) * 0.1),
                          mat("patch%d" % k, ["coral", "sun", "lilac"][k]), n=6, rot=(math.radians(90), 0, 0)),
                      "chest", sep)
    return f


def held_box(sep="HELD_box"):
    """Paper bag held in front with both hands (used when carrying an order)."""
    def f(B):
        B.add(box("hbx", (0.28, 0.18, 0.34), (0, -0.32, 0.78), mat("paper", "#d9b384"), bevel=0.01), "hand_R", sep)
    return f


def held_phone(sep="HELD_phone"):
    def f(B):
        p = V(SK["hand_R"][0]) + Vector((0.0, -0.04, -0.06))
        B.add(box("ph", (0.07, 0.012, 0.14), p, mat("phone", "#2b2b30"), bevel=0.008), "hand_R", sep)
        B.add(box("phs", (0.06, 0.002, 0.12), p + Vector((0, -0.008, 0.01)), "EMIT_screen"), "hand_R", sep)
    return f


def wrist_phone(B):
    p = V(SK["forearm_L"][1]) + Vector((0.0, -0.03, 0.03))
    B.add(box("wph", (0.05, 0.03, 0.08), p, mat("phone", "#2b2b30"), bevel=0.008), "forearm_L")
    B.add(box("wphs", (0.04, 0.005, 0.06), p + Vector((0, -0.017, 0)), "EMIT_screen"), "forearm_L")


# ------------------------------------------------------------------ posing
class Poser:
    """Computes bone world deltas from joint rotations (armature axes) and writes keyframes."""

    def __init__(self, rig):
        self.rig = rig
        self.rest = {}
        for b in rig.data.bones:
            self.rest[b.name] = (b.matrix_local.to_quaternion(), Vector(b.head_local), Vector(b.tail_local),
                                 b.parent.name if b.parent else None)

    def fk(self, q, hips_off=Vector((0, 0, 0))):
        """q: {bone: Quaternion (armature axes, relative)} -> (D, head positions) world."""
        D, P = {}, {}
        for bn in ORDER:
            Rr, h, t, p = self.rest[bn]
            qb = q.get(bn, Quaternion())
            if p is None:
                D[bn] = qb
                P[bn] = h.copy()
            else:
                D[bn] = D[p] @ qb
                P[bn] = P[p] + D[p] @ (h - self.rest[p][1])
            if bn == "hips":
                P[bn] = P[bn] + hips_off
        return D, P

    def tip(self, D, P, bn):
        Rr, h, t, p = self.rest[bn]
        return P[bn] + D[bn] @ (t - h)

    def ik2(self, q, chain, target, pole, hips_off, end=None, end_dir=None):
        """Two-bone IK: chain=(upper, lower). Sets q[upper], q[lower] so that lower's tip reaches target.
        pole: world direction the joint bends toward. Optional end bone oriented so its rest dir -> end_dir."""
        up, lo = chain
        D, P = self.fk(q, hips_off)
        a = P[up]
        l1 = (self.rest[up][2] - self.rest[up][1]).length
        l2 = (self.rest[lo][2] - self.rest[lo][1]).length
        tvec = target - a
        dist = min(tvec.length, l1 + l2 - 1e-4)
        dist = max(dist, abs(l1 - l2) + 1e-4)
        tdir = tvec.normalized()
        # joint position via law of cosines
        cosA = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
        A = math.acos(max(-1, min(1, cosA)))
        side = (pole - pole.dot(tdir) * tdir)
        if side.length < 1e-6:
            side = Vector((0, -1, 0))
        side.normalize()
        u1 = (tdir * math.cos(A) + side * math.sin(A)).normalized()
        joint = a + u1 * l1
        u2 = (a + tdir * dist - joint).normalized()
        par = self.rest[up][3]
        Dp = D[par]
        d1 = (self.rest[up][2] - self.rest[up][1]).normalized()
        q[up] = d1.rotation_difference(Dp.inverted() @ u1)
        D, P = self.fk(q, hips_off)
        d2 = (self.rest[lo][2] - self.rest[lo][1]).normalized()
        q[lo] = d2.rotation_difference(D[up].inverted() @ u2)
        if end and end_dir is not None:
            D, P = self.fk(q, hips_off)
            de = (self.rest[end][2] - self.rest[end][1]).normalized()
            q[end] = de.rotation_difference(D[lo].inverted() @ end_dir.normalized())
        return q

    def key(self, frame, q, hips_off=Vector((0, 0, 0)), root_off=None, root_rot=None):
        for bn in ORDER:
            pb = self.rig.pose.bones[bn]
            Rr = self.rest[bn][0]
            qb = q.get(bn, Quaternion())
            if bn == "root" and root_rot is not None:
                qb = root_rot @ qb
            pb.rotation_quaternion = Rr.inverted() @ qb @ Rr
            pb.keyframe_insert("rotation_quaternion", frame=frame)
        hb = self.rig.pose.bones["hips"]
        hb.location = self.rest["hips"][0].inverted() @ hips_off
        hb.keyframe_insert("location", frame=frame)
        rb = self.rig.pose.bones["root"]
        rb.location = self.rest["root"][0].inverted() @ (root_off or Vector((0, 0, 0)))
        rb.keyframe_insert("location", frame=frame)


def Q(axis, deg):
    ax = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}[axis] if isinstance(axis, str) else Vector(axis)
    return Quaternion(ax, math.radians(deg))


def QQ(*pairs):
    q = Quaternion()
    for ax, d in pairs:
        q = Q(ax, d) @ q
    return q
