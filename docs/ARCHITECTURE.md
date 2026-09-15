# Architecture — DXN1 STUDIO 3 (fully C++23)

One process. One binary. A truecolor terminal. Zero dependencies.

```
┌──────────────────────────────────────────────────────┐
│ main.cpp — the studio shell                          │
│   raw-mode keyboard · poll(0) · fixed 1/60 timestep  │
│   PLAY ── tab ──▶ INSPECT        e ──▶ FILE VIEW     │
│   goal touched ──▶ load scene.next, keep score       │
├───────────────────────────┬──────────────────────────┤
│ spark.hpp/.cpp            │ tui.hpp/.cpp             │
│   the engine core         │   the face               │
│   AABB player physics     │   half-block pixels      │
│   movers + rider carry    │   rect / rectGradient    │
│   coins + magnetism       │   per-cell text spans    │
│   spikes · goal · ball    │   HUD · help rail        │
│   camera follow + zoom    │   ANSI emit, diffed      │
│   shake + flash + toast   │                          │
│   std::expected scene I/O │ json.hpp                 │
│   normalize/toJson        │   recursive descent      │
│                           │   \uXXXX → UTF-8         │
└───────────────────────────┴──────────────────────────┘
            │                              ▲
            ▼                              │
     scenes/*.dxn1.json ───────────────────┘
```

## The layers

**`spark.hpp/.cpp` — engine core, no terminal knowledge.**
`Game` owns a normalized `Scene` (clamped gravity, zoom 0.3–4, valid hex
colors) and steps it in place: `stepPlayer` (accel/friction/jump, AABB
resolve), `stepMovers` (waypoint ping-pong + rider carry by per-tick delta),
`stepCoins` (magnet pull + pickup), `stepTags` (spikes respawn, goals lock
the transition and chain `scene.next`, balls bounce forever, `spin`
rotates), `stepCamera` (zoom-aware exponential follow). Scene I/O is
honest: `loadScene` returns `std::expected<Scene, LoadError>`, junk fields
fall back to normalized defaults rather than exploding.

**`tui.hpp/.cpp` — truecolor renderer, no engine knowledge.**
A `Screen` is a grid of RGB cells (two cells per terminal row, emitted as
U+2580 upper-half blocks) plus per-cell text spans that overlay the grid.
`flush()` diffs foreground/background pairs so frames carry minimal ANSI.
Everything the player sees — gradients, coin shine, spike triangles, goal
stripes, the flash — is drawn through this 2D cell grid.

**`main.cpp` — the shell.**
Raw-mode terminal, 0-timeout `poll` input (keystrokes never freeze the
loop), fixed-timestep accumulator, three modes (PLAY / INSPECT / FILE
VIEW), camera zoom keys clamped by the same policy as the engine, and the
goal→next-scene handoff that preserves score and time across scenes.

**`json.hpp` — dependency-free JSON.**
Recursive descent, order-preserving objects, `\uXXXX` → UTF-8 (so signs
render their arrows), honest error strings surfaced through `expected`.

## Data

A scene is plain JSON — `scenes/*.dxn1.json`. The schema lives in the
README; the canonical reader is `spark.cpp`, the canonical writers are the
files themselves. Goals reference the next scene by repo-relative path, so
the campaign is just a linked list: playground → level-1 → level-2 →
playground.

## QA

`scripts/gates.sh` runs: a zero-warning `-std=c++23` build → the engine
selftest (normalization clamps, magnetism, pickups, hazard respawn,
transition lock, mover ping-pong + rider carry, camera follow + shake
decay, ball bounce) → a real headless frame rendered from **every** scene →
zero electron-era files tracked → VERSION ↔ CHANGELOG consistency. The QA
lane is the same language as the product; there is no second stack to keep
alive.

## Why C++23

`std::expected` makes scene errors honest without exceptions; `std::print`
formats without pulling a dependency; concepts and ranges keep the JSON and
engine code short; `-std=c++23` on GCC 12+ / clang 17+ costs nothing. One
language from physics to pixels — that is the whole point of the farewell.

## The farewell (v3.0.06)

The Electron shell, the JS renderer, the Python engine and the browser QA
harness were deleted — not deprecated, not hidden behind a flag: deleted.
They served v3.0.01–v3.0.05 and their history is intact in git. The studio
is one binary now.
