"""DXN1 STUDIO — the DS2 cheat sheet (v1.7).

One window that answers "what can this thing do?": keyboard shortcuts,
palette power commands, the AI workflow, the visual git suite, memory
and usage — grouped, searchable, and written like a human. Open it from
Help → Cheat sheet or the palette ("Cheat sheet…").
"""

import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

SHEETS = [
    ("CORE MOVES", [
        ("Ctrl+K", "Command palette — every command; type @ for symbols"),
        ("Ctrl+P", "Quick open — fuzzy jump to any file"),
        ("Ctrl+S", "Save"), ("Ctrl+N", "New file"),
        ("Ctrl+O", "Open file"), ("F5", "Run the project"),
        ("Ctrl+F", "Find in file (Ctrl+H replaces)"),
        ("Ctrl+G", "Go to line"), ("Ctrl+W", "Close tab"),
    ]),
    ("EDITOR POWER (DS2)", [
        ("Tab", "Expand snippets — def, class, try, with, fn…"),
        ("Ctrl+F2", "Toggle bookmark on this line (F2 walks them)"),
        ("Ctrl+/", "Toggle comment"), ("Alt+Up/Down", "Move line"),
        ("Ctrl+Shift+D", "Duplicate line"), ("Ctrl+Shift+K", "Delete line"),
        ("Ctrl+\\", "Split editor"),
        ("Ctrl++ / Ctrl+-", "Bigger / smaller editor text"),
    ]),
    ("AI WORKFLOW (DS2)", [
        ("Select → ⚡", "Quick actions: explain, refactor, tests, fix, "
                        "types, docstring, optimize"),
        ("AI: review file", "Whole-file AI review with severity findings"),
        ("Pair mode", "Agent plans first → you approve → it builds in the "
                      "sandbox"),
        ("✨ AI msg", "AI drafts your commit message from the staged diff"),
        ("remember: …", "Teach the agent a fact — recalled every session"),
    ]),
    ("GIT, VISUALIZED (DS2)", [
        ("Graph", "Commit graph across all branches — click for details"),
        ("Branches", "Branch manager: create, merge, rename, delete, track"),
        ("⇄ Diff", "Word-level visual diff — split or unified view"),
        ("✨ AI msg", "Commit message drafts live in the source control "
                      "panel"),
    ]),
    ("INTELLIGENCE (DS2)", [
        ("Agent memory", "Per-workspace facts + prefs, injected into every "
                         "agent conversation"),
        ("Token usage", "Where your tokens went: 14-day chart, per-model "
                        "bars, cost estimates, CSV"),
        ("remember: …", "Teach the agent instantly from the chat — no "
                        "model call, instant confirmation"),
    ]),
    ("POCKET KNIFE (DS2)", [
        ("Dev tools", "Regex tester, JSON fixer, text transformer, time "
                      "converter — one window (Help → Developer Tools, "
                      "or type `tools` in the terminal)"),
        ("regex tab", "Live matches with spans + groups, i/m/s flags, "
                      "replace preview"),
        ("json tab", "Pretty / minify / validate with line:col on errors"),
        ("text tab", "snake/camel/kebab, base64, URL%, \\u escapes, "
                     "MD5/SHA, word counts — chain via ↑"),
        ("time tab", "epoch ↔ ISO ↔ '3h ago', ticking clock, local/UTC"),
        ("color tab", "hex ↔ rgb ↔ hsl, WCAG contrast grade, harmony "
                      "swatches — click to copy"),
        ("cron <expr>", "Decode any cron schedule — plain English, field "
                        "table, next five runs (`cron 0 9 * * 1-5`)"),
        ("readability", "Flesch / Kincaid / Fog report for the current "
                        "file: long sentences + word pressure"),
        ("jwt <token>", "Decode a JWT — header, payload, humanized "
                        "expiry (decode only, never verified)"),
        ("env", "Lint the workspace .env — duplicates, quoting, secret "
                "smells — and copy a masked version"),
        ("gen", "Test data generator — UUID v4, ULID, nanoid, passwords, "
                "lorem, fake users/events as JSON"),
        ("db <file>", "SQLite Lab — browse tables, schema dive, run "
                      "queries, export CSV/markdown (read-only default)"),
        ("tree <dir>", "Directory tree export — junk-aware ASCII tree, "
                       "depth + sizes, one-click clipboard copy"),
        ("hash <file>", "Hasher — chunked MD5/SHA digests, folder "
                        "manifests (sha256sum -c style), verify verdicts"),
        ("focus <min>", "Pomodoro timer — 25/5 cycles (custom blocks "
                        "welcome), session dots + long-break reminders"),
        ("sort <mode>", "Line tools — sort az/za/len, dedupe, shuffle, "
                        "reverse, trim; selection or whole file "
                        "(Ctrl+Alt+S/D/H/R)"),
        ("clip", "Clipboard history — last 25 copies, double-click to "
                 "paste back (Ctrl+Shift+V)"),
        ("md", "Markdown preview — live dual-pane render, tables + "
               "code blocks, copy/export HTML (F5)"),
        ("color", "Color Kit — hex/rgb/hsl at a glance, WCAG contrast "
                  "verdicts, click-to-copy shade ramps"),
        ("rest", "REST Bench — send GET/POST/PATCH…, inspect status + "
                 "JSON, copy any request as curl (Ctrl+Enter)"),
        ("chart", "Chart Studio — paste numbers, get line/bar/"
                  "histogram views, stats and a sparkline"),
        ("unit", "Unit Converter — length/mass/temperature/data/"
                 "time/speed, all units at once, offline"),
        ("lang", "Language — switch UI language packs (en es fr de "
                 "pt zh hi ja), remembered across restarts"),
        ("scribe <n>", "Writing meter — ✎ chip in the statusbar shows "
                       "words, WPM and goal progress; click for a "
                       "session toast")
    ]),
    ("TERMINAL TALK", [
        ("help", "List every studio command"),
        ("run", "Execute the current project"),
        ("git status", "Repo status without leaving the studio"),
        ("todo", "Scan the workspace for TODO / FIXME"),
        ("palette", "Open the command palette from the keyboard"),
    ]),
]


