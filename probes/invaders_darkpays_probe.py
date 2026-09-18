#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.98): this pin lived outside the walls since
# R32 and flaked ~50% there — the flake hunt named the mechanism, and it
# was never the engine's. The night purse is pay*2 over UFOS=[50,100,150,
# 300], so the doubled set is {100,200,300,600} — which OVERLAPS the day
# set at 100 and 300. The old pin "the doubled purse is never an odd
# purse value" (n not in UFOS) was therefore UNSATISFIABLE whenever the
# drawn tier was 50 or 150 — two of the four tiers, exactly the ~50%
# red. A pin that depends on the draw is a horoscope; the law's honest,
# draw-proof content: the night purse HALVES into an honest day purse
# (n // 2 in UFOS), the say speaks the doubling, and the kill frame
# stands in the proven dark (the moon's glow tracked to the kill tick,
# the capture-at-the-kill-frame proof the R36 candidate asked for).
# DS2-R32 probe: invaders.js "the dark pays double" — over the real
# wire (node SDK) at the host's own geometry (120x84).
# pins: a DAY kill pays the honest purse (50/100/150/300) with NO
# suffix; the wave-1 clear speaks "the sky fills again, darker now";
# the fade is honest in dt — 20 packets later the moon SHINES (glow 4,
# alpha 1.0) and the stars ride 0.9; the tally continues — 13 more
# launches summon the mystery again, now under moonlight; a kill in
# the FULL dark pays the DOUBLED purse — the say says "the dark pays
# double", the purse halves into the day set, the score keeps the SAME
# number, the kill frame stands in the full dark, and both saucer and
# shot rest dark.
import json, subprocess, sys, os, select, re

REPO = _HOME
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []
UFOS = [50, 100, 150, 300]
DOUBLE = [n * 2 for n in UFOS]

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "invaders.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def read(timeout=4.0):
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r: return None
    line = p.stdout.readline()
    if not line: return None
    try: return json.loads(line)
    except Exception: return None

# the moon's last seen state, tracked across every frame — the kill
# frame's darkness is read from this ledger (frames are deltas: the
# moon only appears when it changes, so the ledger, not the frame,
# carries the truth to the kill tick)
MOON = {"alpha": None, "glow": None}

def frame(keys=None, chars="", dt=0.1, hits=None):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": hits or []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            for e in f["set"]:
                if e.get("name") == "moon":
                    MOON["alpha"] = e.get("alpha")
                    MOON["glow"] = e.get("glow", 0)
            return {e["name"]: e for e in f["set"]}, f

W, H = 120, 84
send({"t": "hello", "w": W, "h": H})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
names = [e["name"] for e in scene["entities"]]
pin("scene has 62 entities (the night sky included)", len(names) == 62, str(len(names)))

ents, f = frame()
s = ents["saucer"]
pin("the mystery starts parked and dark (day)",
    s["x"] == -999 and s.get("glow", 0) == 0, f"x={s['x']} glow={s.get('glow')}")
moon0 = ents["moon"]
pin("the moon starts a whisper (0.25, unlit)",
    abs(moon0["alpha"] - 0.25) < 1e-9 and moon0.get("glow", 0) == 0,
    f"alpha={moon0['alpha']} glow={moon0.get('glow')}")

def dodge(ents, aim=None):
    px = ents["player"]["x"]
    keys = []
    threat = None
    for bi in range(3):
        b = ents[f"bomb-{bi}"]
        if b["x"] > -100 and b["y"] > 30 and abs(b["x"] - px) < 9:
            if threat is None or b["y"] > ents[f"bomb-{threat}"]["y"]:
                threat = bi
    if aim is not None:
        if aim > px + 1: keys.append("right")
        elif aim < px - 1: keys.append("left")
    elif threat is not None:
        bx = ents[f"bomb-{threat}"]["x"]
        keys.append("right" if bx > px else "left")
    return keys

def summon_and_kill(ents, dark):
    """13 launches, then the lead-and-steer honest-overlap kill.
    Returns (ents, f, shotname, score_before) — score_before is the hud
    text the payment packet started from."""
    launches = 0
    summoned = False
    vx = None
    f = {}
    for i in range(500):
        keys = dodge(ents) + ["space"]
        ents, f = frame(keys=keys)
        if ents["player"].get("glow") == 4:
            launches += 1
        if launches >= 13 and ents["saucer"]["x"] > -100:
            summoned = True
            break
    if not summoned:
        return ents, f, None, None
    # measure the crossing speed, then hunt
    for attempt in range(3):
        if ents["saucer"]["x"] <= -100:          # escaped — summon again
            launches = 0
            ok = False
            for i in range(500):
                keys = dodge(ents) + ["space"]
                ents, f = frame(keys=keys)
                if ents["player"].get("glow") == 4: launches += 1
                if launches >= 13 and ents["saucer"]["x"] > -100:
                    ok = True; break
            if not ok: return ents, f, None, None
        for i in range(6):
            prev_x = ents["saucer"]["x"]
            ents, f = frame(keys=dodge(ents))
            if ents["saucer"]["x"] <= -100: break
            d = ents["saucer"]["x"] - prev_x
            vx = d if vx is None else vx
        # the hunt: lead the crossing, fire, honest overlap
        for i in range(90):
            s = ents["saucer"]
            if s["x"] <= -100: break             # escaped this pass
            climb = (ents["player"]["y"] - 4 - (s["y"] + 3)) / 4.0
            predict = s["x"] + 5 + vx * max(0.0, climb - 1)
            aim = predict - 4
            keys = dodge(ents, aim=aim)
            if abs((ents["player"]["x"] + 4) - predict) < 4 and "space" not in keys:
                keys.append("space")
            ents, f = frame(keys=keys)
            hits = []
            for si in range(3):
                sh = ents[f"shot-{si}"]
                if sh["x"] > -100 and sh["x"] < s["x"] + 12 and sh["x"] + 2 > s["x"] \
                   and sh["y"] < s["y"] + 3 and sh["y"] + 4 > s["y"]:
                    hits = [sh["name"], "saucer"]
                    break
            if hits:
                score_before = ents["hud"]["text"]
                ents, f = frame(keys=dodge(ents), hits=hits)
                return ents, f, hits[0], score_before
    return ents, f, None, None

