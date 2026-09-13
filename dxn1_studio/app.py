"""DXN1 STUDIO — main application window."""

import os
import sys

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from . import APP_NAME, APP_VERSION, APP_CHANNEL, APP_TAGLINE
from .theme import from_config, FONT_UI, FONT_MONO
from .widgets import FileTree, CodeEditor, Terminal
from .onboarding import WelcomeWizard
from .tour import InteractiveTour


class DXN1Studio:
    def __init__(self, config, smoke_test=False):
        self.config = config
        self.theme = from_config(config)
        self.smoke_test = smoke_test
        self.restart_requested = False

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}  ·  v{APP_VERSION}-{APP_CHANNEL}")
        self.root.geometry("1200x800")
        self.root.minsize(860, 560)
        self.root.configure(bg=self.theme["bg"])

        self.open_files = {}
        self.active_file = None
        self.sidebar_visible = True
        self.terminal_visible = True

        self.widgets = {}
        self._wizard = None
        self._tour = None

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

        right = tk.Frame(self.statusbar, bg=t["statusbar"])
        right.pack(side=tk.RIGHT, padx=12)
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
        tabs_frame = tk.Frame(editor_container, bg=t["header"], height=36)
        tabs_frame.pack(fill=tk.X)
        tabs_frame.pack_propagate(False)
        self.tabs_frame = tabs_frame

        self.editor = CodeEditor(editor_container, t)
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.right_panel.add(editor_container, minsize=200)

        self.terminal = Terminal(self.right_panel, t, greeting="Ready")
        self.right_panel.add(self.terminal, height=200, minsize=80)

        self.widgets = {
            "sidebar": self.sidebar,
            "tabs_frame": self.tabs_frame,
            "editor": self.editor,
            "terminal": self.terminal,
        }

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
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=t["sidebar"], fg=t["text"],
                            activebackground=t["hover"], activeforeground=t["text"])
        view_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal)
        view_menu.add_command(label="Toggle Sidebar", command=self.toggle_sidebar)
        view_menu.add_separator()
        view_menu.add_command(label=f"Switch to {'Light' if self.theme.is_dark else 'Dark'} Theme",
                              command=self.switch_theme)
        menubar.add_cascade(label="View", menu=view_menu)

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

    # ------------------------------------------------------------- session
    def _greet(self):
        name = self.config.get("name") or "developer"
        back = not self.first_launch
        self.terminal.log(f"{APP_NAME} v{APP_VERSION}-{APP_CHANNEL} — {APP_TAGLINE}")
        self.terminal.log(f"{'Welcome back' if back else 'Welcome'}, {name}!")
        if not self.config.get("onboarded"):
            self.terminal.log("First run detected — starting setup…")

    # ------------------------------------------------------------- onboarding
    def start_wizard(self):
        if self._wizard is not None and self._wizard.win.winfo_exists():
            return
        self._tour_done_cleanup()
        self._wizard = WelcomeWizard(self.root, self.config,
                                     on_complete=self._on_wizard_complete)

    def _on_wizard_complete(self, config):
        self._wizard = None
        # if the wizard changed look-and-feel, restart into the new theme,
        # and the tour will auto-start right after.
        if config.get("theme") != self.theme.mode or \
                config.get("accent") != self.theme.accent_name:
            self.restart_requested = True
            self.root.after(150, self.root.destroy)
            return
        self.terminal.log(f"Setup complete — welcome aboard, "
                          f"{config.get('name') or 'developer'}!")
        self.start_tour()

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
    def run(self):
        if self.smoke_test:
            self._schedule_smoke_test()
        elif not self.config.needs_onboarding:
            if not self.config.get("tour_done"):
                self.root.after(700, self.start_tour)
        else:
            self.root.after(500, self.start_wizard)
        self.root.mainloop()

    def _schedule_smoke_test(self):
        """Headless self-check: wizard → tour → clean exit."""
        self.root.after(25000, self.root.destroy)  # watchdog: never hang CI

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
                bail("step1")

        def step2():
            try:
                if self._wizard is not None and self._wizard.win.winfo_exists():
                    self._wizard.finish()
                self.root.after(1500, step3)
            except Exception:
                bail("step2")

        def step3():
            try:
                self._tour_done_cleanup()
                self.start_tour()
                self.root.after(1500, step4)
            except Exception:
                bail("step3")

        def step4():
            try:
                if self._tour is not None:
                    self._tour.finish()
                self.terminal.log("Smoke test passed ✔")
                print("SMOKE-PASS", flush=True)
                self.root.after(400, self.root.destroy)
            except Exception:
                bail("step4")

        self.root.after(300, step1)


def main():
    from .config import Config

    args = sys.argv[1:]
    config = Config()
    if "--reset-config" in args:
        config.reset()

    while True:
        app = DXN1Studio(config, smoke_test="--smoke-test" in args)
        app.run()
        if not app.restart_requested:
            break
