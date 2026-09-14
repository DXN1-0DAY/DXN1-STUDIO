"""DS2 MathPad — a safe expression calculator.

Type arithmetic, get answers. The engine evaluates Python-like
expressions through the ``ast`` module with a strict whitelist —
no ``eval``, no attribute access, no imports — so pasted junk can
only ever produce an error message, never side effects.

Supported: ``+ - * / // % **`` (``^`` accepted as power), unary
``- +``, parentheses, constants (``pi e tau inf``), 26 functions
(``sqrt cbrt log log2 log10 exp sin cos tan abs round floor ceil
factorial gcd …``), hex/binary literals and ``1_000`` separators.

Engine (evaluate / fmt / CalcError) is pure and unit-tested; the
window adds variables (``x = 5`` then ``x*2``), an ``_`` last-answer
name, history with click-to-copy and never raises on junk input.

Open with: Workshop menu, palette, terminal ``calc`` / ``math``.
"""

import ast
import math
import re
import tkinter as tk

from .i18n import tr

__all__ = ["CalcError", "evaluate", "fmt", "FUNCTIONS", "CONSTANTS",
           "MathPad", "open_mathpad"]


class CalcError(ValueError):
    """Raised for any expression the safe evaluator refuses."""


def _fact(n):
    if isinstance(n, float):
        if not n.is_integer():
            raise CalcError("factorial needs a whole number")
        n = int(n)
    if n < 0 or n > 10_000:
        raise CalcError("factorial limited to 0..10000")
    return math.factorial(n)


def _cbrt(x):
    # real cube root for negatives too
    return -((-x) ** (1.0 / 3.0)) if x < 0 else x ** (1.0 / 3.0)


CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau,
             "inf": math.inf, "nan": math.nan}

FUNCTIONS = {
    "sqrt": math.sqrt, "cbrt": _cbrt, "abs": abs, "round": round,
    "floor": math.floor, "ceil": math.ceil, "trunc": math.trunc,
    "exp": math.exp, "log": math.log, "log2": math.log2,
    "log10": math.log10, "sin": math.sin, "cos": math.cos,
    "tan": math.tan, "asin": math.asin, "acos": math.acos,
    "atan": math.atan, "atan2": math.atan2, "sinh": math.sinh,
    "cosh": math.cosh, "tanh": math.tanh, "degrees": math.degrees,
    "radians": math.radians, "gcd": math.gcd, "hypot": math.hypot,
    "min": min, "max": max, "factorial": _fact, "sign": lambda v: (
        0 if v == 0 else (1 if v > 0 else -1)),
}

_BINOPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
           ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
           ast.FloorDiv: lambda a, b: a // b,
           ast.Mod: lambda a, b: a % b, ast.Pow: lambda a, b: a ** b}

_MAX_EXPONENT = 10_000


def _parse(expr):
    """Common parse step; returns the AST tree or raises CalcError."""
    if not isinstance(expr, str) or not expr.strip():
        raise CalcError("type an expression")
    source = expr.strip().replace("^", "**")
    try:
        return ast.parse(source, mode="eval")
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        raise CalcError("could not read that expression") from None


def _eval_node(node, scope):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, scope)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(
                node.value, (int, float)):
            raise CalcError("only numbers go here (got %r)"
                            % (node.value,))
        return node.value
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise CalcError("operator not allowed")
        left = _eval_node(node.left, scope)
        right = _eval_node(node.right, scope)
        if isinstance(node.op, ast.Pow) and isinstance(right, int) \
                and abs(right) > _MAX_EXPONENT:
            raise CalcError("exponent too large (max %d)"
                            % _MAX_EXPONENT)
        try:
            result = op(left, right)
        except ZeroDivisionError:
            raise CalcError("division by zero") from None
        except OverflowError:
            raise CalcError("result too large") from None
        if isinstance(result, complex):
            raise CalcError("complex results not supported")
        return result
    if isinstance(node, ast.UnaryOp):
        val = _eval_node(node.operand, scope)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return +val
        raise CalcError("operator not allowed")
    if isinstance(node, ast.Name):
        if node.id in scope:
            return scope[node.id]
        raise CalcError("unknown name %r (try pi, e, tau)" % node.id)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or \
                node.func.id not in FUNCTIONS:
            raise CalcError("function not allowed")
        if node.keywords:
            raise CalcError("keyword arguments not supported")
        args = [_eval_node(a, scope) for a in node.args]
        try:
            result = FUNCTIONS[node.func.id](*args)
        except CalcError:
            raise
        except TypeError:
            raise CalcError("%s() got the wrong number of arguments"
                            % node.func.id) from None
        except ValueError:
            raise CalcError("%s() domain error (input out of range?)"
                            % node.func.id) from None
        except OverflowError:
            raise CalcError("%s() result too large"
                            % node.func.id) from None
        if isinstance(result, complex):
            raise CalcError("complex results not supported")
        return result
    raise CalcError("expression not allowed")


def evaluate(expr):
    """Evaluate *expr* safely and return an int or float.

    ``^`` is accepted as power, ``0xff`` / ``0b101`` / ``1_000``
    literals work. Raises :class:`CalcError` with a short human
    message for anything the whitelist refuses.
    """
    result = _eval_node(_parse(expr).body, dict(CONSTANTS))
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise CalcError("expression must produce a number")
    return result


def fmt(value):
    """Human-friendly number formatting. Never raises."""
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, int):
            return str(value)
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        if value == int(value) and abs(value) < 1e16:
            return str(int(value))
        return "%.12g" % value
    except Exception:  # noqa: BLE001 — formatting must never die
        return str(value)


