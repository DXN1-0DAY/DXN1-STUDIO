"""DS2 v2.65.0 UI smoke — the window manager learns to tidy and the
statusbar grows a window chip: `tools cascade` stacks every open
tool window from the top-left, 28px apart, sizes kept; `tools tile`
deals them into a screen-filling grid; both answer honestly when
nothing is open. The new open-windows chip counts quietly, turns
amber at 6+, clicks into the honest listing, and its menu reaches
the keyboard (`chip windows`). And the twice-parked chip-menu row
tooltips land: hint-carrying rows expose `_ds2_hints`, bind Motion,
and the unpost poller retires the tip.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v650.py

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
check("TERMINAL_HELP knows tools cascade | tile",
      "tools cascade | tile" in verbs_list)
check("help advertises the tidy verbs",
      any("cascade stacks them title-bar by title-bar" in v
          for _k, v in TERMINAL_HELP))

logs = []
_old_log = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))


def dispatch(cmd):
    logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(logs)


# ------------------------------------- honest empty answers
check("cascade honest when none open",
      "none open" in dispatch("tools cascade"))
check("tile honest when none open",
      "none open" in dispatch("tools tile"))

# ------------------------------------- cascade keeps sizes, stacks 28px
w1 = tk.Toplevel(root)
w1.title("Smoke one")
w1.transient(root)
w1.geometry("300x200+900+700")
w2 = tk.Toplevel(root)
w2.title("Smoke two")
w2.transient(root)
w2.geometry("300x200+900+700")
root.update()
blob = dispatch("tools cascade")
x1 = int(w1.winfo_geometry().split("+")[1])
x2 = int(w2.winfo_geometry().split("+")[1])
check("cascade moved from the parked corner", x1 == 60)
check("cascade stacked 28px apart", x2 - x1 == 28)
check("cascade keeps sizes",
      w1.winfo_geometry().split("+")[0] == "300x200")
check("cascade reports the stack", "2 windows stacked" in blob)

# ------------------------------------- tile: grid on the screen
blob = dispatch("tools tile")
root.update()
g = w1.winfo_geometry()
w_, h_ = g.split("+")[0].split("x")
gx, gy = int(g.split("+")[1]), int(g.split("+")[2])
check("tile resized to a cell", (int(w_), int(h_)) != (300, 200))
check("tile honours the margin", gx == 8)
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
check("tile keeps windows on-screen",
      gx + int(w_) <= sw and gy + int(h_) <= sh)
check("tile reports the grid", "into a 2x1 grid" in blob)

# ------------------------------------- the windows chip
check("chip quiet again after the windows close",
      (w1.destroy(), w2.destroy(), root.update(),
       app._update_wins_chip(force=True),
       app.status_wins.cget("text") == "")[-1])
wa = tk.Toplevel(root)
wa.title("Chip smoke")
wa.transient(root)
root.update()
app._update_wins_chip(force=True)
check("chip counts one", app.status_wins.cget("text") == "1 open")
check("chip is muted while small",
      app.status_wins.cget("fg") == app.theme["text_muted"])
sig = app._wins_sig_state
app._update_wins_chip()
check("chip signature cache holds", app._wins_sig_state == sig)
wa.destroy()
root.update()
app._update_wins_chip(force=True)
check("chip quiet once the single window closes",
      app.status_wins.cget("text") == "")
pile = []
for i in range(6):
    tw = tk.Toplevel(root)
    tw.title("Pile %d" % i)
    tw.transient(root)
    pile.append(tw)
root.update()
app._update_wins_chip(force=True)
check("chip turns amber at six",
      app.status_wins.cget("text") == "6 open"
      and app.status_wins.cget("fg") == "#f59e0b")
for tw in pile:
    tw.destroy()
root.update()

# click: the VERB really dispatches (no "$ tools windows" shell echo)
app._update_wins_chip(force=True)
logs.clear()
app._wins_chip_click()
root.update()
check("chip click runs the honest listing",
      any("tools windows — " in s for s in logs), )

# ------------------------------------- chip windows: keyboard reach
blob = dispatch("chip windows")
menu = app._last_chip_menu
check("`chip windows` posts the menu",
      menu is not None and bool(menu.winfo_exists()))
hints = getattr(menu, "_ds2_hints", None)
check("menu carries hint rows", isinstance(hints, dict) and
      len(hints) == 4)
check("hint keys name real command rows",
      hints and all(menu.type(i) == "command" for i in hints))
check("first hint says alt-tab", "alt-tab" in list(hints.values())[0])
check("menu bound Motion for tooltips", bool(menu.bind("<Motion>")))
check("tip closer armed", callable(getattr(menu, "_ds2_tip_close", None)))
labels = [menu.entrycget(i, "label")
          for i in app._menu_command_rows(menu)]
check("menu rows: list, cascade, tile, close-all",
      labels == ["List open windows", "Cascade windows",
                 "Tile windows", "Close all transient"], )
check("registry knows wins", "wins" in app._chip_menu_registry())
check("alias windows → wins",
      app._CHIP_MENU_ALIASES.get("windows") == "wins")
check("bare chip lists windows", "windows" in dispatch("chip"))
check("unknown chip is refused honestly",
      "unknown chip" in dispatch("chip nope"))

# a menu row really dispatches its verb (invoke, not just wiring)
dispatch("chip windows")
menu = app._last_chip_menu
logs.clear()
try:
    menu.invoke(0)   # "List open windows"
    root.update()
except Exception:    # noqa: BLE001 — headless menus may refuse invoke
    pass
check("menu row dispatches the listing verb",
      any("tools windows — " in s for s in logs))

# the unpost poller retires the tip
closed = {"n": 0}
menu._ds2_tip_close = (lambda: closed.__setitem__("n", closed["n"] + 1))
try:
    menu.unpost()
except Exception:    # noqa: BLE001 — headless menu may refuse
    pass
root.update()
menu._ds2_poll()
check("unpost poller retires the tip closer", closed["n"] >= 1)

# other chip menus carry hints too (the parked idea, everywhere)
dispatch("chip scribe")
check("scribe menu hints", len(getattr(
    app._last_chip_menu, "_ds2_hints", {})) == 3)
dispatch("chip autosave")
check("sesave menu hints", len(getattr(
    app._last_chip_menu, "_ds2_hints", {})) == 3)

# ------------------------------------- pure math regression
from dxn1_studio.geom import cascade_positions, tile_rects  # noqa: E402
big = cascade_positions(200, 800, 600)
check("cascade wraps before leaving the screen",
      len(big) == 200 and all(0 <= x <= 800 - 120 - 8
                              and 0 <= y <= 600 - 40 - 8
                              for x, y in big))
tiny = tile_rects(4, 400, 300)
check("tiny screen wins over the minimum cell",
      all(x + w <= 400 and y + h <= 300 for x, y, w, h in tiny))
check("single tile fills the screen",
      tile_rects(1, 1920, 1080) == [(8, 8, 1904, 1064)])

# ------------------------------------- docs consistency
_ft = open(os.path.join("docs", "FEATURES.md"), encoding="utf-8").read()
check("FEATURES.md speaks the tidy verbs",
      "tools cascade" in _ft and "tools tile" in _ft)
check("FEATURES.md speaks the windows chip",
      "open-windows chip" in _ft)
_arch = open(os.path.join("docs", "ARCHITECTURE.md"),
             encoding="utf-8").read()
check("ARCHITECTURE.md lists smoke_v650", "smoke_v650" in _arch)
_chlog = open("CHANGELOG.md", encoding="utf-8").read()
check("CHANGELOG has 2.65.0", "## [2.65.0]" in _chlog)
check("studio version is 2.65.0",
      __import__("dxn1_studio").APP_VERSION == "2.65.0")

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
