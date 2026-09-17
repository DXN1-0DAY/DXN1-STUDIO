# DXN1 STUDIO 3

![DXN1 STUDIO 3](assets/banner.png)

![version](https://img.shields.io/badge/version-3.1.79-8b5cf6?style=flat-square)
![gates](https://github.com/DXN1-termux/DXN1-STUDIO/actions/workflows/ci.yml/badge.svg)
![native](https://img.shields.io/badge/native-C%2B%2023-f97316?style=flat-square)
![face](https://img.shields.io/badge/face-terminal_truecolor-22d3ee?style=flat-square)
![deps](https://img.shields.io/badge/dependencies-zero-34d399?style=flat-square)
![engine](https://img.shields.io/badge/spark_2d-built_in-fbbf24?style=flat-square)
![launch](https://img.shields.io/badge/launch-dxn3_one_liner-22c55e?style=flat-square)

**A beautiful game engine with a studio for code — one C++23 binary, zero dependencies.**
STUDIO 3 is a real engine: open it and you start with nothing — you write code
(Python, JavaScript, C++, anything), and it runs LIVE beside your editor. The
Spark 2D core renders, feeds input, reports collisions and consoles your game
in truecolor; your code IS the game. It also ships an eight-scene campaign as a
demo of what the engine can do. Scenes are plain JSON, games are plain code,
and the whole thing builds with `make`.

The engine core has no Electron, no Node and no Python **in it** — one C++23
binary, nothing else. Your games, though, can speak any language you like:
the engine hosts them as child processes over a tiny JSON protocol
([sdk/PROTOCOL.md](sdk/PROTOCOL.md)), with thin SDKs for Python and
JavaScript in `sdk/` and first-class support for compiled C++ games.

## Install — one line, fully launchable

Every push runs the full gauntlet in CI — a zero-warning C++23 build under
g++ **and** clang++, the engine selftest, a real headless frame for every
scene, and a live probe of the one-liner installer.

```bash
curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/scripts/install.sh | bash
```

The installer checks `git` and a C++23 compiler (g++ or clang++, probing that
C++23 actually compiles), clones the repo, builds `native/build/dxn3-native`,
runs the engine selftest so you know it's green, and drops a `dxn3` launcher
into `~/.local/bin`. That's the whole dependency list: git, a compiler,
libstdc++. Then:

```bash
dxn3                              # THE ENGINE — write a game, it goes live
dxn3 sdk/examples/background.py   # your first background, then a shooter
dxn3 scenes/level-1.dxn1.json     # the demo campaign, by path
dxn3 --list-scenes                # what's installed, with entity counts
dxn3 --screenshot shot.png        # headless PNG of any scene
```

Prefer it by hand?

```bash
git clone https://github.com/DXN1-termux/DXN1-STUDIO.git
cd DXN1-STUDIO && make -C native && ./native/build/dxn3-native
```

## The engine: your code, our canvas

`dxn3` with no arguments opens the IDE: an editor pane with line numbers and
syntax tint, a **live viewport**, and a console rail. You start with
absolutely nothing — a starter game is loaded, and it is already running.
Edit anything and pause for a beat: your code re-runs itself and the
viewport refreshes — *code a background, and boom, a background.*

- **Any language.** `.py` and `.js` run via the SDKs, `.cpp` games are
  compiled and hosted, and `--host-cmd 'ruby game.rb'` covers everything
  else. The protocol is one page: [sdk/PROTOCOL.md](sdk/PROTOCOL.md).
- **The engine does the heavy lifting.** Rendering (truecolor half-block
  pixels, discs, triangles, gradients, starfield skies), input, collision
  reporting, the HUD, the console. Your code owns the game logic.
- **The SDK is one import.** `from dxn3 import *` gives you `rect`,
  `circle`, `tri`, `label`, `on_key` / `on_tick` / `on_hit`, `destroy`,
  `vars`, `camera` — and `run()`. Entities are plain objects; move them
  and the engine sees it. C++ games `#include "dxn3.hpp"` and compile
  to a binary the studio hosts — see `sdk/examples/pong.cpp`.
- **Examples in `sdk/examples/`:** `background.py` (the hello world),
  `shooter.py` (bullets, score, two threat classes — the bulk and the DRIFTING TWIN, smaller and faster on a sine bob and worth 25, each respawning from its OWN NAMED STREAM so the same run deals the same respawns forever — and the TENTH hit turns the sky: nine stars and a moon fade in from their own stream, the moon shines glow 4, the hunters wear a faint ring), `flappy.py`
  (gravity, pipes, one-key flying — the pipes FADE IN from the
  horizon, a clean pass makes the bird GLOW, a crash BLEACHES
  it white, and the score turns the sky: night falls at 3, dawn
  at 8, and every five after — the dark fades in over two honest
  seconds, the pipes dress pale with a faint halo so the gap reads
  in the dark, and the moon SHINES when the fade completes), `bounce.js`
  (breakout with a steering paddle — the lantern FLARES when it
  bites a brick and wears back to its resting 2, a flare with a
  floor, and the end plaques are born with a bloom of glow 3 that
  wears to dark while the words stay), `cards.py` (balatro-lite poker
  hands vs the blind — the selected card GLOWS like a lamp, a played
  card FLASHES white as it lands in your hand row, and the score
  reads chips x mult with red suits paying double — and the DECK is
  real now: forty cards shuffled by their own named stream, dealt
  five at a hand, the muck growing until the dry deck RETURNS
  through its reshuffle stream and the title SPEAKS the reshuffle
  while the fresh hand ghosts in again), `snake.py` (the classic — a turn queue that
  plays fair under held keys, meals that sharpen the step, a tail
  that grows, the meal SPEAKS on the HUD and wears the engine's
  glow, every meal BLEACHES the head white (the flash field —
  milestones flash the new tail too), milestones name you — the
  garden snake, the hunter, the
  anaconda, the world eater — and every death arrives as a banner), `asteroids.js` (a hull that REALLY turns — a rotated tri,
  its thrust flame LIT WHOLE the frame the thrust lands and worn
  down the burn's own staircase to dark — splitting rocks that fly
  faster as they shrink and BLOOM glow 2 as they're born, worn 3/s
  by the game's own ledger, the SHOT a muzzle flash with a bloom of
  its own (one ledger for every transient light), a hull hit that BLEACHES
  the ship with the engine's flash and says so on the HUD, a grace
  blink after), `lunar.py` (side-thrusters, one main engine,
  two pads that pay by their risk — the hills are not for landing —
  halos that BREATHE on a sine, the summit's taller because it pays
  richer, a touchdown that makes the pleased pad FLARE and wear it
  honestly, and a fuel gauge that empties in width AND color, green
  to amber to red, blinking under a quarter tank while the warning
  speaks),
  `raycast.py` (a Wolfenstein-style 3D view painted out of plain
  rects — the engine is a canvas, so it can be ANY canvas),
  `windmill.py` (four blades orbit the hub while the SDK drives
  their rot each tick — and the hub's little square turns itself
  with the engine's own spin), `invaders.js` (the classic march:
  a grid that steps, drops and speeds up as it thins, pooled guns
  parked off-screen until their moment, and four SHELTERS that
  drink one hit per block — your shot, their bomb or the march
  itself — honest destroys that erode the arch to its shoulders;
  the SECOND wave comes in the dark: nine stars and a moon fade in
  from their own seeded stream, the moon shines at the end, and the
  living march wears the faint ring;
  r rebuilds from the ashes), `dino.js` (an endless
  runner whose desert is SEEDED — the same run, the same cacti,
  forever — with a night that falls at 200 m: seven stars and a
  moon from their OWN seed fade in through the alpha law (day a
  rumor at 0.15, night a sky at 0.9) until the moon shines at
  glow 4, and r walks again under a fresh day), `tetris.js` (the
  falling order: a 7-bag seeded like the stars, locked cells as
  their own entities, line clears that are ten honest destroys,
  wall-kicked turns, a GHOST that wears alpha 0.32 where the order
  will land — the alpha law as honest wayfinding; s sinks the
  piece, the wire's held keys never carried "down" — and the NEXT
  piece previewed right of the well, the queue ahead peeked
  honestly so the seeded law survives the preview; every lock
  BLOOMS and wears at 3/s, and a cleared line SPEAKS twice — the
  say grows a level callout while a banner over the well wears
  linearly to invisible, never a flash-forever — and the well
  COUNTS THE STREAK: consecutive clearing locks speak
  "· combo ×N" and burn brighter (the banner born at bloom
  2 + min(combo-1, 6)), while one dry lock breaks it — the next
  lone clear speaks plain again), `lightbot.js` (the night shift: a diamond of
  twelve unlit lamps — walk the grid, SPACE lights the lamp under
  you and every flame wears the engine's glow, the wayfinding is
  literally made of light — steps counted, wins graded, r re-runs
  the shift), `pong.cpp` (a compiled C++ pong
  with an AI that caps its speed — the hardest SDK proof in the
  set).
- **The editor forgives.** `ctrl+z` undoes — typing bursts coalesce the
  way real editors group them, `enter`/`del` are their own restore
  points, and undo restores the document AND the cursor. `ctrl+y`
  walks it forward again; a fresh edit cuts the redo branch, honestly.
  Two hundred steps deep, so you can code without fear.
- **The block rides down.** Enter auto-indents: openers (`:`, `{`)
  bump a level, closers (`else`, `end`, …) drop back one, everything
  else inherits — python and C-family both feel at home.
- **The searchlight.** `ctrl+f` finds in your file — case-insensitive
  by default (the beginner way), every hit glows behind the text,
  `enter` walks you to the next one (wrapping), and the rail counts
  them while you type. `:cases` flips the light strict — only exact
  casing answers, an `(Aa)` marker rides the rail — and flipping
  re-aims the hits the instant it turns. The header always tells you
  where you stand: `Ln 12 · Col 8 · sel 87`.
- **Pairs carry their closers.** `(`, `[`, `{` and quotes type their
  other half for you; a closer you already have is skipped over, never
  doubled; backspace between an empty pair removes both halves; an
  apostrophe inside a word (`don't`) stays honest. `ctrl+d`
  duplicates the line under the cursor in one undo step. `ctrl+t`
  transposes the two neighbors around the hand — `teh` becomes `the`
  with the hand where you left it. `ctrl+u` walks the word's coat —
  `hello` → `HELLO` → `Hello` → `hello` — the hand never moves, and
  a coat that paints nothing (a lone `V2`) bows out honestly. With a
  crew live the breath is shared: every hand coats its own word in
  one undo step. Over a selection the span speaks: every word held
  WHOLE takes its coat; a word the span cuts is left honest.
- **`:open` learned the ledger.** `:open <file>` loads any script on
  the machine — your own games and the `sdk/examples/` gallery
  whisper their names as you type, and the LEDGER of files you had
  open speaks first. A bare `:open` reopens your most recent file in
  one word; an empty ledger refuses honestly. Ghost files are
  refused too.
- **`:record` and `:macro` make your verbs repeatable.** Start the
  recorder, run any verbs, end the take, and `:macro` replays them
  through the same dispatch, in order, at 60 verbs a second — a
  session's choreography, saved as a register of honest lines.
- **`:shuffle` deals the bed like cards.** The selection's lines land in
  random order, Fisher-Yates honest; a seed replays the deal exactly
  (the receipt names it), a bare verb rolls one from the clock. Pins
  follow their words, the census covers the bed, one undo takes it back.
- **`:changes` reads the census of your session.** Every line the
  hand changed since the page opened, ascending with its count —
  the answer to "where did the last hour go?". The pins' structural
  law keeps it honest through splits, splices, sorts and cuts; undo
  rewinds the document but never the record; a reload restarts it
  (the disk wrote, not you). The map rail ticks your touched lines
  emerald, the header counts them, and a clean page says so kindly.
  `:changes <word>` asks the census a question — which touched lines
  SPEAK the word? The find's case law answers, the pin's diamond
  rides the listing, and a bare verb still lists while a number
  still leaps.
- **`:diff` compares the page with the disk.** A look, never a save:
  the classic LCS speaks an edit script in three voices — lines the
  page adds, lines it let go, and a drop standing beside an add in
  the same breath, which is one honest change. The gutter's own
  numbers name the lines (a removal points where the line once
  stood), the samples cap at six with a `+k more` tail, an empty
  path says the disk has never heard of the page, and a bed too big
  to think refuses politely. The map rail
  wears the census's finding amber — a drifted line carries the
  amber tick until `:w` speaks it to the disk (the pin's bar and the
  session's emerald keep their own edges); a save or a fresh page
  sweeps the amber away. **And the drift breathes**: on a slow
  silent beat (a quarter second) the page re-hears the disk — the
  amber follows the edits live while they are still unsaved, a disk
  that moved under a settled page is worn on the rail without a
  word, and the header speaks the count (`N drifted`) at a glance.
  The breath never spends a console line; the store is the whole
  breath.
- **Word hops and the partner.** `ctrl+←`/`ctrl+→` jump word by word —
  the same words `ctrl+w` bites — across line edges when they must.
  `ctrl+delete` eats exactly what a hop would cross; `ctrl+/` toggles
  the line's comment in the file's own language (`#`, `//`, `--`).
  Stand on a bracket and its partner glows across the file, nesting
  respected. And long lines slide under the cursor instead of being
  chopped at the pane's edge; the gutter marks the cut with `…`.
- **The input parser grew up.** Escape sequences are parsed whole and
  unknown ones are swallowed — terminal control chatter (mouse
  reports, modifier-keyed arrows, split reads) can never leak into
  your code as text again. `ctrl+↑`/`ctrl+↓` nudge the view without
  moving the cursor.
- **The snippet shelf speaks your language.** `:snip tick` lands
  `def on_tick(dt):` in a .py file, `on.tick(() => { … })` in a .js
  one, `g.onTick = [&](float dt) { … }` in C++ — eleven python
  starters, seven js, five cpp, each one honest to the sdk/ wire
  contract; prefix-complete with whispers — the shelf itself speaks
  when you type `:snip `, every name carrying its one-line
  description ("tick — the every-frame hook"), the typed prefix
  narrowing by name, one undo step to take it
  back. Dim guides at columns 79 and 99 keep the margins visible
  (`:ruler` toggles), `:stats` counts what you're holding, and
  `ctrl+home`/`ctrl+end` jump the edges of the document.
- **The minimap rides the right edge.** A six-column map of the
  whole document lives in the pane's right border on wide terminals:
  indent compresses 2:1, the viewport's rows carry a soft band and
  burn brighter, the cursor's row is the brightest bar, comments
  speak gray, find hits glow amber — and `:minimap` sends it home
  when you want the columns back.
- **The pointer works.** Click the code to move the hand (hscroll
  included), click the gutter for the line start, click the minimap
  to jump whole lines; `shift+click` extends a selection like the
  shift+arrows, a bare click deselects — and looking around never
  re-runs your game. Clicks in the viewport, console or header belong
  to nobody and are swallowed whole.
- **The selection is real.** `shift+arrows` extend a glowing
  anchor↔cursor range across lines; typing, backspace, delete or
  enter replaces it in one undo step; `ctrl+/` comments or strips
  EVERY line the selection covers; a plain move drops it.
- **The clipboard.** `ctrl+c` copies the selection (or the whole
  cursor line when nothing is selected), `ctrl+x` cuts — a bare cut
  lifts the whole line out — and `ctrl+v` pastes: character-wise
  clips splice at the cursor, line-wise clips land above the cursor
  line, and a live selection is the paste's bed, replaced in the
  same undo step. Copy never dirties the doc; cut and paste are one
  honest step each.
- **The word select and the ceremony.** `shift+ctrl+←`/`→` extend the
  selection word by word (the anchor rides the same hops `ctrl+←`/`→`
  make). Enter between a bracket pair splits into three lines — the
  naked middle line takes the cursor, `{` bumps it a level, the
  closer keeps its ground at the base indent; quotes stay out, so
  breaking a string is still just a split. `ctrl+d` duplicates every
  line a multi-line selection covers, and the copy carries the
  selection with it.
- **The tab trigger.** Type a shelf name (`tick`, `key`, `fn`, …) and
  reach for `tab` — the word becomes the boilerplate in place, tail
  text riding behind the block, one undo step to take it back. Plain
  `tab` still gives four honest spaces, indents a selected block,
  and `shift+tab` dedents the block (or the hand's line) again.
  And `:screenshot` whispers its default name before it writes one.
- **The clipboard bridges out.** `ctrl+c`/`ctrl+x` also emit OSC 52
  so terminals that honor it (kitty, alacritty, wezterm, foot,
  iTerm2, Windows Terminal…) keep the OS clipboard in sync — while
  `ctrl+v` always pastes from the studio's own ring, so a plain
  terminal loses nothing. Pasting an empty clip says so instead of
  pretending. And every undo speaks its name now — `ctrl+z` says
  `undo — paste · 3 steps left`, not a blind count — while a shelf
  word under the hand whispers `⇥ tab expands 'tick'` from the rail.
- **The pins: bookmarks that follow the code.** `:mark` plants a pin
  on the hand's line (`ctrl+F2` from the keyboard), `F2` leaps to the
  next pin and `shift+F2` walks back, both wrapping — `:bm N` takes
  the Nth, a bare `:bm` takes the next. Pinned lines burn amber in
  the gutter (a `◆` rides its edge) and carry an amber bar on the
  minimap, so the file's shape shows where you've been. The pins
  FOLLOW the document: lines landing above slide them down, a cut
  takes its pin along, and undo/redo prune pins the restored document
  never had. Planting and leaping are a look, never an edit — nothing
  dirties, nothing undoes — and the header counts the pins at a
  glance. The pin's diamond is a BUTTON: a plain click on the gutter's
  edge of a pinned line pulls it (the hand stays put).
- **The quiet (`:zen`).** The console rail hides and the body
  breathes — two more rows of code on every screen. The searchlight
  keeps its own row while it is up (a query you cannot see is a
  query that cannot end); receipts gather silently until the quiet
  ends, then speak. The header carries a small `· zen` so the mode
  never hides ITSELF, the pointer's geometry follows the body's new
  edge, and a second `:zen` wakes the rail with everything it
  gathered waiting below.
- **Housekeeping verbs.** `:trim` sweeps every line's trailing
  whitespace in one undo step (a clean doc is refused without a
  phantom step); `:sort` orders the selected lines, A before B, the
  hand landing at the block's head; `:rsort` is the mirror — the
  same bed lands Z before A, one honest restore point of its own;
  `:upper`, `:lower` and `:title` change the selection's voice (a
  same-line selection counts — case is an in-line edit — and
  title stands each line's word-starts up); `:uniq` collapses lines that repeat back-to-back (no selection
  means the whole document, its difference from the sort family told
  out loud; the pins follow the survivors down); `:squeeze` breathes
  runs of blank lines down to one (the pins speak uniq's law: ride
  home, or die with the fallen); `:retab` widens every leading tab
  to four honest spaces (a tab inside a string literal keeps its
  meaning); `:ws` is the whitespace census — it changes nothing, it
  counts trailing, tab-indented and 80-column-law lines; `:rev` flips the
  selection's line order end for end (no alphabet invited — the
  pins ride to their mirrors); `:indent` and `:dedent` breathe the
  selection's lines one level right or back (a line of pure air
  keeps its silence, and a bed with no work takes no phantom step);
  `:lift` and `:drop` ride the selection's lines one line up or down
  (no selection moves the hand's line; the pins ride along, and undo
  carries them back); `:dup` says the selection's lines twice, the
  copies landing below while the originals keep their pins; `:join`
  folds the bed into one line at a seam the hand can stand on
  (vim's J law with no selection); `:goto <line>` jumps the editor
  and `:goto +N`/`-N` ride from where the hand stands;
  `:stats` counts lines, words, chars and dialect. The gutter earns
  its width honestly — four columns to 999 lines, five from 1000,
  six from 10000 — and the pointer, ruler and glows all speak the
  same rule. A drag parked at the viewport's edge pulls the view one
  line every 70ms, and past 1.2 seconds of hold the SECOND WIND
  doubles the pace; release, stall, or leaving the edge spends it
  and the walk restarts slow.

Keys: `ctrl+r` run · `ctrl+s` save · `ctrl+z` undo · `ctrl+y` redo ·
`ctrl+c`/`ctrl+x`/`ctrl+v` copy · cut · paste ·
`ctrl+f` find · `enter` next hit · `F3` next · `shift+F3` back —
the walk outlives the bar ·
`ctrl+d` duplicate lines · `ctrl+t` transpose — the two neighbors
around the hand trade places (the typo's fix) ·
`ctrl+u` the word's coat — `whisper → SHOUT → Title`, the seat never
moves ·
`ctrl+w` delete word · `ctrl+del` delete word ahead · `ctrl+/`
comment toggle (multi-line with a selection) ·
`shift+arrows` select · `shift+ctrl+←`/`→` select words ·
`home` the honest home — the line's first non-blank, then the head, then back ·
`mouse` click code/map to move · shift+click selects ·
`tab` snippet/indent · `shift+tab` dedent ·
`ctrl+←`/`ctrl+→` word hops ·
`ctrl+↑`/`ctrl+↓` nudge the view ·
`F2` next pin · `shift+F2` previous pin · `ctrl+F2` plant/pull a pin ·
`alt+↑`/`alt+↓` ride the hand's line up/down (the bar's `:lift`/`:drop`) ·
`ctrl+n` next template (or `:new`) · `ctrl+g` jump to the error line ·
`ctrl+p` screenshot of your live game · `pgup/pgdn` page · `home/end`
line ends · `ctrl+home`/`ctrl+end` doc edges · `del` forward-delete ·
`esc` play your game fullscreen · `e` back to the editor ·
`:open` [file] loads any script — bare, it reopens the ledger's head ·
`:recent` lists and reopens · `:goto <line>` jumps the editor ·
`:template <name>` loads a starter · `:snip <name>` drops boilerplate ·
`:minimap` toggles the map rail · `:zen` the quiet — the rail rests ·
`:theme <name|n>` wears one of the editor's coats — dracula,
gruvbox, nord, solar-dark, solar-light or the house dxn — by name,
unique prefix or 1-based index, a bare `:theme` lists the wardrobe
marking what's worn, the bar whispers the coats as you type, and the
choice keeps across nights in `~/.dxn3-theme` ·
**and the wardrobe 2.0 takes your own coats**: one per line in
`~/.dxn3-themes` — `name:base:comment:string:keyword:pane:sel`, each
color speaking decimal (`30,41,59`) or hex (`#e2e8f0`); shipped
names are refused, your own earlier coats re-tailor in place, and
the list marks your coats `[user]` ·
**the keepsake**: the editor's habits — `:ruler` `:minimap` `:zen`
`:relnum` `:wrap` — ride one line in `~/.dxn3-settings` and return
with you at boot; toggle one and the whole set keeps itself ·
`:wrap` the fold — long lines break into the pane, ↑/↓ walk its rows ·
`:crew <n>` plants the crew — many hands, one breath, every hand writes ·
`:crew <n>` again GROWS the crew — the new hands plant below the last ·
`:trim` sweeps trailing whitespace ·
`:sort` orders the selection (all-number beds count: 2 before 10) ·
`:rsort` lands it last-first ·
`:upper`/`:lower`/`:title` change the selection's voice ·
`:uniq` collapses back-to-back repeats · `:squeeze` breathes blank runs to one · `:retab` widens leading tabs · `:ws` counts the margin's sins · `:match` walks to the bracket's twin (strings respected) · `:rev` flips the order ·
`:shuffle` deals the lines like cards, its seed replays the deal ·
`:indent`/`:dedent` breathe the selection one level ·
`:lift`/`:drop` ride lines up and down ·
`:dup` says the bed twice · `:join` folds it into one ·
`:cases` find respects case (Aa) ·
`:mark`/`:marks`/`:bm` pin lines and leap between them (the pins
whisper as you type) ·
`:w` [file] saves the session's work — a .bak is kept ·
`:wq` saves and sleeps · `:hist` lists the undo ledger ·
`:scene <name>` loads a demo (with
completion whispers) · `:q` quit.

## The built-in demo: a thirteen-scene campaign

The Spark engine ships with a chained platformer — real headless renders
of the shipped scenes, the same frames your terminal draws. It is a demo
of the renderer; your games are the product:

| the playground | the gap (level-1) |
|---|---|
| ![playground](docs/img/shot-playground.png) | ![level-1](docs/img/shot-level-1.png) |
| **the movers (level-2)** | **the climb (level-3)** |
| ![level-2](docs/img/shot-level-2.png) | ![level-3](docs/img/shot-level-3.png) |
| **the gauntlet (level-4)** | **the vault (level-5)** |
| ![level-4](docs/img/shot-level-4.png) | ![level-5](docs/img/shot-level-5.png) |
| **the ascent (level-6)** | **the descent (level-7)** |
| ![level-6](docs/img/shot-level-6.png) | ![level-7](docs/img/shot-level-7.png) |
| **the beacon (level-8)** | **the crossing (level-9)** |
| ![level-8](docs/img/shot-level-8.png) | ![level-9](docs/img/shot-level-9.png) |
| **the fog (level-10)** | **the return (level-11)** |
| ![level-10](docs/img/shot-level-10.png) | ![level-11](docs/img/shot-level-11.png) |
| **the epilogue (level-12)** — one scene stands alone, like the quiet after |
| ![level-12](docs/img/shot-level-12.png) | *the door home wears glow 9 — the brightest the campaign has ever shipped* |

Goals chain the scenes into a thirteen-scene campaign: **playground → level-1 (the
gap) → level-2 (the movers) → level-3 (the climb) → level-4 (the gauntlet) →
level-5 (the vault) → level-6 (the ascent) → level-7 (the descent) →
level-8 (the beacon) → level-9 (the crossing) → level-10 (the fog) →
level-11 (the return) → level-12 (the epilogue) → back home.** Coins score (+10, magnetized inside the scene's radius), spikes
respawn you with a camera shake, movers carry you across the gaps — and the
HUD counts it all: `COINS x/y · SCORE · TIME`, scene name on the right.
Level-3 goes vertical — two lifts, a springboard shortcut and a gradient
summit. Level-4 is the exam: nine fangs, three ferries, a saw-guarded island
and a spinning gate before the last door. Level-5 is the vault: two
counter-phased lifts, a saw-patrolled high deck, a ferry under a saw
and a fang-lined last stretch. Level-6 is the ascent: three lifts up a
five-terrace tower where the saws finally bite — jump them, ride past
them, and the summit door is the highest the campaign has ever reached.
Level-12 is the epilogue: a walking-pace victory lap that replays every
law the road taught — mist, ferry, saw, counter lifts, a leaning fang,
a glowing stair — and ends at the door home wearing glow 9. The full
walkthrough lives in the
[campaign field guide](docs/CAMPAIGN.md).

## Play

| key | action |
|-----|--------|
| `a` / `d` | run left / right |
| `w` / `space` | jump |
| `r` | reset to spawn |
| `+` / `-` | camera zoom (clamped 0.3×–4×) |
| `f` | zoom-to-fit the whole scene |
| `tab` | INSPECT — the live entity table, game paused |
| `e` | FILE VIEW — the scene's source, `j/k` scroll, `/` search with wrap-around |
| `p` | screenshot → `exports/<scene>-<n>.png` |
| `:` | the command bar (below) |
| `q` / `esc` | quit |

## The command bar

`:` opens a vim-style command line with honest errors — bad verbs, junk
numbers and out-of-range values are refused with usage, never silently
accepted:

| command | what it does |
|---------|--------------|
| `:scene <file>` | load any scene mid-flight |
| `:zoom in\|out\|<factor>` | camera zoom, clamped 0.3–4× |
| `:fit` | zoom-to-fit |
| `:reset` | back to spawn |
| `:w [file]` | save the scene (a `.bak` is kept) |
| `:wq` | save and quit |
| `:q` | quit |
| `:screenshot [file]` | PNG of the live frame |
| `:magnet <px>` | coin magnet radius, live |
| `:gravity <force>` | gravity, live |
| `:open [file]` | load any script; bare `:open` reopens the ledger's head |
| `:o [file]` / `:e [file]` | :open in the vim tongue — the ledger resolves a tail |
| `:recent [name]` | the ledger — list it, or reopen a prefix match |
| `:help [verb]` | the verbs — or one verb's law, spoken to the console |
| `:record` | the recorder — run verbs, `:record` again to end the take |
| `:macro [n]` | replay the register, one verb per frame; a number runs the take N times |
| `:template <name>` | load a starter (blank, shooter, cards, …) |
| `:snip <name>` | drop language-aware boilerplate at the hand |
| `:goto <line>` | jump the editor to a line — `+N`/`-N` ride from the hand |
| `:mark` | plant/pull a pin on this line — F2 leaps; click the gutter's ◆ to pull |
| `:marks` | list every pin in the file |
| `:bm [n]` | leap to a pin; bare `:bm` takes the next, wrapping — the pins whisper as you type |
| `:changes [n\|word]` | the census — a bare verb lists the session's touched lines; a number leaps to the Nth; a word asks which touched lines speak it |
| `:drift [n]` | the amber census — a bare verb lists the lines that disagree with the disk; a number leaps to the Nth; `:diff` asks, `:w` sweeps; the silent beat keeps it live |
| `:git [log [n] \| branch \| tag]` | the repo's truth in one breath — branch, uncommitted count, the last commit's name; `:git log [n]` walks the memory; `:git branch` names the locals, the current starred; `:git tag` counts the milestones (read-only; refuses honestly without git) |
| `:ruler` | toggle the 79/99 column guides |
| `:minimap` | toggle the document's map rail |
| `:theme [name\|n]` | wear a coat — six ship inside (dxn, dracula, gruvbox, nord, solar-dark, solar-light) and YOURS load from `~/.dxn3-themes` (name:base:comment:string:keyword:pane:sel, decimal or hex); by name, unique prefix or 1-based index; a bare verb lists the wardrobe; the choice keeps across nights |
| `:center` | the view centers on your hand — z.'s law, clamped to the edges |
| `:zen` | the quiet — the rail rests, the body breathes; `:zen` wakes it |
| `:wrap` | the fold — long lines break into the pane at the last space or hyphen that fits, and ↑/↓ walk the rows; a second `:wrap` wakes the slide |
| `:crew [n]` | the crew — a number plants that many hands below yours; type once and every hand writes (typing, backspace, enter, delete, `ctrl+u` the word's coat); planting again grows the crew from the last hand; a bare `:crew` bows them out |
| `:count [word]` | the census of a query — a bare verb counts the searchlight's query everywhere; a word counts itself |
| `:stats` | lines, words, chars, dialect, where you stand |
| `:trim` | sweep trailing whitespace, one undo step |
| `:sort` | order the selected lines, one undo step |
| `:rsort` | the selected lines land Z before A — the sort's mirror |
| `:upper` | the selection SHOUTS — one undo step |
| `:lower` | the selection whispers — one undo step |
| `:title` | every word's first letter stands up |
| `:uniq` | collapse lines that repeat back-to-back — whole doc, or the selection |
| `:match` | jump to the bracket's twin — quote-honest, cross-line, honest when it never closes |
| `:s/old/new` | replace every exact old with new on the selection's lines — one undo step; an EMPTY old borrows the find query as the old |
| `:sa/old/new` | the whole document is the bed — the swap's other face; an empty old borrows the find query too |
| `:<line>` | a bare number jumps — `:42` is the goto's absolute form |
| `:rev` | flip the selection's line order, no alphabet invited |
| `:shuffle [seed]` | deal the selection's lines into random order; the seed replays the deal |
| `:indent` | the selected lines step right one level, pure air keeps its silence |
| `:dedent` | the selected lines step back left — up to four spaces each |
| `:lift` | the selection's lines step one line up — no selection rides the hand's line |
| `:drop` | the selection's lines step one line down — the pins ride along |
| `:dup` | duplicate the selection's lines — the copies sit below, the pins stay true |
| `:join` | fold the selection's lines into one — trimmed pieces, single spaces, the hand at the seam |
| `:cases` | find respects case exactly (Aa), or forgives |
| `:help` | list commands |

## Scenes are JSON

A scene is a `.dxn1.json` file — data only, no code:

```json
{
  "name": "level-1",
  "bg": "#0b0e1a",
  "gravity": 1500,
  "magnet": 120,
  "next": "scenes/level-2.dxn1.json",
  "camera": { "x": 200, "y": 250, "zoom": 0.85 },
  "entities": [
    { "name": "hero", "tag": "player", "x": 60, "y": 300, "w": 34, "h": 44 },
    { "name": "lift", "tag": "mover", "x": 620, "y": 372, "w": 140, "h": 20,
      "path": [ { "x": 620, "y": 372 }, { "x": 760, "y": 372 } ], "pspeed": 70 },
    { "name": "gem", "tag": "coin", "x": 340, "y": 290, "w": 22, "h": 22, "color": "#facc15" },
    { "name": "pain", "tag": "spike", "x": 590, "y": 430, "w": 50, "h": 28, "color": "#ef4444" },
    { "name": "out", "tag": "goal", "x": 1590, "y": 180, "w": 40, "h": 70, "color": "#22c55e" },
    { "name": "tip", "tag": "sign", "text": "ride the mover →", "color": "#a78bfa" }
  ]
}
```

Tags: `player` (the hero), `mover` (path-following platform with rider
carry), `coin` (score + magnetism), `spike` (respawn + shake), `goal`
(next-scene transition, locked after one touch), `ball` (perpetual demo
bounce), `sign` (floating text). Tagless entities are solid geometry.
Colors may set `color2` + `"fill": "gradient"`, and `spin` rotates them.
Any entity may carry `"glow": <px>` — a dim halo behind the body (a real
ring on circles, the coins' rect aura elsewhere), patchable per frame
over the wire so a pulse is just a `set`. Any entity may carry
`"flash": <0..1>` — a hit-flash that bleaches the body toward white and
decays at 4/s inside `update`: one wire patch marks a hit, the engine
does the fading, and both rasters agree on the bleach. Any entity may
carry `"alpha": <0..1>` — the body blends toward the scene's own air,
so a scene can ship ghost ledges, fog banks and glass (the playground
hides one above its first ledge), and a wire `set` thins or thickens
it live.

## Engine selftest + gates

```bash
make -C native test      # engine assertions: physics, movers, coins,
                         # magnetism, hazards, transitions, camera,
                         # command grammar, PNG writer vectors
scripts/gates.sh         # the full gauntlet
```

The gates are: a zero-warning `-std=c++23` build, the selftest — including a
**real end-to-end host: the Python SDK spawns a child game that crosses the
pipe and reports home** — every scene must render one real headless frame,
every `next` in the campaign chain must resolve to a real scene file (no
ghost doors), zero electron-era files tracked, and VERSION ↔ CHANGELOG
consistency.

## Layout

```
native/src/spark.hpp/.cpp   the engine: AABB physics, movers + rider carry,
                            coins + magnetism, hazards, goal transitions,
                            camera follow + zoom + decay shake,
                            std::expected scene I/O
native/src/tui.hpp/.cpp     the face: truecolor half-block renderer,
                            gradients, HUD spans, text rails
native/src/logo32.hpp       the mark: the studio emblem as a 32×32
                            truecolor bitmap for the title card
native/src/cmd.hpp          the command bar grammar — honest usage errors
native/src/fx.hpp           the deterministic per-scene starfield
native/src/png.hpp          zero-dependency PNG writer (stored deflate)
native/src/shot.hpp         headless + in-game screenshots
native/src/json.hpp         recursive-descent JSON with \uXXXX → UTF-8
native/src/host.hpp         the ScriptHost: child-process games in ANY
                            language, line-JSON protocol, the IDE frame
                            applier, language runner table
native/src/main.cpp         the studio shell: raw-mode input, fixed
                            timestep, title card, THE ENGINE IDE (editor +
                            live viewport + console), PLAY / INSPECT /
                            FILE VIEW / command modes
native/src/selftest.cpp     engine assertions, including a live SDK child
sdk/dxn3.py                 the Python SDK — one import, whole engine
sdk/dxn3.js                 the JavaScript SDK (NODE_PATH, plain CJS)
sdk/dxn3.hpp                the C++ SDK — compiled games, deque-stable
                            entity pointers
sdk/PROTOCOL.md             the one-page wire contract
sdk/examples/               background · shooter · flappy · bounce ·
                            cards · lightbot · pong
assets/                     the brand: emblem, banner, social card + SVG src
scenes/*.dxn1.json          the nine-scene campaign — data only
scripts/install.sh          the curl one-liner
scripts/gates.sh            the quality gauntlet
```

## History

STUDIO 3 was born as an Electron app with a Python brain (v3.0.01–v3.0.04).
v3.0.05 ported the Spark engine to C++23 and played it in the terminal.
v3.0.06 deleted the Electron, web and Python stacks for good — the studio is
one binary now. v3.0.07 gave the studio its face: the mark descends from the
STUDIO 2 circuit spiral (preserved on the
[`ds2-archive`](https://github.com/DXN1-termux/DXN1-STUDIO/tree/ds2-archive)
branch) with a monolithic 3 carved into it, the title card greets every
launch, the HUD counts your coins, and the command bar whispers usage hints
while you type. v3.0.08 gave the studio somewhere to go: the campaign grew
from three scenes to five — the climb and the gauntlet — and the gauntlet
itself moved into CI, where g++, clang++ and the one-liner installer are
probed on every push. v3.0.09 turned the studio into an engine IDE: boot
into a code editor with your game running beside it, hosted in your own
language — Python, JavaScript, C++23, or anything that speaks stdio JSON —
starting from nothing, live while you type. v3.0.09 is the pivot: the studio became an **engine**.
Bare `dxn3` opens an IDE where you start with nothing, write code in any
language — Python, JavaScript, C++, anything that speaks the one-page
protocol — and it runs live beside your editor; the campaign is now the
demo, the SDKs ship in `sdk/`, and the selftest hosts a real child game
end to end on every run.

MIT — DXN1-termux
