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
