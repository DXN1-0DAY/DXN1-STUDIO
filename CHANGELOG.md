# Changelog

All notable changes to DXN1 STUDIO. Format based on
[Keep a Changelog](https://keepachangelog.com/); versioning is
`MAJOR.MINOR.PATCH` while in **beta**.

## [2.13.0] — 2026-09-14 · beta · "nothing copied is lost"

### Added
- **Clipboard history** (`clipboard.py`, Edit menu → *Paste from
  History…*, palette, terminal `clip`, Ctrl+Shift+V) — a 1.5 s
  background poller (defensive, never raises) watches the system
  clipboard and keeps the last 25 distinct entries. The window pastes
  any earlier copy at the editor cursor with one double-click;
  repeats move to the top instead of duplicating; previews are
  one-line, whitespace-collapsed, 90-char capped.

### Tests
- Engine suite **43 cases** (+clip ring: bounds, eviction, repeat-to-
  front, junk rejection, preview truncation); boot QA 17/17 and a
  live window check (selection copy, clear, clean close).

## [2.12.0] — 2026-09-14 · beta · "order from chaos"

### Added
- **Line tools** (`linesort.py`, Edit menu, palette, terminal
  `sort <mode>`, Ctrl+Alt+S/D/H/R) — sort A→Z / Z→A / by length,
  dedupe (case- and whitespace-insensitive, first wins), seeded
  shuffle, reverse and trailing-whitespace trim. Works on the
  selection when there is one, the whole file otherwise; text outside
  the range is preserved byte-for-byte and a trailing newline never
  becomes a sortable phantom empty line.

### Tests
- Engine suite **42 cases** (+linesort: modes, ranges, seeded
  determinism, newline-shape preservation, hostile-input safety);
  boot QA 17/17.

## [2.11.0] — 2026-09-14 · beta · "heads down"

### Added
- **Focus timer** (`focus.py`, Workshop menu, palette, terminal
  `focus` / `focus <minutes>`) — a pomodoro that lives in the IDE:
  big clock, phase labels, session dots, start/pause/reset/skip and a
  log line that celebrates finished blocks. The engine is a
  deterministic state machine — transitions fire the exact second a
  phase hits zero, long break every 4th block, custom minute blocks
  via `focus 50`.

### Tests
- Engine suite **41 cases** (+focus state machine: roll-overs,
  long-break cadence, paused no-ops, skip/reset semantics); smoke at
  **31 checks**; boot QA 17/17.

## [2.10.0] — 2026-09-14 · beta · "trust, but verify"

### Added
- **Hasher** (`hasher.py`, Workshop menu, palette, terminal `hash` /
  `hash <file>`) — checksum lab: chunked MD5/SHA-1/SHA-256/SHA-512
  digests (1 MiB chunks, gigabyte files stay safe), folder manifests
  in `sha256sum -c`-compatible form with copy/save, paste-a-hash
  MATCH/MISMATCH verdicts and a *Verify ALL* pass that reports
  `N ok · M MISMATCH · K not in pasted manifest`.

### Tests
- Engine suite **40 cases** (+hasher: digest correctness vs hashlib,
  walk order, manifest round-trips, malformed/comment/binary-marker
  parsing); v2.9.0 smoke grew to **27 checks** (hasher windows joins
  the grid + manifest + mismatch paths); boot QA 17/17.

## [2.9.0] — 2026-09-14 · beta · "data in, trees out"

### Added
- **SQLite Lab** (`sqlitelab.py`, Workshop menu, palette, terminal
  `db` / `db <file>`) — a real database browser: tables and views with
  live row counts in the sidebar, a Browse grid with truncation-aware
  cells and CSV/markdown export, a Schema tab (columns with type/null/
  default/pk plus index flags), an F5 query bench (SELECT fills a grid
  capped at 500 rows, writes report affected counts and refresh the
  sidebar, errors land in the status line), an Info page with file
  size, journal mode and encoding — and read-only-by-default
  connections so browsing can never corrupt your data. The lab
  auto-discovers `.db` / `.sqlite` files in the workspace.
- **Directory tree export** (`treeexport.py`, Workshop menu, palette,
  terminal `tree` / `tree <dir>`) — README-ready ASCII trees with
  dirs-first sorting, depth 1–6, hidden-files and per-file size
  toggles (live regeneration), a shared junk-skip set (`.git`,
  `node_modules`, `__pycache__`…) with a skipped counter, a truncation
  flag, clipboard copy and save-to-file.

### Tests
- Engine suite now **39 cases** (+sqlitelab engine, +treeexport
  engine); the v2.9.0 UI smoke (`scripts/smoke_v290.py`) runs **21
  checks** across both new windows; boot QA stays 17/17.

## [2.8.0] — 2026-09-14 · beta · "the workshop"

### Fixed
- **The menu bar was dead.** The themed top bar's render loop destroyed
  every `tk.Menu` created as a child of the bar, so all six menus
  (File, Edit, View, Tools, Help) pointed at destroyed Tcl commands
  and never opened. Menus are now parented to the root and excluded
  from the render clear-loop; re-renders (theme switches) are verified
  safe. Every one of the 61 menu entries now carries a live binding.

### Added
- **Workshop menu** — one place for every DS2 tool window: Developer
  Tools, Cron Explainer, Readability Report, JWT Decoder, .env Lint &
  Mask, Data Generator and the Token Usage dashboard.
- **Cron decoder ring** (`cronexp.py`, palette, terminal `cron <expr>`)
  — any cron string becomes a plain-English sentence ("at 09:00, on
  MON"), a field-by-field table (names, steps, ranges, lists,
  7==Sunday, `@hourly`…`@reboot`) and the next five run times,
  computed by a built-in minute-stepper with month fast-forward.
- **Readability report** (`readability.py`, palette, terminal
  `readability`) — Flesch Reading Ease with a human verdict,
  Flesch–Kincaid grade, Gunning Fog, complex-word %, the sentences
  over 25 words and a word-pressure table; copies as markdown.
- **JWT decoder** (`jwt.py`, palette, terminal `jwt <token>`) —
  header + payload pretty-printed, time claims humanized ("expires in
  1h 59m" / "expired 3d ago"), claims table with iss/sub/aud/jti up
  front. Decode only — and it says so.
- **.env lint & mask** (`envcheck.py`, palette, terminal `env`) —
  lints duplicate keys, invalid key characters, spaces around `=`,
  unquoted spaces, ` # ` comment pitfalls, unclosed quotes, empty
  values — and produces a share-safe masked copy (secret keys starred,
  `postgres://user:***@host` URLs).
- **Data generator** (`gen.py`, palette, terminal `gen`) — RFC 4122
  UUID v4, spec-length ULIDs (26-char Crockford, newest first),
  nanoids, hex tokens, class-guaranteed passwords, PINs, lorem and
  fake users/events as ready-to-paste JSON — all via the `secrets`
  module.
- **Terminal help refresh** — `tools`, `cron`, `readability`, `jwt`,
  `env`, `gen` and `explain` now listed.

### Tests
- Engine suite grew to **37 cases**; the UI smoke grew to **28
  checks** (`scripts/smoke_v280.py`), and a new boot QA asserts all
  six menus are alive with bound commands after render and re-render.

## [2.7.0] — 2026-09-14 · beta · "the pocket knife"

### Added
- **Developer tools window** (`devtools.py`, Help → *Developer Tools…*,
  palette, terminal `tools`) — four tabs of everyday ammunition in one
  themed window, every engine pure and unit-tested:
  - **Regex tester** — live match list with spans, capture groups and
    named-group hints; ignore-case / multiline / dotall toggles;
    replace-with preview with backreferences; copy all rows; a
    500-match cap keeps the UI honest on pathological patterns.
  - **JSON workshop** — pretty (2/4), minify, validate, sort keys;
    errors report the exact `line X, col Y` of the offending byte.
  - **Text transformer** — `snake_case`, `camelCase`, `PascalCase`,
    `kebab-case`, `CONST_CASE`, Title Case with real identifier
    splitting (`HTTPServer2` → http, server, 2); base64 and URL
    encode/decode; `\u`/`\U` escape round-trips including the astral
    plane; MD5/SHA-1/SHA-256; word/char/line counts; *↑ use output as
    input* chains transforms.
  - **Time converter** — ticking ISO clock (local or UTC), epoch ↔ ISO
    both directions (`Z`-suffix and naive-timestamp handling) and
    relative labels (`3h ago`, `in 2d`).
  - **Color lab** — hex ↔ rgb ↔ hsl live conversion with a swatch,
    WCAG contrast ratio with AA/AAA grading against any second color,
    and eight harmony swatches (complement, analogous, triadic,
    lighter/darker) — click one to copy its hex.
- **Terminal shortcuts** — `tools`, `devtools` and `regex` open the
  window; `regex` seeds the pattern from the current editor selection.
- **Welcome tour step** — the tour now introduces the pocket knife.

### Tests
- Engine suite grew to **32 cases** (identifier splitting, codec
  round-trips, regex groups/flags/errors/cap, JSON line:col errors,
  epoch/ISO round-trips, relative time, color conversions, WCAG
  anchors, harmonies). New 22-check UI smoke (`scripts/smoke_v270.py`)
  drives every tab end-to-end under Xvfb.

## [2.6.0] — 2026-09-14 · beta · "know your places"

### Added
- **Hub workspace insights** (`workspace_stats.py`, Project Hub) — an
  aggregate *at a glance* strip above your recent workspaces: total
  workspaces, files, lines, disk size and the dominant languages
  across everything the hub tracks, recomputed on every refresh.
- **Branch chips on hub cards** — every recent workspace shows its
  current git branch (`⎇ main`) right on the card, best-effort with a
  4-second timeout so a locked repo can never stall the hub.
- **Hub right-click menu** — right-click any recent workspace for
  *Open*, *Reveal in file manager*, *Open terminal here* (falls back
  through x-terminal-emulator → gnome-terminal → konsole → xfce4 →
  xterm), *Copy path*, and *Snapshot now* — a one-click zip backup via
  the snapshot engine. Actions confirm themselves in a small flash
  message in the hub's bottom bar.
- **Encoding + line-endings chip** (`app.py`) — the statusbar now
  shows `UTF-8 · LF` (or `UTF-8 BOM`, `UTF-16`, `non-UTF8`, `CRLF`,
  `CR`) for the file you are editing. Encoding is sniffed once per
  open; line endings update live as you type.
- **Engine tests** — the consolidated suite grew to 26 cases covering
  insight aggregation, language-mix normalization, branch detection
  and the encoding sniffer.

## [2.5.0] — 2026-09-14 · beta · "the studio remembers"

### Added
- **Persistent bookmarks** (`bookmarks.py`) — the gutter bookmarks you
  already use now survive restarts. Per-workspace
  `.dxn1/bookmarks.json` (global fallback), restored whenever a file
  opens, split-view aware, atomic writes, corrupt-file recovery, and a
  workspace-wide **bookmark browser** with snippet previews, jump,
  remove and clear-file. Palette → *Bookmarks — browse all…*.
- **Prompt library** (`prompts.py`) — saved reusable asks for the
  agent: six starters (explain / review / tests / refactor /
  docstrings / commit message), `{file}`, `{selection}`, `{lang}`,
  `{workspace}`, `{date}` placeholders that fill themselves in,
  type-ahead picker, save-from-input, and one-key insert into the
  agent chat. Palette → *Prompt library*.
- **Line tools** (`widgets.py`, Edit menu) — Sort Lines A→Z / numeric
  / Z→A and Remove Duplicate Lines on the selection; numeric sort
  compares leading numbers so `2` beats `10`.
- **Error explainer** (`app.py`, terminal `explain`) — a nonzero exit
  plus a detected traceback prints a hint; `explain` (or the palette
  entry) hands the block to the agent with a fix-me prompt. Clipboard
  fallback when the agent panel is closed.
- **What's New viewer** (`whatsnew.py`, Help → *What's New…*) — the
  changelog rendered as a version rail + notes pane, and it auto-opens
  exactly once after every upgrade (`last_seen_version` guard).
- **Recent-files picker everywhere** — Ctrl+R and a File-menu entry
  now open the fuzzy recents popup; the palette entry remains.
- **File-statistics report export** — *Export .md* writes
  `.dxn1/filestats.md` (markdown table + largest files); the engine
  behind clipboard, CLI and export is shared.

### Changed
- Editor gutter click / F2 / Ctrl+F2 / Shift+F2 bookmark flow is
  unchanged — but every toggle now persists immediately.

## [2.4.0] — 2026-09-14 · beta · "know your workspace"

### Added
- **File statistics explorer** (`filestats.py`) — the honest answer to
  "what is in this workspace?": one read-only scan aggregates file
  counts and bytes per extension, finds the largest files and reports
  every noisy directory it skipped (.git, node_modules, caches,
  venvs). The window renders summary cards, a per-extension bar chart
  (click a bar to filter the list below) and a largest-files table
  (double-click copies the path). Copy-report button, rescan, and a
  CLI: `python3 -m dxn1_studio.filestats [dir]`. Palette → *File
  statistics*; terminal `stats` prints the one-line summary.
- **Recent-files fuzzy picker** (`recents.py`) — the File menu has
  recents, muscle memory wants Quick-Open: type a few letters, arrows
  to choose, Enter to jump. Relevance ranking puts basename prefix
  hits above path substring hits, with a subsequence fallback, so
  `util` finds `src/util.py` first. Palette → *Recent files…*.
- **Plugin status items in the statusbar** — the plugin API could
  register status items; now they actually show up. One compact label
  (left of the agents status) refreshes every 5 s, capped at three
  items so the bar stays calm, and survives broken plugin callbacks.

### Fixed
- Recents picker rendered an empty list on first open (shown-list
  initialised after first render).

## [2.3.0] — 2026-09-14 · beta · "fourteen ways to start"

### Added
- **Next.js + Svelte scaffolds** (`projects.py`) — the hub gallery now
  ships **14 templates**: Next.js gets real pages, an API route and a
  working package.json; Svelte gets App.svelte with a rune-ready
  counter and vite config.
- **Zen writing stats** (`zen.py`) — deep work, measured: honest
  words-per-minute (paste spikes filtered), session peak, word-goal
  percentage and an in-zen HUD card. Memory-only — nothing is
  recorded anywhere.
- **Plugin API** (`plugins.py`) — hooks, command registration and a
  manager UI, pulling the roadmap's plugin system forward.

## [2.2.0] — 2026-09-14 · beta · "see the whole file"

### Added
- **Editor minimap** (`minimap.py`) — the VS Code trick, the honest
  way: every line is a thin block coloured by role (keywords glow,
  comments dim, blanks vanish), with a draggable viewport rectangle.
  Polls the buffer cheaply, hides for short files. Palette →
  *Editor minimap on/off*.
- **Task runner** (`term.py`) — project tasks without ceremony: a
  `.dxn1/tasks.json` defines named commands ("test": "pytest -q"),
  sensible defaults per project kind ship built-in, and Task Runner
  executes through the studio's own process runner so output lands in
  the terminal. Palette → *Task runner*.

## [2.1.0] — 2026-09-14 · beta · "the studio speaks your language"

### Added
- **Internationalization** (`i18n.py`) — a tiny, honest i18n layer with
  **eight language packs**: English, Español, Français, Deutsch,
  Português, 简体中文, हिन्दी, 日本語. Dotted keys, graceful English
  fallback, `{placeholder}` support, and community packs as plain JSON
  in `~/.dxn1-studio/lang/`. `tr()` never raises.
- **Settings sync** (`sync.py`) — your setup, everywhere: export the
  safe subset of preferences to a **private GitHub gist** and pull it
  back on any machine. Reuses the GitHub CLI login (no new accounts);
  secrets never travel — the bundle is keys-whitelisted by design.

## [2.0.0] — 2026-09-14 · beta · **"DXN1 STUDIO 2" — the DS2 grand release**

Six releases in one sprint: the visual git suite, a remembering agent,
seven AI quick actions, pair programming with a plan-first engine, a
smarter welcome, a grown-up Project Hub, and a theme gallery — all in
pure Python + Tk, all defensively wired, all themed end-to-end.

### Highlights
- **Visual Git Suite** — word-level diff viewer (split/unified), commit
  graph with real lane routing, branch manager with merge/track/force.
- **The agent remembers** — per-workspace memory bank injected into
  every conversation; `remember:` teaches it instantly.
- **Token usage dashboard** — 14-day chart, per-model bars, cost
  estimates, CSV export.
- **AI quick actions** — Explain / Refactor / Docstring / Tests / Fix /
  Types / Optimize on any selection, streamed with insert-or-replace.
- **AI commit messages** — ✨ AI msg drafts Conventional Commits from
  the staged diff.
- **AI review** — whole-file findings with severity colours.
- **Pair mode** — plan → approve → build through the sandboxed engine.
- **Onboarding v2** — workflow wizard slide, tour covering every DS2
  power, the DS2 Cheat Sheet (Help → DS2 Cheat Sheet…).
- **Project Hub v2** — pins, live workspace stats, instant search,
  Rust + Go scaffolds (12 templates).
- **Theme gallery** — 12 palettes, live swatches, safe custom-theme
  engine; themes are data and can be shared as JSON.
- **Editor power tools** — macros, multi-cursor, snippet engine.

### Docs
- `docs/FEATURES.md` — the full DS2 feature index
- `docs/ARCHITECTURE.md` — the layer cake, module contract, theme engine
- `docs/KEYBINDINGS.md` — every shortcut

## [1.9.0] — 2026-09-14 · beta · "paint it your way"

### Added
- **Theme gallery** (`community_themes.py`) — twelve curated palettes
  (Midnight Violet, Deep Ocean, Forest Night, Ember Dark, Carbon,
  Paper White, Warm Paper, Mint Light, Rosy Dawn, Nordic Light,
  Solarized-ish…) shown as live swatch cards with a code sample in
  the actual palette. **Apply** saves the palette to config and
  restarts the studio into it — the same safe swap as the built-in
  dark/light toggle.
- **Custom theme engine** (`theme.py`) — `from_config` now resolves a
  stored `custom_theme` palette override with strict fallbacks: keys
  must exist in the base palette, anything missing or broken silently
  falls back, so a half-written theme can never render the studio
  unreadable. Themes are plain JSON — export, share, import.
- **First-run gallery** (`gallery.py`) — the hero art loader for the
  new onboarding surfaces.

## [1.8.0] — 2026-09-14 · beta · "the hub grows up"

### Added
- **Workspace statistics** (`workspace_stats.py`) — fast, honest
  numbers for any folder: file count, total lines, language mix, disk
  size and git commit count, computed in one capped walk that can
  never freeze the UI or raise.
- **Project Hub v2** — recents now show live stats ("128 files ·
  Python 61% · 12 commits"), workspaces can be **pinned** (they float
  to the top with an accent border), and the whole list filters as you
  type.
- **Rust and Go scaffolds** — the hub gallery grows to 12 templates:
  real Cargo.toml + main.rs and go.mod + main.go starters, ready for
  `cargo run` and `go run` respectively.

## [1.7.0] — 2026-09-14 · beta · "the welcome gets smarter"

### Added
- **Workflow Essentials wizard slide** — new "Four moves worth knowing
  tonight" step between Agents and Ready: the command palette, quick
  open, AI quick actions and `remember:` — the shortcuts that make DS2
  feel like it reads your mind, taught on first launch.
- **Interactive tour v2** — two new spotlight steps: *Pair mode & quick
  actions* (for agent users) and *The studio remembers* (memory bank,
  usage dashboard, visual git suite), so the tour now covers every DS2
  superpower.
- **The DS2 Cheat Sheet** (`cheatsheet.py`) — a searchable, grouped
  reference window: core moves, editor power, the AI workflow, the
  visual git suite, intelligence features and terminal talk. Live in
  **Help → DS2 Cheat Sheet…** with a live filter box.
- **First-run checklist** (`checklist.py`) — a friendly starter
  checklist for brand-new workspaces.

## [1.6.0] — 2026-09-14 · beta · "the assistant gets superpowers"

### Added
- **AI quick actions** (`quick_actions.py`) — select code, get seven
  streamed superpowers: **Explain, Refactor, Add docstring, Write
  tests, Fix bugs, Add type hints, Optimize**. Answers stream into a
  themed result window; code blocks are detected and can be inserted
  below the cursor or swapped straight into the selection. A launcher
  menu (one palette entry) keeps all seven one click away. Worker
  threads + queue marshalling — the editor never blocks.
- **AI commit messages** (`commit_msg.py`) — a **✨ AI msg** chip in the
  Source Control panel drafts a Conventional Commits message from the
  staged diff (falls back to working tree + untracked files), streams
  it into the commit box, and never commits on its own. You edit
  everything before it lands.
- **AI review — gutter eyes** (`ai_lint.py`) — the brain reviews the
  whole file and returns structured findings (bug / smell / perf /
  clarity / praise); the findings panel maps severity to colour and
  jumps to the line on double-click. Robust JSON extraction survives
  chatty models.
- **Pair mode — plan, agree, build** (`pair.py`) — two-phase pair
  programming: the agent writes a numbered plan (no code), you edit or
  approve it, then execution runs through the real sandboxed
  AgentEngine with the same approval gates as the agent panel. Plan
  first kills the sprint-off-in-the-wrong-direction failure mode.
- **Editor power tools** (`macros.py`, `multicursor.py`,
  `snippets2.py`) — action-level macro recorder with cancellable
  playback and a persisted library; an emulated multi-caret engine
  (add-next / select-all occurrences, bottom-up stable edits); and a
  snippet engine with tabstops, `${name:default}` variables, builtin
  variables, four language packs and a user snippet store.

## [1.5.0] — 2026-09-14 · beta · "the assistant gets a memory"

### Added
- **Per-workspace agent memory** (`memory.py`) — the assistant now
  remembers between sessions. A JSON memory bank lives at
  ``<workspace>/.dxn1/memory.json`` (facts, preferences, a rolling
  summary); before every agent turn the bank is rendered into a compact
  block and injected into the system prompt, so the agent opens every
  conversation already knowing your stack, your quirks and your rules.
  **Say `remember: …` in the agent chat** to teach it instantly — no
  model call, instant confirmation. The **Agent Memory editor** (palette
  → *Agent memory*) gives the bank a face: add with Enter, delete per
  fact, import/export JSON, live path display.
- **Token usage dashboard** (`usagedash.py`) — know what your agents
  actually spend. Every engine turn records its token delta into a local
  ledger (`~/.dxn1-studio/usage.json`, trimmed at 5,000 events); the
  dashboard renders a **14-day bar chart**, **per-model share bars**,
  **per-workspace totals**, today's burn, generation counts and
  clearly-labeled **cost estimates** from published list prices
  (unknown models estimate at the table median). Export to CSV, or wipe
  the ledger with a two-click confirm. Zero network, zero accounts.
- **Agent engine integration** — `AgentEngine` injects the memory block
  at construction and reports token deltas after every run; both hooks
  are best-effort and can never break a chat.

### Changed
- Version bookkeeping: `APP_VERSION` is now **1.5.0**.

## [1.4.0] — 2026-09-14 · beta · "the visual git suite"

### Added
- **The visual diff viewer** (`diffview.py`) — a real diff window, not a
  wall of red and green text. Two panes side by side (or a unified patch
  view, one click away), **word-level highlighting** so only the words
  that actually changed glow, tinted gutters, live `+adds −dels ~mods`
  pills in the header, and hunk navigation (‹ › or F3 / Shift+F3) with a
  `3 / 17` counter that jumps and scrolls for you. A **Copy patch**
  button puts a clean unified diff on the clipboard. Powered by
  stdlib `difflib`, themed end-to-end, zero new dependencies.
- **The commit graph** (`gitgraph.py`) — your history as an interactive
  graph across **all branches**: one colored lane per branch line, real
  parent-based lane routing (merges fork out, first parents stay
  straight), hover cursor, click a commit and a detail card slides in
  with sha, author, parents and refs — plus **Copy sha**,
  **Diff vs parent** (opens the visual diff viewer) and
  **Checkout**. Filter box searches subjects, authors and shas live;
  decorated refs (`HEAD -> master`, `tag: v1.4.0`, `origin/…`) render
  beside their commits in the accent colour.
- **The branch manager** (`branches.py`) — create, checkout (double-click
  a branch), rename, delete, **merge** and **track** remote branches in
  one focused window. Ahead/behind badges come from
  `git for-each-ref` in a single call; the last commit subject shows
  beside every branch; tags live in a chip row (double-click to
  checkout). Deleting an unmerged branch takes a deliberate two-click
  confirm — and a second deliberate click to force.
- **Source control toolbar** — the git panel now carries **Graph** and
  **Branches** buttons, so the whole visual suite is one click from the
  sidebar.
- **Three new palette commands** — *Commit graph (all branches)*,
  *Branch manager — create / merge / cleanup* and *Diff workspace vs
  HEAD* (diffs the open file against its committed self). All wired
  defensively: if a DS2 module is missing, the palette pretends nothing
  happened.

### Changed
- Version bookkeeping: `APP_VERSION` is now **1.4.0** and the config
  default follows.

## [1.1.6] — 2026-09-14 · beta

### Fixed
- **Launch crash on fresh installs** — on machines where the splash
  artwork wasn't present, the boot card's shimmer animation touched a
  coordinate pair that only exists on the artwork path
  (`'Splash' object has no attribute 'track'`) and the studio died
  before its first frame. The flat fallback card now speaks the same
  coordinate language, the shimmer loop reads track bounds defensively,
  and — belt and braces — a broken splash can never again stop boot:
  any exception in the splash now falls through to the studio proper.
- **Installers now ship the splash art** — `splash_bg.png` was missing
  from both the `install.sh` asset list and the Update Portal's
  in-place refresh list, so streamed installs always ran without the
  animated boot card. Both lists now include it (and the portal
  auto-repairs the missing file on the next update).

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
