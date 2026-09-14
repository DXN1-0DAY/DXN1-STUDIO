"""DS2 v2.32.0 UI smoke — crash-safe session autosave (60s cycle) and
the engine-snapshot recovery path after a simulated crash.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v320.py

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


# --------------------------------------------------------- installer flag
_r = subprocess.run(["bash", "install.sh", "--version"],
                    capture_output=True, text=True)
check("install.sh: --version prints 2.32.0",
      _r.returncode == 0 and "2.32.0" in _r.stdout)
_r2 = subprocess.run(["bash", "install.sh", "-V"],
                     capture_output=True, text=True)
check("install.sh: -V alias works", _r2.returncode == 0)

# --------------------------------------------------------------- defaults
from dxn1_studio.config import Config, DEFAULTS  # noqa: E402

check("config: session_autosave defaults on",
      bool(DEFAULTS.get("session_autosave")))
check("config: autosave interval default 60",
      int(DEFAULTS.get("session_autosave_secs", 0)) == 60)

# ----------------------------------------------------------------- boot 1
_cfg_dir = os.path.join(HOME, ".dxn1-studio")
os.makedirs(_cfg_dir, exist_ok=True)
with open(os.path.join(_cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"onboarded": True, "hub_on_startup": False,
               "check_updates": False}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.app import DXN1Studio  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

# ------------------------------------------------------------ fixtures
tmp = tempfile.mkdtemp(prefix="ds2-v320-")
app.project_dir = tmp
f1 = os.path.join(tmp, "alpha.py")
with open(f1, "w", encoding="utf-8") as fh:
    fh.write("def one():\n    pass\n\n"
             "# pad 4\n# pad 5\n# pad 6\n# pad 7\n# pad 8\n")
f2 = os.path.join(tmp, "beta.py")
with open(f2, "w", encoding="utf-8") as fh:
    fh.write("BETA = 1\nline2\nline3\n")

app.open_file(f1)
app.open_file(f2)          # beta active now
app._activate_tab(f1)      # alpha active, cursor parked below
app.root.update()
app.editor.text.mark_set("insert", "7.3")
app.root.update()

# ------------------------------------------------------ autosave write
from dxn1_studio import session as sess  # noqa: E402

spath = sess.session_path(tmp)
if os.path.exists(spath):                    # clean slate
    os.remove(spath)
app._autosave_session()                      # direct call — never raises
check("autosave: session file written", os.path.isfile(spath))
snap = sess.load(tmp)
curs = (snap or {}).get("cursor") or {}
check("autosave: tabs + active captured",
      str(f1) in (snap or {}).get("tabs", [])
      and (snap or {}).get("active") == str(f1))
check("autosave: cursor line 7 merged",
      (curs.get(f1) or {}).get("line") == 7)
check("autosave: reschedule job set",
      bool(getattr(app, "_session_autosave_job", None)))

# switch off → snapshot untouched
before = open(spath, "r", encoding="utf-8").read()
app.config.set("session_autosave", False)
app._autosave_session()
check("autosave: off switch silences writes",
      open(spath, "r", encoding="utf-8").read() == before)
app.config.set("session_autosave", True)
for junk in ("0", "nonsense", 99999):        # junk intervals never raise
    app.config.set("session_autosave_secs", junk)
    app._autosave_session()
check("autosave: junk intervals survive",
      bool(getattr(app, "_session_autosave_job", None)))

# --------------------------------------- simulated crash + recovery boot
try:                      # crash = no _on_close, root just dies
    app.root.destroy()
except Exception:  # noqa: BLE001
    pass
try:
    app.root.update()     # dead root is expected here
except Exception:  # noqa: BLE001
    pass

app2 = DXN1Studio(Config(), no_splash=True)
app2.root.update()
if app2._hub is not None and app2._hub.winfo_exists():
    app2._on_hub_explore()
app2.root.update()
app2.project_dir = tmp
app2._restore_engine_session(tmp)            # recovery path
app2.root.update()
check("recovery: both tabs reopened",
      str(f1) in app2._tab_frames and str(f2) in app2._tab_frames)
check("recovery: active file focused", app2.editor.file_path == str(f1))
check("recovery: cursor 7.3 restored",
      app2.editor.text.index("insert") == "7.3")
check("recovery: per-buffer map seeded",
      app2._buffer_cursors.get(str(f2)) == "4.0")  # beta opens at end
app2._activate_tab(str(f2))
app2.root.update()
check("recovery: beta keeps 4.0 on switch",
      app2.editor.text.index("insert") == "4.0")

# close hook still writes the shared snapshot (v2.30 behaviour intact)
app2._activate_tab(str(f2))
app2.root.update()
app2.editor.text.mark_set("insert", "3.0")   # current insert wins
try:
    app2._on_close()
except Exception:  # noqa: BLE001 — destroy-time noise is fine
    pass
snap2 = sess.load(tmp)
curs2 = (snap2 or {}).get("cursor") or {}
check("close hook: snapshot still saved", bool(snap2))
check("close hook: beta cursor line 3",
      (curs2.get(str(f2)) or {}).get("line") == 3)

# ------------------------------------------------------------- cleanup
try:
    sess.clear(tmp)
except Exception:  # noqa: BLE001
    pass
shutil.rmtree(os.path.join(_cfg_dir, "sessions"), ignore_errors=True)
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
