"""DXN1 STUDIO — main application window.

Boot flow: splash → (first run: welcome wizard) → Project Hub → the IDE.

v1.1 layout: a slim activity bar switches the left sidebar between
Explorer / Search / Packages; the editor gained syntax highlighting, tab
buffers with dirty markers, a find bar and a command palette (Ctrl+K).
Everything extra stays opt-in: Flask & friends are installed only from
the Packages view, and DXN1 Agents (if enabled) asks permission before
every edit and command unless you switch it to full access — and it is
always sandboxed to the open workspace.
"""

import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
import webbrowser
from tkinter import ttk, filedialog, messagebox

from . import APP_NAME, APP_VERSION, APP_CHANNEL, APP_TAGLINE
from .theme import from_config, FONT_UI, FONT_MONO, ACCENTS
from .widgets import FileTree, CodeEditor, Terminal, TREE_SKIP
from .onboarding import WelcomeWizard
from .tour import InteractiveTour
from . import errors
from . import projects, export, llm
from .sandbox import (WorkspaceSandbox, AgentEngine, FakeBackend,
                      SandboxError)
from .hub import ProjectHub
from .splash import Splash
from .packages import PackagesView
from .search import SearchPanel
from .gitpanel import GitPanel
from .agent import DXN1AgentPanel, AgentSettingsDialog, ConnectDialog, \
    AGENTS_NAME
from . import updater

FONT_SIZES = (("small", 10), ("medium", 11), ("large", 13))

REPO_URL = "https://github.com/DXN1-termux/DXN1-STUDIO"
TEXT_EXTS = {".py", ".pyw", ".pyi", ".js", ".ts", ".jsx", ".tsx", ".html",
             ".htm", ".css", ".json", ".md", ".txt", ".yml", ".yaml",
             ".toml", ".sh", ".cfg", ".ini", ".xml", ".svg", ".csv",
             ".rs", ".go", ".c", ".h", ".cpp", ".java", ".sql", ".env"}


