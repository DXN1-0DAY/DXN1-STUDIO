"""DXN1 STUDIO — core widgets: file explorer, code editor, terminal.

Every widget receives the active :class:`~dxn1_studio.theme.Theme` at
construction so the whole IDE can be rebuilt under a new palette.
"""

import os
import tkinter as tk
from tkinter import ttk

from . import APP_NAME, APP_VERSION, APP_CHANNEL
from .theme import FONT_UI, FONT_MONO


class FileTree(tk.Frame):
    """Project explorer sidebar — click any file to open it."""

    def __init__(self, parent, theme, on_file_select=None, start_dir=None):
        super().__init__(parent, bg=theme["sidebar"])
        self.theme = theme
        self.on_file_select = on_file_select
        self.current_dir = start_dir or os.path.expanduser("~")

        header = tk.Frame(self, bg=theme["header"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="EXPLORER", bg=theme["header"],
                 fg=theme["text_secondary"], font=(FONT_UI, 10, "bold"),
                 ).pack(side=tk.LEFT, padx=15)

        self.canvas = tk.Canvas(self, bg=theme["sidebar"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL,
                                       command=self.canvas.yview)
        self.tree_frame = tk.Frame(self.canvas, bg=theme["sidebar"])

        self.tree_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._win = self.canvas.create_window((0, 0), window=self.tree_frame,
                                              anchor="nw", width=230)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))

        self.load_directory(self.current_dir)

    def load_directory(self, path):
        for widget in self.tree_frame.winfo_children():
            widget.destroy()
        try:
            entries = sorted(os.listdir(path),
                             key=lambda x: (not os.path.isdir(os.path.join(path, x)),
                                            x.lower()))
            for entry in entries:
                full_path = os.path.join(path, entry)
                is_dir = os.path.isdir(full_path)

                item_frame = tk.Frame(self.tree_frame, bg=self.theme["sidebar"])
                item_frame.pack(fill=tk.X, pady=1)

                icon = "▸" if is_dir else "·"
                label = tk.Label(item_frame, text=f"{icon}  {entry}",
                                 bg=self.theme["sidebar"], fg=self.theme["text"],
                                 font=(FONT_MONO, 9), anchor="w")
                label.pack(fill=tk.X, padx=14, pady=3)

                if not is_dir and self.on_file_select:
                    label.bind("<Button-1>",
                               lambda e, p=full_path: self.on_file_select(p))
                    label.bind("<Enter>",
                               lambda e, w=label: w.config(bg=self.theme["hover"]))
                    label.bind("<Leave>",
                               lambda e, w=label: w.config(bg=self.theme["sidebar"]))
        except PermissionError:
            pass


class CodeEditor(tk.Frame):
    """Line-numbered editor with undo support."""

    def __init__(self, parent, theme):
        super().__init__(parent, bg=theme["editor"])
        self.theme = theme
        self.file_path = None
        self.modified = False

        self.text_frame = tk.Frame(self, bg=theme["editor"])
        self.text_frame.pack(fill=tk.BOTH, expand=True)

        self.line_numbers = tk.Text(self.text_frame, width=4, padx=10, pady=6,
                                    bg=theme["linenum_bg"], fg=theme["linenum_fg"],
                                    font=(FONT_MONO, 11), state="disabled",
                                    relief=tk.FLAT, bd=0, highlightthickness=0)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.text = tk.Text(self.text_frame, bg=theme["editor"], fg=theme["text"],
                            insertbackground=theme["text"],
                            selectbackground=theme.accent,
                            selectforeground=theme["select_fg"],
                            font=(FONT_MONO, 11), padx=14, pady=6,
                            relief=tk.FLAT, bd=0, undo=True,
                            highlightthickness=0, wrap=tk.NONE)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text.bind("<KeyRelease>", self.update_line_numbers)
        self.text.bind("<MouseWheel>", self.update_line_numbers)
        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        lines = self.text.get("1.0", tk.END).count("\n")
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        for i in range(1, lines + 1):
            self.line_numbers.insert(tk.END, f"{i}\n")
        self.line_numbers.config(state="disabled")

    def set_content(self, content):
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.update_line_numbers()

    def get_content(self):
        return self.text.get("1.0", tk.END)


