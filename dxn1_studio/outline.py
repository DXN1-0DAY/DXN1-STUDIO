"""DXN1 STUDIO — Symbol Outline.

`Go to symbol in file` — parses the active file with ``ast`` (Python)
or a regex fallback (JS/TS, Go, Rust) and offers a fuzzy-pickable list
of functions, classes, methods, structs and section headers. Choosing
one scrolls the editor to the definition and flashes it.

Engine is UI-free:

* :func:`symbols_for(text, path)` → ``[{line, kind, name, indent}]``
* :func:`filter_symbols(syms, query)` → scored, ordered matches

The picker (``SymbolPicker``) reuses the studio's dark-window look and
supports arrow keys, Enter and type-ahead.
"""

from __future__ import annotations

import ast
import os
import re

# ------------------------------------------------------------------ engine
_KIND_GLYPH = {
    "class": "◇", "function": "ƒ", "method": "·", "async": "ƒ",
    "struct": "◇", "interface": "◇", "impl": "◇", "fn": "ƒ",
    "func": "ƒ", "type": "◇", "heading": "≡", "component": "◆",
}

_PY_RE = re.compile(r"\.pyi?$", re.I)
_JS_RE = re.compile(r"\.(js|jsx|ts|tsx|mjs|cjs|svelte)$", re.I)
_GO_RE = re.compile(r"\.go$", re.I)
_RS_RE = re.compile(r"\.rs$", re.I)
_MD_RE = re.compile(r"\.(md|markdown|rst)$", re.I)


def symbols_for(text, path=""):
    """Extract top-level structure. Never raises — worst case [])."""
    if not text:
        return []
    try:
        if _PY_RE.search(path or "") or not path:
            syms = _python_symbols(text)
            if syms or _PY_RE.search(path or ""):
                return syms
        if _JS_RE.search(path or ""):
            return _js_symbols(text)
        if _GO_RE.search(path or ""):
            return _go_symbols(text)
        if _RS_RE.search(path or ""):
            return _rust_symbols(text)
        if _MD_RE.search(path or ""):
            return _md_symbols(text)
        return _python_symbols(text) or []
    except Exception:  # noqa: BLE001 — outline must never break the editor
        return []


def _python_symbols(text):
    out = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def visit(node, indent=0):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "async" if isinstance(child, ast.AsyncFunctionDef) \
                    else ("method" if indent else "function")
                out.append({"line": child.lineno, "kind": kind,
                            "name": child.name, "indent": indent})
                visit(child, indent + 1)
            elif isinstance(child, ast.ClassDef):
                out.append({"line": child.lineno, "kind": "class",
                            "name": child.name, "indent": indent})
                visit(child, indent + 1)

    visit(tree)
    return out


