"""DS2 Unit Converter — instant, offline, honest.

Convert length, mass, temperature, data size, duration and speed
with a pure engine (exact factor tables, temperature handled by real
formulas) and a compact live window: pick a category, type a value,
read every unit at once. Junk input shows a friendly dash instead of
crashing or lying.

Engine (convert / convert_str / batch_table) is pure and unit-tested;
the window never raises.

Open with: Workshop menu, palette, terminal ``unit`` / ``convert``.
"""

import tkinter as tk
from tkinter import ttk

from . import hints
from .i18n import tr

__all__ = ["categories", "units", "convert", "convert_str",
           "batch_table", "UnitConverter", "open_unit_converter"]

# ----------------------------------------------------------- factor data
# All tables convert TO the base unit; conversion = v * from / to.

_LENGTH = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
           "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
_MASS = {"mg": 1e-6, "g": 0.001, "kg": 1.0, "t": 1000.0,
         "oz": 0.028349523125, "lb": 0.45359237}
_DATA = {"B": 1.0, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12,
         "KiB": 1024.0, "MiB": 1024.0 ** 2, "GiB": 1024.0 ** 3,
         "TiB": 1024.0 ** 4}
_TIME = {"ms": 0.001, "s": 1.0, "min": 60.0, "h": 3600.0,
         "d": 86400.0, "week": 604800.0}
_SPEED = {"m/s": 1.0, "km/h": 1.0 / 3.6, "mph": 0.44704,
          "knot": 0.514444}

TABLES = {
    "length": _LENGTH,
    "mass": _MASS,
    "data": _DATA,
    "time": _TIME,
    "speed": _SPEED,
    "temperature": {"C": None, "F": None, "K": None},  # formula-based
}


def categories():
    """Sorted category names."""
    return sorted(TABLES)


def units(cat):
    """Sorted unit names for a category; unknown → []."""
    table = TABLES.get(cat) if isinstance(cat, str) else None
    return sorted(table) if table else []


def _to_celsius(value, unit):
    if unit == "C":
        return value
    if unit == "F":
        return (value - 32.0) * 5.0 / 9.0
    if unit == "K":
        return value - 273.15
    return None


def _from_celsius(c, unit):
    if unit == "C":
        return c
    if unit == "F":
        return c * 9.0 / 5.0 + 32.0
    if unit == "K":
        return c + 273.15
    return None


def convert(value, frm, to, cat=None):
    """Convert *value* from unit *frm* to unit *to*. Returns a float
    or None on junk/unknown units. Temperature auto-detected."""
    if cat is None:
        cat = _detect_cat(frm, to)
    table = TABLES.get(cat) if isinstance(cat, str) else None
    if table is None or frm not in table or to not in table:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        try:
            value = float(str(value).strip())
        except (TypeError, ValueError):
            return None
    if cat == "temperature":
        c = _to_celsius(float(value), frm)
        if c is None:
            return None
        return _from_celsius(c, to)
    return float(value) * table[frm] / table[to]


def _detect_cat(frm, to):
    for cat, table in TABLES.items():
        if frm in table and to in table:
            return cat
    # ambiguous unit (e.g. "m" only in length) → fine, first hit wins
    for cat, table in TABLES.items():
        if frm in table or to in table:
            return cat
    return None


def convert_str(value, frm, to):
    """Formatted conversion or '—' on junk. Never raises."""
    result = convert(value, frm, to)
    if result is None:
        return "—"
    return "%g %s" % (result, to)


def batch_table(value, frm, cat):
    """[(unit, float_value)] for every unit in a category, or None."""
    table = TABLES.get(cat) if isinstance(cat, str) else None
    if table is None or frm not in table:
        return None
    out = []
    for unit in sorted(table):
        if unit == frm:
            out.append((unit, float(value) if _is_num(value) else None))
            continue
        out.append((unit, convert(value, frm, unit, cat=cat)))
    return out


