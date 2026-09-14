# DXN1 STUDIO 2 — Architecture

DS2 is a single-process, pure-Python desktop IDE: **Python 3 +
Tkinter + the standard library**, with optional AI backends. No
framework, no build step, no native dependencies — clone it, run it.

```
dxn1_studio/
├── app.py            ← the studio: window, menus, palette, terminal, wiring
├── widgets.py        ← core widgets: file explorer, code editor, terminal
├── config.py/theme.py← persistence + theme engine (everything is themed)
└── … 79 feature modules, one lane each, described below
```

## Design rules (what keeps 79 modules coherent)

1. **One module = one lane.** Every feature lives in its own file
   with a public `open_*(parent, theme, …)` opener, so parallel
   contributors never collide.
2. **Defensive wiring.** `app.py` attaches each module through
   `try/except` closures — a broken feature deactivates itself, the
   studio keeps booting (menu, palette, terminal and help entries
   are all defensive patches).
3. **Pure engines + thin windows.** Logic that can be tested is a
   plain function/class (`ClipRing`, `FocusEngine`, `parse_blocks`,
   `http_request`, `shade_ramp`…); the Tk window is a dumb shell
   over it. That's why `tests/` runs headless and fast.
4. **Never raise at the UI boundary.** Every window refresh, poller
   and close path swallows and logs; error reporting goes through
   `errors.py`.
5. **Persist into the workspace, not the OS.** `.dxn1/` holds
   bookmarks, scan history, agent memory; the user-level store holds
   config, sessions and window geometry.

## Layer map

### Core
| Module | Role |
|---|---|
| `app` | Main window: menus, command palette (Ctrl+K), terminal command router, statusbar chips, session save/restore, toasts, what's-new |
| `widgets` | File explorer, code editor (gutter, bookmarks, minimap hooks), terminal |
| `config` | JSON-backed settings + needs-onboarding flow |
| `theme` | Theme engine (`from_config`), dark/light/community palettes |
| `errors` | Traceback capture, quiet logging, explain-handoff to the agent |
| `splash`, `onboarding`, `tour`, `checklist`, `whatsnew`, `cheatsheet` | First-run & learnability surface |

### Editor features
`multicursor`, `snippets2`, `macros`, `minimap`, `linesort` (sort/
dedupe/shuffle/trim), `bookmarks` (persistent, gutter, F2 nav),
`outline`, `search` (find-in-files), `diffview`, `recents`,
`quick_actions`, `scratch`, `zen` (focus writing + session stats),
`scribe` (statusbar words/WPM meter), `focus` (pomodoro),
`clipboard` (paste-from-history ring), `geom` (per-screen window
geometry memory).

### Git & projects
`gitpanel` (source control sidebar), `branches` (branch manager),
`gitgraph` (visual graph), `commit_msg` (AI commit messages),
`backup` (workspace snapshots), `export` (ZIP/export), `projects`
(scaffolding), `hub` (Project Hub), `gallery` (templates),
`workspace_stats`, `filestats` (+ scan-history sparkline),
`treeexport` (ASCII tree for READMEs).

### Developer tools (Workshop menu)
`devtools` (regex/JSON/text/time), `sqlitelab` (SQLite browser),
`hasher` (checksums/manifests), `restbench` (HTTP workbench),
`colorkit` (hex/rgb/hsl + WCAG contrast + ramps), `markprev`
(live markdown preview), `charts` (paste-numbers chart studio),
`unitconv` (unit converter), `charmap` (Unicode browser),
`textcase` (identifier case converter), `pwdgen` (secrets-CSPRNG PassForge), `numbase` (bases 2-36 + bit inspector), `csvkit` (CSV Lab paste-&-peek), `mathpad` (safe expression calculator), `hexdump` (ByteSnoop hex inspector), `textdiff` (two-paste diff), `xmlbench` (XML pretty/minify/validate), `jwt`, `cronexp`,
`envcheck`, `gen` (test data), `readability`, `usagedash`,
`packages`, `doctor` (environment audit).

### AI surface
`agent` (DXN1 Agents 2.0 panel), `llm` (pluggable backends),
`ai_lint` (AI code review), `memory` (per-workspace agent memory),
`prompts` (prompt library), `pair` (pair mode), `sandbox`
(agent tool loop with permissions), `quick_actions`.

### Platform
`i18n` (eight language packs, `lang` switcher, tr() live in splash/hub/git/newest windows), `plugins` (Plugin API v1 + registry),
`sync` (settings sync), `term` (task runner), `updater`
(update portal), `community_themes` (theme gallery).

## Testing & QA harness

| Harness | What it proves |
|---|---|
| `python3 -m pytest tests/` | 53 unit groups over every pure engine |
| `scripts/smoke_v290.py` (Xvfb) | 131 live-window checks across 21 feature windows |
| `scripts/boot_qa.py` (Xvfb) | 20 checks booting the real studio: menus bound, palette entries live, modules import, scribe chip wired |
| `python3 -m compileall -q dxn1_studio` | The tree always compiles — the gate before every tag |

## Release protocol

Every feature increment: conventional commit → push. Every hour:
bump `APP_VERSION` + README badge + CHANGELOG, run all four gates,
`git tag vX.Y.Z`, `git push origin master --tags`. The tag history
(`git tag --sort=-v`) doubles as the sprint's feature timeline.
