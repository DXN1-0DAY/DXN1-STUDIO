"""DXN1 STUDIO — workspace sandbox + agent tool loop.

Security model
--------------
The agent can only ever touch paths that resolve *inside* the open
workspace folder. ``WorkspaceSandbox.resolve`` rejects absolute paths,
``..`` traversal, symlink escapes (checked against ``os.path.realpath``)
and sensitive dot-directories like ``.git``. Read-only tools are free;
*every* write and every command goes through an approval callback that
the UI wires to its Accept/Decline cards. Full-access mode auto-approves
— except catastrophic commands (``rm -rf /``, ``sudo``, pipe-to-shell,
raw disk writes…), which always stop and ask, no matter what.

Tool protocol (text-based so it works on free/local models that lack
native function calling)::

    <tool name="write_file">{"path": "app.py", "content": "..."}</tool>
    <done>one-line summary</done>
"""

import difflib
import json
import os
import re
import subprocess

# ------------------------------------------------------------- dangerous ops
DANGEROUS_PATTERNS = [
    (r"\brm\s+(-[a-zA-Z]*\s+)*-[a-zA-Z]*[rfRF][a-zA-Z]*\s+(/|~|\$HOME|\*)",
     "recursive delete of a system path / wildcard"),
    (r"(^|\s|/)sudo(\s|$)", "sudo"),
    (r"\bmkfs(\.\w+)?\b", "format a filesystem"),
    (r"\bdd\b\s+if=", "raw disk write"),
    (r">\s*/dev/sd[a-z]", "raw disk write"),
    (r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b", "pipe-to-shell download"),
    (r"\bgit\s+push\b.*(--force|-f)\b", "forced git push"),
    (r"\bchmod\s+(-R\s+)?777\s+/(?!.*dxn1)", "chmod 777 on filesystem root"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "shutting the machine down"),
    (r"\bkill(all)?\s+-?9?\s+1\b", "killing a system process"),
]

BANNED_DIRS = {".git", ".dxn1-studio", ".ssh"}
SKIP_TREE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
                  ".dxn1-studio", "dist", "build", ".mypy_cache"}

MAX_READ_CHARS = 16000
MAX_WRITE_CHARS = 200000
MAX_TREE_ENTRIES = 300
MAX_TREE_DEPTH = 4
MAX_CMD_OUTPUT = 4000
MAX_CMD_SECONDS = 60


class SandboxError(Exception):
    """A tool tried to do something outside its lane."""


class WorkspaceSandbox:
    """Hard boundary around one workspace folder."""

    def __init__(self, root):
        self.root = os.path.realpath(os.path.abspath(root))
        if not os.path.isdir(self.root):
            raise SandboxError(f"workspace vanished: {self.root}")

    # -------------------------------------------------------------- paths
    def resolve(self, rel):
        """Map a workspace-relative path to an absolute, jailed path."""
        rel = str(rel or "").strip().replace("\\", "/")
        if os.path.splitdrive(rel)[0] or rel.startswith("/"):
            raise SandboxError("absolute paths are not allowed — use "
                               "workspace-relative paths")
        parts = []
        for part in rel.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                raise SandboxError("paths may not climb out of the workspace")
            parts.append(part)
        if not parts:
            raise SandboxError("empty path")
        if parts[0] in BANNED_DIRS or any(p in BANNED_DIRS for p in parts):
            raise SandboxError(f"'{'/'.join(parts)}' is off-limits to the agent")
        abs_path = os.path.join(self.root, *parts)
        real_root = self.root
        real = os.path.realpath(abs_path)
        if real != real_root and not real.startswith(real_root + os.sep):
            raise SandboxError("resolved path escapes the workspace (symlink?)")
        return abs_path

    def rel(self, abs_path):
        try:
            return os.path.relpath(abs_path, self.root)
        except ValueError:
            return abs_path

    # -------------------------------------------------------------- tools
    def list_tree(self):
        """Compact file listing the model can reason over."""
        lines = []
        base_depth = self.root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_TREE_DIRS
                                 and not d.startswith("."))
            depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
            if depth >= MAX_TREE_DEPTH:
                dirnames[:] = []
                continue
            indent = "  " * depth
            rel_dir = self.rel(dirpath)
            if depth > 0:
                lines.append(f"{indent}{os.path.basename(rel_dir)}/")
            for fn in sorted(filenames):
                if len(lines) >= MAX_TREE_ENTRIES:
                    lines.append("  … (listing truncated)")
                    return "\n".join(lines)
                try:
                    size = os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    size = 0
                lines.append(f"{indent}  {fn} ({size} B)")
        return "\n".join(lines) or "(the workspace is empty)"

    def read_file(self, rel):
        path = self.resolve(rel)
        if not os.path.isfile(path):
            raise SandboxError(f"no such file in the workspace: {rel}")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(MAX_READ_CHARS + 1)
        if len(content) > MAX_READ_CHARS:
            content = content[:MAX_READ_CHARS] + \
                "\n… (truncated — read again in chunks if needed)"
        return content

    def read_for_diff(self, abs_path):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""

    def write_file(self, rel, content):
        path = self.resolve(rel)
        content = str(content or "")
        if len(content) > MAX_WRITE_CHARS:
            raise SandboxError("content too large for one write")
        existed = os.path.isfile(path)
        os.makedirs(os.path.dirname(path) or self.root, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path, existed

    @staticmethod
    def check_command(cmd):
        """Return (dangerous, reason). Dangerous ⇒ always ask, even in
        full-access mode."""
        for pattern, reason in DANGEROUS_PATTERNS:
            if re.search(pattern, cmd):
                return True, reason
        return False, ""


# ------------------------------------------------------------- diff helper
def make_diff(old, new, path):
    diff = list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""))
    if not diff:
        return "(no textual changes)"
    if len(diff) > 60:
        diff = diff[:60] + ["… diff truncated …"]
    return "\n".join(diff)


