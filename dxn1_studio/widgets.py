"""DXN1 STUDIO — core widgets: file explorer, code editor, terminal.

Every widget receives the active :class:`~dxn1_studio.theme.Theme` at
construction so the whole IDE can be rebuilt under a new palette.

v1.1 additions: lightweight syntax highlighting (regex-based, no deps,
theme-aware), an in-editor find bar API, an expandable file tree and
runtime font-size / word-wrap controls.
"""

import os
import re
import tkinter as tk
from tkinter import ttk

from . import APP_NAME, APP_VERSION, APP_CHANNEL
from .theme import FONT_UI, FONT_MONO

# directories the explorer never renders (huge / irrelevant)
TREE_SKIP = {".git", "__pycache__", ".venv", "venv", "node_modules",
             ".dxn1-studio", ".pytest_cache", ".mypy_cache", "dist",
             "build", ".idea", ".vs"}


# =====================================================================
#  syntax highlighting — one master regex per language, zero deps
# =====================================================================
HL_COLORS = {
    "dark": {
        "keyword":   "#ff7b72",
        "string":    "#a5d6ff",
        "comment":   "#8b949e",
        "number":    "#79c0ff",
        "builtin":   "#d2a8ff",
        "decorator": "#ffa657",
        "self":      "#79c0ff",
        "defname":   "#7ee787",
        "tag":       "#7ee787",
        "attr":      "#ffa657",
        "prop":      "#79c0ff",
    },
    "light": {
        "keyword":   "#cf222e",
        "string":    "#0a3069",
        "comment":   "#6e7781",
        "number":    "#0550ae",
        "builtin":   "#8250df",
        "decorator": "#bc4c00",
        "self":      "#0550ae",
        "defname":   "#116329",
        "tag":       "#116329",
        "attr":      "#bc4c00",
        "prop":      "#0550ae",
    },
}

_PY_KW = (r"\b(?:False|None|True|and|as|assert|async|await|break|class|"
          r"continue|def|del|elif|else|except|finally|for|from|global|if|"
          r"import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|"
          r"while|with|yield|match|case)\b")
_PY_BUILTIN = (r"\b(?:print|len|range|str|int|float|bool|list|dict|set|"
               r"tuple|open|input|isinstance|enumerate|zip|map|filter|sum|"
               r"min|max|abs|round|sorted|reversed|any|all|super|type|"
               r"repr|hash|iter|next|getattr|setattr|hasattr)\b")

LANG_RULES = {
    ".py": re.compile(
        r"(?P<comment>\#[^\n]*)"
        r"|(?P<string>(?:[rbfu]{0,2})'''(?:[^'\\]|\\.)*?(?:'''|$)"
        r"|(?:[rbfu]{0,2})\"\"\"(?:[^\"\\]|\\.)*?(?:\"\"\"|$)"
        r"|(?:[rbfu]{0,2})\"(?:[^\"\\\n]|\\.)*\"?"
        r"|(?:[rbfu]{0,2})'(?:[^'\\\n]|\\.)*'?)"
        r"|(?P<decorator>@[\w.]+)"
        r"|(?P<keyword>" + _PY_KW + r")"
        r"|(?P<self>\bself\b)"
        r"|(?P<defname>\b(?:def|class)\s+\w+)"
        r"|(?P<number>\b\d+(?:\.\d+)?\b)"
        r"|(?P<builtin>" + _PY_BUILTIN + r")",
        re.X),
    ".html": re.compile(
        r"(?P<comment><!--.*?-->)"
        r"|(?P<tag></?\s*[a-zA-Z][\w-]*)"
        r"|(?P<string>\"[^\"]*\"|'[^']*')"
        r"|(?P<attr>\b[a-zA-Z-]+(?=\s*=))",
        re.X | re.S),
    ".css": re.compile(
        r"(?P<comment>/\*.*?\*/)"
        r"|(?P<string>\"[^\"]*\"|'[^']*')"
        r"|(?P<prop>[a-zA-Z-]+(?=\s*:))"
        r"|(?P<number>\#[0-9a-fA-F]{3,8}\b|\b\d+(?:\.\d+)?(?:px|em|rem|vh|"
        r"vw|%|s|ms|fr)?\b)",
        re.X | re.S),
    ".js": re.compile(
        r"(?P<comment>//[^\n]*|/\*.*?\*/)"
        r"|(?P<string>`(?:[^`\\]|\\.)*`|\"(?:[^\"\\\n]|\\.)*\""
        r"|'(?:[^'\\\n]|\\.)*')"
        r"|(?P<keyword>\b(?:const|let|var|function|return|if|else|for|"
        r"while|do|class|extends|new|import|from|export|default|async|"
        r"await|try|catch|finally|throw|switch|case|break|continue|"
        r"typeof|instanceof|this|super|null|undefined|true|false)\b)"
        r"|(?P<number>\b\d+(?:\.\d+)?\b)",
        re.X | re.S),
    ".json": re.compile(
        r"(?P<key>\"(?:[^\"\\]|\\.)*\"(?=\s*:))"
        r"|(?P<string>\"(?:[^\"\\]|\\.)*\")"
        r"|(?P<number>-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)"
        r"|(?P<keyword>\b(?:true|false|null)\b)",
        re.X),
    ".md": re.compile(
        r"(?P<keyword>^\#{1,6}\s.*$)"
        r"|(?P<string>```[\s\S]*?```|`[^`\n]+`)"
        r"|(?P<decorator>\*\*[^*\n]+\*\*)"
        r"|(?P<comment>\[[^\]]+\]\([^)]+\))",
        re.X | re.M),
}

