extends Minigame
## Macrodata Refinement. A field of drifting digits hides "scary" groups. Each group has a temper that shows in
## how it moves under the lens: Woe sinks, Frolic bounces, Dread trembles, Malice twitches. Tap a group, then
## tap the bin of its temper. args: file (index), time (seconds, optional), final (bool), free (bool).

const Quests := preload("res://scripts/quests.gd")
const TEMPERS := ["wo", "fc", "dr", "ma"]

var field: NumberField
var bins := {}
var bin_bars := {}
var groups := []          # {cells: [i], temper, done}
var selected := -1
var total := 0
var refined := 0
var time_left := -1.0
var file_name := ""
var hint_lbl: Label


func _build() -> void:
	var fi: int = args.get("file", 0)
	file_name = Quests.FILES[fi % Quests.FILES.size()]
	title_lbl.text = Game.t("mdr_title") + "  ·  " + Game.t("mdr_file", {"name": file_name})
	if args.has("time"):
		time_left = float(args["time"])
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	UiKit.full(v)
	body.add_child(v)
	hint_lbl = UiKit.label(Game.t("mdr_hint") + "\n" + Game.t("mdr_legend"), 15, Color(0.45, 0.95, 0.82, 0.75), true,
		HORIZONTAL_ALIGNMENT_CENTER)
	hint_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(hint_lbl)
	field = NumberField.new()
	field.mg = self
	field.size_flags_vertical = Control.SIZE_EXPAND_FILL
	field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(field)
	var bh := HBoxContainer.new()
	bh.add_theme_constant_override("separation", 10)
	bh.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(bh)
	for k in TEMPERS.size():
		var tmp: String = TEMPERS[k]
		var bv := VBoxContainer.new()
		bv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var b := UiKit.crt_button("0%d  %s" % [k + 1, Game.t("bin_" + tmp)], 19)
		b.custom_minimum_size = Vector2(0, 56)
		b.pressed.connect(_on_bin.bind(tmp))
		bv.add_child(b)
		var pb := ProgressBar.new()
		pb.custom_minimum_size = Vector2(0, 10)
		pb.show_percentage = false
		pb.add_theme_stylebox_override("background", UiKit.sb(Color(0.1, 0.25, 0.2), 2, 0, Color.TRANSPARENT, 0))
		pb.add_theme_stylebox_override("fill", UiKit.sb(UiKit.TEMPER_COL[tmp], 2, 0, Color.TRANSPARENT, 0))
		bv.add_child(pb)
		bh.add_child(bv)
		bins[tmp] = b
		bin_bars[tmp] = pb
	call_deferred("_make_groups")


func _make_groups() -> void:
	var n_per := 2
	if args.get("final", false):
		n_per = 3
	elif args.has("time"):
		n_per = 2
	elif args.get("free", false):
		n_per = 1 + randi() % 2
	var cols := field.cols
	var rows := field.rows
	var used := {}
	for tmp in TEMPERS:
		for k in n_per:
			for attempt in 60:
				var start := Vector2i(randi_range(1, cols - 2), randi_range(1, rows - 2))
				var cells := [start]
				var ok := true
				var cur := start
				var want := randi_range(4, 6)
				var tries := 0
				while cells.size() < want and tries < 40:
					tries += 1
					var d: Vector2i = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)].pick_random()
					var nx: Vector2i = cur + d
					if nx.x < 0 or nx.y < 0 or nx.x >= cols or nx.y >= rows:
						continue
					if not cells.has(nx):
						cells.append(nx)
					cur = nx
				for c in cells:
					for dy in range(-1, 2):
						for dx in range(-1, 2):
							if used.has(c + Vector2i(dx, dy)):
								ok = false
				if ok:
					var idxs := []
					for c in cells:
						used[c] = true
						idxs.append(c.y * cols + c.x)
					groups.append({"cells": idxs, "temper": tmp, "done": false, "phase": randf() * TAU})
					break
	total = groups.size()
	for g in groups.size():
		for i in groups[g]["cells"]:
			field.group_of[i] = g
	_update_info()


func _update_info() -> void:
	var pct := int(round(100.0 * refined / maxf(total, 1)))
	var s := "%d%%" % pct
	if time_left >= 0.0:
		s = Game.t("mdr_time", {"t": "%d:%02d" % [int(time_left) / 60, int(time_left) % 60]}) + "   " + s
	info_lbl.text = s + "   "
	for tmp in TEMPERS:
		var n := 0
		var d := 0
		for g in groups:
			if g["temper"] == tmp:
				n += 1
				if g["done"]:
					d += 1
		(bin_bars[tmp] as ProgressBar).value = 100.0 * d / maxf(n, 1)


func select_group(g: int) -> void:
	if g < 0 or groups[g]["done"]:
		selected = -1
		Sfx.play("tick", 0.4)
		return
	selected = g
	Sfx.play("select", 0.7)


func _on_bin(tmp: String) -> void:
	if selected < 0 or finished:
		shake(bins[tmp])
		return
	var g: Dictionary = groups[selected]
	if g["temper"] == tmp:
		g["done"] = true
		refined += 1
		field.fly(g["cells"], bins[tmp].get_global_rect().get_center(), UiKit.TEMPER_COL[tmp])
		Sfx.play("refine", 0.8, randf_range(0.95, 1.08))
		selected = -1
		_update_info()
		if refined >= total:
			flash_info(Game.t("mdr_done"), UiKit.C_TEAL)
			finish(true)
	else:
		Sfx.play("wrong", 0.8)
		shake(bins[tmp])
		flash_info(Game.t("mdr_wrong"))
		if time_left > 0.0:
			time_left = maxf(time_left - 5.0, 0.0)
		selected = -1


