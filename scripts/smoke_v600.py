"""DS2 v2.60.0 UI smoke — the checkup comes home and learns to
heal: the desk runs the checkup on its own working copy
(automatically on every Import, on demand by button or Ctrl+T) and
the verdict lives under the meter — red for findings, green for
clean, recomputed silently on every change once asked for;
`lang fix <code>` applies the safe repairs the checkup names to a
user pack file (junk dropped, empty values back to English, unknown
keys cut — nothing written unless something changes, unsafe strings
never touched because a deletion is not a translation); and width
accounting round two beyond the pack windows: the Project Hub opens
no narrower (or shorter) than what it actually packed.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v600.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest.mock as mock

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

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

_lang_dir = i18nmod.LANG_DIR


def _editors():
    return [w for w in root.winfo_children() if isinstance(w, le.PackEditor)]


# ------------------------------------- the verb: the check is the dry-run
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))


def _run(cmd):
    _logs.clear()
    app.handle_terminal_command(cmd)
    root.update()
    return "\n".join(_logs)


check("verb: bare lang fix names the dry-run",
      "usage: lang fix <code>" in _run("lang fix")
      and "lang check <code> is the dry-run" in "\n".join(_logs))
check("verb: en is refused", "nothing to fix" in _run("lang fix en"))
check("verb: a built-in without a user pack says so",
      "no user pack file to fix" in _run("lang fix es")
      and "built-ins are read-only here" in "\n".join(_logs))
check("verb: unknown language named",
      "unknown language 'nosuch'" in _run("lang fix nosuch"))

# a dirty user pack, hand-written (save_user_pack refuses empties)
os.makedirs(_lang_dir, exist_ok=True)
_dirty = os.path.join(_lang_dir, "dirty60.json")
with open(_dirty, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "MiArchivoX", "dead.key": "zzz",
               "menu.edit": "", "menu.view": "Ver",
               "num": 123}, fh)
_blob = _run("lang fix dirty60")
check("verb: findings by name, every number",
      "1 unknown key cut (dead.key)" in _blob
      and "1 empty value back to English (menu.edit)" in _blob
      and "1 junk pair dropped" in _blob and "2 strings kept" in _blob)
with open(_dirty, encoding="utf-8") as fh:
    _after = json.load(fh)
check("verb: the file on disk is repaired",
      _after == {"menu.file": "MiArchivoX", "menu.view": "Ver"})
check("verb: already clean answers with the kept count",
      "already clean" in _run("lang fix dirty60")
      and "2 strings kept" in "\n".join(_logs))
# unsafe strings are NOT touched — a deletion is not a translation
_unsafe = os.path.join(_lang_dir, "unsafe60.json")
with open(_unsafe, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "İstanbul"}, fh)
_run("lang fix unsafe60")
with open(_unsafe, encoding="utf-8") as fh:
    check("verb: unsafe strings survive the fix",
          json.load(fh) == {"menu.file": "İstanbul"})
# an active language re-activates, repaired pack live at once
with open(os.path.join(_lang_dir, "live60.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"menu.file": "Archivo", "stale.old": "x"}, fh)
i18nmod.set_language("live60")
_blob = _run("lang fix live60")
check("verb: the repaired pack goes live at once",
      "the repaired pack is live at once" in _blob
      and i18nmod.tr("menu.file") == "Archivo")
i18nmod.set_language("en")
# lang check's hint names the fix
check("check: the hint names the fix as the way out",
      "apply the safe fixes with lang fix es" in _run("lang check es"))
# the audit names the whole family, fix included
check("audit: the family line grew the fix",
      "lang fix <code>" in _run("lang audit"))

# ------------------------------------- the desk: the checkup comes home
app.handle_terminal_command("lang edit es")
root.update()
_desk = _editors()[0]
check("desk: the verdict starts empty — asked for, not assumed",
      _desk.verdict.cget("text") == "" and not _desk._checked)
check("desk: the button and the gesture exist",
      _desk.check_btn.cget("text") == "Check this pack"
      and bool(_desk.bind("<Control-t>")))

_dirt = os.path.join(HOME, "dirt.json")
with open(_dirt, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "MiArchivo", "junk.key": "x",
               "menu.view": "  "}, fh)
_logs.clear()
with mock.patch("tkinter.filedialog.askopenfilename",
                return_value=_dirt):
    _desk._import_pack()
root.update()
_v = _desk.verdict.cget("text")
# the import itself applies the empty→English rule and skips junk,
# so what REMAINS is the unknown key — the verdict says so, in red
check("desk: an import runs the checkup itself",
      _desk._checked and "1 finding" in _v and "1 unknown" in _v)
check("desk: the verdict wears red for findings",
      _desk.verdict.cget("foreground") == "#f85149")
_blob = "\n".join(_logs)
check("desk: the full findings reach the terminal renderer",
      "the desk's working copy" in _blob
      and "verdict: 1 finding" in _blob
      and "apply the safe fixes with lang fix es" in _blob)

# the verdict keeps up as the working copy changes — silently
_desk.work.pop("junk.key", None)
_desk._verdict_tick()
root.update()
_v2 = _desk.verdict.cget("text")
check("desk: green when clean — and honest about the 99%",
      "✓" in _v2 and "checkup clean" in _v2
      and "99% real" in _v2
      and _desk.verdict.cget("foreground") == "#3fb950")
_desk.work["menu.file"] = "İstanbul"
_desk._verdict_tick()
_v3 = _desk.verdict.cget("text")
check("desk: an unsafe string turns it red again",
      "1 unsafe" in _v3 and "⚠" in _v3
      and _desk.verdict.cget("foreground") == "#f85149")
_desk._close()
root.update()

# ------------------------------------- width sweep round two
from dxn1_studio import hub as hubmod  # noqa: E402
_real_hub = app._hub if getattr(app, "_hub", None) else None
_hub = hubmod.ProjectHub(root, app.config, app.theme,
                         on_open=lambda *a: None,
                         on_explore=lambda *a: None)
root.update()
check("hub: opens no narrower than what it packed",
      _hub.winfo_width() >= hubmod.HUB_W
      and _hub.winfo_width() >= _hub.winfo_reqwidth() - 2)
check("hub: the request really did beat the 940 default "
      "(the old fixed geometry was clipping)",
      _hub.winfo_reqwidth() > hubmod.HUB_W
      or _hub.winfo_reqheight() > hubmod.HUB_H)
_hub._teardown()
root.update()

app.terminal.log = _old_log

# ------------------------------------- help + docs agree
with open(os.path.join("dxn1_studio", "langedit.py"),
          encoding="utf-8") as fh:
    _le = fh.read()
check("source: the repair and the verdict are written where they run",
      "def fix_pack_file" in _le and "def _run_check" in _le
      and "def _verdict_tick" in _le
      and "a deletion is not" in _le)
with open(os.path.join("dxn1_studio", "app.py"), encoding="utf-8") as fh:
    _apsrc = fh.read()
check("source: the verb is advertised",
      '"lang fix <code>"' in _apsrc)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "The Checkup Comes Home" in _ft and "lang fix" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v600" in _ar)

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
