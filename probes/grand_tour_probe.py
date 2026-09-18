#!/usr/bin/env python3
"""THE GRAND TOUR — the walk grows legs (v3.1.115).

chain_walk_probe pinned hop 1 (playground -> level-1). The tour walks
ON: level-1's pit arc, level-2's mover boarding, level-3's two lifts —
and pins a welcome receipt per hop, straight off the event wire.

HOP 3 (v3.1.117) walks level-2's INTERIOR, and its gate is not a mover
but a sentence of geometry — THE SIGN VALVE: the spawn body already
overlaps the sign's skirt (box 90..300 x 360..390 hangs 4px into the
standing hero's 386..430 band), so walking right pins the hero at its
left wall (x = 90 - 34 = 56). Three laws answer it:
  the VALVE HOP — pinned at 56, jump: the rise hugs the wall while the
  body overlaps the skirt, then drifts over the top and lands ON it;
  the CHUTE — walking off the sign's right edge (or missing its top on
  any descent), hold LEFT: the valve's horizontal resolution (vx < 0
  snaps to s.x + s.w = 300) is a chute that returns the fall to the
  boarding strip. Gated on vy > 0 so no rising arc ever fires it;
  THE GROUND-ONLY BOARD — the boarding hop demands py >= 380: the
  sign's top is py 316, and a hop from up there lands in the pit.

And level-2's boarding has its own law — THE RECEIPT LOCK (the ride
law's first amendment, earned by simulation): mover-1's diagonal deck
boards ONLY within ~17 physics steps of leaving its low corner
(400,360) — 0 successes across 1,820 simulated arcs from 7 launch
spots at every other phase: the deck approaches from up-right, and a
left-side approach either side-clips its wall (the x-first resolution
pushes the hero out and drops him past), lands the saw, or feeds the
void. The 57-death run proved the same on live iron: the walk is
deterministic, so an honest death re-walks the SAME walk and the phase
NEVER shifts on its own. But the deck's clock is deterministic from
scene load, and the load is SPOKEN: the welcome receipt's s= field is
the movers' t=0, exact to one physics step, and the hop fires when
(s - s_receipt) mod 308 <= 16. Death-proof (the mover's clock never
resets), drift-proof, and read off the same trace as every other law.
The PHASE SCAN (a fresh uniform delay per life, the hero holding the
strip under the valve's handbrake) stays as the fallback should the
receipt's step ever go unread.

And level-1 grows its own law — THE GAP-DECK DISEMBARK: a horizontal
carry never moves py, so the ride law (a vertical law) is blind to the
gap deck; the walker kept steering, and when the pit arc landed on the
deck the cooldown ate the watcher window and carried the hero off the
deck's right end into the spike's box (deaths at x 906-911). Standing
on the deck IS a py band (328 = deck top 372 - 44) and the deck's x
ends at 900: the jump from that window lands 1118+, past the spike.

THE RIDE LAW (phase-independent): the movers ping-pong from scene load
on a fixed clock, but the walker ARRIVES at whatever phase its own
walking earned — so no choreography may TIME a mover. The law instead:
board by geometry (jump windows pinned to the LEDGES, not the mover),
detect the ride from telemetry (py carried while the hands are off),
let the mover carry, disembark at honest thresholds — and a missed
attempt is an honest death: the respawn re-walks, the phase shifts,
the tour retries per life, exactly like a player. No pause is ever
taken (the R37 crawl stays dead): the walk steers on the engine's
pause-free trace telemetry and keeps the pty drained for life.

THE RECEIPT LAW: the rendered say() is paint, not bytes — the machine
truth lives on the event wire: EVENT shell: welcome to <name> when the
shell consumes pendingNext. The tour stops the moment the last hop's
receipt lands — the machine decides when it's done."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os, pty, random, re, select, sys, tempfile, time

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")

HOPS = ["level-1", "level-2", "level-3"]  # receipts to pin (hop 3 walks
                                          # level-2's interior: the sign
                                          # valve, the diagonal deck, the
                                          # walk under mover-2 to the goal)
CAP = 170.0                       # wall cap (gate 8 kills probes at 180)

tfd, TRACE = tempfile.mkstemp(prefix="dxn3_grand_tour_", suffix=".trace")
os.close(tfd)

DIRTY0 = _os.popen(f"git -C {REPO!r} status --porcelain").read()

pid, fd = pty.fork()
if pid == 0:
    os.chdir(REPO)                      # the chain's next paths are relative
    os.environ["TERM"] = "xterm-256color"
    os.environ["DXN3_TRACE"] = TRACE
    os.environ["DXN3_TRACE_MS"] = "25"  # 40Hz steering telemetry
    os.execv(BIN, [BIN, "--scene", "scenes/playground.dxn1.json"])
    os._exit(1)

buf = b""
def drainf(seconds):
    """read EVERYTHING the pty says in the window — the flood never
    backs up, the child never stalls on a full pipe"""
    global buf
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [],
                                min(0.004, max(0.001, end - time.time())))
        if r:
            try: chunk = os.read(fd, 1 << 16)
            except OSError: return False
            if not chunk: return False
            buf += chunk
    return True

def send(s): os.write(fd, s if isinstance(s, bytes) else s.encode())

LINE = re.compile(rb"w=\s*([\d.]+) f=\s*\d+ s=\s*(\d+)[^\n]*px=(-?[\d.]+) py=(-?[\d.]+) "
                  rb"vx=(-?[\d.]+) vy=(-?[\d.]+)")
WELCOME = re.compile(rb"EVENT shell: welcome to (\S+)")
EVENT = re.compile(rb"^  EVENT", re.M)

class TraceTail:
    """THE TAIL LAW: the trace grows all walk long, and a probe that
    re-reads the WHOLE file every decision tick drowns in its own
    telemetry — by s~9900 the parse cost seconds per decision and the
    steering landed on a world that had already moved on (the chute's
    'a' arriving after the hero had drifted past the strip's edge).
    The tail reads only the NEW bytes: one seek, the new complete
    lines, the newest sample kept. Decisions return to tick cadence."""
    def __init__(self, path):
        self.path = path; self.pos = 0; self.tail = b""
        self.last = None            # (w str, s int, x, y, vx, vy)
        self.prev_s = None          # the s of the newest telemetry line
        self.welcome = None         # the newest welcome receipt's name
        self.welcome_s = None       # the s spoken just before it
    def pump(self):
        try:
            with open(self.path, "rb") as f:
                f.seek(self.pos)
                chunk = f.read()
        except OSError:
            return
        if not chunk: return
        self.pos += len(chunk)
        self.tail += chunk
        lines = self.tail.split(b"\n")
        self.tail = lines.pop()               # the partial last line
        for ln in lines:
            m = LINE.search(ln)
            if m:
                self.last = (m.group(1), int(m.group(2)), float(m.group(3)),
                             float(m.group(4)), float(m.group(5)),
                             float(m.group(6)))
                self.prev_s = self.last[1]
            elif ln.startswith(b"  EVENT"):
                wm = WELCOME.search(ln)
                if wm:
                    self.welcome = wm.group(1).decode()
                    self.welcome_s = self.prev_s

def trace_text():
    try:
        with open(TRACE, "rb") as f: return f.read()
    except OSError:
        return b""

def hero():
    return tail.last

tail = TraceTail(TRACE)

# ---- the choreographies -------------------------------------------------
class St:
    __slots__ = ("last_x", "stuck", "stuck_w", "last_jump", "py_hist",
                 "last_w", "scan", "load_s", "drive_until", "drive_w",
                 "drive_s")
    def __init__(self):
        self.last_x = None; self.stuck = 0; self.stuck_w = None
        self.last_jump = 0.0
        self.py_hist = []; self.last_w = None
        self.scan = random.uniform(0.0, 5.2)   # THE PHASE SCAN: a fresh
                                               # slice of the deck's cycle
                                               # per life (the fallback)
        self.load_s = None                     # THE RECEIPT LOCK: the
                                               # scene's first physics step
                                               # (the movers' t=0), read off
                                               # the wire's s= field
        self.drive_until = 0.0                 # THE DRIVE: the boarding
                                               # hop's sustained right-drift
        self.drive_w = False                   # the one 'w' the jump edge
                                               # may eat (a second 'w' on a
                                               # deck re-arms the edge and
                                               # hops the rider off the deck)
        self.drive_s = 0                       # the fire's step — the drive
                                               # ends at the first grounded
                                               # tick past the launch

def ride_check(st, h):
    """THE RIDE LAW: grounded + py carried over ~4 telemetry samples
    (75ms — a mover's 55-110px/s carry moves py 4-8px in that window,
    while a standing hero's py never moves) = a mover has me.
    THE UPPER GUARD (earned at the strip's edge): a LANDING also moves
    py 30-40px across 4 samples — the fall's last four samples look
    exactly like a carry the instant the hero touches down, and the
    phantom ride held him hands-off at the strip's 4px margin while he
    drifted into the pit. A carry is SMALL and SUSTAINED; a fall is
    huge. The law now demands 1.5 <= delta <= 20."""
    w, s, x, y, vx, vy = h
    if w != st.last_w:                  # sample at telemetry cadence
        st.last_w = w
        st.py_hist.append(y)
        if len(st.py_hist) > 4: st.py_hist.pop(0)
    if abs(vy) >= 1.0 or len(st.py_hist) < 4:
        return False
    d = abs(st.py_hist[-1] - st.py_hist[-4])
    return 1.5 <= d <= 20.0

def common_reset(st, h):
    """teleport (respawn / scene transition) awareness — and every
    respawn is a NEW LIFE: the phase scan re-draws its slice, or the
    deterministic re-walk would land on the same deck phase forever
    (the 54-death lesson: an honest death alone shifts nothing).
    The receipt lock needs no re-draw — the mover's clock never
    resets, so the lock survives every death by construction."""
    x = h[2]
    if st.last_x is not None and abs(x - st.last_x) > 400:
        st.stuck = 0; st.last_x = None; st.py_hist = []; st.last_w = None
        st.scan = random.uniform(0.0, 5.2)
        return True
    return False

def stuck_jump(st, h, now):
    """the wedge hop (chain_walk's law), but honest about the clock:
    a stall is measured across TELEMETRY samples (w changes), never
    across decision ticks — the decisions spin ~10x faster than the
    25ms telemetry, so tick-counting saw x as frozen between samples
    and hopped the rider clean off every deck he boarded"""
    w, s, x, y, vx, vy = h
    if w != st.stuck_w:                 # a new telemetry sample
        st.stuck_w = w
        grounded = abs(vy) < 1.0
        if st.last_x is not None and abs(x - st.last_x) < 0.5 and grounded:
            st.stuck += 1
        else:
            st.stuck = 0
        st.last_x = x
    if st.stuck >= 4 and now - st.last_jump > 0.35:
        st.last_jump = now; st.stuck = 0
        return b"wd"
    return None

def dec_playground(h, st, now):
    if common_reset(st, h): st.last_x = h[2]; return b"d"
    w, s, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    j = stuck_jump(st, h, now)
    if j: st.last_x = x; return j
    for lo, hi in ((380.0, 452.0), (530.0, 690.0)):    # chain_walk's bands
        if lo <= x <= hi and grounded and now - st.last_jump > 0.55:
            st.last_jump = now; st.last_x = x; return b"wd"
    st.last_x = x
    return b"d"

def dec_level1(h, st, now):
    if common_reset(st, h): st.last_x = h[2]; return b"d"
    w, s, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    if ride_check(st, h):               # THE ELEVATOR (1330, 372 -> 250)
        if y <= 215 and x >= 1330:      # its top: walk off onto sky-ledge
            st.py_hist = []; st.last_w = None; st.last_x = x
            return b"d"
        st.last_x = x
        return b""                      # hands off, let it carry
    # THE GAP-DECK DISEMBARK: a horizontal carry never moves py, so
    # ride_check (a vertical law) is blind to the gap deck — and when
    # the pit arc landed on it, the cooldown ate the watcher window
    # and the carry walked the hero off the deck's right end into the
    # watcher spike's box (deaths at x 906-911). Standing on the deck
    # IS a py band (328 = deck top 372 - 44) and the deck's x ends at
    # 900: the jump from this window lands 1118+ on ground-b, past
    # the spike. The x band excludes the elevator (1330+), whose own
    # ride passes through this py at its bottom.
    if grounded and 320 <= y <= 336 and 830 <= x <= 910 \
            and now - st.last_jump > 0.5:
        st.last_jump = now; st.last_x = x; return b"wd"
    # the pit arc: one full jump from this window clears the 240px pit
    # (fangs included) and lands far-ledge — the-gap mover is optional
    if 505 <= x <= 545 and grounded and now - st.last_jump > 0.8:
        st.last_jump = now; st.last_x = x; return b"wd"
    # the watcher spike (940..984): jump the window, land 1143..1168
    if 870 <= x <= 895 and grounded and now - st.last_jump > 0.8:
        st.last_jump = now; st.last_x = x; return b"wd"
    # the elevator board: from this window the arc lands on the deck
    # WHATEVER its phase (the tip-2 float is cleared or missed clean)
    if 1140 <= x <= 1175 and grounded and now - st.last_jump > 0.8:
        st.last_jump = now; st.last_x = x; return b"wd"
    j = stuck_jump(st, h, now)
    if j: st.last_x = x; return j
    st.last_x = x
    return b"d"

def dec_level2(h, st, now):
    if common_reset(st, h): st.last_x = h[2]; return b"d"
    w, s, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    if ride_check(st, h):               # MOVER-1 (diagonal 400,360->660,250)
        if x >= 655 and now - st.last_jump > 0.5:
            st.py_hist = []; st.last_w = None; st.last_x = x
            return b"wd"                # the disembark arc lands 928+
        st.last_x = x
        return b""                      # hands off: a rider's feet never
                                        # exceed the deck's top (360), so
                                        # the saw (top 396) cannot clip a
                                        # true rider — but a CAMPER who
                                        # walks left off the deck's left
                                        # edge falls PAST it into the saw
                                        # and the void (the 40-death
                                        # lesson: no walking on a mover
                                        # you cannot see)
    # THE DRIVE: sustained right through the boarding flight. It starts
    # the instant the lock fires and ENDS AT THE FIRST GROUNDED TICK
    # past the launch — the boarding. Whatever he stands on then, the
    # hands come off: the ride law takes a moving deck, the stall law
    # takes a still one (its hop from the deck's home stand lands 821,
    # on ground-b, clear of the saw). The drive that kept walking past
    # the boarding strolled the rider off the deck's right end into the
    # saw below — the feet stop when the deck arrives.
    if now < st.drive_until and not (grounded and s - st.drive_s > 8):
        st.last_x = x
        if st.drive_w:
            st.drive_w = False; return b"wd"   # the ONE 'w' — the edge
                                               # must never re-arm on a
                                               # deck (the 850-saw death:
                                               # a drained queue frame
                                               # reset jumpHeld_, the
                                               # next 'w' re-jumped the
                                               # rider mid-deck and flew
                                               # him into the saw's lap)
        return b"d"
    # THE SIGN VALVE, law one — THE VALVE HOP: pinned at the sign's
    # left wall (56), jump: the rise hugs the wall while the body
    # overlaps the skirt (feet in [360,434]), then the held 'd' drifts
    # the arc over the top and it lands ON the sign (py 316).
    if grounded and y >= 380 and 50 <= x <= 60 and now - st.last_jump > 0.8:
        st.last_jump = now; st.last_x = x; return b"wd"
    # law two — THE CHUTE: falling off the sign's right edge (or any
    # descent that misses its top inside the valve's x shadow), hold
    # LEFT: the valve's horizontal resolution (vx < 0 snaps the hero
    # to s.x + s.w = 300) is a chute that returns the fall to the
    # boarding strip at ground level. Gated on vy > 0 so no rising
    # arc ever fires it — the valve hop's climb and the board hop's
    # launch are untouched. The band reaches 380: the walk-off leaves
    # the edge with +330px/s of 'd' inertia and the 'a' flip spends
    # ~25px before it bites, so the fall crosses 300-355 before the
    # chute can steer it (a hero landing at 355.8 stands 4px from
    # ground-a's edge — one breath from the pit).
    if not grounded and vy > 0 and 320 < y < 380 and 240 <= x <= 380:
        st.last_x = x; return b"a"
    # law three — THE GROUND-ONLY BOARD: the deck is under the arc or
    # it isn't — a miss is an honest death. The py >= 380 guard keeps
    # the hop off the sign's top (py 316: a hop from up there lands in
    # the pit). The 1.1s floor is the RACE the ride detection must
    # win: the boarding arc spends 0.83s airborne, so a 0.6s cooldown
    # would re-fire ON the deck and hop the rider straight back into
    # the pit (the 52-death loop the first draft died of).
    #
    # THE RECEIPT LOCK — the ride law's amendment, earned by the sim:
    # a geometry-only board is IMPOSSIBLE here (0 successes across
    # 1,820 simulated arcs from 7 launch spots — the deck approaches
    # from up-right, and every left approach either side-clips its
    # wall, lands the saw, or feeds the void). The deck boards only
    # within ~17 physics steps of leaving its low corner (400,360) —
    # and its clock is deterministic from scene load, which the wire
    # SPEAKS: the welcome receipt's s= field is the movers' t=0. So
    # the hop fires when (s - s_receipt) mod 308 sits in the low-
    # corner window: exact, death-proof (the mover's clock never
    # resets), and read from the same trace as every other law. If
    # the receipt's step was ever unreadable, the PHASE SCAN (the
    # per-life uniform delay) stays as the honest fallback.
    if x >= 280 and y >= 380 and grounded:
        fire = False
        if st.load_s is not None:
            # THE 45-STEP PIPELINE: the welcome receipt is SPOKEN ~45
            # physics steps (0.75s) before the movers' t=0 — the
            # transition's own duration, measured twice on live iron
            # (the boardings landed on the home-standing deck at ph 45
            # and 47 after fires at ph 1 and 3). The deck boards within
            # ~17 steps of leaving home, so the lock fires at the true
            # home's window — and the boarding happens mid-rise, where
            # the carry is alive (a home-standing deck's flat py blinds
            # ride_check and the drive walks the rider off the deck's
            # right end into the saw below).
            ph = (s - st.load_s) % 308
            fire = 43 <= ph <= 58
        elif now - st.last_jump > 1.1 + st.scan:
            fire = True                           # the scan fallback
        if fire and now - st.last_jump > 0.4:
            if _os.environ.get("DXN3_TOUR_DEBUG"):
                print(f"[board-fire] s={s} load_s={st.load_s} "
                      f"ph={(s - st.load_s) % 308 if st.load_s is not None else '-'} "
                      f"x={x:.0f}", file=sys.stderr, flush=True)
            st.last_jump = now
            st.drive_until = now + 0.95     # THE DRIVE: outlive the hold's
                                            # queued 'a' bytes — the engine
                                            # polls ~6 probe ticks a frame,
                                            # so a single 'wd' lands between
                                            # holds and the NEXT frames read
                                            # LEFT again (the sandwich that
                                            # neutered 60 boarding arcs: the
                                            # jump rose, then vx was fed to
                                            # the left mid-flight)
            st.drive_w = True
            st.drive_s = s
            st.last_x = x; return b"wd"
        st.last_x = x; return b"a"          # hold the strip, wait the lock
    # spike-1 hazard (880..914): safety if an arc ever lands short — the
    # window starts at ground-b's edge (760), because a walk-off from the
    # deck lands ~772 and the hero's own 330px/s momentum carries his
    # right edge into the saw's box (overlap starts at x 846) faster
    # than any decision round-trip
    if 760 <= x <= 870 and grounded and now - st.last_jump > 0.4:
        st.last_jump = now; st.last_x = x; return b"wd"
    # THE HANDS-OFF STAND: grounded somewhere that is neither the
    # ground band (py >= 380) nor the sign's top (x < 350) is a mover's
    # back. The ride law owns a moving deck; a STILL one belongs to the
    # stall law — but its hop must fit the stand: the drifted hop from
    # x <= 540 lands 760..846 (ground-b, clear of the saw whose box
    # overlap starts at 846), while from the deck's right end (547 = 3px
    # from the edge, where the boarding's residual drift settles) the
    # drifted hop lands 853 — inside the saw. There the hop goes
    # STRAIGHT up: the outward deck slides ~40px under the rise and the
    # hero falls back onto its top, the carry catches, the ride resumes.
    if grounded and y < 380 and 350 <= x <= 660:
        j = stuck_jump(st, h, now)
        if j:
            st.last_x = x
            return b"w" if x > 540 else j
        st.last_x = x; return b""
    j = stuck_jump(st, h, now)
    if j: st.last_x = x; return j
    st.last_x = x
    return b"d"

def dec_level3(h, st, now):
    if common_reset(st, h): st.last_x = h[2]; return b"d"
    w, s, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    if ride_check(st, h):
        # LIFT-1 (990..1120, 330 -> 190): jump off MID-RIDE at py 200 —
        # the arc lands ledge-b's safe left, clear of the watcher spike
        if y <= 200 and x <= 1125 and now - st.last_jump > 0.5:
            st.py_hist = []; st.last_w = None; st.last_x = x
            return b"wd"
        # LIFT-2 (1430..1550, 190 -> 60): at its top the jump arc flies
        # THROUGH the goal box (1750..1790) — the door IS the disembark
        if y <= 24 and x >= 1425 and now - st.last_jump > 0.5:
            st.py_hist = []; st.last_w = None; st.last_x = x
            return b"wd"
        st.last_x = x
        return b""
    # the fang (430..464): jump the window — the arc lands ON the
    # springboard top, the wedge at ledge-a's wall does the climbing
    if 395 <= x <= 425 and grounded and now - st.last_jump > 0.8:
        st.last_jump = now; st.last_x = x; return b"wd"
    # ledge-b: this jump clears the watcher spike AND boards lift-2
    # whatever its phase (the arcs land 1430..1550 from this window)
    if 1180 <= x <= 1262 and grounded and now - st.last_jump > 0.5:
        st.last_jump = now; st.last_x = x; return b"wd"
    j = stuck_jump(st, h, now)
    if j: st.last_x = x; return j
    st.last_x = x
    return b"d"

DECIDE = {"playground": dec_playground, "level-1": dec_level1,
          "level-2": dec_level2, "level-3": dec_level3}

# ---- the tour itself ----------------------------------------------------
t0 = time.time()
alive = drainf(3.0)
scene = "playground"
st = St()
while time.time() - t0 < CAP:
    tail.pump()                         # THE TAIL: new bytes only — the
                                        # decisions keep tick cadence
    if tail.welcome and tail.welcome != scene:
        scene = tail.welcome
        st = St()
        # THE RECEIPT'S STEP: the s= of the telemetry line spoken just
        # before the welcome receipt — the exact physics step the new
        # scene's movers call t=0 (their clock never resets after)
        st.load_s = tail.welcome_s
        if scene == HOPS[-1]:
            break
    h = hero()
    if h:
        key = DECIDE.get(scene, lambda h, st, now: b"d")(h, st, time.time())
        if key: send(key)
    if not drainf(0.0025):
        break
drainf(1.2)                             # the last load + its first frames
tr = trace_text()

pins = []
def pin(name, cond, detail=""):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""))

pin("boot alive (the scene game steps immediately — no esc, esc quits)",
    alive)
for i, hop in enumerate(HOPS, 1):
    pin(f"hop {i}: the wire receipt 'welcome to {hop}' (the door touched, "
        "pendingNext consumed, the load spoken on the event wire)",
        f"EVENT shell: welcome to {hop}".encode() in tr)
events = re.findall(rb"EVENT respawn\([^)]*\) ([^\n]*)", tr)
pin("every fall death named its scene's own spawn honestly",
    all(re.search(rb"-> -?\d+,-?\d+\s*$", e) for e in events))
pin("every respawn is the honest fall voice (no ghost states)",
    all(b"respawn(ouch" in m.group(0)
        for m in re.finditer(rb"EVENT respawn[^\n]*", tr)))
pin("the clock stayed honest through the whole tour (pi=0 — no pause "
    "was ever taken; the R37 crawl is dead)",
    b"pi=0.00" in tr and b"pi=0.01" not in tr and b"pi=0.1" not in tr)
pin("the flood keeps flowing after the last hop", drainf(0.6))

try: os.kill(pid, 15)
except Exception: pass
drainf(0.4)
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
if _os.environ.get("DXN3_TOUR_DEBUG"):
    _os.system(f"cp {TRACE} /tmp/tour_trace.txt")
try: os.unlink(TRACE)
except Exception: pass

dirty = _os.popen(f"git -C {REPO!r} status --porcelain").read()
pin("the tour wrote nothing (tree snapshot unchanged across the walk)",
    dirty == DIRTY0, dirty[:80])

fails = [n for n, ok in pins if not ok]
print(f"\ngrand_tour_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s ({len(events)} honest deaths)")
sys.exit(1 if fails else 0)
