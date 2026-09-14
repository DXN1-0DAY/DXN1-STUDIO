"""DS2 v2.33.0 UI smoke — "save session now": palette/terminal/chip
surface on top of the v2.32 crash-safe autosave.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v330.py

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
from dxn1_studio.app import DXN1Studio  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

# ------------------------------------------------------------- the chip
check("session chip: exists on the statusbar",
      app.status_sesave.winfo_exists())
check("session chip: quiet at boot",
      str(app.status_sesave.cget("text")) == "")
check("session chip: click-to-save bound",
      bool(app.status_sesave.bind("<Button-1>")))

# ------------------------------------------------------------ fixtures
tmp = tempfile.mkdtemp(prefix="ds2-v330-")
app.project_dir = tmp
f1 = os.path.join(tmp, "alpha.py")
with open(f1, "w", encoding="utf-8") as fh:
    fh.write("def one():\n    pass\n\n"
             "# pad 4\n# pad 5\n# pad 6\n# pad 7\n# pad 8\n")
app.open_file(f1)
app.root.update()
app.editor.text.mark_set("insert", "7.3")

# --------------------------------------------------------- save now
from dxn1_studio import session as sess  # noqa: E402

spath = sess.session_path(tmp)
if os.path.exists(spath):
    os.remove(spath)
app.save_session_now()
check("save now: snapshot on disk", os.path.isfile(spath))
snap = sess.load(tmp)
check("save now: active file + cursor captured",
      (snap or {}).get("active") == str(f1)
      and ((snap or {}).get("cursor") or {}).get(f1, {}).get("line") == 7)
check("save now: chip painted with stamp",
      "session saved" in str(app.status_sesave.cget("text")))
check("save now: chip glows accent",
      str(app.status_sesave.cget("fg")) == str(app.theme.accent))
check("save now: muted fade scheduled",
      bool(getattr(app, "_sesave_job", None)))

# ------------------------------------------------- terminal verb
app.handle_terminal_command("session save")
check("terminal: `session save` reaches the snapshot",
      "session saved" in str(app.status_sesave.cget("text")))

# ------------------------------------------------- autosave paints too
app.config.set("session_autosave", True)
app.config.set("restore_session", True)
app._autosave_session()
check("autosave: chip updated by the 60s cycle",
      "session saved" in str(app.status_sesave.cget("text")))

# ------------------------------------------------- palette entry
app.open_palette()
pal = app._palette
pal.entry.delete(0, tk.END)
pal.entry.insert(0, "save ssion")     # fuzzy: "save session now"
pal._on_type()
pal.rows.update_idletasks()
rows = pal.rows.winfo_children()
check("palette: `save ssion` has rows", len(rows) >= 1)
texts = "".join(str(w.cget("text")) for w in rows[0].winfo_children())
check("palette: top hit is Save Session Now",
      "save session now" in texts.lower())
pal.close()
app.root.update()

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
