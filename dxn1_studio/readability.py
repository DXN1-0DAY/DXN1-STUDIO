"""DXN1 STUDIO — readability report (DS2).

How hard is your prose?  Paste-free analysis of the current file —
Flesch Reading Ease, Flesch–Kincaid grade, Gunning Fog, sentence
length pressure and the words you lean on too hard.  Aimed at
READMEs, docs and long comments, but it happily judges your code
comments too.

Every engine function is pure and unit-tested; the window is a thin
skin.  Open from the palette:  "Readability report for this file…"
"""

import re
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
_VOWELS = "aeiouy"
_STOP = set("""a an the and or but if then of to in on for with as at by from
is are was were be been being it its this that these those you your we our
they their he she his her not no do does did done can could should would
will shall may might must have has had about into over under out up down
than so such very more most much many any all each other some""".split())


def words(text):
    return _WORD_RE.findall(text or "")


def sentences(text):
    """Split on ., !, ? — ellipses and abbreviations survive as one."""
    parts = re.split(r"[.!?]+(?:\s+|$)",
                     (text or "").replace("\n", " "))
    parts = [p.strip() for p in parts if p.strip()]
    return parts or ([text.strip()] if text and text.strip() else [])


def syllables(word):
    """Heuristic English syllable counter (~90% accurate on prose)."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    count = 0
    prev_vowel = False
    for ch in w:
        is_v = ch in _VOWELS
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    return max(1, count)


def _nums(text):
    ws = words(text)
    syl = sum(syllables(w) for w in ws)
    return ws, syl, max(1, len(sentences(text)))


def flesch_reading_ease(text):
    """206.835 - 1.015*ASL - 84.6*ASW  (100 = very easy, 0 = very hard)."""
    ws, syl, ns = _nums(text)
    if not ws:
        return 0.0
    asl = len(ws) / ns
    asw = syl / len(ws)
    return max(0.0, min(100.0, 206.835 - 1.015 * asl - 84.6 * asw))


def flesch_kincaid_grade(text):
    ws, syl, ns = _nums(text)
    if not ws:
        return 0.0
    asl = len(ws) / ns
    asw = syl / len(ws)
    return max(0.0, 0.39 * asl + 11.8 * asw - 15.59)


def gunning_fog(text):
    ws, _syl, ns = _nums(text)
    if not ws:
        return 0.0
    complex_n = sum(1 for w in ws if syllables(w) >= 3 and
                    not w.endswith("es") and not w.endswith("ed"))
    return 0.4 * ((len(ws) / ns) + 100.0 * complex_n / len(ws))


def grade_label(score):
    """Flesch score -> human verdict."""
    if score >= 90:
        return "very easy"
    if score >= 80:
        return "easy"
    if score >= 70:
        return "fairly easy"
    if score >= 60:
        return "plain English"
    if score >= 50:
        return "fairly difficult"
    if score >= 30:
        return "difficult"
    return "very difficult"


def stats(text):
    ws, syl, ns = _nums(text)
    if not ws:
        return {}
    long_n = sum(1 for s in sentences(text) if len(words(s)) > 25)
    complex_n = sum(1 for w in ws if syllables(w) >= 3)
    return {
        "words": len(ws),
        "sentences": len(sentences(text)),
        "syllables": syl,
        "avg_sentence_words": round(len(ws) / ns, 1),
        "long_sentences": long_n,
        "complex_words": complex_n,
        "complex_pct": round(100.0 * complex_n / len(ws), 1),
        "flesch": round(flesch_reading_ease(text), 1),
        "kincaid_grade": round(flesch_kincaid_grade(text), 1),
        "fog": round(gunning_fog(text), 1),
    }


def long_sentences(text, limit=25, cap=12):
    """-> [(word_count, preview)] longest-first, capped for the UI."""
    out = []
    for s in sentences(text):
        n = len(words(s))
        if n > limit:
            out.append((n, s.strip()[:120] + ("…" if len(s) > 120 else "")))
    out.sort(key=lambda t: -t[0])
    return out[:cap]


def top_words(text, k=12):
    """-> [(word, count)] most repeated content words (stopwords out)."""
    counts = {}
    for w in words(text):
        lw = w.lower().strip("'-")
        if lw in _STOP or len(lw) < 3:
            continue
        counts[lw] = counts.get(lw, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


def report_text(text, name="file", markdown=False):
    """Plain or markdown report — shared by the copy button and tests."""
    st = stats(text)
    if not st:
        return f"No prose found in {name}." if not markdown else \
            f"**No prose found in {name}.**"
    if markdown:
        lines = [
            f"# Readability — {name}",
            "",
            f"**Flesch {st['flesch']}** ({grade_label(st['flesch'])}) · "
            f"grade {st['kincaid_grade']} · fog {st['fog']}",
            "",
            f"- words: {st['words']} in {st['sentences']} sentences "
            f"(avg {st['avg_sentence_words']} words)",
            f"- complex words: {st['complex_words']} "
            f"({st['complex_pct']}%)",
            f"- sentences over 25 words: {st['long_sentences']}",
            "",
        ]
    else:
        lines = [
            f"Readability — {name}",
            f"Flesch {st['flesch']} ({grade_label(st['flesch'])}) · "
            f"grade {st['kincaid_grade']} · fog {st['fog']}",
            f"{st['words']} words, {st['sentences']} sentences "
            f"(avg {st['avg_sentence_words']}), complex "
            f"{st['complex_pct']}%, long sentences {st['long_sentences']}",
            "",
        ]
    longs = long_sentences(text)
    if longs:
        lines.append("Long sentences:" if not markdown else
                     "## Long sentences")
        for n, preview in longs:
            lines.append(f"  ({n} words) {preview}"
                         if not markdown else f"- ({n} words) {preview}")
        lines.append("")
    top = top_words(text)
    if top:
        lines.append("Word pressure:" if not markdown else
                     "## Word pressure")
        if markdown:
            lines += [f"- **{w}** ×{c}" for w, c in top]
        else:
            lines.append("  " + ", ".join(f"{w}×{c}" for w, c in top))
    return "\n".join(lines)


# --------------------------------------------------------------- window

class ReadabilityWindow(tk.Toplevel):
    def __init__(self, parent, theme, text="", name="file"):
        super().__init__(parent)
        self.t = theme
        self.title(f"Readability — {name}")
        self.configure(bg=theme["bg"])
        self.geometry("720x560")
        # DS2 v2.62 — width accounting round four: once the build
        # settles, open no narrower (or shorter) than what it
        # actually packed (the 720x560 default is the floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 720, 560))
        self.minsize(560, 420)
        try:
            self.transient(parent.winfo_toplevel()
                           if parent is not None else parent)
        except Exception:
            pass
        self._text = text or ""
        self._name = name
        self._build()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 720, 560
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _card(self, master, big, small, col, row):
        t = self.t
        card = tk.Frame(master, bg=t["card"],
                        highlightbackground=t["card_border"],
                        highlightthickness=1)
        card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        tk.Label(card, text=big, bg=t["card"], fg=t["text"],
                 font=(FONT_MONO, 16, "bold")).pack(pady=(10, 0))
        tk.Label(card, text=small, bg=t["card"],
                 fg=t["text_secondary"], font=(FONT_UI, 9)) \
            .pack(pady=(0, 10))
        return card

    def _build(self):
        t = self.t
        st = stats(self._text)
        head = tk.Frame(self, bg=t["bg"])
        head.pack(fill="x", padx=12, pady=(12, 0))
        if not st:
            tk.Label(head, text="No prose found in this file.",
                     bg=t["bg"], fg=t["text_secondary"],
                     font=(FONT_UI, 12)).pack(anchor="w")
            return
        verdict = grade_label(st["flesch"])
        tk.Label(head, text=f"Flesch {st['flesch']} — {verdict}",
                 bg=t["bg"], fg=t.get("accent", t["text"]),
                 font=(FONT_UI, 18, "bold")).pack(anchor="w")
        grid = tk.Frame(self, bg=t["bg"])
        grid.pack(fill="x", padx=8, pady=(8, 0))
        for c in range(4):
            grid.columnconfigure(c, weight=1)
        cards = [
            (st["words"], "words"), (st["sentences"], "sentences"),
            (st["avg_sentence_words"], "avg words / sentence"),
            (st["kincaid_grade"], "kincaid grade"),
            (st["fog"], "gunning fog"), (st["complex_pct"], "complex %"),
            (st["long_sentences"], "sentences > 25 words"),
            (st["syllables"], "syllables"),
        ]
        for i, (big, small) in enumerate(cards):
            self._card(grid, big, small, i % 4, i // 4)

        body = tk.Frame(self, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Read.Treeview", background=t["card"],
                        fieldbackground=t["card"], foreground=t["text"],
                        rowheight=24, borderwidth=0, font=(FONT_MONO, 10))
        style.configure("Read.Treeview.Heading", background=t["header"],
                        foreground=t["text_secondary"], relief="flat",
                        font=(FONT_UI, 9))
        lw = tk.Frame(body, bg=t["border"])
        lw.pack(side="left", fill="both", expand=True)
        tk.Label(lw, text="long sentences — split these", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9),
                 anchor="w", padx=8).pack(fill="x")
        cols = ("n", "preview")
        self.long_tree = ttk.Treeview(lw, columns=cols, show="headings",
                                      height=8, style="Read.Treeview")
        self.long_tree.heading("n", text="words")
        self.long_tree.heading("preview", text="sentence")
        self.long_tree.column("n", width=60, anchor="e", stretch=False)
        self.long_tree.column("preview", width=260, anchor="w")
        self.long_tree.pack(fill="both", expand=True, padx=(1, 1),
                            pady=(1, 1))
        for n, preview in long_sentences(self._text):
            self.long_tree.insert("", "end", values=(n, preview))

        rw = tk.Frame(body, bg=t["border"])
        rw.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(rw, text="word pressure — variety is oxygen",
                 bg=t["header"], fg=t["text_secondary"],
                 font=(FONT_UI, 9), anchor="w", padx=8).pack(fill="x")
        self.word_tree = ttk.Treeview(rw, columns=("w", "c"),
                                      show="headings", height=8,
                                      style="Read.Treeview")
        self.word_tree.heading("w", text="word")
        self.word_tree.heading("c", text="uses")
        self.word_tree.column("w", width=140, anchor="w")
        self.word_tree.column("c", width=60, anchor="e", stretch=False)
        self.word_tree.pack(fill="both", expand=True, padx=(1, 1),
                            pady=(1, 1))
        for w, c in top_words(self._text):
            self.word_tree.insert("", "end", values=(w, c))

        bar = tk.Frame(self, bg=t["bg"])
        bar.pack(fill="x", padx=12, pady=10)
        tk.Button(bar, text="Copy report", relief="flat", cursor="hand2",
                  bg=t["header"], fg=t["text"], bd=0, padx=14, pady=6,
                  activebackground=t["hover"],
                  activeforeground=t["text"], font=(FONT_UI, 10),
                  command=self._copy).pack(side="left")
        self.status = tk.Label(bar, text="", bg=t["bg"],
                               fg=t["text_muted"], font=(FONT_UI, 9))
        self.status.pack(side="left", padx=(10, 0))

        # the door sign
        from . import hints
        self.hintbar = hints.hint_bar(
            self, t,
            notes=("read-only report — computed from the file as it is",
                   "click Copy report for a markdown copy"))

    def _copy(self):
        try:
            data = report_text(self._text, self._name, markdown=True)
            self.clipboard_clear()
            self.clipboard_append(data)
            self.status.configure(text=f"copied {len(data)} chars "
                                       "as markdown",
                                  fg=self.t["success"])
        except tk.TclError:
            pass


def open_readability(parent, theme, text="", name="file"):
    return ReadabilityWindow(parent, theme, text, name)
