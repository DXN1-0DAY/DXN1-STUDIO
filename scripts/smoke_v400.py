"""DS2 v2.40.0 UI smoke — the git lane chip (statusbar branch name,
amber ●N when files wait to be committed, ↑/↓ arrows on divergence,
click opens Source Control, `git watch [on|off]`), deps severity (the
watch chip goes RED when imports are missing from requirements, amber
only for drift), and chip tooltips.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v400.py

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
from dxn1_studio.app import (DXN1Studio, TERMINAL_HELP,  # noqa: E402
                             palette_help_rows)
from dxn1_studio import depcheck as dc  # noqa: E402
from dxn1_studio.gitpanel import repo_state  # noqa: E402
from dxn1_studio import verbs as vb     # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                   text=True)


# --------------------------------------------- engine: repo_state probe
plain = os.path.join(HOME, "plain")
os.makedirs(plain, exist_ok=True)
check("engine: a plain folder is not a repo",
      repo_state(plain)["repo"] is False)
check("engine: a missing folder is not a repo",
      repo_state(os.path.join(HOME, "ghost"))["repo"] is False)

ws = os.path.join(HOME, "ws-v400")
os.makedirs(ws, exist_ok=True)
_git("init", "-q", cwd=ws)
check("engine: fresh repo, branch named, nothing dirty",
      repo_state(ws)["repo"] is True
      and repo_state(ws)["branch"] != "" and repo_state(ws)["dirty"] == 0)
with open(os.path.join(ws, ".gitignore"), "w", encoding="utf-8") as fh:
    fh.write(".dxn1/\n")          # studio state never dirties the repo
with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
    fh.write("import yaml\nimport uvicorn\n")
with open(os.path.join(ws, "requirements.txt"), "w",
          encoding="utf-8") as fh:
    fh.write("PyYAML\n")
check("engine: untracked files count as dirty",
      repo_state(ws)["dirty"] == 3)   # .gitignore + main.py + requirements
_git("add", ".", cwd=ws)
check("engine: staged files count as dirty too",
      repo_state(ws)["dirty"] == 3)
_git("-c", "user.email=t@t", "-c", "user.name=t",
     "commit", "-qm", "one", cwd=ws)
st = repo_state(ws)
check("engine: after a commit it is clean again",
      st["dirty"] == 0 and bool(st["branch"]))
_git("checkout", "-q", "--detach", "HEAD", cwd=ws)
check("engine: detached HEAD is named honestly",
      repo_state(ws)["branch"] == "(detached)")
_git("checkout", "-q", "-", cwd=ws)

# ahead/behind honesty: git only knows what it fetched — after a fetch
# the branch line's tracking summary shows up in the probe
_o = os.path.join(HOME, "o.git")
subprocess.run(["git", "init", "-q", "--bare", _o], capture_output=True)
_c2 = os.path.join(HOME, "c2")
subprocess.run(["git", "clone", "-q", _o, _c2], capture_output=True)
_git("config", "user.email", "t@t", cwd=_c2)
_git("config", "user.name", "t", cwd=_c2)
with open(os.path.join(_c2, "f.txt"), "w", encoding="utf-8") as fh:
    fh.write("1\n")
_git("add", ".", cwd=_c2)
_git("commit", "-qm", "one", cwd=_c2)
_br = repo_state(_c2)["branch"]
_git("push", "-q", "-u", "origin", _br, cwd=_c2)
_c3 = os.path.join(HOME, "c3")
subprocess.run(["git", "clone", "-q", _o, _c3], capture_output=True)
_git("config", "user.email", "t@t", cwd=_c3)
_git("config", "user.name", "t", cwd=_c3)
with open(os.path.join(_c3, "g.txt"), "w", encoding="utf-8") as fh:
    fh.write("2\n")
_git("add", ".", cwd=_c3)
_git("commit", "-qm", "two", cwd=_c3)
_git("push", "-q", cwd=_c3)
_git("fetch", "-q", cwd=_c2)
st2 = repo_state(_c2)
check("engine: behind shows after a fetch (honest tracking)",
      st2["behind"] == 1 and st2["dirty"] == 0)
with open(os.path.join(_c2, "h.txt"), "w", encoding="utf-8") as fh:
    fh.write("3\n")
st3 = repo_state(_c2)
check("engine: dirty and behind report together",
      st3["dirty"] == 1 and st3["behind"] == 1)

# ------------------------------------- engine: deps severity in cache_state
check("engine: cache_state reads absent on a fresh workspace",
      dc.cache_state(ws)["state"] == "absent")
rep = dc.check_cached(ws)
_st = dc.cache_state(ws)
check("engine: stored report exposes its missing list",
      _st["state"] == "cached" and _st["missing"] == rep["missing"]
      and rep["missing"] == ["uvicorn"])

# ------------------------------------------------- app: the git chip
logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
opened = []
_real_view = app.show_sidebar_view
app.show_sidebar_view = lambda name, *a, **k: opened.append(name)
try:
    app._update_gitchip(force=True)
    check("chip: no workspace keeps it quiet",
          app.status_git.cget("text") == "")
    app.project_dir = plain
    app._update_gitchip(force=True)
    check("chip: a plain folder keeps it quiet too",
          app.status_git.cget("text") == "")
    app.project_dir = ws
    app._update_gitchip(force=True)
    branch = repo_state(ws)["branch"]
    check("chip: a clean repo shows the muted branch name",
          app.status_git.cget("text") == branch
          and "bold" not in str(app.status_git.cget("font")))
    with open(os.path.join(ws, "u.txt"), "w", encoding="utf-8") as fh:
        fh.write("x\n")
    app._update_gitchip(force=True)
    check("chip: an uncommitted file turns it amber, bold, ●N",
          app.status_git.cget("text") == "%s ●1" % branch
          and app.status_git.cget("fg") == "#f59e0b"
          and "bold" in str(app.status_git.cget("font")))
    app._git_chip_click()
    check("chip: clicking opens Source Control",
          "git" in opened and app.status_git.cget("text") != "")
    logs.clear()
    app.handle_terminal_command("git watch off")
    check("chip: off hides it and remembers",
          app.status_git.cget("text") == ""
          and app.config.get("git_watch", True) is False)
    logs.clear()
    app.handle_terminal_command("git watch maybe")
    check("chip: junk gets an honest usage line",
          any("usage: git watch" in s for s in logs)
          and app.config.get("git_watch", True) is False)
    logs.clear()
    app.handle_terminal_command("git watch")
    check("chip: bare verb flips it back on, amber ●1 again",
          app.config.get("git_watch", True) is True
          and "●1" in app.status_git.cget("text"))
    logs.clear()
    app.handle_terminal_command("git watch on")
    check("chip: explicit on is accepted",
          app.config.get("git_watch", True) is True)
    ran = []
    app.run_command = lambda cmd: ran.append(cmd)
    app.handle_terminal_command("git status --short")
    check("chip: plain git commands still pass through",
          ran == ["git status --short"])
    _git("add", ".", cwd=ws)
    _git("-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "two", cwd=ws)
    app._update_gitchip(force=True)
    check("chip: a commit calms it back to the branch name",
          app.status_git.cget("text") == branch)
    try:
        app._deps_watch_poll()
        check("chip: the shared 30s poll runs both lanes", True)
    except Exception:
        check("chip: the shared 30s poll runs both lanes", False)
finally:
    app.terminal.log = _real_tlog
    app.show_sidebar_view = _real_view

# --------------------------------------------- app: deps severity ladder
logs = []
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
try:
    shutil.rmtree(os.path.join(ws, ".dxn1"), ignore_errors=True)
    app.project_dir = ws
    app._update_depswatch(force=True)
    check("deps: absent shows the quiet placeholder",
          app.status_deps.cget("text") == "deps —")
    app.handle_terminal_command("deps")
    check("deps: an unpinned import lights the chip RED",
          app.status_deps.cget("text") == "● deps 1 missing"
          and app.status_deps.cget("fg") == "#f85149")
    logs.clear()
    with open(os.path.join(ws, "requirements.txt"), "a",
              encoding="utf-8") as fh:
        fh.write("uvicorn\n")
    app._update_depswatch(force=True)
    check("deps: edited requirements read as drift (amber)",
          app.status_deps.cget("text") == "● deps drift")
    app._deps_chip_click()
    check("deps: pinned import calms the chip back to ok",
          app.status_deps.cget("text") == "deps ok")
    logs.clear()
    app.handle_terminal_command("deps watch maybe")
    check("deps: the usage line explains both severities",
          any("amber" in s and "red" in s for s in logs))
finally:
    app.terminal.log = _real_tlog

# ------------------------------------------------- tooltips + registers
tip_widgets = [app.status_git, app.status_deps, app.status_sesave,
               app.status_scribe]
check("polish: every statusbar chip carries a hover tooltip",
      all(w.bind("<Enter>") for w in tip_widgets))
rows = vb.verb_rows(TERMINAL_HELP)
vmap = dict(rows)
check("help: TERMINAL_HELP advertises git watch",
      "git watch [on|off]" in vmap and "amber" in vmap["git watch [on|off]"])
check("help: the verbs browser flattens the new row",
      any(c == "git watch [on|off]" for c, _ in rows))
labels = [r[0] for r in palette_help_rows(app)]
check("palette: source-control watch entry registered",
      any("Source control watch" in l for l in labels))

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)
shutil.rmtree(os.path.join(tempfile.gettempdir(), "ds2-v400-git"),
              ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
