# DXN1 STUDIO 2 — Architecture

DS2 is a single-process, pure-Python desktop IDE: **Python 3 +
Tkinter + the standard library**, with optional AI backends. No
framework, no build step, no native dependencies — clone it, run it.

```
dxn1_studio/
├── app.py            ← the studio: window, menus, palette, terminal, wiring
├── widgets.py        ← core widgets: file explorer, code editor, terminal
├── config.py/theme.py← persistence + theme engine (everything is themed)
└── … 86 feature modules, one lane each, described below
```

## Design rules (what keeps 86 modules coherent)

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
`packages`, `doctor` (environment audit), `depcheck` (imports vs requirements, per-workspace cache), `verbs` (terminal verbs browser).

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
| `python3 -m pytest tests/` | 90 unit groups over every pure engine |
| `scripts/smoke_v290.py` (Xvfb) | 155 live-window checks across 26 feature windows |
| `scripts/smoke_v310.py` (Xvfb) | 20 checks: fuzzy highlight runs, per-buffer cursor memory, session cursor merge |
| `scripts/smoke_v320.py` (Xvfb) | 18 checks: autosave write/switch gates, crash simulation + engine recovery boot, installer `--version` |
| `scripts/smoke_v330.py` (Xvfb) | 13 checks: save-session-now chip (paint, accent glow, fade job), terminal `session save`, palette fuzzy hit |
| `scripts/smoke_v340.py` (Xvfb) | 10 checks: HASHES.txt coverage + sha spot-check, Workshop menu entry, live delta pass (unchanged file skipped, no network) |
| `scripts/smoke_v350.py` (Xvfb) | 20 checks: skip-this-version memory (decline records, auto-check quiet, manual overrides, e2e no-portal), atomic config save, engine-first boot restore with legacy fallback |
| `scripts/smoke_v360.py` (Xvfb) | 16 checks: update heartbeat gating + junk clamp, live `deps` report (missing/unused/alias), `whatsnew` verb, settings round-trip (minutes → clamped seconds), palette fuzzy hits |
| `scripts/smoke_v370.py` (Xvfb) | 15 checks: `deps fix` appends/dedupes/creates requirements.txt with alias-correct pins, second-run no-op, `help <verb>` exact/substring/fuzzy/honest-miss, bare `help` intact, Workshop Dependency Check entry |
| `scripts/smoke_v380.py` (Xvfb) | 24 checks: deps cache fingerprints (stable/content-sensitive/root-listing), hit-after-store, honest invalidation, .dxn1 self-invalidation guard, corrupt-cache fallback, `deps fresh`, fix-sees-late-import, `commands` full/filtered/fuzzy/empty, palette help fallback |
| `scripts/smoke_v390.py` (Xvfb) | 28 checks: cache_state absent/cached/stale/corrupt, verb_rows flattening + git merge + uniqueness, filter honesty, chip states (placeholder → ok → amber drift → click-rescan → off/on toggle + usage line), poll, palette entries, `verbs` window (live filter, honest empty, count label, prefill), Workshop entries |
| `scripts/smoke_v400.py` (Xvfb) | 33 checks: repo_state honesty (plain folder, missing folder, fresh/untracked/staged/clean, detached HEAD, behind-after-fetch with real bare+clone pushes, dirty+behind together), cache_state missing-list severity, git chip states (quiet no-ws/plain-folder, muted branch, amber ●N bold, click→Source Control, off/on toggle + usage, passthrough, commit calms, shared poll), deps severity ladder (absent → red 1 missing → amber drift → red 2 missing → pinned ok), usage lines, chip tooltips, TERMINAL_HELP + verbs + palette rows |
| `scripts/smoke_v410.py` (Xvfb) | 18 checks: red-chip one-gesture repair (click queues `deps fix`, Enter pins, chip honest again, cache re-scanned), amber click stays a plain rescan, branch-chip context menu (repo rows, stage-all routing, copy-branch clipboard, open Source Control, honest plain-folder menu, renderer never raises), Settings watch-chip section round-trip (persist + live redraw both ways) |
| `scripts/smoke_v420.py` (Xvfb) | 15 checks: deps-chip context menu (red-state rows, queue-fix prefill + Enter hint, rescan through the terminal, ok-state loses the repair row, fresh rescan bypasses cache, watch toggle silences the chip), branch-menu additions (AI draft opens panel + fires helper, push/pull route to the visible runner, plain folder stays honest), one shared popup renderer + right-click tooltips |
| `scripts/smoke_v430.py` (Xvfb) | 18 checks: the chip family completes — scribe menu (summary/goal/reset with goal preserved), sesave menu (autosave toggle live both ways, honest no-workspace toast, real snapshot write with chip flash, browse routes to the browser), branch menu 'Commit staged…' (opens Source Control + focuses the box, real focus_message wired), one renderer driving all four menus, Button-3 on every chip, four tooltips, palette rows |
| `scripts/smoke_v440.py` (Xvfb) | 18 checks: the studio keeps its receipts — toasts archive newest-first with kinds, the Activity window e2e (live filter narrowing, honest empty state, click-to-copy through the callback, Clear wipes ring + rows), the scribe goal dialog driven through the app's menu row (prefilled, junk gets an inline error, Set applies chip+config+toast+terminal, Escape cancels), `activity`/`notifications` verb routing, palette row, single archive hook |
| `scripts/smoke_v450.py` (Xvfb) | 16 checks: the receipts survive the night — a seeded activity.json reloads at boot marked previous-session, a toast lands on top and persists atomically, the window shows the "since last time" divider with relative stamps ("just now" / "1h ago"), Clear through the app's real on_change empties ring + file, the next toast re-seeds, a torn file loads as None |
| `scripts/smoke_v460.py` (Xvfb) | 22 checks: the receipts go where you send them — kind dots hide/restore each kind with an honest count (an unnamed kind survives every filter state), Copy all puts the chronological diary on the clipboard and acknowledges, Save as file… drives the real dialog seam to a real atomic file (a cancelled dialog writes nothing), the verbs `activity copy` / `activity export [path]` + honest nonsense hint, help rows, opener wiring |
| `scripts/boot_qa.py` (Xvfb) | 20 checks booting the real studio: menus bound, palette entries live, modules import, scribe chip wired |
| `python3 -m compileall -q dxn1_studio` | The tree always compiles — the gate before every tag |

## Release protocol

Every feature increment: conventional commit → push. Every hour:
bump `APP_VERSION` + README badge + CHANGELOG, run all four gates,
`git tag vX.Y.Z`, `git push origin master --tags`. The tag history
(`git tag --sort=-v`) doubles as the sprint's feature timeline.
