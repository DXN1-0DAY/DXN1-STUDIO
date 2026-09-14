# DS2 Feature Index — everything shipped in the DS2 sprint

> The complete, grouped list of what **DXN1 STUDIO 2** adds on top of
> the classic studio. Every module is pure stdlib + Tk, defensively
> wired (any missing module degrades gracefully), and themed end-to-end.

## Visual Git Suite (v1.4.0)

| Feature | Where | What it does |
|---|---|---|
| Visual diff viewer | `diffview.py`, palette → *Diff workspace vs HEAD* | Side-by-side panes with word-level highlighting, or unified patch view; tinted gutters; `+adds −dels ~mods` pills; hunk navigation ‹ › with a live counter; Copy patch |
| Commit graph | `gitgraph.py`, git panel → *Graph* | All-branch history as a real lane graph from parent topology; click a commit for sha/parents/refs; Copy SHA, Diff vs parent, Checkout; live filter box |
| Branch manager | `branches.py`, git panel → *Branches* | Create, checkout (double-click), rename, delete (two-click confirm + force path), merge `--no-ff`, track remote branches; ahead/behind badges; tag chips |
| Panel toolbar | `gitpanel.py` | Graph + Branches buttons one click from Source Control |

## Intelligence (v1.5.0)

| Feature | Where | What it does |
|---|---|---|
| Agent memory | `memory.py`, palette → *Agent memory* | Per-workspace JSON bank (`.dxn1/memory.json`): facts (deduped), preferences, rolling summary; injected into the system prompt every session |
| `remember:` | agent chat | `remember: this project uses pytest` — instant teaching, no model call |
| Token usage dashboard | `usagedash.py`, palette → *Token usage dashboard* | 14-day chart, per-model share bars, per-workspace totals, cost estimates, CSV export, two-click clear |
| Engine hooks | `sandbox.py` | `AgentEngine` injects memory at build; records token deltas per turn — best-effort, never blocks |

## Assistant Superpowers (v1.6.0)

| Feature | Where | What it does |
|---|---|---|
| AI quick actions | `quick_actions.py`, palette → *AI: …* | Explain, Refactor, Add docstring, Write tests, Fix bugs, Add type hints, Optimize — streamed, with code-block extraction and Insert/Replace-selection |
| AI commit messages | `commit_msg.py`, git panel → *✨ AI msg* | Conventional Commits draft from the staged diff; you edit before commit |
| AI review ("gutter eyes") | `ai_lint.py`, palette → *AI: review this file* | Whole-file review → severity-coloured findings; double-click jumps to the line |
| Pair mode | `pair.py`, palette → *Pair mode* | Plan (no code) → you approve/edit → build through the real sandboxed engine with approval gates |

## Onboarding v2 (v1.7.0)

| Feature | Where | What it does |
|---|---|---|
| Workflow slide | `onboarding.py` | New wizard step: the four moves worth knowing tonight |
| Tour v2 | `tour.py` | Spotlight steps for pair mode, quick actions, memory, usage, visual git |
| Cheat sheet | `cheatsheet.py`, Help → *DS2 Cheat Sheet…* | Searchable grouped reference: core moves, editor power, AI workflow, visual git, intelligence, terminal talk |
| First-run checklist | `checklist.py` | Friendly starter checklist for brand-new workspaces |

## Project Hub v2 (v1.8.0)

| Feature | Where | What it does |
|---|---|---|
| Workspace statistics | `workspace_stats.py` | Files, lines, language mix, size, commit count — one capped walk, zero exceptions |
| Pinned workspaces | hub recents | Pin ⚑ floats a workspace to the top with an accent border |
| Live stats on cards | hub recents | "128 files · Python 61% · 12 commits" under every recent |
| Instant search | hub recents | Type to filter workspaces by name or path |
| Rust + Go scaffolds | `projects.py` | Real Cargo.toml + main.rs, go.mod + main.go starters — 12 templates total |

## Themes (v1.9.0)

| Feature | Where | What it does |
|---|---|---|
| Theme gallery | `community_themes.py`, palette → *Theme gallery* | 12 curated palettes as live swatch cards; Apply saves + restarts into the theme |
| Custom theme engine | `theme.py` | `custom_theme` palette overrides with strict fallbacks — broken themes can never break the studio |

## Keyboard additions (DS2)

- `Ctrl+K` → type the feature name (graph, branches, memory, usage,
  pair, review, themes…) — every DS2 feature is a palette command
- `remember: <fact>` in the agent chat
- `@symbol` jump, bookmarks, snippets — unchanged, now documented in
  the cheat sheet

## i18n & Sync (v2.1.0)

| Feature | Where | What it does |
|---|---|---|
| Localization | `i18n.py` | 8 language packs (en/es/fr/de/pt/zh/hi/ja), dotted keys, graceful fallback, community packs as JSON |
| Settings sync | `sync.py` | Private-gist sync of the safe settings subset via the GitHub CLI login — secrets never travel |

## Seeing & Doing (v2.2.0)

| Feature | Where | What it does |
|---|---|---|
| Editor minimap | `minimap.py`, palette toggle | Role-coloured line blocks with a draggable viewport; hides for short files |
| Task runner | `term.py`, palette → *Task runner* | `.dxn1/tasks.json` named commands with per-kind defaults, run through the studio's process runner |

## Starting & Measuring (v2.3.0)

| Feature | Where | What it does |
|---|---|---|
| Next.js + Svelte scaffolds | `projects.py` | Real package.json/pages/API route and App.svelte/vite starters — 14 templates |
| Zen writing stats | `zen.py` | Paste-spike-filtered WPM, session peak, word-goal HUD — memory only |
| Plugin API | `plugins.py` | Hooks, command registration, manager UI |

