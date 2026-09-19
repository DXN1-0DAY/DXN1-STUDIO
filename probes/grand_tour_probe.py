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

HOPS = ["level-1", "level-2", "level-3", "level-4"]  # receipts (R49: the
                                          # level-2's interior: the sign
                                          # valve, the THAWED diagonal deck,
                                          # the walk under mover-2 to the
                                          # goal). R48 also BUILT the hop-4
                                          # summit walk (dec_level3's
                                          # interior: fang, ledge-a, two
                                          # lifts, the golden door) — the
                                          # law set is in place and the
                                          # telemetry-driven boardings fire,
                                          # but the 170s cap crossing is not
                                          # proven yet: growing HOPS to
                                          # level-4 is R49's first debt.
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
# THE MOVER LINES (R48): the engine confesses every live mover's true
# pose at the player line's cadence — the boarding windows read the
# deck's REAL position instead of inferring a phase from a constant
# that was measured against a frozen statue (the R47 lesson).
MOVERL = re.compile(rb"MOVER n=(\S+) x=(-?[\d.]+) y=(-?[\d.]+) pxi=(\d+) dir=(-?\d+)")
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
        self.movers = {}            # name -> (x, y, pxi, dir) — the decks'
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
            elif ln.startswith(b"  MOVER"):
                mm = MOVERL.search(ln)
                if mm:
                    self.movers[mm.group(1).decode()] = (
                        float(mm.group(2)), float(mm.group(3)),
                        int(mm.group(4)), int(mm.group(5)))
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
                 "drive_s", "coast", "silent", "silentAir")
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
        self.coast = False                     # THE COAST LATCH: the 'd'
                                               # release is committed until
                                               # the fire or the window closes
        self.silent = False                    # THE FLIGHT LATCH: set at the
                                               # fire, cleared at the landing
        self.silentAir = False                 # an airborne sample was seen

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
    # THE GROUND GUARD (R50, tour_fail_1789776578): a LANDING's own py
    # decay (371 -> 386 across 4 telemetry samples, d=15) fits the
    # carry band — a PHANTOM RIDE on the ground — and the ride laws
    # re-fired their disembark jumps on solid floor: level-2's fired at
    # x 1016 (benign) then again at 1225, whose arc crossed the goal's
    # x-band 100px ABOVE the goal box and dropped the hero past
    # ground-b's edge (the 1640,933 death — a race the greens kept
    # winning by timing luck); level-3's fired on ledge-b and lofted
    # the hero past lift-2 (the 1435,937 death). The ground stands at
    # py 386; every real deck in the campaign carries its rider at
    # py < 380 — so a "ride" at py >= 380 is a landing ghost, never a
    # deck. The phantom is dead at the source, in every scene at once.
    return 1.5 <= d <= 20.0 and y < 380.0

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
        st.scan = random.uniform(0.0, 5.2); st.coast = False; st.silent = False
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
        # hands off: a rider's feet never exceed the deck's top (360),
        # so the saw (top 396) cannot clip a true rider — but a CAMPER
        # who walks left off the deck's left edge falls PAST it into
        # the saw and the void (the 40-death lesson: no walking on a
        # mover you cannot see)
        if x >= 655 and now - st.last_jump > 0.5:
            st.py_hist = []; st.last_w = None; st.last_x = x
            return b"wd"                # the disembark arc lands 940..966
        st.last_x = x
        return b""
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
    # the pit). The 0.4s cooldown is the RACE the ride detection must
    # win: the boarding arc spends 0.83s airborne, so a re-fire ON the
    # deck would hop the rider straight back into the pit.
    #
    # THE THAWED BOARD (R48): the deck's true pose rides the wire as a
    # MOVER line — fire when the deck is OUTBOUND (pxi==1) within ~80px
    # of its home corner (the sim's ph 0..78 band: the arc chases the
    # leaving deck and boards mid-rise, landing 940..966 past the saw;
    # the arrival turn is caught for free — at home the deck flips to
    # pxi==1). The frozen era inferred this window from the 45-step
    # pipeline, a constant measured against the statue itself; the wire
    # now speaks the deck's real position and the inference is dead.
    # If the wire is ever unreadable, the PHASE SCAN (the per-life
    # uniform delay) stays as the honest fallback.
    # THE BOARD owns the STRIP ONLY (x <= 400: ground-a ends at 360).
    # R48's lesson: the disembark lands 940..966 on ground-b — ALSO
    # y >= 380 and grounded — and an unbounded x >= 280 gate told THAT
    # hero to hold LEFT into spike-1 (four saw deaths in one run).
    if 280 <= x <= 400 and y >= 380 and grounded:
        fire = False
        m1 = tail.movers.get("mover-1")
        if m1 is not None:
            fire = m1[2] == 1 and m1[0] <= 480.0
        elif now - st.last_jump > 1.1 + st.scan:
            fire = True                           # the scan fallback
        if fire and now - st.last_jump > 0.4:
            if _os.environ.get("DXN3_TOUR_DEBUG"):
                m1d = f"{m1[0]:.0f},{m1[1]:.0f},pxi={m1[2]}" if m1 else "-"
                print(f"[board-fire] s={s} deck(mover-1)={m1d} "
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
    # ground-b, past the saw: walk RIGHT to the goal under the thawed
    # mover-2 (its box 300..322 hangs 64px over the walking hero's
    # head — no jump, no interference; the goal is at 1330)
    if grounded and y >= 380 and 870 <= x < 1290:
        st.last_x = x; return b"d"
    # THE DOOR STAND: the goal box starts at 1330 and the touch fires
    # the transition — but the walk that keeps holding 'd' carries the
    # hero off ground-b's end (1460) DURING the 0.75s load, the fall
    # death respawns him, and the respawn CANCELS pendingNext (eleven
    # deaths in one run). Hands off at the door: the 330px/s coast
    # spends its 29px inside the goal box and stops there, mid-door,
    # while the shell speaks the welcome.
    if grounded and y >= 380 and x >= 1290:
        st.last_x = x; return b""
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

def dbg3(tag, x, y, vx=0.0):
    if _os.environ.get("DXN3_TOUR_DEBUG"):
        print(f"[L3-{tag}] x={x:.0f} y={y:.0f} vx={vx:.0f}",
              file=sys.stderr, flush=True)

def dec_level3(h, st, now):
    """THE SUMMIT WALK (R48) — the interior the frozen tour never saw.
    The spawn walk runs right through the pass-through sign-1; the
    fang (430..464, top 402) is jumped from R47's band 340 — the feet
    are 50px clear before the hero's right edge reaches the kill box —
    and the arc lands 589..629, INSIDE the ledge-a window. The ledge-a
    jump (549..657, from the ground) clears the ledge's left edge on
    the rise (box-right x0+83 <= 760) and lands 798..906 on its top.
    From the ledge's boarding band (783..813) the hero jumps when
    lift-1 is turning at its bottom (y >= 320, rising): the falling
    feet meet the rising deck at x 988..1026, the swept-band carry
    catches, and the ride law owns the deck. On the deck the hero
    walks right toward the launch band (1060), then at the TOP
    (py <= 150) jumps: the +247..249px arc lands box-left
    x0+249 >= 1324 — right of the watcher spike (1290..1324) — on
    ledge-b. A hero stranded left of the launch band rides down and
    loop-backs (wa) onto ledge-a at the deck's bottom to re-position.
    Ledge-b's own jump (1240..1262) clears the watcher AND boards
    lift-2 low; on lift-2 the hero walks right to 1460 and at the top
    (py <= 40) the arc flies THROUGH the goal box (1750..1790) — the
    door IS the disembark."""
    if common_reset(st, h): st.last_x = h[2]; return b"d"
    w, s, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    l1 = tail.movers.get("lift-1")
    l2 = tail.movers.get("lift-2")
    # THE FLIGHT SILENCE, before every other law: the coast jump's b""
    # must persist until the hero lands — the airborne hero fails
    # ride_check, so a silence living inside the ride branch never ran,
    # the default b"d" re-accelerated the arc to 330, and the hero
    # flew 120px OVER ledge-b into the void (the ninth autopsy).
    if st.silent:
        if not grounded:
            st.silentAir = True            # the flight was witnessed
            st.last_x = x; return b""
        if st.silentAir:                   # grounded after flying: landed
            st.silent = False; st.silentAir = False
        # else: the stale grounded sample right after the fire — the fire
        # happens ON the deck, so ~10 ticks still see vy=0; clearing here
        # resurrects the default b"d" and the arc flies at 330 (the tenth
        # autopsy). Stay silent until the air is witnessed.
        st.last_x = x; return b""
    if ride_check(st, h):
        if x >= 1400:                       # riding LIFT-2 (deck 1430..1550)
            if x < 1460:                    # walk to the door's launch band
                st.last_x = x; return b"d"  # (the release slide lands
                                            #  box-left ~1470-89, the
                                            #  deck's edge is 1550)
            # the fire window is the RISE through the top only: a
            # descent fire (the lift falling back 60..90) launched the
            # arc too low — its fall crossed the door's y band at x
            # 1651..1704, short of the door's 1750, and the hero fell
            # past the whole summit (the flake's second source).
            if y <= 24 and l2 is not None and l2[1] <= 70.0:
                dbg3("door", x, y, vx)
                st.py_hist = []; st.last_w = None; st.last_x = x
                return b"wd"                # the golden door: the arc
                                            # accelerates mid-air (RUN_ACCEL
                                            # applies airborne) and flies
                                            # THROUGH the goal box
            st.last_x = x; return b""
        if x >= 900:                        # riding LIFT-1 (deck 990..1120)
            # THE COAST-JUMP DISEMBARK (R48, earned across five trace
            # autopsies): the full-speed arc overshoots ledge-b — the
            # watcher spike (1290..1324) leaves no safe full-speed
            # landing — so the fire rides the vx BAND [230,290] (the
            # +111..156px arc lands 1156..1251, ledge-b's left region).
            # The band is crossed BOTH accelerating and coasting, so the
            # gate watches every tick. The latch buys the FLIGHT
            # SILENCE: after the fire, b"" until the hero lands again —
            # releasing it re-arms the default b"d" mid-air, the arc
            # stretches into the watcher, and the hero dies on the
            # landing. The rest converges to [1043,1063]: the fire then
            # happens at x 1055..1081, far from the deck's 1120 edge
            # (the walk-to-edge walk-off was the first autopsy's kill).
            if y > 200:
                if x > 1022: st.last_x = x; return b"a"
                if x < 1008: st.last_x = x; return b"d"
                if l1 is not None and l1[1] >= 320.0 and l1[2] == 0 \
                        and now - st.last_jump > 0.5:
                    dbg3("loopback", x, y, vx)
                    st.py_hist = []; st.last_w = None; st.last_x = x
                    return b"wa"            # the rescue: jump back to ledge-a
                st.last_x = x; return b""       # hold at the rest
            # THE W-JUMP DISEMBARK (R49, the eleventh autopsy): the fire
            # is 'w' ONLY — the walk's own momentum is the launch vx and
            # no 'd' byte can merge into the fire (the 'wd' fires made the
            # TRUE launch vx 330 regardless of the sampled gate: the walk's
            # queued bytes + the fire's own 'd' accelerated the first two
            # frames, the arc stretched to 190px and landed ON the
            # watcher). The +187px arc lands 1205..1235 on ledge-b's left
            # region. The flight silence (st.silent) starves the rest.
            # R50 (the twelfth autopsy, tour_fail_1789772528): the fire
            # is RISE-ONLY — the y <= 200 window catches the deck's fall
            # too, and a descent fire launched the arc from a lower,
            # falling deck: the flight shortened and the hero landed 57px
            # short (the 1148,931 death) — the same bug family as the
            # door's descent fire, which R48 already fixed; the wjump
            # gate just never got the direction check.
            if vx >= 290 and x <= 1040 and l1 is not None \
                    and l1[2] == 1 and now - st.last_jump > 0.4:
                st.silent = True                # the flight silence begins
                st.silentAir = False
                dbg3("lift1-wjump", x, y, vx)
                st.py_hist = []; st.last_w = None; st.last_x = x
                return b"w"                     # NO 'd' — the honest arc
            if vx < 330:
                st.last_x = x; return b"d"      # walk — the gate fires at speed
            st.last_x = x; return b""
        st.last_x = x; return b""
    # THE SUMMIT GUARD (R50, tour_fail_1789772528): a door arc shifted
    # right by the byte lag landed on the summit PAST the goal
    # (x > 1790) and the default walk carried the hero off the
    # summit's right edge (1840) into the void (the 1889,936 death).
    # Any grounded hero high up right of the goal walks LEFT back
    # through the goal box; the touch fires on overlap.
    if grounded and y <= 30 and x > 1795:
        st.last_x = x; return b"a"
    # ledge-b's LEFT region (1180..1256 — the watcher's kill shadow
    # starts at box-left 1257): the lift-2 boarding needs a full-speed
    # run-jump (the arc from a standing start still accelerates mid-air
    # — RUN_ACCEL applies in the air — but the run-up makes the fire
    # band deterministic). Position at the run-up start, then run
    # right and fire mid-run when lift-2 is sinking from its top.
    if grounded and 140 <= y <= 152 and 1180 <= x <= 1256:
        # R50: the sink window is <= 100 (was 130) — a fire sampled in
        # the 100..130 band lagged into a deck that reached its BOTTOM
        # (190) before the arc's 0.805s arrival: the feet crossed the
        # deck's x-band 17px BELOW its top and the hero fell past into
        # the pit (five deaths at x 1372..1434 in the red run). Fires
        # sampled at <= 100 put the deck 13px ABOVE the feet at arrival
        # for every lag up to 0.3s — a legal landing every time.
        win = l2 is not None and l2[1] <= 100.0 and l2[2] == 0
        if win:
            if x >= 1205 and vx >= 280 and x <= 1232 \
                    and now - st.last_jump > 0.4:
                dbg3("lift2-board", x, y, vx)
                st.last_jump = now; st.last_x = x
                return b"wd"                # the run-jump onto the deck
            if x < 1205:
                st.last_x = x; return b"d"  # run right through the band
            if x > 1230:
                st.last_x = x; return b"a"  # the safe reverse: a walk-past
                                            # slid into the watcher's 1px
                                            # shadow (the box-right 1291
                                            # graze) — flip before 1254
            st.last_x = x; return b""       # brake at the fire line
        if x > 1206:
            st.last_x = x; return b"a"      # walk to the run-up start
        if x < 1177:
            st.last_x = x; return b"d"      # nudge right
        st.last_x = x; return b""           # hold at the start
    # ledge-a (760..940, top 330, standing py 286) — THE PARK-AND-RUN
    # BOARDING (R50, the twelfth autopsy — tour_fail_1789772528): the
    # old coast-through band (783..813, fire at ANY vx) was a 30px
    # slice crossed at full speed between two probe samples under
    # load; the missed window slid the hero into a brake oscillation
    # whose 67px stopping distance walked it off the ledge's LEFT
    # edge, and the recovery walk fell off the ground's right edge at
    # 800 — three deaths per red run. Now: the arrival coasts right
    # and brakes only past 845 (a brake fired earlier slides 79px off
    # the left edge), the idle hero is velocity-damped into the park
    # box [772,784] (position bang-bang alone overshoots by v²/2a),
    # and the fire is a RUN: on the deck's bottom-turn (y >= 320,
    # rising) the hero accelerates and fires b"wd" at the first
    # sample with vx >= 290 inside the launch box [800,845] — the
    # landing = sampled x + lag(8..25px) + the ~205..215px arc (R48's
    # own greens) ∈ [1013,1085], inside the deck's 990..1120 for
    # every lag. A missed cycle is a safe re-park, not a death.
    if grounded and 280 <= y <= 292 and 755 <= x <= 945:
        if l1 is not None and l1[1] >= 320.0 and l1[2] == 1 \
                and now - st.last_jump > 0.5:
            if 800 <= x <= 845 and vx >= 290:
                if _os.environ.get("DXN3_TOUR_DEBUG"):
                    print(f"[L3-board] x={x:.0f} vx={vx:.0f} "
                          f"deck={l1[0]:.0f},{l1[1]:.0f}",
                          file=sys.stderr, flush=True)
                st.last_jump = now
                st.drive_until = now + 0.95    # the boarding flight's 'd'
                st.drive_w = True
                st.drive_s = s
                st.last_x = x
                return b"wd"                # board the rising lift
            if x < 845:                     # the run-up through the box
                st.last_x = x; return b"d"
            st.last_x = x; return b"a"      # overshot the box: brake back
        if vx > 60 and x > 845:             # the arrival brake: the slide
            st.last_x = x; return b"a"      # from >=845 stops on the ledge
        if vx > 60:                         # sliding right below 845:
            st.last_x = x; return b""       # coast (a brake here slides
                                            # 79px off the LEFT edge)
        if vx < -60:                        # sliding left: brake NOW
            st.last_x = x; return b"d"
        if x < 772:                         # nudge into the park box
            st.last_x = x; return b"d"
        if x > 784:
            st.last_x = x; return b"a"
        st.last_x = x; return b""           # parked; the cycle returns (4.7s)
    # the ledge-a jump: from the ground, the rising crossing clears the
    # ledge's left edge (box-right x0+83 <= 760) and the landing
    # (x0+249 = 798..906) overlaps the top
    if grounded and y >= 380 and 549 <= x <= 657 \
            and now - st.last_jump > 0.8:
        if _os.environ.get("DXN3_TOUR_DEBUG"):
            print(f"[L3-ledgeA] x={x:.0f}", file=sys.stderr, flush=True)
        st.last_jump = now; st.last_x = x; return b"wd"
    # THE GROUND-EDGE GUARD (R50, tour_fail_1789772528): a hero that
    # fell off ledge-a's left edge lands on the ground at x 700..760 —
    # right of the jump window — and the default walk then carried it
    # off the ground's right edge at 800 into the pit (three deaths
    # per red run). Walk LEFT back into the window; the ledge-a jump
    # law re-fires (its cooldown has expired during the walk back) and
    # the boarding attempt restarts. A missed window is now a
    # recovery loop, not a death spiral.
    if grounded and y >= 380 and 657 < x < 800:
        st.last_x = x; return b"a"
    # the fang (430..464, top 402): THE STANDING FIRE (R49) — the run-up
    # fires raced the byte lag (a load-stretched lag landed the jump at
    # x 395+, INSIDE the kill box). Now the hero brakes at 300 (the
    # slide settles ~329) and fires from the STAND: a stopped hero
    # cannot be dragged past the window by any lag, the mid-air accel
    # fills in the arc (+249 lands 578, inside the ledge-a window), and
    # the feet are 78px clear of the fang's top when the box-right
    # crosses 430.
    if grounded and y >= 380 and 300 <= x < 320:
        st.last_x = x; return b""          # the brake; the slide settles
    if grounded and y >= 380 and 320 <= x <= 350 \
            and now - st.last_jump > 0.8:
        if _os.environ.get("DXN3_TOUR_DEBUG"):
            print(f"[L3-fang] x={x:.0f}", file=sys.stderr, flush=True)
        st.last_jump = now; st.last_x = x; return b"wd"
    # the FANG WALL: a hero on the ground at x 381..548 who does not
    # jump is one step from the fang's kill box (x-overlap starts at
    # 397 — the box-right 431 crossing the fang's left edge 430). The
    # walk right may NEVER pass 396 without the arc: walk LEFT back
    # into the fire window (the cooldown has expired by the walk back).
    if grounded and y >= 380 and 351 <= x <= 548:
        st.last_x = x
        return b"a"
    # the ground walks: through both windows run right; past the ledge
    # window (658..800) walk LEFT back into it (the ground ends at 800
    # — beyond is the honest fall). The x < 340 region falls THROUGH to
    # the stuck check — and the stuck check MUST compare against the
    # PREVIOUS sample's x, so the fall-through leaves st.last_x alone
    # (setting it here made every new sample read dx=0 and the stuck
    # law fired 'wd' every 100ms of honest walking — the arcs landed
    # in the fang and the tour bled 40 lives in its first run).
    if grounded and y >= 380:
        if 340 <= x <= 657:
            st.last_x = x; return b"d"      # through both windows
        if x > 657:
            st.last_x = x; return b"a"      # back to the ledge window
    j = stuck_jump(st, h, now)
    if j:
        if _os.environ.get("DXN3_TOUR_DEBUG"):
            print(f"[L3-stuck] x={x:.0f} y={y:.0f}", file=sys.stderr,
                  flush=True)
        st.last_x = x; return j
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
        tail.movers.clear()          # the new scene's decks speak for it
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
if any(not ok for _, ok in pins):
    _fail_trace = f"/tmp/tour_fail_{int(time.time())}.trace"
    try:
        _os.system(f"cp {TRACE} {_fail_trace}")
        print(f"(the failed walk's trace kept at {_fail_trace})")
    except Exception:
        pass
try: os.unlink(TRACE)
except Exception: pass

dirty = _os.popen(f"git -C {REPO!r} status --porcelain").read()
pin("the tour wrote nothing (tree snapshot unchanged across the walk)",
    dirty == DIRTY0, dirty[:80])

fails = [n for n, ok in pins if not ok]
print(f"\ngrand_tour_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s ({len(events)} honest deaths)")
sys.exit(1 if fails else 0)
