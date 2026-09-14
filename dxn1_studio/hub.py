"""DXN1 STUDIO — Project Hub.

The place the studio starts from: create a new workspace (Python script,
Flask web app, Tkinter app or empty folder), open an existing folder,
clone straight from GitHub, or jump back into a recent one. The Hub keeps
the wizard's cinematic dark look so it feels like part of the onboarding
family, whatever theme the IDE itself uses.
"""

import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from . import APP_NAME, APP_VERSION, APP_CHANNEL
from .onboarding import load_scaled
from . import projects
from .theme import FONT_UI, FONT_MONO

HUB_W, HUB_H = 940, 720

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

C = {"overlay": "#0d1117", "text": "#e6edf3", "secondary": "#9aa7b8",
     "muted": "#6e7a8a", "card": "#131a22", "card_border": "#232c3d",
     "input_bg": "#11161d", "hover": "#1a212c", "success": "#3fb950",
     "error": "#f85149"}


def rel_time(stamp):
    """'2026-09-14 10:30' -> '2h ago' style label (best effort)."""
    if not stamp:
        return ""
    try:
        then = time.mktime(time.strptime(stamp[:16], "%Y-%m-%d %H:%M"))
        delta = max(0, time.time() - then)
    except (ValueError, OverflowError):
        return stamp
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    if delta < 86400 * 30:
        return f"{int(delta // 86400)}d ago"
    return stamp[:10]


class NameDialog(tk.Toplevel):
    """Small modal asking for a workspace name (validated on the fly)."""

    def __init__(self, master, accent, title="Name your workspace"):
        super().__init__(master)
        self.accent = accent
        self.value = None
        self.configure(bg=C["overlay"])
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        box = tk.Frame(self, bg=C["overlay"])
        box.pack(padx=30, pady=24)
        tk.Label(box, text=title, bg=C["overlay"], fg=C["text"],
                 font=(FONT_UI, 14, "bold")).pack(anchor="w")
        tk.Label(box, text="Letters, numbers and dashes. You can rename the folder later.",
                 bg=C["overlay"], fg=C["muted"], font=(FONT_UI, 9)
                 ).pack(anchor="w", pady=(2, 12))

        self.entry = tk.Entry(box, width=32, bg=C["input_bg"], fg=C["text"],
                              insertbackground=C["text"], relief=tk.FLAT,
                              font=(FONT_UI, 12), highlightthickness=1,
                              highlightbackground=C["card_border"],
                              highlightcolor=accent)
        self.entry.pack(ipady=8)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.confirm())
        self.entry.bind("<KeyRelease>", self._validate_live)

        row = tk.Frame(box, bg=C["overlay"])
        row.pack(pady=(14, 0), fill=tk.X)
        self.err = tk.Label(row, text="", bg=C["overlay"], fg=C["error"],
                            font=(FONT_UI, 9))
        self.err.pack(side=tk.LEFT)

        cancel = tk.Label(row, text="Cancel", bg=C["overlay"], fg=C["secondary"],
                          font=(FONT_UI, 10), cursor="hand2", padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: self.destroy())
        self.ok_btn = tk.Label(row, text="Create  ✦", bg=accent, fg="#ffffff",
                               font=(FONT_UI, 10, "bold"), cursor="hand2",
                               padx=16, pady=6)
        self.ok_btn.pack(side=tk.RIGHT)
        self.ok_btn.bind("<Button-1>", lambda e: self.confirm())

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        mx = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        my = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 3
        self.geometry(f"+{max(0, mx)}+{max(0, my)}")

    def _validate_live(self, event=None):
        if self.value is not None:
            return  # dialog already closing
        if len(self.entry.get()) > 48:
            self.err.config(text="Keep it under 48 characters")

    def confirm(self):
        name = self.entry.get().strip()
        if not name:
            self.err.config(text="Give it a name first")
            return
        if len(name) > 48:
            self.err.config(text="Keep it under 48 characters")
            return
        self.value = name
        self.grab_release()
        self.destroy()


