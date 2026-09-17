#!/usr/bin/env python3
"""probe for sdk/examples/invaders.js — THE SECOND WAVE COMES IN THE
DARK (v3.1.78). The moon check's last big fleet member, pinned on the
real wire:

  1. the scene carries SIXTY-TWO entities and the night's furniture
     is born a rumor: every star alpha 0.15, the moon 0.25 and unlit;
  2. ONE STREAM PER CONCERN: "the night sky" (FNV-1a + xorshift32,
     the dino's law) deals the same star layout on every run — two
     children, identical positions, and the probe predicts them from
     the replicated stream;
  3. THE SILENCE LAW: fourteen kills and the sky says nothing — the
     war starts in daylight, the stars stay 0.15;
  4. the FIFTEENTH kill clears wave one: the say speaks "wave 1
     cleared — the sky fills again, darker now" on the rebuild frame,
     and the stars are STILL 0.15 there (the fade pays next tick —
     the hit-pair timing contract);
  5. THE FADE IS HONEST IN DT: one tick later the stars ride
     0.15 + 0.75 * 0.025, two ticks 0.15 + 0.75 * 0.05, and the
     visible march wears the cacti ring (glow = nightT);
  6. at the fade's end the sky is DONE: stars 0.9, moon 1.0, the moon
     SHINES glow 4, the march rings at 1.0;
  7. A FRESH RUN IS A FRESH DAY: three bombs take the cannon down,
     r rebuilds — and the daylight is poured back (stars 0.15, moon
     0.25, unlit).
"""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
import json, subprocess, sys, os, time, threading, queue, math

REPO = _HOME
W_W, H_W = 120, 44                       # the probe's world (gate 6's size)

env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")

