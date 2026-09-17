#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R24 probe: dino.js "the noon dragonfly" — v3.1.62. The owl hunts
# the jump; the dragonfly THANKS it: it crosses a band (rows H-15/H-14)
# only a leap's shoulders reach — time the leap and the run pays
# (+1 snack, the runner glows). Its OWN seeded stream ("the noon
# dragonfly"); the owl's launch law (feet-down, nothing ahead, the draw
# only on a real launch); it NEVER kills (tag "snack"); the desert
# NEVER STOPS for it (no spawn freeze); and LUNCH SUMMONS THE SWARM
# (a catch pays one draw: 4-10 s to the next fly).
# WIRE LAWS this probe pays for:
#   - a bare wire child does NO collision detection: the STUDIO scans
#     the last frame's tagged pairs and forwards them in the next
#     packet — a probe harness must inject the hits itself
#   - the FNV seed multiplies in FLOAT64 and SIGNED int32 (the R22
#     law, re-learned: the unsigned python FNV diverges at draw one)
# Pins: 24 entities; honest first launch (feet-down, clear road); the
#   buzz rows; 1.2x crossing; zero-drift spawns (the desert never
#   stops); THE CATCH (glow 6 whole, 5.7/5.4 stairs); the summons
#   (launch 2 never early, no eligible tick skipped); no launch 3
#   before night; the owl intact; reseed on rebirth (same delta).
import subprocess, sys, json, os, select

REPO = _HOME
EX = os.path.join(REPO, "sdk", "examples")
DT = 0.05
W, H = 120, 84
GROUND = H - 9
FLY_COLOR = "#fdba74"

def fnv1a(name):
    # JS bitwise = SIGNED int32 (the R22 law) and JS * is a FLOAT64
    # multiply — the unsigned python FNV never matches. the owl probe's
    # mirror, bit for bit.
    h = 2166136261
    for ch in name:
        h ^= ord(ch)
        if h >= 1 << 31:
            h -= 1 << 32
        h = int(float(h) * 16777619) % (1 << 32)
    return h

class Rng:                                # the game's xorshift, bit for bit
    def __init__(self, name):
        self.s = fnv1a(name)
    def next(self):
        s = self.s
        s ^= (s << 13) & 0xFFFFFFFF
        s ^= s >> 17
        s ^= (s << 5) & 0xFFFFFFFF
        self.s = s & 0xFFFFFFFF
        return self.s / 4294967296

frng = Rng("the noon dragonfly")
F_LAUNCH1 = 10 + frng.next() * 12         # launch 1's countdown (19.996 s)
F_SUMMON = 4 + frng.next() * 6            # the catch's summons (7.552 s)
F_LAUNCH3 = 10 + frng.next() * 12         # would-be launch 3 (17.556 s)

