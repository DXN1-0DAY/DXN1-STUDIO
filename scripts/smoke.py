#!/usr/bin/env python3
"""The studio's smoke: drives the REAL binary through a real pty.

Why this file is COMMITTED: the smoke used to live outside the repo and
was lost between sessions (the same failure class as the v3.0.32 ssh
shim — a lost artifact costs a whole round to rebuild). It lives here
now, so every future round can run it and extend it.

The laws it encodes (each one cost a session to learn):
  MODE LAW    — the studio boots in the IDE; ESC leaves the IDE for
                play; a bare ESC in PLAY QUITS. The bar only opens from
                play (':' in the IDE types a ':'). So opening the bar is
                ALWAYS: ESC (ide→play), a real gap, then ':'.
  COALESCING  — ESC and the next key must not land in one pty read:
                pollKeys would see esc + typed ':' in one frame (the
                v3.0.28 corruption). Every mode switch sleeps ≥150ms.
  SGR LAW     — the renderer repaints the whole screen every frame:
                ESC[H then rows×cols cells (SGR 38;2/48;2, glyphs,
                \\r\\n between rows, ESC[0m at the end). Text row =
                doc line + 1 (0-based); SGR col = doc col + 5 at
                hcol=0 with the 4-col gutter (1-based). A terminal of
                100 cols has no minimap (mapOn needs ≥110).
  TRANSITIONS — take the LAST COMPLETE frame in the capture (the first
                frame after a key may still paint the previous state).
  HYGIENE     — never clear the capture between drain and read; only
                trim the ancient head (2MB tail holds ~60 frames).

Usage: python3 scripts/smoke.py [--bin native/build/dxn3-native]
Exit 0 only when every check is green.
"""
import os
import pty
import sys
import time
import signal
import struct
import termios
import fcntl
import select
import threading

ROWS, COLS = 32, 100
RAIL_BG = (10, 7, 18)
PANE_BG = (16, 12, 30)
CURSOR_BG = (167, 139, 250)
AMBER = (250, 204, 21)
GUTTER = 4                      # <1000 lines

ESC = "\x1b"
F2 = ESC + "[15~"
F2_CTRL = ESC + "[15;5~"
F2_SHIFT = ESC + "[15;2~"
CTRL_END = ESC + "[1;5F"
UP = ESC + "[A"
S_UP = ESC + "[1;2A"
S_DOWN = ESC + "[1;2B"
S_RIGHT = ESC + "[1;2C"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    mark = "ok  " if cond else "FAIL"
    print(f"   {mark} {name}" + (f"  [{detail}]" if detail and not cond else ""))
    return bool(cond)


class Screen:
    """A parsed frame: (glyph, fg, bg) per cell."""

    def __init__(self, grid):
        self.grid = grid

    def text(self, row):
        return "".join(c[0] for c in self.grid[row])

    def cell(self, row, col):
        return self.grid[row][col]

    def bg_at(self, row, col):
        return self.grid[row][col][2]

    def fg_at(self, row, col):
        return self.grid[row][col][1]

    def find(self, sub):
        for r in range(ROWS):
            t = self.text(r)
            i = t.find(sub)
            if i >= 0:
                return (r, i)
        return None


def parse_frame(b):
    grid = [[(" ", None, None) for _ in range(COLS)] for _ in range(ROWS)]
    fg = bg = None
    r = c = 0
    i, n = 0, len(b)
    while i < n:
        ch = b[i]
        if ch == 0x1B:
            if i + 1 < n and b[i + 1:i + 2] == b"[":
                j = i + 2
                while j < n and not (0x40 <= b[j] <= 0x7E):
                    j += 1
                if j >= n:
                    break
                seq, fin = b[i + 2:j], b[j:j + 1]
                if fin == b"m":
                    parts = seq.decode("ascii", "ignore").split(";")
                    if seq == b"0":
                        fg = bg = None
                    k = 0
                    while k < len(parts):
                        if parts[k] == "38" and k + 4 < len(parts) and \
                                parts[k + 1] == "2":
                            fg = (int(parts[k + 2]), int(parts[k + 3]),
                                  int(parts[k + 4]))
                            k += 4
                        elif parts[k] == "48" and k + 4 < len(parts) and \
                                parts[k + 1] == "2":
                            bg = (int(parts[k + 2]), int(parts[k + 3]),
                                  int(parts[k + 4]))
                            k += 4
                        k += 1
                # H / J / K / ?25l / mouse responses: full repaints — ignore
                i = j + 1
            elif i + 1 < n and b[i + 1:i + 2] == b"]":
                bel = b.find(b"\x07", i)
                st = b.find(b"\x1b\\", i)
                ends = [x for x in (bel, st) if x != -1]
                if not ends:
                    break
                end = min(ends)
                i = end + (1 if end == bel else 2)
            else:
                i += 2
            continue
        if ch == 0x0D:
            c = 0
            i += 1
            continue
        if ch == 0x0A:
            r += 1
            c = 0
            i += 1
            continue
        if ch < 0x80:
            ln = 1
        elif ch >= 0xF0:
            ln = 4
        elif ch >= 0xE0:
            ln = 3
        elif ch >= 0xC0:
            ln = 2
        else:
            i += 1
            continue
        glyph = b[i:i + ln].decode("utf-8", "replace")
        if 0 <= r < ROWS and 0 <= c < COLS:
            grid[r][c] = (glyph, fg, bg)
        c += 1
        i += ln
    return Screen(grid)


