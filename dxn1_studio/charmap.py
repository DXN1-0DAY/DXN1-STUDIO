"""DS2 Character Map — find, inspect and copy Unicode glyphs.

A compact Unicode browser: browse curated blocks (arrows, math, box
drawing, CJK, emoji-ish dingbats…), search by block name or hex
codepoint, click any character to copy it and read its codepoint.

Engine (block_names / chars_in / search / describe) is pure and
unit-tested; the window never raises.

Open with: Workshop menu, palette, terminal ``charmap`` / ``char``.
"""

import unicodedata
import tkinter as tk

from .i18n import tr

__all__ = ["block_names", "chars_in", "search", "describe",
           "CharacterMap", "open_charmap"]

# (name, first codepoint, last codepoint) — curated, offline blocks
_BLOCKS = (
    ("Basic Latin", 0x20, 0x7E),
    ("Latin-1 Supplement", 0xA0, 0xFF),
    ("Latin Extended-A", 0x100, 0x17F),
    ("Greek", 0x391, 0x3C9),
    ("Cyrillic", 0x410, 0x44F),
    ("Hebrew", 0x5D0, 0x5EA),
    ("Arabic", 0x627, 0x64A),
    ("Punctuation", 0x2013, 0x205E),
    ("Currency", 0x20A0, 0x20BF),
    ("Arrows", 0x2190, 0x21FF),
    ("Math Operators", 0x2200, 0x22FF),
    ("Technical", 0x2300, 0x23FF),
    ("Box Drawing", 0x2500, 0x257F),
    ("Block Elements", 0x2580, 0x259F),
    ("Geometric Shapes", 0x25A0, 0x25FF),
    ("Misc Symbols", 0x2600, 0x26FF),
    ("Dingbats", 0x2700, 0x27BF),
    ("Braille", 0x2800, 0x28FF),
    ("CJK Punctuation", 0x3000, 0x303F),
    ("Hiragana", 0x3041, 0x3096),
    ("Katakana", 0x30A1, 0x30FA),
    ("Bopomofo", 0x3105, 0x312F),
    ("Hangul Syllables", 0xAC00, 0xAC1B),
    ("CJK Unified (sample)", 0x4E00, 0x4E3B),
    ("Fullwidth Forms", 0xFF01, 0xFF5E),
)


def block_names():
    """Sorted block names."""
    return sorted(b[0] for b in _BLOCKS)


def chars_in(name, limit=512):
    """Characters of a block (bounded). Junk name → []."""
    if not isinstance(name, str):
        return []
    for bname, lo, hi in _BLOCKS:
        if bname.lower() == name.strip().lower():
            return [chr(c) for c in range(lo, min(hi, lo + limit - 1) + 1)]
    return []


def search(query, limit=200):
    """Search characters: block-name substring, hex codepoint
    (``00e9`` / ``U+00E9``) or a literal character. Never raises."""
    if not isinstance(query, str):
        return []
    q = query.strip()
    if not q:
        return []
    if len(q) == 1:
        return [q]
    hexpart = q.lower().replace("u+", "").replace("0x", "")
    try:
        return [chr(int(hexpart, 16))]
    except ValueError:
        pass
    out = []
    for bname, lo, hi in _BLOCKS:
        if q.lower() in bname.lower():
            out.extend(chr(c) for c in range(lo, hi + 1))
        if len(out) >= limit:
            break
    return out[:limit]


def describe(ch):
    """One-line description like ``U+00E9 · é · LATIN SMALL LETTER …``."""
    try:
        cp = ord(ch)
    except (TypeError, ValueError):
        return ""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = "<unnamed>"
    return "U+%04X · %s · %s" % (cp, ch, name)


# --------------------------------------------------------------- window

class CharacterMap(tk.Toplevel):
    """Click-to-copy Unicode browser. Never raises on weird input."""

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Character Map — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("640x480")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 640x480 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 640, 480))
        self.minsize(500, 380)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="character map",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=(10, 8), pady=8)
        self.query = tk.StringVar()
        entry = tk.Entry(top, textvariable=self.query, width=22,
                         bg=t.get("editor_bg", "#1a1a24"),
                         fg=t.get("text", "#e8e8f0"),
                         insertbackground=t.get("text", "#fff"),
                         relief=tk.FLAT)
        entry.pack(side=tk.LEFT, padx=4)
        entry.bind("<KeyRelease>", lambda _e: self.refresh())
        self.block_pick = tk.StringVar(value=block_names()[0])
        pick = tk.OptionMenu(top, self.block_pick, *block_names(),
                             command=lambda _v: self.refresh())
        pick.config(bg=t.get("button", "#2a2a3a"),
                    fg=t.get("text", "#e8e8f0"),
                    activebackground=t.get("button_hover", "#33334a"),
                    highlightthickness=0)
        pick.pack(side=tk.RIGHT, padx=(4, 10), pady=4)

        self.grid = tk.Text(self, wrap="char", font=("TkFixedFont", 14),
                            bg=t.get("editor_bg", "#1a1a24"),
                            fg=t.get("text", "#e8e8f0"), relief=tk.FLAT,
                            padx=10, pady=8, cursor="hand2")
        self.grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        self.grid.bind("<Button-1>", self._pick)
        self.grid.tag_config("sel", background="")
        self.grid.config(state=tk.NORMAL)

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text=tr("charmap.click_copy"),
                               anchor="w", bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text="copy all shown", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_all).pack(side=tk.RIGHT, padx=8,
                                               pady=4)

        self.refresh()

    # ---------------------------------------------------- behaviour
    def _current_chars(self):
        """Characters to show. A query that matches nothing returns []
        (honest 'nothing matches'); only a query-less view falls back."""
        q = self.query.get().strip()
        if q:
            return search(q, limit=400)
        return chars_in(self.block_pick.get(), limit=400) or \
            chars_in("Basic Latin", limit=200)

    def refresh(self):
        """Rebuild the glyph grid. Never raises."""
        try:
            chars = self._current_chars()
            self.grid.config(state=tk.NORMAL)
            self.grid.delete("1.0", "end")
            if chars:
                # space every glyph for click precision
                self.grid.insert("1.0", " ".join(chars))
                self.status.config(
                    text="%d characters — click to copy"
                         % len(chars))
            else:
                self.status.config(
                    text="nothing matches — try a block name, a "
                         "hex codepoint (U+2192) or a character")
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _pick(self, event):
        """Click a glyph → describe it and copy it."""
        try:
            index = self.grid.index("@%s,%s" % (event.x, event.y))
            line, col = index.split(".")
            ch = self.grid.get("%s.%s" % (line, col))
            if not ch or ch == " ":
                return
            self.clipboard_clear()
            self.clipboard_append(ch)
            self.status.config(text=describe(ch) + "  — copied")
        except Exception:  # noqa: BLE001
            pass

    def _copy_all(self):
        try:
            chars = self._current_chars()
            self.clipboard_clear()
            self.clipboard_append("".join(chars))
            self.status.config(text="%d characters copied"
                               % len(chars))
        except Exception:
            pass


def open_charmap(parent, theme):
    """Public entry: open the Character Map window. Never raises."""
    try:
        win = CharacterMap(parent, theme)
        win.grab_release()
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
