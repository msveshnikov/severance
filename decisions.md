# Decisions (made without asking)

## Remake (2026-11-19)

- **Full remake in Godot 4.7, isometric 3D ("2.5D").** The old game was a Vite/Cordova web page: a flat 2D canvas with
  pixel sprites running on the spot and 32 "directives". The Cordova project (`www/`, `platforms/`, `plugins/`, `res/`,
  `config.xml`, `package*.json`) was deleted, as the owner asked. Kept for reference in `concept/old_cordova/`: the six
  painted artworks (now hung as paintings in the game), the character sprites (colour reference for the 3D cast),
  `music.mp3` (now the title-screen music) and the old directive texts. Its release keystore was backed up first to
  `~/.android/severance-cordova.keystore` (+ `.txt`); `~/.android/severance-upload.jks` is a copy with key password =
  store password (Godot takes one password), same fingerprint `65:73:58:B5:…:56:5C`.
- **Camera**: orthographic, yaw 45°, pitch 36°, from the south-east. Default zoom puts a standing character at ~1/10 of
  the screen height (as asked); wheel / pinch zoom 7–22 m.
- **Walls**: real 2.7 m walls with a dithered "cutaway" hole on the line of sight to the active innie (global shader
  uniforms `cut_center/cut_dir/cut_radius`, `shaders/cutaway.gdshader`), so rooms read as rooms but the player is never
  hidden. Back faces of walls are not built at all (faces exist only between a solid and a walkable cell), so the outer
  walls nearest the camera never block the view.
- **Grid world**: plans in `blender/scripts/office_plan.py` (0.5 m cells, rooms separated by one solid cell). Blender
  writes the architecture glTF + `*_layout.json` (grid, rooms, props, markers, doors, routes, signs); Godot builds the
  level at runtime and walks on an `AStarGrid2D` with string-pulling. No physics bodies: collision is the grid.
- **No concept art from ChatGPT** this time: the design follows the show's look (white corridors, green MDR carpet,
  retro cream terminals, wood-panelled wellness room) and the cast follows the colours of the old sprites. Everything 3D
  is procedural Blender code (71 props, 12 rigged characters incl. Kier's wax likeness and a baby goat).
- **Characters**: stylised (big heads, readable at 70 px), one shared 20-bone rig, 19 animations (walk/run/sneak, sit,
  sit_type, talk, interact, dance ×2, cheer, lever, read, feed, lie, point, wave, nervous, sleep_sit) + goat rig (idle,
  walk, eat, hop). Portraits for the UI are rendered by the same script.
- **Story rewritten**: 32 loose directives (many "Reddit theory" fetch quests) → 18 directives in 3 acts + finale, each
  with its own verb and most with a minigame: orientation survey, refinement (core), Statement of Compunction (timing),
  O&D gift delivery, timed refinement for finger traps, the book in the restroom, a stealth run past Milchick and Graner
  (vision cones), Petey's map pieces, Ms. Casey's wellness session (breathing rhythm), Kier's spectacles code, stealing
  Graner's keycard while he naps, printing a copy (temperature hold), the red elevator, feeding baby goats, the cold
  storage keypad, the two-person Overtime Contingency (two innies hold two switches at once — character switching is the
  puzzle), 100% quota and the Music Dance Experience (4-lane rhythm game to Defiant Jazz) + waffle party.
- **Refinement minigame**: scary groups are found by motion, as in the show: Woe sinks, Frolic bounces, Dread trembles,
  Malice twitches; a lens magnifies digits under the cursor/finger. Files are the show's file names.
- **Four innies are switchable** (portraits, Tab, 1–4, or tap an innie). Inactive innies wander back to their desks
  and type. Each directive names the innie it needs; the portrait pulses.
- **Languages**: English and Russian (auto by OS locale, switch in Settings). All texts in `scripts/texts.gd`.
- **Audio** synthesized by `tools/make_audio.py` (numpy + scipy): piano/pad office theme, testing-floor drone, stealth
  ostinato, a swing "Defiant Jazz" loop (walking bass, ride, brushes, Rhodes, muted trumpet), ambience and ~30 effects.
  The old game's `music.mp3` plays on the title screen.
- **Rendering**: Forward+ on desktop (shadows, SSAO, fill lights per room), Compatibility on Web/Android ("auto" quality
  = fast there: no shadows / fill lights). MSAA off (Mali leak, see Hot Bag).
- **Android package kept as `com.maxsoft.Severance`** (the existing Google Play app, Cordova build code 10007) →
  2.0.0 (code 20000). The Play AAB is signed with the same upload key as the old app.
- **Deploy**: the web build replaces the old game at the root of https://severance.lol/ (owner's request).

## 2.1.0 (2026-11-19, after the owner's playtest)

- **Flicker fixed at the source**: Blender materials are now single-sided (`use_backface_culling`), so the hidden
  bottom faces of stacked boxes no longer z-fight with the floor or the box below; door headers stop 12 mm under the
  wall caps; the blob shadow sits 3.5 cm above the floor (rugs are 1.6 cm).
- **No more walking through walls**: when the target is unreachable (a locked room), A* returns a partial path and the
  game used to append the exact click — a straight line through the wall. The final point is now only snapped when the
  path really reached the target cell. `--walltest` checks 1200 random paths and 800 WASD runs per build (0 violations).
- **Choices in dialogue** are spoken by the person answering (`["?helly", "A|B"]`), not by the active innie.
- **Sitting**: the innie steps in front of the chair, turns, sits and types for a second before a terminal minigame opens.
- **New cast (lib_char2.py)**: adult proportions (~7.3 heads, 1.76 m) instead of big-headed cartoons, small natural
  eyes, lips, nose, jaw, sculpted hair, tailored clothes (lapels, collars, cuffs, buttons, pockets), hands with
  fingers. The designs stay original: colours from the old game's sprites, no attempt to copy the actors' likenesses,
  so no ChatGPT "look-alike" portraits either — portraits are rendered from the new models.
