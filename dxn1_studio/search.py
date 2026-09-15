"""DXN1 STUDIO — find-in-files.

A sidebar view that scans the whole workspace for a query in a worker
thread (never blocking the UI) and groups the matches by file. Clicking
a match opens the file at that line. Skips caches/venvs and huge binary
-looking files; capped so a runaway search can't eat memory.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO
from .widgets import TREE_SKIP

MAX_RESULTS = 300
MAX_FILE_BYTES = 512 * 1024
TEXT_EXTS = {".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm",
             ".css", ".json", ".md", ".txt", ".yml", ".yaml", ".toml",
             ".ini", ".cfg", ".sh", ".env", ".xml", ".svg", ".sql",
             ".c", ".h", ".cpp", ".hpp", ".java", ".kt", ".rs", ".go",
             ".rb", ".php", ".lua", ".flask", ""}


class SearchPanel(tk.Frame):
    """'Search' sidebar — find text across every file in the workspace."""

    def __init__(self, parent, theme, on_open_match=None):
        super().__init__(parent, bg=theme["sidebar"])
        self.theme = theme
        self.on_open_match = on_open_match
        self.workspace = None
        self._hits = []
        self._searching = False

        header = tk.Frame(self, bg=theme["header"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="SEARCH", bg=theme["header"],
                 fg=theme["text_secondary"], font=(FONT_UI, 10, "bold"),
                 ).pack(side=tk.LEFT, padx=15)

        row = tk.Frame(self, bg=theme["sidebar"])
        row.pack(fill=tk.X, padx=10, pady=(10, 2))
        self.entry = tk.Entry(row, bg=theme["editor"], fg=theme["text"],
                              insertbackground=theme["text"], relief=tk.FLAT,
                              font=(FONT_MONO, 10), highlightthickness=1,
                              highlightbackground=theme["border"],
                              highlightcolor=theme.accent)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.entry.bind("<Return>", lambda e: self.start_search())
        self.entry.bind("<KP_Enter>", lambda e: self.start_search())

        self.case_btn = tk.Label(row, text="Aa", bg=theme["card"],
                                 fg=theme["text_muted"],
                                 font=(FONT_UI, 8, "bold"), cursor="hand2",
                                 padx=7, pady=4)
        self.case_btn.pack(side=tk.LEFT, padx=(6, 0))
        self.case_btn.bind("<Button-1>", lambda e: self._toggle_case())
        self.case_sensitive = False

        self.status = tk.Label(self, text="Type a query, hit Enter.",
                               bg=theme["sidebar"], fg=theme["text_muted"],
                               font=(FONT_UI, 8), anchor="w")
        self.status.pack(fill=tk.X, padx=12, pady=(0, 4))

        self.canvas = tk.Canvas(self, bg=theme["sidebar"], highlightthickness=0)
        sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview,
                           style="TS2.Vertical.TScrollbar")
        self.results = tk.Frame(self.canvas, bg=theme["sidebar"])
        self._win = self.canvas.create_window((0, 0), window=self.results,
                                              anchor="nw", width=240)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.results.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))

    # ---------------------------------------------------------------- ui
    def _toggle_case(self):
        self.case_sensitive = not self.case_sensitive
        self.case_btn.config(
            fg=self.theme.accent if self.case_sensitive
            else self.theme["text_muted"])

    def set_workspace(self, path):
        self.workspace = path if path and os.path.isdir(path) else None
        self._clear_results()
        self.status.config(text="Type a query, hit Enter." if self.workspace
                           else "Open a workspace to search it.")

    def _clear_results(self):
        for w in self.results.winfo_children():
            w.destroy()
        self._hits = []

    # ------------------------------------------------------------ engine
    def start_search(self):
        needle = self.entry.get().strip()
        if not needle or self._searching or not self.workspace:
            return
        self._searching = True
        self._clear_results()
        self.status.config(text="searching…")
        threading.Thread(target=self._scan, args=(needle,),
                         daemon=True).start()
        self._poll_done(needle)

    def _poll_done(self, needle):
        if self._searching:
            self.after(150, lambda: self._poll_done(needle))
            return
        self._render(needle)

    def _scan(self, needle):
        try:
            key = needle if self.case_sensitive else needle.lower()
            hits = []
            for dirpath, dirnames, filenames in os.walk(self.workspace):
                dirnames[:] = [d for d in dirnames if d not in TREE_SKIP
                               and not d.startswith(".")]
                for fn in sorted(filenames):
                    if len(hits) >= MAX_RESULTS:
                        break
                    path = os.path.join(dirpath, fn)
                    if os.path.splitext(fn)[1].lower() not in TEXT_EXTS:
                        continue
                    try:
                        if os.path.getsize(path) > MAX_FILE_BYTES:
                            continue
                        with open(path, "r", encoding="utf-8",
                                  errors="replace") as fh:
                            for i, line in enumerate(fh, 1):
                                hay = line if self.case_sensitive \
                                    else line.lower()
                                if key in hay:
                                    col = hay.find(key)
                                    hits.append((path, i, line.strip()[:120],
                                                 col))
                                    if len(hits) >= MAX_RESULTS:
                                        break
                    except OSError:
                        continue
            self._hits = hits
        except Exception:   # noqa: BLE001 — a bad scan beats a dead panel
            self._hits = []
        finally:
            self._searching = False

    def _render(self, needle):
        for w in self.results.winfo_children():
            w.destroy()
        self._hits = self._hits or []
        n_files = len({h[0] for h in self._hits})
        shown = len(self._hits)
        if not self._hits:
            self.status.config(text=f"No matches for “{needle}”."
                               if self.workspace else "No workspace.")
            return
        cap = " (capped)" if shown >= MAX_RESULTS else ""
        self.status.config(text=f"{shown} matches in {n_files} files{cap}")
        by_file = {}
        for path, line, text, col in self._hits:
            by_file.setdefault(path, []).append((line, text, col))
        for path, rows in by_file.items():
            fh = tk.Frame(self.results, bg=self.theme["sidebar"])
            fh.pack(fill=tk.X, pady=(8, 1))
            tk.Label(fh, text=f"◈  {os.path.basename(path)}",
                     bg=self.theme["sidebar"], fg=self.theme.accent,
                     font=(FONT_UI, 9, "bold"), anchor="w").pack(anchor="w")
            for line, text, col in rows[:12]:
                lbl = tk.Label(
                    self.results,
                    text=f"  {line:>4}  {text}"[:110],
                    bg=self.theme["sidebar"], fg=self.theme["text_secondary"],
                    font=(FONT_MONO, 8), anchor="w", cursor="hand2")
                lbl.pack(fill=tk.X, pady=1)
                lbl.bind("<Button-1>",
                         lambda e, p=path, l=line, c=col:
                         self._open(p, l, c))
                lbl.bind("<Enter>", lambda e, w=lbl: w.config(
                    fg=self.theme["text"]))
                lbl.bind("<Leave>", lambda e, w=lbl: w.config(
                    fg=self.theme["text_secondary"]))

    def _open(self, path, line, col):
        if self.on_open_match:
            try:
                self.on_open_match(path, line, col)
            except Exception:  # noqa: BLE001
                pass
