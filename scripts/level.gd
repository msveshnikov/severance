extends Node3D
class_name Level
## Builds a level at runtime from assets/levels/<name>.gltf + <name>_layout.json: architecture with the cutaway
## wall shader, props, room signs, locked doors, the walk grid (AStarGrid2D, 0.5 m cells) and interactables.

const CUT_SHADER := preload("res://shaders/cutaway.gdshader")
const CRT_SHADER := preload("res://shaders/crt_screen.gdshader")
const CCTV_SHADER := preload("res://shaders/cctv.gdshader")
const DIGITS := preload("res://assets/ui/digits.png")
const Quests := preload("res://scripts/quests.gd")

## props whose height hides the player get the cutaway shader too
const TALL := ["bookshelf", "lockers", "monitor_wall", "server_rack", "vending", "fridge", "filing_cabinet", "plant_tall",
	"coat_rack", "cryo_pod", "desk_pod", "elevator", "red_elevator", "stall_row", "kitchen_counter", "printer3d",
	"shelf_art", "tree_small", "water_cooler", "fireplace", "tent", "door_lock", "sink_counter", "otc_switch"]
## terminal -> the chair the innie sits on while using it
const SEAT_FOR := {"term_mark": "seat_mark", "term_helly": "seat_helly", "term_dylan": "seat_dylan",
	"term_irving": "seat_irving", "seat_break": "seat_break", "seat_wellness": "seat_wellness"}
const DOOR_INT := {"cryo": "cryo_keypad", "otc": "otc_door"}

var lname := ""
var data := {}
var cell := 0.5
var gw := 0
var gh := 0
var grid := []                    # rows of chars
var astar := AStarGrid2D.new()
var interactables := {}           # id -> {id, node, pos, yaw, stand, label, seat, kind}
var markers := []
var doors := {}                   # lock -> {node, cells, open, data}
var props_by_id := {}
var screens := []                 # MeshInstance3D with CRT material (for MDE disco etc.)
var room_ids := []
var room_rows := []
var _scene_cache := {}
var _mat_cache := {}


func build(level_name: String) -> void:
	lname = level_name
	var txt := FileAccess.get_file_as_string("res://assets/levels/%s_layout.json" % level_name)
	data = JSON.parse_string(txt)
	cell = data["cell"]
	gw = int(data["w"])
	gh = int(data["h"])
	grid = []
	for r in data["grid"]:
		grid.append(String(r))
	room_ids = data["room_ids"]
	room_rows = data["room_rows"]
	markers = data["markers"]
	var arch: Node3D = load("res://assets/levels/%s.gltf" % level_name).instantiate()
	add_child(arch)
	_convert_materials(arch, true)
	for p in data["props"]:
		_add_prop(p)
	for s in data["signs"]:
		_add_sign(s)
	for d in data["doors"]:
		if d.get("lock") != null:
			_add_lock(d)
	_build_astar()
	for id in interactables:
		_finish_interactable(interactables[id])


# ------------------------------------------------------------------ coordinates
func plan_to_world(x: float, y: float, h: float = 0.0) -> Vector3:
	return Vector3(x, h, y)


func cell_of(p: Vector3) -> Vector2i:
	return Vector2i(int(floor(p.x / cell)), int(floor(p.z / cell)))


func cell_center(c: Vector2i) -> Vector3:
	return Vector3((c.x + 0.5) * cell, 0.0, (c.y + 0.5) * cell)


