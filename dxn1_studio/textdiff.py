"""DS2 Paste Diff — compare two pasted texts.

Select two texts, pick a granularity and see what changed: word
mode highlights reworded spans, char mode catches single-letter
edits, line mode gives classic ``- / +`` rows. The engine is a
thin, honest wrapper over stdlib ``difflib`` — pure, unit-tested,
junk-tolerant — and the window never raises on weird input.

Open with: Workshop menu, palette, terminal ``textdiff`` / ``diff2``.
"""

import difflib
import re
import tkinter as tk

from .i18n import tr

__all__ = ["diff_lines", "inline_diff", "similarity",
           "TextDiff", "open_textdiff"]

_WORD_RE = re.compile(r"\s+")


def _tokens(text, mode):
    if not isinstance(text, str):
        return []
    if mode == "char":
        return list(text)
    if mode == "word":
        return _WORD_RE.split(text.strip()) if text.strip() else []
    return text.splitlines()


def diff_lines(old, new):
    """Line diff: list of ``(kind, line)`` with kind in
    ``same / delete / insert / replace``. Junk → []."""
    if not isinstance(old, str) or not isinstance(new, str):
        return []
    out = []
    a = old.splitlines()
    b = new.splitlines()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for line in a[i1:i2]:
                out.append(("same", line))
        elif tag == "delete":
            for line in a[i1:i2]:
                out.append(("delete", line))
        elif tag == "insert":
            for line in b[j1:j2]:
                out.append(("insert", line))
        else:  # replace
            for line in a[i1:i2]:
                out.append(("delete", line))
            for line in b[j1:j2]:
                out.append(("insert", line))
    return out


def inline_diff(old, new, mode="word"):
    """One flattened paragraph where edits are marked.

    Unchanged text is plain, deletions are wrapped in ``[-…-]``
    and insertions in ``{+…+}`` (the standard rdiff convention,
    greppable and unambiguous). Junk → "".
    """
    a = _tokens(old, mode)
    b = _tokens(new, mode)
    if not isinstance(old, str) or not isinstance(new, str):
        return ""
    sep = "" if mode == "char" else " "
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    parts = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(sep.join(a[i1:i2]))
        elif tag == "delete":
            parts.append("[-%s-]" % sep.join(a[i1:i2]))
        elif tag == "insert":
            parts.append("{+%s+}" % sep.join(b[j1:j2]))
        else:
            parts.append("[-%s-]" % sep.join(a[i1:i2]))
            parts.append("{+%s+}" % sep.join(b[j1:j2]))
    text = sep.join(p for p in parts if p)
    return re.sub(r"\s+" if mode != "char" else r"\n{2,}", " "
                  if mode != "char" else "\n", text).strip()


def similarity(old, new):
    """Similarity as a 0-100 float. Junk inputs → 0.0."""
    if not isinstance(old, str) or not isinstance(new, str):
        return 0.0
    if not old.strip() and not new.strip():
        return 0.0
    return round(difflib.SequenceMatcher(
        None, old.splitlines(), new.splitlines(),
        autojunk=False).ratio() * 100.0, 1)


def summary(old, new):
    """Human counts: ``+N -M lines · P% similar``. Never raises."""
    try:
        kinds = [k for k, _l in diff_lines(old, new)]
        added = kinds.count("insert")
        removed = kinds.count("delete")
        return "+%d -%d lines · %.1f%% similar" % (
            added, removed, similarity(old, new))
    except Exception:  # noqa: BLE001 — status must never die
        return "stats unavailable"


# --------------------------------------------------------------- window

SAMPLE_OLD = "the quick brown fox jumps over the lazy dog"
SAMPLE_NEW = "the quick red fox leaps over the sleepy dog"


