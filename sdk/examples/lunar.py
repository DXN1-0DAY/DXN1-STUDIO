# LUNAR LANDER in the DXN1 STUDIO — gravity is the enemy, the pads forgive.
# run:  dxn3 sdk/examples/lunar.py
# left/right side-thrusters · space burns the main engine · land SOFT.
from dxn3 import *
import random

background("#050810")

hud = label("hud", 2, 2, "FUEL 100 · SCORE 0 · LIVES 3")
fuel = 100.0
score = 0
lives = 3
flash = 0.0            # freeze beats: touchdown pays, crash mourns
burn = 0.0             # the flame lives only this long after a burn

# the moonscape: hills are honest (and lethal) ground, pads pay
HILLS = [(-40, 430, 260, 120), (250, 390, 180, 160), (760, 400, 300, 150),
         (1090, 360, 200, 190), (1320, 430, 320, 120)]
PADS = [(460, 440, 130, 14, 50),      # the valley pad — easy, small pay
        (1140, 346, 110, 14, 100)]    # the summit pad — risky, double

for i, (x, y, w, h) in enumerate(HILLS):
    hill = rect(f"hill{i}", x, y, w, h, "#1f2937")
    hill.tag = "ground"

pays = {}
for i, (x, y, w, h, pay) in enumerate(PADS):
    p = rect(f"pad{i}", x, y, w, h, "#22c55e")
    p.tag = "pad"
    pays[f"pad{i}"] = pay

land = circle("land", W // 2, 40, 14, 14, "#e9e5ff")
land.tag = "ship"
flame = circle("flame", W // 2, 56, 6, 6, "#facc15")
flame.visible = 0

G = 60.0               # the moon pulls gently
BURN = 95.0            # main engine acceleration
SIDE = 40.0            # side thrusters
SOFT_VY = 65.0         # the fastest touch the legs forgive
SOFT_VX = 35.0
gen = 0


def respawn_lander():
    global fuel, burn
    land.x = random.randint(20, W - 40)
    land.y = 30
    land.vx = random.choice([-12, 12])
    land.vy = 10
    fuel = 100.0
    burn = 0.0
    flame.visible = 0


def freeze(beat):
    global flash, burn
    flash = beat
    land.vx = land.vy = 0            # the world holds its breath
    flame.visible = 0
    burn = 0.0


def on_key(k):
    if flash > 0 or fuel <= 0:
        return
    if k == "space":
        land.vy -= BURN * dt
        fuel = max(0.0, fuel - 14 * dt)
        burn = 0.09
    elif k == "left":
        land.vx -= SIDE * dt
        fuel = max(0.0, fuel - 4 * dt)
    elif k == "right":
        land.vx += SIDE * dt
        fuel = max(0.0, fuel - 4 * dt)


def crash(why):
    global lives, score, flash
    lives -= 1
    if lives <= 0:
        print(f"game over — final score {score}")
        score = 0
        lives = 3
    else:
        print(f"crash — {why}")
    vars(score=score)
    freeze(1.2)


def on_tick(dt2):
    global flash, burn, score
    if burn > 0:
        burn -= dt2
        if burn <= 0:
            flame.visible = 0
    if flash > 0:
        flash -= dt2
        if flash <= 0:
            if lives > 0:
                respawn_lander()
        return
    land.vy += G * dt2               # the moon never sleeps
    if land.y > H + 60:
        crash("lost to the dark below")
    elif land.x < -30 or land.x > W + 30:
        crash("drifted off the moon")
    hud.text = f"FUEL {int(fuel)} · SCORE {score} · LIVES {lives}"


def on_hit(a, b):
    global score, flash
    if flash > 0:
        return
    other = b if a.name == "land" else (a if b.name == "land" else None)
    if other is None:
        return
    if other.tag == "ground":
        crash("the hills are not for landing")
        return
    if other.tag == "pad":
        if abs(land.vy) > SOFT_VY or abs(land.vx) > SOFT_VX:
            crash(f"{int(land.vy)} down, {int(land.vx)} across — legs gave")
            return
        pay = pays.get(other.name, 0)
        score += pay
        vars(score=score)
        print(f"touchdown — pad pays {pay} · fuel left {int(fuel)}")
        freeze(1.4)


respawn_lander()
run()
