#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R23 probe: dino.js "the owl hunts the jump" — over the real wire
# (node SDK) at the host's own geometry (120x84).
# pins: 22 entities (two owls parked off right); the owl flies its OWN
# seeded stream ("the night owl" — the cactus stream stays untouched,
# and this probe replays BOTH streams bit for bit); it launches only
# when night AND the desert is empty AND no cactus is imminent
# (spawnIn > 2) AND the runner's feet are down — so it can never steal
# a leap a cactus demanded (the fairness pin counts zero suppressions);
# its band (rows H-13/H-14) never dips into the standing runner (top
# H-9); the first owl waits >= 6 s after nightfall; every launch
# speaks "hoot hoot" and the owl wears the pale dress; mirrored
# launches land on the observed packets with ZERO drift (waiting
# consumes no randomness — the draw happens only on a real launch);
# and after death + r the owls go home and the SECOND night's owl
# flies from the RESEEDED stream (predicted again, zero drift) while
# the cactus stream continues unbroken across both runs.
# THE BUFFER LAW (v3.1.105): the read goes through the fleet's shared
# harness (probes/_harness.py) — raw os.read, own line buffer.
import json, subprocess, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Wire

REPO = _HOME
env = dict(os.environ)
env["NODE_PATH"] = os.path.join(REPO, "sdk")
fails = []
DT = 0.1
TC = {5: 0.179, 4: 0.133, 3: 0.094}      # rise time to clear each height
OWL_COLOR = "#d8b4fe"

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

def fnv1a(name):
    # JS bitwise = SIGNED int32 — the R22 law. once bit 31 sets, the
    # seed multiplies negative and ToUint32 wraps it; the unsigned
    # python FNV never matches
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

rng = Rng("the long run")                 # the desert's own stream
orngr = Rng("the night owl")              # the owl's own stream

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "dino.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

w = Wire(p)

def send(o):
    w.send(o)

def read(timeout=4.0):
    return w.read(timeout)

def frame(keys=None, chars=None, hits=None, dt=DT):
    # letters ride via CHARS — the engine's held-key whitelist only
    # forwards left/right/jump/space from keys (the R15 lesson, re-learned)
    w.send({"t": "tick", "dt": dt,
            "keys": {k: True for k in (keys or [])},
            "chars": chars or "", "hits": hits or []})
    while True:
        f = w.read()
        if f is None: raise AssertionError("no frame — child stalled")
        if f.get("t") == "frame":
            return {e["name"]: e for e in f["set"]}, f

W, H = 120, 84
GROUND = H - 9
send({"t": "hello", "w": W, "h": H})
scene = read()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
sent = {e["name"]: e for e in scene["entities"]}
pin("scene has 24 entities (two owls, two flies parked)", len(sent) == 24, str(len(sent)))
owls_born = all(sent[f"owl-{i}"]["x"] == -999 and sent[f"owl-{i}"]["y"] == H - 13
                and sent[f"owl-{i}"].get("color") == OWL_COLOR for i in range(2))
pin("the owls are born parked, pale, in their high band", owls_born)

ents, f = frame()

# ---- mirrored state (the game's own order, tick by tick) -------------
m_speed, m_dist, m_spawnIn = 55.0, 0.0, 2.2
m_night = False
m_owlIn = 0.0
m_owlFree = 0
spawn_n = 0
band_ok = True
bands_seen = set()
night_pinneds = []
launches = []                             # (pkt, owl_idx) — all phases
hoot_ok = True
owl_invariants_ok = True
freeze_broken = False                     # a spawn/ahead cactus during flight
suppressed = 0                            # leaps the owl forbade
stolen = 0                                # …while the cactus DEMANDED it
phase = 1
death_pkt = None
r_pkt = None
max_meters = 0
PREAMBLE_TICKS = 1

# the preamble: the hello handshake ran the integration once — mirror
# it, or every spawn prediction drifts one packet (the skin probe's law)
for _ in range(PREAMBLE_TICKS):
    m_speed += 2 * DT
    m_dist += m_speed * DT
    m_spawnIn -= DT

PKT_CAP = 1000
pkt = 0
phase2_left = None
awaiting_r = False

