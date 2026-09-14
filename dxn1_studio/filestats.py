"""DXN1 STUDIO — File statistics (DS2).

Answers the question every developer asks at least once: *what is
actually inside this workspace?* A single read-only scan aggregates
file counts and bytes per extension, finds the largest files, and
renders everything as a small interactive report: summary cards, a
bar chart by extension (click a bar to filter), and a largest-files
table (double-click to copy the path).

Design notes
------------
* Read-only: nothing in the workspace is ever modified.
* Skips the usual noise (.git, node_modules, caches, venvs, builds)
  so the numbers reflect *your* code, not your dependencies.
* The engine is UI-free and fully testable; the window is a thin
  Tk shell over ``scan_workspace``.
* Also runnable from the CLI::

      python3 -m dxn1_studio.filestats [directory]
"""

from __future__ import annotations

import os
import shutil

from . import APP_NAME

# Directories that never contain "your" code — always skipped.
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".dxn1", ".github",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".nox", ".venv", "venv", "env",
    "dist", "build", "out", "target", ".next", ".nuxt", ".svelte-kit",
    "site-packages", ".eggs", ".cache", ".parcel-cache", "coverage",
    ".idea", ".vscode", "Pods", ".terraform",
}

# Binary blobs we count but never try to read.
MAX_LARGEST = 15          # rows in the largest-files table
MAX_BARS = 12             # bars in the per-extension chart
SINGLE_FILE_LIMIT = 64 * 1024 * 1024   # still counted, not opened


