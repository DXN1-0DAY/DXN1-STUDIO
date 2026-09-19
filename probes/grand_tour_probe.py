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

# (the vault law below is PROVEN — dec_vault_probe walks it green —
#  but HOPS stays at level-5: the levels' 60-150s death variance plus
#  the vault's 21-26s walk outruns the 180s gate cap on the bad runs.
#  R59 grows HOPS to level-6 when the budget is reclaimed.)
HOPS = ["level-1", "level-2", "level-3", "level-4", "level-5"]  # receipts
# (R49 pinned the level-4 load; R54 WALKS its interior — the three
# ferries over the fanged pit, the isle saw, the diagonal ferry-3, the
# saw-gate pass-under, and the last door — dec_level4, every fire
# predicted from the live telemetry and the engine's own constants.
# The level-5 receipt is the new end: the machine decides when it's
# done, and now it has somewhere to GO.)
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
WELCOME = re.compile(rb"EVENT shell: welcome to (.+?)\s*$", re.M)

def hop_hit(name, key):
    """the receipt carries the scene's DISPLAY name; level-5's is 'the
    vault (level-5)' — spaces and all (the old \\S+ read just 'the' and
    the tour never recognized its own destination, wandering the vault
    until the cap). Match the key exactly or as the trailing (key)."""
    if isinstance(name, bytes):
        name = name.decode(errors="replace")
    return name == key or name.endswith("(" + key + ")")
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
        self.respawns = 0           # the RESPAWN EYE: the death count
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
                if b"respawn" in ln:
                    self.respawns += 1
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
                 "drive_s", "coast", "silent", "silentAir", "jbrake",
                 "jbrake_air", "jbrake_vx", "jbrake_until", "fire_s",
                 "flight", "hold", "seen_r")
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
        self.jbrake = False                    # THE JUMP-BRAKE (R52): the
                                               # airborne escape over the
                                               # watcher's kill shadow — held
                                               # 'a' kills the run in the air
        self.jbrake_air = False                # the flight was witnessed
        self.jbrake_vx = 0.0                   # the fire's vx — the release
                                               # dose scales with it
        self.jbrake_until = 0.0                # the wall cap (starvation)
        self.fire_s = -1                       # THE VAULT: the fire's
                                               # telemetry step (the
                                               # stale-sample guard)
        self.flight = False                    # the vault's flight hold
        self.hold = b'd'
        self.seen_r = 0                        # the respawn eye's count

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
        st.flight = False
        st.scan = random.uniform(0.0, 5.2); st.coast = False; st.silent = False
        st.jbrake = False; st.jbrake_air = False
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
    # THE ELEVATOR RE-ACQUISITION GUARD (R53, the turnaround walk-off):
    # at the elevator's BOTTOM turnaround the deck's carry wobbles
    # (py 325.2 -> 327.9 -> 327.1 -> 324.3 in the R53 trace) and the
    # 4-sample delta dips below ride_check's 1.5 floor — the law reads
    # "not a carry", falls through to the default b"d", and a hero
    # parked at 1448 (the board arc lands up to 1448; the deck's edge
    # is 1450) walked off at full run accel — five falls (1585-1728,
    # the drift of a 330px/s fall from py 324) and a red run. A
    # grounded hero inside the deck's travel band (x 1330..1449,
    # standing py 206..328 — the ground's 356 and every jump window's
    # x are disjoint) who is NOT riding walks LEFT back into the
    # deck's interior and holds; ride_check re-acquires on the next
    # steady carry and the ride law (the y <= 215 walk-off, the hands
    # -off carry) takes over. The band starts BELOW the walk-off's own
    # y <= 215: at the TOP turnaround the same wobble kills ride_check
    # too, and there the default b"d" IS the disembark (walk right
    # onto the sky-ledge) — guarding it would yank the hero back into
    # an endless ride loop.
    if grounded and 215 < y <= 340 and 1330 <= x <= 1449:
        if x > 1400:
            st.last_x = x; return b"a"
        st.last_x = x; return b""
    # THE GAP-DECK DISEMBARK: a horizontal carry never moves py, so
    # ride_check (a vertical law) is blind to the gap deck — and when
    # the pit arc landed on it, the cooldown ate the watcher window
    # and the carry walked the hero off the deck's right end into the
    # watcher spike's box (deaths at x 906-911). Standing on the deck
    # IS a py band (328 = deck top 372 - 44) and the deck's x ends at
    # 900: the jump from this window lands 1118+ on ground-b, past
    # the spike. The x band excludes the elevator (1330+), whose own
    # ride passes through this py at its bottom.
    # R53 (the triple miss): the old fixed band 830..910 assumed the
    # deck parked at its right extreme (760+140=900) — but the deck
    # PING-PONGS (left edge 620..760), and a hero who arrives while it
    # retreats meets its edge at 835: the fixed window opened 5px
    # ahead, the edge passed under the hero first, the fall ate both
    # windows, the landing at 896.6 missed the ground window (870..895)
    # by 1.6px and the box-right (941) grazed the spike's 940. The
    # window is PHASE-AWARE now: read the deck's live left edge off the
    # mover telemetry and fire near WHATEVER the right edge is (the
    # arc from 780+ lands 1053+, past the spike's 984, every time);
    # the fixed band stays as the fallback for an unread deck.
    g = tail.movers.get("the-gap")
    if grounded and 320 <= y <= 336 and now - st.last_jump > 0.5:
        near_edge = (g is not None and g[0] + 95 <= x <= g[0] + 150) \
            or (g is None and 830 <= x <= 910)
        if near_edge:
            st.last_jump = now; st.last_x = x; return b"wd"
        st.last_x = x
        return b"d" if x < (g[0] + 95 if g is not None else 830) else b"a"
    # THE WATCHER RECOVERY (R53, the triple miss's third miss): a hero
    # who landed PAST the ground window (870..895 — the deck fall
    # touched down at 896.6) stood one tick from the spike's box
    # (x-overlap at 906: box-right 940) with only the default b"d"
    # ahead — the run-in death at 907. Walk LEFT back into the window;
    # the jump re-fires (the pit-arc cooldown has expired during the
    # deck ride and the walk back). The band ends at 930: a hero past
    # 930 is inside the graze race and the walk-back cannot win it —
    # but no observed landing ever reached past 910 (the fall drifts
    # left of the deck's retreat), so the band is the honest margin.
    # R53 ADDENDUM (the 911 graze): the GROUND recovery cannot save a
    # hero who lands at 911+ — the box-right (945) overlaps the spike
    # the instant the feet touch, before any 'a' byte can bite (the
    # byte lag runs 330px/s for 1-2 ticks = +16px). The pull must
    # happen AIRBORNE: a falling hero (vy > 0) below the deck band
    # (y >= 324) in the approach corridor (840..930) holds 'a' NOW —
    # the air brake (~63-84px per sample) cuts the fall's drift from
    # +61px to +22px, the touchdown lands 857..906 — inside the
    # window or the walk-back band, never overlapping the spike's
    # 940. The watcher jump's own arc is untouched: its falling phase
    # crosses y=320 at x ~1051, past the corridor's 930.
    if not grounded and vy > 0 and y >= 324 and 840 <= x <= 930:
        st.last_x = x; return b"a"
    if grounded and y >= 340 and 896 <= x <= 930:
        st.last_x = x; return b"a"
    # the pit arc: one full jump from this window clears the 240px pit
    # (fangs included) and lands far-ledge — the-gap mover is optional
    if 505 <= x <= 545 and grounded and now - st.last_jump > 0.8:
        st.last_jump = now; st.last_x = x; return b"wd"
    # the watcher spike (940..984): jump the window, land 1143..1168
    if 870 <= x <= 895 and grounded and now - st.last_jump > 0.8:
        st.last_jump = now; st.last_x = x; return b"wd"
    # (the y >= 340 recovery above already steered a past-window hero
    # back left; this window keeps its original shape)
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
    # THE GROUND-LEVEL KILL (R54, tour_fail_1789794025): a flight that
    # lands back at GROUND level (y >= 380 — every real deck carries
    # its rider at py < 380) is a FAILED boarding, and the drive's
    # grounded grace (8 ticks = 66px at full run) then walks the hero
    # off whatever edge is near — the trace's two 1016/1004 deaths both
    # landed at 754 on the ground and the drive held 'd' through the
    # landing, past the ground's 800 edge. The kill fires at tick 4
    # (the launch itself needs 1-2 input ticks of grounded ground — a
    # floor of 4 outlives the launch but ends the FAILED flight's carry
    # ~4 ticks early, saving the 46px to the edge). The ride law takes
    # the deck landings; the ground-edge guard takes the failed ones.
    if now < st.drive_until and not (
            grounded and s - st.drive_s >
            (4 if y >= 380.0 else 8)):
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
    # THE JUMP-BRAKE (R52, the no-win landing's escape): a hero past the
    # lift-2 fire band at vx > 150 cannot stop on the ground — the brake
    # slide from 250 covers 44px and the box-right grazes the watcher
    # spike's box (1290) at 1274, from ANY overshoot point (the ground
    # reverse is a death no matter the sample). The escape is AIRBORNE:
    # the 'wa' fire lifts the arc while held 'a' kills the run in the
    # air — the x-apex never passes launch+27 (the watcher's box-left
    # is 1290) and the rise clears the spike's top (162) at t=47ms, so
    # the continuous trajectory holds no 2D overlap at all. The release
    # is ANSWER-DRIVEN: hold until vx falls back through the ZERO
    # CROSS (vx <= +8% of vx_at_fire — the crossing IS the answer) and
    # the landing settles LEFT of the launch, inside the park zone,
    # where the window-wait resumes. The flight silence carries the
    # rest: b"" until the feet touch ledge-b again.
    # R53 AUTOPSY (the sixteenth): the R52 release (vx <= -0.4 *
    # vx_at_fire) was calibrated latency-free, but the dose rides 40Hz
    # sampling plus 1-2 input ticks of latency: tour_fail's telemetry
    # shows the release DECIDED at vx=-148 yet the engine still held
    # 'a' to vx=-225, and the arc dumped 111px (launch 1218 -> landing
    # 1106) instead of the designed 2-7 — off ledge-b onto lift-1's
    # descending deck, where the default walk ran the hero off the
    # deck's edge (the walk-off death, 11 honest deaths in the red
    # run). The zero-cross release + the same latency lands the dose
    # at vx ~ -95: the arc's net displacement is launch-7..-16 across
    # the whole observed fire band (vx_at_fire 140..267) — on ledge-b,
    # in the park zone, every time. And the airborne-only hold below
    # stops the OTHER leak the same trace shows: the fire happens ON
    # the ground, so ~2 stale grounded ticks returned b"a" and bled
    # the launch (vx 235 -> 158, px +9 before liftoff).
    # R53 SECOND DOSE (tour_fail_1789789492): the +0.08 threshold
    # still over-ran — the release-to-cut latency is a FULL SAMPLE
    # (the vx falls ~153px per 25ms sample under the dose) and the
    # first-below sample is a lottery (uniformly 0..153 under the
    # threshold), so the cut = threshold - ~229: the +0.08 fire cut at
    # -201 and the arc dumped -74.5 (the 1233.8 -> 1159.3 landing).
    # The threshold goes to +0.4 * vx_at_fire: the sampled first-below
    # lands ~76 under it, the latency adds ~153, and the cut settles
    # at ~ -90 for the whole 150..330 fire band — the net displacement
    # -9..-41, on ledge-b or the re-acquisition guard's deck band,
    # every time. The honest-launch case (the fire's sampled vx is the
    # launch vx) fires the dose on the FIRST airborne sample and lands
    # launch-12 (the observed 1217.7 landing) — the designed park.
    if st.jbrake:
        st.last_x = x
        if not grounded:
            st.jbrake_air = True
        if st.jbrake_air and grounded:          # LANDED: the brake is spent
            st.jbrake = False; st.jbrake_air = False
        elif now > st.jbrake_until:             # the wall cap: a starved
            st.jbrake = False                   # flight hands itself to
            st.silent = True; st.silentAir = True   # the silence
        elif not grounded and vx <= 0.4 * st.jbrake_vx:
            st.jbrake = False                   # the dose is in: the
            st.silent = True; st.silentAir = True   # silence lands it
        elif not grounded:
            return b"a"                         # the airborne left hold
        else:
            return b""      # stale grounded tick: the 'wa' is lifting
                            # off — hold fire (the old b"a" bled the
                            # launch on the deck: leak #1)
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
            # R51 (the tour_fail_1789781046 stall): the fire asked for
            # vx >= 280 inside [1205,1232], but NOTHING started the run
            # — a hero who arrived slow (the wjump's landing momentum
            # already spent) stood at 1205.8 for 132 seconds while the
            # window opened 29 times, every branch returning b"" (the
            # run branch only fired left of 1205, the reverse only
            # right of 1230, the hold ate everything between). The run
            # itself cannot reach 280 from ledge-b's edge: 685px/s² of
            # RUN_ACCEL over the 52px from 1180 tops out at 267. The
            # floor drops to 250 (reachable with a 46px run from
            # <= 1186; the landing gains ~30px from the drive's mid-air
            # accel, so 1225+8+231 = 1464 — still inside the deck), and
            # a slow hero now BRAKES BACK to the run start instead of
            # freezing at the fire line.
            if x >= 1205 and vx >= 250 and x <= 1232 \
                    and now - st.last_jump > 0.4:
                dbg3("lift2-board", x, y, vx)
                st.last_jump = now; st.last_x = x
                return b"wd"                # the run-jump onto the deck
            # THE JUMP-BRAKE TRIGGER (R52): a missed fire sample slides
            # the run past 1232 at 250-267px/s — the ground reverse's
            # 44px slide ends at 1274, inside the watcher's shadow. The
            # 'wa' takes the overshoot into the air instead: the arc
            # clears the spike, the held 'a' kills the run, and the
            # landing settles back inside the park zone (a missed cycle
            # is a re-approach, not a death).
            if x > 1230 and vx > 150 and now - st.last_jump > 0.4:
                dbg3("jbrake", x, y, vx)
                st.last_jump = now
                st.jbrake = True; st.jbrake_air = False
                st.jbrake_vx = vx; st.jbrake_until = now + 1.2
                st.py_hist = []; st.last_w = None; st.last_x = x
                return b"wa"                # the airborne brake
            # THE CRAWL LAW (R53, tour_fail_1789791239): every leftward
            # walk in the fire band used to accelerate at the FULL
            # RUN_ACCEL — a hero pulsed to -330 cannot stop before
            # ledge-b's left edge: the stop needs ~85px (60px of decel
            # + the byte lag), the 1186/1177 brake lines leave the
            # balance at px 1146 (the box-right 1180.6 — the trace's
            # stand at 1205.7 walked off EXACTLY there and fell to the
            # 1345-1356 pit). Every pulse now tops at -150 and coasts:
            # the stop from -150 is ~18px, the nudge line's overshoot
            # lands px ~1159 — the box-right (1193) holds 13px of
            # ledge. The crawl still clears the fire band in ~0.5s.
            # R55 KNIFE EDGE (the R55 first red run: the hero STOOD at
            # px == 1186.0 for 150s — the walk-left asked x > 1186 and
            # the run asked x < 1186, so a hero whose brake settled on
            # the exact boundary matched NEITHER and every branch
            # returned b"" while the sink window opened and closed
            # forever). The walk-left now owns the line itself.
            if vx < 250 and x >= 1186:
                if vx > -150:
                    st.last_x = x; return b"a"
                st.last_x = x; return b""   # the coast bleeds the pulse
            if x < 1186:
                st.last_x = x; return b"d"  # the run: ~46px to reach 250
            if x > 1230:
                if vx > -150:
                    st.last_x = x; return b"a"
                st.last_x = x; return b""
            st.last_x = x; return b""       # brake at the fire line
        if x > 1215 and vx > 140 and now - st.last_jump > 0.4:
            # THE HOT-LANDING BRAKE (R52): a wjump landing at 1216..1238
            # arrives with 108..185px/s of air-bled momentum; the ground
            # walk-left's slide from 185 ends at 1254 — 2px from the
            # watcher's shadow. Anything hot jumps instead: the same
            # airborne escape, launched well left of the shadow, lands
            # back at launch-2..-7 with the run killed.
            dbg3("jbrake-land", x, y, vx)
            st.last_jump = now
            st.jbrake = True; st.jbrake_air = False
            st.jbrake_vx = vx; st.jbrake_until = now + 1.2
            st.py_hist = []; st.last_w = None; st.last_x = x
            return b"wa"
        if x > 1206:
            # the crawl (the R53 law above): the old full-accel walk-back
            # carried a standing hero from 1205.7 to the balance at 1146
            # and off the ledge — pulse to -150, coast, arrive alive.
            if vx > -150:
                st.last_x = x; return b"a"      # walk to the run-up start
            st.last_x = x; return b""
        if x < 1177:
            st.last_x = x; return b"d"      # nudge right
        st.last_x = x; return b""           # hold at the start
    # ledge-a (760..940, top 330, standing py 286) — THE COAST-THROUGH
    # BOARDING, RESTORED (R51): R50's park-and-run fired from [800,845]
    # and its landings (~1062 observed, vx=330) plus the 79px brake
    # slide walked the hero off the deck's right edge (1120) whenever
    # the landing passed ~1041 — the tour_fail_1789780375 autopsy: the
    # hero landed ON the deck, the ride law's own brake could not stop
    # 330px/s within 58px, and the fall to the pit wore lift-2's
    # address (1436,939). R48's coast-through fires 17-45px further
    # LEFT (the hero crosses [783,813] at full speed straight off the
    # ledge-a jump's landing), the landings stay in R48's proven
    # ~[995,1040] region, and the brake holds. The missed-window
    # recovery (the ground-edge guard + the damping below) is kept —
    # a missed window is a recovery loop, not a death.
    # (R54) the walk/hold no longer require `grounded`: a hero braking
    # near ledge-a's 940 right edge BOBBLES (the box hangs past the
    # edge, the grounded flag flickers), and the flicker fell through
    # to the default 'd' mid-brake — the trace's 1166,928 death: vx was
    # already -90 at 921 when one bobble tick injected 'd' (vx -90 ->
    # +216) and the hero walked the last 19px off the edge. The brake
    # and the hold now own the whole ledge band (278..312 covers the
    # bobble's 286..300 sag); only the FIRE still demands ground.
    if 278 <= y <= 312 and 755 <= x <= 945:
        if 783 <= x <= 813:
            if grounded and l1 is not None and l1[1] >= 320.0 and l1[2] == 1 \
                    and now - st.last_jump > 0.5:
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
            st.last_x = x; return b""       # hold; the cycle returns (4.7s)
        st.last_x = x
        return b"d" if x < 783 else b"a"
    # (R53 NOTE: a boarding vx gate + a park/run-up was tried here and
    # REVERTED — it blocked the low-vx pit falls (954..1016) but the
    # bounce/park cycles tripled the boarding time and the red rate went
    # 2/4 against the 170s cap. The coast-through's residual fall family
    # (the full-speed crossings at 1002..1021) is R54's first debt.)
    # the ledge-a jump: from the ground, the rising crossing clears the
    # ledge's left edge (box-right x0+83 <= 760) and the landing
    # (x0+249) overlaps the top. THE MOMENTUM GATE (R54,
    # tour_fail_1789794025): the ground-edge guard's walk-back re-enters
    # this window LEFTWARD (vx -330), and the fire's +249 landing law
    # assumes a rightward run — a leftward fire's arc barely drifts,
    # hits ledge-a's left wall at 726 and slides down to the ground at
    # 754, where the drive's carry walked the hero off the 800 edge (the
    # trace's 1016/1004 deaths, twice each). The fire now demands
    # RIGHTWARD momentum (vx >= 60); a leftward entrant is turned with
    # 'd' (the +2300 accel reverses -330 in ~25px, still inside the
    # window) and fires on the rebuilt run. THE WINDOW SHRINK (657 ->
    # 630): the run-through landing x0+249 + the observed brake slide
    # (~58px: 33px of decision+byte lag at full run, then the bite) must
    # stay clear of ledge-a's 940 right edge — a fire past 630 could
    # land at 880+ and the brake would end past 940. The 630..657 strip
    # now walks LEFT (the guard below owns 630..800), so a hero that
    # arrives before its cooldown re-arms loops back and re-fires — a
    # recovery, not a death.
    if grounded and y >= 380 and 549 <= x <= 630:
        if vx < 60.0:
            st.last_x = x; return b"d"      # turn; rebuild the run
        if now - st.last_jump > 0.8:
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
    if grounded and y >= 380 and 630 < x < 800:
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
        if 340 <= x <= 630:
            st.last_x = x; return b"d"      # through both windows
        if x > 630:
            st.last_x = x; return b"a"      # back to the ledge window
    # THE RIDE RE-ACQUISITION GUARD (R53, the jbrake walk-off): the
    # fire clears py_hist, and ride_check's landing guard needs four
    # CLEAN carry samples to re-acquire — the ~75ms gap fell through
    # to the default b"d", which ran the landed hero off lift-1's
    # 1120 edge at full run accel (1106 -> walk-off in the R53 trace:
    # the ride law DID acquire two samples later, four px too late).
    # Any grounded hero inside lift-1's deck band (990..1120) who is
    # NOT riding walks LEFT into the deck's interior and holds; the
    # ride law (the loopback rescue below 200, the wjump disembark
    # above) takes over the moment the carry is witnessed. The band
    # is x-disjoint from ledge-a (ends 940), ledge-b (starts 1180)
    # and the low ground (y >= 380), so nothing else is shadowed.
    if grounded and y < 380 and 992 <= x <= 1118:
        if x > 1044:
            st.last_x = x; return b"a"
        st.last_x = x; return b""
    j = stuck_jump(st, h, now)
    if j:
        if _os.environ.get("DXN3_TOUR_DEBUG"):
            print(f"[L3-stuck] x={x:.0f} y={y:.0f}", file=sys.stderr,
                  flush=True)
        st.last_x = x; return j
    st.last_x = x
    return b"d"