func in_grid(c: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < gw and c.y < gh


func walkable(c: Vector2i) -> bool:
	return in_grid(c) and not astar.is_point_solid(c)


func walkable_pos(p: Vector3) -> bool:
	return walkable(cell_of(p))


func room_at(p: Vector3) -> String:
	var c := cell_of(p)
	if not in_grid(c):
		return ""
	var ch: String = room_rows[c.y][c.x]
	if ch == " ":
		return ""
	return room_ids[ch.unicode_at(0) - 65]


func nearest_walkable(p: Vector3, max_r: int = 8) -> Vector3:
	var c := cell_of(p)
	if walkable(c):
		return cell_center(c)
	var best := Vector2i(-1, -1)
	var bd := 1e9
	for r in range(1, max_r + 1):
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				if abs(dx) != r and abs(dy) != r:
					continue
				var q := c + Vector2i(dx, dy)
				if walkable(q):
					var d := cell_center(q).distance_squared_to(p)
					if d < bd:
						bd = d
						best = q
		if best.x >= 0:
			return cell_center(best)
	return p


func find_path(from: Vector3, to: Vector3) -> PackedVector3Array:
	var a := cell_of(nearest_walkable(from))
	var b := cell_of(nearest_walkable(to))
	var ids := astar.get_id_path(a, b, true)
	var pts := PackedVector3Array()
	for c in ids:
		pts.append(cell_center(c))
	# only snap to the exact click when the path really reached the target cell (a locked room gives a
	# partial path that ends at the wall: going on to the click would walk through it)
	if pts.size() > 0 and ids[ids.size() - 1] == b and walkable_pos(to):
		var prev := pts[pts.size() - 2] if pts.size() > 1 else from
		if line_clear(prev, to):
			pts[pts.size() - 1] = Vector3(to.x, 0, to.z)
	return _smooth(from, pts)


func _smooth(from: Vector3, pts: PackedVector3Array) -> PackedVector3Array:
	## string-pulling: skip points while the straight line stays on walkable cells
	if pts.size() < 3:
		return pts
	var out := PackedVector3Array()
	var cur := from
	var i := 0
	while i < pts.size():
		var j := pts.size() - 1
		while j > i and not line_clear(cur, pts[j]):
			j -= 1
		out.append(pts[j])
		cur = pts[j]
		i = j + 1
	return out


func line_clear(a: Vector3, b: Vector3, radius: float = 0.22) -> bool:
	var d := Vector2(b.x - a.x, b.z - a.z)
	var n := int(ceil(d.length() / (cell * 0.35))) + 1
	var side := Vector2(-d.y, d.x).normalized() * radius
	for k in range(n + 1):
		var t := float(k) / n
		var p := Vector2(a.x, a.z) + d * t
		for o in [Vector2.ZERO, side, -side]:
			var q: Vector2 = p + o
			if not walkable(Vector2i(int(floor(q.x / cell)), int(floor(q.y / cell)))):
				return false
	return true


func _build_astar() -> void:
	astar.region = Rect2i(0, 0, gw, gh)
	astar.cell_size = Vector2(1, 1)
	astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	astar.default_compute_heuristic = AStarGrid2D.HEURISTIC_OCTILE
	astar.default_estimate_heuristic = AStarGrid2D.HEURISTIC_OCTILE
	astar.update()
	for j in gh:
		var row: String = grid[j]
		for i in gw:
			var ch := row[i]
			if ch != "." and ch != "D":
				astar.set_point_solid(Vector2i(i, j), true)
	for lock in doors:
		_set_door_solid(lock, not doors[lock]["open"])


func block_cells(cells: Array, solid: bool) -> void:
	for c in cells:
		if in_grid(c):
			var ch: String = grid[c.y][c.x]
			if ch == "." or ch == "D":
				astar.set_point_solid(c, solid)


# ------------------------------------------------------------------ materials
func _convert_materials(root: Node, arch: bool, tall: bool = false) -> void:
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m: MeshInstance3D = mi
		if m.mesh == null:
			continue
		var nm := String(m.name)
		for s in m.mesh.get_surface_count():
			var mat := m.mesh.surface_get_material(s)
			if mat == null:
				continue
			var mname := mat.resource_name
			if mname.begins_with("EMIT_screen_blue") or (nm.begins_with("EMIT_screen_") and nm.length() <= 14):
				var sm := ShaderMaterial.new()
				sm.shader = CCTV_SHADER
				sm.set_shader_parameter("seed", randf() * 10.0)
				m.set_surface_override_material(s, sm)
				screens.append(m)
			elif mname.begins_with("EMIT_screen"):
				var sm := ShaderMaterial.new()
				sm.shader = CRT_SHADER
				sm.set_shader_parameter("digits", DIGITS)
				sm.set_shader_parameter("seed", randf() * 10.0)
				m.set_surface_override_material(s, sm)
				screens.append(m)
			elif mname.begins_with("EMIT_"):
				if mat is BaseMaterial3D:
					var bm := (mat as BaseMaterial3D).duplicate()
					bm.emission_enabled = true
					bm.emission_energy_multiplier = 2.0
					m.set_surface_override_material(s, bm)
			elif (arch and (mname.begins_with("WALL") or nm.begins_with("HEADERS") or nm.begins_with("WALLTOP"))) or \
					(tall and mat is BaseMaterial3D and (mat as BaseMaterial3D).transparency == BaseMaterial3D.TRANSPARENCY_DISABLED):
				m.set_surface_override_material(s, _cut_mat(mat))
			if mat is BaseMaterial3D and (mat as BaseMaterial3D).transparency != BaseMaterial3D.TRANSPARENCY_DISABLED:
				m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if arch and nm.begins_with("FLOOR"):
			m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _cut_mat(mat: Material) -> Material:
	if _mat_cache.has(mat):
		return _mat_cache[mat]
	var sm := ShaderMaterial.new()
	sm.shader = CUT_SHADER
	if mat is BaseMaterial3D:
		var bm := mat as BaseMaterial3D
		sm.set_shader_parameter("albedo", bm.albedo_color)
		if bm.albedo_texture:
			sm.set_shader_parameter("albedo_tex", bm.albedo_texture)
			sm.set_shader_parameter("use_tex", true)
		sm.set_shader_parameter("roughness", bm.roughness)
		sm.set_shader_parameter("metallic", bm.metallic)
		if bm.emission_enabled:
			sm.set_shader_parameter("emission", Vector3(bm.emission.r, bm.emission.g, bm.emission.b) * bm.emission_energy_multiplier)
	if mat.resource_name.begins_with("WALLTOP"):
		sm.set_shader_parameter("stub_h", 0.0)
	_mat_cache[mat] = sm
	return sm


# ------------------------------------------------------------------ props
func prop_scene(a: String) -> PackedScene:
	if not _scene_cache.has(a):
		_scene_cache[a] = load("res://assets/props/%s.gltf" % a)
	return _scene_cache[a]


func _add_prop(p: Dictionary) -> Node3D:
	var a: String = p["a"]
	var ps := prop_scene(a)
	if ps == null:
		push_warning("missing prop " + a)
		return null
	var n: Node3D = ps.instantiate()
	n.position = Vector3(p["x"], p.get("z", 0.0), p["y"])
	n.rotation.y = deg_to_rad(p.get("yaw", 0.0))
	n.set_meta("asset", a)
	add_child(n)
	_convert_materials(n, false, a in TALL)
	var id = p.get("id")
	if id != null and id != "":
		props_by_id[id] = n
		var label: String = Quests.LABELS.get(id, "")
		interactables[id] = {"id": id, "node": n, "pos": n.position, "yaw": n.rotation.y, "label": label,
			"seat": SEAT_FOR.get(id, ""), "kind": "prop", "asset": a}
	return n


func _add_sign(s: Dictionary) -> void:
	var l := Label3D.new()
	l.text = Game.t("sign_" + String(s["key"]))
	l.font = preload("res://assets/fonts/Rubik-Variable.ttf")
	l.font_size = 64
	l.outline_size = 12
	l.pixel_size = 0.0045
	l.modulate = Color(0.92, 0.95, 0.93)
	l.outline_modulate = Color(0.05, 0.12, 0.1, 0.9)
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = false
	l.position = Vector3(s["x"], 3.05, s["y"])
	l.set_meta("sign_key", s["key"])
	add_child(l)


func refresh_signs() -> void:
	for c in get_children():
		if c is Label3D and c.has_meta("sign_key"):
			(c as Label3D).text = Game.t("sign_" + String(c.get_meta("sign_key")))


func _add_lock(d: Dictionary) -> void:
	var lock: String = d["lock"]
	var n: Node3D = prop_scene("door_lock").instantiate()
	n.position = Vector3(d["x"], 0, d["y"])
	n.rotation.y = 0.0 if d["axis"] == "x" else PI / 2
	n.scale = Vector3(float(d["w"]) / 2.0, 1, 1)
	add_child(n)
	_convert_materials(n, false, true)
	var cells := []
	var half := float(d["w"]) / 2.0 + 0.01
	for j in gh:
		for i in gw:
			var cc := cell_center(Vector2i(i, j))
			if grid[j][i] == "D" and abs(cc.x - float(d["x"])) <= (half if d["axis"] == "x" else 0.3) \
					and abs(cc.z - float(d["y"])) <= (0.3 if d["axis"] == "x" else half):
				cells.append(Vector2i(i, j))
	var open: bool = Game.flag("open_" + lock)
	doors[lock] = {"node": n, "cells": cells, "open": open, "data": d}
	if open:
		_slide(n, true, true)
	if DOOR_INT.has(lock):
		var id: String = DOOR_INT[lock]
		interactables[id] = {"id": id, "node": n, "pos": n.position, "label": Quests.LABELS.get(id, "i_keypad"),
			"seat": "", "kind": "door", "lock": lock, "yaw": n.rotation.y}


func _set_door_solid(lock: String, solid: bool) -> void:
	block_cells(doors[lock]["cells"], solid)


func open_door(lock: String, instant: bool = false) -> void:
	if not doors.has(lock):
		Game.set_flag("open_" + lock)
		return
	Game.set_flag("open_" + lock)
	doors[lock]["open"] = true
	_set_door_solid(lock, false)
	_slide(doors[lock]["node"], true, instant)
	if not instant:
		Sfx.play("door", 0.9)


func _slide(n: Node3D, open: bool, instant: bool) -> void:
	for side in ["INT_door_L", "INT_door_R"]:
		var leaf := n.find_child(side, true, false) as Node3D
		if leaf == null:
			continue
		if not leaf.has_meta("x0"):
			leaf.set_meta("x0", leaf.position.x)
		var x0: float = leaf.get_meta("x0")
		var target := x0 + (0.95 if side.ends_with("R") else -0.95) * (1.0 if open else 0.0)
		if instant:
			leaf.position.x = target
		else:
			var tw := create_tween()
			tw.tween_property(leaf, "position:x", target, 0.7).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)


