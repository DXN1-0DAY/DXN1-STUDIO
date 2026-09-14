"""DXN1 STUDIO — the DXN1 Agents assistant.

DXN1 Agents is the studio's built-in copilot. It can create files,
scaffold whole apps, run the project and install packages — but how much
it may do is always under your control:

* **Ask mode** (default) — every file edit and every command appears as a
  proposal card you Accept or Decline.
* **Full access** — turn both prompts off in the agent settings and the
  agent stops asking, applying edits and running commands directly.

The agent is fully local and rule-based in this beta: no account, no
network calls, no data leaving the machine.
"""

import os
import re
import tkinter as tk

from . import APP_NAME
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

        self._build_header()
        self._build_message_area()
        self._build_input()

        self.agent_say(f"{AGENTS_NAME} online. I can create files, scaffold a "
                       f"Flask app, run your project or install packages — "
                       f"always with your permission. Type “help” to see "
                       f"everything.")

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
        self.mode_chip.pack(side=tk.LEFT, padx=10)

        gear = tk.Label(head, text="⚙", bg=self.t["header"], fg=self.t["text_muted"],
                        font=(FONT_UI, 11), cursor="hand2")
        gear.pack(side=tk.RIGHT, padx=12)
        gear.bind("<Button-1>", lambda e: self.open_settings())

        self.refresh_mode()

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
        row = tk.Frame(self, bg=self.t["sidebar"])
        row.pack(fill=tk.X, padx=10, pady=(0, 10))

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

        tk.Label(self, text="try: create file utils.py · run · install flask · help",
                 bg=self.t["sidebar"], fg=self.t["text_muted"],
                 font=(FONT_UI, 8), anchor="w").pack(fill=tk.X, padx=12, pady=(0, 6))

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

    def user_say(self, text):
        card = self._new_card()
        tk.Label(card, text=f"You  ·  {text}", bg=self.t["card"],
                 fg=self.t["text_secondary"], font=(FONT_MONO, 9),
                 wraplength=240, justify=tk.LEFT,
                 anchor="w").pack(anchor="w", padx=10, pady=7)
        self._scroll_down()

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

    def _scroll_down(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    # ------------------------------------------------------------- driving
    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.user_say(text)
        try:
            self.handle(text)
        except Exception as exc:  # never kill the IDE from the chat box
            self.agent_say(f"That hit a snag: {exc}")

    # ------------------------------------------------------------------ io
    def base_dir(self):
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
        self.app.refresh_explorer()
        names = ", ".join(os.path.basename(p) for p, _ in files)
        self.app.terminal.log(f"Agents wrote: {names}")

    def open_settings(self):
        AgentSettingsDialog(self.app)

    # -------------------------------------------------------------- intents
    def handle(self, text):
        low = text.lower().strip()

        if low in ("help", "?", "what can you do"):
            self.agent_say(
                "Here's my toolkit:\n"
                "• create file <name> — new file with a starter template\n"
                "• new flask app — scaffold a full web app (3 files)\n"
                "• run — execute the current file / project (F5)\n"
                "• install <package> — pip install, shown live in the terminal\n"
                "• open <file> — open a workspace file in the editor\n"
                "• explain — stats about the file in the editor\n"
                "• dxn1 studio — replay the boot splash\n"
                "• shell <command> — propose any terminal command")
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

        self.agent_say("I didn't catch that one yet — try “help” for the "
                       "full list of things I know how to do.")

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


class AgentSettingsDialog(tk.Toplevel):
    """Per-agent switches: enable + the two permission gates."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        cfg = app.config
        self.title(f"{AGENTS_NAME} — Settings")
        self.configure(bg=app.theme["bg"])
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        box = tk.Frame(self, bg=app.theme["bg"])
        box.pack(padx=26, pady=22)

        tk.Label(box, text=AGENTS_NAME, bg=app.theme["bg"], fg=app.theme["text"],
                 font=(FONT_UI, 14, "bold")).pack(anchor="w")
        tk.Label(box, text=AGENTS_TAGLINE, bg=app.theme["bg"],
                 fg=app.theme["text_secondary"], font=(FONT_UI, 10)
                 ).pack(anchor="w", pady=(2, 14))

        self.enable_v = tk.BooleanVar(value=bool(cfg.get("agents_enabled")))
        self.edits_v = tk.BooleanVar(value=bool(cfg.get("agents_ask_edits")))
        self.cmds_v = tk.BooleanVar(value=bool(cfg.get("agents_ask_commands")))

        def check(parent, var, title, sub):
            row = tk.Frame(parent, bg=app.theme["card"], highlightthickness=1,
                           highlightbackground=app.theme["card_border"])
            row.pack(fill=tk.X, pady=4, ipady=6)
            cb = tk.Checkbutton(row, variable=var, bg=app.theme["card"],
                                fg=app.theme["text"], activebackground=app.theme["card"],
                                activeforeground=app.theme["text"],
                                selectcolor=app.theme["editor"],
                                highlightthickness=0, bd=0)
            cb.pack(side=tk.LEFT, padx=(12, 4))
            txt = tk.Frame(row, bg=app.theme["card"])
            txt.pack(side=tk.LEFT)
            tk.Label(txt, text=title, bg=app.theme["card"],
                     fg=app.theme["text"], font=(FONT_UI, 10, "bold"),
                     anchor="w").pack(anchor="w")
            tk.Label(txt, text=sub, bg=app.theme["card"],
                     fg=app.theme["text_secondary"], font=(FONT_UI, 8),
                     wraplength=380, justify=tk.LEFT, anchor="w").pack(anchor="w")

        check(box, self.enable_v, "Enable DXN1 Agents",
              "Shows the assistant panel on the right side of the studio.")
        check(box, self.edits_v, "Ask before editing files",
              "Every file the agent creates or changes needs your Accept.")
        check(box, self.cmds_v, "Ask before running commands",
              "Commands (run project, pip install, shell) need your approval.")

        note = tk.Frame(box, bg=app.theme["bg"])
        note.pack(fill=tk.X, pady=(10, 0))
        tk.Label(note, text="Turn both prompts off to give the agent full "
                            "access — it then applies edits and runs commands "
                            "without asking. You can switch back anytime.",
                 bg=app.theme["bg"], fg=app.theme["text_muted"],
                 font=(FONT_UI, 8, "italic"), wraplength=430,
                 justify=tk.LEFT).pack(anchor="w")

        row = tk.Frame(box, bg=app.theme["bg"])
        row.pack(fill=tk.X, pady=(16, 0))
        cancel = tk.Label(row, text="Cancel", bg=app.theme["bg"],
                          fg=app.theme["text_secondary"], font=(FONT_UI, 10),
                          cursor="hand2", padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: self.destroy())
        save = tk.Label(row, text="Save", bg=app.theme.accent, fg="#ffffff",
                        font=(FONT_UI, 10, "bold"), cursor="hand2",
                        padx=18, pady=6)
        save.pack(side=tk.RIGHT)
        save.bind("<Button-1>", lambda e: self._save())

        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.master.winfo_rootx() + max(0, (self.master.winfo_width() - w) // 2)
        y = self.master.winfo_rooty() + max(0, (self.master.winfo_height() - h) // 3)
        self.geometry(f"+{x}+{y}")

    def _save(self):
        cfg = self.app.config
        cfg.set("agents_enabled", bool(self.enable_v.get()))
        cfg.set("agents_ask_edits", bool(self.edits_v.get()))
        cfg.set("agents_ask_commands", bool(self.cmds_v.get()))
        self.app.apply_agents_visibility()
        self.app.terminal.log(
            f"{AGENTS_NAME}: " + ("enabled" if self.enable_v.get() else "disabled")
            + ("" if (self.edits_v.get() and self.cmds_v.get())
               else " · full access mode"))
        self.grab_release()
        self.destroy()
