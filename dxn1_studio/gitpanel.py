"""DXN1 STUDIO — source control sidebar (v1.1.3).

A Git panel that speaks plain ``git`` through ``subprocess`` — no
libraries, no daemons. It shows the branch, the changed files (staged
and unstaged), lets you stage/unstage, write a message and commit, and
browse the last commits. Everything is one short-lived ``git`` call per
refresh, so the panel costs nothing when you are not looking at it.

States it handles gracefully: git not installed, folder is not a
repository (offers ``git init``), empty repository (offers the first
commit), and merge conflicts (files marked with a red "!" flag).
"""

import os
import subprocess
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO
from .widgets import TREE_SKIP
from .i18n import tr

try:  # DS2 visual git suite — optional at boot, never blocks the panel
    from . import gitgraph
    from . import branches as branches_mod
except Exception:  # pragma: no cover — broken install keeps git working
    gitgraph = None
    branches_mod = None

STATUS_FLAG = {
    "M": ("M", "#e3b341"),      # modified
    "A": ("A", "#3fb950"),      # added
    "D": ("D", "#f85149"),      # deleted
    "R": ("R", "#a371f7"),      # renamed
    "C": ("C", "#a371f7"),      # copied
    "U": ("!", "#f85149"),      # unmerged / conflict
    "?": ("+", "#e3b341"),      # untracked
}


