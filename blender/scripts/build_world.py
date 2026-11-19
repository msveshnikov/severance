"""Task 3: the two levels from office_plan.py.
blender -b --factory-startup -P build_world.py -- [--no-render] [--only severed]
Writes assets/levels/<level>.gltf (FLOOR, WALLS, WALLTOP, HEADERS), assets/levels/<level>_layout.json
(grid, rooms, props, markers, doors, routes, signs), assets/ui/map_<level>.png, renders/levels/*.png.

Wall faces exist only where a solid cell borders a walkable one, each face gets the wall material of the room
it faces, so one wall band shows white on the MDR side and wood on the Wellness side.
"""
import bpy
import bmesh
import sys
import os
import math
import json

sys.path.insert(0, os.path.dirname(__file__))
from lib_geo import *  # noqa
import lib_render as R
import office_plan as PL
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NO_RENDER = "--no-render" in ARGS
ONLY = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
C = PL.CELL
H = PL.WALL_H
DOOR_H = 2.25
WALL_TILE = 2.4


def wall_mat(name):
    return mat("WALL_" + name, "#ffffff", tex=name, tile=WALL_TILE, rough=0.8)


def floor_mat(name):
    tiles = {"hall_floor": 2.0, "tiles_small": 2.0, "tiles_check": 2.0, "marble": 1.5, "testing_floor": 2.0,
             "wood_floor": 2.4, "grass": 4.0, "concrete": 4.0}
    return mat("FLOOR_" + name, "#ffffff", tex=name, tile=tiles.get(name, 2.0), rough=0.9)


