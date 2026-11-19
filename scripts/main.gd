extends Node
## Scene root: isometric camera, light/environment, level + actors, input (tap/click to walk and interact,
## WASD, pinch/wheel zoom), UI layers, transitions, effects and the --autotest / --tour modes.

const Quests := preload("res://scripts/quests.gd")
const MgSmall := preload("res://scripts/ui/mg_small.gd")
const Menus := preload("res://scripts/ui/menus.gd")
const POST := preload("res://shaders/post.gdshader")
const GLOW := preload("res://assets/ui/glow.png")

const CAM_YAW := 45.0
const CAM_PITCH := 36.0
const CAM_DIST := 40.0
const STAFF := {"severed": ["milchick", "cobel", "burt", "casey", "graner"], "testing": ["keeper"]}

var world: Node3D
var env: WorldEnvironment
var sun: DirectionalLight3D
var cam_rig: Node3D
var cam: Camera3D
var level: Level
var actors := {}
var story: Story
var hud: Hud
var dlg: DialogBox
var post: ColorRect
var fade: ColorRect
var hover_lbl: Label
var mg_layer: CanvasLayer
var menu_layer: CanvasLayer
var hud_layer: CanvasLayer
var marker: MeshInstance3D
var fill_lights: Array[Light3D] = []
var party_lights: Array[Light3D] = []

var state := "title"
var zoom := 13.0
var zoom_target := 13.0
var cam_look := Vector3(28, 0, 12)
var pending := {}
var menu: Control
var mg_open: Minigame
var _press_pos := Vector2.ZERO
var _press_t := 0.0
var _touches := {}
var _pinch_d := 0.0
var _title_t := 0.0
var _room := ""
var _goat_t := 0.0
var _busy_dialog := false


func _ready() -> void:
	randomize()
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_world()
	_build_ui()
	apply_quality()
	if Game.args.has("tour"):
		await _tour()
		return
	await load_level(Game.level if Game.has_save() else "severed")
	show_title()
	if Game.autotest:
		_autotest()


# ------------------------------------------------------------------ setup
func _build_world() -> void:
	world = Node3D.new()
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	env = WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_CLEAR_COLOR
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.78, 0.84, 0.86)
	e.ambient_light_energy = 0.62
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	e.tonemap_exposure = 1.05
	e.glow_enabled = true
	e.glow_intensity = 0.55
	e.glow_bloom = 0.05
	e.glow_hdr_threshold = 1.1
	env.environment = e
	world.add_child(env)
	sun = DirectionalLight3D.new()
	sun.light_color = Color(1.0, 0.98, 0.95)
	sun.light_energy = 1.15
	sun.shadow_enabled = true
	sun.shadow_opacity = 0.55
	sun.shadow_blur = 1.5
	sun.directional_shadow_max_distance = 60.0
	world.add_child(sun)
	sun.look_at_from_position(Vector3(-8, 20, 14), Vector3.ZERO)
	cam_rig = Node3D.new()
	world.add_child(cam_rig)
	cam = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = zoom
	cam.near = 1.0
	cam.far = 120.0
	cam_rig.add_child(cam)
	_place_cam()
	cam.current = true
	marker = MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.22
	sm.height = 0.5
	sm.radial_segments = 4
	sm.rings = 2
	marker.mesh = sm
	var mm := StandardMaterial3D.new()
	mm.albedo_color = Color(0.45, 0.95, 0.82)
	mm.emission_enabled = true
	mm.emission = Color(0.45, 0.95, 0.82)
	mm.emission_energy_multiplier = 2.5
	mm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	marker.material_override = mm
	marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	marker.visible = false
	world.add_child(marker)


func _place_cam() -> void:
	var y := deg_to_rad(CAM_YAW)
	var p := deg_to_rad(CAM_PITCH)
	var off := Vector3(sin(y) * cos(p), sin(p), cos(y) * cos(p)) * CAM_DIST
	cam.position = off
	cam.look_at(Vector3.ZERO, Vector3.UP)
	RenderingServer.global_shader_parameter_set("cut_dir", off.normalized())


