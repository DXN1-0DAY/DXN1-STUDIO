"""DXN1 STUDIO — developer tools, four tabs, zero excuses (DS2).

A pocket knife that lives inside the studio: a regex tester with live
match + group inspection and replace preview, a JSON formatter and
validator that points at the exact broken byte, a text transformer
(case conversions, base64, URL, unicode escapes, hashes, counts) and
a time converter (epoch <-> ISO <-> "3 hours ago").  Every engine
function below is pure and unit-tested; the window is a thin,
defensive skin over them.

Open from the palette:  "Developer tools — regex, JSON, text, time…"
"""

import base64
import hashlib
import json
import re
import tkinter as tk
from datetime import datetime, timezone
from tkinter import ttk
from urllib.parse import quote, unquote

from .theme import FONT_UI, FONT_MONO
from .i18n import tr
from . import hints

MAX_MATCHES = 500  # keep the UI honest on huge inputs


# ------------------------------------------------------------------ case

_WORD_RE = re.compile(
    r"[A-Z]+(?=[A-Z][a-z0-9])|[A-Z]?[a-z0-9]+|[A-Z]+")


def _fallback(s):
    """Passthrough for symbol-only strings; whitespace collapses to ''."""
    return s if s and s.strip() else ""


def _split_words(s):
    """Split any identifier-ish string into lowercase words.

    Understands camelCase, PascalCase, snake_case, kebab-case,
    CONST_CASE, dotted paths and plain sentences ("HTTPServer2" ->
    http, server, 2).
    """
    if not s:
        return []
    parts = re.split(r"[-_.\s]+", s.strip())
    out = []
    for p in parts:
        if not p:
            continue
        out.extend(m.group(0).lower() for m in _WORD_RE.finditer(p))
    return out


def to_snake(s):
    w = _split_words(s)
    return "_".join(w) if w else _fallback(s)


def to_kebab(s):
    w = _split_words(s)
    return "-".join(w) if w else _fallback(s)


def to_const(s):
    w = _split_words(s)
    return "_".join(w).upper() if w else _fallback(s)


def to_pascal(s):
    w = _split_words(s)
    return "".join(x[:1].upper() + x[1:] for x in w) if w else _fallback(s)


def to_camel(s):
    w = _split_words(s)
    if not w:
        return _fallback(s)
    return w[0] + "".join(x[:1].upper() + x[1:] for x in w[1:])


def to_title(s):
    w = _split_words(s)
    return " ".join(x[:1].upper() + x[1:] for x in w) if w else _fallback(s)


# ----------------------------------------------------------------- codecs

def b64_encode(s):
    try:
        return base64.b64encode((s or "").encode("utf-8")).decode("ascii"), ""
    except Exception as e:  # pragma: no cover — utf-8 never fails
        return "", str(e)


def b64_decode(s):
    try:
        raw = base64.b64decode((s or "").strip(), validate=True)
        return raw.decode("utf-8"), ""
    except Exception as e:
        return "", f"not valid base64: {e}"


def url_encode(s):
    try:
        return quote(s or "", safe=""), ""
    except Exception as e:  # pragma: no cover
        return "", str(e)


def url_decode(s):
    try:
        return unquote(s or ""), ""
    except Exception as e:  # pragma: no cover
        return "", str(e)


def hashes(s):
    b = (s or "").encode("utf-8")
    return {
        "md5": hashlib.md5(b).hexdigest(),
        "sha1": hashlib.sha1(b).hexdigest(),
        "sha256": hashlib.sha256(b).hexdigest(),
    }


_ESC_RE = re.compile(r"\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})")


def unicode_escape(s):
    out = []
    for ch in s or "":
        o = ord(ch)
        if 32 <= o < 127:
            out.append(ch)
        elif o <= 0xFFFF:
            out.append("\\u%04x" % o)
        else:
            out.append("\\U%08x" % o)
    return "".join(out), ""


def unicode_unescape(s):
    def sub(m):
        code = m.group(1) or m.group(2)
        try:
            return chr(int(code, 16))
        except ValueError:
            return m.group(0)
    return _ESC_RE.sub(sub, s or ""), ""


def text_counts(s):
    s = s or ""
    lines = s.count("\n") + (1 if s and not s.endswith("\n") else 0)
    return {
        "chars": len(s),
        "chars_no_ws": len(re.sub(r"\s", "", s)),
        "words": len(s.split()),
        "lines": lines,
    }


# ------------------------------------------------------------------ regex

_FLAG_MAP = {
    "i": re.IGNORECASE,
    "m": re.MULTILINE,
    "s": re.DOTALL,
    "x": re.VERBOSE,
}


