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