func _build_ui() -> void:
	var pl := CanvasLayer.new()
	pl.layer = 1
	add_child(pl)
	post = ColorRect.new()
	var pm := ShaderMaterial.new()
	pm.shader = POST
	post.material = pm
	post.mouse_filter = Control.MOUSE_FILTER_IGNORE
	UiKit.full(post)
	pl.add_child(post)
	hud_layer = CanvasLayer.new()
	hud_layer.process_mode = Node.PROCESS_MODE_PAUSABLE
	hud_layer.layer = 2
	add_child(hud_layer)
	hud = Hud.new()
	hud_layer.add_child(hud)
	hud.visible = false
	hud.switch_requested.connect(set_active)
	hud.use_pressed.connect(_use_nearest)
	hud.pause_pressed.connect(open_pause)
	hud.archive_pressed.connect(open_archive)
	hud.map_pressed.connect(open_map)
	hover_lbl = UiKit.label("", 18, Color(0.95, 0.98, 0.96), false)
	hover_lbl.add_theme_constant_override("outline_size", 7)
	hover_lbl.add_theme_color_override("font_outline_color", Color(0.03, 0.08, 0.07))
	hud_layer.add_child(hover_lbl)
	dlg = DialogBox.new()
	hud_layer.add_child(dlg)
	mg_layer = CanvasLayer.new()
	mg_layer.layer = 3
	add_child(mg_layer)
	menu_layer = CanvasLayer.new()
	menu_layer.layer = 4
	add_child(menu_layer)
	var fl := CanvasLayer.new()
	fl.layer = 10
	add_child(fl)
	fade = ColorRect.new()
	fade.color = Color(0.02, 0.05, 0.04, 0.0)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	UiKit.full(fade)
	fl.add_child(fade)
	story = Story.new()
	story.process_mode = Node.PROCESS_MODE_PAUSABLE
	story.main = self
	add_child(story)
	Game.lang_changed.connect(_on_lang)
	Game.state_changed.connect(refresh_hud)


func apply_quality() -> void:
	var low := Game.low_quality()
	sun.shadow_enabled = not low
	var e := env.environment
	if RenderingServer.get_current_rendering_method() == "forward_plus":
		e.ssao_enabled = not low
		e.ssao_radius = 1.2
		e.ssao_intensity = 1.6
	for l in fill_lights:
		if is_instance_valid(l):
			l.visible = not low
	get_viewport().msaa_3d = Viewport.MSAA_DISABLED
	get_viewport().screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if not low and RenderingServer.get_current_rendering_method() != "gl_compatibility" else Viewport.SCREEN_SPACE_AA_DISABLED


# ------------------------------------------------------------------ level + actors
func load_level(lname: String) -> void:
	if level:
		level.queue_free()
		for id in actors:
			if is_instance_valid(actors[id]):
				actors[id].queue_free()
		actors.clear()
		for l in fill_lights:
			if is_instance_valid(l):
				l.queue_free()
		fill_lights.clear()
		await get_tree().process_frame
	Game.level = lname
	level = Level.new()
	world.add_child(level)
	level.build(lname)
	_add_fill_lights()
	var e := env.environment
	if lname == "testing":
		e.ambient_light_color = Color(0.7, 0.72, 0.8)
		e.ambient_light_energy = 0.45
		sun.light_energy = 0.75
		sun.light_color = Color(0.85, 0.9, 1.0)
	else:
		e.ambient_light_color = Color(0.78, 0.84, 0.86)
		e.ambient_light_energy = 0.62
		sun.light_energy = 1.15
		sun.light_color = Color(1.0, 0.98, 0.95)
	# innies
	for id in Game.INNIES:
		if lname == "testing" and id not in Game.unlocked:
			continue
		_spawn(id, id)
	for id in STAFF[lname]:
		_spawn(id, id)
	if lname == "severed":
		var k := 0
		for p in level.data["props"]:
			if p["a"] == "pedestal":
				k += 1
				var a := _spawn("kier%d" % k, "kier")
				a.global_position = Vector3(p["x"], 0.46, p["y"])
				a.rotation.y = deg_to_rad(p["yaw"])
				a.play("statue")
				a.set_meta("statue", true)
	else:
		for m in level.markers:
			if m["k"] == "goat":
				var g := _spawn(m["id"], "goat")
				g.global_position = Vector3(m["x"], 0, m["y"])
	# the active innie
	var p := player()
	if p:
		p.set_active(true)
		var start := level.marker_pos("player_start") if (lname == "severed" and Game.directive == 0 and Game.step == 0) else Vector3.ZERO
		if start == Vector3.ZERO:
			var seat: Node3D = level.props_by_id.get("seat_" + Game.active)
			start = level.nearest_walkable(seat.position + Vector3(0, 0, 0.8)) if seat else level.marker_pos("red_arrive")
		p.global_position = level.nearest_walkable(start)
	story.apply_world()
	snap_camera()
	_music_for_level()


func _spawn(key: String, model: String) -> Actor:
	var a := Actor.new()
	world.add_child(a)
	a.setup(model, level)
	a.set_meta("key", key)
	actors[key] = a
	return a


func _add_fill_lights() -> void:
	## soft ceiling light per room (desktop quality only)
	for r in level.data["rooms"]:
		if r["id"] == "hall":
			continue
		for rc in r["rects"]:
			var cx: float = (rc[0] + rc[2]) / 2.0
			var cy: float = (rc[1] + rc[3]) / 2.0
			var w: float = rc[2] - rc[0]
			var h: float = rc[3] - rc[1]
			var l := OmniLight3D.new()
			l.position = Vector3(cx, 2.4, cy)
			l.omni_range = maxf(w, h) * 0.75
			l.light_energy = 0.55
			l.light_color = Color(0.92, 0.97, 1.0) if level.lname == "severed" else Color(1.0, 0.75, 0.7)
			if r["id"] in ["wellness", "waffle", "perpetual"]:
				l.light_color = Color(1.0, 0.86, 0.66)
			if r["id"] in ["goats"]:
				l.light_color = Color(0.9, 1.0, 0.8)
			if r["id"] in ["cryo"]:
				l.light_color = Color(0.6, 0.85, 1.0)
			l.shadow_enabled = false
			world.add_child(l)
			fill_lights.append(l)
	apply_quality()


