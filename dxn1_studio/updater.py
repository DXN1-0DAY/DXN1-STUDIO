"""DXN1 STUDIO — the Update Portal (v1.1.5).

When the studio detects a newer release on GitHub it doesn't whisper
about it in a toast — it opens the Update Portal: a full-screen,
cinematic takeover built around the studio's violet portal art. The
portal announces the new version, offers a one-click in-place update
(files are streamed from GitHub, verified with compileall, then the
studio restarts itself into the fresh build) and shows real progress
along the way. Staying on an old version is possible, but the studio
says goodbye — old builds miss security fixes and polish.

Everything here is stdlib: urllib for the network, Tk for the show,
optional PIL only to rescale the art to any screen shape.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request

from . import APP_NAME, APP_VERSION
from .theme import FONT_UI, FONT_MONO

REPO_API = "https://api.github.com/repos/DXN1-termux/DXN1-STUDIO"
REPO_RAW = "https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master"
UA = f"DXN1-Studio/{APP_VERSION} (update-portal)"

# the files an in-place update refreshes — mirrors install.sh exactly
MODULES = (
    "__init__.py", "app.py", "config.py", "theme.py", "widgets.py",
    "onboarding.py", "tour.py", "projects.py", "hub.py", "splash.py",
    "packages.py", "export.py", "agent.py", "sandbox.py", "llm.py",
    "search.py", "errors.py", "gitpanel.py", "updater.py",
)
ENTRY_SCRIPTS = ("dxn1-studio", "dxn1", "DXN1 STUDIO")
ASSETS = ("logo.png", "welcome_hero.png", "hub_hero.png", "agents_hero.png",
          "update_hero.png")

MIN_SHOW_SECONDS = 3.0     # the progress show never flashes past too fast


def _ascii(text):
    """Tk font fallbacks on Linux miss typographic glyphs (em-dash,
    ellipsis, warning sign) — keep every portal string ASCII-safe."""
    text = str(text or "")
    for src, dst in (("\u2014", " - "), ("\u2013", "-"), ("\u2026", "..."),
                     ("\u2018", "'"), ("\u2019", "'"),
                     ("\u201c", '"'), ("\u201d", '"'), ("\u203a", ">"),
                     ("\u00bb", ">>"), ("\u26a0", "!"), ("\u2022", "-"),
                     ("\u2192", "->")):
        text = text.replace(src, dst)
    return text.encode("ascii", "replace").decode("ascii")


# ------------------------------------------------------------ version feed
def fetch_latest():
    """Latest GitHub release. Returns (tag, url, notes) or ("", "", "")."""
    req = urllib.request.Request(
        f"{REPO_API}/releases/latest",
        headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    tag = (data.get("tag_name") or "").lstrip("v")
    body = (data.get("body") or "").strip()
    lines = [ln.lstrip("-* ").strip() for ln in body.splitlines()
             if ln.strip().startswith(("-", "*"))][:3]
    return tag, data.get("html_url") or REPO_API, lines


def ver_tuple(version):
    import re
    parts = re.findall(r"\d+", version or "")
    if not parts:
        return (0, 0, 0)
    nums = [int(p) for p in parts[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(latest, current=APP_VERSION):
    return ver_tuple(latest) > ver_tuple(current)


# --------------------------------------------------------------- installer
def _package_root():
    """Directory that contains the dxn1_studio package."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _download(rel_path, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = f"{REPO_RAW}/{urllib.request.quote(rel_path)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    tmp = dest + ".new"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest)
    return len(data)


def _is_git_checkout(root):
    return os.path.isdir(os.path.join(root, ".git"))


def _git_pull(root):
    out = subprocess.run(
        ["git", "-C", root, "pull", "--ff-only"], capture_output=True,
        text=True, timeout=120)
    return out.returncode == 0, (out.stdout + out.stderr).strip()


def perform_update(report):
    """Download + install the new build. ``report(dict)`` keeps the UI fed.

    Keys posted: stage (label), done (files finished), total, error, ok.
    Runs on a worker thread — never touches Tk.
    """
    root = _package_root()
    pkg = os.path.join(root, "dxn1_studio")
    files = [(f"dxn1_studio/{m}", os.path.join(pkg, m)) for m in MODULES]
    files += [(s, os.path.join(root, s)) for s in ENTRY_SCRIPTS]
    files += [(f"assets/{a}", os.path.join(root, "assets", a))
              for a in ASSETS]

    git_ok = False
    if _is_git_checkout(root):
        report(stage="Pulling the new build from GitHub...")
        git_ok, _ = _git_pull(root)

    if not git_ok:
        total = len(files)
        report(stage="Downloading the new build...", total=total)
        done = 0
        for rel, dest in files:
            try:
                _download(rel, dest)
            except Exception as exc:  # noqa: BLE001 — surface in the portal
                report(error=f"{rel}: {exc}")
                return False
            done += 1
            report(done=done, detail=os.path.basename(rel))
    else:
        report(done=len(files), total=len(files),
               detail="git pull --ff-only")

    report(stage="Verifying the new build...")
    import py_compile
    for m in MODULES:
        path = os.path.join(pkg, m)
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as exc:
            report(error=f"verification failed: {exc}")
            return False
    report(ok=True)
    return True