func slide_elevator(id: String, open: bool) -> void:
	var n: Node3D = props_by_id.get(id)
	if n == null:
		return
	for side in ["INT_door_L", "INT_door_R"]:
		var leaf := n.find_child(side, true, false) as Node3D
		if leaf == null:
			continue
		if not leaf.has_meta("x0"):
			leaf.set_meta("x0", leaf.position.x)
		var x0: float = leaf.get_meta("x0")
		var tw := create_tween()
		tw.tween_property(leaf, "position:x", x0 + (0.7 if side.ends_with("R") else -0.7) * (1.0 if open else 0.0), 0.8)


# ------------------------------------------------------------------ interactables
func _finish_interactable(it: Dictionary) -> void:
	## stand point: walk out of the prop along its front until a free cell
	var pos: Vector3 = it["pos"]
	var yaw: float = it["yaw"]
	var front := Vector3(sin(yaw), 0, cos(yaw))
	if it["kind"] == "door":
		# stand on the hall side (the side with the lower room index = hall comes first in rooms)
		var a := pos + front * 0.9
		var b := pos - front * 0.9
		it["stand"] = nearest_walkable(a if room_at(a) == "hall" else b)
		it["look"] = pos
		return
	var seat: String = it.get("seat", "")
	if seat != "" and props_by_id.has(seat):
		var sn: Node3D = props_by_id[seat]
		it["seat_pos"] = sn.position
		it["seat_yaw"] = sn.rotation.y
		var sf := Vector3(sin(sn.rotation.y), 0, cos(sn.rotation.y))
		it["stand"] = _free_along(sn.position, sf, 0.3)
		it["look"] = pos
		return
	it["stand"] = _free_along(pos, front, 0.35)
	it["look"] = pos


