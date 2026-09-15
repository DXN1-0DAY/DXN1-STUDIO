# Contributing to DXN1 STUDIO 3

The studio is one C++23 binary, a folder of JSON scenes and two shell
scripts. Contributions are welcome — scenes are the easiest way in, and
they require zero C++.

## The one rule

**All gates green, always.** Before you push, run:

```bash
bash scripts/gates.sh
```

Six checks must pass: zero-warning C++23 build (g++), the engine selftest,
a real headless frame for every scene, the campaign chain resolving to real
files, zero electron-era files tracked, and VERSION ↔ CHANGELOG consistency.
CI runs the same gauntlet on every push under g++ **and** clang++ — a red
badge gets reverted.

## Ways in

**1. Scenes (no code, pure JSON).** A scene is a `.dxn1.json` file — copy
`scenes/playground.dxn1.json`, keep the schema (`player`, `coin`, `mover`,
`spike`, `goal`, `sign` tags; movers carry riders, coins magnetize), wire
`next` to chain it into the campaign, and gate 3 + 3b will verify your
frame and your door. Design rules of thumb: ledge steps ≤ ~90 px of climb,
bigger climbs ride a `mover`, every hazard should be avoidable at the
speed the sign promises.

**2. Native (C++23).** `native/src/` is the engine (`spark`), the face
(`tui`), the command grammar (`cmd`), the PNG writer (`png`, `shot`) and
the shell (`main.cpp`). Keep the build zero-warning under `-Wall -Wextra
-Wpedantic`, keep dependencies at zero (libstdc++ only), and grow the
selftest (`native/src/selftest.cpp`) with every engine behavior you add —
62 assertion groups and counting.

**3. Docs & brand.** `assets/` holds the mark with its SVG sources;
screenshots in `docs/img/` are rendered by the binary itself
(`dxn3-native --scene <file> --screenshot out.png`) — regenerate, never
hand-edit.

## Conventions

- Conventional commits: `feat:`, `fix:`, `docs:`, with a body that says
  why, not just what.
- Small releases: bump `VERSION`, prepend `CHANGELOG.md`, tag `vX.Y.Z`,
  push with `--tags`. Never tag red.
- Scenes are data: if a level needs new engine behavior, the engine gets
  a selftest first, then the level uses it.

MIT — DXN1-termux
