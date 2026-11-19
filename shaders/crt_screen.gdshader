// Lumon terminal screens: rows of drifting digits on a teal CRT with scanlines and a soft glow.
shader_type spatial;
render_mode unshaded;

uniform sampler2D digits : source_color, filter_linear;
uniform vec3 tint : source_color = vec3(0.45, 0.95, 0.82);
uniform float cols = 14.0;
uniform float rows = 9.0;
uniform float seed = 0.0;
uniform float energy = 1.0;

float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void fragment() {
	vec2 uv = vec2(UV.x, 1.0 - UV.y);
	vec2 g = uv * vec2(cols, rows);
	vec2 cell = floor(g);
	vec2 f = fract(g);
	float t = TIME * 0.6 + seed * 10.0;
	float n = floor(h(cell + seed) * 10.0 + floor(t * (0.3 + h(cell * 1.7)) ) );
	float d = mod(n, 10.0);
	float wob = 0.06 * sin(TIME * 3.0 + h(cell) * 6.28);
	vec2 duv = vec2((d + clamp((f.x - 0.5) * 1.15 + 0.5, 0.0, 1.0)) / 10.0, clamp(f.y + wob, 0.0, 1.0));
	float a = texture(digits, duv).a;
	float scary = step(0.93, h(cell + floor(TIME * 0.2)));
	vec3 col = tint * (0.08 + a * (0.75 + 0.5 * scary));
	col *= 0.85 + 0.15 * sin(uv.y * 400.0);
	float vig = smoothstep(0.75, 0.2, length(uv - 0.5));
	ALBEDO = col * (0.4 + 0.6 * vig) * energy;
}
