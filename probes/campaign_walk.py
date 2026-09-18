#!/usr/bin/env python3
"""THE GRAND TOUR — the campaign walked on the wire, hop by hop (R39).

The chain walk (gate 8) proved ONE hop: playground -> level-1, walked,
receipt spoken. The grand tour is the sequel: keep walking. Every scene
in the chain must be walked through its door — ferries ridden, lifts
boarded, fangs hopped — until the shell consumes pendingNext again and
again and the loop closes where it began.

THE WALKER'S LAWS (inherited from the chain walk):
- NEVER pause: steer on the pause-free trace telemetry (px/py/vx/vy at
  25ms), drain the pty every microsecond of its life. The freeze-frame
  is a lie the drive tells itself.
- The keys are per-tick presses (pollKeys builds a fresh Keys every
  frame): HOLDING right means bytes flowing; RELEASED means silence.
- The rendered say() is paint, not bytes: the machine truth lives on
  the event wire — EVENT goal( when a door touches, shell: welcome to
  <scene> when the shell consumes pendingNext, respawn(ouch ...) with
  the honest spawn when a fall or a fang collects a life.
- Every fall is an honest respawn: the walker retries per life. Boards
  sweep their phase across lives (a missed ferry costs ~3s, shifts the
  arrival phase; the sweep converges without any clock math).

THE WALKER'S STATES:
- run: hold right; jump bands (hazards, climbs); wedge-hop when stuck.
- board: standing at a ferry's ledge (d silent); jump when the
  scene-time phase window says the ferry is home; after two deaths the
  board goes opportunistic (a jump every sweep period — the phase
  sweep rides on honest respawns).
- listen: just jumped (d held through the flight, then silent): if the
  landing is CARRIED (position moves with no input) the ride law takes
  over; if the ground is still, run resumes.
- ride (ferry): aboard, silent, watching the exit window — walk off or
  jump off when the plan says so.
- ride (lift): aboard, silent; exit at the lift's TOP REVERSAL (py
  turns from rising to falling) — walk off or jump off per the plan.
  A lift boarded on its way down rides through the bottom reversal and
  exits at the top; that is the whole trick.
- elev: at a lift's ledge; hop-right bursts until one lands aboard.

THE PLANS: hand-read from the scenes the tour must cross (the recon
that convicted level-2's frozen ferries)."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os, pty, re, select, sys, tempfile, time, json

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")
HOPS = int(os.environ.get("DXN3_TOUR_HOPS", "3"))
CAP = float(os.environ.get("DXN3_TOUR_CAP", "300"))

tfd, TRACE = tempfile.mkstemp(prefix="dxn3_tour_", suffix=".trace")
os.close(tfd)
DIRTY0 = _os.popen(f"git -C {REPO!r} status --porcelain").read()

# ---- the chain, read honestly from the scene files (no hardcoding) ----
def scene_file(name):
    return os.path.join(REPO, "scenes", name + ".dxn1.json")

CHAIN, SCENES = [], {}
_name = "playground"
while _name not in SCENES:
    with open(scene_file(_name)) as f:
        d = json.load(f)
    SCENES[_name] = d
    CHAIN.append(_name)
    nxt = d.get("next", "")
    if not nxt:
        break
    _name = os.path.basename(nxt).replace(".dxn1.json", "")
SPAWN = {}
for _n, _d in SCENES.items():
    for _e in _d["entities"]:
        if _e.get("tag") == "player":
            SPAWN[_n] = (int(_e["x"]), int(_e["y"]))

# ---- the plans (from the recon; see the header) ----
# bands: (x_lo, x_hi[, listen]) — jump when grounded inside; listen=True
#        means the landing must be listened to (it may be a mover).
# boards: edge window + the ferry's real geometry (x0, x1, vx, width)
#         — the policy simulates the ping-pong and jumps only when the
#         predicted landing (x + range, flight seconds from now) will
#         be covered by the ferry's span. No hand-tuned phase windows:
#         the flight time was the lie that killed the first drafts.
# exits: while riding a ferry, jump/walk off inside the x window; the
#         landing (x + range) must dodge every avoid band (spikes).
# elev: at=the x-span (for mode lookup during rides), mode=how to leave
#         at the top reversal; board="burst" stops and hop-boards at
#         the ledge, board="wall" just marches into the lift's wall and
#         wedge-hops (the wall is a safe waiting room).
PLANS = {
    "playground": dict(bands=[(380, 452), (530, 690)]),
    "level-1": dict(
        bands=[(890, 1000)],
        boards=[dict(edge=(480, 548), x0=620, x1=760, vx=70, width=140,
                     flight=0.75, range=175)],
        exits=[dict(x=(600, 9999), mode="jump")],
        elev=[dict(at=(1180, 1460), mode="walk", board="wall")]),
    "level-2": dict(
        bands=[(830, 925)],
        boards=[dict(edge=(290, 352), x0=400, x1=660, vx=101, width=150,
                     flight=0.75, range=175)],
        exits=[dict(x=(590, 9999), mode="jump", avoid=[(870, 925)])]),
    "level-3": dict(
        bands=[(390, 470), (660, 745), (1245, 1335, True)],
        elev=[dict(at=(850, 935), mode="jump", board="burst"),
              dict(at=(1325, 1378), mode="jump", board="burst")]),
}

# ---- the child on the wire ----
pid, fd = pty.fork()
if pid == 0:
    os.chdir(REPO)
    os.environ["TERM"] = "xterm-256color"
    os.environ["DXN3_TRACE"] = TRACE
    os.environ["DXN3_TRACE_MS"] = "25"
    os.execv(BIN, [BIN, "--scene", "scenes/playground.dxn1.json"])
    os._exit(1)

class Tour:
    """one walk: incremental trace reading, receipts, honest deaths."""
    LINE = re.compile(rb"px=(-?[\d.]+) py=(-?[\d.]+) vx=(-?[\d.]+) vy=(-?[\d.]+)")
    EV_GOAL = re.compile(rb"EVENT goal\(")
    EV_WELCOME = re.compile(rb"EVENT shell: welcome to ([a-z0-9-]+)")
    EV_RESPAWN = re.compile(rb"EVENT respawn\(([^)]*)\) -?[\d.]+,-?[\d.]+"
                            rb" -> (-?[\d.]+),(-?[\d.]+)")

    def __init__(self):
        self.buf = b""
        self.tail = b""
        self.tr_off = 0
        self.hero = None
        self.events = []           # (kind, data) in arrival order
        self.scene = CHAIN[0]
        self.scene_t0 = time.time()
        self.deaths = {n: 0 for n in CHAIN}

    def drainf(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            r, _, _ = select.select([fd], [], [],
                                    min(0.004, max(0.001, end - time.time())))
            if r:
                try:
                    chunk = os.read(fd, 1 << 16)
                except OSError:
                    return False
                if not chunk:
                    return False
                self.buf = chunk           # the flood is skimmed, not kept
        return True

    def send(self, s):
        try:
            os.write(fd, s if isinstance(s, bytes) else s.encode())
        except OSError:
            pass

    def pump_trace(self):
        try:
            with open(TRACE, "rb") as f:
                f.seek(self.tr_off)
                data = f.read()
                self.tr_off = f.tell()
        except OSError:
            return
        if not data:
            return
        self.tail += data
        *lines, self.tail = self.tail.split(b"\n")
        for ln in lines:
            m = self.LINE.search(ln)
            if m:
                self.hero = (float(m.group(1)), float(m.group(2)),
                             float(m.group(3)), float(m.group(4)))
            if b"EVENT goal(" in ln:
                self.events.append(("goal", None))
            for w in self.EV_WELCOME.finditer(ln):
                self.events.append(("welcome", w.group(1).decode()))
            for r in self.EV_RESPAWN.finditer(ln):
                self.events.append(("respawn",
                                    (float(r.group(2)), float(r.group(3)))))

    def scene_time(self):
        return time.time() - self.scene_t0

# ---- the policy ----
DEBUG = os.environ.get("DXN3_TOUR_DEBUG", "")

def ferry_left(b, ph):
    """the ferry's left edge at phase ph (ping-pong, x only)."""
    span = b["x1"] - b["x0"]
    t1 = span / b["vx"] if b["vx"] else 1e9
    ph = ph % (2 * t1)
    if ph <= t1:
        return b["x0"] + b["vx"] * ph
    return b["x1"] - b["vx"] * (ph - t1)