## Knowing Your Workspace (v2.4.0)

| Feature | Where | What it does |
|---|---|---|
| File statistics | `filestats.py`, palette → *File statistics*, terminal `stats` | Read-only scan: per-extension counts/bytes, largest files, skipped-dirs report; clickable bar chart filters the largest-files table; copy report, export `.dxn1/filestats.md`, CLI `python3 -m dxn1_studio.filestats` |
| Recent-files picker | `recents.py`, Ctrl+R, File menu | Quick-Open-style fuzzy popup over the existing recents list — basename prefix beats path substring beats subsequence |
| Plugin status items | `app.py` statusbar | Plugin-registered status text now appears in the bar (5 s refresh, capped at 3, broken plugins can't hurt it) |
| Persistent bookmarks | `bookmarks.py`, palette → *Bookmarks — browse all…* | The old gutter bookmarks now survive restarts: `.dxn1/bookmarks.json` per workspace, restored on open, split-view aware, with a workspace-wide browser (snippet previews, jump/remove/clear) |
| Prompt library | `prompts.py`, palette → *Prompt library* | Saved reusable asks with `{file}/{selection}/{lang}…` auto-fill, 6 starters, save-from-input, inserts straight into the agent chat |
| Line tools | `widgets.py`, Edit menu | Sort lines (A→Z / numeric / Z→A) and Remove Duplicate Lines on the selection |
| Error explainer | `app.py`, terminal `explain`, palette | Nonzero exit + traceback detected → one command hands the block to the agent with a fix-me prompt (clipboard fallback) |
| What's New | `whatsnew.py`, Help → *What's New…* | The changelog rendered as a release rail + notes pane; auto-opens exactly once after each upgrade (`last_seen_version`) |

## Knowing Your Places (v2.6.0)

| Feature | Where | What it does |
|---|---|---|
| Hub insights strip | `workspace_stats.py` + Project Hub | An aggregate *at a glance* line above the recent workspaces: total workspaces, files, lines, disk size and the dominant languages across everything the hub tracks |
| Branch chips | Project Hub cards | Every recent workspace shows its current git branch (`⎇ main`) — 4 s timeout, locked repos can't stall the hub |
| Hub context menu | Project Hub, right-click a card | Open, Reveal in file manager, Open terminal here (5-way fallback), Copy path, Snapshot now (zip backup), Pin/Unpin, Remove — with a flash-status confirmation in the bottom bar |
| Encoding + EOL chip | `app.py` statusbar | `UTF-8 · LF` (or `UTF-8 BOM` / `UTF-16` / `non-UTF8` / `CRLF` / `CR`) for the current file; sniffed per open, EOL live per keystroke |
| Smarter error explainer | `app.py::extract_error_block` | Terminal `explain` now understands pytest `FAILED …::test` summaries and unittest `FAIL: test_x` headers (with assert context), guarded against ordinary "Failed to …" lines |

## Making & Testing (v2.8.0)

| Feature | Where | What it does |
|---|---|---|
| Data generator | `gen.py`, palette, terminal `gen` | Fills your clipboard with dev fuel: proper RFC 4122 UUID v4, spec-length ULIDs (26-char Crockford, newest first), nanoids, 32-char hex tokens, 20-char passwords with guaranteed class coverage (secrets module everywhere), PINs, lorem paragraphs, and fake users / fake events as ready-to-paste JSON |

## Scheduling & Prose (v2.8.0)

| Feature | Where | What it does |
|---|---|---|
| JWT decoder | `jwt.py`, palette, terminal `jwt <token>` | Paste a token, see header + payload pretty-printed, every time claim humanized ("expires in 1h 59m" / "expired 3d ago"), claims table with iss/sub/aud/jti pulled to the front — decode only, and it says so |
| .env lint & mask | `envcheck.py`, palette, terminal `env` | Lints the workspace `.env`: duplicate keys, invalid key characters, spaces around `=`, unquoted spaces, ` # ` comments silently lost, unclosed quotes, empty values — then produces a masked copy (secret keys starred, `postgres://user:***@host` URLs) safe to paste into an issue |

| Feature | Where | What it does |
|---|---|---|
| Cron decoder ring | `cronexp.py`, palette, terminal `cron <expr>` | Any cron string becomes a plain-English sentence ("at 09:00, on MON"), a field-by-field table (names, steps, ranges, lists, 7==Sunday, `@hourly`…`@reboot` shorthands) and the next five run times — computed by a built-in minute-stepper with month fast-forward, no cron daemon needed |
| Readability report | `readability.py`, palette, terminal `readability` | Flesch Reading Ease with a human verdict, Flesch–Kincaid grade, Gunning Fog, complex-word %, sentences-over-25-words list and a word-pressure table (stopwords filtered); one click copies the report as markdown |
| Terminal help refresh | terminal `help` | The studio command list now covers `tools`, `cron`, `readability` and `explain` |

## The Pocket Knife (v2.7.0)

| Feature | Where | What it does |
|---|---|---|
| Developer tools window | `devtools.py`, Help → *Developer Tools…*, palette, terminal `tools` | Four tabs of everyday ammunition: regex, JSON, text and time — all engines pure and unit-tested, all state defensive |
| Regex tester | Dev tools → *Regex* | Live match list with spans, capture groups and named-group hints; ignore-case / multiline / dotall toggles; replace-with preview; copy-all-rows; 500-match cap keeps the UI honest |
| JSON workshop | Dev tools → *JSON* | Pretty (2/4), minify, validate, sort keys — errors report the exact `line X, col Y` of the offending byte |
| Text transformer | Dev tools → *Text* | `snake_case`, `camelCase`, `PascalCase`, `kebab-case`, `CONST_CASE`, Title Case (understands `HTTPServer2`); base64 and URL encode/decode; `\u`/`\U` escape round-trips incl. astral plane; MD5/SHA-1/SHA-256; word/char/line counts; *↑ use output as input* chains transforms |
| Time converter | Dev tools → *Time* | Ticking ISO clock (local or UTC), epoch ↔ ISO both directions, `Z`-suffix and naive-timestamp handling, relative labels (`3h ago`, `in 2d`) |
| Color lab | Dev tools → *Color* | hex ↔ rgb ↔ hsl live conversion with swatch, WCAG contrast ratio + AA/AAA grade against any second color, eight harmony swatches (complement, analogous, triadic, lighter/darker) — click one to copy its hex |
| Terminal shortcuts | terminal `tools` / `devtools` / `regex` | Opens the window; `regex` seeds the pattern from the current editor selection |

## The SQLite Lab (v2.9.0)

| Feature | Where | What it does |
|---|---|---|
| Database browser | `sqlitelab.py`, Workshop → *SQLite Browser…*, palette, terminal `db` / `db <file>` | Point it at any `.db` / `.sqlite` file (auto-discovers them in the workspace) and get tables, views, row counts, schema, live queries and exports in one window |
| Read-only by default | SQLite Lab toolbar | Opens via SQLite URI `mode=ro` so browsing can never corrupt your data; flip the top-right toggle for a read-write session when you really mean it |
| Tables sidebar | SQLite Lab left pane | Tables and views with live row counts; double-click to browse rows, single-click loads the schema tab |
| Browse grid | *Browse* tab | Sample rows (50–5000 limit spinner) with long cells truncated and BLOBs summarized (`<2 bytes>`); export to CSV or copy as a GitHub-flavored markdown table |
| Schema dive | *Schema* tab | Every column with type / null / default / pk flags, plus the index list with columns and unique/pk origin flags |
| Query bench | *Query* tab, F5 | One statement at a time — SELECT fills a grid (capped at 500 rows), writes report affected counts and refresh the sidebar; errors land in the status line, never a crash |
| DB intel | *Info* tab | SQLite version, file size from page math, page/freelist counts, journal mode, encoding, table/view census |
| Pure engine | `tests/test_ds2.py` | connect / introspection / sample / query / export / markdown / finder all unit-tested — writes blocked read-only, affected counts correct, quoting safe (`qident`), markdown pipes escaped |

## The Tree Export (v2.9.0)

| Feature | Where | What it does |
|---|---|---|
| Directory tree export | `treeexport.py`, Workshop → *Directory Tree Export…*, palette, terminal `tree` / `tree <dir>` | Turns any folder into a README-ready ASCII tree — `├──`/`└──` connectors, directories first, one-click copy to clipboard or save as .txt/.md |
| Junk-aware skipping | engine (shared skip set) | `.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, `build` and friends never pollute your tree — the skipped count shows in the stats line |
| Depth & size controls | toolbar | Depth spinner (1–6), hidden-files toggle, per-file human sizes (`2.0 KB`) — the tree regenerates live on every toggle (or press F5) |
| Honest stats | status bar | `N dirs · M files · size`, skipped-junk count, and a visible *truncated* flag when the entry cap kicks in — no silent lies |
| Pure engine | `tests/test_ds2.py` | skip rules, dir-first sorting, depth caps, hidden toggle, size math and invalid-root safety are all unit-tested |

## The Hasher (v2.10.0)

| Feature | Where | What it does |
|---|---|---|
| Checksum lab | `hasher.py`, Workshop → *Hasher — checksums…*, palette, terminal `hash` / `hash <file>` | Hash any file or folder with MD5 / SHA-1 / SHA-256 / SHA-512 — results in a grid with digest, size and path |
| Chunked engine | `hash_file` / `hash_bytes` | 1 MiB chunks — a 4 GB file never loads into memory; pure stdlib, raises only real OS/algorithm errors |
| Folder manifests | `hash_dir` + *Copy/Save manifest* | Recursive, hidden-file-aware (toggleable via engine kwargs), sorted, `sha256sum -c`-compatible lines (`<digest>␣␣<relpath>`, 5000-file cap) |
| Paste-a-hash verify | right panel | Paste an expected digest → instant MATCH / MISMATCH verdict; paste a whole manifest → *Verify ALL* reports `N ok · M MISMATCH · K not in pasted manifest` |
| Tests | `tests/test_ds2.py` | Digest correctness against `hashlib`, folder walk order, manifest round-trip, malformed/comment/binary-marker line parsing |

## The Focus Timer (v2.11.0)

| Feature | Where | What it does |
|---|---|---|
| Pomodoro window | `focus.py`, Workshop → *Focus Timer…*, palette, terminal `focus` / `focus 50` | A 25/5 focus timer that lives inside the IDE — big clock, phase label, session dots, start/pause/reset/skip |
| Deterministic engine | `FocusEngine.tick()` | State machine with whole-second ticks — work → short break → … → long break every 4th block; transitions fire the second a phase hits zero (unit-tested tick-by-tick, no wall-clock flakiness) |
| Custom blocks | `focus 50` | Any minute count ≥ 1 replaces the 25-minute work block; break lengths scale from the engine defaults |
| Session feedback | window log line | Finished blocks count up ("stretch, drink water"); a completed set of 4 announces the long break |
| Tests | `tests/test_ds2.py` | Phase roll-overs, long-break cadence, paused-tick no-ops, skip semantics, reset, `fmt_mmss` edge cases |

## Line Tools (v2.12.0)

| Feature | Where | What it does |
|---|---|---|
| Sort / dedupe / shuffle / reverse / trim | Edit menu → *Line Tools*, palette, terminal `sort <mode>` | Seven transforms on the selected lines (or the whole file when nothing is selected): A→Z, Z→A, shortest-first, dedupe (case/whitespace-insensitive, keeps first), seeded shuffle, reverse, trailing-whitespace trim |
| Keyboard | Ctrl+Alt+S / D / H / R | Sort, dedupe, shuffle, reverse without touching the mouse |
| Trailing-newline honesty | engine | A file ending in `\n` never grows a sortable phantom empty line — the terminator shape is preserved byte-for-byte |
| Range discipline | engine | Text outside the selection is preserved exactly; dedupe/shuffle only ever touch the requested block |
| Pure engine | `tests/test_ds2.py` | Deterministic with an injected RNG, clamps hostile ranges, never raises on non-text input |

## Clipboard History (v2.13.0)

| Feature | Where | What it does |
|---|---|---|
| Clipboard memory | `clipboard.py`, Edit menu → *Paste from History…*, palette, terminal `clip`, **Ctrl+Shift+V** | A background poller (1.5 s, never raises) watches the system clipboard and keeps the last 25 distinct entries in a bounded ring — copies made anywhere on your desktop show up in the studio |
| Paste-back window | double-click / Enter | Pastes the chosen entry at the editor cursor (marks the buffer dirty properly); with no editor focus it copies the entry back to the clipboard |
| Smart dedupe | `ClipRing` engine | Re-copying an older entry moves it to the top instead of duplicating it; identical consecutive copies are ignored; empty/whitespace and non-string payloads never enter the ring |
| One-line previews | list rows | Whitespace collapsed, 90-char cap with an ellipsis — multi-line snippets stay scannable |
| Pure engine | `tests/test_ds2.py` | Ring bounds, eviction order, repeat-to-front, junk rejection, size coercion and preview truncation are all unit-tested |

## Markdown Preview (v2.14.0)

| Feature | Where | What it does |
|---|---|---|
| Dual-pane window | `markprev.py`, Workshop → *Markdown Preview…*, palette, terminal `md` / `preview` / `markdown` | Edit markdown on the left, see the rendered result on the right — opens pre-loaded with the current editor buffer |
| Zero-dependency renderer | `parse_blocks` + `inline_spans` | Headings `#`–`######`, **bold**, *italic*, ~~strikethrough~~, `` `inline code` ``, fenced code blocks with language label, blockquotes, ordered/unordered lists, pipe tables, links, horizontal rules — no packages, pure stdlib |
| Live re-render | debounced 300 ms on typing, F5 for instant | The preview follows your keystrokes; the status bar reports words, lines, blocks and render time in milliseconds |
| HTML export | *Copy HTML* / *Export HTML…* buttons | One click copies a full standalone HTML document (embedded CSS) or saves it next to your notes |
| Forgiving parser | engine, unit-tested | Unclosed fences, missing blank lines, snake_case text and empty input all degrade gracefully — the renderer never loses characters or raises |
| Tests | `tests/test_ds2.py` | Every block kind, inline style, table cells, paragraph folding, HTML escaping and hostile-input paths covered |

## Color Kit (v2.15.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Conversion workbench | `colorkit.py`, Workshop → *Color Kit — convert & contrast…*, palette, terminal `color` / `colorkit` | Paste any color (`#7c3aed`, `7c3aed`, `#abc`) and instantly see hex, `rgb()`, `hsl()` and a tkinter-ready form |
| WCAG contrast | contrast panel | Live contrast ratios against white and black with the AA 4.5:1 verdict and a "best partner" recommendation for text color |
| Shade ramps | click-to-copy chips | A deterministic 9-step light→dark ramp through your color — every chip copies its hex to the clipboard |
| Pure engine | `tests/test_ds2.py` | normalize/hex↔rgb↔hsl round-trips, 0-255 clamping, WCAG luminance math, mix/lighten/darken monotonicity and junk-input safety all unit-tested |

## REST Bench (v2.15.0 lane)

| Feature | Where | What it does |
|---|---|---|
| HTTP workbench | `restbench.py`, Workshop → *REST Bench — fire HTTP requests…*, palette, terminal `rest` / `http` / `restbench` | Pick a method (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS), edit URL, headers and body, hit Send (or Ctrl+Enter) without leaving the studio |
| Zero-dependency engine | `http_request()` on `urllib.request` | Status, reason, headers, body, elapsed ms and byte size come back in one `RestResponse`; network errors, bad schemes and timeouts become readable error responses instead of crashes |
| Response viewer | response pane | Response headers in muted ink, JSON bodies auto-pretty-printed, status line always visible; a 30-entry history ring remembers recent exchanges |
| Copy as curl | toolbar button | Any request converts to a copy-pasteable `curl` command with proper shell quoting (apostrophes included) |
| Offline-testable | `tests/test_ds2.py` | The suite runs against a local `http.server` (round-trip POST with headers + body, GET, connection-refused path) plus opener injection — zero external network |

## Window Geometry Memory (v2.15.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Per-screen memory | `geom.py`, config key `window_geometry_by_screen` | Every screen shape (`1920x1080`, `2560x1440`, …) gets its own remembered window geometry — dock at the 4K monitor, undock on the laptop panel, and the studio opens right-sized for whichever display it finds |
| Restore on boot | app boot, defensive | The saved geometry for the current screen replaces the default `1280x820` at startup; nothing stored → boot is unchanged |
| Save on close | `_on_close`, defensive | The live window position/size is snapshotted before exit; maximized/fullscreen states are skipped (they are window-manager states, not geometry) |
| Clamp safety | `clamp_geometry` | Restored windows can never open off-screen or bigger than the display — a geometry left over from a since-disconnected monitor is pulled back inside the visible area |
| LRU store | `remember()` | At most 8 screen shapes are kept (oldest evicted); re-remembering a shape moves it instead of duplicating; stored junk is ignored on recall |
| Tests | `tests/test_ds2.py` | Parse/make round-trips (including negative offsets), clamping edge cases, LRU cap, signature isolation and junk-recall safety |

## Scribe Mini Chip (v2.16.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Statusbar writing meter | `scribe.py` + statusbar right side, terminal `scribe` / `scribe 750` | A compact `✎ 1,234 w · 27 wpm · 45%` chip tracks the live word count, trailing words-per-minute and progress toward a session word goal — zen mode has the full card, the main editor now has the mini version |
| Throttled observation | `ScribeChip.observe()` | Word counts are sampled at most every 2 s at the app layer and 2 s inside the engine, so even huge buffers never make typing laggy; paste spikes are capped like zen's tracker |
| Session toast | click the chip | A toast summarizes the session: words, current WPM, peak WPM, elapsed minutes and goal percentage |
| Goal control | terminal `scribe 750` / `scribe 0` | Sets the words-per-session goal (persisted in config); 0 hides the percentage part; `scribe` alone prints the current session stats |
| Pure engine | `tests/test_ds2.py` | Throttle timing, change detection, goal hiding, junk rejection, paste-spike cap and reset-keeps-goal semantics are unit-tested with deterministic clocks |

## Filestats Scan History (v2.16.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Growth history | `filestats.py` engine, `.dxn1/filestats_history.json` per workspace | Every File statistics scan records a timestamped snapshot (files + bytes); identical shapes refresh the newest point instead of stacking, and the store keeps the last 60 snapshots |
| Sparkline strip | trend label under the summary cards | A `▁▂▃▄▅▆▇█` trend line of the last 40 scans renders above the type chart, with a `+12 files · +340 KB bytes vs previous scan` delta line — see your project grow at a glance |
| Deterministic renderer | `sparkline()` / `delta_line()` | Junk input renders empty, all-equal series render mid blocks, over-long series bucket-compress (chunk max) — pure functions, fully unit-tested |
| Forgiving store | `load_history()` / `append_history()` | Missing or corrupt history files rebuild silently on the next scan; persistence failures never break the stats window |
| Tests | `tests/test_ds2.py` | Round-trips, dedupe, cap, first-scan/growth/shrink delta lines and corrupt-store recovery all covered with temp workspaces |

## Chart Studio (v2.17.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Paste-to-chart | `charts.py`, Workshop → *Chart Studio — paste numbers, see them…*, palette, terminal `chart` / `charts` / `plot` | Paste logs, CSV columns, test timings or build sizes — any text containing numbers becomes a live chart, no external plotting library |
| Four views | line / bar / histogram radiobuttons + a unicode sparkline strip | Line charts draw connected points, bar charts scale rectangles relative to the max, histograms bin the distribution (constant series get one honest bin), and the sparkline compresses long series into bucket means |
| Stats panel | count / min / max / mean / median / stdev / range / sum | Recomputed on every keystroke (300 ms debounce), one click copies the whole summary to the clipboard |
| Junk-tolerant parser | `parse_series()` | Splits on spaces/commas/semicolons/pipes, understands `12ms`, `5px`, `8%` suffixes and scientific notation, skips garbage tokens silently — a text box of nonsense renders a friendly "no numbers yet" instead of crashing |
| Pure geometry | `scale_points()` / `bar_rects()` | Flat series draw a mid-height line, single points center, negative values hang below the zero line; pads respected; every function unit-tested including junk dimensions |

## Unit Converter (v2.17.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Six categories | `unitconv.py`, Workshop → *Unit Converter — length/mass/data…*, palette, terminal `unit` / `units` / `convert` | Length, mass, temperature, data size, duration and speed — pick a category, type a value, read every unit converted at once |
| Exact factors | mm→mi, kg→lb, MB→MiB, min→h, km/h→mph | Conversion tables carry full precision (international foot, avoirdupois pound, binary KiB/MiB/GiB family); temperature uses real C/F/K formulas instead of offsets |
| All-units panel | list under the live result | Every unit in the category shown with the current value; the source unit is marked; one click copies the headline result |
| Junk honesty | `convert()` returns `None`, UI shows `—` | Garbage input, unknown units and booleans are rejected politely; the status bar asks for a number instead of lying with a zero |
| Offline | no network, no dependencies | Pure engine, fully unit-tested (factors, temperature formulas, junk tolerance, batch tables) |

## Language Switcher (v2.17.0 — i18n activation)

| Feature | Where | What it does |
|---|---|---|
| `lang` terminal command | terminal, persisted via config `language` key | `lang` lists available packs and the current one; `lang es` / `lang zh` / `lang ja` activates a pack — eight ship built-in (en es fr de pt zh hi ja) and any file dropped in `~/.dxn1-studio/lang/<code>.json` joins the list automatically |
| Boot persistence | `i18n.boot_from_config()` at studio start | The remembered language is honoured on every launch, so the choice survives restarts |
| Translation template | `i18n.export_template(dest, code)` | Community packs start from a complete JSON template — honest groundwork for the tr() plumbing that now has a switchable substrate |

## Character Map (v2.18.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Glyph browser | `charmap.py`, Workshop → *Character Map — browse & copy Unicode…*, palette, terminal `charmap` / `char` / `unicode` | 25 curated offline blocks — Arrows, Math Operators, Box Drawing, Block Elements, Geometric Shapes, Currency, Braille, Hiragana, Katakana, CJK samples, Fullwidth Forms and more — rendered in a click-to-copy glyph grid |
| Three-way search | type in the search box | Matches block names (`box`), hex codepoints (`U+2192`, `0x00e9`, `2192`) or any literal character you paste; a failed search says so honestly instead of silently falling back |
| Click-to-copy | clicking a glyph | Copies the character and prints `U+00E9 · é · LATIN SMALL LETTER E WITH ACUTE` (unnamed glyphs handled); *copy all shown* grabs the whole grid for pasting into an editor |
| Pure engine | `block_names()` / `chars_in()` / `search()` / `describe()` | Junk-tolerant, bounded, fully unit-tested; the window never raises |

## TextCase (v2.19.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Identifier converter | `textcase.py`, Workshop → *TextCase — snake/camel/kebab/… converter*, palette, terminal `case` / `textcase` | Type any identifier in any convention and read all eight styles live: snake_case, camelCase, PascalCase, kebab-case, CONSTANT_CASE, Title Case, dot.case, flatcase — click any row to copy |
| Acronym-aware splitter | `words()` | `getHTTPResponse_2` splits to get/HTTP/Response/2 — acronym runs stay whole, digits stay attached to their word, snake/kebab/dot/space delimiters all respected |
| Junk-tolerant | `convert()` / `all_cases()` | Non-strings and delimiters-only input convert to empty; unknown style names return empty instead of raising; camel→snake round-trips are stable |
| Live rows | eight labelled rows with click-to-copy | Paste button reads the clipboard; every conversion updates on each keystroke |

## i18n tr() Deepening (v2.19.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Six new UI keys | `i18n.py`, full translations in all eight packs | `markprev.copy_html` / `markprev.export_html` / `chart.copy_stats` / `unit.copy_result` / `textcase.click_copy` / `charmap.click_copy` — every pack now carries 68 keys |
| Translated buttons | markprev, charts, unitconv, textcase, charmap | The newest windows' copy/export buttons and hints resolve through the active language pack; `lang es` visibly re-speaks them |

## PassForge (v2.20.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Password generator | `pwdgen.py`, Workshop → *PassForge — strong passwords + entropy…*, palette, terminal `passgen` / `password` / `passforge` | Lengths 4–128 from toggled classes (A-Z, a-z, 0-9, symbols) with an optional "no `Il1O0o`" ambiguous-glyph filter |
| Real CSPRNG | stdlib `secrets.choice` | No home-made randomness anywhere; tests stay deterministic by injecting a seeded rng into `generate()` |
| Entropy meter | `entropy_bits()` / `strength_label()` | Shannon entropy `length · log2(pool)` with an honest ladder: weak < 28 ≤ fair < 36 ≤ strong < 60 ≤ excellent < 128 ≤ overkill; empty pools and junk input read zero instead of lying |
| Junk-tolerant | every engine entry | Non-integer lengths, zero/negative lengths, disabled pools all return empty strings; the window asks for options instead of crashing |

## NumBase (v2.21.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Number base workbench | `numbase.py`, Workshop → *NumBase — bin/oct/dec/hex + bases 2-36…*, palette, terminal `base` / `numbase` / `hex` | Type a value in any base 2–36 and read it simultaneously as binary, octal, decimal, hex plus 11 more bases — click any row to copy |
| Parser | `parse_number()` | Accepts +/- signs, `_` digit separators and the classic 0x/0o/0b prefixes (which override the chosen base); junk digits, empty prefixes and out-of-range bases return None instead of guessing |
| Bit inspector | `inspect_bits()` | Bit length, popcount, big-endian hex bytes and a two's-complement note for negative values |
| Round-trip proof | `tests/test_ds2.py` | Formatting then re-parsing 255 round-trips for every base 2..36 |

## CSV Lab

| Feature | Where | What it does |
|---|---|---|
| Table peeker | `csvkit.py`, Workshop → *CSV Lab — paste & peek tables…*, palette, terminal `csv` / `csvlab` / `tsv` | Paste CSV/TSV/semicolon/pipe data and the table renders instantly in a ttk treeview; the header row becomes column headings |
| Delimiter sniffing | `sniff_delimiter()` | Auto-detects `,` `;` `\t` `|` from the sample; an "auto" radio plus explicit picks override it |
| Honest parsing | `parse_csv()` / `table_stats()` | Stdlib csv parser (quoted fields with embedded delimiters work), blank rows skipped, ragged-width tables flagged; junk renders an empty grid instead of crashing |
| TSV export | one click | The grid copies back out as tab-separated text — paste straight into a spreadsheet |

## MathPad

| Feature | Where | What it does |
|---|---|---|
| Safe evaluator | `mathpad.py`, Workshop → *MathPad — safe expression calculator…*, palette, terminal `calc` / `math` / `mathpad` | Expressions run through Python's `ast` with a strict whitelist — no `eval`, no attribute access, no imports; pasted junk can only produce an error message, never side effects |
| Operators | everywhere | `+ - * / // % **` plus `^` accepted as power, unary minus, parentheses; `0xff`, `0b101` and `1_000` literals parse for free |
| 26 functions | function chips + typing | `sqrt cbrt abs round floor ceil trunc exp log log2 log10 sin cos tan asin acos atan atan2 sinh cosh tanh degrees radians gcd hypot min max factorial sign`; chips insert the common ones in one click |
| Constants | `pi e tau inf` | Available by name in every expression |
| Variables | `x = 5` then `x*3` | Assignments are stored in the session scope; `_` and `ans` always hold the last answer |
| Hard limits | engine | Exponents capped at 10,000, factorials at 10,000!, complex results rejected, division-by-zero reported honestly — no hangs, no crashes |
| Human output | `fmt()` | Integers stay integers, floats are trimmed to 12 significant digits (`0.1+0.2` reads `0.3`), huge values switch to scientific notation |
| History | click-to-copy | Every evaluation lands in a 200-row history list; clicking a row copies its answer |
| i18n | `math.*` keys | Copy button and history hint translate across all 8 language packs |

## ByteSnoop

| Feature | Where | What it does |
|---|---|---|
| Hexdump renderer | `hexdump.py`, Workshop → *ByteSnoop — hexdump & byte inspector…*, palette, terminal `hexdump` / `bytes` / `bytesnoop` | Classic 16-bytes-per-row dump with `00000000`-style offsets, a fixed-width hex column and an aligned ASCII gutter; non-printables render as dots |
| Hex input | text / hex radio | Flip the source to hex and paste `41 42 43`, `41:42:43`, `0x41`, comma/newline separated or xxd-style offset columns — all tolerated |
| Honest parsing | `from_hex()` | Odd digit counts or zero hex digits refuse to parse with a clear status message instead of guessing |
| Byte stats | `byte_stats()` / `stats_line()` | Live line with total bytes, unique values, printable % and high-bit % — updates as you type |
| Copy | one click | The whole dump copies back out as text |
| i18n | `hex.*` keys | Copy button and row label translate across all 8 language packs |

## Paste Diff

| Feature | Where | What it does |
|---|---|---|
| Two-paste compare | `textdiff.py`, Workshop → *Paste Diff — compare two texts…*, palette, terminal `diff2` / `pastediff` / `textdiff` | Paste the original and the revised side by side; the diff updates as you type |
| Word & char modes | `inline_diff()` | Edits are marked inline with the greppable rdiff convention — `[-deletion-]` and `{+insertion+}` — so single-letter edits and reworded spans both stand out |
| Line mode | `diff_lines()` | Classic `- / +` rows derived from difflib opcodes (same/delete/insert/replace) |
| Similarity meter | `similarity()` / `summary()` | Live `+N -M lines · P% similar` status computed from the same opcodes |
| Copy | one click | The rendered diff copies back out as plain text |
| i18n | `diff.*` keys | Copy button and empty-state hint translate across all 8 language packs |

## Markup Bench

| Feature | Where | What it does |
|---|---|---|
| XML workbench | `xmlbench.py`, Workshop → *Markup Bench — pretty & inspect XML…*, palette, terminal `xml` / `markup` / `xmlbench` | Paste XML, pretty-print or minify it, with live validation and stats as you type |
| Pretty printer | `xml_pretty()` | Re-indents with 2–8 spaces; returns honest `line X, column Y` errors for malformed input |
| Minifier | `xml_minify()` | Drops inter-element whitespace while preserving real text nodes |
| Element census | `tag_stats()` / `stats_line()` | Total elements, unique tags, top-3 tag counts, max depth, attribute total |
| Safety guards | engine | 512 KB input cap, 200-level depth cap, DTD entities refused outright — hostile XML is declined, never executed |
| i18n | `xml.*` keys | Copy button and empty-state hint translate across all 8 language packs |

## Contrast Auditor

| Feature | Where | What it does |
|---|---|---|
| WCAG theme audit | `contrast.py`, Workshop → *Contrast Auditor — WCAG grades for themes…*, palette, terminal `contrast` / `a11y` / `wcag` / `audit` | Grades 13 semantic text pairs (body/sidebar/header/card/terminal/statusbar, secondary, muted, gutter, selection-on-accent, success, overlay) for every theme the studio can wear |
| Grading | `grade()` / `fmt_ratio()` | AAA ≥ 7:1, AA ≥ 4.5:1, AA-L ≥ 3:1, FAIL below — human ratios like `21:1` and `4.53:1` |
| Auto-fix suggestions | `suggest_fg()` | Below AA, searches lighten/darken steps until the foreground clears 4.5:1 against its background; honest `—` when unfixable |
| Theme inventory | `iter_auditable_themes()` | Built-in Dark + Light, all 12 community gallery themes, and user-saved themes — junk themes audit to honest FAIL rows, never crash |
| Copyable report | `report_text()` | Plain-text audit (pair, ratio, grade, fix) for issue reports and theme reviews |

## Cheat Sheet

| Feature | Where | What it does |
|---|---|---|
| Printable export | `cheatsheet.py`, Workshop → *Cheat Sheet — printable HTML export…*, palette, terminal `cheat` / `cheatsheet` / `man` | One standalone HTML page with every terminal command and keyboard shortcut, inline CSS, `@media print` rules — save it, open in any browser, Ctrl+P |
| Zero drift | `TERMINAL_HELP` / `default_sections()` | The command list is the same tuple the terminal's `help` prints (extracted to module level this release), so new features appear on the sheet automatically |
| Preview + actions | window | Plain-text preview of the full sheet; save HTML anywhere, open in browser instantly (temp file fallback), copy HTML to clipboard |
| Honest saves | `save_html()` | Empty paths, directories, and missing folders return real error strings — the window reports them, never crashes |

## Colorblind Lab

| Feature | Where | What it does |
|---|---|---|
| CVD preview | `cvdlab.py`, Workshop → *Colorblind Lab — CVD preview of themes…*, palette, terminal `cvd` / `colorblind` / `vision` | Renders the active theme's swatches the way color-blind users see them: deuteranopia, protanopia, tritanopia, achromatopsia |
| Severity blend | `simulate_hex(hex, kind, severity)` | 0–100% slider blends original vs simulated for design tuning; severity 0 is identity |
| Contrast under CVD | `sim_summary()` / `survive_line()` | Re-runs the Contrast Auditor on the simulated palette — a live "CVD view: 13 pairs · 13 pass · 0 fail" verdict |
| Custom hex | window | Type any hex, see it simulated instantly, copy the result |
| Honest engine | engine | sRGB-space approximation (design review, not clinical); junk hex returns None; Theme wrapper and plain dicts both accepted |

## Fuzzy Launcher Scoring

| Feature | Where | What it does |
|---|---|---|
| Fuzzy palette | `fuzzy.py`, Command Palette (Ctrl+K) | Commands rank by relevance, not substring luck: word-boundary starts (+8), camel humps (+5), contiguous runs (+4), prefix anchor (+6); gaps cost −1. `qpn` finds "Quick open a file" |
| Fuzzy symbols | palette `@` mode | Jump-to-symbol tolerates gaps: `@gmmthre` finds `gamma_three` |
| Fuzzy Quick Open | `path_score()` | Subsequence match over paths with a +3 basename boost — files beat folders; deterministic tie-break keeps short paths first |
| Never crashes | engine | `None` never matches, non-strings coerce via `str()`, broken key functions fall back to `str(item)`; empty queries preserve the original order; legacy substring filter stays as fallback |

## Dependency Cross-Check

| Feature | Where | What it does |
|---|---|---|
| `deps` verb | terminal `deps`, palette *Dependency Check — imports vs requirements…* | Cross-checks the workspace's imports against `requirements*.txt` (and `pyproject.toml [project] dependencies`): reports **imported but never required** and **required but never imported**, with a one-line summary first |
| Static scanner | `depcheck.scan_imports()` | AST walk over every `*.py` (junk dirs skipped, unreadable files skipped silently) collecting top-level import names — as-imports, from-imports, dotted roots; relative imports count as local |
| Honest classification | `depcheck.classify()` | Splits names into stdlib (via `sys.stdlib_module_names`), local (root `*.py` stems + packages with `__init__.py`) and third-party — only the third bucket can be missing |
| Requirements parsing | `depcheck.read_requirements()` | Pins, extras, inline comments, `-r`/`-e`/`--hash` plumbing, `name @ URL` and VCS lines (`git+…`) handled; PEP 503 canonical names out |
| Famous alias table | `depcheck.ALIASES` | Pillow→PIL, beautifulsoup4→bs4, PyYAML→yaml, scikit-learn→sklearn, python-dotenv→dotenv and ~25 more pairs so `PyYAML` satisfies `import yaml` |
| Honest caveats | `depcheck.check()` | No requirements file → a notice instead of an error; unknown dist↔import pairs can false-positive, and the report says exactly that |

## Session Restore

| Feature | Where | What it does |
|---|---|---|
| Close-hook snapshot | `session.py`, app close | Every close saves open tabs, the active file and the cursor position (line + column) to `~/.dxn1-studio/sessions/<workspace-hash>.json` — atomic write, up to 50 tabs |
| Crash-safe autosave | app `_autosave_session()` | While you work, the same snapshot is silently rewritten every 60 s (Settings ▸ *Autosave the session*; interval clamped 15–600 s) — a crash, kill or battery death now costs at most a minute of workspace state instead of everything since the last clean exit |
| Crash recovery | app `_restore_engine_session()` | Open a workspace with no clean-exit record (i.e. after a crash) and the last autosaved snapshot becomes the recovery point: tabs reopen, the active file refocuses at its saved cursor spot, and every other buffer keeps its position for the tab switch |
| Engine-first boot | app `_restore_session_tabs()` | Reopening a workspace tries the engine snapshot BEFORE the legacy clean-exit record — the snapshot is refreshed by every close and by the 60s autosave, so a crash costs one minute of tabs instead of resurrecting a week-old `session_tabs` entry; the legacy record remains the fallback for pre-v2.30 installs |
| Save session now | palette, terminal `session save` / `ssave`, statusbar chip click | Snapshot on demand with visible feedback: the statusbar chip paints `◐ session saved HH:MM` in the accent colour for a moment, then fades back to muted — and a toast explains when no workspace is open |
| Session manager | Workshop → *Session Restore — pick up where you left off…*, palette, terminal `session` / `sessions` / `resume` | Browse every saved workspace (tabs count + saved time), preview its files with the active one marked, restore with one click — files reopen and the cursor jumps back to its line |
| Cursor memory | `snapshot()` / `restore_plan()` | `{path: (line, col)}` per session; only the position is restored that files still exist — ghost files are filtered, never error |
| Durable store | engine | Corrupt JSON reads back as empty; save returns honest `(ok, error)`; up to 40 sessions kept, newest first; `base=` override makes the whole store testable |

## Delta Updates

| Feature | Where | What it does |
|---|---|---|
| HASHES.txt | repo root, `scripts/gen_hashes.py` | sha256 (sha256sum format) of all 94 shipped files — 83 modules, entry scripts, README, MANIFEST and the six art assets; CI-tested to stay in sync, regenerating is one command |
| Delta update | `updater._remote_hashes()` + delta pass | The update portal fetches HASHES.txt first, hashes the local install and streams **only the files that actually changed or are missing** — a one-module fix no longer re-downloads the whole IDE; unchanged files are skipped byte-identical |
| Honest fallback | `perform_update()` | HASHES.txt unreachable → the classic full download runs exactly as before; the delta pass is an optimization, never a correctness risk |
| Installer integrity gate | `install.sh` | After downloading all modules the installer verifies every sha256 against HASHES.txt — a truncated or corrupted download fails the install with a clear message instead of shipping a broken IDE |
| Workshop shortcut | Workshop ▸ *Save Session Now — snapshot tabs + cursors* | The session snapshot joins the menu bar next to Session Restore (palette, terminal and statusbar chip were already there) |
| Skip this version | portal decline → `updater_skip_version` | "I'll stay on this version" remembers the exact release: the automatic boot check goes quiet for it (a one-line terminal note points to `update`), manual checks always open the portal, and any newer release nags again |
| Atomic config saves | `Config.save()` | Preferences write to a temp file and `os.replace` into place — a crash mid-save can no longer tear config.json (which also silently destroyed the session records crash recovery depends on) |
