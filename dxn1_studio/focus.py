"""DS2 Focus Timer — pomodoro sessions that live in your IDE.

Pure engine (FocusEngine state machine: work → short break → … → long
break, deterministic ticks) + a compact window with session dots,
start/pause/reset and a completed-session log. Tests drive the engine
tick-by-tick — no wall-clock flakiness.

Open with: palette, Workshop menu, terminal ``focus`` / ``focus 50``.
"""

import tkinter as tk

__all__ = ["FocusEngine", "FocusWindow", "open_focus", "fmt_mmss"]

WORK_DEFAULT = 25 * 60
BREAK_DEFAULT = 5 * 60
LONG_BREAK_DEFAULT = 15 * 60
LONG_EVERY = 4          # long break after every 4th work block


def fmt_mmss(secs):
    """1500 -> '25:00'; clamp negatives to zero."""
    try:
        secs = max(0, int(secs))
    except (TypeError, ValueError):
        return "00:00"
    return f"{secs // 60:02d}:{secs % 60:02d}"


class FocusEngine:
    """Deterministic pomodoro state machine.

    Phases: 'work', 'break', 'long'. tick(seconds) advances remaining
    time, rolls over phase boundaries and returns the list of events
    that fired ('work-done', 'break-done', 'cycle-done'). Never raises.
    """

    def __init__(self, work=WORK_DEFAULT, brk=BREAK_DEFAULT,
                 long_break=LONG_BREAK_DEFAULT, long_every=LONG_EVERY):
        self.work = max(60, int(work))
        self.brk = max(30, int(brk))
        self.long_break = max(60, int(long_break))
        self.long_every = max(2, int(long_every))
        self.reset()

    def reset(self):
        """Back to a fresh first work block (keeps durations)."""
        self.phase = "work"
        self.remaining = self.work
        self.cycle = 1            # work blocks finished in current set
        self.completed = 0        # total work blocks finished
        self.running = False
        return []

    def duration_of(self, phase):
        return {"work": self.work, "break": self.brk,
                "long": self.long_break}[phase]

    def tick(self, secs=1):
        """Advance by whole seconds; returns fired events."""
        events = []
        try:
            secs = max(0, int(secs))
        except (TypeError, ValueError):
            return events
        if not self.running:
            return events
        for _ in range(secs):
            if self.remaining > 0:
                self.remaining -= 1
            if self.remaining == 0:
                # phase elapsed inside this very second → transition now
                if self.phase == "work":
                    events.append("work-done")
                    self.completed += 1
                    if self.cycle >= self.long_every:
                        events.append("cycle-done")
                        self.phase = "long"
                        self.cycle = 1
                    else:
                        self.phase = "break"
                        self.cycle += 1
                else:
                    events.append("break-done")
                    self.phase = "work"
                self.remaining = self.duration_of(self.phase)
        return events

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def skip(self):
        """Jump to the next phase immediately (as if time elapsed)."""
        was_running = self.running
        self.remaining = 0
        self.running = True
        events = self.tick(1)
        self.running = was_running
        return events

    def label(self):
        """'25:00' style display for the current remaining time."""
        return fmt_mmss(self.remaining)

    def phase_label(self):
        return {"work": "FOCUS", "break": "SHORT BREAK",
                "long": "LONG BREAK"}[self.phase]


