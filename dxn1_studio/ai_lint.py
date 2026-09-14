"""DXN1 STUDIO — AI code review (DS2 v1.6).

A focused reviewer for the file in the editor: the AI reads the code
and answers with a strict JSON list of findings — each with a line
number, severity (error / warn / info), a short title and a concrete
suggestion. The review window lists findings with severity colours,
clicking one jumps to that line in the editor, and a footer shows how
many issues were found.

Response parsing is deliberately forgiving: if the model wraps JSON in
fences or adds prose, the extractor recovers it; if parsing fails
entirely, the raw text is shown so the review is never lost.
"""

import json
import re
import threading
import tkinter as tk
from tkinter import ttk

from . import errors
from .theme import FONT_UI, FONT_MONO

SEVERITY_STYLE = {
    "error": ("#f85149", "✖"),
    "warn": ("#e3b341", "▲"),
    "info": ("#60a5fa", "ℹ"),
}
VALID_SEVERITIES = set(SEVERITY_STYLE)

SYSTEM_PROMPT = (
    "You are a meticulous but pragmatic code reviewer for DXN1 STUDIO. "
    "Review the given file and reply with ONLY a JSON array — no prose, "
    "no fences — of findings: "
    '[{"line": <int>, "severity": "error|warn|info", "title": "<short>", '
    '"detail": "<one or two sentences, concrete and actionable"}]. '
    "Report only real issues (bugs, race conditions, leaks, logic "
    "errors, security footguns, misleading names). Max 10 findings, "
    "most important first. If the code is clean, reply with [].")


def parse_findings(text):
    """Extract findings from a (possibly messy) model answer."""
    if not text:
        return []
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end > start:
            cleaned = cleaned[start:end + 1]
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return []
    findings = []
    if isinstance(data, list):
        for item in data[:20]:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity", "info")).lower()
            if severity not in VALID_SEVERITIES:
                severity = "info"
            try:
                line = max(1, int(item.get("line", 0) or 1))
            except (TypeError, ValueError):
                line = 1
            findings.append({
                "line": line,
                "severity": severity,
                "title": str(item.get("title", "finding"))[:90],
                "detail": str(item.get("detail", ""))[:400],
            })
    return findings


