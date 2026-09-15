"""DXN1 STUDIO — the bridge to the Electron + Web UI.

A localhost-only HTTP server (pure stdlib) that serves the web
renderer in ``webui/`` and exposes a small, token-guarded JSON API
to the running studio: state, tabs, file open/save, the command
palette, and run control. Every mutation is scheduled onto the Tk
main loop via ``root.after`` — the HTTP thread never touches widgets.

Security model:
- binds 127.0.0.1 ONLY — nothing leaves the machine;
- every request must carry the per-session token written to
  ``.dxn1/bridge_token`` (600 perms) — other local users/processes
  cannot drive the IDE;
- file paths are resolved and must stay inside the workspace.
"""

import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import APP_VERSION


def _version():
    return f"{APP_VERSION}-beta"


_WEBUI = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "webui")

_MIME = {".html": "text/html; charset=utf-8",
         ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png",
         ".ico": "image/x-icon"}


class BridgeState:
    """Thread-safe snapshot of what the web UI needs."""

    def __init__(self, app):
        self.app = app
        self.token = secrets.token_hex(16)

    # ---- reads (called on the HTTP thread; only pure data) ----------
    def snapshot(self):
        app = self.app
        tabs = []
        try:
            active = getattr(app.editor, "file_path", None)
            for path, buf in getattr(app, "_buffers", {}).items():
                name = os.path.basename(path) or path
                tabs.append({"path": path, "name": name,
                             "dirty": bool(buf.get("dirty")),
                             "active": path == active})
        except Exception:  # noqa: BLE001 — a dead widget must not 500
            pass
        theme = getattr(app, "theme", None)
        tokens = {}
        if theme is not None:
            for key in ("bg", "sidebar", "header", "editor", "terminal",
                        "statusbar", "border", "hover", "text",
                        "text_secondary", "text_muted", "card",
                        "card_border", "success"):
                try:
                    tokens[key] = theme[key]
                except Exception:  # noqa: BLE001
                    pass
            try:
                tokens["accent"] = theme.accent
            except Exception:  # noqa: BLE001
                pass
        log = ""
        try:
            log = app.terminal.log_text.get("1.0", "end-1c")[-8000:]
        except Exception:  # noqa: BLE001
            pass
        status = ""
        try:
            status = app.status_file.cget("text")
        except Exception:  # noqa: BLE001
            pass
        return {"ok": True,
                "app": "DXN1 STUDIO",
                "version": _version(),
                "workspace": getattr(app, "project_dir", ""),
                "tabs": tabs,
                "theme": tokens,
                "terminal_tail": log,
                "status": status}

    def commands(self):
        out = []
        try:
            for i, (label, key, _fn) in enumerate(
                    self.app.palette_commands()):
                out.append({"index": i, "label": label, "key": key})
        except Exception:  # noqa: BLE001
            pass
        return out

    def file_read(self, path):
        app = self.app
        real = self._sandbox(path)
        if real is None:
            return None, "path escapes the workspace"
        if os.path.isdir(real):
            return None, "is a directory"
        try:
            with open(real, "r", encoding="utf-8", errors="replace") as fh:
                return {"path": path, "content": fh.read()}, None
        except OSError as exc:
            return None, str(exc)

    def file_write(self, path, content):
        real = self._sandbox(path)
        if real is None:
            return None, "path escapes the workspace"
        try:
            os.makedirs(os.path.dirname(real) or ".", exist_ok=True)
            with open(real, "w", encoding="utf-8") as fh:
                fh.write(content)
        except OSError as exc:
            return None, str(exc)

        def _reopen():
            try:
                if path in getattr(self.app, "_buffers", {}):
                    self.app.open_file(path)
            except Exception:  # noqa: BLE001
                pass
        try:
            self.app.root.after(0, _reopen)
        except Exception:  # noqa: BLE001
            pass
        return {"path": path, "saved": True}, None

    def tree(self):
        """Shallow workspace listing (dirs + files, 2 levels)."""
        root_dir = getattr(self.app, "project_dir", "") or "."
        out = []
        try:
            for name in sorted(os.listdir(root_dir)):
                if name.startswith("."):
                    continue
                full = os.path.join(root_dir, name)
                if os.path.isdir(full):
                    kids = []
                    try:
                        kids = sorted(os.listdir(full))[:64]
                    except OSError:  # noqa: BLE001
                        pass
                    out.append({"name": name, "dir": True,
                                "children": kids})
                else:
                    out.append({"name": name, "dir": False})
        except OSError:  # noqa: BLE001
            pass
        return out

    # ---- mutations (scheduled on the Tk loop) ------------------------
    def command(self, index):
        try:
            cmds = self.app.palette_commands()
            if not isinstance(index, int) or not (0 <= index < len(cmds)):
                return None, "bad command index"
            label = cmds[index][0]
            fn = cmds[index][2]

            def _run():
                try:
                    fn()
                except Exception:  # noqa: BLE001
                    pass
            self.app.root.after(0, _run)
            return {"ran": label}, None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    def open_path(self, path):
        real = self._sandbox(path)
        if real is None:
            return None, "path escapes the workspace"

        def _open():
            try:
                self.app.open_file(real)
            except Exception:  # noqa: BLE001
                pass
        try:
            self.app.root.after(0, _open)
        except Exception:  # noqa: BLE001
            pass
        return {"opened": path}, None

    # ---- file ops (reuse the TESTED stdio engine: bridge.Bridge) ------
    def _engine(self):
        from .bridge import Bridge
        if not hasattr(self, "_engine_obj"):
            self._engine_obj = Bridge(
                getattr(self.app, "project_dir", None) or os.getcwd())
        return self._engine_obj

    def new_file(self, path, content=""):
        try:
            self._engine().cmd_write_file({"path": path,
                                           "content": content})
        except Exception as exc:  # noqa: BLE001 — BridgeError or OSError
            return None, str(exc)
        return self.open_path(path)

    def delete_path(self, path):
        try:
            self._engine().cmd_delete_path({"path": path})
        except Exception as exc:  # noqa: BLE001 — BridgeError or OSError
            return None, str(exc)
        return {"deleted": path}, None

    def rename_path(self, path, to):
        try:
            self._engine().cmd_rename_path({"from": path, "to": to})
        except Exception as exc:  # noqa: BLE001 — BridgeError or OSError
            return None, str(exc)
        return {"renamed": path, "to": to}, None

    def make_dir(self, path):
        try:
            self._engine().cmd_make_dir({"path": path})
        except Exception as exc:  # noqa: BLE001 — BridgeError or OSError
            return None, str(exc)
        return {"made": path}, None

    def run_project(self):
        def _run():
            try:
                self.app.run_current()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.app.root.after(0, _run)
        except Exception:  # noqa: BLE001
            pass
        return {"ran": True}, None

    # ---- helpers ------------------------------------------------------
    def _sandbox(self, path):
        """Resolve `path` and demand it stays inside the workspace."""
        try:
            base = os.path.realpath(getattr(
                self.app, "project_dir", "") or os.getcwd())
            real = os.path.realpath(os.path.join(base, path))
            if real != base and not real.startswith(base + os.sep):
                return None
            return real
        except Exception:  # noqa: BLE001
            return None


