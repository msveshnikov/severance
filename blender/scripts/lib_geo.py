"""Geometry, materials, UVs and glTF export helpers for Severance: Lumon Office.
Stylised retro-corporate look: bevelled boxes, muted flat colours, numpy-painted tileable textures.
Conventions (decisions.md): 1 unit = 1 m, front faces Blender -Y, pivot = base centre on the ground.
"""
import bpy
import bmesh
import math
import os
import random
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX = os.path.join(ROOT, "assets", "textures")
ASSETS = os.path.join(ROOT, "assets")
RENDERS = os.path.join(ROOT, "renders")
BLEND = os.path.join(ROOT, "blender")

# ---------------------------------------------------------------- palette
PAL = {
    "terracotta": "#d9774f", "cream": "#f3e3c3", "sun": "#f6c945", "mint": "#8fd3b0",
    "sky": "#7ec3e8", "coral": "#ef6a5b", "asphalt": "#4b4f57", "turq": "#22b8b0",
    "pink": "#f2a7a0", "lilac": "#b9a3d8", "peach": "#f6b98a", "olive": "#a9b86a",
    "white": "#f7f3ea", "dark": "#33302e", "wood": "#8a5a37", "darkwood": "#5c3b26",
    "metal": "#5d6670", "steel": "#9aa4ad", "glass": "#3a5a78", "black": "#24252a",
    "green": "#5fae4e", "leaf": "#6cbf4f", "leaf2": "#4fa046", "red": "#d9483b",
    "yellow": "#f2c230", "orange": "#ef8f3a", "blue": "#3f7fc9", "stone": "#d6c3a3",
    "roof": "#c8613f", "roof2": "#9c4b3a", "slate": "#5a6577", "brown": "#7a4b2e",
    "lumon_white": "#e9ece6", "lumon_green": "#5f8c6a", "lumon_dkgreen": "#2f5a3d", "lumon_blue": "#1f3a5f",
    "crt_beige": "#d8d2c0", "crt_dark": "#2d3330", "steel_brushed": "#b8bec2", "brass": "#c9a24a",
}


