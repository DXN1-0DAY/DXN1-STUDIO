#!/usr/bin/env python3
# DS2-R32 probe: snake.py "the meal wears the heat" — over the real
# wire (python SDK) on an 18x13 board (220x160).
#
# THE DRIVER: a deterministic serpentine sweep. The probe paces the
# game (dt = the game's own speed law, the SAME double, so every
# packet is exactly one step) and walks a fixed boustrophedon that
# visits EVERY cell — the food is crossed whatever cell it occupies,
# and the geometry is provably self-safe for a snake of length <= 21
# (parallel corridors are one row apart; the trail is 36 cells behind
# at the row turn, longer than the snake ever grows). Turn pairs
# (vertical + new horizontal) are queued together at the row-end
# trigger, aligned with the wire's two-packet dispatch latency.
#
# THE STRONG PIN: the probe integrates the game's own breath clock
# (t = the sum of the dt it sent) and subtracts 1.5*sin(4t) from every
# observed glow — the implied BASE must equal 3 + 1.5*min(score,20)/20
# EXACTLY on every frame: the birth law (3.0), meal 10 (3.75), the cap
# (4.5), and every staircase step between. Plus: the milestone voice
# speaks the cap ("as sharp as it gets") from twenty on and stays bare
# at fifteen; the ranks survive; and the sweep reaches the cap alive.
import json, subprocess, sys, os, re, math

import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
REPO = _HOME
os.environ["PYTHONPATH"] = f"{REPO}/sdk"
W, H, CELL = 220, 160, 12
COLS = W // CELL                     # 18
ROWS = H // CELL                     # 13

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

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
        return child_line()

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

t_known = 0.0
dt_now = 0.14
def tick(keys=None, chars=""):
    """one packet — the probe is the metronome (dt = the speed law)."""
    global t_known
    send({"t": "tick", "dt": dt_now,
          "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": []})
    t_known += dt_now
    while True:
        pkt = child_line()
        if pkt is None:
            print("FAIL: child died"); sys.exit(1)
        if pkt.get("t") == "frame":
            return {e["name"]: e for e in pkt["set"]}, pkt

KEY = {(-1, 0): "left", (1, 0): "right", (0, -1): "jump", (0, 1): "s"}
CH = {(0, 1): "s", (0, -1): "w", (-1, 0): "a", (1, 0): "d"}
# the SDK dispatches the keys DICT first (in its own fixed order) and
# the chars STRING second — so a TURN PAIR must ride chars alone when
# order matters: the string's order IS the queue's order

def turn_packet(d):
    """(keys, chars) for a direction — down rides chars."""
    name = KEY[d]
    return ([name], "") if name != "s" else ([], "s")

send({"t": "hello", "w": W, "h": H})
scene = child_line()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:100]}"
ents = {e["name"]: e for e in scene["entities"]}
pin("scene has 5 entities (hud + food + 3 segs)", len(ents) == 5, str(len(ents)))
pin("the meal is born at glow 3.0 exactly", ents["food"].get("glow") == 3.0,
    str(ents["food"].get("glow")))
headname = next(n for n in ents if re.match(r"seg\d+_0$", n))

def hud_score(ents):
    m = re.search(r"score (\d+)", (ents.get("hud") or {}).get("text", ""))
    return int(m.group(1)) if m else None

# ---- the serpentine sweep --------------------------------------------
# cells: x in 0..COLS-1, y in 0..ROWS-1 (in pixel terms x*CELL, y*CELL)
# the head walks rows horizontally; at each row's far cell it turns
# vertically one cell, then back horizontally. At the top/bottom edge
# the vertical direction bounces. Every cell is visited.
sweep_dir = 1                        # +1 right, -1 left
vdir = 1                             # +1 down, -1 up (the row-end turn)
pending = []                         # turns sent, not yet observed landed
next_keys, next_chars = [], ""

def far_x(sd):
    return (COLS - 1) * CELL if sd > 0 else 0

score = 0
says = {}
bad = []              # (tick, score, implied, expected)
samples = []          # (score, implied_base)
dead = False
prev_score = 0
actual = (1, 0)
head_last = None
dbg = []

