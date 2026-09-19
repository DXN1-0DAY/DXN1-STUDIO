#!/usr/bin/env python3
"""THE ASCENT WALK — the dedicated level-6 summit (v3.1.141, R63).

R62 grew the tour's HOPS to level-6 (the sixth receipt counts the LOAD,
not the walk). This probe walks the ascent's INTERIOR alone (--scene, no
levels 1-5 tax; the 180s gate cap belongs to the climb) so the law can
be proven before the tour grows HOPS to level-7.

THE AUTOPSY THAT SHAPED THIS LAW (scenes/level-6.dxn1.json + spark.hpp):
  the scene: five vertical movers (lift-1 400<->230 @75, lift-2 230<->420
  @95, lift-3 400<->180 @85, summit-lift 180<->60 @70), two saws biting
  OVER their decks (saw-1 over terrace-2, saw-2 over mid-deck), three
  fangs on deck tops, the magnet at 150 (the gems collect themselves).
  The jump's honest ceiling: JUMPV^2/(2G) = 128.07px — every fire in
  this law was checked against it by hand (the draft's "jump to the
  terrace-2" from the lift-1's low half is geometrically dead: the deck
  at 400 stands 170px above the launch's reach).

  THE MID-DECK CROSING (the round's structural find): the mid-deck's
  safe stand zone between saw-2 (x 1500..1538, y 368..406) and fang-2
  (x 1630..1664) is x 1542..1596 — 54px wide. From lift-2's deck the
  FULL-hold flight lands x0+331 (the deck top fire) — the saw's band
  re-entry (the descent's feet-368 crossing, ~0.07s before the
  touchdown) forces the box past 1538+delta while the fang's shadow
  (the arrival slide) caps the landing at 1560: the window is ~1px
  wide at the deck's top phase — A LOTTERY, not a law. THE FIX: the
  PARTIAL HOLD — the fire releases its sustained 'd' mid-flight
  (st.hold_t); the AIR_DRAG 220/s then decays the flight's vx (the
  exact code path: dir==0 -> AIR_FRICTION*dt), shaving the drift by
  110*(t-t1)^2 AND softening the arrival vx to 330-220*(t-t1) — the
  brake slide shrinks quadratically. The solver searches t1 on a 10ms
  grid and fires only when the clearance, the landing window, the
  arrival slide and the living vx all pass — every margin computed,
  none assumed.

THE WALK (ten bands, first match wins — every fire PREDICTED, a miss
is a held stand or an honest death, never a leap of faith):
  START LEDGE (top 430): stand zone 240..315; the first board fires
    when catch_sim puts the box on lift-1's span (the solver owns the
    phase; the bonk's ascent-crossing check is the solver's).
  LIFT-1 RIDER: creep right to 508..536; the TERRACE JUMP fires near
    the cycle top (the deck 230..254): the drop to terrace-1 (250),
    the drift lands 740..786 — past fang-1's 700..734 shadow with the
    descent's feet-222 crossing clearing its x (>= 738).
  TERRACE-1: brake the arrival; stand zone 750..800; the TERRACE-2
    JUMP (rise 80) lands 944..990 — left of saw-1's stand shadow
    (1026..1098) WITH the arrival slide room (the slid end <= 1020).
  TERRACE-2: brake; stand zone 980..1006 (saw-1's shadow is 1026+);
    the LIFT-2 BOARD fires when catch_sim lands the box on lift-2's
    span 1244..1272 (the arrival slide keeps the box on the 110px
    deck); the saw's flight band cleared BOTH ways (the ascent entry
    past t=0.1164's x, the descent re-entry past 1098).
  LIFT-2 RIDER: brake; creep right to 1280..1300 (no edge hangs); the
    MID-DECK FIRE = THE PARTIAL HOLD SOLVER (above).
  MID-DECK: brake (the slide stops ~1571, clear of fang-2); stand zone
    1570..1585; the LIFT-3 BOARD fires when catch_sim lands the box on
    lift-3's low half 1794..1820 — over fang-2 (the ascent enters its
    x-window at feet ~345, the descent's feet-402 crossing past 1668).
  LIFT-3 RIDER: brake; creep to 1800..1840; the SKY-LEDGE JUMP fires
    near the cycle top (the deck 176..204): the drop to the ledge
    (200), the drift lands 1998..2086 — past fang-3's 1960..1994
    shadow, the descent's feet-172 crossing clearing its x.
  SKY-LEDGE: brake; stand zone 2020..2100; the SUMMIT-LIFT BOARD fires
    when catch_sim lands the box on the lift's span 2244..2272 (the
    100px deck is narrow — the gate is tight by geometry, the solver
    owns the phase).
  SUMMIT-LIFT RIDER: brake; creep to 2270..2285; the SUMMIT JUMP fires
    at the deck 100..140 (the rise 30..70 to the summit's 70): the
    drift lands 2400..2506 — the goal's x-band (2510..2540) is touched
    on the landing box's right edge or by the walk-in (the receipt
    decides, the machine never overrides it).
  SUMMIT: walk right into the goal.
The tour ends the moment the level-7 receipt lands — the machine
decides when it's done."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os, pty, re, select, sys, tempfile, time

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")

DEST = "level-7"                  # the receipt that ends the walk
CAP = 170.0                       # wall cap (gate 8 kills probes at 180)

tfd, TRACE = tempfile.mkstemp(prefix="dxn3_l6_", suffix=".trace")
os.close(tfd)

DIRTY0 = _os.popen(f"git -C {REPO!r} status --porcelain").read()

pid, fd = pty.fork()
if pid == 0:
    os.chdir(REPO)
    os.environ["TERM"] = "xterm-256color"
    os.environ["DXN3_TRACE"] = TRACE
    os.environ["DXN3_TRACE_MS"] = "25"
    os.execv(BIN, [BIN, "--scene", "scenes/level-6.dxn1.json"])
    os._exit(1)

buf = b""
def drainf(seconds):
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
MOVERL = re.compile(rb"MOVER n=(\S+) x=(-?[\d.]+) y=(-?[\d.]+) pxi=(\d+) dir=(-?\d+)")
WELCOME = re.compile(rb"EVENT shell: welcome to (.+?)\s*$", re.M)
RESPAWN = re.compile(rb"^  EVENT respawn", re.M)

def hop_hit(name, key):
    if isinstance(name, bytes):
        name = name.decode(errors="replace")
    return name == key or name.endswith("(" + key + ")")

class TraceTail:
    """the tail law (grand_tour's): new bytes only, the newest sample
    kept — plus the RESPAWN EYE: every 'EVENT respawn' line bumps a
    counter the decision reads (a death mid-flight must clear the
    flight latch even when the spawn sits < 400px from the pit)."""
    def __init__(self, path):
        self.path = path; self.pos = 0; self.tail = b""
        self.last = None
        self.welcome = None
        self.movers = {}
        self.respawns = 0
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
        self.tail = lines.pop()
        for ln in lines:
            m = LINE.search(ln)
            if m:
                self.last = (m.group(1), int(m.group(2)), float(m.group(3)),
                             float(m.group(4)), float(m.group(5)),
                             float(m.group(6)))
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
                if RESPAWN.match(ln):
                    self.respawns += 1

def trace_text():
    try:
        with open(TRACE, "rb") as f: return f.read()
    except OSError:
        return b""

tail = TraceTail(TRACE)

# ---- the constants (scenes/level-6.dxn1.json + native/src/spark.hpp) ----
G, JUMPV, RACCEL, RUNMAX = 1500.0, 620.0, 2300.0, 330.0
AIR_DRAG = 220.0                  # AIR_FRICTION: the no-input decay /s
HERO_W = 34.0

def dbg(tag, x, y, vx, note=""):
    if _os.environ.get("DXN3_L6_DEBUG"):
        print(f"[L6-{tag}] x={x:.0f} y={y:.0f} vx={vx:.0f} {note}",
              file=sys.stderr, flush=True)

def drift_wd(t, vx):
    """the held-'d' drift over t: the exact RUN_ACCEL ramp from the live
    vx to the 330 cap (the flight hold delivers every px of this)."""
    if vx >= RUNMAX:
        return RUNMAX * t
    tt = (RUNMAX - vx) / RACCEL
    if t <= tt:
        return vx * t + 0.5 * RACCEL * t * t
    return vx * tt + 0.5 * RACCEL * tt * tt + RUNMAX * (t - tt)

def drift_ph(t, t1, vx):
    """the PARTIAL-HOLD drift: the sustained 'd' until t1 (the exact
    ramp), then released — the AIR_DRAG 220/s owns the rest (the code
    path: dir==0 -> AIR_FRICTION*dt; the vx decays linearly, the drift
    gains vx*(t-t1) - 110*(t-t1)^2). The hold's own vx at t1 is capped
    at 330 (t1 >= 0.1 always saturates the ramp)."""
    d = drift_wd(t1, vx)
    if t <= t1:
        return d
    v1 = min(RUNMAX, vx + RACCEL * t1)
    dt = t - t1
    return d + v1 * dt - 0.5 * AIR_DRAG * dt * dt

def arc_t(rise):
    """the DESCENT time at which the arc's feet cross `rise` px above
    the launch (a negative rise = a drop, the formula holds); None if
    the plane sits above the apex (rise > JUMPV^2/(2G) = 128.07)."""
    d = JUMPV * JUMPV - 2.0 * G * rise
    if d < 0.0:
        return None
    return (JUMPV + d ** 0.5) / G

def arc_t_asc(rise):
    """the ASCENT time of the same crossing (the small root); None if
    the plane sits above the apex."""
    d = JUMPV * JUMPV - 2.0 * G * rise
    if d < 0.0:
        return None
    return (JUMPV - d ** 0.5) / G

def catch_sim(wp, speed, axis, plane_fixed, pos, tgt, feet0, x0, vx0,
              span_lo, span_w, tmax=1.7, dt=0.005):
    """THE HONEST CATCH — the moving-deck landing, simulated.

    wp = the deck's two waypoint coords on its axis (in path order),
    speed = pspeed, pos = the live coord, tgt = the waypoint index the
    deck heads to (the telemetry's pxi). axis 'y': the deck's plane is
    its own y (the span check uses the FIXED x extent [span_lo,
    +span_w]); axis 'x': the plane is plane_fixed (unused here) and
    the span MOVES with the deck.

    The hero: feet(t) = feet0 - 620t + 750t^2, x(t) = x0 + drift_wd(t,
    vx0) — the flight hold delivers every px. Steps 5ms: the first
    DESCENT crossing (the feet come onto the plane from above) with the
    landing box on the deck's span is THE LANDING; an ascent crossing
    with the box over the span is THE BONK (the resolve snaps him below
    — the deck is lost) and rejects the fire.
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


# ---- the ascent's movers (scenes/level-6.dxn1.json, path order) ----------
L1_WP, L1_SP, L1_LO, L1_W = (400.0, 230.0), 75.0, 460.0, 110.0
L2_WP, L2_SP, L2_LO, L2_W = (230.0, 420.0), 95.0, 1240.0, 110.0
L3_WP, L3_SP, L3_LO, L3_W = (400.0, 180.0), 85.0, 1790.0, 110.0
SL_WP, SL_SP, SL_LO, SL_W = (180.0, 60.0), 70.0, 2240.0, 100.0


class St:
    __slots__ = ("last_x", "last_jump", "flight", "hold", "fire_s",
                 "fire_vx", "fire_t", "hold_t", "seen_r")

    def __init__(self):
        self.last_x = None; self.last_jump = 0.0
        self.flight = False; self.hold = b"d"; self.fire_s = -1
        self.fire_vx = 0.0
        self.fire_t = 0.0            # the fire's predicted flight time
        self.hold_t = 0.0            # THE PARTIAL HOLD's release time
        self.seen_r = 0


def common_reset(st, h):
    x = h[2]
    if st.last_x is not None and abs(x - st.last_x) > 400:
        st.flight = False
        st.last_x = None
        return True
    return False


def middeck_solve(x, vx, feet0):
    """THE PARTIAL HOLD SOLVER (the round's engine): search the release
    t1 on a 10ms grid; every candidate must pass ALL of —
      (a) the saw-2 band clearance: the box past 1542 at the descent's
          feet-368 re-entry (the saw's y-band the box cannot overlap);
      (b) the landing window [1542, 1560] (past the saw's standing
          shadow, inside the 54px stand zone the fang's shadow caps);
      (c) the arrival slide: the brake slide varr^2/4600 keeps the
          slid end <= 1592 (4px inside fang-2's 1596 standing shadow);
      (d) the arrival vx >= 40 (a dead stall is not a landing).
    Returns the best-margin (t1, t_land, t_band, L, varr) or None."""
    t_land = arc_t(feet0 - 430.0)
    if t_land is None:
        return None
    t_band = arc_t(feet0 - 368.0)
    if t_band is None or t_band > t_land:
        t_band = t_land
    best = None
    n = int((t_land - 0.05 - 0.20) / 0.01) + 1
    for i in range(max(0, n)):
        t1 = 0.20 + i * 0.01
        if t1 > t_land - 0.05:
            break
        clr = x + drift_ph(t_band, t1, vx)
        if clr < 1542.0:
            continue                 # (a) fails; a longer hold only
                                     # raises the band drift, so keep
                                     # searching upward
        L = x + drift_ph(t_land, t1, vx)
        if not (1542.0 <= L <= 1584.0):
            continue                 # (b) — the cap is generous here:
                                     # the (c) slid-end check does the
                                     # real work (a deep release lands
                                     # far right and slides SHORT)
        varr = RUNMAX - AIR_DRAG * (t_land - t1)
        if varr < 40.0:
            continue                 # (d)
        end = L + varr * varr / 4600.0 + 2.0
        if end > 1592.0:
            continue                 # (c)
        score = min(clr - 1542.0, 1584.0 - L, 1592.0 - end)
        if best is None or score > best[0]:
            best = (score, t1, t_land, t_band, L, varr)
    if best is None:
        return None
    return best[1:]


def dec_level6(h, st, now):
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
    feet = y + 44.0
    fire = now - st.last_jump > 0.6

    # THE FLIGHT LATCH: the fire's sustained hold — the drift the
    # prediction assumed, delivered (b"" would let the 220 air friction
    # steal it). THE PARTIAL HOLD: the hold ends at st.hold_t (the
    # solver's release), then b"" — the drag owns the tail exactly as
    # the prediction computed. THE STALE-SAMPLE GUARD (the R58 law):
    # the telemetry trails the engine by up to 25ms, so the sample
    # right after a fire still reads GROUNDED — the latch clears only
    # on a landing sample newer than the fire by a 10-step margin.
    if st.flight:
        if grounded and s > st.fire_s + 10:
            st.flight = False
        elif grounded and s > st.fire_s + 4 and \
                vx > st.fire_vx + 120.0:
            # THE EATEN-W EYE (R60): grounded samples at +5..+10 whose
            # vx is RUNNING AWAY (the held 'd' adds +57px/s per line)
            # are PROOF the fire's 'w' never reached the engine.
            st.flight = False
        elif now - st.last_jump < st.hold_t:
            return st.hold           # the sustained hold
        else:
            return b""               # the released tail (the drag law)

    # ---- 1. THE START LEDGE (top 430, stand py 386, x <= 430): stand
    # zone 240..315 (the bonk-free stretch — the solver rejects the
    # rest); the first board fires when catch_sim lands the box on
    # lift-1's span 464..502 (the box + the arrival slide stay on the
    # 110px deck; every x in the zone owns a rise window 30..128).
    if grounded and 375 <= y <= 400 and x <= 430:
        st.last_x = x
        l1 = tail.movers.get("lift-1")
        if x > 315:
            return b"a" if vx > -150 else b""
        if x < 240:
            return b"d" if vx < 150 else b""
        if l1 is None or not fire or abs(vx) > 60.0:
            return b""               # the settle: the fire waits for
                                     # the deck's phase from a stand
        t, land, dpos, bonk = catch_sim(
            L1_WP, L1_SP, "y", 0.0, l1[1], l1[2], feet, x, vx,
            L1_LO, L1_W)
        if t is not None and not bonk and 464.0 <= land <= 502.0:
            dbg("start-board", x, y, vx,
                f"s={s} age={now-st.last_jump:.2f} l1={l1[1]:.0f} t={t:.2f} "
                f"land={land:.0f} deck={dpos:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 2. LIFT-1 RIDER (deck 460..570, ride py 186..356): creep
    # right into 508..536; the TERRACE JUMP fires near the cycle top
    # (the deck 230..254, the only reach: the terrace-1's 250 is at the
    # launch's own plane, and the deck's low half stands 150-170px ABOVE
    # the jump's 128px ceiling). The drift lands 740..786 — past
    # fang-1's 700..734 — and the descent's feet-222 crossing must
    # clear the fang's x (>= 738): the ascent side is safe by
    # construction (the box enters the fang's window at feet ~133,
    # already 89px above its 222 plane).
    if grounded and 455 <= x <= 545 and 180 <= y <= 365:
        st.last_x = x
        if x > 536:
            return b"a" if vx > -150 else b""
        if x < 508:
            return b"d" if vx < 150 else b""
        if not fire or abs(vx) > 60.0:
            return b""
        rise = feet - 250.0          # the plane-above convention (the
                                     # terrace 250 is a 0..24px DROP
                                     # from the deck's 226..254 top)
        if rise < -24.0 or rise > 4.0:
            return b""               # the deck 226..254 only
        t = arc_t(rise)
        if t is None:
            return b""
        land = x + drift_wd(t, vx)
        t2 = arc_t(feet - 222.0)
        clr = x + drift_wd(t2, vx) if t2 is not None else 1e9
        if 740.0 <= land <= 786.0 and clr >= 738.0:
            dbg("terrace-jump", x, y, vx, f"rise={rise:.0f} t={t:.2f} "
                f"land={land:.0f} clr={clr:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 3. TERRACE-1 (top 250, stand py 206, x 620..860): brake the
    # arrival (the slid end stays <= 816, the 860 edge owned); stand
    # zone 750..800; the TERRACE-2 JUMP (rise 80) lands 944..990 — left
    # of saw-1's stand shadow (1026..1098) with the arrival slide room
    # (the slid end <= 1020, 6px inside the shadow). The flight passes
    # UNDER the saw-1's band by construction: the box's right edge at
    # the landing is <= 1024 < 1060, the saw's x never overlapped.
    if grounded and 620 <= x <= 860 and 195 <= y <= 215:
        st.last_x = x
        if vx > 40:
            return b"a"              # THE ARRIVAL BRAKE
        if x > 790:
            return b"a" if vx > -150 else b""
        if x < 750:
            return b"d" if vx < 150 else b""
        if not fire or abs(vx) > 60.0:
            return b""
        t = arc_t(feet - 170.0)      # the rise 80 (the plane 80 ABOVE
                                     # the launch — y-down, 170 < 250)
        if t is None:
            return b""
        land = x + drift_wd(t, vx)
        if 944.0 <= land <= 990.0:
            dbg("terrace2-jump", x, y, vx, f"t={t:.2f} land={land:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 4. TERRACE-2 (top 170, stand py 126, x 940..1160): brake the
    # arrival; stand zone 980..1006 (saw-1's stand shadow begins at
    # 1026 — the box [980,1040] keeps 20px); the LIFT-2 BOARD fires
    # when catch_sim lands the box on lift-2's span 1244..1272 (the
    # arrival slide keeps the box + slide on the 110px deck). THE SAW'S
    # FLIGHT BAND cleared BOTH ways: the box's right edge at the
    # ascent's feet-108 crossing stays <= 1056 (the entry after the
    # clearance), and the descent's feet-108 re-entry happens with the
    # box already past 1102.
    if grounded and 940 <= x <= 1160 and 115 <= y <= 135:
        st.last_x = x
        l2 = tail.movers.get("lift-2")
        if vx > 40:
            return b"a"
        if x > 1000:
            return b"a" if vx > -150 else b""
        if x < 975:
            return b"d" if vx < 150 else b""
        if l2 is None or not fire or abs(vx) > 60.0:
            return b""
        ta = arc_t_asc(feet - 108.0)
        td = arc_t(feet - 108.0)
        if ta is None or td is None:
            return b""
        xe = x + drift_wd(ta, vx) + 34.0     # the box's right at the
                                             # ascent's 108 crossing
        xd = x + drift_wd(td, vx)            # the box's left at the
                                             # descent's re-entry
        t, land, dpos, bonk = catch_sim(
            L2_WP, L2_SP, "y", 0.0, l2[1], l2[2], feet, x, vx,
            L2_LO, L2_W)
        if _os.environ.get("DXN3_L6_DEBUG") and s % 8 == 0:
            _ls = f"{land:.0f}" if land is not None else "None"
            dbg("l2board-probe", x, y, vx,
                f"l2={l2[1]:.0f} pxi={l2[2]} t={t} land={_ls} "
                f"bonk={bonk} xe={xe:.0f} xd={xd:.0f}")
        if t is not None and not bonk \
                and 1244.0 <= land <= 1276.0 \
                and xe <= 1056.0 and xd >= 1102.0:
            dbg("lift2-board", x, y, vx,
                f"s={s} age={now-st.last_jump:.2f} l2={l2[1]:.0f} t={t:.2f} "
                f"land={land:.0f} deck={dpos:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 5. LIFT-2 RIDER (deck 1240..1350, ride py 186..376): brake
    # the arrival; creep right into 1280..1300 (no edge hangs — the
    # partial-hold solver needs no deck-edge lottery); the MID-DECK
    # FIRE = THE PARTIAL HOLD SOLVER (the round's engine, see the
    # header): the hold releases at t1, the drag eats 110*(t-t1)^2 of
    # the drift, the arrival vx softens to 330-220*(t-t1) and the brake
    # slide shrinks quadratically — the 54px stand zone between saw-2
    # and fang-2 becomes a LAW, not a lottery.
    if grounded and 1234 <= x <= 1320 and 180 <= y <= 380:
        st.last_x = x
        if vx > 40:
            return b"a"
        if x > 1300:
            return b"a" if vx > -150 else b""
        if x < 1280:
            return b"d" if vx < 150 else b""
        if not fire or abs(vx) > 30.0:
            return b""               # the tighter settle: the partial
                                     # hold's margins live on the live vx
        r = middeck_solve(x, vx, feet)
        if r is None:
            return b""
        t1, t_land, t_band, L, varr = r
        dbg("middeck-fire", x, y, vx,
            f"feet={feet:.0f} t1={t1:.2f} tland={t_land:.2f} L={L:.0f} "
            f"varr={varr:.0f}")
        st.last_jump = now; st.fire_s = s; st.fire_vx = vx
        st.flight = True; st.fire_t = t_land; st.hold_t = t1; st.hold = b"d"
        return b"wd"

    # ---- 6. THE MID-DECK (top 430, stand py 386, x 1400..1700): brake
    # the arrival (the slid end <= 1590, fang-2's 1596 shadow owned);
    # stand zone 1570..1585; the LIFT-3 BOARD fires when catch_sim
    # lands the box on lift-3's low half 1794..1820 — the deck's low
    # park is only 30px above the launch plane, the drift's reach
    # (223..235 at rise 30..41) is the binding constraint, so the zone
    # is tight and the gate is honest. Over fang-2 by construction: the
    # ascent enters its x-window at feet ~345 (57px above its 402
    # plane), the descent's feet-402 crossing happens with the box past
    # 1668 (the gate computes it live).
    if grounded and 1400 <= x <= 1700 and 375 <= y <= 395:
        st.last_x = x
        l3 = tail.movers.get("lift-3")
        if vx > 40:
            return b"a"
        if x > 1585:
            return b"a" if vx > -150 else b""
        if x < 1570:
            return b"d" if vx < 150 else b""
        if l3 is None or not fire or abs(vx) > 60.0:
            return b""
        t, land, dpos, bonk = catch_sim(
            L3_WP, L3_SP, "y", 0.0, l3[1], l3[2], feet, x, vx,
            L3_LO, L3_W)
        if t is None or bonk:
            return b""
        t402 = arc_t(feet - 402.0)
        clr = x + drift_wd(t402, vx) if t402 is not None else 1e9
        if 1794.0 <= land <= 1820.0 and clr >= 1668.0:
            dbg("lift3-board", x, y, vx,
                f"s={s} age={now-st.last_jump:.2f} l3={l3[1]:.0f} t={t:.2f} "
                f"land={land:.0f} deck={dpos:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 7. LIFT-3 RIDER (deck 1790..1900, ride py 136..356): brake
    # the arrival; creep into 1800..1840; the SKY-LEDGE JUMP fires near
    # the cycle top (the deck 176..204): the drop to the ledge (200),
    # the drift lands 1998..2086 — past fang-3's 1960..1994 shadow with
    # the descent's feet-172 crossing clearing its x (>= 1998). The
    # ledge's left edge is ADJACENT to the deck's right (1900 = 1900):
    # no gap, the flight just clears the ledge's box on the way.
    if grounded and 1785 <= x <= 1870 and 130 <= y <= 360:
        st.last_x = x
        if vx > 40:
            return b"a"
        if x > 1825:
            return b"a" if vx > -150 else b""
        if x < 1800:
            return b"d" if vx < 150 else b""
        if not fire or abs(vx) > 60.0:
            return b""
        rise = feet - 200.0          # the plane-above convention (the
                                     # ledge 200 is a 0..24px DROP from
                                     # the deck's 176..204 top)
        if rise < -24.0 or rise > 4.0:
            return b""               # the deck 176..204 only
        t = arc_t(rise)
        if t is None:
            return b""
        land = x + drift_wd(t, vx)
        t2 = arc_t(feet - 172.0)
        clr = x + drift_wd(t2, vx) if t2 is not None else 1e9
        if 1998.0 <= land <= 2086.0 and clr >= 1998.0:
            dbg("skyledge-jump", x, y, vx, f"rise={rise:.0f} t={t:.2f} "
                f"land={land:.0f} clr={clr:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 8. THE SKY-LEDGE (top 200, stand py 156, x 1900..2160):
    # brake the arrival (the slid end <= 2116, the 2160 edge owned);
    # stand zone 2020..2100; the SUMMIT-LIFT BOARD fires when catch_sim
    # lands the box on the lift's span 2244..2272 — the 100px deck is
    # narrow (the box + the slide = 64px of the 100), the gate is tight
    # by geometry and the solver owns the phase (the deck 60..180 @70;
    # the rise <= 126 caps the reachable half).
    if grounded and 1900 <= x <= 2160 and 145 <= y <= 165:
        st.last_x = x
        sl = tail.movers.get("summit-lift")
        if vx > 40:
            return b"a"
        if x > 2100:
            return b"a" if vx > -150 else b""
        if x < 2020:
            return b"d" if vx < 150 else b""
        if sl is None or not fire or abs(vx) > 60.0:
            return b""
        t, land, dpos, bonk = catch_sim(
            SL_WP, SL_SP, "y", 0.0, sl[1], sl[2], feet, x, vx,
            SL_LO, SL_W)
        if t is not None and not bonk and 2244.0 <= land <= 2272.0:
            dbg("summit-board", x, y, vx,
                f"s={s} age={now-st.last_jump:.2f} sl={sl[1]:.0f} t={t:.2f} "
                f"land={land:.0f} deck={dpos:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 9. SUMMIT-LIFT RIDER (deck 2240..2340, ride py 16..136):
    # brake the arrival; creep into 2270..2285; the SUMMIT JUMP fires
    # at the deck 100..140 (the rise 30..70 to the summit's top plane
    # 70): the drift lands 2400..2506 — the goal's x-band (2510..2540)
    # is touched by the landing box's right edge (L+34 >= 2510 for every
    # honest fire) or by the walk-in; the summit's own top (70) is
    # cleared on the ascent (the apex 12..42) and the landing IS the
    # touch. A deck lower than 100 overshoots the summit's right edge
    # (the drift >= 254 from the zone lands past 2524) — the gate
    # refuses and the ride continues.
    if grounded and 2235 <= x <= 2310 and 10 <= y <= 140:
        st.last_x = x
        if vx > 40:
            return b"a"
        if x > 2285:
            return b"a" if vx > -150 else b""
        if x < 2270:
            return b"d" if vx < 150 else b""
        if not fire or abs(vx) > 60.0:
            return b""
        rise = feet - 70.0
        if rise < 28.0 or rise > 72.0:
            return b""               # the deck 100..140 only
        t = arc_t(rise)
        if t is None:
            return b""
        land = x + drift_wd(t, vx)
        if 2400.0 <= land <= 2506.0:
            dbg("summit-jump", x, y, vx, f"rise={rise:.0f} t={t:.2f} "
                f"land={land:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx
            st.flight = True; st.fire_t = t; st.hold_t = t; st.hold = b"d"
            return b"wd"
        return b""

    # ---- 10. THE SUMMIT (top 70, stand py 26, x 2340..2560): walk
    # right into the goal — the receipt decides when the climb is done.
    if grounded and 2340 <= x <= 2560 and 15 <= y <= 35:
        st.last_x = x
        return b"d"

    # ---- 11. THE DEFAULT (any unbanded state): walk right — a
    # short-sitting hero feeds a fang honestly (the respawn is the
    # recovery; the saws and the void do the rest).
    st.last_x = x
    return b"d"


# ---- the walk itself -----------------------------------------------------
t0 = time.time()
alive = drainf(3.0)
scene = None
st = St()
while time.time() - t0 < CAP:
    tail.pump()                    # THE TAIL: new bytes only
    if tail.welcome and tail.welcome != scene:
        scene = tail.welcome
        st = St()
        tail.movers.clear()        # the new scene's decks speak for it
        if hop_hit(scene, DEST):
            break                  # THE MACHINE DECIDES: the ascent is
                                   # crossed when level-7's receipt lands
    h = tail.last
    if h:
        key = dec_level6(h, st, time.time())
        if key: send(key)
    if not drainf(0.0025):
        break
drainf(1.2)                        # the last load + its first frames
tr = trace_text()

pins = []
def pin(name, cond, detail=""):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""))

pin("boot alive (the scene game steps immediately — no esc, esc quits)",
    alive)
pin(f"the ascent crossed: the wire receipt 'welcome to {DEST}' (the goal "
    "touched, pendingNext consumed, the load spoken)",
    scene is not None and hop_hit(scene, DEST))
events = re.findall(rb"EVENT respawn\([^)]*\) ([^\n]*)", tr)
pin("every fall death named its spawn honestly",
    all(re.search(rb"-> -?\d+,-?\d+\s*$", e) for e in events))
pin("every respawn is the honest fall voice (no ghost states)",
    all(b"respawn(ouch" in m.group(0)
        for m in re.finditer(rb"EVENT respawn[^\n]*", tr)))
pin("the clock stayed honest through the whole walk (pi=0 — no pause "
    "was ever taken)",
    b"pi=0.00" in tr and b"pi=0.01" not in tr and b"pi=0.1" not in tr)
pin("the flood keeps flowing after the receipt", drainf(0.6))
pin("the walk stayed affordable (the honest deaths bounded — a law "
    "churning respawns is a broken law)",
    len(events) <= 60, f"{len(events)} deaths")

try: os.kill(pid, 15)
except Exception: pass
drainf(0.4)
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
if _os.environ.get("DXN3_L6_DEBUG"):
    _os.system(f"cp {TRACE} /tmp/l6_trace.txt")
if any(not ok for _, ok in pins):
    _fail_trace = f"/tmp/l6_fail_{int(time.time())}.trace"
    try:
        _os.system(f"cp {TRACE} {_fail_trace}")
        print(f"(the failed walk's trace kept at {_fail_trace})")
        import glob as _glob
        _olds = sorted(_glob.glob("/tmp/l6_fail_*.trace"))
        for _o in _olds[:-4]:
            try: os.unlink(_o)
            except Exception: pass
    except Exception:
        pass
try: os.unlink(TRACE)
except Exception: pass

dirty = _os.popen(f"git -C {REPO!r} status --porcelain").read()
pin("the walk wrote nothing (tree snapshot unchanged across the walk)",
    dirty == DIRTY0, dirty[:80])

fails = [n for n, ok in pins if not ok]
print(f"\ndec_level6_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s ({len(events)} honest deaths)")
sys.exit(1 if fails else 0)
