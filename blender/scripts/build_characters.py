"""Task 2: the innies, the managers, the floor staff, Kier's wax likeness and the baby goats.
blender -b --factory-startup -P build_characters.py -- [--no-render] [--only mark,helly] [--anims idle,walk]
Writes assets/characters/<name>.gltf, assets/characters/anim_speeds.json, assets/ui/portrait_<name>.png,
renders/characters/*.png. Colours follow the sprites of the old web version (concept/old_cordova/*_run.png).
"""
import bpy
import sys
import os
import math
import json

sys.path.insert(0, os.path.dirname(__file__))
from lib_geo import *  # noqa
from lib_char import *  # noqa
import lib_render as R
import lib_char2 as H
from mathutils import Vector, Quaternion

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NO_RENDER = "--no-render" in ARGS
ONLY = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
ANIMS = ARGS[ARGS.index("--anims") + 1].split(",") if "--anims" in ARGS else None
SPEEDS = {}


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def relaxed_arms(q, amt=1.0):
    # adult proportions: the rest pose already hangs naturally, open the arms a touch so hands clear the hips
    q["upper_arm_L"] = Q("Y", -5 * amt) @ q.get("upper_arm_L", Quaternion())
    q["upper_arm_R"] = Q("Y", 5 * amt) @ q.get("upper_arm_R", Quaternion())
    q["forearm_L"] = Q("X", -12 * amt) @ q.get("forearm_L", Quaternion())
    q["forearm_R"] = Q("X", -12 * amt) @ q.get("forearm_R", Quaternion())
    return q


def gait(ph, amp, knee, arm, lean=0.0, arm_bend=15, bounce=0.02, crouch=0.0):
    """ph in radians. Left leg forward at ph=pi/2."""
    q = {}
    for s, sgn in (("L", 1), ("R", -1)):
        p = ph if s == "L" else ph + math.pi
        th = -amp * math.sin(p) - crouch
        kb = knee * max(0.0, math.cos(p)) ** 1.5 + 6 + crouch * 1.6
        q["thigh_" + s] = Q("X", th)
        q["shin_" + s] = Q("X", kb)
        q["foot_" + s] = Q("X", -(th + kb) * 0.5 + 5)
        a = arm * math.sin(p)
        q["upper_arm_" + s] = Q("X", a) @ Q("Y", -sgn * 4)
        q["forearm_" + s] = Q("X", -arm_bend - max(0, -a) * 0.6)
    q["hips"] = Q("Z", 6 * math.sin(ph) * (amp / 30))
    q["chest"] = Q("X", lean) @ Q("Z", -9 * math.sin(ph) * (amp / 30))
    q["head"] = Q("X", -lean * 0.6)
    hz = -bounce * abs(math.cos(ph)) - crouch * 0.004
    return q, Vector((0, 0, hz))


def _fcurves(act):
    try:
        return list(act.fcurves)
    except Exception:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out += list(cb.fcurves)
        return out


def make_action(rig, name, frames, fn, loop=True, poser=None):
    P = poser or Poser(rig)
    act = bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action = act
    for f in range(frames + 1):
        t = (f % frames) / frames if loop else f / frames
        res = fn(t, P)
        q, ho = res[0], res[1]
        extra = res[2] if len(res) > 2 else {}
        P.key(f, q, ho, root_off=extra.get("root_off"), root_rot=extra.get("root_rot"))
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    rig.animation_data.action = None
    tr = rig.animation_data.nla_tracks.new()
    tr.name = name
    st = tr.strips.new(name, 0, act)
    st.name = name
    tr.mute = True
    act.use_fake_user = True
    return act


# ------------------------------------------------------------------ animation library
def A_idle(t, P):
    ph = 2 * math.pi * t
    q = relaxed_arms({})
    q["chest"] = Q("X", 1.5 * math.sin(ph))
    q["head"] = Q("Z", 5 * math.sin(ph)) @ Q("X", -1.5 * math.sin(ph))
    q["upper_arm_L"] = Q("X", 2 * math.sin(ph)) @ q["upper_arm_L"]
    q["upper_arm_R"] = Q("X", -2 * math.sin(ph)) @ q["upper_arm_R"]
    return q, Vector((0, 0, -0.004 * (1 + math.sin(ph))))


def A_walk(t, P):
    return gait(2 * math.pi * t, 26, 45, 22)


def A_run(t, P):
    q, h = gait(2 * math.pi * t, 42, 85, 40, lean=12, arm_bend=75, bounce=0.05)
    return q, h + Vector((0, 0, 0.02))


def A_sneak(t, P):
    q, h = gait(2 * math.pi * t, 20, 50, 10, lean=22, arm_bend=60, bounce=0.01, crouch=25)
    return q, h - Vector((0, 0, 0.05))


