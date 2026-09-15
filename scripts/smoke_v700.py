"""DS2 v2.70.0 UI smoke — the chip menu admits the drift: the
windows chip menu's recall rows are marked fresh at every post —
`· as saved` when the live desk still matches the layout exactly,
`· drifted` when anything moved, closed or strayed in, and no mark
at all for a book that cannot be read (no well-formed snapshot, no
claim) — while the row still recalls, because a mark is garnish
and a recall is a promise.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v700.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + i18n dir
sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk  # noqa: E402

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# ------------------------------------- seed a quiet boot
_cfg_dir = os.path.join(HOME, ".dxn1-studio")
os.makedirs(_cfg_dir, exist_ok=True)
with open(os.path.join(_cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"onboarded": True, "hub_on_startup": False,
               "check_updates": False}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.config import Config  # noqa: E402
from dxn1_studio.app import DXN1Studio, TERMINAL_HELP, accel_pattern  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

logs = []
_old_log = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))


def dispatch(cmd):
    logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(logs)


def _recall_rows():
    return [e for e in app._wins_menu_entries()
            if e[0].startswith("Recall layout")]


w = tk.Toplevel(root)
w.title("Chart")
w.transient(root)
w.geometry("300x200+10+10")
root.update()
app.config.set("tool_window_layouts", {
    "clean": [{"title": "Chart", "geometry": "300x200+10+10",
               "transient": False}]})
_rows = _recall_rows()
check("an aligned desk is marked as saved",
      _rows and _rows[0][0].endswith("· as saved"))
check("the hint explains the mark",
      _rows and "drifted means the desk has moved" in _rows[0][4])
check("every command row still carries a hint",
      all(len(e) > 4 and e[4] for e in app._wins_menu_entries()
          if e[0] != "---"))

w.geometry("500x300+40+40")
root.update()
check("a wandered desk is marked drifted, fresh at every post",
      _recall_rows()[0][0].endswith("· drifted"))

w.destroy()
root.update()
check("a window closed behind the layout's back is drift too",
      _recall_rows()[0][0].endswith("· drifted"))

app.config.set("tool_window_layouts", {
    "junk": "banana",
    "mixed": [None, {"title": "Chart", "geometry": "1x1+0+0",
                     "transient": True}]})
_rows = _recall_rows()
check("a book that cannot be read makes no claim at all",
      len(_rows) == 2
      and all("·" not in r[0].split(") ", 1)[-1] for r in _rows)
      and "junk' (0 window" in " ".join(r[0] for r in _rows))

# the mark is garnish: the row still recalls for real
app.config.set("tool_window_layouts", {
    "recallable": [{"title": "Recall probe",
                    "geometry": "400x300+30+30",
                    "transient": False}]})
_probe = tk.Toplevel(root)
_probe.title("Recall probe")
_probe.transient(root)
_probe.geometry("1x1+0+0")
root.update()
_recall = [e for e in app._wins_menu_entries()
           if e[0].startswith("Recall layout 'recallable'")][0]
_recall[1]()
check("the marked row still dispatches the real restore",
      "back in place" in "\n".join(logs)
      and _probe.winfo_geometry() == "400x300+30+30")
_probe.destroy()
dispatch("tools layout forget all")

# ------------------------------------- docs & versions
_ft = open(os.path.join("docs", "FEATURES.md"), encoding="utf-8").read()
check("FEATURES.md speaks the drift marks",
      "as saved" in _ft and "drifted" in _ft)
_arch = open(os.path.join("docs", "ARCHITECTURE.md"),
             encoding="utf-8").read()
check("ARCHITECTURE.md lists smoke_v700", "smoke_v700" in _arch)
_chlog = open("CHANGELOG.md", encoding="utf-8").read()
_ver = __import__("dxn1_studio").APP_VERSION
check("CHANGELOG has 2.70.0", "## [2.70.0]" in _chlog)
check("studio version lives on top of the CHANGELOG",
      _ver >= "2.70.0" and "## [%s]" % _ver in _chlog)

# ------------------------------------- regression: the palette audit
_audited, _broken = 0, []
for _label, _hint, _fn in app.palette_commands():
    if not str(_hint or "").startswith(("Ctrl", "Alt", "F")):
        continue
    _pat = accel_pattern(_hint)
    if not _pat or not root.bind(_pat):
        _broken.append((_label, _hint))
    else:
        _audited += 1
check("regression: the palette audit still passes (%d audited)"
      % _audited, _audited >= 19 and not _broken)

# ------------------------------------- cleanup
app.terminal.log = _old_log
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
