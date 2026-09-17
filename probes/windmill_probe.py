#!/usr/bin/env python3
"""Deterministic probe for sdk/examples/windmill.py — the turn showcase."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os

EX = _os.path.join(_HOME, "sdk", "examples")
fails = []

def check(name, ok, detail=""):
    print(("   ok  " if ok else "   FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not ok:
        fails.append(name)

env = dict(os.environ)
env["PYTHONPATH"] = _os.path.join(_HOME, "sdk")
p = subprocess.Popen(["python3", f"{EX}/windmill.py"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n")
    p.stdin.flush()

def recv():
    line = p.stdout.readline()
    try:
        return json.loads(line)
    except Exception:
        return None

def settle(n=3, keys=None):
    frames = []
    for i in range(n):
        send({"t": "tick", "dt": 0.05, "keys": keys or {}, "chars": "", "hits": []})
        pkt = recv()
        while pkt is not None and pkt.get("t") != "frame":
            pkt = recv()
        if pkt:
            frames.append(pkt)
    return frames

send({"t": "hello", "w": 120, "h": 44})
scene = None
for _ in range(20):
    line = p.stdout.readline()
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
check("scene arrives with the mill", scene is not None and len(ents) == 13,
      f"{len(ents)} entities")
check("blades exist", all(f"blade-{i}" in ents for i in range(4)))
check("the hub turns itself (engine spin)", ents.get("hubspin", {}).get("spin") == 180)

f1 = settle(2)
b0 = None
for f in f1:
    for s in f.get("set", []):
        if s.get("name") == "blade-0":
            b0 = s
check("blade-0 speaks rot", b0 is not None and "rot" in b0,
      f"rot={b0.get('rot') if b0 else None}")
x1, rot1 = b0.get("x"), b0.get("rot")

f2 = settle(4)
positions = []
for f in f2:
    for s in f.get("set", []):
        if s.get("name") == "blade-0":
            positions.append((s.get("x"), s.get("rot")))
moved = any(p[0] != x1 for p in positions)
turns = any(p[1] != rot1 for p in positions)
check("blade-0 orbits the hub (x moves)", moved, f"x {x1} → {positions[-1][0]}")
check("blade-0 turns (rot moves)", turns, f"rot {rot1} → {positions[-1][1]}")

# pause: space held — the mill holds the wind
settle(1, keys={"space": True})
frozen_before = settle(2)[-1]
xs = []
for f in settle(3):
    for s in f.get("set", []):
        if s.get("name") == "blade-0":
            xs.append(s.get("x"))
check("space holds the wind (blade x frozen)", len(set(xs)) <= 1,
      f"xs={xs}")

try:
    p.stdin.close()
except Exception:
    pass
p.wait(timeout=5)
out = p.stdout.read() or ""
check("no tracebacks on the wire", "Traceback" not in out, out[-120:])
print("WINDMILL " + ("PASS" if not fails else f"FAIL {fails}"))
sys.exit(1 if fails else 0)