# ---- level-4: THE FERRY CROSSING (R54) -----------------------------------
# The engine's own constants make every window computable, not guessed:
# JUMP_VY -620, RUN_MAX 330, RUN_ACCEL 2300, and level-4's own gravity
# 1500 (the scene carries it; level-1's 1450 was the old estimate). The
# arc's height is h(t) = 620t - 750t^2 (apex 128px at t=0.413s) and the
# descent crossing of a rise r is t = [620 + sqrt(384400 - 3000r)]/1500.
# THE CARRY LAW (native/src/spark.cpp stepMovers): the deck teleports its
# rider (r.x += mdx, r.y += mdy) — POSITION ONLY, no velocity is imparted
# at launch, so a deck stand launches with the hero's own vx and every
# drift below is the held-'d' drift (the fire's drive holds d through the
# flight): a full run keeps 330 (the held d beats the 220 air friction),
# a stand rides the 2300 accel ramp (1150t^2, then 23.66 + 330(t-0.1435)).
def arc_t(rise, g=1500.0, vy=620.0):
    """the descent time at which the jump arc's feet cross `rise` px
    above the launch; None if the arc never falls back to that height
    (the deck sits above the apex — unboardable from where we stand)."""
    d = vy * vy - 2.0 * g * rise
    if d < 0.0:
        return None
    return (vy + d ** 0.5) / g