def A_talk(t, P):
    ph = 2 * math.pi * t
    q = relaxed_arms({})
    q["upper_arm_R"] = Q("X", -30 - 15 * math.sin(2 * ph)) @ Q("Y", -15)
    q["forearm_R"] = Q("X", -50 + 20 * math.sin(3 * ph))
    q["upper_arm_L"] = Q("X", -15 - 10 * math.sin(ph + 1)) @ q["upper_arm_L"]
    q["forearm_L"] = Q("X", -40)
    q["head"] = Q("Z", 8 * math.sin(ph)) @ Q("X", 4 * math.sin(2 * ph))
    q["chest"] = Q("Z", 3 * math.sin(ph))
    return q, Vector((0, 0, 0))


def A_interact(t, P):
    """Standing, both hands working a panel / keypad in front of the chest."""
    ph = 2 * math.pi * t
    q = {}
    for s, sx, o in (("L", 1, 0), ("R", -1, math.pi)):
        q["upper_arm_" + s] = Q("X", -50 - 6 * math.sin(2 * ph + o)) @ Q("Y", sx * 12)
        q["forearm_" + s] = Q("X", -45 - 10 * max(0, math.sin(2 * ph + o)))
    q["chest"] = Q("X", 6)
    q["head"] = Q("X", 8 + 3 * math.sin(ph))
    return q, Vector((0, 0, 0))


def sit_pose(q=None):
    q = q or {}
    for s in ("L", "R"):
        q["thigh_" + s] = Q("X", -88)
        q["shin_" + s] = Q("X", 88)
        q["foot_" + s] = Q("X", 0)
    return q, H.SIT_HIPS.copy()


def A_sit(t, P):
    q, h = sit_pose(relaxed_arms({}))
    q["chest"] = Q("X", -3 + 1.5 * math.sin(2 * math.pi * t))
    q["upper_arm_L"] = Q("X", -25) @ q["upper_arm_L"]
    q["upper_arm_R"] = Q("X", -25) @ q["upper_arm_R"]
    q["forearm_L"] = Q("X", -30)
    q["forearm_R"] = Q("X", -30)
    return q, h


def A_sit_type(t, P):
    """Seated at the terminal: typing, the right hand rolling the trackball now and then."""
    ph = 2 * math.pi * t
    q, h = sit_pose({})
    for s, sx, o in (("L", 1, 0.0), ("R", -1, 1.7)):
        tap = max(0.0, math.sin(6 * ph + o)) ** 3
        q["upper_arm_" + s] = Q("X", -38 - 4 * tap) @ Q("Y", sx * 14)
        q["forearm_" + s] = Q("X", -58 + 8 * tap)
    roll = max(0.0, math.sin(ph))
    q["upper_arm_R"] = Q("Z", -10 * roll) @ q["upper_arm_R"]
    q["chest"] = Q("X", 8)
    q["head"] = Q("X", 4 + 3 * math.sin(2 * ph)) @ Q("Z", 4 * math.sin(ph))
    return q, h


def A_sleep_sit(t, P):
    ph = 2 * math.pi * t
    q, h = sit_pose(relaxed_arms({}))
    q["chest"] = Q("X", 10 + 2 * math.sin(ph))
    q["head"] = Q("X", 32 + 3 * math.sin(ph)) @ Q("Z", 8)
    q["upper_arm_L"] = Q("X", -20) @ q["upper_arm_L"]
    q["upper_arm_R"] = Q("X", -20) @ q["upper_arm_R"]
    q["forearm_L"] = Q("X", -50)
    q["forearm_R"] = Q("X", -50)
    return q, h + Vector((0, 0, -0.01 * math.sin(ph)))


def A_dance(t, P):
    """Defiant Jazz: bouncing, alternate fists pumping up, torso twisting."""
    ph = 2 * math.pi * t
    q = {}
    b = abs(math.sin(2 * ph))
    for s, sx, o in (("L", 1, 0.0), ("R", -1, math.pi)):
        up = 0.5 + 0.5 * math.sin(2 * ph + o)
        q["upper_arm_" + s] = Q("Y", sx * (-30 - 100 * up)) @ Q("X", -20)
        q["forearm_" + s] = Q("X", -40 - 50 * (1 - up))
        q["thigh_" + s] = Q("X", -18 * max(0, math.sin(2 * ph + o)))
        q["shin_" + s] = Q("X", 30 * max(0, math.sin(2 * ph + o)))
    q["chest"] = Q("Z", 14 * math.sin(2 * ph)) @ Q("X", -4)
    q["hips"] = Q("Z", -10 * math.sin(2 * ph))
    q["head"] = Q("X", -8 * b) @ Q("Z", 10 * math.sin(2 * ph + 0.6))
    return q, Vector((0, 0, 0.06 * b))


