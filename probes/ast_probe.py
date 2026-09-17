#!/usr/bin/env python3
"""ast_probe: deterministic asteroids.js path proof.
No bullets early (so rocks can't die from real play) → three spaced
synthetic ship↔rock pairs walk lives 3→0 → the game-over rebuild MUST
fire. Then fire one bullet and pair it with a fresh-generation rock →
the bullet-split path MUST fire. No tracebacks allowed anywhere."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os

BASE = _HOME
SDK = os.path.join(BASE, "sdk")
EX = os.path.join(SDK, "examples")


def main():
    env = dict(os.environ)
    env["PYTHONPATH"] = SDK
    env["NODE_PATH"] = SDK
    p = subprocess.Popen(["node", f"{EX}/asteroids.js"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=BASE, text=True, bufsize=1, env=env)

    def send(o):
        try:
            p.stdin.write(json.dumps(o) + "\n")
            p.stdin.flush()
        except BrokenPipeError:
            return False
        return True

    st = {"frames": 0, "logs": [], "scene": None, "last_set": []}

    def read_line():
        line = p.stdout.readline()
        if not line:
            return None
        s = line.strip()
        try:
            return json.loads(s)
        except Exception:
            st["logs"].append(s[:160])      # console.log chatter
            return {}

    def read_frame():
        pkt = read_line()
        if pkt is None:
            return False
        if pkt.get("t") == "frame":
            st["frames"] += 1
            st["last_set"] = pkt.get("set", [])
            return True
        if pkt.get("t") == "scene":
            st["scene"] = pkt
        return True

    def hits_at(i):
        if i == 40:
            return ["ship", "rock0_0"]
        if i == 200:                       # past the 2.2s grace blink
            return ["ship", "rock0_1"]
        if i == 360:                       # third hull hit → game over
            return ["ship", "rock0_2"]
        if i == 470:
            return ["bul1_1", "rock1_3"]   # a fresh-gen bullet splits
        return []

    send({"t": "hello", "w": 160, "h": 60})
    read_line()                              # scene

    for i in range(600):
        hold = {"space": True} if 450 <= i <= 455 else {}
        if not send({"t": "tick", "dt": 0.016, "keys": hold, "chars": "",
                     "hits": hits_at(i)}):
            break
        if not read_frame():
            break

    p.kill()
    joined = "\n".join(st["logs"])
    need = ["hull hit — 2 left", "hull hit — 1 left",
            "game over — score"]
    ok = all(n in joined for n in need) and st["frames"] >= 590 \
        and "Error" not in joined and "rock1_" in json.dumps(st["last_set"])
    print(f"frames={st['frames']}")
    for c in st["logs"][:10]:
        print("   log:", c)
    missing = [n for n in need if n not in joined]
    if missing:
        print("   missing:", missing)
    print("AST", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


main()
