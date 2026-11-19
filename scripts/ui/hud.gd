extends Control
class_name Hud
## In-game overlay: floor/room badge, directive card, quota, team portraits, USE button, toasts, banners and
## the off-screen arrow to the current target.

signal switch_requested(id: String)
signal use_pressed
signal pause_pressed
signal archive_pressed
signal map_pressed

var badge_floor: Label
var badge_room: Label
var card: PanelContainer
var card_head: Label
var card_title: Label
var card_step: Label
var quota_bar: ProgressBar
var quota_lbl: Label
var team_box: HBoxContainer
var team_btns := {}
var use_btn: Button
var toast_box: VBoxContainer
var banner: Label
var banner_sub: Label
var hint: Label
var arrow_target := Vector2(-1, -1)   # screen position of an off-screen target (set by main)
var arrow_on := false
var need_innie := ""
var _t := 0.0


func _ready() -> void:
	UiKit.full(self)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	# --- badge (top-left)
	var bp := UiKit.panel(Color(0.04, 0.09, 0.08, 0.82), 10, 1, UiKit.C_TEAL)
	var bv := VBoxContainer.new()
	bv.add_theme_constant_override("separation", 0)
	var top := HBoxContainer.new()
	var logo := LumonLogo.new()
	logo.custom_minimum_size = Vector2(30, 30)
	top.add_child(logo)
	var lt := UiKit.label("LUMON", 20, Color(0.85, 0.92, 0.95), true)
	top.add_child(lt)
	bv.add_child(top)
	badge_floor = UiKit.label("", 13, UiKit.C_TEAL, true)
	bv.add_child(badge_floor)
	badge_room = UiKit.label("", 16, Color(0.9, 0.93, 0.9))
	bv.add_child(badge_room)
	bp.add_child(bv)
	add_child(bp)
	UiKit.place(bp, Control.PRESET_TOP_LEFT, Vector2(14, 12), Vector2(250, 0))
	# --- directive card (top-centre)
	card = UiKit.panel(Color(0.93, 0.94, 0.91, 0.93), 12, 2, UiKit.C_NAVY)
	card.mouse_filter = Control.MOUSE_FILTER_STOP
	var cv := VBoxContainer.new()
	cv.add_theme_constant_override("separation", 2)
	card_head = UiKit.label("", 13, UiKit.C_NAVY, true)
	card_title = UiKit.label("", 22, UiKit.C_INK)
	card_step = UiKit.label("", 16, Color(0.2, 0.3, 0.3))
	card_step.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card_step.custom_minimum_size = Vector2(380, 0)
	cv.add_child(card_head)
	cv.add_child(card_title)
	cv.add_child(card_step)
	card.add_child(cv)
	add_child(card)
	card.gui_input.connect(func(e):
		if e is InputEventMouseButton and e.pressed:
			archive_pressed.emit())
	# --- quota + pause (top-right)
	var qp := UiKit.panel(Color(0.04, 0.09, 0.08, 0.82), 10, 1, UiKit.C_TEAL)
	var qv := VBoxContainer.new()
	quota_lbl = UiKit.label("", 15, UiKit.C_TEAL, true)
	qv.add_child(quota_lbl)
	quota_bar = ProgressBar.new()
	quota_bar.custom_minimum_size = Vector2(170, 12)
	quota_bar.show_percentage = false
	quota_bar.add_theme_stylebox_override("background", UiKit.sb(Color(0.1, 0.2, 0.18), 4, 0, Color.TRANSPARENT, 0))
	quota_bar.add_theme_stylebox_override("fill", UiKit.sb(UiKit.C_TEAL, 4, 0, Color.TRANSPARENT, 0))
	qv.add_child(quota_bar)
	qp.add_child(qv)
	add_child(qp)
	UiKit.place(qp, Control.PRESET_TOP_RIGHT, Vector2(-86, 12), Vector2(200, 0))
	var pb := UiKit.button("II", 22, true)
	pb.custom_minimum_size = Vector2(58, 54)
	pb.pressed.connect(func(): pause_pressed.emit())
	add_child(pb)
	UiKit.place(pb, Control.PRESET_TOP_RIGHT, Vector2(-14, 12), Vector2(58, 54))
	var mb := UiKit.button("▦", 22, false)
	mb.text = "MAP"
	mb.add_theme_font_size_override("font_size", 15)
	mb.pressed.connect(func(): map_pressed.emit())
	add_child(mb)
	UiKit.place(mb, Control.PRESET_TOP_RIGHT, Vector2(-14, 74), Vector2(58, 40))
	mb.set_meta("map_btn", true)
	# --- team (bottom-left)
	team_box = HBoxContainer.new()
	team_box.add_theme_constant_override("separation", 8)
	add_child(team_box)
	UiKit.place(team_box, Control.PRESET_BOTTOM_LEFT, Vector2(14, -14), Vector2(4 * 92, 96))
	# --- USE (bottom-right)
	use_btn = UiKit.button("", 24, true)
	use_btn.custom_minimum_size = Vector2(230, 74)
	use_btn.pressed.connect(func(): use_pressed.emit())
	use_btn.visible = false
	add_child(use_btn)
	UiKit.place(use_btn, Control.PRESET_BOTTOM_RIGHT, Vector2(-18, -18), Vector2(260, 74))
	# --- toasts, banner, hint
	toast_box = VBoxContainer.new()
	toast_box.alignment = BoxContainer.ALIGNMENT_BEGIN
	toast_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(toast_box)
	UiKit.place(toast_box, Control.PRESET_CENTER_TOP, Vector2(0, 150), Vector2(600, 200))
	banner = UiKit.label("", 46, Color(0.95, 0.97, 0.95), false, HORIZONTAL_ALIGNMENT_CENTER)
	banner.add_theme_constant_override("outline_size", 10)
	banner.add_theme_color_override("font_outline_color", Color(0.04, 0.1, 0.09))
	add_child(banner)
	UiKit.place(banner, Control.PRESET_CENTER, Vector2(0, -60), Vector2(1100, 70))
	banner_sub = UiKit.label("", 22, UiKit.C_TEAL, true, HORIZONTAL_ALIGNMENT_CENTER)
	banner_sub.add_theme_constant_override("outline_size", 8)
	banner_sub.add_theme_color_override("font_outline_color", Color(0.04, 0.1, 0.09))
	add_child(banner_sub)
	UiKit.place(banner_sub, Control.PRESET_CENTER, Vector2(0, 0), Vector2(1100, 40))
	banner.modulate.a = 0
	banner_sub.modulate.a = 0
	hint = UiKit.label("", 17, Color(0.9, 0.95, 0.92), false, HORIZONTAL_ALIGNMENT_CENTER)
	hint.add_theme_constant_override("outline_size", 6)
	hint.add_theme_color_override("font_outline_color", Color(0.04, 0.1, 0.09))
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(hint)
	UiKit.place(hint, Control.PRESET_CENTER_BOTTOM, Vector2(0, -110), Vector2(700, 60))
	resized.connect(_layout)
	_layout()


