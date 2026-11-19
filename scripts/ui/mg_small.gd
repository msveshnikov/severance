extends RefCounted
## The smaller minigames, each an inner class extending Minigame. Create with MgSmall.make(kind, args).

const Dance := preload("res://scripts/ui/mg_dance.gd")
const Mdr := preload("res://scripts/ui/mg_mdr.gd")


static func make(kind: String, args: Dictionary) -> Minigame:
	match kind:
		"mdr":
			return Mdr.new(args)
		"compunction":
			return Compunction.new(args)
		"printer":
			return Printer.new(args)
		"wellness":
			return Wellness.new(args)
		"goats":
			return Goats.new(args)
		"keypad":
			return Keypad.new(args)
		"dance":
			return Dance.new(args)
	return Minigame.new(args)


# =============================================================================== Statement of Compunction
class Compunction extends Minigame:
	var meter: Control
	var hits := 0
	var need := 5
	var needle := 0.0
	var spd := 1.2
	var zone_w := 0.3
	var zone_c := 0.5
	var text_lbl: RichTextLabel
	var dots: Label
	var _tt := 0.0

	func _build() -> void:
		title_lbl.text = Game.t("comp_title")
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 20)
		UiKit.full(h)
		body.add_child(h)
		var left := VBoxContainer.new()
		left.add_child(UiKit.portrait("milchick", 180))
		var nl := UiKit.label(Game.char_name("milchick").to_upper(), 18, UiKit.C_TEAL, true, HORIZONTAL_ALIGNMENT_CENTER)
		left.add_child(nl)
		h.add_child(left)
		var v := VBoxContainer.new()
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		v.add_theme_constant_override("separation", 14)
		h.add_child(v)
		text_lbl = RichTextLabel.new()
		text_lbl.fit_content = true
		text_lbl.add_theme_font_override("normal_font", UiKit.MONO)
		text_lbl.add_theme_font_size_override("normal_font_size", 20)
		text_lbl.add_theme_color_override("default_color", Color(0.85, 0.95, 0.9))
		text_lbl.text = Game.t("comp_text")
		text_lbl.visible_characters = 0
		text_lbl.custom_minimum_size = Vector2(0, 150)
		v.add_child(text_lbl)
		v.add_child(UiKit.label(Game.t("comp_sincerity"), 16, UiKit.C_TEAL, true))
		meter = Control.new()
		meter.custom_minimum_size = Vector2(0, 56)
		meter.draw.connect(_draw_meter)
		v.add_child(meter)
		dots = UiKit.label("", 30, UiKit.C_TEAL, true, HORIZONTAL_ALIGNMENT_CENTER)
		v.add_child(dots)
		var b := UiKit.crt_button(Game.t("comp_btn"), 28)
		b.custom_minimum_size = Vector2(0, 70)
		b.pressed.connect(_press)
		v.add_child(b)
		v.add_child(UiKit.label(Game.t("comp_hint"), 15, Color(0.45, 0.95, 0.82, 0.7), true, HORIZONTAL_ALIGNMENT_CENTER))
		_update()

	func _update() -> void:
		var s := ""
		for i in need:
			s += ("■ " if i < hits else "□ ")
		dots.text = s

	func _draw_meter() -> void:
		var w := meter.size.x
		var hh := meter.size.y
		meter.draw_rect(Rect2(0, hh * 0.3, w, hh * 0.4), Color(0.1, 0.25, 0.2), true)
		meter.draw_rect(Rect2((zone_c - zone_w / 2) * w, hh * 0.25, zone_w * w, hh * 0.5), Color(0.35, 0.85, 0.5, 0.8), true)
		var x := needle * w
		meter.draw_rect(Rect2(x - 3, 0, 6, hh), Color(1, 0.95, 0.8), true)

	func _press() -> void:
		if finished:
			return
		if absf(needle - zone_c) <= zone_w / 2:
			hits += 1
			Sfx.play("good", 0.8)
			flash_info(Game.t("comp_good"), UiKit.C_TEAL)
			zone_w = maxf(0.1, zone_w * 0.8)
			spd *= 1.15
			zone_c = randf_range(0.2, 0.8)
			if hits >= need:
				finish(true)
		else:
			hits = maxi(0, hits - 1)
			Sfx.play("wrong", 0.8)
			flash_info(Game.t("comp_again"))
		_update()

	func _tick(delta: float) -> void:
		_tt += delta
		needle = 0.5 + 0.5 * sin(_tt * spd * 2.0)
		if text_lbl.visible_characters >= 0:
			text_lbl.visible_characters += 1 if fmod(_tt, 0.03) < delta else 0
			if text_lbl.visible_characters >= text_lbl.text.length():
				text_lbl.visible_characters = -1
		meter.queue_redraw()

	func _unhandled_input(e: InputEvent) -> void:
		if e is InputEventKey and e.pressed and not e.echo and e.keycode == KEY_SPACE:
			_press()

	func autosolve() -> void:
		needle = zone_c
		_press()
		if not finished:
			_auto_t = 0.2


