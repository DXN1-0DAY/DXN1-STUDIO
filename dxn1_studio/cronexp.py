"""DXN1 STUDIO — cron expression decoder ring (DS2).

Paste a cron expression, get a human sentence ("at 09:00, every
Monday, in January"), the next five run times and a field-by-field
breakdown.  Pure engine (no cron daemon, no third-party libs — the
schedule math is implemented here with a minute-stepper) + a themed
window.  Open from the palette ("Cron explainer…") or terminal
`cron <expr>`.

Supports the standard five fields (minute hour dom month dow), the
shorthands @hourly/@daily/@weekly/@monthly/@yearly/@reboot, step
values (*/5, 1-30/2), ranges, lists, names (mon, jan) and both `dow`
conventions (0-6 with 7==Sunday).
"""

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11,
           "dec": 12}
_DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5,
         "sat": 6}

_NICKS = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@reboot": "",
}


# ------------------------------------------------------------- parsing

def _parse_field(field, lo, hi, names=None):
    """'*/5', '1-5', '3,7,mon-fri' -> sorted set of ints. Never raises."""
    out = set()
    for part in (field or "").split(","):
        part = part.strip().lower()
        if not part:
            return None
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            try:
                step = int(step_s)
            except ValueError:
                return None
            if step < 1:
                return None
        if part in ("*", ""):
            start, end = lo, hi
        elif "-" in part.lstrip("-"):
            a, b = part.split("-", 1)
            start = _atom(a, names)
            end = _atom(b, names)
            if start is None or end is None:
                return None
            # dom/month cannot wrap; dow 7 == 0 (Sunday)
            if end < start:
                if hi == 6:            # dow wrap: 5-1 -> 5,6,0,1
                    return sorted({v for v in range(start, hi + 1)} |
                                  {v for v in range(lo, end + 1)}) \
                        if step == 1 else None
                return None
        else:
            start = _atom(part, names)
            if start is None:
                return None
            end = start if step == 1 else hi
            if step > 1 and part != "*":
                end = hi
        if end > hi or start < lo:
            return None
        out.update(range(start, end + 1, step))
    vals = sorted(v for v in out if lo <= v <= hi)
    return vals or None


def _atom(tok, names):
    tok = (tok or "").strip().lower()
    if tok.isdigit():
        return int(tok)
    if names and tok in names:
        return names[tok]
    return None


def parse_cron(expr):
    """-> (dict of field->list, error). dict is None on error."""
    expr = (expr or "").strip()
    if not expr:
        return None, "empty expression"
    low = expr.lower()
    if low in _NICKS:
        if _NICKS[low] == "":
            return None, "@reboot runs once at startup — no schedule math"
        expr = _NICKS[low]
    parts = expr.split()
    if len(parts) != 5:
        return None, f"need 5 fields (minute hour dom month dow), got {len(parts)}"
    minute = _parse_field(parts[0], 0, 59)
    hour = _parse_field(parts[1], 0, 23)
    dom = _parse_field(parts[2], 1, 31)
    month = _parse_field(parts[3], 1, 12, _MONTHS)
    dow = _parse_field(parts[4], 0, 7, _DAYS)
    for name, val in (("minute", minute), ("hour", hour), ("day-of-month", dom),
                      ("month", month), ("day-of-week", dow)):
        if val is None:
            return None, f"bad {name} field: {parts[('minute hour dom month dow'.split().index(name))]}"
    if dow and 7 in dow:               # normalize 7 -> Sunday
        dow = sorted({0 if v == 7 else v for v in dow})
    fields = {"minute": minute, "hour": hour, "dom": dom,
              "month": month, "dow": dow}
    return fields, ""


# ------------------------------------------------------------ matching

def _matches(fields, dt):
    if dt.minute not in fields["minute"]:
        return False
    if dt.hour not in fields["hour"]:
        return False
    if dt.month not in fields["month"]:
        return False
    dom_ok = dt.day in fields["dom"]
    dow_ok = (dt.weekday() + 1) % 7 in fields["dow"]
    # classic vixie-cron semantics: if both dom and dow are restricted,
    # either may match; if only one is restricted, it must match.
    dom_star = len(fields["dom"]) == 31
    dow_star = len(fields["dow"]) == 7
    if dom_star and dow_star:
        return True
    if dom_star:
        return dow_ok
    if dow_star:
        return dom_ok
    return dom_ok or dow_ok


