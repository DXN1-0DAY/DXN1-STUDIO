"""DXN1 STUDIO — session restore (DS2 v2.30).

Pick up exactly where you left off. Every close snapshots the open
tabs, the active file and the cursor position into
``~/.dxn1-studio/sessions/<workspace-hash>.json``; the Workshop's
*Session Restore* window (or terminal ``session`` / ``resume``) lists
every saved workspace and reopens it — files, focus and cursor line.

The engine is pure and junk-tolerant: corrupt JSON reads back as an
empty session, exotic paths coerce via ``str()``, saving never raises
(honest ``(ok, error)`` tuples). ``base=`` overrides the storage
directory for tests. Note: the app's lightweight auto-restore of tab
paths on project open (config key ``session_tabs``) stays as-is —
this store is the richer sibling with cursors and a manager UI.
"""

import hashlib
import json
import os
import time

import tkinter as tk
from tkinter import ttk

try:
    from .i18n import tr
except ImportError:  # pragma: no cover — direct self-test run
    def tr(key, **kwargs):
        return key

MAX_TABS = 50
MAX_SESSIONS = 40          # json files kept on disk
_SCHEMA = 1


# ------------------------------------------------------------------ engine
def workspace_key(workspace):
    """Stable short id for a workspace path (agent.py convention)."""
    try:
        s = str(workspace)
    except Exception:  # noqa: BLE001 — exotic path objects
        return "unknown"
    if not s or s == "None":
        return "unknown"
    raw = os.path.abspath(s)
    return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:10]


def session_dir(base=None):
    """Storage directory (created on demand); ``(path,)`` never raises."""
    root = base or os.path.join(os.path.expanduser("~"), ".dxn1-studio",
                                "sessions")
    return os.path.abspath(str(root))


def session_path(workspace, base=None):
    return os.path.join(session_dir(base),
                        workspace_key(workspace) + ".json")


