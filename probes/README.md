# the probes

The law pins live IN the repo now, and `scripts/gates.sh` (gate 8)
runs every `probes/*_probe.py` on the real wire.

Why: a probe the gates never run ages into a liar. Four drift
catches on record — pins that were green when written and RED on a
clean tree months (or rounds) later, because nothing re-walked them:

1. ast_wear_probe pinned the old hold-then-cut flame law after the
   code had worn the flame from birth (v3.1.86).
2. the lunar gauge's first-cut boundary bug was caught by its own
   probe before shipping (v3.1.87) — proof the pins work when they
   actually run.
3. tetris_probe's scene census still read 8 entities from the
   v3.1.48 era — red on the clean v3.1.88 tree (v3.1.89).
4. tetris_combo_probe's "dry locks speak nothing" had no answer for
   the dregs' air-voice the rails' law added (v3.1.89).

The rule: **a law isn't shipped until its pin is in `probes/` and
gate 8 walks it.** One family per round — tetris first (the
driftiest), then the asteroids, lunar, cards, bounce and shooter
families come home.

Every probe is stdlib-only python, spawns its game over the wire,
and exits non-zero on any red pin. `REPO` resolves relative to this
directory — the probes run from any checkout.

## the harness laws — how a probe stays honest

Five laws the fleet paid for, each with its receipt:

1. **Wait for the ANSWER, not for silence.** (v3.1.96, the door's
   diet) — the auto-hosted game's render flood never lets a pty go
   quiet, and the splash quiesces before the editor finishes
   booting. Poll in slices until the expected receipt appears in
   the buffer, capped. The machine decides when it's done.
2. **A drive that cannot prove its own timing will betray the
   pins.** (v3.1.94/95, the chase; re-pinned v3.1.99) — one line
   per tick lets chatter steal a frame and the plan steers on stale
   state. Pump thread, read-until-FRAME, a metronome dt — and the
   probe must pin its own metronome: `frames == ticks sent`. The
   layout-lucky `frames > 40` was a horoscope (a lucky food draw
   feeds three meals in 27 ticks and the magic number convicted an
   honest early finish).
3. **A pin that depends on the draw is a horoscope.** (v3.1.97,
   v3.1.100 — the harvest) — unseeded randomness is honest, so the
   pins must hold under EVERY draw. Three named specimens: the
   radar's saturated ties (re-pinned to the monotone direction the
   machine guarantees: the CLOSEST rock always wears the brightest
   alpha); the bleach's death-frozen witness (witness the
   STAIRCASE — 1.0 -> 0.4 -> dark — across every open meal, not
   one meal's clock); the saucer's coin-flip corridor (a chase
   from the near side can never catch a corridor that recedes at
   1.6 px/tick from a 1 px/tick walk — pre-position the hunter
   where BOTH crossing directions pass through). The honest
   repairs: re-pin to the direction the machine guarantees, witness
   the process instead of one arrival, or pre-position so the
   ritual holds under every draw — never to a bigger magic number.
4. **Capture, CHECK THE EXIT, then tag.** (v3.1.100, the process
   law) — a pipe to `tail` swallows both the FAIL lines and the
   exit status, and an `&&` chain never notices; a tag rode a red
   that way once. Capture the full log, CHECK THE EXIT, then tag.
   Two companions from the same hunt: never exec a binary a
   concurrent `make` is relinking (the ENOENT horoscope — 25/25
   "reds" that were path ghosts), and beware `cd X && Y &` — the
   `&` backgrounds the whole chain, the foreground shell never
   changes directory, and every path after it is a lie.
5. **The preserved log is the confession.** — a flake caught
   without its log teaches nothing. The hunt keeps every red's
   full output before the next round overwrites it; the gates'
   `tail -6` window has cut off the deciding line more than once.
   A failure that cannot say why will happen again.
6. **select() on the fd and readline() on a buffer are a
   deadlock.** (v3.1.103, ast_lives) — the respawn chatter and the
   payment frame shared one read chunk; the frame sat in Python's
   own buffer while select waited for fd data that would never come
   until the child saw the next tick it never would. Both sides
   waited; the pin died of thirst, ~one run in five under churn.
   The fleet's shared harness (`probes/_harness.py`) reads RAW and
   splits lines itself — everything the child said is visible to
   the splitter immediately. Sixteen probes carried the latent
   pattern; they migrate family by family.

## the drift ledger — every outsider came home