def regex_flags(chs):
    """'ims' -> re flags (engine helper so tests + UI share one map)."""
    f = 0
    for c in chs or "":
        f |= _FLAG_MAP.get(c, 0)
    return f


def regex_matches(pattern, text, flags=0):
    """-> (list of match dicts, error string). Never raises."""
    if not pattern:
        return [], ""
    try:
        rx = re.compile(pattern, flags)
    except re.error as e:
        return [], f"pattern error: {e}"
    out = []
    try:
        for m in rx.finditer(text or ""):
            out.append({
                "start": m.start(),
                "end": m.end(),
                "text": m.group(0),
                "groups": [g if g is not None else ""
                           for g in m.groups()],
                "groupdict": {k: (v if v is not None else "")
                              for k, v in (m.groupdict() or {}).items()},
            })
            if len(out) >= MAX_MATCHES:
                break
    except Exception as e:  # catastrophic patterns etc.
        return out, str(e)
    return out, ""


def regex_do_replace(pattern, repl, text, flags=0):
    """-> (result, error). Never raises."""
    if not pattern:
        return text or "", ""
    try:
        return re.compile(pattern, flags).sub(repl, text or ""), ""
    except re.error as e:
        return "", f"pattern error: {e}"


# ------------------------------------------------------------------- json

def _json_pos(text, pos):
    text = text or ""
    line = text.count("\n", 0, pos) + 1
    col = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return line, col


def json_format(text, indent=2, sort_keys=False):
    """Pretty-print JSON. -> (result, error with line/col). Never raises."""
    try:
        obj = json.loads(text or "")
    except json.JSONDecodeError as e:
        line, col = _json_pos(text, e.pos or 0)
        return "", f"line {line}, col {col}: {e.msg}"
    except Exception as e:
        return "", str(e)
    try:
        return json.dumps(obj, indent=indent, sort_keys=sort_keys,
                          ensure_ascii=False), ""
    except Exception as e:
        return "", str(e)


def json_minify(text):
    """Minify JSON. -> (result, error). Never raises."""
    try:
        obj = json.loads(text or "")
    except json.JSONDecodeError as e:
        line, col = _json_pos(text, e.pos or 0)
        return "", f"line {line}, col {col}: {e.msg}"
    except Exception as e:
        return "", str(e)
    try:
        return json.dumps(obj, separators=(",", ":"),
                          ensure_ascii=False), ""
    except Exception as e:
        return "", str(e)


def json_validate(text):
    return json_format(text)[1]


# ------------------------------------------------------------------- time

def epoch_to_iso(ts, local=False):
    try:
        ts = float(str(ts).strip())
    except (TypeError, ValueError):
        return "", "not a number"
    try:
        if local:
            dt = datetime.fromtimestamp(ts).astimezone()
        else:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as e:
        return "", f"bad epoch: {e}"
    return dt.isoformat(timespec="seconds"), ""


