"""DS2 v2.42.0 UI smoke — every chip has a menu: the drift chip
gains a right-click menu (rescan, the repair row only when the chip
is red, a cache-bypassing fresh scan, the watch toggle) and the
branch chip's menu grows the AI commit draft plus push/pull through
the visible terminal runner — one shared themed renderer underneath.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v420.py

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


# ------------------------------------------- deps chip: the right-click menu
logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
ws = os.path.join(HOME, "ws-v420")
os.makedirs(ws, exist_ok=True)
with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
    fh.write("import uvicorn\nimport yaml\n")
with open(os.path.join(ws, "requirements.txt"), "w",
          encoding="utf-8") as fh:
    fh.write("PyYAML\n")
app.project_dir = ws
try:
    app.handle_terminal_command("deps")
    app._update_depswatch(force=True)
    check("deps: an unpinned import lights the chip red",
          app.status_deps.cget("text") == "● deps 1 missing")
    labels = [e[0] for e in app._deps_menu_entries()]
    check("menu: the red chip's menu offers the full lane",
          "Rescan deps" in labels
          and any(l.startswith("Queue deps fix") for l in labels)
          and "Fresh rescan (bypass cache)" in labels
          and "Deps watch on/off" in labels and "Rescan chip" in labels)
    # the repair row: same one-gesture contract as the red click
    app.terminal.input.delete(0, tk.END)
    logs.clear()
    for lab, cmd, *_r in app._deps_menu_entries():
        if lab.startswith("Queue deps fix"):
            cmd()
    check("menu: queue-fix prefills `deps fix` + the Enter hint",
          app.terminal.input.get() == "deps fix"
          and any("press Enter" in s for s in logs))
    # rescan row actually rescans
    logs.clear()
    for lab, cmd, *_r in app._deps_menu_entries():
        if lab == "Rescan deps":
            cmd()
    check("menu: rescan runs the report through the terminal",
          any("file(s) scanned" in s for s in logs))
    # after a repair the red row disappears — honest per state
    app.handle_terminal_command("deps fix")
    app._update_depswatch(force=True)
    check("deps: the fix healed the workspace (chip ok)",
          app.status_deps.cget("text") == "deps ok")
    labels = [e[0] for e in app._deps_menu_entries()]
    check("menu: an ok workspace gets no repair row",
          "Queue deps fix" not in labels)
    # fresh rescan bypasses the cache and still lands
    logs.clear()
    for lab, cmd, *_r in app._deps_menu_entries():
        if lab == "Fresh rescan (bypass cache)":
            cmd()
    check("menu: fresh rescan re-scans beyond the cache",
          any("file(s) scanned" in s for s in logs))
    # watch toggle from the menu silences the chip
    for lab, cmd, *_r in app._deps_menu_entries():
        if lab == "Deps watch on/off":
            cmd()
    check("menu: the watch toggle silences the chip",
          app.status_deps.cget("text") == ""
          and app.config.get("deps_watch") is False)
    app.config.set("deps_watch", True)
    app._deps_sig_state = ""
    app._update_depswatch(force=True)
    app._deps_chip_menu()          # renderer never raises
finally:
    app.terminal.log = _real_tlog

# ------------------------------------------- git chip: AI draft + push/pull
repo = os.path.join(HOME, "repo-v420")
os.makedirs(repo, exist_ok=True)
_git("init", "-q", cwd=repo)
with open(os.path.join(repo, "f.txt"), "w", encoding="utf-8") as fh:
    fh.write("x\n")
_git("add", ".", cwd=repo)
_git("-c", "user.email=t@t", "-c", "user.name=t",
     "commit", "-qm", "one", cwd=repo)
app.project_dir = repo
opened, drafted, ran = [], [], []
_real_view = app.show_sidebar_view
app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
_real_ai = app.git_view.ai_message
app.git_view.ai_message = lambda: drafted.append(1)
_real_run = app.run_command
app.run_command = lambda cmd: ran.append(cmd)
try:
    labels = [e[0] for e in app._git_menu_entries()]
    check("menu: the branch menu gained the new lane rows",
          "Draft AI commit message" in labels
          and "Push to origin" in labels
          and "Pull from upstream" in labels
          and "Open Source Control" in labels and "Rescan" in labels)
    for lab, cmd, *_r in app._git_menu_entries():
        if lab in ("Push to origin", "Pull from upstream"):
            cmd()
    check("menu: push/pull route to the visible terminal runner",
          ran == ["git push", "git pull"])
    for lab, cmd, *_r in app._git_menu_entries():
        if lab == "Draft AI commit message":
            cmd()
    check("menu: the AI draft opens Source Control + fires the helper",
          opened == ["git"] and drafted == [1])
    # a plain folder: the lane rows stay honest
    plain = os.path.join(HOME, "plain-v420")
    os.makedirs(plain, exist_ok=True)
    app.project_dir = plain
    labels = [e[0] for e in app._git_menu_entries()]
    check("menu: a plain folder loses every repo row",
          "Draft AI commit message" not in labels
          and "Push to origin" not in labels
          and "Pull from upstream" not in labels
          and "Open Source Control" in labels)
    app._git_chip_menu()           # renderer never raises
finally:
    app.show_sidebar_view = _real_view
    app.git_view.ai_message = _real_ai
    app.run_command = _real_run

# ------------------------------------------------------- one shared renderer
src = open("dxn1_studio/app.py", encoding="utf-8").read()
# v2.43: all four chips (git, deps, sesave, scribe) advertise menus now
check("tooltips: every chip advertises its right-click menu",
      src.count("right-click for actions") == 6)
check("renderer: exactly one popup renderer drives both menus",
      src.count("def _render_chip_menu") == 1
      and "_render_chip_menu(self._git_menu_entries(), event)"
      in src and "_render_chip_menu(self._deps_menu_entries(), event)" in src)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