Caught red (or flaky) on the clean v3.1.90/91 trees during the
homecoming sweep; each kept its story as it was rescued, rebuilt,
or retired:

- `ast_wear_probe` — FIXED at the door: its `closest == brightest`
  pin flaked on the corner rocks' EQUIDISTANT PAIRS (min/max break
  a float tie on opposite sides); the pin now reads the law's
  honest content — the brightest rock stands at the closest band,
  ties allowed.
- `invaders_darkpays_probe` — FLAKY (~50%): a dark summon
  occasionally pays the BASE purse; the ritual cannot yet PROVE
  darkness at the kill frame. Re-pin it with a darkness-proof
  before it walks.
- RESCUED in v3.1.92 and walking inside the walls:
  `shooter_light_probe` (census 3 -> 15, the night sky included),
  `flappy_wear_probe` (census 9 -> 11), `invaders_probe`
  (census 51 -> 62), and `snake_light_probe` — the deep one: its
  milestone pin sampled ONE frame (often the flash's birth, 1.0)
  and demanded it already decayed; the wire then taught the real
  law — the tail's bleach is a HEARTBEAT, re-bloomed by every
  milestone meal, each bloom wearing 1.0 -> 0.4 -> 0.0 — and its
  greedy drive may self-bite before the wall phase, so the probe
  now falls again (space revives; three lives).
- RESCUED in v3.1.93 and walking inside the walls:
  `cards_breathe_probe` (rebuilt on the replicated stream — the
  R22 version spawned on relative paths, prisoner of its birth
  directory, and its card identities predated the deck law; the
  stream taught the truth: the first hand is ALL RED and the first
  black card leads hand two) and `shooter_bolt_probe` (the bolt
  ledger's one true home: bolts destroyed off the top, the count
  returns to 15, the night stays put — absolute birth-checkout
  paths and the stale census 3 fixed at the door).
- RETIRED in v3.1.93, their laws living on in younger pins:
  `cards_probe` (watched the pre-deck-law `msg` entity — gone from
  the scene; the exact stream arithmetic is cards_deck's law now),
  `cards_glow_probe` (identity pins predate the stream; the glow
  hand and the seat lift are pinned by the rescued breathe), and
  `bounce_light_probe` (superseded whole by the lantern probe,
  which pins the flare, the floor, and both plaques besides).
- RESCUED in v3.1.94 and walking inside the walls:
  `chase_probe` — the load-flake finally named and killed: its drive
  read ONE line per tick, so every meal's chatter stole the next
  frame and the plan steered on stale state (green on an idle
  machine, red under full-gates load, wall-biting at score 0). The
  rebuild rides the metronome: a pump thread drains stdout, every
  tick reads until the FRAME, the drive is the serpentine (greedy
  hunters orbit the meal forever — the trace proved a perfect
  clockwise circle), and the restart path is exercised ON PURPOSE:
  stop steering, the wall speaks, exactly one space revives. Two
  new wire laws minted in sdk/PROTOCOL.md (#2's per-character fine
  print, #8's one-tick command flight). 8 pins, 5x green under
  concurrent load.
- DIETED in v3.1.96 (it was walking inside the walls all along —
  its exile was the 35 seconds): `ide_door_probe`, from 35 s of
  fixed sleeps to answer-driven waits (13/13 in 11.7 s, three
  runs green): the
  auto-hosted game floods the pty continuously, so the first
  diet's quiescence never fired (every cap burned) and a
  half-booted IDE ate the first command; the diet that works
  waits for THE ANSWER — poll in slices until the expected
  receipt appears in the post-enter buffer, capped.
- HOME in v3.1.98 (and hardened in v3.1.100):
  `invaders_darkpays_probe` — the outsider list is EMPTY. The ~50%
  flake was never the engine: the night purse is pay*2 over
  [50,100,150,300], so the doubled set overlaps the day set at 100
  and 300 — the old "never an odd purse value" pin was
  unsatisfiable on two of four tiers. Re-pinned draw-proof: the
  night purse HALVES into an honest day purse; the moon ledger
  carries the kill frame's darkness. v3.1.100 named the second
  coin: the crossing's direction is `Math.random() < 0.5` and the
  near-side chase can never catch the corridor — the summon now
  drifts the hunter to the sky's center so both directions pass
  through, six attempts, forensics in the pin detail.
- The fleet stands at 52 walking pins as of v3.1.100. Nothing is
  outside the walls; the ledger keeps the rescue stories.
