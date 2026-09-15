"""DS2 Chart Studio — paste numbers, get instant charts.

A tiny, honest charting lab: feed it any text that contains numbers
(pasted logs, CSV columns, test timings, build sizes) and it parses a
numeric series, computes the stats, and draws line / bar / histogram /
sparkline views on a Tkinter canvas. No external plotting libraries —
the canvas primitives are enough, and determinism is a feature.

Engine (parse_series / summary / scale_points / bar_rects /
histogram / sparkline) is pure and unit-tested; the window never
raises on weird input — junk tokens are skipped, empty series draw
an honest "no data" state instead of crashing.

Open with: Workshop menu, palette, terminal ``chart`` / ``charts``.
"""

import tkinter as tk

from .i18n import tr

__all__ = ["parse_series", "summary", "scale_points", "bar_rects",
           "histogram", "sparkline", "ChartStudio", "open_chart_studio"]

SPARK_CHARS = "▁▂▃▄▅▆▇█"


# --------------------------------------------------------------- engine

def parse_series(text):
    """Extract every plain number from *text* as a list of floats.

    Splits on whitespace, commas, semicolons and pipes; understands
    integers, decimals, scientific notation and a trailing '%' or
    'ms'/'px' suffix on a token. Junk tokens are skipped. Never raises.
    """
    if not isinstance(text, str):
        return []
    out = []
    for tok in text.replace("|", " ").replace(";", " ").split(","):
        for part in tok.split():
            clean = part.strip().rstrip("%").rstrip("ms").rstrip("px")
            clean = clean.rstrip("%")  # "12%%" paranoia
            try:
                out.append(float(clean))
            except ValueError:
                continue
    return out


def summary(series):
    """Descriptive stats dict for a numeric list. Empty → honest zeros."""
    if not series:
        return {"count": 0, "min": 0.0, "max": 0.0, "sum": 0.0,
                "mean": 0.0, "median": 0.0, "stdev": 0.0, "range": 0.0}
    count = len(series)
    smin, smax = min(series), max(series)
    total = float(sum(series))
    mean = total / count
    ordered = sorted(series)
    mid = count // 2
    if count % 2:
        median = float(ordered[mid])
    else:
        median = (ordered[mid - 1] + ordered[mid]) / 2.0
    var = sum((v - mean) ** 2 for v in series) / count
    stdev = var ** 0.5
    return {"count": count, "min": smin, "max": smax, "sum": total,
            "mean": mean, "median": median, "stdev": stdev,
            "range": smax - smin}


def scale_points(series, width, height, pad=10.0):
    """Line-chart pixel points (x, y) for a series. Never raises.

    A flat series (all equal) draws a mid-height line; a single point
    is centered; empty returns [].
    """
    try:
        width = float(width)
        height = float(height)
        pad = float(pad)
    except (TypeError, ValueError):
        return []
    if not series or width <= 0 or height <= 0:
        return []
    lo, hi = min(series), max(series)
    span = hi - lo
    inner_w = max(width - 2 * pad, 1.0)
    inner_h = max(height - 2 * pad, 1.0)
    count = len(series)
    pts = []
    for i, v in enumerate(series):
        x = pad + (inner_w * i / (count - 1)) if count > 1 else width / 2
        if span <= 0:
            y = height / 2
        else:
            y = pad + inner_h * (1.0 - (v - lo) / span)
        pts.append((round(x, 1), round(y, 1)))
    return pts


def bar_rects(series, width, height, gap=4.0, pad=10.0):
    """Bar-chart rectangles (x, y, w, h). Empty → []. Never raises."""
    try:
        width = float(width)
        height = float(height)
        gap = float(gap)
        pad = float(pad)
    except (TypeError, ValueError):
        return []
    if not series or width <= 0 or height <= 0:
        return []
    hi = max(max(series), 0.0)
    lo = min(min(series), 0.0)
    span = hi - lo if hi > lo else 1.0
    inner_h = max(height - 2 * pad, 1.0)
    slot = (width - 2 * pad + gap) / len(series)
    bar_w = max(slot - gap, 1.0)
    zero_y = pad + inner_h * (hi / span)
    rects = []
    for i, v in enumerate(series):
        x = pad + i * slot
        h = inner_h * (abs(v) / span)
        if v >= 0:
            y = zero_y - h
        else:
            y = zero_y
        rects.append((round(x, 1), round(y, 1), round(bar_w, 1),
                      round(h, 1)))
    return rects


