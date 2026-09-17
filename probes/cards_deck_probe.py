#!/usr/bin/env python3
"""probe for sdk/examples/cards.py — THE DECK LAW (v3.1.74).

The deck is real now: forty cards shuffled by their own named stream,
dealt five at a hand, the muck growing, the reshuffle speaking:

  1. the scene still carries 12 entities (the deck law adds no
     furniture) and the muck label starts HONEST — v3.1.80's deal
     refresh means it reads the true count: 'muck: 0 · deck: 35';
  2. the first hand is EXACTLY the stream's first five draws —
     random.Random("the deck's order") over the forty, shuffled;
  3. the last play of a hand deals the next five: the fresh hand is
     the stream's draws 6-10, the deck count reads 30, and the ghost
     clock re-runs (the fresh hand's alpha is born at 0.15);
  4. the score arithmetic rides the replicated stream: red pays 4 and
     a mult, black pays 2 — the title's text is EXACTLY what the
     replicated run computes;
  5. at the 40th play the deck runs dry: the muck returns, the
     reshuffle stream ('the deck's reshuffle') reorders it, and the
     title SPEAKS '· reshuffled' — born once, not stuck;
  6. the post-reshuffle hand is EXACTLY the reshuffled deck's first
     five draws, the muck label reads 'muck: 0 · deck: 35', and the
     ghost law re-runs again.
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

# the replicated stream: the probe knows every card before the game deals
DECK = [(r, s) for s in SUITS for r in RANKS]
RD = random.Random("the deck's order")
RD.shuffle(DECK)
muck = []
pos = 0                                    # draw pointer into DECK
RS = random.Random("the deck's reshuffle") # advanced only at the reshuffle

env = dict(os.environ)
env["PYTHONPATH"] = os.path.join(REPO, "sdk")
p = subprocess.Popen(["python3", os.path.join(REPO, "sdk", "examples", "cards.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

_q = queue.Queue()
CONSOLE = []
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
            CONSOLE.append(ln.strip()[:120])
            continue
    return None

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

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

send({"t": "hello", "w": 120, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents0 = {e["name"]: e for e in scene["entities"]}
pin("the scene still carries 12 entities (the deck adds no furniture)",
    len(scene["entities"]) == 12, str(len(scene["entities"])))
pin("the muck label starts honest (the deal refreshes it now)",
    ents0["hand"]["text"] == "muck: 0 · deck: 35", repr(ents0["hand"]["text"]))
hand1 = DECK[pos:pos + 5]; pos += 5
pin("the first hand is EXACTLY the stream's first five draws",
    all(ents0[f"ct{i}"]["text"] == r + s for i, (r, s) in enumerate(hand1)),
    str([ents0[f"ct{i}"]["text"] for i in range(5)]) + " vs " + str(hand1))

def play_hand(n):
    """play all five seats; return (title, muck_lbl, alphas, hand_texts)
    from the frame after the LAST play (the deal rides that frame)"""
    chips_t, mult_t = 0, 1
    global pos, muck
    for seat in range(5):
        if seat > 0:
            tick(["right"])
        r, s = DECK[pos - 5 + seat]        # the seat's card (this hand)
        if s in "♥♦":
            chips_t += 4; mult_t += 1
        else:
            chips_t += 2
        muck.append(r + s)
        ents, pkt = tick(["space"])
        if seat == 4:
            pos += 5                       # the deal consumed the next five
            return ents, pkt, chips_t, mult_t
    raise AssertionError("unreachable")

# ---- hand 1: five plays; the deal to hand 2 rides the 5th play ----
ents, pkt, chips_t, mult_t = play_hand(1)
hand2 = DECK[pos - 5:pos]
title = ents["title"]["text"]
exp = (f"BLATRO — played {hand1[4][0]}{hand1[4][1]} · "
       f"score: {chips_t} x {mult_t} · deck 30")
pin("the title after hand 1 is EXACTLY the replicated arithmetic",
    title == exp, f"{title!r} vs {exp!r}")
pin("the fresh hand is the stream's draws 6-10",
    all(ents[f"ct{i}"]["text"] == r + s for i, (r, s) in enumerate(hand2)),
    str([ents[f"ct{i}"]["text"] for i in range(5)]))
pin("the deck count reads 30 and the muck 5",
    ents["hand"]["text"] == "muck: 5 · deck: 30", repr(ents["hand"]["text"]))
alphas = [ents[f"card{i}"].get("alpha") for i in range(5)]
pin("the ghost clock re-ran (the fresh hand born at alpha 0.15)",
    all(abs(a - 0.15) < 1e-9 for a in alphas), str(alphas))

# ---- hands 2-6: walk toward the dry deck (25 more plays) ----
for h in range(2, 7):
    ents, pkt, chips_t, mult_t = play_hand(h)
pin("after hand 6 the deck holds its last five (muck 30 · deck 5)",
    ents["hand"]["text"] == "muck: 30 · deck: 5", repr(ents["hand"]["text"]))

# ---- hand 7: dealt from the deck's last five (muck 35 · deck 0) ----
ents, pkt, chips_t, mult_t = play_hand(7)
pin("after hand 7 the deck has dealt its last five (muck 35 · deck 0)",
    ents["hand"]["text"] == "muck: 35 · deck: 0", repr(ents["hand"]["text"]))

# ---- hand 8: its 5th play finds the deck dry — THE RESHUFFLE ----
ents, pkt, chips_t, mult_t = play_hand(8)
title = ents["title"]["text"]
pin("THE RESHUFFLE SPEAKS: the title carries '· reshuffled'",
    "· reshuffled" in title, repr(title))
# the replicated reshuffle: the muck returns in played order, the
# reshuffle stream reorders it, the hand takes the first five
returned = list(muck)
RS.shuffle(returned)
exp_hand = returned[:5]
pin("the post-reshuffle hand is EXACTLY the reshuffled deck's first five",
    all(ents[f"ct{i}"]["text"] == c for i, c in enumerate(exp_hand)),
    str([ents[f"ct{i}"]["text"] for i in range(5)]) + " vs " + str(exp_hand))
pin("the muck label reads 'muck: 0 · deck: 35' after the return",
    ents["hand"]["text"] == "muck: 0 · deck: 35", repr(ents["hand"]["text"]))
alphas = [ents[f"card{i}"].get("alpha") for i in range(5)]
pin("the ghost law re-runs after the reshuffle too (alpha 0.15)",
    all(abs(a - 0.15) < 1e-9 for a in alphas), str(alphas))

# the say is born once, not stuck: one more play speaks plain
tick(["right"])
ents, pkt = tick(["space"])
pin("the say is born once — the next play's title speaks plain",
    "· reshuffled" not in ents["title"]["text"],
    repr(ents["title"]["text"]))

p.kill()
print()
print("child console (deals):")
for c in CONSOLE:
    if c.startswith("dealt") or "Traceback" in c or "Error" in c:
        print("  ", c)
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the deck is real: forty cards dealt from a")
print("named stream, the muck growing, the dry deck returning through")
print("its own reshuffle stream, the say born once, the ghost re-run.")
