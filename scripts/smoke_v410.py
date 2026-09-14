"""DS2 v2.41.0 UI smoke — chip gestures: the red deps chip click
queues `deps fix` (one-gesture repair, Enter runs it, the workspace
rescans and the cache never lies after a fix), the branch chip's
right-click menu is honest per state with working commands, and the
Settings dialog gained a "Statusbar watch chips" section.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v410.py

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
from dxn1_studio.app import DXN1Studio, SettingsDialog  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                   text=True)


# ------------------------------------------- deps: one-gesture repair
logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
ws = os.path.join(HOME, "ws-v410")
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
    app.terminal.input.delete(0, tk.END)
    logs.clear()
    app._deps_chip_click()
    check("deps: the red click queues `deps fix` in the input",
          app.terminal.input.get() == "deps fix"
          and any("press Enter" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("deps fix")     # the Enter press
    req = open(os.path.join(ws, "requirements.txt"),
               encoding="utf-8").read()
    check("deps: Enter pinned uvicorn into requirements.txt",
          "uvicorn" in req)
    check("deps: after the fix the chip is honest again (ok)",
          app.status_deps.cget("text") == "deps ok")
    check("deps: the fix re-scanned and re-stored the cache",
          any("added 1 pin" in s for s in logs))
    # amber click stays a plain rescan — no prefill
    app.terminal.input.delete(0, tk.END)
    with open(os.path.join(ws, "late.py"), "w", encoding="utf-8") as fh:
        fh.write("import flask\n")
    app._update_depswatch(force=True)
    check("deps: a new import reads as drift (amber)",
          app.status_deps.cget("text") == "● deps drift")
    logs.clear()
    app._deps_chip_click()
    check("deps: the amber click is just a rescan (no queueing)",
          app.terminal.input.get() == ""
          and any("file(s) scanned" in s for s in logs))
finally:
    app.terminal.log = _real_tlog

# ------------------------------------------- git: the chip context menu
repo = os.path.join(HOME, "repo-v410")
os.makedirs(repo, exist_ok=True)
_git("init", "-q", cwd=repo)
with open(os.path.join(repo, "f.txt"), "w", encoding="utf-8") as fh:
    fh.write("x\n")
app.project_dir = repo
opened = []
_real_view = app.show_sidebar_view
app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
ran = []
_real_run = app.run_command
app.run_command = lambda cmd: ran.append(cmd)
try:
    labels = [e[0] for e in app._git_menu_entries()]
    check("menu: a repo offers the full lane actions",
          "Open Source Control" in labels and "Commit graph" in labels
          and "Stage all changes" in labels and "Rescan" in labels)
    for lab, cmd, *_r in app._git_menu_entries():
        if lab == "Stage all changes":
            cmd()
    check("menu: stage-all routes to the shell runner",
          ran == ["git add -A"])
    _git("add", ".", cwd=repo)          # stage-all was only recorded
    _git("-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "one", cwd=repo)
    app._update_gitchip(force=True)
    branch = app.status_git.cget("text")
    check("menu: the committed repo shows the muted branch name",
          branch not in ("",) and "●" not in branch)
    for lab, cmd, *_r in app._git_menu_entries():
        if lab == "Copy branch name":
            cmd()
    check("menu: copy-branch fills the clipboard + toasts",
          app.root.clipboard_get() == branch)
    for lab, cmd, *_r in app._git_menu_entries():
        if lab == "Open Source Control":
            cmd()
    check("menu: open jumps to Source Control",
          opened == ["git"])
    # the renderer never raises, repo or not
    app._git_chip_menu()
    plain = os.path.join(HOME, "plain-v410")
    os.makedirs(plain, exist_ok=True)
    app.project_dir = plain
    labels = [e[0] for e in app._git_menu_entries()]
    check("menu: a plain folder gets an honest menu (lane rows gone)",
          "Stage all changes" not in labels
          and "Copy branch name" not in labels
          and "Open Source Control" in labels and "Rescan" in labels)
    app._git_chip_menu()
finally:
    app.show_sidebar_view = _real_view
    app.run_command = _real_run

# ------------------------------------------------- settings: watch chips
app.project_dir = repo               # the chip needs a repo to show
try:
    dlg = SettingsDialog(app)
    app.root.update()
    check("settings: the watch-chip section exists",
          hasattr(dlg, "depswatch_v") and hasattr(dlg, "gitwatch_v"))
    dlg.gitwatch_v.set(False)
    dlg.depswatch_v.set(False)
    dlg._save()
    app.root.update()
    check("settings: unchecking both chips persists",
          app.config.get("git_watch") is False
          and app.config.get("deps_watch") is False)
    check("settings: saving hides both chips immediately",
          app.status_git.cget("text") == ""
          and app.status_deps.cget("text") == "")
    dlg.gitwatch_v.set(True)
    dlg.depswatch_v.set(True)
    dlg._save()
    app.root.update()
    check("settings: re-checking restores config + chips",
          app.config.get("git_watch") is True
          and app.status_git.cget("text") != "")
    try:
        dlg.destroy()
    except Exception:  # noqa: BLE001
        pass
except Exception as exc:  # noqa: BLE001
    check(f"settings: dialog round-trip failed ({exc})", False)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
