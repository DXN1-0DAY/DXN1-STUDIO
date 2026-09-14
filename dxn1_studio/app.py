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

import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from . import APP_NAME, APP_VERSION, APP_CHANNEL, APP_TAGLINE
from .theme import from_config, FONT_UI, FONT_MONO, ACCENTS
from .widgets import FileTree, CodeEditor, Terminal
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
from .agent import DXN1AgentPanel, AgentSettingsDialog, ConnectDialog, \
    AGENTS_NAME

FONT_SIZES = (("small", 10), ("medium", 11), ("large", 13))


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
        self.entry = tk.Entry(wrap, bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"], relief=tk.FLAT,
                              font=(FONT_UI, 12), highlightthickness=0)
        self.entry.pack(fill=tk.X, padx=12, pady=12, ipady=6)
        self.entry.insert(0, "")
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", lambda e: self._run_selected())
        self.entry.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Down>", lambda e: self._move(1))

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
            tk.Label(row, text=label, bg=row.cget("bg"),
                     fg="#ffffff" if active else self.t["text"],
                     font=(FONT_UI, 10), anchor="w").pack(
                side=tk.LEFT, padx=10, pady=6)
            if hint:
                tk.Label(row, text=hint, bg=row.cget("bg"),
                         fg="#ffffff" if active else self.t["text_muted"],
                         font=(FONT_UI, 8)).pack(side=tk.RIGHT, padx=10)
            row.bind("<Button-1>", lambda e, i=i: self._pick(i))
        if not self.filtered:
            tk.Label(self.rows, text="no matching command",
                     bg=self.t["card"], fg=self.t["text_muted"],
                     font=(FONT_UI, 9)).pack(pady=8)

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
        self._greet()

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

        # body: activity rail + main panes
        body = tk.Frame(self.root, bg=t["bg"])
        body.pack(fill=tk.BOTH, expand=True)

        self.activity = tk.Frame(body, width=46, bg=t["header"])
        self.activity.pack(side=tk.LEFT, fill=tk.Y)
        self.activity.pack_propagate(False)
        self._build_activity()

        # NOTE: uses theme["border"]; v1.0 crashed here (DARK_BORDER)
        self.main_container = tk.PanedWindow(body, orient=tk.HORIZONTAL,
                                             bg=t["border"], sashwidth=3,
                                             bd=0)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ---- sidebar container with switchable views
        self.sidebar_container = tk.Frame(self.main_container,
                                          bg=t["sidebar"])
        self.sidebar = FileTree(self.sidebar_container, t,
                                on_file_select=self.open_file)
        self.sidebar.pack(fill=tk.BOTH, expand=True)
        self.search_view = SearchPanel(self.sidebar_container, t,
                                       on_open_match=self.open_search_match)
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

        self.widgets = {
            "sidebar": self.sidebar,
            "sidebar_container": self.sidebar_container,
            "activity": self.activity,
            "search": self.search_view,
            "packages": self.packages_view,
            "tabs_frame": self.tabs_frame,
            "toolbar": self.toolbar,
            "editor": self.editor,
            "terminal": self.terminal,
        }

        # DXN1 Agents dock (right) — only when opted in
        self.agents_visible = False
        self._build_agent_panel()
        self._refresh_agents_status()

    # --------------------------------------------------------- activity bar
    def _build_activity(self):
        t = self.theme
        self._activity_items = []
        for key, tip, cmd in (
                ("explorer", "Explorer", lambda: self.show_sidebar_view("explorer")),
                ("search", "Search in files", lambda: self.show_sidebar_view("search")),
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
        elif kind == "packages":
            canvas.create_rectangle(11, 13, 35, 31, outline=color, width=2)
            canvas.create_line(11, 20, 35, 20, fill=color)
            canvas.create_line(23, 13, 23, 20, fill=color)
        elif kind == "hub":
            for x, y in ((12, 11), (25, 11), (12, 24), (25, 24)):
                canvas.create_rectangle(x, y, x + 9, y + 9,
                                        outline=color, width=2)
        elif kind == "agents":
            canvas.create_polygon(23, 9, 34, 21, 23, 33, 12, 21,
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
        if name not in ("explorer", "search", "packages"):
            return
        self.sidebar_view = name
        self.sidebar.pack_forget()
        for view in (self.search_view, self.packages_view):
            view.pack_forget()
        view = {"explorer": self.sidebar, "search": self.search_view,
                "packages": self.packages_view}[name]
        view.pack(fill=tk.BOTH, expand=True)
        self._paint_activity()
        if name == "search":
            self.search_view.set_workspace(self.project_dir)
            self.search_view.entry.focus_set()

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

    def _build_agent_panel(self):
        if self.agent_panel is not None:
            return
        self.agent_panel = DXN1AgentPanel(self.main_container, self)
        if self.project_dir:
            self.agent_panel.set_workspace(self.project_dir)
        if self.agents_visible:
            self.main_container.add(self.agent_panel, width=300, minsize=240)
        self.widgets["agents"] = self.agent_panel
        self._paint_activity()

    def apply_agents_visibility(self):
        enabled = bool(self.config.get("agents_enabled"))
        if enabled and self.agent_panel is None:
            self._build_agent_panel()
            self.agents_visible = True
            self.main_container.add(self.agent_panel, width=300, minsize=240)
        elif not enabled and self.agent_panel is not None:
            try:
                self.main_container.forget(self.agent_panel)
            except tk.TclError:
                pass
            self.agent_panel.destroy()
            self.agent_panel = None
            self.widgets.pop("agents", None)
            self.agents_visible = False
        elif enabled and self.agent_panel is not None and \
                self.agents_visible and \
                self.agent_panel not in self.main_container.panes():
            self.main_container.add(self.agent_panel, width=300, minsize=240)
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
                self.main_container.forget(self.agent_panel)
            except tk.TclError:
                pass
            self.agents_visible = False
        else:
            self.main_container.add(self.agent_panel, width=300, minsize=240)
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
        t = self.theme
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"],
                            activeforeground=t["text"])
        file_menu.add_command(label="New File", command=self.new_file,
                              accelerator="Ctrl+N")
        file_menu.add_command(label="Open File…", command=self.open_file_dialog,
                              accelerator="Ctrl+O")
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
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"],
                            activeforeground=t["text"])
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
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"],
                            activeforeground=t["text"])
        view_menu.add_command(label="Command Palette",
                              command=self.open_palette,
                              accelerator="Ctrl+K")
        view_menu.add_separator()
        view_menu.add_command(label="Explorer", command=lambda:
                              self.show_sidebar_view("explorer"))
        view_menu.add_command(label="Search in Files", command=lambda:
                              self.show_sidebar_view("search"))
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
        menubar.add_cascade(label="View", menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                             activebackground=t["hover"],
                             activeforeground=t["text"])
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
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"],
                            activeforeground=t["text"])
        help_menu.add_command(label="Replay Welcome & Tour",
                              command=self.start_wizard)
        help_menu.add_separator()
        help_menu.add_command(label="About DXN1 STUDIO", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def setup_bindings(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-y>", lambda e:
                       self.editor.text.event_generate("<<Redo>>"))
        self.root.bind("<F5>", lambda e: self.run_current())
        self.root.bind("<Control-comma>", lambda e: self.open_settings())
        self.root.bind("<Control-k>", lambda e: self.open_palette())
        self.root.bind("<Control-P>", lambda e: self.open_palette())
        self.root.bind("<Control-f>", lambda e: self.toggle_find())
        self.root.bind("<Control-w>", lambda e: self.close_active_tab())
        self.root.bind("<Control-Tab>", lambda e: self.cycle_tab(1))
        self.root.bind("<Control-plus>", lambda e: self.change_font_size(1))
        self.root.bind("<Control-equal>", lambda e: self.change_font_size(1))
        self.root.bind("<Control-minus>", lambda e: self.change_font_size(-1))
        self.root.bind("<Escape>", self._on_escape)

    def _on_escape(self, event=None):
        if self.findbar.winfo_ismapped():
            self.toggle_find(show=False)
            return "break"

    def _update_cursor_pos(self, event=None):
        try:
            line, col = self.editor.text.index("insert").split(".")
            self.status_pos.config(text=f"Ln {line}, Col {int(col) + 1}")
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
        self.root.deiconify()
        if not self.config.get("tour_done"):
            self.root.after(800, self.start_tour)

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
        self.status_file.config(text=filepath)
        self._update_cursor_pos()
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
            tab = tk.Frame(self.tabs_frame, bg=t["header"])
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
            self._tab_frames[filepath] = {"frame": tab, "label": label,
                                          "close": close, "bar": bar}
        self._activate_tab(filepath)

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
        x = tk.Label(row, text="✕", bg=t["header"], fg=t["text_muted"],
                     font=(FONT_UI, 10), cursor="hand2", padx=8)
        x.pack(side=tk.RIGHT)
        x.bind("<Button-1>", lambda e: self.toggle_find(show=False))
        return bar

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
            self.findbar.pack_forget()
            self.editor.text.focus_set()

    def _find_live(self, event=None):
        if event and event.keysym in ("Return", "Escape", "Up", "Down"):
            return
        needle = self.find_var.get()
        if not needle:
            self.editor.clear_find()
            self.find_count.config(text="")
            return
        count = self.editor.find(needle)
        self.find_count.config(
            text=f"{count} hit{'s' if count != 1 else ''}"
            if count else "no hits")

    def _find_next(self, delta):
        needle = self.find_var.get()
        if needle:
            self.editor.find(needle, backwards=delta < 0)

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
        if low.startswith("agent "):
            if self.agent_panel is not None:
                self.agent_panel.handle(text[6:].strip())
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
        messagebox.showinfo(
            "About DXN1 STUDIO",
            f"{APP_NAME} v{APP_VERSION}-{APP_CHANNEL}\n\n"
            f"{APP_TAGLINE}\n\n"
            "A custom IDE GUI built with Python & Tkinter.\n"
            "© 2026 DXN1 — MIT License")

    # ------------------------------------------------------------------ run
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
                    emit=lambda s: None, approve=lambda *a, **k: True,
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
                self.root.after(500, step10)
            except Exception:
                bail("step9c-find-toast")

        def step10():
            try:
                self.toggle_find(show=False)
                self.handle_terminal_command("help")
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
        self.splash_v = tk.BooleanVar(value=bool(cfg.get("splash_enabled", True)))
        self.hub_v = tk.BooleanVar(value=bool(cfg.get("hub_on_startup", True)))

        box = tk.Frame(self, bg=t["bg"])
        box.pack(padx=26, pady=20)

        tk.Label(box, text="Settings", bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 14, "bold")).pack(anchor="w")

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
                 "Save the active file shortly after you stop typing.")):
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
                 "The logo card for ~2 seconds when DXN1 STUDIO starts."),
                (self.hub_v, "Start at the Project Hub",
                 "Create or reopen a workspace every launch.")):
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
        return inner

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
        cfg.set("splash_enabled", bool(self.splash_v.get()))
        cfg.set("hub_on_startup", bool(self.hub_v.get()))
        # editor changes apply live; colours need the rebuild
        self.app.editor.set_font_size(cfg.get("editor_font_size", 11))
        self.app.editor.set_wrap(bool(cfg.get("word_wrap", False)))
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