def landing_on_ferry(b, x, ph_now):
    """will the ferry be under the predicted landing when the flight
    touches down? The flight time was the lie that killed the static
    windows — the ferry moves ~half its width while the arc flies.
    The margin is ASYMMETRIC on purpose: landing a pixel short of the
    ferry is a fang pit, landing deep inside is a ride. The landing
    must be well inside the span."""
    land = x + b["range"]
    left = ferry_left(b, ph_now + b["flight"])
    return left + 15 <= land <= left + b["width"] - 15

def fresh_state():
    return {"state": "run", "d_until": 0.0, "last_jump": 0.0,
            "hop_at": 0.0, "stuck": 0, "last_x": None,
            "py_hist": [], "listen0": None, "listen0y": None}

def run_policy(T, st, now):
    h = T.hero
    if not h:
        return
    x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    plan = PLANS.get(T.scene, {})
    bands = plan.get("bands", [])
    boards = plan.get("boards", [])
    exits = plan.get("exits", [])
    elevs = plan.get("elev", [])
    d_until = st["d_until"]

    # a fresh life runs free for a beat (the spawn zone is safe)
    if now - st.get("respawn_at", 0.0) < 0.7:
        T.send(b"d")
        return

    # the march is CONTINUOUS: while d_until is in the future, d flows
    # no matter the state (jumps steer by holding right through the
    # flight — one tick of d is a 5px hop, the ferry is 80px away)
    if now < d_until:
        T.send(b"d")
        if st["state"] in ("board", "elev", "ride"):
            return                     # a burst never re-triggers logic

    # ---- RIDE: aboard something; the exit law ------------------------
    if st["state"] == "ride":
        if st["kind"] == "lift":
            st["py_hist"].append(y)
            if len(st["py_hist"]) > 3:
                st["py_hist"].pop(0)
            if len(st["py_hist"]) == 3:
                a, b, c = st["py_hist"]
                if a > b and c > b + 0.5:      # rising then falling: TOP
                    if st["mode"] == "walk":
                        st["d_until"] = now + 0.7
                    else:
                        T.send(b"w")
                        st["d_until"] = now + 1.1
                    st["state"] = "listen"
                    st["listen0"] = None
                    st["last_jump"] = now
                    st["py_hist"] = []
                    return
            # the carry ended under us? TIME-BASED stillness: a lift
            # at 55px/s moves 0.18px per 3ms poll — a per-poll 1px
            # threshold reads every slow ride as "still" and bails at
            # 42ms, marching the hero off mid-height. Compare position
            # across a 0.3s window instead.
            mark = st.get("ride_mark")
            if grounded and mark and now - mark[2] >= 0.3:
                if abs(x - mark[0]) < 1.0 and abs(y - mark[1]) < 1.0:
                    st["state"] = "run"        # the carry truly ended
                    st["ride_mark"] = None
                    return
                st["ride_mark"] = (x, y, now)
            elif grounded and not mark:
                st["ride_mark"] = (x, y, now)
            return
        # ferry: watch the exit windows (the same time-based stillness)
        mark = st.get("ride_mark")
        if grounded and mark and now - mark[2] >= 0.3:
            if abs(x - mark[0]) < 1.0 and abs(y - mark[1]) < 1.0:
                st["state"] = "run"
                st["ride_mark"] = None
                return
            st["ride_mark"] = (x, y, now)
        elif grounded and not mark:
            st["ride_mark"] = (x, y, now)
        for e in exits:
            lo, hi = e["x"]
            if lo <= x <= hi:
                rng = e.get("range", 190)
                if any(a <= x + rng <= c
                       for a, c in e.get("avoid", [])):
                    continue               # the landing would be a spike
                if e["mode"] == "jump":
                    T.send(b"w")
                    st["d_until"] = now + 1.1
                else:
                    st["d_until"] = now + 0.7
                st["state"] = "listen"
                st["listen0"] = None
                st["last_jump"] = now
                return
        return                                     # aboard: silence holds

    # ---- LISTEN: just landed (or still flying); carried? -------------
    if st["state"] == "listen":
        if now > st["last_jump"] + 2.2:
            st["state"] = "run"
            return
        if not grounded or now < d_until:
            return
        if st["listen0"] is None:
            st["listen0"] = (x, y, now)
            return
        x0, y0, t0 = st["listen0"]
        if now - t0 > 0.16:
            dx, dy = x - x0, y - y0
            if abs(dx) > 2.5 or abs(dy) > 2.5:
                st["state"] = "ride"
                st["ride_still"] = 0
                st["kind"] = "lift" if abs(dy) >= abs(dx) else "ferry"
                if st["kind"] == "lift":
                    st["mode"] = "jump"
                    for e in elevs:
                        lo, hi = e["at"]
                        if lo - 40 <= x <= hi + 40:
                            st["mode"] = e["mode"]
                            break
                else:
                    st["mode"] = st.get("listen_mode", "jump")
                st["py_hist"] = [y, y, y]
                st["last_ride_x"], st["last_ride_y"] = x, y
            else:
                st["state"] = "run"
            st["listen0"] = None
        return

    # ---- ELEV: at a lift ledge; hop-right bursts until carried -------
    if st["state"] == "elev":
        e = st["elev"]
        lo, hi = e["at"]
        if not (lo - 60 <= x <= hi + 70):
            st["state"] = "run"
            return
        if grounded and now >= st["hop_at"]:
            T.send(b"d"); T.send(b"w")
            st["d_until"] = now + 0.55     # the burst steers the flight
            st["hop_at"] = now + 0.75
            return
        if grounded and now > d_until:
            if st.get("elev_y") is not None and y < st["elev_y"] - 1.5:
                st["state"] = "ride"
                st["kind"] = "lift"
                st["mode"] = e["mode"]
                st["py_hist"] = [y, y, y]
                st["ride_still"] = 0
                st["last_ride_y"] = y
            st["elev_y"] = y
        return

    # ---- BOARD: at a ferry edge; jump on the phase window ------------
    if st["state"] == "board":
        b = st["board"]
        lo, hi = b["edge"]
        if not (lo - 50 <= x <= hi + 80):
            st["state"] = "run"
            return
        if grounded and landing_on_ferry(b, x, T.scene_time()):
            T.send(b"w")
            st["d_until"] = now + 1.1       # hold through the flight
            st["state"] = "listen"
            st["listen0"] = None
            st["listen_mode"] = "jump"
            st["last_jump"] = now
            return
        return                                  # silent at the lip

    # ---- RUN: the default march ---------------------------------------
    if grounded and now > d_until:
        for b in boards:
            lo, hi = b["edge"]
            if lo <= x <= hi:
                st["state"] = "board"
                st["board"] = b
                st["board_hold"] = time.time()
                return
        for e in elevs:
            if e.get("board", "wall") != "burst":
                continue                   # wall-boarded lifts: just run
            lo, hi = e["at"]
            if lo <= x <= hi:
                st["state"] = "elev"
                st["elev"] = e
                st["elev_y"] = None
                st["hop_at"] = 0.0
                return
        if now - st["last_jump"] > 0.55:
            for bd in bands:
                lo, hi = bd[0], bd[1]
                if lo <= x <= hi:
                    T.send(b"w")
                    st["last_jump"] = now
                    if len(bd) > 2 and bd[2]:
                        st["d_until"] = now + 1.1
                        st["state"] = "listen"
                        st["listen0"] = None
                        st["listen_mode"] = "jump"
                    break
            else:
                stx = st["last_x"]
                if stx is not None and abs(x - stx) < 0.5:
                    st["stuck"] += 1
                else:
                    st["stuck"] = 0
                if st["stuck"] >= 4 and now - st["last_jump"] > 0.35:
                    T.send(b"w")
                    st["last_jump"] = now
                    st["stuck"] = 0
                    if st.get("deep_stuck", 0) >= 8:
                        # long-wedged (a sign wall, a lip): the big
                        # drift — hold right through the whole flight
                        # so the landing clears whatever wedged us
                        st["d_until"] = now + 0.85
                    else:
                        st["deep_stuck"] = st.get("deep_stuck", 0) + 1
                elif st["stuck"] == 0:
                    st["deep_stuck"] = 0
        st["last_x"] = x
    T.send(b"d")                                # the march is CONTINUOUS