def A_dance2(t, P):
    """Side-step shuffle with swinging arms and a hip wiggle."""
    ph = 2 * math.pi * t
    q = {}
    sway = math.sin(ph)
    for s, sx in (("L", 1), ("R", -1)):
        lift = max(0.0, sx * math.sin(ph))
        q["thigh_" + s] = Q("X", -25 * lift) @ Q("Y", sx * 8)
        q["shin_" + s] = Q("X", 45 * lift)
        q["upper_arm_" + s] = Q("X", -50 * math.sin(2 * ph) * sx) @ Q("Y", sx * 40)
        q["forearm_" + s] = Q("X", -70)
    q["hips"] = Q("Y", 10 * sway)
    q["chest"] = Q("Y", -12 * sway)
    q["head"] = Q("Y", 8 * sway) @ Q("X", -6)
    return q, Vector((0.1 * sway, 0, 0.03 * abs(math.cos(ph))))


def A_cheer(t, P):
    ph = 2 * math.pi * t
    q = {}
    jump = max(0, math.sin(ph))
    for s, sx in (("L", 1), ("R", -1)):
        q["upper_arm_" + s] = Q("Y", sx * (-130 + 15 * math.sin(2 * ph))) @ Q("X", -10)
        q["forearm_" + s] = Q("X", -20)
        q["thigh_" + s] = Q("X", -20 * jump)
        q["shin_" + s] = Q("X", 35 * jump)
    q["head"] = Q("X", -10)
    return q, Vector((0, 0, 0.18 * jump))


def A_lever(t, P):
    """Holding the OTC lever down with both hands, straining."""
    ph = 2 * math.pi * t
    q = {}
    sh = 2.0 * math.sin(8 * ph)
    for s, sx in (("L", 1), ("R", -1)):
        q["upper_arm_" + s] = Q("X", -70 + sh) @ Q("Y", sx * 8)
        q["forearm_" + s] = Q("X", -25)
        q["thigh_" + s] = Q("X", -20)
        q["shin_" + s] = Q("X", 30)
    q["chest"] = Q("X", 18)
    q["head"] = Q("X", -10)
    return q, Vector((0, 0, -0.06))


def A_read(t, P):
    ph = 2 * math.pi * t
    q = {}
    for s, sx in (("L", 1), ("R", -1)):
        q["upper_arm_" + s] = Q("X", -25) @ Q("Y", sx * 10)
        q["forearm_" + s] = Q("X", -95) @ Q("Y", -sx * 25)
    q["head"] = Q("X", 18 + 2 * math.sin(ph)) @ Q("Z", 6 * math.sin(ph * 2))
    q["chest"] = Q("X", 4)
    return q, Vector((0, 0, 0))


def A_feed(t, P):
    ph = 2 * math.pi * t
    q = relaxed_arms({})
    q["upper_arm_R"] = Q("X", -65 + 5 * math.sin(2 * ph)) @ Q("Y", -10)
    q["forearm_R"] = Q("X", -15)
    q["chest"] = Q("X", 16)
    q["head"] = Q("X", 14)
    for s in ("L", "R"):
        q["thigh_" + s] = Q("X", -25)
        q["shin_" + s] = Q("X", 45)
    return q, Vector((0, 0, -0.08))


def A_lie(t, P):
    ph = 2 * math.pi * t
    q = {}
    for s, sx in (("L", 1), ("R", -1)):
        q["upper_arm_" + s] = Q("Y", sx * 8)
    q["chest"] = Q("X", 1.5 * math.sin(ph))
    return q, Vector((0, 0, 0)), dict(root_rot=Q("X", -90), root_off=Vector((0, 0, 0.17)))


def A_point(t, P):
    ph = 2 * math.pi * t
    q = relaxed_arms({})
    q["upper_arm_R"] = Q("X", -85) @ Q("Y", -5)
    q["forearm_R"] = Q("X", -5 - 4 * math.sin(2 * ph))
    q["head"] = Q("Z", -6)
    return q, Vector((0, 0, 0))


def A_wave(t, P):
    ph = 2 * math.pi * t
    q = relaxed_arms({})
    q["upper_arm_R"] = Q("Y", 140) @ Q("X", -10)
    q["upper_arm_R"] = Q("Y", -150) @ Q("X", -10)
    q["forearm_R"] = Q("Y", 30 * math.sin(2 * ph)) @ Q("X", -10)
    q["head"] = Q("Z", -5) @ Q("X", -4)
    return q, Vector((0, 0, 0))


def A_nervous(t, P):
    """Arms crossed, glancing around (waiting innies, Helly before the Break Room)."""
    ph = 2 * math.pi * t
    q = {}
    for s, sx in (("L", 1), ("R", -1)):
        q["upper_arm_" + s] = Q("X", -30) @ Q("Y", sx * 12)
        q["forearm_" + s] = Q("Z", -sx * 80) @ Q("X", -80)
    q["head"] = Q("Z", 20 * math.sin(ph)) @ Q("X", -3)
    q["chest"] = Q("Z", 3 * math.sin(ph))
    return q, Vector((0, 0, 0))


def A_statue(t, P):
    """Kier's wax pose: chin up, right hand on a cane, left hand on the lapel."""
    q = {}
    q["head"] = Q("X", -8)
    q["upper_arm_R"] = Q("X", -20) @ Q("Y", -25)
    q["forearm_R"] = Q("X", -30)
    q["upper_arm_L"] = Q("X", -15) @ Q("Y", 10)
    q["forearm_L"] = Q("Z", -70) @ Q("X", -90)
    q["thigh_R"] = Q("Y", -6)
    return q, Vector((0, 0, 0))


