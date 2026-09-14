"""DXN1 STUDIO — first-run mastery checklist (DS2 v1.7).

A small, dismissible "get good, fast" card that lives in the sidebar
until the new user has done the six things that make the studio click:
open a workspace, commit, run, ask the agents, try the palette, and
personalise the theme. Every step ticks itself automatically the moment
the user does it for real — no nagging, no modals, just quiet progress
that persists in the config and disappears when it has done its job.

Other modules tick steps with one defensive call::

    try:
        from .checklist import mark
        mark(app.config, "commit")
    except Exception:
        pass
"""

import tkinter as tk

from .theme import FONT_UI, FONT_MONO

STEPS = [
    ("open", "Open a workspace", "Project Hub → open any folder"),
    ("run", "Run your project", "Hit F5 — output lands in the terminal"),
    ("commit", "Make a git commit", "Source Control panel → message → Commit"),
    ("agent", "Ask DXN1 Agents something", "Free brain, no account needed"),
    ("palette", "Try the command palette", "Ctrl+K — every command, one place"),
    ("theme", "Personalise the studio", "Dark or light, six accent colours"),
]

CONFIG_KEY = "ds2_checklist"
DISMISS_KEY = "ds2_checklist_dismissed"


def _state(config):
    try:
        data = config.get(CONFIG_KEY) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_done(config, step_id):
    return bool(_state(config).get(step_id))


def all_done(config):
    return all(is_done(config, sid) for sid, _lbl, _hint in STEPS)


def mark(config, step_id):
    """Tick a step (idempotent). Returns True when newly completed."""
    if step_id not in {sid for sid, _l, _h in STEPS}:
        return False
    state = _state(config)
    if state.get(step_id):
        return False
    state[step_id] = True
    try:
        config.set(CONFIG_KEY, state)
    except Exception:
        pass
    return True


def progress(config):
    """(done_count, total) for status bars and badges."""
    state = _state(config)
    total = len(STEPS)
    done = sum(1 for sid, _l, _h in STEPS if state.get(sid))
    return done, total


def dismissed(config):
    try:
        return bool(config.get(DISMISS_KEY))
    except Exception:
        return False


class FirstRunChecklist(tk.Frame):
    """The sidebar card: six steps, live ticks, auto-hide when complete."""

    HEIGHT = 214

    def __init__(self, parent, theme, config, on_log=None,
                 on_navigate=None):
        super().__init__(parent, bg=theme["sidebar"])
        self.t = theme
        self.config = config
        self.on_log = on_log or (lambda msg: None)
        self.on_navigate = on_navigate or (lambda view: None)
        self.rows = {}
        self._build()
        self.refresh()

    # ------------------------------------------------------------- build
    def _build(self):
        t = self.t
        header = tk.Frame(self, bg=t["sidebar"])
        header.pack(fill=tk.X, padx=12, pady=(12, 2))
        tk.Label(header, text="GET GOOD, FAST", bg=t["sidebar"],
                 fg=t["text_secondary"], font=(FONT_UI, 9, "bold")
                 ).pack(side=tk.LEFT)
        self.prog = tk.Label(header, text="", bg=t["sidebar"],
                             fg=t["text_muted"], font=(FONT_MONO, 8))
        self.prog.pack(side=tk.LEFT, padx=6)
        x = tk.Label(header, text="✕", bg=t["sidebar"], fg=t["text_muted"],
                     font=(FONT_UI, 9), cursor="hand2")
        x.pack(side=tk.RIGHT)
        x.bind("<Button-1>", lambda e: self.dismiss())

        self.bar = tk.Canvas(self, height=4, bg=t["card"],
                             highlightthickness=0)
        self.bar.pack(fill=tk.X, padx=12, pady=(2, 4))

        for sid, label, hint in STEPS:
            row = tk.Frame(self, bg=t["sidebar"])
            row.pack(fill=tk.X, padx=12, pady=1)
            glyph = tk.Label(row, text="○", bg=t["sidebar"], fg=t["text_muted"],
                             font=(FONT_UI, 10), width=2)
            glyph.pack(side=tk.LEFT)
            text = tk.Label(row, text=label, bg=t["sidebar"], fg=t["text"],
                            font=(FONT_UI, 9), cursor="hand2", anchor="w")
            text.pack(side=tk.LEFT, fill=tk.X, expand=True)
            hint_lbl = tk.Label(row, text=hint, bg=t["sidebar"],
                                fg=t["text_muted"], font=(FONT_UI, 7),
                                anchor="e")
            hint_lbl.pack(side=tk.RIGHT, padx=2)
            for w in (text, hint_lbl):
                w.bind("<Enter>", lambda e, r=row: r.config(
                    bg=self.t["hover"]))
                w.bind("<Leave>", lambda e, r=row: r.config(
                    bg=self.t["sidebar"]))
            self.rows[sid] = (glyph, text, hint_lbl, row)

    # ----------------------------------------------------------- refresh
    def refresh(self):
        done, total = progress(self.config)
        state = _state(self.config)
        for sid, (glyph, text, hint_lbl, row) in self.rows.items():
            if state.get(sid):
                glyph.config(text="✓", fg=self.t["success"])
                text.config(fg=self.t["text_muted"])
                hint_lbl.config(text="done")
            else:
                glyph.config(text="○", fg=self.t["text_muted"])
                text.config(fg=self.t["text"])
        self.prog.config(text=f"{done}/{total}")
        width = self.bar.winfo_width() or 200
        self.bar.delete("all")
        if total:
            self.bar.create_rectangle(0, 0, max(6, int(width * done / total)),
                                      4, fill=self.t.accent, outline="")
        if done >= total:
            self.after(1600, self._celebrate)

    def _celebrate(self):
        try:
            for w in self.winfo_children():
                w.destroy()
            card = tk.Frame(self, bg=self.t["card"], highlightthickness=1,
                            highlightbackground=self.t["card_border"])
            card.pack(fill=tk.X, padx=12, pady=12)
            tk.Label(card, text="✓  Checklist complete — you know the "
                     "studio now. Build something great.",
                     bg=self.t["card"], fg=self.t["success"],
                     font=(FONT_UI, 9, "bold"), wraplength=200,
                     justify=tk.LEFT).pack(padx=10, pady=10)
            self.config.set(DISMISS_KEY, True)
        except Exception:
            pass

    def dismiss(self):
        try:
            self.config.set(DISMISS_KEY, True)
        except Exception:
            pass
        self.pack_forget()
        self.on_log("checklist dismissed")


def visible_for(config):
    """Should the card show at all? (not dismissed, not all done)."""
    return not dismissed(config) and not all_done(config)