def snapshot(tabs, active="", cursor=None, workspace=""):
    """Normalize a session into the stored dict shape.

    ``tabs`` — iterable of paths (str-coerced, deduped, capped at 50);
    ``active`` — the focused file; ``cursor`` — optional
    ``{path: (line, col)}`` mapping, clamped to sane integers. Junk is
    dropped, never raised.
    """
    clean, seen = [], set()
    for t in (tabs or []):
        if not isinstance(t, (str, bytes, os.PathLike)):
            continue
        try:
            p = os.path.abspath(os.fspath(t))
        except Exception:  # noqa: BLE001
            continue
        if p and p not in seen:
            seen.add(p)
            clean.append(p)
        if len(clean) >= MAX_TABS:
            break
    act = ""
    try:
        act = os.path.abspath(os.fspath(active)) if active else ""
    except Exception:  # noqa: BLE001
        act = ""
    curs = {}
    for k, v in (cursor or {}).items():
        try:
            line, col = int(v[0]), int(v[1])
        except Exception:  # noqa: BLE001
            continue
        if line >= 1:
            curs[str(k)] = {"line": line, "col": max(0, col)}
    return {"v": _SCHEMA, "workspace": str(workspace or ""),
            "tabs": clean, "active": act, "cursor": curs,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")}


def save(workspace, data, base=None):
    """Write the session JSON atomically. Returns ``(ok, error)``."""
    d = session_dir(base)
    try:
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, workspace_key(workspace) + ".json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
        return True, ""
    except Exception as exc:  # noqa: BLE001 — honest failure
        return False, str(exc)


def load(workspace, base=None):
    """Read a session; corrupt or missing files read as ``{}``."""
    try:
        with open(session_path(workspace, base), "r",
                  encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 — missing/corrupt is just empty
        return {}


def clear(workspace, base=None):
    """Delete one saved session. Returns ``(ok, error)``."""
    try:
        os.remove(session_path(workspace, base))
        return True, ""
    except FileNotFoundError:
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def list_sessions(base=None):
    """All saved sessions, newest first: ``[{key, data, path}, ...]``."""
    d = session_dir(base)
    out = []
    try:
        names = os.listdir(d)
    except Exception:  # noqa: BLE001
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(d, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                out.append({"key": name[:-5], "path": path,
                            "data": data})
        except Exception:  # noqa: BLE001 — corrupt file is skipped
            continue
    out.sort(key=lambda s: str(s["data"].get("saved_at", "")),
             reverse=True)
    return out[:MAX_SESSIONS]


def describe(data):
    """One-line human summary, e.g. ``3 tabs · active main.py · 14:20``."""
    if not isinstance(data, dict):
        return "empty session"
    tabs = data.get("tabs") or []
    active = os.path.basename(str(data.get("active") or "")) \
        if data.get("active") else "—"
    when = str(data.get("saved_at") or "").replace("T", " ")[11:16] \
        if data.get("saved_at") else "?"
    return f"{len(tabs)} tabs · active {active} · {when}"


def restore_plan(data):
    """Filter a session down to what can actually be reopened.

    Returns ``(tabs, active, cursor_for_active)`` — only existing
    files survive, tabs capped at 50, cursor is ``None`` when unknown.
    """
    if not isinstance(data, dict):
        return [], "", None
    tabs = [p for p in (data.get("tabs") or [])
            if isinstance(p, str) and os.path.isfile(p)][:MAX_TABS]
    active = data.get("active")
    if not (isinstance(active, str) and os.path.isfile(active)):
        active = ""
    cursor = None
    curs = data.get("cursor")
    if isinstance(curs, dict) and active and active in curs:
        try:
            cursor = (int(curs[active].get("line", 1)),
                      int(curs[active].get("col", 0)))
        except Exception:  # noqa: BLE001
            cursor = None
    return tabs, active, cursor


# ------------------------------------------------------------------ window
class SessionRestore(tk.Toplevel):
    """Saved-workspace browser: pick a session, restore it, or clear."""

    def __init__(self, parent, theme, app=None, base=None):
        super().__init__(parent)
        self.app = app
        self.base = base
        self.title("Session Restore — DXN1 STUDIO")
        self.geometry("620x380")
        try:
            self.configure(bg=theme["bg"])
        except Exception:  # noqa: BLE001 — junk theme falls back
            self.configure(bg="#16161e")
        self.t = theme

        head = tk.Label(self, text=tr("session.saved"), bg=theme["bg"],
                        fg=theme["text"], font=("TkDefaultFont", 12,
                                                "bold"))
        head.pack(anchor="w", padx=14, pady=(12, 2))
        self.sub = tk.Label(self, text="", bg=theme["bg"],
                            fg=theme["text_muted"], font=("TkDefaultFont",
                                                          9))
        self.sub.pack(anchor="w", padx=14, pady=(0, 6))

        wrap = tk.Frame(self, bg=theme["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=14)
        self.tree = ttk.Treeview(wrap, columns=("ws", "tabs", "saved"),
                                 show="headings", height=7,
                                 style="DS2.Treeview")
        for col, txt, w in (("ws", "workspace", 280), ("tabs", "tabs", 60),
                            ("saved", "saved", 130)):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb = ttk.Scrollbar(wrap, command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.preview = tk.Label(self, text="", bg=theme["card"],
                                fg=theme["text_muted"],
                                font=("TkFixedFont", 9), anchor="w",
                                justify="left")
        self.preview.pack(fill=tk.X, padx=14, pady=8)

        btns = tk.Frame(self, bg=theme["bg"])
        btns.pack(fill=tk.X, padx=14, pady=(0, 4))
        self.b_restore = tk.Button(
            btns, text=tr("session.restore"), command=self.restore_selected,
            bg=theme["button"], fg=theme["text"],
            activebackground=theme["button_hover"], relief=tk.FLAT)
        self.b_restore.pack(side=tk.LEFT, padx=(0, 6))
        self.b_clear = tk.Button(
            btns, text=tr("session.clear"), command=self.clear_selected,
            bg=theme["button"], fg=theme["text"],
            activebackground=theme["button_hover"], relief=tk.FLAT)
        self.b_clear.pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btns, text="Refresh", command=self._refresh,
                  bg=theme["button"], fg=theme["text"],
                  activebackground=theme["button_hover"],
                  relief=tk.FLAT).pack(side=tk.LEFT)

        self.status = tk.Label(self, text="", bg=theme["bg"],
                               fg=theme["text_muted"],
                               font=("TkDefaultFont", 9))
        self.status.pack(anchor="w", padx=14, pady=(2, 10))
        if self.app is None:
            self.status.configure(
                text="engine-only preview (no app attached)")
        self._refresh()
        try:
            self.transient(parent)
        except Exception:  # noqa: BLE001
            pass
        # DS2 v2.61 — width accounting round three: open no narrower
        # than what it actually packed (long workspace names, full
        # preview lines)
        from . import geom as _geom
        _geom.fit_to_content(self, 620, 380)

    # ------------------------------------------------------------- actions
    def _refresh(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        sessions = list_sessions(base=self.base)
        for s in sessions:
            data = s["data"]
            ws = os.path.basename(str(data.get("workspace") or
                                      s["key"])) or s["key"]
            when = str(data.get("saved_at") or "?").replace("T", " ")
            self.tree.insert("", tk.END, iid=s["key"],
                             values=(ws, len(data.get("tabs") or []),
                                     when))
        n = len(sessions)
        self.sub.configure(text=f"{n} workspace"
                           f"{'' if n == 1 else 's'} saved")
        if not sessions:
            self.preview.configure(text="no saved sessions yet — "
                                   "they appear when you close the "
                                   "studio with files open")

    def _sel_data(self):
        sel = self.tree.selection()
        if not sel:
            return None
        for s in list_sessions(base=self.base):
            if s["key"] == sel[0]:
                return s
        return None

    def _on_select(self, _event=None):
        s = self._sel_data()
        if not s:
            self.preview.configure(text="")
            return
        data = s["data"]
        lines = []
        for p in (data.get("tabs") or [])[:8]:
            mark = " → " if p == data.get("active") else "   "
            lines.append(mark + os.path.basename(p))
        if len(data.get("tabs") or []) > 8:
            lines.append(f"   … +{len(data['tabs']) - 8} more")
        self.preview.configure(text="\n".join(lines) or
                               "(empty session)")

    def restore_selected(self):
        s = self._sel_data()
        if not s:
            return
        tabs, active, cursor = restore_plan(s["data"])
        if not tabs and not active:
            self.status.configure(
                text="nothing restorable — files no longer exist")
            return
        if self.app is None:
            self.status.configure(
                text=f"would restore {len(tabs)} tab(s) "
                     f"(no app attached)")
            return
        opened = 0
        for path in tabs:
            try:
                if path != getattr(self.app.editor, "file_path", ""):
                    self.app.open_file(path)
                opened += 1
            except Exception:  # noqa: BLE001 — one bad tab must not
                continue      # block the rest of the restore
        if active and cursor:
            try:
                self.app.editor.goto_line(cursor[0])
                self.app.editor.text.mark_set(
                    "insert", f"{cursor[0]}.{cursor[1]}")
                self.app.editor.text.see("insert")
            except Exception:  # noqa: BLE001 — cursor is best-effort
                pass
        self.status.configure(
            text=f"restored {opened} tab(s)"
                 f"{f', cursor line {cursor[0]}' if cursor else ''}")

    def clear_selected(self):
        s = self._sel_data()
        if not s:
            return
        ok, err = clear_by_key(s["key"], base=self.base)
        self._refresh()
        self.status.configure(text="cleared" if ok
                              else f"clear failed: {err}")


def clear_by_key(key, base=None):
    """Delete a session file by its listed key (window helper)."""
    try:
        os.remove(os.path.join(session_dir(base), str(key) + ".json"))
        return True, ""
    except FileNotFoundError:
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def open_session_restore(parent, theme, app=None, base=None):
    """Defensive opener — the window never raises to the caller."""
    try:
        return SessionRestore(parent, theme, app=app, base=base)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- self-test
if __name__ == "__main__":
    import tempfile
    base = tempfile.mkdtemp(prefix="ds2-session-selftest-")
    wdir = os.path.join(base, "w")
    os.makedirs(wdir, exist_ok=True)
    fa, fb = os.path.join(wdir, "a.py"), os.path.join(wdir, "b.py")
    open(fa, "w").write("x = 1\n")
    open(fb, "w").write("y = 2\n")
    assert workspace_key(None) == "unknown"
    assert workspace_key("/a") != workspace_key("/b")
    snap = snapshot([fa, fa, 42, None, fb],
                    active=fa,
                    cursor={fa: (12, 4), "junk": "x"},
                    workspace=wdir)
    assert snap["tabs"] == [fa, fb]
    assert snap["cursor"][fa] == {"line": 12, "col": 4}
    ok, err = save(wdir, snap, base=base)
    assert ok and not err, err
    assert load(wdir, base=base)["active"].endswith("a.py")
    assert load("/missing", base=base) == {}
    open(os.path.join(base, "corrupt.json"), "w").write("{oops")
    assert list_sessions(base=base) != []
    assert describe(snap).startswith("2 tabs · active a.py")
    assert describe(None) == "empty session"
    tabs, act, cur = restore_plan(snap)
    assert act.endswith("a.py") and cur == (12, 4)
    assert save(wdir, snapshot([], workspace=wdir), base=base)[0]
    ok, _ = clear(wdir, base=base)
    assert ok and load(wdir, base=base) == {}
    assert clear("/never", base=base)[0] is True
    print("session.py self-test OK")
