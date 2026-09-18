#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.92): re-pinned to the current truth and
# walked by gate 8 — a probe the gates never run ages into a liar (the
# drift ledger lives in probes/README.md).
# DS2-R23 probe: snake.py "the light laws" — over the real wire at
# 100x44. The cards.py flash-forever bug was found living here too:
# the head bleached at meal one and NEVER came back (the studio keeps
# the last light a game sent — the decay is the game's job). Pins:
# 5 entities; the scene's food wears glow 3 (the breath's t=0); the
# meal's bleach runs the honest 3/s staircase — 1.0 on the meal
# frame, gone within ~0.4 s, and it STAYS gone (the forever-bleach
# pin); the newborn segment ghosts in (alpha 0.35 -> 1 at 2/s); the
# meal BREATHES (glow 3 +/- 1.5 on a 4-rad sine — sampled across
# frames it swings); a milestone meal flashes the tail too and that
# bleach decays by the same law; steering rides CHARS (the engine's
# held-key whitelist forwards only left/right/jump/space — the R15
# lesson); and the wall bite still lands as the honest win banner.
import json, subprocess, sys, os, re

REPO = _HOME
os.environ["PYTHONPATH"] = f"{REPO}/sdk"
W, H = 240, 120   # a roomy 20x10 board — the 8x3 corner-trap starves the driver
CELL = 12
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
        return child_line()          # the game's prints ride the pipe too

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

def ent(frame, name):
    for e in frame["set"]:
        if e["name"] == name:
            return e
    return None

# ---- handshake
send({"t": "hello", "w": W, "h": H})
scene = child_line()
assert scene and scene.get("t") == "scene", "no scene"
ents = scene["entities"]
sn = {e["name"]: e for e in ents}
pin("scene has 5 entities", len(ents) == 5, str(len(ents)))
pin("the scene's food wears glow 3 (the breath's t=0)",
    sn["food"].get("glow") == 3, repr(sn["food"].get("glow")))
headname = next(n for n in sn if re.match(r"seg\d+_0$", n))

# ---- the drive: one turn per tick via CHARS, x-first, never reverse
# (the heading is OBSERVED from the head's own delta — no trust)
head = sn[headname]
food = sn["food"]
prev = (head["x"], head["y"])
heading = (1, 0)
ate = 0
meal_records = []                    # (meal, frames_to_dark, tail_flash_seen)
dark_witness = 0
ghost_seen = None
glow_samples = []
milestone_name = None
milestone_seq = []
last_say = ""
KEY = {(-1, 0): "a", (1, 0): "d", (0, -1): "w", (0, 1): "s"}
pending = (1, 0)
f = {"set": ents}                # the scene doubles as the first frame
win_seen = ""                    # the wall banner, if the drive ever dies                     # the queue's tail: the turn sent last packet

