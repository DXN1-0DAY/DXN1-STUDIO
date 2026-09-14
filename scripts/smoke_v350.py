"""DS2 v2.35.0 UI smoke — the polite updater ("skip this version"
memory + quiet auto-check) and the engine-first boot restore (a crash
costs one minute of tabs, not a week-old clean-exit record).

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v350.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile
import time

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + sessions
sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk  # noqa: E402

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# ------------------------------------------------- config defaults + io
import dxn1_studio.config as cfgmod  # noqa: E402

check("defaults: updater_skip_version present and empty",
      cfgmod.DEFAULTS.get("updater_skip_version", "missing") == "")
_cfg = cfgmod.Config()
_cfg.set("updater_skip_version", "9.9.9")
check("atomic save: config.json written, no .tmp debris",
      os.path.isfile(cfgmod.CONFIG_PATH)
      and not os.path.exists(cfgmod.CONFIG_PATH + ".tmp"))
check("atomic save: value survives reload",
      cfgmod.Config().get("updater_skip_version") == "9.9.9")

# ----------------------------------------------------------------- boot
_cfg_dir = os.path.join(HOME, ".dxn1-studio")
os.makedirs(_cfg_dir, exist_ok=True)
with open(os.path.join(_cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"onboarded": True, "hub_on_startup": False,
               "check_updates": False}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.config import Config  # noqa: E402
from dxn1_studio.app import DXN1Studio  # noqa: E402
from dxn1_studio import updater  # noqa: E402
from dxn1_studio import session as sess  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

# ------------------------------------------------ the polite updater
class _StubPortal:
    decline = updater.UpdatePortal.decline

    def __init__(self, app, latest):
        self.app, self.latest, self._phase = app, latest, "offer"

    def _paint(self):
        self.painted = True


stub = _StubPortal(app, "9.9.9")
stub.decline()
check("decline: phase flipped to declined", stub._phase == "declined")
check("decline: version remembered in config",
      app.config.get("updater_skip_version") == "9.9.9")
check("nag: auto-check goes quiet for the skipped version",
      app._update_should_nag("9.9.9") is False)
check("nag: any other version still speaks up",
      app._update_should_nag("10.0.0") is True)
check("nag: manual check always shows the portal",
      app._update_should_nag("9.9.9", manual=True) is True)

# ---------------------------------------- end-to-end check_for_updates
import threading  # noqa: E402
import urllib.request  # noqa: E402

payload = json.dumps({"tag_name": "v9.9.9", "body": "- n",
                      "html_url": "https://example.com/r"}).encode()


class _FakeResp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return payload


class _InlineThread:
    """Run the worker synchronously — root.after from a secondary
    thread needs a live mainloop, which this harness stubs out."""

    def __init__(self, target=None, daemon=None, *a, **k):
        self._target = target

    def start(self):
        self._target()


_real_urlopen = urllib.request.urlopen
_real_portal = updater.UpdatePortal
_real_tlog = app.terminal.log
_real_thread = threading.Thread
opened, logs = [], []
urllib.request.urlopen = lambda req, timeout=10: _FakeResp()
updater.UpdatePortal = lambda *a, **k: opened.append(a)
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
app._updater_shown = False
try:
    threading.Thread = _InlineThread
    app.check_for_updates(manual=False)
    for _ in range(50):
        app.root.update()
        if not app._updater_shown:
            break
        time.sleep(0.02)
    check("e2e: the auto check actually finished", not app._updater_shown)
    check("e2e: skipped version opens no portal", not opened)
    check("e2e: terminal explains the skip",
          any("skip" in s for s in logs))
    app._updater_shown = False
    app.check_for_updates(manual=True)
    for _ in range(50):
        app.root.update()
        if not app._updater_shown:
            break
        time.sleep(0.02)
    check("e2e: manual check still opens the portal", bool(opened))
finally:
    urllib.request.urlopen = _real_urlopen
    updater.UpdatePortal = _real_portal
    app.terminal.log = _real_tlog
    threading.Thread = _real_thread

# ------------------------------------------- engine-first boot restore
proj = os.path.join(HOME, "ws-v350")
os.makedirs(proj, exist_ok=True)
fa = os.path.join(proj, "alpha.py")
fb = os.path.join(proj, "beta.py")
with open(fa, "w", encoding="utf-8") as fh:
    fh.write("def gmm(x):\n    return x\n"
             + "".join(f"line {i}\n" for i in range(3, 13)))
with open(fb, "w", encoding="utf-8") as fh:
    fh.write("beta one\nbeta two\n")

app2 = DXN1Studio(Config(), no_splash=True)
app2.root.update()
app2.project_dir = proj
check("engine: no snapshot yet → honest False",
      app2._restore_engine_session(proj) is False)

# a week-old clean-exit record knows only beta…
app2.config.set("session_tabs",
                {os.path.abspath(proj): {"tabs": [fb], "active": fb}})
# …but last night's autosave snapshot knows both files + cursors
sess.save(proj, sess.snapshot([fa, fb], active=fa,
                              cursor={fa: (7, 3), fb: (2, 0)},
                              workspace=proj))
check("engine: snapshot present → True",
      app2._restore_engine_session(proj) is True)
app2.root.update()
check("engine: both tabs + active + cursor restored",
      fa in app2._tab_frames and fb in app2._tab_frames
      and app2.editor.file_path == fa
      and app2.editor.text.index("insert") == "7.3")

app3 = DXN1Studio(Config(), no_splash=True)
app3.root.update()
app3.project_dir = proj
app3._restore_session_tabs(proj)
app3.root.update()
check("boot: engine-first beats the stale legacy record",
      fa in app3._tab_frames and app3.editor.file_path == fa)
check("boot: buffer cursors seeded for tab switches",
      app3._buffer_cursors.get(fb) == "2.0")

sess.clear(proj)
check("engine: cleared snapshot → False again",
      app3._restore_engine_session(proj) is False)
app4 = DXN1Studio(Config(), no_splash=True)
app4.root.update()
app4.project_dir = proj
app4._restore_session_tabs(proj)
app4.root.update()
check("boot: legacy clean-exit record is the fallback",
      app4.editor.file_path == fb)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
