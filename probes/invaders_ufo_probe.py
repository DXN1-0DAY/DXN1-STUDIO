#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R22 probe: invaders.js "the mystery takes the sky" — over the real
# wire (node SDK) at the host's own geometry (120x84).
# pins: 62 entities (the night sky rides along); the saucer rests parked and DARK until the gun
# 13th LAUNCHED shot (muzzle glow 4 marks each launch) — not 12, not
# 14; it crosses as its own lantern (glow 4) at exactly +/-1.6 px per
# packet; their bombs cannot touch it (injected, refused, score still);
# a steered + LED host kills it — the say speaks the SAME number the
# score keeps (50/100/150/300), the saucer rests dark, the shot parks
# dark; the tally continues — launch 26 summons it again; and an
# unpurchased crossing parks dark at the far edge.
import json, subprocess, sys, os, select

REPO = _HOME
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []
UFOS = [50, 100, 150, 300]

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

def frame(keys=None, chars="", dt=0.1, hits=None):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": chars, "hits": hits or []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

W, H = 120, 84
send({"t": "hello", "w": W, "h": H})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
names = [e["name"] for e in scene["entities"]]
pin("scene has 62 entities", len(names) == 62, str(len(names)))
pin("the saucer exists and is tagged ufo",
    "saucer" in names and scene["entities"][names.index("saucer")].get("tag") == "ufo")

ents, f = frame()
s = ents["saucer"]
pin("the mystery starts parked and dark",
    s["x"] == -999 and s.get("glow", 0) == 0, f"x={s['x']} glow={s.get('glow')}")

# --- dodge helper: steer away from any bomb about to land on us -------
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

# --- 1. the summon law: 12 launches stay silent, the 13th calls it ----
launches = 0
summon_frame = None
flight_xs = []
for i in range(400):
    keys = dodge(ents) + ["space"]
    prev = launches
    ents, f = frame(keys=keys)
    if ents["player"].get("glow") == 4:            # the muzzle speaks a launch
        launches += 1
    if launches == 12 and prev == 11:
        parked_now = ents["saucer"]["x"] == -999 and ents["saucer"].get("glow", 0) == 0
        pin("12 launches and the sky is still empty", parked_now,
            f"x={ents['saucer']['x']} glow={ents['saucer'].get('glow')}")
    if launches == 13:
        s = ents["saucer"]
        ok = s["x"] > -100 and s.get("glow") == 4 and (f.get("say") or "") != ""
        pin("the 13th LAUNCHED shot summons the mystery (lit, announced)",
            ok, f"x={s['x']} glow={s.get('glow')} say={f.get('say')!r}")
        summon_frame = True
        break
pin("the summon arrived inside the packet budget", summon_frame is not None)

# --- 2. the flight law: exactly vx*dt per packet, lantern lit ---------
if summon_frame:
    vx = None
    steady = True
    for i in range(6):
        prev_x = ents["saucer"]["x"]
        ents, f = frame(keys=dodge(ents))
        s = ents["saucer"]
        if s["x"] <= -100: break
        d = s["x"] - prev_x
        if vx is None: vx = d
        if abs(d - vx) > 1e-9 or abs(abs(vx) - 1.6) > 1e-9: steady = False
        if s.get("glow") != 4: steady = False
    pin("the crossing walks exactly 1.6 px per packet (16 px/s)",
        steady, f"vx={vx}")
    pin("the lantern holds (glow 4) through the flight", steady)

    # --- 3. their bombs cannot touch it: injected, refused ------------
    score_before = ents["hud"]["text"]
    ents, f = frame(keys=dodge(ents), hits=["bomb-0", "saucer"])
    s = ents["saucer"]
    pin("a bomb refuses to pay the mystery (still flying, same score)",
        s["x"] > -100 and s.get("glow") == 4 and ents["hud"]["text"] == score_before,
        f"x={s['x']} hud={ents['hud']['text']}")

    # --- 4. the kill: steer, LEAD the crossing, fire, honest overlap ---
    paid = None
    for attempt in range(60):
        s = ents["saucer"]
        if s["x"] <= -100: break                      # escaped — retry law below
        climb = (ents["player"]["y"] - 4 - (s["y"] + 3)) / 4.0   # packets to reach
        predict = s["x"] + 5 + vx * max(0.0, climb - 1)          # lead the crossing
        aim = predict - 4                              # shot spawns at px+4
        keys = dodge(ents, aim=aim)
        if abs((ents["player"]["x"] + 4) - predict) < 4 and "space" not in keys:
            keys.append("space")
        ents, f = frame(keys=keys)
        # the honest overlap: a flying shot geometrically on the saucer
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
            break
    s = ents["saucer"]
    say = f.get("say") or ""
    import re
    m = re.search(r"the mystery pays (\d+)", say)
    if m:
        n = int(m.group(1))
        old = re.search(r"score (\d+)", score_before)
        new = re.search(r"score (\d+)", ents["hud"]["text"])
        delta = int(new.group(1)) - int(old.group(1)) if old and new else -1
        pin("the bounty is from the purse (50/100/150/300)", n in UFOS, str(n))
        pin("the say speaks the SAME number the score keeps", delta == n,
            f"say={n} delta={delta}")
        pin("the paid saucer rests dark", s["x"] == -999 and s.get("glow", 0) == 0,
            f"x={s['x']} glow={s.get('glow')}")
        spent = ents[hits[0]] if hits and hits[0] in ents else None
        pin("the killing shot parks dark too",
            spent is not None and spent["x"] == -999 and spent.get("glow", 0) == 0)
    else:
        pin("the mystery pays (say announced)", False, f"say={say!r}")

# --- 5. the tally continues: launch 26 summons again -------------------
launches2 = 0
second = False
for i in range(400):
    keys = dodge(ents) + ["space"]
    ents, f = frame(keys=keys)
    if ents["player"].get("glow") == 4:
        launches2 += 1
    if launches2 >= 13 and ents["saucer"]["x"] > -100:
        second = True
        break
s = ents["saucer"]
pin("the tally continues — 13 more shots summon it again",
    second, f"launches2={launches2} x={s['x']}")

# --- 6. the unpurchased crossing parks dark at the far edge ------------
if second:
    esc = False
    for i in range(200):
        ents, f = frame(keys=dodge(ents))
        if ents["saucer"]["x"] == -999:
            esc = True
            break
    s = ents["saucer"]
    pin("an unpurchased crossing parks dark at the edge",
        esc and s.get("glow", 0) == 0, f"x={s['x']} glow={s.get('glow')}")

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the mystery takes the sky")
