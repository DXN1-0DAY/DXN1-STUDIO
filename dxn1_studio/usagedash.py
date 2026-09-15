"""DXN1 STUDIO — token usage dashboard (DS2 v1.5).

Know what your agents actually spend. Every generation reports its token
count into a tiny local ledger (``~/.dxn1-studio/usage.json``), and this
window turns that ledger into a 14-day bar chart, per-model share bars,
per-workspace totals, cost estimates and an exportable CSV.

Estimates use published list prices for common models and clearly label
themselves as estimates — no pretending, no network calls, no accounts.
Pure stdlib, one small JSON file, trimmed to 5,000 events.
"""

import csv
import json
import os
import time
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

LEDGER_PATH = os.path.join(os.path.expanduser("~"), ".dxn1-studio",
                           "usage.json")
MAX_EVENTS = 5000

# rough published list prices (USD per 1M tokens, blended in/out).
# unknown models estimate at the median of this table.
PRICES = {
    "gpt-4o": 5.00, "gpt-4o-mini": 0.60, "gpt-4.1": 4.00,
    "gpt-4.1-mini": 1.00, "o3": 8.00, "o4-mini": 2.00,
    "claude-3-5-sonnet": 9.00, "claude-sonnet-4": 9.00,
    "claude-3-5-haiku": 2.40, "claude-opus-4": 45.00,
    "gemini-2.0-flash": 0.30, "gemini-2.5-flash": 0.60,
    "gemini-2.5-pro": 5.00, "deepseek-chat": 0.50,
    "deepseek-reasoner": 1.10, "llama-3.3-70b": 0.60,
    "mistral-large": 3.00, "qwen-2.5-72b": 0.90,
}


def est_cost_per_mtok(model):
    """Best-effort USD per 1M tokens for a model id (median if unknown)."""
    m = (model or "").lower()
    for key, price in PRICES.items():
        if key in m:
            return price
    return 2.50


class UsageLedger:
    """Append-only local ledger of generation events."""

    def __init__(self, path=None):
        self.path = path or LEDGER_PATH
        self.events = []
        self.load()

    # ---------------------------------------------------------------- io
    def load(self):
        self.events = []
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, list):
                    self.events = [e for e in data
                                   if isinstance(e, dict)]
        except (OSError, ValueError):
            self.events = []

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.events[-MAX_EVENTS:], fh)
        except OSError:
            pass

    # ------------------------------------------------------------ record
    def record(self, tokens, model="", backend="", workspace="",
               kind="chat"):
        """Add one generation event (tokens int, no network)."""
        try:
            tokens = max(0, int(tokens))
        except (TypeError, ValueError):
            return
        self.events.append({
            "t": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": (model or "?")[:60],
            "backend": (backend or "?")[:24],
            "workspace": os.path.basename(workspace or "")[:60] or "—",
            "kind": kind[:12] or "chat",
            "tokens": tokens,
        })
        if len(self.events) > MAX_EVENTS + 200:
            self.events = self.events[-MAX_EVENTS:]
        self.save()

    # --------------------------------------------------------- aggregates
    def totals(self):
        return {"events": len(self.events),
                "tokens": sum(e.get("tokens", 0) for e in self.events)}

    def today(self):
        day = time.strftime("%Y-%m-%d")
        return sum(e.get("tokens", 0) for e in self.events
                   if str(e.get("t", "")).startswith(day))

    def by_day(self, days=14):
        """Ordered list of (YYYY-MM-DD, tokens) for the last N days."""
        out = []
        stamps = [time.strftime("%Y-%m-%d",
                                time.localtime(time.time() - i * 86400))
                  for i in range(days - 1, -1, -1)]
        sums = {s: 0 for s in stamps}
        for e in self.events:
            day = str(e.get("t", ""))[:10]
            if day in sums:
                sums[day] += e.get("tokens", 0)
        return [(s, sums[s]) for s in stamps]

    def by_model(self, top=8):
        sums = {}
        for e in self.events:
            key = e.get("model", "?")
            sums[key] = sums.get(key, 0) + e.get("tokens", 0)
        return sorted(sums.items(), key=lambda kv: -kv[1])[:top]

    def by_workspace(self, top=6):
        sums = {}
        for e in self.events:
            key = e.get("workspace", "—")
            sums[key] = sums.get(key, 0) + e.get("tokens", 0)
        return sorted(sums.items(), key=lambda kv: -kv[1])[:top]

    def est_cost(self):
        cents = 0.0
        for model, tokens in self.by_model(top=999):
            cents += est_cost_per_mtok(model) * tokens / 1_000_000
        return cents

    def export_csv(self, path):
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=[
                    "t", "model", "backend", "workspace", "kind",
                    "tokens"])
                writer.writeheader()
                for e in self.events:
                    writer.writerow({k: e.get(k, "") for k in
                                     writer.fieldnames})
            return True
        except OSError:
            return False

    def wipe(self):
        self.events = []
        self.save()


