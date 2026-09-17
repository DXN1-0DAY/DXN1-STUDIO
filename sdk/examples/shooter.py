# a SHOOTER in the DXN1 STUDIO — run:  dxn3 sdk/examples/shooter.py
# v3.1.47 wears the engine's light: the muzzle GLOWS when you fire
# (and fades honestly in tick), bolts carry their own small halo, and
# every hit respawns the next threat as a GHOST — alpha 0.15 rising to
# full over DRIFT seconds, the radar-field's law, so the void always
# announces what it is about to throw at you. Even the first threat
# drifts in.
# v3.1.73 adds a SECOND THREAT CLASS — the drifting twin: smaller,
# faster, riding a sine bob, worth 25 to the bulk's 10. Both threats
# respawn from their OWN NAMED STREAMS (the seed chapter's
# one-stream-per-concern: "the threat's return", "the twin's return")
# so the same run deals the same respawns forever, and a replay probe
# can predict every position to the packet.
from dxn3 import *
import random, math

background("#0a0d1c")
ship  = rect("ship",  W // 2 - 6, H - 12, 12, 5, "#8b5cf6"); ship.tag = "ship"
ship.glow = 0                             # declare the light before it speaks
enemy = circle("enemy", W // 3, 6, 10, 10, "#fb7185"); enemy.tag = "enemy"
enemy.alpha = 0.15                       # the first threat drifts in too
twin  = circle("twin",  W - 18, 14, 7, 7, "#38bdf8"); twin.tag = "twin"
twin.alpha = 0.15                        # the twin announces itself as well
hud   = label("hud", 2, 2, "SCORE 0")
score, shots = 0, 0
live = []                                # the bolts still in the sky
DRIFT = 0.9                              # seconds from ghost to full
TWIN_SPEED = 0.55                        # the twin drifts nearly twice as fast
TWIN_BOB = 4.0                           # the bob's amplitude, world px
twb = 14.0                               # the bob's base row
twp = 0.0                                # the bob's phase
TH = random.Random("the threat's return")  # one stream per concern —
TW = random.Random("the twin's return")    # each named after what it grows

def on_key(k):
    global shots
    if k == "left":  ship.x = ship.x - 1
    if k == "right": ship.x = ship.x + 1
    if k == "space":
        shots += 1
        s = circle(f"shot{shots}", ship.x + 5, ship.y - 3, 3, 3, "#facc15")
        s.vy = -2.5
        s.tag = "shot"
        s.glow = 2                       # the bolt carries its own light
        ship.glow = 5                    # the muzzle speaks — tick fades it
        live.append(s)                   # the ledger remembers its own

def on_tick(dt2):
    global twp
    enemy.x = enemy.x + 0.3
    if enemy.x > W - 12: enemy.x = 2
    if enemy.alpha < 1: enemy.alpha = min(1, enemy.alpha + dt2 / DRIFT)
    twp += dt2 * 2.2                     # the bob's phase, honest in dt
    twin.x = twin.x + TWIN_SPEED
    if twin.x > W - 9: twin.x = 2
    twin.y = twb + math.sin(twp) * TWIN_BOB
    if twin.alpha < 1: twin.alpha = min(1, twin.alpha + dt2 / DRIFT)
    if ship.glow > 0: ship.glow = max(0, ship.glow - 12 * dt2)
    # the bolts come home: what leaves the sky takes its light with it.
    # a shot that never dies is an entity the studio scans forever —
    # the hit-pair scan is O(n^2) over the scene, so a leak here is a
    # slow-down paid on every later frame.
    for s in live[:]:
        if s.y < -4:
            destroy(s.name)
            live.remove(s)
    hud.text = "SCORE " + str(score)

def on_hit(a, b):
    global score, twb, twp
    pair = (a.tag, b.tag)
    if "shot" in pair and "enemy" in pair:
        shot = a if a.tag == "shot" else b
        score += 10
        destroy(shot.name)
        for s in live[:]:
            if s.name == shot.name:
                live.remove(s)           # the ledger forgets the spent bolt
        enemy.x = TH.randint(2, W - 14)  # the threat's own stream answers
        enemy.y = TH.randint(2, H // 2)
        enemy.alpha = 0.15               # the next threat fades in from the void
        print("hit! score", score)
    elif "shot" in pair and "twin" in pair:
        shot = a if a.tag == "shot" else b
        score += 25                      # the twin pays double-plus — it moves
        destroy(shot.name)
        for s in live[:]:
            if s.name == shot.name:
                live.remove(s)
        twin.x = TW.randint(2, W - 14)   # the twin's own stream, never shared
        twb = TW.randint(6, H // 2)      # the bob re-anchors at the new row
        twin.y = float(twb)
        twp = 0.0
        twin.alpha = 0.15                # and the void announces it again
        print("twin! score", score)

run()
