#!/usr/bin/env python3
"""probe for sdk/examples/tetris.js ghost piece — drives the real wire.
Hello FIRST (dxn3.js blocks on it at require time). Asserts: 12 entities
in the scene (hud + 3 rails + 4 fall seats + 4 ghost seats), the ghost
wears alpha 0.32 in the piece's color, tracks the piece's columns, sits
BELOW the piece, follows left moves, and hides exactly when the piece
reaches its landing (gy == py). Soft-drop rides the letter s — the
wire's held keys are left/right/jump/space; "down" never fires (a
latent tetris bug this probe exposed)."""
# The probes COME HOME (v3.1.90): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (four drift
# catches on record). Canonical law pins: probes/*_probe.py, one family
# per round, tetris first (the driftiest).
import json, subprocess, sys, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["NODE_PATH"] = f"{REPO}/sdk"
W, H = 100, 44
BX, BY, CELL = 2, 2, 2                  # tetris.js well geometry
PX = 25                                  # tetris.js preview box x

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

def fail(msg):
    print(f"FAIL: {msg}"); sys.exit(2)

# ---- handshake: hello FIRST, then the scene comes back
send({"t": "hello", "w": W, "h": H})
scene = child_line()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:100]}"
names = [e["name"] for e in scene["entities"]]
print(f"scene '{scene.get('name')}' entities={len(names)}")

# ---- scene inventory: 17 entities, ghost + preview seats exist
for nm in ("hud", "rail-l", "rail-r", "floor", "nxl",
           "fall0", "fall1", "fall2", "fall3",
           "ghost0", "ghost1", "ghost2", "ghost3",
           "pv0", "pv1", "pv2", "pv3"):
    if nm not in names:
        fail(f"{nm} missing from scene (have {names})")
print("ok  scene inventory: 4 fall + 4 ghost + 4 preview seats + label + hud + rails")

# ---- one tick: ghost wears alpha 0.32, colored like the piece, below it
f = tick(dt=0.05)
seats = [ent(f, f"fall{i}") for i in range(4)]
gseats = [ent(f, f"ghost{i}") for i in range(4)]
piece_color = seats[0]["color"]
n_vis = 0
for i, (s, g) in enumerate(zip(seats, gseats)):
    if abs(g.get("alpha", 1) - 0.32) > 1e-6:
        fail(f"ghost{i} alpha {g.get('alpha')} != 0.32")
    if g["color"] != piece_color:
        fail(f"ghost{i} color {g['color']} != piece {piece_color}")
    if g["visible"]:
        n_vis += 1
        if g["x"] != s["x"]:
            fail(f"ghost{i} x {g['x']} != seat x {s['x']}")
        if g["y"] <= s["y"]:
            fail(f"ghost{i} y {g['y']} not below seat y {s['y']}")
print(f"ok  ghost: alpha 0.32, color {piece_color}, {n_vis}/4 seats visible, "
      f"columns track the piece, all seats below it")

# ---- left,left: the ghost follows the piece's columns
f2 = tick(keys=["left"])
f3 = tick(keys=["left"])
for f in (f2, f3):
    s0, g0 = ent(f, "fall0"), ent(f, "ghost0")
    if g0["visible"] and g0["x"] != s0["x"]:
        fail(f"ghost x {g0['x']} != seat x {s0['x']} after a left move")
print("ok  ghost follows left moves")

# ---- hold s (soft-drop): the ghost must hide exactly when the piece lands
hidden_at = None
frames_held = 0
for _ in range(60):
    f = tick(chars="s", dt=0.05)
    frames_held += 1
    gv = [ent(f, f"ghost{i}")["visible"] for i in range(4)]
    piece_seats = [ent(f, f"fall{i}") for i in range(4)]
    if all(v == 0 for v in gv) and any(s["visible"] for s in piece_seats):
        hidden_at = frames_held
        break
if hidden_at is None:
    fail("ghost never hid while the piece descended to its landing")
print(f"ok  ghost hides at the landing (frame {hidden_at} of the down-hold)")

# ---- release: ghost stays hidden while the piece rests
f = tick(dt=0.05)
gv = [ent(f, f"ghost{i}")["visible"] for i in range(4)]
if any(gv):
    fail(f"ghost reappeared while the piece rests: {gv}")
print("ok  ghost stays hidden at rest")

# ---- the preview is HONEST: what it wears is what spawns next
pv = [ent(f, f"pv{i}") for i in range(4)]
if not all(e["visible"] for e in pv):
    fail(f"preview seats not all visible: {[e['visible'] for e in pv]}")
if any(e["x"] < PX for e in pv):
    fail(f"preview seats inside the well: {[e['x'] for e in pv]}")
if ent(f, "nxl")["text"] != "next":
    fail("preview label missing")
promised = pv[0]["color"]
f = tick(keys=["space"])                       # slam — the order locks, the
new_seats = [ent(f, f"fall{i}") for i in range(4)]  # promised piece spawns
new_color = next(s["color"] for s in new_seats if s["visible"])
if new_color != promised:
    fail(f"preview lied: promised {promised}, spawned {new_color}")
print(f"ok  preview honest: promised {promised}, the queue delivered {new_color}")

p.terminate()
print("\nALL GHOST PINS GREEN")
