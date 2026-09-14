"""DS2 TextCase — identifier case converter.

Paste an identifier in any convention — ``user_profile_id``,
``getHTTPResponse``, ``MyApp2-file`` — and read it in every style at
once: snake_case, camelCase, PascalCase, kebab-case, CONSTANT_CASE,
Title Case, dot.case and flatcase. One click copies any row.

Engine (_words / convert / all_cases) is pure and unit-tested; the
window never raises on weird input.

Open with: Workshop menu, palette, terminal ``case`` / ``textcase``.
"""

import re
import tkinter as tk

from .i18n import tr

__all__ = ["words", "convert", "all_cases", "TextCase", "open_textcase"]

_DELIM = re.compile(r"[^0-9a-zA-Z]+")


def words(text):
    """Split any identifier into words. Pure + junk-tolerant.

    Handles snake/kebab/dot/space delimiters, camelCase and PascalCase
    boundaries, and acronym runs (``getHTTPResponse`` → get/HTTP/
    Response). Empty/non-string → [].
    """
    if not isinstance(text, str):
        return []
    parts = _DELIM.sub(" ", text).split()
    out = []
    for part in parts:
        # split camel boundaries, keeping acronym runs whole
        part = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", part)
        part = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", part)
        out.extend(p for p in part.split() if p)
    return out


def convert(text, style):
    """Convert *text* to a named style. Unknown style → ''."""
    w = words(text)
    if not w:
        return ""
    if style == "snake":
        return "_".join(x.lower() for x in w)
    if style == "camel":
        return w[0].lower() + "".join(
            x[:1].upper() + x[1:].lower() for x in w[1:])
    if style == "pascal":
        return "".join(x[:1].upper() + x[1:].lower() for x in w)
    if style == "kebab":
        return "-".join(x.lower() for x in w)
    if style == "constant":
        return "_".join(x.upper() for x in w)
    if style == "title":
        return " ".join(x[:1].upper() + x[1:].lower() for x in w)
    if style == "dot":
        return ".".join(x.lower() for x in w)
    if style == "flat":
        return "".join(x.lower() for x in w)
    return ""


def all_cases(text):
    """Dict of every style → converted string (skips empties)."""
    return {style: convert(text, style) for style in
            ("snake", "camel", "pascal", "kebab", "constant",
             "title", "dot", "flat") if convert(text, style)}


# --------------------------------------------------------------- window

class TextCase(tk.Toplevel):
    """Identifier case conversion window. Never raises on junk."""

    STYLES = ("snake", "camel", "pascal", "kebab",
              "constant", "title", "dot", "flat")

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("TextCase — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("560x420")
        self.minsize(460, 340)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="textcase", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=(10, 8), pady=8)
        self.entry = tk.Entry(top, width=26,
                              bg=t.get("editor_bg", "#1a1a24"),
                              fg=t.get("text", "#e8e8f0"),
                              insertbackground=t.get("text", "#fff"),
                              relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT, padx=4, pady=6)
        self.entry.insert(0, initial or "getHTTPResponse_2")
        self.entry.bind("<KeyRelease>", lambda _e: self.refresh())
        tk.Button(top, text="paste", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._paste).pack(side=tk.RIGHT, padx=(4, 10))

        self.rows = tk.Frame(self, bg=t.get("bg", "#16161e"))
        self.rows.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        self.labels = {}
        for style in self.STYLES:
            row = tk.Frame(self.rows, bg=t.get("bg", "#16161e"))
            row.pack(fill=tk.X, pady=3)
            name = tk.Label(row, text=style, width=9, anchor="w",
                            bg=t.get("bg", "#16161e"),
                            fg=t.get("accent", "#7aa2f7"),
                            font=("TkFixedFont", 10, "bold"))
            name.pack(side=tk.LEFT)
            value = tk.Label(row, text="—", anchor="w",
                             bg=t.get("bg", "#16161e"),
                             fg=t.get("text", "#e8e8f0"),
                             font=("TkFixedFont", 11), cursor="hand2")
            value.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            value.bind("<Button-1>",
                       lambda _e, s=style: self._copy(s))
            self.labels[style] = value

        self.status = tk.Label(self, text=tr("textcase.click_copy"),
                               anchor="w", bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.refresh()

    # ---------------------------------------------------- behaviour
    def _paste(self):
        try:
            text = self.clipboard_get().strip()
        except Exception:
            text = ""
        if text:
            self.entry.delete(0, "end")
            self.entry.insert(0, text)
            self.refresh()

    def refresh(self):
        """Recompute all styles. Junk-tolerant by design."""
        try:
            cases = all_cases(self.entry.get())
            for style, label in self.labels.items():
                label.config(text=cases.get(style, "—"))
            n = len(cases)
            self.status.config(
                text="%d conversions — %s" % (n, tr("textcase.click_copy"))
                if n else "type an identifier — junk is tolerated")
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _copy(self, style):
        try:
            text = self.labels[style].cget("text")
            if text == "—":
                return
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text="%s copied: %s" % (style, text))
        except Exception:
            pass


def open_textcase(parent, theme, initial=""):
    """Public entry: open the TextCase window. Never raises."""
    try:
        win = TextCase(parent, theme, initial=initial)
        win.grab_release()
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
