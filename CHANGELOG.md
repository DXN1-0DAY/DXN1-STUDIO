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
