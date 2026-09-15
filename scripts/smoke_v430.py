"""DS2 v2.43.0 UI smoke — the whole family is chipped in: the scribe
chip (summary / goal / reset) and the session-autosave chip (snapshot
now / browse / autosave toggle) gain right-click menus through the
one shared themed renderer, and the branch chip's menu grows
'Commit staged…' which opens Source Control and puts the cursor in
the commit message box.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v430.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + sessions
sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk  # noqa: E402

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# ----------------------------------------------------------------- boot
_cfg_dir = os.path.join(HOME, ".dxn1-studio")
os.makedirs(_cfg_dir, exist_ok=True)
with open(os.path.join(_cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"onboarded": True, "hub_on_startup": False,
               "check_updates": False}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.config import Config  # noqa: E402
from dxn1_studio.app import DXN1Studio  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                   text=True)


logs, toasts = [], []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
app.toast = lambda msg, kind="info": toasts.append(str(msg))

# ------------------------------------------- scribe chip: the right-click menu
try:
    rows = app._scribe_menu_entries()
    labels = [e[0] for e in rows]
    check("scribe: the menu offers summary, goal and reset",
          labels == ["Session summary", "Set writing goal…",
                     "Reset session meter"])
    # the goal row: opens the v2.44 dialog — nothing fires by accident
    app.terminal.input.delete(0, tk.END)
    logs.clear()
    # v2.44: the goal row opens the themed dialog now (an explicit
    # Set gesture commits it) — assert a Writing goal window appears
    for lab, cmd, *_r in rows:
        if lab == "Set writing goal…":
            cmd()
    app.root.update()
    goal_dlg = [w for w in app.root.winfo_children()
                if isinstance(w, tk.Toplevel)
                and str(w.title()) == "Writing goal"]
    check("scribe: goal row opens the themed goal dialog",
          bool(goal_dlg))
    if goal_dlg:
        goal_dlg[-1].destroy()
        app.root.update()
    # the reset row: the meter restarts, the goal survives
    if app.scribe_chip is not None:
        app.scribe_chip.observe(1200, now=0.0)
        app.scribe_chip.observe(1300, now=30.0)
        goal_before = app.scribe_chip.goal_words
        logs.clear()
        toasts.clear()
        for lab, cmd, *_r in rows:
            if lab == "Reset session meter":
                cmd()
        check("scribe: reset zeroes words and repaints the chip",
              app.scribe_chip.words() == 0
              and app.status_scribe.cget("text") ==
              app.scribe_chip.text())
        check("scribe: reset keeps the goal and says so",
              app.scribe_chip.goal_words == goal_before
              and any("reset" in s.lower() for s in toasts))
    app._scribe_chip_menu()                # renderer never raises
    check("scribe: the popup renderer serves the menu",
          True)
except Exception as exc:  # noqa: BLE001 — a smoke reports, not crashes
    check("scribe menu flow raised: %s" % exc, False)

# ------------------------------------------ sesave chip: the right-click menu
try:
    rows = app._sesave_menu_entries()
    labels = [e[0] for e in rows]
    check("sesave: the menu offers snapshot, browse and toggle",
          "Snapshot session now" in labels
          and "Browse snapshots…" in labels
          and "Autosave on/off" in labels)
    # the toggle: live config flip both ways, honest feedback
    app.config.set("session_autosave", True)
    toasts.clear()
    for lab, cmd, *_r in rows:
        if lab == "Autosave on/off":
            cmd()
    off_ok = (app.config.get("session_autosave") is False
              and any("off" in s for s in toasts))
    logs.clear()
    for lab, cmd, *_r in app._sesave_menu_entries():
        if lab == "Autosave on/off":
            cmd()
    check("sesave: the toggle flips live and logs the beat",
          off_ok and app.config.get("session_autosave") is True
          and any("session autosave is now on" in s for s in logs))
    # snapshot row with no workspace: the honest toast, nothing raised
    app.project_dir = ""
    toasts.clear()
    for lab, cmd, *_r in app._sesave_menu_entries():
        if lab == "Snapshot session now":
            cmd()
    check("sesave: no workspace → the honest toast",
          any("No workspace open" in s for s in toasts))
    # snapshot row with a real workspace: the chip flashes saved
    ws = os.path.join(HOME, "ws-v430")
    os.makedirs(ws, exist_ok=True)
    with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
        fh.write("print('hi')\n")
    app.project_dir = ws
    logs.clear()
    for lab, cmd, *_r in app._sesave_menu_entries():
        if lab == "Snapshot session now":
            cmd()
    check("sesave: a click on the row writes the snapshot",
          any("Session snapshot saved" in s for s in logs)
          and app.status_sesave.cget("text").startswith("◐"))
    # browse row routes to the existing snapshot browser (stub BEFORE
    # the build — rows capture the bound method at build time)
    browsed = []
    app.open_session_restore = lambda *a, **k: browsed.append(1)
    for lab, cmd, *_r in app._sesave_menu_entries():
        if lab == "Browse snapshots…":
            cmd()
    check("sesave: browse opens the snapshot browser",
          browsed == [1])
    app._sesave_chip_menu()                # renderer never raises
except Exception as exc:  # noqa: BLE001 — a smoke reports, not crashes
    check("sesave menu flow raised: %s" % exc, False)

# --------------------------------------- branch chip: Commit staged… row
repo = os.path.join(HOME, "repo-v430")
os.makedirs(repo, exist_ok=True)
_git("init", "-q", cwd=repo)
with open(os.path.join(repo, "f.txt"), "w", encoding="utf-8") as fh:
    fh.write("x\n")
_git("add", ".", cwd=repo)
_git("-c", "user.email=t@t", "-c", "user.name=t",
     "commit", "-qm", "one", cwd=repo)
app.project_dir = repo
opened, focused = [], []
_real_view = app.show_sidebar_view
app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
_real_focus = app.git_view.focus_message
app.git_view.focus_message = lambda: focused.append(1)
try:
    labels = [e[0] for e in app._git_menu_entries()]
    check("git: the branch menu gained 'Commit staged…'",
          "Commit staged…" in labels, )
    for lab, cmd, *_r in app._git_menu_entries():
        if lab == "Commit staged…":
            cmd()
    check("git: commit row opens Source Control + focuses the box",
          opened == ["git"] and focused == [1])
finally:
    app.show_sidebar_view = _real_view
    app.git_view.focus_message = _real_focus
try:
    app.git_view.focus_message()   # the real method never raises
    check("git: the panel's real focus_message is wired", True)
except Exception as exc:  # noqa: BLE001
    check("git: real focus_message raised: %s" % exc, False)

# ------------------------------------------------- one renderer, four menus
src = open("dxn1_studio/app.py", encoding="utf-8").read()
check("renderer: exactly one popup renderer for the family",
      src.count("def _render_chip_menu") == 1
      and all(("_render_chip_menu(self._%s_menu_entries(), event)" % lane)
              in src for lane in ("git", "deps", "scribe", "sesave")))
check("bindings: all four chips bind Button-3",
      "self.status_scribe.bind(\"<Button-3>\"" in src
      and "self.status_sesave.bind(\"<Button-3>\"" in src
      and "self.status_deps.bind(\"<Button-3>\"" in src
      and "self.status_git.bind(\"<Button-3>\"" in src)
check("tooltips: every chip advertises right-click for actions",
      src.count("right-click for actions") == 6)
check("palette: the chip-family rows are registered",
      "Session — snapshot tabs now…" in src
      and "Scribe — reset the writing meter…" in src)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
