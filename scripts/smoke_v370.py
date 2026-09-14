"""DS2 v2.37.0 UI smoke — `deps fix` (self-healing requirements),
`help <verb>` (per-verb docs), and the Workshop Dependency Check entry.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v370.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
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
from dxn1_studio.app import DXN1Studio, matching_help_rows  # noqa: E402
from dxn1_studio import depcheck as dc  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

# --------------------------------------------- engine: reverse aliases
check("engine: PIL suggests pillow", dc.dist_for_import("PIL") == "pillow")
check("engine: yaml suggests pyyaml",
      dc.dist_for_import("yaml") == "pyyaml")

# --------------------------------------------------- deps fix (live)
ws = os.path.join(HOME, "ws-v370")
os.makedirs(ws, exist_ok=True)
with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
    fh.write("import yaml\nimport httpx\n")
with open(os.path.join(ws, "requirements.txt"), "w", encoding="utf-8") as fh:
    fh.write("PyYAML\n")

logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
app.project_dir = ws
try:
    app.handle_terminal_command("deps fix")
    app.root.update()
    body = open(os.path.join(ws, "requirements.txt"),
                encoding="utf-8").read()
    check("deps fix: httpx appended to requirements.txt",
          "httpx" in body and "# added by deps on" in body)
    check("deps fix: pyyaml NOT duplicated (PyYAML satisfies yaml)",
          body.lower().count("pyyaml") == 1)
    check("deps fix: terminal announces the pin",
          any("added 1 pin(s)" in s and "httpx" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("deps fix")
    check("deps fix: second run says nothing to add",
          any("nothing to add" in s for s in logs))

    # fix creates requirements.txt when none exists, using the alias
    ws2 = os.path.join(HOME, "ws-v370-bare")
    os.makedirs(ws2, exist_ok=True)
    with open(os.path.join(ws2, "only.py"), "w", encoding="utf-8") as fh:
        fh.write("import yaml\n")
    logs.clear()
    app.project_dir = ws2
    app.handle_terminal_command("deps fix")
    body2 = open(os.path.join(ws2, "requirements.txt"),
                 encoding="utf-8").read()
    check("deps fix: creates the file on demand",
          os.path.isfile(os.path.join(ws2, "requirements.txt")))
    check("deps fix: pins pyyaml (the dist), not yaml (the import)",
          "pyyaml" in body2 and "yaml\n" not in body2.replace(
              "pyyaml", ""))
finally:
    app.terminal.log = _real_tlog

# ------------------------------------------------------- help <verb>
logs = []
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
try:
    app.handle_terminal_command("help deps")
    check("help: `help deps` prints the deps row",
          any("cross-check imports" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("help session")
    check("help: `help session` prints several rows",
          sum("session" in s.lower() for s in logs) >= 2)
    logs.clear()
    app.handle_terminal_command("help zzzqqqxxx")
    check("help: unknown verb gets the honest line",
          any("No help for" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("help")
    check("help: bare `help` still lists everything",
          any("Studio commands:" in s for s in logs)
          and sum(" — " in s for s in logs) >= 30)
    check("helper: fuzzy `dps` finds deps",
          matching_help_rows("dps")[0][0] == "deps")
finally:
    app.terminal.log = _real_tlog

# --------------------------------------------------- Workshop menu
_labels = []


def _walk(menu, depth=0):
    if menu is None or depth > 4:
        return
    try:
        n = menu.index("end") or 0
    except Exception:  # noqa: BLE001
        return
    for i in range(n + 1):
        try:
            ent = menu.entrycget(i, "label")
            if ent:
                _labels.append(str(ent))
            sub = app.root.nametowidget(str(menu.entrycget(i, "menu")))
            _walk(sub, depth + 1)
        except Exception:  # noqa: BLE001 — separators etc.
            continue


try:
    for _child in app.menu_bar.winfo_children():
        try:
            _walk(app.root.nametowidget(str(_child.cget("menu"))))
        except Exception:  # noqa: BLE001 — non-menu children
            continue
except Exception:  # noqa: BLE001
    pass
check("workshop menu: Dependency Check present",
      any("Dependency Check" in s for s in _labels))

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
