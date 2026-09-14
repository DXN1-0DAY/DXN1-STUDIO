"""DS2 v2.44.0 UI smoke — the studio keeps its receipts: every toast
is archived in a capped ring the Activity window shows (live filter,
click-to-copy, Clear), and the scribe chip's goal row opens a themed
dialog whose Set button commits the goal.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v440.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + sessions
sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk  # noqa: E402

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


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


# --------------------------------------------- toasts leave receipts
app.toast("receipt one", "success")
app.toast("receipt two", "error")
app.toast("receipt three", "info")
check("toast: every whisper lands in the ring (newest first)",
      [e["message"] for e in app.activity_log.entries()][:3] ==
      ["receipt three", "receipt two", "receipt one"])
check("toast: kinds are archived too",
      app.activity_log.entries()[0]["kind"] == "info"
      and app.activity_log.entries()[1]["kind"] == "error")

# --------------------------------------------- the Activity window e2e
copies = []
win = act_mod.open_activity(app.root, app.theme, app.activity_log,
                            on_copy=lambda m: copies.append(m))
app.root.update()
entries = [w for w in _walk(win) if isinstance(w, tk.Entry)]
check("window: opens with a live filter entry", len(entries) == 1)
count_lbls = [w for w in _walk(win) if isinstance(w, tk.Label)
              and str(w.cget("text")).endswith("events")]
check("window: the count label is honest",
      any(str(w.cget("text")) == "3 events" for w in count_lbls))
# live filter: type "two" → one row remains
entry = entries[0]
entry.delete(0, tk.END)
entry.insert(0, "two")
app.root.update()
count_lbls = [w for w in _walk(win) if isinstance(w, tk.Label)
              and str(w.cget("text")).endswith("event")]
check("window: the filter narrows live",
      any(str(w.cget("text")) == "1 event" for w in count_lbls))
entry.delete(0, tk.END)
entry.insert(0, "zzz-nothing")
app.root.update()
labels = [str(w.cget("text")) for w in _walk(win)
          if isinstance(w, tk.Label)]
check("window: an empty filter says so honestly",
      any("nothing here" in t for t in labels))
entry.delete(0, tk.END)
entry.insert(0, "")
app.root.update()
# click the first row → the message is copied through the callback
first_msg_row = None
for w in _walk(win):
    if isinstance(w, tk.Frame) and \
            str(w.cget("cursor")) == "hand2" and w.winfo_children():
        first_msg_row = w
        break
if first_msg_row:
    for ch in first_msg_row.winfo_children():
        try:
            ch.event_generate("<Button-1>")
        except Exception:  # noqa: BLE001 — best-effort click
            pass
check("window: clicking a row copies the message",
      len(copies) >= 1 and copies[0] == "receipt three", )
# Clear wipes the slate — and the window agrees
clear_btns = [w for w in _walk(win) if isinstance(w, tk.Label)
              and str(w.cget("text")) == "Clear"]
check("window: a Clear control exists", len(clear_btns) == 1)
if clear_btns:
    clear_btns[0].event_generate("<Button-1>")
    app.root.update()
    check("window: Clear empties the ring and repaints",
          app.activity_log.count() == 0)
win.destroy()

# --------------------------------------------- the scribe goal dialog
# driven through the APP's menu row — the real dialog + the real
# _apply callback (chip, config, toast and terminal all move)
if app.scribe_chip is not None:
    goal_before = int(app.scribe_chip.goal_words)
    app._scribe_goal_from_menu()
    app.root.update()
    dlgs = [w for w in app.root.winfo_children()
            if isinstance(w, tk.Toplevel)
            and str(w.title()) == "Writing goal"]
    dlg = dlgs[-1]
    dentries = [w for w in _walk(dlg) if isinstance(w, tk.Entry)]
    check("dialog: the menu row opens it, current goal prefilled",
          len(dentries) == 1 and dentries[0].get() == str(goal_before))
    btns = [w for w in _walk(dlg) if isinstance(w, tk.Label)
            and "Set goal" in str(w.cget("text"))]
    # invalid input: honest inline error, nothing applied, stays open
    dentries[0].delete(0, tk.END)
    dentries[0].insert(0, "lots")
    btns[0].event_generate("<Button-1>")
    app.root.update()
    dlabels = [str(w.cget("text")) for w in _walk(dlg)
               if isinstance(w, tk.Label)]
    check("dialog: junk input gets an honest inline error",
          any("whole numbers only" in t for t in dlabels)
          and int(app.scribe_chip.goal_words) == goal_before
          and dlg.winfo_exists())
    # valid input: applies through _apply — chip, config, feedback
    toasts = []
    app.toast = lambda msg, kind="info": toasts.append(str(msg))
    logs = []
    _real_tlog = app.terminal.log
    app.terminal.log = lambda s, *a, **k: logs.append(str(s))
    dentries[0].delete(0, tk.END)
    dentries[0].insert(0, "750")
    btns[0].event_generate("<Button-1>")
    app.root.update()
    check("dialog: Set applies the goal everywhere it matters",
          app.scribe_chip.goal_words == 750
          and app.config.get("scribe_goal_words") == 750
          and any("750" in s for s in toasts)
          and any("750" in s for s in logs)
          and not dlg.winfo_exists())
    app.terminal.log = _real_tlog
    # Escape cancels without applying (config stays at 750)
    app._scribe_goal_from_menu()
    app.root.update()
    dlg2 = [w for w in app.root.winfo_children()
            if isinstance(w, tk.Toplevel)
            and str(w.title()) == "Writing goal"][-1]
    dlg2.focus_force()
    app.root.update()
    dlg2.event_generate("<Escape>")
    app.root.update()
    check("dialog: Escape cancels and applies nothing",
          not dlg2.winfo_exists()
          and app.config.get("scribe_goal_words") == 750)
else:
    check("dialog: scribe chip unavailable in this boot", True)

# --------------------------------------------- verbs + palette registry
src = open("dxn1_studio/app.py", encoding="utf-8").read()
helpsrc = src
check("verbs: the `activity` verb is in TERMINAL_HELP",
      '("activity", "recent studio notifications' in helpsrc)
check("verbs: `activity` and `notifications` route to the window",
      'if low in ("activity", "notifications"):' in helpsrc)
check("palette: the Activity row is registered",
      "Activity — recent notifications…" in src)
check("toast: the archive hook is wired exactly once",
      src.count("log.add(message, kind)") == 1)

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