def child():
    p = subprocess.Popen(
        ["node", os.path.join(REPO, "sdk", "examples", "invaders.js")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    _q = queue.Queue()
    _raw = []
    def _pump():
        for ln in p.stdout:
            _raw.append(ln.rstrip()[:160])
            _q.put(ln)
    threading.Thread(target=_pump, daemon=True).start()

    def send(o):
        p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

    def read(timeout=8):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                ln = _q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                return json.loads(ln)
            except Exception:
                continue
        return ("RAW", list(_raw[-5:]))     # never silently None

    def tick(keys=None, hits=None, dt=0.05, chars=""):
        send({"t": "tick", "dt": dt,
              "keys": {k: True for k in (keys or [])},
              "chars": chars, "hits": hits or []})
        while True:
            pkt = read()
            if not isinstance(pkt, dict):
                raise AssertionError(f"child stalled: {str(pkt)[:200]}")
            if pkt.get("t") == "frame":
                return {e["name"]: e for e in pkt["set"]}, pkt
    return p, send, read, tick

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name +
          (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

# the replicated stream — the dino's law in python. THE FLOAT TRAP:
# JS multiplies in float64 — sseed * 16777619 exceeds 2^53 and ToUint32
# then keeps only the exact float's low bits — so the replication must
# multiply in float and truncate, never in clean int math.
def to_int32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x

def to_uint32_f(x):                      # ToUint32 of a float64
    return int(math.fmod(x, 4294967296.0)) % 4294967296

seed = 2166136261
for ch in "the night sky":
    # the honest line — XOR in int32, multiply in float64, ToUint32:
    seed = to_uint32_f(float(to_int32(seed) ^ ord(ch)) * 16777619.0)
def nnext():
    global seed
    seed = (seed ^ ((seed << 13) & 0xFFFFFFFF)) & 0xFFFFFFFF
    seed = (seed ^ (seed >> 17)) & 0xFFFFFFFF
    seed = (seed ^ ((seed << 5) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return seed / 4294967296
expected = []
for _ in range(9):
    expected.append((2 + math.floor(nnext() * (W_W - 6)),
                     3 + math.floor(nnext() * 9)))

# ---------- child A: the law ----------
p, send, read, tick = child()
send({"t": "hello", "w": W_W, "h": H_W})
scene = read()
assert isinstance(scene, dict) and scene.get("t") == "scene", \
    f"no scene: {str(scene)[:300]}"
ents = {e["name"]: e for e in scene["entities"]}
names = sorted(ents)
pin("the scene carries sixty-two entities",
    len(names) == 62 and
    all(f"star-{i}" in ents for i in range(9)) and "moon" in ents,
    f"{len(names)}: {names[:6]}...")
born = [ents[f"star-{i}"].get("alpha") for i in range(9)]
pin("the stars are born a rumor at 0.15",
    all(abs(a - 0.15) < 1e-9 for a in born), str(born))
pin("the moon is born a whisper at 0.25, unlit",
    abs(ents["moon"].get("alpha") - 0.25) < 1e-9 and
    ents["moon"].get("glow", 0) == 0,
    f"alpha={ents['moon'].get('alpha')} glow={ents['moon'].get('glow')}")
got = [(ents[f"star-{i}"]["x"], ents[f"star-{i}"]["y"]) for i in range(9)]
pin("the stars sit EXACTLY where the replicated stream deals them",
    got == expected, f"got={got} exp={expected}")

# ---------- child B: the same sky ----------
p2, send2, read2, tick2 = child()
send2({"t": "hello", "w": W_W, "h": H_W})
scene2 = read2()
assert isinstance(scene2, dict) and scene2.get("t") == "scene", \
    f"no scene B: {str(scene2)[:300]}"
ents2 = {e["name"]: e for e in scene2["entities"]}
got2 = [(ents2[f"star-{i}"]["x"], ents2[f"star-{i}"]["y"]) for i in range(9)]
pin("one stream per concern: the same run grows the same sky",
    got == got2, f"a={got} b={got2}")
p2.kill()

# ---------- the silence law: fourteen kills ----------
for k in range(14):
    r, c = k % 3, k // 3                 # walk the seats row by row
    tick(hits=[f"shot-0", f"alien-{r}-{c}"])
    tick([])
say14 = tick([])[1].get("say", "")
a14 = tick([])[0]["star-0"].get("alpha")
pin("fourteen kills and the sky says nothing (the war starts in day)",
    say14 == "" and abs(a14 - 0.15) < 1e-9, f"say={say14!r} a={a14}")

# ---------- the fifteenth kill: wave one clears, night earns in ----------
entsH, pktH = tick(hits=["shot-0", "alien-2-4"])
pin("the fifteenth kill speaks the darker rebuild on its own frame",
    pktH.get("say", "") == "wave 1 cleared \u2014 the sky fills again, "
    "darker now", repr(pktH.get("say")))
aH = entsH.get("star-0", {}).get("alpha")
pin("and the stars are still 0.15 on the rebuild frame (the fade "
    "pays next tick)",
    aH is not None and abs(aH - 0.15) < 1e-9, f"a={aH}")

# ---------- the fade, honest in dt ----------
ents1, _ = tick([])
ents2, _ = tick([])
a1, a2 = ents1["star-0"].get("alpha"), ents2["star-0"].get("alpha")
g2 = ents2.get("alien-0-0", {}).get("glow")
pin("the fade is honest in dt: 0.15+0.75*0.025 then 0.15+0.75*0.05",
    abs(a1 - (0.15 + 0.75 * 0.025)) < 1e-9 and
    abs(a2 - (0.15 + 0.75 * 0.05)) < 1e-9, f"a1={a1} a2={a2}")
pin("the march wears the cacti ring (glow = nightT)",
    g2 is not None and abs(g2 - 0.05) < 1e-9, f"glow={g2}")

# ---------- the fade's end ----------
for _ in range(38):
    entsE, _ = tick([])
pin("at the fade's end the sky is DONE",
    abs(entsE["star-0"].get("alpha") - 0.9) < 1e-9 and
    abs(entsE["moon"].get("alpha") - 1.0) < 1e-9 and
    entsE["moon"].get("glow") == 4 and
    abs(entsE.get("alien-0-0", {}).get("glow", 0) - 1.0) < 1e-9,
    f"star={entsE['star-0'].get('alpha')} moon={entsE['moon'].get('alpha')}"
    f"/g{entsE['moon'].get('glow')} alien={entsE.get('alien-0-0', {}).get('glow')}")

# ---------- a fresh run is a fresh day ----------
lives_log, win_seen = [], ""
for i in range(3):
    entsHi, pktHi = tick(hits=["bomb-0", "player"])
    if pktHi.get("win", ""): win_seen = pktHi["win"]
    lives_log.append(entsHi.get("hud", {}).get("text", ""))
    tick([])
pin("three bombs end the run (EARTH FALLS rides the hit frame)",
    win_seen == "EARTH FALLS", f"win={win_seen!r} hud={lives_log}")
entsR, pktR = tick(chars="r")   # letters ride chars, not keys
pin("r speaks the reborn",
    pktR.get("say", "") == "the cannon is reborn", repr(pktR.get("say")))
entsD, _ = tick([])
pin("and the daylight is poured back",
    abs(entsD["star-0"].get("alpha") - 0.15) < 1e-9 and
    abs(entsD["moon"].get("alpha") - 0.25) < 1e-9 and
    entsD["moon"].get("glow", 0) == 0,
    f"star={entsD['star-0'].get('alpha')} moon={entsD['moon'].get('alpha')}"
    f"/g{entsD['moon'].get('glow')}")

p.kill()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the second wave comes in the dark: the sky")
print("from its own stream, the fade honest in dt, the moon shining at")
print("the end, the march ringing faintly, and a fresh run pouring the")
print("daylight back.")