func _layout() -> void:
	var w := size.x
	var cw := clampf(w - 2 * 300, 300, 520)
	if w < 1000:
		cw = clampf(w - 2 * 230, 260, 480)
	card_step.custom_minimum_size = Vector2(cw - 40, 0)
	UiKit.place(card, Control.PRESET_CENTER_TOP, Vector2(0, 10), Vector2(cw, 0))


func set_floor(f: String, room: String) -> void:
	badge_floor.text = f
	badge_room.text = room


func set_directive(head: String, title: String, step: String) -> void:
	card_head.text = head
	card_title.text = title
	card_step.text = step
	card.reset_size()
	_layout()


func set_quota(q: float) -> void:
	quota_lbl.text = "%s  %d%%" % [Game.t("quota"), int(round(q))]
	var tw := create_tween()
	tw.tween_property(quota_bar, "value", q, 0.8)


func set_team(ids: Array, active: String) -> void:
	for c in team_box.get_children():
		c.queue_free()
	team_btns.clear()
	for id in ids:
		var b := Button.new()
		b.custom_minimum_size = Vector2(84, 92)
		b.focus_mode = Control.FOCUS_NONE
		var on: bool = id == active
		b.add_theme_stylebox_override("normal", UiKit.sb(Color(0.04, 0.09, 0.08, 0.85), 12, 3 if on else 1, UiKit.C_TEAL if on else Color(0.3, 0.4, 0.38), 2))
		b.add_theme_stylebox_override("hover", UiKit.sb(Color(0.08, 0.16, 0.14, 0.9), 12, 3, UiKit.C_TEAL, 2))
		b.add_theme_stylebox_override("pressed", UiKit.sb(Color(0.1, 0.2, 0.18, 0.9), 12, 3, UiKit.C_TEAL, 2))
		var v := VBoxContainer.new()
		v.mouse_filter = Control.MOUSE_FILTER_IGNORE
		v.add_theme_constant_override("separation", -4)
		var p := UiKit.portrait(id, 70)
		v.add_child(p)
		var n := UiKit.label(Game.char_name(id).split(" ")[0], 13, Color(0.9, 0.95, 0.92), false, HORIZONTAL_ALIGNMENT_CENTER)
		v.add_child(n)
		b.add_child(v)
		UiKit.full(v)
		b.pressed.connect(func(): switch_requested.emit(id))
		team_box.add_child(b)
		team_btns[id] = b


