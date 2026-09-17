#!/usr/bin/env python3
"""Deterministic probe for sdk/examples/dino.js — the seeded long run."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, select

env = dict(os.environ)
env["NODE_PATH"] = _os.path.join(_HOME, "sdk")
fails = []

def check(name, ok, detail=""):
    print(("   ok  " if ok else "   FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not ok:
        fails.append(name)

p = subprocess.Popen(["node", _os.path.join(_HOME, "sdk", "examples", "dino.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n")
    p.stdin.flush()

def readline_ms(timeout=2.0):
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r:
        return None
    return p.stdout.readline()

send({"t": "hello", "w": 120, "h": 44})
scene = None
for _ in range(30):
    line = readline_ms()
    if line is None or not line:
        break
    try:
        pkt = json.loads(line)
    except Exception:
        continue
    if pkt.get("t") == "scene":
        scene = pkt
        break
ents = {e["name"]: e for e in (scene or {}).get("entities", [])}
check("scene arrives with the desert", scene is not None and len(ents) == 24,
      f"{len(ents)} entities")
check("six cacti wait in the pool",
      sum(1 for n in ents if n.startswith("cactus-")) == 6)

# ---- the night sky: 7 stars + a moon from their OWN seed
sky_n = sum(1 for n in ents if n.startswith("star-"))
check("seven stars hang in the day sky", sky_n == 7, f"{sky_n}")
check("the moon hangs too", "moon" in ents)

def fnxa(s):
    # replicate JS exactly: bitwise ops yield SIGNED int32 — the seed
    # goes negative and the FNV multiply runs on the negative DOUBLE
    # (values exceed 2^53, low bits round off) before >>>0 restores
    # unsigned. Miss the sign or the float rounding and the stream
    # diverges.
    h = 2166136261
    for ch in s:
        h = (h ^ ord(ch)) & 0xFFFFFFFF
        if h >= 2**31:
            h -= 2**32                       # ToInt32: JS multiplies signed
        h = int(float(h) * 16777619.0) % 2**32
    return h

# the sky's positions must match the FNV/xorshift of "the night sky"
# run independently here — the desert's seed is never touched
W_PROBE, H_PROBE = 120, 44
state_h = fnxa("the night sky")
def snext():
    global state_h
    state_h = (state_h ^ ((state_h << 13) & 0xFFFFFFFF)) & 0xFFFFFFFF
    state_h ^= state_h >> 17
    state_h = (state_h ^ ((state_h << 5) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return state_h / 4294967296.0

stars_ok = True
for i in range(7):
    ex_x = 2 + int(snext() * (W_PROBE - 6))
    ex_y = 3 + int(snext() * 9)
    e = ents.get(f"star-{i}", {})
    if e.get("x") != ex_x or e.get("y") != ex_y:
        stars_ok = False
        print(f"      star-{i}: got ({e.get('x')},{e.get('y')}) want ({ex_x},{ex_y})")
check("the sky wears its own seed (positions match)", stars_ok)
check("day sky is a rumor (alpha 0.15 / moon 0.25)",
      all(abs(ents.get(f"star-{i}", {}).get("alpha", 1) - 0.15) < 1e-6 for i in range(7))
      and abs(ents.get("moon", {}).get("alpha", 1) - 0.25) < 1e-6
      and not ents.get("moon", {}).get("glow"))

def tick(keys=None, chars=""):
    send({"t": "tick", "dt": 0.05, "keys": keys or {}, "chars": chars, "hits": []})
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
    return {s["name"]: s for s in frame.get("set", [])}

st = state(tick())
y0 = st["dino"]["y"]
st = state(tick({"space": True}))
y1 = st["dino"]["y"]
st = state(tick())
y2 = st["dino"]["y"]
check("the leap is set on the key frame", y1 == y0,
      f"y {y0} → {y1} (keys land after the tick's physics — SDK law)")
check("the leap lifts the runner next frame", y2 < y0, f"y {y0} → {y2}")
arc = []
for _ in range(16):                      # a full leap is ~13 ticks
    arc.append(state(tick())["dino"]["y"])
check("gravity returns the runner to the ground", arc[-1] == y0,
      f"arc {arc[0]:.1f} → {arc[-1]:.1f} over 16 ticks")

f = None
for _ in range(80):                      # 4s — the seed spawns by now
    f = tick()
    if f is None:
        break
    st = state(f)
    onscreen = [n for n, s in st.items()
                if n.startswith("cactus-") and s.get("x", -999) > 0]
    if onscreen:
        break
check("the seeded desert spawns a cactus", f is not None and onscreen,
      str(onscreen))

x_before = st.get(onscreen[0], {}).get("x") if onscreen else None
st2 = state(tick())
x_after = st2.get(onscreen[0], {}).get("x") if onscreen else None
check("the cactus scrolls at the run's speed",
      x_before is not None and x_after is not None and x_after < x_before,
      f"{x_before} → {x_after}")

# ---- the night fade: run past 200 m on coarse ticks (hits are ours —
# no death), then the alpha law fades the sky in over two seconds
def tick_dt(keys=None, chars="", dt=0.5):
    send({"t": "tick", "dt": dt, "keys": keys or {}, "chars": chars, "hits": []})
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

night_frame = None
for _ in range(90):
    f = tick_dt()
    if f is None:
        break
    stn = state(f)
    if any(abs(s.get("alpha", 0.15) - 0.15) > 1e-6
           for n, s in stn.items() if n.startswith("star-")):
        night_frame = f
        break
check("night falls at 200 m (the sky wakes)", night_frame is not None)
for _ in range(8):                        # the fade runs to full in 4 coarse ticks
    night_frame = tick_dt()
stn = state(night_frame) if night_frame else {}
check("the stars burn at alpha 0.9",
      all(abs(stn.get(f"star-{i}", {}).get("alpha", 0) - 0.9) < 0.02 for i in range(7)))
check("the moon shines (alpha 1, glow 4)",
      abs(stn.get("moon", {}).get("alpha", 0) - 1.0) < 0.02
      and stn.get("moon", {}).get("glow") == 4)
check("the clouds dim to half",
      all(abs(stn.get(n, {}).get("alpha", 1) - 0.5) < 0.02
          for n in ("cloud-a", "cloud-b")))

# the fatal touch: the engine reports hits, the runner falls
if onscreen:
    send({"t": "tick", "dt": 0.05, "keys": {}, "chars": "",
          "hits": ["dino", onscreen[0]]})
    fr = None
    for _ in range(10):
        line = readline_ms()
        if line is None or not line:
            break
        try:
            pkt = json.loads(line)
        except Exception:
            continue
        if pkt.get("t") == "frame":
            fr = pkt
            break
    win_txt = (fr or {}).get("win", "")
    check("the fall speaks its meters", "down at" in win_txt, win_txt[:40])
    # ---- r walks again: a fresh run is a fresh DAY
    f = tick(chars="r")
    st = state(f) if f else {}
    check("r resets the sky to day (alpha 0.15, moon 0.25, no glow)",
          all(abs(st.get(f"star-{i}", {}).get("alpha", 1) - 0.15) < 1e-6
              for i in range(7))
          and abs(st.get("moon", {}).get("alpha", 1) - 0.25) < 1e-6
          and not st.get("moon", {}).get("glow"))
    check("the day ground returns",
          st.get("ground", {}).get("color") == "#5b4a3a",
          str(st.get("ground", {}).get("color")))

try:
    p.stdin.close()
except Exception:
    pass
p.wait(timeout=5)
out = p.stdout.read() or ""
check("no tracebacks on the wire", "Traceback" not in out and "Error" not in out,
      out[-120:])
print("DINO " + ("PASS" if not fails else f"FAIL {fails}"))
sys.exit(1 if fails else 0)
