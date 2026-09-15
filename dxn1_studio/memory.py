"""DXN1 STUDIO — per-workspace agent memory (DS2 v1.5).

Agents forget everything between sessions. This module fixes that:
a tiny JSON "memory bank" per workspace (``<workspace>/.dxn1/memory.json``)
stores durable facts ("this project uses pytest", "the user prefers
tabs"), preferences and a rolling summary. Before every agent turn the
bank is rendered into a compact context block and injected into the
system prompt — so the agent opens every conversation already knowing
the project.

The file lives inside the workspace, which means memory travels with
the project (git-committable if the user wants, ignored if not — their
call, we never touch .gitignore ourselves).
"""

import json
import os
import time
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

BANK_DIR = ".dxn1"
BANK_FILE = "memory.json"
MAX_FACTS = 64
MAX_RECALL_CHARS = 1500


def _bank_path(workspace):
    return os.path.join(workspace or "", BANK_DIR, BANK_FILE)


class MemoryBank:
    """Tiny JSON-backed memory for one workspace."""

    def __init__(self, workspace):
        self.workspace = workspace or ""
        self.path = _bank_path(self.workspace)
        self.facts = []       # [{id, text, created, source}]
        self.prefs = {}       # {key: value}
        self.summary = ""     # rolling conversation summary
        self.load()

    # ---------------------------------------------------------------- io
    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    facts = data.get("facts", [])
                    self.facts = facts if isinstance(facts, list) else []
                    prefs = data.get("prefs", {})
                    self.prefs = prefs if isinstance(prefs, dict) else {}
                    self.summary = str(data.get("summary") or "")
        except (OSError, json.JSONDecodeError, ValueError):
            self.facts, self.prefs, self.summary = [], {}, ""

    def save(self):
        if not self.workspace:
            return False
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump({"facts": self.facts[:MAX_FACTS],
                           "prefs": self.prefs,
                           "summary": self.summary[:4000],
                           "updated": time.strftime("%Y-%m-%dT%H:%M:%S")},
                          fh, indent=2)
            return True
        except OSError:
            return False

    # ------------------------------------------------------------- facts
    def add_fact(self, text, source="user"):
        text = (text or "").strip()
        if not text:
            return None
        # de-duplicate (case-insensitive)
        low = text.lower()
        for fact in self.facts:
            if fact.get("text", "").lower() == low:
                return fact.get("id")
        fact_id = f"f{int(time.time() * 1000) % 10_000_000}"
        self.facts.append({"id": fact_id, "text": text,
                           "created": time.strftime("%Y-%m-%d"),
                           "source": source})
        if len(self.facts) > MAX_FACTS:
            self.facts = self.facts[-MAX_FACTS:]
        self.save()
        return fact_id

    def remove_fact(self, fact_id):
        before = len(self.facts)
        self.facts = [f for f in self.facts if f.get("id") != fact_id]
        changed = len(self.facts) != before
        if changed:
            self.save()
        return changed

    def set_pref(self, key, value):
        self.prefs[str(key)] = value
        self.save()

    def get_pref(self, key, default=None):
        return self.prefs.get(str(key), default)

    def set_summary(self, text):
        self.summary = (text or "").strip()
        self.save()

    def context_block(self, max_chars=MAX_RECALL_CHARS):
        """Alias of :meth:`recall_block` — engine integration name."""
        return self.recall_block(max_chars)

    # ------------------------------------------------------------ recall
    def recall_block(self, max_chars=MAX_RECALL_CHARS):
        """Render memory as a compact block for the system prompt."""
        if not self.facts and not self.summary and not self.prefs:
            return ""
        lines = ["## Workspace memory (DXN1 STUDIO)"]
        for fact in self.facts:
            lines.append(f"- {fact.get('text', '')}")
        for key, value in list(self.prefs.items())[:8]:
            lines.append(f"- preference: {key} = {value}")
        if self.summary:
            snippet = self.summary
            lines.append("### Continuing context")
            lines.append(snippet[: max_chars // 2])
        block = "\n".join(line for line in lines if line.strip())
        if len(block) > max_chars:
            block = block[:max_chars - 3].rstrip() + "..."
        return block


def recall_block(workspace, max_chars=MAX_RECALL_CHARS):
    """One-call helper: build the memory block (or "") for a workspace."""
    try:
        return MemoryBank(workspace).recall_block(max_chars)
    except Exception:
        return ""


# ------------------------------------------------------------- editor
class MemoryEditor(tk.Toplevel):
    """View and edit the current workspace's memory bank."""

    def __init__(self, parent, theme, workspace, on_log=None):
        super().__init__(parent)
        self.t = theme
        self.workspace = workspace or ""
        self.bank = MemoryBank(self.workspace)
        self.on_log = on_log or (lambda msg: None)
        self.title("Agent Memory — DXN1 STUDIO")
        self.configure(bg=self.t["bg"])
        self.geometry("640x540")
        self.minsize(460, 360)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build()
        self._refresh()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            # DS2 v2.61 — width accounting round three: fit what it
            # packed (the 640x540 default is the floor), then center
            from . import geom as _geom
            _geom.fit_to_content(self, 640, 540)
            self.update_idletasks()
            w = max(640, self.winfo_width())
            h = max(540, self.winfo_height())
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=46)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="✦  AGENT MEMORY", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        self.path_lbl = tk.Label(bar, text=self.bank.path, bg=t["header"],
                                 fg=t["text_muted"], font=(FONT_MONO, 7))
        self.path_lbl.pack(side=tk.LEFT, padx=8)
        tk.Label(bar, text="Remembered facts are injected into every "
                 "agent conversation in this workspace.", bg=t["header"],
                 fg=t["text_muted"], font=(FONT_UI, 8)).pack(
            side=tk.RIGHT, padx=12)

        # add row
        row = tk.Frame(self, bg=t["bg"])
        row.pack(fill=tk.X, padx=12, pady=(12, 0))
        self.entry = tk.Entry(row, bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"], relief=tk.FLAT,
                              font=(FONT_UI, 10), highlightthickness=1,
                              highlightbackground=t["border"],
                              highlightcolor=t.accent)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.entry.insert(0, "")
        self._placeholder()
        self.entry.bind("<FocusIn>", self._ph_clear)
        self.entry.bind("<FocusOut>", self._ph_set)
        self.entry.bind("<Return>", lambda e: self.add())
        btn = tk.Label(row, text="+  Remember", bg=t.accent, fg="#ffffff",
                       font=(FONT_UI, 9, "bold"), cursor="hand2",
                       padx=14, pady=7)
        btn.pack(side=tk.LEFT, padx=(8, 0))
        btn.bind("<Button-1>", lambda e: self.add())

        # facts list
        wrap = tk.Frame(self, bg=t["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(10, 0))
        self.canvas = tk.Canvas(wrap, bg=t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.canvas.yview,
                           style="TS2.Vertical.TScrollbar")
        self.list = tk.Frame(self.canvas, bg=t["bg"])
        self._win = self.canvas.create_window((0, 0), window=self.list,
                                              anchor="nw", width=600)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.list.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))

        # summary editor
        srow = tk.Frame(self, bg=t["bg"])
        srow.pack(fill=tk.X, padx=12, pady=(8, 10))
        tk.Label(srow, text="Rolling summary", bg=t["bg"],
                 fg=t["text_muted"], font=(FONT_UI, 8, "bold")).pack(
            anchor="w")
        self.summary = tk.Text(srow, height=4, bg=t["editor"], fg=t["text"],
                               insertbackground=t["text"], relief=tk.FLAT,
                               font=(FONT_MONO, 9), highlightthickness=1,
                               highlightbackground=t["border"],
                               highlightcolor=t.accent, wrap=tk.WORD)
        from .theme import make_scrollbar
        _sb = make_scrollbar(srow, t, tk.VERTICAL,
                             command=self.summary.yview)
        self.summary.configure(yscrollcommand=_sb.set)
        _sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary.pack(fill=tk.X, pady=(2, 0))
        self.summary.insert("1.0", self.bank.summary)
        save = tk.Label(srow, text="Save summary", bg=t["card"],
                        fg=t["text_secondary"], font=(FONT_UI, 8, "bold"),
                        cursor="hand2", padx=10, pady=4)
        save.pack(anchor="e", pady=(4, 0))
        save.bind("<Button-1>", self._save_summary)

        self.status = tk.Label(self, text="", bg=t["statusbar"],
                               fg=t["text_secondary"], font=(FONT_UI, 8),
                               anchor="w", padx=12, pady=5)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        # the door sign
        from . import hints
        self.hintbar = hints.hint_bar(
            self, t,
            pairs=(("Enter", "remember"),),
            notes=("facts ride along in every agent chat in this "
                   "workspace", "click ✕ on a fact to forget it"),
            before=self.status)   # keep the very bottom edge

    # ---------------------------------------------------------- helpers
    def _placeholder(self):
        if not self.entry.get():
            self.entry.insert(0, "e.g. 'this project uses pytest — always "
                                 "run tests after edits'")
            self.entry.config(fg=self.t["text_muted"])

    def _ph_clear(self, _e=None):
        if self.entry.get().startswith("e.g."):
            self.entry.delete(0, tk.END)
            self.entry.config(fg=self.t["text"])

    def _ph_set(self, _e=None):
        if not self.entry.get():
            self._placeholder()

    def _say(self, text):
        self.status.config(text=text)

    def _clear(self):
        for w in self.list.winfo_children():
            w.destroy()

    def _refresh(self):
        self._clear()
        t = self.t
        if not self.facts_shown():
            tk.Label(self.list,
                     text="Nothing remembered yet — add a fact above.\n\n"
                          "Try: project conventions, test commands, "
                          "naming rules, what to never touch.",
                     bg=t["bg"], fg=t["text_muted"], font=(FONT_UI, 9),
                     justify=tk.LEFT).pack(anchor="w", padx=6, pady=10)
            return
        for fact in list(self.bank.facts)[::-1]:
            row = tk.Frame(self.list, bg=t["card"], highlightthickness=1,
                           highlightbackground=t["card_border"])
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=fact.get("text", ""), bg=t["card"],
                     fg=t["text"], font=(FONT_UI, 9), anchor="w",
                     wraplength=480, justify=tk.LEFT).pack(
                side=tk.LEFT, padx=10, pady=6)
            tk.Label(row, text=fact.get("created", ""), bg=t["card"],
                     fg=t["text_muted"], font=(FONT_MONO, 7)).pack(
                side=tk.LEFT, padx=4)
            x = tk.Label(row, text="✕", bg=t["card"], fg="#f85149",
                         font=(FONT_UI, 10, "bold"), cursor="hand2", padx=10)
            x.pack(side=tk.RIGHT)
            x.bind("<Button-1>", lambda e, fid=fact.get("id"):
                   self.remove(fid))

    def facts_shown(self):
        return bool(self.bank.facts)

    # ---------------------------------------------------------- actions
    def add(self):
        self._ph_clear()
        text = self.entry.get().strip()
        if not text:
            self._say("Type what the agent should remember.")
            return
        self.bank.add_fact(text)
        self.entry.delete(0, tk.END)
        self._ph_set()
        self.on_log(f"memory: remembered '{text[:48]}'")
        self._say("Remembered ✓")
        self._refresh()

    def remove(self, fact_id):
        self.bank.remove_fact(fact_id)
        self._say("Forgotten.")
        self._refresh()

    def _save_summary(self, _e=None):
        text = self.summary.get("1.0", tk.END).strip()
        self.bank.set_summary(text)
        self._say("Summary saved ✓")


def open_memory_editor(parent, theme, workspace, on_log=None):
    """Convenience opener — mirrors the studio's one-call dialog style."""
    return MemoryEditor(parent, theme, workspace, on_log=on_log)


# DS2 alias — the palette and engine both open the editor by this name
open_memory = open_memory_editor
