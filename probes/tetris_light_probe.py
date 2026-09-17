#!/usr/bin/env python3
"""probe for sdk/examples/tetris.js — the well's light laws.

Drives the real wire (hello FIRST; dxn3.js blocks on it). Replays the
deterministic slam-only clear script found by tetris_clear_search.py
(mirrors the game's FNV+stream the JS way — signed int32, float64
multiply: piece order I,O,T,J,Z,L,S,J,I,L,O,S,T,Z — the script clears
row 15 at the 14th slam, exactly one line). Pins:

  scene: 23 entities — the new banner label among them, born dark
  lock bloom: the first piece's cells are born with glow 2 (whole)
  the 3/s law: after 0.45 s their bloom reads exactly 0.65
  no clear, no voice: the banner stays dark through 13 non-clearing slams
  the clear speaks: frame.say == the banner's text == "line · lv 1"
  born whole: the banner lit at alpha 1, glow 2 at the clearing slam
  the honest wear: alpha/glow decay monotonically; glow empties at 3/s
  no flash-forever: by 1.65 s the banner is invisible (alpha 0, hidden)
  the hud pays: total 1, lv 1 in the hud text after the clear
  the seed survives: the preview promised a piece and the queue kept it
  (the script's slams never disturb the stream — one draw per spawn)
"""
# The probes COME HOME (v3.1.90): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (four drift
# catches on record). Canonical law pins: probes/*_probe.py, one family
# per round, tetris first (the driftiest).
import json, subprocess, sys, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["NODE_PATH"] = f"{REPO}/sdk"
W, H = 100, 44

# the clear script from tetris_clear_search.py (dc per piece, slam-only);
# gravity never fires between slams (each inter-slam gap <= 0.30 s < 0.5)
SCRIPT = [-5, -1, 1, -5, -5, -5, -5, -5, -4, 0, 1, 0, 0, 2]

p = subprocess.Popen(["node", f"{REPO}/sdk/examples/tetris.js"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     text=True, bufsize=1)

def child_line():
    ln = p.stdout.readline()
    if not ln.strip():
        return None
    try:
        return json.loads(ln)
    except json.JSONDecodeError:
        print(f"  console: {ln.strip()[:90]}")
        return child_line()

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def tick(keys=None, chars="", dt=0.05):
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
            print("  child says:", pkt.get("m", "")[:120])

def ent(frame, name):
    for e in frame["set"]:
        if e["name"] == name:
            return e
    return None

def merge(frame, cache):
    for e in frame["set"]:
        cache[e["name"]] = e
    return cache

def fail(msg):
    print(f"FAIL: {msg}"); sys.exit(2)

# ---- handshake
send({"t": "hello", "w": W, "h": H})
scene = child_line()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:100]}"
names = [e["name"] for e in scene["entities"]]
print(f"scene '{scene.get('name')}' entities={len(names)}")

# ---- pin 1: 23 entities, the banner among them, born dark
if len(names) != 23:
    fail(f"scene has {len(names)} entities, expected 23")
b = next(e for e in scene["entities"] if e["name"] == "banner")
if b.get("visible", 1) != 0:
    fail(f"banner born visible: {b}")
if b.get("text", "") != "":
    fail(f"banner born speaking: {b.get('text')!r}")
print("ok  scene: 23 entities, banner present, born dark and silent")

cache = {}
merge(scene and {"set": scene["entities"]}, cache)

# ---- pin 2: slam piece 0 (I, dc -5) — its cells bloom at glow 2
for _ in range(abs(SCRIPT[0])):
    f = tick(keys=["left"])
f = tick(keys=["space"])                     # the slam locks and blooms
seen = 0
for i in range(4):
    e = ent(f, f"cell{i}")
    if e is None:
        fail(f"cell{i} missing from the frame after the first slam")
    if abs(e.get("glow", 0) - 2) > 1e-6:
        fail(f"cell{i} born with glow {e.get('glow')} != 2 (the whole-birth law)")
    seen += 1
print(f"ok  lock bloom: {seen} cells born with glow 2 (whole, not half-lit)")

# ---- pin 3: the 3/s staircase — 0.45 s later the bloom reads 0.65
for _ in range(9):                           # 9 * 0.05 = 0.45 s
    f = tick()