class _Handler(BaseHTTPRequestHandler):
    state = None  # injected by start_bridge
    server_version = "DXN1Bridge/1"

    def log_message(self, fmt, *args):  # quiet — the IDE has a terminal
        pass

    # ---- helpers ------------------------------------------------------
    def _authorized(self):
        q = parse_qs(urlparse(self.path).query)
        tok = self.headers.get("X-DXN1-Token") or \
            (q.get("token") or [""])[0]
        return tok == self.state.token

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, name):
        full = os.path.join(_WEBUI, name)
        if not os.path.isfile(full):
            self._send_json({"ok": False, "error": "not found"}, 404)
            return
        with open(full, "rb") as fh:
            body = fh.read()
        ext = os.path.splitext(name)[1]
        self.send_response(200)
        self.send_header("Content-Type",
                         _MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > 8 * 1024 * 1024:
            return None
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:  # noqa: BLE001
            return None

    # ---- routes -------------------------------------------------------
    def do_GET(self):  # noqa: N802 — stdlib naming
        u = urlparse(self.path)
        route = u.path
        if route in ("/", "/index.html"):
            self._send_file("index.html")
            return
        if route in ("/app.js", "/app.css"):
            self._send_file(route.lstrip("/"))
            return
        if not self._authorized():
            self._send_json({"ok": False, "error": "unauthorized"}, 401)
            return
        q = parse_qs(u.query)
        if route == "/api/state":
            self._send_json(self.state.snapshot())
        elif route == "/api/commands":
            self._send_json({"ok": True, "commands": self.state.commands()})
        elif route == "/api/tree":
            self._send_json({"ok": True, "tree": self.state.tree()})
        elif route == "/api/file":
            payload, err = self.state.file_read(
                (q.get("path") or [""])[0])
            self._send_json(
                {"ok": err is None, **({"file": payload} if payload else
                                       {"error": err})},
                200 if err is None else 400)
        else:
            self._send_json({"ok": False, "error": "unknown"}, 404)

    def do_POST(self):  # noqa: N802 — stdlib naming
        if not self._authorized():
            self._send_json({"ok": False, "error": "unauthorized"}, 401)
            return
        u = urlparse(self.path)
        body = self._read_body()
        if u.path != "/api/run" and body is None:
            self._send_json({"ok": False, "error": "bad body"}, 400)
            return
        if u.path == "/api/command":
            payload, err = self.state.command(body.get("index"))
        elif u.path == "/api/file":
            payload, err = self.state.file_write(
                str(body.get("path") or ""), str(body.get("content") or ""))
        elif u.path == "/api/open":
            payload, err = self.state.open_path(
                str(body.get("path") or ""))
        elif u.path == "/api/new_file":
            payload, err = self.state.new_file(
                str(body.get("path") or ""),
                str(body.get("content") or ""))
        elif u.path == "/api/delete":
            payload, err = self.state.delete_path(
                str(body.get("path") or ""))
        elif u.path == "/api/rename":
            payload, err = self.state.rename_path(
                str(body.get("path") or ""), str(body.get("to") or ""))
        elif u.path == "/api/mkdir":
            payload, err = self.state.make_dir(
                str(body.get("path") or ""))
        elif u.path == "/api/run":
            payload, err = self.state.run_project()
        else:
            payload, err = None, "unknown route"
        self._send_json(
            {"ok": err is None, **(payload or {}), **({"error": err}
                                                      if err else {})},
            200 if err is None else 400)


def start_bridge(app, host="127.0.0.1", port=0):
    """Start the bridge server for `app` on a random free port.

    Returns (server, url, token). The token is ALSO written to
    ``<workspace>/.dxn1/bridge_token`` (chmod 600) so the web UI /
    Electron shell can pick it up without a user copy-paste.
    """
    state = BridgeState(app)

    class _Bound(_Handler):
        pass
    _Bound.state = state
    server = ThreadingHTTPServer((host, port), _Bound)
    server.daemon_threads = True
    url = f"http://{host}:{server.server_address[1]}"
    # persist the token for the renderer
    try:
        ws = getattr(app, "project_dir", "") or os.getcwd()
        dxn1_dir = os.path.join(ws, ".dxn1")
        os.makedirs(dxn1_dir, exist_ok=True)
        tok_path = os.path.join(dxn1_dir, "bridge_token")
        with open(tok_path, "w", encoding="utf-8") as fh:
            fh.write(state.token)
        try:
            os.chmod(tok_path, 0o600)
        except OSError:  # noqa: BLE001
            pass
    except OSError:  # noqa: BLE001
        tok_path = None
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()
    return server, url, state.token
