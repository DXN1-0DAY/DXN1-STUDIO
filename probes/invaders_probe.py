#!/usr/bin/env python3
"""Deterministic probe for sdk/examples/invaders.js — the march, the guns."""

import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.92): re-pinned to the current truth and
# walked by gate 8 — a probe the gates never run ages into a liar (the
# drift ledger lives in probes/README.md).
import json, subprocess, sys, os, select

env = dict(os.environ)
env["NODE_PATH"] = _os.path.join(_HOME, "sdk")
fails = []

def check(name, ok, detail=""):
    print(("   ok  " if ok else "   FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not ok:
        fails.append(name)

p = subprocess.Popen(["node", _os.path.join(_HOME, "sdk", "examples", "invaders.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n")
    p.stdin.flush()

def readline_ms(timeout=2.0):
    """a line with a deadline — a silent child never hangs the probe."""
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r:
        return None
    return p.stdout.readline()

send({"t": "hello", "w": 120, "h": 44})   # the SDK eats hello at module load
scene = None
for _ in range(30):
    line = readline_ms()
    if line is None:
        break
    if not line:
        break
    try:
        pkt = json.loads(line)
    except Exception:
        continue
    if pkt.get("t") == "scene":
        scene = pkt
        break
ents = {e["name"]: e for e in (scene or {}).get("entities", [])}
check("scene arrives with the invasion", scene is not None and len(ents) == 62,
      f"{len(ents)} entities")
check("the grid seats 15 aliens",
      sum(1 for n in ents if n.startswith("alien-")) == 15)
check("both gun pools exist", all(f"shot-{i}" in ents for i in range(3))
      and all(f"bomb-{i}" in ents for i in range(3)))

def tick(keys=None, chars=""):
    send({"t": "tick", "dt": 0.05, "keys": keys or {}, "chars": chars, "hits": []})
    pkt = None
    for _ in range(10):
        line = readline_ms()
        if line is None or not line:
            return None
        try:
            pkt = json.loads(line)
        except Exception:
            continue
        if pkt.get("t") == "frame":
            return pkt
    return None

def state(frame):
    out = {}
    for s in frame.get("set", []):
        out[s["name"]] = s
    return out

f0 = tick()
st0 = state(f0)
ax0 = st0["alien-0-0"]["x"]
ay0 = st0["alien-0-0"]["y"]

f1 = [tick() for _ in range(20)]          # 1.0s — past the first step
st6 = state(f1[-1])
ax6, ay6 = st6["alien-0-0"]["x"], st6["alien-0-0"]["y"]
check("the grid marches sideways", ax6 != ax0, f"x {ax0} → {ax6}")
check("the grid holds its row (no drop yet)", ay6 == ay0, f"y {ay0} = {ay6}")

# fire and let the bullet climb: space held two frames, then coast
tick({"space": True})
f8 = tick({"space": True})
st8 = state(f8)
shot = next((st8[n] for n in st8 if n.startswith("shot-") and st8[n]["x"] > -100), None)
check("space fires a shot from the cannon", shot is not None,
      str(shot) if shot else "all parked")

# march an alien into the player's bullet — a real hit pair, honestly set
hit_frame = None
for name in list(st8):
    if name.startswith("alien-") and st8[name].get("y", 0) > 0:
        send({"t": "tick", "dt": 0.05, "keys": {}, "chars": "",
              "hits": [name, "player"] if shot is None else
                      [name, next((n for n in st8 if n.startswith("shot-")), "shot-0")]})
        hit_frame = tick()
        break
st_hit = state(hit_frame) if hit_frame else {}
scored = any("score 30" in str(s.get("text", "")) or "score 20" in str(s.get("text", ""))
             or "score 10" in str(s.get("text", ""))
             for s in st_hit.values() if s.get("name") == "hud")
check("a hit pays its row's points", scored, "hud updated" if scored else "no score")

# ---- the SHELTERS: four arches of 7 blocks, honest destroys
# (first: drain stale frames — the alien-hit section above leaves one
# unread, which would shift every read below by one)
def drain():
    while True:
        ln = readline_ms(0.2)
        if ln is None or not ln:
            return

drain()

def inject(pair):
    # send the hits-tick and read ITS OWN frame — a plain tick() here
    # would leak one frame and shift the whole stream
    send({"t": "tick", "dt": 0.05, "keys": {}, "chars": "", "hits": list(pair)})
    for _ in range(10):
        line = readline_ms()
        if line is None or not line:
            return None
        try:
            pkt = json.loads(line)
        except Exception:
            continue
        if pkt.get("t") == "frame":
            return pkt
    return None

shields = [n for n in ents if n.startswith("shield-")] 
check("four shelters stand (28 blocks)", len(shields) == 28, f"{len(shields)} blocks")

f = inject(["shot-0", "shield-0-0"])
check("a shot eats its block", f is not None and "shield-0-0" in (f.get("del") or []),
      str((f or {}).get("del")))
st = state(f) if f else {}
s0 = st.get("shot-0")
check("the drinking shot is parked", s0 is not None and s0["x"] <= -100,
      str(s0 and s0["x"]))

f = inject(["bomb-0", "shield-1-4"])
check("a bomb eats its block", f is not None and "shield-1-4" in (f.get("del") or []),
      str((f or {}).get("del")))
st = state(f) if f else {}
b0 = st.get("bomb-0")
check("the drinking bomb is parked", b0 is not None and b0["x"] <= -100,
      str(b0 and b0["x"]))

st = state(tick())
grinder = next((n for n in st if n.startswith("alien-") and st[n].get("visible")), None)
check("a living alien exists for the grind", grinder is not None)
if grinder:
    f = inject([grinder, "shield-2-1"])
    check("the march grinds the shelter",
          f is not None and "shield-2-1" in (f.get("del") or []),
          str((f or {}).get("del")))
    st = state(f) if f else {}
    check("the grinder walks on", st.get(grinder, {}).get("visible") == 1)

# ---- an honest mini-host: fire from under bunker 3's hollow (75..78,
# untouched — the grind pin above already ate bunker 2's crown) and
# feed the REAL overlaps the engine would — the shot must be drunk
for _ in range(12):
    tick({"right": True})                   # player 60 → 72: shot exits at 76..78
f = tick({"space": True})
st = state(f)
shot = next((st[n] for n in st if n.startswith("shot-") and st[n]["x"] > -100), None)
check("the cannon fires from under the arch", shot is not None)
ate = None
for _ in range(14):
    f2 = tick()
    if f2 is None:
        break
    st2 = state(f2)
    s = next((st2[n] for n in st2 if n.startswith("shot-") and st2[n]["x"] > -100), None)
    if s is None:
        break
    blk = next((n for n in st2 if n.startswith("shield-")
                and s["x"] < st2[n]["x"] + 3 and s["x"] + s["w"] > st2[n]["x"]
                and s["y"] < st2[n]["y"] + 2 and s["y"] + s["h"] > st2[n]["y"]), None)
    if blk:
        f3 = inject([next(n for n in st2 if n.startswith("shot-") and st2[n]["x"] > -100), blk])
        ate = blk if f3 and blk in (f3.get("del") or []) else None
        break
check("the arch drinks the climbing shot", ate is not None, str(ate))

# ---- r from the ashes: game over, then a full rebuild
st = state(tick())
doomed = next((n for n in st if n.startswith("alien-") and st[n].get("visible")
               and st[n].get("y", 99) > 0), None)
check("an alien remains to end the world", doomed is not None)
if doomed:
    f = inject([doomed, "player"])
    check("earth can fall", f is not None and f.get("win") == "EARTH FALLS",
          str((f or {}).get("win")))
    f = tick(chars="r")
    st = state(f) if f else {}
    back = sum(1 for n in st if n.startswith("shield-"))
    check("r rebuilds the shelters (28 blocks back)", back == 28, f"{back} blocks")
    check("the reborn cannon keeps score 0",
          "score 0" in str(st.get("hud", {}).get("text", "")),
          str(st.get("hud", {}).get("text", "")))

try:
    p.stdin.close()
except Exception:
    pass
p.wait(timeout=5)
out = p.stdout.read() or ""
check("no tracebacks on the wire", "Traceback" not in out and "Error" not in out,
      out[-120:])
print("INVADERS " + ("PASS" if not fails else f"FAIL {fails}"))
sys.exit(1 if fails else 0)
