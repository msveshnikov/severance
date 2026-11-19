extends Node3D
class_name Actor
## A character on the floor: glTF model + AnimationPlayer, path following on the level grid, sitting,
## one-shot actions, a blob shadow, the selection ring (for the active innie) and a speech bubble.

signal arrived

const BLOB := preload("res://assets/ui/blob.png")
const SPEEDS := {"walk": 0.993, "run": 2.274, "sneak": 0.696}   # assets/characters/anim_speeds.json

var id := ""
var level: Level
var model: Node3D
var anim: AnimationPlayer
var path := PackedVector3Array()
var speed := 3.4
var move_anim := "run"
var idle_anim := "idle"
var seated := false
var busy := false              # in a minigame / dialogue / holding a lever
var yaw_target := 0.0
var is_innie := false
var ring: MeshInstance3D
var bubble: Label3D
var _bubble_t := 0.0
var _cur_anim := ""
var _step_t := 0.0
var _stand_before_sit := Vector3.ZERO
var held: Node3D


func setup(char_id: String, lvl: Level) -> void:
	id = char_id
	level = lvl
	is_innie = char_id in Game.INNIES
	model = load("res://assets/characters/%s.gltf" % char_id).instantiate()
	add_child(model)
	anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if anim:
		for a in anim.get_animation_list():
			var an := anim.get_animation(a)
			if an:
				an.loop_mode = Animation.LOOP_LINEAR
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	# blob shadow
	var sh := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(0.9, 0.9) if char_id != "goat" else Vector2(0.6, 0.7)
	q.orientation = PlaneMesh.FACE_Y
	sh.mesh = q
	var sm := StandardMaterial3D.new()
	sm.albedo_texture = BLOB
	sm.albedo_color = Color(0, 0, 0, 0.55)
	sm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sh.material_override = sm
	sh.position.y = 0.012
	sh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sh)
	# selection ring (active innie)
	ring = MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.42
	tm.outer_radius = 0.5
	tm.rings = 24
	tm.ring_segments = 6
	ring.mesh = tm
	var rm := StandardMaterial3D.new()
	rm.albedo_color = Color(0.55, 0.95, 0.8, 0.85)
	rm.emission_enabled = true
	rm.emission = Color(0.35, 0.95, 0.75)
	rm.emission_energy_multiplier = 1.5
	rm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring.material_override = rm
	ring.scale = Vector3(1, 0.05, 1)
	ring.position.y = 0.03
	ring.visible = false
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ring)
	# speech bubble
	bubble = Label3D.new()
	bubble.font = preload("res://assets/fonts/Rubik-Variable.ttf")
	bubble.font_size = 44
	bubble.outline_size = 10
	bubble.pixel_size = 0.005
	bubble.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	bubble.no_depth_test = true
	bubble.modulate = Color(1, 1, 1)
	bubble.outline_modulate = Color(0.05, 0.12, 0.1)
	bubble.position.y = 2.25 if char_id != "goat" else 0.95
	bubble.visible = false
	bubble.width = 600
	bubble.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(bubble)
	play(idle_anim)


func head_pos() -> Vector3:
	return global_position + Vector3(0, 1.85 if id != "goat" else 0.7, 0)


func play(a: String, blend: float = 0.18, spd: float = 1.0) -> void:
	if anim == null:
		return
	if not anim.has_animation(a):
		a = "idle" if anim.has_animation("idle") else anim.get_animation_list()[0]
	if a == _cur_anim:
		anim.speed_scale = spd
		return
	_cur_anim = a
	anim.play(a, blend)
	anim.speed_scale = spd


func say(text: String, dur: float = 2.5, col: Color = Color.WHITE) -> void:
	bubble.text = text
	bubble.modulate = col
	bubble.visible = true
	_bubble_t = dur


func set_active(on: bool) -> void:
	ring.visible = on


func walk_to(target: Vector3, run: bool = true) -> void:
	if seated:
		stand_up()
	path = level.find_path(global_position, target)
	move_anim = "run" if run else "walk"
	speed = 3.4 if run else 1.5
	if Game.flag("sneaking") and is_innie:
		move_anim = "sneak"
		speed = 1.6


func walk_route(pts: PackedVector3Array, walk_speed: float = 1.4) -> void:
	path = pts
	move_anim = "walk"
	speed = walk_speed