# --------------------------------------------------------------- window

SAMPLE_EXPR = "sqrt(144) + 2^10 / 4"


class MathPad(tk.Toplevel):
    """Safe calculator window. Never raises on junk input."""

    CHIPS = ("sqrt(", "log(", "sin(", "cos(", "tan(", "floor(",
             "round(", "abs(", "factorial(", "pi", "e")

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme
        self.vars = {}
        self.last = None

        self.title("MathPad — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("560x470")
        self.minsize(430, 360)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="mathpad — safe expression calculator",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=10, pady=8)

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        tk.Label(body, text="expression  ( + - * / // % ^  ·  x = 5 "
                            "assigns  ·  _ is the last answer )",
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.entry = tk.Entry(body, font=("TkFixedFont", 13),
                              bg=t.get("editor_bg", "#1a1a24"),
                              fg=t.get("text", "#e8e8f0"),
                              insertbackground=t.get("text", "#fff"),
                              relief=tk.FLAT)
        self.entry.pack(fill=tk.X, pady=(4, 6))
        self.entry.insert(0, initial or SAMPLE_EXPR)
        self.entry.bind("<Return>", lambda _e: self.do_eval())
        self.entry.focus_set()

        chips = tk.Frame(body, bg=t.get("bg", "#16161e"))
        chips.pack(fill=tk.X)
        for label in self.CHIPS:
            tk.Button(chips, text=label, relief=tk.FLAT,
                      bg=t.get("button", "#2a2a3a"),
                      fg=t.get("text", "#e8e8f0"),
                      activebackground=t.get("button_hover",
                                             "#33334a"),
                      font=("TkDefaultFont", 8),
                      command=lambda s=label: self._insert_chip(s)
                      ).pack(side=tk.LEFT, padx=(0, 3), pady=(0, 6))

        self.result = tk.Label(body, text="=", anchor="w",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text", "#e8e8f0"),
                               font=("TkDefaultFont", 17, "bold"))
        self.result.pack(fill=tk.X, pady=(2, 6))

        tk.Label(body, text="history — %s" % tr("math.click_copy"),
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.history = tk.Listbox(body, height=8, activestyle="none",
                                  bg=t.get("editor_bg", "#1a1a24"),
                                  fg=t.get("text", "#e8e8f0"),
                                  relief=tk.FLAT)
        self.history.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.history.bind("<Button-1>", self._copy_row)

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text="ready", anchor="w",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text=tr("math.copy_result"), relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_result).pack(side=tk.RIGHT,
                                                  padx=8, pady=4)

        self.do_eval()

    # ---------------------------------------------------- behaviour
    def _insert_chip(self, text):
        try:
            self.entry.insert(tk.INSERT, text)
            self.entry.focus_set()
        except Exception:
            pass

    def _record(self, line):
        try:
            self.history.insert(0, line)
            if self.history.size() > 200:
                self.history.delete(200, "end")
        except Exception:
            pass

    def do_eval(self):
        """Evaluate the entry. Junk in → honest message, no crash."""
        try:
            expr = self.entry.get().strip()
            if not expr:
                self.result.config(
                    text="=", fg=self.theme.get("text_muted",
                                                "#8a8a9a"))
                self.status.config(text="type an expression")
                return
            scope = dict(CONSTANTS)
            scope.update(self.vars)
            scope["_"] = self.last if self.last is not None else 0
            scope["ans"] = scope["_"]

            assign = re.match(r"^([A-Za-z_]\w*)\s*=(?!=)\s*(.+)$", expr)
            if assign:
                name, rhs = assign.group(1), assign.group(2)
                value = _eval_node(_parse(rhs).body, scope)
                self.vars[name] = value
                shown = fmt(value)
                self.result.config(text="%s = %s" % (name, shown),
                                   fg=self.theme.get("ok", "#7ee787"))
                self._record("%s = %s" % (expr, shown))
                self.last = value
                self.status.config(text="variable %r stored — %d names "
                                        "in scope" % (name,
                                                      len(self.vars) + 5))
                return

            value = _eval_node(_parse(expr).body, scope)
            self.result.config(text="= " + fmt(value),
                               fg=self.theme.get("ok", "#7ee787"))
            self._record("%s = %s" % (expr, fmt(value)))
            self.last = value
            self.status.config(text="26 functions · constants: pi e "
                                    "tau inf · _ is the last answer")
        except CalcError as exc:
            self.result.config(text="= ?",
                               fg=self.theme.get("error", "#ff6b6b"))
            self.status.config(text=str(exc))
        except Exception:  # noqa: BLE001 — the window must not die
            self.result.config(text="= ?",
                               fg=self.theme.get("error", "#ff6b6b"))
            self.status.config(text="hiccup (input kept)")

    def _copy_row(self, _event):
        try:
            sel = self.history.curselection()
            if not sel:
                return None
            line = self.history.get(sel[0])
            answer = line.rsplit("= ", 1)[-1]
            self.clipboard_clear()
            self.clipboard_append(answer)
            self.status.config(text="copied %s" % answer)
        except Exception:
            pass
        return None

    def _copy_result(self):
        try:
            if self.last is None:
                self.status.config(text="nothing to copy yet")
                return
            self.clipboard_clear()
            self.clipboard_append(fmt(self.last))
            self.status.config(text="result copied")
        except Exception:
            pass


def open_mathpad(parent, theme, initial=""):
    """Public entry: open the MathPad window. Never raises."""
    try:
        win = MathPad(parent, theme, initial=initial)
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
