# a SHOOTER in the DXN1 STUDIO — run:  dxn3 sdk/examples/shooter.py
from dxn3 import *
import random

background("#0a0d1c")
ship  = rect("ship",  W // 2 - 6, H - 12, 12, 5, "#8b5cf6"); ship.tag = "ship"
enemy = circle("enemy", W // 3, 6, 10, 10, "#fb7185"); enemy.tag = "enemy"
hud   = label("hud", 2, 2, "SCORE 0")
score, shots = 0, 0

def on_key(k):
    global shots
    if k == "left":  ship.x = ship.x - 1
    if k == "right": ship.x = ship.x + 1
    if k == "space":
        shots += 1
        s = circle(f"shot{shots}", ship.x + 5, ship.y - 3, 3, 3, "#facc15")
        s.vy = -2.5
        s.tag = "shot"

def on_tick(dt2):
    enemy.x = enemy.x + 0.3
    if enemy.x > W - 12: enemy.x = 2
    hud.text = "SCORE " + str(score)

def on_hit(a, b):
    global score
    if "shot" in (a.tag, b.tag) and "enemy" in (a.tag, b.tag):
        score += 10
        destroy((a if a.tag == "shot" else b).name)
        enemy.x = random.randint(2, W - 14)
        enemy.y = random.randint(2, H // 2)
        print("hit! score", score)

run()
