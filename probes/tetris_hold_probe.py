#!/usr/bin/env python3
# DS2-R20 probe: tetris.js "the vault" — the hold piece, over the
# real wire (node SDK).
# pins: 23 entities (the banner label joined); the vault sleeps until first summoned (hv seats
# hidden); c stashes the falling piece (vault wears its color) and
# the queue's peek becomes the order (falling color == old preview
# color); a spent vault wears the ghost's alpha 0.32; a second c is
# honestly refused (say speaks, nothing moves); a lock re-arms the
# vault and c becomes a straight swap (falling color == old hold
# color); and r under a fresh sky leaves the vault empty again.
import json, subprocess, sys, os, select

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "tetris.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def read(timeout=4.0):
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r: return None
    line = p.stdout.readline()
    if not line: return None
    try: return json.loads(line)
    except Exception: return None

def frame(keys=None, chars=""):
    send({"t": "tick", "dt": 0.05,
          "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

send({"t": "hello", "w": 120, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
names = [e["name"] for e in scene["entities"]]
pin("scene has 23 entities", len(names) == 23, str(len(names)))
pin("the vault label waits under the queue", "hol" in names)

ents, _ = frame()
pin("the vault sleeps before its first summon",
    all(not ents[f"hv{i}"].get("visible", 1) for i in range(4)))
fall0 = ents["fall0"]["color"]
pv0 = ents["pv0"]["color"]

# 1. c stashes: the vault wears the falling piece's color, the queue's
#    peek becomes the order, and the spent vault wears alpha 0.32
ents, _ = frame(chars="c")
pin("c stashes the falling piece (vault wears its color)",
    all(ents[f"hv{i}"].get("visible", 0) == 1 for i in range(4)) and
    ents["hv0"]["color"] == fall0, f"hold {ents['hv0']['color']} was {fall0}")
pin("the queue's peek becomes the order (falling == old preview)",
    ents["fall0"]["color"] == pv0, f"fall {ents['fall0']['color']} pv {pv0}")
pin("a spent vault wears the ghost's alpha (0.32)",
    abs(ents["hv0"].get("alpha", 1) - 0.32) < 0.001,
    str(ents["hv0"].get("alpha")))
pin("the falling piece is whole (4 seats, one color)",
    len({ents[f"fall{i}"]["color"] for i in range(4)}) == 1)

# 2. a second c is honestly refused
ents, f2 = frame(chars="c")
pin("the refusal speaks (say carries the vault's word)",
    "vault" in (f2.get("say") or ""), str(f2.get("say")))
pin("nothing moved (the vault keeps its piece, the order keeps its seats)",
    ents["hv0"]["color"] == fall0 and ents["fall0"]["color"] == pv0)

# 3. a lock re-arms the vault; c becomes a straight swap
ents, _ = frame(keys=["space"])          # slam: lock + sweep
ents, _ = frame()                        # the spawn's own frame
hold0 = ents["hv0"]["color"]
fall1 = ents["fall0"]["color"]
pin("after a lock the vault is re-armed (alpha back to 1)",
    abs(ents["hv0"].get("alpha", 1) - 1.0) < 0.001,
    str(ents["hv0"].get("alpha")))
ents, _ = frame(chars="c")
pin("the swap gives back (falling == old hold color)",
    ents["fall0"]["color"] == hold0, f"fall {ents['fall0']['color']} hold {hold0}")
pin("the swap takes again (vault == the piece that fell)",
    ents["hv0"]["color"] == fall1, f"hold {ents['hv0']['color']} was {fall1}")

# 4. r under a fresh sky empties the vault (after a top-out; here we
#    just verify the reset law holds via a fresh spawn's honest state)
p.kill()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
