extends RefCounted
## Screens built in code: title, pause, settings, directive archive, floor map.

const Quests := preload("res://scripts/quests.gd")


static func _overlay(alpha: float = 0.72) -> Control:
	var root := Control.new()
	UiKit.full(root)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	var bg := ColorRect.new()
	bg.color = Color(0.02, 0.05, 0.04, alpha)
	UiKit.full(bg)
	root.add_child(bg)
	return root


static func _window(root: Control, title: String, w: float = 620, h: float = 520) -> VBoxContainer:
	var p := UiKit.panel(Color(0.94, 0.95, 0.92, 0.98), 18, 3, UiKit.C_NAVY)
	root.add_child(p)
	var fit := func():
		UiKit.place(p, Control.PRESET_CENTER, Vector2.ZERO, Vector2(minf(w, root.size.x - 24), minf(h, root.size.y - 24)))
	root.resized.connect(fit)
	fit.call_deferred()
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	p.add_child(v)
	var t := UiKit.label(title, 30, UiKit.C_NAVY, true, HORIZONTAL_ALIGNMENT_CENTER)
	v.add_child(t)
	var line := ColorRect.new()
	line.color = UiKit.C_NAVY
	line.custom_minimum_size = Vector2(0, 2)
	v.add_child(line)
	return v


# ------------------------------------------------------------------ title
static func title(main) -> Control:
	var root := Control.new()
	UiKit.full(root)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	var grad := TextureRect.new()
	var gt := GradientTexture2D.new()
	var g := Gradient.new()
	g.set_color(0, Color(0.02, 0.05, 0.04, 0.0))
	g.set_color(1, Color(0.02, 0.05, 0.04, 0.85))
	gt.gradient = g
	gt.fill_from = Vector2(0.5, 0.0)
	gt.fill_to = Vector2(0.5, 1.0)
	grad.texture = gt
	UiKit.full(grad)
	grad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(grad)
	var v := VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", 10)
	root.add_child(v)
	var logo := Hud.LumonLogo.new()
	logo.custom_minimum_size = Vector2(120, 120)
	logo.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(logo)
	var tl := UiKit.label(Game.t("title"), 84, Color(0.93, 0.96, 0.94), true, HORIZONTAL_ALIGNMENT_CENTER)
	tl.add_theme_constant_override("outline_size", 14)
	tl.add_theme_color_override("font_outline_color", Color(0.02, 0.06, 0.05))
	v.add_child(tl)
	var st := UiKit.label(Game.t("subtitle"), 26, UiKit.C_TEAL, true, HORIZONTAL_ALIGNMENT_CENTER)
	st.add_theme_constant_override("outline_size", 8)
	st.add_theme_color_override("font_outline_color", Color(0.02, 0.06, 0.05))
	v.add_child(st)
	var sp := Control.new()
	sp.custom_minimum_size = Vector2(0, 20)
	v.add_child(sp)
	var bx := VBoxContainer.new()
	bx.add_theme_constant_override("separation", 10)
	bx.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(bx)
	if Game.has_save():
		var c := UiKit.button(Game.t("continue"), 26)
		c.custom_minimum_size = Vector2(340, 62)
		c.pressed.connect(func(): main.start_game(false))
		bx.add_child(c)
	var n := UiKit.button(Game.t("new_game"), 26, not Game.has_save())
	n.custom_minimum_size = Vector2(340, 62)
	n.pressed.connect(func():
		if Game.has_save():
			main.confirm(Game.t("new_game_confirm"), func(): main.start_game(true))
		else:
			main.start_game(true))
	bx.add_child(n)
	var s := UiKit.button(Game.t("settings"), 22, false)
	s.custom_minimum_size = Vector2(340, 52)
	s.pressed.connect(func(): main.open_settings())
	bx.add_child(s)
	if not Game.is_web and not Game.is_mobile:
		var q := UiKit.button(Game.t("quit"), 22, false)
		q.custom_minimum_size = Vector2(340, 52)
		q.pressed.connect(func(): main.get_tree().quit())
		bx.add_child(q)
	var cr := UiKit.label(Game.t("credits"), 14, Color(0.7, 0.8, 0.76), false, HORIZONTAL_ALIGNMENT_CENTER)
	root.add_child(cr)
	UiKit.place(cr, Control.PRESET_CENTER_BOTTOM, Vector2(0, -14), Vector2(900, 24))
	root.resized.connect(func(): UiKit.place(v, Control.PRESET_CENTER, Vector2(0, -10), Vector2(600, 620)))
	(func(): UiKit.place(v, Control.PRESET_CENTER, Vector2(0, -10), Vector2(600, 620))).call_deferred()
	return root


