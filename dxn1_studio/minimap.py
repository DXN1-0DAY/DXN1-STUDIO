"""DXN1 STUDIO — editor minimap (DS2 v2.2).

The VS Code trick, the honest way: a slim canvas beside the editor
where every line is a thin block — width proportional to its length,
colour by role (keywords glow, comments dim, blanks disappear) — plus
a viewport rectangle you can drag to fly through the file.

It polls the editor buffer a few times a second (cheap: it never
copies text, it only measures), hides itself when the file is short,
and never touches the editor's own key bindings.
"""

import tkinter as tk

from .theme import FONT_MONO

POLL_MS = 350
LINE_H = 2          # px per source line in the minimap
MAX_LINES = 4000    # never paint more than this


class Minimap(tk.Canvas):
    """Attach to a CodeEditor's Text widget: Minimap(parent, theme, editor.text)."""

    def __init__(self, parent, theme, text_widget, on_jump=None, **kwargs):
        super().__init__(parent, width=76, highlightthickness=0,
                         bg=theme["editor"], **kwargs)
        self.t = theme
        self.text = text_widget
        self.on_jump = on_jump
        self._drag = False
        self._after_id = None
        self.bind("<Button-1>", self._on_jump)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Button-4>", lambda e: self._scroll(-2))
        self.bind("<Button-5>", lambda e: self._scroll(2))
        self.after(POLL_MS, self._tick)

    # ------------------------------------------------------------ helpers
    def _total_lines(self):
        try:
            return int(self.text.index("end-1c").split(".")[0])
        except (tk.TclError, ValueError):
            return 0

    def _visible_lines(self):
        try:
            first = int(self.text.index("@0,0").split(".")[0])
            last = int(self.text.index(f"@0,{self.text.winfo_height()}").
                       split(".")[0])
            return first, max(first + 1, last)
        except (tk.TclError, ValueError):
            return 1, 2

    def _line_role(self, content):
        stripped = content.strip()
        if not stripped:
            return "blank"
        if stripped.startswith(("#", "//", "/*", "*", '"""', "'''")):
            return "comment"
        if any(k in content for k in ("def ", "class ", "function",
                                      "func ", "if ", "for ", "while ",
                                      "return")):
            return "keyword"
        return "plain"

    def _colors(self):
        t = self.t
        return {
            "blank": t["editor"],
            "plain": t["border"],
            "comment": t["linenum_fg"],
            "keyword": t.accent,
            "viewport": t["hover"],
        }

    # ------------------------------------------------------------ painting
    def _tick(self):
        try:
            self.refresh()
        except tk.TclError:
            return
        self._after_id = self.after(POLL_MS, self._tick)

    def refresh(self):
        self.delete("all")
        total = self._total_lines()
        if total < 40:
            return               # short file — minimap adds nothing
        colors = self._colors()
        try:
            height = max(int(self.winfo_height() or 400), 100)
        except (tk.TclError, ValueError):
            height = 400
        draw_lines = min(total, MAX_LINES)
        step = max(1, draw_lines // int(height / LINE_H))
        first_visible, last_visible = self._visible_lines()
        line_no = 1
        while line_no <= draw_lines:
            try:
                content = self.text.get(f"{line_no}.0", f"{line_no}.end")
            except tk.TclError:
                content = ""
            role = self._line_role(content)
            if role != "blank":
                width = min(70, 6 + int(len(content) * 1.15))
                y = int(line_no / step) * LINE_H
                self.create_rectangle(2, y, 2 + width, y + LINE_H - 1,
                                      fill=colors[role], outline="")
            line_no += step
        # viewport window
        if total > 0:
            scale = draw_lines / total
            vy0 = int(first_visible * scale) * LINE_H
            vy1 = int(last_visible * scale) * LINE_H + LINE_H
            self.create_rectangle(0, vy0, self.winfo_width() or 76, vy1,
                                  outline=colors["keyword"], width=1,
                                  fill="", tags=("vp",))

    # ------------------------------------------------------------ events
    def _y_to_line(self, event_y):
        total = self._total_lines()
        if total <= 0:
            return 1
        try:
            height = max(int(self.winfo_height() or 400), 100)
        except (tk.TclError, ValueError):
            height = 400
        draw_lines = min(total, MAX_LINES)
        step = max(1, draw_lines // int(height / LINE_H))
        row = max(0, int(event_y) // LINE_H)
        return max(1, min(total, row * step))

    def _on_press(self, event):
        self._drag = True

    def _on_drag(self, event):
        if self._drag:
            self._scroll_to(self._y_to_line(event.y))

    def _on_release(self, event):
        self._drag = False

    def _on_jump(self, event):
        line = self._y_to_line(event.y)
        self._scroll_to(line)

    def _scroll_to(self, line):
        try:
            self.text.see(f"{line}.0")
            if self.on_jump:
                self.on_jump(line)
        except tk.TclError:
            pass

    def _wheel(self, event):
        self._scroll(-3 if getattr(event, "delta", 0) > 0 else 3)

    def _scroll(self, units):
        try:
            self.text.yview_scroll(units, "units")
        except tk.TclError:
            pass