def _is_num(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    try:
        float(str(value).strip())
        return True
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------- window

SAMPLE_VALUE = "2.5"


class UnitConverter(tk.Toplevel):
    """Live unit conversion window. Never raises on junk input."""

    CATS = ("length", "mass", "temperature", "data", "time", "speed")

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Unit Converter — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("560x460")
        self.minsize(460, 380)
        try:
            self.transient(parent)
        except Exception:
            pass

        head = tk.Frame(self, bg=t.get("header", "#242432"))
        head.pack(fill=tk.X)
        tk.Label(head, text="unit converter",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=(10, 8), pady=8)
        self.cat = tk.StringVar(value="length")
        for c in self.CATS:
            tk.Radiobutton(head, text=c, value=c, variable=self.cat,
                           command=self._recat, bg=t.get("header",
                                                         "#242432"),
                           fg=t.get("text", "#e8e8f0"),
                           selectcolor=t.get("editor_bg", "#1a1a24"),
                           activebackground=t.get("header", "#242432"),
                           activeforeground=t.get("text", "#e8e8f0"),
                           highlightthickness=0).pack(side=tk.LEFT,
                                                      padx=2)

        row = tk.Frame(self, bg=t.get("bg", "#16161e"))
        row.pack(fill=tk.X, padx=12, pady=(12, 4))
        self.value = tk.StringVar(value=SAMPLE_VALUE)
        entry = tk.Entry(row, textvariable=self.value, width=12,
                         bg=t.get("editor_bg", "#1a1a24"),
                         fg=t.get("text", "#e8e8f0"),
                         insertbackground=t.get("text", "#fff"),
                         relief=tk.FLAT, font=("TkDefaultFont", 12))
        entry.pack(side=tk.LEFT)
        entry.bind("<KeyRelease>", lambda _e: self.refresh())
        self.frm = ttk.Combobox(row, width=8, state="readonly")
        self.frm.pack(side=tk.LEFT, padx=6)
        self.frm.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        tk.Button(row, text="⇄ swap", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._swap).pack(side=tk.LEFT, padx=2)
        self.to = ttk.Combobox(row, width=8, state="readonly")
        self.to.pack(side=tk.LEFT, padx=6)
        self.to.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self.result = tk.Label(self, anchor="w", justify=tk.LEFT,
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("accent", "#7aa2f7"),
                               font=("TkDefaultFont", 15, "bold"))
        self.result.pack(fill=tk.X, padx=14, pady=(6, 2))

        tk.Label(self, text="all units in this category",
                 anchor="w", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(
            fill=tk.X, padx=14, pady=(8, 0))
        self.table = tk.Label(self, anchor="nw", justify=tk.LEFT,
                              bg=t.get("bg", "#16161e"),
                              fg=t.get("text", "#e8e8f0"),
                              font=("TkFixedFont", 10))
        self.table.pack(fill=tk.BOTH, expand=True, padx=14, pady=(2, 4))

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text="ready", anchor="w",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text=tr("unit.copy_result"), relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy).pack(side=tk.RIGHT, padx=8,
                                           pady=4)

        # keys first advertised by the bar below (v2.50 wave 3)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-r>", lambda _e: self._swap())
        self.bind("<Control-C>", lambda _e: self._copy())
        hints.hint_bar(self, t,
                       pairs=[("Ctrl+R", "swap units"),
                              ("Ctrl+Shift+C", "copy result")])

        self._recat()

    # ---------------------------------------------------- behaviour
    def _recat(self):
        cat = self.cat.get()
        opts = units(cat)
        if not opts:
            return
        self.frm["values"] = opts
        self.to["values"] = opts
        keep_f = self.frm.get() if self.frm.get() in opts else None
        keep_t = self.to.get() if self.to.get() in opts else None
        defaults = {"length": ("m", "ft"), "mass": ("kg", "lb"),
                    "temperature": ("C", "F"), "data": ("MB", "MiB"),
                    "time": ("min", "h"), "speed": ("km/h", "mph")}
        d_f, d_t = defaults.get(cat, (opts[0], opts[-1]))
        self.frm.set(keep_f or d_f)
        self.to.set(keep_t or d_t)
        self.refresh()

    def _swap(self):
        f, t = self.frm.get(), self.to.get()
        self.frm.set(t)
        self.to.set(f)
        self.refresh()

    def refresh(self):
        """Live recompute. Junk-tolerant by design — never raises."""
        try:
            cat = self.cat.get()
            raw = self.value.get()
            num = None
            if _is_num(raw):
                num = float(str(raw).strip())
            if num is None:
                self.result.config(
                    text="—  (type a number, junk is tolerated)")
                self.table.config(text="")
                self.status.config(text="waiting for a number")
                return
            frm, to = self.frm.get(), self.to.get()
            self.result.config(
                text="%s %s  =  %s" % ("%g" % num, frm,
                                       convert_str(num, frm, to)))
            rows = batch_table(num, frm, cat) or []
            lines = []
            for unit, val in rows:
                shown = "—" if val is None else "%g" % val
                mark = " ←" if unit == frm else ""
                lines.append("  %-6s %s%s" % (unit, shown, mark))
            self.table.config(text="\n".join(lines) or " ")
            self.status.config(text="%s · %d units · offline" %
                               (cat, len(rows)))
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.result.cget("text"))
            self.status.config(text="result copied to clipboard")
        except Exception:
            pass


def open_unit_converter(parent, theme):
    """Public entry: open the Unit Converter window. Never raises."""
    try:
        win = UnitConverter(parent, theme)
        win.grab_release()
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
