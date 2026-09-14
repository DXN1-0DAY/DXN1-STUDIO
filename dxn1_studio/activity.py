"""DS2 v2.44 — the studio keeps its receipts.

Toasts auto-dismiss after ~3.4 seconds and were gone forever: an
error you looked away from, a "copied" confirmation, a snapshot
acknowledgement. The Activity log archives every notification in a
ring buffer (newest first, capped) and opens them in one themed,
searchable window — click a row to copy the message, Clear to wipe
the slate.

DS2 v2.45 — the receipts survive the night: the ring saves itself
to disk (atomic write, corrupt-file fallback) and reloads at boot;
entries from a previous session show under a "since last time"
divider with relative stamps ("2m ago").

Pure engine first (`ActivityLog`), window second (`open_activity`),
same one-lane-one-module rule as the rest of DS2.
"""
import json
import os
import time as _time
import tkinter as tk

FONT_UI = "TkDefaultFont"
FONT_MONO = "TkFixedFont"

_KIND_DOT = {"success": "#3fb950", "error": "#f85149", "info": None}


class ActivityLog:
    """A capped ring of recent notifications, newest first.

    Every entry is a plain dict — ``message``, ``kind``, ``t`` — so
    tests and callers can inspect it without widgets. Never raises
    on add: a logging lane must not be able to break the lane that
    produced the event."""

    def __init__(self, cap=100):
        self.cap = max(1, int(cap))
        self._entries = []

    def add(self, message, kind="info", now=None):
        """Record one notification; trims to ``cap``. Returns the
        entry dict (handy for tests). New entries belong to the
        current session (``prev=False``) — loaded ones don't."""
        try:
            entry = {"message": str(message or ""),
                     "kind": str(kind or "info"),
                     "t": float(now if now is not None
                                else _time.time()),
                     "prev": False}
            self._entries.insert(0, entry)
            del self._entries[self.cap:]
            return entry
        except Exception:  # noqa: BLE001 — never break the caller
            return None

    def entries(self):
        """A tuple copy, newest first."""
        return tuple(self._entries)

    def count(self):
        return len(self._entries)

    def clear(self):
        """Wipe the slate (the window's Clear button)."""
        self._entries = []

    def filtered(self, query):
        """Entries whose message contains ``query`` (case-insensitive
        substring — the same first pass `help <q>` uses). An empty
        query returns everything, never None."""
        q = str(query or "").strip().lower()
        if not q:
            return list(self._entries)
        return [e for e in self._entries
                if q in str(e.get("message", "")).lower()]

    # ------------------------------------------------- DS2 v2.45 persistence
    def to_list(self):
        """Plain-dict copies of every entry (for the JSON file)."""
        return [dict(e) for e in self._entries]

    @classmethod
    def from_list(cls, items, cap=100):
        """Rebuild a ring from a saved list; every loaded entry is
        marked ``prev=True`` (it belongs to a previous session).
        Malformed rows are skipped honestly; order is trusted (the
        file was written newest-first)."""
        log = cls(cap=cap)
        for it in (items or []):
            try:
                if not isinstance(it, dict):
                    continue
                log._entries.append({
                    "message": str(it.get("message", "")),
                    "kind": str(it.get("kind", "info")),
                    "t": float(it.get("t", 0.0)),
                    "prev": True})
            except Exception:  # noqa: BLE001 — skip the bad row
                continue
        del log._entries[log.cap:]
        return log


def format_time(t):
    """Local HH:MM:SS for one entry timestamp (never raises)."""
    try:
        return _time.strftime("%H:%M:%S", _time.localtime(float(t)))
    except Exception:  # noqa: BLE001 — garnish
        return ""


