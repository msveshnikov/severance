extends Minigame
## Music Dance Experience: a four-lane rhythm game to the Defiant Jazz loop. Lanes are the four tempers.
## The window sits on the right so the dancing innies stay visible on the floor behind it.

const BPM := 132.0
const LANES := ["wo", "fc", "dr", "ma"]
const KEYS := [KEY_D, KEY_F, KEY_J, KEY_K]
const TRAVEL := 1.6          # seconds a note takes to fall to the line
const LENGTH_BEATS := 72

var notes := []              # {t, lane, hit}
var lane_ctl: Control
var t0 := 0.0
var now := 0.0
var perfect := 0
var good := 0
var miss := 0
var combo := 0
var judge_lbl: Label
var flashes := [0.0, 0.0, 0.0, 0.0]
var started := false


func _init(a: Dictionary = {}) -> void:
	super(a)
	window_size = Vector2(560, 680)
	dim = false


func _build() -> void:
	title_lbl.text = Game.t("dn_genre")
	exit_btn.visible = false
	var v := VBoxContainer.new()
	UiKit.full(v)
	body.add_child(v)
	v.add_child(UiKit.label(Game.t("dn_hint"), 14, Color(0.85, 0.95, 0.9), true, HORIZONTAL_ALIGNMENT_CENTER))
	lane_ctl = Control.new()
	lane_ctl.size_flags_vertical = Control.SIZE_EXPAND_FILL
	lane_ctl.mouse_filter = Control.MOUSE_FILTER_STOP
	lane_ctl.draw.connect(_draw_lanes)
	lane_ctl.gui_input.connect(_lane_input)
	v.add_child(lane_ctl)
	judge_lbl = UiKit.label("", 26, UiKit.C_GOLD, true, HORIZONTAL_ALIGNMENT_CENTER)
	v.add_child(judge_lbl)
	_make_chart()


func _layout() -> void:
	var w := minf(size.x * 0.46, window_size.x)
	var h := minf(size.y - 24, window_size.y)
	UiKit.place(win, Control.PRESET_CENTER_RIGHT, Vector2(-16, 0), Vector2(w, h))
	win.pivot_offset = win.size / 2


func _make_chart() -> void:
	var beat := 60.0 / BPM
	var r := RandomNumberGenerator.new()
	r.seed = 77
	var lane := 0
	for b in range(4, LENGTH_BEATS):
		var bar_pos := b % 8
		var t := b * beat
		# swing-ish pattern: on-beats always, some off-beats in the busier half
		if bar_pos != 7:
			lane = (lane + r.randi_range(1, 3)) % 4
			notes.append({"t": t, "lane": lane, "hit": false})
		if b > 24 and (bar_pos == 2 or bar_pos == 5) and r.randf() < 0.7:
			notes.append({"t": t + beat * 0.66, "lane": (lane + 2) % 4, "hit": false})
		if b > 48 and bar_pos == 0:
			notes.append({"t": t, "lane": (lane + 1) % 4, "hit": false})


func _tick(delta: float) -> void:
	if not started:
		started = true
		Sfx.music("jazz", 0.2)
		t0 = Time.get_ticks_msec() / 1000.0
	var mp := Sfx.music_pos()
	now = mp if mp > 0.0 else Time.get_ticks_msec() / 1000.0 - t0
	for n in notes:
		if not n["hit"] and now - n["t"] > 0.18:
			n["hit"] = true
			miss += 1
			combo = 0
			_judge(Game.t("dn_miss"), UiKit.C_RED)
	for i in 4:
		flashes[i] = maxf(0.0, flashes[i] - delta * 4.0)
	var total := notes.size()
	var score := int(100.0 * (perfect + good * 0.6) / maxf(total, 1))
	info_lbl.text = Game.t("dn_score", {"n": score}) + ("  x%d" % combo if combo > 3 else "") + "   "
	if not finished and now > notes[-1]["t"] + 1.0:
		if score >= 55 or Game.autotest:
			finish(true)
		else:
			flash_info(Game.t("dn_retry"))
			for n in notes:
				n["hit"] = false
			perfect = 0
			good = 0
			miss = 0
			t0 = Time.get_ticks_msec() / 1000.0
			Sfx.music("", 0.1)
			started = false
	lane_ctl.queue_redraw()


func hit(lane: int) -> void:
	flashes[lane] = 1.0
	var best = null
	var bd := 1e9
	for n in notes:
		if n["hit"] or n["lane"] != lane:
			continue
		var d := absf(n["t"] - now)
		if d < bd:
			bd = d
			best = n
	if best == null or bd > 0.2:
		Sfx.play("tick", 0.3)
		return
	best["hit"] = true
	if bd < 0.08:
		perfect += 1
		combo += 1
		_judge(Game.t("dn_perfect"), UiKit.C_TEAL)
	else:
		good += 1
		combo += 1
		_judge(Game.t("dn_good"), UiKit.C_GOLD)
	Sfx.play("hit", 0.5, 1.0 + lane * 0.12)


func _judge(s: String, c: Color) -> void:
	judge_lbl.text = s
	judge_lbl.add_theme_color_override("font_color", c)


func _lane_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		hit(clampi(int(e.position.x / lane_ctl.size.x * 4.0), 0, 3))
	elif e is InputEventScreenTouch and e.pressed:
		hit(clampi(int(e.position.x / lane_ctl.size.x * 4.0), 0, 3))


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo:
		var i := KEYS.find(e.keycode)
		if i < 0:
			i = [KEY_LEFT, KEY_DOWN, KEY_UP, KEY_RIGHT].find(e.keycode)
		if i >= 0:
			hit(i)


func _draw_lanes() -> void:
	var s := lane_ctl.size
	var lw := s.x / 4.0
	var line_y := s.y - 70.0
	for i in 4:
		var col: Color = UiKit.TEMPER_COL[LANES[i]]
		lane_ctl.draw_rect(Rect2(i * lw + 3, 0, lw - 6, s.y), Color(col.r, col.g, col.b, 0.06 + 0.25 * flashes[i]), true)
		lane_ctl.draw_circle(Vector2(i * lw + lw / 2, line_y), lw * 0.32, Color(col.r, col.g, col.b, 0.25 + 0.6 * flashes[i]))
		lane_ctl.draw_arc(Vector2(i * lw + lw / 2, line_y), lw * 0.32, 0, TAU, 32, col, 3.0, true)
		var lab := Game.t("bin_" + LANES[i])
		var fs := 15
		var tw := UiKit.MONO.get_string_size(lab, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		lane_ctl.draw_string(UiKit.MONO, Vector2(i * lw + (lw - tw) / 2, s.y - 22), lab, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, col)
		var k: String = ["D", "F", "J", "K"][i]
		lane_ctl.draw_string(UiKit.MONO, Vector2(i * lw + lw / 2 - 6, line_y + 7), k, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(0, 0, 0, 0.6))
	lane_ctl.draw_line(Vector2(0, line_y), Vector2(s.x, line_y), Color(1, 1, 1, 0.3), 2.0)
	for n in notes:
		if n["hit"]:
			continue
		var dt: float = n["t"] - now
		if dt > TRAVEL or dt < -0.2:
			continue
		var y := line_y - dt / TRAVEL * line_y
		var i: int = n["lane"]
		var col: Color = UiKit.TEMPER_COL[LANES[i]]
		var c := Vector2(i * lw + lw / 2, y)
		lane_ctl.draw_circle(c, lw * 0.26, col)
		lane_ctl.draw_circle(c, lw * 0.15, Color(1, 1, 1, 0.8))


func autosolve() -> void:
	finish(true)
