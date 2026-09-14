# Changelog

All notable changes to DXN1 STUDIO. Format based on
[Keep a Changelog](https://keepachangelog.com/); versioning is
`MAJOR.MINOR.PATCH` while in **beta**.

## [1.1.5] — 2026-09-14 · beta

### Added
- **The Update Portal** — detecting a new GitHub release now opens a
  full-screen, cinematic takeover (built around new portal art):
  *"We have detected a new version"* with the detected version number,
  release highlights, and one big **Install update & restart** button.
  Installing streams the new build from GitHub (or `git pull --ff-only`
  in clones), verifies every module with `compileall`, shows honest
  progress for **at least 3 seconds**, then restarts the studio into
  the fresh build. Decline and the portal answers: *"You cannot
  continue on this version — for security and for your own experience
  reasons."* (new `updater.py`; checks run at launch and via
  Help → Check for Updates)
- **Agents 2.0 — the chat, rebuilt.** Streaming answers with a live
  **■ stop** button; markdown chat rendering (headings, bullets, code
  cards with **Copy · To editor · Save as…** + language chip); **6
  personas** (Balanced, Concise, Senior dev, Architect, Debugger,
  Teacher) with a one-tap persona bar; **17 slash commands** (`/help`,
  `/new`, `/tests`, `/bugs`, `/explain`, `/run`, `/persona`,
  `/sessions`, …) with an arrow-key palette; **@-mentions** that attach
  workspace files to any prompt; **per-workspace session history** that
  survives restarts (`/sessions` to reopen)
- **`search_code` agent tool** — regex grep across the workspace, so
  the agent finds things itself instead of asking
- **Editor Pro.** Regex find & replace with `\\1`-style template
  expansion (the `.*` toggle in the find bar, "bad regex" surfaced
  inline); block indent/outdent (Tab / Shift+Tab, Ctrl+] / Ctrl[)
  across selections as single undo steps; word-under-cursor spotlight
  (3+ chars, suppressed while selecting or finding); **10 new
  languages**: Go, Rust, Java, C, C++, C#, Kotlin, PHP, Ruby, Shell
  (plus `.cc/.cxx/.hpp/.h/.bash/.zsh/.kts/.phtml/...` aliases)
- Chat code blocks drop straight into a fresh editor tab (**To editor**)
- The installer now ships every module from a list kept in sync with
  the package (including `gitpanel.py` and `updater.py`) and pins the
  installed copy's version to the installer's own

### Fixed
- **The installer lied about versions.** It still announced 1.1.3
  while the latest release was 1.1.4 — the version is now a single
  `INSTALLER_VERSION` constant, printed correctly and stamped into the
  downloaded copy so the IDE never claims an older number than what it
  ships
- The installer's module list had drifted from the package (new
  modules were missing from fresh installs); the update portal mirrors
  the exact same list, so an in-place update can never strand a file
- Update notices were easy to miss (a small toast); the portal replaces
  them and is impossible to overlook

## [1.1.4] — 2026-09-14 · beta

### Fixed
- **The free cloud brain is alive again.** Pollinations started
  requiring a web `Referer` on anonymous calls — every request got
  HTTP 403 and the keyless tier looked dead. The client now sends the
  right headers on both the JSON and plain-text routes, and skips
  pointless model retries when the provider answers 403/401.
- **Provider boilerplate never poses as an answer.** When a provider
  answers HTTP 200 with "the API key used for this request has reached
  its budget" prose, the stack now treats it as a failure and falls
  over (or surfaces the friendly setup guidance) instead of printing
  the junk into the chat.

### Added
- **Find & Replace** — the find bar grew a replace row (`Ctrl+H`, or
  the `⌄ replace` chevron): live hit counter, Replace current, Replace
  all as a single undoable step, and a status line that tells you
  exactly what happened.
- **Canvas Game project template** — a complete, playable orb-dodging
  game loop (arrows/WASD, lives, score ramp, R to restart) as a new
  scaffold on the Hub and in the wizard. The Hub template grid now
  sits flush at ten cards — no lone-hole row.
- **`@` symbols for C-family languages** — `Ctrl+K` `@` now outlines
  Go, Rust, Java, Kotlin, C/C++, C#, Swift, Dart and PHP files
  (functions, structs, impls, classes), with control-flow keywords
  filtered so `while` never shows up as a function.
- Fresh hub hero artwork — the concentric-squares motif is no longer
  clipped by the banner edge.

## [1.1.3] — 2026-09-14 · beta

### Added
- **Source Control panel** — a Git sidebar that speaks plain `git`:
  branch chip, changed files with staged/unstaged sections, per-file
  stage/unstage, one-click commit (auto-stages when nothing is staged),
  recent history, `git init` offer for plain folders, conflict markers.
  Reachable from the activity bar, the toolbar, the View menu and
  `git <args>` terminal commands that stream output live.
- **Free-brain failover stack** — the "Free cloud" brain is no longer a
  single vendor: keyless cloud models first, transparent failover to
  GitHub Models when a GitHub login exists, and the header chip always
  names the provider that actually answered.
- **`@` symbols in the command palette** — type `@` in Ctrl+K to jump to
  any `def` / `class` in the open file (JS/TS functions and Markdown
  headings too).
- **Bookmarks** — click a line number (or Ctrl+F2) to bookmark; F2 /
  Shift+F2 walk them; accent-highlighted in the gutter.
- **Tab snippets** — Tab expands `ifmain`, `pdb` and `smain` in Python
  files; plain indent otherwise (never steals focus).
- **Agent quick actions** — one-tap chips above the agent input:
  Explain file · Write tests · Find bugs · Docstrings.
- **Searchable settings** — type in Settings to filter rows across every
  section; empty cards collapse away.
- **New project kinds** — CLI Tool (argparse with subcommands) and
  Static Website (HTML + CSS + JS), on the Hub and in the wizard.
- **Animated boot splash** — baked brand card (logo, wordmark, version
  chip) with fade-in, shimmer progress bar and rotating status lines.
  Click to skip; `dxn1 studio` in the terminal replays it.
- Word count, selection stats and bookmark state in the status bar;
  per-tab context menu (close others / close all / copy path / reveal in
  file manager); "Reveal in File Manager" in the explorer menu too.
- Workspace session restore, auto-save, update checker against GitHub
  releases, and a shortcuts cheat-sheet.

### Changed
- **Themed in-app menu bar** — the native menubar (un-themeable white on
  Linux) is replaced by a dark bar that matches the studio: brand mark,
  version chip, hover states, fully styled dropdowns.
- Project Hub: uniform card grid, slimmer regenerated hero artwork that
  blends into the background, tighter geometry — all nine templates plus
  recents fit without clipping.
- Terminal: ANSI escapes stripped, carriage-return progress bars
  resolved, log capped so long runs can't eat memory.

### Fixed
- Gutter current-line number rendered with a literal `_` suffix instead
  of an accent highlight.
- Command palette and Quick Open kept their opening size after the
  result list shrank, leaving a large dead area.
- Git panel listed an untracked directory as a nameless row (now
  `status -uall`) and showed `HEAD` on fresh repositories (now resolves
  the unborn branch name).
- Source-control panel constructed before the terminal existed during
  boot (attribute-order crash on first launch).

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
