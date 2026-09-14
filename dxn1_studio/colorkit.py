"""DS2 Color Kit — hex/rgb/hsl conversion, contrast, shade ramps.

A compact color workbench for UI development: paste any color,
get every format back (hex, rgb(), hsl(), tkinter-friendly),
check WCAG contrast against white/black/text, and generate shade
ramps for themes.

Engine (colorkit functions) is pure and unit-tested; the window
never raises on weird input.

Open with: Workshop menu, palette, terminal ``color`` / ``colorkit``.
"""

import colorsys
import re
import tkinter as tk

__all__ = ["normalize_hex", "hex_to_rgb", "rgb_to_hex", "rgb_to_hsl",
           "hsl_to_rgb", "relative_luminance", "contrast_ratio",
           "lighten", "darken", "mix", "shade_ramp", "ColorKit",
           "open_colorkit"]

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_hex(value):
    """Return ``#rrggbb`` lowercase, or None when unparseable.

    Accepts ``#abc`` short form, ``aabbcc`` without hash, extra
    whitespace; None for anything else (never raises).
    """
    if not isinstance(value, str):
        return None
    m = _HEX_RE.match(value.strip())
    if not m:
        return None
    hexpart = m.group(1)
    if len(hexpart) == 3:
        hexpart = "".join(ch * 2 for ch in hexpart)
    return "#" + hexpart.lower()


def hex_to_rgb(value):
    """``#rrggbb`` → (r, g, b) ints 0-255, or None when bad."""
    norm = normalize_hex(value)
    if not norm:
        return None
    return tuple(int(norm[i:i + 2], 16) for i in (1, 3, 5))


def rgb_to_hex(r, g, b):
    """(r, g, b) ints → ``#rrggbb`` (clamped to 0-255)."""
    def _cl(v):
        return max(0, min(255, int(round(float(v)))))
    return "#%02x%02x%02x" % (_cl(r), _cl(g), _cl(b))


def rgb_to_hsl(r, g, b):
    """(r, g, b) 0-255 → (h, s, l) floats — h in 0-360, s/l in 0-100,
    one decimal of precision (round-trips back to the same rgb)."""
    h, lig, sat = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return (round(h * 360, 1) % 360, round(sat * 100, 1),
            round(lig * 100, 1))


def hsl_to_rgb(h, s, l):
    """(h 0-360, s 0-100, l 0-100) → (r, g, b) 0-255."""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0,
                                  max(0.0, min(1.0, l / 100.0)),
                                  max(0.0, min(1.0, s / 100.0)))
    return (round(r * 255), round(g * 255), round(b * 255))


