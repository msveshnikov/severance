extends Node
class_name Story
## Runs the directives: places NPCs for the current directive, reacts to talk/use/pickup, opens minigames and
## dialogues, hands out rewards, and drives the special set pieces (patrols, sleeping Graner, OTC, the MDE party).

const Quests := preload("res://scripts/quests.gd")
const MgSmall := preload("res://scripts/ui/mg_small.gd")
const CONE := preload("res://shaders/cone.gdshader")

var main            # main.gd
var level: Level
var actors := {}
var patrols := {}         # npc id -> {pts, i, cone, alert}
var graner_awake := false
var graner_t := 0.0
var otc_held := {}        # "otc_a"/"otc_b" -> innie id
var mde_on := false
var idle_timers := {}
var _caught_lock := false


func dir() -> Dictionary:
	if Game.directive >= Quests.LIST.size():
		return {}
	return Quests.LIST[Game.directive]


func cur_step() -> Dictionary:
	var d := dir()
	if d.is_empty() or Game.step >= d["steps"].size():
		return {}
	return d["steps"][Game.step]


# ------------------------------------------------------------------ world state per directive
func apply_world() -> void:
	level = main.level
	actors = main.actors
	patrols.clear()
	otc_held.clear()
	mde_on = false
	Game.set_flag("sneaking", false)
	for lock in level.doors:
		if Game.flag("open_" + lock):
			level.open_door(lock, true)
	var d := dir()
	var di := Game.directive
	var st: String = d.get("start", "")
	if st == "open_od" or di > 3:
		level.open_door("od", true)
	if level.lname == "severed":
		_place_severed(di, st)
	else:
		_place_testing(di)
	_spawn_pickups()
	main.refresh_hud()


func _seat(id: String, seat: String, a: String = "sit_type") -> void:
	if not actors.has(id) or not level.props_by_id.has(seat):
		return
	var s: Node3D = level.props_by_id[seat]
	var act: Actor = actors[id]
	act.global_position = level.nearest_walkable(s.position + Vector3(sin(s.rotation.y), 0, cos(s.rotation.y)) * 0.7)
	act.sit(s.position, s.rotation.y, a)


func _stand(id: String, pos: Vector3, yaw: float, a: String = "idle") -> void:
	if not actors.has(id):
		return
	var act: Actor = actors[id]
	act.stand_up()
	act.global_position = pos
	act.rotation.y = yaw
	act.yaw_target = yaw
	act.idle_anim = a
	act.play(a)


func _place_severed(di: int, st: String) -> void:
	# innies: at their desks unless they are the active one
	for id in Game.INNIES:
		if not actors.has(id):
			continue
		if id == "helly" and "helly" not in Game.unlocked:
			var a: Actor = actors["helly"]
			a.global_position = Vector3(16.5, 0.78, 34.25)
			a.rotation.y = 0
			a.yaw_target = 0
			a.idle_anim = "lie"
			a.play("lie")
			a.busy = true
			continue
		if id != Game.active:
			_seat(id, "seat_" + id)
	# managers and staff
	_stand("milchick", level.marker_pos("npc_milchick"), 0.0, "idle")
	if di == 2 and Game.step >= 1:
		_seat("milchick", "seat_break_m", "sit")
	if st == "mde" or di == 16:
		_stand("milchick", Vector3(28.0, 0, 17.6), PI, "idle")
	_seat("cobel", "seat_cobel", "sit_type")
	_stand("burt", level.marker_pos("npc_burt"), PI, "idle")
	_seat("casey", "seat_casey", "sit")
	if st == "graner_sleeps":
		_seat("graner", "seat_graner", "sleep_sit")
		graner_awake = false
		graner_t = 5.0
	else:
		_seat("graner", "seat_graner", "sit_type")
	if st == "stealth":
		_start_patrol("milchick")
		_start_patrol("graner")
		Game.set_flag("sneaking", true)
		if actors.has("helly"):
			(actors["helly"] as Actor).hold_item("book")
		main.hud.toast(Game.t("stealth_on"), UiKit.C_RED)
	if Game.finished:
		level.open_door("waffle", true)


