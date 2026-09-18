#!/usr/bin/env python3
"""R40 probe: one event wire, every save — the IDE's pen confesses on
DXN3_TRACE. The sim had a wire (respawn, the shell's chain receipts)
but the IDE's saves were mute on it: the rail heard the census, the
wire heard nothing. Now every save (save-as, plain :w, ctrl+S, :wq)
wears its census on the wire: `EVENT ide: saved <path> (+a ~c -r)`,
"(same)" when the storyless pen fell, " bak" when a past was kept.
Drives the real binary in a pty, cwd = a temp dir, DXN3_TRACE=<file>
at 25 ms; the wire's word is read from the file the child itself
writes — the probe never trusts its own echo.

Driving law (inherited from ide_door_probe): the boot stage is the
editor; esc to play, ':' opens the bar, the verb takes the stage back.
Typing goes into the DOC only when the editor holds the stage."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import os, pty, select, time, sys, shutil, re

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")
WORK = "/tmp/dxn3_wire_e2e"
TRACE = os.path.join(WORK, "wire.log")

shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK)

pid, fd = pty.fork()
if pid == 0:
    os.chdir(WORK)
    os.environ["TERM"] = "xterm-256color"
    os.environ["DXN3_TRACE"] = TRACE
    os.environ["DXN3_TRACE_MS"] = "25"
    os.execv(BIN, [BIN])
    os._exit(1)

buf = b""
def drainf(seconds):
    global buf
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.02)
        if r:
            try: chunk = os.read(fd, 65536)
            except OSError: return False
            if not chunk: return False
            buf += chunk
    return True

def send(s):
    os.write(fd, s if isinstance(s, bytes) else s.encode())

in_ide = True
def cmd(line, until=None, cap=2.5, takes_stage=True):
    """the ide_door law: esc when the editor holds the stage, ':' opens
    the bar, one honest burst, enter — then WAIT FOR THE ANSWER."""
    global buf, in_ide
    buf = b""
    if in_ide:
        send(b"\x1b"); drainf(0.5)
        buf = b""
    send(":"); drainf(0.2)
    send(line); drainf(0.15)
    send("\r")
    mark = len(buf)
    end = time.time() + cap
    if until is not None:
        while time.time() < end:
            if until(buf[mark:]):
                break
            if not drainf(0.06):
                break
    else:
        drainf(0.5)
    in_ide = takes_stage
    return buf

def wire_events(from_off=0):
    """the child's own confession file, from a byte offset — the wire
    flushes on its 25 ms tick, so a short settle precedes every read."""
    time.sleep(0.35)
    try:
        with open(TRACE, "rb") as f:
            f.seek(from_off)
            return f.read()
    except OSError:
        return b""

pins = []
def pin(name, cond, detail=""):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""))

t0 = time.time()
alive = drainf(3.0)
pin("boot alive", alive)

off = 0   # the wire's read head: each step reads only its own night

# ---- 1. the save-as rides the wire with its birth census ---------------
w = cmd("w probe_a.py", until=lambda b: b"saved as probe_a.py" in b)
pin("the save-as receipt speaks on the rail",
    b"saved as probe_a.py" in w)
ev = wire_events(off); off += len(ev)
m = re.search(rb"EVENT ide: saved probe_a\.py\s*\(\+\d+ ~\d+ -\d+\)", ev)
pin("the save-as census rides the wire", m is not None, ev[-200:])
pin("the birth census speaks real adds",
    m is not None and b"(+0 ~" not in m.group(0), m.group(0) if m else "")
# one truth, two mouths: the rail's census and the wire's census must
# name the same numbers — the event wire is not a second opinion
rail_c = re.search(rb"saved as probe_a\.py\s*\(\+(\d+) ~(\d+) -(\d+)\)", w)
wired_c = re.search(rb"EVENT ide: saved probe_a\.py\s*\(\+(\d+) ~(\d+) -(\d+)\)", ev)
pin("the rail's census and the wire's census agree",
    rail_c is not None and wired_c is not None and
    rail_c.groups() == wired_c.groups(),
    f"rail={rail_c.groups() if rail_c else None} "
    f"wire={wired_c.groups() if wired_c else None}")

# ---- 2. the storyless save confesses (same) on the wire ----------------
# a save-as to the name it already wears: the census calls it same, the
# rail speaks no counts (the past is still kept — (.bak kept) rides),
# and the wire is not allowed the rail's silence — a save the disk
# heard IS a fact, even when nothing changed.
w = cmd("w probe_a.py", until=lambda b: b"saved as probe_a.py" in b)
pin("the storyless rail speaks no census",
    b"engine: saved as probe_a.py  (.bak kept)" in w, w[-140:])
ev = wire_events(off); off += len(ev)
pin("the storyless save confesses (same) on the wire",
    b"EVENT ide: saved probe_a.py (same) bak\n" in ev, ev[-200:])

# ---- 3. the keyboard's :w (ctrl+S) rides the same wire -----------------
# the editor holds the stage: honest typing goes into the DOC, then the
# old reflex saves. Typed like a hand — one char at a time: a burst is
# a gale the pty's one-frame mouth can choke on (the debug lesson that
# bought this pin: slow bytes land, bursts vanish into the flood).
# And the pin reads the WIRE, not the flood: the rail's receipt sits
# behind the render backlog (the render flood never sleeps), while the
# save's confession is written straight to the trace file the moment
# the pen falls — the machine's word, not the paint's.
for _ch in b"the wire hears the pen":
    send(bytes([_ch])); time.sleep(0.03)
# the reflex rides IN the idle window: the machine auto-runs (and the
# auto-run SAVES) after 0.6s of a dirty idle — pause here and the
# keyboard's save finds the disk already heard the page: a storyless
# census that would teach the wrong lesson. \r then \x13, back to back.
send(b"\r"); send(b"\x13"); drainf(0.3)   # ctrl+S — the keyboard's own :w
end = time.time() + 4.0
evtail = b""
while time.time() < end:
    chunk = wire_events(off)
    off += len(chunk)
    evtail += chunk
    if re.search(rb"EVENT ide: saved probe_a\.py\s*\(\+\d+ ~\d+ -\d+\) bak",
                 evtail):
        break
pin("the keyboard's save confesses on the wire",
    re.search(rb"EVENT ide: saved probe_a\.py\s*\(\+\d+ ~\d+ -\d+\) bak",
              evtail) is not None, evtail[-200:])
pin("the hand's save is not a storyless one",
    re.search(rb"EVENT ide: saved probe_a\.py\s*\(\+[1-9]", evtail)
    is not None, evtail[-200:])

# ---- 4. :wq — the save rides the wire even as the studio sleeps --------
w = cmd("wq", until=lambda b: True, cap=1.2, takes_stage=False)
time.sleep(0.8)                     # the normal exit flushes the streams
ev = wire_events(off); off = len(ev) if off == 0 else off + len(ev)
try: os.waitpid(pid, os.WNOHANG)
except Exception: pass
pin("the wq save rides the wire with the kept past",
    re.search(rb"EVENT ide: saved probe_a\.py.* bak", ev) is not None,
    ev[-200:])
gone = True
try:
    r = os.waitpid(pid, os.WNOHANG)
    gone = r[0] == pid
except ChildProcessError:
    gone = True
except Exception:
    gone = False
pin("the studio sleeps after the save", gone)

# ---- cleanup -----------------------------------------------------------
try: os.kill(pid, 15)
except Exception: pass
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
shutil.rmtree(WORK, ignore_errors=True)

fails = [n for n, ok in pins if not ok]
print(f"\nide_wire_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