func player() -> Actor:
	return actors.get(Game.active)


func change_level(to: String, marker_kind: String) -> void:
	await _fade(1.0, 0.45)
	await load_level(to)
	var p := player()
	var arrive := level.marker_pos(marker_kind)
	p.global_position = level.nearest_walkable(arrive)
	p.rotation.y = level.marker_yaw(marker_kind)
	var k := 0
	for id in Game.unlocked:
		if id == Game.active or not actors.has(id):
			continue
		k += 1
		var a: Actor = actors[id]
		if to == "testing" or Game.directive >= 16:
			a.stand_up()
			a.global_position = level.nearest_walkable(arrive + Vector3((k - 2) * 0.9, 0, 1.2 if to == "severed" else (k % 2) * 1.0))
	snap_camera()
	hud.set_floor(Game.t("floor_" + to), "")
	await _fade(0.0, 0.5)
	var eid := "red_elevator" if to == "severed" else "red_elevator_up"
	level.slide_elevator(eid, true)
	Sfx.play("ding", 0.9)
	await get_tree().create_timer(1.0).timeout
	level.slide_elevator(eid, false)


func _fade(a: float, t: float) -> void:
	var tw := create_tween()
	tw.tween_property(fade, "color:a", a, t)
	await tw.finished


func _music_for_level() -> void:
	if state == "title":
		Sfx.music("title")
	elif level.lname == "testing":
		Sfx.music("testing")
	elif Game.flag("sneaking"):
		Sfx.music("tension")
	else:
		Sfx.music("office")
	Sfx.ambience("drone" if level.lname == "testing" else "hum")


# ------------------------------------------------------------------ flow
func show_title() -> void:
	state = "title"
	hud.visible = false
	_close_menu_node()
	menu = Menus.title(self)
	menu_layer.add_child(menu)
	_music_for_level()


func start_game(new: bool) -> void:
	_close_menu_node()
	if new:
		Game.new_game()
		await _fade(1.0, 0.4)
		await load_level("severed")
	elif Game.level != level.lname:
		await _fade(1.0, 0.4)
		await load_level(Game.level)
	else:
		await _fade(1.0, 0.3)
		story.apply_world()
	state = "play"
	hud.visible = true
	refresh_hud()
	snap_camera()
	_music_for_level()
	await _fade(0.0, 0.5)
	hud.set_hint(Game.t("tut_move") if Game.is_mobile else Game.t("tut_move_pc"))
	get_tree().create_timer(9.0).timeout.connect(func(): hud.set_hint(""))
	if Game.finished:
		hud.show_banner(Game.t("done_title"), Game.t("free_play"), 3.0)
	elif Game.step == 0:
		await story.begin_directive()
	else:
		refresh_hud()


func to_title() -> void:
	Game.save_game()
	get_tree().paused = false
	show_title()


func confirm(text: String, yes: Callable) -> void:
	var root := Control.new()
	UiKit.full(root)
	var bg := ColorRect.new()
	bg.color = Color(0, 0, 0, 0.6)
	UiKit.full(bg)
	root.add_child(bg)
	var p := UiKit.panel()
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 16)
	var l := UiKit.label(text, 22, UiKit.C_INK, false, HORIZONTAL_ALIGNMENT_CENTER)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(380, 0)
	v.add_child(l)
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_theme_constant_override("separation", 16)
	var by := UiKit.button(Game.t("yes"), 22)
	by.pressed.connect(func():
		root.queue_free()
		yes.call())
	var bn := UiKit.button(Game.t("no"), 22, false)
	bn.pressed.connect(func(): root.queue_free())
	h.add_child(by)
	h.add_child(bn)
	v.add_child(h)
	p.add_child(v)
	root.add_child(p)
	menu_layer.add_child(root)
	(func(): UiKit.place(p, Control.PRESET_CENTER, Vector2.ZERO, Vector2(460, 0))).call_deferred()


func _close_menu_node() -> void:
	if menu and is_instance_valid(menu):
		menu.queue_free()
	menu = null


func close_menu() -> void:
	_close_menu_node()
	if state == "title":
		show_title()
		return
	get_tree().paused = false


func _open(m: Control) -> void:
	_close_menu_node()
	menu = m
	menu.process_mode = Node.PROCESS_MODE_ALWAYS
	menu_layer.add_child(menu)
	if state == "play":
		get_tree().paused = true


func open_pause() -> void:
	if state != "play":
		return
	_open(Menus.pause(self))


func open_settings() -> void:
	_open(Menus.settings(self))


func open_archive() -> void:
	if state != "play":
		return
	_open(Menus.archive(self))


