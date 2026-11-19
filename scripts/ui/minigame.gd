extends Control
class_name Minigame
## Base for the CRT minigames: dims the floor, opens a terminal-style window, emits `done(ok)`.

signal done(ok: bool)

var args := {}
var win: PanelContainer
var body: Control
var title_lbl: Label
var info_lbl: Label
var exit_btn: Button
var finished := false
var _auto_t := -1.0
var window_size := Vector2(1040, 620)
var dim := true


func _init(a: Dictionary = {}) -> void:
	args = a


func _ready() -> void:
	UiKit.full(self)
	mouse_filter = Control.MOUSE_FILTER_STOP
	if dim:
		var bg := ColorRect.new()
		bg.color = Color(0.0, 0.03, 0.02, 0.6)
		UiKit.full(bg)
		bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(bg)
	win = PanelContainer.new()
	win.add_theme_stylebox_override("panel", UiKit.sb(UiKit.C_CRT, 18, 3, Color(0.35, 0.75, 0.65), 18))
	add_child(win)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	win.add_child(v)
	var head := HBoxContainer.new()
	title_lbl = UiKit.label("", 22, UiKit.C_TEAL, true)
	title_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(title_lbl)
	info_lbl = UiKit.label("", 20, UiKit.C_TEAL, true)
	head.add_child(info_lbl)
	exit_btn = UiKit.crt_button("[X] " + Game.t("mdr_exit"), 18)
	exit_btn.pressed.connect(func(): finish(false))
	head.add_child(exit_btn)
	v.add_child(head)
	var line := ColorRect.new()
	line.color = Color(0.45, 0.95, 0.82, 0.5)
	line.custom_minimum_size = Vector2(0, 2)
	v.add_child(line)
	body = Control.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.clip_contents = false
	v.add_child(body)
	resized.connect(_layout)
	_build()
	_layout()
	win.pivot_offset = win.size / 2
	win.scale = Vector2(0.92, 0.92)
	win.modulate.a = 0.0
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(win, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(win, "modulate:a", 1.0, 0.2)
	Sfx.play("crt_on", 0.7)
	if Game.autotest:
		_auto_t = 2.5


func _layout() -> void:
	var w := minf(size.x - 24, window_size.x)
	var h := minf(size.y - 24, window_size.y)
	UiKit.place(win, Control.PRESET_CENTER, Vector2.ZERO, Vector2(w, h))
	win.pivot_offset = win.size / 2


func _build() -> void:
	pass


func finish(ok: bool) -> void:
	if finished:
		return
	finished = true
	Sfx.play("win" if ok else "close", 0.8)
	var tw := create_tween()
	tw.tween_interval(0.9 if ok else 0.05)
	tw.tween_property(win, "modulate:a", 0.0, 0.2)
	tw.tween_callback(func():
		done.emit(ok)
		queue_free())


func autosolve() -> void:
	finish(true)


func _process(delta: float) -> void:
	if _auto_t > 0.0:
		_auto_t -= delta
		if _auto_t <= 0.0:
			autosolve()
	_tick(delta)


func _tick(_delta: float) -> void:
	pass


func flash_info(text: String, col: Color = UiKit.C_RED) -> void:
	var l := UiKit.label(text, 26, col, true, HORIZONTAL_ALIGNMENT_CENTER)
	l.add_theme_constant_override("outline_size", 8)
	l.add_theme_color_override("font_outline_color", Color(0, 0.05, 0.04))
	body.add_child(l)
	UiKit.place(l, Control.PRESET_CENTER, Vector2(0, -40), Vector2(700, 40))
	var tw := create_tween()
	tw.tween_property(l, "position:y", l.position.y - 30, 1.2)
	tw.parallel().tween_property(l, "modulate:a", 0.0, 1.2).set_delay(0.4)
	tw.tween_callback(l.queue_free)


func shake(c: Control) -> void:
	var x := c.position.x
	var tw := create_tween()
	for i in 4:
		tw.tween_property(c, "position:x", x + (8 if i % 2 == 0 else -8), 0.04)
	tw.tween_property(c, "position:x", x, 0.04)