EXT_ALIAS = {".pyw": ".py", ".pyi": ".py", ".htm": ".html", ".xml": ".html",
             ".jsx": ".js", ".ts": ".js", ".tsx": ".js", ".markdown": ".md"}


def language_for(path):
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower()
    ext = EXT_ALIAS.get(ext, ext)
    return LANG_RULES.get(ext)


class Highlighter:
    """Debounced, whole-buffer highlighter for one Text widget."""

    MAX_CHARS = 120_000          # skip highlighting huge buffers

    def __init__(self, text, theme):
        self.text = text
        self.theme = theme
        self.master = None
        self._job = None
        self._make_tags()

    def _make_tags(self):
        colors = HL_COLORS["dark" if self.theme.is_dark else "light"]
        for name, color in colors.items():
            self.text.tag_configure(f"hl_{name}", foreground=color)
        self.text.tag_lower("hl_comment")
        self.text.tag_lower("hl_string")

    def set_theme(self, theme):
        self.theme = theme
        self._make_tags()

    def set_language(self, path):
        self.master = language_for(path)
        self.schedule()

    def schedule(self, delay=180):
        if self._job is not None:
            try:
                self.text.after_cancel(self._job)
            except Exception:
                pass
        self._job = self.text.after(delay, self.run)

    def run(self):
        self._job = None
        if self.master is None:
            return
        try:
            content = self.text.get("1.0", "end-1c")
        except tk.TclError:
            return
        for tag in self.text.tag_names():
            if str(tag).startswith("hl_"):
                self.text.tag_remove(tag, "1.0", "end")
        if len(content) > self.MAX_CHARS:
            return
        for m in self.master.finditer(content):
            for group, value in m.groupdict().items():
                if value:
                    start = f"1.0+{m.start(group)}c"
                    end = f"1.0+{m.end(group)}c"
                    self.text.tag_add(f"hl_{group}", start, end)


