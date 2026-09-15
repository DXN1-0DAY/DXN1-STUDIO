# DXN1 STUDIO 3

![version](https://img.shields.io/badge/version-3.0.01-8b5cf6?style=flat-square)
![face](https://img.shields.io/badge/face-electron-22d3ee?style=flat-square)
![brain](https://img.shields.io/badge/brain-python-34d399?style=flat-square)
![engine](https://img.shields.io/badge/spark_2d-built_in-fbbf24?style=flat-square)

**A beautiful studio for code and games.** STUDIO 3 is a full rebuild:
the old Python/Tkinter app is retired (archived on the `ds2-archive`
branch) and this repo starts fresh, UI-first.

- **Electron face** — frameless window, dark glass design system,
  gradient accents, command palette, custom titlebar. The UI is the
  product: every pixel is meant.
- **Python brain** — `engine/` owns the workspace over a stdio JSON
  protocol (atomic writes, sandboxed paths, honest errors). Same brain,
  any face.
- **Spark 2D engine, built in** — scenes are plain JSON
  (`scenes/*.dxn1.json`), edited in the studio's scene dock and played
  with **F5**. Entities, AABB physics, platformer controller, camera
  follow, particles — 2D only, on purpose.

## Run

```bash
npm install && npm start        # desktop (Electron + Python engine)
```

Or open `renderer/index.html` in a browser: the face runs in demo mode
with a virtual filesystem — the whole UI works, honestly labelled.

## Keyboard

| Keys | Action |
|---|---|
| `Ctrl K` | command palette |
| `Ctrl P` | go to file |
| `F5` | play / stop scene |
| `Ctrl S` | save |
| `Ctrl \`` | toggle terminal |
| `Ctrl ,` | settings |
| `Ctrl Shift F` | search in project |

## The 24-hour plan (set by DXN1)

| Day | Focus |
|---|---|
| **Day 1 — today** | the UI: full Electron rebuild, design system, Spark playable |
| **Day 2** | the engine, purely: Spark deepens (tilemaps, sprites, sound, export) |
| **Day 3** | the IDE functions: git suite, agents, plugins, the full toolkit |

Versions start at **v3.0.01** and grow by giant hourly updates:
v3.0.01 → v3.0.02 → … — every update is worth installing.

## Layout

```
electron/    main + preload (spawn the engine, IPC, frameless window)
renderer/    index.html · styles.css (design system) · app.js · spark.js
engine/      the Python brain — stdio JSON bridge (python3 -m engine)
scenes/      Spark scenes (*.dxn1.json)
tests/       engine tests:  python3 -m unittest discover -s tests
```