func _place_testing(_di: int) -> void:
	var arrive := level.marker_pos("red_arrive")
	var k := 0
	for id in Game.unlocked:
		if not actors.has(id):
			continue
		if id == Game.active:
			continue
		k += 1
		_stand(id, level.nearest_walkable(arrive + Vector3(0.9 * k, 0, (k % 2) * 1.2 - 0.6)), PI / 2)
	_stand("keeper", level.marker_pos("npc_keeper"), 0.0, "idle")


func _spawn_pickups() -> void:
	if Game.directive == 7 and Game.step == 0 and level.lname == "severed":
		for m in level.markers:
			if m["k"] == "map_piece" and not Game.flag("got_" + m["id"]):
				level.add_pickup(m["id"], Vector3(m["x"], 0, m["y"]), "map_piece")


func _start_patrol(id: String) -> void:
	if not actors.has(id) or not level.data["routes"].has(id):
		return
	var pts := PackedVector3Array()
	for p in level.data["routes"][id]:
		pts.append(Vector3(p[0], 0, p[1]))
	var a: Actor = actors[id]
	a.stand_up()
	a.global_position = pts[0]
	var cone := MeshInstance3D.new()
	cone.mesh = _cone_mesh(6.0, deg_to_rad(70))
	var m := ShaderMaterial.new()
	m.shader = CONE
	cone.material_override = m
	cone.position.y = 0.04
	cone.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	a.add_child(cone)
	patrols[id] = {"pts": pts, "i": 1, "cone": cone, "alert": 0.0}
	a.walk_route(PackedVector3Array([pts[1]]), 1.5)


func _cone_mesh(r: float, ang: float) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 14
	for i in n:
		var a0 := -ang / 2 + ang * i / n
		var a1 := -ang / 2 + ang * (i + 1) / n
		st.set_uv(Vector2(0, 0))
		st.add_vertex(Vector3.ZERO)
		st.set_uv(Vector2(1, 0))
		st.add_vertex(Vector3(sin(a0), 0, cos(a0)) * r)
		st.set_uv(Vector2(1, 0))
		st.add_vertex(Vector3(sin(a1), 0, cos(a1)) * r)
	return st.commit()


func stop_patrols() -> void:
	for id in patrols:
		var p: Dictionary = patrols[id]
		if is_instance_valid(p["cone"]):
			p["cone"].queue_free()
	patrols.clear()


# ------------------------------------------------------------------ queries for main / HUD
func step_text() -> String:
	if Game.finished:
		return Game.t("free_play")
	var d := dir()
	if d.is_empty():
		return ""
	var s := cur_step()
	var key := "d%d_s%d" % [Game.directive, Game.step]
	if s.get("k") == "otc":
		key = "d%d_s%d" % [Game.directive, 1 if otc_held.is_empty() else 2]
	elif s.get("k") == "dance":
		key = "d17_s0"
	elif Game.directive == 17 and Game.step == 1:
		key = "d17_s2"
	var vars := {}
	if s.get("k") == "collect":
		var n := 0
		for i in s["ids"]:
			if Game.flag("got_" + i):
				n += 1
		vars["n"] = n
	return Game.t(key, vars) if Game.has_text(key) else Game.t("d%d_desc" % Game.directive)


func needed_innie() -> String:
	var d := dir()
	if d.is_empty() or Game.finished:
		return ""
	var s := cur_step()
	if s.get("k") == "otc" and otc_held.size() == 1:
		return ""
	return d.get("who", "")


func target_pos() -> Variant:
	## world position of the current objective (or null)
	if Game.finished or main.level == null:
		return null
	var s := cur_step()
	if s.is_empty():
		return null
	match s["k"]:
		"talk":
			if actors.has(s["who"]):
				return (actors[s["who"]] as Actor).global_position
		"use", "level":
			if level.interactables.has(s["id"]):
				return level.interactables[s["id"]]["pos"]
			if s["id"] == "red_elevator" and level.lname == "testing":
				return null
		"collect":
			var best = null
			var bd := 1e9
			for i in s["ids"]:
				if level.interactables.has(i):
					var p: Vector3 = level.interactables[i]["pos"]
					var d := p.distance_to(main.player().global_position)
					if d < bd:
						bd = d
						best = p
			return best
		"otc":
			if otc_held.has("otc_a") and level.interactables.has("otc_b"):
				return level.interactables["otc_b"]["pos"]
			if level.interactables.has("otc_a"):
				return level.interactables["otc_a"]["pos"]
		"dance":
			if actors.has("milchick"):
				return (actors["milchick"] as Actor).global_position
	return null


