#!/usr/bin/env python3
"""THE SDK'S CONFESSION — the host's lifecycle on the wire (v3.1.118).

The studio hosts a child game in any language (the sdk/ protocol), and
until now its lifecycle spoke only to the console rail — `engine:
hosting ...`, `engine: built N entities`, `engine: your game exited` —
while the event wire, the machine's own mouth, stayed silent. The
words exist on the wire now (`wire: hosting`, `wire: built N entities`,
`wire: host exited (code N)`), and this probe pins them off the REAL
wire: the engine boots a copy of sdk/examples/background.py, ctrl+R
runs it, and the wire must name the host (interpreter AND script),
count the child's scene honestly, and carry the exit's code when the
child is slain. The probes read the wire, never the paint — the rail's
half of each confession is rendered paint, and the paint can lie.

(The script runs from a /tmp copy: ctrl+R SAVES before it runs — the
engine's honest law — and the probe must not write into the tree.)

The R41 debt, collected: the sdk/ examples confess their own shell
words in kind, pinned by gate 8 like every other word."""
import os, pty, re, select, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(REPO, "native", "build", "dxn3-native")
SRC = os.path.join(REPO, "sdk", "examples", "background.py")

CAP = 30.0
tfd, TRACE = tempfile.mkstemp(prefix="dxn3_sdk_wire_", suffix=".trace")
os.close(tfd)

# the child's copy: outside the tree, so the engine's save-before-run
# law writes its normalization where the repo cannot hear it.
# THE TRUNCATOR LAW (R45, caught live): this copy once read
#   with open(SRC, "w") as f: f.write(open(SRC, "r").read())
# — the "w" open TRUNCATED THE REPO'S OWN EXAMPLE to zero before the
# read, every gates run sawed the file to 0 bytes, and gate 6's next
# run failed on the corpse while the pins above still passed (the
# engine's default stage also builds 3 entities — vacuous green).
# The copy reads SRC first, then writes the tmp file; and the source's
# own pin below fails LOUDLY if the example is ever a corpse again.
with open(SRC, "r") as f:
    src_text = f.read()
tmpdir = tempfile.mkdtemp(prefix="dxn3_sdk_wire_run_")
SCRIPT = os.path.join(tmpdir, "background.py")
with open(SCRIPT, "w") as f:
    f.write(src_text)
CHILD_NEEDLE = "python3 " + SCRIPT      # matches the child, never the
                                        # engine (whose argv says --scene)

DIRTY0 = os.popen(f"git -C {REPO!r} status --porcelain").read()

pid, fd = pty.fork()
if pid == 0:
    os.chdir(REPO)
    os.environ["TERM"] = "xterm-256color"
    os.environ["DXN3_TRACE"] = TRACE
    os.execv(BIN, [BIN, "--scene", SCRIPT])
    os._exit(1)

buf = b""
def drainf(seconds):
    """read EVERYTHING the pty says in the window — the flood never
    backs up, the child never stalls on a full pipe"""
    global buf
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [],
                                max(0.001, min(0.005, end - time.time())))
        if r:
            try: chunk = os.read(fd, 1 << 16)
            except OSError: return False
            if not chunk: return False
            buf += chunk
    return True

t0 = time.time()
alive = drainf(1.5)
os.write(fd, b"\x12")           # ctrl+R — the IDE's run: save, host, live
drainf(4.0)                     # the host spawns; the child's scene lands

def trace_text():
    try:
        with open(TRACE, "rb") as f: return f.read()
    except OSError:
        return b""

tr = trace_text()

# the child is slain so the exit's receipt lands (an honest kill: the
# engine confesses whatever code the child kept). The needle matches
# the CHILD's argv only — the engine's own argv says --scene, and the
# probe that kills its own engine learns nothing.
subprocess.run(["pkill", "-f", CHILD_NEEDLE], capture_output=True)
drainf(2.0)
tr = trace_text()

pins = []
def pin(name, cond, detail=""):
    pins.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""))

pin("boot alive (the IDE opens the script; the studio renders)", alive)
pin("the source example is real (the hello-world lives; if this fails, "
    "restore: git show 301d388:sdk/examples/background.py)",
    len(src_text) > 100, f"{len(src_text)} bytes")
wm = re.search(rb"EVENT wire: hosting ([^\n]*)", tr)
pin("the wire confesses the host: 'wire: hosting python3 <script>'",
    wm is not None and b"python3" in wm.group(1)
    and b"background.py" in wm.group(1),
    wm.group(1)[:60] if wm else "absent")
mb = re.search(rb"EVENT wire: built (\d+) entities", tr)
pin("the wire confesses the child's scene: 'wire: built N entities' "
    "(N>=3: ground, moon, stars)",
    mb is not None and int(mb.group(1)) >= 3,
    mb.group(1).decode() if mb else "absent")
pin("the child's prints never masquerade on the wire (the console is "
    "their only mouth — the refusals' law, in kind; the paint carries "
    "what it carries and the probes trust it not)",
    b"EVENT a background, from" not in tr and
    b"EVENT wire: print" not in tr)
pin("the exit's receipt: 'wire: host exited (code N)' after the child "
    "is slain",
    re.search(rb"EVENT wire: host exited \(code -?\d+\)", tr) is not None)
pin("the clock stayed honest through the host's whole life (pi=0)",
    b"pi=0.00" in tr and b"pi=0.01" not in tr and b"pi=0.1" not in tr)
pin("the flood keeps flowing after the confession", drainf(0.6))

try: os.kill(pid, 15)
except Exception: pass
drainf(0.4)
try: os.close(fd)
except Exception: pass
try: os.waitpid(pid, 0)
except Exception: pass
if os.environ.get("DXN3_SDK_DEBUG"):
    os.system(f"cp {TRACE} /tmp/sdk_wire_trace.txt")
try: os.unlink(TRACE)
except Exception: pass
subprocess.run(["rm", "-rf", tmpdir], capture_output=True)

dirty = os.popen(f"git -C {REPO!r} status --porcelain").read()
pin("the probe wrote nothing (tree snapshot unchanged across the run)",
    dirty == DIRTY0, dirty[:80])

fails = [n for n, ok in pins if not ok]
print(f"\nsdk_wire_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
