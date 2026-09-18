#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R22 probe: dino.js "the desert grows three shapes" — over the real
# wire (node SDK) at the host's own geometry (120x84).
# pins: 20 entities; the cacti wear THREE shapes from ONE draw of the
# seed (the fat twin is new: 6 wide, 4 tall) — the stream is untouched,
# so the probe replays FNV-1a + xorshift and predicts every spawn's
# shape and packet EXACTLY (bit for bit, worst drift 0 packets); the
# sky's clock dresses the desert — every spawn before night wears
# green with no halo, every spawn after night wears pale with glow 1,
# and the transition packet is the mirrored 200 m law ("night falls at
# 200"); and the steered host SURVIVES the whole run — honest overlap
# injection, a real leap per cactus, meters piling past the night.
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
DAY, NIGHT = "#34d399", "#a5f3fc"
TC = {5: 0.179, 4: 0.133, 3: 0.094}      # rise time to clear each height (vy 36)

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

def fnv1a(name):
    # JS bitwise ops yield SIGNED int32: once bit 31 is set, the seed
    # multiplies as a NEGATIVE double and ToUint32 wraps that — the
    # unsigned FNV everyone writes in python never matches it
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

p = subprocess.Popen(["node", os.path.join(REPO, "sdk", "examples", "dino.js")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

w = Wire(p)

def send(o):
    w.send(o)

def read(timeout=4.0):
    return w.read(timeout)

def frame(keys=None, hits=None, dt=DT):
    w.send({"t": "tick", "dt": dt,
            "keys": {k: True for k in (keys or [])},
            "chars": "", "hits": hits or []})
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
names = [e["name"] for e in scene["entities"]]
pin("scene has 24 entities", len(names) == 24, str(len(names)))

# the mirrored run — the game's own state, replayed in the same order
m_speed, m_dist, m_spawnIn = 55.0, 0.0, 2.2
m_night = False
spawn_n = 0
band_ok = dress_ok = timing_ok = True
bands_seen, night_spawns, day_spawns = set(), 0, 0
night_packet_ok = False
prev_x = {f"cactus-{i}": -999 for i in range(6)}
died = None
max_meters = 0

ents, f = frame()
# the preamble tick ran the game's integration once — mirror it, or
# every spawn prediction drifts one packet and the pin lies
m_speed += 2 * DT
m_dist += m_speed * DT
m_spawnIn -= DT
trace = []
for pkt in range(1, 461):
    # --- steer from the last frame: leap at the honest lead -----------
    keys = []
    d = ents["dino"]
    grounded = d["y"] >= GROUND
    # the R23 owl law: while an owl flies the desert holds its breath —
    # the spawn block is frozen, no draws consumed (owlFlying is the
    # PRE-tick state, exactly what the game's step 0 reads)
    owl_flying = any(ents[f"owl-{i}"]["x"] > -100 for i in range(2))
    lead = None
    for i in range(6):
        c = ents[f"cactus-{i}"]
        # still AHEAD of the runner — a passed cactus (x far left) must
        # never steer, or its negative tti pogo-sticks the dino to death
        if c["x"] > -100 and c["x"] + c["w"] > d["x"] + 2:
            if lead is None or c["x"] < lead["x"]:
                lead = c
    if lead is not None and grounded:
        tti = (lead["x"] - (d["x"] + 7)) / m_speed
        # +0.25 = the wire's own latency (one packet between measuring
        # and the leap's key phase) + a half-window of slack
        if tti <= TC[lead["h"]] + 0.25:
            keys = ["space"]
    # --- honest hits from the last frame's geometry --------------------
    hits = []
    for i in range(6):
        c = ents[f"cactus-{i}"]
        if c["x"] > -100 and d["x"] < c["x"] + c["w"] and d["x"] + 7 > c["x"] \
           and d["y"] < c["y"] + c["h"] and d["y"] + 6 > c["y"]:
            hits = ["dino", f"cactus-{i}"]
            break
    ents, f = frame(keys=keys, hits=hits)
    c0 = ents["cactus-0"]
    nd = ents["dino"]                    # the FRESH frame's dino — a stale
    trace.append((pkt, round(c0["x"], 1), c0["h"], c0["w"],   # reference lied
                  round(nd["y"], 2), f.get("say") or "", bool(hits)))
    if f.get("win"):
        died = f["win"]
        break
    # --- mirror the tick, in the game's own order ----------------------
    m_speed += 2 * DT
    m_dist += m_speed * DT
    max_meters = max(max_meters, int(m_dist / 10))
    m_spawnIn -= DT
    if m_spawnIn <= 0 and not owl_flying:
        band = rng.next()                     # one draw, as always
        interval = 1.4 + rng.next() * (90.0 / m_speed) + 0.5
        m_spawnIn = interval
        if band > 0.75: eh, ew = 5, 3          # the tall sentinel
        elif band > 0.4: eh, ew = 4, 6         # the fat twin
        else: eh, ew = 3, 3                    # the short spire
        bands_seen.add((eh, ew))
        idx = spawn_n % 6
        cname = f"cactus-{idx}"
        spawn_n += 1
        c = ents.get(cname, {})
        if not (c.get("x", -999) > 100 and c.get("h") == eh and c.get("w") == ew):
            band_ok = False
            print(f"    spawn#{spawn_n} pkt{pkt}: predict (h{eh},w{ew}) "
                  f"obs ({c.get('h')},{c.get('w')}) x={c.get('x')}")
        edress = NIGHT if m_night else DAY
        if c.get("color") == edress and c.get("glow", 0) == (1 if m_night else 0):
            if m_night: night_spawns += 1
            else: day_spawns += 1
        else:
            dress_ok = False
    meters = int(m_dist / 10)
    if not m_night and meters >= 200:
        m_night = True
        night_packet_ok = (ents["ground"].get("color") == "#2b2620"
                           and f.get("say") == "night falls at 200")
    for i in range(6):
        prev_x[f"cactus-{i}"] = ents[f"cactus-{i}"]["x"]

pin("the steered host survives to the night and past it",
    died is None and max_meters >= 230, f"meters={max_meters} win={died!r}")
if died:
    for row in trace[-22:]:
        print("   ", row)
pin("every spawn's shape matches the mirrored band (worst drift: 0 packets)",
    band_ok and timing_ok, f"spawns={spawn_n}")
pin("all three shapes grew in one run (short, the fat twin, tall)",
    (3, 3) in bands_seen and (4, 6) in bands_seen and (5, 3) in bands_seen,
    str(bands_seen))
pin("day spawns wear green with no halo",
    day_spawns >= 3 and dress_ok, f"day={day_spawns}")
pin("night spawns wear pale with their own faint ring",
    night_spawns >= 2 and dress_ok, f"night={night_spawns}")
pin("the night law fires at the mirrored 200 m packet",
    night_packet_ok and m_night)

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the desert grows three shapes")
