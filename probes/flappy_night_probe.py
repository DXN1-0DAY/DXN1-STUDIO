#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R25 probe: flappy.py "the night owns this sky too" — v3.1.66.
# The score turns the sky: night falls at 3, dawn at 8, and every
# five after. The dark fades over two honest seconds (the dino law),
# the moon rises and SHINES only when the fade completes, and the
# pipes DRESS FOR IT — pale by night with a faint halo (the cacti
# law), back to green at dawn. The probe PLAYS the seeded sky
# (bang-bang controller, the flappy_light precedent) through night,
# dawn, and back into the dark. Pins:
#   - scene 11 (sky + moon joined); day birth: sky alpha 0, moon 0.25
#   - night falls at 3: the say on the flip frame; pipes pale + glow 1
#   - the fade: sky alpha climbs 0.45 x nightT; moon rises to 1.0
#   - the moon SHINES only at the completed fade (glow 4, not before)
#   - dawn at 8: the say flips back; pipes green, glow 0; the sky
#     fades home to 0 and the moon dims (and the bird still lives)
#   - a fresh flight is a fresh day: death + restart restores day
import subprocess, sys, json, os, time, threading, queue

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
os.environ["PYTHONPATH"] = os.path.join(REPO, "sdk") + ":" + os.environ.get("PYTHONPATH", "")