def human_size(num):
    """1234567 -> '1.2 MB' — stable, human-friendly byte formatting."""
    try:
        num = float(num)
    except (TypeError, ValueError):
        return "0 B"
    neg = num < 0
    num = abs(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024.0 or unit == "TB":
            if unit == "B":
                val = "%d" % int(num)
            elif num >= 100:
                val = "%.0f" % num
            elif num >= 10:
                val = "%.1f" % num
            else:
                val = "%.2f" % num
            return ("-" if neg else "") + val + " " + unit
        num /= 1024.0
    return ("-" if neg else "") + "%.0f TB" % num


def _wants_dir(name):
    return name not in SKIP_DIRS and not name.startswith(".git")


def scan_workspace(root, largest_n=MAX_LARGEST, on_progress=None):
    """Walk ``root`` and aggregate file statistics.

    Returns a dict::

        {
          "root": str, "exists": bool,
          "total_files": int, "total_bytes": int, "total_dirs": int,
          "hidden_files": int, "errors": int,
          "skipped_dirs": [names actually skipped],
          "by_ext": {".py": {"count": n, "bytes": b}, ...},  # bytes desc
          "no_ext": {"count": n, "bytes": b},
          "largest": [(relpath, bytes), ...],                # desc
        }

    ``on_progress(dirpath)`` may be supplied for GUI feedback; it is
    called at most every 25 directories so the UI stays cheap.
    """
    result = {
        "root": root, "exists": bool(root) and os.path.isdir(root),
        "total_files": 0, "total_bytes": 0, "total_dirs": 0,
        "hidden_files": 0, "errors": 0,
        "skipped_dirs": [],
        "by_ext": {}, "no_ext": {"count": 0, "bytes": 0},
        "largest": [],
    }
    if not result["exists"]:
        return result

    largest = []
    seen_dirs = 0
    for dirpath, dirnames, filenames in os.walk(root, onerror=None):
        seen_dirs += 1
        if on_progress and seen_dirs % 25 == 0:
            try:
                on_progress(dirpath)
            except Exception:       # noqa: BLE001 — progress never breaks
                pass
        # prune skip-lists in place (os.walk respects this)
        keep = []
        for name in sorted(dirnames):
            if name in SKIP_DIRS:
                if name not in result["skipped_dirs"]:
                    result["skipped_dirs"].append(name)
                if os.path.isdir(os.path.join(dirpath, name)):
                    continue
            elif name == ".git" or name.startswith(".git"):
                continue
            keep.append(name)
        dirnames[:] = keep
        result["total_dirs"] += len(keep)

        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                size = os.lstat(fpath).st_size
            except OSError:
                result["errors"] += 1
                continue
            rel = os.path.relpath(fpath, root).replace(os.sep, "/")
            result["total_files"] += 1
            result["total_bytes"] += size
            if fname.startswith("."):
                result["hidden_files"] += 1
            ext = os.path.splitext(fname)[1].lower()
            if ext and 1 <= len(ext) <= 12:
                bucket = result["by_ext"].setdefault(
                    ext, {"count": 0, "bytes": 0})
                bucket["count"] += 1
                bucket["bytes"] += size
            else:
                result["no_ext"]["count"] += 1
                result["no_ext"]["bytes"] += size
            largest.append((rel, size))

    largest.sort(key=lambda t: -t[1])
    result["largest"] = largest[: max(1, int(largest_n or MAX_LARGEST))]

    by_ext = result["by_ext"]
    result["by_ext"] = dict(
        sorted(by_ext.items(), key=lambda kv: (-kv[1]["bytes"], -kv[1]["count"])))
    return result


def top_extensions(stats, n=MAX_BARS):
    """First ``n`` extensions of a scan result, largest bytes first."""
    items = [(ext, d["count"], d["bytes"])
             for ext, d in (stats.get("by_ext") or {}).items()]
    items.sort(key=lambda t: (-t[2], -t[1]))
    return items[: max(1, int(n or MAX_BARS))]


def summary_lines(stats):
    """Two-line human summary used by the CLI and the GUI header."""
    if not stats.get("exists"):
        return "no workspace", ""
    skipped = stats.get("skipped_dirs") or []
    skip_txt = ", ".join(sorted(skipped)[:5]) + ("…" if len(skipped) > 5 else "")
    return (
        "%s files · %s · %s dirs · %s hidden" % (
            stats["total_files"], human_size(stats["total_bytes"]),
            stats["total_dirs"], stats["hidden_files"]),
        ("skipped: " + skip_txt) if skip_txt else "nothing skipped",
    )


# ------------------------------------------------------------------ GUI
_C = {}   # filled in open_stats from the live theme


def open_stats(master, theme, workspace=None, on_log=None):
    """Open the File statistics window for ``workspace``."""
    import tkinter as tk
    from tkinter import ttk

    log = on_log or (lambda m: None)
    ws = workspace or os.getcwd()
    for key, val in (
            ("bg", theme["bg"]), ("card", theme["card"]),
            ("header", theme["header"]), ("border", theme["border"]),
            ("text", theme["text"]), ("muted", theme["text_muted"]),
            ("hover", theme["hover"]),
            ("input", theme.get("overlay") or theme["card"]),
            ("statusbar", theme["statusbar"])):
        _C[key] = val
    accent = getattr(theme, "accent", "#7c3aed")
    accent_soft = getattr(theme, "accent_soft", accent)
    font = getattr(theme, "font", lambda s=10, w="normal": ("sans-serif", s, w))
    mono = getattr(theme, "mono", lambda s=10, w="normal": ("monospace", s, w))

    win = tk.Toplevel(master)
    win.title("File statistics — DS2")
    win.configure(bg=_C["bg"])
    win.transient(master)
    win.geometry("760x640")

    # ---- header -----------------------------------------------------
    head = tk.Frame(win, bg=_C["header"])
    head.pack(fill=tk.X)
    tk.Label(head, text="FILE STATISTICS", bg=_C["header"], fg=_C["text"],
             font=font(13, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
    sub = tk.Label(head, text=ws, bg=_C["header"], fg=_C["muted"],
                   font=mono(9))
    sub.pack(anchor="w", padx=16, pady=(0, 2))
    status = tk.Label(head, text="scanning…", bg=_C["header"],
                      fg=accent, font=font(9))
    status.pack(anchor="w", padx=16, pady=(0, 10))

    # ---- body -------------------------------------------------------
    body = tk.Frame(win, bg=_C["bg"])
    body.pack(fill=tk.BOTH, expand=True)

    cards = tk.Frame(body, bg=_C["bg"])
    cards.pack(fill=tk.X, padx=16, pady=(12, 0))
    card_widgets = {}

    def make_card(title):
        f = tk.Frame(cards, bg=_C["card"], highlightthickness=1,
                     highlightbackground=_C["border"])
        f.pack(side=tk.LEFT, padx=(0, 10), ipadx=6, ipady=2)
        big = tk.Label(f, text="—", bg=_C["card"], fg=accent,
                       font=font(16, "bold"))
        big.pack(anchor="w", padx=10, pady=(8, 0))
        tk.Label(f, text=title, bg=_C["card"], fg=_C["muted"],
                 font=font(8)).pack(anchor="w", padx=10, pady=(0, 8))
        card_widgets[title] = big
        return f

    for title in ("Files", "On disk", "Folders", "Hidden"):
        make_card(title)

    tk.Label(body, text="BY TYPE  ·  click a bar to filter the list",
             bg=_C["bg"], fg=_C["muted"], font=font(8, "bold")
             ).pack(anchor="w", padx=16, pady=(14, 2))

    chart = tk.Canvas(body, bg=_C["card"], highlightthickness=1,
                      highlightbackground=_C["border"], height=210)
    chart.pack(fill=tk.X, padx=16)

    tk.Label(body, text="LARGEST FILES  ·  double-click to copy path",
             bg=_C["bg"], fg=_C["muted"], font=font(8, "bold")
             ).pack(anchor="w", padx=16, pady=(12, 2))

    list_wrap = tk.Frame(body, bg=_C["card"], highlightthickness=1,
                         highlightbackground=_C["border"])
    list_wrap.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 6))

    cols = ("size", "path")
    tree = ttk.Treeview(list_wrap, columns=cols, show="headings", height=8)
    style = ttk.Style()
    try:
        style.map("Treeview", background=[("selected", accent)])
        style.configure("Treeview", bg=_C["card"], fg=_C["text"],
                        fieldbackground=_C["card"], rowheight=24,
                        font=mono(9))
        style.configure("Treeview.Heading", bg=_C["header"],
                        fg=_C["text"], font=font(9, "bold"))
    except Exception:               # noqa: BLE001 — theming is best-effort
        pass
    tree.heading("size", text="Size")
    tree.heading("path", text="Path")
    tree.column("size", width=90, anchor="e", stretch=False)
    tree.column("path", width=560, anchor="w")
    vsb = ttk.Scrollbar(list_wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 0),
              pady=2)
    vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=2)

    state = {"stats": None, "filter": None, "bar_ids": {}}

    # ---- footer -----------------------------------------------------
    foot = tk.Frame(win, bg=_C["statusbar"])
    foot.pack(fill=tk.X, side=tk.BOTTOM)
    filter_lbl = tk.Label(foot, text="", bg=_C["statusbar"],
                          fg=accent_soft, font=font(9))
    filter_lbl.pack(side=tk.LEFT, padx=12)

    def copy_report():
        s = state["stats"]
        if not s:
            return
        lines = ["File statistics — %s" % s["root"], summary_lines(s)[0], ""]
        lines.append("By type:")
        for ext, cnt, bts in top_extensions(s, 30):
            lines.append("  %-8s %6d files  %10s" % (ext, cnt, human_size(bts)))
        if s["no_ext"]["count"]:
            lines.append("  %-8s %6d files  %10s"
                         % ("(none)", s["no_ext"]["count"],
                            human_size(s["no_ext"]["bytes"])))
        lines.append("")
        lines.append("Largest files:")
        for rel, bts in s["largest"]:
            lines.append("  %10s  %s" % (human_size(bts), rel))
        text = "\n".join(lines)
        try:
            win.clipboard_clear()
            win.clipboard_append(text)
            log("file stats: report copied to clipboard")
            filter_lbl.config(text="report copied ✓")
            win.after(1500, lambda: filter_lbl.config(
                text=_filter_text()))
        except Exception:           # noqa: BLE001
            pass

    def open_folder():
        try:
            if os.path.isdir(ws):
                shutil.which("xdg-open") and os.popen(
                    "xdg-open '%s' &" % ws.replace("'", "'\\''"))
        except Exception:           # noqa: BLE001
            log("file stats: could not open folder")

    for text_, cmd in (("Copy report", copy_report),
                       ("Open folder", open_folder),
                       ("Rescan", lambda: scan())):
        tk.Button(foot, text=text_, command=cmd, bg=_C["card"],
                  fg=_C["text"], activebackground=_C["hover"],
                  activeforeground=_C["text"], relief=tk.FLAT,
                  font=font(9), padx=10, pady=3).pack(
            side=tk.RIGHT, padx=(0, 8), pady=6)

    # ---- rendering ---------------------------------------------------
    def _filter_text():
        f = state["filter"]
        if not f:
            return ""
        return ("filter: %s — click the bar again or press Esc to clear"
                % (f if f != "(none)" else "no extension"))

    def render_bars():
        chart.delete("all")
        state["bar_ids"].clear()
        s = state["stats"]
        if not s:
            return
        tops = top_extensions(s, MAX_BARS)
        if s["no_ext"]["count"] and len(tops) < MAX_BARS:
            tops.append(("(none)", s["no_ext"]["count"],
                         s["no_ext"]["bytes"]))
        if not tops:
            chart.create_text(10, 16, anchor="w", text="no files yet",
                              fill=_C["muted"], font=font(9))
            return
        chart.update_idletasks()
        w = max(200, chart.winfo_width() - 24)
        row_h = 21
        biggest = max(b for _, _, b in tops) or 1
        max_files = max(c for _, c, _ in tops) or 1
        x0, y0 = 8, 8
        chart.config(height=min(240, y0 + row_h * len(tops) + 10))
        for i, (ext, cnt, bts) in enumerate(tops):
            y = y0 + i * row_h
            selected = state["filter"] == ext
            label = ext if ext != "(none)" else "(no ext)"
            chart.create_text(x0, y + row_h // 2, anchor="w",
                              text="%-8s" % label,
                              fill=_C["text"] if selected else _C["muted"],
                              font=mono(9))
            bar_x = x0 + 92
            bar_w = max(2, int((w - 92 - 190) * (bts / biggest)))
            color = accent if (selected or not state["filter"]) else accent_soft
            if state["filter"] and not selected:
                color = _C["border"]
            rid = chart.create_rectangle(bar_x, y + 3, bar_x + bar_w,
                                         y + row_h - 5, fill=color,
                                         outline="", tags=("bar%d" % i,))
            info = "%d files · %s" % (cnt, human_size(bts))
            chart.create_text(bar_x + bar_w + 8, y + row_h // 2, anchor="w",
                              text=info, fill=_C["muted"], font=mono(8))
            chart.tag_bind(rid, "<Button-1>", lambda e, ex=ext: toggle_filter(ex))
            chart.tag_bind(rid, "<Enter>", lambda e: chart.config(
                cursor="hand2"))
            chart.tag_bind(rid, "<Leave>", lambda e: chart.config(
                cursor=""))
            state["bar_ids"][ext] = rid

    def render_tree():
        tree.delete(*tree.get_children())
        s = state["stats"]
        if not s:
            return
        f = state["filter"]
        rows = [(rel, bts) for rel, bts in s["largest"]]
        if f == "(none)":
            rows = [(r, b) for r, b in rows
                    if not os.path.splitext(os.path.basename(r))[1]]
        elif f:
            rows = [(r, b) for r, b in rows
                    if os.path.splitext(r)[1].lower() == f]
        for rel, bts in rows:
            tree.insert("", tk.END, values=(human_size(bts), rel))
        if not rows:
            tree.insert("", tk.END, values=("—",
                       "no files match this filter in the top %d"
                       % MAX_LARGEST))

    def toggle_filter(ext):
        state["filter"] = None if state["filter"] == ext else ext
        filter_lbl.config(text=_filter_text())
        render_bars()
        render_tree()

    def clear_filter(event=None):
        if state["filter"]:
            state["filter"] = None
            filter_lbl.config(text="")
            render_bars()
            render_tree()

    win.bind("<Escape>", clear_filter)

    def scan():
        status.config(text="scanning…", fg=accent)
        win.update_idletasks()
        s = scan_workspace(ws, on_progress=lambda d: win.update_idletasks())
        state["stats"] = s
        if not s["exists"]:
            status.config(text="workspace not found", fg="#e06c75")
            return
        line1, _line2 = summary_lines(s)
        status.config(text=line1, fg=accent)
        card_widgets["Files"].config(text=str(s["total_files"]))
        card_widgets["On disk"].config(text=human_size(s["total_bytes"]))
        card_widgets["Folders"].config(text=str(s["total_dirs"]))
        card_widgets["Hidden"].config(text=str(s["hidden_files"]))
        render_bars()
        render_tree()
        log("file stats: %s" % line1)

    def copy_path(event=None):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if len(vals) >= 2 and vals[1] not in ("", "—"):
            win.clipboard_clear()
            win.clipboard_append(os.path.join(ws, vals[1]))
            filter_lbl.config(text="path copied ✓")
            win.after(1200, lambda: filter_lbl.config(
                text=_filter_text()))

    tree.bind("<Double-1>", copy_path)
    scan()
    return win


# ------------------------------------------------------------------ CLI
def _main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    root = argv[0] if argv else os.getcwd()
    stats = scan_workspace(root)
    if not stats["exists"]:
        print("not a directory: %s" % root)
        return 2
    print("File statistics — %s" % root)
    print(summary_lines(stats)[0])
    print()
    print("By type:")
    for ext, cnt, bts in top_extensions(stats, 30):
        print("  %-8s %6d files  %10s" % (ext, cnt, human_size(bts)))
    if stats["no_ext"]["count"]:
        print("  %-8s %6d files  %10s"
              % ("(none)", stats["no_ext"]["count"],
                 human_size(stats["no_ext"]["bytes"])))
    print()
    print("Largest files:")
    for rel, bts in stats["largest"]:
        print("  %10s  %s" % (human_size(bts), rel))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
