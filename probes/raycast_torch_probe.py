#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R21 probe: raycast.py "the torch breathes" — the game is python,
# so the probe mirrors the march BIT FOR BIT.
# pins: 26 entities; the eye's lantern glows (2); a still world BREATHES
# — the wall colors sway on the torch's sine and the probe's full
# ray-march mirror matches the engine's colors exactly, tick for tick;
# the breath is honest (multiple distinct colors, a true period, the
# same stillness twice gives the same colors twice); and turning still
# paints a different world (the old law, untouched).
import json, subprocess, sys, os, math

# THE BUFFER LAW (v3.1.105): the read goes through the fleet's shared
# harness (probes/_harness.py) — raw os.read, own line buffer — the old
# select-on-the-fd + readline-on-a-buffered-stream pairing was the
# deadlock species.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Wire


EX = _os.path.join(_HOME, "sdk", "examples")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

env = dict(os.environ)
env["PYTHONPATH"] = _os.path.join(_HOME, "sdk")
p = subprocess.Popen(["python3", f"{EX}/raycast.py"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

w = Wire(p)

def send(o):
    w.send(o)

def read(timeout=4.0):
    return w.read(timeout)

def frame(keys=None, dt=0.05):
    w.send({"t": "tick", "dt": dt, "keys": {k: True for k in (keys or [])},
            "chars": "", "hits": []})
    while True:
        f = w.read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}

W, H = 120, 84
send({"t": "hello", "w": W, "h": H})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents = {e["name"]: e for e in scene["entities"]}
NCOL = max(24, min(110, W // 8))
pin(f"scene has {NCOL + 2} entities ({NCOL} columns, hud, mark)",
    len(ents) == NCOL + 2, str(len(ents)))
pin("the eye's lantern glows (2)", ents["mark"].get("glow") == 2,
    str(ents["mark"].get("glow")))

# the mirror: the game IS python — replicate the march exactly
MAP = ["################", "#..............#", "#.####.....##..#",
       "#.#..........#.#", "#.#..###..#..#.#", "#.......#..#...#",
       "#.###..##......#", "#.....#....##..#", "#..#.....#...#.#",
       "#..#.##......#.#", "#..............#", "################"]
MH, MW = len(MAP), len(MAP[0])
CELL = 64.0
FOV = math.pi / 3.0
px, py = 1.5 * CELL, 1.5 * CELL
COLW = W / NCOL

def solid(mx, my):
    if mx < 0 or my < 0 or my >= MH or mx >= MW:
        return True
    return MAP[my][mx] == "#"

def mirror_shade(i, flick):
    ray = 0.0 - FOV / 2 + FOV * (i + 0.5) / NCOL
    step = 4.0
    dist, kind = 1.0, "y"
    cx, cy = px, py
    sx, sy = math.cos(ray) * step, math.sin(ray) * step
    for _ in range(600):
        cx += sx; cy += sy
        mx, my = int(cx // CELL), int(cy // CELL)
        if solid(mx, my):
            dist = math.hypot(cx - px, cy - py)
            kind = "x" if int((cx - sx) // CELL) != mx else "y"
            break
    t = max(0.0, min(1.0, 1.0 - dist / (9.0 * CELL)))
    if kind == "x":
        r, g, b = int(90 + 120 * t), int(70 + 90 * t), int(200 + 55 * t)
    else:
        r, g, b = int(60 + 70 * t), int(45 + 55 * t), int(140 + 40 * t)
    r = min(255, int(r * flick))
    g = min(255, int(g * flick))
    b = min(255, int(b * flick))
    return f"#{r:02x}{g:02x}{b:02x}"

# 1. a still world breathes: hold still, mirror the colors tick for tick.
tt = 0.0
mirror_ok = True
worst_name = ""
seen = set()
seq0 = []
for k in range(1, 61):
    ents = frame()
    tt += 0.05
    flick = 1.0 + 0.05 * math.sin(tt * 9.0)
    for i in (0, NCOL // 2, NCOL - 1):
        want = mirror_shade(i, flick)
        got = ents[f"c{i}"]["color"]
        if got != want:
            mirror_ok = False
            worst_name = f"c{i} tick {k}: {got} != {want}"
    seen.add(ents[f"c{NCOL // 2}"]["color"])
    seq0.append(ents["c0"]["color"])
pin("the wall colors mirror the torch's breath exactly (3 columns x 60 ticks)",
    mirror_ok, worst_name)
pin("the breath is real (the mid column wears many colors)", len(seen) >= 4,
    f"{len(seen)} distinct")

# 2. the breath is near-periodic: the sine returns to its phase every
# ~14 ticks; 8-bit colors quantize, so period-mates stay within 2 units.
def chans(hx):
    return int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16)
period = int(round(2 * math.pi / (9.0 * 0.05)))
near = all(max(abs(a - b) for a, b in zip(chans(seq0[k]), chans(seq0[k + period]))) <= 2
           for k in range(0, len(seq0) - period))
maxd = max(max(abs(a - b) for a, b in zip(chans(seq0[k]), chans(seq0[k + period])))
           for k in range(0, len(seq0) - period))
pin(f"the breath returns to itself every {period} ticks (within 2 units)",
    near, f"max channel drift={maxd}")

# 3. turning still paints a different world (the old law, untouched).
before = ents["c0"]["color"]
ents = frame(keys=["left"])
after = ents["c0"]["color"]
pin("turning paints a different world", before != after,
    f"{before} -> {after}")

print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the torch breathes")