LIB = [  # name, frames, fn, loop
    ("idle", 48, A_idle, True), ("walk", 24, A_walk, True), ("run", 16, A_run, True), ("sneak", 30, A_sneak, True),
    ("talk", 48, A_talk, True), ("interact", 24, A_interact, True), ("sit", 48, A_sit, True),
    ("sit_type", 48, A_sit_type, True), ("sleep_sit", 72, A_sleep_sit, True), ("dance", 24, A_dance, True),
    ("dance2", 32, A_dance2, True), ("cheer", 24, A_cheer, True), ("lever", 24, A_lever, True),
    ("read", 48, A_read, True), ("feed", 36, A_feed, True), ("lie", 72, A_lie, True), ("point", 36, A_point, True),
    ("wave", 24, A_wave, True), ("nervous", 72, A_nervous, True),
]
STATUE_LIB = [("statue", 2, A_statue, True)]
SPEED_ANIMS = {"walk": 24, "run": 16, "sneak": 30}


def measure_speed(rig, act_name, frames):
    P = Poser(rig)
    fn = dict((n, f) for n, _, f, _ in LIB)[act_name]
    xs = []
    for f in range(frames):
        q, ho = fn(f / frames, P)[:2]
        D_, Pp = P.fk(q, ho)
        tipL = P.tip(D_, Pp, "foot_L")
        tipR = P.tip(D_, Pp, "foot_R")
        xs.append((tipL.y, tipL.z, tipR.y, tipR.z))
    dist = 0.0
    for i in range(frames):
        a, b = xs[i], xs[(i + 1) % frames]
        if a[1] <= a[3]:
            dist += max(0.0, b[0] - a[0])
        else:
            dist += max(0.0, b[2] - a[2])
    return round(dist / (frames / FPS), 3)


# ------------------------------------------------------------------ costume pieces
def suit(shirt="#f2f2ee", tie="#2a2f3a", lapel=None, buttons=True):
    def f(B):
        sh = mat("shirt_" + shirt.lstrip("#"), shirt)
        B.add(prism("shirtv", [(-0.075, 0.2), (0.075, 0.2), (0, 0)], 0.012, (0, -0.148, 1.02), sh, axis="Y"), "chest")
        B.add(prism("tie", [(-0.022, 0), (0.022, 0), (0.03, -0.2), (0, -0.24), (-0.03, -0.2)], 0.01,
                    (0, -0.16, 1.215), mat("tie_" + tie.lstrip("#"), tie), axis="Y"), "chest")
        B.add(torus("collar", 0.07, 0.022, (0, -0.005, 1.205), sh), "chest")
        if lapel:
            lm = mat("lapel_" + lapel.lstrip("#"), lapel)
            for sx in (-1, 1):
                B.add(box("lapel%d" % sx, (0.035, 0.015, 0.22), (sx * 0.085, -0.15, 1.0), lm,
                          rot=(0, math.radians(sx * 18), 0)), "chest")
        if buttons:
            for k in range(2):
                B.add(sphere("btn%d" % k, 0.011, (0.0, -0.165, 0.9 - k * 0.07), mat("btn_dark", "#1d1f22"), seg=6,
                             rings=4), "spine")
    return f


def lanyard(c="#1f3a5f"):
    def f(B):
        m = mat("lanyard_" + c.lstrip("#"), c)
        for sx in (-1, 1):
            B.add(tube_path("lan%d" % sx, [(sx * 0.07, -0.03, 1.22), (sx * 0.06, -0.14, 1.12), (sx * 0.02, -0.168, 1.0)],
                            0.007, m, n=5), "chest")
        B.add(box("badge", (0.06, 0.008, 0.08), (0.0, -0.172, 0.93), mat("badge", "#f6f6f0")), "chest")
        B.add(box("badgestripe", (0.05, 0.004, 0.015), (0.0, -0.177, 0.975), mat("badge_blue", "#1f3a5f")), "chest")
    return f


def short_sleeves(c):
    def f(B):
        m = mat("cloth_" + c.lstrip("#"), c)
        for s in ("L", "R"):
            a = Vector(SK["upper_arm_" + s][0])
            b = a + (Vector(SK["upper_arm_" + s][1]) - a) * 0.6
            B.capsule("ssl" + s, a, b, 0.068, 0.062, m, "upper_arm_" + s)
    return f


def apron(c):
    def f(B):
        m = mat("apron_" + c.lstrip("#"), c)
        B.add(box("bib", (0.24, 0.012, 0.22), (0, -0.15, 1.0), m), "chest")
        B.add(box("aprsk", (0.36, 0.012, 0.42), (0, -0.155, 0.42), m), "hips")
        B.add(torus("aprstrap", 0.165, 0.01, (0, 0, 0.86), m), "spine")
    return f