func available(id: String) -> bool:
	## should this interactable show a prompt right now?
	if not level.interactables.has(id):
		return false
	var it: Dictionary = level.interactables[id]
	if it["kind"] == "pickup":
		return true
	var s := cur_step()
	if not Game.finished and s.get("k") in ["use", "level"] and s.get("id") == id:
		return true
	if s.get("k") == "otc" and id in ["otc_a", "otc_b"]:
		return true
	if Quests.FLAVOUR.has(id):
		return true
	if id == "term_" + Game.active:
		return true
	if id in ["red_elevator", "red_elevator_up"] and Game.flag("open_red"):
		return true
	if id == "waffle_table" and Game.finished:
		return true
	return false


func label_for(id: String) -> String:
	var s := cur_step()
	if s.get("k") == "use" and s.get("id") == id and s.has("label"):
		return Game.t(s["label"])
	var it: Dictionary = level.interactables.get(id, {})
	var lk: String = it.get("label", "")
	return Game.t(lk) if lk != "" else ""


# ------------------------------------------------------------------ actions
func _wrong_innie(who: String) -> bool:
	if who != "" and Game.active != who:
		main.hud.toast(Game.t("need_innie", {"name": Game.char_name(who)}), UiKit.C_GOLD)
		Sfx.play("wrong", 0.5)
		return true
	return false


func on_talk(npc: String) -> void:
	var p: Actor = main.player()
	var s := cur_step()
	if not Game.finished and s.get("k") == "talk" and s.get("who") == npc:
		if _wrong_innie(dir().get("who", "")):
			return
		_face_pair(p, npc)
		var dl: String = s.get("dlg", "")
		if dl != "":
			await main.dialog(dl)
		_complete_step()
		return
	if not Game.finished and s.get("k") == "dance" and npc == "milchick":
		_start_mde()
		return
	_face_pair(p, npc)
	if not actors.has(npc):
		return
	var kind: String = (actors[npc] as Actor).id
	var bark := Game.lines("bark_" + kind)
	if bark.size() > 0:
		var l: Array = bark.pick_random()
		(actors[npc] as Actor).say(l[1], 3.0)
		Sfx.play("blip_lo" if kind in ["milchick", "burt", "graner"] else "blip_hi", 0.5)
		if kind == "goat":
			Sfx.play("bleat", 0.8, randf_range(1.0, 1.4))


func _face_pair(p: Actor, npc: String) -> void:
	if not actors.has(npc):
		return
	var n: Actor = actors[npc]
	p.face(n.global_position)
	if not n.seated and not patrols.has(npc) and npc != "helly":
		n.face(p.global_position)
	if npc == "helly" and "helly" not in Game.unlocked:
		pass


func on_use(id: String) -> void:
	var p: Actor = main.player()
	var it: Dictionary = level.interactables.get(id, {})
	if it.is_empty():
		return
	if it["kind"] == "pickup":
		_pickup(id)
		return
	p.face(it.get("look", it["pos"]))
	var s := cur_step()
	var quest: bool = not Game.finished and (s.get("k") in ["use", "level"]) and s.get("id") == id
	if s.get("k") == "otc" and id in ["otc_a", "otc_b"]:
		_otc(id)
		return
	if quest:
		if _wrong_innie(dir().get("who", "")):
			return
		if id == "keycard" and graner_awake:
			await _caught("d10_caught", Vector3(51.5, 0, 26.5))
			return
		if id == "otc_door":
			if not Game.has("keycard"):
				return
			level.open_door("otc")
			Sfx.play("beep", 0.8)
			_complete_step()
			return
		if s["k"] == "level":
			await ride(s["to"])
			_complete_step()
			return
		if it.get("seat", "") != "" and it.has("seat_pos"):
			p.sit(it["seat_pos"], it["seat_yaw"], "sit_type" if id.begins_with("term_") else "sit")
			await main.get_tree().create_timer(1.1).timeout
		var dl: String = s.get("dlg", "")
		if dl != "":
			await main.dialog(dl, {"code": Game.code, "q": int(Game.quota)})
		if s.has("mg"):
			var ok: bool = await main.minigame(s["mg"], s.get("mg_args", {}))
			if not ok:
				p.stand_up()
				return
			if s["mg"] == "keypad":
				level.open_door("cryo")
		if s.has("give"):
			Game.give(s["give"])
			main.hud.toast(Game.t("item_got", {"item": Game.t("item_" + String(s["give"]))}), UiKit.C_GOLD)
			Sfx.play("pickup", 0.8)
			if s["give"] == "keycard" and level.props_by_id.has("keycard"):
				var c: Node = level.props_by_id["keycard"].find_child("INT_card", true, false)
				if c:
					c.visible = false
		if s.has("take"):
			Game.take(s["take"])
		_complete_step()
		return
	# not a quest target: free actions
	if id.begins_with("term_") and id == "term_" + Game.active:
		if it.has("seat_pos"):
			p.sit(it["seat_pos"], it["seat_yaw"], "sit_type")
			await main.get_tree().create_timer(1.1).timeout
		var file := randi() % Quests.FILES.size()
		await main.minigame("mdr", {"file": file, "free": true})
		return
	if id in ["red_elevator", "red_elevator_up"] and Game.flag("open_red"):
		await ride("testing" if id == "red_elevator" else "severed")
		return
	if id == "waffle_table" and Game.finished:
		await main.dialog("d17_end")
		return
	if Quests.FLAVOUR.has(id):
		await main.dialog(Quests.FLAVOUR[id], {"q": int(Game.quota)})


