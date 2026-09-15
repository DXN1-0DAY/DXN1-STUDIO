"""DXN1 STUDIO — Scratchpad.

A persistent, always-available jot buffer. Every workspace (and a
global one for when no workspace is open) gets a ``scratch.md`` that
survives restarts. Open it from the palette, type, close — auto-saved
every keystroke-burst and on close.

One idea per moment: the buffer is plain Markdown so it works
everywhere, and a small stamp helper inserts a timestamped line for
quick logging (``Ctrl+Enter`` inserts ``- [HH:MM] ``).
"""

from __future__ import annotations

import os
import time

from . import APP_NAME
from . import hints

GLOBAL_SCRATCH = os.path.join(os.path.expanduser("~"), ".dxn1-studio",
                              "scratch.md")
WS_SCRATCH = os.path.join(".dxn1", "scratch.md")

HEADER = """<!-- {app} scratchpad — auto-saved. Free-format notes. -->
<!-- Ctrl+Enter stamps a new dated bullet. -->
"""


def scratch_path(workspace=None):
    """Workspace scratchpad if a workspace is open, else the global one."""
    if workspace:
        return os.path.join(workspace, WS_SCRATCH)
    return GLOBAL_SCRATCH


def load_scratch(workspace=None):
    path = scratch_path(workspace)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return HEADER.format(app=APP_NAME)


def save_scratch(text, workspace=None):
    path = scratch_path(workspace)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def stamp_line():
    """`- [HH:MM] ` — drop-in prefix for quick log entries."""
    return f"- [{time.strftime('%H:%M')}] "


def append_entry(text, workspace=None):
    """Append a timestamped bullet (creates the file on demand)."""
    body = load_scratch(workspace)
    if not body.endswith("\n"):
        body += "\n"
    body += stamp_line() + text.rstrip("\n") + "\n"
    save_scratch(body, workspace)
    return body


# --------------------------------------------------------------------- GUI
_SC_C = {"bg": "#0d1117", "border": "#232c3d", "text": "#e6edf3",
         "secondary": "#9aa7b8", "muted": "#6e7a8a", "editor": "#0a0e14",
         "saved": "#3fb950"}


def open_scratchpad(master, theme, config=None, workspace=None,
                    on_log=None):
    """Open the scratchpad window (palette entry point)."""
    return Scratchpad(master, theme, workspace, on_log=on_log)


class Scratchpad:
    """Borderless-feeling editor window with autosave + stamping."""

    def __init__(self, master, theme, workspace=None, on_log=None):
        import tkinter as tk

        self.tk = tk
        self.workspace = workspace
        self.accent = getattr(theme, "accent", "#7c3aed")
        self.on_log = on_log or (lambda m: None)
        self._after_id = None

        self.win = tk.Toplevel(master)
        self.win.title(f"{APP_NAME} — Scratchpad")
        self.win.configure(bg=_SC_C["bg"])
        self.win.transient(master)
        self.win.geometry("560x520")
        # DS2 v2.62 — width accounting round four: once the build
        # settles, open no narrower (or shorter) than what it
        # actually packed (the 560x520 default is the floor)
        from . import geom as _geom
        self.win.after_idle(lambda: _geom.fit_to_content(
            self.win, 560, 520))
        self.win.bind("<Escape>", lambda e: self._close())

        head = tk.Frame(self.win, bg=_SC_C["bg"])
        head.pack(fill="x", padx=14, pady=(12, 0))
        where = "workspace" if workspace else "global"
        tk.Label(head, text="Scratchpad", bg=_SC_C["bg"], fg=_SC_C["text"],
                 font=("sans-serif", 13, "bold")).pack(side="left")
        tk.Label(head, text=f"· {where} · auto-saved", bg=_SC_C["bg"],
                 fg=_SC_C["muted"], font=("sans-serif", 9)
                 ).pack(side="left", padx=(8, 0))
        close = tk.Label(head, text="✕", bg=_SC_C["bg"], fg=_SC_C["muted"],
                         font=("sans-serif", 11, "bold"), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self._close())

        self.status = tk.Label(self.win, text="", bg=_SC_C["bg"],
                               fg=_SC_C["saved"], font=("sans-serif", 8))
        self.status.pack(anchor="e", padx=14)

        self.text = tk.Text(self.win, bg=_SC_C["editor"], fg=_SC_C["text"],
                            insertbackground=_SC_C["text"],
                            relief="flat", bd=0, wrap="word",
                            font=("monospace", 10),
                            highlightthickness=1,
                            highlightbackground=_SC_C["border"],
                            highlightcolor=self.accent, undo=True)
        from .theme import make_scrollbar
        _sb = make_scrollbar(self.win, _SC_C, "vertical",
                             command=self.text.yview)
        self.text.configure(yscrollcommand=_sb.set)
        _sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True, padx=14, pady=(4, 12))
        self.text.insert("1.0", load_scratch(workspace))
        self.text.bind("<KeyRelease>", self._schedule_save)
        self.text.bind("<Control-Return>", self._stamp)

        # v2.49 — the honest door sign replaces the hand-written hint
        # label: same promise, now verified against the real bindings.
        self.win._scratch_hint = hints.hint_bar(
            self.win, theme,
            pairs=(("Ctrl+Return", "stamp a new bullet"),),
            notes=("auto-saved as you type",))

        self.win.protocol("WM_DELETE_WINDOW", self._close)

    def _schedule_save(self, event=None):
        if self._after_id:
            try:
                self.win.after_cancel(self._after_id)
            except Exception:           # noqa: BLE001
                pass
        self._after_id = self.win.after(600, self._save)

    def _save(self):
        try:
            save_scratch(self.text.get("1.0", "end-1c"),
                         self.workspace)
            self.status.config(
                text=f"saved {time.strftime('%H:%M:%S')}",
                fg=_SC_C["saved"])
        except OSError as exc:
            self.status.config(text=f"save failed: {exc}", fg="#f85149")

    def _stamp(self, event=None):
        self.text.mark_set("insert", "end-1c")
        self.text.insert("insert", "\n" + stamp_line())
        self.text.see("insert")
        self._schedule_save()
        return "break"

    def _close(self):
        self._save()
        try:
            self.win.destroy()
        except Exception:               # noqa: BLE001
            pass
