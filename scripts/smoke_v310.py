"""DS2 v2.31.0 UI smoke — fuzzy highlight rendering, per-buffer cursor
memory and the session-snapshot cursor merge.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v310.py

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


# --------------------------------------------------------------- engine
from dxn1_studio import fuzzy  # noqa: E402

runs = fuzzy.split_runs("qpn", [0, 2])   # non-contiguous → 3 runs
check("split_runs: non-contiguous runs", len(runs) == 3
      and sum(m for _c, m in runs) == 2)
check("split_runs: contiguous collapses", len(fuzzy.split_runs(
    "qpn", [0, 1, 2])) == 1)
check("split_runs: round-trip join",
      "".join(c for c, _m in fuzzy.split_runs("quick open", [0, 6, 7]))
      == "quick open")
merged = fuzzy.split_runs("abcdef", [1, 2, 3])
check("split_runs: contiguous merge", len(merged) == 3
      and merged[1] == ("bcd", True))
check("split_runs: None text safe", fuzzy.split_runs(None, [0]) == [])
check("split_runs: junk positions ignored",
      fuzzy.split_runs("abc", [-1, 9, "x", None]) == [("abc", False)])

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

app = DXN1Studio(Config(), no_splash=True)
app.root.update()
if app._hub is not None and app._hub.winfo_exists():
    app._on_hub_explore()
app.root.update()
check("studio booted headless", app.root.winfo_exists())

# ------------------------------------------------------------ fixtures
tmp = tempfile.mkdtemp(prefix="ds2-v310-")
app.project_dir = tmp           # QuickOpen scans the workspace
f1 = os.path.join(tmp, "alpha.py")
with open(f1, "w", encoding="utf-8") as fh:
    fh.write("def gmmthre_alpha():\n    pass\n\n"
             "# pad 4\n# pad 5\n# pad 6\n# pad 7\n# pad 8\n")
f2 = os.path.join(tmp, "beta.py")
with open(f2, "w", encoding="utf-8") as fh:
    fh.write("BETA = 1\nline2\nline3\n")

app.open_file(f1)
app.open_file(f2)          # beta active now
app.root.update()
app._activate_tab(f1)      # back to alpha
app.root.update()

# ------------------------------------------------- per-buffer cursors
app.editor.text.mark_set("insert", "7.3")
app._activate_tab(f2)      # outgoing alpha cursor recorded
app._activate_tab(f1)      # ...and restored on the way back
app.root.update()
check("cursor memory: 7.3 restored",
      app.editor.text.index("insert") == "7.3")
check("cursor memory: map populated",
      "." in str(app._buffer_cursors.get(f2, "")))

# ------------------------------------------------- palette highlight
app.open_palette()
pal = app._palette
pal.entry.delete(0, tk.END)
pal.entry.insert(0, "qpn")
pal._on_type()
pal.rows.update_idletasks()
rows = pal.rows.winfo_children()
check("palette: qpn has rows", len(rows) >= 1)
row0 = rows[0]


def bold_labels(widget):
    out = []
    for w in widget.winfo_children():
        try:
            if "bold" in str(w.cget("font")):
                out.append(w)
        except Exception:  # noqa: BLE001
            pass
    return out


texts = "".join(str(w.cget("text")) for w in row0.winfo_children())
check("palette: qpn top hit is quick open",
      "quick open" in texts.lower())
check("palette: qpn renders 3 bold runs", len(bold_labels(row0)) == 3)

pal.entry.delete(0, tk.END)
pal.entry.insert(0, "@gmr")     # g0 m1 ... r5 → 2 name runs + kind chip
pal._on_type()
pal.rows.update_idletasks()
rows = pal.rows.winfo_children()
check("palette: @gmr has symbol rows", len(rows) >= 1)
srow = rows[0]
stexts = "".join(str(w.cget("text")) for w in srow.winfo_children())
check("palette: @gmr hits gmmthre_alpha",
      "gmmthre_alpha" in stexts.lower().replace(" ", ""))
check("palette: @gmr renders 3 bold labels",
      len(bold_labels(srow)) == 3)   # 2 name runs + 1 always-bold kind
pal.close()
app.root.update()

# ------------------------------------------------- quick open highlight
app.open_quick_open()
qo = app._quick_open
qo.entry.delete(0, tk.END)
qo.entry.insert(0, "alp")       # alpha.py → a-l-p contiguous prefix
qo._on_type()
qo.rows.update_idletasks()
qrows = qo.rows.winfo_children()
check("quick open: alp has rows", len(qrows) >= 1)
check("quick open: row shows bold match",
      len(bold_labels(qrows[0])) >= 1)
qo.close()
app.root.update()

# ------------------------------------------------- session cursor merge
app._buffer_cursors[f1] = "7.3"
app._buffer_cursors[f2] = "2.0"
app.project_dir = tmp           # deterministic workspace key
try:
    app._on_close()             # writes snapshot, then destroys root
except Exception:  # noqa: BLE001 — destroy-time noise is fine
    pass

from dxn1_studio import session as sess  # noqa: E402

snap = sess.load(tmp)
curs = (snap or {}).get("cursor") or {}
check("session: snapshot saved", bool(snap))
check("session: alpha cursor line 7",
      (curs.get(f1) or {}).get("line") == 7)
check("session: beta cursor line 2",
      (curs.get(f2) or {}).get("line") == 2)

# ------------------------------------------------------------- cleanup
try:
    sess.clear(tmp)
except Exception:  # noqa: BLE001
    pass
for p in (os.path.join(_cfg_dir, "sessions"),):
    shutil.rmtree(p, ignore_errors=True)
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