class TextDiff(tk.Toplevel):
    """Two-paste diff window. Never raises on junk input."""

    MODES = ("word", "char", "line")

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Paste Diff — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("760x500")
        self.minsize(600, 380)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="paste diff — what changed?",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=10, pady=8)
        self.mode = tk.StringVar(value="word")
        for m in self.MODES:
            tk.Radiobutton(top, text=m, value=m, variable=self.mode,
                           command=self.refresh,
                           bg=t.get("header", "#242432"),
                           fg=t.get("text", "#e8e8f0"),
                           selectcolor=t.get("editor_bg", "#1a1a24"),
                           activebackground=t.get("header", "#242432"),
                           activeforeground=t.get("text", "#e8e8f0"),
                           highlightthickness=0).pack(side=tk.LEFT,
                                                      padx=2)

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True)

        pair = tk.Frame(body, bg=t.get("bg", "#16161e"))
        pair.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        self.old_text = self._pane(pair, "old — paste the original",
                                   0)
        self.new_text = self._pane(pair, "new — paste the revised",
                                   1)
        self.old_text.insert("1.0", initial or SAMPLE_OLD)
        self.new_text.insert("1.0", initial or SAMPLE_NEW)
        for widget in (self.old_text, self.new_text):
            widget.bind("<KeyRelease>", lambda _e: self._schedule())

        tk.Label(body, text="diff — [-deletions-]  {+insertions+}",
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(
            anchor="w", padx=10)
        self.output = tk.Text(body, height=8, wrap="word",
                              bg=t.get("editor_bg", "#1a1a24"),
                              fg=t.get("text", "#e8e8f0"),
                              relief=tk.FLAT, padx=8, pady=6)
        self.output.pack(fill=tk.BOTH, expand=True,
                         padx=10, pady=(4, 0))
        self.output.configure(state=tk.DISABLED)

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text="ready", anchor="w",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text=tr("diff.copy_diff"), relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_diff).pack(side=tk.RIGHT,
                                                padx=8, pady=4)

        self._after_id = None
        self.refresh()

        # v2.49 — real keys + the honest door sign
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-C>", lambda e: self._copy_diff())
        from . import hints
        self.hintbar = hints.hint_bar(
            self, self.theme,
            pairs=(("Ctrl+Shift+C", "copy diff"),),
            notes=("type in either pane — the diff follows",
                   "word / char / line modes above"))

    def _pane(self, parent, label, col):
        frame = tk.Frame(parent, bg=self.theme.get("bg", "#16161e"))
        frame.grid(row=0, column=col, sticky="nsew",
                   padx=(0, 4) if col else (0, 0))
        parent.columnconfigure(col, weight=1)
        parent.rowconfigure(0, weight=1)
        tk.Label(frame, text=label,
                 bg=self.theme.get("bg", "#16161e"),
                 fg=self.theme.get("text_muted", "#8a8a9a")).pack(
            anchor="w")
        widget = tk.Text(frame, width=22, height=6, wrap="word",
                         bg=self.theme.get("editor_bg", "#1a1a24"),
                         fg=self.theme.get("text", "#e8e8f0"),
                         insertbackground=self.theme.get("text",
                                                         "#fff"),
                         relief=tk.FLAT, padx=8, pady=6)
        widget.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        return widget

    # ---------------------------------------------------- behaviour
    def _schedule(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._after_id = self.after(300, self.refresh)
        except Exception:
            pass

    def refresh(self):
        """Re-diff both panes. Junk-tolerant — never raises."""
        try:
            old = self.old_text.get("1.0", "end").rstrip("\n")
            new = self.new_text.get("1.0", "end").rstrip("\n")
            self.output.configure(state=tk.NORMAL)
            self.output.delete("1.0", "end")
            if not old.strip() and not new.strip():
                self.status.config(
                    text=tr("diff.paste_hint"))
            else:
                if self.mode.get() == "line":
                    for kind, line in diff_lines(old, new):
                        mark = {"delete": "- ", "insert": "+ "}.get(
                            kind, "  ")
                        self.output.insert("end", mark + line + "\n")
                else:
                    self.output.insert(
                        "end", inline_diff(old, new,
                                           self.mode.get()) + "\n")
                self.status.config(text=summary(old, new))
            self.output.configure(state=tk.DISABLED)
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _copy_diff(self):
        try:
            text = self.output.get("1.0", "end").rstrip("\n")
            if not text:
                self.status.config(text="nothing to copy")
                return
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text="diff copied")
        except Exception:
            pass


def open_textdiff(parent, theme, initial=""):
    """Public entry: open the Paste Diff window. Never raises."""
    try:
        win = TextDiff(parent, theme, initial=initial)
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
