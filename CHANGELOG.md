# Changelog

All notable changes to DXN1 STUDIO. Format based on
[Keep a Changelog](https://keepachangelog.com/); versioning is
`MAJOR.MINOR.PATCH` while in **beta**.

## [2.58.0] — 2026-09-15 · beta · "the pack gets a checkup" (validate before sharing + the terminal export verb)

### Added
- **The checkup core** — `langedit.check_mapping()` reads a
  key→value mapping the way an import WOULD and reports what it
  would meet before anything moves: non-string pairs (junk — an
  import skips them), whitespace values (empty — an import drops
  them back to English), keys the source never names (unknown —
  dead weight that ages into stale), and values that change length
  under `.lower()` (unsafe — the highlight contract, a property of
  the value, stale keys included), with real/seeds and
  `covered_pct`/`real_pct` riding along — the honest ledger
  computed for the thing in hand. `check_pack()` reviews an
  installed pack (what the runtime speaks); `check_pack_file()`
  reviews a file and answers with the error class for unreadable
  and non-dict ones, the same honesty `merge_pack_file` owes.
- **`lang check [code|file]`** — the pre-flight before sharing:
  one ledger line (`N pairs read · N real, N still English ·
  coverage N% · N% real`), every finding by name, then the verdict
  — `clean — nothing blocks an import`, or `N findings — a pack
  worth sharing is worth fixing`. A code reviews the installed
  pack, a path reviews the file itself; the bare verb reviews the
  current language (`en` has nothing to check); a seeded pack reads
  0% real with a pointer at `lang diff`. Unknown codes get the list
  plus the file hint.
- **`lang pack <code> [dest]`** — the terminal door for sharing:
  writes a pack's own strings as a user-pack-shaped JSON file
  (default `./<code>.json`, a directory dest lands `<code>.json`
  inside it) — what the desk imports back, and `lang check` on the
  file says what an import would meet.

### Changed
- **`lang pack` never overwrites** — an existing file is answered
  with `not overwriting` instead of being replaced: sharing should
  not destroy. `en` is refused (the source is not shared);
  unwritable paths report the OSError class honestly.

## [2.57.0] — 2026-09-15 · beta · "packs travel light" (export/import pack files + the audit prints every number)

### Added
- **Export pack** — the desk's working copy leaves as a JSON file
  shaped exactly like a user pack (desk button or Ctrl+E): what the
  desk exports the desk imports, and `set_language` would layer it
  over built-ins untouched. Sharing a pack is copying one file.
- **Import pack** — overlay a pack file onto the working copy in
  place (desk button or Ctrl+I): the desk's own exports, user
  packs, and `export_template` files alike. Valid pairs replace,
  empty values drop the key back to English, junk is skipped and
  counted, and nothing reaches the pack file until Save. Unreadable
  files answer `(-1, 0)` — reported honestly, never guessed.
- **The audit prints every number** — `lang audit` lines now carry
  the honest ledger's `real_pct` (`· N% real`), skipped for `en`
  and unreadable packs, with an explanation that names the flattery
  coverage is prone to; a seeded pack shows `100% — 0 missing,
  0 stale · 0% real` in one line.

### Changed
- **The preview's anatomy grew a buttons slice** — the common
  dialog buttons (Cancel · Copy · Export… · Import… · Refresh ·
  Close) render in the pack beside title bar, menu bar, toolbar,
  sidebar and find bar.

## [2.56.0] — 2026-09-15 · beta · "the desk grows eyes and tells no lies" (the honest ledger + a live preview of the studio in your pack)

### Added
- **The honest ledger** — `lang diff [code]` (`langedit.pack_diff()`):
  the coverage meter can flatter — a pack seeded from English and
  never edited shows 100% covered while every string still reads
  English. The diff splits a pack's own strings into **real**
  translations (they differ from English) and **untouched seeds**
  (byte-identical — wearing the pack, not speaking it), alongside
  missing / stale / unsafe, and prints `real_pct`: the number that
  cannot lie. Bare `lang diff` names the current language; `en` is
  refused ("it does not differ from itself"); unknown packs get the
  list; seeds are named (up to 8) where you can act on them.
- **Untouched filter** — the desk's fifth chip (All · **Untouched** ·
  Missing · Stale · Unsafe): the seeds reviewable in place. Edit one
  and it leaves the bucket at once; `pack_counts` carries the
  counter and the meter prints it (`… · N untouched`), so the header
  keeps telling the truth about seeds.
- **Pack preview** — the desk grows eyes (`langedit.PackPreview`,
  opened by the *Preview the studio* button or Ctrl+P): a slice of
  the studio UI — title bar, menu bar, toolbar, sidebar, find bar —
  rendered in the pack being edited, LIVE. Typing in the desk keeps
  the preview up keystroke for keystroke, so Menu ▸ Settings…
  becomes Ajustes… in context before saving. What the pack speaks
  wears the accent; English that shows through stays grey (exactly
  what `tr()` would answer). Closing the desk closes its eyes.
- **Ctrl+P in the desk** — preview as a real gesture, advertised in
  the desk's hint bar beside Ctrl+S; one press re-renders or raises
  the open preview instead of stacking windows.

## [2.55.0] — 2026-09-15 · beta · "the translator gets a desk" (a real editor for language packs + a launcher that grows to fit)

### Added
- **Translation desk** — a themed editor for any language pack: every
  English key beside its translation, ● translated / ○ missing /
  ✕ stale / ⚠ unsafe list markers, All · Missing · Stale · Unsafe
  filter chips over the key list plus a type-to-filter box, the EN
  source read-only above the translation box, and typing that commits
  into the working copy live so the header meter (covered/total,
  %, missing, stale, unsafe) never lies. Open it three ways:
  `lang edit [code]` (no code names the chooser), Settings ▸
  Look & feel ▸ *Edit a language pack…*, or the palette row.
- **Live highlight-safety warning** — the v2.54 audit's contract as
  you type: a string that changes length under `.lower()` (İ is the
  classic) gets an inline red warning, because every fuzzy highlight
  after it would shift.
- **Atomic user packs** — Save writes `~/.dxn1-studio/lang/<code>.json`
  via temp file + `os.replace`; empty translations mean "back to
  English" and are dropped; an active pack re-activates on save so
  edited strings go live at once. **Seed from English** fills every
  missing key as a starting point to edit down.
- **The chooser** — one honest row per pack with live coverage from
  `pack_stats`, or name a new code for a clean slate; junk codes get
  an inline reason and `en` is refused (the source of truth is
  translated FROM, not edited).

### Fixed
- **The AI quick-actions launcher no longer clips** — it asked for
  300px but long action labels and a full hint bar can request more;
  the geometry now grows to the real requested width.

## [2.54.0] — 2026-09-15 · beta · "every pack answers for itself" (the i18n fuzzy-highlight audit + a branch menu that hands you the command)

### Fixed
- **Fuzzy highlights can no longer drift** — the audit's root find:
  lowering a label can change its length ('İ'.lower() is 'i̇', two
  code points), and every fuzzy-match position after that character
  was computed against the shifted lowered string while the palette
  rendered the raw one — highlights lighting the wrong letters.
  `fuzzy.match()` now re-lowers per raw character when lengths
  disagree, so positions and `split_runs` runs stay aligned with the
  text actually rendered; the ASCII path is unchanged.

### Added
- **Pack audit** — `i18n.pack_stats()` reports every language pack
  honestly: coverage %, missing keys, stale keys, and
  highlight-safety (whether `.lower()` keeps each string's length —
  the property the fuzzy highlight assumes). User packs on disk are
  included; an unreadable pack reports itself instead of
  disappearing.
- **The `lang audit` verb** — the audit in the terminal, one line
  per pack with the NOT highlight-safe keys named; `lang` itself
  joined the terminal help table and the verbs browser (a
  documentation gap since the packs shipped).
