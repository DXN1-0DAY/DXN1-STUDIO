#!/usr/bin/env python3
"""lunar_probe: deterministic path proof for lunar.py.
tick 5  → forced (land, pad0) pair while vy≈15 (< SOFT_VY 65) → touchdown,
          pad pays 50, score mirrors, freeze beat, respawn.
tick 200/400/600 → forced (land, hill0) → three crashes → game over →
          score reset. No tracebacks anywhere, frames must keep flowing."""
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
    p = subprocess.Popen(["python3", f"{EX}/lunar.py"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=BASE, text=True, bufsize=1, env=env)

    def send(o):
        try:
            p.stdin.write(json.dumps(o) + "\n")
            p.stdin.flush()
        except BrokenPipeError:
            return False
        return True

    st = {"frames": 0, "logs": [], "score_var": 0, "scene_ents": 0,
          "fb": None, "fb_colors": set(), "fb_vis": set(), "says": []}

    def read_line():
        line = p.stdout.readline()
        if not line:
            return None
        s = line.strip()
        try:
            return json.loads(s)
        except Exception:
            st["logs"].append(s[:160])        # print() chatter
            return {}

    def read_frame():
        pkt = read_line()
        if pkt is None:
            return False
        if pkt.get("t") == "frame":
            st["frames"] += 1
            v = pkt.get("vars", {})
            if "score" in v:
                st["score_var"] = v["score"]
            for e in pkt.get("set", []):
                if e.get("name") == "fuelbar":
                    st["fb"] = dict(e)
                    st["fb_colors"].add(e["color"])
                    st["fb_vis"].add(e["visible"])
            if pkt.get("say"):
                st["says"].append(pkt["say"])
            return True
        if pkt.get("t") == "scene":
            st["scene_ents"] = len(pkt.get("entities", []))
        return True

    def hits_at(i):
        if i == 5:
            return ["land", "pad0"]           # soft (vy ≈ 15) → touchdown
        if i == 200:
            return ["land", "hill0"]          # the hills are not for landing
        if i == 400:
            return ["land", "hill1"]
        if i == 600:
            return ["land", "hill2"]          # third crash → game over
        return []

    send({"t": "hello", "w": 960, "h": 540})
    first = read_line()                       # the scene packet, once
    if first and first.get("t") == "scene":
        st["scene_ents"] = len(first.get("entities", []))

    for i in range(800):
        hold = {"space": True} if 40 <= i <= 55 else {}
        if not send({"t": "tick", "dt": 0.016, "keys": hold, "chars": "",
                     "hits": hits_at(i)}):
            break
        if not read_frame():
            break

    # ---- the gauge phase: burn a fresh tank dry and watch the bar
    # speak — width shrinks, green → amber → red, it BLINKS under a
    # quarter tank, and the low-fuel warning speaks exactly once
    for _ in range(60):
        if not send({"t": "tick", "dt": 0.25, "keys": {"space": True},
                     "chars": "", "hits": []}):
            break
        if not read_frame():
            break

    p.kill()
    joined = "\n".join(st["logs"])
    need = ["touchdown — pad pays 50", "crash — the hills are not for landing",
            "game over — final score"]
    gauge_ok = (st["scene_ents"] == 11 and st["fb"] is not None
                and "#22c55e" in st["fb_colors"]
                and "#facc15" in st["fb_colors"]
                and "#ef4444" in st["fb_colors"]
                and len(st["fb_vis"]) >= 2
                and any("fuel low" in s for s in st["says"]))
    ok = all(n in joined for n in need) and st["frames"] >= 840 \
        and st["scene_ents"] == 11 and st["score_var"] == 0 \
        and "Traceback" not in joined and gauge_ok
    print(f"cond need={all(n in joined for n in need)} "
          f"frames={st['frames'] >= 840} ents={st['scene_ents'] == 11} "
          f"score={st['score_var'] == 0} clean={'Traceback' not in joined} "
          f"gauge={gauge_ok}")
    print(f"frames={st['frames']} scene_ents={st['scene_ents']} "
          f"score_var={st['score_var']}")
    print(f"gauge: colors={sorted(st['fb_colors'])} "
          f"vis={sorted(st['fb_vis'])} warns={[s for s in st['says'] if 'fuel' in s]}")
    for c in st["logs"][:8]:
        print("   log:", c)
    missing = [n for n in need if n not in joined]
    if missing:
        print("   missing:", missing)
    if not ok:
        tbs = [l for l in st["logs"]
               if "Error" in l or "Traceback" in l or l.startswith("  ")]
        for t in tbs[:8]:
            print("   tb:", t)
    print("LUNAR", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


main()