# ---- the walk ----
T = Tour()
st = fresh_state()
t0 = time.time()
drained = T.drainf(3.0)
target = CHAIN[1:] + [CHAIN[0]] if HOPS >= len(CHAIN) else CHAIN[1:1 + HOPS]
need = [n.encode() for n in target]
need_ix = 0
hop_log = []

while time.time() - t0 < CAP and need_ix < len(need):
    T.pump_trace()
    T.drainf(0.0022)
    while T.events:
        kind, data = T.events.pop(0)
        if kind == "welcome" and need_ix < len(need) \
           and data.encode() == need[need_ix]:
            hop_log.append((data, round(time.time() - t0, 1),
                            T.deaths.get(data, 0)))
            T.scene = data
            T.scene_t0 = time.time()
            T.deaths.setdefault(data, 0)
            st = fresh_state()
            need_ix += 1
        elif kind == "respawn":
            T.deaths[T.scene] = T.deaths.get(T.scene, 0) + 1
            st["respawn_at"] = time.time()
            st["state"] = "run"
            st["d_until"] = 0.0
    run_policy(T, st, time.time())
    if DEBUG and T.hero:
        hb = int((time.time() - t0) * 2)
        if hb != st.get("hb"):
            st["hb"] = hb
            h = T.hero
            print(f"   .. t={time.time()-t0:6.1f} scene={T.scene:11s} "
                  f"state={st['state']:7s} x={h[0]:7.1f} y={h[1]:7.1f} "
                  f"deaths={T.deaths.get(T.scene,0)}", flush=True)

