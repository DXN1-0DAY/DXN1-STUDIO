# probes/_harness.py — the fleet's shared wire harness.
#
# THE BUFFER LAW (v3.1.103): select() on the fd + readline() on a
# buffered file object DEADLOCK the moment chatter and a frame share
# one read chunk — the frame sits in Python's own buffer while select
# waits for fd data that will never come until the child sees the
# next tick, and the child will never see the next tick because the
# probe is still waiting for the frame. Both sides wait; the pin
# dies of thirst. The harness reads RAW (os.read) and splits lines
# itself, so everything the child said is visible to the splitter
# immediately. ast_lives_probe died of this exactly at its death
# ticks (the respawn chatter + the payment frame in one chunk).
import json, os, select, time


class Wire:
    """one child on the wire: raw reads, own line buffer, generous waits."""

    def __init__(self, proc, timeout=15.0):
        self.p = proc
        self.timeout = timeout
        self.buf = b""

    def send(self, obj):
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def read(self, timeout=None):
        """one JSON packet (or None on a stall kept generous / EOF).
        Chatter (the game's prints) is skipped in place, never allowed
        to steal a frame — the metronome law at the read end."""
        timeout = self.timeout if timeout is None else timeout
        end = time.time() + timeout
        while True:
            if b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                try:
                    return json.loads(line)
                except Exception:
                    continue          # chatter — keep reading
            r, _, _ = select.select([self.p.stdout], [], [], 0.05)
            if r:
                chunk = os.read(self.p.stdout.fileno(), 65536)
                if not chunk:
                    return None       # EOF — the child is gone
                self.buf += chunk
            elif time.time() > end:
                return None           # the honest stall, waited out

    def frame(self, dt=0.05, keys=None, chars="", hits=None):
        """one honest tick, one honest frame back."""
        self.send({"t": "tick", "dt": dt,
                   "keys": {k: True for k in (keys or [])},
                   "chars": chars, "hits": hits or []})
        while True:
            f = self.read()
            if f is None:
                raise AssertionError("no frame — child stalled")
            if f.get("t") == "frame":
                return {e["name"]: e for e in f["set"]}, f
