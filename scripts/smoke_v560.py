"""DS2 v2.56.0 UI smoke — the desk grows eyes and tells no lies:
`lang diff [code]` prints the honest ledger (real translations vs
untouched seeds that still read English — a seeded pack can show
100% covered while 0% of it is real), pack_counts carries the
untouched counter, the desk's fifth filter chip reviews those seeds
in place and the meter prints them, and the live PackPreview renders
a slice of the studio in the pack being edited — keeping up with
every keystroke, accent for what the pack speaks and grey for the
English that shows through, closing with the desk that opened it.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v560.py

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

# ------------------------------------- the ledger, e2e
_d = le.pack_diff("es")
check("ledger: es speaks for every key",
      _d["name"] == "Español" and _d["seeds"] == []
      and "menu.file" in _d["real"] and _d["real_pct"] == 100)
le.save_user_pack("seedpack", dict(i18nmod.EN))
_d2 = le.pack_diff("seedpack")
check("ledger: a seeded pack is 100% covered and 0% real",
      _d2["real"] == [] and len(_d2["seeds"]) == len(i18nmod.EN)
      and _d2["real_pct"] == 0)
_c2 = le.pack_counts("seedpack")
check("counts: the honest counter agrees with the ledger",
      _c2["covered"] == _c2["total"]
      and _c2["untouched"] == len(_d2["seeds"]))
le.save_user_pack("mixed", {"menu.file": "MiArchivo",
                            "menu.edit": "Edit",
                            "menu.run": "İşlet",
                            "ghost.key": "old"})
_d3 = le.pack_diff("mixed")
check("ledger: real / seed / stale buckets are exact",
      _d3["real"] == ["menu.file", "menu.run"]
      and _d3["seeds"] == ["menu.edit"]
      and _d3["stale"] == ["ghost.key"])
check("ledger: unsafe is a property, not a bucket",
      _d3["unsafe"] == ["menu.run"]
      and "menu.run" in _d3["real"])
check("ledger: a junk code has nothing to say",
      le.pack_diff("nosuch")["real"] == []
      and sorted(le.pack_diff("nosuch")["missing"])
      == sorted(i18nmod.EN))


def _editors():
    return [w for w in root.winfo_children() if isinstance(w, le.PackEditor)]


def _previews():
    return [w for w in root.winfo_children()
            if isinstance(w, le.PackPreview)]


# ------------------------------------- the verb through the dispatcher
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))
try:
    app.handle_terminal_command("lang diff es")
    _blob = "\n".join(_logs)
    check("verb: `lang diff es` prints the ledger",
          "%d real translations" % len(i18nmod.EN) in _blob
          and "0 untouched seeds" in _blob and "100% real" in _blob)
    check("verb: the closing line names the meter that cannot lie",
          "real_pct cannot lie" in _blob)
    i18nmod.set_language("fr")
    _logs.clear()
    app.handle_terminal_command("lang diff")
    check("verb: bare `lang diff` names the current language",
          any("lang diff fr" in m for m in _logs))
    i18nmod.set_language("en")
    _logs.clear()
    app.handle_terminal_command("lang diff en")
    check("verb: the source of truth does not differ from itself",
          any("does not differ from itself" in m for m in _logs))
    _logs.clear()
    app.handle_terminal_command("lang diff NOPE!!")
    check("verb: unknown packs are refused with the list",
          any("unknown language" in m for m in _logs))
    _logs.clear()
    app.handle_terminal_command("lang diff seedpack")
    _blob = "\n".join(_logs)
    check("verb: a seeded pack's ledger shows its seeds",
          "%d untouched seeds" % len(i18nmod.EN) in _blob
          and "0 real translations" in _blob
          and "byte-identical to English" in _blob)
finally:
    app.terminal.log = _old_log

# ------------------------------------- the desk: chip + meter + ledger
app.handle_terminal_command("lang edit es")
root.update()
_desks = _editors()
check("verb: `lang edit es` opens the desk", len(_desks) == 1)
desk = _desks[0]
check("desk: the meter prints the untouched counter",
      "0 untouched" in desk.meter.cget("text"))
check("desk: five filter chips — All · Untouched · Missing · Stale · "
      "Unsafe", set(desk._chips) == {"all", "untouched", "missing",
                                     "stale", "unsafe"})
# clear one key, seed it back → exactly that key is untouched
desk._select_index(desk._row_keys.index("menu.file"))
desk._clear_key()
desk._seed_from_en()
desk._set_filter("untouched")
check("desk: the Untouched filter holds exactly the re-seeded key",
      desk._row_keys == ["menu.file"])
# editing it makes it real → out of the untouched bucket
desk._select_index(0)
desk.edit.delete("1.0", "end")
desk.edit.insert("1.0", "Archivador")
desk._flush_edit()
check("desk: an edited seed leaves the Untouched bucket",
      desk._row_keys == [] and desk.work.get("menu.file") == "Archivador")
desk._set_filter("all")

# ------------------------------------- the preview: eyes for the desk
_pv = desk._open_preview()
root.update()
check("preview: the desk grows eyes",
      isinstance(_pv, le.PackPreview) and _pv.winfo_exists()
      and _pv.desk is desk)
_labels = []
for _strip in _pv.body.winfo_children():
    for _w in _strip.winfo_children():
        if isinstance(_w, tk.Label):
            _labels.append(_w)
_texts = {w.cget("text") for w in _labels}
check("preview: the studio speaks the pack's strings",
      i18nmod.EN["menu.file"] not in _texts
      and "Archivador" in _texts
      and i18nmod.EN["app.tagline"] not in _texts)
_spoken = [w for w in _labels if w.cget("fg") == _pv.theme.accent]
check("preview: what the pack speaks wears the accent", bool(_spoken))
check("preview: six anatomy slices render",
      len(_pv.SLICES) == 6 and len(_labels)
      == sum(len(k) for _c, k in _pv.SLICES))

# the fallback path: a fresh desk shows English, all muted
_desk2 = le.PackEditor(app, "tlh")
root.update()
_pv2 = _desk2._open_preview()
root.update()
_labels2 = []
for _strip in _pv2.body.winfo_children():
    for _w in _strip.winfo_children():
        if isinstance(_w, tk.Label):
            _labels2.append(_w)
check("preview: a silent pack shows English through",
      i18nmod.EN["menu.file"] in {w.cget("text") for w in _labels2}
      and not [w for w in _labels2
               if w.cget("fg") == _pv2.theme.accent])
# live: type into the desk, the preview keeps up
_desk2._select_index(_desk2._row_keys.index("menu.save"))
_desk2.edit.delete("1.0", "end")
_desk2.edit.insert("1.0", "Waqtaq")
_desk2._flush_edit()
root.update()
_texts2 = {w.cget("text") for _strip in _pv2.body.winfo_children()
           for w in _strip.winfo_children() if isinstance(w, tk.Label)}
check("preview: it keeps up with every keystroke",
      "Waqtaq" in _texts2 and i18nmod.EN["menu.save"] not in _texts2)
check("preview: Ctrl+P re-opens the same window",
      _desk2._open_preview() is _pv2)
_pv2._close()
root.update()
check("preview: Esc hands the eyes back",
      _desk2._preview is None and not _pv2.winfo_exists())
_pv3 = _desk2._open_preview()
_desk2._close()
root.update()
check("preview: closing the desk closes its eyes",
      _pv3 is not None and not _previews())
desk._close()
root.update()

# ------------------------------------- help + docs agree
_vl = [r[0] for r in TERMINAL_HELP]
check("help: lang diff is a first-class verb", "lang diff [code]" in _vl)
with open(os.path.join("dxn1_studio", "langedit.py"),
          encoding="utf-8") as fh:
    _le = fh.read()
with open(os.path.join("dxn1_studio", "app.py"), encoding="utf-8") as fh:
    _ap = fh.read()
check("source: the ledger is written where it runs",
      "def pack_diff" in _le and "real_pct" in _le
      and '"lang diff [code]"' in _ap)
check("source: the eyes are plumbed through the desk",
      "class PackPreview" in _le and "_open_preview" in _le
      and "_refresh_preview" in _le)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "The Desk Grows Eyes" in _ft and "lang diff" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v560" in _ar)

# ------------------------------------- regression: the palette audit
_audited, _broken = 0, []
for _label, _hint, _fn in app.palette_commands():
    if not str(_hint or "").startswith(("Ctrl", "Alt", "F")):
        continue
    from dxn1_studio.app import accel_pattern
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
