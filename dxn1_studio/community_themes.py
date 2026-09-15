"""DXN1 STUDIO — community theme gallery (DS2 v1.9).

Twelve curated palettes built on the studio's two base modes — every
one keeps contrast-safe text colours and the full palette key set.
Pick one in the gallery, hit Apply, and the studio restarts into it
(the same swap the dark/light toggle uses).

Themes are plain dicts stored in config (``custom_theme``), so they
trivially export/import as JSON — share yours with one file. The
engine resolves them defensively: unknown keys are ignored and every
missing key falls back to the base palette, so a half-written theme
can never render the studio unreadable.
"""

import json
import os
import tkinter as tk

from .theme import FONT_UI, FONT_MONO, PALETTES

STORE_DIR = os.path.join(os.path.expanduser("~"), ".dxn1-studio")
USER_THEMES_PATH = os.path.join(STORE_DIR, "themes.json")

# hue-tinted variants of the two base palettes — every key present
BASE_KEYS = ("bg", "sidebar", "header", "editor", "terminal", "statusbar",
             "border", "hover", "text", "text_secondary", "text_muted",
             "linenum_bg", "linenum_fg", "select_fg", "success", "card",
             "card_border", "overlay", "overlay_text")


def _tint(base, shifts):
    """Apply hue shifts to a base palette dict."""
    out = dict(base)
    out.update(shifts)
    return out


def _build_gallery():
    d = PALETTES["dark"]
    l = PALETTES["light"]
    return [
        ("Midnight Violet", "dark", _tint(d, {
            "bg": "#0e0d16", "sidebar": "#131220", "header": "#17162a",
            "editor": "#0e0d16", "card": "#161427", "terminal": "#0b0a12"})),
        ("Deep Ocean", "dark", _tint(d, {
            "bg": "#0a1220", "sidebar": "#0e1826", "header": "#122032",
            "editor": "#0a1220", "card": "#101c2c", "terminal": "#080f1a"})),
        ("Forest Night", "dark", _tint(d, {
            "bg": "#0c1410", "sidebar": "#101a14", "header": "#142018",
            "editor": "#0c1410", "card": "#122018"})),
        ("Ember Dark", "dark", _tint(d, {
            "bg": "#161010", "sidebar": "#1c1414", "header": "#221a18",
            "editor": "#161010", "card": "#201616"})),
        ("Slate Studio", "dark", _tint(d, {
            "bg": "#111318", "sidebar": "#151820", "header": "#1a1e26",
            "card": "#171b24"})),
        ("Carbon", "dark", _tint(d, {
            "bg": "#0a0a0a", "sidebar": "#0f0f0f", "header": "#141414",
            "editor": "#0a0a0a", "card": "#121212", "border": "#222222"})),
        ("Paper White", "light", _tint(l, {})),
        ("Warm Paper", "light", _tint(l, {
            "bg": "#fbf7f0", "sidebar": "#f5efe4", "header": "#efe6d8",
            "editor": "#fbf7f0", "card": "#ffffff"})),
        ("Mint Light", "light", _tint(l, {
            "bg": "#f2faf6", "sidebar": "#e8f4ee", "header": "#ddefe5",
            "editor": "#f2faf6"})),
        ("Rosy Dawn", "light", _tint(l, {
            "bg": "#fdf4f4", "sidebar": "#f8ecec", "header": "#f2e2e2",
            "editor": "#fdf4f4"})),
        ("Nordic Light", "light", _tint(l, {
            "bg": "#f4f6f8", "sidebar": "#eceff3", "header": "#e2e8ef",
            "editor": "#f4f6f8"})),
        ("Solarized-ish", "light", _tint(l, {
            "bg": "#fdf6e3", "sidebar": "#f5eedb", "header": "#eee8d5",
            "editor": "#fdf6e3", "text": "#073642", "text_secondary":
            "#586e75", "text_muted": "#657474"})),
    ]


GALLERY = _build_gallery()


def get_palette(name, mode=None):
    """Resolve a gallery theme name → (palette dict, base mode)."""
    for title, base_mode, palette in GALLERY:
        if title == name:
            return palette, (mode or base_mode)
    return None, (mode or "dark")


