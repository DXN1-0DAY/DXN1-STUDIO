# Changelog — DXN1 STUDIO 3

Giant hourly updates. Every version is worth installing.

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
