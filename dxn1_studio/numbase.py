"""DS2 NumBase — number base workbench.

Type a value in any base (2–36, with the classic 0x / 0o / 0b
prefixes accepted) and read it simultaneously as binary, octal,
decimal, hex and any custom base — plus a bit-level inspector
(bit length, popcount, byte split). A staple for systems work.

Engine (parse_number / format_base / inspect_bits) is pure and
unit-tested; the window never raises on weird input.

Open with: Workshop menu, palette, terminal ``numbase`` / ``base``.
"""

import tkinter as tk

__all__ = ["parse_number", "format_base", "inspect_bits",
           "NumBase", "open_numbase"]

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"

_PREFIXES = {"0x": 16, "0o": 8, "0b": 2}


def parse_number(text, base=10):
    """Parse an integer in the given base (2–36). Returns int or None.

    Accepts optional +/- sign, underscores as digit separators, and
    the classic 0x/0o/0b prefixes (which override *base*). Junk,
    floats and out-of-range bases → None. Never raises.
    """
    if not isinstance(text, str):
        return None
    try:
        base = int(base)
    except (TypeError, ValueError):
        return None
    if base < 2 or base > 36:
        return None
    raw = text.strip().lower().replace("_", "")
    if not raw:
        return None
    sign = 1
    if raw[0] in "+-":
        sign = -1 if raw[0] == "-" else 1
        raw = raw[1:]
    if not raw:
        return None
    for prefix, pbase in _PREFIXES.items():
        if raw.startswith(prefix):
            base = pbase
            raw = raw[len(prefix):]
            break
    if not raw:
        return None
    value = 0
    for ch in raw:
        digit = _DIGITS.find(ch)
        if digit < 0 or digit >= base:
            return None
        value = value * base + digit
    return sign * value


def format_base(value, base):
    """Format a positive-or-negative int in *base* (2–36).

    Negative values keep a leading '-'; junk → ''.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return ""
    try:
        base = int(base)
    except (TypeError, ValueError):
        return ""
    if base < 2 or base > 36:
        return ""
    if value == 0:
        return "0"
    negative = value < 0
    value = abs(value)
    out = []
    while value:
        value, digit = divmod(value, base)
        out.append(_DIGITS[digit])
    return ("-" if negative else "") + "".join(reversed(out))


def inspect_bits(value):
    """Bit-level facts for an int. Junk → {}.

    Returns bit_length, popcount (ones), hex bytes (big-endian) and
    the two's-complement note for negatives.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return {}
    if value == 0:
        return {"bit_length": 0, "ones": 0, "hex": "0x00",
                "note": "zero"}
    magnitude = abs(value)
    bits = magnitude.bit_length()
    ones = bin(magnitude).count("1")
    nbytes = max(1, (bits + 7) // 8)
    try:
        hexbytes = "0x" + magnitude.to_bytes(
            nbytes, "big").hex()
    except OverflowError:  # pragma: no cover — magnitude is bounded
        hexbytes = "0x?"
    note = ("negative — two's complement needs %d bits"
            % (bits + 1)) if value < 0 else "positive"
    return {"bit_length": bits, "ones": ones, "hex": hexbytes,
            "note": note}


# --------------------------------------------------------------- window

class NumBase(tk.Toplevel):
    """Live number-base conversion window. Never raises on junk."""

    BASES = ("2", "8", "10", "16", "3", "4", "5", "6", "7", "9",
             "11", "12", "20", "32", "36")

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("NumBase — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("520x430")
        # DS2 v2.62 — width accounting round four: once the build
        # settles, open no narrower (or shorter) than what it
        # actually packed (the 520x430 default is the floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 520, 430))
        self.minsize(430, 340)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="numbase", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=(10, 8), pady=8)
        tk.Label(top, text="input base", bg=t.get("header", "#242432"),
                 fg=t.get("text", "#e8e8f0")).pack(side=tk.LEFT)
        self.in_base = tk.StringVar(value="10")
        spin = tk.Spinbox(top, from_=2, to=36, width=4,
                          textvariable=self.in_base, command=self.refresh,
                          relief=tk.FLAT,
                          bg=t.get("editor_bg", "#1a1a24"),
                          fg=t.get("text", "#e8e8f0"),
                          buttonbackground=t.get("button", "#2a2a3a"),
                          insertbackground=t.get("text", "#fff"))
        spin.pack(side=tk.LEFT, padx=6, pady=6)
        spin.bind("<KeyRelease>", lambda _e: self.refresh())

        self.entry = tk.Entry(self, font=("TkFixedFont", 13),
                              relief=tk.FLAT,
                              bg=t.get("editor_bg", "#1a1a24"),
                              fg=t.get("text", "#e8e8f0"),
                              insertbackground=t.get("text", "#fff"))
        self.entry.pack(fill=tk.X, padx=12, pady=(12, 2), ipady=5)
        self.entry.insert(0, initial or "255")
        self.entry.bind("<KeyRelease>", lambda _e: self.refresh())

        self.rows = tk.Frame(self, bg=t.get("bg", "#16161e"))
        self.rows.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        self.labels = {}
        for base in self.BASES:
            row = tk.Frame(self.rows, bg=t.get("bg", "#16161e"))
            row.pack(fill=tk.X, pady=2)
            name = tk.Label(row, text="base %s" % base, width=9,
                            anchor="w", bg=t.get("bg", "#16161e"),
                            fg=t.get("accent", "#7aa2f7"),
                            font=("TkFixedFont", 10, "bold"))
            name.pack(side=tk.LEFT)
            value = tk.Label(row, text="—", anchor="w",
                             bg=t.get("bg", "#16161e"),
                             fg=t.get("text", "#e8e8f0"),
                             font=("TkFixedFont", 11), cursor="hand2")
            value.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            value.bind("<Button-1>",
                       lambda _e, b=base: self._copy(b))
            self.labels[base] = value

        self.bits = tk.Label(self, justify=tk.LEFT, anchor="w",
                             bg=t.get("bg", "#16161e"),
                             fg=t.get("text_muted", "#8a8a9a"),
                             font=("TkFixedFont", 10))
        self.bits.pack(fill=tk.X, padx=12, pady=(4, 0))

        self.status = tk.Label(self, text="click any row to copy",
                               anchor="w", bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.refresh()

    # ---------------------------------------------------- behaviour
    def refresh(self):
        """Recompute every base. Junk-tolerant by design — never raises."""
        try:
            value = parse_number(self.entry.get(), self.in_base.get())
            if value is None:
                for label in self.labels.values():
                    label.config(text="—")
                self.bits.config(text="")
                self.status.config(text="not a valid base-%s number"
                                   % self.in_base.get())
                return
            for base, label in self.labels.items():
                label.config(text=format_base(value, int(base)))
            info = inspect_bits(value)
            if info:
                self.bits.config(
                    text="bit length {bit_length} · ones {ones} · "
                         "hex bytes {hex} · {note}".format(**info))
            self.status.config(text="click any row to copy")
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _copy(self, base):
        try:
            text = self.labels[base].cget("text")
            if text == "—":
                return
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text="base %s copied: %s" % (base, text))
        except Exception:
            pass


def open_numbase(parent, theme, initial=""):
    """Public entry: open the NumBase window. Never raises."""
    try:
        win = NumBase(parent, theme, initial=initial)
        win.grab_release()
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
