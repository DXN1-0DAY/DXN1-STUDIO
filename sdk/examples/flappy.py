# FLAPPY in the DXN1 STUDIO — run:  dxn3 sdk/examples/flappy.py
# the worn pipes: pipes fade in from the horizon (alpha wears with
# distance), a death BLEACHES the bird and the bleach WEARS OFF at
# 3/s while the world waits — the bird settles into a half-light
# ghost, never a forever-statue (the wire game owns its decay),
# a clean pass makes it GLOW on an honest 6/s staircase.
# v3.1.66 — THE NIGHT OWNS THIS SKY TOO: the score turns it — night
# falls at 3, dawn at 8, and every five after (the sky's own rhythm,
# derived from the score, no second stream). The dark fades in over
# two honest seconds (the dino law), the moon rises and SHINES when
# the fade completes (glow 4), and the pipes DRESS FOR IT — pale by
# night with a faint halo of their own (the cacti law), so the gap
# stays readable in the dark. The ghost's alpha 0.32 was wayfinding
# by honesty; the halo is wayfinding by light.
from dxn3 import *
import random

random.seed(7)                       # honest demo pipes — same sky every run
background("#0a0e1e")

# the night's own furniture — created FIRST so the world renders over it
sky = rect("sky", 0, 0, W, H, "#020617")
sky.alpha = 0                        # the dark, waiting for its hours
moon = circle("moon", W - 12, 4, 5, 5, "#e2e8f0")
moon.alpha = 0.25                    # the moon haunts the day sky faintly
moon.glow = 0
night = False                        # the score turns the sky: night at 3,
nightT = 0.0                         # dawn at 8, and every five after;
                                     # nightT fades over two honest seconds

