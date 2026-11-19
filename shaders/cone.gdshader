// Patrol vision cone on the floor.
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, blend_mix;

uniform vec4 color : source_color = vec4(1.0, 0.2, 0.15, 0.35);
uniform float alert = 0.0;

void fragment() {
	float r = UV.x;
	float a = color.a * (1.0 - r * 0.7) * (0.8 + 0.2 * sin(TIME * 6.0 - r * 12.0));
	ALBEDO = mix(color.rgb, vec3(1.0, 0.0, 0.0), alert);
	ALPHA = a * (1.0 + alert);
}
