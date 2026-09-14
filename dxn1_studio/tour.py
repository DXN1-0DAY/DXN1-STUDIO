"""DXN1 STUDIO — interactive guided tour.

A borderless spotlight card floats next to each real UI element
(explorer, tabs, editor, terminal), highlighting the target with an accent
border. Next/Back/Skip included; finishing marks the tour as done so it
never nags again.
"""

import tkinter as tk

from .theme import FONT_UI

MARGIN = 14


class TourStep:
    def __init__(self, target_key, title, body, anchor="below", final=False):
        self.target_key = target_key
        self.title = title
        self.body = body
        self.anchor = anchor
        self.final = final


class InteractiveTour:
    """Click-through tour over the live main window."""

    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.theme = app.theme
        self.accent = self.theme.accent
        self.index = -1
        self.card = None
        self._highlighted = None
        self._saved_highlight = None
        self.done = False

        self.steps = [
            TourStep("sidebar", "File Explorer",
                     "Your whole workspace, one click away. Click any file to open it "
                     "instantly in the editor — folders stay tidy on top.",
                     "right"),
            TourStep("tabs_frame", "Editor Tabs",
                     "Every file you open lands here as a tab. Hit the ✕ to close one. "
                     "Your active file always shows its path in the status bar below.",
                     "below"),
            TourStep("toolbar", "Run, Packages & Export",
                     "One strip for the power stuff: Run (F5) executes your code and "
                     "streams output to the terminal, Packages installs optional extras "
                     "like Flask, Export zips the whole workspace to share.",
                     "below"),
            TourStep("editor", "The Editor",
                     "Line numbers, unlimited undo and a distraction-free dark (or light) "
                     "canvas in your chosen accent colour. This is where flow happens.",
                     "left"),
            TourStep("terminal", "Terminal with Studio Commands",
                     "Activity is echoed here — and you can type too. Try “run”, "
                     "“packages” or the classic “dxn1 studio” to replay the boot "
                     "splash. “help” lists everything.",
                     "above"),
        ]
        if self.app.config.get("agents_enabled"):
            self.steps.append(TourStep(
                "agents", "DXN1 Agents",
                "Your sandboxed copilot. Attach a brain in its settings — "
                "your own API key (BYOK), the free GitHub Models tier or the "
                "lightweight Kilo gateway — or stay on built-in offline "
                "skills. Every edit and command lands as a card you accept "
                "or decline, and it never leaves this workspace.",
                "left"))
        self.steps.append(TourStep(
            None, "You're ready",
            "That's the studio — clean, fast and already yours. Start a new "
            "workspace from File → Project Hub anytime, and replay this tour "
            "from Help → Replay Welcome & Tour.",
            "center", final=True))

    # ---------------------------------------------------------------- public
    def start(self):
        self.show(0)

    def finish(self, skipped=False):
        if self.done:
            return
        self.done = True
        self._restore_highlight()
        self._destroy_card()
        self.config.set("tour_done", True)
        if not skipped:
            self.app.terminal.log("Tour complete — happy coding!")

    # ---------------------------------------------------------------- engine
    def show(self, idx):
        if self.done:
            return
        self._restore_highlight()
        self.index = idx
        step = self.steps[idx]
        target = None if step.target_key is None else \
            self.app.widgets.get(step.target_key)
        if not step.final and (target is None or not target.winfo_exists()):
            self.finish(skipped=True)
            return
        if target is not None:
            self._highlight(target)
        self._render_card(step, target)

    def next(self):
        if self.index < len(self.steps) - 1:
            self.show(self.index + 1)
        else:
            self.finish()

    def back(self):
        self.show(max(0, self.index - 1))

    # ------------------------------------------------------------- highlight
    def _highlight(self, widget):
        self._highlighted = widget
        self._saved_highlight = (widget.cget("highlightthickness"),
                                 widget.cget("highlightbackground"))
        widget.config(highlightthickness=2, highlightbackground=self.accent,
                      highlightcolor=self.accent)

    def _restore_highlight(self):
        if self._highlighted is not None and self._highlighted.winfo_exists() \
                and self._saved_highlight is not None:
            try:
                self._highlighted.config(highlightthickness=self._saved_highlight[0],
                                         highlightbackground=self._saved_highlight[1])
            except tk.TclError:
                pass
        self._highlighted = None
        self._saved_highlight = None

    # ------------------------------------------------------------------ card
    def _destroy_card(self):
        if self.card is not None:
            try:
                self.card["top"].destroy()
            except tk.TclError:
                pass
            self.card = None

    def _render_card(self, step, target):
        self._destroy_card()
        top = tk.Toplevel(self.app.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=self.accent)

        inner = tk.Frame(top, bg=self.theme["card"],
                         highlightthickness=1, highlightbackground=self.accent)
        inner.pack(fill=tk.BOTH, expand=True)

        head = tk.Frame(inner, bg=self.theme["card"])
        head.pack(fill=tk.X, padx=18, pady=(14, 0))
        total = len(self.steps)
        tk.Label(head, text=f"{self.index + 1} / {total}", bg=self.theme["card"],
                 fg=self.theme["text_muted"], font=(FONT_UI, 9, "bold")).pack(side=tk.LEFT)
        dots = tk.Frame(head, bg=self.theme["card"])
        dots.pack(side=tk.RIGHT)
        for i in range(total):
            tk.Label(dots, text="●", font=(FONT_UI, 6),
                     bg=self.theme["card"],
                     fg=self.accent if i == self.index else self.theme["card_border"]
                     ).pack(side=tk.LEFT, padx=1)

        mid = tk.Frame(inner, bg=self.theme["card"])
        mid.pack(fill=tk.X, padx=18, pady=(8, 0))
        tk.Label(mid, text=step.title, bg=self.theme["card"], fg=self.accent,
                 font=(FONT_UI, 14, "bold")).pack(anchor="w")
        tk.Label(mid, text=step.body, bg=self.theme["card"], fg=self.theme["text"],
                 font=(FONT_UI, 10), wraplength=330, justify=tk.LEFT
                 ).pack(anchor="w", pady=(6, 0))

        btnrow = tk.Frame(inner, bg=self.theme["card"])
        btnrow.pack(fill=tk.X, padx=18, pady=(12, 14))
        if self.index > 0:
            back = tk.Label(btnrow, text="← Back", bg=self.theme["card"],
                            fg=self.theme["text_secondary"], font=(FONT_UI, 9, "bold"),
                            cursor="hand2")
            back.pack(side=tk.LEFT)
            back.bind("<Button-1>", lambda e: self.back())
        skip = tk.Label(btnrow, text="Skip tour", bg=self.theme["card"],
                        fg=self.theme["text_muted"], font=(FONT_UI, 9, "underline"),
                        cursor="hand2")
        skip.pack(side=tk.RIGHT)
        skip.bind("<Button-1>", lambda e: self.finish(skipped=True))

        primary_txt = "Finish ✦" if step.final else "Next →"
        primary = tk.Label(btnrow, text=primary_txt, bg=self.accent, fg="#ffffff",
                           font=(FONT_UI, 9, "bold"), cursor="hand2", padx=14, pady=5)
        primary.pack(side=tk.RIGHT, padx=10)
        primary.bind("<Button-1>", lambda e: self.next())

        self.card = {"top": top, "inner": inner}
        top.update_idletasks()
        self._place_card(step, target)

    def _place_card(self, step, target):
        top = self.card["top"]
        cw, ch = top.winfo_reqwidth(), top.winfo_reqheight()
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        rx = self.app.root.winfo_rootx()
        ry = self.app.root.winfo_rooty()
        rw = self.app.root.winfo_width()
        rh = self.app.root.winfo_height()

        if target is None:
            x = rx + (rw - cw) // 2
            y = ry + (rh - ch) // 2 - 60
        else:
            tx, ty = target.winfo_rootx(), target.winfo_rooty()
            tw, th = target.winfo_width(), target.winfo_height()
            anchors = {
                "above":  (tx + (tw - cw) // 2, ty - ch - 12),
                "below":  (tx + (tw - cw) // 2, ty + th + 12),
                "left":   (tx - cw - 12,        ty + (th - ch) // 2),
                "right":  (tx + tw + 12,        ty + (th - ch) // 2),
            }
            x, y = anchors.get(step.anchor, anchors["below"])

        x = max(MARGIN, min(x, sw - cw - MARGIN))
        y = max(MARGIN, min(y, sh - ch - MARGIN))
        top.geometry(f"+{x}+{y}")
        top.deiconify()
