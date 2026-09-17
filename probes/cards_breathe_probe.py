#!/usr/bin/env python3
"""probe for sdk/examples/cards.py — THE HAND REMEMBERS (re-homed v3.1.93).

The memory probe, rebuilt on the replicated stream. The R22-era
external version was broken twice over: it spawned its child on
relative paths (it only ever ran from its birth directory) and its
card identities predated the deck law — it expected 2♠ under seat 0.
The stream taught the truth: the first hand is ALL RED (6♥ 5♦ 8♦
5♥ 2♥) and the first BLACK card leads hand two (4♠) — so both pay
laws are pinned on real, computed cards:

  1. the scene carries 12 entities; the hand is born ghosting
     (alpha 0.15) with card0 lit and the muck label honest;
  2. the hand ghosts in on ONE shared clock — cards and ranks
     mirrored bit for bit, the drift only rises, it lands at 1.0;
  3. the red play (6♥) flashes full white, the bounty speaks
     (glow 3) and the title carries the replicated arithmetic;
  4. the flash and the bounty cool down their honest staircases
     on the SAME ticks, bit for bit (3/s down, 6/s down);
  5. the spent seat wears 0.5 (card AND rank), the muck label
     remembers, the unspent hand stays full;
  6. the glow hand follows the selection and the seat lifts;
  7. the hand's last play deals hand two — the fresh hand is born
     at 0.15 again, the accumulated arithmetic rides the title;
  8. the BLACK play (4♠) pays the black price and the bounty
     STAYS DARK — and the black seat remembers its 0.5 too.
"""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.93): rescued from the external scripts dir
# where relative spawn paths kept it a prisoner of its birth directory.
# Canonical law pins: probes/*_probe.py, walked by gate 8.
import json, subprocess, sys, os, time, threading, queue, random

REPO = _HOME
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
SUITS = ["♠", "♥", "♦", "♣"]

# the replicated stream — the probe knows every card before the deal
DECK = [(r, s) for s in SUITS for r in RANKS]
RD = random.Random("the deck's order")
RD.shuffle(DECK)
HAND1 = DECK[0:5]                          # 6♥ 5♦ 8♦ 5♥ 2♥ — all red
HAND2 = DECK[5:10]                         # 4♠ leads — the first black

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

def tick(keys=None, dt=0.1):
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
pin("the scene carries 12 entities", len(scene["entities"]) == 12,
    str(len(scene["entities"])))
pin("the first hand matches the replicated stream",
    all(ents0[f"ct{i}"]["text"] == r + s for i, (r, s) in enumerate(HAND1)),
    str([ents0[f"ct{i}"]["text"] for i in range(5)]))
pin("the hand is born ghosting (alpha 0.15) and card0 is lit",
    abs(ents0["card0"].get("alpha", -1) - 0.15) < 1e-9 and
    ents0["card0"].get("glow", 0) == 6 and
    all(ents0[f"card{i}"].get("glow", 0) == 0 for i in range(1, 5)),
    f"a={ents0['card0'].get('alpha')} g={ents0['card0'].get('glow')}")
pin("the muck label starts honest",
    ents0["hand"]["text"] == "muck: 0 · deck: 35", repr(ents0["hand"]["text"]))

# ---- 2. the shared ghost clock: bit for bit, rise only, lands 1.0 ----
ghostT = 0.0
worst = 0.0
rise_ok = True
prev = -1.0
landed = False
for k in range(1, 13):
    ents, f = tick()
    ghostT = min(1.0, ghostT + 0.1 / 0.9)      # the game's own recurrence
    A = 0.15 + 0.85 * ghostT
    vals = [ents["card0"].get("alpha"), ents["ct0"].get("alpha"),
            ents["card4"].get("alpha"), ents["ct4"].get("alpha")]
    if any(v is None for v in vals):
        rise_ok = False
        break
    worst = max(worst, max(abs(v - A) for v in vals))
    if vals[0] < prev - 1e-12:
        rise_ok = False                        # the drift must never sink
    prev = vals[0]
    if k >= 10 and vals[0] == 1.0:
        landed = True
pin("the hand ghosts in on ONE shared clock (cards + ranks, worst err %.1e)"
    % worst, rise_ok and worst == 0.0, f"worst={worst}")
pin("the drift only rises and lands at full alpha (1.0)", rise_ok and landed,
    f"a0={ents['card0'].get('alpha')}")

# ---- 3. the red play: 6♥ flashes, the bounty speaks ----
ents, f = tick(["space"])                      # seat 0 plays 6♥ (red)
r0, s0 = HAND1[0]
pin("the landing flash speaks full white (1.0) on the play frame",
    ents["card0"].get("flash") == 1.0, str(ents["card0"].get("flash")))
pin("the bounty speaks (title glow 3)",
    ents["title"].get("glow") == 3, str(ents["title"].get("glow")))
pin("the title carries the replicated arithmetic (4 x 2, played 6♥)",
    ents["title"]["text"] ==
    f"BLATRO — played {r0}{s0} · score: 4 x 2 · deck 35",
    repr(ents["title"]["text"]))

