"""Floor plans of the two levels (pure data, no bpy) — the single source of truth for build_world.py.

Plan coordinates: metres, x = east, y = SOUTH (screen down). Blender position = (x, -y, z); Godot = (x, z, y).
Grid: CELL = 0.5 m. Rooms are walkable rectangles separated by one solid cell (0.5 m walls). A door is a
rectangle of walkable cells cut through such a wall band.
Yaw (degrees) is the Blender yaw: 0 = the front faces south (+y plan, towards the camera), 90 = faces east,
180 = north, -90 = west. The iso camera sits south-east, so props that matter go on north and west walls.
"""

CELL = 0.5
WALL_H = 2.7

LEVELS = {}

# ----------------------------------------------------------------------------- the severed floor
SEV = dict(
    name="severed",
    size=(66, 43),
    rooms=[
        dict(id="hall", rects=[(9, 2, 53, 5), (9, 2, 12, 41), (50, 2, 53, 41), (9, 20, 64, 23), (9, 38, 53, 41)],
             floor="hall_floor", wall="wall_hall"),
        dict(id="break", rects=[(12.5, 5.5, 19.5, 11.5)], floor="carpet_grey", wall="wall_white"),
        dict(id="cobel", rects=[(12.5, 12, 19.5, 19.5)], floor="carpet_blue", wall="wall_white"),
        dict(id="mdr", rects=[(20, 5.5, 36, 19.5)], floor="carpet_green", wall="wall_white"),
        dict(id="wellness", rects=[(36.5, 5.5, 49.5, 11.5)], floor="carpet_warm", wall="wall_wood"),
        dict(id="perpetual", rects=[(36.5, 12, 49.5, 19.5)], floor="carpet_teal", wall="wall_cream"),
        dict(id="restroom", rects=[(12.5, 23.5, 19.5, 28)], floor="tiles_small", wall="wall_tile"),
        dict(id="orientation", rects=[(12.5, 28.5, 19.5, 37.5)], floor="carpet_grey", wall="wall_white"),
        dict(id="od", rects=[(20, 23.5, 36, 37.5)], floor="carpet_ochre", wall="wall_green"),
        dict(id="security", rects=[(36.5, 23.5, 49.5, 29.5)], floor="tiles_check", wall="wall_grey"),
        dict(id="kitchen", rects=[(36.5, 30, 49.5, 37.5)], floor="tiles_check", wall="wall_tile"),
        dict(id="lobby", rects=[(2, 26, 8.5, 37)], floor="marble", wall="wall_white"),
        dict(id="waffle", rects=[(53.5, 5.5, 64, 15)], floor="wood_floor", wall="wall_cabin"),
    ],
    doors=[
        dict(id="d_break", rect=(12, 8, 12.5, 9.5)),
        dict(id="d_cobel", rect=(15, 19.5, 16.5, 20)),
        dict(id="d_mdr", rect=(27, 19.5, 29, 20)),
        dict(id="d_wellness", rect=(49.5, 8, 50, 9.5)),
        dict(id="d_perpetual", rect=(42, 19.5, 43.5, 20)),
        dict(id="d_restroom", rect=(12, 25, 12.5, 26.5)),
        dict(id="d_orientation", rect=(12, 32, 12.5, 33.5)),
        dict(id="d_od", rect=(27, 23, 29, 23.5), lock="od"),
        dict(id="d_security", rect=(42, 23, 43.5, 23.5)),
        dict(id="d_kitchen", rect=(49.5, 33, 50, 34.5)),
        dict(id="d_lobby", rect=(8.5, 30.5, 9, 32.5)),
        dict(id="d_waffle", rect=(53, 9, 53.5, 10.5), lock="waffle"),
    ],
    # props: asset, x, y, yaw, optional id (for interactables / quest targets), z (mounted height for wall art)
    props=[
        # --- MDR: the four-desk pod, Mark S / Helly W / Dylan N / Irving E
        dict(a="desk_pod", x=28, y=12.5, yaw=0),
        dict(a="terminal", x=28, y=13.85, yaw=0, id="term_mark", z=0.74),
        dict(a="terminal", x=26.65, y=12.5, yaw=-90, id="term_helly", z=0.74),
        dict(a="terminal", x=28, y=11.15, yaw=180, id="term_dylan", z=0.74),
        dict(a="terminal", x=29.35, y=12.5, yaw=90, id="term_irving", z=0.74),
        dict(a="chair_office", x=28, y=15.0, yaw=180, id="seat_mark"),
        dict(a="chair_office", x=25.5, y=12.5, yaw=90, id="seat_helly"),
        dict(a="chair_office", x=28, y=10.0, yaw=0, id="seat_dylan"),
        dict(a="chair_office", x=30.5, y=12.5, yaw=-90, id="seat_irving"),
        dict(a="filing_cabinet", x=21.0, y=6.0, yaw=0), dict(a="filing_cabinet", x=21.8, y=6.0, yaw=0),
        dict(a="filing_cabinet", x=22.6, y=6.0, yaw=0, id="mdr_cabinet"),
        dict(a="water_cooler", x=34.8, y=6.1, yaw=0),
        dict(a="plant_tall", x=35.3, y=18.8, yaw=0), dict(a="plant_tall", x=20.7, y=18.8, yaw=0),
        dict(a="coat_rack", x=25.8, y=19.0, yaw=0),
        dict(a="painting_kier", x=28, y=5.5, yaw=0, z=1.55),
        dict(a="wall_clock", x=32.5, y=5.5, yaw=0, z=2.15),
        dict(a="board_quota", x=20.0, y=12.5, yaw=90, z=1.5, id="mdr_board"),
        dict(a="trash_bin", x=33.0, y=6.0, yaw=0),
        # --- break room
        dict(a="break_table", x=16.0, y=8.5, yaw=0),
        dict(a="chair_simple", x=16.0, y=9.6, yaw=180, id="seat_break"),
        dict(a="chair_simple", x=16.0, y=7.4, yaw=0, id="seat_break_m"),
        dict(a="sign_compliance", x=16.0, y=5.5, yaw=0, z=1.6),
        dict(a="plant_small", x=19.0, y=6.0, yaw=0),
        # --- Cobel's office
        dict(a="exec_desk", x=16.0, y=14.6, yaw=0, id="cobel_desk"),
        dict(a="chair_exec", x=16.0, y=13.4, yaw=0, id="seat_cobel"),
        dict(a="bookshelf", x=18.6, y=12.25, yaw=0),
        dict(a="couch", x=13.3, y=17.3, yaw=90),
        dict(a="plant_tall", x=19.0, y=19.0, yaw=0),
        dict(a="painting_tempers", x=14.0, y=12.0, yaw=0, z=1.55),
        # --- wellness
        dict(a="armchair", x=41.0, y=8.6, yaw=90, id="seat_casey"),
        dict(a="armchair", x=44.4, y=8.6, yaw=-90, id="seat_wellness"),
        dict(a="side_table", x=42.7, y=7.0, yaw=0),
        dict(a="floor_lamp", x=38.0, y=6.2, yaw=0),
        dict(a="painting_landscape", x=42.7, y=5.5, yaw=0, z=1.55),
        dict(a="plant_tall", x=48.8, y=6.2, yaw=0),
        dict(a="rug", x=42.7, y=8.6, yaw=0),
        # --- Perpetual Wing
        dict(a="pedestal", x=39.5, y=13.6, yaw=0), dict(a="pedestal", x=43.0, y=13.6, yaw=0, id="kier_wax"),
        dict(a="pedestal", x=46.5, y=13.6, yaw=0),
        dict(a="rope_line", x=43.0, y=15.3, yaw=0),
        dict(a="display_case", x=46.8, y=17.6, yaw=0, id="display_case"),
        dict(a="painting_young_kier", x=36.5, y=16.5, yaw=90, z=1.55),
        dict(a="painting_tempers", x=40.0, y=12.0, yaw=0, z=2.05),
        dict(a="bench", x=40.0, y=18.4, yaw=180),
        # --- restroom
        dict(a="stall_row", x=16.5, y=23.5, yaw=0, id="stall"),
        dict(a="sink_counter", x=12.5, y=27.0, yaw=90),
        # --- orientation
        dict(a="conf_table", x=16.5, y=33.0, yaw=90, id="orient_table"),
        dict(a="chair_simple", x=14.6, y=32.0, yaw=90), dict(a="chair_simple", x=14.6, y=34.0, yaw=90),
        dict(a="chair_simple", x=18.4, y=33.0, yaw=-90, id="seat_orient"),
        dict(a="painting_kier", x=16.0, y=28.5, yaw=0, z=1.55),
        # --- O&D
        dict(a="printer3d", x=22.0, y=24.6, yaw=0, id="printer"),
        dict(a="drafting_table", x=24.5, y=28.5, yaw=0), dict(a="drafting_table", x=27.0, y=28.5, yaw=0),
        dict(a="drafting_table", x=24.5, y=31.5, yaw=0), dict(a="drafting_table", x=27.0, y=31.5, yaw=0),
        dict(a="exec_desk", x=32.5, y=26.0, yaw=0, id="burt_desk"),
        dict(a="shelf_art", x=20.0, y=30.5, yaw=90),
        dict(a="sculpture", x=31.5, y=32.5, yaw=0),
        dict(a="plant_tall", x=35.3, y=24.2, yaw=0), dict(a="plant_tall", x=35.3, y=36.8, yaw=0),
        dict(a="plant_tall", x=20.7, y=36.8, yaw=0), dict(a="plant_small", x=29.8, y=24.0, yaw=0),
        dict(a="painting_barbarity", x=32.5, y=23.5, yaw=0, z=1.55),
        dict(a="painting_massacre", x=24.5, y=23.5, yaw=0, z=1.9),
        # --- security
        dict(a="monitor_wall", x=44.5, y=23.5, yaw=0, id="cctv"),
        dict(a="security_desk", x=44.5, y=25.3, yaw=0),
        dict(a="chair_office", x=44.5, y=26.5, yaw=180, id="seat_graner"),
        dict(a="lockers", x=36.5, y=26.5, yaw=90),
        dict(a="keycard_box", x=45.6, y=25.3, yaw=0, id="keycard", z=0.76),
        dict(a="plant_small", x=49.0, y=29.0, yaw=0),
        # --- kitchen
        dict(a="kitchen_counter", x=42.0, y=30.0, yaw=0),
        dict(a="coffee_machine", x=40.4, y=30.3, yaw=0, id="coffee", z=0.92),
        dict(a="fridge", x=47.6, y=30.4, yaw=0),
        dict(a="kitchen_table", x=42.5, y=34.0, yaw=0),
        dict(a="chair_simple", x=41.6, y=34.0, yaw=90), dict(a="chair_simple", x=43.4, y=34.0, yaw=-90),
        dict(a="vending", x=36.5, y=35.5, yaw=90, id="vending"),
        # --- lobby
        dict(a="elevator", x=2.0, y=29.0, yaw=90, id="elevator_main"),
        dict(a="elevator", x=2.0, y=34.0, yaw=90),
        dict(a="lumon_logo", x=5.25, y=26.0, yaw=0, z=1.2),
        dict(a="bench", x=6.0, y=36.5, yaw=180),
        dict(a="plant_tall", x=8.0, y=26.6, yaw=0),
        # --- waffle room (Kier's cabin replica)
        dict(a="waffle_table", x=58.5, y=10.5, yaw=0, id="waffle_table"),
        dict(a="cabin_bed", x=62.3, y=7.4, yaw=-90),
        dict(a="fireplace", x=58.5, y=5.5, yaw=0, id="fireplace"),
        dict(a="painting_kier", x=55.0, y=5.5, yaw=0, z=1.55),
        dict(a="candles", x=55.0, y=13.8, yaw=0), dict(a="candles", x=62.5, y=13.8, yaw=0),
        # --- halls
        dict(a="red_elevator", x=61.0, y=20.0, yaw=0, id="red_elevator"),
        dict(a="painting_young_kier", x=24.0, y=20.0, yaw=0, z=1.55),
        dict(a="painting_kier", x=46.5, y=20.0, yaw=0, z=1.55),
        dict(a="painting_tempers", x=33.0, y=2.0, yaw=0, z=1.55),
        dict(a="water_fountain", x=9.0, y=15.0, yaw=90),
        dict(a="bench", x=9.3, y=27.5, yaw=90),
        dict(a="fire_ext", x=50.0, y=31.0, yaw=90, z=0.0),
        dict(a="trash_bin", x=52.6, y=22.6, yaw=0),
        dict(a="plant_small", x=52.6, y=2.4, yaw=0), dict(a="plant_small", x=9.4, y=2.4, yaw=0),
        dict(a="painting_massacre", x=9.0, y=36.0, yaw=90, z=1.55),
    ],
    # markers: kind, x, y, yaw (+ optional fields)
    markers=[
        dict(k="player_start", x=16.5, y=35.8, yaw=180),
        dict(k="lobby_arrive", x=4.5, y=29.0, yaw=90),
        dict(k="red_arrive", x=61.0, y=21.5, yaw=0),
        dict(k="npc_milchick", x=30.0, y=21.5, yaw=0),
        dict(k="npc_cobel", x=16.0, y=13.4, yaw=0),
        dict(k="npc_burt", x=32.5, y=27.3, yaw=180),
        dict(k="npc_casey", x=41.0, y=8.6, yaw=90),
        dict(k="npc_graner", x=44.5, y=26.5, yaw=180),
        dict(k="helly_table", x=16.5, y=33.0, yaw=0),
        # Petey's map fragments (hidden in odd corners)
        dict(k="map_piece", x=50.6, y=40.4, yaw=0, id="map1"),
        dict(k="map_piece", x=63.4, y=22.4, yaw=0, id="map2"),
        dict(k="map_piece", x=19.0, y=36.9, yaw=0, id="map3"),
        dict(k="map_piece", x=9.6, y=2.6, yaw=0, id="map4"),
    ],
    # patrol routes for the stealth directives
    routes=dict(
        milchick=[(14, 21.5), (48, 21.5), (51.5, 21.5), (51.5, 39.5), (10.5, 39.5), (10.5, 21.5)],
        graner=[(51.5, 3.5), (51.5, 30.0), (51.5, 3.5), (10.5, 3.5), (10.5, 18.0), (10.5, 3.5)],
    ),
    signs=[  # room name plates next to doors (Godot draws them with Label3D): key, x, y, yaw
        ("mdr", 30.2, 20.0, 0), ("od", 30.2, 23.0, 180), ("break", 12.0, 7.4, -90), ("cobel", 17.6, 20.0, 0),
        ("wellness", 50.0, 7.4, 90), ("perpetual", 44.7, 20.0, 0), ("restroom", 12.0, 24.4, -90),
        ("orientation", 12.0, 31.4, -90), ("security", 44.7, 23.0, 180), ("kitchen", 50.0, 32.4, 90),
        ("waffle", 53.0, 8.4, 90),
    ],
)
LEVELS["severed"] = SEV

