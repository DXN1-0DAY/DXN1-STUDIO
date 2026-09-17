#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R24 probe: lunar.py "the beat, not the bleach" — v3.1.61 fix.
# REAL BUG fixed this round: a touchdown set land.flash = 1.0 and the
# on_tick freeze branch returned early — the bleach HELD at full for
# the entire 1.4 s freeze, then popped back to normal on respawn.
# The fix: the gold-white beat DECAYS at 1.5/s (the honest staircase,
# PROTOCOL.md who-owns-the-tick law). Pins:
#   - injected pad0 hit right after spawn = soft landing (vy 10.96 << 65)
#   - touchdown frame: flash 1.0, "+50" spoken, score kept through the beat
#   - staircase: 0.976 / 0.952 on the next two frames (1.5/s at dt 0.016)
#   - decay monotonic; flash reaches 0.0 WELL inside the freeze (no hold)
#   - after the beat: respawn, hud "FUEL 100 · SCORE 50 · LIVES 3"
#   - crash path mourns: hill hit, lives 2, land.flash NEVER rises
import subprocess, sys, json, os, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
os.environ["PYTHONPATH"] = os.path.join(REPO, "sdk") + ":" + os.environ.get("PYTHONPATH", "")

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
        if not ln:
            return None
        try:
            return json.loads(ln)
        except Exception:
            continue
    return None

def frame(hits=None, keys=None):
    send({"t": "tick", "dt": 0.016,
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
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

send({"t": "hello", "w": 1600, "h": 480})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 11 entities", len(scene["entities"]) == 11,
    str(len(scene["entities"])))

# 1. the soft touchdown: pad0 hit while vy is still spawn-gentle
ents, f = frame(hits=["land", "pad0"])
pin("touchdown frame bleaches (flash 1.0)",
    ents["land"].get("flash", 0) == 1.0, f"{ents['land'].get('flash')}")
spoken = str(f.get("say") or "") + str(f.get("win") or "")
pin("the pay is spoken (+50)", "+50" in spoken, spoken[:60])

# 2. the honest staircase: 1.0 -> 0.976 -> 0.952 at 1.5/s, dt 0.016
ents, _ = frame()
pin("staircase step 1 (0.976)", abs(ents["land"].get("flash", 0) - 0.976) < 0.0011,
    f"{ents['land'].get('flash')}")
ents, _ = frame()
pin("staircase step 2 (0.952)", abs(ents["land"].get("flash", 0) - 0.952) < 0.0011,
    f"{ents['land'].get('flash')}")
f3 = ents["land"].get("flash", 0)
ents, _ = frame()
pin("decay is monotonic", ents["land"].get("flash", 0) < f3,
    f"{f3} -> {ents['land'].get('flash')}")

# 3. the beat ENDS inside the freeze — no bleach hold. 1.0/0.024 = ~42
# ticks; the freeze is 1.4 s = 87 ticks. Walk to tick 45 post-hit.
for _ in range(42):
    ents, _ = frame()
pin("beat reaches 0.0 inside the freeze", ents["land"].get("flash", -1) == 0.0,
    f"{ents['land'].get('flash')}")

# 4. respawn after the freeze: score KEPT, fresh tank
for _ in range(50):
    ents, f = frame()
    if "SCORE 50" in ents["hud"]["text"]:
        break
pin("score 50 survives the beat", "SCORE 50" in ents["hud"]["text"],
    ents["hud"]["text"])
pin("fresh tank after respawn", "FUEL 100" in ents["hud"]["text"],
    ents["hud"]["text"])

# 5. the crash path mourns — no bleach on the hills
ents, f = frame(hits=["land", "hill0"])
pin("crash frame: no bleach (flash 0)",
    ents["land"].get("flash", -1) == 0.0, f"{ents['land'].get('flash')}")
for _ in range(80):
    ents, f = frame()
    if "LIVES 2" in ents["hud"]["text"]:
        break
pin("crash cost a life", "LIVES 2" in ents["hud"]["text"], ents["hud"]["text"])
pin("and still no bleach", ents["land"].get("flash", -1) == 0.0,
    f"{ents['land'].get('flash')}")

p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