- **Copy recovery command** — the branch chip menu's copy sibling,
  state-aware: diverged offers `git pull --rebase && git push`,
  ahead-only `git push`, behind-only `git pull`, in sync stays
  silent; clipboard + toast + terminal receipt, junk kinds ignored
  (the same honesty the deps menu's pip row set in v2.53).

## [2.53.0] — 2026-09-15 · beta · "the menus come to you" (every chip menu opens from the keyboard + a deps menu that hands you the fix)

### Added
- **Keyboard doors to every chip menu** — the four statusbar menus
  (branch, deps, scribe, autosave) stop living only under
  right-click: palette rows, real accelerators and a terminal verb
  all open them anchored just above their own chip, in the
  renderer's new "keyboard" mode. A palette row, an accelerator or a
  verb is a REAL user gesture, so the grab is kept (the v2.52
  lesson: that grab is what routes keys to the posted menu) and
  Enter/arrows/digits work immediately — the same contract a
  right-click gets, with the same unpost poller releasing it.
- **Real accelerators** — `Ctrl+Alt+G` branch menu, `Ctrl+Alt+E`
  deps menu, `Ctrl+Alt+W` scribe menu, `Ctrl+Alt+A` autosave menu;
  chosen to miss every existing `Ctrl+Alt+` binding (s/d/h/r/z),
  advertised by the palette rows and policed by the v2.47
  honest-keys audit.
- **The `chip <name>` verb** — `chip branch` (`git`), `chip deps`
  (`env`), `chip scribe` (`writing`), `chip autosave` (`session`);
  bare `chip` lists the four names, an unknown chip is told
  honestly, and every open logs its receipt ("Enter runs the
  highlighted row, Esc puts it away").
- **Copy pip install command** — when the deps chip is red, its
  menu gains a helper beside the repair row: one click puts a ready
  `pip install <pins>` line on the clipboard, pins resolved by
  `depcheck.suggested_pins` over the stored report's missing list
  (PIL → pillow, yaml → pyyaml), toast + terminal receipt confirm,
  and with nothing missing the answer is an honest info card.
- **Tooltips name the key** — all four chip tooltips end with their
  accelerator ("right-click for actions · Ctrl+Alt+G"), so the
  keyboard path is discoverable at the point of use.

### Changed
- `_render_chip_menu()` names its opening modes: "gesture" (pointer,
  grab kept), "program" (`event=None`, the tests' seam — grab
  released at once, untouched) and "keyboard" (a real non-pointer
  gesture — grab kept, anchored at the chip). Same poller, same
  dismissal, same cleanup contract in every mode.
- `tests/test_ds2.py` gained the `test_menu_reach` group (the doors,
  the kept grab, the clipboard truth, the verb, the settings-search
  pin) and `scripts/smoke_v530.py` drives the round through the real
  studio (30 checks).

## [2.52.0] — 2026-09-15 · beta · "the menus learn the keyboard" (chip menus answer to keys + the git menu wears its divergence + a real snapshot-interval picker)

### Added
- **Keyboard-ready chip menus** — right-click any statusbar chip (git,
  deps, scribe, session autosave) and the menu now answers to the
  keyboard: the first activatable row wakes up active so Enter takes
  it straight away, Up/Down walk the rows, Escape closes, and the
  menu answers to `Home`/`End` and digits `1…9` on top of Tk's own
  traversal (digits count commands, never separators). A probe found
  the root cause first: `tk_popup` takes an X grab and that grab is
  what routes keys to the posted menu — the renderer had been
  releasing it immediately since v2.42, so every chip menu was
  mouse-only and Tk's own traversal starved.
- **The unpost poller** — the grab is released the moment the menu
  unposts (a 40ms watcher) and the focus hands back to wherever it
  was; the intent is recorded on the menu (`_ds2_focus_back`) and the
  rows are introspectable (`_ds2_rows`), same spirit as v2.50's
  `bar.pairs`.
- **Git menu wears its divergence** — the sync rows take the branch's
  severity: red `Push to origin` / `Pull from upstream` when the
  branch diverged, amber when one plain push or pull would settle it,
  silent when already in sync — the same language the deps menu
  learned in v2.51.
- **Snapshot-interval picker** — Settings → Activity gains "Hours
  between snapshots": a themed spinbox (1–168) that reads the saved
  value, clamps on save, and lands junk on 24; the engine honors it
  on every half-hourly beat, and bare `activity auto` now names the
  interval in its report.

### Fixed
- **A grab left behind** — Tk's grab state is per-DISPLAY and
  process-wide: a menu left posted with its grab at teardown kept
  swallowing pointer events from whatever ran next (found by the
  pytest interps). Programmatic opens (no pointer gesture) release
  the grab at once, the poller releases it on unpost, and the
  studio's quit path puts the menu away before the root goes down
  (`_dismiss_chip_menu`).

## [2.51.0] — 2026-09-15 · beta · "the diary writes itself" (nightly activity auto-snapshot + a menu that wears its severity)

### Added
- **Nightly receipts auto-snapshot** — when the gate is on, the whole
  activity diary lands in `<config>/exports/activity-auto-<stamp>.json`
  every 24 hours: checked politely 8 seconds after boot and re-armed
  every half hour (the clock decides, not the session count), written
  atomically in ring order, round-tripping through `load_json`, with
  the last 14 snapshots kept and older ones pruned. The gate ships
  OFF — nothing writes behind your back until you ask.
- **`activity snap`** — write a snapshot now, gate or no gate: the
  same code path the nightly clock uses, so the verb keeps the
  machinery honest. **`activity auto on|off`** flips the gate from
  the terminal; bare `activity auto` reports the state.
- **Settings: Activity section** — the gate as a checkbox, the
  retention rule and the terminal verbs named underneath, persisted
  with every other setting.
- **The deps menu wears its severity** — the shared chip-menu
  renderer accepts a 4th row element (foreground): the deps menu
  paints `Queue deps fix (N missing)` and the fresh rescan with the
  chip's red when imports are missing, and its rescans with the
  chip's amber when the cache drifted. The menu and the chip finally
  tell the same story in the same colors.

### Changed
- The activity help rows grew the two new verbs; the deps repair row
  now names its number ("2 missing") instead of asking you to guess.

## [2.50.0] — 2026-09-15 · beta · "every sign now hangs on a real key" (hint bars wave 3)

### Added
- **Ten more windows carry honest hint bars** — branches, template
  gallery, SQLite Lab, XML bench, CSV lab, unit converter, Byte
  snoop, Math pad, PassForge and both AI quick-action surfaces join
  the family; every chip is still verified against a real binding
  (`accel_pattern` + `tree_bound`) before it is allowed on the bar,
  and bars now expose `bar.pairs` so their promises are
  introspectable by tests instead of scraped from labels.
- **The five converter-lab windows learned keys** — XML bench
  (`Ctrl+P` pretty, `Ctrl+M` minify, `Ctrl+Shift+C` copy output),
  CSV lab (`Ctrl+Shift+C` copy as TSV), Byte snoop (`Ctrl+Shift+C`
  copy dump), PassForge (`F5` new password, `Ctrl+Shift+C` copy) and
  the unit converter (`Ctrl+R` swap units, `Ctrl+Shift+C` copy
  result) answered only to the mouse before this wave; the keys
  came first, the sign second.
- **AI quick actions go keyboard-native** — the streaming result
  window copies its answer (`Ctrl+Shift+C`) and, when the action ran
  on a code selection, replaces that selection (`Ctrl+R`) or inserts
  below (`Ctrl+Shift+I`), with the bar honestly showing those two
  chips only when the verbs exist; the launcher menu binds each
  row's position so `1…7` runs that action straight from the menu.
- **Gallery search jump** — the template gallery jumps to its search
  box (`Ctrl+F`) and re-applies the filter (`F5`); branches gains
  `F5` refresh beside its existing Esc/Return; math pad's entry
  Return and SQLite Lab's `F5` run-query are finally advertised now
  that a bar can vouch for them.

### Changed
- **Copy keys use the canonical spelling** — `Ctrl+Shift+C` arrives
  at Tk as keysym `C`, so the window binds `<Control-C>`: the same
  pattern wave 2 pinned for the translator. A deliberate side effect
  is that text inputs keep their native `Ctrl+C` selection copy —
  the unshifted `c` never matches the uppercase keysym — while the
  hint text still says `Ctrl+Shift+C`, because that is what the
  human presses and the verifier checks the binding the press
  actually hits.

## [2.49.0] — 2026-09-15 · beta · "every door gets its sign" (hint bars wave 2 + two latent crash fixes)

### Fixed
- **The diff viewer opens again** — `DiffViewer.__init__` had called
  `self._build_footer()` since v1.4 but the method was never defined:
  every diff window died with AttributeError the moment it opened.
  The pure diff engine below it was fully tested, the window itself
  had zero coverage, and the crash was never noticed. The footer now
  exists and carries its weight: a one-line verdict of what changed
  (`before → after · 14 rows · +4 −2 ~1 · 3 changed hunks`), and the
  header hunk counter echoes "patch copied" when the patch is copied.
- **The git graph finally draws its diagonals** — `_draw()` referenced
  `lane_of` on every parent edge, but that map was only ever defined
  inside `assign_lanes()`: any repository with ≥ 2 commits died
  mid-draw with NameError, leaving a partial graph (or raising on a
  direct call). The bug shipped with v1.4 and survived 57 tags because
  every prior check drove the graph **vacuously** — the 80 ms refresh
  timer had not fired yet, so `rows` was still empty and the broken
  code path never ran while the assertions counted the one "No
  commits yet" text as painted rows. `_draw()` now rebuilds the map
  from its own rows, and the wave-2 tests/smoke drive a real merge
  topology (4 commits, 2 parent edges, 27+ canvas items) so the
  vacuous pass can never repeat.
- **Off-screen tooltips cannot silently die** — a negative cursor
  position produced `"+-x+y"` geometry, which Tk rejects; the tooltip
  position is clamped to ≥ 0 so the hover whisper survives any
  screen arrangement (and the never-raise contract stays honest).

### Added
- **Hint bars wave 2** — six more windows carry the honest door sign,
  and most gained real keys to advertise:
  - **Diff viewer**: `F3` / `Shift+F3` step changes, `Ctrl+U` flips
    split/unified view, `Ctrl+C` copies the clean patch — the
    navigation the ‹ › buttons already offered is keyboard-native,
    and the bar lists exactly what is bound.
  - **Developer tools**: the five tabs answer to `Ctrl+1…5`
    (`select_tab()` never raises on a stray index) — regex, JSON,
    text, time and color are one keystroke apart, and the bar shows
    a chip per tab.
  - **File statistics**: `Ctrl+C` copies the report, `Ctrl+E` exports
    the markdown, `F5` rescans — the three mouse buttons gained
    keyboard paths; the Esc chip honestly reads "clear filter" (what
    it really does) instead of the default "close".
  - **Text diff**: `Ctrl+Shift+C` copies the diff, `Esc` closes —
    chosen over `Ctrl+C` so selecting text in the panes keeps its
    native meaning.
  - **Cheat sheet**: `Ctrl+Shift+C` copies the HTML, `Ctrl+S` opens
    Save-as, `Esc` closes.
  - **Scratchpad**: the hand-written "- Ctrl+Enter: stamp…" label is
    replaced by a verified hint bar — the same promise, now checked
    against the real bindings instead of trusted.
  - **Writing-goal dialog**: the standard bar whispers `Enter set
    goal · Esc close`, both really bound.
- **Lane hover tooltip** — hovering a graph row shows the whole
  truth: the full commit subject (the canvas row truncates at 72
  characters; the tooltip never does), every ref on the commit, and
  the author · date line. It hides on off-row hover, on leave and on
  click; the graph's hint bar note advertises it ("hover a commit
  for the full message").
- **Keybindings doc — Tool windows (v2.49)** — the second wave's
  keys are documented with the same rule stated out loud, and the
  test suite pins every new row against the source.

## [2.48.0] — 2026-09-15 · beta · "the way out is written on the door" (honest hint bars + git-graph zoom)

### Added
- **Honest hint bars** — a new `dxn1_studio/hints.py` module prints
  a themed bar along the bottom edge of the studio's tool windows
  listing the keys that window really answers to. The contract is
  the v2.47 honest-keys one, extended to every window: a key hint is
  rendered only if its exact Tk event pattern (via `accel_pattern`)
  is genuinely bound on the window or any descendant; the `Esc`
  chip appears only when `<Escape>` is really bound; an unbacked
  hint is dropped and reported in `dropped_hints` instead of being
  shown as a lie; mouse notes ("click a row to copy") describe the
  mouse, so they can never lie about keys. Verification runs on the
  first idle moment after construction (bindings made after the bar
  is created are still counted) and can be re-run via `refresh()`;
  a bar that would render nothing hides itself, and a bar on a
  dying window quietly disappears — a hint bar never raises.
- **Eight windows carry the door sign** — the git graph
  (`F5 refresh · +/− zoom · 0 reset · Esc close · click a commit
  for details`), the Activity window (`Ctrl+F filter · Ctrl+L
  clear · Esc close · click a row to copy` — its first keyboard
  bindings at all), bookmarks (`Enter jump · double-click a row`),
  the recents picker and the outline/symbol picker (`↑↓ move ·
  Enter open/jump · type to filter`), the environment doctor (`F5`
  or `Ctrl+R` rerun · `Ctrl+Shift+C` copy report · `Esc close`),
  token usage (`F5 refresh · Esc close`) and What's New (`Esc
  close · click a version to read its notes`).
- **Git-graph zoom** — `+` / `−` step a real row-density zoom
  (0.5×–3.0×, `0` resets): rows, lanes, dots, edges and click
  hit-testing all rescale together; `F5` / `Ctrl+R` refresh the
  graph from the keyboard. The canvas answers the way the bar
  advertises, because the bar verified the bindings before
  painting them.
- **Keybindings doc — Tool windows section** — `docs/KEYBINDINGS.md`
  gained the v2.48 window keys and now states the rule out loud:
  a key appears in a hint bar only if the code really binds it.

### Fixed
- `accel_pattern("+")` translated a bare plus key to `""` (the
  split logic ate it) — bare `+` / `-` now translate to
  `<plus>` / `<minus>`; the v2.48 smoke pins all four spellings
  (`+`, `-`, `Ctrl++`, `Ctrl+-`) so the graph's zoom hints can
  never silently vanish.

## [2.47.0] — 2026-09-15 · beta · "honest keys and a quieter voice" (accelerator audit + toast mute + export formats)

### Added
- **Honest keys** — a real accelerator audit: every keybinding the
  command palette advertises is translated (`accel_pattern`) into
  the exact Tk event pattern and verified against the bindings the
  code actually has, so a label can never drift from the truth
  again. `looks_like_accel` keeps the audit honest about what is a
  claim ("Ctrl+S", "F5", "Enter") and what is not ("DS2" category
  tags, "line 42" symbol positions). The chip-menu renderer accepts
  optional accelerator columns — the git menu's *Commit staged…*
  now advertises `Enter`, which the commit box really honors — and
  `docs/KEYBINDINGS.md` was corrected to match the code
  (`Ctrl+Shift+D` duplicate, `Ctrl+Shift+K` delete line,
  `Ctrl++`/`Ctrl+-` text size).
- **Toast mute (per kind)** — a new searchable *Toasts* settings
  section: mute info, success or error cards separately. A muted
  kind keeps its receipt in the Activity log and skips only the
  3.4-second card — the log remembers, the screen stays quiet.
- **Export formats** — `activity export json [path]` and
  `activity export csv [path]` write the receipts as a loadable
  JSON snapshot or a quoted CSV sheet; the window's Save-as…
  follows the typed extension (`.json` / `.csv` / text diary), an
  explicit format argument overrides the extension, and the
  acknowledgement toast names the format it chose.

### Changed
- `export_csv()` / `export_json()` / `export_to()` join the pure
  engine lane in `activity.py` (the text `export_file` remains);
  the smoke suite count grew to 20 suites (527 checks), the unit
  groups to 91 — including `test_honest_keys`, the audit itself.

## [2.46.0] — 2026-09-15 · beta · "the receipts go where you send them" (activity export + kind filters)

### Added
- **Kind filters in the Activity window** — a row of colored dots
  (● success / ● error / ● info) below the search box toggles each
  kind on or off; hidden kinds turn hollow and muted, the count
  label follows the view honestly, and a kind the studio cannot
  name *always* shows — you cannot re-show what you cannot name,
  so a filter can never make receipts silently vanish.
- **Copy all** — one header click puts the whole ring on the
  clipboard as a chronological diary (oldest first, one receipt
  per line: `[YYYY-MM-DD HH:MM:SS] kind    message`), whatever the
  filter is showing. Long copies acknowledge as "Copied N
  characters" instead of shouting the whole text back in a toast.
- **Save as file…** — a save dialog (seeded with the studio's
  config dir, timestamped default name) writes the same diary to
  any path: atomic write (tmp + `os.replace`, the house pattern), a
  cancelled dialog is an honest no-op, and the app acknowledges the
  saved path in a toast and a terminal line.
- **Export verbs** — `activity copy` (diary → clipboard) and
  `activity export [path]` (diary → file, default beside
  `activity.json`); a nonsense sub-command gets an honest `try:`
  hint. `help` documents both rows, and the command palette gained
  "Activity — export receipts to a file…".

### Changed
- `ActivityLog.filtered()` accepts an optional `kinds` narrowing
  (engine-level, shared with the window); `export_text()` /
  `export_file()` / `stamp_full()` join the pure engine lane; the
  window opener grew `export_dir` / `on_export` seams. Smoke grew a
  22-check suite (`smoke_v460.py`); the unit group behind the
  activity lane covers the export engine, the filter rule and the
  new verbs end to end.

## [2.45.0] — 2026-09-15 · beta · "the receipts survive the night" (persistent activity log + since last time)

### Added
- **Persistent activity log** — the ring now lives on disk beside
  `config.json` (`activity.json`): every toast re-writes it
  atomically (tmp + `os.replace`, the same pattern `Config.save`
  uses, so a crash mid-write can never tear the file), and boot
  reloads whatever the last session whispered. A corrupt or torn
  file falls back to a fresh ring honestly — lost receipts are
  never fatal.
- **"Since last time" divider** — entries from a previous session
  are marked at load and render under a muted divider in the
  Activity window: this session's whispers on top, the older
  receipts below, one glance to tell them apart.
- **Relative stamps** — rows now show "just now", "2m ago",
  "3h ago", "5d ago" instead of clock times; a future timestamp
  renders as an honest blank.
- **Clear persists** — wiping the slate through the window fires
  the app's `on_change`, so the file on disk agrees immediately
  (no resurrected receipts on the next boot).

### Changed
- The Activity window's `open_activity()` accepts an optional
  `on_change` callback (fired after Clear); `open_activity`'s
  existing callers are unaffected.

## [2.44.0] — 2026-09-15 · beta · "the studio keeps its receipts" (activity log + scribe goal dialog)

### Added
- **Activity log** — toasts auto-dismissed after ~3.4 seconds and
  were gone forever. Every notification is now archived in a capped
  ring buffer (100 events, newest first) with its kind (info /
  success / error) and timestamp, and opens in one themed,
  searchable window: live substring filter with an honest empty
  state, kind-colored dots, click a row to copy the message,
  Clear wipes the slate.
- **Terminal verb `activity`** (alias `notifications`) — opens the
  Activity window; `help activity` explains it; the verbs browser
  lists it.
- **Palette row** — *Activity — recent notifications…*.
- **Scribe goal dialog** — the ✎ chip menu's *Set writing goal…*
  row now opens a themed dialog prefilled with the current goal:
  type the count, press Set or Enter. Invalid input gets an inline
  honest error and the dialog stays open; Escape cancels without
  applying. Applying updates the chip, persists
  `scribe_goal_words`, and confirms with a toast + terminal line.

### Changed
- **Nothing fires by accident, upgraded** — the goal row used to
  prefill the terminal; now an explicit Set gesture commits the
  goal. The terminal verb `scribe <words>` keeps working exactly
  as before.

## [2.43.0] — 2026-09-15 · beta · "the whole family is chipped in" (scribe + autosave menus, Commit staged…)

### Added
- **Scribe chip context menu** — right-click the ✎ writing chip for
  the lane's actions in one themed menu: **Session summary** (the
  same toast the click gives — words, current/peak wpm, elapsed
  time, goal %), **Set writing goal…** (queues `scribe goal ` in
  the terminal input — type the number, press Enter; the same
  one-gesture contract as the deps repair row, nothing fires by
  accident) and **Reset session meter** (words, wpm and the elapsed
  clock restart from now, the goal survives, the chip repaints and
  a toast confirms).
- **Session-autosave chip context menu** — right-click the ◐ session
  chip: **Snapshot session now** (the same path as the click — tabs
  and cursor spots on disk with visible feedback), **Browse
  snapshots…** (the existing snapshot browser, one menu row away)
  and **Autosave on/off**.
- **Live autosave toggle** — the menu's switch flips
  `session_autosave` immediately; the 60s autosave loop reads the
  config every tick, so the change lands on its next beat. A toast
  and a terminal line say which way it went.
- **Branch chip menu: Commit staged…** — one row opens the Source
  Control panel and puts the cursor straight into the commit
  message box (`gitpanel.focus_message()`; the panel's own
  FocusIn binding clears the placeholder by itself) — stage, type,
  Enter.
- **Palette rows** — *Session — snapshot tabs now…* and *Scribe —
  reset the writing meter…* join the command palette.

### Changed
- **Every chip has a menu, for real** — all four statusbar chips
  (branch, deps, session autosave, scribe) now bind right-click,
  and every tooltip advertises it: what the chip is, what a click
  does, that a right-click opens the lane's actions. One shared
  themed renderer drives all four menus.

## [2.42.0] — 2026-09-15 · beta · "every chip has a menu" (deps menu + AI draft + push/pull)

### Added
- **Deps chip context menu** — right-click the dependency chip for
  the lane's actions in one themed menu: Rescan deps, Fresh rescan
  (bypass cache), Deps watch on/off, Rescan chip. The menu is
  honest per state: the **Queue deps fix** repair row appears only
  when the last report actually found missing imports (the chip is
  red) — it queues `deps fix` in the terminal input exactly like
  the red chip click, and Enter still runs it.
- **Branch chip menu: Draft AI commit message** — one menu row
  brings the Source Control panel forward and fires its ✨ AI
  helper: the panel reads the diff, drafts a Conventional Commits
  message, and the user edits/commits as always (the panel guards
  repo and brain state itself — the menu only opens the door).
- **Branch chip menu: Push to origin / Pull from upstream** — the
  two everyday git verbs join the menu, routed through the visible
  terminal runner so output, errors and credentials stay exactly
  where they always are.

### Changed
- **One shared popup renderer** — `_render_chip_menu` now drives
  every statusbar chip menu (branch + deps): one themed Menu
  builder, `(label, command)` rows, `("---", None)` separators,
  cursor-anchored popup, best-effort by contract. Both menus never
  raise.
- Chip tooltips now advertise the right-click ("click opens the
  panel, right-click for actions") instead of describing only the
  click gesture.

## [2.41.0] — 2026-09-15 · beta · "one gesture to repair" (chip gestures + context menu + settings)

### Added
- **One-gesture repair** — clicking the deps chip while it is RED
  (imports missing from requirements) now rescans *and* queues
  `deps fix` in the terminal input with a one-line hint: press Enter
  to pin the missing imports. Nothing fires by accident — Enter
  stays the trigger. The amber click stays a plain rescan.
- **`deps fix` heals its own cache** — after pinning, the workspace
  is re-scanned and re-stored immediately, so the cache and the
  watch chip never lie about a workspace the studio just fixed; a
  rare pin that doesn't satisfy its import is called out honestly
  ("still missing after the pin").
- **Branch chip context menu** — right-click the git chip for the
  lane's actions in one themed menu: Open Source Control, Commit
  graph, Stage all changes (routes through the visible terminal
  runner), Copy branch name (clipboard + toast), Rescan. Repo rows
  appear only when the chip is actually watching a repository — a
  plain folder gets the honest two-row menu.
- **Settings: "Statusbar watch chips"** — the Dependency watch and
  Source control watch toggles now live in the Settings dialog too
  (alongside the `deps watch` / `git watch` verbs); saving redraws
  both chips immediately.

## [2.40.0] — 2026-09-15 · beta · "the lanes have eyes" (git lane chip + deps severity)

### Added
- **Git lane chip** — the statusbar now has a branch indicator that
  earns its place: the branch name sits quietly in muted text while
  everything is committed and in sync, and turns **amber and bold —
  `branch ●N`** the moment N files wait to be committed (staged,
  unstaged and untracked all count). `↑N` / `↓K` arrows ride along
  when the branch diverges from the locally-known upstream — honest
  by design: git only knows what it has fetched, so the chip never
  silently networks; `behind` appears after a fetch, `ahead` the
  moment you commit. Plain folders and non-repos stay silent — no
  nagging for workspaces that are not repositories.
- **One probe, both lanes** — the drift poll that watches deps every
  30 s now watches the git lane in the same pass; each chip probes
  at most once per 3 s (`git status --porcelain -b` is one cheap
  subprocess), forced redraws on saves, clicks and boot. Clicking
  the git chip opens Source Control — the chip points at work, the
  panel is where it gets done.
- **`git watch [on|off]`** — bare `git watch` flips the branch chip,
  `on`/`off` are explicit, junk gets an honest usage line, and the
  preference persists (`git_watch`, default on). The intercept is
  prefix-exact: plain `git <args>` commands still pass through to
  the shell untouched. Palette entry: *Source control watch on/off…*;
  `TERMINAL_HELP` and the verbs browser gained the row.
- **Deps severity** — the dependency watch chip no longer says "ok"
  when the cached report found unpinned imports: a cached workspace
  whose imports are missing from requirements lights the chip **red
  — `● deps N missing`**. Amber means drift (rescan to learn), red
  means missing (run `deps fix`); `depcheck.cache_state()` now
  returns the stored report's missing list alongside the state.
  The `deps watch` usage line explains both severities.
- **Chip tooltips** — hovering any statusbar chip (git, deps,
  session autosave, scribe) shows a quiet themed tooltip explaining
  what it is and what clicking it does.

### Changed
- v2.39's chip flow expectations updated to the honest ladder: a
  drift-click rescan with unpinned imports now shows red, not a
  fake "ok" (tests/smoke assert the full
  amber → red → pinned → ok sequence).

## [2.39.0] — 2026-09-15 · beta · "the drift you can see" (deps watch chip + terminal verbs browser)

### Added
- **Dependency watch chip** — the statusbar now watches your deps
  for you: a quiet `deps ok` sits next to the session chip and turns
  **amber — `● deps drift`** the moment the workspace fingerprint
  moves past the last deps report. A file saved in the editor, a
  module dropped in from outside the studio, a requirements edit —
  the chip lights up without running anything. The probe is honest
  and cheap: `depcheck.cache_state()` compares the stored cache
  signature only (three states: `absent` / `cached` / `stale`), it
  never rescans, it is throttled to one pass per 3 s, and a 30 s
  poll catches drift while you are mid-thought. Click the chip to
  rescan (a drifted workspace is a cache miss, so this is a real
  scan) and it calms back down.
- **`deps watch [on|off]`** — bare `deps watch` flips the chip,
  `on`/`off` are explicit, junk arguments get an honest usage line,
  and the preference persists (`deps_watch`, default on). The
  `TERMINAL_HELP` deps row now reads `(fix / fresh / watch)`.
- **Terminal verbs browser** — `verbs`, the Workshop ▸ *Terminal
  Verbs* entry and the palette's *Terminal verbs…* open a themed,
  searchable window listing every verb the terminal speaks (55+
  after merging the `git` continuation line back into one honest
  description). Live substring filter over verb + description (the
  same first pass `help <q>` uses), a count label that follows the
  filter, mouse-wheel scrolling and an honest "nothing matches —
  try a shorter filter" empty state. One data source: `verbs.verb_rows()`
  flattens the same `TERMINAL_HELP` tuple behind `help` and the cheat
  sheet, so the three views can never disagree. Clicking a row drops
  the verb into the terminal input and focuses it — Enter runs it;
  nothing fires by accident.

### Changed
- Saving a file now nudges the watch chip (throttled), `_run_depcheck`
  re-anchors the chip after every `deps` / `deps fresh` / `deps fix`
  run, and boot draws it once alongside the other statusbar chips.
- Architecture doc: 85 modules, 85 pytest groups, smoke_v390 row;
  FEATURES gains the watch-chip rows and a Terminal Verbs Browser
  section.

### Tests
- pytest: `test_deps_watch` (cache_state matrix, chip text/colour
  states, click-to-rescan, toggle persistence, usage line) and
  `test_verbs_window` (row flattening + git merge + uniqueness,
  filter honesty, palette entries, `verbs` verb opens the window,
  live filter + empty state via the new `search_entry`/`refilter`
  hooks, click-prefills the terminal input) → 85 groups.
- smoke_v390: 28 live checks, all green under Xvfb.

## [2.38.0] — 2026-09-15 · beta · "instant answers, honest invalidation" (deps cache + commands verb)

### Added
- **deps per-workspace cache** — repeat `deps` reports are instant:
  the verdict is stored in `<workspace>/.dxn1/depcheck_cache.json`
  with a change-sensitive fingerprint (every scanned `*.py` and
  requirements file's `mtime_ns` + size, plus the workspace-root
  listing, since a new top-level module changes the local-module
  set). Any edit invalidates honestly and a real scan re-stores; a
  corrupt cache file falls back to the scan path; the cache's own
  `.dxn1` write can never self-invalidate the fingerprint it lives
  in. A cached report says so — `deps: served from cache (workspace
  unchanged) — `deps fresh` rescans`.
- **`deps fresh`** — bypass the cache, rescan, re-store. `deps fix`
  always works from a fresh scan (a cached report must never decide
  what gets pinned).
- **`commands [filter]`** — every command the Ctrl+K palette offers
  (109+) listed in the terminal with its shortcut; a filter tail
  narrows by substring first, then the closest fuzzy hits
  (`commands line`, `commands sve fil` → *Save file*), capped at 24
  rows with an honest "+N more — narrow the filter".
- **Palette help fallback** — `help <query>` now searches the
  palette's own registry when no terminal row matches:
  `help duplicate` answers `palette: Duplicate line —
  Ctrl+Shift+D`. The palette's vocabulary is discoverable without
  opening the palette.

## [2.37.0] — 2026-09-14 · beta · "deps that fix themselves" (deps fix + help <verb>)

### Added
- **`deps fix`** — the dependency cross-check can now heal the file
  it audits: missing imports are appended to `requirements*.txt` as
  canonical PEP 503 pins (via the reverse alias table — `import
  yaml` pins **pyyaml**, `from PIL import …` pins **pillow**,
  `import cv2` pins **opencv-python**). The append is atomic
  (temp-file + replace), marked with a `# added by deps on <date>`
  comment, dedupes against everything already present, and creates
  `requirements.txt` on demand when the workspace has none. A second
  run is always an honest no-op.
- **`help <verb>`** — the terminal answers per-verb questions:
  exact command match first, then substring over commands and
  descriptions, then the three closest fuzzy hits (so `help dps`
  still finds `deps`); an unknown verb gets an honest "No help for"
  line. The bare `help` listing is unchanged.
- Workshop ▸ *Dependency Check — imports vs requirements…* menu
  entry, next to Session Restore and Save Session Now.

## [2.36.0] — 2026-09-14 · beta · "keeps you current" (update heartbeat + deps cross-check)

### Added
- **Update heartbeat** — update checks are no longer boot-only: a
  quiet after-loop re-asks GitHub while the studio runs (default
  hourly, Settings ▸ *Update heartbeat* 15–360 min, clamped
  15 min..6 h). The polite skip memory applies — a release you
  declined stays silent; a newer one nags.
- **`deps` — the dependency cross-check** (new `depcheck.py`): an
  AST walk over the workspace's `*.py` files vs `requirements*.txt`
  (plus `pyproject.toml [project] dependencies`) that reports
  **imported but never required** and **required but never
  imported**. Pure static analysis — the project's code is never
  executed. A table of famous distribution↔import pairs
  (Pillow→PIL, beautifulsoup4→bs4, PyYAML→yaml, …) covers the
  classic mapping traps; unknown pairs fall back to PEP 503
  normalisation and the report honestly flags best-effort caveats.
  Run it from the terminal (`deps`), the palette, or with no
  requirements file at all — you get a notice, not an error.
- **`whatsnew` terminal verb** — the What's New release-rail viewer
  opens on demand (`whatsnew` / `whats new` / `changelog`), next to
  the Help menu entry and the once-per-version auto-open.
- Palette commands for both: *Dependency Check — imports vs
  requirements…* and *What's New — release notes digest…*.
- Settings ▸ *Check for updates* text now tells the truth about the
  heartbeat and the skip memory.

## [2.35.0] — 2026-09-14 · beta · "the boot path that never lies" (engine-first restore + polite updater)

### Changed
- **Engine-first boot restore** — reopening a workspace now tries the
  crash-safe engine snapshot BEFORE the legacy clean-exit record.
  Every clean exit refreshes the snapshot and the 60s autosave keeps
  it warm in between, so it is always at least as fresh as the
  `session_tabs` entry: a hard crash now costs one minute of open
  tabs instead of resurrecting a week-old clean-exit tab set. The
  legacy record stays as the fallback for pre-v2.30 installs, and
  `_restore_engine_session` now reports whether it actually restored
  anything (True/False).
- **Atomic config saves** — `Config.save()` writes to a temp file and
  `os.replace`s it into place: a crash mid-save can no longer tear
  config.json in half (which also silently destroyed the session
  records the crash recovery depends on).

### Added
- **The polite updater** — "I'll stay on this version" on the update
  portal now remembers that exact release (`updater_skip_version`):
  the automatic boot check goes quiet for it and logs a one-line
  "run `update` to reconsider" in the terminal instead of forcing the
  full-screen portal on you every launch. Manual checks (menu,
  palette, terminal `update`) always open the portal, and any newer
  release than the skipped one nags again, as it should. The offer
  screen now says exactly that.

## [2.34.0] — 2026-09-14 · beta · "stream the difference" (delta updates)

### Added
- **Delta updates** — the update portal now fetches `HASHES.txt`
  (sha256 of all 94 shipped files, sha256sum format) before touching
  anything, hashes the local install and downloads **only the files
  that actually changed or are missing**. A one-module fix no longer
  re-streams the whole IDE; byte-identical files are skipped. If
  HASHES.txt is unreachable the classic full download runs exactly as
  before — the delta pass is an optimization, never a risk.
- **Installer integrity gate** — `install.sh` verifies every
  downloaded module's sha256 against HASHES.txt: a truncated or
  corrupted download now fails the install with a clear message
  instead of shipping a broken IDE.
- **HASHES.txt + generator** — `scripts/gen_hashes.py` regenerates the
  checksum manifest in one command; a CI drift test fails the moment
  any shipped file changes without it (same guard pattern as
  MANIFEST.txt).
- Workshop ▸ *Save Session Now — snapshot tabs + cursors* menu entry,
  completing the four entry points (menu, palette, terminal, chip)
  to the session snapshot engine.

## [2.33.0] — 2026-09-14 · beta · "the session you can see" (save now + chip)

### Added
- **Save Session Now** — snapshot on demand from three places: the
  command palette (*Save Session Now — snapshot tabs + cursors…*),
  the terminal (`session save`, `save session` or `ssave`), and a
  click on the new statusbar chip. Uses the exact same file and data
  shape as the close hook and the 60 s autosave — one snapshot, three
  ways to reach it.
- **Session statusbar chip** — a quiet `◐ session saved HH:MM` chip
  on the right of the status bar. It glows in the accent colour right
  after any snapshot (autosave included) for 2.5 s, then fades back
  to muted ink. Click it to snapshot right now. With no workspace
  open, save-now degrades to an honest toast instead of an error.

### Changed
- `TERMINAL_HELP` documents the new verb; the palette command joins
  the fuzzy index, so `save ssion` already finds it.

## [2.32.0] — 2026-09-14 · beta · "even a crash comes back" (session autosave)

### Added
- **Crash-safe session autosave** — the rich session snapshot (tabs +
  active file + per-buffer cursor spots) used to be written only on a
  clean close, so a crash, `kill -9` or battery death lost the whole
  workspace state. A silent autosave now rewrites the identical
  snapshot once a minute (`_autosave_session`, interval clamped
  15–600 s, `session_autosave_secs` config key), so the worst case is
  one minute of state instead of everything.
- **Crash recovery** — open a workspace with no clean-exit record and
  `_restore_engine_session` picks up the last autosaved snapshot
  automatically: tabs reopen, the active file refocuses at its exact
  saved cursor spot, and every other buffer keeps its position for the
  first tab switch (the v2.31 per-buffer cursor map is seeded from the
  snapshot). Ghost files are filtered by the existing `restore_plan`.
- **Installer `--version` / `-V`** — `install.sh --version` prints the
  installer version and exits, without touching the install; handy for
  support triage and scripts.
- Settings ▸ Boot behaviour gained an *Autosave the session* switch
  (default on) next to *Restore last session*; both switches gate the
  autosave, and junk interval values can never break the reschedule.

### Changed
- Close-hook and autosave now share one `_save_session_snapshot()`
  code path — identical data, same file, one less drift risk.

## [2.31.0] — 2026-09-14 · beta · "never miss a module again" (installer fix + polish round)

### Fixed
- **Installer shipped a 19-module list for an 83-module app** — fresh
  installs crashed on launch with `ModuleNotFoundError: No module named
  'dxn1_studio.i18n'` (hub.py imports it). install.sh now downloads
  `MANIFEST.txt` (generated from `dxn1_studio/*.py`, CI-tested to stay
  in sync) and fetches every module it lists, with a post-download
  sanity gate that verifies all modules landed. A minimal built-in
  core list (including `i18n.py`) remains as a fallback.
- **The in-place updater had the same stale list** — updater.py now
  resolves the module set from the repo's MANIFEST.txt first, then the
  locally installed one, then the fallback list; the update portal's
  progress estimate uses the resolved count and verification compiles
  every module it actually downloaded.
- **Installer version-stamp downgrade removed** — the script used to
  rewrite the downloaded `__init__.py` to claim `1.1.6`, which made the
  update portal re-prompt forever and mislabel the installed build. The
  app's real version now always comes from the shipped file.

### Added
- **Fuzzy highlight rendering** — palette command rows, `@` symbol
  rows and Quick Open now paint the matched characters bold + accent
  (white bold on the selected row), via `fuzzy.split_runs`, which
  merges contiguous match positions into single runs.
- **Per-buffer cursor memory** — switching tabs or opening another
  file records the outgoing buffer's insert mark and restores it on
  return; the close hook merges the whole map into the session
  snapshot (current file wins).
- **`install.sh --uninstall`** — removes the app + CLI links, keeps
  `~/.dxn1-studio` settings.

### Tests
- 4 new pytest groups (69 total): `split_runs` semantics, cursor-memory
  record/guards, the manifest↔package drift guard (fails CI the moment
  a new module isn't in MANIFEST.txt), and updater manifest helpers.
- New committed UI smoke `scripts/smoke_v310.py` (20 checks): live
  palette/QuickOpen highlight runs, cursor restore on both switch
  paths, session snapshot cursor merge.

## [2.30.0] — 2026-09-14 · beta · "pick up where you left off" (bonus round)

### Added
- **Session Restore** (`session.py`, Workshop menu, palette,
  terminal `session` / `sessions` / `resume`) — a saved-session
  browser: every workspace you close with files open gets a snapshot
  (tabs, active file, cursor position), and one click reopens
  everything with the cursor back on its line.
- **Cursor memory** — the close hook records the exact insert
  position (line + column) of the active file; restore jumps there
  and scrolls it into view.
- **Durable session store** — `~/.dxn1-studio/sessions/<hash>.json`
  per workspace (sha1 key, same convention as agent chats), atomic
  writes, newest-first browsing, up to 40 workspaces retained, up to
  50 tabs each.

### Changed
- The existing lightweight auto-restore of tab paths on project open
  (config key `session_tabs`) is unchanged — the JSON store is the
  richer sibling with cursors and a manager UI, and both coexist.

### Notes
- Pure, junk-tolerant engine: corrupt JSON reads back as an empty
  session, ghost files are filtered from restore plans, `base=`
  overrides the storage dir for tests. i18n: `session.*` keys in all
  8 packs. Smoke now also drives the real close hook (155 checks /
  26 windows).

## [2.29.0] — 2026-09-14 · beta · "type a few letters" (bonus round)

### Added
- **Fuzzy launcher scoring** (`fuzzy.py`) — the command palette and
  Quick Open now rank by relevance instead of requiring substrings:
  `qpn` finds "Quick open a file", `sttngs` finds "Settings…",
  `@gmmthre` finds `gamma_three` in symbol mode. Documented,
  deterministic weights: word-boundary starts, camel humps and
  contiguous runs score high; spread-out matches lose; substring
  hits still win.
- **Basename boost for Quick Open** (`path_score()`) — a query
  matching the file name outranks the same letters in a deep
  directory path, so files beat folders; deterministic tie-breaks
  keep short paths first.
- **Fuzzy symbol mode** — the palette's `@` needle no longer needs to
  be a substring of the symbol name.

### Changed
- Empty queries keep the original order everywhere; legacy substring
  filters remain as an automatic fallback if the fuzzy import ever
  fails (the launcher can never break, worst case it degrades).

### Notes
- Pure, junk-tolerant engine: `None` never matches, exotic objects
  coerce via `str()`, broken key functions fall back — scoring never
  raises. The Xvfb smoke now boots the real app and drives the
  palette, symbol mode and Quick Open live (148 checks / 25 windows).

## [2.28.0] — 2026-09-14 · beta · "through their eyes" (bonus round)

### Added
- **Colorblind Lab** (`cvdlab.py`, Workshop menu, palette, terminal
  `cvd` / `colorblind` / `vision`) — see the studio's themes the way
  color-blind users do: deuteranopia, protanopia, tritanopia and
  achromatopsia previews with a 0–100% severity blend slider.
- **Contrast under CVD** — the lab re-runs the Contrast Auditor on
  the simulated palette and shows a live verdict ("CVD view: 13
  pairs · 13 pass · 0 fail"). The two accessibility tools now work
  as a suite.
- Custom hex entry with instant simulation + copy; sRGB-space
  approximation documented honestly in the module docstring.
- i18n: `cvdlab.severity` + `cvdlab.copy_hex` in all 8 packs.

### Fixed
- **Applied the Contrast Auditor's own findings to the palettes**:
  FAIL-grade gutter pairs fixed in dark (`#4d5766`→`#778498`,
  2.48:1→4.55:1) and light (`#8b949e`→`#67707b`, 2.89:1→5.0:1)
  built-ins, light `text_muted` raised to AA, Solarized-ish muted
  fixed — the auditor now reports **0 FAILs across all 14 themes**
  (gallery themes inherit the corrected base values).

### Notes
- 63/63 pytest groups · 141/141 smoke checks across 23 windows ·
  20/20 boot QA · 81 feature modules.

## [2.27.0] — 2026-09-14 · beta · "print me" (bonus round)

### Added
- **Cheat Sheet** (`cheatsheet.py`, Workshop menu, palette, terminal
  `cheat` / `cheatsheet` / `man`) — one standalone print-friendly HTML
  page with every terminal command and keyboard shortcut: inline CSS,
  `@media print` rules, kbd chips, zero dependencies.
- **Zero-drift data** — the sheet is generated from the same
  `TERMINAL_HELP` tuple the terminal's `help` prints, plus a curated
  shortcuts table mirroring `setup_bindings()` and a tips section.
- Window: plain-text preview, save HTML anywhere, open in browser
  (temp-file fallback), copy HTML to clipboard; honest error strings
  for bad paths — never raises.
- i18n: 4 new `cheatsheet.*` keys in all 8 language packs.

### Changed
- Refactor: the terminal help list (48 commands) extracted from
  `handle_terminal_command` to module-level `TERMINAL_HELP` — single
  source of truth shared by terminal, cheat sheet, and tests.

### Notes
- 62/62 pytest groups · 136/136 smoke checks across 22 windows ·
  20/20 boot QA · 80 feature modules.

## [2.26.0] — 2026-09-14 · beta · "readable or it didn't happen" (bonus round)

### Added
- **Contrast Auditor** (`contrast.py`, Workshop menu, palette, terminal
  `contrast` / `a11y` / `wcag` / `audit`) — WCAG 2.x audit for every
  theme the studio can wear: 13 semantic text pairs graded per theme
  (AAA / AA / AA-L / FAIL), theme picker covers Built-in Dark & Light,
  all 12 community gallery themes, and user-saved themes.
- **Auto-fix suggestions** — pairs below AA get a concrete fix: the
  engine searches lighten/darken steps until the foreground clears
  4.5:1 (e.g. gutter `#4d5766` on `#11161d` -> `#778498`); honest `—`
  when no simple fix exists (selection white on violet accent).
- **Copyable plain-text report** per theme for issue reports, plus a
  graded summary line (pass/fail counts + average ratio + worst pair).
- i18n: `contrast.copy_report` + `contrast.audit_hint` in all 8
  language packs.

### Fixed
- Auditor tolerates the studio's `Theme` wrapper and half-written
  community themes alike — junk palettes audit to honest FAIL rows,
  the window never raises.

### Notes
- First findings are real: built-in gutters (`#4d5766` on `#11161d`)
  and light-theme muted text fall short of AA — the auditor now makes
  these visible instead of invisible.

## [2.25.0] — 2026-09-14 · beta · "well-formed or bust" (bonus round)

### Added
- **Markup Bench** (`xmlbench.py`, Workshop → *Markup Bench — pretty & inspect XML…*, terminal `xml` / `markup` / `xmlbench`) — an XML workbench: pretty-print with 2–8 space indent, minify (real text nodes preserved, inter-element whitespace dropped), live validation with honest line/column errors, and an element census (total elements, unique tags, top-3 counts, max depth, attributes). Safety first for untrusted input: 512 KB size cap, 200-level depth cap, and DTD entities refused outright (the billion-laughs vector) — junk in, honest message out.

### Changed
- i18n: `xml.copy_out` + `xml.paste_hint` translated in all 8 language packs.
- Smoke harness now **126 checks across 20 live windows**; test suite at **60 groups**; boot QA 20/20.

## [2.24.0] — 2026-09-14 · beta · "what changed?" (bonus round)

### Added
- **Paste Diff** (`textdiff.py`, Workshop → *Paste Diff — compare two texts…*, terminal `diff2` / `pastediff` / `textdiff`) — compare two pasted texts at word, character or line granularity: word/char modes mark edits inline with the greppable `[-deletion-]` / `{+insertion+}` rdiff convention, line mode gives classic `- / +` rows; a live status line counts `+N -M lines · P% similar` and one click copies the diff. Thin honest wrapper over stdlib difflib — no vendored algorithms, nothing clever to go wrong.

### Changed
- i18n: `diff.copy_diff` + `diff.paste_hint` translated in all 8 language packs.
- Smoke harness now **121 checks across 19 live windows**; test suite at **59 groups**; boot QA 20/20.

## [2.23.0] — 2026-09-14 · beta · "snoop the bytes" (bonus round)

### Added
- **ByteSnoop** (`hexdump.py`, Workshop → *ByteSnoop — hexdump & byte inspector…*, terminal `hexdump` / `bytes` / `bytesnoop`) — a hexdump & byte inspector: paste text or raw hex and read a classic 16-byte-per-row dump with offset columns and an aligned ASCII gutter (non-printables become dots). Hex input tolerates spaces, colons, commas, `0x` prefixes and xxd-style offset columns; odd digit counts are refused honestly. A live stats line shows total bytes, unique values, printable % and high-bit %; one click copies the whole dump.

### Changed
- i18n: 2 new keys (`hex.copy_dump`, `hex.rows_label`) translated in all 8 language packs and wired into ByteSnoop's button and label.
- Smoke harness now **116 checks across 18 live windows**; test suite at **58 groups**; boot QA 20/20.

## [2.22.0] — 2026-09-14 · beta · "the finale: math, tables, and one big thank-you"

### Added
- **CSV Lab** (`csvkit.py`, Workshop → *CSV Lab — paste & peek tables…*, terminal `csv` / `csvlab` / `tsv`) — paste CSV/TSV/semicolon/pipe data and it renders instantly as a table: delimiter auto-sniffing, stdlib csv parsing (quoted fields with embedded delimiters work), ragged-width flagging, header row as column headings, honest empty-grid on junk, one-click copy back out as TSV.
- **MathPad** (`mathpad.py`, Workshop → *MathPad — safe expression calculator…*, terminal `calc` / `math` / `mathpad`) — a safe expression calculator: the engine evaluates through Python's `ast` with a strict whitelist (no `eval`, no attribute access, no imports), so pasted junk can only ever produce an error message. Operators `+ - * / // % **` (`^` accepted as power), 26 functions (`sqrt cbrt log log2 log10 exp sin cos tan abs round floor ceil factorial gcd hypot …`), constants `pi e tau inf`, hex/binary/`1_000` literals. The window adds variable assignment (`x = 5` then `x*3`), `_`/`ans` last-answer names, click-to-copy history, function chips, and honest error states. Hard limits keep it safe: exponents capped at 10,000, factorials at 10,000!, complex results rejected.

### Changed
- i18n deepens again: 2 new keys (`math.copy_result`, `math.click_copy`) fully translated in **all 8 language packs** (en es fr de pt zh hi ja); MathPad's copy button and history hint respond to the active language.
- Smoke harness now **111 checks across 17 live windows**; test suite at **57 groups**; boot QA 20/20; ARCHITECTURE.md and FEATURES.md refreshed for the finale.

### Finale note
- This tag closes the **7-hour DS2 sprint**: v1.4.0 → v2.22.0, 30+ tagged releases, ~76 feature modules, thousands of lines of tested, documented, defensively-wired code. Thank you for flying DXN1.

## [2.21.0] — 2026-09-14 · beta · "count in every base"

### Added
- **NumBase** (`numbase.py`, Workshop → *NumBase — bin/oct/dec/hex + bases 2-36…*, terminal `base` / `numbase` / `hex`) — a live number-base workbench: type a value in any base 2–36 (0x/0o/0b prefixes and `_` separators accepted) and read it simultaneously in fifteen bases with a bit inspector (bit length, popcount, hex bytes, two's-complement note for negatives); click any row to copy; round-trips are unit-tested for every base 2..36.

### Changed
- Smoke harness crossed the **100-check milestone** (now 15 live windows); test suite at 55 groups; ARCHITECTURE.md Workshop line updated with PassForge + NumBase.

## [2.20.0] — 2026-09-14 · beta · "secrets, not guesses"

### Added
- **PassForge** (`pwdgen.py`, Workshop → *PassForge — strong passwords + entropy…*, terminal `passgen` / `password` / `passforge`) — a cryptographic password generator: toggled character classes (A-Z / a-z / 0-9 / symbols), an "no `Il1O0o`" ambiguous-glyph switch, lengths 4–128, stdlib `secrets` CSPRNG (no home-made randomness), a live Shannon-entropy readout (`20 chars of a 86-glyph pool ≈ 119.1 bits`) and an honest strength ladder from *weak* to *overkill*; one click copies.

## [2.19.0] — 2026-09-14 · beta · "speak the case, speak the language"

### Added
- **TextCase** (`textcase.py`, Workshop → *TextCase — snake/camel/kebab/… converter*, terminal `case` / `textcase`) — paste an identifier in any convention (`user_profile_id`, `getHTTPResponse`, `MyApp2-file`) and read all eight styles at once: snake_case, camelCase, PascalCase, kebab-case, CONSTANT_CASE, Title Case, dot.case, flatcase; acronym runs split whole (`getHTTPResponse` → `get_http_response`), digits stay attached, click any row to copy.

### Changed
- **tr() deepening** — six new UI keys shipped with full translations in all eight language packs (68 keys each): markdown preview's Copy/Export HTML buttons, chart studio's copy-stats, unit converter's copy-result, TextCase and Character Map click-to-copy hints now resolve through the active language; missing keys keep falling back to English by design.

## [2.18.0] — 2026-09-14 · beta · "every glyph at your fingertips"

### Added
- **Character Map** (`charmap.py`, Workshop → *Character Map…*, terminal `charmap` / `char` / `unicode`) — a click-to-copy Unicode browser: 25 curated offline blocks (Arrows, Math Operators, Box Drawing, Geometric Shapes, Hiragana, CJK, Currency…), search by block name, by hex codepoint (`U+2192`, `0x00e9`, `2192`) or paste a literal character; clicking a glyph copies it and prints `U+00E9 · é · LATIN SMALL LETTER E WITH ACUTE`; "copy all shown" grabs the whole grid.

### Changed
- **First tr() plumbing** — the splash-screen tagline, the Project Hub welcome headline (name substituted in all seven packs) and the git-panel commit-message placeholder now resolve through language packs, so `lang es` / `lang zh` visibly re-speaks core surfaces after restart; placeholder clearing uses a locale-safe translated prefix.

## [2.17.0] — 2026-09-14 · beta · "see the numbers, know the words"

### Added
- **Chart Studio** (`charts.py`, Workshop → *Chart Studio…*, terminal `chart` / `charts` / `plot`) — paste any text containing numbers and get instant line/bar/histogram views on a canvas, a unicode sparkline strip and a live stats panel (count/min/max/mean/median/stdev/range/sum) with copy-to-clipboard; junk-tolerant parser understands `12ms`, `5px`, `8%` suffixes and skips garbage tokens; zero plotting dependencies.
- **Unit Converter** (`unitconv.py`, Workshop → *Unit Converter…*, terminal `unit` / `convert`) — six categories (length, mass, temperature, data, time, speed) with exact international factors and real C/F/K formulas; type a value and read every unit converted at once, swap units, copy the result; junk input shows an honest dash instead of a fake zero.
- **Language switcher** (i18n activation, terminal `lang`) — the eight built-in language packs (en es fr de pt zh hi ja) are now reachable: `lang` lists them, `lang <code>` activates and persists across restarts via the new `boot_from_config()` hook; community packs in `~/.dxn1-studio/lang/` join automatically.

### Changed
- Terminal help, cheatsheet and Workshop menu now cover all three new tools; smoke harness extended to 77 checks, test suite to 51 groups.
## [2.16.0] — 2026-09-14 · beta · "the studio keeps score"

### Added
- **Scribe mini chip** (`scribe.py`, statusbar, terminal `scribe` / `scribe 750`) — a live `✎ 1,234 w · 27 wpm · 45%` writing meter in the statusbar: throttled word-count sampling (never lags typing), trailing WPM with paste-spike cap, session word goal with click-for-toast summary; zen mode's tracker engine reused under the hood.
- **Filestats scan history** (`filestats.py`, `.dxn1/filestats_history.json`) — every File statistics scan now records a snapshot and renders a `▁▂▃▄▅▆▇█` sparkline of the last 40 scans with a `+12 files · +340 KB vs previous scan` delta line; deduped, capped at 60 points, corrupt-store tolerant.

## [2.15.0] — 2026-09-14 · beta · "tools that talk to the world"

### Added
- **Color Kit** (`colorkit.py`, Workshop → *Color Kit — convert & contrast…*, terminal `color`) — paste any hex (`#7c3aed`, `7c3aed`, `#abc`) and get rgb/hsl/tk forms instantly, WCAG contrast ratios against white/black with AA verdicts, and deterministic click-to-copy shade ramps; pure stdlib engine with stable round-trips.
- **REST Bench** (`restbench.py`, Workshop → *REST Bench…*, terminal `rest` / `http`) — a zero-dependency HTTP workbench: GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS with custom headers and body, Ctrl+Enter send, response viewer with pretty-printed JSON and muted headers, elapsed-time/size readout, 30-entry history and copy-as-curl with proper shell quoting; every failure mode (bad scheme, timeout, refused connection) becomes a readable error response.
- **Window geometry memory** (`geom.py`) — the studio now remembers size & position per screen shape: restore on boot, save on close, hard-clamped so windows can never reopen off-screen or larger than the display (docking/undocking safe), LRU of 8 screen shapes, maximized/fullscreen states skipped.

## [2.14.0] — 2026-09-14 · beta · "write it, see it"

### Added
- **Markdown preview** (`markprev.py`, Workshop → *Markdown Preview…*, palette, terminal `md` / `preview` / `markdown`) — dual-pane window: edit markdown on the left, live rendered result on the right; opens pre-loaded with the current editor buffer.
- **Zero-dependency markdown engine** — `parse_blocks` (headings, fenced code with language, blockquotes, ordered/unordered lists, pipe tables, horizontal rules, paragraph folding) + `inline_spans` (bold, italic, strikethrough, inline code, links); pure stdlib, unit-tested.
- **Live re-render** — debounced 300 ms while typing, F5 for instant; status bar reports words, lines, blocks and render time in ms.
- **HTML export** — one click copies a standalone styled HTML document or saves it via *Export HTML…*.

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
