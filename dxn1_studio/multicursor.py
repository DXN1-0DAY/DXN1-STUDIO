"""DXN1 STUDIO — multi-cursor editing (DS2 v1.5).

Tk's Text widget natively has one cursor, so DS2 emulates multi-cursor
editing: extra carets are tracked as index pairs, painted with a
``multi_sel`` highlight tag, and every edit is applied to each caret
bottom-up so earlier indices stay valid while later ones shift.

Supported: *add next occurrence* (Ctrl+D in VS Code terms), *select all
occurrences*, caret-at-each-region typing, deletion, and arbitrary
callbacks. The engine never fights the real selection — when only zero
or one region is active it is a no-op wrapper around normal editing.
"""

import re
import tkinter as tk

MULTI_TAG = "multi_sel"


def _index(text, index):
    """'line.col' → (line, col) ints."""
    line, col = str(index).split(".")
    return int(line), int(col)


def _mk(line, col):
    return f"{line}.{col}"


class MultiCursor:
    """Emulated multi-caret editing over a Tk Text widget."""

    def __init__(self, text_widget, theme_colors=None):
        self.text = text_widget
        self.regions = []  # [(start_idx, end_idx)] as (line,col) tuples
        self.text.tag_configure(
            MULTI_TAG,
            background=(theme_colors or {}).get(
                "multi_bg", "#264f78"),
            foreground=(theme_colors or {}).get(
                "multi_fg", "#ffffff"))

    # ------------------------------------------------------------- state
    def active(self):
        return len(self.regions) > 1

    def clear(self):
        self.regions = []
        self.text.tag_remove(MULTI_TAG, "1.0", "end")

    def _paint(self):
        self.text.tag_remove(MULTI_TAG, "1.0", "end")
        for start, end in self.regions:
            if start != end:
                self.text.tag_add(MULTI_TAG, _mk(*start), _mk(*end))

    def _sorted_regions(self):
        return sorted(self.regions, key=lambda r: (r[0], r[1]),
                      reverse=True)  # bottom-up for stable edits

    # ------------------------------------------------------------ adding
    def add_current_word(self):
        """Seed regions with the word under the cursor."""
        word, start, end = self._word_at_cursor()
        if word:
            self.regions = [(start, end)]
            self._paint()
            return word
        return None

    def _word_at_cursor(self):
        insert = self.text.index(tk.INSERT)
        line, col = _index(self.text, insert)
        content = self.text.get(_mk(line, 0), _mk(line, "end"))
        # find the word boundaries around col
        for match in re.finditer(r"\w+", content):
            if match.start() <= col <= match.end():
                return match.group(0), (line, match.start()), \
                    (line, match.end())
        return None, None, None

    def add_next_occurrence(self):
        """Add the next match of the seed word as a new region."""
        if not self.regions:
            word = self.add_current_word()
            if not word:
                return 0
        seed = self.text.get(_mk(*self.regions[0][0]),
                             _mk(*self.regions[0][1]))
        if not seed:
            return 0
        # search after the last region (wrapping once)
        last = max(self.regions, key=lambda r: (r[0], r[1]))
        start_at = _mk(*last[1])
        pos = self.text.search(seed, start_at, nocase=False)
        if not pos and self.regions:
            first = min(self.regions, key=lambda r: (r[0], r[1]))
            pos = self.text.search(seed, "1.0", stopindex=_mk(*first[0]))
        if not pos:
            return len(self.regions)
        s = _index(self.text, pos)
        e = (s[0], s[1] + len(seed))
        if (s, e) not in self.regions:
            self.regions.append((s, e))
            self._paint()
        return len(self.regions)

    def select_all_occurrences(self):
        """Select every occurrence of the seed word in the buffer."""
        if not self.regions:
            if not self.add_current_word():
                return 0
        seed = self.text.get(_mk(*self.regions[0][0]),
                             _mk(*self.regions[0][1]))
        if not seed:
            return 0
        self.regions = []
        pos = "1.0"
        while True:
            pos = self.text.search(seed, pos + "+1c" if pos != "1.0" else pos,
                                   stopindex="end", nocase=False)
            if not pos:
                break
            s = _index(self.text, pos)
            e = (s[0], s[1] + len(seed))
            self.regions.append((s, e))
        self._paint()
        return len(self.regions)

    # ----------------------------------------------------------- editing
    def insert_at_each(self, content):
        """Insert ``content`` at every caret (bottom-up)."""
        if not self.regions:
            return
        for start, _end in self._sorted_regions():
            self.text.insert(_mk(*start), content)
        self.clear()

    def delete_at_each(self, count=1):
        """Delete ``count`` chars after (or before, negative) each caret."""
        if not self.regions:
            return
        for start, _end in self._sorted_regions():
            if count >= 0:
                self.text.delete(_mk(*start), _mk(start[0], start[1] + count))
            else:
                self.text.delete(_mk(start[0], start[1] + count),
                                 _mk(*start))
        self.clear()

    def apply_to_each(self, fn):
        """Run ``fn(text_widget, start_index_str, end_index_str)`` per region.

        Bottom-up, so ``fn`` may modify text lengths freely. Regions are
        cleared afterwards (standard multi-cursor behaviour).
        """
        if not self.regions:
            return 0
        n = 0
        for start, end in self._sorted_regions():
            try:
                fn(self.text, _mk(*start), _mk(*end))
                n += 1
            except tk.TclError:
                continue
        self.clear()
        return n

    def replace_each(self, replacement):
        """Replace every region's content with ``replacement``."""
        return self.apply_to_each(
            lambda w, s, e: (w.delete(s, e), w.insert(s, replacement)))

    def regions_info(self):
        return len(self.regions)
