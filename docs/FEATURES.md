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
