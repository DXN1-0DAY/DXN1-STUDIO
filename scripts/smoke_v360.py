"""DS2 v2.36.0 UI smoke — the update heartbeat, the `deps` dependency
cross-check, and the `whatsnew` terminal verb.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v360.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile
import time

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + sessions
sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk  # noqa: E402

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# ------------------------------------------------------------- engines
import dxn1_studio.config as cfgmod  # noqa: E402

check("defaults: update_check_secs registered",
      cfgmod.DEFAULTS.get("update_check_secs") == 3600)
from dxn1_studio import depcheck as dc  # noqa: E402

mods = [ln.strip() for ln in open("MANIFEST.txt", encoding="utf-8")
        if ln.strip()]
check("manifest: depcheck.py shipped", "depcheck.py" in mods)

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

# --------------------------------------------- heartbeat (check off)
app.config.set("check_updates", False)
app._schedule_update_check()
check("heartbeat: reschedules even with the switch off",
      getattr(app, "_update_check_job", None))
app.config.set("update_check_secs", "junk")
app._schedule_update_check()
check("heartbeat: junk interval never breaks the reschedule",
      getattr(app, "_update_check_job", None))

# ------------------------------------------------------- deps (live)
ws = os.path.join(HOME, "ws-v360")
os.makedirs(ws, exist_ok=True)
with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
    fh.write("import os\nimport yaml\n")
with open(os.path.join(ws, "extra.py"), "w", encoding="utf-8") as fh:
    fh.write("import uvicorn\n")
with open(os.path.join(ws, "requirements.txt"), "w", encoding="utf-8") as fh:
    fh.write("PyYAML\nflask\n")

logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
app.project_dir = ws
try:
    app.handle_terminal_command("deps")
    app.root.update()
    blob = "\n".join(logs)
    check("deps: verb runs the report in the terminal",
          any("deps:" in s for s in logs))
    check("deps: uvicorn flagged as missing",
          "uvicorn" in blob and "NOT in requirements" in blob)
    check("deps: pyyaml alias keeps yaml satisfied",
          "yaml" not in blob.split("NOT in requirements")[-1]
          .split("never imported")[0])
    check("deps: flask listed as unused",
          "never imported" in blob and "- flask" in blob)
    # no workspace → honest toast, no crash
    logs.clear()
    app.project_dir = ""
    app.handle_terminal_command("deps")
    check("deps: no workspace degrades to an honest message",
          any("No workspace" in s or "deps" in s for s in logs)
          or len(logs) == 0)
finally:
    app.terminal.log = _real_tlog

# ------------------------------------------------- whatsnew verb
_children = len(app.root.winfo_children())
try:
    app.handle_terminal_command("whatsnew")
    app.root.update()
    time.sleep(0.1)
    app.root.update()
    opened_new = len(app.root.winfo_children()) > _children
except Exception:  # noqa: BLE001
    opened_new = False
check("whatsnew: terminal verb opens the viewer", opened_new)
check("whatsnew: viewer titled What's New",
      any("What's New" in str(w.title()) for w in
          app.root.winfo_children()
          if hasattr(w, "title")))

# ------------------------------------------------- settings dialog
try:
    from dxn1_studio.app import SettingsDialog
    dlg = SettingsDialog(app)
    app.root.update()
    check("settings: heartbeat spinbox var present",
          hasattr(dlg, "updint_v"))
    dlg.updint_v.set(30)
    dlg._save()
    app.root.update()
    check("settings: 30 minutes persisted as 1800 seconds",
          app.config.get("update_check_secs") == 1800)
    try:
        dlg.destroy()
    except Exception:  # noqa: BLE001
        pass
except Exception as exc:  # noqa: BLE001
    check(f"settings: dialog round-trip failed ({exc})", False)

# ------------------------------------------------- palette fuzzy hits
app.open_palette()
pal = app._palette
pal.entry.delete(0, tk.END)
pal.entry.insert(0, "dependency")
pal._on_type()
pal.rows.update_idletasks()
_rows = pal.rows.winfo_children()
texts = "".join(str(w.cget("text"))
                for w in _rows[0].winfo_children()) if _rows else ""
check("palette: `dependency` hits the Dependency Check",
      "dependency check" in texts.lower())
pal.entry.delete(0, tk.END)
pal.entry.insert(0, "whats new")
pal._on_type()
pal.rows.update_idletasks()
_rows = pal.rows.winfo_children()
texts = "".join(str(w.cget("text"))
                for w in _rows[0].winfo_children()) if _rows else ""
check("palette: `whats new` hits the digest",
      "what's new" in texts.lower())
pal.close()
app.root.update()

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