def rel_time(t, now=None):
    """DS2 v2.45 — a relative stamp for one entry: "just now",
    "2m ago", "3h ago", "5d ago". Pure and testable; a future or
    unparseable timestamp returns "" (the row just shows the dot)."""
    try:
        t = float(t)
        now = float(now if now is not None else _time.time())
        d = now - t
        if d < 0:
            return ""
        if d < 10:
            return "just now"
        if d < 3600:
            return "%dm ago" % max(1, int(d // 60))
        if d < 86400:
            return "%dh ago" % int(d // 3600)
        return "%dd ago" % int(d // 86400)
    except Exception:  # noqa: BLE001 — garnish
        return ""


# ------------------------------------------------------- DS2 v2.45 disk IO
_ACT_VERSION = 1


def save_json(log, path):
    """Atomically write the ring to ``path`` (tmp + os.replace — the
    same pattern Config.save uses, so a crash mid-write can never
    tear the file). Returns True on success, never raises."""
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"version": _ACT_VERSION,
                       "entries": log.to_list()}, fh)
        os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001 — a full disk must not break a toast
        return False


def load_json(path, cap=100):
    """Load the ring from ``path``; missing or corrupt file returns
    None and the caller keeps its own (empty) log. Never raises."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        items = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return None
        return ActivityLog.from_list(items, cap=cap)
    except Exception:  # noqa: BLE001 — corrupt receipts are not fatal
        return None


def open_activity(master, theme, log, on_copy=None, on_change=None):
    """Open the Activity window: every recent notification, live-
    filtered, click-to-copy, current session above a "since last
    time" divider with relative stamps. ``on_change`` fires after
    Clear so the caller can persist the wiped ring. Returns the
    Toplevel so callers (tests, smoke) can inspect it. Best-effort
    by contract."""
    win = tk.Toplevel(master)
    win.title("Activity")
    win.configure(bg=theme["card"])
    win.transient(master)
    win.geometry("620x480")
    win.minsize(440, 320)

    wrap = tk.Frame(win, bg=theme["card"], highlightthickness=1,
                    highlightbackground=theme["card_border"])
    wrap.pack(fill=tk.BOTH, expand=True)

    head = tk.Frame(wrap, bg=theme["card"])
    head.pack(fill=tk.X, padx=14, pady=(14, 6))
    tk.Label(head, text="ACTIVITY", bg=theme["card"], fg=theme["text"],
             font=(FONT_UI, 12, "bold")).pack(side=tk.LEFT)
    count_lbl = tk.Label(head, text="0 events", bg=theme["card"],
                         fg=theme["text_muted"], font=(FONT_UI, 9))
    count_lbl.pack(side=tk.RIGHT)
    clear_btn = tk.Label(head, text="Clear", bg=theme["card"],
                         fg=theme["text_secondary"], cursor="hand2",
                         font=(FONT_UI, 9))
    clear_btn.pack(side=tk.RIGHT, padx=(0, 12))

    searchrow = tk.Frame(wrap, bg=theme["card"])
    searchrow.pack(fill=tk.X, padx=14, pady=(0, 8))
    var = tk.StringVar(value="")
    entry = tk.Entry(searchrow, textvariable=var, bg=theme["editor"],
                     fg=theme["text"], insertbackground=theme["text"],
                     relief=tk.FLAT, font=(FONT_UI, 10),
                     highlightthickness=1,
                     highlightbackground=theme["border"],
                     highlightcolor=theme.accent)
    entry.pack(fill=tk.X, ipady=4)
    entry.insert(0, "")
    tk.Label(searchrow, text="filter — substring, case-insensitive",
             bg=theme["card"], fg=theme["text_muted"],
             font=(FONT_UI, 8), anchor="w").pack(fill=tk.X, pady=(2, 0))

    body = tk.Frame(wrap, bg=theme["card"])
    body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 10))
    canvas = tk.Canvas(body, bg=theme["card"], highlightthickness=0)
    sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = tk.Frame(canvas, bg=theme["card"])
    canvas.create_window((0, 0), window=inner, anchor="nw")

    empty_lbl = None

    def _copy(message):
        try:
            win.clipboard_clear()
            win.clipboard_append(message)
        except Exception:  # noqa: BLE001 — clipboard is garnish
            pass
        try:
            if on_copy:
                on_copy(message)
        except Exception:  # noqa: BLE001 — the callback owns itself
            pass

    def _refilter(_event=None):
        nonlocal empty_lbl
        try:
            empty_lbl.destroy()
        except Exception:  # noqa: BLE001 — first pass has nothing yet
            pass
        empty_lbl = None
        for child in inner.winfo_children():
            child.destroy()
        hits = log.filtered(var.get())
        count_lbl.config(text="%d event%s"
                         % (len(hits), "" if len(hits) == 1 else "s"))
        if not hits:
            empty_lbl = tk.Label(
                inner,
                text="nothing here — the studio whispers when it does",
                bg=theme["card"], fg=theme["text_muted"],
                font=(FONT_UI, 10), anchor="w")
            empty_lbl.pack(fill=tk.X, padx=14, pady=12)
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            return
        prev_seen = False
        for entry in hits:
            # v2.45: a "since last time" divider between this
            # session's receipts and the loaded ones
            if not prev_seen and entry.get("prev"):
                prev_seen = True
                div = tk.Frame(inner, bg=theme["card"])
                div.pack(fill=tk.X, padx=10, pady=(6, 2))
                tk.Frame(div, bg=theme["border"], height=1).pack(
                    fill=tk.X)
                tk.Label(div, text="— since last time —",
                         bg=theme["card"], fg=theme["text_muted"],
                         font=(FONT_UI, 8)).pack(pady=(2, 0))
            dot_color = _KIND_DOT.get(entry.get("kind", "info"),
                                      theme.accent)
            row = tk.Frame(inner, bg=theme["card"], cursor="hand2")
            row.pack(fill=tk.X, padx=10, pady=1)
            dot = tk.Label(row, text="●", bg=theme["card"],
                           fg=dot_color or theme.accent,
                           font=(FONT_UI, 9), width=2)
            dot.pack(side=tk.LEFT)
            when = tk.Label(row, text=rel_time(entry.get("t")),
                            bg=theme["card"], fg=theme["text_muted"],
                            font=(FONT_UI, 8), width=9, anchor="w")
            when.pack(side=tk.LEFT, padx=(0, 6))
            msg = tk.Label(row,
                           text=str(entry.get("message", "")),
                           bg=theme["card"], fg=theme["text"],
                           font=(FONT_UI, 9), anchor="w")
            msg.pack(side=tk.LEFT, fill=tk.X, expand=True)
            for w in (row, dot, when, msg):
                w.bind("<Button-1>",
                       lambda _e, m=str(entry.get("message", "")):
                       _copy(m))
                w.bind("<Enter>", lambda _e, r=row: r.config(
                    bg=theme["hover"]))
                w.bind("<Leave>", lambda _e, r=row: r.config(
                    bg=theme["card"]))
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    var.trace_add("write", lambda *_a: _refilter())
    entry.bind("<KeyRelease>", _refilter)

    def _wipe(_event=None):
        log.clear()
        _refilter()
        try:
            if on_change:
                on_change()
        except Exception:  # noqa: BLE001 — the callback owns itself
            pass

    clear_btn.bind("<Button-1>", _wipe)

    _refilter()
    try:
        entry.focus_set()
    except Exception:  # noqa: BLE001 — focus is garnish
        pass
    return win