def head_preview(text, limit=600):
    text = str(text or "").strip()
    return text[:limit] + ("…" if len(text) > limit else "") or "(empty)"


# ------------------------------------------------------------ tool protocol
TOOL_RE = re.compile(r"<tool\s+name\s*=\s*\"([a-z_]+)\"\s*>(.*?)</tool\s*>",
                     re.S)
DONE_RE = re.compile(r"<done>(.*?)</done>", re.S)


def parse_tools(text):
    """Return (clean_reply, [(tool_name, args_dict), …]). Tolerant of
    malformed JSON — the model gets a readable error as the tool result."""
    tools = []

    def _grab(match):
        raw = match.group(2).strip()
        args = {}
        if raw:
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                b1, b2 = raw.find("{"), raw.rfind("}")
                if 0 <= b1 < b2:
                    try:
                        args = json.loads(raw[b1:b2 + 1])
                    except json.JSONDecodeError:
                        args = {}
        if not isinstance(args, dict):
            args = {"_raw": str(args)}
        tools.append((match.group(1), args))
        return ""

    clean = TOOL_RE.sub(_grab, text)
    return clean.strip(), tools


# ------------------------------------------------------- system-prompt styles
# Short style blocks spliced into the base persona. "custom" means the user's
# extra prompt replaces the personality section entirely (tools stay locked).
PROMPT_STYLES = {
    "default": {
        "label": "Default",
        "description": "Balanced copilot — explains briefly, codes cleanly.",
        "block": "Tone: friendly and practical. Explain decisions in one or "
                 "two sentences before acting; keep answers tight.",
    },
    "concise": {
        "label": "Concise",
        "description": "Minimal talk, maximum doing.",
        "block": "Tone: telegraphic. No filler, no pleasantries, no restating "
                 "the task. Emit tools immediately; one line per action.",
    },
    "senior": {
        "label": "Senior dev",
        "description": "Careful reviewer — edge cases, tests, small steps.",
        "block": "Tone: senior engineer. Prefer small, reviewable changes; "
                 "mention edge cases and error handling; add or suggest tests "
                 "when behaviour changes; flag risky commands before running.",
    },
    "custom": {
        "label": "Custom",
        "description": "Your extra prompt fully defines the personality.",
        "block": "",
    },
}


