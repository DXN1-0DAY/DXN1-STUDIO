"""DS2 v2.49.0 UI smoke — every door gets its sign: the diff viewer's
never-defined _build_footer is built (it crashed every open since
v1.4) with real F3/Ctrl+U/Ctrl+C keys and an honest bar, the git
graph's lane_of NameError is fixed and driven with a REAL merge
topology (the old checks passed vacuously before the 80ms refresh
timer fired), six more windows carry hint bars with real keys, and
hovering a graph row whispers the full truth.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v490.py

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
from dxn1_studio.app import DXN1Studio, accel_pattern  # noqa: E402
from dxn1_studio import hints  # noqa: E402
from dxn1_studio.theme import Theme  # noqa: E402
from dxn1_studio.diffview import DiffViewer  # noqa: E402
from dxn1_studio.gitgraph import GitGraphWindow, fetch_commits  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())


def _walk_all(w):
    yield w
    for c in w.winfo_children():
        yield from _walk_all(c)


def _bars(win):
    return [w for w in _walk_all(win) if getattr(w, "filled", None)]


def _chips(bar):
    out = []
    for w in bar.winfo_children():
        try:
            out.append(str(w.cget("text")))
        except Exception:  # noqa: BLE001 — frames have no text
            pass
    return out


def _labels(win):
    out = []
    for w in _walk_all(win):
        if isinstance(w, tk.Label):
            out.append(str(w.cget("text")))
    return out


EV = lambda x, y: type("E", (), {"x": x, "y": y})()

# --------------------------------------------- lane A: the diff viewer
t = Theme("dark", "violet")
dv = DiffViewer(app.root, t, "alpha\nbeta\ngamma",
                "alpha\nbeta TWO\ngamma\ndelta",
                old_label="before", new_label="after", title="smoke")
app.root.update()
check("diff: the window OPENS (the v1.4 _build_footer regression)",
      dv.winfo_exists() and dv.mode == "split")
check("diff: the footer carries the one-line verdict",
      any("+2" in s and "\u22121" in s and "2 changed hunks" in s
          for s in _labels(dv)))
check("diff: the hint bar is honest",
      dv.hintbar.filled and not dv.hintbar.dropped_hints
      and "F3" in _chips(dv.hintbar) and "\u21e7F3" in _chips(dv.hintbar)
      and "Ctrl+U" in _chips(dv.hintbar) and "Ctrl+C" in _chips(dv.hintbar)
      and "click \u2039 \u203a to step changes" in _chips(dv.hintbar))
check("diff: the advertised keys are really bound",
      bool(dv.bind("<F3>")) and bool(dv.bind("<Shift-F3>"))
      and bool(dv.bind("<Control-u>")) and bool(dv.bind("<Control-c>")))
dv.left.focus_set(); app.root.update()
dv.left.event_generate("<Control-u>"); app.root.update()
check("diff: Ctrl+U flips to the unified view", dv.mode == "unified")
dv._focus_text.focus_set(); app.root.update()
dv._focus_text.event_generate("<Control-u>"); app.root.update()
check("diff: Ctrl+U flips back to split", dv.mode == "split")
dv._focus_text.event_generate("<Control-c>"); app.root.update()
check("diff: Ctrl+C copies the clean unified patch",
      "beta TWO" in app.root.clipboard_get())
dv._focus_text.event_generate("<F3>"); app.root.update()
dv._focus_text.event_generate("<Shift-F3>"); app.root.update()
check("diff: F3 / Shift+F3 walk the hunks",
      dv.jump_at == 0 and dv._hunk_text() == "1 / 2")
dv.destroy()

# --------------------------------------------- lane B: the real graph
_repo = os.path.join(HOME, "mergerepo")
os.makedirs(_repo, exist_ok=True)
_env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="a@b",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="a@b")


def _g(*args):
    subprocess.run(["git"] + list(args), cwd=_repo, env=_env,
                   capture_output=True, text=True)


subprocess.run(["git", "init", "-q", "-b", "main"], cwd=_repo)
_g("commit", "-qm", "base", "--allow-empty")
_g("checkout", "-qb", "feature")
_g("commit", "-qm", "feature work", "--allow-empty")
_g("checkout", "-q", "main")
_g("commit", "-qm", "on main", "--allow-empty")
_g("merge", "--no-ff", "feature", "-m", "merge feature")
commits, err = fetch_commits(_repo, 200)
check("graph: the merge topology fetched",
      not err and len(commits) == 4)
gw = GitGraphWindow(app.root, app.theme, _repo)
gw.refresh()                       # drive it — no timer racing
app.root.update()
check("graph: real rows loaded (never the vacuous empty pass)",
      len(gw.rows) == 4)
gw._draw()                         # the v1.4 lane_of NameError died here
_items = len(gw.canvas.find("all"))
check("graph: a direct draw paints the full picture",
      _items > 25, )
check("graph: the merge row carries both parent edges",
      len([e for _l, c, e in gw.rows
           if c["subject"] == "merge feature"][0]) == 2)
check("graph: the bar advertises the hover whisper",
      gw.hintbar.filled and not gw.hintbar.dropped_hints
      and "hover a commit for the full message" in _chips(gw.hintbar))
gw._on_hover(EV(100, 20)); app.root.update()
_tip_ok = gw._tip is not None and gw._tip_sha == gw.rows[0][1]["sha"]
_texts = []
if gw._tip is not None:
    for _w in gw._tip.winfo_children():
        for _c in _w.winfo_children():
            _texts.append(str(_c.cget("text")))
check("graph: hovering a row whispers the full subject + refs",
      _tip_ok and "merge feature" in _texts
      and "feature" in " ".join(_texts))
gw._on_hover(EV(100, 2)); app.root.update()
check("graph: moving off a row hides the whisper",
      gw._tip is None and gw._tip_sha is None)
gw._on_hover(EV(100, 20)); app.root.update()
gw._on_leave(); app.root.update()
check("graph: leaving the canvas hides the whisper", gw._tip is None)
gw._on_hover(EV(100, 20)); app.root.update()
gw._on_click(EV(100, 20)); app.root.update()
check("graph: clicking hides the whisper and selects the commit",
      gw._tip is None and gw.selected_sha == gw.rows[0][1]["sha"])
gw.destroy()

# --------------------------------------------- lane C: the new keys
dt = __import__("dxn1_studio.devtools", fromlist=["DevTools"]) \
    .DevTools(app.root, app.theme)
app.root.update()
check("devtools: the bar lists all five tabs honestly",
      dt.hintbar.filled and not dt.hintbar.dropped_hints
      and all("Ctrl+%d" % i in _chips(dt.hintbar) for i in range(1, 6))
      and "regex" in _chips(dt.hintbar) and "color" in _chips(dt.hintbar))
dt.focus_set(); app.root.update()
dt.event_generate("<Control-3>"); app.root.update()
_dt_tab3 = dt.nb.index(dt.nb.select())
dt.event_generate("<Control-1>"); app.root.update()
check("devtools: Ctrl+1…5 really switch tabs",
      _dt_tab3 == 2 and dt.nb.index(dt.nb.select()) == 0)
dt.select_tab(4)
_stray = dt.nb.index(dt.nb.select())
dt.select_tab(99)
check("devtools: a stray index never raises",
      _stray == 4 and dt.nb.index(dt.nb.select()) == 4)
dt.destroy()

td = __import__("dxn1_studio.textdiff", fromlist=["TextDiff"]) \
    .TextDiff(app.root, app.theme, initial="")
app.root.update()
check("textdiff: honest bar with the copy key",
      td.hintbar.filled and not td.hintbar.dropped_hints
      and "Ctrl+Shift+C" in _chips(td.hintbar)
      and "copy diff" in _chips(td.hintbar) and "Esc" in _chips(td.hintbar))
td.focus_set(); app.root.update()
td.event_generate("<Control-C>"); app.root.update()
check("textdiff: Ctrl+Shift+C really copies",
      "copied" in str(td.status.cget("text")))
td.event_generate("<Escape>"); app.root.update()
check("textdiff: Esc really closes", not td.winfo_exists())

cs = __import__("dxn1_studio.cheatsheet", fromlist=["CheatSheet"]) \
    .CheatSheet(app.root, app.theme)
app.root.update()
check("cheatsheet: honest bar (copy HTML, save, close)",
      cs.hintbar.filled and not cs.hintbar.dropped_hints
      and "Ctrl+Shift+C" in _chips(cs.hintbar)
      and "copy HTML" in _chips(cs.hintbar)
      and "Ctrl+S" in _chips(cs.hintbar) and "Esc" in _chips(cs.hintbar))
cs.focus_set(); app.root.update()
cs.event_generate("<Control-C>"); app.root.update()
check("cheatsheet: Ctrl+Shift+C copies the HTML",
      "HTML copied" in str(cs.status.cget("text")))
cs.destroy()

_ws = os.path.join(HOME, "statsws")
os.makedirs(_ws, exist_ok=True)
for _n in ("a.py", "b.py", "c.md"):
    open(os.path.join(_ws, _n), "w").write("x" * 100)
fw = __import__("dxn1_studio.filestats", fromlist=["open_stats"]) \
    .open_stats(app.root, app.theme, workspace=_ws, on_log=lambda m: None)
app.root.update()
_fbars = _bars(fw)
check("filestats: the bar is honest about keys AND the mouse",
      bool(_fbars) and not _fbars[0].dropped_hints
      and "Ctrl+C" in _chips(_fbars[0]) and "copy report" in _chips(_fbars[0])
      and "Ctrl+E" in _chips(_fbars[0]) and "F5" in _chips(_fbars[0])
      and "Esc" in _chips(_fbars[0]) and "clear filter" in _chips(_fbars[0])
      and "click a bar to filter" in _chips(_fbars[0])
      and "double-click a file to copy its path" in _chips(_fbars[0]))
fw.focus_set(); app.root.update()
fw.event_generate("<Control-c>"); app.root.update()
check("filestats: Ctrl+C copies the report",
      "File statistics" in app.root.clipboard_get())
fw.destroy()

sp = __import__("dxn1_studio.scratch", fromlist=["open_scratchpad"]) \
    .open_scratchpad(app.root, app.theme)
app.root.update()
check("scratch: the hand-written hint is now a verified bar",
      sp.win._scratch_hint.filled
      and not sp.win._scratch_hint.dropped_hints
      and "Ctrl+Return" in _chips(sp.win._scratch_hint)
      and "stamp a new bullet" in _chips(sp.win._scratch_hint)
      and "auto-saved as you type" in _chips(sp.win._scratch_hint))
sp.win.destroy()

gd = __import__("dxn1_studio.scribe", fromlist=["open_goal_dialog"]) \
    .open_goal_dialog(app.root, app.theme, 500, on_set=lambda gv: None)
app.root.update()
_gbars = _bars(gd)
check("goal dialog: the bar whispers Enter / Esc",
      bool(_gbars) and not _gbars[0].dropped_hints
      and "Enter" in _chips(_gbars[0]) and "set goal" in _chips(_gbars[0])
      and "Esc" in _chips(_gbars[0]))
gd.destroy()

# --------------------------------------------- lane D: docs + audit
_srcs = {m: open("dxn1_studio/%s" % m, encoding="utf-8").read()
         for m in ("diffview.py", "gitgraph.py", "devtools.py",
                   "textdiff.py", "cheatsheet.py", "filestats.py",
                   "scratch.py", "scribe.py")}
check("source: the diff footer and hint bar are wired",
      "def _build_footer" in _srcs["diffview.py"]
      and "_build_hintbar()" in _srcs["diffview.py"])
check("source: the lane_of fix lives in _draw",
      'lane_of = {cm["sha"]: ln for ln, cm, _e in self.rows}'
      in _srcs["gitgraph.py"] and "def _show_tip" in _srcs["gitgraph.py"])
check("source: the new keys are really bound in source",
      'self.bind("<Control-%d>" % (_i + 1)' in _srcs["devtools.py"]
      and 'win.bind("<Control-c>"' in _srcs["filestats.py"]
      and 'self.bind("<Control-C>"' in _srcs["textdiff.py"]
      and 'self.bind("<Control-C>"' in _srcs["cheatsheet.py"]
      and 'hints.hint_bar(' in _srcs["scribe.py"])
check("source: the scratch hand-label is gone",
      'Ctrl+Enter: stamp' not in _srcs["scratch.py"])
_doc = open("docs/KEYBINDINGS.md", encoding="utf-8").read()
check("doc: the v2.49 keybindings agree with the code",
      "## Tool windows (v2.49)" in _doc
      and "`F3` / `Shift+F3` | Diff viewer: step changes" in _doc
      and "`Ctrl+U` | Diff viewer: split / unified" in _doc
      and "`Ctrl+1…5` | DevTools: switch tab" in _doc
      and "`Ctrl+Shift+C` | Text diff / Cheat sheet: copy" in _doc
      and "`Ctrl+C` / `Ctrl+E` | File stats: copy / export report" in _doc)
check("regression: the translator still knows the wave-2 keys",
      accel_pattern("F3") == "<F3>"
      and accel_pattern("Shift+F3") == "<Shift-F3>"
      and accel_pattern("Ctrl+U") == "<Control-u>"
      and accel_pattern("Ctrl+1") == "<Control-1>"
      and accel_pattern("Ctrl+Return") == "<Control-Return>"
      and accel_pattern("Ctrl+Shift+C") == "<Control-C>")
_audited, _broken = 0, []
for _label, _hint, _fn in app.palette_commands():
    if not str(_hint or "").startswith(("Ctrl", "Alt", "F")):
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
