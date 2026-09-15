"""DXN1 STUDIO — visual diff viewer (DS2 v1.4).

A theme-aware diff window that can show two texts side by side with
word-level highlighting, or as a unified patch. It also navigates hunks
(‹ ›) with a live "3 / 17" counter, copies a clean unified diff to the
clipboard, and renders everything from the active palette — no hardcoded
colours outside the two diff tint pairs.

Everything is stdlib: ``difflib`` does the line and word matching, and
the widget tree is plain Tk — so the viewer costs nothing extra to ship
and runs anywhere the studio runs, including Termux.
"""

import difflib
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO
from . import hints

# ------------------------------------------------------------------ tints
# Line/word colours per theme mode. These are the only fixed colours in
# this module; everything else comes from the resolved Theme.

TINTS = {
    "dark": {
        "add_bg":      "#12261a",
        "add_word":    "#56d364",
        "del_bg":      "#2d1416",
        "del_word":    "#f85149",
        "mod_bg":      "#241a2e",
        "gutter_add":  "#1b3a26",
        "gutter_del":  "#3d1a1d",
        "hunk_bg":     "#1a2233",
        "hunk_fg":     "#7d8590",
    },
    "light": {
        "add_bg":      "#e6ffec",
        "add_word":    "#1a7f37",
        "del_bg":      "#ffebe9",
        "del_word":    "#cf222e",
        "mod_bg":      "#f5f0ff",
        "gutter_add":  "#ccffd8",
        "gutter_del":  "#ffd7d5",
        "hunk_bg":     "#eaeef2",
        "hunk_fg":     "#57606a",
    },
}


# ------------------------------------------------------------------ engine
def compute_row_diff(old_text, new_text):
    """Diff two texts and return a list of row dicts.

    Each row: ``{"kind": "same|add|del|mod", "old": int|None,
    "new": int|None, "text": str, "pairs": [(word, tag), ...]}``.
    ``pairs`` carries word-level segments for modified rows (``None``
    for rows that are unchanged), so the view can paint just the words
    that actually moved.
    """
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    rows = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append({"kind": "same", "old": i1 + k + 1,
                             "new": j1 + k + 1, "text": old_lines[i1 + k],
                             "pairs": None})
        elif tag == "delete":
            for k in range(i2 - i1):
                rows.append({"kind": "del", "old": i1 + k + 1, "new": None,
                             "text": old_lines[i1 + k],
                             "pairs": [((old_lines[i1 + k]), "del")]})
        elif tag == "insert":
            for k in range(j2 - j1):
                rows.append({"kind": "add", "old": None, "new": j1 + k + 1,
                             "text": new_lines[j1 + k],
                             "pairs": [((new_lines[j1 + k]), "add")]})
        else:  # replace — pair lines and word-diff each pair
            a_block = old_lines[i1:i2]
            b_block = new_lines[j1:j2]
            n = max(len(a_block), len(b_block))
            for k in range(n):
                a = a_block[k] if k < len(a_block) else None
                b = b_block[k] if k < len(b_block) else None
                if a is None:
                    rows.append({"kind": "add", "old": None,
                                 "new": j1 + k + 1, "text": b,
                                 "pairs": [(b, "add")]})
                elif b is None:
                    rows.append({"kind": "del", "old": i1 + k + 1,
                                 "new": None, "text": a,
                                 "pairs": [(a, "del")]})
                else:
                    rows.append({"kind": "mod", "old": i1 + k + 1,
                                 "new": j1 + k + 1, "text": b,
                                 "pairs": word_diff(a, b)})
    return rows


def word_diff(a, b):
    """Word-level diff of two strings → ``[(segment, "same|add|del")]``.

    Used inside modified lines so only the words that changed glow,
    not the whole line.
    """
    aw = a.split()
    bw = b.split()
    sm = difflib.SequenceMatcher(a=aw, b=bw, autojunk=False)
    segs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            segs.append((" ".join(aw[i1:i2]), "same"))
        elif tag == "delete":
            segs.append((" ".join(aw[i1:i2]), "del"))
        elif tag == "insert":
            segs.append((" ".join(bw[j1:j2]), "add"))
        else:
            if i1 < i2:
                segs.append((" ".join(aw[i1:i2]), "del"))
            if j1 < j2:
                segs.append((" ".join(bw[j1:j2]), "add"))
    # rebuild spacing conservatively (display-only; copy uses raw text)
    out = []
    for idx, (txt, kind) in enumerate(segs):
        if not txt:
            continue
        out.append((txt if idx == len(segs) - 1 else txt + " ", kind))
    return out or [(a + " → " + b, "same")]


