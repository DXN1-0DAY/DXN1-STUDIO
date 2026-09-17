#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R20 probe: lunar.py "the last light" — over the real wire
# (python SDK).
# pins: 11 entities; the pads wear pay-sized halos (3 and 4); the
# flame RIDES the lander (x+4, y+16 — it used to burn at the spawn
# point forever, a latent bug) and GLOWS while burning, then goes
# dark; a soft touchdown (injected pair) pays, says, BLEACHES the
# lander (flash 1.0) and freezes the world; a fresh tank earns a
# fresh lander (respawn restores the birth state).
import subprocess, sys, json, os, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
os.environ["PYTHONPATH"] = os.path.join(REPO, "sdk") + ":" + os.environ.get("PYTHONPATH", "")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["python3", "-u", os.path.join(EX, "lunar.py")],
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
pin("scene has 11 entities", len(scene["entities"]) == 11,
    str(len(scene["entities"])))
sc = {e["name"]: e for e in scene["entities"]}
pin("the valley pad's halo is its pay (glow 3)", sc["pad0"].get("glow") == 3,
    str(sc["pad0"].get("glow")))
pin("the summit pad's halo is richer (glow 4)", sc["pad1"].get("glow") == 4,
    str(sc["pad1"].get("glow")))
pin("the flame sleeps at spawn", not sc["flame"].get("visible", 1))

# 1. a burn lights the flame UNDER the lander, and it glows
ents, _ = frame(keys=["space"])
fl, la = ents["flame"], ents["land"]
pin("the burn lights the flame (visible, glow 4)",
    fl.get("visible", 0) == 1 and fl.get("glow") == 4,
    f"vis={fl.get('visible')} glow={fl.get('glow')}")
pin("the flame RIDES the lander (x+4, y+16)",
    abs(fl["x"] - (la["x"] + 4)) < 0.01 and abs(fl["y"] - (la["y"] + 16)) < 0.01,
    f"flame=({fl['x']},{fl['y']}) land=({la['x']},{la['y']})")
for _ in range(4): ents, _ = frame()
pin("the burn ends, the flame goes dark",
    ents["flame"].get("visible", 0) == 0 and ents["flame"].get("glow", 0) == 0,
    f"vis={ents['flame'].get('visible')} glow={ents['flame'].get('glow')}")

# 2. a soft touchdown: pays, says, bleaches, freezes — the say word
# rides the HIT tick's own frame (a transient line: one frame only)
ents, fh = frame(hits=["land", "pad0"])
pin("the touchdown's word rides the say field",
    "touchdown" in (fh.get("say") or ""), str(fh.get("say")))
ents2, _ = frame()
# the honest staircase (v3.1.61): one dt-0.05 frame after the hit the
# bleach has already worn 1.0 -> 0.925 (1.5/s) — the beat probe pins
# the exact staircase at dt 0.016; this pin accepts the worn value
pin("the lander bleaches gold-white (1.0 worn to 0.925 at 1.5/s)",
    ents2["land"].get("flash") == 0.925, str(ents2["land"].get("flash")))
pin("the world holds its breath (vx = vy = 0)",
    ents2["land"]["vx"] == 0 and ents2["land"]["vy"] == 0,
    f"vx={ents2['land']['vx']} vy={ents2['land']['vy']}")

# 3. the freeze beat ends: a fresh lander, a clean tank
for _ in range(28): ents, _ = frame()
pin("the respawn restores the birth state (flash 0, tank wide)",
    ents["land"].get("flash", 0) == 0 and ents["fuelbar"]["w"] == 28,
    f"flash={ents['land'].get('flash')} w={ents['fuelbar']['w']}")
p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
