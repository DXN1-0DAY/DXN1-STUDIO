"""DXN1 STUDIO — Project Hub.

The place the studio starts from: create a new workspace (Python script,
Flask web app, Tkinter app or empty folder) or jump back into a recent
one. The Hub keeps the wizard's cinematic dark look so it feels like part
of the onboarding family, whatever theme the IDE itself uses.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from . import APP_NAME, APP_VERSION, APP_CHANNEL
from .onboarding import load_scaled
from . import projects
from .theme import FONT_UI, FONT_MONO

HUB_W, HUB_H = 940, 660

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

C = {"overlay": "#0d1117", "text": "#e6edf3", "secondary": "#9aa7b8",
     "muted": "#6e7a8a", "card": "#131a22", "card_border": "#232c3d",
     "input_bg": "#11161d", "hover": "#1a212c", "success": "#3fb950"}


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
        self.err = tk.Label(row, text="", bg=C["overlay"], fg="#f85149",
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
        self.entry.bind("<Return>", lambda e: self.confirm())
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


class ProjectHub(tk.Toplevel):
    """Modal hub window — creation cards + recent workspaces."""

    def __init__(self, master, config, theme, on_open, on_explore):
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

        hero = load_scaled(os.path.join(ASSETS_DIR, "hub_hero.png"), 880, 190)
        if hero:
            self._imgrefs.append(hero)
            tk.Label(self, image=hero, bg=C["overlay"]).pack(pady=(14, 0))

        name = self.config.get("name") or "developer"
        tk.Label(self, text=f"Welcome, {name}. Where to?",
                 bg=C["overlay"], fg=C["text"], font=(FONT_UI, 20, "bold")
                 ).pack(anchor="w", padx=32, pady=(16, 2))
        tk.Label(self, text="Start something new or reopen a recent workspace — "
                            "everything stays optional and lightweight.",
                 bg=C["overlay"], fg=C["secondary"], font=(FONT_UI, 10)
                 ).pack(anchor="w", padx=32)

        tk.Label(self, text="START SOMETHING NEW", bg=C["overlay"],
                 fg=C["muted"], font=(FONT_UI, 9, "bold")
                 ).pack(anchor="w", padx=32, pady=(18, 6))
        cards = tk.Frame(self, bg=C["overlay"])
        cards.pack(anchor="w", padx=32)
        for i, kind in enumerate(projects.KIND_ORDER):
            self._new_card(cards, kind, i)

        tk.Label(self, text="RECENT WORKSPACES", bg=C["overlay"],
                 fg=C["muted"], font=(FONT_UI, 9, "bold")
                 ).pack(anchor="w", padx=32, pady=(18, 6))
        self.recents_box = tk.Frame(self, bg=C["overlay"])
        self.recents_box.pack(anchor="w", padx=32, fill=tk.X)
        self._refresh_recents()

        bottom = tk.Frame(self, bg=C["overlay"])
        bottom.pack(fill=tk.X, padx=32, pady=(14, 20))
        explore = tk.Label(bottom, text="Just explore the studio  →",
                           bg=C["overlay"], fg=self.accent,
                           font=(FONT_UI, 11, "bold"), cursor="hand2")
        explore.pack(side=tk.LEFT)
        explore.bind("<Button-1>", lambda e: self._finish_explore())
        tk.Label(bottom, text="Projects live wherever you want — DXN1 keeps track.",
                 bg=C["overlay"], fg=C["muted"], font=(FONT_UI, 9)
                 ).pack(side=tk.RIGHT)

    def _new_card(self, parent, kind, col):
        label, pitch, icon = projects.TEMPLATE_INFO[kind]
        card = tk.Frame(parent, bg=C["card"], highlightthickness=2,
                        highlightbackground=C["card_border"],
                        highlightcolor=self.accent, cursor="hand2")
        card.grid(row=0, column=col, padx=6, ipadx=4, ipady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1, uniform="hubcards")

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
            w.bind("<Enter>", lambda e, w=card: w.config(
                highlightbackground=self.accent))
            w.bind("<Leave>", lambda e, w=card: w.config(
                highlightbackground=C["card_border"]))

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
            tk.Label(row, text=label, bg=C["card"], fg=C["secondary"],
                     font=(FONT_UI, 8), padx=8).pack(side=tk.LEFT)
            open_lbl = tk.Label(row, text="Open  →", bg=C["card"], fg=self.accent,
                                font=(FONT_UI, 10, "bold"), cursor="hand2", padx=12)
            open_lbl.pack(side=tk.RIGHT)
            for w in (row, mid, open_lbl):
                w.bind("<Button-1>", lambda e, p=r["path"], k=r["kind"]:
                       self._finish_open(p, k))
                w.bind("<Enter>", lambda e: row.config(
                    highlightbackground=self.accent))
                w.bind("<Leave>", lambda e: row.config(
                    highlightbackground=C["card_border"]))

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
