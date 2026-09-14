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
from .i18n import tr

HUB_W, HUB_H = 940, 830

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

        hero = load_scaled(os.path.join(ASSETS_DIR, "hub_hero.png"), 880, 120)
        if hero:
            self._imgrefs.append(hero)
            tk.Label(self, image=hero, bg=C["overlay"]).pack(pady=(10, 0))

        name = self.config.get("name") or "developer"
        tk.Label(self, text=tr("hub.welcome", name=name),
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
            self._new_card(cards, kind, i % 4, i // 4)

        # DS2: full template gallery — search, categories, favourites,
        # plus the extra template pack that doesn't fit on these cards
        try:
            from .gallery import all_templates as _all_tpl
            n_tpl = len(_all_tpl())
        except Exception:  # noqa: BLE001
            n_tpl = 0
        if n_tpl:
            browse = tk.Label(
                self, text=f"or browse the full template gallery "
                           f"({n_tpl} templates, search + favourites)  →",
                bg=C["overlay"], fg=self.accent, font=(FONT_UI, 10, "bold"),
                cursor="hand2")
            browse.pack(anchor="w", padx=32, pady=(8, 0))
            browse.bind("<Button-1>", lambda e: self.open_gallery())

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
        # DS2: filter the recents list as you type
        filter_row = tk.Frame(self, bg=C["overlay"])
        filter_row.pack(anchor="w", padx=32, fill=tk.X, pady=(0, 6))
        self.filter_var = tk.StringVar()
        self._filter_entry = tk.Entry(filter_row,
                                      textvariable=self.filter_var,
                                      bg=C["input_bg"], fg=C["text"],
                                      insertbackground=C["text"],
                                      relief=tk.FLAT, font=(FONT_MONO, 9),
                                      highlightthickness=1,
                                      highlightbackground=C["card_border"],
                                      highlightcolor=self.accent)
        self._filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                                ipady=4)
        self._filter_entry.insert(0, "")
        self._filter_entry.bind("<KeyRelease>",
                                lambda e: self._refresh_recents())
        tk.Label(filter_row, text="⌕ type to filter", bg=C["overlay"],
                 fg=C["muted"], font=(FONT_UI, 8)).pack(side=tk.LEFT,
                                                        padx=(8, 0))
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
        # DS2 v2.6: transient status flash for hub actions (context menu)
        self.flash_lbl = tk.Label(bottom, text="", bg=C["overlay"],
                                  fg=C["secondary"], font=(FONT_UI, 8))
        self.flash_lbl.pack(side=tk.RIGHT, padx=(0, 14))
        clear = tk.Label(bottom, text="clear recents", bg=C["overlay"],
                         fg=C["muted"], font=(FONT_UI, 8, "underline"),
                         cursor="hand2")
        clear.pack(side=tk.RIGHT)
        clear.bind("<Button-1>", lambda e: self._clear_recents())

    def _card_shell(self, parent, col, row):
        card = tk.Frame(parent, bg=C["card"], highlightthickness=2,
                        highlightbackground=C["card_border"],
                        highlightcolor=self.accent, cursor="hand2",
                        height=96, width=200)
        card.grid_propagate(False)          # every card identical size
        card.grid(row=row, column=col, padx=6, ipadx=4, ipady=4,
                  sticky="nsew")
        parent.grid_columnconfigure(col, weight=1, uniform="hubcards")
        parent.grid_rowconfigure(row, weight=1)
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
                 ).pack(padx=12, pady=(9, 1), anchor="w")
        tk.Label(card, text=label, bg=C["card"], fg=C["text"],
                 font=(FONT_UI, 11, "bold"), wraplength=170,
                 justify=tk.LEFT).pack(padx=12, anchor="w")
        tk.Label(card, text=pitch, bg=C["card"], fg=C["secondary"],
                 font=(FONT_UI, 9), wraplength=180, justify=tk.LEFT
                 ).pack(padx=12, pady=(2, 9), anchor="w")
        for w in card.winfo_children():
            w.bind("<Button-1>", lambda e, k=kind: self.create_workspace(k))
        card.bind("<Button-1>", lambda e, k=kind: self.create_workspace(k))
        self._hover(card)

    def _action_card(self, parent, action, label, pitch, col):
        card = self._card_shell(parent, col, 0)
        icon = "⌂" if action == "open" else "⬇"
        tk.Label(card, text=icon, bg=C["card"], fg=self.accent,
                 font=(FONT_MONO, 9, "bold"), padx=6, pady=2
                 ).pack(padx=12, pady=(9, 1), anchor="w")
        tk.Label(card, text=label, bg=C["card"], fg=C["text"],
                 font=(FONT_UI, 11, "bold"), wraplength=170,
                 justify=tk.LEFT).pack(padx=12, anchor="w")
        tk.Label(card, text=pitch, bg=C["card"], fg=C["secondary"],
                 font=(FONT_UI, 9), wraplength=180, justify=tk.LEFT
                 ).pack(padx=12, pady=(2, 9), anchor="w")
        cmd = self.open_existing if action == "open" else self.open_clone
        for w in card.winfo_children():
            w.bind("<Button-1>", lambda e, c=cmd: c())
        card.bind("<Button-1>", lambda e, c=cmd: c())
        self._hover(card)

    def _refresh_recents(self):
        for w in self.recents_box.winfo_children():
            w.destroy()
        recents = projects.list_recent(self.config)
        # DS2: pinned workspaces float to the top
        pinned = self.config.get("pinned_projects") or []
        recents.sort(key=lambda r: (r.get("path") not in pinned,))
        needle = ""
        try:
            needle = self.filter_var.get().strip().lower()
        except (AttributeError, tk.TclError):
            pass
        if needle:
            recents = [r for r in recents
                       if needle in r.get("name", "").lower()
                       or needle in r.get("path", "").lower()]
        if not recents:
            msg = ("No workspaces yet — your new projects will show up here."
                   if not needle else
                   f"Nothing matches '{needle}'.")
            tk.Label(self.recents_box,
                     text=msg,
                     bg=C["overlay"], fg=C["muted"], font=(FONT_UI, 9)
                     ).pack(anchor="w", pady=(0, 2))
            return
        # DS2: live workspace stats — computed once per refresh, capped
        stats_map = {}
        if len(recents) <= 8:
            try:
                from .workspace_stats import stats_for
                for r in recents:
                    stats_map[r.get("path", "")] = stats_for(
                        r.get("path", ""))
            except Exception:
                stats_map = {}
        # DS2 v2.6: aggregate "at a glance" strip above the rows
        self._refresh_insights(list(stats_map.values()), len(recents))
        # DS2 v2.6: per-row current-branch chips (best effort, capped)
        branch_map = {}
        try:
            from .workspace_stats import current_branch
            for r in recents[:8]:
                branch_map[r.get("path", "")] = current_branch(
                    r.get("path", ""))
        except Exception:
            branch_map = {}
        for r in recents:
            self._recent_row(r, stats_map.get(r.get("path", ""), {}),
                             r.get("path") in pinned,
                             branch_map.get(r.get("path", ""), ""))

    def _refresh_insights(self, stats_list, total_workspaces):
        """DS2 v2.6: one-line aggregate strip above the recents rows.

        Shows the sum of what you keep: workspaces, files, lines and
        the dominant languages across everything the hub tracks.
        Fully defensive — a stats failure just means no strip.
        """
        try:
            old = getattr(self, "insights_row", None)
            if old is not None and old.winfo_exists():
                old.destroy()
        except Exception:  # noqa: BLE001
            pass
        try:
            from .workspace_stats import aggregate_insights, aggregate_line
            line = aggregate_line(aggregate_insights(stats_list))
        except Exception:  # noqa: BLE001
            return
        if not line:
            return
        extra = total_workspaces - len(stats_list)
        if extra > 0:
            line += f"  ·  +{extra} more"
        self.insights_row = tk.Frame(self.recents_box, bg=C["overlay"])
        tk.Label(self.insights_row, text="Σ", bg=C["overlay"],
                 fg=self.accent, font=(FONT_UI, 11, "bold")
                 ).pack(side=tk.LEFT)
        tk.Label(self.insights_row, text="  at a glance:  " + line,
                 bg=C["overlay"], fg=C["muted"], font=(FONT_UI, 8)
                 ).pack(side=tk.LEFT)
        self.insights_row.pack(anchor="w", pady=(0, 4))

    def _recent_row(self, r, stats, is_pinned, branch=""):
        """DS2: one recent card — richer info line, pin + remove actions."""
        row = tk.Frame(self.recents_box, bg=C["card"], highlightthickness=1,
                       highlightbackground=self.accent if is_pinned
                       else C["card_border"])
        row.pack(fill=tk.X, pady=3, ipady=5)
        label, _, icon = projects.TEMPLATE_INFO.get(
            r["kind"], ("Workspace", "", "◻"))
        tk.Label(row, text=icon, bg=C["card"], fg=self.accent,
                 font=(FONT_MONO, 8, "bold"), padx=6, pady=2
                 ).pack(side=tk.LEFT, padx=(12, 4))
        mid = tk.Frame(row, bg=C["card"])
        mid.pack(side=tk.LEFT, fill=tk.X, expand=True)
        name_row = tk.Frame(mid, bg=C["card"])
        name_row.pack(anchor="w")
        tk.Label(name_row, text=r["name"], bg=C["card"], fg=C["text"],
                 font=(FONT_UI, 10, "bold"), anchor="w").pack(side=tk.LEFT)
        if is_pinned:
            tk.Label(name_row, text="  ⚑ pinned", bg=C["card"],
                     fg=self.accent, font=(FONT_UI, 7, "bold")
                     ).pack(side=tk.LEFT)
        info = r["path"]
        if stats:
            try:
                from .workspace_stats import summary_line
                line = summary_line(stats)
                if line:
                    info = f"{r['path']}   ·   {line}"
            except Exception:
                pass
        tk.Label(mid, text=info, bg=C["card"], fg=C["muted"],
                 font=(FONT_UI, 8), anchor="w").pack(anchor="w")
        tk.Label(row, text=rel_time(r.get("opened", "")),
                 bg=C["card"], fg=C["muted"], font=(FONT_UI, 8),
                 padx=6).pack(side=tk.LEFT)
        if branch:   # DS2 v2.6: current git branch chip
            tk.Label(row, text=f"⎇ {branch}", bg=C["card"],
                     fg=self.accent, font=(FONT_MONO, 7, "bold"),
                     padx=5, pady=1).pack(side=tk.LEFT)
        tk.Label(row, text=label, bg=C["card"], fg=C["secondary"],
                 font=(FONT_UI, 8), padx=6).pack(side=tk.LEFT)
        pin_lbl = tk.Label(row, text="⚑" if is_pinned else "⚐",
                           bg=C["card"],
                           fg=self.accent if is_pinned else C["muted"],
                           font=(FONT_UI, 11), cursor="hand2", padx=8)
        pin_lbl.pack(side=tk.RIGHT)
        pin_lbl.bind("<Button-1>", lambda e, p=r["path"]:
                     self._toggle_pin(p))
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
        # DS2 v2.6: right-click context menu on the card
        for w in (row, mid):
            w.bind("<Button-3>", lambda e, p=r["path"], k=r["kind"]:
                   self._recent_menu(e, p, k))

    # ------------------------------------------------ DS2 v2.6 hub actions
    def _recent_menu(self, event, path, kind):
        """Right-click actions for a recent workspace card."""
        try:
            is_pinned = path in (self.config.get("pinned_projects") or [])
            menu = tk.Menu(self, tearoff=0, bg=C["card"], fg=C["text"],
                           activebackground=self.accent,
                           activeforeground="#ffffff",
                           font=(FONT_UI, 9))
            menu.add_command(label="Open workspace",
                             command=lambda: self._finish_open(path, kind))
            menu.add_command(label="Reveal in file manager",
                             command=lambda: self._reveal(path))
            menu.add_command(label="Open terminal here",
                             command=lambda: self._open_terminal(path))
            menu.add_command(label="Copy path",
                             command=lambda: self._copy_path(path))
            menu.add_separator()
            menu.add_command(label="Snapshot now (zip backup)",
                             command=lambda: self._snapshot(path))
            menu.add_separator()
            menu.add_command(label="⚐ Unpin" if is_pinned else "⚑ Pin",
                             command=lambda: self._toggle_pin(path))
            menu.add_command(label="✕ Remove from list",
                             command=lambda: self._remove_recent(path))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        except Exception:  # noqa: BLE001 — a menu must never crash the hub
            pass
        return "break"

    def _reveal(self, path):
        import subprocess
        try:
            subprocess.Popen(["xdg-open", path],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            self._hub_flash("Revealed in file manager")
        except Exception:  # noqa: BLE001
            self._hub_flash("No file manager available")

    def _open_terminal(self, path):
        import subprocess
        for term in ("x-terminal-emulator", "gnome-terminal", "konsole",
                     "xfce4-terminal", "xterm"):
            try:
                subprocess.Popen([term, "--working-directory", path],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                self._hub_flash(f"Opened {term}")
                return
            except FileNotFoundError:
                continue
            except Exception:  # noqa: BLE001
                break
        self._hub_flash("No terminal emulator found")

    def _copy_path(self, path):
        try:
            self.clipboard_clear()
            self.clipboard_append(path)
            self._hub_flash("Path copied to clipboard")
        except Exception:  # noqa: BLE001
            pass

    def _snapshot(self, path):
        """Zip-backup a workspace straight from the hub (backup engine)."""
        try:
            from .backup import create_snapshot
            snap_path, stats = create_snapshot(path, label="hub")
            self._hub_flash(
                f"Snapshot created — {stats.get('zipped', 0)} files")
        except Exception as exc:  # noqa: BLE001
            self._hub_flash(f"Snapshot failed: {exc}")

    def _hub_flash(self, msg):
        """Tiny status flash in the hub's bottom bar (auto-clears 4 s)."""
        try:
            lbl = getattr(self, "flash_lbl", None)
            if lbl is None:
                return
            lbl.config(text=msg)
            after_id = getattr(self, "_flash_after", None)
            if after_id:
                try:
                    self.after_cancel(after_id)
                except Exception:  # noqa: BLE001
                    pass
            self._flash_after = self.after(
                4000, lambda: self._flash_clear(lbl))
        except Exception:  # noqa: BLE001
            pass

    def _flash_clear(self, lbl):
        try:
            lbl.config(text="")
        except Exception:  # noqa: BLE001
            pass

    def _toggle_pin(self, path):
        pinned = list(self.config.get("pinned_projects") or [])
        if path in pinned:
            pinned.remove(path)
            self.on_log_pin("unpinned")
        else:
            pinned.insert(0, path)
            self.on_log_pin("pinned")
        self.config.set("pinned_projects", pinned)
        self._refresh_recents()

    def on_log_pin(self, verb):
        pass  # hook for the studio log; hub usually has no logger

    def _remove_recent(self, path):
        recents = [r for r in (self.config.get("recent_projects") or [])
                   if r.get("path") != path]
        self.config.set("recent_projects", recents)
        self._refresh_recents()

    def _clear_recents(self):
        projects.clear_recent(self.config)
        self._refresh_recents()

    def open_gallery(self):
        """DS2: browsable template gallery (search / categories / stars)."""
        try:
            from .gallery import open_gallery as _open
            self._gallery = _open(self, self.config, self.accent,
                                  on_pick=self.create_workspace)
        except Exception as exc:  # noqa: BLE001 — gallery is optional
            messagebox.showinfo("Template Gallery",
                                f"Gallery unavailable: {exc}")

    # ----------------------------------------------------------------- flow
    def _template_label(self, kind):
        """Human label for any template kind, DS2 extras included."""
        info = projects.TEMPLATE_INFO.get(kind)
        if info:
            return info[0]
        try:
            from .gallery import all_templates
            return all_templates().get(kind, ("Workspace",))[0]
        except Exception:  # noqa: BLE001 — labels must never break the flow
            return "Workspace"

    def create_workspace(self, kind):
        dlg = NameDialog(self, self.accent,
                         title=f"New {self._template_label(kind)}")
        self.wait_window(dlg)
        if not dlg.value:
            return
        parent = filedialog.askdirectory(
            title="Where should it live?", initialdir=projects.ensure_projects_root())
        # user closed the picker -> default to ~/DXN1 instead of aborting
        parent = parent or projects.DEFAULT_PROJECTS_ROOT
        try:
            # DS2: gallery.scaffold_any covers built-ins AND the extra
            # template pack (data / scraper / bot / tests / todo)
            try:
                from .gallery import scaffold_any
                path, real_kind = scaffold_any(kind, parent, dlg.value)
            except ImportError:
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
