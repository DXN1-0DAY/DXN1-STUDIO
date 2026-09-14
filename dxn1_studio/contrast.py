"""DXN1 STUDIO — theme contrast auditor (DS2 v2.26).

WCAG 2.x contrast audit for every palette the studio can wear. The
engine walks thirteen semantic text pairs per theme (body text on
background/sidebar/header/card/terminal/statusbar, secondary and
muted text, gutter numbers, selection-on-accent, success and overlay
text), grades each pair (AAA / AA / AA-L / FAIL) and, when a pair
falls short of AA, searches for the closest simple fix — lighten or
darken the foreground until it clears 4.5:1.

Color math is reused from colorkit (relative luminance, contrast
ratio, lighten/darken) — nothing here re-implements WCAG. Every
engine function is junk-tolerant: non-dicts, unknown keys and
unparseable colors produce honest "n/a" rows instead of exceptions,
so the window can never crash on a half-written community theme.
"""

import tkinter as tk
import tkinter.ttk as ttk

from .colorkit import (contrast_ratio, darken, hex_to_rgb,
                       lighten, relative_luminance)
from .i18n import tr

# ----------------------------------------------------------------- engine

GRADE_LIMITS = (("AAA", 7.0), ("AA", 4.5), ("AA-L", 3.0))


def grade(ratio):
    """WCAG grade label for a ratio: AAA / AA / AA-L / FAIL."""
    try:
        r = float(ratio)
    except (TypeError, ValueError):
        return "FAIL"
    if r != r or r in (float("inf"),):  # NaN guard
        return "FAIL"
    for label, floor in GRADE_LIMITS:
        if r >= floor:
            return label
    return "FAIL"


def fmt_ratio(ratio):
    """Human ratio text: 21:1, 4.53:1 — trailing zeros trimmed."""
    try:
        r = float(ratio)
    except (TypeError, ValueError):
        return "n/a"
    return ("%.2f" % r).rstrip("0").rstrip(".") + ":1"


def _bg_of(pal):
    """Background color from a dict palette or a Theme-like object
    (anything indexable); '' when unavailable. Never raises."""
    try:
        if isinstance(pal, dict):
            return pal.get("bg", "")
        return pal["bg"]
    except Exception:  # noqa: BLE001 — junk palette
        return ""


def mode_of(palette):
    """'dark' or 'light', judged by the background's luminance.
    Accepts plain dicts and the studio's Theme wrapper alike."""
    rgb = hex_to_rgb(_bg_of(palette))
    if rgb and relative_luminance(*rgb) >= 0.5:
        return "light"
    return "dark"


def suggest_fg(fg, bg, target=4.5):
    """Closest simple fix for a weak pair: step the fg color until it
    clears ``target`` against ``bg``. Lighten on dark backgrounds,
    darken on light ones, then try the other direction for mid-tones.
    Returns a hex string, or None when already passing / unfixable /
    junk input. Pure function — no I/O, never raises."""
    try:
        target = max(1.0, min(21.0, float(target)))
    except (TypeError, ValueError):
        target = 4.5
    base = contrast_ratio(fg, bg)
    if base <= 0.0:          # junk colors — honest "no suggestion"
        return None
    if base >= target:       # already passing — nothing to fix
        return None
    rgb = hex_to_rgb(bg)
    bg_lum = relative_luminance(*rgb) if rgb else 0.0
    primary = lighten if bg_lum < 0.5 else darken
    fallback = darken if bg_lum < 0.5 else lighten
    for op in (primary, fallback):
        for step in range(2, 101, 2):
            cand = op(fg, step)
            if cand and contrast_ratio(cand, bg) >= target:
                return cand
    return None


# thirteen semantic text pairs every theme must survive
PAIR_SPECS = (
    ("body text / background", "text", "bg"),
    ("body text / sidebar", "text", "sidebar"),
    ("body text / header bar", "text", "header"),
    ("body text / card", "text", "card"),
    ("body text / terminal", "text", "terminal"),
    ("body text / status bar", "text", "statusbar"),
    ("secondary text / background", "text_secondary", "bg"),
    ("secondary text / card", "text_secondary", "card"),
    ("muted text / background", "text_muted", "bg"),
    ("line numbers / gutter", "linenum_fg", "linenum_bg"),
    ("selection text / highlight", "select_fg", "@accent"),
    ("success text / background", "success", "bg"),
    ("overlay text / dialog", "overlay_text", "overlay"),
)

_ACCENTS_FALLBACK = {"dark": "#8b5cf6", "light": "#7c3aed"}


