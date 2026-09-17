#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R26 probe: asteroids.js "the wear audit" — v3.1.69.
# Two laws audited and pinned on the real wire (node SDK, dt 0.016):
#  1. THE SPLIT BLOOMS: a split is a small detonation — the two child
#     rocks are BORN with glow 2 whole (on.hit runs after the tick, so
#     the birth frame carries the full bloom), worn by the game's own
#     3/s staircase (2 -> 1.952 -> 1.904 at dt 0.016) down to dark at
#     ~0.67 s. Fresh-ring rocks carry NO bloom — their entrance is the
#     drift-in alpha fade, honestly absent light.
#  2. THE FLAME WEARS HONESTLY: the thrust key LIGHTS the flame whole
#     (glow 4, visible) the very frame it arrives — the key handler
#     runs after the tick, so a glow left to the tick's wear would
#     render already faded (the birth-tick law, key edition). Holding
#     holds it at 4; release wears it down the burn's own linear
#     staircase (0.12 s of burn: 3.4667, 2.9333, 2.4, ... 0) — the old
#     hard cut 4 -> 0 is retired.
#  3. THE LEDGER FORGETS: a blooming rock destroyed by a shot takes its
#     bloom off the ledger the same tick — no ghost patches, no crash.
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

def frame(keys=None, hits=None):
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

send({"t": "hello", "w": 160, "h": 60})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents = {e["name"]: e for e in scene["entities"]}
SCENE_NAMES = set(ents)                 # the fresh ring + hud + ship + nose
pin("scene has 7 entities (no new furniture)", len(ents) == 7, str(len(ents)))
pin("fresh-ring rocks carry NO bloom (the drift-in is their entrance)",
    all(ents[f"rock0_{i}"].get("glow", 0) == 0 for i in range(4)),
    str([ents[f"rock0_{i}"].get("glow") for i in range(4)]))
pin("the flame is born dark before the first thrust",
    ents["nose"].get("glow", 0) == 0 and ents["nose"].get("visible", 1) in (0, 1))

# ---- 1. the thrust lights the flame WHOLE the very frame the key lands
ents, f = frame(keys=["jump"])
pin("thrust frame: the flame is visible", ents["nose"].get("visible") == 1,
    str(ents["nose"].get("visible")))
pin("thrust frame: the flame is LIT WHOLE (glow 4)", ents["nose"].get("glow") == 4,
    str(ents["nose"].get("glow")))
ents, _ = frame(keys=["jump"])
pin("held: the burn holds the light at 4", ents["nose"].get("glow") == 4,
    str(ents["nose"].get("glow")))
ents, _ = frame(keys=["jump"])
pin("held: still 4 — no born-faded light", ents["nose"].get("glow") == 4,
    str(ents["nose"].get("glow")))

# ---- 2. release: the honest staircase down the burn's own age
ents, _ = frame()                       # burn 0.104 -> glow 3.4667
g1 = ents["nose"].get("glow")
pin("release step 1 (3.4667)", abs(g1 - 3.4666666666666663) < 1e-6, str(g1))
ents, _ = frame()
g2 = ents["nose"].get("glow")
pin("release step 2 (2.9333)", abs(g2 - 2.933333333333333) < 1e-6, str(g2))
for _ in range(6):                      # walk the rest of the burn out
    ents, _ = frame()
pin("the flame wears to dark (glow 0, hidden)",
    ents["nose"].get("glow") == 0 and ents["nose"].get("visible") == 0,
    f"glow={ents['nose'].get('glow')} visible={ents['nose'].get('visible')}")

# ---- 3. the split blooms: inject the hull hit, read the children
ents, f = frame(hits=["ship", "rock0_0"])
kids = [n for n in ents if n not in SCENE_NAMES and n != "hud"]
pin("the split bore two children", len(kids) == 2, str(sorted(kids)))
pin("the children are BORN WHOLE (glow 2)",
    all(ents[k].get("glow") == 2 for k in kids),
    str([(k, ents[k].get("glow")) for k in kids]))
ents, _ = frame()
pin("the bloom wears (1.952 at dt 0.016)",
    all(abs(ents[k].get("glow", 0) - 1.952) < 0.0011 for k in kids),
    str([(k, ents[k].get("glow")) for k in kids]))
ents, _ = frame()
pin("the bloom wears (1.904)",
    all(abs(ents[k].get("glow", 0) - 1.904) < 0.0011 for k in kids),
    str([(k, ents[k].get("glow")) for k in kids]))
for _ in range(44):                     # 2 / (3 * 0.016) ~= 42 ticks to dark
    ents, _ = frame()
pin("the split's light empties — no flash-forever",
    all(ents[k].get("glow", 0) == 0 for k in kids if k in ents),
    str([(k, ents[k].get("glow")) for k in kids if k in ents]))

# ---- 4. the ledger forgets: shoot a blooming child out of the sky
ents, _ = frame(keys=["space"])         # fire (uid 2 -> bul0_2)
bul = [n for n in ents if n.startswith("bul")]
pin("the shot exists", len(bul) == 1, str(bul))
pin("the muzzle flash: the shot is BORN WHOLE (glow 2)",
    ents[bul[0]].get("glow") == 2, str(ents[bul[0]].get("glow")))
ents, _ = frame()
pin("the muzzle flash wears (1.952 at dt 0.016)",
    abs(ents[bul[0]].get("glow", 0) - 1.952) < 0.0011,
    str(ents[bul[0]].get("glow")))
target = kids[0]
ents, f = frame(hits=[bul[0], target])
gone = f.get("del", [])
pin("the shot and its target both go home",
    target in gone and bul[0] in gone, f"del={gone}")
pin("the split paid its points (a size-8 child is 50)",
    f.get("vars", {}).get("score") == 50, str(f.get("vars")))
ents, _ = frame()
pin("the ledger forgot the dead rock (no ghost patches)",
    target not in ents, str([n for n in ents if "rock" in n]))

p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
