#!/usr/bin/env python3
"""probe for sdk/examples/tetris.js — THE LAST AIR BURNS (v3.1.89).

The low-light law's FIFTH transplant (cards hand -> snake meal ->
asteroids hull -> lunar tank -> tetris rails): the rails' glow is
the headroom's countdown, read off the well's own ledger.

Pinned over the real wire with straight slams (the scout verified
the seeded bag's slam heights: 1,3,5,7,8,10,11,13,14,16 — no clears,
the streak ledger untouched, combo stays 0 throughout):

  1. birth quiet: both rails glow 0 on an empty well;
  2. quiet while the air is rich: heights 1..8 wear glow 0;
  3. THE RING: height 10 turns the rails to glow 1 (and 11 holds it);
  4. THE BRIGHT: height 13 burns glow 2 AND the dregs speak once —
     "the well runs shallow — the last air burns";
  5. once per descent: height 14 raises no second say, the glow holds;
  6. the run tops out deterministically and 'r' pours the quiet back —
     glow 0 on a fresh well;
  7. THE RE-ARM: the second descent (a fresh bag — the seeded stream
     advances on reseed, so its ladder is its own) rings before it
     burns, and the dregs speak AGAIN — once per descent, not once
     per run — and exactly once;
  8. symmetry: rail-l and rail-r wear the same tier at every sampled
     frame.
"""
# The probes COME HOME (v3.1.90): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (four drift
# catches on record). Canonical law pins: probes/*_probe.py, one family
# per round, tetris first (the driftiest).
import json, subprocess, sys, os, time, threading, queue

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "tetris.js")],
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

def tick(keys=None, chars="", dt=0.05):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": []})
    while True:
        pkt = read()
        if pkt is None:
            raise AssertionError("no frame — child stalled")
        if pkt.get("t") == "frame":
            return {e["name"]: e for e in pkt["set"]}, pkt

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

def stack_height(ents):
    top = 16
    for nm, e in ents.items():
        if nm.startswith("cell") and nm[4:].isdigit():
            r = (e["y"] - 2) // 2
            if r < top: top = r
    return 16 - top

def rails(ents):
    return (ents["rail-l"].get("glow", 0), ents["rail-r"].get("glow", 0))

send({"t": "hello", "w": 100, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 23 entities (the law adds no furniture)",
    len(scene["entities"]) == 23, str(len(scene["entities"])))

ents, pkt = tick([])
pin("birth quiet: an empty well wears glow 0 on both rails",
    rails(ents) == (0, 0) and stack_height(ents) == 0, str(rails(ents)))

seen_win = None
says = {}                                 # slam idx -> say text
heights = {}
glow_seq = {}

def climb(idx_target):
    """slam until idx_target slams total; record says/heights/glows."""
    global seen_win
    while len(heights) < idx_target and not seen_win:
        i = len(heights) + 1
        ents, pkt = tick(["space"])
        w = str(pkt.get("win") or "")
        if w:
            seen_win = w
        heights[i] = stack_height(ents)
        glow_seq[i] = rails(ents)
        if pkt.get("say"):
            says[i] = str(pkt.get("say"))

# ---- the FIRST DESCENT ------------------------------------------------
climb(5)
pin("quiet while the air is rich: heights 1..8 wear glow 0",
    all(glow_seq[i] == (0, 0) for i in range(1, 6)) and
    heights[5] == 8, f"{heights} {glow_seq}")

climb(6)
pin("THE RING: height 10 turns both rails to glow 1",
    heights[6] == 10 and glow_seq[6] == (1, 1), f"h={heights[6]} g={glow_seq[6]}")

climb(7)
pin("the ring holds through height 11",
    heights[7] == 11 and glow_seq[7] == (1, 1), f"h={heights[7]} g={glow_seq[7]}")

climb(8)
pin("THE BRIGHT: height 13 burns glow 2 and the dregs speak ONCE",
    heights[8] == 13 and glow_seq[8] == (2, 2) and
    says.get(8) == "the well runs shallow — the last air burns",
    f"h={heights[8]} g={glow_seq[8]} say={says.get(8)!r}")

climb(9)
pin("once per descent: height 14 raises no second say, the glow holds",
    heights[9] == 14 and 9 not in says and glow_seq[9] == (2, 2),
    f"h={heights[9]} says={says} g={glow_seq[9]}")

sym_ok = all(glow_seq[i][0] == glow_seq[i][1] for i in glow_seq)
pin("symmetry: both rails wear the same tier at every sampled frame",
    sym_ok, str(glow_seq))

# ---- top-out and the quiet's return -----------------------------------
for _ in range(40):
    if seen_win: break
    ents, pkt = tick(["space"])
    w = str(pkt.get("win") or "")
    if w:
        seen_win = w
pin("the run tops out deterministically", seen_win is not None and
    "TOPPED OUT" in seen_win, repr(seen_win))

ents, pkt = tick(chars="r")
pin("'r' pours the quiet back: a fresh well wears glow 0",
    rails(ents) == (0, 0) and stack_height(ents) == 0, str(rails(ents)))

# ---- the SECOND DESCENT (the re-arm) ----------------------------------
# (the bag's seeded shuffle stream ADVANCES on reseed — reset() deals a
# fresh order from the same seed's later position, so the second climb
# is its own ladder; what the law pins is the TIERS, not the steps)
heights2, glow2, says2 = {}, {}, {}
seen_win = None
for i in range(1, 12):
    ents, pkt = tick(["space"])
    w = str(pkt.get("win") or "")
    if w:
        seen_win = w
    heights2[i] = stack_height(ents)
    glow2[i] = rails(ents)
    if pkt.get("say"):
        says2[i] = str(pkt.get("say"))
    if seen_win: break

ring_idx = next((i for i in sorted(glow2) if glow2[i] == (1, 1)), None)
bright_idx = next((i for i in sorted(glow2) if glow2[i] == (2, 2)), None)
pin("the re-armed ring: the second descent rings before it burns",
    ring_idx is not None and bright_idx is not None and ring_idx < bright_idx,
    f"ring={ring_idx} bright={bright_idx} glows={glow2}")
pin("THE RE-ARMED DREGS: the second descent speaks AGAIN at its own crossing",
    bright_idx is not None and
    says2.get(bright_idx) == "the well runs shallow — the last air burns",
    f"bright={bright_idx} says={says2}")
pin("still once per descent: exactly one dregs say in the second descent",
    sum(1 for s in says2.values() if "last air" in s) == 1, str(says2))

p.kill()
print()
if fails:
    print(f"FAIL: {len(fails)} pins red: {fails}"); sys.exit(1)
print("the last air burns: quiet rich, ring thinning, bright dregs — once per descent.")
