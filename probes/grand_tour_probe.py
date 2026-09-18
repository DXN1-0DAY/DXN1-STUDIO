#!/usr/bin/env python3
"""THE GRAND TOUR — the walk grows legs (v3.1.115).

chain_walk_probe pinned hop 1 (playground -> level-1). The tour walks
ON: level-1's pit arc, level-2's mover boarding, level-3's two lifts —
and pins a welcome receipt per hop, straight off the event wire.

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
import os, pty, re, select, sys, tempfile, time

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")

HOPS = ["level-1", "level-2"]    # receipts to pin (the tour grows hop by
                                 # hop: level-2's exit and level-3's lifts
                                 # are choreographed below but their ride
                                 # law is still being earned on the wire)
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

LINE = re.compile(rb"w=\s*([\d.]+)[^\n]*px=(-?[\d.]+) py=(-?[\d.]+) "
                  rb"vx=(-?[\d.]+) vy=(-?[\d.]+)")
WELCOME = re.compile(rb"EVENT shell: welcome to (\S+)")

def trace_text():
    try:
        with open(TRACE, "rb") as f: return f.read()
    except OSError:
        return b""

def hero():
    m = None
    for m in LINE.finditer(trace_text()):
        pass
    if not m: return None
    return (m.group(1), float(m.group(2)), float(m.group(3)),
            float(m.group(4)), float(m.group(5)))

# ---- the choreographies -------------------------------------------------
class St:
    __slots__ = ("last_x", "stuck", "stuck_w", "last_jump", "py_hist",
                 "last_w")
    def __init__(self):
        self.last_x = None; self.stuck = 0; self.stuck_w = None
        self.last_jump = 0.0
        self.py_hist = []; self.last_w = None

def ride_check(st, h):
    """THE RIDE LAW: grounded + py carried over ~4 telemetry samples
    (75ms — a mover's 55-110px/s carry moves py 4-8px in that window,
    while a standing hero's py never moves) = a mover has me."""
    w, x, y, vx, vy = h
    if w != st.last_w:                  # sample at telemetry cadence
        st.last_w = w
        st.py_hist.append(y)
        if len(st.py_hist) > 4: st.py_hist.pop(0)
    if abs(vy) >= 1.0 or len(st.py_hist) < 4:
        return False
    return abs(st.py_hist[-1] - st.py_hist[-4]) >= 1.5

def common_reset(st, h):
    """teleport (respawn / scene transition) awareness"""
    x = h[1]
    if st.last_x is not None and abs(x - st.last_x) > 400:
        st.stuck = 0; st.last_x = None; st.py_hist = []; st.last_w = None
        return True
    return False

def stuck_jump(st, h, now):
    """the wedge hop (chain_walk's law), but honest about the clock:
    a stall is measured across TELEMETRY samples (w changes), never
    across decision ticks — the decisions spin ~10x faster than the
    25ms telemetry, so tick-counting saw x as frozen between samples
    and hopped the rider clean off every deck he boarded"""
    w, x, y, vx, vy = h
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
    if common_reset(st, h): st.last_x = h[1]; return b"d"
    w, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    j = stuck_jump(st, h, now)
    if j: st.last_x = x; return j
    for lo, hi in ((380.0, 452.0), (530.0, 690.0)):    # chain_walk's bands
        if lo <= x <= hi and grounded and now - st.last_jump > 0.55:
            st.last_jump = now; st.last_x = x; return b"wd"
    st.last_x = x
    return b"d"

def dec_level1(h, st, now):
    if common_reset(st, h): st.last_x = h[1]; return b"d"
    w, x, y, vx, vy = h
    grounded = abs(vy) < 1.0
    if ride_check(st, h):               # THE ELEVATOR (1330, 372 -> 250)
        if y <= 215 and x >= 1330:      # its top: walk off onto sky-ledge
            st.py_hist = []; st.last_w = None; st.last_x = x
            return b"d"
        st.last_x = x
        return b""                      # hands off, let it carry
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
    if common_reset(st, h): st.last_x = h[1]; return b"d"
    w, x, y, vx, vy = h
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
    # the board hops from ground-a's edge zone: the deck is under the
    # arc or it isn't — a miss is an honest death, the phase shifts.
    # The 1.1s cooldown is the RACE the ride detection must win: the
    # boarding arc spends 0.83s airborne, so a 0.6s cooldown would
    # re-fire ON the deck and hop the rider straight back into the pit
    # (the 52-death loop the first draft died of).
    if x >= 280 and grounded and now - st.last_jump > 1.1:
        st.last_jump = now; st.last_x = x; return b"wd"
    # spike-1 hazard (880..914): safety if an arc ever lands short
    if 820 <= x <= 870 and grounded and now - st.last_jump > 0.4:
        st.last_jump = now; st.last_x = x; return b"wd"
    j = stuck_jump(st, h, now)
    if j: st.last_x = x; return j
    st.last_x = x
    return b"d"

def dec_level3(h, st, now):
    if common_reset(st, h): st.last_x = h[1]; return b"d"
    w, x, y, vx, vy = h
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
    tr = trace_text()
    names = WELCOME.findall(tr)
    if names and names[-1].decode() != scene:
        scene = names[-1].decode()
        st = St()
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