def next_runs(expr, count=5, now=None, limit_days=366 * 5):
    """-> (list of datetimes, error). Never raises."""
    fields, err = parse_cron(expr)
    if err:
        return [], err
    now = now or datetime.now()
    dt = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    end = now + timedelta(days=limit_days)
    out = []
    while dt <= end and len(out) < count:
        if _matches(fields, dt):
            out.append(dt)
        dt += timedelta(minutes=1)
        # fast-forward through months that can never match
        if not out and dt.month not in fields["month"] and dt.day == 1 \
                and dt.hour == 0 and dt.minute == 0:
            months = sorted(fields["month"])
            nxt = next((m for m in months if m > dt.month), None)
            if nxt is None:
                try:
                    dt = dt.replace(year=dt.year + 1, month=months[0])
                except ValueError:
                    break
            else:
                dt = dt.replace(month=nxt)
    if not out:
        return [], "no runs in the next five years"
    return out, ""


# ------------------------------------------------------------- describe

def describe(expr):
    """-> (human sentence, error).  The plain-English one-liner."""
    fields, err = parse_cron(expr)
    if err:
        return "", err
    m, h = fields["minute"], fields["hour"]
    dom, mon, dow = fields["dom"], fields["month"], fields["dow"]

    def list_txt(vals, names=None, pad=0):
        if names and all(v in names.values() for v in vals):
            inv = {v: k.upper() for k, v in names.items()}
            return ", ".join(inv[v] for v in vals)
        return ", ".join(str(v).zfill(pad) for v in vals)

    bits = []
    if len(m) == 60:
        pass
    elif len(m) == 1:
        bits.append(f"at minute {m[0]}")
    else:
        bits.append(f"at minute {list_txt(m, pad=2)}")
    if len(h) != 24:
        bits.append(f"past hour {list_txt(h, pad=2)}" if len(h) > 1
                    else f"past {h[0]:02d}:00")
    if len(mon) != 12:
        bits.append(f"in {list_txt(mon, _MONTHS)}")
    dom_star = len(dom) == 31
    dow_star = len(dow) == 7
    if not dom_star and not dow_star:
        bits.append(f"on day-of-month {list_txt(dom)} or "
                    f"{list_txt(dow, _DAYS)}")
    elif not dom_star:
        bits.append(f"on day {list_txt(dom)} of the month")
    elif not dow_star:
        bits.append(f"on {list_txt(dow, _DAYS)}")
    if not bits:
        return "every minute", ""
    # single minute? merge hour+minute into clock times ("at 09:00 on MON")
    if len(m) == 1:
        if len(h) == 24:
            sentence = f"at :{m[0]:02d} past every hour"
        else:
            sentence = "at " + ", ".join(
                f"{hh:02d}:{m[0]:02d}" for hh in h)
        if len(mon) != 12:
            sentence += f" in {list_txt(mon, _MONTHS)}"
        if not dom_star and not dow_star:
            sentence += f", on day-of-month {list_txt(dom)} or " \
                        f"{list_txt(dow, _DAYS)}"
        elif not dom_star:
            sentence += f", on day {list_txt(dom)} of the month"
        elif not dow_star:
            sentence += f", on {list_txt(dow, _DAYS)}"
        return sentence, ""
    return ", ".join(bits), ""


def field_table(expr):
    """-> list of (field, raw, meaning) rows for the UI table."""
    raw = (expr or "").strip().lower()
    if raw in _NICKS and _NICKS[raw]:
        raw = _NICKS[raw]
    parts = raw.split()
    fields, err = parse_cron(expr)
    if err:
        return []
    labels = (("minute", 60, None), ("hour", 24, None),
              ("day-of-month", 31, None), ("month", 12, _MONTHS),
              ("day-of-week", 7, _DAYS))
    rows = []
    for i, (name, total, names) in enumerate(labels):
        vals = fields[{"minute": "minute", "hour": "hour",
                       "day-of-month": "dom", "month": "month",
                       "day-of-week": "dow"}[name]]
        if len(vals) == total:
            meaning = "every " + ("minute" if name == "minute" else name)
        elif names:
            meaning = ", ".join(
                sorted((k.upper() for k, v in names.items()
                        if v in vals), key=lambda x: names[x.lower()]))
        else:
            meaning = ", ".join(str(v) for v in vals)
        rows.append((name, parts[i], meaning))
    return rows


# --------------------------------------------------------------- window