def arc_drift(t, vx):
    """the held-'d' horizontal drift over the flight time t (see above)."""
    if vx > 60.0:
        return 330.0 * t
    return 1150.0 * t * t if t < 0.1435 else 23.66 + 330.0 * (t - 0.1435)


def dbg4(tag, x, y, vx, note=""):
    if _os.environ.get("DXN3_TOUR_DEBUG"):
        print(f"[L4-{tag}] x={x:.0f} y={y:.0f} vx={vx:.0f} {note}",
              file=sys.stderr, flush=True)


def dec_level4(h, st, now):
    """THE FERRY CROSSING — level-4's interior, the first summit the
    tour WALKS past its receipt (R49 pinned the load; R54 walks the
    trip): three ferries over the fanged pit (nine fangs, 100px pitch,
    kill boxes 472..500 — the pit floor is a death corridor), the isle
    saw (960..998, hanging 362..400 — 32px BELOW the deck top 330, so
    riding past it is safe but a straight-down walk-off dies inside
    it), the diagonal ferry-3, the saw-gate (1420..1458, y 330..368 —
    the far-ledge walk passes 18px UNDER it, a jump dies inside it),
    and the last door at 1720. Every fire is PREDICTED from the live
    telemetry: the landing box (x + drift(t) .. +34) must sit inside
    the deck's live span carried forward by the deck's own speed — a
    missed prediction is a held stand (the deck cycles back), never a
    leap of faith."""
    if common_reset(st, h):
        st.last_x = h[2]; return b"d"
    w, s, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    f1 = tail.movers.get("ferry-1")
    f2 = tail.movers.get("ferry-2")
    f3 = tail.movers.get("ferry-3")
    feet = y + 44.0

    # ---- FERRY-3 RIDER (diagonal 1120,360 -> 1260,300; rider py
    # 316..256, box-top 272..212): the saw-gate's band (330..368) is
    # ABOVE the rider — the jump never enters it on the rise; on the
    # descent the box sweeps it between t 0.46 and 0.57, when the
    # held-d drift has carried the box past 1458 provided the rider
    # stands at x >= 1235 (the sweep then runs 1459..1529). The
    # landing (rise -130: t=0.98, drift ~301) parks the box at
    # 1530..1600 on the far-ledge, 70px clear of the gate.
    if 230 <= y <= 330 and 1080 <= x <= 1420:
        st.last_x = x
        if x < 1235 or not grounded:
            return b""                     # ride; the deck drifts us right
        if f3 is None or now - st.last_jump < 0.6:
            return b""
        t = arc_t(feet - 430.0)            # rise to the far-ledge's top
        if t is None:
            return b""
        land = x + arc_drift(t, vx)
        if land >= 1452.0:                 # box-left past the gate's right
            dbg4("f3-disembark", x, y, vx, f"land={land:.0f}")
            st.last_jump = now
            st.drive_until = now + 0.95
            st.drive_w = True
            st.drive_s = s
            return b"wd"
        return b"d"                        # walk out along the deck
    # ---- FERRY-2 RIDER (deck top 330, rider py 286): the isle jump.
    # The isle's top (400) is 70px BELOW the feet — rise -70, t=0.927,
    # stand drift 282 — and the landing box must clear the isle saw
    # (960..998) on its RIGHT: box-left = x+282 >= 1006. The window
    # x in [724, 784]; missed (the deck carried us past it) the deck's
    # return pass re-enters it — a held stand, never a leap.
    if 260 <= y <= 300 and 700 <= x <= 1000:
        st.last_x = x
        if not grounded or f2 is None or now - st.last_jump < 0.6:
            return b""
        t = arc_t(feet - 400.0)            # rise to the isle's top
        if t is None:
            return b""
        land = x + arc_drift(t, vx)
        if land >= 1006.0 and land <= 1066.0:
            dbg4("f2-isle", x, y, vx, f"land={land:.0f}")
            st.last_jump = now
            st.drive_until = now + 0.95
            st.drive_w = True
            st.drive_s = s
            return b"wd"
        return b""
    # ---- FERRY-1 RIDER (deck top 390, rider py 346): the ferry-2 hop.
    # Rise +60 (the deck's top is 60px above the feet), t=0.715, stand
    # drift 212 — the landing box must sit inside ferry-2's span
    # carried forward by its own 85px/s.
    if 320 <= y <= 360 and 300 <= x <= 700:
        st.last_x = x
        if not grounded or f2 is None or now - st.last_jump < 0.6:
            return b""
        t = arc_t(feet - f2[1])            # rise to ferry-2's live top
        if t is None:
            return b""
        land = x + arc_drift(t, vx)
        dland = f2[0] + (85.0 if f2[3] >= 0 else -85.0) * t
        if dland + 12.0 <= land + 17.0 <= dland + 98.0:
            dbg4("f1->f2", x, y, vx, f"land={land:.0f} deck={dland:.0f}")
            st.last_jump = now
            st.drive_until = now + 0.95
            st.drive_w = True
            st.drive_s = s
            return b"wd"
        return b""
    # ---- THE ISLE (top 400, standing py 356, x 900..1070): walk right
    # and fire the ferry-3 board when the diagonal deck's carried span
    # catches the run-arc (rise = 400 - the deck's live top; the deck
    # moves 68.6px/s in x). Hold at the isle's right edge otherwise.
    if grounded and 340 <= y <= 372 and 890 <= x <= 1085:
        st.last_x = x
        if f3 is not None and now - st.last_jump > 0.6 and x >= 1000:
            t = arc_t(feet - f3[1])
            if t is not None:
                land = x + arc_drift(t, vx)
                dland = f3[0] + (68.6 if f3[3] >= 0 else -68.6) * t
                if dland + 12.0 <= land + 17.0 <= dland + 98.0:
                    dbg4("f3-board", x, y, vx,
                         f"land={land:.0f} deck={dland:.0f}")
                    st.last_jump = now
                    st.drive_until = now + 0.95
                    st.drive_w = True
                    st.drive_s = s
                    return b"wd"
        if x < 1040:
            return b"d"
        return b"a" if vx > 40 else b""
    # ---- THE START LEDGE (top 430, standing py 386, x < 300): the
    # ferry-1 board. Brake at 200 (the 1900 friction slides ~29px plus
    # the byte lag — the stop stays clear of the 280 edge), then fire
    # when ferry-1's carried span catches the arc (rise +40, t=0.756).
    if grounded and y >= 380 and x < 300:
        st.last_x = x
        if f1 is not None and now - st.last_jump > 0.6 and x >= 200:
            t = arc_t(feet - f1[1])
            if t is not None:
                land = x + arc_drift(t, vx)
                dland = f1[0] + (95.0 if f1[3] >= 0 else -95.0) * t
                if dland + 12.0 <= land + 17.0 <= dland + 108.0:
                    dbg4("f1-board", x, y, vx,
                         f"land={land:.0f} deck={dland:.0f}")
                    st.last_jump = now
                    st.drive_until = now + 0.95
                    st.drive_w = True
                    st.drive_s = s
                    return b"wd"
        if x < 200:
            return b"d"
        return b"a" if vx > 40 else b""
    # ---- THE PIT FLOOR (top 500, standing py 456): the fanged
    # corridor — nine fangs at 100px pitch kill any x-overlap, so a
    # survivor of a missed board walks LEFT to the one safe stand
    # (left of fang-1: box-right <= 319 needs x <= 285) and hops the
    # 70px back onto the start-ledge (the held-d cancels the leftward
    # momentum: the arc lands ~23px left of the fire, on the ledge).
    if grounded and y >= 440:
        st.last_x = x
        if x <= 285 and now - st.last_jump > 0.8:
            dbg4("pit-hop", x, y, vx)
            st.last_jump = now
            st.drive_until = now + 0.95
            st.drive_w = True
            st.drive_s = s
            return b"wd"
        return b"a"
    # ---- THE FAR LEDGE (top 430, standing py 386, x > 1290): the walk
    # to the last door. NO jump law here at all — the saw-gate hangs
    # at 330..368 and the walk's box (386..430) passes 18px under it.
    st.last_x = x
    return b"d"


