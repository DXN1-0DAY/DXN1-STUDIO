"""DXN1 STUDIO — Task Runner.

Small, fast, file-based run configurations. A workspace can declare
tasks in ``<workspace>/.dxn1/tasks.json``; the runner also proposes
sensible defaults per project kind so ``pytest``, ``cargo run`` or
``npm run dev`` are one click away without any setup.

``.dxn1/tasks.json`` format::

    {
      "tasks": [
        {"name": "tests",  "cmd": "pytest -q", "cwd": ""},
        {"name": "format", "cmd": "ruff format .", "shell": true}
      ]
    }

* ``cwd`` is relative to the workspace root ("" = root)
* ``env`` adds environment variables on top of the inherited ones
* ``shell`` (default true) runs the command through /bin/sh -c so
  pipes and && work — commands run with your user's permissions,
  exactly like typing them in the studio terminal

The engine is UI-free (engine tests run headless); TaskRunnerWindow
streams output live, supports stopping tasks and editing the JSON.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time

from . import APP_NAME
from . import projects

TASKS_DIR = os.path.join(".dxn1")
TASKS_FILE = os.path.join(TASKS_DIR, "tasks.json")

MAX_BUFFER_LINES = 4000            # output guardrail


# ------------------------------------------------------------------ engine
def tasks_path(workspace):
    """Absolute path of the workspace's tasks.json (not required to exist)."""
    return os.path.join(workspace, TASKS_DIR, "tasks.json") if workspace else ""


def list_tasks(workspace):
    """Validated task list from tasks.json — [] on any problem."""
    path = tasks_path(workspace)
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        raw = data.get("tasks") if isinstance(data, dict) else data
        if not isinstance(raw, list):
            return []
    except (OSError, ValueError):
        return []
    out = []
    for t in raw:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name") or "").strip()
        cmd = str(t.get("cmd") or "").strip()
        if not name or not cmd:
            continue
        out.append({
            "name": name,
            "cmd": cmd,
            "cwd": str(t.get("cwd") or ""),
            "env": t.get("env") if isinstance(t.get("env"), dict) else {},
            "shell": t.get("shell", True) is not False,
        })
    return out


def save_tasks(workspace, tasks):
    """Write tasks.json (creates .dxn1/). Returns the path written."""
    if not workspace:
        raise ValueError("no workspace")
    os.makedirs(os.path.join(workspace, TASKS_DIR), exist_ok=True)
    path = tasks_path(workspace)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"tasks": tasks}, fh, indent=2)
        fh.write("\n")
    return path


def default_tasks_for(kind):
    """Sensible starter tasks per project kind (engine-tested)."""
    table = {
        "python": [("run main.py", "python main.py"),
                   ("syntax check", "python -m compileall -q .")],
        "flask": [("dev server", "python app.py"),
                  ("install deps", "pip install -r requirements.txt")],
        "fastapi": [("dev server", "python -m uvicorn main:app --reload"),
                    ("install deps", "pip install -r requirements.txt")],
        "requests": [("run main.py", "python main.py")],
        "tkinter": [("run app", "python main.py")],
        "game": [("play", "python main.py")],
        "todo": [("run app", "python main.py")],
        "package": [("pytest", "python -m pytest -q"),
                    ("build sdist+wheel", "python -m build")],
        "tests": [("pytest", "python -m pytest -q")],
        "cli": [("help", "python -m {slug} --help")],
        "static": [("open index.html", "echo open index.html in a browser")],
        "rust": [("cargo run", "cargo run"),
                 ("cargo test", "cargo test"),
                 ("cargo build --release", "cargo build --release")],
        "go": [("go run", "go run ."),
               ("go test", "go test ./...")],
        "nextjs": [("dev server", "npm run dev"),
                   ("build", "npm run build"),
                   ("install deps", "npm install")],
        "svelte": [("dev server", "npm run dev"),
                   ("build", "npm run build"),
                   ("install deps", "npm install")],
        "data": [("explore", "python main.py"),
                 ("install deps", "pip install -r requirements.txt")],
        "scraper": [("scrape", "python main.py"),
                    ("install deps", "pip install -r requirements.txt")],
        "bot": [("run bot", "python bot.py"),
                ("install deps", "pip install -r requirements.txt")],
    }
    return [{"name": n, "cmd": c.format(slug="main"), "cwd": "", "env": {},
             "shell": True}
            for n, c in table.get(kind, [("run main.py", "python main.py")])]


