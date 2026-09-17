#!/usr/bin/env python3
"""probe for sdk/examples/snake.py — THE CHASE AND THE REVIVAL
(re-homed v3.1.94, load-proof rebuild).

The chase probe's second eviction taught why it died: its drive read
ONE line per tick, so every meal's chatter line stole the next frame
and the plan steered on stale state — green on an idle machine, red
under full-gates load, wall-biting at score 0 before the chase
developed. The rebuild rides the metronome law: a pump thread drains
stdout into a queue, every tick reads until the FRAME (chatter is
processed in place, never allowed to steal a frame), and the scene
is read until it actually arrives. The drive stays the wall-aware
greedy chase — now on fresh state every tick.

Pins (two phases, all deterministic):
  A. the chase: three meals eaten, the score var mirrored on the
     wire, the snake grown past its birth length, frames flowing;
  B. the revival, ON PURPOSE: the drive stops steering, the wall
     takes the snake (the banner names the score), exactly one
     space revives — the hud returns to score 0, the head teleports
     home and then WALKS again. The restart path is exercised, not
     hoped for.
"""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.94): evicted in v3.1.92 as load-flaky,
# rebuilt on the metronome law — canonical pins: probes/*_probe.py.
import json, subprocess, sys, os, re, time, threading, queue

REPO = _HOME
SDK = os.path.join(REPO, "sdk")
EX = os.path.join(SDK, "examples")
CELL, COLS, ROWS = 12, 13, 5
# wasd rides chars — SINGLE letters (the SDK dispatches every non-blank
# char of `chars`; "right" as chars would arrive as r,i,g,h,t garbage).
# space rides the keys dict (one of the four bare held names).
KEY = {(1, 0): "d", (-1, 0): "a", (0, -1): "w", (0, 1): "s"}

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