def build_system_prompt(sandbox, agent_name="DXN1 Agents", extra="",
                        style="default"):
    root = sandbox.root
    spec = PROMPT_STYLES.get(style) or PROMPT_STYLES["default"]
    prompt = f"""You are {agent_name}, the built-in coding agent of DXN1 STUDIO.
You are helping the user inside their open workspace.

HARD BOUNDARIES (non-negotiable):
- You can only see and touch files inside the workspace root:
  {root}
- Anything outside that folder is unreachable. Never promise to edit,
  read or run things elsewhere. Never ask the user to move files out
  of the workspace so you can reach them.
- You never handle secrets: if a file looks like keys/tokens, don't
  repeat its contents.

TOOLS — act by emitting tool calls, exactly one JSON object each:
<tool name="list_files">{{}}</tool>
<tool name="read_file">{{"path": "app.py"}}</tool>
<tool name="write_file">{{"path": "app.py", "content": "…full file…"}}</tool>
<tool name="edit_file">{{"path": "app.py", "find": "exact text", "replace": "new text"}}</tool>
<tool name="run_command">{{"command": "python main.py"}}</tool>

Tool rules:
- write_file creates or overwrites with the FULL content.
- edit_file is surgical: "find" must match exactly once; prefer it for
  small changes, write_file for new files or big rewrites.
- After each tool you receive a TOOL RESULT message; keep working until
  the task is complete, then finish with: <done>one-line summary</done>
- Writes and commands need the user's approval unless they enabled full
  access. If something is declined, adapt — don't retry the same thing.
- Keep prose short. Put code in files, not in chat, unless asked.

{{style_block}}

Current workspace listing (may be stale — use list_files to refresh):
{sandbox.list_tree()}"""
    if spec["block"] and style != "custom":
        prompt = prompt.replace("{style_block}", spec["block"])
    elif style == "custom" and extra:
        prompt = prompt.replace(
            "{style_block}",
            "PERSONALITY — defined entirely by the user:\n" + extra)
    else:
        prompt = prompt.replace("{style_block}",
                                PROMPT_STYLES["default"]["block"])
    if extra and style != "custom":
        prompt += "\n\nEXTRA PERSONALITY / INSTRUCTIONS FROM THE USER:\n" + extra
    return prompt


