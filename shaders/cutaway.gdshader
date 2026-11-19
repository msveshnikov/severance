// Walls and tall props: a dithered hole opens around the line of sight to the active innie, so walls between
// the camera and the player melt down to a short stub. Globals are updated by main.gd every frame.
shader_type spatial;
render_mode cull_back;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform vec4 albedo : source_color = vec4(1.0);
uniform bool use_tex = false;
uniform float roughness = 0.8;
uniform float metallic = 0.0;
uniform vec3 emission = vec3(0.0);
uniform float stub_h = 0.42;
uniform float cut_enabled = 1.0;

global uniform vec3 cut_center;
global uniform vec3 cut_dir;
global uniform float cut_radius;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float bayer(vec2 p) {
	ivec2 q = ivec2(mod(p, 4.0));
	int i = q.x + q.y * 4;
	float m[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
	return (m[i] + 0.5) / 16.0;
}

void fragment() {
	vec3 v = wpos - cut_center;
	float along = dot(v, cut_dir);
	float d = length(v - cut_dir * along);
	float k = smoothstep(cut_radius, cut_radius * 0.72, d) * smoothstep(-0.6, 0.4, along) * step(stub_h, wpos.y);
	if (k * cut_enabled > bayer(FRAGCOORD.xy)) {
		discard;
	}
	vec4 c = albedo;
	if (use_tex) {
		c *= texture(albedo_tex, UV);
	}
	ALBEDO = c.rgb;
	ROUGHNESS = roughness;
	METALLIC = metallic;
	EMISSION = emission;
}