def _run_git(repo, *args, timeout=15):
    """Run git in repo; return (ok, stdout, stderr)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True,
            timeout=timeout)
    except FileNotFoundError:
        return False, "", "git is not installed"
    except subprocess.TimeoutExpired:
        return False, "", "git timed out"
    except OSError as exc:
        return False, "", str(exc)
    return proc.returncode == 0, proc.stdout, proc.stderr.strip()


def repo_state(workspace):
    """DS2 v2.40 — cheap repo probe for the statusbar git chip.

    One ``git status --porcelain -b`` call, no UI, never raises.
    Returns ``{"repo": bool, "branch": str, "dirty": int,
    "ahead": int, "behind": int}`` where ``dirty`` counts every
    porcelain row (staged, unstaged and untracked alike) and
    ``ahead``/``behind`` come from the branch line's tracking
    summary. A missing workspace, a non-repo, or any git trouble
    reads as ``repo: False`` — the chip stays quiet for plain
    folders instead of nagging."""
    ws = str(workspace or "")
    out = {"repo": False, "branch": "", "dirty": 0, "ahead": 0,
           "behind": 0}
    if not ws or not os.path.isdir(ws):
        return out
    ok, text, _err = _run_git(ws, "status", "--porcelain", "-b",
                              "--untracked-files=normal", timeout=8)
    if not ok:
        return out                       # not a repo / git missing
    out["repo"] = True
    for i, line in enumerate(text.splitlines()):
        if i == 0 and line.startswith("##"):
            body = line[2:].strip()
            low = body.lower()
            if "no branch" in low:       # detached HEAD
                out["branch"] = "(detached)"
                continue
            if low.startswith("no commits yet on "):
                out["branch"] = body.rsplit(" ", 1)[-1]
                continue
            head, _, rest = body.partition("...")
            out["branch"] = head.strip()
            if "[" in rest and "]" in rest:
                flags = rest[rest.index("[") + 1:rest.index("]")]
                for part in flags.split(","):
                    bits = part.strip().split()
                    if len(bits) == 2 and bits[1].isdigit():
                        if bits[0] == "ahead":
                            out["ahead"] = int(bits[1])
                        elif bits[0] == "behind":
                            out["behind"] = int(bits[1])
        elif line.strip():
            out["dirty"] += 1
    return out


class GitPanel(tk.Frame):
    """'Source Control' sidebar — the studio's view over your repo."""

    def __init__(self, parent, theme, on_open_file=None, on_log=None,
                 config=None):
        super().__init__(parent, bg=theme["sidebar"])
        self.theme = theme
        self.on_open_file = on_open_file
        self.on_log = on_log or (lambda msg: None)
        self.config = config          # DS2: needed for the AI message chip
        self.workspace = None
        self._is_repo = False

        # ------------------------------------------------------------ header
        header = tk.Frame(self, bg=theme["header"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="SOURCE CONTROL", bg=theme["header"],
                 fg=theme["text_secondary"],
                 font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT, padx=15)
        self.branch_lbl = tk.Label(header, text="", bg=theme["header"],
                                   fg=theme["text_muted"],
                                   font=(FONT_MONO, 8))
        self.branch_lbl.pack(side=tk.LEFT, padx=4)
        refresh = tk.Label(header, text="⟳", bg=theme["header"],
                           fg=theme["text_secondary"], cursor="hand2",
                           font=(FONT_UI, 11, "bold"))
        refresh.pack(side=tk.RIGHT, padx=12)
        refresh.bind("<Button-1>", lambda e: self.refresh())

        # ------------------------------------------------------- commit box
        box = tk.Frame(self, bg=theme["sidebar"])
        box.pack(fill=tk.X, padx=10, pady=(10, 4))
        self.msg = tk.Entry(box, bg=theme["editor"], fg=theme["text"],
                            insertbackground=theme["text"], relief=tk.FLAT,
                            font=(FONT_MONO, 9), highlightthickness=1,
                            highlightbackground=theme["border"],
                            highlightcolor=theme.accent)
        self.msg.pack(fill=tk.X, ipady=5)
        self.msg.insert(0, "")
        self._placeholder()
        self.msg.bind("<FocusIn>", self._placeholder_clear)
        self.msg.bind("<FocusOut>", self._placeholder)
        self.msg.bind("<Return>", lambda e: self.commit())

        crow = tk.Frame(box, bg=theme["sidebar"])
        crow.pack(fill=tk.X, pady=(6, 0))
        self.commit_btn = tk.Label(
            crow, text="✓  Commit", bg=theme.accent, fg="#ffffff",
            font=(FONT_UI, 9, "bold"), cursor="hand2", padx=12, pady=5)
        self.commit_btn.pack(side=tk.LEFT)
        self.commit_btn.bind("<Button-1>", lambda e: self.commit())
        # DS2: AI commit message chip
        self.ai_btn = tk.Label(crow, text="✨ AI msg", bg=theme["card"],
                               fg=theme["text_secondary"],
                               font=(FONT_UI, 9, "bold"), cursor="hand2",
                               padx=10, pady=5)
        self.ai_btn.pack(side=tk.LEFT, padx=(6, 0))
        self.ai_btn.bind("<Button-1>", lambda e: self.ai_message())
        stage_all = tk.Label(crow, text="+ Stage all", bg=theme["card"],
                             fg=theme["text_secondary"], cursor="hand2",
                             font=(FONT_UI, 9), padx=10, pady=5)
        stage_all.pack(side=tk.LEFT, padx=(6, 0))
        stage_all.bind("<Button-1>", lambda e: self.stage_all())

        self.status = tk.Label(self, text="", bg=theme["sidebar"],
                               fg=theme["text_muted"], font=(FONT_UI, 8),
                               anchor="w")
        self.status.pack(fill=tk.X, padx=12, pady=(2, 0))

        # --------------------------------------------- DS2 git toolbar
        self.tools = tk.Frame(self, bg=theme["sidebar"])
        self.tools.pack(fill=tk.X, padx=10, pady=(4, 0))
        for label, cmd in (("Graph", self._open_graph),
                           ("Branches", self._open_branches)):
            chip = tk.Label(self.tools, text=label, bg=theme["card"],
                            fg=theme["text_secondary"],
                            font=(FONT_UI, 9), cursor="hand2",
                            padx=10, pady=4)
            chip.pack(side=tk.LEFT, padx=(0, 6))
            chip.bind("<Button-1>", lambda e, fn=cmd: fn())

        # ----------------------------------------------------------- results
        self.canvas = tk.Canvas(self, bg=theme["sidebar"],
                                highlightthickness=0)
        sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.results = tk.Frame(self.canvas, bg=theme["sidebar"])
        self._win = self.canvas.create_window((0, 0), window=self.results,
                                              anchor="nw", width=240)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.results.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))

    # ------------------------------------------------------- placeholder
    def _placeholder(self, event=None):
        if not self.msg.get():
            self.msg.insert(0, tr("git.message_placeholder"))
            self.msg.config(fg=self.theme["text_muted"])

    def _placeholder_clear(self, event=None):
        # compare a locale-safe prefix of the translated placeholder
        if self.msg.get().startswith(tr("git.message_placeholder")[:8]):
            self.msg.delete(0, tk.END)
            self.msg.config(fg=self.theme["text"])

    # ------------------------------------------------------------- state
    def set_workspace(self, path):
        self.workspace = path if path and os.path.isdir(path) else None
        self.refresh()

    def _say(self, text):
        self.status.config(text=text)

    def _clear(self):
        for w in self.results.winfo_children():
            w.destroy()

    @staticmethod
    def _rel(repo, path):
        try:
            return os.path.relpath(path, repo).replace(os.sep, "/")
        except ValueError:
            return path

    # ------------------------------------------------------------ refresh
    def refresh(self):
        self._clear()
        t = self.theme
        if not self.workspace:
            self.branch_lbl.config(text="")
            self._say("Open a workspace first.")
            self._card("No workspace",
                       "Open a folder to see its source control here.")
            return
        ok, _, err = _run_git(self.workspace, "rev-parse", "--is-inside-work-tree")
        if not ok:
            self._is_repo = False
            self.branch_lbl.config(text="")
            if "not installed" in (err or ""):
                self._card("Git not found",
                           "Install git and hit ⟳ — the panel picks it up "
                           "automatically.")
            else:
                self._card("Not a repository",
                           "This folder has no git history yet. "
                           "Initialize one?")
                self._action_btn("git init", self._init_repo)
            self._say("")
            return
        self._is_repo = True
        ok, branch, _ = _run_git(self.workspace, "symbolic-ref", "--short",
                                 "HEAD")
        if not ok:
            # detached or unborn — either way, ask rev-parse, else "main"
            ok, branch, _ = _run_git(self.workspace, "rev-parse",
                                     "--abbrev-ref", "HEAD")
        self.branch_lbl.config(text="◆ " + ((branch or "main").strip()
                                             or "main"))
        self._render_changes()

    def _init_repo(self):
        ok, _, err = _run_git(self.workspace, "init")
        if ok:
            self.on_log("git init — repository created")
            self.refresh()
        else:
            self._say(f"git init failed: {err}")

    # ------------------------------------------------------------ changes
    def _render_changes(self):
        t = self.theme
        repo = self.workspace
        ok, out, err = _run_git(repo, "status", "--porcelain", "-b",
                                "-uall")
        if not ok:
            self._say(f"git status failed: {err}")
            return
        staged, unstaged, untracked = {}, {}, []
        lines = out.splitlines()
        for line in lines:
            if line.startswith("##") or len(line) < 4:
                continue
            x, y, path = line[0], line[1], line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ")[-1]
            if x == "?" and y == "?":
                untracked.append(path)
            else:
                if x not in (" ", "?"):
                    staged.setdefault(x, []).append(path)
                if y not in (" ", "?"):
                    unstaged.setdefault(y, []).append(path)
        branch = lines[0][3:].strip() if lines and lines[0].startswith("##") \
            else ""
        if branch:
            ahead = "ahead" in branch or "behind" in branch
            self._say(("↑ " + branch.split("[")[-1].rstrip("]"))
                      if ahead else "")

        total = len(staged) + len(unstaged) + len(untracked)
        if total == 0:
            self._card("Working tree clean",
                       "Nothing to commit — every file matches HEAD.")
            self._render_log()
            return

        seen = set()

        def flag_of(x, y):
            if x == "U" or y == "U":
                return STATUS_FLAG["U"]
            if x == "?":
                return STATUS_FLAG["?"]
            return STATUS_FLAG.get(x or y, STATUS_FLAG["M"])

        if staged:
            self._section("STAGED")
            for x, paths in staged.items():
                for p in paths:
                    if (p, "s") in seen:
                        continue
                    seen.add((p, "s"))
                    self._file_row(p, flag_of(x, " "), staged_side=True)
        if unstaged or untracked:
            self._section("CHANGES")
            for y, paths in unstaged.items():
                for p in paths:
                    self._file_row(p, flag_of(" ", y), staged_side=False)
            for p in untracked:
                self._file_row(p, STATUS_FLAG["?"], staged_side=False,
                               untracked=True)
        self._render_log()

    def _section(self, text):
        tk.Label(self.results, text=text, bg=self.theme["sidebar"],
                 fg=self.theme["text_muted"], font=(FONT_UI, 8, "bold"),
                 anchor="w").pack(fill=tk.X, padx=2, pady=(10, 2))

    def _file_row(self, path, flag, staged_side, untracked=False):
        """One changed file: flag, name, stage/unstage + open actions."""
        t = self.theme
        glyph, color = flag
        row = tk.Frame(self.results, bg=t["card"], highlightthickness=1,
                       highlightbackground=t["card_border"])
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=glyph, bg=t["card"], fg=color,
                 font=(FONT_MONO, 9, "bold"), width=2).pack(
            side=tk.LEFT, padx=(8, 0))
        name = tk.Label(row, text=os.path.basename(path), bg=t["card"],
                        fg=t["text"], font=(FONT_MONO, 9), cursor="hand2")
        name.pack(side=tk.LEFT, padx=6)
        sub = self._rel(self.workspace, path)
        if sub != path:
            name.config(text=os.path.basename(path))
        act = tk.Label(row, text="−" if staged_side else "+",
                       bg=t["card"], fg=t["text_secondary"],
                       font=(FONT_UI, 11, "bold"), cursor="hand2", padx=8)
        act.pack(side=tk.RIGHT)
        act.bind("<Button-1>", lambda e: self._stage_toggle(
            path, untrack=untracked, unstage=staged_side))
        name.bind("<Button-1>", lambda e: self._open(path))
        tip = sub if sub != os.path.basename(path) else ""
        if tip:
            _attach_tooltip(name, tip)

    def _card(self, title, body):
        t = self.theme
        card = tk.Frame(self.results, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        card.pack(fill=tk.X, pady=8, padx=2)
        tk.Label(card, text=title, bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 10, "bold"), anchor="w"
                 ).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(card, text=body, bg=t["card"], fg=t["text_secondary"],
                 font=(FONT_UI, 8), anchor="w", justify=tk.LEFT,
                 wraplength=210).pack(anchor="w", padx=12, pady=(0, 8))

    def _action_btn(self, text, cmd):
        btn = tk.Label(self.results, text=text, bg=self.theme.accent,
                       fg="#ffffff", font=(FONT_UI, 9, "bold"),
                       cursor="hand2", padx=12, pady=6)
        btn.pack(pady=(2, 8))
        btn.bind("<Button-1>", lambda e: cmd())

    # ------------------------------------------------------------- actions
    def _open_graph(self):
        if gitgraph is None or not self._is_repo:
            return
        try:
            gitgraph.open_graph(self.winfo_toplevel(), self.theme,
                                self.workspace, on_log=self.on_log)
        except Exception as exc:  # pragma: no cover — never kill the panel
            self._say(f"graph failed: {exc}")

    def _open_branches(self):
        if branches_mod is None or not self._is_repo:
            return
        try:
            branches_mod.open_branches(self.winfo_toplevel(), self.theme,
                                       self.workspace, on_log=self.on_log)
        except Exception as exc:  # pragma: no cover — never kill the panel
            self._say(f"branches failed: {exc}")

    def _open(self, relpath):
        full = os.path.join(self.workspace, relpath)
        if os.path.isfile(full) and self.on_open_file:
            self.on_open_file(full)

    def _stage_toggle(self, relpath, untrack=False, unstage=False):
        if unstage:
            ok, _, err = _run_git(self.workspace, "restore", "--staged",
                                  "--", relpath)
        else:
            ok, _, err = _run_git(self.workspace, "add", "--",
                                  relpath)
        if not ok:
            self._say(f"git failed: {err}")
            return
        verb = "unstaged" if unstage else "staged"
        self.on_log(f"git: {verb} {relpath}")
        self.refresh()

    def stage_all(self):
        if not self._is_repo:
            return
        ok, _, err = _run_git(self.workspace, "add", "-A")
        if not ok:
            self._say(f"git add failed: {err}")
            return
        self.on_log("git: staged every change")
        self.refresh()

    def ai_message(self):
        """DS2: generate a commit message with the studio's brain."""
        if not self._is_repo or not self.workspace:
            self._say("Open a repository first.")
            return
        if self.config is None:
            self._say("AI message needs the agent brain — connect one in "
                      "DXN1 Agents settings.")
            return
        self.ai_btn.config(text="… thinking", fg=self.theme["text_muted"])
        self._say("Writing a commit message from the diff…")

        def done(message):
            try:
                self.ai_btn.config(text="✨ AI msg",
                                   fg=self.theme["text_secondary"])
                if not message:
                    self._say("No changes to describe — stage something "
                              "first.")
                    return
                self._placeholder_clear()
                self.msg.delete(0, tk.END)
                self.msg.insert(0, message.splitlines()[0])
                if len(message.splitlines()) > 1:
                    self._say(message.splitlines()[1].strip()[:120])
                else:
                    self._say("AI message ready — edit if you like.")
                self.on_log("git: AI commit message generated")
            except tk.TclError:
                pass

        def fail(reason):
            try:
                self.ai_btn.config(text="✨ AI msg",
                                   fg=self.theme["text_secondary"])
                self._say(reason)
            except tk.TclError:
                pass

        def worker_cb(message):
            self.after(0, lambda: done(message))

        def error_cb(reason):
            self.after(0, lambda: fail(reason))

        try:
            from . import commit_msg
            commit_msg.generate_message(self.workspace, self.config,
                                        worker_cb, error_cb)
        except Exception as exc:
            fail(f"AI message failed: {exc}")

    def commit(self):
        if not self._is_repo:
            return
        self._placeholder_clear()
        message = self.msg.get().strip()
        if not message or message.startswith("Message ("):
            self._say("Write a commit message first.")
            self.msg.focus_set()
            return
        ok, out, _ = _run_git(self.workspace, "diff", "--cached", "--quiet")
        if ok:
            # exit 0 == nothing staged — stage everything so one
            # click just works
            _run_git(self.workspace, "add", "-A")
            self.on_log("git: nothing was staged — staged all changes")
        ok, _, err = _run_git(self.workspace, "commit", "-m", message)
        if not ok:
            self._say(f"commit failed: {err[:120]}")
            return
        self.msg.delete(0, tk.END)
        self._placeholder()
        self.on_log(f"git commit: {message}")
        try:  # DS2: plugin on_commit hook — best effort
            from . import plugins as _pl
            _pl.get_registry().fire_commit(message,
                                           workspace=self.workspace)
        except Exception:
            pass
        try:  # DS2: first-run checklist
            from .checklist import mark
            mark(self.config, "commit")
        except Exception:
            pass
        self._say("Committed ✓")
        self.refresh()

    # ----------------------------------------------------------------- log
    def _render_log(self):
        ok, out, _ = _run_git(self.workspace, "log", "--oneline", "-8",
                              "--no-decorate")
        if not ok or not out.strip():
            self._section("HISTORY")
            tk.Label(self.results,
                     text="No commits yet — write the first one ↑",
                     bg=self.theme["sidebar"],
                     fg=self.theme["text_muted"],
                     font=(FONT_UI, 8)).pack(anchor="w", padx=6, pady=4)
            return
        self._section("HISTORY")
        for line in out.strip().splitlines()[:8]:
            sha, _, msg = line.partition(" ")
            row = tk.Label(
                self.results, text=f"{msg[:30]:<30}  {sha[:7]}"[:44],
                bg=self.theme["sidebar"], fg=self.theme["text_secondary"],
                font=(FONT_MONO, 8), anchor="w")
            row.pack(fill=tk.X, padx=6, pady=1)


def _attach_tooltip(widget, text):
    """Minimal hover tooltip (single shared Toplevel per widget)."""
    tip = {"win": None}

    def enter(_e):
        if tip["win"] is not None:
            return
        x = widget.winfo_rootx() + 12
        y = widget.winfo_rooty() - 26
        win = tk.Toplevel(widget)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"+{x}+{y}")
        tk.Label(win, text=text, bg="#1c1926", fg="#c9c4d6",
                 font=(FONT_UI, 8), padx=8, pady=3,
                 highlightthickness=1, highlightbackground="#3b3454"
                 ).pack()
        tip["win"] = win

    def leave(_e):
        if tip["win"] is not None:
            try:
                tip["win"].destroy()
            except tk.TclError:
                pass
            tip["win"] = None

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)