# =====================================================================
#  file tree — expandable folders, click file to open
# =====================================================================
class FileTree(tk.Frame):
    """Project explorer sidebar — expandable folders, click to open."""

    def __init__(self, parent, theme, on_file_select=None, start_dir=None):
        super().__init__(parent, bg=theme["sidebar"])
        self.theme = theme
        self.on_file_select = on_file_select
        self.current_dir = start_dir or os.path.expanduser("~")
        self._open = {self.current_dir}

        header = tk.Frame(self, bg=theme["header"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="EXPLORER", bg=theme["header"],
                 fg=theme["text_secondary"], font=(FONT_UI, 10, "bold"),
                 ).pack(side=tk.LEFT, padx=15)

        refresh = tk.Label(header, text="↻", bg=theme["header"],
                           fg=theme["text_muted"], font=(FONT_UI, 11),
                           cursor="hand2")
        refresh.pack(side=tk.RIGHT, padx=12)
        refresh.bind("<Button-1>", lambda e: self.load_directory(
            self.current_dir))
        refresh.bind("<Enter>", lambda e: refresh.config(
            fg=theme["text"]))
        refresh.bind("<Leave>", lambda e: refresh.config(
            fg=theme["text_muted"]))

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
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_wheel())

        self.load_directory(self.current_dir)

    # ------------------------------------------------------------- wheel
    def _bind_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)   # linux
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-2, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(2, "units")
        else:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # ------------------------------------------------------------- render
    def load_directory(self, path):
        self.current_dir = path
        self._open = {path}
        for widget in self.tree_frame.winfo_children():
            widget.destroy()
        self._render(path, self.tree_frame, 0)

    def _row(self, container, depth):
        frame = tk.Frame(container, bg=self.theme["sidebar"])
        frame.pack(fill=tk.X, pady=1)
        label = tk.Label(frame, bg=self.theme["sidebar"],
                         fg=self.theme["text"], font=(FONT_MONO, 9),
                         anchor="w")
        label.pack(fill=tk.X, padx=(12 + depth * 13, 8), pady=2)
        label.bind("<Enter>", lambda e: label.config(bg=self.theme["hover"]))
        label.bind("<Leave>", lambda e: label.config(bg=self.theme["sidebar"]))
        return frame, label

    def _render(self, dirpath, container, depth):
        try:
            entries = sorted(os.listdir(dirpath),
                             key=lambda x: (not os.path.isdir(
                                 os.path.join(dirpath, x)), x.lower()))
        except OSError:
            row, label = self._row(container, depth)
            label.config(text="·  (unreadable folder)",
                         fg=self.theme["text_muted"])
            return
        for entry in entries:
            if entry in TREE_SKIP:
                continue
            full = os.path.join(dirpath, entry)
            if os.path.isdir(full):
                opened = full in self._open
                row, label = self._row(container, depth)
                label.config(text=f"{'▾' if opened else '▸'}  {entry}/")
                childbox = tk.Frame(container, bg=self.theme["sidebar"])
                if opened:
                    childbox.pack(fill=tk.X)
                    self._render(full, childbox, depth + 1)
                label.bind(
                    "<Button-1>",
                    lambda e, d=full, b=childbox, dep=depth:
                    self._toggle(d, b, dep))
            else:
                row, label = self._row(container, depth)
                label.config(text=f"   {entry}")
                if self.on_file_select:
                    label.bind(
                        "<Button-1>",
                        lambda e, p=full: self.on_file_select(p))

    def _toggle(self, dirpath, childbox, depth=0):
        try:
            if dirpath in self._open:
                self._open.discard(dirpath)
                childbox.pack_forget()
                for w in childbox.winfo_children():
                    w.destroy()
            else:
                self._open.add(dirpath)
                childbox.pack(fill=tk.X)
                self._render(dirpath, childbox, depth + 1)
        except tk.TclError:
            pass
        self.canvas.update_idletasks()


