#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R19 probe: asteroids.js "the radar field" — real wire conformance.
# pins: 7 entities; the fresh ring DRIFTS IN (first-tick alphas ~ 0,
# full after 1.5 s); the radar law (alpha = 1 - 0.6*far, far band
# 30..100 px from the hull) holds for every rock; the closest rock is
# the brightest; the thrust flame GLOWS (4) while burning and goes
# dark after; a shot dissolves over its last quarter second (alpha
# steps ~0.2/tick) and then the name is honestly gone.
# discipline inherited: on_tick runs before on_key → one empty tick
# after every key tick; drain the stdout queue between sections.
import json, subprocess, sys, os, math

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

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "asteroids.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

w = Wire(p)

def send(o):
    w.send(o)

def read(timeout=4.0):
    return w.read(timeout)

def frame(keys=None):
    w.send({"t": "tick", "dt": 0.05,
            "keys": {k: True for k in (keys or [])},
            "chars": "", "hits": []})
    while True:
        f = w.read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

send({"t": "hello", "w": 120, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
names = [e["name"] for e in scene["entities"]]
pin("scene has 7 entities", len(names) == 7, str(names))

def law(shipx, shipy, rock):
    dx = rock["x"] - (shipx + 4); dy = rock["y"] - (shipy + 5)
    d = math.sqrt(dx * dx + dy * dy)
    far = max(0.0, min(1.0, (d - 30) / 70))
    return (1 - 0.6 * far), d

# 1. the ring drifts in — first tick, born = 0.05/1.5, alphas near zero
ents, _ = frame()
rocks = {n: ents[n] for n in ents if n.startswith("rock")}
pin("four rocks stand at the corners", len(rocks) == 4, str(list(rocks)))
pin("first tick: the ring is ghostly (all alphas < 0.1)",
    all(rocks[n].get("alpha", 1) < 0.1 for n in rocks),
    str({n: round(rocks[n].get("alpha", -1), 3) for n in rocks}))

# 2. after 2 s the ring has fully drifted in — the radar law holds
for _ in range(39): ents, _ = frame()
rocks = {n: ents[n] for n in ents if n.startswith("rock")}
ship = ents["ship"]
ok_law, worst = True, ""
for n in rocks:
    want, d = law(ship["x"], ship["y"], rocks[n])
    got = rocks[n].get("alpha", -1)
    if abs(got - want) > 0.03:
        ok_law = False; worst += f"{n}: got {got:.3f} want {want:.3f} d={d:.0f}; "
pin("radar law holds for every rock (|a - law| < 0.03)", ok_law, worst)
# (v3.1.91: the old pin `closest == brightest` flaked — the four
#  corner rocks come in EQUIDISTANT PAIRS, and min()/max() break a
#  float tie on opposite sides. v3.1.97: its repair — "brightest
#  within 2px of closest" — flaked the OTHER way, because the ring's
#  spawn jitter is honest randomness (Math.random, unseeded) and two
#  rocks inside the 30px burn band SATURATE at the same alpha; max()
#  then picks an arbitrary rock and the +2px band is layout luck.
#  The law's honest, layout-proof content runs the other direction:
#  alpha is monotone in distance (far = clamp((d-30)/70) never
#  decreases as d grows, every rock shares the one ring fade), so
#  THE CLOSEST ROCK ALWAYS WEARS THE BRIGHTEST ALPHA — under every
#  layout, ties included. That is the radar law read directly.)
d_of = {n: law(ship["x"], ship["y"], rocks[n])[1] for n in rocks}
closest = min(rocks, key=lambda n: d_of[n])
top = max(rocks[n].get("alpha", -1) for n in rocks)
pin("the closest rock wears the brightest alpha (ties allowed)",
    rocks[closest].get("alpha", -1) >= top - 1e-9,
    f"closest {closest} at d={d_of[closest]:.1f} "
    f"alpha={rocks[closest].get('alpha', -1):.3f}, max alpha={top:.3f}")

# 3. the flame glows while burning, then goes dark: born WHOLE (glow
#    4) the very key frame, then the burn's own staircase wears it —
#    one dt 0.05 tick later the honest walk reads 4 * 0.07/0.12
key_ents, _ = frame(["jump"])   # the key phase patches this same frame
pin("the key frame lights the flame whole (glow 4)",
    key_ents["nose"].get("glow") == 4, str(key_ents["nose"].get("glow")))
ents, _ = frame()               # one tick of burn spent (0.12 -> 0.07)
pin("the flame wears the burn's own staircase (glow 2.333)",
    abs(ents["nose"].get("glow", 0) - 4 * 0.07 / 0.12) < 1e-6,
    str(ents["nose"].get("glow")))
for _ in range(5): ents, _ = frame()
pin("burn ends, the flame goes dark",
    ents["nose"].get("glow", 0) == 0 and ents["nose"].get("visible", 1) == 0,
    f"glow={ents['nose'].get('glow')} vis={ents['nose'].get('visible')}")

# 4. a shot dissolves over its last quarter second, then is gone
ents, _ = frame(["space"])
ents, _ = frame()
bul = [n for n in ents if n.startswith("bul")]
pin("a bullet exists after firing", len(bul) == 1, str(bul))
seq = []
gone = False
for _ in range(22):                       # 0.9 s life at dt 0.05 = 18 ticks
    ents, _ = frame()
    live = [n for n in ents if n.startswith("bul")]
    if not live: gone = True; break
    seq.append(ents[live[0]].get("alpha", 1))
pin("shot holds full light, then dissolves (alpha steps down)",
    len(seq) >= 3 and all(seq[i] >= seq[i + 1] - 1e-9 for i in range(len(seq) - 1))
    and seq[-1] < 0.9,
    f"seq={[round(a, 3) for a in seq]}")
pin("last seen alpha is inside the dissolve window (< 0.3)",
    seq and seq[-1] < 0.3, f"{seq[-1] if seq else 'none'}")
pin("the expired bullet's name is honestly gone", gone)
p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