func open_map() -> void:
	if state != "play":
		return
	var tp = story.target_pos()
	_open(Menus.map(self, level, actors, tp if tp != null else Vector3(-1, 0, -1)))


func _on_lang() -> void:
	if level:
		level.refresh_signs()
	refresh_hud()
	if state == "title":
		show_title()


func ui_busy() -> bool:
	return dlg.active or mg_open != null or menu != null or state != "play"


# ------------------------------------------------------------------ services for Story
func dialog(key: String, vars: Dictionary = {}) -> void:
	var l := Game.lines(key)
	if l.is_empty():
		return
	_busy_dialog = true
	var p := player()
	if p:
		p.stop()
	dlg.play(l, vars)
	await dlg.finished
	_busy_dialog = false


func minigame(kind: String, args: Dictionary) -> bool:
	var p := player()
	if p:
		p.stop()
		p.busy = true
	var mg := MgSmall.make(kind, args)
	mg_open = mg
	mg_layer.add_child(mg)
	hud.set_use("")
	var ok: bool = await mg.done
	mg_open = null
	if p:
		p.busy = false
	if kind != "dance":
		_music_for_level()
	return ok


func refresh_hud() -> void:
	if hud == null or level == null:
		return
	var di := Game.directive
	if Game.finished:
		hud.set_directive(Game.t("done_title").to_upper(), Game.t("done_title"), Game.t("free_play"))
	elif di < Quests.LIST.size():
		var d: Dictionary = Quests.LIST[di]
		var head := "%s %02d/%02d  ·  %s" % [Game.t("directive"), di + 1, Quests.LIST.size(), Game.t("act%d" % d["act"]).split(" · ")[0]]
		if d["who"] != "":
			head += "  ·  " + Game.char_name(d["who"]).to_upper()
		hud.set_directive(head, Game.t("d%d_title" % di), story.step_text())
	hud.set_quota(Game.quota)
	hud.set_team(Game.unlocked, Game.active)
	hud.need_innie = story.needed_innie() if story.needed_innie() != Game.active else ""
	hud.set_floor(Game.t("floor_" + level.lname), Game.t("room_" + _room) if _room != "" else "")


func snap_camera() -> void:
	var p := player()
	if p:
		cam_look = p.global_position
		cam_rig.position = cam_look


func flash(col: Color, dur: float) -> void:
	var m := post.material as ShaderMaterial
	m.set_shader_parameter("flash", Color(col.r, col.g, col.b, 0.55))
	var tw := create_tween()
	tw.tween_method(func(a): m.set_shader_parameter("flash", Color(col.r, col.g, col.b, a)), 0.55, 0.0, dur)


func fx_sparkle(pos: Vector3) -> void:
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.amount = 24
	p.lifetime = 0.9
	p.explosiveness = 0.9
	p.direction = Vector3.UP
	p.spread = 70
	p.initial_velocity_min = 1.5
	p.initial_velocity_max = 3.0
	p.gravity = Vector3(0, -3, 0)
	p.scale_amount_min = 0.06
	p.scale_amount_max = 0.14
	var qm := QuadMesh.new()
	qm.size = Vector2(1, 1)
	var m := StandardMaterial3D.new()
	m.albedo_texture = GLOW
	m.albedo_color = Color(0.6, 1.0, 0.9)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	qm.material = m
	p.mesh = qm
	p.position = pos
	world.add_child(p)
	p.emitting = true
	get_tree().create_timer(1.5).timeout.connect(p.queue_free)


func fx_confetti() -> void:
	var c := CPUParticles2D.new()
	c.one_shot = true
	c.amount = 90
	c.lifetime = 2.6
	c.explosiveness = 0.85
	c.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	c.emission_rect_extents = Vector2(hud.size.x / 2, 10)
	c.position = Vector2(hud.size.x / 2, -10)
	c.direction = Vector2(0, 1)
	c.spread = 30
	c.initial_velocity_min = 120
	c.initial_velocity_max = 320
	c.gravity = Vector2(0, 280)
	c.angular_velocity_min = -300
	c.angular_velocity_max = 300
	c.scale_amount_min = 4
	c.scale_amount_max = 8
	var g := Gradient.new()
	g.set_color(0, Color(0.45, 0.95, 0.82))
	g.add_point(0.33, Color(0.98, 0.85, 0.35))
	g.add_point(0.66, Color(0.98, 0.42, 0.38))
	g.set_color(1, Color(0.45, 0.62, 0.95))
	c.color_initial_ramp = g
	hud.add_child(c)
	c.emitting = true
	get_tree().create_timer(3.5).timeout.connect(c.queue_free)


func party(on: bool) -> void:
	for l in party_lights:
		if is_instance_valid(l):
			l.queue_free()
	party_lights.clear()
	if on:
		var cols := [Color(1, 0.3, 0.3), Color(0.3, 1, 0.5), Color(0.4, 0.6, 1), Color(1, 0.85, 0.3)]
		for i in 4:
			var l := OmniLight3D.new()
			l.light_color = cols[i]
			l.light_energy = 2.2
			l.omni_range = 6.0
			l.position = Vector3(28, 2.2, 15)
			l.set_meta("ph", i * PI / 2)
			world.add_child(l)
			party_lights.append(l)
		env.environment.ambient_light_energy = 0.35
	else:
		env.environment.ambient_light_energy = 0.62
		_music_for_level()