def _js_symbols(text):
    out = []
    pat = re.compile(
        r"^(?P<i>[ \t]*)(?:export\s+)?(?:default\s+)?"
        r"(?:async\s+)?function\s+(?P<n>[A-Za-z_$][\w$]*)"
        r"|^(?P<c>[ \t]*)(?:export\s+)?(?:abstract\s+)?class\s+"
        r"(?P<cn>[A-Za-z_$][\w$]*)"
        r"|^(?P<m>[ \t]*)const\s+(?P<mn>[A-Za-z_$][\w$]*)\s*=\s*"
        r"(?:async\s*)?\(", re.M)
    for m in pat.finditer(text):
        line = text[:m.start()].count("\n") + 1
        indent = len((m.group("i") or m.group("c") or m.group("m") or ""))
        name = m.group("n") or m.group("cn") or m.group("mn")
        kind = "class" if m.group("cn") else \
            ("function" if indent == 0 else "method")
        out.append({"line": line, "kind": kind, "name": name,
                    "indent": indent // 2})
    return out


def _go_symbols(text):
    out = []
    pat = re.compile(
        r"^(?:func\s+(?:\([^)]*\)\s*)?(?P<f>[A-Za-z_]\w*)"
        r"|type\s+(?P<t>[A-Za-z_]\w*)\s+(?:struct|interface))", re.M)
    for m in pat.finditer(text):
        line = text[:m.start()].count("\n") + 1
        if m.group("f"):
            out.append({"line": line, "kind": "func",
                        "name": m.group("f"), "indent": 0})
        else:
            out.append({"line": line, "kind": "type",
                        "name": m.group("t"), "indent": 0})
    return out


def _rust_symbols(text):
    out = []
    pat = re.compile(
        r"^(?P<i>[ \t]*)(?:pub(?:\([^)]*\))?\s+)?"
        r"(?:fn\s+(?P<f>[a-z_][\w]*)"
        r"|struct\s+(?P<s>[A-Z_][\w]*)"
        r"|trait\s+(?P<t>[A-Z_][\w]*)"
        r"|impl(?:<[^>]*>)?\s+(?P<i2>[A-Za-z_][\w:]*))", re.M)
    for m in pat.finditer(text):
        line = text[:m.start()].count("\n") + 1
        indent = len(m.group("i")) // 4
        name = m.group("f") or m.group("s") or m.group("t") or m.group("i2")
        kind = ("fn" if m.group("f") else
                "struct" if m.group("s") else
                "trait" if m.group("t") else "impl")
        out.append({"line": line, "kind": kind, "name": name,
                    "indent": indent})
    return out


def _md_symbols(text):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            out.append({"line": i, "kind": "heading",
                        "name": m.group(2).strip(),
                        "indent": len(m.group(1)) - 1})
    return out


def filter_symbols(syms, query, limit=200):
    """Substring/fuzzy ranking: prefix and word starts rank first."""
    if not query:
        return syms[:limit]
    q = query.lower()
    scored = []
    for s in syms:
        name = s["name"].lower()
        if q in name:
            score = 0
            if name.startswith(q):
                score -= 10
            if any(part.startswith(q) for part in
                   re.split(r"[_\-\s]", name)):
                score -= 6
            scored.append((score, s))
    scored.sort(key=lambda t: (t[0], t[1]["line"]))
    return [s for _, s in scored[:limit]]


def glyph(kind):
    return _KIND_GLYPH.get(kind, "·")


# --------------------------------------------------------------------- GUI
_OL_C = {"bg": "#0d1117", "input": "#11161d", "border": "#232c3d",
         "text": "#e6edf3", "secondary": "#9aa7b8", "muted": "#6e7a8a",
         "accent_row": "#1a212c"}


def open_outline(master, theme, get_text, on_jump, path="", on_log=None):
    """Open the symbol picker.

    ``get_text()`` returns the current buffer text; ``on_jump(line)``
    scrolls to the 1-based line. Both come from the host app.
    """
    return SymbolPicker(master, theme, get_text, on_jump, path,
                        on_log=on_log)


class SymbolPicker:
    """Type-ahead symbol list — arrow keys + Enter, Esc closes."""

    def __init__(self, master, theme, get_text, on_jump, path="",
                 on_log=None):
        import tkinter as tk

        self.tk = tk
        self.accent = getattr(theme, "accent", "#7c3aed")
        self.get_text = get_text
        self.on_jump = on_jump
        self.path = path
        self.on_log = on_log or (lambda m: None)
        self.selected = 0

        self.win = tk.Toplevel(master)
        self.win.title("Go to symbol")
        self.win.configure(bg=_OL_C["bg"])
        self.win.transient(master)
        self.win.resizable(False, False)
        self.win.bind("<Escape>", lambda e: self._close())

        self.entry = tk.Entry(self.win, bg=_OL_C["input"],
                              fg=_OL_C["text"],
                              insertbackground=_OL_C["text"],
                              relief=tk.FLAT, font=("sans-serif", 12),
                              highlightthickness=1,
                              highlightbackground=_OL_C["border"],
                              highlightcolor=self.accent)
        self.entry.pack(fill=tk.X, padx=14, pady=(14, 6), ipady=7)
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Down>", lambda e: self._move(1))
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Return>", lambda e: self._pick())
        self.entry.bind("<Escape>", lambda e: self._close())

        self.list_frame = tk.Frame(self.win, bg=_OL_C["bg"])
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 10))
        self.rows = []
        self.syms = []

        self._reload()
        # v2.48 — the honest door sign (arrows/Enter live on the entry)
        from . import hints
        hints.hint_bar(self.win,
                       {"header": _OL_C.get("card") or _OL_C["bg"],
                        "text_muted": _OL_C["muted"],
                        "accent": self.accent},
                       pairs=(("Up", "move", "\u2191\u2193"),
                              ("Return", "jump", "Enter")),
                       notes=("type to filter",),
                       before=self.list_frame)
        self.win.update_idletasks()
        w = 480
        h = min(560, max(220, self.win.winfo_reqheight()))
        try:
            x = self.win.master.winfo_rootx() + \
                (self.win.master.winfo_width() - w) // 2
            y = self.win.master.winfo_rooty() + 80
        except Exception:               # noqa: BLE001
            x = y = 60
        self.win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self.entry.focus_set()

    def _reload(self):
        try:
            text = self.get_text() or ""
        except Exception:               # noqa: BLE001
            text = ""
        self.all_syms = symbols_for(text, self.path)
        self.syms = self.all_syms
        self.selected = 0
        self._render()

    def _on_type(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        q = self.entry.get().strip()
        self.syms = filter_symbols(self.all_syms, q)
        self.selected = 0
        self._render()

    def _move(self, delta):
        if not self.syms:
            return
        self.selected = max(0, min(len(self.syms) - 1,
                                   self.selected + delta))
        self._render(highlight_only=True)

    def _pick(self):
        if 0 <= self.selected < len(self.syms):
            sym = self.syms[self.selected]
            self.on_log(f"outline: jump to {sym['name']} (line "
                        f"{sym['line']})")
            self.on_jump(sym["line"])
        self._close()

    def _close(self):
        try:
            self.win.destroy()
        except Exception:               # noqa: BLE001
            pass

    def _render(self, highlight_only=False):
        tk = self.tk
        if not highlight_only:
            for w in self.list_frame.winfo_children():
                w.destroy()
            self.rows = []
            if not self.all_syms:
                tk.Label(self.list_frame,
                         text="No symbols found in this file.",
                         bg=_OL_C["bg"], fg=_OL_C["muted"],
                         font=("sans-serif", 9)).pack(anchor="w", padx=8)
                return
            if not self.syms:
                tk.Label(self.list_frame,
                         text="Nothing matches — keep typing.",
                         bg=_OL_C["bg"], fg=_OL_C["muted"],
                         font=("sans-serif", 9)).pack(anchor="w", padx=8)
                return
            for i, sym in enumerate(self.syms[:120]):
                row = tk.Frame(self.list_frame, bg=_OL_C["bg"])
                row.pack(fill=tk.X, padx=4, pady=1)
                pad = "    " * sym.get("indent", 0)
                lbl = tk.Label(
                    row, text=f"{glyph(sym['kind'])}  {pad}{sym['name']}",
                    bg=_OL_C["bg"], fg=_OL_C["text"],
                    font=("monospace", 10), anchor="w")
                lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
                meta = tk.Label(row, text=f"{sym['kind']} · "
                                          f"L{sym['line']}",
                                bg=_OL_C["bg"], fg=_OL_C["muted"],
                                font=("sans-serif", 8))
                meta.pack(side=tk.RIGHT)
                for w in (row, lbl, meta):
                    w.bind("<Button-1>",
                           lambda e, idx=i: self._click(idx))
                self.rows.append(row)
        for i, row in enumerate(self.rows):
            active = i == self.selected
            row.configure(bg=self.accent if active else _OL_C["bg"])
            for child in row.winfo_children():
                try:
                    child.configure(
                        bg=self.accent if active else _OL_C["bg"],
                        fg="#ffffff" if active else
                        (_OL_C["text"] if i < len(self.syms)
                         else _OL_C["muted"]))
                except tk.TclError:
                    pass

    def _click(self, idx):
        self.selected = idx
        self._pick()
