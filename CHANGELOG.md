## v3.1.131 — the jump-brake learns its latency, and every tab wears its world

*(the R53 session: four autopsies' worth of telemetry honesty in the
grand tour, the tab thumbnails, and the hero's own face on the PIE HUD;
the 03:00 and 04:00 UTC boundaries are covered by this tag — the round
spent them mid-autopsy and the debt is declared honestly here.)*

- **THE SIXTEENTH AUTOPSY — THE JUMP-BRAKE'S DOSE**: the R52 release
  (`vx <= -0.4 * vx_at_fire`) was calibrated latency-free, but the dose
  rides 40Hz sampling plus 1-2 input ticks: the trace shows the release
  DECIDED at vx=-148 yet the engine still held 'a' to vx=-225, and the
  arc dumped 111px (launch 1218 -> landing 1106) — off ledge-b onto
  lift-1's descending deck, where the default walk ran the hero off the
  deck's edge (11 honest deaths in the red run). Two dose leaks fixed:
  the hold is AIRBORNE-ONLY (the old branch returned 'a' on the stale
  grounded ticks and bled the launch 235 -> 158), and the release is
  the zero-cross at +0.4 * vx_at_fire — the sampled first-below lands
  ~76 under the threshold, the latency adds ~153, and the cut settles
  at ~ -90 across the whole 150..330 fire band. The arc now parks
  launch-9..-41 on ledge-b every time (the honest-launch case measured
  at launch-12).
- **THE ELEVATOR TURNAROUND WALK-OFF (level-1)**: at the elevator's
  bottom turnaround the deck's carry wobbles (py 325.2 -> 327.9 ->
  327.1 -> 324.3) and the 4-sample delta dips below ride_check's 1.5
  floor — the law read "not a carry", fell through to the default
  b"d", and a hero parked at 1448 (the board arc lands up to 1448; the
  deck's edge is 1450) walked off at full run accel — five falls
  (1585..1728, the drift of a 330px/s fall from py 324). The elevator
  re-acquisition guard now owns the deck's travel band (x 1330..1449,
  standing 215..340): a non-riding hero walks back into the interior
  and holds until the carry is witnessed; the top turnaround stays
  unguarded because there the default IS the disembark.
- **THE GAP-DECK TRIPLE MISS (level-1)**: the disembark's fixed band
  (830..910) assumed the deck parked at its right extreme — but the
  deck ping-pongs, a hero who arrives while it retreats meets its edge
  at 835, the fall ate both windows, and the landing at 896.6 missed
  the ground window by 1.6px (the box-right 941 grazed the spike's
  940; four deaths at 907..909). Three layers now: the disembark is
  PHASE-AWARE (it reads the deck's live left edge and fires near
  whatever the right edge is), a falling hero in the approach corridor
  holds 'a' so the byte lag can't eat the pull (the air brake cuts the
  fall's drift from +61px to +22px), and a past-window landing walks
  back into the window.
- **THE FIRE-BAND CRAWL (level-3)**: every leftward walk in the lift-2
  fire band accelerated at the FULL RUN_ACCEL — a hero pulsed to -330
  cannot stop before ledge-b's left edge (the stop needs ~85px, the
  balance sits at px 1146: the trace's stand at 1205.7 walked off
  EXACTLY there and fell to the 1345..1356 pit). All three leftward
  laws pulse to -150 and coast — the stop is ~18px, the overshoot
  holds 13px of ledge.
- **THE BOARDING GATE THAT WASN'T**: a boarding vx gate + a park/run-up
  was built to block the low-vx pit falls (954..1016) — measured 2/4
  red (the bounce/park cycles tripled the boarding time against the
  170s cap) and REVERTED by evidence; the R51 coast-through stands and
  the residual full-speed-crossing family (1002..1021) is R54's first
  declared debt.
- **THE UI MARQUEE — THE TAB THUMBNAILS**: every scene tab now wears a
  live miniature of its own map — the biome sky tint, the platforms,
  the movers, the spikes, the coins and the goal fitted into a 76x44
  canvas, redrawn from the scene's own geometry on every tab render
  AND on every edit of the active scene; the active tile wears the
  brand-violet glow. **THE PLAYER PORTRAIT**: the PIE HUD wears the
  generated hero bust (image gen, mandatory — the JPEG-bytes law's
  14th catch, re-encoded to a real PNG, magic verified) in a rounded
  brand-violet frame with a live HP bar that bleeds with every death
  and is restored on the load.
- ui_editor_probe pins 19 (was 18) — the R53 law group re-pins the
  thumbnails' render, the edit-follow, the portrait's real PNG bytes
  and the HP bleed. Five corners wear 3.1.131; this tag's release must
  carry dxn3-3.1.131.tar.gz.

## v3.1.130 — the About modal becomes a credits splash

*(the same R52 session, one increment later — push often.)*