class CommandPalette(tk.Toplevel):
    """Fuzzy command launcher (Ctrl+K / Ctrl+Shift+P)."""

    ROW_H = 34

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.commands = app.palette_commands()
        self.filtered = list(self.commands)
        self.selected = 0
        t = app.theme
        self.t = t
        self.title("Command Palette")
        self.configure(bg=t["card"])
        self.transient(app.root)
        self.overrideredirect(False)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        wrap = tk.Frame(self, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        wrap.pack(fill=tk.BOTH, expand=True)
        row = tk.Frame(wrap, bg=t["card"])
        row.pack(fill=tk.X, padx=12, pady=12)
        tk.Label(row, text="⌕", bg=t["card"], fg=t.accent,
                 font=(FONT_UI, 13, "bold")).pack(side=tk.LEFT, padx=(2, 8))
        self.entry = tk.Entry(row, bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"], relief=tk.FLAT,
                              font=(FONT_UI, 12), highlightthickness=0)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.entry.insert(0, "")
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", lambda e: self._run_selected())
        self.entry.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Down>", lambda e: self._move(1))

        tk.Label(wrap, text="commands ·  @symbols in this file",
                 bg=t["card"], fg=t["text_muted"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=14, pady=(0, 4))

        self.rows = tk.Frame(wrap, bg=t["card"])
        self.rows.pack(fill=tk.X, padx=8, pady=(0, 10))
        self._render()
        self._center()
        self.entry.focus_set()
        self.bind("<Escape>", lambda e: self.close())

    # ------------------------------------------------------------- logic
    def _on_type(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        q = self.entry.get().strip().lower()
        if q.startswith("@"):
            # symbol mode — jump to def / class in the active file
            needle = q[1:].strip()
            syms = self.app.editor.symbols()
            self.filtered = [(f"{kind}  {name}", f"line {line}",
                              ("sym", line))
                             for line, kind, name in syms
                             if not needle or needle in name.lower()]
        else:
            self.filtered = [c for c in self.commands
                             if not q or q in c[0].lower()]
        self.selected = 0
        self._render()

    def _move(self, delta):
        if not self.filtered:
            return
        self.selected = (self.selected + delta) % len(self.filtered)
        self._render()

    def _run_selected(self):
        if self.filtered:
            cmd = self.filtered[min(self.selected, len(self.filtered) - 1)]
            self.close()
            try:
                if isinstance(cmd[2], tuple) and cmd[2] and \
                        cmd[2][0] == "sym":
                    self.app.editor.goto_line(cmd[2][1])
                    self.app.editor.text.focus_set()
                    self.app._update_cursor_pos()
                else:
                    cmd[2]()
            except Exception as exc:  # noqa: BLE001 — palette never crashes
                errors.log_exception(f"palette command '{cmd[0]}' failed")
                self.app.toast(f"{cmd[0]} failed: {exc}", "error")

    def _render(self):
        for w in self.rows.winfo_children():
            w.destroy()
        for i, (label, hint, _fn) in enumerate(self.filtered[:9]):
            active = i == self.selected
            row = tk.Frame(self.rows, bg=self.t.accent if active
                           else self.t["card"])
            row.pack(fill=tk.X, pady=1)
            fg = "#ffffff" if active else self.t["text"]
            fg2 = "#ffffff" if active else self.t["text_muted"]
            if isinstance(_fn, tuple) and _fn and _fn[0] == "sym":
                kind, _, name = label.partition("  ")
                tk.Label(row, text=name, bg=row.cget("bg"), fg=fg,
                         font=(FONT_MONO, 10), anchor="w").pack(
                    side=tk.LEFT, padx=10, pady=6)
                tk.Label(row, text=kind, bg=row.cget("bg"),
                         fg=self.t.accent if not active else fg,
                         font=(FONT_MONO, 8, "bold")).pack(
                    side=tk.LEFT, padx=(0, 8))
                tk.Label(row, text=hint, bg=row.cget("bg"), fg=fg2,
                         font=(FONT_UI, 8)).pack(side=tk.RIGHT, padx=10)
            else:
                tk.Label(row, text=label, bg=row.cget("bg"), fg=fg,
                         font=(FONT_UI, 10), anchor="w").pack(
                    side=tk.LEFT, padx=10, pady=6)
                if hint:
                    tk.Label(row, text=hint, bg=row.cget("bg"), fg=fg2,
                             font=(FONT_UI, 8)).pack(side=tk.RIGHT, padx=10)
            row.bind("<Button-1>", lambda e, i=i: self._pick(i))
        if not self.filtered:
            tk.Label(self.rows, text="no matching command",
                     bg=self.t["card"], fg=self.t["text_muted"],
                     font=(FONT_UI, 9)).pack(pady=8)
        # re-fit the window so it never trails a big empty area
        try:
            self._center()
        except tk.TclError:
            pass

    def _pick(self, i):
        self.selected = i
        self._run_selected()

    def _center(self):
        self.update_idletasks()
        w = 520
        h = min(560, self.winfo_reqheight())
        sw = self.winfo_screenwidth()
        x = self.app.root.winfo_rootx() + \
            max(0, (self.app.root.winfo_width() - w) // 2)
        y = self.app.root.winfo_rooty() + 80
        self.geometry(f"{w}x{h}+{max(0, x)}+{y}")

    def close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class QuickOpen(tk.Toplevel):
    """Fuzzy file opener across the workspace (Ctrl+P, VSCode style)."""

    MAX_FILES = 600

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.t = t = app.theme
        self.files = self._scan()
        self.filtered = list(self.files)
        self.selected = 0
        self.title("Quick Open")
        self.configure(bg=t["card"])
        self.transient(app.root)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        wrap = tk.Frame(self, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        wrap.pack(fill=tk.BOTH, expand=True)
        self.entry = tk.Entry(wrap, bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"], relief=tk.FLAT,
                              font=(FONT_UI, 12), highlightthickness=0)
        self.entry.pack(fill=tk.X, padx=12, pady=12, ipady=6)
        self.entry.insert(0, "")
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", lambda e: self._open_selected())
        self.entry.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Down>", lambda e: self._move(1))

        tk.Label(wrap, text="type a file name · ↑↓ to pick · Enter to open",
                 bg=t["card"], fg=t["text_muted"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=14)
        self.rows = tk.Frame(wrap, bg=t["card"])
        self.rows.pack(fill=tk.X, padx=8, pady=(2, 10))
        self._render()
        self._center()
        self.entry.focus_set()
        self.bind("<Escape>", lambda e: self.close())

    def _scan(self):
        base = self.app.project_dir or os.path.expanduser("~")
        out = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in TREE_SKIP]
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext and ext not in TEXT_EXTS:
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, base)
                out.append((name, rel, full))
                if len(out) >= self.MAX_FILES:
                    return out
        out.sort(key=lambda r: r[1].lower())
        return out

    def _on_type(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        q = self.entry.get().strip().lower()
        if not q:
            self.filtered = list(self.files)
        else:
            scored = []
            for name, rel, full in self.files:
                low = rel.lower()
                if q in low:
                    # prefer hits closer to the file name
                    score = low.rfind(q) - len(low)
                    scored.append((score, (name, rel, full)))
            scored.sort(key=lambda p: p[0])
            self.filtered = [item for _, item in scored]
        self.selected = 0
        self._render()

    def _move(self, delta):
        if self.filtered:
            self.selected = (self.selected + delta) % len(self.filtered)
            self._render()

    def _open_selected(self):
        if not self.filtered:
            return
        item = self.filtered[min(self.selected, len(self.filtered) - 1)]
        self.close()
        self.app.open_file(item[2])

    def _render(self):
        for w in self.rows.winfo_children():
            w.destroy()
        for i, (name, rel, _full) in enumerate(self.filtered[:9]):
            active = i == self.selected
            row = tk.Frame(self.rows, bg=self.t.accent if active
                           else self.t["card"])
            row.pack(fill=tk.X, pady=1)
            fg = "#ffffff" if active else self.t["text"]
            fg2 = "#ffffff" if active else self.t["text_muted"]
            tk.Label(row, text=name, bg=row.cget("bg"), fg=fg,
                     font=(FONT_UI, 10), anchor="w").pack(
                side=tk.LEFT, padx=10, pady=5)
            tk.Label(row, text=rel, bg=row.cget("bg"), fg=fg2,
                     font=(FONT_UI, 8), anchor="e").pack(
                side=tk.RIGHT, padx=10)
            row.bind("<Button-1>", lambda e, i=i: self._pick(i))
        if not self.filtered:
            tk.Label(self.rows, text="no matching files",
                     bg=self.t["card"], fg=self.t["text_muted"],
                     font=(FONT_UI, 9)).pack(pady=8)
        try:
            self._center()
        except tk.TclError:
            pass

    def _pick(self, i):
        self.selected = i
        self._open_selected()

    def _center(self):
        self.update_idletasks()
        w = 560
        h = min(520, self.winfo_reqheight())
        x = self.app.root.winfo_rootx() + \
            max(0, (self.app.root.winfo_width() - w) // 2)
        y = self.app.root.winfo_rooty() + 80
        self.geometry(f"{w}x{h}+{max(0, x)}+{y}")

    def close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class DXN1Studio:
    def __init__(self, config, smoke_test=False, no_splash=False):
        self.config = config
        self.theme = from_config(config)
        self.smoke_test = smoke_test
        self.no_splash = no_splash
        self.restart_requested = False

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}  ·  v{APP_VERSION}-{APP_CHANNEL}")
        self.root.geometry("1280x820")
        self.root.minsize(940, 580)
        self.root.configure(bg=self.theme["bg"])

        self.open_files = {}
        self.active_file = None
        self.sidebar_visible = True
        self.sidebar_view = "explorer"
        self.terminal_visible = True
        self._tab_frames = {}
        self._buffers = {}          # path -> {"content": str, "dirty": bool}
        self._autosave_job = None
        self._palette = None
        self._quick_open = None
        self._split = None          # second editor when split view is on
        self.zen_mode = False
        self._zen_state = None
        self._updater_shown = False

        self.project_dir = None
        self.project_kind = "empty"
        self.pending_project = None      # from --project CLI arg
        self.agent_panel = None
        self.agents_visible = False
        self._hub = None
        self._wizard = None
        self._tour = None
        self._splash_active = False
        self.proc = None
        self._proc_q = queue.Queue()

        self.widgets = {}
        self.first_launch = config.register_launch()
        self.setup_ui()
        self.setup_menu()
        self.setup_bindings()

        errors.set_notifier(self.toast)
        errors.install(self.root)
        self.editor.auto_indent = \
            bool(self.config.get("editor_auto_indent", True))
        self.editor.auto_close = \
            bool(self.config.get("editor_auto_close", True))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._greet()
        if not self.smoke_test and self.config.get("check_updates", True):
            self.root.after(4000, lambda: self.check_for_updates(manual=False))

    # ------------------------------------------------------------------- ui
    def setup_ui(self):
        t = self.theme

        # status bar (packed first so it always stays visible)
        self.statusbar = tk.Frame(self.root, bg=t["statusbar"], height=30)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.statusbar.pack_propagate(False)

        left = tk.Frame(self.statusbar, bg=t["statusbar"])
        left.pack(side=tk.LEFT, padx=12)
        self.status_ready = tk.Label(left, text="● Ready", bg=t["statusbar"],
                                     fg=t["success"], font=(FONT_UI, 9, "bold"))
        self.status_ready.pack(side=tk.LEFT)
        self.status_file = tk.Label(left, text="No file open", bg=t["statusbar"],
                                    fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_file.pack(side=tk.LEFT, padx=(14, 0))
        self.status_pos = tk.Label(left, text="", bg=t["statusbar"],
                                   fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_pos.pack(side=tk.LEFT, padx=(14, 0))
        self.status_ws = tk.Label(left, text="", bg=t["statusbar"],
                                  fg=t.accent, font=(FONT_UI, 9, "bold"))
        self.status_ws.pack(side=tk.LEFT, padx=(14, 0))
        self.status_branch = tk.Label(left, text="", bg=t["statusbar"],
                                      fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_branch.pack(side=tk.LEFT, padx=(10, 0))

        right = tk.Frame(self.statusbar, bg=t["statusbar"])
        right.pack(side=tk.RIGHT, padx=12)
        self.status_agents = tk.Label(right, text="", bg=t["statusbar"],
                                      fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_agents.pack(side=tk.RIGHT, padx=(0, 10))
        tk.Label(right, text=f"v{APP_VERSION}-{APP_CHANNEL}", bg=t["statusbar"],
                 fg=t["text_muted"], font=(FONT_UI, 9)).pack(side=tk.RIGHT)

        # toast layer (placed above the status bar, right aligned)
        self.toast_layer = tk.Frame(self.root, bg=t["bg"])
        self.toast_layer.place(relx=1.0, rely=1.0, x=-14, y=-44,
                               anchor="se")

        # themed menu bar — drawn by us so dark mode never flashes a
        # system-white strip above the studio (the native menubar can't
        # be recoloured on Linux/X11)
        self.menu_bar = tk.Frame(self.root, bg=t["header"], height=32)
        self.menu_bar.pack(side=tk.TOP, fill=tk.X)
        self.menu_bar.pack_propagate(False)

        # body: activity rail + main panes
        body = tk.Frame(self.root, bg=t["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        self.body = body

        self.activity = tk.Frame(body, width=46, bg=t["header"])
        self.activity.pack(side=tk.LEFT, fill=tk.Y)
        self.activity.pack_propagate(False)
        self._build_activity()

        # the agents dock claims its right rail BEFORE the pane cavity is
        # handed out (pack order = slab order in Tk)
        self.agents_visible = bool(self.config.get("agents_enabled"))
        self._build_agent_panel()

        # NOTE: uses theme["border"]; v1.0 crashed here (DARK_BORDER)
        self.main_container = tk.PanedWindow(body, orient=tk.HORIZONTAL,
                                             bg=t["border"], sashwidth=3,
                                             bd=0)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ---- sidebar container with switchable views
        self.sidebar_container = tk.Frame(self.main_container,
                                          bg=t["sidebar"])
        self.sidebar = FileTree(self.sidebar_container, t,
                                on_file_select=self.open_file,
                                on_context=self._explorer_menu)
        self.sidebar.pack(fill=tk.BOTH, expand=True)
        self.search_view = SearchPanel(self.sidebar_container, t,
                                       on_open_match=self.open_search_match)
        self.git_view = GitPanel(self.sidebar_container, t,
                                 on_open_file=self.open_file,
                                 on_log=lambda msg: self.terminal.log(msg))
        self.packages_view = PackagesView(self.sidebar_container, t)
        self.main_container.add(self.sidebar_container, width=252,
                                minsize=190)
        self.show_sidebar_view("explorer", initial=True)

        self.right_panel = tk.PanedWindow(self.main_container,
                                          orient=tk.VERTICAL,
                                          bg=t["border"], sashwidth=3, bd=0)
        self.main_container.add(self.right_panel)

        editor_container = tk.Frame(self.right_panel, bg=t["editor"])

        toolbar = tk.Frame(editor_container, bg=t["header"], height=38)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        self.toolbar = toolbar
        self._build_toolbar()

        tabs_frame = tk.Frame(editor_container, bg=t["header"], height=36)
        tabs_frame.pack(fill=tk.X)
        tabs_frame.pack_propagate(False)
        self.tabs_frame = tabs_frame

        self.findbar = self._build_findbar(editor_container)

        self.editor = CodeEditor(editor_container, t)
        self.editor.text.bind("<KeyRelease>", self._on_editor_key)
        self.editor.text.bind("<ButtonRelease-1>", self._update_cursor_pos)
        self.editor.set_font_size(self.config.get("editor_font_size", 11))
        self.editor.set_wrap(bool(self.config.get("word_wrap", False)))
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.right_panel.add(editor_container, minsize=200)

        self.terminal = Terminal(self.right_panel, t, greeting="Ready",
                                 on_command=self.handle_terminal_command)
        self.right_panel.add(self.terminal, height=200, minsize=80)
        # keep the editor the pane that grows: pin the sash so the
        # terminal keeps its height when the window resizes — until the
        # user drags it themselves
        self._sash_user = False
        self.right_panel.bind("<B1-Motion>",
                              lambda e: setattr(self, "_sash_user", True))
        self.right_panel.bind("<Configure>", self._pin_sash, add="+")

        self.widgets = {
            "sidebar": self.sidebar,
            "sidebar_container": self.sidebar_container,
            "activity": self.activity,
            "search": self.search_view,
            "git": self.git_view,
            "packages": self.packages_view,
            "tabs_frame": self.tabs_frame,
            "toolbar": self.toolbar,
            "editor": self.editor,
            "terminal": self.terminal,
        }

        # DXN1 Agents dock — built above; just refresh its status here
        self._refresh_agents_status()

    # --------------------------------------------------------- activity bar
    def _build_activity(self):
        t = self.theme
        self._activity_items = []
        for key, tip, cmd in (
                ("explorer", "Explorer", lambda: self.show_sidebar_view("explorer")),
                ("search", "Search in files", lambda: self.show_sidebar_view("search")),
                ("git", "Source control", lambda: self.show_sidebar_view("git")),
                ("packages", "Packages", lambda: self.show_sidebar_view("packages"))):
            self._activity_items.append(
                self._activity_button(key, tip, cmd, top=True))
        tk.Frame(self.activity, bg=t["border"], height=1).pack(
            fill=tk.X, pady=(6, 6), padx=8)
        for key, tip, cmd in (
                ("hub", "Project Hub", self.open_hub),
                ("agents", "DXN1 Agents", self.toggle_agents_panel)):
            self._activity_items.append(
                self._activity_button(key, tip, cmd, top=False))
        self._paint_activity()

    def _activity_button(self, key, tip, cmd, top=True):
        t = self.theme
        side = tk.TOP if top else tk.BOTTOM
        canvas = tk.Canvas(self.activity, width=46, height=42,
                           bg=t["header"], highlightthickness=0,
                           cursor="hand2")
        canvas.pack(side=side)
        canvas.bind("<Button-1>", lambda e: cmd())
        canvas.bind("<Enter>", lambda e: self._paint_activity_item(
            key, hover=True))
        canvas.bind("<Leave>", lambda e: self._paint_activity_item(key))
        item = {"key": key, "canvas": canvas, "tip": tip}
        self._draw_activity_icon(canvas, key)
        return item

    def _draw_activity_icon(self, canvas, kind, hover=False):
        t = self.theme
        active = (self.sidebar_view == kind) if kind in \
            ("explorer", "search", "packages") else \
            (kind == "agents" and self.agents_visible)
        color = t["text"] if hover else (t.accent if active
                                         else t["text_muted"])
        canvas.delete("all")
        if active:
            canvas.create_rectangle(0, 0, 3, 42, fill=t.accent, outline="")
        if kind == "explorer":
            canvas.create_rectangle(12, 11, 34, 31, outline=color, width=2)
            for y in (17, 22, 27):
                canvas.create_line(16, y, 30, y, fill=color)
        elif kind == "search":
            canvas.create_oval(12, 11, 26, 25, outline=color, width=2)
            canvas.create_line(25, 24, 33, 32, fill=color, width=2)
        elif kind == "git":
            # branch glyph: a node with two commits
            canvas.create_line(23, 12, 23, 30, fill=color, width=2)
            canvas.create_oval(19, 8, 27, 16, outline=color, width=2)
            canvas.create_oval(19, 26, 27, 34, outline=color, width=2)
            canvas.create_line(27, 30, 33, 30, fill=color, width=2)
            canvas.create_oval(31, 26, 37, 34, outline=color, width=2)
        elif kind == "packages":
            canvas.create_rectangle(11, 13, 35, 31, outline=color, width=2)
            canvas.create_line(11, 20, 35, 20, fill=color)
            canvas.create_line(23, 13, 23, 20, fill=color)
        elif kind == "hub":
            for x, y in ((12, 11), (25, 11), (12, 24), (25, 24)):
                canvas.create_rectangle(x, y, x + 9, y + 9,
                                        outline=color, width=2)
        elif kind == "agents":
            canvas.create_polygon(23, 11, 33, 21, 23, 31, 13, 21,
                                  outline=color, width=2, fill="")

    def _paint_activity_item(self, key, hover=False):
        for item in self._activity_items:
            if item["key"] == key:
                self._draw_activity_icon(item["canvas"], key, hover=hover)

    def _paint_activity(self):
        for item in self._activity_items:
            self._draw_activity_icon(item["canvas"], item["key"])

    # ------------------------------------------------------- sidebar views
    def show_sidebar_view(self, name, initial=False):
        if name not in ("explorer", "search", "git", "packages"):
            return
        self.sidebar_view = name
        self.sidebar.pack_forget()
        for view in (self.search_view, self.git_view, self.packages_view):
            view.pack_forget()
        view = {"explorer": self.sidebar, "search": self.search_view,
                "git": self.git_view,
                "packages": self.packages_view}[name]
        view.pack(fill=tk.BOTH, expand=True)
        self._paint_activity()
        if name == "search":
            self.search_view.set_workspace(self.project_dir)
            self.search_view.entry.focus_set()
        elif name == "git":
            self.git_view.set_workspace(self.project_dir)

    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self.main_container.forget(self.sidebar_container)
        else:
            self.main_container.forget(self.right_panel)
            self.main_container.add(self.sidebar_container, width=252,
                                    minsize=190)
            self.main_container.add(self.right_panel)
        self.sidebar_visible = not self.sidebar_visible
        self._paint_activity()

    def _pin_sash(self, event=None):
        """Editor absorbs window growth; terminal keeps its height."""
        if getattr(self, "_sash_user", False) or not self.terminal_visible:
            return
        self.root.after_idle(self._pin_sash_now)

    def _pin_sash_now(self):
        if self._sash_user or not self.terminal_visible:
            return
        try:
            h = self.right_panel.winfo_height()
            if h > 340 and str(self.terminal) in self.right_panel.panes():
                self.right_panel.sash_place(0, 0, h - 224)
        except (tk.TclError, IndexError):
            pass

    def _build_agent_panel(self):
        if self.agent_panel is not None:
            return
        # docked OUTSIDE the paned window (like VS Code's side bars):
        # a fixed-width right rail that never fights the editor for space
        self.agent_panel = DXN1AgentPanel(self.body, self)
        self.agent_panel.configure(width=300)
        self.agent_panel.pack_propagate(False)
        if self.project_dir:
            self.agent_panel.set_workspace(self.project_dir)
        if self.agents_visible:
            kw = {"side": tk.RIGHT, "fill": tk.Y}
            # re-packs (toggles) must land before the panes in pack order
            if getattr(self, "main_container", None) is not None:
                kw["before"] = self.main_container
            self.agent_panel.pack(**kw)
        self.widgets["agents"] = self.agent_panel
        self._paint_activity()

    def apply_agents_visibility(self):
        enabled = bool(self.config.get("agents_enabled"))
        if enabled and self.agent_panel is None:
            self._build_agent_panel()
            self.agents_visible = True
            self.agent_panel.pack(side=tk.RIGHT, fill=tk.Y,
                                  before=self.main_container)
        elif not enabled and self.agent_panel is not None:
            try:
                self.agent_panel.pack_forget()
            except tk.TclError:
                pass
            self.agent_panel.destroy()
            self.agent_panel = None
            self.widgets.pop("agents", None)
            self.agents_visible = False
        elif enabled and self.agent_panel is not None and \
                self.agents_visible and \
                not self.agent_panel.winfo_ismapped():
            self.agent_panel.pack(side=tk.RIGHT, fill=tk.Y,
                                  before=self.main_container)
        if self.agent_panel is not None:
            self.agent_panel.refresh_mode()
        self._build_toolbar()
        self.setup_menu()          # rebuild so agent entries appear/disappear
        self._refresh_agents_status()
        self._paint_activity()

    def toggle_agents_panel(self):
        if self.agent_panel is None:
            return
        if self.agents_visible:
            try:
                self.agent_panel.pack_forget()
            except tk.TclError:
                pass
            self.agents_visible = False
        else:
            self.agent_panel.pack(side=tk.RIGHT, fill=tk.Y,
                                  before=self.main_container)
            self.agents_visible = True
        self._paint_activity()

    def _refresh_agents_status(self):
        if not self.config.get("agents_enabled"):
            self.status_agents.config(text="")
            return
        full = not self.config.get("agents_ask_edits") and \
            not self.config.get("agents_ask_commands")
        self.status_agents.config(
            text=f"◆ Agents: {llm.describe_backend(self.config)} · "
                 f"{'full access' if full else 'ask mode'}",
            fg=self.theme["success"] if full else self.theme["text_muted"])

    def setup_menu(self):
        """Build the in-app themed menu bar (replaces the native one,
        which cannot be dark-themed on Linux/X11)."""
        t = self.theme
        bar_defs = []
        menu_opts = dict(tearoff=0, bg=t["sidebar"], fg=t["text"],
                         activebackground=t["hover"],
                         activeforeground=t["text"], bd=0)

        file_menu = tk.Menu(self.menu_bar, **menu_opts)
        recents = self.config.get("recent_files") or []
        file_menu.add_command(label="New File", command=self.new_file,
                              accelerator="Ctrl+N")
        file_menu.add_command(label="Open File…", command=self.open_file_dialog,
                              accelerator="Ctrl+O")
        file_menu.add_command(label="Quick Open…", command=self.open_quick_open,
                              accelerator="Ctrl+P")
        if recents:
            recent_menu = tk.Menu(file_menu, **menu_opts)
            shown = 0
            for path in recents:
                if os.path.isfile(path):
                    recent_menu.add_command(
                        label=f"{os.path.basename(path)}  ·  "
                              f"{os.path.dirname(path)}",
                        command=lambda p=path: self.open_file(p))
                    shown += 1
                if shown >= 10:
                    break
            if shown:
                file_menu.add_cascade(label="Open Recent", menu=recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_file,
                              accelerator="Ctrl+S")
        file_menu.add_command(label="Save As…", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Project Hub…", command=self.open_hub)
        file_menu.add_command(label="Open Workspace…",
                              command=self.open_workspace_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Export Project as ZIP…",
                              command=self.export_project_zip)
        file_menu.add_command(label="Export Current File As…",
                              command=self.export_current_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        bar_defs.append(("File", file_menu))

        edit_menu = tk.Menu(self.menu_bar, **menu_opts)
        txt = lambda: self.editor.text
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z",
                              command=lambda: txt().event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y",
                              command=lambda: txt().event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X",
                              command=lambda: txt().event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C",
                              command=lambda: txt().event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V",
                              command=lambda: txt().event_generate("<<Paste>>"))
        edit_menu.add_command(label="Find…", command=self.toggle_find,
                              accelerator="Ctrl+F")
        edit_menu.add_command(label="Replace…", command=self.open_replace,
                              accelerator="Ctrl+H")
        edit_menu.add_command(label="Go to Line…", command=self.goto_line_dialog,
                              accelerator="Ctrl+G")
        edit_menu.add_separator()
        edit_menu.add_command(label="Toggle Comment",
                              accelerator="Ctrl+/",
                              command=self.editor.toggle_comment)
        edit_menu.add_command(label="Duplicate Line",
                              accelerator="Ctrl+Shift+D",
                              command=self.editor.duplicate_line)
        edit_menu.add_command(label="Delete Line",
                              accelerator="Ctrl+Shift+K",
                              command=self.editor.delete_line)
        edit_menu.add_command(label="Move Line Up", accelerator="Alt+Up",
                              command=lambda: self.editor.move_line(-1))
        edit_menu.add_command(label="Move Line Down", accelerator="Alt+Down",
                              command=lambda: self.editor.move_line(1))
        edit_menu.add_separator()
        edit_menu.add_command(label="Bigger Text", accelerator="Ctrl++",
                              command=lambda: self.change_font_size(1))
        edit_menu.add_command(label="Smaller Text", accelerator="Ctrl+-",
                              command=lambda: self.change_font_size(-1))
        wrap_state = tk.BooleanVar(
            value=bool(self.config.get("word_wrap", False)))
        edit_menu.add_checkbutton(label="Word Wrap", variable=wrap_state,
                                  command=self.toggle_word_wrap)
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings…", command=self.open_settings,
                              accelerator="Ctrl+,")
        bar_defs.append(("Edit", edit_menu))

        view_menu = tk.Menu(self.menu_bar, **menu_opts)
        view_menu.add_command(label="Command Palette",
                              command=self.open_palette,
                              accelerator="Ctrl+K")
        view_menu.add_command(label="Quick Open File",
                              command=self.open_quick_open,
                              accelerator="Ctrl+P")
        view_menu.add_separator()
        view_menu.add_command(label="Split Editor",
                              command=self.toggle_split,
                              accelerator="Ctrl+\\")
        view_menu.add_command(label="Zen Mode",
                              command=self.toggle_zen,
                              accelerator="Ctrl+Alt+Z")
        view_menu.add_command(label="Explorer", command=lambda:
                              self.show_sidebar_view("explorer"))
        view_menu.add_command(label="Search in Files", command=lambda:
                              self.show_sidebar_view("search"))
        view_menu.add_command(label="Source Control", command=lambda:
                              self.show_sidebar_view("git"))
        view_menu.add_command(label="Packages", command=lambda:
                              self.show_sidebar_view("packages"))
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal)
        view_menu.add_command(label="Toggle Sidebar", command=self._toggle_sidebar)
        if self.config.get("agents_enabled"):
            view_menu.add_command(label="Toggle DXN1 Agents",
                                  command=self.toggle_agents_panel)
        view_menu.add_separator()
        view_menu.add_command(
            label=f"Switch to {'Light' if self.theme.is_dark else 'Dark'} Theme",
            command=self.switch_theme)
        bar_defs.append(("View", view_menu))

        tools_menu = tk.Menu(self.menu_bar, **menu_opts)
        tools_menu.add_command(label="Run Project", command=self.run_current,
                               accelerator="F5")
        tools_menu.add_command(label="Stop", command=self.stop_run)
        tools_menu.add_separator()
        tools_menu.add_command(label="Manage Packages…", command=lambda:
                               self.show_sidebar_view("packages"))
        tools_menu.add_command(label="Search in Files…", command=lambda:
                               self.show_sidebar_view("search"))
        tools_menu.add_command(label="Project Hub…", command=self.open_hub)
        if self.config.get("agents_enabled"):
            tools_menu.add_command(label=f"{AGENTS_NAME} Settings…",
                                   command=lambda: AgentSettingsDialog(self))
            tools_menu.add_command(label=f"Connect a Brain…",
                                   command=lambda: ConnectDialog(self))
        bar_defs.append(("Tools", tools_menu))

        help_menu = tk.Menu(self.menu_bar, **menu_opts)
        help_menu.add_command(label="Check for Updates…",
                              command=lambda: self.check_for_updates(manual=True))
        help_menu.add_command(label="Keyboard Shortcuts",
                              command=self.show_shortcuts)
        help_menu.add_command(label="Replay Welcome & Tour",
                              command=self.start_wizard)
        help_menu.add_separator()
        help_menu.add_command(label="About DXN1 STUDIO", command=self.show_about)
        bar_defs.append(("Help", help_menu))

        self._render_menu_bar(bar_defs)

    def _render_menu_bar(self, bar_defs):
        """Paint the themed top bar: brand mark + one Menubutton per menu."""
        t = self.theme
        for child in self.menu_bar.winfo_children():
            child.destroy()
        tk.Label(self.menu_bar, text="◆", bg=t["header"], fg=t.accent,
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=(12, 6))
        tk.Label(self.menu_bar, text="DXN1 STUDIO", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9, "bold")
                 ).pack(side=tk.LEFT)
        tk.Label(self.menu_bar, text=f"v{APP_VERSION}-{APP_CHANNEL}",
                 bg=t["header"], fg=t["text_muted"], font=(FONT_MONO, 8)
                 ).pack(side=tk.LEFT, padx=(8, 0))
        for label, menu in bar_defs:
            btn = tk.Menubutton(self.menu_bar, text=label, menu=menu,
                                bg=t["header"], fg=t["text_secondary"],
                                activebackground=t["hover"],
                                activeforeground=t["text"],
                                font=(FONT_UI, 9), padx=10, pady=6, bd=0,
                                cursor="hand2")
            btn.pack(side=tk.LEFT)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=t["hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=t["header"]))

    def setup_bindings(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-y>", lambda e:
                       self.editor.text.event_generate("<<Redo>>"))
        self.root.bind("<F5>", lambda e: self.run_current())
        self.root.bind("<Control-comma>", lambda e: self.open_settings())
        self.root.bind("<Control-k>", lambda e: self.open_palette())
        self.root.bind("<Control-K>", lambda e: self.editor.delete_line())
        self.root.bind("<Control-D>", lambda e: self.editor.duplicate_line())
        self.root.bind("<Control-slash>", lambda e: self.editor.toggle_comment())
        self.root.bind("<Control-g>", lambda e: self.goto_line_dialog())
        self.root.bind("<Alt-Up>", lambda e: self.editor.move_line(-1))
        self.root.bind("<Alt-Down>", lambda e: self.editor.move_line(1))
        self.root.bind("<Control-backslash>", lambda e: self.toggle_split())
        self.root.bind("<Control-Alt-z>", lambda e: self.toggle_zen())
        self.root.bind("<Control-p>", lambda e: self.open_quick_open())
        self.root.bind("<Control-P>", lambda e: self.open_quick_open())
        self.root.bind("<Control-f>", lambda e: self.toggle_find())
        # Ctrl+H: the Text class binding maps it to backspace, so the
        # editor widget itself gets a break-binding to swallow that, and
        # the toplevel binding covers every other focus target
        self.editor.text.bind("<Control-h>",
                              lambda e: (self.open_replace(), "break")[1])
        self.root.bind("<Control-h>", lambda e: self.open_replace())
        self.root.bind("<Control-w>", lambda e: self.close_active_tab())
        self.root.bind("<Control-Tab>", lambda e: self.cycle_tab(1))
        self.root.bind("<Control-plus>", lambda e: self.change_font_size(1))
        self.root.bind("<Control-equal>", lambda e: self.change_font_size(1))
        self.root.bind("<Control-minus>", lambda e: self.change_font_size(-1))
        # bookmarks: Ctrl+F2 toggle · F2 next · Shift+F2 previous
        self.root.bind("<Control-F2>", lambda e: self.editor.toggle_bookmark())
        self.root.bind("<F2>", lambda e: self.editor.next_bookmark())
        self.root.bind("<Shift-F2>", lambda e: self.editor.prev_bookmark())
        self.root.bind("<Escape>", self._on_escape)

    def _on_escape(self, event=None):
        if self.findbar.winfo_ismapped():
            self.toggle_find(show=False)
            return "break"

    def _update_cursor_pos(self, event=None):
        try:
            t = self.editor.text
            line, col = t.index("insert").split(".")
            info = f"Ln {line}, Col {int(col) + 1}"
            sel = t.tag_ranges("sel")
            if sel:
                chars = len(t.get(sel[0], sel[1]))
                lines = t.get(sel[0], sel[1]).count("\n") + 1
                info += f"  ·  {chars} chars selected"
                if lines > 1:
                    info += f" ({lines} lines)"
            total = int(t.index("end-1c").split(".")[0])
            info += f"  ·  {total} lines"
            if self.editor.file_path:
                words = len(t.get("1.0", "end-1c").split())
                if words:
                    info += f"  ·  {words} words"
            self.status_pos.config(text=info)
        except Exception:
            pass

    def _on_editor_key(self, event=None):
        """App-level hook for editor keystrokes (cursor pos + dirty tab)."""
        self._update_cursor_pos()
        self._mark_dirty()

    # ------------------------------------------------------------ toolbar
    def _chip(self, parent, text, fg=None, accent=False, cmd=None):
        lbl = tk.Label(parent, text=text,
                       bg=self.theme.accent if accent else self.theme["header"],
                       fg="#ffffff" if accent else (fg or
                                                    self.theme["text_secondary"]),
                       font=(FONT_UI, 9, "bold" if accent else "normal"),
                       cursor="hand2", padx=10, pady=6)
        lbl.pack(side=tk.LEFT, padx=(0, 6), pady=4)
        if cmd:
            default_bg = lbl.cget("bg")
            lbl.bind("<Button-1>", lambda e: cmd())
            lbl.bind("<Enter>", lambda e: lbl.config(
                bg=self.theme["hover"] if not accent else self.theme.accent))
            lbl.bind("<Leave>", lambda e: lbl.config(bg=default_bg))
        return lbl

    def _build_toolbar(self):
        t = self.theme
        for child in self.toolbar.winfo_children():
            child.destroy()
        # right-side chip packed FIRST so it never gets squeezed out
        if self.config.get("agents_enabled"):
            self._agents_chip = tk.Label(
                self.toolbar, text="◆ Agents", bg=t["header"],
                fg=t.accent, font=(FONT_UI, 9, "bold"), cursor="hand2",
                padx=10, pady=6)
            self._agents_chip.pack(side=tk.RIGHT, padx=(6, 12), pady=4)
            self._agents_chip.bind("<Button-1>",
                                   lambda e: self.toggle_agents_panel())
        self._chip(self.toolbar, "+ New", cmd=self.new_file)
        self._chip(self.toolbar, "Open", cmd=self.open_file_dialog)
        self._chip(self.toolbar, "Save", cmd=self.save_file)
        tk.Frame(self.toolbar, bg=t["border"], width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=8)
        self._chip(self.toolbar, "▶ Run", accent=True, cmd=self.run_current)
        self._chip(self.toolbar, "■ Stop", fg=t["text_muted"],
                   cmd=self.stop_run)
        tk.Frame(self.toolbar, bg=t["border"], width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=8)
        self._chip(self.toolbar, "Search", cmd=lambda:
                   self.show_sidebar_view("search"))
        self._chip(self.toolbar, "Git", cmd=lambda:
                   self.show_sidebar_view("git"))
        self._chip(self.toolbar, "Packages", cmd=lambda:
                   self.show_sidebar_view("packages"))
        self._chip(self.toolbar, "Export ZIP", cmd=self.export_project_zip)
        self._chip(self.toolbar, "Hub", cmd=self.open_hub)

    # legacy alias — some callers still say toggle_sidebar
    def toggle_sidebar(self):
        self._toggle_sidebar()

    def show_settings_saved(self):
        self.terminal.log("Settings saved.")

    # ------------------------------------------------------------- session
    def _greet(self):
        name = self.config.get("name") or "developer"
        back = not self.first_launch
        self.terminal.log(f"{APP_NAME} v{APP_VERSION}-{APP_CHANNEL} — "
                          f"{APP_TAGLINE}")
        self.terminal.log(f"{'Welcome back' if back else 'Welcome'}, {name}!")
        self.terminal.log("Type 'help' for studio commands — or press Ctrl+K "
                          "for the command palette.")
        if not self.config.get("onboarded"):
            self.terminal.log("First run detected — starting setup…")

    # ------------------------------------------------------------ boot flow
    def run(self):
        self.root.withdraw()
        if self.smoke_test:
            self._after_splash()
            self._schedule_smoke_test()
        elif self.no_splash or not self.config.get("splash_enabled", True):
            self._after_splash()
        else:
            self._splash_active = True
            Splash(self.root, accent=self.theme.accent, duration_ms=2000,
                   on_done=self._after_splash)
        self.root.mainloop()

    def _after_splash(self):
        self._splash_active = False
        if self.smoke_test:
            return
        if self.config.needs_onboarding:
            self.start_wizard()
            return
        if self.pending_project:
            path = self.pending_project
            self.pending_project = None
            self._show_main(path)
            return
        if self.config.get("hub_on_startup", True):
            self.open_hub()
        else:
            last = self.config.get("last_project") or ""
            self._show_main(last if os.path.isdir(last) else None)

    def _show_main(self, project_path=None):
        """Deiconify the IDE; optionally dive straight into a workspace."""
        kind = "empty"
        if project_path and os.path.isdir(project_path):
            meta = projects.read_project_meta(project_path)
            kind = meta["kind"]
            self._set_workspace(project_path, kind)
            self._restore_session_tabs(project_path)
        self.root.deiconify()
        if not self.config.get("tour_done"):
            self.root.after(800, self.start_tour)

    def _restore_session_tabs(self, project_path):
        """Reopen the tabs (and active file) saved for this workspace."""
        if not self.config.get("restore_session", True):
            return
        sessions = self.config.get("session_tabs") or {}
        data = sessions.get(os.path.abspath(project_path))
        if not data:
            return
        for path in data.get("tabs", []):
            if os.path.isfile(path) and path != self.editor.file_path:
                try:
                    self.open_file(path)
                except Exception:
                    pass
        active = data.get("active")
        if active and os.path.isfile(active):
            try:
                self.open_file(active)
            except Exception:
                pass

    # ------------------------------------------------------------- hub flow
    def open_hub(self):
        if self._hub is not None and self._hub.winfo_exists():
            self._hub.lift()
            return
        preselect = ""
        if self._wizard is None:
            preselect = self.config.get("wizard_first_kind", "")
        self._hub = ProjectHub(self.root, self.config, self.theme,
                               on_open=self._on_hub_open,
                               on_explore=self._on_hub_explore,
                               preselect_kind=preselect)
        if preselect:
            self.config.set("wizard_first_kind", "")

    def _on_hub_open(self, path, kind):
        self._hub = None
        if not self.root.winfo_ismapped():
            self._show_main(path)
        else:
            self._set_workspace(path, kind)
            self.root.deiconify()

    def _on_hub_explore(self):
        self._hub = None
        if not self.root.winfo_ismapped():
            self._show_main(None)
        else:
            self.root.deiconify()

    def open_workspace_dialog(self):
        path = filedialog.askdirectory(title="Open Workspace",
                                       initialdir=self.project_dir
                                       or projects.ensure_projects_root())
        if path:
            self._set_workspace(path,
                                projects.read_project_meta(path)["kind"])

    def _set_workspace(self, path, kind):
        self.project_dir = os.path.abspath(path)
        self.project_kind = kind
        meta = projects.read_project_meta(path)
        name = meta["name"]
        projects.touch_recent(self.config, path, kind)
        self.sidebar.load_directory(self.project_dir)
        self.search_view.set_workspace(self.project_dir)
        self.status_ws.config(text=f"◆ {name}")
        self.status_branch.config(
            text=f"⎇ {self._git_branch()}" if self._git_branch() else "")
        self.root.title(f"{name} — {APP_NAME} · v{APP_VERSION}-{APP_CHANNEL}")
        self.terminal.log(f"Workspace: {name} ({kind}) — {self.project_dir}")
        # bind the agent to this workspace (fresh jail + conversation)
        if self.agent_panel is not None:
            self.agent_panel.set_workspace(self.project_dir)
        # auto-open the most interesting entry file
        if not self.editor.file_path:
            for cand in ("app.py", "main.py"):
                p = os.path.join(self.project_dir, cand)
                if os.path.isfile(p):
                    self.open_file(p)
                    break

    def _git_branch(self):
        if not self.project_dir:
            return ""
        head = os.path.join(self.project_dir, ".git", "HEAD")
        try:
            with open(head, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read().strip()
            return data.rsplit("/", 1)[-1] if data.startswith("ref:") \
                else "detached"
        except OSError:
            return ""

    def refresh_explorer(self):
        self.sidebar.load_directory(self.project_dir or os.path.expanduser("~"))

    # ---------------------------------------------------------- onboarding
    def start_wizard(self):
        if self._wizard is not None and self._wizard.win.winfo_exists():
            return
        self._tour_done_cleanup()
        self._wizard = WelcomeWizard(self.root, self.config,
                                     on_complete=self._on_wizard_complete)

    def _on_wizard_complete(self, config):
        self._wizard = None
        # if the wizard changed look-and-feel, restart into the new theme
        if config.get("theme") != self.theme.mode or \
                config.get("accent") != self.theme.accent_name:
            self.restart_requested = True
            self.root.after(150, self.root.destroy)
            return
        # honour a mid-wizard opt-in (or opt-out) without a restart
        self.apply_agents_visibility()
        self.editor.set_font_size(config.get("editor_font_size", 11))
        self.terminal.log(f"Setup complete — welcome aboard, "
                          f"{config.get('name') or 'developer'}!")
        self.open_hub()

    def start_tour(self):
        if self._tour is not None:
            return
        self._tour = InteractiveTour(self, self.config)
        self.root.after(350, lambda: self._tour.start()
                        if not self._tour.done else None)

    def _tour_done_cleanup(self):
        if self._tour is not None and not self._tour.done:
            self._tour.finish(skipped=True)
        self._tour = None

    # -------------------------------------------------------------- actions
    def new_file(self):
        self.editor.set_content("")
        self.editor.file_path = None
        self.editor.highlighter.set_language(None)
        self.status_file.config(text="Untitled")
        self.terminal.log("Created new file")

    def open_file_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Open File",
            filetypes=[("All Files", "*.*"), ("Python", "*.py"),
                       ("JavaScript", "*.js"), ("HTML", "*.html"),
                       ("CSS", "*.css"), ("Text", "*.txt")])
        if filepath:
            self.open_file(filepath)

    def open_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8",
                      errors="replace") as fh:
                content = fh.read()
        except Exception as e:
            errors.log_exception(f"open {filepath}")
            messagebox.showerror("Error", f"Failed to open file:\n{e}")
            return
        self._buffers[filepath] = {"content": content, "dirty": False}
        self.editor.set_content(content, path=filepath)
        self._sync_split(content, filepath)
        self.status_file.config(text=filepath)
        self._update_cursor_pos()
        self._record_recent_file(filepath)
        self.terminal.log(f"Opened: {filepath}")
        self.add_tab(os.path.basename(filepath), filepath)

    def open_search_match(self, path, line, col):
        self.open_file(path)
        target = f"{int(line)}.{int(col)}"
        try:
            self.editor.text.mark_set("insert", target)
            self.editor.text.see(target)
            self.editor.text.focus_set()
            self._update_cursor_pos()
        except tk.TclError:
            pass

    def _record_recent_file(self, filepath):
        recents = list(self.config.get("recent_files") or [])
        filepath = os.path.abspath(filepath)
        recents = [r for r in recents if r != filepath]
        recents.insert(0, filepath)
        self.config.set("recent_files", recents[:12])

    def open_quick_open(self):
        if self._quick_open is not None:
            try:
                self._quick_open.destroy()
            except tk.TclError:
                pass
        self._quick_open = QuickOpen(self)

    # ------------------------------------------------------------ split view
    def toggle_split(self):
        t = self.theme
        if self._split is not None:
            try:
                self._split.pack_forget()
            except tk.TclError:
                pass
            self._split.destroy()
            self._split = None
            try:
                self.editor.pack_forget()
                self.editor.pack(fill=tk.BOTH, expand=True)
            except tk.TclError:
                pass
            self.terminal.log("Split view closed.")
            return
        self._split = CodeEditor(self.editor.master, t)
        self._split.set_font_size(
            int(self.config.get("editor_font_size", 11)))
        self._split.set_wrap(bool(self.config.get("word_wrap", False)))
        self._split.text.bind("<KeyRelease>", self._on_editor_key)
        self._split.text.bind("<ButtonRelease-1>", self._update_cursor_pos)
        self._split.text.bind("<FocusIn>",
                              lambda e: self._focus_split_side())
        if self.editor.file_path and \
                self.editor.file_path in self._buffers:
            self._split.set_content(self.editor.get_content(),
                                    path=self.editor.file_path)
        else:
            self._split.set_content("")
        self.editor.pack_forget()
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                         padx=(0, 3))
        self._split.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.terminal.log("Split view — same buffer, edit on either side.")

    def _focus_split_side(self):
        """Clicked into the split editor — make it the active editor."""
        if self._split is None or self.editor is self._split:
            return
        old, self.editor = self.editor, self._split
        # push the other side's content into the shared buffer, then load
        path = self.editor.file_path
        if path:
            self._buffers[path] = {"content": old.get_content(),
                                   "dirty": True}
            self.editor.set_content(old.get_content(), path=path)
        self._update_cursor_pos()

    def _sync_split(self, content, path=None):
        """Mirror the active buffer into the split editor (when visible)."""
        if self._split is None or self.editor is self._split:
            return
        try:
            self._split.set_content(content, path=path)
        except tk.TclError:
            pass

    # -------------------------------------------------------------- zen mode
    def toggle_zen(self):
        if not self.zen_mode:
            self._zen_state = (self.sidebar_visible, self.terminal_visible,
                               self.agents_visible,
                               self.findbar.winfo_ismapped())
            if self.sidebar_visible:
                self._toggle_sidebar()
            if self.terminal_visible:
                self.toggle_terminal()
            if self.agents_visible:
                self.toggle_agents_panel()
            if self._zen_state[3]:
                self.toggle_find(show=False)
            self.zen_mode = True
            self.toast("Zen mode — Ctrl+Alt+Z to exit", "info")
        else:
            if self._zen_state:
                side, term, agents, find = self._zen_state
                if side and not self.sidebar_visible:
                    self._toggle_sidebar()
                if term and not self.terminal_visible:
                    self.toggle_terminal()
                if agents and self.agent_panel is not None \
                        and not self.agents_visible:
                    self.toggle_agents_panel()
            self.zen_mode = False
            self.toast("Zen mode off", "info")

    def save_file(self, silent=False):
        if self.editor.file_path:
            try:
                with open(self.editor.file_path, "w", encoding="utf-8") as fh:
                    fh.write(self.editor.get_content())
                if self.editor.file_path in self._buffers:
                    self._buffers[self.editor.file_path] = \
                        {"content": self.editor.get_content(),
                         "dirty": False}
                self._paint_tab_dirty(self.editor.file_path)
                self._sync_split(self.editor.get_content(),
                                 self.editor.file_path)
                self.terminal.log(f"Saved: {self.editor.file_path}")
                if not silent:
                    self.toast("Saved", "success")
            except Exception as e:
                errors.log_exception(f"save {self.editor.file_path}")
                messagebox.showerror("Error", f"Failed to save file:\n{e}")
        else:
            self.save_file_as()

    def save_file_as(self):
        filepath = filedialog.asksaveasfilename(title="Save As",
                                                defaultextension=".txt")
        if filepath:
            self.editor.file_path = filepath
            self._buffers[filepath] = {"content":
                                       self.editor.get_content(),
                                       "dirty": False}
            self.status_file.config(text=filepath)
            self.save_file(silent=True)

    # ---------------------------------------------------------------- tabs
    def add_tab(self, filename, filepath=None):
        filepath = filepath or self.editor.file_path or filename
        if filepath not in self._tab_frames:
            t = self.theme
            tab = tk.Frame(self.tabs_frame, bg=t["header"], cursor="hand2")
            label = tk.Label(tab, text=filename, bg=t["header"], fg=t["text"],
                             font=(FONT_UI, 9))
            label.pack(side=tk.LEFT, padx=10, pady=8)
            close = tk.Label(tab, text="✕", bg=t["header"],
                             fg=t["text_muted"], font=(FONT_UI, 9),
                             cursor="hand2")
            close.pack(side=tk.RIGHT, padx=8)
            bar = tk.Frame(tab, bg=t["header"], height=2)
            bar.pack(side=tk.BOTTOM, fill=tk.X)
            tab.pack(side=tk.LEFT)
            close.bind("<Button-1>", lambda e, p=filepath: self.close_tab(p))
            tab.bind("<Button-2>", lambda e, p=filepath: self.close_tab(p))
            tab.bind("<Button-3>", lambda e, p=filepath, w=tab:
                     self._tab_menu(p, w, e))
            self._tab_frames[filepath] = {"frame": tab, "label": label,
                                          "close": close, "bar": bar}
        self._activate_tab(filepath)

    def _tab_menu(self, filepath, widget, event):
        """Right-click on a tab: close options, copy path, reveal."""
        t = self.theme
        menu = tk.Menu(self.root, tearoff=0, bg=t["sidebar"], fg=t["text"],
                       activebackground=t["hover"],
                       activeforeground=t["text"], font=(FONT_UI, 9))
        menu.add_command(label="Close", accelerator="Ctrl+W",
                         command=lambda: self.close_tab(filepath))
        menu.add_command(label="Close others", command=lambda:
                         self._close_other_tabs(filepath))
        menu.add_command(label="Close all", command=self._close_all_tabs)
        menu.add_separator()
        menu.add_command(label="Copy path", command=lambda:
                         self._copy_path(filepath))
        menu.add_command(label="Reveal in file manager", command=lambda:
                         self.reveal_in_file_manager(filepath))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _close_other_tabs(self, keep):
        for path in list(self._tab_frames):
            if path != keep:
                self.close_tab(path)

    def _close_all_tabs(self):
        for path in list(self._tab_frames):
            self.close_tab(path)

    def reveal_in_file_manager(self, path):
        """Open the OS file manager with the item selected."""
        path = os.path.abspath(path)
        if not os.path.exists(path):
            self.toast("Path no longer exists", "error")
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open",
                                  os.path.dirname(path) or "/"])
        except Exception as exc:  # noqa: BLE001
            self.toast(f"Couldn't open file manager: {exc}", "error")

    def _activate_tab(self, filepath):
        t = self.theme
        for path, w in self._tab_frames.items():
            active = path == filepath
            bg = t["editor"] if active else t["header"]
            w["frame"].config(bg=bg)
            w["label"].config(bg=bg,
                              fg=t["text"] if active else t["text_secondary"])
            w["close"].config(bg=bg)
            w["bar"].config(bg=t.accent if active else bg)
        if filepath and filepath != self.editor.file_path and \
                filepath in self._buffers:
            content = self._buffers[filepath]["content"]
            self.editor.set_content(content, path=filepath)
            self._sync_split(content, filepath)
            self.status_file.config(text=filepath)
            self._update_cursor_pos()

    def _mark_dirty(self, event=None):
        path = self.editor.file_path
        if path and path in self._buffers:
            if not self._buffers[path]["dirty"]:
                self._buffers[path]["dirty"] = True
                self._paint_tab_dirty(path)
        if self.config.get("auto_save", False):
            if self._autosave_job is not None:
                try:
                    self.root.after_cancel(self._autosave_job)
                except Exception:
                    pass
            self._autosave_job = self.root.after(1600,
                                                 lambda: self.save_file(
                                                     silent=True))

    def _paint_tab_dirty(self, path):
        entry = self._tab_frames.get(path)
        if entry is None:
            return
        t = self.theme
        dirty = self._buffers.get(path, {}).get("dirty", False)
        active = path == self.editor.file_path
        bg = t["editor"] if active else t["header"]
        name = os.path.basename(path)
        entry["label"].config(text=f"{'● ' if dirty else ''}{name}", bg=bg)

    def close_active_tab(self):
        if self.editor.file_path:
            self.close_tab(self.editor.file_path)

    def cycle_tab(self, delta):
        paths = list(self._tab_frames)
        if len(paths) < 2:
            return
        try:
            i = paths.index(self.editor.file_path)
        except ValueError:
            i = 0
        self.open_file(paths[(i + delta) % len(paths)]) \
            if paths[(i + delta) % len(paths)] != self.editor.file_path else \
            self._activate_tab(paths[(i + delta) % len(paths)])

    def close_tab(self, filepath):
        entry = self._tab_frames.pop(filepath, None)
        if entry is None:
            return
        entry["frame"].destroy()
        self._buffers.pop(filepath, None)
        self.terminal.log(f"Closed: {os.path.basename(filepath)}")
        if self.editor.file_path == filepath:
            if self._tab_frames:
                last = list(self._tab_frames)[-1]
                self.editor.file_path = None
                self._activate_tab(last)
            else:
                self.editor.set_content("")
                self.editor.file_path = None
                self.editor.highlighter.set_language(None)
                self.status_file.config(text="No file open")
                self.status_pos.config(text="")

    # ------------------------------------------------------------- find bar
    def _build_findbar(self, parent):
        t = self.theme
        bar = tk.Frame(parent, bg=t["header"])
        row = tk.Frame(bar, bg=t["header"])
        row.pack(fill=tk.X, padx=10, pady=6)
        self._find_row = row
        tk.Label(row, text="⌕", bg=t["header"], fg=t.accent,
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT)
        self.find_var = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.find_var, bg=t["editor"],
                         fg=t["text"], insertbackground=t["text"],
                         relief=tk.FLAT, font=(FONT_MONO, 10),
                         highlightthickness=1, highlightbackground=t["border"],
                         highlightcolor=t.accent, width=28)
        entry.pack(side=tk.LEFT, padx=(8, 6), ipady=4)
        entry.bind("<Return>", lambda e: self._find_next(1))
        entry.bind("<KeyRelease>", self._find_live)
        self.find_count = tk.Label(row, text="", bg=t["header"],
                                   fg=t["text_muted"], font=(FONT_UI, 9),
                                   width=10)
        self.find_count.pack(side=tk.LEFT)
        for label, delta in (("↑", -1), ("↓", 1)):
            btn = tk.Label(row, text=label, bg=t["header"],
                           fg=t["text_secondary"], font=(FONT_UI, 10, "bold"),
                           cursor="hand2", padx=8)
            btn.pack(side=tk.LEFT)
            btn.bind("<Button-1>", lambda e, d=delta: self._find_next(d))
        self.find_regex = False
        self.regex_btn = tk.Label(row, text=".*", bg=t["header"],
                                  fg=t["text_muted"],
                                  font=(FONT_MONO, 9, "bold"),
                                  cursor="hand2", padx=7)
        self.regex_btn.pack(side=tk.LEFT)
        self.regex_btn.bind("<Button-1>",
                            lambda e: self._toggle_find_regex())
        self.replace_chevron = tk.Label(row, text="⌄ replace", bg=t["header"],
                                        fg=t["text_secondary"],
                                        font=(FONT_UI, 9), cursor="hand2",
                                        padx=8)
        self.replace_chevron.pack(side=tk.LEFT)
        self.replace_chevron.bind("<Button-1>",
                                  lambda e: self.toggle_replace())
        x = tk.Label(row, text="✕", bg=t["header"], fg=t["text_muted"],
                     font=(FONT_UI, 10), cursor="hand2", padx=8)
        x.pack(side=tk.RIGHT)
        x.bind("<Button-1>", lambda e: self.toggle_find(show=False))

        # ---- replace row (hidden until the chevron or Ctrl+H) ----
        self.replace_row = tk.Frame(bar, bg=t["header"])
        tk.Label(self.replace_row, text="→", bg=t["header"],
                 fg=t["text_muted"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT)
        self.replace_var = tk.StringVar()
        rentry = tk.Entry(self.replace_row, textvariable=self.replace_var,
                          bg=t["editor"], fg=t["text"],
                          insertbackground=t["text"], relief=tk.FLAT,
                          font=(FONT_MONO, 10), highlightthickness=1,
                          highlightbackground=t["border"],
                          highlightcolor=t.accent, width=28)
        rentry.pack(side=tk.LEFT, padx=(8, 6), ipady=4)
        rentry.bind("<Return>", lambda e: self._replace_current())
        rbtn = tk.Label(self.replace_row, text="Replace", bg=t["card"],
                        fg=t["text"], font=(FONT_UI, 9, "bold"),
                        cursor="hand2", padx=9, pady=3)
        rbtn.pack(side=tk.LEFT, padx=2)
        rbtn.bind("<Button-1>", lambda e: self._replace_current())
        rabtn = tk.Label(self.replace_row, text="Replace all", bg=t["card"],
                         fg=t["text"], font=(FONT_UI, 9, "bold"),
                         cursor="hand2", padx=9, pady=3)
        rabtn.pack(side=tk.LEFT, padx=2)
        rabtn.bind("<Button-1>", lambda e: self._replace_all())
        self.replace_status = tk.Label(self.replace_row, text="", bg=t["header"],
                                       fg=t["text_muted"], font=(FONT_UI, 9))
        self.replace_status.pack(side=tk.LEFT, padx=6)
        return bar

    def toggle_replace(self, show=None):
        """Show/hide the replace row under the find bar."""
        visible = self.replace_row.winfo_ismapped()
        if show is None:
            show = not visible
        if show and not visible:
            self.replace_row.pack(fill=tk.X, padx=10, pady=(0, 6),
                                  after=self._find_row)
            self.replace_chevron.config(text="⌃ replace")
        elif not show and visible:
            self.replace_row.pack_forget()
            self.replace_chevron.config(text="⌄ replace")
            self.replace_status.config(text="")

    def open_replace(self):
        """Ctrl+H — find bar with the replace row visible."""
        if not self.findbar.winfo_ismapped():
            self.toggle_find(show=True)
        self.toggle_replace(show=True)
        for w in self.replace_row.winfo_children():
            if isinstance(w, tk.Entry):
                w.focus_set()
                break

    def _replace_current(self):
        needle, repl = self.find_var.get(), self.replace_var.get()
        if not needle:
            return
        if self.editor.replace_current(needle, repl,
                                       regex=self.find_regex):
            self.replace_status.config(text="replaced 1",
                                       fg=self.theme.accent)
        else:
            self.replace_status.config(text="no selection — pick a hit first",
                                       fg=self.theme["text_muted"])
        self._find_live()

    def _replace_all(self):
        needle, repl = self.find_var.get(), self.replace_var.get()
        if not needle:
            return
        count = self.editor.replace_all(needle, repl,
                                        regex=self.find_regex)
        if count < 0:
            self.replace_status.config(text="bad regex", fg="#f87171")
            return
        self.replace_status.config(
            text=(f"replaced {count}" if count else "no hits"),
            fg=(self.theme.accent if count else self.theme["text_muted"]))
        self._find_live()

    def toggle_find(self, show=None):
        visible = self.findbar.winfo_ismapped()
        if show is None:
            show = not visible
        if show and not visible:
            self.findbar.pack(fill=tk.X, before=self.editor)
            self.find_var.set("")
            self.find_count.config(text="")
            for w in self.findbar.winfo_children():
                for c in w.winfo_children():
                    if isinstance(c, tk.Entry):
                        c.focus_set()
                        break
        elif not show and visible:
            self.editor.clear_find()
            self.replace_row.pack_forget()
            self.replace_chevron.config(text="⌄ replace")
            self.findbar.pack_forget()
            self.editor.text.focus_set()

    def _toggle_find_regex(self):
        """Flip the find bar into regex mode (.*) and re-run live."""
        self.find_regex = not self.find_regex
        self.regex_btn.config(
            fg=self.theme.accent if self.find_regex
            else self.theme["text_muted"])
        self._find_live()

    def _find_live(self, event=None):
        if event and event.keysym in ("Return", "Escape", "Up", "Down"):
            return
        needle = self.find_var.get()
        if not needle:
            self.editor.clear_find()
            self.find_count.config(text="")
            return
        count = self.editor.find(needle, regex=self.find_regex)
        if count < 0:
            self.find_count.config(text="bad regex", fg="#f87171")
            return
        self.find_count.config(
            text=f"{count} hit{'s' if count != 1 else ''}"
            if count else "no hits",
            fg=self.theme["text_muted"])

    def _find_next(self, delta):
        needle = self.find_var.get()
        if needle:
            self.editor.find(needle, backwards=delta < 0,
                             regex=self.find_regex)

    # ------------------------------------------------------------- packages
    def open_packages(self, autostart=None):
        self.show_sidebar_view("packages")
        if autostart:
            self.packages_view.install_packages(autostart)
        return self.packages_view

    # -------------------------------------------------------------- export
    def export_project_zip(self):
        src = self.project_dir
        if not src:
            src = filedialog.askdirectory(title="Choose a workspace to export")
            if not src:
                return
        if self.project_kind == "flask":
            export.ensure_requirements(src, "flask")
        dest = filedialog.asksaveasfilename(
            title="Export Project as ZIP", defaultextension=".zip",
            initialfile=export.default_zip_name(src))
        if not dest:
            return
        try:
            path, count = export.export_project_zip(src, dest)
        except Exception as e:
            errors.log_exception("export zip")
            messagebox.showerror("Export", f"Export failed:\n{e}")
            return
        self.terminal.log(f"Exported {count} files → {path}")
        self.toast(f"Exported {count} files", "success")

    def export_current_file(self):
        if not self.editor.file_path:
            self.save_file_as()
            if not self.editor.file_path:
                return
        self.save_file(silent=True)
        dest = filedialog.asksaveasfilename(
            title="Export Current File As",
            initialfile=os.path.basename(self.editor.file_path))
        if not dest:
            return
        try:
            export.export_file_bytes(self.editor.get_content(), dest)
        except Exception as e:
            errors.log_exception("export file")
            messagebox.showerror("Export", f"Export failed:\n{e}")
            return
        self.terminal.log(f"Exported current file → {dest}")

    # ------------------------------------------------------------- run/stop
    def run_current(self):
        """F5 — run the active file, or the workspace entry script."""
        target = None
        if self.editor.file_path and self.editor.file_path.endswith(".py"):
            target = self.editor.file_path
        elif self.project_dir:
            for cand in ("app.py", "main.py"):
                p = os.path.join(self.project_dir, cand)
                if os.path.isfile(p):
                    target = p
                    break
        if not target:
            self.terminal.log("Nothing to run — open a Python file first.")
            self.toast("Nothing to run", "error")
            return
        self.run_file(target)

    def run_file(self, path):
        path = os.path.abspath(path)
        if path == self.editor.file_path:
            self.save_file(silent=True)
        self._start_process([sys.executable, path], shell=False,
                            cwd=os.path.dirname(path))

    def run_command(self, cmd):
        self._start_process(cmd, shell=True,
                            cwd=self.project_dir or os.path.expanduser("~"))

    def _start_process(self, cmd, shell=False, cwd=None):
        self.stop_run(silent=True)
        self.terminal.log(f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
        self.terminal.log_raw("")
        try:
            self.proc = subprocess.Popen(
                cmd, shell=shell, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
        except Exception as e:
            self.terminal.log(f"failed to start: {e}")
            return
        self.status_ready.config(text="● Running", fg=self.theme.accent)

        def pump():
            try:
                for line in self.proc.stdout:
                    self._proc_q.put(line)
                code = self.proc.wait()
            except Exception as exc:  # noqa: BLE001
                self._proc_q.put(f"[process error: {exc}]\n")
                code = 1
            self._proc_q.put(("exit", code))
        threading.Thread(target=pump, daemon=True).start()
        self._poll_process()

    def _poll_process(self):
        done = False
        try:
            while True:
                item = self._proc_q.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "exit":
                    code = item[1]
                    self.terminal.log_raw("")
                    self.terminal.log(f"Process finished with exit code {code}")
                    self.status_ready.config(text="● Ready",
                                             fg=self.theme["success"])
                    done = True
                    continue
                self.terminal.log_raw(item.rstrip("\n"))
        except queue.Empty:
            pass
        if not done:
            self.root.after(120, self._poll_process)

    def stop_run(self, silent=False):
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            if not silent:
                self.terminal.log("Stopped.")
        elif not silent:
            self.terminal.log("Nothing is running.")

    # ------------------------------------------------------- agent callbacks
    def agent_execute_command(self, cmd):
        """Run an agent-proposed command inside the workspace jail.

        Called from the agent's worker thread; UI updates are marshalled
        back through ``root.after``. Returns (exit_code, combined_output).
        """
        cwd = self.project_dir or os.path.expanduser("~")
        self.root.after(0, lambda: self.terminal.log(f"$ {cmd}"))
        try:
            proc = subprocess.run(cmd, shell=True, cwd=cwd,
                                  capture_output=True, text=True, timeout=60)
            out = ((proc.stdout or "") + (proc.stderr or "")).strip()
            code = proc.returncode
        except subprocess.TimeoutExpired:
            out, code = "(timed out after 60s)", 124
        except Exception as exc:  # noqa: BLE001
            out, code = f"(failed to start: {exc})", 1
        tail = out[-4000:]
        self.root.after(0, lambda: self.terminal.log_raw(
            tail if tail else f"(exit {code}, no output)"))
        return code, out

    def chat_code_to_editor(self, code):
        """Drop an agent code block into a fresh untitled editor tab."""
        self.new_file()
        if code:
            self.editor.set_content(code if code.endswith("\n")
                                    else code + "\n")
            self._update_cursor_pos()

    def agent_on_written(self, path):
        """Agent touched a file — refresh explorer, reload if it's open."""
        def ui():
            try:
                if os.path.isdir(self.project_dir or ""):
                    self.sidebar.load_directory(self.project_dir)
                self.terminal.log(f"Agents wrote: {os.path.basename(path)}")
                if self.editor.file_path and \
                        os.path.abspath(self.editor.file_path) == \
                        os.path.abspath(path):
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as fh:
                        self.editor.set_content(fh.read())
            except Exception:
                errors.log_exception("agent_on_written", quiet=True)
        self.root.after(0, ui)

    # --------------------------------------------------- terminal commands
    def handle_terminal_command(self, text):
        low = text.strip().lower()
        if re.fullmatch(r"dxn1[\s_-]*studio", low):
            self.relaunch_with_splash()
            return
        if low in ("help", "?"):
            self.terminal.log("Studio commands:")
            for cmd, desc in (
                    ("dxn1 studio", "replay the boot splash"),
                    ("run", "run the current file / project (F5)"),
                    ("stop", "stop the running process"),
                    ("clear", "clear this terminal"),
                    ("packages", "open the optional-dependencies view"),
                    ("search <query>", "search across the workspace"),
                    ("find <text>", "find text in the current file"),
                    ("palette", "open the command palette (Ctrl+K)"),
                    ("todo", "scan the workspace for TODO / FIXME"),
                    ("git <args>", "run git in the workspace (status, add,"),
                    ("", "commit, log… output streams below"),
                    ("split", "toggle split editor view"),
                    ("zen", "toggle zen mode"),
                    ("goto <line>", "jump to a line"),
                    ("recent", "list recently opened files"),
                    ("update", "check GitHub for a newer release"),
                    ("hub", "open the Project Hub"),
                    ("export", "export the workspace as a ZIP"),
                    ("agent <request>", "talk to DXN1 Agents (if enabled)"),
                    ("settings", "open studio settings")):
                self.terminal.log(f"  {cmd:<18} — {desc}")
            return
        if low == "clear":
            self.terminal.clear()
            return
        if low == "run":
            self.run_current()
            return
        if low == "stop":
            self.stop_run()
            return
        if low in ("packages", "pkg"):
            self.open_packages()
            return
        if low == "todo":
            self.scan_todos()
            return
        if low == "split":
            self.toggle_split()
            return
        if low == "zen":
            self.toggle_zen()
            return
        if low == "recent":
            recents = [r for r in (self.config.get("recent_files") or [])
                       if os.path.isfile(r)][:8]
            if not recents:
                self.terminal.log("No recent files yet.")
            for i, r in enumerate(recents, 1):
                self.terminal.log(f"  {i}. {r}")
            return
        if low.startswith("goto "):
            num = text[5:].strip()
            if num.isdigit():
                self.editor.goto_line(int(num))
                self._update_cursor_pos()
            return
        if low == "update":
            self.check_for_updates(manual=True)
            return
        if low in ("hub", "project hub"):
            self.open_hub()
            return
        if low == "palette":
            self.open_palette()
            return
        if low.startswith("search "):
            self.show_sidebar_view("search")
            self.search_view.entry.delete(0, tk.END)
            self.search_view.entry.insert(0, text[7:].strip())
            self.search_view.start_search()
            return
        if low.startswith("find "):
            self.toggle_find(show=True)
            self.find_var.set(text[5:].strip())
            self._find_live()
            return
        if low.startswith("export"):
            self.export_project_zip()
            return
        if low.startswith("git ") or low == "git":
            self.run_command(text.strip())
            return
        if low.startswith("agent "):
            if self.agent_panel is not None:
                self.agent_panel.route(text[6:].strip())
            else:
                self.terminal.log("DXN1 Agents is disabled — enable it in "
                                  "Settings → DXN1 Agents.")
            return
        if low in ("settings",):
            self.open_settings()
            return
        self.terminal.log("Unknown command — try 'help'.")

    def relaunch_with_splash(self):
        """The 'dxn1 studio' moment: hide, show the logo card, come back."""
        if self._splash_active:
            return
        self._splash_active = True
        self.root.withdraw()
        Splash(self.root, accent=self.theme.accent, duration_ms=2000,
               on_done=lambda: (setattr(self, "_splash_active", False),
                                self.root.deiconify()))
        self.terminal.log("Booting DXN1 STUDIO…")

    # ------------------------------------------------------------- palette
    def open_palette(self):
        if self._palette is not None:
            try:
                self._palette.destroy()
            except tk.TclError:
                pass
            self._palette = None
        self._palette = CommandPalette(self)

    def palette_commands(self):
        cmds = [
            ("Run project (F5)", "F5", self.run_current),
            ("Stop process", "", self.stop_run),
            ("Save file", "Ctrl+S", lambda: self.save_file()),
            ("New file", "Ctrl+N", self.new_file),
            ("Open file…", "Ctrl+O", self.open_file_dialog),
            ("Find in file", "Ctrl+F", self.toggle_find),
            ("Quick open a file", "Ctrl+P", self.open_quick_open),
            ("Go to line…", "Ctrl+G", self.goto_line_dialog),
            ("Toggle comment", "Ctrl+/", self.editor.toggle_comment),
            ("Duplicate line", "Ctrl+Shift+D", self.editor.duplicate_line),
            ("Delete line", "Ctrl+Shift+K", self.editor.delete_line),
            ("Move line up", "Alt+Up", lambda: self.editor.move_line(-1)),
            ("Move line down", "Alt+Down", lambda: self.editor.move_line(1)),
            ("Split editor", "Ctrl+\\", self.toggle_split),
            ("Source control panel", "", lambda:
             self.show_sidebar_view("git")),
            ("Toggle bookmark on this line", "Ctrl+F2",
             lambda: self.editor.toggle_bookmark()),
            ("Next bookmark", "F2", self.editor.next_bookmark),
            ("Zen mode", "Ctrl+Alt+Z", self.toggle_zen),
            ("Scan for TODOs / FIXMEs", "", self.scan_todos),
            ("Go to symbol…  (type @)", "", self.open_palette),
            ("Check for updates…", "",
             lambda: self.check_for_updates(manual=True)),
            ("Keyboard shortcuts", "", self.show_shortcuts),
            ("Search in files", "", lambda: self.show_sidebar_view("search")),
            ("Explorer", "", lambda: self.show_sidebar_view("explorer")),
            ("Packages", "", lambda: self.show_sidebar_view("packages")),
            ("Toggle terminal", "", self.toggle_terminal),
            ("Toggle sidebar", "", self._toggle_sidebar),
            ("Export workspace as ZIP…", "", self.export_project_zip),
            ("Project Hub…", "", self.open_hub),
            ("Open workspace…", "", self.open_workspace_dialog),
            ("Settings…", "Ctrl+,", self.open_settings),
            (f"Switch to {'light' if self.theme.is_dark else 'dark'} theme", "",
             self.switch_theme),
            ("Word wrap on/off", "", self.toggle_word_wrap),
            ("Bigger editor text", "Ctrl++", lambda: self.change_font_size(1)),
            ("Smaller editor text", "Ctrl+-", lambda: self.change_font_size(-1)),
            ("Replay welcome & tour", "", self.start_wizard),
        ]
        if self.config.get("agents_enabled"):
            cmds += [
                ("Toggle DXN1 Agents panel", "", self.toggle_agents_panel),
                ("DXN1 Agents settings…", "",
                 lambda: AgentSettingsDialog(self)),
                ("Connect a brain…", "", lambda: ConnectDialog(self)),
            ]
        return cmds

    # --------------------------------------------------------------- toast
    def toast(self, message, kind="info"):
        """Small notification card above the status bar; auto-dismisses."""
        t = self.theme
        colors = {"success": t["success"], "error": "#f85149",
                  "info": t.accent}
        frame = tk.Frame(self.toast_layer, bg=t["card"], highlightthickness=1,
                         highlightbackground=t["card_border"])
        frame.pack(fill=tk.X, pady=3, padx=2)
        tk.Frame(frame, bg=colors.get(kind, t.accent), width=3).pack(
            side=tk.LEFT, fill=tk.Y)
        tk.Label(frame, text=message, bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 9), padx=10, pady=6).pack(side=tk.LEFT)
        self.root.after(3400, frame.destroy)

    # ------------------------------------------------------------ settings
    def open_settings(self):
        SettingsDialog(self)

    def toggle_terminal(self):
        if self.terminal_visible:
            self.right_panel.forget(self.terminal)
        else:
            self.right_panel.forget(self.editor.master)
            self.right_panel.add(self.editor.master, minsize=200)
            self.right_panel.add(self.terminal, height=200, minsize=80)
            self._sash_user = False
            self._pin_sash()
        self.terminal_visible = not self.terminal_visible

    def switch_theme(self):
        self.config.set("theme", "light" if self.theme.is_dark else "dark")
        self.restart_requested = True
        self.root.after(120, self.root.destroy)

    def change_font_size(self, delta):
        current = int(self.config.get("editor_font_size", 11))
        new = max(8, min(20, current + delta))
        if new == current:
            return
        self.config.set("editor_font_size", new)
        self.editor.set_font_size(new)
        self.toast(f"Editor text: {new}px", "info")

    def toggle_word_wrap(self):
        new = not bool(self.config.get("word_wrap", False))
        self.config.set("word_wrap", new)
        self.editor.set_wrap(new)
        self.toast(f"Word wrap {'on' if new else 'off'}", "info")

    def show_about(self):
        t = self.theme
        win = tk.Toplevel(self.root)
        win.title("About")
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        box = tk.Frame(win, bg=t["bg"])
        box.pack(padx=34, pady=26)
        from .onboarding import load_scaled
        import os as _os
        logo_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "assets", "logo.png")
        logo = load_scaled(logo_path, 84, 84)
        if logo:
            self._about_logo_ref = logo
            tk.Label(box, image=logo, bg=t["bg"]).pack()
        tk.Label(box, text=f"{APP_NAME}  v{APP_VERSION}-{APP_CHANNEL}",
                 bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 14, "bold")).pack(pady=(10, 0))
        tk.Label(box, text=APP_TAGLINE, bg=t["bg"],
                 fg=t["text_secondary"], font=(FONT_UI, 10)).pack()
        tk.Label(box, text="Pure Python + Tkinter. No Electron, no "
                           "frameworks, no bloat.",
                 bg=t["bg"], fg=t["text_muted"], font=(FONT_UI, 9)
                 ).pack(pady=(12, 0))
        link = tk.Label(box, text=REPO_URL, bg=t["bg"], fg=t.accent,
                        font=(FONT_UI, 9, "underline"), cursor="hand2")
        link.pack(pady=(4, 0))
        link.bind("<Button-1>",
                  lambda e: webbrowser.open(REPO_URL))
        tk.Label(box, text="MIT License · © 2026 DXN1", bg=t["bg"],
                 fg=t["text_muted"], font=(FONT_UI, 8)).pack(pady=(10, 0))
        upd = tk.Label(box, text="Check for updates…", bg=t["bg"],
                       fg=t.accent, font=(FONT_UI, 9, "bold"),
                       cursor="hand2")
        upd.pack(pady=(8, 0))
        upd.bind("<Button-1>",
                 lambda e: self.check_for_updates(manual=True))
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + \
            max(0, (self.root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = self.root.winfo_rooty() + 110
        win.geometry(f"+{x}+{y}")

    # ------------------------------------------------------ explorer menu
    def _explorer_menu(self, path, is_dir, x, y):
        t = self.theme
        menu = tk.Menu(self.root, tearoff=0, bg=t["sidebar"], fg=t["text"],
                       activebackground=t["hover"],
                       activeforeground=t["text"], font=(FONT_UI, 9))
        if is_dir:
            menu.add_command(label="New File…", command=lambda:
                             self._explorer_new(path, file=True))
            menu.add_command(label="New Folder…", command=lambda:
                             self._explorer_new(path, file=False))
            menu.add_separator()
            menu.add_command(label="Rename…", command=lambda:
                             self._explorer_rename(path))
            menu.add_command(label="Copy Path", command=lambda:
                             self._copy_path(path))
            menu.add_command(label="Reveal in File Manager", command=lambda:
                             self.reveal_in_file_manager(path))
            menu.add_separator()
            menu.add_command(label="Refresh", command=self.refresh_explorer)
            menu.add_command(label="Delete", command=lambda:
                             self._explorer_delete(path))
        else:
            menu.add_command(label="Open", command=lambda:
                             self.open_file(path))
            menu.add_command(label="Open in Split View", command=lambda:
                             (self.open_file(path),
                              self.toggle_split() if self._split is None
                              else None))
            if path.endswith(".py"):
                menu.add_command(label="Run This File", command=lambda:
                                 self.run_file(path))
            menu.add_separator()
            menu.add_command(label="Duplicate", command=lambda:
                             self._explorer_duplicate(path))
            menu.add_command(label="Rename…", command=lambda:
                             self._explorer_rename(path))
            menu.add_command(label="Copy Path", command=lambda:
                             self._copy_path(path))
            menu.add_command(label="Reveal in File Manager", command=lambda:
                             self.reveal_in_file_manager(path))
            menu.add_separator()
            menu.add_command(label="Delete", command=lambda:
                             self._explorer_delete(path))
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _explorer_new(self, parent, file=True):
        name = ""
        if file:
            name = self._ask("New File", "File name (e.g. utils.py):")
        else:
            name = self._ask("New Folder", "Folder name:")
        if not name:
            return
        target = os.path.join(parent, name)
        try:
            if file:
                os.makedirs(os.path.dirname(target) or parent, exist_ok=True)
                with open(target, "w", encoding="utf-8") as fh:
                    fh.write("")
            else:
                os.makedirs(target, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("New", f"Couldn't create {name}:\n{exc}")
            return
        self.refresh_explorer()
        if file:
            self.open_file(target)
        self.toast(f"Created {name}", "success")

    def _explorer_rename(self, path):
        new = self._ask("Rename", "New name:",
                        initial=os.path.basename(path))
        if not new or new == os.path.basename(path):
            return
        target = os.path.join(os.path.dirname(path), new)
        try:
            os.rename(path, target)
        except OSError as exc:
            messagebox.showerror("Rename", f"Couldn't rename:\n{exc}")
            return
        # migrate any open tab
        if path in self._tab_frames:
            self._buffers[target] = self._buffers.pop(path)
            entry = self._tab_frames.pop(path)
            self._tab_frames[target] = entry
            if self.editor.file_path == path:
                self.editor.file_path = target
                self.editor.set_content(self._buffers[target]["content"],
                                        path=target)
        self.refresh_explorer()
        self.toast(f"Renamed to {new}", "success")

    def _explorer_duplicate(self, path):
        base, ext = os.path.splitext(path)
        target = f"{base} copy{ext}"
        n = 2
        while os.path.exists(target):
            target = f"{base} copy {n}{ext}"
            n += 1
        try:
            import shutil
            shutil.copy2(path, target)
        except OSError as exc:
            messagebox.showerror("Duplicate", f"Couldn't copy:\n{exc}")
            return
        self.refresh_explorer()
        self.open_file(target)

    def _explorer_delete(self, path):
        kind = "folder" if os.path.isdir(path) else "file"
        if not messagebox.askyesno(
                "Delete",
                f"Delete the {kind} '{os.path.basename(path)}'?\n\n"
                f"{path}\n\nThis cannot be undone."):
            return
        try:
            import shutil
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as exc:
            messagebox.showerror("Delete", f"Couldn't delete:\n{exc}")
            return
        if path in self._tab_frames:
            self.close_tab(path)
        self.refresh_explorer()
        self.toast(f"Deleted {os.path.basename(path)}", "info")

    def _copy_path(self, path):
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.toast("Path copied", "info")

    def _ask(self, title, prompt, initial=""):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=self.theme["card"])
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        tk.Label(dlg, text=prompt, bg=self.theme["card"],
                 fg=self.theme["text"], font=(FONT_UI, 10)
                 ).pack(padx=18, pady=(16, 8))
        var = tk.StringVar(value=initial)
        entry = tk.Entry(dlg, textvariable=var, bg=self.theme["editor"],
                         fg=self.theme["text"], relief=tk.FLAT,
                         insertbackground=self.theme["text"],
                         font=(FONT_MONO, 10), width=34,
                         highlightthickness=1,
                         highlightbackground=self.theme["border"],
                         highlightcolor=self.theme.accent)
        entry.pack(padx=18, ipady=5)
        entry.selection_range(0, tk.END)
        entry.focus_set()
        result = {"value": ""}

        def ok(event=None):
            result["value"] = var.get().strip()
            dlg.destroy()

        entry.bind("<Return>", ok)
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        row = tk.Frame(dlg, bg=self.theme["card"])
        row.pack(fill=tk.X, pady=14)
        cancel = tk.Label(row, text="Cancel", bg=self.theme["card"],
                          fg=self.theme["text_secondary"], cursor="hand2",
                          font=(FONT_UI, 10), padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: dlg.destroy())
        confirm = tk.Label(row, text="OK", bg=self.theme.accent, fg="#ffffff",
                           cursor="hand2", font=(FONT_UI, 10, "bold"),
                           padx=16, pady=4)
        confirm.pack(side=tk.RIGHT, padx=(0, 14))
        confirm.bind("<Button-1>", ok)
        dlg.update_idletasks()
        x = self.root.winfo_rootx() + \
            max(0, (self.root.winfo_width() - dlg.winfo_reqwidth()) // 2)
        y = self.root.winfo_rooty() + 140
        dlg.geometry(f"+{x}+{y}")
        self.root.wait_window(dlg)
        return result["value"]

    # ---------------------------------------------------------- TODO scan
    def scan_todos(self):
        """Workspace-wide TODO / FIXME hunt → clickable results window."""
        if not self.project_dir:
            self.toast("Open a workspace first", "error")
            return
        base = self.project_dir
        self.terminal.log("Scanning for TODO / FIXME…")
        hits = []
        pattern = re.compile(r"(?i)\b(TODO|FIXME)\b[:\s]?(.{0,90})")
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in TREE_SKIP]
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext and ext not in TEXT_EXTS:
                    continue
                full = os.path.join(dirpath, name)
                try:
                    with open(full, "r", encoding="utf-8",
                              errors="replace") as fh:
                        for lineno, line in enumerate(fh, 1):
                            m = pattern.search(line)
                            if m:
                                hits.append((full, lineno, line.strip()[:120]))
                            if len(hits) >= 200:
                                break
                except OSError:
                    continue
                if len(hits) >= 200:
                    break
            if len(hits) >= 200:
                break
        self._show_todo_results(hits)
        self.terminal.log(f"Found {len(hits)} TODO/FIXME markers.")

    def _show_todo_results(self, hits):
        t = self.theme
        win = tk.Toplevel(self.root)
        win.title("TODO / FIXME")
        win.configure(bg=t["bg"])
        win.geometry("720x420")
        tk.Label(win, text=f"{len(hits)} markers in this workspace",
                 bg=t["bg"], fg=t["text"], font=(FONT_UI, 12, "bold")
                 ).pack(anchor="w", padx=16, pady=(14, 6))
        if not hits:
            tk.Label(win, text="Nothing to do — you're actually done. 🎉",
                     bg=t["bg"], fg=t["text_secondary"], font=(FONT_UI, 10)
                     ).pack(pady=30)
        box = tk.Frame(win, bg=t["bg"])
        box.pack(fill=tk.BOTH, expand=True, padx=10)
        canvas = tk.Canvas(box, bg=t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=canvas.yview)
        rows = tk.Frame(canvas, bg=t["bg"])
        rows.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=rows, anchor="nw", width=690)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(cw, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        for path, lineno, text in hits[:200]:
            row = tk.Frame(rows, bg=t["card"], highlightthickness=1,
                           highlightbackground=t["card_border"])
            row.pack(fill=tk.X, pady=2, padx=2)
            head = tk.Label(row, anchor="w", justify=tk.LEFT, wraplength=640,
                            text=f"{os.path.basename(path)}  ·  line {lineno}",
                            bg=t["card"], fg=t.accent,
                            font=(FONT_UI, 9, "bold"), cursor="hand2")
            head.pack(anchor="w", padx=10, pady=(6, 0))
            body = tk.Label(row, anchor="w", justify=tk.LEFT, wraplength=640,
                            text=text, bg=t["card"], fg=t["text_secondary"],
                            font=(FONT_MONO, 8))
            body.pack(anchor="w", padx=10, pady=(0, 6))
            for w in (head, body):
                w.bind("<Button-1>", lambda e, p=path, l=lineno:
                       self.open_search_match(p, l, 0))

    def goto_line_dialog(self):
        if not self.editor.file_path and not self.editor.get_content():
            return
        value = self._ask("Go to Line", "Line number:")
        if value and value.isdigit():
            if self.editor.goto_line(int(value)):
                self._update_cursor_pos()
            else:
                self.toast("No such line", "error")

    # ------------------------------------------------------------- updater
    def check_for_updates(self, manual=False):
        """GitHub releases check — stdlib only, never blocks the UI."""
        if self._updater_shown or self.smoke_test:
            if manual and self.smoke_test:
                self.toast("Update checks are off in smoke-test mode", "info")
            return

        def worker():
            result = {"state": "error", "latest": "", "url": "",
                      "notes": []}
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/DXN1-termux/DXN1-STUDIO/"
                    "releases/latest",
                    headers={"User-Agent": f"DXN1-Studio/{APP_VERSION}",
                             "Accept": "application/vnd.github+json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8", "replace"))
                tag = (data.get("tag_name") or "").lstrip("v")
                lines = [ln.lstrip("-* ").strip() for ln in
                         (data.get("body") or "").splitlines()
                         if ln.strip().startswith(("-", "*"))][:3]
                result = {"state": "ok", "latest": tag, "notes": lines,
                          "url": data.get("html_url") or REPO_URL}
            except Exception:
                pass

            def finish():
                self._updater_shown = False
                if result["state"] != "ok":
                    if manual:
                        self.toast("Couldn't reach GitHub — try later",
                                   "error")
                    return
                try:
                    newer = updater.is_newer(result["latest"], APP_VERSION)
                except ValueError:
                    newer = False
                if newer:
                    # the full-screen Update Portal — no sneaky toasts
                    updater.UpdatePortal(self, result["latest"],
                                         result["url"], result["notes"])
                    self.terminal.log(f"Update available: v{APP_VERSION} → "
                                      f"v{result['latest']} — {result['url']}")
                elif manual:
                    self.toast(f"You're on the latest "
                               f"(v{APP_VERSION})", "success")

            self.root.after(0, finish)

        self._updater_shown = True
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _ver_tuple(version):
        parts = re.findall(r"\d+", version or "")
        if not parts:
            raise ValueError(version)
        return tuple(int(p) for p in parts[:3]) + (0,) * (3 - len(parts[:3]))

    # ----------------------------------------------------------- shortcuts
    def show_shortcuts(self):
        t = self.theme
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        rows = (
            ("Ctrl+N / Ctrl+O / Ctrl+S", "new / open / save"),
            ("Ctrl+P", "quick open a file"),
            ("Ctrl+K", "command palette — type @ for symbols"),
            ("Ctrl+F", "find in file"),
            ("Ctrl+G", "go to line"),
            ("Ctrl+/", "toggle comment"),
            ("Ctrl+Shift+D", "duplicate line"),
            ("Ctrl+Shift+K", "delete line"),
            ("Alt+Up / Alt+Down", "move line up / down"),
            ("Tab", "expand snippet (ifmain · pdb · smain)"),
            ("Ctrl+F2 / F2 / Shift+F2", "bookmark line · next · previous"),
            ("Ctrl+\\", "split editor"),
            ("Ctrl+Alt+Z", "zen mode"),
            ("Ctrl+W · Ctrl+Tab", "close tab · cycle tabs"),
            ("F5", "run project"),
            ("Ctrl+,", "settings"),
        )
        box = tk.Frame(win, bg=t["bg"])
        box.pack(padx=24, pady=18)
        tk.Label(box, text="Keyboard shortcuts", bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 13, "bold")).pack(anchor="w", pady=(0, 10))
        for keys, action in rows:
            row = tk.Frame(box, bg=t["bg"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=keys, bg=t["bg"], fg=t.accent, width=22,
                     anchor="w", font=(FONT_MONO, 9, "bold")).pack(
                side=tk.LEFT)
            tk.Label(row, text=action, bg=t["bg"], fg=t["text_secondary"],
                     font=(FONT_UI, 9)).pack(side=tk.LEFT, padx=12)
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + \
            max(0, (self.root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = self.root.winfo_rooty() + 120
        win.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------ run
    def _on_close(self):
        """WM_DELETE_WINDOW — save session, then quit cleanly."""
        try:
            self.stop_run(silent=True)
            if self.config.get("restore_session", True) and \
                    self.project_dir:
                sessions = dict(self.config.get("session_tabs") or {})
                sessions[os.path.abspath(self.project_dir)] = {
                    "tabs": list(self._tab_frames),
                    "active": self.editor.file_path or "",
                }
                # keep sessions for workspaces that still exist, max 20
                kept = {p: v for p, v in sessions.items()
                        if os.path.isdir(p)}
                self.config.set(
                    "session_tabs",
                    dict(list(kept.items())[-20:]))
        except Exception:
            errors.log_exception("save session", quiet=True)
        self.root.destroy()

    def _schedule_smoke_test(self):
        """Headless self-check exercising the whole v1.1 surface."""
        self.root.after(60000, self.root.destroy)  # watchdog: never hang CI
        tmp = tempfile.mkdtemp(prefix="dxn1-smoke-")

        def bail(err):
            import traceback
            traceback.print_exc()
            print(f"SMOKE-FAIL: {err}", flush=True)
            self.root.destroy()

        def step1():
            try:
                if self.config.needs_onboarding:
                    self.start_wizard()
                self.root.after(1200, step2)
            except Exception:
                bail("step1-wizard")

        def step2():
            try:
                if self._wizard is not None and self._wizard.win.winfo_exists():
                    self._wizard.choose_agents(True)   # opt-in path
                    if hasattr(self._wizard, "choose_brain"):
                        self._wizard.choose_brain("free")
                    self._wizard.finish()
                self.root.after(1400, step3)
            except Exception:
                bail("step2-wizard-finish")

        def step3():
            try:
                if self._hub is not None and self._hub.winfo_exists():
                    self._hub._finish_explore()        # 'Just explore'
                self.root.after(1200, step4)
            except Exception:
                bail("step3-hub")

        def step4():
            try:
                self._tour_done_cleanup()
                self.start_tour()
                self.root.after(1300, step5)
            except Exception:
                bail("step4-tour")

        def step5():
            try:
                if self._tour is not None:
                    self._tour.finish()
                # scaffold a python workspace + open it
                path, kind = projects.scaffold("python", tmp, "Smoke Script")
                self._set_workspace(path, kind)
                self.root.after(900, step6)
            except Exception:
                bail("step5-scaffold")

        def step6():
            try:
                # full-access agent writes a file with zero prompts
                self.config.set("agents_enabled", True)
                self.config.set("agents_ask_edits", False)
                self.apply_agents_visibility()
                self.agent_panel.handle("create file agent_demo.py")
                made = os.path.join(self.project_dir, "agent_demo.py")
                assert os.path.isfile(made), "agent did not write file"
                self.root.after(600, step6b)
            except Exception:
                bail("step6-agent")

        def step6b():
            try:
                # engine + sandbox + parser, fully offline
                from .sandbox import parse_tools
                sb = WorkspaceSandbox(self.project_dir)
                eng = AgentEngine(
                    FakeBackend([
                        '<tool name="write_file">'
                        '{"path": "engine_demo.py", '
                        '"content": "print(42)\\n"}'
                        '</tool>Wrote the file. <done>done</done>'
                    ]),
                    sb, self.config, name="Smoke",
                    emit=lambda *a, **k: None, approve=lambda *a, **k: True,
                    execute_command=lambda c: (0, "ok"),
                    on_written=lambda p: None)
                eng.run("write engine_demo.py")
                assert os.path.isfile(
                    os.path.join(self.project_dir, "engine_demo.py")), \
                    "engine did not write file"
                try:
                    sb.resolve("../escape.py")
                    raise AssertionError("sandbox escape allowed")
                except SandboxError:
                    pass
                clean, tools = parse_tools(
                    'hi <tool name="read_file">{"path": "a.py"}</tool>')
                assert tools and tools[0][0] == "read_file" and clean == "hi"
                self.terminal.log("Engine + sandbox checks passed")
                self.root.after(500, step7)
            except Exception:
                bail("step6b-engine")

        def step7():
            try:
                self.run_file(os.path.join(self.project_dir, "main.py"))
                self.root.after(2500, step8)
            except Exception:
                bail("step7-run")

        def step8():
            try:
                self.stop_run(silent=True)
                out = os.path.join(tmp, "export.zip")
                path, count = export.export_project_zip(self.project_dir, out)
                assert os.path.isfile(path) and count >= 2, "export failed"
                self.open_packages()
                self.root.after(900, step9)
            except Exception:
                bail("step8-export-packages")

        def step9():
            try:
                # search view end-to-end (synchronous scan via thread + wait)
                self.show_sidebar_view("search")
                self.search_view.entry.insert(0, "Hello")
                self.search_view.start_search()
                self.root.after(900, step9b)
            except Exception:
                bail("step9-search")

        def step9b():
            try:
                assert self.search_view._hits, "search found nothing"
                # palette open + close
                self.open_palette()
                self.root.after(400, step9c)
            except Exception:
                bail("step9b-palette")

        def step9c():
            try:
                assert self._palette is not None
                self._palette.close()
                self._palette = None
                # find bar + toast
                self.toggle_find(show=True)
                self.find_var.set("Hello")
                self._find_live()
                self.toast("smoke toast", "info")
                self.root.after(500, step9d)
            except Exception:
                bail("step9c-find-toast")

        def step9d():
            try:
                self.toggle_find(show=False)
                # quick open
                self.open_quick_open()
                self.root.after(300, self._quick_open.close)
                self.root.after(500, step9e)
            except Exception:
                bail("step9d-quickopen")

        def step9e():
            try:
                # split view + edit on both sides
                self.toggle_split()
                assert self._split is not None, "split view missing"
                self.toggle_split()
                assert self._split is None, "split view won't close"
                # zen round-trip
                self.toggle_zen()
                self.toggle_zen()
                # comment toggle on main.py
                self.open_file(os.path.join(self.project_dir, "main.py"))
                self.editor.text.mark_set("insert", "1.0")
                self.editor.toggle_comment()
                assert self.editor.get_content().lstrip().startswith("#"), \
                    "comment toggle failed"
                self.editor.toggle_comment()
                # auto-indent sanity via editor internals
                self.editor.auto_indent = True
                self.editor.auto_close = True
                # goto line
                assert self.editor.goto_line(1), "goto failed"
                self.root.after(400, step9f)
            except Exception:
                bail("step9e-split-zen-comment")

        def step9f():
            try:
                # --- git panel: init, stage, commit on a scratch repo
                self.show_sidebar_view("git")
                self.git_view.set_workspace(self.project_dir)
                self.root.after(400, step9g)
            except Exception:
                bail("step9f-git-view")

        def step9g():
            try:
                g = self.git_view
                if not g._is_repo:
                    g._init_repo()
                assert g._is_repo, "git panel did not detect/init repo"
                from .gitpanel import _run_git
                _run_git(self.project_dir, "config", "user.name", "Smoke")
                _run_git(self.project_dir, "config", "user.email",
                         "smoke@test.local")
                g.msg.delete(0, tk.END)
                g.msg.insert(0, "smoke: first commit")
                g.commit()
                self.root.after(500, step9h)
            except Exception:
                bail("step9g-git-commit")

        def step9h():
            try:
                from .gitpanel import _run_git
                ok, out, _ = _run_git(self.project_dir, "log",
                                      "--oneline", "-1")
                assert ok and "smoke: first commit" in out, \
                    "commit didn't land"
                self.terminal.log("Git panel checks passed")
                self.root.after(300, step9i)
            except Exception:
                bail("step9h-git-log")

        def step9i():
            try:
                # --- palette @symbols
                self.open_palette()
                self._palette.entry.insert(0, "@")
                self._palette._on_type()
                assert self._palette.filtered, "no symbols found"
                self._palette.close()
                self._palette = None
                # --- bookmarks
                self.editor.toggle_bookmark(2)
                assert 2 in self.editor.bookmarks, "bookmark add failed"
                self.editor.goto_line(1)
                self.editor.next_bookmark()
                assert str(self.editor.text.index(
                    "insert").split(".")[0]) == "2", "bookmark jump failed"
                self.editor.prev_bookmark()
                self.editor.toggle_bookmark(2)
                assert 2 not in self.editor.bookmarks, "bookmark del failed"
                # --- snippet expansion
                self.editor.set_content("ifmain",
                                        path=self.editor.file_path)
                self.editor.text.mark_set("insert", "end-1c")
                self.editor._on_tab()
                assert '__name__' in self.editor.get_content(), \
                    "snippet didn't expand"
                # --- settings search filter
                dlg = SettingsDialog(self)
                dlg._filter_settings("wrap")
                dlg.destroy()
                self.terminal.log("Symbols + bookmarks + snippets passed")
                self.root.after(400, step9j)
            except Exception:
                bail("step9i-symbols-bookmarks-snippets")

        def step9j():
            try:
                # --- v1.1.4: replace bar (open_replace + replace_all UI)
                self.open_replace()
                self.root.update()
                assert self.replace_row.winfo_ismapped(), \
                    "replace row missing"
                self.find_var.set("__name__")
                self.replace_var.set("__core__")
                self._find_live()
                self._replace_all()
                assert "__core__" in self.editor.get_content(), \
                    "replace_all UI failed"
                self.toggle_replace(show=False)
                self.toggle_find(show=False)
                # --- v1.1.4: C-family symbols via the palette
                go_path = os.path.join(self.project_dir, "notes.go")
                with open(go_path, "w", encoding="utf-8") as fh:
                    fh.write("package main\n\nfunc main() {\n}\n\n"
                             "func Add(a int, b int) int {\n\treturn a\n}\n")
                self.open_file(go_path)
                syms = self.editor.symbols()
                names = [n for _, _, n in syms]
                assert "main" in names and "Add" in names, syms
                # --- v1.1.4: game template scaffolds + compiles
                import py_compile
                gpath, gkind = projects.scaffold(
                    "game", tmp, "Smoke Game")
                assert gkind == "game"
                py_compile.compile(os.path.join(gpath, "main.py"),
                                       doraise=True)
                # --- v1.1.4: free-brain guard stays honest
                from .llm import _looks_like_provider_error
                assert _looks_like_provider_error(
                    "The API key used for this request has reached its "
                    "budget. Please [raise ...]"), "guard missed budget"
                assert not _looks_like_provider_error(
                    "def fix(): return rate_limit_explained"), \
                    "guard false positive"
                from .llm import PollinationsBackend
                pb = PollinationsBackend(self.config)
                self.terminal.log("v1.1.4 checks passed")
                self.root.after(400, step9k)
            except Exception:
                bail("step9j-v114")

        def step9k():
            # --- v1.1.5: agents 2.0 — markdown chat, personas, sessions
            try:
                from .agent import (parse_chat_blocks, SessionStore,
                                    PERSONAS, SLASH_COMMANDS)
                blocks = parse_chat_blocks(
                    "# Plan\n- one\n- two\n\nPlain para.\n"
                    "```python\nprint('hi')\n```\ntail line")
                kinds = [k for k, _ in blocks]
                assert kinds[0] == "h" and kinds[1] == "li", kinds
                assert ("code", ) == (kinds[4],), kinds
                assert blocks[4][1][0] == "python", blocks[4]
                ap = self.agent_panel
                assert ap is not None, "agents panel missing"
                ap.set_persona("senior")
                assert ap._persona()[0] == "senior", "persona switch failed"
                ap.set_persona("default")
                assert len(PERSONAS) >= 6 and len(SLASH_COMMANDS) >= 12
                store = SessionStore()
                store.save(self.project_dir, "smoke-1", "Smoke chat",
                           [{"role": "user", "text": "hi"},
                            {"role": "agent", "text": "hello"}], stats="3 tok")
                got = store.load(self.project_dir, "smoke-1")
                assert got and got["messages"][-1]["text"] == "hello"
                # slash dispatch must not crash offline (local quickies only)
                ap.route("/help")
                self.root.update()
                # search_code tool through the engine's tool host
                sb = WorkspaceSandbox(self.project_dir)
                eng = AgentEngine(
                    FakeBackend(["ok <done>done</done>"]),
                    sb, self.config, name="Smoke",
                    emit=lambda *a, **k: None, approve=lambda *a, **k: True,
                    execute_command=lambda c: (0, "ok"),
                    on_written=lambda p: None)
                res = eng._exec_tool("search_code",
                                     {"pattern": "SMOKE", "max": 5})
                assert isinstance(res, str) and "error" not in res[:20], res
                self.terminal.log("v1.1.5 agents checks passed")
                self.root.after(400, step9l)
            except Exception:
                bail("step9k-agents2")

        def step9l():
            # --- v1.1.5: update portal — logic + every phase paints
            try:
                from .updater import (ver_tuple, is_newer, UpdatePortal,
                                      MIN_SHOW_SECONDS)
                assert ver_tuple("1.1.5") == (1, 1, 5)
                assert is_newer("1.1.5", "1.1.4") and not is_newer(
                    "1.1.4", "1.1.4")
                assert MIN_SHOW_SECONDS >= 3
                portal = UpdatePortal(self, "9.9.9",
                                      notes=["smoke note one",
                                             "smoke note two"])
                self.root.update()
                assert portal._phase == "offer"
                portal._paint()                      # offer phase renders
                portal.decline()                     # security goodbye screen
                self.root.update()
                assert portal._phase == "declined"
                portal._draw_progress(self.root.winfo_width(),
                                      self.root.winfo_height())
                portal._draw_restarting(self.root.winfo_width(),
                                        self.root.winfo_height())
                portal._target = 0.42
                portal._animate()
                self.root.update()
                portal.after_cancel(portal._restart_job) \
                    if portal._restart_job else None
                portal.grab_release()
                portal.destroy()
                self._updater_shown = False
                self.terminal.log("v1.1.5 update portal checks passed")
                self.root.after(400, step9m)
            except Exception:
                bail("step9l-updater")

        def step9m():
            # --- v1.1.5: editor pro — indent, regex find/replace, word hl
            try:
                from .widgets import language_for, LANG_RULES
                ed = self.editor
                # block indent / outdent over a selection
                ed.set_content("alpha bravo\ngamma delta\n", "pro.py")
                ed.text.tag_add("sel", "1.0", "end")
                ed._on_tab()
                assert ed.text.get("1.0", "1.end").startswith("    alpha"), \
                    ed.text.get("1.0", "1.end")
                ed._on_outdent()
                assert not ed.text.get("1.0", "1.end").startswith(" "), \
                    "outdent failed"
                # regex find: both two-word pairs light up
                n = ed.find(r"(\w+) (\w+)", regex=True)
                assert n == 2, n
                # regex replace_all with template expansion
                n = ed.replace_all(r"(\w+) (\w+)", r"\2-\1", regex=True)
                assert n == 2, n
                body = ed.get_content()
                assert "bravo-alpha" in body and "delta-gamma" in body, body
                # bad regex is surfaced, never crashes
                assert ed.find("([unclosed", regex=True) == -1
                assert ed.replace_all("([bad", "x", regex=True) == -1
                # word-under-cursor highlight: two "needle" occurrences
                ed.set_content("needle here\nneedle there\n", "pro2.py")
                ed.text.mark_set("insert", "1.2")
                ed._word_hl()
                tags = ed.text.tag_ranges("word_hl")
                assert tags and len(tags) == 4, tags
                # new language rules are live
                assert language_for("main.go") is LANG_RULES[".go"]
                assert language_for("lib.rs") is LANG_RULES[".rs"]
                assert language_for("App.java") is LANG_RULES[".java"]
                assert language_for("run.sh") is LANG_RULES[".sh"]
                self.terminal.log("v1.1.5 editor pro checks passed")
                self.root.after(400, step10)
            except Exception:
                bail("step9m-editorpro")

        def step10():
            try:
                self.handle_terminal_command("help")
                self.scan_todos()
                self.handle_terminal_command("dxn1 studio")  # splash replay
                self.root.after(2600, step11)
            except Exception:
                bail("step10-commands")

        def step11():
            try:
                assert self.root.winfo_ismapped() or \
                    self.root.state() == "normal", "splash did not restore"
                self.terminal.log("Smoke test passed ✔")
                print("SMOKE-PASS", flush=True)
                self.root.after(400, self.root.destroy)
            except Exception:
                bail("step11-final")

        self.root.after(300, step1)


class SettingsDialog(tk.Toplevel):
    """Studio preferences: look & feel, editor, boot behaviour, agents."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        t = app.theme
        self.t = t
        cfg = app.config
        self.title("DXN1 STUDIO — Settings")
        self.configure(bg=t["bg"])
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        self.theme_v = tk.StringVar(value=cfg.get("theme", "dark"))
        self.accent_v = tk.StringVar(value=cfg.get("accent", "violet"))
        self.size_v = tk.StringVar(value=str(cfg.get("editor_font_size", 11)))
        self.wrap_v = tk.BooleanVar(value=bool(cfg.get("word_wrap", False)))
        self.autosave_v = tk.BooleanVar(value=bool(cfg.get("auto_save", False)))
        self.autoindent_v = tk.BooleanVar(
            value=bool(cfg.get("editor_auto_indent", True)))
        self.autoclose_v = tk.BooleanVar(
            value=bool(cfg.get("editor_auto_close", True)))
        self.splash_v = tk.BooleanVar(value=bool(cfg.get("splash_enabled", True)))
        self.hub_v = tk.BooleanVar(value=bool(cfg.get("hub_on_startup", True)))
        self.session_v = tk.BooleanVar(
            value=bool(cfg.get("restore_session", True)))
        self.updates_v = tk.BooleanVar(
            value=bool(cfg.get("check_updates", True)))

        box = tk.Frame(self, bg=t["bg"])
        box.pack(padx=26, pady=20)

        tk.Label(box, text="Settings", bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 14, "bold")).pack(anchor="w")

        # searchable — type to filter rows across every section
        srow = tk.Frame(box, bg=t["bg"])
        srow.pack(fill=tk.X, pady=(8, 0))
        self.search_var = tk.StringVar()
        s_ent = tk.Entry(srow, textvariable=self.search_var, bg=t["editor"],
                         fg=t["text"], insertbackground=t["text"],
                         relief=tk.FLAT, font=(FONT_UI, 10),
                         highlightthickness=1, highlightbackground=t["border"],
                         highlightcolor=t.accent)
        s_ent.pack(fill=tk.X, ipady=5)
        s_ent.insert(0, "Search settings…")
        s_ent.config(fg=t["text_muted"])
        s_ent.bind("<FocusIn>", lambda e: (
            s_ent.delete(0, tk.END), s_ent.config(fg=t["text"])))
        s_ent.bind("<FocusOut>", lambda e: (
            self._filter_settings(self.search_var.get()), None))
        s_ent.bind("<KeyRelease>", lambda e: self._filter_settings(
            self.search_var.get()))
        self._settings_search = s_ent

        self._sections = []

        # --- look & feel
        sec1 = self._section(box, "Look & feel")
        row = tk.Frame(sec1, bg=t["card"])
        row.pack(fill=tk.X, pady=(0, 6))
        for mode, label in (("dark", "Dark"), ("light", "Light")):
            tk.Radiobutton(row, text=label, variable=self.theme_v, value=mode,
                           bg=t["card"], fg=t["text"],
                           activebackground=t["card"], activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0, bd=0
                           ).pack(side=tk.LEFT, padx=12)
        row2 = tk.Frame(sec1, bg=t["card"])
        row2.pack(fill=tk.X)
        for name, spec in sorted(ACCENTS.items()):
            tk.Radiobutton(row2, text=spec["label"], variable=self.accent_v,
                           value=name,
                           bg=t["card"], fg=t["text"],
                           activebackground=t["card"], activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0, bd=0
                           ).pack(side=tk.LEFT, padx=8)

        # --- editor
        secE = self._section(box, "Editor")
        srow = tk.Frame(secE, bg=t["card"])
        srow.pack(fill=tk.X, pady=(0, 6))
        tk.Label(srow, text="Text size:", bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 9)).pack(side=tk.LEFT)
        for label, px in (("Small · 10", 10), ("Medium · 11", 11),
                          ("Large · 13", 13)):
            tk.Radiobutton(srow, text=label, variable=self.size_v,
                           value=str(px), bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0,
                           bd=0).pack(side=tk.LEFT, padx=8)
        for var, label, sub in (
                (self.wrap_v, "Word wrap",
                 "Soft-wrap long lines instead of horizontal scroll."),
                (self.autosave_v, "Auto-save",
                 "Save the active file shortly after you stop typing."),
                (self.autoindent_v, "Auto-indent",
                 "Keep indentation on Enter; deeper after ':' and '{'."),
                (self.autoclose_v, "Auto-close brackets",
                 "Typing ( [ { closes the pair; type-over included.")):
            crow = tk.Frame(secE, bg=t["card"])
            crow.pack(fill=tk.X, pady=2, ipady=2)
            tk.Checkbutton(crow, variable=var, bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"], selectcolor=t["editor"],
                           highlightthickness=0, bd=0).pack(side=tk.LEFT,
                                                            padx=(12, 4))
            tk.Label(crow, text=label, bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(crow, text=f"  ·  {sub}", bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT)

        # --- boot behaviour
        sec2 = self._section(box, "Boot behaviour")
        for var, label, sub in (
                (self.splash_v, "Show the boot splash",
                 "The branded card with the shimmer bar on launch."),
                (self.hub_v, "Start at the Project Hub",
                 "Create or reopen a workspace every launch."),
                (self.session_v, "Restore last session",
                 "Reopen your tabs when you dive back into a workspace."),
                (self.updates_v, "Check for updates",
                 "Quietly ask GitHub on boot; toast when a new release is up.")):
            row = tk.Frame(sec2, bg=t["card"])
            row.pack(fill=tk.X, pady=3, ipady=4)
            tk.Checkbutton(row, variable=var, bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"], selectcolor=t["editor"],
                           highlightthickness=0, bd=0).pack(side=tk.LEFT,
                                                            padx=(12, 4))
            tk.Label(row, text=label, bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(row, text=f"  ·  {sub}", bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT)

        # --- agents
        sec3 = self._section(box, "DXN1 Agents")
        btn = tk.Label(sec3, text="Open agent settings…", bg=t["card"],
                       fg=t.accent, font=(FONT_UI, 10, "bold"),
                       cursor="hand2", padx=10, pady=8)
        btn.pack(fill=tk.X)
        btn.bind("<Button-1>", lambda e: AgentSettingsDialog(app))
        btn2 = tk.Label(sec3, text="Connect a brain (Kilo · OpenRouter · "
                                   "GitHub)…", bg=t["card"], fg=t.accent,
                        font=(FONT_UI, 10, "bold"), cursor="hand2",
                        padx=10, pady=8)
        btn2.pack(fill=tk.X)
        btn2.bind("<Button-1>", lambda e: ConnectDialog(app))
        tk.Label(sec3, text="Permission gates (ask vs full access) live in "
                            "agent settings. The workspace sandbox is always on.",
                 bg=t["card"], fg=t["text_secondary"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=10, pady=(0, 6))

        # --- buttons
        self._finalize_sections()
        row = tk.Frame(box, bg=t["bg"])
        row.pack(fill=tk.X, pady=(16, 0))
        cancel = tk.Label(row, text="Cancel", bg=t["bg"],
                          fg=t["text_secondary"],
                          font=(FONT_UI, 10), cursor="hand2", padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: self.destroy())
        save = tk.Label(row, text="Save", bg=t.accent, fg="#ffffff",
                        font=(FONT_UI, 10, "bold"), cursor="hand2",
                        padx=18, pady=6)
        save.pack(side=tk.RIGHT)
        save.bind("<Button-1>", lambda e: self._save())

        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=self.t["bg"],
                 fg=self.t["text_secondary"],
                 font=(FONT_UI, 9, "bold")).pack(anchor="w", pady=(14, 4))
        frame = tk.Frame(parent, bg=self.t["card"], highlightthickness=1,
                         highlightbackground=self.t["card_border"])
        frame.pack(fill=tk.X, ipady=8, ipadx=4)
        inner = tk.Frame(frame, bg=self.t["card"])
        inner.pack(fill=tk.X, padx=10)
        self._sections.append({"title": title, "parent": parent,
                               "inner": inner, "rows": []})
        return inner

    def _texts_of(self, widget):
        """Widget text + its children's text, for settings filtering."""
        out = []
        try:
            out.append(str(widget.cget("text")))
        except (tk.TclError, KeyError):
            pass
        try:
            for child in widget.winfo_children():
                out.append(self._texts_of(child))
        except tk.TclError:
            pass
        return " ".join(out)

    def _finalize_sections(self):
        """Snapshot each row's pack options so filtering can restore them."""
        for sec in self._sections:
            sec["rows"] = [(w, w.pack_info())
                           for w in sec["inner"].winfo_children()]
            sec["card"] = sec["inner"].master

    def _filter_settings(self, query):
        """Type-to-filter: keep rows whose text matches, drop empty cards."""
        q = (query or "").strip().lower()
        if not q and self._settings_search.get() == "Search settings…":
            q = ""
        for sec in self._sections:
            visible = 0
            for w, info in sec["rows"]:
                hit = (not q) or q in self._texts_of(w).lower() \
                    or q in sec["title"].lower()
                try:
                    if hit:
                        w.pack(**info)
                        visible += 1
                    else:
                        w.pack_forget()
                except tk.TclError:
                    pass
            header = None
            for w in sec["parent"].winfo_children():
                if isinstance(w, tk.Label) and \
                        w.cget("text") == sec["title"]:
                    header = w
                    break
            try:
                if visible:
                    if header is not None:
                        header.pack(anchor="w", pady=(14, 4))
                    sec["card"].pack(fill=tk.X, ipady=8, ipadx=4)
                else:
                    if header is not None:
                        header.pack_forget()
                    sec["card"].pack_forget()
            except tk.TclError:
                pass

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.master.winfo_rootx() + \
            max(0, (self.master.winfo_width() - w) // 2)
        y = self.master.winfo_rooty() + \
            max(0, (self.master.winfo_height() - h) // 3)
        self.geometry(f"+{x}+{y}")

    def _save(self):
        cfg = self.app.config
        cfg.set("theme", self.theme_v.get())
        cfg.set("accent", self.accent_v.get())
        try:
            cfg.set("editor_font_size", max(8, min(20,
                                                   int(self.size_v.get()))))
        except ValueError:
            pass
        cfg.set("word_wrap", bool(self.wrap_v.get()))
        cfg.set("auto_save", bool(self.autosave_v.get()))
        cfg.set("editor_auto_indent", bool(self.autoindent_v.get()))
        cfg.set("editor_auto_close", bool(self.autoclose_v.get()))
        cfg.set("splash_enabled", bool(self.splash_v.get()))
        cfg.set("hub_on_startup", bool(self.hub_v.get()))
        cfg.set("restore_session", bool(self.session_v.get()))
        cfg.set("check_updates", bool(self.updates_v.get()))
        # editor changes apply live; colours need the rebuild
        self.app.editor.set_font_size(cfg.get("editor_font_size", 11))
        self.app.editor.set_wrap(bool(cfg.get("word_wrap", False)))
        self.app.editor.auto_indent = \
            bool(cfg.get("editor_auto_indent", True))
        self.app.editor.auto_close = \
            bool(cfg.get("editor_auto_close", True))
        if self.app._split is not None:
            self.app._split.auto_indent = self.app.editor.auto_indent
            self.app._split.auto_close = self.app.editor.auto_close
        look_changed = self.theme_v.get() != self.app.theme.mode or \
            self.accent_v.get() != self.app.theme.accent_name
        self.app.terminal.log("Settings saved."
                              + (" Restarting to apply the new look…"
                                 if look_changed else ""))
        if look_changed:
            self.app.restart_requested = True
            self.app.root.after(400, self.app.root.destroy)
        self.grab_release()
        self.destroy()


def main():
    from .config import Config
    import dxn1_studio.config as cfgmod

    args = sys.argv[1:]

    # --smoke-test must never touch the real user config
    smoke = "--smoke-test" in args
    if smoke:
        tmp_cfg = tempfile.mkdtemp(prefix="dxn1-smoke-cfg-")
        cfgmod.CONFIG_DIR = tmp_cfg
        cfgmod.CONFIG_PATH = os.path.join(tmp_cfg, "config.json")

    config = Config()
    if "--reset-config" in args:
        config.reset()

    # inline args
    filtered = []
    project = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project" and i + 1 < len(args):
            project = args[i + 1]
            i += 2
            continue
        if a in ("--smoke-test", "--reset-config", "--no-splash"):
            i += 1
            continue
        # bare path convenience: dxn1 studio ~/my-app
        if os.path.isdir(a) and project is None:
            project = a
            i += 1
            continue
        filtered.append(a)
        i += 1

    while True:
        app = DXN1Studio(config, smoke_test=smoke,
                         no_splash="--no-splash" in args)
        app.pending_project = project
        app.run()
        if not app.restart_requested:
            break



