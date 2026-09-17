#!/usr/bin/env python3
"""probe for sdk/examples/shooter.py — THE OWL HUNTS THE FLASH
(v3.1.80). The void's third threat class, night only, pinned on the
real wire:

  1. the scene carries FIFTEEN entities — the owl parked off-screen,
     born with the drift's 0.15 and its own halo (glow 2);
  2. DAYLIGHT SILENCE: shots fired before the night is full draw
     NOTHING from "the night owl" — the stream is untouched by day;
  3. THE LAUNCH LAW, draw for draw: at full night each parked-state
     shot draws randint(1, 3); the first 1 wakes the owl and takes
     two more draws — an edge (random() < 0.5) and a bolt row
     (randint(4, 10)). The probe replicates the stream exactly and
     the owl must launch on EXACTLY that shot, at EXACTLY that edge
     and row, alpha 0.15 (the drift announces it);
  4. the drift is honest: one tick later the owl's alpha is
     0.15 + 0.05/0.9 (the radar-field law);
  5. THE FEED: a bolt that touches the shadow dies by it — the del
     carries the bolt, the owl leaves fed (parked), the say speaks
     "the owl takes your shot", and the score pays NOTHING;
  6. THE STREAM ADVANCES: the next full-night parked-state shots
     take the NEXT draws, and the second launch is again exactly
     what the stream deals.
"""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, time, threading, queue, random

REPO = _HOME
W_W, H_W = 120, 44                       # the probe's world (gate 6's size)

env = dict(os.environ)
env["PYTHONPATH"] = os.path.join(REPO, "sdk")

