"""DS2 v2.34.0 UI smoke — delta updates (HASHES.txt + sha256 skip)
and the Workshop menu entry for Save Session Now.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v340.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import hashlib
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


# ------------------------------------------------------------ hash engine
from dxn1_studio import updater  # noqa: E402

hpath = "HASHES.txt"
check("HASHES.txt: exists at repo root", os.path.isfile(hpath))
hashes = updater.parse_hashes(open(hpath, encoding="utf-8").read())
mods = [ln.strip() for ln in open("MANIFEST.txt", encoding="utf-8")
        if ln.strip()]
check("HASHES.txt: covers every manifest module",
      all(f"dxn1_studio/{m}" in hashes for m in mods))
check("HASHES.txt: covers spaced filenames too",
      "DXN1 STUDIO" in hashes and "README.md" in hashes)
check("HASHES.txt: module sha matches the real file",
      hashes.get("dxn1_studio/session.py") ==
      updater._local_sha256("dxn1_studio/session.py"))

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

# --------------------------------------------- Workshop menu: save now
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


try:
    # DS2 uses a themed Menubutton bar (not root["menu"]) — walk each
    # Menubutton's attached dropdown
    for _child in app.menu_bar.winfo_children():
        try:
            _walk(app.root.nametowidget(str(_child.cget("menu"))))
        except Exception:  # noqa: BLE001 — non-menu children
            continue
except Exception:  # noqa: BLE001
    pass
check("workshop menu: Save Session Now present",
      any("Save Session Now" in s for s in _labels))
check("workshop menu: Session Restore still present",
      any("Session Restore" in s for s in _labels))

# ------------------------------------------- live delta (no network)
tmp = tempfile.mkdtemp(prefix="ds2-v340-")
pkg = os.path.join(tmp, "dxn1_studio")
os.makedirs(pkg)
with open(os.path.join(pkg, "a.py"), "w", encoding="utf-8") as fh:
    fh.write("x = 1\n")
_real_pkgroot = updater._package_root
_real_resolve = updater.resolve_modules
_real_git = updater._is_git_checkout
_real_hashes = updater._remote_hashes
_real_download = updater._download
updater._package_root = lambda: tmp
updater.resolve_modules = lambda root: ["a.py"]
updater._is_git_checkout = lambda root: False
updater._remote_hashes = lambda: {
    "dxn1_studio/a.py":
        hashlib.sha256(b"x = 1\n").hexdigest()}
downloads = []
updater._download = lambda rel, dest: downloads.append(rel) or 10
try:
    ok = updater.perform_update(lambda **kw: None)
finally:  # restore regardless — the smoke must not poison later code
    updater._package_root = _real_pkgroot
    updater.resolve_modules = _real_resolve
    updater._is_git_checkout = _real_git
    updater._remote_hashes = _real_hashes
    updater._download = _real_download
check("delta: perform_update succeeded", ok)
check("delta: unchanged module skipped",
      "dxn1_studio/a.py" not in downloads)
check("delta: hashes + manifest still refreshed",
      "MANIFEST.txt" in downloads and "HASHES.txt" in downloads)

# ------------------------------------------------------------- cleanup
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
