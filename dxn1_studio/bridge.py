"""DXN1 STUDIO — Electron bridge.

The Python engine speaks a tiny newline-delimited JSON protocol on
stdio so the Electron shell can drive the real studio core without
Tkinter. This is the VS Code pattern: a native (web-tech) front end,
a local process doing the actual work.

Protocol — one JSON object per line:
    request : {"id": 7, "cmd": "tree", "args": {...}}
    reply   : {"id": 7, "ok": true,  "result": ...}
            | {"id": 7, "ok": false, "error": "human message"}

Commands (v1):
    hello          -> {app, version, channel, workspace, python}
    workspace.set  -> {workspace}        (switch workspace root)
    tree           -> {entries: [...]}   (recursive file listing)
    read_file      -> {path, content, size, mtime}
    write_file     -> {path, size}       (creates parent dirs; refuses
                                            paths outside workspace)
    rename_path    -> {from, to}
    delete_path    -> {path}
    make_dir       -> {path}
    stat           -> {path, exists, size, mtime, is_dir}
    reveal         -> {path}             (OS file manager)
    open_external  -> {url}              (browser)

Every reply is flushed immediately; the loop never crashes on a bad
request — errors ride back as {"ok": false}. Paths are always
resolved against the workspace root and escapes are refused, so the
UI can never read/write outside the opened workspace by accident.
"""

import json
import os
import subprocess
import sys
import threading
import time

from . import APP_CHANNEL, APP_NAME, APP_VERSION

_BRIDGE_MAX_BYTES = 8 * 1024 * 1024      # single read_file ceiling
_BRIDGE_TREE_LIMIT = 20_000              # entries before truncation
_BRIDGE_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".dxn1",
}


class BridgeError(Exception):
    """Raised for expected, user-facing bridge failures."""