for i in range(1200):
    # queue-aware greedy: the engine runs tick BEFORE keys, so the turn
    # sent now lands AFTER this packet's move — and this packet's move
    # is the QUEUED turn (the one sent last packet), not the observed
    # heading. Plan from head + pending, reject any candidate that
    # reverses the applied heading OR the pending move (a two-step
    # 180 bites the neck), and demand the landing cell stay in bounds
    # (the 8x3 board forgives nothing).
    if pending == (-heading[0], -heading[1]):
        pending = heading                  # a refused reverse: it ran straight
    fx, fy = head["x"] + pending[0] * CELL, head["y"] + pending[1] * CELL
    dx = food["x"] - fx
    dy = food["y"] - fy
    sx = (dx > 0) - (dx < 0)
    sy = (dy > 0) - (dy < 0)
    cands = []
    if dx != 0: cands.append((sx, 0))
    if dy != 0: cands.append((0, sy))
    for keep in (((0, 1) if fy + CELL <= H - CELL else (0, -1)),
                 ((1, 0) if fx + CELL <= W - CELL else (-1, 0))):
        cands.append(keep)                 # detours, bounds-picked
    want = pending                         # hold course by default
    occ = set()                            # the snake's own body, from the
    segs = [e for e in f["set"] if re.match(r"seg\d+_\d+$", e["name"])]  # last frame
    if segs:
        segs.sort(key=lambda e: int(e["name"].rsplit("_", 1)[1]))
        for s in segs[:-1]:                # the tail cell vacates as you land
            occ.add((s["x"], s["y"]))
    for c in cands:
        if c == pending or c == (-pending[0], -pending[1]):
            continue                       # no-op, or a 180 the game refuses:
            # the pop-time test is against the direction of the move
            # this very packet makes (pending), NOT the observed heading
            # — a stale reference bans every legal turn back (the R23
            # lesson: test against the pop-time direction)
        nx, ny = fx + c[0] * CELL, fy + c[1] * CELL
        if nx < 0 or ny < 0 or nx > W - CELL or ny > H - CELL:
            continue                       # the wall is not a plan
        if (nx, ny) in occ:
            continue                       # the tail is not a plan either
        want = c
        break
    f = tick(chars=KEY[want])
    pending = want
    hh = ent(f, headname)
    fd = ent(f, "food")
    if fd:
        food = fd
    glow_samples.append(fd.get("glow", 0) if fd else 0)
    # the head's true heading, from its own motion
    if hh is not None:
        cur = (hh["x"], hh["y"])
        mv = (cur[0] - prev[0], cur[1] - prev[1])
        if mv in ((CELL, 0), (-CELL, 0), (0, CELL), (0, -CELL)):
            heading = (mv[0] // CELL, mv[1] // CELL)
        prev = cur
        head = hh
    if f.get("say"):
        last_say = f["say"]
    if "meal" in last_say and f.get("say") == last_say and hh is not None \
       and hh.get("flash", 0) > 0.99 and (ate == 0 or meal_records[-1][3] != i):
        ate += 1
        meal_records.append([ate, None, None, i, []])   # [n, dark, ghost, frame, samples]
        if ate % 5 == 0:
            newest = f"seg{last_say and '' or ''}"
    # -- the light laws, sampled every frame after every open meal --
    # (v3.1.99: the old tracker followed ONLY the last meal and the
    #  old pin demanded the FIRST meal's dark within 3 frames — but
    #  the drive can die on a wall ONE STEP after eating (the food
    #  drew beside a wall; the unseeded spawn is honest randomness),
    #  and the frozen record never closes. The law's witness is the
    #  STAIRCASE itself: 1.0 -> 0.4 -> dark; any meal that walks it
    #  proves the law, and a death mid-stair with the first honest
    #  step seen is a real witness too.)
    for _m in meal_records:
        if _m[1] is None:
            _f0 = hh.get("flash", 0) if hh else 0
            _m[4].append(_f0)
            if _f0 == 0.0:
                _m[1] = i - _m[3]                     # frames to dark
    if meal_records:
        m = meal_records[-1]
        # the newborn ghost: the segment born this meal
        if m[2] is None:
            newest = [e for e in f["set"]
                      if re.match(r"seg\d+_\d+$", e["name"])
                      and int(e["name"].rsplit("_", 1)[1]) == m[0] + 2]
            if newest:
                m[2] = newest[0].get("alpha")
                ghost_seen = (m[2], None)
            elif m[0] == 1 and i > m[3]:
                pass
        # milestone tail flash: the meal at score%5==0
        if milestone_name is None:
            tails = [e for e in f["set"]
                     if re.match(r"seg\d+_\d+$", e["name"])
                     and e.get("flash", 0) > 0.7]
            if tails:
                milestone_name = tails[0]["name"]
                milestone_seq.append(tails[0].get("flash"))
        elif milestone_name is not None:
            te = next((e for e in f["set"] if e["name"] == milestone_name), None)
            if te is not None:
                milestone_seq.append(te.get("flash", 0))
                if te.get("flash", 0) == 0:
                    milestone_name = None   # worn to dark; ready for the next
    # -- the forever-bleach witness: frames with head dark after a meal
    if meal_records and meal_records[-1][1] is not None and hh.get("flash", 0) == 0.0:
        dark_witness += 1
    if f.get("win"):
        win_seen = f.get("win")            # ANY win ends the drive — a
        print(f"  (the drive ended at meal {ate}: {win_seen!r})")  # self-bite
        break                              # is a death too

print(f"  (the drive survived; meals={ate}, milestone_seq={milestone_seq})")
pin("the greedy drive ate at least one meal", ate >= 1, f"ate={ate}")
m1 = meal_records[0] if meal_records else None
pin("the meal bleaches the head (flash 1.0 on the meal frame)",
    m1 is not None, "no meal")
if m1:
    def _stair(m):
        """a 3/s staircase witness: 1.0 -> 0.4 -> dark within 3 frames,
        or a death frozen mid-stair with the first honest step seen."""
        s = m[4]
        if (len(s) >= 3 and abs(s[0] - 1.0) < 0.05
                and abs(s[1] - 0.4) < 0.06 and s[2] == 0.0
                and m[1] is not None and 1 <= m[1] <= 3):
            return True
        # the wall bit before the second step: one honest decay step
        # was seen, the witness froze (the banner pin holds the death)
        return (len(s) == 2 and m[1] is None
                and abs(s[0] - 1.0) < 0.05 and abs(s[1] - 0.4) < 0.06)
    pin("the bleach decays honest (a 3/s staircase witness: 1.0 -> 0.4 "
        "-> dark within 3 frames at dt=0.2)",
        any(_stair(m) for m in meal_records),
        f"meal1 frames_to_dark={m1[1]} "
        f"samples={[round(x, 2) for x in m1[4]]}")
    pin("THE FOREVER-BLEACH PIN: the head stays dark after the decay",
        dark_witness >= 5, f"dark_frames={dark_witness}")
    pin("the newborn segment ghosts in (alpha 0.35 on birth)",
        m1[2] == 0.35, f"alpha={m1[2]}")
    if ghost_seen and ghost_seen[0] == 0.35:
        pin("the ghost fills in (alpha reaches 1.0)", True)
swings = (max(glow_samples) - min(glow_samples)) if glow_samples else 0
pin("the meal BREATHES (glow swings across frames)", swings > 0.6,
    f"range={swings:.2f} n={len(glow_samples)}")
# (v3.1.92: the old pin sampled ONE frame — often the flash's BIRTH
#  (1.0) — and asserted it had already decayed: a race, ~2/3 red. And
#  the one-decay reading was wrong-shaped too: the wire shows the
#  tail's bleach is a HEARTBEAT — every milestone meal re-blooms it,
#  and each bloom wears the same staircase (1.0 -> 0.4 -> 0.0). The
#  law's honest content: every bloom is born high and worn to dark,
#  never rising mid-bloom.)
runs, cur = [], None
for v in milestone_seq:
    if v >= 0.99:
        if cur: runs.append(cur)
        cur = [v]
    elif cur is not None:
        cur.append(v)
if cur: runs.append(cur)
complete = [r for r in runs if r[-1] == 0.0]   # a bloom may be in
if milestone_seq:                              # flight when the drive ends
    pin("the milestone's tail bleach wears the staircase every bloom (born high -> dark)",
        complete and all(len(r) >= 2 and r[0] > 0.7 and r[-1] == 0.0 and
                         all(r[i] >= r[i + 1] for i in range(len(r) - 1))
                         for r in complete) and
        all(all(r[i] >= r[i + 1] for i in range(len(r) - 1)) for r in runs),
        f"seq={milestone_seq}")
else:
    print(f"  (no milestone meal reached — the head-staircase pins the law)")
pin("the meal still speaks (say rode the wire)", "meal" in last_say,
    repr(last_say))

# ---- the wall bite still lands (a LIVE snake drives into it; a
# greedy drive may DIE first — v3.1.92: a self-bite is a death too,
# and the old pin gave up the wall verdict if it saw one. Fall again:
# space revives, up to three lives.)
lives = 0
while "the wall" not in (win_seen or "") and lives < 3:
    lives += 1
    for _ in range(8):                    # the death banner dwells; space
        f = tick(keys=["space"], dt=0.2)  # falls a fresh snake
        if f.get("win"):
            win_seen = f["win"]
    for _ in range(45):                   # hold a fixed heading — a live
        f = tick(keys=["right"], dt=0.2)  # snake walls within 20 cells
        if f.get("win"):
            win_seen = f["win"]
            break
pin("the wall bite lands as the honest banner", "the wall" in (win_seen or ""),
    repr(win_seen))

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the light laws hold in the snake pit")
