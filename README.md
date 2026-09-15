# DXN1 STUDIO 3

![version](https://img.shields.io/badge/version-3.0.06-8b5cf6?style=flat-square)
![native](https://img.shields.io/badge/native-C%2B%2023-f97316?style=flat-square)
![face](https://img.shields.io/badge/face-terminal_truecolor-22d3ee?style=flat-square)
![deps](https://img.shields.io/badge/dependencies-zero-34d399?style=flat-square)
![engine](https://img.shields.io/badge/spark_2d-built_in-fbbf24?style=flat-square)

**A beautiful studio for code and games — one C++23 binary, zero dependencies.**
STUDIO 3 is the Spark 2D engine and a truecolor terminal studio compiled into a
single native core. Scenes are plain JSON. The whole thing builds with `make`.
There is no Electron, no Node and no Python in this repo anymore — the studio
is one binary and the binary is the product.

## Install — one line

```bash
curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/scripts/install.sh | bash
```

The installer checks `git` and a C++23 compiler (g++ or clang++), clones the
repo, builds `native/build/dxn3-native`, runs the engine selftest so you know
it's green, and drops a `dxn3` launcher into `~/.local/bin`. That's the whole
dependency list: git, a compiler, libstdc++.

Prefer it by hand?

```bash
git clone https://github.com/DXN1-termux/DXN1-STUDIO.git
cd DXN1-STUDIO && make -C native && ./native/build/dxn3-native
```

## Play

`dxn3` opens the playground scene in truecolor (half-block pixels, gradients,
HUD). Goals chain scenes into a little campaign: **playground → level-1 →
level-2 → back home.**

| key | action |
|-----|--------|
| `a` / `d` | run left / right |
| `w` / `space` | jump |
| `r` | reset to spawn |
| `+` / `-` | camera zoom (clamped 0.3×–4×) |
| `f` | zoom-to-fit the whole scene |
| `tab` | INSPECT — the live entity table, game paused |
| `e` | FILE VIEW — the scene's own source with line numbers, `j/k` scroll, `/` search |
| `q` / `esc` | quit |

Coins score (+10, magnetized within the scene's radius), spikes respawn you
with a camera shake, movers carry you across the gaps, the ball keeps itself
company.

## Scenes are JSON

A scene is a `.dxn1.json` file — data only, no code:

```json
{
  "name": "level-1",
  "bg": "#0b0e1a",
  "gravity": 1500,
  "magnet": 120,
  "next": "scenes/level-2.dxn1.json",
  "camera": { "x": 200, "y": 250, "zoom": 0.85 },
  "entities": [
    { "name": "hero", "tag": "player", "x": 60, "y": 300, "w": 34, "h": 44 },
    { "name": "lift", "tag": "mover", "x": 620, "y": 372, "w": 140, "h": 20,
      "path": [ { "x": 620, "y": 372 }, { "x": 760, "y": 372 } ], "pspeed": 70 },
    { "name": "gem", "tag": "coin", "x": 340, "y": 290, "w": 22, "h": 22, "color": "#facc15" },
    { "name": "pain", "tag": "spike", "x": 590, "y": 430, "w": 50, "h": 28, "color": "#ef4444" },
    { "name": "out", "tag": "goal", "x": 1590, "y": 180, "w": 40, "h": 70, "color": "#22c55e" },
    { "name": "tip", "tag": "sign", "text": "ride the mover →", "color": "#a78bfa" }
  ]
}
```

Tags: `player` (the hero), `mover` (path-following platform with rider
carry), `coin` (score + magnetism), `spike` (respawn + shake), `goal`
(next-scene transition, locked after one touch), `ball` (perpetual demo
bounce), `sign` (floating text). Tagless entities are solid geometry.
Colors may set `color2` + `"fill": "gradient"`, and `spin` rotates them.

## Engine selftest + gates

```bash
make -C native test      # engine assertions: physics, movers, coins,
                         # magnetism, hazards, transitions, camera
scripts/gates.sh         # the full gauntlet
```

The gates are: a zero-warning `-std=c++23` build, the selftest, **every scene
must render one real headless frame**, zero electron-era files tracked, and
VERSION ↔ CHANGELOG consistency. No Node, no Python — the QA lane eats its
own dog food.

## Layout

```
native/src/spark.hpp/.cpp   the engine: AABB physics, movers + rider carry,
                            coins + magnetism, hazards, goal transitions,
                            camera follow + zoom + decay shake,
                            std::expected scene I/O
native/src/tui.hpp/.cpp     the face: truecolor half-block renderer,
                            gradients, HUD spans
native/src/json.hpp         recursive-descent JSON with \uXXXX → UTF-8
native/src/main.cpp         the studio shell: raw-mode input, fixed
                            timestep, PLAY / INSPECT / FILE VIEW modes
native/src/selftest.cpp     engine assertions
scenes/*.dxn1.json          the campaign — data only
scripts/install.sh          the curl one-liner
scripts/gates.sh            the quality gauntlet
```

## History

STUDIO 3 was born as an Electron app with a Python brain (v3.0.01–v3.0.04).
v3.0.05 ported the Spark engine to C++23 and played it in the terminal.
v3.0.06 deleted the Electron, web and Python stacks for good — the studio is
one binary now, and the old lives are in git history where they belong.

MIT — DXN1-termux
