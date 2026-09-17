#!/usr/bin/env python3
"""probe for sdk/examples/lightbot.js — drives the real wire protocol.
Hello FIRST (dxn3.js blocks on it at require time), then the scene.
Greedy nearest-neighbor over the 12 lamps, one key per tick, per-step
bot-position verification, then asserts: lamp lights, counts, win
banner, r-reset honesty."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os

REPO = _HOME
os.environ["NODE_PATH"] = f"{REPO}/sdk"
W, H = 100, 44
GX, GY, T = 29, 9, 6                    # lightbot.js grid geometry

p = subprocess.Popen(["node", f"{REPO}/sdk/examples/lightbot.js"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     text=True, bufsize=1)

def child_line():
    ln = p.stdout.readline()
    return json.loads(ln) if ln.strip() else None

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
        if pkt.get("t") == "print":
            print("  child says:", pkt.get("m", "")[:120])

def ent(frame, name):
    for e in frame["set"]:
        if e["name"] == name:
            return e
    return None

def assert_bot(f, c, r, via):
    b = ent(f, "bot")
    ex, ey = GX + c * T + 1, GY + r * T + 1
    if (b["x"], b["y"]) != (ex, ey):
        print(f"DRIFT via {via!r}: bot px ({b['x']},{b['y']}) != expected ({ex},{ey}) col={c} row={r}")
        sys.exit(2)

def walk_to(c0, r0, c1, r1):
    out = []
    out += [("keys", "right")] * (c1 - c0) if c1 > c0 else [("keys", "left")] * (c0 - c1)
    out += [("keys", "jump")] * (r0 - r1) if r1 < r0 else [("chars", "s")] * (r1 - r0)
    return out

# ---- handshake: hello FIRST, then the scene comes back
send({"t": "hello", "w": W, "h": H})
scene = child_line()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:100]}"
ents = scene["entities"]
names = [e["name"] for e in ents]
assert len(ents) == 38, f"entity count {len(ents)} != 38 (35 tiles + bot + 2 labels)"
assert "bot" in names and "hud" in names and "r0c0" in names and "r4c6" in names
print(f"ok  scene: {len(ents)} entities, name={scene.get('name','?')!r}")

LAMPS = [(2,0),(4,0),(1,1),(3,1),(5,1),(0,2),(6,2),(1,3),(3,3),(5,3),(2,4),(4,4)]

# ---- space on the centre tile (no lamp): honest refusal, no crash
f = tick(keys=["space"])                  # centre (3,2) has NO lamp
hud0 = ent(f, "hud")["text"]
assert "0/12" in hud0, f"hud shows {hud0!r}"
print("ok  space on lamp-less tile refused honestly")

# ---- greedy nearest-neighbour tour, every step position-verified
# the win banner is TRANSIENT (one frame) — capture it inside the tour
cur = (3, 2); todo = LAMPS[:]; win_seen = ""
while todo:
    nxt = min(todo, key=lambda L: abs(L[0]-cur[0]) + abs(L[1]-cur[1]))
    for kind, k in walk_to(cur[0], cur[1], nxt[0], nxt[1]):
        f = tick(keys=[k] if kind == "keys" else [],
                 chars=k if kind == "chars" else "")
        dc = 1 if k == "right" else -1 if k == "left" else 0
        dr = 1 if k == "s" else -1 if k == "jump" else 0
        assert_bot(f, cur[0] + dc, cur[1] + dr, k)
        cur = (cur[0] + dc, cur[1] + dr)
    f = tick(keys=["space"])
    assert_bot(f, cur[0], cur[1], "space")
    hud_now = ent(f, "hud")["text"]
    sys.stdout.write(f"  space at {nxt} -> {hud_now[43:]} say={f.get('say','')!r}\n"); sys.stdout.flush()
    todo.remove(nxt)
    assert cur == nxt, f"probe cur {cur} != planned {nxt}"
    if f.get("win"):
        win_seen = f["win"]

# ---- assertions after the tour: one more frame lets the hud catch up
# (the winning frame's hud was drawn before light() ran), while the
# banner was captured on the winning frame itself
f = tick(dt=0.2)
win_msg = win_seen
hud = ent(f, "hud")["text"]
assert "12/12" in hud, f"hud after tour: {hud!r}"
assert win_msg, "no win banner captured on the winning frame"
print(f"ok  ALL LIT: win={win_msg!r}")

r2c0 = ent(f, "r2c0")
assert r2c0["color"] == "#facc15" and r2c0.get("glow", 0) == 3, \
    f"lit tile wrong: color={r2c0['color']} glow={r2c0.get('glow')}"
print("ok  lit tile wears gold + glow 3 (v3.1.20's law in the wild)")

# ---- steps honesty: the banner must report the SAME steps the hud counted
steps = int(hud.split(", ")[1].split()[0])
assert str(steps) in win_msg, f"banner {win_msg!r} vs hud steps {steps}"
print(f"ok  steps honest: hud {steps} == banner")

# ---- r resets everything ('r' is not a held key — it rides chars)
tick(chars="r")
f = tick(dt=0.2)                          # the reset frame's hud lags one tick
hud = ent(f, "hud")["text"]
r2c0 = ent(f, "r2c0")
assert "0/12" in hud and r2c0["color"] == "#3a3120" and r2c0.get("glow", 0) == 0, \
    f"reset incomplete: hud={hud!r} tile={r2c0}"
assert not f.get("win"), "win banner survived the reset"
print("ok  r resets: dark tiles, zero counts, banner gone")

# ---- walls refuse: mash left far past the edge
for _ in range(6):
    f = tick(keys=["left"])
assert_bot(f, 0, 2, "wall mash")          # pinned at col 0, row 2
print("ok  grid walls survive mashing (bot pinned at col 0)")

p.stdin.close(); p.wait(timeout=5)
print("LIGHTBOT PROBE: ALL PASS")
