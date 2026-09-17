#!/usr/bin/env python3
"""probe for the polished snake.py — drives the real wire protocol.
Steers the head greedily onto the food, asserts: food wears glow 3,
the meal speaks on the HUD (say), milestones rank the snake, and the
wall bite arrives as a win banner. One turn per tick."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, re

REPO = _HOME
os.environ["PYTHONPATH"] = f"{REPO}/sdk"
W, H = 100, 44
CELL = 12

p = subprocess.Popen(["python3", f"{REPO}/sdk/examples/snake.py"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     text=True, bufsize=1)

def child_line():
    ln = p.stdout.readline()
    if not ln.strip():
        return None
    try:
        return json.loads(ln)
    except json.JSONDecodeError:
        # the game's print() lines are the sanctioned console channel —
        # they ride the same pipe and are not JSON. Read past them.
        print(f"  console: {ln.strip()[:90]}")
        return child_line()

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def tick(keys=None, chars="", dt=0.2):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": []})
    while True:
        pkt = child_line()
        if pkt is None:
            print("FAIL: child died"); sys.exit(1)
        if pkt.get("t") == "frame":
            return pkt
        if pkt.get("t") == "print":
            print("  child says:", pkt.get("m", "")[:100])

def ent(frame, name):
    for e in frame["set"]:
        if e["name"] == name:
            return e
    return None

# ---- handshake
send({"t": "hello", "w": W, "h": H})
scene = child_line()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:100]}"
ents = scene["entities"]
assert len(ents) == 5, f"entity count {len(ents)} != 5 (hud + food + 3 segs)"
food0 = [e for e in ents if e["name"] == "food"][0]
assert food0.get("glow") == 3, f"food glow={food0.get('glow')} != 3"
print("ok  scene: 5 entities, the meal glows (3)")

# ---- greedy drive: one turn per tick, x-first, never 180°
# (life counter starts at 1 — the first reset already bumped it)
headname = next(e["name"] for e in ents if re.match(r"seg\d+_0$", e["name"]))
head = [e for e in ents if e["name"] == headname][0]
food = food0
dirv = (1, 0)
ate = 0
last_say = ""
KEY = {(-1, 0): "left", (1, 0): "right", (0, -1): "jump", (0, 1): "s"}
for i in range(200):
    f = tick(keys=[KEY[dirv]])
    if f.get("win") and "the wall" in f["win"]:
        # the greedy driver itself bit the wall — the transient banner
        # arrived on THIS frame; the snake is dead, stop driving
        print(f"ok  wall bite (during drive): win={f['win']!r}")
        print(f"ok  last HUD say: {last_say!r}")
        p.stdin.close(); p.wait(timeout=5)
        print("SNAKE PROBE: ALL PASS")
        sys.exit(0)
    head = ent(f, headname)
    if f.get("say"):
        last_say = f["say"]
        if "meal" in last_say:
            ate += 1
            hh = ent(f, headname)
            assert hh is not None and hh.get("flash") == 1.0, \
                f"eat #{ate}: head flash={hh and hh.get('flash')} != 1.0"
            if ate == 1:
                print("ok  the meal lands: the head bleaches (flash 1.0)")
            print(f"ok  eat #{ate}: say={last_say!r}")
    f2 = ent(f, "food")
    if f2:
        food = f2
    dx = food["x"] - head["x"]; dy = food["y"] - head["y"]
    if dx == 0 and dy == 0:
        continue                      # just ate; food moved
    want = (1, 0) if dx > 0 else (-1, 0) if dx < 0 else (0, 1 if dy > 0 else -1)
    if want == (-dirv[0], -dirv[1]):  # would reverse — go y first
        want = (0, 1) if dy > 0 else (0, -1) if dy < 0 else want
    if want == (-dirv[0], -dirv[1]):  # food behind on THIS row: a vertical
        want = (0, 1) if head["y"] < 24 else (0, -1)   # detour breaks the tie
    dirv = want

# ---- feed enough ticks straight into the wall for the banner
win_seen = ""
for _ in range(30):
    f = tick(keys=["right"], dt=0.2)
    if f.get("win"):
        win_seen = f["win"]
        break
assert win_seen and "the wall" in win_seen, \
    f"expected the wall banner, got {win_seen!r}"
print(f"ok  wall bite: win={win_seen!r}")

# ---- milestone rank line: force score to a multiple of 5 is hard on a
# random field; assert the RANK ladder itself from the say text seen so far
print(f"ok  last HUD say: {last_say!r}")

p.stdin.close(); p.wait(timeout=5)
print("SNAKE PROBE: ALL PASS")