# =============================================================================== O&D printer
class Printer extends Minigame:
	var temp := 30.0
	var vel := 0.0
	var holding := false
	var band := 75.0
	var prog := 0.0
	var gauge: Control
	var card: Control
	var _tt := 0.0

	func _build() -> void:
		title_lbl.text = Game.t("pr_title")
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 24)
		UiKit.full(h)
		body.add_child(h)
		gauge = Control.new()
		gauge.custom_minimum_size = Vector2(160, 0)
		gauge.draw.connect(_draw_gauge)
		h.add_child(gauge)
		var v := VBoxContainer.new()
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		v.add_theme_constant_override("separation", 12)
		h.add_child(v)
		v.add_child(UiKit.label(Game.t("pr_hint"), 18, Color(0.85, 0.95, 0.9), true))
		card = Control.new()
		card.size_flags_vertical = Control.SIZE_EXPAND_FILL
		card.draw.connect(_draw_card)
		v.add_child(card)
		var b := UiKit.crt_button(Game.t("pr_hold"), 26, UiKit.C_GOLD)
		b.custom_minimum_size = Vector2(0, 80)
		b.button_down.connect(func(): holding = true)
		b.button_up.connect(func(): holding = false)
		v.add_child(b)

	func _tick(delta: float) -> void:
		_tt += delta
		band = 70.0 + 12.0 * sin(_tt * 0.7)
		var acc := 55.0 if holding or Input.is_key_pressed(KEY_SPACE) else -45.0
		vel = clampf(vel + acc * delta, -40.0, 40.0)
		temp = clampf(temp + vel * delta, 0.0, 110.0)
		if temp <= 0.0:
			vel = 0.0
		if absf(temp - band) < 8.0:
			prog = minf(1.0, prog + delta * 0.11)
			if randf() < delta * 6.0:
				Sfx.play("print", 0.25, randf_range(0.9, 1.2))
		if temp >= 105.0 and not finished:
			prog = 0.0
			temp = 40.0
			vel = 0.0
			Sfx.play("wrong", 0.8)
			flash_info(Game.t("pr_over"))
		info_lbl.text = "%s %d°C   %s %d%%   " % [Game.t("pr_temp"), int(temp), Game.t("pr_progress"), int(prog * 100)]
		if prog >= 1.0 and not finished:
			flash_info(Game.t("pr_done"), UiKit.C_TEAL)
			finish(true)
		gauge.queue_redraw()
		card.queue_redraw()

	func _draw_gauge() -> void:
		var s := gauge.size
		var x := s.x * 0.5
		var top := 10.0
		var bot := s.y - 30
		gauge.draw_rect(Rect2(x - 26, top, 52, bot - top), Color(0.1, 0.2, 0.18), true)
		var yb := bot - (band + 8) / 110.0 * (bot - top)
		var ye := bot - (band - 8) / 110.0 * (bot - top)
		gauge.draw_rect(Rect2(x - 26, yb, 52, ye - yb), Color(0.35, 0.85, 0.5, 0.7), true)
		var yt := bot - temp / 110.0 * (bot - top)
		var col := Color(0.95, 0.4, 0.3) if temp > 95 else Color(1, 0.85, 0.5)
		gauge.draw_rect(Rect2(x - 14, yt, 28, bot - yt), col, true)
		gauge.draw_circle(Vector2(x, bot + 8), 22, col)
		gauge.draw_rect(Rect2(x - 26, top, 52, bot - top), UiKit.C_TEAL, false, 2.0)

	func _draw_card() -> void:
		var s := card.size
		var w := minf(s.x * 0.6, 340)
		var hh := w * 0.63
		var r := Rect2((s.x - w) / 2, (s.y - hh) / 2, w, hh)
		card.draw_rect(r, Color(0.2, 0.3, 0.28, 0.6), false, 2.0)
		var fill := Rect2(r.position, Vector2(w, hh * prog))
		card.draw_rect(fill, Color(0.7, 0.15, 0.17), true)
		card.draw_rect(Rect2(r.position + Vector2(0, hh * 0.18), Vector2(w, hh * 0.12 * minf(prog * 3, 1))), Color(0.1, 0.1, 0.1), true)
		var hy := r.position.y + hh * prog
		card.draw_rect(Rect2(r.position.x - 10, hy - 6, w + 20, 12), Color(0.9, 0.55, 0.2), true)

	func autosolve() -> void:
		prog = 1.0


