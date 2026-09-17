# LUNAR LANDER in the DXN1 STUDIO — gravity is the enemy, the pads forgive.
# run:  dxn3 sdk/examples/lunar.py
# left/right side-thrusters · space burns the main engine · land SOFT.
# v3.1.49 — the last light: the flame FOLLOWS the lander (it used to
# burn at the spawn point forever — a latent bug the polish round
# exposed), it GLOWS while burning, the pads wear halos sized to
# their pay (the brighter the halo, the richer the touchdown), and a
# clean landing BLEACHES the lander gold-white for a beat.
# v3.1.65 — the halos BREATHE: one shared clock (the snake meal's
# 4-rad sine), two amplitudes — the summit's halo breathes taller
# because its pay is richer (the halo IS the pay, still). They are
# born at the top of the breath (whole, no pop), and a touchdown
# makes the pleased pad FLARE (+2 bloom) that wears at the house's
# 3/s even while the freeze holds the world — no flash-forever.
from dxn3 import *
import math
import random

background("#050810")

hud = label("hud", 2, 2, "FUEL 100 · SCORE 0 · LIVES 3")
fuelbar = rect("fuelbar", 2, 5, 28, 2, "#22c55e")   # the tank, drawn honest
fuel = 100.0
score = 0
lives = 3
flash = 0.0            # freeze beats: touchdown pays, crash mourns
burn = 0.0             # the flame lives only this long after a burn
alarm_t = 0.0          # the low-fuel blink's clock
warned_low = False     # the one honest warning per tank

# the moonscape: hills are honest (and lethal) ground, pads pay
HILLS = [(-40, 430, 260, 120), (250, 390, 180, 160), (760, 400, 300, 150),
         (1090, 360, 200, 190), (1320, 430, 320, 120)]
PADS = [(460, 440, 130, 14, 50),      # the valley pad — easy, small pay
        (1140, 346, 110, 14, 100)]    # the summit pad — risky, double

for i, (x, y, w, h) in enumerate(HILLS):
    hill = rect(f"hill{i}", x, y, w, h, "#1f2937")
    hill.tag = "ground"

pays = {}
blooms = {}                            # a pleased pad's flare, wearing
pad_t = math.pi / 2                    # the halos' shared clock, born
                                       # at the breath's TOP (no pop)
for i, (x, y, w, h, pay) in enumerate(PADS):
    p = rect(f"pad{i}", x, y, w, h, "#22c55e")
    p.tag = "pad"
    p.glow = 2 + pay // 50             # the halo IS the pay: 3 and 4
    pays[f"pad{i}"] = pay
    blooms[f"pad{i}"] = 0.0


def paint_halo(nm):                    # one clock, two amplitudes: the
    e = find(nm)                       # breath is base*(0.75+0.25*sin)
    if e:                              # and the pay still reads — the
        base = 2 + pays[nm] // 50      # summit's halo breathes taller
        e.glow = round(base * (0.75 + 0.25 * math.sin(pad_t))
                       + blooms[nm], 3)

