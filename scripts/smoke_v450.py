"""DS2 v2.45.0 UI smoke — the receipts survive the night: the
activity ring persists beside config.json (atomic write on every
toast, reload at boot), previous-session entries show under a
"since last time" divider with relative stamps, and Clear through
the window persists the wipe.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v450.py

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


# ------------------------------------- seed the previous session's receipts
_cfg_dir = os.path.join(HOME, ".dxn1-studio")
os.makedirs(_cfg_dir, exist_ok=True)
with open(os.path.join(_cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"onboarded": True, "hub_on_startup": False,
               "check_updates": False}, fh)
_hour_ago = time.time() - 3600
with open(os.path.join(_cfg_dir, "activity.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"version": 1, "entries": [
        {"message": "old whisper A", "kind": "info", "t": _hour_ago},
        {"message": "old whisper B", "kind": "error", "t": _hour_ago},
    ]}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.config import Config  # noqa: E402
from dxn1_studio.app import DXN1Studio  # noqa: E402
import dxn1_studio.activity as act_mod  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())


def _walk(w):
    yield w
    for c in w.winfo_children():
        yield from _walk(c)


# --------------------------------------------- boot reloads the receipts
check("boot: the previous session's receipts are back",
      app.activity_log.count() == 2
      and [e["message"] for e in app.activity_log.entries()] ==
      ["old whisper A", "old whisper B"])
check("boot: loaded entries are marked as previous-session",
      all(e.get("prev") is True for e in app.activity_log.entries()))

# --------------------------------------------- a toast lands on top + persists
app.toast("fresh receipt", "success")
check("toast: the new whisper is current-session, on top",
      app.activity_log.count() == 3
      and app.activity_log.entries()[0]["message"] == "fresh receipt"
      and app.activity_log.entries()[0]["prev"] is False)
_apath = os.path.join(_cfg_dir, "activity.json")
_disk = json.loads(open(_apath, encoding="utf-8").read())
check("toast: the ring persisted to disk atomically",
      _disk["version"] == 1 and len(_disk["entries"]) == 3
      and _disk["entries"][0]["message"] == "fresh receipt")

# --------------------------------------------- the window: divider + rel stamps
# driven through the APP's real opener so the production on_change
# (save-on-clear) is what runs — the file is the assertion
opened = []
_real_open = act_mod.open_activity
act_mod.open_activity = (lambda *a, **k:
                         opened.append(a[2]) or _real_open(*a, **k))
app.handle_terminal_command("activity")
act_mod.open_activity = _real_open
win = [w for w in app.root.winfo_children()
       if isinstance(w, tk.Toplevel) and str(w.title()) == "Activity"][-1]
app.root.update()
texts = [str(w.cget("text")) for w in _walk(win)
         if isinstance(w, tk.Label)]
check("window: the verb opened it and the count tells the truth",
      len(opened) == 1 and "3 events" in texts)
check("window: a 'since last time' divider separates the sessions",
      any("since last time" in t for t in texts))
check("window: relative stamps — 'just now' and '1h ago'",
      "just now" in texts and "1h ago" in texts)
# Clear persists through the app's real on_change callback
clear_btns = [w for w in _walk(win) if isinstance(w, tk.Label)
              and str(w.cget("text")) == "Clear"]
if clear_btns:
    clear_btns[0].event_generate("<Button-1>")
    app.root.update()
check("clear: the wipe empties the ring",
      app.activity_log.count() == 0)
check("clear: the file agrees — the app's on_change persisted it",
      json.loads(open(_apath, encoding="utf-8").read())["entries"] == [])
win.destroy()

# --------------------------------------------- a fresh toast re-seeds the file
app.toast("post-wipe whisper", "info")
_disk = json.loads(open(_apath, encoding="utf-8").read())
check("after wipe: the next toast re-seeds the file",
      len(_disk["entries"]) == 1
      and _disk["entries"][0]["message"] == "post-wipe whisper")

# --------------------------------------------- corrupt file → honest fresh boot
os.makedirs(_cfg_dir, exist_ok=True)
with open(_apath, "w", encoding="utf-8") as fh:
    fh.write("{torn in half")
from dxn1_studio.activity import load_json  # noqa: E402
check("corrupt: a torn file loads as None (caller keeps its own)",
      load_json(_apath) is None)

# --------------------------------------------- registry checks
src = open("dxn1_studio/app.py", encoding="utf-8").read()
check("wiring: boot loads the ring before the toast layer",
      "load_json(self._activity_path(), cap=100)" in src)
check("wiring: every toast persists the ring",
      src.count("save_json(log, self._activity_path())") == 1)
check("wiring: the window's Clear persists through on_change",
      "on_change=lambda: save_json(" in src)
check("engine: rel_time is the window's stamp source",
      "text=rel_time(entry.get(\"t\"))" in
      open("dxn1_studio/activity.py", encoding="utf-8").read())

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
