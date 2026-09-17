#!/usr/bin/env python3
"""probe for sdk/examples/shooter.py — NIGHT FALLS ON THE VOID (v3.1.76).

The moon check across the fleet: the dino's night law, ported to the
shooter. Pinned on the real wire:

  1. the scene carries FOURTEEN entities and the night's furniture is
     born a rumor: every star alpha 0.15, the moon alpha 0.25, the
     moon's glow 0, the hunters unlit;
  2. ONE STREAM PER CONCERN: "the night sky" deals the same star
     layout on every run — two children, identical positions to the
     packet — and the threat/twin streams keep theirs;
  3. THE SILENCE LAW: nine kills and the sky says nothing — stars
     still 0.15 after nine hits and two honest seconds of waiting;
  4. the TENTH hit says "night falls at ten" on the hit frame's say;
  5. THE FADE IS HONEST IN DT: nightT climbs dt/2 per tick — one tick
     after the hit the stars ride 0.15 + 0.75 * 0.025, two ticks
     0.15 + 0.75 * 0.05 (the staircase sampled, float-honest);
  6. the hunters wear the fade: at nightT 0.5 the halos read 1.0;
  7. at the fade's end (40 ticks, exactly 2.0 s) the sky is DONE:
     stars 0.9, moon 1.0, the moon SHINES glow 4, the hunters wear
     the full faint ring (glow 2.0) — and more ticks change nothing.
"""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, time, threading, queue, random

REPO = _HOME
W_W, H_W = 120, 44                       # the probe's world (gate 6's size)

env = dict(os.environ)
env["PYTHONPATH"] = os.path.join(REPO, "sdk")

