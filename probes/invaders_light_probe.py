#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R21 probe: invaders.js "the war wears the light" — over the real
# wire (node SDK) at the host's own geometry (120x84).
# pins: 51 entities; every wave GHOSTS IN — the alien grid and the
# shelters share one clock, alpha 0.15 rising to full over 0.9 s, and
# the mirror matches the engine bit for bit (worst err 0.0); the
# muzzle GLOWS 4 on the fire frame (keys fire after the tick) and
# cools down the honest staircase 3.6, 3.2; the flying shot wears
# halo 2 and the SPENT shot parks its light (glow 0 at the top);
# their bombs fly lit (2) and park dark; and a steered host kills a
# real alien — score 30, the seat emptied, the spent shot dark.
import json, subprocess, sys, os

# THE BUFFER LAW (v3.1.105): the read goes through the fleet's shared
# harness (probes/_harness.py) — raw os.read, own line buffer — the old
# select-on-the-fd + readline-on-a-buffered-stream pairing was the
# deadlock species.

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Wire

REPO = _HOME
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "invaders.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

w = Wire(p)

def send(o):
    w.send(o)

def read(timeout=4.0):
    return w.read(timeout)

def frame(keys=None, chars="", dt=0.05, hits=None):
    w.send({"t": "tick", "dt": dt,
            "keys": {k: True for k in (keys or [])},
            "chars": chars, "hits": hits or []})
    while True:
        f = w.read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

W, H = 120, 84
send({"t": "hello", "w": W, "h": H})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
names = [e["name"] for e in scene["entities"]]
pin("scene has 62 entities", len(names) == 62, str(len(names)))

# 1. the ghost-in: grid and shelters share one clock, mirrored exactly.
waveT = 0.0
worst = 0.0
rise_ok = True
prev = -1.0
landed = False
for k in range(1, 26):
    ents, f = frame()
    waveT = min(1.0, waveT + 0.05 / 0.9)   # the engine's own accumulation
    A = 0.15 + 0.85 * waveT
    a0 = ents["alien-0-0"].get("alpha")
    s0 = ents["shield-0-0"].get("alpha")
    if a0 is None or s0 is None:
        rise_ok = False
        break
    worst = max(worst, abs(a0 - A), abs(s0 - A))
    if a0 < prev - 1e-12:
        rise_ok = False                    # the drift must never sink
    prev = a0
    if k >= 19 and a0 == 1.0:
        landed = True
pin("the wave ghosts in on one shared clock (grid + shelters, worst err %.1e)"
    % worst, rise_ok and worst == 0.0, f"worst={worst}")
pin("the drift only rises, and lands at full alpha (1.0)", rise_ok and landed,
    f"a0={ents['alien-0-0'].get('alpha')}")

# 2. the muzzle: the fire frame carries the full 4, then cools 8/s.
ents, f = frame(keys=["space"])
pin("the fire frame speaks glow 4 from the muzzle",
    ents["player"].get("glow") == 4, str(ents["player"].get("glow")))
pin("the flying shot wears halo 2", ents["shot-0"].get("glow") == 2,
    str(ents["shot-0"].get("glow")))
ents, f = frame()
g1 = ents["player"].get("glow")
ents, f = frame()
g2 = ents["player"].get("glow")
pin("the muzzle cools down the honest staircase (3.6, 3.2)",
    abs(g1 - 3.6) < 1e-9 and abs(g2 - 3.2) < 1e-9, f"{g1}, {g2}")

# 3. the spent shot parks its light (flies to the top, parks dark).
parked = False
for i in range(40):
    ents, f = frame(dt=0.1)
    if ents["shot-0"]["x"] == -999:
        parked = True
        break
pin("the spent shot parks its body AND its light (glow 0)",
    parked and ents["shot-0"].get("glow") == 0,
    f"parked={parked} glow={ents['shot-0'].get('glow')}")

# 4. their bombs fly lit, and park dark.
lit = False
park_b = False
for i in range(120):
    ents, f = frame(dt=0.1)
    for bi in range(3):
        b = ents[f"bomb-{bi}"]
        if b["x"] > -100 and b.get("glow") == 2:
            lit = True
        if b["x"] == -999 and b.get("glow") == 0 and b["y"] > 0:
            park_b = True                  # flew its course, parked dark
    if lit and park_b:
        break
pin("a flying bomb wears halo 2", lit)
pin("a spent bomb parks dark", park_b)

# 5. a steered host kills a real alien — and the spent shot is dark.
# a rising shot eats the target's COLUMN from below (rows 2, 1, then
# 0 — each row it crosses is an honest kill), and every kill THINS
# the grid, which QUADRUPLES the march (stepEvery falls back to 0.2)
# — so the host measures the march rate live, aims at the lowest
# alive alien of the column, and leads by rate × flight time.
hist = []
killed = False
tname = None
for i in range(260):
    # the lowest alive alien of column 2 — the shot's first contact
    tname, tal = None, None
    for ri in (2, 1, 0):
        al = ents.get(f"alien-{ri}-2")
        if al and al.get("visible", 1):
            tname, tal = f"alien-{ri}-2", al
            break
    if tname is None:
        killed = True                      # the column is eaten whole
        break
    ax = tal["x"]
    hist.append(ax)
    if len(hist) > 12:
        hist.pop(0)
    rate = (hist[-1] - hist[0]) / max(1, len(hist) - 1)   # px per packet
    px = ents["player"]["x"]
    flight = max(1.0, (ents["player"]["y"] - 4 - (tal["y"] + 5)) / 2.0)
    aim = ax + rate * flight
    keys = []
    if aim > px + 1:
        keys = ["right"]
    elif aim < px - 1:
        keys = ["left"]
    if abs((px + 4) - aim) < 2.5:
        keys = keys + ["space"] if keys else ["space"]
    # inject the first real shot-alien overlap (the host's gift)
    hits = []
    for si in range(3):
        s = ents[f"shot-{si}"]
        if s["x"] > -100:
            for ri in range(3):
                for ci in range(5):
                    al = ents.get(f"alien-{ri}-{ci}")
                    if al and al.get("visible", 1) and \
                       s["x"] < al["x"] + 7 and s["x"] + 2 > al["x"] and \
                       s["y"] < al["y"] + 5 and s["y"] + 4 > al["y"]:
                        hits = [s["name"], al["name"]]
                        break
                if hits: break
        if hits: break
    ents, f = frame(keys=keys, hits=hits)
    dead = ents.get(tname)
    if dead is None or not dead.get("visible", 1):
        killed = True
        break
pin("the steered host kills a real alien (seat empty, honest score)", killed,
    f"last hits={hits}")
if killed:
    a = ents.get(tname)
    pin("the killed seat is gone from the world",
        a is None or not a.get("visible", 1) or a["y"] == -50)
    # the score law: every dead seat pays its row's price
    pts = [30, 20, 10]
    expect = 0
    for ri in range(3):
        for ci in range(5):
            al = ents.get(f"alien-{ri}-{ci}")
            if al is None or not al.get("visible", 1):
                expect += pts[ri]
    pin("the score speaks the honest sum of every row's price",
        f"score {expect}" in ents["hud"]["text"],
        f"hud={ents['hud']['text']} expect={expect}")
    spent_dark = all(ents[f"shot-{si}"].get("glow", 0) == 0
                     for si in range(3)
                     if ents[f"shot-{si}"]["x"] == -999)
    pin("every spent shot rests dark", spent_dark)
    pin("the surviving grid keeps its full light",
        ents["alien-0-0"].get("alpha") == 1.0,
        str(ents["alien-0-0"].get("alpha")))

print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the war wears the light")