class CheatSheet(tk.Toplevel):
    """Searchable, grouped cheat sheet."""

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.t = theme
        self.title("Cheat sheet — DXN1 STUDIO")
        self.configure(bg=self.t["bg"])
        self.geometry("720x640")
        self.minsize(520, 420)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build()
        self._render("")
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 720, 640
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=46)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⌘  CHEAT SHEET", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        self.search = tk.Entry(bar, bg=t["editor"], fg=t["text"],
                               insertbackground=t["text"], relief=tk.FLAT,
                               font=(FONT_UI, 10), width=30,
                               highlightthickness=1,
                               highlightbackground=t["border"],
                               highlightcolor=t.accent)
        self.search.pack(side=tk.RIGHT, padx=12, ipady=4)
        self.search.insert(0, "filter…")
        self.search.config(fg=t["text_muted"])
        self.search.bind("<FocusIn>", self._s_in)
        self.search.bind("<FocusOut>", self._s_out)
        self.search.bind("<KeyRelease>", lambda e: self._render(
            self.search.get() if self.search.get() != "filter…" else ""))

        wrap = tk.Frame(self, bg=t["bg"])
        wrap.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(wrap, bg=t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=t["bg"])
        self._win = self.canvas.create_window((0, 0), window=self.inner,
                                              anchor="nw", width=690)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))

    def _s_in(self, _e=None):
        if self.search.get() == "filter…":
            self.search.delete(0, tk.END)
            self.search.config(fg=self.t["text"])

    def _s_out(self, _e=None):
        if not self.search.get():
            self.search.insert(0, "filter…")
            self.search.config(fg=self.t["text_muted"])

    def _render(self, query):
        for w in self.inner.winfo_children():
            w.destroy()
        t = self.t
        q = (query or "").lower()
        total = 0
        for section, items in SHEETS:
            rows = [(k, d) for k, d in items
                    if not q or q in k.lower() or q in d.lower()]
            if not rows:
                continue
            total += len(rows)
            tk.Label(self.inner, text=section, bg=t["bg"],
                     fg=t.accent, font=(FONT_UI, 9, "bold"),
                     anchor="w").pack(fill=tk.X, padx=6, pady=(14, 3))
            for key, desc in rows:
                row = tk.Frame(self.inner, bg=t["card"],
                               highlightthickness=1,
                               highlightbackground=t["card_border"])
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=key, bg=t["card"], fg=t["text"],
                         font=(FONT_MONO, 9, "bold"), width=18,
                         anchor="w").pack(side=tk.LEFT, padx=10, pady=5)
                tk.Label(row, text=desc, bg=t["card"],
                         fg=t["text_secondary"], font=(FONT_UI, 9),
                         anchor="w", wraplength=460,
                         justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X,
                                               expand=True, padx=6, pady=5)
        if not total:
            tk.Label(self.inner, text="Nothing matches — try 'git', 'AI' "
                     "or 'palette'.", bg=t["bg"], fg=t["text_muted"],
                     font=(FONT_UI, 10)).pack(anchor="w", padx=8, pady=14)


def open_cheatsheet(parent, theme):
    """Convenience opener — mirrors the studio's one-call dialog style."""
    return CheatSheet(parent, theme)
