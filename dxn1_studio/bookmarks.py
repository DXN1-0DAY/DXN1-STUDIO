"""DXN1 STUDIO — Persistent bookmarks (DS2).

The editor has always had in-session bookmarks (gutter click, F2 /
Ctrl+F2 / Shift+F2) — close the app and they evaporate. DS2 fixes
that: this module persists bookmarks **per workspace** in
``.dxn1/bookmarks.json`` (a global file is used when no workspace is
open), restores them whenever a file is opened, and adds a
workspace-wide **bookmark browser** with snippet previews.

Shape of the store::

    { "src/app.py": [12, 48, 120], "README.md": [3] }

Keys are workspace-relative POSIX paths; absolute paths (files outside
the workspace) are stored as-is so nothing is ever lost.

Engine is UI-free and testable; ``open_browser`` is the thin shell.
"""

from __future__ import annotations

import json
import os

from . import APP_NAME

WS_STORE = os.path.join(".dxn1", "bookmarks.json")
GLOBAL_STORE = os.path.join(os.path.expanduser("~"), ".dxn1-studio",
                            "bookmarks.json")
MAX_PER_FILE = 500          # safety valve per file
MAX_FILES = 400             # …and across the workspace


def store_path(workspace=None):
    """Where bookmarks live: workspace store, else the global one."""
    if workspace:
        return os.path.join(workspace, WS_STORE)
    return GLOBAL_STORE


def key_for(filepath, workspace=None):
    """Workspace-relative POSIX key for ``filepath`` (abspath outside)."""
    if not filepath:
        return ""
    path = os.path.abspath(filepath)
    if workspace:
        try:
            rel = os.path.relpath(path, workspace)
            if not rel.startswith(".."):
                return rel.replace(os.sep, "/")
        except ValueError:          # different drive on Windows
            pass
    return path.replace(os.sep, "/")


class BookmarkStore:
    """JSON-backed bookmark persistence. Never raises on bad data."""

    def __init__(self, workspace=None):
        self.workspace = os.path.abspath(workspace) if workspace else None
        self.path = store_path(workspace)
        self._data = {}
        self.load()

    # ---- io ----------------------------------------------------------
    def load(self):
        self._data = {}
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                for key, lines in raw.items():
                    if isinstance(key, str) and isinstance(lines, list):
                        clean = sorted({int(n) for n in lines
                                        if isinstance(n, (int, float))
                                        and int(n) >= 1})
                        if clean:
                            self._data[key] = clean[:MAX_PER_FILE]
        except (OSError, ValueError, TypeError):
            self._data = {}         # missing or corrupt: start clean
        return self._data

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            items = list(self._data.items())[:MAX_FILES]   # bounded
            self._data = dict(items)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=1, sort_keys=True)
            os.replace(tmp, self.path)   # atomic on POSIX
            return True
        except (OSError, TypeError, ValueError):
            return False

    # ---- api ----------------------------------------------------------
    def get(self, key):
        return list(self._data.get(key, []))

    def set(self, key, lines):
        if not key:
            return
        clean = sorted({int(n) for n in (lines or [])
                        if isinstance(n, (int, float)) and int(n) >= 1})
        if clean:
            self._data[key] = clean[:MAX_PER_FILE]
        else:
            self._data.pop(key, None)

    def toggle(self, key, line):
        """Add/remove one bookmark; returns True when added."""
        line = max(1, int(line))
        lines = self.get(key)
        if line in lines:
            lines.remove(line)
            added = False
        else:
            lines.append(line)
            added = True
        self.set(key, lines)
        return added

    def clear(self, key):
        self._data.pop(key, None)

    def all(self):
        """{key: [sorted lines]} — files with bookmarks only."""
        return {k: list(v) for k, v in sorted(self._data.items())}

    def count(self):
        return sum(len(v) for v in self._data.values())

    def prune_missing(self, workspace=None):
        """Drop keys whose files no longer exist on disk."""
        root = os.path.abspath(workspace) if workspace else self.workspace
        dropped = []
        for key in list(self._data):
            path = key if os.path.isabs(key) else \
                os.path.join(root or "", key)
            if not os.path.isfile(path):
                del self._data[key]
                dropped.append(key)
        return dropped


def snippet_for(filepath, line, width=64):
    """The text of one line, trimmed — for browser previews. Safe."""
    try:
        if not filepath or not os.path.isfile(filepath):
            return ""
        if os.path.getsize(filepath) > 1024 * 1024:
            return ""
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            for i, text in enumerate(fh, 1):
                if i == line:
                    return text.strip()[:width]
        return ""
    except OSError:
        return ""


# ------------------------------------------------------------------ GUI
_C = {}