def record_usage(tokens, model="", backend="", workspace="", kind="chat"):
    """One-call module-level hook — never raises, never blocks."""
    try:
        UsageLedger().record(tokens, model=model, backend=backend,
                             workspace=workspace, kind=kind)
    except Exception:  # pragma: no cover — usage must never break the IDE
        pass


# ------------------------------------------------------------------- view
class UsageDashboard(tk.Toplevel):
    """The 'where did my tokens go' window."""

    def __init__(self, parent, theme, workspace="", on_log=None):
        super().__init__(parent)
        self.t = theme
        self.workspace = workspace
        self.ledger = UsageLedger()
        self.title("Token usage")
        self.configure(bg=self.t["bg"])
        self.geometry("720x600")
        self.minsize(560, 420)
        self.transient(parent.winfo_toplevel()
                       if hasattr(parent, "winfo_toplevel") else parent)
        self._build_header()
        self._build_body()
        self._build_status()
        # v2.48 — the dashboard answers to keys, and the bar says so
        from . import hints
        self.bind("<F5>", lambda e: self.refresh())
        self.hintbar = hints.hint_bar(
            self, self.t,
            pairs=(("F5", "refresh", "F5"),),
            esc=True, before=self.status)
        self.bind("<Escape>", lambda e: self.destroy())
        self.refresh()
        self._center()

    def _center(self):
        try:
            # DS2 v2.61 — width accounting round three: the dashboard
            # fits what it packed (the 720x600 default is the floor),
            # then centers on the size it actually got
            from . import geom as _geom
            _geom.fit_to_content(self, 720, 600)
            self.update_idletasks()
            w = max(720, self.winfo_width())
            h = max(600, self.winfo_height())
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    # ------------------------------------------------------------- chrome
    def _build_header(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="≈  Token usage", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        self.pills = tk.Frame(bar, bg=t["header"])
        self.pills.pack(side=tk.LEFT, padx=8)
        for label, fn in (("Export CSV…", self._export),
                          ("Refresh", self.refresh),
                          ("Clear", None)):
            if fn is None:
                chip = tk.Label(bar, text=label, bg=t["card"],
                                fg="#f85149", font=(FONT_UI, 9),
                                cursor="hand2", padx=9, pady=4)
                chip.bind("<Button-1>",
                          lambda e, c=chip: self._guarded(c))
                chip._is_wipe = True
            else:
                chip = tk.Label(bar, text=label, bg=t["card"],
                                fg=t["text_secondary"], font=(FONT_UI, 9),
                                cursor="hand2", padx=9, pady=4)
                chip.bind("<Button-1>", lambda e, f=fn: f())
            chip.pack(side=tk.RIGHT, padx=(6, 12 if label == "Export CSV…"
                                           else 0))

    def _guarded(self, chip):
        if chip.cget("text") == "sure?":
            chip.config(text="Clear", bg=self.t["card"], fg="#f85149")
            self.ledger.wipe()
            self.refresh()
            return
        chip.config(text="sure?", bg="#f85149", fg="#ffffff")
        self.after(3000, lambda: self._revert(chip))

    def _revert(self, chip):
        try:
            if chip.cget("text") == "sure?":
                chip.config(text="Clear", bg=self.t["card"],
                            fg="#f85149")
        except tk.TclError:
            pass

    def _build_body(self):
        t = self.t
        self.body = tk.Frame(self, bg=t["bg"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

    def _build_status(self):
        t = self.t
        self.status = tk.Label(self, text="", bg=t["statusbar"],
                               fg=t["text_muted"], font=(FONT_UI, 8),
                               anchor="w")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _say(self, text):
        self.status.config(text=text)

    def _section(self, parent, text):
        tk.Label(parent, text=text, bg=self.t["bg"],
                 fg=self.t["text_muted"], font=(FONT_UI, 8, "bold"),
                 anchor="w").pack(fill=tk.X, pady=(12, 3))

    # ------------------------------------------------------------ refresh
    def refresh(self):
        self.ledger.load()
        for w in self.body.winfo_children():
            w.destroy()
        t = self.t
        totals = self.ledger.totals()
        cost = self.ledger.est_cost()

        # ---- top pills
        pills = tk.Frame(self.body, bg=t["bg"])
        pills.pack(fill=tk.X)
        pill_specs = [
            (f"{totals['tokens']:,}", "tokens total"),
            (f"{self.ledger.today():,}", "today"),
            (f"~${cost:.2f}", "est. spend"),
            (f"{totals['events']:,}", "generations"),
        ]
        for value, label in pill_specs:
            card = tk.Frame(pills, bg=t["card"], highlightthickness=1,
                            highlightbackground=t["card_border"])
            card.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
            tk.Label(card, text=value, bg=t["card"], fg=t.accent,
                     font=(FONT_MONO, 13, "bold")).pack(
                anchor="w", padx=12, pady=(8, 0))
            tk.Label(card, text=label, bg=t["card"],
                     fg=t["text_muted"],
                     font=(FONT_UI, 8)).pack(anchor="w", padx=12,
                                             pady=(0, 8))

        # ---- 14-day chart
        self._section(self.body, "LAST 14 DAYS")
        chart = tk.Canvas(self.body, height=120, bg=t["card"],
                          highlightthickness=1,
                          highlightbackground=t["card_border"])
        chart.pack(fill=tk.X)
        days = self.ledger.by_day(14)
        width = max(int(chart.winfo_width() or 680), 400)
        chart.configure(width=width)
        max_v = max([v for _d, v in days] + [1])
        n = len(days)
        bw = max(6, int((width - 40) / n) - 8)
        for i, (day, v) in enumerate(days):
            x = 20 + i * (bw + 8)
            h = int(78 * v / max_v)
            color = t.accent if v == max_v and v > 0 else \
                t["text_muted"]
            chart.create_rectangle(x, 100 - h, x + bw, 100,
                                   fill=color if v else t["hover"],
                                   outline="")
            chart.create_text(x + bw // 2, 108, anchor="n",
                              fill=t["text_muted"], font=(FONT_UI, 7),
                              text=day[5:])
            if v:
                chart.create_text(x + bw // 2, 92 - h, anchor="s",
                                  fill=t["text"], font=(FONT_MONO, 7),
                                  text=f"{v // 1000}k" if v >= 1000
                                  else str(v))
        chart.create_text(width - 14, 14, anchor="e",
                          fill=t["text_muted"], font=(FONT_UI, 7),
                          text=f"peak {max_v:,}")

        # ---- per-model share bars
        self._section(self.body, "BY MODEL")
        models = self.ledger.by_model()
        if models:
            total = sum(v for _m, v in models) or 1
            for model, v in models:
                share = v / total
                row = tk.Frame(self.body, bg=t["bg"])
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=(model[:34] or "?"), bg=t["bg"],
                         fg=t["text"], font=(FONT_MONO, 8),
                         width=36, anchor="w").pack(side=tk.LEFT)
                bar_wrap = tk.Frame(row, bg=t["bg"])
                bar_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True,
                              padx=8)
                bar = tk.Frame(bar_wrap, bg=t.accent,
                               height=10)
                bar.place(relwidth=max(0.02, share), relheight=1.0)
                bar_wrap.configure(height=10)
                bar_wrap.pack_propagate(False)
                tk.Label(row, text=f"{v:,}", bg=t["bg"],
                         fg=t["text_muted"], font=(FONT_MONO, 8)
                         ).pack(side=tk.RIGHT)
                tk.Label(row, text=f"{share * 100:.0f}%", bg=t["bg"],
                         fg=t["text_secondary"], font=(FONT_MONO, 8),
                         width=5).pack(side=tk.RIGHT)
        else:
            tk.Label(self.body,
                     text="No usage recorded yet — generate something "
                          "with DXN1 Agents and it shows up here.",
                     bg=t["bg"], fg=t["text_muted"],
                     font=(FONT_UI, 9)).pack(anchor="w", pady=6)

        # ---- per-workspace
        self._section(self.body, "BY WORKSPACE")
        ws = self.ledger.by_workspace()
        if ws:
            for name, v in ws:
                row = tk.Frame(self.body, bg=t["bg"])
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=name[:40], bg=t["bg"],
                         fg=t["text_secondary"], font=(FONT_MONO, 8),
                         anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=f"{v:,}", bg=t["bg"],
                         fg=t["text_muted"], font=(FONT_MONO, 8)
                         ).pack(side=tk.RIGHT)

    # ------------------------------------------------------------ actions
    def _export(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Export usage CSV", defaultextension=".csv",
            initialfile="dxn1-usage.csv",
            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        ok = self.ledger.export_csv(path)
        self._say("CSV exported ✓" if ok else "export failed")


def open_dashboard(parent, theme, workspace="", on_log=None):
    """Convenience opener matching the studio's dialog style."""
    return UsageDashboard(parent, theme, workspace, on_log=on_log)