def cardigan(c):
    def f(B):
        m = mat("cardi_" + c.lstrip("#"), c)
        for sx in (-1, 1):
            B.add(box("cardi%d" % sx, (0.1, 0.02, 0.38), (sx * 0.1, -0.145, 0.88), m, bevel=0.01), "chest")
    return f


def hair_bob(c):
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        B.add(sphere("bob", 0.228, (0, 0.035, 1.55), m, seg=16, rings=10, scale=(1.05, 1.02, 0.85)), "head")
        for sx in (-1, 1):
            B.add(sphere("bobside%d" % sx, 0.11, (sx * 0.17, 0.04, 1.42), m, seg=12, rings=8, scale=(0.75, 1.3, 1.3)),
                  "head")
        B.add(sphere("bobback", 0.2, (0, 0.1, 1.42), m, seg=12, rings=8, scale=(1.1, 0.8, 1.1)), "head")
        B.add(box("bangs", (0.3, 0.07, 0.06), (0, -0.165, 1.63), m, bevel=0.025), "head")
    return f


def hair_slick(c):
    """Short, neat hair with a side part (Milchick)."""
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        B.add(sphere("hsl", 0.215, (0, 0.03, 1.55), m, seg=16, rings=10, scale=(1.02, 1.0, 0.72)), "head")
    return f


def beard(c):
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        B.add(sphere("beard", 0.15, (0, -0.1, 1.33), m, seg=12, rings=8, scale=(1.15, 0.8, 0.9)), "head")
    return f


def bald_sides(c):
    def f(B):
        m = mat("hair_" + c.lstrip("#"), c)
        for sx in (-1, 1):
            B.add(sphere("side%d" % sx, 0.1, (sx * 0.17, 0.07, 1.48), m, seg=10, rings=8, scale=(0.6, 1.1, 0.9)), "head")
        B.add(sphere("back", 0.15, (0, 0.15, 1.47), m, seg=10, rings=8, scale=(1.2, 0.6, 0.9)), "head")
    return f


def lashes(B):
    m = mat("lash", "#2b2320")
    for sx in (-1, 1):
        B.add(box("lash%d" % sx, (0.06, 0.01, 0.012), (sx * 0.075, -0.2, 1.53), m, rot=(0, math.radians(sx * -15), 0)),
              "head")


def headset(B):
    m = mat("black", "black")
    B.add(torus("hs", 0.225, 0.012, (0, 0.02, 1.5), m, rot=(math.radians(90), 0, 0)), "head")
    B.add(sphere("hsear", 0.05, (-0.21, 0, 1.47), m, seg=8, rings=6), "head")


def cane(B):
    w = mat("darkwood", "darkwood")
    p = Vector(SK["hand_R"][1])
    B.add(tube_path("cane", [(p.x - 0.02, p.y - 0.05, 0.0), (p.x, p.y - 0.02, p.z + 0.05)], 0.018, w, n=6), "hand_R")
    B.add(sphere("knob", 0.035, (p.x, p.y - 0.02, p.z + 0.06), mat("brass", "brass", metal=0.8), seg=8, rings=6), "hand_R")


def vest(c):
    def f(B):
        m = mat("vest_" + c.lstrip("#"), c)
        B.add(sphere("vest", 0.188, (0, -0.01, 1.04), m, seg=16, rings=10, scale=(1.02, 0.78, 0.9)), "chest")
    return f


