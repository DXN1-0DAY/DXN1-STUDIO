"""DS2 v2.62.0 UI smoke — width accounting round four, the
mechanical batch: ten more fixed windows ride geom.fit_to_content
via after_idle — terminal window, scratch pad, text diff, tree
export, REST bench, quick-actions launcher, readability panel, pair
mode, unit converter, text case — each opening no narrower (or
shorter) than what it actually packed, with the designed default as
the floor and the fit firing once the build settles.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v620.py

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
from dxn1_studio.app import DXN1Studio  # noqa: E402
from dxn1_studio import geom  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

# ------------------------------------- the after_idle contract
_win = tk.Toplevel(root)
tk.Label(_win, text="A" * 160).pack(padx=8, pady=8)
_win.geometry("400x200")
_win.after_idle(lambda: geom.fit_to_content(_win, 400, 200))
root.update()
check("helper: a queued fit fires once the build settles",
      _win.winfo_width() >= _win.winfo_reqwidth() - 2 >= 400)
_win.destroy()
root.update()

# ------------------------------------- a real converted window opens
# the unit converter (floor 560x460, req ~549 — the floor must win)
from dxn1_studio import unitconv as _uc  # noqa: E402
_ucv = _uc.UnitConverter(root, app.theme)
root.update()
check("unitconv: opens at its floor with the fit queued",
      _ucv.winfo_width() >= 560 and _ucv.winfo_height() >= 460)
_ucv.destroy()
root.update()

# the text-case window (floor 560x420)
from dxn1_studio import textcase as _tc  # noqa: E402
_tcw = _tc.TextCase(root, app.theme)
root.update()
check("textcase: opens no narrower than its floor",
      _tcw.winfo_width() >= 560 and _tcw.winfo_height() >= 420)
_tcw.destroy()
root.update()

# ------------------------------------- the fleet agrees in source
_converted = 0
for _m, _w, _h in (("term.py", 860, 520), ("scratch.py", 560, 520),
                   ("textdiff.py", 760, 500), ("treeexport.py", 760, 600),
                   ("restbench.py", 900, 640), ("quick_actions.py", 760, 560),
                   ("readability.py", 720, 560), ("pair.py", 720, 600),
                   ("unitconv.py", 560, 460), ("textcase.py", 560, 420),
                   ("hexdump.py", 700, 460), ("numbase.py", 520, 430),
                   ("projects.py", 420, 260), ("xmlbench.py", 720, 480),
                   ("pwdgen.py", 520, 360), ("branches.py", 760, 600),
                   ("branches.py", 360, 120), ("csvkit.py", 680, 480),
                   ("jwt.py", 880, 600)):
    with open(os.path.join("dxn1_studio", _m), encoding="utf-8") as fh:
        s = fh.read()
    # NB: "self.win" is a substring of "self.winfo…", so try both
    # attrs instead of sniffing the file
    _hit = "after_idle" in s and any(
        "fit_to_content(\n%s%s, %d, %d)" % (" " * 12, a, _w, _h) in s
        for a in ("self.win", "self", "win"))
    if _hit:
        _converted += 1
check("source: nineteen more windows ride the helper (%d/19)"
      % _converted, _converted == 19)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "Round Four" in _ft and "after_idle" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v620" in _ar)

# ------------------------------------- regression: the palette audit
from dxn1_studio.app import accel_pattern  # noqa: E402
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
app._dismiss_chip_menu()
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
