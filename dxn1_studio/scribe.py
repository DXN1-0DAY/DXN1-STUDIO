"""DS2 Scribe Chip — a live words/WPM mini meter in the statusbar.

A tiny writing tracker for the main editor (zen mode has its own
stats card): the statusbar chip shows current words, trailing WPM
and progress toward a session word goal. Observations are throttled
so big buffers stay snappy, and the engine is pure & unit-tested.

Open with: it lives in the statusbar; click it for a session toast.
Configure: terminal ``scribe <words>`` sets the goal.
"""

import time
import tkinter as tk

from .theme import FONT_UI, FONT_MONO
from .zen import SessionStats

__all__ = ["ScribeChip", "chip_text", "open_goal_dialog"]

MIN_INTERVAL = 2.0          # seconds between fed observations


def chip_text(words, wpm, pct, goal=0):
    """The exact string the chip renders (pure, testable)."""
    pct_part = " · %d%%" % pct if goal > 0 else ""
    return "✎ %s w · %d wpm%s" % (format_count(words), round(wpm),
                                  pct_part)


def format_count(n):
    """1234 → ``1,234`` (grouped thousands)."""
    return "{:,}".format(max(0, int(n)))


class ScribeChip:
    """Throttled observer around SessionStats + label text builder."""

    def __init__(self, goal_words=500, stats=None, min_interval=None):
        self.stats = stats if stats is not None \
            else SessionStats(goal_words=goal_words)
        self.min_interval = (MIN_INTERVAL if min_interval is None
                             else float(min_interval))
        self._last_fed = None
        self._last_words = 0
        self._last_wpm = 0.0
        self._last_text = ""

    # ------------------------------------------------------- feeding
    def observe(self, word_count, now=None):
        """Feed one word count; returns True when the text changed.

        Throttled: observations closer together than min_interval
        update nothing (except the very first one). Explicit ``now``
        keeps tests deterministic. (The underlying SessionStats
        stamps wall-clock times internally — the throttle therefore
        keeps its own clock instead of trusting sample stamps.)
        """
        now = time.time() if now is None else now
        if self._last_fed is not None and \
                now - self._last_fed < self.min_interval:
            return False
        self._last_fed = now
        self.stats.observe(word_count)
        self._last_words = word_count
        self._last_wpm = self.stats.current_wpm()
        new_text = self.text()
        changed = new_text != self._last_text
        self._last_text = new_text
        return changed

    # ------------------------------------------------------- output
    @property
    def goal_words(self):
        return self.stats.goal_words

    def set_goal(self, goal_words):
        """Change the session goal (0 hides the percentage part)."""
        try:
            self.stats.goal_words = max(0, int(goal_words))
        except (TypeError, ValueError):
            return False
        self._last_text = self.text()
        return True

    def words(self):
        return self._last_words

    def wpm(self):
        return self._last_wpm

    def peak_wpm(self):
        return self.stats.peak_wpm

    def elapsed_min(self):
        return self.stats.elapsed_min()

    def goal_pct(self):
        return self.stats.goal_pct()

    def text(self):
        """Current chip label (never raises)."""
        try:
            return chip_text(self._last_words, self._last_wpm,
                             self.goal_pct(),
                             goal=self.stats.goal_words)
        except Exception:  # noqa: BLE001 — a chip must never kill UI
            return ""

    def reset(self):
        """Start a fresh session (goal preserved)."""
        goal = self.stats.goal_words
        self.stats = SessionStats(goal_words=goal)
        self._last_fed = None
        self._last_words = 0
        self._last_wpm = 0.0
        self._last_text = self.text()


def open_goal_dialog(master, theme, current, on_set=None):
    """DS2 v2.44 — a themed goal dialog for the scribe chip menu:
    type a word count (or keep the prefilled current one), press Set
    or Enter — nothing changes until then. Invalid input gets an
    inline honest error and the dialog stays open. Returns the
    Toplevel so callers (tests, smoke) can inspect it. Best-effort
    by contract."""
    win = tk.Toplevel(master)
    win.title("Writing goal")
    win.configure(bg=theme["card"])
    win.transient(master)
    win.resizable(False, False)

    wrap = tk.Frame(win, bg=theme["card"], highlightthickness=1,
                    highlightbackground=theme["card_border"])
    wrap.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    tk.Label(wrap, text="WRITING GOAL", bg=theme["card"],
             fg=theme["text"], font=(FONT_UI, 11,
                                     "bold")).pack(
        anchor="w", padx=16, pady=(14, 2))
    tk.Label(wrap, text="Words for this writing session — the ✎ chip "
                        "shows your progress toward it.",
             bg=theme["card"], fg=theme["text_muted"],
             font=(FONT_UI, 8), anchor="w", wraplength=260,
             justify="left").pack(anchor="w", padx=16, pady=(0, 8))

    var = tk.StringVar(value=str(int(current) if current else 0))
    entry = tk.Entry(wrap, textvariable=var, bg=theme["editor"],
                     fg=theme["text"], insertbackground=theme["text"],
                     relief=tk.FLAT, font=(FONT_MONO, 11),
                     highlightthickness=1,
                     highlightbackground=theme["border"],
                     highlightcolor=theme.accent, width=16,
                     justify="center")
    entry.pack(padx=16, ipady=5, fill=tk.X)

    err = tk.Label(wrap, text="", bg=theme["card"], fg="#f85149",
                   font=(FONT_UI, 8), anchor="w")
    err.pack(anchor="w", padx=16, pady=(4, 0))

    def _set(_event=None):
        raw = var.get().strip()
        try:
            goal = int(raw)
        except (TypeError, ValueError):
            err.config(text="whole numbers only — e.g. 500")
            return False
        if goal < 0:
            err.config(text="zero or more — e.g. 500 (0 = no goal)")
            return False
        try:
            if on_set:
                on_set(goal)
        except Exception:  # noqa: BLE001 — the callback owns itself
            pass
        try:
            win.destroy()
        except Exception:  # noqa: BLE001 — dying root is fine
            pass
        return True

    def _cancel(_event=None):
        try:
            win.destroy()
        except Exception:  # noqa: BLE001 — dying root is fine
            pass
        return "break"

    btns = tk.Frame(wrap, bg=theme["card"])
    btns.pack(fill=tk.X, padx=16, pady=(10, 14))
    set_btn = tk.Label(btns, text="✓  Set goal", bg=theme.accent,
                       fg="#ffffff", font=(FONT_UI, 9, "bold"),
                       cursor="hand2", padx=12, pady=5)
    set_btn.pack(side=tk.LEFT)
    set_btn.bind("<Button-1>", _set)
    cancel_btn = tk.Label(btns, text="Cancel", bg=theme["card"],
                          fg=theme["text_secondary"], cursor="hand2",
                          padx=10, pady=5)
    cancel_btn.pack(side=tk.LEFT, padx=(8, 0))
    cancel_btn.bind("<Button-1>", _cancel)

    entry.bind("<Return>", _set)
    win.bind("<Escape>", _cancel)
    try:
        entry.focus_set()
        entry.selection_range(0, tk.END)
    except Exception:  # noqa: BLE001 — focus is garnish
        pass
    return win