ROSTER = {
    # the innies of Macrodata Refinement (original designs; colours from the old game's sprites)
    "mark": dict(skin="#e3b08c", top="suit", top_c="#3b4047", pants="#3b4047", shirt="#f0f0ea", tie="#27303e",
                 lapel="#33373d", hair_c="#3a2a1f", stubble="#b98f74", eyes="#5a4330", jaw=1.06,
                 extras=[H.hair_short_part("#3a2a1f"), H.lanyard()]),
    "helly": dict(skin="#f1c7ab", female=True, top="blouse", top_c="#3b6aa8", skirt="#202228", pants="#e8bea2",
                  shoes="#1d1f22", hair_c="#a8422a", eyes="#4b6a3a", lip="#c0756a", bare_legs=True, heels=True,
                  extras=[H.hair_ponytail("#a8422a"), H.lanyard()]),
    "dylan": dict(skin="#e6b18d", top="shirt", top_c="#7aa6d6", sleeves="short", tie="#26324d", pants="#2a2c32",
                  hair_c="#4e3422", glasses=True, belly=0.035, jaw=1.08, eyes="#3d2a1c",
                  extras=[H.hair_wavy("#4e3422"), H.lanyard()]),
    "irving": dict(skin="#e2ad8c", top="suit", top_c="#25304a", pants="#25304a", tie="#1e2a44", lapel="#1f2940",
                   hair_c="#a7a7a5", brow_c="#8c8c8a", mustache="#9a9a98", height=1.04, eyes="#4a5560",
                   extras=[H.hair_combed_back("#a7a7a5"), H.lanyard(), H.pocket_square()]),
    # management and staff
    "milchick": dict(skin="#7a4a35", top="shirt", top_c="#f3f3ef", tie="#55606c", pants="#2c2e34", hair_c="#161414",
                     mustache="#161414", height=1.02, eyes="#2a1a12", lip="#6e3e34",
                     extras=[H.hair_slick("#161414")]),
    "cobel": dict(skin="#efc8b2", female=True, top="dress", top_c="#4a6a9a", pants="#3a3a42", skirt=None,
                  shoes="#1d1f22", hair_c="#c4c4ca", brow_c="#9a9aa0", eyes="#5d7088", lip="#b97a74", heels=True,
                  extras=[H.hair_bun("#c4c4ca", low=True), H.cardigan("#34507a")]),
    "burt": dict(skin="#ebbfa0", top="shirt", top_c="#b7bcc2", pants="#3a3d44", shoes="#3a2a20", hair_c="#e6e6e4",
                 glasses=True, mustache="#e2e2e0", height=1.01, eyes="#5a6a74",
                 extras=[H.hair_bald_sides("#e6e6e4"), H.apron("#6f8f4a"), H.lanyard("#5f8c6a")]),
    "casey": dict(skin="#efcab3", female=True, top="dress", top_c="#8aa7ad", pants="#e9c4ae", shoes="#3a3d44",
                  hair_c="#e3cc8a", brow_c="#c9b07a", eyes="#6a8aa0", lip="#c48a80", height=0.97, bare_legs=True,
                  extras=[H.hair_bob("#e3cc8a")]),
    "graner": dict(skin="#e0ae90", top="suit", top_c="#1f2a40", pants="#1f2a40", tie="#1b2235", lapel="#18213a",
                   hair_c="#8e8e8e", glasses=True, belly=0.03, height=1.03, jaw=1.1, eyes="#4a4a4a",
                   extras=[H.hair_short_part("#8e8e8e"), H.headset]),
    "keeper": dict(skin="#e6b896", female=True, top="labcoat", top_c="#f1f1eb", pants="#4a4f57", shoes="#e6e6e0",
                   hair_c="#6b4a2e", glasses=True, eyes="#4a3a2a", extras=[H.hair_bun("#6b4a2e")]),
    # Kier Eagan's wax likeness (Perpetual Wing)
    "kier": dict(skin="#ecd2ba", top="coat", top_c="#1c1c20", pants="#1c1c20", shoes="#2a1e16", shirt="#e9e2d2",
                 tie="#3a2c22", hair_c="#c9c4ba", beard="#c9c4ba", mustache="#c9c4ba", height=1.05, statue=True,
                 extras=[H.hair_combed_back("#c9c4ba"), H.vest("#5a4630"), H.cane]),
}


# ------------------------------------------------------------------ the baby goat (own small rig)
GOAT_BONES = {
    "root": ((0, 0, 0), (0, 0, 0.1), None),
    "body": ((0, 0.12, 0.32), (0, -0.12, 0.32), "root"),
    "neck": ((0, -0.15, 0.38), (0, -0.22, 0.5), "body"),
    "head": ((0, -0.22, 0.5), (0, -0.33, 0.52), "neck"),
    "tail": ((0, 0.2, 0.38), (0, 0.27, 0.46), "body"),
}
for nm, (x, y) in (("FL", (0.07, -0.13)), ("FR", (-0.07, -0.13)), ("BL", (0.07, 0.15)), ("BR", (-0.07, 0.15))):
    GOAT_BONES["leg_" + nm] = ((x, y, 0.27), (x, y, 0.0), "body")
GOAT_ORDER = ["root", "body", "neck", "head", "tail", "leg_FL", "leg_FR", "leg_BL", "leg_BR"]


