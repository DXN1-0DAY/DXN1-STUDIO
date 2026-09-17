#!/usr/bin/env python3
"""probe for sdk/examples/cards.py — THE DECK'S LOW LIGHT (v3.1.80).

The hand label wears the countdown: the deck drains five a hand, and
the label's glow speaks what the numbers whisper:

  1. hands dealt above ten cards are QUIET (glow 0) — the first five
     hands all sit there (deck 35 down to 15);
  2. the hand dealt at ten cards wears the FAINT RING (glow 1) —
     the muck's return is two hands away;
  3. the hands dealt at FIVE — and at the last dregs (deck 0) —
     burn BRIGHTER (glow 2): the muck's return is at hand;
  4. the reshuffle's deal (the muck back, deck 35) pours the quiet
     back (glow 0);
  5. the light is a steady state, not a flash: it holds unchanged
     through the mid-hand plays;
  6. and the label's count stays honest at every step.
"""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, time, threading, queue, random

REPO = _HOME
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
SUITS = ["♠", "♥", "♦", "♣"]

DECK = [(r, s) for s in SUITS for r in RANKS]
RD = random.Random("the deck's order")
RD.shuffle(DECK)
pos = 0                                    # the draw pointer

env = dict(os.environ)
env["PYTHONPATH"] = os.path.join(REPO, "sdk")
p = subprocess.Popen(["python3", os.path.join(REPO, "sdk", "examples", "cards.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

_q = queue.Queue()
def _pump():
    for ln in p.stdout:
        _q.put(ln)
threading.Thread(target=_pump, daemon=True).start()

_raw = []
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
            _raw.append(ln.rstrip()[:160])
            continue
    raise AssertionError(f"child stalled: {list(_raw[-8:])}")

def tick(keys=None, dt=0.05):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": "", "hits": []})
    while True:
        pkt = read()
        if pkt is None:
            raise AssertionError("no frame — child stalled")
        if pkt.get("t") == "frame":
            return {e["name"]: e for e in pkt["set"]}, pkt

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

send({"t": "hello", "w": 120, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents0 = {e["name"]: e for e in scene["entities"]}
pin("the scene still carries twelve entities (the light adds no "
    "furniture)", len(ents0) == 12, str(len(ents0)))
pin("the first hand is born quiet (deck 35, glow 0)",
    ents0["hand"].get("glow", 0) == 0 and
    ents0["hand"]["text"] == "muck: 0 · deck: 35",
    f"glow={ents0['hand'].get('glow')} {ents0['hand']['text']!r}")

def play_hand():
    """play all five seats; return the frame after the LAST play (the
    deal rides that frame)"""
    global pos
    for seat in range(5):
        if seat > 0:
            tick(["right"])
        ents, pkt = tick(["space"])
        if seat == 4:
            pos += 5                       # the deal consumed the next five
            return ents
    raise AssertionError("unreachable")

# hands 2-5: the deck walks 30 -> 15, every hand quiet
quiet_ok, quiet_detail = True, []
for n in range(2, 6):
    ents = play_hand()
    g = ents["hand"].get("glow", 0)
    if g != 0:
        quiet_ok = False
    quiet_detail.append(f"h{n}:g{g}/{ents['hand']['text']}")
pin("hands 2-5 stay quiet while the deck runs 30 -> 15 (glow 0)",
    quiet_ok, str(quiet_detail))

# mid-hand steadiness: the light is a state, not a flash
ents = play_hand()                         # hand 6 dealt at deck 10 —
pin("the hand dealt at TEN wears the faint ring (glow 1)",
    ents["hand"].get("glow", 0) == 1 and
    ents["hand"]["text"] == "muck: 25 · deck: 10",
    f"glow={ents['hand'].get('glow')} {ents['hand']['text']!r}")
tick(["right"])
ents_mid, _ = tick(["space"])              # a mid-hand play — no deal
pin("and the light holds steady through the hand's plays",
    ents_mid["hand"].get("glow", 0) == 1,
    f"glow={ents_mid['hand'].get('glow')}")

# finish hand 6; its LAST play triggers the deal at deck FIVE —
# capture that frame: the light burns brighter
for seat in range(3):
    tick(["right"])
    tick(["space"])
tick(["right"])
ents_five, _ = tick(["space"])
pin("the hand dealt at FIVE burns brighter (glow 2)",
    ents_five["hand"].get("glow", 0) == 2 and
    ents_five["hand"]["text"] == "muck: 30 · deck: 5",
    f"glow={ents_five['hand'].get('glow')} {ents_five['hand']['text']!r}")

# hand 8: played from the last dregs — its deal leaves the deck at
# ZERO and the light stays bright: the return is at hand
ents_dregs = play_hand()
pin("the dregs hand (deck 0) stays bright — the return is at hand",
    ents_dregs["hand"].get("glow", 0) == 2 and
    ents_dregs["hand"]["text"] == "muck: 35 · deck: 0",
    f"glow={ents_dregs['hand'].get('glow')} {ents_dregs['hand']['text']!r}")

# hand 9: its last play dries the deck — the muck returns through the
# reshuffle and the quiet pours back
ents_re = play_hand()
pin("the reshuffle's deal pours the quiet back (deck 35, glow 0)",
    ents_re["hand"].get("glow", 0) == 0 and
    ents_re["hand"]["text"] == "muck: 0 · deck: 35",
    f"glow={ents_re['hand'].get('glow')} {ents_re['hand']['text']!r}")

# hand 10: the returned deck drains honestly — five more gone, quiet
ents_after = play_hand()
pin("and the returned deck drains again, still quiet (deck 30)",
    ents_after["hand"].get("glow", 0) == 0 and
    ents_after["hand"]["text"] == "muck: 5 · deck: 30",
    f"glow={ents_after['hand'].get('glow')} {ents_after['hand']['text']!r}")

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the deck's low light: quiet, faint ring at")
print("ten, brighter at the last hand, quiet again when the muck")
print("returns — the countdown you can see from across the table.")
