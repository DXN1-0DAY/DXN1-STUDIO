#!/usr/bin/env python3
"""probe for sdk/examples/tetris.js — THE STREAK LAW (v3.1.70), part 1.

Pins the reachable half of the streak law on the real wire, over the
R25-verified slam script ([-5,-1,1,-5,-5,-5,-5,-5,-4,0,1,0,0,2] — its
14th slam clears row 15; the x1 path is untouched by the combo edit):

  1. the lone clear speaks plain: say "line · lv 1" — combo x1, no
     suffix, the banner BORN WHOLE (alpha 1, glow 2 — a lone clear
     keeps the honest bloom; the streak's brightness starts at x2);
  2. the banner's bloom wears the honest 0.15/tick (3/s at dt 0.05);
  3. the banner wears to invisible in the say's own 1.6 s — never a
     flash-forever;
  4. the dry slams after the clear leave the well silent (no voice
     without a clear);
  5. the run eventually tops out deterministically and 'r' revives a
     fresh well — the ledger reset() zeroes.

(The x2-suffix and reset-visibility pins ride on the scripted
CONSECUTIVE-PAIR replay — the build-phase search is mapped in
tetris_combo_search3.py / tetris_combo_build.py and lands next round.)
"""
# The probes COME HOME (v3.1.90): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (four drift
# catches on record). Canonical law pins: probes/*_probe.py, one family
# per round, tetris first (the driftiest).
import json, subprocess, sys, os, time, threading, queue

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = [-5, -1, 1, -5, -5, -5, -5, -5, -4, 0, 1, 0, 0, 2]

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
seen_win = None                           # the win rides ONE frame — every
                                          # phase must be watching for it
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

send({"t": "hello", "w": 100, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 23 entities (the streak adds no furniture)",
    len(scene["entities"]) == 23, str(len(scene["entities"])))

# the base script: dc slides then slam, per piece; gravity never
# misplaces anything (each inter-slam gap <= 0.30 s; the sim's tick
# law says a stray fire merely drops the piece one row mid-slide)
clear_frame = None
wear_seq = []
for dc in BASE:
    for _ in range(abs(dc)):
        ents, pkt = tick(["left" if dc < 0 else "right"])
    ents, pkt = tick(["space"])
    if pkt.get("say"):
        clear_frame = (str(pkt.get("say")), ents["banner"].get("glow"),
                       ents["banner"].get("alpha"))
        break
pin("the clear speaks: 'line · lv 1' (combo x1 — no suffix)",
    clear_frame is not None and clear_frame[0] == "line · lv 1",
    repr(clear_frame))
pin("the banner is BORN WHOLE (alpha 1)", clear_frame[2] == 1,
    str(clear_frame[2]))
pin("a lone clear keeps the honest bloom 2", clear_frame[1] == 2,
    str(clear_frame[1]))

# the wear: 0.15/tick
for _ in range(10):
    ents, pkt = tick([])
    wear_seq.append(ents["banner"].get("glow"))
steps = [round(wear_seq[i - 1] - wear_seq[i], 6) for i in range(1, len(wear_seq))]
pin("the bloom wears 0.15/tick (the house's 3/s at dt 0.05)",
    len(wear_seq) == 10 and abs(wear_seq[0] - 1.85) < 0.011 and
    all(abs(s - 0.15) < 0.0011 for s in steps), f"{wear_seq}")

# dry slams: the STREAK's voice stays silent — no clear callout, no
# combo suffix (the dregs' air-voice is the rails' law, v3.1.89: a
# dry lock that pushes the stack into the last rows speaks as the
# air, not as the streak)
STREAK_WORDS = ("line", "double", "triple", "TETRIS!", "combo")
dry_says = []
for dc in (0, 0, 0):
    ents, pkt = tick(["space"])
    if pkt.get("say"):
        dry_says.append(str(pkt.get("say")))
    seen_win = seen_win or str(pkt.get("win") or "")
pin("dry locks speak nothing from the streak (the dregs' air-voice is another law)",
    dry_says == ["the well runs shallow — the last air burns"],
    repr(dry_says))

# walk out the say's own 1.6 s dwell: invisible, no flash-forever
for _ in range(24):
    ents, pkt = tick([])
    seen_win = seen_win or str(pkt.get("win") or "")
pin("the banner wears to invisible in the say's own dwell",
    ents["banner"].get("visible") == 0 and ents["banner"].get("alpha", 1) == 0,
    f"visible={ents['banner'].get('visible')} alpha={ents['banner'].get('alpha')}")

# the run tops out deterministically under straight-down slams (the
# win may ride a gravity-locked spawn during ANY wait — every phase
# watches for it)
for _ in range(220):
    ents, pkt = tick(["space"])
    seen_win = seen_win or str(pkt.get("win") or "")
    if seen_win:
        break
pin("the run tops out deterministically", seen_win is not None and
    "TOPPED OUT" in seen_win, repr(seen_win))

# 'r' rides CHARS (the wire's held keys never carry letters) and
# revives a fresh well — reset() zeroed the ledger
ents, pkt = tick(chars="r")
ents, pkt = tick([])                     # the hud pays one tick late
cells_after = [n for n in ents if n.startswith("cell")]
pin("'r' revives a fresh well (no locked cells)",
    len(cells_after) == 0, str(cells_after[:6]))
pin("the fresh well speaks nothing (banner dark)",
    ents["banner"].get("visible", 0) == 0, str(ents["banner"].get("visible")))
pin("the hud is back to total 0", "· 0 ·" in ents["hud"]["text"],
    ents["hud"]["text"])

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the streak ledger lives: lone clears speak plain,")
print("the banner wears honestly, and r falls again from zero.")
