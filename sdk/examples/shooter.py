# a SHOOTER in the DXN1 STUDIO — run:  dxn3 sdk/examples/shooter.py
# v3.1.47 wears the engine's light: the muzzle GLOWS when you fire
# (and fades honestly in tick), bolts carry their own small halo, and
# every hit respawns the next threat as a GHOST — alpha 0.15 rising to
# full over DRIFT seconds, the radar-field's law, so the void always
# announces what it is about to throw at you. Even the first threat
# drifts in.
from dxn3 import *
import random

background("#0a0d1c")
ship  = rect("ship",  W // 2 - 6, H - 12, 12, 5, "#8b5cf6"); ship.tag = "ship"
ship.glow = 0                             # declare the light before it speaks
enemy = circle("enemy", W // 3, 6, 10, 10, "#fb7185"); enemy.tag = "enemy"
enemy.alpha = 0.15                       # the first threat drifts in too
hud   = label("hud", 2, 2, "SCORE 0")
score, shots = 0, 0
DRIFT = 0.9                              # seconds from ghost to full

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

def on_tick(dt2):
    enemy.x = enemy.x + 0.3
    if enemy.x > W - 12: enemy.x = 2
    if enemy.alpha < 1: enemy.alpha = min(1, enemy.alpha + dt2 / DRIFT)
    if ship.glow > 0: ship.glow = max(0, ship.glow - 12 * dt2)
    hud.text = "SCORE " + str(score)

def on_hit(a, b):
    global score
    if "shot" in (a.tag, b.tag) and "enemy" in (a.tag, b.tag):
        score += 10
        destroy((a if a.tag == "shot" else b).name)
        enemy.x = random.randint(2, W - 14)
        enemy.y = random.randint(2, H // 2)
        enemy.alpha = 0.15               # the next threat fades in from the void
        print("hit! score", score)

run()