def relative_luminance(r, g, b):
    """WCAG 2.x relative luminance of an (r, g, b) 0-255 triple."""
    def _chan(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.04045 else \
            ((v + 0.055) / 1.055) ** 2.4
    return (0.2126 * _chan(r) + 0.7152 * _chan(g)
            + 0.0722 * _chan(b))


def contrast_ratio(fg, bg):
    """WCAG contrast ratio (1.0-21.0) between two hex colors."""
    rgb1 = hex_to_rgb(fg)
    rgb2 = hex_to_rgb(bg)
    if not rgb1 or not rgb2:
        return 0.0
    l1 = relative_luminance(*rgb1)
    l2 = relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def lighten(value, amount):
    """Lighten a hex color by ``amount`` percent (0-100)."""
    rgb = hex_to_rgb(value)
    if not rgb:
        return None
    h, s, l = rgb_to_hsl(*rgb)
    return rgb_to_hex(*hsl_to_rgb(h, s, min(100, l + amount)))


def darken(value, amount):
    """Darken a hex color by ``amount`` percent (0-100)."""
    return lighten(value, -abs(amount))


def mix(value_a, value_b, weight=0.5):
    """Blend two hex colors; weight 0 → a, 1 → b."""
    a = hex_to_rgb(value_a)
    b = hex_to_rgb(value_b)
    if not a or not b:
        return None
    w = max(0.0, min(1.0, float(weight)))
    return rgb_to_hex(*(a[i] + (b[i] - a[i]) * w for i in range(3)))


def shade_ramp(value, steps=9):
    """A light→dark ramp through the color, ends are white/black-ish.

    Returns a list of hex strings; the middle steps hover around the
    original hue. Deterministic, never raises (bad input → []).
    """
    rgb = hex_to_rgb(value)
    if not rgb or steps < 2:
        return []
    h, s, l = rgb_to_hsl(*rgb)
    out = []
    for i in range(steps):
        t = i / (steps - 1)                    # 0 → 1
        lig = 97.0 - t * 92.0                  # 97% → 5%
        sat = s if 10 <= lig <= 90 else max(0, s - 30)
        out.append(rgb_to_hex(*hsl_to_rgb(h, sat, lig)))
    mid = steps // 2
    out[mid] = normalize_hex(value) or out[mid]
    return out


SAMPLE_PALETTE = "#7c3aed"


class ColorKit(tk.Toplevel):
    """Color conversion + contrast + ramp workbench."""

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Color Kit — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("560x560")
        self.minsize(460, 460)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="color", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(
            side=tk.LEFT, padx=(10, 4), pady=8)
        self.entry = tk.Entry(top, width=16,
                              bg=t.get("editor_bg", "#1a1a24"),
                              fg=t.get("text", "#e8e8f0"),
                              insertbackground=t.get("text", "#fff"),
                              relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT, padx=4)
        self.entry.insert(0, initial or SAMPLE_PALETTE)
        self.entry.bind("<KeyRelease>", lambda _e: self.refresh())
        self.swatch = tk.Label(top, width=6, bg=self._base())
        self.swatch.pack(side=tk.LEFT, padx=8, pady=4)

        self.info = tk.Label(self, justify=tk.LEFT, anchor="w",
                             bg=t.get("bg", "#16161e"),
                             fg=t.get("text", "#e8e8f0"))
        self.info.pack(fill=tk.X, padx=12, pady=(10, 4))

        self.contrast = tk.Label(self, justify=tk.LEFT, anchor="w",
                                 bg=t.get("bg", "#16161e"),
                                 fg=t.get("text", "#e8e8f0"))
        self.contrast.pack(fill=tk.X, padx=12, pady=4)

        self.ramp = tk.Frame(self, bg=t.get("bg", "#16161e"))
        self.ramp.pack(fill=tk.X, padx=12, pady=6)
        self.ramp_label = tk.Label(
            self, text="shade ramp — click a chip to copy",
            anchor="w", bg=t.get("bg", "#16161e"),
            fg=t.get("text_muted", "#8a8a9a"))
        self.ramp_label.pack(fill=tk.X, padx=12)

        self.status = tk.Label(self, anchor="w",
                               bg=t.get("header", "#242432"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        self.bind("<Escape>", lambda _e: self.destroy())
        self.refresh()

    # ------------------------------------------------------- actions
    def _base(self):
        norm = normalize_hex(self.entry.get())
        return norm or "#000000"

    def refresh(self):
        """Recompute every panel (never raises)."""
        try:
            raw = self.entry.get()
            norm = normalize_hex(raw)
            rgb = hex_to_rgb(raw)
            self.swatch.configure(bg=norm or "#000000")
            if not norm or not rgb:
                self.info.configure(
                    text="enter a color: #7c3aed, 7c3aed, #abc …")
                self.contrast.configure(text="")
                for w in self.ramp.winfo_children():
                    w.destroy()
                return
            h, s, l = rgb_to_hsl(*rgb)
            self.info.configure(text=(
                "hex  %s\nrgb  rgb(%d, %d, %d)\nhsl  hsl(%d, %d%%, %d%%)"
                "\ntk   %s" % (norm, rgb[0], rgb[1], rgb[2],
                               h, s, l, norm.upper())))
            cw = contrast_ratio(norm, "#ffffff")
            cb = contrast_ratio(norm, "#000000")
            best = "white" if cw >= cb else "black"
            self.contrast.configure(text=(
                "contrast vs white  %.2f:1   vs black  %.2f:1\n"
                "AA text needs 4.5 — best partner: %s"
                % (cw, cb, best)))
            for w in self.ramp.winfo_children():
                w.destroy()
            for shade in shade_ramp(norm):
                chip = tk.Label(self.ramp, bg=shade, width=6, height=2,
                                text="", cursor="hand2")
                chip.pack(side=tk.LEFT, padx=1)
                chip.bind("<Button-1>",
                          lambda _e, v=shade: self._copy(v))
            self._flash("%s — chips copy the hex" % norm)
        except Exception:  # noqa: BLE001 — the workbench stays alive
            pass

    def _copy(self, value):
        try:
            self.clipboard_clear()
            self.clipboard_append(value)
            self._flash("copied %s" % value)
        except Exception:  # noqa: BLE001
            self._flash("clipboard unavailable")

    def _flash(self, msg):
        try:
            self.status.configure(text=msg)
        except Exception:  # noqa: BLE001
            pass


def open_colorkit(parent, theme, initial=""):
    """Public opener — palette / menu / terminal entry point."""
    return ColorKit(parent, theme, initial=initial)
