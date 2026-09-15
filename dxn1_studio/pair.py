"""DXN1 STUDIO — pair programming mode (DS2 v1.6).

Plan first, act second — the way big tasks should run. Describe a goal,
let the brain draft a numbered step plan, check the steps (edit or drop
what you disagree with), then hand the whole plan — or one step at a
time — to the DXN1 Agents engine through its normal ``route()`` entry,
so approvals, sandboxing and diffs all work exactly as usual.

Pair mode never touches files itself; it is a thinking layer above the
agent, which is why it is safe to use at any autonomy level.
"""

import re
import threading
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

PLAN_PROMPT = (
    "You are the planning half of a pair-programming session in DXN1 "
    "STUDIO. The user gives a goal plus optional context. Reply with a "
    "numbered plan of 3 to 7 concrete steps — each one line, each "
    "directly actionable in this workspace (files to touch, commands to "
    "run). No preamble, no conclusion, numbered lines only.")


def parse_plan(text):
    """Extract numbered steps from a model answer (very forgiving)."""
    steps = []
    for line in (text or "").splitlines():
        line = line.strip()
        m = re.match(r"^\d+[\.\)]\s*(.{4,})", line)
        if m:
            steps.append(m.group(1).strip())
    if not steps:
        # fall back to non-empty lines that look like actions
        steps = [ln.strip("-• ") for ln in text.splitlines()
                 if len(ln.strip()) > 8][:7]
    return steps[:8]


