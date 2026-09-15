"""DS2 v2.69.0 UI smoke — the desk admits its drift: `tools layout
diff <name>` compares a saved layout against the live desk with the
SAME exact-then-substring matching the restore uses — what still
stands where the layout left it, what wandered (saved vs now, both
honest), what is not open (named, never conjured), and what is open
that the layout never knew (unbooked) — read-only, not a single
window touched.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v690.py

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
from dxn1_studio.geom import layout_drift  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

check("TERMINAL_HELP teaches diff",
      "diff <name>" in dict(TERMINAL_HELP)["tools layout <name>"])

logs = []
_old_log = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))


def dispatch(cmd):
    logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(logs)


# ------------------------------------- the engine, pure
class _W:
    def __init__(self, title, geo):
        self._t, self._g = title, geo

    def title(self):
        if self._t is None:
            raise RuntimeError("window died")
        return self._t

    def winfo_geometry(self):
        if self._g is None:
            raise RuntimeError("window died")
        return self._g


_snap = [{"title": "Chart", "geometry": "300x200+10+10",
          "transient": True}]
check("in place: standing exactly where the layout left it",
      layout_drift(_snap, [_W("Chart", "300x200+10+10")])
      == ([("Chart", "300x200+10+10")], [], [], []))
check("moved: saved vs live, both named honestly",
      layout_drift(_snap, [_W("Chart", "500x300+40+40")])
      == ([], [("Chart", "300x200+10+10", "500x300+40+40")], [], []))
check("missing: named, never conjured",
      layout_drift(_snap, [])[2] == ["Chart"])
check("unbooked: what is open that the layout never knew",
      layout_drift([], [_W("Stray", "1x1+0+0")])
      == ([], [], [], [("Stray", "1x1+0+0")]))
check("junk on either side never raises",
      layout_drift("banana", [_W("X", "1x1+0+0")])
      == ([], [], [], [("X", "1x1+0+0")])
      and layout_drift([None, {}], [_W(None, None)])
      == ([], [], [], []))
check("substring matching agrees with the restore",
      layout_drift([{"title": "Chart", "geometry": "9x9+1+1",
                     "transient": True}],
                    [_W("My Chart Studio", "9x9+1+1")])[0]
      == [("Chart", "9x9+1+1")])

# ------------------------------------- the verb, live
w = tk.Toplevel(root)
w.title("Chart")
w.transient(root)
w.geometry("300x200+10+10")
root.update()

check("bare diff answers usage", "usage:" in dispatch("tools layout diff"))
check("an unknown layout is answered honestly",
      "not remembered" in dispatch("tools layout diff nope"))
dispatch("tools layout save desk")
_blob = dispatch("tools layout diff desk")
check("a fresh save diffs clean",
      "1 of 1 window still in place" in _blob
      and "the desk is exactly as it was saved" in _blob)

w.geometry("500x300+40+40")
_stray = tk.Toplevel(root)
_stray.title("Stray")
_stray.transient(root)
_stray.geometry("200x100+5+5")
root.update()
_blob = dispatch("tools layout diff desk")
check("the drift is named: moved with both geometries",
      "moved: Chart — saved 300x200+10+10, now 500x300+40+40"
      in _blob)
check("a stray window is called unbooked",
      "unbooked: Stray (200x100+5+5)" in _blob
      and "the layout never knew it" in _blob)
check("diff is read-only — nothing moved because it was diffed",
      w.winfo_geometry() == "500x300+40+40"
      and _stray.winfo_geometry() == "200x100+5+5")
_blob = dispatch("tools layout restore desk")
check("the restore still agrees with what the diff saw",
      "back in place" in _blob
      and w.winfo_geometry() == "300x200+10+10")
_stray.destroy()
root.update()
_blob = dispatch("tools layout diff desk")
check("after the recall, with the stray gone, it diffs clean",
      "the desk is exactly as it was saved" in _blob)
_blob = dispatch("tools layout diff desk")
check("no stray, no unbooked noise",
      "unbooked" not in _blob
      and "the desk is exactly as it was saved" in _blob)

# ------------------------------------- docs & versions
_ft = open(os.path.join("docs", "FEATURES.md"), encoding="utf-8").read()
check("FEATURES.md speaks the drift",
      "layout_drift" in _ft and "diff <name>" in _ft)
_arch = open(os.path.join("docs", "ARCHITECTURE.md"),
             encoding="utf-8").read()
check("ARCHITECTURE.md lists smoke_v690", "smoke_v690" in _arch)
_chlog = open("CHANGELOG.md", encoding="utf-8").read()
_ver = __import__("dxn1_studio").APP_VERSION
check("CHANGELOG has 2.69.0", "## [2.69.0]" in _chlog)
check("studio version lives on top of the CHANGELOG",
      _ver >= "2.69.0" and "## [%s]" % _ver in _chlog)

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