bird = circle("bird", 16, H // 2, 6, 6, "#facc15"); bird.tag = "bird"
hud  = label("hud", 2, 2, "SCORE 0")
tip  = label("tip", 2, 4, "space to flap")
score, vy, dead = 0, 0, False
GAP, SPEED, LIFT = 12, 0.4, 1.1      # the whole physics story, in pixels
# LIFT was 2.6 — a hop 21px tall in a 6px window: NO arc could stay in
# the gap for the 30 ticks a pipe takes to cross (apex plateau is 12
# ticks for ANY lift — the old flappy could never score, the pass-glow
# was dead code). LIFT 1.1 bounces a 3.8px arc that fits the window:
# rhythm taps hold the line. REAL playability bug, found by a probe
# that finally PLAYS (the dino desert lesson, learned again).

pairs = []                           # three pipe pairs cross the sky forever

def gap_at(p, x):                    # one pipe pair, a fresh gap, placed at x
    top_h = random.randint(4, max(5, H - GAP - 8))
    p["top"].x, p["top"].h = x, top_h
    p["bot"].x, p["bot"].y = x, top_h + GAP
    p["bot"].h = H - top_h - GAP
    p["passed"] = False

def wear(x):                         # distance wears the pipes: far = ghost
    return round(0.35 + 0.65 * max(0.0, min(1.0, (150 - x) / 140)), 3)

for i in range(3):
    p = {"top": rect(f"ptop{i}", 0, 0, 6, 8, "#22c55e"),
         "bot": rect(f"pbot{i}", 0, 0, 6, 8, "#16a34a"),
         "passed": False}
    p["top"].tag = p["bot"].tag = "pipe"
    gap_at(p, W + 8 + i * 22)
    pairs.append(p)

def die():
    global dead
    dead = True
    bird.flash = 1.0                     # the crash bleaches the bird
    bird.glow = 0                        # death puts the light out — a
                                         # glow frozen mid-pulse would
                                         # haunt the ghost forever
    tip.text = "space to fly again"
    win(f"game over — score {score}")
    print("game over — score", score)

def dress(night_now):                # the pipes dress for the dark (the
    top_c = "#4ade80" if night_now else "#22c55e"    # cacti law: pale by
    bot_c = "#34d399" if night_now else "#16a34a"    # night, faint halo)
    for p in pairs:
        p["top"].color = top_c
        p["bot"].color = bot_c
        p["top"].glow = 1 if night_now else 0
        p["bot"].glow = 1 if night_now else 0

def on_key(k):
    global vy, dead, score, night, nightT
    if k != "space": return
    if dead:
        dead, score, vy = False, 0, 0
        bird.x, bird.y = 16, H // 2
        bird.flash, bird.glow = 0, 0          # a fresh bird wears no scars
        bird.alpha = 1                        # the ghost flies again
        for i, p in enumerate(pairs):
            gap_at(p, W + 8 + i * 22)
        hud.text, tip.text = "SCORE 0", "space to flap"
        night, nightT = False, 0.0            # a fresh flight is a fresh day
        sky.alpha = 0
        moon.alpha, moon.glow = 0.25, 0
        dress(False)
        print("new flight — good luck")
    else:
        vy = -LIFT

def on_tick(dt2):
    global vy, score, night, nightT
    if dead:
        # the honest staircase (PROTOCOL.md, the who-owns-the-tick
        # law): the studio keeps the last light a wire game sent, so
        # a bleach that is never decayed is a bleach FOREVER — the
        # crash flash wears at 3/s while the world waits, and the
        # bird's alpha wears with it down to a half-light ghost.
        if bird.flash > 0:
            bird.flash = round(max(0.0, bird.flash - 3 * dt2), 3)
            bird.alpha = round(0.5 + 0.5 * bird.flash, 3)
        return                            # frozen until space restarts
    vy += 0.16                            # gravity, one honest pixel per tick
    bird.y = bird.y + vy
    if bird.y < 0 or bird.y > H - 6:
        die()
        return
    if bird.glow:
        # the glow wears at 6/s — a TIME-based staircase (the old
        # 0.82-per-tick shrink finished in ~0.3 s at 60 fps, a pulse
        # no eye could catch). 8 -> 0 now takes a visible 1.3 s.
        # The decay runs BEFORE the pass check (the birth-tick law):
        # a fresh pass's 8.0 shows whole, and wears from the next tick.
        bird.glow = round(max(0.0, bird.glow - 6 * dt2), 3)
    for p in pairs:
        p["top"].x -= SPEED
        p["bot"].x -= SPEED
        a = wear(p["top"].x)              # the horizon wears every pipe
        p["top"].alpha = a
        p["bot"].alpha = a
        if not p["passed"] and p["top"].x + 6 < bird.x:
            p["passed"] = True            # a clean pass through the gap
            score += 1
            bird.glow = 8                 # the pass makes the bird GLOW
            hud.text = "SCORE " + str(score)
        if p["top"].x < -6:               # gone off the left — recycle it
            gap_at(p, W + 4)
    # THE SKY'S OWN RHYTHM: night falls at 3, dawn at 8, and every five
    # after — derived from the score alone (one law, no second stream).
    # The dark fades over two honest seconds; the moon rises with it
    # and SHINES only when the fade completes. The pipes dressed on
    # the flip; the sky and the moon ride the fade.
    now_night = ((score + 2) // 5) % 2 == 1
    if now_night != night:
        night = now_night
        say(("night falls at %d" % score) if night else ("dawn at %d" % score))
        dress(night)
    target = 1.0 if night else 0.0
    if nightT != target:
        step = 0.5 * dt2 if night else -0.5 * dt2
        nightT = round(max(0.0, min(1.0, nightT + step)), 3)
        sky.alpha = round(0.45 * nightT, 3)
        moon.alpha = round(0.25 + 0.75 * nightT, 3)
        moon.glow = 4 if nightT >= 1 else 0

def on_hit(a, b):
    if not dead and "bird" in (a.tag, b.tag) and "pipe" in (a.tag, b.tag):
        die()

run()
