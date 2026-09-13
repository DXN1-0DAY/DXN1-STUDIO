"""DXN1 STUDIO — first-launch Welcome wizard.

A three-step cinematic dark splash shown once:
  1. Welcome        — hero art + display-name entry
  2. Make it yours  — dark/light theme cards + accent colour picker
  3. Ready          — summary + launch into the interactive tour
"""

import os
import tkinter as tk
from tkinter import font as tkfont

from . import APP_NAME, APP_VERSION, APP_CHANNEL, APP_TAGLINE
from .theme import PALETTES, ACCENTS, FONT_UI

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

WIZ_W, WIZ_H = 880, 580

# ---- image loading (PIL when available, native PhotoImage fallback) --------

def load_scaled(path, width, height):
    """Return a PhotoImage scaled to fit (width, height) or None."""
    if not os.path.exists(path):
        return None
    try:
        from PIL import Image, ImageTk
        img = Image.open(path).convert("RGBA")
        img.thumbnail((width, height), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except ImportError:
        try:
            ph = tk.PhotoImage(file=path)
            ratio = max(1, -(-ph.width() // width), -(-ph.height() // height))
            if ratio > 1:
                ph = ph.subsample(ratio, ratio)
            return ph
        except tk.TclError:
            return None
    except Exception:
        return None


def rounded_pill(parent, text, bg, fg, padx=10, pady=4, size=9):
    return tk.Label(parent, text=text, bg=bg, fg=fg,
                    font=(FONT_UI, size, "bold"), padx=padx, pady=pady)


class WizardSlide(tk.Frame):
    """Base slide on the wizard's dark overlay canvas."""

    def __init__(self, parent, wizard):
        super().__init__(parent, bg=wizard.colors["overlay"])
        self.wizard = wizard


class WelcomeWizard:
    """Modal first-launch experience."""

    def __init__(self, master, config, on_complete):
        self.master = master
        self.config = config
        self.on_complete = on_complete
        self.accent_name = config.get("accent", "violet")
        self.accent = ACCENTS.get(self.accent_name, ACCENTS["violet"])["dark"]
        self.theme_choice = config.get("theme", "dark")
        self.name_value = config.get("name", "") or ""
        self._imgrefs = []
        self.index = 0
        self.done = False

        self.colors = {"overlay": "#0d1117", "text": "#e6edf3",
                       "secondary": "#9aa7b8", "muted": "#6e7a8a",
                       "card": "#131a22", "card_border": "#232c3d",
                       "input_bg": "#11161d", "success": "#3fb950"}

        self.win = tk.Toplevel(master)
        self.win.title(f"Welcome to {APP_NAME}")
        self.win.configure(bg=self.colors["overlay"], width=WIZ_W, height=WIZ_H)
        self.win.resizable(False, False)
        self.win.transient(master)
        self.win.protocol("WM_DELETE_WINDOW", lambda: self.finish(skip=True))

        self._build_chrome()
        self._build_slides()
        self._center_over_master()

        self.win.grab_set()
        self.show(0)

    # ---------------------------------------------------------------- chrome
    def _build_chrome(self):
        top = tk.Frame(self.win, bg=self.colors["overlay"])
        top.pack(fill=tk.X, padx=28, pady=(18, 0))

        logo = load_scaled(os.path.join(ASSETS_DIR, "logo.png"), 30, 30)
        if logo:
            self._imgrefs.append(logo)
            tk.Label(top, image=logo, bg=self.colors["overlay"]).pack(side=tk.LEFT)
        tk.Label(top, text=f"{APP_NAME}", bg=self.colors["overlay"],
                 fg=self.colors["text"], font=(FONT_UI, 11, "bold")
                 ).pack(side=tk.LEFT, padx=(10, 8))
        rounded_pill(top, f"{APP_VERSION} · {APP_CHANNEL.upper()}",
                     self.colors["card"], self.colors["secondary"], padx=8, pady=2,
                     size=8).pack(side=tk.LEFT, pady=2)

        self.dots = []
        dotrow = tk.Frame(top, bg=self.colors["overlay"])
        dotrow.pack(side=tk.RIGHT)
        for i in range(3):
            d = tk.Label(dotrow, text="●", font=(FONT_UI, 9),
                         bg=self.colors["overlay"], fg=self.colors["card_border"])
            d.pack(side=tk.LEFT, padx=3)
            self.dots.append(d)

    def _paint_dots(self):
        for i, d in enumerate(self.dots):
            d.config(fg=self.accent if i == self.index else self.colors["card_border"])

    # ---------------------------------------------------------------- slides
    def _build_slides(self):
        # reserve the bottom bar edge first, then let the page expand into
        # the rest — explicit sides keep pack allocation stable when the
        # toplevel is resized to its final geometry.
        bar = tk.Frame(self.win, bg=self.colors["overlay"])
        bar.pack(side=tk.BOTTOM, fill=tk.X, padx=28, pady=(0, 20))

        self.page = tk.Frame(self.win, bg=self.colors["overlay"])
        self.page.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.slides = [
            self._slide_welcome(),
            self._slide_personalize(),
            self._slide_ready(),
        ]
        for s in self.slides:
            s.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.skip_link = tk.Label(bar, text="Skip setup", bg=self.colors["overlay"],
                                  fg=self.colors["muted"], font=(FONT_UI, 9, "underline"),
                                  cursor="hand2")
        self.skip_link.pack(side=tk.RIGHT)
        self.skip_link.bind("<Button-1>", lambda e: self.finish(skip=True))

        self.back_btn = tk.Label(bar, text="←  Back", bg=self.colors["overlay"],
                                 fg=self.colors["secondary"], font=(FONT_UI, 10),
                                 cursor="hand2", padx=14, pady=7)
        self.back_btn.pack(side=tk.LEFT)
        self.back_btn.bind("<Button-1>", lambda e: self.show(max(0, self.index - 1)))

        self.next_btn = tk.Label(bar, text="Continue  →", bg=self.accent,
                                 fg="#ffffff", font=(FONT_UI, 10, "bold"),
                                 cursor="hand2", padx=22, pady=8)
        self.next_btn.pack(side=tk.LEFT, padx=12)
        self.next_btn.bind("<Button-1>", lambda e: self._advance())

        self.hint = tk.Label(bar, text="", bg=self.colors["overlay"],
                             fg=self.colors["muted"], font=(FONT_UI, 9))
        self.hint.pack(side=tk.LEFT, padx=6)

    def _advance(self):
        if self.index < len(self.slides) - 1:
            self.show(self.index + 1)
        else:
            self.finish()

    # ------------------------------------------------------------- slide 1
    def _slide_welcome(self):
        s = WizardSlide(self.page, self)
        wrap = tk.Frame(s, bg=self.colors["overlay"])
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        hero = load_scaled(os.path.join(ASSETS_DIR, "welcome_hero.png"), 660, 300)
        if hero:
            self._imgrefs.append(hero)
            tk.Label(wrap, image=hero, bg=self.colors["overlay"]).pack()
        else:
            c = tk.Canvas(wrap, width=660, height=220, bg=self.colors["overlay"],
                          highlightthickness=0)
            c.pack()
            c.create_polygon(330, 40, 430, 110, 330, 180, 230, 110,
                             fill=self.accent, outline="")
            for i in range(3):
                c.create_rectangle(60, 90 + i * 26, 260, 100 + i * 26,
                                   fill=self.colors["card_border"], outline="")

        title_row = tk.Frame(wrap, bg=self.colors["overlay"])
        title_row.pack(pady=(26, 0))
        tk.Label(title_row, text="Welcome to DXN1 STUDIO", bg=self.colors["overlay"],
                 fg=self.colors["text"], font=(FONT_UI, 26, "bold")).pack(side=tk.LEFT)
        rounded_pill(title_row, "BETA", self.accent, "#ffffff", padx=8, pady=2,
                     size=9).pack(side=tk.LEFT, padx=(12, 0), pady=8)

        tk.Label(wrap, text=APP_TAGLINE, bg=self.colors["overlay"],
                 fg=self.colors["secondary"], font=(FONT_UI, 12)).pack(pady=(6, 20))

        entry_row = tk.Frame(wrap, bg=self.colors["overlay"])
        entry_row.pack()
        tk.Label(entry_row, text="What should we call you?", bg=self.colors["overlay"],
                 fg=self.colors["text"], font=(FONT_UI, 11)).pack(anchor="w")
        self.name_entry = tk.Entry(entry_row, width=34, bg=self.colors["input_bg"],
                                   fg=self.colors["text"], insertbackground=self.colors["text"],
                                   relief=tk.FLAT, font=(FONT_UI, 12),
                                   highlightthickness=1, highlightbackground=self.colors["card_border"],
                                   highlightcolor=self.accent)
        self.name_entry.pack(pady=(8, 0), ipady=8)
        if self.name_value:
            self.name_entry.insert(0, self.name_value)
        self.name_entry.bind("<Return>", lambda e: self._advance())
        tk.Label(entry_row, text="Used for greetings inside the studio — you can stay anonymous too.",
                 bg=self.colors["overlay"], fg=self.colors["muted"],
                 font=(FONT_UI, 9)).pack(anchor="w", pady=(6, 0))
        return s

    # ------------------------------------------------------------- slide 2
    def _slide_personalize(self):
        s = WizardSlide(self.page, self)
        wrap = tk.Frame(s, bg=self.colors["overlay"])
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrap, text="Make it yours", bg=self.colors["overlay"],
                 fg=self.colors["text"], font=(FONT_UI, 22, "bold")).pack(anchor="w")
        tk.Label(wrap, text="Pick a look — switch anytime from the View menu.",
                 bg=self.colors["overlay"], fg=self.colors["secondary"],
                 font=(FONT_UI, 11)).pack(anchor="w", pady=(4, 14))

        cards = tk.Frame(wrap, bg=self.colors["overlay"])
        cards.pack()
        self.theme_cards = {}
        for mode, label, sub in (("dark", "Dark", "Deep space. Easy on the eyes."),
                                 ("light", "Light", "Crisp daylight. Maximum focus.")):
            card = tk.Frame(cards, bg=self.colors["card"], bd=0,
                            highlightthickness=2,
                            highlightbackground=self.colors["card_border"],
                            highlightcolor=self.accent, cursor="hand2")
            card.grid(row=0, column=0 if mode == "dark" else 1, padx=8, ipadx=6, ipady=6)
            self.theme_cards[mode] = card
            prev = tk.Canvas(card, width=168, height=80, bg=self.colors["card"],
                             highlightthickness=0)
            prev.pack(padx=6, pady=(6, 4))
            self._draw_preview(prev, mode)
            tk.Label(card, text=label, bg=self.colors["card"], fg=self.colors["text"],
                     font=(FONT_UI, 12, "bold")).pack(anchor="w", padx=10)
            tk.Label(card, text=sub, bg=self.colors["card"], fg=self.colors["secondary"],
                     font=(FONT_UI, 9)).pack(anchor="w", padx=10, pady=(0, 6))
            card.bind("<Button-1>", lambda e, m=mode: self.choose_theme(m))

        tk.Label(wrap, text="Accent colour", bg=self.colors["overlay"],
                 fg=self.colors["text"], font=(FONT_UI, 12, "bold")
                 ).pack(anchor="w", pady=(14, 6))
        sw = tk.Frame(wrap, bg=self.colors["overlay"])
        sw.pack(anchor="w")
        self.swatches = {}
        for name, spec in ACCENTS.items():
            col = spec["dark"]
            dot = tk.Canvas(sw, width=34, height=34, bg=self.colors["overlay"],
                            highlightthickness=0, cursor="hand2")
            dot.pack(side=tk.LEFT, padx=(0, 12))
            dot.create_oval(5, 5, 29, 29, fill=col, outline="", tags="dot")
            dot.create_text(17, 17, text="", fill="#ffffff", font=(FONT_UI, 11, "bold"),
                            tags="mark")
            dot.bind("<Button-1>", lambda e, n=name: self.choose_accent(n))
            self.swatches[name] = dot
        self.accent_label = tk.Label(wrap, text="", bg=self.colors["overlay"],
                                     fg=self.colors["secondary"], font=(FONT_UI, 10))
        self.accent_label.pack(anchor="w", pady=(8, 0))

        self._refresh_personalize()
        return s

    def _draw_preview(self, c, mode):
        p = PALETTES[mode]
        a = ACCENTS[self.accent_name]["dark" if mode == "dark" else "light"]
        c.create_rectangle(0, 0, 168, 14, fill=p["header"], outline="")
        c.create_rectangle(0, 14, 44, 80, fill=p["sidebar"], outline="")
        c.create_rectangle(44, 14, 168, 80, fill=p["editor"], outline="")
        for i in range(3):
            c.create_rectangle(8, 22 + i * 11, 36, 28 + i * 11,
                               fill=p["linenum_fg"], outline="")
        c.create_rectangle(52, 22, 150, 28, fill=a, outline="")
        for i in range(3):
            c.create_rectangle(52, 36 + i * 12, 120 + (i % 2) * 24, 42 + i * 12,
                               fill=p["linenum_fg"], outline="")
        c.create_rectangle(0, 80, 168, 88, fill=p["statusbar"], outline="")

    def choose_theme(self, mode):
        self.theme_choice = mode
        self._refresh_personalize()

    def choose_accent(self, name):
        self.accent_name = name
        self.accent = ACCENTS[name]["dark"]
        self._refresh_personalize()

    def _refresh_personalize(self):
        for mode, card in self.theme_cards.items():
            card.config(highlightbackground=self.accent if mode == self.theme_choice
                        else self.colors["card_border"])
        for name, dot in self.swatches.items():
            on = name == self.accent_name
            dot.itemconfigure("mark", text="✓" if on else "")
            dot.itemconfigure("dot", outline="#ffffff" if on else "",
                              width=2 if on else 0)
        self.accent_label.config(
            text=f"Selected: {ACCENTS[self.accent_name]['label']} — colours the editor, buttons and highlights")

    # ------------------------------------------------------------- slide 3
    def _slide_ready(self):
        s = WizardSlide(self.page, self)
        wrap = tk.Frame(s, bg=self.colors["overlay"])
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        self.ready_title = tk.Label(wrap, text="You're all set!", bg=self.colors["overlay"],
                                    fg=self.colors["text"], font=(FONT_UI, 28, "bold"))
        self.ready_title.pack()
        tk.Label(wrap, text="Here's your setup:", bg=self.colors["overlay"],
                 fg=self.colors["secondary"], font=(FONT_UI, 12)).pack(pady=(8, 18))

        self.summary = tk.Frame(wrap, bg=self.colors["overlay"])
        self.summary.pack()
        for icon, label, value in (("◐", "Theme", "Dark"), ("◆", "Accent", "Violet"),
                                   ("→", "Next", "Quick guided tour")):
            row = tk.Frame(self.summary, bg=self.colors["card"],
                           highlightthickness=1, highlightbackground=self.colors["card_border"])
            row.pack(fill=tk.X, pady=4, ipadx=12, ipady=7)
            tk.Label(row, text=icon, bg=self.colors["card"], fg=self.accent,
                     font=(FONT_UI, 12, "bold"), width=3).pack(side=tk.LEFT)
            tk.Label(row, text=label, bg=self.colors["card"], fg=self.colors["secondary"],
                     font=(FONT_UI, 10), width=8, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=self.colors["card"], fg=self.colors["text"],
                     font=(FONT_UI, 10, "bold"), anchor="w").pack(side=tk.LEFT)
        return s

    def _refresh_ready(self):
        name = (self.name_entry.get() or "").strip() or "developer"
        self.ready_title.config(text=f"You're all set, {name}!")
        theme_lbl = "Dark" if self.theme_choice == "dark" else "Light"
        accent_lbl = ACCENTS[self.accent_name]["label"]
        vals = [theme_lbl, accent_lbl, "Quick guided tour"]
        for row, v in zip(self.summary.winfo_children(), vals):
            row.winfo_children()[2].config(text=v)

    # ---------------------------------------------------------------- flow
    def _center_over_master(self):
        self.win.update_idletasks()
        self.win.geometry(f"{WIZ_W}x{WIZ_H}")
        mx = self.master.winfo_rootx() + max(0, (self.master.winfo_width() - WIZ_W) // 2)
        my = self.master.winfo_rooty() + max(40, (self.master.winfo_height() - WIZ_H) // 3)
        self.win.geometry(f"{WIZ_W}x{WIZ_H}+{max(0, mx)}+{max(0, my)}")

    def show(self, idx):
        self.index = idx
        if idx == len(self.slides) - 1:
            self._refresh_ready()
        for i, s in enumerate(self.slides):
            if i == idx:
                s.lift()
            else:
                s.lower()
        self._paint_dots()
        last = idx == len(self.slides) - 1
        self.next_btn.config(text="Launch DXN1 STUDIO  ✦" if last else "Continue  →")
        self.back_btn.config(
            fg=self.colors["secondary"] if idx > 0 else self.colors["card_border"])
        hints = ["", "Changes apply instantly across the IDE",
                 "A quick guided tour comes next"]
        self.hint.config(text=hints[idx])

    def finish(self, skip=False):
        if self.done:
            return
        self.done = True
        # capture state before the window (and its widgets) is destroyed
        name = ""
        if not skip:
            try:
                name = (self.name_entry.get() or "").strip()
            except tk.TclError:
                name = ""
            self.config.set("name", name, save=False)
            self.config.set("theme", self.theme_choice, save=False)
            self.config.set("accent", self.accent_name, save=False)
        try:
            self.win.grab_release()
            self.win.destroy()
        except tk.TclError:
            pass
        self.config.set("onboarded", True)
        self.on_complete(self.config)
