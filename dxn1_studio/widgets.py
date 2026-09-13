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
    """Output panel — everything DXN1 does is echoed here."""

    def __init__(self, parent, theme, greeting=None):
        super().__init__(parent, bg=theme["terminal"])
        self.theme = theme

        header = tk.Frame(self, bg=theme["header"], height=30)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="TERMINAL", bg=theme["header"],
                 fg=theme["text_secondary"], font=(FONT_UI, 9, "bold")
                 ).pack(side=tk.LEFT, padx=15)

        self.output = tk.Text(self, bg=theme["terminal"], fg=theme["text"],
                              font=(FONT_MONO, 10), state="disabled",
                              relief=tk.FLAT, padx=10, pady=6, bd=0,
                              highlightthickness=0, insertbackground=theme["text"])
        self.output.pack(fill=tk.BOTH, expand=True)

        if greeting:
            self.log(greeting)
        else:
            self.log(f"Welcome to {APP_NAME} v{APP_VERSION}-{APP_CHANNEL}")
            self.log("Ready")

    def log(self, message):
        self.output.config(state="normal")
        self.output.insert(tk.END, f"> {message}\n")
        self.output.see(tk.END)
        self.output.config(state="disabled")