func _pickup(id: String) -> void:
	Game.set_flag("got_" + id)
	level.remove_interactable(id)
	Sfx.play("pickup", 0.9, 1.1)
	main.hud.toast(Game.t("item_got", {"item": Game.t("item_map")}), UiKit.C_GOLD)
	main.fx_sparkle(main.player().global_position + Vector3(0, 1, 0))
	var s := cur_step()
	if s.get("k") == "collect":
		var all := true
		for i in s["ids"]:
			if not Game.flag("got_" + i):
				all = false
		if all:
			_complete_step()
		else:
			main.refresh_hud()


func _otc(id: String) -> void:
	var p: Actor = main.player()
	if otc_held.has(id):
		return
	if otc_held.is_empty() and id == "otc_a" and Game.active != "dylan":
		_wrong_innie("dylan")
		return
	if otc_held.values().has(Game.active):
		return
	otc_held[id] = Game.active
	var it: Dictionary = level.interactables[id]
	p.global_position = it["stand"]
	p.face(it["pos"])
	p.busy = true
	p.idle_anim = "lever"
	p.play("lever")
	var lever := (it["node"] as Node3D).find_child("INT_lever", true, false) as Node3D
	if lever:
		create_tween().tween_property(lever, "rotation:x", 0.9, 0.4)
	Sfx.play("lever", 0.9)
	if otc_held.size() == 1:
		main.hud.toast(Game.t("otc_hold"), UiKit.C_GOLD)
		main.refresh_hud()
		await main.dialog("d15_dylan")
	else:
		main.flash(Color(1, 0.2, 0.15), 0.8)
		Sfx.play("alarm", 1.0)
		for k in otc_held:
			var a: Actor = actors[otc_held[k]]
			a.busy = false
			a.idle_anim = "idle"
			a.play("idle")
		otc_held.clear()
		_complete_step()


func _caught(dlg: String, back: Vector3) -> void:
	if _caught_lock:
		return
	_caught_lock = true
	Sfx.play("caught", 1.0)
	main.hud.show_banner(Game.t("caught"), "", 1.0)
	main.flash(Color(0.8, 0.1, 0.1), 0.5)
	var p: Actor = main.player()
	p.stop()
	await main.dialog(dlg)
	p.global_position = level.nearest_walkable(back)
	main.snap_camera()
	for id in patrols:
		patrols[id]["alert"] = 0.0
	_caught_lock = false


func ride(to: String) -> void:
	var from := level.lname
	var eid := "red_elevator" if from == "severed" else "red_elevator_up"
	level.slide_elevator(eid, true)
	Sfx.play("ding", 1.0)
	await main.get_tree().create_timer(0.6).timeout
	await main.change_level(to, "red_arrive")


# ------------------------------------------------------------------ progression
func _complete_step() -> void:
	var d := dir()
	Game.step += 1
	if Game.step >= d["steps"].size():
		await _complete_directive()
	else:
		Sfx.play("step_done", 0.8)
		main.refresh_hud()
		Game.save_game()
		apply_step_state()


