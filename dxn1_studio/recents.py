"""DXN1 STUDIO — Recent files picker (DS2).

The File menu already lists recent files, but muscle memory wants a
Quick-Open-style popup: type a few letters of the file name, arrows
to choose, Enter to jump. This module adds that popup on top of the
existing ``recent_files`` config list (no new persistence — it rides
what the app already tracks).

Ranking (same spirit as the symbol picker): basename prefix beats
path prefix beats word-start beats substring; basename matches rank
above full-path matches so typing ``util`` finds ``src/util.py``
before ``src/util_tests.py``… by relevance, not alphabet.

Engine is UI-free and testable; ``RecentPicker`` is the thin shell.
"""

from __future__ import annotations

import os

MAX_SHOWN = 12          # keep in sync with app.py's recents cap


def load_recents(config, must_exist=True):
    """Normalized, de-duplicated recent-file list from a config object.

    Accepts anything with ``.get(key, default)`` (the app config or the
    ``_Cfg`` test shim). Entries are checked for existence when
    ``must_exist`` is true, absolute-ised, and capped at MAX_SHOWN.
    """
    try:
        raw = config.get("recent_files") or []
    except Exception:               # noqa: BLE001 — config is defensive
        raw = []
    out, seen = [], set()
    for item in raw:
        if not item or not isinstance(item, str):
            continue
        path = os.path.abspath(os.path.expanduser(item))
        if path in seen:
            continue
        if must_exist and not os.path.isfile(path):
            continue
        seen.add(path)
        out.append(path)
        if len(out) >= MAX_SHOWN:
            break
    return out


def _score(path, q):
    """Relevance of query ``q`` for one path. Higher wins; 0 = no match."""
    base = os.path.basename(path)
    lb, lp = base.lower(), path.lower()
    # exact basename hit — unbeatable
    if lb == q:
        return 1000
    score = 0
    if lb.startswith(q):
        score = 500
    elif lp.startswith(q):
        score = 400
    elif "/" + q in lp or os.sep + q in lp:
        score = 380                 # right after a directory separator
    elif q in lb:
        score = 300
    elif q in lp:
        score = 200
    else:
        # in-order subsequence fallback on the basename, weakest match
        it = iter(lb)
        if all(ch in it for ch in q):
            score = 100
    if not score:
        return 0
    # shorter basenames break ties upward (closer to the query)
    return score * 1000 - min(len(base), 999)


def filter_recents(recents, query):
    """Ranked list for the picker. Empty query = original order."""
    q = (query or "").strip().lower()
    if not q:
        return list(recents)
    scored = [(p, _score(p, q)) for p in recents]
    hits = [(s, p) for p, s in scored if s > 0]
    hits.sort(key=lambda t: (-t[0], t[1]))
    return [p for _s, p in hits]


def display_row(path, root=None):
    """(basename, dirname) row labels; dirname relative to ``root``."""
    base = os.path.basename(path)
    d = os.path.dirname(path)
    if root:
        try:
            rel = os.path.relpath(d, root)
            if not rel.startswith(".."):
                d = rel if rel != "." else "."
        except ValueError:          # different drive on Windows
            pass
    return base, d


# ------------------------------------------------------------------ GUI
_C = {}


