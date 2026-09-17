#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.94): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R35 probe: pong.cpp "the set's tension" — the low-light law's SIXTH
# transplant (cards hand -> snake meal -> asteroids hull -> lunar tank ->
# tetris rails -> pong ball), driven over the real wire.
# pins: 5 entities; the scene travels lean (no light on the wire at
# birth); the BALL wears the set's tension — dark while either score is
# under three, ring 1 at 3, BRIGHT 2 at the match point (4) — checked on
# EVERY parsed frame against the hud's own arithmetic; the scorer that
# lands on 4 SPEAKS ("match point", both flavors); the AI's rung halo
# coexists untouched (glow == clamp(3+you-cpu, 1, 5)); and when the set
# ends the reset pours the dark back (YOU WIN, 0-0, the ball rides dark
# again). The idle drive walks the whole staircase: the ball crosses the
# open goal every five ticks and the scorers alternate, so one unsteered
# set visits 0 -> ring -> bright -> match point -> the win -> fresh dark.
import json, subprocess, sys, os, re, tempfile, shutil, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

tmp = tempfile.mkdtemp(prefix="pong-tension-")
bin_ = os.path.join(tmp, "pong")
build = subprocess.run(["g++", "-std=c++23", "-O2", os.path.join(EX, "pong.cpp"),
                        "-o", bin_], capture_output=True, text=True)
assert build.returncode == 0, "pong.cpp build failed: " + build.stderr[:200]

p = subprocess.Popen([bin_], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

_q = queue.Queue()
def _pump():
    for ln in p.stdout:
        _q.put(ln)
threading.Thread(target=_pump, daemon=True).start()

def read(timeout=4.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            ln = _q.get(timeout=0.1)
        except queue.Empty:
            continue
        if not ln: return None
        try: return json.loads(ln)
        except Exception: continue
    return None

def frame(hits=None):
    send({"t": "tick", "dt": 0.05, "keys": {}, "chars": "",
          "hits": hits or []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

send({"t": "hello", "w": 120, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 5 entities", len(scene["entities"]) == 5,
    str([e["name"] for e in scene["entities"]]))
pin("the scene travels lean (no default light on the wire)",
    all("glow" not in e and "flash" not in e and "alpha" not in e
        for e in scene["entities"]),
    str([e["name"] for e in scene["entities"] if "glow" in e]))

hud_rx = re.compile(r"YOU (\d+) · CPU (\d+) · first to 5 · CPU L(\d)")

# ── the idle drive: the ball crosses the open goal every ~5 ticks and
# the scorers alternate — one unsteered set walks the whole staircase.
tension_checks = 0
tension_violations = ""
rung_violations = ""
rung_checks = 0
says_seen = {"you": False, "cpu": False}
dark_frames = 0
ring_frames = 0
bright_frames = 0
win_seen = False
fresh_dark = False
prev = None
set_done_at = None

for i in range(140):
    ents, _ = frame()
    hud = ents["hud"].get("text", "")
    msg = ents["msg"].get("text", "")
    m = hud_rx.search(hud)
    if not m:
        prev = None
        continue
    you, cpu, lvl = int(m.group(1)), int(m.group(2)), int(m.group(3))

    # the tension law, every parsed frame: the ball's light IS the set
    want_glow = 2 if (you >= 4 or cpu >= 4) else (1 if (you >= 3 or cpu >= 3) else 0)
    got = ents["ball"].get("glow", 0)
    tension_checks += 1
    if abs(got - want_glow) > 0.01:
        tension_violations += f"{i}:{you}-{cpu} glow {got} want {want_glow}; "
    if want_glow == 0: dark_frames += 1
    elif want_glow == 1: ring_frames += 1
    else: bright_frames += 1

    # the rung halo coexists untouched
    rung_checks += 1
    want_lvl = max(1, min(5, 3 + you - cpu))
    if abs(ents["ai"].get("glow", 0) - want_lvl) > 0.01:
        rung_violations += f"{i}:ai {ents['ai'].get('glow')} want L{want_lvl}; "

    # the say: a scorer landing on 4 speaks
    if prev is not None:
        py, pc = prev
        if you == 4 and py == 3:
            says_seen["you"] = "match point" in msg
        if cpu == 4 and pc == 3:
            says_seen["cpu"] = "match point" in msg
        if (py >= 4 or pc >= 4) and you == 0 and cpu == 0:
            win_seen = "YOU WIN" in msg
            set_done_at = i
    prev = (you, cpu)

    # after the reset: the fresh set rides dark again
    if set_done_at is not None and i >= set_done_at + 2:
        if abs(ents["ball"].get("glow", 0)) < 0.01:
            fresh_dark = True
        break

pin(f"the tension law held on every frame ({tension_checks} frames)",
    tension_checks >= 30 and tension_violations == "",
    tension_violations[:160])
pin("the idle set walked the whole staircase (dark, ring, bright)",
    dark_frames >= 10 and ring_frames >= 2 and bright_frames >= 2,
    f"dark={dark_frames} ring={ring_frames} bright={bright_frames}")
pin("the scorer that lands on 4 SPEAKS — both flavors",
    says_seen["you"] and says_seen["cpu"], str(says_seen))
pin("the rung halo coexists (the tension didn't evict the ladder)",
    rung_checks >= 30 and rung_violations == "", rung_violations[:120])
pin("the set ends honestly (YOU WIN, 0-0)", win_seen, "no win frame seen")
pin("the reset pours the dark back (the fresh set starts quiet)",
    fresh_dark, "the fresh set still wears light")
p.kill(); shutil.rmtree(tmp, ignore_errors=True)
print()
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