def histogram(series, bins=8):
    """Bin counts for a distribution view. Empty → [].

    Returns [(bin_lo, bin_hi, count), ...]; a constant series gets a
    single full-height bin instead of dividing by zero.
    """
    if not series:
        return []
    try:
        bins = int(bins)
    except (TypeError, ValueError):
        bins = 8
    bins = max(1, min(bins, 64))
    lo, hi = min(series), max(series)
    if hi <= lo:
        return [(lo, hi, len(series))]
    step = (hi - lo) / bins
    counts = [0] * bins
    for v in series:
        idx = int((v - lo) / step)
        if idx >= bins:  # the max value belongs to the last bin
            idx = bins - 1
        counts[idx] += 1
    return [(round(lo + i * step, 4), round(lo + (i + 1) * step, 4),
             counts[i]) for i in range(bins)]


def sparkline(series, width=40):
    """Unicode sparkline string; empty → ''. Deterministic."""
    if not series:
        return ""
    try:
        width = max(1, int(width))
    except (TypeError, ValueError):
        width = 40
    # bucket-compress long series into *width* buckets (mean per bucket)
    if len(series) > width:
        bucket = len(series) / width
        compact = []
        for b in range(width):
            start = int(b * bucket)
            end = max(int((b + 1) * bucket), start + 1)
            chunk = series[start:end]
            compact.append(sum(chunk) / len(chunk))
        series = compact
    lo, hi = min(series), max(series)
    if hi <= lo:
        mid = len(SPARK_CHARS) // 2
        return SPARK_CHARS[mid] * len(series)
    out = []
    for v in series:
        idx = int((v - lo) / (hi - lo) * (len(SPARK_CHARS) - 1))
        out.append(SPARK_CHARS[idx])
    return "".join(out)


# --------------------------------------------------------------- window

SAMPLE_DATA = (
    "build times (ms)\n"
    "412 388 401 356 342 371 365 340 352 331\n"
    "318 322 299 305 288 291 275 280 262 270\n"
)


