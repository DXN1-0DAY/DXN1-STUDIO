"""DXN1 STUDIO — branch manager (DS2 v1.4).

A focused window over your branches: create, checkout, rename, delete,
merge and track, with ahead/behind badges pulled from
``git for-each-ref`` in a single call. Remote sections show every
``origin/*`` head with a one-click "track" that creates the local
branch. Tags live in their own section with checkout-to-detached.

Destructive actions (delete) use a two-click confirm — the button turns
into "sure?" for three seconds, so no modal dialogs interrupt the flow.
Every operation reports through a status line and the studio log.
"""

import subprocess
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO


def run_git(repo, *args, timeout=15):
    """Run git in repo; return (ok, stdout, stderr)."""
    try:
        proc = subprocess.run(["git", *args], cwd=repo,
                              capture_output=True, text=True,
                              timeout=timeout)
    except FileNotFoundError:
        return False, "", "git is not installed"
    except subprocess.TimeoutExpired:
        return False, "", "git timed out"
    except OSError as exc:
        return False, "", str(exc)
    return proc.returncode == 0, proc.stdout, proc.stderr.strip()


def list_branches(repo):
    """One-shot branch inventory.

    Returns (locals, remotes, tags) where each branch dict has:
    name, short, upstream, track, is_head. Tag list is [name, sha].
    """
    fmt = ("%(refname:short)\x1f%(objectname:short)\x1f"
           "%(upstream:short)\x1f%(upstream:track)\x1f%(HEAD)")
    locals_, remotes = [], []
    ok, out, err = run_git(repo, "for-each-ref", f"--format={fmt}",
                           "refs/heads")
    if ok:
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) != 5:
                continue
            name, short, upstream, track, head = parts
            if not name or name.endswith("/HEAD"):
                continue
            locals_.append({"name": name, "short": short,
                            "upstream": upstream, "track": track.strip(),
                            "is_head": head == "*"})
    ok, out, err = run_git(repo, "for-each-ref", f"--format={fmt}",
                           "refs/remotes")
    if ok:
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) != 5:
                continue
            name, short, upstream, track, head = parts
            if (not name or name == "origin" or name.endswith("/HEAD")
                    or "/" not in name):
                continue
            remotes.append({"name": name, "short": short,
                            "upstream": "", "track": "",
                            "is_head": False})
    tags = []
    ok, out, _ = run_git(repo, "for-each-ref",
                         "--sort=-creatordate",
                         "--format=%(refname:short)\x1f%(objectname:short)",
                         "refs/tags")
    if ok:
        for line in out.splitlines()[:60]:
            parts = line.split("\x1f")
            if len(parts) == 2:
                tags.append((parts[0], parts[1]))
    return locals_, remotes, tags


def subjects_for(repo, shas):
    """Map short-sha → subject using one git log call."""
    if not shas:
        return {}
    ok, out, _ = run_git(repo, "log", "--all", "--no-decorate",
                         "--pretty=format:%h\x1f%s")
    if not ok:
        return {}
    return dict(line.split("\x1f", 1) for line in out.splitlines()
                if "\x1f" in line)


def current_branch(repo):
    ok, out, _ = run_git(repo, "symbolic-ref", "--short", "HEAD")
    if ok:
        return out.strip()
    ok, out, _ = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if ok else "HEAD"


