# DXN1 STUDIO 2 — FAQ

## Running

**How do I start the studio?**
`python3 -m dxn1_studio` from the repo root (or `python main.py`).
Python 3.8+ with Tkinter is the whole requirement; everything else —
SQLite browser, hasher, REST bench, markdown preview — is stdlib.

**It didn't boot. Now what?**
Run `python3 -m dxn1_studio.doctor` (Environment Doctor): it checks
Tk, fonts, config JSON, workspace stores and prints a fix-or-explain
report. Config corruption is recovered from `.bak` automatically.

**Where does DS2 keep my data?**
Per-workspace: `.dxn1/` inside your project (bookmarks, filestats
history, agent memory). User-level: `~/.dxn1-studio/` (config,
sessions, theme picks, window geometry). Nothing is written outside
those two places.

**My window opens in the wrong place / on a missing monitor.**
Window geometry is remembered *per screen shape* and clamped to the
visible display on restore — undocking can't lose your window. To
reset, delete `window_geometry_by_screen` from the config JSON.

## Features

**Is my code sent anywhere?**
No. Every tool (SQLite Lab, Hasher, REST Bench, Color Kit, diff
viewer…) runs locally. Network calls happen only when *you* send a
REST Bench request, check for updates, or enable an AI backend.

**Which AI backends are supported?**
The studio ships with a free/local default and pluggable backends in
`llm.py` (agent panel → brain picker). `packages.py` can install
optional SDKs; without them, AI features degrade to copy-a-prompt
mode instead of failing.

**Can I extend it?**
Yes — Plugin API v1 (`plugins.py`): register palette commands and
statusbar items from a plain Python file. Community themes install
from the theme gallery. Agents get a sandboxed tool loop with
permission prompts (`sandbox.py`).

**How do I stop the terminal command list from scrolling away?**
`help` reprints it; the cheat sheet window (Help menu) shows the
same commands grouped by task.

**Why does the statusbar show `✎ 1,234 w · 27 wpm · 45%`?**
That's the scribe meter: live word count, trailing words-per-minute
and your session word goal (`scribe 750` sets it, `scribe 0` hides
the percentage, click the chip for the session toast).

**Does the file-statistics window remember anything?**
Yes — every scan appends to `.dxn1/filestats_history.json` (last 60
snapshots) and renders a sparkline of your project's growth with a
delta line versus the previous scan.

**Can I trust the Hasher's folder manifests?**
They follow `sha256sum -c` format (two spaces), chunked at 1 MiB,
capped at 5000 files per folder — paste any expected digest back
into the window to get ok/MISMATCH/missing verdicts.

## Contributing

**Where do I add a feature?**
New file + `open_*(parent, theme, …)` opener + defensive wiring in
`app.py` (menu, palette, terminal, help) + tests + a smoke check +
a FEATURES.md row. See `docs/ARCHITECTURE.md` for the rules — the
repo is built so parallel contributors never collide.

**Why does every module look so defensive?**
The studio must boot even when a feature is broken: each wiring
patch is `try/except`, each window refresh swallows, each poller
never raises. A dead feature disables itself; the IDE stays alive.