env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
p = subprocess.Popen(["node", f"{EX}/dino.js"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     cwd=REPO, text=True, bufsize=1, env=env)

def send(o):
    try:
        p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
    except BrokenPipeError:
        return False
    return True

def read(timeout=6.0):
    r, _, _ = select.select([p.stdout], [], [], timeout)
    if not r: return None
    line = p.stdout.readline()
    if not line: return None
    try: return json.loads(line)
    except Exception: return None

def frame(keys=None, chars=None, hits=None):
    send({"t": "tick", "dt": DT,
          "keys": {k: True for k in (keys or [])},
          "chars": chars or "", "hits": hits or []})
    while True:
        f = read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

def hit_pairs(ents):
    # the studio's job, done by the harness: scan the LAST frame's
    # tagged pairs and forward them in this packet
    out = []
    dn = ents["dino"]
    for n in [f"cactus-{i}" for i in range(6)] + [f"fly-{i}" for i in range(2)]:
        e = ents[n]
        if e["x"] <= -100:
            continue
        if (dn["x"] < e["x"] + e["w"] and dn["x"] + dn["w"] > e["x"]
                and dn["y"] < e["y"] + e["h"] and dn["y"] + dn["h"] > e["y"]):
            out += ["dino", n]
    return out

def road_clear(ents):
    return all(ents[f"cactus-{j}"]["x"] <= -999
               or ents[f"cactus-{j}"]["x"] + ents[f"cactus-{j}"]["w"] <= 6
               for j in range(6))

def steer(ents, m_speed, catch_open, air_ticks):
    # the coordinated driver: dodge cacti, catch flies — one leap serves
    # both. the catch can ride a leap that is already rising (the fly's
    # band holds ticks ~2.7-13.3 of a leap; the x-overlap ~2.5 ticks).
    dino = ents["dino"]
    grounded = dino["y"] >= GROUND
    if grounded:
        air_ticks = None
    elif air_ticks is not None:
        air_ticks += 1
    keys = []
    dodge = False
    for i in range(6):
        c = ents[f"cactus-{i}"]
        if c["x"] > -100 and grounded:
            gap = c["x"] - 13
            if 0 < gap / m_speed < 0.30:
                dodge = True
    fly_name = "fly-0" if ents["fly-0"]["x"] > -100 else "fly-1"
    fly = ents[fly_name]
    want_catch = False
    if catch_open and fly["x"] > -100:
        d = fly["x"] - 13
        if grounded and 14 <= d <= 40:
            want_catch = True
        elif (air_ticks is not None and air_ticks <= 13
              and 2 < d + (air_ticks - 2) * 4.3 <= 13):
            want_catch = True
    if want_catch or dodge:
        keys.append("space")
        if air_ticks is None:
            air_ticks = 0
    return keys, air_ticks, fly_name

fails = []
def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

# ================= phase A: hello -> day (both flies) -> night =========
send({"t": "hello", "w": W, "h": H})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
sent = {e["name"]: e for e in scene["entities"]}
pin("scene has 24 entities (two owls, two flies parked)", len(sent) == 24,
    str(len(sent)))
flies_born = all(sent[f"fly-{i}"]["x"] == -999 and sent[f"fly-{i}"]["y"] == H - 15
                 and sent[f"fly-{i}"].get("color") == FLY_COLOR
                 and sent[f"fly-{i}"].get("glow") == 1
                 and sent[f"fly-{i}"].get("tag") == "snack" for i in range(2))
pin("the flies are born parked, amber, shimmering, tagged snack", flies_born)

m_speed, m_spawnIn = 55.0, 2.2
desert = Rng("the long run")
m_speed += 2 * DT; m_spawnIn -= DT        # the hello handshake ran once

ents, f = frame()
pkt = 0
PKT_A = 1400
night_pkt = None
owl_hoot_pkt = None
launches = []
spawns, predicted_spawns = [], []
catch_pkt = None
catch_say = None
glow_stairs = []
death_win = None
prev_cactus = {f"cactus-{i}": -999 for i in range(6)}
prev_fly = {"fly-0": -999, "fly-1": -999}
buzz_seen = set()
cross = []
last_x, last_name = None, None
air_ticks = None
eligible_skipped = 0

while pkt < PKT_A:
    pkt += 1
    if night_pkt and owl_hoot_pkt and pkt > night_pkt + int(4.0 / DT):
        break
    keys, air_ticks, fly_name = steer(ents, m_speed, catch_pkt is None, air_ticks)
    fly = ents[fly_name]
    ents, f = frame(keys=keys, hits=hit_pairs(ents))

    # --- mirror advance (the game's order) ----------------------------
    m_speed += 2 * DT
    owl_flying = any(ents[f"owl-{i}"]["x"] > -100 for i in range(2))
    m_spawnIn -= DT
    if m_spawnIn <= 0 and not owl_flying:
        desert.next()                              # the band draw
        m_spawnIn = 1.4 + desert.next() * (90 / m_speed) + 0.5
        predicted_spawns.append(pkt)
    # --- observations --------------------------------------------------
    say = str(f.get("say") or "")
    win = str(f.get("win") or "")
    for i in range(6):
        n = f"cactus-{i}"
        x = ents[n]["x"]
        if prev_cactus[n] <= -999 and x > -100:
            spawns.append(pkt)
        prev_cactus[n] = x
    for i in range(2):
        n = f"fly-{i}"
        x = ents[n]["x"]
        if prev_fly[n] <= -999 and x > -100:
            launches.append({"pkt": pkt, "name": n, "x": x, "y": ents[n]["y"],
                             "say": say, "speed": m_speed, "feet": ents["dino"]["y"],
                             "clear": road_clear(ents)})
        prev_fly[n] = x
    if fly["x"] > -100:
        buzz_seen.add(ents[fly_name]["y"])
        if last_name == fly_name and last_x is not None:
            cross.append(((last_x - fly["x"]) / DT, m_speed))
        last_x, last_name = fly["x"], fly_name
    if catch_pkt is None and "+1 snack" in say:
        catch_pkt = pkt
        catch_say = say
        glow_stairs.append(ents["dino"].get("glow"))
    elif catch_pkt is not None and len(glow_stairs) < 3:
        g = ents["dino"].get("glow", 0)
        if g > 0:
            glow_stairs.append(g)
    # the summons wait: between the countdown crossing and launch 2 the
    # launch law may hold the fly — but it may never SKIP an eligible tick
    if (catch_pkt is not None and len(launches) < 2
            and (pkt - catch_pkt) * DT >= F_SUMMON - DT):
        if ents["dino"]["y"] >= GROUND and road_clear(ents):
            eligible_skipped += 1
    if night_pkt is None and "night falls" in say:
        night_pkt = pkt
    if night_pkt and owl_hoot_pkt is None and "hoot" in say:
        owl_hoot_pkt = pkt
    if win and death_win is None:
        death_win = (pkt, win)
        break

# ================= phase B: death -> r -> reseed witness ===============
run2 = {"launches": [], "catch": None, "summon_delta": None}
if death_win is None:
    # force the death: walk blind (no dodges) until a cactus collects
    for _ in range(500):
        pkt += 1
        ents, f = frame(hits=hit_pairs(ents))
        if "night falls" in str(f.get("say") or "") and night_pkt is None:
            night_pkt = pkt
        win = str(f.get("win") or "")
        if win:
            death_win = (pkt, win)
            break
if death_win:
    ents, f = frame(chars="r")          # letters ride chars (the R15 law)
    pkt += 1
    prev2 = {"fly-0": -999, "fly-1": -999}
    caught2 = False
    air2 = None
    m2 = 55.0 + 2 * DT                  # walkAgain restarts the run's clock
    skipped2 = 0
    for _ in range(int(24.0 / DT)):
        pkt += 1
        keys, air2, _ = steer(ents, m2, not caught2, air2)
        m2 += 2 * DT
        ents, f = frame(keys=keys, hits=hit_pairs(ents))
        say = str(f.get("say") or "")
        if str(f.get("win") or ""):
            break                       # run 2 died — the pin below will say
        for i in range(2):
            n = f"fly-{i}"
            x = ents[n]["x"]
            if prev2[n] <= -999 and x > -100:
                run2["launches"].append(pkt)
            prev2[n] = x
        if not caught2 and "+1 snack" in say:
            caught2 = True
            run2["catch"] = pkt
        if (caught2 and len(run2["launches"]) < 2
                and (pkt - run2["catch"]) * DT >= F_SUMMON - DT
                and ents["dino"]["y"] >= GROUND and road_clear(ents)):
            skipped2 += 1
        if len(run2["launches"]) >= 2:
            run2["summon_delta"] = (run2["launches"][1] - run2["launches"][0]) * DT
            run2["skipped"] = skipped2
            break

p.kill()

# ---- pins -------------------------------------------------------------
pin("no fly launches before 8 s",
    launches and launches[0]["pkt"] >= int(8.0 / DT) - 1,
    f"first launch pkt {launches[0]['pkt'] if launches else None}")
L0 = launches[0] if launches else None
pin("the first launch is honest (one tick of flight, y H-15, bzzz)",
    L0 and abs(L0["x"] - (W + 2 - 1.2 * L0["speed"] * DT)) < 0.6
    and L0["y"] in (H - 15, H - 16) and "bzzz" in L0["say"],
    str({k: L0[k] for k in ("x", "y", "say")} if L0 else None))
pin("the launch law held (feet-down, clear road)",
    L0 and L0["feet"] >= GROUND and L0["clear"],
    f"feet {L0['feet'] if L0 else None} vs {GROUND}, clear {L0['clear'] if L0 else None}")
pin("the fly buzzes in its own two rows (H-16/H-15, never lower)",
    buzz_seen and max(buzz_seen) <= H - 15 and min(buzz_seen) >= H - 16,
    str(sorted(buzz_seen)))
if cross:
    ratios = [d / (1.2 * s) for d, s in cross]
    avg = sum(ratios) / len(ratios)
    pin("the fly crosses at 1.2x the run", abs(avg - 1.0) < 0.08,
        f"mean ratio {avg:.3f} over {len(ratios)} steps")
else:
    pin("the fly crosses at 1.2x the run", False, "no crossing steps seen")
n_cmp = min(len(spawns), len(predicted_spawns))
drift = max((abs(o - m) for o, m in zip(spawns[:n_cmp], predicted_spawns[:n_cmp])),
            default=999)
pin("the desert never stops: every spawn on the mirrored packet (zero drift)",
    len(predicted_spawns) >= 6 and n_cmp == len(predicted_spawns) and drift <= 2,
    f"{len(spawns)} observed vs {len(predicted_spawns)} mirrored, max drift {drift}")
pin("a spawn happened during the first fly's crossing",
    L0 and any(L0["pkt"] < s < L0["pkt"] + int(1.7 / DT) for s in spawns),
    f"launch pkt {L0['pkt'] if L0 else None}, spawns {spawns[:8]}")
pin("THE CATCH: +1 snack spoken, the noon pays",
    catch_pkt is not None and "snack" in (catch_say or ""), str(catch_say))
pin("the bite's light is born whole (glow 6)",
    glow_stairs and glow_stairs[0] == 6, str(glow_stairs[:3]))
pin("the glow wears at 6/s (5.7, 5.4)",
    len(glow_stairs) >= 3 and abs(glow_stairs[1] - 5.7) < 0.0011
    and abs(glow_stairs[2] - 5.4) < 0.0011, str(glow_stairs[:3]))
pin("LUNCH SUMMONS THE SWARM: launch 2 never early, no eligible tick skipped",
    len(launches) >= 2 and catch_pkt is not None
    and launches[1]["name"] == "fly-1"
    and (launches[1]["pkt"] - catch_pkt) * DT >= F_SUMMON - 1.5 * DT
    and eligible_skipped == 0,
    f"catch pkt {catch_pkt}, launch2 pkt "
    f"{launches[1]['pkt'] if len(launches) >= 2 else None}, mirrored "
    f"{F_SUMMON:.3f} s, eligible skipped {eligible_skipped}")
pin("no launch 3 before night (the next delta outlives noon)",
    night_pkt is not None and len(launches) <= 2
    and all(l["pkt"] < night_pkt for l in launches),
    f"launches {[l['pkt'] for l in launches]}, night {night_pkt}")
pin("night falls and NO fly launches at night",
    night_pkt is not None and all(l["pkt"] < night_pkt for l in launches),
    f"night pkt {night_pkt}, launches {[l['pkt'] for l in launches]}")
pin("the owl still hoots at night (the night shift intact)",
    owl_hoot_pkt is not None, f"hoot pkt {owl_hoot_pkt}")
pin("a life ended by a cactus (the injected hits are honest)",
    death_win is not None and "down at" in death_win[1], str(death_win))
pin("reseed on rebirth: run 2 repeats the summon, never early, no skips",
    len(run2["launches"]) >= 2 and run2["summon_delta"] is not None
    and run2["summon_delta"] >= F_SUMMON - 1.5 * DT
    and run2.get("skipped", 999) == 0,
    f"run2 launches {run2['launches']}, delta {run2['summon_delta']}, "
    f"mirrored {F_SUMMON:.3f} s, skipped {run2.get('skipped', 999)}")

print("PROBE " + ("GREEN" if not fails else f"RED: {fails}"))
sys.exit(1 if fails else 0)