# =============================================================================== Wellness session
class Wellness extends Minigame:
	var calm := 0.0
	var circle: Control
	var fact_lbl: Label
	var fact_i := 0
	var _tt := 0.0
	var period := 3.0

	func _build() -> void:
		title_lbl.text = Game.t("wl_title")
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 20)
		UiKit.full(h)
		body.add_child(h)
		var left := VBoxContainer.new()
		left.add_child(UiKit.portrait("casey", 180))
		left.add_child(UiKit.label(Game.char_name("casey").to_upper(), 18, UiKit.C_TEAL, true, HORIZONTAL_ALIGNMENT_CENTER))
		h.add_child(left)
		var v := VBoxContainer.new()
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		h.add_child(v)
		fact_lbl = UiKit.label("“" + Game.t("wl_fact0") + "”", 24, Color(0.9, 0.95, 0.95), false, HORIZONTAL_ALIGNMENT_CENTER)
		fact_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		fact_lbl.custom_minimum_size = Vector2(0, 70)
		v.add_child(fact_lbl)
		circle = Control.new()
		circle.size_flags_vertical = Control.SIZE_EXPAND_FILL
		circle.mouse_filter = Control.MOUSE_FILTER_STOP
		circle.draw.connect(_draw_circle)
		circle.gui_input.connect(func(e):
			if e is InputEventMouseButton and e.pressed:
				_tap())
		v.add_child(circle)
		var b := UiKit.crt_button(Game.t("wl_tap"), 24, Color(0.55, 0.8, 1.0))
		b.custom_minimum_size = Vector2(0, 64)
		b.pressed.connect(_tap)
		v.add_child(b)
		v.add_child(UiKit.label(Game.t("wl_hint"), 15, Color(0.45, 0.95, 0.82, 0.7), true, HORIZONTAL_ALIGNMENT_CENTER))

	func _phase() -> float:
		return 0.5 - 0.5 * cos(_tt / period * TAU)

	func _tap() -> void:
		if finished:
			return
		var err := absf(_phase() - 0.72)
		if err < 0.06:
			calm += 22
			Sfx.play("good", 0.8, 1.1)
		elif err < 0.14:
			calm += 12
			Sfx.play("good", 0.6)
		else:
			calm = maxf(0, calm - 8)
			Sfx.play("wrong", 0.6)
		fact_i += 1
		fact_lbl.text = "“" + Game.t("wl_fact%d" % (fact_i % 8)) + "”"
		if calm >= 100:
			finish(true)

	func _tick(delta: float) -> void:
		_tt += delta
		info_lbl.text = "%s %d%%   " % [Game.t("wl_calm"), int(minf(calm, 100))]
		circle.queue_redraw()

	func _draw_circle() -> void:
		var c := circle.size / 2
		var rmax := minf(c.x, c.y) * 0.95
		var target := rmax * 0.72
		circle.draw_arc(c, target, 0, TAU, 64, Color(0.55, 0.8, 1.0, 0.9), 4.0, true)
		var r := rmax * _phase()
		circle.draw_circle(c, r, Color(0.55, 0.8, 1.0, 0.18))
		circle.draw_arc(c, r, 0, TAU, 64, Color(0.8, 0.95, 1.0), 2.0, true)
		circle.draw_arc(c, rmax, -PI / 2, -PI / 2 + TAU * minf(calm, 100) / 100.0, 64, UiKit.C_TEAL, 6.0, true)

	func _unhandled_input(e: InputEvent) -> void:
		if e is InputEventKey and e.pressed and not e.echo and e.keycode == KEY_SPACE:
			_tap()

	func autosolve() -> void:
		_tt = acos(1.0 - 2.0 * 0.72) / TAU * period
		_tap()
		if not finished:
			_auto_t = 0.15


