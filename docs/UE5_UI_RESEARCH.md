# UE5 Editor Research — how the studio wears its clothes

*DS3 kickoff artifact (v3.1.119). The browser editor in `ui/index.html` is
built directly on these notes: what Unreal Engine 5's editor actually looks
like, how it behaves, and which of its idioms we adopted for the Spark wire.*

## 1. The layout map (what UE5 puts where)

| Region | UE5 content | Studio adoption |
|---|---|---|
| Menu bar | File · Edit · Window · Tools · Help, dropdowns with shortcut hints | Same five menus, same dropdown pattern, `Ctrl+S/Z/Y/D` hints |
| Toolbar | Big icon buttons: select/translate/rotate/scale, then play/pause/eject | Select/Pan/Zoom tools + snap/grid + Play/Stop (P toggles PIE) |
| Left dock | **Place Assets/Actors** palette (draggable archetypes) | Place Actors tab: solid, mover, goal, hazard, spike, bouncy, ball, coin, sign, player spawn |
| Left dock | **Outliner**: hierarchical actor tree, visibility eyes, search | Outliner tab: entity rows with tag chip + colored swatch + eye toggle + search |
| Center | **Viewport**: the world, gizmo top-right, view-mode pills top-left | Canvas world with grid, orange selection + 8 handles, `Perspective/Lit/Show` pills, axis gizmo top-right |
| Right dock | **Details**: categorized properties, numeric drag-scrub fields | Transform (x/y/w/h scrubbers), Appearance (color/alpha/shape), Identity (name/tag/solid), Mover Law (pspeed + path points) |
| Bottom dock | **Content Browser**: breadcrumb + asset cards with thumbnails | Scene cards (AI-generated thumbs, entity counts, chain arrows) + New Scene |
| Bottom dock | **Output Log**: timestamped severity-colored engine chatter | Output Log with `[boot]/[wire]/[pie]/[lint]` channels + `Cmd ▸` command bar |
| Status bar | Scene stats, mode, engine version | Scene name · entity count · selection · zoom · grid · sim state · gates · version |

## 2. The interaction idioms we copied

- **Selection is orange** — UE5's active-actor outline is orange; ours is
  `#ff9b26` with 8 corner/edge handles, dashed hover-outline in viewport,
  and the same orange tint on Outliner rows.
- **Numeric fields scrub** — in UE5 you drag a value field sideways and the
  number follows the mouse. Every x/y/w/h field in Details is an
  `ew-resize` scrubber with pointer capture.
- **Shift-click multi-select**, click-empty deselects, `Esc` deselects —
  the same triad.
- **Pan = MMB drag** (or the pan tool / hold Space), **zoom = wheel to
  cursor** — zoom-to-cursor keeps the world point under the mouse fixed.
- **Play In Editor (PIE)** — the viewport becomes the game; a warning bar
  separates it from edit mode; stopping returns the stage untouched.
  Ours runs spark's own constants: gravity `1500`, jump `-620`, movers
  ride their path at `pspeed` px/s, bouncy affects only balls (the player
  springboard is a plain solid — the engine's tag dispatch is law).
- **The engine is authoritative; the editor is a face.** UE5's editor
  panels are views over the world's data; ours are views over the same
  scene JSON the binary speaks. PIE is an honest approximation and says
  so — the binary remains the law.

## 3. The palette (measured against UE5's dark theme)

| Role | UE5-ish | Studio token |
|---|---|---|
| Window chrome | `#1a1a1a`–`#161616` | `--win #161719` |
| Panels | `#2a2a2a` | `--panel #232427` |
| Toolbar / headers | `#3b3b3b` | `--toolbar #2f3035`, `--head #2e2f33` |
| Hairline borders | `#101010` + `#3f3f3f` | `--border #101113`, `--hair #3a3b40` |
| Text | `#d0d0d0`, dims `#808080` | `--text #cfcfd2`, `--dim #8a8b91` |
| Selection | orange `#ff9b26`-family | `--sel #ff9b26` |
| Viewport bg | near-black with grid | `--sky #0d0e11` + `rgba` violet wash |

Fonts: 11–12px UI stack (Segoe UI/Roboto), monospace only for the log and
command bar — matching UE5's small dense type.

## 4. Sources

- Unreal Engine 5.8 docs — *Unreal Editor Interface* (Outliner sits
  upper-right; Details right; Content Browser bottom; Viewport center).
- *A Beginner's Tour of the UE5 Editor Interface* — Viewport / Outliner /
  Details / Content Browser / toolbar & menus, docking, layout reset.
- *Viewport Modes in Unreal Engine* — the view-mode pills (`Lit`,
  `Show All`) and their diagnostic value.
- UE5 editor hotkey cheat sheets — W/E/R widget modes, G grid snap,
  F focus, Home recenter (adopted verbatim).
- Editor Preferences → Theme (Dark) — the palette reference.

## 5. What we deliberately did NOT copy

- Docking widgets (draggable panel splinters) — one fixed, honest layout;
  panels toggle instead of float.
- The fake "Perspective" camera for a 2D world — the pill exists but tells
  the truth when clicked: this is a sprite stage, the binary renders the
  true frame.
- C++/reflection property gutters — Details edits plain JSON, the wire's
  own tongue.