# ------------------------------------------------------------------ input
func set_active(id: String) -> void:
	if id == Game.active or not actors.has(id) or id not in Game.unlocked or ui_busy():
		return
	var old := player()
	if old:
		old.set_active(false)
		old.stop()
	Game.active = id
	var p := player()
	p.set_active(true)
	pending = {}
	Sfx.play("switch", 0.8)
	hud.toast(Game.t("switched", {"name": Game.char_name(id)}))
	refresh_hud()
	Game.save_game()


func _cycle_innie() -> void:
	var u := Game.unlocked
	var i := u.find(Game.active)
	set_active(u[(i + 1) % u.size()])


func _unhandled_input(e: InputEvent) -> void:
	if state != "play" or ui_busy() or get_tree().paused:
		return
	if e is InputEventScreenTouch:
		if e.pressed:
			_touches[e.index] = e.position
		else:
			_touches.erase(e.index)
		if _touches.size() < 2:
			_pinch_d = 0.0
	elif e is InputEventScreenDrag:
		_touches[e.index] = e.position
		if _touches.size() >= 2:
			var ks := _touches.keys()
			var d: float = (_touches[ks[0]] as Vector2).distance_to(_touches[ks[1]])
			if _pinch_d > 0.0:
				zoom_target = clampf(zoom_target * _pinch_d / maxf(d, 1.0), 7.0, 22.0)
			_pinch_d = d
	elif e is InputEventMouseButton:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP and e.pressed:
			zoom_target = clampf(zoom_target * 0.9, 7.0, 22.0)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN and e.pressed:
			zoom_target = clampf(zoom_target * 1.1, 7.0, 22.0)
		elif e.button_index == MOUSE_BUTTON_LEFT:
			if e.pressed:
				_press_pos = e.position
				_press_t = Time.get_ticks_msec() / 1000.0
			elif _touches.size() < 2 and e.position.distance_to(_press_pos) < 18.0:
				_tap(e.position)
	elif e is InputEventMouseMotion:
		_hover(e.position)
	elif e is InputEventKey and e.pressed and not e.echo:
		match e.keycode:
			KEY_E, KEY_SPACE, KEY_ENTER:
				_use_nearest()
			KEY_TAB:
				_cycle_innie()
			KEY_1, KEY_2, KEY_3, KEY_4:
				var i: int = e.keycode - KEY_1
				if i < Game.unlocked.size():
					set_active(Game.unlocked[i])
			KEY_ESCAPE, KEY_P:
				open_pause()
			KEY_M:
				open_map()
			KEY_J:
				open_archive()


func _input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and e.keycode == KEY_ESCAPE and menu != null and state == "play":
		close_menu()
		get_viewport().set_input_as_handled()


func _pick(sp: Vector2) -> Dictionary:
	var best := {}
	var bd := 46.0
	for key in actors:
		var a: Actor = actors[key]
		if key == Game.active or a.has_meta("statue"):
			continue
		var f := cam.unproject_position(a.global_position + Vector3(0, 0.2, 0))
		var h := cam.unproject_position(a.global_position + Vector3(0, 1.6 if a.id != "goat" else 0.5, 0))
		var d := Geometry2D.get_closest_point_to_segment(sp, f, h).distance_to(sp)
		if d < bd:
			bd = d
			best = {"kind": "actor", "id": key}
	if best.is_empty():
		bd = 52.0
		for id in level.interactables:
			if not story.available(id):
				continue
			var it: Dictionary = level.interactables[id]
			var c := cam.unproject_position(it["pos"] + Vector3(0, 0.6, 0))
			var d := c.distance_to(sp)
			if d < bd:
				bd = d
				best = {"kind": "use", "id": id}
	return best


func _floor_point(sp: Vector2) -> Variant:
	var o := cam.project_ray_origin(sp)
	var n := cam.project_ray_normal(sp)
	if absf(n.y) < 1e-4:
		return null
	var t := -o.y / n.y
	return o + n * t


func _tap(sp: Vector2) -> void:
	var p := player()
	if p == null or p.busy:
		if p and p.busy and story.otc_held.values().has(Game.active):
			return
		if p == null or p.busy:
			return
	var hit := _pick(sp)
	if hit.get("kind") == "actor":
		var key: String = hit["id"]
		if key in Game.unlocked and key != Game.active:
			set_active(key)
			return
		_go_talk(key)
		return
	if hit.get("kind") == "use":
		_go_use(hit["id"])
		return
	var fp = _floor_point(sp)
	if fp != null:
		pending = {}
		p.walk_to(fp)
		_tap_ring(level.nearest_walkable(fp))


