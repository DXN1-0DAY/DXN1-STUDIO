#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R21 probe: windmill.py "the dusk law" — the day is measured in
# turns. pins: 13 entities (no new ones — the sky the mill already
# had); the sun's alpha mirrors the cosine law (1.0 at noon, 0.45 at
# the deepest nightfall, a degree of wind is a degree of day, a full
# day per 720 degrees); the sweep never breaks its banks; the clouds
# wear the dusk at a third of its depth; the sun glows 4 by day and
# goes dark past dusk 0.4; the hud names the hour (noon, dusk,
# nightfall); holding the wind HOLDS the sun where it stands; and
# the day cycles — the sun returns to full strength a full turn of
# the day later.
import json, subprocess, sys, os, math

EX = _os.path.join(_HOME, "sdk", "examples")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

env = dict(os.environ)
env["PYTHONPATH"] = _os.path.join(_HOME, "sdk")
p = subprocess.Popen(["python3", f"{EX}/windmill.py"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def read(timeout=4.0):
    import select
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r: return None
    line = p.stdout.readline()
    if not line: return None
    try: return json.loads(line)
    except Exception: return None

def frame(keys=None, chars="", dt=0.05):
    send({"t": "tick", "dt": dt, "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

# the mirror: speed starts 90; daydeg += speed*dt per turning tick
speed = 90.0
daydeg = 0.0

def mirror_step():
    global daydeg
    daydeg = (daydeg + speed * 0.05) % 720.0

def dusk(d):
    return 0.5 - 0.5 * math.cos(math.radians(d))

send({"t": "hello", "w": 120, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents = {e["name"]: e for e in scene["entities"]}
pin("scene has 13 entities (no new ones)", len(ents) == 13, str(len(ents)))

# 1. the law: sun alpha mirrors 1 - 0.55*dusk(daydeg), tick for tick.
worst = 0.0
sun_ok = cloud_ok = banks_ok = glow_ok = True
hud_phases = set()
for k in range(1, 161):                    # two full days
    ents, f = frame()
    mirror_step()
    dd = dusk(daydeg)
    a = ents["sun"].get("alpha")
    if a is None:
        sun_ok = False; banks_ok = False; break
    worst = max(worst, abs(a - (1.0 - 0.55 * dd)))
    if worst > 1e-6:
        sun_ok = False
    if not (0.45 - 1e-6 <= a <= 1.0 + 1e-6):
        banks_ok = False
    ca = ents["cloud-a"].get("alpha")
    if ca is None or abs(ca - (1.0 - 0.35 * dd)) > 1e-6:
        cloud_ok = False
    g = ents["sun"].get("glow", 0)
    if (dd < 0.4 and g != 4) or (dd >= 0.4 and g != 0):
        glow_ok = False
    hud_phases.add(ents["hud"]["text"])
pin("the sun's alpha mirrors the dusk law (worst err %.1e)" % worst, sun_ok,
    f"worst={worst}")
pin("the sweep never breaks its banks (0.45..1.0)", banks_ok)
pin("the clouds wear the dusk at a third of its depth", cloud_ok)
pin("the sun glows by day and goes dark past dusk 0.4", glow_ok)

# 2. the hud names the hour.
noon = any("noon" in h for h in hud_phases)
duskw = any("· dusk" in h or "dusk" in h and "nightfall" not in h for h in hud_phases)
night = any("nightfall" in h for h in hud_phases)
pin("the hud speaks noon", noon)
pin("the hud speaks dusk", duskw)
pin("the hud speaks nightfall", night)

# 3. holding the wind holds the sun where it stands.
# e1's tick still turns the day one last time (keys fire after the
# tick), so the frozen truth is e1's own alpha.
e1, _ = frame(keys=["space"])              # hold the wind
frozen_a = e1["sun"]["alpha"]
e2, _ = frame()
e3, _ = frame()
pin("the held wind holds the sun (alpha frozen)",
    e2["sun"]["alpha"] == frozen_a and e3["sun"]["alpha"] == frozen_a,
    f"{frozen_a} -> {e2['sun']['alpha']} -> {e3['sun']['alpha']}")
pin("the hud names it HELD while frozen", "HELD" in e3["hud"]["text"],
    e3["hud"]["text"])
e4, _ = frame(keys=["space"])              # release: the day turns again
e5, _ = frame()
pin("the released wind turns the day again", e5["sun"]["alpha"] != frozen_a,
    f"{frozen_a} -> {e5['sun']['alpha']}")

# 4. the hud answers the wind keys (the old law, still true).
e6, _ = frame(keys=["right"])
pin("right hastens the wind (120 on the hud)", "120" in e6["hud"]["text"],
    e6["hud"]["text"])

print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the day is measured in turns")