def open_browser(master, theme, workspace=None, on_jump=None, on_log=None):
    """Open the workspace bookmark browser.

    ``on_jump(abspath, line)`` decides what "jump" means (the app opens
    the file and goes to the line).
    """
    import tkinter as tk
    from tkinter import ttk

    log = on_log or (lambda m: None)
    ws = os.path.abspath(workspace) if workspace else None
    store = BookmarkStore(ws)
    accent = getattr(theme, "accent", "#7c3aed")
    font = getattr(theme, "font", lambda s=10, w="normal": ("sans-serif", s, w))
    mono = getattr(theme, "mono", lambda s=10, w="normal": ("monospace", s, w))

    for key, val in (
            ("bg", theme["bg"]), ("card", theme["card"]),
            ("header", theme["header"]), ("border", theme["border"]),
            ("text", theme["text"]), ("muted", theme["text_muted"]),
            ("hover", theme["hover"]),
            ("statusbar", theme["statusbar"])):
        _C[key] = val

    win = tk.Toplevel(master)
    win.title("Bookmarks — DS2")
    win.configure(bg=_C["bg"])
    win.transient(master)
    win.geometry("720x520")
    # DS2 v2.63 — width accounting round five: once the
    # build settles, open no narrower (or shorter) than
    # what it actually packed (the 720x520 default is the
    # floor)
    from . import geom as _geom
    win.after_idle(lambda: _geom.fit_to_content(
        win, 720, 520))

    head = tk.Frame(win, bg=_C["header"])
    head.pack(fill=tk.X)
    tk.Label(head, text="BOOKMARKS", bg=_C["header"], fg=_C["text"],
             font=font(13, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
    sub = tk.Label(head, text=ws or "global (no workspace open)",
                   bg=_C["header"], fg=_C["muted"], font=mono(9))
    sub.pack(anchor="w", padx=16, pady=(0, 10))

    wrap = tk.Frame(win, bg=_C["card"], highlightthickness=1,
                    highlightbackground=_C["border"])
    wrap.pack(fill=tk.BOTH, expand=True, padx=16, pady=(12, 6))

    tree = ttk.Treeview(wrap, columns=("line", "snippet"),
                        show="tree headings", height=12)
    try:
        style = ttk.Style()
        style.map("Treeview", background=[("selected", accent)])
        style.configure("Treeview", bg=_C["card"], fg=_C["text"],
                        fieldbackground=_C["card"], rowheight=24,
                        font=mono(9))
        style.configure("Treeview.Heading", bg=_C["header"], fg=_C["text"],
                        font=font(9, "bold"))
    except Exception:               # noqa: BLE001 — theming is best-effort
        pass
    tree.heading("#0", text="File")
    tree.heading("line", text="Line")
    tree.heading("snippet", text="Content")
    tree.column("#0", width=240, anchor="w")
    tree.column("line", width=60, anchor="e", stretch=False)
    tree.column("snippet", width=380, anchor="w")
    vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview,
                        style="TS2.Vertical.TScrollbar")
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 0), pady=2)
    vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=2)

    foot = tk.Frame(win, bg=_C["statusbar"])
    foot.pack(fill=tk.X, side=tk.BOTTOM)
    info = tk.Label(foot, text="", bg=_C["statusbar"], fg=accent,
                    font=font(9))
    info.pack(side=tk.LEFT, padx=12)

    def resolve(key):
        return key if os.path.isabs(key) else os.path.join(ws or "", key)

    def selected_row():
        sel = tree.selection()
        if not sel:
            return None
        item = sel[0]
        parent = tree.parent(item)
        if not parent:              # a file group row
            return None
        line = int(tree.set(item, "line"))
        key = tree.item(parent, "text")
        return key, line

    def do_jump(_event=None):
        row = selected_row()
        if row and on_jump:
            key, line = row
            on_jump(resolve(key), line)

    def do_remove():
        row = selected_row()
        if not row:
            return
        key, line = row
        store.toggle(key, line)
        store.save()
        refresh()

    def do_clear_file():
        row = selected_row()
        key = row[0] if row else None
        if key is None:
            sel = tree.selection()
            if sel and not tree.parent(sel[0]):
                key = tree.item(sel[0], "text")
        if key is None:
            return
        store.clear(key)
        store.save()
        refresh()
        log("bookmarks: cleared %s" % key)

    def refresh():
        tree.delete(*tree.get_children())
        data = store.all()
        total = 0
        for key, lines in data.items():
            abspath = resolve(key)
            fid = tree.insert("", tk.END, text=key,
                              open=len(lines) <= 6)
            for ln in lines:
                total += 1
                tree.insert(fid, tk.END, values=(
                    ln, snippet_for(abspath, ln)))
        info.config(text="%d bookmark%s in %d file%s" % (
            total, "" if total == 1 else "s",
            len(data), "" if len(data) == 1 else "s"))
        if not data:
            tree.insert("", tk.END, values=("", "no bookmarks yet — click a "
                        "line number in the gutter or press Ctrl+F2"))

    for text_, cmd in (("Jump", do_jump), ("Remove", do_remove),
                       ("Clear file", do_clear_file), ("Refresh", refresh)):
        tk.Button(foot, text=text_, command=cmd, bg=_C["card"],
                  fg=_C["text"], activebackground=_C["hover"],
                  activeforeground=_C["text"], relief=tk.FLAT,
                  font=font(9), padx=10, pady=3).pack(
            side=tk.RIGHT, padx=(0, 8), pady=6)

    tree.bind("<Double-1>", do_jump)
    tree.bind("<Return>", do_jump)
    win.bind("<Escape>", lambda e: win.destroy())
    # v2.48 — the honest door sign (only keys the browser really binds)
    from . import hints
    hints.hint_bar(win,
                   {"header": _C["statusbar"], "text_muted": _C["muted"],
                    "accent": accent},
                   pairs=(("Return", "jump", "Enter"),),
                   notes=("double-click a row to jump",),
                   before=foot)
    # expose internals — tests and plugins may drive the browser
    win.tree = tree
    win.do_jump = do_jump
    win.do_remove = do_remove
    win.do_clear_file = do_clear_file
    win.refresh = refresh
    win.store = store
    refresh()
    return win