# =============================================================================== Goat feeding
class Goats extends Minigame:
	var goats := []      # {state, t, fed, btn, bubble}
	var need := 3
	var _tt := 0.0

	func _build() -> void:
		title_lbl.text = Game.t("gt_title")
		var v := VBoxContainer.new()
		UiKit.full(v)
		v.add_theme_constant_override("separation", 10)
		body.add_child(v)
		v.add_child(UiKit.label(Game.t("gt_hint"), 18, Color(0.9, 0.95, 0.9), true, HORIZONTAL_ALIGNMENT_CENTER))
		var h := HBoxContainer.new()
		h.size_flags_vertical = Control.SIZE_EXPAND_FILL
		h.add_theme_constant_override("separation", 18)
		v.add_child(h)
		for i in 3:
			var b := Button.new()
			b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			b.focus_mode = Control.FOCUS_NONE
			b.add_theme_stylebox_override("normal", UiKit.sb(Color(0.25, 0.4, 0.2, 0.6), 14, 2, Color(0.5, 0.8, 0.4), 6))
			b.add_theme_stylebox_override("hover", UiKit.sb(Color(0.3, 0.5, 0.25, 0.7), 14, 2, Color(0.6, 0.9, 0.5), 6))
			b.add_theme_stylebox_override("pressed", UiKit.sb(Color(0.35, 0.55, 0.3, 0.8), 14, 2, Color(0.6, 0.9, 0.5), 6))
			var gv := VBoxContainer.new()
			gv.mouse_filter = Control.MOUSE_FILTER_IGNORE
			UiKit.full(gv)
			var bub := UiKit.label("", 34, Color(1, 1, 1), true, HORIZONTAL_ALIGNMENT_CENTER)
			gv.add_child(bub)
			var pic := UiKit.portrait("goat", 190)
			pic.size_flags_vertical = Control.SIZE_EXPAND_FILL
			gv.add_child(pic)
			var fed := UiKit.label("", 26, UiKit.C_GOLD, true, HORIZONTAL_ALIGNMENT_CENTER)
			gv.add_child(fed)
			b.add_child(gv)
			b.pressed.connect(_tap.bind(i))
			h.add_child(b)
			goats.append({"state": "idle", "t": randf_range(0.5, 2.0), "fed": 0, "btn": b, "bub": bub, "lbl": fed, "pic": pic})
		_refresh()

	func _refresh() -> void:
		var tot := 0
		for g in goats:
			tot += mini(g["fed"], need)
			(g["lbl"] as Label).text = "%d / %d" % [mini(g["fed"], need), need]
		info_lbl.text = Game.t("gt_fed", {"n": tot, "m": need * goats.size()}) + "   "

	func _tap(i: int) -> void:
		var g: Dictionary = goats[i]
		if g["state"] == "hungry":
			g["fed"] += 1
			g["state"] = "idle"
			g["t"] = randf_range(0.8, 2.0)
			(g["bub"] as Label).text = "♥"
			Sfx.play("slurp", 0.8, randf_range(0.9, 1.2))
			var pic: Control = g["pic"]
			pic.pivot_offset = pic.size / 2
			var tw := create_tween()
			tw.tween_property(pic, "scale", Vector2(1.15, 0.9), 0.08)
			tw.tween_property(pic, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_BACK)
		elif g["state"] == "sleepy":
			Sfx.play("bleat", 0.9, 0.7)
			flash_info("…", UiKit.C_GOLD)
			g["fed"] = maxi(0, g["fed"] - 1)
			g["state"] = "idle"
			g["t"] = 1.5
		else:
			Sfx.play("tick", 0.4)
		_refresh()
		var done_all := true
		for gg in goats:
			if gg["fed"] < need:
				done_all = false
		if done_all:
			finish(true)

	func _tick(delta: float) -> void:
		_tt += delta
		for g in goats:
			if g["fed"] >= need:
				(g["bub"] as Label).text = "✓"
				continue
			g["t"] -= delta
			if g["t"] <= 0.0:
				match g["state"]:
					"idle":
						if randf() < 0.75:
							g["state"] = "hungry"
							g["t"] = 1.6
							(g["bub"] as Label).text = "MEEH!"
							Sfx.play("bleat", 0.8, randf_range(1.1, 1.4))
						else:
							g["state"] = "sleepy"
							g["t"] = 1.8
							(g["bub"] as Label).text = "z z z"
					_:
						g["state"] = "idle"
						g["t"] = randf_range(0.6, 1.8)
						(g["bub"] as Label).text = ""
			var pic: Control = g["pic"]
			if g["state"] == "hungry":
				pic.rotation = sin(_tt * 20.0) * 0.06
			else:
				pic.rotation = 0.0

	func autosolve() -> void:
		for g in goats:
			g["fed"] = need
		_tap(0)


