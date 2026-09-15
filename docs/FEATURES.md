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
| Self-healing pins | terminal `deps fix`, `depcheck.fix_requirements()` | Missing imports become canonical pins appended atomically to `requirements*.txt` (`# added by deps on <date>`) — the reverse alias table picks the distribution (`yaml` → `pyyaml`, `PIL` → `pillow`); deduped against existing lines, creates the file on demand, second run is a no-op |
| Per-workspace cache | terminal `deps`, `deps fresh`, `depcheck.check_cached()` | Repeat reports are instant: the verdict is stored in `<ws>/.dxn1/depcheck_cache.json` with a change-sensitive fingerprint (every scanned file's mtime + size, plus the root listing); any edit invalidates honestly, a corrupt cache falls back to a real scan, the cache's own `.dxn1` write never self-invalidates, and `deps fix` always works from a fresh scan |
| Per-verb help | terminal `help <verb>`, `matching_help_rows()` | Exact command match, then substring over commands/descriptions, then the three closest fuzzy hits — `help dps` finds `deps`; unknown verbs get an honest "No help for" line |
| Palette help fallback | terminal `help <query>`, `palette_help_rows()` | When no terminal row matches, `help` searches the palette's own command registry — `help duplicate` finds *Duplicate line — Ctrl+Shift+D*; the Ctrl+K vocabulary is discoverable without opening the palette |
| Dependency watch chip | statusbar, `depcheck.cache_state()` | A quiet `deps ok` sits in the statusbar and turns **amber — `● deps drift`** the moment the workspace fingerprint moves past the last deps report (a saved file, a file added outside the studio, a requirements edit). v2.40 severity: a cached report whose imports are missing from requirements lights the chip **red — `● deps N missing`** — drift (amber) asks for a rescan, missing imports (red) ask for `deps fix`. The probe is cheap (no scan — signature compare only, throttled to one pass per 3 s) and a 30 s poll catches silent drift. Click the chip to rescan; `deps —` means never scanned here |
| Watch toggle | terminal `deps watch [on|off]`, palette *Dependency watch on/off…* | Bare `deps watch` flips the statusbar drift chip on/off (default on, persisted as `deps_watch`); junk arguments get an honest usage line explaining both severities; `deps fix` / `deps fresh` keep working exactly as before |
| One-gesture repair | statusbar chip click, app `_deps_chip_click()` | Clicking the chip while it is RED rescans *and* queues `deps fix` in the terminal input (Enter runs it — nothing fires by accident); the amber click stays a plain rescan |
| Deps context menu | right-click the deps chip, app `_deps_menu_entries()` | The lane's actions in one themed menu: Rescan deps, **Queue deps fix** (only when the chip is actually red — same one-gesture contract, Enter still runs it), Fresh rescan (bypass cache), Deps watch on/off, Rescan chip |
| Fix heals its cache | terminal `deps fix`, app `_run_depcheck(fix=True)` | After pinning, the workspace is re-scanned and re-stored immediately — the cache and the chip never lie about a workspace the studio just fixed; a pin that doesn't satisfy its import is called out honestly |
| Commands listing | terminal `commands [filter]`, app `_list_palette_commands()` | Every palette command (109+) listed in the terminal with its shortcut; a filter tail narrows by substring then fuzzy (`commands line`, `commands sve fil` → *Save file*), capped at 24 rows with an honest "+N more — narrow the filter" |

## Terminal Verbs Browser

| Feature | Where | What it does |
|---|---|---|
| Verbs window | Workshop → *Terminal Verbs…*, palette, terminal `verbs` / `verb`, `verbs.open_verbs()` | Every verb the terminal speaks (55+), browsable in one themed window: live search box (substring over verb + description, same first pass as `help <q>`), count label, scrollable rows, honest "nothing matches — try a shorter filter" |
| Click to prefill | `verbs.open_verbs(on_insert=…)`, app `_prefill_terminal()` | Clicking a row drops the verb into the terminal input and focuses it — Enter runs it, so nothing fires by accident; multi-line `help` rows are merged back into one complete description per verb |
| One data source | `verbs.verb_rows()` | Flattens the same `TERMINAL_HELP` tuple used by `help` and the cheat-sheet exporter (continuation lines folded into the previous row) — the terminal, the cheat sheet and the browser can never disagree about what the studio can do |

## Git Lane Chip (v2.40.0 lane)

| Feature | Where | What it does |
|---|---|---|
| Branch chip | statusbar, `gitpanel.repo_state()` | The branch name sits quietly in the statusbar in muted text while everything is committed and in sync — plain folders and non-repos stay silent (no nagging), as does a missing workspace |
| Uncommitted attention | `git status --porcelain -b` probe | Any uncommitted change (staged, unstaged or untracked) turns the chip **amber and bold — `branch ●N`** with the count of waiting files; arrows ride along when the branch also diverges (`branch ●2 ↑1`) |
| Divergence arrows | branch-line tracking summary | `↑N` / `↓K` show ahead/behind vs the locally-known upstream — honest by design: git only knows what it has fetched, so the chip never silently networks; behind shows after a fetch, ahead the moment you commit |
| One cheap probe | 3 s throttle + shared 30 s poll | One `git status` call max per 3 s (forced on saves, clicks and boot); the drift poll that watches deps now watches the git lane in the same pass — one timer, both lanes |
| Click opens Source Control | app `_git_chip_click()` | The chip points at work; the Source Control panel is where it gets done — click opens the panel and redraws the chip in one gesture |
| Watch toggle | terminal `git watch [on|off]`, palette *Source control watch on/off…* | Bare `git watch` flips the branch chip (default on, persisted as `git_watch`); junk gets an honest usage line; plain `git <args>` commands still pass through to the shell untouched (the intercept is prefix-exact) |
| Context menu | right-click the branch chip, app `_git_menu_entries()` | The lane's actions in one themed menu: Open Source Control, Commit graph, Stage all changes, **Commit staged…**, Draft AI commit message, Push to origin, Pull from upstream, Copy branch name (clipboard + toast), Rescan — repo rows appear only when a repository is watched, so a plain folder gets the honest two-row menu |
| Commit staged… | menu row, app `_commit_staged_from_chip()` + `gitpanel.focus_message()` | One row opens the Source Control panel and puts the cursor straight into the commit message box — stage, type, Enter; the panel guards repo state itself (the menu only opens the door) |
| AI commit draft | menu row, app `_ai_commit_from_chip()` | One row brings the Source Control panel forward and fires its ✨ AI helper — the diff is read, a Conventional Commits draft streams into the commit box, the user edits/commits as always (the panel guards repo and brain state itself) |
| Push / Pull rows | menu rows through the visible terminal runner | The two everyday git verbs join the menu, routed through `run_command` so output, errors and credentials stay exactly where they always are — the menu never shells out invisibly |
| Settings toggles | Settings ▸ *Statusbar watch chips*, `deps_watch` / `git_watch` | Both watch chips live in the Settings dialog beside their terminal verbs; saving persists and redraws both chips immediately |
| Chip tooltips | app `_chip_tip()` | Hover any statusbar chip (git, deps, session autosave, scribe) and a quiet themed tooltip explains what it is, what clicking it does and that a right-click opens its menu |
| One shared renderer | app `_render_chip_menu()` | Every statusbar chip menu (branch, deps, scribe, session autosave) is built by one themed popup renderer — `(label, command)` rows, `"---"` separators, cursor-anchored, best-effort by contract: a menu must never break typing |

## The Chip Family (v2.43.0)

| Feature | Where | What it does |
|---|---|---|
| Scribe chip menu | right-click the scribe chip, app `_scribe_menu_entries()` | The writing lane's actions in one themed menu: **Session summary** (the same toast the click gives), **Set writing goal…** (opens the themed goal dialog — see below), **Reset session meter** (words, wpm and the elapsed clock restart from now; the goal survives) |
| Scribe goal dialog | menu row → `scribe.open_goal_dialog()` | A themed dialog prefilled with the current goal: type the count, press Set or Enter — an explicit gesture commits it, nothing fires by accident. Invalid input gets an inline honest error ("whole numbers only") and the dialog stays open; Escape cancels without applying. Applying updates the chip, persists `scribe_goal_words`, and confirms with a toast + terminal line; the terminal verb `scribe <words>` keeps working exactly as before |
| Scribe meter reset | menu row, app `_scribe_reset_from_menu()` + `scribe.ScribeChip.reset()` | A fresh writing session without touching the goal — the chip repaints immediately and a toast confirms the reset |
| Autosave chip menu | right-click the session chip, app `_sesave_menu_entries()` | The session lane's actions in one themed menu: **Snapshot session now**, **Browse snapshots…** (the existing snapshot browser), a separator, **Autosave on/off** |
| Autosave toggle | menu row, app `_sesave_autosave_toggle()` | Flips `session_autosave` live — the 60s autosave loop reads the config every tick, so the switch lands on the next beat; a toast and a terminal line say which way it went |
| Family tooltips | app `_chip_tip()` | All four chips (git, deps, session autosave, scribe) advertise their menus on hover: what the chip is, what a click does, that a right-click opens the lane's actions |

## Hint Bars (v2.48.0)

| Feature | Where | What it does |
|---|---|---|
| Honest hint bars | `hints.hint_bar()`, eight tool windows | Every tool window prints a themed bar along its bottom edge listing the keys it really answers to — git graph (`F5 refresh · +/− zoom · 0 reset`), Activity (`Ctrl+F filter · Ctrl+L clear`), bookmarks (`Enter jump`), recents/outline (`↑↓ move · Enter open`), doctor (`F5 rerun · Ctrl+Shift+C copy report`), usage (`F5 refresh`), What's New — with a muted mouse note where the mouse is the tool ("click a row to copy") |
| The honesty contract | `hints.tree_bound()` + `accel_pattern()` | A key hint is rendered only if its exact Tk event pattern is genuinely bound on the window or any descendant (both `<0>` and `<Key-0>` spellings count); the `Esc` chip appears only when `<Escape>` is really bound; an unbacked hint is dropped and reported in `dropped_hints` instead of being shown as a lie — the door sign cannot outlive the door's truth |
| Never raises | `hints.hint_bar()` | Verification runs on the first idle moment after construction (bindings made after the bar is created are still counted) and re-runs via `refresh()`; a bar with nothing honest to say hides itself; a bar on a dying window quietly disappears — a hint bar never raises, a window never loses content to garnish |
| Git-graph zoom | `GitGraphWindow.zoom_step()` / `zoom_reset()`, keys `+` `−` `0` | A real row-density zoom (0.5×–3.0×): rows, lanes, dots, diagonal edges, click hit-testing and the scroll region rescale together, so a 200-commit repo reads as a trunk or as a spreadsheet at one keystroke; `F5` / `Ctrl+R` refresh from the keyboard |
| Doc states the rule | `docs/KEYBINDINGS.md` — Tool windows (v2.48) | The keybindings doc gained the window keys and says the rule out loud: a key appears in a hint bar only if the code really binds it — unit-tested so it stays that way |

## The Packs Answer for Themselves (v2.54.0)

| Feature | Where | What it does |
|---|---|---|
| Index-aligned fuzzy matching | `fuzzy.match()` | The audit's root fix: lowering a label can change its length ('İ'.lower() is 'i̇' — TWO code points), and every position after it drifted, lighting up the wrong letters in the palette's highlight runs. Matching now re-lowers per raw character (first lowered code point each) when lengths disagree, so positions — and `split_runs` highlight runs — stay aligned with the text actually rendered; the ASCII path is byte-for-byte unchanged |
| Pack audit | `i18n.pack_stats()` | Every language pack answers for itself: coverage (keys present vs the English source), missing, stale (keys the source no longer names), and highlight-safe — whether every string keeps its length under `.lower()`, the property the fuzzy highlight silently assumes. Built-ins first, then user packs on disk; a pack that cannot be read reports itself as unreadable instead of vanishing |
| The audit verb | terminal `lang audit` | Prints the audit where you work: one line per pack (code, native name, built-in or user, coverage %, missing, stale), a `· NOT highlight-safe (key…)` marker naming up to three offending keys, and a closing line explaining what highlight-safe means — plus `lang` itself finally joined the terminal help table and the verbs browser |
| Copy recovery command | `_git_menu_entries()`, `_git_copy_command()` | The branch chip menu's copy sibling, state-aware like the deps menu's pip row: diverged offers `git pull --rebase && git push`, ahead-only offers `git push`, behind-only offers `git pull`, in sync stays silent (a row must earn its place) — the command lands on the clipboard with toast + terminal receipt, ready to run anywhere |
| Junk kinds ignored | `_git_copy_command()` | An unknown kind copies nothing and raises nothing — a helper row must never become a hazard |

## The Menus Come to You (v2.53.0)

| Feature | Where | What it does |
|---|---|---|
| Keyboard doors to every chip menu | `_open_chip_menu_keyboard()`, `_chip_menu_registry()` | The four statusbar menus stop living only under right-click: the branch, deps, scribe and autosave menus open from the keyboard, anchored just above their own chip (the menu's requested height lifts it clear of the statusbar) and in the renderer's new "keyboard" mode — a palette row, an accelerator or a verb is a REAL user gesture, so the grab is kept and the posted menu hears Enter/arrows/digits immediately, the same contract a right-click gets |
| Palette rows | `palette_commands()` | Four new rows — *Branch chip menu*, *Deps chip menu*, *Scribe chip menu*, *Autosave chip menu* — advertise `Ctrl+Alt+G/E/W/A` and open their menu through the keyboard path; the v2.47 honest-keys audit polices every claim, so the accelerators are really bound |
| Real accelerators | root binds `<Control-Alt-g/e/w/a>` | `Ctrl+Alt+G` opens the branch menu (commit, push, pull, graph), `Ctrl+Alt+E` the deps menu (rescan, repair, watch), `Ctrl+Alt+W` the scribe menu (summary, goal, reset), `Ctrl+Alt+A` the autosave menu (snapshot, browse, toggle) — chosen to miss every existing `Ctrl+Alt+` binding (s/d/h/r/z) |
| The chip verb | terminal `chip <name>` | `chip branch` (aliases: `git`), `chip deps` (`env`, `dependencies`), `chip scribe` (`writing`), `chip autosave` (`session`, `sesave`) each open their menu and log the honest receipt — "Enter runs the highlighted row, Esc puts it away"; bare `chip` lists the four names, an unknown chip is told honestly |
| Copy pip install command | `_deps_copy_install()`, deps menu red state | When the deps chip is red, the menu gains a helper beside the repair row: one click puts a ready `pip install <pins>` line on the clipboard — pins from `depcheck.suggested_pins` over the stored report's missing list (PIL becomes pillow, yaml becomes pyqml-canonical names), a toast and a terminal receipt confirm, and with nothing missing the row's work is an honest "No missing imports to install" |
| Tooltips name the key | `_chip_tip()` | All four chip tooltips now end with their accelerator ("right-click for actions · Ctrl+Alt+G") — discovery at the point of use, not just in the docs |
| The seam stays honest | `_render_chip_menu(mode=…)` | Three named modes: "gesture" (a real pointer event — grab kept), "program" (`event=None`, the tests' way in — grab released at once, the v2.52 seam untouched) and "keyboard" (a real non-pointer gesture — grab kept, anchored `at` the chip). Same poller, same dismissal, same cleanup contract in every mode |

## Menus That Learn the Keyboard (v2.52.0)

| Feature | Where | What it does |
|---|---|---|
| Keyboard-ready chip menus | `_render_chip_menu()` | The probe that designed this round: `tk_popup` takes an X grab and that grab is exactly what routes key events to the posted menu — but the renderer released it immediately, so every chip menu since v2.42 was mouse-only and Tk's own Up/Down/Return/Escape/typeahead starved. A menu opened by a real right-click now KEEPS the grab while it is up |
| The unpost poller | `_arm_menu_unpost_poll()` | The other half of the fix: a 40ms poller watches the posted menu and releases the grab the moment it unposts, handing the focus back to wherever it was — bounded, idempotent, and it dies quietly with its menu. Tk's grab state is per-DISPLAY and process-wide, so nothing may outlive the menu (found by the pytest interps) |
| First row wakes up active | renderer, `menu.activate()` | The first activatable row is active the moment the menu opens: Enter takes it straight away, Up/Down walk from there — no blind arrow-pressing to find out whether the keyboard works |
| Home / End / digits 1–9 | `_wire_menu_keys()` | Bound on the posted menu itself: Home/End jump to the first/last activatable row, digits run the Nth COMMAND (separators never count — the number is the number it is invoked by, the same trick the AI quick-actions launcher learned in v2.50) |
| The programmatic seam | `event=None` | A menu opened without a pointer gesture (the tests' way in) releases the grab at once — nothing outlives the call. The lesson is written in the code: a grab left held at teardown keeps swallowing pointer events from whatever runs next |
| Quit puts the menu away | `_dismiss_chip_menu()`, `_on_close()` | The studio's quit path unposts the last chip menu and releases its grab BEFORE the root goes down — leaving cleanly means leaving nothing behind |
| Introspectable menus | `menu._ds2_rows`, `app._last_chip_menu` | The posted menu carries the rows it was built from (same spirit as v2.50's `bar.pairs`): tests assert a menu's promises without scraping labels |
| Git menu wears its divergence | `_git_menu_entries()` | The sync rows take the branch's severity through the renderer's color element: red `Push to origin` / `Pull from upstream` when the branch diverged (push/pull blind is how commits get lost), amber when one plain push or pull would settle it, silent when already in sync — the same language the deps menu learned in v2.51 |
| Interval picker | Settings → Activity | "Hours between snapshots" — a themed spinbox (1–168) replacing the hardcoded 24: reads the saved value, clamps on save, junk lands on 24. The engine reads it on every half-hourly beat, and bare `activity auto` names the interval in its report |

## The Diary Writes Itself (v2.51.0)

| Feature | Where | What it does |
|---|---|---|
| Nightly auto-snapshot | `activity.autosnap()`, gate `activity_autosnap` | When the gate is on, the whole receipt diary lands in `<config>/exports/activity-auto-<stamp>.json` every 24h (checked 8s after boot, then every half hour — the clock decides, not the session count); the ring order is preserved, the write is atomic, and the last 14 snapshots are kept — older ones are pruned by name, count reported |
| Honest defaults | `activity.autosnap_due()` | The gate ships OFF — nothing writes behind your back until you ask; a missing last-run stamp means due the moment the gate turns on; a junk interval falls back to 24h; a full disk is a silent non-event (the diary itself survives) |
| `activity snap` | terminal verb | Write a snapshot now, gate or no gate — the same code path the nightly clock uses, so the verb tests the machinery |
| `activity auto on\|off` | terminal verb | Flip the nightly gate from the terminal; bare `activity auto` reports the state honestly |
| Settings: Activity section | `app.py` settings window | The gate as a checkbox ("every 24h the whole diary lands in exports/ as JSON — the last 14 are kept") with the terminal verbs named underneath; persisted with every other setting |
| Deps menu wears its severity | `_deps_menu_entries()` + `_render_chip_menu()` | The chip-menu renderer takes a 4th tuple element (foreground): the deps menu now paints its rows with the chip's own palette — red `Queue deps fix (N missing)` + red fresh rescan when imports are missing, amber rescans when the cache drifted — so the menu and the chip tell the same story in the same colors |

## Hint Bars Wave 3 (v2.50.0)

| Feature | Where | What it does |
|---|---|---|
| Ten more door signs | branches, gallery, sqlitelab, xmlbench, csvkit, unitconv, hexdump, mathpad, pwdgen, quick actions | Every remaining workshop window prints the honest bottom-edge bar — twenty-five windows now open their keys to the keyboard, and every chip is verified against a real binding through `accel_pattern` + `tree_bound` before it is allowed on the bar |
| Five windows that had no keys at all | `xmlbench` / `csvkit` / `unitconv` / `hexdump` / `pwdgen` | The converter-lab windows answered only to the mouse. Each gained real window-level bindings before the bar was allowed to advertise them: XML bench pretty/minify/copy (`Ctrl+P`/`Ctrl+M`/`Ctrl+Shift+C`), CSV lab copy-as-TSV, Byte snoop copy-dump, PassForge new-password (`F5`) and copy, unit converter swap (`Ctrl+R`) and copy |
| The canonical copy spelling | `<Control-C>` everywhere | `Ctrl+Shift+C` arrives at Tk as keysym `C` — the canonical pattern `<Control-C>` — which is also why text inputs keep their native `Ctrl+C` selection copy untouched: the unshifted `c` never matches the uppercase keysym. The hint text still says `Ctrl+Shift+C` because that is what the human presses; the verifier checks the binding the press really hits |
| Introspectable honesty | `hints.hint_bar()` → `bar.pairs` | A bar now carries the claims it makes: `bar.pairs` lists every `(key, text)` pair it advertises, so tests (and the curious) can assert a bar's promises against the code without scraping labels — `dropped_hints` and `filled` were already readable |
| AI result window keys | `quick_actions.ResultWindow`, `Ctrl+Shift+C` / `Ctrl+R` / `Ctrl+Shift+I` | The streaming answer window copies its answer, and — when the action ran on a code selection — replaces that selection or inserts below from the keyboard; the bar shows the replace/insert chips only when those verbs exist |
| Number-key launcher | `ActionsMenu`, `1…7` | The AI quick-actions menu binds each row's position: press the number, run the action, menu closes. The bar advertises every row by number and label — all really bound |
| Gallery search jump | `TemplateGallery`, `Ctrl+F` / `F5` | The template gallery (previously Esc-only) jumps to its search box and re-applies the filter from the keyboard |

## Hint Bars Wave 2 (v2.49.0)

| Feature | Where | What it does |
|---|---|---|
| Diff viewer footer, at last | `DiffViewer._build_footer()` | The method had been *called* since v1.4 but never defined — every diff window died with AttributeError the instant it opened (the pure engine below it tested fine, so nobody noticed). Now the bottom edge carries a one-line verdict: `before → after · 14 rows · +4 −2 ~1 · 3 changed hunks`, and the header counter echoes "patch copied" when you copy |
| Diff viewer keys | `F3` / `Shift+F3` / `Ctrl+U` / `Ctrl+C` | The hunk navigation the mouse could already do (‹ ›) is now keyboard-native: step changes, flip split/unified view, copy the clean patch — and the honest hint bar advertises exactly these, nothing more |
| The graph finally draws its diagonals | `GitGraphWindow._draw()` | `lane_of` was referenced on every edge but only ever defined inside `assign_lanes` — any repo with ≥2 commits died mid-draw with NameError, silently: every prior check looked before the 80ms refresh timer fired, so the graph checks passed vacuously on an empty canvas. The map is now rebuilt per draw, and the wave-2 tests drive a real merge topology (4 commits, 2 parent edges, 27 canvas items) so the diagonals can never silently vanish again |
| Lane hover tooltip | `GitGraphWindow._show_tip()` / `_hide_tip()` | Hovering a graph row whispers the whole truth: the full commit subject (the canvas truncates at 72 chars — the tooltip never does), every ref, and the author/date line; it hides on off-row, on leave, on click, clamps its position to the screen, and never raises |
| DevTools tab keys | `DevTools.select_tab()`, `Ctrl+1…5` | The five tabs (regex, JSON, text, time, color) answer from the keyboard — and the bar advertises all five, one chip each |
| Text diff + cheat sheet keys | `Ctrl+Shift+C`, `Ctrl+S`, `Esc` | The paste-diff window copies its diff and closes from the keyboard; the cheat sheet copies its HTML, saves it, closes — both advertise only what is really bound |
| File stats keys | `Ctrl+C` / `Ctrl+E` / `F5` | Copy report, export the markdown, rescan — the three mouse buttons gained honest keyboard paths, and the Esc chip says "clear filter" (what it really does) instead of the default "close" |
| Scratchpad's verified sign | `scratch.py` | The hand-written "- Ctrl+Enter: stamp…" label is replaced by a real hint bar — same promise, now verified against the actual bindings instead of trusted |
| Goal dialog whispers | `scribe.open_goal_dialog()` | The writing-goal dialog carries the standard bar: `Enter set goal · Esc close` — both really bound |

## Honest Keys (v2.47.0)

| Feature | Where | What it does |
|---|---|---|
| Accelerator audit | `app.accel_pattern()` + `looks_like_accel()`, palette | Every accelerator the command palette advertises is translated into the exact Tk event pattern and verified against the real bindings — a hint that claims `Ctrl+S` without a bound `<Control-s>` cannot survive the audit; category tags ("DS2") and symbol positions ("line 42") are never chased as claims |
| Chip-menu accelerators | `_render_chip_menu()` 3-tuple rows, git menu | A chip-menu row may advertise an accelerator right-aligned in the themed popup — but only where a real binding exists: *Commit staged…* shows `Enter` (the commit box really does commit on Return); menus for lanes with no bindings advertise nothing |
| Doc agreement | `docs/KEYBINDINGS.md` | The keybindings doc says exactly what the code binds (`Ctrl+Shift+D` duplicate, `Ctrl+Shift+K` delete line, `Ctrl++`/`Ctrl+-` text size) — the stale `Ctrl+D` claim is gone; unit-tested so it stays that way |

## Activity Log (v2.44.0)

| Feature | Where | What it does |
|---|---|---|
| Toast receipts | every `app.toast()` call, `activity.ActivityLog` | Every notification the studio whispers — confirmations, errors, snapshot acks — is archived in a capped ring buffer (100 events, newest first) with its kind (info / success / error) and a timestamp; a toast can never break the lane that produced the event |
| Activity window | terminal `activity` / `notifications`, palette *Activity — recent notifications…*, `activity.open_activity()` | One themed window lists the receipts: kind-colored dots, relative stamps ("2m ago"), live substring filter (the same first pass `help <q>` uses) with an honest "nothing here" empty state, and a count label that tells the truth |
| Click to copy | window rows, `on_copy` callback | Clicking a row copies its message to the clipboard and fires a confirmation toast — a notification you looked away from can still become a bug report |
| Clear | window header | One click wipes the slate — the ring, the rows and the count agree immediately |
| Night survival | `activity.save_json()` / `load_json()`, `<config-dir>/activity.json` | The receipts survive the night: every toast re-writes the ring atomically (tmp + `os.replace`, the `Config.save` pattern), boot reloads whatever the last session whispered, and a corrupt or torn file falls back to a fresh ring honestly — lost receipts are never fatal |
| Since last time | `ActivityLog.from_list()` prev-marking, window divider | Entries loaded from disk carry `prev=True` and render under a muted "— since last time —" divider: this session's whispers on top, the older receipts below, one glance to tell them apart |
| Relative stamps | `activity.rel_time()` | Rows show "just now", "2m ago", "3h ago", "5d ago" instead of clock times — pure and unit-tested, with a future timestamp rendering as an honest blank |
| Clear persists | window `on_change` callback | Wiping the slate fires the app's `on_change`, so the file on disk agrees immediately — no resurrected receipts on the next boot |
| Kind filters | window dot row, `ActivityLog.filtered(query, kinds)` | Click a colored dot (● success / ● error / ● info) to hide that kind; click the hollow dot to bring it back. A kind the studio cannot name always shows — you cannot re-show what you cannot name, so nothing silently vanishes. The count label always tells the truth about what is on screen |
| Copy all | window header, `activity.export_text()` | One click puts the whole ring on the clipboard as a chronological diary (oldest first, one receipt per line: `[stamp] kind    message`) — whatever the filter shows, every receipt ships. Long copies acknowledge as "Copied N characters" instead of shouting the whole text back |
| Export to file | window *Save as file…*, `activity.export_to()` | A save dialog (seeded with the studio's config dir) writes the receipts to any path — the typed extension picks the format (`.json` → a loadable snapshot, `.csv` → the sheet, anything else → the text diary), the write is atomic, and a cancelled dialog is an honest no-op; the app acknowledges the path and the format it chose in a toast and the terminal |
| Export verbs | terminal `activity copy` / `activity export [json|csv] [path]` | The `activity` verb grew hands: `copy` puts the diary on the clipboard, `export` writes it beside `activity.json` (or to the path you give, with an explicit `json`/`csv` override naming the default file's extension). A nonsense sub-command gets an honest `try:` line, and `help` documents both |
| Verbs registry | TERMINAL_HELP + `verbs` browser | `activity` is a first-class verb: `help activity` explains it, `help act` finds it fuzzily, and the Terminal Verbs browser lists it with the rest |
| Toast mute | Settings → Toasts, `toast_show_info` / `toast_show_success` / `toast_show_error` | Each toast kind can be muted separately (searchable settings section): a muted kind keeps its receipt in the Activity log but skips the 3.4-second card — the log remembers, the screen stays quiet; an unknown kind always whispers |

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

## The Translator Gets a Desk (v2.55.0)

| Feature | Where | What it does |
|---|---|---|
| Translation desk | `langedit.PackEditor`, terminal `lang edit [code]`, Settings ▸ Look & feel ▸ *Edit a language pack…*, palette | Every English key beside its translation in one themed window: the EN source read-only above, the translation box below, list markers at a glance — ● translated, ○ missing (English shows through), ✕ stale (the source dropped the key), ⚠ translated but NOT highlight-safe. Typing commits into the working copy live, so the header meter (covered/total, %, missing, stale, unsafe) is always honest |
| Filters + search | desk filter chips | All / Missing / Stale / Unsafe chips over the key list, plus a type-to-filter box across keys, translations and English source — a translator with an hour can work only the missing bucket and stop |
| Live unsafe warning | desk detail pane | The v2.54 highlight contract as you type: a string that changes length under `.lower()` (İ → 'i̇' is two code points) gets an inline red warning, because every fuzzy highlight after it would shift. Flagged live, counted in the meter, ⚠ on the row |
| Atomic user packs | `langedit.save_user_pack()` | Save writes `~/.dxn1-studio/lang/<code>.json` via temp file + `os.replace` — a crash mid-save cannot tear the pack. Empty translations mean "back to English" and are dropped; a pack that is the active language re-activates on save, so edited strings go live at once |
| Seed from English | desk button | Fill every missing key with the English string — a starting point to edit down, the desk's version of `export_template`. Nothing is written until Save |
| The chooser | `langedit.PackChooser` | Bare `lang edit` (or the Settings/palette door) opens the desk's door: one honest row per pack with live coverage from `pack_stats`, or name a new code to start clean. Junk codes get an inline reason; `en` is refused — the source of truth is translated FROM, not edited |
| Honest verbosity | everywhere | Unknown codes through the verb are refused with the naming rules, stale keys are kept on save (the desk edits, it does not silently drop), and the launcher window that grows to fit its content: the AI quick-actions menu now accounts for its real requested width instead of clipping at a fixed 300px |

## The Desk Grows Eyes (v2.56.0)

| Feature | Where | What it does |
|---|---|---|
| The honest ledger | `langedit.pack_diff()`, terminal `lang diff [code]` | The coverage meter can flatter: a pack seeded from English and never edited shows 100% covered while every string still reads English. The diff splits a pack's own strings into **real** translations (they differ from English) and **untouched seeds** (byte-identical — wearing the pack, not speaking it), alongside missing / stale / unsafe, and prints `real_pct` — the number that cannot lie: real translations over the English total. Bare `lang diff` names the current language; `en` is refused with "it does not differ from itself"; unknown packs get the list |
| Untouched filter | desk chip #5 | All · **Untouched** · Missing · Stale · Unsafe — the seeds are reviewable in place: every pack string that is byte-identical to English, seeded maybe but not yet translated. Edit one and it leaves the bucket at once; the meter carries the count (`… · N untouched`) so the header stays honest |
| Pack preview | `langedit.PackPreview`, desk button / Ctrl+P | The desk grows eyes: a slice of the studio UI — title bar, menu bar, toolbar, sidebar, find bar — rendered in the pack being edited, LIVE. Type in the desk and the preview keeps up keystroke for keystroke, so Menu ▸ Settings… becomes Ajustes… in context before saving. What the pack speaks wears the accent; English that shows through stays grey (exactly what `tr()` would answer). Closing the desk closes its eyes — no orphaned windows |
| Ctrl+P in the desk | desk keybinding + hint bar | Preview is a real gesture, advertised in the desk's hint bar beside Ctrl+S — one press re-renders or raises the open preview instead of stacking windows |

## Packs Travel Light (v2.57.0)

| Feature | Where | What it does |
|---|---|---|
| Export pack | `langedit.export_pack()`, desk button / Ctrl+E | The working copy leaves as a JSON file shaped exactly like a user pack — `{key: value}`, empty values already dropped. What the desk exports the desk imports, and `i18n.set_language` would layer it over built-ins untouched: sharing a pack is copying one file |
| Import pack | `langedit.merge_pack_file()`, desk button / Ctrl+I | Overlay a pack file onto the working copy IN PLACE — the desk's own exports, user packs, and `export_template` files alike. Valid pairs replace, empty values drop the key back to English (the desk's own rule, so a pack round-trips disk without changing its mind), junk is skipped and counted, and nothing reaches the pack file until Save. Unreadable files answer `(-1, 0)` so the desk reports honestly instead of guessing |
| The audit prints every number | `lang audit` | The honest ledger's `real_pct` rides along on every per-pack line (`· N% real`), skipped for `en` (the source does not differ from itself) and for unreadable packs; the closing explanation names the flattery coverage is prone to and points at `lang diff <code>` for the seeds. A seeded pack now shows `100% — 0 missing, 0 stale · 0% real` in one line |
| Buttons slice in the preview | `langedit.PackPreview` | The live preview's anatomy grew a sixth strip: the common dialog buttons (Cancel · Copy · Export… · Import… · Refresh · Close) rendered in the pack, beside title bar, menu bar, toolbar, sidebar and find bar |

## The Pack Gets a Checkup (v2.58.0)

| Feature | Where | What it does |
|---|---|---|
| The checkup core | `langedit.check_mapping()` | Reads a key→value mapping the way an import WOULD and reports what it would meet — BEFORE anything moves: non-string pairs (`junk`, skipped by an import), whitespace values (`empty`, dropped back to English), keys the source never names (`unknown` — dead weight that ages into stale), and values that change length under `.lower()` (`unsafe` — v2.54's highlight contract, a property of the value, stale keys included). Alongside: real/seeds counts and `covered_pct`/`real_pct` — the honest ledger computed for the thing in hand |
| `lang check [code\|file]` | terminal verb, `app._emit_checkup` | The pre-flight before sharing: a code reviews the installed pack (built-ins + the user pack on disk — what the runtime speaks), a path reviews the file itself. One ledger line (`N pairs read · N real, N still English · coverage N% · N% real`), every finding by name, then the verdict — `clean — nothing blocks an import` or `N findings — a pack worth sharing is worth fixing`. Unreadable files say so; unknown codes get the list plus the file hint; bare verb reviews the current language (`en` has nothing to check); a seeded pack reads 0% real with a pointer at `lang diff` |
| `lang pack <code> [dest]` | terminal verb | The terminal door for sharing: writes a pack's own strings as a user-pack-shaped JSON file (default `./<code>.json`; a directory dest lands `<code>.json` inside it). What the desk imports back, `set_language` would layer over built-ins untouched — and `lang check` on the file says what an import would meet. NEVER overwrites: an existing file is answered with `not overwriting` — sharing should not destroy. `en` is refused (the source is not shared); unwritable paths report the OSError class honestly |

## The Desk Grows to Fit (v2.59.0)

| Feature | Where | What it does |
|---|---|---|
| The chooser prints every number | `langedit.PackChooser._paint_packs` | The desk's door now speaks the honest ledger: every pack row reads `code · name · kind · coverage · N% real` — the same numbers the audit prints, one row per pack, so a seeded pack cannot look finished at the door. Unreadable packs keep their `· unreadable` note instead |
| The desk grows to fit | `langedit.PackEditor._fit_once()` | The v2.55 ActionsMenu pattern, desk edition: the desk opens no narrower than what it actually packed — a long meter, hint bar or translated header wins over the 680px default instead of clipping at the right edge. One-time at open; after that the window is the user's to resize |
| The preview ratchets out | `langedit.PackPreview._fit()` | The live preview re-measures itself on every refresh: a translated string longer than the 440px it opened at pushes the window out to fit (tested at 120 chars), and the ratchet never shrinks back — a manual resize is never fought, and a clipped preview can no longer lie about the pack |

## The Checkup Comes Home (v2.60.0)

| Feature | Where | What it does |
|---|---|---|
| The desk runs its own checkup | `langedit.PackEditor._run_check()` / `_render_verdict()` / `_verdict_tick()` | The checkup lives where the editing happens: `Check this pack` (or Ctrl+T) runs `check_mapping` on the desk's LIVE working copy and the verdict lands under the meter — red `⚠ checkup: N findings — …` for findings, green `✓ checkup clean — nothing blocks an import (N pairs · N% real)` when clean. **Every Import runs it automatically** — the moment you let a file in is the moment you most want to know what it was. Once asked for, the verdict recomputes silently on every keystroke, clear and import alike: it must never describe a working copy that is gone. The full findings list goes to the terminal through the app's shared `_emit_checkup` renderer, the way `lang check` prints them |
| `lang fix <code>` | `langedit.fix_pack_file()` + terminal verb | The checkup learns to heal: applies the SAFE repairs the checkup names to the user pack FILE — junk pairs dropped, empty values back to English (the import rule), unknown keys cut (dead weight that ages into stale) — names every repair, and re-activates the pack at once if it is the active language. The check is the dry-run, the fix applies. Nothing is written unless something actually changes; the rewrite is atomic (tmp + `os.replace`); unsafe strings are NEVER touched — a deletion is not a translation. `en` refused, unknown languages named, built-ins without a user pack answered ("built-ins are read-only here"), unreadable files report the error class |
| Width accounting round two | `hub.ProjectHub._center()` + `agent.PromptPreviewDialog` | The v2.55 pattern beyond the pack windows: the Project Hub opens no narrower (or shorter) than what it actually packed — the real request measured 972px against the 940 default, so the old fixed geometry WAS clipping long workspace rows — and the agent's prompt preview grows past 680px when its content asks. |
| Audit crash fix | `app.py` audit verb | A dormant v2.54 bug the v2.60 smoke caught: the `NOT highlight-safe` suffix re-applied `%`-formatting to the WHOLE audit line, which exploded on any literal `%` already in it (e.g. `100%`) the moment a pack carried an unsafe string. The suffix formats itself now |

## A Safety Net for the Fix (v2.61.0)

| Feature | Where | What it does |
|---|---|---|
| The fix writes a safety net | `langedit.fix_pack_file()` | Before any repair moves, the pre-fix copy lands beside the pack as `<code>.json.bak` — the fix line announces it ("second thoughts are one `lang unfix` away"). Only the most recent fix is undoable (a new fix overwrites the old net); a clean fix (nothing changed) writes no backup; a failed backup is reported ("this fix cannot be undone") while the fix itself still applies |
| `lang unfix <code>` | `langedit.undo_fix_file()` + terminal verb | The way back: restores the user pack file from the `.bak` — byte-for-byte, atomically — and CONSUMES the backup, so an undo cannot run twice by accident. The report carries both counts (`restored N from the pre-fix copy · the fixed pack had M`). Missing backups, unreadable backups and `en` all answer honestly; the same regex / unknown-language gates `lang fix` has; an active language re-activates with the restored pack live |
| The desk fixes itself | `langedit.PackEditor._apply_safe_fixes()` | The repair moves into the desk: the `Apply safe fixes` button cuts every unknown key from the LIVE working copy at one click — the verdict turns green on its own (`_verdict_tick` rides `_refresh`), the status says `cut N`, and the terminal log names every key. Unsafe strings are not touched here either (a deletion is not a translation); an empty working copy answers `nothing to fix` |
| `geom.fit_to_content()` | `dxn1_studio/geom.py` | The v2.55 width pattern becomes ONE helper: opens a window no narrower (or shorter) than what it actually packed, with the designed default as the floor; `ratchet=True` records the high-water mark (`win._fit_size`) and never shrinks back — never raises. Eight more fixed windows now ride it: TODO/FIXME results (720x420), What's New (780x560), terminal verbs (640x520), usage dashboard (720x600, re-centered on the size it actually got), packages (800x620), session restore (620x380), agent memory (640x540), sqlite lab (1000x640) |

## Width Accounting, Round Four (v2.62.0)

| Feature | Where | What it does |
|---|---|---|
| Nineteen more windows ride the helper | `term.py` · `scratch.py` · `textdiff.py` · `treeexport.py` · `restbench.py` · `quick_actions.py` · `readability.py` · `pair.py` · `unitconv.py` · `textcase.py` | The mechanical batch: each fixed window keeps its designed default as the FLOOR and queues `geom.fit_to_content` via `after_idle` — the fit fires once the build settles, so the window opens no narrower (or shorter) than what it actually packed whenever the real request is bigger, and never fights a smaller one. Batch one: terminal window 860x520, scratch pad 560x520, text diff 760x500, tree export 760x600, REST bench 900x640, quick-actions launcher 760x560, readability panel 720x560, pair mode 720x600, unit converter 560x460, text case 560x420. Batch two: hex dump 700x460, number base 520x430, project dialog 420x260, XML bench 720x480, password generator 520x360, branch manager 760x600, its rename dialog 360x120, CSV kit 680x480, JWT lab 880x600 |
| The after_idle contract | `geom.fit_to_content` consumers | A fit queued in `__init__` cannot measure un-built content — `after_idle` runs it on the first event-loop pass after construction, when every widget is packed. The window may draw one frame at its floor, then fit; the smoke verifies both halves of the contract (queued ≠ applied, applied after `update()`) |

## The Sweep Completes, the Ledger Goes Public (v2.63.0)

| Feature | Where | What it does |
|---|---|---|
| Width accounting, round five — the sweep completes | `devtools.py` · `envcheck.py` · `charts.py` · `gitgraph.py` · `clipboard.py` · `diffview.py` · `hasher.py` · `contrast.py` · `colorkit.py` · `cronexp.py` · `ai_lint.py` · `gen.py` · `focus.py` · `charmap.py` · `mathpad.py` · `community_themes.py` · `macros.py` · `markprev.py` · `cvdlab.py` · `cheatsheet.py` · `activity.py` · `bookmarks.py` · `filestats.py` · `agent.py` | The last twenty-four fixed windows join `geom.fit_to_content` — devtools 880x620, .env lint 840x600, chart studio 760x560, git graph 860x640, clipboard history 640x420, diff viewer 980x640, hasher 860x560, contrast 860x520, color kit 560x560, cron explainer 760x520, AI lint 680x520, scaffold generator 760x560, focus timer 360x300, character map 640x480, math pad 560x470, theme gallery 760x600, macro panel 520x460, markdown preview 980x640, CVD lab 760x540, cheatsheet 720x520, activity 620x480, bookmarks 720x520, file stats 760x640, and the agent's system-prompt preview (whose v2.60 inline heal is retired). The two v2.59 custom ratchets (desk, live preview) ride the shared helper too — same semantics, one body (`ratchet=True`). Every fixed-geometry window in the package now speaks one pattern, and the fleet audit in `test_width_sweep_five` keeps it that way forever: any future fixed window without a fit fails CI |
| `lang report [dest]` | `langedit.build_report()` · `langedit.format_report()` + terminal verb | The whole honest ledger at once: one row per installed pack (English excluded — the source is not graded against itself), each carrying covered %, real %, real/seeds/missing/stale/unsafe counts, sorted WORST-FIRST by real_pct so a seeded pack cannot hide in alphabetical order. Bare `lang report` prints the table inline; `lang report <dest>` writes the shareable text file — never overwriting (a report should not destroy either), quoted paths unquoted, a directory dest landing `lang-report.txt`, an unwritable path answered honestly. The verdict names the fully-real packs and the seeded ones, and the closing lines point at the whole verb family: `lang diff <code>` names every string · `lang check <code>` is the dry-run · `lang fix <code>` applies the safe repairs |

## The Studio Keeps Its Windows (v2.64.0)

| Feature | Where | What it does |
|---|---|---|
| `tools windows [raise|close <n|title>]` | `app.py` terminal verb | The studio's window manager: a dozen tool windows can pile up and alt-tab is the only way back. Bare `tools windows` lists every open Toplevel of the root — numbered, honest geometry, transient marked — or answers that none is open; `raise <n|title>` deiconifies, lifts and focuses the match (a 1-based index or a case-insensitive title substring both name it); `close <n|title>` destroys it and says so; a substring matching several windows is REFUSED with the candidates named (guessing is not closing); `close all` destroys only the TRANSIENT tool windows — the transient flag is the guard, and the report counts what was spared (`N non-transient left alone`) |
| The report says who wrote it | `langedit.format_report()` | A shareable `lang report <dest>` file now carries the studio's own version in its header (`generated … · English source: N keys · DXN1 STUDIO 2.64.0`) — best effort, so an exotic embedding without the package attribute still reports, just without the version line |

## The Windows Learn to Mind Their Places (v2.65.0)

| Feature | Where | What it does |
|---|---|---|
| `tools cascade` · `tools tile` | `geom.cascade_positions()` · `geom.tile_rects()` + terminal verbs | The window manager learns to tidy. `tools cascade` stacks every open tool window from the top-left, each title bar 28px down-right of the last so every one stays grabbable, wrapping back toward the origin when the stack would march a title bar off-screen — sizes are KEPT (the width sweep taught every window its right size; this only puts them in a place). `tools tile` deals every open tool window into a cols x rows grid (cols = ceil(sqrt(n))) covering the screen inside a small margin, each window resized to its cell so nothing hides behind nothing — the designed minimum cell holds while the screen allows, and on a screen too small the SCREEN wins (a window past the edge is invisible, a cramped one is merely small). Both verbs answer honestly when nothing is open, and the `tools windows` footer now points at them |
| The open-windows chip | `app.py` statusbar (`status_wins`) + 2s tick | The window manager's face in the statusbar: quiet while no tool window is open, muted "N open" while the pile is manageable, amber (bold) at 6+ — because that is when alt-tab stops being a strategy. Signature-cached so the 2s heartbeat redraws only on change, cancelled on close. Click runs the honest `tools windows` listing (dispatched as a terminal verb — a shell subprocess cannot speak studio verbs); right-click opens the chip's menu (list · cascade · tile · close-all transient), and the menu reaches the keyboard too: `chip windows` (aliases `wins`/`windows`) |
| Chip-menu row tooltips | `_render_chip_menu` · `_wire_menu_row_tips` | The twice-parked polish lands: a chip-menu row may carry a fifth element — the hint — and hovering that row shows a quiet tooltip at the row's height BESIDE the menu (never on top of the rows, so it never steals the click). Motion-driven: a row without a hint, the pointer leaving, or the menu closing — the tip is gone, and the unpost poller retires it too so a tooltip never outlives its menu. The windows, scribe, autosave and git chip menus all carry hints now |

## The Window Manager Remembers (v2.66.0)

| Feature | Where | What it does |
|---|---|---|
| `tools layout save <name>` · `tools layout <name>` · `list` · `forget <name|all>` | `geom.capture_layout()` · `geom.store_layout()` · `geom.apply_layout()` + terminal verb | The window manager's memory: arrange the desk once, recall it forever. `save <name>` snapshots every open tool window's title, geometry and transient flag into the config store — the same name overwrites (arranging the desk twice is an update, not an error), oldest layouts fall off past 12, and a desk of nothing saves nothing (an honest refusal). The bare `tools layout <name>` — or `restore <name>`, spaces included — hands each saved geometry back to the live window whose title matches it EXACT-first, then as a substring, so an impostor window never steals a place; a saved window that is not open is reported missing BY NAME — a layout arranges what exists, never conjures. `list` shows the book (each layout with its windows), `forget <name|all>` removes without touching the windows themselves (the book forgets, the windows stay) |
