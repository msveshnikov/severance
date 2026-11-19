"""Preview renders, mood switching and contact sheets."""
import bpy
import math
import os
from mathutils import Vector
from lib_geo import hexrgb, MATS


def setup_render(res=(640, 480), engine_pref=("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH")):
    s = bpy.context.scene
    for e in engine_pref:
        try:
            s.render.engine = e
            break
        except TypeError:
            continue
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.film_transparent = False
    try:
        s.eevee.taa_render_samples = 16
    except Exception:
        pass
    try:
        s.view_settings.view_transform = "Standard"
        s.view_settings.look = "None"
    except Exception:
        pass
    return s


def world(color="#bfe3f5", strength=1.0):
    w = bpy.data.worlds.get("W") or bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = hexrgb(color) + (1,)
    bg.inputs["Strength"].default_value = strength


def sun(name="SUN", energy=3.5, rot=(50, 0, 35), color="#fff3dc"):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ld = bpy.data.lights.new(name, "SUN")
        ob = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(ob)
    ob.data.energy = energy
    ob.data.color = hexrgb(color)
    ob.data.angle = math.radians(8)
    ob.rotation_euler = tuple(math.radians(a) for a in rot)
    return ob


MOODS = {
    "day": dict(world="#bfe3f5", ws=1.0, sun=3.5, sun_rot=(50, 0, 35), sun_col="#fff3dc", emit=0.0),
    "evening": dict(world="#f2b48a", ws=0.6, sun=2.2, sun_rot=(75, 0, -60), sun_col="#ffb36b", emit=1.5),
    "night": dict(world="#1d2b55", ws=0.25, sun=0.25, sun_rot=(60, 0, 120), sun_col="#9fb6ff", emit=4.0),
    "rain": dict(world="#9aa8b5", ws=0.7, sun=1.0, sun_rot=(55, 0, 30), sun_col="#dfe8f0", emit=0.6),
}


def mood(name):
    m = MOODS[name]
    world(m["world"], m["ws"])
    sun(energy=m["sun"], rot=m["sun_rot"], color=m["sun_col"])
    for mt in bpy.data.materials:
        if mt.name.startswith(("EMIT_window", "EMIT_lamp", "EMIT_neon", "EMIT_clock", "EMIT_sign")):
            b = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if b:
                b.inputs["Emission Strength"].default_value = m["emit"]
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.data.type != "SUN":
            ob.hide_render = name in ("day",)


def bbox(objs):
    pts = []
    for o in objs:
        if o.type == "MESH" and not o.name.endswith("-colonly"):
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    if not pts:
        return Vector((0, 0, 0)), Vector((1, 1, 1))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def camera(name="CAM", loc=(0, -10, 5), target=(0, 0, 1), lens=40, ortho=None):
    ob = bpy.data.objects.get(name)
    if ob is None:
        cd = bpy.data.cameras.new(name)
        ob = bpy.data.objects.new(name, cd)
        bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        ob.data.type = "ORTHO"
        ob.data.ortho_scale = ortho
    else:
        ob.data.type = "PERSP"
        ob.data.lens = lens
    ob.data.clip_end = 2000
    bpy.context.scene.camera = ob
    return ob


def frame_objects(objs, yaw=-30, pitch=22, lens=45, margin=1.15):
    mn, mx = bbox(objs)
    c = (mn + mx) / 2
    size = (mx - mn).length
    dist = size * margin / (2 * math.tan(math.atan(18 / lens)))  # 36mm sensor
    dist = max(dist, 1.0)
    yr, pr = math.radians(yaw), math.radians(pitch)
    loc = c + Vector((math.sin(yr) * math.cos(pr), -math.cos(yr) * math.cos(pr), math.sin(pr))) * dist
    return camera(loc=loc, target=c, lens=lens)


def ground_plane(size=200, color="#d9d4c7"):
    from lib_geo import box, mat
    m = mat("preview_ground", color)
    g = bpy.data.objects.get("PREVIEW_GROUND") or box("PREVIEW_GROUND", (size, size, 0.02), (0, 0, -0.02), m)
    return g


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("render", path)


def isolate(objs_visible):
    """Hide everything in render except the given objects (and helpers)."""
    keep = set()
    for o in objs_visible:
        stack = [o]
        while stack:
            x = stack.pop()
            keep.add(x.name)
            stack.extend(x.children)
    for o in bpy.data.objects:
        if o.type in ("CAMERA",) or o.name in ("SUN", "PREVIEW_GROUND"):
            continue
        o.hide_render = (o.name not in keep) or o.name.endswith("-colonly") or o.type == "EMPTY"
