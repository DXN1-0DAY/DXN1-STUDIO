# THE WINDMILL in the DXN1 STUDIO — a love letter to the turn.
# run:  dxn3 sdk/examples/windmill.py
# left / right slow or hasten the mill · space holds the wind · the
# blades ORBIT the hub (the SDK drives x/y/rot each tick) while the
# hub's little square turns ITSELF (the engine's own spin — no SDK
# work at all). Two kinds of rotation, one sky.
# the DUSK LAW: the day is measured in turns — every degree the wind
# carries is a degree of the day (a full day per 720°). The sun's
# alpha sweeps 1.0 → 0.45 and back, the clouds wear the dusk at a
# third of its depth, the sun glows by day and goes dark at
# nightfall, and holding the wind holds the sun where it stands.
import math
from dxn3 import *

background("#0d1226")

hud = label("hud", 2, 1, "THE MILL  ·  left/right the wind  ·  space holds")

sun = circle("sun", 5, 3, 7, 7, "#fbbf24")
cloud_a = rect("cloud-a", 14, 6, 16, 3, "#3b4468")
cloud_b = rect("cloud-b", 58, 10, 20, 3, "#333c5e")
grass = rect("grass", 0, H - 4, W, 4, "#14532d")
grass.fill = "gradient"
grass.color2 = "#0e3a20"

tower = rect("tower", W // 2 - 7, H - 22, 14, 18, "#5b4a7a")
tower.fill = "gradient"
tower.color2 = "#3c3157"
cap = rect("cap", W // 2 - 5, H - 25, 10, 4, "#7c6aa6")
door = rect("door", W // 2 - 2, H - 8, 4, 6, "#241c38")

HUB_X, HUB_Y = W // 2, H - 23          # the blades turn about the cap
hubspin = rect("hubspin", HUB_X - 2, HUB_Y - 2, 5, 5, "#facc15")
hubspin.spin = 180                     # the engine turns this one itself

BLADES = []
for i in range(4):
    b = rect(f"blade-{i}", HUB_X - 1, HUB_Y - 18, 3, 18, "#e2e8f0")
    b.tag = "blade"
    BLADES.append(b)

speed = 90.0                           # wind degrees per second
wdir = 0.0                             # where the wind points now
held = True
daydeg = 0.0                           # the day, measured in turns


def dusk_depth():
    """0 at noon, 1 at the deepest nightfall — a cosine on the day."""
    return 0.5 - 0.5 * math.cos(math.radians(daydeg))


def phase(d):
    if d < 0.35:
        return "noon"
    return "dusk" if d < 0.75 else "nightfall"


def hud_text():
    return (f"THE MILL  ·  wind {speed:.0f}°/s"
            f"{' · HELD' if not held else ''}")


def place_blades():
    """orbit the hub, and keep each blade radial — the long axis of a
    vertical rect points along y, so the body's rot is θ - 90."""
    for i, b in enumerate(BLADES):
        th = math.radians(wdir + i * 90)
        cx = HUB_X + 11.5 * math.cos(th)
        cy = HUB_Y + 11.5 * math.sin(th)
        b.x = round(cx - 1.5)
        b.y = round(cy - 9)
        b.rot = (wdir + i * 90) - 90


def on_start():
    place_blades()


def on_tick(dt2):
    global wdir, daydeg
    if not held:
        return
    wdir = (wdir + speed * dt2) % 360
    daydeg = (daydeg + speed * dt2) % 720.0   # a degree of wind, a degree of day
    d = dusk_depth()
    sun.alpha = 1.0 - 0.55 * d              # the sun sweeps 1.0 → 0.45
    sun.glow = 4 if d < 0.4 else 0          # a lantern by day, a coal by night
    cloud_a.alpha = 1.0 - 0.35 * d          # the clouds wear the dusk too
    cloud_b.alpha = 1.0 - 0.35 * d
    place_blades()
    # the clouds drift with the same wind, and wrap the sky honestly
    cloud_a.x = (cloud_a.x + dt2 * 6) % (W + 20) - 10
    cloud_b.x = (cloud_b.x + dt2 * 9) % (W + 24) - 12
    hud.text = hud_text() + f"  ·  {phase(d)}"


def on_key(k):
    global speed, held
    if k == "left":
        speed = max(15.0, speed - 30.0)
    elif k == "right":
        speed = min(400.0, speed + 30.0)
    elif k == "space":
        held = not held
    hud.text = hud_text()


run()
