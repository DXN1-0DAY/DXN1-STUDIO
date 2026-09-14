"""DXN1 STUDIO — Workspace Snapshots.

Time-point backups of the open workspace, stored *inside* the workspace
itself (``<ws>/.dxn1/backups/*.zip``) so they travel with the folder
and never leave the machine unless the developer copies them.

* :func:`create_snapshot` — zip the workspace, skipping noise
  (``.git``, ``__pycache__``, ``node_modules``, virtualenvs, previous
  backups) and binary heavies only when asked
* :func:`list_snapshots`  — name / size / label / file count
* :func:`restore_snapshot` — safe unzip with **zip-slip protection**
  (refuses any member path that escapes the workspace)
* :func:`prune_snapshots`  — keep the newest N, delete the rest

GUI: snapshot browser with create/restore/delete/prune. Palette:
``Snapshot — back up this workspace now`` and ``Browse snapshots…``.
"""

from __future__ import annotations

import json
import os
import time
import zipfile

BACKUP_DIR = os.path.join(".dxn1", "backups")
META_NAME = "snapshot.json"

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
             "env", ".mypy_cache", ".pytest_cache", ".ruff_cache",
             ".tox", ".idea", ".vscode", ".dxn1"}
SKIP_FILES = {".DS_Store", "Thumbs.db"}
MAX_ZIP_BYTES = 512 * 1024 * 1024          # refuse snapshots > 512 MiB


def backups_root(workspace):
    if not workspace:
        return ""
    return os.path.join(workspace, BACKUP_DIR)


