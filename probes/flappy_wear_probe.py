#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.92): re-pinned to the current truth and
# walked by gate 8 — a probe the gates never run ages into a liar (the
# drift ledger lives in probes/README.md).
# DS2-R18 probe: flappy.py "the worn pipes" — real wire conformance.
# pins: 9 entities; pipe alpha wears with distance (near pipe > mid >
# far, far clamps at 0.35); living ticks push pipes closer so alpha
# RISES; death bleaches the bird (flash==1.0) and says "game over";
# restart resets the wear AND the scars (flash back to 0).
# lessons from the cards probe, applied: tick-only events, pump thread,
# and one empty tick after a key tick (on_tick runs before on_key).
import subprocess, sys, json, os, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
os.environ["PYTHONPATH"] = os.path.join(REPO, "sdk") + ":" + os.environ.get("PYTHONPATH", "")

p = subprocess.Popen(["python3", "-u", os.path.join(EX, "flappy.py")],
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
        if not ln:
            return None
        try:
            return json.loads(ln)
        except Exception:
            continue
    return None

def frame(keys=None):
    send({"t": "tick", "dt": 0.05,
          "keys": {k: True for k in (keys or [])},
          "chars": "", "hits": []})
    while True:
        f = read()
        if f is None:
            raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

send({"t": "hello", "w": 100, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 11 entities", len(scene["entities"]) == 11,
    str(len(scene["entities"])))

# 1. after one tick, the three pipes wear in decreasing alpha
ents, _ = frame()
a0, a1, a2 = (ents[f"ptop{i}"].get("alpha") for i in range(3))
pin("near pipe wears in (a0 ~ 0.547)", abs(a0 - 0.547) < 0.01, f"{a0}")
pin("mid pipe fainter (a1 ~ 0.445)", abs(a1 - 0.445) < 0.01, f"{a1}")
pin("far pipe at the 0.35 floor", abs(a2 - 0.35) < 0.001, f"{a2}")
pin("wear is monotonic a0>a1>a2", a0 > a1 > a2)

# 2. living ticks push pipes closer — alpha must RISE
x_start = ents["ptop0"]["x"]
for _ in range(20):
    ents, f = frame()
    if ents["bird"].get("flash", 0) > 0:
        break                                # the bird hit the floor
a_dead = ents["ptop0"]["alpha"]
pin("dead: pipes closer, alpha rose", a_dead > 0.547 + 0.01, f"{a_dead} vs 0.547")
pin("death bleaches the bird (flash 1.0)",
    ents["bird"].get("flash", 0) == 1.0, f"{ents['bird'].get('flash')}")
pin("death says game over", "game over" in (f.get("win") or ""), str(f.get("win")))

# 3. restart: wear resets AND scars clean
ents, _ = frame(["space"])
pin("restart cleans the bird's scars", ents["bird"].get("flash", 0) == 0,
    f"{ents['bird'].get('flash')}")
ents, _ = frame()                            # one tick so on_tick re-wears
pin("restart resets pipe wear", abs(ents["ptop0"]["alpha"] - 0.547) < 0.01,
    f"{ents['ptop0']['alpha']}")

p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
