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
# two scenes join the night BEFORE the boot: the bare :scene's count
# and the by-name resolution both read ./scenes — a night with no
# scenes can only confess a zero. (Child 2's setup below re-copies;
# idempotent by law.)
os.makedirs(os.path.join(WORK, "scenes"))
for _s in ("level-1", "level-2"):
    shutil.copyfile(os.path.join(REPO, "scenes", f"{_s}.dxn1.json"),
                    os.path.join(WORK, "scenes", f"{_s}.dxn1.json"))

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
    the bar, ONE HONEST CHAR AT A TIME (the R40 law — a burst is a gale
    the pty's one-frame mouth chokes on; `scene level-2` lost its tail
    mid-burst and the ghost's error taught the wrong lesson), enter —
    then WAIT FOR THE ANSWER."""
    global buf, in_ide
    buf = b""
    if in_ide:
        send(b"\x1b"); drainf(0.5)
        buf = b""
    send(":"); drainf(0.2)
    for _ch in line:
        send(_ch); time.sleep(0.03)
    drainf(0.15)
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

def wire_events(from_off=0, path=None):
    """the child's own confession file, from a byte offset — the wire
    flushes on its 25 ms tick, so a short settle precedes every read."""
    if path is None: path = TRACE
    time.sleep(0.35)
    try:
        with open(path, "rb") as f:
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
pin("the night's first word names the scene it opened with",
    b"EVENT shell: scene untitled" in ev, ev[:220])
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

# ---- 3b. the open's confession ------------------------------------------
# the shell's :open re-reads the file it already wears — the rail
# speaks, the wire speaks, the machine can pin both.
w = cmd("open probe_a.py", until=lambda b: b"engine: opened probe_a.py" in b)
pin("the open's receipt speaks on the rail",
    b"engine: opened probe_a.py" in w)
ev = wire_events(off); off += len(ev)
pin("the open's confession rides the wire",
    b"EVENT shell: opened probe_a.py" in ev, ev[-200:])

# ---- 3c. the template's confession --------------------------------------
# :new cycles the page — a stage change the wire used to miss (:scene
# and :open spoke, the gallery stayed silent). The rail names the new
# page ("engine: template — X (...)"), the wire names the same word:
# one truth, two mouths. The probe does not guess the gallery's order
# — it reads the name from the rail and demands the wire agree.
w = cmd("new", until=lambda b: b"engine: template" in b)
m = re.search(rb"engine: template \xe2\x80\x94 ([a-z]+) ", w)
pin("the new page's receipt speaks on the rail", m is not None, w[-140:])
ev = wire_events(off); off += len(ev)
nm = m.group(1) if m else b""
pin("the template's name rides the wire",
    nm and b"EVENT shell: template " + nm in ev, ev[-200:])

# the cycle changed the page the studio wears (the :wq below would
# save the TEMPLATE's page, not the night's story — its receipt said
# exactly that when the pin went red: `saved untitled.py (+0 ~9 -25)`).
# The page is given back before the farewell save.
w = cmd("open probe_a.py", until=lambda b: b"engine: opened probe_a.py" in b)

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

# ---- 5. the scene's save confesses too (a play-mode night) -------------
# a session where NO IDE ever opened: boot on a scene in play, :w —
# the shell's save wears the wire as well (the IDE's saves spoke in
# the last scenario; ideEver was true, so the play-mode :w saved the
# DOC. This child never takes the stage: the scene belongs to the
# shell alone). The second night gets its own trace file — the trace
# opens trunc, and the first night's word is already read and pinned.
TRACE2 = os.path.join(WORK, "wire2.log")
SCENES = os.path.join(WORK, "scenes")
os.makedirs(SCENES, exist_ok=True)
SRC = os.path.join(REPO, "scenes", "playground.dxn1.json")
SEEN = os.path.join(SCENES, "playground.dxn1.json")
shutil.copyfile(SRC, SEEN)
src_bytes = open(SRC, "rb").read()

pid, fd = pty.fork()
if pid == 0:
    os.chdir(WORK)
    os.environ["TERM"] = "xterm-256color"
    os.environ["DXN3_TRACE"] = TRACE2
    os.environ["DXN3_TRACE_MS"] = "25"
    os.execv(BIN, [BIN, "scenes/playground.dxn1.json"])
    os._exit(1)

buf = b""
in_ide = False                      # play mode: ':' IS the bar, no esc
alive2 = drainf(3.0)
pin("the play-mode studio boots alive", alive2)
off2 = 0
w = cmd("w", until=lambda b: b"saved" in b, takes_stage=False)
ev2 = b""
end = time.time() + 4.0
while time.time() < end:
    chunk = wire_events(off2, TRACE2)
    off2 += len(chunk)
    ev2 += chunk
    if b"EVENT shell: scene saved" in ev2:
        break
pin("the shell's scene save rides the wire",
    b"EVENT shell: scene saved scenes/playground.dxn1.json" in ev2,
    ev2[-200:])
pin("the play night opens by naming its scene too",
    b"EVENT shell: scene playground\n" in ev2, ev2[:220])
pin("the pen kept the bytes it found (the .bak is the original)",
    os.path.exists(SEEN + ".bak") and
    open(SEEN + ".bak", "rb").read() == src_bytes)
pin("the saved scene is a real scene again",
    os.path.exists(SEEN) and open(SEEN, "rb").read().startswith(b"{"))

# ---- 6. the manual :scene rides the direct line (and the refusals'
# silence is law) ----------------------------------------------------------
# the verb's load used to PARK its word on the fresh Game's slot — the
# cadence's whenever, one host rebuild away from a dying slot. The
# census's law (the direct line) says a receipt tied to an instant
# speaks the moment the hand returns. The refusals keep the :open law:
# the rail speaks them, the wire stays silent — and the silence is
# PINNED, so it is law, not omission. Two more scenes join the temp
# dir first: sceneStems() scans ./scenes, and resolution needs names.
for _s in ("level-1", "level-2"):
    shutil.copyfile(os.path.join(REPO, "scenes", f"{_s}.dxn1.json"),
                    os.path.join(SCENES, f"{_s}.dxn1.json"))

# the ambiguous refusal: 'lev' matches two stems, the bar lists, the
# wire says nothing (no load happened — the wire does not fib).
w = cmd("scene lev", until=lambda b: b"ambiguous scene 'lev'" in b,
        takes_stage=False)
pin("the ambiguous refusal lists itself on the rail",
    b"ambiguous scene 'lev'" in w and b"level-1" in w and b"level-2" in w,
    w[-160:])
ev6 = wire_events(off2, TRACE2); off2 += len(ev6)
pin("the refusal's wire silence is law",
    b"EVENT shell: scene" not in ev6, ev6[-200:])

# the ghost: a name nobody owns passes through to loadScene's honest
# error — the rail speaks, the wire keeps the same law.
w = cmd("scene ghost", until=lambda b: b"no such file" in b,
        takes_stage=False)
pin("the ghost's honest error speaks on the rail",
    b"no such file" in w, w[-160:])
ev6 = wire_events(off2, TRACE2); off2 += len(ev6)
pin("the ghost's wire silence is the same law",
    b"EVENT shell: scene" not in ev6, ev6[-200:])

# the load: :scene level-2 — the wire speaks the INSTANT the hand
# returns (the direct line), naming the scene the shell wears now.
w = cmd("scene level-2", until=lambda b: True, cap=2.0, takes_stage=False)
ev6 = b""
end = time.time() + 4.0
while time.time() < end:
    chunk = wire_events(off2, TRACE2)
    off2 += len(chunk)
    ev6 += chunk
    if b"EVENT shell: scene level-2\n" in ev6:
        break
pin("the manual load's word rides the wire",
    b"EVENT shell: scene level-2\n" in ev6,
    f"rail={w[-120:]!r} wire={ev6[-200:]!r}")

# and the pen's home moved with the verb: the play-mode :w now saves
# the scene the shell wears — level-2, not the playground it was born
# with (scenePath = resolved is the law the save confesses).
w = cmd("w", until=lambda b: b"saved" in b, takes_stage=False)
ev6 = b""
end = time.time() + 4.0
while time.time() < end:
    chunk = wire_events(off2, TRACE2)
    off2 += len(chunk)
    ev6 += chunk
    if b"EVENT shell: scene saved scenes/level-2.dxn1.json" in ev6:
        break
pin("the verb moved the pen's home (:w saves what :scene wore)",
    b"EVENT shell: scene saved scenes/level-2.dxn1.json" in ev6, ev6[-200:])
pin("the moved pen kept the bytes it found (level-2's .bak is born)",
    os.path.exists(os.path.join(SCENES, "level-2.dxn1.json") + ".bak"))

# ---- 6b. bare :scene confesses where you stand ---------------------------
# the fixing of :scene-by-name made the bare verb's silence a lie of
# its own: it answered "no such file" for an EMPTY question (the
# parser's needsArg law answered before the verb could). This
# play-mode night is the honest home for the pin — no IDE reflex to
# fight (ideEver false: no auto-run, no page churn). The bare verb
# takes the stage (the family law) and names the wearing — level-2,
# the scene the shell has worn since the load — and the count: three
# scenes (the playground the night was born with, plus the two the
# setup planted). The roster itself lives in the whisper, where an
# empty prefix matches every stem.
w = cmd("scene", until=lambda b: b"engine: wearing" in b, takes_stage=False)
pin("the bare scene names the wearing and the count",
    b"wearing level-2" in w and b"3 scenes answer by name" in w, w[-180:])

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
