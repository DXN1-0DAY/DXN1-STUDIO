# FLAPPY in the DXN1 STUDIO — run:  dxn3 sdk/examples/flappy.py
# the worn pipes: pipes fade in from the horizon (alpha wears with
# distance), a death BLEACHES the bird, a clean pass makes it GLOW.
from dxn3 import *
import random

random.seed(7)                       # honest demo pipes — same sky every run
background("#0a0e1e")

bird = circle("bird", 16, H // 2, 6, 6, "#facc15"); bird.tag = "bird"
hud  = label("hud", 2, 2, "SCORE 0")
tip  = label("tip", 2, 4, "space to flap")
score, vy, dead = 0, 0, False
GAP, SPEED, LIFT = 12, 0.4, 2.6      # the whole physics story, in pixels

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
    tip.text = "space to fly again"
    win(f"game over — score {score}")
    print("game over — score", score)

def on_key(k):
    global vy, dead, score
    if k != "space": return
    if dead:
        dead, score, vy = False, 0, 0
        bird.x, bird.y = 16, H // 2
        bird.flash, bird.glow = 0, 0          # a fresh bird wears no scars
        for i, p in enumerate(pairs):
            gap_at(p, W + 8 + i * 22)
        hud.text, tip.text = "SCORE 0", "space to flap"
        print("new flight — good luck")
    else:
        vy = -LIFT

def on_tick(dt2):
    global vy, score
    if dead: return                       # frozen until space restarts
    vy += 0.16                            # gravity, one honest pixel per tick
    bird.y = bird.y + vy
    if bird.y < 0 or bird.y > H - 6:
        die()
        return
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
    if bird.glow:
        bird.glow = round(bird.glow * 0.82, 3)   # the glow decays each tick
        if bird.glow < 0.05:
            bird.glow = 0

def on_hit(a, b):
    if not dead and "bird" in (a.tag, b.tag) and "pipe" in (a.tag, b.tag):
        die()

run()