class CronExplainer(tk.Toplevel):
    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.t = theme
        self.title("Cron explainer — DXN1 STUDIO")
        self.configure(bg=theme["bg"])
        self.geometry("760x520")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 760x520 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 760, 520))
        self.minsize(620, 420)
        try:
            self.transient(parent.winfo_toplevel()
                           if parent is not None else parent)
        except Exception:
            pass
        self._build()
        if initial:
            self.var.set(initial)
        self._update()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 760, 520
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        top = tk.Frame(self, bg=t["bg"])
        top.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(top, text="expression", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 10)).pack(side="left")
        self.var = tk.StringVar(value="*/15 9-17 * * mon-fri")
        self.entry = tk.Entry(top, textvariable=self.var, relief="flat",
                              bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"],
                              font=(FONT_MONO, 13), bd=0,
                              highlightthickness=1,
                              highlightbackground=t["border"],
                              highlightcolor=t.get("accent", t["hover"]))
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 8),
                        ipady=6)
        tk.Button(top, text="Decode", relief="flat", cursor="hand2",
                  bg=t["header"], fg=t["text"], bd=0, padx=14, pady=6,
                  activebackground=t["hover"],
                  activeforeground=t["text"], font=(FONT_UI, 10),
                  command=self._update).pack(side="left")
        self.var.trace_add("write", lambda *a: self._update())

        self.sentence = tk.Label(self, text="", bg=t["bg"],
                                 fg=t.get("accent", t["text_secondary"]),
                                 font=(FONT_UI, 13), wraplength=700,
                                 justify="left", anchor="w")
        self.sentence.pack(fill="x", padx=12, pady=(6, 2))

        self.error = tk.Label(self, text="", bg=t["bg"],
                              fg=t["text_secondary"], font=(FONT_UI, 10),
                              wraplength=700, justify="left", anchor="w")
        self.error.pack(fill="x", padx=12)

        cols = ("field", "value", "meaning")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Cron.Treeview", background=t["card"],
                        fieldbackground=t["card"], foreground=t["text"],
                        rowheight=24, borderwidth=0, font=(FONT_MONO, 10))
        style.configure("Cron.Treeview.Heading", background=t["header"],
                        foreground=t["text_secondary"], relief="flat",
                        font=(FONT_UI, 9))
        tw = tk.Frame(self, bg=t["border"])
        tw.pack(fill="x", padx=12, pady=(8, 0))
        self.table = ttk.Treeview(tw, columns=cols, show="headings",
                                  height=5, style="Cron.Treeview")
        for cid, label, w in (("field", "field", 130), ("value", "raw", 160),
                              ("meaning", "meaning", 380)):
            self.table.heading(cid, text=label)
            self.table.column(cid, width=w, anchor="w")
        from .theme import make_scrollbar
        _tsb = make_scrollbar(tw, t, "vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=_tsb.set)
        _tsb.pack(side="right", fill="y")
        self.table.pack(fill="x")

        tk.Label(self, text="next runs (local time)", bg=t["bg"],
                 fg=t["text_muted"], font=(FONT_UI, 9)) \
            .pack(anchor="w", padx=12, pady=(10, 2))
        self.runs = tk.Text(self, height=6, relief="flat", bg=t["editor"],
                            fg=t["text"], font=(FONT_MONO, 11), bd=0,
                            padx=10, pady=6, wrap="word", state="disabled")
        _rsb = make_scrollbar(self, t, "vertical", command=self.runs.yview)
        self.runs.configure(yscrollcommand=_rsb.set)
        _rsb.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))
        self.runs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # the door sign
        from . import hints
        self.hintbar = hints.hint_bar(
            self, t,
            notes=("type a cron expression — it decodes as you type",
                   "click Decode to refresh"))

    def _update(self):
        expr = self.var.get()
        sentence, err = describe(expr)
        try:
            self.sentence.configure(
                text=sentence if not err else "")
            self.error.configure(text=err if err else "")
            self.table.delete(*self.table.get_children(""))
            self.runs.configure(state="normal")
            self.runs.delete("1.0", "end")
            if err:
                self.runs.insert("1.0", "—")
                self.runs.configure(state="disabled")
                return
            for row in field_table(expr):
                self.table.insert("", "end", values=row)
            runs, rerr = next_runs(expr, count=5)
            self.runs.insert("1.0", "\n".join(
                d.strftime("%Y-%m-%d %a %H:%M") for d in runs)
                if not rerr else rerr)
            self.runs.configure(state="disabled")
        except tk.TclError:
            pass


def open_cron(parent, theme, initial=""):
    return CronExplainer(parent, theme, initial)
