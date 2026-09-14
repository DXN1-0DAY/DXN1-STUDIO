"""DXN1 STUDIO — main application window.

v2.1 flow: boot splash → (first run: welcome wizard) → Project Hub →
the IDE itself. Everything extra stays opt-in: Flask & friends are
installed only from the Packages page, and DXN1 Agents (if enabled in
onboarding) asks permission before every edit and command unless you
switch it to full access.
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
from .theme import from_config, FONT_UI, FONT_MONO
from .widgets import FileTree, CodeEditor, Terminal
from .onboarding import WelcomeWizard
from .tour import InteractiveTour
from . import projects, export
from .hub import ProjectHub
from .splash import Splash
from .packages import PackageManager
from .agent import DXN1AgentPanel, AgentSettingsDialog, AGENTS_NAME


class DXN1Studio:
    def __init__(self, config, smoke_test=False, no_splash=False):
        self.config = config
        self.theme = from_config(config)
        self.smoke_test = smoke_test
        self.no_splash = no_splash
        self.restart_requested = False

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}  ·  v{APP_VERSION}-{APP_CHANNEL}")
        self.root.geometry("1240x800")
        self.root.minsize(900, 560)
        self.root.configure(bg=self.theme["bg"])

        self.open_files = {}
        self.active_file = None
        self.sidebar_visible = True
        self.terminal_visible = True

        self.project_dir = None
        self.project_kind = "empty"
        self.pending_project = None      # from --project CLI arg
        self.agent_panel = None
        self.agents_visible = False
        self._hub = None
        self._wizard = None
        self._tour = None
        self._packages = None
        self._splash_active = False
        self.proc = None
        self._proc_q = queue.Queue()

        self.widgets = {}
        self.first_launch = config.register_launch()
        self.setup_ui()
        self.setup_menu()
        self.setup_bindings()

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
        self.status_ws = tk.Label(left, text="", bg=t["statusbar"],
                                  fg=t.accent, font=(FONT_UI, 9, "bold"))
        self.status_ws.pack(side=tk.LEFT, padx=(14, 0))

        right = tk.Frame(self.statusbar, bg=t["statusbar"])
        right.pack(side=tk.RIGHT, padx=12)
        self.status_agents = tk.Label(right, text="", bg=t["statusbar"],
                                      fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_agents.pack(side=tk.RIGHT, padx=(0, 10))
        tk.Label(right, text=f"v{APP_VERSION}-{APP_CHANNEL}", bg=t["statusbar"],
                 fg=t["text_muted"], font=(FONT_UI, 9)).pack(side=tk.RIGHT)

        # main panes — NOTE: uses theme["border"]; v1.0 crashed here (DARK_BORDER)
        self.main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                                             bg=t["border"], sashwidth=3, bd=0)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.sidebar = FileTree(self.main_container, t, on_file_select=self.open_file)
        self.main_container.add(self.sidebar, width=250, minsize=180)

        self.right_panel = tk.PanedWindow(self.main_container, orient=tk.VERTICAL,
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

        self.editor = CodeEditor(editor_container, t)
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.right_panel.add(editor_container, minsize=200)

        self.terminal = Terminal(self.right_panel, t, greeting="Ready",
                                 on_command=self.handle_terminal_command)
        self.right_panel.add(self.terminal, height=200, minsize=80)

        self.widgets = {
            "sidebar": self.sidebar,
            "tabs_frame": self.tabs_frame,
            "toolbar": self.toolbar,
            "editor": self.editor,
            "terminal": self.terminal,
        }

        # DXN1 Agents dock (right) — only when opted in
        self.agents_visible = False
        if self.config.get("agents_enabled"):
            self._build_agent_panel()
        self._refresh_agents_status()

    def _chip(self, parent, text, fg=None, accent=False, cmd=None):
        lbl = tk.Label(parent, text=text,
                       bg=self.theme.accent if accent else self.theme["header"],
                       fg="#ffffff" if accent else (fg or self.theme["text_secondary"]),
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
        self._chip(self.toolbar, "■ Stop", fg=t["text_muted"], cmd=self.stop_run)
        tk.Frame(self.toolbar, bg=t["border"], width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=8)
        self._chip(self.toolbar, "Packages", cmd=self.open_packages)
        self._chip(self.toolbar, "Export ZIP", cmd=self.export_project_zip)
        self._chip(self.toolbar, "Hub", cmd=self.open_hub)

    def _build_agent_panel(self):
        if self.agent_panel is not None:
            return
        self.agent_panel = DXN1AgentPanel(self.main_container, self)
        if self.agents_visible:
            self.main_container.add(self.agent_panel, width=300, minsize=240)
        self.widgets["agents"] = self.agent_panel

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

    def _refresh_agents_status(self):
        if not self.config.get("agents_enabled"):
            self.status_agents.config(text="")
            return
        if not self.config.get("agents_ask_edits") and \
                not self.config.get("agents_ask_commands"):
            self.status_agents.config(text="◆ Agents: full access",
                                      fg=self.theme["success"])
        else:
            self.status_agents.config(text="◆ Agents: ask mode",
                                      fg=self.theme["text_muted"])

    def setup_menu(self):
        t = self.theme
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"], activeforeground=t["text"])
        file_menu.add_command(label="New File", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open File…", command=self.open_file_dialog,
                              accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As…", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Project Hub…", command=self.open_hub)
        file_menu.add_command(label="Open Workspace…", command=self.open_workspace_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Export Project as ZIP…",
                              command=self.export_project_zip)
        file_menu.add_command(label="Export Current File As…",
                              command=self.export_current_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"], activeforeground=t["text"])
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
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings…", command=self.open_settings,
                              accelerator="Ctrl+,")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"], activeforeground=t["text"])
        view_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal)
        view_menu.add_command(label="Toggle Sidebar", command=self.toggle_sidebar)
        if self.config.get("agents_enabled"):
            view_menu.add_command(label="Toggle DXN1 Agents",
                                  command=self.toggle_agents_panel)
        view_menu.add_separator()
        view_menu.add_command(
            label=f"Switch to {'Light' if self.theme.is_dark else 'Dark'} Theme",
            command=self.switch_theme)
        menubar.add_cascade(label="View", menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                             activebackground=t["hover"], activeforeground=t["text"])
        tools_menu.add_command(label="Run Project", command=self.run_current,
                               accelerator="F5")
        tools_menu.add_command(label="Stop", command=self.stop_run)
        tools_menu.add_separator()
        tools_menu.add_command(label="Manage Packages…", command=self.open_packages)
        tools_menu.add_command(label="Project Hub…", command=self.open_hub)
        if self.config.get("agents_enabled"):
            tools_menu.add_command(label=f"{AGENTS_NAME} Settings…",
                                   command=lambda: AgentSettingsDialog(self))
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"], activeforeground=t["text"])
        help_menu.add_command(label="Replay Welcome & Tour", command=self.start_wizard)
        help_menu.add_separator()
        help_menu.add_command(label="About DXN1 STUDIO", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def setup_bindings(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-y>", lambda e: self.editor.text.event_generate("<<Redo>>"))
        self.root.bind("<F5>", lambda e: self.run_current())
        self.root.bind("<Control-comma>", lambda e: self.open_settings())

    # ------------------------------------------------------------- session
    def _greet(self):
        name = self.config.get("name") or "developer"
        back = not self.first_launch
        self.terminal.log(f"{APP_NAME} v{APP_VERSION}-{APP_CHANNEL} — {APP_TAGLINE}")
        self.terminal.log(f"{'Welcome back' if back else 'Welcome'}, {name}!")
        self.terminal.log("Type 'help' for studio commands.")
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
        self._hub = ProjectHub(self.root, self.config, self.theme,
                               on_open=self._on_hub_open,
                               on_explore=self._on_hub_explore)

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
            self._set_workspace(path, projects.read_project_meta(path)["kind"])

    def _set_workspace(self, path, kind):
        self.project_dir = os.path.abspath(path)
        self.project_kind = kind
        meta = projects.read_project_meta(path)
        name = meta["name"]
        projects.touch_recent(self.config, path, kind)
        self.sidebar.load_directory(self.project_dir)
        self.status_ws.config(text=f"◆ {name}")
        self.root.title(f"{name} — {APP_NAME} · v{APP_VERSION}-{APP_CHANNEL}")
        self.terminal.log(f"Workspace: {name} ({kind}) — {self.project_dir}")
        # auto-open the most interesting entry file
        if not self.editor.file_path:
            for cand in ("app.py", "main.py"):
                p = os.path.join(self.project_dir, cand)
                if os.path.isfile(p):
                    self.open_file(p)
                    break

    def refresh_explorer(self):
        self.sidebar.load_directory(self.project_dir or os.path.expanduser("~"))

    # ------------------------------------------------------------- onboarding
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
            with open(filepath, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file:\n{e}")
            return
        self.editor.set_content(content)
        self.editor.file_path = filepath
        self.status_file.config(text=filepath)
        self.terminal.log(f"Opened: {filepath}")
        self.add_tab(os.path.basename(filepath))

    def save_file(self):
        if self.editor.file_path:
            try:
                with open(self.editor.file_path, "w", encoding="utf-8") as fh:
                    fh.write(self.editor.get_content())
                self.terminal.log(f"Saved: {self.editor.file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{e}")
        else:
            self.save_file_as()

    def save_file_as(self):
        filepath = filedialog.asksaveasfilename(title="Save As", defaultextension=".txt")
        if filepath:
            self.editor.file_path = filepath
            self.status_file.config(text=filepath)
            self.save_file()

    def add_tab(self, filename):
        tab = tk.Frame(self.tabs_frame, bg=self.theme["header"])
        tk.Label(tab, text=filename, bg=self.theme["header"], fg=self.theme["text"],
                 font=(FONT_UI, 9)).pack(side=tk.LEFT, padx=10, pady=8)
        close = tk.Label(tab, text="✕", bg=self.theme["header"], fg=self.theme["text_muted"],
                         font=(FONT_UI, 9), cursor="hand2")
        close.pack(side=tk.RIGHT, padx=8)
        tab.pack(side=tk.LEFT)
        close.bind("<Button-1>", lambda e, t=tab, n=filename: self.close_tab(t, n))

    def close_tab(self, tab, filename):
        tab.destroy()
        self.editor.set_content("")
        self.editor.file_path = None
        self.status_file.config(text="No file open")
        self.terminal.log(f"Closed: {filename}")

    # ------------------------------------------------------------- packages
    def open_packages(self, autostart=None):
        if self._packages is not None and self._packages.winfo_exists():
            self._packages.deiconify()
            self._packages.lift()
        else:
            self._packages = PackageManager(self.root, self.theme)
        if autostart:
            self._packages.install_packages(autostart)
        return self._packages

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
            messagebox.showerror("Export", f"Export failed:\n{e}")
            return
        self.terminal.log(f"Exported {count} files → {path}")

    def export_current_file(self):
        if not self.editor.file_path:
            self.save_file_as()
            if not self.editor.file_path:
                return
        self.save_file()
        dest = filedialog.asksaveasfilename(
            title="Export Current File As",
            initialfile=os.path.basename(self.editor.file_path))
        if not dest:
            return
        export.export_file_bytes(self.editor.get_content(), dest)
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
            return
        self.run_file(target)

    def run_file(self, path):
        path = os.path.abspath(path)
        if path == self.editor.file_path:
            self.save_file()
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
                    ("packages", "open the optional-dependencies page"),
                    ("hub", "open the Project Hub"),
                    ("export", "export the workspace as a ZIP"),
                    ("agent <request>", "talk to DXN1 Agents (if enabled)"),
                    ("settings", "open studio settings")):
                self.terminal.log(f"  {cmd:<12} — {desc}")
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

    # ------------------------------------------------------------- settings
    def open_settings(self):
        SettingsDialog(self)

    def show_settings_saved(self):
        self.terminal.log("Settings saved.")

    # ----------------------------------------------------------------- view
    def toggle_terminal(self):
        if self.terminal_visible:
            self.right_panel.forget(self.terminal)
        else:
            self.right_panel.forget(self.editor.master)
            self.right_panel.add(self.editor.master, minsize=200)
            self.right_panel.add(self.terminal, height=200, minsize=80)
        self.terminal_visible = not self.terminal_visible

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.main_container.forget(self.sidebar)
        else:
            self.main_container.forget(self.right_panel)
            self.main_container.add(self.sidebar, width=250, minsize=180)
            self.main_container.add(self.right_panel)
        self.sidebar_visible = not self.sidebar_visible

    def switch_theme(self):
        self.config.set("theme", "light" if self.theme.is_dark else "dark")
        self.restart_requested = True
        self.root.after(120, self.root.destroy)

    def show_about(self):
        messagebox.showinfo(
            "About DXN1 STUDIO",
            f"{APP_NAME} v{APP_VERSION}-{APP_CHANNEL}\n\n"
            f"{APP_TAGLINE}\n\n"
            "A custom IDE GUI built with Python & Tkinter.\n"
            "© 2026 DXN1 — MIT License")

    # ------------------------------------------------------------------ run
    def _schedule_smoke_test(self):
        """Headless self-check exercising the whole v2.1 surface."""
        self.root.after(45000, self.root.destroy)  # watchdog: never hang CI
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
                self.root.after(600, step7)
            except Exception:
                bail("step6-agent")

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
                if self._packages is not None:
                    self._packages.destroy()
                    self._packages = None
                self.handle_terminal_command("help")
                self.handle_terminal_command("dxn1 studio")  # splash replay
                self.root.after(2600, step10)
            except Exception:
                bail("step9-commands")

        def step10():
            try:
                assert self.root.winfo_ismapped() or \
                    self.root.state() == "normal", "splash did not restore"
                self.terminal.log("Smoke test passed ✔")
                print("SMOKE-PASS", flush=True)
                self.root.after(400, self.root.destroy)
            except Exception:
                bail("step10-final")

        self.root.after(300, step1)


class SettingsDialog(tk.Toplevel):
    """Studio preferences: look & feel, boot behaviour, agent switches."""

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
        for name, spec in (("violet", "Violet"), ("cyan", "Cyan"),
                           ("green", "Green"), ("orange", "Orange")):
            tk.Radiobutton(row2, text=spec, variable=self.accent_v, value=name,
                           bg=t["card"], fg=t["text"],
                           activebackground=t["card"], activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0, bd=0
                           ).pack(side=tk.LEFT, padx=12)

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
                           highlightthickness=0, bd=0).pack(side=tk.LEFT, padx=(12, 4))
            tk.Label(row, text=label, bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(row, text=f"  ·  {sub}", bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8)).pack(side=tk.LEFT)

        # --- agents
        sec3 = self._section(box, "DXN1 Agents")
        btn = tk.Label(sec3, text="Open agent settings…", bg=t["card"],
                       fg=t.accent, font=(FONT_UI, 10, "bold"), cursor="hand2",
                       padx=10, pady=8)
        btn.pack(fill=tk.X)
        btn.bind("<Button-1>", lambda e: AgentSettingsDialog(app))
        tk.Label(sec3, text="Permission gates (ask vs full access) live there.",
                 bg=t["card"], fg=t["text_secondary"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=10, pady=(0, 6))

        # --- buttons
        row = tk.Frame(box, bg=t["bg"])
        row.pack(fill=tk.X, pady=(16, 0))
        cancel = tk.Label(row, text="Cancel", bg=t["bg"], fg=t["text_secondary"],
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
        tk.Label(parent, text=title, bg=self.t["bg"], fg=self.t["text_secondary"],
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
        x = self.master.winfo_rootx() + max(0, (self.master.winfo_width() - w) // 2)
        y = self.master.winfo_rooty() + max(0, (self.master.winfo_height() - h) // 3)
        self.geometry(f"+{x}+{y}")

    def _save(self):
        cfg = self.app.config
        cfg.set("theme", self.theme_v.get())
        cfg.set("accent", self.accent_v.get())
        cfg.set("splash_enabled", bool(self.splash_v.get()))
        cfg.set("hub_on_startup", bool(self.hub_v.get()))
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