def suggest_tasks(workspace, kind=None):
    """tasks.json tasks, or defaults for the workspace kind."""
    tasks = list_tasks(workspace)
    if tasks:
        return tasks, "file"
    if kind is None and workspace:
        kind = projects.read_project_meta(workspace).get("kind", "empty")
    return default_tasks_for(kind), "default"


class RunningTask:
    """Handle over one live subprocess (threaded streaming)."""

    def __init__(self, task, workspace, on_line=None, on_done=None):
        self.task = task
        self.workspace = workspace
        self._on_line = on_line or (lambda line: None)
        self._on_done = on_done or (lambda code: None)
        self.proc = None
        self.started = time.time()
        self.exit_code = None
        self._thread = None

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        cwd = os.path.join(self.workspace, self.task["cwd"]) \
            if self.workspace and self.task["cwd"] else \
            (self.workspace or os.getcwd())
        env = dict(os.environ)
        env.update({str(k): str(v) for k, v in self.task["env"].items()})
        args = self.task["cmd"]
        popen_kwargs = dict(cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            bufsize=1, errors="replace")
        if self.task["shell"]:
            popen_kwargs["shell"] = True
            args = self.task["cmd"]
        else:
            args = self.task["cmd"].split()
        try:
            self.proc = subprocess.Popen(args, **popen_kwargs)
        except OSError as exc:
            self._on_line(f"[runner] could not start: {exc}\n")
            self.exit_code = -1
            self._on_done(-1)
            return self

        def pump():
            assert self.proc and self.proc.stdout
            n = 0
            for line in self.proc.stdout:
                if n >= MAX_BUFFER_LINES:
                    self._on_line("[runner] output truncated\n")
                    break
                self._on_line(line)
                n += 1
            code = self.proc.wait()
            self.exit_code = code
            secs = time.time() - self.started
            self._on_line(f"[runner] exited {code} in {secs:.1f}s\n")
            self._on_done(code)

        self._thread = threading.Thread(target=pump, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if not self.alive:
            return False
        try:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self._on_line("[runner] stopped by user\n")
            return True
        except OSError:
            return False


def run_task(task, workspace, on_line=None, on_done=None):
    """Convenience: start a task, return the RunningTask handle."""
    return RunningTask(task, workspace, on_line, on_done).start()


# --------------------------------------------------------------------- GUI
_TR_C = {"bg": "#0d1117", "card": "#131a22", "border": "#232c3d",
         "text": "#e6edf3", "secondary": "#9aa7b8", "muted": "#6e7a8a",
         "ok": "#3fb950", "bad": "#f85149", "input": "#11161d"}


def open_runner(master, theme, config=None, workspace=None, kind=None,
                on_log=None):
    """Open the Task Runner window (palette entry point)."""
    return TaskRunnerWindow(master, theme, workspace, kind,
                            on_log=on_log)


class TaskRunnerWindow:
    """Left: task list (file tasks + defaults). Right: live output."""

    def __init__(self, master, theme, workspace=None, kind=None,
                 on_log=None):
        import tkinter as tk
        from tkinter import messagebox

        self.tk = tk
        self.msgbox = messagebox
        self.accent = getattr(theme, "accent", "#7c3aed")
        self.workspace = workspace
        self.kind = kind
        self.on_log = on_log or (lambda m: None)
        self.current = None            # RunningTask

        self.win = tk.Toplevel(master)
        self.win.title(f"{APP_NAME} — Tasks")
        self.win.configure(bg=_TR_C["bg"])
        self.win.transient(master)
        self.win.resizable(True, True)
        self.win.geometry("860x520")
        # DS2 v2.62 — width accounting round four: once the build
        # settles, open no narrower (or shorter) than what it
        # actually packed (the 860x520 default is the floor)
        from . import geom as _geom
        self.win.after_idle(lambda: _geom.fit_to_content(
            self.win, 860, 520))
        self.win.bind("<Escape>", lambda e: self.win.destroy())

        head = tk.Frame(self.win, bg=_TR_C["bg"])
        head.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(head, text="Task Runner", bg=_TR_C["bg"], fg=_TR_C["text"],
                 font=("sans-serif", 13, "bold")).pack(side="left")
        self.src_lbl = tk.Label(head, text="", bg=_TR_C["bg"],
                                fg=_TR_C["muted"], font=("sans-serif", 9))
        self.src_lbl.pack(side="left", padx=(10, 0))
        close = tk.Label(head, text="✕", bg=_TR_C["bg"], fg=_TR_C["muted"],
                         font=("sans-serif", 11, "bold"), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self._close())

        body = tk.Frame(self.win, bg=_TR_C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(8, 0))

        # left column — tasks
        left = tk.Frame(body, bg=_TR_C["bg"])
        left.pack(side="left", fill="y", padx=(0, 10))
        self.task_list = tk.Frame(left, bg=_TR_C["bg"])
        self.task_list.pack(fill="y", expand=True)

        add_row = tk.Frame(left, bg=_TR_C["bg"])
        add_row.pack(fill="x", pady=(8, 0))
        self.name_var = tk.StringVar()
        self.cmd_var = tk.StringVar()
        name_e = tk.Entry(add_row, textvariable=self.name_var, width=14,
                          bg=_TR_C["input"], fg=_TR_C["text"],
                          insertbackground=_TR_C["text"], relief="flat",
                          font=("sans-serif", 9))
        name_e.pack(side="top", fill="x", pady=(0, 3))
        cmd_e = tk.Entry(add_row, textvariable=self.cmd_var, width=22,
                         bg=_TR_C["input"], fg=_TR_C["text"],
                         insertbackground=_TR_C["text"], relief="flat",
                         font=("sans-serif", 9))
        cmd_e.pack(side="top", fill="x", pady=(0, 3))
        add_btn = tk.Label(add_row, text="＋ save task", bg=_TR_C["card"],
                           fg=self.accent, font=("sans-serif", 9, "bold"),
                           padx=8, pady=4, cursor="hand2")
        add_btn.pack(side="left")
        add_btn.bind("<Button-1>", lambda e: self._add_task())
        edit_btn = tk.Label(add_row, text="edit JSON", bg=_TR_C["card"],
                            fg=_TR_C["secondary"],
                            font=("sans-serif", 9, "bold"),
                            padx=8, pady=4, cursor="hand2")
        edit_btn.pack(side="left", padx=(6, 0))
        edit_btn.bind("<Button-1>", lambda e: self._edit_json())

        # right column — output
        right = tk.Frame(body, bg=_TR_C["bg"])
        right.pack(side="left", fill="both", expand=True)
        out_head = tk.Frame(right, bg=_TR_C["bg"])
        out_head.pack(fill="x")
        self.status_lbl = tk.Label(out_head, text="idle", bg=_TR_C["bg"],
                                   fg=_TR_C["muted"],
                                   font=("sans-serif", 9))
        self.status_lbl.pack(side="left")
        stop = tk.Label(out_head, text="■ stop", bg=_TR_C["card"],
                        fg=_TR_C["bad"], font=("sans-serif", 9, "bold"),
                        padx=10, pady=3, cursor="hand2")
        stop.pack(side="right")
        stop.bind("<Button-1>", lambda e: self._stop())
        clear = tk.Label(out_head, text="clear", bg=_TR_C["card"],
                         fg=_TR_C["secondary"],
                         font=("sans-serif", 9, "bold"), padx=10, pady=3,
                         cursor="hand2")
        clear.pack(side="right", padx=(0, 6))
        clear.bind("<Button-1>", lambda e: self.out.delete("1.0", "end"))

        self.out = tk.Text(right, bg="#0a0e14", fg=_TR_C["secondary"],
                           font=("monospace", 9), relief="flat", bd=0,
                           state="disabled", wrap="none",
                           highlightthickness=1,
                           highlightbackground=_TR_C["border"])
        from .theme import make_scrollbar
        _sb = make_scrollbar(right, _TR_C, "vertical",
                             command=self.out.yview)
        self.out.configure(yscrollcommand=_sb.set)
        _sb.pack(side="right", fill="y")
        self.out.pack(fill="both", expand=True, pady=(4, 12))

        self.refresh_tasks()
        self.win.protocol("WM_DELETE_WINDOW", self._close)

    # ------------------------------------------------------------- tasks
    def refresh_tasks(self):
        tk = self.tk
        for w in self.task_list.winfo_children():
            w.destroy()
        tasks, source = suggest_tasks(self.workspace, self.kind)
        self.src_lbl.config(
            text=f"· {len(tasks)} tasks from {source}"
                 + ("" if self.workspace else " · no workspace open"))
        if not tasks:
            tk.Label(self.task_list, text="No tasks available.",
                     bg=_TR_C["bg"], fg=_TR_C["muted"],
                     font=("sans-serif", 9)).pack(anchor="w")
            return
        for t in tasks:
            self._task_row(t)

    def _task_row(self, task):
        tk = self.tk
        row = tk.Frame(self.task_list, bg=_TR_C["card"],
                       highlightthickness=1,
                       highlightbackground=_TR_C["border"])
        row.pack(fill="x", pady=2, ipady=3)
        name = tk.Label(row, text=task["name"], bg=_TR_C["card"],
                        fg=_TR_C["text"], font=("sans-serif", 9, "bold"),
                        width=16, anchor="w")
        name.pack(side="left", padx=(10, 2))
        cmd = tk.Label(row, text=task["cmd"], bg=_TR_C["card"],
                       fg=_TR_C["muted"], font=("monospace", 8),
                       anchor="w")
        cmd.pack(side="left", fill="x", expand=True)
        run = tk.Label(row, text="▶", bg=_TR_C["card"], fg=self.accent,
                       font=("sans-serif", 11, "bold"), padx=10,
                       cursor="hand2")
        run.pack(side="right")
        run.bind("<Button-1>", lambda e, t=task: self._run(t))
        for w in (row, name, cmd):
            w.bind("<Button-1>", lambda e, t=task: self._run(t))

    # ------------------------------------------------------------ actions
    def _say(self, text):
        self.out.config(state="normal")
        self.out.insert("end", text)
        if self.out.index("end-1c").split(".")[
                0] > str(MAX_BUFFER_LINES):
            self.out.delete("1.0", "200.0")
        self.out.see("end")
        self.out.config(state="disabled")

    def _run(self, task):
        if self.current and self.current.alive:
            self._say("[runner] a task is already running — stop it first\n")
            return
        if not self.workspace:
            self._say("[runner] open a workspace first\n")
            return
        self._say(f"$ {task['cmd']}\n")
        self.status_lbl.config(text=f"running: {task['name']}",
                               fg=self.accent)
        self.current = run_task(
            task, self.workspace,
            on_line=lambda line: self.win.after(0, self._say, line),
            on_done=lambda code: self.win.after(
                0, lambda c=code: self._done(task, c)))

    def _done(self, task, code):
        self.status_lbl.config(
            text=f"{task['name']} — exit {code}",
            fg=_TR_C["ok"] if code == 0 else _TR_C["bad"])
        self.on_log(f"task '{task['name']}' exited {code}")

    def _stop(self):
        if self.current and self.current.alive:
            self.current.stop()
        else:
            self._say("[runner] nothing to stop\n")

    def _add_task(self):
        name = self.name_var.get().strip()
        cmd = self.cmd_var.get().strip()
        if not name or not cmd:
            self._say("[runner] give the task a name and a command\n")
            return
        if not self.workspace:
            self._say("[runner] open a workspace first\n")
            return
        tasks = list_tasks(self.workspace)
        tasks = [t for t in tasks if t["name"] != name]
        tasks.append({"name": name, "cmd": cmd, "cwd": "", "env": {},
                      "shell": True})
        try:
            save_tasks(self.workspace, tasks)
        except OSError as exc:
            self._say(f"[runner] save failed: {exc}\n")
            return
        self.name_var.set("")
        self.cmd_var.set("")
        self._say(f"[runner] saved task '{name}' -> .dxn1/tasks.json\n")
        self.refresh_tasks()

    def _edit_json(self):
        if not self.workspace:
            return
        try:
            save_tasks(self.workspace,
                       list_tasks(self.workspace))
        except OSError:
            pass
        path = tasks_path(self.workspace)
        self._say(f"[runner] tasks file: {path}\n")
        # open in the studio's editor if the host provided a way
        self.on_log(f"tasks file: {path}")

    def _close(self):
        try:
            self._stop()
        except Exception:               # noqa: BLE001
            pass
        self.win.destroy()
