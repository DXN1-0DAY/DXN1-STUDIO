#!/usr/bin/env python3
# DS2-R26 probe: bounce.js "the lantern flares" — v3.1.69.
# Deterministic by construction: every hit is INJECTED (the probe law —
# a probe that waits for a real overlap waits forever), so no steering
# lottery and no Math.random dependence. Pins, on the real wire
# (node SDK, dt 0.05, the host's own 120x84 room):
#  1. the lantern rests at glow 2 (unchanged — the room's lamp);
#  2. a brick BITE flares it to glow 4, WHOLE in the hit frame
#     (on.hit runs after the tick — the birth-tick law, hit edition);
#  3. the flare wears back down the honest 3/s staircase (4 -> 3.85 ->
#     3.70 ...) to its RESTING FLOOR 2 — a flare with a floor: never
#     below the lamp's own rest, never a flash-forever;
#  4. twelve injected bites clear the wall — the win plaque is born
#     with a bloom of glow 3, worn 3/s to dark (2.85, 2.70, ... 0),
#     the words STAY after the light is gone (a plaque is not a lamp);
#  5. three lost balls (a fresh child, untouched) light the game-over
#     plaque under the same law.
import json, subprocess, sys, os, select

import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
REPO = _HOME
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

def spawn_child():
    p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "bounce.js")],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    return p

def send(p, o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def read(p, timeout=4.0):
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r: return None
    line = p.stdout.readline()
    if not line: return None
    try: return json.loads(line)
    except Exception: return None

def frame(p, keys=None, hits=None, dt=0.05):
    send(p, {"t": "tick", "dt": dt,
             "keys": {k: True for k in (keys or [])},
             "chars": "", "hits": hits or []})
    while True:
        f = read(p)
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

def hello(p, w=120, h=84):
    send(p, {"t": "hello", "w": w, "h": h})
    scene = read(p)
    assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
    return scene

# ================= child 1: the flare and the win plaque =================
p = spawn_child()
scene = hello(p)
ents = {e["name"]: e for e in scene["entities"]}
pin("scene has 21 entities", len(ents) == 21, str(len(ents)))
pin("the lantern rests at glow 2", ents["ball"].get("glow") == 2,
    str(ents["ball"].get("glow")))

def step1(hits=None):
    """one tick of host-played rally: with no hit of our own to send,
    save the ball whenever it falls past mid-court — the host's own
    arbitration, keeping the balls bank alive across the wait walks."""
    global ents
    b = ents["ball"]
    if not hits and b["y"] > 50 and b["vy"] > 0:
        ents, f = frame(p, hits=["ball", "pad"])
    else:
        ents, f = frame(p, hits=hits)
    return f

# 1. the bite: inject the first brick pair
ents, f = frame(p, hits=["ball", "brick0"])
pin("the bite flares the lantern WHOLE (glow 4)", ents["ball"].get("glow") == 4,
    str(ents["ball"].get("glow")))
pin("the brick is destroyed in the same frame", "brick0" in f.get("del", []),
    str(f.get("del")))
pin("the hud pays one tick late (the lag law)",
    "BRICKS 12" in ents["hud"]["text"], ents["hud"]["text"])

# 2. the honest wear back to the floor
f = step1()
g1 = ents["ball"].get("glow")
f = step1()
g2 = ents["ball"].get("glow")
pin("wear steps (3.85, 3.70)", abs(g1 - 3.85) < 1e-9 and abs(g2 - 3.7) < 1e-9,
    f"{g1}, {g2}")
for _ in range(14):                      # (4-2)/0.15 ~= 13.3 ticks to the floor
    step1()
pin("the flare settles at the lantern's REST (exactly 2)",
    ents["ball"].get("glow") == 2, str(ents["ball"].get("glow")))
floored = True
for _ in range(30):                      # the floor HOLDS — never below rest
    step1()
    if ents["ball"].get("glow") != 2: floored = False
pin("the floor holds for 30 more ticks (never below the rest)", floored,
    str(ents["ball"].get("glow")))

# 3. twelve bites clear the wall — the win plaque's honest bloom.
# The probe plays host: while the ball falls past mid-court it injects
# a pad save (the host's own arbitration) so the rally survives the
# twelve bites — an untouched ball would drain the balls bank mid-wall.
cleared_frame = None
i, bites, guard = 1, 0, 0
while bites < 11 and i <= 11 and guard < 400:
    guard += 1
    b = ents["ball"]
    if b["y"] > 50 and b["vy"] > 0:
        step1(hits=["ball", "pad"])      # the save does not consume a bite
        continue
    f = step1(hits=["ball", f"brick{i}"])
    bites += 1
    if i == 11: cleared_frame = f        # the twelfth bite lights the plaque
    i += 1
pin("twelve honest bites clear the wall (the bites bit)",
    bites == 11 and cleared_frame is not None, f"bites={bites}")
pin("the win plaque is born", cleared_frame is not None and "win" in ents,
    str(sorted(ents)))
pin("the win plaque is BORN WHOLE (glow 3)",
    ents.get("win", {}).get("glow") == 3, str(ents.get("win", {}).get("glow")))
plaque_glow_seq = []
for _ in range(24):                      # the wear: 2.85 .. 0 at dt 0.05
    step1()
    plaque_glow_seq.append(ents.get("win", {}).get("glow"))
first3 = plaque_glow_seq[:3]
pin("the plaque's bloom wears 3/s (2.85, 2.70, 2.55)",
    len(plaque_glow_seq) > 2 and
    all(g is not None for g in first3) and
    abs(first3[0] - 2.85) < 1e-9 and
    abs(first3[1] - 2.7) < 1e-9 and
    abs(first3[2] - 2.55) < 1e-9, str(first3))
pin("the plaque's light empties — the words STAY",
    plaque_glow_seq[-1] == 0 and ents.get("win", {}).get("visible") == 1,
    f"glow={plaque_glow_seq[-1]} visible={ents.get('win', {}).get('visible')}")
pin("the hud pays its toll one tick late (BRICKS 0 after the wear)",
    "BRICKS 0" in ents["hud"]["text"], ents["hud"]["text"])
p.kill()

# ================= child 2: the game-over plaque, untouched =============
p2 = spawn_child()
hello(p2)
over_seen = None
for _ in range(90):                      # three untouched falls (~9 ticks each)
    ents, f = frame(p2)
    if "over" in ents and over_seen is None:
        over_seen = (ents["over"].get("glow"), ents["over"].get("visible"))
        break
pin("three lost balls light the game-over plaque", over_seen is not None,
    str(ents["hud"]["text"]))
pin("the over plaque is BORN WHOLE (glow 3)",
    over_seen == (3, 1), str(over_seen))
wear = []
for _ in range(24):
    ents, _ = frame(p2)
    wear.append(ents.get("over", {}).get("glow"))
pin("the over plaque's bloom wears 3/s to dark",
    abs(wear[0] - 2.85) < 1e-9 and wear[-1] == 0, f"{wear[0]} .. {wear[-1]}")
p2.kill()

print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the lantern flares, the plaques wear honestly")