class BranchManager(tk.Toplevel):
    """Create / switch / merge / clean up — without the terminal."""

    def __init__(self, parent, theme, workspace, on_log=None):
        super().__init__(parent)
        self.t = theme
        self.workspace = workspace
        self.on_log = on_log or (lambda msg: None)
        self.title("Branches")
        self.configure(bg=self.t["bg"])
        self.geometry("760x600")
        self.minsize(560, 380)
        self.transient(parent.winfo_toplevel()
                       if hasattr(parent, "winfo_toplevel") else parent)

        self._build_header()
        self._build_new_row()
        self._build_list()
        self._build_status()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()
        self.refresh()

    def _center(self):
        try:
            self.update_idletasks()
            x = max(0, (self.winfo_screenwidth() - 760) // 2)
            y = max(0, (self.winfo_screenheight() - 600) // 3)
            self.geometry(f"760x600+{x}+{y}")
        except tk.TclError:
            pass

    # ------------------------------------------------------------- chrome
    def _build_header(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⎇  Branches", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        self.current_lbl = tk.Label(bar, text="", bg=t["header"],
                                    fg=t.accent,
                                    font=(FONT_MONO, 10, "bold"))
        self.current_lbl.pack(side=tk.LEFT, padx=8)
        refresh = tk.Label(bar, text="⟳ Refresh", bg=t["card"],
                           fg=t["text_secondary"], font=(FONT_UI, 9),
                           cursor="hand2", padx=10, pady=4)
        refresh.pack(side=tk.RIGHT, padx=12)
        refresh.bind("<Button-1>", lambda e: self.refresh())

    def _build_new_row(self):
        t = self.t
        row = tk.Frame(self, bg=t["bg"])
        row.pack(fill=tk.X, padx=12, pady=(10, 4))
        self.new_entry = tk.Entry(row, bg=t["editor"], fg=t["text"],
                                  insertbackground=t["text"],
                                  relief=tk.FLAT, font=(FONT_MONO, 10),
                                  highlightthickness=1,
                                  highlightbackground=t["border"],
                                  highlightcolor=t.accent)
        self.new_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.new_entry.insert(0, "")
        self.new_entry.bind("<Return>", lambda e: self.create_branch())
        btn = tk.Label(row, text="+ New branch", bg=t.accent, fg="#ffffff",
                       font=(FONT_UI, 9, "bold"), cursor="hand2",
                       padx=12, pady=6)
        btn.pack(side=tk.LEFT, padx=(8, 0))
        btn.bind("<Button-1>", lambda e: self.create_branch())

    def _build_list(self):
        t = self.t
        wrap = tk.Frame(self, bg=t["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 4))
        canvas = tk.Canvas(wrap, bg=t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=canvas.yview)
        self.list_inner = tk.Frame(canvas, bg=t["bg"])
        self._win = canvas.create_window((0, 0),
                                         window=self.list_inner,
                                         anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(
            self._win, width=e.width))
        self.list_inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        self.canvas = canvas

    def _build_status(self):
        t = self.t
        self.status = tk.Label(self, text="", bg=t["statusbar"],
                               fg=t["text_muted"], font=(FONT_UI, 8),
                               anchor="w")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _say(self, text):
        self.status.config(text=text)

    def _section(self, text):
        tk.Label(self.list_inner, text=text, bg=self.t["bg"],
                 fg=self.t["text_muted"], font=(FONT_UI, 8, "bold"),
                 anchor="w").pack(fill=tk.X, padx=2, pady=(12, 3))

    # ------------------------------------------------------------ refresh
    def refresh(self):
        for w in self.list_inner.winfo_children():
            w.destroy()
        if not self.workspace:
            self._say("No workspace open.")
            return
        self.current_lbl.config(text="◆ " + current_branch(self.workspace))
        locals_, remotes, tags = list_branches(self.workspace)
        subs = subjects_for(self.workspace, set())
        if not locals_ and not remotes:
            self._section("BRANCHES")
            tk.Label(self.list_inner,
                     text="No branches yet — create the first one above.",
                     bg=self.t["bg"], fg=self.t["text_muted"],
                     font=(FONT_UI, 9)).pack(anchor="w", padx=4, pady=6)
            return
        self._section("LOCAL")
        for b in sorted(locals_, key=lambda x: (not x["is_head"],
                                                x["name"])):
            self._branch_row(b, subs.get(b["short"], ""), local=True)
        if remotes:
            self._section("REMOTE")
            for b in sorted(remotes, key=lambda x: x["name"]):
                self._branch_row(b, subs.get(b["short"], ""), local=False)
        if tags:
            self._section(f"TAGS ({len(tags)})")
            row = tk.Frame(self.list_inner, bg=self.t["bg"])
            row.pack(fill=tk.X, padx=2)
            flow = tk.Frame(row, bg=self.t["bg"])
            flow.pack(fill=tk.X)
            for i, (name, sha) in enumerate(tags[:14]):
                chip = tk.Label(flow, text=f"⏕ {name}", bg=self.t["card"],
                                fg=self.t["text_secondary"],
                                font=(FONT_MONO, 8), padx=8, pady=3)
                chip.grid(row=i // 5, column=i % 5, sticky="w", padx=2,
                          pady=2)
                chip.bind("<Double-Button-1>",
                          lambda e, n=name: self.checkout(n))
                Tooltip(chip, f"{sha} — double-click to checkout")
        self._say(f"{len(locals_)} local · {len(remotes)} remote · "
                  f"{len(tags)} tags")

    # -------------------------------------------------------------- rows
    def _branch_row(self, b, subject, local=True):
        t = self.t
        row = tk.Frame(self.list_inner, bg=t["card"],
                       highlightthickness=1,
                       highlightbackground=t["card_border"])
        row.pack(fill=tk.X, pady=1)
        if b["is_head"]:
            mark = tk.Label(row, text="◆", bg=t["card"], fg=t.accent,
                            font=(FONT_UI, 10, "bold"))
            mark.pack(side=tk.LEFT, padx=(10, 0))
        name = tk.Label(row, text=b["name"], bg=t["card"],
                        fg=t["text"] if b["is_head"] else
                        t["text_secondary"],
                        font=(FONT_MONO, 10,
                              "bold" if b["is_head"] else "normal"),
                        cursor="hand2")
        name.pack(side=tk.LEFT, padx=6)
        name.bind("<Double-Button-1>",
                  lambda e, n=b["name"]: self.checkout(n))
        Tooltip(name, "double-click to checkout")
        tk.Label(row, text=b["short"], bg=t["card"],
                 fg=t["text_muted"], font=(FONT_MONO, 8)).pack(
            side=tk.LEFT, padx=6)
        if b["track"] and local:
            tk.Label(row, text=b["track"].strip("()"), bg=t["card"],
                     fg="#e3b341" if "ahead" in b["track"] else
                     ("#3fb950" if "behind" in b["track"] else
                      t["text_muted"]),
                     font=(FONT_MONO, 8, "bold")).pack(side=tk.LEFT,
                                                       padx=4)
        if subject:
            tk.Label(row, text=subject[:52], bg=t["card"],
                     fg=t["text_muted"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT, padx=8)
        actions = tk.Frame(row, bg=t["card"])
        actions.pack(side=tk.RIGHT, padx=6)
        if not b["is_head"]:
            self._act(actions, "checkout", lambda n=b["name"]:
                      self.checkout(n))
        if local:
            self._act(actions, "merge", lambda n=b["name"]:
                      self.merge(n))
            self._act(actions, "rename", lambda n=b["name"]:
                      self.rename(n))
            self._act(actions, "delete", lambda n=b["name"]:
                      self.delete(n), danger=True)
        else:
            self._act(actions, "track", lambda n=b["name"]:
                      self.track(n))

    def _act(self, parent, text, cmd, danger=False):
        t = self.t
        lbl = tk.Label(parent, text=text, bg=t["card"],
                       fg="#f85149" if danger else t.accent,
                       font=(FONT_UI, 8, "bold"), cursor="hand2", padx=7)
        lbl.pack(side=tk.LEFT, padx=2)
        lbl.bind("<Button-1>", lambda e: self._guarded(lbl, text, cmd))

    def _guarded(self, lbl, text, cmd):
        """Two-click confirm for dangerous actions."""
        if text != "delete":
            cmd()
            return
        if lbl.cget("text") == "sure?":
            lbl.config(text="delete")
            cmd()
            return
        lbl.config(text="sure?", fg="#ffffff", bg="#f85149")
        self.after(3000, lambda: self._revert(lbl))

    def _revert(self, lbl):
        try:
            if lbl.cget("text") == "sure?":
                lbl.config(text="delete", bg=self.t["card"],
                           fg="#f85149")
        except tk.TclError:
            pass

    # ----------------------------------------------------------- actions
    def create_branch(self):
        name = self.new_entry.get().strip()
        if not name or " " in name:
            self._say("Pick a branch name (no spaces).")
            return
        ok, _, err = run_git(self.workspace, "checkout", "-b", name)
        if ok:
            self.on_log(f"git checkout -b {name}")
            self._say(f"Created and switched to '{name}'")
            self.new_entry.delete(0, tk.END)
            self.refresh()
        else:
            self._say(f"failed: {err[:140]}")

    def checkout(self, name):
        ok, _, err = run_git(self.workspace, "checkout", name)
        if ok:
            self.on_log(f"git checkout {name}")
            self._say(f"On '{name}'")
            self.refresh()
        else:
            self._say(f"checkout failed: {err[:140]}")

    def track(self, remote_name):
        local = remote_name.split("/", 1)[1]
        ok, _, err = run_git(self.workspace, "checkout", "-b", local,
                             remote_name)
        if not ok:
            ok, _, err = run_git(self.workspace, "checkout", local)
        if ok:
            self.on_log(f"git track {remote_name} → {local}")
            self._say(f"Tracking '{remote_name}' as '{local}'")
            self.refresh()
        else:
            self._say(f"track failed: {err[:140]}")

    def merge(self, name):
        ok, out, err = run_git(self.workspace, "merge", "--no-ff", name)
        if ok:
            self.on_log(f"git merge --no-ff {name}")
            self._say(f"Merged '{name}' ✓")
            self.refresh()
        else:
            self._say(f"merge failed: {err[:160]}")

    def rename(self, name):
        win = tk.Toplevel(self)
        win.title(f"Rename {name}")
        win.configure(bg=self.t["bg"])
        win.transient(self)
        win.geometry("360x120")
        win.resizable(False, False)
        tk.Label(win, text=f"New name for '{name}'", bg=self.t["bg"],
                 fg=self.t["text"], font=(FONT_UI, 9)).pack(
            anchor="w", padx=14, pady=(12, 4))
        ent = tk.Entry(win, bg=self.t["editor"], fg=self.t["text"],
                       insertbackground=self.t["text"], relief=tk.FLAT,
                       font=(FONT_MONO, 10), highlightthickness=1,
                       highlightbackground=self.t["border"],
                       highlightcolor=self.t.accent)
        ent.pack(fill=tk.X, padx=14, ipady=5)
        ent.insert(0, name)
        ent.select_range(0, tk.END)

        def go(_e=None):
            new = ent.get().strip()
            if not new or new == name:
                win.destroy()
                return
            ok, _, err = run_git(self.workspace, "branch", "-m", name,
                                 new)
            win.destroy()
            if ok:
                self.on_log(f"git branch -m {name} {new}")
                self._say(f"Renamed to '{new}'")
                self.refresh()
            else:
                self._say(f"rename failed: {err[:140]}")
        ent.bind("<Return>", go)
        btn = tk.Label(win, text="Rename", bg=self.t.accent, fg="#ffffff",
                       font=(FONT_UI, 9, "bold"), cursor="hand2",
                       padx=12, pady=5)
        btn.pack(anchor="e", padx=14, pady=10)
        btn.bind("<Button-1>", go)
        ent.focus_set()

    def delete(self, name):
        if getattr(self, "_force", None) == name:
            ok, _, err = run_git(self.workspace, "branch", "-D", name)
            self._force = None
        else:
            ok, _, err = run_git(self.workspace, "branch", "-d", name)
            if not ok and "not fully merged" in (err or ""):
                self._force = name
                self._say(f"'{name}' has unmerged commits — "
                          f"click delete again to force.")
                return
        if ok:
            self.on_log(f"git branch -d {name}")
            self._say(f"Deleted '{name}'")
            self.refresh()
        else:
            self._force = None
            self._say(f"delete failed: {err[:140]}")


class Tooltip:
    """Minimal hover tooltip (same pattern as gitpanel._attach_tooltip)."""

    def __init__(self, widget, text):
        self.win = None
        self.widget = widget
        self.text = text
        widget.bind("<Enter>", self._enter)
        widget.bind("<Leave>", self._leave)

    def _enter(self, _e):
        if self.win is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() - 26
        self.win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, bg="#1c1926", fg="#c9c4d6",
                 font=(FONT_UI, 8), padx=8, pady=3,
                 highlightthickness=1,
                 highlightbackground="#3b3454").pack()

    def _leave(self, _e):
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None


def open_branches(parent, theme, workspace, on_log=None):
    """Convenience opener matching the studio's dialog style."""
    return BranchManager(parent, theme, workspace, on_log=on_log)
