"""DS2 v2.66.0 UI smoke — the window manager's memory: `tools
layout save <name>` snapshots every open tool window's title and
geometry into the config store (same name overwrites, oldest falls
off past 12); `tools layout <name>` (or `restore <name>`, spaces
included) hands each saved geometry back to the live window whose
title matches exact-first then substring — a saved window that is
not open is reported missing by name, never conjured; `tools layout
list` shows the book; `tools layout forget <name|all>` forgets
without touching the windows.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v660.py

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
from dxn1_studio.geom import (capture_layout, store_layout,  # noqa: E402
                              apply_layout, LAYOUT_CAP)

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

verbs_list = [r[0] for r in TERMINAL_HELP]
check("TERMINAL_HELP knows tools layout",
      "tools layout <name>" in verbs_list)

logs = []
_old_log = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))


def dispatch(cmd):
    logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(logs)


# ------------------------------------- honest empty answers
check("bare verb teaches its usage",
      "usage: tools layout save" in dispatch("tools layout"))
check("saving an empty desk is refused honestly",
      "none open" in dispatch("tools layout save desk"))

# ------------------------------------- save two windows
w1 = tk.Toplevel(root)
w1.title("Chart Studio")
w1.transient(root)
w1.geometry("760x560+10+10")
w2 = tk.Toplevel(root)
w2.title("Terminal")
w2.transient(root)
w2.geometry("860x520+30+30")
root.update()
blob = dispatch("tools layout save desk")
check("save reports what it remembers", "remembers 2 windows" in blob)
check("the store persisted through the app config",
      "desk" in (app.config.get("tool_window_layouts") or {}))

# ------------------------------------- recall by the bare name
w1.geometry("1x1+400+400")
w2.geometry("1x1+400+400")
root.update()
blob = dispatch("tools layout desk")
check("bare-name restore reports the count",
      "2 windows back in place" in blob)
check("window 1 is exactly back", w1.winfo_geometry() == "760x560+10+10")
check("window 2 is exactly back", w2.winfo_geometry() == "860x520+30+30")

# ------------------------------------- names with spaces + restore verb
blob = dispatch("tools layout save my desk")
check("a name with spaces saves", "remembers 2 windows" in blob)
w1.geometry("1x1+0+0")
root.update()
check("`restore <name>` works with spaces",
      "2 windows back in place" in dispatch(
          "tools layout restore my desk"))

# ------------------------------------- the book
blob = dispatch("tools layout list")
check("list shows every layout",
      "2 remembered" in blob and "my desk · 2 windows" in blob)

# ------------------------------------- missing honesty
w1.destroy()
root.update()
blob = dispatch("tools layout desk")
check("partial restore reports the count",
      "1 window back in place" in blob)
check("the closed window is reported missing by name",
      "not open: Chart Studio" in blob)
check("nothing was conjured", not w1.winfo_exists())

# ------------------------------------- forgetting
check("unknown layout answered honestly",
      "not remembered" in dispatch("tools layout nope"))
check("forget removes one",
      "'desk' is gone" in dispatch("tools layout forget desk"))
check("forgetting twice is honest",
      "not a remembered layout" in dispatch("tools layout forget desk"))
check("forget all reports the count",
      "1 layout forgotten" in dispatch("tools layout forget all"))
check("forget all on an empty book",
      "0 layouts forgotten" in dispatch("tools layout forget all"))

# ------------------------------------- engine regression (pure math)
class _W:
    def __init__(self, t, g):
        self._t, self._g = t, g

    def title(self):
        return self._t

    def winfo_geometry(self):
        return self._g

    def transient(self):
        return True


_snap = capture_layout([_W("A", "10x10+1+1"), _W("B", "20x20+2+2")])
check("capture keeps titles and geometry",
      [e["title"] for e in _snap] == ["A", "B"]
      and _snap[0]["geometry"] == "10x10+1+1")
_store = {}
for i in range(LAYOUT_CAP + 5):
    store_layout(_store, "l%d" % i, _snap)
check("the LRU cap holds", len(_store) == LAYOUT_CAP)
_rest, _miss = apply_layout(_snap, [_W("a", "1x1+0+0"),
                                    _W("XB", "1x1+0+0")])
check("exact match beats the substring impostor",
      [t for t, _g in _rest] == ["A", "B"] and _miss == [])

# ------------------------------------- docs consistency
_ft = open(os.path.join("docs", "FEATURES.md"), encoding="utf-8").read()
check("FEATURES.md speaks the layouts",
      "tools layout" in _ft and "arranges what exists" in _ft)
_arch = open(os.path.join("docs", "ARCHITECTURE.md"),
             encoding="utf-8").read()
check("ARCHITECTURE.md lists smoke_v660", "smoke_v660" in _arch)
_chlog = open("CHANGELOG.md", encoding="utf-8").read()
_ver = __import__("dxn1_studio").APP_VERSION
check("CHANGELOG has 2.66.0", "## [2.66.0]" in _chlog)
check("studio version lives on top of the CHANGELOG",
      _ver > "2.66.0" and "## [%s]" % _ver in _chlog)

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
