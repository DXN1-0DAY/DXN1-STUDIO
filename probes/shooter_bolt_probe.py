#!/usr/bin/env python3
"""probe for sdk/examples/shooter.py — THE BOLT LEDGER (re-homed v3.1.93).

The R24-era external version died two deaths: absolute paths that only
worked in its birth checkout, and a census pin (3) that predates the
night sky. The law it guards is still real and pinned nowhere else —
what leaves the stage takes its light with it:

  1. the scene carries 15 entities (ship, enemy, hud — plus the
     night's furniture: nine stars and a moon, all still rumors);
  2. one tap = one bolt carrying its own light (glow 2), the muzzle
     speaks (glow 5) and fades down 12/s;
  3. the bolt is DESTROYED off the top — the set forgets it, the
     count returns to 15 (the leak is gone, the stars stay);
  4. three bolts leave the ledger honest (15 again);
  5. an injected shot-enemy hit still pays (SCORE 10), the next
     threat drifts in at alpha 0.15, and the spent bolt is
     forgotten by the ledger too.
"""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.93): rescued from the external scripts dir
# where absolute birth-checkout paths kept it a prisoner of one machine.
# Canonical law pins: probes/*_probe.py, walked by gate 8.
import subprocess, sys, json, os, time, threading, queue

REPO = _HOME
env = dict(os.environ)
env["PYTHONPATH"] = os.path.join(REPO, "sdk")

p = subprocess.Popen(["python3", "-u", os.path.join(REPO, "sdk", "examples", "shooter.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

_q = queue.Queue()
def _pump():
    for ln in p.stdout:
        _q.put(ln)
    _q.put("")
threading.Thread(target=_pump, daemon=True).start()

def read(timeout=6):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            ln = _q.get(timeout=0.1)
        except queue.Empty:
            continue
        if not ln:
            return None
        try:
            return json.loads(ln)
        except Exception:
            continue
    return None

def frame(keys=None, hits=None, dt=0.2):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": "", "hits": hits or []})
    while True:
        f = read()
        if f is None:
            raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

BASE = 15                                   # the night sky lives here now

send({"t": "hello", "w": 100, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin(f"scene has {BASE} entities (the crew plus the night sky)",
    len(scene["entities"]) == BASE, str(len(scene["entities"])))

# 1. one tap: one bolt, carrying its own light; the muzzle speaks
ents, f = frame(keys=["space"])
pin("one tap spawns one bolt", "shot1" in ents, str(sorted(ents)[:8]))
pin("the bolt carries its own light (glow 2)",
    ents.get("shot1", {}).get("glow") == 2,
    f"{ents.get('shot1', {}).get('glow')}")
pin("the muzzle speaks (glow 5)", ents["ship"].get("glow") == 5,
    f"{ents['ship'].get('glow')}")

# 2. the muzzle fades at 12/s (2.4/tick at dt 0.2)
ents, _ = frame()
pin("the muzzle fades (2.6)", abs(ents["ship"].get("glow", 0) - 2.6) < 0.0011,
    f"{ents['ship'].get('glow')}")
ents, _ = frame()
pin("the muzzle fades (0.2)", abs(ents["ship"].get("glow", 0) - 0.2) < 0.0011,
    f"{ents['ship'].get('glow')}")

# 3. the bolt leaves the sky — the set forgets it, the stars stay
# (the bolt rises 2.5 px/s from mid-sky: ~12 s to clear the top)
left = False
for _ in range(80):
    ents, f = frame()
    if "shot1" not in ents:
        left = True
        break
pin("the bolt is destroyed off the top", left, str(sorted(ents)[:8]))
pin(f"the count returns to {BASE} (no leak, the night stays)",
    len(ents) == BASE, str(len(ents)))

# 4. three more bolts — the ledger stays honest
for i in range(3):
    ents, f = frame(keys=["space"])
for _ in range(85):
    ents, f = frame()
    if not any(n.startswith("shot") for n in ents):
        break
pin("three bolts fired, all come home, count honest",
    len(ents) == BASE and not any(n.startswith("shot") for n in ents),
    f"{len(ents)} entities: {sorted(ents)[:8]}")

# 5. an injected hit still pays — and the ledger forgets the spent bolt
ents, _ = frame(keys=["space"])            # fire shot5
ents, f = frame(hits=["shot5", "enemy"])
pin("the next threat drifts in (alpha 0.15)",
    ents["enemy"].get("alpha") == 0.15, f"{ents['enemy'].get('alpha')}")
ents, f = frame()                          # the hud lags one frame (tick
                                           # runs before hits — the R23 law)
pin("the hit pays (score 10)", ents["hud"]["text"] == "SCORE 10",
    ents["hud"]["text"])
for _ in range(85):
    ents, f = frame()
    if not any(n.startswith("shot") for n in ents):
        break
pin("the spent bolt is forgotten by the ledger too",
    len(ents) == BASE and not any(n.startswith("shot") for n in ents),
    f"{len(ents)} entities: {sorted(ents)[:8]}")

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the bolt ledger: what leaves the stage takes")
print("its light with it, the count returns, the night stays put.")
