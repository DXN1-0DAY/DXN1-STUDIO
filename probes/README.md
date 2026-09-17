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