# =============================================================================== Keypad
class Keypad extends Minigame:
	var entry := ""
	var disp: Label

	func _init(a: Dictionary = {}) -> void:
		super(a)
		window_size = Vector2(520, 620)

	func _build() -> void:
		title_lbl.text = Game.t("kp_title")
		var v := VBoxContainer.new()
		UiKit.full(v)
		v.add_theme_constant_override("separation", 10)
		body.add_child(v)
		v.add_child(UiKit.label(Game.t("kp_hint"), 17, Color(0.85, 0.95, 0.9), true, HORIZONTAL_ALIGNMENT_CENTER))
		disp = UiKit.label("_ _ _ _", 48, UiKit.C_TEAL, true, HORIZONTAL_ALIGNMENT_CENTER)
		v.add_child(disp)
		var g := GridContainer.new()
		g.columns = 3
		g.add_theme_constant_override("h_separation", 10)
		g.add_theme_constant_override("v_separation", 10)
		g.size_flags_vertical = Control.SIZE_EXPAND_FILL
		v.add_child(g)
		for k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "OK"]:
			var b := UiKit.crt_button(k, 30)
			b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			b.size_flags_vertical = Control.SIZE_EXPAND_FILL
			b.pressed.connect(_key.bind(k))
			g.add_child(b)

	func _key(k: String) -> void:
		if finished:
			return
		if k == "C":
			entry = ""
		elif k == "OK":
			if entry == Game.code:
				disp.text = Game.t("kp_granted")
				disp.add_theme_font_size_override("font_size", 30)
				finish(true)
				return
			disp.text = Game.t("kp_denied")
			Sfx.play("wrong", 0.9)
			shake(disp)
			entry = ""
			await get_tree().create_timer(0.8).timeout
		elif entry.length() < 4:
			entry += k
		var s := ""
		for i in 4:
			s += (entry[i] if i < entry.length() else "_") + " "
		disp.text = s.strip_edges()

	func _unhandled_input(e: InputEvent) -> void:
		if e is InputEventKey and e.pressed and not e.echo:
			if e.keycode >= KEY_0 and e.keycode <= KEY_9:
				_key(str(e.keycode - KEY_0))
			elif e.keycode >= KEY_KP_0 and e.keycode <= KEY_KP_9:
				_key(str(e.keycode - KEY_KP_0))
			elif e.keycode in [KEY_ENTER, KEY_KP_ENTER]:
				_key("OK")
			elif e.keycode == KEY_BACKSPACE:
				_key("C")

	func autosolve() -> void:
		entry = Game.code
		_key("OK")
