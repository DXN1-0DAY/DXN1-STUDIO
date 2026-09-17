#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R24 probe: asteroids.js "the bleach wears off" — v3.1.61 fix.
# REAL BUG fixed this round: on.hull-hit set ship.flash = nose.flash = 1
# and the comment claimed "the engine does the fading" — a lie the
# cards/snake rounds buried (the studio keeps the last light a wire
# game sent; nothing decays it). The ship stayed BLEACHED FOREVER.
# The fix: the wire game owns the decay — 3/s in on.tick.
#   - hit frame: flash 1.0 both, "hull hit — 2 left", safe blink armed
#   - staircase: 0.952 / 0.904 at 3/s, dt 0.016 (round-3 law)
#   - the bleach SURVIVES resetShip's blink (it must: resetShip runs
#     after the bleach is set) and is GONE before the blink ends
#   - second hit re-bleaches (the law repeats); fatal hit still bleaches
#   - the fresh game inherits NO scar: 3/s wears it inside 21 ticks
import subprocess, sys, json, os, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")

env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
p = subprocess.Popen(["node", os.path.join(EX, "asteroids.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1,
                     cwd=REPO, env=env)

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

def frame(hits=None):
    send({"t": "tick", "dt": 0.016, "keys": {}, "chars": "", "hits": hits or []})
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

send({"t": "hello", "w": 160, "h": 60})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 7 entities", len(scene["entities"]) == 7,
    str(len(scene["entities"])))

# 1. the first hull hit
ents, f = frame(hits=["ship", "rock0_0"])
pin("hit bleaches the ship (flash 1.0)",
    ents["ship"].get("flash", 0) == 1.0, f"{ents['ship'].get('flash')}")
pin("the flame bleaches too", ents["nose"].get("flash", 0) == 1.0,
    f"{ents['nose'].get('flash')}")
spoken = str(f.get("say") or "")
pin("hull hit spoken, 2 left", "2 left" in spoken, spoken[:60])

# 2. the honest staircase at 3/s
ents, _ = frame()
pin("staircase step 1 (0.952)", abs(ents["ship"].get("flash", 0) - 0.952) < 0.0011,
    f"{ents['ship'].get('flash')}")
ents, _ = frame()
pin("staircase step 2 (0.904)", abs(ents["ship"].get("flash", 0) - 0.904) < 0.0011,
    f"{ents['ship'].get('flash')}")
ents, _ = frame()
pin("nose decays in step", abs(ents["nose"].get("flash", 0) - 0.856) < 0.0011,
    f"{ents['nose'].get('flash')}")

# 3. walk out the blink (2.2 s = 137 ticks): the bleach is long gone
for _ in range(134):
    ents, _ = frame()
pin("blink end: ship visible again", ents["ship"].get("visible", 0) == 1,
    f"visible={ents['ship'].get('visible')}")
pin("bleach fully worn inside the blink", ents["ship"].get("flash", -1) == 0.0,
    f"{ents['ship'].get('flash')}")

# 4. the second hit re-bleaches — the law repeats
ents, f = frame(hits=["ship", "rock0_1"])
pin("second hit bleaches again", ents["ship"].get("flash", 0) == 1.0,
    f"{ents['ship'].get('flash')}")
pin("one life left", "1 left" in str(f.get("say") or ""), str(f.get("say"))[:60])
for _ in range(140):                       # walk out the second blink
    ents, _ = frame()

# 5. the fatal hit: still bleaches, then the fresh game wears clean
ents, f = frame(hits=["ship", "rock0_2"])
pin("fatal hit bleaches the corpse", ents["ship"].get("flash", 0) == 1.0,
    f"{ents['ship'].get('flash')}")
pin("game over banner", "game over" in str(f.get("win") or ""), str(f.get("win"))[:60])
pin("lives back to 3 (rebuild)", "lives 3" in ents["hud"]["text"],
    ents["hud"]["text"])
for _ in range(24):
    ents, _ = frame()
pin("fresh game: no inherited scar", ents["ship"].get("flash", -1) == 0.0,
    f"{ents['ship'].get('flash')}")

p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
