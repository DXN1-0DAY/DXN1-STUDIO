"""DS2 CSV Lab — paste CSV, see the table.

A tiny spreadsheet peeker: paste CSV (or TSV / semicolon / pipe
separated), the engine sniffs the delimiter, parses with the stdlib
``csv`` module and renders a sortable ttk treeview with row/column
counts. One click copies the grid back out as TSV.

Engine (sniff_delimiter / parse_csv / table_stats / to_tsv) is pure
and unit-tested; the window never raises on weird input.

Open with: Workshop menu, palette, terminal ``csv`` / ``csvkit``.
"""

import csv
import io
import tkinter as tk
from tkinter import ttk

from . import hints

__all__ = ["sniff_delimiter", "parse_csv", "table_stats", "to_tsv",
           "CsvLab", "open_csv_lab"]

_CANDIDATES = (",", ";", "\t", "|")


def sniff_delimiter(text):
    """Most likely delimiter for *text* (default ','). Never raises."""
    if not isinstance(text, str):
        return ","
    sample = text[:4000]
    counts = {d: sample.count(d) for d in _CANDIDATES}
    best = max(_CANDIDATES, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def parse_csv(text, delimiter=None):
    """Parse CSV text into rows (list of lists of str).

    Delimiter auto-sniffed when None. Junk → []. Never raises.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    if delimiter is None:
        delimiter = sniff_delimiter(text)
    try:
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [row for row in reader if any(cell.strip()
                                             for cell in row)]
        return rows
    except (csv.Error, ValueError):
        return []


def table_stats(rows):
    """Shape summary for a parsed table. Empty → honest zeros."""
    if not rows:
        return {"rows": 0, "cols": 0, "headers": [], "ragged": False}
    widths = {len(r) for r in rows}
    return {"rows": len(rows),
            "cols": max(widths),
            "headers": rows[0],
            "ragged": len(widths) > 1}


def to_tsv(rows):
    """Render rows back out as TSV text (paste into a spreadsheet)."""
    if not rows:
        return ""
    try:
        out = io.StringIO()
        writer = csv.writer(out, delimiter="\t",
                            quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)
        return out.getvalue().rstrip("\r\n")
    except (csv.Error, ValueError):
        return ""


# --------------------------------------------------------------- window

SAMPLE_CSV = """name,role,stars
DXN1,maintainer,42
community,contributors,7
you,contributor,1
"""


class CsvLab(tk.Toplevel):
    """Paste-CSV table window. Never raises on junk input."""

    DELIMS = (",", ";", "tab", "|")

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("CSV Lab — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("680x480")
        self.minsize(520, 380)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="csv lab", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=(10, 8), pady=8)
        tk.Label(top, text="delimiter", bg=t.get("header", "#242432"),
                 fg=t.get("text", "#e8e8f0")).pack(side=tk.LEFT)
        self.delim = tk.StringVar(value="auto")
        for d in ("auto",) + self.DELIMS:
            tk.Radiobutton(top, text=d, value=d, variable=self.delim,
                           command=self.refresh,
                           bg=t.get("header", "#242432"),
                           fg=t.get("text", "#e8e8f0"),
                           selectcolor=t.get("editor_bg", "#1a1a24"),
                           activebackground=t.get("header", "#242432"),
                           activeforeground=t.get("text", "#e8e8f0"),
                           highlightthickness=0).pack(side=tk.LEFT,
                                                      padx=2)

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True)

        # left: raw text
        left = tk.Frame(body, bg=t.get("bg", "#16161e"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                  padx=(10, 4), pady=10)
        tk.Label(left, text="paste csv / tsv / semicolon / pipe",
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.input = tk.Text(left, width=26, wrap="none",
                             bg=t.get("editor_bg", "#1a1a24"),
                             fg=t.get("text", "#e8e8f0"),
                             insertbackground=t.get("text", "#fff"),
                             relief=tk.FLAT, padx=8, pady=6)
        self.input.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.input.insert("1.0", initial or SAMPLE_CSV)
        self.input.bind("<KeyRelease>", lambda _e: self._schedule())

        # right: treeview grid
        right = tk.Frame(body, bg=t.get("bg", "#16161e"))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                   padx=(4, 10), pady=10)
        self.tree = ttk.Treeview(right, show="headings", height=10)
        self.tree.pack(fill=tk.BOTH, expand=True)
        vsb = ttk.Scrollbar(right, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne",
                  width=12)
        try:
            style = ttk.Style(self)
            style.configure("Csv.Treeview",
                            background=t.get("editor_bg", "#1a1a24"),
                            foreground=t.get("text", "#e8e8f0"),
                            fieldbackground=t.get("editor_bg",
                                                  "#1a1a24"))
            self.tree.configure(style="Csv.Treeview")
        except Exception:
            pass

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text="ready", anchor="w",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text="copy as TSV", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_tsv).pack(side=tk.RIGHT, padx=8,
                                               pady=4)

        # keys first advertised by the bar below (v2.50 wave 3)
        self.bind("<Escape>", lambda _e: self.destroy())
        # Ctrl+Shift+C, not Ctrl+C — the input keeps its native copy
        self.bind("<Control-C>", lambda _e: self._copy_tsv())
        hints.hint_bar(self, t,
                       pairs=[("Ctrl+Shift+C", "copy as TSV")],
                       notes=["live table as you type"])

        self._after_id = None
        self.refresh()

    # ---------------------------------------------------- behaviour
    def _schedule(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._after_id = self.after(300, self.refresh)
        except Exception:
            pass

    def _delimiter(self):
        pick = self.delim.get()
        if pick == "auto":
            return None
        return "\t" if pick == "tab" else pick

    def refresh(self):
        """Re-parse + re-render the grid. Junk-tolerant — never raises."""
        try:
            text = self.input.get("1.0", "end")
            rows = parse_csv(text, self._delimiter())
            self.tree.delete(*self.tree.get_children())
            cols = [c for c in range(max((len(r) for r in rows),
                                         default=0))]
            self.tree["columns"] = cols
            if rows:
                for i in cols:
                    self.tree.heading(
                        i, text=rows[0][i] if i < len(rows[0]) else
                        "col%d" % (i + 1))
                    self.tree.column(i, width=110, stretch=True)
                for r in rows[1:]:
                    self.tree.insert("", "end",
                                     values=[c[:60] for c in r])
                stats = table_stats(rows)
                note = " · ragged widths" if stats["ragged"] else ""
                self.status.config(
                    text="%d rows × %d cols%s — header row used as "
                         "headings" % (stats["rows"] - 1,
                                       stats["cols"], note))
            else:
                self.status.config(
                    text="nothing tabular yet — paste data on the left")
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _copy_tsv(self):
        try:
            text = self.input.get("1.0", "end")
            rows = parse_csv(text, self._delimiter())
            tsv = to_tsv(rows)
            if not tsv:
                self.status.config(text="nothing to copy")
                return
            self.clipboard_clear()
            self.clipboard_append(tsv)
            self.status.config(text="grid copied as TSV")
        except Exception:
            pass


def open_csv_lab(parent, theme, initial=""):
    """Public entry: open the CSV Lab window. Never raises."""
    try:
        win = CsvLab(parent, theme, initial=initial)
        win.grab_release()
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
