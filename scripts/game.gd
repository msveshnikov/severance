extends Node
## Autoload "Game": persistent state, save/load, settings, texts, command-line flags.

signal event(kind: String, id: String)
signal state_changed
signal lang_changed

const SAVE_PATH := "user://save.json"
const SAVE_VERSION := 1
const INNIES := ["mark", "helly", "dylan", "irving"]
const NAMES := {
	"mark": "Mark S.", "helly": "Helly R.", "dylan": "Dylan G.", "irving": "Irving B.",
	"milchick": "Mr. Milchick", "cobel": "Ms. Cobel", "burt": "Burt G.", "casey": "Ms. Casey",
	"graner": "Mr. Graner", "keeper": "Goat Keeper", "kier": "Kier Eagan", "goat": "Goat",
}
const NAMES_RU := {
	"mark": "Марк С.", "helly": "Хелли Р.", "dylan": "Дилан Дж.", "irving": "Ирвинг Б.",
	"milchick": "Мистер Милчик", "cobel": "Миссис Кобел", "burt": "Бёрт Г.", "casey": "Мисс Кейси",
	"graner": "Мистер Грейнер", "keeper": "Смотрительница", "kier": "Кир Иган", "goat": "Козлёнок",
}

var Texts = preload("res://scripts/texts.gd")

# --- state (saved)
var directive := 0            # index into Quests.LIST
var step := 0                 # step inside the directive
var quota := 0.0              # 0..100
var flags := {}               # misc booleans / values
var items := {}               # inventory id -> true
var unlocked := ["mark", "dylan", "irving"]
var active := "mark"
var level := "severed"
var finished := false
var code := ""                # the four digits engraved on Kier's spectacles
var play_time := 0.0

# --- settings (saved)
var lang := "en"
var music_vol := 0.7
var sfx_vol := 0.8
var quality := "auto"         # auto | low | high

# --- runtime
var args := {}
var autotest := false
var is_mobile := false
var is_web := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	is_web = OS.has_feature("web")
	is_mobile = OS.has_feature("mobile") or OS.has_feature("web_android") or OS.has_feature("web_ios")
	_parse_args()
	var os_lang := OS.get_locale_language()
	lang = "ru" if os_lang in ["ru", "uk", "be", "kk"] else "en"
	if not args.has("fresh"):
		load_game()
	if args.has("lang"):
		lang = args["lang"]
	autotest = args.has("autotest")
	if code == "":
		var r := RandomNumberGenerator.new()
		r.randomize()
		code = "%d%d%d%d" % [r.randi_range(1, 9), r.randi_range(0, 9), r.randi_range(0, 9), r.randi_range(0, 9)]


func _process(delta: float) -> void:
	play_time += delta


func _parse_args() -> void:
	var a := OS.get_cmdline_user_args()
	if FileAccess.file_exists("user://cmdline.txt"):
		a = PackedStringArray(FileAccess.get_file_as_string("user://cmdline.txt").strip_edges().split(" ", false))
	var i := 0
	while i < a.size():
		var s: String = a[i]
		if s.begins_with("--"):
			var k := s.substr(2)
			if i + 1 < a.size() and not String(a[i + 1]).begins_with("--"):
				args[k] = a[i + 1]
				i += 1
			else:
				args[k] = true
		i += 1


# ------------------------------------------------------------------ texts
func t(key: String, vars: Dictionary = {}) -> String:
	var d: Dictionary = Texts.RU if lang == "ru" else Texts.EN
	var s: String = d.get(key, Texts.EN.get(key, key))
	for k in vars:
		s = s.replace("{" + str(k) + "}", str(vars[k]))
	return s


func has_text(key: String) -> bool:
	return Texts.EN.has(key)


func lines(key: String) -> Array:
	## Dialogue: Texts.DIALOG[lang][key] -> [[speaker, text], ...]
	var d: Dictionary = Texts.DIALOG_RU if lang == "ru" else Texts.DIALOG_EN
	return d.get(key, Texts.DIALOG_EN.get(key, []))


func char_name(id: String) -> String:
	return (NAMES_RU if lang == "ru" else NAMES).get(id, id)


func set_lang(l: String) -> void:
	lang = l
	save_game()
	lang_changed.emit()


# ------------------------------------------------------------------ state helpers
func emit_event(kind: String, id: String = "") -> void:
	event.emit(kind, id)


func give(item: String) -> void:
	items[item] = true
	state_changed.emit()


func take(item: String) -> void:
	items.erase(item)
	state_changed.emit()


func has(item: String) -> bool:
	return items.get(item, false)


func flag(k: String, default = false):
	return flags.get(k, default)


func set_flag(k: String, v = true) -> void:
	flags[k] = v
	state_changed.emit()


func add_quota(v: float) -> void:
	quota = clampf(quota + v, 0.0, 100.0)
	state_changed.emit()


func unlock(innie: String) -> void:
	if innie not in unlocked:
		unlocked.append(innie)
		state_changed.emit()


func new_game() -> void:
	directive = 0
	step = 0
	quota = 0.0
	flags = {}
	items = {}
	unlocked = ["mark", "dylan", "irving"]
	active = "mark"
	level = "severed"
	finished = false
	code = ""
	var r := RandomNumberGenerator.new()
	r.randomize()
	code = "%d%d%d%d" % [r.randi_range(1, 9), r.randi_range(0, 9), r.randi_range(0, 9), r.randi_range(0, 9)]
	play_time = 0.0
	save_game()


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH) and (directive > 0 or step > 0 or quota > 0.0)


func save_game() -> void:
	if autotest and not args.has("save"):
		return
	var d := {
		"v": SAVE_VERSION, "directive": directive, "step": step, "quota": quota, "flags": flags, "items": items,
		"unlocked": unlocked, "active": active, "level": level, "finished": finished, "code": code,
		"play_time": play_time, "lang": lang, "music_vol": music_vol, "sfx_vol": sfx_vol, "quality": quality,
	}
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(d))


func load_game() -> void:
	if not FileAccess.file_exists(SAVE_PATH):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(d) != TYPE_DICTIONARY:
		return
	directive = int(d.get("directive", 0))
	step = int(d.get("step", 0))
	quota = float(d.get("quota", 0.0))
	flags = d.get("flags", {})
	items = d.get("items", {})
	unlocked = Array(d.get("unlocked", unlocked))
	active = d.get("active", "mark")
	level = d.get("level", "severed")
	finished = d.get("finished", false)
	code = str(d.get("code", ""))
	play_time = float(d.get("play_time", 0.0))
	music_vol = float(d.get("music_vol", music_vol))
	sfx_vol = float(d.get("sfx_vol", sfx_vol))
	quality = d.get("quality", quality)
	if d.has("lang"):
		lang = d["lang"]
	call_deferred("_apply_lang_loaded", d.get("lang", ""))


func _apply_lang_loaded(l: String) -> void:
	if l != "":
		lang = l


func low_quality() -> bool:
	if quality == "low":
		return true
	if quality == "high":
		return false
	return is_web or is_mobile or RenderingServer.get_current_rendering_method() != "forward_plus"