class PairSession(tk.Toplevel):
    """Plan → review → execute, one focused window."""

    def __init__(self, parent, theme, app, on_log=None):
        super().__init__(parent)
        self.t = theme
        self.app = app
        self.on_log = on_log or (lambda msg: None)
        self.steps = []
        self.title("Pair mode — plan & act")
        self.configure(bg=self.t["bg"])
        self.geometry("720x600")
        # DS2 v2.62 — width accounting round four: once the build
        # settles, open no narrower (or shorter) than what it
        # actually packed (the 720x600 default is the floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 720, 600))
        self.minsize(520, 420)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 720, 600
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    # -------------------------------------------------------------- ui
    def _build(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⚙  PAIR MODE", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        tk.Label(bar, text="plan → review → the agent acts",
                 bg=t["header"], fg=t["text_muted"],
                 font=(FONT_UI, 8)).pack(side=tk.LEFT, padx=8)
        self.status = tk.Label(bar, text="", bg=t["header"],
                               fg=t["text_muted"], font=(FONT_UI, 8))
        self.status.pack(side=tk.RIGHT, padx=12)

        # goal row
        goal = tk.Frame(self, bg=t["bg"])
        goal.pack(fill=tk.X, padx=12, pady=(12, 0))
        tk.Label(goal, text="Goal", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 8, "bold")).pack(anchor="w")
        self.goal = tk.Text(goal, height=3, bg=t["editor"], fg=t["text"],
                            insertbackground=t["text"], relief=tk.FLAT,
                            font=(FONT_MONO, 10), wrap=tk.WORD,
                            highlightthickness=1,
                            highlightbackground=t["border"],
                            highlightcolor=t.accent)
        self.goal.pack(fill=tk.X, pady=(2, 6))

        row = tk.Frame(self, bg=t["bg"])
        row.pack(fill=tk.X, padx=12)
        self.draft_btn = tk.Label(row, text="✦ Draft plan", bg=t.accent,
                                  fg="#ffffff", font=(FONT_UI, 9, "bold"),
                                  cursor="hand2", padx=14, pady=7)
        self.draft_btn.pack(side=tk.LEFT)
        self.draft_btn.bind("<Button-1>", lambda e: self.draft_plan())
        send_all = tk.Label(row, text="▷ Send plan to agent", bg=t["card"],
                            fg=t["text"], font=(FONT_UI, 9, "bold"),
                            cursor="hand2", padx=12, pady=7)
        send_all.pack(side=tk.LEFT, padx=(8, 0))
        send_all.bind("<Button-1>", lambda e: self.send_whole_plan())

        # plan editor
        tk.Label(self, text="Plan (edit freely — one step per line)",
                 bg=self.t["bg"], fg=self.t["text_muted"],
                 font=(FONT_UI, 8, "bold")).pack(anchor="w", padx=12,
                                                 pady=(10, 2))
        self.plan = tk.Text(self, height=9, bg=self.t["editor"],
                            fg=self.t["text"], insertbackground=t["text"],
                            relief=tk.FLAT, font=(FONT_MONO, 10),
                            wrap=tk.WORD, highlightthickness=1,
                            highlightbackground=t["border"],
                            highlightcolor=t.accent)
        from .theme import make_scrollbar
        _psb = make_scrollbar(self, self.t, "vertical",
                              command=self.plan.yview)
        self.plan.configure(yscrollcommand=_psb.set)
        _psb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 12), pady=(0, 6))
        self.plan.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 6))

        footer = tk.Frame(self, bg=self.t["statusbar"])
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(footer, text="Steps are executed by DXN1 Agents with all "
                 "its approvals and diff previews.",
                 bg=t["statusbar"], fg=t["text_muted"],
                 font=(FONT_UI, 8)).pack(side=tk.LEFT, padx=12, pady=5)
        one = tk.Label(footer, text="▷ Run selected step",
                       bg=t["card"], fg=t["text"], font=(FONT_UI, 9,
                                                         "bold"),
                       cursor="hand2", padx=12, pady=5)
        one.pack(side=tk.RIGHT, padx=8, pady=4)
        one.bind("<Button-1>", lambda e: self.run_selected_step())

        # the door sign — keeps the very bottom edge below the footer
        from . import hints
        self.hintbar = hints.hint_bar(
            self, t,
            notes=("draft a plan, edit the lines, then send it",
                   "run one step: click ▷ with the cursor on its line"),
            before=footer)

    def _set_status(self, text):
        try:
            self.status.config(text=text)
        except tk.TclError:
            pass

    # -------------------------------------------------------- plan draft
    def draft_plan(self):
        goal_text = self.goal.get("1.0", "end-1c").strip()
        if not goal_text:
            self._set_status("describe the goal first")
            return
        try:
            from . import llm
            backend = llm.build_backend(self.app.config)
        except Exception:
            backend = None
        if backend is None:
            self._set_status("connect a brain first (Agents settings)")
            return
        self.draft_btn.config(text="… planning", bg=self.t["card"],
                              fg=self.t["text_muted"])
        self._set_status("drafting plan…")
        context = ""
        try:
            context = getattr(self.app, "project_dir", "") or ""
        except Exception:
            pass

        def worker():
            answer = ""
            error = None
            try:
                answer = backend.chat(
                    [{"role": "user", "content": PLAN_PROMPT +
                      f"\n\nWorkspace: {context}\n\nGoal: {goal_text}"}],
                    max_tokens=500, temperature=0.3)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)

            def deliver():
                try:
                    self.draft_btn.config(text="✦ Draft plan",
                                          bg=self.t.accent, fg="#ffffff")
                except tk.TclError:
                    return
                if error:
                    self._set_status(f"plan failed: {error[:90]}")
                    return
                steps = parse_plan(answer)
                if not steps:
                    self._set_status("the brain returned no steps — try "
                                     "rephrasing")
                    return
                self.plan.delete("1.0", "end")
                for i, step in enumerate(steps, 1):
                    self.plan.insert(tk.END, f"{i}. {step}\n")
                self._set_status(f"plan drafted — {len(steps)} steps, "
                                 f"edit then send")
                self.on_log(f"pair mode: plan drafted ({len(steps)} steps)")

            try:
                self.after(0, deliver)
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------- send
    def _route(self, text):
        panel = getattr(self.app, "agent_panel", None)
        if panel is None or not hasattr(panel, "route"):
            self._set_status("DXN1 Agents panel is not open")
            return
        try:
            panel.route(text)
            self._set_status("handed to the agent ✓")
            self.on_log("pair mode: plan handed to the agent")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"agent refused: {exc}")

    def send_whole_plan(self):
        plan_text = self.plan.get("1.0", "end-1c").strip()
        goal_text = self.goal.get("1.0", "end-1c").strip()
        if not plan_text:
            self._set_status("nothing to send — draft or write a plan")
            return
        message = (f"Work through this plan step by step. "
                   f"Goal: {goal_text}\n\n{plan_text}\n\n"
                   f"Start with step 1 and continue until done.")
        self._route(message)

    def run_selected_step(self):
        try:
            sel = self.plan.tag_ranges("sel")
            if sel:
                line_text = self.plan.get("sel.first linestart",
                                          "sel.last lineend")
            else:
                insert = self.plan.index(tk.INSERT)
                line_text = self.plan.get(f"{insert} linestart",
                                          f"{insert} lineend")
        except tk.TclError:
            line_text = ""
        step = re.sub(r"^\d+[\.\)]\s*", "", (line_text or "").strip())
        if len(step) < 4:
            self._set_status("put the cursor on a step line first")
            return
        self._route(f"Execute exactly this step, then report: {step}")


def open_pair_session(app):
    """Open pair mode (palette entry point). Never raises."""
    try:
        return PairSession(app.root, app.theme, app,
                           on_log=lambda m: app.toast(m))
    except Exception as exc:  # pragma: no cover
        try:
            app.toast(f"pair mode failed: {exc}", "error")
        except Exception:
            pass
        return None


# DS2 alias — app.py's palette block opens pair mode by this name
open_pair = open_pair_session
