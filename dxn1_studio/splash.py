"""DXN1 STUDIO — boot splash, remade for v1.1.3.

A borderless, centred card: baked brand artwork (logo card, wordmark,
tagline, version chip) with live animation on top —

* fade-in / fade-out (window ``-alpha`` where supported)
* an indeterminate shimmer progress bar
* a rotating status line ("charging the activity bar…")

Click anywhere to skip. Disable in Settings ("Show boot splash") or run
with ``--no-splash``. Falls back to a flat card when the baked artwork
or PIL is unavailable.
"""

import os
import tkinter as tk

from . import APP_NAME, APP_VERSION, APP_CHANNEL
from .onboarding import load_scaled

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

DARK_BG = "#0d0b14"
TEXT = "#f0eef7"
MUTED = "#948fa3"
TRACK = "#1e1b2c"
BORDER = "#2a2440"

STATUSES = (
    "warming up the editor",
    "charging the activity bar",
    "sharpening the highlighter",
    "polishing the pixels",
    "almost there",
)


class Splash:
    """Brand boot card shown while the studio warms up."""

    W, H = 480, 340

    def __init__(self, root, accent="#7c3aed", duration_ms=2400, on_done=None):
        self.root = root
        self.accent = accent
        self.on_done = on_done
        self.closed = False
        self._status_i = 0
        self._shine = 0          # shimmer offset, px
        self._fade = 0

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=DARK_BG)
        try:
            self.win.attributes("-alpha", 0.0)
            self._alpha_ok = True
        except tk.TclError:
            self._alpha_ok = False

        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        self.win.geometry(f"{self.W}x{self.H}+{(sw - self.W) // 2}"
                          f"+{(sh - self.H) // 2 - 40}")

        self._bg = load_scaled(os.path.join(ASSETS_DIR, "splash_bg.png"),
                               self.W, self.H)
        if self._bg is not None:
            self._build_art_card()
        else:
            self._build_flat_card()

        self.win.bind("<Button-1>", lambda e: self.close())
        self.win.deiconify()   # master may be hidden during boot — map anyway
        self._fade_in()
        self._rotate_status()
        self._shimmer()
        self.root.after(duration_ms, self.close)

    # ------------------------------------------------------------ art card
    def _build_art_card(self):
        """Baked artwork + live shimmer bar + status line."""
        self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
                                bg=DARK_BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self._bg, anchor="nw")

        # progress track: y=560/2 → 280, x 160..800/2 → 80..400
        self.track = (80, 400)
        ty = 286
        self.canvas.create_rectangle(self.track[0], ty, self.track[1], ty + 4,
                                     fill=TRACK, outline="", width=0)
        self._shine_rect = self.canvas.create_rectangle(
            self.track[0], ty, self.track[0] + 56, ty + 4,
            fill=self.accent, outline="", width=0)

        self.status = self.canvas.create_text(
            self.W / 2, 312, text="warming up the editor", fill=MUTED,
            font=("Segoe UI", 9))

    def _build_flat_card(self):
        """Fallback when the baked artwork can't load."""
        outer = tk.Frame(self.win, bg=self.accent)
        outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner = tk.Frame(outer, bg=DARK_BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        logo = load_scaled(os.path.join(ASSETS_DIR, "logo.png"), 112, 112)
        if logo:
            self._logo_ref = logo
            tk.Label(inner, image=logo, bg=DARK_BG).pack(pady=(30, 0))
        else:
            c = tk.Canvas(inner, width=110, height=110, bg=DARK_BG,
                          highlightthickness=0)
            c.pack(pady=(30, 0))
            c.create_polygon(55, 16, 90, 55, 55, 94, 20, 55,
                             fill=self.accent, outline="")

        tk.Label(inner, text=APP_NAME, bg=DARK_BG, fg=TEXT,
                 font=("Segoe UI", 17, "bold")).pack(pady=(12, 0))
        tk.Label(inner, text="The clean, modern IDE. Built for flow.",
                 bg=DARK_BG, fg=MUTED, font=("Segoe UI", 9)).pack(pady=(2, 0))
        tk.Label(inner, text=f"v{APP_VERSION} · {APP_CHANNEL.upper()}",
                 bg=DARK_BG, fg=self.accent,
                 font=("Consolas", 10, "bold")).pack(pady=(10, 0))

        bar = tk.Frame(inner, bg=DARK_BG)
        bar.pack(pady=(16, 0))
        self._flat_track = tk.Frame(bar, bg=TRACK, width=280, height=4)
        self._flat_track.pack()
        self._flat_shine = tk.Frame(self._flat_track, bg=self.accent,
                                    width=56, height=4)
        self._flat_shine.place(x=0, y=0)

        self.status_lbl = tk.Label(inner, text="warming up the editor",
                                   bg=DARK_BG, fg=MUTED,
                                   font=("Segoe UI", 9))
        self.status_lbl.pack(side=tk.BOTTOM, pady=12)

    # ------------------------------------------------------------ animation
    def _fade_in(self):
        if self.closed or not self._alpha_ok:
            return
        self._fade = min(1.0, self._fade + 0.12)
        try:
            self.win.attributes("-alpha", self._fade)
        except tk.TclError:
            return
        if self._fade < 1.0:
            self.root.after(16, self._fade_in)

    def _close_fade(self):
        if not self._alpha_ok:
            self._finish()
            return
        self._fade = max(0.0, self._fade - 0.14)
        try:
            self.win.attributes("-alpha", self._fade)
        except tk.TclError:
            self._finish()
            return
        if self._fade > 0.0:
            self.root.after(12, self._close_fade)
        else:
            self._finish()

    def _shimmer(self):
        if self.closed:
            return
        self._shine += 7
        span = self.track[1] - self.track[0] - 56
        pos = abs((self._shine % (2 * span)) - span)   # ping-pong
        try:
            if hasattr(self, "_shine_rect"):
                self.canvas.coords(self._shine_rect,
                                   self.track[0] + pos, 286,
                                   self.track[0] + pos + 56, 290)
            elif hasattr(self, "_flat_shine"):
                self._flat_shine.place(x=pos, y=0)
        except tk.TclError:
            return
        self.root.after(34, self._shimmer)

    def _rotate_status(self):
        if self.closed:
            return
        self._status_i += 1
        text = STATUSES[self._status_i % len(STATUSES)]
        try:
            if hasattr(self, "status"):
                self.canvas.itemconfigure(self.status, text=text)
            elif hasattr(self, "status_lbl"):
                self.status_lbl.config(text=text)
        except tk.TclError:
            return
        self.root.after(700, self._rotate_status)

    # ---------------------------------------------------------------- close
    def close(self):
        if self.closed:
            return
        self.closed = True
        self._close_fade()

    def _finish(self):
        try:
            self.win.grab_release()
            self.win.destroy()
        except tk.TclError:
            pass
        if self.on_done is not None:
            self.on_done()
