#!/usr/bin/env python3
"""R31 probe: the save speaks the census (:w/save-as receipt wears
(+added ~changed -removed), :journal remembers) and the wardrobe's
door (:theme export/import). Drives the real binary in a pty, cwd = a
temp dir so the repo stays clean. RE-HOMED v3.1.96 and DIETED: the
old drive slept on fixed timers (35 s of mostly waiting); the first
diet tried quiescence and was taught by the auto-hosted game — its
render flood NEVER lets the pty go quiet, so every cap burned and a
half-booted IDE ate the first command. The diet that works: WAIT FOR
THE ANSWER — poll in slices until the expected receipt appears in the
post-enter buffer, capped. The machine decides when it's done; the
probe stops guessing.

Driving law learned by this probe: in the IDE, ':' types into the doc —
commands run from PLAY mode: esc first, then the bar; every verb takes
the stage back. The starter auto-hosts, so the host keeps the doc's own
file current — a plain :w is a storyless save by design; the census
speaks on a save-as to a fresh name (the honest birth line)."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.96): dieted from 35 s of fixed sleeps to
# answer-driven waits. Canonical law pins: probes/*_probe.py, gate 8.
import os, pty, select, time, sys, shutil, re

REPO = _HOME
BIN = os.path.join(REPO, "native", "build", "dxn3-native")
WORK = "/tmp/dxn3_door_e2e"

shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK)

pid, fd = pty.fork()
if pid == 0:
    os.chdir(WORK)
    os.environ["TERM"] = "xterm-256color"
    os.execv(BIN, [BIN])
    os._exit(1)

buf = b""
def drainf(seconds):
    """read everything the pty says for a fixed window (the auto-hosted
    game floods the pipe continuously — there is no silence to wait
    for once play mode starts)."""
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

in_ide = True   # the boot stage is the editor
def cmd(line, until=None, cap=2.5, takes_stage=True):
    """esc to play (only when the IDE holds the stage — esc in play
    QUITS), ':' opens the bar (its own frame), the verb typed in one
    honest burst, enter. Then WAIT FOR THE ANSWER: slices until the
    `until` predicate matches the post-enter bytes, or `cap` — the
    receipt rides a real host re-boot, the flood never sleeps, and
    the answer arrives when it arrives."""
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

pins = []
def pin(name, cond, detail=""):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""))

def receipts(w):
    return [m.group(0).decode(errors="replace")
            for m in re.finditer(rb'engine:[^\x1b\r]{0,120}', w)]

t0 = time.time()
alive = drainf(3.0)
pin("boot alive", alive)

# ---- 1. the birth census: a save-as to a fresh name speaks (+N) -------
w = cmd("w probe_a.py", until=lambda b: b"saved as probe_a.py" in b)
rec = [r for r in receipts(w) if "saved as probe_a.py" in r]
pin("save-as receipt speaks the birth census",
    any(re.search(r"saved as probe_a\.py  \(\+\d+ ~\d+ -\d+\)", r)
        for r in rec))
pin("the fresh name keeps no .bak (no past)",
    any("(.bak kept)" not in r for r in rec))

# ---- 2. :journal remembers the save ------------------------------------
w = cmd("journal", until=lambda b: b"probe_a.py" in b)
jrn = receipts(w) + [m.group(0).decode(errors="replace")
                     for m in re.finditer(rb'\+\d+ ~\d+ -\d+[^\x1b\r]{0,80}', w)]
pin("journal lists the save with the census voice",
    re.search(rb'\+\d+ ~\d+ -\d+\s+probe_a\.py', w) is not None)

# ---- 3. a storyless save: the census called same, no counts spoken ----
w = cmd("w probe_a.py", until=lambda b: b"saved as probe_a.py" in b)
rec = [r for r in receipts(w) if "saved as probe_a.py" in r]
pin("storyless save wears no counts",
    any("(+" not in r for r in rec))
w = cmd("journal", until=lambda b: b"the last" in b)
pin("the storyless save took no journal line",
    b"the last 1 save the disk heard" in w)

# ---- 4. the wardrobe's door: export ------------------------------------
w = cmd("theme export", until=lambda b: b"dxn:226,232,240" in b)
pin("bare export speaks the worn coat's line",
    "dxn's line" in "".join(receipts(w)) and
    re.search(rb'dxn:226,232,240:96,104,126:250,204,21:167,139,250:16,12,30:30,22,52', w)
    is not None)
COAT = os.path.join(WORK, "coat.txt")
if os.path.exists(COAT): os.remove(COAT)
w = cmd("theme export nord " + COAT,
        until=lambda b: b"coat nord appended" in b)
pin("export with a path appends and reports",
    any("coat nord appended to" in r for r in receipts(w)))
line = open(COAT).read().strip() if os.path.exists(COAT) else ""
pin("the coat's line is the seven-field truth",
    line.startswith("nord:236,239,244:97,110,136:"))

# ---- 5. the door inward: import ----------------------------------------
w = cmd("theme import " + COAT,
        until=lambda b: b"the wardrobe waits" in b)
pin("import of shipped names is honest zero",
    any("the wardrobe waits" in r for r in receipts(w)))
w = cmd("theme export nope", until=lambda b: b"no such theme: nope" in b)
pin("a ghost coat is refused at the door",
    any("no such theme: nope" in r for r in receipts(w)))
w = cmd("theme nord extra", until=lambda b: b"one coat at a time" in b,
        takes_stage=False)
pin("the wearing law still refuses two words",
    b"one coat at a time" in w)
w = cmd("theme import",
        until=lambda b: b"waits" in b or b"imported" in b
        or b"no HOME" in b)
pin("default import from the wardrobe's home is honest",
    any("waits" in r or "imported" in r or "no HOME" in r
        for r in receipts(w)))

# ---- 6. the ledger's keepsake: :journal survives the restart ----------
# (v3.1.105) the journal is the PROJECT's memory: one line per save the
# disk heard, kept in .dxn3-journal at the project root. Quit the
# studio, start a FRESH binary in the same cwd, ask :journal — the
# session's save must still be listed, loaded from the ledger file.
JFILE = os.path.join(WORK, ".dxn3-journal")
try: os.kill(pid, 15)
except Exception: pass
drainf(0.5)
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
pin("the ledger file exists at the project root", os.path.exists(JFILE),
    "no .dxn3-journal")
ledger_lines = (open(JFILE).read().splitlines()
                if os.path.exists(JFILE) else [])
pin("the ledger carries the session's save with its census",
    any("probe_a.py" in ln and ln.startswith("+") for ln in ledger_lines),
    str(ledger_lines)[:120])

pid, fd = pty.fork()
if pid == 0:
    os.chdir(WORK)
    os.environ["TERM"] = "xterm-256color"
    os.execv(BIN, [BIN])
    os._exit(1)
buf = b""
in_ide = True
drainf(2.0)
w = cmd("journal", until=lambda b: b"probe_a.py" in b, takes_stage=True)
pin("a fresh session's :journal remembers the last night's save",
    re.search(rb'\+\d+ ~\d+ -\d+\s+probe_a\.py', w) is not None)
pin("the restarted studio speaks the ledger's voice",
    b"the disk heard" in w, w[:100])

# ---- 7. the clear verb's gate pin (the R39 debt, collected) ------------
# The R39 attempt died on a stale flag: since :journal clear shipped, the
# journal verb TAKES THE STAGE (takeStage in the verb's branch) — the old
# takes_stage=False left the probe's shadow believing play mode held the
# wheel, so the next ':' typed into the DOC, no bar opened, no receipt
# came. A probe's state machine must walk with the engine's.
w = cmd("journal clear", until=lambda b: b"forgiven" in b)
pin("the clear speaks the count it forgave",
    b"the journal forgets" in w and b"1 line forgiven" in w, w[:120])
pin("the disk's ledger is blank after the clear",
    os.path.exists(JFILE) and open(JFILE).read() == "")
w = cmd("journal", until=lambda b: b"the journal is blank" in b)
pin("the bare journal confesses the blank ledger",
    b"the journal is blank" in w, w[:120])
w = cmd("journal junk", until=lambda b: b"usage: :journal" in b
        or b"knows only clear" in b, takes_stage=False)
pin("a story is refused at the clear's door",
    b"usage: :journal" in w or b"knows only clear" in w, w[:120])

# ---- cleanup -----------------------------------------------------------
try: os.kill(pid, 15)
except Exception: pass
drainf(0.5)
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
shutil.rmtree(WORK, ignore_errors=True)

fails = [n for n, ok in pins if not ok]
print(f"\nide_door_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
