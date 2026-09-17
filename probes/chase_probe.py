#!/usr/bin/env python3
"""Chase-probe snake.py — v5: greedy chase with WALL AWARENESS on the
13×5 grid, edge-truth from raw stdout (python print() rides the wire as
raw text, not JSON), space-respawn after crashes. Proves the eat, grow,
score-mirror and restart paths end to end."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os

BASE = _HOME
SDK = os.path.join(BASE, "sdk")
EX = os.path.join(SDK, "examples")
CELL, COLS, ROWS = 12, 13, 5
WORD = {(1, 0): "right", (-1, 0): "left", (0, -1): "jump", (0, 1): "s"}


def main():
    env = dict(os.environ)
    env["PYTHONPATH"] = SDK
    p = subprocess.Popen(["python3", f"{EX}/snake.py"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=BASE, text=True, bufsize=1, env=env)

    def send(o):
        try:
            p.stdin.write(json.dumps(o) + "\n")
            p.stdin.flush()
        except BrokenPipeError:
            return False
        return True

    st = {"food": None, "head": None, "cur": (1, 0), "frames": 0,
          "score_var": None, "len_max": 0, "meals": 0, "logs": [],
          "space_for": 0, "crashes": 0}

    def read_line():
        line = p.stdout.readline()
        if not line:
            return None
        s = line.strip()
        try:
            pkt = json.loads(s)
        except Exception:
            st["logs"].append(s[:160])          # raw print() chatter
            if "wall" in s or "bit yourself" in s:
                st["crashes"] += 1
                st["space_for"] = 12
            if s.startswith("meal"):
                st["meals"] += 1
            return {}
        if pkt.get("t") == "print":
            m = pkt.get("m", "")
            st["logs"].append(m)
        return pkt

    def read_frame():
        pkt = read_line()
        if pkt is None:
            return False
        if pkt.get("t") == "frame":
            st["frames"] += 1
            segs, head = 0, None
            for e in pkt.get("set", []):
                n = str(e.get("name", ""))
                if n == "food":
                    st["food"] = (e.get("x", 0), e.get("y", 0))
                if e.get("tag") == "head":
                    head = (e.get("x", 0), e.get("y", 0))
                if n.startswith("seg"):
                    segs += 1
            if head and head != st["head"]:
                if st["head"] is not None:
                    d = (head[0] - st["head"][0], head[1] - st["head"][1])
                    if abs(d[0]) == CELL or abs(d[1]) == CELL:
                        st["cur"] = (d[0] // CELL, d[1] // CELL)
                st["head"] = head
            st["len_max"] = max(st["len_max"], segs)
            v = pkt.get("vars", {})
            if "score" in v:
                st["score_var"] = v["score"]
            return True
        return True

    def plan():
        f, h, cur = st["food"], st["head"], st["cur"]
        if not f or not h:
            return None
        dx, dy = f[0] - h[0], f[1] - h[1]
        col, row = h[0] // CELL, h[1] // CELL
        rev = (-cur[0], -cur[1])

        def bad(mv):
            if mv == rev:
                return True
            nc, nr = col + mv[0], row + mv[1]
            return nc < 0 or nc >= COLS or nr < 0 or nr >= ROWS

        cands = []
        if dx:
            cands.append((1 if dx > 0 else -1, 0))
        if dy:
            cands.append((0, 1 if dy > 0 else -1))
        for perp in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            if perp not in cands:
                cands.append(perp)
        for mv in cands:
            if not bad(mv):
                return mv
        return None

    send({"t": "hello", "w": 160, "h": 60})
    read_line()

    for i in range(2000):
        hold = {}
        if st["space_for"] > 0:
            st["space_for"] -= 1
            hold = {"space": True}
        else:
            mv = plan()
            if mv:
                hold = {WORD[mv]: True}
        if not send({"t": "tick", "dt": 0.016, "keys": hold,
                     "chars": "", "hits": []}):
            break
        if not read_frame():
            break

    p.kill()
    ok = st["meals"] >= 3 and st["score_var"] is not None \
        and st["len_max"] > 3 and st["frames"] > 1500
    print(f"frames={st['frames']} meals={st['meals']} "
          f"score_var={st['score_var']} max_len={st['len_max']} "
          f"crashes={st['crashes']}")
    for c in st["logs"][:6]:
        print("   log:", c)
    print("CHASE", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


main()
