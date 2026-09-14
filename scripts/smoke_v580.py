"""DS2 v2.58.0 UI smoke — the pack gets a checkup: check_mapping
reads a mapping the way an import WOULD and reports unknown keys,
empty values, junk pairs and highlight-unsafe strings before
anything moves; check_pack reviews an installed pack (what the
runtime speaks), check_pack_file reviews a file and answers
honestly for unreadable ones; `lang check [code|file]` opens both
doors with one verdict line each, and `lang pack <code> [dest]`
exports a pack without opening the desk — never overwriting what
is already there.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v580.py

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
from dxn1_studio.app import DXN1Studio, TERMINAL_HELP  # noqa: E402
from dxn1_studio import i18n as i18nmod  # noqa: E402
from dxn1_studio import langedit as le  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

# ------------------------------------- the data layer
_tmp = tempfile.mkdtemp(prefix="ds2-checkup-")
_rep = le.check_mapping({"menu.file": "MiArchivo",
                         "menu.edit": i18nmod.EN["menu.edit"],
                         "junk.key": "x", "menu.view": "   "})
check("checkup: a mixed mapping lands in the right buckets",
      _rep["pairs"] == 4 and _rep["real"] == 1 and _rep["seeds"] == 1
      and _rep["unknown"] == ["junk.key"]
      and _rep["empty"] == ["menu.view"]
      and _rep["real_pct"] == int(round(100.0 / len(i18nmod.EN))))
check("checkup: junk pairs are counted the way an import skips them",
      le.check_mapping({"k": 3, 5: "x", None: "y"})["junk"] == 3)
check("checkup: unsafe is a property of the value — stale keys "
      "included",
      le.check_mapping({"a.b": "İstanbul"})["unsafe"] == ["a.b"]
      and le.check_mapping({"a.b": "İstanbul"})["unknown"] == ["a.b"])
check("checkup: es speaks for itself — clean, every number full",
      le.check_pack("es")["real_pct"] == 100
      and le.check_pack("es")["covered_pct"] == 100
      and le.check_pack("es")["unknown"] == [])
_good = os.path.join(_tmp, "good.json")
with open(_good, "w", encoding="utf-8") as fh:
    json.dump({"menu.file": "MiArchivo", "junk.key": "x",
               "menu.view": ""}, fh)
_frep = le.check_pack_file(_good)
check("checkup: a file answers with the same report",
      _frep["ok"] and _frep["pairs"] == 3
      and _frep["unknown"] == ["junk.key"]
      and _frep["empty"] == ["menu.view"])
_arr = os.path.join(_tmp, "arr.json")
with open(_arr, "w", encoding="utf-8") as fh:
    fh.write("[1,2]")
_bad = os.path.join(_tmp, "bad.json")
with open(_bad, "w", encoding="utf-8") as fh:
    fh.write("{nope")
check("checkup: unreadable and non-dict files refuse honestly",
      not le.check_pack_file(_arr)["ok"]
      and le.check_pack_file(_arr)["error"] == "not a JSON object"
      and le.check_pack_file(_bad)["error"] == "JSONDecodeError"
      and le.check_pack_file(os.path.join(_tmp, "nope.json"))[
          "error"] == "FileNotFoundError")
le.save_user_pack("seed58", dict(i18nmod.EN))
_srep = le.check_pack("seed58")
check("checkup: a seeded pack is structurally clean and 0% real",
      _srep["seeds"] == len(i18nmod.EN) and _srep["real"] == 0
      and _srep["real_pct"] == 0 and _srep["covered_pct"] == 100
      and _srep["unknown"] == [])

# ------------------------------------- the verbs
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))


def _run(cmd):
    _logs.clear()
    app.handle_terminal_command(cmd)
    return "\n".join(_logs)


try:
    check("verb: bare lang check with en current refuses honestly",
          "nothing to check" in _run("lang check"))
    i18nmod.set_language("es")
    _blob = _run("lang check")
    i18nmod.set_language("en")
    check("verb: bare lang check with a pack current reviews it",
          "lang check es" in _blob and "verdict: clean" in _blob)
    _blob = _run("lang check es")
    check("verb: named pack — head, ledger line, verdict, way out",
          "lang check es — Español [built-in]" in _blob
          and "coverage 100%" in _blob and "100% real" in _blob
          and "verdict: clean" in _blob
          and "share it with lang pack es" in _blob)
    _blob = _run("lang check seed58")
    check("verb: a seeded pack reads 0% real in one breath",
          "0% real" in _blob and "verdict: clean" in _blob
          and "though %d strings still read English" % len(i18nmod.EN)
          in _blob)
    check("verb: unknown code and no file — both doors named",
          "unknown language 'nosuch' and no such file"
          in _run("lang check nosuch"))
    _blob = _run("lang check %s" % _good)
    check("verb: file mode names every finding and counts the verdict",
          "1 unknown key — the source never names it" in _blob
          and "1 empty value — an import drops it back to English"
          in _blob and "verdict: 2 findings" in _blob
          and "import it from the desk" in _blob)
    check("verb: an unreadable file says so",
          "unreadable (JSONDecodeError)" in _run("lang check %s" % _bad))

    _dest = os.path.join(_tmp, "out", "es.json")
    os.makedirs(os.path.dirname(_dest), exist_ok=True)
    _blob = _run("lang pack es %s" % _dest)
    _data = json.load(open(_dest, encoding="utf-8"))
    check("verb: lang pack writes the pack's own strings",
          "wrote" in _blob and str(_dest) in _blob
          and _data.get("menu.file") == "Archivo"
          and set(_data) <= set(i18nmod.EN))
    check("verb: lang pack never overwrites — sharing does not "
          "destroy",
          "already exists — not overwriting"
          in _run("lang pack es %s" % _dest))
    check("verb: en is refused — the source is not shared",
          "nothing to share" in _run(
              "lang pack en %s" % os.path.join(_tmp, "en.json")))
    check("verb: bare lang pack prints the usage",
          "usage: lang pack <code> [dest]" in _run("lang pack"))
    check("verb: unknown code lists what is available",
          "unknown language 'nosuch'" in _run("lang pack nosuch"))
    _blob = _run("lang pack fr %s" % os.path.dirname(_dest))
    check("verb: a directory dest lands <code>.json inside it",
          os.path.exists(os.path.join(os.path.dirname(_dest), "fr.json"))
          and "wrote" in _blob)
finally:
    app.terminal.log = _old_log

# ------------------------------------- help + docs agree
_vl = [r[0] for r in TERMINAL_HELP]
check("help: lang check and lang pack are first-class verbs",
      "lang check [code|file]" in _vl and "lang pack <code> [dest]"
      in _vl)
with open(os.path.join("dxn1_studio", "langedit.py"),
          encoding="utf-8") as fh:
    _le = fh.read()
with open(os.path.join("dxn1_studio", "app.py"), encoding="utf-8") as fh:
    _ap = fh.read()
check("source: the checkup is written where it runs",
      "def check_mapping" in _le and "def check_pack(" in _le
      and "def check_pack_file" in _le
      and "def _emit_checkup" in _ap and "not overwriting" in _ap)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "The Pack Gets a Checkup" in _ft and "lang check" in _ft
      and "lang pack" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v580" in _ar)

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