def build_level(L):
    reset()
    std_mats()
    coll = collection(L["name"])
    W, Hh, cells = PL.grid(L)
    rooms = {r["id"]: r for r in L["rooms"]}

    def walk(i, j):
        return 0 <= i < W and 0 <= j < Hh and cells[j][i] is not None

    def room_at(i, j):
        v = cells[j][i]
        if v is None:
            return None
        if v.startswith("door:"):
            return "hall" if "hall" in rooms else L["rooms"][0]["id"]
        return v

    def wall_room(i, j):
        """The room whose wall material a face looking into cell (i,j) uses."""
        v = cells[j][i]
        if v.startswith("door:"):
            # door reveals take the material of a neighbouring room cell
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if walk(a, b) and not cells[b][a].startswith("door:"):
                    return cells[b][a]
            return "hall"
        return v

    solid = set()
    for j in range(Hh):
        for i in range(W):
            if cells[j][i] is None:
                for dj in (-1, 0, 1):
                    for di in (-1, 0, 1):
                        if walk(i + di, j + dj):
                            solid.add((i, j))

    # ------------------------------------------------------------------ floors (per room, per rect)
    fm = bmesh.new()
    mats = []

    def mat_index(m):
        if m not in mats:
            mats.append(m)
        return mats.index(m)

    uvl = fm.loops.layers.uv.new("UVMap")

    def quad(bm, pts, mi, uvs):
        vs = [bm.verts.new(p) for p in pts]
        f = bm.faces.new(vs)
        f.material_index = mi
        for lp, uv in zip(f.loops, uvs):
            lp[uvl].uv = uv
        return f

    for r in L["rooms"]:
        m = floor_mat(r["floor"])
        mi = mat_index(m)
        t = MAT_TILE[m.name]
        for (x0, y0, x1, y1) in r["rects"]:
            pts = [(x0, -y1, 0), (x1, -y1, 0), (x1, -y0, 0), (x0, -y0, 0)]
            quad(fm, pts, mi, [(p[0] / t, p[1] / t) for p in pts])
    hall_floor = floor_mat(rooms.get("hall", L["rooms"][0])["floor"])
    for d in L["doors"]:
        x0, y0, x1, y1 = d["rect"]
        mi = mat_index(hall_floor)
        t = MAT_TILE[hall_floor.name]
        pts = [(x0, -y1, 0), (x1, -y1, 0), (x1, -y0, 0), (x0, -y0, 0)]
        quad(fm, pts, mi, [(p[0] / t, p[1] / t) for p in pts])
    me = bpy.data.meshes.new("FLOOR")
    fm.to_mesh(me)
    fm.free()
    for m in mats:
        me.materials.append(m)
    floor = bpy.data.objects.new("FLOOR", me)
    coll.objects.link(floor)

    # ------------------------------------------------------------------ walls: faces between solid and walkable
    wb = bmesh.new()
    wuv = wb.loops.layers.uv.new("UVMap")
    wmats = []

    def wmi(m):
        if m not in wmats:
            wmats.append(m)
        return wmats.index(m)

    # collect edge runs: key (dir, line, material) -> list of cell indices along the run
    runs = {}
    for (i, j) in solid:
        for di, dj, dname in ((0, 1, "S"), (0, -1, "N"), (1, 0, "E"), (-1, 0, "W")):
            a, b = i + di, j + dj
            if not walk(a, b):
                continue
            rid = wall_room(a, b)
            wm = wall_mat(rooms[rid]["wall"])
            if dname in ("S", "N"):
                line = j + (1 if dname == "S" else 0)   # y line in cells
                runs.setdefault((dname, line, wm.name), []).append(i)
            else:
                line = i + (1 if dname == "E" else 0)
                runs.setdefault((dname, line, wm.name), []).append(j)
    for (dname, line, mname), idx in runs.items():
        idx.sort()
        segs = []
        s0 = p = idx[0]
        for k in idx[1:]:
            if k == p + 1:
                p = k
                continue
            segs.append((s0, p + 1))
            s0 = p = k
        segs.append((s0, p + 1))
        mi = wmi(bpy.data.materials[mname])
        for a, b in segs:
            if dname in ("S", "N"):
                y = -line * C
                xa, xb = a * C, b * C
                if dname == "S":   # face looks south (-Y in Blender): verts left->right seen from the south
                    pts = [(xa, y, 0), (xb, y, 0), (xb, y, H), (xa, y, H)]
                    us = [xa, xb, xb, xa]
                else:
                    pts = [(xb, y, 0), (xa, y, 0), (xa, y, H), (xb, y, H)]
                    us = [-xb, -xa, -xa, -xb]
            else:
                x = line * C
                ya, yb = -a * C, -b * C
                if dname == "E":   # face looks east (+X): walk towards +Y so the normal points +X
                    pts = [(x, yb, 0), (x, ya, 0), (x, ya, H), (x, yb, H)]
                    us = [yb, ya, ya, yb]
                else:
                    pts = [(x, ya, 0), (x, yb, 0), (x, yb, H), (x, ya, H)]
                    us = [-ya, -yb, -yb, -ya]
            vs = [wb.verts.new(p) for p in pts]
            f = wb.faces.new(vs)
            f.material_index = mi
            for lp, u, p in zip(f.loops, us, pts):
                lp[wuv].uv = (u / WALL_TILE, p[2] / H)
    me = bpy.data.meshes.new("WALLS")
    wb.to_mesh(me)
    wb.free()
    for m in wmats:
        me.materials.append(m)
    walls = bpy.data.objects.new("WALLS", me)
    coll.objects.link(walls)

    # ------------------------------------------------------------------ wall tops (dark caps) + door headers
    tb = bmesh.new()
    for (i, j) in solid:
        x0, x1 = i * C, (i + 1) * C
        y0, y1 = -(j + 1) * C, -j * C
        vs = [tb.verts.new(p) for p in ((x0, y0, H), (x1, y0, H), (x1, y1, H), (x0, y1, H))]
        tb.faces.new(vs)
    for d in L["doors"]:
        x0, y0, x1, y1 = d["rect"]
        vs = [tb.verts.new(p) for p in ((x0, -y1, H), (x1, -y1, H), (x1, -y0, H), (x0, -y0, H))]
        tb.faces.new(vs)
    bmesh.ops.remove_doubles(tb, verts=tb.verts, dist=0.001)
    me = bpy.data.meshes.new("WALLTOP")
    tb.to_mesh(me)
    tb.free()
    me.materials.append(mat("WALLTOP", "#1d2422", rough=0.9))
    top = bpy.data.objects.new("WALLTOP", me)
    coll.objects.link(top)

    hd = []
    for d in L["doors"]:
        x0, y0, x1, y1 = d["rect"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        w, dd = x1 - x0, y1 - y0
        hm = wall_mat(rooms["hall" if "hall" in rooms else L["rooms"][0]["id"]]["wall"])
        hd.append(box("hdr_" + d["id"], (w, dd, H - DOOR_H), (cx, -cy, DOOR_H), hm))
        # door frame trim on both faces
        trim = mat("door_trim", "#c9cdc6", rough=0.5)
        horiz = w > dd
        for s in (-1, 1):
            if horiz:
                hd.append(box("jamb%s%d" % (d["id"], s), (0.08, dd + 0.06, DOOR_H), (cx + s * (w / 2 - 0.04), -cy, 0), trim))
            else:
                hd.append(box("jamb%s%d" % (d["id"], s), (w + 0.06, 0.08, DOOR_H), (cx, -(cy + s * (dd / 2 - 0.04)), 0), trim))
        hd.append(box("lintel" + d["id"], (w + 0.06 if horiz else w + 0.06, dd + 0.06 if horiz else dd + 0.06, 0.08),
                      (cx, -cy, DOOR_H - 0.08), trim))
    for o in hd:
        apply_xform(o)
        world_uv(o, 2.4)
    headers = join(hd, "HEADERS") if hd else None
    if headers:
        # header faces use wall UVs (v = z / H) so the trim band of the texture lines up
        me = headers.data
        uv = me.uv_layers.active.data
        for p in me.polygons:
            if headers.data.materials[p.material_index].name.startswith("WALL_"):
                for li in p.loop_indices:
                    co = me.vertices[me.loops[li].vertex_index].co
                    uv[li].uv = (uv[li].uv[0], co.z / H)

    root = bpy.data.objects.new(L["name"], None)
    coll.objects.link(root)
    for o in (floor, walls, top, headers):
        if o:
            o.parent = root
    export_gltf(root, os.path.join(ASSETS, "levels", L["name"] + ".gltf"))

    # ------------------------------------------------------------------ layout JSON (+ prop blocking)
    info = json.load(open(os.path.join(ASSETS, "props", "props_info.json")))
    blocked = set()
    for p in L["props"]:
        pi = info.get(p["a"])
        if not pi or not pi.get("block") or pi.get("mounted"):
            continue
        (mnx, mny, _), (mxx, mxy, _) = pi["min"], pi["max"]
        pad = pi.get("pad", 0.0) - 0.05
        mnx -= pad; mny -= pad; mxx += pad; mxy += pad
        th = math.radians(p.get("yaw", 0))
        cs, sn = math.cos(th), math.sin(th)
        # cells whose centre falls inside the rotated footprint (plan coords: rotate by -yaw)
        r = math.hypot(max(abs(mnx), abs(mxx)), max(abs(mny), abs(mxy))) + 0.5
        for j in range(int((p["y"] - r) / C), int((p["y"] + r) / C) + 1):
            for i in range(int((p["x"] - r) / C), int((p["x"] + r) / C) + 1):
                if not walk(i, j):
                    continue
                dx, dy = (i + 0.5) * C - p["x"], (j + 0.5) * C - p["y"]
                # plan -> prop-local (inverse of the Blender CCW yaw seen in plan axes)
                lx = dx * cs - dy * sn
                ly = dx * sn + dy * cs
                if mnx <= lx <= mxx and mny <= ly <= mxy:
                    blocked.add((i, j))
    rows = []
    room_ids = [r["id"] for r in L["rooms"]]
    room_rows = []
    for j in range(Hh):
        row, rr = [], []
        for i in range(W):
            v = cells[j][i]
            if v is None:
                row.append("#" if (i, j) in solid else " ")
                rr.append(" ")
            elif v.startswith("door:"):
                row.append("D")
                rr.append(chr(65 + room_ids.index("hall")) if "hall" in room_ids else "A")
            else:
                row.append("x" if (i, j) in blocked else ".")
                rr.append(chr(65 + room_ids.index(v)))
        rows.append("".join(row))
        room_rows.append("".join(rr))
    doors = []
    for d in L["doors"]:
        x0, y0, x1, y1 = d["rect"]
        doors.append(dict(id=d["id"], x=(x0 + x1) / 2, y=(y0 + y1) / 2, w=max(x1 - x0, y1 - y0),
                          axis="x" if (x1 - x0) > (y1 - y0) else "y", lock=d.get("lock")))
    layout = dict(name=L["name"], cell=C, w=W, h=Hh, wall_h=H, door_h=DOOR_H, grid=rows, room_ids=room_ids,
                  room_rows=room_rows,
                  rooms=[dict(id=r["id"], rects=r["rects"], floor=r["floor"], wall=r["wall"]) for r in L["rooms"]],
                  props=[dict(a=p["a"], x=p["x"], y=p["y"], yaw=p.get("yaw", 0), z=p.get("z", 0.0), id=p.get("id"))
                         for p in L["props"]],
                  markers=L["markers"], doors=doors, routes={k: [list(v) for v in vs] for k, vs in L["routes"].items()},
                  signs=[dict(key=s[0], x=s[1], y=s[2], yaw=s[3]) for s in L["signs"]],
                  map=dict(rect=[0, 0, L["size"][0], L["size"][1]]))
    json.dump(layout, open(os.path.join(ASSETS, "levels", L["name"] + "_layout.json"), "w"), indent=0)
    print("layout", L["name"], W, Hh, "blocked", len(blocked))

    if NO_RENDER:
        return
    # ------------------------------------------------------------------ map (top-down ortho) + iso preview
    sx, sy = L["size"]
    R.setup_render((int(sx * 24), int(sy * 24)))
    R.world("#0b1512", 1.0)
    R.sun(energy=3.2, rot=(0, 0, 0))
    cam = R.camera(loc=(sx / 2, -sy / 2, 40), target=(sx / 2, -sy / 2, 0), ortho=max(sx, sy))
    bpy.context.scene.render.film_transparent = True
    R.render(os.path.join(ASSETS, "ui", "map_%s.png" % L["name"]))
    bpy.context.scene.render.film_transparent = False
    R.setup_render((1280, 720))
    R.sun(energy=3.0, rot=(50, 0, 35))
    c = Vector((sx / 2, -sy / 2, 0))
    R.camera(loc=c + Vector((40, -40, 46)), target=c, ortho=max(sx, sy) * 0.95)
    R.render(os.path.join(RENDERS, "levels", "%s_iso.png" % L["name"]))


def main():
    for name, L in PL.LEVELS.items():
        if ONLY and name not in ONLY:
            continue
        build_level(L)
        print("built", name)
    print("DONE")


if __name__ == "__main__":
    main()
