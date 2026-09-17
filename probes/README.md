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

## the drift ledger — still outside the walls

Caught red (or flaky) on the clean v3.1.90/91 trees during the
homecoming sweep; they stay external until re-pinned:

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
- `chase_probe` — EVICTED in v3.1.92: green standalone, red under
  full-gates load (the driven snake wall-bites at score 0 before
  the chase develops — load-sensitive drive). Outside until its
  drive is load-proof.
- STILL OUTSIDE (re-pin or retire):
  `invaders_darkpays_probe` — FLAKY (~50%): a dark summon
  occasionally pays the BASE purse; the ritual cannot yet PROVE
  darkness at the kill frame. Re-pin it with a darkness-proof
  before it walks.
- `ide_door_probe` — green but 35 s; bring it home when it dieted
  (gate 8 must stay quick).