func _free_along(pos: Vector3, dir: Vector3, start: float) -> Vector3:
	var d := start
	while d < 3.5:
		var p := pos + dir * d
		if walkable_pos(p):
			return p
		d += 0.15
	return nearest_walkable(pos + dir * 0.8)


func add_pickup(id: String, pos: Vector3, asset: String) -> Node3D:
	var n: Node3D = prop_scene(asset).instantiate()
	n.position = pos + Vector3(0, 0.05, 0)
	n.scale = Vector3.ONE * 1.6
	add_child(n)
	n.set_meta("spin", true)
	interactables[id] = {"id": id, "node": n, "pos": pos, "yaw": 0.0, "label": "i_map", "seat": "", "kind": "pickup",
		"stand": nearest_walkable(pos), "look": pos}
	return n


func remove_interactable(id: String) -> void:
	if interactables.has(id):
		var n: Node3D = interactables[id]["node"]
		if interactables[id]["kind"] == "pickup" and is_instance_valid(n):
			n.queue_free()
		interactables.erase(id)


func marker(kind: String, id: String = "") -> Dictionary:
	for m in markers:
		if m["k"] == kind and (id == "" or m.get("id", "") == id):
			return m
	return {}


func marker_pos(kind: String, id: String = "") -> Vector3:
	var m := marker(kind, id)
	if m.is_empty():
		return Vector3.ZERO
	return Vector3(m["x"], 0, m["y"])


func marker_yaw(kind: String, id: String = "") -> float:
	var m := marker(kind, id)
	return deg_to_rad(m.get("yaw", 0.0)) if not m.is_empty() else 0.0


func _process(delta: float) -> void:
	for c in get_children():
		if c is Node3D and c.has_meta("spin"):
			(c as Node3D).rotation.y += delta * 1.5
			(c as Node3D).position.y = 0.08 + sin(Time.get_ticks_msec() * 0.004) * 0.05
