#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R24 probe: flappy.py "the ghost, the glow, and the hop that
# finally flies" — v3.1.61 fix. TWO REAL BUGS this round:
# (1) the flash-forever class: die() set bird.flash = 1.0 and the dead
#     branch returned early — the bleach HELD forever until restart.
#     Fix: the dead bleach wears at 3/s, the bird settles a 0.5 ghost.
# (2) the playability lie: LIFT 2.6 hopped 21px in a 6px window — the
#     apex plateau is 12 ticks for ANY lift, the pipe crossing takes
#     30, so flappy could NEVER score; the pass-glow was dead code.
#     Fix: LIFT 1.1 bounces a 3.8px arc that fits the window.
# Pins: the probe PLAYS a clean pass (SCORE 1, glow 8.0); glow stairs
#   7.7/7.4 at 6/s; death frame flash 1.0 alpha 1.0; dead stairs
#   0.85/0.925 then 0.7/0.85; the bleach ENDS into a 0.5 ghost;
#   restart restores alpha 1 and re-wears the pipes.
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

def frame(keys=False):
    send({"t": "tick", "dt": 0.05,
          "keys": {"space": True} if keys else {},
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
pin("scene has 11 entities (sky + moon joined)", len(scene["entities"]) == 11,
    str(len(scene["entities"])))

# 1. the flight that PLAYS: bang-bang down the seeded sky (seed 7).
# tick runs before keys, so a flap in packet N bites in tick N+1 (the
# R23 law). vy is estimated from consecutive frames; the flap line sits
# at gap-center + 2.2 so the whole 3.8px bounce arc stays inside the
# 6px window (apex >= h+0.16, floor <= h+5.2).
# the flight state machine: step(flap) advances one tick; the bang-bang
# keeps flying across SECTIONS (the bird must stay alive while the glow
# staircase is walked). tick runs before keys, so a flap in packet N
# bites in tick N+1 (the R23 law). vy is estimated from consecutive
# frames; the flap line sits at gap-center + 2.2 so the whole 3.8px
# bounce arc stays inside the 6px window (apex >= h+0.16, floor <= h+5.2).
state = {"prev_y": None, "flap": False}

def step(keep_flying=True):
    ents, f = frame(keys=state["flap"] if keep_flying else False)
    y = ents["bird"]["y"]
    vy = (y - state["prev_y"]) if state["prev_y"] is not None else 0.0
    state["prev_y"] = y
    if keep_flying and ents["bird"].get("flash", 0) == 0:
        nxt = None
        for j in range(3):
            x = ents[f"ptop{j}"]["x"]
            if x + 6 >= 16 and (nxt is None or x < ents[f"ptop{nxt}"]["x"]):
                nxt = j
        if nxt is None:
            nxt = 0
        target = ents[f"ptop{nxt}"]["h"] + 3.0       # gap center (bird top)
        state["flap"] = (y + vy + 0.16 > target + 2.2)
    return ents, f

for i in range(900):
    ents, f = step()
    if ents["bird"].get("flash", 0) > 0:
        break                                  # died mid-flight — the sky won
    if ents["hud"]["text"] == "SCORE 1":
        break
pin("the probe PLAYS a clean pass (SCORE 1)", ents["hud"]["text"] == "SCORE 1",
    ents["hud"]["text"])
pin("the pass makes the bird GLOW (8.0)",
    ents["bird"].get("glow", 0) == 8.0, f"{ents['bird'].get('glow')}")

# 2. the honest glow staircase, WITNESSED MID-FLIGHT: 6/s at dt 0.05
# = 0.3/tick. The birth-tick law puts the whole 8.0 on the pass frame.
ents, _ = step()
pin("glow step 1 (7.7)", abs(ents["bird"].get("glow", 0) - 7.7) < 0.0011,
    f"{ents['bird'].get('glow')}")
ents, _ = step()
pin("glow step 2 (7.4)", abs(ents["bird"].get("glow", 0) - 7.4) < 0.0011,
    f"{ents['bird'].get('glow')}")
for _ in range(30):
    ents, f = step()
    if ents["bird"].get("glow", -1) == 0.0 and ents["bird"].get("flash", 0) == 0.0:
        break
pin("glow worn out in ~27 ticks, still flying", ents["bird"].get("glow", -1) == 0.0,
    f"{ents['bird'].get('glow')}")
pin("and the bird still lives", ents["bird"].get("flash", 0) == 0.0,
    f"{ents['bird'].get('flash')}")

# 3. stop flapping — the fall, the bleach, the honest wear
for _ in range(40):
    ents, f = step(keep_flying=False)
    if ents["bird"].get("flash", 0) > 0:
        break
pin("death bleaches (flash 1.0)", ents["bird"].get("flash", 0) == 1.0,
    f"{ents['bird'].get('flash')}")
pin("death frame: alpha still full (absent = default 1.0)",
    ents["bird"].get("alpha", 1.0) == 1.0,
    f"{ents['bird'].get('alpha')}")

# 4. the dead staircase: flash 3/s, alpha wears with it
ents, _ = frame()
pin("dead flash step 1 (0.85)", abs(ents["bird"].get("flash", 0) - 0.85) < 0.0011,
    f"{ents['bird'].get('flash')}")
pin("dead alpha wears (0.925)", abs(ents["bird"].get("alpha", 0) - 0.925) < 0.0011,
    f"{ents['bird'].get('alpha')}")
ents, _ = frame()
pin("dead flash step 2 (0.7)", abs(ents["bird"].get("flash", 0) - 0.7) < 0.0011,
    f"{ents['bird'].get('flash')}")
for _ in range(20):
    ents, _ = frame()
pin("the bleach ENDS (0.0)", ents["bird"].get("flash", -1) == 0.0,
    f"{ents['bird'].get('flash')}")
pin("the bird rests a 0.5 ghost", ents["bird"].get("alpha", 0) == 0.5,
    f"{ents['bird'].get('alpha')}")

# 5. restart: the ghost flies again
ents, _ = frame(keys=True)
pin("restart: scars cleaned", ents["bird"].get("flash", -1) == 0.0,
    f"{ents['bird'].get('flash')}")
pin("restart: alpha restored", ents["bird"].get("alpha", 0) == 1.0,
    f"{ents['bird'].get('alpha')}")
ents, _ = frame()
pin("restart: pipes re-worn from the horizon",
    abs(ents["ptop0"].get("alpha", 0) - 0.547) < 0.01, f"{ents['ptop0'].get('alpha')}")

p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
