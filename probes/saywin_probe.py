#!/usr/bin/env python3
"""saywin_probe: prove the say()/win() bridge in BOTH SDKs end to end.
A micro game (python AND node) calls say()+win() on tick 1 only; the
probe asserts the frame carries both fields, and that tick 2's frame
is clean (the words live one frame, not forever)."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, tempfile

BASE = _HOME
SDK = os.path.join(BASE, "sdk")

PY_GAME = '''
from dxn3 import *
hud = label("hud", 2, 2, "saywin")
n = {"i": 0}
def on_tick(dt):
    n["i"] += 1
    if n["i"] == 1:
        say("the bridge speaks")
        win("banner!")
run()
'''

JS_GAME = '''
const { label, say, win, on, run } = require("dxn3");
label("hud", 2, 2, "saywin");
let i = 0;
on.tick(() => { i++; if (i === 1) { say("the bridge speaks"); win("banner!"); } });
run();
'''


def probe(cmd, ext, src):
    env = dict(os.environ)
    env["PYTHONPATH"] = SDK
    env["NODE_PATH"] = SDK
    f = tempfile.NamedTemporaryFile("w", suffix=ext, delete=False, dir="/tmp")
    f.write(src)
    f.close()
    p = subprocess.Popen(cmd + [f.name], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=BASE, text=True, bufsize=1, env=env)

    def send(o):
        p.stdin.write(json.dumps(o) + "\n")
        p.stdin.flush()

    send({"t": "hello", "w": 120, "h": 44})
    scene = json.loads(p.stdout.readline())
    frames = []
    for i in range(3):
        send({"t": "tick", "dt": 0.016, "keys": {}, "chars": "", "hits": []})
        frames.append(json.loads(p.stdout.readline()))
    p.kill()
    os.unlink(f.name)
    return scene, frames


fails = 0
for name, cmd, ext, src in [
        ("python", ["python3"], ".py", PY_GAME),
        ("node", ["node"], ".js", JS_GAME)]:
    try:
        scene, frames = probe(cmd, ext, src)
        f1, f2 = frames[0], frames[1]
        ok = (f1.get("say") == "the bridge speaks"
              and f1.get("win") == "banner!"
              and f2.get("say") == "" and f2.get("win") == ""
              and scene.get("t") == "scene")
        print(f"{name}: f1 say={f1.get('say')!r} win={f1.get('win')!r} · "
              f"f2 say={f2.get('say')!r} win={f2.get('win')!r} → "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails += 1
    except Exception as e:
        print(f"{name}: EXCEPTION {e}")
        fails += 1

print("SAYWIN", "PASS" if not fails else "FAIL")
sys.exit(1 if fails else 0)
