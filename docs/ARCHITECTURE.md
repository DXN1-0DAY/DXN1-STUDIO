# DS2 Architecture — how the studio fits together

> DXN1 STUDIO is a desktop IDE in pure Python + Tkinter. DS2 adds a
> constellation of feature modules around the same core. This document
> maps the terrain for contributors.

## The layer cake

```
┌──────────────────────────────────────────────────────────┐
│ app.py  — DXN1Studio: window, tabs, palette, menus, glue │
├──────────────────────────────────────────────────────────┤
│ panels: explorer (widgets.FileTree), gitpanel, search,   │
│         packages, agent.py (DXN1 Agents)                 │
├──────────────────────────────────────────────────────────┤
│ editor: widgets.CodeEditor (+ Highlighter, snippets2)    │
├──────────────────────────────────────────────────────────┤
│ brains: llm.py (Pollinations / GitHub Models / BYOK /    │
│         Kilo) → sandbox.AgentEngine (tool loop)          │
├──────────────────────────────────────────────────────────┤
│ DS2 feature modules (self-contained, defensively wired)  │
├──────────────────────────────────────────────────────────┤
│ theme.py — two palettes × accents (+ custom overrides)   │
│ config.py — one JSON file under ~/.dxn1-studio           │
└──────────────────────────────────────────────────────────┘
```

## DS2 module conventions

Every DS2 module follows the same contract, which is why the studio
stays stable even if one of them is missing:

1. **Self-contained** — one file, stdlib + Tk only, its own `_run_git`
   (or equivalent) helper, no imports from other DS2 modules at module
   level (lazy imports inside functions where needed).
2. **Defensively wired** — the entry point in `app.py` wraps the
   import + call in `try/except`; a broken feature can never break a
   session.
3. **Themed end-to-end** — everything reads from the resolved
   `Theme` object; no hardcoded colours outside documented tint pairs
   (see `diffview.TINTS`).
4. **No modal dialogs for danger** — two-click confirms
   (`delete` → `sure?` → 3-second auto-disarm).
5. **Threads never touch Tk** — worker threads push to a
   `queue.Queue`; the UI thread drains it via `after(45, …)`
   (see `quick_actions.StreamToText`).
6. **Analytics never cost a generation** — usage/memory failures are
   swallowed (`sandbox._record_usage`, `memory.recall_block`).

## Module map (DS2)

| Module | Talks to | Persists to |
|---|---|---|
| `diffview.py` | difflib, `git show` | — |
| `gitgraph.py` | `git log --all` | — |
| `branches.py` | `git for-each-ref`, `checkout`, `merge` | — |
| `memory.py` | `AgentEngine` (prompt injection) | `<workspace>/.dxn1/memory.json` |
| `usagedash.py` | wraps backend `chat`/`chat_stream` | `~/.dxn1-studio/usage.json` |
| `quick_actions.py` | `llm.build_backend` | — |
| `commit_msg.py` | `git diff --cached`, backend | — |
| `ai_lint.py` | backend, editor selection | — |
| `pair.py` | `sandbox.AgentEngine` (full tool loop) | — |
| `cheatsheet.py` | — | — |
| `workspace_stats.py` | `os.walk` (capped), `git rev-list` | — |
| `community_themes.py` | `theme.from_config` | `config.custom_theme` |
| `snippets2.py` | editor Text widget | `~/.dxn1-studio/snippets.json` |
| `macros.py` | editor actions | `~/.dxn1-studio/macros.json` |
| `multicursor.py` | editor Text widget | — |

## The theme engine

`theme.Theme` resolves one of two base palettes (`dark`/`light`) plus
an accent (6 colours). DS2 adds a third layer: `config.custom_theme`
overrides any subset of palette keys at resolution time
(`theme.from_config`). Resolution is defensive — unknown keys are
ignored, missing keys fall back — so community themes are data, not
code.

## Restart-driven settings

Theme changes (and a few others) restart the studio: set config,
`restart_requested = True`, destroy the root after 120 ms; the
launcher reboots the app. DS2's `_ds2_restart` mirrors `switch_theme`
exactly.

## Concurrency rules (for agents & contributors)

- Validate before every push: `python3 -m compileall -q dxn1_studio`
- Engine logic is testable headless (no Tk window needed): import the
  module and call its pure functions
- CI runs `compileall` + a headless boot smoke test on 3.8–3.13
