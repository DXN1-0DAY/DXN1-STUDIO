"""DXN1 STUDIO — Colorblind Lab (DS2 v2.28).

See the studio's themes the way color-blind users do. The engine
applies the classic CVD transformation matrices (deuteranopia,
protanopia, tritanopia, achromatopsia) to any hex color or whole
palette, with a severity blend for design tuning. The lab also
re-runs the Contrast Auditor on the simulated palette, so the real
question gets answered: "is my theme still readable under CVD?"

The matrices work in sRGB space — the standard quick approximation
used by design tools (great for review decisions; this is not a
clinical simulation). Every function is junk-tolerant: bad hex in,
None out; bad palettes audit to honest FAILs. The window never
raises.
"""

import tkinter as tk
from tkinter import ttk

from .colorkit import hex_to_rgb, rgb_to_hex
from .i18n import tr

# ----------------------------------------------------------------- engine

# sRGB-space CVD approximation matrices (row-mixing of R,G,B in 0..1)
KINDS = ("deuteranopia", "protanopia", "tritanopia", "achromatopsia")

MATRICES = {
    "deuteranopia": ((0.625, 0.375, 0.000),
                     (0.700, 0.300, 0.000),
                     (0.000, 0.300, 0.700)),
    "protanopia":   ((0.567, 0.433, 0.000),
                     (0.558, 0.442, 0.000),
                     (0.000, 0.242, 0.758)),
    "tritanopia":   ((0.950, 0.050, 0.000),
                     (0.000, 0.433, 0.567),
                     (0.000, 0.475, 0.525)),
    "achromatopsia": ((0.299, 0.587, 0.114),
                      (0.299, 0.587, 0.114),
                      (0.299, 0.587, 0.114)),
}

KIND_LABELS = {
    "deuteranopia": "Deuteranopia (green-blind)",
    "protanopia": "Protanopia (red-blind)",
    "tritanopia": "Tritanopia (blue-blind)",
    "achromatopsia": "Achromatopsia (no color)",
}

# palette keys the lab previews, in display order
SWATCH_KEYS = ("bg", "sidebar", "header", "card", "editor", "terminal",
               "text", "text_secondary", "text_muted", "success",
               "linenum_fg", "select_fg")


def _pairs(pal):
    """(key, value) pairs from a dict palette or a Theme-like object
    (anything indexable / with items()). Never raises."""
    if isinstance(pal, dict):
        return list(pal.items())
    try:
        return list(pal.items())
    except Exception:  # noqa: BLE001 — wrapper without items()
        pass
    out = []
    for k in SWATCH_KEYS:
        try:
            v = pal[k]
        except Exception:  # noqa: BLE001
            continue
        if v:
            out.append((k, v))
    return out


def simulate_hex(hex_color, kind="deuteranopia", severity=1.0):
    """Simulate one color under a CVD kind. Returns a hex string or
    None on junk. ``severity`` 0..1 blends original vs simulated."""
    rgb = hex_to_rgb(hex_color)
    matrix = MATRICES.get(kind if kind in KINDS else "deuteranopia")
    if not rgb or not matrix:
        return None
    try:
        sev = min(1.0, max(0.0, float(severity)))
    except (TypeError, ValueError):
        sev = 1.0
    r, g, b = (c / 255.0 for c in rgb)
    sim = []
    for row in matrix:
        val = row[0] * r + row[1] * g + row[2] * b
        val = min(1.0, max(0.0, val))
        sim.append(val)
    out = [round(255 * (orig * (1 - sev) + s * sev))
           for orig, s in zip((r, g, b), sim)]
    return rgb_to_hex(*out)


def simulate_palette(palette, kind="deuteranopia", severity=1.0):
    """Simulate every parseable key of a palette (dict or Theme-like
    object); junk values are dropped (the contrast engine fills
    honest gaps downstream)."""
    out = {}
    for key, val in _pairs(palette):
        sim = simulate_hex(val, kind, severity)
        if sim:
            out[key] = sim
    return out


def swatch_rows(palette, kind="deuteranopia", severity=1.0):
    """(key, original_hex, simulated_hex) for the display keys —
    entries skip themselves when a color can't be parsed."""
    vals = dict(_pairs(palette))
    rows = []
    for key in SWATCH_KEYS:
        orig = vals.get(key, "")
        sim = simulate_hex(orig, kind, severity)
        if orig and sim:
            rows.append((key, str(orig), sim))
    return rows


def sim_summary(palette, kind="deuteranopia", severity=1.0):
    """Contrast-audit the simulated palette — ties the Colorblind
    Lab to the Contrast Auditor. Returns the usual summary dict."""
    from .contrast import audit_palette, audit_summary
    sim = simulate_palette(palette, kind, severity)
    return audit_summary(audit_palette(sim))


def survive_line(palette, kind, severity=1.0):
    """One-line verdict: 'CVD view: 13 pairs · 11 pass · 2 fail'."""
    s = sim_summary(palette, kind, severity)
    return "CVD view: %d pairs · %d pass · %d fail" % (
        s["total"], s["total"] - s["FAIL"], s["FAIL"])


# ----------------------------------------------------------------- window