# ----------------------------------------------------------------------------- the testing floor (sub-level)
TST = dict(
    name="testing",
    size=(46, 28),
    rooms=[
        dict(id="hall", rects=[(8, 12.5, 44, 15.5)], floor="testing_floor", wall="wall_testing"),
        dict(id="t_lobby", rects=[(0.5, 10, 7.5, 18)], floor="carpet_red", wall="wall_testing"),
        dict(id="goats", rects=[(12, 2, 26, 12)], floor="grass", wall="wall_green"),
        dict(id="tent", rects=[(28, 2, 42, 12)], floor="concrete", wall="wall_white"),
        dict(id="cryo", rects=[(12, 16, 26, 26)], floor="testing_floor", wall="wall_grey"),
        dict(id="otc", rects=[(28, 16, 42, 26)], floor="concrete", wall="wall_testing"),
    ],
    doors=[
        dict(id="d_tlobby", rect=(7.5, 13, 8, 15)),
        dict(id="d_goats", rect=(18, 12, 19.5, 12.5)),
        dict(id="d_tent", rect=(34, 12, 35.5, 12.5)),
        dict(id="d_cryo", rect=(18, 15.5, 19.5, 16), lock="cryo"),
        dict(id="d_otc", rect=(34, 15.5, 35.5, 16), lock="otc"),
    ],
    props=[
        dict(a="red_elevator", x=0.5, y=14.0, yaw=90, id="red_elevator_up"),
        dict(a="bench", x=4.0, y=17.5, yaw=180),
        dict(a="lumon_logo", x=4.0, y=10.0, yaw=0, z=1.2),
        # goats
        dict(a="goat_fence", x=19.0, y=6.5, yaw=0),
        dict(a="hay_bale", x=14.0, y=3.2, yaw=0), dict(a="hay_bale", x=15.3, y=3.0, yaw=20),
        dict(a="hay_bale", x=24.6, y=10.6, yaw=0),
        dict(a="trough", x=21.5, y=4.0, yaw=0, id="trough"),
        dict(a="tree_small", x=13.0, y=10.5, yaw=0), dict(a="tree_small", x=25.0, y=3.0, yaw=0),
        dict(a="milk_crate", x=13.6, y=11.2, yaw=0, id="milk"),
        # tent
        dict(a="tent", x=35.0, y=6.0, yaw=0, id="tent"),
        dict(a="lab_bench", x=29.5, y=2.6, yaw=0), dict(a="lab_bench", x=40.5, y=2.6, yaw=0),
        dict(a="server_rack", x=28.4, y=10.0, yaw=90),
        # cryo
        dict(a="cryo_pod", x=14.5, y=16.4, yaw=0), dict(a="cryo_pod", x=17.0, y=16.4, yaw=0),
        dict(a="cryo_pod", x=19.5, y=16.4, yaw=0, id="cryo_pod"), dict(a="cryo_pod", x=22.0, y=16.4, yaw=0),
        dict(a="cryo_pod", x=24.5, y=16.4, yaw=0),
        dict(a="cryo_console", x=12.0, y=22.0, yaw=90, id="cryo_console"),
        dict(a="server_rack", x=25.6, y=24.5, yaw=-90),
        # OTC room
        dict(a="otc_switch", x=29.5, y=16.0, yaw=0, id="otc_a"),
        dict(a="otc_switch", x=40.5, y=16.0, yaw=0, id="otc_b"),
        dict(a="server_rack", x=33.0, y=16.4, yaw=0), dict(a="server_rack", x=37.0, y=16.4, yaw=0),
        dict(a="security_desk", x=35.0, y=22.5, yaw=0),
        dict(a="monitor_wall", x=35.0, y=26.0, yaw=180),
    ],
    markers=[
        dict(k="red_arrive", x=2.5, y=14.0, yaw=90),
        dict(k="npc_keeper", x=19.0, y=10.6, yaw=0),
        dict(k="goat", x=16.0, y=5.0, yaw=0, id="goat1"), dict(k="goat", x=20.0, y=7.5, yaw=90, id="goat2"),
        dict(k="goat", x=22.5, y=5.5, yaw=180, id="goat3"),
        dict(k="pen", x=19.0, y=6.5, yaw=0, w=9.0, h=6.0),
    ],
    routes=dict(),
    signs=[("goats", 20.3, 12.0, 0), ("tent", 36.3, 12.0, 0), ("cryo", 20.3, 15.5, 180), ("otc", 36.3, 15.5, 180)],
)
LEVELS["testing"] = TST


# ----------------------------------------------------------------------------- rasterising
def grid(level):
    """-> (W, H, cells) where cells[j][i] is a room id, 'door:<id>' or None. Cell (i, j) covers
    x in [i*CELL, (i+1)*CELL), y in [j*CELL, (j+1)*CELL)."""
    W = int(round(level["size"][0] / CELL))
    H = int(round(level["size"][1] / CELL))
    cells = [[None] * W for _ in range(H)]

    def fill(rect, val):
        x0, y0, x1, y1 = rect
        for j in range(int(round(y0 / CELL)), int(round(y1 / CELL))):
            for i in range(int(round(x0 / CELL)), int(round(x1 / CELL))):
                if 0 <= i < W and 0 <= j < H:
                    cells[j][i] = val

    for r in level["rooms"]:
        for rc in r["rects"]:
            fill(rc, r["id"])
    for d in level["doors"]:
        fill(d["rect"], "door:" + d["id"])
    return W, H, cells


def room_of(level, rid):
    for r in level["rooms"]:
        if r["id"] == rid:
            return r
    return None
