"""DS2 v2.50.0 UI smoke — hint bars wave 3: ten more windows get their
door sign, and every advertised key is really bound FIRST. The five
converter-lab windows (xmlbench, csvkit, unitconv, hexdump, pwdgen)
and mathpad had ZERO window keys before this wave; copy keys use
<Control-C>, the canonical spelling of Ctrl+Shift+C (Ctrl+Shift+c
arrives as keysym 'C', and the input widgets keep their native Ctrl+c
copy); the AI quick-action result window and its launcher menu gain
keys, with number keys running actions straight from the menu.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v500.py

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
from dxn1_studio.pwdgen import PassForge  # noqa: E402
from dxn1_studio.xmlbench import XmlBench  # noqa: E402
from dxn1_studio.csvkit import CsvLab  # noqa: E402
from dxn1_studio.unitconv import UnitConverter  # noqa: E402
from dxn1_studio.hexdump import ByteSnoop  # noqa: E402
from dxn1_studio.mathpad import MathPad  # noqa: E402
from dxn1_studio.branches import BranchManager  # noqa: E402
from dxn1_studio.gallery import TemplateGallery  # noqa: E402
from dxn1_studio.sqlitelab import SQLiteLab  # noqa: E402
from dxn1_studio.quick_actions import (ResultWindow, ActionsMenu,  # noqa: E402
                                       ACTIONS)

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

root = app.root
t = Theme("dark", "violet")


def bar_of(win):
    bars = [w for w in win.winfo_children()
            if getattr(w, "filled", None)]
    check("bar filled: " + type(win).__name__, bool(bars))
    return bars[0] if bars else None


def honest(win, bar, expect, label):
    ok = bar is not None and not bar.dropped_hints
    ch = []
    if bar is not None:
        for w in bar.winfo_children():
            try:
                ch.append(str(w.cget("text")))
            except Exception:
                pass
    for want in expect:
        if not any(want in s for s in ch):
            ok = False
    for entry in (bar.pairs if bar is not None else ()):
        pat = accel_pattern(entry[0])
        if not pat or not hints.tree_bound(win, pat):
            ok = False
    check("honest bar (" + label + ")", ok)


def key(win, pattern):
    win.focus_force()
    root.update()
    win.event_generate(pattern, when="now")
    root.update()


# --- pwdgen: zero window keys before this wave — now F5 + copy + Esc
pf = PassForge(root, t)
root.update()
honest(pf, bar_of(pf), ["Esc", "F5", "new password",
                        "Ctrl+Shift+C", "copy"], "pwdgen")
first = pf.out.get()
key(pf, "<F5>")
check("pwdgen F5 regenerates", pf.out.get() != first)
pf._copy()
check("pwdgen copy puts the secret on the clipboard",
      root.clipboard_get() == pf.out.get())
pf.destroy()

# --- xmlbench: Ctrl+P pretty / Ctrl+M minify / Ctrl+Shift+C copy
xb = XmlBench(root, t, initial="<a><b>x</b></a>")
root.update()
honest(xb, bar_of(xb), ["Ctrl+P", "pretty", "Ctrl+M", "minify",
                        "Ctrl+Shift+C", "copy output",
                        "live parse"], "xmlbench")
key(xb, "<Control-p>")
pretty = xb.output.get("1.0", "end-1c")
check("xmlbench Ctrl+P pretty-prints", "<b>" in pretty and "\n" in pretty)
key(xb, "<Control-m>")
check("xmlbench Ctrl+M minifies",
      "\n" not in xb.output.get("1.0", "end-1c"))
key(xb, "<Control-C>")
check("xmlbench copy key ships the output", "<" in root.clipboard_get())
xb.destroy()

# --- csvkit: Ctrl+Shift+C copies the table as TSV
cv = CsvLab(root, t, initial="a,b\n1,2\n3,4")
root.update()
honest(cv, bar_of(cv), ["Ctrl+Shift+C", "copy as TSV",
                        "live table"], "csvkit")
key(cv, "<Control-C>")
clip = root.clipboard_get()
check("csvkit copy lands as TSV", "a\tb" in clip and "3\t4" in clip)
cv.destroy()

# --- unitconv: Ctrl+R swaps, Ctrl+Shift+C copies the result
uc = UnitConverter(root, t)
root.update()
honest(uc, bar_of(uc), ["Ctrl+R", "swap units",
                        "Ctrl+Shift+C", "copy result"], "unitconv")
frm, to = uc.frm.get(), uc.to.get()
key(uc, "<Control-r>")
check("unitconv Ctrl+R swaps units",
      (uc.frm.get(), uc.to.get()) == (to, frm))
uc._copy()
check("unitconv copy puts the result on the clipboard",
      root.clipboard_get().strip() != "")
uc.destroy()

# --- hexdump: Ctrl+Shift+C copies the dump
hx = ByteSnoop(root, t, initial="AB")
root.update()
honest(hx, bar_of(hx), ["Ctrl+Shift+C", "copy dump",
                        "hex + ascii"], "hexdump")
key(hx, "<Control-C>")
check("hexdump copy ships hex bytes", "41" in root.clipboard_get())
hx.destroy()

# --- mathpad: Return already lived on the entry — now advertised
mp = MathPad(root, t, initial="6*7")
root.update()
honest(mp, bar_of(mp), ["Return", "evaluate", "Ctrl+Shift+C",
                        "copy result"], "mathpad")
check("mathpad Return is backed by the entry",
      hints.tree_bound(mp, "<Return>"))
mp.entry.delete(0, "end")
mp.entry.insert(0, "2+3")
key(mp.entry, "<Return>")
check("mathpad Return evaluates", "= 5" in mp.result.cget("text"))
mp._copy_result()
check("mathpad copy ships the result", root.clipboard_get() == "5")
mp.destroy()

# --- branches: F5 refresh joins Esc/Return on a real repo
repo = tempfile.mkdtemp(prefix="ds2-br-")
env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="a@b",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="a@b")
subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, env=env,
               capture_output=True)
subprocess.run(["git", "commit", "-qm", "x", "--allow-empty"], cwd=repo,
               env=env, capture_output=True)
bm = BranchManager(root, t, repo)
root.update()
honest(bm, bar_of(bm), ["Return", "new branch", "F5", "refresh",
                        "double-click"], "branches")
check("branches F5 really bound", hints.tree_bound(bm, "<F5>"))
bm.destroy()

# --- gallery: Ctrl+F really lands in the search box
gal = TemplateGallery(root, {"gallery_favs": []}, t.accent,
                      lambda k: None)
root.update()
honest(gal, bar_of(gal), ["Ctrl+F", "search", "F5", "re-filter",
                          "star"], "gallery")
gal.focus_force()
root.update()
gal.event_generate("<Control-f>", when="now")
root.update()
check("gallery Ctrl+F focuses search",
      str(root.focus_get()) == str(gal.search))
gal.destroy()

# --- sqlitelab: its F5/Esc finally signed
db = os.path.join(tempfile.mkdtemp(prefix="ds2-db-"), "t.db")
sl = SQLiteLab(root, t, db_path=db)
root.update()
honest(sl, bar_of(sl), ["Esc", "F5", "run query"], "sqlitelab")
sl.destroy()

# --- quick actions: result keys + launcher number keys
class _StubCfg:
    def get(self, _k, d=None):
        return d


class _StubApp:
    def __init__(self, root):
        self.root = root
        self.theme = t
        self.config = _StubCfg()
        self.editor = type("E", (), {"text": tk.Text(root)})()
        self.toast_msgs = []
        self.toast = lambda m, kind="info": self.toast_msgs.append(m)


stub = _StubApp(root)
rw = ResultWindow(root, t, "tw", "explain", app=stub,
                  code="print(1)\n", on_log=lambda m: None)
root.update()
honest(rw, bar_of(rw), ["Ctrl+Shift+C", "copy answer", "Ctrl+R",
                        "Ctrl+Shift+I"], "result window")
rw.text.insert("1.0", "THE-ANSWER")
key(rw, "<Control-C>")
check("result window copy ships the answer",
      root.clipboard_get() == "THE-ANSWER")
rw.destroy()
picked = []
am = ActionsMenu(stub)
root.update()
b = bar_of(am)
honest(am, b, ["Esc", "1", "2"], "actions menu")
check("menu advertises every action",
      len(b.pairs) == len(ACTIONS))
am._pick = lambda a: picked.append(a)
key(am, "<Key-2>")
key(am, "<Key-1>")
check("menu number keys run actions",
      picked == [list(ACTIONS)[1], list(ACTIONS)[0]])
am.destroy()

# ------------------------------------------------- pins + agreement
check("regression: the translator still knows the wave-2 keys",
      accel_pattern("Ctrl+Shift+C") == "<Control-C>")
check("the translator canonicalizes the wave-3 keys",
      accel_pattern("Ctrl+P") == "<Control-p>"
      and accel_pattern("Ctrl+M") == "<Control-m>"
      and accel_pattern("Ctrl+R") == "<Control-r>"
      and accel_pattern("Ctrl+F") == "<Control-f>"
      and accel_pattern("F5") == "<F5>"
      and accel_pattern("Return") == "<Return>"
      and accel_pattern("1") == "<1>"
      and accel_pattern("Ctrl+Shift+I") == "<Control-I>")

_src = {}
for _mod in ("xmlbench.py", "csvkit.py", "unitconv.py", "hexdump.py",
             "mathpad.py", "pwdgen.py", "branches.py", "gallery.py",
             "sqlitelab.py", "quick_actions.py", "hints.py"):
    with open(os.path.join("dxn1_studio", _mod), encoding="utf-8") as fh:
        _src[_mod] = fh.read()
check("source agreement: every wave-3 window wires a hint bar",
      all("hints.hint_bar(" in s for _n, s in _src.items()
          if _n != "hints.py"))
check("source agreement: bars are introspectable",
      "bar.pairs = " in _src["hints.py"])
check("source agreement: copy keys use the canonical spelling",
      'self.bind("<Control-C>"' in _src["xmlbench.py"]
      and 'self.bind("<Control-C>"' in _src["csvkit.py"]
      and 'self.bind("<Control-C>"' in _src["hexdump.py"]
      and 'self.bind("<Control-C>"' in _src["mathpad.py"]
      and 'self.bind("<Control-C>"' in _src["pwdgen.py"]
      and 'self.bind("<Control-C>"' in _src["quick_actions.py"])
with open(os.path.join("docs", "KEYBINDINGS.md"), encoding="utf-8") as fh:
    _kb = fh.read()
check("doc agreement: the v2.50 section exists",
      "## Tool windows (v2.50)" in _kb)
check("doc agreement: the new rows tell the truth",
      "`Ctrl+P` / `Ctrl+M` | XML bench: pretty / minify" in _kb
      and "`Ctrl+R` | Unit converter: swap units" in _kb
      and "`1…7` | AI quick actions menu: run that action" in _kb)

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
      % _audited, _audited >= 15 and not _broken)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)
shutil.rmtree(repo, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
