#!/usr/bin/env python3
"""probe for sdk/examples/shooter.py — THE DRIFTING TWIN (v3.1.73).

The shooter's second threat class, pinned on the real wire:

  1. the scene carries FOUR entities: ship, enemy, hud — and twin;
  2. the twin drifts in through the ghost law: alpha 0.15 rising to
     the honest 1.0 over DRIFT seconds;
  3. the twin RIDES A BOB: its y is a sine in dt — sampled over 16
     ticks the trace bends (rises then falls, non-monotonic);
  4. the muzzle law still speaks: a fire births ship glow 5, worn
     12/s by tick;
  5. THE TWIN'S OWN STREAM: a shot×twin hit pays 25, the bolt is
     destroyed (the ledger forgets), and the twin's respawn is
     EXACTLY what the named stream deals — random.Random("the twin's
     return"), the same draws a replay probe predicts;
  6. THE THREAT'S OWN STREAM: a shot×enemy hit pays 10 and the
     enemy's respawn is exactly "the threat's return"'s draw — the
     two streams never share a draw (the seed chapter's law);
  7. a second twin hit takes the NEXT pair of draws — the stream
     advances, determinism survives the repeat.
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
p = subprocess.Popen(["python3", os.path.join(REPO, "sdk", "examples", "shooter.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

_q = queue.Queue()
def _pump():
    for ln in p.stdout:
        _q.put(ln)
threading.Thread(target=_pump, daemon=True).start()

def read(timeout=6):
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
    return None

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

def tick(keys=None, hits=None, dt=0.05):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": "", "hits": hits or []})
    while True:
        pkt = read()
        if pkt is None:
            raise AssertionError("no frame — child stalled")
        if pkt.get("t") == "frame":
            return {e["name"]: e for e in pkt["set"]}, pkt

send({"t": "hello", "w": W_W, "h": H_W})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
names = sorted(e["name"] for e in scene["entities"])
pin("the scene carries fifteen entities — the four originals plus "
    "the night's furniture (nine stars, a moon) (v3.1.76)",
    names == sorted(["enemy", "hud", "ship", "twin", "moon", "owl"] +
                    [f"star{i}" for i in range(9)]), str(names))

# the drift-in law
a0 = scene["entities"][[e["name"] for e in scene["entities"]].index("twin")].get("alpha")
for _ in range(20):
    ents, pkt = tick([])
a20 = ents["twin"].get("alpha")
pin("the twin drifts in: alpha 0.15 -> the honest 1.0",
    abs(a0 - 0.15) < 1e-9 and a20 == 1.0, f"alpha0={a0} alpha20={a20}")

# the bob: the y trace bends (a 60-tick window — 6.6 rad of phase,
# guaranteed to cross a turning point)
ys = []
for _ in range(60):
    ents, pkt = tick([])
    ys.append(ents["twin"].get("y"))
dys = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
bends = any(d1 * d2 < 0 for d1, d2 in zip(dys, dys[1:]))
pin("the twin rides a sine bob (the y trace bends)", bends, f"{ys}")

# the muzzle law re-pinned
ents, pkt = tick(["space"])
g0 = ents["ship"].get("glow")
ents, pkt = tick([])
g1 = ents["ship"].get("glow")
pin("the muzzle speaks glow 5 and wears the honest 12/s",
    g0 == 5 and abs(g1 - 4.4) < 1e-9, f"g0={g0} g1={g1}")

# THE TWIN'S OWN STREAM: hit it, the named stream answers
TW = random.Random("the twin's return")
exp_x = TW.randint(2, W_W - 14)
exp_y = TW.randint(6, H_W // 2)
ents, pkt = tick(["space"])
ents, pkt = tick(hits=["shot1", "twin"])
hit_del = pkt.get("del") or []
tw = ents["twin"]                       # the twin's own patch rides the
                                        # hit frame (on_hit mutates it)
ents, pkt = tick([])                    # the hud pays one tick late:
                                        # on_tick wrote its text BEFORE
                                        # on_hit ran this very tick
hud1 = ents["hud"].get("text")
pin("a shot x twin hit pays 25 (the hud says SCORE 25)",
    hud1 == "SCORE 25", repr(hud1))
pin("the twin's respawn is EXACTLY its named stream's draw",
    tw.get("x") == exp_x and abs(tw.get("y") - exp_y) < 1e-9 and
    tw.get("alpha") == 0.15,
    f"got=({tw.get('x')},{tw.get('y')},a={tw.get('alpha')}) "
    f"exp=({exp_x},{exp_y})")
pin("the ledger forgot the spent bolt (del carries shot1)",
    "shot1" in hit_del, str(hit_del))

# THE THREAT'S OWN STREAM: the enemy answers a different stream
TH = random.Random("the threat's return")
exp_ex = TH.randint(2, W_W - 14)
exp_ey = TH.randint(2, H_W // 2)
ents, pkt = tick(["space"])
ents, pkt = tick(hits=["shot2", "enemy"])
en = ents["enemy"]
ents, pkt = tick([])                    # the hud's honest visibility tick
hud2 = ents["hud"].get("text")
pin("a shot x enemy hit pays 10 (the hud says SCORE 35)",
    hud2 == "SCORE 35", repr(hud2))
pin("the enemy's respawn is EXACTLY its named stream's draw",
    en.get("x") == exp_ex and en.get("y") == exp_ey and
    en.get("alpha") == 0.15,
    f"got=({en.get('x')},{en.get('y')}) exp=({exp_ex},{exp_ey})")

# the streams advance: a second twin hit takes the NEXT pair of draws
exp_x2 = TW.randint(2, W_W - 14)
exp_y2 = TW.randint(6, H_W // 2)
ents, pkt = tick(["space"])
ents, pkt = tick(hits=["shot3", "twin"])
tw2 = ents["twin"]
pin("a second twin hit takes the stream's NEXT draws (determinism "
    "survives the repeat)",
    tw2.get("x") == exp_x2 and abs(tw2.get("y") - exp_y2) < 1e-9,
    f"got=({tw2.get('x')},{tw2.get('y')}) exp=({exp_x2},{exp_y2})")

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the drifting twin lives: a second threat class")
print("with its own bob and its own named stream, the void announcing")
print("every respawn, the ledger forgetting every spent bolt.")