func _tick(delta: float) -> void:
	if time_left > 0.0 and not finished:
		time_left -= delta
		if int(time_left + delta) != int(time_left):
			_update_info()
		if time_left <= 0.0:
			flash_info(Game.t("mdr_timeout"))
			time_left = float(args["time"])
			for g in groups:
				g["done"] = false
			refined = 0
			_update_info()


func autosolve() -> void:
	# play it properly: select each group and drop it in the right bin
	for gi in groups.size():
		if not groups[gi]["done"]:
			selected = gi
			_on_bin(groups[gi]["temper"])
			_auto_t = 0.12
			return


class NumberField extends Control:
	var mg
	var cols := 16
	var rows := 8
	var vals := []
	var group_of := {}
	var lens := Vector2(-999, -999)
	var lens_on := false
	var t := 0.0
	var flyers := []
	var font := UiKit.MONO

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		clip_contents = true
		for i in cols * rows:
			vals.append(randi() % 10)

	func cell_pos(i: int) -> Vector2:
		var cw := size.x / cols
		var ch := size.y / rows
		return Vector2((i % cols + 0.5) * cw, (i / cols + 0.5) * ch)

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseMotion:
			lens = e.position
			lens_on = true
		elif e is InputEventScreenDrag:
			lens = e.position
			lens_on = true
		elif e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			lens = e.position
			lens_on = true
			var best := -1
			var bd := 1e9
			for i in vals.size():
				var d := cell_pos(i).distance_to(e.position)
				if d < bd:
					bd = d
					best = i
			mg.select_group(group_of.get(best, -1) if bd < size.x / cols else -1)

	func fly(cells: Array, target_global: Vector2, col: Color) -> void:
		for i in cells:
			flyers.append({"p": cell_pos(i), "v": vals[i], "t": 0.0, "to": target_global - global_position, "col": col})
			vals[i] = randi() % 10

	func _process(delta: float) -> void:
		t += delta
		var i := 0
		while i < flyers.size():
			flyers[i]["t"] += delta * 1.6
			if flyers[i]["t"] >= 1.0:
				flyers.remove_at(i)
			else:
				i += 1
		queue_redraw()

	func _offset(g: int, k: float) -> Vector2:
		var tmp: String = mg.groups[g]["temper"]
		var ph: float = mg.groups[g]["phase"]
		match tmp:
			"wo":
				return Vector2(0, (0.5 + 0.5 * sin(t * 1.3 + ph)) * 14.0 * k)
			"fc":
				return Vector2(0, -absf(sin(t * 5.0 + ph)) * 16.0 * k)
			"dr":
				return Vector2(randf_range(-1, 1), randf_range(-1, 1)) * 4.5 * k
			"ma":
				var s := sin(t * 2.2 + ph)
				return Vector2((12.0 if s > 0.85 else (-12.0 if s < -0.85 else 0.0)) * k, 0)
		return Vector2.ZERO

	func _draw() -> void:
		if size.x < 40 or size.y < 40:
			return
		var cw := size.x / cols
		var ch := size.y / rows
		var fs := int(minf(cw, ch) * 0.55)
		var lr := minf(size.x, size.y) * 0.24
		for i in vals.size():
			var p := cell_pos(i)
			var g: int = group_of.get(i, -1)
			var gd: bool = g >= 0 and mg.groups.size() > g and mg.groups[g]["done"]
			var drift := Vector2(sin(t * 0.7 + i * 1.3), cos(t * 0.6 + i * 0.7)) * 2.0
			var dist := p.distance_to(lens) if lens_on else 1e9
			var k := clampf(1.0 - dist / lr, 0.0, 1.0)
			var sc := 1.0 + k * 0.9
			var col := Color(0.45, 0.95, 0.82, 0.55 + 0.45 * k)
			var off := drift
			if g >= 0 and not gd:
				off += _offset(g, 0.35 + k * 1.3)
				sc += 0.1 * k
				if k > 0.05:
					col = col.lerp(UiKit.TEMPER_COL[mg.groups[g]["temper"]], 0.25 * k)
				if g == mg.selected:
					col = Color(1, 1, 1)
					sc *= 1.25
			var s := str(vals[i])
			var fsz := maxi(4, int(fs * sc))
			var tw := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, fsz).x
			draw_string(font, p + off + Vector2(-tw / 2, fsz * 0.35), s, HORIZONTAL_ALIGNMENT_LEFT, -1, fsz, col)
		if mg.selected >= 0:
			for i in mg.groups[mg.selected]["cells"]:
				var p := cell_pos(i)
				draw_rect(Rect2(p - Vector2(cw, ch) * 0.45, Vector2(cw, ch) * 0.9), Color(1, 1, 1, 0.12), true)
		for f in flyers:
			var a: Vector2 = f["p"]
			var b: Vector2 = f["to"]
			var tt: float = f["t"]
			var e := tt * tt * (3 - 2 * tt)
			var pp := a.lerp(b, e) + Vector2(0, -sin(tt * PI) * 80)
			draw_string(font, pp, str(f["v"]), HORIZONTAL_ALIGNMENT_CENTER, -1, maxi(4, int(fs * (1.2 - tt * 0.6))), f["col"] * Color(1, 1, 1, 1 - tt * 0.5))
		# lens ring
		if lens_on:
			draw_arc(lens, lr * 0.98, 0, TAU, 48, Color(0.45, 0.95, 0.82, 0.12), 2.0, true)
		# scanlines
		var y := 0.0
		while y < size.y:
			draw_line(Vector2(0, y), Vector2(size.x, y), Color(0, 0, 0, 0.12), 1.0)
			y += 3.0