func _tap_ring(pos: Vector3) -> void:
	var r := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.2
	tm.outer_radius = 0.26
	r.mesh = tm
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.45, 0.95, 0.82, 0.9)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	r.material_override = m
	r.position = pos + Vector3(0, 0.03, 0)
	r.scale = Vector3(1, 0.05, 1)
	world.add_child(r)
	var tw := create_tween()
	tw.tween_property(r, "scale", Vector3(2.2, 0.05, 2.2), 0.4)
	tw.parallel().tween_property(m, "albedo_color:a", 0.0, 0.4)
	tw.tween_callback(r.queue_free)


func _go_talk(key: String) -> void:
	var p := player()
	var a: Actor = actors[key]
	var dirv := p.global_position - a.global_position
	dirv.y = 0
	var goal := level.nearest_walkable(a.global_position + dirv.normalized() * 1.0)
	pending = {"kind": "talk", "id": key, "goal": goal}
	if p.global_position.distance_to(a.global_position) < 1.6:
		p.stop()
	else:
		p.walk_to(goal)


func _go_use(id: String) -> void:
	var p := player()
	var it: Dictionary = level.interactables[id]
	var goal: Vector3 = it["stand"]
	pending = {"kind": "use", "id": id, "goal": goal}
	if p.global_position.distance_to(goal) < 0.45 or (p.seated and id.begins_with("term_")):
		p.stop()
	else:
		p.walk_to(goal)


func _nearest_action() -> Dictionary:
	var p := player()
	if p == null:
		return {}
	var best := {}
	var bd := 1.9
	for id in level.interactables:
		if not story.available(id):
			continue
		var it: Dictionary = level.interactables[id]
		var d := minf(p.global_position.distance_to(it["stand"]), Vector2(p.global_position.x - it["pos"].x, p.global_position.z - it["pos"].z).length() - 0.4)
		if d < bd:
			bd = d
			best = {"kind": "use", "id": id}
	for key in actors:
		if key == Game.active or (actors[key] as Actor).has_meta("statue"):
			continue
		var d := p.global_position.distance_to((actors[key] as Actor).global_position)
		if d < minf(bd, 1.8):
			bd = d
			best = {"kind": "actor", "id": key}
	return best


func _use_nearest() -> void:
	if ui_busy():
		return
	var n := _nearest_action()
	if n.is_empty():
		return
	if n["kind"] == "use":
		_go_use(n["id"])
	else:
		var key: String = n["id"]
		if key in Game.unlocked:
			set_active(key)
		else:
			_go_talk(key)


func _hover(sp: Vector2) -> void:
	if Game.is_mobile:
		return
	var h := _pick(sp)
	var txt := ""
	if h.get("kind") == "use":
		txt = story.label_for(h["id"])
	elif h.get("kind") == "actor":
		var key: String = h["id"]
		txt = Game.char_name((actors[key] as Actor).id)
		if key in Game.unlocked:
			txt += "  ⇄" if false else ""
	hover_lbl.text = txt
	hover_lbl.position = sp + Vector2(18, 10)
	hover_lbl.visible = txt != ""
	Input.set_default_cursor_shape(Input.CURSOR_POINTING_HAND if txt != "" else Input.CURSOR_ARROW)