def hexrgb(h):
    if isinstance(h, (tuple, list)):
        return tuple(h[:3])
    h = PAL.get(h, h).lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    # sRGB -> linear for Blender colour inputs
    return tuple(((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in srgb)


# ---------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    return s


def collection(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c


# ---------------------------------------------------------------- materials
MATS = {}
MAT_TILE = {}  # material name -> metres per texture tile (None = no texture)


def _img(name):
    fn = name if "." in name else name + ".png"
    img = bpy.data.images.get(fn)
    if img is None:
        img = bpy.data.images.load(os.path.join(TEX, fn))
    return img


def mat(name, color="white", rough=0.85, tex=None, tile=2.0, emit=None, emit_strength=1.0,
        metal=0.0, alpha=None):
    """Flat cartoon material. tex multiplies colour (exported as baseColorTexture * factor).
    emit: emission colour (used for windows, signs, lamps; Godot toggles per mood by material name)."""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    # single-sided: hidden bottom faces of stacked boxes must not z-fight with the floor / the box below
    m.use_backface_culling = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    col = hexrgb(color) + (1.0,)
    if tex:
        ti = nt.nodes.new("ShaderNodeTexImage")
        ti.image = _img(tex)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(ti.outputs["Color"], mix.inputs[6])
        mix.inputs[7].default_value = col
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        MAT_TILE[name] = tile
    else:
        bsdf.inputs["Base Color"].default_value = col
        MAT_TILE[name] = None
    if emit:
        bsdf.inputs["Emission Color"].default_value = hexrgb(emit) + (1.0,)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    if alpha is not None:
        bsdf.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    m.diffuse_color = col
    MATS[name] = m
    return m


def std_mats():
    """Shared material set. Names are stable: Godot looks some of them up (EMIT_*, WALL_*)."""
    mat("wood", "#ffffff", tex="wood", tile=1.2)
    mat("wood_light", "#ffffff", tex="wood_light", tile=1.2)
    mat("trim_white", "lumon_white", rough=0.6)
    mat("plastic_white", "#eef0ea", rough=0.45)
    mat("plastic_beige", "crt_beige", rough=0.5)
    mat("divider_green", "#6f9a78", rough=0.8)
    mat("frame_dark", "dark")
    mat("metal", "metal", rough=0.5, metal=0.3)
    mat("steel", "steel_brushed", rough=0.35, metal=0.6)
    mat("brass", "brass", rough=0.35, metal=0.8)
    mat("black", "black", rough=0.6)
    mat("darkwood", "darkwood")
    mat("leaf", "#4f8f4a", rough=0.9)
    mat("leaf2", "#3b7340", rough=0.9)
    mat("fabric_green", "#3f6a4c", rough=0.95)
    mat("fabric_cream", "#d8ccb0", rough=0.95)
    mat("fabric_grey", "#6c7275", rough=0.95)
    mat("leather", "#3b2a22", rough=0.55)
    mat("red_mark", "#b3262b", rough=0.5)
    mat("paper", "#f3efe2", rough=0.9)
    mat("glass", "#a9d6e0", rough=0.05, alpha=0.35)
    # emissive (screens and lamps glow in Godot; names start with EMIT_)
    mat("EMIT_screen", "#0d2a24", emit="#58e0b8", emit_strength=1.2)
    mat("EMIT_screen_blue", "#0d1a2a", emit="#69b4ff", emit_strength=1.2)
    mat("EMIT_lamp", "#fff4d6", rough=0.3, emit="#ffe2a8", emit_strength=2.0)
    mat("EMIT_red", "#5a1010", emit="#ff3030", emit_strength=2.0)
    mat("EMIT_green", "#103a1a", emit="#40ff70", emit_strength=2.0)
    mat("EMIT_cryo", "#1a3a4a", emit="#7fe6ff", emit_strength=1.5)
    mat("EMIT_fire", "#ff8a30", emit="#ff7a20", emit_strength=4.0)


# ---------------------------------------------------------------- mesh primitives
def _obj(name, bm, mat_obj=None, coll=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    if mat_obj is not None:
        if isinstance(mat_obj, str):
            mat_obj = MATS.get(mat_obj) or mat(mat_obj, mat_obj)  # palette name -> flat material
        me.materials.append(mat_obj)
    return ob


def box(name, size, loc=(0, 0, 0), m=None, bevel=0.0, seg=2, coll=None, base=True, rot=None):
    """Axis box. base=True: loc is the centre of the bottom face."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if base:
        bmesh.ops.translate(bm, vec=(0, 0, sz / 2), verts=bm.verts)
    ob = _obj(name, bm, m, coll)
    if bevel > 0:
        bevel_obj(ob, bevel, seg)
    if rot:
        ob.rotation_euler = rot
    ob.location = loc
    return ob


def cyl(name, r, h, loc=(0, 0, 0), m=None, n=16, r2=None, coll=None, bevel=0.0, seg=2, rot=None, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=n, radius1=r,
                          radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
    ob = _obj(name, bm, m, coll)
    if bevel > 0:
        bevel_obj(ob, bevel, seg)
    if rot:
        ob.rotation_euler = rot
    ob.location = loc
    smooth(ob)
    return ob


def sphere(name, r, loc=(0, 0, 0), m=None, scale=(1, 1, 1), seg=16, rings=10, coll=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    ob = _obj(name, bm, m, coll)
    ob.location = loc
    smooth(ob)
    return ob


def torus(name, R, r, loc=(0, 0, 0), m=None, n=20, nr=8, rot=None, coll=None):
    bm = bmesh.new()
    verts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ring = []
        for j in range(nr):
            b = 2 * math.pi * j / nr
            x = (R + r * math.cos(b)) * math.cos(a)
            y = (R + r * math.cos(b)) * math.sin(a)
            z = r * math.sin(b)
            ring.append(bm.verts.new((x, y, z)))
        verts.append(ring)
    for i in range(n):
        for j in range(nr):
            a = verts[i][j]; b = verts[(i + 1) % n][j]
            c = verts[(i + 1) % n][(j + 1) % nr]; d = verts[i][(j + 1) % nr]
            bm.faces.new((a, b, c, d))
    ob = _obj(name, bm, m, coll)
    if rot:
        ob.rotation_euler = rot
    ob.location = loc
    smooth(ob)
    return ob


def prism(name, pts2d, h, loc=(0, 0, 0), m=None, coll=None, bevel=0.0, seg=2, axis="Z", rot=None):
    """Extrude a 2D polygon (counter-clockwise) by h along +Z (or along +Y for axis='Y': profile in XZ)."""
    bm = bmesh.new()
    if axis == "Z":
        vs = [bm.verts.new((x, y, 0)) for x, y in pts2d]
        vec = (0, 0, h)
    else:  # profile in XZ plane, extruded along Y, centred
        vs = [bm.verts.new((x, -h / 2, z)) for x, z in pts2d]
        vec = (0, h, 0)
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=vec, verts=nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = _obj(name, bm, m, coll)
    if bevel > 0:
        bevel_obj(ob, bevel, seg)
    if rot:
        ob.rotation_euler = rot
    ob.location = loc
    return ob


def gable_roof(name, w, d, h, overhang=0.4, thick=0.25, m="roof_tiles", loc=(0, 0, 0), coll=None, ridge_x=True):
    """Gable roof whose ridge runs along X (front/back slopes face -Y/+Y)."""
    W = w + 2 * overhang
    D = d + 2 * overhang
    if ridge_x:
        prof = [(-D / 2, 0), (D / 2, 0), (D / 2, thick), (0, h + thick), (-D / 2, thick)]
        bm = bmesh.new()
        vs = [bm.verts.new((-W / 2, y, z)) for y, z in prof]
        f = bm.faces.new(vs)
        ext = bmesh.ops.extrude_face_region(bm, geom=[f])
        nv = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(W, 0, 0), verts=nv)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = _obj(name, bm, m, coll)
    ob.location = loc
    bevel_obj(ob, 0.06, 2)
    return ob


def hip_roof(name, w, d, h, overhang=0.4, m="roof_tiles", loc=(0, 0, 0), coll=None):
    W = w / 2 + overhang
    D = d / 2 + overhang
    r = max(0.0, W - D) if W > D else 0.0
    bm = bmesh.new()
    a = bm.verts.new((-W, -D, 0)); b = bm.verts.new((W, -D, 0))
    c = bm.verts.new((W, D, 0)); dd = bm.verts.new((-W, D, 0))
    if W >= D:
        t1 = bm.verts.new((-r, 0, h)); t2 = bm.verts.new((r, 0, h))
        bm.faces.new((a, b, t2, t1)); bm.faces.new((c, dd, t1, t2))
        bm.faces.new((b, c, t2)); bm.faces.new((dd, a, t1))
    else:
        r = D - W
        t1 = bm.verts.new((0, -r, h)); t2 = bm.verts.new((0, r, h))
        bm.faces.new((a, b, t1)); bm.faces.new((c, dd, t2))
        bm.faces.new((b, c, t2, t1)); bm.faces.new((dd, a, t1, t2))
    bm.faces.new((dd, c, b, a))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = _obj(name, bm, m, coll)
    ob.location = loc
    bevel_obj(ob, 0.08, 2)
    return ob


def pyramid(name, w, d, h, m="roof_slate", loc=(0, 0, 0), coll=None, tip=0.0):
    bm = bmesh.new()
    a = bm.verts.new((-w / 2, -d / 2, 0)); b = bm.verts.new((w / 2, -d / 2, 0))
    c = bm.verts.new((w / 2, d / 2, 0)); dd = bm.verts.new((-w / 2, d / 2, 0))
    t = bm.verts.new((0, 0, h))
    for f in ((a, b, t), (b, c, t), (c, dd, t), (dd, a, t), (dd, c, b, a)):
        bm.faces.new(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = _obj(name, bm, m, coll)
    ob.location = loc
    return ob


def tube_path(name, pts, r, m=None, n=8, coll=None):
    """Round tube along a polyline (for rails, handlebars, frames)."""
    bm = bmesh.new()
    rings = []
    P = [Vector(p) for p in pts]
    for i, p in enumerate(P):
        if i == 0:
            t = (P[1] - P[0]).normalized()
        elif i == len(P) - 1:
            t = (P[-1] - P[-2]).normalized()
        else:
            t = ((P[i + 1] - P[i]).normalized() + (P[i] - P[i - 1]).normalized()).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(up).normalized()
        v = t.cross(u).normalized()
        ring = []
        for j in range(n):
            a = 2 * math.pi * j / n
            ring.append(bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * r))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(n):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % n], rings[i + 1][(j + 1) % n], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    ob = _obj(name, bm, m, coll)
    smooth(ob)
    return ob


def empty(name, loc=(0, 0, 0), yaw_deg=0.0, coll=None, size=0.3, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = size
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(yaw_deg))
    (coll or bpy.context.scene.collection).objects.link(e)
    if parent:
        e.parent = parent
    return e


def point_light(name, loc, energy_w=60, color="#ffd690", radius=0.15, coll=None):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy_w
    ld.color = hexrgb(color)
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


# ---------------------------------------------------------------- modifiers & helpers
def bevel_obj(ob, width, seg=2):
    mod = ob.modifiers.new("bev", "BEVEL")
    mod.width = width
    mod.segments = seg
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(35)
    mod.harden_normals = False
    apply_mods(ob)
    smooth(ob, angle=40)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    eo = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(eo)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)


def smooth(ob, angle=40):
    me = ob.data
    if not hasattr(me, "polygons"):
        return
    for p in me.polygons:
        p.use_smooth = True
    try:
        # Blender 4.1+: smooth by angle via set_sharpness_by_angle
        me.set_sharpness_by_angle(angle=math.radians(angle))
    except Exception:
        pass


def crooked(ob, shear=0.0, taper=0.0, height=None):
    """Cartoon 'crooked' look: shear X by z, taper width with z."""
    h = height or max(v.co.z for v in ob.data.vertices) or 1
    for v in ob.data.vertices:
        t = v.co.z / h
        v.co.x += shear * t
        v.co.x *= (1 - taper * t)
        v.co.y *= (1 - taper * 0.5 * t)


def join(objs, name):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name
        objs[0].data.name = name
        return objs[0]
    ctx = {"active_object": objs[0], "selected_editable_objects": objs, "selected_objects": objs,
           "object": objs[0]}
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
    o = objs[0]
    o.name = name
    o.data.name = name
    return o


def apply_xform(ob):
    """Bake loc/rot/scale into mesh (keeps world placement, resets object transform)."""
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    if ob.type == "MESH":
        ob.data.transform(mw)
    ob.matrix_world = Matrix.Identity(4)


def world_uv(ob, default_tile=2.0):
    """Box projection in world metres per face, scale from material tile size.
    Run after the object is in its final asset-space position."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    mw = ob.matrix_world
    nm = mw.to_3x3()
    for p in me.polygons:
        mname = me.materials[p.material_index].name if me.materials else None
        tile = MAT_TILE.get(mname) or default_tile
        n = (nm @ p.normal).normalized()
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 2:
                u, v = co.x, co.y
            elif ax == 0:
                u, v = co.y * (1 if n.x > 0 else -1), co.z
            else:
                u, v = co.x * (-1 if n.y > 0 else 1), co.z
            uv[li].uv = (u / tile, v / tile)


def finish_asset(objs, root_name, coll, keep_separate=None):
    """Join plain geometry by material-agnostic union, keep INT_/MARK_/ANIM_/LIGHT_/colonly separate.
    Returns the root empty (asset node)."""
    keep_separate = keep_separate or []
    bpy.context.view_layer.update()
    root = bpy.data.objects.new(root_name, None)
    coll.objects.link(root)
    geo = []
    for o in objs:
        if o is None:
            continue
        n = o.name
        special = n.startswith(("INT_", "MARK_", "ANIM_", "LIGHT_", "ACC_", "HELD_", "WHEEL_", "STEER", "CRANK",
                                "EMIT_", "TLAMP")) or n.endswith("-colonly") or o in keep_separate
        if not special and o.type == "MESH":
            geo.append(o)
    for o in objs:
        if o is None:
            continue
        if o.type == "MESH":
            world_uv(o)
    if geo:
        g = join(geo, root_name + "_mesh")
        g.parent = root
    for o in objs:
        if o is not None and o not in geo and o.parent is None:
            o.parent = root
    return root


def colbox(name, size, loc=(0, 0, 0), coll=None, rot=None):
    """Simplified collision box: exported as <name>-colonly (Godot -> StaticBody3D)."""
    ob = box(name + "-colonly", size, loc, None, coll=coll, rot=rot)
    ob.display_type = "WIRE"
    ob.hide_render = True
    return ob


# ---------------------------------------------------------------- export
def select_tree(root):
    bpy.ops.object.select_all(action="DESELECT")
    stack = [root]
    while stack:
        o = stack.pop()
        o.hide_render = False if not o.name.endswith("-colonly") else o.hide_render
        o.select_set(True)
        stack.extend(o.children)
    bpy.context.view_layer.objects.active = root


def export_gltf(root, path):
    """Export one asset tree as glTF Separate with textures shared in assets/textures."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    loc = root.location.copy()
    root.location = (0, 0, 0)
    select_tree(root)
    # colonly objects must be exported (they are hidden in render only)
    tex_rel = os.path.relpath(TEX, os.path.dirname(path)).replace("\\", "/")
    kw = dict(filepath=path, export_format="GLTF_SEPARATE", use_selection=True, export_apply=True,
              export_texture_dir=tex_rel, export_lights=True, export_extras=True, export_yup=True,
              export_import_convert_lighting_mode="RAW", export_animations=True)
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop("export_import_convert_lighting_mode", None)
        bpy.ops.export_scene.gltf(**kw)
    root.location = loc


def scale_lights_for_export(root, factor=1 / 30):
    stack = [root]
    saved = []
    while stack:
        o = stack.pop()
        if o.type == "LIGHT":
            saved.append((o, o.data.energy))
            o.data.energy *= factor
        stack.extend(o.children)
    return saved


def restore_lights(saved):
    for o, e in saved:
        o.data.energy = e


def rnd(seed):
    return random.Random(seed)