class FocusWindow(tk.Toplevel):
    """Compact focus timer window."""

    def __init__(self, parent, theme, minutes=0, workspace=""):
        super().__init__(parent)
        self.theme = theme or {}
        self.workspace = workspace
        t = self.theme

        work = (int(minutes) * 60) if minutes and int(minutes) >= 1 \
            else WORK_DEFAULT
        self.engine = FocusEngine(work=work)

        self.title("Focus Timer — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("360x300")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 360x300 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 360, 300))
        self.resizable(False, False)
        try:
            self.transient(parent)
        except Exception:
            pass

        self.phase_lbl = tk.Label(
            self, text=self.engine.phase_label(),
            bg=t.get("bg", "#16161e"),
            fg=t.get("text_muted", "#8a8a9a"),
            font=("TkDefaultFont", 12, "bold"))
        self.phase_lbl.pack(pady=(18, 0))
        self.clock_lbl = tk.Label(
            self, text=self.engine.label(),
            bg=t.get("bg", "#16161e"),
            fg=t.get("text", "#e8e8f0"),
            font=("TkFixedFont", 44, "bold"))
        self.clock_lbl.pack(pady=(0, 4))

        self.dots = tk.Label(self, text=self._dots_text(),
                             bg=t.get("bg", "#16161e"),
                             fg=t.get("success", "#5ad19c"),
                             font=("TkDefaultFont", 12))
        self.dots.pack()

        btns = tk.Frame(self, bg=t.get("bg", "#16161e"))
        btns.pack(pady=8)
        self.toggle_btn = self._btn(btns, "Start", self.toggle)
        self.toggle_btn.pack(side=tk.LEFT, padx=4)
        self._btn(btns, "Reset", self.do_reset).pack(side=tk.LEFT, padx=4)
        self._btn(btns, "Skip", self.do_skip).pack(side=tk.LEFT, padx=4)

        self.log_lbl = tk.Label(
            self, text="no sessions finished yet",
            bg=t.get("bg", "#16161e"),
            fg=t.get("text_muted", "#8a8a9a"))
        self.log_lbl.pack(side=tk.BOTTOM, pady=(0, 10))

        self._job = None
        self.bind("<Escape>", lambda _e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._render()

    # ------------------------------------------------------------- UI
    def _btn(self, parent, text, cmd):
        t = self.theme
        return tk.Button(
            parent, text=text, command=cmd, relief="flat", bd=0, width=7,
            bg=t.get("hover", "#2c2c3e"), fg=t.get("text", "#e8e8f0"),
            activebackground=t.get("border", "#3a3a4e"),
            activeforeground=t.get("text", "#e8e8f0"),
            padx=8, pady=3, cursor="hand2")

    def _dots_text(self):
        return "● " * (self.engine.cycle - 1) + \
               "○ " * (self.engine.long_every - self.engine.cycle + 1)

    def _render(self):
        t = self.theme
        self.clock_lbl.config(text=self.engine.label())
        self.phase_lbl.config(text=self.engine.phase_label())
        self.dots.config(text=self._dots_text())
        self.toggle_btn.config(
            text="Pause" if self.engine.running else "Start")

    def _log(self, events):
        if "work-done" in events:
            self.log_lbl.config(
                text=f"{self.engine.completed} focus block(s) finished —"
                     " stretch, drink water")
        if "cycle-done" in events:
            self.log_lbl.config(
                text="set of 4 done — take a long break, you earned it")

    def _loop(self):
        if self.engine.running:
            events = self.engine.tick(1)
            self._log(events)
            self._render()
        self._job = self.after(1000, self._loop)

    # -------------------------------------------------------- actions
    def toggle(self):
        if self.engine.running:
            self.engine.pause()
        else:
            self.engine.start()
        self._render()

    def do_reset(self):
        self.engine.reset()
        self.log_lbl.config(text="no sessions finished yet")
        self._render()

    def do_skip(self):
        events = self.engine.skip()
        self._log(events)
        self._render()

    def _close(self):
        try:
            if self._job:
                self.after_cancel(self._job)
        except Exception:
            pass
        self.destroy()


def open_focus(parent, theme, initial="", workspace=""):
    """Public opener — palette / menu / terminal entry point.

    ``initial`` may be a number of minutes for a custom work block.
    """
    try:
        minutes = int(str(initial).strip())
    except (TypeError, ValueError):
        minutes = 0
    return FocusWindow(parent, theme, minutes=minutes,
                       workspace=workspace)
