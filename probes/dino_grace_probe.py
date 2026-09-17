#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R21 probe: dino.js "the grace law" — over the real wire (node SDK).
# pins: 20 entities (dust born parked); a grounded leap says "up!" and
# the arc mirrors the law EXACTLY tick for tick (rise floats at 90,
# fall bites at 144 — and the fall from the apex is shorter than the
# rise in continuous time); a press kept mid-air speaks "kept" and
# lands as "grace!" (the dino rises again the next frame); a kept
# press from high above decays and is honestly forgotten (no grace,
# but the touchdown still speaks dust at alpha 0.7 and the dust
# descends the honest staircase 0.56, 0.42 ... to zero and parks);
# standing feet raise no dust; and r after the fall walks again with
# nothing kept and no phantom dust. The death march injects the
# overlap itself — hits are the host's gift.
import json, subprocess, sys, os, select, math

REPO = _HOME
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "dino.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def read(timeout=4.0):
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r: return None
    line = p.stdout.readline()
    if not line: return None
    try: return json.loads(line)
    except Exception: return None

def frame(keys=None, chars="", dt=0.05, hits=None):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": hits or []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

H = 44
GROUND = H - 9          # dino's grounded y

send({"t": "hello", "w": 120, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
names = [e["name"] for e in scene["entities"]]
pin("scene has 24 entities (dust included)", len(names) == 24, str(len(names)))

ents, _ = frame()
dust = ents["dust"]
pin("the dust is born parked and transparent",
    dust["x"] == -999 and dust["alpha"] == 0, f"x={dust['x']} a={dust['alpha']}")

# 1. the grounded leap: "up!", and the arc mirrors the law exactly.
ents, f = frame(keys=["space"])
pin("a grounded leap speaks up!", f.get("say") == "up!", str(f.get("say")))

ys = []
while True:
    ents, f = frame()
    ys.append(ents["dino"]["y"])
    if ents["dino"]["y"] >= GROUND and len(ys) > 1:
        break
    if len(ys) > 40:
        raise AssertionError("never landed")

# mirror the engine's law tick for tick (rise 90, fall 144, dt 0.05)
mvy, my = -36.0, float(GROUND)
mirror = []
for _ in range(40):
    mvy += (90.0 if mvy < 0 else 144.0) * 0.05
    my = min(float(GROUND), my + mvy * 0.05)
    mirror.append(my)
    if my >= GROUND and len(mirror) > 1:
        break

arc_ok = all(abs(a - b) < 1e-9 for a, b in zip(ys, mirror)) and len(ys) == len(mirror)
pin("the arc mirrors the law exactly (rise 90 / fall 144)", arc_ok,
    f"meas={ys[:8]} mir={mirror[:8]}")
apex_h = GROUND - min(ys)
pin("the discrete apex clears six units (7.2 continuous, Euler-sampled)",
    apex_h > 6.0, f"rise={apex_h:.3f}")
rise_t, fall_t = 36.0 / 90.0, math.sqrt(2 * apex_h / 144.0)
pin("the arc bites: the fall from the apex is shorter than the rise",
    fall_t < rise_t, f"rise={rise_t:.3f}s fall={fall_t:.3f}s")

# 2. the grace law: a press kept just above the ground lands as grace!.
# SDK order is tick THEN keys, so the press must be airborne at key
# time: the new discrete fall (apex 6.3, g 144) crosses 2.7 -> 0.9 ->
# landed, so the honest window is gap in [1.0, 2.8] while falling —
# the landing is then 1-2 ticks away and the memory still lives.
while ents["dino"]["y"] < GROUND:
    ents, _ = frame()
ents, f = frame(keys=["space"])            # grounded leap
press_done = False
grace_ents = None
prev_gap = 0.0
for i in range(40):
    ents, f = frame()
    d = ents["dino"]
    gap = GROUND - d["y"]
    falling = gap < prev_gap - 1e-9        # the gap shrinks only on the fall
    prev_gap = gap
    if f.get("win"):
        break                              # dead mid-watch: honest failure
    if not press_done and falling and 1.0 <= gap <= 2.8:
        ents, f2 = frame(keys=["space"])   # the early press
        pin("an airborne press is kept, not lost", f2.get("say") == "kept",
            f"say={f2.get('say')!r} gap={GROUND - ents['dino']['y']:.2f}")
        press_done = True
        continue
    if press_done and f.get("say") == "grace!":
        grace_ents = dict(ents)
        break
pin("the kept press lands as grace!", grace_ents is not None,
    f"last say={f.get('say')!r}")
if grace_ents:
    pin("the grace leap fires from the ground itself",
        grace_ents["dino"]["y"] == GROUND, f"y={grace_ents['dino']['y']}")
    ents, f = frame()
    pin("the dino rises again the very next frame",
        ents["dino"]["y"] < GROUND, f"y={ents['dino']['y']}")

# 3. the memory decays: a press kept high above is honestly forgotten.
while ents["dino"]["y"] < GROUND:
    ents, _ = frame()
ents, f = frame(keys=["space"])            # grounded leap: "up!"
ents, f = frame()
press_done = False
for i in range(40):
    if f.get("win"):
        break
    if not press_done and ents["dino"]["y"] < GROUND - 3.0:
        ents, f2 = frame(keys=["space"])   # kept, high above the ground
        press_done = True
        if f2.get("say") == "kept":
            ents, f = frame()
            continue
    ents, f = frame()
    if ents["dino"]["y"] >= GROUND and press_done:
        break
pin("a decayed press is honestly forgotten (no grace at the landing)",
    f.get("say") == "", f"say={f.get('say')!r}")
land_ents, land_f = ents, f
ents, f2 = frame()
pin("no second chance rises after the memory dies",
    ents["dino"]["y"] == GROUND, f"y={ents['dino']['y']}")

# 4. the dust: the touchdown spoke, and the staircase descends honestly.
d = land_ents["dust"]
pin("the touchdown spoke dust (alpha 0.7 at the feet)",
    d["x"] == 8 and abs(d["alpha"] - 0.7) < 1e-9 and d["y"] == H - 4,
    f"x={d['x']} a={d['alpha']} y={d['y']}")
pin("the first stair (0.56)", abs(ents["dust"]["alpha"] - 0.56) < 1e-9,
    f"a={ents['dust']['alpha']}")
ents, f = frame()
pin("the second stair (0.42)", abs(ents["dust"]["alpha"] - 0.42) < 1e-9,
    f"a={ents['dust']['alpha']}")
faded, steps = False, 0
for i in range(8):
    ents, f = frame()
    steps = i + 1
    if ents["dust"]["alpha"] == 0:
        faded = True
        break
pin("the dust reaches zero within five ticks", faded and steps <= 5,
    f"steps={steps} a={ents['dust']['alpha']}")
pin("the spent dust parks itself", ents["dust"]["x"] == -999,
    f"x={ents['dust']['x']}")

# 5. standing feet raise no dust.
ents, _ = frame()
ents, f = frame()
pin("standing feet are silent",
    ents["dust"]["x"] == -999 and ents["dust"]["alpha"] == 0,
    f"x={ents['dust']['x']} a={ents['dust']['alpha']}")

# 6. r after the fall: nothing kept, no phantom dust, the leap still
# speaks. the death march injects the overlap — hits are the host's gift.
dead = False
for i in range(120):
    ents, f = frame(dt=0.1)
    if f.get("win"):
        dead = True
        break
    for ci in range(6):
        cx = ents.get(f"cactus-{ci}", {}).get("x", -999)
        if cx > -100 and cx < 13 and cx + 3 > 6:
            ents, f = frame(dt=0.1, hits=["dino", f"cactus-{ci}"])
            if f.get("win"):
                dead = True
            break
    if dead:
        break
pin("the desert claims the runner (win banner)", dead)
if dead:
    ents, f = frame(chars="r")
    d = ents["dino"]
    pin("r walks again at 0 m", "0 m" in ents["hud"]["text"],
        ents["hud"]["text"])
    pin("the fresh run keeps nothing and raises no phantom dust",
        d["y"] == GROUND and ents["dust"]["x"] == -999
        and ents["dust"]["alpha"] == 0,
        f"y={d['y']} dust_x={ents['dust']['x']} a={ents['dust']['alpha']}")
    ents, f = frame(keys=["space"])
    pin("the fresh leap still speaks up!", f.get("say") == "up!",
        str(f.get("say")))

print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the grace law holds")
