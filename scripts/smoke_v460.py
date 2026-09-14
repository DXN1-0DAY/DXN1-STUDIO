"""DS2 v2.46.0 UI smoke — the receipts go where you send them: the
Activity window grows kind filters (click a dot to hide that kind,
unnamed kinds always survive), Copy all (the whole chronological
diary onto the clipboard) and Save as file… (the dialog seam stubbed,
the file real), and the `activity` verb grew hands: `activity copy`
and `activity export [path]`.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v460.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + activity
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
        {"message": "old info whisper", "kind": "info", "t": _hour_ago},
        {"message": "old error whisper", "kind": "error", "t": _hour_ago},
        {"message": "old success whisper", "kind": "success",
         "t": _hour_ago},
    ]}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.config import Config  # noqa: E402
from dxn1_studio.app import DXN1Studio  # noqa: E402
import dxn1_studio.activity as act_mod  # noqa: E402
from dxn1_studio.activity import export_text  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

_logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: _logs.append(str(s))


def _walk(w):
    yield w
    for c in w.winfo_children():
        yield from _walk(c)


def _labels(win):
    return [str(w.cget("text")) for w in _walk(win)
            if isinstance(w, tk.Label)]


def _dot(win, text):
    hits = [w for w in _walk(win) if isinstance(w, tk.Label)
            and str(w.cget("text")) == text]
    return hits[0] if hits else None


# --------------------------------------------- boot reloads the receipts
check("boot: the previous session's receipts are back, marked prev",
      app.activity_log.count() == 3
      and all(e.get("prev") is True
              for e in app.activity_log.entries()))

# ------------------------------- a toast lands on top; one unnamed kind
app.toast("fresh receipt", "success")
app.activity_log.add("odd duck", "weird")   # a kind the studio can't name
check("ring: the newest add sits on top, the unnamed kind is kept",
      app.activity_log.count() == 5
      and app.activity_log.entries()[0]["message"] == "odd duck"
      and app.activity_log.entries()[1]["message"] == "fresh receipt")

# --------------------------------------------- open the window via the verb
app.handle_terminal_command("activity")
app.root.update()
win = [w for w in app.root.winfo_children()
       if isinstance(w, tk.Toplevel) and str(w.title()) == "Activity"][-1]
app.root.update()
texts = _labels(win)
check("window: the verb opened it and the count tells the truth",
      "5 events" in texts)
check("window: the kind dots are all shown",
      "show:" in texts and "● success" in texts
      and "● error" in texts and "● info" in texts)

# --------------------------------------------- kind filters
_dot(win, "● error").event_generate("<Button-1>")
app.root.update()
texts = _labels(win)
check("filter: hiding the error kind removes its rows honestly",
      "4 events" in texts and "old error whisper" not in texts
      and "old info whisper" in texts)
for _d in ("● success", "● info"):
    _dot(win, _d).event_generate("<Button-1>")
app.root.update()
texts = _labels(win)
check("filter: an unnamed kind survives every filter state",
      "1 event" in texts and "odd duck" in texts)
for _d in ("○ success", "○ error", "○ info"):
    _dot(win, _d).event_generate("<Button-1>")
app.root.update()
texts = _labels(win)
check("filter: the dots restore every row",
      "5 events" in texts and "old error whisper" in texts
      and "● error" in texts)

# --------------------------------------------- Copy all
# snapshot BEFORE the click: the acknowledgment toast archives itself
_expected = export_text(app.activity_log.entries())
_dot(win, "Copy all").event_generate("<Button-1>")
app.root.update()
clip = win.clipboard_get()
check("copy all: the whole chronological diary is on the clipboard",
      clip == _expected
      and clip.splitlines()[0].endswith("old info whisper"))
newest = app.activity_log.entries()[0]["message"]
check("copy all: the app acknowledged the big copy",
      newest.startswith("Copied ") and "characters" in newest)

# the acknowledgment receipt is part of the diary now — re-snapshot
_expected = export_text(app.activity_log.entries())

# --------------------------------------------- Save as file…
target = os.path.join(HOME, "receipts-chosen.txt")
seen_kwargs = {}
_real_fd = act_mod.filedialog
act_mod.filedialog = SimpleNamespace(
    asksaveasfilename=lambda **k: (seen_kwargs.update(k)
                                   or str(target)))
try:
    _dot(win, "Save as file…").event_generate("<Button-1>")
    app.root.update()
    check("save as: the dialog got the studio's export dir and the "
          "file is real",
          os.path.isfile(target)
          and seen_kwargs.get("initialdir") == _cfg_dir
          and str(seen_kwargs.get("defaultextension")) == ".txt")
    written = open(target, encoding="utf-8").read().splitlines()
    check("save as: the file holds the whole diary, oldest first",
          written == _expected.splitlines()
          and written[0].endswith("old info whisper"))
    newest = app.activity_log.entries()[0]["message"]
    check("save as: the app acknowledged with the path",
          newest.startswith("Receipts saved →")
          and any("activity receipts written to" in s for s in _logs))
    # a cancelled dialog is an honest no-op: nothing new whispered,
    # the file untouched
    newest_before = app.activity_log.entries()[0]["message"]
    act_mod.filedialog = SimpleNamespace(asksaveasfilename=lambda **k: "")
    _dot(win, "Save as file…").event_generate("<Button-1>")
    app.root.update()
    check("save as: a cancelled dialog wrote nothing at all",
          app.activity_log.entries()[0]["message"] == newest_before
          and open(target, encoding="utf-8").read().splitlines()
          == _expected.splitlines())
finally:
    act_mod.filedialog = _real_fd
win.destroy()

# --------------------------------------------- the verb grew hands
app.handle_terminal_command("activity copy")
app.root.update()
clip = app.root.clipboard_get()
newest = app.activity_log.entries()[0]["message"]
check("verb: activity copy puts the diary on the clipboard",
      "old success whisper" in clip and clip.splitlines()[0]
      .endswith("old info whisper"))
check("verb: activity copy acknowledges in receipts",
      newest.startswith("Copied ") and "receipt" in newest)

app.handle_terminal_command("activity export")
app.root.update()
made = [f for f in os.listdir(_cfg_dir)
        if f.startswith("activity-export-") and f.endswith(".txt")]
check("verb: activity export lands beside activity.json",
      len(made) == 1
      and "old error whisper" in
      open(os.path.join(_cfg_dir, made[0]),
           encoding="utf-8").read())

explicit = os.path.join(HOME, "sent-receipts.txt")
app.handle_terminal_command("activity export %s" % explicit)
app.root.update()
check("verb: activity export honors an explicit path",
      os.path.isfile(explicit)
      and "fresh receipt" in
      open(explicit, encoding="utf-8").read())

app.handle_terminal_command("activity nonsense")
app.root.update()
check("verb: a nonsense sub-command gets an honest hint",
      any("try: activity" in s for s in _logs))

help_rows = [r[0] for r in
             __import__("dxn1_studio.app",
                        fromlist=["TERMINAL_HELP"]).TERMINAL_HELP]
check("help: the new verbs are documented",
      "activity copy" in help_rows
      and "activity export [path]" in help_rows)

# --------------------------------------------- wiring checks
app_src = open("dxn1_studio/app.py", encoding="utf-8").read()
act_src = open("dxn1_studio/activity.py", encoding="utf-8").read()
check("wiring: the opener hands the window an export dir + on_export",
      "export_dir=os.path.dirname(" in app_src
      and "on_export=self._activity_exported" in app_src)
check("wiring: the window's rows filter through the kind set",
      "log.filtered(var.get(), kinds=shown)" in act_src)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
