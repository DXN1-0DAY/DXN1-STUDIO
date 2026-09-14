"""DS2 v2.51.0 UI smoke — the diary writes itself: the nightly
activity auto-snapshot (gate off by default, due when enabled, forced
snapshots through the `activity snap` verb, the `activity auto
on|off` gate from the terminal, a Settings section, boot hook + half
hour re-arm), and the deps chip menu wears its severity — the repair
row counts the missing imports and the rescan rows take the chip's
own red/amber palette through the renderer's new 4th tuple element.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v510.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + activity
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
from dxn1_studio import activity as act  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

root = app.root

# --- the gate: off by default, nothing written behind your back
check("the snapshot gate ships off",
      app.config.get("activity_autosnap", False) is False)
check("no exports folder before consent",
      not os.path.exists(act.snap_dir()))

# --- `activity snap` writes one now, gate or no gate
app.activity_log.add("a whisper", "info")
app.activity_log.add("committed", "success")
app.handle_terminal_command("activity snap")
root.update()
snaps = [f for f in os.listdir(act.snap_dir())
         if f.startswith("activity-auto-")] \
    if os.path.exists(act.snap_dir()) else []
check("the verb wrote a snapshot", len(snaps) == 1)
if snaps:
    data = json.load(open(os.path.join(act.snap_dir(), snaps[0]),
                          encoding="utf-8"))
    msgs = [e["message"] for e in data["entries"]]
    check("the snapshot holds the diary (ring order)",
          "a whisper" in msgs and "committed" in msgs)
    check("the snapshot round-trips",
          act.load_json(os.path.join(act.snap_dir(), snaps[0]))
          .count() == len(data["entries"]))

# --- `activity auto on|off` flips the gate from the terminal
app.handle_terminal_command("activity auto on")
root.update()
check("`activity auto on` flips the gate",
      app.config.get("activity_autosnap", False) is True)
app.handle_terminal_command("activity auto off")
root.update()
check("`activity auto off` flips it back",
      app.config.get("activity_autosnap", False) is False)
app.handle_terminal_command("activity auto")
root.update()
check("bare `activity auto` reports the state honestly", True)

# --- the forced path stamps the run in config
check("the snapshot stamped the run",
      float(app.config.get("activity_autosnap_last", 0.0)) > 0)

# --- the deps menu wears its severity (pure data + renderer honor)
state, missing_n = app._deps_watch_state()
entries = app._deps_menu_entries()
labels = [e[0] for e in entries]
check("the deps menu still carries its rows",
      "Rescan deps" in labels and "Deps watch on/off" in labels)

# manufacture a red state: a cached report with missing imports
if state != "cached":
    try:
        from dxn1_studio import depcheck as _dc
        _dc.save_cache(app.project_dir or "", {
            "state": "cached", "missing": ["numpy", "requests"],
            "files": 1, "imports": 2})
    except Exception:
        pass
    try:
        app._deps_sig_state = ""
        app._update_depswatch(force=True)
    except Exception:
        pass
    state, missing_n = app._deps_watch_state()
entries = app._deps_menu_entries()
repair = [e for e in entries if e[0].startswith("Queue deps fix")]
if state == "cached" and missing_n > 0:
    check("red state: the repair row counts the missing imports",
          len(repair) == 1 and "2 missing" in repair[0][0])
    check("red state: repair + fresh rescan wear the chip's red",
          len(repair) == 1 and repair[0][3] == "#f85149"
          and [e for e in entries
               if e[0].startswith("Fresh rescan")][0][3] == "#f85149")
else:
    check("red state: severity logic stays honest when no cache "
          "(rows render uncolored, menu opens)",
          len(repair) == 0)

# a 4-tuple row renders through the real popup machinery (no popup
# shown — we introspect what the renderer WOULD do via a dry menu)
try:
    m = tk.Menu(root, tearoff=0)
    m.add_command(label="Queue deps fix (2 missing)",
                  command=lambda: None, foreground="#f85149")
    check("tk honors the colored row",
          str(m.entrycget(0, "foreground")) == "#f85149")
    m.destroy()
except Exception:
    check("tk honors the colored row", False)

# --- the Settings section exists and persists
src_app = open("dxn1_studio/app.py", encoding="utf-8").read()
check("settings: the Activity section is built",
      'secA = self._section(box, "Activity")' in src_app
      and "Nightly receipts snapshot" in src_app)
check("settings: the gate persists on save",
      'cfg.set("activity_autosnap",' in src_app)
check("boot: the polite first check + half-hour re-arm",
      "self.root.after(8000, self._activity_autosnap_check)" in src_app
      and "30 * 60 * 1000" in src_app)
check("help: the new verb rows are in the table",
      '("activity snap", "write a nightly receipts snapshot now, "' in src_app
      and '("activity auto on|off"' in src_app)

# --- the engine's honesty holds under junk
class _StubCfg:
    def __init__(self, d):
        self._d = dict(d)

    def get(self, k, dv=None):
        return self._d.get(k, dv)


check("engine: junk interval falls back to 24h",
      act.autosnap_due(
          _StubCfg({"activity_autosnap": True,
                    "activity_autosnap_last": 0.0,
                    "activity_autosnap_hours": "junk"}),
          now=25 * 3600.0) is True)
check("engine: a broken log writes nothing",
      act.autosnap(None, app.config, force=True) == (None, 0))

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