class Bridge:
    """Workspace file engine shared by the stdio loop and tests."""

    def __init__(self, workspace=None, stdin=None, stdout=None):
        self.workspace = os.path.abspath(workspace or os.getcwd())
        self._stdin = stdin if stdin is not None else sys.stdin
        self._stdout = stdout if stdout is not None else sys.stdout
        self._alive = True

    # ------------------------------------------------------------ paths
    def resolve(self, rel):
        """Resolve `rel` inside the workspace; refuse escapes."""
        rel = (rel or "").replace("\\", "/").lstrip("/")
        if rel in ("", "."):
            return self.workspace
        target = os.path.abspath(os.path.join(self.workspace, rel))
        root = self.workspace.rstrip(os.sep) + os.sep
        if target != self.workspace and not target.startswith(root):
            raise BridgeError("path escapes the workspace")
        return target

    # ---------------------------------------------------------- handlers
    def cmd_hello(self, args):
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "channel": APP_CHANNEL,
            "workspace": self.workspace,
            "python": sys.version.split()[0],
        }

    def cmd_workspace_set(self, args):
        new = args.get("workspace") or ""
        if not os.path.isdir(new):
            raise BridgeError(f"not a directory: {new}")
        self.workspace = os.path.abspath(new)
        return {"workspace": self.workspace}

    def cmd_tree(self, args):
        limit = int(args.get("limit") or _BRIDGE_TREE_LIMIT)
        entries = []
        truncated = False
        for dirpath, dirnames, filenames in os.walk(self.workspace):
            dirnames[:] = sorted(
                d for d in dirnames if d not in _BRIDGE_SKIP_DIRS
                and not d.startswith("."))
            rel_dir = os.path.relpath(dirpath, self.workspace)
            if rel_dir == ".":
                rel_dir = ""
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.join(rel_dir, name) if rel_dir else name
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                entries.append({"path": rel.replace(os.sep, "/"),
                                "size": st.st_size,
                                "mtime": st.st_mtime})
                if len(entries) >= limit:
                    truncated = True
                    break
            if truncated:
                break
        return {"entries": entries, "truncated": truncated,
                "workspace": self.workspace}

    def cmd_read_file(self, args):
        path = self.resolve(args.get("path"))
        if os.path.isdir(path):
            raise BridgeError("that is a directory, not a file")
        if not os.path.exists(path):
            raise BridgeError(f"file not found: {args.get('path')}")
        size = os.path.getsize(path)
        if size > _BRIDGE_MAX_BYTES:
            raise BridgeError(
                f"file too large ({size // 1024 // 1024} MB) — "
                "the bridge reads up to 8 MB")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        return {"path": args.get("path"), "content": content,
                "size": size, "mtime": os.path.getmtime(path)}

    def cmd_write_file(self, args):
        rel = args.get("path")
        if not rel:
            raise BridgeError("write_file needs a path")
        path = self.resolve(rel)
        content = args.get("content") or ""
        os.makedirs(os.path.dirname(path) or self.workspace,
                    exist_ok=True)
        tmp = path + ".dxn1-tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
        return {"path": rel, "size": len(content.encode("utf-8")),
                "mtime": time.time()}

    def cmd_rename_path(self, args):
        src = self.resolve(args.get("from"))
        dst = self.resolve(args.get("to"))
        if not os.path.exists(src):
            raise BridgeError(f"not found: {args.get('from')}")
        if os.path.exists(dst):
            raise BridgeError(f"destination exists: {args.get('to')}")
        os.makedirs(os.path.dirname(dst) or self.workspace, exist_ok=True)
        os.rename(src, dst)
        return {"from": args.get("from"), "to": args.get("to")}

    def cmd_delete_path(self, args):
        path = self.resolve(args.get("path"))
        if path == self.workspace:
            raise BridgeError("refusing to delete the workspace itself")
        if not os.path.exists(path):
            raise BridgeError(f"not found: {args.get('path')}")
        if os.path.isdir(path):
            os.rmdir(path)          # refuse non-empty dirs on purpose
        else:
            os.remove(path)
        return {"path": args.get("path")}

    def cmd_make_dir(self, args):
        path = self.resolve(args.get("path"))
        os.makedirs(path, exist_ok=True)
        return {"path": args.get("path")}

    def cmd_stat(self, args):
        path = self.resolve(args.get("path"))
        exists = os.path.exists(path)
        return {"path": args.get("path"), "exists": exists,
                "is_dir": os.path.isdir(path) if exists else False,
                "size": os.path.getsize(path) if exists else 0,
                "mtime": os.path.getmtime(path) if exists else 0}

    def cmd_reveal(self, args):
        path = self.resolve(args.get("path"))
        if not os.path.exists(path):
            raise BridgeError(f"not found: {args.get('path')}")
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open",
                              os.path.dirname(path) or "/"])
        return {"revealed": args.get("path")}

    def cmd_open_external(self, args):
        url = str(args.get("url") or "")
        if not url.startswith(("http://", "https://")):
            raise BridgeError("only http(s) URLs may be opened")
        import webbrowser
        webbrowser.open(url)
        return {"opened": url}

    # ------------------------------------------------------------- loop
    def handle(self, line):
        """Handle one request line -> reply dict (never raises)."""
        try:
            req = json.loads(line)
        except (ValueError, TypeError) as exc:
            return {"id": None, "ok": False,
                    "error": f"bad json: {exc}"}
        rid = req.get("id")
        cmd = str(req.get("cmd") or "")
        args = req.get("args") or {}
        handler = getattr(self, f"cmd_{cmd}", None)
        if handler is None or not cmd.replace("_", "").isalnum():
            return {"id": rid, "ok": False,
                    "error": f"unknown command: {cmd}"}
        try:
            return {"id": rid, "ok": True, "result": handler(args)}
        except BridgeError as exc:
            return {"id": rid, "ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 — the loop must survive
            return {"id": rid, "ok": False,
                    "error": f"{type(exc).__name__}: {exc}"}

    def serve_forever(self):
        """Read request lines, write replies — until stdin closes."""
        while self._alive:
            try:
                line = self._stdin.readline()
            except Exception:  # noqa: BLE001
                break
            if not line:
                break
            reply = self.handle(line)
            try:
                self._stdout.write(json.dumps(reply) + "\n")
                self._stdout.flush()
            except Exception:  # noqa: BLE001 — parent went away
                break

    def stop(self):
        self._alive = False


def serve(workspace=None):
    """Entry point: `python3 -m dxn1_studio.bridge [workspace]`."""
    ws = workspace
    if not ws and len(sys.argv) > 1:
        ws = sys.argv[1]
    Bridge(ws).serve_forever()


if __name__ == "__main__":
    serve()