def build_goat(coll):
    arm = bpy.data.armatures.new("goat_rig")
    rig = bpy.data.objects.new("goat_rig", arm)
    coll.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bn in GOAT_ORDER:
        h, t, p = GOAT_BONES[bn]
        eb = arm.edit_bones.new(bn)
        eb.head, eb.tail = Vector(h), Vector(t)
        if p:
            eb.parent = arm.edit_bones[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    fur = mat("goat_fur", "#f1ece2", rough=0.95)
    spot = mat("goat_spot", "#7a5a3e", rough=0.95)
    B = Body("goat", coll)
    B.add(sphere("torso", 0.17, (0, 0.0, 0.34), fur, scale=(0.85, 1.4, 0.85)), "body")
    B.add(sphere("spot", 0.09, (0.08, 0.06, 0.41), spot, scale=(0.6, 1.2, 0.8)), "body")
    B.add(sphere("neckm", 0.07, (0, -0.19, 0.43), fur, scale=(1, 1, 1.4)), "neck")
    B.add(sphere("headm", 0.115, (0, -0.28, 0.55), fur, scale=(0.85, 1.2, 0.9)), "head")
    B.add(sphere("snout", 0.055, (0, -0.39, 0.52), mat("goat_nose", "#e8c4b4"), scale=(0.9, 1.0, 0.8)), "head")
    for sx in (-1, 1):
        B.add(sphere("ear%d" % sx, 0.04, (sx * 0.12, -0.25, 0.57), spot, scale=(1.8, 0.6, 0.6)), "head")
        B.add(sphere("eye%d" % sx, 0.02, (sx * 0.065, -0.36, 0.59), mat("eye_pupil", "#2b2320"), seg=8, rings=6), "head")
        B.add(cyl("horn%d" % sx, 0.015, 0.045, (sx * 0.04, -0.26, 0.64), mat("horn", "#d9cbb0"), n=6, r2=0.005), "head")
    B.add(sphere("tailm", 0.03, (0, 0.24, 0.43), fur, scale=(1, 1, 1.6)), "tail")
    for nm in ("FL", "FR", "BL", "BR"):
        h, t, _ = GOAT_BONES["leg_" + nm]
        B.capsule("leg" + nm, h, (t[0], t[1], 0.05), 0.035, 0.028, fur, "leg_" + nm)
        B.add(cyl("hoof" + nm, 0.03, 0.05, (t[0], t[1], 0.0), mat("hoof", "#3a2e26"), n=8), "leg_" + nm)
    meshes = B.finish(rig)
    return rig, meshes


class GoatPoser(Poser):
    def __init__(self, rig):
        self.rig = rig
        self.rest = {}
        for b in rig.data.bones:
            self.rest[b.name] = (b.matrix_local.to_quaternion(), Vector(b.head_local), Vector(b.tail_local),
                                 b.parent.name if b.parent else None)

    def key(self, frame, q, hips_off=Vector((0, 0, 0)), root_off=None, root_rot=None):
        for bn in GOAT_ORDER:
            pb = self.rig.pose.bones[bn]
            Rr = self.rest[bn][0]
            qb = q.get(bn, Quaternion())
            pb.rotation_quaternion = Rr.inverted() @ qb @ Rr
            pb.keyframe_insert("rotation_quaternion", frame=frame)
        rb = self.rig.pose.bones["root"]
        rb.location = self.rest["root"][0].inverted() @ (hips_off or Vector((0, 0, 0)))
        rb.keyframe_insert("location", frame=frame)


def G_idle(t, P):
    ph = 2 * math.pi * t
    return {"head": Q("X", 6 * math.sin(ph)) @ Q("Z", 12 * math.sin(ph * 0.5 * 2)),
            "tail": Q("Z", 30 * math.sin(4 * ph))}, Vector((0, 0, 0))


def G_walk(t, P):
    ph = 2 * math.pi * t
    q = {}
    for nm, o in (("FL", 0), ("BR", 0), ("FR", math.pi), ("BL", math.pi)):
        q["leg_" + nm] = Q("X", 28 * math.sin(ph + o))
    q["head"] = Q("X", 5 * math.sin(2 * ph))
    q["tail"] = Q("Z", 25 * math.sin(3 * ph))
    return q, Vector((0, 0, 0.02 * abs(math.sin(ph))))


def G_eat(t, P):
    ph = 2 * math.pi * t
    return {"neck": Q("X", 55), "head": Q("X", 15 + 8 * math.sin(4 * ph)), "tail": Q("Z", 20 * math.sin(3 * ph))}, \
        Vector((0, 0, 0))


def G_hop(t, P):
    ph = 2 * math.pi * t
    j = max(0, math.sin(ph))
    q = {"body": Q("X", -15 * math.sin(ph)), "head": Q("X", -10 * j), "tail": Q("Z", 40 * math.sin(6 * ph))}
    for nm in ("FL", "FR", "BL", "BR"):
        q["leg_" + nm] = Q("X", (-25 if nm[0] == "F" else 25) * j)
    return q, Vector((0, 0, 0.22 * j))


GOAT_LIB = [("idle", 48, G_idle, True), ("walk", 16, G_walk, True), ("eat", 48, G_eat, True), ("hop", 20, G_hop, True)]


# ------------------------------------------------------------------ build / export / renders
def build(name, spec):
    coll = collection(name)
    rig, meshes = H.human(name, coll, spec)
    if spec.get("height"):
        rig.scale = (spec["height"],) * 3
    lib = STATUE_LIB if spec.get("statue") else [x for x in LIB if (ANIMS is None or x[0] in ANIMS)]
    for an, frames, fn, loop in lib:
        make_action(rig, an, frames, fn, loop)
    return rig, meshes


def export_char(rig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for c in rig.children:
        c.select_set(True)
    bpy.context.view_layer.objects.active = rig
    tex_rel = os.path.relpath(TEX, os.path.dirname(path)).replace("\\", "/")
    kw = dict(filepath=path, export_format="GLTF_SEPARATE", use_selection=True, export_apply=False,
              export_texture_dir=tex_rel, export_animations=True, export_yup=True, export_skins=True,
              export_frame_range=False, export_force_sampling=True, export_def_bones=False)
    for mode in ("NLA_TRACKS", "ACTIONS"):
        try:
            bpy.ops.export_scene.gltf(export_animation_mode=mode, **kw)
            print("exported", path, mode)
            return
        except TypeError as e:
            print("export retry", e)
    bpy.ops.export_scene.gltf(**kw)


def pose_at(rig, P, fn, t):
    res = fn(t, P)
    extra = res[2] if len(res) > 2 else {}
    P.key(0, res[0], res[1], root_off=extra.get("root_off"), root_rot=extra.get("root_rot"))
    bpy.context.scene.frame_set(0)


def render_char(rig, meshes, name, statue=False, goat=False):
    P = GoatPoser(rig) if goat else Poser(rig)
    rig.animation_data.action = None
    for tr in rig.animation_data.nla_tracks:
        tr.mute = True
    R.isolate([rig] + meshes)
    act = bpy.data.actions.new("preview")
    rig.animation_data.action = act
    h = rig.scale.z
    if goat:
        poses = [("idle", G_idle, 0.0), ("walk", G_walk, 0.25), ("eat", G_eat, 0.2), ("hop", G_hop, 0.25)]
    elif statue:
        poses = [("statue", A_statue, 0.0)]
    else:
        poses = [("idle", A_idle, 0.0), ("walk", A_walk, 0.25), ("run", A_run, 0.3), ("sit_type", A_sit_type, 0.1),
                 ("dance", A_dance, 0.25), ("lever", A_lever, 0.0), ("read", A_read, 0.0), ("sneak", A_sneak, 0.25)]
    for pn, fn, t in poses:
        pose_at(rig, P, fn, t)
        if goat:
            R.camera(loc=(1.0, -1.6, 0.9), target=(0, 0, 0.35), lens=45)
        else:
            R.camera(loc=(1.6 * h, -3.0 * h, 1.5 * h), target=(0, 0, 0.85 * h), lens=45)
        R.render(os.path.join(RENDERS, "characters", "%s_%s.png" % (name, pn)))
    if goat:
        sc = bpy.context.scene
        sc.render.film_transparent = True
        sc.render.resolution_x = sc.render.resolution_y = 256
        gp = bpy.data.objects.get("PREVIEW_GROUND")
        if gp:
            gp.hide_render = True
        pose_at(rig, P, G_idle, 0.0)
        R.camera(loc=(0.9, -1.5, 0.75), target=(0, -0.08, 0.38), lens=50)
        R.render(os.path.join(ASSETS, "ui", "portrait_goat.png"))
        return
    # iso-view check (the game camera: yaw 45, pitch ~38, orthographic)
    pose_at(rig, P, poses[0][1], 0.0)
    R.camera(loc=(4, -4, 4.6), target=(0, 0, 0.9 * h), ortho=2.6)
    R.render(os.path.join(RENDERS, "characters", "%s_iso.png" % name))
    # portrait for the UI (transparent background, head and shoulders)
    sc = bpy.context.scene
    old = (sc.render.resolution_x, sc.render.resolution_y)
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 256
    gp = bpy.data.objects.get("PREVIEW_GROUND")
    if gp:
        gp.hide_render = True
    pose_at(rig, P, A_idle, 0.0)
    R.camera(loc=(0.42 * h, -1.45 * h, 1.72 * h), target=(0, 0, 1.6 * h), lens=70)
    R.render(os.path.join(ASSETS, "ui", "portrait_%s.png" % name))
    sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = old
    if gp:
        gp.hide_render = False


def setup_scene():
    reset()
    std_mats()
    R.setup_render((360, 420))
    R.world("#d9dde2")
    R.sun(energy=3.0)
    R.ground_plane(color="#c9ccd1")


def main():
    for name, spec in ROSTER.items():
        if ONLY and name not in ONLY:
            continue
        setup_scene()
        rig, meshes = build(name, spec)
        if name == "mark":
            for an, fr in SPEED_ANIMS.items():
                SPEEDS[an] = measure_speed(rig, an, fr)
        export_char(rig, os.path.join(ASSETS, "characters", name + ".gltf"))
        print("built", name)
        if not NO_RENDER:
            render_char(rig, meshes, name, statue=spec.get("statue", False))
    if not ONLY or "goat" in ONLY:
        setup_scene()
        coll = collection("goat")
        rig, meshes = build_goat(coll)
        P = GoatPoser(rig)
        for an, frames, fn, loop in GOAT_LIB:
            make_action(rig, an, frames, fn, loop, poser=P)
        export_char(rig, os.path.join(ASSETS, "characters", "goat.gltf"))
        print("built goat")
        if not NO_RENDER:
            render_char(rig, meshes, "goat", goat=True)
    if SPEEDS:
        json.dump(dict(speeds_mps=SPEEDS, fps=FPS), open(os.path.join(ASSETS, "characters", "anim_speeds.json"), "w"),
                  indent=1)
        print("speeds", SPEEDS)
    print("DONE")


if __name__ == "__main__":
    main()
