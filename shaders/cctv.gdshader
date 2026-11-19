// Security monitors: grainy grey-blue camera feeds with rolling bars.
shader_type spatial;
render_mode unshaded;

uniform float seed = 0.0;
uniform float blackout = 0.0;

float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void fragment() {
	vec2 uv = vec2(UV.x, 1.0 - UV.y);
	float t = TIME;
	// a fake corridor in perspective
	float corridor = smoothstep(0.02, 0.0, abs(abs(uv.x - 0.5) - (0.12 + uv.y * 0.35)));
	float floorline = step(0.62, uv.y) * 0.25;
	float figure = smoothstep(0.03, 0.0, length((uv - vec2(0.5 + 0.25 * sin(t * 0.3 + seed * 3.0), 0.55)) * vec2(3.0, 1.0)) - 0.05);
	float g = h(uv * 300.0 + t);
	float bar = 0.1 * smoothstep(0.0, 0.05, abs(fract(uv.y * 1.0 - t * 0.2 + seed) - 0.5));
	vec3 col = vec3(0.35, 0.45, 0.55) * (0.35 + corridor * 0.5 + floorline + figure * 0.6 + g * 0.18 - bar);
	float rec = step(length(uv - vec2(0.9, 0.1)), 0.03) * step(0.5, fract(t));
	col += vec3(0.9, 0.1, 0.1) * rec;
	col = mix(col, vec3(h(uv * 200.0 + t * 3.0)) * 0.3, blackout);
	ALBEDO = col;
}