# =====================================================================
#  code editor — line numbers, highlighter, find, font & wrap controls
# =====================================================================
class CodeEditor(tk.Frame):
    """Line-numbered editor with undo, highlighting and find support."""

    def __init__(self, parent, theme):
        super().__init__(parent, bg=theme["editor"])
        self.theme = theme
        self.file_path = None
        self.modified = False

        self.text_frame = tk.Frame(self, bg=theme["editor"])
        self.text_frame.pack(fill=tk.BOTH, expand=True)

        gutter = tk.Frame(self.text_frame, bg=theme["linenum_bg"])
        gutter.pack(side=tk.LEFT, fill=tk.Y)

        self.line_numbers = tk.Text(gutter, width=4, padx=10, pady=6,
                                    bg=theme["linenum_bg"],
                                    fg=theme["linenum_fg"],
                                    font=(FONT_MONO, 11), state="disabled",
                                    relief=tk.FLAT, bd=0, highlightthickness=0,
                                    cursor="arrow")
        self.line_numbers.pack(fill=tk.Y)

        body = tk.Frame(self.text_frame, bg=theme["editor"])
        body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text = tk.Text(body, bg=theme["editor"], fg=theme["text"],
                            insertbackground=theme["text"],
                            selectbackground=theme.accent,
                            selectforeground=theme["select_fg"],
                            font=(FONT_MONO, 11), padx=14, pady=6,
                            relief=tk.FLAT, bd=0, undo=True,
                            highlightthickness=0, wrap=tk.NONE)
        self.text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.xscroll = tk.Scrollbar(body, orient=tk.HORIZONTAL,
                                    command=self.text.xview)
        self.text.configure(xscrollcommand=self.xscroll.set)

        # find tags
        self.text.tag_configure("find_all",
                                background=self.theme["hover"])
        self.text.tag_configure("find_cur",
                                background=self.theme.accent,
                                foreground="#ffffff")

        self.highlighter = Highlighter(self.text, theme)

        self.text.bind("<KeyRelease>", self._on_key)
        self.text.bind("<MouseWheel>", self.update_line_numbers)
        self.text.bind("<ButtonRelease-1>", self.update_line_numbers)
        self._sync_xscroll()
        self.update_line_numbers()

    # ------------------------------------------------------------ helpers
    def _sync_xscroll(self):
        if self.text.cget("wrap") == tk.NONE:
            self.xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        else:
            self.xscroll.pack_forget()

    def _on_key(self, event=None):
        self.modified = True
        self.update_line_numbers()
        self.highlighter.schedule()

    def set_font_size(self, size):
        size = max(8, min(20, int(size)))
        self.text.config(font=(FONT_MONO, size))
        self.line_numbers.config(font=(FONT_MONO, size))

    def set_wrap(self, enabled):
        self.text.config(wrap=tk.WORD if enabled else tk.NONE)
        self._sync_xscroll()

    def update_line_numbers(self, event=None):
        lines = self.text.get("1.0", tk.END).count("\n")
        current = self.text.index("insert").split(".")[0]
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        for i in range(1, lines + 1):
            mark = f"{i}_" if str(i) == current else f"{i}"
            self.line_numbers.insert(tk.END, f"{mark}\n")
        self.line_numbers.config(state="disabled")

    def set_content(self, content, path=None):
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.modified = False
        if path is not None:
            self.file_path = path
        self.update_line_numbers()
        self.highlighter.set_language(self.file_path)

    def get_content(self):
        return self.text.get("1.0", tk.END)

    # --------------------------------------------------------------- find
    def find(self, needle, backwards=False):
        """Highlight all matches; move selection to next/prev. Returns
        match count (0 when needle is empty)."""
        self.clear_find()
        if not needle:
            return 0
        content = self.text.get("1.0", "end-1c")
        count = content.count(needle)
        if not count:
            return 0
        pos = 0
        for _ in range(count):
            idx = content.find(needle, pos)
            self.text.tag_add("find_all", f"1.0+{idx}c",
                              f"1.0+{idx + len(needle)}c")
            pos = idx + max(1, len(needle))
        try:
            rng = self.text.tag_prevrange(
                "find_all", "end") if backwards else \
                self.text.tag_nextrange("find_all", "1.0")
            ranges = []
            r = self.text.tag_nextrange("find_all", "1.0")
            while r:
                ranges.append(r)
                r = self.text.tag_nextrange("find_all", r[1])
            if ranges:
                if backwards:
                    rng = ranges[-1]
                else:
                    cur = self.text.index("insert")
                    rng = None
                    for a, b in ranges:
                        if self.text.compare(a, ">=", cur):
                            rng = (a, b)
                            break
                    rng = rng or ranges[0]
                self.text.tag_add("find_cur", rng[0], rng[1])
                self.text.mark_set("insert", rng[1])
                self.text.see(rng[0])
        except tk.TclError:
            pass
        return count

    def clear_find(self):
        for tag in ("find_all", "find_cur"):
            self.text.tag_remove(tag, "1.0", "end")


# =====================================================================
#  terminal — studio commands + streamed output
# =====================================================================
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
                              highlightthickness=0,
                              insertbackground=theme["text"])
        self.output.pack(fill=tk.BOTH, expand=True)

        # command input row
        row = tk.Frame(self, bg=theme["terminal"])
        row.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Label(row, text="❯", bg=theme["terminal"], fg=theme.accent,
                 font=(FONT_MONO, 10, "bold")).pack(side=tk.LEFT)
        self.input = tk.Entry(row, bg=theme["terminal"], fg=theme["text"],
                              insertbackground=theme["text"], relief=tk.FLAT,
                              font=(FONT_MONO, 10), highlightthickness=0, bd=0)
        self.input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0),
                        ipady=4)
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

    def log_error(self, message):
        """Red-tinted error line (tag survives theme swap by rebuilding)."""
        self._append(f"! {message}\n")

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