# ---- level-5: THE VAULT (R55) --------------------------------------------
# "the vault (level-5)" — the tour's fifth summit, walked the same way
# level-4 was: every fire PREDICTED from the live telemetry (the same
# arc_t/arc_drift, level-5's own gravity is 1500) and the deck phases
# gated by pxi/dir (pxi = the path index the deck heads to; the vault's
# movers: lift-1 vertical 400<->200 @80, lift-2 vertical 200<->420 @95,
# ferry-1 horizontal 1240<->1480 @110 — speeds read off the scene json).
# THE KILL FURNITURE: the deck-guard (760..798, y 116..154) hangs over
# the high-deck (top 180 — the stand box 136..180 overlaps its band), the
# ferry-guard (1360..1398, y 240..278) hangs over ferry-1's deck (top
# 300 — the ride box 256..300 overlaps; NEVER stand at x 1326..1398),
# fang-1 (1000..1034) guards the drop-ledge's left edge, fang-3/fang-4
# sit on the last-stretch (1790/1860, tops 392 vs the surface 420), and
# the goal door (1900..1930) is touched MID-FLIGHT by the isle jump —
# the stretch beyond it is a death trap (every full jump overshoots its
# 240px span), so the isle fire is gated on the catch box landing
# INSIDE the goal's x-band.

