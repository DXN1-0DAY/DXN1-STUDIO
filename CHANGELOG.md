## v3.0.61 — the second chance, spoken (:undo/:redo)

- **`:undo` / `:redo` — the ledger's twins, spoken from the bar.**
  ctrl+z and ctrl+y had the second chance to themselves; the bar now
  speaks it too. ONE law with the keys: the same walk, the same
  receipts ("engine: undo — typing · 4 steps left"), the same honest
  refusals ("nothing to undo", "nothing to redo"). The grammar puts
  them in the no-argument family (`:redo now` is refused with the
  family's usage), the whisper names the twins ("ctrl+z's twin",
  "ctrl+y's twin"), and :help's verb list finally carries :hist beside
  them (it shipped v3.0.58 without its name in the list — a word owed).
- Selftest group 69 (9 asserts) — 626 → 635 groups. Smoke section
  13a2 (4 checks) — 99 → 103: the walk there and back, the honest
  refusal, and the fold surviving the round trip on the real screen.

## v3.0.60 — one law for every whisper

- **`whisperOffer` — the completion clip law, written once.** Four
  whispers (:recent, :bm's pins, :snip's shelf and :open's ledger)
  carried the same eleven lines: join with " · ", end the line at the
  FIRST entry that does not fit the bar's honest width, never a cut
  word, never a half description. Now they all call one function, and
  the law has its own selftest target — a bar too narrow for even one
  entry holds its tongue, an entry fits a bar of exactly its width,
  and a full whisper leaves the line untouched.
- Selftest group 68 (5 asserts) — 621 → 626 groups. Smoke stays at
  99 (every whisper's outward word is byte-identical).

## v3.0.59 — the counting sort

- **`:sort` and `:rsort` grew numeric awareness.** When EVERY line of
  the bed opens with a number (air may lead it; decimals and
  negatives count), the order is by that number — "2" lands before
  "10", the way humans count, not the way bytes land, and 1.10 sorts
  as the 1.1 it truly is. Ties keep the byte order; negative numbers
  open honestly. One mixed line and the whole bed stays byte-honest —
  the classic sort, no surprises. The receipts name the law ("sorted
  3 lines by their numbers — 2 before 10"), and so do the bar's
  whispers.
- Selftest group 67 (15 asserts) — 608 → 621 groups. Smoke stays at
  99 (the letter beds' receipts still speak their law).

## v3.0.58 — the ledger, listed

- **`:hist` — the second chance, listed.** One honest line in the
  console: the undo ledger's names, NEWEST first ("join · drop ·
  typing · paste …"), capped at eight with the deeper truth confessed
  ("… +5 deeper"), the depth spoken in steps ("[12 steps back]"), and
  the redo's head riding after the divider when undo has already
  walked. An untouched doc refuses with the way out ("every edit you
  make lands here — ctrl+z walks it back"). The names are the same
  words the undo receipt speaks — the ledger and the walk share one
  vocabulary.
- Selftest group 66 (7 asserts) — 601 → 608 groups. Smoke grew the
  ledger section (the fold on top, the depth honest) — 97 → 99
  checks.

## v3.0.57 — the pen

- **`:w` and `:wq` follow the session's work.** The pen saves the
  studio's document when the studio has been on stage (it IS the boot
  stage for interactive runs) and the scene for play-only sessions —
  so `:w` in the editor finally means the SCRIPT, not the JSON behind
  it. A name saves AS that name: `:w other.py` writes the doc there,
  adopts the path, and the ledger remembers it; a refused write never
  steals the doc's own name. `:wq` saves and sleeps; a failed pen
  never quits — the honest error stays on the bar.
- **The .bak law is every document's now.** The scene always kept a
  `.bak`; scripts now do too — every save (the bar's pen, ctrl+s,
  even the auto-run's silent save before hosting) copies the file
  that exists to `<path>.bak` before writing. A first save has no
  past to keep; the receipts say "(.bak kept)" only when it is true.
- **The sdk is found beside the binary, not beside the cwd.** The
  hosted game's `PYTHONPATH`/`NODE_PATH` now resolve from the
  studio's own installation (<repo>/native/build → <repo>/sdk, with
  the cwd as fallback) — a studio launched from any directory hosts
  `from dxn3 import *` the same way. Found by the smoke's new
  hermetic harness: it now runs the studio in a private tmp dir, so
  saves never dirty the repo.
- Selftest group 65 (2 asserts) — 599 → 601 groups. Smoke grew the
  pen sections (the save, the .bak, the save-as, the disk truth, the
  :wq sleep, the fresh-studio exit) — 87 → 97 checks.

## v3.0.56 — the ride in the hands

- **alt+↑ / alt+↓ — :lift and :drop without opening the bar.** The
  xterm modifier digit 3 joins the arrow grammar (shift=2 selects,
  ctrl=5 nudges the view, alt=3 now rides). The bed law is the bar's
  own: the selection's lines move as one block, or the hand's line
  when nothing is selected; the pins ride along (the displaced
  neighbor's pin lands where the neighbor went); the hand lands on
  the block's head; each ride is ONE undo step ("lift"/"drop"); the
  edges refuse with the honest receipt — "nothing above to lift
  into" / "nothing below to drop into" — never a phantom step, and
  the receipts name the ride exactly as the verbs do.
- Selftest group 64 (11 asserts) — 588 → 599 groups. Smoke grew the
  ride-in-the-hands section (the edge refusal, the lift, the tail's
  truth, the drop home, the clean handoff) — 81 → 87 checks.

## v3.0.55 — the hunt

- **F3 and shift+F3 — the walk that outlives the bar.** Close the
  searchlight with esc and the hunt goes on: F3 hops to the next hit
  of the last query, shift+F3 walks back, both wrapping around the
  file. The hits are recomputed live before every step (the doc may
  have moved since the light rested), the console speaks the count
  ("hit 2/7 — line 12") because with the bar down there is no
  counter, and the walk is a look — nothing dirties, nothing undoes,
  any selection is left behind like every hop. F3 works inside the
  bar too, and the bar itself now whispers "enter/F3 next".
- **THE STRICT LAW — a real find bug fixed.** enter used to aim the
  light at the first hit at/after the hand and then step PAST it —
  so a hand standing BETWEEN two hits skipped its own next hit and
  wrapped early. One law now rules both stances: the next hit is the
  first one STRICTLY after the hand (the previous hit, strictly
  before, for shift+F3). A hand on a hit walks to the following one;
  a hand between hits lands on its next one. The xterm grammar gets
  F3 too: SS3 R (ESC O R) walks as well, while a CSI R cursor
  position report stays silent.
- Selftest group 63 (15 asserts) — 573 → 588 groups. Smoke grew the
  hunt section (the count, the landing's inverse video, the wrap,
  the walk, the walk back) — 72 → 81 checks.

## v3.0.54 — the ride of the jump

- **`:goto +N` and `:goto -N` — the jump rides from where the hand
  stands.** The absolute form stays 1-based (`:goto 42` is line 42);
  the relative form climbs or descends N lines from the hand, both
  clamping to the document — a jump never lands outside the world.
  The receipt speaks the ride ("jumped down 3 — now at line 8"), the
  whisper names the form, and zero rides nothing (refused with the
  honest usage).
- Selftest group 62 (9 asserts) — 564 → 573 groups. Smoke grew the
  jump block (absolute, +3 down, -2 up) — 69 → 72 checks.

## v3.0.53 — the fold

- **`:join` — the selection's lines say it once, in one breath.**
  Each line trimmed, the pieces separated by one honest space, pure
  air contributing nothing. The bed is the selection's lines; with
  no selection the hand's line folds with the one below (vim's J
  law — the fold's natural home). A same-line bed folds nothing, a
  bed on the last line has nothing below — both refuse without a
  phantom step. The uniq's pin law speaks (a pin on a folded line
  dies, the world beneath slides up); the hand rests at the SEAM,
  where the first fold landed.
- Selftest group 61 (13 asserts) — 551 → 564 groups. Smoke grew the
  fold section (the receipt, "zz aa" at the seam) — 67 → 69 checks.

## v3.0.52 — the echo

- **`:dup` — the selection's lines say it twice.** The copies land
  directly below the bed, the originals keep their pins (a pin marks
  a line, not its echo), and the world beneath slides down by the
  bed's size. With no selection the hand's line is the bed (the
  ride's law); the hand lands on the COPY's head — the fresh work is
  the echo. Never refuses: the hand's line always says something
  twice.
- A real bug fixed on the way in: the first implementation inserted
  the bed's iterators into their own vector — reallocation dangled
  the range and the copies landed as garbage. The bed is copied
  first now; the selftest caught it in both beds.
- Selftest group 60 (11 asserts) — 540 → 551 groups. Smoke grew the
  echo section (the receipt, original and echo in view) — 65 → 67
  checks.

## v3.0.51 — the ride

- **`:lift` and `:drop` — the selection's lines step one line up or
  down.** No alphabet, no mirror: the bed slides one neighbor over
  and the neighbor walks around it. The bed is the selection's lines
  — and with no selection, the hand's line (the move's natural
  home). The pins RIDE their lines and the displaced neighbor's pin
  lands where the neighbor went, the ledger re-sorted (the move is a
  cousin of the flip); the hand rides the block's head; a bed
  pressed against the edge takes no snapshot and no step.
- **The pins walk back through undo.** A real fix the ride flushed
  out: the undo snapshot carried the document and the hand but NOT
  the pins — so undoing a pin-moving operation (uniq, rev, and now
  lift/drop) left pins pointing where the redo-world had put them.
  IdeSnap now carries the ledger, and undo/redo restore it: every
  step back in time takes the pins with it.
- Selftest group 59 (17 asserts) — 523 → 540 groups. Smoke grew the
  ride section (the drop, the neighbor's slide, the lift home) —
  61 → 65 checks.

## v3.0.50 — the shelf that speaks

- **`:snip ` whispers the shelf, described.** Typing `:snip ` in the
  bar now speaks every snippet name with its one-line description —
  "fn — a named function · tick — the every-frame hook · … · main —
  a whole playable scene" — the same words for every dialect (a
  "tick" is the every-frame hook whether the file speaks py, js or
  cpp). The typed prefix narrows by NAME with the description riding
  along; the ledger's clipping law ends the line before a cut word,
  never a half description; and the shelf is the file's own dialect
  (cpp speaks five, js seven, py eleven). The shelf also speaks BARE
  now (the gallery's law) — before this round it waited for a first
  letter.
- Selftest group 58 (10 asserts) — 513 → 523 groups. Smoke +2 (the
  described bare shelf, the narrowed description) — 59 → 61 checks.

## v3.0.49 — the breath

- **`:indent` and `:dedent` — the selection's lines step one level
  right, or back.** The transform family's sibling: the same bed (a
  selection names lines — and a same-line one counts, because one
  line is a fine bed for a breath; tab and shift+tab already own the
  hand's line, the verbs own the selection's), ONE restore point
  named for the verb, the hand resting at the bed's head and riding
  the shift, the selection let go. The trim's law honored both ways:
  a line of pure air keeps its silence (no indent gathers on
  emptiness), a line with no leading air gives dedent nothing — and
  what would not move is counted BEFORE the snapshot, so a bed with
  no work takes no phantom step. The pins hold their lines — a
  breath moves no line.
- Selftest group 57 (19 asserts) — 494 → 513 groups. Smoke grew the
  breath section (the count, the four honest spaces, the round trip,
  the refusal) — 54 → 59 checks. One timing law recorded: a verb's
  auto-run spark burst still flies when the NEXT verb's frame is
  read — quiet-settle 2.5s before asserting body text.

## v3.0.48 — the diamond button

- **The pin's diamond is a button.** A plain click on the gutter's
  edge of a pinned line — the exact cell the `◆` rides — pulls that
  pin. A look, never an edit: the hand stays put (the click is spent
  on the ledger, not on the cursor), the receipt speaks ("pin pulled
  from line N"), and shift+click keeps its extend-the-selection law.
  A click on an unpinned line's gutter edge keeps the old law — the
  line start.
- The pointer's three gutter zones now speak cleanly: the diamond
  pulls, the number takes the line start, the code lands the hand.
- Smoke grew the diamond section (the ◆ visible, the pull, the
  stationary hand, the receipt, the sibling pin unharmed) — 49 → 54
  checks. 494 selftest groups stand.

## v3.0.47 — the flip

- **`:rev` — the selection's lines walk end for end.** The sort
  family's bed and refusals, but no alphabet has a say: the first
  line lands last, the last lands first. ONE restore point named
  "rev", the hand at the block's head, the selection let go.
- **The pins ride the flip to their mirrors** — the content-following
  law the collapse taught, applied to the one move that can unsort
  the ledger: each pin lands at `r0 + (r1 − m)`, and the ledger is
  re-sorted so the ":marks order" invariant survives the flip.
- Selftest group 56 (11 asserts: the flip, the mirrored pins, the
  refusals, the undo that lands the hand where it stood, the
  grammar) — 483 → 494 groups. The smoke grew the flip of the
  sort/rsort round-trip tail — 47 → 49 checks.

## v3.0.46 — the collapse

- **`:uniq` — lines that repeat back-to-back say it once.** A
  multi-line selection is the bed; NO selection means the whole
  document (uniq's natural home — its difference from the sort
  family, told out loud in the docs). The trim's law: nothing to
  collapse → no snapshot, no phantom step. ONE restore point named
  "uniq", the hand resting where the first line fell.
- **The pins speak the structural law honestly.** A pin on a fallen
  duplicate dies; a pin on a kept line rides the line to its new
  home (a newHome map, not a blind slide); a pin beneath the bed
  slides up by the count that fell. Undo still clamps the ghosts.
- Selftest group 55 (13 asserts: the whole-document law, the
  interleaved survivor, the selection bed, the pin map, the no-
  phantom law, the grammar) — 470 → 483 groups. The smoke grew the
  echo sweep (two typed "zz"s collapse to one, the view clamping up
  a row as the doc shrinks) — 45 → 47 checks.

## v3.0.45 — the case

- **`:upper`, `:lower`, `:title` — the selection changes its voice.**
  One law for three verbs: a selection is the bed (a same-line one
  counts — case is an in-line edit, unlike the sort family), ONE
  restore point named for the verb, the hand resting at the
  selection's head, the selection let go. Title stands each line's
  word-starts up and quiets the rest (`foo_bar 9lives` →
  `Foo_Bar 9Lives` — underscore and digits start words).
- The trim's honest law applies: what would not change is counted
  BEFORE the snapshot, so a letterless selection takes no phantom
  undo step. Refusals name the way out.
- Selftest group 54 (15 asserts: the three voices, the two-line bed,
  the edges holding, the word-start law, the no-phantom law, the
  grammar) — 455 → 470 groups. The smoke grew the voice dance
  (`dxn3` → `DXN3` → `dxn3` through the real bar) — 43 → 45 checks.

## v3.0.44 — the gallery

- **`:template` whispers the gallery.** The bar's eighth whisper
  source — type `:template ` and every starter's name speaks
  (`blank · shooter · cards · background · flappy · bounce · pong`),
  the typed prefix narrowing the list by the SAME law the verb's
  resolution follows: an exact name wins, a unique prefix resolves,
  and the whisper shows you all three outcomes before enter does.
- **The header counts the pins.** Next to `· zen` and `· sel N`, a
  document carrying pins now carries `· pins N` — the ledger's size
  at a glance, no `:marks` needed in big files.
- Smoke grew the gallery checks (bare whisper + narrowed prefix,
  through the real bar) and the pin-count header checks — 39 → 43
  checks. 455 selftest groups stand.

## v3.0.43 — the choir

- **The pins whisper: `:bm` completes itself as you type.** The bar's
  seventh whisper source — type `:bm ` and the ledger speaks
  `1) Ln 37 · 2) Ln 40` in the `:marks` order; the typed number
  narrows the choir to the pins it names, and the bar's honest width
  ends the line (the SAME clipping law as the ledger's whisper: the
  first entry that does not fit stops the line). An empty ledger
  stays silent — bare `:bm` already refuses with the way out.
- The leap verbs were already honest; now they are discoverable
  BEFORE you know the numbers — the whisper is the `:marks` list,
  one row earlier in the story.
- Selftest group 53 (7 asserts: the full choir, the narrowing
  prefix, prefix-by-head, the silent misses, the narrow bar, the
  one-entry fit, the pinless silence) — 448 → 455 groups. The smoke
  grew the whisper checks (bare + narrowed, through the real bar) —
  37 → 39 checks.

## v3.0.42 — the mirror

- **`:rsort` — the selection's lines land Z before A.** The sort's
  honest mirror: the same bed (a multi-line selection), the same
  refusals (no selection, a same-line one), the hand resting at the
  block's head, the selection let go, and ONE restore point of its
  own named "rsort" — undo unorders exactly as it stood. `:sort`
  then `:rsort` on the same bed is a clean round trip.
- The bar whispers the descending law (`:rsort — the selected lines
  land Z before A, one undo step`), `:help` names the verb, and the
  README's command table and housekeeping bullet speak it.
- Selftest group 52 (9 asserts: the descending order, the named
  restore point, the undo, the released selection, the grammar) —
  439 → 448 groups. The smoke grew an rsort section (the round trip
  through the real bar) — 35 → 37 checks.

## v3.0.41 — the quiet

- **`:zen` — the console rail hides and the body breathes.** Two more
  rows of code on every screen: the rail's rows join the viewport, and
  the pointer speaks the same geometry (a click on the old rail row
  now lands in the document, the drag's edge sensor watches the body's
  new bottom, and pgup/pgdn follow the taller page). The header
  carries a small `· zen` so the mode never hides ITSELF.
- **The quiet is honest, not blind.** The searchlight keeps its own
  row while it is up — a query you cannot see is a query that cannot
  end. Receipts gather silently until the quiet ends; waking the rail
  (`:zen` again) speaks "the rail is back — everything zen gathered
  waits below". The bar whispers the way in and the way out.
- **The smoke is now a shipped artifact.** `scripts/smoke.py` drives
  the REAL binary through a real pty — 35 checks across boot, zen
  (geometry, searchlight, pointer, wake), the live auto-run, the
  pins, the bar's refusals and `:sort`, ending on a clean exit. It
  encodes the laws that cost sessions to learn: the SPLASH LAW (the
  emblem eats the first keypress — wait it out), the MODE LAW (ESC in
  play quits; the bar opens from play), the COALESCING LAW (ESC and
  the next key must not share a pty frame; a coalesced arrow burst is
  one flag, not three), the SGR LAW (text row = doc line + 1; the
  frame parser walks the renderer's full-repaint protocol), and
  transition-frame dropping with a trimmed capture tail.

## v3.0.40 — the pins

- **Bookmarks: lines you pin so the hand can leap back.** `:mark`
  plants a pin on the hand's line — a second `:mark` (or `ctrl+F2`)
  pulls it. `F2` leaps to the next pin, `shift+F2` walks back, both
  wrapping the ends; `:bm N` takes the Nth pin (the `:marks` order),
  a bare `:bm` takes the next. `:marks` lists the ledger.
- **The pins are visible.** A pinned line's number burns amber in the
  gutter and a `◆` rides the gutter's edge (the hscroll `…` waits —
  the pin wins); on the minimap the pinned row carries an amber bar
  drawn last so it never drowns in the shape's bars.
- **The pins follow the document.** Every structural edit speaks the
  same law: lines landing above a pin slide it down (enter, paste,
  duplicate, snippet, block insert), lines cut beneath take the pin
  along (backspace/del joins, line cut, selection cut), a pin inside
  a cut dies with its line, and undo/redo prune pins the restored
  document never had. Loading a document starts a fresh ledger.
- **A look, never an edit.** Planting, pulling and leaping never
  dirty the document, never take an undo step, and every leap speaks
  its landing in the console; refusals (pinless leaps) name the way
  out (`:mark`).
- Selftest: group 50 (plant/pull/has, sorted+dedup ledger under
  out-of-order planting, wrap both ways, pinless refusals, the
  shift/erase/clamp laws, F2/shift+F2/ctrl+F2 through the real
  ideKey with no dirty and no undo) — 413 → 433 assertion groups.
- Discoverability: README command table + keys, `--help` keys card,
  the bar's usage hints, the console rail hint (F2 pins), `:help`.

## v3.0.39 — the fresh slate

- **ctrl+l wipes the console.** The console rail is where your game
  speaks — and where noise gathers: ticks, prints, stale engine
  notes. One keystroke clears the slate so the NEXT traceback reads
  at a glance, and the fresh console says so ("the console is fresh
  — ctrl+r replays your game"). The wipe is furniture, never an
  edit: the document never hears about it, nothing dirties, nothing
  undoes. Discoverability rides along — the `--help` keys card and
  the README name ctrl+l.
- Selftest: group 49 (the wipe with its receipt, no dirty / no undo
  step / no document change, and a second wipe staying one honest
  line) — 409 → 413 assertion groups, all green.

## v3.0.38 — the open book

- **Documentation caught up with the editor.** The README's command
  table now lists EVERY studio verb — `:open` (with its new bare
  form), `:recent`, `:template`, `:snip`, `:goto`, `:ruler`,
  `:minimap`, `:stats`, `:trim`, `:sort`, `:cases` — instead of
  hiding the IDE's vocabulary behind the play-mode verbs. The
  feature bullets tell the searchlight's two moods (:cases and the
  `(Aa)` marker), the ledger's bare `:open`, the honest wide gutter,
  the second wind, and the housekeeping verbs; the keys paragraph
  names them all in one breath.
- Polish: the header position line's doc example now shows the
  selection counter too (`Ln 12 · Col 8 · sel 87`), so a reader
  meets the drag's honest count before their first drag.
- Zero code changes — the binary speaks exactly as 3.0.37 spoke;
  409 assertion groups stand green.

## v3.0.37 — the ordering

- **`:sort` orders the selected lines.** Select a block (drag or
  shift+arrows), speak one word, and its whole lines stand in order,
  byte-honest A before B — the way every editor's sort-lines command
  speaks. The world outside the selection rests untouched, the hand
  lands at the head of the ordered block, the selection lets go, and
  ONE restore point named "sort" carries the whole ordering back on
  undo. Without a real bed the verb refuses honestly — no selection,
  or a same-line one (a single line is always already in order) —
  with the way out named in the console ("select the lines to sort
  first — shift+arrows, or drag"), never a phantom step.
- Discoverability rides along: the :help card names :sort and the
  bar's usage hint explains it while you type it.
- Selftest: group 48 (the honest count, the range ordered while the
  outside rests, the hand's landing, the named restore point, undo
  unordering exactly, and both refusals without phantom steps) —
  402 → 409 assertion groups, all green.

## v3.0.36 — the honest case

- **`:cases` flips the searchlight's sensitivity.** By default the
  light forgives — the beginner way, "hello" finds HELLO — and one
  command turns it strict: only the honest exact casing answers,
  with an "(Aa)" marker on the find rail so you always know which
  law is live. Flipping re-aims the light the INSTANT it turns (the
  hits and the current one are recomputed mid-search, no reopening,
  no retyping), and the console receipt names both directions
  ("find is case-SENSITIVE — Hello only greets Hello" / "find
  forgives case — hello finds HELLO"). The :help card and the bar's
  usage hint name the verb before enter is ever pressed.
- The law stays pure: `ideFindAll` reads `findCase` from the state —
  sensitive search is a straight substring read, forgiving search is
  the same lowercase dance as before, and nothing about hit order,
  the forward-aim, or the wrap changes.
- Selftest: group 47 (3 hits forgiving, the exact one strict with
  its row and column, flipping back reopens the net, and the
  forgiving light is deaf to casing in BOTH directions) — 397 → 402
  assertion groups, all green.

## v3.0.35 — the sweep

- **`:trim` sweeps every line's trailing whitespace.** Tail spaces
  and tabs come off every line; a line of pure air goes truly blank;
  clean lines rest untouched. The whole document is ONE honest
  restore point named "trim" — undo puts the air back exactly as it
  stood — and a document with nothing to sweep is refused WITHOUT a
  phantom step ("nothing to trim — the doc is already clean"). The
  console receipt names the work: "trimmed N lines of trailing
  air". Discoverability rides along: the :help card names :trim and
  the bar's usage hint explains it before enter is ever pressed.
- The verb's law lives in ONE pure function: `ideTrimTrailing` in
  edit.hpp counts what would move BEFORE taking the snapshot (the
  undo step must hold the air), sweeps, clamps the cursor to its
  line's new honest end, and returns the count.
- Selftest: group 46 (the honest count, tails off / pure air blank /
  clean lines rest, one named restore point, the cursor clamp, the
  clean-document refusal with no phantom step, and undo putting the
  air back) — 391 → 397 assertion groups, all green.

## v3.0.34 — the second wind

- **A sustained autoscroll pull doubles its pace.** Drag to the
  viewport's edge and hold: for the first 1.2 seconds the pull walks
  one line every 70ms — careful, precise; past 1.2s the SECOND WIND
  arrives and the notches come every 35ms — long documents are
  reached at speed. The law stays honest everywhere: the wind is
  spent by a release, by a stall (the dt > 0.5s guard), and by the
  hand leaving the edge — every restart walks slowly again, so short
  documents can never be skipped past. No new keys, no new state the
  hand must learn: the meter (`dragHold`) simply remembers how long
  the pull has been sustained, and the period halves.
- Selftest: group 45 (24 frames at one period each: 17 slow + 14
  fast notches with the ride contract intact; release → hold and
  meter rest; a fresh press walks slowly again — 5, not 10; the
  stall's honest reset; leaving the edge spends the wind) — 385 →
  391 assertion groups, all green. The float law rides along: 0.035
  is exactly half of 0.07 in binary, so the accelerated meter never
  drifts.

## v3.0.33 — the bare open

- **A bare `:open` reopens the ledger's head.** The verb you used to
  refuse without a file now answers with what you had LAST — one
  word, your most recent file, back on the stage. An empty ledger
  still refuses, honestly, with the way out ("name a path — :recent
  lists the ledger"). The grammar follows the truth: `:open`'s
  argument is optional now, exactly like `:recent`'s.
- **The :open whisper speaks YOUR files first.** Type `:open bo` and
  the ledger's matches whisper ahead of the filesystem's — full path
  OR basename carries the prefix, ledger order, then the cwd's
  scripts and the gallery's examples fill in behind, deduped (a path
  the ledger already spoke is never spoken twice), clipped to the
  bar's honest width by the SAME law as the :recent whisper. A bare
  `:open` whispers what enter WILL open — the head, or "(the ledger
  is empty — name a path)". The bar never lies ahead of the truth.
- Selftest: group 44 (the bare :open parse, ledger-before-filesystem
  order, dedup, the ledger-only ghost path that still whispers, the
  disk-only basename match, the silent ghost, the narrow bar, the
  empty ledger) plus the two assertions that rode along — the old
  ":open without a file is refused" now asserts the new law, and the
  version quad moved — 377 → 385 assertion groups, all green.

## v3.0.32 — the wide gutter

- **The gutter earns its width.** Four columns carried line numbers
  honestly to 999; now a bigger document EARNS its extra digit, one
  notch at a time — five columns from line 1000, six from line 10000
  (the draw speaks the number with `%*d`, so the digits simply fit).
  The rule lives in ONE place: `ideGutterWidth(lineCount)` in
  edit.hpp, and everything that speaks the body's geometry reads it —
  the draw, the pointer's cell translation (a click on a 1200-line
  doc lands one column further right, and lands TRUE), the 79/99
  ruler guides, the selection glow, the bracket glow, the cursor and
  the searchlight's wake. The pane's code window pays for the digit
  honestly: textW = editW − 1 − G − map rail, so a wide gutter can
  never push the minimap or the divider out of the pane.
- Selftest: group 43 (the four boundaries — 999/1000/9999/10000 — the
  empty and negative counts, and the pane-width arithmetic for a
  1200-line document) — 371 → 377 assertion groups, all green.

## v3.0.31 — the leap

- **ctrl+\\ jumps the hand to the partner bracket.** The partner
  glow's keyboard sibling arrives: with the hand on (or just past) a
  bracket, ctrl+\\ lands it on the matching ( [ { across any
  distance — the SAME honest match rule as the glow (the cell at the
  cursor, then the one behind it; quotes stay out of it). A leap is a
  look, never an edit: nothing dirties, nothing undoes, and any
  selection lets go when the hand flies. A bracket with no partner
  refuses the leap with the hand unmoved — the glow never lies about
  a pair, and neither does the leap.
- **Polish — discoverability.** The editor's rail hint names the leap
  ("ctrl+\\ leap") next to run/undo/clipboard, and the :help keys
  card gains its own line.
- Selftest: group 42 (the round trip, the cross-line pair, the
  behind-the-hand probe, the partnerless refusal, the plain-text
  refusal, the selection release) — 363 → 371 assertion groups, all
  green. Smoke: section 12i leaps a live hand across flappy.py
  (102 → 105 checks).

## v3.0.30 — the whisper

- **:recent completes itself while you type.** The command bar's
  whisper family grows its last member: type `:recent bo` and the
  bar speaks `sdk/examples/bounce.js` before enter is ever pressed —
  full paths whose path OR basename carries the prefix, ledger order,
  joined with " · ", clipped to the width the bar honestly holds. A
  bare `:recent` whispers the head of the ledger; an empty ledger
  says "(the ledger is empty)"; a ghost stays silent because enter
  will refuse it and the bar never lies ahead of the truth.
- Selftest: group 41 (basename and full-path prefixes, the ordered
  bare whisper, the tail name, the silent ghost, the empty ledger,
  the narrow-bar clip) — 355 → 363 assertion groups, all green.
  Smoke: section 12h watches the live bar whisper (99 → 102 checks).
- **Polish — the hint yields.** The bar's usage hint no longer bleeds
  through behind a shorter whisper: the whisper paints alone when it
  speaks, and the usage speaks only when the bar is silent.

## v3.0.29 — the autoscroll

- **A drag at the edge pulls the unseen into view.** The mouse
  vocabulary is complete: while the button is held and the hand parks
  on the viewport's top or bottom row, the view slides toward the
  unseen lines — one honest notch every ~70 ms, metered by a
  wall-clock accumulator. The hand IS the edge: every notch the slide
  reveals, the hand takes, so the selection grows from the anchor
  exactly like every desktop editor's autoscroll. The wheel's pager
  contract holds (the doc never dirties, the hand never leaves
  sight), a stationary press never pulls (a real drag needs an
  anchor), a long gap is an honest reset — never a catch-up jump —
  and the void clamp still ends every pull at the last full page.
- **Polish — the header counts.** While a selection rides with the
  hand, the header speaks its honest size: "Ln 3 · Col 4 · sel 87".
  A drag always says how much it holds, live.
- Selftest: group 40 (the pull metered, the bare-press refusal, the
  stall reset, the upward ride home, the void clamp, the sel counter)
  — 344 → 355 assertion groups, all green. Smoke: section 12g drives
  a real edge-park through the pty (94 → 99 checks) — the park's
  SGR row is 28, the body's last row, not 27 (the coordinate the
  first draft got wrong; the app's honest no-op taught the test).

## v3.0.28 — the guard

- **ESC owns its frame.** A bare ESC is a mode key, and when a busy
  pty delivers it coalesced with typing (the app stalled past a
  keypress burst), the text belonged to the next frame — but the
  editor happily typed it into the live document FIRST. The studio's
  own gate caught the result: a smoke run once typed `:recent` into
  bounce.js and the auto-run saved it. Now `ideKey` returns the
  moment it sees an ESC: nothing that follows an ESC in the same
  breath may touch the document. The corrupted example was restored
  from history and the guard keeps every document honest from here
  on.
- Selftest: unchanged (344 groups — the guard is a refusal, and the
  smoke's 94 checks now run clean with the example files byte-pristine
  through every drag, wheel and ledger step).

## v3.0.27 — the ledger

- **:recent — the studio remembers.** Every document this studio has
  hosted (the boot file, every template, every `:open`) lives in a
  twelve-name ledger, most recent first. `:recent` reads it aloud in
  the console rail; `:recent <prefix>` reopens — an exact name wins,
  a unique prefix (of the path OR the bare file name — hands think
  in file names) resolves, an ambiguous prefix lists its matches,
  and a ghost is refused honestly with a flash. Reopening a file
  moves it back to the front; the ledger never grows past twelve.
  One honest code path (`openScript`) serves both `:open` and
  `:recent`, so the stage-taking, the searchlight reset and the
  ledger-keeping can never drift apart.
- Selftest: group 39 (most-recent-first, dedup-to-front, the
  twelve-name cap, empty paths ignored, exact/unique/ambiguous/
  ghost resolution) — 336 → 344. Smoke: 90 → 94 checks — :open a
  real file, the ledger lists it, `recent bounce` reopens it, a
  ghost is refused.
- QA note: a refusal flash renders on the bottom row — which the
  IDE's console rail paints over. The verb therefore only takes the
  stage when it has something to SHOW (the list); refusals flash in
  play mode where they can be seen.

## v3.0.26 — the drag

- **Drag selects.** Button-motion tracking (`?1002h`, off at exit)
  completes the mouse: press where the selection starts, sweep, and
  the selection rides the hand cell by cell — across lines, through
  the horizontal slide, glow and all. Release, and the selection
  stays exactly where you left it; a plain click-press-release never
  selects (standard). Motion without the button is hover and moves
  nothing. The press/drag cells share one translation path with
  clicks, so the gutter, the map rail and the horizontal slide all
  speak the same geometry.
- Selftest: group 38 (press remembers, drag selects from press to
  hand, never dirty, release keeps the selection, hover moves
  nothing, plain clicks select nothing) — 330 → 336. Smoke: 85 → 90
  checks — press lands Ln 2, the drag rides to Ln 3 · Col 4, the
  release keeps the hand, hover moves nothing, zero leaked bytes.

## v3.0.25 — the wheel

- **The mouse wheel rolls.** SGR buttons 64/65 (wheel up/down) slide
  the editor's view three lines per notch — and in the file view too.
  The pager contract holds: the hand is never lost out of sight, so a
  scroll that would leave the cursor behind carries it along the
  edge (`ideScroll`, pure and selftest-covered). Looking around —
  clicks or wheel — never dirties the doc; your game never re-runs
  because you moved.
- **A real bug died on the operating table.** `ideScroll`'s first
  draft clamped the view to `lines − 1` while the draw clamps to
  `lines − page`; on documents that fit the viewport the two
  disagreed, the top oscillated, and the wheel died after one notch.
  The smoke caught it; the fix makes both maxes the same.
- Selftest: group 37 (ride down, ride home, the void clamp, zero
  no-op, the hand mid-view stays) — 323 → 330. Smoke: 80 → 85
  checks — flappy returns for the wheel (the ceremony's 16-line doc
  honestly has nothing to scroll), 8 down-notches show line-40's
  gutter with the hand riding to Ln 25, 8 up-notches come home, and
  no wheel bytes ever leak into the document.

## v3.0.24 — the pointer

- **The studio hears the mouse.** SGR click tracking (`?1000;1006h`,
  disabled on exit) feeds the parser real clicks: a left click in the
  code lands the hand on the exact cell (horizontal scroll included),
  a click on the gutter takes the line start, a click on the minimap
  jumps to the doc line under the hand, and a click in the game's
  viewport, console or header is nobody's — swallowed whole.
  `shift+click` extends a selection from the old hand, exactly like
  the shift+arrows; a bare click lets the selection go. Looking
  around never dirties the doc: no re-run of your game follows a
  click.
- **A latent bar bug dies with it.** The command bar never parsed CSI
  sequences, so an arrow key's `ESC[` faked a bare ESC and slammed
  the bar shut mid-thought. The bar parses now: a BARE esc still
  closes it, but arrows, mouse reports and DSR answers are swallowed
  whole, never leaked.
- Selftest: group 36 (click lands, wild clicks clamp, click
  deselects, shift+click extends, clickless frames leave the hand) —
  317 → 323. Smoke: 76 → 80 checks — SGR presses written straight
  into the pty land Ln/Col deterministically (code, gutter, map) and
  viewport clicks prove no leak and no dirty.

## v3.0.23 — the map

- **The minimap rides the right edge.** A six-column map of the whole
  document lives inside the editor pane's right border whenever the
  terminal is wide enough to spare it (split mode, 110+ columns).
  One doc line is one map row; leading whitespace compresses 2:1 so
  deep nests stay inside the rail, and text compresses to half its
  length rounding UP so even one character shows. The viewport's rows
  carry a soft band and burn brighter, the cursor's row is the
  brightest bar on the map, comments speak gray, find hits glow
  amber, blank lines keep one dim dot so the rows stay anchored. The
  map slides to keep the cursor centered once the doc outgrows the
  pane and never slides past either end. `:minimap` toggles it.
  The math (`ideMiniMap`) lives in edit.hpp, pure and selftestable —
  main.cpp only paints.
- **The undo receipt names the move.** Every restore point now
  carries a label — typing, backspace, enter, delete, selection,
  comment, duplicate, word bite, forward bite, indent, dedent,
  snippet, cut, paste — and `ctrl+z` says `undo — paste · 3 steps
  left` instead of a blind count. Labels ride the redo branch too,
  so `ctrl+y` speaks the same name coming back.
- **The shelf whispers from the rail.** A snippet word ending at the
  cursor (`tick`, `key`, `fn`, …) now names its boilerplate in the
  console rail's right seat — `⇥ tab expands 'tick'` — so the tab
  trigger is discoverable before you know it exists. No word, no
  whisper; the editor is not a barker.
- Selftest: groups 34 (bar math: 2:1 indent compression, blank dots,
  comment classification by the file's own prefix, hit glow, centered
  slide, viewport band, degenerate widths) + 35 (every undo label,
  receipts through undo AND redo, whisper/ghost silence) — 292 → 317.
  Smoke: 68 → 76 checks — the OSC 52 payload is now DECODED and
  compared against the selection, and the map's divider and bars are
  asserted present, gone (`:minimap off`), and back.

## v3.0.22 — the bridge

- **The system clipboard hears you.** `ctrl+c` and `ctrl+x` now also
  emit an OSC 52 escape carrying the clip (base64, `ESC]52;c;…ST`) —
  terminals that honor it (kitty, alacritty, wezterm, foot, iTerm2,
  Windows Terminal…) keep the OS clipboard in sync with the studio's.
  The internal ring stays the paste truth: `ctrl+v` pastes from the
  studio, so a terminal without OSC 52 support loses nothing.
  `ideClipText` joins the clip's lines and `ideBase64` encodes them
  honestly (RFC 4648, with the honest `=` padding).
- **An empty paste speaks up.** `ctrl+v` with nothing in the
  clipboard used to pretend to happen; now the console rail says
  `the clipboard is empty — ctrl+c first`, and the doc isn't dirtied
  (no pointless re-run of your game).
- Selftest: group 33 (clip text joins, base64 vectors, empty-paste
  receipt) — 284 → 292. Smoke: 67 → 68 checks (the copy window
  carries the `]52;c;` bridge bytes).

## v3.0.21 — the clipboard

- **`ctrl+c` / `ctrl+x` / `ctrl+v` — a real clipboard.** Copy takes
  the exact selection (character-wise) or, with none live, the whole
  cursor line (line-wise) — and never dirties the doc. Cut is the
  copy plus the deletion, one honest undo step; a bare cut lifts the
  whole line out and turns the clip line-wise. Paste splices
  character-wise clips at the cursor (tail text rides behind the
  block, the cursor lands at the clip's end) and drops line-wise
  clips in above the cursor line; a live selection is the paste's
  bed, replaced in the same undo step. Cut with a multi-line
  selection? The clip carries every line's shape.
- **Word-wise selection.** `shift+ctrl+←`/`→` extend the selection
  word by word — the anchor is born at the cursor and rides the same
  hops `ctrl+←`/`→` make, across line edges when they must. A plain
  move still drops it.
- **The pair ceremony.** Enter between a bracket pair splits into
  three lines: the naked middle line takes the cursor, `{` bumps it
  a level, and the closer keeps its ground on the base indent.
  Quotes stay honestly out — breaking a string literal is still just
  a split.
- **`ctrl+d` duplicates the whole selection.** With a multi-line
  selection live, every touched line is copied below the range and
  the copy carries both the cursor and the anchor with it. The plain
  single-line duplicate is unchanged.
- **The tab trigger.** Type a shelf name (`tick`, `key`, `fn`, …)
  and reach for `tab` — the word is eaten and the boilerplate lands
  in its place, tail text riding behind the block, the cursor at the
  block's end, one undo step to take it all back. Plain `tab` still
  gives four honest spaces (grouped like typing), a selected block
  indents every touched line (the selection survives), and
  `shift+tab` — a real `ESC[Z` parse — dedents the block or the
  hand's line by up to four spaces.
- **`:screenshot` whispers its default.** With no name typed and no
  shots in `exports/`, the bar tells you what enter WILL write —
  `exports/<scene>-N.png — the default` — before it writes it.
- Selftest: groups 31–32 (clipboard semantics, word select, the
  ceremony, multi-dup, tab triggers, block indent/dedent)
  — 241 → 284. Smoke: 50 → 67 checks, including a live
  clipboard round-trip on the flappy import line — and the smoke's
  own honest-quit fix (LESSON #4: the bar needs play mode; in the
  IDE a `:` types into the doc and the quit never lands).

## v3.0.20 — the selection

- **`shift+arrows` select.** The anchor is born at the cursor on the
  first shift-extension and the selection glows cell by cell as it
  grows — across lines, backward, whatever shape you draw. A plain
  move drops it; undo/redo drop it too; jumps (`:goto`, find-walk,
  template loads, `:open`) never drag a stale selection along.
- **Edits replace the range.** A typed character, backspace,
  forward-delete or enter with a selection live replaces the range —
  VS Code's contract — and the whole replacement is ONE honest undo
  step. A spanning cut joins the lines at the range's edges; an
  anchor equal to the cursor is no selection at all.
- **`ctrl+/` speaks multi-line.** With a selection spanning lines,
  the comment toggle touches EVERY line the selection covers — the
  first talking line decides whether the range gets stripped or
  dressed, blank lines are skipped, and the whole toggle is one
  undo step.
- Selftest: group 30 (extend/replace/span/cut/undo semantics)
  — 229 → 241.

## v3.0.19 — the ruler, the snippets and the edges

- **`:snip <name>` drops boilerplate from a shelf that speaks your
  file's language.** `tick` in game.py is `def on_tick(dt):`, in
  game.js it's `on.tick(() => { … })`, in game.cpp it's
  `g.onTick = [&](float dt) { … }` — every template checked against
  the real sdk/ contracts. The py shelf stocks eleven (fn tick key
  hit start loop ifelse class try imports main), js and cpp speak
  their own seven and five. An exact name wins, a unique prefix
  resolves (`:snip im` → imports), an ambiguous prefix lists, a
  ghost is refused with the full list — and the shelf whispers its
  names as you type. A blank line is the stage (the snippet takes
  it over), otherwise the block slides in after the cursor line,
  cursor resting at its end, one honest undo step.
- **The ruler: honest guides at columns 79 and 99.** Dim dots mark
  the classic margins in the editor pane — but only where the cell
  is blank, so the guide never paints over your code. `:ruler`
  toggles them off and back on.
- **`:stats` tells you what you're holding**: lines, words, chars,
  where you stand, which dialect the file speaks, whether the host
  is live.
- **`ctrl+home` / `ctrl+end` jump the edges** — the very top, the
  very bottom, cursor honest, the document never dirtied.
- **More whispers**: `:screenshot <part>` completes from the shots
  already in exports/, `:w <part>` completes the campaign's scene
  paths, `:snip <part>` completes the shelf.
- Selftest: groups 28–29 (the snippet shelf + the edges + grammar)
  — 206 → 229.

## v3.0.18 — the forward bite and the talking line

- **`ctrl+delete` eats the word ahead** — the exact sibling of
  ctrl+w: it bites precisely what ctrl+right would hop over, the gap
  and the run in one mouthful, punctuation runs included, an honest
  no-op at the line end, one undo step.
- **`ctrl+/` makes the line talk** (or hushes it). The comment prefix
  follows the file's language — `#` for python and shell, `//` for
  js and C-family, `--` for lua — lands after the leading whitespace,
  and strips again with the same keystroke, cursor along for the
  ride. The game hears about it: the live re-run fires like any edit.
- **`:template <name>`** loads a starter directly — `:template flappy`
  instead of cycling ctrl+n. Exact name wins, a unique prefix
  resolves, an ambiguous prefix lists the candidates, a ghost is
  refused with the full list. The ctrl+n gallery still cycles.
- Selftest: group 27 (the bite forward + the talking line + grammar)
  — 191 → 206.

## v3.0.17 — the long line and the partner

- **`ctrl+←` / `ctrl+→` hop word by word.** The same classification the
  ctrl+w bite uses — whitespace is a gap, a run of word characters or
  punctuation is ONE hop — but forward hops land at a run's end and
  backward hops at its start, the classic editor split. Hops cross
  line edges: an empty line is just a wider gap, and the hop never
  touches the document.
- **Long lines slide under the cursor.** Lines wider than the pane no
  longer end at a chopped `…` — the view follows the cursor with a
  small margin on whichever side you came from, an honest `…` marks
  the cut in the gutter, and the line end stays reachable (clamped,
  stable, and a line that fits never slides).
- **The bracket's partner glows.** Stand on a `(`, `[` or `{` (or just
  behind one) and its match lights up across the file — nesting and
  line edges respected, quotes are just characters, and an unclosed
  bracket refuses to fake a match.
- **The escape parser grew up.** CSI sequences are parsed whole and
  unknown ones are swallowed — `ctrl+arrows` used to leak `1;5C` into
  your code as text, mouse reports and DSR answers leaked digits, and
  split reads typed fragments. Nothing leaks now, and SS3 (`ESC O A`)
  arrows are understood too.
- **`ctrl+↑` / `ctrl+↓` nudge the view** without moving the cursor —
  the honest scroll that gets out of the way the moment you move.
- Selftest: groups 25 (word hops) + 26 (bracket match + the slide) —
  157 → 193.

## v3.0.16 — the bite and the leap

- **`ctrl+w` eats the word behind the cursor.** The gap counts as part
  of the bite, punctuation runs go in one mouthful, snake_case names
  stay whole, and an honest no-op at the line start. One undo step,
  like every structural edit.
- **`:goto <line>`** jumps the editor to any line — ctrl+g's sibling
  for lines without a traceback. The studio takes the stage mid-file
  (the jump lands four rows down for context) and the console names
  the line it landed on.
- Selftest: group 24 (the bite) + `:goto` grammar asserts — 146 → 157.

## v3.0.15 — the searchlight: find, pairs, the copy machine

- **`ctrl+f` finds in your file.** The searchlight is case-insensitive
  the way beginners think, aims at the first hit at or after your
  cursor, and `enter` walks you hit by hit with a honest wrap-around.
  Every match glows behind the text — the current one burns amber —
  and the rail counts them live (`2/7 · enter next · esc done`).
  Typing under the searchlight feeds the query, never the buffer, and
  backspace on an empty query closes it.
- **The header knows where you stand**: `Ln 12 · Col 8` rides next to
  the file name, always current.
- **Pairs carry their own closers.** `(`, `[`, `{` and quotes type
  their other half; a closer you already have is skipped over, never
  doubled; backspace between an empty pair removes both halves; an
  apostrophe inside a word (`don't`) never hijacks a pair; nesting
  (`f([x])`) just works.
- **`ctrl+d` duplicates the line** under the cursor — column kept,
  one undo step, the copy takes your place.
- **`:open <file>`** loads any script into the studio from the command
  bar. Your cwd and the `sdk/examples/` gallery whisper their file
  names as you type (matching on the file name, showing the path); a
  ghost file is refused with an honest error, and a running game hands
  the stage over cleanly.
- **Fixed: the command-bar whispers were dead code.** The completion
  matcher looked for a leading `":"` that `cmdBuf` never carries —
  `:scene` name completion never drew a whisper since it shipped. The
  matcher is fixed, and `:open` joins it with file-name matching.
- **Fixed: a pasted command died silently.** Text landing in the same
  read as its enter was dropped before `cmdBuf` ever saw it; the bar
  now absorbs same-frame typing, so paste-style commands execute.
- **Fixed: command frames leaked into the editor.** A `:open` executed
  in the same read as its text let that text then be typed INTO the
  freshly loaded document (and the auto-run saved the corruption back
  to the file — a shipped example came home with the command as its
  first line). A frame the command bar polled is now the bar's alone.
- **Fixed: saves keep their trailing newline.** `ideSave` now writes
  POSIX-honest files ending in `\n`, so loading an example and running
  it no longer rewrites the file with a stripped last byte.
- **Fixed:** forward-delete (`del`) never marked the document dirty —
  a joined line would not re-run the game until the next edit. Now
  `del` and `ctrl+d` both flag the auto-refresh honestly.
- Selftest grew two groups (find-in-file, pairs + duplicate): 33 new
  asserts, 146 total.

## v3.0.14 — the block rides down: auto-indent

- **Enter carries the block.** A new line inherits the previous line's
  indentation; a line ending in `:` (python) or `{` (C-family) bumps
  one level before the cursor lands, and splitting before a closer
  (`else`, `elif`, `except`, `finally`, `case`, `default`, the whole
  `end` family) drops back a level instead of staircasing into the
  margin. Whole-word matching, so `endless` never dedents.
- Typed code keeps flowing at the new indent — write `def on_tick(dt):`,
  press enter, and the body line is already where it belongs.
- Nine more selftest asserts (113 total): opener/closer units,
  trailing-space tolerance, mid-line splits, closer dedents, and the
  proof that auto-indent splits undo like any other edit.

## v3.0.13 — the second chance: an editor that forgives

**ctrl+z has entered the studio**
- **Real undo/redo.** `ctrl+z` rewinds, `ctrl+y` walks it forward
  again — and both restore the document AND the cursor, so the second
  chance lands you exactly where you were standing. Two hundred steps
  deep, snapshots capped honestly, and a fresh edit after an undo cuts
  the redo branch the way every editor you trust does.
- **Undo groups like humans type.** A burst of typing coalesces into
  one step while the hand is quick (the same 0.8s pause timer that
  drives the live auto-run); a pause opens a new step; `enter`,
  forward-delete and template loads are always their own restore
  point. Fifteen new selftest asserts walk the whole story: bursts,
  coalescing, rewind, redo, branch cuts, line splits and joins.
- **The editor heart moved to `edit.hpp`** — one shared truth for the
  IDE and the selftest, and a latent dangling-reference hardening on
  the enter/del paths (the buffer can reallocate mid-gesture; now it
  re-fetches).
- **A new file starts truly empty** — no ghost leading space on line 1.

**The gallery goes multilingual**
- `ctrl+n` now cycles seven templates across every language the studio
  hosts: `blank`, `shooter`, `cards`, `background`, `flappy` (new),
  `bounce.js` and `pong.cpp` — the console names the language of each.
- **`flappy.py`** — gravity, recycled pipe pairs with fresh gaps,
  one-key flying, honest game-over and restart. The wire contract
  probes it on every push (9 entities, scene + frames), and a
  keys/hit/restart playtest rides in the QA kit.

**Polish**
- **`ctrl+p` screenshots your live game from the editor** — and every
  screenshot leaves a receipt in the studio console
  (`engine: saved exports/…png — a real PNG of your frame`).
- The status-rail hint and `--help` now advertise
  `ctrl+z`/`ctrl+y`/`ctrl+p`.
- `.gitignore` covers the template gallery's `untitled-*` files, so
  ctrl+n + auto-run no longer litters `git status`.

## v3.0.12 — the typed word: an IDE that fixes with you

**The editor grows up**
- **Real editor keys**: `pgup`/`pgdn` page through the file,
  `home`/`end` snap to line ends, `del` forward-deletes and joins the
  next line up — the IDE finally feels like an editor, not a typewriter.
- **ctrl+g: the console talks back.** When your game crashes, the
  console's traceback carries the line number — python
  (`File "game.py", line 12`) and node (`game.js:28:1`) both — and the
  status rail turns red with `ctrl+g jumps to line 12`. One keystroke
  from the stack trace to the offending line.
- **`:new` joins the command bar** — the template gallery without
  leaving the keyboard; it even opens the studio from play mode.

**The C++ SDK: compiled games, first-class**
- `sdk/dxn3.hpp` — a header-only C++ SDK: `g.rect(...)`, `g.onTick`,
  `g.onKey`, `g.onHit`, `g.var(...)`, `g.run()`. Entity pointers are
  stable for the life of the game (a `deque`, on purpose — a `vector`
  silently dangled them and segfaulted real games mid-frame; the gate
  now proves it doesn't).
- `sdk/examples/pong.cpp` — a compiled pong with a speed-capped AI,
  paddle-edge steering and set scoring. `dxn3 sdk/examples/pong.cpp`
  compiles it on the spot and hosts it.
- **Gate 6: the wire contract runs on every push.** A fake engine feeds
  every shipped example — python, node and the compiled C++ game — and
  checks the scene and frames come back. Broken examples fail the
  build now, not the user's afternoon.

**The selftest grew to 86 assertion groups** — the new console-readback
group parses python and node tracebacks for line numbers, last frame
wins.

## v3.0.11 — the polish round

- **Discs are genuinely round now**: circles rasterize per dot, so in
  braille mode every coin, moon and enemy is a true curve with a rim
  light — no more stair steps.
- **Ctrl+N cycles starting points** in the IDE: a bouncing-ball blank,
  the shooter, the card game, the background — each loads into the
  editor and goes live, so "start with nothing" never means "start
  alone".

## v3.0.10 — the de-pixel: braille dots

**Four times the pixels, zero new dependencies**
- The world renderer composes **braille cells** (U+2800..) now: every
  terminal cell carries a 2×4 dot block, so the world renders at 2×2 dots
  per half-block pixel — four times the resolution of the chunky old
  face. Platforms, ships, gradients and the starfield all gain real
  edges; the "pixelated terminal game" look is gone.
- `b` toggles between braille dots and half blocks in play — the old
  face is still there if you want it (or if your font can't do braille).
- The IDE viewport, the splash card and the HUD all render through the
  same dot pipeline; text overlays stay crisp text.
- Engine selftest grew to 81 assertion groups (protocol, resolution,
  scene-name resolution, shapes).

## v3.0.09 — the engine: your code, our canvas

**The studio becomes an engine IDE**
- Boot is the **IDE** now: an editor beside a live viewport and a console
  rail. You start with nothing — the starter is a working shooter in 30
  lines — you edit, and the viewport refreshes while you type. `Ctrl+R`
  runs, `Ctrl+S` saves, `esc` plays your game fullscreen, `esc` again
  returns to the code.
- **Your game is your program, in your language.** The engine hosts it as
  a child process speaking line-JSON on stdio (hello → scene → ticks →
  frames, one page in `sdk/PROTOCOL.md`): Python and JavaScript SDKs ship
  in `sdk/`, `.cpp` games are compiled and hosted on the spot, and
  `--host-cmd 'ruby mygame.rb'` hosts literally anything that reads
  stdin and writes stdout. The engine owns rendering, input, collision;
  your code owns the rules — shooters, card games, whatever you write.
- **The ScriptHost** (`native/src/host.hpp`): fork/exec pipes, a
  fixed-timestep tick with held keys + typed chars + overlap hits, frame
  patches applied by name (spawn/move/recolor/despawn), game vars mirrored
  to the HUD, camera taken live. Unparsable child output becomes console
  lines and SIGPIPE is ignored — a dead game is an honest exit line in
  the console, never a dead studio.
- The SDKs are zero-ceremony: define `on_tick(dt)`, `on_key(k)`,
  `on_hit(a, b)` and call `run()`. print() lands in the console rail.
  A fresh `dt` is injected into your frame every tick; hits fire on
  enter, not every frame; re-drawing a name redraws in place.
- Examples in `sdk/examples/`: `background.py` (the hello world — three
  lines and the viewport answers), `shooter.py` (move, shoot, score),
  `bounce.js` (breakout with a steering paddle — proof the JS SDK bites),
  `cards.py` (balatro-lite hold-and-score — no physics, pure state,
  proof the engine is not just platformers).

**The engine underneath**
- Entities gained a real `shape` (rect / circle / tri / text) parsed and
  round-tripped through the JSON — coins are true discs now, drawn with a
  rim light, and any entity can be any shape.
- `:scene level-3` resolves by name — exact or unique prefix; an
  ambiguous prefix lists the matches instead of guessing, and the
  command bar whispers the matches while you type.
- The selftest grew to **81 assertion groups**, including scene-name
  resolution and **the whole engine end to end: a real Python SDK child
  hosted through the real protocol** — scene across the pipe, prints in
  the console, honest exit.
- The launcher boots the engine IDE from the install root (so `sdk/`
  resolves for every hosted game); the five-scene campaign is the demo.
  `--host-cmd`, `--list-scenes` and the installer carry the new story;
  the version constant tells the truth again (3.0.09 everywhere).

## v3.0.08 — the campaign: somewhere to go

**The campaign grows: five scenes**
- Two new levels chain the world together: **playground → level-1 (the gap)
  → level-2 (the movers) → level-3 (the climb) → level-4 (the gauntlet) →
  back home.**
- `level-3 — the climb`: the studio goes vertical. Two lifts, a fanged
  approach, a springboard shortcut for the greedy, coins on the way up and
  a gradient summit waiting at the top.
- `level-4 — the gauntlet`: the exam. Nine fangs on the pit floor, three
  ferries on staggered heights, a saw-guarded island rest stop, a spinning
  gate before the last door — the hardest jump timing in the campaign.
- Both levels ship with real map-framed renders in the README, generated
  by the binary itself (`--screenshot`), same as the rest.

**The repo fires: quality gates in public**
- GitHub Actions CI now runs the full gauntlet on every push and pull
  request: the zero-warning C++23 build under **g++ and clang++** (a
  compiler matrix), the engine selftest, one real headless frame for
  every scene, the zero-electron tripwire and VERSION ↔ CHANGELOG
  consistency.
- A second CI job probes the one-liner installer end to end — clone,
  build, selftest, launcher — straight from `origin/master`, so the curl
  line on the README is exercised by machines, not just by hope.
- README carries the gates badge; the campaign section, screenshot
  gallery and history tell the five-scene story.

## v3.0.07 — the mark: a face for the studio

**The brand**
- The studio has its emblem: the STUDIO 2 circuit spiral (preserved on the
  `ds2-archive` branch) with a monolithic beveled **3** carved into it —
  Unreal-Engine energy, purple-on-black, one mark everywhere. The brand
  suite lives in `assets/` with the SVG sources: emblem, README banner and
  the repo social card.
- The binary carries the mark too: `native/src/logo32.hpp` renders it as a
  32×32 truecolor bitmap and the studio opens on a **title card** — the
  emblem, the wordmark, the version, one key to play.

**The UI**
- Title card on launch (any key plays, `q` quits) — the studio greets you
  as a product, not a process, carrying the mark as a 32×32 truecolor
  bitmap straight from the binary.
- The HUD counts it all: `COINS x/y · SCORE · TIME` on the left, the scene
  name on the right — you always know where you are in the campaign.
- `dxn3 --list-scenes` prints every installed scene with its name and
  entity count — discoverability without reading files, and `--help`
  covers the whole CLI.
- The vim-style **command bar** ships: `:scene :zoom :fit :reset :w :wq :q
  :screenshot :magnet :gravity :help`, honest errors with usage, the game
  paused while it's open — and it whispers: a live usage hint follows your
  typing, dim and out of the way.
- **PNG screenshots** ship, zero dependencies: `p` in play saves
  `exports/<scene>-<n>.png`, and `dxn3-native --screenshot out.png` renders
  any scene headless (the README's screenshots are made this way).
- **Scene saving** ships with a git-style safety net: `:w` writes the scene
  and keeps the previous bytes as `<file>.bak` before the new ones land.
- The deterministic parallax **starfield** (`fx.hpp`) — every scene seeds
  its own sky from its name, so the same scene draws the same stars in
  every session and every screenshot.
- **`--list-scenes`**: `dxn3 --list-scenes` prints every `.dxn1.json` it
  can find with its scene name and entity count — unreadable files are
  reported, never swallowed.
- The live view reached **poster parity**: the terminal now draws the same
  sky gradient, coin halos and edge vignette as the PNG raster, and
  INSPECT / FILE VIEW wear the same rail headers and zebra rows.
- **Poster framing**: `--screenshot` fits the whole scene like a map —
  world-centered, edges and all — which is how the README shots are made.

## v3.0.06 — the Electron farewell: fully C++23

**One binary to rule them all**
- Deleted, for real and forever: `electron/`, the JS renderer, the Python
  engine and its QA stand-in, `package.json`, the Node scripts, the pytest
  lane and the stale UI screenshots. Nothing in the tree mentions Electron
  outside this changelog's history.
- `scripts/gates.sh` rebuilt native-only: zero-warning C++23 build, the
  engine selftest, **every scene must render one real headless frame**,
  zero electron-era files tracked, VERSION ↔ CHANGELOG consistency. The
  gates need nothing but a C++23 compiler now — the QA lane eats its own
  dog food.
- `scripts/install.sh` rebuilt: checks git + g++/clang++ (probing that
  C++23 actually compiles), clones, builds, runs the selftest, writes the
  `dxn3` launcher. The curl one-liner stays exactly where it was.
- New campaign scene `scenes/level-1.dxn1.json` — **the gap**: a mover
  bridge over a spiked pit, an elevator to a sky ledge, a five-coin arc and
  a goal that chains into level-2. The campaign is now
  playground → level-1 → level-2 → home.
- README + ARCHITECTURE rewritten around the native core. The studio is
  one binary; the past lives in git history.

# Changelog — DXN1 STUDIO 3

Giant hourly updates. Every version is worth installing.

## v3.0.05 — the native core: Spark in C++23

**The engine now speaks C++ too**
- `native/` — a complete, dependency-free **C++23 port of the Spark
  engine**: same scene JSON, same AABB physics, movers with rider
  carry, coin magnetism, hazards, goal→next-scene transitions, camera
  follow + zoom + decay shake. `std::expected` scene loading, a
  hand-rolled JSON parser (with `\uXXXX`→UTF-8 so signs render their
  arrows), fixed-timestep loop mirroring the JS runtime 1:1.
- **Truecolor terminal renderer** — half-block pixels (two world
  pixels per cell, 24-bit color), gradient fills, striped goal flags,
  triangle spikes, HUD with score/time, help rails. The studio plays
  beautifully in any modern terminal.
- **The studio shell** — PLAY and INSPECT modes (Tab pauses and prints
  the entity table: name, tag, position, size, color, aliveness),
  run/jump, zoom in/out/fit, reset, honest quit summary. Runs from any
  working directory; `--scene` picks the level.
- **Selftest: 29 engine assertions** — clamps, magnetism (pull + off),
  pickups, hazard respawn + shake, transition locking, mover
  ping-pong + rider carry, camera follow, eternal ball. Wired into the
  quality gates as gate 7 — the repo does not ship unless C++23 builds
  clean (`-Wall -Wextra -Wpedantic`) and stays green.

**Spark (browser) gains the same powers**
- **Coin magnetism** — `"magnet": 110` per scene; coins drift toward
  the player, pull growing as they close in. Both demo scenes ship
  magnetized.
- **Camera shake** — time-decayed, cosmetic-only; hazards shake on
  respawn. `game.shake(power, seconds)` from scene code.
- **Word autocomplete** — Ctrl+Space pops frequency-ranked completions
  from the buffer; arrows/click to accept, Esc dismisses, caret-true
  positioning.
- **Breadcrumbs** — the path of the open file sits above the editor,
  clickable per segment.
- **Search grouped by file** — project grep results now file their
  matches under per-file headers with counts.
- **"Play level 2" hero card** — the welcome screen now jumps straight
  into the movers-and-magnet level.

## v3.0.04 — the git suite completes; the editor sees the line you're on

**Source control — the full loop**
- Diff viewer: click ± on any changed file to see exactly what
  changed vs HEAD — unified hunks, +/− coloring, line numbers, add and
  delete counts. Untracked files show as all-additions; no-HEAD repos
  handled honestly.
- Branch switcher: click the branch chip to switch or create branches
  (duplicate and ghost names refused, hostile names rejected). Demo
  mode simulates per-branch snapshots and histories, checkout and all.
- Rail badge: the source control icon counts your live changes.

**Editor**
- Current-line highlight follows the caret (and scrolls with it).
- Gutter now scroll-syncs with the editor — line numbers finally
  follow long files (a latent bug since v3.0.01).
- Editor context menu: undo, redo, cut, copy, paste, select all,
  find, replace, go to line — right where you are.

**Spark engine**
- Entities rotate: `rot` (degrees, visual-only — physics stays an
  honest AABB) and `spin` (degrees/sec) — level-2 gained a spinning
  saw hazard. Inspector rows for rot / color2 / gradient fill.
- 2-line-context LCS diffs power the demo diff viewer.

**Under the hood**
- Engine cmd_git_diff / git_branches / git_checkout with honest errors
  (path required · no such branch · branch already exists · invalid
  branch name). Branch parse fixed for "No commits yet on master".
- Tests 20/20 · gates 6/6 · browser QA 46/46.

# Changelog — DXN1 STUDIO 3

Giant hourly updates. Every version is worth installing.

## v3.0.03 — the scene comes alive, and source control is real

**Spark engine**
- Moving platforms: `path: {toX, toY, speed}` — entities shuttle
  ping-pong between two points and CARRY whatever stands on them.
  Motion rails drawn as dashed cyan lines in the editor.
- Scene transitions: tag an entity `goal`, point `next` at another
  scene — touching it loads the next level and the run keeps playing.
  Two demo levels ship and loop: playground → level-2 → playground.
- Camera zoom (wheel, toward cursor) + pan (middle-drag / Space+drag)
  + zoom-fit button — the whole render pipeline is zoom-aware, grid,
  culling, selection, camera follow.
- Parallax layers are scene data: `parallax: [{speed, color, size,
  count}]`. Timer HUD joins the score.

**Scene editor**
- Canvas right-click toolbox: add any of 8 entity kinds exactly at the
  cursor, duplicate, delete, bring to front, send to back.
- Z-order controls in the inspector (front / up / down / back) and in
  the entity list right-click.
- New presets: mover (pre-wired path) and goal (the finish flag).
- Inspector: motion rows (to x / to y / speed), make-it-move and
  remove-motion buttons.

**Editor**
- Replace in file (Ctrl+H): replace current hit or all, live counts.
- Go to line (Ctrl+G).
- Bracket & quote auto-close, selection wrap, type-over closers,
  empty-pair backspace.
- Editor context menu: undo, redo, cut, copy, paste, select all,
  find, replace, go to line.

**Source control — wired honestly**
- The git panel is no longer dead UI: branch + changed files with
  M/A/D badges (click to open), commit box, history list.
- The Python engine speaks real git (status/log/commit over
  subprocess, honest errors for non-repos); demo mode carries a
  simulated history with the same protocol.
- Statusbar shows the branch. Terminal gained `git` and `zoom` verbs.

**Installer**
- One-line curl install: `curl -fsSL .../scripts/install.sh | bash`
  — checks tools, clones, offers desktop or `--demo` browser mode
  (Termux-friendly). README rewritten around it.

**Quality**
- Engine tests +6 (git status/commit/log/non-repo/message guards).
- Renderer selftest grew to 9 assertion groups (goal, next-chaining,
  movers, parallax, zoom helpers).
- Gates 6/6 green before tag.

# Changelog — DXN1 STUDIO 3

Giant hourly updates. Every version is worth installing.

## v3.0.03 — the studio learns to move (and to remember)

**Spark engine**
- Moving platforms: give any entity a motion rail (`path: {toX, toY,
  speed}`) and it shuttles between the two points, ping-pong, CARRYING
  whatever stands on it — elevators, ferries, drifting ledges.
- Scene transitions: a `goal` entity + a scene-level `next` path sends
  the player into the next scene without leaving play mode. The demo
  ships two chained scenes (playground → level-2 → playground).
- Timer HUD next to the score; parallax layers are now scene config
  (`parallax: [{speed, color, size, count}]`).
- The editor draws each mover's dashed motion rail on the canvas.

**Scene editor**
- Camera zoom (wheel, toward the cursor) + pan (middle-drag or
  space-drag) + ⊕ fit. Grid, culling and selection all respect zoom.
- Canvas right-click: add any entity exactly where you clicked,
  duplicate / delete, and z-order (bring to front / send to back /
  forward / backward). Z-order buttons also live in the inspector.
- New presets: ⚑ goal and ⇄ mover.
- Inspector: add motion / edit rail target + speed / remove motion.

**Editor**
- Replace-in-file: findbar grew Replace + Replace All (Ctrl+H).
- Go to line: Ctrl+G, clamped, statusbar-confirmed.
- Bracket & quote auto-close with selection wrap and skip-over.
- Editor context menu: undo / redo / cut / copy / paste / select all /
  go to line / find.

**Source control — wired for real**
- The git panel was dead UI; now it speaks to the engine:
  branch + ahead, per-file status badges (A/M/D/U), click a file to
  open it, commit box (adds all, honest errors), and a log with hash +
  subject + age. The Python engine shells out to real git; the demo
  filesystem keeps an honest simulated history. Statusbar shows the
  branch.

**Install from one line**
- `curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash`
  installs STUDIO 3 and a `dxn3` launcher (Electron when available,
  honest web preview otherwise).

**Also**
- scenes/level-2.dxn1.json — a mover-and-goal level built for the demo.
- Terminal verbs: `git`, `zoom in|out|fit`. Palette: 22 commands.
- Engine: git_status / git_log / git_commit with honest errors; 18
  engine tests; selftest guards the new Spark schema (8 groups).

## v3.0.02 — the editor & the scene editor get muscles

**Scene editor (Spark)**
- Entity palette: add block / platform / coin / spike / bouncer / text
  with one click — spawned snapped to the grid at the camera center.
- Duplicate (Ctrl+D / ⧉ / right-click) and delete (Del / ✕ / right-click)
  entities, with auto-unique names.
- Edit grid overlay (⌗) with 8px snapping while dragging — Alt drags free.
- Live repaint while dragging or editing the inspector — the canvas is
  never stale again (this was a real editing bug: changes only showed
  after pressing play).
- Spark engine: triangle shape, text entities (with size), hazard tag
  (spikes respawn the player with a burst), proper spawn-point handling,
  identity-based selection rendering (duplicates render correctly).

**Editor**
- Find in file: Ctrl+F, live match count, Enter / Shift+Enter navigation
  with wrap-around, Esc to close.
- Minimap, DS3 style: one bar per line, indent-aware, viewport lens,
  click/drag to jump, toggleable.
- Tab drag-to-reorder.
- Sidebar resize via drag handle (persisted).
- Syntax highlighting for HTML and CSS.
- Keybindings reference table in Settings.

**Terminal**: new verbs `grid`, `ent`, `find <text>`, `mm`.
**Demo scene**: spikes + a signpost label show off the new engine powers.

## v3.0.01 — the rebirth

Fresh-history rebuild of the whole repo:
- Electron face + Python brain (stdio JSON bridge, atomic writes,
  path-escape guards) + DemoFS so the UI never dies in a browser.
- Workbench: welcome hero, editor (gutter + highlighting + transparent
  textarea), game view (canvas + scene dock: entity list + inspector),
  terminal dock, statusbar, command palette (13 commands), toasts,
  context menus.
- SPARK 2D engine: entities, AABB physics (axis-separated), platformer
  controller, bounce, coin pickup + score + particles, camera follow,
  parallax stars, HUD. Scenes are plain JSON.
- Playable playground scene; light/dark themes; five accents.
