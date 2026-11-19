extends RefCounted
## The 18 directives. Step kinds:
##   talk    who=<actor>           tap the actor with the right innie -> dialogue `dlg` -> done
##   use     id=<interactable>     use it -> optional dialogue `dlg`, minigame `mg` (+mg_args), item `give`
##   collect ids=[...]             pick up every marked item (Petey's map pieces)
##   level   id=<interactable> to=<level>   ride an elevator
##   otc                           both OTC switches held at once
## Directive keys: who (required innie, "" = any), act, steps, start (setup tag for Story.apply_world),
## quota (+% on completion), unlock (innie), done (dialogue after completion), take (item removed at the end).

const LIST := [
	# ---------------------------------------------------------------- ACT I
	{"who": "mark", "act": 1, "steps": [{"k": "talk", "who": "helly", "dlg": "d0_helly"}], "unlock": "helly"},
	{"who": "mark", "act": 1, "steps": [{"k": "use", "id": "term_mark", "mg": "mdr", "mg_args": {"file": 0}}],
		"quota": 10, "done": "d1_done"},
	{"who": "helly", "act": 1, "start": "milchick_hall", "steps": [
		{"k": "talk", "who": "milchick", "dlg": "d2_milchick"},
		{"k": "use", "id": "seat_break", "mg": "compunction"}], "quota": 5, "done": "d2_done"},
	{"who": "irving", "act": 1, "start": "open_od", "steps": [
		{"k": "talk", "who": "burt", "dlg": "d3_burt"},
		{"k": "use", "id": "burt_desk", "give": "gift", "label": "i_gift"},
		{"k": "use", "id": "term_irving", "label": "i_place_gift", "take": "gift"}], "quota": 5, "done": "d3_done",
		"after": "gift_placed"},
	{"who": "dylan", "act": 1, "steps": [{"k": "use", "id": "term_dylan", "mg": "mdr", "mg_args": {"file": 1, "time": 120}}],
		"quota": 10, "done": "d4_done", "reward": "trap"},
	# ---------------------------------------------------------------- ACT II
	{"who": "mark", "act": 2, "steps": [{"k": "use", "id": "stall", "dlg": "d5_book", "give": "book"}], "quota": 2},
	{"who": "helly", "act": 2, "start": "stealth", "steps": [{"k": "talk", "who": "burt", "dlg": ""}], "quota": 6,
		"done": "d6_done", "take": "book"},
	{"who": "dylan", "act": 2, "start": "map_pieces", "steps": [
		{"k": "collect", "ids": ["map1", "map2", "map3", "map4"]},
		{"k": "use", "id": "mdr_cabinet", "label": "i_cabinet"}], "quota": 6, "done": "d7_done"},
	{"who": "irving", "act": 2, "steps": [
		{"k": "talk", "who": "casey", "dlg": "d8_casey"},
		{"k": "use", "id": "seat_wellness", "mg": "wellness"}], "quota": 6, "done": "d8_done"},
	{"who": "mark", "act": 2, "steps": [
		{"k": "use", "id": "kier_wax", "dlg": "d9_kier"},
		{"k": "use", "id": "display_case", "dlg": "d9_case"}], "quota": 5},
	# ---------------------------------------------------------------- ACT III
	{"who": "dylan", "act": 3, "start": "graner_sleeps", "steps": [{"k": "use", "id": "keycard", "give": "keycard"}],
		"quota": 5, "done": "d10_done"},
	{"who": "dylan", "act": 3, "steps": [{"k": "use", "id": "printer", "mg": "printer"}], "quota": 5, "done": "d11_done"},
	{"who": "", "act": 3, "start": "open_red", "steps": [{"k": "level", "id": "red_elevator", "to": "testing"}],
		"quota": 2, "done": "d12_arrive"},
	{"who": "helly", "act": 3, "steps": [
		{"k": "talk", "who": "keeper", "dlg": "d13_keeper"},
		{"k": "use", "id": "milk", "give": "milk"},
		{"k": "use", "id": "trough", "mg": "goats", "label": "i_goat"}], "quota": 6, "done": "d13_done", "take": "milk"},
	{"who": "irving", "act": 3, "steps": [
		{"k": "use", "id": "cryo_keypad", "mg": "keypad"},
		{"k": "use", "id": "cryo_pod", "dlg": "d14_pod"}], "quota": 5},
	{"who": "dylan", "act": 3, "steps": [
		{"k": "use", "id": "otc_door", "label": "i_otc_door"},
		{"k": "otc"}], "quota": 6, "done": "d15_done", "after_level": "severed"},
	# ---------------------------------------------------------------- FINALE
	{"who": "mark", "act": 4, "steps": [{"k": "use", "id": "term_mark", "mg": "mdr", "mg_args": {"file": 2, "final": true}}],
		"quota": 100, "done": "d16_done"},
	{"who": "", "act": 4, "start": "mde", "steps": [
		{"k": "dance"},
		{"k": "use", "id": "waffle_table", "dlg": "d17_end"}], "done": ""},
]

## interactable id -> label key (for props that are interactable at all; quest steps may override)
const LABELS := {
	"term_mark": "i_term", "term_helly": "i_term", "term_dylan": "i_term", "term_irving": "i_term",
	"stall": "i_stall", "kier_wax": "i_kier", "display_case": "i_case", "keycard": "i_keycard", "printer": "i_printer",
	"red_elevator": "i_red_elevator", "red_elevator_up": "i_red_elevator", "milk": "i_milk", "trough": "i_goat",
	"cryo_keypad": "i_keypad", "cryo_pod": "i_pod", "otc_a": "i_switch", "otc_b": "i_switch", "seat_break": "i_sit",
	"seat_wellness": "i_sit", "mdr_cabinet": "i_cabinet", "burt_desk": "i_gift", "waffle_table": "i_waffles",
	"mdr_board": "i_board", "elevator_main": "i_elevator", "coffee": "i_coffee", "vending": "i_vending",
	"fireplace": "i_fireplace", "tent": "i_tent", "cctv": "i_cctv", "cobel_desk": "i_cobel_desk", "otc_door": "i_otc_door",
}

## always-usable flavour interactables -> dialogue key
const FLAVOUR := {
	"coffee": "coffee", "vending": "vending", "fireplace": "fireplace", "cctv": "cctv", "tent": "tent",
	"cobel_desk": "cobel_desk", "mdr_board": "board", "elevator_main": "elevator",
}

const FILES := ["Cold Harbor", "Allentown", "Siena", "Tumwater", "Dranesville", "Labrador", "Jesup", "Moonbeam"]
