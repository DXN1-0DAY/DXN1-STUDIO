"""DS2 v2.71.0 UI smoke — two saved layouts, compared book to
book: `tools layout diff <a> <b>` reports the windows standing
identically in both, the windows that changed (geometry AND layer
deltas named — ghost level and pin — because a layout is skin and
place alike), and the windows only one book knows. The single-name
live-diff form is tried FIRST so names with spaces keep working.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v710.py

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
from dxn1_studio.geom import layout_compare  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

check("TERMINAL_HELP teaches the two-name form",
      "diff <a> <b>" in dict(TERMINAL_HELP)["tools layout <name>"])

logs = []
_old_log = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))


def dispatch(cmd):
    logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(logs)


# ------------------------------------- the engine, pure
_A = [{"title": "Chart", "geometry": "300x200+10+10",
       "transient": False, "alpha": 1.0, "topmost": False},
      {"title": "Solo", "geometry": "100x100+0+0",
       "transient": True}]
_B = [{"title": "chart", "geometry": "500x300+40+40",
       "transient": False, "alpha": 0.4, "topmost": True},
      {"title": "Extra", "geometry": "9x9+1+1",
       "transient": True}]
check("changed windows name geometry AND layer deltas",
      layout_compare(_A, _B)[1]
      == [("Chart", "300x200+10+10", "500x300+40+40",
           "ghost solid → 40% · pin off → on")])
check("titles match case-insensitively, book to book",
      layout_compare(_A, _B)[0] == []
      and layout_compare(_A, _B)[2] == [("Solo", "100x100+0+0")]
      and layout_compare(_A, _B)[3] == [("Extra", "9x9+1+1")])
check("identical books agree completely",
      layout_compare(_A, [dict(e) for e in _A])
      == ([("Chart", "300x200+10+10"), ("Solo", "100x100+0+0")],
          [], [], []))
check("a layer-only change is still a change",
      layout_compare([{"title": "X", "geometry": "1x1+0+0",
                       "transient": False, "alpha": 1.0,
                       "topmost": False}],
                     [{"title": "X", "geometry": "1x1+0+0",
                       "transient": False, "alpha": 0.5,
                       "topmost": False}])[1]
      == [("X", "1x1+0+0", "1x1+0+0", "ghost solid → 50%")])
check("junk on both sides never raises",
      layout_compare("banana", [None]) == ([], [], [], []))

# ------------------------------------- the verb, live
app.config.set("tool_window_layouts", {"day": _A, "night": _B})
_blob = dispatch("tools layout diff day night")
check("the verb compares book to book with the arrow honest",
      "diff 'day' → 'night' — 0 of 2 windows unchanged" in _blob)
check("the changed line carries both books' truth",
      "changed: Chart — 300x200+10+10 → 500x300+40+40"
      in _blob and "ghost solid → 40%" in _blob
      and "pin off → on" in _blob)
check("windows only one book knows are named",
      "only in 'day': Solo (100x100+0+0)" in _blob
      and "only in 'night': Extra (9x9+1+1)" in _blob)
_blob = dispatch("tools layout diff night day")
check("reversed order reverses the note",
      "ghost 40% → solid" in _blob and "pin on → off" in _blob)
app.config.set("tool_window_layouts",
               {"a1": _A, "a2": [dict(e) for e in _A]})
_blob = dispatch("tools layout diff a1 a2")
check("identical books agree out loud",
      "2 of 2 windows unchanged" in _blob
      and "the two layouts agree completely" in _blob)
check("an unknown name is answered honestly",
      "is not remembered" in dispatch("tools layout diff day nope"))
_blob = dispatch("tools layout diff")
check("the bare verb teaches BOTH forms",
      "diff <name>" in _blob and "diff <a> <b>" in _blob)

# ------------------------------------- docs & versions
_ft = open(os.path.join("docs", "FEATURES.md"), encoding="utf-8").read()
check("FEATURES.md speaks the book-to-book compare",
      "layout_compare" in _ft and "diff <a> <b>" in _ft)
_arch = open(os.path.join("docs", "ARCHITECTURE.md"),
             encoding="utf-8").read()
check("ARCHITECTURE.md lists smoke_v710", "smoke_v710" in _arch)
_chlog = open("CHANGELOG.md", encoding="utf-8").read()
_ver = __import__("dxn1_studio").APP_VERSION
check("CHANGELOG has 2.71.0", "## [2.71.0]" in _chlog)
check("studio version lives on top of the CHANGELOG",
      _ver >= "2.71.0" and "## [%s]" % _ver in _chlog)

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