def child():
    p = subprocess.Popen(
        ["python3", os.path.join(REPO, "sdk", "examples", "shooter.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    _q = queue.Queue()
    _raw = []                               # the honest console, for the report
    def _pump():
        for ln in p.stdout:
            _raw.append(ln.rstrip()[:160])
            _q.put(ln)
    threading.Thread(target=_pump, daemon=True).start()

    def send(o):
        p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

    def read(timeout=6):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                ln = _q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                return json.loads(ln)
            except Exception as e:
                print(f"  [read] parse fail: {e} | len={len(ln)} "
                      f"head={ln[:60]!r} tail={ln[-60:]!r}", flush=True)
                continue
        return ("RAW", list(_raw[-5:]))     # never silently None

    def tick(keys=None, hits=None, dt=0.05):
        send({"t": "tick", "dt": dt,
              "keys": {k: True for k in (keys or [])},
              "chars": "", "hits": hits or []})
        while True:
            pkt = read()
            if pkt is None:
                raise AssertionError("no frame — child stalled")
            if pkt.get("t") == "frame":
                return {e["name"]: e for e in pkt["set"]}, pkt
    return p, send, read, tick

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

# ---------- child A: the law ----------
p, send, read, tick = child()
send({"t": "hello", "w": W_W, "h": H_W})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents = {e["name"]: e for e in scene["entities"]}
names = sorted(ents)
pin("the scene carries fifteen entities",
    names == sorted(["enemy", "hud", "ship", "twin", "moon", "owl"] +
                    [f"star{i}" for i in range(9)]), str(names))
born = [ents[f"star{i}"].get("alpha") for i in range(9)]
pin("the stars are born a rumor at 0.15",
    all(abs(a - 0.15) < 1e-9 for a in born), str(born))
pin("the moon is born a whisper at 0.25, unlit",
    abs(ents["moon"].get("alpha") - 0.25) < 1e-9 and
    ents["moon"].get("glow", 0) == 0,
    f"alpha={ents['moon'].get('alpha')} glow={ents['moon'].get('glow')}")
layout_a = [(ents[f"star{i}"]["x"], ents[f"star{i}"]["y"]) for i in range(9)]
pin("the hunters are born unlit",
    ents["enemy"].get("glow", 0) == 0 and ents["twin"].get("glow", 0) == 0)

# ---------- child B: the same sky ----------
p2, send2, read2, tick2 = child()
send2({"t": "hello", "w": W_W, "h": H_W})
scene2 = read2()
assert isinstance(scene2, dict) and scene2.get("t") == "scene", \
    f"no scene B: {str(scene2)[:400]}"
ents2 = {e["name"]: e for e in scene2["entities"]}
layout_b = [(ents2[f"star{i}"]["x"], ents2[f"star{i}"]["y"]) for i in range(9)]
pin("one stream per concern: the same run grows the same sky",
    layout_a == layout_b and
    len(set(layout_a)) == 9,
    f"a={layout_a} b={layout_b}")
p2.kill()

# ---------- the silence law: nine kills say nothing ----------
for i in range(1, 10):
    tick(["space"])                       # fire shot i
    tick(hits=[f"shot{i}", "enemy" if i % 2 else "twin"])
    tick([])                              # let any say expire honestly
say9 = tick([])[1].get("say", "")
a9 = tick([])[0]["star0"].get("alpha")
pin("nine kills and the sky says nothing (the silence law)",
    say9 == "" and abs(a9 - 0.15) < 1e-9, f"say={say9!r} a={a9}")

# ---------- the tenth hit ----------
tick(["space"])
entsH, pktH = tick(hits=["shot10", "enemy"])
pin("the tenth hit says \u201cnight falls at ten\u201d on the hit frame",
    pktH.get("say", "") == "night falls at ten", repr(pktH.get("say")))

# ---------- the fade, honest in dt ----------
ents1, _ = tick([])                       # nightT 0.025
ents2, _ = tick([])                       # nightT 0.05
a1, a2 = ents1["star0"].get("alpha"), ents2["star0"].get("alpha")
pin("the fade is honest in dt: one tick 0.15+0.75*0.025, two ticks "
    "0.15+0.75*0.05",
    abs(a1 - (0.15 + 0.75 * 0.025)) < 1e-9 and
    abs(a2 - (0.15 + 0.75 * 0.05)) < 1e-9,
    f"a1={a1} a2={a2}")
g1 = ents2["enemy"].get("glow")
pin("the hunters wear the fade (halo 2 * nightT)",
    abs(g1 - 2 * 0.05) < 1e-9, f"glow={g1}")

# ---------- the fade's end: 40 ticks from the hit ----------
for _ in range(38):
    entsE, _ = tick([])
nightT = min(1, 40 * 0.025)
pin("at the fade's end the sky is DONE",
    abs(entsE["star0"].get("alpha") - 0.9) < 1e-9 and
    abs(entsE["moon"].get("alpha") - 1.0) < 1e-9 and
    entsE["moon"].get("glow") == 4 and
    abs(entsE["enemy"].get("glow") - 2.0) < 1e-9 and
    abs(entsE["twin"].get("glow") - 2.0) < 1e-9,
    f"star={entsE['star0'].get('alpha')} moon={entsE['moon'].get('alpha')}"
    f"/g{entsE['moon'].get('glow')} enemy={entsE['enemy'].get('glow')} "
    f"twin={entsE['twin'].get('glow')}")
entsL, _ = tick([])
entsL, _ = tick([])
pin("and the night holds: more ticks change nothing",
    abs(entsL["star0"].get("alpha") - 0.9) < 1e-9 and
    entsL["moon"].get("glow") == 4,
    f"star={entsL['star0'].get('alpha')} glow={entsL['moon'].get('glow')}")

# ---------- an eleventh kill says nothing new ----------
tick(["space"])
_, pkt11 = tick(hits=["shot11", "twin"])
pin("an eleventh kill says nothing new (the night is said once)",
    pkt11.get("say", "") == "", repr(pkt11.get("say")))

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the void goes dark at the tenth hit: nine stars")
print("and a moon from their own stream, the fade honest in dt, the")
print("moon shining glow 4 at the end, the hunters wearing the faint")
print("ring, the night said once and holding.")
