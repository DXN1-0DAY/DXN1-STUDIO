"""DXN1 STUDIO — task runner (DS2 v2.2).

Project tasks without the ceremony: a ``tasks.json`` in the workspace
defines named commands ("test": "pytest -q", "dev": "python main.py"),
the terminal panel can run them by name, and the Task Runner window
lists them with one-click Run. Ships with sensible defaults per
project kind when no tasks.json exists yet.

JSON shape (tolerant — strings are promoted to {"command": str}):

{
  "tasks": {
    "run":  {"command": "python main.py", "desc": "start the app"},
    "test": {"command": "pytest -q"}
  }
}
"""

import json
import os
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

TASKS_FILE = os.path.join(".dxn1", "tasks.json")

DEFAULT_TASKS = {
    "run": {"command": "python main.py", "desc": "start the app"},
    "test": {"command": "pytest -q", "desc": "run the test suite"},
}


def load_tasks(workspace):
    """Read tasks.json (tolerant) or the defaults. Returns {name: dict}."""
    if not workspace:
        return {}
    path = os.path.join(workspace, TASKS_FILE)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            tasks = data.get("tasks", data) if isinstance(data, dict) else {}
            out = {}
            for name, spec in tasks.items():
                if isinstance(spec, str):
                    out[str(name)] = {"command": spec}
                elif isinstance(spec, dict) and spec.get("command"):
                    out[str(name)] = spec
            return out
    except (OSError, ValueError, AttributeError):
        pass
    return {k: dict(v) for k, v in DEFAULT_TASKS.items()}


def save_tasks(workspace, tasks):
    if not workspace:
        return False
    path = os.path.join(workspace, TASKS_FILE)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"tasks": tasks}, fh, indent=2)
        return True
    except OSError:
        return False


class TaskRunner(tk.Toplevel):
    """List tasks, click Run — commands execute through the studio's
    own terminal so output lands where the user expects it."""

    def __init__(self, parent, theme, workspace, on_run=None, on_log=None):
        super().__init__(parent)
        self.t = theme
        self.workspace = workspace or ""
        self.on_run = on_run or (lambda cmd: None)
        self.on_log = on_log or (lambda msg: None)
        self.title("Tasks — DXN1 STUDIO")
        self.configure(bg=self.t["bg"])
        self.geometry("520x420")
        self.minsize(420, 300)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build()
        self._refresh()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            x = max(0, (self.winfo_screenwidth() - 520) // 2)
            y = max(0, (self.winfo_screenheight() - 420) // 3)
            self.geometry(f"520x420+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="▶  TASKS", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        tk.Label(bar, text="tasks live in .dxn1/tasks.json", bg=t["header"],
                 fg=t["text_muted"], font=(FONT_UI, 8)).pack(
            side=tk.RIGHT, padx=12)
        self.body = tk.Frame(self, bg=t["bg"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.status = tk.Label(self, text="", bg=t["statusbar"],
                               fg=t["text_muted"], font=(FONT_UI, 8),
                               anchor="w", padx=12, pady=5)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _refresh(self):
        for w in self.body.winfo_children():
            w.destroy()
        t = self.t
        tasks = load_tasks(self.workspace)
        if not tasks:
            tk.Label(self.body,
                     text="No tasks here.\n\nAdd .dxn1/tasks.json:\n"
                          '{ "tasks": { "run": "python main.py" } }',
                     bg=t["bg"], fg=t["text_muted"], font=(FONT_MONO, 9),
                     justify=tk.LEFT).pack(anchor="w", pady=10)
            return
        for name, spec in sorted(tasks.items()):
            row = tk.Frame(self.body, bg=t["card"], highlightthickness=1,
                           highlightbackground=t["card_border"])
            row.pack(fill=tk.X, pady=2, ipady=4)
            tk.Label(row, text=name, bg=t["card"], fg=t.accent,
                     font=(FONT_MONO, 10, "bold"), width=12,
                     anchor="w").pack(side=tk.LEFT, padx=10)
            info = spec.get("desc") or spec.get("command", "")
            tk.Label(row, text=info[:52], bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8),
                     anchor="w").pack(side=tk.LEFT, fill=tk.X,
                                      expand=True, padx=6)
            run = tk.Label(row, text="▶ run", bg=t["editor"],
                           fg=t["text"], font=(FONT_UI, 8, "bold"),
                           cursor="hand2", padx=10, pady=3)
            run.pack(side=tk.RIGHT, padx=(0, 8))
            run.bind("<Button-1>", lambda e, c=spec.get("command", ""):
                     self._run_task(c))

    def _run_task(self, command):
        if not command:
            return
        self.on_log(f"task: {command}")
        try:
            self.on_run(command)
            self.status.config(text=f"running: {command[:60]}")
        except Exception as exc:
            self.status.config(text=f"failed: {str(exc)[:60]}")


def open_tasks(parent, theme, workspace, on_run=None, on_log=None):
    """Convenience opener — mirrors the studio's one-call dialog style."""
    return TaskRunner(parent, theme, workspace, on_run=on_run,
                      on_log=on_log)
