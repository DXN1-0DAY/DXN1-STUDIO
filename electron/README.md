# DXN1 STUDIO — Electron shell

The Electron front end over the **same Python engine** you already
run. The shell is pure HTML/CSS/JS (no build step); the engine keeps
owning files, workspaces and every future capability, exposed over a
newline-delimited JSON stdio bridge (`dxn1_studio/bridge.py`).

```
electron/                 ← this shell (UI frontier)
dxn1_studio/bridge.py     ← the engine side of the bridge
```

## Run it

```bash
cd electron
npm install          # downloads Electron once (~100 MB)
npm start
```

Optional environment:

| Variable        | Meaning                                        |
|-----------------|------------------------------------------------|
| `DXN1_PYTHON`   | python executable for the engine (default: auto) |
| `DXN1_WORKSPACE`| folder to open at boot (default: repo root)    |

## What works in the shell today

- custom titlebar with real window controls
- explorer: create / rename / delete files & folders (engine-backed),
  collapsible dirs, per-file size, right-click context menus
- search across every file in the workspace
- editor: syntax highlighting (python/js/ts/json/html/css/md/sh),
  line numbers, find bar, word wrap, font zoom, auto-indent,
  dirty dots, autosave option
- tabs: open/close/dirty-guard, middle-click close, right-click menu,
  **tab overview** (Ctrl+Alt+T)
- command palette (Ctrl+K) + quick open (Ctrl+P), fuzzy
- terminal panel with working verbs (`help`, `ls`, `cat`, `new`,
  `rm`, `theme`, `accent`, `about`, …)
- settings: dark/light, six accents, font size, autosave, wrap
- session restore (open tabs survive restarts)
- **demo mode**: if the engine can't be reached, a virtual workspace
  keeps every control alive — no dead buttons, ever.

## Architecture

```
┌──────────────┐  ipc   ┌───────────┐  stdio JSON  ┌──────────────┐
│ renderer     │ ─────▶ │ main.js   │ ───────────▶ │ bridge.py    │
│ (HTML/CSS/JS)│ ◀───── │ (Electron)│ ◀─────────── │ (the engine) │
└──────────────┘        └───────────┘              └──────────────┘
```

Security: context isolation on, node integration off, the renderer
only ever talks to the small `window.dxn1` API in `preload.js`.