while pkt < PKT_CAP:
    pkt += 1
    if phase2_left is not None:
        phase2_left -= 1
        if phase2_left < 0:
            break
    # --- steer from the last frame: leap at the honest lead, but never
    # while an owl is in flight (the owl hunts the jump) ---------------
    keys = []
    d = ents["dino"]
    grounded = d["y"] >= GROUND
    owl_flying = any(ents[f"owl-{i}"]["x"] > -100 for i in range(2))
    lead = None
    for i in range(6):
        c = ents[f"cactus-{i}"]
        if c["x"] > -100 and c["x"] + c["w"] > d["x"] + 2:
            if lead is None or c["x"] < lead["x"]:
                lead = c
    demand_leap = False
    if lead is not None and grounded and not awaiting_r:
        tti = (lead["x"] - (d["x"] + 7)) / m_speed
        if tti <= TC[lead["h"]] + 0.25:
            demand_leap = True
            if owl_flying:
                suppressed += 1
                if tti <= TC[lead["h"]] + 0.25:
                    stolen += 1
            else:
                keys = ["space"]
    # phase 1b: after 460 clean packets, stop leaping — run into the
    # first cactus honestly (overlap injected from real geometry)
    if phase == 1 and pkt > 460 and not awaiting_r:
        keys = []
    # --- honest hits from the last frame's geometry --------------------
    hits = []
    if not awaiting_r:
        for i in range(6):
            c = ents[f"cactus-{i}"]
            if c["x"] > -100 and d["x"] < c["x"] + c["w"] and d["x"] + 7 > c["x"] \
               and d["y"] < c["y"] + c["h"] and d["y"] + 6 > c["y"]:
                hits = ["dino", f"cactus-{i}"]
                break
    ents, f = frame(keys=keys, hits=hits)
    # --- mirror the tick — SKIPPED only while dead. the engine's order
    # is physics -> tick -> keys -> hits: on the DEATH packet the game's
    # on.tick ran FULLY before on.hit fired, so the math applies there
    # too (skipping it desyncs the stream by one draw — the R23 lesson)
    if not awaiting_r:
        m_speed += 2 * DT
        m_dist += m_speed * DT
        max_meters = max(max_meters, int(m_dist / 10))
        m_spawnIn -= DT
        # the desert holds its breath while an owl flies (owl_flying is
        # the PRE-tick state — the same value the game's step 0 read)
        if m_spawnIn <= 0 and not owl_flying:
            band = rng.next()             # the desert's stream, unbroken
            interval = 1.4 + rng.next() * (90.0 / m_speed) + 0.5
            m_spawnIn = interval
            if band > 0.75: eh, ew = 5, 3
            elif band > 0.4: eh, ew = 4, 6
            else: eh, ew = 3, 3
            bands_seen.add((eh, ew))
            idx = spawn_n % 6
            spawn_n += 1
            c = ents[f"cactus-{idx}"]
            if not (c.get("x", -999) > 100 and c.get("h") == eh and c.get("w") == ew):
                band_ok = False
        # step 8: the owl's gate (night, feet down, nothing ahead)
        if m_night:
            m_owlIn -= DT
            if m_owlIn <= 0:
                dd = ents["dino"]
                feet_down = dd["y"] >= GROUND
                clear_ahead = all(ents[f"cactus-{i}"]["x"] <= -999
                                  or ents[f"cactus-{i}"]["x"] + ents[f"cactus-{i}"]["w"] <= dd["x"]
                                  for i in range(6))
                if feet_down and clear_ahead:
                    idx = m_owlFree % 2
                    m_owlFree += 1
                    m_owlIn = 6.0 + orngr.next() * 8.0   # ONE draw, its stream
                    o = ents[f"owl-{idx}"]
                    good = (0 < o["x"] <= W + 2 and o["y"] in (H - 13, H - 14)
                            and o.get("color") == OWL_COLOR)
                    if not good:
                        owl_invariants_ok = False
                    if f.get("say") != "hoot hoot":
                        hoot_ok = False
                    launches.append((pkt, idx, phase))
        # step 9: nightfall — AFTER the owl block, as the game does
        meters = int(m_dist / 10)
        if not m_night and meters >= 200:
            m_night = True
            m_owlIn = 6.0                 # the first owl no sooner than 6 s
            night_pinneds.append((pkt, f.get("say") == "night falls at 200"
                                  and ents["ground"].get("color") == "#2b2620"))
        # the owl band never dips toward the runner: owl bottom edge
        # (y+h) must stay <= H-11 (rows H-13/H-12 at rest, H-14/H-13 on
        # the lifted beat — the standing runner's top edge is H-9, two
        # full rows of clear sky between)
        for i in range(2):
            o = ents[f"owl-{i}"]
            if o["x"] > -100 and o["y"] + o["h"] > H - 11:
                owl_invariants_ok = False
        # THE FREEZE, observed: while an owl flies, nothing is ahead —
        # the gate demanded it at launch and no spawn may break it
        flying_now = any(ents[f"owl-{i}"]["x"] > -100 for i in range(2))
        if flying_now:
            dd = ents["dino"]
            if any(ents[f"cactus-{i}"]["x"] > -999
                   and ents[f"cactus-{i}"]["x"] + ents[f"cactus-{i}"]["w"] > dd["x"]
                   for i in range(6)):
                freeze_broken = True
    # --- death, then r walks again (once) ------------------------------
    if f.get("win") and death_pkt is None:
        death_pkt = pkt
        awaiting_r = True
    if awaiting_r and phase == 1:
        phase = 2
        ents, f = frame(chars="r")        # walkAgain — the runners return
        r_pkt = pkt
        awaiting_r = False
        phase2_left = 400
        # walkAgain resets the RUN but not the desert's stream: the owl
        # stream reseeds, the cactus stream continues, the owl clock
        # restarts, the owls go home
        orngr = Rng("the night owl")
        m_owlIn = 0.0
        m_owlFree = 0
        m_night = False
        m_speed, m_dist, m_spawnIn = 55.0, 0.0, 2.2
        owls_home = all(ents[f"owl-{i}"]["x"] == -999 for i in range(2))
        cacti_home = all(ents[f"cactus-{i}"]["x"] == -999 for i in range(6))

