"""DS2 v2.47.0 UI smoke — honest keys and a quieter voice: every
accelerator the palette advertises is a binding the code really has
(`accel_pattern` + `looks_like_accel`), the git chip menu advertises
Enter-to-commit only where a repo exists, a muted toast kind keeps
its receipt while the screen stays quiet (Settings Toasts section
round-trips), and the receipts export follows the file's extension
(.json / .csv / text diary) through the verbs and the Save-as
dialog.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v470.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + activity
sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk  # noqa: E402

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# ------------------------------------- seed a previous session's receipts
_cfg_dir = os.path.join(HOME, ".dxn1-studio")
os.makedirs(_cfg_dir, exist_ok=True)
with open(os.path.join(_cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"onboarded": True, "hub_on_startup": False,
               "check_updates": False}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.config import Config  # noqa: E402
from dxn1_studio.app import (DXN1Studio, SettingsDialog,  # noqa: E402
                             accel_pattern, looks_like_accel)
import dxn1_studio.activity as act_mod  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

_logs = []
app.terminal.log = lambda s, *a, **k: _logs.append(str(s))


def _walk_all(w):
    yield w
    for c in w.winfo_children():
        yield from _walk_all(c)

# --------------------------------------------- lane A: honest keys
audited = 0
_broken = []
for _label, _hint, _fn in app.palette_commands():
    if not looks_like_accel(_hint):
        continue
    _pat = accel_pattern(_hint)
    if not _pat or not app.root.bind(_pat):
        _broken.append((_label, _hint))
    else:
        audited += 1
check("keys: every advertised palette accel is really bound (%d audited)"
      % audited, audited >= 15 and not _broken)
check("keys: category tags are never chased as bindings",
      not looks_like_accel("DS2") and not looks_like_accel("line 42")
      and looks_like_accel("Ctrl+S") and looks_like_accel("F5"))

_repo = os.path.join(HOME, "repo")
os.makedirs(_repo, exist_ok=True)
subprocess.run(["git", "init", "-q"], cwd=_repo)
subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=t",
                "commit", "-qm", "x", "--allow-empty"], cwd=_repo)
app.project_dir = _repo
_commit_rows = [e for e in app._git_menu_entries()
                if e[0] == "Commit staged…"]
check("keys: the git menu advertises Enter where a repo exists",
      bool(_commit_rows) and len(_commit_rows[0]) == 3
      and _commit_rows[0][2] == "Enter")
_src = open("dxn1_studio/app.py", encoding="utf-8").read()
check("keys: the shared renderer passes accelerators to the real menu",
      "accelerator=accel" in _src)
_doc = open("docs/KEYBINDINGS.md", encoding="utf-8").read()
check("keys: the keybindings doc agrees with the code",
      "`Ctrl+Shift+D` | Duplicate line" in _doc
      and "`Ctrl+Shift+K` | Delete line" in _doc
      and "`Ctrl+D` | Duplicate line" not in _doc)

# --------------------------------------------- lane B: the quiet kind
app.config.set("toast_show_error", False)
_cards0 = len(app.toast_layer.winfo_children())
app.toast("hushed error", "error")
app.root.update()
check("mute: a muted error keeps its receipt",
      app.activity_log.entries()[0]["message"] == "hushed error"
      and app.activity_log.entries()[0]["kind"] == "error")
check("mute: but the screen stays quiet",
      len(app.toast_layer.winfo_children()) == _cards0)
app.config.set("toast_show_error", True)
app.toast("loud success", "success")
app.root.update()
check("mute: an unmuted kind still shows its card",
      len(app.toast_layer.winfo_children()) == _cards0 + 1)

_dlg = SettingsDialog(app)
app.root.update()
_has = (hasattr(_dlg, "toastinfo_v") and hasattr(_dlg, "toastsuccess_v")
        and hasattr(_dlg, "toasterror_v"))
_dlg.toastinfo_v.set(False)
_dlg.toastsuccess_v.set(False)
_dlg._save()
app.root.update()
check("settings: the Toasts section persists both ways",
      _has and app.config.get("toast_show_info") is False
      and app.config.get("toast_show_error") is True)
app.config.set("toast_show_info", True)
app.config.set("toast_show_success", True)

# --------------------------------------------- lane C: your format
app.toast("csv me", "info")
app.handle_terminal_command("activity export json")
app.root.update()
_made_json = [f for f in os.listdir(_cfg_dir)
              if f.startswith("activity-export-") and f.endswith(".json")]
_json_ok = False
if _made_json:
    _data = json.loads(open(os.path.join(_cfg_dir, _made_json[0]),
                            encoding="utf-8").read())
    _json_ok = (_data["version"] == 1
                and any(e["message"] == "csv me"
                        for e in _data["entries"]))
check("export: `activity export json` writes a loadable snapshot",
      _json_ok)

app.handle_terminal_command("activity export csv")
app.root.update()
_made_csv = [f for f in os.listdir(_cfg_dir)
             if f.startswith("activity-export-") and f.endswith(".csv")]
_csv_ok = False
if _made_csv:
    _lines = open(os.path.join(_cfg_dir, _made_csv[0]),
                  encoding="utf-8").read().splitlines()
    _csv_ok = (_lines[0] == "stamp,kind,message"
               and any("csv me" in ln for ln in _lines[1:]))
check("export: `activity export csv` writes the sheet with a header",
      _csv_ok)

_explicit = os.path.join(HOME, "forced.txt")
app.handle_terminal_command("activity export csv %s" % _explicit)
app.root.update()
check("export: an explicit fmt overrides the extension",
      os.path.isfile(_explicit)
      and open(_explicit, encoding="utf-8").read()
      .splitlines()[0] == "stamp,kind,message")

# the window's Save-as… follows a typed .csv extension too
_wout = []
_win = act_mod.open_activity(app.root, app.theme, app.activity_log,
                             export_dir=_cfg_dir, on_export=_wout.append)
app.root.update()
_target = os.path.join(HOME, "typed-receipts.csv")
_real_fd = act_mod.filedialog
act_mod.filedialog = SimpleNamespace(
    asksaveasfilename=lambda **k: str(_target))
try:
    _btn = [w for w in _walk_all(_win) if isinstance(w, tk.Label)
            and str(w.cget("text")) == "Save as file…"]
    if _btn:
        _btn[0].event_generate("<Button-1>")
        app.root.update()
finally:
    act_mod.filedialog = _real_fd
_csv2 = (os.path.isfile(_target)
         and open(_target, encoding="utf-8").read()
         .splitlines()[0] == "stamp,kind,message")
check("window: Save-as… follows the typed .csv extension", _csv2)
_win.destroy()

_rows = [r[0] for r in __import__("dxn1_studio.app",
                                  fromlist=["TERMINAL_HELP"])
         .TERMINAL_HELP]
check("help: the export verb documents the formats",
      "activity export [json|csv] [path]" in _rows)
check("wiring: the toast gate sits after the archive hook",
      "toast_show_%s" in _src
      and _src.index("log.add(message, kind)")
      < _src.index('toast_show_%s" % kind'))
check("wiring: the verbs route through export_to",
      "from .activity import export_to" in _src)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
