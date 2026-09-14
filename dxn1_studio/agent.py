"""DXN1 STUDIO — the DXN1 Agents assistant.

DXN1 Agents is the studio's built-in copilot. It can create files,
scaffold apps, edit code surgically, run commands and install packages —
but how much it may do is always under your control:

* **Ask mode** (default) — every file edit and every command appears as
  a proposal card you Accept or Decline.
* **Full access** — turn both prompts off in the agent settings and the
  agent stops asking, applying edits and running commands directly.
* **Sandbox** — whatever the mode, the agent only ever touches paths
  inside the open workspace. Never your home folder, never your PC.

Brains
------
local     Built-in offline skills (rule engine — no network, no key).
byok      Bring your own key: OpenRouter / Groq / Gemini / Mistral /
          OpenAI / Ollama / any OpenAI-compatible endpoint.
github    GitHub Models — free tier, tracked via your GitHub login.
kilo      Kilo gateway — free-model routing through one tiny direct
          HTTP client (never a bundled Kilo instance, so RAM stays low).
"""

import os
import queue
import re
import threading
import tkinter as tk
import webbrowser

from . import APP_NAME
from . import llm
from .sandbox import (WorkspaceSandbox, SandboxError, AgentEngine,
                      head_preview, PROMPT_STYLES, build_system_prompt)
from .theme import FONT_UI, FONT_MONO

AGENTS_NAME = "DXN1 Agents"
AGENTS_TAGLINE = "Your studio copilot — with permission."

FILE_TEMPLATES = {
    ".py":    '"""{stem} — created with DXN1 Agents."""\n\n\ndef main():\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
    ".html":  '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <title>{stem}</title>\n</head>\n<body>\n  <h1>{stem}</h1>\n</body>\n</html>\n',
    ".css":   "/* {stem} */\nbody {{\n  margin: 0;\n  font-family: system-ui, sans-serif;\n}}\n",
    ".js":    "// {stem}\n\n",
    ".json":  '{\n  "name": "{stem}"\n}\n',
    ".md":    "# {stem}\n\n",
    ".txt":   "",
}

# messages the rule engine always answers instantly, even with an LLM brain
LOCAL_EXACT = {"help", "?", "what can you do", "clear", "clear terminal",
               "hub", "project hub", "packages", "manage packages",
               "explain", "explain this", "what is this file", "analyze"}


class Proposal:
    """One actionable suggestion the agent puts on the table."""

    _next_id = 1

    def __init__(self, kind, title, detail, action, preview=None):
        self.kind = kind            # "edit" | "command"
        self.title = title
        self.detail = detail
        self.action = action        # callable, executed on accept
        self.preview = preview      # optional code/command preview text
        self.id = Proposal._next_id
        Proposal._next_id += 1


