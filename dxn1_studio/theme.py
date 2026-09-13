"""DXN1 STUDIO — theme engine.

Two complete palettes (dark + light) and four accent colours. Everything in
the IDE reads from a resolved ``Theme`` object — no hardcoded colours, so a
theme switch is a single object swap (main window rebuilds to apply).
"""

from . import APP_NAME, APP_VERSION, APP_CHANNEL

# --------------------------------------------------------------------- palettes
PALETTES = {
    "dark": {
        "bg":              "#0d1117",
        "sidebar":         "#11161d",
        "header":          "#161c24",
        "editor":          "#0d1117",
        "terminal":        "#0a0e13",
        "statusbar":       "#10151c",
        "border":          "#1f2633",
        "hover":           "#1a212c",
        "text":            "#e6edf3",
        "text_secondary":  "#9aa7b8",
        "text_muted":      "#6e7a8a",
        "linenum_bg":      "#11161d",
        "linenum_fg":      "#4d5766",
        "select_fg":       "#ffffff",
        "success":         "#3fb950",
        "card":            "#131a22",
        "card_border":     "#232c3d",
        "overlay":         "#0d1117",   # wizard / splash canvas
        "overlay_text":    "#e6edf3",
    },
    "light": {
        "bg":              "#ffffff",
        "sidebar":         "#f6f8fa",
        "header":          "#eef1f4",
        "editor":          "#ffffff",
        "terminal":        "#f6f8fa",
        "statusbar":       "#f0f3f6",
        "border":          "#d8dee4",
        "hover":           "#eaeef2",
        "text":            "#1f2328",
        "text_secondary":  "#57606a",
        "text_muted":      "#8b949e",
        "linenum_bg":      "#f6f8fa",
        "linenum_fg":      "#8b949e",
        "select_fg":       "#ffffff",
        "success":         "#1a7f37",
        "card":            "#ffffff",
        "card_border":     "#d0d7de",
        "overlay":         "#0d1117",   # wizard keeps its cinematic dark look
        "overlay_text":    "#e6edf3",
    },
}

# --------------------------------------------------------------------- accents
ACCENTS = {
    "violet": {"dark": "#8b5cf6", "light": "#7c3aed", "label": "Violet"},
    "cyan":   {"dark": "#22d3ee", "light": "#0891b2", "label": "Cyan"},
    "green":  {"dark": "#4ade80", "light": "#16a34a", "label": "Green"},
    "orange": {"dark": "#fb923c", "light": "#ea580c", "label": "Orange"},
}

# ---------------------------------------------------------------------- fonts
FONT_UI = "Segoe UI"      # Tk falls back gracefully when unavailable
FONT_MONO = "Consolas"


class Theme:
    """Resolved palette + accent for the active session."""

    def __init__(self, mode="dark", accent="violet"):
        self.mode = mode if mode in PALETTES else "dark"
        self.accent_name = accent if accent in ACCENTS else "violet"
        self._p = PALETTES[self.mode]
        self._a = ACCENTS[self.accent_name]

    # palette access — theme["bg"], theme.get("hover")
    def __getitem__(self, key):
        return self._p[key]

    def get(self, key, default=None):
        return self._p.get(key, default)

    @property
    def accent(self):
        return self._a["dark" if self.is_dark else "light"]

    @property
    def accent_soft(self):
        """Dimmer accent for borders/badges."""
        return self._a["light" if self.is_dark else "dark"]

    @property
    def accent_label(self):
        return self._a["label"]

    @property
    def is_dark(self):
        return self.mode == "dark"

    @property
    def opposite(self):
        return Theme("light" if self.is_dark else "dark", self.accent_name)

    # font helpers ---------------------------------------------------------
    def font(self, size=10, weight="normal"):
        return (FONT_UI, size, weight)

    def mono(self, size=10, weight="normal"):
        return (FONT_MONO, size, weight)

    def __repr__(self):
        return f"Theme(mode={self.mode!r}, accent={self.accent_name!r})"


def from_config(config):
    return Theme(config.get("theme", "dark"), config.get("accent", "violet"))