# --- 1. the DAY law: the honest purse, no suffix -----------------------
ents, f, shotname, score_before = summon_and_kill(ents, dark=False)
say = f.get("say") or ""
m = re.search(r"the mystery pays (\d+)", say)
if m and shotname and score_before:
    n = int(m.group(1))
    pin("a DAY kill pays the honest purse (50/100/150/300)", n in UFOS, str(n))
    pin("the day say carries NO double suffix", "double" not in say, say)
    old = re.search(r"score (\d+)", score_before)
    new = re.search(r"score (\d+)", ents["hud"]["text"])
    delta = int(new.group(1)) - int(old.group(1)) if old and new else -1
    pin("the day say speaks the SAME number the score keeps", delta == n,
        f"say={n} delta={delta}")
    pin("the day saucer rests dark",
        ents["saucer"]["x"] == -999 and ents["saucer"].get("glow", 0) == 0)
else:
    pin("the day mystery paid (say announced)", False, f"say={say!r}")

# --- 2. force the dark: one honest packet per alien seat ---------------
# the seats are named alien-<row>-<col> — fifteen of them
cleared = False
for r in range(3):
    for c in range(5):
        ents, f = frame(hits=[f"alien-{r}-{c}", "shot-0"], keys=dodge(ents))
        if "darker now" in (f.get("say") or ""):
            cleared = True
pin("the 15th seat cleared speaks the darker sky", cleared,
    f"say={f.get('say')!r}")

# --- 3. the fade is honest in dt: 20 packets, then the moon SHINES -----
shines = False
for i in range(30):
    ents, f = frame()
    if ents["moon"].get("glow") == 4:
        shines = True
        break
moon = ents["moon"]
stars_full = all(abs(ents[f"star-{i}"]["alpha"] - 0.9) < 1e-9 for i in range(9))
pin("the fade ends — the moon SHINES (glow 4)", shines,
    f"alpha={moon['alpha']} glow={moon.get('glow')}")
pin("the moon reached full (alpha 1.0)", abs(moon["alpha"] - 1.0) < 1e-9,
    str(moon["alpha"]))
pin("the nine stars ride 0.9", stars_full,
    str([ents[f"star-{i}"]["alpha"] for i in range(3)]))
pin("the living march wears the cacti ring",
    all((ents[f"alien-{r}-{c}"].get("glow", 0) == 1) or
        ents[f"alien-{r}-{c}"]["visible"] == 0
        for r in range(3) for c in range(5)))

# --- 4. the NIGHT law: the doubled purse, the say says so --------------
ents, f, shotname, score_before = summon_and_kill(ents, dark=True)
say = f.get("say") or ""
m = re.search(r"the mystery pays (\d+)", say)
if m and shotname and score_before:
    n = int(m.group(1))
    pin("a kill in the FULL dark pays the DOUBLED purse (100/200/300/600)",
        n in DOUBLE, str(n))
    pin("the night purse halves into an honest day purse (50/100/150/300)",
        n % 2 == 0 and n // 2 in UFOS, str(n))
    pin("the night say speaks 'the dark pays double'",
        "the dark pays double" in say, say)
    old = re.search(r"score (\d+)", score_before)
    new = re.search(r"score (\d+)", ents["hud"]["text"])
    delta = int(new.group(1)) - int(old.group(1)) if old and new else -1
    pin("the night say speaks the SAME number the score keeps", delta == n,
        f"say={n} delta={delta}")
    pin("the kill frame stands in the full dark (the moon shines at "
        "the kill tick)",
        MOON["glow"] == 4 and abs(MOON["alpha"] - 1.0) < 1e-9,
        f"moon alpha={MOON['alpha']} glow={MOON['glow']}")
    pin("the paid saucer rests dark",
        ents["saucer"]["x"] == -999 and ents["saucer"].get("glow", 0) == 0)
    spent = ents.get(shotname)
    pin("the killing shot parks dark too",
        spent is not None and spent["x"] == -999 and spent.get("glow", 0) == 0)
else:
    pin("the night mystery paid (say announced)", False, f"say={say!r}")

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the dark pays double, and the ledger proves it")
sys.exit(0)
