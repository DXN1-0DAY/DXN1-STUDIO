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

# ANSI escape sequences (colours, cursor moves) — stripped in the terminal
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b.")



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

_GO_KW = (r"\b(?:break|case|chan|const|continue|default|defer|else|"
          r"fallthrough|for|func|go|goto|if|import|interface|map|package|"
          r"range|return|select|struct|switch|type|var|nil|true|false)\b")
_GO_BUILTIN = (r"\b(?:append|cap|close|complex|copy|delete|imag|len|make|"
               r"new|panic|print|println|real|recover)\b")
_RS_KW = (r"\b(?:as|async|await|break|const|continue|crate|dyn|else|enum|"
          r"extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|"
          r"ref|return|self|Self|static|struct|super|trait|true|type|unsafe|"
          r"use|where|while)\b")
_JAVA_KW = (r"\b(?:abstract|assert|boolean|break|byte|case|catch|char|"
            r"class|const|continue|default|do|double|else|enum|extends|"
            r"final|finally|float|for|goto|if|implements|import|instanceof|"
            r"int|interface|long|native|new|package|private|protected|"
            r"public|record|return|short|static|strictfp|super|switch|"
            r"synchronized|this|throw|throws|transient|try|var|void|"
            r"volatile|while|true|false|null)\b")
_CS_KW = (r"\b(?:abstract|as|async|await|base|bool|break|byte|case|catch|"
          r"char|checked|class|const|continue|decimal|default|delegate|do|"
          r"double|else|enum|event|explicit|extern|false|finally|fixed|"
          r"float|for|foreach|get|goto|if|implicit|in|int|interface|"
          r"internal|is|lock|long|namespace|new|null|object|operator|out|"
          r"override|params|private|protected|public|readonly|ref|return|"
          r"sbyte|sealed|set|short|sizeof|stackalloc|static|string|struct|"
          r"switch|this|throw|true|try|typeof|uint|ulong|unchecked|unsafe|"
          r"ushort|using|var|virtual|void|volatile|when|where|while|yield)"
          r"\b")
_KT_KW = (r"\b(?:as|break|catch|class|constructor|continue|do|else|false|"
          r"final|finally|for|fun|if|in|init|interface|is|null|object|"
          r"package|private|protected|public|return|super|this|throw|true|"
          r"try|typealias|val|var|when|while)\b")
_PHP_KW = (r"\b(?:abstract|and|array|as|break|callable|case|catch|class|"
           r"clone|const|continue|declare|default|do|echo|else|elseif|"
           r"empty|endswitch|endwhile|extends|final|finally|fn|for|foreach|"
           r"function|global|goto|if|implements|include|include_once|"
           r"instanceof|insteadof|interface|isset|list|match|namespace|new|"
           r"or|print|private|protected|public|readonly|require|require_once|"
           r"return|static|switch|throw|trait|try|unset|use|var|while|xor|"
           r"yield|true|false|null)\b")
_RB_KW = (r"\b(?:alias|and|begin|break|case|class|def|defined|do|else|"
          r"elsif|end|ensure|false|for|if|in|module|next|nil|not|or|raise|"
          r"redo|rescue|retry|return|self|super|then|true|undef|unless|"
          r"until|when|while|yield|require|attr_accessor|attr_reader|"
          r"attr_writer|puts|print|p)\b")
_SH_KW = (r"\b(?:if|then|else|elif|fi|for|while|until|do|done|case|esac|"
          r"function|in|select|time|coproc|break|continue|return|exit|"
          r"local|export|readonly|declare|typeset|unset|shift|source|alias|"
          r"eval|exec|trap|set|true|false|echo|cd|pwd)\b")


def _c_rule(kw, extras=()):
    """Shared rule shape for the C family: // and /* */ comments,
    three string flavors, optional language extras, annotations and
    preprocessor lines, keywords, numbers."""
    parts = [r"(?P<comment>//[^\n]*|/\*.*?\*/)",
             r"(?P<string>`(?:[^`\\]|\\.)*`|\"(?:[^\"\\\n]|\\.)*\""
             r"|'(?:[^'\\\n]|\\.)*')"]
    parts.extend(extras)
    parts.append(r"(?P<decorator>@\w+|\#[A-Za-z_]\w*)")
    parts.append(r"(?P<keyword>" + kw + r")")
    parts.append(r"(?P<number>\b\d+(?:\.\d+)?\b)")
    return re.compile("|".join(parts), re.X | re.S)


