#!/usr/bin/env python3
"""THE VAULT WALK — the dedicated vault summit (v3.1.136, R58).

R55 walked the tour to level-5's receipt and drafted the vault interior
(dec_vault, dormant). R57 mined the five red runs: 15/21 deaths in the
px 410-520 transfer pit, the decks OPPOSITE-moving at the fall moments.
This probe walks the vault ALONE (the engine takes --scene — no levels
1-4 tax, the 180s gate cap belongs to the vault) so the law can be
proven before the tour grows HOPS to level-6.

THE AUTOPSY THAT SHAPED THIS LAW (from the scene json + spark.cpp):
  the draft's fires were geometrically dead in three places —
  (1) the l2->deck gate allowed landings at 838..940, but the deck-guard
      hangs at 760..798 OVER the high-deck: the box's y overlaps the
      guard's band from t=0.09s to the LANDING itself (the stand box
      136..180 lives inside the band's 116..154), so the landing box
      must clear the guard's x — land <= 725, never 838+;
  (2) the ferry->isle fire from the guard-safe strip (1404..1424) lands
      at 1684..1726 — PAST the isle's 1680 edge: the gate 1538..1672
      could never pass and the fire never fired; the isle jump is a
      PURE VERTICAL hop fired where the ride carries the box over the
      isle's top (x >= 1510, the deck's right extreme);
  (3) the guard-jump window [565,633] hangs OFF the deck (the deck
      starts at 640) — a hero obeying it walked into the void.

THE HONEST CATCH (the round's engine): every fire onto a MOVER is
predicted by catch_sim() — the deck's ping-pong kinematics (waypoints,
speed, live pose/phase from the telemetry) stepped at 5ms against the
hero's jump parabola (feet = feet0 - 620t + 750t^2, gravity 1500) and
the held-'d' drift (drift_wd: the exact RUN_ACCEL 2300 ramp to the 330
cap, matching the flight hold). The first descent crossing with the box
on the deck's span is THE LANDING; an ascent crossing over the span is
THE BONK (the resolve snaps him below) and rejects the fire. Static
targets (the high-deck, the isle) use the closed-form arc.

THE WALK (eight bands, first match wins — every fire PREDICTED, a miss
is a held stand or an honest death, never a leap of faith):
  START LEDGE (top 430): shuttle 45..200; fire when catch_sim puts the
    box on lift-1's span (the deck descending OR rising — the solver
    owns the phase; the run and the stand both predict honestly).
  LIFT-1 RIDER: pulse-creep left to 298..316; the TRANSFER fires when
    catch_sim lands the box on lift-2's RISING deck (a descending deck
    recedes at 95px/s — no drift reaches it, R55's 620..687 falls).
  LIFT-2 RIDER: pulse to 481..505; the DECK-JUMP fires when the arc to
    the high-deck (rise feet-180) lands the box in 644..722 — LEFT of
    the guard's 760 with the whole flight's x monotonic under 759, so
    the guard's band is cleared by construction.
  HIGH-DECK: the GUARD-JUMP (stand fire 640..671, the apex clears the
    band's y, the descent re-enters it PAST 798) lands 880..920; the
    EDGE-JUMP (stand fire 860..884) drops the arc onto the drop-ledge
    past fang-1 (the descent crosses the fang's y at x ~1151+).
  DROP-LEDGE: walk to 1130..1185; the FERRY BOARD fires when catch_sim
    lands the box on ferry-1's carried span with the ride offset 30..84
    (the offset pins the isle jump's reach) and land >= 1406 (past the
    ferry-guard's 1326..1398 stand-kill shadow).
  FERRY RIDER: walk right (never into the shadow — the landing is past
    it and walking right only grows x); brake at 1502, the ISLE JUMP is
    a pure vertical 'w' (hold b"" — the momentum would carry +210 past
    the isle) fired from the stand over the isle's top.
  ISLE: walk right into 1564..1659 at full run; the GOAL JUMP's touch
    is gated on the box crossing the goal's x-band INSIDE the y-overlap
    window t in [0.82, 0.914] — the touch happens mid-flight, the
    death-trap stretch beyond is never stood on.
The tour ends the moment the level-6 receipt lands — the machine
decides when it's done."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os, pty, re, select, sys, tempfile, time

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")

DEST = "level-6"                  # the receipt that ends the walk
CAP = 170.0                       # wall cap (gate 8 kills probes at 180)

tfd, TRACE = tempfile.mkstemp(prefix="dxn3_vault_", suffix=".trace")
os.close(tfd)

DIRTY0 = _os.popen(f"git -C {REPO!r} status --porcelain").read()

pid, fd = pty.fork()
if pid == 0:
    os.chdir(REPO)
    os.environ["TERM"] = "xterm-256color"
    os.environ["DXN3_TRACE"] = TRACE
    os.environ["DXN3_TRACE_MS"] = "25"
    os.execv(BIN, [BIN, "--scene", "scenes/level-5.dxn1.json"])
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

# ---- the constants (scenes/level-5.dxn1.json + native/src/spark.hpp) ----
G, JUMPV, RACCEL, RUNMAX = 1500.0, 620.0, 2300.0, 330.0
HERO_W = 34.0

def dbg(tag, x, y, vx, note=""):
    if _os.environ.get("DXN3_VAULT_DEBUG"):
        print(f"[V-{tag}] x={x:.0f} y={y:.0f} vx={vx:.0f} {note}",
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

def arc_t(rise):
    """the descent time at which the arc's feet cross `rise` px above
    the launch; None if the plane sits above the apex."""
    d = JUMPV * JUMPV - 2.0 * G * rise
    if d < 0.0:
        return None
    return (JUMPV + d ** 0.5) / G

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


class St:
    __slots__ = ("last_x", "last_jump", "flight", "hold", "fire_s",
                 "fire_vx",
                 "seen_r")

    def __init__(self):
        self.last_x = None; self.last_jump = 0.0
        self.flight = False; self.hold = b"d"; self.fire_s = -1
        self.fire_vx = 0.0
        self.seen_r = 0


def common_reset(st, h):
    x = h[2]
    if st.last_x is not None and abs(x - st.last_x) > 400:
        st.flight = False
        st.last_x = None
        return True
    return False


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
        elif grounded and s > st.fire_s + 4 and \
                vx > st.fire_vx + 120.0:
            # THE EATEN-W EYE (R60, vx-gated after the tour's runs 7-9
            # lesson): grounded samples at +5..+10 whose vx is RUNNING
            # AWAY (the held 'd' adds +57px/s per line) are PROOF the
            # fire's 'w' never reached the engine. The PRE-JUMP stale
            # lines carry vx ~= fire_vx and can NEVER trip +120 — the
            # fixed-threshold eye false-released REAL flights under
            # load. A fire from a run keeps the full 10-step margin.
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
            dbg("transfer", x, y, vx,
                f"s={s} age={now-st.last_jump:.2f} l2={l2[1]:.0f} t={t:.2f} land={land:.0f} deck={dpos:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b"d"
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
        if 654.0 <= land <= 668.0:   # (R60b) was 722/680 — the
                                     # arrivals land at vx 330 and the
                                     # brake slide is ~40px; the upper
                                     # landings slid into the guard's
                                     # 727 shadow (the saw deaths)
            dbg("deck-jump", x, y, vx,
                f"rise={rise:.0f} t={t:.2f} land={land:.0f}")
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b"d"
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
                        dbg("edge-jump", x, y, vx, f"land={land:.0f}")
                        st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b"d"
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
        if 672 <= x <= 726:
            return b"a"               # THE OWNERSHIP HOLE (R60, the
                                      # tour's run-6 saw deaths at
                                      # 686..735): the deck-jump lands
                                      # the box at 654..722 but the
                                      # guard-jump window ends at 671 —
                                      # the upper landings owned NOTHING
                                      # and the default 'd' walked them
                                      # into the guard's 727 shadow.
        if 631 <= x <= 671:           # THE GUARD-JUMP window (stand
                                      # fire) — the deck's left edge
                                      # parks landings at 630-640 and
                                      # the fire reaches x >= 628.8
            if abs(vx) < 40:
                t = arc_t(0.0)              # the same plane: t = 0.827
                land = x + drift_wd(t, vx)
                xc = x + drift_wd(0.706, vx)   # the band's y re-entry
                if 876.0 <= land <= 914.0 and xc >= 798.0:
                    dbg("guard-jump", x, y, vx, f"land={land:.0f}")
                    st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b"d"
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
                    dbg("ferry-board", x, y, vx,
                        f"t={t:.2f} land={land:.0f} deck={dpos:.0f} "
                        f"off={off:.0f}")
                    st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b"d"
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
            dbg("isle-jump", x, y, vx)
            st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b""
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
                dbg("goal-jump", x, y, vx,
                    f"t82={t82:.0f} t91={t91:.0f}")
                st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b"d"
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
                    dbg("start-board", x, y, vx,
                        f"s={s} age={now-st.last_jump:.2f} l1={l1[1]:.0f} t={t:.2f} land={land:.0f} "
                        f"deck={dpos:.0f}")
                    st.last_jump = now; st.fire_s = s; st.fire_vx = vx; st.flight = True; st.hold = b"d"
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
            break                  # THE MACHINE DECIDES: the vault is
                                   # crossed when level-6's receipt lands
    h = tail.last
    if h:
        key = dec_vault(h, st, time.time())
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
pin(f"the vault crossed: the wire receipt 'welcome to {DEST}' (the goal "
    "touched mid-flight, pendingNext consumed, the load spoken)",
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
if _os.environ.get("DXN3_VAULT_DEBUG"):
    _os.system(f"cp {TRACE} /tmp/vault_trace.txt")
if any(not ok for _, ok in pins):
    _fail_trace = f"/tmp/vault_fail_{int(time.time())}.trace"
    try:
        _os.system(f"cp {TRACE} {_fail_trace}")
        print(f"(the failed walk's trace kept at {_fail_trace})")
        import glob as _glob
        _olds = sorted(_glob.glob("/tmp/vault_fail_*.trace"))
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
print(f"\ndec_vault_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s ({len(events)} honest deaths)")
sys.exit(1 if fails else 0)
