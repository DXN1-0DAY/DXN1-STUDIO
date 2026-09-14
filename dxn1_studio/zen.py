"""DXN1 STUDIO — writing stats & session goals (DS2 v2.3).

Zen mode hides the chrome; this adds the other half of deep work:
knowing how the session went. It watches the editor buffer (keystrokes
approximated by buffer deltas, zero keylogging — only text length and
word counts are recorded), tracks a live WPM, peak, and a session goal
("500 words" or "25 minutes"), and shows a small stats card.

Everything lives in memory for the session. Nothing is recorded
anywhere. Privacy first: we count characters, we never store them.
"""

import time
import tkinter as tk

from .theme import FONT_UI, FONT_MONO

POLL_MS = 1000


class SessionStats:
    """In-memory writing tracker for one studio session."""

    def __init__(self, goal_words=500):
        self.goal_words = goal_words
        self.started = time.time()
        self.samples = []            # (timestamp, word_count)
        self.peak_wpm = 0.0
        self._last_count = None
        self._last_time = None

    def observe(self, word_count):
        now = time.time()
        if self._last_count is not None and self._last_time is not None:
            delta = word_count - self._last_count
            dt = max(0.5, now - self._last_time)   # real seconds elapsed
            if delta > 0:
                wpm = delta / (dt / 60.0)
                if wpm < 400:                      # ignore paste spikes
                    self.peak_wpm = max(self.peak_wpm, wpm)
        self._last_count = word_count
        self._last_time = now
        self.samples.append((now, word_count))
        # keep an hour of samples
        cutoff = now - 3600
        self.samples = [s for s in self.samples if s[0] >= cutoff]

    def elapsed_min(self):
        return (time.time() - self.started) / 60.0

    def words(self):
        return self._last_count or 0

    def current_wpm(self, window=180):
        """Words-per-minute over the trailing window."""
        if len(self.samples) < 2:
            return 0.0
        now = time.time()
        recent = [(t, w) for t, w in self.samples if t >= now - window]
        if len(recent) < 2:
            return 0.0
        dt = recent[-1][0] - recent[0][0]
        dw = recent[-1][1] - recent[0][1]
        if dt <= 0 or dw <= 0:
            return 0.0
        return min(400.0, dw / (dt / 60.0))   # paste-spike guard

    def goal_pct(self):
        if self.goal_words <= 0:
            return 0
        return min(100, int(self.words() * 100 / self.goal_words))


class ZenStatsCard(tk.Frame):
    """The small in-zen HUD: WPM, goal ring text, session time."""

    def __init__(self, parent, theme, stats, on_exit=None):
        super().__init__(parent, bg=theme["statusbar"])
        self.t = theme
        self.stats = stats
        self.on_exit = on_exit
        tk.Label(self, text="◉ zen", bg=theme["statusbar"],
                 fg=theme.accent, font=(FONT_MONO, 9, "bold")).pack(
            side=tk.LEFT, padx=(12, 8), pady=4)
        self.wpm_lbl = tk.Label(self, text="0 wpm", bg=theme["statusbar"],
                                fg=theme["text_secondary"],
                                font=(FONT_MONO, 9))
        self.wpm_lbl.pack(side=tk.LEFT, padx=6)
        self.goal_lbl = tk.Label(self, text="", bg=theme["statusbar"],
                                 fg=theme["text_muted"], font=(FONT_MONO, 9))
        self.goal_lbl.pack(side=tk.LEFT, padx=6)
        self.time_lbl = tk.Label(self, text="", bg=theme["statusbar"],
                                 fg=theme["text_muted"], font=(FONT_MONO, 9))
        self.time_lbl.pack(side=tk.LEFT, padx=6)
        if on_exit:
            exit_lbl = tk.Label(self, text="exit zen ✕",
                                bg=theme["statusbar"],
                                fg=theme["text_muted"], font=(FONT_UI, 8),
                                cursor="hand2")
            exit_lbl.pack(side=tk.RIGHT, padx=12)
            exit_lbl.bind("<Button-1>", lambda e: on_exit())
        self._tick()

    def _tick(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        wpm = self.stats.current_wpm()
        self.wpm_lbl.config(text=f"{wpm:.0f} wpm · peak "
                                 f"{self.stats.peak_wpm:.0f}")
        self.goal_lbl.config(text=f"goal {self.stats.goal_pct()}% "
                                  f"({self.stats.words()} words)")
        mins = self.stats.elapsed_min()
        self.time_lbl.config(text=f"{int(mins)}m {int(mins * 60) % 60}s")
        self.after(POLL_MS, self._tick)


def observe_editor(stats, text_widget):
    """One observation cycle — call from a poller."""
    try:
        content = text_widget.get("1.0", "end-1c")
        stats.observe(len(content.split()))
    except tk.TclError:
        pass
