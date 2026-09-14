"""DS2 v2.38.0 UI smoke — deps per-workspace cache (instant repeat
reports, honest invalidation, `deps fresh`), the `commands [filter]`
terminal verb (palette registry in the terminal), and `help` falling
back into the palette.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v380.py

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
from dxn1_studio.app import (DXN1Studio, palette_help_rows,  # noqa: E402
                             matching_help_rows)
from dxn1_studio import depcheck as dc  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

# ------------------------------------------- engine: cache fingerprints
ws = os.path.join(HOME, "ws-v380")
os.makedirs(ws, exist_ok=True)
with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
    fh.write("import yaml\nimport httpx\n")
with open(os.path.join(ws, "requirements.txt"), "w", encoding="utf-8") as fh:
    fh.write("PyYAML\n")

sig1 = dc.cache_sig(ws)
check("engine: signature stable without changes",
      dc.cache_sig(ws) == sig1)
with open(os.path.join(ws, "main.py"), "w", encoding="utf-8") as fh:
    fh.write("import yaml\nimport httpx\nimport pendulum\n")
check("engine: content change moves the signature",
      dc.cache_sig(ws) != sig1)
sig_now = dc.cache_sig(ws)
check("engine: root listing is fingerprinted",
      any(e[0] == "root:requirements.txt" for e in sig_now))

rep1 = dc.check_cached(ws)
check("engine: first run is a real scan",
      not rep1.get("cached") and rep1["files"] == 1)
rep2 = dc.check_cached(ws)
check("engine: second run is a cache hit",
      rep2.get("cached") is True and rep2["files"] == 1)
check("engine: cache stored under .dxn1",
      os.path.isfile(os.path.join(ws, ".dxn1", "depcheck_cache.json")))
check("engine: no .tmp debris",
      not os.path.exists(os.path.join(ws, ".dxn1",
                                      "depcheck_cache.json.tmp")))
with open(os.path.join(ws, "extra.py"), "w", encoding="utf-8") as fh:
    fh.write("import pendulum\n")
rep3 = dc.check_cached(ws)
check("engine: new file invalidates honestly",
      not rep3.get("cached") and "pendulum" in rep3["missing"])
check("engine: creating .dxn1 did not self-invalidate",
      dc.check_cached(ws).get("cached") is True)
with open(os.path.join(ws, ".dxn1", "depcheck_cache.json"), "w",
          encoding="utf-8") as fh:
    fh.write("{corrupt")
check("engine: corrupt cache falls back to a real scan",
      not dc.check_cached(ws).get("cached"))
repf = dc.check_cached(ws, use_cache=False)
check("engine: fresh bypass rescans and re-stores",
      not repf.get("cached")
      and dc.check_cached(ws).get("cached") is True)

# --------------------------------------------------- app: deps + cache
logs = []
_real_tlog = app.terminal.log
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
app.project_dir = ws
try:
    shutil.rmtree(os.path.join(ws, ".dxn1"), ignore_errors=True)
    app.handle_terminal_command("deps")
    check("deps: cold run has no cache note",
          not any("served from cache" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("deps")
    check("deps: repeat run says served from cache",
          any("served from cache" in s for s in logs)
          and any("`deps fresh` rescans" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("deps fresh")
    check("deps fresh: rescans without the cache note",
          not any("served from cache" in s for s in logs)
          and any("2 file(s) scanned" in s for s in logs))
    # fix always works from a fresh scan
    with open(os.path.join(ws, "late.py"), "w", encoding="utf-8") as fh:
        fh.write("import uvicorn\n")
    logs.clear()
    app.handle_terminal_command("deps fix")
    check("deps fix: fresh scan sees the late import",
          any("uvicorn" in s for s in logs)
          and any("added 3 pin(s)" in s for s in logs))
finally:
    app.terminal.log = _real_tlog

# --------------------------------------------------- commands verb
logs = []
app.terminal.log = lambda s, *a, **k: logs.append(str(s))
try:
    rows = palette_help_rows(app)
    check("commands: palette registry flattens",
          len(rows) >= 40 and ("Run project (F5)", "F5") in rows)
    app.handle_terminal_command("commands")
    check("commands: full listing with the fire-any hint",
          any("palette commands" in s and "Ctrl+K" in s for s in logs)
          and any("Run project (F5)" in s for s in logs)
          and any("more — narrow the filter" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("commands line")
    blob = "\n".join(logs)
    check("commands: substring filter narrows",
          "Duplicate line" in blob and "matching 'line'" in blob
          and "Sort lines" in blob)
    logs.clear()
    app.handle_terminal_command("commands sve fil")
    check("commands: fuzzy fallback finds Save file",
          any("Save file" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("commands zzzqqqxxx")
    check("commands: honest empty state",
          any("nothing matches" in s for s in logs))
    logs.clear()
    app.handle_terminal_command("help duplicate")
    check("help: falls back into the palette registry",
          any("palette: Duplicate line" in s and "Ctrl+Shift+D" in s
              for s in logs))
    logs.clear()
    app.handle_terminal_command("help commands")
    check("help: the new commands row is discoverable",
          any("list palette commands" in s for s in logs))
    check("helper: terminal rows still win for terminal verbs",
          matching_help_rows("deps")[0][0] == "deps")
finally:
    app.terminal.log = _real_tlog

# ------------------------------------------------------------- cleanup
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
