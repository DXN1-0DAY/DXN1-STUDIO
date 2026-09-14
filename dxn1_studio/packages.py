"""DXN1 STUDIO — optional dependency manager.

DXN1 itself is intentionally lightweight: nothing is pip-installed unless
the user asks for it. This window is the one place to opt in — a curated
catalog of the extras power users usually want (Flask first), custom
package installs, and uninstalling, all with live ``pip`` output.
"""

import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

try:
    from importlib import metadata as _md
except ImportError:  # Python < 3.8
    _md = None

# pip name, display name, pitch, import-distribution name for detection
CATALOG = [
    ("flask",    "Flask",     "Powers Web App workspaces — the classic micro web framework.", "flask"),
    ("requests", "Requests",  "HTTP for humans — APIs, scraping, webhooks.", "requests"),
    ("httpx",    "httpx",     "Modern HTTP client with async support.", "httpx"),
    ("pillow",   "Pillow",    "Image handling — also upgrades DXN1's art rendering.", "PIL"),
    ("numpy",    "NumPy",     "Fast arrays and math for data work.", "numpy"),
    ("rich",     "Rich",      "Gorgeous terminal output — colours, tables, progress.", "rich"),
    ("pytest",   "pytest",    "The testing framework everybody reaches for.", "pytest"),
    ("black",    "Black",     "The uncompromising Python code formatter.", "black"),
    ("ruff",     "Ruff",      "Blazing-fast linter + formatter, zero config.", "ruff"),
]


def installed_version(dist_name):
    """Return the installed version of a distribution, or None."""
    if _md is None:
        return None
    try:
        return _md.version(dist_name)
    except Exception:
        return None