class DXN1AgentPanel(tk.Frame):
    """Right-docked assistant panel. One instance per main window."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=app.theme["sidebar"])
        self.app = app
        self.t = app.theme
        self._imgref = None
        self._canvas_win = None

        self.sandbox = None          # WorkspaceSandbox, set per workspace
        self.backend = None          # llm backend or None (local skills)
        self.engine = None           # AgentEngine when a brain is attached
        self._eq = queue.Queue()     # engine -> UI mailbox
        self._busy = False
        self._think_job = None
        self._think_dots = 0

        self._build_header()
        self._build_message_area()
        self._build_input()
        self.refresh_backend()

        self.agent_say(
            f"{AGENTS_NAME} online. I can create files, scaffold a Flask "
            f"app, edit code, run your project or install packages — "
            f"always inside this workspace, always with your permission. "
            f"Type “help” to see everything.")
        self.maybe_show_setup_hint()

    # ------------------------------------------------------------------ ui
    def _build_header(self):
        head = tk.Frame(self, bg=self.t["header"])
        head.pack(fill=tk.X)

        tk.Label(head, text="◆", bg=self.t["header"], fg=self.t.accent,
                 font=(FONT_UI, 12, "bold")).pack(side=tk.LEFT, padx=(14, 6), pady=10)
        tk.Label(head, text="DXN1 AGENTS", bg=self.t["header"],
                 fg=self.t["text"], font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)

        self.mode_chip = tk.Label(head, text="", bg=self.t["header"],
                                  fg=self.t["text_muted"], font=(FONT_UI, 8, "bold"),
                                  padx=8, pady=2)
        self.mode_chip.pack(side=tk.LEFT, padx=6)
        self.mode_chip.bind("<Button-1>", lambda e: self.open_settings())

        self.brain_chip = tk.Label(head, text="", bg=self.t["header"],
                                   fg=self.t["text_muted"],
                                   font=(FONT_UI, 8), padx=8, pady=2,
                                   cursor="hand2")
        self.brain_chip.pack(side=tk.LEFT)
        self.brain_chip.bind("<Button-1>", lambda e: self.open_settings())

        gear = tk.Label(head, text="⚙", bg=self.t["header"], fg=self.t["text_muted"],
                        font=(FONT_UI, 11), cursor="hand2")
        gear.pack(side=tk.RIGHT, padx=12)
        gear.bind("<Button-1>", lambda e: self.open_settings())

        self.think = tk.Label(self, text="", bg=self.t["header"],
                              fg=self.t.accent, font=(FONT_UI, 8, "italic"),
                              anchor="w")
        self.think.pack(fill=tk.X, padx=14)

        self.refresh_mode()
        self.refresh_header()

    def refresh_header(self):
        if self.engine is not None and self.backend is not None:
            label = self.backend.display
            if len(label) > 26:
                label = label[:24].rstrip() + "…"
            self.brain_chip.config(text=label, fg=self.t.accent)
        else:
            self.brain_chip.config(text="local skills", fg=self.t["text_muted"])

    def refresh_mode(self):
        cfg = self.app.config
        if not cfg.get("agents_ask_edits") and not cfg.get("agents_ask_commands"):
            self.mode_chip.config(text="FULL ACCESS", bg=self.t["success"],
                                  fg="#ffffff")
        else:
            self.mode_chip.config(text="ASK MODE", bg=self.t["card"],
                                  fg=self.t["text_secondary"])

    def _build_message_area(self):
        wrap = tk.Frame(self, bg=self.t["sidebar"])
        wrap.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(wrap, bg=self.t["sidebar"], highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.stream = tk.Frame(self.canvas, bg=self.t["sidebar"])
        self._canvas_win = self.canvas.create_window(
            (0, 0), window=self.stream, anchor="nw", width=270)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.stream.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._canvas_win, width=e.width))
        wrap.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._wheel))
        wrap.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _build_input(self):
        # one-tap quick actions — crafted prompts for the active file
        quick = tk.Frame(self, bg=self.t["sidebar"])
        quick.pack(fill=tk.X, padx=10, pady=(0, 6))
        for label, prompt in (
                ("✦ Explain", "explain"),
                ("✦ Tests", "Write tests for the file currently open "
                 "in the editor. Read it first, then create a pytest-style "
                 "test file tests/test_<name>.py with plain asserts."),
                ("✦ Bugs", "Review the file currently open in the "
                 "editor for bugs and edge cases. List your findings "
                 "concisely — propose fixes, don't apply them without "
                 "asking."),
                ("✦ Docs", "Add a short docstring to every def and "
                 "class that is missing one in the file open in the "
                 "editor. Change nothing else.")):
            chip = tk.Label(quick, text=label, bg=self.t["card"],
                            fg=self.t["text_secondary"], cursor="hand2",
                            font=(FONT_UI, 8, "bold"), padx=8, pady=3,
                            highlightthickness=1,
                            highlightbackground=self.t["card_border"])
            chip.pack(side=tk.LEFT, padx=(0, 4))
            chip.bind("<Button-1>", lambda e, p=prompt: self.route(p))
            chip.bind("<Enter>", lambda e, c=chip: c.config(
                fg=self.t.accent))
            chip.bind("<Leave>", lambda e, c=chip: c.config(
                fg=self.t["text_secondary"]))

        row = tk.Frame(self, bg=self.t["sidebar"])
        row.pack(fill=tk.X, padx=10, pady=(0, 2))

        self.entry = tk.Entry(row, bg=self.t["editor"], fg=self.t["text"],
                              insertbackground=self.t["text"], relief=tk.FLAT,
                              font=(FONT_MONO, 10), highlightthickness=1,
                              highlightbackground=self.t["border"],
                              highlightcolor=self.t.accent)
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=7)
        self.entry.bind("<Return>", lambda e: self.send())
        self.entry.focus_set()

        send = tk.Label(row, text="↩", bg=self.t.accent, fg="#ffffff",
                        font=(FONT_UI, 11, "bold"), cursor="hand2",
                        padx=11, pady=6)
        send.pack(side=tk.LEFT, padx=(6, 0))
        send.bind("<Button-1>", lambda e: self.send())

        foot = tk.Frame(self, bg=self.t["sidebar"])
        foot.pack(fill=tk.X, padx=12, pady=(0, 6))
        tk.Label(foot, text="try: fix the bug in app.py · new flask app · run",
                 bg=self.t["sidebar"], fg=self.t["text_muted"],
                 font=(FONT_UI, 8), anchor="w").pack(side=tk.LEFT)
        self.stop_lbl = tk.Label(foot, text="■ stop", bg=self.t["sidebar"],
                                 fg=self.t["text_muted"], font=(FONT_UI, 8, "bold"),
                                 cursor="hand2")
        self.stop_lbl.pack(side=tk.RIGHT)
        self.stop_lbl.bind("<Button-1>", lambda e: self.stop_engine())
        self.stats_lbl = tk.Label(self, text="", bg=self.t["sidebar"],
                                  fg=self.t["text_muted"], font=(FONT_UI, 8),
                                  anchor="w")
        self.stats_lbl.pack(fill=tk.X, padx=12, pady=(0, 4))

    # ------------------------------------------------------------ messages
    def _new_card(self, accent_edge=False):
        card = tk.Frame(self.stream, bg=self.t["card"], highlightthickness=1,
                        highlightbackground=self.t["card_border"])
        if accent_edge:
            tk.Frame(card, bg=self.t.accent, width=3).pack(
                side=tk.LEFT, fill=tk.Y)
        card.pack(fill=tk.X, pady=4, padx=8, ipady=2)
        return card

    def agent_say(self, text):
        card = self._new_card(accent_edge=True)
        tk.Label(card, text=AGENTS_NAME, bg=self.t["card"], fg=self.t.accent,
                 font=(FONT_UI, 8, "bold"), anchor="w").pack(
            anchor="w", padx=10, pady=(6, 0))
        tk.Label(card, text=text, bg=self.t["card"], fg=self.t["text"],
                 font=(FONT_UI, 9), wraplength=240, justify=tk.LEFT,
                 anchor="w").pack(anchor="w", padx=10, pady=(2, 8))
        self._scroll_down()

    def system_note(self, text):
        card = self._new_card()
        tk.Label(card, text=text, bg=self.t["card"], fg=self.t["text_muted"],
                 font=(FONT_UI, 8, "italic"), wraplength=240, justify=tk.LEFT,
                 anchor="w").pack(anchor="w", padx=10, pady=6)
        self._scroll_down()

    def action_card(self, text, btn_label, cmd):
        """A note with one action button (used by the Connect flow)."""
        card = self._new_card(accent_edge=True)
        tk.Label(card, text=text, bg=self.t["card"], fg=self.t["text"],
                 font=(FONT_UI, 9), wraplength=240, justify=tk.LEFT,
                 anchor="w").pack(anchor="w", padx=10, pady=(8, 4))
        btn = tk.Label(card, text=btn_label, bg=self.t.accent, fg="#ffffff",
                       font=(FONT_UI, 9, "bold"), cursor="hand2", padx=12,
                       pady=5)
        btn.pack(anchor="w", padx=10, pady=(0, 8))
        btn.bind("<Button-1>", lambda e: cmd())
        self._scroll_down()

    def user_say(self, text):
        card = self._new_card()
        tk.Label(card, text=f"You  ·  {text}", bg=self.t["card"],
                 fg=self.t["text_secondary"], font=(FONT_MONO, 9),
                 wraplength=240, justify=tk.LEFT,
                 anchor="w").pack(anchor="w", padx=10, pady=7)
        self._scroll_down()

    def _scroll_down(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    # ---------------------------------------------------------- thinking ui
    def _set_thinking(self, on):
        if self._think_job is not None:
            self.after_cancel(self._think_job)
            self._think_job = None
        if on:
            self._think_dots = 0
            self._tick_think()
        else:
            self.think.config(text="")

    def _tick_think(self):
        self._think_dots = (self._think_dots + 1) % 4
        self.think.config(text="thinking" + "·" * self._think_dots)
        self._think_job = self.after(420, self._tick_think)

    # ------------------------------------------------------ proposal cards
    def _propose(self, proposal):
        """Render a proposal card — or auto-approve in full-access mode."""
        if proposal.kind == "edit" and \
                not self.app.config.get("agents_ask_edits"):
            proposal.action()
            self.agent_say(f"{proposal.title} — done automatically "
                           f"(full access mode).")
            return
        if proposal.kind == "command" and \
                not self.app.config.get("agents_ask_commands"):
            self.agent_say(f"Running: {proposal.title} (full access mode).")
            proposal.action()
            return

        card = self._new_card(accent_edge=True)
        head = tk.Frame(card, bg=self.t["card"])
        head.pack(fill=tk.X, padx=10, pady=(6, 0))
        kind_tag = "EDIT" if proposal.kind == "edit" else "COMMAND"
        tk.Label(head, text=kind_tag, bg=self.t["card"], fg=self.t.accent,
                 font=(FONT_UI, 8, "bold")).pack(side=tk.LEFT)
        tk.Label(head, text=f"  {proposal.title}", bg=self.t["card"],
                 fg=self.t["text"], font=(FONT_UI, 9, "bold"), anchor="w"
                 ).pack(side=tk.LEFT)
        if proposal.detail:
            tk.Label(card, text=proposal.detail, bg=self.t["card"],
                     fg=self.t["text_secondary"], font=(FONT_UI, 8),
                     wraplength=240, justify=tk.LEFT, anchor="w"
                     ).pack(anchor="w", padx=10, pady=(2, 0))
        if proposal.preview:
            tk.Label(card, text=proposal.preview, bg=self.t["terminal"],
                     fg=self.t["text"], font=(FONT_MONO, 8),
                     wraplength=250, justify=tk.LEFT, anchor="w"
                     ).pack(anchor="w", padx=10, pady=(4, 0), ipadx=6, ipady=4)

        btns = tk.Frame(card, bg=self.t["card"])
        btns.pack(fill=tk.X, padx=10, pady=(8, 8))

        def decide(approved):
            for child in btns.winfo_children():
                child.destroy()
            if approved:
                tk.Label(btns, text="Accepted ✓", bg=self.t["card"],
                         fg=self.t["success"], font=(FONT_UI, 9, "bold")
                         ).pack(side=tk.LEFT)
                proposal.action()
            else:
                tk.Label(btns, text="Declined", bg=self.t["card"],
                         fg=self.t["text_muted"], font=(FONT_UI, 9)
                         ).pack(side=tk.LEFT)
                self.agent_say("No problem — declined. I won't touch it.")

        accept = tk.Label(btns, text="Accept", bg=self.t.accent, fg="#ffffff",
                          font=(FONT_UI, 9, "bold"), cursor="hand2",
                          padx=12, pady=4)
        accept.pack(side=tk.LEFT)
        accept.bind("<Button-1>", lambda e: decide(True))
        decline = tk.Label(btns, text="Decline", bg=self.t["card"],
                           fg=self.t["text_secondary"], font=(FONT_UI, 9),
                           cursor="hand2", padx=10, pady=4)
        decline.pack(side=tk.LEFT, padx=6)
        decline.bind("<Button-1>", lambda e: decide(False))
        self._scroll_down()

    def _approve_card(self, kind, title, detail, preview, danger,
                      holder, event):
        """Card for engine approvals — flips the Event when decided."""
        card = self._new_card(accent_edge=True)
        head = tk.Frame(card, bg=self.t["card"])
        head.pack(fill=tk.X, padx=10, pady=(6, 0))
        tk.Label(head, text="EDIT" if kind == "edit" else "COMMAND",
                 bg=self.t["card"], fg=self.t.accent,
                 font=(FONT_UI, 8, "bold")).pack(side=tk.LEFT)
        if danger:
            tk.Label(head, text=" ⚠ NEEDS A HUMAN", bg=self.t["card"],
                     fg="#f85149", font=(FONT_UI, 8, "bold")).pack(side=tk.LEFT)
        tk.Label(head, text=f"  {title}"[:60], bg=self.t["card"],
                 fg=self.t["text"], font=(FONT_UI, 9, "bold"), anchor="w"
                 ).pack(side=tk.LEFT)
        if detail:
            tk.Label(card, text=detail, bg=self.t["card"],
                     fg=self.t["text_secondary"], font=(FONT_UI, 8),
                     wraplength=240, justify=tk.LEFT, anchor="w"
                     ).pack(anchor="w", padx=10, pady=(2, 0))
        if preview:
            tk.Label(card, text=preview, bg=self.t["terminal"],
                     fg=self.t["text"], font=(FONT_MONO, 8),
                     wraplength=250, justify=tk.LEFT, anchor="w"
                     ).pack(anchor="w", padx=10, pady=(4, 0), ipadx=6, ipady=4)

        btns = tk.Frame(card, bg=self.t["card"])
        btns.pack(fill=tk.X, padx=10, pady=(8, 8))

        def decide(approved):
            holder[0] = bool(approved)
            for child in btns.winfo_children():
                child.destroy()
            tk.Label(btns, text="Accepted ✓" if approved else "Declined",
                     bg=self.t["card"], fg=self.t["success"] if approved
                     else self.t["text_muted"],
                     font=(FONT_UI, 9, "bold")).pack(side=tk.LEFT)
            event.set()

        accept = tk.Label(btns, text="Accept", bg=self.t.accent, fg="#ffffff",
                          font=(FONT_UI, 9, "bold"), cursor="hand2",
                          padx=12, pady=4)
        accept.pack(side=tk.LEFT)
        accept.bind("<Button-1>", lambda e: decide(True))
        decline = tk.Label(btns, text="Decline", bg=self.t["card"],
                           fg=self.t["text_secondary"], font=(FONT_UI, 9),
                           cursor="hand2", padx=10, pady=4)
        decline.pack(side=tk.LEFT, padx=6)
        decline.bind("<Button-1>", lambda e: decide(False))
        self._scroll_down()

    # ---------------------------------------------------------- engine glue
    def refresh_backend(self):
        """(Re)build the brain from current settings. Local ⇒ rules only."""
        self.backend = llm.build_backend(self.app.config)
        if self.backend is not None and self.sandbox is not None:
            self.engine = AgentEngine(
                self.backend, self.sandbox, self.app.config, name=AGENTS_NAME,
                emit=lambda text: self._eq.put(("say", text)),
                approve=self._engine_approve,
                execute_command=self.app.agent_execute_command,
                on_written=self.app.agent_on_written)
        else:
            self.engine = None
        self.refresh_header()

    def set_workspace(self, path):
        """Bind the agent to a new workspace jail + fresh conversation."""
        try:
            self.sandbox = WorkspaceSandbox(path)
        except SandboxError:
            self.sandbox = None
            self.engine = None
            self.refresh_header()
            return
        self.refresh_backend()

    # --------------------------------------------------------- connect flow
    def maybe_show_setup_hint(self):
        """When the wizard picked a brain that still needs a key/token,
        surface an in-app Connect card once."""
        pending = (self.app.config.get("agents_setup_pending") or "").strip()
        if not pending or not self.app.config.get("agents_enabled"):
            return
        label = {"kilo": "Kilo gateway (free — Google login)",
                 "byok": "your own API key (BYOK)"}.get(pending, pending)
        self.action_card(
            f"One step left: this studio's agent brain is set to {label}. "
            f"Connect inside the app — takes about a minute.",
            "Connect now", self.open_connect)

    def open_connect(self):
        ConnectDialog(self.app)

    def update_stats(self):
        parts = []
        if self.engine is not None:
            if self.engine.steps_used:
                parts.append(f"steps {self.engine.steps_used}")
            if self.engine.tokens_used:
                parts.append(f"tokens {self.engine.tokens_used:,}")
        elif self.backend is not None and getattr(self.backend,
                                                  "total_tokens", 0):
            parts.append(f"tokens {self.backend.total_tokens:,}")
        self.stats_lbl.config(text="  ·  ".join(parts))

    def _engine_approve(self, kind, title, detail, preview, danger=False):
        """Runs on the engine thread — marshal to the UI and wait."""
        cfg = self.app.config
        ask = cfg.get("agents_ask_edits") if kind == "edit" \
            else cfg.get("agents_ask_commands")
        if not danger and not ask:
            self._eq.put(("auto", f"{title} — done automatically "
                                  f"(full access)."))
            return True
        holder = [None]
        ev = threading.Event()
        self._eq.put(("approve", (kind, title, detail, preview, danger),
                      holder, ev))
        ev.wait(timeout=1800)          # 30 min, then treat as declined
        return bool(holder[0])

    def _engine_thread(self, text):
        try:
            self.engine.run(text)
        except Exception as exc:  # noqa: BLE001 — report, never crash UI
            self._eq.put(("say", f"⚠ That hit a snag: {exc}"))
        finally:
            self._eq.put(("done", None))

    def _poll_engine(self):
        try:
            while True:
                kind, payload = self._eq.get_nowait()
                if kind == "say":
                    self.agent_say(payload)
                elif kind == "auto":
                    self.system_note(payload)
                elif kind == "approve":
                    spec, holder, ev = payload
                    self._approve_card(spec[0], spec[1], spec[2], spec[3],
                                       spec[4], holder, ev)
                elif kind == "done":
                    self._busy = False
                    self._set_thinking(False)
                    self.entry.config(state="normal")
                    self.update_stats()
        except queue.Empty:
            pass
        self.after(120, self._poll_engine)

    def stop_engine(self):
        if self.engine is not None and self.engine.busy:
            self.engine.stop()
            self.system_note("Stopping after the current step…")

    # ------------------------------------------------------------- driving
    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.route(text)

    def route(self, text):
        """One entry point for chat: local quickies, else the brain."""
        if self._busy:
            self.system_note("Still working on the previous task — "
                             "press ■ stop to interrupt it first.")
            return
        low = text.lower().strip()
        self.user_say(text)
        if low in LOCAL_EXACT or re.fullmatch(r"dxn1[\s_-]*studio", low):
            try:
                self.handle(low if low in LOCAL_EXACT else "dxn1 studio")
            except Exception as exc:  # never kill the IDE from the chat box
                self.agent_say(f"That hit a snag: {exc}")
            return
        if self.engine is not None:
            self._busy = True
            self._set_thinking(True)
            self.entry.config(state="disabled")
            threading.Thread(target=self._engine_thread, args=(text,),
                             daemon=True).start()
            return
        try:
            self.handle(text)
        except Exception as exc:
            self.agent_say(f"That hit a snag: {exc}")

    def open_settings(self):
        AgentSettingsDialog(self.app)

    # ------------------------------------------------------------------ io
    def base_dir(self):
        if self.sandbox is not None:
            return self.sandbox.root
        return self.app.project_dir or os.path.expanduser("~")

    def _safe_join(self, base, rel):
        rel = rel.strip().lstrip("/\\").replace("\\", "/")
        parts = [p for p in rel.split("/") if p not in ("", ".", "..")]
        if not parts:
            raise ValueError("that filename doesn't look safe")
        return os.path.join(base, *parts)

    def _write_files(self, files):
        """files: list of (abs_path, content). Writes + refreshes UI."""
        for path, content in files:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            self.app.agent_on_written(path)
        names = ", ".join(os.path.basename(p) for p, _ in files)
        self.app.terminal.log(f"Agents wrote: {names}")

    # -------------------------------------------------------------- intents
    def handle(self, text):
        low = text.lower().strip()

        if low in ("help", "?", "what can you do"):
            brain = "a real model" if self.engine is not None else "local skills"
            self.agent_say(
                f"My brain right now: {brain}.\n\n"
                "Instant skills (offline):\n"
                "• create file <name> — new file with a starter template\n"
                "• new flask app — scaffold a full web app (3 files)\n"
                "• run — execute the current file / project (F5)\n"
                "• install <package> — pip install, shown live\n"
                "• open <file> — open a workspace file in the editor\n"
                "• explain — stats about the file in the editor\n"
                "• shell <command> — propose any terminal command\n\n"
                "Anything else you type goes to my model brain (if one is "
                "attached) — it can read files, write code and run commands "
                "inside this workspace, sandboxed.")
            return

        m = re.match(r"^(?:create|new)\s+file\s+(.+)$", low)
        if m:
            self._intent_create_file(m.group(1))
            return

        if re.match(r"^new\s+(flask\s+)?(web\s?app|webapp)$", low) or \
                low in ("flask app", "new flask", "scaffold flask"):
            self._intent_flask()
            return

        if low in ("run", "run app", "run project", "run file", "f5"):
            self._intent_run()
            return

        m = re.match(r"^install\s+(.+)$", low)
        if m:
            self._intent_install(m.group(1))
            return

        m = re.match(r"^open\s+(.+)$", low)
        if m:
            self._intent_open(m.group(1))
            return

        if low in ("explain", "explain this", "what is this file", "analyze"):
            self._intent_explain()
            return

        if low in ("clear", "clear terminal"):
            self.app.terminal.clear()
            self.agent_say("Terminal cleared.")
            return

        if low == "dxn1 studio":
            self.agent_say("Rebooting the studio — enjoy the splash.")
            self.app.relaunch_with_splash()
            return

        if low in ("hub", "project hub"):
            self.app.open_hub()
            return

        if low in ("packages", "manage packages"):
            self.app.open_packages()
            return

        m = re.match(r"^(?:shell|!)\s+(.+)$", low)
        if m:
            self._propose(Proposal(
                "command", m.group(1),
                "A raw terminal command, executed in your workspace.",
                lambda cmd=m.group(1): self.app.run_command(cmd),
                preview=f"$ {m.group(1)}"))
            return

        if self.engine is not None:
            # brain is attached — let it take this one
            self.user_say(text)
            self._busy = True
            self._set_thinking(True)
            self.entry.config(state="disabled")
            threading.Thread(target=self._engine_thread, args=(text,),
                             daemon=True).start()
            return

        self.agent_say("I didn't catch that one yet — try “help” for the "
                       "full list of things I know how to do, or attach a "
                       "model brain in Settings → DXN1 Agents.")

    # -------------------------------------------------------------- actions
    def _intent_create_file(self, raw):
        path = self._safe_join(self.base_dir(), raw)
        ext = os.path.splitext(path)[1].lower()
        stem = os.path.basename(path)
        content = FILE_TEMPLATES.get(ext, "")
        if os.path.exists(path):
            self.agent_say(f"{stem} already exists — I won't overwrite it. "
                           f"Pick another name and I'll create that instead.")
            return
        preview = content.strip()[:160] + ("…" if len(content.strip()) > 160 else "")
        self._propose(Proposal(
            "edit", f"Create {os.path.relpath(path, self.base_dir())}",
            "A new file in your workspace with a small starter template.",
            lambda: self._write_files([(path, content)]),
            preview=preview or "(empty file)"))

    def _intent_flask(self):
        base = self.base_dir()
        files = [
            (os.path.join(base, "app.py"),
             '"""Flask app — scaffolded by DXN1 Agents."""\n'
             "from flask import Flask, render_template\n\n"
             "app = Flask(__name__)\n\n\n"
             '@app.route("/")\n'
             'def index():\n    return render_template("index.html")\n\n\n'
             'if __name__ == "__main__":\n    app.run(debug=True)\n'),
            (os.path.join(base, "templates", "index.html"),
             '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
             '  <meta charset="utf-8">\n  <title>Served by Flask</title>\n'
             "</head>\n<body style=\"font-family:system-ui;display:grid;"
             "place-items:center;min-height:100vh;background:#0d1117;"
             'color:#e6edf3">\n  <h1>It runs.</h1>\n</body>\n</html>\n'),
            (os.path.join(base, "requirements.txt"), "flask>=3.0\n"),
        ]
        new = [(p, c) for p, c in files if not os.path.exists(p)]
        if not new:
            self.agent_say("A Flask app is already here (app.py exists). "
                           "Press Run or F5 to start it.")
            return
        self._propose(Proposal(
            "edit", f"Scaffold Flask app ({len(new)} files)",
            "app.py + template + requirements.txt. If Flask isn't installed "
            "yet, say “install flask” after accepting.",
            lambda: self._write_files(new)))

    def _intent_run(self):
        app = self.app
        target = None
        if app.editor.file_path and app.editor.file_path.endswith(".py"):
            target = app.editor.file_path
        elif app.project_dir:
            for cand in ("app.py", "main.py"):
                p = os.path.join(app.project_dir, cand)
                if os.path.isfile(p):
                    target = p
                    break
        if not target:
            self.agent_say("There's no Python file to run yet — open one or "
                           "say “create file main.py” first.")
            return
        rel = os.path.relpath(target, self.base_dir())
        self._propose(Proposal(
            "command", f"python {rel}",
            "Runs your code with the studio's Python; output streams into "
            "the terminal below.",
            lambda t=target: app.run_file(t),
            preview=f"$ python {rel}"))

    def _intent_install(self, raw):
        names = [n for n in re.split(r"[\s,]+", raw) if re.match(
            r"^[A-Za-z0-9_.\[\]=<>!~-]+$", n)]
        if not names:
            self.agent_say("That package name didn't look right — try "
                           "something like “install flask”.")
            return
        self._propose(Proposal(
            "command", f"pip install {' '.join(names)}",
            "Installs with pip; live output lands in the terminal. Nothing "
            "installs unless you accept (or run full access).",
            lambda: self.app.open_packages(autostart=names),
            preview=f"$ python -m pip install {' '.join(names)}"))

    def _intent_open(self, raw):
        base = self.base_dir()
        path = self._safe_join(base, raw)
        if os.path.isfile(path):
            self.app.open_file(path)
            self.agent_say(f"Opened {os.path.basename(path)} in the editor.")
            return
        # fuzzy: match by substring anywhere in the workspace
        hits = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in
                           (".git", "__pycache__", ".venv", "venv")]
            for fn in filenames:
                if raw.lower() in fn.lower():
                    hits.append(os.path.join(dirpath, fn))
            if len(hits) >= 5:
                break
        if len(hits) == 1:
            self.app.open_file(hits[0])
            self.agent_say(f"Opened {os.path.basename(hits[0])}.")
        elif hits:
            self.agent_say("Found a few matches:\n" +
                           "\n".join("• " + os.path.relpath(h, base)
                                     for h in hits[:5]))
        else:
            self.agent_say(f"I can't find “{raw}” in the workspace.")

    def _intent_explain(self):
        content = self.app.editor.get_content()
        lines = content.count("\n")
        defs_ = len(re.findall(r"^\s*def\s+\w+", content, re.M))
        classes = len(re.findall(r"^\s*class\s+\w+", content, re.M))
        imports = len(re.findall(r"^\s*(?:import|from)\s+\w+", content, re.M))
        fname = (os.path.basename(self.app.editor.file_path)
                 if self.app.editor.file_path else "the editor buffer")
        self.agent_say(
            f"{fname}: {lines} lines, {len(content)} characters. "
            f"{classes} class(es), {defs_} function(s), {imports} import(s)."
            + (" Looks like an empty canvas to me." if not content.strip()
               else ""))


# ================================================================= settings
class _CfgShim:
    """Reads like a Config but serves the dialog's current field values."""

    def __init__(self, data):
        self._d = dict(data)

    def get(self, key, default=None):
        return self._d.get(key, default)


