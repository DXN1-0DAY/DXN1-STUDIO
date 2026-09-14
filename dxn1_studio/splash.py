"""DXN1 STUDIO — boot splash.

The studio opens with a small borderless logo window (the "boot card")
for about two seconds, then hands over to the main window / Project Hub.
Run ``dxn1 studio`` in any terminal to see it in action. Disable it in
Settings ("Show boot splash") or with ``--no-splash``.
"""

import os
import tkinter as tk

from . import APP_NAME, APP_VERSION, APP_CHANNEL
from .onboarding import load_scaled

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

DARK_BG = "#0d1117"
TEXT = "#e6edf3"
MUTED = "#6e7a8a"
CARD_BORDER = "#232c3d"


class Splash:
    """Borderless logo card shown while the studio warms up."""

    def __init__(self, root, accent="#7c3aed", duration_ms=2000, on_done=None):
        self.root = root
        self.accent = accent
        self.on_done = on_done
        self.closed = False

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=DARK_BG)

        w, h = 300, 320
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        self.win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2 - 40}")

        outer = tk.Frame(self.win, bg=self.accent)
        outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner = tk.Frame(outer, bg=DARK_BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        logo = load_scaled(os.path.join(ASSETS_DIR, "logo.png"), 128, 128)
        if logo:
            self._ref = logo  # keep a reference alive
            tk.Label(inner, image=logo, bg=DARK_BG).pack(pady=(44, 0))
        else:  # geometric fallback when assets/PIL are missing
            c = tk.Canvas(inner, width=120, height=120, bg=DARK_BG,
                          highlightthickness=0)
            c.pack(pady=(44, 0))
            c.create_polygon(60, 18, 98, 60, 60, 102, 22, 60,
                             fill=self.accent, outline="")

        tk.Label(inner, text=APP_NAME, bg=DARK_BG, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(pady=(14, 0))
        tk.Label(inner, text=f"v{APP_VERSION} · {APP_CHANNEL.upper()}",
                 bg=DARK_BG, fg=MUTED, font=("Segoe UI", 9)).pack()

        self.status = tk.Label(inner, text="warming up", bg=DARK_BG, fg=MUTED,
                               font=("Segoe UI", 9))
        self.status.pack(side=tk.BOTTOM, pady=16)

        self._dots = 0
        self._tick()
        self.win.deiconify()   # master may be hidden during boot — map anyway
        self.win.bind("<Button-1>", lambda e: self.close())
        self.root.after(duration_ms, self.close)

    def _tick(self):
        if self.closed:
            return
        try:
            self._dots = (self._dots + 1) % 4
            self.status.config(text="warming up" + "." * self._dots)
            self.root.after(280, self._tick)
        except tk.TclError:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.win.grab_release()
            self.win.destroy()
        except tk.TclError:
            pass
        if self.on_done is not None:
            self.on_done()