for i in range(6000):
    ents, f = tick(keys=next_keys, chars=next_chars)
    next_keys, next_chars = [], ""
    head, food_e = ents.get(headname), ents.get("food")
    if head is None or food_e is None or f.get("win"):
        dead = True
        if os.environ.get("HEAT_DEBUG"):
            print("   death frame:", f.get("win"),
                  "head=", head and (head["x"], head["y"]),
                  "actual=", actual, "pending=", pending)
        break
    s = hud_score(ents)
    if s is not None:
        score = s
    # pace the next packet: the game's own speed law, one step per packet
    dt_now = max(0.06, 0.14 - score * 0.004)
    if f.get("say"):
        m = re.match(r"(\d+) meals", f["say"])
        if m:
            says[int(m.group(1))] = f["say"]
    # the observed facing: the head's last hop, per the wire
    if head_last is not None:
        dx, dy = head["x"] - head_last[0], head["y"] - head_last[1]
        if dx or dy:
            actual = (dx // CELL if dx else 0, dy // CELL if dy else 0)
            if pending and actual == pending[0]:
                pending.pop(0)               # the turn landed
    head_last = (head["x"], head["y"])
    # the strong pin — but SKIP the eat frame: on_tick paints the
    # breath BEFORE it eats, so the eat frame's glow wears the PREVIOUS
    # score's base while the HUD already says the new one
    if s == prev_score:
        implied = (food_e.get("glow") or 0) - 1.5 * math.sin(4 * t_known)
        expected = 3 + 1.5 * min(score, 20) / 20
        samples.append((score, implied))
        if abs(implied - expected) > 1e-6:
            bad.append((i, score, round(implied, 6), round(expected, 6)))
    prev_score = s if s is not None else prev_score
    if os.environ.get("HEAT_DEBUG") and i % 40 == 0:
        print(f"   trace i={i} score={score} head=({head['x']},{head['y']}) "
              f"actual={actual} food=({food_e['x']},{food_e['y']}) dt={dt_now} "
              f"pending={pending}")
    if score >= 21:
        break
    # ---- the sweep's turn schedule ----
    # the trigger is ONE CELL BEFORE the far cell: the head coasts onto
    # the far cell (the coast law — one unavoidable cell of inertia),
    # and the queued pair lands on the two ticks after
    hx, hy = head["x"] // CELL, head["y"] // CELL
    if not pending and hx == far_x(sweep_dir) // CELL - sweep_dir \
       and actual[1] == 0:
        # the vertical bounce is ABSOLUTE at the edges: the last row
        # turns up, the first row turns down
        if hy == ROWS - 1:
            vdir = -1
        elif hy == 0:
            vdir = 1
        # queue the row-end pair (V, then H') — both ride chars, in order
        pair = [(0, vdir), (-sweep_dir, 0)]
        next_chars = "".join(CH[d] for d in pair)
        pending = list(pair)
        sweep_dir = -sweep_dir
    elif pending and actual == (0, 1) and pending and pending[0] == (0, -1):
        pass                                 # (defensive; never taken)


pin("the sweep reached the cap alive (score >= 21, no win banner)",
    not dead and score >= 21, f"score={score} dead={dead}")
pin("the implied base is the EXACT staircase on every frame",
    not bad, f"{len(bad)} bad frames, first={bad[:2]}")

def base_at(lo, hi):
    b = [v for s, v in samples if lo <= s <= hi]
    return (min(b), max(b)) if b else (None, None)

b0 = base_at(0, 0)
b10 = base_at(10, 10)
bcap = base_at(20, 40)
pin("the birth base is exactly 3.0", b0[0] is not None and
    abs(b0[0] - 3.0) < 1e-6 and abs(b0[1] - 3.0) < 1e-6, str(b0))
pin("the base at meal 10 is exactly 3.75", b10[0] is not None and
    abs(b10[0] - 3.75) < 1e-6 and abs(b10[1] - 3.75) < 1e-6, str(b10))
pin("the base at the cap is exactly 4.5", bcap[0] is not None and
    abs(bcap[0] - 4.5) < 1e-6 and abs(bcap[1] - 4.5) < 1e-6, str(bcap))
pin("the milestone voice at twenty speaks the cap",
    20 in says and "as sharp as it gets" in says[20], str(says.get(20)))
pin("the milestone voice at fifteen stays bare",
    15 in says and "as sharp as it gets" not in says[15], str(says.get(15)))
pin("the ranks survive the heat law",
    5 in says and "you are" in says[5], str(says.get(5)))

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the meal wears the heat")