class AgentSettingsDialog(tk.Toplevel):
    """Assistant switches + brain picker (local / BYOK / GitHub / Kilo)."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        cfg = app.config
        t = app.theme
        self.t = t
        self.title(f"{AGENTS_NAME} — Settings")
        self.configure(bg=t["bg"])
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        box = tk.Frame(self, bg=t["bg"])
        box.pack(padx=24, pady=18)

        head = tk.Frame(box, bg=t["bg"])
        head.pack(fill=tk.X)
        tk.Label(head, text=AGENTS_NAME, bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 14, "bold")).pack(side=tk.LEFT)
        tk.Label(head, text="  " + AGENTS_TAGLINE, bg=t["bg"],
                 fg=t["text_secondary"], font=(FONT_UI, 10)
                 ).pack(side=tk.LEFT, pady=(4, 0))

        # ---------------------------------------------------- assistant
        sec = self._section(box, "Assistant")
        self.enable_v = tk.BooleanVar(value=bool(cfg.get("agents_enabled")))
        self.edits_v = tk.BooleanVar(value=bool(cfg.get("agents_ask_edits")))
        self.cmds_v = tk.BooleanVar(value=bool(cfg.get("agents_ask_commands")))
        self._check(sec, self.enable_v, "Enable DXN1 Agents",
                    "Shows the assistant panel on the right side of the studio.")
        self._check(sec, self.edits_v, "Ask before editing files",
                    "Every file the agent creates or changes needs your Accept.")
        self._check(sec, self.cmds_v, "Ask before running commands",
                    "Commands (run project, pip install, shell) need approval.")
        tk.Label(sec, text="Turn both prompts off for full access — the agent "
                           "then acts without asking. Dangerous commands still "
                           "stop and ask. The sandbox (workspace-only) is "
                           "always on.",
                 bg=t["card"], fg=t["text_muted"], font=(FONT_UI, 8, "italic"),
                 wraplength=500, justify=tk.LEFT
                 ).pack(anchor="w", padx=10, pady=(4, 6))

        # ---------------------------------------------------- brain
        secb = self._section(box, "Brain — pick where the agent thinks")
        self.kind_v = tk.StringVar(value=cfg.get("agents_backend", "local"))
        if self.kind_v.get() not in llm.BACKEND_KINDS:
            self.kind_v.set("local")
        kinds = (("local", "Local skills", "Offline · no network · no key"),
                 ("free", "Free cloud", "Keyless · auto-failover to GitHub Models"),
                 ("byok", "BYOK", "Your API key · OpenRouter, Groq, Gemini…"),
                 ("github", "GitHub Models", "Free tier · your GitHub login"),
                 ("kilo", "Kilo gateway", "Free models · Google login · tiny client"))
        row = tk.Frame(secb, bg=t["card"])
        row.pack(fill=tk.X, padx=10, pady=(0, 6))
        self._kind_btns = {}
        for kid, label, sub in kinds:
            b = tk.Label(row, text=label, bg=t["card"], fg=t["text"],
                         font=(FONT_UI, 9, "bold"), cursor="hand2",
                         padx=10, pady=6)
            b.pack(side=tk.LEFT, padx=(0, 6))
            b.bind("<Button-1>", lambda e, k=kid: self._pick_kind(k))
            self._kind_btns[kid] = b

        self._detail = tk.Frame(secb, bg=t["card"])
        self._detail.pack(fill=tk.X, padx=10, pady=(0, 8))
        self._subframes = {}
        self._build_local_sub()
        self._build_free_sub(cfg)
        self._build_byok_sub(cfg)
        self._build_github_sub(cfg)
        self._build_kilo_sub(cfg)

        # ---------------------------------------------------- behaviour
        secbh = self._section(box, "Behaviour — the agent's system prompt")
        prow = tk.Frame(secbh, bg=t["card"])
        prow.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Label(prow, text="Style preset:", bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 9)).pack(anchor="w")
        self.preset_v = tk.StringVar(
            value=cfg.get("agents_prompt_preset", "default"))
        if self.preset_v.get() not in PROMPT_STYLES:
            self.preset_v.set("default")
        prow2 = tk.Frame(secbh, bg=t["card"])
        prow2.pack(fill=tk.X, padx=10)
        for key, spec in PROMPT_STYLES.items():
            tk.Radiobutton(prow2, text=spec["label"], variable=self.preset_v,
                           value=key, bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0,
                           bd=0, command=self._preset_changed
                           ).pack(side=tk.LEFT, padx=(0, 10))
        self.preset_note = tk.Label(secbh, text="", bg=t["card"],
                                    fg=t["text_secondary"], font=(FONT_UI, 8),
                                    wraplength=500, justify=tk.LEFT, anchor="w")
        self.preset_note.pack(anchor="w", padx=10, pady=(2, 4))
        prow3 = tk.Frame(secbh, bg=t["card"])
        prow3.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Label(prow3, text="Extra instructions (persona, house style…):",
                 bg=t["card"], fg=t["text"], font=(FONT_UI, 9)
                 ).pack(anchor="w")
        self.prompt_txt = tk.Text(prow3, height=3, bg=t["editor"], fg=t["text"],
                                  insertbackground=t["text"], relief=tk.FLAT,
                                  font=(FONT_MONO, 9), highlightthickness=1,
                                  highlightbackground=t["border"],
                                  highlightcolor=t.accent, wrap=tk.WORD)
        self.prompt_txt.pack(fill=tk.X, pady=(3, 4))
        if cfg.get("agents_system_prompt"):
            self.prompt_txt.insert("1.0", cfg.get("agents_system_prompt"))
        pview = tk.Label(prow3, text="Preview the effective system prompt",
                         bg=t["card"], fg=t.accent, font=(FONT_UI, 8, "bold"),
                         cursor="hand2")
        pview.pack(anchor="w", pady=(0, 2))
        pview.bind("<Button-1>", lambda e: self._preview_prompt())
        srow = tk.Frame(secbh, bg=t["card"])
        srow.pack(fill=tk.X, padx=10, pady=(0, 8))
        tk.Label(srow, text="Max tool steps per message:", bg=t["card"],
                 fg=t["text"], font=(FONT_UI, 9)).pack(side=tk.LEFT)
        self.steps_v = tk.StringVar(value=str(cfg.get("agents_max_steps", 12)))
        tk.Entry(srow, textvariable=self.steps_v, width=4, bg=t["editor"],
                 fg=t["text"], insertbackground=t["text"], relief=tk.FLAT,
                 font=(FONT_MONO, 10), highlightthickness=1,
                 highlightbackground=t["border"],
                 highlightcolor=t.accent).pack(side=tk.LEFT, padx=8)

        # ---------------------------------------------------- test + buttons
        trow = tk.Frame(box, bg=t["bg"])
        trow.pack(fill=tk.X, pady=(8, 0))
        test_btn = tk.Label(trow, text="Test connection", bg=t["card"],
                            fg=t.accent, font=(FONT_UI, 10, "bold"),
                            cursor="hand2", padx=12, pady=6)
        test_btn.pack(side=tk.LEFT)
        test_btn.bind("<Button-1>", lambda e: self._test())
        self.test_result = tk.Label(trow, text="", bg=t["bg"],
                                    fg=t["text_muted"], font=(FONT_UI, 9))
        self.test_result.pack(side=tk.LEFT, padx=10)

        row = tk.Frame(box, bg=t["bg"])
        row.pack(fill=tk.X, pady=(12, 0))
        cancel = tk.Label(row, text="Cancel", bg=t["bg"],
                          fg=t["text_secondary"], font=(FONT_UI, 10),
                          cursor="hand2", padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: self.destroy())
        save = tk.Label(row, text="Save", bg=t.accent, fg="#ffffff",
                        font=(FONT_UI, 10, "bold"), cursor="hand2",
                        padx=18, pady=6)
        save.pack(side=tk.RIGHT)
        save.bind("<Button-1>", lambda e: self._save())

        self.bind("<Escape>", lambda e: self.destroy())
        self._pick_kind(self.kind_v.get())
        self._preset_changed()
        self._center()

    # ------------------------------------------------------------- widgets
    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=self.t["bg"],
                 fg=self.t["text_secondary"], font=(FONT_UI, 9, "bold")
                 ).pack(anchor="w", pady=(12, 4))
        frame = tk.Frame(parent, bg=self.t["card"], highlightthickness=1,
                         highlightbackground=self.t["card_border"])
        frame.pack(fill=tk.X, ipady=6)
        inner = tk.Frame(frame, bg=self.t["card"])
        inner.pack(fill=tk.X)
        return inner

    def _check(self, parent, var, title, sub):
        row = tk.Frame(parent, bg=self.t["card"])
        row.pack(fill=tk.X, pady=2, ipady=2)
        cb = tk.Checkbutton(row, variable=var, bg=self.t["card"],
                            fg=self.t["text"],
                            activebackground=self.t["card"],
                            activeforeground=self.t["text"],
                            selectcolor=self.t["editor"],
                            highlightthickness=0, bd=0)
        cb.pack(side=tk.LEFT, padx=(10, 4))
        txt = tk.Frame(row, bg=self.t["card"])
        txt.pack(side=tk.LEFT)
        tk.Label(txt, text=title, bg=self.t["card"], fg=self.t["text"],
                 font=(FONT_UI, 10, "bold"), anchor="w").pack(anchor="w")
        tk.Label(txt, text=sub, bg=self.t["card"], fg=self.t["text_secondary"],
                 font=(FONT_UI, 8), wraplength=440, justify=tk.LEFT,
                 anchor="w").pack(anchor="w")

    def _field(self, parent, label, value, width=38, show="", hint=None):
        tk.Label(parent, text=label, bg=self.t["card"], fg=self.t["text"],
                 font=(FONT_UI, 9)).pack(anchor="w", pady=(4, 1))
        var = tk.StringVar(value=value)
        e = tk.Entry(parent, textvariable=var, width=width, show=show,
                     bg=self.t["editor"], fg=self.t["text"],
                     insertbackground=self.t["text"], relief=tk.FLAT,
                     font=(FONT_MONO, 9), highlightthickness=1,
                     highlightbackground=self.t["border"],
                     highlightcolor=self.t.accent)
        e.pack(fill=tk.X, ipady=4)
        if hint:
            tk.Label(parent, text=hint, bg=self.t["card"],
                     fg=self.t["text_muted"], font=(FONT_UI, 8),
                     wraplength=470, justify=tk.LEFT,
                     anchor="w").pack(anchor="w", pady=(1, 0))
        return var

    # ------------------------------------------------------- brain subpages
    def _build_local_sub(self):
        f = tk.Frame(self._detail, bg=self.t["card"])
        self._subframes["local"] = f
        tk.Label(f, text="The agent runs its built-in offline skills — "
                         "create files, scaffold apps, run, install. No key, "
                         "no network. Attach a model below whenever you want "
                         "a brain that can reason about your code.",
                 bg=self.t["card"], fg=self.t["text_secondary"],
                 font=(FONT_UI, 9), wraplength=470, justify=tk.LEFT
                 ).pack(anchor="w", pady=(2, 4))

    def _build_free_sub(self, cfg):
        f = tk.Frame(self._detail, bg=self.t["card"])
        self._subframes["free"] = f
        tk.Label(f, text="The free stack — keyless cloud models first, then "
                         "automatic failover to GitHub Models when a GitHub "
                         "login is detected (gh CLI / token). No account, no "
                         "API key, no setup. The header chip always shows "
                         "which brain actually answered.",
                 bg=self.t["card"], fg=self.t["text_secondary"],
                 font=(FONT_UI, 9), wraplength=470, justify=tk.LEFT
                 ).pack(anchor="w", pady=(2, 2))
        self.free_model_v = self._field(
            f, "Model (optional — empty = auto with fallback chain)",
            cfg.get("agents_model", "") if
            cfg.get("agents_backend") == "free" else "", width=44,
            hint="Defaults to the free chain: " + " → ".join(llm.FREE_MODELS)
                 + ". Hit “Fetch models” to see what's live today.")
        row = tk.Frame(f, bg=self.t["card"])
        row.pack(fill=tk.X, pady=(4, 2))
        self._fetch_btn = tk.Label(row, text="Fetch models", bg=self.t["card"],
                                   fg=self.t.accent, font=(FONT_UI, 9, "bold"),
                                   cursor="hand2", padx=10, pady=5)
        self._fetch_btn.pack(side=tk.LEFT)
        self._fetch_btn.bind("<Button-1>", lambda e: self._fetch_models(
            llm.PollinationsBackend.BASE, ""))
        self._fetch_result = tk.Label(row, text="", bg=self.t["card"],
                                      fg=self.t["text_muted"],
                                      font=(FONT_UI, 8))
        self._fetch_result.pack(side=tk.LEFT, padx=8)

    def _build_byok_sub(self, cfg):
        f = tk.Frame(self._detail, bg=self.t["card"])
        self._subframes["byok"] = f
        self.provider_v = tk.StringVar(
            value=cfg.get("agents_provider", "openrouter"))
        prow = tk.Frame(f, bg=self.t["card"])
        prow.pack(fill=tk.X)
        tk.Label(prow, text="Provider:", bg=self.t["card"], fg=self.t["text"],
                 font=(FONT_UI, 9)).pack(side=tk.LEFT)
        names = [f"{pid}  ·  {p['label']}" for pid, p in llm.PRESETS.items()]
        self._provider_menu = tk.OptionMenu(
            prow, self.provider_v, *list(llm.PRESETS.keys()))
        self._provider_menu.config(bg=self.t["editor"], fg=self.t["text"],
                                   activebackground=self.t["hover"],
                                   highlightthickness=0, bd=0,
                                   font=(FONT_UI, 9))
        self._provider_menu.pack(side=tk.LEFT, padx=8)
        self.byok_url_v = self._field(
            f, "Endpoint (OpenAI-compatible)",
            cfg.get("agents_base_url", ""), width=44)
        self.byok_key_v = self._field(
            f, "API key", cfg.get("agents_api_key", ""), width=44,
            show="•", hint="Stored only in ~/.dxn1-studio/config.json on this "
                           "machine. Free-model tip: OpenRouter models ending "
                           "in :free cost nothing.")
        self.byok_model_v = self._field(
            f, "Model", cfg.get("agents_model", ""), width=44)
        self.byok_note = tk.Label(f, text="", bg=self.t["card"],
                                  fg=self.t["text_secondary"], font=(FONT_UI, 8),
                                  wraplength=470, justify=tk.LEFT, anchor="w")
        self.byok_note.pack(anchor="w", pady=(2, 0))
        brow = tk.Frame(f, bg=self.t["card"])
        brow.pack(fill=tk.X, pady=(6, 2))
        fetch = tk.Label(brow, text="Fetch models", bg=self.t["card"],
                         fg=self.t.accent, font=(FONT_UI, 9, "bold"),
                         cursor="hand2", padx=10, pady=5)
        fetch.pack(side=tk.LEFT)
        fetch.bind("<Button-1>", lambda e: self._fetch_models(
            self.byok_url_v.get(), self.byok_key_v.get()))
        connect = tk.Label(brow, text="Connect online…", bg=self.t["card"],
                           fg=self.t.accent, font=(FONT_UI, 9, "bold"),
                           cursor="hand2", padx=10, pady=5)
        connect.pack(side=tk.LEFT, padx=(8, 0))
        connect.bind("<Button-1>", lambda e: ConnectDialog(self.app))
        self.byok_fetch_result = tk.Label(brow, text="", bg=self.t["card"],
                                          fg=self.t["text_muted"],
                                          font=(FONT_UI, 8))
        self.byok_fetch_result.pack(side=tk.LEFT, padx=8)
        # register the preset watcher only AFTER the fields exist, then seed
        self.provider_v.trace_add("write", lambda *a: self._apply_preset())
        self.provider_v.set(cfg.get("agents_provider", "openrouter"))
        self._apply_preset()

    def _apply_preset(self):
        pid = self.provider_v.get()
        preset = llm.PRESETS.get(pid, llm.PRESETS["openrouter"])
        if not (self.byok_url_v.get() or "").strip():
            self.byok_url_v.set(preset["base_url"])
        self.byok_note.config(text=preset["note"] +
                              ("  Suggested: " + " · ".join(preset["models"][:3])
                               if preset["models"] else ""))

    def _build_github_sub(self, cfg):
        f = tk.Frame(self._detail, bg=self.t["card"])
        self._subframes["github"] = f
        tk.Label(f, text="Free models, tracked via your GitHub account. If "
                         "you're signed in with GitHub CLI, zero setup — "
                         "otherwise paste a token (needs no paid plan; "
                         "rate limits apply).",
                 bg=self.t["card"], fg=self.t["text_secondary"],
                 font=(FONT_UI, 9), wraplength=470, justify=tk.LEFT
                 ).pack(anchor="w", pady=(2, 2))
        self.gh_key_v = self._field(
            f, "GitHub token (optional if gh is logged in)",
            cfg.get("agents_github_key", ""), width=44, show="•",
            hint="Checked in order: this field → GH_TOKEN → `gh auth token`.")
        self.gh_model_v = self._field(
            f, "Model", cfg.get("agents_model", "") or "openai/gpt-4o-mini",
            width=44,
            hint="Catalog: github.com/marketplace/models — e.g. "
                 "openai/gpt-4o-mini, meta/Meta-Llama-3.3-70B-Instruct.")

    def _build_kilo_sub(self, cfg):
        f = tk.Frame(self._detail, bg=self.t["card"])
        self._subframes["kilo"] = f
        tk.Label(f, text="Kilo gateway gives you free-model routing. This is "
                         "a direct HTTP client built into the studio — NOT "
                         "the VS Code extension — so it adds near-zero RAM "
                         "instead of hundreds of MB.",
                 bg=self.t["card"], fg=self.t["text_secondary"],
                 font=(FONT_UI, 9), wraplength=470, justify=tk.LEFT
                 ).pack(anchor="w", pady=(2, 2))
        self.kilo_url_v = self._field(
            f, "Gateway endpoint",
            cfg.get("agents_kilo_url", "") or llm.KiloBackend.DEFAULT_BASE,
            width=44,
            hint="If your Kilo dashboard shows a different endpoint, paste "
                 "it here.")
        self.kilo_key_v = self._field(
            f, "Kilo token", cfg.get("agents_kilo_key", ""), width=44,
            show="•")
        self.kilo_model_v = self._field(
            f, "Model", cfg.get("agents_model", ""), width=44,
            hint='"auto" lets the gateway pick; model ids follow your Kilo '
                 'account.')
        brow = tk.Frame(f, bg=self.t["card"])
        brow.pack(fill=tk.X, pady=(6, 2))
        connect = tk.Label(brow, text="Connect online…", bg=self.t["card"],
                           fg=self.t.accent, font=(FONT_UI, 9, "bold"),
                           cursor="hand2", padx=10, pady=5)
        connect.pack(side=tk.LEFT)
        connect.bind("<Button-1>", lambda e: ConnectDialog(self.app))

    def _pick_kind(self, kind):
        self.kind_v.set(kind)
        for kid, btn in self._kind_btns.items():
            btn.config(bg=self.t.accent if kid == kind else self.t["card"],
                       fg="#ffffff" if kid == kind else self.t["text"])
        for kid, frame in self._subframes.items():
            if kid == kind:
                frame.pack(fill=tk.X, expand=True)
            else:
                frame.pack_forget()

    # ------------------------------------------------------- prompt helpers
    def _preset_changed(self):
        spec = PROMPT_STYLES.get(self.preset_v.get(), PROMPT_STYLES["default"])
        self.preset_note.config(text=spec["description"] +
                                ("  Your extra text below IS the personality."
                                 if self.preset_v.get() == "custom" else
                                 "  Extra text below is appended."))

    def _preview_prompt(self):
        sandbox = None
        panel = self.app.agent_panel
        if panel is not None and panel.sandbox is not None:
            sandbox = panel.sandbox
        if sandbox is None:
            try:
                sandbox = WorkspaceSandbox(os.getcwd())
            except SandboxError:
                sandbox = None
        if sandbox is None:
            PromptPreviewDialog(self.app, "(no workspace open — start the "
                                "sandbox to preview the real prompt)")
            return
        try:
            prompt = build_system_prompt(
                sandbox, AGENTS_NAME,
                self.prompt_txt.get("1.0", "end").strip(),
                style=self.preset_v.get())
        except Exception as exc:  # noqa: BLE001
            prompt = f"(preview failed: {exc})"
        PromptPreviewDialog(self.app, prompt)

    def _fetch_models(self, base_url, api_key):
        result = self._fetch_result if self.kind_v.get() == "free" else \
            self.byok_fetch_result
        result.config(text="fetching…", fg=self.t["text_muted"])

        def work():
            try:
                ids = llm.fetch_models(base_url, api_key)
                text = " · ".join(ids[:6]) + (" …" if len(ids) > 6 else "")
                self.after(0, lambda: result.config(
                    text=text[:120], fg=self.t["success"]))
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)[:120]
                self.after(0, lambda: result.config(
                    text=msg, fg="#f85149"))
        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------------- test
    def _dialog_config(self):
        return _CfgShim({
            "agents_backend": self.kind_v.get(),
            "agents_provider": self.provider_v.get(),
            "agents_base_url": self.byok_url_v.get(),
            "agents_api_key": self.byok_key_v.get(),
            "agents_model": self._model_for_kind(),
            "agents_github_key": self.gh_key_v.get(),
            "agents_kilo_url": self.kilo_url_v.get(),
            "agents_kilo_key": self.kilo_key_v.get(),
        })

    def _model_for_kind(self):
        kind = self.kind_v.get()
        if kind == "free":
            return self.free_model_v.get()
        if kind == "github":
            return self.gh_model_v.get()
        if kind == "kilo":
            return self.kilo_model_v.get()
        return self.byok_model_v.get()

    def _test(self):
        self.test_result.config(text="testing…", fg=self.t["text_muted"])
        backend = llm.build_backend(self._dialog_config())
        if backend is None:
            self.test_result.config(text="local skills need no connection ✓",
                                    fg=self.t["success"])
            return

        def work():
            ok, detail = llm.test_backend(backend)
            self.after(0, lambda: self.test_result.config(
                text=("✓ " + detail) if ok else ("✗ " + detail),
                fg=self.t["success"] if ok else "#f85149"))
        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------- save/close
    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.master.winfo_rootx() + max(0, (self.master.winfo_width() - w) // 2)
        y = self.master.winfo_rooty() + max(0, (self.master.winfo_height() - h) // 3)
        self.geometry(f"+{x}+{y}")

    def _save(self):
        cfg = self.app.config
        try:
            steps = max(2, min(40, int(self.steps_v.get())))
        except ValueError:
            steps = 12
        cfg.set("agents_enabled", bool(self.enable_v.get()))
        cfg.set("agents_ask_edits", bool(self.edits_v.get()))
        cfg.set("agents_ask_commands", bool(self.cmds_v.get()))
        cfg.set("agents_backend", self.kind_v.get())
        cfg.set("agents_provider", self.provider_v.get())
        cfg.set("agents_base_url", self.byok_url_v.get().strip())
        cfg.set("agents_api_key", self.byok_key_v.get().strip())
        cfg.set("agents_model", self._model_for_kind().strip())
        cfg.set("agents_github_key", self.gh_key_v.get().strip())
        cfg.set("agents_kilo_url", self.kilo_url_v.get().strip())
        cfg.set("agents_kilo_key", self.kilo_key_v.get().strip())
        cfg.set("agents_system_prompt",
                self.prompt_txt.get("1.0", "end").strip())
        cfg.set("agents_prompt_preset", self.preset_v.get())
        cfg.set("agents_max_steps", steps)
        # a successful save means the brain is wired up — drop the hint
        cfg.set("agents_setup_pending", "")

        self.app.apply_agents_visibility()
        if self.app.agent_panel is not None:
            if self.app.project_dir:
                self.app.agent_panel.set_workspace(self.app.project_dir)
            else:
                self.app.agent_panel.refresh_backend()
        self.app.terminal.log(
            f"{AGENTS_NAME}: "
            + ("enabled" if self.enable_v.get() else "disabled")
            + f" · brain: {llm.describe_backend(cfg)}"
            + ("" if (self.edits_v.get() and self.cmds_v.get())
               else " · full access mode"))
        self.grab_release()
        self.destroy()


# ================================================================= connect
class PromptPreviewDialog(tk.Toplevel):
    """Read-only view of the agent's effective system prompt."""

    def __init__(self, app, text):
        super().__init__(app.root)
        t = app.theme
        self.title("Effective system prompt")
        self.configure(bg=t["bg"])
        self.geometry("680x520")
        self.transient(app.root)
        tk.Label(self, text="What the agent is told (plus live workspace "
                            "listing at runtime):", bg=t["bg"],
                 fg=t["text_secondary"], font=(FONT_UI, 9), anchor="w"
                 ).pack(fill=tk.X, padx=14, pady=(12, 4))
        box = tk.Text(self, bg=t["editor"], fg=t["text"], relief=tk.FLAT,
                      font=(FONT_MONO, 9), wrap=tk.WORD, padx=12, pady=10,
                      highlightthickness=1, highlightbackground=t["border"])
        box.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))
        box.insert("1.0", text)
        box.config(state="disabled")
        self.bind("<Escape>", lambda e: self.destroy())


