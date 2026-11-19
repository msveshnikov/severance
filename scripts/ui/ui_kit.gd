extends RefCounted
class_name UiKit
## Shared look: Lumon off-white panels with a thin navy rule, teal CRT accents, Rubik for UI, DejaVu Mono for CRT.

const FONT := preload("res://assets/fonts/Rubik-Variable.ttf")
const MONO := preload("res://assets/fonts/DejaVuSansMono-Bold.ttf")
const C_BG := Color(0.043, 0.082, 0.071)
const C_PANEL := Color(0.93, 0.94, 0.91, 0.96)
const C_INK := Color(0.11, 0.18, 0.2)
const C_NAVY := Color(0.12, 0.23, 0.37)
const C_TEAL := Color(0.45, 0.95, 0.82)
const C_CRT := Color(0.03, 0.09, 0.08, 0.97)
const C_RED := Color(0.85, 0.22, 0.2)
const C_GOLD := Color(0.86, 0.68, 0.3)
const TEMPER_COL := {"wo": Color(0.45, 0.62, 0.95), "fc": Color(0.98, 0.85, 0.35), "dr": Color(0.55, 0.9, 0.55),
	"ma": Color(0.98, 0.42, 0.38)}


static func sb(col: Color, radius: int = 10, border: int = 0, bcol: Color = Color.TRANSPARENT, pad: int = 12) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = col
	s.set_corner_radius_all(radius)
	s.set_border_width_all(border)
	s.border_color = bcol
	s.content_margin_left = pad
	s.content_margin_right = pad
	s.content_margin_top = pad * 0.6
	s.content_margin_bottom = pad * 0.6
	s.anti_aliasing = true
	return s


static func label(text: String, size: int = 22, col: Color = C_INK, mono: bool = false, align: int = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", MONO if mono else FONT)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


static func button(text: String, size: int = 24, primary: bool = true, mono: bool = false) -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_override("font", MONO if mono else FONT)
	b.add_theme_font_size_override("font_size", size)
	var base := C_NAVY if primary else Color(0.85, 0.87, 0.84)
	var fg := Color(0.95, 0.97, 0.95) if primary else C_INK
	b.add_theme_stylebox_override("normal", sb(base, 10, 2, base.darkened(0.25), 18))
	b.add_theme_stylebox_override("hover", sb(base.lightened(0.12), 10, 2, C_TEAL, 18))
	b.add_theme_stylebox_override("pressed", sb(base.darkened(0.15), 10, 2, C_TEAL, 18))
	b.add_theme_stylebox_override("focus", sb(base.lightened(0.12), 10, 2, C_TEAL, 18))
	b.add_theme_stylebox_override("disabled", sb(base.darkened(0.4), 10, 0, Color.TRANSPARENT, 18))
	for k in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(k, fg)
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(func(): Sfx.play("click", 0.7))
	return b


static func crt_button(text: String, size: int = 22, col: Color = C_TEAL) -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_override("font", MONO)
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_stylebox_override("normal", sb(Color(col.r, col.g, col.b, 0.08), 4, 2, col, 14))
	b.add_theme_stylebox_override("hover", sb(Color(col.r, col.g, col.b, 0.22), 4, 2, col, 14))
	b.add_theme_stylebox_override("pressed", sb(Color(col.r, col.g, col.b, 0.4), 4, 2, col, 14))
	b.add_theme_stylebox_override("focus", sb(Color(col.r, col.g, col.b, 0.22), 4, 2, col, 14))
	for k in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(k, col)
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(func(): Sfx.play("beep", 0.5))
	return b


static func panel(col: Color = C_PANEL, radius: int = 14, border: int = 2, bcol: Color = C_NAVY) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", sb(col, radius, border, bcol, 16))
	return p


static func full(c: Control) -> void:
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


static func place(c: Control, preset: int, offset: Vector2 = Vector2.ZERO, size: Vector2 = Vector2.ZERO) -> void:
	## anchor to a corner/edge and set offsets relative to it (never .position: see godot-ui gotchas)
	c.set_anchors_preset(preset)
	var ax := c.anchor_left
	var ay := c.anchor_top
	var sz := size if size != Vector2.ZERO else c.get_combined_minimum_size()
	var x0 := offset.x - sz.x * ax
	var y0 := offset.y - sz.y * ay
	c.offset_left = x0
	c.offset_top = y0
	c.offset_right = x0 + sz.x
	c.offset_bottom = y0 + sz.y


static func portrait(id: String, size: int = 72) -> TextureRect:
	var t := TextureRect.new()
	var p := "res://assets/ui/portrait_%s.png" % id
	if ResourceLoader.exists(p):
		t.texture = load(p)
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	t.custom_minimum_size = Vector2(size, size)
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return t


static func slider(v: float) -> HSlider:
	var s := HSlider.new()
	s.min_value = 0.0
	s.max_value = 1.0
	s.step = 0.05
	s.value = v
	s.custom_minimum_size = Vector2(260, 32)
	s.focus_mode = Control.FOCUS_NONE
	return s