class RecentPicker:
    """Type-ahead popup over the recents list — arrows/Enter/Esc."""

    def __init__(self, master, theme, recents, on_open, root=None,
                 on_log=None):
        import tkinter as tk

        self.tk = tk
        self.accent = getattr(theme, "accent", "#7c3aed")
        self.accent_soft = getattr(theme, "accent_soft", self.accent)
        font = getattr(theme, "font",
                       lambda s=10, w="normal": ("sans-serif", s, w))
        mono = getattr(theme, "mono",
                       lambda s=10, w="normal": ("monospace", s, w))
        self.on_open = on_open or (lambda p: None)
        self.recents = list(recents)
        self.root_dir = root
        self.on_log = on_log or (lambda m: None)
        self.selected = 0

        for key, val in (
                ("bg", theme["bg"]), ("card", theme["card"]),
                ("header", theme["header"]), ("border", theme["border"]),
                ("text", theme["text"]), ("muted", theme["text_muted"]),
                ("hover", theme["hover"]),
                ("input", theme.get("overlay") or theme["card"])):
            _C[key] = val

        self.win = tk.Toplevel(master)
        self.win.title("Recent files")
        self.win.configure(bg=_C["bg"])
        self.win.transient(master)
        self.win.resizable(False, False)
        self.win.bind("<Escape>", lambda e: self._close())

        self.entry = tk.Entry(self.win, bg=_C["input"], fg=_C["text"],
                              insertbackground=_C["text"], relief=tk.FLAT,
                              font=mono(11), highlightthickness=1,
                              highlightbackground=_C["border"],
                              highlightcolor=self.accent)
        self.entry.pack(fill=tk.X, padx=14, pady=(14, 6), ipady=7)
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Down>", lambda e: self._move(1))
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Return>", lambda e: self._pick())
        self.entry.bind("<Escape>", lambda e: self._close())

        self.list_frame = tk.Frame(self.win, bg=_C["bg"])
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 10))
        self.rows = []
        self.shown = list(self.recents)   # initial view: full recents list

        self._render()
        # v2.48 — the honest door sign (arrows/Enter live on the entry)
        from . import hints
        hints.hint_bar(self.win,
                       {"header": _C["card"], "text_muted": _C["muted"],
                        "accent": self.accent},
                       pairs=(("Up", "move", "\u2191\u2193"),
                              ("Return", "open", "Enter")),
                       notes=("type to filter",),
                       before=self.list_frame)
        self.win.update_idletasks()
        w = 560
        h = min(520, max(160, self.win.winfo_reqheight()))
        try:
            x = self.win.master.winfo_rootx() + \
                (self.win.master.winfo_width() - w) // 2
            y = self.win.master.winfo_rooty() + 90
        except Exception:           # noqa: BLE001
            x = y = 60
        self.win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self.entry.focus_set()

    # ---- behaviour ---------------------------------------------------
    def _close(self):
        try:
            self.win.destroy()
        except Exception:           # noqa: BLE001
            pass

    def _on_type(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        self.shown = filter_recents(self.recents, self.entry.get())
        self.selected = 0
        self._render()

    def _move(self, delta):
        if not self.shown:
            return
        self.selected = (self.selected + delta) % len(self.shown)
        self._render()

    def _pick(self):
        if 0 <= self.selected < len(self.shown):
            path = self.shown[self.selected]
            self._close()
            try:
                self.on_open(path)
            except Exception as exc:    # noqa: BLE001 — never crash the UI
                self.on_log("recent files: open failed — %s" % exc)

    # ---- rendering ---------------------------------------------------
    def _render(self):
        for row in self.rows:
            try:
                row.destroy()
            except Exception:       # noqa: BLE001
                pass
        self.rows = []
        if not self.recents:
            lbl = self.tk.Label(
                self.list_frame,
                text="No recent files yet — open a file and it will "
                     "appear here.",
                bg=_C["bg"], fg=_C["muted"], font=("sans-serif", 10),
                wraplength=520, justify="left")
            lbl.pack(anchor="w", padx=10, pady=14)
            self.rows.append(lbl)
            self.shown = []
            return
        if not self.shown:
            lbl = self.tk.Label(self.list_frame,
                                text="no recents match — try fewer letters",
                                bg=_C["bg"], fg=_C["muted"],
                                font=("sans-serif", 10))
            lbl.pack(anchor="w", padx=10, pady=10)
            self.rows.append(lbl)
            return
        for i, path in enumerate(self.shown):
            base, d = display_row(path, self.root_dir)
            active = i == self.selected
            row = self.tk.Frame(self.list_frame,
                                bg=_C["hover"] if active else _C["bg"])
            row.pack(fill=self.tk.X, padx=2, pady=1)
            dot = self.tk.Label(row, text="›" if active else " ",
                                bg=row["bg"],
                                fg=self.accent if active else _C["muted"],
                                font=("sans-serif", 11, "bold"), width=2)
            dot.pack(side="left")
            name = self.tk.Label(row, text=base, bg=row["bg"],
                                 fg=_C["text"],
                                 font=("sans-serif", 11,
                                       "bold" if active else "normal"))
            name.pack(side="left")
            self.tk.Label(row, text="  " + d, bg=row["bg"], fg=_C["muted"],
                          font=("sans-serif", 9)).pack(
                side="left", padx=(4, 0))
            row.bind("<Button-1>", lambda e, idx=i: self._pick_at(idx))
            for w_ in (dot, name):
                w_.bind("<Button-1>", lambda e, idx=i: self._pick_at(idx))
            self.rows.append(row)

    def _pick_at(self, idx):
        self.selected = idx
        self._pick()


def open_recents(master, theme, config, on_open, root=None, on_log=None):
    """Open the picker. ``root`` = workspace for relative path display."""
    recents = load_recents(config)
    return RecentPicker(master, theme, recents, on_open, root=root,
                        on_log=on_log)
