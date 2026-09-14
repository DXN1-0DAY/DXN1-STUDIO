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
| `Ctrl+Shift+D` | Duplicate line |
| `Ctrl+Shift+K` | Delete line |
| `Ctrl+H` | Editor replace / history helper |
| `Ctrl+/` | Toggle comment |
| `Ctrl+Y` | Redo / line helper |
| `Alt+Up` / `Alt+Down` | Move line up / down |
| `Ctrl++` / `Ctrl+-` | Editor text size |

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

## Tool windows (v2.48)
Every tool window prints an honest hint bar along its bottom edge —
a key appears there only if the code really binds it.
| Keys | Action |
|---|---|
| `F5` / `Ctrl+R` | Git Graph / Doctor: refresh / rerun |
| `+` / `−` | Git Graph: zoom rows in / out (`0` resets) |
| `Ctrl+F` | Activity: refocus the filter box |
| `Ctrl+L` | Activity: clear the receipt log |
| `Ctrl+Shift+C` | Doctor: copy the report |
| `F5` | Token usage: refresh |
| `Enter` | Bookmarks: jump · Recents/Outline: open/jump |
| `↑` / `↓` | Recents / Outline: move the selection |

## Tool windows (v2.49)
The second wave of door signs — six more windows learned keys, and
the hint bar still refuses to advertise anything the code does not
really bind.
| Keys | Action |
|---|---|
| `F3` / `Shift+F3` | Diff viewer: step changes |
| `Ctrl+U` | Diff viewer: split / unified view |
| `Ctrl+C` | Diff viewer: copy the clean patch |
| `Ctrl+1…5` | DevTools: switch tab (regex, JSON, text, time, color) |
| `Ctrl+Shift+C` | Text diff / Cheat sheet: copy |
| `Ctrl+S` | Cheat sheet: save the HTML |
| `Ctrl+C` / `Ctrl+E` | File stats: copy / export report |
| `F5` | File stats: rescan |
| `Ctrl+Return` | Scratchpad: stamp a new bullet |
| `Enter` / `Esc` | Writing-goal dialog: set / cancel |

## Chip menus from anywhere (v2.53)
The menus themselves joined the keyboard: every statusbar chip menu
(branch, deps, scribe, autosave) opens without the mouse, from the
palette, an accelerator or the terminal `chip <name>` verb. A
keyboard-opened menu keeps the grab exactly like a right-clicked one —
Enter/arrows/digits work immediately — and floats just above its chip.
| Keys | Action |
|---|---|
| `Ctrl+Alt+G` | branch chip menu — commit, push, pull, graph |
| `Ctrl+Alt+E` | deps chip menu — rescan, repair, watch |
| `Ctrl+Alt+W` | scribe chip menu — summary, goal, reset |
| `Ctrl+Alt+A` | autosave chip menu — snapshot, browse, toggle |
| `chip <name>` | terminal: `branch` · `deps` · `scribe` · `autosave` (aliases `git`/`env`/`writing`/`session`) |

## Chip menus (v2.52)
Right-click a statusbar chip (git, deps, scribe, session autosave) and
the menu answers to the keyboard: a real right-click keeps Tk's grab
while the menu is up — that grab is what routes keys to the posted
menu — and an unpost poller releases it the moment the menu closes and
hands the focus back. Up/Down/Return/Escape and first-letter jumping
stay Tk's own menu traversal; the rows below are wired on top. The
first activatable row wakes up active, so Enter takes it straight
away. Digits count commands, never separators.
| Keys | Action |
|---|---|
| `Home` / `End` | chip menus: first / last row |
| `1…9` | chip menus: run that row |
| `Up` / `Down` | move the selection (Tk's own traversal) |
| `Enter` | run the active row — the first row is active on open |
| `Esc` | close the menu, focus returns where it was |

## Tool windows (v2.50)
The third wave of door signs — ten more windows learned keys, and the
bar still refuses to advertise anything the code does not really
bind. Copy keys use `Ctrl+Shift+C` so text inputs keep their native
`Ctrl+C` selection copy.
| Keys | Action |
|---|---|
| `Ctrl+P` / `Ctrl+M` | XML bench: pretty / minify |
| `Ctrl+Shift+C` | XML bench: copy output · CSV lab: copy as TSV · Byte snoop: copy dump · Math pad: copy result · PassForge: copy · Unit converter: copy result · AI result window: copy answer |
| `Ctrl+R` | Unit converter: swap units |
| `F5` | PassForge: new password · Branches: refresh · Template gallery: re-filter · SQLite Lab: run query |
| `Return` | Math pad: evaluate · Branches: create the typed branch |
| `Ctrl+F` | Template gallery: jump to search |
| `Ctrl+R` / `Ctrl+Shift+I` | AI result window: replace selection / insert below |
| `1…7` | AI quick actions menu: run that action |

## Terminal commands (type `help` in the terminal)
`run`, `git …`, `db <file>`, `tree <dir>`, `hash <file>`,
`focus <min>`, `clip`, `md`, `color`, `rest`, `scribe <n>`,
`sort <mode>`, `todo`, `gen`, `env`, `jwt <token>`, `cron <expr>`,
`readability`, `palette`, `goto <line>`, `recent`, `split`, `zen`,
`update`, `hub`, `explain`
