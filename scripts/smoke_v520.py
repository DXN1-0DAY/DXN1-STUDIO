"""DS2 v2.52.0 UI smoke — the chip menus learn the keyboard: a real
pointer gesture keeps Tk's grab while the menu is up (that grab is
what routes keys to it — the old release-immediately left every chip
menu mouse-only), an unpost poller releases it and records the focus
hand-back, the first activatable row wakes up active so Enter takes
it, Home/End/digits 1-9 drive real rows, programmatic opens (no
event) release the grab at once, the git chip menu's sync rows wear
the branch's divergence (red diverged, amber one move from sync),
and the nightly-snapshot interval becomes a real Settings picker
that clamps and junk-proofs.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v520.py

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
from dxn1_studio.app import DXN1Studio, accel_pattern  # noqa: E402
from dxn1_studio.activity import autosnap_due  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

root = app.root


def grab_path():
    # raw Tcl: the grab registry is display-global and a cross-interp
    # nametowidget raises (probe lesson r2)
    return str(root.tk.call("grab", "current", "."))


class _Ev:
    """A real pointer gesture, like Button-3 carries."""
    x_root = 42
    y_root = 42


# --- the keyboard fix: a gesture keeps the grab, keys can arrive
ran = []
entries = [("First", lambda: ran.append("first")),
           ("Second", lambda: ran.append("second")),
           ("---", None),
           ("Third", lambda: ran.append("third"))]
app._render_chip_menu(entries, _Ev())
root.update()
m = app._last_chip_menu
check("gesture open: menu posted", m is not None and m.winfo_ismapped())
check("gesture open: the grab is held (keys can reach it)",
      grab_path() == str(m))
check("the first activatable row wakes up active",
      m.index("active") == 0)
check("the rows are introspectable promises",
      [e[0] for e in getattr(m, "_ds2_rows", [])] ==
      ["First", "Second", "---", "Third"])
check("separators never count as rows",
      app._menu_command_rows(m) == [0, 1, 3])
check("Home/End/digit binds really exist",
      bool(m.bind("<Key-Home>")) and bool(m.bind("<Key-End>"))
      and bool(m.bind("<Key-5>")))
m.unpost()
root.update()
m._ds2_poll()
root.update()
check("the poller releases the grab the moment the menu unposts",
      grab_path() == "")

# --- the keys drive real rows
app._render_chip_menu(entries, _Ev())
root.update()
m = app._last_chip_menu
m._ds2_keys["end"]()
root.update()
check("End lands on the last row", m.index("active") == 3)
m._ds2_keys["home"]()
root.update()
check("Home lands on the first row", m.index("active") == 0)
m._ds2_keys["nth"](2)()
root.update()
check("digit 2 runs the second COMMAND (separator never counts)",
      ran == ["second"] and m.index("active") == 1)
m._ds2_keys["nth"](9)()
check("a digit beyond the end is a no-op", ran == ["second"])
app._dismiss_chip_menu()
root.update()

# --- the natural 40ms poll also releases once unposted
app._render_chip_menu(entries, _Ev())
root.update()
m = app._last_chip_menu
m.unpost()
deadline = time.time() + 2.0
while time.time() < deadline and grab_path():
    root.update()
    time.sleep(0.03)
root.update()
check("the natural poll releases on its own cadence",
      grab_path() == "")

# --- a programmatic open (event=None) never holds the grab
app._render_chip_menu(entries, None)
root.update()
m = app._last_chip_menu
check("programmatic open: menu still posts", m.winfo_ismapped())
check("programmatic open: nothing outlives the call",
      grab_path() == "")
app._dismiss_chip_menu()
root.update()

# --- an empty menu never raises and answers honestly
app._render_chip_menu([("---", None)], _Ev())
root.update()
m = app._last_chip_menu
check("an empty menu posts without raising", m.winfo_ismapped())
check("an empty menu owns no rows", app._menu_command_rows(m) == [])
app._dismiss_chip_menu()
root.update()

# --- every real chip menu still serves its rows, now keyboard-ready
ok = True
for opener in (app._git_chip_menu, app._deps_chip_menu,
               app._scribe_chip_menu, app._sesave_chip_menu):
    app._dismiss_chip_menu()
    root.update()
    opener(_Ev())
    root.update()
    mm = app._last_chip_menu
    ok = ok and mm is not None and mm.winfo_ismapped() \
        and grab_path() == str(mm) and mm.index("active") is not None
app._dismiss_chip_menu()
root.update()
check("all four chip menus open grabbed and keyboard-ready", ok)

# --- the git menu wears the branch's divergence
app._git_watch_state = lambda: {"repo": True, "branch": "main",
                                "dirty": 0, "ahead": 1, "behind": 0}
app._render_chip_menu(app._git_menu_entries(), _Ev())
root.update()
mg = app._last_chip_menu
gcmds = [e for e in mg._ds2_rows if e[0] != "---"]
gpos = gcmds.index(next(e for e in gcmds if e[0] == "Push to origin"))
gpull = gcmds.index(next(e for e in gcmds
                         if e[0] == "Pull from upstream"))
grow = app._menu_command_rows(mg)[gpos]
check("ahead-only: Push to origin wears amber",
      str(mg.entrycget(grow, "foreground")) == "#f59e0b"
      and gcmds[gpos][3] == "#f59e0b")
check("ahead-only: Pull from upstream stays silent",
      gcmds[gpull][3] is None)
app._git_watch_state = lambda: {"repo": True, "branch": "main",
                                "dirty": 0, "ahead": 1, "behind": 2}
app._render_chip_menu(app._git_menu_entries(), _Ev())
root.update()
md = app._last_chip_menu
dcmds = [e for e in md._ds2_rows if e[0] != "---"]
check("diverged: both sync rows wear red",
      all(e[3] == "#f85149" for e in dcmds
          if e[0] in ("Push to origin", "Pull from upstream")))
app._git_watch_state = lambda: {"repo": True, "branch": "main",
                                "dirty": 0, "ahead": 0, "behind": 0}
app._render_chip_menu(app._git_menu_entries(), _Ev())
root.update()
ms = app._last_chip_menu
scmds = [e for e in ms._ds2_rows if e[0] != "---"]
check("in sync: both sync rows stay silent",
      all(e[3] is None for e in scmds
          if e[0] in ("Push to origin", "Pull from upstream")))
app._git_watch_state = lambda: None
app._render_chip_menu(app._git_menu_entries(), _Ev())
root.update()
mp = app._last_chip_menu
check("a plain folder offers no sync rows at all",
      all(e[0] not in ("Push to origin", "Pull from upstream")
          for e in mp._ds2_rows))
app._dismiss_chip_menu()
root.update()

# --- the interval picker: reads config, clamps, junk-proofs
app.config.set("activity_autosnap_hours", 7)
from dxn1_studio.app import SettingsDialog  # noqa: E402
dlg = SettingsDialog(app)
root.update()
check("the picker reads the saved interval",
      dlg.activity_hours_v.get() == "7")
dlg.activity_hours_v.set("999")
dlg._save()
check("saving 999 clamps to 168",
      app.config.get("activity_autosnap_hours") == 168)
dlg2 = SettingsDialog(app)
dlg2.activity_hours_v.set("banana")
dlg2._save()
check("saving junk lands on 24",
      app.config.get("activity_autosnap_hours") == 24)
dlg3 = SettingsDialog(app)
dlg3.activity_hours_v.set("0")
dlg3._save()
check("saving 0 clamps up to 1",
      app.config.get("activity_autosnap_hours") == 1)

# the engine honors the saved interval, and the verb names it
app.config.set("activity_autosnap_hours", 1)
app.config.set("activity_autosnap", True)
app.config.set("activity_autosnap_last", 0.0)
check("the engine honors a 1h gate",
      autosnap_due(app.config, now=2 * 3600.0) is True)
_real_log = app.terminal.log
_seen = []
app.terminal.log = lambda msg, *a, **k: _seen.append(str(msg))
try:
    app.handle_terminal_command("activity auto")
finally:
    app.terminal.log = _real_log
check("bare `activity auto` names the interval",
      any("every 1h" in s for s in _seen), )
app.config.set("activity_autosnap", False)

# --- source agreement: the contract is written down
_src = {}
for _name in ("app.py",):
    with open(os.path.join("dxn1_studio", _name), encoding="utf-8") as fh:
        _src[_name] = fh.read()
_ap = _src["app.py"]
check("source: the gesture gate is real",
      "if event is None:\n                    menu.grab_release()" in _ap)
check("source: the unpost poller is armed",
      "self._arm_menu_unpost_poll(menu, prev_focus)" in _ap
      and "menu._ds2_poll = lambda: poll(attempts)" in _ap)
check("source: the focus hand-back is recorded",
      "menu._ds2_focus_back = prev_focus" in _ap)
check("source: Home/End/digits are wired on the menu",
      'menu.bind("<Key-Home>", _home)' in _ap
      and 'menu.bind("<Key-End>", _end)' in _ap
      and 'menu.bind("<Key-%d>" % d, _run_nth(d))' in _ap)
check("source: the quit path puts the menu away first",
      "def _dismiss_chip_menu(self):" in _ap
      and "self._dismiss_chip_menu()" in _ap)
check("source: the sync rows carry their severity",
      '"#f85149" if diverged else' in _ap
      and "sync_c if ahead else None" in _ap)
check("source: the interval picker persists",
      "self.activity_hours_v = tk.StringVar" in _ap
      and 'cfg.set("activity_autosnap_hours", _snap_h)' in _ap)

# --- the keybindings doc agrees
with open(os.path.join("docs", "KEYBINDINGS.md"), encoding="utf-8") as fh:
    _kb = fh.read()
check("doc agreement: the v2.52 section exists",
      "## Chip menus (v2.52)" in _kb)
check("doc agreement: the new rows tell the truth",
      "`Home` / `End` | chip menus: first / last row" in _kb
      and "`1…9` | chip menus: run that row" in _kb)

# --- regression: the palette audit still passes
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
      % _audited, _audited >= 15 and not _broken)

# ------------------------------------------------------------- cleanup
app._dismiss_chip_menu()
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