def iso_to_epoch(s):
    s = (s or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        return 0, f"bad ISO: {e}"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # naive means UTC here
    try:
        return int(dt.timestamp()), ""
    except (OverflowError, OSError) as e:
        return 0, f"bad ISO: {e}"


def now_iso(local=False):
    dt = datetime.now().astimezone() if local \
        else datetime.now(timezone.utc)
    return dt.isoformat(timespec="seconds")


def rel_time(ts, now=None):
    """epoch -> '3h ago' / 'in 2d'. Empty string when ts is nonsense."""
    try:
        ts = float(str(ts).strip())
    except (TypeError, ValueError):
        return ""
    if now is None:
        now = datetime.now(timezone.utc).timestamp()
    d = ts - float(now)
    future = d > 0
    d = abs(d)
    steps = ((365 * 86400, "y"), (30 * 86400, "mo"), (86400, "d"),
             (3600, "h"), (60, "m"), (1, "s"))
    for secs, unit in steps:
        if d >= secs:
            n = int(d // secs)
            return f"in {n}{unit}" if future else f"{n}{unit} ago"
    return "now"



# ------------------------------------------------------------------ color

def hex_to_rgb(s):
    s = (s or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return 0, 0, 0, "need #rgb or #rrggbb"
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), ""
    except ValueError:
        return 0, 0, 0, "need hex digits"


def rgb_to_hex(r, g, b):
    clamp = lambda v: max(0, min(255, int(round(v))))  # noqa: E731
    return "#{:02x}{:02x}{:02x}".format(clamp(r), clamp(g), clamp(b))


def rgb_to_hsl(r, g, b):
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l * 100
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return (h * 60) % 360, s * 100, l * 100


def hsl_to_rgb(h, s, l):
    h, s, l = (h % 360) / 360, max(0, min(1, s / 100)), max(0, min(1, l / 100))
    if s == 0:
        r = g = b = l
    else:
        def f(n):
            k = (n + h * 12) % 12
            a = s * min(l, 1 - l)
            return l - a * max(-1, min(k - 3, 9 - k, 1))
        r, g, b = f(0), f(8), f(4)
    return r * 255, g * 255, b * 255


def _chan_lum(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rel_luminance(r, g, b):
    return (0.2126 * _chan_lum(r) + 0.7152 * _chan_lum(g)
            + 0.0722 * _chan_lum(b))


def contrast_ratio(hex1, hex2):
    r1, g1, b1, e1 = hex_to_rgb(hex1)
    r2, g2, b2, e2 = hex_to_rgb(hex2)
    if e1 or e2:
        return 0.0
    l1, l2 = rel_luminance(r1, g1, b1), rel_luminance(r2, g2, b2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def color_harmonies(hex_color):
    """Complementary, analogous, triadic + lighter/darker neighbours."""
    r, g, b, err = hex_to_rgb(hex_color)
    if err:
        return {}
    h, s, l = rgb_to_hsl(r, g, b)
    def hx(hh, ss=None, ll=None):
        rr, gg, bb = hsl_to_rgb(hh, s if ss is None else ss,
                                l if ll is None else ll)
        return rgb_to_hex(rr, gg, bb)
    return {
        "base": rgb_to_hex(r, g, b),
        "complement": hx(h + 180),
        "analogous -30": hx(h - 30),
        "analogous +30": hx(h + 30),
        "triadic 120": hx(h + 120),
        "triadic 240": hx(h + 240),
        "lighter +20%": hx(h, ll=l + 20),
        "darker -20%": hx(h, ll=l - 20),
    }

# ------------------------------------------------------------------ window

class DevTools(tk.Toplevel):
    """Four tabs: Regex, JSON, Text, Time. Exposes internals so the
    smoke harness can drive every path without poking at privates."""

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.t = theme
        self.title("Developer tools — DXN1 STUDIO")
        self.configure(bg=theme["bg"])
        self.geometry("880x620")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 880x620 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 880, 620))
        self.minsize(700, 480)
        try:
            self.transient(parent.winfo_toplevel()
                           if parent is not None else parent)
        except Exception:
            pass
        self._rx_job = None
        self._clock_job = None
        self._style()
        self.nb = ttk.Notebook(self, style="Dev.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)
        self._tab_regex()
        self._tab_json()
        self._tab_text()
        self._tab_time()
        self._tab_color()
        self.nb.select(0)
        self.bind("<Escape>", lambda e: self.destroy())
        # v2.49 — the tabs answer to the keyboard: Ctrl+1…5 select,
        # and the hint bar advertises exactly what is really bound.
        self._tabs = ("regex", "json", "text", "time", "color")
        for _i in range(len(self._tabs)):
            self.bind("<Control-%d>" % (_i + 1),
                      lambda e, i=_i: self.select_tab(i))
        self._build_hintbar()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._center()

    def select_tab(self, index):
        """v2.49 — keyboard tab switching (Ctrl+1…5). Never raises."""
        try:
            self.nb.select(index)
        except Exception:  # noqa: BLE001 — a stray index is garnish
            pass

    def _build_hintbar(self):
        self.hintbar = hints.hint_bar(
            self, self.t,
            pairs=tuple(("Ctrl+%d" % (i + 1), name)
                        for i, name in enumerate(self._tabs)))

    # ------------------------------------------------------------- chrome

    def _close(self):
        try:
            if self._clock_job:
                self.after_cancel(self._clock_job)
        except Exception:
            pass
        self.destroy()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 880, 620
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _style(self):
        t = self.t
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Dev.TNotebook", background=t["bg"],
                     borderwidth=0, tabmargins=(0, 0, 0, 6))
        st.configure("Dev.TNotebook.Tab", background=t["header"],
                     foreground=t["text_secondary"], padding=(14, 7),
                     borderwidth=0, font=(FONT_UI, 10))
        st.map("Dev.TNotebook.Tab",
               background=[("selected", t["hover"])],
               foreground=[("selected", t["text"])])
        st.configure("Dev.Treeview", background=t["card"],
                     fieldbackground=t["card"], foreground=t["text"],
                     rowheight=24, borderwidth=0, font=(FONT_MONO, 10))
        st.configure("Dev.Treeview.Heading", background=t["header"],
                     foreground=t["text_secondary"], relief="flat",
                     font=(FONT_UI, 9))
        st.map("Dev.Treeview",
               background=[("selected", t["hover"])],
               foreground=[("selected", t["text"])])
        st.configure("Dev.Vertical.TScrollbar", background=t["header"],
                     troughcolor=t["bg"], borderwidth=0, arrowsize=12)

    def _btn(self, master, text, cmd, accent=False):
        t = self.t
        bg = t.get("accent", t["header"]) if accent else t["header"]
        fg = t.get("select_fg", "#ffffff") if accent else t["text"]
        b = tk.Button(master, text=text, command=cmd, relief="flat",
                      cursor="hand2", bg=bg, fg=fg, bd=0, padx=12, pady=5,
                      activebackground=t["hover"],
                      activeforeground=t["text"], font=(FONT_UI, 9))
        return b

    def _entry(self, master, textvariable=None, mono=True):
        t = self.t
        e = tk.Entry(master, textvariable=textvariable, relief="flat",
                     bg=t["editor"], fg=t["text"],
                     insertbackground=t["text"],
                     font=(FONT_MONO if mono else FONT_UI, 11),
                     bd=0, highlightthickness=1,
                     highlightbackground=t["border"],
                     highlightcolor=t.get("accent", t["hover"]))
        return e

    def _mono_text(self, master, height=8, read_only=False):
        t = self.t
        wrap = tk.Frame(master, bg=t["border"])
        txt = tk.Text(wrap, height=height, wrap="word", relief="flat",
                      bg=t["editor"], fg=t["text"],
                      insertbackground=t["text"],
                      selectbackground=t["hover"], selectforeground=t["text"],
                      font=(FONT_MONO, 11), padx=8, pady=6, bd=0,
                      undo=True)
        sb = ttk.Scrollbar(wrap, command=txt.yview, style="Dev.Vertical.TScrollbar")
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        if read_only:
            txt.configure(state="disabled")
        return wrap, txt

    def _status(self, master):
        t = self.t
        lbl = tk.Label(master, text="", anchor="w", bg=t["bg"],
                       fg=t["text_muted"], font=(FONT_UI, 9))
        lbl.pack(fill="x", pady=(6, 0))
        return lbl

    def _set_status(self, lbl, msg, ok=None):
        t = self.t
        try:
            lbl.configure(text=msg,
                          fg=t["success"] if ok else t["text_muted"]
                          if ok is None else t["text_secondary"])
        except tk.TclError:
            pass

    def _copy(self, widget, lbl):
        try:
            data = widget.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(data)
            self._set_status(lbl, f"copied {len(data)} chars", ok=True)
        except tk.TclError:
            pass

    # --------------------------------------------------------- tab: regex

    def _tab_regex(self):
        t = self.t
        page = tk.Frame(self.nb, bg=t["bg"])
        self.nb.add(page, text="  Regex  ")

        top = tk.Frame(page, bg=t["bg"])
        top.pack(fill="x", pady=(0, 6))
        self.rx_pattern_var = tk.StringVar()
        self.rx_pattern = self._entry(top, self.rx_pattern_var)
        self.rx_pattern.pack(side="left", fill="x", expand=True,
                             ipady=5)
        self.rx_flags = {}
        for name, ch in (("ignore case", "i"), ("multiline", "m"),
                         ("dotall", "s")):
            v = tk.BooleanVar(value=False)
            self.rx_flags[ch] = v
            cb = tk.Checkbutton(top, text=name, variable=v,
                                command=self._rx_schedule,
                                bg=t["bg"], fg=t["text_secondary"],
                                activebackground=t["bg"],
                                activeforeground=t["text"],
                                selectcolor=t["editor"],
                                font=(FONT_UI, 9), bd=0,
                                highlightthickness=0)
            cb.pack(side="left", padx=(8, 0))
        self.rx_pattern_var.trace_add("write", lambda *a: self._rx_schedule())

        mid = tk.Frame(page, bg=t["bg"])
        mid.pack(fill="both", expand=True)
        wrap, self.rx_test = self._mono_text(mid, height=9)
        wrap.pack(side="left", fill="both", expand=True)

        rw = tk.Frame(mid, bg=t["bg"])
        rw.pack(side="left", fill="both", padx=(8, 0))
        cols = ("span", "match", "groups")
        self.rx_tree = ttk.Treeview(rw, columns=cols, show="headings",
                                    height=12, style="Dev.Treeview")
        for cid, label, w in (("span", "span", 110),
                              ("match", "match", 200),
                              ("groups", "groups", 190)):
            self.rx_tree.heading(cid, text=label)
            self.rx_tree.column(cid, width=w, stretch=True, anchor="w")
        sb = ttk.Scrollbar(rw, command=self.rx_tree.yview,
                           style="Dev.Vertical.TScrollbar")
        self.rx_tree.configure(yscrollcommand=sb.set)
        self.rx_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.rx_status = self._status(page)

        bot = tk.Frame(page, bg=t["bg"])
        bot.pack(fill="x", pady=(8, 0))
        tk.Label(bot, text="replace with", bg=t["bg"],
                 fg=t["text_muted"], font=(FONT_UI, 9)).pack(side="left")
        self.rx_repl_var = tk.StringVar()
        self.rx_repl = self._entry(bot, self.rx_repl_var)
        self.rx_repl.pack(side="left", fill="x", expand=True,
                          padx=(8, 8), ipady=5)
        self._btn(bot, tr("devtools.preview"),
                  lambda: self._rx_replace(self.rx_repl_var.get())) \
            .pack(side="left")
        self.rx_preview, _unused = None, None
        pw, self.rx_preview = self._mono_text(page, height=5,
                                              read_only=True)
        pw.pack(fill="both", pady=(6, 0))
        self._btn(page, tr("common.copy_matches"),
                  lambda: self._copy_tree(self.rx_tree, self.rx_status)) \
            .pack(anchor="e", pady=(6, 0))

        self._rx_eval()

    def _copy_tree(self, tree, lbl):
        try:
            rows = []
            for iid in tree.get_children(""):
                rows.append("\t".join(tree.item(iid, "values")))
            data = "\n".join(rows)
            self.clipboard_clear()
            self.clipboard_append(data)
            self._set_status(lbl, f"copied {len(rows)} rows", ok=True)
        except tk.TclError:
            pass

    def _rx_schedule(self):
        try:
            if self._rx_job:
                self.after_cancel(self._rx_job)
        except Exception:
            self._rx_job = None
        self._rx_job = self.after(200, self._rx_eval)

    def _rx_flags_int(self):
        f = 0
        for ch, var in self.rx_flags.items():
            if var.get():
                f |= regex_flags(ch)
        return f

    def _rx_eval(self):
        self._rx_job = None
        pattern = self.rx_pattern_var.get()
        text = self.rx_test.get("1.0", "end-1c")
        matches, err = regex_matches(pattern, text, self._rx_flags_int())
        try:
            self.rx_tree.delete(*self.rx_tree.get_children(""))
        except tk.TclError:
            return
        if err:
            self._set_status(self.rx_status, err, ok=False)
            return
        for i, m in enumerate(matches, 1):
            groups = ", ".join(g for g in m["groups"]) if m["groups"] else ""
            gd = " ".join(f"{k}={v}" for k, v in m["groupdict"].items())
            extra = f"  {gd}" if gd else ""
            self.rx_tree.insert("", "end", values=(
                f"{m['start']}..{m['end']}",
                (m["text"][:120] or "∅"),
                (groups + extra)[:160]))
        shown = f"{len(matches)} match(es)" + \
            (" (capped)" if len(matches) >= MAX_MATCHES else "")
        self._set_status(self.rx_status, shown, ok=bool(matches))

    def _rx_replace(self, repl):
        text = self.rx_test.get("1.0", "end-1c")
        result, err = regex_do_replace(self.rx_pattern_var.get(), repl,
                                       text, self._rx_flags_int())
        try:
            self.rx_preview.configure(state="normal")
            self.rx_preview.delete("1.0", "end")
            if err:
                self._set_status(self.rx_status, err, ok=False)
            else:
                self.rx_preview.insert("1.0", result)
                n = text and result != text
                self._set_status(self.rx_status,
                                 "replaced" if n else "no change",
                                 ok=bool(n))
            self.rx_preview.configure(state="disabled")
        except tk.TclError:
            pass

    # ---------------------------------------------------------- tab: json

    def _tab_json(self):
        t = self.t
        page = tk.Frame(self.nb, bg=t["bg"])
        self.nb.add(page, text="  JSON  ")

        row = tk.Frame(page, bg=t["bg"])
        row.pack(fill="x", pady=(0, 6))
        self._btn(row, "Pretty 2", lambda: self._json_run("pretty2")) \
            .pack(side="left")
        self._btn(row, "Pretty 4", lambda: self._json_run("pretty4")) \
            .pack(side="left", padx=(6, 0))
        self._btn(row, "Minify", lambda: self._json_run("minify")) \
            .pack(side="left", padx=(6, 0))
        self._btn(row, "Validate", lambda: self._json_run("validate")) \
            .pack(side="left", padx=(6, 0))
        self.json_sort = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="sort keys", variable=self.json_sort,
                       bg=t["bg"], fg=t["text_secondary"],
                       activebackground=t["bg"],
                       activeforeground=t["text"],
                       selectcolor=t["editor"], font=(FONT_UI, 9),
                       bd=0, highlightthickness=0).pack(side="left",
                                                        padx=(12, 0))
        self._btn(row, tr("common.copy_output"),
                  lambda: self._copy(self.json_out, self.json_status)) \
            .pack(side="right")

        iw, self.json_in = self._mono_text(page, height=9)
        iw.pack(fill="both", expand=True)
        ow, self.json_out = self._mono_text(page, height=9,
                                            read_only=True)
        ow.pack(fill="both", expand=True, pady=(6, 0))
        self.json_status = self._status(page)
        self._json_run("validate")

    def _json_run(self, mode):
        src = self.json_in.get("1.0", "end-1c")
        sort = self.json_sort.get() if hasattr(self, "json_sort") else False
        if mode == "minify":
            out, err = json_minify(src)
        elif mode == "validate":
            err = json_validate(src)
            out = "" if err else "valid JSON ✓"
        else:
            out, err = json_format(src, indent=2 if mode == "pretty2" else 4,
                                   sort_keys=sort)
        try:
            self.json_out.configure(state="normal")
            self.json_out.delete("1.0", "end")
            self.json_out.insert("1.0", out or err)
            self.json_out.configure(state="disabled")
        except tk.TclError:
            return
        msg = err if err else (f"ok · {len(out)} chars" if out else "empty input")
        self._set_status(self.json_status, msg, ok=not err and bool(out))

    # ---------------------------------------------------------- tab: text

    _TRANSFORMS = (
        ("snake_case", to_snake), ("camelCase", to_camel),
        ("PascalCase", to_pascal), ("kebab-case", to_kebab),
        ("CONST_CASE", to_const), ("Title Case", to_title),
        ("base64 →", "b64e"), ("← base64", "b64d"),
        ("URL % →", "urle"), ("← URL %", "urld"),
        ("\\u esc", "uesc"), ("\\u unesc", "uunesc"),
        ("MD5", "md5"), ("SHA-1", "sha1"), ("SHA-256", "sha256"),
    )

    def _tab_text(self):
        t = self.t
        page = tk.Frame(self.nb, bg=t["bg"])
        self.nb.add(page, text="  Text  ")

        grid = tk.Frame(page, bg=t["bg"])
        grid.pack(fill="x", pady=(0, 6))
        for i, (name, fn) in enumerate(self._TRANSFORMS):
            self._btn(grid, name,
                      lambda f=fn: self._tx_apply(f)) \
                .grid(row=i // 5, column=i % 5, sticky="ew", padx=2,
                      pady=2)
        for c in range(5):
            grid.columnconfigure(c, weight=1)
        acts = tk.Frame(page, bg=t["bg"])
        acts.pack(fill="x", pady=(0, 6))
        self._btn(acts, "↑ use output as input",
                  self._tx_feedback).pack(side="left")
        self._btn(acts, tr("devtools.count"),
                  lambda: self._tx_counts()).pack(side="left", padx=(6, 0))
        self._btn(acts, tr("common.copy_output"),
                  lambda: self._copy(self.tx_out, self.tx_status)) \
            .pack(side="right")

        iw, self.tx_in = self._mono_text(page, height=8)
        iw.pack(fill="both", expand=True)
        ow, self.tx_out = self._mono_text(page, height=8, read_only=True)
        ow.pack(fill="both", expand=True, pady=(6, 0))
        self.tx_status = self._status(page)

    def _tx_apply(self, fn):
        src = self.tx_in.get("1.0", "end-1c")
        err = ""
        if callable(fn):                       # case transforms + codecs
            res = fn(src)
            if isinstance(res, tuple):
                out, err = res
            else:
                out, err = res, ""
        else:                                  # string codes
            if fn in ("md5", "sha1", "sha256"):
                out, err = hashes(src)[fn], ""
            else:
                codec = {"b64e": b64_encode, "b64d": b64_decode,
                         "urle": url_encode, "urld": url_decode,
                         "uesc": unicode_escape,
                         "uunesc": unicode_unescape}.get(fn)
                if codec is not None:
                    out, err = codec(src)
                else:
                    out, err = "", "unknown transform"
        try:
            self.tx_out.configure(state="normal")
            self.tx_out.delete("1.0", "end")
            self.tx_out.insert("1.0", out if not err else "")
            self.tx_out.configure(state="disabled")
            self._set_status(self.tx_status,
                             err if err else f"applied · {len(out)} chars",
                             ok=not err)
        except tk.TclError:
            pass

    def _tx_feedback(self):
        data = self.tx_out.get("1.0", "end-1c")
        try:
            self.tx_in.delete("1.0", "end")
            self.tx_in.insert("1.0", data)
            self._set_status(self.tx_status,
                             "output moved to input — chain away",
                             ok=True)
        except tk.TclError:
            pass

    def _tx_counts(self):
        src = self.tx_in.get("1.0", "end-1c")
        c = text_counts(src)
        try:
            self.tx_out.configure(state="normal")
            self.tx_out.delete("1.0", "end")
            self.tx_out.insert(
                "1.0",
                f"chars      {c['chars']}\n"
                f"no spaces  {c['chars_no_ws']}\n"
                f"words      {c['words']}\n"
                f"lines      {c['lines']}")
            self.tx_out.configure(state="disabled")
            self._set_status(self.tx_status,
                             f"{c['words']} words · {c['chars']} chars",
                             ok=True)
        except tk.TclError:
            pass

    # ---------------------------------------------------------- tab: time

    def _tab_time(self):
        t = self.t
        page = tk.Frame(self.nb, bg=t["bg"])
        self.nb.add(page, text="  Time  ")

        self.ts_clock_var = tk.StringVar(value=now_iso())
        tk.Label(page, textvariable=self.ts_clock_var, bg=t["bg"],
                 fg=t.get("accent", t["text_secondary"]),
                 font=(FONT_MONO, 16)).pack(anchor="w", pady=(0, 10))
        self._tick_clock()

        row1 = tk.Frame(page, bg=t["bg"])
        row1.pack(fill="x")
        tk.Label(row1, text="epoch", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 10), width=6, anchor="w").pack(side="left")
        self.ts_epoch_var = tk.StringVar()
        self.ts_epoch = self._entry(row1, self.ts_epoch_var)
        self.ts_epoch.pack(side="left", fill="x", expand=True, ipady=5)
        self._btn(row1, "→ ISO", lambda: self._ts_to_iso()).pack(
            side="left", padx=(8, 0))
        self._btn(row1, "Now", lambda: self._ts_now()).pack(
            side="left", padx=(6, 0))

        row2 = tk.Frame(page, bg=t["bg"])
        row2.pack(fill="x", pady=(8, 0))
        tk.Label(row2, text="ISO", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 10), width=6, anchor="w").pack(side="left")
        self.ts_iso_var = tk.StringVar()
        self.ts_iso = self._entry(row2, self.ts_iso_var)
        self.ts_iso.pack(side="left", fill="x", expand=True, ipady=5)
        self._btn(row2, "→ epoch", lambda: self._ts_to_epoch()).pack(
            side="left", padx=(8, 0))

        self.ts_local = tk.BooleanVar(value=False)
        tk.Checkbutton(page, text="use local timezone (else UTC)",
                       variable=self.ts_local, bg=t["bg"],
                       fg=t["text_secondary"], activebackground=t["bg"],
                       activeforeground=t["text"],
                       selectcolor=t["editor"], font=(FONT_UI, 9),
                       bd=0, highlightthickness=0).pack(anchor="w",
                                                        pady=(10, 0))
        self.ts_rel_var = tk.StringVar(value="")
        tk.Label(page, textvariable=self.ts_rel_var, bg=t["bg"],
                 fg=t["text_secondary"], font=(FONT_UI, 11)) \
            .pack(anchor="w", pady=(10, 0))
        self.ts_status = self._status(page)
        self._ts_now()

    def _tick_clock(self):
        try:
            self.ts_clock_var.set(now_iso(local=self.ts_local.get()))
        except Exception:
            pass
        self._clock_job = self.after(1000, self._tick_clock)

    def _ts_now(self):
        now = now_iso()
        self.ts_iso_var.set(now)
        ep, err = iso_to_epoch(now)
        self.ts_epoch_var.set(str(ep) if not err else "")
        self._ts_relative()
        self._set_status(self.ts_status, "current time filled in", ok=True)

    def _ts_relative(self):
        ep = self.ts_epoch_var.get().strip()
        self.ts_rel_var.set(f"relative: {rel_time(ep)}" if ep
                            else "relative: —")

    def _ts_to_iso(self):
        iso, err = epoch_to_iso(self.ts_epoch_var.get().strip(),
                                local=self.ts_local.get())
        if err:
            self._set_status(self.ts_status, err, ok=False)
            return
        self.ts_iso_var.set(iso)
        self._ts_relative()
        self._set_status(self.ts_status, "converted → ISO", ok=True)

    def _ts_to_epoch(self):
        ep, err = iso_to_epoch(self.ts_iso_var.get())
        if err:
            self._set_status(self.ts_status, err, ok=False)
            return
        self.ts_epoch_var.set(str(ep))
        self._ts_relative()
        self._set_status(self.ts_status, "converted → epoch", ok=True)


    # --------------------------------------------------------- tab: color

    def _tab_color(self):
        t = self.t
        page = tk.Frame(self.nb, bg=t["bg"])
        self.nb.add(page, text="  Color  ")

        row = tk.Frame(page, bg=t["bg"])
        row.pack(fill="x")
        tk.Label(row, text="hex", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 10)).pack(side="left")
        self.cl_hex_var = tk.StringVar(value="#4f8cff")
        self.cl_hex = self._entry(row, self.cl_hex_var)
        self.cl_hex.pack(side="left", fill="x", expand=True, padx=(8, 8),
                         ipady=5)
        self.cl_swatch = tk.Label(row, text="      ", bg="#4f8cff",
                                  width=4)
        self.cl_swatch.pack(side="left", fill="y")
        self.cl_readout = tk.Label(row, text="", bg=t["bg"],
                                   fg=t["text_secondary"], font=(FONT_MONO, 10))
        self.cl_readout.pack(side="left", padx=(10, 0))
        self.cl_hex_var.trace_add("write", lambda *a: self._cl_update())

        row2 = tk.Frame(page, bg=t["bg"])
        row2.pack(fill="x", pady=(10, 0))
        tk.Label(row2, text="contrast with", bg=t["bg"],
                 fg=t["text_muted"], font=(FONT_UI, 10)).pack(side="left")
        self.cl_vs_var = tk.StringVar(value="#ffffff")
        self.cl_vs = self._entry(row2, self.cl_vs_var)
        self.cl_vs.pack(side="left", fill="x", expand=True, padx=(8, 8),
                        ipady=5)
        self.cl_ratio = tk.Label(row2, text="", bg=t["bg"],
                                 fg=t["text_secondary"],
                                 font=(FONT_MONO, 11))
        self.cl_ratio.pack(side="left")
        self.cl_vs_var.trace_add("write", lambda *a: self._cl_update())

        tk.Label(page, text="harmonies — click a swatch to copy its hex",
                 bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 9)).pack(anchor="w", pady=(14, 6))
        self.cl_harm = tk.Frame(page, bg=t["bg"])
        self.cl_harm.pack(fill="x")
        self.cl_status = self._status(page)
        self._cl_update()

    def _cl_update(self):
        t = self.t
        r, g, b, err = hex_to_rgb(self.cl_hex_var.get())
        if err:
            try:
                self.cl_readout.configure(text=err)
            except tk.TclError:
                pass
            return
        h, s_, l = rgb_to_hsl(r, g, b)
        try:
            self.cl_swatch.configure(bg=rgb_to_hex(r, g, b))
            self.cl_readout.configure(
                text=f"rgb({r}, {g}, {b})  hsl({h:.0f}, {s_:.0f}%, "
                     f"{l:.0f}%)")
        except tk.TclError:
            return
        ratio = contrast_ratio(self.cl_hex_var.get(), self.cl_vs_var.get())
        if ratio:
            grade = ("AAA" if ratio >= 7 else "AA" if ratio >= 4.5
                     else "AA-large" if ratio >= 3 else "fail")
            self.cl_ratio.configure(text=f"{ratio:5.2f}:1  {grade}")
        else:
            self.cl_ratio.configure(text="")
        for wdg in self.cl_harm.winfo_children():
            wdg.destroy()
        for name, hx in color_harmonies(self.cl_hex_var.get()).items():
            cell = tk.Frame(self.cl_harm, bg=t["bg"])
            cell.pack(side="left", padx=(0, 8))
            sw = tk.Label(cell, text="      ", bg=hx, cursor="hand2")
            sw.pack()
            sw.bind("<Button-1>", lambda e, hx=hx: (
                self.clipboard_clear(), self.clipboard_append(hx),
                self._set_status(self.cl_status,
                                 f"copied {hx}", ok=True)))
            tk.Label(cell, text=name.replace("analogous ", "an ")
                     .replace("triadic ", "tr "), bg=t["bg"],
                     fg=t["text_muted"], font=(FONT_UI, 8)).pack()


def open_devtools(parent, theme):
    """Convenience opener — mirrors the studio's one-call dialog style."""
    return DevTools(parent, theme)
