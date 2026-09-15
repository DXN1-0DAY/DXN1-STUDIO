"""DXN1 STUDIO — terminal verbs browser (DS2 v2.39).

The terminal speaks dozens of studio verbs (``deps``, ``csv``,
``git <args>``, ``session save``…) but until now the only way to see
them all was typing ``help`` and scrolling the output. This module
gives the verbs a real window: searchable, grouped by nothing smarter
than alphabetical order, and one click drops the verb into the
terminal input — Enter runs it, the user stays in charge.

The data is the same ``TERMINAL_HELP`` tuple the terminal's ``help``
verb and the cheat-sheet exporter use, so the three views can never
disagree about what the studio can do. Multi-line rows (``git``) are
merged back into one honest description here.
"""

import tkinter as tk

from .widgets import FONT_UI, FONT_MONO


def verb_rows(rows=None):
    """``TERMINAL_HELP`` flattened for display: continuation lines
    (empty command) are folded into the previous description, so every
    row is a complete ``(verb, description)`` pair. Never raises."""
    try:
        if rows is None:
            from .app import TERMINAL_HELP
            rows = TERMINAL_HELP
        out = []
        for cmd, desc in rows:
            cmd = str(cmd or "").strip()
            desc = " ".join(str(desc or "").split())
            if not cmd:
                if out and desc:
                    prev_cmd, prev_desc = out[-1]
                    out[-1] = (prev_cmd,
                               (prev_desc + " " + desc).strip())
                continue
            if not desc:
                desc = "(studio command)"
            out.append((cmd, desc))
        return out
    except Exception:  # noqa: BLE001 — a browser must never crash boot
        return []


def filter_rows(rows, query):
    """Rows whose verb or description contains ``query`` (case-
    insensitive substring — the same first pass ``help <q>`` uses).
    An empty query returns every row, never None."""
    q = str(query or "").strip().lower()
    if not q:
        return list(rows or [])
    return [r for r in (rows or [])
            if q in r[0].lower() or q in r[1].lower()]