class GitHubCloneDialog(tk.Toplevel):
    """In-app clone flow: paste a GitHub URL, watch git output live."""

    def __init__(self, master, accent, on_cloned):
        super().__init__(master)
        self.accent = accent
        self.on_cloned = on_cloned        # fn(path)
        self.configure(bg=C["overlay"])
        self.title("Clone from GitHub")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self._proc = None

        box = tk.Frame(self, bg=C["overlay"])
        box.pack(padx=28, pady=22)
        tk.Label(box, text="Clone from GitHub", bg=C["overlay"], fg=C["text"],
                 font=(FONT_UI, 14, "bold")).pack(anchor="w")
        tk.Label(box, text="Paste a repo URL (https://github.com/owner/repo)\n"
                           "or just owner/repo — it lands in your DXN1 folder.",
                 bg=C["overlay"], fg=C["muted"], font=(FONT_UI, 9),
                 justify=tk.LEFT).pack(anchor="w", pady=(2, 10))

        self.entry = tk.Entry(box, width=42, bg=C["input_bg"], fg=C["text"],
                              insertbackground=C["text"], relief=tk.FLAT,
                              font=(FONT_MONO, 11), highlightthickness=1,
                              highlightbackground=C["card_border"],
                              highlightcolor=accent)
        self.entry.pack(ipady=8)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.start())

        self.log = tk.Text(box, height=6, width=52, bg=C["input_bg"],
                           fg=C["secondary"], font=(FONT_MONO, 8),
                           state="disabled", relief=tk.FLAT, bd=0,
                           highlightthickness=1,
                           highlightbackground=C["card_border"])
        self.log.pack(pady=(10, 0), fill=tk.X)

        row = tk.Frame(box, bg=C["overlay"])
        row.pack(pady=(12, 0), fill=tk.X)
        self.err = tk.Label(row, text="", bg=C["overlay"], fg=C["error"],
                            font=(FONT_UI, 9), wraplength=280, justify=tk.LEFT)
        self.err.pack(side=tk.LEFT)

        cancel = tk.Label(row, text="Close", bg=C["overlay"], fg=C["secondary"],
                          font=(FONT_UI, 10), cursor="hand2", padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: self.destroy())
        self.go_btn = tk.Label(row, text="Clone  ⬇", bg=accent, fg="#ffffff",
                               font=(FONT_UI, 10, "bold"), cursor="hand2",
                               padx=16, pady=6)
        self.go_btn.pack(side=tk.RIGHT)
        self.go_btn.bind("<Button-1>", lambda e: self.start())

        self.bind("<Escape>", lambda e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        mx = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        my = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 3
        self.geometry(f"+{max(0, mx)}+{max(0, my)}")

    def _say(self, text):
        self.log.config(state="normal")
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.config(state="disabled")

    def start(self):
        raw = self.entry.get().strip()
        if not raw:
            self.err.config(text="Paste a repo URL first.")
            return
        url = raw
        if not raw.startswith(("http://", "https://", "git@")):
            if re_ok := _REPO_RE.fullmatch(raw):
                url = f"https://github.com/{raw}.git"
            else:
                self.err.config(text="That doesn't look like a GitHub repo.")
                return
        if not _which_git():
            self.err.config(text="git isn't installed — install git, then "
                                 "retry (or use “Open folder” for local work).")
            return
        name = url.rstrip("/").removesuffix(".git").split("/")[-1] or "repo"
        dest = os.path.join(projects.ensure_projects_root(), name)
        if os.path.exists(dest):
            self.err.config(text=f"“{name}” already exists locally — open it "
                                 f"from Recents or remove that folder first.")
            return
        self.err.config(text="")
        self.go_btn.config(text="cloning…", cursor="watch")

        def work():
            try:
                proc = subprocess.Popen(
                    ["git", "clone", "--depth", "1", url, dest],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
                self._proc = proc
                for line in proc.stdout:
                    self.after(0, lambda l=line.rstrip(): self._say(l + "\n"))
                code = proc.wait()
                self.after(0, lambda: self._finish(code, dest))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._fail(str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _finish(self, code, dest):
        self.go_btn.config(text="Clone  ⬇", cursor="hand2")
        if code == 0:
            self._say("✓ done\n")
            self.grab_release()
            self.destroy()
            self.on_cloned(dest)
        else:
            self.err.config(text=f"git exited with code {code} — is the repo "
                                 f"public? (private repos need your git login)")

    def _fail(self, message):
        self.go_btn.config(text="Clone  ⬇", cursor="hand2")
        self.err.config(text=f"clone failed: {message}")


def _which_git():
    from shutil import which
    return which("git")


_REPO_RE = __import__("re").compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


class ProjectHub(tk.Toplevel):
    """Modal hub window — creation cards + recent workspaces."""

    def __init__(self, master, config, theme, on_open, on_explore,
                 preselect_kind=None):
        super().__init__(master)
        self.config = config
        self.theme = theme
        self.accent = theme.accent
        self.on_open = on_open          # fn(path, kind)
        self.on_explore = on_explore    # fn()
        self._imgrefs = []
        self.closed = False

        self.title(f"{APP_NAME} — Project Hub")
        self.configure(bg=C["overlay"])
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._finish_explore)

        self._build()
        self._center()
        # the main window is hidden while the hub owns the boot flow —
        # explicitly map, or the Toplevel never appears on X11.
        self.deiconify()
        if preselect_kind:
            self.after(450, lambda k=preselect_kind:
                       self.create_workspace(k))

    # ------------------------------------------------------------------ ui
    def _build(self):
        top = tk.Frame(self, bg=C["overlay"])
        top.pack(fill=tk.X, padx=28, pady=(18, 0))
        logo = load_scaled(os.path.join(ASSETS_DIR, "logo.png"), 28, 28)
        if logo:
            self._imgrefs.append(logo)
            tk.Label(top, image=logo, bg=C["overlay"]).pack(side=tk.LEFT)
        tk.Label(top, text=f"{APP_NAME} — Project Hub", bg=C["overlay"],
                 fg=C["text"], font=(FONT_UI, 12, "bold")
                 ).pack(side=tk.LEFT, padx=(10, 8))
        tk.Label(top, text=f"v{APP_VERSION} · {APP_CHANNEL.upper()}",
                 bg=C["card"], fg=C["secondary"], font=(FONT_UI, 8),
                 padx=8, pady=2).pack(side=tk.LEFT, pady=2)

        close = tk.Label(top, text="✕", bg=C["overlay"], fg=C["muted"],
                         font=(FONT_UI, 12, "bold"), cursor="hand2")
        close.pack(side=tk.RIGHT)
        close.bind("<Button-1>", lambda e: self._finish_explore())

        hero = load_scaled(os.path.join(ASSETS_DIR, "hub_hero.png"), 880, 170)
        if hero:
            self._imgrefs.append(hero)
            tk.Label(self, image=hero, bg=C["overlay"]).pack(pady=(12, 0))

        name = self.config.get("name") or "developer"
        tk.Label(self, text=f"Welcome back, {name}. Where to?",
                 bg=C["overlay"], fg=C["text"], font=(FONT_UI, 20, "bold")
                 ).pack(anchor="w", padx=32, pady=(14, 2))
        tk.Label(self, text="Start something new, bring an existing folder, "
                            "clone from GitHub — or reopen a recent workspace.",
                 bg=C["overlay"], fg=C["secondary"], font=(FONT_UI, 10)
                 ).pack(anchor="w", padx=32)

        tk.Label(self, text="START SOMETHING NEW", bg=C["overlay"],
                 fg=C["muted"], font=(FONT_UI, 9, "bold")
                 ).pack(anchor="w", padx=32, pady=(14, 6))
        cards = tk.Frame(self, bg=C["overlay"])
        cards.pack(anchor="w", padx=32)
        for i, kind in enumerate(projects.KIND_ORDER):
            self._new_card(cards, kind, i % 4, 0)

        actions = tk.Frame(self, bg=C["overlay"])
        actions.pack(anchor="w", padx=32, pady=(8, 0))
        self._action_card(actions, "open", "Open existing folder",
                          "Work on any folder on this machine — it becomes a "
                          "tracked workspace instantly.", 0)
        self._action_card(actions, "clone", "Clone from GitHub",
                          "Paste a repo URL; the studio clones it with git "
                          "and opens it as a workspace.", 1)

        tk.Label(self, text="RECENT WORKSPACES", bg=C["overlay"],
                 fg=C["muted"], font=(FONT_UI, 9, "bold")
                 ).pack(anchor="w", padx=32, pady=(14, 6))
        self.recents_box = tk.Frame(self, bg=C["overlay"])
        self.recents_box.pack(anchor="w", padx=32, fill=tk.X)
        self._refresh_recents()

        bottom = tk.Frame(self, bg=C["overlay"])
        bottom.pack(fill=tk.X, padx=32, pady=(12, 18))
        explore = tk.Label(bottom, text="Just explore the studio  →",
                           bg=C["overlay"], fg=self.accent,
                           font=(FONT_UI, 11, "bold"), cursor="hand2")
        explore.pack(side=tk.LEFT)
        explore.bind("<Button-1>", lambda e: self._finish_explore())
        clear = tk.Label(bottom, text="clear recents", bg=C["overlay"],
                         fg=C["muted"], font=(FONT_UI, 8, "underline"),
                         cursor="hand2")
        clear.pack(side=tk.RIGHT)
        clear.bind("<Button-1>", lambda e: self._clear_recents())

    def _card_shell(self, parent, col, row):
        card = tk.Frame(parent, bg=C["card"], highlightthickness=2,
                        highlightbackground=C["card_border"],
                        highlightcolor=self.accent, cursor="hand2")
        card.grid(row=row, column=col, padx=6, ipadx=4, ipady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1, uniform="hubcards")
        return card

    def _hover(self, card):
        card.bind("<Enter>", lambda e: card.config(
            highlightbackground=self.accent))
        card.bind("<Leave>", lambda e: card.config(
            highlightbackground=C["card_border"]))

    def _new_card(self, parent, kind, col, row):
        label, pitch, icon = projects.TEMPLATE_INFO[kind]
        card = self._card_shell(parent, col, row)
        tk.Label(card, text=icon, bg=C["card"], fg=self.accent,
                 font=(FONT_MONO, 9, "bold"), padx=6, pady=2
                 ).pack(padx=12, pady=(12, 2), anchor="w")
        tk.Label(card, text=label, bg=C["card"], fg=C["text"],
                 font=(FONT_UI, 11, "bold"), wraplength=170,
                 justify=tk.LEFT).pack(padx=12, anchor="w")
        tk.Label(card, text=pitch, bg=C["card"], fg=C["secondary"],
                 font=(FONT_UI, 9), wraplength=170, justify=tk.LEFT
                 ).pack(padx=12, pady=(3, 12), anchor="w")
        for w in card.winfo_children():
            w.bind("<Button-1>", lambda e, k=kind: self.create_workspace(k))
        self._hover(card)

    def _action_card(self, parent, action, label, pitch, col):
        card = self._card_shell(parent, col, 0)
        icon = "⌂" if action == "open" else "⬇"
        tk.Label(card, text=icon, bg=C["card"], fg=self.accent,
                 font=(FONT_MONO, 9, "bold"), padx=6, pady=2
                 ).pack(padx=12, pady=(12, 2), anchor="w")
        tk.Label(card, text=label, bg=C["card"], fg=C["text"],
                 font=(FONT_UI, 11, "bold"), wraplength=170,
                 justify=tk.LEFT).pack(padx=12, anchor="w")
        tk.Label(card, text=pitch, bg=C["card"], fg=C["secondary"],
                 font=(FONT_UI, 9), wraplength=170, justify=tk.LEFT
                 ).pack(padx=12, pady=(3, 12), anchor="w")
        cmd = self.open_existing if action == "open" else self.open_clone
        for w in card.winfo_children():
            w.bind("<Button-1>", lambda e, c=cmd: c())
        self._hover(card)

    def _refresh_recents(self):
        for w in self.recents_box.winfo_children():
            w.destroy()
        recents = projects.list_recent(self.config)
        if not recents:
            tk.Label(self.recents_box,
                     text="No workspaces yet — your new projects will show up here.",
                     bg=C["overlay"], fg=C["muted"], font=(FONT_UI, 9)
                     ).pack(anchor="w", pady=(0, 2))
            return
        for r in recents:
            row = tk.Frame(self.recents_box, bg=C["card"], highlightthickness=1,
                           highlightbackground=C["card_border"])
            row.pack(fill=tk.X, pady=3, ipady=5)
            label, _, icon = projects.TEMPLATE_INFO.get(
                r["kind"], ("Workspace", "", "◻"))
            tk.Label(row, text=icon, bg=C["card"], fg=self.accent,
                     font=(FONT_MONO, 8, "bold"), padx=6, pady=2
                     ).pack(side=tk.LEFT, padx=(12, 4))
            mid = tk.Frame(row, bg=C["card"])
            mid.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(mid, text=r["name"], bg=C["card"], fg=C["text"],
                     font=(FONT_UI, 10, "bold"), anchor="w").pack(anchor="w")
            tk.Label(mid, text=r["path"], bg=C["card"], fg=C["muted"],
                     font=(FONT_UI, 8), anchor="w").pack(anchor="w")
            tk.Label(row, text=rel_time(r.get("opened", "")),
                     bg=C["card"], fg=C["muted"], font=(FONT_UI, 8),
                     padx=6).pack(side=tk.LEFT)
            tk.Label(row, text=label, bg=C["card"], fg=C["secondary"],
                     font=(FONT_UI, 8), padx=6).pack(side=tk.LEFT)
            remove = tk.Label(row, text="✕", bg=C["card"], fg=C["muted"],
                              font=(FONT_UI, 9), cursor="hand2", padx=8)
            remove.pack(side=tk.RIGHT)
            remove.bind("<Button-1>", lambda e, p=r["path"]:
                        self._remove_recent(p))
            open_lbl = tk.Label(row, text="Open  →", bg=C["card"],
                                fg=self.accent,
                                font=(FONT_UI, 10, "bold"), cursor="hand2",
                                padx=12)
            open_lbl.pack(side=tk.RIGHT)
            for w in (row, mid, open_lbl):
                w.bind("<Button-1>", lambda e, p=r["path"], k=r["kind"]:
                       self._finish_open(p, k))
                w.bind("<Enter>", lambda e: row.config(
                    highlightbackground=self.accent))
                w.bind("<Leave>", lambda e: row.config(
                    highlightbackground=C["card_border"]))

    def _remove_recent(self, path):
        recents = [r for r in (self.config.get("recent_projects") or [])
                   if r.get("path") != path]
        self.config.set("recent_projects", recents)
        self._refresh_recents()

    def _clear_recents(self):
        projects.clear_recent(self.config)
        self._refresh_recents()

    # ----------------------------------------------------------------- flow
    def create_workspace(self, kind):
        dlg = NameDialog(self, self.accent,
                         title=f"New {projects.TEMPLATE_INFO[kind][0]}")
        self.wait_window(dlg)
        if not dlg.value:
            return
        parent = filedialog.askdirectory(
            title="Where should it live?", initialdir=projects.ensure_projects_root())
        # user closed the picker -> default to ~/DXN1 instead of aborting
        parent = parent or projects.DEFAULT_PROJECTS_ROOT
        try:
            path, real_kind = projects.scaffold(kind, parent, dlg.value)
        except OSError as exc:
            messagebox.showerror("Project Hub",
                                 f"Could not create the workspace:\n{exc}")
            return
        self._finish_open(path, real_kind)

    def open_existing(self):
        path = filedialog.askdirectory(title="Open an existing folder")
        if not path:
            return
        meta = projects.read_project_meta(path)
        self._finish_open(path, meta["kind"])

    def open_clone(self):
        dlg = GitHubCloneDialog(self, self.accent,
                                on_cloned=lambda p: self._finish_open(
                                    p, projects.read_project_meta(p)["kind"]))
        self.wait_window(dlg)

    def _finish_open(self, path, kind):
        if self.closed:
            return
        self.closed = True
        self._teardown()
        self.on_open(path, kind)

    def _finish_explore(self):
        if self.closed:
            return
        self.closed = True
        self._teardown()
        self.on_explore()

    def _teardown(self):
        try:
            self.grab_release()
            self.destroy()
        except tk.TclError:
            pass

    def _center(self):
        self.update_idletasks()
        self.geometry(f"{HUB_W}x{HUB_H}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{HUB_W}x{HUB_H}+{(sw - HUB_W) // 2}+{max(20, (sh - HUB_H) // 2 - 20)}")