func set_use(label: String) -> void:
	use_btn.visible = label != ""
	if use_btn.text == label:
		return
	use_btn.text = label
	var fs := 24 if label.length() < 18 else (20 if label.length() < 26 else 17)
	use_btn.add_theme_font_size_override("font_size", fs)
	var w := clampf(use_btn.get_theme_font("font").get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x + 48, 200, minf(460, size.x * 0.45))
	UiKit.place(use_btn, Control.PRESET_BOTTOM_RIGHT, Vector2(-18, -18), Vector2(w, 74))


func toast(text: String, col: Color = Color(0.93, 0.96, 0.94)) -> void:
	var p := UiKit.panel(Color(0.04, 0.09, 0.08, 0.88), 10, 1, UiKit.C_TEAL)
	var l := UiKit.label(text, 19, col, false, HORIZONTAL_ALIGNMENT_CENTER)
	p.add_child(l)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	toast_box.add_child(p)
	p.modulate.a = 0
	var tw := create_tween()
	tw.tween_property(p, "modulate:a", 1.0, 0.25)
	tw.tween_interval(2.6)
	tw.tween_property(p, "modulate:a", 0.0, 0.5)
	tw.tween_callback(p.queue_free)


func show_banner(title: String, sub: String = "", dur: float = 2.6) -> void:
	banner.text = title
	banner_sub.text = sub
	banner.scale = Vector2(0.9, 0.9)
	banner.pivot_offset = banner.size / 2
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(banner, "modulate:a", 1.0, 0.35)
	tw.tween_property(banner_sub, "modulate:a", 1.0, 0.5)
	tw.tween_property(banner, "scale", Vector2.ONE, 0.5).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.chain().tween_interval(dur)
	tw.chain().tween_property(banner, "modulate:a", 0.0, 0.6)
	tw.parallel().tween_property(banner_sub, "modulate:a", 0.0, 0.6)


func set_hint(text: String) -> void:
	hint.text = text


func _process(delta: float) -> void:
	_t += delta
	for id in team_btns:
		var b: Button = team_btns[id]
		if id == need_innie:
			b.modulate = Color(1, 1, 1).lerp(Color(0.6, 1.4, 1.2), 0.5 + 0.5 * sin(_t * 6.0))
		else:
			b.modulate = Color.WHITE
	queue_redraw()


func _draw() -> void:
	if not arrow_on:
		return
	var c := size / 2
	var dir := (arrow_target - c).normalized()
	var m := Vector2(70, 120)
	var p := arrow_target
	p.x = clampf(p.x, m.x, size.x - m.x)
	p.y = clampf(p.y, m.y + 40, size.y - m.y)
	var pulse := 1.0 + 0.15 * sin(_t * 7.0)
	var a := dir.angle()
	var pts := PackedVector2Array([Vector2(26, 0), Vector2(-12, 16), Vector2(-4, 0), Vector2(-12, -16)])
	var out := PackedVector2Array()
	for q in pts:
		out.append(p + (q * pulse).rotated(a))
	draw_colored_polygon(out, Color(0.45, 0.95, 0.82, 0.95))
	draw_polyline(out + PackedVector2Array([out[0]]), Color(0.04, 0.1, 0.09), 2.0, true)


class LumonLogo extends Control:
	func _draw() -> void:
		var c := size / 2
		var r := minf(size.x, size.y) * 0.45
		var col := Color(0.61, 0.76, 0.9)
		for k in [1.0, 0.72, 0.45]:
			draw_arc(c, r * k, 0, TAU, 32, col, 1.6, true)
		draw_line(c - Vector2(r, 0), c + Vector2(r, 0), col, 1.2, true)
		for k in [0.35, 0.7]:
			var pts := PackedVector2Array()
			for i in 33:
				var a := TAU * i / 32.0
				pts.append(c + Vector2(cos(a) * r * k, sin(a) * r))
			draw_polyline(pts, col, 1.2, true)