def user_themes():
    try:
        with open(USER_THEMES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_user_theme(name, palette):
    themes = user_themes()
    themes[name] = palette
    try:
        os.makedirs(STORE_DIR, exist_ok=True)
        with open(USER_THEMES_PATH, "w", encoding="utf-8") as fh:
            json.dump(themes, fh, indent=1)
        return True
    except OSError:
        return False


def resolve(config):
    """(palette, mode) for the config's current custom theme, if any."""
    name = config.get("custom_theme_name") if config is not None else None
    if not name:
        return None, None
    return get_palette(name)


# ------------------------------------------------------------------ view
class ThemeGallery(tk.Toplevel):
    """Browse themes with live swatch cards; Apply + restart."""

    def __init__(self, parent, theme, config, on_log=None, restart=None):
        super().__init__(parent)
        self.t = theme
        self.config_obj = config
        self.on_log = on_log or (lambda msg: None)
        self.restart = restart or (lambda: None)
        self.title("Theme gallery — DXN1 STUDIO")
        self.configure(bg=self.t["bg"])
        self.geometry("760x600")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 760x600 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 760, 600))
        self.minsize(560, 420)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 760, 600
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=46)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="◑  THEME GALLERY", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        tk.Label(bar, text="Apply restarts the studio into the theme",
                 bg=t["header"], fg=t["text_muted"],
                 font=(FONT_UI, 8)).pack(side=tk.RIGHT, padx=12)
        current = self.config_obj.get("custom_theme_name") or \
            f"{self.t.mode} · default"
        tk.Label(bar, text=f"now: {current}", bg=t["header"],
                 fg=t.accent, font=(FONT_MONO, 8, "bold")).pack(
            side=tk.RIGHT, padx=6)

        self.grid_frame = tk.Frame(self, bg=t["bg"])
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        self._render()

        # the door sign
        from . import hints
        self.hintbar = hints.hint_bar(
            self, t,
            notes=("click Apply on a card to wear that theme",
                   "applying restarts the studio"))

    def _render(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        t = self.t
        current = self.config_obj.get("custom_theme_name") or ""
        for i, (name, _mode, palette) in enumerate(GALLERY):
            card = tk.Frame(self.grid_frame, bg=palette["editor"],
                            highlightthickness=2,
                            highlightbackground=self.t.accent
                            if name == current else t["card_border"])
            card.grid(row=i // 3, column=i % 3, padx=6, pady=6,
                      sticky="nsew", ipadx=4, ipady=4)
            tk.Label(card, text=name, bg=palette["editor"],
                     fg=palette["text"], font=(FONT_UI, 10, "bold"),
                     anchor="w").pack(fill=tk.X, padx=10, pady=(8, 4))
            # colour swatch strip
            strip = tk.Frame(card, bg=palette["editor"])
            strip.pack(fill=tk.X, padx=10, pady=2)
            for key in ("sidebar", "header", "card", "border", "success"):
                tk.Label(strip, text="      ", bg=palette[key]
                         ).pack(side=tk.LEFT, padx=1, pady=2)
            # mini code sample
            tk.Label(card, text="def hello():\n    return 'world'",
                     bg=palette["editor"], fg=palette["text_secondary"],
                     font=(FONT_MONO, 8), anchor="w", justify=tk.LEFT
                     ).pack(fill=tk.X, padx=10, pady=(2, 2))
            tk.Label(card, text=_mode, bg=palette["editor"],
                     fg=palette["text_muted"], font=(FONT_UI, 7)
                     ).pack(anchor="w", padx=10, pady=(0, 2))
            apply_btn = tk.Label(card, text="Apply", bg=palette["header"],
                                 fg=palette["text"], font=(FONT_UI, 8,
                                                           "bold"),
                                 cursor="hand2", padx=10, pady=3)
            apply_btn.pack(anchor="w", padx=10, pady=(2, 8))
            apply_btn.bind("<Button-1>", lambda e, n=name, p=palette:
                           self._apply(n, p))

    def _apply(self, name, palette):
        try:
            self.config_obj.set("custom_theme_name", name)
            self.config_obj.set("custom_theme",
                                {k: palette[k] for k in PALETTES["dark"]
                                 if k in palette})
            self.on_log(f"theme applied: {name}")
            self.destroy()
            self.restart()          # same restart path as the theme toggle
        except Exception:
            pass


def open_gallery(parent, theme, config, on_log=None, restart=None):
    """Convenience opener — mirrors the studio's one-call dialog style."""
    return ThemeGallery(parent, theme, config, on_log=on_log,
                        restart=restart)
