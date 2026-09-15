"""DS2 v2.59.0 UI smoke — the desk grows to fit: the v2.55
ActionsMenu pattern applied across the pack windows — the desk
opens no narrower than what it actually packed (a long meter or
hint bar must not clip at 680px), the live preview ratchets OUT to
fit a translated string longer than the 440px it opened at and
never shrinks back (a manual resize is never fought), and the
chooser prints every number — the honest ledger's real_pct riding
along on each row, the way the audit prints them. The audit's
closing lines name the whole verb family.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v590.py

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

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())


def _editors():
    return [w for w in root.winfo_children() if isinstance(w, le.PackEditor)]


# ------------------------------------- the chooser prints every number
app.handle_terminal_command("lang edit")
root.update()
_chooser = [w for w in root.winfo_children()
            if isinstance(w, le.PackChooser)][0]
_labels = [w.cget("text") for w in _chooser._rows_frame.winfo_children()]
_es = [t for t in _labels if t.startswith("es ")][0]
check("chooser: rows carry the honest ledger",
      "100% real" in _es and len(_labels) >= 7)
_seedname = "seedfit59"
le.save_user_pack(_seedname, dict(i18nmod.EN))
_chooser._paint_packs()
root.update()
_labels = [w.cget("text") for w in _chooser._rows_frame.winfo_children()]
_seedrow = [t for t in _labels if t.startswith(_seedname + " ")][0]
check("chooser: a seeded pack reads 0% real in its row",
      "0% real" in _seedrow and "100%" in _seedrow)
_chooser._close()
root.update()

# ------------------------------------- the desk opens no narrower
app.handle_terminal_command("lang edit es")
root.update()
_desk = _editors()[0]
root.update()
check("desk: opens no narrower than what it packed",
      _desk.winfo_width() >= 680
      and _desk.winfo_width() >= _desk.winfo_reqwidth() - 2)

# ------------------------------------- the preview ratchet
_desk.work["menu.file"] = "X" * 120
_pv = _desk._open_preview()
root.update()
_grown = _pv.winfo_width()
check("preview: a long string ratchets the window out",
      _grown > 440 and _pv.winfo_width() >= _pv.winfo_reqwidth() - 2)
check("preview: the ratchet recorded its high-water mark",
      getattr(_pv, "_fit_w", 0) >= _grown - 2)
_desk.work["menu.file"] = "Sí"
_pv.refresh()
root.update()
check("preview: a short string never shrinks it back",
      _pv.winfo_width() >= _grown - 2
      and _pv._fit_w >= _grown - 2)
_desk._close()
root.update()

# ------------------------------------- the audit names the family
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))
try:
    app.handle_terminal_command("lang audit")
    _blob = "\n".join(_logs)
    check("audit: the closing lines name the whole verb family",
          "lang check <file>" in _blob and "lang pack <code>" in _blob
          and "lang diff <code>" in _blob)
finally:
    app.terminal.log = _old_log

# ------------------------------------- help + docs agree
with open(os.path.join("dxn1_studio", "langedit.py"),
          encoding="utf-8") as fh:
    _le = fh.read()
check("source: the fit pattern is written where it runs",
      "def _fit_once" in _le and "def _fit(" in _le
      and "%d%% real" in _le and "ratchets OUT" in _le)
with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "The Desk Grows to Fit" in _ft and "real_pct" in _ft)
with open(os.path.join("docs", "ARCHITECTURE.md"),
          encoding="utf-8") as fh:
    _ar = fh.read()
check("ARCHITECTURE.md: the smoke suite is registered",
      "smoke_v590" in _ar)

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
