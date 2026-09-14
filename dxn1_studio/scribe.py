"""DS2 Scribe Chip — a live words/WPM mini meter in the statusbar.

A tiny writing tracker for the main editor (zen mode has its own
stats card): the statusbar chip shows current words, trailing WPM
and progress toward a session word goal. Observations are throttled
so big buffers stay snappy, and the engine is pure & unit-tested.

Open with: it lives in the statusbar; click it for a session toast.
Configure: terminal ``scribe <words>`` sets the goal.
"""

import time

from .zen import SessionStats

__all__ = ["ScribeChip", "chip_text"]

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