class AIReviewWindow(tk.Toplevel):
    """Findings list with severity colours and line jumps."""

    def __init__(self, parent, theme, filename, on_goto_line=None,
                 on_log=None):
        super().__init__(parent)
        self.t = theme
        self.filename = filename or "untitled"
        self.on_goto_line = on_goto_line or (lambda line: None)
        self.on_log = on_log or (lambda msg: None)
        self.title(f"AI Review — {self.filename}")
        self.configure(bg=self.t["bg"])
        self.geometry("680x520")
        self.minsize(460, 320)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 680, 520
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="◎  AI REVIEW", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        self.title_lbl = tk.Label(bar, text=self.filename, bg=t["header"],
                                  fg=t["text_muted"], font=(FONT_MONO, 8))
        self.title_lbl.pack(side=tk.LEFT, padx=8)
        self.status = tk.Label(bar, text="", bg=t["header"],
                               fg=t["text_muted"], font=(FONT_UI, 8))
        self.status.pack(side=tk.RIGHT, padx=12)

        wrap = tk.Frame(self, bg=t["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(10, 4))
        self.canvas = tk.Canvas(wrap, bg=t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.list = tk.Frame(self.canvas, bg=t["bg"])
        self._win = self.canvas.create_window((0, 0), window=self.list,
                                              anchor="nw", width=620)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.list.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))

        self.raw = tk.Text(self, bg=t["editor"], fg=t["text"],
                           relief=tk.FLAT, font=(FONT_MONO, 9),
                           wrap=tk.WORD, height=0)

    # -------------------------------------------------------------- rows
    def clear(self):
        for w in self.list.winfo_children():
            w.destroy()

    def show_pending(self):
        self.clear()
        self._set_status("reviewing…")
        card = tk.Frame(self.list, bg=self.t["card"], highlightthickness=1,
                        highlightbackground=self.t["card_border"])
        card.pack(fill=tk.X, pady=4)
        tk.Label(card, text="Reading the file and thinking…",
                 bg=self.t["card"], fg=self.t["text_muted"],
                 font=(FONT_UI, 9)).pack(anchor="w", padx=12, pady=10)

    def show_findings(self, findings, raw_text=""):
        self.clear()
        t = self.t
        if not findings:
            if raw_text.strip():
                self._set_status("review returned prose — shown below")
                box = tk.Frame(self.list, bg=t["card"], highlightthickness=1,
                               highlightbackground=t["card_border"])
                box.pack(fill=tk.BOTH, expand=True, pady=4)
                txt = tk.Text(box, bg=t["editor"], fg=t["text"],
                              relief=tk.FLAT, font=(FONT_MONO, 9),
                              wrap=tk.WORD, height=16)
                txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
                txt.insert("1.0", raw_text)
                txt.configure(state=tk.DISABLED)
            else:
                self._set_status("no issues found ✓")
                card = tk.Frame(self.list, bg=t["card"], highlightthickness=1,
                                highlightbackground=t["card_border"])
                card.pack(fill=tk.X, pady=4)
                tk.Label(card, text="✓  Clean — the reviewer found nothing "
                         "worth flagging.", bg=t["card"], fg=t["success"],
                         font=(FONT_UI, 10, "bold")).pack(anchor="w",
                                                          padx=12, pady=12)
            return
        self._set_status(f"{len(findings)} finding"
                         f"{'s' if len(findings) != 1 else ''}")
        for f in findings:
            color, glyph = SEVERITY_STYLE.get(f["severity"],
                                              SEVERITY_STYLE["info"])
            card = tk.Frame(self.list, bg=t["card"], highlightthickness=1,
                            highlightbackground=t["card_border"])
            card.pack(fill=tk.X, pady=2)
            head = tk.Frame(card, bg=t["card"])
            head.pack(fill=tk.X)
            tk.Label(head, text=glyph, bg=t["card"], fg=color,
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT,
                                                      padx=(10, 4), pady=6)
            tk.Label(head, text=f["title"], bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 9, "bold")).pack(side=tk.LEFT)
            jump = tk.Label(head, text=f"line {f['line']}", bg=t["card"],
                            fg=t.accent, font=(FONT_MONO, 8, "bold"),
                            cursor="hand2")
            jump.pack(side=tk.RIGHT, padx=10)
            jump.bind("<Button-1>",
                      lambda e, line=f["line"]: self._goto(line))
            if f["detail"]:
                tk.Label(card, text=f["detail"], bg=t["card"],
                         fg=t["text_secondary"], font=(FONT_UI, 8),
                         anchor="w", justify=tk.LEFT,
                         wraplength=560).pack(fill=tk.X, padx=(34, 10),
                                              pady=(0, 8))

    def _goto(self, line):
        self.on_goto_line(line)
        self.on_log(f"AI review: jumped to line {line}")

    def _set_status(self, text):
        try:
            self.status.config(text=text)
        except tk.TclError:
            pass


def review_current_file(app):
    """Review the editor's current file with the configured brain."""
    editor = getattr(app, "editor", None)
    text_widget = getattr(editor, "text", None)
    if text_widget is None:
        return None
    code = text_widget.get("1.0", "end-1c")
    if not code.strip():
        try:
            app.toast("Nothing to review — open a file first.", "error")
        except Exception:
            pass
        return None
    try:
        from . import llm
        backend = llm.build_backend(app.config)
    except Exception:
        backend = None
    if backend is None:
        try:
            app.toast("AI review needs a brain — connect one in DXN1 "
                      "Agents settings.", "error")
        except Exception:
            pass
        return None

    filename = getattr(editor, "path", "") or "untitled"
    import os
    short = os.path.basename(filename)
    win = AIReviewWindow(app.root, app.theme, short,
                         on_goto_line=lambda line: (
                             getattr(editor, "goto_line", lambda n: None)(line),
                             text_widget.mark_set(tk.INSERT, f"{line}.0"),
                             text_widget.see(f"{line}.0")),
                         on_log=lambda m: app.toast(m))
    win.show_pending()

    def worker():
        answer = ""
        try:
            answer = backend.chat(
                [{"role": "system", "content": SYSTEM_PROMPT},
                 {"role": "user",
                  "content": f"File: {filename}\n\n```\n{code}\n```"}],
                max_tokens=1400, temperature=0.15)
        except Exception as exc:  # noqa: BLE001 — report inside the window
            errors.log_exception("ai review failed")
            answer = ""
            error = str(exc)
        else:
            error = None

        def deliver():
            findings = parse_findings(answer)
            if error and not findings:
                win.show_findings([], f"⚠ Review failed: {error}")
            else:
                win.show_findings(findings, raw_text=answer)

        try:
            win.after(0, deliver)
        except tk.TclError:
            pass  # window closed before the review landed

    threading.Thread(target=worker, daemon=True).start()
    return win


def palette_command(app):
    """Palette entry tuple for the review action."""
    return ("AI: review this file for issues", "DS2",
            lambda: review_current_file(app))