class Terminal(tk.Frame):
    """Interactive terminal panel.

    Everything the studio does is echoed here, and the user can type
    studio commands (``dxn1 studio``, ``help``, ``clear``, ``packages``,
    ``run``…) — handled by the callback the app passes in.
    """

    def __init__(self, parent, theme, greeting=None, on_command=None):
        super().__init__(parent, bg=theme["terminal"])
        self.theme = theme
        self.on_command = on_command
        self.history = []
        self.history_pos = None

        header = tk.Frame(self, bg=theme["header"], height=30)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="TERMINAL", bg=theme["header"],
                 fg=theme["text_secondary"], font=(FONT_UI, 9, "bold")
                 ).pack(side=tk.LEFT, padx=15)
        tk.Label(header, text="type 'help' for studio commands",
                 bg=theme["header"], fg=theme["text_muted"],
                 font=(FONT_UI, 8)).pack(side=tk.LEFT, padx=8)

        clear_btn = tk.Label(header, text="clear", bg=theme["header"],
                             fg=theme["text_muted"], font=(FONT_UI, 8, "underline"),
                             cursor="hand2")
        clear_btn.pack(side=tk.RIGHT, padx=12)
        clear_btn.bind("<Button-1>", lambda e: self.clear())

        self.output = tk.Text(self, bg=theme["terminal"], fg=theme["text"],
                              font=(FONT_MONO, 10), state="disabled",
                              relief=tk.FLAT, padx=10, pady=6, bd=0,
                              highlightthickness=0, insertbackground=theme["text"])
        self.output.pack(fill=tk.BOTH, expand=True)

        # command input row
        row = tk.Frame(self, bg=theme["terminal"])
        row.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Label(row, text="❯", bg=theme["terminal"], fg=theme.accent,
                 font=(FONT_MONO, 10, "bold")).pack(side=tk.LEFT)
        self.input = tk.Entry(row, bg=theme["terminal"], fg=theme["text"],
                              insertbackground=theme["text"], relief=tk.FLAT,
                              font=(FONT_MONO, 10), highlightthickness=0, bd=0)
        self.input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), ipady=4)
        self.input.bind("<Return>", self._submit)
        self.input.bind("<Up>", lambda e: self._history_step(-1))
        self.input.bind("<Down>", lambda e: self._history_step(1))

        if greeting:
            self.log(greeting)
        else:
            self.log(f"Welcome to {APP_NAME} v{APP_VERSION}-{APP_CHANNEL}")
            self.log("Ready")

    # ---------------------------------------------------------------- output
    def log(self, message):
        self._append(f"> {message}\n")

    def log_raw(self, text):
        """Stream process output verbatim (no '> ' prefix)."""
        if not text.endswith("\n"):
            text += "\n"
        self._append(text)

    def _append(self, text):
        self.output.config(state="normal")
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def clear(self):
        self.output.config(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.config(state="disabled")

    # ---------------------------------------------------------------- input
    def _submit(self, event=None):
        text = self.input.get().strip()
        self.input.delete(0, tk.END)
        if not text:
            return
        self.history.append(text)
        self.history_pos = None
        self.log(text)
        if self.on_command:
            try:
                self.on_command(text)
            except Exception as exc:  # noqa: BLE001 — terminal never crashes IDE
                self.log(f"command error: {exc}")

    def _history_step(self, delta):
        if not self.history:
            return
        if self.history_pos is None:
            self.history_pos = len(self.history) - 1 if delta < 0 else None
        else:
            self.history_pos = max(0, min(len(self.history) - 1,
                                          self.history_pos + delta))
        if self.history_pos is not None:
            self.input.delete(0, tk.END)
            self.input.insert(0, self.history[self.history_pos])
        else:
            self.input.delete(0, tk.END)
