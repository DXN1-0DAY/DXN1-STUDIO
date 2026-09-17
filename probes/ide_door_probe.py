#!/usr/bin/env python3
"""R31 probe: the save speaks the census (:w/save-as receipt wears
(+added ~changed -removed), :journal remembers) and the wardrobe's
door (:theme export/import). Drives the real binary in a pty, cwd = a
temp dir so the repo stays clean.

Driving law learned by this probe: in the IDE, ':' types into the doc —
commands run from PLAY mode: esc first, then the bar; every verb takes
the stage back. The starter auto-hosts, so the host keeps the doc's own
file current — a plain :w is a storyless save by design; the census
speaks on a save-as to a fresh name (the honest birth line)."""
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
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
def drain(seconds):
    global buf
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            try: chunk = os.read(fd, 65536)
            except OSError: return False
            if not chunk: return False
            buf += chunk
    return True

def send(s):
    os.write(fd, s if isinstance(s, bytes) else s.encode())

in_ide = True   # the boot stage is the editor
def cmd(line, wait=1.2, takes_stage=True):
    """esc to play (only when the IDE holds the stage — esc in play
    QUITS), ':' opens the bar (its own frame), the verb typed char by
    char, enter. Verbs take the stage back; a parse-refused command
    does not (it never reaches a handler) — the caller says which."""
    global buf, in_ide
    buf = b""
    if in_ide:
        send(b"\x1b"); drain(0.5)
        buf = b""
    send(":"); drain(0.35)
    for ch in line:
        send(ch); drain(0.05)
    drain(0.25)
    send("\r")
    drain(wait)
    in_ide = takes_stage
    return buf

pins = []
def pin(name, cond):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)

def receipts(w):
    return [m.group(0).decode(errors="replace")
            for m in re.finditer(rb'engine:[^\x1b\r]{0,120}', w)]

alive = drain(3.0)
pin("boot alive", alive)

# ---- 1. the birth census: a save-as to a fresh name speaks (+N) -------
w = cmd("w probe_a.py")
rec = [r for r in receipts(w) if "saved as probe_a.py" in r]
pin("save-as receipt speaks the birth census",
    any(re.search(r"saved as probe_a\.py  \(\+\d+ ~\d+ -\d+\)", r)
        for r in rec))
pin("the fresh name keeps no .bak (no past)",
    any("(.bak kept)" not in r for r in rec))

# ---- 2. :journal remembers the save ------------------------------------
w = cmd("journal")
jrn = receipts(w) + [m.group(0).decode(errors="replace")
                     for m in re.finditer(rb'\+\d+ ~\d+ -\d+[^\x1b\r]{0,80}', w)]
pin("journal lists the save with the census voice",
    re.search(rb'\+\d+ ~\d+ -\d+\s+probe_a\.py', w) is not None)

# ---- 3. a storyless save: the census called same, no counts spoken ----
w = cmd("w probe_a.py")
rec = [r for r in receipts(w) if "saved as probe_a.py" in r]
pin("storyless save wears no counts",
    any("(+" not in r for r in rec))
w = cmd("journal")
pin("the storyless save took no journal line",
    b"the last 1 save the disk heard" in w)

# ---- 4. the wardrobe's door: export ------------------------------------
w = cmd("theme export")
pin("bare export speaks the worn coat's line",
    "dxn's line" in "".join(receipts(w)) and
    re.search(rb'dxn:226,232,240:96,104,126:250,204,21:167,139,250:16,12,30:30,22,52', w)
    is not None)
COAT = os.path.join(WORK, "coat.txt")
if os.path.exists(COAT): os.remove(COAT)
w = cmd("theme export nord " + COAT)
pin("export with a path appends and reports",
    any("coat nord appended to" in r for r in receipts(w)))
line = open(COAT).read().strip() if os.path.exists(COAT) else ""
pin("the coat's line is the seven-field truth",
    line.startswith("nord:236,239,244:97,110,136:"))

# ---- 5. the door inward: import ----------------------------------------
w = cmd("theme import " + COAT)
pin("import of shipped names is honest zero",
    any("the wardrobe waits" in r for r in receipts(w)))
w = cmd("theme export nope")
pin("a ghost coat is refused at the door",
    any("no such theme: nope" in r for r in receipts(w)))
w = cmd("theme nord extra", takes_stage=False)
pin("the wearing law still refuses two words",
    b"one coat at a time" in w)
w = cmd("theme import")
pin("default import from the wardrobe's home is honest",
    any("waits" in r or "imported" in r or "no HOME" in r
        for r in receipts(w)))

# ---- cleanup -----------------------------------------------------------
try: os.kill(pid, 15)
except Exception: pass
drain(0.5)
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
shutil.rmtree(WORK, ignore_errors=True)

fails = [n for n, ok in pins if not ok]
print(f"\nide_door_probe: {len(pins)-len(fails)}/{len(pins)} pins green")
sys.exit(1 if fails else 0)