func apply_step_state() -> void:
	## small world changes between steps of one directive
	var di := Game.directive
	if di == 2 and Game.step == 1:
		var m: Actor = actors.get("milchick")
		if m:
			var seat: Node3D = level.props_by_id.get("seat_break_m")
			if seat:
				m.walk_to(level.nearest_walkable(seat.position + Vector3(0, 0, -0.7)), false)
				await m.arrived
				_seat("milchick", "seat_break_m", "sit")
	main.refresh_hud()


func _complete_directive() -> void:
	var d := dir()
	var di := Game.directive
	stop_patrols()
	Game.set_flag("sneaking", false)
	if actors.has("helly"):
		(actors["helly"] as Actor).drop_item()
	if d.has("unlock"):
		Game.unlock(d["unlock"])
		if d["unlock"] == "helly" and actors.has("helly"):
			var h: Actor = actors["helly"]
			h.busy = false
			h.idle_anim = "idle"
			h.global_position = level.nearest_walkable(Vector3(18.5, 0, 34.5))
			h.play("idle")
	if d.has("take"):
		Game.take(d["take"])
	if d.has("reward"):
		Game.give(d["reward"])
	var q: float = d.get("quota", 0)
	if q > 0:
		var before := Game.quota
		Game.add_quota(q if q < 100 else 100.0 - Game.quota)
		main.hud.toast(Game.t("quota_up", {"n": int(round(Game.quota - before))}), UiKit.C_TEAL)
	Sfx.play("directive", 1.0)
	main.hud.show_banner(Game.t("directive_done"), Game.t("d%d_title" % di), 2.0)
	main.fx_confetti()
	if d.get("done", "") != "":
		await main.get_tree().create_timer(1.2).timeout
		await main.dialog(d["done"], {"code": Game.code})
	if d.has("after"):
		main.hud.toast(Game.t(d["after"]), UiKit.C_GOLD)
	Game.directive += 1
	Game.step = 0
	if Game.directive >= Quests.LIST.size():
		Game.finished = true
		Game.save_game()
		main.refresh_hud()
		main.hud.show_banner(Game.t("done_title"), Game.t("done_desc"), 4.0)
		return
	Game.save_game()
	if d.has("after_level") and level.lname != d["after_level"]:
		await ride(d["after_level"])
	await begin_directive()


func begin_directive() -> void:
	var d := dir()
	if d.is_empty():
		return
	var di := Game.directive
	if di == 0 or Quests.LIST[di - 1]["act"] != d["act"]:
		main.hud.show_banner(Game.t("act%d" % d["act"]), "", 2.4)
		await main.get_tree().create_timer(2.6).timeout
	main.hud.show_banner(Game.t("new_directive"), Game.t("d%d_title" % di), 2.2)
	Sfx.play("chime", 0.8)
	var st: String = d.get("start", "")
	match st:
		"open_od":
			level.open_door("od")
		"open_red":
			Game.set_flag("open_red")
	if st in ["stealth", "graner_sleeps", "map_pieces", "milchick_hall", "mde"] or di == 16:
		apply_world()
	if st == "mde":
		pass
	main.refresh_hud()
	if d.get("who", "") != "" and d["who"] != Game.active and d["who"] in Game.unlocked:
		main.hud.toast(Game.t("switch_to", {"name": Game.char_name(d["who"])}), UiKit.C_GOLD)


