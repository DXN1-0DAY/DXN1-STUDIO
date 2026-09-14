"""DS2 v2.55.0 UI smoke — the translator gets a desk: the new
langedit module edits any language pack beside its English source
(missing / stale / highlight-unsafe marked at a glance), the
`lang edit [code]` verb and a Settings click both open it, saving
writes an atomic user pack that overrides built-ins and goes live
the moment its pack is active, the chooser refuses junk codes and
the source of truth itself, and the AI quick-actions launcher grows
to fit what it packed instead of clipping at a fixed width.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v550.py

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
from dxn1_studio.app import (DXN1Studio, SettingsDialog,  # noqa: E402
                             TERMINAL_HELP, accel_pattern)
from dxn1_studio import i18n as i18nmod  # noqa: E402
from dxn1_studio import langedit as le  # noqa: E402
from dxn1_studio import quick_actions as qa  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

# ------------------------------------- the data layer, e2e
check("data: es speaks for itself",
      le.own_translations("es").get("menu.file") == "Archivo")
check("data: en is the source, never a pack",
      le.own_translations("en") == {})
check("data: the working dict falls back to English",
      le.pack_working("nosuch") == dict(i18nmod.EN)
      and le.pack_working("es")["menu.file"] == "Archivo")
check("data: the İ predicate matches the v2.54 contract",
      le.is_unsafe("İstanbul") and not le.is_unsafe("")
      and not le.is_unsafe("plain ascii"))
_counts = le.pack_counts("es")
check("data: the meter counts like the audit does",
      _counts["covered"] == _counts["total"] == len(i18nmod.EN)
      and _counts["pct"] == 100 and _counts["missing"] == 0)


def _editors():
    return [w for w in root.winfo_children() if isinstance(w, le.PackEditor)]


def _choosers():
    return [w for w in root.winfo_children()
            if isinstance(w, le.PackChooser)]


# ------------------------------------- the desk through the real verb
app.handle_terminal_command("lang edit es")
root.update()
_desks = _editors()
check("verb: `lang edit es` opens the desk", len(_desks) == 1)
desk = _desks[0]
check("desk: the header meter is honest",
      desk.code == "es" and "100%" in desk.meter.cget("text")
      and "0 missing" in desk.meter.cget("text"))
check("desk: every English key has a row",
      len(desk._row_keys) == len(i18nmod.EN))
check("desk: translated rows wear the ● marker",
      desk._marker(desk._state_of("menu.file",
                                  desk.work.get("menu.file"))) == "●")
check("desk: a missing row wears the ○ marker",
      desk._marker(desk._state_of("menu.nope", None)) == "○")
check("desk: a stale row wears the ✕ marker",
      desk._marker(desk._state_of("old.thing", "x")) == "✕")

# ------------------------------------- live editing, live warnings
desk._select_index(0)
_key = desk._current
desk.edit.delete("1.0", "end")
desk.edit.insert("1.0", "DeskValue")
desk._flush_edit()
check("desk: typing commits into the working copy",
      desk.work.get(_key) == "DeskValue")
desk.edit.delete("1.0", "end")
desk.edit.insert("1.0", "İçerik")
desk._flush_edit()
root.update()
check("desk: an unsafe string is flagged in so many words",
      "NOT highlight-safe" in desk.warn.cget("text"))
check("desk: the unsafe marker wins the row glyph",
      desk._state_of(_key, "İçerik") == "unsafe"
      and desk._marker("unsafe") == "⚠")
desk._set_filter("unsafe")
check("desk: the Unsafe filter holds exactly the İ key",
      desk._row_keys == [_key])
desk._set_filter("all")

# ------------------------------------- clear + seed, then save
desk._clear_key()
check("desk: clearing puts English back (missing again)",
      _key not in desk.work)
desk._seed_from_en()
check("desk: seeding fills every missing key from English",
      len([k for k in i18nmod.EN if k in desk.work])
      == len(i18nmod.EN))
desk.work["menu.file"] = "Archivo"     # the built-in value, restored
# put the İ string back the way a translator would — through the box
desk._select_index(desk._row_keys.index(_key))
desk.edit.delete("1.0", "end")
desk.edit.insert("1.0", "İçerik")
desk._flush_edit()

i18nmod.set_language("es")
_saved_ok = desk._save()
root.update()
_lang_file = os.path.join(HOME, ".dxn1-studio", "lang", "es.json")
check("save: the desk writes a user pack", _saved_ok
      and os.path.isfile(_lang_file))
with open(_lang_file, encoding="utf-8") as fh:
    _saved = json.load(fh)
check("save: the working copy landed verbatim",
      _saved.get("menu.file") == "Archivo"
      and _saved.get(_key) == "İçerik")
check("save: an active pack re-activates live",
      i18nmod.tr("menu.file") == "Archivo")
desk._select_index(desk._row_keys.index("menu.file"))
desk.edit.delete("1.0", "end")
desk.edit.insert("1.0", "Escritorio")
desk._flush_edit()
desk._save()
root.update()
check("save: edited strings go live at once",
      i18nmod.tr("menu.file") == "Escritorio")
i18nmod.set_language("en")
desk._close()
root.update()

# ------------------------------------- the chooser is the honest door
app.handle_terminal_command("lang edit")
root.update()
_cho = _choosers()
check("verb: bare `lang edit` opens the chooser", len(_cho) == 1)
chooser = _cho[0]
check("chooser: one row per pack, English excluded",
      len(chooser._rows_frame.winfo_children()) >= 7)
check("chooser: a junk code gets an honest inline error",
      (chooser.code_var.set("Bad Code!") or chooser._open_new()) is False
      and "not a pack code" in chooser.err.cget("text"))
check("chooser: the source of truth is not edited",
      (chooser.code_var.set("en") or chooser._open_new()) is False
      and "source of truth" in chooser.err.cget("text"))
_before = len(_editors())
chooser.code_var.set("tlh")
check("chooser: a valid new code opens a clean desk",
      chooser._open_new() is True and len(_editors()) == _before + 1
      and _editors()[-1].code == "tlh" and _editors()[-1].work == {})
_editors()[-1]._close()
chooser._close()
root.update()

# ------------------------------------- verb honesty
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))
try:
    app.handle_terminal_command("lang edit NOPE!!")
    app.handle_terminal_command("lang edit en")
finally:
    app.terminal.log = _old_log
check("verb: junk codes are refused with a reason",
      any("not a pack code" in m for m in _logs))
check("verb: `lang edit en` explains itself",
      any("translated FROM" in m for m in _logs))

# ------------------------------------- settings + palette doors
_dlg = SettingsDialog(app)
try:
    _texts = " ".join(_dlg._texts_of(w) for w
                      in _dlg._sections[0]["inner"].winfo_children())
    check("settings: the desk is one click from Look & feel",
          "Edit a language pack…" in _texts)
    _dlg._filter_settings("language")
    _vis = [w for w, _info in _dlg._sections[0]["rows"]
            if w.winfo_manager()]
    _texts = " ".join(_dlg._texts_of(w) for w in _vis)
    check("settings: search 'language' finds the desk row",
          "Edit a language pack…" in _texts)
    _dlg._filter_settings("")
finally:
    _dlg.destroy()
root.update()
_pcmds = [c[0] for c in app.palette_commands()]
check("palette: the desk is one row among the powers",
      "Edit a language pack…" in _pcmds)
_vl = [r[0] for r in TERMINAL_HELP]
check("help: lang edit is a first-class verb",
      "lang edit [code]" in _vl)

# ------------------------------------- ActionsMenu width accounting
_menu = qa.ActionsMenu(app)
root.update()
try:
    _w = int(_menu.geometry().split("x")[0])
    check("launcher: geometry never clips its content",
          _w >= _menu.winfo_reqwidth() and _w >= qa.ActionsMenu.WIDTH)
finally:
    try:
        _menu.destroy()
    except tk.TclError:
        pass

# ------------------------------------- regression: the palette audit
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

# ------------------------------------- docs agree
with open(os.path.join("dxn1_studio", "langedit.py"),
          encoding="utf-8") as fh:
    _le = fh.read()
with open(os.path.join("dxn1_studio", "app.py"), encoding="utf-8") as fh:
    _ap = fh.read()
with open(os.path.join("dxn1_studio", "quick_actions.py"),
          encoding="utf-8") as fh:
    _qa = fh.read()
check("source: the desk saves atomically",
      "def save_user_pack" in _le and "os.replace" in _le)
check("source: the verb and the doors are wired",
      '"lang edit [code]"' in _ap and "Edit a language pack…" in _ap
      and "_open_lang_desk" in _ap)
check("source: the launcher grows to fit",
      "w = max(self.WIDTH, self.winfo_reqwidth())" in _qa)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "The Translator Gets a Desk" in _ft and "lang edit" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v550" in _ar)

# ------------------------------------- cleanup
app._dismiss_chip_menu()
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