class ConnectDialog(tk.Toplevel):
    """In-app provider connect flow.

    The whole flow stays inside DXN1 STUDIO: the studio opens the provider
    page (Google login happens there), you paste the key/token back into
    THIS window, hit Test, then Save. Nothing is written anywhere except
    the studio's own local config.
    """

    PROVIDERS = {
        "kilo": {
            "title": "Kilo gateway (free · Google login)",
            "url": "https://kilocode.ai",
            "steps": ["1.  Open kilocode.ai and sign in with Google.",
                      "2.  Grab your API token from the dashboard.",
                      "3.  Paste it below — the studio stores it locally."],
            "key_label": "Kilo token",
            "model": "auto",
            "fields": ("agents_kilo_key", "agents_kilo_url"),
            "backend": "kilo",
        },
        "openrouter": {
            "title": "OpenRouter (free models · Google login)",
            "url": "https://openrouter.ai/settings/keys",
            "steps": ["1.  Open openrouter.ai — sign in with Google.",
                      "2.  Create a key (Keys page). Free models end in :free.",
                      "3.  Paste the key below — it never leaves this machine."],
            "key_label": "OpenRouter API key",
            "model": "deepseek/deepseek-chat-v3.1:free",
            "fields": ("agents_api_key", "agents_base_url"),
            "backend": "byok",
        },
        "github": {
            "title": "GitHub Models (free · GitHub login)",
            "url": "https://github.com/settings/tokens",
            "steps": ["1.  Already using `gh auth login`? Zero setup — hit Test.",
                      "2.  Otherwise create a classic token (no scopes needed "
                      "for models).",
                      "3.  Paste it below or rely on gh."],
            "key_label": "GitHub token (optional)",
            "model": "openai/gpt-4o-mini",
            "fields": ("agents_github_key", None),
            "backend": "github",
        },
    }

    def __init__(self, app, provider=None):
        super().__init__(app.root)
        self.app = app
        self.cfg = app.config
        t = app.theme
        self.t = t
        self.provider = provider or self.cfg.get("agents_setup_pending") or "kilo"
        if self.provider not in self.PROVIDERS:
            self.provider = "kilo"
        self.title("DXN1 STUDIO — Connect a brain")
        self.configure(bg=t["bg"])
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        box = tk.Frame(self, bg=t["bg"])
        box.pack(padx=26, pady=20)
        tk.Label(box, text="Connect a brain — inside the app",
                 bg=t["bg"], fg=t["text"], font=(FONT_UI, 14, "bold")
                 ).pack(anchor="w")
        tk.Label(box, text="Google login happens on the provider's page; the "
                           "key comes back into this window. Stored only in "
                           "~/.dxn1-studio/config.json.",
                 bg=t["bg"], fg=t["text_secondary"], font=(FONT_UI, 9),
                 wraplength=460, justify=tk.LEFT).pack(anchor="w", pady=(2, 10))

        prow = tk.Frame(box, bg=t["bg"])
        prow.pack(fill=tk.X, pady=(0, 8))
        self._prov_btns = {}
        for pid, spec in self.PROVIDERS.items():
            b = tk.Label(prow, text=spec["title"].split(" (")[0],
                         bg=t["card"], fg=t["text"], font=(FONT_UI, 9, "bold"),
                         cursor="hand2", padx=10, pady=6)
            b.pack(side=tk.LEFT, padx=(0, 6))
            b.bind("<Button-1>", lambda e, k=pid: self._pick(k))
            self._prov_btns[pid] = b

        self.body = tk.Frame(box, bg=t["bg"])
        self.body.pack(fill=tk.X)
        self._step_labels = []
        self._build_provider_body()

        row = tk.Frame(box, bg=t["bg"])
        row.pack(fill=tk.X, pady=(14, 0))
        self.test_result = tk.Label(row, text="", bg=t["bg"],
                                    fg=t["text_muted"], font=(FONT_UI, 9))
        self.test_result.pack(side=tk.LEFT)
        later = tk.Label(row, text="Later", bg=t["bg"], fg=t["text_secondary"],
                         font=(FONT_UI, 10), cursor="hand2", padx=10)
        later.pack(side=tk.RIGHT)
        later.bind("<Button-1>", lambda e: self.destroy())
        self.save_btn = tk.Label(row, text="Test & Save", bg=t.accent,
                                 fg="#ffffff", font=(FONT_UI, 10, "bold"),
                                 cursor="hand2", padx=16, pady=6)
        self.save_btn.pack(side=tk.RIGHT)
        self.save_btn.bind("<Button-1>", lambda e: self._save())

        self.bind("<Escape>", lambda e: self.destroy())
        self._pick(self.provider)
        self._center()

    # ------------------------------------------------------------ widgets
    def _build_provider_body(self):
        for w in self.body.winfo_children():
            w.destroy()
        spec = self.PROVIDERS[self.provider]
        t = self.t
        card = tk.Frame(self.body, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        card.pack(fill=tk.X, ipady=8)
        for step in spec["steps"]:
            tk.Label(card, text=step, bg=t["card"], fg=t["text_secondary"],
                     font=(FONT_UI, 9), wraplength=440, justify=tk.LEFT,
                     anchor="w").pack(anchor="w", padx=12, pady=1)
        open_lbl = tk.Label(card, text="⟶  Open " + spec["url"].split("/")[2],
                            bg=t["card"], fg=t.accent,
                            font=(FONT_UI, 10, "bold"), cursor="hand2")
        open_lbl.pack(anchor="w", padx=12, pady=(6, 2))
        open_lbl.bind("<Button-1>", lambda e: self._open_site())
        tk.Label(card, text=spec["key_label"] + ":", bg=t["card"],
                 fg=t["text"], font=(FONT_UI, 9), anchor="w"
                 ).pack(anchor="w", padx=12, pady=(6, 1))
        key_field = spec["fields"][0]
        current = self.cfg.get(key_field, "")
        self.key_v = tk.StringVar(value=current)
        e = tk.Entry(card, textvariable=self.key_v, width=46, show="•",
                     bg=t["editor"], fg=t["text"],
                     insertbackground=t["text"], relief=tk.FLAT,
                     font=(FONT_MONO, 10), highlightthickness=1,
                     highlightbackground=t["border"],
                     highlightcolor=t.accent)
        e.pack(fill=tk.X, padx=12, ipady=5)
        tk.Label(card, text="Model:", bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 9), anchor="w").pack(anchor="w", padx=12,
                                                     pady=(6, 1))
        model_field = spec["fields"][1]
        stored_model = self.cfg.get("agents_model", "")
        self.model_v = tk.StringVar(value=stored_model or spec["model"])
        tk.Entry(card, textvariable=self.model_v, width=46,
                 bg=t["editor"], fg=t["text"], insertbackground=t["text"],
                 relief=tk.FLAT, font=(FONT_MONO, 10), highlightthickness=1,
                 highlightbackground=t["border"],
                 highlightcolor=t.accent).pack(fill=tk.X, padx=12, ipady=5)

    def _pick(self, pid):
        self.provider = pid
        for k, b in self._prov_btns.items():
            b.config(bg=self.t.accent if k == pid else self.t["card"],
                     fg="#ffffff" if k == pid else self.t["text"])
        self._build_provider_body()

    def _open_site(self):
        url = self.PROVIDERS[self.provider]["url"]
        self.test_result.config(text=f"opening {url.split('/')[2]} in your "
                                     f"browser — come back here with the "
                                     f"key…", fg=self.t["text_muted"])
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            self.test_result.config(text=f"couldn't open a browser — visit "
                                         f"{url} manually ({exc})",
                                    fg="#f85149")

    def _dialog_config(self):
        spec = self.PROVIDERS[self.provider]
        data = {"agents_backend": spec["backend"],
                "agents_provider": self.provider
                if spec["backend"] == "byok" else
                self.cfg.get("agents_provider", "openrouter"),
                "agents_model": self.model_v.get().strip(),
                "agents_base_url": self.cfg.get("agents_base_url", ""),
                "agents_api_key": self.cfg.get("agents_api_key", ""),
                "agents_github_key": self.cfg.get("agents_github_key", ""),
                "agents_kilo_url": self.cfg.get("agents_kilo_url", ""),
                "agents_kilo_key": self.cfg.get("agents_kilo_key", "")}
        key_field, _url_field = spec["fields"]
        data[key_field] = self.key_v.get().strip()
        return _CfgShim(data)

    def _save(self):
        self.test_result.config(text="testing connection…",
                                fg=self.t["text_muted"])
        backend = llm.build_backend(self._dialog_config())

        def work():
            ok, detail = (True, "local skills need no connection") \
                if backend is None else llm.test_backend(backend)
            if ok:
                spec = self.PROVIDERS[self.provider]
                key_field, _u = spec["fields"]
                self.cfg.set("agents_backend", spec["backend"])
                if spec["backend"] == "byok":
                    self.cfg.set("agents_provider", self.provider)
                self.cfg.set(key_field, self.key_v.get().strip())
                self.cfg.set("agents_model", self.model_v.get().strip())
                self.cfg.set("agents_setup_pending", "")
                self.cfg.set("agents_enabled", True)
            def finish():
                if ok:
                    self.test_result.config(text="✓ " + detail,
                                            fg=self.t["success"])
                    app = self.app
                    app.apply_agents_visibility()
                    if app.agent_panel is not None:
                        if app.project_dir:
                            app.agent_panel.set_workspace(app.project_dir)
                        else:
                            app.agent_panel.refresh_backend()
                    app.terminal.log(
                        f"{AGENTS_NAME}: connected · "
                        f"{llm.describe_backend(self.cfg)}")
                    self.grab_release()
                    self.destroy()
                else:
                    self.test_result.config(text="✗ " + str(detail)[:110],
                                            fg="#f85149")
            self.after(0, finish)
        threading.Thread(target=work, daemon=True).start()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.master.winfo_rootx() + \
            max(0, (self.master.winfo_width() - w) // 2)
        y = self.master.winfo_rooty() + \
            max(0, (self.master.winfo_height() - h) // 3)
        self.geometry(f"+{x}+{y}")
