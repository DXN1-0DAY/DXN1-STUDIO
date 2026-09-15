"""DS2 v2.63.0 UI smoke — width accounting round five (the sweep
COMPLETES: the last twenty-four fixed windows ride geom.fit_to_content,
the two v2.59 custom ratchets join the helper, agent.py's inline v2.60
heal is retired — one pattern, every window, audited by the fleet
check) and the lang report verb (the whole honest ledger at once: one
table, worst pack first, shareable as a file that never overwrites).

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v630.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import re
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
from dxn1_studio.app import DXN1Studio, TERMINAL_HELP  # noqa: E402
from dxn1_studio import geom  # noqa: E402
from dxn1_studio import langedit as _le  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

# ------------------------------------- the sweep: converted windows
# the macro runner (floor 520x460)
from dxn1_studio import macros as _mac  # noqa: E402
_mv = _mac.MacroPanel(root, app.theme, editor=None)
root.update()
check("macros: opens at its floor with the fit queued",
      _mv.winfo_width() >= 520 and _mv.winfo_height() >= 460)
_mv.destroy()
root.update()

# the charmap (floor 640x480)
from dxn1_studio import charmap as _cm  # noqa: E402
_cv = _cm.CharacterMap(root, app.theme)
root.update()
check("charmap: opens at its floor with the fit queued",
      _cv.winfo_width() >= 640 and _cv.winfo_height() >= 480)
_cv.destroy()
root.update()

# the community themes gallery (floor 760x600)
from dxn1_studio import community_themes as _ct  # noqa: E402
_tv = _ct.ThemeGallery(root, app.theme, app.config)
root.update()
check("community_themes: opens at its floor with the fit queued",
      _tv.winfo_width() >= 760 and _tv.winfo_height() >= 600)
_tv.destroy()
root.update()

# ------------------------------------- the fleet audit in smoke form
BASE = "/home/z/dxn1-studio-original"
_pkg = os.path.join(BASE, "dxn1_studio")
_pat = re.compile(r'(?:self|win|root)?\.?geometry\("(\d+)x(\d+)"\)')
_naked = []
for _name in sorted(os.listdir(_pkg)):
    if not _name.endswith(".py"):
        continue
    _lines = open(os.path.join(_pkg, _name),
                  encoding="utf-8").read().splitlines()
    for _i, _ln in enumerate(_lines):
        if not _pat.search(_ln):
            continue
        _window = "\n".join(_lines[_i:_i + 120])
        if ("fit_to_content" in _window or "_fit_w" in _window
                or "restore_root" in _window):
            continue
        if _name == "app.py" and _i < 800:
            continue                       # the root window
        if _name == "gallery.py":
            continue                       # generated-code literal
        if 'geometry("+' in _ln or 'geometry(f"+' in _ln:
            continue                       # position-only
        _naked.append("%s:%d" % (_name, _i + 1))
check("fleet audit: every fixed-geometry window is fit-covered",
      not _naked, )
if _naked:
    print("   naked:", _naked)

# the desk + preview ride the helper; agent's inline heal retired
with open(os.path.join(_pkg, "langedit.py"), encoding="utf-8") as fh:
    _le_src = fh.read()
check("langedit: desk and preview speak the shared helper",
      "_geom.fit_to_content(self, 680, 560)" in _le_src
      and "ratchet=True" in _le_src
      and "self._fit_w = max(440" not in _le_src)
with open(os.path.join(_pkg, "agent.py"), encoding="utf-8") as fh:
    _ag = fh.read()
check("agent.py: the v2.60 inline heal is retired",
      "fit_to_content(\n            self, 680, 520)" in _ag
      and "max(680, self.winfo_reqwidth())" not in _ag)

# ------------------------------------- the lang report verb
verbs_list = [r[0] for r in TERMINAL_HELP]
check("TERMINAL_HELP knows lang report [dest]",
      "lang report [dest]" in verbs_list)

_logs = []
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))

# bare: the whole table prints inline
app.handle_terminal_command("lang report")
_blob = "\n".join(_logs)
check("lang report (bare): the table prints inline",
      "DXN1 STUDIO — language report" in _blob
      and "code" in _blob and "seeds" in _blob
      and "lang report <dest> writes this table" in _blob)

# the data layer agrees with the printed table
_rep = _le.build_report()
_rows = [r for r in _rep["rows"]]
_pcts = [r["real_pct"] if r["real_pct"] is not None else -1
         for r in _rows]
check("build_report: one row per non-en pack, worst first",
      len(_rows) == len([c for c in __import__("dxn1_studio.i18n",
                                               fromlist=["available"])
                         .available() if c != "en"])
      and _pcts == sorted(_pcts)
      and _rep["total_real"] == sum(r["real"] for r in _rows))
check("format_report: verdict names full and seeded packs",
      "fully real" in _le.format_report(_rep, when="x")
      and ("still seeded" in _le.format_report(_rep, when="x")
           or not _rep["seeded"]))

# dest: the file lands; a second run never overwrites
_dest = os.path.join(HOME, "smoke-report.txt")
_logs.clear()
app.handle_terminal_command("lang report %s" % _dest)
_wrote = os.path.exists(_dest)
_body = open(_dest, encoding="utf-8").read() if _wrote else ""
check("lang report <dest>: the file lands with the verdict",
      _wrote and "DXN1 STUDIO — language report" in _body
      and ("still seeded" in _body or "fully real" in _body))
_logs.clear()
app.handle_terminal_command("lang report %s" % _dest)
check("lang report: never overwrites",
      any("already exists — not overwriting" in m for m in _logs))
_logs.clear()
app.handle_terminal_command(
    "lang report %s" % os.path.join(HOME, "no", "such", "dir", "x.txt"))
check("lang report: an unwritable dest answers honestly",
      any("could not write" in m for m in _logs))
app.terminal.log = getattr(app.terminal, "_old_log", app.terminal.log)

# ------------------------------------- source agreement: the 24 riders
_riders = ["devtools.py", "envcheck.py", "charts.py", "gitgraph.py",
           "clipboard.py", "diffview.py", "hasher.py", "contrast.py",
           "colorkit.py", "cronexp.py", "ai_lint.py", "gen.py",
           "focus.py", "charmap.py", "mathpad.py", "community_themes.py",
           "macros.py", "markprev.py", "cvdlab.py", "cheatsheet.py",
           "activity.py", "bookmarks.py", "filestats.py", "agent.py"]
_missing = []
for _mod in _riders:
    with open(os.path.join(_pkg, _mod), encoding="utf-8") as fh:
        if "width accounting round five" not in fh.read() \
                and _mod != "langedit.py":
            _missing.append(_mod)
check("source agreement: all 24 round-five riders commented",
      not _missing)
if _missing:
    print("   missing marker:", _missing)

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
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