- **THE ABOUT MODAL REFRESH** — UE5's credits-splash shape: the hero
  banner under a chip row (the version in brand violet, the gates'
  count, the C++23 zero-deps badge), the four pillars as cards (the
  engine's spark constants, the editor's UE5 cloth, the grand tour's
  five walked scenes, the gates' ALL GREEN law), and the four biome
  HUD skins as a thumbnail gallery — industrial, twilight, dawn, void
  — the studio showing its own generated art off.
- The drag-drop spawn audit: the Place Actors palette's drag-to-viewport
  spawn (dragstart sets text/dxn1-actor, the drop spawns snapped at the
  cursor with history and a toast) was found COMPLETE in the tree —
  R51's debt list carried it in error; the debt is closed by evidence.
- ui_editor_probe stays 18 pins — the R52 law group grows to four (the
  About chrome's cloth, the skins gallery, the dawn frame inside it).
- Five corners wear 3.1.130; this tag's release must carry
  dxn3-3.1.130.tar.gz.

## v3.1.129 — the no-win landing learns to fly, and the selection edits as one

*(the 02:00 UTC boundary's tag; the R52 round pays it.)*

- **THE FIFTEENTH AUTOPSY — THE NO-WIN LANDING**: the lift-2 boarding's
  dirty secret, found by re-reading tour_fail_1789781046's telemetry with
  the engine's own constants (RUN_ACCEL 2300, AIR_FRICTION 220, JUMP_VY
  -620 — the wjump's flight bled its 330 launch to 108-185 by landing):
  the ground truth is the MISSED FIRE, not the landing. The [1205,1232]
  fire band is 1-2 telemetry samples wide; one missed sample slides the
  run past 1230 at 250-267px/s, and the ground reverse's 44-49px brake
  ends at 1274-1279 — box-right >= 1308 inside the watcher spike's box
  (1290). No ground brake from any overshoot point survives (290px/s
  alone slides 61px from the leftmost landing). The debt's "lands at
  vx=330" was the wrong premise; the geometry is honest now.
- **THE JUMP-BRAKE** — the escape is AIRBORNE: the overshoot fires 'wa'
  (x > 1230, vx > 150; hot wjump landings at x > 1215, vx > 140) and the
  flight holds 'a' until vx <= -0.4 x vx_at_fire — answer-driven, the
  back-drift cancels the out-drift, and the landing settles 2-20px LEFT
  of the launch inside the park zone. The arc's x-apex never passes
  launch+27 (the watcher's box-left is 1290) and the rise clears the
  spike's top (162) at t=47ms, so the continuous trajectory holds no 2D
  overlap at all; a wall cap hands a starved flight to the flight
  silence. Three solo greens after the fix (45.7s/1, 47.3s/1, 58.8s/5
  honest deaths — all recoverable), 10/10 pins each.
- **THE MIXED PILL — the multi-select Details grows UE5's per-property
  bulk edit**: the multi panel's new Properties grid renders every
  property of the selection as a row (x, y, w, h, alpha, color, shape,
  solid) — values every actor shares edit in place; values that differ
  wear the italic dashed "Multiple Values" pill, and one click adopts
  the first actor's value into a real editor whose edit writes the
  WHOLE selection (num rows keep the scrub, the select and the check
  ride the same law). The Appearance color row is the grid's now.
- **THE DAWN HUD SKIN** — the map's missing fourth biome frame lands
  (image gen, mandatory — the JPEG-bytes law's 13th catch, re-encoded
  to a real PNG, magic verified): rose-gold sunrise filigree corners
  for the alpine dawn scenes (level-3/5/8), keyed by scene file in
  HSKINS like its three siblings.
- ui_editor_probe pins 18 (was 17) — three R52 laws re-pin the pill's
  cloth, the grid's coverage and the dawn frame's real PNG bytes.
- Five corners wear 3.1.129; this tag's release must carry
  dxn3-3.1.129.tar.gz.

## v3.1.128 — the runner learns GCC 14, and the release train ships steel

*(the 01:00 UTC boundary's tag; the R51 round pays it.)*

- **THE FOURTEENTH AUTOPSY — THE RUNNER'S COMPILER**: every release
  since v3.1.121 minted with notes but no binary, and the CI badge
  burned red — the cause was one header: the engine includes C++23's
  `<print>` (std::println on the wire's welcome mat), which ships
  with **GCC 14**, while GitHub's ubuntu-latest runner defaults to
  **GCC 13**. The local Debian g++ is 14.2, so every local gate ran
  green while the runner's `make` died on the first include — the
  v3.1.126/127 releases minted via the sweep's notes-only path and
  the mint's upload had no file to upload. The fix: both workflows
  install `g++-14` (in ubuntu 24.04's own repos — still zero
  dependencies of OUR own) and the Makefile's `CXX=` override points
  the build at it; the CI matrix narrows to `g++-14` (clang's
  libstdc++ pairing had the same 13-shaped hole).
- **THE INSTALLER'S HONEST PROBE**: install.sh's tool check accepted
  any compiler that recognized `-std=c++23` — GCC 13 recognizes the
  flag and then fails three steps later on the real source. The probe
  now compiles a literal `#include <print>` one-liner and FAILS the
  install loudly on a compiler that lacks it, prefers g++-14 when
  present, and passes its own choice to the Makefile (`CXX=$CXX_BIN`).
- v3.1.127's release (the first tag after the by-value mint rewrite)
  still minted asset-less — the compiler was the last lie. This tag's
  release is the first that must carry dxn3-3.1.128.tar.gz; the run
  log echoes the asset list it uploaded. Five corners wear 3.1.128.

## v3.1.127 — the outliner grows a hierarchy, and the camera keeps slots

*(the R51 round's first tag; the 01:00 boundary's debt moved to
v3.1.128 when this landed nine minutes early.)*

- **THE OUTLINER TREE** — UE5's outliner is a hierarchy, not a flat
  list: the entities now group under their tag's folder (player,
  solid, coin, mover…), every folder wears a live count chip, a fold
  arrow and its own eye — the eye hides or reveals the WHOLE group in
  one click (five coins at once, verified). The fold state rides the
  editor's prefs and survives a reload (fold "solid" → 18 children
  collapse to 11 → reload → still 11). A search flattens the tree the
  way the real thing reveals filtered actors. Live headless-verified:
  7 folders over 18 entities on playground, fold → reload → persist,
  the group eye on and off.
- **THE CAMERA BOOKMARKS** — UE5's viewport slots land: Ctrl+1..9
  saves the camera, 1..9 recalls it, and the "1-9" pill in the
  viewport bar opens the desk — nine slots wearing their camera
  coordinates, each with Save and Restore buttons. The slots ride the
  prefs across reloads and sleep during PIE (the digits belong to the
  game while it plays). Live headless-verified: Ctrl+1 save → move →
  1 recall → the camera returns to the saved frame; the desk lists 9
  slots with slot 1 armed.
- **THE HUD SKINS** — the PIE HUD's chrome now follows the biome, the
  same law the skies obey: keyed by scene file with the generic frame
  as the honest fallback. Three generated frames (image gen,
  mandatory — the JPEG-bytes law's 10th, 11th and 12th catches, all
  re-encoded to real PNGs, magic verified): the twilight temple's
  violet scrollwork (level-2/7/12), the industrial factory's riveted
  amber hazard plate (level-1/6), the cosmic void's crystalline
  starlit corners (level-4/9/10). Live headless-verified: level-2
  wears hud-twilight.png, level-4 wears hud-void.png, the skies and
  the chrome now agree on the biome.
- ui_editor_probe pins 17 (was 16) — five R51 laws re-pin the tree's
  fold law, the group eye, the bookmark save/recall/desk trio, the
  PIE sleep guard and the skins' real-PNG cloth. Five corners wear
  3.1.127. This is also the first tag pushed since the mint job was
  rewritten to take the tag by value — its release is the first that
  must carry dxn3-3.1.127.tar.gz, and the run log now echoes the
  asset list it uploaded.

## v3.1.126 — the phantom ride is dead, and PIE wears the game's face

*(the 00:00 UTC boundary's tag; the R50 round pays it.)*

- **THE THIRTEENTH AUTOPSY — THE PHANTOM RIDE**: `ride_check`'s
  carry band (py drifting 1.5-20px across 4 telemetry samples) also
  fits a LANDING's own decay (371 -> 386 across the same window,
  d=15) — a phantom ride on solid floor — and the ride laws re-fired
  their disembark jumps on the ground: level-2's fired at x 1016
  (benign) and again at 1225, whose arc crossed the goal's x-band
  100px ABOVE the goal box and dropped the hero past ground-b's edge
  (the 1640,933 death — a parasite-vs-touch race the greens kept
  winning by timing luck; run 6 lost it and bled 172s); level-3's
  fired on ledge-b and lofted the hero past lift-2 (the 1435,937
  death). The fix is one honest predicate: the ground stands at
  py 386 and every real deck in the campaign carries its rider at
  py < 380, so a "ride" at py >= 380 is a landing ghost, never a
  deck. The phantom is dead at the source, in every scene at once.
  Two consecutive solo greens after the full fix set: 41.7s with
  ZERO deaths and 59.3s with 2 — against run 6's 172s/5-deaths red.
- **THE PARK-AND-RUN BOARDING** (the twelfth autopsy,
  tour_fail_1789775071): the old coast-through band (783..813, fire
  at any vx) was a 30px slice crossed at full speed between two
  probe samples under load; the missed window slid the hero into a
  brake oscillation whose 67px stopping distance walked it off
  ledge-a's left edge, and the recovery walk fell off the ground's
  right edge at 800 — a 133-death loop (the round's first run).
  Now: the arrival coasts right and brakes only past 845 (an earlier
  brake slides 79px off the left edge), the idle hero is
  velocity-damped into the park box [772,784], and the fire is a
  RUN — on the deck's bottom-turn the hero accelerates and fires
  b"wd" at the first sample with vx >= 290 inside the launch box
  [800,845]; the landing = sampled x + lag(8..25px) + the
  ~205..215px arc ∈ [1013,1085], inside the deck's 990..1120 for
  every lag. A missed cycle is a safe re-park, not a death.
- **THE RECOVERY LAWS**: the ground-edge guard (657 < x < 800 walks
  LEFT back into the ledge-a jump window — a missed window is now a
  recovery loop), the summit guard (a door arc shifted right by the
  byte lag that lands past the goal walks LEFT back through the
  goal box — the 1889,936 void death is recoverable), the wjump is
  RISE-ONLY (a descent fire launched the arc from a falling deck and
  landed 57px short — the same bug family as R48's door fix), and
  the lift-2 sink window tightened to y <= 100 (fires sampled in the
  100..130 band lagged into a deck already at its bottom — five
  deaths at x 1372..1434 in the red run).
- **THE PIE HUD — the game's face during play**: playing in editor
  now wears a real HUD, not one bare canvas line — the DOM overlay
  carries the stat pills (SCORE with the coin icon, the clock,
  DEATHS), the live spark telemetry bars (vx against PIESPEED, vy
  against gravity's 1500) and the grounded/airborne state, switched
  on by startPlay, off by stopPlay, fed by drawSim at frame rate
  (five textContent writes and two bar widths per frame). Live
  headless-verified: boot -> Play -> the clock ticks, the vx bar
  pins 100% at run speed, a 'w' flip flips the state airborne with
  the vy bar riding the rise (9.7% at 145px/s), stop strips the
  overlay; console clean.
- **THE GENERATED CHROME** (image gen, mandatory — the JPEG-bytes
  law's 8th and 9th catches): the HUD wears hud-frame.png (the four
  glowing corner brackets over the viewport, screen-blended) and
  hud-panel.png (the carbon-slate pill backdrop); both arrived as
  raw JPEG and were re-encoded to real PNGs, magic verified. The
  Place Actors palette's hover states land too — the cards lift and
  their icons glow.
- **THE RELEASE TRAIN CARRIES ITS BINARY**: the mint job now builds
  the zero-dependency binaries on the runner (make, both artifacts
  test-executed) and uploads dxn3-<tag>.tar.gz (binaries + scenes +
  ui + README + CHANGELOG) to every tag's release — every release
  since v3.1.121 minted with notes but zero assets (the API eyes
  finally looked); the next tag is the first that ships the box.
  ui_editor_probe pins 16 (was 15) — the four R50 laws re-pin the
  HUD's cloth, its sim feed, its real-PNG chrome and the palette
  hover. Five corners wear 3.1.126.

## v3.1.125 — the summit is crossed, and the selection scales as one

*(the 23:00 UTC boundary's tag; the R49 round pays it.)*

- **THE SUMMIT CROSSING**: the grand tour walks playground ->
  level-1 -> level-2 (the thawed decks) -> level-3 (the fang, the
  ledge-a, the two lifts, the golden door) -> level-4 — 10/10 pins,
  49-78s against the 170 cap, three consecutive greens. The walk
  through level-3's interior is the campaign's hardest sentence of
  geometry, and every window in it is now telemetry-honest:
  - the coast-jump disembark fires 'w' ONLY — the walk's own
    momentum is the launch vx, because a 'wd' fire merged the walk's
    queued bytes with the fire's own 'd' and the TRUE launch vx was
    330 regardless of the sampled gate (the arc stretched onto the
    watcher);
  - the flight-silence latch clears only after an AIRBORNE sample
    was witnessed — the fire happens on the deck, so ~10 probe ticks
    still see vy=0 and the old latch read "landed" instantly,
    resurrecting the default walk mid-flight;
  - the fang fires from a STAND (the brake at 300, the fire at
    [320,350]) — a stopped hero cannot be dragged past the window by
    any byte lag, and the mid-air accel fills in the +249 arc;
  - the door fires on the lift's RISE only (y<=24, lift y<=70) — a
    descent launch crossed the door's y band 100px short of the door
    and fell past the whole summit;
  - the lift-2 run-jump widened to [1205,1232] with a safe reverse
    at 1230 (the walk-past used to graze the watcher by 1px);
  - failed walks keep their trace at /tmp/tour_fail_*.trace (the
    forensics law — the non-debug red runs used to delete their own
    evidence; the patch itself hit a NameError on `fails` and the
    run convicted it).
- **the selection scales as one**: the 8 scale handles now live on
  ONE box — a single selection wears its own, a multi wears the
  bounding box — and the drag is the GROUP SCALE: every selected
  entity rides the bbox factor (position AND size), so the group
  keeps its shape exactly as UE5's multi-scale does. Live-verified:
  a three-entity selection's SE drag +100,+50 grew the bbox
  1430x220 -> 1530x270 with the NW anchor pinned and all three
  entities at factor-exact positions; the single-selection scale
  and the translate gizmo's axis lock survived the refactor. The
  history lands as "scale 1430x220 -> 107%".
- **the studio's face refreshes** (image gen, mandatory): the boot
  splash wears splash-v2 (the four biome portals over charcoal) and
  the Content Browser opens under campaign-map — the campaign's four
  biomes as one glowing strip. Both raw files were JPEG (the
  JPEG-bytes law's 6th and 7th catch) — PIL re-encoded, magic
  verified.
- ui_editor_probe pins 15: pin 14's scale law re-pins the group
  math (selBox + bboxHandles + the factor loop) and the new art.
- ui/index.html, VERSION, version.hpp and the README badge wear
  3.1.125.

## v3.1.124 — the handles bite, the desk remembers its tabs, the sky follows the biome

*(the 22:00 UTC boundary's tag; the R48 UI round pays it.)*

- **THE PARSE LAW (the round's deepest find)**: v3.1.119 shipped a
  syntax error inside the editor's script — `for(const x,hy] of`, a
  destructuring bracket lost to a bad merge — and FOUR releases plus
  six all-green gate runs never saw it, because every
  ui_editor_probe pin read strings and none parsed the cloth: the
  whole editor was dead in every browser while the gates stayed
  green (R45's "the probe pinned the cloth, not the runtime" law,
  proven again at scale). The probe grows pin 13 — the script must
  PARSE (`new Function()` compiles it without running, via bun) —
  and the syntax is fixed. The parse law now guards every future
  edit; a probe that reads strings is a probe that trusts a corpse.
- **the scale gizmo**: the 8 orange squares on the selection's box
  were drawn since v3.1.119 and never once bit — R48 makes them the
  scale gizmo. Corners resize both axes, edge midpoints one; every
  drag anchors the OPPOSITE edge (the SE handle grows the box, the
  NW corner never moves); snap-aware with an honest 8px floor; the
  history lands as "scale WxH"; the hover wears the resize cursors
  and the grabbed handle brightens. One source of truth
  (handlePos) draws them AND hit-tests them, so the paint and the
  pick can never disagree. Live-verified headless: the ground's SE
  drag +60,+40 grew it 1400x90 -> 1460x130 with the anchor pinned,
  and the translate gizmo's axis lock survived the refactor.
- **the desk remembers its tabs**: openTabs join the localStorage
  prefs — open level-2, reload, and the tab bar (and the active
  tab) come back exactly as left. Live-verified: two tabs before
  the reload, the same two after, cur restored.
- **the sky follows the biome**: four generated wide backdrops
  (1344x768, one per campaign biome — twilight temple, industrial
  dusk, dawn peaks, cosmic void) keyed by the scene file (SKYS
  map, the generic sky.png stays the fallback). The viewport wears
  the scene's own sky at the same worn 0.5 alpha; the images are
  real PNGs (the JPEG-bytes law caught all four raw — PIL
  re-encoded, magic verified) and the loader caches one Image per
  asset. Live-verified: level-2 renders sky-twilight at full
  decode, console clean.
- ui_editor_probe pins 15 (was 13): the parse law and the four R48
  studio laws join the twelve. ui/index.html, VERSION,
  version.hpp and the README badge wear 3.1.124.

## v3.1.123 — the ferries thaw, and the wire speaks the decks' truth

*(the 21:00 UTC boundary owed a tag; the R48 round pays it.)*

- **engine mover telemetry** (native/src/main.cpp): when DXN3_TRACE is
  set, every live mover now confesses its true pose on the wire at the
  player line's own cadence — `MOVER n=<name> x= y= pxi= dir=` (pxi is
  the path index the deck heads to, 1 = outbound; dir is the ping-pong
  sign). The tour's boarding windows read the deck's REAL position
  instead of inferring a phase from a constant that was measured
  against a frozen statue. Same env gate; invisible in honest play.
- **the thaw** (scenes/level-2.dxn1.json): two lines — mover-1 and
  mover-2 wear tag:"mover" and the ferries run their paths, ping-pong
  deterministic per spark.cpp's stepMovers. The diagonal deck now
  carries riders from (400,360) to (660,250) and back; mover-2 slides
  980..1130 over the walk to the goal (64px over a walking hero's
  head — no interference, verified on the wire).
- **the tour's thawed board** (probes/grand_tour_probe.py): the frozen
  era's receipt-lock (a 45-step pipeline constant measured against the
  statue itself) is REPLACED by the telemetry law — fire the strip
  jump when the deck is OUTBOUND within ~80px of its home corner; the
  arc chases the leaving deck and boards mid-rise, and the ride law
  carries the rider to the 655 disembark whose arc lands 940..966,
  past the saw. The scan fallback stays for a wire-less run.
- **the door stand**: the goal touch fires the transition, but the
  walk that kept holding 'd' carried the hero off ground-b's end
  DURING the 0.75s load — the fall death respawned him and the
  respawn CANCELLED pendingNext (eleven deaths in one run). The hero
  now stands hands-off at the door while the shell speaks the welcome.
- **the stuck-law sharing fix**: dec_level3's ground-walk set
  st.last_x before stuck_jump read it, every new sample measured dx=0,
  and the stuck law fired 'wd' every 100ms of honest walking — the
  arcs landed in the fang and the tour bled 40 lives in its first
  thawed run. The fall-through now leaves last_x to the stuck check,
  the way dec_level1/dec_level2 always had it.
- **R48 also BUILT** the level-3 summit walk (dec_level3's interior:
  the fang band, the ledge-a jump, two telemetry-driven lift
  boardings, the coast-jump disembark whose flight silence keeps the
  arc out of the watcher, the golden door) — ten trace autopsies deep,
  the chain fires end to end but the 170s cap crossing is not proven
  yet: HOPS stays at three and growing to level-4 is R49's first
  debt. The law set ships in this probe so the next round walks in
  armed.
- ui/index.html, VERSION, version.hpp and the README badge wear
  3.1.123 (the fifth corner pinned by ui_editor_probe).

## v3.1.122 — the viewport wears tabs, the gizmo moves armies, the palette wears its icons

*(the 19:00 UTC boundary owed a tag; the R47 round pays it.)*

- **the viewport wears tabs** — every scene visit opens a tab over
  the viewport (click to switch, ✕ or middle-click to close, the
  last tab never dies — a studio always shows something). The scene
  picker and the tabs stay in sync, and closing the active tab
  activates its neighbor.
- **the translate gizmo anchors any selection** — single selection
  pivots at the entity's center; multi-selection pivots at the
  bounding box's center and the axis drag moves the whole selection
  (verified live in the browser: three entities, one shared dx, y
  untouched, history "gizmo x").
- **the Content Browser's cards grow a context menu** — right-click
  any scene card for Load in viewport, Duplicate scene… (deep-copies
  the JSON into memory, opens its tab), Rename… (rekeys the scene in
  memory, SCENES, the open tabs and the picker), and Save to disk.
- **the palette wears its icons** — ten generated per-actor icons
  (block, mover, goal, hazard, spike, bouncy, ball, coin, sign,
  player) replace the unicode glyphs, downscaled to 128px real PNGs
  (the JPEG-bytes law caught all eleven raw files); the About modal
  wears a new wide hero banner. `ui_editor_probe` pins 13: the five
  R47 studio laws (tabs, the bbox-pivot gizmo, the card menu, the
  icon set, the banner) join the twelve.
- **the ferries investigation (attempted, reverted, queued)** — this
  round's probe work found a REAL scene bug: level-2's mover-1 and
  mover-2 carry `path` and `pspeed` but never the `tag: "mover"`
  spark's law requires, so both ferries have stood FROZEN since
  v3.1.106's dialect conversion (the sign says "ride the lifts"; the
  lifts never moved; every green tour run to date boarded a frozen
  statue). The thaw itself is one line per ferry — but it invalidates
  the grand tour's entire level-2 choreography, whose boarding
  windows were tuned against a deck that never moved (hands-off
  rides, a receipt lock measured on a statue). Three laws were
  rewritten for moving decks (the run-the-deck ride, the sign-top
  walk-off with a latch and an arrival-only catch window, the
  scan-only boarding) and the walk crossed the THAWED level-2 green
  — but not within the probe's 170s cap under load: the crossing's
  catch windows need the deck's true phase, and the trace carries no
  mover state. The honest move: the scene fix and the tour changes
  are REVERTED here, re-landed in R48 behind an engine-side mover
  telemetry line (a mover line in the trace, then the windows derived
  from data). The bug is real, documented, and one round from fixed.

## v3.1.121 — the gizmo you can grab, the world you can edit, the lifts that behave

*(the 18:00 UTC boundary owed a tag; the R46 round pays it. Also folds
in the live-boot fix that landed after the v3.1.120 tag — see f5cea47:
v3.1.119's editor never completed a real browser boot because the top
level `fitCanvas(); renderStats();` hit `renderStats`'s naked `ents()`
while the wire's scenes were still in flight; the guard now precedes
the call, pin 9 pins the order, and the probe grew to 12 pins.)*

- **the translate gizmo is real** — selecting a single entity draws
  the UE5 arrows at its center: red X to the right, green Y downward
  (the wire's y grows downward, so the arrow does too). Grab an arrow
  and the entity slides along THAT axis only — axis-locked, snap-aware,
  mover paths rebased — even when the arrows cross another actor: the
  gizmo outranks the body. The cursor confesses the axis it is over
  (`ew-resize` / `ns-resize`), the drag lands in history as
  "gizmo x/y", and PIE gets no arrows (it has gravity instead). The
  corner compass stays — the map, while these arrows are the
  territory.
- **the outliner grows a context menu** — right-click any row (an
  unselected row selects first, UE5's law) for Focus, Duplicate,
  Rename…, Hide/Unhide, Select-all-with-this-tag, and the red Delete.
  Clicking an already-selected row no longer betrays the rest of a
  multi-selection, and Escape closes the menu.
- **World Settings** — with nothing selected the Details panel now
  edits the stage itself: scene name, background color, gravity, and
  the next-scene link. These are the scene's own JSON fields, the
  same ones spark reads off the wire — gravity is a REAL field
  (spark.cpp:37, clamped ±5000 at :176), and the panel obeys the same
  clamp. Negative gravity falls UP; spark truly allows it.
- **PIE obeys the scene's gravity** — the sim no longer parrots the
  constant: `startPlay` reads the scene's own `gravity` field (1500
  default, ±5000 clamp, exactly like spark.cpp) and the PIE receipt
  logs it. A scene that ships `gravity: 3000` now plays at 3000 in
  the editor and in the binary.
- **PIE now speaks the engine's collision law verbatim** — the smoke
  test exposed three divergences, all fixed against spark.cpp as the
  reference: (1) the engine NEVER reads the `solid` field — tagless
  bodies are solid, movers are solid vertically only (boarding from
  the side is legal), everything tagged lets the player pass; PIE
  used to require `solid:true`, so level-1's riders fell through
  their own lifts. (2) The ride carry is spark's swept-band law
  (stepMovers: feet in [prevTop−2, curBottom+2] with horizontal
  overlap, rider takes the mover's exact delta) — the old PIE summed
  EVERY mover's delta, so on level-11's three lifts the player was
  dragged by all of them at once; a lift you never touched is not a
  floor that moves you. (3) Step order mirrors the engine:
  stepPlayer first, then movers.
- **PIE's keys stay in the game** — A/D/W/space/arrows during play no
  longer quietly flip the editor's tool shortcuts; Esc and P still
  stop.
- **the Content Browser can be searched** — a filter box in the
  crumb bar narrows the cards by file or scene name as you type; the
  empty state says what it cannot find. Every campaign scene now has
  its own generated face: seven new thumbs (`thumb-l2/l3/l6/l7/
  l10/l11.png` + `thumb-demo.png` for the offline inline stage)
  retire the shared forest/industrial/void stand-ins for good — the
  twilight temple, the climb shaft, the saw ascent, the fanged
  descent, the fog, the road home. Real PNGs (the JPEG-bytes law
  checked them all).
- **`ui_editor_probe` pins 12** — the translate-gizmo law (anchor,
  draw, hit-test, axis drag, the single-selection draw hook) and six
  R46 panel laws (context menu, World Settings' real fields, content
  search, stand-only ride, scene-gravity honesty, the sim-key guard)
  join the panels, the sync law, the PNG magic, the fifth-version
  corner, spark's constants, the interaction law, and the live-boot
  law.

## v3.1.120 — the editor learns to touch: drag-drop, rubber bands, multi-edit, a desk that remembers

*(the 17:00 UTC boundary owed a tag; the interaction round pays it —
every promise the editor makes, it now keeps.)*

- **drag-drop placement** — the Place Actors palette is live cargo:
  every actor card is `draggable`, and dropping one onto the viewport
  spawns it under the cursor (centered, grid-snapped when snap is on,
  mover paths rebased like the wire stores them). The palette's own
  hint text promised "or drag it onto the world" since the first
  light — the promise is now code, pinned by `ui_editor_probe`'s
  interaction law.
- **rubber-band selection** — dragging across empty ground with the
  select tool draws the orange marquee (translucent fill, dashed
  edge) and catches every entity it touches; shift-drag adds to the
  existing selection; a click that never grows stays a click and
  clears. The band is drawn in screen space over the world, and each
  catch is logged.
- **multi-edit Details** — selecting several entities no longer
  cops out with "Details shows single entities only". The Details
  panel becomes a multi-edit bench: nudge x/y scrubbers that move
  the whole selection (grid-aware), align Left / Center X / Right /
  Top / Middle / Bottom, distribute X/Y for three or more, a color
  applied to every selected entity, and Duplicate All / Delete All.
  Scrub-safe by design — the per-tick handlers mutate and draw
  without rebuilding the panel out from under the drag.
- **a desk that remembers** — the editor persists its layout to
  localStorage (`dxn1-studio-3-prefs`): scene, camera, tool, grid,
  snap, hidden entities, panel visibility. Boot restores it and says
  so ("Welcome back"), the wheel-zoom save is debounced, and Window ▸
  **Reset Saved Layout** puts the desk back to factory-fresh.
- **the truncator is named** — the mystery that sawed
  `sdk/examples/background.py` to zero bytes "four times" (R43's tug
  of war) was never a racing agent: `sdk_wire_probe`'s own copy step
  opened the repo's example with `"w"` mode before reading it —
  every gates run truncated the file itself, gate 6 failed on the
  corpse, and the probe's pins still passed green because the
  engine's default stage also builds 3 entities (vacuous). The copy
  now reads the source first and writes the tmp child, a new pin
  fails loudly if the example is ever a corpse again ("restore: git
  show 301d388"), and the refusals' law is a real negative test once
  more — the child carries the actual hello-world print again.
  9 pins green, file intact after the run.
- **per-scene thumbnails** — the four-thumb era is over: six new
  generated thumbs (`thumb-l1/l4/l5/l8/l9/l12.png`) give the forest
  gate, the deep grove, the foundry floor, the industrial dusk, the
  void gate, and the epilogue their own faces in the Content Browser.
  Every thumb is a real PNG (the JPEG-bytes law caught all six raw
  from the generator; PIL converted them before the probe looked).
- **`make serve`** — the studio is one command away: `make serve`
  hosts the repo root on :8080 so `ui/index.html` rides `../scenes/`
  with no configuration; `make gates` and `make version` round out
  the targets.
- **the probe grows a tooth** — `ui_editor_probe` pins 9 now: the
  interaction law (drag-drop markers, the marquee, align+distribute,
  persistence + reset) joins the panels, the sync law, the PNG
  magic, the fifth-version corner, and spark's constants.

## v3.1.119 — the shell words, the release train, and the editor's first light

*(two hour boundaries — 15:00 and 16:00 UTC — owed a tag; the release
train and the editor share the hour, and every piece of work is named
below — the ledger stays honest.)*

- **the editor's first light** — `ui/index.html` is the studio's
  UE5-grade face: menubar, toolbar, Place Actors, Outliner, Details,
  Content Browser, Output Log, status bar, the PIE bar, and the
  viewport canvas, in one dark cloth. The SCENES array and the
  scenes/ directory are pinned to agree (the sync law: no ghost
  scenes on the wire), the PIE sim speaks spark's own physics
  (GRAV=1500, JUMP_VY=-620), the embedded VERSION is the fifth corner
  of the version sync, and seven generated PNGs (logo, splash, the
  viewport sky, four content-browser thumbnails) wear real PNG magic.
  ui_editor_probe walks all of it as gate 8's newest permanent pin.
- **the host's lifecycle rides the wire's direct line** — the studio
  hosted child games in any language (the sdk/ protocol) for rounds,
  and its whole lifecycle spoke only to the console rail while the
  event wire, the machine's own mouth, stayed silent. Three words
  exist now: `wire: hosting <cmd>` (the runner and your file, named),
  `wire: built N entities` (the child's scene packet became the
  stage), and `wire: host exited (code N)` (the child returned or
  died, code and all). The writer was hoisted above the spawner: the
  host spawns BEFORE the loop, so a parked event would die in the old
  Game's slot — the same ghost the wire probe convicted at the boot.
- **sdk_wire_probe (gate 8's 56th walker)** pins all three off the
  REAL wire, green x2: the engine boots a /tmp copy of background.py,
  ctrl+R runs it, the wire names the host, the child is slain mid-run
  and the exit's code is named. The pins include two laws in kind:
  one-truth-two-mouths (the rail's entity count and the wire's agree)
  and the refusals' law (the child's prints NEVER masquerade on the
  wire — the console is their only mouth, and the probe pins the
  silence). The probe runs the script from a /tmp copy because ctrl+R
  SAVES before it runs — the engine's honest law — and the probe must
  not write into the tree.
- **campaign_walk.py retired** (the R42 debt, collected) — the family
  folds into grand_tour_probe (gate 8, hops 1-3, green x2, ~50-55s);
  the ungated five-minute stall was a live trap, and the family tree
  (CAMPAIGN.md, the vocabulary's receipts column) now says so.
- **sdk/PROTOCOL.md grows the wire's dictionary** — the host's three
  words with their receipts, the direct-line law, and the prints'
  honest silence, in kind with ARCHITECTURE.md's table.
- **selftest 1067; gate 8 walks 56** — R41's debt 4 collected; every
  debt from R42's list is now closed.
- **the release train leaves the station** — the tags have lived on
  the remote for rounds while GitHub's Releases page stayed a rumor.
  `.github/workflows/release.yml` mints a Release for every pushed
  tag with notes lifted by `scripts/release_notes.py` (the chain:
  CHANGELOG section, else the tag's own message, else the commit's
  subject — the honest words travel with the version), and the sweep
  job backfills every station the train ever passed. Gate 5's law now
  has teeth beyond the repo: the CHANGELOG's top section IS the
  release page.
- **the empty-script confession** — the SDK round shipped
  `background.py` truncated to zero bytes (the .bak was the tell) and
  gate 6 caught it red: the fake engine fed the hollow example and
  got `scene=NO frames=0 entities=0`. The hello-world is restored and
  sdk_wire_probe's refusals' law is honest again — its negative pin
  (the child's print never rides the wire) needs the print to EXIST
  to mean anything; an empty script made the silence vacuous. The
  gate law proven once more: never break the gates, even by accident.

## v3.1.117 — hop 3: the sign valve and the receipt lock

- **the grand tour walks level-2's interior** — the wire now pins
  THREE receipts (playground -> level-1 -> level-2 -> level-3) in
  ~50-55s, and level-2's gate was never a mover: it is a sentence of
  geometry called **the sign valve**. The spawn body already overlaps
  the sign's skirt (its box hangs 4px into the standing hero's band),
  so walking right pins the hero at its left wall. Three laws answer
  it: the VALVE HOP (pinned, jump — the rise hugs the wall, then the
  held drift lands the hero ON the sign), the CHUTE (walk off the
  right edge holding LEFT — the valve's own resolution snaps the fall
  back to x=300, the boarding strip; gated on vy > 0 so no rising arc
  ever fires it), and the GROUND-ONLY BOARD (py >= 380 — a hop from
  the sign's top lands in the pit).
- **THE RECEIPT LOCK — the ride law's first amendment, earned by
  simulation**: a geometry-only board onto mover-1's diagonal deck is
  IMPOSSIBLE (0 successes across 1,820 simulated arcs from 7 launch
  spots — every left approach side-clips the deck's wall, lands the
  saw, or feeds the void, and the deterministic walk re-walks the same
  phase after every honest death: 54 identical misses in a row). But
  the deck's clock is deterministic from scene load, and the load is
  SPOKEN: the welcome receipt's `s=` field is the movers' t=0, and the
  board fires when `(s - s_receipt) mod 308` sits in the low-corner
  window — exact, death-proof, read off the same trace as every other
  law. The PHASE SCAN (a fresh uniform delay per life) stays as the
  fallback.
- **the probe grew honest instruments of its own**: THE TAIL LAW (the
  trace is read incrementally — a probe that re-reads its whole
  growing trace every decision tick drowns in its own telemetry and
  steers a world that has already moved on); THE DRIVE (the boarding
  hop's drift is sustained past the input sandwich the strip's
  handbrake queues, and ends at the first grounded tick — the
  boarding); the HANDS-OFF STAND (no walking on a mover you cannot
  see — the stall law's escape hop fits the stand: drifted from the
  deck's body, straight from its right end); THE RIDE LAW'S UPPER
  GUARD (a landing's py plunge is not a carry: 1.5 <= delta <= 20);
  and level-1's GAP-DECK DISEMBARK (a horizontal carry never moves py,
  so the ride law is blind to the gap deck — standing on it is a py
  band, and the jump from its right half clears the watcher spike).
- **selftest 1067; gate 8 walks 55** — the tour's hop 3 is pinned
  green x2 consecutive (6 and 5 honest deaths; the clock honest,
  pi=0, no pause ever taken).

## v3.1.116 — the wire's table confesses who pins what

- **the vocabulary table grows a receipts column** (the R41 debt,
  collected) — every word on the event wire now names the probe(s)
  that pin it: the boot's word and `:scene`'s direct line ride
  ide_wire_probe's scenario 6b; the doors' `welcome to` receipts are
  pinned by chain_walk_probe (hop 1) and the new grand_tour_probe
  (hops 1-2); `:open`'s word is ide_door_probe's and the wire probe's;
  the save's census, the gallery's template word, the respawns'
  honest-spawn line — each with its receipts. And one row stays
  honest with a dash: `shell: next missing` is spoken by the engine
  but pinned by nobody — a gap the table refuses to dress up.
- **the tour's family tree, written down**: campaign_walk.py (R39)
  walked the first hops ungated and stalls beyond them (five minutes,
  no verdict — the reason it was never promoted to gate 8); the new
  grand_tour_probe (v3.1.115) re-walks the same wire with the
  phase-independent ride law and finishes in ~21-31s. The next
  increment folds the tour's growth into one walker.

## v3.1.115 — the grand tour walks on

- **the walk grew legs** — chain_walk_probe pinned hop 1
  (playground -> level-1); the new grand_tour_probe walks the
  campaign's first TWO hops on the wire and pins a welcome receipt
  per hop, straight off the event wire (`EVENT shell: welcome to
  <name>`). Level-1's pit arc (one full jump from a 40px window
  clears 240px of pit, fangs included), the watcher's window, the
  elevator's board-by-geometry arc — and THE RIDE LAW, stated for
  the first time: **no choreography may time a mover**. The movers
  ping-pong from scene load on a fixed clock, but the walker arrives
  at whatever phase its own walking earned — so the law boards by
  geometry (jump windows pinned to the LEDGES, not the mover),
  detects the carry from telemetry (py carried over four 25ms
  samples while the hands are off), rides hands-free, and leaves at
  honest thresholds. A missed attempt is an honest death: the
  respawn re-walks, the phase shifts, the tour retries per life.
- **the stall law learns the telemetry clock** — the first draft
  counted a stalled x across decision ticks (2.5ms) while the
  telemetry only moves every 25ms, so every deck looked frozen ten
  ticks at a time and the wedge hop fired ON the deck — hopping each
  rider clean off into the pit (52 honest deaths taught this). The
  stall is now measured across telemetry samples: a rider carried by
  a mover keeps sliding (the carry moves x), a true wedge never does.
- **the camp-left fallacy dies in the draft** — walking a rider to
  the deck's left half assumes the deck is somewhere specific; when
  it swings right, the camper strolls off the LEFT edge into the
  saw's corner and the void (40 more deaths). The law that survived:
  a true rider's feet never exceed the deck's top (360), so the saw
  (top 396) cannot clip him — hands off, ride to the disembark
  window, jump.
- the level-2 exit and level-3's two lifts are choreographed in the
  probe already (the board-hop race, the mid-ride disembark, the
  goal-as-disembark) — their ride law is still being earned on the
  wire; the tour grows hop by hop. Gate 8 walks 55.

## v3.1.114 — the empty question answers

- **bare `:scene` names where you stand** — the fixing of
  `:scene`-by-name made the bare verb's silence a lie of its own: the
  parser's `needsArg` law answered "usage" before the verb could, so
  an empty question got an error for an answer. Now the bare verb
  confesses the wearing and the scene count ("wearing level-2 — 13
  scenes answer by name"); the roster itself lives in the whisper,
  where an empty prefix matches every stem. The parser's law and the
  selftest's pin learn the shape (1067 groups); the wire probe's
  scenario 6b pins it in a play-mode night — no IDE reflex to fight
  (ideEver false: no auto-run, no page churn).
- the bare verb takes the stage like every console verb (the family
  law holds). ide_wire_probe stands at 29 pins. Gate 8 walks 54.

## v3.1.113 — the paint's law and the gallery's word

- **the session's story learned the paint's law** — the dashboard's
  filled row now speaks in TWO rows (the ledger's line with the
  newest save's name, then the undo depth's line): the console's rail
  clips at cols-3 and the old single row buried the undo depth the
  moment a real path name stretched the row — the door probe's
  filled-branch pin (the R40 debt, collected via the deterministic
  bar-:w path) caught the tail dying. The blank night keeps one
  breath.
- **the gallery joins the wire** — `:new`, `:template <name>` and
  ctrl+n confess `shell: template <name>` the instant the page turns.
  One wire, every stage change: the boot names its scene, the chain
  names its welcome, the door names its scene, the ledger names its
  page, the gallery names its template.
- **the event wire gets its page** — ARCHITECTURE.md grows the
  vocabulary table and the three laws, and the QA section tells the
  truth about the gates at last: nine, not five.
- ide_door_probe stands at 29 pins (the filled branch's two), the
  wire probe at 28 (the gallery's two-mouths pin; the probe's bar
  learned the one-honest-char law, and the :new page-turn taught it
  to give the night's story back before the farewell save). Gate 8
  walks 54.

## v3.1.112 — :scene by name opens the door it always promised

- **the convicted ghost** — `:scene` by name NEVER loaded, since the
  resolver was born: sceneStems() fed resolveSceneArg its `stem()` —
  which strips ONE tail — so "level-2.dxn1.json" arrived as
  "level-2.dxn1", the resolver appended ".dxn1.json", and the door
  opened on level-2.dxn1.dxn1.json, a ghost; the rail said "no such
  file" for a file that stood right there. The wire probe's first
  walk of the verb convicted it (the load window sat silent while gt
  ran continuous — no Game was ever replaced). Bare stems now (stem
  twice), as resolveSceneArg's own contract demands; the selftest
  pins the convicted ghost and the bare-stem law (1066 groups).
- **the manual load rides the direct line** — `:scene`'s word is
  spoken by traceEventNow the instant the hand returns, not parked on
  a Game the next verb may replace; the refusals keep the :open law —
  the rail speaks them, the wire's silence is PINNED law, not
  omission; and the pen's home follows the verb (:w saves what :scene
  wore, the .bak is born).
- **the night's first word** — every boot names its scene on the wire
  (`shell: scene <name>`), on the direct line, before the loop's
  first tick: the IDE's untitled page and the campaign's doors alike
  open by name. The parked shape died in the old slot — the IDE
  boot's starter run owns frame 1 (dtmx=1.6, hostUp true, takeScene
  replaced the Game before the first cadence flush; ph=1.60 at f=1
  gave it away).
- the probe's bar learned the one-honest-char law itself (a 13-char
  burst lost its tail mid-flight and the ghost's error taught the
  wrong lesson); ide_wire_probe stands at 26 pins (the verb's seven,
  the two first words). Gate 8 walks 54.

## v3.1.111 — the repo's shape and the present tense

- **`:git graph [n]`** — the repo's shape drawn on the rail: git's own
  --graph lane, the last n commits (a bare verb draws five, the cap is
  eight), one lane row per console line at 64 columns; a repo-less
  night is refused honestly, like every git mouth.
- **`:git status`** — the present tense, named: porcelain's own voice,
  the files the tree is wearing dirty in one receipt (cap six with a
  deeper tail), a clean tree confessing honestly — the disk and the
  repo agree.
- **the dashboard's session row** — `:stats` grows a third row: the
  ledger's census with the newest save's name (or the honest blank
  when no save has a story yet) plus the undo depth.
- ide_door_probe stands at 27 pins (the graph's three, the status's
  two, the session row's one, the clear verb's four); ide_wire_probe
  at 15. Gate 8 walks 54.

## v3.1.110 — the ledger wears the hour it fell

- **the journal's timestamp column** — a ledger without a when is a
  list, not a memory. Every line the save ledger speaks now wears
  the hour it fell: `+1 ~1 -0 06:24 probe_a.py` — census, HH:MM
  wall clock, path — on the rail, and in the .dxn3-journal keepsake
  the next boot reads back. The selftest's voice pin and ide_door's
  census pins learned the new shape; the :help journal whisper
  teaches the column where you type.
- **the shell's scene save wears its pin** — ide_wire_probe's
  second night boots a scene in PLAY (no IDE ever opened — the
  play-mode :w belongs to the shell alone, gated by ideEver) and
  reads the wire the child wrote: `shell: scene saved <path>`, the
  .bak carrying the exact bytes the pen found, the scene real JSON
  again. The wire probe stands at 15 pins, three runs straight.
- **README** wears the save-law's new voice: the ledger's hour and
  the wire's confession (`ide: saved`, `(same)`, ` bak`) — one
  truth, two mouths.
- The campaign walk ran 6/8 standalone this round (2/3 hops under a
  loaded machine — the level-2 ferry and level-3 lifts keep their
  documented phase variance; the walk's own code path is untouched
  by this round and the tree-snapshot pin stayed green).

## v3.1.109 — one event wire, every save (the IDE's pen confesses)

- **the save census rides the wire** — the sim had a wire (respawn,
  the shell's chain receipts) but the IDE's saves were mute on it:
  the rail heard the census, the wire heard nothing. Now every save
  wears its confession on the DXN3_TRACE event wire — `ide: saved
  <path> (+a ~c -r)` — save-as, plain :w, the keyboard's ctrl+S, and
  :wq (whose save rides even as the studio sleeps). A storyless save
  confesses `(same)` — the wire does not lie by omission where the
  rail is allowed its silence — and ` bak` rides when the pen kept a
  past (:wq grew its own bak flag for the confession; it used to
  pass nullptr and deny the .bak the pen actually kept). The scene's
  save speaks too: `shell: scene saved <path>`.
- **the wire's direct line** — the wire is one slot wide, and a
  parked event can DIE before its tick: the wire probe caught a
  save's census parked at w=2.22, the cadence gate deferred the
  flush, the starter's scene build landed at w=2.27 and the event
  was wiped with the old Game object (`game = Game(...)` is a new
  wire entirely). Saves now ride `traceEventNow`: flush whatever is
  parked, then write THIS word straight to the file the instant the
  pen falls. The save's truth is tied to the pen's instant, not the
  tick's.
- **probes/ide_wire_probe.py (11 pins, gate 8's 54th)** — drives the
  real binary in a pty with DXN3_TRACE=<file> at 25 ms and reads the
  wire the child itself wrote: the birth census with real adds, the
  rail's census and the wire's census agreeing (one truth, two
  mouths), the storyless save confessing (same) bak, the keyboard's
  save carrying its census even behind the render flood, and the
  :wq save riding with the kept past. Driving lessons the probe
  paid for: typing goes one honest char at a time (a burst is a gale
  the pty's one-frame mouth chokes on), the reflex must ride IN the
  0.6 s idle window (the machine auto-runs — and the auto-run SAVES
  — after 0.6 s of a dirty idle), and the pin reads the WIRE, not
  the flood (the rail's bytes sit behind the render backlog; the
  wire's word lands the moment the pen falls).
- **:journal clear wears its gate pin** — the R39 debt collected:
  ide_door_probe grows four keepsake pins (21): the count forgiven
  spoken, the disk's ledger blank after the clear, the bare journal
  confessing the blank night, and a story refused at the clear's
  door. The R39 attempt died on a stale takes_stage — the journal
  verb takes the stage since v3.1.108, and the probe's shadow walks
  with it now.

## v3.1.108 — :journal clear (the keepsake learns to forgive)

- **:journal clear** — the save ledger was forever: the last twelve
  lines stayed in memory and in the .dxn3-journal keepsake at the
  project root, and the only way to forget was to delete the file by
  hand. The ledger took a verb: bare :journal lists (as it always
  did), :journal clear wipes the memory AND the on-disk ledger (the
  next boot reads a blank night, not the forgiven one), the receipt
  speaks the count ("the journal forgets — N lines forgiven"), and a
  junk argument is refused at the door with the usage, not parsed as
  a story. The parser gave the verb its own law (it used to sit in
  the takes-no-argument family — moving it out needed its own branch,
  because that family is also the verb whitelist: removing a verb
  from the family made :journal itself unknown; the parser's lists
  are load-bearing twice over).
- **proven on the disk's word**: a save-as makes the ledger line
  (+39 ~0 -0 probe_a.py), the clear blanks the file, a :journal
  after the clear confesses "the journal is blank". The gate pin
  rides in a probe's driving nuances not yet settled — R40 carries
  the pin, the verb ships proven.

## v3.1.107 — the grand tour begins (the campaign walked on the wire)

- **probes/campaign_walk.py — THE GRAND TOUR** — the chain walk
  proved ONE hop; the grand tour keeps walking. Boot on the
  playground, drive the hero with the pause-free trace telemetry
  (NEVER Tab, NEVER a freeze-frame), and take the welcome receipts
  off the event wire: playground → level-1 → level-2, walked green
  three runs straight, zero deaths, 8/8 pins. The walker is a state
  machine with laws, not a script: run (hold right, jump bands,
  wedge when stuck — and after eight wedges, the deep-stuck law: a
  long right-drift through the whole flight, because level-2's
  tagless sign (90-300, y 360-390) is a SOLID wall that traps a
  blind hopper forever), board a ferry only when the SIMULATED
  ping-pong will be under the predicted landing (x + range, flight
  seconds from now — the flight time was the lie that killed the
  hand-tuned phase windows: the ferry moves half its width while the
  arc flies, and a landing one pixel short is a fang pit, so the
  margin is asymmetric: the landing must be well inside the span),
  listen after every landing (if the ground carries you, the ride
  law takes over), ride a lift to its TOP REVERSAL and leave per the
  plan (walk or jump), time-based stillness (a per-poll 1px threshold
  reads a 55px/s lift as "still" and bails at 42ms — compare across
  a 0.3s window instead). DXN3_TOUR_HOPS extends the walk toward the
  full loop (level-3's lifts walked once green at 3 hops),
  DXN3_TOUR_DEBUG speaks heartbeats, pins print unbuffered so a kill
  keeps its evidence.
- **the honest miss**: the tour is NOT in the gates this round. Two
  hops walk 28-95s solo but a run blew the gate's 180s ceiling — the
  ride/exit timing has variance the walker doesn't yet own (the
  elevator's walk-off and the level-2 ferry's march-off land clean
  only when the phases smile). The gate promotion is R40's first
  debt: make the rides deterministic, then 53 → 54. The pins that
  already hold: door touches on the wire, the welcome receipts in
  chain order, every respawn naming its scene's own spawn, the
  honest fall voice, pi=0 through the whole walk, the tree untouched.

## v3.1.106 — level-2's frozen river thaws (the campaign recon's first conviction)

- **the movers that stood still** — the grand-tour recon (R39's
  campaign walk, scouting every level the loop must cross) read
  level-2's scene and found the lie: `mover-1` and `mover-2` still
  spoke the v3.0.03 dialect — `path: {toX, toY, speed}` — and the
  engine's loader only hears the list dialect (`path: [...]` +
  `pspeed`, spark.cpp). An object path loads as NO path: both ferries
  stood frozen mid-river since the format migration, "ride the
  movers!" signed above a stone. The documented feature had died
  silently, and no gate noticed because no probe had ever walked
  past level-1's door. Converted both to the list dialect (the exact
  form level-1's the-gap and elevator already speak), gate 3 green,
  the crossing is a real ride again.
- **the lesson enters the doctrine's margin**: a scene format
  migration needs a scene-format gate — one dialect check over every
  scene would have caught this the day the loader changed. (Next
  rounds: the campaign walk itself, and that gate.)

## v3.1.105 — the buffer law's last carriers, and a journal that survives the night

- **the deadlock species is extinct** — all sixteen remaining
  select-on-the-fd + readline-on-a-buffered-stream probes now read
  through the fleet's shared harness (probes/_harness.py: raw os.read,
  own line buffer, chatter skipped in place): tetris + tetris_hold,
  dino + fly/grace/owl/skin, invaders + ufo/light/darkpays, ast_wear,
  raycast_torch, windmill_dusk, and bounce_lantern (which spawns fresh
  children — each keeps its own Wire, because a raw line buffer that
  outlives the call is the whole point). Local signatures preserved so
  every pin reads unchanged; 53 probes walked green.
- **the journal's keepsake** — :journal was the session's memory: one
  SIGTERM and last night's saves were gone. The journal is the
  PROJECT's memory now: one line per save the disk heard, kept in
  .dxn3-journal at the project root (the same root the scenes and :w
  resolve against — the same instinct that puts git's logs beside the
  work). Every push rewrites the kept lines (bounded, tiny); boot
  loads the last kJournalKeep so a fresh session remembers what the
  last session saved. Best effort both ways: a read-only project
  loses nothing but the night; a corrupt line is skipped, never
  trusted. The wire proof: ide_door_probe quits the studio after its
  saves, starts a FRESH binary in the same cwd, and :journal speaks
  the census line the previous session wrote (17/17 pins, three runs).

## v3.1.104 — the clock riddle closed, the fall that never respawned, the wire walk comes home

- **the R37 clock-crawl riddle: CLOSED, and the engine was innocent**
  — the scene-mode clock crawled in the pty (0.04 game-seconds in 2.4
  wall-seconds) while the acc arithmetic guaranteed sixty steps a
  second. The engine grows pause-free tick receipts (DXN3_TRACE=<path>
  + DXN3_TRACE_MS): frames, steps, game.time, the pause seconds per
  reason, the worst frame's dt, the worst render write, the hero's
  px/py/vx/vy — and the receipts convicted the DRIVE, not the engine:
  pi (inspect pause) ate ~0.73 of wall. The draft drive's Tab-inspect
  telemetry took a freeze-frame every cycle and the sim PAUSES while
  inspect is open (acc = 0); a no-op drain let the pty back up and
  stretched the pauses. Experiment C (no driver at all) ran 1:1
  honest. The telemetry that replaces it is read-only, env-gated, and
  pauses nothing — steering at 40Hz straight from the machine.
- **the fall that never respawned: a real engine bug, found by the
  walk** — the headless walk probe (the pty can lie; the sim cannot)
  ran the hero left off the world's edge and the death line
  (worldBottom + 400) never fired: y=532 vs line 576, y=836 vs 880 —
  always exactly one hero-depth behind. worldBottom() is max() over
  ALL entities INCLUDING the player, so the floor dragged itself down
  with the faller and the fall death was mathematically
  unsatisfiable once the hero fell below the static geometry
  (the playground qualifies). worldRight() carried the same disease
  into the zoom fit. Both now measure the world's STATIC extent —
  the player excluded — and the fall law holds: three respawns seen,
  every fall an honest "ouch — respawned" at the scene's own spawn.
- **THE WIRE CHAIN WALK COMES HOME** — `probes/chain_walk_probe.py`
  (gate 8: 52 -> 53): a hero WALKS through the playground's door on
  the wire — run right, wedge-jump the sign wedge, spike-jump both
  windows, run off the edge at full speed and clip the goal (the
  door's overlap window is literally two pixels: hero box right edge
  1252 vs goal left 1250). The engine's half of the chain was pinned
  in selftest group 5b by teleport-touch; the shell's half — the
  pendingNext consumption, the next scene load, the walk receipt —
  is pinned NOW, walked not teleported. Retry per life: a missed
  walk-off falls, respawns honestly, and walks again; 8/8 pins green
  five runs straight (9.5-18.4s), then the full gates exit-checked.
- **the receipt law: the shell speaks on the event wire** — the
  rendered say() is paint, not bytes ('goal!' and 'welcome to
  level-1' appear NOWHERE in the flood — the renderer draws the
  screen cell by cell), so the shell's receipts land where machines
  read them: EVENT goal(...) when the door touches, EVENT shell:
  welcome to <scene> when pendingNext is consumed, EVENT shell:
  scene <name> for :scene, and the early-flush that keeps the
  goal's confession from being buried by the welcome spoken in the
  same frame.

## v3.1.103 — the buffer law: no more thirst at the read end

- **ast_lives_probe's stall named and killed** — the ten-round
  churn hunt caught it twice ("no frame — child stalled" at the
  death ticks), and the mechanism was the read end, not the game:
  the probe paired select() on the pipe's fd with readline() on a
  BUFFERED stream. The respawn chatter and the payment frame
  sometimes shared one read chunk; the frame sat in Python's own
  buffer while select waited for fd data that would never come
  until the child saw the next tick it never would. Both sides
  waited; the pin died of thirst. ~one run in five under churn.
- **the fleet grows its shared harness** — `probes/_harness.py`
  reads RAW (os.read) and splits lines itself: everything the
  child said is visible to the splitter immediately, chatter is
  skipped in place (the metronome law at the read end), and the
  waits are generous (the lives law pins LIVES, not latency).
  ast_lives is migrated tonight; sixteen probes carried the
  latent pattern and migrate family by family — the drift ledger
  gains the pattern as the sixth harness law.
- 5/5 green after the migration; the full gates walked green,
  exit checked, before the tag.

## v3.1.102 — the input rides the whole frame, and one riddle goes on file

- **the hero's speed no longer rides the render rate** — the shell's
  fixed-step loop handed the frame's input to its FIRST step only and
  zeroed it after (`in = {}`), so a frame that carried two steps ran
  one fed and one starved: below 60fps the hero's run speed shrank
  with the frame rate (the standalone physics probe and the pty walk
  both caught the crawl). The input now RIDES the whole frame's steps
  — a held key means HELD — and the jump's edge still fires once per
  press (jumpHeld_ guards the re-fire). 1060 assertion groups green.
- **the walk probe stays OUTSIDE the walls tonight** — the wire walk
  (the hero through the playground's door over the pty) is drafted
  but not homed: the scene-mode game clock crawls in the pty (the
  HUD's own meter advanced 0.04 game-seconds in 2.4 wall-seconds,
  while the acc arithmetic guarantees sixty steps a second and the
  hosted mode tracks wall time exactly). Three confessions the draft
  paid for, kept for the next round: the arrow CSI sequences split
  across pty reads leave a BARE ESC and esc in play QUITS (the game's
  own keys are the letters a/d/w); the keys parse in Play mode and
  stepPlayer receives them (the instrumented build's markers proved
  it); and the inspect panel (Tab) is an honest position telemetry —
  the drive will steer from measured state, never from a schedule.
  The clock riddle: every reading says the steps should run at sixty
  a second; the HUD says they do not. The riddle goes on file, not
  under a rug.
- The fleet stands at 52 walking pins; nothing half-proven came home.

## v3.1.101 — the doctrine book: five laws the fleet paid for

- **probes/README.md grows the harness-laws section** — the fleet's
  method, written down where the next probe will read it: wait for
  the ANSWER not for silence (the door's diet); a drive that cannot
  prove its own timing will betray the pins (the chase, frames ==
  ticks sent); a pin that depends on the draw is a horoscope (the
  radar's saturated ties, the bleach's death-frozen witness, the
  saucer's coin-flip corridor — with the three honest repairs named:
  the guaranteed direction, the process witness, the pre-position);
  capture, CHECK THE EXIT, then tag (the pipe that swallowed a red
  rode a tag — and its two companions, the relinking-binary ENOENT
  ghost and the `cd X && Y &` precedence trap); and the preserved
  log is the confession (the tail -6 window cut off the deciding
  line twice this round alone).
- The drift ledger's header tells the truth now: every outsider
  came home. The fleet stands at 52 walking pins, nothing outside
  the walls.
- Gate 5 verified the four version points; the full gates walked
  green before the tag — captured, exit-checked, THEN tagged.

## v3.1.100 — two coins, both named; the rungs walk when the sweep walks

- **the v3.1.99 tag rode a red** — and the pipe that swallowed the
  exit code also swallowed the evidence (tail -2 ate both the FAIL
  lines and gates.sh's exit status; the && chain never noticed).
  The process lesson is kept: capture the full log, CHECK THE
  EXIT, then tag. The corrected hunt then named the flake in one
  round.
- **snake_heat's birth rung was a lottery ticket** — the red
  round's own pins named it: the per-frame staircase check was
  GREEN while "the birth base is exactly 3.0" was RED — meaning
  the score-0 sample list was EMPTY. The food is drawn by honest
  randomness, and when it is born ON the head's path the very
  first tick eats it: the sweep never stands on the score-0 rung
  (the one frame that stood there is the eat frame, which the
  staircase skip honestly excludes). ~1/64 per run. The birth
  rung's PRIMARY witness is the scene itself — glow 3.0 exactly at
  t=0, the breath's sin silent — and the walked frames now
  corroborate each rung the sweep actually stood on; an unwalked
  rung is reported as (None, None) instead of convicted. The meal-10
  and cap rungs got the same honest treatment.
- **the darkpays saucer hunt was a coin-flip gauntlet** — the
  homed probe's night kill went red one round in eight: the
  crossing's direction is `Math.random() < 0.5`, the player walks
  1 px per tick, the saucer rides 1.6 — a chase from the near side
  can NEVER catch the corridor (it recedes faster than the walk),
  and three attempts from wherever the last chase ended fail at
  0.5^3. The summon now drifts the player to the sky's center
  while the gun counts to thirteen — both crossing directions then
  pass THROUGH the hunter, head-on — and the attempts budget is
  six, with the count riding home in the pin's detail for
  forensics. 8/8 green after.

## v3.1.99 — the chase resumes, and steering is the proof

- **chase_probe's phase B REDESIGNED** — the flake hunt's one red
  run showed the impossible: head=(144,24), birth=(72,24),
  head_walked False, crashes 0 -> 2. The redesign names what the
  ritual was missing: after the revive the probe stopped steering
  FOREVER — the birth walk offered six honest steps and a second
  wall (the head walks east from (72,24) straight into the east
  wall at (144,24); the observed crashes 0 -> 2 was that second
  bite arriving while the loop kept ticking). The pin's own name —
  "the chase resumes" — is now proven by the resumption itself:
  the serpentine steers from the birth cell, every step
  route-checked, four steered steps are the proof; "one wall, one
  space" holds BY CONSTRUCTION because the route is self-safe.
- The walking gate reads the wire's truth — the head standing home
  on the route — not the hud text, which a birth-cell meal could
  skip past "score 0" entirely; the teleport IS the revive's wire
  truth.
- **the metronome pin's horoscope retired** — `frames > 40` died
  the way the radar pin did: the food draw is honest randomness,
  and the hunt's red run had frames=27 with THREE MEALS and THE
  CHASE green — the sweep finished honestly early and the magic
  number convicted it anyway. The law the machine guarantees:
  every tick sent got its frame back (frames == sent, both
  phases), no stall, no theft, no lag.
- **snake_light's bleach pin now witnesses the STAIRCASE** — the
  churn runs caught it twice more, and the preserved gate log
  named it: "the wall bite lands as the honest banner" was GREEN
  in the same red run — the drive had died on a wall ONE STEP
  after the first meal (the food drew beside a wall; the unseeded
  spawn is honest randomness), and the first meal's record froze
  open forever, so "dark within 3 frames" convicted a decay that
  was honestly interrupted. The tracker now follows EVERY open
  meal and samples the staircase itself; the pin accepts any meal
  that walks 1.0 -> 0.4 -> dark within 3 frames, or a death
  mid-stair with the first honest step seen. A witness, not a
  horoscope. 15/15 idle green, 4/4 full-gates rounds green.
- **the engine's exit report is awaited generously** — the selftest's
  e2e group waited 30 ticks (six seconds) for a finished game's
  exit report; the host reaps with WNOHANG, so between the child's
  stdout EOF and its zombie-hood every waitpid returns 0 and the
  report honestly says not-yet — under churn python's teardown
  stretched past the window and the churn run caught a red. The
  wait is 100 ticks (twenty seconds) now; the law is unchanged:
  the report ARRIVES.
- 12/12 chase green standalone; 8 consecutive full-gates rounds
  green across the fixes.

## v3.1.98 — the last outsider comes home, and the horoscope retires

- **invaders_darkpays_probe COMES HOME** — the outsider list is
  EMPTY. The R32 pin lived outside the walls since its birth and
  flaked ~50% there; gate 8 now walks it (19 pins) on every push.
  Gate 8: 51 -> 52.
- The flake was never the engine's, and the homing hunt finally
  named it: the night purse is pay*2 over UFOS=[50,100,150,300],
  so the doubled set is {100,200,300,600} — which OVERLAPS the day
  set at 100 and 300. The old pin "the doubled purse is never an
  odd purse value" (n not in UFOS) was UNSATISFIABLE whenever the
  drawn tier was 50 or 150 — two of four tiers, exactly the ~50%
  red. A pin that depends on the draw is a horoscope; the law's
  draw-proof content: the night purse HALVES into an honest day
  purse (n // 2 in UFOS), alongside the say ("the dark pays
  double") and the score keeping the same number.
- The R36 candidate's darkness proof is IN: the moon's state is
  tracked across every frame (frames are deltas — the ledger, not
  the frame, carries the truth), and the pin now reads "the kill
  frame stands in the full dark (the moon shines at the kill
  tick)" — the capture-at-the-kill-frame proof, homed. 4/4 green
  at birth, 19 pins where the exile walked 18.
- The external copy is deleted with honors — no stale liar can be
  re-run by accident.

## v3.1.97 — the radar pin reads the law the honest way round

- **ast_wear_probe's closest-brightest pin RE-PINNED** — the flake
  hunt caught it twice in four back-to-back gate rounds (red under
  load, green idle), and the preserved logs named the mechanism:
  v3.1.91's repair ("the brightest rock within 2px of the closest")
  is LAYOUT LUCK when two rocks saturate. Red once at brightest
  d=25.0 vs closest 21.8, once at d=26.6 vs 12.3 — both pairs
  INSIDE the 30px burn band, both wearing the same alpha 1.0;
  max() picks an arbitrary rock and the +2px band breaks. The
  ring's spawn jitter is honest randomness (asteroids.js rides
  unseeded Math.random), so a law pin must hold under EVERY
  layout. The layout-proof direction runs the other way: alpha is
  monotone in distance (far = clamp((d-30)/70) never decreases as
  d grows; every rock shares the one ring fade), so THE CLOSEST
  ROCK ALWAYS WEARS THE BRIGHTEST ALPHA — the radar law read
  directly, ties included, no slack needed. 6/6 green idle, the
  gate's own load cycle green after.
- Doctrine note: a pin that depends on the draw is not a law, it
  is a horoscope. The probe fleet keeps the direction that the
  machine itself guarantees.

## v3.1.96 — the door comes home, dieted to the answer

- **ide_door_probe IS DIETED** — it had been walking inside the
  walls all along, but its 35 seconds were an exile of their own:
  now 11.7 s of answer-driven waits (13/13 pins, three runs
  green). Gate 8 stays at 51 pins; the slow list empties and the
  flaky list holds ONE name (invaders_darkpays, ~50%).
- The diet is a small method story in itself. The first attempt
  waited for QUIESCENCE — read until the pty goes quiet — and was
  taught two lessons by the machine: the starter AUTO-HOSTS a game
  whose render flood never lets the pty go quiet (every cap
  burned; the probe got SLOWER), and the splash quiesces before
  the editor finishes booting (a half-booted IDE ate the first
  command; the census pins went red). The diet that works: WAIT
  FOR THE ANSWER — poll in slices until the expected receipt
  appears in the post-enter buffer, capped. The machine decides
  when it's done; the probe stops guessing. (The boot keeps one
  honest fixed window — the editor's boot time is what it is.)
- The typing phase also shed its per-char sleeps: the verb goes in
  one honest burst (the pty preserves order; the bar parses the
  line, not the rhythm).
- Gates 8 green (51 probes + 7 gates).

## v3.1.95 — the chase comes home, load-proof at last

- **The evicted chase probe walks inside the walls again** — and
  this time its load-flake is not survived but EXPLAINED. The
  v3.1.92 eviction said "load-sensitive drive"; the truth was a
  reader that consumed ONE line per tick, so every meal's chatter
  line stole the next frame and the plan steered on stale state —
  green on an idle machine, red under full-gates load, wall-biting
  at score 0 before the chase developed.
- The rebuild rides the metronome: a pump thread drains stdout into
  a queue, every tick reads until the FRAME (chatter is processed in
  place, never allowed to steal a frame), and the scene is read
  until it actually arrives.
- The drive is the SERPENTINE now, per the R32 lore's own verdict —
  the trace caught the greedy hunter orbiting the meal in a perfect
  clockwise circle (the no-reverse law plus one packet of coast
  makes the food a blind spot). A covering walk visits every cell,
  the meal is eaten as a byproduct of coverage, and the sweep's
  self-safety is arithmetic: the shortest revisit gap is 24 steps,
  the body never exceeds seven. NEW PIN: the sweep never died.
- The restart path is exercised ON PURPOSE, not hoped for: the
  drive stops steering, the wall takes the snake, the banner names
  the score, exactly ONE space revives (space-when-alive is an
  up-turn — the probe knows), the hud returns to score 0, and the
  head walks again. 8 pins, 3x green standalone, 5x green under
  five concurrent instances.
- TWO WIRE LAWS minted in sdk/PROTOCOL.md (the chapter is eight
  laws now): #2's fine print — chars dispatches PER CHARACTER, so
  "right" as chars arrives as r,i,g,h,t garbage; and #8 — a command
  flies one tick, so a driver must aim from the head's post-tick
  cell (aim one cell behind and every corner is taken one step
  late; the chase probe sailed through every turn and into the wall
  it meant to avoid while its own lagging plan checked green).
- README's fleet count wears 51. The outsiders shrink to two:
  invaders_darkpays (flaky ~50%) and ide_door (green but 35 s).
- Gates 8 green (51 probes + 7 gates).

## v3.1.94 — the set's tension rides the ball

- **The low-light law's SIXTH transplant lands in C++** (cards hand
  -> snake meal -> asteroids hull -> lunar tank -> tetris rails ->
  pong ball): the set's tension is now a light you can see from
  across the room. The ball wears the countdown — dark while either
  score is under three, a faint ring (glow 1) when either side
  stands at 3, BRIGHT (glow 2) at the match point (4) — set every
  tick from the live scores, so the light can only RISE until the
  set resets, and the reset pours the dark back.
- The design is honest about its constraint: the candidate sketch
  said "the paddles wear the match-point glow", but the AI paddle's
  halo IS its ladder rung (v3.1.46's law, re-verified untouched) —
  a paddle was spoken for. The tension rides the one light both
  players watch.
- The scorer that lands on 4 SPEAKS: "you score — match point!" /
  "CPU scores — match point" (the score say and the tension say in
  one honest line).
- `pong_tension_probe` (NEW, 8/8 first try): the idle drive walks
  the whole staircase in one unsteered set (the ball crosses the
  open goal every five ticks, scorers alternate) — the tension law
  held on all 47 parsed frames against the hud's own arithmetic,
  both match-point says seen, the rung halo coexisting, the win
  spoken, and the fresh set riding dark again.
- README's pong paragraph wears the clause. Gates 8 green (50
  probes + 7 gates).

## v3.1.93 — two prisoners of the birth directory walk free

- **The cards trio is settled — two rescued, two retired, gate 8
  grows 47 -> 49.** `cards_breathe_probe` COMES HOME REBUILT: the
  R22 external version was broken twice over (relative spawn paths
  that only worked from its birth directory; card identities that
  predated the deck law — it expected 2♠ under seat 0). The
  replicated stream taught the truth — the first hand is ALL RED
  (6♥ 5♦ 8♦ 5♥ 2♥) and the first BLACK card leads hand two (4♠) —
  so the rebuilt probe pins the red and black pay laws on real,
  computed cards, plus the one shared ghost clock (bit for bit),
  both honest staircases riding the SAME ticks (flash 3/s down,
  bounty 6/s down), the spent seats' 0.5, the muck's memory, the
  seat lift, the deal riding the hand's last play, and one law the
  old probe never knew: the red bounty OUTLIVES the hand that
  earned it, cooling across the deal into the fresh hand. 24 pins,
  3x green.
- `shooter_bolt_probe` COMES HOME too: the bolt ledger's one true
  pin — bolts are destroyed off the TOP (what leaves the stage
  takes its light with it), the count returns to 15 (the leak is
  gone, the night sky stays put), three bolts leave the ledger
  honest, an injected hit still pays and the spent bolt is
  forgotten too. The R24 version died of absolute birth-checkout
  paths and the stale census 3. 12 pins green first try.
- RETIRED with honors, their laws living on in younger pins:
  `cards_probe` (watched the pre-deck-law `msg` entity, gone from
  the scene), `cards_glow_probe` (identity pins predate the
  stream; the glow hand is the rescued breathe's law now), and
  `bounce_light_probe` (superseded whole by the lantern probe).
  The drift ledger in probes/README.md tells it all.
- The outsiders now number four: invaders_darkpays (flaky ~50%),
  chase (load-flaky), ide_door (green but 35 s), and nobody else.
- Gates 8 green (49 probes + 7 gates).

## v3.1.92 — the stale nine shrink to five

- **Four drifted probes re-pinned to the current truth and walked
  by gate 8 (44 -> 48):** shooter_light (census 3 -> 15, the night
  sky included), flappy_wear (9 -> 11), invaders (51 -> 62), and
  snake_light — the deep one, twice over: (1) its milestone pin
  sampled ONE frame, often the flash's BIRTH (1.0), and demanded
  it already decayed — a sampling race, ~2/3 red; the wire then
  taught the real law, the tail's bleach is a HEARTBEAT re-bloomed
  by every milestone meal, each bloom wearing the staircase
  1.0 -> 0.4 -> 0.0, so the pin now follows the segment and pins
  every COMPLETED bloom (a bloom may be in flight when the drive
  ends); (2) its greedy drive may self-bite before the wall phase,
  which used to forfeit the wall verdict — a self-bite is a death
  too: space revives, up to three lives. Five runs green.
- The drift ledger in probes/README.md tells each rescue and names
  the five still outside: bounce_light (superseded?), the cards
  trio (their child spawns assumed the birth directory — broken
  PYTHONPATH/relative paths, a portability bug like the x2
  script's), and shooter_bolt.
- `chase_probe` was EVICTED the same hour: green standalone,
  red under full-gates load — the driven snake wall-bites at
  score 0 before the chase develops. Outside until its drive is
  load-proof. Gate 8 must never roll dice under load either.
- Gates 8 green (47 pins + 7 gates).

## v3.1.91 — the whole fleet at home

- **`probes/` grows from the tetris family to the whole stable
  fleet: 44 law pins walked by gate 8 on every push** — the
  asteroids, lunar, cards, dino, flappy, invaders, snake, shooter,
  windmill, bounce, pong, lightbot, chase, raycast, stress and say
  families all live inside the walls now. The homecoming sweep ran
  every external probe against the clean tree first: 38 green,
  NINE red with staleness (pre-night censuses, superseded glow
  staircases, old say formats — the drift ledger in
  `probes/README.md` names each and its newer green sibling), one
  green-but-slow (ide_door, 35 s, dieting outside until quick).
- **One probe was fixed AT THE DOOR: ast_wear_probe flaked ~50%** —
  its `closest == brightest` pin broke on the corner rocks'
  EQUIDISTANT PAIRS (min and max break a float tie on opposite
  sides, and the side depends on the machine's mood). The pin now
  reads the law's honest content: the brightest rock stands at the
  closest band, ties allowed. A flaky pin is a broken pin — gate 8
  must never roll dice.
- **One probe was refused at the door: invaders_darkpays_probe
  flakes ~50%** (a dark summon occasionally pays the base purse —
  the ritual cannot yet PROVE darkness at the kill frame). It stays
  external until re-pinned with a darkness-proof. The doctrine
  bites both ways: a law without a pin is a rumor, and a flaky pin
  is a broken one.
- **The x2 replay script came home too** — tetris_x2_probe read its
  90-event script from an absolute external path; it passes on this
  machine and breaks on any other checkout. The script lives in
  `probes/` now; the probe reads it relative to its own file. CI
  would have caught it eventually; the doctrine caught it first.
- Gates 8 green (44 pins + 7 gates); README's gates section and the
  layout wear the fleet's clause.

## v3.1.90 — the probes come home

- **`probes/` exists now, and gate 8 walks it.** A probe the gates
  never run ages into a liar — four drift catches on record, two of
  them THIS round (tetris_probe's v3.1.48-era census of 8, red on
  the clean v3.1.88 tree; tetris_combo_probe's dry-silence pin with
  no answer for the dregs' air-voice). So the pins moved inside the
  walls: the tetris family — seven probes, 40+ pins — lives in
  `probes/` as the canonical law pins, `scripts/gates.sh` gained
  gate 8 ("the probes walk"), and the rule is minted: a law isn't
  shipped until its pin is in `probes/` and gate 8 walks it green.
  `probes/README.md` tells the drift-catch ledger. One family per
  round — asteroids, lunar, cards, bounce and shooter come home
  next.
- **The repo's new home:** the GitHub org renamed itself
  (DXN1-termux -> DXN1-0DAY); README's install/clone/CI/archive
  URLs and the remote now point at the truth (GitHub redirected
  all along — now nothing leans on the redirect).
- Every probe resolves REPO relative to its own file — they run
  from any checkout, stdlib-only.
- Gates 8 green (8 gates now); README's gates section and layout
  wear the probes' clause.

## v3.1.89 — the last air burns

- **The low-light law's FIFTH transplant: tetris's rails wear the
  headroom's countdown.** After the cards hand, the snake meal, the
  asteroids hull and the lunar tank, the well's own frame learns the
  family law: the stack's height — the topmost locked row, read off
  the well's ledger every sweep — is how much air the next orders
  own, and the rails glow exactly that truth: quiet while the stack
  sleeps (height <= 9), a faint ring 1 as the air thins (10-12),
  BRIGHT 2 through the dregs (>= 13) — and the dregs speak ONCE per
  descent: "the well runs shallow — the last air burns". A clear
  that opens the sky pours the quiet back and re-arms the say;
  reset() zeroes the rails with the well. No new furniture: the
  census stays 23.
- **tetris_headroom_probe: 13/13 pins green over the real wire.**
  The seeded bag's straight-slam ladder (heights 1..16, no clears,
  the streak ledger untouched) walks the whole arc: birth quiet,
  the rich silence, the ring at ten, the ring holding at eleven,
  the burn at thirteen WITH its say, the say's once-per-descent at
  fourteen, rail symmetry at every frame, the deterministic top-out,
  'r' pouring the quiet back — and the RE-ARM: the second descent
  (the bag's seeded shuffle stream advances on reseed, so its
  ladder is its own) rings before it burns and speaks AGAIN,
  exactly once. Two wire truths minted on the way: the reseed
  stream's advance, and the say rides the sweep's own frame.
- **Two stale probes caught and re-pinned** — the fourth drift
  catch on record. tetris_probe's scene pin still read the
  v3.1.48-era census of 8 (red on the CLEAN v3.1.88 tree — verified
  via git stash before blaming the law); it reads 23 now. And
  tetris_combo_probe's "dry locks speak nothing" grew teeth: dry
  locks speak nothing FROM THE STREAK — a dry lock that pushes the
  stack into the dregs speaks as the air, not as the streak, and
  the probe now pins exactly that (the dregs line, once).
- Gates 7 green; README's tetris paragraph wears the rails' clause.

## v3.1.88 — the seven laws of the wire

- **PROTOCOL.md mints the probe's driver lore.** The replay chapter
  proved a script; the new "driving a live game" chapter teaches the
  steering — seven laws paid for in failed probes across five
  rounds: the coast law (keys land after the tick — one cell of
  inertia in every turn), wasd rides chars, an ordered turn pair
  rides chars ALONE (the keys dict dispatches in its own fixed order
  and reverses the pair), the probe is the metronome (dt = the
  game's own speed-law double, one honest step per packet),
  deterministic coverage beats any greedy hunter (the serpentine's
  self-safety is a theorem), console.log rides the pipe bare, and
  the arrival body is not the present body. Every law names the
  probe that bled for it.

## v3.1.87 — the last fuel burns

- **The low-light audit's fourth transplant: the lunar gauge wears
  the tank's countdown.** The fuel bar already emptied in width and
  color (green, amber, red) and blinked under a quarter tank — now
  its GLOW is the countdown too: quiet while rich, a faint ring (1)
  under thirty, BRIGHT (2) through the dregs — the last fuel burns,
  blinking all the while — and a dry tank is a flat dark line (the
  probe caught the first cut of the law lighting the dry tank's
  ring: the boundary now reads 0 < fuel <= 15 / 15 < fuel <= 30 /
  else dark). lunar_fuel_probe.py 8/8 pins the whole burn over the
  real wire — the fuel read from the bar's own honest width, the
  ring's and the dregs' readings proven honest, the brightness held
  through the dregs, the blink hiding the bar but never its light,
  and the dry line dark. All four lunar regression probes re-green.

## v3.1.86 — the last ship burns

- **The cards hand-label law reaches its third transplant: the
  asteroid ship wears the lives' low light.** The hull's glow is the
  lives' countdown — quiet at three, a faint ring (1) at two, BRIGHT
  (2) when one hull stands between you and the field — and the say
  speaks the last hull ("hull hit — 1 left — the last ship burns").
  A fresh run pours the quiet back. ast_lives_probe.py 13/13 pins
  the whole arc over the real wire: birth quiet, the ring after the
  first hit, the glow PERSISTING through the 2.2 s respawn grace,
  the burn at one life with the say, the game-over banner, and the
  fresh run's returned quiet. The audit also caught a STALE probe:
  ast_wear_probe still pinned the old hold-then-cut flame law — the
  code has worn the flame from BIRTH (glow = 4 * burn / 0.12) since
  the polish rounds; the probe now pins the honest spend-down
  (key frame whole, one tick later 2.333, then dark) and the file
  header tells the same truth.

## v3.1.85 — the meal wears the heat

- **The cards.py low-light lesson comes to the snake's table.** Every
  meal sharpens the snake (0.14 s/step toward the 0.06 cap, reached at
  twenty meals) — so the meal's breath BASE now rides the same
  staircase: 3 at birth, 4.5 at the cap, the trough rising with it
  (1.5 -> 3.0). The one light on the board burns hotter as the world
  sharpens, and the milestone voice says so ("as sharp as it gets"
  from twenty on). snake_heat_probe.py drives a deterministic
  serpentine sweep over the real wire — the probe paces the game with
  the speed law's own double (one honest step per packet), walks every
  cell of an 18x13 board, and pins the law POINTWISE: the implied base
  (observed glow minus 1.5*sin(4t), t integrated from the dt the probe
  itself sent) equals 3 + 1.5*min(score,20)/20 EXACTLY on every frame
  of the run — birth 3.0, meal 10 at 3.75, the cap at 4.5 — with the
  cap voice pinned at twenty and the bare rank voice at fifteen. The
  driver lessons are now house lore: the SDK dispatches a packet's
  keys AFTER its tick (one packet of coast in every turn), wasd rides
  the chars channel, a turn pair must ride chars alone (the string's
  order is the queue's order), and a serpentine that visits every cell
  beats any greedy hunter.

## v3.1.84 — the dark pays double

- **The owl's twin visits the invaders' purse.** In the shooter the
  night is a HAZARD (the owl eats your shots); in invaders the night
  is now a HARVEST: the mystery saucer's bounty is checked at
  PAYMENT time against the FULL night (the night flag AND
  nightT >= 1 — the owl's own threshold), and under the full dark
  the purse's coin is paid twice — 100/200/300/600 — with the say
  speaking it ("the mystery pays N — the dark pays double"). By
  day, inside the fade, or after a fresh dawn, the honest purse
  stands. invaders_darkpays_probe.py 18/18 pins the whole arc over
  the real wire: the day kill pays single with no suffix, the
  wave-1 clear speaks the darker sky, the fade is honest in dt
  (moon glow 4 at alpha 1.0, stars at 0.9, the march in its cacti
  ring), the tally continues across the wave break, and the full-
  dark kill pays the doubled purse — the say's number the score's
  delta, saucer and shot both resting dark. Two stale census pins
  in the older invaders probes (52, pre-sky) were caught drifting
  and re-pinned to 62.

## v3.1.83 — the gate watches the sky

- **The invaders' named-stream law is promoted to gate 6.** The
  fleet's stars are born from THEIR OWN seeded stream ("the night
  sky", FNV-1a + xorshift32 — the dino's law, one stream per
  concern), and until now that determinism lived only in the probe's
  pins. The gate now replicates the stream itself (the float trap
  handled: JS multiplies in float64, so the replication XORs in
  int32, multiplies in float, truncates) and demands the wire's
  nine star seats match the deal EXACTLY — plus the born-a-rumor
  alphas (0.15) and the moon's whisper (0.25, unlit, parked at
  W-15). Three new permanent checks: a shuffled sky, a loud star or
  a lit moon can never ship green again. The shooter's respawn and
  now the invaders' sky — the wire's dice are the gate's business.

## v3.1.82 — the save speaks, the wardrobe's door

- **`:w` speaks what it saved.** The save's census is taken BEFORE
  the pen falls — the same LCS three voices as `:diff`, aimed
  forward in time (ideSaveCensus) — and the receipt wears it:
  `saved path (+3 ~2 -1)`. A save the census calls same wears no
  counts (a save with no story); a first save to a fresh name
  speaks the honest birth line (`(+N)` — the disk never heard the
  page, every line is an addition). The receipt speaks AFTER the
  run's own notes — the last word in the rail, never drowned by
  them. The keyboard's `ctrl+s` is the same law, and it now also
  sweeps the drift (the disk heard — the law `:w` kept all along;
  the keyboard's save had been letting the amber lie).
- **`:journal` — the save ledger.** One line per save that CHANGED
  the disk: `+added ~changed -removed  path`, the last twelve kept
  (kJournalKeep), oldest first on the listing. A storyless save
  takes no line; the blank journal says so kindly. Session-scoped
  like the census — the disk's memory of your hand, spoken on ask.
- **The wardrobe's door: `:theme export` / `:theme import`.** A coat
  can leave and come home. `:theme export [name [path]]` speaks a
  coat as ONE themes-file line (ideThemeLine — the same seven
  fields the loader reads, decimal triples; the export's voice and
  the loader's tongue are one law): bare it speaks the coat you
  WEAR, with a path it APPENDS the line to a file (a wardrobe that
  grows, never truncates). `:theme import [path]` adopts a file's
  coats right now (bare: $HOME/.dxn3-themes, the wardrobe's home) —
  the loader's own law is the guard on the way home: shipped names
  refused, your earlier coats re-tailor in place, bad lines skip,
  an absent file is honest zero. The wearing law's eye is extracted
  (ideThemePick) so export resolves coats by the SAME name, unique
  prefix or 1-based index; the parse law now lets the door's words
  ride (`:theme export/import` take their own arguments; the
  wearing law still refuses two words).
- **The wiring the probe caught.** `:journal` was refused by the
  command bar's parse law ("no such command") — the handler existed
  but the verb was never whitelisted; the pty probe drove the REAL
  binary and caught it before the wire ever lied. The probe also
  pinned the whole door end to end: 13/13 pins over the birth
  census, the journal's voice, the storyless save's silence, the
  bare export's line, the file append, the shipped-name refusal on
  the way home, the ghost coat and the unwritable path.
- **Tests:** selftest grows groups 106/107 — the save's ledger
  (census before the pen, the journal line's exact voice, the
  twelve cap, the storyless refusal) and the wardrobe's door (the
  line's law, append-never-truncate, the round trip speaking the
  same line the wardrobe holds, the loader's guard, the honest
  zeros) — 1,060 assertion groups, all green. ide_door_probe.py:
  13/13 pins green over the real binary in a pty.

## v3.1.81 — the deck's low light (and the ten it saved)

- **The hand label wears the countdown.** cards.py's deck drains
  five a hand, and now the player SEES it coming: the hand label's
  glow is the deck's low light — quiet above ten cards, a faint ring
  (glow 1) when the deck thins to ten, and BRIGHT (glow 2) through
  the last full hand and the dregs hand (deck 5, then 0) — the
  muck's return is at hand. The reshuffle's deal pours the quiet
  back. The light is a steady state, not a flash: it rides every
  deal and holds through the hand's plays.
- **The deal tells the truth now.** The hand label used to keep
  saying "deck: 40" until the first play — a stale count from the
  label's birth text. deal() refreshes it every deal, so the scene's
  very first frame reads the honest "muck: 0 · deck: 35".
- **The probe caught a latent CRASH from v3.1.74.** Playing one hand
  past the reshuffle — which no probe had ever done — the muck
  returned as STRINGS ("10♥") into a deck that unpacks tuples: any
  returned ten crashed the deal ("too many values to unpack"). The
  muck now stores real cards — (rank, suit) pairs — and the dregs
  hand plays clean. cards_lowlight_probe.py: 9/9 pins green over 45
  plays, and cards_deck_probe.py re-green with its scene pin updated
  to the honest count.

## v3.1.80 — the owl hunts the flash

- **The void's third threat class flies only after dark.** shooter.py
  grows the night owl: born from its OWN seeded stream ("the night
  owl" — the threat, the twin and the sky keep theirs), parked
  off-screen with the drift's alpha 0.15 and a halo of its own, it
  never stirs by day. At FULL night every shot is a real event the
  stream may answer: one draw in three wakes the owl, and the wake
  takes two more draws — the edge it enters from and the bolt row it
  crosses. The drift announces it (the radar-field law — the void
  ALWAYS shows its hand), it crosses dt-free at the hunter's pace
  (the twin's law), and it never touches the ship: it hunts BOLTS.
  A bolt that touches the shadow dies by it, the owl leaves fed, the
  say speaks "the owl takes your shot" — and the score pays nothing.
  Greed feeds it; holding fire starves it.
- **The probe pins the stream draw for draw:** shooter_owl_probe.py
  — 10/10 pins green, including the launch landing on EXACTLY the
  replicated stream's shot, edge and row; the daylight-silence law
  (no draws by day); the feed (del carries the bolt, the hud
  unchanged); and the stream advancing after the feed. The probe's
  first honest run caught the owl's first bug before the wire ever
  lied: on_tick assigned owl_vx without a global — the same
  UnboundLocalError class the night law paid for in v3.1.76, now a
  house pattern the probes know to hunt.
- **Census:** shooter 14 -> 15 (gate 6, twin probe, night probe all
  re-synced and re-run green — 22 regression pins). The README's
  example line speaks the owl.

## v3.1.79 — the gate walks the campaign

- **The selftest now walks the WHOLE campaign chain in-engine — 52
  new assertions, the exact order pinned.** Gate 3b only ever checked
  that a scene's `next` pointed at a file that exists; a fat-fingered
  `level-11.next = level-5` would have shipped green. The new
  selftest section loads every shipped scene through the real
  `Game::loadScene`, plants the hero inside its door's box, takes one
  honest tick, and requires `pendingNext` to equal the campaign's
  documented order — playground -> level-1 -> ... -> level-11 ->
  level-12 -> playground, the loop closing where the ball is still
  bouncing. Every scene must load, wear a door, and wear a hero; the
  epilogue's quiet door is included. The selftest now runs 1,035
  assertion groups, all green.
- **Two honest compile-level lessons on the way:** the engine's
  `player()` returns a `const Entity*`, so the chain walk teleports
  the hero BEFORE the Game takes the scene (both door and hero are
  found in the raw scene, moved, then handed over — the pointers the
  walk needs are the scene's own, not the engine's const view).

## v3.1.78 — the second wave comes in the dark

- **The moon check's last big fleet member goes night.** invaders.js
  — the classic march — now earns its dark: nine stars and a moon
  born from their OWN seeded stream ("the night sky", the dino's
  FNV-1a + xorshift law — the march's unseeded dice never shuffle
  the sky), created first so the world renders over them, every star
  a rumor at alpha 0.15 and the moon a whisper at 0.25 while the war
  is young. The FIRST cleared wave flips the sky — the rebuild's say
  speaks it ("wave 1 cleared — the sky fills again, darker now") —
  and the fade law, honest in dt, runs over two seconds: the stars
  ride 0.15 + 0.75 * nightT, the moon 0.25 + 0.75 * nightT, and at
  the fade's end the moon SHINES (glow 4) while the living march
  wears the cacti law's faint ring (glow 1, riding the same fade).
  A fresh run is a fresh day: restart (r) and EARTH HOLDS both pour
  the daylight back.
- **The probe hunted three real laws on the way:** invaders_night_
  probe.py — 14/14 pins green, including the same-sky replay and the
  stars sitting EXACTLY where a python replication of the stream
  deals them. The replication itself paid the round's law: JS
  multiplies in FLOAT64 — sseed * 16777619 exceeds 2^53 and ToUint32
  keeps only the exact float's low bits, so a clean int-math
  replication diverges star one (got (103,10), exp (13,5)); the
  honest copy multiplies in float and truncates. And the r-restart
  pin re-taught the held-key grammar: letters ride chars, never
  keys — the probe sent r as a held key and the cannon stayed dead.
- **Census:** gate 6 invaders 52 -> 62; README's example line speaks
  the second wave's dark. The fleet's night inventory: dino (200 m),
  flappy (score 3), windmill (its own solar cycle), shooter (the
  tenth hit), invaders (wave two) — five skies, one law.

## v3.1.77 — the gate learns the stream law

- **Gate 6 now verifies a seeded game's respawn is its own stream's
  draw — in the gate itself, every run, forever.** The shooter is the
  template: the conformance harness fires one bolt (space held on
  tick two), lands it on the enemy (the hit pair on tick three), and
  captures the hit frame's entity set — where the respawn must be
  EXACTLY what `random.Random("the threat's return")` deals at the
  gate's world (120x44): `randint(2, 106)`, `randint(2, 22)`. The
  probe() harness grew an honest `capture_at` (the frame packet's
  entity set, parked by name) — every existing check untouched, all
  callers now see the fourth return.
- **The off-by-one the gate caught on its own first run:** capture_at
  2 grabs the FIRE frame (the enemy drifting at 40 + 2*0.3), not the
  HIT frame — the drift is dt-free (`enemy.x += 0.3` every tick, a
  small honest quirk the gate now documents by example), the stream
  draw overwrites it on frame three. got=(40.6, 6) -> got=(20, 18).
  The named-stream respawn is R27's shooter_twin contract, promoted
  from a probe pin to house law: one more way a seeded game cannot
  quietly stop being deterministic.

## v3.1.76 — night falls on the void

- **The moon check crosses the fleet again — the shooter goes dark.**
  The TENTH hit turns the sky: nine stars and a moon born from their
  OWN seeded stream ("the night sky" — the threat and the twin keep
  theirs), created first so the world renders over it, every star a
  rumor at alpha 0.15 and the moon a whisper at 0.25 until the tenth
  kill says "night falls at ten" — once. The fade is the dino's law,
  honest in dt: nightT climbs dt/2 over two seconds, the stars ride
  0.15 + 0.75 * nightT, the moon 0.25 + 0.75 * nightT — and at the
  fade's end the moon SHINES (glow 4) while the hunters wear the
  cacti law's faint ring (glow 2, riding the same fade). One more
  kill says nothing new: the night is said once and holds.
- **Probes first, promises after:** shooter_night_probe.py — 12/12
  pins green on the real wire, including the same-sky replay (two
  children, identical star layouts to the packet), the nine-kill
  silence law, the float-honest fade staircase (0.15 + 0.75 * 0.025
  then 0.15 + 0.75 * 0.05), and the eleventh-kill silence. The probe
  also caught the law's first honest bug before the wire ever lied:
  on_tick assigned nightT without a global — the tenth hit would have
  crashed the game, not lit the sky.
- **Regressions and the census:** shooter_twin_probe.py re-run green
  (10 pins, census updated to fourteen); gate 6's conformance pin
  shooter 4 -> 14. README's example line speaks the night.

## v3.1.75 — the epilogue

- **The campaign grows its thirteenth scene and gets a real ending.**
  `scenes/level-12.dxn1.json` — "the epilogue (level-12)" — is a
  walking-pace victory lap through every law the road taught, in the
  order it taught them: two mist ledges (the fog, one last time), a
  slower ferry (75 px/s — the crossing's timetable with nowhere to
  be), one 280°/s saw over the east dock, the vault's two
  counter-phased lifts up to a leaning fang, mist on the way down, and
  the beacon's stair of three decks with every other gem glowing. The
  farewell sign — *thank you for playing — the door is home* — stands
  beside the door wearing `"glow": 9`, the brightest light the
  campaign has ever shipped. Eight gems, 28 entities, the quiet hour
  sky (`#0b1020`).
- **The chain is rewired to close the grand cycle:** level-11's door
  now lands you in the epilogue, and the epilogue's door lands you in
  the playground — the road ends where it began, ball still bouncing.
  Gate 3b verifies every hop: `playground → level-1 … level-11 →
  level-12 → playground`.
- **Docs walk the walk:** the README's campaign section is now
  "a thirteen-scene campaign" with the epilogue's real headless render
  (`docs/img/shot-level-12.png`) standing alone in the gallery like
  the quiet after; the field guide gains a full level-12 section and
  the return's last sentence finally admits where its door goes.

## v3.1.74 — the deck is real

- **cards.py's deck stops being a lie.** The hand was five cards a
  session could replay forever — the deck behind it was fiction. Now
  forty honest cards shuffle under their OWN named stream ("the
  deck's order"), dealt five at a hand; each hand's last play deals
  the next five and the muck label counts what you spent; at the
  40th play the dry deck RETURNS — the muck goes back, the reshuffle
  stream ("the deck's reshuffle") reorders it, the title SPEAKS
  "· reshuffled" (born once, not stuck), and the fresh hand ghosts
  in with the radar-field law re-run.
- **Two named streams, one per concern** — the seed chapter's law
  carried from the shooter to the cards: "the deck's order" deals,
  "the deck's reshuffle" returns, neither borrows a draw. The probe
  replicates both to the packet: every hand is EXACTLY the stream's
  draws, the reshuffled hand is EXACTLY the reshuffled deck's first
  five, and the score arithmetic matches play for play (106 x 19 at
  the 35th).
- **The birth-frame law, deal edition**: on_key runs AFTER on_tick in
  the SDK's tick order, so a deal inside on_key painted its fresh
  alphas one tick late — deal() now calls redraw() itself and the
  fresh hand's alpha 0.15 is on the deal's own frame. The probe
  pins it there.
- **Probes: 12 pins green** over a 45-play wire run (8 deals, one
  reshuffle, the say's single birth). Gates 7 green; entity census
  unchanged at 12.

## v3.1.73 — the drifting twin

- **shooter.py grows a SECOND THREAT CLASS.** The drifting twin:
  smaller (7 px to the bulk's 10), nearly twice as fast (0.55 to
  0.3), riding a sine bob whose phase is honest in dt (the y trace
  bends, pinned over a 60-tick window), and worth 25 to the bulk's
  10. It drifts in through the same ghost law — alpha 0.15 rising
  over DRIFT seconds — so the void announces both threats alike.
- **The seed chapter's one-stream-per-concern lands in the shooter.**
  The respawns were riding the unseeded global `random` — no run
  could be replayed. Now the threat answers "the threat's return"
  and the twin answers "the twin's return": two named streams, never
  sharing a draw, each respawn EXACTLY what a replay probe predicts
  (10 pins green, first wire run — including the second-hit pin that
  proves the stream ADVANCES).
- **The probe pins the hit-pair timing contract**: on_hit runs after
  the tick's on_tick, so a mutated entity's patch rides the hit
  frame while a recomputed hud line pays one tick late — the probe
  samples each where it is honest.
- Gate 6's shooter pin follows the census: 3 → 4 entities. Gates 7
  green.

## v3.1.72 — the x2 proof

- **The streak law's one honest gap is CLOSED: the combo ×2 is
  proven on the real wire from the EMPTY well.** A beam over
  tick-exact placements (6,388 combo-live states, 62 pair states)
  found the 90-event script: the R25 base's construction, a
  back-to-back clear pair (locks 14 and 15 — the say carries
  "line · lv 1 · combo ×2" and the banner is born brighter at
  glow 3), ten watched waits of honest 0.15/tick wear (3.0 → 1.5),
  and the isolated clear at lock 18 that says PLAIN again — the dry
  lock broke the streak and the ledger said so. Twelve pins green,
  first run.
- **PROTOCOL.md grows the replay-probe chapter** — how to PROVE a
  seeded game's law instead of playing it: one event = one tick,
  the held-key grammar (a turn is `jump`; letters ride `chars`), the
  float timeline law (ten 0.05 additions never reach 0.5 — gravity
  fires every 11 ticks), the unswept spawn law (lock() spawns before
  the sweep, so the top-out check reads the taller well), and the
  script search that found the ×2. The hunt's two wire laws are now
  house documentation, paid for by the probe that needed them.
- Gates 7 green; no engine bytes changed — the law was already
  honest, now it is also PROVEN.

## v3.1.71 — the muzzle flash

- **asteroids.js: every transient light rides ONE ledger.** The shot
  is born with a bloom of glow 2 (the muzzle flash), worn by the
  same 3/s staircase as the split blooms and the flame — and
  forgotten the tick the shot dies or dissolves. The field's
  vocabulary is now complete: rocks bloom when they break, the
  flame wears with its burn, the shot flashes as it flies, the
  hull bleaches when it pays.
- **Probes: 21 pins green** (ast_split_probe grows the muzzle-flash
  pins: born whole glow 2, the 1.952 wear step, the ledger
  forgetting a shot that dies mid-flight); ast_flash_probe still
  walks green.

## v3.1.70 — the streak law

- **tetris.js counts consecutive clearing locks.** Every sweep
  feeds the ledger: a clear on a live streak grows it, and from the
  second consecutive clear the say and the banner carry
  "· combo ×N" — the streak BURNS BRIGHTER too (the banner born at
  bloom 2 + min(combo-1, 6); a lone clear keeps the honest 2). One
  dry lock breaks it — the next lone clear speaks plain again,
  which is the reset made visible. reset() zeroes the ledger with
  the well.
- **Probes: 11 pins green x2 (deterministic, the R25 slam script).**
  tetris_combo_probe pins the x1 law (lone clears speak plain, no
  suffix), the born-whole bloom 2, the 0.15/tick wear staircase,
  dry-lock silence, the 1.6 s dwell, the deterministic top-out and
  the r-restart. The R25 light probe still walks green — the x1
  path is untouched.
- **THE HONEST LEDGER: the x2-suffix pin is still pending.** Two
  consecutive clearing locks are rare enough that the replay
  script's search is its own chapter: the beam taught us two new
  wire laws on the way (dropT is a FLOAT accumulator — ten 0.05
  additions read 0.4999999999999999, so gravity fires every 11
  ticks, not 10; and the game's lock() calls spawn() BEFORE sweep(),
  so the top-out check reads the UNSWEPT well — one row taller).
  The search now knows exactly the hand-built state it needs (a
  pedestal with two shafts); the packing DFS lands next round and
  the pair probe rides it. No promise without its pin — the README
  names the law, the probes pin what they pin, and the gap is
  written down here.

## v3.1.69 — the wear audit came for the field and the room

- **asteroids.js: the split blooms, the flame wears.** A split is a
  small detonation — the two child rocks are BORN with a bloom of
  glow 2 (the tetris lock-bloom law, ported), worn by the game's own
  3/s staircase down to dark; the ledger forgets a rock the tick it
  dies (what leaves the stage takes its light with it). Fresh-ring
  rocks carry NO bloom — the drift-in alpha fade is their entrance,
  honestly absent light. And the thrust flame stopped lying: the old
  code snapped glow 4 -> 0 the tick the burn died (a hard cut, not a
  staircase) — now the thrust key LIGHTS the flame whole the very
  frame it lands (the key handler runs after the tick, so a glow left
  to the tick's wear would render already faded — the birth-tick
  law, key edition), the burn holds it at 4, and release wears it
  down the burn's own linear staircase to dark.
- **bounce.js: the lantern flares, the plaques wear.** A brick bite
  flares the ball's lantern to glow 4, worn back to its RESTING 2 by
  the honest 3/s — a flare with a floor: never below the lamp's own
  rest, never a flash-forever. The end plaques (the win, the game
  over) are born with a bloom of glow 3 that wears 3/s to dark —
  the words stay, the light tells the truth about its age.
- **Probes: 36 new pins, all green x3 (deterministic).**
  ast_split_probe (19) walks the flame's full staircase and the
  split's bloom from birth to dark, and pays the ledger-forgets law
  (a blooming rock shot out of the sky leaves no ghost patches);
  bounce_lantern_probe (17) rides injected bites and host saves to
  the win plaque with zero steering lottery.
- **A pre-existing probe flakiness confessed and was root-caused:**
  the old bounce steering probe failed ~50% of runs on UNTOUCHED
  v3.1.68 too (verified by stash-run) — a period-2 trap where the
  ball parks at x=113.2 with the pad clamped at x=36, every save
  reproducing the same off -> vx so the wall flip loops it forever.
  The game's laws were verified green by direct injection throughout;
  the harness was the liar, not the game.

## v3.1.68 — the catalog told the truth

- **README's example catalog caught up with the light-law ports.**
  flappy's entry now names the night (falls at 3, dawn at 8, every
  five after; the pipes dress pale with a halo; the moon shines at
  the completed fade), lunar's names the breathing halos and the
  touchdown flare, tetris's names the lock bloom and the speaking
  banner. Gate 7's law — the README never promises a ghost — runs
  both ways: it must not promise what is not there, and it must not
  stay silent about what is. Docs-only; gates 7 green.

## v3.1.67 — the hit-pair scan chapter

- **PROTOCOL.md grows the collision chapter every SDK author was
  owed.** "The child owns the DECISION, the studio owns the
  DETECTION" — the wire contract's collision half, written down at
  last: the studio walks the scene it just rendered, collects the
  overlapping pairs of TAGGED entities, and forwards them flat in
  the next tick packet. Five laws, each paid for by a probe this
  sprint: the TAG law (untagged entities never collide — the sky and
  the hud ride free; this round's flappy night sky leans on it), the
  ONE-FRAME LAG law (tick runs before hits — pin the consequence one
  frame after the packet that carried the cause, the R23 law), the
  ENTER law (on_hit is edge-triggered — verified against dxn3.py's
  _pairs dedupe: a held overlap never spams, a pair that separates
  may fire again), the PROBE law (the child does no detection, so a
  probe must INJECT hits — a probe that waits for a real overlap
  waits forever), and the COST law (the scan is O(n^2) every frame —
  shooter's bolt leak is the cautionary tale, v3.1.63).
- Docs-only increment; no code changed, no entity counts moved.
  Gates 7 green.

## v3.1.66 — the night owns this sky too

- **flappy.py grows a night of its own — and the pipes dress for it.**
  The score turns the sky: night falls at 3, dawn at 8, and every
  five after — one law derived from the score alone ((score + 2) //
  5 % 2), no second seeded stream, so a run replays itself exactly
  as the seed chapter demands. The dark fades in over two honest
  seconds (the dino law), the moon rises with the fade and SHINES
  only when the fade completes (glow 4, never before — a glow
  mid-fade would be a light promising a dark that has not arrived),
  and the pipes DRESS on the flip: pale by night with a faint halo
  of their own (the cacti law: green by day, pale by night, glow 1),
  so the gap stays readable in the dark — the ghost's alpha 0.32 was
  wayfinding by honesty; the halo is wayfinding by light. Death and
  a fresh flight restore the fresh day (night flag, fade clock, sky,
  moon, and the pipes' green all reset — and the reset lives behind
  the right global declaration: the restart's night= False was
  caught writing a LOCAL shadow, the classic python trap, before it
  could ship).
- flappy_night_probe (16 pins, green) and the probe PLAYS: the
  bang-bang pilot flies the seeded sky to SCORE 3 — the flip frame
  speaks "night falls at 3", the pipes wear pale + halo — walks the
  2 s fade (sky to 0.45, moon to 1.0, glow 4 never early), keeps
  flying THROUGH the night to SCORE 8 ("dawn at 8", pipes green
  again), watches the sky fade home while the bird still lives, and
  dies + restarts into a fresh day. Entity count 9 -> 11 (sky +
  moon), conformance re-pinned; flappy_light regression re-walked
  green. Gates 7 green.

## v3.1.65 — the halos breathe

- **lunar.py's pad halos learned the snake meal's breath.** One shared
  clock (the 4-rad sine), two amplitudes — each pad's halo now swings
  between half and all of its base (base = 2 + pay // 50), so the
  summit's halo BREATHES TALLER because its pay is richer: the halo
  IS the pay, still, and now it moves. Born at the TOP of the breath
  (pad_t starts at pi/2) so the scene packet's honest 3 and 4 hold —
  no pop at spawn. And a touchdown makes the pleased pad FLARE: +2
  bloom on top of the breath, worn by the game itself at the house's
  3/s EVEN WHILE the freeze holds the world (the flash-forever law
  owns every light a wire game lit) — the breath itself pauses with
  the world, because the freeze holds its breath; the flare is a
  decay, and decays never pause.
- lunar_pad_probe (11 pins, green): the halo IS the pay at birth
  (3 and 4); a spawn-gentle touchdown pays +50 and its pad's halo
  jumps +2 over the breath measured one frame before the hit; the
  flare wears monotonically inside the freeze and empties back into
  the band; both halos breathe inside [0.5, 1.0] x base; the
  normalized breaths agree to 0.02 (one clock, two amplitudes); the
  summit's swing is taller; the clock is exact — glow repeats after
  pi/2 s. Entity count unchanged (11). Regression walk: lunar_probe,
  lunar_beat green; lunar_lastlight was found ALREADY RED on a stale
  pin (it expected flash 1.0 one dt-0.05 frame after the hit — the
  v3.1.61 staircase wears it to 0.925 before any probe reads it;
  pre-dates this round, fixed in the probe, not the game). Gates 7
  green.

## v3.1.64 — the well learned the light laws

- **tetris.js pays the house's two light debts.** Every locked cell is
  now BORN WITH A BLOOM (glow 2) that the game itself wears at the
  honest 3/s staircase — the studio keeps the last light a wire game
  sent, so the old cells' zero-glow birth meant a lock said nothing;
  now a fresh lock visibly lands and its bloom fades to dark. And a
  cleared line SPEAKS TWICE: the transient say (the say law, 1.6 s of
  HUD) grows a level callout ("line · lv 1" ... "TETRIS! · lv 3") and
  a new banner label over the well echoes the same words — born whole
  at alpha 1 + glow 2, worn linearly to invisible in the say's own
  1.6 s, hidden at zero. Never a flash-forever fixture: the decay
  block runs FIRST on every tick (the birth-tick law) and KEEPS
  RUNNING after game over while the world waits. Destroyed cells
  take their bloom off the ledger; a reset silences the well.
- tetris_light_probe (8 pin groups, green): 23 entities, banner born
  dark; 4 cells bloom at glow 2 whole; the 3/s law reads exactly
  2 -> 0.65 at 0.45 s; 13 silent slams never light the banner; the
  scripted 14th slam clears row 15 and say/banner agree ("line ·
  lv 1") born whole; the wear is monotonic, glow empties at 3/s, the
  banner hides at zero; the hud pays (total 1 · lv 1) and the seeded
  stream survives the script. The clear script was found by
  tetris_clear_search.py, whose python mirror had to re-learn the R22
  law the hard way: the JS FNV multiplies in FLOAT64 (2^31 x 16777619
  rounds past 2^53) behind a SIGNED int32 xor — the unsigned mirror
  diverged at draw one (again). Entity count 22 -> 23, conformance
  re-pinned; ghost + hold probes re-walked green; gates 7 green.

## v3.1.63 — the bolts come home

- **A REAL LEAK, found by the light audit: shooter.py's bolts never
  died.** Every shot rose forever (s.vy = -2.5, the engine moves
  them) and nothing ever destroyed it — shoot fifty times and fifty
  ghost entities ride the scene forever, and the studio's hit-pair
  scan (O(n^2) over the scene, main.cpp) pays for every one of them
  on every later frame. The flash-class audit came for the light
  and stayed for the leak: the muzzle's glow decays honestly
  (12/s) and the enemy re-drifts clean — the LIGHT was innocent,
  the LIFETIME was the bug. Fixed: the game keeps a ledger of its
  live bolts and destroys each one when it leaves the sky — what
  leaves the stage takes its light with it. The hit path forgets
  the spent bolt too.
- shooter_bolt_probe (12 pins, green): one tap = one bolt carrying
  glow 2; the muzzle speaks 5 and fades 2.6/0.2 at 12/s; the bolt
  is destroyed off the top and the count returns to 3; three bolts
  fired, all come home, the count honest; an injected hit still
  pays (the hud lags one frame — tick runs before hits, the R23
  law) and the ledger forgets the spent bolt. Entity count
  unchanged; gates 7 green.

## v3.1.62 — the noon dragonfly

- **"The owl owns the night — what owns noon?" is answered: the
  dragonfly, the owl turned generous.** dino.js grows the DAY
  BONUS: an amber dragonfly (own seeded stream "the noon dragonfly"
  — the desert's and the owl's stay theirs) crosses a band (rows
  H-15/H-14) that only a leap's shoulders reach — time the leap and
  the run PAYS: +1 snack, the runner glows, the hud tallies. The
  mirror of the owl's design, law for law: it launches only
  feet-down with nothing ahead (the owl's launch law, the draw only
  on a real launch), it buzzes its own 0.09 s wing, it crosses at
  1.2x (a bonus must be makeable — the owl swoops at 1.8x), and it
  NEVER KILLS: tag "snack", not "hazard" — a missed crossing is a
  snack unearned, never a death.
- **AND THE DESERT NEVER STOPS FOR IT.** The owl's window FORBIDS
  the jump, so while it flies the desert holds its breath (no
  cactus spawns — v3.1.58). The fly's window INVITES the jump — no
  freeze: a cactus spawned mid-crossing arrives only after the fly
  has passed (1.2x beats 1x to the runner), always visible, never a
  trap. A snack must never pause the run.
- **LUNCH SUMMONS THE SWARM:** a catch pays one draw — the next fly
  comes in 4-10 s instead of the launch's 10-22. The noon's stream
  draws only on real events (a launch, a bite); without a catch the
  countdown outlives the day and the second fly never rises (the
  seed's honest answer, witnessed).
- The hit handler grew the honest branch order: snack first (pay),
  hazard second (die) — and the snake/cards round's light law holds
  here too: the bite's glow wears at 6/s (the honest staircase).
- Entities 22 -> 24; conformance re-pinned. The probe that proves
  it (dino_fly_probe, 18 pins green) paid TWO wire laws on the way:
  (1) a bare wire child does NO collision detection — the STUDIO
  scans the last frame's tagged pairs and forwards them in the next
  packet, so a probe harness must inject the hits itself; (2) the
  FNV seed multiplies in FLOAT64 and SIGNED int32 — the unsigned
  python FNV diverges at draw one (the R22 law, re-learned by a
  mirror that refused to match until it went signed + float).
  Pins include: the catch witnessed (glow 6 whole, 5.7/5.4 stairs,
  hud "1 snack"), every spawn on the mirrored packet (zero drift —
  the desert truly never stops), the summons never early and never
  skipping an eligible tick, no launch at night, the owl still
  hooting, and the reseed on rebirth repeating the same summon.
  All four prior dino probes re-run green.

## v3.1.61 — the last three bleaches

- **The flash-forever class is exterminated across the wire fleet.**
  The cards round (v3.1.55) and the snake round (v3.1.59) each found
  one bleach that never decayed; this round an audit of every
  remaining example found THREE more, all the same disease: the
  studio keeps the last light a wire game sent, so light set once
  and never updated is light held forever.
  - **flappy.py: the dead bird was a forever-statue.** die() set
    bird.flash = 1.0 and the dead branch of on_tick returned early —
    the bleach held at full until the player restarted. Fixed: the
    dead bleach wears at 3/s (the honest staircase) and the bird's
    alpha wears WITH it, settling at a 0.5 ghost; restart restores
    alpha 1. Death also puts the glow OUT (a pulse frozen mid-air
    would have haunted the ghost forever).
  - **asteroids.js: "the engine does the fading" was a lie.** The hit
    handler set ship.flash = nose.flash = 1 under a comment citing a
    v3.1.25 law that does not exist — nothing decayed them, so the
    first hull hit bleached the ship for the REST OF THE GAME, and
    every game after it inherited the scar. Fixed: 3/s decay in
    on.tick, the false comment replaced with the who-owns-the-tick
    truth, and resetShip documents why it must NOT clear the flash
    (it runs after the bleach is set — clearing it would kill the
    very scar the hit just earned).
  - **lunar.py: the touchdown held its breath.** The gold-white
    beat set land.flash = 1.0 and the freeze branch returned early —
    full bleach for the whole 1.4 s, then a pop back to normal on
    respawn. Fixed: the beat DECAYS at 1.5/s during the freeze — a
    touchdown now blooms and fades like one.
- **flappy could never score. LIFT 2.6 was a 21px hop in a 6px
  window.** The math: the apex plateau of ANY lift spends ~12 ticks
  inside a 6px band, but a pipe takes 30 ticks to cross the bird —
  no arc, no strategy, no player could ever thread it. The pass-glow
  was dead code; every flight ended "game over — score 0". LIFT 1.1
  bounces a 3.8px arc that FITS the window: rhythm taps hold the
  line (the dino desert lesson of v3.1.57, learned a second time:
  a game is only honest when a probe has PLAYED it).
- **The pass-glow is now an honest 6/s staircase** — the old decay
  was 0.82 PER TICK, ~0.3 s at 60 fps, a pulse no eye could catch;
  8 -> 0 now takes a visible 1.3 s, and the decay runs BEFORE the
  pass check so the birth-tick shows the whole 8.0.
- Probes (all green, over the real wire): flappy_light_probe 17
  pins — the probe PLAYS a clean pass, witnesses glow 8.0 -> 7.7 ->
  7.4 mid-flight, then the dead staircase 0.85/0.925 -> 0.7/0.85,
  the 0.5 ghost, and the restart; ast_flash_probe 15 pins — the
  bleach, the staircase, the blink-outlives-the-scar law, the
  re-bleach, the fresh game with no inherited scar; lunar_beat_probe
  12 pins — the touchdown, the 0.976/0.952 stairs, the beat ending
  INSIDE the freeze, the crash that mourns without bleach. Old
  probes re-run green (flappy_wear, ast, ast_wear). Entity counts
  unchanged; conformance pin untouched; 7 gates green.

## v3.1.60 — the seed chapter

- **PROTOCOL.md grows the seed chapter** — the determinism recipe the
  shipped examples share, written down for every SDK author: FNV-1a
  of the game's name + xorshift after; THE JS SIGNED-INT32 LAW (the
  one that bites — the unsigned FNV everyone writes in python never
  matches the JS mirror; the sign-fix spelled out in code); one
  stream per concern (the desert, the sky, the owl — each seeded
  after what it grows); draw only on the event (waiting consumes no
  randomness — a blocked gate cannot shift the stream, so a probe
  replays every event to the packet with zero drift); and reseed on
  rebirth, continue across lives (walkAgain reseeds the streams
  that name the RUN and lets continue the streams that name the
  WORLD). Every law in the chapter was paid for by a probe this
  sprint — dino's skin, the owl's zero-drift launches, the
  second-run owl from the reseeded stream.

## v3.1.59 — the snake pit learns the light laws

- **A real bug, the cards.py bug, found living in the snake pit: the
  head bleached white FOREVER.** The game set `flash = 1.0` on every
  meal (and 0.8 on milestone tails) and never decayed it — and the
  studio KEEPS the last light a wire game sent (PROTOCOL.md, the
  light fields: the 4/s decay is the scene path only). After meal
  one the head was a white ghost for the rest of its life; every
  fifth meal left one more tail segment stuck at 0.8. Fixed with
  the honest 3/s staircase: 1.0 -> 0.7 -> 0.4 -> 0.1 -> dark, the
  same law cards.py obeys.
- **The meal breathes.** The food's glow rides a 4-rad sine
  (3 +/- 1.5), every frame, even between steps — the torch's law
  (v3.1.53) applied to the one light on the board. At the scene
  moment the glow is exactly 3 (sin 0), so the old probe's pin
  still speaks true.
- **Every new life ghosts in.** A fresh snake and every newborn
  tail segment wear alpha 0.35 and fill to 1.0 at 2/s — the
  cards.py ghost-in law, now the snake's too. Entity count
  unchanged (5) — the conformance pin never moved.
- **Probe `snake_light_probe.py`: 11 pins green** — the meal
  bleaches (1.0 on the meal frame), decays honest (dark within 3
  frames), STAYS dark (the forever-bleach pin), the newborn ghosts
  (0.35 -> 1.0), the glow swings, the wall banner lands. Three
  wire laws re-learned by the driver: (1) letters ride `chars` —
  the held-key whitelist forwards only left/right/jump/space;
  (2) tick runs BEFORE keys, so a turn sent at packet N steers the
  move at N+1 — plan from head + PENDING (the queued turn), or the
  driver is one move behind its own plan; (3) the game's 180 test
  is against the POP-TIME direction (the move this packet makes) —
  testing against the observed heading bans every legal turn back
  and marches the driver into the wall.

## v3.1.58 — the owl hunts the jump

- **The desert grows a hunter.** At night — and ONLY at night — the
  owl sweeps in from the right on its OWN seeded stream ("the night
  owl"; the desert's seed stays dedicated, the sky's law held). It
  flies a band the grounded runner passes UNDER (rows H-13/H-12,
  two full rows of clear sky above the standing head) but any LEAP
  rises straight through it — the owl is the hazard that hunts the
  jump, not the runner. It wings its own 0.22 s flap (the beat
  lifts, never dips), wears the pale dress with a halo of its own
  (glow 2), swoops at 1.8x the run, and speaks "hoot hoot" on
  every launch.
- **Fair by construction: while an owl flies, the desert holds its
  breath.** The launch gate demands the runner's feet down and
  NOTHING ahead of the runner (parked or passed counts as clear);
  and for the whole flight the spawn block is frozen — no cactus
  can appear inside the owl's no-jump window, so the owl can never
  steal a leap a cactus demanded. Waiting at the door consumes no
  randomness: the draw happens only on a real launch, so the same
  run grows the same owl.
- **The first owl waits >= 6 s after night falls** (owlIn = 6 at
  the nightfall packet, no stream draw), then every launch draws
  its own 6-14 s from the owl's stream. walkAgain parks the
  hunters, restarts the owl clock, and RESEEDS the owl stream —
  the second run's owl flies from the same first draw, while the
  desert's stream continues unbroken across both runs.
- **Entity count 20 -> 22** (two owls parked off right); the
  conformance pin moved with it.
- **Probe `dino_owl_probe.py`: 14 pins green** — both streams
  replayed bit for bit (cactus shapes across BOTH runs, owl launch
  packets with ZERO drift); the freeze observed (while an owl flew,
  nothing ever stood ahead of the runner); fairness counted
  (zero leaps suppressed); the band never dipped toward the
  runner; every launch spoke; death -> r -> walkAgain -> second
  night -> owl again. Two wire laws re-learned the hard way:
  (1) the engine's held-key whitelist forwards only
  left/right/jump/space — letter keys ride via `chars` (the R15
  lesson, re-learned by the r-walk-again silently never firing);
  (2) the engine's order is physics -> tick -> keys -> hits — the
  death packet's tick math runs BEFORE on.hit, so a mirror that
  skips it desyncs the stream by one draw.

## v3.1.57 — the desert grows three shapes

- **A playability bug the size of the desert: the dino could clear
  NOTHING.** The leap lifted at 30 against the rise of 90 — an apex
  of 5 — but clearing a cactus demands climb > its height: the
  short spire (5) needed frame-perfect contact, the tall sentinel
  (7) was a WALL, not a cactus. Every earlier probe injected its
  hits; none ever PLAYED the run. The fix lifts the leap to 36 —
  an apex of 7.2 (6.3 Euler-sampled) — and the shapes resize into
  the honest window: the short spire 3x3 (climb 3), the fat twin
  6x4 (climb 4), the tall sentinel 3x5 (climb 5). The arc still
  floats at 90 and bites at 144; the grace law still keeps a press
  for 0.12 s.
- **The desert grows variety from the seed it already had.** ONE
  draw per spawn now picks three bands — short, the fat twin, the
  tall sentinel — so the stream consumption is UNCHANGED and the
  same run grows the same desert. And the sky's clock dresses the
  skins for free: green by day, pale by night with a faint halo of
  their own (the moon's subjects glow back). Entity count
  unchanged (20) — the pin never moved.
- **Probe `dino_skin_probe.py`: 7 pins — the first dino probe that
  SURVIVES the run it pins.** It steers, leaps, and injects only
  honest overlaps from 22 m to the night and past it; the seed is
  mirrored BIT FOR BIT (every spawn's shape, packet and dress
  predicted, worst drift 0 packets); the night law fires at the
  mirrored 200 m. Three hard-won wire laws banked: (1) JS bitwise
  ops yield SIGNED int32 — once bit 31 sets, the FNV seed
  multiplies as a NEGATIVE double and ToUint32 wraps that; the
  unsigned FNV everyone writes in python NEVER matches it;
  (2) a cactus that already passed the runner must never steer —
  its negative time-to-impact pogo-sticks the dino to death;
  (3) a probe that reads a stale entity reference reports the
  frame before last and lies by one packet.
- The grace probe re-pinned for the new arc (all 16 green): the
  discrete apex is 6.3, and the kept-press window moved to
  gap in [1.0, 2.8] — the honest gap the new fall actually walks
  through (2.7 -> 0.9 -> landed).

## v3.1.56 — the light field, documented honestly

- **sdk/PROTOCOL.md grows "the light fields" — and loses a lie.**
  The old flash paragraph said a flash "decays at 4/s in update" —
  true for the engine's own `:scene` entities (spark.cpp decays at
  4/s) and MISLEADING for every wire game this document is written
  for: the studio (host.hpp) keeps whatever the game last sends,
  and the decay is the GAME's job. A wire author following the old
  paragraph would have written v3.1.55's bleached-card bug exactly.
  Now the doc states both paths side by side — a table of who owns
  the tick, who owns the decay — plus the house conventions: the
  honest staircase (constant rate every tick), and the birth-tick
  law (compute the decay BEFORE the spawn, or the subject is born
  already faded).
- **background.py, the hello-world, learns glow in one attribute:**
  the moon wears `glow = 3`. Six lines of code plus one — the
  first thing a newcomer ships now also teaches the light.

## v3.1.55 — the hand remembers

- **A REAL light bug, caught by reading the engine before the probe
  could catch it live: cards.py's played card stayed white FOREVER.**
  The studio (host.hpp) keeps whatever flash the game last sent — the
  decay is the GAME's job — and cards.py set `c.flash = 1.0` on play
  and never lowered it. One play bleached that card for the rest of
  the run. Now the flash decays down the honest staircase (3/s: 1.0,
  0.7, 0.4, 0.1, 0.0).
- **The hand wears the full light law.** The five cards AND their
  rank labels ghost in on ONE shared clock (alpha 0.15 → full over
  0.9 s — the radar-field law); a PLAYED card wears alpha 0.5 for
  the rest of the run (the hand remembers what it spent); and a red
  card's double pay SPEAKS — the title glows 3 and cools at six a
  second. Entity count unchanged (12): the light rides existing
  bodies, the conformance pin never moved.
- **Probe `cards_breathe_probe.py`: 17 pins, all green** — the
  ghost clock mirrored bit for bit (worst err 0.0), both scoring
  laws pinned (black = chips only "2 x 1", red = chips AND mult
  "6 x 2"), the staircase honest, the spent alphas worn. The probe
  also learned the wire's own rhythm the honest way: a selection
  made in keys appears on the NEXT frame's redraw (tick before
  keys — the same order law the SDK packet taught in R21).

## v3.1.54 — the mystery takes the sky

- **invaders.js grows the mystery saucer — the old ROM's law,
  reborn on the wire.** The gun keeps a tally: every 13th LAUNCHED
  shot (muzzle glow 4 marks each launch) summons the saucer. It
  crosses the sky ABOVE the grid (y 0..3 never touches row 0 at
  y 5 — the geometry is proven, not hoped), rides as its own
  lantern (glow 4) at exactly 16 px/s, and pays a bounty from the
  purse 50/100/150/300 — and the say speaks the SAME number the
  score keeps. Their bombs cannot touch it: the pair is refused,
  the score stays. Escaped or paid, it parks dark at the edge like
  every other spent body on this wire.
- **Probe `invaders_ufo_probe.py`: 15 pins, all green.** The
  steered host LEADS the crossing (the R21 lesson, applied: the
  saucer walks 1.6 px per packet while the shot climbs 4 — the aim
  is predicted, not chased) and kills it with an honest overlap.
  The probe also pins the tally's continuation (13 more shots
  summon it again) and the unpurchased escape (parks dark at the
  far edge). Entity 51 -> 52; the conformance pin moved with it,
  and the R21 light probe was re-run green after its own count pin
  learned the new number.

## v3.1.53 — the torch breathes

- **raycast.py wears the light — every example now speaks the
  engine's glow.** The eye's lantern (mark.glow 2) burns on the hud
  rail, and the whole world's shade sways ±5% on a nine-radian
  sine — the torch breathes: near walls burn and rest, the dark
  breathes back, and the breath is DETERMINISTIC (the same
  stillness, the same breath).
- **The probe taught the difference between a law and a look.** The
  first cut swung the shade's t by ±7% — mathematically present,
  bit-mirrored by the probe, and INVISIBLE: 8-bit channels
  quantized the breath to one color. The fix scales the CHANNELS
  (clamped at 255) so every distance breathes visibly, far and
  near alike. Probe `raycast_torch_probe.py`: 6 pins — the game is
  python, so the probe replicates the full ray march and matches
  the engine's colors EXACTLY across 3 columns x 60 ticks, pins
  the breath's ~14-tick near-period (within 2 channel units), and
  confirms turning still paints a different world.

## v3.1.52 — the war wears the light

- **invaders.js wears the light — the last undressed example.**
  Every wave now GHOSTS IN: the alien grid AND the four shelters
  share one clock and fade from alpha 0.15 to full over 0.9 s (the
  radar-field law — "the sky fills again" is finally something you
  can SEE, every redeploy included). The muzzle GLOWS 4 on the fire
  frame and cools at eight a second down an honest staircase
  (3.6, 3.2 ...); flying shots and bombs carry their own halo (2);
  and a spent bullet parks its light WITH its body — no glowing
  ghosts sleep in the pool.
- Entity count unchanged (51 — the light rides existing bodies), so
  Gate 6's pin never moved. The fire frame carries the full 4
  because keys fire after the tick (the dino birth-tick lesson,
  applied a third time).
- Probe `invaders_light_probe.py`: 14 pins green at the host's own
  geometry (120x84). The kill choreography earned three hard
  lessons: (1) LEAD the target — the grid marches 0.125 px per
  packet and the shot's 35-packet flight lets a centered aim drift
  4 px past; (2) a rising shot eats the target's COLUMN from below
  (rows 2, 1, then 0 — every row crossed is an honest kill);
  (3) each kill THINS the grid, stepEvery falls back to 0.2 and
  the march QUADRUPLES — a fixed lead is wrong forever after. The
  probe now measures the march rate live (a 12-packet window),
  aims at the lowest alive alien of the column, and leads by
  rate x flight time. The score pin sums every dead seat's row
  price (30/20/10) against the hud — the scoring law itself is
  pinned, not a constant.

## v3.1.51 — the comet and the dusk

- **bounce.js: the wall fits the room — a REAL latent defect fixed.**
  The old wall was authored for a ~900x200 canvas: bricks at
  x=60..820, y=80..184 — on the host's own world (cols x
  (rows-2)*2, e.g. 120x84) EIGHTEEN of eighteen bricks were born
  off-screen and the win was unreachable. The gate's scene-only
  check never saw it; the probe did. The wall is now sized from W
  and H — twelve bricks, four across, three deep (24x8), every one
  on screen above the floor — and the probe clears all twelve and
  reads the win label for real. The top wall moved to y=2 (the old
  y=30 band swallowed a third of the room); the hud's two dialects
  merged into one.
- **bounce.js wears the light.** The ball is the room's lantern
  (glow 2) and leaves a COMET: six seats that slide back one each
  tick, seat 0 standing exactly where the ball stood one tick ago
  (bit for bit — the probe mirrors the flight), each wearing its
  own age as alpha (0.5 down to 0.10). The pad answers a touch
  with a glow that decays at twelve a second — and never in the
  tick it was lit (hits fire after the tick, so the touch frame
  carries the full 3 — the dino's birth-tick lesson, applied).
  A lost ball parks the comet; the fresh serve re-forms it.
- **windmill.py: the dusk law.** The day is measured in turns —
  every degree the wind carries is a degree of the day (a full day
  per 720 degrees). The sun's alpha sweeps 1.0 -> 0.45 -> 1.0 on
  the cosine of the day (the probe mirrors it BIT FOR BIT — worst
  error 0.0e+00), the clouds wear the dusk at a third of its
  depth, the sun glows 4 by day and goes dark past dusk 0.4, the
  hud names the hour (noon / dusk / nightfall), and HOLDING the
  wind holds the sun where it stands — the pause key pauses the
  sky too.
- Probes: `bounce_light_probe.py` (16 pins — including the host
  playing honestly: one hit per tick, an aim that alternates on
  every save, since a perfectly centered pad makes off=0, vx=0, a
  dead loop straight up and down) and `windmill_dusk_probe.py`
  (12 pins). Gate 6: bounce's pin survives at 21 (12 bricks + 6
  comet seats + pad + ball + hud); windmill's 13 untouched.

## v3.1.50 — the grace law

- **Dino's jump-feel pass, in three laws.** The GRACE LAW: a press
  that arrives while airborne is KEPT for 0.12 s ("kept" speaks the
  moment it lands on the memory) — if the ground arrives before the
  memory expires, the leap fires anyway ("grace!") and the runner
  rises again the very next frame. The desert is flat, so this is
  the runner's coyote time: the press that lands before the ground
  does is not a lost press. The memory decays honestly (0.12 s,
  gone is gone — a press kept high above the ground is forgotten by
  the touchdown) and `r` resets it with everything else.
- **The arc bites.** The rise floats at gravity 90, the fall drops
  at 144 — the apex still clears four units, but the way down is
  measurably shorter than the way up (0.264 s against 0.333 s from
  the same height). The probe mirrors the engine tick for tick and
  the flight matches BIT FOR BIT — the law is exact, not approximate.
- **The dust speaks.** Every touchdown (grace or clean) leaves a
  dust puff at the dino's feet: alpha 0.7, descending the honest
  staircase 0.56, 0.42, 0.28, 0.14, gone in five ticks, parked at
  -999 when it dies. **The probe caught a real birth-tick bug here
  before shipping:** the fade block originally ran after the spawn,
  so the dust was born already faded to 0.56 — the fade now runs
  before the physics, and the dust lives its first tick at 0.7.
- Entity 19 → 20 (the dust); Gate 6's dino pin moved with it.
  Probe `dino_grace_probe.py`: 22 pins green over the real wire —
  including the death march, which injects the overlap itself
  (hits are the host's gift), and the fresh-run reset (nothing
  kept, no phantom dust, the leap still says "up!").

## v3.1.49 — the last light

- **Lunar's polish round exposed a REAL latent bug:** the flame,
  once lit, burned FOREVER at the spawn point — `on_key` wrote
  `burn = 0.09` without `global burn`, so the module's fuse never
  burned down and the hide-branch never ran. (The old flame was a
  fixture of the launch pad, not a ship light.) The fuse is the
  module's now; the flame goes dark when the burn ends.
- **The polish, on top of the truth:** the flame RIDES the lander
  (x+4, y+16 — it never followed the ship before), it GLOWS (4)
  while burning, the pads wear halos sized to their pay (the valley
  3, the summit 4 — the brighter the halo, the richer the
  touchdown), and a clean landing BLEACHES the lander gold-white
  (flash 1.0) for the freeze beat.
- Probe `lunar_lastlight_probe.py`: 11 pins green — pay-sized
  halos, the sleeping flame, the riding glow, the dark after the
  burn, the touchdown's word on the say field (one frame only),
  the bleach, the frozen world, the respawn's clean tank.

## v3.1.48 — the vault

- **Tetris learns to hold.** `c` stashes the falling piece in a
  VAULT under the next-queue: the first hold trades the current
  piece for the queue's peek (one draw — the seeded law survives,
  the queue is never re-rolled), every later hold is a straight
  swap. The vault is honest about its state: it wears the stashed
  piece's color, and a SPENT vault wears the ghost's own alpha
  0.32 — used, but readable. One hold per drop: a second `c` speaks
  "the vault already gave — one hold per drop" and refuses; a lock
  re-arms it. HUD says "c holds" now.
- Gate 6 pin 17 → 22 (four vault seats + the vault's label).
- Probe `tetris_hold_probe.py`: 12 pins green — the sleeping vault,
  the stash (vault wears the fallen color, the peek becomes the
  order), the spent alpha, the refusal (say + nothing moves), the
  re-arm after a lock, and the straight swap. Probe lesson: a pin
  must honor the render law — top-row seats at py=-1 are honestly
  hidden, so "the piece is whole" pins the COLORS, not the
  visibility of seats above the well.

## v3.1.47 — the last undressed example

- **Shooter wears the engine's light** — the gallery's last example
  to speak it: the muzzle GLOWS (5) when you fire and fades honestly
  in tick (12/s), every bolt carries its own small halo (2), and
  every hit respawns the next threat as a GHOST — alpha 0.15 rising
  to full over 0.9 s, the radar-field's law, so the void announces
  what it is about to throw at you. Even the FIRST threat drifts in.
- Probe `shooter_light_probe.py`: 11 pins green — birth ghost, the
  drift to full, bolt halo, muzzle rise/fall, the hit (bolt gone,
  teleport, re-ghost, "SCORE 10", drift again). Probe lessons: a
  python entity's light fields must be DECLARED before they are
  read (`ship.glow = 0` at birth — missing keys read as None and
  the comparison dies); the frame of the KEY tick itself already
  carries the new world (handlers run before the frame is sent);
  and the hud's score lags one frame after a hit — on_tick writes
  BEFORE on_hit fires.

## v3.1.46 — the C++ SDK sees the light

- **The compiled SDK speaks the engine's light now.** `dxn3.hpp`'s
  `Ent` gains the three fields its JS and Python siblings always
  had: `glow` (a halo), `flash` (a hit-bleach the host decays), and
  `alpha` (a ghost-thin body). Zero-cost until used — the frame
  only carries them when they differ from their defaults, so every
  existing compiled game wires exactly as before.
- **Pong wears its own law:** the AI paddle's halo IS its rung
  (`ai->glow = lvl`) — L5's halo burns, L1's barely breathes. The
  ladder you can now SEE without reading the hud.
- **BUG the probe's lean-pin caught before shipping:** `mk()`'s
  positional aggregate init silently SHIFTED when the light fields
  joined the struct — every entity came out glowing (glow = 1).
  `mk()` now uses designated initializers, which cannot lie about
  member order and stay safe for future additions.
- Probe `pong_ladder_probe.py` grew to 7 pins: the scene travels
  lean (no default light on the wire), the AI's halo equals its
  rung across 300 frames, plus the existing hud/movement/rung
  laws. All green.

## v3.1.45 — the ladder

- **Pong's CPU climbs a difficulty ladder now** — and the rung is
  the SCORE's rubber band: an even set stands at L3 (the classic
  190 px/s cap, so an even game plays exactly as it always did);
  when YOU lead, the CPU digs in, up to L5 (285); when the CPU
  leads, it eases off, down to L1 (120). A set that stays dramatic
  on purpose. The hud always names the rung it stands on
  ("YOU 0 · CPU 0 · first to 5 · CPU L3") — and "first to 5"
  finally survives past the first tick.
- **BUG the probe caught before shipping:** the first speech mixed
  the PRE-score rung with POST-score numbers on the tick a point
  landed — "YOU 0 · CPU 1 · CPU L3" where the law says L2. The
  rung is now recomputed after the scoring, one score one truth.
- Probe `pong_ladder_probe.py`: 5 pins green — hud law on every
  tick (idle + steered rally), 3+ rungs observed in one idle set,
  and the movement law measured across 478 ticks: the AI's move is
  EXACTLY min(step, |gap|) toward want, no overshoot, whatever the
  rung. Probe lessons: the engine's order is physics FIRST, then
  onTick (the AI tracks the POST-physics ball — the probe's model
  must too); the standalone C++ SDK detects NO overlaps (hits are
  the host's gift — inject them, and a no-hit tick clears the pair
  memory, so periodic injections re-fire for real).

## v3.1.44 — the census

- **:stats speaks the file's weather now.** The document row gains
  four honest counts: shouted markers (`TODO` `FIXME` `XXX` `HACK`
  on word boundaries, upper-case exactly — lowercase prose never
  shouts, and a line counts ONCE however many markers it wears),
  comment lines (by the file's own comment stem, the same
  extension table the :toggle commentator uses — shebangs included),
  lines of pure air, and the DEEPEST INDENT (tab = 4 columns, so
  mixed files measure on one ruler). One row, no windows displaced
  — the census rides the size row it belongs with.
- Pure and selftested: `ideDocCensus` in edit.hpp, selftest group
  105 (7 pins) — word-boundary honesty ("FIXED is not FIXME"), the
  once-per-line law, the trailing-`//` is-ink-not-comment law, tab
  arithmetic, and the newborn document's one line of air. 983
  assertion groups green.

## v3.1.43 — the radar field

- **Asteroids wears the engine's light — all three fields, one
  law each.** A rock's `alpha` is now its PROXIMITY: inside 30 px
  of your hull it burns at full light, by 100 px it has sunk to a
  0.4 floor — the danger literally brightens as it closes in. Fresh
  rings DRIFT IN: 1.5 s from nothing to the radar's truth (the
  console always said "a new ring drifts in"; now the screen says
  it too). A shot DISSOLVES over its last quarter second instead
  of winking out — `alpha = remaining/0.25`, honest to the tick.
  And the thrust flame GLOWS (4) while it burns: the engine's
  light, spent on honest exhaust.
- The fourth gallery example dressed by alpha (snake's ghost,
  flappy's worn pipes, dino's night sky, now the radar field) —
  and the third dressed by glow.
- Probe `ast_wear_probe.py`: 11 pins green — ring drift-in, the
  radar law exact for every rock, closest==brightest, flame glow
  rise/fall, the dissolve staircase (~0.2/tick), the expired
  bullet's name honestly gone. Probe lesson: `"w"` is not an
  engine key — thrust travels as `jump` (or chars).

## v3.1.42 — the keepsake

- **The editor's habits survive the night now.** The five toggles —
  `:ruler` `:minimap` `:zen` `:relnum` `:wrap` — ride one line in
  `~/.dxn3-settings` ("ruler=1 minimap=0 zen=0 relnum=1 wrap=0").
  Toggle any one and the whole set saves itself; boot recalls it,
  right beside the coat recall. The theme's wardrobe kept your
  colors; the keepsake keeps your arrangement.
- **Honesty rules, borrowed from the wardrobe:** a partial line
  wears only the switches it names; a value that is not exactly 0
  or 1 is ignored (no guessing what "maybe" means); unknown keys
  are not crimes — they change nothing; a missing file or $HOME
  changes nothing. Garbage loses, defaults stand.
- Selftest group 104: 4 pins (birth habits, store → recall, partial
  line, garbage line). 976 groups green.

## v3.1.41 — the wardrobe 2.0

- **:theme takes YOUR coats now.** One per line in
  `~/.dxn3-themes` — `name:base:comment:string:keyword:pane:sel` —
  each color speaking decimal (`30,41,59`) or hex (`#e2e8f0`,
  `#` optional). Blank lines and `#comments` skip, half-lines and
  bad colors skip, and the file loads at boot, before the recall —
  last night's choice can name a coat you tailored yourself.
- **The wardrobe keeps its manners:** a user coat wearing a SHIPPED
  name is refused (the six built-ins are the house's, not yours);
  redefining one of YOUR earlier coats re-tailors it in place,
  never duplicates; bare `:theme` marks your coats `[user]`; name,
  unique prefix and 1-based index all reach them; `:theme`'s store
  → recall round trip keeps a user coat across nights; and the bar
  whispers them as you type.
- **BUG the selftest caught before shipping:** the decimal color
  parser demanded digit-only components — `" 30, 41, 59 "` (spaces
  after the commas) was refused, so an honest coat silently failed
  to adopt. Components now trim their own spaces. Selftest group
  103: 15 pins (adopt counts, hex+decimal values, shipped-name
  refusal, re-tailoring, index/prefix wear, `[user]` list mark,
  store → recall).

## v3.1.40 — the worn pipes

- **flappy.py learns depth: the pipes FADE IN from the horizon.**
  Every pipe's alpha wears with its distance — near-pipes stand at
  full strength, the mid pipe is fainter, and far pipes clamp at a
  0.35 floor — so each new pipe materializes out of the dark
  instead of popping in. Restarting a flight resets the wear.
- **A clean pass makes the bird GLOW** (glow 8, decaying 0.82 per
  tick — the same light the cards wear), **a crash BLEACHES it**
  (the flash field), and a fresh flight clears both scars. The
  three engine light fields — glow, flash, alpha — now dress THREE
  gallery examples each.
- Probe: 10 pins green on the real wire, first run — the cards
  round's lessons (tick-only packets, pump threads, one empty tick
  after a key tick) applied as discipline, not discovery. The wear
  curve is pinned at three distances plus monotonicity, the rise
  while flying is pinned, and the restart reset (wear AND scars)
  is pinned.

## v3.1.39 — the glow hand

- **cards.py stops being a flat menu and becomes a TABLE.** The
  selected card GLOWS (the engine's glow field, 6 — the same light
  the campaign's gems wear) and follows your A/D cursor; a played
  card FLASHES white (the flash field, the same bleach the snake's
  meal wears) the instant it lands.
- **The dead `played` list finally speaks:** every played card
  collects in the hand row — "hand: 5♥ 8♦ A♣" — the game keeps a
  visible memory of what you spent.
- **chips x mult scoring, balatro-style:** red suits pay +4 chips
  and +1 mult, black suits pay +2 chips; the title reads
  "score: 8 x 3" so a red streak visibly compounds.
- **Probe lessons (3 green runs to get there):** the python SDK
  only speaks `tick` events — a bare `keys` packet is silently
  ignored; select() on the child's fd starves once TextIOWrapper
  buffers ahead (probe v2's stall) — pump threads beat selectors;
  and the run loop draws on_tick BEFORE on_key, so a key tick
  returns the old world and one empty tick must follow it.
  11 pins green on the real wire.

## v3.1.38 — the gauge

- **lunar.py grows a fuel gauge — the tank is finally SEEABLE.** A
  bar under the HUD empties in width AND color: green while rich,
  amber under half, red under a quarter — BLINKING when the landing
  has to be planned, with one honest "fuel low — plan the landing"
  per tank, and a fresh tank after every respawn.
- **BUG the gauge probe exposed:** `on_key` never declared
  `global fuel` — the assignment shadowed the module global and the
  FIRST key press died on UnboundLocalError. The lander could never
  burn a drop; the freeze-beat's early return hid it from every
  forced-hit probe. Fixed, and the gauge pins (width shrink, color
  ladder, blink, warning) prove the burn end to end. Gate 6: lunar
  entities 10 → 11.

## v3.1.37 — the wardrobe

- **The editor learns to dress: `:theme` — six coats ship inside.**
  dxn (the house coat), dracula, gruvbox, nord, solar-dark and
  solar-light — each naming drawCodeLine's four code voices (base,
  comment, string, keyword) and the pane's two chrome washes. Wear
  one by exact name, UNIQUE PREFIX or 1-based index; a bare
  `:theme` lists the wardrobe marking what's worn; ambiguous
  prefixes and ghost names are refused honestly; the command bar
  whispers the coats as you type. The choice survives the night:
  one line in `~/.dxn3-theme`, recalled at boot, garbage-tolerant
  (a bad peg keeps the house coat on).
- Selftest group 102: registry sanity, name/prefix/index/ghost/
  ambiguous/list pins, store→recall round trip, garbage peg. 957
  assertion groups, all green. README editor sections + `--help`
  + `:help` speak the wardrobe.

## v3.1.36 — the meal bleaches

- **snake.py adopts the flash field — every meal bleaches the head
  white** (`body[0].flash = 1.0`, the engine decays it at 4/s), and
  every fifth meal — a rank-up — flashes the freshly grown tail
  segment too. The last of the three engine light fields now works
  in the gallery: glow (the food), flash (the meal), alpha (tetris
  ghost, dino sky). Probe: the greedy driver gained a same-row-
  behind detour, and the meal pin asserts head flash == 1.0 on the
  eat frame.

## v3.1.35 — the night gets a sky

- **dino.js: the 200 m night now arrives with seven stars and a
  moon.** The sky comes from its OWN seeded stream ("the night
  sky" — the desert's cactus seed stays dedicated, and a probe pin
  proves it by matching every star position against an independent
  FNV/xorshift emulation). Day: alpha 0.15, a rumor. At 200 m the
  alpha law fades the sky in over two seconds (stars → 0.9, moon →
  1.0, clouds dim to half) and the moon ends at `"glow": 4` — the
  engine's two light fields as weather. r walks again under a
  fresh day (sky reset pinned). Gate 6: dino entities 11 → 19.
- Probe lesson recorded: JS bitwise ops yield SIGNED int32, so the
  seed loop multiplies a NEGATIVE double (with 2^53-exceeding
  rounding) before >>>0 restores unsigned — the probe's emulation
  had to match both quirks to pin the stream.

## v3.1.34 — the shelters

- **invaders.js grows the classic SHELTERS — four arches of 7
  blocks each between the cannon and the order.** Every block
  absorbs exactly one hit and is DESTROYED for good (honest
  destroys, not fading): your own shots eat the arch from below,
  their bombs eat it from above, and the march grinds whatever it
  steps on. Erosion you can watch; a fresh run pours new concrete
  ("EARTH HOLDS" rebuilds, and a new `r` key restarts from the
  ashes after EARTH FALLS). Gate 6: invaders entities 23 → 51.
- Probe: invaders_probe.py extended to 19 pins — all green,
  including a mini-host that feeds the REAL overlaps a climb makes
  (the arch drinks the climbing shot) and the full r-rebuild cycle.

## v3.1.33 — the queue ahead

- **tetris.js previews the NEXT piece** right of the well — four
  preview seats plus a "next" label, worn in the coming piece's own
  color. The queue is PEEKED HONESTLY: one RNG draw per piece (the
  spawn consumes the pre-pulled piece, then pulls the next), so the
  seeded law — the same run, the same falls — survives the preview.
  Preview honesty is probe-pinned: what the box promises is exactly
  what spawns after the slam. Gate 6: tetris entities 12 → 17.

## v3.1.32 — the ghost

- **tetris.js grows a GHOST piece — the alpha law becomes gameplay.**
  Four ghost seats wear `"alpha": 0.32` in the piece's own color at
  the exact landing spot, tracking slides and turns, hiding the
  moment the order rests (gy == py). The engine's newest field, put
  to work as honest wayfinding.
- **BUG the ghost probe exposed:** soft-drop (`k === "down"`) was
  UNREACHABLE over the wire — the protocol's held keys are
  left/right/jump/space and no host ever sent "down". Soft-drop now
  rides the letter `s` (probe-driven fix, verified end to end:
  ghost hides exactly on landing, stays hidden at rest). Gate 6:
  tetris entities 8 → 12.
- Probe: scripts/tetris_ghost_probe.py (my-project side) — 6 pin
  groups, all green. README tetris blurb updated.

## v3.1.31 — the return

- **level-11 — the return, the TWELFTH scene and the campaign's
  finale.** A homecoming built from every law the road taught: three
  mist ledges (`"alpha"`, the fog's law), a timetable ferry (the
  crossing's), two counter-phased lifts trading the deep pit (the
  vault's), saw tolls at 300/320°/s and a leaning fang (the
  gauntlet's), and a beacon-style stair where the door itself wears
  `"glow": 7` — the light marks home. Eight gems, the campaign's
  best pay. Chain: level-10.next → level-11 → playground (gate 3b
  walked, 29 entities).
- Gallery pair six complete (the fog | the return); twelve-scene
  counts (README ×2, CAMPAIGN); CAMPAIGN section "the return".
  Screenshot is a real headless render (960×540).

## v3.1.30 — the fog

- **level-10 — the fog, the ELEVENTH scene, and the first built
  from the alpha law.** Four platforms are made of mist
  (`"alpha": 0.35`–`0.5`): see-through, and they hold you anyway.
  The gate sign tells the only truth about the place — what you can
  see through is still real. Between the mist: two saws (280/320°/s),
  a leaning fang, one ferry. Four of seven gems float over the mist,
  each glowing — the light marks what matters when the ground won't.
  Chain: level-9.next → level-10 → playground (gate 3b walked, 26
  entities).
- Gallery row, eleven-scene counts (README ×2, CAMPAIGN), the fog's
  own field-guide section, screenshot rendered with the real blend.

## v3.1.29 — the gradient wears the air too

- **QA fix the alpha release needed:** gradient fills parsed
  `color2` fresh and skipped BOTH the alpha blend and the flash
  bleach — a half-transparent gradient had one leg in the fog and
  one on solid ground. Both rasters now run `color2` through the
  same law as `color`: alpha blends it toward the scene bg, flash
  bleaches it toward white. A ghost is a ghost all the way through.

## v3.1.28 — a body made of air

- **`alpha` — a general entity field.** Any entity may carry
  `"alpha": <0..1>` (default 1): the body blends toward the scene bg
  in BOTH rasters — ghosts, fog banks and glass are now data, not
  tricks. `alpha: 0` is the air itself. A wire `set` thins or
  thickens it live (a vanishing act is a patch), `toJson` round-trips
  it, and PROTOCOL.md + README document the law.
- The playground ships the first ghost: `ghost-ledge` (alpha 0.45)
  floats between ledge-a and ledge-b with a coin for anyone who
  trusts the fog — a tutorial for the eyes, painted the same way
  your terminal paints it. Gallery screenshot re-rendered with the
  real blend.
- Selftest group 101 pins: parse, the solid default, toJson, the
  wire patch, and a PNG render. Selftest 926 → 931 assertion groups.

## v3.1.27 — every death speaks

- **flappy and lunar join the banner law.** The examples were a
  mixed choir: some deaths were banners (dino, invaders, tetris,
  snake, asteroids), some were quiet console lines. Now flappy's
  crash and lunar's last life arrive as win banners, lunar's
  mid-flight crashes speak on the HUD — and every game in the
  gallery mourns out loud, the same way.
- The wire probes pass; the mixed-choir audit is written down so
  the next example starts with a banner, not a print.

## v3.1.26 — the flash goes to war

- **asteroids.js adopts the engine's flash.** A hull hit now
  BLEACHES the ship and its thrust flame (`flash: 1` — one wire
  patch, the engine fades it), speaks on the HUD (`hull hit — 2
  left`), and the final death arrives as a win banner. The grace
  blink stays — the flash is the pain, the blink is the shield.
- The ast probe passes end to end (two hull hits, game over, rock
  split, rebuild ring). Conformance pin unchanged (7 entities —
  flash is a field, not an entity).

## v3.1.25 — a hit you can see

- **`flash` — a general entity field.** Any entity may carry
  `"flash": <0..1>`: the body bleaches toward white in BOTH rasters
  (terminal and PNG agree), and `Game::update` decays it at 4/s
  until it burns out exactly at zero — never negative. A game marks
  a hit with ONE wire patch (`{"name":"ship","flash":1}`); the
  engine does the fading.
- Parsed from scenes, patchable over the wire, round-tripped by
  `toJson`, documented in PROTOCOL.md and the README. Selftest
  group 100 pins the whole law: parse, patch, the 4/s decay (under
  the 1/30 dt clamp), the exact burnout, and a PNG render.
- Selftest 919 → 926 assertion groups. Probe lesson honored: the
  first decay pin used dt=0.1 and forgot the engine clamps dt to
  1/30 — the ENGINE was right, the test author was sloppy (again).

## v3.1.24 — the meal speaks

- **snake.py polish — the classic learns to talk.** The meal now
  wears the engine's glow (the one lit thing in the dark), every
  bite says so on the HUD (`meal 4 · 5 long`), every fifth meal
  names what you have become (the garden snake at 5, the hunter at
  10, the anaconda at 15, the world eater at 20), and all three
  deaths — the wall, your own tail, the snake that IS the world —
  arrive as win banners instead of quiet console lines.
- Wire probe: greedy driver steers the head onto the food, asserts
  the glow pin, the per-meal say lines, and the transient wall
  banner captured on the exact frame it flies.

## v3.1.23 — the crossing

- **level-9 — the crossing, the TENTH scene.** Three abysses with no
  floor, crossed only by ferries that keep a timetable (75 → 85 →
  90 px/s, each rung faster than the last). The middle abyss forks
  into the campaign's honest dilemma: a HIGH road over two pillars —
  glowing gems, a fang leaning across the exit — or the LOW ledges,
  longer but nothing leans. Two saws keep the decks, a vertical ferry
  pays out a two-gem summit, and the door home tops the far shore.
  Seven gems, four of them lit. Chain: level-8.next → level-9 →
  playground (gate 3b walked, 25 entities).
- Gallery completes its fifth pair (level-8 | level-9), ten-scene
  counts in README and CAMPAIGN, the crossing's own field-guide
  section. The screenshot is a real headless render (960×540).

## v3.1.22 — the night shift

- **`lightbot.js` — the fifteenth wire example, and the first built
  to PROVE the glow law.** A diamond of twelve unlit lamps on a 7×5
  grid: walk with the arrows, SPACE lights the lamp under you, and
  every flame wears the engine's glow (v3.1.20) — the wayfinding is
  literally made of light. Steps counted honestly, wins graded
  (a ghost of the grid / steady hands / the long way home), the done
  shift's head-lamp breathes, and r takes the shift again. Held keys
  are throttled by a cooldown, the walls refuse honestly
  ("the grid ends there"), and the reset restores every tile.
- **Two bugs the wire probe caught before shipping:** the diamond's
  top and bottom rows were lopsided (lamps at cols 2+5 instead of
  2+4 — the puzzle looked wrong and the shortest path made no
  sense), and the HUD froze one count behind the win (the winning
  frame's hud was drawn before light() ran — now the finished shift
  reads 12/12 in gold).
- Probe: per-step bot-position verification, greedy nearest-neighbour
  tour over all 12 lamps, transient win-banner capture, reset and
  wall-mash checks. Gallery 14 → 15 examples (py 8, js 6, cpp 1).

## v3.1.21 — the light learns to fall

- **Glow grew a falloff.** v3.1.20's halo was flat paint; now the
  circular ring blends with a radial falloff — bright where the body
  meets the halo, gone at the rim — and the rect aura became a stepped
  one (three nested rects, brighter toward the body). Both rasters obey
  the same law, and the PNG rect aura now blends against the pixel it
  lands on, so stars survive behind the light.
- **level-8 — the beacon, the ninth scene.** The first scene BUILT
  from the glow law: six gems AND the goal door all carry
  `"glow": 7` across the darkest sky in the campaign — wayfinding
  made of light. Three fangs (one against the grain), two saws at
  300°/s and 340°/s, two counter-phased lifts plus a summit ferry.
  Chain: level-7.next → level-8 → playground (gate 3b walked).
- Gallery row, CAMPAIGN section, nine-scene counts — the README
  promises only what ships (gate 7 walked).

## v3.1.20 — the halo anyone can wear

- **`glow` — a general entity field.** The coins' halo was hardcoded;
  now ANY entity can carry `"glow": <px>` and breathe the same dim
  aura — circles get a real per-dot ring, everything else the rect
  aura the coins have always worn. Both rasters obey (the terminal
  and the PNG poster agree on the shape test), the wire's `set`
  patches it like any field (a pulse is a patch), `toJson` round-trips
  it, and the selftest pins the parse, the patch and the
  byte-identical render (group 99).

## v3.1.19 — the gate that reads the promise

- **`scripts/gates.sh` grows gate 7: the README never promises a
  ghost.** Every `docs/img/*.png` and every `sdk/examples/*` path
  the README mentions must EXIST on disk, and the README's version
  badge must equal the VERSION file — checked before a tag can
  leave the machine. A gallery row pointing at a screenshot that
  was never rendered, an example named but never committed, a
  badge left one version behind: all of them are GATES RED now,
  not a slow embarrassment discovered later.

## v3.1.18 — the falling order

- **`sdk/examples/tetris.js` — the classic, honestly built.** A 10×16
  well with rail-and-floor chrome; the seven tetrominoes drawn from a
  SEEDED 7-bag (FNV-1a + xorshift, the studio's determinism law: the
  same run, the same falls, forever); left/right slide, up-or-jump
  turns (with wall kicks ±1, ±2), down soft-drops, space SLAMS; the
  drop rate tightens with the level (0.5s → 0.08s floor). The design
  law worth reading: LOCKED CELLS ARE THEIR OWN ENTITIES — one rect
  per seat, named by sequence — because the falling seats must stay
  free for the next order, or a sweep would destroy the piece that is
  falling (the probe caught exactly that draft). A cleared line is
  ten honest destroys and everything above falls one row; TETRIS!
  speaks its name; an untouched well tops out with its count —
  "TOPPED OUT at 0 — r falls again" — and r, arriving through the
  wire's chars channel, walks again. 8 entities at the scene's birth;
  gate 6 roster 13 → 14; the JS gallery grows to FIVE.
- **Probed end to end** (deterministic probe): the first order paints
  its four seats, right slides, jump turns, gravity drops, the slam
  buries four named cells, the untouched well tops out honestly, and
  the reset re-births the falling four. The probe's findings, fixed
  before the tag: a double-offset in the slide/gravity fits-checks
  (seats probed at py+py), the missing cells-assignment in turn(), and
  the lock-into-falling-seats design bug above.

## v3.1.17 — the bracket's twin

- **`:match` — the hand walks to the other half.** From the
  cursor, the nearest bracket at or after it finds its twin: an
  opener scans forward, a closer scans back, nesting counts itself
  honestly, and the walk crosses lines without flinching. The walk
  is QUOTE-HONEST — a bracket inside a string literal is ink, not
  structure (single or double quotes, backslash escapes, the
  quote's law ending at its own line's edge). An unclosed bracket
  says so instead of guessing; a jump takes no stage (the ledger
  keeps its peace). Six selftest pins: the round trip, the string
  lie, the cross-line walk, and the two honest silences. 907 →
  913 assertion groups.
- **A ghost verb buried**: `:chomp` still lingered in the command
  grammar's no-argument list from v3.1.13's cut — the parser
  accepted it while the dispatch refused it. The grammar and the
  dispatch now agree: :trim is the one true sweep.

## v3.1.16 — the nose-dot lie retires

- **`sdk/examples/asteroids.js` — the ship turns for REAL.** Since
  the engine's first version the wire carried `rot`, and since
  v3.1.10 both rasters render it — but the asteroids ship still
  faced you with a nose dot orbiting a round core, an honest
  geometry hack standing in for a missing feature. The hack is
  retired: the hull is a rotated TRI whose apex rides the heading
  (the Turn math live in the gallery), and the nose survives as a
  THRUST FLAME — golden, and visible only while you burn, which is
  one more bit of honest information than the old dot ever gave.
  Entity count unchanged (the flame keeps the nose's seat), so
  gate 6's roster stands at 13 and the deterministic probe still
  passes: three spaced hull hits to game over, the rebuild ring
  under fresh names, the grace timer swallowing in-window hits.

## v3.1.15 — the descent (the campaign's eighth scene)

- **`scenes/level-7.dxn1.json` — "the descent".** The summit's
  answer: the only way out is DOWN. Five platforms stair-step from
  the clouds to an indigo vault floor; three lifts ride down or
  counter-phase; six gems mark the honest line; and the campaign's
  first LEANING FANGS — spikes with a rot of their own (20° to
  40°, two against the grain) — possible since the engine learned
  to turn, used here for the first time. carousel-saw runs at
  360°/s, the fastest thing in the campaign, and it is VISIBLE now
  (v3.1.10's rot doing its job). The chain walked: level-6 →
  **level-7** → playground, gate 3b green; 27 entities render one
  real headless frame, gate 3 green.
- **`docs/img/shot-level-7.png`** — the descent's real poster in
  the README gallery, table row added.
- **CAMPAIGN.md** gains the descent's section (the leaning fangs,
  the carousel, the door home) and the chain line says eight.
- Smoke's boot check can reach it like any scene: `--scene
  scenes/level-7.dxn1.json` boots and quits clean.

## v3.1.14 — the long run, on a seeded desert

- **`sdk/examples/dino.js` — an endless runner.** Space leaps (one
  honest gravity, 90 px/s², the ground ends the fall), the desert
  speeds up forever (+2 px/s per second), the meters pile up in the
  HUD. The cacti come from a POOL of six parked off-screen — an
  idle cactus costs the wire nothing — and the SPAWN LAW is SEEDED
  (FNV-1a of the runner's name, xorshift after): the same run, the
  same desert, forever — the studio's determinism law, now a
  gameplay promise. Night falls at 200 m (the ground goes dark);
  a touch speaks your meters honestly — "down at 13 m" — and `r`
  walks again. 11 entities exactly; gate 6 roster 12 → 13, the JS
  gallery grows to FOUR.
- **Probed for truth** (deterministic probe): 11 entities, the
  leap is set on the key frame and lifts NEXT frame (the SDK's
  dispatch order — keys land after the tick's physics — is now
  documented in the probe), the 16-tick arc returns to earth, a
  cactus spawns and scrolls at the run's speed, the fatal touch
  speaks its meters, zero tracebacks.

## v3.1.13 — the margin's hygiene kit

- **`:squeeze`** — wherever two or more blank lines stand together,
  all but the first of the run fall (whole bed or the selection).
  The pins speak uniq's structural law word for word: a pin on a
  fallen line dies, a pin on a kept line rides it home, a pin
  beneath the bed slides up. One honest restore point, taken only
  when a run actually falls.
- **`:retab`** — every leading tab widens to four spaces, the
  editor's tab law; a tab INSIDE the line keeps its meaning (a
  string literal is nobody's indent). Mixed indents keep their
  columns. Shape never changes, so no pin map is needed.
- **`:ws` — the whitespace census.** A mirror, not a broom: it
  counts lines wearing trailing whitespace, lines indented with
  tabs, and lines over the 80-column law, then tells you which
  verb tidies them (:trim and :retab). It changes nothing.
- **Duplicate verb caught and cut**: the new `:chomp` duplicated
  the existing `:trim` (trailing-whitespace sweep) — removed before
  it ever shipped, per the studio's one-name-one-verb law. The
  census receipt now speaks of :trim, not of a ghost.
- **13 → 10 new selftest pins** (911 → 907 after the chomp cut):
  squeeze's run law and pin law, retab's four-space law and the
  mid-line tab's immunity, the census's three honest numbers and
  its mirror vow. ALL GATES GREEN.

## v3.1.12 — the invasion, and a rounder sky

- **`sdk/examples/invaders.js` — the classic march.** Fifteen
  aliens step, drop at the edges and speed up as their ranks thin
  (0.8s → 0.2s by the last survivor); the cannon fires from a
  three-shot pool, the grid answers from its own pool — bullets
  PARK off-screen at x −999 until a gun needs them, so an idle
  bullet costs the wire nothing. Three waves, then EARTH HOLDS;
  the grid landing costs a life, three losses — EARTH FALLS.
  Probed for truth: 23 entities exactly, the march moves, a hit
  pays its row's points, a parked pool exists, no tracebacks.
  Gate 6 roster 11 → 12, and the JS gallery grows to three.
- **The poster renders real discs.** The terminal drew circles
  per-dot from day one, but the PNG raster fell through to plain
  rects — every coin and sun in every poster was a square wearing
  a halo. Now the poster runs the same disc test per pixel (with
  the rim's lighter edge), and coins keep their halo around a
  ROUND body. The sky got rounder everywhere.
- **`docs/img/shot-windmill.png` — the gallery gains the mill.**
  The windmill posed for its portrait: four blades frozen mid-sweep
  (every one REALLY rotated through v3.1.10's Turn math), the hub's
  diamond caught at 45°, gradient tower and grass, a sun that is —
  as of this version — finally a circle in the poster too.
- **smoke's section 16 verified green** before this tag: level-6
  "the ascent" boots a real frame and quits clean.

## v3.1.11 — the windmill, and spikes that turn

- **`sdk/examples/windmill.py` — the turn showcase.** Four blades
  orbit the hub: the SDK drives each blade's `x`, `y` AND `rot`
  every tick, so the thin rects stay radial as they sweep the sky
  — the first gallery piece built on the rot path from v3.1.10.
  The hub's little square turns ITSELF with the engine's own
  `spin` (no SDK work at all): two kinds of rotation, one mill.
  left/right work the wind (15–400°/s), space holds it, the clouds
  drift and wrap, the grass wears a gradient. Probed for truth:
  13 entities exactly, the blade orbits AND turns, rot arrives on
  the wire, space freezes the wind, zero tracebacks.
- **Spikes turn too** — the tri profile (terminal raster and PNG
  poster alike) now honors `rot` with the same shared `Turn` math:
  inverse-rotate each dot/pixel, test the shrinking row, edge the
  slopes. A rotated spike is a real rotated spike now, in the
  terminal and in the poster.
- **Gate 6 roster 10 → 11** — windmill.py probed on the wire
  (13 entities, counted exactly).
- **smoke gains section 16** — level-6 "the ascent", the newest
  campaign scene, boots a real frame and quits clean.

## v3.1.10 — the saws truly turn (rot renders at last)

- **The engine renders `rot` — in BOTH rasters.** The wire carried
  `rot` and `spin` from day one (scenes parsed them, the sim wound
  them at degrees per second), but the terminal raster and the PNG
  poster both ignored the angle when they drew: six scenes of saws
  span in the data and stood still on the glass. Now a body with a
  non-zero rot is painted per-dot/per-pixel through a shared
  inverse-rotation test (`Turn`, in fx.hpp) — the same math for the
  live terminal and the poster, so both rasters can never disagree.
  Spinning hazards visibly tumble now; a square sweeps through its
  diamond pose every quarter turn.
- **Gradient bodies rotate with their fill** — a rotated rect with
  `fill: "gradient"` samples its color ramp in the body's local
  frame, so the gradient turns WITH the body instead of staying
  screen-aligned (poster raster; the live view follows its own
  gradient law).
- **Shared math pinned by the selftest** — identity at 0°, the 90°
  arm-sweep (screen y is down, so +x asks for local -y), a square
  turning onto itself, the 45° diagonal extent (√2·20), a posed rot
  holding still while nothing spins it, spin winding rot through 15
  real engine ticks (25°), and an end-to-end poster render of a
  turned body as a real PNG on disk. 891 → 898 assertion groups.

## v3.1.9 — a world of rects, and the third tongue

- **`sdk/examples/raycast.py` — the flagship: a 3D world out of
  plain rects.** A Wolfenstein-style raycaster — a 16×12 grid map, a
  DDA ray march per column, and `W/8` thin rects whose heights are
  the walls' honest distance and whose colors sink into the dark as
  the corridor recedes (the two wall faces wear different tones, so
  corners read). Left/right turn, w/s walk, a wall stops you — the
  probe walked, turned and walked back through 120 frames and the
  perspective gradient is real: 53 → 4 → 40. The engine is a
  canvas; this is what "any canvas" means.
- **`sdk/dxn3.hpp` — the C++ SDK speaks too.** `g.say(...)` and
  `g.win(...)` join their Python and JavaScript siblings: the frame
  carries both words, the run loop clears them at send, and the
  wire probe proved it (tick 1 speaks, tick 2 is clean). All THREE
  SDKs now tell one story with PROTOCOL.md.
- **Gate 6 grew the flagship** — raycast.py probed on the wire (26
  scene entities at the probe's world, counted exactly). TEN
  examples now speak the protocol.

## v3.1.8 — the SDKs learn to speak (say / win)

- **`say(...)` and `win(...)` in BOTH SDKs** — the wire protocol
  always carried the frame's `say` and `win` fields (the engine's
  `applyFrame` reads them: a transient HUD line and a banner + screen
  flash), but the Python and JavaScript SDKs never exposed them.
  The bridge exists now: the words ride ONE frame, the run loop
  clears them the moment the frame is sent, and the probe suite
  proved both halves end to end (python + node: tick 1 speaks, tick
  2 is clean). The lunar lander wears it first — every touchdown
  says `+N — touchdown` on the HUD, transiently, the way the engine
  meant it.
- **sdk/PROTOCOL.md** says so in print: the frame packet section now
  names the SDK verbs, so the document and the SDKs tell one story.
- The Python half earned its honesty the hard way: the first draft
  hit Python's local-shadow law (`_say` assigned in `run()` made it
  local — UnboundLocalError on the very first frame), caught by the
  saywin probe before any push. `global _say, _win` in the run loop;
  the words ride one frame.

## v3.1.7 — the moon joins the gallery

- **`sdk/examples/lunar.py` — the lander, the ninth proof.** Gravity
  is the enemy and the pads forgive: side-thrusters steer, the main
  engine burns fuel by the frame, and two pads pay by their risk —
  the valley's easy 50 and the summit's doubled 100. Land softer
  than 65 down and 35 across or the legs give; the hills are honest
  ground and honest ground is lethal; drift off the moon and the
  dark keeps you. The flame lives only while the engine burns (one
  breath per burn, snuffed by the tick), a freeze beat holds the
  world while a touchdown pays or a crash mourns, and three wrecks
  end the run with an honest final score.
- **Gate 6 grew another row** — the lander probed on the wire (10
  scene entities, counted exactly), and the probe suite on the
  author's side walked every path deterministically: touchdown,
  hill-crash, game-over reset, score mirror, 800 frames, zero
  tracebacks. NINE examples now speak the protocol.

## v3.1.6 — the saws bite, and the ascent begins

- **FIXED: the hazard tag kills — the campaign's saws finally saw.**
  Six scenes shipped with saws that could not saw: `deck-guard`,
  `ferry-guard` and friends wear `tag: "hazard"`, but the kill rule
  only knew the word `spike` — every saw in the vault, the gauntlet
  and the movers was decorative, and level-5's own sign ("mind the
  saws") was a lie. Both killing tags fire now, each speaking its
  own name: the fang says `ouch — spike!`, the saw says `ouch — the
  saw!`. Selftest group 4b pins the law three ways (the saw
  respawns, the saw speaks, a saw across the room never bites —
  888 → 891).
- **`scenes/level-6.dxn1.json` — the ascent, the campaign's seventh
  scene and its highest tower.** Three lifts stack the climb, five
  terraces carry the honest ledge work, two saws guard the air at
  jump height now that they bite, six gems mark the line, and the
  summit — indigo, because it earned it — holds the highest door in
  the campaign. `level-5`'s door now chains to the ascent; the
  ascent's door brings you home to the playground. The loop is
  seven scenes, gate 3b walks every link.
- **Docs keep pace**: README speaks seven scenes (twice), the
  screenshot table gains the ascent's real headless frame, and the
  campaign field guide tells the tower's story.

## v3.1.5 — the gallery grows a snake and a starfield

- **`sdk/examples/snake.py` — the classic, on the wire.** A grid
  snake whose turn queue plays fair: a HELD key fires every frame,
  so the queue dedupes its tail and stays three turns deep — the
  snake steers where you LOOK, not where your keyboard drifted
  (the bug the chase probe caught: a drowned queue kept steering
  long after the player changed their mind). Meals grow the tail
  and sharpen the step (0.14s down to 0.06s), the score mirrors to
  the HUD through `vars`, the wall and your own tail bite honestly,
  and `space` rebirths a fresh snake — each life names its segments
  anew, because a name re-spawned AND retired in one frame dies
  twice: the engine applies `set` before `del`, and this game is
  built on that law instead of tripping over it.
- **`sdk/examples/asteroids.js` — the discs drift.** A ship whose
  facing is honest GEOMETRY — a nose dot orbits the core, because
  the raster tells no rotational lies — with thrust, drift and
  friction, eight bullets deep, rocks that split 13 → 8 → 5 and fly
  faster as they shrink, a 2.2-second grace blink after a hull hit,
  three lives, and a game over that rebuilds the whole ring under
  fresh names. The wrap-around is the game's own math, every edge,
  every frame. Bullets inherit half your drift; the field, once
  cleared, deals a new ring and says so.
- **Gate 6 grew two rows** — both games probed on the wire for real
  (5 and 7 scene entities, counted exactly), and the full gauntlet
  stays green: build, selftest (888), every scene renders a frame,
  the campaign chain resolves, VERSION ↔ CHANGELOG agrees, and all
  EIGHT examples now speak the protocol.

## v3.1.4 — :git tag (the milestones, counted) and the help that keeps up

- **`:git tag` — the milestones, spoken.** One receipt, the cap is
  six with a `+k more` tail, each name held to 16 columns. A repo
  with no tags says so honestly (`no tags yet — the milestones
  wait to be cut`), a folder with no repo is refused, never
  guessed — the probe speaks for the git that isn't there. Still
  read-only: the verb reads the milestones, it never cuts one.
  The git family is now four mouths: `:git` the present, `:git
  log` the past, `:git branch` the paths, `:git tag` the peaks.
- **DOCS DEBT PAID: the `:help` row keeps up.** The bare `:help`
  listed the verbs but never named `:diff`, `:drift`, or `:git`
  — three families shipped silent. The row speaks them now; the
  whispers (`:help <verb>`) always worked, the front door didn't.
- Selftest group 29 pins two more laws (886 -> 888). Smoke 13w
  grew the tag drive — the sandbox cuts `v0.0.1`, the verb reads
  it (217 -> 218). Gates ALL GREEN.

## v3.1.3 — :git branch (the locals, spoken)

- **The branch manager's sapling.** `:git branch` — the local
  branches, spoken in one receipt: the current wears the star,
  the names join with a middot, the cap is six with a `+k more`
  tail, each name held to 22 columns. Still read-only — the verb
  names the paths, it never walks them for you — and still
  refused honestly without git. The trio is whole: `:git` speaks
  the present, `:git log` the past, `:git branch` the paths.
- **The BUG the drive caught (before any push):** the first
  draft asked `git branch --porcelain` — no such flag on
  `git branch` (that is `git status`'s word); exit 129, and the
  verb's honest refusal fired in the smoke instead of the
  listing. The real form is `--format="%(HEAD) %(refname:short)"`,
  the star riding the current line, the padding stripped from
  the rest.
- Selftest group 29 pins two more laws (884 -> 886): the bare
  verb is well-formed, and it takes no argument. Smoke 13w grew
  the drive (216 -> 217). Gates ALL GREEN.

## v3.1.2 — :git log (the repo's memory, spoken)

- **The branch manager's seed grows a root system.** `:git log [n]`
  — the repo's memory, walked: a bare verb speaks the last three
  commits, a number (1 to 8) speaks that many, each as `hash
  subject`, joined into ONE receipt with a middot between them
  (the ledger's window is two rows — a line per commit would
  scroll itself into silence). Each subject is capped at 38
  columns, the whole receipt at 96, honesty kept with an
  ellipsis. Still read-only, still refused honestly without git.
- **The grammar has edges and they bite.** `:git log banana` is
  refused with usage; `:git log 9` is refused (the cap is eight);
  `:git push` is refused — the verb asks, never writes. The
  refusal's law in the smoke: a refused verb never dispatches,
  so the stage stays in play and the usage paints over the
  resting bar for 3.5 seconds — the drive asserts there, on its
  own studio, and lets the elder's flow keep its stage.
- Selftest group 29 pins five new laws (879 -> 884). Smoke 13w
  grew three drives (213 -> 216): the walk, the honored count,
  the honest refusal. Gates ALL GREEN.

## v3.1.1 — the drift that breathes

- **The amber is no longer a photograph — it is a pulse.** On a
  slow silent beat (a quarter second) the page re-hears the disk:
  the drift store refreshes without a word — the amber follows the
  edits live while they are still unsaved, and a disk that moved
  under a settled page (a checkout, a teammate, another hand) is
  worn on the rail and spoken in the header (`N drifted`) the
  moment the census hears it. The breath never spends a console
  line; the store is the whole breath. The census's own laws
  hold inside it: an agreeing beat clears, a bed too big keeps
  the old ticks, a lost disk copy is skipped, never spoken.
- **Every saving mouth sweeps the amber now.** The auto-run's
  save (the idle live-refresh) obeyed `:w`'s receipt but kept the
  stale ticks — a page saved clean still wore amber for lines the
  disk had just heard. The sweep rides the save itself, the same
  law the `:w` and `:wq` verbs speak.
- Smoke 13x: THREE drives on a fresh studio — the ledger settles
  (no pending word scrolls the listing away), the disk loses its
  tail, and a bare `:drift` lists `1 line drifted from disk` with
  NO `:diff` ever asked (207 -> 213 checks; the breath proved
  silent, live, and swept). Selftest stays 879 (the breath rides
  the store's pinned laws). README speaks the breath in the diff
  prose and the `:drift` row. Gates ALL GREEN.

## v3.1.0 — :git (the repo's truth in one breath)

- **The branch manager's seed: the studio knows its repo.** `:git` —
  one breath, one receipt: the branch, the uncommitted count (or a
  plain `clean`), and the last commit's name (hash + subject,
  capped at 52 columns with an ellipsis for honesty). Read-only —
  the verb asks the process's own working directory, the same
  ground the saves land on, and never touches a thing. A machine
  without git, or a folder that is no repository, is refused
  honestly, never guessed.
- **The BUG the third drive caught (before any push):** a clean
  tree printed `0 uncommitted` — the census's zero spoke as a
  count. The law now: zero IS clean, in words. Smoke 13w grew a
  third drive — the sandbox's own repo is committed mid-run and
  the receipt must say `clean` (209 -> 210 checks; the first two
  drives seed a real repo so the read-only questions have honest
  answers).
- Selftest group 29 pins the grammar: `:git` is well-formed bare
  and its whisper names what it speaks (877 -> 879 groups). The
  README's verbs table wears the row. Gates ALL GREEN.

## v3.0.99 — :drift (the amber census as addresses)

- **The drift is not just a mirror — it is a set of addresses.**
  `:drift` — a bare verb LISTS the lines the last `:diff` heard
  disagreeing with the disk (the amber ticks' own numbers, capped at
  eight with the `... +k deeper` tail); a number LEAPS to the Nth —
  the same real leap the pins' `:bm` and the census's `:changes`
  obey: planted in the jumps ledger, the selection dropped, the
  landing mid-screen. The drift is the census's memory: `:diff`
  asks the disk first, `:w` sweeps what it heard, and a page with
  no drift says so with the way out (`:diff` first). One law, three
  census voices now: `:changes` speaks the session, `:count` speaks
  the query, `:drift` speaks the disk.
- Selftest stayed 877 (the drift store/ask laws are pinned in group
  98; the leap lives in the verb layer). Smoke 13v: TWO drives
  (205 -> 207) — the listing after a real drift, the leap landing
  the hand (the header's Ln speaks it). Gates ALL GREEN.

## v3.0.98 — the dashboard's truth (:stats speaks the drift)

- **`:stats` — the one-line session dashboard, extended.** The
  census's first line now also speaks `N drifted from disk` (when
  the diff census has heard disagreement — the amber ticks' own
  count, in words at last) and `M pins` when the page carries them:
  lines, words, chars, longest, changed-this-session, drifted,
  pins — everything the session owns, one receipt.
- Docs debt PAID: the `:crew` growth law was shipped but never
  spoken — planting again GROWS the crew from the last hand (the
  seed is the crew's tail, not the primary's seat). The README's
  verbs row and the verb table now say so, and the four edit verbs'
  list gains `ctrl+u` — the word's coat rides the crew since
  v3.0.93.
- Gates ALL GREEN.

## v3.0.97 — the amber drift (:diff wears the rail)

- **`:diff`'s finding now lives on the map.** The census stores the
  page lines that disagree with the disk (`ideDriftStore` — the
  additions and changes, sorted, unique, 0-based; a removal no
  longer stands on the page, so it cannot wear a tick), and the
  minimap's edge wears them AMBER — the pin's bar and the session's
  emerald keep their own edges, but now a drifted line announces
  itself at a glance until you act. The law of the leaving: `:w`
  sweeps the amber (the disk heard the page), a fresh page never
  inherits it, and an agreeing census clears it. A look, never an
  edit — the drift is the census's memory, nothing more.
- Docs debt PAID: the README gallery showed the playground twice
  and never showed level-2 (the movers) — all six scenes now sit in
  the table, and the headless renders were regenerated to prove the
  determinism (byte-identical to the shipped set).
- Selftest group 98: THREE drift laws (874 -> 877) — the sorted
  0-based store with its dedup, the rail's honest ask with the
  edges, the sweep. MY BUG (build): the drift helpers were placed
  before IdeDiffReport's definition — the compiler spoke; the
  helpers moved below the law they serve. Gates ALL GREEN.

## v3.0.96 — :diff (the page against the disk)

- **`:diff` — the page and the disk, spoken honestly.** A look,
  never an edit, never a save: the classic LCS builds the edit
  script, and the script's voices are the receipt — `N added (…)` ·
  `N changed (…)` · `N removed (…)`, the gutter's own numbers,
  samples capped at six with a `+k more` tail. A drop standing
  beside an add in the same block is one honest CHANGE (the
  rewrite's law — and the pairing is block-wise, so an add that
  walks BEFORE its drop pairs too); extras speak in their own
  voices. A removal points where the line once stood on the disk;
  an addition or change points at the page's line. An untitled page
  says the disk has never heard of it; a lost disk copy says the
  page stands alone; a bed too big to think (over ~2000 lines
  squared) refuses politely. `ideDiffCensus` is the engine's own
  law — pure lines in, report out.
- Selftest group 97: EIGHT diff laws (866 -> 874) — the agreement,
  the pure addition and removal, the rewrite as one voice, the
  interleaved block pairing (MY BUG: the first pass only paired
  drop-then-add; an add walking before its drop stayed unpaired —
  the block law fixed it), the extras, the newborn page, the
  honest refusal. Smoke 13u: TWO drives (203 -> 205) — the drift
  heard, the agreement heard. Gates ALL GREEN.

## v3.0.95 — the census's question (:changes <word>)

- **`:changes <word>` marries the census with the query.** A bare
  `:changes` lists every line this session wrote; a number leaps to
  the Nth; now a WORD asks the census which of those touched lines
  speak it — `N of M touched lines speak 'word'`, the matches listed
  in touched order, capped at eight with the `… +k deeper` tail. The
  find's case law answers (case-honest / case sleeps, named in the
  receipt), and the pin's diamond rides the listing (`7◆`) — one
  marking law across `:changes`, `:jumps`, and now the question. The
  helper `ideChangesAsk` is the engine's own law, so the selftest
  pins it; the leap path keeps its teeth (numeric args still parse —
  my first validation rewrite dropped the parse lambda's side
  effect, and the smoke's census-leap drive caught the regression
  before any push).
- Selftest group 96: FIVE question laws (861 -> 866) — the match
  set, the sleeping case, the honest case, the untouched line's
  silence, the empty question. Smoke 13t: TWO drives (201 -> 203) —
  the marker word's question, the honest refusal. Gates ALL GREEN.

## v3.0.94 — the selection's coat (ctrl+U over a live span)

- **A selection changes ctrl+U's breath.** With a live span, every
  word held WHOLE inside it takes its next coat in one breath, one
  named undo step — and a word the span CUTS is left honest: the
  selection never edits what it doesn't hold, teaching a clean drag.
  The law bites on both edges: a run cut by the span's head (the
  first row starting mid-word) skips too. Rows ride their own
  windows — the first row from c0, the last to c1, the middle rows
  whole — so a multi-row span coats every word of every row it
  holds. The breath drops the selection either way (the frame's
  own, the transpose's law); a span with no coatable word refuses
  honestly — no undo, no dirt. Under the hood the coat walk factored
  into `ideCaseNext` (shared by hand, crew, and span) plus
  `ideCasePlanSelection`.
- Selftest group 95: SEVEN span laws (854 -> 861) — the whole-word
  breath, the dropped anchor, the named undo, the cut word's
  honesty, the multi-row span, the digit refusal. MY BUG (caught on
  review before any gate): SelRange is an std::array<int,4>, not a
  struct — the first build spoke its name. Smoke 13s: TWO drives
  (199 -> 201) — the span end-to-end via shift+arrows, one undo
  restoring it. Gates ALL GREEN.

## v3.0.93 — the crew's coats (one breath, every hand's word)

- **`ctrl+U` edits THROUGH the crew.** With hands planted, the cycle
  thinks for every hand first — each rides its own word (on it,
  behind it, ahead of it) — then all the paints land in one breath
  behind ONE shared undo step. The cycle is length-preserving, so
  there is no seat math at all: the crew survives the frame, every
  hand keeping its seat. Two hands on one word think from the SAME
  text and take one coat, not two — replace is its own idempotence.
  A hand that cannot paint (bare digits) refuses alone; the others
  paint. Under the hood the cycle split into plan + apply
  (`ideCasePlanAt` / `ideCaseApply`) — the thought is per-hand, the
  paint is shared.
- Selftest group 94: SIX crew laws (848 -> 854) — the shared breath,
  the crew's survival, the one named undo, the lone refusal, the
  one-coat idempotence. Smoke 13r: THREE drives (196 -> 199) — the
  primary's coat, the crew hand riding a gap served by the word
  ahead, one undo peeling every coat. Gates ALL GREEN.

## v3.0.92 — the case cycle (ctrl+U, the word's three coats)

- **`ctrl+U` walks the word's coat.** The word under the hand cycles
  `hello` -> `HELLO` -> `Hello` -> `hello`, one breath per press: the
  whisper shouts, the SHOUT titles, the Title whispers — the wheel
  closes on itself. The hand rides a word ON it, BEHIND it (the open
  past the tail), or AHEAD of it (a hand before the words). The coat
  never moves a letter, so the seat never moves — press again and the
  same word takes its next coat. Digits and underscores ride along
  (`v2` <-> `V2`); a coat that would paint nothing bows out and the
  walk takes the next; a word with no letter at all (`123`) refuses
  honestly — no undo, no dirt. One named undo step ("case cycle"),
  pushed BEFORE the paint.
- Selftest group 93: TWELVE coat laws (836 -> 848) — the full wheel,
  the seat's promise, the word behind and ahead, the two-coat life of
  `V2`, the digit refusal, the empty line's refusal, the named undo
  and its restore. Smoke 13q: SIX drives (190 -> 196) — the wheel
  end-to-end, the undo peeling one coat at a time (the console's two
  rows bury the receipt under the re-run's breath; the name is the
  selftest's law), the page sitting as it sat. `--help` speaks ctrl+t (docs debt from v3.0.89,
  paid) and ctrl+u together. Gates ALL GREEN.

## v3.0.91 — the census (:count, the find's law as a number)

- **`:count [word]` — the census of a query.** A bare `:count` counts
  the searchlight's query everywhere in the document — no bar, no
  aim, just the number; `:count <word>` counts the word itself. The
  receipt speaks the case law honestly ("case-honest" or "the
  beginner way (case sleeps)"), the counting is the FIND's own law
  (`ideFindAll`: non-overlapping, like every editor) — one law, two
  windows. A look, never an edit: nothing dirties, nothing undoes.
  An empty query refuses with the honest pointer.
- Selftest group 92: three census laws (833 -> 836) — non-overlap,
  the case-honest shout, the sleeping case. Smoke 13p: TWO drives
  (188 -> 190) — the word's census and the borrowed query. The :help
  list and the verbs table carry :count. Gates ALL GREEN.

## v3.0.90 — the honest home (first non-blank, then the head)

- **`home` learned the three-way toggle.** The hand's first breath
  lands on the line's FIRST NON-BLANK — the indent's edge, where code
  actually begins; already there, the head (col 0); already there,
  back to the first non-blank. The dance the honest editors speak:
  `middle → indent edge → head → indent edge → …` A blank line's home
  is the head, honestly (there is no edge to find). `end` keeps its
  old law; `ctrl+home`/`ctrl+end` still take the document's edges.
- Selftest group 91: four home laws (829 -> 833) — the first
  non-blank landing, the head toggle both ways, the blank line's
  honest head. Smoke 13o: THREE drives (185 -> 188) — the toggle
  end-to-end via the header's honest Col census, with the pure air
  typed in swept away by one undo after. The :s/:sa README rows now
  speak the query's borrow (docs debt from v3.0.86, paid).
- Gates ALL GREEN.

## v3.0.89 — the transpose (the two neighbors trade places)

- **`ctrl+T` — the typo's honest fix.** The two neighbors around the
  hand trade places, the vim xp law: the hand ON a char (or between
  chars) swaps it with the one ahead; at the line's tail (the hand ON
  or AFTER the last char) the LAST two trade — so `teh` with the hand
  where you left it becomes `the`. The hand lands after the
  transposed pair. A line too short to hold a pair refuses honestly
  (no trade, no undo step, no dirt).
- One honest undo step ("transpose"), the census touched, the game
  hears about it; a live selection drops — the trade is the frame's
  own. The line-level dance already exists as alt+↑/↓ (the ride) —
  one law per verb, no duplication.
- Selftest group 90: seven transpose laws (822 -> 829) — the tail
  trade, the ahead trade, the hand's landing, the head trade, the
  short-line refusal, the named undo step and the restore. Smoke 13n:
  TWO drives (183 -> 185): the neighbors' trade end-to-end and the
  one-step restore. Gates ALL GREEN.

## v3.0.88 — the crew (many hands, one breath)

- **`:crew <n>` plants the crew — true multi-cursor editing.** A number
  plants that many extra hands straight below yours, each on the next
  line at the same column (clamped to that line's honest end; the
  document's edge refuses with the receipt). Type once and EVERY hand
  writes: the four edit verbs — typing, backspace, enter, forward
  delete — speak through every hand at once, highest hand first so no
  hand's edit shifts another's ground.
- **ONE law, many mouths.** The single hand's four verb laws were
  pulled out whole (`ideTypeCharAt`, `ideBackAt`, `ideDelAt`,
  `ideEnterAt`) and both the solo path and the crew now speak the same
  helpers — the bracket pairs, the closer-skip, the pair-eat
  backspace, the indent-inheriting split, the pins and the census
  rides: byte-identical behavior, provably no drift. Crew-only laws on
  top: hands that land together merge; a hand landed on a row another
  hand's join erases rides the seam (row and column remapped honestly);
  one undo step per frame, named "the crew's typing" (and kin), with
  the same quick-hands coalescing the solo hand obeys — and the crew
  itself rides the restore (undo brings the hands back).
- **A transient crew.** Any frame that is not one of the four verbs —
  movement, a click, esc, a command — dissolves it back to the single
  hand; a bare `:crew` bows the hands out with the receipt; an undo
  past the crew's birth or a page open leaves the hands behind. The
  header carries the count ("· 3 hands"); every hand burns a humbled
  violet caret on the pane — the SAME cell law as the primary
  (visual row under the fold), dimmed so the primary stays brightest.
- Selftest group 89: seventeen crew laws (804 -> 821) — the plant, the
  clamp, the census, the edge's refusal, typed-through-hands, the pair
  law riding, the bite and the join in one breath, the seam's remap,
  the split's shift-bump, the undo restoring hands and document, the
  dissolve on movement and on esc. Gates ALL GREEN.

## v3.0.87 — the eye's walk (up/down ride the fold's rows)

- **↑/↓ walk VISUAL rows under the fold.** From a line's continuation
  row, up lands on the line's OWN head — not the line above — and the
  eye's column is kept, clamped to the landing row's honest width
  (a row boundary the cursor cannot occupy resolves to the row's last
  true cell). The fold asleep (or a walk off the document's edge)
  hands the move back to the logical law — the identity is untouched.
- The walk rebuilds the fold's layout from `lastTextW` — the width
  the last draw just painted — one frame stale at worst, so the keys
  speak the SAME geometry the paint spoke. shift+up/down extend the
  selection through rows exactly as they extended it through lines.
- Selftest group 88 grows five walk laws (799 -> 804); smoke grows
  the walk's three-step drive (175 -> 178): the hand rides the
  continuation row, up lands on the line's own head (Ln holds), the
  next up climbs to the line above. Gates ALL GREEN.

## v3.0.86 — the query's tongue (:s//new borrows the find)

- **`:s//new` speaks the searchlight's query.** An empty old that
  still carries the slash borrows the live find query as the old —
  the find and the swap share one bed law, so the word you searched
  is the word you replace (`:s//Y` on the hand's bed, `:sa//Y` across
  the whole document). A bare `:s` with no slash refuses as always —
  nothing is guessed, and the receipt says when the query spoke
  ("the query's old — N replaced...").
- **The hyphen's law.** The fold now breaks rows after `-` as well as
  space — code's compound names (left-right-left, self-documenting
  dashes) part honestly at the dash instead of taking a hard cut
  mid-word. A compound that fits never breaks.
- **`:stats` speaks the longest line** ("· longest N") — the fold's
  companion census: before the fold even speaks, a hand can see
  whether anything will fold (longest > the pane's width), and by how
  much the document's worst offender offends. Pure law, selftested.
- Selftest group 87 grows four laws (795 -> 799); smoke grows the
  longest-line receipt and the borrow's drive (173 -> 175). Gates ALL
  GREEN.

## v3.0.85 — the fold (:wrap — the long line's courtesy)

- **`:wrap` folds long lines into the pane.** The slide chops what the
  pane cannot show; the fold breaks the line at the last space the row
  can hold instead (a word longer than the pane takes the honest hard
  cut), one logical line painting as many rows as it needs. A second
  `:wrap` wakes the slide again. While the fold speaks, the slide
  sleeps (hcol rests at zero), the 79/99 guides rest with it (a folded
  line has no honest column), the gutter names a line on its first row
  and wears a dim ellipsis on its continuations, and the header
  carries `· wrap`.
- ONE geometry law: the fold's layout is built fresh every draw —
  rows, owners, offsets — and wrap OFF builds the identity (one line,
  one row), so the pager, the pointer, the wheel, the drag's edge
  pull, :center and every glow speak visual rows through the same
  table. No two laws ever disagree about where a byte lands.
- Selftest group 86 grows eleven fold laws (784 -> 795); smoke grows
  the fold's drive — the receipt, a typed line past the pane's width
  painting its continuation gutter, the second toggle, and the slide's
  honest unfold (169 -> 173). Gates ALL GREEN.

## v3.0.84 — the vim tongue (:o and :e speak the ledger)

- **`:o` and `:e` ARE `:open`** — two names the hands already know,
  one law: a bare verb reopens the ledger's head, a file name rides
  (the ledger resolves a tail first — the same courtesy :recent
  speaks — then the open is honest, the welcome back keeping the
  hand). `:e` re-reads the current page in one verb; the full help
  names both.
- Selftest group 85 grows three parse laws (781 -> 784); smoke
  grows the :e re-read drive (168 -> 169). The usage hints whisper
  the vim law as you type.

## v3.0.83 — the vault's portrait (the README table completes)

- The vault's real headless portrait (960x540, captured by the
  engine's own `--screenshot`) takes its seat in the README's
  campaign table — the six-scene demo is fully pictured, every
  scene, no stubbed cells.

## v3.0.82 — the vault (level-5 joins the campaign)

- **The campaign grew a sixth scene: level-5, the vault.** It opens
  after the gauntlet's last door: two counter-phased lifts trade the
  first pit, a saw patrols the high deck's airspace, a ferry crosses
  under a second saw, and a fang-lined last stretch guards the door
  home. Five gems — one per machine, none free. The chain is
  playground → the gap → the movers → the climb → the gauntlet → the
  vault → back home.
- The gates render the vault headlessly (entities=22) and resolve
  the extended chain; the campaign field guide and the README's
  campaign section tell the vault's story.
- A game-side round: the IDE had nine features in nine releases —
  the vault keeps the engine's demo campaign honest for authors.

## v3.0.81 — the other face (:sa; :42 is a goto)

- **`:sa/old/new` — the swap's other face.** The WHOLE document is
  the bed: every byte-exact occurrence across every line trades, one
  undo step holds the entire take ("N replaced on M lines across the
  document"). The same law as :s, spoken by the same
  ideReplaceSel — the bed is simply the biggest selection a document
  can hold; a clean document refuses with the words standing.
- **`:42` is a goto.** A bare number is vim's law — the goto's
  absolute form, spelled the way the hand thinks it. 1..99999, the
  parse refuses a number with letters; `:1` jumps to the very top.
  The relative forms (+N/-N) stay :goto's own.
- Selftest group 85 (9 asserts) 771 -> 781; smoke 13i3 grows the
  document-wide trade and the bare-number jump (166 -> 168).

## v3.0.80 — the swap (:s/old/new — the bed's bytes trade places)

- **`:s/old/new` — find & replace, the house way.** Every
  byte-exact occurrence of old becomes new on the selection's lines
  (or the hand's line alone — the sort family's bed law). "3
  replaced on 2 lines — one undo step takes it back"; an empty new
  is a deletion; a newline in the new is refused (the bed never
  grows); an empty old is refused by name.
- **The match is EXACT.** The searchlight forgives case, the swap
  does not — a replace that guesses case would rewrite what it was
  not asked to touch. Only the lines that actually changed carry a
  touch (the census stays honest); ONE restore point named
  "replace", taken only when something matched (a clean bed takes no
  phantom step — "'absent' is not on this bed — nothing replaced").
- **The parse grew one special token.** `:s/old/new` has no space —
  the slash makes the verb token, so the split-by-space rule steps
  aside for exactly the "s/" prefix; a bare `:s` without its slashes
  is no verb at all. The handler splits on the FIRST slash (new may
  carry more; old may not).
- Selftest group 84 (12 asserts) 759 -> 771; smoke 13i3 (3 checks)
  163 -> 166 — the trade, the landing, and the clean-bed refusal,
  through the real pty.

## v3.0.79 — the rebalance (:center; the census joins :stats)

- **`:center` — the view centers on your hand.** z. in vim's tongue:
  the hand rides the viewport's middle (the SAME page the draw and
  the wheel use), clamped to the document's honest edges — a hand
  near the top keeps the top, a hand near the bottom keeps the
  bottom; the middle is a preference, the document is the law. A
  look, never an edit: nothing dirties, nothing undoes. The pure law
  is `ideCenter` in edit.hpp (top = curR − page/2, clamped); the
  smoke drives a mid-document line to the gutter's middle row.
- **`:stats` speaks the census.** The document's first line now ends
  "· N changed this session" when the session has touched anything —
  the census's third face (the header badge, the map's emerald
  ticks, and now the stats receipt) — so the count answers in the
  same breath as the words and chars.
- Selftest group 83 (6 asserts) 754 -> 759; smoke 13i2 (2 checks)
  161 -> 163 — the landing receipt and the gutter's middle row,
  through the real pty.

## v3.0.78 — the take, listed (:record shows its work; :macro N)

- **The recorder's stop receipt lists the take.** `:record` ends and
  names the register verbatim — "the recorder rests — 2 verbs in the
  macro (stats · words) — :macro plays it" — capped at four with the
  "… +N deeper" tail, so a long take stays one honest line. The
  answer to "what did I just record?", at a glance.
- **`:macro N` runs the take N times.** A bare `:macro` plays once;
  `:macro 3` walks the register three times over (1..99, the parse
  refuses a wild count). The start receipt speaks the choreography
  ("playing 2 verbs × 3") and the done receipt lands "the macro ran
  — 2 verbs × 3, done" — six 60fps verb-frames inside the first
  one, receipts honest throughout.
- `:record` keeps its no-arg law (the take IS the typing); the bar's
  usage hint names the count. Selftest group 82 grows two parse
  laws (752 -> 754); smoke 13k grows the listed take and the ×3
  replay (159 -> 161).

## v3.0.77 — the register (:record captures, :macro replays)

- **`:record` records a macro of verbs.** Start it, run verbs —
  :trim, :sort, :goto, :stats, any of them — and each well-formed
  line joins the register verbatim; `:record` again ends it and
  counts the take ("the recorder rests — 2 verbs in the macro —
  :macro plays it"). A fresh recording starts from an empty register;
  the register is a session fact, surviving opens and reloads.
- **`:macro` replays the register** through the SAME dispatch the
  bar speaks — one verb per frame, in the order it was recorded,
  every receipt honest. The replay refuses while the recorder is
  live, refuses an empty register ("nothing recorded — :record
  starts a macro"), and announces its end ("the macro ran — 2
  verbs, done"). The recorder never records itself (:record and
  :macro are the two meta-verbs).
- **THE SEAM this release was built on:** the verb dispatch — one
  600-line if-else chain buried in the bar's enter handler — is now
  a first-class `runCommand(line)` lambda, the ONE law for the bar's
  enter AND the macro's playback. The two loop-breaks (:q, :wq)
  became quit returns. Two dispatch bugs died on the way: a
  cmdBuf.clear() that ate the verb before the parse (every verb
  dispatched empty — the zen cascade caught it), and a silent
  python replace that skipped the recorder capture (the register
  stayed empty — the 13k checks caught it).
- Selftest group 82 (5 asserts) 747 -> 752; smoke 13k (4 checks)
  155 -> 159 — the record, the count, the replay, and the done
  receipt through the real pty. `:help` lists both verbs; the bar
  whispers their usage.

## v3.0.76 — :help <verb> (the bar's whisper, promoted to the console)

- **`:help <verb>` teaches one verb's law.** `:help sort` speaks
  ":sort — order the selected lines; all-number beds count (2 before
  10)" into the console, where it can be read slowly — the SAME hint
  table the bar whispers while you type, now reachable as a command.
  A bare `:help` still lists every verb (and now names the new way:
  "or :help <verb>"); an unknown verb refuses honestly; a two-word
  argument is refused by the parse ("one verb at a time").
- **A stage-law bug the gates caught:** the help handler was the
  only verb that did not takeStage() — typing `:help <verb>` left
  the studio in play, the receipt pushed into a console nobody was
  showing, and every later verb's receipt read blank. One line
  fixed it: every verb takes the stage — a law, not a suggestion.
- Selftest group 81 (5 asserts) 742 -> 747; smoke grows the
  help-teaches check (154 -> 155).

## v3.0.75 — the census wears the pins (one marking law, two listings)

- **`:changes` speaks the pins' diamond.** A touched line that is
  ALSO a pin reads "55◆" in the census, exactly as it does in the
  :jumps ledger — one marking law across both listings, so a line
  you wrote AND nailed down answers to the same glyph everywhere.
  The plain whisper keeps its plain law (the caller chooses).
- The new `ideTouchWhisper(s, marks)` overload rides the pins' own
  sorted-unique invariant, the same contract the jumps listing's
  cross-marks speak. Selftest group 79 grows two asserts (740 ->
  742); smoke 13i grows the census-diamond check (153 -> 154) —
  the pin lands on line 55, the edit touches it, and the census
  names it "55◆" through the real pty.

## v3.0.74 — the dice (:shuffle — the deal its seed can replay)

- **`:shuffle` deals the selection's lines like cards.** Fisher-Yates
  over the bed, honest coins, no alphabet, no mirror — the sort
  family's bed and refusals, ONE restore point named "shuffle", the
  hand resting at the bed's head, the selection let go. The bed of
  one refuses (one line has no other order); the census touches
  every line the deal rewrote.
- **The seed is the law's anchor.** `:shuffle 7` deals EXACTLY the
  same order every time — undo, re-select, deal again, and the same
  order lands (the replay law, proven twice: 9 selftest asserts and
  a real-pty drive that undoes and re-deals the same bed). A bare
  `:shuffle` rolls a seed from the clock and NAMES it — "3 lines
  shuffled (seed 7) — :shuffle 7 replays the deal, one undo takes
  it back" — so a lucky deal is replayable and shareable, the way
  a seed should be.
- **The pins ride their content.** A pin follows its words to the
  new home (the flip's law, told by a permutation — home built from
  the deal, the ledger re-sorted after), and the census rides its
  lines the same way before the bed-wide touch lands.
- Selftest group 80 (9 asserts) 731 -> 740; smoke 13j (3 checks)
  150 -> 153 — the deal, the receipt's seed, and the replay law
  through the real pty. `--help` and `:help` document the verb;
  the bar whispers its usage as you type.

## v3.0.73 — the cross-marks (the ledger and the pins agree)

- **`:jumps` wears the pins.** A leap that lands on a PIN now wears
  the pin's diamond in the listing ("now 55◆ · 30 · 7") — the ledger
  and the pins are two ledgers over one document, and the listing
  answers "where have I been" AND "which of those places did I nail
  down" in one breath. The walker's ">" prefixes its entry, the
  pin's "◆" suffixes every pinned one, and both can ride ONE entry
  (">30◆": you are walking on a pinned leap).
- **`:changes` learned to leap.** A bare `:changes` lists the census;
  a NUMBER leaps to the Nth touched line ("the hand leaps to the
  census's line 1 — line 55") — the census is not just a mirror, it
  is a set of addresses. The leap is a REAL one: planted in the
  ledger, the selection dropped, the landing mid-screen — the same
  laws the pins' `:bm` obeys. A wild index refuses honestly ("no
  such touch — :changes lists 2"), a clean page says so.
- **The walker owns the hint rail.** While the walker stands in the
  ledger's past, the IDE's hint row becomes the walk's teacher —
  "walk 2/6 of the ledger · alt+→ climbs out · ctrl+o deeper" —
  context that teaches the mode you are IN, the way the find bar
  counts its hits. A bookmark on the newest entry is the walker at
  now: the plain hints come back (the same law the listing's ">"
  speaks).
- The pure law is a third `ideJumpsWhisper(jumps, walkIx, marks)`
  overload (the 2-arg delegate keeps the old callers honest; `marks`
  rides the pins' own sorted-unique invariant). Selftest group 79
  (7 asserts) 724 -> 731; smoke 13i (5 checks) 145 -> 150, driving
  the cross-mark, the census's leap, the landing, and both hint
  rails through the real pty.

## v3.0.72 — the census (:changes — the lines the session wrote)

- **`:changes` reads the census of your session.** Every line the
  hand CHANGED since the page opened — typing, paste, split, join,
  sort, dedent, trim, comment, snippet, duplicate — listed ascending
  with its count ("2 lines touched since the page opened — 7 · 30").
  A clean page refuses kindly ("a clean page — nothing touched since
  it opened"). The census is the answer to "where did the last hour
  go?" in a file you have been living in.
- **The pins' structural law speaks here too.** A landing above slides
  a touch down; a cut carries the touches it holds out — a touched
  line dies WITH its line; a splice feeds every line it touched; the
  sort family's beds and the flip's mirror all keep the census honest
  through structure. Only the lines that actually moved are touched:
  a trim of a clean line touches nothing, a dedent of an unindented
  line touches nothing, a comment strip touches only real comments.
- **Undo rewinds the document, never the record.** A touch is a
  session fact — ctrl+z restores the page but the census keeps what
  the session wrote, clamped to the restored document. A reload
  restarts it: `:fresh`'s truth is the disk's, and the disk wrote,
  not you. Opening any page starts a clean census.
- **The map rail wears the session's hand.** A touched line wears an
  emerald tick on the map's edge (the pin's amber ▌ keeps its
  precedence) — see WHERE you have been writing in a big file,
  at a glance. The header speaks the count too ("· 3 changed"),
  dot-joined last so a crowded row sheds it first and keeps the
  older truths — whole segments only, never a mangled half-truth.
- The pure laws live in edit.hpp — `ideTouch`/`ideTouchShift`/
  `ideTouchErase`/`ideTouchClamp`/`ideTouchHas`/`ideTouchWhisper` —
  with the census wired into every edit path the IDE owns (the
  keystroke funnel, the clipboard, the block verbs, the snippet
  splice). Selftest group 78 (18 asserts) 706 -> 724; smoke 13h
  (4 checks) 141 -> 145, driving the census through the real pty:
  clean page, first touch, a second line ascending, and the
  reload's restart.

## v3.0.71 — the walker (ctrl+o / alt+←→ walk the jumps)

- **The jumps ledger is now walkable.** ctrl+o (the vim law) and
  alt+← step one leap into the past; alt+→ climbs back out — the
  IDE-standard navigate-back/forward pair, wired to the ledger the
  studio was already keeping. The receipt speaks each landing
  ("the hand walks back to line 30"), the edges refuse honestly
  ("the ledger's first jump — nothing behind it", "nothing ahead —
  you stand on the newest leap", "no jumps to walk" naming the
  three planters).
- **WALKING IS NOT LEAPING.** The walk moves the hand and the
  walker's bookmark — it plants NOTHING (the ledger kept its truth:
  where the hand has BEEN, not a second history of the walking).
  A real leap kills the bookmark and puts the walker back at "now".
- **`:jumps` wears the bookmark.** The listing marks the entry the
  walker stands on (">") so it answers both questions at once —
  where the leaps went AND where the walker stands ("now 7 · 55 ·
  >30 · 7"). No bookmark, a wild one, or one sitting on "now":
  the plain listing; a bookmark hidden beyond the 8-cap stays
  unseen.
- The pure laws live in edit.hpp — `ideJumpWalkBack`/`ideJumpWalkFwd`
  (the bookmark moves, the edges refuse), an `ideJumpPush(IdeState&,
  int)` overload (the leap kills the bookmark), and an
  `ideJumpsWhisper(vector, walkIx)` overload (the marker) — with
  the keys parsed in pollKeys: ctrl+o as byte 0x0f, alt+←/→ as CSI
  modifier 3 on 'D'/'C'. The three leap sites share the stateful
  plant. `--help` documents the keys.
- **A :fresh reload keeps the ledger.** The walker caught a law
  conflict the day after :fresh shipped: openScript cleared the
  jumps, but a reload is the SAME document re-read — history
  doesn't lie (the pins still go home: a marker may point at
  different words after the disk reshapes the page, history only
  remembers). openScript now takes `keepJumps`; only :fresh says
  yes.
- Selftest group 77 (19 asserts) — 687 → 706 groups: the empty
  refusal, the two steps down, the first-jump edge, the climb out,
  the newest edge, the bookmark's death by leap, the walk that
  never plants, the marker in place/on the tail/ignored, and the
  real-key walks through `ideKey` with receipts. Smoke section 13g
  (5 checks) — 136 → 141: alt+← twice, the marked `:jumps`, alt+→
  out, ctrl+o one more step.

## v3.0.70 — :fresh (the disk's truth wins the page back)

- **`:fresh` reloads the page from its file** — `:e!`'s twin. The
  editor's truth is negotiable; the disk's is not. A reload walks
  the ONE `openScript` path, so everything the studio already knows
  how to do, it does: the welcome back keeps the hand (the receipt
  says "the hand returns to line 7"), the undo history starts
  fresh, the pins go home with the document they were planted in,
  and the ledger remembers the file it re-read.
- **A page that was never written has no truth to win** — the
  refusal is honest and names the way out: "nothing on disk to
  reload — :w writes the page first".
- The grammar joins the no-arg family, the whisper says whose truth
  wins ("the disk's"), and `:help` carries the verb. Selftest group
  76 (3 asserts) — 684 → 687 groups: the verb, the argument refusal,
  the whisper. Smoke section 13f (2 checks) — 134 → 136: an edit
  saved (ZZZ), an edit left unsaved (QQ), the reload landing the
  hand back on line 7 with the disk's line on screen — QQ gone, ZZZ
  stays.

## v3.0.69 — the jumps (:jumps — where the hand has been)

- **`:jumps` lists the lines the hand LEAPT to.** Every real leap —
  a `:goto`, the pins' F2, the welcome back's landing — plants the
  line it landed on; the verb reads the ledger NEWEST first with the
  freshest named "now" ("the jumps, newest first — now 55 · 30 · 7"),
  capped at 8 with "… +N deeper". An empty ledger refuses honestly
  and names the three planters.
- **THE JUMP'S LAW: standing is not jumping.** Only a CHANGE of line
  plants — a `:goto` onto the line you already stand on and an F2
  leap whose only pin is the hand's own line change nothing, so they
  plant nothing. Returning to an old line is an honest leap and is
  remembered twice (the ledger answers "where have I BEEN", not
  "which lines exist"). The ledger caps at 32 — the oldest leap
  falls off — and clears with the document, because a jump belongs
  to the doc it leapt in.
- The law lives in pure, selftested helpers in edit.hpp —
  `ideJumpPush` (the plant: negative lines refused, head-dedupe, the
  cap) and `ideJumpsWhisper` (the reading) — with the three wiring
  sites sharing it: the `:goto` handler, the pins' F2 leap in
  `ideKey`, and the welcome back's landing in the one `openScript`
  path. `:jumps` joins the no-arg family, the whispers and `:help`.
- Selftest group 75 (13 asserts) — 671 → 684 groups: the plant, the
  stand's refusal, the wild line, the honest return, the 32-cap, the
  whisper's order/cap/1-based names, the F2 drive through the real
  `ideKey`, the grammar and the hint. Smoke section 13e (2 checks) —
  132 → 134: goto 30, goto 55, the list speaking "now 55 · 30 · 7"
  with the welcome back's 7 riding in it, and the stand that plants
  nothing.

## v3.0.68 — the welcome back (a reopen is a continuation)

- **`:open` and `:recent` remember where your hand stood.** Leaving a
  file plants its hand — the exact (row, col) the cursor held the
  moment you walked away — and reopening it lands the hand back
  there, the view jumping with it so the landing stays mid-screen.
  A reopen is a continuation, not a rewind: the receipt says so
  ("engine: opened game.py — the hand returns to line 7"), while a
  file's first visit still opens plainly at the top.
- **The LANDING law is honest about time.** The remembered hand is
  clamped to the document as it is NOW — a file that shrank keeps
  the hand on its last line, a column clamps into the line it lands
  in, a wild hand still lands inside the page, and a file vanished
  to zero bytes holds the hand at the top (an empty page indexes
  nothing — this was a real crash path in the first draft, caught
  before it ever shipped).
- The law lives in pure, selftested helpers in edit.hpp —
  `ideDocCurRemember` (a nameless file plants nothing),
  `ideDocCurLookup` (an unknown file has no past), `ideDocCurLand`
  (the clamp) — and the shell's one `openScript` path means
  `:open`, `:recent <name>` and a bare `:open` (the ledger's head)
  all share the welcome. The `:open`/`:recent` whispers name it
  ("the hand returns where it left").
- Selftest group 74 (11 asserts) — 660 → 671 groups: the plant, the
  nameless refusal, the lookup, the replace, the four clamps and
  the empty page. Smoke section 13d (7 checks) — 125 → 132: two
  files walked on a real studio, the first visits opening plainly,
  the reopen speaking "the hand returns to line 7" with the gutter
  standing on 7.
- README's version badge caught drifting (it said 3.0.66) — the
  badge now rides the release bump again.

## v3.0.67 — the quiet's ledger (:zen replays what it gathered)

- **`:zen` wakes with its ledger.** Receipts that gathered while the
  rail rested used to vanish under the two-row console window — the
  wake said "everything zen gathered waits below" and showed almost
  none of it. Now the wake COUNTS what it kept ("zen kept 3
  receipts") and replays the newest three in one digest line,
  oldest first so the ledger reads chronologically, long receipts
  trimmed honestly, the cap counting what it hides
  ("… +N more in the console"). The entering line itself counts —
  it was never shown either. A quiet that gathered two or fewer
  receipts leaves them where they lie (the window already shows
  them); a quiet that gathered nothing says so plainly.
- The law lives in a pure, selftested `ideZenDigest(console, since,
  kept*)` in edit.hpp; the shell only speaks it. `zenSince` rides on
  IdeState so the selftest can drive the quiet with the same
  keystrokes the editor uses. The `:zen` whisper now names the
  replay ("wakes it and replays its ledger").
- Selftest group 73 (9 asserts) — 651 → 660 groups: the count, the
  chronological order, the newest-three cap, the 47-bytes-plus-…
  trim, the short quiet's silence. Smoke section 13a7 (2 checks) —
  123 → 125: two dark `:ruler` receipts, the wake counts 3 and the
  digest rides the newest row; the zen wake receipt now asserts the
  honest count ("zen kept 1 receipt").

## v3.0.66 — the selection's own census (:stats)

- **`:stats` answers for the selection.** With a selection live, the
  stats now end with the SELECTION's own census — lines, words and
  chars of the honest slice (the first line from c0, the last line to
  c1, the middle whole), counted by the same law as the document and
  computed in a pure, selftested `ideSelStats` the shell only prints.
  It is spoken LAST so the console's two-row window shows the most
  specific truth newest — the console shows two lines, and the
  freshest word is the one that answers the question you just asked.
- Selftest group 72 (2 asserts) — 649 → 651 groups. Smoke section
  13a6 (1 check) — 122 → 123: a real shift+↓ selection, the census at
  the console's tail.

## v3.0.65 — the vim gutter (:relnum)

- **`:relnum` — the gutter counts from the hand.** The vim way:
  every line shows its DISTANCE from the cursor and the hand's own
  line keeps its true name — the numbers you navigate by (:goto +N,
  the rides, the pins) sit right where your eyes already are. The
  hand's row wears a brighter number so the anchor never hides, a
  second :relnum wakes the absolutes, :help's verb list and the
  whisper carry the law. The gutter's width rule is untouched —
  relative or absolute, the same honest column per extra digit.
- Smoke section 13a5 (4 checks) — 118 → 122: the hand keeps its name,
  rows 2-4 count 1 2 3, the absolutes return. Selftest stays at 649
  groups (the gutter is the shell's brush; the screen is its witness).

## v3.0.64 — the marker hunt (:todo)

- **`:todo` — the debts the document owes, named where they live.**
  Every line carrying TODO, FIXME, XXX or HACK is listed LINE-LED
  ("2: jump()  # TODO make it fair") — the number leads because a long
  census clips from the right and the line number is the one truth
  that must survive the clip (the :hist law again). The honest
  uppercase markers only: lowercase prose is not a promise (a "todo"
  in a sentence is a thought, not a debt — asserted). Entries trim
  their line and cap at 32 chars with an ellipsis, the list caps at
  six with an honest tail ("… +1 deeper in the file"), a clean file
  refuses with what would have landed there, :help's verb list and
  the whisper carry the hunt.
- Selftest group 71 (8 asserts) — 642 → 649 groups. Smoke section
  13a4 (2 checks) — 116 → 118: a real TODO typed at the doc's tail
  and hunted by its line.

## v3.0.63 — the census (:words)

- **`:words` — the document's word census, ranked and counted.** :stats
  counts words; the census NAMES them. The laws, all selftested:
  case is FORGIVEN (the beginner law — "The" and "the" are one word),
  punctuation is stripped from the EDGES only ("spawn", (spawn) and
  spawn, all count as spawn), the INSIDE is kept whole (gem-1 stays
  gem-1, on_hit stays on_hit), pure-punctuation tokens say nothing,
  ties take the alphabet so the order never wobbles, and the list
  caps at six with an honest tail ("… +2 more words"). The bar prints
  "engine: the census, most-said first — spawn×4 · gem-1×3 · the×3",
  an empty document refuses with the way out, :help's verb list
  carries the new name, and the whisper explains the law.
- Selftest group 70 (7 asserts) — 635 → 642 groups. Smoke section
  13a3 (2 checks) — 114 → 116: the census speaks and it counts.

## v3.0.62 — the hunt walks the file view

- **F3/shift+F3 in the file view — the scene's source joins the hunt.**
  The searchlight's walk was the IDE's alone — and the reason was a
  GATE, not a missing verb: pollKeys' whole `~` case was Ide-gated, so
  CSI 16~ never even reached the file view. The gate now carves F3 out
  first; `/`'s question survives its enter and F3 walks the hits of
  the scene source, shift+F3 walks back. ONE law with the IDE's F3
  (v3.0.55): strictly
  after the hand going down, strictly before going up, the full cycle
  IS the wrap, an empty question silent. A landing paints its line
  with a dark-amber bed and a lit gutter number, and the header rail
  speaks the walk: " /coin  hit 2/5 — F3 walks" — the ordinal honest,
  a fruitless question confessed with "no hits — / reasks".
- **The strict law for enter too**: the same question asked again
  walks from its last landing (it never re-lands the hit you stand
  on — the exact skip-class bug the IDE's hunt fixed); a fresh
  question starts from the viewport's head. And `/` reopens with the
  committed query pre-filled for editing — the question survives, back
  eats it, a new word re-asks.
- SS3 R (the xterm F3 dialect) now serves the file view as well as the
  IDE, and the view's hint rail names the walk.
- Smoke section 15 (12 checks) — 103 → 115: the view, the question,
  the landing's bed on its natural row (the file fits the view, the
  clamp keeps it honest), the walk, the walk back, the surviving
  question, the fresh question's own first hit, the clean exit.
  Selftest stays at 635 groups (the hunt lives in the shell; the
  screen is its witness).

## v3.0.61 — the second chance, spoken (:undo/:redo)

- **`:undo` / `:redo` — the ledger's twins, spoken from the bar.**
  ctrl+z and ctrl+y had the second chance to themselves; the bar now
  speaks it too. ONE law with the keys: the same walk, the same
  receipts ("engine: undo — typing · 4 steps left"), the same honest
  refusals ("nothing to undo", "nothing to redo"). The grammar puts
  them in the no-argument family (`:redo now` is refused with the
  family's usage), the whisper names the twins ("ctrl+z's twin",
  "ctrl+y's twin"), and :help's verb list finally carries :hist beside
  them (it shipped v3.0.58 without its name in the list — a word owed).
- Selftest group 69 (9 asserts) — 626 → 635 groups. Smoke section
  13a2 (4 checks) — 99 → 103: the walk there and back, the honest
  refusal, and the fold surviving the round trip on the real screen.

## v3.0.60 — one law for every whisper

- **`whisperOffer` — the completion clip law, written once.** Four
  whispers (:recent, :bm's pins, :snip's shelf and :open's ledger)
  carried the same eleven lines: join with " · ", end the line at the
  FIRST entry that does not fit the bar's honest width, never a cut
  word, never a half description. Now they all call one function, and
  the law has its own selftest target — a bar too narrow for even one
  entry holds its tongue, an entry fits a bar of exactly its width,
  and a full whisper leaves the line untouched.
- Selftest group 68 (5 asserts) — 621 → 626 groups. Smoke stays at
  99 (every whisper's outward word is byte-identical).

## v3.0.59 — the counting sort

- **`:sort` and `:rsort` grew numeric awareness.** When EVERY line of
  the bed opens with a number (air may lead it; decimals and
  negatives count), the order is by that number — "2" lands before
  "10", the way humans count, not the way bytes land, and 1.10 sorts
  as the 1.1 it truly is. Ties keep the byte order; negative numbers
  open honestly. One mixed line and the whole bed stays byte-honest —
  the classic sort, no surprises. The receipts name the law ("sorted
  3 lines by their numbers — 2 before 10"), and so do the bar's
  whispers.
- Selftest group 67 (15 asserts) — 608 → 621 groups. Smoke stays at
  99 (the letter beds' receipts still speak their law).

## v3.0.58 — the ledger, listed

- **`:hist` — the second chance, listed.** One honest line in the
  console: the undo ledger's names, NEWEST first ("join · drop ·
  typing · paste …"), capped at eight with the deeper truth confessed
  ("… +5 deeper"), the depth spoken in steps ("[12 steps back]"), and
  the redo's head riding after the divider when undo has already
  walked. An untouched doc refuses with the way out ("every edit you
  make lands here — ctrl+z walks it back"). The names are the same
  words the undo receipt speaks — the ledger and the walk share one
  vocabulary.
- Selftest group 66 (7 asserts) — 601 → 608 groups. Smoke grew the
  ledger section (the fold on top, the depth honest) — 97 → 99
  checks.

## v3.0.57 — the pen

- **`:w` and `:wq` follow the session's work.** The pen saves the
  studio's document when the studio has been on stage (it IS the boot
  stage for interactive runs) and the scene for play-only sessions —
  so `:w` in the editor finally means the SCRIPT, not the JSON behind
  it. A name saves AS that name: `:w other.py` writes the doc there,
  adopts the path, and the ledger remembers it; a refused write never
  steals the doc's own name. `:wq` saves and sleeps; a failed pen
  never quits — the honest error stays on the bar.
- **The .bak law is every document's now.** The scene always kept a
  `.bak`; scripts now do too — every save (the bar's pen, ctrl+s,
  even the auto-run's silent save before hosting) copies the file
  that exists to `<path>.bak` before writing. A first save has no
  past to keep; the receipts say "(.bak kept)" only when it is true.
- **The sdk is found beside the binary, not beside the cwd.** The
  hosted game's `PYTHONPATH`/`NODE_PATH` now resolve from the
  studio's own installation (<repo>/native/build → <repo>/sdk, with
  the cwd as fallback) — a studio launched from any directory hosts
  `from dxn3 import *` the same way. Found by the smoke's new
  hermetic harness: it now runs the studio in a private tmp dir, so
  saves never dirty the repo.
- Selftest group 65 (2 asserts) — 599 → 601 groups. Smoke grew the
  pen sections (the save, the .bak, the save-as, the disk truth, the
  :wq sleep, the fresh-studio exit) — 87 → 97 checks.

## v3.0.56 — the ride in the hands

- **alt+↑ / alt+↓ — :lift and :drop without opening the bar.** The
  xterm modifier digit 3 joins the arrow grammar (shift=2 selects,
  ctrl=5 nudges the view, alt=3 now rides). The bed law is the bar's
  own: the selection's lines move as one block, or the hand's line
  when nothing is selected; the pins ride along (the displaced
  neighbor's pin lands where the neighbor went); the hand lands on
  the block's head; each ride is ONE undo step ("lift"/"drop"); the
  edges refuse with the honest receipt — "nothing above to lift
  into" / "nothing below to drop into" — never a phantom step, and
  the receipts name the ride exactly as the verbs do.
- Selftest group 64 (11 asserts) — 588 → 599 groups. Smoke grew the
  ride-in-the-hands section (the edge refusal, the lift, the tail's
  truth, the drop home, the clean handoff) — 81 → 87 checks.

## v3.0.55 — the hunt

- **F3 and shift+F3 — the walk that outlives the bar.** Close the
  searchlight with esc and the hunt goes on: F3 hops to the next hit
  of the last query, shift+F3 walks back, both wrapping around the
  file. The hits are recomputed live before every step (the doc may
  have moved since the light rested), the console speaks the count
  ("hit 2/7 — line 12") because with the bar down there is no
  counter, and the walk is a look — nothing dirties, nothing undoes,
  any selection is left behind like every hop. F3 works inside the
  bar too, and the bar itself now whispers "enter/F3 next".
- **THE STRICT LAW — a real find bug fixed.** enter used to aim the
  light at the first hit at/after the hand and then step PAST it —
  so a hand standing BETWEEN two hits skipped its own next hit and
  wrapped early. One law now rules both stances: the next hit is the
  first one STRICTLY after the hand (the previous hit, strictly
  before, for shift+F3). A hand on a hit walks to the following one;
  a hand between hits lands on its next one. The xterm grammar gets
  F3 too: SS3 R (ESC O R) walks as well, while a CSI R cursor
  position report stays silent.
- Selftest group 63 (15 asserts) — 573 → 588 groups. Smoke grew the
  hunt section (the count, the landing's inverse video, the wrap,
  the walk, the walk back) — 72 → 81 checks.

## v3.0.54 — the ride of the jump

- **`:goto +N` and `:goto -N` — the jump rides from where the hand
  stands.** The absolute form stays 1-based (`:goto 42` is line 42);
  the relative form climbs or descends N lines from the hand, both
  clamping to the document — a jump never lands outside the world.
  The receipt speaks the ride ("jumped down 3 — now at line 8"), the
  whisper names the form, and zero rides nothing (refused with the
  honest usage).
- Selftest group 62 (9 asserts) — 564 → 573 groups. Smoke grew the
  jump block (absolute, +3 down, -2 up) — 69 → 72 checks.

## v3.0.53 — the fold

- **`:join` — the selection's lines say it once, in one breath.**
  Each line trimmed, the pieces separated by one honest space, pure
  air contributing nothing. The bed is the selection's lines; with
  no selection the hand's line folds with the one below (vim's J
  law — the fold's natural home). A same-line bed folds nothing, a
  bed on the last line has nothing below — both refuse without a
  phantom step. The uniq's pin law speaks (a pin on a folded line
  dies, the world beneath slides up); the hand rests at the SEAM,
  where the first fold landed.
- Selftest group 61 (13 asserts) — 551 → 564 groups. Smoke grew the
  fold section (the receipt, "zz aa" at the seam) — 67 → 69 checks.

## v3.0.52 — the echo

- **`:dup` — the selection's lines say it twice.** The copies land
  directly below the bed, the originals keep their pins (a pin marks
  a line, not its echo), and the world beneath slides down by the
  bed's size. With no selection the hand's line is the bed (the
  ride's law); the hand lands on the COPY's head — the fresh work is
  the echo. Never refuses: the hand's line always says something
  twice.
- A real bug fixed on the way in: the first implementation inserted
  the bed's iterators into their own vector — reallocation dangled
  the range and the copies landed as garbage. The bed is copied
  first now; the selftest caught it in both beds.
- Selftest group 60 (11 asserts) — 540 → 551 groups. Smoke grew the
  echo section (the receipt, original and echo in view) — 65 → 67
  checks.

## v3.0.51 — the ride

- **`:lift` and `:drop` — the selection's lines step one line up or
  down.** No alphabet, no mirror: the bed slides one neighbor over
  and the neighbor walks around it. The bed is the selection's lines
  — and with no selection, the hand's line (the move's natural
  home). The pins RIDE their lines and the displaced neighbor's pin
  lands where the neighbor went, the ledger re-sorted (the move is a
  cousin of the flip); the hand rides the block's head; a bed
  pressed against the edge takes no snapshot and no step.
- **The pins walk back through undo.** A real fix the ride flushed
  out: the undo snapshot carried the document and the hand but NOT
  the pins — so undoing a pin-moving operation (uniq, rev, and now
  lift/drop) left pins pointing where the redo-world had put them.
  IdeSnap now carries the ledger, and undo/redo restore it: every
  step back in time takes the pins with it.
- Selftest group 59 (17 asserts) — 523 → 540 groups. Smoke grew the
  ride section (the drop, the neighbor's slide, the lift home) —
  61 → 65 checks.

## v3.0.50 — the shelf that speaks

- **`:snip ` whispers the shelf, described.** Typing `:snip ` in the
  bar now speaks every snippet name with its one-line description —
  "fn — a named function · tick — the every-frame hook · … · main —
  a whole playable scene" — the same words for every dialect (a
  "tick" is the every-frame hook whether the file speaks py, js or
  cpp). The typed prefix narrows by NAME with the description riding
  along; the ledger's clipping law ends the line before a cut word,
  never a half description; and the shelf is the file's own dialect
  (cpp speaks five, js seven, py eleven). The shelf also speaks BARE
  now (the gallery's law) — before this round it waited for a first
  letter.
- Selftest group 58 (10 asserts) — 513 → 523 groups. Smoke +2 (the
  described bare shelf, the narrowed description) — 59 → 61 checks.

## v3.0.49 — the breath

- **`:indent` and `:dedent` — the selection's lines step one level
  right, or back.** The transform family's sibling: the same bed (a
  selection names lines — and a same-line one counts, because one
  line is a fine bed for a breath; tab and shift+tab already own the
  hand's line, the verbs own the selection's), ONE restore point
  named for the verb, the hand resting at the bed's head and riding
  the shift, the selection let go. The trim's law honored both ways:
  a line of pure air keeps its silence (no indent gathers on
  emptiness), a line with no leading air gives dedent nothing — and
  what would not move is counted BEFORE the snapshot, so a bed with
  no work takes no phantom step. The pins hold their lines — a
  breath moves no line.
- Selftest group 57 (19 asserts) — 494 → 513 groups. Smoke grew the
  breath section (the count, the four honest spaces, the round trip,
  the refusal) — 54 → 59 checks. One timing law recorded: a verb's
  auto-run spark burst still flies when the NEXT verb's frame is
  read — quiet-settle 2.5s before asserting body text.

## v3.0.48 — the diamond button

- **The pin's diamond is a button.** A plain click on the gutter's
  edge of a pinned line — the exact cell the `◆` rides — pulls that
  pin. A look, never an edit: the hand stays put (the click is spent
  on the ledger, not on the cursor), the receipt speaks ("pin pulled
  from line N"), and shift+click keeps its extend-the-selection law.
  A click on an unpinned line's gutter edge keeps the old law — the
  line start.
- The pointer's three gutter zones now speak cleanly: the diamond
  pulls, the number takes the line start, the code lands the hand.
- Smoke grew the diamond section (the ◆ visible, the pull, the
  stationary hand, the receipt, the sibling pin unharmed) — 49 → 54
  checks. 494 selftest groups stand.

## v3.0.47 — the flip

- **`:rev` — the selection's lines walk end for end.** The sort
  family's bed and refusals, but no alphabet has a say: the first
  line lands last, the last lands first. ONE restore point named
  "rev", the hand at the block's head, the selection let go.
- **The pins ride the flip to their mirrors** — the content-following
  law the collapse taught, applied to the one move that can unsort
  the ledger: each pin lands at `r0 + (r1 − m)`, and the ledger is
  re-sorted so the ":marks order" invariant survives the flip.
- Selftest group 56 (11 asserts: the flip, the mirrored pins, the
  refusals, the undo that lands the hand where it stood, the
  grammar) — 483 → 494 groups. The smoke grew the flip of the
  sort/rsort round-trip tail — 47 → 49 checks.

## v3.0.46 — the collapse

- **`:uniq` — lines that repeat back-to-back say it once.** A
  multi-line selection is the bed; NO selection means the whole
  document (uniq's natural home — its difference from the sort
  family, told out loud in the docs). The trim's law: nothing to
  collapse → no snapshot, no phantom step. ONE restore point named
  "uniq", the hand resting where the first line fell.
- **The pins speak the structural law honestly.** A pin on a fallen
  duplicate dies; a pin on a kept line rides the line to its new
  home (a newHome map, not a blind slide); a pin beneath the bed
  slides up by the count that fell. Undo still clamps the ghosts.
- Selftest group 55 (13 asserts: the whole-document law, the
  interleaved survivor, the selection bed, the pin map, the no-
  phantom law, the grammar) — 470 → 483 groups. The smoke grew the
  echo sweep (two typed "zz"s collapse to one, the view clamping up
  a row as the doc shrinks) — 45 → 47 checks.

## v3.0.45 — the case

- **`:upper`, `:lower`, `:title` — the selection changes its voice.**
  One law for three verbs: a selection is the bed (a same-line one
  counts — case is an in-line edit, unlike the sort family), ONE
  restore point named for the verb, the hand resting at the
  selection's head, the selection let go. Title stands each line's
  word-starts up and quiets the rest (`foo_bar 9lives` →
  `Foo_Bar 9Lives` — underscore and digits start words).
- The trim's honest law applies: what would not change is counted
  BEFORE the snapshot, so a letterless selection takes no phantom
  undo step. Refusals name the way out.
- Selftest group 54 (15 asserts: the three voices, the two-line bed,
  the edges holding, the word-start law, the no-phantom law, the
  grammar) — 455 → 470 groups. The smoke grew the voice dance
  (`dxn3` → `DXN3` → `dxn3` through the real bar) — 43 → 45 checks.

## v3.0.44 — the gallery

- **`:template` whispers the gallery.** The bar's eighth whisper
  source — type `:template ` and every starter's name speaks
  (`blank · shooter · cards · background · flappy · bounce · pong`),
  the typed prefix narrowing the list by the SAME law the verb's
  resolution follows: an exact name wins, a unique prefix resolves,
  and the whisper shows you all three outcomes before enter does.
- **The header counts the pins.** Next to `· zen` and `· sel N`, a
  document carrying pins now carries `· pins N` — the ledger's size
  at a glance, no `:marks` needed in big files.
- Smoke grew the gallery checks (bare whisper + narrowed prefix,
  through the real bar) and the pin-count header checks — 39 → 43
  checks. 455 selftest groups stand.

## v3.0.43 — the choir

- **The pins whisper: `:bm` completes itself as you type.** The bar's
  seventh whisper source — type `:bm ` and the ledger speaks
  `1) Ln 37 · 2) Ln 40` in the `:marks` order; the typed number
  narrows the choir to the pins it names, and the bar's honest width
  ends the line (the SAME clipping law as the ledger's whisper: the
  first entry that does not fit stops the line). An empty ledger
  stays silent — bare `:bm` already refuses with the way out.
- The leap verbs were already honest; now they are discoverable
  BEFORE you know the numbers — the whisper is the `:marks` list,
  one row earlier in the story.
- Selftest group 53 (7 asserts: the full choir, the narrowing
  prefix, prefix-by-head, the silent misses, the narrow bar, the
  one-entry fit, the pinless silence) — 448 → 455 groups. The smoke
  grew the whisper checks (bare + narrowed, through the real bar) —
  37 → 39 checks.

## v3.0.42 — the mirror

- **`:rsort` — the selection's lines land Z before A.** The sort's
  honest mirror: the same bed (a multi-line selection), the same
  refusals (no selection, a same-line one), the hand resting at the
  block's head, the selection let go, and ONE restore point of its
  own named "rsort" — undo unorders exactly as it stood. `:sort`
  then `:rsort` on the same bed is a clean round trip.
- The bar whispers the descending law (`:rsort — the selected lines
  land Z before A, one undo step`), `:help` names the verb, and the
  README's command table and housekeeping bullet speak it.
- Selftest group 52 (9 asserts: the descending order, the named
  restore point, the undo, the released selection, the grammar) —
  439 → 448 groups. The smoke grew an rsort section (the round trip
  through the real bar) — 35 → 37 checks.

## v3.0.41 — the quiet

- **`:zen` — the console rail hides and the body breathes.** Two more
  rows of code on every screen: the rail's rows join the viewport, and
  the pointer speaks the same geometry (a click on the old rail row
  now lands in the document, the drag's edge sensor watches the body's
  new bottom, and pgup/pgdn follow the taller page). The header
  carries a small `· zen` so the mode never hides ITSELF.
- **The quiet is honest, not blind.** The searchlight keeps its own
  row while it is up — a query you cannot see is a query that cannot
  end. Receipts gather silently until the quiet ends; waking the rail
  (`:zen` again) speaks "the rail is back — everything zen gathered
  waits below". The bar whispers the way in and the way out.
- **The smoke is now a shipped artifact.** `scripts/smoke.py` drives
  the REAL binary through a real pty — 35 checks across boot, zen
  (geometry, searchlight, pointer, wake), the live auto-run, the
  pins, the bar's refusals and `:sort`, ending on a clean exit. It
  encodes the laws that cost sessions to learn: the SPLASH LAW (the
  emblem eats the first keypress — wait it out), the MODE LAW (ESC in
  play quits; the bar opens from play), the COALESCING LAW (ESC and
  the next key must not share a pty frame; a coalesced arrow burst is
  one flag, not three), the SGR LAW (text row = doc line + 1; the
  frame parser walks the renderer's full-repaint protocol), and
  transition-frame dropping with a trimmed capture tail.

## v3.0.40 — the pins

- **Bookmarks: lines you pin so the hand can leap back.** `:mark`
  plants a pin on the hand's line — a second `:mark` (or `ctrl+F2`)
  pulls it. `F2` leaps to the next pin, `shift+F2` walks back, both
  wrapping the ends; `:bm N` takes the Nth pin (the `:marks` order),
  a bare `:bm` takes the next. `:marks` lists the ledger.
- **The pins are visible.** A pinned line's number burns amber in the
  gutter and a `◆` rides the gutter's edge (the hscroll `…` waits —
  the pin wins); on the minimap the pinned row carries an amber bar
  drawn last so it never drowns in the shape's bars.
- **The pins follow the document.** Every structural edit speaks the
  same law: lines landing above a pin slide it down (enter, paste,
  duplicate, snippet, block insert), lines cut beneath take the pin
  along (backspace/del joins, line cut, selection cut), a pin inside
  a cut dies with its line, and undo/redo prune pins the restored
  document never had. Loading a document starts a fresh ledger.
- **A look, never an edit.** Planting, pulling and leaping never
  dirty the document, never take an undo step, and every leap speaks
  its landing in the console; refusals (pinless leaps) name the way
  out (`:mark`).
- Selftest: group 50 (plant/pull/has, sorted+dedup ledger under
  out-of-order planting, wrap both ways, pinless refusals, the
  shift/erase/clamp laws, F2/shift+F2/ctrl+F2 through the real
  ideKey with no dirty and no undo) — 413 → 433 assertion groups.
- Discoverability: README command table + keys, `--help` keys card,
  the bar's usage hints, the console rail hint (F2 pins), `:help`.

## v3.0.39 — the fresh slate

- **ctrl+l wipes the console.** The console rail is where your game
  speaks — and where noise gathers: ticks, prints, stale engine
  notes. One keystroke clears the slate so the NEXT traceback reads
  at a glance, and the fresh console says so ("the console is fresh
  — ctrl+r replays your game"). The wipe is furniture, never an
  edit: the document never hears about it, nothing dirties, nothing
  undoes. Discoverability rides along — the `--help` keys card and
  the README name ctrl+l.
- Selftest: group 49 (the wipe with its receipt, no dirty / no undo
  step / no document change, and a second wipe staying one honest
  line) — 409 → 413 assertion groups, all green.

## v3.0.38 — the open book

- **Documentation caught up with the editor.** The README's command
  table now lists EVERY studio verb — `:open` (with its new bare
  form), `:recent`, `:template`, `:snip`, `:goto`, `:ruler`,
  `:minimap`, `:stats`, `:trim`, `:sort`, `:cases` — instead of
  hiding the IDE's vocabulary behind the play-mode verbs. The
  feature bullets tell the searchlight's two moods (:cases and the
  `(Aa)` marker), the ledger's bare `:open`, the honest wide gutter,
  the second wind, and the housekeeping verbs; the keys paragraph
  names them all in one breath.
- Polish: the header position line's doc example now shows the
  selection counter too (`Ln 12 · Col 8 · sel 87`), so a reader
  meets the drag's honest count before their first drag.
- Zero code changes — the binary speaks exactly as 3.0.37 spoke;
  409 assertion groups stand green.

## v3.0.37 — the ordering

- **`:sort` orders the selected lines.** Select a block (drag or
  shift+arrows), speak one word, and its whole lines stand in order,
  byte-honest A before B — the way every editor's sort-lines command
  speaks. The world outside the selection rests untouched, the hand
  lands at the head of the ordered block, the selection lets go, and
  ONE restore point named "sort" carries the whole ordering back on
  undo. Without a real bed the verb refuses honestly — no selection,
  or a same-line one (a single line is always already in order) —
  with the way out named in the console ("select the lines to sort
  first — shift+arrows, or drag"), never a phantom step.
- Discoverability rides along: the :help card names :sort and the
  bar's usage hint explains it while you type it.
- Selftest: group 48 (the honest count, the range ordered while the
  outside rests, the hand's landing, the named restore point, undo
  unordering exactly, and both refusals without phantom steps) —
  402 → 409 assertion groups, all green.

## v3.0.36 — the honest case

- **`:cases` flips the searchlight's sensitivity.** By default the
  light forgives — the beginner way, "hello" finds HELLO — and one
  command turns it strict: only the honest exact casing answers,
  with an "(Aa)" marker on the find rail so you always know which
  law is live. Flipping re-aims the light the INSTANT it turns (the
  hits and the current one are recomputed mid-search, no reopening,
  no retyping), and the console receipt names both directions
  ("find is case-SENSITIVE — Hello only greets Hello" / "find
  forgives case — hello finds HELLO"). The :help card and the bar's
  usage hint name the verb before enter is ever pressed.
- The law stays pure: `ideFindAll` reads `findCase` from the state —
  sensitive search is a straight substring read, forgiving search is
  the same lowercase dance as before, and nothing about hit order,
  the forward-aim, or the wrap changes.
- Selftest: group 47 (3 hits forgiving, the exact one strict with
  its row and column, flipping back reopens the net, and the
  forgiving light is deaf to casing in BOTH directions) — 397 → 402
  assertion groups, all green.

## v3.0.35 — the sweep

- **`:trim` sweeps every line's trailing whitespace.** Tail spaces
  and tabs come off every line; a line of pure air goes truly blank;
  clean lines rest untouched. The whole document is ONE honest
  restore point named "trim" — undo puts the air back exactly as it
  stood — and a document with nothing to sweep is refused WITHOUT a
  phantom step ("nothing to trim — the doc is already clean"). The
  console receipt names the work: "trimmed N lines of trailing
  air". Discoverability rides along: the :help card names :trim and
  the bar's usage hint explains it before enter is ever pressed.
- The verb's law lives in ONE pure function: `ideTrimTrailing` in
  edit.hpp counts what would move BEFORE taking the snapshot (the
  undo step must hold the air), sweeps, clamps the cursor to its
  line's new honest end, and returns the count.
- Selftest: group 46 (the honest count, tails off / pure air blank /
  clean lines rest, one named restore point, the cursor clamp, the
  clean-document refusal with no phantom step, and undo putting the
  air back) — 391 → 397 assertion groups, all green.

## v3.0.34 — the second wind

- **A sustained autoscroll pull doubles its pace.** Drag to the
  viewport's edge and hold: for the first 1.2 seconds the pull walks
  one line every 70ms — careful, precise; past 1.2s the SECOND WIND
  arrives and the notches come every 35ms — long documents are
  reached at speed. The law stays honest everywhere: the wind is
  spent by a release, by a stall (the dt > 0.5s guard), and by the
  hand leaving the edge — every restart walks slowly again, so short
  documents can never be skipped past. No new keys, no new state the
  hand must learn: the meter (`dragHold`) simply remembers how long
  the pull has been sustained, and the period halves.
- Selftest: group 45 (24 frames at one period each: 17 slow + 14
  fast notches with the ride contract intact; release → hold and
  meter rest; a fresh press walks slowly again — 5, not 10; the
  stall's honest reset; leaving the edge spends the wind) — 385 →
  391 assertion groups, all green. The float law rides along: 0.035
  is exactly half of 0.07 in binary, so the accelerated meter never
  drifts.

## v3.0.33 — the bare open

- **A bare `:open` reopens the ledger's head.** The verb you used to
  refuse without a file now answers with what you had LAST — one
  word, your most recent file, back on the stage. An empty ledger
  still refuses, honestly, with the way out ("name a path — :recent
  lists the ledger"). The grammar follows the truth: `:open`'s
  argument is optional now, exactly like `:recent`'s.
- **The :open whisper speaks YOUR files first.** Type `:open bo` and
  the ledger's matches whisper ahead of the filesystem's — full path
  OR basename carries the prefix, ledger order, then the cwd's
  scripts and the gallery's examples fill in behind, deduped (a path
  the ledger already spoke is never spoken twice), clipped to the
  bar's honest width by the SAME law as the :recent whisper. A bare
  `:open` whispers what enter WILL open — the head, or "(the ledger
  is empty — name a path)". The bar never lies ahead of the truth.
- Selftest: group 44 (the bare :open parse, ledger-before-filesystem
  order, dedup, the ledger-only ghost path that still whispers, the
  disk-only basename match, the silent ghost, the narrow bar, the
  empty ledger) plus the two assertions that rode along — the old
  ":open without a file is refused" now asserts the new law, and the
  version quad moved — 377 → 385 assertion groups, all green.

## v3.0.32 — the wide gutter

- **The gutter earns its width.** Four columns carried line numbers
  honestly to 999; now a bigger document EARNS its extra digit, one
  notch at a time — five columns from line 1000, six from line 10000
  (the draw speaks the number with `%*d`, so the digits simply fit).
  The rule lives in ONE place: `ideGutterWidth(lineCount)` in
  edit.hpp, and everything that speaks the body's geometry reads it —
  the draw, the pointer's cell translation (a click on a 1200-line
  doc lands one column further right, and lands TRUE), the 79/99
  ruler guides, the selection glow, the bracket glow, the cursor and
  the searchlight's wake. The pane's code window pays for the digit
  honestly: textW = editW − 1 − G − map rail, so a wide gutter can
  never push the minimap or the divider out of the pane.
- Selftest: group 43 (the four boundaries — 999/1000/9999/10000 — the
  empty and negative counts, and the pane-width arithmetic for a
  1200-line document) — 371 → 377 assertion groups, all green.

## v3.0.31 — the leap

- **ctrl+\\ jumps the hand to the partner bracket.** The partner
  glow's keyboard sibling arrives: with the hand on (or just past) a
  bracket, ctrl+\\ lands it on the matching ( [ { across any
  distance — the SAME honest match rule as the glow (the cell at the
  cursor, then the one behind it; quotes stay out of it). A leap is a
  look, never an edit: nothing dirties, nothing undoes, and any
  selection lets go when the hand flies. A bracket with no partner
  refuses the leap with the hand unmoved — the glow never lies about
  a pair, and neither does the leap.
- **Polish — discoverability.** The editor's rail hint names the leap
  ("ctrl+\\ leap") next to run/undo/clipboard, and the :help keys
  card gains its own line.
- Selftest: group 42 (the round trip, the cross-line pair, the
  behind-the-hand probe, the partnerless refusal, the plain-text
  refusal, the selection release) — 363 → 371 assertion groups, all
  green. Smoke: section 12i leaps a live hand across flappy.py
  (102 → 105 checks).

## v3.0.30 — the whisper

- **:recent completes itself while you type.** The command bar's
  whisper family grows its last member: type `:recent bo` and the
  bar speaks `sdk/examples/bounce.js` before enter is ever pressed —
  full paths whose path OR basename carries the prefix, ledger order,
  joined with " · ", clipped to the width the bar honestly holds. A
  bare `:recent` whispers the head of the ledger; an empty ledger
  says "(the ledger is empty)"; a ghost stays silent because enter
  will refuse it and the bar never lies ahead of the truth.
- Selftest: group 41 (basename and full-path prefixes, the ordered
  bare whisper, the tail name, the silent ghost, the empty ledger,
  the narrow-bar clip) — 355 → 363 assertion groups, all green.
  Smoke: section 12h watches the live bar whisper (99 → 102 checks).
- **Polish — the hint yields.** The bar's usage hint no longer bleeds
  through behind a shorter whisper: the whisper paints alone when it
  speaks, and the usage speaks only when the bar is silent.

## v3.0.29 — the autoscroll

- **A drag at the edge pulls the unseen into view.** The mouse
  vocabulary is complete: while the button is held and the hand parks
  on the viewport's top or bottom row, the view slides toward the
  unseen lines — one honest notch every ~70 ms, metered by a
  wall-clock accumulator. The hand IS the edge: every notch the slide
  reveals, the hand takes, so the selection grows from the anchor
  exactly like every desktop editor's autoscroll. The wheel's pager
  contract holds (the doc never dirties, the hand never leaves
  sight), a stationary press never pulls (a real drag needs an
  anchor), a long gap is an honest reset — never a catch-up jump —
  and the void clamp still ends every pull at the last full page.
- **Polish — the header counts.** While a selection rides with the
  hand, the header speaks its honest size: "Ln 3 · Col 4 · sel 87".
  A drag always says how much it holds, live.
- Selftest: group 40 (the pull metered, the bare-press refusal, the
  stall reset, the upward ride home, the void clamp, the sel counter)
  — 344 → 355 assertion groups, all green. Smoke: section 12g drives
  a real edge-park through the pty (94 → 99 checks) — the park's
  SGR row is 28, the body's last row, not 27 (the coordinate the
  first draft got wrong; the app's honest no-op taught the test).

## v3.0.28 — the guard

- **ESC owns its frame.** A bare ESC is a mode key, and when a busy
  pty delivers it coalesced with typing (the app stalled past a
  keypress burst), the text belonged to the next frame — but the
  editor happily typed it into the live document FIRST. The studio's
  own gate caught the result: a smoke run once typed `:recent` into
  bounce.js and the auto-run saved it. Now `ideKey` returns the
  moment it sees an ESC: nothing that follows an ESC in the same
  breath may touch the document. The corrupted example was restored
  from history and the guard keeps every document honest from here
  on.
- Selftest: unchanged (344 groups — the guard is a refusal, and the
  smoke's 94 checks now run clean with the example files byte-pristine
  through every drag, wheel and ledger step).

## v3.0.27 — the ledger

- **:recent — the studio remembers.** Every document this studio has
  hosted (the boot file, every template, every `:open`) lives in a
  twelve-name ledger, most recent first. `:recent` reads it aloud in
  the console rail; `:recent <prefix>` reopens — an exact name wins,
  a unique prefix (of the path OR the bare file name — hands think
  in file names) resolves, an ambiguous prefix lists its matches,
  and a ghost is refused honestly with a flash. Reopening a file
  moves it back to the front; the ledger never grows past twelve.
  One honest code path (`openScript`) serves both `:open` and
  `:recent`, so the stage-taking, the searchlight reset and the
  ledger-keeping can never drift apart.
- Selftest: group 39 (most-recent-first, dedup-to-front, the
  twelve-name cap, empty paths ignored, exact/unique/ambiguous/
  ghost resolution) — 336 → 344. Smoke: 90 → 94 checks — :open a
  real file, the ledger lists it, `recent bounce` reopens it, a
  ghost is refused.
- QA note: a refusal flash renders on the bottom row — which the
  IDE's console rail paints over. The verb therefore only takes the
  stage when it has something to SHOW (the list); refusals flash in
  play mode where they can be seen.

## v3.0.26 — the drag

- **Drag selects.** Button-motion tracking (`?1002h`, off at exit)
  completes the mouse: press where the selection starts, sweep, and
  the selection rides the hand cell by cell — across lines, through
  the horizontal slide, glow and all. Release, and the selection
  stays exactly where you left it; a plain click-press-release never
  selects (standard). Motion without the button is hover and moves
  nothing. The press/drag cells share one translation path with
  clicks, so the gutter, the map rail and the horizontal slide all
  speak the same geometry.
- Selftest: group 38 (press remembers, drag selects from press to
  hand, never dirty, release keeps the selection, hover moves
  nothing, plain clicks select nothing) — 330 → 336. Smoke: 85 → 90
  checks — press lands Ln 2, the drag rides to Ln 3 · Col 4, the
  release keeps the hand, hover moves nothing, zero leaked bytes.

## v3.0.25 — the wheel

- **The mouse wheel rolls.** SGR buttons 64/65 (wheel up/down) slide
  the editor's view three lines per notch — and in the file view too.
  The pager contract holds: the hand is never lost out of sight, so a
  scroll that would leave the cursor behind carries it along the
  edge (`ideScroll`, pure and selftest-covered). Looking around —
  clicks or wheel — never dirties the doc; your game never re-runs
  because you moved.
- **A real bug died on the operating table.** `ideScroll`'s first
  draft clamped the view to `lines − 1` while the draw clamps to
  `lines − page`; on documents that fit the viewport the two
  disagreed, the top oscillated, and the wheel died after one notch.
  The smoke caught it; the fix makes both maxes the same.
- Selftest: group 37 (ride down, ride home, the void clamp, zero
  no-op, the hand mid-view stays) — 323 → 330. Smoke: 80 → 85
  checks — flappy returns for the wheel (the ceremony's 16-line doc
  honestly has nothing to scroll), 8 down-notches show line-40's
  gutter with the hand riding to Ln 25, 8 up-notches come home, and
  no wheel bytes ever leak into the document.

## v3.0.24 — the pointer

- **The studio hears the mouse.** SGR click tracking (`?1000;1006h`,
  disabled on exit) feeds the parser real clicks: a left click in the
  code lands the hand on the exact cell (horizontal scroll included),
  a click on the gutter takes the line start, a click on the minimap
  jumps to the doc line under the hand, and a click in the game's
  viewport, console or header is nobody's — swallowed whole.
  `shift+click` extends a selection from the old hand, exactly like
  the shift+arrows; a bare click lets the selection go. Looking
  around never dirties the doc: no re-run of your game follows a
  click.
- **A latent bar bug dies with it.** The command bar never parsed CSI
  sequences, so an arrow key's `ESC[` faked a bare ESC and slammed
  the bar shut mid-thought. The bar parses now: a BARE esc still
  closes it, but arrows, mouse reports and DSR answers are swallowed
  whole, never leaked.
- Selftest: group 36 (click lands, wild clicks clamp, click
  deselects, shift+click extends, clickless frames leave the hand) —
  317 → 323. Smoke: 76 → 80 checks — SGR presses written straight
  into the pty land Ln/Col deterministically (code, gutter, map) and
  viewport clicks prove no leak and no dirty.

## v3.0.23 — the map

- **The minimap rides the right edge.** A six-column map of the whole
  document lives inside the editor pane's right border whenever the
  terminal is wide enough to spare it (split mode, 110+ columns).
  One doc line is one map row; leading whitespace compresses 2:1 so
  deep nests stay inside the rail, and text compresses to half its
  length rounding UP so even one character shows. The viewport's rows
  carry a soft band and burn brighter, the cursor's row is the
  brightest bar on the map, comments speak gray, find hits glow
  amber, blank lines keep one dim dot so the rows stay anchored. The
  map slides to keep the cursor centered once the doc outgrows the
  pane and never slides past either end. `:minimap` toggles it.
  The math (`ideMiniMap`) lives in edit.hpp, pure and selftestable —
  main.cpp only paints.
- **The undo receipt names the move.** Every restore point now
  carries a label — typing, backspace, enter, delete, selection,
  comment, duplicate, word bite, forward bite, indent, dedent,
  snippet, cut, paste — and `ctrl+z` says `undo — paste · 3 steps
  left` instead of a blind count. Labels ride the redo branch too,
  so `ctrl+y` speaks the same name coming back.
- **The shelf whispers from the rail.** A snippet word ending at the
  cursor (`tick`, `key`, `fn`, …) now names its boilerplate in the
  console rail's right seat — `⇥ tab expands 'tick'` — so the tab
  trigger is discoverable before you know it exists. No word, no
  whisper; the editor is not a barker.
- Selftest: groups 34 (bar math: 2:1 indent compression, blank dots,
  comment classification by the file's own prefix, hit glow, centered
  slide, viewport band, degenerate widths) + 35 (every undo label,
  receipts through undo AND redo, whisper/ghost silence) — 292 → 317.
  Smoke: 68 → 76 checks — the OSC 52 payload is now DECODED and
  compared against the selection, and the map's divider and bars are
  asserted present, gone (`:minimap off`), and back.

## v3.0.22 — the bridge

- **The system clipboard hears you.** `ctrl+c` and `ctrl+x` now also
  emit an OSC 52 escape carrying the clip (base64, `ESC]52;c;…ST`) —
  terminals that honor it (kitty, alacritty, wezterm, foot, iTerm2,
  Windows Terminal…) keep the OS clipboard in sync with the studio's.
  The internal ring stays the paste truth: `ctrl+v` pastes from the
  studio, so a terminal without OSC 52 support loses nothing.
  `ideClipText` joins the clip's lines and `ideBase64` encodes them
  honestly (RFC 4648, with the honest `=` padding).
- **An empty paste speaks up.** `ctrl+v` with nothing in the
  clipboard used to pretend to happen; now the console rail says
  `the clipboard is empty — ctrl+c first`, and the doc isn't dirtied
  (no pointless re-run of your game).
- Selftest: group 33 (clip text joins, base64 vectors, empty-paste
  receipt) — 284 → 292. Smoke: 67 → 68 checks (the copy window
  carries the `]52;c;` bridge bytes).

## v3.0.21 — the clipboard

- **`ctrl+c` / `ctrl+x` / `ctrl+v` — a real clipboard.** Copy takes
  the exact selection (character-wise) or, with none live, the whole
  cursor line (line-wise) — and never dirties the doc. Cut is the
  copy plus the deletion, one honest undo step; a bare cut lifts the
  whole line out and turns the clip line-wise. Paste splices
  character-wise clips at the cursor (tail text rides behind the
  block, the cursor lands at the clip's end) and drops line-wise
  clips in above the cursor line; a live selection is the paste's
  bed, replaced in the same undo step. Cut with a multi-line
  selection? The clip carries every line's shape.
- **Word-wise selection.** `shift+ctrl+←`/`→` extend the selection
  word by word — the anchor is born at the cursor and rides the same
  hops `ctrl+←`/`→` make, across line edges when they must. A plain
  move still drops it.
- **The pair ceremony.** Enter between a bracket pair splits into
  three lines: the naked middle line takes the cursor, `{` bumps it
  a level, and the closer keeps its ground on the base indent.
  Quotes stay honestly out — breaking a string literal is still just
  a split.
- **`ctrl+d` duplicates the whole selection.** With a multi-line
  selection live, every touched line is copied below the range and
  the copy carries both the cursor and the anchor with it. The plain
  single-line duplicate is unchanged.
- **The tab trigger.** Type a shelf name (`tick`, `key`, `fn`, …)
  and reach for `tab` — the word is eaten and the boilerplate lands
  in its place, tail text riding behind the block, the cursor at the
  block's end, one undo step to take it all back. Plain `tab` still
  gives four honest spaces (grouped like typing), a selected block
  indents every touched line (the selection survives), and
  `shift+tab` — a real `ESC[Z` parse — dedents the block or the
  hand's line by up to four spaces.
- **`:screenshot` whispers its default.** With no name typed and no
  shots in `exports/`, the bar tells you what enter WILL write —
  `exports/<scene>-N.png — the default` — before it writes it.
- Selftest: groups 31–32 (clipboard semantics, word select, the
  ceremony, multi-dup, tab triggers, block indent/dedent)
  — 241 → 284. Smoke: 50 → 67 checks, including a live
  clipboard round-trip on the flappy import line — and the smoke's
  own honest-quit fix (LESSON #4: the bar needs play mode; in the
  IDE a `:` types into the doc and the quit never lands).

## v3.0.20 — the selection

- **`shift+arrows` select.** The anchor is born at the cursor on the
  first shift-extension and the selection glows cell by cell as it
  grows — across lines, backward, whatever shape you draw. A plain
  move drops it; undo/redo drop it too; jumps (`:goto`, find-walk,
  template loads, `:open`) never drag a stale selection along.
- **Edits replace the range.** A typed character, backspace,
  forward-delete or enter with a selection live replaces the range —
  VS Code's contract — and the whole replacement is ONE honest undo
  step. A spanning cut joins the lines at the range's edges; an
  anchor equal to the cursor is no selection at all.
- **`ctrl+/` speaks multi-line.** With a selection spanning lines,
  the comment toggle touches EVERY line the selection covers — the
  first talking line decides whether the range gets stripped or
  dressed, blank lines are skipped, and the whole toggle is one
  undo step.
- Selftest: group 30 (extend/replace/span/cut/undo semantics)
  — 229 → 241.

## v3.0.19 — the ruler, the snippets and the edges

- **`:snip <name>` drops boilerplate from a shelf that speaks your
  file's language.** `tick` in game.py is `def on_tick(dt):`, in
  game.js it's `on.tick(() => { … })`, in game.cpp it's
  `g.onTick = [&](float dt) { … }` — every template checked against
  the real sdk/ contracts. The py shelf stocks eleven (fn tick key
  hit start loop ifelse class try imports main), js and cpp speak
  their own seven and five. An exact name wins, a unique prefix
  resolves (`:snip im` → imports), an ambiguous prefix lists, a
  ghost is refused with the full list — and the shelf whispers its
  names as you type. A blank line is the stage (the snippet takes
  it over), otherwise the block slides in after the cursor line,
  cursor resting at its end, one honest undo step.
- **The ruler: honest guides at columns 79 and 99.** Dim dots mark
  the classic margins in the editor pane — but only where the cell
  is blank, so the guide never paints over your code. `:ruler`
  toggles them off and back on.
- **`:stats` tells you what you're holding**: lines, words, chars,
  where you stand, which dialect the file speaks, whether the host
  is live.
- **`ctrl+home` / `ctrl+end` jump the edges** — the very top, the
  very bottom, cursor honest, the document never dirtied.
- **More whispers**: `:screenshot <part>` completes from the shots
  already in exports/, `:w <part>` completes the campaign's scene
  paths, `:snip <part>` completes the shelf.
- Selftest: groups 28–29 (the snippet shelf + the edges + grammar)
  — 206 → 229.

## v3.0.18 — the forward bite and the talking line

- **`ctrl+delete` eats the word ahead** — the exact sibling of
  ctrl+w: it bites precisely what ctrl+right would hop over, the gap
  and the run in one mouthful, punctuation runs included, an honest
  no-op at the line end, one undo step.
- **`ctrl+/` makes the line talk** (or hushes it). The comment prefix
  follows the file's language — `#` for python and shell, `//` for
  js and C-family, `--` for lua — lands after the leading whitespace,
  and strips again with the same keystroke, cursor along for the
  ride. The game hears about it: the live re-run fires like any edit.
- **`:template <name>`** loads a starter directly — `:template flappy`
  instead of cycling ctrl+n. Exact name wins, a unique prefix
  resolves, an ambiguous prefix lists the candidates, a ghost is
  refused with the full list. The ctrl+n gallery still cycles.
- Selftest: group 27 (the bite forward + the talking line + grammar)
  — 191 → 206.

## v3.0.17 — the long line and the partner

- **`ctrl+←` / `ctrl+→` hop word by word.** The same classification the
  ctrl+w bite uses — whitespace is a gap, a run of word characters or
  punctuation is ONE hop — but forward hops land at a run's end and
  backward hops at its start, the classic editor split. Hops cross
  line edges: an empty line is just a wider gap, and the hop never
  touches the document.
- **Long lines slide under the cursor.** Lines wider than the pane no
  longer end at a chopped `…` — the view follows the cursor with a
  small margin on whichever side you came from, an honest `…` marks
  the cut in the gutter, and the line end stays reachable (clamped,
  stable, and a line that fits never slides).
- **The bracket's partner glows.** Stand on a `(`, `[` or `{` (or just
  behind one) and its match lights up across the file — nesting and
  line edges respected, quotes are just characters, and an unclosed
  bracket refuses to fake a match.
- **The escape parser grew up.** CSI sequences are parsed whole and
  unknown ones are swallowed — `ctrl+arrows` used to leak `1;5C` into
  your code as text, mouse reports and DSR answers leaked digits, and
  split reads typed fragments. Nothing leaks now, and SS3 (`ESC O A`)
  arrows are understood too.
- **`ctrl+↑` / `ctrl+↓` nudge the view** without moving the cursor —
  the honest scroll that gets out of the way the moment you move.
- Selftest: groups 25 (word hops) + 26 (bracket match + the slide) —
  157 → 193.

## v3.0.16 — the bite and the leap

- **`ctrl+w` eats the word behind the cursor.** The gap counts as part
  of the bite, punctuation runs go in one mouthful, snake_case names
  stay whole, and an honest no-op at the line start. One undo step,
  like every structural edit.
- **`:goto <line>`** jumps the editor to any line — ctrl+g's sibling
  for lines without a traceback. The studio takes the stage mid-file
  (the jump lands four rows down for context) and the console names
  the line it landed on.
- Selftest: group 24 (the bite) + `:goto` grammar asserts — 146 → 157.

## v3.0.15 — the searchlight: find, pairs, the copy machine

- **`ctrl+f` finds in your file.** The searchlight is case-insensitive
  the way beginners think, aims at the first hit at or after your
  cursor, and `enter` walks you hit by hit with a honest wrap-around.
  Every match glows behind the text — the current one burns amber —
  and the rail counts them live (`2/7 · enter next · esc done`).
  Typing under the searchlight feeds the query, never the buffer, and
  backspace on an empty query closes it.
- **The header knows where you stand**: `Ln 12 · Col 8` rides next to
  the file name, always current.
- **Pairs carry their own closers.** `(`, `[`, `{` and quotes type
  their other half; a closer you already have is skipped over, never
  doubled; backspace between an empty pair removes both halves; an
  apostrophe inside a word (`don't`) never hijacks a pair; nesting
  (`f([x])`) just works.
- **`ctrl+d` duplicates the line** under the cursor — column kept,
  one undo step, the copy takes your place.
- **`:open <file>`** loads any script into the studio from the command
  bar. Your cwd and the `sdk/examples/` gallery whisper their file
  names as you type (matching on the file name, showing the path); a
  ghost file is refused with an honest error, and a running game hands
  the stage over cleanly.
- **Fixed: the command-bar whispers were dead code.** The completion
  matcher looked for a leading `":"` that `cmdBuf` never carries —
  `:scene` name completion never drew a whisper since it shipped. The
  matcher is fixed, and `:open` joins it with file-name matching.
- **Fixed: a pasted command died silently.** Text landing in the same
  read as its enter was dropped before `cmdBuf` ever saw it; the bar
  now absorbs same-frame typing, so paste-style commands execute.
- **Fixed: command frames leaked into the editor.** A `:open` executed
  in the same read as its text let that text then be typed INTO the
  freshly loaded document (and the auto-run saved the corruption back
  to the file — a shipped example came home with the command as its
  first line). A frame the command bar polled is now the bar's alone.
- **Fixed: saves keep their trailing newline.** `ideSave` now writes
  POSIX-honest files ending in `\n`, so loading an example and running
  it no longer rewrites the file with a stripped last byte.
- **Fixed:** forward-delete (`del`) never marked the document dirty —
  a joined line would not re-run the game until the next edit. Now
  `del` and `ctrl+d` both flag the auto-refresh honestly.
- Selftest grew two groups (find-in-file, pairs + duplicate): 33 new
  asserts, 146 total.

## v3.0.14 — the block rides down: auto-indent

- **Enter carries the block.** A new line inherits the previous line's
  indentation; a line ending in `:` (python) or `{` (C-family) bumps
  one level before the cursor lands, and splitting before a closer
  (`else`, `elif`, `except`, `finally`, `case`, `default`, the whole
  `end` family) drops back a level instead of staircasing into the
  margin. Whole-word matching, so `endless` never dedents.
- Typed code keeps flowing at the new indent — write `def on_tick(dt):`,
  press enter, and the body line is already where it belongs.
- Nine more selftest asserts (113 total): opener/closer units,
  trailing-space tolerance, mid-line splits, closer dedents, and the
  proof that auto-indent splits undo like any other edit.

## v3.0.13 — the second chance: an editor that forgives

**ctrl+z has entered the studio**
- **Real undo/redo.** `ctrl+z` rewinds, `ctrl+y` walks it forward
  again — and both restore the document AND the cursor, so the second
  chance lands you exactly where you were standing. Two hundred steps
  deep, snapshots capped honestly, and a fresh edit after an undo cuts
  the redo branch the way every editor you trust does.
- **Undo groups like humans type.** A burst of typing coalesces into
  one step while the hand is quick (the same 0.8s pause timer that
  drives the live auto-run); a pause opens a new step; `enter`,
  forward-delete and template loads are always their own restore
  point. Fifteen new selftest asserts walk the whole story: bursts,
  coalescing, rewind, redo, branch cuts, line splits and joins.
- **The editor heart moved to `edit.hpp`** — one shared truth for the
  IDE and the selftest, and a latent dangling-reference hardening on
  the enter/del paths (the buffer can reallocate mid-gesture; now it
  re-fetches).
- **A new file starts truly empty** — no ghost leading space on line 1.

**The gallery goes multilingual**
- `ctrl+n` now cycles seven templates across every language the studio
  hosts: `blank`, `shooter`, `cards`, `background`, `flappy` (new),
  `bounce.js` and `pong.cpp` — the console names the language of each.
- **`flappy.py`** — gravity, recycled pipe pairs with fresh gaps,
  one-key flying, honest game-over and restart. The wire contract
  probes it on every push (9 entities, scene + frames), and a
  keys/hit/restart playtest rides in the QA kit.

**Polish**
- **`ctrl+p` screenshots your live game from the editor** — and every
  screenshot leaves a receipt in the studio console
  (`engine: saved exports/…png — a real PNG of your frame`).
- The status-rail hint and `--help` now advertise
  `ctrl+z`/`ctrl+y`/`ctrl+p`.
- `.gitignore` covers the template gallery's `untitled-*` files, so
  ctrl+n + auto-run no longer litters `git status`.

## v3.0.12 — the typed word: an IDE that fixes with you

**The editor grows up**
- **Real editor keys**: `pgup`/`pgdn` page through the file,
  `home`/`end` snap to line ends, `del` forward-deletes and joins the
  next line up — the IDE finally feels like an editor, not a typewriter.
- **ctrl+g: the console talks back.** When your game crashes, the
  console's traceback carries the line number — python
  (`File "game.py", line 12`) and node (`game.js:28:1`) both — and the
  status rail turns red with `ctrl+g jumps to line 12`. One keystroke
  from the stack trace to the offending line.
- **`:new` joins the command bar** — the template gallery without
  leaving the keyboard; it even opens the studio from play mode.

**The C++ SDK: compiled games, first-class**
- `sdk/dxn3.hpp` — a header-only C++ SDK: `g.rect(...)`, `g.onTick`,
  `g.onKey`, `g.onHit`, `g.var(...)`, `g.run()`. Entity pointers are
  stable for the life of the game (a `deque`, on purpose — a `vector`
  silently dangled them and segfaulted real games mid-frame; the gate
  now proves it doesn't).
- `sdk/examples/pong.cpp` — a compiled pong with a speed-capped AI,
  paddle-edge steering and set scoring. `dxn3 sdk/examples/pong.cpp`
  compiles it on the spot and hosts it.
- **Gate 6: the wire contract runs on every push.** A fake engine feeds
  every shipped example — python, node and the compiled C++ game — and
  checks the scene and frames come back. Broken examples fail the
  build now, not the user's afternoon.

**The selftest grew to 86 assertion groups** — the new console-readback
group parses python and node tracebacks for line numbers, last frame
wins.

## v3.0.11 — the polish round

- **Discs are genuinely round now**: circles rasterize per dot, so in
  braille mode every coin, moon and enemy is a true curve with a rim
  light — no more stair steps.
- **Ctrl+N cycles starting points** in the IDE: a bouncing-ball blank,
  the shooter, the card game, the background — each loads into the
  editor and goes live, so "start with nothing" never means "start
  alone".

## v3.0.10 — the de-pixel: braille dots

**Four times the pixels, zero new dependencies**
- The world renderer composes **braille cells** (U+2800..) now: every
  terminal cell carries a 2×4 dot block, so the world renders at 2×2 dots
  per half-block pixel — four times the resolution of the chunky old
  face. Platforms, ships, gradients and the starfield all gain real
  edges; the "pixelated terminal game" look is gone.
- `b` toggles between braille dots and half blocks in play — the old
  face is still there if you want it (or if your font can't do braille).
- The IDE viewport, the splash card and the HUD all render through the
  same dot pipeline; text overlays stay crisp text.
- Engine selftest grew to 81 assertion groups (protocol, resolution,
  scene-name resolution, shapes).

## v3.0.09 — the engine: your code, our canvas

**The studio becomes an engine IDE**
- Boot is the **IDE** now: an editor beside a live viewport and a console
  rail. You start with nothing — the starter is a working shooter in 30
  lines — you edit, and the viewport refreshes while you type. `Ctrl+R`
  runs, `Ctrl+S` saves, `esc` plays your game fullscreen, `esc` again
  returns to the code.
- **Your game is your program, in your language.** The engine hosts it as
  a child process speaking line-JSON on stdio (hello → scene → ticks →
  frames, one page in `sdk/PROTOCOL.md`): Python and JavaScript SDKs ship
  in `sdk/`, `.cpp` games are compiled and hosted on the spot, and
  `--host-cmd 'ruby mygame.rb'` hosts literally anything that reads
  stdin and writes stdout. The engine owns rendering, input, collision;
  your code owns the rules — shooters, card games, whatever you write.
- **The ScriptHost** (`native/src/host.hpp`): fork/exec pipes, a
  fixed-timestep tick with held keys + typed chars + overlap hits, frame
  patches applied by name (spawn/move/recolor/despawn), game vars mirrored
  to the HUD, camera taken live. Unparsable child output becomes console
  lines and SIGPIPE is ignored — a dead game is an honest exit line in
  the console, never a dead studio.
- The SDKs are zero-ceremony: define `on_tick(dt)`, `on_key(k)`,
  `on_hit(a, b)` and call `run()`. print() lands in the console rail.
  A fresh `dt` is injected into your frame every tick; hits fire on
  enter, not every frame; re-drawing a name redraws in place.
- Examples in `sdk/examples/`: `background.py` (the hello world — three
  lines and the viewport answers), `shooter.py` (move, shoot, score),
  `bounce.js` (breakout with a steering paddle — proof the JS SDK bites),
  `cards.py` (balatro-lite hold-and-score — no physics, pure state,
  proof the engine is not just platformers).

**The engine underneath**
- Entities gained a real `shape` (rect / circle / tri / text) parsed and
  round-tripped through the JSON — coins are true discs now, drawn with a
  rim light, and any entity can be any shape.
- `:scene level-3` resolves by name — exact or unique prefix; an
  ambiguous prefix lists the matches instead of guessing, and the
  command bar whispers the matches while you type.
- The selftest grew to **81 assertion groups**, including scene-name
  resolution and **the whole engine end to end: a real Python SDK child
  hosted through the real protocol** — scene across the pipe, prints in
  the console, honest exit.
- The launcher boots the engine IDE from the install root (so `sdk/`
  resolves for every hosted game); the five-scene campaign is the demo.
  `--host-cmd`, `--list-scenes` and the installer carry the new story;
  the version constant tells the truth again (3.0.09 everywhere).

## v3.0.08 — the campaign: somewhere to go

**The campaign grows: five scenes**
- Two new levels chain the world together: **playground → level-1 (the gap)
  → level-2 (the movers) → level-3 (the climb) → level-4 (the gauntlet) →
  back home.**
- `level-3 — the climb`: the studio goes vertical. Two lifts, a fanged
  approach, a springboard shortcut for the greedy, coins on the way up and
  a gradient summit waiting at the top.
- `level-4 — the gauntlet`: the exam. Nine fangs on the pit floor, three
  ferries on staggered heights, a saw-guarded island rest stop, a spinning
  gate before the last door — the hardest jump timing in the campaign.
- Both levels ship with real map-framed renders in the README, generated
  by the binary itself (`--screenshot`), same as the rest.

**The repo fires: quality gates in public**
- GitHub Actions CI now runs the full gauntlet on every push and pull
  request: the zero-warning C++23 build under **g++ and clang++** (a
  compiler matrix), the engine selftest, one real headless frame for
  every scene, the zero-electron tripwire and VERSION ↔ CHANGELOG
  consistency.
- A second CI job probes the one-liner installer end to end — clone,
  build, selftest, launcher — straight from `origin/master`, so the curl
  line on the README is exercised by machines, not just by hope.
- README carries the gates badge; the campaign section, screenshot
  gallery and history tell the five-scene story.

## v3.0.07 — the mark: a face for the studio

**The brand**
- The studio has its emblem: the STUDIO 2 circuit spiral (preserved on the
  `ds2-archive` branch) with a monolithic beveled **3** carved into it —
  Unreal-Engine energy, purple-on-black, one mark everywhere. The brand
  suite lives in `assets/` with the SVG sources: emblem, README banner and
  the repo social card.
- The binary carries the mark too: `native/src/logo32.hpp` renders it as a
  32×32 truecolor bitmap and the studio opens on a **title card** — the
  emblem, the wordmark, the version, one key to play.

**The UI**
- Title card on launch (any key plays, `q` quits) — the studio greets you
  as a product, not a process, carrying the mark as a 32×32 truecolor
  bitmap straight from the binary.
- The HUD counts it all: `COINS x/y · SCORE · TIME` on the left, the scene
  name on the right — you always know where you are in the campaign.
- `dxn3 --list-scenes` prints every installed scene with its name and
  entity count — discoverability without reading files, and `--help`
  covers the whole CLI.
- The vim-style **command bar** ships: `:scene :zoom :fit :reset :w :wq :q
  :screenshot :magnet :gravity :help`, honest errors with usage, the game
  paused while it's open — and it whispers: a live usage hint follows your
  typing, dim and out of the way.
- **PNG screenshots** ship, zero dependencies: `p` in play saves
  `exports/<scene>-<n>.png`, and `dxn3-native --screenshot out.png` renders
  any scene headless (the README's screenshots are made this way).
- **Scene saving** ships with a git-style safety net: `:w` writes the scene
  and keeps the previous bytes as `<file>.bak` before the new ones land.
- The deterministic parallax **starfield** (`fx.hpp`) — every scene seeds
  its own sky from its name, so the same scene draws the same stars in
  every session and every screenshot.
- **`--list-scenes`**: `dxn3 --list-scenes` prints every `.dxn1.json` it
  can find with its scene name and entity count — unreadable files are
  reported, never swallowed.
- The live view reached **poster parity**: the terminal now draws the same
  sky gradient, coin halos and edge vignette as the PNG raster, and
  INSPECT / FILE VIEW wear the same rail headers and zebra rows.
- **Poster framing**: `--screenshot` fits the whole scene like a map —
  world-centered, edges and all — which is how the README shots are made.

## v3.0.06 — the Electron farewell: fully C++23

**One binary to rule them all**
- Deleted, for real and forever: `electron/`, the JS renderer, the Python
  engine and its QA stand-in, `package.json`, the Node scripts, the pytest
  lane and the stale UI screenshots. Nothing in the tree mentions Electron
  outside this changelog's history.
- `scripts/gates.sh` rebuilt native-only: zero-warning C++23 build, the
  engine selftest, **every scene must render one real headless frame**,
  zero electron-era files tracked, VERSION ↔ CHANGELOG consistency. The
  gates need nothing but a C++23 compiler now — the QA lane eats its own
  dog food.
- `scripts/install.sh` rebuilt: checks git + g++/clang++ (probing that
  C++23 actually compiles), clones, builds, runs the selftest, writes the
  `dxn3` launcher. The curl one-liner stays exactly where it was.
- New campaign scene `scenes/level-1.dxn1.json` — **the gap**: a mover
  bridge over a spiked pit, an elevator to a sky ledge, a five-coin arc and
  a goal that chains into level-2. The campaign is now
  playground → level-1 → level-2 → home.
- README + ARCHITECTURE rewritten around the native core. The studio is
  one binary; the past lives in git history.

# Changelog — DXN1 STUDIO 3

Giant hourly updates. Every version is worth installing.

## v3.0.05 — the native core: Spark in C++23

**The engine now speaks C++ too**
- `native/` — a complete, dependency-free **C++23 port of the Spark
  engine**: same scene JSON, same AABB physics, movers with rider
  carry, coin magnetism, hazards, goal→next-scene transitions, camera
  follow + zoom + decay shake. `std::expected` scene loading, a
  hand-rolled JSON parser (with `\uXXXX`→UTF-8 so signs render their
  arrows), fixed-timestep loop mirroring the JS runtime 1:1.
- **Truecolor terminal renderer** — half-block pixels (two world
  pixels per cell, 24-bit color), gradient fills, striped goal flags,
  triangle spikes, HUD with score/time, help rails. The studio plays
  beautifully in any modern terminal.
- **The studio shell** — PLAY and INSPECT modes (Tab pauses and prints
  the entity table: name, tag, position, size, color, aliveness),
  run/jump, zoom in/out/fit, reset, honest quit summary. Runs from any
  working directory; `--scene` picks the level.
- **Selftest: 29 engine assertions** — clamps, magnetism (pull + off),
  pickups, hazard respawn + shake, transition locking, mover
  ping-pong + rider carry, camera follow, eternal ball. Wired into the
  quality gates as gate 7 — the repo does not ship unless C++23 builds
  clean (`-Wall -Wextra -Wpedantic`) and stays green.

**Spark (browser) gains the same powers**
- **Coin magnetism** — `"magnet": 110` per scene; coins drift toward
  the player, pull growing as they close in. Both demo scenes ship
  magnetized.
- **Camera shake** — time-decayed, cosmetic-only; hazards shake on
  respawn. `game.shake(power, seconds)` from scene code.
- **Word autocomplete** — Ctrl+Space pops frequency-ranked completions
  from the buffer; arrows/click to accept, Esc dismisses, caret-true
  positioning.
- **Breadcrumbs** — the path of the open file sits above the editor,
  clickable per segment.
- **Search grouped by file** — project grep results now file their
  matches under per-file headers with counts.
- **"Play level 2" hero card** — the welcome screen now jumps straight
  into the movers-and-magnet level.

## v3.0.04 — the git suite completes; the editor sees the line you're on

**Source control — the full loop**
- Diff viewer: click ± on any changed file to see exactly what
  changed vs HEAD — unified hunks, +/− coloring, line numbers, add and
  delete counts. Untracked files show as all-additions; no-HEAD repos
  handled honestly.
- Branch switcher: click the branch chip to switch or create branches
  (duplicate and ghost names refused, hostile names rejected). Demo
  mode simulates per-branch snapshots and histories, checkout and all.
- Rail badge: the source control icon counts your live changes.

**Editor**
- Current-line highlight follows the caret (and scrolls with it).
- Gutter now scroll-syncs with the editor — line numbers finally
  follow long files (a latent bug since v3.0.01).
- Editor context menu: undo, redo, cut, copy, paste, select all,
  find, replace, go to line — right where you are.

**Spark engine**
- Entities rotate: `rot` (degrees, visual-only — physics stays an
  honest AABB) and `spin` (degrees/sec) — level-2 gained a spinning
  saw hazard. Inspector rows for rot / color2 / gradient fill.
- 2-line-context LCS diffs power the demo diff viewer.

**Under the hood**
- Engine cmd_git_diff / git_branches / git_checkout with honest errors
  (path required · no such branch · branch already exists · invalid
  branch name). Branch parse fixed for "No commits yet on master".
- Tests 20/20 · gates 6/6 · browser QA 46/46.

# Changelog — DXN1 STUDIO 3

Giant hourly updates. Every version is worth installing.

## v3.0.03 — the scene comes alive, and source control is real

**Spark engine**
- Moving platforms: `path: {toX, toY, speed}` — entities shuttle
  ping-pong between two points and CARRY whatever stands on them.
  Motion rails drawn as dashed cyan lines in the editor.
- Scene transitions: tag an entity `goal`, point `next` at another
  scene — touching it loads the next level and the run keeps playing.
  Two demo levels ship and loop: playground → level-2 → playground.
- Camera zoom (wheel, toward cursor) + pan (middle-drag / Space+drag)
  + zoom-fit button — the whole render pipeline is zoom-aware, grid,
  culling, selection, camera follow.
- Parallax layers are scene data: `parallax: [{speed, color, size,
  count}]`. Timer HUD joins the score.

**Scene editor**
- Canvas right-click toolbox: add any of 8 entity kinds exactly at the
  cursor, duplicate, delete, bring to front, send to back.
- Z-order controls in the inspector (front / up / down / back) and in
  the entity list right-click.
- New presets: mover (pre-wired path) and goal (the finish flag).
- Inspector: motion rows (to x / to y / speed), make-it-move and
  remove-motion buttons.

**Editor**
- Replace in file (Ctrl+H): replace current hit or all, live counts.
- Go to line (Ctrl+G).
- Bracket & quote auto-close, selection wrap, type-over closers,
  empty-pair backspace.
- Editor context menu: undo, redo, cut, copy, paste, select all,
  find, replace, go to line.

**Source control — wired honestly**
- The git panel is no longer dead UI: branch + changed files with
  M/A/D badges (click to open), commit box, history list.
- The Python engine speaks real git (status/log/commit over
  subprocess, honest errors for non-repos); demo mode carries a
  simulated history with the same protocol.
- Statusbar shows the branch. Terminal gained `git` and `zoom` verbs.

**Installer**
- One-line curl install: `curl -fsSL .../scripts/install.sh | bash`
  — checks tools, clones, offers desktop or `--demo` browser mode
  (Termux-friendly). README rewritten around it.

**Quality**
- Engine tests +6 (git status/commit/log/non-repo/message guards).
- Renderer selftest grew to 9 assertion groups (goal, next-chaining,
  movers, parallax, zoom helpers).
- Gates 6/6 green before tag.

# Changelog — DXN1 STUDIO 3

Giant hourly updates. Every version is worth installing.

## v3.0.03 — the studio learns to move (and to remember)

**Spark engine**
- Moving platforms: give any entity a motion rail (`path: {toX, toY,
  speed}`) and it shuttles between the two points, ping-pong, CARRYING
  whatever stands on it — elevators, ferries, drifting ledges.
- Scene transitions: a `goal` entity + a scene-level `next` path sends
  the player into the next scene without leaving play mode. The demo
  ships two chained scenes (playground → level-2 → playground).
- Timer HUD next to the score; parallax layers are now scene config
  (`parallax: [{speed, color, size, count}]`).
- The editor draws each mover's dashed motion rail on the canvas.

**Scene editor**
- Camera zoom (wheel, toward the cursor) + pan (middle-drag or
  space-drag) + ⊕ fit. Grid, culling and selection all respect zoom.
- Canvas right-click: add any entity exactly where you clicked,
  duplicate / delete, and z-order (bring to front / send to back /
  forward / backward). Z-order buttons also live in the inspector.
- New presets: ⚑ goal and ⇄ mover.
- Inspector: add motion / edit rail target + speed / remove motion.

**Editor**
- Replace-in-file: findbar grew Replace + Replace All (Ctrl+H).
- Go to line: Ctrl+G, clamped, statusbar-confirmed.
- Bracket & quote auto-close with selection wrap and skip-over.
- Editor context menu: undo / redo / cut / copy / paste / select all /
  go to line / find.

**Source control — wired for real**
- The git panel was dead UI; now it speaks to the engine:
  branch + ahead, per-file status badges (A/M/D/U), click a file to
  open it, commit box (adds all, honest errors), and a log with hash +
  subject + age. The Python engine shells out to real git; the demo
  filesystem keeps an honest simulated history. Statusbar shows the
  branch.

**Install from one line**
- `curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash`
  installs STUDIO 3 and a `dxn3` launcher (Electron when available,
  honest web preview otherwise).

**Also**
- scenes/level-2.dxn1.json — a mover-and-goal level built for the demo.
- Terminal verbs: `git`, `zoom in|out|fit`. Palette: 22 commands.
- Engine: git_status / git_log / git_commit with honest errors; 18
  engine tests; selftest guards the new Spark schema (8 groups).

## v3.0.02 — the editor & the scene editor get muscles

**Scene editor (Spark)**
- Entity palette: add block / platform / coin / spike / bouncer / text
  with one click — spawned snapped to the grid at the camera center.
- Duplicate (Ctrl+D / ⧉ / right-click) and delete (Del / ✕ / right-click)
  entities, with auto-unique names.
- Edit grid overlay (⌗) with 8px snapping while dragging — Alt drags free.
- Live repaint while dragging or editing the inspector — the canvas is
  never stale again (this was a real editing bug: changes only showed
  after pressing play).
- Spark engine: triangle shape, text entities (with size), hazard tag
  (spikes respawn the player with a burst), proper spawn-point handling,
  identity-based selection rendering (duplicates render correctly).

**Editor**
- Find in file: Ctrl+F, live match count, Enter / Shift+Enter navigation
  with wrap-around, Esc to close.
- Minimap, DS3 style: one bar per line, indent-aware, viewport lens,
  click/drag to jump, toggleable.
- Tab drag-to-reorder.
- Sidebar resize via drag handle (persisted).
- Syntax highlighting for HTML and CSS.
- Keybindings reference table in Settings.

**Terminal**: new verbs `grid`, `ent`, `find <text>`, `mm`.
**Demo scene**: spikes + a signpost label show off the new engine powers.

## v3.0.01 — the rebirth

Fresh-history rebuild of the whole repo:
- Electron face + Python brain (stdio JSON bridge, atomic writes,
  path-escape guards) + DemoFS so the UI never dies in a browser.
- Workbench: welcome hero, editor (gutter + highlighting + transparent
  textarea), game view (canvas + scene dock: entity list + inspector),
  terminal dock, statusbar, command palette (13 commands), toasts,
  context menus.
- SPARK 2D engine: entities, AABB physics (axis-separated), platformer
  controller, bounce, coin pickup + score + particles, camera follow,
  parallax stars, HUD. Scenes are plain JSON.
- Playable playground scene; light/dark themes; five accents.