# ------------------------------------------------------------------ engine
class AgentEngine:
    """Tool loop: chat → parse tools → sandbox-gated execution → repeat."""

    def __init__(self, backend, sandbox, config, name="DXN1 Agents",
                 emit=None, approve=None, execute_command=None,
                 on_written=None):
        self.backend = backend
        self.sandbox = sandbox
        self.config = config
        self.name = name
        self.emit = emit or (lambda text: None)
        self.approve = approve or (lambda *a, **k: True)
        self.execute_command = execute_command or (lambda cmd: (1, "(no runner)"))
        self.on_written = on_written or (lambda path: None)
        self.stop_flag = False
        self.busy = False
        self.style = (config.get("agents_prompt_preset") or "default") \
            if config else "default"
        self.system_prompt = build_system_prompt(
            sandbox, name,
            (config.get("agents_system_prompt") or "").strip(),
            style=self.style)
        self.history = []
        self.tokens_used = 0      # total tokens reported by the backend
        self.steps_used = 0       # tool-loop turns taken this session

    # ------------------------------------------------------------ controls
    def stop(self):
        self.stop_flag = True

    def reset(self):
        self.history = []

    def _trim(self):
        # keep the last 20 exchanges worth of context
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def _messages(self):
        return [{"role": "system", "content": self.system_prompt}] + self.history

    # ----------------------------------------------------------- main loop
    def run(self, user_text):
        self.busy = True
        self.stop_flag = False
        try:
            self.history.append({"role": "user", "content": user_text})
            max_steps = max(2, int(self.config.get("agents_max_steps", 12) or 12))
            for _ in range(max_steps):
                if self.stop_flag:
                    self.emit("Stopped.")
                    return
                try:
                    reply = self.backend.chat(self._messages())
                except Exception as exc:  # BackendError and friends
                    self.emit(f"⚠ Backend trouble: {exc}\n\n"
                              f"Falling back to my built-in offline skills — "
                              f"try again, or check Settings → DXN1 Agents.")
                    return
                usage = getattr(self.backend, "last_usage", None)
                if isinstance(usage, dict):
                    self.tokens_used += int(usage.get("total_tokens") or 0)
                clean, tools = parse_tools(reply)
                if clean:
                    self.emit(clean)
                self.history.append({"role": "assistant", "content": reply})
                if not tools:
                    return
                results = []
                done_summary = ""
                m = DONE_RE.search(reply)
                if m:
                    done_summary = m.group(1).strip()
                for tool_name, args in tools:
                    if self.stop_flag:
                        self.emit("Stopped mid-task.")
                        return
                    outcome = self._exec_tool(tool_name, args)
                    results.append(f"TOOL RESULT ({tool_name}): {outcome}")
                self._trim()
                self.history.append({"role": "user",
                                     "content": "\n\n".join(results)})
                if done_summary:
                    return
            self.emit("Reached my step limit for this turn — say \"continue\" "
                      "if you want me to keep going.")
        finally:
            self.busy = False

    # ---------------------------------------------------------- tool exec
    def _exec_tool(self, name, args):
        sb = self.sandbox
        self.steps_used += 1
        try:
            if name == "list_files":
                return sb.list_tree()

            if name == "read_file":
                return sb.read_file(args.get("path", ""))

            if name == "write_file":
                return self._tool_write(args)

            if name == "edit_file":
                return self._tool_edit(args)

            if name == "run_command":
                return self._tool_command(args)

            return f"error: unknown tool '{name}'"
        except SandboxError as exc:
            return f"error: {exc}"
        except Exception as exc:  # noqa: BLE001 — never kill the loop
            return f"error: {exc.__class__.__name__}: {exc}"

    def _tool_write(self, args):
        rel = str(args.get("path") or "").strip()
        content = str(args.get("content") or "")
        if not rel:
            return "error: write_file needs a \"path\""
        path = self.sandbox.resolve(rel)          # jail check BEFORE preview
        old = self.sandbox.read_for_diff(path) if os.path.isfile(path) else ""
        existed = os.path.isfile(path)
        verb = "Overwrite" if existed else "Create"
        preview = make_diff(old, content, rel) if existed else head_preview(content)
        ok = self.approve(
            "edit", f"{verb} {rel}",
            ("A file changes" if existed else "A new file lands") +
            " inside your workspace.", preview)
        if not ok:
            return f"user declined the write to {rel}"
        written, _ = self.sandbox.write_file(rel, content)
        self.on_written(written)
        return f"ok — wrote {rel} ({len(content)} chars)"

    def _tool_edit(self, args):
        rel = str(args.get("path") or "").strip()
        find = str(args.get("find") or "")
        replace = str(args.get("replace") or "")
        if not rel or not find:
            return "error: edit_file needs \"path\" and \"find\""
        path = self.sandbox.resolve(rel)
        if not os.path.isfile(path):
            return f"error: {rel} doesn't exist yet — use write_file"
        old = self.sandbox.read_for_diff(path)
        count = old.count(find)
        if count == 0:
            return ("error: \"find\" text not found — re-read the file and "
                    "match it exactly")
        if count > 1:
            return (f"error: \"find\" matches {count} times — add surrounding "
                    f"context so it's unique")
        new = old.replace(find, replace, 1)
        ok = self.approve("edit", f"Edit {rel}",
                          "A surgical find/replace inside your workspace.",
                          make_diff(old, new, rel))
        if not ok:
            return f"user declined the edit to {rel}"
        self.sandbox.write_file(rel, new)
        self.on_written(path)
        return f"ok — edited {rel}"

    def _tool_command(self, args):
        cmd = str(args.get("command") or "").strip()
        if not cmd:
            return "error: run_command needs a \"command\""
        dangerous, reason = WorkspaceSandbox.check_command(cmd)
        detail = f"Runs inside {self.sandbox.rel(self.sandbox.root) or 'the workspace'}."
        if dangerous:
            detail += f" ⚠ flagged: {reason} — needs an explicit yes even in full access."
        ok = self.approve("command", cmd, detail, f"$ {cmd}", danger=dangerous)
        if not ok:
            return f"user declined the command: {cmd}"
        code, output = self.execute_command(cmd)
        out = output[:MAX_CMD_OUTPUT] or "(no output)"
        return f"exit code {code}\n{out}"


# ------------------------------------------------------- offline test double
class FakeBackend:
    """Deterministic scripted backend for CI / --smoke-test."""

    label = "FakeBackend"

    def __init__(self, script):
        self.script = list(script)
        self.i = 0
        self.calls = 0

    @property
    def display(self):
        return "FakeBackend"

    def chat(self, messages, max_tokens=2048, temperature=0.3):
        self.calls += 1
        resp = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        return resp
