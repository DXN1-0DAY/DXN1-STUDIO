"""DS2 PassForge — cryptographic password generator with an entropy meter.

Generate passwords from toggled character classes (upper/lower/digits/
symbols, ambiguous glyphs excluded on request) using the stdlib
``secrets`` module — real CSPRNG, no home-made randomness. The engine
also computes Shannon entropy (``length * log2(pool)``) and maps it to
an honest strength label.

Engine (generate / entropy_bits / strength_label) is pure and
unit-tested (deterministic via an injected rng); the window never
raises.

Open with: Workshop menu, palette, terminal ``passgen`` / ``password``.
"""

import math
import secrets
import string
import tkinter as tk

__all__ = ["pool_for", "generate", "entropy_bits", "strength_label",
           "PassForge", "open_passforge"]

_UPPER = string.ascii_uppercase
_LOWER = string.ascii_lowercase
_DIGITS = string.digits
_SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"
_AMBIGUOUS = set("Il1O0o`'\"|")


def pool_for(upper=True, lower=True, digits=True, symbols=False,
             exclude_ambiguous=False):
    """Character pool for the toggled classes. Empty toggles → ''."""
    chars = ""
    if upper:
        chars += _UPPER
    if lower:
        chars += _LOWER
    if digits:
        chars += _DIGITS
    if symbols:
        chars += _SYMBOLS
    if exclude_ambiguous:
        chars = "".join(c for c in chars if c not in _AMBIGUOUS)
    return chars


def generate(length=16, upper=True, lower=True, digits=True,
             symbols=False, exclude_ambiguous=False, rng=None):
    """A random password, or '' when no class is toggled / junk input.

    Pass ``rng`` (an object with a ``choice`` method) for
    deterministic tests; production paths use ``secrets``.
    """
    try:
        length = int(length)
    except (TypeError, ValueError):
        return ""
    if length < 1 or length > 256:
        return ""
    pool = pool_for(upper, lower, digits, symbols, exclude_ambiguous)
    if not pool:
        return ""
    chooser = rng.choice if rng is not None else secrets.choice
    return "".join(chooser(pool) for _ in range(length))


def entropy_bits(length, upper=True, lower=True, digits=True,
                 symbols=False, exclude_ambiguous=False):
    """Shannon entropy in bits: length * log2(pool). No pool → 0.0."""
    try:
        length = int(length)
    except (TypeError, ValueError):
        return 0.0
    pool = pool_for(upper, lower, digits, symbols, exclude_ambiguous)
    if not pool or length < 1:
        return 0.0
    return round(length * math.log2(len(pool)), 1)


def strength_label(bits):
    """Honest label for an entropy value. Junk → 'very weak'."""
    try:
        bits = float(bits)
    except (TypeError, ValueError):
        return "very weak"
    if bits <= 0:
        return "very weak"
    if bits < 28:
        return "weak"
    if bits < 36:
        return "fair"
    if bits < 60:
        return "strong"
    if bits < 128:
        return "excellent"
    return "overkill"


# --------------------------------------------------------------- window