pin("run one survives 460 steered packets (owls included)",
    death_pkt is not None and death_pkt > 460, f"death_pkt={death_pkt}")
pin("the runner walked again (r)", r_pkt is not None and owls_home and cacti_home,
    f"r_pkt={r_pkt} owls_home={owls_home} cacti_home={cacti_home}")
pin("both runs reach past the night (meters >= 300)", max_meters >= 300,
    f"meters={max_meters}")
pin("the desert's stream never restarted (shapes match across BOTH runs)",
    band_ok, f"spawns={spawn_n}")
pin("THE FREEZE: while an owl flew, nothing ever stood ahead of the runner",
    not freeze_broken)
pin("all three shapes grew across the runs", len(bands_seen) == 3, str(bands_seen))
pin("the night law fired on both runs at the mirrored packet",
    len(night_pinneds) == 2 and all(ok for _, ok in night_pinneds),
    str(night_pinneds))
pin("the owl launched at least twice", len(launches) >= 2, str(launches))
firsts = {}
for p_, idx, ph in launches:
    if ph not in firsts:
        firsts[ph] = p_
nf1 = night_pinneds[0][0] if night_pinneds else -1
nf2 = night_pinneds[1][0] if len(night_pinneds) > 1 else -1
gap1 = (firsts.get(1, -1) - nf1) * DT
gap2 = (firsts.get(2, -1) - nf2) * DT
pin("the first owl of each run waited >= 6 s after nightfall",
    gap1 >= 5.9 and gap2 >= 5.9, f"gap1={gap1:.1f}s gap2={gap2:.1f}s")
pin("every launch spoke 'hoot hoot'", hoot_ok)
pin("the owl's band never dipped into the runner's rows",
    owl_invariants_ok)
pin("FAIRNESS: the owl never forbade a leap a cactus demanded",
    suppressed == 0 and stolen == 0, f"suppressed={suppressed} stolen={stolen}")

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the owl hunts the jump")
