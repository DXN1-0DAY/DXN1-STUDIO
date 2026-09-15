# DXN1 STUDIO — the Electron + Web UI path

**Decision (2026-09-15, DS2 sprint):** the UI goes Electron — the user
wants the best-looking interface possible, and web tech is where that
lives. The Python core is NOT thrown away; it becomes the brain that
every face drives. This is the VS Code architecture, adapted:

```
┌────────────────────────────────────────────────────────────┐
│  FACES (web tech)              │  BRAIN (Python)           │
│  ├─ Electron shell  electron/  │  ├─ agent engine, LLM     │
│  ├─ any browser (Termux, LAN)  │  ├─ 121-command palette   │
│  │    webui/ (no build step)   │  ├─ git suite, tools      │
│  └─ Tkinter desktop (v2 line)  │  └─ workspace + plugins   │
└────────────────────┬───────────┴──────────┬────────────────┘
                     │  localhost JSON APIs │
                     ├─ webridge.py  (HTTP, app-level: tabs, palette,
                     │                run, state, theme tokens, files)
                     └─ bridge.py    (stdio, workspace file engine —
                                      ships since v2.3x, fully tested)
```

## The three layers

1. **`dxn1_studio/webridge.py` — the app bridge (HTTP).** Pure stdlib.
   Binds `127.0.0.1` ONLY, token-guarded (per-session token written to
   `.dxn1/bridge_token`, chmod 600), workspace-sandboxed paths. Serves
   `webui/` and exposes: `/api/state`, `/api/tree`, `/api/file`
   (GET/POST), `/api/commands`, `/api/command` (POST), `/api/open`,
   `/api/run`. Every mutation is scheduled onto the Tk main loop via
   `root.after` — the HTTP thread never touches widgets. Start it from
   the studio: palette → **"Web UI / Electron — start the bridge
   server…"** (URL + token land in the terminal).

2. **`webui/` — the web renderer.** Vanilla HTML/CSS/JS, zero
   dependencies, zero build step (works offline; Termux-friendly).
   Cinematic dark theme with live tokens from the Python theme —
   change the accent in Tkinter settings and the web UI follows on the
   next poll. Current surface: explorer, tabs, editor with line
   gutter + save (Ctrl+S), terminal tail, status bar, full command
   palette (Ctrl+K → all 121 commands).

3. **`electron/` — the native shell.** A thin BrowserWindow around the
   bridge URL (sandboxed renderer, `nodeIntegration: false`,
   contextIsolation on). No UI logic lives here — by design.

## Running it

```bash
# 1. start the studio + bridge (inside the app's palette), or:
python3 -c "from dxn1_studio.webridge import start_bridge"   # API check

# 2. browser face — open the printed URL in any browser

# 3. electron face —
cd electron && npm install && npm start -- \
  --url "http://127.0.0.1:PORT/?token=TOKEN"
```

## Phases

- **Phase 1 (v2.71.4, done):** HTTP bridge + web renderer seed +
  Electron shell scaffold. Tkinter remains the primary face.
- **Phase 2:** web renderer parity sprint — syntax highlighting,
  multi-tab editing, settings, git panel, agent chat over the same
  API. Each parity item is a patch release on the v2.71.x line.
- **Phase 3:** packaging — electron-builder targets (Linux AppImage,
  Windows NSIS, macOS dmg), the studio ships both faces.
- **Termux note:** the browser face is the Android story (the bridge
  + renderer run fine under Termux + browser); Electron itself targets
  desktop platforms only.

## Security rules (non-negotiable)

- Bridge binds localhost only; never `0.0.0.0`.
- Token required on every `/api/*` call; static assets are the only
  unauthenticated routes.
- File paths resolve against the workspace; escapes are refused (the
  same contract `bridge.py`'s tests enforce).
- No Node integration in the renderer; the preload exposes only
  `{shell, platform}` metadata.
