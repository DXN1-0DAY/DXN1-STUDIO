#!/usr/bin/env python3
"""DS3 probe: the studio's UE5 face is real and in sync — ui/index.html
carries every panel (menubar, Place Actors, Outliner, Details, Content
Browser, Output Log, status bar, PIE bar), lists every scene on the wire
(scenes/*.dxn1.json — the SCENES array and the directory agree), wears
every image it references (assets/*.png, PNG magic verified), pins its
embedded VERSION to the repo's VERSION file (the fifth corner of the
version sync), and ships with no TODO lint. Pure-python pins, no engine."""
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(REPO, "ui", "index.html")

pins = []
t0 = time.time()


def pin(name, ok, detail=""):
    pins.append((name, bool(ok)))
    print(f"  {'ok ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail and not ok else ""))


html = ""
try:
    html = open(UI, encoding="utf-8").read()
except OSError as e:
    print(f"  FAIL cannot read {UI}: {e}")
    html = ""

# pin 1 — the editor exists and is a real body of work, not a stub
pin("ui/index.html exists and is substantial", len(html) > 20000, f"{len(html)} bytes")

# pin 2 — every UE5 panel the research doc promised is in the cloth
PANELS = [
    ("menubar", 'id="menubar"'),
    ("toolbar", 'id="toolbar"'),
    ("Place Actors", "Place Actors"),
    ("Outliner", "Outliner"),
    ("Details", "Details"),
    ("Content Browser", "Content Browser"),
    ("Output Log", "Output Log"),
    ("status bar", 'id="statusbar"'),
    ("PIE bar", 'id="piebar"'),
    ("viewport canvas", 'id="viewport"'),
]
missing = [nm for nm, marker in PANELS if marker not in html]
pin("all 10 editor panels present", not missing, ", ".join(missing))

# pin 3 — the SCENES array and the scenes/ directory agree (the sync law)
scenes_dir = sorted(f for f in os.listdir(os.path.join(REPO, "scenes"))
                    if f.endswith(".dxn1.json"))
listed = sorted(set(re.findall(r'f:"([\w.-]+\.dxn1\.json)"', html)))
pin("every scene on disk is in the editor's SCENES array",
    set(scenes_dir) <= set(listed),
    f"missing from UI: {sorted(set(scenes_dir)-set(listed))}")
pin("the editor lists no ghost scenes",
    set(listed) <= set(scenes_dir),
    f"ghosts: {sorted(set(listed)-set(scenes_dir))}")

# pin 4 — every referenced image exists and starts with the PNG magic
assets = sorted(set(re.findall(r'assets/([\w.-]+\.png)', html)))
bad = []
for a in assets:
    p = os.path.join(REPO, "ui", "assets", a)
    try:
        with open(p, "rb") as fh:
            head = fh.read(8)
        if not head.startswith(b"\x89PNG\r\n\x1a\n"):
            bad.append(f"{a}: not a PNG")
    except OSError:
        bad.append(f"{a}: missing")
pin(f"all {len(assets)} referenced ui assets are real PNGs", not bad and bool(assets),
    "; ".join(bad))

# pin 5 — the embedded VERSION equals the VERSION file (the fifth corner)
m = re.search(r'const VERSION = "([\d.]+)"', html)
ver_file = open(os.path.join(REPO, "VERSION"), encoding="utf-8").read().strip()
pin("editor VERSION pin equals the VERSION file",
    bool(m) and m.group(1) == ver_file,
    f"ui says {m.group(1) if m else '???'}, VERSION says {ver_file}")

# pin 6 — spark's constants are spoken honestly in the PIE sim
pin("PIE speaks spark's physics constants",
    "GRAV = 1500" in html and "JUMP_VY = -620" in html)

# pin 7 — no unfinished-work lint
lint = [w for w in ("TODO", "FIXME", "XXX", "placeholder-here") if w in html]
pin("no TODO/FIXME lint in the editor", not lint, ", ".join(lint))

fails = [n for n, ok in pins if not ok]
print(f"\nui_editor_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