func stop() -> void:
	path = PackedVector3Array()


func moving() -> bool:
	return path.size() > 0


func face(p: Vector3) -> void:
	var d := p - global_position
	if Vector2(d.x, d.z).length() > 0.01:
		yaw_target = atan2(d.x, d.z)


func sit(pos: Vector3, yaw: float, a: String = "sit") -> void:
	if not seated:
		_stand_before_sit = global_position
	seated = true
	path = PackedVector3Array()
	var back := Vector3(sin(yaw), 0, cos(yaw)) * -0.08
	var tw := create_tween()
	tw.tween_property(self, "global_position", pos + back + Vector3(0, 0.1, 0), 0.25)
	rotation.y = yaw
	yaw_target = yaw
	play(a, 0.25)


func stand_up() -> void:
	if not seated:
		return
	seated = false
	global_position = level.nearest_walkable(_stand_before_sit if _stand_before_sit != Vector3.ZERO else global_position)
	play(idle_anim)


func _process(delta: float) -> void:
	if _bubble_t > 0.0:
		_bubble_t -= delta
		if _bubble_t <= 0.0:
			bubble.visible = false
	if ring.visible:
		var s := 1.0 + 0.06 * sin(Time.get_ticks_msec() * 0.006)
		ring.scale = Vector3(s, 0.05, s)
	if path.size() > 0 and not seated:
		var tgt := path[0]
		var d := Vector3(tgt.x - global_position.x, 0, tgt.z - global_position.z)
		var step := speed * delta
		if d.length() <= step:
			global_position = Vector3(tgt.x, 0, tgt.z)
			path.remove_at(0)
			if path.size() == 0:
				play(idle_anim)
				arrived.emit()
		else:
			global_position += d.normalized() * step
			yaw_target = atan2(d.x, d.z)
			var ref: float = SPEEDS.get(move_anim, 1.0)
			play(move_anim, 0.15, clampf(speed / ref, 0.4, 2.2))
			_step_t -= delta * speed
			if _step_t <= 0.0 and is_innie and Game.active == id:
				_step_t = 0.75 if move_anim == "run" else 0.9
				Sfx.play("step", 0.35, randf_range(0.9, 1.1))
	rotation.y = lerp_angle(rotation.y, yaw_target, clampf(delta * 12.0, 0.0, 1.0))


func push(dir: Vector3, delta: float) -> void:
	## direct (WASD / stick) movement with grid collision and wall sliding
	if seated:
		stand_up()
	path = PackedVector3Array()
	var sp := 3.4
	var a := "run"
	if Game.flag("sneaking"):
		sp = 1.6
		a = "sneak"
	var mv := dir * sp * delta
	var p := global_position
	var r := 0.22
	var nx := p + Vector3(mv.x, 0, 0)
	if level.walkable_pos(nx + Vector3(sign(mv.x) * r, 0, 0)) and level.walkable_pos(nx + Vector3(sign(mv.x) * r, 0, r * 0.8)) \
			and level.walkable_pos(nx + Vector3(sign(mv.x) * r, 0, -r * 0.8)):
		p = nx
	var nz := p + Vector3(0, 0, mv.z)
	if level.walkable_pos(nz + Vector3(0, 0, sign(mv.z) * r)) and level.walkable_pos(nz + Vector3(r * 0.8, 0, sign(mv.z) * r)) \
			and level.walkable_pos(nz + Vector3(-r * 0.8, 0, sign(mv.z) * r)):
		p = nz
	global_position = p
	yaw_target = atan2(dir.x, dir.z)
	play(a, 0.15, sp / SPEEDS.get(a, 1.0) * 0.9)
	_step_t -= delta * sp
	if _step_t <= 0.0:
		_step_t = 0.75
		Sfx.play("step", 0.35, randf_range(0.9, 1.1))


func hold_item(asset: String) -> void:
	drop_item()
	var ps := level.prop_scene(asset)
	if ps == null:
		return
	held = ps.instantiate()
	held.position = Vector3(0.0, 1.05, 0.28)
	held.rotation.x = -1.2
	add_child(held)


func drop_item() -> void:
	if held and is_instance_valid(held):
		held.queue_free()
	held = null
