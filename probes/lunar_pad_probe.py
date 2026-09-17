#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R25 probe: lunar.py "the halos breathe" — v3.1.65.
# The pads wear halos sized to their pay; now they BREATHE on one
# shared clock (the snake meal's 4-rad sine), two amplitudes — the
# summit's halo breathes taller because its pay is richer. Born at
# the breath's TOP (no pop at spawn). A touchdown makes the pleased
# pad FLARE (+2 bloom) that wears at the house's 3/s even while the
# freeze holds the world. Pins:
#   - scene 11; pad0 glow 3, pad1 glow 4 at birth (the halo IS the pay)
#   - the flare: a spawn-gentle touchdown jumps the halo +2 over the
#     breath measured ONE FRAME BEFORE the hit; it wears monotonically
#     inside the freeze and empties back into the breath band
#   - the breath: glows within [0.5, 1.0] x base over a full period
#   - periodic: glow(t) == glow(t + pi/2 s) — the 4-rad clock, exact
#   - one clock, two amplitudes: glow/3 == glow/4 every sample
#   - the summit breathes taller: its swing exceeds the valley's
import subprocess, sys, json, os, time, threading, queue, math

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
birth = {e["name"]: e for e in scene["entities"]}
pin("the halo IS the pay at birth (3 and 4)",
    birth["pad0"].get("glow") == 3 and birth["pad1"].get("glow") == 4,
    f"{birth['pad0'].get('glow')}/{birth['pad1'].get('glow')}")

# ---- the flare FIRST, while the lander is spawn-gentle (vy ~10 << 65)
ents, _ = frame()
pre0 = ents["pad0"].get("glow", 0)
ents, f = frame(hits=["land", "pad0"])
spoken = str(f.get("say") or "") + str(f.get("win") or "")
pin("touchdown pays (+50 spoken)", "+50" in spoken, spoken[:60])
flare0 = ents["pad0"].get("glow", 0)
pin("the pleased pad flares (+2 over the breath)",
    flare0 >= pre0 + 1.9, f"pre {pre0} -> {flare0}")
prev = flare0
wore = True
for _ in range(60):                      # the flare wears ~3/s inside the freeze
    ents, _ = frame()
    g = ents["pad0"].get("glow", 0)
    if g > prev + 1e-9:
        wore = False
    prev = g
pin("the flare wears monotonically inside the freeze", wore, f"ended {prev}")
pin("the flare empties (back inside the breath band)",
    prev <= 3.0 + 0.01, f"{prev}")

# ---- the freeze ends, the lander respawns; now read the breath
for _ in range(40):                      # walk out the rest of the freeze
    ents, _ = frame()
s0, s1 = [], []
for i in range(99):                      # one full period = pi/2 s ~ 98 ticks
    ents, _ = frame()
    s0.append(ents["pad0"].get("glow", 0))
    s1.append(ents["pad1"].get("glow", 0))
pin("valley breathes in [1.5, 3.0]",
    min(s0) >= 1.5 - 0.01 and max(s0) <= 3.0 + 0.01, f"[{min(s0)}, {max(s0)}]")
pin("summit breathes in [2.0, 4.0]",
    min(s1) >= 2.0 - 0.01 and max(s1) <= 4.0 + 0.01, f"[{min(s1)}, {max(s1)}]")

# ---- one clock, two amplitudes: the normalized breaths agree
norm = [a / 3.0 - b / 4.0 for a, b in zip(s0, s1)]
pin("one shared clock (normalized breaths agree)",
    max(abs(x) for x in norm) < 0.02, f"max drift {max(abs(x) for x in norm):.4f}")

# ---- the summit breathes taller: swing 2.0 vs 1.5
pin("the summit's swing is taller (2.0 > 1.5)",
    (max(s1) - min(s1)) > (max(s0) - min(s0)) + 0.3,
    f"{max(s1) - min(s1):.3f} vs {max(s0) - min(s0):.3f}")

# ---- periodic: glow now == glow one period (pi/2 s = 98.2 ticks) later
ents_a, _ = frame()
a0, a1 = ents_a["pad0"].get("glow"), ents_a["pad1"].get("glow")
for _ in range(98):
    ents_b, _ = frame()
pin("the clock is exact (glow repeats after pi/2 s)",
    abs(ents_b["pad0"].get("glow") - a0) < 0.05
    and abs(ents_b["pad1"].get("glow") - a1) < 0.05,
    f"{a0}->{ents_b['pad0'].get('glow')} / {a1}->{ents_b['pad1'].get('glow')}")

print()
if fails:
    print(f"PROBE RED: {fails}"); sys.exit(2)
print("PROBE GREEN — the halos breathe")
