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

DS2 v2.46 — the receipts go where you send them: `export_text` /
`export_file` turn the ring into a plain chronological text file
(oldest first, one receipt per line), the window grows kind
filters (click a dot to hide that kind — unnamed kinds always
show, so nothing can silently vanish) and Copy all / Save as
file… buttons.

DS2 v2.47 — the receipts in your format: `export_csv` /
`export_json` / `export_to` write the diary as CSV or JSON, the
Save-as dialog and the `activity export` verb both follow the
file's extension (.json / .csv / text), and a muted toast kind
keeps its receipt while the screen stays quiet.

Pure engine first (`ActivityLog`), window second (`open_activity`),
same one-lane-one-module rule as the rest of DS2.
"""
import csv
import io
import json
import os
import time as _time
import tkinter as tk
from tkinter import filedialog

FONT_UI = "TkDefaultFont"
FONT_MONO = "TkFixedFont"

_KIND_DOT = {"success": "#3fb950", "error": "#f85149", "info": None}

# DS2 v2.46 — the three kinds the studio actually whispers. The kind
# filter can only hide these; anything else (a future kind, a plugin's
# kind, a typo) always shows, because you cannot re-show what you
# cannot name.
_CANONICAL_KINDS = ("success", "error", "info")


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

    def filtered(self, query, kinds=None):
        """Entries whose message contains ``query`` (case-insensitive
        substring — the same first pass `help <q>` uses). An empty
        query returns everything, never None.

        DS2 v2.46: ``kinds`` optionally narrows by kind — only the
        canonical trio can be hidden; an entry whose kind is not one
        of them always passes (you cannot re-show what you cannot
        name, so nothing silently vanishes). ``None`` means no kind
        filter at all."""
        q = str(query or "").strip().lower()
        if q:
            base = [e for e in self._entries
                    if q in str(e.get("message", "")).lower()]
        else:
            base = list(self._entries)
        if kinds is None:
            return base
        try:
            allowed = frozenset(str(k) for k in kinds)
        except Exception:  # noqa: BLE001 — a broken filter shows all
            return base
        return [e for e in base
                if str(e.get("kind", "info")) not in _CANONICAL_KINDS
                or str(e.get("kind", "info")) in allowed]

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


# ---------------------------------------------------- DS2 v2.46 export lane
def stamp_full(t):
    """A full local stamp for one entry: "2026-09-14 19:12:03".
    Pure and testable; junk returns "" (the export line then just
    skips the bracket)."""
    try:
        return _time.strftime("%Y-%m-%d %H:%M:%S",
                              _time.localtime(float(t)))
    except Exception:  # noqa: BLE001 — garnish
        return ""


def export_text(entries):
    """The receipts as one plain text block, oldest first — sorted
    by their timestamps, so the file reads like a diary no matter
    what order the ring held (the list view trusts the ring's order;
    a file on disk should not). One receipt per line:
    ``[stamp] kind    message``; entries with an unstampable time
    keep their line anyway. Empty in, empty out — never raises."""
    try:
        rows = list(entries or [])
    except Exception:  # noqa: BLE001 — a broken caller gets ""
        return ""

    def _t(e):
        try:
            return float(e.get("t", 0.0))
        except Exception:  # noqa: BLE001 — junk time sinks to the top
            return 0.0

    rows.sort(key=_t)
    lines = []
    for e in rows:
        try:
            msg = str(e.get("message", ""))
            kind = (str(e.get("kind", "info")) or "info").ljust(7)
            st = stamp_full(e.get("t"))
            lines.append("[%s] %s  %s" % (st, kind, msg) if st
                         else "%s  %s" % (kind, msg))
        except Exception:  # noqa: BLE001 — skip the bad row
            continue
    return "\n".join(lines)


def export_file(log, path):
    """Write every receipt to ``path`` as the plain text diary (kept
    for callers that always want text — the window and the verbs use
    `export_to`, where the format follows the file extension).
    Returns the path on success, None on failure; never raises."""
    return export_to(log, path, fmt="text")


def export_csv(entries):
    """DS2 v2.47 — the receipts as CSV: a ``stamp,kind,message``
    header, then one row per receipt, sorted oldest first exactly
    like the text diary, quoted by the csv module so a message with
    a comma or a newline survives the round-trip. Empty in, honest
    header-only out — never raises."""
    try:
        rows = list(entries or [])
    except Exception:  # noqa: BLE001 — a broken caller gets the header
        rows = []

    def _t(e):
        try:
            return float(e.get("t", 0.0))
        except Exception:  # noqa: BLE001 — junk time sinks to the top
            return 0.0

    rows.sort(key=_t)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["stamp", "kind", "message"])
    for e in rows:
        try:
            msg = str(e.get("message", ""))
            kind = str(e.get("kind", "info")) or "info"
            w.writerow([stamp_full(e.get("t")), kind, msg])
        except Exception:  # noqa: BLE001 — skip the bad row
            continue
    return buf.getvalue()


def export_json(entries):
    """DS2 v2.47 — the receipts as JSON: the same shape the ring
    persists (version + entries, newest-first preserved), plus an
    ``exported`` stamp, so an export round-trips through
    `load_json`. Never raises."""
    try:
        rows = [dict(e) for e in (entries or [])]
    except Exception:  # noqa: BLE001 — a broken caller exports empty
        rows = []
    return json.dumps({"version": _ACT_VERSION,
                       "exported": stamp_full(_time.time()),
                       "entries": rows}, indent=2)


def export_to(log, path, fmt=None):
    """DS2 v2.47 — write every receipt to ``path``, the format
    following the file extension: ``.json`` → the JSON snapshot,
    ``.csv`` → the CSV sheet, anything else → the plain text diary.
    An explicit ``fmt`` ("json" / "csv" / "text") overrides the
    extension. Atomic write (tmp + os.replace). Returns the path on
    success, None on failure; never raises."""
    try:
        f = str(fmt or "").strip().lower()
        if f not in ("json", "csv", "text"):
            ext = os.path.splitext(str(path))[1].lower()
            f = ("json" if ext == ".json"
                 else "csv" if ext == ".csv" else "text")
        if f == "json":
            text = export_json(log.entries())
        elif f == "csv":
            text = export_csv(log.entries())
        else:
            text = export_text(log.entries())
            if text:
                text += "\n"
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
        return path
    except Exception:  # noqa: BLE001 — a full disk must not break a click
        return None


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


def open_activity(master, theme, log, on_copy=None, on_change=None,
                  export_dir=None, on_export=None):
    """Open the Activity window: every recent notification, live-
    filtered, click-to-copy, current session above a "since last
    time" divider with relative stamps. ``on_change`` fires after
    Clear so the caller can persist the wiped ring.

    DS2 v2.46: kind dots filter the list by kind (unnamed kinds
    always show), "Copy all" puts every receipt on the clipboard,
    and "Save as file…" writes the whole ring to a plain text file
    (``export_dir`` seeds the dialog, ``on_export`` gets the path
    for the caller's own feedback). Returns the Toplevel so callers
    (tests, smoke) can inspect it. Best-effort by contract."""
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
    # DS2 v2.46 — the receipts go where you send them
    saveas_btn = tk.Label(head, text="Save as file…", bg=theme["card"],
                          fg=theme["text_secondary"], cursor="hand2",
                          font=(FONT_UI, 9))
    saveas_btn.pack(side=tk.RIGHT, padx=(0, 12))
    copyall_btn = tk.Label(head, text="Copy all", bg=theme["card"],
                           fg=theme["text_secondary"], cursor="hand2",
                           font=(FONT_UI, 9))
    copyall_btn.pack(side=tk.RIGHT, padx=(0, 12))

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

    # DS2 v2.46 — kind filters: click a dot to hide that kind; a
    # kind the studio cannot name always shows (you cannot re-show
    # what you cannot name, so nothing silently vanishes)
    shown = set(_CANONICAL_KINDS)
    filterrow = tk.Frame(wrap, bg=theme["card"])
    filterrow.pack(fill=tk.X, padx=14, pady=(0, 8))
    tk.Label(filterrow, text="show:", bg=theme["card"],
             fg=theme["text_muted"], font=(FONT_UI, 8)).pack(side=tk.LEFT)
    kind_btns = {}

    def _toggle_kind(kind):
        try:
            lbl = kind_btns.get(kind)
            if kind in shown:
                shown.discard(kind)
                lbl.config(text="○ " + kind, fg=theme["text_muted"])
            else:
                shown.add(kind)
                lbl.config(text="● " + kind,
                           fg=_KIND_DOT.get(kind) or theme.accent)
        except Exception:  # noqa: BLE001 — a dot must never raise
            pass
        _refilter()

    for _k in _CANONICAL_KINDS:
        _lbl = tk.Label(filterrow, text="● " + _k, bg=theme["card"],
                        fg=_KIND_DOT.get(_k) or theme.accent,
                        cursor="hand2", font=(FONT_UI, 8))
        _lbl.pack(side=tk.LEFT, padx=(8, 0))
        _lbl.bind("<Button-1>", lambda _e, k=_k: _toggle_kind(k))
        kind_btns[_k] = _lbl

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
        hits = log.filtered(var.get(), kinds=shown)
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

    def _copy_all(_event=None):
        """DS2 v2.46 — every receipt to the clipboard, oldest first
        (the same text the file gets). Never raises."""
        _copy(export_text(log.entries()))

    def _saveas(_event=None):
        """DS2 v2.46 — the receipts as a file, wherever the user
        points; v2.47: the typed extension picks the format (.json /
        .csv / text). A cancelled dialog is an honest no-op. Never
        raises."""
        try:
            stamp = _time.strftime("%Y%m%d-%H%M%S")
            path = filedialog.asksaveasfilename(
                parent=win, title="Export activity receipts",
                defaultextension=".txt",
                initialfile="activity-export-%s.txt" % stamp,
                initialdir=(export_dir if export_dir else None))
            path = str(path or "").strip()
            if not path:
                return
            # v2.47: the format follows the typed extension — .json,
            # .csv or the plain text diary
            got = export_to(log, path)
            if got and on_export:
                on_export(got)
        except Exception:  # noqa: BLE001 — a button must never raise
            pass

    copyall_btn.bind("<Button-1>", _copy_all)
    saveas_btn.bind("<Button-1>", _saveas)

    _refilter()
    try:
        entry.focus_set()
    except Exception:  # noqa: BLE001 — focus is garnish
        pass
    return win