tail_ok = T.drainf(1.2)
T.pump_trace()

# ---- the pins (the trace file is the law) ----
pins = []
def pin(name, cond, detail=""):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""), flush=True)

try:
    with open(TRACE, "rb") as f:
        TR = f.read()
except OSError:
    TR = b""
welcomes = [(m.start(), m.group(1).decode())
            for m in T.EV_WELCOME.finditer(TR)]
goals = len(T.EV_GOAL.findall(TR))
respawns = [(m.start(), m.group(1).decode(),
             (int(float(m.group(2))), int(float(m.group(3)))))
            for m in T.EV_RESPAWN.finditer(TR)]

pin("boot alive (the scene game steps immediately)", drained)
pin(f"every door touched on the wire: {goals} goal events >= {len(target)}",
    goals >= len(target), f"goals={goals}")
offs = [o for o, _ in welcomes]
in_order = all(offs[i] < offs[i + 1] for i in range(len(offs) - 1))
pin("hop receipts speak the chain in order: "
    + " -> ".join(d for _, d in welcomes),
    [d for _, d in welcomes] == target and in_order,
    f"got={[d for _, d in welcomes]} want={target}")
spawns_ok, det = True, []
for o, voice, (sx, sy) in respawns:
    sc = CHAIN[0]
    for wo, wd in welcomes:
        if wo < o:
            sc = wd
    exp = SPAWN.get(sc)
    if exp and (abs(sx - exp[0]) > 2 or abs(sy - exp[1]) > 2):
        spawns_ok = False
        det.append(f"@{o} {voice} -> {sx},{sy} but {sc} spawns at {exp}")