class ChartStudio(tk.Toplevel):
    """Paste-numbers charting window. Never raises on junk input."""

    KINDS = ("line", "bar", "histogram")

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Chart Studio — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("760x560")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 760x560 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 760, 560))
        self.minsize(560, 420)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="chart studio", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=(10, 8), pady=8)
        self.kind = tk.StringVar(value="line")
        for k in self.KINDS:
            tk.Radiobutton(top, text=k, value=k, variable=self.kind,
                           command=self.refresh, bg=t.get("header",
                                                          "#242432"),
                           fg=t.get("text", "#e8e8f0"),
                           selectcolor=t.get("editor_bg", "#1a1a24"),
                           activebackground=t.get("header", "#242432"),
                           activeforeground=t.get("text", "#e8e8f0"),
                           highlightthickness=0).pack(side=tk.LEFT,
                                                      padx=2)
        tk.Button(top, text="sample", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._load_sample).pack(side=tk.RIGHT,
                                                  padx=(4, 10), pady=6)

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True)

        # left: data input
        left = tk.Frame(body, bg=t.get("bg", "#16161e"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                  padx=(10, 4), pady=10)
        tk.Label(left, text="data (any text with numbers)",
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.input = tk.Text(left, width=30, height=10, wrap="word",
                             bg=t.get("editor_bg", "#1a1a24"),
                             fg=t.get("text", "#e8e8f0"),
                             insertbackground=t.get("text", "#fff"),
                             relief=tk.FLAT, padx=8, pady=6)
        from .theme import make_scrollbar
        _sb = make_scrollbar(left, t, "vertical", command=self.input.yview)
        self.input.configure(yscrollcommand=_sb.set)
        _sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(4, 0))
        self.input.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.input.insert("1.0", initial or SAMPLE_DATA)
        self.input.bind("<KeyRelease>", lambda _e: self._schedule())

        # right: canvas + stats
        right = tk.Frame(body, bg=t.get("bg", "#16161e"))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                   padx=(4, 10), pady=10)
        self.canvas = tk.Canvas(right, height=240,
                                bg=t.get("editor_bg", "#1a1a24"),
                                highlightthickness=0)
        self.canvas.pack(fill=tk.X)
        self.stats = tk.Label(right, justify=tk.LEFT, anchor="nw",
                              bg=t.get("bg", "#16161e"),
                              fg=t.get("text", "#e8e8f0"))
        self.stats.pack(fill=tk.X, pady=(8, 0))
        self.spark_label = tk.Label(right, anchor="w",
                                    bg=t.get("bg", "#16161e"),
                                    fg=t.get("accent", "#7aa2f7"),
                                    font=("TkFixedFont", 11))
        self.spark_label.pack(fill=tk.X, pady=(6, 0))

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text="ready",
                               anchor="w", bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text=tr("chart.copy_stats"), relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_stats).pack(side=tk.RIGHT,
                                                 padx=4, pady=4)
        tk.Button(bottom, text="redraw", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self.refresh).pack(side=tk.RIGHT, padx=4)

        self._after_id = None
        self.refresh()

    # ---------------------------------------------------- behaviour
    def _load_sample(self):
        self.input.delete("1.0", "end")
        self.input.insert("1.0", SAMPLE_DATA)
        self.refresh()

    def _schedule(self):
        """Debounce live redraws (300 ms) so typing stays smooth."""
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._after_id = self.after(300, self.refresh)
        except Exception:
            pass

    def refresh(self):
        """Re-parse + redraw. Junk-tolerant by design — never raises."""
        try:
            import time as _t
            t0 = _t.perf_counter()
            text = self.input.get("1.0", "end")
            series = parse_series(text)
            self.canvas.delete("all")
            w = max(self.canvas.winfo_width(), 320)
            h = max(self.canvas.winfo_height(), 240)
            accent = self.theme.get("accent", "#7aa2f7")
            muted = self.theme.get("text_muted", "#8a8a9a")
            if not series:
                self.canvas.create_text(
                    w / 2, h / 2, text="no numbers yet — paste data on "
                    "the left", fill=muted, font=("TkDefaultFont", 11))
                self.stats.config(text="")
                self.spark_label.config(text="")
                self.status.config(text="waiting for data")
                return
            kind = self.kind.get()
            if kind == "line":
                pts = scale_points(series, w, h)
                for i in range(1, len(pts)):
                    self.canvas.create_line(*pts[i - 1], *pts[i],
                                            fill=accent, width=2)
                for (x, y) in pts:
                    self.canvas.create_oval(x - 2.5, y - 2.5,
                                            x + 2.5, y + 2.5,
                                            fill=accent, outline="")
            elif kind == "bar":
                accent2 = self.theme.get("accent2", "#bb9af7")
                for (x, y, bw, bh) in bar_rects(series, w, h):
                    self.canvas.create_rectangle(
                        x, y, x + bw, y + bh, fill=accent2,
                        outline="", width=0)
            else:  # histogram
                bins = histogram(series, bins=min(12, max(4, len(series)
                                                          // 2)))
                lo, hi = min(series), max(series)
                for j, (blo, bhi, count) in enumerate(bins):
                    frac = count / max(b[2] for b in bins)
                    bh = (h - 20) * frac
                    bw = (w - 20) / len(bins)
                    x = 10 + j * bw
                    self.canvas.create_rectangle(
                        x, h - 10 - bh, x + bw - 2, h - 10,
                        fill=self.theme.get("accent", "#7aa2f7"),
                        outline="", width=0)
                self.canvas.create_text(
                    w / 2, 8, anchor="n", fill=muted,
                    font=("TkFixedFont", 8),
                    text="min %.4g · max %.4g" % (lo, hi))
            s = summary(series)
            self.stats.config(text=(
                "n={count}  min={min:.6g}  max={max:.6g}  "
                "mean={mean:.6g}\nmedian={median:.6g}  stdev="
                "{stdev:.6g}  range={range:.6g}  sum={sum:.6g}"
            ).format(**s))
            self.spark_label.config(
                text=sparkline(series, width=48) or " ")
            ms = (_t.perf_counter() - t0) * 1000
            self.status.config(
                text="%s · %d points · render %.1f ms" %
                     (kind, len(series), ms))
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="render hiccup (input kept)")

    def _copy_stats(self):
        try:
            text = self.stats.cget("text")
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text="stats copied to clipboard")
        except Exception:
            pass


def open_chart_studio(parent, theme, initial=""):
    """Public entry: open the Chart Studio window. Never raises."""
    try:
        win = ChartStudio(parent, theme, initial=initial)
        win.grab_release()
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
