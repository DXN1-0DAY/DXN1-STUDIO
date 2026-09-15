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
import queue
import re
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
    """Thread-safe snapshot of what the web UI needs.

    Mutations NEVER call Tk from the HTTP thread — they push a closure
    onto a queue that a main-loop pump drains. `start_bridge` (which
    runs on the Tk main thread) schedules the pump, so cross-thread
    `after` calls are avoided entirely.
    """

    def __init__(self, app):
        self.app = app
        self.token = secrets.token_hex(16)
        self._q = queue.Queue()

    def start_pump(self):
        """Main-thread only: drain the mutation queue every 80 ms."""
        try:
            while True:
                fn = self._q.get_nowait()
                try:
                    fn()
                except Exception:  # noqa: BLE001 — a bad mutation dies alone
                    pass
        except queue.Empty:
            pass
        try:
            self.app.root.after(80, self.start_pump)
        except Exception:  # noqa: BLE001 — root gone: pump ends quietly
            pass

    def post(self, fn):
        """Schedule a closure on the Tk main loop (thread-safe)."""
        self._q.put(fn)

    # ---- reads (called on the HTTP thread; only pure data) ----------
    def snapshot(self):
        app = self.app
        base = getattr(app, "project_dir", None) or os.getcwd()
        tabs = []
        try:
            active = getattr(app.editor, "file_path", None)
            for path, buf in getattr(app, "_buffers", {}).items():
                name = os.path.basename(path) or path
                # workspace-relative for the web face (falls back to the
                # basename for paths outside the workspace)
                try:
                    rel = os.path.relpath(path, base)
                except ValueError:  # noqa: PERF203 — different drive etc.
                    rel = name
                tabs.append({"path": rel, "name": name,
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
        agent = {"busy": False, "transcript": [], "model": ""}
        try:
            panel = getattr(app, "agent_panel", None)
            if panel is not None:
                agent = {"busy": bool(getattr(panel, "_busy", False)),
                         "transcript": list(
                             getattr(panel, "transcript", []))[-40:],
                         "model": getattr(
                             getattr(panel, "engine", None),
                             "name", "") or ""}
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
                "agent": agent,
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
        self.post(_reopen)
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

    _WALK_SKIP = {".git", "__pycache__", "node_modules", ".venv",
                  "venv", ".dxn1", ".mypy_cache", ".pytest_cache",
                  ".ruff_cache"}

    def files(self):
        """Flat relative-path list for Ctrl+P quick-open (capped)."""
        base = getattr(self.app, "project_dir", None) or os.getcwd()
        out = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in sorted(dirnames)
                           if d not in self._WALK_SKIP and
                           not d.startswith(".")]
            for fn in sorted(filenames):
                if fn.startswith("."):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    rel = os.path.relpath(full, base)
                except ValueError:  # noqa: BLE001
                    continue
                out.append(rel)
                if len(out) >= 2000:
                    return out
        return out

    _SNIP_LANGS = {"py": "python", "python": "python",
                   "js": "javascript", "javascript": "javascript",
                   "ts": "javascript", "jsx": "javascript",
                   "tsx": "javascript",
                   "html": "html", "htm": "html",
                   "md": "markdown", "markdown": "markdown",
                   "css": "css", "json": "json"}

    def snippets(self, lang):
        """Snippet pack for the web editor (GET /api/snippets).

        Reuses the Tk-side brain (snippets2): same built-in packs,
        same ~/.dxn1-studio/snippets.json user overrides — both faces
        share one registry, so a snippet added on the desktop shows up
        in the browser and vice versa. Unknown languages answer an
        empty pack (ok:true) — the renderer treats that as "no
        snippets", never as a failure.
        """
        norm = self._SNIP_LANGS.get((lang or "").lower())
        if not norm:
            return {"ok": True, "lang": lang or "", "count": 0,
                    "snippets": []}
        from . import snippets2
        pack = dict(snippets2.default_pack(norm))
        try:
            user = snippets2.SnippetEngine._load_user()
            if isinstance(user, dict):
                pack.update(user.get(norm, {}))
        except Exception:  # noqa: BLE001 — user file must never 500
            pass
        ordered = [{"prefix": p, "body": b}
                   for p, b in sorted(pack.items())]
        return {"ok": True, "lang": norm, "count": len(ordered),
                "snippets": ordered}

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
            self.post(_run)
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
        self.post(_open)
        return {"opened": path}, None

    def close_path(self, path):
        """Close a tab in the desktop app (wave 7: the web face can
        close tabs too — the desktop tab bar stays the single source
        of truth). Refuses dirty buffers so nothing is ever lost."""
        real = self._sandbox(path)
        if real is None:
            return None, "path escapes the workspace"
        buffers = getattr(self.app, "_buffers", {})
        key = real if real in buffers else next(
            (k for k in buffers if self._same_file(k, real)), None)
        if key is None:
            return None, "not open"
        if buffers[key].get("dirty"):
            return None, "unsaved changes — save first (Ctrl+S)"

        def _close():
            try:
                self.app.close_tab(key)
            except Exception:  # noqa: BLE001 — a dead tab dies alone
                pass
        self.post(_close)
        return {"closed": path}, None

    @staticmethod
    def _same_file(a, b):
        try:
            return os.path.realpath(a) == os.path.realpath(b)
        except Exception:  # noqa: BLE001 — fall back to the literal
            return a == b

    # ---- workspace switching (wave 11: web parity for the desktop's
    #      Open Workspace dialog — the desktop stays the single truth) --
    def workspaces(self):
        """Recent workspaces (+ the current one) for the web switcher."""
        from . import projects
        cur = getattr(self.app, "project_dir", "") or ""
        items = []
        try:
            items = projects.list_recent(self.app.config)
        except Exception:  # noqa: BLE001 — a broken registry ≠ a 500
            items = []
        if cur and not any(i.get("path") == cur for i in items):
            try:
                meta = projects.read_project_meta(cur)
            except Exception:  # noqa: BLE001
                meta = {"name": os.path.basename(cur) or cur,
                        "kind": "empty"}
            items.insert(0, {"path": cur, "kind": meta["kind"],
                             "name": meta["name"], "opened": ""})
        for item in items:
            item["current"] = (item.get("path") == cur)
        return {"ok": True, "current": cur, "workspaces": items[:9]}

    def _seed_token(self, ws):
        """(Re)write the bridge token + local excludes into `ws` so an
        Electron shell pointed at the NEW workspace still authenticates."""
        try:
            dxn1_dir = os.path.join(ws, ".dxn1")
            os.makedirs(dxn1_dir, exist_ok=True)
            tok_path = os.path.join(dxn1_dir, "bridge_token")
            with open(tok_path, "w", encoding="utf-8") as fh:
                fh.write(self.token)
            try:
                os.chmod(tok_path, 0o600)
            except OSError:  # noqa: BLE001
                pass
            self._exclude_dxn1(ws)
        except OSError:  # noqa: BLE001 — read-only workspace: bridge
            pass         # stays up, the token file just doesn't move

    def workspace_set(self, path):
        """Switch the studio to another workspace from the web face.

        Same pipeline as the desktop's Open Workspace dialog (recents,
        sidebar, agent jail, terminal log — everything). Refuses while
        ANY open buffer has unsaved changes: nothing is ever lost.
        """
        from . import projects
        path = str(path or "").strip()
        if not path:
            return None, "path required"
        cand = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(cand):
            return None, "not a directory: " + path
        buffers = getattr(self.app, "_buffers", {})
        dirty = [k for k, b in buffers.items() if b.get("dirty")]
        if dirty:
            return None, ("unsaved changes in %d file(s) — save first"
                          % len(dirty))
        try:
            meta = projects.read_project_meta(cand)
        except Exception:  # noqa: BLE001 — switch must never 500
            meta = {"name": os.path.basename(cand) or cand,
                    "kind": "empty"}
        if cand == (getattr(self.app, "project_dir", "") or ""):
            return {"workspace": cand, "name": meta["name"],
                    "kind": meta["kind"], "unchanged": True}, None

        def _switch():
            app = self.app
            # close every open tab first: the new workspace must not
            # inherit dead tabs whose sandboxed paths would escape
            for key in list(getattr(app, "_buffers", {}).keys()):
                try:
                    app.close_tab(key)
                except Exception:  # noqa: BLE001 — a dead tab dies alone
                    pass
            self._seed_token(cand)
            try:
                app._set_workspace(cand, meta["kind"])
            except Exception:  # noqa: BLE001 — never kill the desktop
                pass
        self.post(_switch)
        self._engine_obj = None   # file ops rebind to the new workspace
        return {"workspace": cand, "name": meta["name"],
                "kind": meta["kind"]}, None

    # ---- file ops (reuse the TESTED stdio engine: bridge.Bridge) ------
    def _engine(self):
        from .bridge import Bridge
        # getattr (not hasattr): workspace_set resets this to None on
        # every switch — a None cache must rebuild against the NEW
        # workspace, not come back as the engine itself
        if getattr(self, "_engine_obj", None) is None:
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
        self.post(_run)
        return {"ran": True}, None

    def agent_send(self, message):
        """Route a user message into the agents panel (the same
        single entry point the desktop input uses)."""
        text = str(message or "").strip()
        if not text:
            return None, "message required"
        if len(text) > 8000:
            return None, "message too long (8000 char max)"
        panel = getattr(self.app, "agent_panel", None)
        if panel is None:
            return None, "agents panel unavailable"

        def _send():
            try:
                panel.route(text)
            except Exception:  # noqa: BLE001
                pass
        self.post(_send)
        return {"queued": True}, None

    # ---- diff + terminal input (wave 6) -------------------------------
    def git_diff(self):
        """Unified diff of the working tree vs HEAD (capped)."""
        out, err = self._git("diff", "HEAD")
        if err is not None:
            return None, err
        if len(out) > 64 * 1024:
            out = out[:64 * 1024] + "\n… diff truncated at 64 KB\n"
        return {"diff": out}, None

    def term_command(self, command):
        """Run a terminal command exactly as if typed in the desktop
        terminal (history, log, on_command — all on the Tk loop)."""
        cmd = str(command or "").strip()
        if not cmd:
            return None, "command required"
        if len(cmd) > 2000:
            return None, "command too long (2000 char max)"

        def _run():
            try:
                t = self.app.terminal
                t.history.append(cmd)
                t.history_pos = None
                t.log(cmd)
                if t.on_command:
                    t.on_command(cmd)
            except Exception:  # noqa: BLE001 — never crash the IDE
                pass
        self.post(_run)
        return {"queued": True}, None

    # ---- settings (wave 2: the web face can drive config) -------------
    _CONFIG_KEYS = ("theme", "accent", "word_wrap", "auto_save",
                    "editor_font_size", "terminal_font_size")

    def config_get(self):
        out = {"app": "DXN1 STUDIO", "version": _version()}
        try:
            for key in self._CONFIG_KEYS:
                out[key] = self.app.config.get(key)
        except Exception:  # noqa: BLE001
            pass
        from .theme import ACCENTS
        out["accents"] = {name: spec["label"]
                          for name, spec in ACCENTS.items()}
        return out

    def config_set(self, body):
        from .theme import ACCENTS
        applied = {}
        if not isinstance(body, dict):
            return None, "body must be an object"
        for key, val in body.items():
            if key not in self._CONFIG_KEYS:
                return None, f"setting not exposed: {key}"
            if key == "theme" and val not in ("dark", "light"):
                return None, "theme must be dark or light"
            if key == "accent" and val not in ACCENTS:
                return None, f"accent must be one of: " \
                             f"{', '.join(ACCENTS)}"
            if key in ("word_wrap", "auto_save"):
                val = bool(val)
            if key in ("editor_font_size", "terminal_font_size"):
                try:
                    val = int(val)
                except (TypeError, ValueError):
                    return None, f"{key} must be an integer"
            try:
                self.app.config.set(key, val, save=True)
            except Exception as exc:  # noqa: BLE001
                return None, str(exc)
            applied[key] = val
            # live accent re-colour: the web face polls theme tokens,
            # so the renderer follows instantly (the Tk face re-reads
            # on its normal restart flow)
            if key == "accent":
                try:
                    self.app.theme._a = ACCENTS[val]
                except Exception:  # noqa: BLE001
                    pass
        return {"applied": applied, "config": self.config_get()}, None

    # ---- git surface (wave 3: status + the chip-menu verbs) -----------
    def _git(self, *args):
        """Run a read-only git command in the workspace."""
        import subprocess
        try:
            proc = subprocess.run(
                ["git", "-C", getattr(self.app, "project_dir", None)
                 or os.getcwd(), *args],
                capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, str(exc)
        if proc.returncode != 0:
            return None, proc.stderr.strip() or "git failed"
        return proc.stdout, None

    @staticmethod
    def _exclude_dxn1(ws):
        """Add .dxn1/ to the repo's local excludes (idempotent)."""
        git_info = os.path.join(ws, ".git", "info")
        if not os.path.isdir(git_info):
            return
        excl = os.path.join(git_info, "exclude")
        try:
            existing = ""
            if os.path.isfile(excl):
                with open(excl, encoding="utf-8") as fh:
                    existing = fh.read()
            if ".dxn1/" not in existing:
                with open(excl, "a", encoding="utf-8") as fh:
                    if existing and not existing.endswith("\n"):
                        fh.write("\n")
                    fh.write(".dxn1/\n")
        except OSError:  # noqa: BLE001
            pass

    def git_status(self):
        # keep internal state OUT of git status/commits (.dxn1 holds
        # the bridge token — a secret — plus cache files): local-only
        # via .git/info/exclude, self-healing when a repo appears later
        self._exclude_dxn1(getattr(self.app, "project_dir", None)
                           or os.getcwd())
        out, err = self._git("status", "--porcelain", "-b")
        if err is not None:
            return None, err
        lines = out.splitlines()
        branch = lines[0][3:] if lines and lines[0].startswith("## ") \
            else "?"
        # unborn HEAD: "## No commits yet on master" → clean name
        if branch.startswith("No commits yet on "):
            branch = branch.split("No commits yet on ", 1)[1].strip() \
                + " (fresh)"
        files = [ln[3:] for ln in lines[1:] if ln.strip()]
        out_b, _err_b = self._git("branch", "--format=%(refname:short)")
        branches = (out_b.splitlines() if out_b else [])[:40]
        log, err = self._git("log", "--oneline", "-8")
        commits = log.splitlines() if log else []
        return {"branch": branch, "dirty": len(files),
                "files": files[:40], "commits": commits,
                "branches": branches}, None

    def git_action(self, body):
        action = str(body.get("action") or "")
        if action == "commit":
            msg = str(body.get("message") or "").strip()
            if not msg:
                return None, "commit needs a message"
            self._git("add", "-A")
            out, err = self._git("commit", "-m", msg)
            if err is not None:
                return None, err.splitlines()[-1] if err else "commit failed"
            return {"done": "commit", "detail": out.strip()
                    .splitlines()[-1] if out.strip() else msg}, None
        if action in ("push", "pull"):
            out, err = self._git(action)
            if err is not None:
                return None, err.splitlines()[-1] if err else \
                    f"{action} failed"
            return {"done": action, "detail": out.strip()[:400]}, None
        if action == "checkout":
            return self.git_checkout(body)
        return None, f"action not allowed: {action}"

    # ---- branches (wave 9: switch branches from the web face) ---------
    _BRANCH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")

    def git_checkout(self, body):
        """Switch branches — guarded three ways: strict name syntax
        (no option injection, no ..), a clean working tree, and an
        explicit git failure surface. Nothing is force-dropped."""
        branch = str(body.get("branch") or "").strip()
        if not branch or not self._BRANCH_RE.fullmatch(branch) \
                or ".." in branch or branch.endswith("/"):
            return None, "bad branch name"
        status, err = self.git_status()
        if err is not None:
            return None, err
        if status.get("dirty"):
            return None, (f"working tree has {status['dirty']} changed "
                          "file(s) — commit or stash first")
        out, err = self._git("checkout", branch)
        if err is not None:
            return None, err.splitlines()[-1] if err else \
                "checkout failed"
        return {"done": "checkout", "branch": branch,
                "detail": out.strip()[:200]}, None

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
        elif route == "/api/files":
            self._send_json({"ok": True, "files": self.state.files()})
        elif route == "/api/snippets":
            self._send_json(
                self.state.snippets((q.get("lang") or [""])[0]))
        elif route == "/api/diff":
            payload, err = self.state.git_diff()
            self._send_json(
                {"ok": err is None, **(payload or {}),
                 **({"error": err} if err else {})},
                200 if err is None else 400)
        elif route == "/api/config":
            self._send_json({"ok": True, "config": self.state.config_get()})
        elif route == "/api/git":
            payload, err = self.state.git_status()
            self._send_json(
                {"ok": err is None, **(payload or {}),
                 **({"error": err} if err else {})},
                200 if err is None else 400)
        elif route == "/api/workspaces":
            self._send_json(self.state.workspaces())
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
        elif u.path == "/api/close":
            payload, err = self.state.close_path(
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
        elif u.path == "/api/config":
            payload, err = self.state.config_set(body)
        elif u.path == "/api/workspace":
            payload, err = self.state.workspace_set(
                str(body.get("path") or ""))
        elif u.path == "/api/git":
            payload, err = self.state.git_action(body)
        elif u.path == "/api/run":
            payload, err = self.state.run_project()
        elif u.path == "/api/agent":
            payload, err = self.state.agent_send(
                str(body.get("message") or ""))
        elif u.path == "/api/term":
            payload, err = self.state.term_command(
                str(body.get("command") or ""))
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
        # keep the token OUT of git status/commits (it is a secret and
        # pure noise): .git/info/exclude is local-only by design
        BridgeState._exclude_dxn1(ws)
    except OSError:  # noqa: BLE001
        tok_path = None
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()
    # the pump MUST be scheduled from the Tk main loop (we are on it —
    # the palette command calls start_bridge)
    try:
        state.start_pump()
    except Exception:  # noqa: BLE001 — headless/tests without a loop
        pass
    return server, url, state.token
