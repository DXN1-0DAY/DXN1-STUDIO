#!/usr/bin/env python3
# DS2-R33 probe: asteroids.js "the ship wears the lives' low light" —
# over the real wire (node SDK) at 160x60.
# pins: the ship is born quiet (glow 0); the first hull hit (lives 2)
# rings it faint (glow 1) and the glow PERSISTS between hits; the
# second hit (lives 1) burns it BRIGHT (glow 2) and the say speaks
# "the last ship burns"; the third hit ends the run — and the fresh
# run pours the quiet back (glow 0, lives 3 on the HUD). The hits are
# spaced past the 2.2 s respawn grace; the birth has none (safe = 0),
# so the first synthetic pair lands at once.
import json, subprocess, sys, os, select

import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
REPO = _HOME
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _harness import Wire
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "asteroids.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

# THE BUFFER LAW (v3.1.103): the old read paired select() on the fd
# with readline() on a buffered stream — the respawn chatter and the
# payment frame shared one read chunk, the frame sat in Python's own
# buffer, and select waited for fd data that never came until the
# child saw the next tick it never would. The fleet's shared harness
# reads RAW and splits lines itself (probes/_harness.py).
w = Wire(p)

w.send({"t": "hello", "w": 160, "h": 60})
scene = w.read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents0 = {e["name"]: e for e in scene["entities"]}
pin("the ship is born quiet (glow 0)", ents0["ship"].get("glow", 0) == 0,
    str(ents0["ship"].get("glow")))

ents, f = w.frame()
pin("the first frame stays quiet", ents["ship"].get("glow", 0) == 0,
    str(ents["ship"].get("glow")))

# --- hit 1 (lives 2): the faint ring — no birth grace, it lands now ----
ents, f = w.frame(hits=["ship", "rock0_0"])
pin("the first hull hit bleaches (flash 1)", ents["ship"].get("flash", 0) == 1,
    str(ents["ship"].get("flash")))
pin("lives 2 rings the hull (glow 1)", ents["ship"].get("glow", 0) == 1,
    str(ents["ship"].get("glow")))
pin("the HUD speaks 2 left", "lives 2" in ents["hud"]["text"],
    ents["hud"]["text"])

# the glow PERSISTS between hits (the studio keeps the last light sent)
for _ in range(50):                      # 2.5 s — past the respawn grace
    ents, f = w.frame()
pin("the ring holds through the grace (glow 1)",
    ents["ship"].get("glow", 0) == 1, str(ents["ship"].get("glow")))

# --- hit 2 (lives 1): the last ship burns ------------------------------
ents, f = w.frame(hits=["ship", "rock0_1"])
pin("lives 1 burns the hull (glow 2)", ents["ship"].get("glow", 0) == 2,
    str(ents["ship"].get("glow")))
pin("the say speaks the last ship",
    "the last ship burns" in (f.get("say") or ""), str(f.get("say")))
pin("the HUD speaks 1 left", "lives 1" in ents["hud"]["text"],
    ents["hud"]["text"])

for _ in range(50):
    ents, f = w.frame()
pin("the burn holds through the grace (glow 2)",
    ents["ship"].get("glow", 0) == 2, str(ents["ship"].get("glow")))

# --- hit 3: game over — the fresh run pours the quiet back -------------
ents, f = w.frame(hits=["ship", "rock0_2"])
pin("the third hit ends the run (win banner)",
    "game over" in (f.get("win") or ""), str(f.get("win")))
pin("the fresh run is quiet again (glow 0)",
    ents["ship"].get("glow", 0) == 0, str(ents["ship"].get("glow")))
pin("the fresh HUD speaks 3 lives", "lives 3" in ents["hud"]["text"],
    ents["hud"]["text"])

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the last ship burns")