# ------------------------------------------------------------------ per frame
func _process(delta: float) -> void:
	if level == null or get_tree().paused:
		return
	var p := player()
	if state == "title":
		_title_t += delta
		var c := Vector3(28, 0, 12.5) if level.lname == "severed" else Vector3(20, 0, 10)
		cam_rig.position = c + Vector3(sin(_title_t * 0.12) * 5.0, 0, cos(_title_t * 0.1) * 3.0)
		cam.size = lerpf(cam.size, 15.0, delta)
		RenderingServer.global_shader_parameter_set("cut_center", cam_rig.position + Vector3(0, 0.9, 0))
		RenderingServer.global_shader_parameter_set("cut_radius", 7.0)
		return
	if p == null:
		return
	# WASD / arrows
	var mv := Vector2.ZERO
	if not ui_busy() and not p.busy:
		if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
			mv.y -= 1
		if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
			mv.y += 1
		if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
			mv.x -= 1
		if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
			mv.x += 1
	if mv != Vector2.ZERO:
		pending = {}
		var yaw := deg_to_rad(CAM_YAW)
		var fwd := -Vector3(sin(yaw), 0, cos(yaw))
		var right := Vector3(cos(yaw), 0, -sin(yaw))
		var dirv := (right * mv.x - fwd * mv.y).normalized()
		p.push(dirv, delta)
	elif not p.moving() and not p.seated and not p.busy and p.anim and p._cur_anim in ["run", "walk", "sneak"]:
		p.play(p.idle_anim)
	# pending walk-and-act
	if not pending.is_empty() and not p.moving() and not ui_busy():
		var goal: Vector3 = pending["goal"]
		var pd := pending
		pending = {}
		if p.global_position.distance_to(goal) < 0.9 or pd["kind"] == "talk" and actors.has(pd["id"]) \
				and p.global_position.distance_to((actors[pd["id"]] as Actor).global_position) < 2.2:
			if pd["kind"] == "use":
				story.on_use(pd["id"])
			else:
				story.on_talk(pd["id"])
	# camera follow + zoom + cutaway
	cam_look = cam_look.lerp(p.global_position, 1.0 - exp(-delta * 5.0))
	cam_rig.position = cam_look
	zoom = lerpf(zoom, zoom_target, 1.0 - exp(-delta * 6.0))
	cam.size = zoom
	RenderingServer.global_shader_parameter_set("cut_center", p.global_position + Vector3(0, 0.9, 0))
	RenderingServer.global_shader_parameter_set("cut_radius", 2.2 + zoom * 0.07)
	# room badge
	var r := level.room_at(p.global_position)
	if r != "" and r != _room:
		_room = r
		hud.set_floor(Game.t("floor_" + level.lname), Game.t("room_" + r))
	# USE button + objective marker
	if not ui_busy():
		var n := _nearest_action()
		if n.is_empty():
			hud.set_use("")
		elif n["kind"] == "use":
			hud.set_use(story.label_for(n["id"]))
		else:
			var key: String = n["id"]
			hud.set_use(Game.t("i_talk") + ": " + Game.char_name((actors[key] as Actor).id) if key not in Game.unlocked else Game.char_name(key))
	else:
		hud.set_use("")
	var tp = story.target_pos()
	if tp != null and state == "play":
		marker.visible = true
		marker.position = tp + Vector3(0, 2.6 + sin(Time.get_ticks_msec() * 0.004) * 0.15, 0)
		marker.rotation.y += delta * 2.0
		var sp := cam.unproject_position(marker.position)
		var vr := get_viewport().get_visible_rect().size
		var off := sp.x < 0 or sp.y < 0 or sp.x > vr.x or sp.y > vr.y
		hud.arrow_on = off
		hud.arrow_target = sp
	else:
		marker.visible = false
		hud.arrow_on = false
	# party lights
	for l in party_lights:
		if is_instance_valid(l):
			var ph: float = l.get_meta("ph") + Time.get_ticks_msec() * 0.002
			l.position = Vector3(28 + cos(ph) * 3.5, 2.3, 15.5 + sin(ph) * 2.5)
	# goats wander
	if level.lname == "testing":
		_goat_t -= delta
		if _goat_t <= 0.0:
			_goat_t = 1.5
			var pen := level.marker("pen")
			for key in actors:
				if (actors[key] as Actor).id == "goat" and randf() < 0.35:
					var g: Actor = actors[key]
					var tgt := Vector3(pen["x"] + randf_range(-pen["w"] / 2 + 0.8, pen["w"] / 2 - 0.8), 0,
						pen["y"] + randf_range(-pen["h"] / 2 + 0.8, pen["h"] / 2 - 0.8))
					g.walk_route(PackedVector3Array([tgt]), 0.8)
					g.idle_anim = ["idle", "eat", "idle"].pick_random()


# ------------------------------------------------------------------ autotest / tour
func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://renders/game"))
	img.save_png("res://renders/game/%s.png" % name)
	_log("shot " + name)


func _log(s: String) -> void:
	print("AUTOTEST ", s)
	var f := FileAccess.open("res://renders/autotest.log", FileAccess.READ_WRITE if FileAccess.file_exists("res://renders/autotest.log") else FileAccess.WRITE)
	if f:
		f.seek_end()
		f.store_line(s)


func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout


func _wait_idle(timeout: float = 30.0) -> void:
	var t := 0.0
	while (dlg.active or mg_open != null) and t < timeout:
		await get_tree().process_frame
		t += get_process_delta_time()