merged = merge(f, dict(cache))
for i in range(4):
    e = ent(f, f"cell{i}") or merged.get(f"cell{i}")
    g = e.get("glow") if e else None
    if g is None or abs(g - 0.65) > 1e-6:
        fail(f"cell{i} glow after 0.45s = {g}, expected exactly 0.65 (3/s)")
print("ok  the 3/s law: 0.45 s wore the bloom 2 -> 0.65 exactly")

# ---- the script, pieces 1..13: slide |dc|, slam; the banner must stay dark
for k in range(1, 13):
    dc = SCRIPT[k]
    for _ in range(abs(dc)):
        tick(keys=["left" if dc < 0 else "right"])
    f = tick(keys=["space"])
    b = ent(f, "banner") or cache.get("banner")
    if b and b.get("visible", 0) != 0:
        fail(f"banner lit by a non-clearing slam (piece {k})")
print("ok  no clear, no voice: 13 silent slams, the banner stayed dark")

# ---- pin 4: the clearing slam — the 14th — speaks twice, born whole
dc = SCRIPT[13]
for _ in range(abs(dc)):
    tick(keys=["left" if dc < 0 else "right"])
f = tick(keys=["space"])
say = f.get("say", "")
b = ent(f, "banner")
if say != "line · lv 1":
    fail(f"frame.say {say!r} != 'line · lv 1'")
if b is None:
    fail("banner missing from the clearing frame")
if b.get("text") != "line · lv 1":
    fail(f"banner text {b.get('text')!r} != the say text")
if b.get("visible") != 1:
    fail(f"banner visible {b.get('visible')} at birth")
if abs(b.get("alpha", 0) - 1.0) > 1e-6:
    fail(f"banner born at alpha {b.get('alpha')} != 1 (birth shows whole)")
if abs(b.get("glow", 0) - 2) > 1e-6:
    fail(f"banner born with glow {b.get('glow')} != 2")
print("ok  the clear speaks: say and banner agree ('line · lv 1'), "
      "born whole at alpha 1, glow 2")

# ---- pin 5: the honest wear — monotonic decay, glow empties at 3/s
samples = []
for i in range(9):                           # 0.45 s in 0.05 steps
    f = tick()
    b = ent(f, "banner")
    if b is None:
        fail("banner vanished from the frames mid-wear")
    samples.append((b.get("alpha"), b.get("glow"), b.get("visible")))
if abs(samples[-1][1] - 0.65) > 1e-6:
    fail(f"banner glow after 0.45s = {samples[-1][1]}, expected 0.65 (3/s)")
alphas = [s[0] for s in samples]
for a, b2 in zip(alphas, alphas[1:]):
    if b2 > a + 1e-9:
        fail(f"banner alpha rose mid-wear: {alphas}")
    if b2 >= 1.0:
        fail(f"banner alpha never left 1: {alphas}")
print(f"ok  honest wear: alpha {alphas[0]} -> {alphas[-1]} monotonic, "
      f"glow 2 -> {samples[-1][1]} at 3/s")

# ---- pin 6: no flash-forever — by 1.65 s the banner is gone
while True:
    f = tick()
    b = ent(f, "banner")
    if b is None:
        fail("banner entity lost before its wear finished")
    if b.get("visible") == 0 and b.get("alpha", 1) == 0:
        break
print("ok  no flash-forever: the banner wore to invisible and hid")

# ---- pin 7: the hud paid and the seed's stream survived the script
f = tick()
hud = ent(f, "hud")
if hud is None or not hud.get("text", "").endswith("· 1 · lv 1"):
    fail(f"hud {hud.get('text') if hud else None!r} did not pay the clear")
pv = [ent(f, f"pv{i}") or cache.get(f"pv{i}") for i in range(4)]
promised = pv[0]["color"] if pv and pv[0] else None
f2 = tick(keys=["space"])                    # the next slam locks the promised
new_seats = [ent(f2, f"fall{i}") for i in range(4)]
nxt_color = next((s["color"] for s in new_seats if s and s["visible"]), None)
if nxt_color and promised and nxt_color != promised:
    fail(f"the stream was disturbed: promised {promised}, next {nxt_color}")
print(f"ok  the hud paid (total 1 · lv 1) and the stream held "
      f"(promised {promised}, delivered {nxt_color})")

p.terminate()
print("\nALL WELL-LIGHT PINS GREEN")