# ------------------------------------------------------------------ create
def create_snapshot(workspace, label="", on_progress=None):
    """Zip the workspace into .dxn1/backups/. Returns (path, stats)."""
    if not workspace or not os.path.isdir(workspace):
        raise ValueError("snapshot needs an existing workspace")
    root = backups_root(workspace)
    os.makedirs(root, exist_ok=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe_label = "".join(c for c in str(label) if c.isalnum()
                         or c in "-_")[:32]
    name = f"snapshot-{stamp}" + (f"-{safe_label}" if safe_label else "")
    path = os.path.join(root, name + ".zip")
    n = 2
    while os.path.exists(path):
        path = os.path.join(root, f"{name}-{n}.zip")
        n += 1

    files = []
    total = 0
    for base, dirs, names in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in names:
            if fname in SKIP_FILES or fname.endswith((".pyc", ".pyo",
                                                      ".zip")):
                continue
            full = os.path.join(base, fname)
            rel = os.path.relpath(full, workspace)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            total += size
            files.append((full, rel))
    if total > MAX_ZIP_BYTES:
        raise ValueError(
            f"workspace too large to snapshot ({total / 1048576:.0f} MiB)")

    stats = {"created": time.strftime("%Y-%m-%d %H:%M:%S"),
             "label": str(label or ""), "files": len(files),
             "bytes": total, "workspace": os.path.basename(workspace)}
    count = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in files:
            zf.write(full, arcname=rel)
            count += 1
            if on_progress and count % 200 == 0:
                on_progress(count, len(files))
        zf.writestr(META_NAME, json.dumps(stats, indent=2))
    return path, {**stats, "zipped": count}


# -------------------------------------------------------------------- list
def list_snapshots(workspace):
    """Newest first: [{name, path, size, when, label, files}]."""
    root = backups_root(workspace)
    out = []
    if not root or not os.path.isdir(root):
        return out
    for fname in sorted(os.listdir(root), reverse=True):
        if not fname.endswith(".zip"):
            continue
        path = os.path.join(root, fname)
        try:
            size = os.path.getsize(path)
            when = time.strftime(
                "%Y-%m-%d %H:%M",
                time.strptime(fname[9:24], "%Y%m%d-%H%M%S"))
        except (OSError, ValueError):
            continue
        label, files = "", None
        try:
            with zipfile.ZipFile(path) as zf:
                if META_NAME in zf.namelist():
                    meta = json.loads(zf.read(META_NAME).decode("utf-8"))
                    label = meta.get("label", "")
                    files = meta.get("files")
        except (OSError, ValueError, zipfile.BadZipFile):
            pass
        out.append({"name": fname[:-4], "path": path, "size": size,
                    "when": when, "label": label, "files": files})
    return out


# ----------------------------------------------------------------- restore
def restore_snapshot(workspace, path, mode="merge"):
    """Extract a snapshot back into the workspace.

    ``mode``:
      * ``merge``   — overwrite existing files, keep everything else
      * ``replace`` — refuse if the workspace has non-backup content the
                      caller didn't review (v1: same as merge, kept for
                      API clarity; the GUI shows a confirm dialog)

    Returns the number of files restored. Raises ValueError on any
    path-escape attempt (zip-slip) *before* touching disk.
    """
    if not workspace or not os.path.isdir(workspace):
        raise ValueError("restore needs an existing workspace")
    if not os.path.isfile(path):
        raise ValueError(f"snapshot missing: {path}")

    workspace_real = os.path.realpath(workspace)
    plan = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            rel = os.path.normpath(info.filename)
            if rel in (META_NAME, ".dxn1") or rel.startswith(".dxn1/"):
                continue                       # never restore the backups dir
            if rel.startswith("..") or os.path.isabs(rel) or rel.startswith("/"):
                raise ValueError(f"unsafe path in snapshot: {info.filename}")
            target = os.path.realpath(os.path.join(workspace_real, rel))
            if target != workspace_real and \
                    not target.startswith(workspace_real + os.sep):
                raise ValueError(
                    f"unsafe path in snapshot: {info.filename}")
            if info.is_dir():
                continue
            plan.append((info, target))

    count = 0
    with zipfile.ZipFile(path) as zf:
        for info, target in plan:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            count += 1
    return count


def delete_snapshot(workspace, name_or_path):
    root = backups_root(workspace)
    path = name_or_path if os.path.isabs(str(name_or_path)) \
        else os.path.join(root, f"{name_or_path}.zip")
    real_root = os.path.realpath(root)
    if not os.path.realpath(path).startswith(real_root + os.sep):
        raise ValueError("refusing to delete outside the backups folder")
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def prune_snapshots(workspace, keep=10):
    """Keep the newest ``keep`` snapshots, delete the rest. Returns the
    list of deleted paths."""
    snaps = list_snapshots(workspace)
    removed = []
    for old in snaps[keep:]:
        try:
            os.remove(old["path"])
            removed.append(old["path"])
        except OSError:
            pass
    return removed


# --------------------------------------------------------------------- GUI
_BK_C = {"bg": "#0d1117", "card": "#131a22", "border": "#232c3d",
         "text": "#e6edf3", "secondary": "#9aa7b8", "muted": "#6e7a8a",
         "ok": "#3fb950", "bad": "#f85149"}


def open_snapshots(master, theme, config=None, workspace=None, on_log=None):
    """Open the snapshot browser (palette entry point)."""
    return SnapshotWindow(master, theme, workspace, on_log=on_log)


def _human(n):
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024.0
    return f"{n} B"


class SnapshotWindow:
    """List snapshots; create, restore, delete, prune."""

    def __init__(self, master, theme, workspace=None, on_log=None):
        import tkinter as tk
        from tkinter import messagebox

        self.tk = tk
        self.msgbox = messagebox
        self.accent = getattr(theme, "accent", "#7c3aed")
        self.workspace = workspace
        self.on_log = on_log or (lambda m: None)

        self.win = tk.Toplevel(master)
        self.win.title("DXN1 STUDIO — Snapshots")
        self.win.configure(bg=_BK_C["bg"])
        self.win.transient(master)
        self.win.resizable(False, False)
        self.win.bind("<Escape>", lambda e: self.win.destroy())

        head = tk.Frame(self.win, bg=_BK_C["bg"])
        head.pack(fill="x", padx=22, pady=(16, 0))
        tk.Label(head, text="Workspace Snapshots", bg=_BK_C["bg"],
                 fg=_BK_C["text"], font=("sans-serif", 14, "bold")
                 ).pack(side="left")
        close = tk.Label(head, text="✕", bg=_BK_C["bg"], fg=_BK_C["muted"],
                         font=("sans-serif", 11, "bold"), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.win.destroy())

        sub = ("Point-in-time zips stored in the workspace "
               "(.dxn1/backups) — git metadata, caches and previous "
               "snapshots are excluded.")
        tk.Label(self.win, text=sub, bg=_BK_C["bg"],
                 fg=_BK_C["secondary"], font=("sans-serif", 9),
                 wraplength=640, justify="left").pack(anchor="w", padx=22)

        btns = tk.Frame(self.win, bg=_BK_C["bg"])
        btns.pack(fill="x", padx=22, pady=(10, 0))
        mk = tk.Label(btns, text="＋ Snapshot now", bg=self.accent,
                      fg="#ffffff", font=("sans-serif", 10, "bold"),
                      padx=14, pady=6, cursor="hand2")
        mk.pack(side="left")
        mk.bind("<Button-1>", lambda e: self._create())
        self.label_var = tk.StringVar()
        tk.Entry(btns, textvariable=self.label_var, width=22,
                 bg=_BK_C["card"], fg=_BK_C["text"],
                 insertbackground=_BK_C["text"], relief="flat",
                 font=("sans-serif", 9)).pack(side="left", padx=(8, 0),
                                              ipady=5)
        prune = tk.Label(btns, text="prune (keep 10)", bg=_BK_C["card"],
                         fg=_BK_C["secondary"],
                         font=("sans-serif", 9, "bold"), padx=10, pady=6,
                         cursor="hand2")
        prune.pack(side="right")
        prune.bind("<Button-1>", lambda e: self._prune())

        self.list_box = tk.Frame(self.win, bg=_BK_C["bg"])
        self.list_box.pack(fill="both", expand=True, padx=22,
                           pady=(10, 16))
        self.status = tk.Label(self.win, text="", bg=_BK_C["bg"],
                               fg=_BK_C["muted"], font=("sans-serif", 8))
        self.status.pack(anchor="w", padx=22, pady=(0, 12))

        self.refresh()
        self._center()

    def _close(self):
        self.win.destroy()

    def refresh(self):
        tk = self.tk
        for w in self.list_box.winfo_children():
            w.destroy()
        if not self.workspace:
            tk.Label(self.list_box,
                     text="Open a workspace first — snapshots belong to "
                          "one.",
                     bg=_BK_C["bg"], fg=_BK_C["muted"],
                     font=("sans-serif", 9)).pack(anchor="w")
            return
        snaps = list_snapshots(self.workspace)
        if not snaps:
            tk.Label(self.list_box,
                     text="No snapshots yet — create your first one.",
                     bg=_BK_C["bg"], fg=_BK_C["muted"],
                     font=("sans-serif", 9)).pack(anchor="w", pady=6)
        for s in snaps:
            self._row(s)
        self.status.config(text=f"{len(snaps)} snapshot"
                                f"{'s' if len(snaps) != 1 else ''}")

    def _row(self, s):
        tk = self.tk
        row = tk.Frame(self.list_box, bg=_BK_C["card"],
                       highlightthickness=1,
                       highlightbackground=_BK_C["border"])
        row.pack(fill="x", pady=3, ipady=5)
        left = tk.Frame(row, bg=_BK_C["card"])
        left.pack(side="left", fill="x", expand=True, padx=12)
        tk.Label(left, text=s["name"], bg=_BK_C["card"], fg=_BK_C["text"],
                 font=("sans-serif", 10, "bold"), anchor="w"
                 ).pack(anchor="w")
        extra = f"{s['when']} · {_human(s['size'])}"
        if s["label"]:
            extra += f" · “{s['label']}”"
        if s["files"] is not None:
            extra += f" · {s['files']} files"
        tk.Label(left, text=extra, bg=_BK_C["card"],
                 fg=_BK_C["muted"], font=("sans-serif", 8),
                 anchor="w").pack(anchor="w")
        restore = tk.Label(row, text="restore", bg=_BK_C["card"],
                           fg=self.accent, font=("sans-serif", 9, "bold"),
                           padx=10, cursor="hand2")
        restore.pack(side="right", padx=(0, 10))
        restore.bind("<Button-1>", lambda e, p=s["path"], n=s["name"]:
                     self._restore(p, n))
        dele = tk.Label(row, text="delete", bg=_BK_C["card"],
                        fg=_BK_C["bad"], font=("sans-serif", 9, "bold"),
                        padx=10, cursor="hand2")
        dele.pack(side="right")
        dele.bind("<Button-1>", lambda e, p=s["path"], n=s["name"]:
                  self._delete(p, n))

    def _create(self):
        if not self.workspace:
            return
        try:
            path, stats = create_snapshot(
                self.workspace, label=self.label_var.get().strip())
        except (OSError, ValueError) as exc:
            self.msgbox.showerror("Snapshot", f"Could not snapshot:\n{exc}")
            return
        self.label_var.set("")
        self.on_log(f"snapshot created: {os.path.basename(path)} "
                    f"({stats['zipped']} files)")
        self.status.config(text="snapshot created ✓", fg=_BK_C["ok"])
        self.refresh()

    def _restore(self, path, name):
        if not self.msgbox.askyesno(
                "Restore snapshot",
                f"Restore “{name}”?\n\nExisting files with the same name "
                f"will be overwritten. Files created since the snapshot "
                f"are kept."):
            return
        try:
            n = restore_snapshot(self.workspace, path)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self.msgbox.showerror("Snapshot", f"Restore failed:\n{exc}")
            return
        self.on_log(f"snapshot restored: {name} ({n} files)")
        self.status.config(text=f"restored {n} files ✓", fg=_BK_C["ok"])

    def _delete(self, path, name):
        if not self.msgbox.askyesno("Delete snapshot",
                                    f"Delete “{name}” permanently?"):
            return
        try:
            delete_snapshot(self.workspace, path)
        except (OSError, ValueError) as exc:
            self.msgbox.showerror("Snapshot", f"Delete failed:\n{exc}")
            return
        self.refresh()

    def _prune(self):
        removed = prune_snapshots(self.workspace, keep=10)
        self.on_log(f"pruned {len(removed)} old snapshots")
        self.refresh()

    def _center(self):
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        try:
            mx = self.win.master.winfo_rootx() + \
                (self.win.master.winfo_width() - w) // 2
            my = self.win.master.winfo_rooty() + \
                (self.win.master.winfo_height() - h) // 3
        except Exception:               # noqa: BLE001
            mx = my = 40
        self.win.geometry(f"+{max(0, mx)}+{max(0, my)}")
