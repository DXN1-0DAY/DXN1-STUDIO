# DXN1 STUDIO 2 — Keybindings

Every binding works from the main window; editor-scope ones need the
code editor focused. The command palette (**Ctrl+K**) can trigger
all of this by name — the terminal (`help`) knows them as commands.

## Files & windows
| Keys | Action |
|---|---|
| `Ctrl+N` | New file |
| `Ctrl+O` | Open file… |
| `Ctrl+P` | Quick Open (fuzzy; also opens recent picker via `Ctrl+R`) |
| `Ctrl+R` | Recent files picker |
| `Ctrl+S` | Save |
| `Ctrl+W` | Close active tab |
| `Ctrl+Tab` | Next tab |
| `Ctrl+\` | Toggle split editor view |
| `Ctrl+,` | Settings |
| `Ctrl+Shift+V` | Paste from clipboard history |
| `F5` | Re-render (markdown preview) / run task context |
| `Esc` | Close most tool windows |

## Editing
| Keys | Action |
|---|---|
| `Ctrl+F` | Find (toggle find bar) |
| `Ctrl+G` | Go to line… |
| `Ctrl+D` | Duplicate line |
| `Ctrl+H` | Editor replace / history helper |
| `Ctrl+/` | Toggle comment |
| `Ctrl+Y` | Redo / line helper |
| `Alt+Up` / `Alt+Down` | Move line up / down |

## Bookmarks
| Keys | Action |
|---|---|
| `Ctrl+F2` | Toggle bookmark on the current line (also: gutter click) |
| `F2` / `Shift+F2` | Next / previous bookmark |

## Line tools (v2.12)
| Keys | Action |
|---|---|
| `Ctrl+Alt+S` | Sort lines A→Z (selection or whole buffer) |
| `Ctrl+Alt+D` | Deduplicate lines |
| `Ctrl+Alt+H` | Shuffle lines (seeded, deterministic) |
| `Ctrl+Alt+R` | Reverse lines |

## Modes
| Keys | Action |
|---|---|
| `Ctrl+K` | Command palette (everything above, by name) |
| `Ctrl+Alt+Z` | Toggle zen mode |

## Terminal commands (type `help` in the terminal)
`run`, `git …`, `db <file>`, `tree <dir>`, `hash <file>`,
`focus <min>`, `clip`, `md`, `color`, `rest`, `scribe <n>`,
`sort <mode>`, `todo`, `gen`, `env`, `jwt <token>`, `cron <expr>`,
`readability`, `palette`, `goto <line>`, `recent`, `split`, `zen`,
`update`, `hub`, `explain`