def unified_diff_text(old_text, new_text, old_label="a", new_label="b"):
    """A clean unified patch string — used for the Copy button."""
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    return "\n".join(difflib.unified_diff(
        old_lines, new_lines, fromfile=old_label, tofile=new_label, lineterm=""))


def diff_stats(rows):
    """Return (added, deleted, modified) counts for the header pills."""
    add = sum(1 for r in rows if r["kind"] in ("add", "mod"))
    dele = sum(1 for r in rows if r["kind"] in ("del", "mod"))
    mod = sum(1 for r in rows if r["kind"] == "mod")
    return add, dele, mod


def changed_positions(rows):
    """Row indices worth jumping to (any non-same row)."""
    return [i for i, r in enumerate(rows) if r["kind"] != "same"]


# ------------------------------------------------------------------- view
class DiffViewer(tk.Toplevel):
    """Two-text diff window: split view, unified view, hunk navigation."""

    LINE_H = 18  # px estimate, keeps geometry math simple

    def __init__(self, parent, theme, old_text, new_text,
                 old_label="before", new_label="after", title="Diff"):
        super().__init__(parent)
        self.t = theme
        self.tints = TINTS["dark" if theme.is_dark else "light"]
        self.old_text = old_text or ""
        self.new_text = new_text or ""
        self.old_label = old_label
        self.new_label = new_label
        self.rows = compute_row_diff(self.old_text, self.new_text)
        self.jumps = changed_positions(self.rows)
        self.jump_at = -1
        self.mode = "split"
        self.title(title)
        self.configure(bg=self.t["bg"])
        self.transient(parent.winfo_toplevel()
                       if parent.winfo_toplevel() is not self else parent)
        self.geometry("980x640")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 980x640 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 980, 640))
        self.minsize(560, 320)

        self._build_header(title)
        self._build_body()
        self._build_footer()
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<F3>", lambda e: self.next_hunk())
        self.bind("<Shift-F3>", lambda e: self.prev_hunk())
        self.bind("<Control-u>", lambda e: self.toggle_mode())
        self.bind("<Control-c>", self._copy_patch)
        self._build_hintbar()
        self.after(60, lambda: self.jump_to(0))
        self._center()

    # ------------------------------------------------------------ chrome
    def _build_footer(self):
        """v2.49 — the summary strip along the bottom edge.

        This method was called since v1.4 but never defined — every
        diff window died with AttributeError the moment it opened
        (the engine below was fine, so the tests never noticed).
        Now it carries its weight: a one-line verdict of what changed.
        """
        t = self.t
        add, dele, mod = diff_stats(self.rows)
        hunks = len(self.jumps)
        text = ("%s → %s   ·   %d rows   ·   +%d −%d%s   ·   "
                "%s" % (self.old_label, self.new_label, len(self.rows),
                        add, dele, " ~%d" % mod if mod else "",
                        ("%d changed hunk%s"
                         % (hunks, "" if hunks == 1 else "s"))
                        if hunks else "no changes"))
        bar = tk.Frame(self, bg=t["header"], height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Label(bar, text=text, bg=t["header"], fg=t["text_muted"],
                 font=(FONT_UI, 8), anchor="w").pack(
            fill=tk.X, padx=12)
        self._footer = bar  # the hint bar packs itself below this

    def _build_hintbar(self):
        """v2.49 — the honest door sign (only really-bound keys)."""
        self.hintbar = hints.hint_bar(
            self, self.t,
            pairs=(("F3", "next change", "F3"),
                   ("Shift+F3", "previous change", "\u21e7F3"),
                   ("Ctrl+U", "split / unified"),
                   ("Ctrl+C", "copy patch")),
            notes=("click \u2039 \u203a to step changes",),
            before=getattr(self, "_footer", None))

    # ------------------------------------------------------------ chrome
    def _center(self):
        try:
            self.update_idletasks()
            w, h = 980, 640
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build_header(self, title):
        t, bar = self.t, tk.Frame(self, bg=self.t["header"], height=46)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⇄  " + title, bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        add, dele, mod = diff_stats(self.rows)
        pills = tk.Frame(bar, bg=t["header"])
        pills.pack(side=tk.LEFT, padx=10)
        tk.Label(pills, text=f"+{add}", bg=self.tints["add_bg"],
                 fg=self.tints["add_word"], font=(FONT_MONO, 9, "bold"),
                 padx=7, pady=2).pack(side=tk.LEFT, padx=2)
        tk.Label(pills, text=f"−{dele}", bg=self.tints["del_bg"],
                 fg=self.tints["del_word"], font=(FONT_MONO, 9, "bold"),
                 padx=7, pady=2).pack(side=tk.LEFT, padx=2)
        if mod:
            tk.Label(pills, text=f"~{mod} mod", bg=self.tints["mod_bg"],
                     fg=t.accent, font=(FONT_MONO, 9, "bold"),
                     padx=7, pady=2).pack(side=tk.LEFT, padx=2)

        # mode toggle
        self.mode_btn = tk.Label(bar, text="Unified view", bg=t["card"],
                                 fg=t["text"], font=(FONT_UI, 9),
                                 cursor="hand2", padx=10, pady=4)
        self.mode_btn.pack(side=tk.RIGHT, padx=(6, 12))
        self.mode_btn.bind("<Button-1>", lambda e: self.toggle_mode())
        copy_all = tk.Label(bar, text="Copy patch", bg=t["card"],
                            fg=t["text_secondary"], font=(FONT_UI, 9),
                            cursor="hand2", padx=10, pady=4)
        copy_all.pack(side=tk.RIGHT)
        copy_all.bind("<Button-1>", self._copy_patch)
        # hunk nav
        nav = tk.Frame(bar, bg=t["header"])
        nav.pack(side=tk.RIGHT, padx=6)
        self.hunk_lbl = tk.Label(nav, text=self._hunk_text(), bg=t["header"],
                                 fg=t["text_muted"], font=(FONT_MONO, 9),
                                 width=9)
        self.hunk_lbl.pack(side=tk.RIGHT, padx=4)
        for glyph, fn in (("‹", self.prev_hunk), ("›", self.next_hunk)):
            b = tk.Label(nav, text=glyph, bg=t["card"], fg=t["text"],
                         font=(FONT_UI, 11, "bold"), cursor="hand2",
                         padx=9, pady=1)
            b.pack(side=tk.RIGHT, padx=2)
            b.bind("<Button-1>", lambda e, f=fn: f())

    def _hunk_text(self):
        if not self.jumps:
            return "no changes"
        return f"{self.jump_at + 1} / {len(self.jumps)}"

    def _build_body(self):
        self.body = tk.Frame(self, bg=self.t["bg"])
        self.body.pack(fill=tk.BOTH, expand=True)
        self._render_split()

    def _clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    # ------------------------------------------------------- split view
    def _render_split(self):
        self._clear_body()
        t, tint = self.t, self.tints
        head = tk.Frame(self.body, bg=t["header"])
        head.pack(fill=tk.X)
        tk.Label(head, text="− " + self.old_label, bg=t["header"],
                 fg=tint["del_word"], font=(FONT_MONO, 9, "bold"),
                 anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True,
                                  padx=12, pady=3)
        tk.Label(head, text="+ " + self.new_label, bg=t["header"],
                 fg=tint["add_word"], font=(FONT_MONO, 9, "bold"),
                 anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True,
                                  padx=12, pady=3)

        pane = tk.Frame(self.body, bg=t["border"])
        pane.pack(fill=tk.BOTH, expand=True)

        def make_pane(side, label):
            wrap = tk.Frame(pane, bg=t["editor"])
            wrap.pack(side=side, fill=tk.BOTH, expand=True)
            gut = tk.Text(wrap, width=5, bg=t["linenum_bg"],
                          fg=t["linenum_fg"], font=(FONT_MONO, 9),
                          relief=tk.FLAT, bd=0, highlightthickness=0,
                          takefocus=0, cursor="arrow")
            gut.pack(side=tk.LEFT, fill=tk.Y)
            txt = tk.Text(wrap, bg=t["editor"], fg=t["text"],
                          font=(FONT_MONO, 10), relief=tk.FLAT, bd=0,
                          wrap=tk.NONE, highlightthickness=0,
                          takefocus=0, cursor="arrow")
            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            for tag, opts in (
                    ("add_bg", {"background": tint["add_bg"]}),
                    ("del_bg", {"background": tint["del_bg"]}),
                    ("mod_bg", {"background": tint["mod_bg"]}),
                    ("add_word", {"foreground": tint["add_word"]}),
                    ("del_word", {"foreground": tint["del_word"]}),
                    ("g_add", {"background": tint["gutter_add"]}),
                    ("g_del", {"background": tint["gutter_del"]}),
                    ("g_mod", {"background": tint["gutter_add"]}),
                    ("same", {})):
                txt.tag_configure(tag, **opts)
                gut.tag_configure(tag, **opts)
            return gut, txt

        self.left_gut, self.left = make_pane(tk.LEFT, self.old_label)
        self.right_gut, self.right = make_pane(tk.RIGHT, self.new_label)
        sb = ttk.Scrollbar(pane, orient=tk.VERTICAL, command=self._sync_scroll)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        for txt in (self.left, self.right):
            txt.configure(yscrollcommand=sb.set)

        for row in self.rows:
            kind_tag = {"same": None, "add": "add_bg", "del": "del_bg",
                        "mod": "mod_bg"}.get(row["kind"])
            # left pane — old side
            if row["kind"] in ("same", "del", "mod"):
                if row["kind"] == "mod":
                    dels = [seg for seg, wk in row["pairs"] if wk == "del"]
                    line = " ".join(dels) if dels else row["text"]
                else:
                    line = row["text"]
                self._put(self.left, self.left_gut, line,
                          row["old"], kind_tag or "same", row["pairs"],
                          which="old")
            else:
                self._put(self.left, self.left_gut, "", None, "same",
                          None, which="old")
            # right pane — new side
            if row["kind"] in ("same", "add", "mod"):
                self._put(self.right, self.right_gut, row["text"],
                          row["new"], kind_tag or "same", row["pairs"],
                          which="new")
            else:
                self._put(self.right, self.right_gut, "", None, "same",
                          None, which="new")
        for txt in (self.left, self.right):
            txt.configure(state=tk.DISABLED)
        for gut in (self.left_gut, self.right_gut):
            gut.configure(state=tk.DISABLED)
        self._focus_text = self.left

    def _put(self, txt, gut, line, lineno, kind_tag, pairs, which="old"):
        """Insert one row into a pane + its gutter, tagging words."""
        txt.insert(tk.END, line + "\n", (kind_tag,))
        num = f"{lineno or '':>4}\n"
        gut.insert(tk.END, num, (kind_tag,))
        if not pairs or line == "":
            return
        for seg, wkind in pairs:
            if wkind == "same" or not seg.strip():
                continue
            # only paint words that belong to this side's text
            if which == "old" and wkind != "del":
                continue
            if which == "new" and wkind != "add":
                continue
            at = line.find(seg)
            if at < 0:
                continue
            idx0 = f"end-2l linestart +{at}c"
            idx1 = f"end-2l linestart +{at + len(seg)}c"
            txt.tag_add("add_word" if wkind == "add" else "del_word",
                        idx0, idx1)

    def _sync_scroll(self, first, last):
        for w in (self.left, self.right, self.left_gut, self.right_gut):
            try:
                w.yview_moveto(first)
            except tk.TclError:
                pass

    # ---------------------------------------------------- unified view
    def _render_unified(self):
        self._clear_body()
        t, tint = self.t, self.tints
        pane = tk.Frame(self.body, bg=t["editor"])
        pane.pack(fill=tk.BOTH, expand=True)
        gut = tk.Text(pane, width=9, bg=t["linenum_bg"],
                      fg=t["linenum_fg"], font=(FONT_MONO, 9),
                      relief=tk.FLAT, bd=0, highlightthickness=0,
                      takefocus=0, cursor="arrow")
        gut.pack(side=tk.LEFT, fill=tk.Y)
        txt = tk.Text(pane, bg=t["editor"], fg=t["text"],
                      font=(FONT_MONO, 10), relief=tk.FLAT, bd=0,
                      wrap=tk.NONE, highlightthickness=0)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(pane, orient=tk.VERTICAL,
                           command=lambda f, l: (txt.yview_moveto(f),
                                                 gut.yview_moveto(f)))
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.configure(yscrollcommand=sb.set)
        gut.configure(yscrollcommand=sb.set)
        txt.tag_configure("add_bg", background=tint["add_bg"])
        txt.tag_configure("del_bg", background=tint["del_bg"])
        txt.tag_configure("mod_bg", background=tint["mod_bg"])
        txt.tag_configure("add_word", foreground=tint["add_word"])
        txt.tag_configure("del_word", foreground=tint["del_word"])
        txt.tag_configure("hunk", background=tint["hunk_bg"],
                          foreground=tint["hunk_fg"])
        gut.tag_configure("add_bg", background=tint["gutter_add"])
        gut.tag_configure("del_bg", background=tint["gutter_del"])
        gut.tag_configure("mod_bg", background=tint["gutter_add"])
        gut.tag_configure("hunk", background=tint["hunk_bg"])

        # build unified patch rows with hunk separators
        old_no = new_no = 0
        prev_kind = None
        for row in self.rows:
            kind = row["kind"]
            if kind == "same":
                old_no += 1
                new_no += 1
                gut.insert(tk.END, f"{old_no:>4} {new_no:>4}\n", "same")
                txt.insert(tk.END, "  " + row["text"] + "\n")
            elif kind == "del":
                old_no += 1
                gut.insert(tk.END, f"{old_no:>4}     \n", "del_bg")
                txt.insert(tk.END, "− " + row["text"] + "\n", "del_bg")
            elif kind == "add":
                new_no += 1
                gut.insert(tk.END, f"     {new_no:>4}\n", "add_bg")
                txt.insert(tk.END, "+ " + row["text"] + "\n", "add_bg")
            else:
                old_no += 1
                new_no += 1
                gut.insert(tk.END, f"{old_no:>4} {new_no:>4}\n", "mod_bg")
                txt.insert(tk.END, "~ " + row["text"] + "\n", "mod_bg")
            prev_kind = kind
        for w in (txt, gut):
            w.configure(state=tk.DISABLED)
        self._focus_text = txt

    # --------------------------------------------------------- actions
    def toggle_mode(self):
        self.mode = "unified" if self.mode == "split" else "split"
        self.mode_btn.config(
            text="Split view" if self.mode == "unified" else "Unified view")
        if self.mode == "split":
            self._render_split()
        else:
            self._render_unified()
        self.after(50, lambda: self.jump_to(self.jump_at))

    def _copy_patch(self, event=None):
        patch = unified_diff_text(self.old_text, self.new_text,
                                  self.old_label, self.new_label)
        self.clipboard_clear()
        self.clipboard_append(patch)
        try:  # v2.49 — the footer echoes the gesture
            self.hunk_lbl.config(text="patch copied")
            self.after(1400, lambda: self.hunk_lbl.config(
                text=self._hunk_text()))
        except Exception:  # noqa: BLE001 — garnish
            pass

    def jump_to(self, idx):
        if not self.jumps:
            self.hunk_lbl.config(text="no changes")
            return
        self.jump_at = max(0, min(idx, len(self.jumps) - 1))
        row = self.jumps[self.jump_at]
        widget = self._active_widget()
        try:
            widget.see(f"{max(1, row - 2)}.0")
            widget.update_idletasks()
        except tk.TclError:
            pass
        self.hunk_lbl.config(text=self._hunk_text())

    def _active_widget(self):
        widget = getattr(self, "_focus_text", None)
        if widget is not None:
            return widget
        return self.left if self.mode == "split" else None

    def next_hunk(self):
        if self.jumps:
            self.jump_to((self.jump_at + 1) % len(self.jumps))

    def prev_hunk(self):
        if self.jumps:
            self.jump_to((self.jump_at - 1) % len(self.jumps))


def show_diff(parent, theme, old_text, new_text, old_label="before",
              new_label="after", title="Diff"):
    """Convenience opener — mirrors the studio's one-call dialog style."""
    return DiffViewer(parent, theme, old_text, new_text, old_label,
                      new_label, title)