# ------------------------------------------------------------------ pause
static func pause(main) -> Control:
	var root := _overlay()
	var v := _window(root, Game.t("paused"), 460, 520)
	for pair in [["resume", func(): main.close_menu()], ["archive", func(): main.open_archive()],
			["map", func(): main.open_map()], ["settings", func(): main.open_settings()],
			["to_title", func(): main.to_title()]]:
		var b := UiKit.button(Game.t(pair[0]), 24, pair[0] == "resume")
		b.custom_minimum_size = Vector2(0, 58)
		b.pressed.connect(pair[1])
		v.add_child(b)
	return root


# ------------------------------------------------------------------ settings
static func settings(main) -> Control:
	var root := _overlay()
	var v := _window(root, Game.t("settings"), 560, 520)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 20)
	grid.add_theme_constant_override("v_separation", 16)
	v.add_child(grid)
	grid.add_child(UiKit.label(Game.t("language"), 22))
	var lh := HBoxContainer.new()
	for l in [["en", "English"], ["ru", "Русский"]]:
		var b := UiKit.button(l[1], 20, Game.lang == l[0])
		b.pressed.connect(func():
			Game.set_lang(l[0])
			main.open_settings())
		lh.add_child(b)
	grid.add_child(lh)
	grid.add_child(UiKit.label(Game.t("music"), 22))
	var ms := UiKit.slider(Game.music_vol)
	ms.value_changed.connect(func(x):
		Game.music_vol = x
		Sfx.refresh_volumes())
	grid.add_child(ms)
	grid.add_child(UiKit.label(Game.t("sounds"), 22))
	var ss := UiKit.slider(Game.sfx_vol)
	ss.value_changed.connect(func(x):
		Game.sfx_vol = x
		Sfx.refresh_volumes()
		Sfx.play("click", 0.8))
	grid.add_child(ss)
	grid.add_child(UiKit.label(Game.t("quality"), 22))
	var qh := HBoxContainer.new()
	for q in ["auto", "low", "high"]:
		var b := UiKit.button(Game.t("q_" + q), 18, Game.quality == q)
		b.pressed.connect(func():
			Game.quality = q
			Game.save_game()
			main.apply_quality()
			main.open_settings())
		qh.add_child(b)
	grid.add_child(qh)
	var sp := Control.new()
	sp.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(sp)
	var bk := UiKit.button(Game.t("back"), 22)
	bk.custom_minimum_size = Vector2(0, 56)
	bk.pressed.connect(func():
		Game.save_game()
		main.close_menu())
	v.add_child(bk)
	return root


# ------------------------------------------------------------------ archive
static func archive(main) -> Control:
	var root := _overlay()
	var v := _window(root, Game.t("archive"), 760, 640)
	var sc := ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	v.add_child(sc)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 8)
	sc.add_child(list)
	var act := 0
	for i in Quests.LIST.size():
		var d: Dictionary = Quests.LIST[i]
		if d["act"] != act:
			act = d["act"]
			list.add_child(UiKit.label(Game.t("act%d" % act), 18, UiKit.C_NAVY, true))
		var done: bool = i < Game.directive or Game.finished
		var cur: bool = i == Game.directive and not Game.finished
		var col := UiKit.C_INK if (done or cur) else Color(0.55, 0.6, 0.6)
		var h := HBoxContainer.new()
		var mark := UiKit.label("[x]" if done else ("[>]" if cur else "[ ]"), 18, UiKit.C_NAVY if cur else col, true)
		h.add_child(mark)
		var tv := VBoxContainer.new()
		tv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var title := ("%02d  " % (i + 1)) + (Game.t("d%d_title" % i) if (done or cur) else "????????")
		if d["who"] != "" and (done or cur):
			title += "  ·  " + Game.char_name(d["who"])
		tv.add_child(UiKit.label(title, 20, col))
		if cur or done:
			var dl := UiKit.label(Game.t("d%d_desc" % i), 15, Color(0.3, 0.38, 0.38))
			dl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			tv.add_child(dl)
		h.add_child(tv)
		list.add_child(h)
	if Game.directive > 9 or Game.finished:
		list.add_child(UiKit.label(Game.t("code_reminder", {"code": Game.code}), 20, UiKit.C_RED, true))
	var bk := UiKit.button(Game.t("close"), 22)
	bk.custom_minimum_size = Vector2(0, 54)
	bk.pressed.connect(func(): main.close_menu())
	v.add_child(bk)
	return root


