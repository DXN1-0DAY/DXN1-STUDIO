"""DXN1 STUDIO — Environment Doctor.

One command, honest answers. The doctor inspects the Python runtime,
Tk, git, pip, Pillow, the studio's config file, the current workspace,
agent memory, disk space and the configured LLM backend — then reports
everything as colour-coded pass/warn/fail rows with fix-it hints.

Usable three ways:

* Command palette → ``Doctor — check my environment`` (GUI window)
* CLI: ``python3 -m dxn1_studio.doctor`` (plain-text report, exit code
  0 when healthy, 1 when any check fails, 2 when warnings only)
* Programmatically: :func:`run_checks` / :func:`format_report`

No network access, no writes — the doctor only reads.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time

from . import APP_NAME, APP_VERSION, APP_CHANNEL

# ------------------------------------------------------------------ model
OK, WARN, FAIL = "ok", "warn", "fail"

_ICONS = {OK: "✓", WARN: "!", FAIL: "✗"}
# colours resolved at window build time; text report uses the markers
_COLORS = {OK: "#3fb950", WARN: "#d29922", FAIL: "#f85149"}


class CheckResult:
    """One row of the doctor's report."""

    __slots__ = ("name", "status", "detail", "hint")

    def __init__(self, name, status, detail="", hint=""):
        self.name = name
        self.status = status if status in (OK, WARN, FAIL) else WARN
        self.detail = detail
        self.hint = hint

    @property
    def healthy(self):
        return self.status == OK


def _first_line(text):
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""