def _generic_rule(comment, kw, extras=(), deco=r"@[A-Za-z_]\w*"):
    """#-comment family (shell, ruby, python-ish shapes)."""
    parts = [r"(?P<comment>%s)" % comment,
             r"(?P<string>\"(?:[^\"\\]|\\.)*\"|'[^'\n]*')"]
    parts.extend(extras)
    if deco:
        parts.append(r"(?P<decorator>%s)" % deco)
    parts.append(r"(?P<keyword>" + kw + r")")
    parts.append(r"(?P<number>\b\d+(?:\.\d+)?\b)")
    return re.compile("|".join(parts), re.X | re.S)


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
    ".go": _c_rule(_GO_KW, (r"(?P<builtin>" + _GO_BUILTIN + r")",)),
    ".rs": _c_rule(_RS_KW, (r"(?P<builtin>\b[a-z_]\w*!)",
                            r"(?P<self>\b[a-z_]\w*!\s*\[)")),
    ".java": _c_rule(_JAVA_KW),
    ".c": _c_rule(_JAVA_KW),
    ".cpp": _c_rule(_JAVA_KW, (r"(?P<self>\bstd::\w+)",)),
    ".cs": _c_rule(_CS_KW),
    ".kt": _c_rule(_KT_KW),
    ".php": _c_rule(_PHP_KW),
    ".rb": _generic_rule("#[^\n]*", _RB_KW,
                         (r"(?P<tag>:[a-zA-Z_]\w*)",
                          r"(?P<self>@[A-Za-z_]\w*)")),
    ".sh": _generic_rule("#[^\n]*", _SH_KW,
                         (r"(?P<decorator>\$\{?[A-Za-z_]\w*\}?)",),
                         deco=None),
}

