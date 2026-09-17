#!/usr/bin/env python3
"""Deterministic probe for sdk/examples/tetris.js — the falling order."""
# The probes COME HOME (v3.1.90): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (four drift
# catches on record). Canonical law pins: probes/*_probe.py, one family
# per round, tetris first (the driftiest).
import json, subprocess, sys, os, select

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk")
fails = []

def check(name, ok, detail=""):
    print(("   ok  " if ok else "   FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not ok:
        fails.append(name)

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "tetris.js")],
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
# (re-pinned 8 -> 23: the census grew with the vault, the preview, the
# banner and the light laws — caught STALE on the clean v3.1.88 tree,
# the fourth drift catch: probes age, gates don't run them)
check("scene arrives with the well", scene is not None and len(ents) == 23,
      f"{len(ents)} entities")
check("the four falling seats exist",
      sum(1 for n in ents if n.startswith("fall")) == 4)
check("the well wears its rails and floor",
      all(n in ents for n in ("rail-l", "rail-r", "floor")))

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

def piece_cells(st):
    return sorted((s["y"], s["x"]) for n, s in st.items()
                  if n.startswith("fall") and s.get("visible") == 1)

f0 = tick()
st0 = state(f0)
pc0 = piece_cells(st0)
check("the first piece paints four live seats", len(pc0) == 4, str(pc0))

st1 = state(tick({"right": True}))
pc1 = piece_cells(st1)
check("right slides the order one seat over",
      len(pc1) == 4 and all(b[1] > a[1] for a, b in zip(sorted(pc0), sorted(pc1))),
      f"{pc0[0]} → {pc1[0]}")

st2 = state(tick({"jump": True}))   # the wire's tongue for turn is "jump"
pc2 = piece_cells(st2)
check("jump turns the piece (its seats rearrange)", pc2 != pc1)

# gravity: 30 ticks at dt=0.05 (1.5s, drop=0.5) — the piece falls ~3 rows
y_before = max(y for y, _ in pc2)
for _ in range(30):
    f = tick()
st3 = state(f)
pc3 = piece_cells(st3)
y_after = max(y for y, _ in pc3)
check("gravity drops the piece", y_after > y_before, f"{y_before} → {y_after}")

# hard slam: space locks — the buried cells are born as their OWN entities
f = tick({"space": True})
st4 = state(f)
locked = [n for n in st4 if n.startswith("cell")]
check("space slams — the buried cells are their own entities",
      len(locked) >= 4, str(locked[:6]))

# a full well tops out honestly: press nothing for a long while
fell = False
for _ in range(2400):                    # 120s of game time, no input
    f = tick()
    if f is None:
        break
    if "TOPPED OUT" in (f.get("win") or ""):
        fell = True
        break
check("an untouched well tops out with its count", fell,
      (f or {}).get("win", "")[:40])

# r walks again — letters reach the game through chars, not keys
if fell:
    f = tick(chars="r")
    st5 = state(f)
    live = [n for n in st5 if n.startswith("fall") and st5[n].get("visible") == 1]
    check("r falls again — the next order is born (2+ seats live)",
          len(live) >= 2 and "TOPPED OUT" not in (f.get("win") or ""),
          f"{len(live)} seats")

try:
    p.stdin.close()
except Exception:
    pass
p.wait(timeout=5)
out = p.stdout.read() or ""
check("no tracebacks on the wire", "Traceback" not in out and "Error" not in out,
      out[-120:])
print("TETRIS " + ("PASS" if not fails else f"FAIL {fails}"))
sys.exit(1 if fails else 0)
