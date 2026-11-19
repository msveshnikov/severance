extends Node
## Autoload "Sfx": one-shot sounds (pooled players) and cross-faded music / ambience loops.

const DIR := "res://assets/audio/"
var _cache := {}
var _pool: Array[AudioStreamPlayer] = []
var _music: Array[AudioStreamPlayer] = []
var _cur := 0
var _music_name := ""
var _amb: AudioStreamPlayer
var _amb_name := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in 14:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		_pool.append(p)
	for i in 2:
		var m := AudioStreamPlayer.new()
		add_child(m)
		_music.append(m)
	_amb = AudioStreamPlayer.new()
	add_child(_amb)


func _stream(n: String) -> AudioStream:
	if _cache.has(n):
		return _cache[n]
	var s: AudioStream = null
	for ext in [".wav", ".ogg", ".mp3"]:
		if ResourceLoader.exists(DIR + n + ext):
			s = load(DIR + n + ext)
			break
	_cache[n] = s
	return s


func play(n: String, vol: float = 1.0, pitch: float = 1.0) -> void:
	var s := _stream(n)
	if s == null or Game.sfx_vol <= 0.001:
		return
	for p in _pool:
		if not p.playing:
			p.stream = s
			p.volume_db = linear_to_db(maxf(vol * Game.sfx_vol, 0.0001))
			p.pitch_scale = pitch
			p.play()
			return


func music(n: String, fade: float = 1.5) -> void:
	if n == _music_name:
		return
	_music_name = n
	var old := _music[_cur]
	_cur = 1 - _cur
	var nw := _music[_cur]
	var s := _stream(n) if n != "" else null
	if old.playing:
		var tw := create_tween()
		tw.tween_property(old, "volume_db", -60.0, fade)
		tw.tween_callback(old.stop)
	if s:
		_set_loop(s)
		nw.stream = s
		nw.volume_db = -60.0
		nw.play()
		var tw2 := create_tween()
		tw2.tween_property(nw, "volume_db", linear_to_db(maxf(Game.music_vol * 0.8, 0.0001)), fade)


func ambience(n: String) -> void:
	if n == _amb_name:
		return
	_amb_name = n
	var s := _stream(n) if n != "" else null
	if s == null:
		_amb.stop()
		return
	_set_loop(s)
	_amb.stream = s
	_amb.volume_db = linear_to_db(maxf(Game.sfx_vol * 0.35, 0.0001))
	_amb.play()


func music_pos() -> float:
	var m := _music[_cur]
	return m.get_playback_position() if m.playing else 0.0


func refresh_volumes() -> void:
	_music[_cur].volume_db = linear_to_db(maxf(Game.music_vol * 0.8, 0.0001))
	_amb.volume_db = linear_to_db(maxf(Game.sfx_vol * 0.35, 0.0001))


func _set_loop(s: AudioStream) -> void:
	if s is AudioStreamWAV:
		var w := s as AudioStreamWAV
		if w.loop_mode == AudioStreamWAV.LOOP_DISABLED:
			w.loop_mode = AudioStreamWAV.LOOP_FORWARD
			w.loop_begin = 0
			w.loop_end = int(w.get_length() * w.mix_rate)
	elif s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	elif s is AudioStreamMP3:
		(s as AudioStreamMP3).loop = true
