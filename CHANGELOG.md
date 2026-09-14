# Changelog

All notable changes to DXN1 STUDIO. Format based on
[Keep a Changelog](https://keepachangelog.com/); versioning is
`MAJOR.MINOR.PATCH` while in **beta**.

## [1.1.2] — 2026-09-14 · beta

### Added
- Public GitHub launch: real screenshots, social preview, CI (Python 3.10 /
  3.12 headless self-test on Xvfb), contributing guide and issue templates.
- README rebuilt around captured UI shots of the Hub, the IDE with an
  agent proposal card, the command palette, the Packages view and the
  light theme.

### Fixed
- Version metadata across the installer and splash card now reports
  `1.1.2-beta` consistently.

## [1.1.1] — 2026-09-14 · beta

### Added
- **DXN1 Agents** brains table: Local skills (offline), Free cloud
  (Pollinations — no account, no key, no login), BYOK on any
  OpenAI-compatible provider, GitHub Models (free, tracked by GitHub
  login), and the Kilo gateway via an in-studio HTTP client (near-zero RAM —
  never a bundled Kilo instance).
- **In-app Connect flow** for providers that need a login: the studio opens
  the provider page, you sign in, paste the token back, Test & Save. Keys
  never leave `~/.dxn1-studio/config.json`.
- **System prompt studio**: style presets (Default / Concise / Senior dev /
  Custom), extra instructions, and a live preview of the exact effective
  prompt including sandbox boundaries.
- Live `steps · tokens` usage counter fed by backends that report usage.

### Hardened
- Workspace jail: `..` traversal, absolute escapes and symlink escapes are
  rejected; `.git` / `.ssh` / studio internals are unreadable and
  unwritable to agents; catastrophic commands (`rm -rf /`, `sudo`,
  pipe-to-shell downloads, forced pushes) always require explicit Accept —
  even in full-access mode.

## [1.1.0] — 2026-09-13 · beta

### Added
- **Project Hub** as the launch surface: scaffold Python / Flask / Tkinter
  workspaces, open any folder, clone from GitHub with live `git clone`
  output, recent workspaces with relative timestamps.
- **Boot splash**: `dxn1 studio` shows the logo card ~2s, then the studio
  rises. `--no-splash` skips it.
- **Welcome wizard** (5 steps) with hero, name, theme + accent + editor text
  size, first-project intent, and an opt-in Agents slide with brain picker.
- **Interactive guided tour** — spotlight walk across the real UI.
- **Activity bar**, **command palette** (Ctrl+K), **find-in-files**,
  **tab buffers** with unsaved markers, **toasts**, in-editor find bar with
  hit counting, word wrap toggle, auto-save option.
- **Packages view** — opt-in installs (Flask, Requests, httpx, Pillow,
  NumPy, Rich, pytest, Black, Ruff, FastAPI, Uvicorn) with live `pip`
  output, version detection and uninstall.
- **Project export** — ZIP of the workspace (caches/venvs skipped, Flask
  projects get a `requirements.txt`) and single-file export.
- **Run system** — F5 streams the active file (or `app.py` / `main.py`)
  into the interactive terminal; `help` lists studio commands.
- **Error log** — uncaught exceptions land in
  `~/.dxn1-studio/logs/studio.log` with a friendly toast.
- One-command installer (`curl … | bash`) and `--reset-config`,
  `--smoke-test` flags.

## [1.0.0] — 2026-09-13 · beta

### Added
- First internal build: themed Tkinter shell, file explorer, highlighted
  editor, terminal, config persistence, dark/light palettes with four
  accent colours.

[1.1.2]: https://github.com/DXN1-termux/DXN1-STUDIO/releases/tag/v1.1.2
[1.1.1]: https://github.com/DXN1-termux/DXN1-STUDIO/releases/tag/v1.1.1
[1.1.0]: https://github.com/DXN1-termux/DXN1-STUDIO/releases/tag/v1.1.0
[1.0.0]: https://github.com/DXN1-termux/DXN1-STUDIO/releases/tag/v1.0.0
