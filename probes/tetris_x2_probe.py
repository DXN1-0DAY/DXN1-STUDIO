#!/usr/bin/env python3
"""probe for sdk/examples/tetris.js — THE STREAK LAW (v3.1.70), part 2:
THE X2 ON THE REAL WIRE, from the EMPTY well (R27).

The 90-event script (tetris_x2_script.json, sim-verified tick-exact
from a fresh game) plays the R25 base's first 12 slams, then a
construction run whose 14th and 15th locks clear BACK-TO-BACK — the
streak x2 — and, after dry locks, an isolated clear (the reset proof):

  1. the first clear says plain: "line · lv 1" — combo x1, banner
     born whole (alpha 1, glow 2);
  2. the very next lock clears too: the say grows "· combo ×2" and
     the banner is born BRIGHTER — glow 3 = 2 + min(x-1, 6) at x2;
  3. the x2 banner wears the honest 0.15/tick (3/s at dt 0.05) —
     ten watched waits, 3.0 -> 1.5, one ledger;
  4. the dry locks between the pair and the reset speak nothing;
  5. the isolated clear says PLAIN AGAIN — "line · lv 1", glow 2:
     the dry lock broke the streak and the ledger said so;
  6. the run tops out deterministically and 'r' revives a fresh
     well, the ledger zeroed with it.
"""
# The probes COME HOME (v3.1.90): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (four drift
# catches on record). Canonical law pins: probes/*_probe.py, one family
# per round, tetris first (the driftiest).
import json, subprocess, sys, os, time, threading, queue

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tetris_x2_script.json")))
EVENTS = SCRIPT["events"]
CLEAR_EV = SCRIPT["clear_ev"]                 # [57, 64, 89]
X1_EV, X2_EV, RESET_EV = CLEAR_EV
WEAR_A, WEAR_B = SCRIPT["wear_start"], SCRIPT["wear_end"]

WIRE = {"turn": "jump", "left": "left", "right": "right",
        "space": "space", "wait": None}

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

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

send({"t": "hello", "w": 100, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 23 entities", len(scene["entities"]) == 23,
    str(len(scene["entities"])))

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

# ---- the scripted run: one event = one tick, every frame watched ----
says = {}                                 # event idx -> say text
glow_at = {}                              # event idx -> banner glow
alpha_at = {}
for i, ev in enumerate(EVENTS):
    k = WIRE[ev]
    ents, pkt = tick([k] if k else [])
    if pkt.get("say"):
        says[i] = str(pkt.get("say"))
    if "banner" in ents:
        glow_at[i] = ents["banner"].get("glow")
        alpha_at[i] = ents["banner"].get("alpha")

pin("the first clear speaks plain: 'line · lv 1' (x1)",
    says.get(X1_EV) == "line · lv 1", repr(says.get(X1_EV)))
pin("the x1 banner is born whole (alpha 1, glow 2)",
    alpha_at.get(X1_EV) == 1 and glow_at.get(X1_EV) == 2,
    f"alpha={alpha_at.get(X1_EV)} glow={glow_at.get(X1_EV)}")
pin("THE X2: the very next lock clears and the say carries "
    "'· combo ×2'",
    says.get(X2_EV) == "line · lv 1 · combo ×2", repr(says.get(X2_EV)))
pin("the x2 banner is born BRIGHTER (glow 3 = 2 + min(x-1,6))",
    glow_at.get(X2_EV) == 3 and alpha_at.get(X2_EV) == 1,
    f"glow={glow_at.get(X2_EV)} alpha={alpha_at.get(X2_EV)}")

# the wear staircase across the watched waits
wear = [glow_at.get(i) for i in range(WEAR_A, WEAR_B + 1)]
steps = [round(wear[i - 1] - wear[i], 6) for i in range(1, len(wear))
         if wear[i - 1] is not None and wear[i] is not None]
pin("the x2 bloom wears 0.15/tick across 10 watched waits (3.0 -> 1.5)",
    len(wear) == 10 and abs(wear[0] - 2.85) < 0.011 and
    abs(wear[-1] - 1.5) < 0.011 and
    all(abs(s - 0.15) < 0.0011 for s in steps), f"{wear}")

dry_silent = all(i not in says for i in range(X2_EV + 1, RESET_EV))
pin("the dry locks between pair and reset speak nothing", dry_silent,
    str({i: says[i] for i in sorted(says) if X2_EV < i < RESET_EV}))
pin("THE RESET: the isolated clear says PLAIN again ('line · lv 1', "
    "glow 2) — the dry lock broke the streak",
    says.get(RESET_EV) == "line · lv 1" and glow_at.get(RESET_EV) == 2,
    f"say={says.get(RESET_EV)} glow={glow_at.get(RESET_EV)}")

# ---- the tail: straight slams top out; 'r' revives from zero ----
seen_win = None
for _ in range(260):
    ents, pkt = tick(["space"])
    seen_win = seen_win or str(pkt.get("win") or "")
    if seen_win:
        break
pin("the run tops out deterministically",
    seen_win is not None and "TOPPED OUT" in seen_win, repr(seen_win))

ents, pkt = tick(chars="r")
ents, pkt = tick([])
cells_after = [n for n in ents if n.startswith("cell")]
pin("'r' revives a fresh well (no locked cells)", len(cells_after) == 0,
    str(cells_after[:6]))
pin("the fresh well speaks nothing (banner dark)",
    ents["banner"].get("visible", 0) == 0, str(ents["banner"].get("visible")))
pin("the hud is back to total 0", "· 0 ·" in ents["hud"]["text"],
    ents["hud"]["text"])

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the streak law's full arc on the real wire:")
print("x1 speaks plain, the back-to-back clear carries '· combo ×2'")
print("with the brighter bloom, the wear is one honest ledger, the")
print("dry lock breaks the streak, and the next clear says plain again.")