# ------------------------------------------------------------------ the MDE party
func _start_mde() -> void:
	if mde_on:
		return
	var s := cur_step()
	var p: Actor = main.player()
	_face_pair(p, "milchick")
	await main.dialog("d17_milchick")
	# everyone to the middle of MDR
	mde_on = true
	var spots := [Vector3(26.3, 0, 16.7), Vector3(29.7, 0, 16.7), Vector3(25.0, 0, 18.2), Vector3(31.0, 0, 18.2)]
	var k := 0
	for id in Game.INNIES:
		if actors.has(id):
			var a: Actor = actors[id]
			a.stand_up()
			a.global_position = spots[k]
			a.rotation.y = PI * 0.0
			a.yaw_target = 0.0
			a.idle_anim = "dance" if k % 2 == 0 else "dance2"
			a.play(a.idle_anim)
			k += 1
	(actors["milchick"] as Actor).idle_anim = "dance2"
	(actors["milchick"] as Actor).play("dance2", 0.2, 0.8)
	main.party(true)
	var ok: bool = await main.minigame("dance", {})
	main.party(false)
	for id in Game.INNIES:
		if actors.has(id):
			var a: Actor = actors[id]
			a.idle_anim = "cheer"
			a.play("cheer")
	await main.get_tree().create_timer(1.0).timeout
	for id in Game.INNIES:
		if actors.has(id):
			(actors[id] as Actor).idle_anim = "idle"
			(actors[id] as Actor).play("idle")
	(actors["milchick"] as Actor).idle_anim = "idle"
	mde_on = false
	if ok:
		await main.dialog("d17_done")
		level.open_door("waffle")
		_complete_step()


# ------------------------------------------------------------------ per-frame: patrols, Graner, idle innies
func _process(delta: float) -> void:
	if main == null or main.level == null:
		return
	var p: Actor = main.player()
	for id in patrols:
		var pt: Dictionary = patrols[id]
		var a: Actor = actors[id]
		if not a.moving() and not _caught_lock and not main.ui_busy():
			pt["i"] = (pt["i"] + 1) % pt["pts"].size()
			a.walk_route(PackedVector3Array([pt["pts"][pt["i"]]]), 1.5)
		# vision
		if p == null or _caught_lock or main.ui_busy():
			continue
		var to := p.global_position - a.global_position
		to.y = 0
		var fwd := Vector3(sin(a.rotation.y), 0, cos(a.rotation.y))
		var seen := false
		if to.length() < 6.0 and to.length() > 0.1 and fwd.angle_to(to) < deg_to_rad(36) \
				and level.line_clear(a.global_position, p.global_position, 0.0):
			seen = true
		if to.length() < 1.1:
			seen = true
		pt["alert"] = clampf(pt["alert"] + (delta * 2.2 if seen else -delta), 0.0, 1.0)
		var cone: MeshInstance3D = pt["cone"]
		(cone.material_override as ShaderMaterial).set_shader_parameter("alert", pt["alert"])
		if seen and pt["alert"] > 0.2 and randf() < delta * 3.0:
			a.say(Game.t("hey"), 0.6, UiKit.C_RED)
		if pt["alert"] >= 1.0:
			_caught("d6_caught" if id == "milchick" else "d6_caught_g", level.marker_pos("npc_milchick") + Vector3(-1.5, 0, 0))
	# Graner's naps
	if dir().get("start", "") == "graner_sleeps" and actors.has("graner") and level.lname == "severed" and not main.ui_busy():
		graner_t -= delta
		var g: Actor = actors["graner"]
		if graner_t <= 0.0:
			graner_awake = not graner_awake
			graner_t = randf_range(1.8, 2.8) if graner_awake else randf_range(4.0, 6.5)
			g.play("sit_type" if graner_awake else "sleep_sit", 0.3)
			g.say(Game.t("hey") if graner_awake else Game.t("zzz"), graner_t * 0.9, UiKit.C_RED if graner_awake else Color.WHITE)
			if graner_awake:
				Sfx.play("snort", 0.7)
		if graner_awake and p and p.global_position.distance_to(g.global_position) < 2.2 and p.moving():
			_caught("d10_caught", Vector3(51.5, 0, 26.5))
	# inactive innies drift back to their desks
	if level.lname == "severed" and not mde_on and otc_held.is_empty():
		for id in Game.unlocked:
			if id == Game.active or not actors.has(id):
				continue
			var a: Actor = actors[id]
			if a.seated or a.busy or a.moving():
				idle_timers[id] = 0.0
				continue
			idle_timers[id] = idle_timers.get(id, 0.0) + delta
			if idle_timers[id] > 25.0:
				idle_timers[id] = 0.0
				var seat: Node3D = level.props_by_id.get("seat_" + id)
				if seat:
					a.walk_to(level.nearest_walkable(seat.position + Vector3(sin(seat.rotation.y), 0, cos(seat.rotation.y)) * 0.7), false)
					a.arrived.connect(func():
						if id != Game.active and not a.busy:
							_seat(id, "seat_" + id), CONNECT_ONE_SHOT)