class PackageManager(tk.Toplevel):
    """'Tools -> Manage Packages' — the opt-in dependency page."""

    def __init__(self, master, theme, on_change=None):
        super().__init__(master)
        self.theme = theme
        self.t = theme
        self.on_change = on_change          # notified after installs/removals
        self._q = queue.Queue()
        self._busy = set()

        self.title("DXN1 STUDIO — Packages")
        self.configure(bg=self.t["bg"])
        self.geometry("780x600")
        self.minsize(680, 520)
        self.transient(master)

        self._build_header()
        self._build_custom_row()
        self._build_catalog()
        self._build_log()
        self._poll_queue()
        self._refresh_all()

    # ------------------------------------------------------------------ ui
    def _build_header(self):
        head = tk.Frame(self, bg=self.t["header"])
        head.pack(fill=tk.X)
        inner = tk.Frame(head, bg=self.t["header"])
        inner.pack(fill=tk.X, padx=18, pady=12)
        tk.Label(inner, text="Optional Packages", bg=self.t["header"],
                 fg=self.t["text"], font=(FONT_UI, 14, "bold")
                 ).pack(anchor="w")
        tk.Label(inner,
                 text="DXN1 installs nothing until you ask. Add the heavy tools "
                      "whenever you're ready — the studio stays fast either way.",
                 bg=self.t["header"], fg=self.t["text_secondary"],
                 font=(FONT_UI, 9), wraplength=640, justify=tk.LEFT
                 ).pack(anchor="w", pady=(2, 0))

    def _build_custom_row(self):
        row = tk.Frame(self, bg=self.t["bg"])
        row.pack(fill=tk.X, padx=18, pady=(14, 4))
        tk.Label(row, text="Install any package:", bg=self.t["bg"],
                 fg=self.t["text"], font=(FONT_UI, 10)).pack(side=tk.LEFT)
        self.custom_entry = tk.Entry(row, bg=self.t["editor"], fg=self.t["text"],
                                     insertbackground=self.t["text"],
                                     relief=tk.FLAT, font=(FONT_MONO, 10),
                                     highlightthickness=1,
                                     highlightbackground=self.t["border"],
                                     highlightcolor=self.t.accent, width=28)
        self.custom_entry.pack(side=tk.LEFT, padx=(10, 6), ipady=5)
        self.custom_entry.bind("<Return>", lambda e: self._install_custom())
        btn = tk.Label(row, text="pip install", bg=self.t.accent, fg="#ffffff",
                       font=(FONT_UI, 9, "bold"), cursor="hand2", padx=12, pady=5)
        btn.pack(side=tk.LEFT)
        btn.bind("<Button-1>", lambda e: self._install_custom())
        tk.Label(row, text="Multiple names like \"flask requests\" work too.",
                 bg=self.t["bg"], fg=self.t["text_muted"],
                 font=(FONT_UI, 8)).pack(side=tk.LEFT, padx=8)

    def _build_catalog(self):
        wrap = tk.Frame(self, bg=self.t["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(6, 4))

        self.canvas = tk.Canvas(wrap, bg=self.t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=self.t["bg"])
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.list_frame,
                                              anchor="nw", width=700)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        wrap.bind("<Enter>", lambda e: self._bind_wheel())
        wrap.bind("<Leave>", lambda e: self._unbind_wheel())

        self.rows = {}
        for i, (pip_name, disp, pitch, dist) in enumerate(CATALOG):
            row = tk.Frame(self.list_frame, bg=self.t["card"],
                           highlightthickness=1,
                           highlightbackground=self.t["card_border"])
            row.pack(fill=tk.X, pady=3, ipady=6)
            left = tk.Frame(row, bg=self.t["card"])
            left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=14)
            tk.Label(left, text=disp, bg=self.t["card"], fg=self.t["text"],
                     font=(FONT_UI, 11, "bold"), anchor="w").pack(anchor="w")
            tk.Label(left, text=pitch, bg=self.t["card"],
                     fg=self.t["text_secondary"], font=(FONT_UI, 9),
                     wraplength=430, justify=tk.LEFT, anchor="w").pack(anchor="w")
            self.rows[pip_name] = {"row": row, "dist": dist,
                                   "status": None, "btn": None}
            status = tk.Label(row, text="…", bg=self.t["card"],
                              fg=self.t["text_muted"], font=(FONT_UI, 9), width=14)
            status.pack(side=tk.RIGHT, padx=(4, 0))
            action = tk.Label(row, text="Install", bg=self.t.accent, fg="#ffffff",
                              font=(FONT_UI, 9, "bold"), cursor="hand2",
                              padx=12, pady=5)
            action.pack(side=tk.RIGHT, padx=12)
            self.rows[pip_name]["status"] = status
            self.rows[pip_name]["btn"] = action

    def _build_log(self):
        tk.Label(self, text="pip output", bg=self.t["bg"],
                 fg=self.t["text_muted"], font=(FONT_UI, 8, "bold")
                 ).pack(anchor="w", padx=18, pady=(4, 0))
        self.log_box = tk.Text(self, height=7, bg=self.t["terminal"],
                               fg=self.t["text"], font=(FONT_MONO, 9),
                               state="disabled", relief=tk.FLAT, bd=0,
                               padx=10, pady=6, highlightthickness=1,
                               highlightbackground=self.t["border"])
        self.log_box.pack(fill=tk.X, padx=18, pady=(2, 14))

    # ------------------------------------------------------------- helpers
    def _log(self, text, tag=None):
        self.log_box.config(state="normal")
        if tag:
            self.log_box.insert(tk.END, text, tag)
        else:
            self.log_box.insert(tk.END, text)
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def _bind_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _set_row(self, pip_name, status_text, btn_text, btn_bg=None, busy=False):
        info = self.rows.get(pip_name)
        if not info:
            return
        info["status"].config(text=status_text,
                              fg=self.t["success"] if "Installed" in status_text
                              else self.t["text_muted"])
        btn = info["btn"]
        if btn_text:
            btn.config(text=btn_text, bg=btn_bg or self.t.accent,
                       fg="#ffffff" if btn_bg is None else btn_bg,
                       cursor="hand2" if not busy else "watch")
            if not busy:
                verb = btn_text
                btn.bind("<Button-1>", lambda e, n=pip_name, v=verb:
                         self._action(n, v))
        else:
            btn.config(text="…", bg=self.t["card_border"], fg=self.t["text_muted"],
                       cursor="watch")

    def _refresh_all(self):
        for pip_name, disp, _, dist in CATALOG:
            ver = installed_version(dist)
            if ver:
                self._set_row(pip_name, f"Installed · {ver}", "Uninstall",
                              btn_bg=self.t["card_border"])
            else:
                self._set_row(pip_name, "Not installed", "Install")

    def _install_custom(self):
        names = self.custom_entry.get().strip()
        if names:
            self.custom_entry.delete(0, tk.END)
            self._run_pip(["install"] + names.split(), label=names)

    def _action(self, pip_name, verb):
        if pip_name in self._busy:
            return
        if verb == "Install":
            self._run_pip(["install", pip_name], label=pip_name)
        elif verb == "Uninstall":
            self._run_pip(["uninstall", "-y", pip_name], label=pip_name)

    # ------------------------------------------------------------ plumbing
    def install_packages(self, names):
        """Public entry used by DXN1 Agents ('install flask') and menus."""
        if isinstance(names, str):
            names = [names]
        self._run_pip(["install"] + list(names), label=" ".join(names))

    def _run_pip(self, pip_args, label=""):
        self._log(f"\n$ python -m pip {' '.join(pip_args)}\n")
        def work():
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", *pip_args],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
                for line in proc.stdout:
                    self._q.put(("line", line))
                proc.wait()
                self._q.put(("done", (pip_args[0], proc.returncode)))
            except Exception as exc:  # noqa: BLE001 — surface anything
                self._q.put(("line", f"error: {exc}\n"))
                self._q.put(("done", (pip_args[0], 1)))
        threading.Thread(target=work, daemon=True).start()

    def _poll_queue(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "line":
                    self._log(payload)
                elif kind == "done":
                    verb, code = payload
                    self._log(f"→ pip {verb} exited with code {code}\n")
                    self._refresh_all()
                    if self.on_change:
                        try:
                            self.on_change()
                        except Exception:
                            pass
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)
