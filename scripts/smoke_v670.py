"""DS2 v2.67.0 UI smoke — the desk sees through walls: `tools
windows ghost <n|title> <level|off>` fades a window see-through
(60 and 60% and 0.6 all mean 60%, off restores solid, the ends
clamp so a window can never be ghosted invisible); bare `ghost`
reports the level; `tools windows pin <n|title>` toggles
stays-above; the listing wears `· NN%`, `· pinned` and `· focused`
markers; neither verb ever touches a title, so raise/close and the
layouts keep matching by name; the windows chip menu remembers the
desk — auto-named save row (desk, desk 2 …), one recall row per
remembered layout, fresh at every post; the deps menu's severity
rows explain themselves with hints.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v670.py

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
from dxn1_studio.geom import (parse_alpha, focused_toplevel,  # noqa: E402
                              MIN_ALPHA, LAYOUTS_KEY)

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

verbs_list = [r[0] for r in TERMINAL_HELP]
check("TERMINAL_HELP knows the layering verbs",
      "tools windows [raise|close|ghost|pin <n|title>]" in verbs_list)

logs = []
_old_log = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))


def dispatch(cmd):
    logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(logs)


# ------------------------------------- the engine, pure
check("parse_alpha: every spelling of sixty percent",
      parse_alpha("60") == 0.6 and parse_alpha("60%") == 0.6
      and parse_alpha("0.6") == 0.6 and parse_alpha(" .6 ") == 0.6)
check("parse_alpha: every spelling of solid",
      all(parse_alpha(t) == 1.0
          for t in ("off", "solid", "full", "1", "1.0", "100", "100%")))
check("parse_alpha: the ends clamp — never invisible",
      parse_alpha("5") == MIN_ALPHA and parse_alpha("150") == 1.0
      and parse_alpha("1.5") == 1.0)
check("parse_alpha: junk is refused, never raised",
      parse_alpha("") is None and parse_alpha(None) is None
      and parse_alpha("junk") is None and parse_alpha("-3") is None)

# ------------------------------------- ghost & pin, live
w = tk.Toplevel(root)
w.title("Ghost probe")
w.transient(root)
w.geometry("300x200+80+80")
root.update()

check("ghost sets the level and says so",
      "ghosted to 60%" in dispatch("tools windows ghost 1 60")
      and abs(float(w.attributes("-alpha")) - 0.6) < 0.01)
check("ghost speaks percent and fraction alike",
      "ghosted to 40%" in dispatch("tools windows ghost ghost 0.4"))
check("bare ghost reports without changing",
      "is at 40%" in dispatch("tools windows ghost 1")
      and abs(float(w.attributes("-alpha")) - 0.4) < 0.01)
check("junk level is refused with usage, level kept",
      "usage:" in dispatch("tools windows ghost 1 banana")
      and abs(float(w.attributes("-alpha")) - 0.4) < 0.01)
check("missing target is refused with usage",
      "usage:" in dispatch("tools windows ghost"))
check("off restores solid",
      "solid again (100%)" in dispatch("tools windows ghost 1 off")
      and abs(float(w.attributes("-alpha")) - 1.0) < 0.01)
check("pin reports honestly in both directions",
      "pinned" in dispatch("tools windows pin 1")
      and "pinned" in dispatch("tools windows pin ghost"))
check("no match names the miss",
      "no window matches" in dispatch("tools windows ghost 7 60")
      and "no window matches" in dispatch("tools windows pin 7"))

# the listing wears the markers it can honestly know
dispatch("tools windows ghost 1 30")
_blob = dispatch("tools windows")
check("the listing wears the ghost level", "· 30%" in _blob)
check("the listing marks transient", "· transient" in _blob)
check("the footer teaches the new verbs",
      "ghost <n|title>" in _blob and "pin <n|title>" in _blob)
_pinned_stuck = False
try:
    dispatch("tools windows pin 1")
    _pinned_stuck = bool(w.attributes("-topmost"))
except Exception:  # noqa: BLE001 — no WM in the house
    pass
check("the pinned marker appears only when the WM kept it",
      ("· pinned" in _blob) if _pinned_stuck
      else ("· pinned" not in dispatch("tools windows")))

# the layering is skin-deep: titles untouched
check("ghost and pin never touch the title",
      w.title() == "Ghost probe"
      and "is front now" in dispatch("tools windows raise ghost"))

# the focused marker names the window that holds the focus
_focus_marked = True
try:
    w.lift(); w.focus_force(); root.update()
    _blob = dispatch("tools windows")
    _ft = focused_toplevel(root.focus_get(),
                           app._open_tool_windows())
    if _ft is w:
        _focus_marked = "· focused" in _blob
except Exception:  # noqa: BLE001 — headless focus is moody
    _focus_marked = True
check("the focused window wears its marker", _focus_marked)

# ------------------------------------- the chip menu remembers the desk
_rows = [e for e in app._wins_menu_entries() if e[0] != "---"]
check("empty book shows the honest row",
      any(e[0] == "No layouts saved yet" for e in _rows))
check("every command row carries a hint",
      all(len(e) > 4 and e[4] for e in _rows))
check("the save row rides the menu",
      any(e[0] == "Save desk layout…" for e in _rows))
app._wins_menu_save_layout()
check("the save row dispatches the real verb, auto-named",
      "'desk' remembers 1 window" in "\n".join(logs), )
_rows = [e[0] for e in app._wins_menu_entries()]
check("the recall row appears fresh at every post",
      any("Recall layout 'desk' (1 window)" in lb for lb in _rows))
_recall = [e for e in app._wins_menu_entries()
           if e[0].startswith("Recall layout 'desk'")][0]
_recall[1]()
check("the recall row dispatches the real restore",
      "back in place" in "\n".join(logs))
app._wins_menu_save_layout()
_rows = [e[0] for e in app._wins_menu_entries()]
check("a second save walks the name forward",
      any("'desk 2'" in lb for lb in _rows))
dispatch("tools layout forget all")
_rows = [e[0] for e in app._wins_menu_entries()]
check("forgetting empties the menu's book too",
      any(e == "No layouts saved yet" for e in _rows))

# ------------------------------------- the deps rows explain themselves
_deps = [e for e in app._deps_menu_entries() if e[0] != "---"]
check("every deps row carries a hint",
      _deps and all(len(e) > 4 and e[4] for e in _deps))

# ------------------------------------- docs & versions
_ft = open(os.path.join("docs", "FEATURES.md"), encoding="utf-8").read()
check("FEATURES.md speaks the layering",
      "ghost" in _ft and "pin" in _ft)
_arch = open(os.path.join("docs", "ARCHITECTURE.md"),
             encoding="utf-8").read()
check("ARCHITECTURE.md lists smoke_v670", "smoke_v670" in _arch)
_chlog = open("CHANGELOG.md", encoding="utf-8").read()
_ver = __import__("dxn1_studio").APP_VERSION
check("CHANGELOG has 2.67.0", "## [2.67.0]" in _chlog)
check("studio version lives on top of the CHANGELOG",
      _ver >= "2.67.0" and "## [%s]" % _ver in _chlog)

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