func _autotest() -> void:
	var fails := 0
	if FileAccess.file_exists("res://renders/autotest.log"):
		DirAccess.remove_absolute(ProjectSettings.globalize_path("res://renders/autotest.log"))
	_log("start")
	await _wait(1.5)
	await _shot("00_title")
	Game.new_game()
	await start_game(true)
	await _wait(3.0)
	await _shot("01_start")
	# walk test: Mark walks to the MDR door
	var p := player()
	p.walk_to(Vector3(28, 0, 21.5))
	var t := 0.0
	while p.moving() and t < 20.0:
		await get_tree().process_frame
		t += get_process_delta_time()
	_log("walk arrived=%s pos=%s" % [str(p.global_position.distance_to(Vector3(28, 0, 21.5)) < 1.0), str(p.global_position)])
	if p.global_position.distance_to(Vector3(28, 0, 21.5)) > 1.0:
		fails += 1
	await _shot("02_hall")
	if Game.args.has("from"):
		var fr := int(Game.args["from"])
		Game.directive = fr
		Game.step = 0
		Game.quota = [0, 0, 10, 15, 20, 30, 32, 38, 44, 50, 55, 60, 65, 67, 73, 78, 84, 100][fr]
		Game.unlocked = ["mark", "dylan", "irving", "helly"]
		if fr >= 6:
			Game.give("book")
		if fr >= 11:
			Game.give("keycard")
		if fr >= 12:
			Game.set_flag("open_red")
		Game.set_flag("open_od")
		if fr >= 13 and fr <= 15:
			await change_level("testing", "red_arrive")
		else:
			story.apply_world()
		await story.begin_directive()
	var only_upto := int(Game.args.get("upto", 99))
	while not Game.finished and Game.directive < only_upto:
		var di := Game.directive
		var d: Dictionary = Quests.LIST[di]
		if d["who"] != "" and d["who"] in Game.unlocked:
			set_active(d["who"])
		await _wait(0.3)
		var guard := 0
		while Game.directive == di and guard < 8 and not Game.finished:
			guard += 1
			var s := story.cur_step()
			_log("directive %d step %d %s" % [di, Game.step, str(s)])
			var pl := player()
			match s.get("k"):
				"talk":
					var a: Actor = actors.get(s["who"])
					if a:
						pl.global_position = level.nearest_walkable(a.global_position + Vector3(0.9, 0, 0.9))
						snap_camera()
					await _wait(0.4)
					if guard == 1:
						await _shot("d%02d_a" % di)
					story.on_talk(s["who"])
				"use", "level":
					var it: Dictionary = level.interactables.get(s["id"], {})
					if it.is_empty():
						_log("FAIL missing interactable " + s["id"])
						fails += 1
						break
					pl.walk_to(it["stand"])
					var tt := 0.0
					while pl.moving() and tt < 25.0:
						await get_tree().process_frame
						tt += get_process_delta_time()
					if pl.global_position.distance_to(it["stand"]) > 1.0:
						_log("WARN walk to %s failed, teleporting" % s["id"])
						pl.global_position = it["stand"]
					snap_camera()
					if guard == 1:
						await _shot("d%02d_a" % di)
					story.on_use(s["id"])
					await _wait(1.2)
					if mg_open:
						await _shot("d%02d_mg" % di)
				"collect":
					for i in s["ids"]:
						if level.interactables.has(i):
							pl.global_position = level.interactables[i]["stand"]
							snap_camera()
							await _wait(0.2)
							story.on_use(i)
					await _shot("d%02d_a" % di)
				"otc":
					set_active("dylan")
					await _wait(0.2)
					player().global_position = level.interactables["otc_a"]["stand"]
					story.on_use("otc_a")
					await _wait_idle()
					var other := "mark" if "mark" in Game.unlocked else "irving"
					set_active(other)
					player().global_position = level.interactables["otc_b"]["stand"]
					snap_camera()
					await _wait(0.5)
					await _shot("d%02d_a" % di)
					story.on_use("otc_b")
				"dance":
					var m: Actor = actors["milchick"]
					pl.global_position = level.nearest_walkable(m.global_position + Vector3(0, 0, -1.0))
					story.on_talk("milchick")
					await _wait(3.5)
					await _shot("d%02d_dance" % di)
			var st0 := Game.step
			var tw0 := 0.0
			while Game.directive == di and Game.step == st0 and tw0 < 30.0:
				await get_tree().process_frame
				tw0 += get_process_delta_time()
			await _wait_idle(60.0)
			await _wait(0.6)
			if di == 6 and guard == 1:
				await _shot("d06_stealth")
		if Game.directive == di and not Game.finished:
			_log("FAIL directive %d stuck at step %d" % [di, Game.step])
			fails += 1
			break
		await _wait(2.8)
		_log("directive %d done quota=%d level=%s" % [di, int(Game.quota), level.lname])
		if di in [0, 2, 8, 12, 13]:
			await _shot("d%02d_done" % di)
	await _wait(2.0)
	await _shot("90_final")
	open_map()
	await _wait(0.5)
	await _shot("91_map")
	close_menu()
	open_archive()
	await _wait(0.5)
	await _shot("92_archive")
	close_menu()
	open_pause()
	await _wait(0.3)
	await _shot("93_pause")
	close_menu()
	Game.set_lang("ru")
	await _wait(0.5)
	await _shot("94_ru")
	Game.set_lang("en")
	_log("AUTOTEST DONE fails=%d quota=%d finished=%s" % [fails, int(Game.quota), str(Game.finished)])
	await _wait(0.5)
	get_tree().quit()


func _tour() -> void:
	## --tour "level:x,z,zoom x,z,zoom ..." screenshots of spots (no story)
	var spec: String = str(Game.args["tour"])
	var parts := spec.split(" ", false)
	var lname := "severed"
	if parts.size() > 0 and parts[0].contains(":"):
		lname = parts[0].split(":")[0]
		parts[0] = parts[0].split(":")[1]
	await load_level(lname)
	state = "play"
	hud.visible = true
	refresh_hud()
	var k := 0
	for s in parts:
		var v := s.split(",")
		var pos := Vector3(float(v[0]), 0, float(v[1]))
		player().global_position = level.nearest_walkable(pos)
		zoom = float(v[2]) if v.size() > 2 else 13.0
		zoom_target = zoom
		snap_camera()
		await _wait(1.2)
		await _shot("tour_%02d" % k)
		k += 1
	get_tree().quit()