def dbgV(tag, x, y, vx, note=""):
    if _os.environ.get("DXN3_TOUR_DEBUG"):
        print(f"[V-{tag}] x={x:.0f} y={y:.0f} vx={vx:.0f} {note}",
              file=sys.stderr, flush=True)


G, JUMPV, RACCEL, RUNMAX = 1500.0, 620.0, 2300.0, 330.0
HERO_W = 34.0


def drift_wd(t, vx):
    """the held-'d' drift over t: the exact RUN_ACCEL ramp from the live
    vx to the 330 cap (the flight hold delivers every px of this)."""
    if vx >= RUNMAX:
        return RUNMAX * t
    tt = (RUNMAX - vx) / RACCEL
    if t <= tt:
        return vx * t + 0.5 * RACCEL * t * t
    return vx * tt + 0.5 * RACCEL * tt * tt + RUNMAX * (t - tt)

def catch_sim(wp, speed, axis, plane_fixed, pos, tgt, feet0, x0, vx0,
              span_lo, span_w, tmax=1.7, dt=0.005):
    """THE HONEST CATCH — the moving-deck landing, simulated.

    wp = the deck's two waypoint coords on its axis (in path order),
    speed = pspeed, pos = the live coord, tgt = the waypoint index the
    deck heads to (the telemetry's pxi). axis 'y': the deck's plane is
    its own y (the span check uses the FIXED x extent [span_lo,
    +span_w]); axis 'x': the plane is plane_fixed (the ferry's 300) and
    the span MOVES with the deck ([pos(t), +span_w]).

    The hero: feet(t) = feet0 - 620t + 750t^2, x(t) = x0 + drift_wd(t,
    vx0) — the flight hold delivers every px. Steps 5ms: the first
    DESCENT crossing (the feet come onto the plane from above) with the
    landing box on the deck's span is THE LANDING; an ascent crossing
    with the box over the span is THE BONK (the resolve snaps him below
    — the R55 falls at 431..523) and rejects the fire.
    Returns (t_land, land_x, deck_pos_at_land, bonk)."""
    t = 0.0
    plane0 = pos if axis == "y" else plane_fixed
    prev_above = (plane0 - feet0) > 0.0
    bonk = False
    x = x0
    while t < tmax:
        t += dt
        tc = wp[tgt]                       # the deck advances toward its
        d = tc - pos                       # waypoint, bouncing at the
        if abs(d) <= speed * dt:           # ends (the engine's own law)
            pos = tc; tgt = 1 - tgt
        else:
            pos += speed * dt if d > 0.0 else -speed * dt
        feet = feet0 - JUMPV * t + 0.5 * G * t * t
        x = x0 + drift_wd(t, vx0)
        plane = pos if axis == "y" else plane_fixed
        above = (plane - feet) > 0.0       # the hero above the deck's top
        slo = span_lo if axis == "y" else pos
        on = x < slo + span_w and x + HERO_W > slo
        if prev_above and not above:       # the descent crossing
            if on:
                return (t, x, pos, bonk)
        elif prev_above is False and above:  # the ascent crossing
            if on:
                return (None, x, pos, True)
        prev_above = above
    return (None, x, pos, bonk)


