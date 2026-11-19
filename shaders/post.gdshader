// Screen overlay: vignette, faint film grain, colour wash for flashes.
shader_type canvas_item;

uniform float vignette = 0.35;
uniform float grain = 0.035;
uniform vec4 flash : source_color = vec4(1.0, 1.0, 1.0, 0.0);

float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void fragment() {
	vec2 uv = SCREEN_UV;
	float v = smoothstep(0.45, 1.05, length((uv - 0.5) * vec2(1.25, 1.0)) * 1.25);
	float g = (h(uv * 900.0 + fract(TIME * 7.0)) - 0.5) * grain;
	vec4 c = vec4(0.02, 0.05, 0.04, v * vignette);
	c.rgb += g;
	c.a = max(c.a, abs(g));
	c = mix(c, vec4(flash.rgb, 1.0), flash.a);
	COLOR = c;
}
