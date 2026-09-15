"""DS2 v2.61.0 UI smoke — the fix gets a safety net and moves into
the desk: fix_pack_file writes the pre-fix copy beside the pack as
`<code>.json.bak` BEFORE anything moves, `lang unfix <code>`
restores it and CONSUMES the backup (an undo you cannot run twice
by accident, an active language re-activating live); the desk's
Apply safe fixes button cuts the dead weight from the working copy
at one click with the verdict turning green on its own; and the
v2.55 width pattern becomes one shared helper — geom.fit_to_content
— now riding eight more fixed windows (todo results, what's new,
terminal verbs, usage dashboard, packages, session restore, agent
memory, sqlite lab).

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v610.py

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
from dxn1_studio import i18n as i18nmod  # noqa: E402
from dxn1_studio import langedit as le  # noqa: E402
from dxn1_studio import geom  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

_lang_dir = i18nmod.LANG_DIR
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))


def _run(cmd):
    _logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(_logs)


# ------------------------------------- the safety net + the way back
os.makedirs(_lang_dir, exist_ok=True)
_p = os.path.join(_lang_dir, "net60.json")
_pre = {"menu.file": "MiArchivoX", "dead.key": "zzz", "menu.view": "Ver"}
with open(_p, "w", encoding="utf-8") as fh:
    json.dump(_pre, fh)
_blob = _run("lang fix net60")
check("verb: the fix announces its safety net",
      "lang unfix net60" in _blob and ".bak" in _blob)
_bak = _p + ".bak"
check("verb: the pre-fix copy is on disk",
      os.path.exists(_bak)
      and json.load(open(_bak, encoding="utf-8")) == _pre)
_blob = _run("lang unfix net60")
check("verb: unfix restores and consumes",
      "restored 3 strings" in _blob and "cannot run twice" in _blob
      and json.load(open(_p, encoding="utf-8")) == _pre
      and not os.path.exists(_bak))
check("verb: a second unfix is refused honestly",
      "no backup to undo" in _run("lang unfix net60"))
check("verb: the gates lang fix has, unfix has too",
      "usage: lang unfix <code>" in _run("lang unfix")
      and "nothing to unfix" in _run("lang unfix en")
      and "unknown language" in _run("lang unfix nosuch"))
# re-activation
with open(_p, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "ArchivoX", "old.k": "x"}, fh)
_run("lang fix net60")
i18nmod.set_language("net60")
_blob = _run("lang unfix net60")
i18nmod.set_language("en")
check("verb: the restored pack goes live at once",
      "the restored pack is live at once" in _blob
      and json.load(open(_p, encoding="utf-8"))
      == {"menu.file": "ArchivoX", "old.k": "x"})

# ------------------------------------- the desk fixes itself
app.handle_terminal_command("lang edit es")
root.update()
_desk = [w for w in root.winfo_children()
         if isinstance(w, le.PackEditor)][0]
check("desk: the button is there",
      _desk.fix_btn.cget("text") == "Apply safe fixes")
_desk.work["junk.key"] = "x"
_desk.work["dead2"] = "y"
_desk._run_check()
check("desk: the verdict names the dead weight first",
      "2 unknown" in _desk.verdict.cget("text"))
_logs.clear()
_n = _desk._apply_safe_fixes()
root.update()
check("desk: one click cuts the dead weight",
      _n == 2 and "junk.key" not in _desk.work
      and "dead2" not in _desk.work
      and "✓" in _desk.verdict.cget("text")
      and "applied safe fixes — cut 2 unknown keys" in "\n".join(_logs))
_n = _desk._apply_safe_fixes()
check("desk: nothing to fix answers honestly",
      _n == 0 and _desk.status.cget("text") == "nothing to fix")
_desk.work["menu.file"] = "İstanbul"
_n = _desk._apply_safe_fixes()
check("desk: unsafe strings survive (a deletion is not a translation)",
      _n == 0 and _desk.work.get("menu.file") == "İstanbul")
_desk._close()
root.update()

# ------------------------------------- the shared width helper
_win = tk.Toplevel(root)
tk.Label(_win, text="W" * 200).pack(padx=10, pady=10)
_applied = geom.fit_to_content(_win, 400, 300)
root.update()
check("helper: grows past the floor when content asks",
      _win.winfo_width() >= _win.winfo_reqwidth() - 2 >= 400
      and _applied.endswith("x300"))
_win.destroy()
_win2 = tk.Toplevel(root)
tk.Label(_win2, text="Z" * 200).pack(padx=10, pady=10)
geom.fit_to_content(_win2, 300, 200, ratchet=True)
root.update()
_wide = _win2.winfo_width()
tk.Label(_win2, text="s").pack(padx=1, pady=1)
geom.fit_to_content(_win2, 300, 200, ratchet=True)
root.update()
check("helper: the ratchet holds the high-water mark",
      _win2.winfo_width() >= _wide - 2
      and _win2._fit_size[0] >= _wide - 2)
_win2.destroy()
root.update()

app.terminal.log = _old_log

# ------------------------------------- help + docs agree
with open(os.path.join("dxn1_studio", "langedit.py"),
          encoding="utf-8") as fh:
    _le = fh.read()
check("source: the safety net is written where it runs",
      "def undo_fix_file" in _le and "_apply_safe_fixes" in _le
      and ".bak" in _le and "an undo you cannot run twice by accident"
      in _le)
with open(os.path.join("dxn1_studio", "geom.py"),
          encoding="utf-8") as fh:
    _gs = fh.read()
check("source: the shared helper lives in geom",
      "def fit_to_content" in _gs and "ratchet" in _gs)
_converted = 0
for _m, _mk in (("app.py", "fit_to_content(win, 720, 420)"),
                ("whatsnew.py", "fit_to_content(win, 780, 560)"),
                ("verbs.py", "fit_to_content(win, 640, 520)"),
                ("usagedash.py", "fit_to_content(self, 720, 600)"),
                ("packages.py", "fit_to_content(self, 800, 620)"),
                ("session.py", "fit_to_content(self, 620, 380)"),
                ("memory.py", "fit_to_content(self, 640, 540)"),
                ("sqlitelab.py", "fit_to_content(self, 1000, 640)")):
    with open(os.path.join("dxn1_studio", _m), encoding="utf-8") as fh:
        if _mk in fh.read():
            _converted += 1
check("source: eight more windows ride the helper (%d/8)"
      % _converted, _converted == 8)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "A Safety Net for the Fix" in _ft and "fit_to_content" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v610" in _ar)

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
