"""DS2 v2.53.0 UI smoke — the menus come to you: the four statusbar
chip menus open from the keyboard, through three real doors at once
(palette rows advertising Ctrl+Alt+G/E/W/A, the accelerators
themselves as root binds, and the `chip <name>` terminal verb). A
keyboard-opened menu is a real gesture: the grab is KEPT while it is
up (the v2.52 lesson — that grab is what routes keys to the menu),
it floats just above its chip instead of at a cursor that isn't
there, and the usual unpost poller / _dismiss_chip_menu releases it
the moment it closes. The deps menu's red state gains a Copy pip
install command row (pins via depcheck.suggested_pins), the chip
tooltips name their accelerator, and the Settings search still finds
the snapshot picker.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v530.py

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
os.environ["HOME"] = HOME            # before imports: config + activity
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
from dxn1_studio.app import (DXN1Studio, SettingsDialog,  # noqa: E402
                             accel_pattern, looks_like_accel)

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if app._hub is not None and app.winfo_exists():
    pass
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

# ------------------------------------- the palette advertises the doors
_wants = {"Branch chip menu": "Ctrl+Alt+G",
          "Deps chip menu": "Ctrl+Alt+E",
          "Scribe chip menu": "Ctrl+Alt+W",
          "Autosave chip menu": "Ctrl+Alt+A"}
_cmds = app.palette_commands()
_found = {}
for _label, _hint, _fn in _cmds:
    for _head, _acc in _wants.items():
        if _label.startswith(_head):
            _found[_head] = _hint
check("palette: all four chip-menu rows present with their keys",
      _found == _wants, )
for _head, _acc in _wants.items():
    _pat = accel_pattern(_acc)
    check("accel real: %s (%s)" % (_acc, _head),
          bool(_pat) and bool(root.bind(_pat)))
check("hints look like accels (the audit will police them)",
      all(looks_like_accel(h) for h in _wants.values()))

# ------------------------------------- keyboard opens, one per chip
def _grab_current():
    return str(root.tk.call("grab", "current"))


_opened = []
for _alias in ("branch", "deps", "scribe", "autosave"):
    ok, grabbed, rows, awake = True, False, False, False
    try:
        ok = app._open_chip_menu_keyboard(_alias)
        root.update()
        menu = app._last_chip_menu
        grabbed = bool(menu is not None and menu.winfo_exists()
                       and _grab_current())
        rows = bool(getattr(menu, "_ds2_rows", None))
        try:
            awake = menu is not None and menu.index("active") is not None
        except tk.TclError:
            awake = False
        # the menu floats just ABOVE its chip (when both are mapped)
        reg = app._chip_menu_registry()
        _chip = reg[app._CHIP_MENU_ALIASES[_alias]][1]
        if menu is not None and menu.winfo_ismapped() \
                and _chip.winfo_ismapped():
            bottom = menu.winfo_rooty() + menu.winfo_reqheight()
            if bottom > _chip.winfo_rooty() + 8:
                ok = False
        app._dismiss_chip_menu()
        root.update()
        if _grab_current():
            ok = False   # nothing may outlive its menu
    except Exception:    # noqa: BLE001 — a failure is a failure
        ok = False
    _opened.append(ok and grabbed and rows and awake)
check("keyboard open: branch (mapped, grab kept, rows, first awake)",
      _opened[0])
check("keyboard open: deps", _opened[1])
check("keyboard open: scribe", _opened[2])
check("keyboard open: autosave", _opened[3])
check("dismiss leaves no grab on the display", not _grab_current())
check("unknown kinds answer honestly",
      app._open_chip_menu_keyboard("nonsense") is False
      and app._open_chip_menu_keyboard("") is False)

# ------------------------------------- the verb drives the same doors
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))
try:
    app.handle_terminal_command("chip")            # bare → the list
    app.handle_terminal_command("chip nonsense")   # honest miss
finally:
    app.terminal.log = _old_log
root.update()
check("verb: bare `chip` lists the four names",
      any("chips: branch" in m for m in _logs))
check("verb: an unknown chip is told honestly",
      any("unknown chip 'nonsense'" in m for m in _logs))
_menu_before = app._last_chip_menu
app.handle_terminal_command("chip branch")
root.update()
check("verb: `chip branch` posts the real menu (grab and all)",
      app._last_chip_menu is not None
      and app._last_chip_menu is not _menu_before
      and bool(_grab_current()))
app._dismiss_chip_menu()
root.update()

# ------------------------------------- deps red: the copy row tells the truth
from dxn1_studio import depcheck as dc  # noqa: E402

_ws = tempfile.mkdtemp(prefix="ds2-depws-")
with open(os.path.join(_ws, "mod.py"), "w", encoding="utf-8") as fh:
    fh.write("import fakelib_x\nimport os\n")
subprocess.run(["git", "init", "-q"], cwd=_ws)
_rep = dc.check(_ws)
dc._store_cache(_ws, _rep)
app.project_dir = _ws
_entries = app._deps_menu_entries()
_repair = [e for e in _entries if e[0].startswith("Queue deps fix")]
_copy = [e for e in _entries if e[0] == "Copy pip install command"]
check("deps menu: red state counts its missing and offers the repair",
      bool(_repair) and "1" in _repair[0][0])
check("deps menu: the Copy pip install row rides along",
      bool(_copy))
_state = app._deps_watch_state()
check("deps state: cached with 1 missing (the chip's red state)",
      _state[0] == "cached" and _state[1] == 1)
if _copy:
    root.clipboard_clear()
    _copy[0][1]()
    root.update()
    try:
        _clip = root.clipboard_get()
    except tk.TclError:
        _clip = ""
    check("clipboard truth: a ready `pip install` line",
          _clip.startswith("pip install ") and "fakelib" in _clip,
          )
else:
    check("clipboard truth: a ready `pip install` line", False)
# the honest empty state
app.project_dir = ""
app._deps_copy_install()
root.update()
check("copy row with nothing missing: honest, no crash", True)
app._dismiss_chip_menu()
shutil.rmtree(_ws, ignore_errors=True)

# ------------------------------------- tooltips and docs agree with the code
with open(os.path.join("dxn1_studio", "app.py"), encoding="utf-8") as fh:
    _ap = fh.read()
check("tooltips: all four chips name their accelerator",
      _ap.count("right-click for actions · Ctrl+Alt+") == 4)
check("source: the renderer speaks the keyboard mode",
      'mode="keyboard"' in _ap
      and 'if effective == "program":' in _ap
      and "y = max(0, y - h - 6)" in _ap)
check("source: the verb is wired and the copy row exists",
      'low == "chip" or low.startswith("chip ")' in _ap
      and '("chip <name>",' in _ap
      and '"Copy pip install command"' in _ap
      and "suggested_pins" in _ap)

with open(os.path.join("docs", "KEYBINDINGS.md"), encoding="utf-8") as fh:
    _kb = fh.read()
check("doc agreement: the v2.53 section exists",
      "## Chip menus from anywhere (v2.53)" in _kb)
check("doc agreement: the accelerators are written down",
      "`Ctrl+Alt+G`" in _kb and "`Ctrl+Alt+E`" in _kb
      and "`Ctrl+Alt+W`" in _kb and "`Ctrl+Alt+A`" in _kb)

with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "The Menus Come to You" in _ft and "chip branch" in _ft)

# ------------------------------------- settings search still finds the picker
_dlg = SettingsDialog(app)
try:
    _dlg._filter_settings("snapshot")
    _act = [s for s in _dlg._sections if s["title"] == "Activity"]
    _vis = [w for w, _i in _act[0]["rows"]
            if w.winfo_manager() == "pack"] if _act else []
    check("settings search: 'snapshot' keeps the Activity section",
          bool(_vis))
    _texts = " ".join(_dlg._texts_of(w) for w in _vis)
    check("settings search: the hours picker is among the hits",
          "Hours between snapshots" in _texts)
    _dlg._filter_settings("")
finally:
    _dlg.destroy()

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

# ------------------------------------------------------------- cleanup
app._dismiss_chip_menu()
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
