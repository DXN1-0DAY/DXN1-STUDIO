# DXN1 STUDIO 3

![DXN1 STUDIO 3](assets/banner.png)

![version](https://img.shields.io/badge/version-3.0.26-8b5cf6?style=flat-square)
![gates](https://github.com/DXN1-termux/DXN1-STUDIO/actions/workflows/ci.yml/badge.svg)
![native](https://img.shields.io/badge/native-C%2B%2023-f97316?style=flat-square)
![face](https://img.shields.io/badge/face-terminal_truecolor-22d3ee?style=flat-square)
![deps](https://img.shields.io/badge/dependencies-zero-34d399?style=flat-square)
![engine](https://img.shields.io/badge/spark_2d-built_in-fbbf24?style=flat-square)
![launch](https://img.shields.io/badge/launch-dxn3_one_liner-22c55e?style=flat-square)

**A beautiful game engine with a studio for code — one C++23 binary, zero dependencies.**
STUDIO 3 is a real engine: open it and you start with nothing — you write code
(Python, JavaScript, C++, anything), and it runs LIVE beside your editor. The
Spark 2D core renders, feeds input, reports collisions and consoles your game
in truecolor; your code IS the game. It also ships a five-scene campaign as a
demo of what the engine can do. Scenes are plain JSON, games are plain code,
and the whole thing builds with `make`.

The engine core has no Electron, no Node and no Python **in it** — one C++23
binary, nothing else. Your games, though, can speak any language you like:
the engine hosts them as child processes over a tiny JSON protocol
([sdk/PROTOCOL.md](sdk/PROTOCOL.md)), with thin SDKs for Python and
JavaScript in `sdk/` and first-class support for compiled C++ games.

## Install — one line, fully launchable

Every push runs the full gauntlet in CI — a zero-warning C++23 build under
g++ **and** clang++, the engine selftest, a real headless frame for every
scene, and a live probe of the one-liner installer.

```bash
curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/scripts/install.sh | bash
```

The installer checks `git` and a C++23 compiler (g++ or clang++, probing that
C++23 actually compiles), clones the repo, builds `native/build/dxn3-native`,
runs the engine selftest so you know it's green, and drops a `dxn3` launcher
into `~/.local/bin`. That's the whole dependency list: git, a compiler,
libstdc++. Then:

```bash
dxn3                              # THE ENGINE — write a game, it goes live
dxn3 sdk/examples/background.py   # your first background, then a shooter
dxn3 scenes/level-1.dxn1.json     # the demo campaign, by path
dxn3 --list-scenes                # what's installed, with entity counts
dxn3 --screenshot shot.png        # headless PNG of any scene
```

Prefer it by hand?

```bash
git clone https://github.com/DXN1-termux/DXN1-STUDIO.git
cd DXN1-STUDIO && make -C native && ./native/build/dxn3-native
```

## The engine: your code, our canvas

`dxn3` with no arguments opens the IDE: an editor pane with line numbers and
syntax tint, a **live viewport**, and a console rail. You start with
absolutely nothing — a starter game is loaded, and it is already running.
Edit anything and pause for a beat: your code re-runs itself and the
viewport refreshes — *code a background, and boom, a background.*

- **Any language.** `.py` and `.js` run via the SDKs, `.cpp` games are
  compiled and hosted, and `--host-cmd 'ruby game.rb'` covers everything
  else. The protocol is one page: [sdk/PROTOCOL.md](sdk/PROTOCOL.md).
- **The engine does the heavy lifting.** Rendering (truecolor half-block
  pixels, discs, triangles, gradients, starfield skies), input, collision
  reporting, the HUD, the console. Your code owns the game logic.
- **The SDK is one import.** `from dxn3 import *` gives you `rect`,
  `circle`, `tri`, `label`, `on_key` / `on_tick` / `on_hit`, `destroy`,
  `vars`, `camera` — and `run()`. Entities are plain objects; move them
  and the engine sees it. C++ games `#include "dxn3.hpp"` and compile
  to a binary the studio hosts — see `sdk/examples/pong.cpp`.
- **Examples in `sdk/examples/`:** `background.py` (the hello world),
  `shooter.py` (bullets, score, respawning enemy), `flappy.py`
  (gravity, pipes, one-key flying), `bounce.js`
  (breakout with a steering paddle), `cards.py` (balatro-lite poker
  hands vs the blind), `pong.cpp` (a compiled C++ pong with an AI that
  caps its speed — the hardest SDK proof in the set).
- **The editor forgives.** `ctrl+z` undoes — typing bursts coalesce the
  way real editors group them, `enter`/`del` are their own restore
  points, and undo restores the document AND the cursor. `ctrl+y`
  walks it forward again; a fresh edit cuts the redo branch, honestly.
  Two hundred steps deep, so you can code without fear.
- **The block rides down.** Enter auto-indents: openers (`:`, `{`)
  bump a level, closers (`else`, `end`, …) drop back one, everything
  else inherits — python and C-family both feel at home.
- **The searchlight.** `ctrl+f` finds in your file — case-insensitive,
  every hit glows behind the text, `enter` walks you to the next one
  (wrapping), and the rail counts them while you type. The header
  always tells you where you stand: `Ln 12 · Col 8`.
- **Pairs carry their closers.** `(`, `[`, `{` and quotes type their
  other half for you; a closer you already have is skipped over, never
  doubled; backspace between an empty pair removes both halves; an
  apostrophe inside a word (`don't`) stays honest. `ctrl+d`
  duplicates the line under the cursor in one undo step.
- **`:open <file>`** loads any script on the machine into the studio —
  your own games and the `sdk/examples/` gallery whisper their names
  as you type. Ghost files are refused honestly.
- **Word hops and the partner.** `ctrl+←`/`ctrl+→` jump word by word —
  the same words `ctrl+w` bites — across line edges when they must.
  `ctrl+delete` eats exactly what a hop would cross; `ctrl+/` toggles
  the line's comment in the file's own language (`#`, `//`, `--`).
  Stand on a bracket and its partner glows across the file, nesting
  respected. And long lines slide under the cursor instead of being
  chopped at the pane's edge; the gutter marks the cut with `…`.
- **The input parser grew up.** Escape sequences are parsed whole and
  unknown ones are swallowed — terminal control chatter (mouse
  reports, modifier-keyed arrows, split reads) can never leak into
  your code as text again. `ctrl+↑`/`ctrl+↓` nudge the view without
  moving the cursor.
- **The snippet shelf speaks your language.** `:snip tick` lands
  `def on_tick(dt):` in a .py file, `on.tick(() => { … })` in a .js
  one, `g.onTick = [&](float dt) { … }` in C++ — eleven python
  starters, seven js, five cpp, each one honest to the sdk/ wire
  contract; prefix-complete with whispers, one undo step to take it
  back. Dim guides at columns 79 and 99 keep the margins visible
  (`:ruler` toggles), `:stats` counts what you're holding, and
  `ctrl+home`/`ctrl+end` jump the edges of the document.
- **The minimap rides the right edge.** A six-column map of the
  whole document lives in the pane's right border on wide terminals:
  indent compresses 2:1, the viewport's rows carry a soft band and
  burn brighter, the cursor's row is the brightest bar, comments
  speak gray, find hits glow amber — and `:minimap` sends it home
  when you want the columns back.
- **The pointer works.** Click the code to move the hand (hscroll
  included), click the gutter for the line start, click the minimap
  to jump whole lines; `shift+click` extends a selection like the
  shift+arrows, a bare click deselects — and looking around never
  re-runs your game. Clicks in the viewport, console or header belong
  to nobody and are swallowed whole.
- **The selection is real.** `shift+arrows` extend a glowing
  anchor↔cursor range across lines; typing, backspace, delete or
  enter replaces it in one undo step; `ctrl+/` comments or strips
  EVERY line the selection covers; a plain move drops it.
- **The clipboard.** `ctrl+c` copies the selection (or the whole
  cursor line when nothing is selected), `ctrl+x` cuts — a bare cut
  lifts the whole line out — and `ctrl+v` pastes: character-wise
  clips splice at the cursor, line-wise clips land above the cursor
  line, and a live selection is the paste's bed, replaced in the
  same undo step. Copy never dirties the doc; cut and paste are one
  honest step each.
- **The word select and the ceremony.** `shift+ctrl+←`/`→` extend the
  selection word by word (the anchor rides the same hops `ctrl+←`/`→`
  make). Enter between a bracket pair splits into three lines — the
  naked middle line takes the cursor, `{` bumps it a level, the
  closer keeps its ground at the base indent; quotes stay out, so
  breaking a string is still just a split. `ctrl+d` duplicates every
  line a multi-line selection covers, and the copy carries the
  selection with it.
- **The tab trigger.** Type a shelf name (`tick`, `key`, `fn`, …) and
  reach for `tab` — the word becomes the boilerplate in place, tail
  text riding behind the block, one undo step to take it back. Plain
  `tab` still gives four honest spaces, indents a selected block,
  and `shift+tab` dedents the block (or the hand's line) again.
  And `:screenshot` whispers its default name before it writes one.
- **The clipboard bridges out.** `ctrl+c`/`ctrl+x` also emit OSC 52
  so terminals that honor it (kitty, alacritty, wezterm, foot,
  iTerm2, Windows Terminal…) keep the OS clipboard in sync — while
  `ctrl+v` always pastes from the studio's own ring, so a plain
  terminal loses nothing. Pasting an empty clip says so instead of
  pretending. And every undo speaks its name now — `ctrl+z` says
  `undo — paste · 3 steps left`, not a blind count — while a shelf
  word under the hand whispers `⇥ tab expands 'tick'` from the rail.

Keys: `ctrl+r` run · `ctrl+s` save · `ctrl+z` undo · `ctrl+y` redo ·
`ctrl+c`/`ctrl+x`/`ctrl+v` copy · cut · paste ·
`ctrl+f` find · `enter` next hit · `ctrl+d` duplicate lines ·
`ctrl+w` delete word · `ctrl+del` delete word ahead · `ctrl+/`
comment toggle (multi-line with a selection) ·
`shift+arrows` select · `shift+ctrl+←`/`→` select words ·
`mouse` click code/map to move · shift+click selects ·
`tab` snippet/indent · `shift+tab` dedent ·
`ctrl+←`/`ctrl+→` word hops ·
`ctrl+↑`/`ctrl+↓` nudge the view ·
`ctrl+n` next template (or `:new`) · `ctrl+g` jump to the error line ·
`ctrl+p` screenshot of your live game · `pgup/pgdn` page · `home/end`
line ends · `ctrl+home`/`ctrl+end` doc edges · `del` forward-delete ·
`esc` play your game fullscreen · `e` back to the editor ·
`:open <file>` loads any script · `:goto <line>` jumps the editor ·
`:template <name>` loads a starter · `:snip <name>` drops boilerplate ·
`:minimap` toggles the map rail ·
`:scene <name>` loads a demo (with
completion whispers) · `:q` quit.

## The built-in demo: a five-scene campaign

The Spark engine ships with a chained platformer — real headless renders
of the shipped scenes, the same frames your terminal draws. It is a demo
of the renderer; your games are the product:

| the playground | the gap (level-1) |
|---|---|
| ![playground](docs/img/shot-playground.png) | ![level-1](docs/img/shot-level-1.png) |
| **the climb (level-3)** | **the gauntlet (level-4)** |
| ![level-3](docs/img/shot-level-3.png) | ![level-4](docs/img/shot-level-4.png) |

Goals chain the scenes into a five-scene campaign: **playground → level-1 (the
gap) → level-2 (the movers) → level-3 (the climb) → level-4 (the gauntlet) →
back home.** Coins score (+10, magnetized inside the scene's radius), spikes
respawn you with a camera shake, movers carry you across the gaps — and the
HUD counts it all: `COINS x/y · SCORE · TIME`, scene name on the right.
Level-3 goes vertical — two lifts, a springboard shortcut and a gradient
summit. Level-4 is the exam: nine fangs, three ferries, a saw-guarded island
and a spinning gate before the last door. The full walkthrough lives in the
[campaign field guide](docs/CAMPAIGN.md).

## Play

| key | action |
|-----|--------|
| `a` / `d` | run left / right |
| `w` / `space` | jump |
| `r` | reset to spawn |
| `+` / `-` | camera zoom (clamped 0.3×–4×) |
| `f` | zoom-to-fit the whole scene |
| `tab` | INSPECT — the live entity table, game paused |
| `e` | FILE VIEW — the scene's source, `j/k` scroll, `/` search with wrap-around |
| `p` | screenshot → `exports/<scene>-<n>.png` |
| `:` | the command bar (below) |
| `q` / `esc` | quit |

## The command bar

`:` opens a vim-style command line with honest errors — bad verbs, junk
numbers and out-of-range values are refused with usage, never silently
accepted:

| command | what it does |
|---------|--------------|
| `:scene <file>` | load any scene mid-flight |
| `:zoom in\|out\|<factor>` | camera zoom, clamped 0.3–4× |
| `:fit` | zoom-to-fit |
| `:reset` | back to spawn |
| `:w [file]` | save the scene (a `.bak` is kept) |
| `:wq` | save and quit |
| `:q` | quit |
| `:screenshot [file]` | PNG of the live frame |
| `:magnet <px>` | coin magnet radius, live |
| `:gravity <force>` | gravity, live |
| `:help` | list commands |

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
                         # magnetism, hazards, transitions, camera,
                         # command grammar, PNG writer vectors
scripts/gates.sh         # the full gauntlet
```

The gates are: a zero-warning `-std=c++23` build, the selftest — including a
**real end-to-end host: the Python SDK spawns a child game that crosses the
pipe and reports home** — every scene must render one real headless frame,
every `next` in the campaign chain must resolve to a real scene file (no
ghost doors), zero electron-era files tracked, and VERSION ↔ CHANGELOG
consistency.

## Layout

```
native/src/spark.hpp/.cpp   the engine: AABB physics, movers + rider carry,
                            coins + magnetism, hazards, goal transitions,
                            camera follow + zoom + decay shake,
                            std::expected scene I/O
native/src/tui.hpp/.cpp     the face: truecolor half-block renderer,
                            gradients, HUD spans, text rails
native/src/logo32.hpp       the mark: the studio emblem as a 32×32
                            truecolor bitmap for the title card
native/src/cmd.hpp          the command bar grammar — honest usage errors
native/src/fx.hpp           the deterministic per-scene starfield
native/src/png.hpp          zero-dependency PNG writer (stored deflate)
native/src/shot.hpp         headless + in-game screenshots
native/src/json.hpp         recursive-descent JSON with \uXXXX → UTF-8
native/src/host.hpp         the ScriptHost: child-process games in ANY
                            language, line-JSON protocol, the IDE frame
                            applier, language runner table
native/src/main.cpp         the studio shell: raw-mode input, fixed
                            timestep, title card, THE ENGINE IDE (editor +
                            live viewport + console), PLAY / INSPECT /
                            FILE VIEW / command modes
native/src/selftest.cpp     engine assertions, including a live SDK child
sdk/dxn3.py                 the Python SDK — one import, whole engine
sdk/dxn3.js                 the JavaScript SDK (NODE_PATH, plain CJS)
sdk/dxn3.hpp                the C++ SDK — compiled games, deque-stable
                            entity pointers
sdk/PROTOCOL.md             the one-page wire contract
sdk/examples/               background · shooter · flappy · bounce ·
                            cards · pong
assets/                     the brand: emblem, banner, social card + SVG src
scenes/*.dxn1.json          the five-scene campaign — data only
scripts/install.sh          the curl one-liner
scripts/gates.sh            the quality gauntlet
```

## History

STUDIO 3 was born as an Electron app with a Python brain (v3.0.01–v3.0.04).
v3.0.05 ported the Spark engine to C++23 and played it in the terminal.
v3.0.06 deleted the Electron, web and Python stacks for good — the studio is
one binary now. v3.0.07 gave the studio its face: the mark descends from the
STUDIO 2 circuit spiral (preserved on the
[`ds2-archive`](https://github.com/DXN1-termux/DXN1-STUDIO/tree/ds2-archive)
branch) with a monolithic 3 carved into it, the title card greets every
launch, the HUD counts your coins, and the command bar whispers usage hints
while you type. v3.0.08 gave the studio somewhere to go: the campaign grew
from three scenes to five — the climb and the gauntlet — and the gauntlet
itself moved into CI, where g++, clang++ and the one-liner installer are
probed on every push. v3.0.09 turned the studio into an engine IDE: boot
into a code editor with your game running beside it, hosted in your own
language — Python, JavaScript, C++23, or anything that speaks stdio JSON —
starting from nothing, live while you type. v3.0.09 is the pivot: the studio became an **engine**.
Bare `dxn3` opens an IDE where you start with nothing, write code in any
language — Python, JavaScript, C++, anything that speaks the one-page
protocol — and it runs live beside your editor; the campaign is now the
demo, the SDKs ship in `sdk/`, and the selftest hosts a real child game
end to end on every run.

MIT — DXN1-termux