def audit_palette(palette, accent_hex=None):
    """Audit one palette → list of row dicts (label, fg, bg, ratio,
    grade, suggestion). Junk-tolerant: missing keys and unparseable
    colors become honest FAIL/n-a rows instead of exceptions."""
    pal = palette if isinstance(palette, dict) else {}
    accent = accent_hex
    if not accent:
        accent = _ACCENTS_FALLBACK.get(mode_of(pal), "#8b5cf6")
    rows = []
    for label, fg_key, bg_key in PAIR_SPECS:
        fg = pal.get(fg_key, "")
        bg = accent if bg_key == "@accent" else pal.get(bg_key, "")
        if not fg or not bg:
            rows.append({"label": label, "fg": str(fg or "n/a"),
                         "bg": str(bg or "n/a"), "ratio": 0.0,
                         "grade": "FAIL", "suggestion": "—"})
            continue
        ratio = contrast_ratio(fg, bg)
        sug = "—"
        if 0.0 < ratio < 4.5:
            fixed = suggest_fg(fg, bg, 4.5)
            if fixed:
                sug = fixed
        rows.append({"label": label, "fg": str(fg), "bg": str(bg),
                     "ratio": float(ratio), "grade": grade(ratio),
                     "suggestion": sug})
    return rows


def audit_summary(rows):
    """Counts + worst pair + average ratio for one audit run."""
    rows = list(rows or [])
    total = len(rows)
    grades = [r["grade"] for r in rows]
    ratios = [r["ratio"] for r in rows
              if isinstance(r.get("ratio"), (int, float)) and r["ratio"] > 0]
    worst = None
    if rows:
        worst_row = min(rows, key=lambda r: r["ratio"]
                        if isinstance(r.get("ratio"), (int, float)) else 0)
        worst = worst_row["label"]
    return {
        "total": total,
        "AAA": grades.count("AAA"),
        "AA": grades.count("AA"),
        "AA-L": grades.count("AA-L"),
        "FAIL": grades.count("FAIL"),
        "avg": round(sum(ratios) / len(ratios), 2) if ratios else 0.0,
        "worst": worst,
        "pass_pct": round(100.0 * (total - grades.count("FAIL")) / total, 1)
        if total else 0.0,
    }


def iter_auditable_themes():
    """(name, palette) for every theme the studio can wear: the two
    built-ins, the community gallery, and any user-saved themes."""
    from .theme import PALETTES
    out = [("Built-in · Dark", dict(PALETTES.get("dark", {}))),
           ("Built-in · Light", dict(PALETTES.get("light", {})))]
    try:
        from .community_themes import GALLERY, user_themes
        for entry in GALLERY:
            name, _mode, pal = (list(entry) + ["", "", {}])[:3]
            out.append((str(name), dict(pal or {})))
        for name, pal in (user_themes() or {}).items():
            out.append((str(name), dict(pal or {})))
    except Exception:  # noqa: BLE001 — gallery optional
        pass
    return out


def report_text(name, rows, summary):
    """Plain-text audit report for the clipboard — one line per pair,
    fixes inline, summary footer. Never raises."""
    name = str(name or "theme")
    lines = ["CONTRAST AUDIT — %s" % name, ""]
    for r in rows or []:
        lines.append("%-5s %8s  %-28s %s on %s" %
                     (r.get("grade", "?"), fmt_ratio(r.get("ratio")),
                      r.get("label", "?"), r.get("fg", "?"),
                      r.get("bg", "?")))
        sug = r.get("suggestion") or "—"
        if sug not in ("—", ""):
            lines.append("%34s fix -> %s (AA)" % ("", sug))
    s = summary or audit_summary(rows)
    lines += ["", "pairs %d · AAA %d · AA %d · AA-L %d · FAIL %d"
              % (s.get("total", 0), s.get("AAA", 0), s.get("AA", 0),
                 s.get("AA-L", 0), s.get("FAIL", 0)),
              "avg %s · worst: %s" % (fmt_ratio(s.get("avg")),
                                      s.get("worst") or "n/a")]
    return "\n".join(lines)


# ----------------------------------------------------------------- window