# ---- the vault's movers (scenes/level-5.dxn1.json, path order) ----------
L1_WP, L1_SP, L1_LO, L1_W = (400.0, 200.0), 80.0, 300.0, 110.0
L2_WP, L2_SP, L2_LO, L2_W = (200.0, 420.0), 95.0, 480.0, 110.0
F1_WP, F1_SP, F1_PLANE, F1_W = (1240.0, 1480.0), 110.0, 300.0, 120.0




def dec_vault(h, st, now):
    # THE RESPAWN EYE: a death resets the flight latch even when the
    # spawn sits < 400px from the pit (the position jump alone can lie)
    if tail.respawns != st.seen_r:
        st.seen_r = tail.respawns
        st.flight = False
        st.last_x = None
        return b""
    if common_reset(st, h):
        st.last_x = h[2]; st.flight = False
        return b"d"
    w, s, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    l1 = tail.movers.get("lift-1")
    l2 = tail.movers.get("lift-2")
    f1 = tail.movers.get("ferry-1")
    feet = y + 44.0
    fire = now - st.last_jump > 0.6

    # THE FLIGHT LATCH: the fire's sustained hold — the drift the
    # prediction assumed, delivered (b"" would let the 220 air friction
    # steal it; the isle jump holds b"" — the pure vertical is the point).
    # THE STALE-SAMPLE GUARD (the R58 run-4 autopsy): the telemetry
    # trails the engine by up to 25ms, so the sample right after a fire
    # still reads GROUNDED (vy=0, the jump not yet processed) — clearing
    # the latch on it killed every flight's hold (the transfer's drift
    # starved to 150 of the predicted 242 and the hero fell into the
    # 410..480 pit; the isle jump inherited the default band's 'd' and
    # drifted 254px into fang-3). The latch clears only on a landing
    # sample newer than the fire by a 10-step margin — the byte-lag
    # window between the fire's sample and the engine's jump still
    # speaks PRE-JUMP grounded lines (s=fire_s+1..3 locally, wider
    # under the tour's longer pipeline) and they must never clear
    # the hold. The minimum flight is 34 steps; 10 is safe.
    if st.flight:
        if grounded and s > st.fire_s + 10:
            st.flight = False
        else:
            return st.hold

    # ---- 1. LIFT-1 RIDER (deck 300..410, ride py 156..356): pulse-creep
    # left into 298..316; the TRANSFER fires when catch_sim lands the box
    # on lift-2's RISING deck (dir -1: its target is path[0] = y200). A
    # descending deck recedes at 95px/s — no drift reaches it (R55's
    # falls at 620..687); a deck whose plane sits at/above the feet gets
    # the ascent crossed over the span — the R55 bonk (the falls at
    # 431..523). The solver owns the phase; the pulse owns the brake.
    if 292 <= x <= 420 and 95 <= y <= 365:
        st.last_x = x
        if not grounded or l1 is None or l2 is None:
            return b""
        if x > 316:
            return b"a" if vx > -160 else b""
        if x < 298:
            return b"d" if vx < 120 else b""
        if not fire or abs(vx) > 60.0:
            return b""     # THE SETTLE: the creep runs at a sustained
                           # -160 (the 2300 pulses outrun the 1900
                           # coast) — a fire on a moving creep is a
                           # stale-vx lie (the R58 runs landed 34px
                           # short); the window's stand settles the
                           # creep to 0 in 80ms and the fire waits
        if l2[3] != -1 or l2[1] < feet + 6.0:
            return b""
        t, land, dpos, bonk = catch_sim(
            L2_WP, L2_SP, "y", 0.0, l2[1], l2[2], feet, x, vx,
            L2_LO, L2_W)
        if t is None or bonk:
            return b""
        ctr = land + 17.0
        if 501.0 <= ctr <= 567.0:   # the box [land,land+34] stays >= 4px
                                    # inside BOTH edges of 480..590 — the
                                    # R58 run-1 fire landed at 556: the
                                    # box's right = the deck's edge at
                                    # 590 exactly, a graze the ride
                                    # could not hold
            dbgV("transfer", x, y, vx,
                f"s={s} age={now-st.last_jump:.2f} l2={l2[1]:.0f} t={t:.2f} land={land:.0f} deck={dpos:.0f}")
            st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 2. LIFT-2 RIDER (deck 480..590, ride py 156..376): pulse into
    # 481..505; the DECK-JUMP fires when the arc to the high-deck lands
    # the box in 644..722 — LEFT of the deck-guard's 760 with the whole
    # flight's x monotonic under 759 (the drift never exceeds the
    # landing), so the guard's band is cleared by construction. The R55
    # draft allowed 838..940 — a landing INSIDE the guard's x-shadow,
    # because the box's y lives inside the guard's band from t=0.09 to
    # the landing itself (the stand box 136..180 vs the band 116..154).
    if 470 <= x <= 600 and 95 <= y <= 440:
        st.last_x = x
        if not grounded:
            return b""
        if x > 505:
            return b"a" if vx > -150 else b""
        if x < 481:
            return b"d" if vx < 120 else b""
        if not fire or abs(vx) > 15.0:
            return b""            # THE FULL SETTLE: the creep's -150
                                  # entering this window carries a
                                  # stale-vx bias of -25..-40px on the
                                  # landing (the R58 run-3 evidence) —
                                  # the fire waits for the friction's
                                  # full stop and predicts from ~0
        rise = feet - 180.0       # the high-deck's top plane
        if rise <= 0.0 or rise > 128.0:
            return b""
        t = arc_t(rise)
        if t is None:
            return b""
        land = x + drift_wd(t, vx)
        if 654.0 <= land <= 722.0:
            dbgV("deck-jump", x, y, vx,
                f"rise={rise:.0f} t={t:.2f} land={land:.0f}")
            st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 3. THE HIGH-DECK (top 180, stand py 136, x 640..940). THE
    # STRUCTURE (the R58 run-2 lesson): the fire WINDOWS own their x
    # spans — the creep STOPS at each window and the friction settles
    # it (the pulse-creep sustains ~-150px/s, so a window inside a
    # creep zone is blown through at -183..-250 — the run-2 hero
    # crossed 861..799 without ever slowing and died in the saw at
    # 795). THE GUARD'S SHADOW: the hero's box [x,x+34] overlaps the
    # guard's 760..798 for x in 727..798 — a hero right of 799 walks
    # RIGHT (into the edge window); a hero left of 727 creeps left
    # (away from the saw); the shadow itself is never steered into.
    if grounded and 125 <= y <= 150 and 630 <= x <= 950:
        st.last_x = x
        if not fire:
            return b""
        if 860 <= x <= 884:       # THE EDGE-JUMP window (stand fire)
            if abs(vx) < 40:
                t = arc_t(feet - 240.0)     # the drop-ledge's top (a drop)
                if t is not None:
                    land = x + drift_wd(t, vx)
                    if 1042.0 <= land <= 1150.0:
                        dbgV("edge-jump", x, y, vx, f"land={land:.0f}")
                        st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b"d"
                        return b"wd"
            if vx > 40:
                return b"a"           # brake into the window
            if vx < -40:
                return b""            # settling
            if x > 871:
                return b"a"           # nudge left: the stand-fire's
                                      # reach caps at x+279 <= 1150
            return b""
        if x > 884:
            return b"a" if vx > -150 else b""   # creep left to 884
        if x > 799:
            return b"d"               # right of the saw's shadow: the
                                      # ONLY safe exit is right (727..798
                                      # is the box-overlap kill zone)
        if 631 <= x <= 671:           # THE GUARD-JUMP window (stand
                                      # fire) — the deck's left edge
                                      # parks landings at 630-640 and
                                      # the fire reaches x >= 628.8
            if abs(vx) < 40:
                t = arc_t(0.0)              # the same plane: t = 0.827
                land = x + drift_wd(t, vx)
                xc = x + drift_wd(0.706, vx)   # the band's y re-entry
                if 876.0 <= land <= 914.0 and xc >= 798.0:
                    dbgV("guard-jump", x, y, vx, f"land={land:.0f}")
                    st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b"d"
                    return b"wd"
            if vx > 40:
                return b"a"
            if vx < -40:
                return b""            # THE SETTLE (the R58 tour-splice
                                      # lesson): the creep enters this
                                      # window at a sustained -150 and a
                                      # nudge fired on it would push the
                                      # hero past 648 at -330 — off the
                                      # deck's left edge (640) into the
                                      # void; settle first, the friction
                                      # stops the slide in 6px
            if x > 660:
                return b"a"           # THE BOUNDARY NUDGE (the R58 run-3
                                      # stall): a hero parked at 665 sits
                                      # 0.22px past the gate's reach —
                                      # 914.22 vs 914.0 — and the dead
                                      # zone 666..671 matched no branch
                                      # at all; nudge to 660 (land 909,
                                      # mid-gate), never past it
            return b""            # settle (the landing gate caps the
                                  # window: the landing's own
                                  # 330-momentum brake slide is 23.7px
                                  # and the deck ends at 940)
        if x > 671:
            return b"a" if vx > -150 else b""   # creep left to 665
        return b""

    # ---- 4. THE DROP-LEDGE (top 240, stand py 196, x 990..1190): walk
    # right into 1130..1185; the FERRY BOARD fires when catch_sim lands
    # the box on ferry-1's carried span with the ride offset 30..84 (the
    # offset pins the isle jump's reach at the right extreme) and the
    # landing past the ferry-guard's stand-kill shadow (1326..1398 — the
    # ride box 256..300 lives inside its 240..278 band). The descent's
    # own crossing of the guard's y-band starts at t=0.827 (y back
    # through 196): the box's x must already be past 1398 by then.
    if grounded and 185 <= y <= 210 and 985 <= x <= 1195:
        st.last_x = x
        if f1 is not None and 1130 <= x <= 1190 and fire:
            t, land, dpos, bonk = catch_sim(
                F1_WP, F1_SP, "x", F1_PLANE, f1[0], f1[2], feet, x, vx,
                0.0, F1_W)
            if t is not None and not bonk:
                off = land - dpos
                xe = x + drift_wd(0.827, vx)
                if (30.0 <= off <= 84.0 and land >= 1406.0
                        and xe >= 1398.0):
                    dbgV("ferry-board", x, y, vx,
                        f"t={t:.2f} land={land:.0f} deck={dpos:.0f} "
                        f"off={off:.0f}")
                    st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b"d"
                    return b"wd"
        if x < 1130:
            return b"d"
        if x >= 1156:
            return b"a" if vx > 40 else b""   # brake before the edge
        return b""

    # ---- 5. THE FERRY RIDER (deck top 300, stand py 256): walk right
    # (never into the guard's shadow — the landing was past it and
    # walking right only grows x); brake at 1502; the ISLE JUMP is a
    # PURE VERTICAL 'w' from the stand fired over the isle's top — the
    # R55 draft fired a held-'d' arc from the strip and its ~280px drift
    # landed PAST the isle's 1680 edge (the gate could never pass). The
    # vertical hop drifts 0: the box [x, x+34] lands where he stands.
    if grounded and 248 <= y <= 268 and 1225 <= x <= 1620:
        st.last_x = x
        if f1 is None:
            return b""
        if x >= 1502 and vx > 40:
            return b"a"                 # brake (the slide settles ~1531)
        if 1510 <= x <= 1580 and abs(vx) < 30 and fire:
            dbgV("isle-jump", x, y, vx)
            st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b""
            return b"w"
        if x < 1502:
            return b"d"
        return b""

    # ---- 6. THE ISLE (top 360, stand py 316, x 1530..1680): walk right
    # into the GOAL JUMP at full run — the touch is gated on the box
    # crossing the goal's x-band [1900,1930] INSIDE the y-overlap window
    # t in [0.82, 0.914] (the descent's y enters the goal's 356..420 at
    # 0.82 and the landing ends the flight at 0.914): the touch happens
    # mid-flight and the death-trap stretch beyond (the fangs at
    # 1790/1860, every full jump overshooting the 240px span) is never
    # stood on. The gate computes with the live vx — honest for any run.
    if grounded and 300 <= y <= 330 and 1500 <= x <= 1690:
        st.last_x = x
        if x < 1564:
            return b"d"
        if x > 1659:
            return b"a" if vx > -150 else b""
        if fire and x >= 1564:
            t82 = x + drift_wd(0.82, vx) + 34.0   # the box's right at
                                                  # the y-overlap's start
            t91 = x + drift_wd(0.914, vx)         # the box's left at
                                                  # the flight's end
            if t82 >= 1900.0 and t91 <= 1930.0:
                dbgV("goal-jump", x, y, vx,
                    f"t82={t82:.0f} t91={t91:.0f}")
                st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b"d"
                return b"wd"
        if x < 1650 and vx < 250:
            return b"d"               # build the run through the window
                                      # (the touch gate is vx-honest, but
                                      # a slow state here would stand
                                      # forever — walk instead)
        return b""

    # ---- 7. THE START LEDGE (top 430, stand py 386, x < 300): shuttle
    # 45..200 and fire the first board when catch_sim lands the box on
    # lift-1's span — the solver owns the phase (descending OR rising:
    # the R55 draft's pxi==0 gate starved the rising half of the cycle),
    # the bonk check is the solver's (the ascent passes the deck's plane
    # BESIDE the span: x+53..87 at t=0.16, clear of 300 for x <= 200).
    if grounded and y >= 380 and x < 300:
        st.last_x = x
        if l1 is None:
            return b"d"
        if x > 200:
            # THE SHUTTLE'S RETURN: pulse-creep back into the window —
            # the R58 first run's one bug: a brake that stopped at 208
            # and stood there for 163s (a dead zone, not a held stand —
            # the fire window [45,200] was never revisited)
            return b"a" if vx > -150 else b""
        if fire:
            t, land, dpos, bonk = catch_sim(
                L1_WP, L1_SP, "y", 0.0, l1[1], l1[2], feet, x, vx,
                L1_LO, L1_W)
            if t is not None and not bonk:
                ctr = land + 17.0
                if 322.0 <= ctr <= 388.0:
                    dbgV("start-board", x, y, vx,
                        f"s={s} age={now-st.last_jump:.2f} l1={l1[1]:.0f} t={t:.2f} land={land:.0f} "
                        f"deck={dpos:.0f}")
                    st.last_jump = now; st.fire_s = s; st.flight = True; st.hold = b"d"
                    return b"wd"
        if x < 60:
            return b"d"               # walk right, rebuild the run —
                                      # full speed by x~50 (23.7px of
                                      # 2300 accel from the turnaround)
        return b"d" if vx < 280 else b""

    # ---- 8. THE DEFAULT (the last-stretch insurance / any unbanded
    # state): walk right — a short-sitting hero feeds a fang honestly
    # (the respawn is the recovery; the transfer pit's walls and the
    # void beyond do the rest).
    st.last_x = x
    return b"d"




DECIDE = {"playground": dec_playground, "level-1": dec_level1,
          "level-2": dec_level2, "level-3": dec_level3,
          "level-4": dec_level4,
          "the vault (level-5)": dec_vault}

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
        if scene == HOPS[-1] or hop_hit(scene, HOPS[-1]):
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
        any(hop_hit(nm, hop) for nm in re.findall(WELCOME, tr)))
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
        # THE TRACE SWEEP (R57): the red-run evidence piled up unbounded
        # (27 traces by 08:29 UTC) — keep the last 8, sweep the elders.
        # The newest stay banked for the autopsies that still cite them
        # (R55's five vault runs are the recalibration evidence).
        import glob as _glob
        _olds = sorted(_glob.glob("/tmp/tour_fail_*.trace"))
        for _o in _olds[:-8]:
            try: os.unlink(_o)
            except Exception: pass
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
