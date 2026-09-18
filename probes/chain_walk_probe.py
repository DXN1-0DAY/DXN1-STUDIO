#!/usr/bin/env python3
"""THE WIRE CHAIN WALK — the walk comes home (v3.1.104).

The engine's half of the scene chain (goal -> pendingNext -> load) is
pinned in selftest group 5b by TELEPORT-touch; the half this probe pins
is the SHELL's — a hero WALKING through the playground's door on the
wire, the shell consuming pendingNext and loading level-1, the walk
receipt spoken where machines read it.

THE R37 CRAWL, CLOSED: the first draft drove with Tab-inspect telemetry
and the clock crawled. The DXN3_TRACE receipts convicted the DRIVE, not
the engine — pi (inspect pause) ate ~0.73 of wall (the freeze-frame WAS
the crawl; acc=0 while inspect is open, and a no-op drain let the pty
back up and stretch it). The engine ran 1:1 honest with no driver. So
this probe never pauses: it steers on the engine's pause-free trace
telemetry (px/py/vx/vy at 25ms) and keeps the pty drained every
microsecond of its life.

THE FALL DEATH, FIXED: the headless walk_probe proved the door clip
(hero box right edge 1252 vs goal left 1250 — two pixels) but the wire
walks fell forever. The receipts convicted worldBottom(): the hero IS
an entity, so the max() floor dragged itself down with the faller and
the death line (worldBottom + 400) chased the fall one hero-depth
behind their feet — unsatisfiable, mathematically. With the player
excluded from the world extent every fall is an honest respawn, so the
walk retries per life: run right, wedge-jump the sign wedge at x=96,
spike-jump both windows, run off the edge at full speed and clip the
door. A missed life respawns and walks again.

THE RECEIPT LAW: the rendered say() is paint, not bytes — 'goal!' and
'welcome to level-1' never appear in the flood (the renderer draws the
screen cell by cell). The machine truth lives on the event wire:
EVENT goal(...) when the door touches, EVENT shell: welcome to
level-1 when the shell consumes pendingNext. The probe stops the
moment the receipt lands — the machine decides when it's done."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os, pty, re, select, sys, tempfile, time

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")

tfd, TRACE = tempfile.mkstemp(prefix="dxn3_chain_walk_", suffix=".trace")
os.close(tfd)

# the walk's own cleanliness: the tree snapshot BEFORE, compared AFTER —
# the walk must write NOTHING (the scene boot writes nothing, the door
# writes nothing), whether the tree around it is committed or mid-fix
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

LINE = re.compile(rb"px=(-?[\d.]+) py=(-?[\d.]+) vx=(-?[\d.]+) vy=(-?[\d.]+)")

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
    return (float(m.group(1)), float(m.group(2)),
            float(m.group(3)), float(m.group(4)))

t0 = time.time()
alive = drainf(3.0)

# ---- the walk: hold right, steer on the trace, NEVER pause ------------
SPIKE_WINDOWS = [(380.0, 452.0), (530.0, 690.0)]   # generous approach bands
RECEIPT = b"EVENT shell: welcome to level-1"
mark = len(buf)
stuck_n, last_jump, last_x = 0, 0.0, None
walked = False
CAP = 40.0
while time.time() - t0 < CAP:
    tr = trace_text()
    if RECEIPT in tr:
        walked = True
        break
    h = hero()
    if h:
        x, y, vx, vy = h
        grounded = abs(vy) < 1.0
        if last_x is not None and abs(x - last_x) < 0.5 and grounded:
            stuck_n += 1
        else:
            stuck_n = 0
        if last_x is not None and abs(x - last_x) > 400:
            stuck_n, last_x = 0, None       # a respawn teleported: reset
            continue
        now = time.time()
        if stuck_n >= 4 and now - last_jump > 0.35:
            send(b"w"); last_jump = now; stuck_n = 0      # wedged: hop it
        else:
            for lo, hi in SPIKE_WINDOWS:
                if lo <= x <= hi and grounded and now - last_jump > 0.55:
                    send(b"w"); last_jump = now            # clear the spikes
                    break
        last_x = x
    send(b"d")                          # the run is CONTINUOUS
    drainf(0.0025)

drainf(1.5)                             # the load + the first level-1 frames
tr = trace_text()
hero_final = hero()

pins = []
def pin(name, cond, detail=""):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""))

pin("boot alive (the scene game steps immediately — no esc, esc quits)",
    alive)
pin("THE DOOR TOUCH ON THE WIRE: EVENT goal( in the trace "
    "(overlap is AABB truth, not paint)",
    b"EVENT goal(" in tr)
pin("THE SHELL RECEIPT ON THE WIRE: pendingNext consumed, level-1 "
    "loaded, the load spoken on the event wire",
    walked, f"hero={hero_final}")
events = re.findall(rb"EVENT respawn\([^)]*\) ([^\n]*)", tr)
pre_load = [e for e in events if b"-> 90,300" in e]
post_load = [e for e in events if b"-> 60,300" in e]
pin("every fall death named its scene's own spawn honestly "
    "(playground 90,300 before the door, level-1 60,300 after)",
    all(b"-> 90,300" in e for e in pre_load) and
    all(b"-> 60,300" in e for e in post_load) and
    (b"EVENT respawn" not in tr or pre_load or post_load))
pin("every respawn is the honest fall voice (no ghost states)",
    all(b"respawn(ouch" in m.group(0)
        for m in re.finditer(rb"EVENT respawn[^\n]*", tr)))
pin("the clock stayed honest through the whole walk (pi=0 — no pause "
    "was ever taken; the R37 crawl is dead)",
    b"pi=0.00" in tr and b"pi=0.01" not in tr and b"pi=0.1" not in tr)
pin("the flood keeps flowing after the transition (level-1 runs)",
    drainf(0.6))

try: os.kill(pid, 15)
except Exception: pass
drainf(0.4)
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
try: os.unlink(TRACE)
except Exception: pass

dirty = _os.popen(f"git -C {REPO!r} status --porcelain").read()
pin("the walk wrote nothing (tree snapshot unchanged across the walk)",
    dirty == DIRTY0, dirty[:80])

fails = [n for n, ok in pins if not ok]
print(f"\nchain_walk_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
