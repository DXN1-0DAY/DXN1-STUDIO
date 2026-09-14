"""DS2 v2.57.0 UI smoke — packs travel light: the desk exports its
working copy as a JSON file shaped exactly like a user pack (what
the desk exports the desk imports, and set_language would layer it
over built-ins untouched), import overlays such a file onto the
working copy — desk exports, user packs and export_template files
alike, junk skipped and counted, empty values dropping keys back to
English, nothing written until Save; `lang audit` prints every
number (real_pct rides along per pack, skipped for en and unreadable
packs); the preview grows a buttons slice.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v570.py

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
from tkinter import filedialog  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

# ------------------------------------- the data layer
_tmp = tempfile.mkdtemp(prefix="ds2-packs-")
_dest = os.path.join(_tmp, "pack.json")
check("export: the working copy lands as a user-pack-shaped file",
      le.export_pack("esx", _dest,
                     work={"menu.file": "MiArchivo", "e": "   ",
                           7: "x", "k": 3}) == 1
      and json.load(open(_dest)) == {"menu.file": "MiArchivo"})
_own_dest = os.path.join(_tmp, "own.json")
_own_n = le.export_pack("es", _own_dest)
with open(_own_dest, encoding="utf-8") as fh:
    _own = json.load(fh)
check("export: without work it exports the pack's own strings",
      _own_n == len(_own) and _own.get("menu.file") == "Archivo"
      and set(_own) <= set(i18nmod.EN))
_target = {}
applied, skipped = le.merge_pack_file(_own_dest, _target)
check("import: the desk re-imports its own export",
      applied == _own_n and skipped == 0
      and _target.get("menu.file") == "Archivo")
_tmpl = os.path.join(_tmp, "tmpl.json")
i18nmod.export_template(_tmpl, "en")
_target = {}
applied, skipped = le.merge_pack_file(_tmpl, _target)
check("import: an export_template file imports whole",
      applied == len(i18nmod.EN) and skipped == 0
      and _target["menu.file"] == i18nmod.EN["menu.file"])
_bad = os.path.join(_tmp, "bad.json")
with open(_bad, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "Nuevo", "menu.view": "", "junk": 5}, fh)
_target = {"menu.file": "OLD", "menu.view": "Ver"}
applied, skipped = le.merge_pack_file(_bad, _target)
check("import: replace + empty-drops + junk-skipped, in place",
      applied == 2 and skipped == 1
      and _target["menu.file"] == "Nuevo"
      and "menu.view" not in _target)
_arr = os.path.join(_tmp, "arr.json")
with open(_arr, "w", encoding="utf-8") as fh:
    fh.write("[1,2]")
check("import: unreadable and non-dict files answer (-1, 0)",
      le.merge_pack_file(os.path.join(_tmp, "nope.json"),
                         _target) == (-1, 0)
      and le.merge_pack_file(_arr, _target) == (-1, 0))


def _editors():
    return [w for w in root.winfo_children() if isinstance(w, le.PackEditor)]


# ------------------------------------- the audit prints every number
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))
try:
    app.handle_terminal_command("lang audit")
    _blob = "\n".join(_logs)
    check("audit: real_pct rides along with the explanation",
          "% real" in _blob and "coverage can flatter" in _blob)
    _es = [m for m in _logs if m.strip().startswith("es ")][0]
    check("audit: es carries 100% real", "100% real" in _es)
    _en = [m for m in _logs if m.strip().startswith("en ")][0]
    check("audit: en is skipped — the source does not differ "
          "from itself", "% real" not in _en)
    le.save_user_pack("seedpack", dict(i18nmod.EN))
    _logs.clear()
    app.handle_terminal_command("lang audit")
    _sp = [m for m in _logs if m.strip().startswith("seedpack ")][0]
    check("audit: a seeded pack shows 100% covered and 0% real "
          "in one line", "100%" in _sp and "0% real" in _sp)
finally:
    app.terminal.log = _old_log

# ------------------------------------- the desk: dialog-driven E/I
app.handle_terminal_command("lang edit es")
root.update()
desk = _editors()[0]
_fdest = os.path.join(_tmp, "exported.json")
filedialog.asksaveasfilename = lambda **k: _fdest
filedialog.askopenfilename = lambda **k: _fdest
check("desk: export writes the working copy",
      desk._export_pack() is True
      and json.load(open(_fdest)).get("menu.file") == "Archivo")
desk.work["menu.file"] = "WILL-BE-REPLACED"
with open(_fdest, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "ReImportado", "junk": 5}, fh)
check("desk: import overlays the working copy, junk skipped",
      desk._import_pack() is True
      and desk.work.get("menu.file") == "ReImportado"
      and "junk" not in desk.work)
root.update()
check("desk: the meter keeps counting after an import",
      "untouched" in desk.meter.cget("text"))
with open(_fdest, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": ""}, fh)
check("desk: an empty value drops the key back to English",
      desk._import_pack() is True and "menu.file" not in desk.work)
filedialog.askopenfilename = lambda **k: _arr
check("desk: an unreadable import says so and changes nothing",
      desk._import_pack() is False
      and "menu.file" not in desk.work)
filedialog.askopenfilename = lambda **k: ""
filedialog.asksaveasfilename = lambda **k: ""
check("desk: cancelled dialogs change nothing",
      desk._import_pack() is False and desk._export_pack() is False)
# export → import → Save makes the file's strings live
with open(_fdest, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "DeArchivo"}, fh)
filedialog.askopenfilename = lambda **k: _fdest
desk._import_pack()
i18nmod.set_language("es")
_saved = desk._save()
root.update()
check("desk: import + Save goes live at once",
      _saved is True and i18nmod.tr("menu.file") == "DeArchivo")
i18nmod.set_language("en")
desk._close()
root.update()

# ------------------------------------- the preview's buttons slice
app.handle_terminal_command("lang edit tlh")
root.update()
_desk2 = [w for w in _editors() if w.code == "tlh"][0]
_pv = _desk2._open_preview()
root.update()
_caps = [w.cget("text") for w in _pv.body.winfo_children()
         if isinstance(w, tk.Label)]
_texts = {w.cget("text") for _strip in _pv.body.winfo_children()
          for w in _strip.winfo_children() if isinstance(w, tk.Label)}
check("preview: six slices — the buttons row joined",
      len(_pv.SLICES) == 6 and "BUTTONS" in _caps)
check("preview: the common buttons render in the pack",
      i18nmod.EN["common.export"] in _texts
      and i18nmod.EN["common.copy"] in _texts)
_desk2._close()
root.update()

# ------------------------------------- help + docs agree
with open(os.path.join("dxn1_studio", "langedit.py"),
          encoding="utf-8") as fh:
    _le = fh.read()
with open(os.path.join("dxn1_studio", "app.py"), encoding="utf-8") as fh:
    _ap = fh.read()
check("source: the travel desks are written where they run",
      "def export_pack" in _le and "def merge_pack_file" in _le
      and "_export_pack" in _le and "_import_pack" in _le
      and '"buttons"' in _le)
check("source: the audit prints every number",
      "coverage can flatter" in _ap and "%d%% real" in _ap)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "Packs Travel Light" in _ft and "Export pack" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v570" in _ar)

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
shutil.rmtree(_tmp, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