class ColorblindLab(tk.Toplevel):
    """CVD preview window. Never raises on junk themes or hexes."""

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Colorblind Lab — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("760x540")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 760x540 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 760, 540))
        self.minsize(620, 420)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="colorblind lab — see your theme through "
                           "CVD eyes",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=10, pady=8)
        self.verdict = tk.Label(top, text="", anchor="e",
                                bg=t.get("header", "#242432"),
                                fg=t.get("success", "#3fb950"))
        self.verdict.pack(side=tk.RIGHT, padx=10)

        bar = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bar.pack(fill=tk.X, padx=10, pady=(8, 0))
        self.kind = tk.StringVar(value=KINDS[0])
        for k in KINDS:
            ttk.Radiobutton(bar, text=KIND_LABELS[k], value=k,
                            variable=self.kind,
                            command=self._refresh).pack(
                side=tk.LEFT, padx=(0, 10))
        tk.Label(bar, text=tr("cvdlab.severity"),
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(side=tk.LEFT,
                                                         padx=(4, 4))
        self.severity = tk.DoubleVar(value=100.0)
        ttk.Scale(bar, from_=0.0, to=100.0, variable=self.severity,
                  command=lambda _v: self._refresh()).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        head = tk.Frame(body, bg=t.get("bg", "#16161e"))
        head.pack(fill=tk.X)
        for text, anchor in (("palette key", "w"),
                             ("original", "center"),
                             ("simulated", "center")):
            tk.Label(head, text=text, width=16 if anchor == "w" else 14,
                     anchor=anchor, bg=t.get("bg", "#16161e"),
                     fg=t.get("text_muted", "#8a8a9a")).pack(
                side=tk.LEFT, padx=(0, 8) if anchor == "w" else (4, 4))
        self.grid = tk.Frame(body, bg=t.get("bg", "#16161e"))
        self.grid.pack(fill=tk.BOTH, expand=True)

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        tk.Label(bottom, text="try a hex:", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(side=tk.LEFT,
                                                         padx=(10, 4))
        self.custom = tk.Entry(bottom, width=12, relief=tk.FLAT,
                               bg=t.get("editor_bg", "#1a1a24"),
                               fg=t.get("text", "#e8e8f0"),
                               insertbackground=t.get("text", "#fff"))
        self.custom.pack(side=tk.LEFT)
        self.custom.insert(0, initial or "#7c3aed")
        self.custom.bind("<KeyRelease>",
                         lambda _e: self._refresh())
        tk.Button(bottom, text=tr("cvdlab.copy_hex"), relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_custom).pack(side=tk.RIGHT,
                                                  padx=8, pady=4)
        self.custom_out = tk.Label(bottom, text="", width=10,
                                   bg=t.get("bg", "#16161e"),
                                   fg=t.get("text", "#e8e8f0"))
        self.custom_out.pack(side=tk.RIGHT, padx=4)

        self._swatch_widgets = []
        self._refresh()

    # ------------------------------------------------------------ actions
    def _sev(self):
        try:
            return float(self.severity.get()) / 100.0
        except Exception:
            return 1.0

    def _refresh(self):
        """Rebuild the swatch grid + verdict. Never raises."""
        try:
            for w in self._swatch_widgets:
                try:
                    w.destroy()
                except Exception:
                    pass
            self._swatch_widgets = []
            kind = self.kind.get()
            sev = self._sev()
            pal = self.theme   # dict or Theme-like — engine handles both
            for key, orig, sim in swatch_rows(pal, kind, sev):
                row = tk.Frame(self.grid, bg=self.theme.get(
                    "bg", "#16161e"))
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=key, width=16, anchor="w",
                         bg=self.theme.get("bg", "#16161e"),
                         fg=self.theme.get("text_muted", "#8a8a9a")
                         ).pack(side=tk.LEFT)
                for color in (orig, sim):
                    chip = tk.Label(row, text=color, width=14,
                                    bg=color,
                                    fg="#ffffff" if self._dark(color)
                                    else "#000000")
                    chip.pack(side=tk.LEFT, padx=4)
                    self._swatch_widgets.append(chip)
                self._swatch_widgets.append(row)
            self.verdict.configure(
                text=survive_line(pal, kind, sev),
                fg=self.theme.get("success", "#3fb950"))
            sim_hex = simulate_hex(self.custom.get(), kind, sev)
            self.custom_out.configure(
                text=sim_hex or "n/a",
                bg=sim_hex or self.theme.get("bg", "#16161e"),
                fg="#ffffff" if sim_hex and self._dark(sim_hex)
                else "#000000" if sim_hex
                else self.theme.get("text_muted", "#8a8a9a"))
        except Exception:  # noqa: BLE001 — window stays alive
            try:
                self.verdict.configure(text="preview failed")
            except Exception:
                pass

    @staticmethod
    def _dark(hex_color):
        rgb = hex_to_rgb(hex_color)
        if not rgb:
            return True
        r, g, b = rgb
        return (0.299 * r + 0.587 * g + 0.114 * b) < 140

    def _copy_custom(self):
        try:
            sim = simulate_hex(self.custom.get(), self.kind.get(),
                               self._sev())
            if not sim:
                self.custom_out.configure(text="n/a")
                return
            self.clipboard_clear()
            self.clipboard_append(sim)
            self.custom_out.configure(text=sim)
        except Exception:  # noqa: BLE001
            pass

    def refresh(self):
        self._refresh()


def open_cvdlab(parent, theme, initial=""):
    """Public entry — open the Colorblind Lab window."""
    return ColorblindLab(parent, theme, initial=initial)


if __name__ == "__main__":  # pragma: no cover — engine demo
    from dxn1_studio.theme import PALETTES
    for kind in KINDS:
        print("%-14s %s" % (kind, survive_line(PALETTES["dark"], kind)))