class ContrastAudit(tk.Toplevel):
    """Theme contrast auditor window. Never raises on junk themes."""

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Contrast Auditor — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("860x520")
        self.minsize(680, 400)
        try:
            self.transient(parent)
        except Exception:
            pass

        self.themes = iter_auditable_themes()
        self.names = [n for n, _p in self.themes]

        # grade colors — theme-aware where possible, honest constants
        dark = mode_of(t) == "dark"
        self.c_ok = t.get("success", "#3fb950" if dark else "#1a7f37")
        self.c_warn = "#d29922" if dark else "#9a6700"
        self.c_bad = "#f85149" if dark else "#cf222e"

        header = tk.Frame(self, bg=t.get("header", "#242432"))
        header.pack(fill=tk.X)
        tk.Label(header, text="contrast auditor — WCAG grades for "
                              "every theme the studio can wear",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=10, pady=8)
        self.summary = tk.Label(header, text="", anchor="e",
                                bg=t.get("header", "#242432"),
                                fg=t.get("success", "#3fb950"))
        self.summary.pack(side=tk.RIGHT, padx=10)

        bar = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bar.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(bar, text="theme:", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(side=tk.LEFT)
        self.var = tk.StringVar(
            value=initial if initial in self.names
            else (self.names[0] if self.names else ""))
        box = ttk.Combobox(bar, textvariable=self.var, values=self.names,
                           state="readonly", width=30)
        box.pack(side=tk.LEFT, padx=(6, 8))
        box.bind("<<ComboboxSelected>>", lambda _e: self._audit())
        tk.Button(bar, text="re-audit", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._audit).pack(side=tk.LEFT)

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Contrast.Treeview",
                        background=t.get("card", "#1a1a24"),
                        fieldbackground=t.get("card", "#1a1a24"),
                        foreground=t.get("text", "#e8e8f0"),
                        rowheight=24, borderwidth=0)
        style.configure("Contrast.Treeview.Heading",
                        background=t.get("header", "#242432"),
                        foreground=t.get("text_muted", "#8a8a9a"),
                        relief="flat")
        style.map("Contrast.Treeview",
                  background=[("selected", t.get("hover", "#2a2a3a"))])

        cols = ("pair", "fg", "bg", "ratio", "grade", "fix")
        self.tree = ttk.Treeview(body, columns=cols, show="headings",
                                 style="Contrast.Treeview")
        for cid, text, width, anchor in (
                ("pair", "text pair", 220, "w"),
                ("fg", "fg", 82, "w"), ("bg", "bg", 82, "w"),
                ("ratio", "ratio", 70, "e"),
                ("grade", "grade", 62, "center"),
                ("fix", "suggested fix (AA)", 120, "w")):
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=width, anchor=anchor,
                             stretch=(cid in ("pair", "fix")))
        vsb = ttk.Scrollbar(body, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.tag_configure("aaa", foreground=self.c_ok)
        self.tree.tag_configure("aa", foreground=self.c_ok)
        self.tree.tag_configure("aal", foreground=self.c_warn)
        self.tree.tag_configure("fail", foreground=self.c_bad)

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(
            bottom, text=tr("contrast.audit_hint"), anchor="w",
            bg=t.get("bg", "#16161e"),
            fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text=tr("contrast.copy_report"),
                  relief=tk.FLAT, bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_report).pack(side=tk.RIGHT,
                                                  padx=8, pady=4)

        self._audit()

    # ------------------------------------------------------------- actions
    def current_rows(self):
        pal = dict(self.themes)[self.var.get()] \
            if self.var.get() in dict(self.themes) else {}
        return audit_palette(pal)

    def _audit(self):
        """Re-run the audit for the selected theme. Never raises."""
        try:
            rows = self.current_rows()
            s = audit_summary(rows)
            self.tree.delete(*self.tree.get_children())
            tag_map = {"AAA": "aaa", "AA": "aa", "AA-L": "aal",
                       "FAIL": "fail"}
            for r in rows:
                self.tree.insert("", tk.END, values=(
                    r["label"], r["fg"], r["bg"],
                    fmt_ratio(r["ratio"]), r["grade"],
                    r["suggestion"] if r["suggestion"] != "—" else "—"),
                    tags=(tag_map.get(r["grade"], "fail"),))
            color = self.c_bad if s["FAIL"] else self.c_ok
            self.summary.configure(
                text="13 pairs · %d pass · %d fail · avg %s"
                     % (s["total"] - s["FAIL"], s["FAIL"],
                        fmt_ratio(s["avg"])),
                fg=color)
            self.status.configure(
                text="%s · worst: %s" % (tr("contrast.audit_hint"),
                                         s["worst"] or "n/a"))
        except Exception:  # noqa: BLE001 — the window stays alive
            try:
                self.status.configure(text="audit failed — "
                                           "theme looks unreadable")
            except Exception:
                pass

    def _copy_report(self):
        try:
            rows = self.current_rows()
            text = report_text(self.var.get(), rows,
                               audit_summary(rows))
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.configure(text="report copied — %d lines"
                                       % len(text.splitlines()))
        except Exception:  # noqa: BLE001
            self.status.configure(text="copy failed — nothing audited")

    def refresh(self):
        self._audit()


def open_contrast(parent, theme, initial=""):
    """Public entry — open the Contrast Auditor window."""
    return ContrastAudit(parent, theme, initial=initial)


if __name__ == "__main__":  # pragma: no cover — engine demo
    for name, pal in iter_auditable_themes():
        s = audit_summary(audit_palette(pal))
        print("%-20s AAA %2d  AA %d  AA-L %d  FAIL %d  avg %.2f"
              % (name, s["AAA"], s["AA"], s["AA-L"], s["FAIL"], s["avg"]))