land = circle("land", W // 2, 40, 14, 14, "#e9e5ff")
land.tag = "ship"
flame = circle("flame", W // 2, 56, 6, 6, "#facc15")
flame.visible = 0
flame.glow = 0
land.flash = 0.0                        # declared before it is read (the
                                        # shooter round's law)

G = 60.0               # the moon pulls gently
BURN = 95.0            # main engine acceleration
SIDE = 40.0            # side thrusters
SOFT_VY = 65.0         # the fastest touch the legs forgive
SOFT_VX = 35.0
gen = 0


def respawn_lander():
    global fuel, burn, warned_low
    land.x = random.randint(20, W - 40)
    land.y = 30
    land.vx = random.choice([-12, 12])
    land.vy = 10
    fuel = 100.0
    burn = 0.0
    warned_low = False               # a fresh tank earns a fresh warning
    fuelbar.w = 28
    fuelbar.color = "#22c55e"
    fuelbar.visible = 1
    flame.visible = 0
    flame.glow = 0
    land.flash = 0.0


def freeze(beat):
    global flash, burn
    flash = beat
    land.vx = land.vy = 0            # the world holds its breath
    flame.visible = 0
    flame.glow = 0
    burn = 0.0


def on_key(k):
    global fuel, burn               # the tank and the flame's fuse are the
    if flash > 0 or fuel <= 0:      # module's — without burn's word the
        return                      # flame lit once and burned forever at
    if k == "space":                # the spawn point (a latent bug the
        land.vy -= BURN * dt        # last-light probe exposed: burn was a
        fuel = max(0.0, fuel - 14 * dt)   # LOCAL — the module's fuse
        burn = 0.09                       # never burned down)
        flame.visible = 1
        flame.glow = 4              # the burn's own light
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
        win(f"game over — final score {score}")
        print(f"game over — final score {score}")
        score = 0
        lives = 3
    else:
        say(f"crash — {why}")
        print(f"crash — {why}")
    vars(score=score)
    freeze(1.2)


def on_tick(dt2):
    global flash, burn, score, alarm_t, warned_low, pad_t
    # A PLEASED PAD'S FLARE WEARS at 3/s — even while the freeze holds
    # the world (the studio keeps the last light a wire game sent, so
    # a flare the game never wears is a flare FOREVER). The breath
    # itself pauses with the world: the freeze holds its breath.
    for nm in blooms:
        if blooms[nm] > 0:
            blooms[nm] = max(0.0, blooms[nm] - 3 * dt2)
            paint_halo(nm)
    if burn > 0:
        burn -= dt2
        if burn <= 0:
            flame.visible = 0
            flame.glow = 0
    # the flame RIDES the lander now — it used to burn at the spawn
    # point forever, a fixture of the launch pad rather than the ship
    flame.x = land.x + 4
    flame.y = land.y + 16
    if flash > 0:
        flash -= dt2
        if land.flash > 0:
            # the gold-white beat DECAYS — 1.5/s, the honest staircase
            # (PROTOCOL.md). It used to hold full bleach for the whole
            # freeze and pop back to normal on respawn: a hold, not a
            # beat. A touchdown now blooms and fades like one.
            land.flash = round(max(0.0, land.flash - 1.5 * dt2), 3)
        if flash <= 0:
            if lives > 0:
                respawn_lander()
        return
    land.vy += G * dt2               # the moon never sleeps
    pad_t = (pad_t + 4 * dt2) % (2 * math.pi)   # the halos breathe,
    for nm in blooms:                # 4 rad/s — the snake meal's sine
        paint_halo(nm)
    if land.y > H + 60:
        crash("lost to the dark below")
    elif land.x < -30 or land.x > W + 30:
        crash("drifted off the moon")
    # the gauge: the tank empties in width AND in color — green while
    # rich, amber under half, red under a quarter, BLINKING when the
    # landing has to be planned, a flat line when the tank is dry
    fuelbar.w = max(0.0, 28 * fuel / 100)
    fuelbar.color = ("#22c55e" if fuel > 50
                     else "#facc15" if fuel > 25 else "#ef4444")
    if 0 < fuel <= 25:
        alarm_t = (alarm_t + dt2) % 0.8
        fuelbar.visible = 1 if alarm_t < 0.5 else 0
    else:
        alarm_t = 0.0
        fuelbar.visible = 1
    if fuel <= 25 and not warned_low:
        warned_low = True
        say("fuel low — plan the landing")
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
        say(f"+{pay} — touchdown")
        print(f"touchdown — pad pays {pay} · fuel left {int(fuel)}")
        land.flash = 1.0             # the gold-white beat the legs earned
        blooms[other.name] = min(6.0, blooms.get(other.name, 0.0) + 2.0)
        paint_halo(other.name)       # the pleased pad FLARES
        freeze(1.4)


respawn_lander()
run()
