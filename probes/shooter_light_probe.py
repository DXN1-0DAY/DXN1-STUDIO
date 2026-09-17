#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.92): re-pinned to the current truth and
# walked by gate 8 — a probe the gates never run ages into a liar (the
# drift ledger lives in probes/README.md).
# DS2-R20 probe: shooter.py "the light" — the last undressed gallery
# example, over the real wire (python SDK).
# pins: 3 entities; the FIRST threat drifts in (scene alpha ~0.15,
# full after ~1 s); a fired bolt carries its own halo (glow 2) and
# the muzzle speaks (ship glow 5), fading to dark in ~9 ticks; an
# injected hit honestly destroys the bolt, scores (hud "SCORE 10"),
# teleports the enemy, and re-ghosts it (alpha back to 0.15, rising
# again). Discipline: tick-only, pump thread, one empty tick after a
# key tick (on_tick runs before on_key).
import subprocess, sys, json, os, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
os.environ["PYTHONPATH"] = os.path.join(REPO, "sdk") + ":" + os.environ.get("PYTHONPATH", "")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["python3", "-u", os.path.join(EX, "shooter.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, cwd=EX)

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
        if not ln: return None
        try: return json.loads(ln)
        except Exception: continue
    return None

def frame(keys=None, hits=None):
    send({"t": "tick", "dt": 0.05,
          "keys": {k: True for k in (keys or [])},
          "chars": "", "hits": hits or []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

send({"t": "hello", "w": 100, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 15 entities (the night sky included)", len(scene["entities"]) == 15,
    str([e["name"] for e in scene["entities"]]))
e0 = next(e for e in scene["entities"] if e["name"] == "enemy")
pin("the first threat is born a ghost (alpha ~0.15)",
    abs(e0.get("alpha", 1) - 0.15) < 0.001, str(e0.get("alpha")))

# 1. the drift-in: ~1 s of ticks brings the enemy to full light
for _ in range(20): ents, _ = frame()
pin("the ghost drifts to full light in about a second",
    abs(ents["enemy"].get("alpha", 1) - 1.0) < 0.02,
    str(ents["enemy"].get("alpha")))

# 2. fire: the bolt glows, the muzzle speaks — the frame of the KEY
# tick itself already carries the new world (handlers run before the
# frame is sent); on_tick's decay only bites the NEXT tick
ents, _ = frame(["space"])
pin("the bolt exists and carries its halo (glow 2)",
    "shot1" in ents and ents["shot1"].get("glow") == 2,
    str(ents.get("shot1", {}).get("glow")))
pin("the muzzle speaks (ship glow 5)", ents["ship"].get("glow") == 5,
    str(ents["ship"].get("glow")))
for _ in range(12): ents, _ = frame()
pin("the muzzle fades honestly (glow 0)",
    ents["ship"].get("glow", 0) == 0, str(ents["ship"].get("glow")))

# 3. a real hit: the bolt dies, the enemy re-ghosts; the hud's score
# lags one frame (on_tick writes BEFORE on_hit fires) — so the score
# pin reads the NEXT tick's frame
x_before, y_before = ents["enemy"]["x"], ents["enemy"]["y"]
ents, _ = frame(hits=["shot1", "enemy"])
pin("the hit drinks the bolt (name gone)", "shot1" not in ents)
e2 = ents["enemy"]
pin("the enemy teleports on the hit",
    (e2["x"], e2["y"]) != (x_before, y_before),
    f"{(x_before, y_before)} -> {(e2['x'], e2['y'])}")
pin("the next threat is a ghost again (alpha ~0.15)",
    abs(e2.get("alpha", 1) - 0.15) < 0.001, str(e2.get("alpha")))
ents, _ = frame()
pin("the score speaks (SCORE 10)", ents["hud"].get("text") == "SCORE 10",
    ents["hud"].get("text"))
for _ in range(18): ents, _ = frame()
pin("and it drifts to full light again",
    abs(ents["enemy"].get("alpha", 1) - 1.0) < 0.05,
    str(ents["enemy"].get("alpha")))
p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
