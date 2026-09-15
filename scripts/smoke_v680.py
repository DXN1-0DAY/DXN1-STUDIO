"""DS2 v2.68.0 UI smoke — the layouts remember the layers: a desk
saved ghosted recalls ghosted, a desk saved solid recalls solid,
and a v2.66-era snapshot moves geometry without touching a skin
(None means DON'T TOUCH — junk is never a license to repaint);
`tools layout show <name>` previews a snapshot window by window,
marking what is open right now; `tools windows find <text>`
narrows the honest listing to the titles carrying the text; and
the open-windows chip's tooltip is COMPUTED at hover — N open plus
ghosted/pinned counts as the desk IS.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v680.py

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
from dxn1_studio.geom import (window_layer, capture_layout,  # noqa: E402
                              layer_counts, apply_layout)

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

verbs_list = [r[0] for r in TERMINAL_HELP]
check("TERMINAL_HELP knows the layout family",
      "tools layout <name>" in verbs_list)
check("TERMINAL_HELP teaches find",
      "or find <text> narrows the list"
      in dict(TERMINAL_HELP)[
          "tools windows [raise|close|ghost|pin <n|title>]"])

logs = []
_old_log = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))


def dispatch(cmd):
    logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(logs)


# ------------------------------------- the honest read, pure
class MuteWin:                        # refuses everything
    def attributes(self, *_a):
        raise RuntimeError("no wm here")


check("window_layer: a window that will not say is assumed ordinary",
      window_layer(MuteWin()) == (1.0, False))
check("window_layer: a banana is no crown and no ghost",
      window_layer(type("J", (), {"attributes":
                   lambda self, k: "banana"})()) == (1.0, False))

w = tk.Toplevel(root)
w.title("Layer probe")
w.transient(root)
w.geometry("300x200+20+20")
root.update()
check("window_layer: a live solid window reads solid",
      abs(window_layer(w)[0] - 1.0) < 0.01 and window_layer(w)[1] is False)
w.attributes("-alpha", 0.6)
root.update()
check("window_layer: the ghost level reads back",
      abs(window_layer(w)[0] - 0.6) < 0.01)

snap = capture_layout([w])
check("capture_layout remembers the layers",
      abs(snap[0]["alpha"] - 0.6) < 0.01 and snap[0]["topmost"] is False)
check("layer_counts: earned, never guessed",
      layer_counts(snap) == (1, 0)
      and layer_counts([{"title": "x", "alpha": "x",
                         "topmost": "yes"}]) == (0, 0)
      and layer_counts("banana") == (0, 0))

new_style = [{"title": "Layer probe", "geometry": "300x200+20+20",
              "transient": True, "alpha": 0.6, "topmost": False}]
old_style = [{"title": "Layer probe", "geometry": "300x200+20+20",
              "transient": True}]
check("apply_layout: the layering rides along",
      apply_layout(new_style, [w])[0][0][2:] == (0.6, False))
check("apply_layout: an old snapshot says None — don't touch",
      apply_layout(old_style, [w])[0][0][2:] == (None, None))
check("apply_layout: junk layers are None too",
      apply_layout([{"title": "Layer probe",
                     "geometry": "300x200+20+20", "transient": True,
                     "alpha": "x", "topmost": "yes"}],
                    [w])[0][0][2:] == (None, None))

# ------------------------------------- save / show / restore, live
w.attributes("-alpha", 1.0)
root.update()
check("a solid desk saves without a layering suffix",
      "remembers 1 window" in dispatch("tools layout save solid_desk")
      and "ghosted" not in "\n".join(logs))
dispatch("tools windows ghost 1 40")
check("a ghosted desk saves honestly about layers",
      "(1 ghosted)" in dispatch("tools layout save layered_desk"))
_blob = dispatch("tools layout list")
check("list marks the layered book only",
      "layered_desk · 1 window · Layer probe · layered" in _blob
      and "solid_desk · 1 window · Layer probe\n" in _blob)

_blob = dispatch("tools layout show layered_desk")
check("show previews the header with the layer counts",
      "remembers 1 window · 1 ghosted · 0 pinned" in _blob)
check("show marks the ghost level and what is open",
      "Layer probe · 300x200+20+20 · 40% · open now" in _blob)
check("show refuses an unknown name honestly",
      "not remembered" in dispatch("tools layout show nope"))
check("bare show answers usage", "usage:" in dispatch("tools layout show"))

# recall the layered desk AFTER solidifying: the ghost comes back
w.attributes("-alpha", 1.0)
w.geometry("800x600+120+90")
root.update()
_blob = dispatch("tools layout restore layered_desk")
check("restore re-ghosts and says so",
      "Layer probe · ghosted to 40%" in _blob
      and abs(float(w.attributes("-alpha")) - 0.4) < 0.01
      and w.winfo_geometry() == "300x200+20+20")
_blob = dispatch("tools layout restore solid_desk")
check("a solid layout actively restores solid — and says so once",
      "Layer probe · solid again" in _blob
      and abs(float(w.attributes("-alpha")) - 1.0) < 0.01)

app.config.set("tool_window_layouts", {"ancient": old_style})
w.attributes("-alpha", 0.5)
root.update()
_blob = dispatch("tools layout restore ancient")
check("a v2.66-era snapshot moves geometry, never skins",
      "back in place" in _blob and "ghosted" not in _blob
      and w.winfo_geometry() == "300x200+20+20"
      and abs(float(w.attributes("-alpha")) - 0.5) < 0.01)

# ------------------------------------- find narrows the listing
w2 = tk.Toplevel(root)
w2.title("Terminal")
w2.transient(root)
w2.geometry("300x200+60+60")
root.update()
check("bare find answers usage",
      "usage:" in dispatch("tools windows find"))
check("find misses honestly, full list pointed at",
      "no open window's title carries it"
      in dispatch("tools windows find zzzqqq"))
_blob = dispatch("tools windows find probe")
check("find narrows with an honest N of M header",
      "find 'probe' — 1 of 2 open" in _blob
      and "Layer probe · 300x200+20+20" in _blob)
check("find is case-insensitive",
      "1 of 2 open" in dispatch("tools windows find PROBE"))
_blob = dispatch("tools windows")
check("the full listing is unchanged by find",
      "2 open" in _blob and "Terminal" in _blob
      and "find <text>" in _blob)

# ------------------------------------- the tooltip is computed at hover
_tip = app._wins_tip_text()
check("the tooltip speaks the desk as it IS",
      "2 open" in _tip and "1 ghosted" in _tip, )
dispatch("tools windows ghost layer off")
check("the tooltip keeps up with the layering",
      "2 open" in app._wins_tip_text()
      and "ghosted" not in app._wins_tip_text())
check("the wins chip's Enter binding is the live one",
      bool(app.status_wins.bind("<Enter>")))

# ------------------------------------- docs & versions
_ft = open(os.path.join("docs", "FEATURES.md"), encoding="utf-8").read()
check("FEATURES.md speaks the layered layouts",
      "layer" in _ft.lower() and "show <name>" in _ft)
_arch = open(os.path.join("docs", "ARCHITECTURE.md"),
             encoding="utf-8").read()
check("ARCHITECTURE.md lists smoke_v680", "smoke_v680" in _arch)
_chlog = open("CHANGELOG.md", encoding="utf-8").read()
_ver = __import__("dxn1_studio").APP_VERSION
check("CHANGELOG has 2.68.0", "## [2.68.0]" in _chlog)
check("studio version lives on top of the CHANGELOG",
      _ver >= "2.68.0" and "## [%s]" % _ver in _chlog)

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
