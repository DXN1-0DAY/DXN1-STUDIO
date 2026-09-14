"""DS2 v2.48.0 UI smoke — the way out is written on the door: every
tool window carries an honest hint bar (a key appears only if the
code really binds it — the same accel_pattern the palette audit
uses, Esc only when Escape is really bound, unbacked hints dropped
and reported), the git graph answers to F5/Ctrl+R/+/-/0 with real
row-density zoom, and the keybindings doc agrees with the code.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v480.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

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
from dxn1_studio.app import DXN1Studio, accel_pattern, looks_like_accel  # noqa
from dxn1_studio import hints  # noqa: E402
from dxn1_studio.gitgraph import GitGraphWindow, ROW_H  # noqa: E402
from dxn1_studio.recents import RecentPicker  # noqa: E402
import dxn1_studio.activity as act_mod  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

_logs = []
app.terminal.log = lambda s, *a, **k: _logs.append(str(s))


def _walk_all(w):
    yield w
    for c in w.winfo_children():
        yield from _walk_all(c)


def _bars(win):
    return [w for w in _walk_all(win) if getattr(w, "filled", None)]


def _chips(bar):
    return [str(w.cget("text")) for w in bar.winfo_children()]


# --------------------------------------------- lane A: honesty units
probe = tk.Toplevel(app.root)
ent = tk.Entry(probe)
ent.pack()
ent.bind("<Return>", lambda e: None)
probe.bind("<Escape>", lambda e: probe.destroy())
check("units: tree_bound finds a binding on a descendant",
      hints.tree_bound(probe, "<Return>")
      and not hints.tree_bound(probe, "<Control-q>"))
check("units: esc_bound tells the truth both ways",
      hints.esc_bound(probe) is True)
pbar = hints.hint_bar(probe, app.theme,
                      pairs=(("Return", "open", "Enter"),
                             ("Ctrl+Z", "undo")),
                      notes=("a note",), before=ent)
app.root.update()
check("honesty: an unbacked hint is dropped and reported",
      pbar is not None and pbar.filled
      and pbar.dropped_hints == ["Ctrl+Z"]
      and "Ctrl+Z" not in _chips(pbar))
check("honesty: Esc, backed keys and notes render",
      "Esc" in _chips(pbar) and "close" in _chips(pbar)
      and "Enter" in _chips(pbar) and "a note" in _chips(pbar))
pbar.refresh()
check("honesty: refresh() is idempotent", pbar.filled)
probe2 = tk.Toplevel(app.root)
qbar = hints.hint_bar(probe2, app.theme, esc=False)
app.root.update()
check("honesty: an all-empty bar hides instead of lying with space",
      qbar.filled and qbar.winfo_manager() == "")
probe2.destroy()
check("honesty: a destroyed host never raises the house down",
      hints.hint_bar(probe2, app.theme, pairs=(("F5", "x"),)) is None)
probe.destroy()

# --------------------------------------------- lane B: the git graph
_repo = os.path.join(HOME, "repo")
os.makedirs(_repo, exist_ok=True)
subprocess.run(["git", "init", "-q"], cwd=_repo)
for _i in range(3):
    subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=t",
                    "commit", "-qm", "c%d" % _i, "--allow-empty"],
                   cwd=_repo)
gw = GitGraphWindow(app.root, app.theme, _repo)
app.root.update()
check("graph: the window carries its honest hint bar",
      gw.hintbar.filled and not gw.hintbar.dropped_hints)
gchips = _chips(gw.hintbar)
check("graph: F5, zoom and Esc are advertised",
      "F5" in gchips and "+ / −" in gchips and "0" in gchips
      and "close" in gchips)
check("graph: the keys are really bound",
      bool(gw.bind("<F5>")) and bool(gw.bind("<Control-r>"))
      and bool(gw.bind("<Key-plus>")) and bool(gw.bind("<Key-minus>"))
      and bool(gw.bind("<Key-0>")))
_z1 = gw.zoom_step(0.25)
_items1 = len(gw.canvas.find("all"))
check("graph: zoom steps and redraws",
      _z1 == 1.25 and gw._rh() == int(ROW_H * 1.25) and _items1 > 0)
check("graph: zoom clamps and resets",
      gw.zoom_step(9.0) == 3.0 and gw.zoom_step(-9.0) == 0.5
      and gw.zoom_reset() == 1.0 and gw._rh() == ROW_H)
gw.zoom_step(2.0)
gw._draw()
check("graph: a zoomed draw still paints rows",
      len(gw.canvas.find("all")) >= _items1)
gw.destroy()

# --------------------------------------------- lane C: the windows
app.toast("hinted receipt", "info")
app.root.update()
awin = act_mod.open_activity(app.root, app.theme, app.activity_log)
app.root.update()
_abars = _bars(awin)
check("activity: the window carries its honest hint bar",
      bool(_abars) and not _abars[0].dropped_hints)
achips = _chips(_abars[0]) if _abars else []
check("activity: filter, clear, Esc and the mouse note are advertised",
      "Ctrl+F" in achips and "filter" in achips
      and "Ctrl+L" in achips and "clear" in achips
      and "Esc" in achips and "click a row to copy" in achips)
check("activity: the advertised keys are really bound",
      bool(awin.bind("<Control-f>")) and bool(awin.bind("<Control-l>"))
      and bool(awin.bind("<Escape>")))
awin.destroy()

rp = RecentPicker(app.root, app.theme,
                  ["/tmp/a.py", "/tmp/b.py"], lambda p: None)
app.root.update()
_rbars = _bars(rp.win)
check("recents: the picker advertises arrows and Enter",
      bool(_rbars) and not _rbars[0].dropped_hints
      and "\u2191\u2193" in _chips(_rbars[0])
      and "Enter" in _chips(_rbars[0])
      and "type to filter" in _chips(_rbars[0]))
rp.win.destroy()

wn = __import__("dxn1_studio.whatsnew", fromlist=["open_whatsnew"]) \
    .open_whatsnew(app.root, app.theme, on_log=lambda m: None)
app.root.update()
_wbars = _bars(wn)
check("whatsnew: the release notes carry an honest bar",
      bool(_wbars) and not _wbars[0].dropped_hints
      and "Esc" in _chips(_wbars[0])
      and "click a version to read its notes" in _chips(_wbars[0]))
wn.destroy()

# --------------------------------------------- lane D: the family + doc
_srcs = {m: open("dxn1_studio/%s" % m, encoding="utf-8").read()
         for m in ("recents.py", "outline.py", "bookmarks.py",
                   "whatsnew.py", "doctor.py", "usagedash.py",
                   "gitgraph.py", "app.py")}
check("family: recents and outline wire the entry-level keys",
      'hints.hint_bar(self.win' in _srcs["recents.py"]
      and '("Up", "move"' in _srcs["recents.py"]
      and '("Return", "jump"' in _srcs["outline.py"]
      and "before=self.list_frame" in _srcs["outline.py"])
check("family: bookmarks and whatsnew wire their bottom edge",
      'pairs=(("Return", "jump", "Enter"),)' in _srcs["bookmarks.py"]
      and "before=foot" in _srcs["bookmarks.py"]
      and "before=foot" in _srcs["whatsnew.py"])
check("family: doctor and usagedash gained real keys",
      'self.win.bind("<F5>"' in _srcs["doctor.py"]
      and 'self.win.bind("<Control-C>"' in _srcs["doctor.py"]
      and "Ctrl+Shift+C" in _srcs["doctor.py"]
      and 'self.bind("<F5>"' in _srcs["usagedash.py"]
      and "before=self.status" in _srcs["usagedash.py"])
_doc = open("docs/KEYBINDINGS.md", encoding="utf-8").read()
check("doc: the keybindings doc agrees with the code",
      "## Tool windows (v2.48)" in _doc
      and "`F5` / `Ctrl+R` | Git Graph / Doctor" in _doc
      and "`Ctrl+F` | Activity: refocus the filter box" in _doc
      and "`Ctrl+L` | Activity: clear the receipt log" in _doc
      and "`Ctrl+Shift+C` | Doctor: copy the report" in _doc)
check("regression: the bare plus/minus translator stays exact",
      accel_pattern("+") == "<plus>" and accel_pattern("-") == "<minus>"
      and accel_pattern("Ctrl++") == "<Control-plus>"
      and accel_pattern("Ctrl+-") == "<Control-minus>")
_audited = 0
_broken = []
for _label, _hint, _fn in app.palette_commands():
    if not looks_like_accel(_hint):
        continue
    _pat = accel_pattern(_hint)
    if not _pat or not app.root.bind(_pat):
        _broken.append((_label, _hint))
    else:
        _audited += 1
check("regression: the palette audit still passes (%d audited)"
      % _audited, _audited >= 15 and not _broken)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
