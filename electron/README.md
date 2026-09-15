# DXN1 STUDIO — Electron shell

A native desktop window around the **same Python engine** you already
run. The engine serves the web face (webui/) over a token-guarded
localhost bridge; this shell is that page in a real window with a
real menu. One brain, two faces — the browser and this window.

```
electron/                 ← this shell (the window)
webui/                    ← the renderer the bridge serves
dxn1_studio/webridge.py   ← the bridge (HTTP + token, engine-backed)
dxn1_studio/bridge.py     ← the stdio JSON engine (headless hosts)
```

## Run it

1. In the Tkinter studio, run the palette command
   **"Web UI / Electron — start the bridge server…"** — it prints a
   `http://127.0.0.1:PORT/?token=TOKEN` URL (the token is also saved
   to `<workspace>/.dxn1/bridge_token`).
2. Then:

```bash
cd electron
npm install          # downloads Electron once (~100 MB)
npm start -- --url "http://127.0.0.1:PORT/?token=TOKEN"
```

No URL given? The shell opens the **ramp page** with these exact
instructions. You can also export `DXN1_URL=…` instead of `--url`.

## Package it (`electron-builder`)

Config lives in `package.json` → `build` (AppImage + deb on Linux,
nsis + portable on Windows, dmg on macOS):

```bash
npm run dist         # output in electron/dist/
```

The Python engine is NOT bundled — the shell talks to whatever
studio/bridge you point it at, so the brain always stays current.

| Variable        | Meaning                                        |
|-----------------|------------------------------------------------|
| `DXN1_URL`      | bridge URL to load at boot (same as `--url`)   |

## What works in the wrapped web face

Everything the browser face has — explorer (create/rename/delete),
tabs (close via ✕ or middle-click, dirty guards), the highlighted
editor (save, word wrap, Ln/Col, session + scroll restore),
Ctrl+K palette, Ctrl+P quick-open, settings with live accents,
source control (status/commit/push/pull/diff), the agents drawer,
and a real terminal with history. See webui/ — one face, no drift.

## Architecture

```
┌──────────────┐  loads  ┌──────────────────┐  serves  ┌──────────────┐
│ main.js      │ ──────▶ │ webui over HTTP  │ ───────▶ │ the engine   │
│ (Electron)   │ ◀────── │ webridge (token) │ ◀─────── │ (Python core)│
└──────────────┘  ipc    └──────────────────┘          └──────────────┘
```

Security: context isolation on, node integration off, sandbox on,
external links open in the system browser, and every API call rides
the bridge token. `electron/renderer/` is the legacy pre-bridge
prototype, kept for reference until DS3.
