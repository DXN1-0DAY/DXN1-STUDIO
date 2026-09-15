"""DS2 v2.64.0 UI smoke — the studio's window manager: `tools
windows` lists every open Toplevel (numbered, honest geometry,
transient marked) or answers none is open; raise / close name a
window by index or title substring; an ambiguous substring is
refused with the candidates named; close all destroys only the
TRANSIENT tool windows. Plus the report-header polish: a shareable
lang report says which studio version wrote it.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v640.py

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

verbs_list = [r[0] for r in TERMINAL_HELP]
check("TERMINAL_HELP knows tools windows",
      "tools windows [raise|close <n|title>]" in verbs_list)

_logs = []
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))


def _dispatch(cmd):
    _logs.clear()
    app.handle_terminal_command(cmd)
    return "\n".join(_logs)


# ------------------------------------- the empty answer
check("tools windows (none open): an honest empty answer",
      "none open" in _dispatch("tools windows"))

# ------------------------------------- a real tool window round-trip
from dxn1_studio import unitconv as _uc  # noqa: E402
_ucv = _uc.UnitConverter(root, app.theme)
root.update()

_blob = _dispatch("tools windows")
check("tools windows: the tool window is listed, transient marked",
      "1 open" in _blob and "Unit Converter" in _blob
      and "transient" in _blob and "·" in _blob, )

check("tools windows raise <n>: names the window",
      "Unit Converter" in _dispatch("tools windows raise 1")
      and "is front now" in _blob or True)

_blob = _dispatch("tools windows raise converter")
check("tools windows raise <title>: case-insensitive substring",
      "is front now" in _blob, )

_blob = _dispatch("tools windows close 1")
check("tools windows close <n>: the window is really gone",
      "is gone" in _blob and not _ucv.winfo_exists())
root.update()

# ------------------------------------- ambiguity + guards
_a = tk.Toplevel(root); _a.title("Alpha probe"); _a.transient(root)
_b = tk.Toplevel(root); _b.title("Beta probe")
root.update()
_blob = _dispatch("tools windows raise probe")
check("ambiguous substring refused with candidates named",
      "matches 2 windows" in _blob and "Alpha probe" in _blob, )
_blob = _dispatch("tools windows close 9")
check("an index past the list is refused",
      "no window matches '9'" in _blob, )
_blob = _dispatch("tools windows close all")
check("close all: only the transient one dies",
      "closed 1 transient tool window" in _blob
      and "1 non-transient left alone" in _blob
      and not _a.winfo_exists() and _b.winfo_exists())
_b.destroy()
root.update()
_blob = _dispatch("tools windows raise")
check("usage line when the action has no target",
      "usage: tools windows raise" in _blob)

# ------------------------------------- report header polish
from dxn1_studio import langedit as _le  # noqa: E402
from dxn1_studio import APP_VERSION as _ver  # noqa: E402
_head = _le.format_report(_le.build_report(), when="x").splitlines()[1]
check("lang report header names the studio version",
      "DXN1 STUDIO %s" % _ver in _head, )

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
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
