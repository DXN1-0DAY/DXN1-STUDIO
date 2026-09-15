# DXN1 STUDIO 2 — Architecture

DS2 is a single-process, pure-Python desktop IDE: **Python 3 +
Tkinter + the standard library**, with optional AI backends. No
framework, no build step, no native dependencies — clone it, run it.

```
dxn1_studio/
├── app.py            ← the studio: window, menus, palette, terminal, wiring
├── widgets.py        ← core widgets: file explorer, code editor, terminal
├── config.py/theme.py← persistence + theme engine (everything is themed)
└── … 87 feature modules, one lane each, described below
```

## Design rules (what keeps 87 modules coherent)

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
| `python3 -m pytest tests/` | 91 unit groups over every pure engine |
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
| `scripts/smoke_v470.py` (Xvfb) | 17 checks: honest keys and a quieter voice — every advertised palette accelerator is really bound (19 audited via accel_pattern/looks_like_accel), category tags never chased, the git menu advertises Enter only where a repo exists, the keybindings doc agrees with the code, a muted toast kind keeps its receipt while the screen stays quiet (Settings Toasts section round-trips), `activity export json|csv` + fmt-override + typed-.csv Save-as all follow the extension |
| `scripts/smoke_v480.py` (Xvfb) | 25 checks: the way out is written on the door — honesty units (descendant bindings, esc truth both ways, unbacked hint dropped + reported, notes render, empty bar hides, destroyed host never raises), the git graph e2e (honest bar with F5/+/0/close, all keys really bound, zoom steps/clamps/resets/redraws), the Activity window's first keyboard lane (bar + real Ctrl+F/Ctrl+L/Esc), recents and whatsnew bars e2e, the rest of the family source-wired, doc agreement, the bare plus/minus translator pinned, the palette audit regression |
| `scripts/smoke_v490.py` (Xvfb) | wave-2 door signs: the diff viewer opens at all (the missing _build_footer regression) with its footer verdict, honest bar and working F3/Ctrl+U/Ctrl+C; the git graph draws a real merge topology (the lane_of NameError regression) with hover-tooltip show/hide truth; devtools Ctrl+1…5 tab switching e2e; textdiff, cheatsheet, filestats, scratchpad and the goal-dialog bars all honest; the vacuous-pass lesson pinned — rows are driven, not awaited |
| `scripts/smoke_v500.py` (Xvfb) | 48 checks: wave-3 door signs — the five converter-lab windows that had zero keys (xmlbench, csvkit, unitconv, hexdump, pwdgen) now bind real ones first and e2e-drive them (Ctrl+P pretty, Ctrl+M minify, Ctrl+Shift+C copies through every window, Ctrl+R swaps units, F5 regenerates), mathpad's entry Return finally advertised, branches F5 + gallery Ctrl+F-focus (asserted on focus_get) + sqlitelab's bar, the AI result window copies/replaces/inserts with contextual chips, the quick-actions menu runs actions by number key, bars introspect via bar.pairs, the canonical `<Control-C>` spelling pinned, translator + doc agreement, palette audit regression |
| `scripts/smoke_v510.py` (Xvfb) | 19 checks: the diary writes itself — the gate ships off (no exports folder before consent), `activity snap` writes the JSON diary through the real terminal verb (ring order preserved, round-trips through load_json), `activity auto on|off` flips the gate from the terminal with honest bare-verb reporting, the forced run stamps the clock, the deps menu wears its severity (repair row counts the missing imports, red/amber through the renderer's 4th element — tk entrycget verified), the Settings Activity section + boot hook + half-hour re-arm, the verb help rows, and the engine's honesty under junk intervals and a broken log |
| `scripts/smoke_v520.py` (Xvfb) | 39 checks: the chip menus learn the keyboard — a gesture-gated grab (a real right-click keeps Tk's grab so keys reach the posted menu; a programmatic open releases at once), the unpost poller releases on unpost and on its own 40ms cadence, the first activatable row wakes up active, Home/End/digits drive real rows through `_ds2_keys` (separators never count, beyond-the-end digits no-op), all four chip menus open grabbed and keyboard-ready, the git sync rows wear their divergence (amber ahead-only, red diverged, silent in sync, plain folder offers nothing) via tk entrycget on the real posted menu, the interval picker reads/clamps/junk-proofs (999→168, banana→24, 0→1), the engine honors a 1h gate, bare `activity auto` names the interval, source + KEYBINDINGS doc agreement, and the palette audit regression |
| `scripts/smoke_v530.py` (Xvfb) | 30 checks: the menus come to you — the four chip menus open from the keyboard through all three doors (palette rows advertising Ctrl+Alt+G/E/W/A, the real root binds behind every claim, the `chip <name>` verb through the real dispatcher), a keyboard-opened menu is a real gesture (grab KEPT, first row awake, `_ds2_rows` introspectable) floating just above its chip, dismissal leaves no display-wide grab, the deps red state gains a Copy pip install row whose clipboard truth carries suggested_pins pins, the honest no-workspace path, tooltips naming their accelerator, settings search still finding the snapshot picker, source + KEYBINDINGS/FEATURES doc agreement, and the palette audit regression |
| `scripts/smoke_v540.py` (Xvfb) | 26 checks: every pack answers for itself — the İ index-drift fix e2e through match/split_runs/ranked (positions index the raw text, highlight runs light the right letters, two İ's never double-drift, ASCII byte-for-byte unchanged), pack_stats over every built-in (en first, 100%, all highlight-safe), the `lang audit` verb through the real dispatcher (header, per-pack lines, closing explanation), the branch menu's state-aware copy sibling with clipboard truth per state (recovery when diverged, plain push/pull one move out, silence in sync, no repo no rows, junk kinds ignored), help table agreement, and source agreement |
| `scripts/smoke_v550.py` (Xvfb) | 40 checks: the translator gets a desk — the data layer e2e (own vs working dicts, the İ predicate, the meter counting like the audit), `lang edit es` through the real dispatcher (header meter honest, every key a row, the four markers), live editing with the NOT-highlight-safe warning, the Unsafe filter holding exactly the İ key, clear + seed + atomic save writing a user pack that overrides built-ins and goes live at once, the chooser refusing junk codes and the source of truth while opening clean desks for new codes, verb honesty, Settings and palette doors, settings search, ActionsMenu width accounting (geometry never clips content), palette audit regression (23), and source + doc agreement |
| `scripts/boot_qa.py` (Xvfb) | 20 checks booting the real studio: menus bound, palette entries live, modules import, scribe chip wired |
| `python3 -m compileall -q dxn1_studio` | The tree always compiles — the gate before every tag |

## Release protocol

Every feature increment: conventional commit → push. Every hour:
bump `APP_VERSION` + README badge + CHANGELOG, run all four gates,
`git tag vX.Y.Z`, `git push origin master --tags`. The tag history
(`git tag --sort=-v`) doubles as the sprint's feature timeline.
| `scripts/smoke_v560.py` (Xvfb) | 33 checks: the desk grows eyes — the honest ledger e2e (`pack_diff` real/seeds/stale buckets exact, unsafe as a property not a bucket, a seeded pack 100% covered and 0% real, junk codes silent), `lang diff` through the real dispatcher (per-pack ledger, bare verb names the current language, `en` refused as the source that does not differ from itself, unknown packs listed, seeds named byte-identical), the desk's fifth chip holding exactly the re-seeded key and releasing it on edit, the meter printing the untouched counter, and the live PackPreview — five anatomy slices rendering the pack's strings in accent while English shows through grey, keeping up keystroke for keystroke, Ctrl+P re-raising the same window, and closing with the desk that opened it; help + source + doc agreement, palette audit regression (23) |
| `scripts/smoke_v570.py` (Xvfb) | 25 checks: packs travel light — the data layer (export as a user-pack-shaped file from work or own strings, the desk re-importing its own export whole, export_template files importing, replace/empty-drops/junk-skips in place, unreadable and non-dict files answering (-1, 0)), `lang audit` printing every number (real_pct per pack, en skipped, a seeded pack showing 100% covered and 0% real in one line), dialog-driven desk export/import through monkeypatched filedialogs (file truth, junk skipped, meter keeps counting, empty drops back to English, unreadable honest, cancelled no-ops, import + Save live at once), the preview's buttons slice, source + doc agreement, and the palette audit regression (23) |
| `scripts/smoke_v580.py` (Xvfb) | 26 checks: the pack gets a checkup — the data layer (a mixed mapping landing in the right buckets with the honest ledger riding along, junk pairs counted the way an import skips them, unsafe as a property of the value with stale keys included, es clean at 100% real, file reports matching installed reports, unreadable/non-dict/missing files refusing with the error class, a seeded pack structurally clean at 0% real), `lang check` through the real dispatcher (bare verb with en current refusing, bare verb reviewing the current pack, named pack head/ledger/verdict/way-out, a seeded pack reading 0% real in one breath, unknown code and no file naming both doors, file mode naming every finding and counting the verdict, unreadable files honest), `lang pack` (file truth, never overwriting, en refused, usage, unknown codes, a directory dest), help + source + doc agreement, and the palette audit regression (23) |
| `scripts/smoke_v590.py` (Xvfb) | 12 checks: the desk grows to fit — the chooser printing every number (es at 100% real, a seeded pack at 0% real in its row), the desk opening no narrower than what it packed (>= 680 and >= its requested width), the preview ratcheting out for a 120-char translated string and never shrinking back (the high-water mark recorded in `_fit_w`), the audit's closing lines naming the whole verb family (lang check <file> · lang pack <code> · lang diff <code>), source + doc agreement, and the palette audit regression (23) |