class PassForge(tk.Toplevel):
    """Password generator window. Never raises on weird input."""

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("PassForge — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("520x360")
        self.minsize(440, 300)
        try:
            self.transient(parent)
        except Exception:
            pass

        head = tk.Frame(self, bg=t.get("header", "#242432"))
        head.pack(fill=tk.X)
        tk.Label(head, text="passforge", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=(10, 8), pady=8)
        tk.Label(head, text="length", bg=t.get("header", "#242432"),
                 fg=t.get("text", "#e8e8f0")).pack(side=tk.LEFT)
        self.length = tk.IntVar(value=20)
        spin = tk.Spinbox(head, from_=4, to=128, width=5,
                          textvariable=self.length,
                          command=self.refresh, relief=tk.FLAT,
                          bg=t.get("editor_bg", "#1a1a24"),
                          fg=t.get("text", "#e8e8f0"),
                          buttonbackground=t.get("button", "#2a2a3a"),
                          insertbackground=t.get("text", "#fff"))
        spin.pack(side=tk.LEFT, padx=6, pady=6)
        spin.bind("<KeyRelease>", lambda _e: self.refresh())

        opts = tk.Frame(self, bg=t.get("bg", "#16161e"))
        opts.pack(fill=tk.X, padx=12, pady=(10, 2))
        self.upper = tk.BooleanVar(value=True)
        self.lower = tk.BooleanVar(value=True)
        self.digits = tk.BooleanVar(value=True)
        self.symbols = tk.BooleanVar(value=False)
        self.no_ambig = tk.BooleanVar(value=False)
        for text, var in (("A-Z", self.upper), ("a-z", self.lower),
                          ("0-9", self.digits), ("!@#", self.symbols),
                          ("no Il1O0o", self.no_ambig)):
            tk.Checkbutton(opts, text=text, variable=var,
                           command=self.refresh,
                           bg=t.get("bg", "#16161e"),
                           fg=t.get("text", "#e8e8f0"),
                           selectcolor=t.get("editor_bg", "#1a1a24"),
                           activebackground=t.get("bg", "#16161e"),
                           activeforeground=t.get("text", "#e8e8f0"),
                           highlightthickness=0).pack(side=tk.LEFT,
                                                      padx=3)

        self.out = tk.Entry(self, font=("TkFixedFont", 13),
                            justify=tk.CENTER, relief=tk.FLAT,
                            bg=t.get("editor_bg", "#1a1a24"),
                            fg=t.get("accent", "#7aa2f7"),
                            insertbackground=t.get("text", "#fff"))
        self.out.pack(fill=tk.X, padx=12, pady=(8, 2), ipady=6)

        self.strength = tk.Label(self, anchor="center",
                                 bg=t.get("bg", "#16161e"),
                                 fg=t.get("text", "#e8e8f0"))
        self.strength.pack(fill=tk.X, pady=(2, 4))

        btns = tk.Frame(self, bg=t.get("bg", "#16161e"))
        btns.pack(fill=tk.X)
        tk.Button(btns, text="generate", relief=tk.FLAT,
                  bg=t.get("accent", "#7aa2f7"),
                  fg="#ffffff" if t.get("is_dark", True) else "#16161e",
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self.refresh).pack(side=tk.LEFT, padx=12,
                                             pady=6)
        tk.Button(btns, text="copy", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy).pack(side=tk.LEFT, padx=2)

        self.status = tk.Label(btns, text="secrets CSPRNG", anchor="e",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.RIGHT, padx=10)

        self.refresh()

    # ---------------------------------------------------- behaviour
    def refresh(self):
        """Generate a fresh password + entropy readout. Never raises."""
        try:
            pwd = generate(self.length.get(),
                           self.upper.get(), self.lower.get(),
                           self.digits.get(), self.symbols.get(),
                           self.no_ambig.get())
            if not pwd:
                self.out.delete(0, "end")
                self.out.insert(0, "toggle at least one class")
                self.strength.config(text="")
                self.status.config(text="waiting for options")
                return
            self.out.delete(0, "end")
            self.out.insert(0, pwd)
            bits = entropy_bits(self.length.get(),
                                self.upper.get(), self.lower.get(),
                                self.digits.get(), self.symbols.get(),
                                self.no_ambig.get())
            self.strength.config(
                text="%s  ·  %.1f bits of entropy"
                     % (strength_label(bits), bits))
            self.status.config(text="secrets CSPRNG")
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (options kept)")

    def _copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.out.get())
            self.status.config(text="copied to clipboard")
        except Exception:
            pass


def open_passforge(parent, theme):
    """Public entry: open the PassForge window. Never raises."""
    try:
        win = PassForge(parent, theme)
        win.grab_release()
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