# ------------------------------------------------------------------ map
static func map(main, level: Level, actors: Dictionary, target: Vector3) -> Control:
	var root := _overlay(0.85)
	var p := "res://assets/ui/map_%s.png" % level.lname
	var tex: Texture2D = load(p) if ResourceLoader.exists(p) else null
	var mv := MapView.new()
	mv.tex = tex
	mv.level = level
	mv.actors = actors
	mv.target = target
	UiKit.full(mv)
	root.add_child(mv)
	var bk := UiKit.button(Game.t("close"), 22)
	bk.pressed.connect(func(): main.close_menu())
	root.add_child(bk)
	UiKit.place(bk, Control.PRESET_CENTER_BOTTOM, Vector2(0, -16), Vector2(220, 54))
	var tl := UiKit.label(Game.t("floor_" + level.lname), 22, UiKit.C_TEAL, true, HORIZONTAL_ALIGNMENT_CENTER)
	root.add_child(tl)
	UiKit.place(tl, Control.PRESET_CENTER_TOP, Vector2(0, 14), Vector2(700, 30))
	return root


class MapView extends Control:
	var tex: Texture2D
	var level: Level
	var actors := {}
	var target := Vector3(-1, 0, -1)
	var _t := 0.0

	func _process(d: float) -> void:
		_t += d
		queue_redraw()

	func _draw() -> void:
		if tex == null or level == null:
			return
		var r: Array = level.data["map"]["rect"]
		var ww: float = r[2]
		var hh: float = r[3]
		var avail := size - Vector2(40, 140)
		var sc := minf(avail.x / ww, avail.y / hh)
		var org := (size - Vector2(ww, hh) * sc) / 2 + Vector2(0, 10)
		draw_texture_rect(tex, Rect2(org, Vector2(ww, hh) * sc), false)
		var font := UiKit.FONT
		# room names
		for rm in level.data["rooms"]:
			if rm["id"] == "hall":
				continue
			var rc: Array = rm["rects"][0]
			var c := org + Vector2((rc[0] + rc[2]) / 2.0, (rc[1] + rc[3]) / 2.0) * sc
			var nm := Game.t("room_" + String(rm["id"]))
			var fs := 14
			var tw := font.get_string_size(nm, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
			draw_string_outline(font, c - Vector2(tw / 2, 0), nm, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, 5, Color(0, 0, 0, 0.8))
			draw_string(font, c - Vector2(tw / 2, 0), nm, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.95, 0.97, 0.95))
		for id in actors:
			var a: Node3D = actors[id]
			if not is_instance_valid(a):
				continue
			var p := org + Vector2(a.global_position.x, a.global_position.z) * sc
			var innie: bool = id in Game.INNIES
			var col := UiKit.C_TEAL if id == Game.active else (Color(0.9, 0.9, 0.95) if innie else Color(0.95, 0.6, 0.4))
			draw_circle(p, 7.0 if id == Game.active else 5.0, col)
			if id == Game.active:
				draw_arc(p, 12 + 3 * sin(_t * 5), 0, TAU, 24, col, 2.0, true)
		if target.x >= 0:
			var tp := org + Vector2(target.x, target.z) * sc
			draw_arc(tp, 10 + 4 * sin(_t * 6), 0, TAU, 24, UiKit.C_GOLD, 3.0, true)