def child():
    p = subprocess.Popen(
        ["python3", os.path.join(REPO, "sdk", "examples", "shooter.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    _q = queue.Queue()
    _raw = []
    def _pump():
        for ln in p.stdout:
            _raw.append(ln.rstrip()[:160])
            _q.put(ln)
    threading.Thread(target=_pump, daemon=True).start()

    def send(o):
        p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

    def read(timeout=8):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                ln = _q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                return json.loads(ln)
            except Exception:
                continue
        return ("RAW", list(_raw[-5:]))     # never silently None

    def tick(keys=None, hits=None, dt=0.05, chars=""):
        send({"t": "tick", "dt": dt,
              "keys": {k: True for k in (keys or [])},
              "chars": chars, "hits": hits or []})
        while True:
            pkt = read()
            if not isinstance(pkt, dict):
                raise AssertionError(f"child stalled: {str(pkt)[:200]}")
            if pkt.get("t") == "frame":
                return {e["name"]: e for e in pkt["set"]}, pkt
    return p, send, read, tick

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p, send, read, tick = child()
send({"t": "hello", "w": W_W, "h": H_W})
scene = read()
assert isinstance(scene, dict) and scene.get("t") == "scene", \
    f"no scene: {str(scene)[:300]}"
ents = {e["name"]: e for e in scene["entities"]}
names = sorted(ents)
pin("the scene carries fifteen entities — the night's owl included",
    names == sorted(["enemy", "hud", "moon", "owl", "ship", "twin"] +
                    [f"star{i}" for i in range(9)]), str(names))
pin("the owl is born parked, a ghost with its own halo",
    ents["owl"].get("x") == -999 and
    abs(ents["owl"].get("alpha", 0) - 0.15) < 1e-9 and
    ents["owl"].get("glow", 0) == 2,
    f"x={ents['owl'].get('x')} a={ents['owl'].get('alpha')} "
    f"g={ents['owl'].get('glow')}")

# ---------- daylight silence: the stream is untouched by day ----------
for i in range(1, 4):
    tick(["space"])
    tick(hits=[f"shot{i}", "enemy" if i % 2 else "twin"])
    tick([])
e3, _ = tick([])
pin("three daylit kills and the owl never stirs (no draws by day)",
    e3["owl"].get("x") == -999,
    f"x={e3['owl'].get('x')}")

# ---------- walk to full night: kills 4..10, then the fade ----------
for i in range(4, 11):
    tick(["space"])
    tick(hits=[f"shot{i}", "enemy" if i % 2 else "twin"])
    tick([])
for _ in range(40):                      # the fade's two honest seconds
    tick([])

# ---------- the replicated stream: draws until the first wake ----------
OW = random.Random("the night owl")
k = 0
while True:
    k += 1
    if OW.randint(1, 3) == 1:
        from_left = OW.random() < 0.5
        row = OW.randint(4, 10)
        break
assert k <= 12, f"unlucky stream (k={k}) — rerun"

owl_frame = None
for i in range(1, k + 1):
    entsF, _ = tick(["space"])           # full-night shot 10+i
    if i == k:
        owl_frame = entsF                # the wake rides the fire frame
exp_x = -12.0 if from_left else W_W + 2.0
pin(f"the owl launches on EXACTLY full-night shot {k}, at exactly "
    "the stream's edge and row",
    owl_frame is not None and owl_frame["owl"].get("x") == exp_x and
    owl_frame["owl"].get("y") == float(row) and
    abs(owl_frame["owl"].get("alpha", 0) - 0.15) < 1e-9,
    f"got=({owl_frame['owl'].get('x')},{owl_frame['owl'].get('y')},"
    f"a={owl_frame['owl'].get('alpha')}) exp=({exp_x},{row},0.15)")

entsD, _ = tick([])
pin("the drift announces it: one tick of the radar-field law",
    abs(entsD["owl"].get("alpha", 0) - (0.15 + 0.05 / 0.9)) < 1e-9,
    f"a={entsD['owl'].get('alpha')}")

# ---------- the feed: a bolt dies by the shadow ----------
hud_before = None
eB, _ = tick([])
hud_before = eB["hud"].get("text")
tick(["space"])                          # shot 10+k+1 flies — no draw,
n_feed = 10 + k + 1                      #   the owl is in the sky
entsFeed, pktFeed = tick(hits=[f"shot{n_feed}", "owl"])
pin("a bolt that touches the shadow dies by it (the del carries it)",
    f"shot{n_feed}" in (pktFeed.get("del") or []),
    str(pktFeed.get("del")))
pin("the owl leaves fed",
    entsFeed["owl"].get("x") == -999,
    f"x={entsFeed['owl'].get('x')}")
pin("the night's due is said plainly",
    pktFeed.get("say", "") == "the owl takes your shot",
    repr(pktFeed.get("say")))
eA, _ = tick([])
pin("and the score pays NOTHING (greed was the only stake)",
    eA["hud"].get("text") == hud_before,
    f"{hud_before!r} -> {eA['hud'].get('text')!r}")

# ---------- the stream advances: the second wake ----------
k2 = 0
while True:
    k2 += 1
    if OW.randint(1, 3) == 1:
        from_left2 = OW.random() < 0.5
        row2 = OW.randint(4, 10)
        break
assert k2 <= 20, f"unlucky second stream (k2={k2}) — rerun"

owl_frame2 = None
for i in range(1, k2 + 1):
    entsF2, _ = tick(["space"])
    if i == k2:
        owl_frame2 = entsF2
exp_x2 = -12.0 if from_left2 else W_W + 2.0
pin(f"the stream advances: the second launch is again exactly its "
    f"draw (shot {k2} after the feed)",
    owl_frame2 is not None and owl_frame2["owl"].get("x") == exp_x2 and
    owl_frame2["owl"].get("y") == float(row2),
    f"got=({owl_frame2['owl'].get('x')},{owl_frame2['owl'].get('y')}) "
    f"exp=({exp_x2},{row2})")

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the owl hunts the flash: night's third threat")
print("draws only on real shots, announces itself by the drift, feeds")
print("on greed, pays nothing back, and its stream never misses.")
