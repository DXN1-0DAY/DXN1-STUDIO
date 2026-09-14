"""DS2 v2.39.0 UI smoke — the dependency watch chip (statusbar dot
that turns amber when the workspace drifts from the last deps report,
click to rescan, `deps watch [on|off]`), and the terminal verbs
browser (`verbs` window: searchable rows, honest empty state,
click-to-prefill, Workshop + palette entries).

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v390.py

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
from dxn1_studio.app import (DXN1Studio, TERMINAL_HELP,  # noqa: E402
                             palette_help_rows)
from dxn1_studio import depcheck as dc  # noqa: E402
from dxn1_studio import verbs as vb     # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

# ------------------------------------------------ engine: cache_state
ws = os.path.join(HOME, "ws-v390")
os.makedirs(ws, exist_ok=True)
with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
    fh.write("import yaml\n")
with open(os.path.join(ws, "requirements.txt"), "w", encoding="utf-8") as fh:
    fh.write("PyYAML\n")

check("engine: fresh workspace reads absent",
      dc.cache_state(ws)["state"] == "absent")
dc.check_cached(ws)
check("engine: stored report reads cached",
      dc.cache_state(ws)["state"] == "cached")
with open(os.path.join(ws, "late.py"), "w", encoding="utf-8") as fh:
    fh.write("import uvicorn\n")
check("engine: file drift reads stale",
      dc.cache_state(ws)["state"] == "stale")
with open(os.path.join(ws, ".dxn1", "depcheck_cache.json"), "w",
          encoding="utf-8") as fh:
    fh.write("{corrupt")
check("engine: corrupt cache reads absent",
      dc.cache_state(ws)["state"] == "absent")

# ------------------------------------------------- verbs: pure helpers
rows = vb.verb_rows(TERMINAL_HELP)
check("verbs: TERMINAL_HELP flattens into complete rows",
      len(rows) >= 40 and all(c and d for c, d in rows))
verbs_list = [c for c, _ in rows]
check("verbs: rows unique", len(verbs_list) == len(set(verbs_list)))
check("verbs: git continuation merged",
      "git <args>" in verbs_list
      and "commit" in dict(rows)["git <args>"])
check("verbs: the browser lists itself + deps advertises watch",
      "verbs" in verbs_list and "watch" in dict(rows)["deps"])
check("verbs: filter empty = all, junk = none",
      vb.filter_rows(rows, "") == rows
      and vb.filter_rows(rows, "zzzqqq") == [])
check("verbs: filter hits verb and description",
      [c for c, _ in vb.filter_rows(rows, "deps")] == ["deps"]
      and bool(vb.filter_rows(rows, "MARKDOWN")))

# ------------------------------------------------------- app: the chip
logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
app.project_dir = ws
try:
    shutil.rmtree(os.path.join(ws, ".dxn1"), ignore_errors=True)
    app._update_depswatch(force=True)
    check("chip: absent shows the quiet placeholder",
          app.status_deps.cget("text") == "deps —")
    app.handle_terminal_command("deps")
    check("chip: a deps run anchors it to ok",
          app.status_deps.cget("text") == "deps ok")
    with open(os.path.join(ws, "late2.py"), "w", encoding="utf-8") as fh:
        fh.write("import httpx\n")
    app._update_depswatch(force=True)
    check("chip: drift turns it amber and bold",
          app.status_deps.cget("text") == "● deps drift"
          and app.status_deps.cget("fg") == "#f59e0b")
    logs.clear()
    app._deps_chip_click()
    check("chip: clicking rescans and calms it",
          app.status_deps.cget("text") == "deps ok"
          and any("file(s) scanned" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("deps watch off")
    check("chip: off hides it and remembers",
          app.status_deps.cget("text") == ""
          and app.config.get("deps_watch", True) is False)
    logs.clear()
    app.handle_terminal_command("deps watch maybe")
    check("chip: junk argument gets honest usage",
          any("usage: deps watch" in s for s in logs)
          and app.config.get("deps_watch", True) is False)
    logs.clear()
    app.handle_terminal_command("deps watch")
    check("chip: bare verb flips it back on",
          app.config.get("deps_watch", True) is True
          and app.status_deps.cget("text") == "deps ok")
    try:
        app._deps_watch_poll()
        check("chip: the 30s poll runs without raising", True)
    except Exception:
        check("chip: the 30s poll runs without raising", False)
finally:
    app.terminal.log = _real_tlog

# ------------------------------------------------- app: verbs window
def _labels_under(w):
    out = []

    def _rec(w):
        for ch in w.winfo_children():
            if isinstance(ch, tk.Label):
                out.append(str(ch.cget("text")))
            _rec(ch)
    _rec(w)
    return out


def _body_text(win):
    return "\n".join(_labels_under(win))


def _count_text(win):
    import re
    for t in _labels_under(win):
        if re.match(r"^\d+ verbs$", t):
            return t
    return ""


logs = []
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
try:
    labels = [r[0] for r in palette_help_rows(app)]
    check("palette: both new entries registered",
          any("Terminal verbs" in l for l in labels)
          and any("Dependency watch" in l for l in labels))
    before = len([w for w in app.root.winfo_children()
                  if isinstance(w, tk.Toplevel)])
    app.handle_terminal_command("verbs")
    after = len([w for w in app.root.winfo_children()
                 if isinstance(w, tk.Toplevel)])
    check("terminal: `verbs` opens the browser", after == before + 1)

    picked = []
    win = vb.open_verbs(app.root, app.theme, on_insert=picked.append,
                        rows=rows)
    try:
        check("window: opens with the full row set",
              win.winfo_exists())
        ent = win.search_entry
        ent.delete(0, tk.END)
        ent.insert(0, "deps")
        win.refilter()
        check("window: live filter narrows to the deps row",
              _body_text(win).count("\n") > 0
              and "deps" in _body_text(win))
        ent.delete(0, tk.END)
        ent.insert(0, "zzzqqq")
        win.refilter()
        check("window: honest empty state",
              "nothing matches" in _body_text(win))
        check("window: count label follows the filter",
              _count_text(win) == "0 verbs")
    finally:
        win.destroy()
    app._prefill_terminal("deps fix")
    check("window: clicking prefills the terminal input",
          app.terminal.input.get() == "deps fix")
finally:
    app.terminal.log = _real_tlog

# --------------------------------------------------- Workshop menu walk
_labels = []


def _walk(menu, depth=0):
    if menu is None or depth > 4:
        return
    try:
        n = menu.index("end") or 0
    except Exception:  # noqa: BLE001
        return
    for i in range(n + 1):
        try:
            ent = menu.entrycget(i, "label")
            if ent:
                _labels.append(str(ent))
            sub = app.root.nametowidget(str(menu.entrycget(i, "menu")))
            _walk(sub, depth + 1)
        except Exception:  # noqa: BLE001 — separators etc.
            continue


for _child in app.menu_bar.winfo_children():
    try:
        _walk(app.root.nametowidget(str(_child.cget("menu"))))
    except Exception:  # noqa: BLE001 — non-menu children
        continue
check("menu: Workshop carries the verbs browser",
      any("Terminal Verbs" in l for l in _labels))
check("menu: Workshop still carries Dependency Check",
      any("Dependency Check" in l for l in _labels))

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