def open_verbs(master, theme, on_insert=None, rows=None):
    """Open the terminal-verbs browser. ``on_insert(verb)`` fires when
    a row is clicked (the app drops it into the terminal input).
    Returns the Toplevel so callers (tests, smoke) can inspect it."""
    data = verb_rows(rows)
    win = tk.Toplevel(master)
    win.title("Terminal Verbs")
    win.configure(bg=theme["card"])
    win.transient(master)
    win.geometry("640x520")
    win.minsize(460, 340)

    wrap = tk.Frame(win, bg=theme["card"], highlightthickness=1,
                    highlightbackground=theme["card_border"])
    wrap.pack(fill=tk.BOTH, expand=True)

    head = tk.Frame(wrap, bg=theme["card"])
    head.pack(fill=tk.X, padx=14, pady=(14, 6))
    tk.Label(head, text="TERMINAL VERBS", bg=theme["card"],
             fg=theme["text"], font=(FONT_UI, 12, "bold")
             ).pack(side=tk.LEFT)
    count_lbl = tk.Label(head, text=f"{len(data)} verbs", bg=theme["card"],
                         fg=theme["text_muted"], font=(FONT_UI, 9))
    count_lbl.pack(side=tk.RIGHT)

    # live search — the same substring pass as `help <q>`'s first stage
    searchrow = tk.Frame(wrap, bg=theme["card"])
    searchrow.pack(fill=tk.X, padx=14, pady=(0, 8))
    # explicit master: the var must live in the same interpreter as
    # the entry (two Tk roots exist under pytest) or entry edits and
    # the write-trace never meet
    var = tk.StringVar(master=master)
    ent = tk.Entry(searchrow, textvariable=var, bg=theme["editor"],
                   fg=theme["text"], insertbackground=theme["text"],
                   relief=tk.FLAT, font=(FONT_UI, 11), highlightthickness=0)
    ent.pack(fill=tk.X, ipady=6)
    ent.insert(0, "")
    ent.focus_set()

    tk.Label(wrap,
             text="click a verb to drop it into the terminal — Enter runs it",
             bg=theme["card"], fg=theme["text_muted"], font=(FONT_UI, 8)
             ).pack(anchor="w", padx=14, pady=(0, 6))

    body = tk.Frame(wrap, bg=theme["card"])
    body.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(body, bg=theme["card"], highlightthickness=0, bd=0)
    sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = tk.Frame(canvas, bg=theme["card"])
    canvas.create_window((0, 0), window=inner, anchor="nw")

    empty_lbl = None

    def _refilter(_event=None):
        nonlocal empty_lbl
        try:
            empty_lbl.destroy()
        except Exception:  # noqa: BLE001 — first pass has nothing yet
            pass
        empty_lbl = None
        for child in inner.winfo_children():
            child.destroy()
        hits = filter_rows(data, var.get())
        count_lbl.config(text=f"{len(hits)} verbs")
        if not hits:
            empty_lbl = tk.Label(
                inner,
                text="nothing matches — try a shorter filter",
                bg=theme["card"], fg=theme["text_muted"],
                font=(FONT_UI, 10), anchor="w")
            empty_lbl.pack(fill=tk.X, padx=14, pady=12)
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            return
        for verb, desc in hits:
            row = tk.Frame(inner, bg=theme["card"], cursor="hand2")
            row.pack(fill=tk.X, padx=10, pady=1)
            lbl_v = tk.Label(row, text=verb, bg=theme["card"],
                             fg=theme.accent, font=(FONT_MONO, 10, "bold"),
                             anchor="w", width=18)
            lbl_v.pack(side=tk.LEFT, padx=(4, 8))
            lbl_d = tk.Label(row, text=desc, bg=theme["card"],
                             fg=theme["text_secondary"], font=(FONT_UI, 9),
                             anchor="w")
            lbl_d.pack(side=tk.LEFT, fill=tk.X, expand=True)
            for w in (row, lbl_v, lbl_d):
                w.bind("<Button-1>", lambda _e, v=verb: _pick(v))
                w.bind("<Enter>", lambda _e, r=row: r.config(
                    bg=theme["hover"]))
                w.bind("<Leave>", lambda _e, r=row: r.config(
                    bg=theme["card"]))
        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _pick(verb):
        if on_insert:
            try:
                on_insert(verb)
            except Exception:  # noqa: BLE001 — the click must survive
                pass

    def _on_wheel(event):  # linux button-4/5, windows delta
        try:
            if getattr(event, "num", 0) == 4 or event.delta > 0:
                canvas.yview_scroll(-2, "units")
            else:
                canvas.yview_scroll(2, "units")
        except Exception:  # noqa: BLE001 — scrolling is cosmetic
            pass
    canvas.bind("<Button-4>", _on_wheel)
    canvas.bind("<Button-5>", _on_wheel)
    canvas.bind("<MouseWheel>", _on_wheel)

    var.trace_add("write", lambda *_a: _refilter())
    _refilter()
    win.bind("<Escape>", lambda _e: win.destroy())
    # semi-public hooks — smoke/pytest drive the live filter without
    # reaching into closures (search_entry pairs with refilter())
    win.search_entry = ent
    win.refilter = _refilter
    # DS2 v2.61 — width accounting round three: open no narrower
    # than what it actually packed
    from . import geom as _geom
    _geom.fit_to_content(win, 640, 520)
    return win


# -------------------------------------------------------------- self-test
if __name__ == "__main__":
    rows = verb_rows()
    assert rows, "verb_rows must flatten TERMINAL_HELP"
    assert all(c and d for c, d in rows), "no empty verbs/descriptions"
    verbs = [c for c, _ in rows]
    assert len(verbs) == len(set(verbs)), "verbs must be unique"
    assert "git <args>" in verbs, "continuation lines merge into git"
    git = dict(rows)["git <args>"]
    assert "commit" in git, git
    assert "deps" in verbs and "verbs" in verbs
    assert filter_rows(rows, "") == rows
    assert [c for c, _ in filter_rows(rows, "deps")] == ["deps"]
    assert filter_rows(rows, "zzzqqq") == []
    assert filter_rows(rows, "PILLOW") == []      # verb text is case-sens.
    assert filter_rows(rows, "markdown")          # desc match
    try:
        import tkinter as _tk
        _root = _tk.Tk()
        _root.withdraw()
        from .theme import Theme
        _th = Theme("dark")
        _win = open_verbs(_root, _th,
                          on_insert=lambda v: None)
        assert _win.winfo_exists()
        _win.destroy()
        _root.destroy()
        print("verbs.py self-test OK (headless window too)")
    except Exception as exc:  # noqa: BLE001 — no display in CI
        print(f"verbs.py self-test OK (no display: {exc})")