# ================================================================== portal
class UpdatePortal(tk.Toplevel):
    """Full-screen, cinematic update takeover. One instance at a time."""

    def __init__(self, app, latest, release_url="", notes=()):
        super().__init__(app.root, bg="#12071f")
        self.app = app
        self.latest = _ascii(latest)
        self.release_url = release_url
        self.notes = [n for n in (_ascii(x) for x in notes) if n]
        self.t = app.theme
        self._eq = queue.Queue()
        self._photo = None
        self._photo_size = (0, 0)
        self._particles = []
        self._frac = 0.0
        self._target = 0.0
        self._t0 = 0.0
        self._restart_job = None
        self._stage = ""
        self._detail = ""
        self._done = 0
        self._total = 0

        self.overrideredirect(True)
        try:
            self.attributes("-fullscreen", True)
        except tk.TclError:
            pass
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.configure(bg="#12071f")
        self.grab_set()

        w = max(1, self.winfo_screenwidth())
        h = max(1, self.winfo_screenheight())
        self.geometry(f"{w}x{h}+0+0")
        self.protocol("WM_DELETE_WINDOW", lambda: None)   # no escape hatch
        self.lift()
        self.focus_force()

        self.canvas = tk.Canvas(self, bg="#12071f", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self._paint())

        self._phase = "offer"
        self._paint()
        self._animate()
        self._poll()
        self.bind("<Escape>", lambda e: None)

    # ------------------------------------------------------------- artwork
    def _paint(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 1
        h = c.winfo_height() or 1
        self._draw_bg(w, h)
        if self._phase == "offer":
            self._draw_offer(w, h)
        elif self._phase == "installing":
            self._draw_progress(w, h)
        elif self._phase == "declined":
            self._draw_declined(w, h)
        else:
            self._draw_restarting(w, h)
        self._draw_particles(w, h)

    def _draw_bg(self, w, h):
        c = self.canvas
        art = os.path.join(_package_root(), "assets", "update_hero.png")
        if (self._photo is None or self._photo_size != (w, h)) and \
                w > 50 and h > 50 and os.path.isfile(art):
            img = None
            try:
                from PIL import Image
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:            # Pillow < 9.1
                    resample = Image.LANCZOS
                from PIL import ImageTk
                img = ImageTk.PhotoImage(
                    Image.open(art).convert("RGB").resize((w, h), resample),
                    master=self)
            except Exception:
                try:
                    img = tk.PhotoImage(file=art, master=self)
                except Exception:
                    img = None
            self._photo = img
            self._photo_size = (w, h) if img is not None else (0, 0)
        if self._photo is not None:
            c.create_image(0, 0, image=self._photo, anchor="nw")
        else:
            # geometric fallback — layered violet glow rings
            cx, cy = w // 2, int(h * 0.42)
            for r, col in ((h * 0.9, "#1a0b2e"), (h * 0.55, "#241040"),
                           (h * 0.32, "#31175a")):
                c.create_oval(cx - r, cy - r * 0.62, cx + r, cy + r * 0.62,
                              fill=col, outline="")
        # dark scrim so text always wins over the art
        c.create_rectangle(0, 0, w, h, fill="#0d0618", outline="",
                           stipple="gray50")

    def _panel(self, c, cx, y0, y1, half_w=430):
        """Solid dark stage behind the text block — readability first."""
        c.create_rectangle(cx - half_w, y0, cx + half_w, y1,
                           fill="#150a28", outline="#2a1548")

    # phases -----------------------------------------------------------
    def _draw_offer(self, w, h):
        c = self.canvas
        cx = w // 2
        y = int(h * 0.24)
        by = int(h * 0.60)
        self._panel(c, cx, y - 34, by + 118)
        c.create_text(cx, y, text="◆  DXN1 STUDIO  ·  UPDATE PORTAL",
                      fill="#c4b5fd", font=(FONT_UI, 13, "bold"))
        c.create_text(cx, y + 56, text=f"v{self.latest} is here",
                      fill="#ffffff", font=(FONT_UI, 44, "bold"))
        # version pill: current -> new
        pill = f"  v{APP_VERSION}   »   v{self.latest}  "
        pw = 14 * len(pill) + 40
        c.create_rectangle(cx - pw // 2, y + 100, cx + pw // 2, y + 132,
                           fill="#241040", outline="#4c2a8f")
        c.create_text(cx, y + 116, text=pill,
                      fill="#d8ccf5", font=(FONT_MONO, 11, "bold"))
        c.create_text(cx, y + 158,
                      text=f"We have detected a new version v{self.latest} "
                           f"of DXN1 STUDIO.",
                      fill="#d8ccf5", font=(FONT_UI, 13))
        ny = y + 192
        for note in self.notes:
            if note:
                c.create_text(cx, ny, text=f">  {note[:88]}",
                              fill="#a89bc9", font=(FONT_UI, 11))
                ny += 26
        install = c.create_rectangle(cx - 190, by, cx + 190, by + 58,
                                     fill="#7c3aed", outline="#a78bfa",
                                     width=2)
        c.create_text(cx, by + 29, text="Install update & restart",
                      fill="#ffffff", font=(FONT_UI, 14, "bold"))
        later = c.create_text(cx, by + 92, text="I'll stay on this version",
                              fill="#8b7bb8", font=(FONT_UI, 10, "underline"))
        for tag in (install, later):
            c.tag_bind(tag, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.config(cursor=""))
        c.tag_bind(install, "<Button-1>", lambda e: self.start_install())
        c.tag_bind(later, "<Button-1>", lambda e: self.decline())

    def _draw_progress(self, w, h):
        c = self.canvas
        cx = w // 2
        y = int(h * 0.30)
        self._panel(c, cx, y - 44, y + 220, half_w=380)
        c.create_text(cx, y, text="◆  DXN1 STUDIO  ·  UPDATE PORTAL",
                      fill="#c4b5fd", font=(FONT_UI, 12, "bold"))
        c.create_text(cx, y + 48, text=f"Installing v{self.latest} ...",
                      fill="#ffffff", font=(FONT_UI, 30, "bold"))
        bw, bh = min(560, int(w * 0.6)), 10
        bx, by = cx - bw // 2, y + 100
        c.create_rectangle(bx, by, bx + bw, by + bh, fill="#241040",
                           outline="#3b2170")
        fw = int(bw * max(0.02, min(1.0, self._frac)))
        if fw > 2:
            c.create_rectangle(bx, by, bx + fw, by + bh, fill="#a855f7",
                               outline="")
        c.create_text(cx, by + 34, text=self._stage or "Preparing...",
                      fill="#d8ccf5", font=(FONT_UI, 11))
        if self._detail:
            c.create_text(cx, by + 58, text=self._detail,
                          fill="#8b7bb8", font=(FONT_MONO, 9))
        c.create_text(cx, by + 96,
                      text="The studio restarts itself when this finishes.",
                      fill="#8b7bb8", font=(FONT_UI, 9, "italic"))

    def _draw_declined(self, w, h):
        c = self.canvas
        cx = w // 2
        y = int(h * 0.26)
        by = int(h * 0.58)
        self._panel(c, cx, y - 40, by + 118)
        # hand-drawn warning triangle — the unicode sign has no glyph here
        tx, ty, s = cx, y + 8, 22
        c.create_polygon(tx, ty - s, tx - s, ty + s * 0.72,
                         tx + s, ty + s * 0.72, fill="",
                         outline="#fbbf24", width=3)
        c.create_text(tx, ty + 5, text="!", fill="#fbbf24",
                      font=(FONT_UI, 15, "bold"))
        c.create_text(cx, y + 76, text="Old versions can't come along.",
                      fill="#ffffff", font=(FONT_UI, 28, "bold"))
        c.create_text(cx, y + 128,
                      text="You cannot continue on this version — for "
                           "security and for your own experience reasons.",
                      fill="#d8ccf5", font=(FONT_UI, 13))
        c.create_text(cx, y + 156,
                      text="Every update carries fixes you'll want the "
                           "moment you need them.",
                      fill="#a89bc9", font=(FONT_UI, 11, "italic"))
        c.create_text(cx, y + 196,
                      text="Your projects, chats and settings stay "
                           "exactly as they are.",
                      fill="#8b7bb8", font=(FONT_UI, 10))
        go = c.create_rectangle(cx - 190, by, cx + 190, by + 58,
                                fill="#7c3aed", outline="#a78bfa", width=2)
        c.create_text(cx, by + 29, text="OK — install the update",
                      fill="#ffffff", font=(FONT_UI, 14, "bold"))
        quit_ = c.create_text(cx, by + 92, text="Exit DXN1 STUDIO",
                              fill="#8b7bb8", font=(FONT_UI, 10, "underline"))
        for tag in (go, quit_):
            c.tag_bind(tag, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.config(cursor=""))
        c.tag_bind(go, "<Button-1>", lambda e: self.start_install())
        c.tag_bind(quit_, "<Button-1>", lambda e: self._exit_app())

    def _draw_restarting(self, w, h):
        c = self.canvas
        cx = w // 2
        y = int(h * 0.40)
        c.create_text(cx, y, text="◆", fill="#e9d5ff", font=(FONT_UI, 34))
        c.create_text(cx, y + 56, text=f"v{self.latest} installed — "
                                       f"restarting the studio...",
                      fill="#ffffff", font=(FONT_UI, 20, "bold"))
        c.create_text(cx, y + 96, text="See you on the other side.",
                      fill="#a89bc9", font=(FONT_UI, 11, "italic"))

    # ------------------------------------------------------------ particles
    def _draw_particles(self, w, h):
        """Drifting light motes above the scrim — keeps the portal alive."""
        c = self.canvas
        c.delete("motes")
        for p in self._particles:
            x, y, s = int(p["x"]), int(p["y"]), p["s"]
            c.create_oval(x - s, y - s, x + s, y + s,
                          fill="#d8b4fe", outline="", tags="motes")

    def _animate(self):
        w = self.winfo_width() or 1
        h = self.winfo_height() or 1
        while len(self._particles) < 16:
            self._particles.append({
                "x": __import__("random").randint(0, max(1, w)),
                "y": h + __import__("random").randint(0, h // 2),
                "v": __import__("random").uniform(0.4, 1.4),
                "s": __import__("random").choice((2, 2, 3)),
            })
        for p in self._particles:
            p["y"] -= p["v"]
            if p["y"] < -6:
                p["y"] = h + 6
                p["x"] = __import__("random").randint(0, max(1, w))
        # smooth progress bar creep toward the latest target
        self._frac += (self._target - self._frac) * 0.08
        if self._phase == "installing":
            self._paint()
        self.after(33, self._animate)

    # ------------------------------------------------------------- actions
    def start_install(self):
        if self._phase == "installing":
            return
        self._phase = "installing"
        self._stage = "Preparing the update..."
        self._detail = ""
        self._target = 0.05
        self._t0 = time.monotonic()
        self._done = 0
        self._total = len(MODULES) + len(ENTRY_SCRIPTS) + len(ASSETS)
        self._paint()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        def report(stage="", done=None, total=None, detail="", error="",
                   ok=False):
            msg = {"stage": stage or self._stage, "detail": detail,
                   "error": error, "ok": ok}
            if done is not None:
                self._done = done
                msg["done"] = done
            if total is not None:
                self._total = total
                msg["total"] = total
            self._eq.put(msg)

        try:
            perform_update(report)
        except Exception as exc:  # noqa: BLE001 — portal never crashes
            report(error=str(exc))

    def _poll(self):
        try:
            while True:
                msg = self._eq.get_nowait()
                if msg.get("error"):
                    self._fail(_ascii(msg["error"]))
                    return
                if "done" in msg and "total" in msg and msg["total"]:
                    self._target = 0.08 + 0.82 * (msg["done"] / msg["total"])
                if msg.get("stage"):
                    self._stage = _ascii(msg["stage"])
                self._detail = _ascii(msg.get("detail", ""))
                if msg.get("ok"):
                    self._target = 1.0
                    elapsed = time.monotonic() - self._t0
                    delay = max(0, int((MIN_SHOW_SECONDS - elapsed) * 1000))
                    self._stage = "Update complete."
                    self._detail = f"v{self.latest} is now on disk."
                    try:
                        self.app.config.set("version", self.latest)
                    except Exception:
                        pass
                    self._restart_job = self.after(
                        delay + 600, self._restart)
        except queue.Empty:
            pass
        self.after(90, self._poll)

    def _restart(self):
        self._phase = "restarting"
        self._paint()
        root = _package_root()
        entry = os.path.join(root, "dxn1-studio")
        self.after(1400, lambda: self._exec_restart(entry))

    def _exec_restart(self, entry):
        try:
            self.app.stop_run(silent=True)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        if os.path.isfile(entry):
            os.execv(sys.executable, [sys.executable, entry])
        os.execv(sys.executable, [sys.executable, "-m", "dxn1_studio"])

    def _fail(self, why):
        self._phase = "offer"
        self._stage = ""
        self._target = 0.0
        self._paint()
        c = self.canvas
        c.create_text(self.winfo_width() // 2, int(self.winfo_height() * 0.9),
                      text=f"! Update hit a snag: {why[:120]} - check your "
                           f"connection and try again.",
                      fill="#fca5a5", font=(FONT_UI, 10))

    def decline(self):
        self._phase = "declined"
        self._paint()

    def _exit_app(self):
        try:
            self.app.stop_run(silent=True)
        except Exception:
            pass
        try:
            self.app.config.save()
        except Exception:
            pass
        self.destroy()
        self.app.root.destroy()