p = subprocess.Popen(["python3", "-u", os.path.join(EX, "flappy.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, cwd=EX)

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

_q = queue.Queue()
def _pump():
    for ln in p.stdout:
        _q.put(ln)
    _q.put("")
threading.Thread(target=_pump, daemon=True).start()

def read(timeout=6):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            ln = _q.get(timeout=0.1)
        except queue.Empty:
            continue
        if not ln:
            return None
        try:
            return json.loads(ln)
        except Exception:
            continue
    return None

def frame(keys=False):
    send({"t": "tick", "dt": 0.05,
          "keys": {"space": True} if keys else {},
          "chars": "", "hits": []})
    while True:
        f = read()
        if f is None:
            raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

send({"t": "hello", "w": 100, "h": 44})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
pin("scene has 11 entities", len(scene["entities"]) == 11,
    str(len(scene["entities"])))
birth = {e["name"]: e for e in scene["entities"]}
pin("day birth: sky dark-less (alpha 0), moon faint (0.25, no glow)",
    birth["sky"].get("alpha", 1) == 0
    and birth["moon"].get("alpha") == 0.25 and birth["moon"].get("glow", 0) == 0,
    f"sky={birth['sky'].get('alpha')} moon={birth['moon'].get('alpha')}")

# the bang-bang pilot (the flappy_light precedent): tick runs before
# keys, so a flap in packet N bites in tick N+1 (the R23 law)
state = {"prev_y": None, "flap": False}

def step():
    ents, f = frame(keys=state["flap"])
    y = ents["bird"]["y"]
    vy = (y - state["prev_y"]) if state["prev_y"] is not None else 0.0
    state["prev_y"] = y
    if ents["bird"].get("flash", 0) == 0:
        nxt = None
        for j in range(3):
            x = ents[f"ptop{j}"]["x"]
            if x + 6 >= 16 and (nxt is None or x < ents[f"ptop{nxt}"]["x"]):
                nxt = j
        if nxt is None:
            nxt = 0
        target = ents[f"ptop{nxt}"]["h"] + 3.0
        state["flap"] = (y + vy + 0.16 > target + 2.2)
    return ents, f

# ---- fly to the third pass: NIGHT FALLS AT 3
flip_say, flip_ents = None, None
for _ in range(1400):
    ents, f = step()
    if ents["bird"].get("flash", 0) > 0:
        break
    if ents["hud"]["text"] == "SCORE 3":
        flip_say = f.get("say") or ""
        flip_ents = ents
        break
pin("the probe PLAYS to nightfall (SCORE 3, bird alive)",
    flip_ents is not None and flip_ents["bird"].get("flash", 0) == 0,
    f"hud={flip_ents['hud']['text'] if flip_ents else 'dead'}")
pin("the flip speaks ('night falls at 3')",
    flip_say == "night falls at 3", repr(flip_say))
pin("the pipes dress pale on the flip",
    flip_ents["ptop0"].get("color") == "#4ade80"
    and flip_ents["pbot0"].get("color") == "#34d399",
    f"{flip_ents['ptop0'].get('color')}/{flip_ents['pbot0'].get('color')}")
pin("and wear their faint halo (glow 1)",
    flip_ents["ptop0"].get("glow", 0) == 1 and flip_ents["pbot1"].get("glow", 0) == 1,
    f"{flip_ents['ptop0'].get('glow')}/{flip_ents['pbot1'].get('glow')}")

# ---- the fade: 2s at 0.5/s; the moon shines ONLY at completion
saw_shine_early = False
completed = False
for _ in range(60):                      # 60 x 0.05 = 3 s > 2 s fade
    ents, f = step()
    if ents["bird"].get("flash", 0) > 0:
        break
    if ents["moon"].get("glow", 0) == 4 and ents["sky"].get("alpha", 0) < 0.45:
        saw_shine_early = True           # shining before the fade completed
    if ents["sky"].get("alpha", 0) == 0.45:
        completed = True
        break
pin("the dark faded all the way in (sky alpha 0.45)", completed,
    f"sky={ents['sky'].get('alpha')}")
pin("the moon rose with it (alpha 1.0)",
    ents["moon"].get("alpha", 0) == 1.0, f"{ents['moon'].get('alpha')}")
pin("the moon SHINES only at the completed fade (glow 4, never early)",
    not saw_shine_early and ents["moon"].get("glow", 0) == 4,
    f"early={saw_shine_early} glow={ents['moon'].get('glow')}")

# ---- fly to the eighth pass: DAWN AT 8
dawn_say, dawn_ents = None, None
for _ in range(2600):
    ents, f = step()
    if ents["bird"].get("flash", 0) > 0:
        break
    if ents["hud"]["text"] == "SCORE 8":
        dawn_say = f.get("say") or ""
        dawn_ents = ents
        break
pin("the probe PLAYS through the night to dawn (SCORE 8, alive)",
    dawn_ents is not None and dawn_ents["bird"].get("flash", 0) == 0,
    f"hud={dawn_ents['hud']['text'] if dawn_ents else 'dead'}")
pin("the flip speaks ('dawn at 8')", dawn_say == "dawn at 8", repr(dawn_say))
pin("the pipes dress green again",
    dawn_ents["ptop0"].get("color") == "#22c55e"
    and dawn_ents["ptop0"].get("glow", 0) == 0,
    f"{dawn_ents['ptop0'].get('color')}/{dawn_ents['ptop0'].get('glow')}")

# ---- the sky fades home; the bird still lives through it
faded = False
for _ in range(60):
    ents, f = step()
    if ents["bird"].get("flash", 0) > 0:
        break
    if ents["sky"].get("alpha", 1) == 0:
        faded = True
        break
pin("the sky faded home to day (alpha 0)", faded,
    f"sky={ents['sky'].get('alpha')}")
pin("the moon dims to its day haunting (0.25, no glow)",
    ents["moon"].get("alpha") == 0.25 and ents["moon"].get("glow", 0) == 0,
    f"{ents['moon'].get('alpha')}/{ents['moon'].get('glow')}")
pin("and the bird still lives", ents["bird"].get("flash", 0) == 0.0,
    f"{ents['bird'].get('flash')}")

# ---- a fresh flight is a fresh day: die, restart, the day holds
for _ in range(50):
    ents, f = frame(keys=False)          # stop flapping — the fall
    if ents["bird"].get("flash", 0) > 0:
        break
ents, f = frame(keys=True)               # the restart flap
restored = (ents["sky"].get("alpha", 1) == 0
            and ents["moon"].get("alpha") == 0.25
            and ents["ptop0"].get("color") == "#22c55e")
pin("death + restart restores the fresh day",
    restored, f"sky={ents['sky'].get('alpha')} top={ents['ptop0'].get('color')}")

print()
if fails:
    print(f"PROBE RED: {fails}"); sys.exit(2)
print("PROBE GREEN — the night owns this sky too")
