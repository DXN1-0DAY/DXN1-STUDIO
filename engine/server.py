"""DXN1 STUDIO 3 — the Python engine (stdio JSON bridge).

Protocol (one JSON object per line):
    request  {"id": 1, "cmd": "read", "args": {"path": "a.py"}}
    reply    {"id": 1, "ok": true,  "result": ...}
             {"id": 1, "ok": false, "error": "why"}

The server NEVER raises: a bad line gets an honest error reply and
the loop continues. Path arguments are workspace-relative and every
resolve refuses to escape the workspace. Writes are atomic
(tmp + rename). These are the DS2 lessons, rebuilt clean for DS3.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MAX_READ = 8 * 1024 * 1024      # 8 MB read ceiling
MAX_TREE = 20000                # tree entry limit
SKIP_NAMES = {".git", "__pycache__", "node_modules", ".dxn1"}


class EngineError(Exception):
    """An honest, user-presentable engine error."""


def _guess_kind(name, is_dir):
    if is_dir:
        return "dir"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return ext or "file"


class Engine:
    def __init__(self, workspace):
        self.set_workspace(workspace)

    # ------------------------------------------------------------ paths
    def set_workspace(self, path):
        path = os.path.abspath(os.path.expanduser(str(path or ".")))
        if not os.path.isdir(path):
            raise EngineError(f"not a directory: {path}")
        self.workspace = path

    def resolve(self, rel):
        rel = str(rel or "").replace("\\", "/").lstrip("/")
        if rel in ("", "."):
            return self.workspace
        target = os.path.abspath(os.path.join(self.workspace, rel))
        root = self.workspace.rstrip(os.sep) + os.sep
        if target != self.workspace and not target.startswith(root):
            raise EngineError("path escapes the workspace")
        return target

    # ----------------------------------------------------------- reads
    def cmd_hello(self, args):
        return {"app": "DXN1 STUDIO 3", "engine": "python",
                "version": __import__("engine").__version__,
                "workspace": self.workspace}

    def cmd_tree(self, args):
        depth = max(1, min(int(args.get("depth") or 2), 6))
        out = []

        def walk(base, level):
            if level > depth or len(out) >= MAX_TREE:
                return
            try:
                entries = sorted(os.scandir(base),
                                 key=lambda e: (not e.is_dir(),
                                                e.name.lower()))
            except OSError:
                return
            for entry in entries:
                if entry.name in SKIP_NAMES or entry.name.startswith("."):
                    continue
                is_dir = entry.is_dir()
                out.append({"name": entry.name,
                            "path": os.path.relpath(entry.path,
                                                    self.workspace)
                                        .replace(os.sep, "/"),
                            "dir": is_dir})
                if len(out) >= MAX_TREE:
                    out.append({"truncated": True})
                    return
                if is_dir:
                    walk(entry.path, level + 1)

        walk(self.workspace, 1)
        return {"tree": out, "count": len(out)}

    def cmd_read(self, args):
        path = self.resolve(args.get("path"))
        if os.path.isdir(path):
            raise EngineError("is a directory")
        try:
            size = os.path.getsize(path)
            if size > MAX_READ:
                raise EngineError(
                    f"file too large ({size} > {MAX_READ} bytes)")
            with open(path, "r", encoding="utf-8",
                      errors="replace") as fh:
                return {"path": str(args.get("path")), "content": fh.read()}
        except OSError as exc:
            raise EngineError(str(exc))

    def cmd_stat(self, args):
        path = self.resolve(args.get("path"))
        if not os.path.exists(path):
            return {"exists": False}
        return {"exists": True, "dir": os.path.isdir(path),
                "size": os.path.getsize(path)}

    # ---------------------------------------------------------- writes
    def cmd_write(self, args):
        path = self.resolve(args.get("path"))
        if os.path.isdir(path):
            raise EngineError("is a directory")
        content = str(args.get("content") or "")
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".",
                                       prefix=".dxn1-tmp-")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp, path)          # atomic on the same volume
        except OSError as exc:
            raise EngineError(str(exc))
        return {"written": str(args.get("path")),
                "bytes": len(content.encode("utf-8"))}

    def cmd_mkdir(self, args):
        path = self.resolve(args.get("path"))
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as exc:
            raise EngineError(str(exc))
        return {"made": str(args.get("path"))}

    def cmd_rename(self, args):
        src = self.resolve(args.get("from"))
        dst = self.resolve(args.get("to"))
        if not os.path.exists(src):
            raise EngineError("no such file or directory")
        if os.path.abspath(src) == self.workspace or \
                os.path.abspath(dst) == self.workspace:
            raise EngineError("refusing to rename the workspace root")
        if os.path.exists(dst):
            raise EngineError("destination already exists")
        try:
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            os.rename(src, dst)
        except OSError as exc:
            raise EngineError(str(exc))
        return {"renamed": str(args.get("from")), "to": str(args.get("to"))}

    def cmd_delete(self, args):
        path = self.resolve(args.get("path"))
        if os.path.abspath(path) == self.workspace:
            raise EngineError("refusing to delete the workspace root")
        if not os.path.exists(path):
            raise EngineError("no such file or directory")
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as exc:
            raise EngineError(str(exc))
        return {"deleted": str(args.get("path"))}

    # ---------------------------------------------------------- scenes
    def cmd_scene_get(self, args):
        """Read a scene file, parsed + validated. Scenes live anywhere
        in the workspace but conventionally under scenes/."""
        data = self.cmd_read(args)
        import json
        try:
            scene = json.loads(data["content"])
        except json.JSONDecodeError as exc:
            raise EngineError(f"scene is not valid JSON: {exc}")
        if not isinstance(scene, dict) or "entities" not in scene:
            raise EngineError("scene needs an 'entities' list")
        return {"path": data["path"], "scene": scene}

    def cmd_scene_save(self, args):
        scene = args.get("scene")
        if not isinstance(scene, dict) or not isinstance(
                scene.get("entities"), list):
            raise EngineError("scene needs an 'entities' list")
        import json
        path = str(args.get("path") or "")
        if not path:
            raise EngineError("path required")
        self.cmd_write({"path": path,
                        "content": json.dumps(scene, indent=2)})
        return {"saved": path}

    # ------------------------------------------------------------- git
    def _git(self, *argv):
        """Run git in the workspace; honest errors, never raises past us."""
        try:
            out = subprocess.run(
                ["git", "-C", self.workspace, *argv],
                capture_output=True, text=True, timeout=20)
        except FileNotFoundError:
            raise EngineError("git is not installed")
        except subprocess.TimeoutExpired:
            raise EngineError("git timed out")
        if out.returncode != 0:
            msg = (out.stderr or out.stdout or "git failed").strip()
            raise EngineError(msg.splitlines()[-1] if msg else "git failed")
        return out.stdout

    def _git_repo(self):
        if not os.path.isdir(os.path.join(self.workspace, ".git")):
            raise EngineError("not a git repository")

    def cmd_git_status(self, args):
        self._git_repo()
        out = self._git("status", "--porcelain", "--branch")
        branch, ahead = "unknown", 0
        files = []
        for line in out.splitlines():
            if line.startswith("## "):
                head = line[3:]
                if head.startswith("No commits yet"):
                    branch = head.rsplit(" ", 1)[-1]   # "... on master"
                else:
                    branch = head.split("...", 1)[0].split(" ", 1)[0] \
                        or "unknown"
                m = re.search(r"\[ahead (\d+)", head)
                if m:
                    ahead = int(m.group(1))
                continue
            if not line.strip():
                continue
            xy, path = line[:2], line[3:]
            if " -> " in path:               # renames: show the new name
                path = path.split(" -> ", 1)[1]
            # effective status: staged X wins, else the worktree Y;
            # untracked (??) reads as "A" — a file about to be added,
            # same shape the demo filesystem speaks
            if xy == "??":
                status = "A"
            else:
                status = xy[0] if xy[0] not in (" ", "?") else (
                    xy[1] if xy[1] not in (" ", "?") else "?")
            files.append({"path": path, "x": status, "y": xy[1].strip() or "?"})
        return {"branch": branch, "ahead": ahead, "files": files,
                "clean": not files}

    def cmd_git_log(self, args):
        self._git_repo()
        out = self._git("log", "-n", "15",
                        "--pretty=format:%h%x1f%s%x1f%an%x1f%ar")
        commits = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\x1f")
            commits.append({"hash": parts[0], "subject": parts[1],
                            "author": parts[2] if len(parts) > 2 else "",
                            "when": parts[3] if len(parts) > 3 else ""})
        return {"commits": commits}

    def cmd_git_commit(self, args):
        self._git_repo()
        message = str(args.get("message") or "").strip()
        if not message:
            raise EngineError("commit message required")
        if len(message) > 400:
            raise EngineError("commit message too long (400 chars max)")
        self._git("add", "-A")
        out = self._git("commit", "-m", message)
        m = re.search(r"\[[^\]]+? ([0-9a-f]+)\]", out)
        return {"committed": m.group(1) if m else "ok", "message": message}

    def _has_head(self):
        try:
            self._git("rev-parse", "--verify", "--quiet", "HEAD")
            return True
        except EngineError:
            return False

    def cmd_git_branches(self, args):
        self._git_repo()
        out = self._git("branch", "--format=%(refname:short)%09%(HEAD)")
        branches = []
        current = "unknown"
        for line in out.splitlines():
            if not line.strip():
                continue
            name, _, mark = line.partition("\t")
            if mark.strip() == "*":
                current = name
            branches.append(name)
        return {"branches": branches, "current": current}

    def cmd_git_checkout(self, args):
        self._git_repo()
        name = str(args.get("name") or "").strip()
        if not name or not re.fullmatch(r"[\w./-]+", name) or name.startswith("-"):
            raise EngineError("invalid branch name")
        if len(name) > 80:
            raise EngineError("branch name too long")
        create = bool(args.get("create"))
        exists = name in self.cmd_git_branches({})["branches"]
        if create and exists:
            raise EngineError(f"branch already exists: {name}")
        if not create and not exists:
            raise EngineError(f"no such branch: {name}")
        out = self._git("checkout", "-b", name) if create \
            else self._git("checkout", name)
        branch = name
        m = re.search(r"Switched to (?:a new )?branch '([^']+)'", out)
        if m:
            branch = m.group(1)
        return {"branch": branch, "created": create}

    def cmd_git_diff(self, args):
        """Unified diff of one file vs HEAD. Untracked files come back
        as an all-added diff; clean files as zero hunks."""
        self._git_repo()
        path = str(args.get("path") or "")
        if not path:
            raise EngineError("path required")
        st = self.cmd_git_status({})
        entry = next((f for f in st["files"] if f["path"] == path), None)
        if entry is None:
            return {"path": path, "status": "clean", "hunks": []}
        if entry["x"] == "?" or not self._has_head():
            # untracked, or no commits yet: everything is an addition
            try:
                with open(self.resolve(path), encoding="utf-8",
                          errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError as exc:
                raise EngineError(str(exc))
            return {"path": path, "status": "added",
                    "hunks": [{"header": f"@@ -0,0 +1,{len(lines)} @@",
                               "lines": [{"t": "+", "s": ln}
                                          for ln in lines]}]}
        out = self._git("diff", "HEAD", "--no-color", "--unified=3", "--", path)
        hunks = []
        for line in out.splitlines():
            if line.startswith(("diff --git", "index ", "--- ", "+++ ")):
                continue
            if line.startswith("@@"):
                hunks.append({"header": line, "lines": []})
            elif hunks and line[:1] in ("+", "-", " "):
                hunks[-1]["lines"].append({"t": line[:1], "s": line[1:]})
        return {"path": path, "status": "modified", "hunks": hunks}

    # ----------------------------------------------------------- serve
    def handle(self, line):
        """One request line -> one reply dict. Never raises."""
        try:
            req = json.loads(line)
            if not isinstance(req, dict):
                raise EngineError("request must be a JSON object")
        except json.JSONDecodeError as exc:
            return {"id": None, "ok": False, "error": f"bad JSON: {exc}"}
        rid = req.get("id")
        cmd = str(req.get("cmd") or "")
        args = req.get("args") or {}
        if not isinstance(args, dict):
            return {"id": rid, "ok": False, "error": "args must be an object"}
        fn = getattr(self, f"cmd_{cmd}", None)
        if fn is None or not cmd.replace("_", "").isalnum():
            return {"id": rid, "ok": False, "error": f"unknown cmd: {cmd}"}
        try:
            return {"id": rid, "ok": True, "result": fn(args)}
        except EngineError as exc:
            return {"id": rid, "ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 — the loop must survive
            return {"id": rid, "ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def serve_forever(self, stdin=None, stdout=None):
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            reply = self.handle(line)
            try:
                stdout.write(json.dumps(reply) + "\n")
                stdout.flush()
            except (BrokenPipeError, ValueError):
                return   # the face went away — end quietly


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    workspace = argv[0] if argv else os.getcwd()
    try:
        eng = Engine(workspace)
    except EngineError as exc:
        print(json.dumps({"id": None, "ok": False, "error": str(exc)}))
        return 1
    eng.serve_forever()
    return 0