class Studio:
    def __init__(self, binary):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            env = dict(os.environ)
            env["TERM"] = "xterm-256color"
            env["LANG"] = "C.UTF-8"
            try:
                os.execvpe(binary, [binary], env)
            except Exception:
                os._exit(127)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                    struct.pack("HHHH", ROWS, COLS, 0, 0))
        self.raw = bytearray()
        self.dead = False
        self.lock = threading.Lock()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()
        self.exit_code = None

    def _read_loop(self):
        while True:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.05)
                if not r:
                    continue
                data = os.read(self.fd, 65536)
            except OSError:
                break
            if not data:
                break
            with self.lock:
                self.raw += data
                if len(self.raw) > 2_000_000:      # keep the last ~60 frames
                    del self.raw[:len(self.raw) - 2_000_000]
        self.dead = True

    def send(self, s):
        os.write(self.fd, s.encode("utf-8"))

    def settle(self, t=0.3):
        time.sleep(t)
        return self.screen()

    def screen(self):
        with self.lock:
            buf = bytes(self.raw)
        chunks = buf.split(b"\x1b[H\x1b[?25l")
        for chunk in reversed(chunks[1:]):
            if chunk.rstrip().endswith(b"\x1b[0m"):
                return parse_frame(chunk)
        return None

    def open_bar(self, stage):
        """The bar only opens from play. From the IDE: ESC first (a real
        gap — never coalesce ESC with the next key), then ':'."""
        if stage == "ide":
            self.send(ESC)
            time.sleep(0.18)
        self.send(":")
        time.sleep(0.28)
        return self.screen()

    def run_verb(self, verb, stage):
        """Open the bar, type the verb, enter. Returns (final, bar_frame).
        Stage AFTER the verb: IDE verbs take the stage; refusals stay
        in play. The caller knows which."""
        bar = self.open_bar(stage)
        self.send(verb)
        time.sleep(0.18)
        self.send("\r")
        time.sleep(0.35)
        return self.screen(), bar

    def wait_exit(self, timeout=4.0):
        end = time.time() + timeout
        while time.time() < end and not self.dead:
            time.sleep(0.05)
        if self.dead:
            try:
                _, status = os.waitpid(self.pid, os.WNOHANG)
                if os.WIFEXITED(status):
                    self.exit_code = os.WEXITSTATUS(status)
            except ChildProcessError:
                self.exit_code = -1
        return self.dead

    def close(self):
        if not self.dead:
            try:
                os.kill(self.pid, signal.SIGKILL)
                os.waitpid(self.pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass


def main():
    binary = "native/build/dxn3-native"
    if "--bin" in sys.argv:
        binary = sys.argv[sys.argv.index("--bin") + 1]
    if not os.path.exists(binary):
        print(f"smoke: {binary} missing — run make -C native first")
        return 2

    s = Studio(binary)
    try:
        # ── 0. boot: the studio opens loud ────────────────────────────
        print("── 0. boot — the studio opens loud")
        # THE SPLASH LAW: the studio opens on an emblem and eats the
        # first keypress (any key ends it). Wait it out — 1.6s + slack —
        # before touching the keyboard, or the first ESC vanishes and
        # the ':' after it types into the document (lesson 4 again).
        scr = s.settle(2.2)
        if not check("a frame arrived", scr is not None):
            return finish(s)
        check("the header brands the studio",
              scr.find("DXN1 STUDIO — ENGINE") is not None)
        check("the starter document is open",
              scr.find("untitled.py") is not None)
        check("the gutter speaks line 1",
              scr.text(1)[:GUTTER] == " 1 "[:GUTTER] or
              scr.text(1)[:GUTTER].strip() == "1",
              repr(scr.text(1)[:8]))
        check("the starter's first line rides row 1",
              "# DXN1 STUDIO" in scr.text(1), repr(scr.text(1)[:40]))
        check("the boot's live refresh — the starter ran and built",
              "engine: built" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:40]))
        check("the hint rail offers the way out",
              "ctrl+r run" in scr.text(ROWS - 1))
        check("the pane breathes pane-color",
              scr.bg_at(4, 20) == PANE_BG, repr(scr.bg_at(4, 20)))

        # ── 1. zen: the quiet ─────────────────────────────────────────
        print("── 1. :zen — the rail rests, the body breathes")
        _, bar = s.run_verb("zen", "ide")
        check("the bar opens with the ':' prompt",
              bar is not None and bar.text(ROWS - 1).startswith(":"),
              repr(bar.text(ROWS - 1)[:20]) if bar else "no frame")
        scr = s.settle(0.25)
        check("the quiet says its name in the header",
              "· zen" in scr.text(0), repr(scr.text(0)[-30:]))
        check("the body breathes — doc line 30 rides the old rail",
              "def on_hit" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:40]))
        check("the body breathes — doc line 31 rides the old hint row",
              "global score" in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:40]))
        check("the zen receipt gathers SILENTLY (never painted)",
              "the rail rests" not in scr.text(ROWS - 2))
        # the searchlight keeps its row while it is up
        s.send("\x06")                            # ctrl+f
        scr = s.settle(0.3)
        check("zen keeps the searchlight honest (its own row)",
              "/ find: " in scr.text(ROWS - 1), repr(scr.text(ROWS - 1)[:40]))
        s.send("print")
        scr = s.settle(0.3)
        check("the searchlight counts its hits in zen",
              "1/1" in scr.text(ROWS - 1), repr(scr.text(ROWS - 1)[:50]))
        s.send(ESC)                               # the searchlight rests
        scr = s.settle(0.3)
        check("esc hands the row back to the body",
              "global score" in scr.text(ROWS - 1))
        # the pointer in zen: the rail's rows now belong to the body
        s.send(ESC + "[<0;6;31M" + ESC + "[<0;6;31m")   # press+release SGR
        scr = s.settle(0.35)
        check("a click on the old rail row lands in the doc (zen geometry)",
              scr.cell(ROWS - 2, GUTTER + 1)[2] == CURSOR_BG,
              repr(scr.cell(ROWS - 2, GUTTER + 1)))
        # wake: :zen again
        scr, _ = s.run_verb("zen", "ide")
        check("the rail is back — its receipt speaks",
              "the rail is back" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:40]))
        check("the hint rail is back",
              "ctrl+r run" in scr.text(ROWS - 1))
        check("the header no longer says zen",
              "· zen" not in scr.text(0))

        # ── 2. typing + the live auto-run ─────────────────────────────
        print("── 2. typing — the doc dirties, the auto-run hosts")
        s.send(CTRL_END)
        s.settle(0.25)
        s.send("\r")                    # enter alone in its frame: a flag
        time.sleep(0.15)                # key can only fire once per frame
        s.send("# smoke was here")      # typed accumulates — a paste
        scr = s.settle(0.4)
        check("typing dirties the header",
              "●" in scr.text(0), repr(scr.text(0)[-30:]))
        check("the typed line lands at the doc's end",
              "# smoke was here" in scr.text(ROWS - 3),
              repr(scr.text(ROWS - 3)[:40]))
        scr = s.settle(1.3)                       # idle > 0.6s → auto-run
        check("the auto-run hosts the game",
              "engine: built" in scr.text(ROWS - 2) or
              "engine: hosting" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:50]))
        check("the header announces LIVE",
              "LIVE" in scr.text(0), repr(scr.text(0)[-30:]))
        s.settle(0.8)                             # let the host settle

        # ── 3. pins: plant, list, leap ────────────────────────────────
        print("── 3. pins — the hand leaps back")
        s.send(F2_CTRL)                           # ctrl+F2 plants on line 40
        scr = s.settle(0.3)
        check("a pin plants its diamond in the gutter",
              scr.cell(ROWS - 3, GUTTER - 1)[0] == "◆",
              repr(scr.cell(ROWS - 3, GUTTER - 1)))
        check("the header counts the pin at a glance",
              "pins 1" in scr.text(0), repr(scr.text(0)[-30:]))
        check("the pinned gutter number burns amber",
              scr.fg_at(ROWS - 3, 1) == AMBER, repr(scr.fg_at(ROWS - 3, 1)))
        for _ in range(3):                # the hand walks up — one arrow
            s.send(UP)                    # per frame: a coalesced burst is
            time.sleep(0.15)              # ONE flag, not three moves
        s.settle(0.3)
        s.send(F2_CTRL)                           # plant on line 37
        scr = s.settle(0.3)
        check("a second pin plants where the hand stands",
              scr.cell(ROWS - 6, GUTTER - 1)[0] == "◆",
              repr(scr.cell(ROWS - 6, GUTTER - 1)))
        check("the header counts both pins",
              "pins 2" in scr.text(0), repr(scr.text(0)[-30:]))
        # the pins whisper: the bar completes :bm as you type
        bar = s.open_bar("ide")
        s.send("bm ")
        scr = s.settle(0.3)
        check("a bare :bm whispers every pin as you type",
              "1) Ln 37 · 2) Ln 40" in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:50]))
        s.send("2")
        scr = s.settle(0.3)
        check("a typed number narrows the choir",
              "2) Ln 40" in scr.text(ROWS - 1) and
              "1) Ln 37" not in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:50]))
        s.send(ESC)                               # the bar rests
        s.settle(0.3)                             # stage: play
        # the shelf whispers: :snip's names carry their descriptions
        bar = s.open_bar("play")
        s.send("snip ")
        scr = s.settle(0.3)
        check("a bare :snip whispers the shelf, described",
              "fn — a named function" in scr.text(ROWS - 1) and
              "tick — the every-frame hook" in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:60]))
        s.send("ke")
        scr = s.settle(0.3)
        check("a typed prefix narrows the shelf, description riding",
              scr.text(ROWS - 1).find("key — the keypress hook") > 0 and
              "fn" not in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:60]))
        s.send(ESC)                               # the bar rests
        s.settle(0.3)                             # stage: play
        # the gallery whispers: the bar knows the starters before you do
        bar = s.open_bar("play")
        s.send("template ")
        scr = s.settle(0.3)
        check("a bare :template whispers the whole gallery",
              "blank · shooter · cards" in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:60]))
        s.send("b")
        scr = s.settle(0.3)
        check("a typed prefix narrows the gallery",
              "blank · background · bounce" in scr.text(ROWS - 1) and
              "shooter" not in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:60]))
        s.send(ESC)                               # the bar rests
        s.settle(0.3)                             # stage: play
        scr, _ = s.run_verb("marks", "play")
        check(":marks lists both pins by line (sorted, not planted)",
              "1) Ln 37" in scr.text(ROWS - 2) and "2) Ln 40" in
              scr.text(ROWS - 2), repr(scr.text(ROWS - 2)[:60]))
        scr, _ = s.run_verb("bm", "ide")
        check("a bare :bm leaps to the next pin (wrapping)",
              "leaps to the pin at line 40" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        s.send(F2_SHIFT)                          # shift+F2 walks back
        scr = s.settle(0.3)
        check("shift+F2 walks back to the pin above",
              "leaps to the pin at line 37" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))

        # ── 4. the bar's honest refusals ──────────────────────────────
        print("── 4. refusals — the bar names the way out")
        scr, _ = s.run_verb("zen x", "ide")
        check(":zen with an argument refuses by name",
              "takes no argument" in scr.text(ROWS - 1),
              repr(scr.text(ROWS - 1)[:60]))

        # ── 5. :sort — the ordering, end to end ───────────────────────
        print("── 5. :sort — two lines order themselves")
        # stage is play after the refusal; the bar opens straight over it
        scr, _ = s.run_verb("marks", "play")      # a stage-taking verb
        s.send(CTRL_END)
        s.settle(0.25)
        for text in ("\r", "zz", "\r", "aa"):     # every step its own frame
            s.send(text)                          # (flags fire once per read)
            time.sleep(0.15)
        s.settle(0.4)
        s.send(S_UP)                              # select the last two lines
        s.settle(0.25)
        scr, _ = s.run_verb("sort", "ide")
        check(":sort names its count",
              "sorted 2 lines" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        check("the lines landed in order (aa before zz)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "aa" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "zz",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))
        # the mirror: :rsort flips the same bed back, Z before A
        # (the hand rests at the block's HEAD after a sort — so the
        # same bed is shift+DOWN, not up)
        s.send(S_DOWN)
        s.settle(0.25)
        scr, _ = s.run_verb("rsort", "ide")
        check(":rsort speaks its descending law",
              "Z before A" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        check("the lines landed Z-ward (zz before aa again)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "zz" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "aa",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))

        # ── 5b. the jump — :goto rides relative to the hand ──────────
        print("── 5b. the jump — :goto +N rides from where you stand")
        scr, _ = s.run_verb("goto 5", "ide")
        check("the absolute jump speaks its line",
              "jumped to line 5" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        scr, _ = s.run_verb("goto +3", "ide")
        check("the relative jump rides and names the landing",
              "jumped down 3 — now at line 8" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        scr, _ = s.run_verb("goto -2", "ide")
        check("the ride works up too",
              "jumped up 2 — now at line 6" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))

        # ── 6. the case — the selection changes its voice ─────────────
        print("── 6. the case — upper shouts, lower whispers")
        scr, _ = s.run_verb("goto 5", "ide")      # the hand: line 5, col 0
        s.settle(0.25)
        for _ in range(5):                        # walk to "dxn3"'s d
            s.send(ESC + "[C")                    # one arrow per frame
            time.sleep(0.13)
        s.settle(0.2)
        for _ in range(4):                        # select "dxn3"
            s.send(S_RIGHT)
            time.sleep(0.13)
        s.settle(0.25)
        scr, _ = s.run_verb("upper", "ide")
        check("the selection shouts (dxn3 -> DXN3)",
              "from DXN3 import *" in scr.text(5),
              repr(scr.text(5)[:40]))
        for _ in range(4):                        # re-select the shout
            s.send(S_RIGHT)
            time.sleep(0.13)
        s.settle(0.25)
        scr, _ = s.run_verb("lower", "ide")
        check("the selection whispers it back (DXN3 -> dxn3)",
              "from dxn3 import *" in scr.text(5),
              repr(scr.text(5)[:40]))

        # ── 7. the collapse — :uniq — back-to-back repeats say it once
        print("── 7. the collapse — :uniq sweeps the echoes")
        s.send(CTRL_END)
        s.settle(0.25)
        for text in ("\r", "zz", "\r", "zz"):    # two echoes at the end
            s.send(text)                          # each step its own frame
            time.sleep(0.15)
        s.settle(0.4)
        scr, _ = s.run_verb("uniq", "ide")
        check(":uniq names the line that fell",
              "1 duplicate line collapsed" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        check("one zz remains where two stood (the view clamps up)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "aa" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "zz",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))

        # ── 8. the flip — :rev — the lines walk end for end ──────────
        print("── 8. the flip — :rev, no alphabet invited")
        # the tail reads aa, zz; the hand rests on the survivor (42,0)
        s.send(S_UP)                              # the bed: the last two
        s.settle(0.25)
        scr, _ = s.run_verb("rev", "ide")
        check(":rev names its count",
              "2 lines flipped" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        check("the bed walked end for end (zz, aa)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "zz" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "aa",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))

        # ── 9. the diamond button — a click on the ◆ pulls the pin ───
        print("── 9. the diamond button — the gutter's edge answers")
        s.settle(1.4)                     # the rev's auto-run speaks first:
                                          # the console quiets before the click
        # pins ride at lines 37 and 40 (0-based 36/39); top is 14, so
        # line 36 paints at row 23, its ◆ at col GUTTER-1
        check("the pin's diamond rides the gutter's edge",
              scr.cell(23, GUTTER - 1)[0] == "◆",
              repr(scr.cell(23, GUTTER - 1)))
        s.send(ESC + "[<0;4;24M" + ESC + "[<0;4;24m")   # click the ◆
        scr = s.settle(0.4)
        check("a click on the diamond pulls the pin",
              scr.cell(23, GUTTER - 1)[0] != "◆",
              repr(scr.cell(23, GUTTER - 1)))
        check("the hand never moved (a look, never an edit)",
              scr.cell(ROWS - 4, GUTTER)[2] == CURSOR_BG,
              repr(scr.cell(ROWS - 4, GUTTER)))
        check("the pull speaks in the ledger",
              "pin pulled from line 37" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:50]))
        check("the sibling pin is unharmed",
              scr.cell(26, GUTTER - 1)[0] == "◆",
              repr(scr.cell(26, GUTTER - 1)))

        # ── 10. the breath — :indent steps the bed right, :dedent back
        print("── 10. the breath — :indent and :dedent, one round trip")
        # the tail reads zz, aa; the hand rests at the rev'd bed's HEAD
        # (41,0) — so the last two lines are shift+DOWN, not up
        s.send(S_DOWN)                            # the bed: the last two
        s.settle(0.25)
        scr, _ = s.run_verb("indent", "ide")
        check(":indent names its count",
              "2 lines stepped right" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        check("the bed stepped right (four honest spaces)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 6] == "    zz" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 6] == "    aa",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))
        # the selection let go and the hand rests at the bed's head —
        # so the same bed is shift+DOWN again (the sort family's law)
        s.send(S_DOWN)
        s.settle(0.25)
        scr, _ = s.run_verb("dedent", "ide")
        check(":dedent names its count",
              "2 lines stepped back left" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        s.settle(2.5)                     # the auto-run's sparks decay:
                                          # the indent's burst still flies
        scr = s.screen()                  # a fresh, quiet frame
        check("the bed stepped back (the round trip is honest)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "zz" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "aa",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))
        scr, _ = s.run_verb("dedent", "ide")      # no bed left: refused
        check(":dedent without a bed is refused, never guessed",
              "select the lines to dedent" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))

        # ── 11. the ride — :drop and :lift move the hand's line ──────
        print("── 11. the ride — the hand's line steps down, then back")
        # the tail reads zz(41), zz(42), aa(43); the hand rests at the
        # breath's bed head (0-based 41 = line 42, "zz")
        scr, _ = s.run_verb("drop", "ide")
        check(":drop names its ride",
              "1 line dropped one line" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        s.settle(2.5)                     # the burst decays before a
        scr = s.screen()                  # body-text assert
        check("the line landed below (the neighbor slid up)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "aa" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "zz",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))
        scr, _ = s.run_verb("lift", "ide")
        check(":lift names the ride home",
              "1 line lifted one line" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        s.settle(2.5)                     # the round trip is honest
        scr = s.screen()
        check("the line rode back (the tail restored)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "zz" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "aa",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))

        # ── 12. the echo — :dup says the hand's line twice ───────────
        print("── 12. the echo — the hand's line says it twice")
        # the tail reads zz(41), zz(42), aa(43); the hand rests at the
        # ride's landing (line 42, "zz")
        scr, _ = s.run_verb("dup", "ide")
        check(":dup names its echo",
              "duplicated 1 line" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        s.settle(2.5)                     # the burst decays before a
        scr = s.screen()                  # body-text assert
        check("the copy sits below (original, echo, in view)",
              scr.text(ROWS - 4)[GUTTER:GUTTER + 2] == "zz" and
              scr.text(ROWS - 3)[GUTTER:GUTTER + 2] == "zz",
              repr(scr.text(ROWS - 4)[:12] + scr.text(ROWS - 3)[:12]))

        # ── 13. the fold — :join says the bed once, in one breath ────
        print("── 13. the fold — the hand's line folds with the one below")
        # the tail reads zz(41), zz(42), zz(43, the echo), aa(44); the
        # hand rests on the echo (line 43)
        scr, _ = s.run_verb("join", "ide")
        check(":join names its fold",
              "folded 2 lines into one" in scr.text(ROWS - 2),
              repr(scr.text(ROWS - 2)[:60]))
        s.settle(2.5)                     # the burst decays before a
        scr = s.screen()                  # body-text assert
        check("the fold speaks one space (zz aa at the seam)",
              scr.text(ROWS - 3)[GUTTER:GUTTER + 5] == "zz aa",
              repr(scr.text(ROWS - 3)[:16]))

        # ── 14. the exit — clean, code 0 ──────────────────────────────
        print("── 14. the exit — esc to play, q quits")
        s.send(ESC)
        time.sleep(0.2)
        s.send("q")
        ok = s.wait_exit()
        check("the studio exits on q (from play)", ok)
        check("the exit is clean (code 0)", s.exit_code == 0,
              repr(s.exit_code))

        return finish(s)
    except Exception as e:
        print(f"smoke: harness error: {e!r}")
        return finish(s, failed=True)


def finish(s, failed=False):
    s.close()
    green = sum(1 for _, ok in results if ok)
    print(f"\nSMOKE: {green}/{len(results)} checks green")
    if green != len(results) or failed:
        print("SMOKE RED — the failures above are real")
        return 1
    print("SMOKE GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