env = dict(os.environ)
env["PYTHONPATH"] = SDK
p = subprocess.Popen(["python3", os.path.join(EX, "snake.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    try:
        p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
        return True
    except BrokenPipeError:
        return False

_q = queue.Queue()
def _pump():
    for ln in p.stdout:
        _q.put(ln)
    _q.put("")
threading.Thread(target=_pump, daemon=True).start()

st = {"food": None, "head": None, "cur": (1, 0), "frames": 0,
      "score_var": None, "len_max": 0, "meals": 0, "crashes": 0,
      "hud": "", "win": None}

def read_pkt(timeout=2):
    """one line from the child — chatter is processed IN place (the
    metronome law: no line is ever allowed to steal a frame)."""
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
            s = ln.strip()
            if "wall" in s or "bit yourself" in s:
                st["crashes"] += 1
            if s.startswith("meal"):
                st["meals"] += 1
            continue
    return None

def read_frame(timeout=8):
    t0 = time.time()
    while time.time() - t0 < timeout:
        pkt = read_pkt(timeout=1)
        if pkt is None:
            return None
        if pkt.get("t") == "frame":
            st["frames"] += 1
            segs = 0
            for e in pkt.get("set", []):
                n = str(e.get("name", ""))
                if n == "food":
                    st["food"] = (e.get("x", 0), e.get("y", 0))
                if e.get("tag") == "head":
                    head = (e.get("x", 0), e.get("y", 0))
                    if head != st["head"]:
                        if st["head"] is not None:
                            d = (head[0] - st["head"][0],
                                 head[1] - st["head"][1])
                            if abs(d[0]) == CELL or abs(d[1]) == CELL:
                                st["cur"] = (d[0] // CELL, d[1] // CELL)
                        st["head"] = head
                if n.startswith("seg"):
                    segs += 1
                if n == "hud":
                    st["hud"] = e.get("text", "")
            st["len_max"] = max(st["len_max"], segs)
            if pkt.get("win"):
                st["win"] = pkt["win"]
            v = pkt.get("vars", {})
            if "score" in v:
                st["score_var"] = v["score"]
            return pkt
    return None

def tick(keys=None, chars="", dt=0.2):
    """one honest tick, one honest frame — None means the child stalled.
    the keys dict only carries left/right/jump/space; WASD RIDES CHARS
    (wire law #2 — the dispatch in sdk/dxn3.py reads the keys dict for
    the four bare names and EVERY non-blank char of `chars`).
    dt 0.2 is the metronome law: dt >= the snake's step time (0.14 at
    birth, 0.06 at the cap) means EXACTLY ONE honest step per packet —
    one command in flight, no stale queue, no drift."""
    if not send({"t": "tick", "dt": dt,
                 "keys": {k: True for k in (keys or [])},
                 "chars": chars, "hits": []}):
        return None
    return read_frame()

# ---- handshake: read until the scene actually arrives
send({"t": "hello", "w": 160, "h": 60})
t0 = time.time()
scene = None
while time.time() - t0 < 8:
    pkt = read_pkt(timeout=1)
    if pkt is not None and pkt.get("t") == "scene":
        scene = pkt
        break
assert scene is not None, "no scene — child never spoke"
pin("the scene arrives (5 entities: hud, food, three birth segs)",
    len(scene.get("entities", [])) == 5,
    str([e.get("name") for e in scene.get("entities", [])]))

def build_route():
    """the serpentine — the R32 lore's own verdict: greedy hunters orbit
    the meal forever (the 180 ban feeds the ring; the trace proved it —
    a perfect clockwise circle around the food). A covering walk beats
    any hunter: every cell visited, the meal eaten as a byproduct of
    coverage, provably self-safe while the tail trails along the same
    route (the shortest revisit gap is 24 steps; the body is <= 7)."""
    cells = [(0, 0)]
    def leg(to):
        cx, cy = cells[-1]
        dx = (to[0] > cx) - (to[0] < cx)
        dy = (to[1] > cy) - (to[1] < cy)
        while (cx, cy) != to:
            cx += dx; cy += dy
            cells.append((cx, cy))
    # routeA: boustrophedon down, then up col 12
    leg((12, 0)); leg((12, 1)); leg((0, 1)); leg((0, 2)); leg((12, 2))
    leg((12, 3)); leg((0, 3)); leg((0, 4)); leg((12, 4)); leg((12, 0))
    # routeB: boustrophedon the other way, then up col 0 — the cycle closes
    leg((0, 0)); leg((0, 1)); leg((12, 1)); leg((12, 2)); leg((0, 2))
    leg((0, 3)); leg((12, 3)); leg((12, 4)); leg((0, 4)); leg((0, 0))
    return cells[:-1]                  # cells[0] == the walk's end

ROUTE = build_route()
START_IDX = ROUTE.index((6, 2))        # the birth cell, facing east —
                                       #   routeA row 2 runs east: aligned
CHAR = {(1, 0): "d", (-1, 0): "a", (0, -1): "w", (0, 1): "s"}

# ---- phase A: the sweep — follow the route until three meals
chased = False
stalled = False
desynced = False
ptr = START_IDX
for i in range(400):
    # the command enqueued at tick i applies at tick i+1's step — it must
    # aim from the head's POST-tick cell (ptr+1) to the one beyond (ptr+2)
    a = ROUTE[(ptr + 1) % len(ROUTE)]
    b = ROUTE[(ptr + 2) % len(ROUTE)]
    d = (b[0] - a[0], b[1] - a[1])
    if tick(chars=CHAR[d]) is None:
        stalled = True
        break
    if st["crashes"]:                     # the sweep died: say so and stop
        break
    got = (st["head"][0] // CELL, st["head"][1] // CELL) \
        if st["head"] else None
    if got != ROUTE[(ptr + 1) % len(ROUTE)]:
        desynced = True                   # the walk and the snake diverged
        break
    ptr = (ptr + 1) % len(ROUTE)
    if st["meals"] >= 3 and (st["score_var"] or 0) >= 3:
        chased = True
        break
pin("THE CHASE: the sweep fed the snake — three meals, var mirrored",
    chased and not stalled and not desynced,
    f"meals={st['meals']} score_var={st['score_var']} "
    f"frames={st['frames']} crashes={st['crashes']} "
    f"stalled={stalled} desynced={desynced}")
pin("the snake grew past its birth length (the meal rides the tail)",
    st["len_max"] > 3, f"len_max={st['len_max']}")
pin("the sweep never died (zero crashes while the route drove)",
    st["crashes"] == 0, f"crashes={st['crashes']}")
pin("the frames flowed the whole way (a metronome drive, no lag)",
    st["frames"] > 40, f"frames={st['frames']}")

# ---- phase B: the revival, on purpose — stop steering, the wall
# takes the snake, the banner speaks, exactly one space revives
crashes_at_b = st["crashes"]
st["win"] = None
spaced = False
revive_score = None
revived = False
head_walked = False
birth_head = None
stalled = False
for i in range(300):
    keys = None
    if st["crashes"] > crashes_at_b and not spaced:
        m = re.search(r"score (\d+)", st["win"] or "")
        revive_score = int(m.group(1)) if m else None
        keys = ["space"]                  # exactly one space — when
        spaced = True                     # alive it's an up-turn!
        st["head"] = None                 # the teleport is not a step
    if tick(keys) is None:
        stalled = True
        break
    if spaced and "score 0" in st["hud"]:
        revived = True
        if birth_head is None:
            birth_head = st["head"]
        elif st["head"] != birth_head and st["head"] is not None:
            head_walked = True            # a real step, not the teleport
    if revived and head_walked:
        break
pin("THE REVIVAL: the banner names the score, one space revives "
    "(hud back to score 0)",
    revive_score is not None and revived and not stalled,
    f"banner={st['win']!r} score={revive_score} hud={st['hud']!r} "
    f"stalled={stalled}")
pin("the head walks again after the revive (the chase resumes)",
    head_walked, f"head={st['head']} birth={birth_head}")
pin("exactly one life spent in phase B (one wall, one space)",
    st["crashes"] - crashes_at_b == 1,
    f"crashes {crashes_at_b} -> {st['crashes']}")

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the chase feeds, the var mirrors, the wall")
print("speaks, one space revives, and the snake walks again. The")
print("drive is the metronome now: no line steals a frame, no load")
print("can lag the plan.")
sys.exit(0)