def _run(cmd, timeout=6):
    """(ok, first-output-line) for a quick subprocess probe."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode == 0, _first_line(proc.stdout or proc.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


# ------------------------------------------------------------------ checks
def check_python():
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 10):
        return CheckResult("Python", OK, ver)
    if v >= (3, 9):
        return CheckResult("Python", WARN, ver,
                           "works, but 3.10+ is recommended")
    return CheckResult("Python", FAIL, ver, "upgrade to Python 3.9+")


def check_tkinter():
    try:
        import tkinter  # noqa: F401
        try:
            root = tkinter.Tk()
            root.withdraw()
            root.destroy()
        except tkinter.TclError as exc:
            return CheckResult("Tkinter", WARN, f"no display ({exc})",
                               "fine for CI — set DISPLAY to use the GUI")
        return CheckResult("Tkinter", OK, f"Tk {tkinter.TkVersion}")
    except ImportError:
        return CheckResult("Tkinter", FAIL, "module missing",
                           "install python3-tk (Debian/Ubuntu) or the "
                           "python-tk package for your distro")


def check_git():
    path = shutil.which("git")
    if not path:
        return CheckResult("git", FAIL, "not found",
                           "install git — source control features need it")
    ok, ver = _run(["git", "--version"])
    return CheckResult("git", OK if ok else WARN,
                       ver or path, "" if ok else "git exists but errors")


def check_pip():
    try:
        import pip  # noqa: F401
        return CheckResult("pip", OK, f"pip {pip.__version__}")
    except ImportError:
        ok, out = _run([sys.executable, "-m", "pip", "--version"])
        if ok:
            return CheckResult("pip", OK, out)
        return CheckResult("pip", FAIL, "not importable",
                           "python -m ensurepip --upgrade")


def check_pillow():
    try:
        import PIL  # noqa: F401
        return CheckResult("Pillow", OK, f"Pillow {PIL.__version__}")
    except ImportError:
        return CheckResult("Pillow", WARN, "not installed",
                           "icons/logo render at reduced quality — "
                           "pip install Pillow")


def check_config(config=None):
    """Config file parses and holds a dict."""
    from .config import CONFIG_PATH
    if not os.path.exists(CONFIG_PATH):
        return CheckResult("Config", WARN, "not created yet",
                           "it appears on first save — nothing broken")
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
        size = os.path.getsize(CONFIG_PATH)
        return CheckResult("Config", OK,
                           f"{len(data)} keys · {size / 1024:.1f} KiB")
    except (OSError, ValueError) as exc:
        return CheckResult("Config", FAIL, f"invalid: {exc}",
                           f"back it up, then remove {CONFIG_PATH} "
                           f"(a fresh one is created)")


def check_workspace(workspace=None):
    if not workspace:
        return CheckResult("Workspace", WARN, "none open",
                           "open or create one from the Project Hub")
    if not os.path.isdir(workspace):
        return CheckResult("Workspace", FAIL, f"missing: {workspace}",
                           "was the folder moved or deleted?")
    files = sum(len(f) for _, _, f in os.walk(workspace))
    meta = os.path.join(workspace, ".dxn1-project.json")
    kind = ""
    if os.path.isfile(meta):
        try:
            with open(meta, "r", encoding="utf-8") as fh:
                kind = f" · {json.load(fh).get('kind', '?')}"
        except (OSError, ValueError):
            pass
    return CheckResult("Workspace", OK,
                       f"{os.path.basename(workspace)} · {files} files{kind}")


def check_workspace_git(workspace=None):
    if not workspace or not os.path.isdir(workspace):
        return CheckResult("Workspace git", WARN, "no workspace",
                           "")
    dotgit = os.path.join(workspace, ".git")
    if not os.path.exists(dotgit):
        return CheckResult("Workspace git", WARN, "not a repository",
                           "Source Control panel can `git init` for you")
    ok, branch = _run(["git", "-C", workspace, "rev-parse",
                       "--abbrev-ref", "HEAD"])
    if not ok:
        return CheckResult("Workspace git", FAIL, "git errors in workspace")
    dirty = []
    if os.path.isdir(dotgit):
        _, status = _run(["git", "-C", workspace, "status", "--porcelain"])
        dirty = [ln for ln in status.splitlines() if ln.strip()]
    extra = f" · {len(dirty)} uncommitted" if dirty else " · clean"
    return CheckResult("Workspace git", OK, f"⎇ {branch}{extra}")


def check_memory(workspace=None):
    if not workspace:
        return CheckResult("Agent memory", WARN, "no workspace", "")
    path = os.path.join(workspace, ".dxn1", "memory.json")
    if not os.path.exists(path):
        return CheckResult("Agent memory", OK, "empty (fresh workspace)",
                           "the agent learns facts via `remember: …`")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            n = len(data)
        elif isinstance(data, dict):
            facts = data.get("facts")
            n = len(facts) if isinstance(facts, list) else len(data)
        else:
            n = 0
        return CheckResult("Agent memory", OK, f"{n} facts stored")
    except (OSError, ValueError) as exc:
        return CheckResult("Agent memory", FAIL, f"invalid: {exc}",
                           f"fix or remove {path}")


def check_llm(config=None):
    cfg = config
    if cfg is None:
        try:
            from .config import Config
            cfg = Config()
        except Exception:  # noqa: BLE001
            return CheckResult("LLM backend", WARN, "config unreadable")
    backend = (cfg.get("backend") or cfg.get("llm_backend") or "auto")
    has_key = bool(cfg.get("api_key") or cfg.get("openai_api_key")
                   or cfg.get("github_token"))
    if has_key:
        return CheckResult("LLM backend", OK, f"{backend} · key configured")
    return CheckResult(
        "LLM backend", WARN, f"{backend} · no API key",
        "free tier works out of the box; add a key in Agent settings "
        "for higher limits")


def check_disk(min_free_mb=200):
    home = os.path.expanduser("~")
    try:
        usage = shutil.disk_usage(home)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < 50:
            return CheckResult("Disk space", FAIL,
                               f"{free_mb:.0f} MiB free",
                               "free space — the studio needs room to work")
        if free_mb < min_free_mb:
            return CheckResult("Disk space", WARN,
                               f"{free_mb:.0f} MiB free",
                               "getting low")
        return CheckResult("Disk space", OK, f"{free_mb:.0f} MiB free")
    except OSError as exc:
        return CheckResult("Disk space", WARN, f"unknown ({exc})")


def check_projects_root():
    from . import projects
    root = projects.DEFAULT_PROJECTS_ROOT
    if not os.path.isdir(root):
        return CheckResult("Projects root", WARN, f"{root} (not created)",
                           "created automatically on first scaffold")
    n = len([d for d in os.listdir(root)
             if os.path.isdir(os.path.join(root, d))
             and not d.startswith(".")])
    return CheckResult("Projects root", OK, f"{root} · {n} folders")


# ------------------------------------------------------------------ runner
def run_checks(config=None, workspace=None, include_env=True):
    """Run every check, return the list of CheckResult in display order."""
    results = []
    if include_env:
        results += [
            check_python(),
            check_tkinter(),
            check_git(),
            check_pip(),
            check_pillow(),
            check_disk(),
            check_projects_root(),
        ]
    results += [
        check_config(config),
        check_llm(config),
        check_workspace(workspace),
        check_workspace_git(workspace),
        check_memory(workspace),
    ]
    return results


def summary(results):
    counts = {OK: 0, WARN: 0, FAIL: 0}
    for r in results:
        counts[r.status] += 1
    return counts


def overall(results):
    """Worst status across all checks."""
    s = summary(results)
    if s[FAIL]:
        return FAIL
    if s[WARN]:
        return WARN
    return OK


def format_report(results, as_of=None):
    """Plain-text report (CLI + Copy button share this)."""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S",
                          time.localtime(as_of or time.time()))
    lines = [
        f"{APP_NAME} doctor — v{APP_VERSION}-{APP_CHANNEL}",
        f"host: {platform.system()} {platform.release()} · "
        f"{platform.python_implementation()} {platform.python_version()}",
        f"generated: {stamp}",
        "-" * 62,
    ]
    for r in results:
        row = f" {_ICONS[r.status]} {r.name:<16} {r.detail}"
        lines.append(row)
        if r.hint:
            lines.append(f"     ↳ {r.hint}")
    s = summary(results)
    lines.append("-" * 62)
    verdict = {
        OK: "all clear — the studio is in good shape",
        WARN: "healthy with warnings — see the ! rows above",
        FAIL: "problems found — see the ✗ rows above",
    }[overall(results)]
    lines.append(f" {s[OK]} ok · {s[WARN]} warnings · {s[FAIL]} failures "
                 f"— {verdict}")
    return "\n".join(lines)


# --------------------------------------------------------------------- CLI
def cli(argv=None):
    """python -m dxn1_studio.doctor [workspace]"""
    argv = list(sys.argv[1:] if argv is None else argv)
    workspace = argv[0] if argv else None
    if workspace and not os.path.isabs(workspace):
        workspace = os.path.abspath(workspace)
    try:
        from .config import Config
        config = Config()
    except Exception:  # noqa: BLE001 — doctor must run even with broken config
        config = None
    results = run_checks(config=config, workspace=workspace)
    print(format_report(results))
    return {OK: 0, WARN: 2, FAIL: 1}[overall(results)]


# -------------------------------------------------------------------- GUI
def open_doctor(master, theme, config=None, workspace=None, on_log=None):
    """Open the Doctor window (palette entry point)."""
    return DoctorWindow(master, theme, config, workspace, on_log=on_log)


class DoctorWindow:
    """Frame-less owner-managed Toplevel with the colour-coded report."""

    def __init__(self, master, theme, config=None, workspace=None,
                 on_log=None):
        import tkinter as tk

        self.master = master
        self.theme = theme
        self.accent = getattr(theme, "accent", "#7c3aed")
        self.on_log = on_log or (lambda msg: None)
        self.config = config
        self.workspace = workspace

        self.win = tk.Toplevel(master)
        self.win.title(f"{APP_NAME} — Doctor")
        self.win.configure(bg="#0d1117")
        self.win.transient(master)
        self.win.resizable(False, False)
        self.win.bind("<Escape>", lambda e: self.win.destroy())

        head = tk.Frame(self.win, bg="#0d1117")
        head.pack(fill="x", padx=22, pady=(16, 0))
        tk.Label(head, text="Environment Doctor", bg="#0d1117",
                 fg="#e6edf3", font=("sans-serif", 14, "bold")
                 ).pack(side="left")
        close = tk.Label(head, text="✕", bg="#0d1117", fg="#6e7a8a",
                         font=("sans-serif", 11, "bold"), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.win.destroy())

        tk.Label(self.win,
                 text="Read-only health check — nothing is changed or sent.",
                 bg="#0d1117", fg="#9aa7b8", font=("sans-serif", 9)
                 ).pack(anchor="w", padx=22)

        self.rows = tk.Frame(self.win, bg="#0d1117")
        self.rows.pack(fill="x", padx=22, pady=(10, 4))

        btns = tk.Frame(self.win, bg="#0d1117")
        btns.pack(fill="x", padx=22, pady=(6, 16))
        rerun = tk.Label(btns, text="Rerun checks", bg="#131a22",
                         fg="#e6edf3", font=("sans-serif", 9, "bold"),
                         padx=12, pady=6, cursor="hand2")
        rerun.pack(side="left")
        rerun.bind("<Button-1>", lambda e: self.refresh())
        copy = tk.Label(btns, text="Copy report", bg="#131a22",
                        fg="#e6edf3", font=("sans-serif", 9, "bold"),
                        padx=12, pady=6, cursor="hand2")
        copy.pack(side="left", padx=(8, 0))
        copy.bind("<Button-1>", lambda e: self._copy())
        self.status = tk.Label(btns, text="", bg="#0d1117", fg="#6e7a8a",
                               font=("sans-serif", 8))
        self.status.pack(side="right")

        # v2.48 — the doctor answers to keys, and the bar says so
        from . import hints
        self.win.bind("<F5>", lambda e: self.refresh())
        self.win.bind("<Control-r>", lambda e: self.refresh())
        self.win.bind("<Control-C>", lambda e: self._copy())
        self.hintbar = hints.hint_bar(self.win,
                       {"header": "#10151c", "text_muted": "#6e7a8a",
                        "accent": self.accent},
                       pairs=(("F5", "rerun", "F5"),
                              ("Ctrl+Shift+C", "copy report", "Ctrl+Shift+C")),
                       esc=True)

        self.refresh()
        self._center()

    def refresh(self):
        import tkinter as tk

        for w in self.rows.winfo_children():
            w.destroy()
        results = run_checks(config=self.config, workspace=self.workspace)
        for r in results:
            row = tk.Frame(self.rows, bg="#0d1117")
            row.pack(fill="x", pady=1)
            mark = tk.Label(row, text=_ICONS[r.status], bg="#0d1117",
                            fg=_COLORS[r.status],
                            font=("sans-serif", 10, "bold"), width=2)
            mark.pack(side="left")
            name = tk.Label(row, text=r.name, bg="#0d1117", fg="#e6edf3",
                            font=("sans-serif", 10, "bold"), width=15,
                            anchor="w")
            name.pack(side="left")
            detail = tk.Label(row, text=r.detail, bg="#0d1117",
                              fg="#9aa7b8", font=("sans-serif", 9),
                              anchor="w")
            detail.pack(side="left", padx=(4, 0))
            if r.hint:
                hint = tk.Label(self.rows, text=f"↳ {r.hint}",
                                bg="#0d1117", fg="#6e7a8a",
                                font=("sans-serif", 8))
                hint.pack(anchor="w", padx=(30, 0))
        s = summary(results)
        worst = overall(results)
        verdict = {OK: "all clear", WARN: "warnings above",
                   FAIL: "failures above"}[worst]
        self.status.config(
            text=f"{s[OK]} ok · {s[WARN]} warn · {s[FAIL]} fail — {verdict}",
            fg=_COLORS[worst])
        self._last_report = format_report(results)
        self.on_log(f"doctor: {s[OK]} ok, {s[WARN]} warn, {s[FAIL]} fail")

    def _copy(self):
        import tkinter as tk

        text = getattr(self, "_last_report", "") or format_report(
            run_checks(config=self.config, workspace=self.workspace))
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        self.status.config(text="report copied to clipboard",
                           fg=self.accent)

    def _center(self):
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        mx = self.master.winfo_rootx() + \
            (self.master.winfo_width() - w) // 2
        my = self.master.winfo_rooty() + \
            (self.master.winfo_height() - h) // 3
        self.win.geometry(f"+{max(0, mx)}+{max(0, my)}")


if __name__ == "__main__":
    raise SystemExit(cli())