EXT_ALIAS = {".pyw": ".py", ".pyi": ".py", ".htm": ".html", ".xml": ".html",
             ".jsx": ".js", ".ts": ".js", ".tsx": ".js", ".markdown": ".md",
             ".cc": ".cpp", ".cxx": ".cpp", ".hpp": ".cpp", ".hh": ".cpp",
             ".h": ".c", ".hpp": ".cpp", ".bash": ".sh",
             ".zsh": ".sh", ".ksh": ".sh", ".kts": ".kt", ".scala": ".kt",
             ".php3": ".php", ".php4": ".php", ".php5": ".php",
             ".phtml": ".php", ".rake": ".rb", ".gemspec": ".rb",
             ".erb": ".rb", ".bashrc": ".sh", ".profile": ".sh"}


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

    def __init__(self, parent, theme, on_file_select=None, start_dir=None,
                 on_context=None):
        super().__init__(parent, bg=theme["sidebar"])
        self.theme = theme
        self.on_file_select = on_file_select
        self.on_context = on_context
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
        # DS2 UI-sprint: horizontal scrollbar for long filenames —
        # at narrow widths names clipped with no way to reach them.
        self.xscroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL,
                                     command=self.canvas.xview)
        self.tree_frame = tk.Frame(self.canvas, bg=theme["sidebar"])

        self.tree_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._win = self.canvas.create_window((0, 0), window=self.tree_frame,
                                              anchor="nw", width=230)
        self.canvas.configure(yscrollcommand=self.scrollbar.set,
                              xscrollcommand=self.xscroll.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_wheel())

        self.load_directory(self.current_dir)

    def _on_canvas_resize(self, event):
        """Inner window follows the canvas width but NEVER squishes the
        rows — overflow goes to the horizontal scrollbar instead."""
        need = max(event.width, self.tree_frame.winfo_reqwidth())
        self.canvas.itemconfigure(self._win, width=need)
        if need > event.width + 2:
            if not self.xscroll.winfo_ismapped():
                self.xscroll.pack(side=tk.BOTTOM, fill=tk.X,
                                  before=self.canvas)
        else:
            if self.xscroll.winfo_ismapped():
                self.xscroll.pack_forget()

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

    def _popup_context(self, path, is_dir, event):
        if self.on_context:
            try:
                self.on_context(path, is_dir, event.x_root, event.y_root)
            except Exception:
                pass
        return "break"

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
                label.bind("<Button-3>",
                           lambda e, p=full: self._popup_context(p, True, e))
            else:
                row, label = self._row(container, depth)
                label.config(text=f"   {entry}")
                if self.on_file_select:
                    label.bind(
                        "<Button-1>",
                        lambda e, p=full: self.on_file_select(p))
                label.bind("<Button-3>",
                           lambda e, p=full: self._popup_context(p, False, e))

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
        # DS2 UI-sprint: the editor finally has a vertical scrollbar —
        # wheel-only scrolling hid the position and broke long files.
        self.yscroll = tk.Scrollbar(body, orient=tk.VERTICAL,
                                    command=self.text.yview,
                                    width=10, troughcolor=theme["editor"],
                                    bg=theme["card"], activebackground=
                                    theme.accent)
        self.xscroll = tk.Scrollbar(body, orient=tk.HORIZONTAL,
                                    command=self.text.xview,
                                    width=10, troughcolor=theme["editor"],
                                    bg=theme["card"], activebackground=
                                    theme.accent)
        self.text.configure(yscrollcommand=self.yscroll.set,
                            xscrollcommand=self.xscroll.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # find / decoration tags
        self.text.tag_configure("find_all",
                                background=self.theme["hover"])
        self.text.tag_configure("find_cur",
                                background=self.theme.accent,
                                foreground="#ffffff")
        self.text.tag_configure("cur_line", background=self.theme["hover"])
        self.text.tag_configure("bracket",
                                background=self.theme["hover"],
                                foreground=self.theme.accent)
        self.text.tag_configure("word_hl",
                                background=self.theme["hover"])

        self.highlighter = Highlighter(self.text, theme)
        self._word_job = None

        # typing helpers (flipped from Settings / app config)
        self.auto_indent = True
        self.auto_close = True

        self.text.bind("<KeyRelease>", self._on_key)
        self.text.bind("<ButtonRelease-1>", self._on_cursor)
        self.text.bind("<MouseWheel>", self.update_line_numbers)
        self.text.bind("<Return>", self._on_return)
        self.text.bind("<Key>", self._on_typing)
        self.text.bind("<Tab>", self._on_tab)
        self.text.bind("<Shift-Tab>", self._on_outdent)
        self.text.bind("<ISO_Left_Tab>", self._on_outdent)
        self.text.bind("<Control-bracketright>",
                       lambda e: self._indent_selection())
        self.text.bind("<Control-bracketleft>", self._on_outdent)

        # bookmarks: line numbers kept in-session, shown in the gutter
        self.bookmarks = set()
        self.line_numbers.tag_configure("cur", foreground=theme.accent,
                                        font=(FONT_MONO, 11, "bold"))
        self.line_numbers.tag_configure("bm", foreground=theme.accent)
        self.line_numbers.bind("<Button-1>", self._gutter_click)
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
        self._decorate_cursor()
        self._schedule_word_hl()

    def _on_cursor(self, event=None):
        self.update_line_numbers()
        self._decorate_cursor()
        self._schedule_word_hl()

    # ---------------------------------------------------- cursor decoration
    def _decorate_cursor(self):
        """Current-line wash + matching-bracket spotlight."""
        t = self.text
        try:
            t.tag_remove("cur_line", "1.0", "end")
            t.tag_remove("bracket", "1.0", "end")
            t.tag_add("cur_line", "insert linestart", "insert lineend+1c")
            pair = self._matching_bracket()
            if pair:
                t.tag_add("bracket", pair[0], pair[1])
        except tk.TclError:
            pass

    _PAIRS = {"(": ")", "[": "]", "{": "}",
              ")": "(", "]": "[", "}": "{"}

    # ------------------------------------------------ Editor Pro (v1.1.5)
    def _schedule_word_hl(self, delay=420):
        """Debounced highlight of the word under the cursor."""
        if self._word_job is not None:
            try:
                self.text.after_cancel(self._word_job)
            except Exception:
                pass
        self._word_job = self.text.after(delay, self._word_hl)

    def _word_hl(self):
        self._word_job = None
        t = self.text
        try:
            t.tag_remove("word_hl", "1.0", "end")
            if t.tag_ranges("sel") or t.tag_ranges("find_all"):
                return                     # selection / active find wins
            word = self._word_under_cursor()
            if not word or len(word) < 3:
                return
            content = t.get("1.0", "end-1c")
            if len(content) > 200_000:
                return
            rx = re.compile(r"\b" + re.escape(word) + r"\b")
            hits = list(rx.finditer(content))
            if len(hits) > 200:
                return
            for m in hits:
                t.tag_add("word_hl", f"1.0+{m.start()}c",
                          f"1.0+{m.end()}c")
        except tk.TclError:
            pass

    def _word_under_cursor(self):
        t = self.text
        try:
            line, col = t.index("insert").split(".")
            line_text = t.get(f"{line}.0", f"{line}.end")
            col = int(col)
            if col >= len(line_text) or not (
                    line_text[col].isalnum() or line_text[col] == "_"):
                if col == 0 or not (line_text[col - 1].isalnum()
                                    or line_text[col - 1] == "_"):
                    return ""
                col -= 1
            start = end = col
            while start > 0 and (line_text[start - 1].isalnum()
                                 or line_text[start - 1] == "_"):
                start -= 1
            while end < len(line_text) - 1 and (
                    line_text[end + 1].isalnum()
                    or line_text[end + 1] == "_"):
                end += 1
            return line_text[start:end + 1]
        except tk.TclError:
            return ""

    def _sel_lines(self):
        """First/last line of the selection (or just the cursor line)."""
        t = self.text
        rng = t.tag_ranges("sel")
        if rng:
            first = int(str(rng[0]).split(".")[0])
            last = int(str(rng[1]).split(".")[0])
            # a selection that ends at column 0 doesn't own that line
            if str(rng[1]).split(".")[1] == "0" and last > first:
                last -= 1
        else:
            first = last = int(t.index("insert").split(".")[0])
        return first, last

    def _indent_selection(self, event=None):
        """Tab / Ctrl+] with a selection — shift every line right."""
        t = self.text
        try:
            first, last = self._sel_lines()
            t.configure(autoseparators=False)
            t.edit_separator()
            for i in range(first, last + 1):
                if t.get(f"{i}.0", f"{i}.end").strip():
                    t.insert(f"{i}.0", "    ")
            t.edit_separator()
            t.configure(autoseparators=True)
            t.tag_remove("sel", "1.0", "end")
            t.tag_add("sel", f"{first}.0", f"{last}.end")
            self._on_key()
        except tk.TclError:
            pass
        return "break"

    def _on_outdent(self, event=None):
        """Shift+Tab / Ctrl+[ — shift the selected lines left."""
        t = self.text
        try:
            first, last = self._sel_lines()
            t.configure(autoseparators=False)
            t.edit_separator()
            for i in range(first, last + 1):
                ln = t.get(f"{i}.0", f"{i}.end")
                strip = len(ln) - len(ln.lstrip(" "))
                if strip == 0 and ln.startswith("\t"):
                    strip = 1
                if strip:
                    t.delete(f"{i}.0", f"{i}.{min(4, strip)}")
            t.edit_separator()
            t.configure(autoseparators=True)
            t.tag_remove("sel", "1.0", "end")
            t.tag_add("sel", f"{first}.0", f"{last}.end")
            self._on_key()
        except tk.TclError:
            pass
        return "break"

    # Tab-expandable typing helpers (per language, stdlib-first)
    SNIPPETS = {
        ".py": {"ifmain": 'if __name__ == "__main__":\n    main()',
                 "pdb": "import pdb; pdb.set_trace()",
                 "smain": "def main():\n    pass"},
    }


    def _matching_bracket(self):
        """Index pair for the bracket at/next to the cursor, else None."""
        t = self.text
        try:
            insert = t.index("insert")
            content = t.get("1.0", "end-1c")
            if len(content) > 200_000:
                return None
            abs_off = len(t.get("1.0", insert))
            for probe in (abs_off - 1, abs_off):
                if probe < 0 or probe >= len(content):
                    continue
                ch = content[probe]
                closer = self._PAIRS.get(ch)
                if not closer:
                    continue
                going_forward = ch in "([{"
                depth = 0
                rng = range(probe, len(content)) if going_forward \
                    else range(probe, -1, -1)
                for i in rng:
                    c = content[i]
                    if c == ch:
                        depth += 1
                    elif c == closer:
                        depth -= 1
                        if depth == 0:
                            i0, i1 = sorted((probe, i))
                            return (f"1.0+{i0}c", f"1.0+{i1 + 1}c")
                break
        except tk.TclError:
            return None
        return None

    # ------------------------------------------------------- typing helpers
    def _on_return(self, event=None):
        """Auto-indent Enter — keeps the leading whitespace, one level
        deeper after ':' , and opens a cuddled block inside pairs."""
        if not self.auto_indent or self.text.tag_ranges("sel"):
            return None                      # default behaviour
        t = self.text
        try:
            line = t.get("insert linestart", "insert lineend")
            col = int(t.index("insert").split(".")[1])
            before, after = line[:col], line[col:]
        except tk.TclError:
            return None
        indent = before[: len(before) - len(before.lstrip())]
        stripped = before.strip()
        next_char = (after.lstrip()[:1] or "")
        insert_text = "\n" + indent
        if stripped.endswith((":", "(", "[", "{")):
            insert_text += "    "
        if stripped.endswith(("{", "(", "[")) and \
                next_char in ("}", ")", "]"):
            # cuddled block: cursor lands on the empty middle line
            t.insert("insert", insert_text + "\n" + indent)
            t.mark_set("insert", f"insert -{len(indent) + 1}c")
            t.see("insert")
            self._on_key()
            return "break"
        t.insert("insert", insert_text)
        t.see("insert")
        self._on_key()
        return "break"

    _CLOSERS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}

    def _on_typing(self, event=None):
        """Auto-close brackets/quotes + type-over — VSCode muscle memory."""
        if not self.auto_close or event is None or event.char == "":
            return None
        ch = event.char
        if ch not in self._CLOSERS and ch not in ")]}":
            return None
        if event.state & 0x0004 or event.state & 0x0001:   # ctrl / alt
            return None
        t = self.text
        try:
            sel = t.tag_ranges("sel")
            nxt = t.get("insert") or ""
            prev = t.get("insert -1c") or ""
            if ch in self._CLOSERS:
                closer = self._CLOSERS[ch]
                if sel:
                    t.insert(sel[1], closer)
                    t.insert(sel[0], ch)
                    t.tag_add("sel", f"{sel[0]} +1c", f"{sel[1]} +1c")
                    self._on_key()
                    return "break"
                if ch in "\"'" and (prev.isalnum() or prev in "\"'"):
                    return None                # plain apostrophe, don't pair
                if ch in "\"'" and nxt.isalnum():
                    return None
                t.insert("insert", ch + closer)
                t.mark_set("insert", "insert -1c")
                self._on_key()
                return "break"
            # type-over: typing a closer that's already next to the cursor
            if ch in ")]}" and nxt == ch:
                t.mark_set("insert", "insert +1c")
                self._on_key()
                return "break"
        except tk.TclError:
            return None
        return None

    # ----------------------------------------------------------- line ops
    def toggle_comment(self):
        """Ctrl+/ — comment/uncomment the selected (or current) lines."""
        prefixes = {".py": "#", ".pyw": "#", ".pyi": "#",
                    ".js": "//", ".ts": "//", ".jsx": "//", ".tsx": "//",
                    ".css": "/*", ".json": "#", ".yml": "#", ".yaml": "#",
                    ".sh": "#", ".toml": "#", ".rs": "//", ".c": "//",
                    ".h": "//", ".cpp": "//", ".java": "//", ".go": "//"}
        ext = os.path.splitext(self.file_path or "")[1].lower() or ".py"
        if ext == ".html" or ext == ".xml":
            open_p, close_p = "<!-- ", " -->"
        else:
            open_p, close_p = prefixes.get(ext, "#"), ""
        t = self.text
        try:
            rng = t.tag_ranges("sel")
            if rng:
                first = int(str(rng[0]).split(".")[0])
                last = int(str(rng[1]).split(".")[0])
            else:
                first = last = int(t.index("insert").split(".")[0])
        except tk.TclError:
            return
        lines = [t.get(f"{i}.0", f"{i}.end") for i in range(first, last + 1)]
        non_empty = [ln for ln in lines if ln.strip()]
        if not non_empty:
            return
        if close_p:
            commented = all(ln.lstrip().startswith(open_p.strip())
                            for ln in non_empty)
        else:
            commented = all(
                ln.lstrip().startswith(open_p) for ln in non_empty)
        for i in range(first, last + 1):
            ln = t.get(f"{i}.0", f"{i}.end")
            if commented:
                if close_p:
                    ln = ln.replace(open_p.strip(), "", 1)
                    ln = ln.replace(close_p.strip(), "", 1)
                else:
                    ln = ln.replace(open_p, "", 1)
                t.delete(f"{i}.0", f"{i}.end")
                t.insert(f"{i}.0", ln)
            else:
                if not ln.strip():
                    continue
                stripped = len(ln) - len(ln.lstrip())
                if close_p:
                    t.insert(f"{i}.{len(ln)}", " " + close_p)
                    t.insert(f"{i}.{stripped}", open_p)
                else:
                    t.insert(f"{i}.{stripped}", open_p)
        t.tag_add("sel", f"{first}.0", f"{last}.end")
        self._on_key()

    def duplicate_line(self):
        """Ctrl+Shift+D — clone the current line below."""
        t = self.text
        try:
            ln = t.get("insert linestart", "insert lineend")
            t.insert("insert lineend", "\n" + ln)
            t.mark_set("insert", "insert +1l linestart")
            t.see("insert")
            self._on_key()
        except tk.TclError:
            pass

    def delete_line(self):
        """Ctrl+Shift+K — remove the current line."""
        t = self.text
        try:
            if t.compare("end-1c", "==", "1.0"):
                t.delete("1.0", "end")
            elif t.compare("insert lineend", ">=", "end-1c"):
                t.delete("insert linestart-1c", "end")
            else:
                t.delete("insert linestart", "insert lineend+1c")
            t.see("insert")
            self._on_key()
        except tk.TclError:
            pass

    def move_line(self, delta):
        """Alt+Up / Alt+Down — shuffle the current line (or selection)."""
        t = self.text
        try:
            rng = t.tag_ranges("sel")
            if rng:
                first = int(str(rng[0]).split(".")[0])
                last = int(str(rng[1]).split(".")[0])
            else:
                first = last = int(t.index("insert").split(".")[0])
            target = first + delta
            if target < 1 or target > int(t.index("end-1c").split(".")[0]):
                return
            block = t.get(f"{first}.0", f"{last}.end")
            if delta < 0:
                anchor = t.get(f"{target}.0", f"{target}.end")
                t.delete(f"{target}.0", f"{target}.end")
                t.insert(f"{target}.0", block + "\n")
                t.insert(f"{last + 1}.0", anchor)
                t.delete(f"{last + 1}.0", f"{last + 1}.end")
            else:
                anchor = t.get(f"{target}.0", f"{target}.end")
                t.delete(f"{target}.0", f"{target + 1}.0")
                t.insert(f"{last}.0", anchor + "\n")
                t.insert(f"{last + 1}.0", block)
            t.tag_remove("sel", "1.0", "end")
            t.tag_add("sel", f"{first + delta}.0",
                      f"{last + delta}.end")
            t.mark_set("insert", f"{first + delta}.0")
            t.see("insert")
            self._on_key()
        except tk.TclError:
            pass

    def _selected_or_current_block(self):
        """(first, last) 1-based line numbers of the selection, or the
        current line when nothing is selected."""
        t = self.text
        rng = t.tag_ranges("sel")
        if rng:
            first = int(str(rng[0]).split(".")[0])
            last = int(str(rng[1]).split(".")[0])
        else:
            first = last = int(t.index("insert").split(".")[0])
        return first, last

    def sort_lines(self, reverse=False, numeric=False):
        """Sort the selected block (or current line). Case-insensitive
        by default; ``numeric`` compares leading numbers so '2' beats
        '10'. Returns the number of lines touched (0 on failure)."""
        t = self.text
        try:
            first, last = self._selected_or_current_block()
            block = t.get(f"{first}.0", f"{last}.end")
            lines = block.split("\n")
            if numeric:
                import re as _re
                key_fn = lambda ln: (  # noqa: E731
                    float(_re.match(r"\s*(-?\d+(?:\.\d+)?)", ln).group(1))
                    if _re.match(r"\s*-?\d+(?:\.\d+)?", ln) else float("inf"),
                    ln.lower())
                lines.sort(key=key_fn, reverse=reverse)
            else:
                lines.sort(key=lambda ln: ln.lower(), reverse=reverse)
            t.delete(f"{first}.0", f"{last}.end")
            t.insert(f"{first}.0", "\n".join(lines))
            t.tag_remove("sel", "1.0", "end")
            t.tag_add("sel", f"{first}.0", f"{last}.end")
            t.mark_set("insert", f"{first}.0")
            t.see("insert")
            self._on_key()
            return len(lines)
        except tk.TclError:
            return 0

    def unique_lines(self):
        """Drop duplicate lines in the selection (keeps first seen,
        case-sensitive). Returns how many duplicates were removed."""
        t = self.text
        try:
            first, last = self._selected_or_current_block()
            block = t.get(f"{first}.0", f"{last}.end")
            lines = block.split("\n")
            seen, out = set(), []
            for ln in lines:
                if ln in seen:
                    continue
                seen.add(ln)
                out.append(ln)
            removed = len(lines) - len(out)
            if removed:
                t.delete(f"{first}.0", f"{last}.end")
                t.insert(f"{first}.0", "\n".join(out))
                t.tag_remove("sel", "1.0", "end")
                t.tag_add("sel", f"{first}.0",
                          f"{first + len(out) - 1}.end")
                t.mark_set("insert", f"{first}.0")
                t.see("insert")
                self._on_key()
            return removed
        except tk.TclError:
            return 0

    def goto_line(self, number):
        """Jump to a 1-based line, clamped. Returns True on success."""
        t = self.text
        try:
            total = int(t.index("end-1c").split(".")[0])
            line = max(1, min(int(number), total))
            t.mark_set("insert", f"{line}.0")
            t.see("insert")
            self._decorate_cursor()
            self.update_line_numbers()
            t.focus_set()
            return True
        except (tk.TclError, ValueError):
            return False

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
        g = self.line_numbers
        g.config(state="normal")
        g.delete("1.0", tk.END)
        for i in range(1, lines + 1):
            g.insert(tk.END, f"{i}\n")
        g.config(state="disabled")
        # current line: bold accent number; bookmarks: accent numbers
        g.tag_remove("cur", "1.0", "end")
        g.tag_remove("bm", "1.0", "end")
        try:
            if 1 <= int(current) <= lines:
                g.tag_add("cur", f"{current}.0", f"{current}.end")
            for ln in self.bookmarks:
                if 1 <= ln <= lines:
                    g.tag_add("bm", f"{ln}.0", f"{ln}.end")
        except tk.TclError:
            pass

    def _gutter_click(self, event=None):
        """Click a line number to bookmark / unbookmark it."""
        if event is None:
            return
        try:
            idx = self.line_numbers.index(f"@{event.x},{event.y}")
            ln = int(str(idx).split(".")[0])
        except (tk.TclError, ValueError):
            return
        self.toggle_bookmark(ln)

    # ------------------------------------------------------------ bookmarks
    def toggle_bookmark(self, line=None):
        """Bookmark the given (or current) line; returns True if added."""
        t = self.text
        if line is None:
            line = int(t.index("insert").split(".")[0])
        line = max(1, int(line))
        if line in self.bookmarks:
            self.bookmarks.discard(line)
            added = False
        else:
            self.bookmarks.add(line)
            added = True
        self.update_line_numbers()
        return added

    def _jump_bookmark(self, lines):
        if not lines:
            return False
        cur = int(self.text.index("insert").split(".")[0])
        target = min(lines, key=lambda ln: (abs(ln - cur), -ln))
        return self.goto_line(target)

    def next_bookmark(self):
        below = sorted(ln for ln in self.bookmarks
                       if ln > int(self.text.index("insert").split(".")[0]))
        wrapped = sorted(self.bookmarks)
        return self._jump_bookmark(below or wrapped)

    def prev_bookmark(self):
        above = sorted((ln for ln in self.bookmarks
                        if ln < int(self.text.index("insert").split(".")[0])),
                       reverse=True)
        wrapped = sorted(self.bookmarks, reverse=True)
        return self._jump_bookmark(above or wrapped)

    # -------------------------------------------------------------- snippets
    def _on_tab(self, event=None):
        """Tab expands a snippet when the word before the cursor matches;
        otherwise a plain indent is inserted (never moves focus)."""
        if self.text.tag_ranges("sel"):
            return self._indent_selection()   # Editor Pro: block indent
        t = self.text
        try:
            word = t.get("insert linestart", "insert")
        except tk.TclError:
            return None
        table = self.SNIPPETS.get(os.path.splitext(
            self.file_path or "")[1].lower(), self.SNIPPETS[".py"])
        expansion = table.get(word.strip())
        if not word.strip() or expansion is None:
            t.insert("insert", "    ")
            self._on_key()
            return "break"
        t.delete("insert -%dc" % len(word.strip()), "insert")
        t.insert("insert", expansion)
        self._on_key()
        return "break"

    def set_content(self, content, path=None):
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.modified = False
        if path is not None:
            self.file_path = path
        self.bookmarks.clear()
        self.update_line_numbers()
        self.highlighter.set_language(self.file_path)

    def symbols(self):
        """Regex outline of the file: [(line, kind, name)] for the palette."""
        import re as _re
        ext = os.path.splitext(self.file_path or "")[1].lower()
        rules = {
            ".py": _re.compile(
                r"^(?:\s*)(def|class)\s+([A-Za-z_]\w*)"),
            ".js": _re.compile(
                r"^(?:\s*)(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)"
                r"\s*=\s*(?:async\s*)?(?:function|\()|class\s+(\w+))"),
        }
        rules.update({e: rules[".js"] for e in
                      (".jsx", ".ts", ".tsx", ".mjs")})
        # C-family + friends: functions and classes share one pattern —
        # a name followed by ( ... ) up to an optional brace, or
        # struct/impl/trait/enum/interface declarations. Keyword guard
        # keeps control flow (while/for/switch…) out of the outline.
        c_like = _re.compile(
            r"^(?:\s*)(?:(?:public|private|protected|static|final|abstract|"
            r"virtual|override|async|pub|unsafe|extern|inline|const)\s+)*"
            r"(?:struct|impl|trait|enum|interface|class)\s+([A-Za-z_]\w*)"
            r"|(?:\s*)(?:[A-Za-z_][\w:<>,\s\*&]*?\s+)?"
            r"(?!while\b|for\b|switch\b|if\b|else\b|return\b|sizeof\b|"
            r"match\b|use\b|new\b|catch\b|do\b)"
            r"([A-Za-z_]\w*)\s*\([^;{)]*\)\s*(?:[^;{]*\{)?\}?\s*$")
        for e in (".c", ".h", ".cpp", ".hpp", ".java", ".kt", ".rs",
                  ".go", ".cs", ".swift", ".dart", ".php"):
            rules[e] = c_like
        rule = rules.get(ext)
        if rule is None:
            # generic fallback: markdown headings only
            if ext == ".md":
                md = _re.compile(r"^(#{1,3})\s+(.{1,60})")
                out = []
                for i, line in enumerate(
                        self.text.get("1.0", "end-1c").splitlines(), 1):
                    m = md.match(line)
                    if m:
                        out.append((i, "h" * len(m.group(1)),
                                    m.group(2).strip()))
                return out
            return []
        out = []
        for i, line in enumerate(
                self.text.get("1.0", "end-1c").splitlines(), 1):
            m = rule.match(line)
            if m:
                if ext == ".py":
                    out.append((i, m.group(1), m.group(2)))
                else:
                    stripped = line.lstrip()
                    is_type = _re.match(
                        r"^(?:\s*)(?:(?:public|private|protected|static|"
                        r"final|abstract|virtual|override|async|pub|unsafe|"
                        r"extern|inline|const)\s+)*"
                        r"(?:struct|impl|trait|enum|interface|class)\b",
                        line)
                    kind = "class" if (is_type or
                                       stripped.startswith("class")) \
                        else "function"
                    name = next((g for g in m.groups() if g), "")
                    if name and not name[0].isdigit():
                        out.append((i, kind, name))
        return out[:200]

    def get_content(self):
        return self.text.get("1.0", tk.END)

    # --------------------------------------------------------------- find
    def find(self, needle, backwards=False, regex=False):
        """Highlight all matches; move selection to next/prev. Returns
        match count, -1 for a bad regex (0 when needle is empty)."""
        self.clear_find()
        self.text.tag_remove("word_hl", "1.0", "end")
        if not needle:
            return 0
        content = self.text.get("1.0", "end-1c")
        if regex:
            try:
                rx = re.compile(needle)
            except re.error:
                return -1
            spans = [(m.start(), m.end()) for m in rx.finditer(content)
                     if m.end() > m.start()]
            count = len(spans)
            if not count:
                return 0
            for start, end in spans:
                self.text.tag_add("find_all", f"1.0+{start}c",
                                  f"1.0+{end}c")
        else:
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

    # ------------------------------------------------------------- replace
    def replace_current(self, needle, repl, regex=False):
        """Replace the currently highlighted find_cur match. Returns
        True when a match was replaced."""
        if not needle:
            return False
        try:
            rng = self.text.tag_prevrange("find_cur", "end")
        except tk.TclError:
            rng = None
        if not rng:
            return False
        newtext = repl
        if regex:
            try:
                m = re.compile(needle).search(self.text.get(rng[0], rng[1]))
            except re.error:
                return False
            if m:
                newtext = m.expand(repl)
        self.text.tag_remove("find_cur", "1.0", "end")
        self.text.delete(rng[0], rng[1])
        self.text.insert(rng[0], newtext)
        self.text.mark_set("insert", f"{rng[0]}+{len(newtext)}c")
        self.text.see(rng[0])
        self.modified = True
        return True

    def replace_all(self, needle, repl, regex=False):
        """Replace every occurrence of needle (literal or regex — regex
        replacements expand \\1 templates). One undoable edit. Returns
        the replacement count, -1 for a bad regex."""
        if not needle:
            return 0
        content = self.text.get("1.0", "end-1c")
        if regex:
            try:
                rx = re.compile(needle)
            except re.error:
                return -1
            spans = [(m.start(), m.end(), m.expand(repl))
                     for m in rx.finditer(content)
                     if m.end() > m.start()]
            if not spans:
                return 0
            self.text.configure(autoseparators=False)
            try:
                self.text.edit_separator()
                for start, end, newtext in reversed(spans):
                    s, e = f"1.0+{start}c", f"1.0+{end}c"
                    self.text.delete(s, e)
                    self.text.insert(s, newtext)
                self.text.edit_separator()
            finally:
                self.text.configure(autoseparators=True)
            self.modified = True
            self.update_line_numbers()
            self.highlighter.schedule(delay=0)
            return len(spans)
        count = content.count(needle)
        if not count:
            return 0
        # one undo step for the whole pass: bracket the group with
        # explicit separators (autoseparators only fire *before* each
        # mod while enabled — without a leading separator the undo
        # would swallow whatever edit happened before this call)
        self.text.configure(autoseparators=False)
        try:
            self.text.edit_separator()
            pos = 0
            while True:
                idx = content.find(needle, pos)
                if idx < 0:
                    break
                start = f"1.0+{idx}c"
                end = f"1.0+{idx + len(needle)}c"
                self.text.delete(start, end)
                self.text.insert(start, repl)
                # recompute offsets after every edit — lengths shift
                after = self.text.index(f"{start}+{len(repl)}c")
                pos = self._offset_of(after)
                content = self.text.get("1.0", "end-1c")
            self.text.edit_separator()
        finally:
            self.text.configure(autoseparators=True)
        self.modified = True
        self.update_line_numbers()
        self.highlighter.schedule(delay=0)
        return count

    def _offset_of(self, index):
        """Tk index -> character offset from start of text."""
        line, col = index.split(".")
        line = int(line)
        if line == 1:
            return int(col)
        return len(self.text.get("1.0", f"{line - 1}.end")) + \
            int(col) + (line - 1)


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
        # DS2 UI-sprint: the terminal gets a real vertical scrollbar —
        # long output was wheel-only and lost past the fold.
        self.yscroll = tk.Scrollbar(self, orient=tk.VERTICAL,
                                    command=self.output.yview,
                                    width=10, troughcolor=theme["terminal"],
                                    bg=theme["card"], activebackground=
                                    theme.accent)
        self.output.configure(yscrollcommand=self.yscroll.set)
        self.output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.yscroll.pack(side=tk.RIGHT, fill=tk.Y)

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
        # strip ANSI escapes + resolve carriage returns (progress bars)
        if "\x1b" in text or "\r" in text:
            text = _ANSI_RE.sub("", text).replace("\r\n", "\n") \
                .replace("\r", "\n")
        self.output.config(state="normal")
        self.output.insert(tk.END, text)
        # keep the log bounded — drop the oldest half past 6k lines
        try:
            if int(self.output.index("end-1c").split(".")[0]) > 6000:
                self.output.delete("1.0", "3000.0")
        except tk.TclError:
            pass
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