# ---- 4. both staircases ride the same ticks, bit for bit ----
exp_f, exp_g = 1.0, 3.0
worst_f = worst_g = 0.0
for k in range(5):
    ents, f = tick()
    exp_f = max(0.0, exp_f - 3 * 0.1)          # the flash decays 3/s
    exp_g = max(0.0, exp_g - 6 * 0.1)          # the bounty cools 6/s
    worst_f = max(worst_f, abs(ents["card0"].get("flash", 0) - exp_f))
    worst_g = max(worst_g, abs(ents["title"].get("glow", 0) - exp_g))
pin("the flash decays down the honest staircase (0.7 … 0.0)",
    worst_f == 0.0 and exp_f == 0.0, f"worst={worst_f}")
pin("the bounty cools down its honest staircase (2.4 … 0.0)",
    worst_g == 0.0 and exp_g == 0.0, f"worst={worst_g}")

# ---- 5. the spent seat remembers, the muck remembers ----
pin("the spent card wears alpha 0.5",
    ents["card0"].get("alpha") == 0.5, str(ents["card0"].get("alpha")))
pin("the spent rank wears it too",
    ents["ct0"].get("alpha") == 0.5, str(ents["ct0"].get("alpha")))
pin("the unspent hand stays full (1.0)",
    ents["card1"].get("alpha") == 1.0 and ents["card2"].get("alpha") == 1.0,
    f"{ents['card1'].get('alpha')}, {ents['card2'].get('alpha')}")
pin("the muck label remembers the play",
    ents["hand"]["text"] == "muck: 1 · deck: 35", repr(ents["hand"]["text"]))

# ---- 6. the glow hand follows, the seat lifts ----
tick(["right"])
ents, f = tick()                               # the key tick shows the OLD draw
pin("the glow follows right (card1 lit, card0 dark)",
    ents["card1"].get("glow") == 6 and ents["card0"].get("glow", 0) == 0,
    f"g1={ents['card1'].get('glow')} g0={ents['card0'].get('glow', 0)}")
pin("the selected seat lifts (the rank rises with it)",
    ents["ct1"].get("y") == 44 // 2 - 5 and ents["ct0"].get("y") == 44 // 2 - 3,
    f"y1={ents['ct1'].get('y')} y0={ents['ct0'].get('y')}")

# ---- 7. play 5♦ (red), then spend the hand — the deal rides ----
ents, f = tick(["space"])
pin("the second red play pays its replicated price (8 x 3)",
    ents["title"].get("glow") == 3 and
    "score: 8 x 3" in ents["title"]["text"], repr(ents["title"]["text"]))
for seat in (2, 3, 4):
    tick(["right"]); tick([])
    ents, f = tick(["space"])
r4, s4 = HAND1[4]
pin("the hand's last play DEALS: the fresh hand is born at 0.15",
    all(abs(ents[f"card{i}"].get("alpha", -1) - 0.15) < 1e-9 for i in range(5)),
    str([ents[f"card{i}"].get("alpha") for i in range(5)]))
pin("the fresh hand is the stream's draws 6-10",
    all(ents[f"ct{i}"]["text"] == r + s for i, (r, s) in enumerate(HAND2)),
    str([ents[f"ct{i}"]["text"] for i in range(5)]))
pin("the accumulated arithmetic rides the title (20 x 6, deck 30)",
    f"played {r4}{s4} · score: 20 x 6 · deck 30" in ents["title"]["text"],
    repr(ents["title"]["text"]))
pin("the muck holds the spent hand (muck: 5 · deck: 30)",
    ents["hand"]["text"] == "muck: 5 · deck: 30", repr(ents["hand"]["text"]))

# ---- 8. the BLACK play: 4♠ pays the black price, the bounty stays dark ----
# the last red play's bounty is still cooling (2.4 at the deal) — let it
# finish its staircase, then prove the black play adds NO light of its own
exp_b = ents["title"].get("glow", 0)           # 2.4 — the bounty outlives
cooled = True                                  #   the hand that earned it
for k in range(5):
    ents, f = tick()
    exp_b = max(0.0, exp_b - 6 * 0.1)
    if abs(ents["title"].get("glow", 0) - exp_b) > 1e-12:
        cooled = False
pin("the red bounty cools across the deal into the fresh hand (2.4 … 0)",
    cooled and exp_b == 0.0 and ents["title"].get("glow", 0) == 0.0,
    f"exp={exp_b} got={ents['title'].get('glow')}")
ents, f = tick(["space"])                      # seat 0 plays 4♠ (black)
pin("THE BLACK LAW: the bounty stays dark (glow 0)",
    ents["title"].get("glow", 0) == 0, str(ents["title"].get("glow", 0)))
pin("the black play still flashes full white",
    ents["card0"].get("flash") == 1.0, str(ents["card0"].get("flash")))
pin("the black price keeps the mult (22 x 6)",
    "score: 22 x 6" in ents["title"]["text"], repr(ents["title"]["text"]))
ents, f = tick()
pin("and the black seat remembers its 0.5 too",
    ents["card0"].get("alpha") == 0.5 and ents["ct0"].get("alpha") == 0.5 and
    ents["title"].get("glow", 0) == 0,
    f"{ents['card0'].get('alpha')}, {ents['ct0'].get('alpha')}, "
    f"{ents['title'].get('glow')}")

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the hand remembers: one ghost clock, honest")
print("staircases, spent seats at 0.5, the red bounty speaks and cools,")
print("the black price stays dark — every identity read off the stream.")
