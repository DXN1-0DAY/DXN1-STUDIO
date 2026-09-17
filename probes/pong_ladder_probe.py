#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R19 probe: pong.cpp "the ladder" — the compiled C++ SDK's AI
# difficulty rubber band, driven over the real wire.
# pins: 5 entities; the hud names the rung (CPU Lk) and it always
# equals clamp(3 + you - cpu, 1, 5) — INCLUDING the tick a point lands
# (the probe caught the first speech mixing pre-score rung with
# post-score numbers); "first to 5" survives on the hud; whenever the
# AI chases with a gap wider than its step, it moves EXACTLY the
# rung's cap * dt (120/155/190/235/285); and a long idle set shows at
# least three distinct rungs — the band breathes.
# probe lessons: pump threads beat selectors (TextIOWrapper read-ahead
# starves select()); the standalone C++ SDK detects NO overlaps — hits
# must be injected, and a no-hit tick clears the pair memory, so an
# injection every few ticks re-fires for real (enter-only semantics).
import json, subprocess, sys, os, re, tempfile, shutil, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
LADDER = [120.0, 155.0, 190.0, 235.0, 285.0]
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

tmp = tempfile.mkdtemp(prefix="pong-ladder-")
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
    _q.put("")
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
hud_mismatches = ""
glow_mismatches = ""
glow_checks = 0
rungs_seen = set()
hud = ""

# ── phase 1: an idle set — the hud law, every tick, points landing live
# The AI's movement law, measured EVERY tick: its move is exactly
# min(step, |gap|) toward want — the capped tracker, no overshoot, no
# undershoot, whatever the rung. Ticks where a point just landed are
# skipped: the move ran on the pre-score rung, the hud speaks the
# post-score one (one score, one truth — but not the same instant).
prev = None
prev_score = None
law_checks = 0
law_violations = ""

def measure(prev, ents, lvl, score):
    global law_checks, law_violations, prev_score
    if prev is None or prev_score is None or score != prev_score:
        return
    ball, ai = ents["ball"], ents["ai"]
    # the engine's order: physics FIRST (ball.y += vy*dt), THEN onTick —
    # so the AI tracks the ball's POST-physics position. Frame N-1's
    # serialized vy is exactly what tick N's physics used.
    ball_y = prev[0] + prev[2] * 0.05
    want_y = ball_y - ai["h"] / 2 + 6
    gap = want_y - prev[1]
    moved = ai["y"] - prev[1]
    step = LADDER[lvl - 1] * 0.05
    want_move = (step if gap > 0 else -step) if abs(gap) > step else gap
    law_checks += 1
    if abs(moved - want_move) > 0.3:
        law_violations += f"L{lvl} moved {moved:.2f} want {want_move:.2f}; "

for i in range(300):
    ents, _ = frame()
    hud = ents["hud"].get("text", "")
    m = hud_rx.search(hud)
    if not m:
        hud_mismatches += f"{i}:unparsed; "; prev = None; continue
    you, cpu, lvl = int(m.group(1)), int(m.group(2)), int(m.group(3))
    want_lvl = max(1, min(5, 3 + you - cpu))
    if lvl != want_lvl:
        hud_mismatches += f"{i}:L{lvl} want L{want_lvl}; "
    # the rung's halo: the AI paddle's glow IS its level (v3.1.46)
    glow_checks += 1
    g_ = ents["ai"].get("glow", 0)
    if abs(g_ - want_lvl) > 0.01:
        glow_mismatches += f"{i}:glow {g_} want {want_lvl}; "
    rungs_seen.add(lvl)
    measure(prev, ents, lvl, (you, cpu))
    prev = (ents["ball"]["y"], ents["ai"]["y"], ents["ball"]["vy"])
    prev_score = (you, cpu)

pin("hud always speaks clamp(3 + you - cpu)", hud_mismatches == "",
    hud_mismatches[:120])
pin(f"the AI's halo is its rung ({glow_checks} frames)",
    glow_checks >= 200 and glow_mismatches == "", glow_mismatches[:120])
pin("'first to 5' survives on the hud", "first to 5" in hud, hud)
pin("an idle set breathes through 3+ rungs",
    len(rungs_seen) >= 3, str(sorted(rungs_seen)))

# ── phase 2: a steered rally — injected paddle hits bend the ball's
# vy for real (the onHit law: vy = 320 * edge offset), exercising the
# movement law under steering, across whatever rungs the band visits
prev = None
prev_score = None
for i in range(300):
    hits = [["ball", "pad"]] if i % 3 == 0 else (
           [["ball", "ai"]] if i % 3 == 1 else None)
    ents, _ = frame(hits)
    hud = ents["hud"].get("text", "")
    m = hud_rx.search(hud)
    if m:
        you, cpu, lvl = int(m.group(1)), int(m.group(2)), int(m.group(3))
        rungs_seen.add(lvl)
        measure(prev, ents, lvl, (you, cpu))
        prev = (ents["ball"]["y"], ents["ai"]["y"], ents["ball"]["vy"])
        prev_score = (you, cpu)
    else:
        prev = None

pin(f"the movement law held across {law_checks} measured ticks",
    law_checks >= 200 and law_violations == "", law_violations[:160])
p.kill(); shutil.rmtree(tmp, ignore_errors=True)
print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
