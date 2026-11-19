extends Control
class_name DialogBox
## Bottom dialogue panel: portrait, name, typewriter text, optional choices. Lines are [speaker, text];
## speaker "?" = choices "A|B", "" = a full-screen narration card.

signal finished
signal line_started(speaker: String)

var lines: Array = []
var idx := -1
var panel: PanelContainer
var portrait: TextureRect
var name_lbl: Label
var text_lbl: RichTextLabel
var choices: HBoxContainer
var cont_lbl: Label
var card: ColorRect
var card_lbl: Label
var _typing := 0.0
var _full := 0
var _vars := {}
var active := false
var _auto := 0.0


func _ready() -> void:
	UiKit.full(self)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false
	card = ColorRect.new()
	card.color = Color(0.02, 0.05, 0.04, 0.92)
	UiKit.full(card)
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(card)
	card_lbl = UiKit.label("", 40, Color(0.92, 0.96, 0.94), true, HORIZONTAL_ALIGNMENT_CENTER)
	card_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	card_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	UiKit.full(card_lbl)
	card.add_child(card_lbl)
	panel = UiKit.panel(Color(0.95, 0.96, 0.93, 0.97), 16, 3, UiKit.C_NAVY)
	add_child(panel)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 14)
	panel.add_child(h)
	var pf := PanelContainer.new()
	pf.add_theme_stylebox_override("panel", UiKit.sb(Color(0.12, 0.2, 0.22), 12, 0, Color.TRANSPARENT, 0))
	portrait = UiKit.portrait("mark", 128)
	pf.add_child(portrait)
	h.add_child(pf)
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_lbl = UiKit.label("", 22, UiKit.C_NAVY, true)
	v.add_child(name_lbl)
	text_lbl = RichTextLabel.new()
	text_lbl.bbcode_enabled = false
	text_lbl.fit_content = true
	text_lbl.scroll_active = false
	text_lbl.add_theme_font_override("normal_font", UiKit.FONT)
	text_lbl.add_theme_font_size_override("normal_font_size", 24)
	text_lbl.add_theme_color_override("default_color", UiKit.C_INK)
	text_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(text_lbl)
	choices = HBoxContainer.new()
	choices.add_theme_constant_override("separation", 12)
	v.add_child(choices)
	cont_lbl = UiKit.label("▼", 16, UiKit.C_NAVY, false, HORIZONTAL_ALIGNMENT_RIGHT)
	cont_lbl.text = ">>"
	v.add_child(cont_lbl)
	h.add_child(v)
	resized.connect(_layout)
	_layout()


func _layout() -> void:
	var w := minf(size.x - 40, 1000)
	UiKit.place(panel, Control.PRESET_CENTER_BOTTOM, Vector2(0, -16), Vector2(w, 190))


func play(l: Array, vars: Dictionary = {}) -> void:
	lines = l
	_vars = vars
	idx = -1
	active = true
	visible = true
	_next()


func _next() -> void:
	idx += 1
	for c in choices.get_children():
		c.queue_free()
	if idx >= lines.size():
		active = false
		visible = false
		finished.emit()
		return
	var sp: String = lines[idx][0]
	var tx: String = lines[idx][1]
	for k in _vars:
		tx = tx.replace("{" + str(k) + "}", str(_vars[k]))
	if sp == "":
		card.visible = true
		panel.visible = false
		card_lbl.text = tx
		card_lbl.modulate.a = 0
		create_tween().tween_property(card_lbl, "modulate:a", 1.0, 0.6)
		Sfx.play("chime", 0.8)
		_auto = 3.2 if Game.autotest else 0.0
		return
	card.visible = false
	panel.visible = true
	if sp == "?":
		var who: String = Game.active
		_show_speaker(who)
		text_lbl.text = ""
		cont_lbl.visible = false
		for opt in tx.split("|"):
			var b := UiKit.button(opt, 20, true)
			b.pressed.connect(func():
				_show_speaker(who)
				_type(opt)
				for c in choices.get_children():
					c.queue_free()
				cont_lbl.visible = true)
			choices.add_child(b)
		if Game.autotest:
			_auto = 0.3
		return
	cont_lbl.visible = true
	_show_speaker(sp)
	_type(tx)
	line_started.emit(sp)
	Sfx.play("blip_" + ("lo" if sp in ["milchick", "burt", "graner", "irving", "mark", "kier"] else "hi"), 0.5)
	if Game.autotest:
		_auto = 0.25


func _show_speaker(sp: String) -> void:
	name_lbl.text = Game.char_name(sp).to_upper()
	var p := "res://assets/ui/portrait_%s.png" % sp
	portrait.texture = load(p) if ResourceLoader.exists(p) else null


func _type(tx: String) -> void:
	text_lbl.text = tx
	text_lbl.visible_characters = 0
	_full = tx.length()
	_typing = 0.0


func _process(delta: float) -> void:
	if not active:
		return
	if text_lbl.visible_characters >= 0 and text_lbl.visible_characters < _full:
		_typing += delta * 55.0
		text_lbl.visible_characters = int(_typing)
		if text_lbl.visible_characters >= _full:
			text_lbl.visible_characters = -1
	if _auto > 0.0:
		_auto -= delta
		if _auto <= 0.0:
			if choices.get_child_count() > 0 and not choices.get_child(0).is_queued_for_deletion():
				(choices.get_child(0) as Button).pressed.emit()
			else:
				advance()
			if active and _auto <= 0.0:
				_auto = 0.3


func advance() -> void:
	if not active:
		return
	if choices.get_child_count() > 0 and not choices.get_child(0).is_queued_for_deletion():
		return
	if text_lbl.visible_characters != -1 and text_lbl.visible_characters < _full and not card.visible:
		text_lbl.visible_characters = -1
		return
	_next()


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		advance()
		accept_event()


func _unhandled_input(e: InputEvent) -> void:
	if active and e is InputEventKey and e.pressed and not e.echo and e.keycode in [KEY_SPACE, KEY_ENTER, KEY_E, KEY_KP_ENTER]:
		advance()
		get_viewport().set_input_as_handled()
