#!/usr/bin/env python3
"""Stress-probe snake.py and asteroids.js beyond the 6-tick wire check:
long runs, held keys, forced hit pairs — tracebacks must never appear,
frames must keep flowing, and state rebuilds (game over) must not die."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, time

BASE = _HOME
SDK = os.path.join(BASE, "sdk")
EX = os.path.join(SDK, "examples")


def run_game(cmd, script, ticks=300, hold_seq=None, hits_seq=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = SDK
    env["NODE_PATH"] = SDK
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, cwd=BASE, text=True,
                         bufsize=1, env=env)
    frames, console, scene = 0, [], None

    def send(o):
        try:
            p.stdin.write(json.dumps(o) + "\n")
            p.stdin.flush()
        except BrokenPipeError:
            pass

    send({"t": "hello", "w": 160, "h": 60})
    end = time.time() + 5
    while time.time() < end and scene is None:
        line = p.stdout.readline()
        if not line:
            break
        try:
            pkt = json.loads(line.strip())
            if pkt.get("t") == "scene":
                scene = pkt
        except Exception:
            pass
    for i in range(ticks):
        hold = hold_seq(i) if hold_seq else {}
        hits = hits_seq(i) if hits_seq else []
        send({"t": "tick", "dt": 0.016, "keys": hold, "chars": "", "hits": hits})
        deadline = time.time() + 5
        got_frame = False
        while time.time() < deadline:
            line = p.stdout.readline()
            if not line:
                break
            s = line.strip()
            try:
                pkt = json.loads(s)
            except Exception:
                console.append(s[:160])
                continue
            t = pkt.get("t")
            if t == "frame":
                frames += 1
                got_frame = True
                break
            elif t == "print":
                console.append(pkt.get("m", ""))
            elif t == "scene":
                scene = scene or pkt
        if not got_frame:
            console.append(f"!! no frame for tick {i}")
            break
    p.kill()
    return frames, console


fails = 0

# ── snake: steer in circles for 300 ticks; it must survive and eat ──
seq = [{"left": True}] * 20 + [{"jump": True}] * 20
frames, console = run_game(["python3", f"{EX}/snake.py"], "snake", ticks=300,
                           hold_seq=lambda i: seq[i % len(seq)])
bad = [c for c in console if "Traceback" in c or "!!" in c or "Error" in c]
meals = [c for c in console if c.startswith("meal")]
print(f"snake.py: frames={frames} meals={len(meals)} console={len(console)}")
for c in bad[:5]:
    print("   BAD:", c)
if bad or frames < 250:
    fails += 1
    print("   FAIL snake.py")

# ── asteroids: fire constantly, force ship hits and bullet hits ──
def hits(i):
    out = []
    if i == 30:
        out += ["ship", "rock0_0"]        # hull hit → split + respawn
    if i == 60:
        out += ["ship", "rock0_1"]        # hull hit 2
    if i == 90:
        out += ["ship", "rock0_2"]        # hull hit 3 → game over rebuild
    if i in (120, 150, 180):
        out += ["bul0_1", "rock1_0"]      # a bullet finding a rock
        out += ["bul0_2", "rock1_0"]      # same rock named twice in one tick
    return out

frames2, console2 = run_game(["node", f"{EX}/asteroids.js"], "ast", ticks=300,
                             hold_seq=lambda i: {"space": True},
                             hits_seq=hits)
bad2 = [c for c in console2 if "Traceback" in c or "!!" in c
        or "Error" in c or "ReferenceError" in c or "TypeError" in c]
print(f"asteroids.js: frames={frames2} console={len(console2)}")
for c in console2[:8]:
    print("   log:", c)
for c in bad2[:5]:
    print("   BAD:", c)
if bad2 or frames2 < 250:
    fails += 1
    print("   FAIL asteroids.js")

print("STRESS", "FAIL" if fails else "PASS")
sys.exit(1 if fails else 0)