pin("every fall death named its scene's own spawn honestly",
    spawns_ok, "; ".join(det[:3]))
pin("every respawn is the honest fall voice (no ghost states)",
    all(v.startswith("ouch") for _, v, _ in respawns), str(respawns[:2]))
pin("the clock stayed honest through the whole tour (pi=0 — no pause "
    "was ever taken)", b"pi=0.00" in TR and b"pi=0.01" not in TR
    and b"pi=0.1" not in TR)
pin("the flood keeps flowing after the last hop", tail_ok)
if HOPS >= len(CHAIN):
    pin("THE GRAND LOOP CLOSED: the tour's last welcome is the boot "
        "scene come again",
        bool(welcomes) and welcomes[-1][1] == CHAIN[0])

try:
    os.kill(pid, 15)
except Exception:
    pass
T.drainf(0.4)
try:
    os.close(fd)
except Exception:
    pass
try:
    os.waitpid(pid, 0)
except Exception:
    pass
try:
    os.unlink(TRACE)
except Exception:
    pass

dirty = _os.popen(f"git -C {REPO!r} status --porcelain").read()
pin("the tour wrote nothing (tree snapshot unchanged)", dirty == DIRTY0,
    dirty[:80])

fails = [n for n, ok in pins if not ok]
print(f"\ntour log: {len(hop_log)}/{len(target)} hops")
for h in hop_log:
    print(f"   hop -> {h[0]}  at {h[1]}s  deaths={h[2]}")
print(f"campaign_walk: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
