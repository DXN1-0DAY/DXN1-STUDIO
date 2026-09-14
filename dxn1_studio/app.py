"""DXN1 STUDIO — main application window.

Boot flow: splash → (first run: welcome wizard) → Project Hub → the IDE.

v1.1 layout: a slim activity bar switches the left sidebar between
Explorer / Search / Packages; the editor gained syntax highlighting, tab
buffers with dirty markers, a find bar and a command palette (Ctrl+K).
Everything extra stays opt-in: Flask & friends are installed only from
the Packages view, and DXN1 Agents (if enabled) asks permission before
every edit and command unless you switch it to full access — and it is
always sandboxed to the open workspace.
"""

import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
import webbrowser
from tkinter import ttk, filedialog, messagebox

from . import APP_NAME, APP_VERSION, APP_CHANNEL, APP_TAGLINE
from .theme import from_config, FONT_UI, FONT_MONO, ACCENTS
from .widgets import FileTree, CodeEditor, Terminal, TREE_SKIP
from .onboarding import WelcomeWizard
from .tour import InteractiveTour
from . import errors
from . import projects, export, llm
from .sandbox import (WorkspaceSandbox, AgentEngine, FakeBackend,
                      SandboxError)
from .hub import ProjectHub
from .splash import Splash
from .packages import PackagesView
from .search import SearchPanel
from .gitpanel import GitPanel
from .agent import DXN1AgentPanel, AgentSettingsDialog, ConnectDialog, \
    AGENTS_NAME
from . import updater

try:  # fuzzy launcher scoring (DS2 v2.29) — legacy substring fallback
    from . import fuzzy
except Exception:  # pragma: no cover
    fuzzy = None

FONT_SIZES = (("small", 10), ("medium", 11), ("large", 13))

REPO_URL = "https://github.com/DXN1-termux/DXN1-STUDIO"
TEXT_EXTS = {".py", ".pyw", ".pyi", ".js", ".ts", ".jsx", ".tsx", ".html",
             ".htm", ".css", ".json", ".md", ".txt", ".yml", ".yaml",
             ".toml", ".sh", ".cfg", ".ini", ".xml", ".svg", ".csv",
             ".rs", ".go", ".c", ".h", ".cpp", ".java", ".sql", ".env"}


# Terminal commands listed by `help` — the single source of
# truth shared with the cheat sheet exporter (cheatsheet.py).
TERMINAL_HELP = (
    ("dxn1 studio", "replay the boot splash"),
    ("run", "run the current file / project (F5)"),
    ("stop", "stop the running process"),
    ("clear", "clear this terminal"),
    ("packages", "open the optional-dependencies view"),
    ("search <query>", "search across the workspace"),
    ("find <text>", "find text in the current file"),
    ("palette", "open the command palette (Ctrl+K)"),
    ("commands", "list palette commands (optional filter)"),
    ("verbs", "browse every terminal verb in a window"),
    ("todo", "scan the workspace for TODO / FIXME"),
    ("tools", "developer tools: regex, JSON, text, time"),
    ("cron <expr>", "decode a cron schedule + next runs"),
    ("readability", "reading level of the current file"),
    ("jwt <token>", "decode a JWT — header, payload, exp"),
    ("env", "lint the workspace .env + masked copy"),
    ("gen", "generate UUIDs, nanoids, fake users, JSON"),
    ("db <file>", "browse SQLite databases — tables, "
                  "schema, queries"),
    ("tree <dir>", "ASCII directory tree for READMEs — "
                   "skips junk, copies to clipboard"),
    ("hash <file>", "checksums: MD5/SHA-1/256/512, folder "
                    "manifests, paste-a-hash verify"),
    ("focus <min>", "pomodoro focus timer — work/break "
                    "cycles with session dots"),
    ("clip", "clipboard history — paste earlier copies"),
    ("md", "live markdown preview — dual-pane, HTML "
           "export"),
    ("color", "color kit — hex/rgb/hsl, WCAG "
              "contrast, shade ramps"),
    ("rest", "REST bench — send HTTP requests, "
             "copy as curl, inspect responses"),
    ("chart", "chart studio — paste numbers, get line/"
              "bar/histogram + stats"),
    ("unit", "unit converter — length/mass/temp/data/"
             "time/speed at a glance"),
    ("charmap", "character map — browse/search Unicode "
                "blocks, click to copy"),
    ("case", "textcase — convert identifiers between "
             "snake/camel/kebab/… instantly"),
    ("passgen", "PassForge — cryptographic passwords "
                "with an entropy meter"),
    ("base", "numbase — convert numbers between any "
             "bases 2-36 + bit inspector"),
    ("csv", "CSV Lab — paste csv/tsv, peek the table, "
            "copy back as TSV"),
    ("calc", "MathPad — safe expression calculator "
             "(x = 5 assigns, _ is the last answer)"),
    ("hexdump", "ByteSnoop — hexdump & byte inspector, "
                "paste text or raw hex"),
    ("diff2", "Paste Diff — compare two pasted texts "
              "word/char/line"),
    ("xml", "Markup Bench — pretty/minify/validate "
            "XML + element stats"),
    ("contrast", "Contrast Auditor — WCAG grades + "
                 "fixes for every theme"),
    ("cheat", "Cheat Sheet — print-friendly HTML export of "
              "every command"),
    ("cvd", "Colorblind Lab — preview themes under color "
            "blindness"),
    ("session save", "snapshot tabs + cursor spots right now"),
    ("session", "list saved workspace sessions and restore one"),
    ("scribe <n>", "set the words-per-session goal for "
                   "the statusbar writing meter"),
    ("explain", "hand the last error to the agent"),
    ("git <args>", "run git in the workspace (status, add,"),
    ("", "commit, log… output streams below"),
    ("git watch [on|off]", "statusbar branch chip — amber when files "
                           "wait to be committed, ↑/↓ on divergence"),
    ("split", "toggle split editor view"),
    ("zen", "toggle zen mode"),
    ("goto <line>", "jump to a line"),
    ("recent", "list recently opened files"),
    ("activity", "recent studio notifications — searchable window "
                 "with kind filters"),
    ("activity copy", "every receipt to the clipboard, oldest first"),
    ("activity export [json|csv] [path]",
     "every receipt to a file — format follows the extension "
     "(default beside activity.json)"),
    ("activity snap", "write a nightly receipts snapshot now, "
                      "gate or no gate"),
    ("activity auto on|off", "the nightly snapshot gate — when on, "
                             "the whole diary lands in exports/ "
                             "every 24h, last 14 kept"),
    ("chip <name>", "open a statusbar chip's menu from the keyboard "
                    "— branch · deps · scribe · autosave"),
    ("lang", "list available UI language packs and the current one"),
    ("lang audit", "every pack answers for itself — coverage, stale "
                   "keys, highlight-safe honest audit"),
    ("lang diff [code]", "the honest ledger — real translations vs "
                         "seeds that still read English, plus "
                         "missing, stale and unsafe"),
    ("lang edit [code]", "open the translation desk — edit a pack "
                         "beside its English source; saved strings "
                         "become a user pack that overrides built-ins"),
    ("lang check [code|file]", "the checkup — a pack or a pack file "
                               "answers for itself before sharing: "
                               "unknown keys, empty values, junk "
                               "pairs, highlight-unsafe, real_pct"),
    ("lang pack <code> [dest]", "write a pack's own strings as a "
                                "shareable .json file (default "
                                "./<code>.json) — never overwrites"),
    ("update", "check GitHub for a newer release"),
    ("whatsnew", "release notes — what changed between tags"),
    ("deps", "cross-check imports vs requirements*.txt "
             "(fix / fresh / watch)"),
    ("hub", "open the Project Hub"),
    ("export", "export the workspace as a ZIP"),
    ("agent <request>", "talk to DXN1 Agents (if enabled)"),
    ("settings", "open studio settings"),
)


def matching_help_rows(query, rows=TERMINAL_HELP):
    """DS2 v2.37: help for one verb — exact command match first, then
    substring over commands/descriptions, then the three closest
    fuzzy hits. Empty when nothing matches."""
    q = str(query or "").strip().lower()
    if not q:
        return []
    exact = [r for r in rows if q == r[0] or q == r[0].split(" ")[0]]
    if exact:
        return exact
    sub = [r for r in rows if q in r[0].lower() or q in r[1].lower()]
    if sub:
        return sub
    try:
        from . import fuzzy as _fz
        scored = sorted(((_fz.score(q, r[0]), r) for r in rows),
                        key=lambda t: t[0], reverse=True)
        return [r for s, r in scored[:3] if s > 0]
    except Exception:  # noqa: BLE001 — help must never raise
        return []


def palette_help_rows(app):
    """DS2 v2.38: ``(label, shortcut)`` rows for every command the
    palette offers — the same registry Ctrl+K shows, flattened for
    the terminal's ``commands`` verb and ``help`` fallback. Never
    raises; an empty list means the palette could not be built."""
    try:
        rows = []
        for label, key, _fn in app.palette_commands():
            lab = " ".join(str(label or "").split())
            if not lab:
                continue
            rows.append((lab, str(key or "").strip()))
        return rows
    except Exception:  # noqa: BLE001 — listing must never raise
        return []


def extract_error_block(text, max_lines=60, max_chars=4000):
    """DS2 v2.6: pull the most recent error block out of terminal text.

    Understands three shapes, checked in order of recency-signal:

    1. **pytest/unittest failures** — a ``FAILED tests/...`` summary
       line, a ``FAIL: test_x`` header or a bare ``error:`` line; the
       block walks up to the ``=== FAILURES ===`` banner, a
       ``____ test_x ____`` underline or the ``FAIL:`` header itself
       (max 40 lines) so the assert context comes along.
    2. **Classic tracebacks** — from the
       ``Traceback (most recent call last)`` / ``…Error:`` line down,
       capped at ``max_lines``.

    Pure function — returns ``''`` when nothing matches, never raises.
    """
    if not text:
        return ""
    lines = text.split("\n")
    n = len(lines)
    # 1) pytest / unittest failure summaries (bottom-up, latest wins)
    #    — guarded so ordinary lines like "Failed to open file" or
    #    "fail-safe" never match: a pytest summary carries a path (::,
    #    .py), unittest headers say "FAIL: test_x (module.Class)".
    for i in range(n - 1, -1, -1):
        low = lines[i].strip().lower()
        is_pytest = (low.startswith("failed ")
                     and ("::" in low or ".py" in low or " - " in low))
        is_unittest = (low.startswith("fail:")
                       and ("test" in low or "(" in low))
        if is_pytest or is_unittest:
            top = i
            for j in range(i - 1, max(-1, i - 40), -1):
                s = lines[j].strip().lower()
                if s.startswith(("=== failures", "____ ")):
                    top = j
                    break
            # pytest: the summary line is the payload (context is above);
            # unittest: the details (exception line etc.) sit BELOW the
            # FAIL: header — take up to 12 lines down.
            bottom = i + 1 if is_pytest else min(n, i + 13)
            block = "\n".join(lines[top:bottom])
            return block.strip()[:max_chars]
    # 2) classic traceback / compiler error (bottom-up, first hit wins)
    for i in range(n - 1, -1, -1):
        low = lines[i].lower()
        if ("traceback (most recent call last)" in low
                or low.rstrip().endswith("error:")
                or (": error" in low) or ("syntaxerror" in low)):
            block = "\n".join(lines[i:i + max_lines])
            return block.strip()[:max_chars]
    return ""


_NAMED_KEYS = {"/": "slash", ",": "comma", "\\": "backslash",
               "+": "plus", "-": "minus", " ": "space",
               "Enter": "Return"}
_MOD_NAMES = {"ctrl": "Control", "alt": "Alt", "shift": "Shift"}


def accel_pattern(accel):
    """DS2 v2.47 — translate a human accelerator ("Ctrl+Shift+D",
    "Ctrl+/", "Ctrl++", "Alt+Up", "F5") into the exact Tk event
    pattern the code must have bound for it ("<Control-D>",
    "<Control-slash>", "<Control-plus>", "<Alt-Up>", "<F5>"). The
    honest bridge between what the UI advertises and what the keys
    really do: an untranslatable string returns "" so the audit can
    flag it instead of guessing."""
    try:
        s = str(accel).strip()
        if s in ("+", "-"):               # a bare plus/minus key
            key, mods_s = s, ""
        elif s.endswith("++"):
            key, mods_s = "+", s[:-2]
        elif s.endswith("+-"):
            key, mods_s = "-", s[:-2]
        else:
            parts = [p for p in s.split("+")]
            key, mods_s = parts[-1], "+".join(parts[:-1])
        key = str(key).strip()
        mods = [m.strip().lower() for m in mods_s.split("+") if m.strip()]
        if not key or key.lower() in _MOD_NAMES:
            return ""
        named = _NAMED_KEYS.get(key)
        if named is not None and len(key) == 1:
            key = named
        elif key in _NAMED_KEYS:          # "Enter" → "Return"
            key = _NAMED_KEYS[key]
        elif len(key) == 1 and key.isalpha():
            if "shift" in mods:
                key = key.upper()
                mods = [m for m in mods if m != "shift"]
            else:
                key = key.lower()
        elif len(key) == 1 and key.isdigit():
            pass                              # digits stay as-is
        # multi-char names (F5, F2, Return, Up…) stay as written
        head = "".join(_MOD_NAMES[m] + "-" for m in mods
                       if m in _MOD_NAMES)
        if not key:
            return ""
        return "<%s%s>" % (head, key)
    except Exception:  # noqa: BLE001 — never guess, never raise
        return ""


def looks_like_accel(hint):
    """DS2 v2.47 — does this palette hint claim to be a keybinding?
    "Ctrl+S", "Alt+Up", "F5", "Enter" → yes; "DS2" (a category tag),
    "line 42" (a symbol position), "" (no hint) → no. The honest-keys
    audit only polices real claims — it must never chase category
    labels."""
    h = str(hint or "").strip()
    if not h:
        return False
    if h.startswith(("Ctrl", "Alt", "Shift", "Meta")):
        return True
    if len(h) <= 6 and h[:1] == "F" and h[1:].isdigit():
        return True
    return h in ("Enter", "Return", "Esc", "Escape", "Tab")


class CommandPalette(tk.Toplevel):
    """Fuzzy command launcher (Ctrl+K / Ctrl+Shift+P)."""

    ROW_H = 34

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.commands = app.palette_commands()
        self.filtered = list(self.commands)
        self.selected = 0
        t = app.theme
        self.t = t
        self.title("Command Palette")
        self.configure(bg=t["card"])
        self.transient(app.root)
        self.overrideredirect(False)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        wrap = tk.Frame(self, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        wrap.pack(fill=tk.BOTH, expand=True)
        row = tk.Frame(wrap, bg=t["card"])
        row.pack(fill=tk.X, padx=12, pady=12)
        tk.Label(row, text="⌕", bg=t["card"], fg=t.accent,
                 font=(FONT_UI, 13, "bold")).pack(side=tk.LEFT, padx=(2, 8))
        self.entry = tk.Entry(row, bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"], relief=tk.FLAT,
                              font=(FONT_UI, 12), highlightthickness=0)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.entry.insert(0, "")
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", lambda e: self._run_selected())
        self.entry.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Down>", lambda e: self._move(1))

        tk.Label(wrap, text="commands ·  @symbols in this file",
                 bg=t["card"], fg=t["text_muted"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=14, pady=(0, 4))

        self.rows = tk.Frame(wrap, bg=t["card"])
        self.rows.pack(fill=tk.X, padx=8, pady=(0, 10))
        self._render()
        self._center()
        self.entry.focus_set()
        self.bind("<Escape>", lambda e: self.close())

    # ------------------------------------------------------------- logic
    def _on_type(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        q = self.entry.get().strip().lower()
        if q.startswith("@"):
            # symbol mode — jump to def / class in the active file
            needle = q[1:].strip()
            syms = self.app.editor.symbols()
            if fuzzy is not None and needle:
                hits = fuzzy.ranked(needle, [s[2] for s in syms])
                order = [syms[i] for i, _s, _p in hits]
                self.positions = [p for _i, _s, p in hits]
            else:
                order = [s for s in syms
                         if not needle or needle in s[2].lower()]
                self.positions = []
            self.filtered = [(f"{kind}  {name}", f"line {line}",
                              ("sym", line))
                             for line, kind, name in order]
        else:
            if fuzzy is not None:
                hits = fuzzy.ranked(q, [c[0] for c in self.commands])
                self.filtered = [self.commands[i] for i, _s, _p in hits]
                self.positions = [p for _i, _s, p in hits]
            else:
                self.filtered = [c for c in self.commands
                                 if not q or q in c[0].lower()]
                self.positions = []
        self.selected = 0
        self._render()

    def _move(self, delta):
        if not self.filtered:
            return
        self.selected = (self.selected + delta) % len(self.filtered)
        self._render()

    def _run_selected(self):
        if self.filtered:
            cmd = self.filtered[min(self.selected, len(self.filtered) - 1)]
            self.close()
            try:
                if isinstance(cmd[2], tuple) and cmd[2] and \
                        cmd[2][0] == "sym":
                    self.app.editor.goto_line(cmd[2][1])
                    self.app.editor.text.focus_set()
                    self.app._update_cursor_pos()
                else:
                    cmd[2]()
            except Exception as exc:  # noqa: BLE001 — palette never crashes
                errors.log_exception(f"palette command '{cmd[0]}' failed")
                self.app.toast(f"{cmd[0]} failed: {exc}", "error")

    def _render(self):
        for w in self.rows.winfo_children():
            w.destroy()
        for i, (label, hint, _fn) in enumerate(self.filtered[:9]):
            active = i == self.selected
            row = tk.Frame(self.rows, bg=self.t.accent if active
                           else self.t["card"])
            row.pack(fill=tk.X, pady=1)
            fg = "#ffffff" if active else self.t["text"]
            fg2 = "#ffffff" if active else self.t["text_muted"]
            if isinstance(_fn, tuple) and _fn and _fn[0] == "sym":
                kind, _, name = label.partition("  ")
                posset = set(self.positions[i]) \
                    if i < len(getattr(self, "positions", [])) \
                    else set()
                runs = fuzzy.split_runs(name, posset) \
                    if (fuzzy is not None and posset) else \
                    [(name, False)]
                for _ri, (chunk, hit) in enumerate(runs):
                    tk.Label(row, text=chunk, bg=row.cget("bg"),
                             fg=self.t.accent if (hit and not active) else fg,
                             font=(FONT_MONO, 10, "bold") if hit
                             else (FONT_MONO, 10),
                             anchor="w").pack(
                        side=tk.LEFT, padx=10 if _ri == 0 else 0,
                        pady=6)
                tk.Label(row, text=kind, bg=row.cget("bg"),
                         fg=self.t.accent if not active else fg,
                         font=(FONT_MONO, 8, "bold")).pack(
                    side=tk.LEFT, padx=(0, 8))
                tk.Label(row, text=hint, bg=row.cget("bg"), fg=fg2,
                         font=(FONT_UI, 8)).pack(side=tk.RIGHT, padx=10)
            else:
                posset = set(self.positions[i]) \
                    if i < len(getattr(self, "positions", [])) \
                    else set()
                runs = fuzzy.split_runs(label, posset) \
                    if (fuzzy is not None and posset) else \
                    [(label, False)]
                for _ri, (chunk, hit) in enumerate(runs):
                    tk.Label(row, text=chunk, bg=row.cget("bg"),
                             fg=self.t.accent if (hit and not active) else fg,
                             font=(FONT_UI, 10, "bold") if hit
                             else (FONT_UI, 10),
                             anchor="w").pack(
                        side=tk.LEFT, padx=10 if _ri == 0 else 0,
                        pady=6)
                if hint:
                    tk.Label(row, text=hint, bg=row.cget("bg"), fg=fg2,
                             font=(FONT_UI, 8)).pack(side=tk.RIGHT, padx=10)
            row.bind("<Button-1>", lambda e, i=i: self._pick(i))
        if not self.filtered:
            tk.Label(self.rows, text="no matching command",
                     bg=self.t["card"], fg=self.t["text_muted"],
                     font=(FONT_UI, 9)).pack(pady=8)
        # re-fit the window so it never trails a big empty area
        try:
            self._center()
        except tk.TclError:
            pass

    def _pick(self, i):
        self.selected = i
        self._run_selected()

    def _center(self):
        self.update_idletasks()
        w = 520
        h = min(560, self.winfo_reqheight())
        sw = self.winfo_screenwidth()
        x = self.app.root.winfo_rootx() + \
            max(0, (self.app.root.winfo_width() - w) // 2)
        y = self.app.root.winfo_rooty() + 80
        self.geometry(f"{w}x{h}+{max(0, x)}+{y}")

    def close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class QuickOpen(tk.Toplevel):
    """Fuzzy file opener across the workspace (Ctrl+P, VSCode style)."""

    MAX_FILES = 600

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.t = t = app.theme
        self.files = self._scan()
        self.filtered = list(self.files)
        self.positions = []   # DS2 v2.31: match positions per filtered row
        self.selected = 0
        self.title("Quick Open")
        self.configure(bg=t["card"])
        self.transient(app.root)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        wrap = tk.Frame(self, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        wrap.pack(fill=tk.BOTH, expand=True)
        self.entry = tk.Entry(wrap, bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"], relief=tk.FLAT,
                              font=(FONT_UI, 12), highlightthickness=0)
        self.entry.pack(fill=tk.X, padx=12, pady=12, ipady=6)
        self.entry.insert(0, "")
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", lambda e: self._open_selected())
        self.entry.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Down>", lambda e: self._move(1))

        tk.Label(wrap, text="type a file name · ↑↓ to pick · Enter to open",
                 bg=t["card"], fg=t["text_muted"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=14)
        self.rows = tk.Frame(wrap, bg=t["card"])
        self.rows.pack(fill=tk.X, padx=8, pady=(2, 10))
        self._render()
        self._center()
        self.entry.focus_set()
        self.bind("<Escape>", lambda e: self.close())

    def _scan(self):
        base = self.app.project_dir or os.path.expanduser("~")
        out = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in TREE_SKIP]
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext and ext not in TEXT_EXTS:
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, base)
                out.append((name, rel, full))
                if len(out) >= self.MAX_FILES:
                    return out
        out.sort(key=lambda r: r[1].lower())
        return out

    def _on_type(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        q = self.entry.get().strip().lower()
        if not q:
            self.filtered = list(self.files)
            self.positions = []
        elif fuzzy is not None:
            scored = []
            positions = []
            for name, rel, full in self.files:
                s = fuzzy.path_score(q, rel)
                if s >= 0:
                    scored.append((-s, rel, (name, rel, full)))
                    positions.append(fuzzy.match(q, rel)[1])
            scored.sort(key=lambda p: (p[0], p[1]))
            by_rel = {rel: pos
                      for (_s, rel, _item), pos in zip(scored, positions)}
            self.filtered = [item for _s, _rel, item in scored]
            self.positions = [by_rel.get(item[1], ())
                              for item in self.filtered]
        else:
            scored = []
            for name, rel, full in self.files:
                low = rel.lower()
                if q in low:
                    # prefer hits closer to the file name
                    score = low.rfind(q) - len(low)
                    scored.append((score, (name, rel, full)))
            scored.sort(key=lambda p: p[0])
            self.filtered = [item for _, item in scored]
            self.positions = []
        self.selected = 0
        self._render()

    def _move(self, delta):
        if self.filtered:
            self.selected = (self.selected + delta) % len(self.filtered)
            self._render()

    def _open_selected(self):
        if not self.filtered:
            return
        item = self.filtered[min(self.selected, len(self.filtered) - 1)]
        self.close()
        self.app.open_file(item[2])

    def _render(self):
        for w in self.rows.winfo_children():
            w.destroy()
        for i, (name, rel, _full) in enumerate(self.filtered[:9]):
            active = i == self.selected
            row = tk.Frame(self.rows, bg=self.t.accent if active
                           else self.t["card"])
            row.pack(fill=tk.X, pady=1)
            fg = "#ffffff" if active else self.t["text"]
            fg2 = "#ffffff" if active else self.t["text_muted"]
            # DS2 v2.31: bold-accent the matched chars in the name and
            # the rel path (positions index into rel)
            posset = set(self.positions[i]) \
                if i < len(getattr(self, "positions", [])) else set()
            runs = fuzzy.split_runs(name, posset) \
                if (fuzzy is not None and posset) else [(name, False)]
            for _ri, (chunk, hit) in enumerate(runs):
                tk.Label(row, text=chunk, bg=row.cget("bg"),
                         fg=self.t.accent if (hit and not active) else fg,
                         font=(FONT_UI, 10, "bold") if hit
                         else (FONT_UI, 10), anchor="w").pack(
                    side=tk.LEFT, padx=10 if _ri == 0 else 0, pady=5)
            tk.Label(row, text=rel, bg=row.cget("bg"), fg=fg2,
                     font=(FONT_UI, 8), anchor="e").pack(
                side=tk.RIGHT, padx=10)
            row.bind("<Button-1>", lambda e, i=i: self._pick(i))
        if not self.filtered:
            tk.Label(self.rows, text="no matching files",
                     bg=self.t["card"], fg=self.t["text_muted"],
                     font=(FONT_UI, 9)).pack(pady=8)
        try:
            self._center()
        except tk.TclError:
            pass

    def _pick(self, i):
        self.selected = i
        self._open_selected()

    def _center(self):
        self.update_idletasks()
        w = 560
        h = min(520, self.winfo_reqheight())
        x = self.app.root.winfo_rootx() + \
            max(0, (self.app.root.winfo_width() - w) // 2)
        y = self.app.root.winfo_rooty() + 80
        self.geometry(f"{w}x{h}+{max(0, x)}+{y}")

    def close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class DXN1Studio:
    def __init__(self, config, smoke_test=False, no_splash=False):
        self.config = config
        self.theme = from_config(config)
        self.smoke_test = smoke_test
        self.no_splash = no_splash
        self.restart_requested = False
        # DS2: honour the persisted UI language (i18n activation)
        try:
            from .i18n import boot_from_config
            boot_from_config(config)
        except Exception:  # noqa: BLE001 — boot continues in English
            pass

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}  ·  v{APP_VERSION}-{APP_CHANNEL}")
        self.root.geometry("1280x820")
        self.root.minsize(940, 580)
        self.root.configure(bg=self.theme["bg"])
        # DS2: restore remembered per-screen geometry (defensive)
        try:
            from .geom import restore_root
            restore_root(self.root, self.config, min_w=940,
                         min_h=580)
        except Exception:  # noqa: BLE001 — boot must never die here
            pass

        self.open_files = {}
        self.active_file = None
        self.sidebar_visible = True
        self.sidebar_view = "explorer"
        self.terminal_visible = True
        self._tab_frames = {}
        self._buffer_cursors = {}   # DS2 v2.31: per-tab cursor memory
        self._buffers = {}          # path -> {"content": str, "dirty": bool}
        self.clip_ring = None       # DS2: clipboard history ring
        self._autosave_job = None
        self._palette = None
        self._quick_open = None
        self._split = None          # second editor when split view is on
        self.zen_mode = False
        self._zen_state = None
        self._updater_shown = False

        self.project_dir = None
        self.project_kind = "empty"
        self.pending_project = None      # from --project CLI arg
        self.agent_panel = None
        self.agents_visible = False
        self._hub = None
        self._wizard = None
        self._tour = None
        self._splash_active = False
        self.proc = None
        self._proc_q = queue.Queue()

        self.widgets = {}
        self.first_launch = config.register_launch()
        self.setup_ui()
        self.setup_menu()
        self.setup_bindings()

        errors.set_notifier(self.toast)
        errors.install(self.root)
        self.editor.auto_indent = \
            bool(self.config.get("editor_auto_indent", True))
        self.editor.auto_close = \
            bool(self.config.get("editor_auto_close", True))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._greet()
        # DS2 v2.36: one heartbeat drives the boot check AND the slow
        # periodic re-check (interval clamped 15 min..6 h)
        self.root.after(4000, self._schedule_update_check)

    # ------------------------------------------------------------------- ui
    def setup_ui(self):
        t = self.theme

        # status bar (packed first so it always stays visible)
        self.statusbar = tk.Frame(self.root, bg=t["statusbar"], height=30)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.statusbar.pack_propagate(False)

        left = tk.Frame(self.statusbar, bg=t["statusbar"])
        left.pack(side=tk.LEFT, padx=12)
        self.status_ready = tk.Label(left, text="● Ready", bg=t["statusbar"],
                                     fg=t["success"], font=(FONT_UI, 9, "bold"))
        self.status_ready.pack(side=tk.LEFT)
        self.status_file = tk.Label(left, text="No file open", bg=t["statusbar"],
                                    fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_file.pack(side=tk.LEFT, padx=(14, 0))
        self.status_pos = tk.Label(left, text="", bg=t["statusbar"],
                                   fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_pos.pack(side=tk.LEFT, padx=(14, 0))
        self.status_ws = tk.Label(left, text="", bg=t["statusbar"],
                                  fg=t.accent, font=(FONT_UI, 9, "bold"))
        self.status_ws.pack(side=tk.LEFT, padx=(14, 0))
        self.status_branch = tk.Label(left, text="", bg=t["statusbar"],
                                      fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_branch.pack(side=tk.LEFT, padx=(10, 0))

        right = tk.Frame(self.statusbar, bg=t["statusbar"])
        right.pack(side=tk.RIGHT, padx=12)
        self.status_agents = tk.Label(right, text="", bg=t["statusbar"],
                                      fg=t["text_muted"], font=(FONT_UI, 9))
        self.status_agents.pack(side=tk.RIGHT, padx=(0, 10))
        tk.Label(right, text=f"v{APP_VERSION}-{APP_CHANNEL}", bg=t["statusbar"],
                 fg=t["text_muted"], font=(FONT_UI, 9)).pack(side=tk.RIGHT)
        # DS2: plugin status items — one compact label fed by
        # plugins.get_registry().status_text() (kept left of agents)
        self.status_plugins = tk.Label(right, text="", bg=t["statusbar"],
                                       fg=t.accent, font=(FONT_UI, 9))
        self.status_plugins.pack(side=tk.RIGHT, padx=(0, 10))
        # DS2 v2.6: encoding + line-endings chip (left of plugins)
        self.status_enc = tk.Label(right, text="", bg=t["statusbar"],
                                   fg=t["text_muted"], font=(FONT_UI, 8))
        self.status_enc.pack(side=tk.RIGHT, padx=(0, 12))
        # DS2: scribe mini chip — live words/WPM/goal meter
        self.scribe_chip = None
        try:
            from .scribe import ScribeChip
            self.scribe_chip = ScribeChip(goal_words=int(
                self.config.get("scribe_goal_words", 500)))
        except Exception:  # noqa: BLE001 — chip is optional
            self.scribe_chip = None
        self.status_scribe = tk.Label(right, text="", bg=t["statusbar"],
                                      fg=t["text_muted"],
                                      font=(FONT_UI, 9), cursor="hand2")
        self.status_scribe.pack(side=tk.RIGHT, padx=(0, 12))
        self.status_scribe.bind("<Button-1>", self._scribe_click)
        # DS2 v2.43: every chip has a menu — the scribe chip joins
        self.status_scribe.bind("<Button-3>", self._scribe_chip_menu)
        # DS2 v2.33: session autosave chip — quiet last-saved hint;
        # click it to snapshot right now
        self.status_sesave = tk.Label(right, text="", bg=t["statusbar"],
                                      fg=t["text_muted"],
                                      font=(FONT_UI, 9), cursor="hand2")
        self.status_sesave.pack(side=tk.RIGHT, padx=(0, 12))
        self.status_sesave.bind("<Button-1>",
                                lambda _e: self.save_session_now())
        # DS2 v2.43: every chip has a menu — the autosave chip joins
        self.status_sesave.bind("<Button-3>", self._sesave_chip_menu)
        # DS2 v2.39: dependency watch chip — a quiet "deps ok" that
        # turns amber the moment the workspace drifts from the last
        # deps report; click it to rescan
        self.status_deps = tk.Label(right, text="", bg=t["statusbar"],
                                    fg=t["text_muted"],
                                    font=(FONT_UI, 9), cursor="hand2")
        self.status_deps.pack(side=tk.RIGHT, padx=(0, 12))
        self.status_deps.bind("<Button-1>",
                              lambda _e: self._deps_chip_click())
        self.status_deps.bind("<Button-3>", self._deps_chip_menu)
        self._deps_sig_state = ""   # last state the chip was drawn for
        self._deps_probed_at = 0.0  # throttle for the cheap-but-not-free probe
        # DS2 v2.40: git lane chip — the branch name sits quietly in the
        # statusbar, turns amber with a ● N when files are uncommitted,
        # and gains ↑/↓ arrows when the branch diverges from upstream;
        # click it to open Source Control
        self.status_git = tk.Label(right, text="", bg=t["statusbar"],
                                   fg=t["text_muted"],
                                   font=(FONT_UI, 9), cursor="hand2")
        self.status_git.pack(side=tk.RIGHT, padx=(0, 12))
        self.status_git.bind("<Button-1>",
                             lambda _e: self._git_chip_click())
        self.status_git.bind("<Button-3>", self._git_chip_menu)
        self._git_sig_state = ""    # last state the git chip was drawn for
        self._git_probed_at = 0.0   # throttle — one git call max per 3s
        self._last_chip_menu = None  # DS2 v2.52: the menu now introspects
        self._chip_tip(self.status_git,
                       "Source control — click opens the panel, "
                       "right-click for actions · Ctrl+Alt+G")
        self._chip_tip(self.status_deps,
                       "Dependency watch — click rescans, "
                       "right-click for actions · Ctrl+Alt+E")
        self._chip_tip(self.status_sesave,
                       "Session autosave — click to snapshot now, "
                       "right-click for actions · Ctrl+Alt+A")
        self._chip_tip(self.status_scribe,
                       "Scribe meter — click for session details, "
                       "right-click for actions · Ctrl+Alt+W")
        # DS2 v2.44: the studio keeps its receipts — every toast is
        # archived in a ring buffer the Activity window can show.
        # DS2 v2.45: the receipts survive the night — reload whatever
        # the last session whispered (corrupt file → fresh ring)
        try:
            from .activity import ActivityLog, load_json
            loaded = load_json(self._activity_path(), cap=100)
            self.activity_log = loaded if loaded is not None \
                else ActivityLog(cap=100)
        except Exception:  # noqa: BLE001 — the log is optional
            self.activity_log = None
        # DS2 v2.51: the diary writes itself — first nightly-snapshot
        # check politely late (the toast layer is alive by then),
        # then re-armed every half hour by the check itself
        try:
            self.root.after(8000, self._activity_autosnap_check)
        except Exception:  # noqa: BLE001 — garnish
            pass

        # toast layer (placed above the status bar, right aligned)
        self.toast_layer = tk.Frame(self.root, bg=t["bg"])
        self.toast_layer.place(relx=1.0, rely=1.0, x=-14, y=-44,
                               anchor="se")

        # themed menu bar — drawn by us so dark mode never flashes a
        # system-white strip above the studio (the native menubar can't
        # be recoloured on Linux/X11)
        self.menu_bar = tk.Frame(self.root, bg=t["header"], height=32)
        self.menu_bar.pack(side=tk.TOP, fill=tk.X)
        self.menu_bar.pack_propagate(False)

        # body: activity rail + main panes
        body = tk.Frame(self.root, bg=t["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        self.body = body

        self.activity = tk.Frame(body, width=46, bg=t["header"])
        self.activity.pack(side=tk.LEFT, fill=tk.Y)
        self.activity.pack_propagate(False)
        self._build_activity()

        # the agents dock claims its right rail BEFORE the pane cavity is
        # handed out (pack order = slab order in Tk)
        self.agents_visible = bool(self.config.get("agents_enabled"))
        self._build_agent_panel()

        # NOTE: uses theme["border"]; v1.0 crashed here (DARK_BORDER)
        self.main_container = tk.PanedWindow(body, orient=tk.HORIZONTAL,
                                             bg=t["border"], sashwidth=3,
                                             bd=0)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ---- sidebar container with switchable views
        self.sidebar_container = tk.Frame(self.main_container,
                                          bg=t["sidebar"])
        self.sidebar = FileTree(self.sidebar_container, t,
                                on_file_select=self.open_file,
                                on_context=self._explorer_menu)
        self.sidebar.pack(fill=tk.BOTH, expand=True)
        self.search_view = SearchPanel(self.sidebar_container, t,
                                       on_open_match=self.open_search_match)
        self.git_view = GitPanel(self.sidebar_container, t,
                                 on_open_file=self.open_file,
                                 on_log=lambda msg: self.terminal.log(msg),
                                 config=self.config)
        self.packages_view = PackagesView(self.sidebar_container, t)
        self.main_container.add(self.sidebar_container, width=252,
                                minsize=190)
        self.show_sidebar_view("explorer", initial=True)

        # DS2: first-run mastery checklist docked under the sidebar views
        try:
            from .checklist import FirstRunChecklist, visible_for
            if visible_for(self.config):
                self.checklist = FirstRunChecklist(
                    self.sidebar_container, t, self.config,
                    on_log=lambda msg: self.terminal.log(msg))
                self.checklist.pack(side=tk.BOTTOM, fill=tk.X)
        except Exception:
            self.checklist = None

        self.right_panel = tk.PanedWindow(self.main_container,
                                          orient=tk.VERTICAL,
                                          bg=t["border"], sashwidth=3, bd=0)
        self.main_container.add(self.right_panel)

        editor_container = tk.Frame(self.right_panel, bg=t["editor"])

        toolbar = tk.Frame(editor_container, bg=t["header"], height=38)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        self.toolbar = toolbar
        self._build_toolbar()

        tabs_frame = tk.Frame(editor_container, bg=t["header"], height=36)
        tabs_frame.pack(fill=tk.X)
        tabs_frame.pack_propagate(False)
        self.tabs_frame = tabs_frame

        self.findbar = self._build_findbar(editor_container)

        self.editor = CodeEditor(editor_container, t)
        self.editor.text.bind("<KeyRelease>", self._on_editor_key)
        self.editor.text.bind("<ButtonRelease-1>", self._update_cursor_pos)
        self.editor.set_font_size(self.config.get("editor_font_size", 11))
        self.editor.set_wrap(bool(self.config.get("word_wrap", False)))
        self._install_bookmark_bridge(self.editor)   # DS2: persistence
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.right_panel.add(editor_container, minsize=200)

        self.terminal = Terminal(self.right_panel, t, greeting="Ready",
                                 on_command=self.handle_terminal_command)
        self.right_panel.add(self.terminal, height=200, minsize=80)
        # keep the editor the pane that grows: pin the sash so the
        # terminal keeps its height when the window resizes — until the
        # user drags it themselves
        self._sash_user = False
        self.right_panel.bind("<B1-Motion>",
                              lambda e: setattr(self, "_sash_user", True))
        self.right_panel.bind("<Configure>", self._pin_sash, add="+")

        self.widgets = {
            "sidebar": self.sidebar,
            "sidebar_container": self.sidebar_container,
            "activity": self.activity,
            "search": self.search_view,
            "git": self.git_view,
            "packages": self.packages_view,
            "tabs_frame": self.tabs_frame,
            "toolbar": self.toolbar,
            "editor": self.editor,
            "terminal": self.terminal,
        }

        # DXN1 Agents dock — built above; just refresh its status here
        self._refresh_agents_status()
        self._refresh_plugin_status()   # DS2: plugins statusbar + 5s timer

    # --------------------------------------------------------- activity bar
    def _build_activity(self):
        t = self.theme
        self._activity_items = []
        for key, tip, cmd in (
                ("explorer", "Explorer", lambda: self.show_sidebar_view("explorer")),
                ("search", "Search in files", lambda: self.show_sidebar_view("search")),
                ("git", "Source control", lambda: self.show_sidebar_view("git")),
                ("packages", "Packages", lambda: self.show_sidebar_view("packages"))):
            self._activity_items.append(
                self._activity_button(key, tip, cmd, top=True))
        tk.Frame(self.activity, bg=t["border"], height=1).pack(
            fill=tk.X, pady=(6, 6), padx=8)
        for key, tip, cmd in (
                ("hub", "Project Hub", self.open_hub),
                ("agents", "DXN1 Agents", self.toggle_agents_panel)):
            self._activity_items.append(
                self._activity_button(key, tip, cmd, top=False))
        self._paint_activity()

    def _activity_button(self, key, tip, cmd, top=True):
        t = self.theme
        side = tk.TOP if top else tk.BOTTOM
        canvas = tk.Canvas(self.activity, width=46, height=42,
                           bg=t["header"], highlightthickness=0,
                           cursor="hand2")
        canvas.pack(side=side)
        canvas.bind("<Button-1>", lambda e: cmd())
        canvas.bind("<Enter>", lambda e: self._paint_activity_item(
            key, hover=True))
        canvas.bind("<Leave>", lambda e: self._paint_activity_item(key))
        item = {"key": key, "canvas": canvas, "tip": tip}
        self._draw_activity_icon(canvas, key)
        return item

    def _draw_activity_icon(self, canvas, kind, hover=False):
        t = self.theme
        active = (self.sidebar_view == kind) if kind in \
            ("explorer", "search", "packages") else \
            (kind == "agents" and self.agents_visible)
        color = t["text"] if hover else (t.accent if active
                                         else t["text_muted"])
        canvas.delete("all")
        if active:
            canvas.create_rectangle(0, 0, 3, 42, fill=t.accent, outline="")
        if kind == "explorer":
            canvas.create_rectangle(12, 11, 34, 31, outline=color, width=2)
            for y in (17, 22, 27):
                canvas.create_line(16, y, 30, y, fill=color)
        elif kind == "search":
            canvas.create_oval(12, 11, 26, 25, outline=color, width=2)
            canvas.create_line(25, 24, 33, 32, fill=color, width=2)
        elif kind == "git":
            # branch glyph: a node with two commits
            canvas.create_line(23, 12, 23, 30, fill=color, width=2)
            canvas.create_oval(19, 8, 27, 16, outline=color, width=2)
            canvas.create_oval(19, 26, 27, 34, outline=color, width=2)
            canvas.create_line(27, 30, 33, 30, fill=color, width=2)
            canvas.create_oval(31, 26, 37, 34, outline=color, width=2)
        elif kind == "packages":
            canvas.create_rectangle(11, 13, 35, 31, outline=color, width=2)
            canvas.create_line(11, 20, 35, 20, fill=color)
            canvas.create_line(23, 13, 23, 20, fill=color)
        elif kind == "hub":
            for x, y in ((12, 11), (25, 11), (12, 24), (25, 24)):
                canvas.create_rectangle(x, y, x + 9, y + 9,
                                        outline=color, width=2)
        elif kind == "agents":
            canvas.create_polygon(23, 11, 33, 21, 23, 31, 13, 21,
                                  outline=color, width=2, fill="")

    def _paint_activity_item(self, key, hover=False):
        for item in self._activity_items:
            if item["key"] == key:
                self._draw_activity_icon(item["canvas"], key, hover=hover)

    def _paint_activity(self):
        for item in self._activity_items:
            self._draw_activity_icon(item["canvas"], item["key"])

    # ------------------------------------------------------- sidebar views
    def show_sidebar_view(self, name, initial=False):
        if name not in ("explorer", "search", "git", "packages"):
            return
        self.sidebar_view = name
        self.sidebar.pack_forget()
        for view in (self.search_view, self.git_view, self.packages_view):
            view.pack_forget()
        view = {"explorer": self.sidebar, "search": self.search_view,
                "git": self.git_view,
                "packages": self.packages_view}[name]
        view.pack(fill=tk.BOTH, expand=True)
        self._paint_activity()
        if name == "search":
            self.search_view.set_workspace(self.project_dir)
            self.search_view.entry.focus_set()
        elif name == "git":
            self.git_view.set_workspace(self.project_dir)

    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self.main_container.forget(self.sidebar_container)
        else:
            self.main_container.forget(self.right_panel)
            self.main_container.add(self.sidebar_container, width=252,
                                    minsize=190)
            self.main_container.add(self.right_panel)
        self.sidebar_visible = not self.sidebar_visible
        self._paint_activity()

    def _pin_sash(self, event=None):
        """Editor absorbs window growth; terminal keeps its height."""
        if getattr(self, "_sash_user", False) or not self.terminal_visible:
            return
        self.root.after_idle(self._pin_sash_now)

    def _pin_sash_now(self):
        if self._sash_user or not self.terminal_visible:
            return
        try:
            h = self.right_panel.winfo_height()
            if h > 340 and str(self.terminal) in self.right_panel.panes():
                self.right_panel.sash_place(0, 0, h - 224)
        except (tk.TclError, IndexError):
            pass

    def _build_agent_panel(self):
        if self.agent_panel is not None:
            return
        # docked OUTSIDE the paned window (like VS Code's side bars):
        # a fixed-width right rail that never fights the editor for space
        self.agent_panel = DXN1AgentPanel(self.body, self)
        self.agent_panel.configure(width=300)
        self.agent_panel.pack_propagate(False)
        if self.project_dir:
            self.agent_panel.set_workspace(self.project_dir)
        if self.agents_visible:
            kw = {"side": tk.RIGHT, "fill": tk.Y}
            # re-packs (toggles) must land before the panes in pack order
            if getattr(self, "main_container", None) is not None:
                kw["before"] = self.main_container
            self.agent_panel.pack(**kw)
        self.widgets["agents"] = self.agent_panel
        self._paint_activity()

    def apply_agents_visibility(self):
        enabled = bool(self.config.get("agents_enabled"))
        if enabled and self.agent_panel is None:
            self._build_agent_panel()
            self.agents_visible = True
            self.agent_panel.pack(side=tk.RIGHT, fill=tk.Y,
                                  before=self.main_container)
        elif not enabled and self.agent_panel is not None:
            try:
                self.agent_panel.pack_forget()
            except tk.TclError:
                pass
            self.agent_panel.destroy()
            self.agent_panel = None
            self.widgets.pop("agents", None)
            self.agents_visible = False
        elif enabled and self.agent_panel is not None and \
                self.agents_visible and \
                not self.agent_panel.winfo_ismapped():
            self.agent_panel.pack(side=tk.RIGHT, fill=tk.Y,
                                  before=self.main_container)
        if self.agent_panel is not None:
            self.agent_panel.refresh_mode()
        self._build_toolbar()
        self.setup_menu()          # rebuild so agent entries appear/disappear
        self._refresh_agents_status()
        self._refresh_plugin_status()   # DS2: pick up reloads immediately
        self._paint_activity()

    def toggle_agents_panel(self):
        if self.agent_panel is None:
            return
        if self.agents_visible:
            try:
                self.agent_panel.pack_forget()
            except tk.TclError:
                pass
            self.agents_visible = False
        else:
            self.agent_panel.pack(side=tk.RIGHT, fill=tk.Y,
                                  before=self.main_container)
            self.agents_visible = True
        self._paint_activity()

    def _refresh_agents_status(self):
        if not self.config.get("agents_enabled"):
            self.status_agents.config(text="")
            return
        full = not self.config.get("agents_ask_edits") and \
            not self.config.get("agents_ask_commands")
        self.status_agents.config(
            text=f"◆ Agents: {llm.describe_backend(self.config)} · "
                 f"{'full access' if full else 'ask mode'}",
            fg=self.theme["success"] if full else self.theme["text_muted"])

    def _refresh_plugin_status(self):
        """DS2: pull plugin status items into the statusbar.

        One compact label shows every registered plugin status item
        (joined with ' · '). Fully defensive — plugins.py may be absent,
        the registry empty, or a callback broken; the statusbar must
        never suffer for it. Re-arms a light 5 s timer so items stay
        fresh (session clocks, counts…) without any extra plumbing.
        """
        try:
            text = ""
            try:
                from . import plugins as _plugins
                vals = _plugins.get_registry().status_text(
                    workspace=getattr(self, "project_dir", "") or "",
                    path=getattr(self.editor, "file_path", "") or "")
                parts = [v for (_k, v) in sorted(vals.items()) if v]
                text = " · ".join(parts[:3])   # keep the bar calm
            except Exception:       # noqa: BLE001 — no plugins, no text
                text = ""
            if hasattr(self, "status_plugins"):
                self.status_plugins.config(text=text)
        except Exception:           # noqa: BLE001 — statusbar stays alive
            pass
        # periodic re-arm (once; every call reschedules itself)
        try:
            if getattr(self, "_plugin_status_job", None):
                try:
                    self.root.after_cancel(self._plugin_status_job)
                except Exception:   # noqa: BLE001
                    pass
            self._plugin_status_job = self.root.after(
                5000, self._refresh_plugin_status)
        except Exception:           # noqa: BLE001 — headless tests
            pass

    def setup_menu(self):
        """Build the in-app themed menu bar (replaces the native one,
        which cannot be dark-themed on Linux/X11)."""
        t = self.theme
        bar_defs = []
        menu_opts = dict(tearoff=0, bg=t["sidebar"], fg=t["text"],
                         activebackground=t["hover"],
                         activeforeground=t["text"], bd=0)

        file_menu = tk.Menu(self.root, **menu_opts)
        recents = self.config.get("recent_files") or []
        file_menu.add_command(label="New File", command=self.new_file,
                              accelerator="Ctrl+N")
        file_menu.add_command(label="Open File…", command=self.open_file_dialog,
                              accelerator="Ctrl+O")
        file_menu.add_command(label="Quick Open…", command=self.open_quick_open,
                              accelerator="Ctrl+P")
        file_menu.add_command(label="Recent files…",  # DS2: fuzzy picker
                              command=self.open_recent_picker,
                              accelerator="Ctrl+R")
        if recents:
            recent_menu = tk.Menu(file_menu, **menu_opts)
            shown = 0
            for path in recents:
                if os.path.isfile(path):
                    recent_menu.add_command(
                        label=f"{os.path.basename(path)}  ·  "
                              f"{os.path.dirname(path)}",
                        command=lambda p=path: self.open_file(p))
                    shown += 1
                if shown >= 10:
                    break
            if shown:
                file_menu.add_cascade(label="Open Recent", menu=recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_file,
                              accelerator="Ctrl+S")
        file_menu.add_command(label="Save As…", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Project Hub…", command=self.open_hub)
        file_menu.add_command(label="Open Workspace…",
                              command=self.open_workspace_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Export Project as ZIP…",
                              command=self.export_project_zip)
        file_menu.add_command(label="Export Current File As…",
                              command=self.export_current_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        bar_defs.append(("File", file_menu))

        edit_menu = tk.Menu(self.root, **menu_opts)
        txt = lambda: self.editor.text
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z",
                              command=lambda: txt().event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y",
                              command=lambda: txt().event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X",
                              command=lambda: txt().event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C",
                              command=lambda: txt().event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V",
                              command=lambda: txt().event_generate("<<Paste>>"))
        edit_menu.add_command(label="Find…", command=self.toggle_find,
                              accelerator="Ctrl+F")
        edit_menu.add_command(label="Replace…", command=self.open_replace,
                              accelerator="Ctrl+H")
        edit_menu.add_command(label="Go to Line…", command=self.goto_line_dialog,
                              accelerator="Ctrl+G")
        edit_menu.add_separator()
        edit_menu.add_command(label="Toggle Comment",
                              accelerator="Ctrl+/",
                              command=self.editor.toggle_comment)
        edit_menu.add_command(label="Duplicate Line",
                              accelerator="Ctrl+Shift+D",
                              command=self.editor.duplicate_line)
        edit_menu.add_command(label="Delete Line",
                              accelerator="Ctrl+Shift+K",
                              command=self.editor.delete_line)
        edit_menu.add_command(label="Move Line Up", accelerator="Alt+Up",
                              command=lambda: self.editor.move_line(-1))
        edit_menu.add_command(label="Move Line Down", accelerator="Alt+Down",
                              command=lambda: self.editor.move_line(1))
        # DS2: line tools
        edit_menu.add_command(label="Sort Lines A→Z", accelerator="Ctrl+Alt+S",
                              command=lambda: self.apply_line_tool("az"))
        edit_menu.add_command(label="Dedupe Lines",
                              accelerator="Ctrl+Alt+D",
                              command=lambda: self.apply_line_tool("dedupe"))
        edit_menu.add_command(label="Shuffle Lines",
                              accelerator="Ctrl+Alt+H",
                              command=lambda: self.apply_line_tool("shuffle"))
        edit_menu.add_command(label="Reverse Lines",
                              accelerator="Ctrl+Alt+R",
                              command=lambda: self.apply_line_tool("reverse"))
        edit_menu.add_command(label="Trim Trailing Whitespace",
                              command=lambda: self.apply_line_tool("trim"))
        edit_menu.add_command(label="Paste from History…",
                              accelerator="Ctrl+Shift+V",
                              command=self.paste_from_history)
        # DS2: line tools — sort & dedupe on the selection
        edit_menu.add_command(label="Sort Lines (A→Z)",
                              command=lambda: self.editor.sort_lines())
        edit_menu.add_command(label="Sort Lines (Numeric)",
                              command=lambda: self.editor.sort_lines(
                                  numeric=True))
        edit_menu.add_command(label="Sort Lines (Z→A)",
                              command=lambda: self.editor.sort_lines(
                                  reverse=True))
        edit_menu.add_command(label="Remove Duplicate Lines",
                              command=lambda: self.editor.unique_lines())
        edit_menu.add_separator()
        edit_menu.add_command(label="Bigger Text", accelerator="Ctrl++",
                              command=lambda: self.change_font_size(1))
        edit_menu.add_command(label="Smaller Text", accelerator="Ctrl+-",
                              command=lambda: self.change_font_size(-1))
        wrap_state = tk.BooleanVar(
            value=bool(self.config.get("word_wrap", False)))
        edit_menu.add_checkbutton(label="Word Wrap", variable=wrap_state,
                                  command=self.toggle_word_wrap)
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings…", command=self.open_settings,
                              accelerator="Ctrl+,")
        bar_defs.append(("Edit", edit_menu))

        view_menu = tk.Menu(self.root, **menu_opts)
        view_menu.add_command(label="Command Palette",
                              command=self.open_palette,
                              accelerator="Ctrl+K")
        view_menu.add_command(label="Quick Open File",
                              command=self.open_quick_open,
                              accelerator="Ctrl+P")
        view_menu.add_separator()
        view_menu.add_command(label="Split Editor",
                              command=self.toggle_split,
                              accelerator="Ctrl+\\")
        view_menu.add_command(label="Zen Mode",
                              command=self.toggle_zen,
                              accelerator="Ctrl+Alt+Z")
        view_menu.add_command(label="Explorer", command=lambda:
                              self.show_sidebar_view("explorer"))
        view_menu.add_command(label="Search in Files", command=lambda:
                              self.show_sidebar_view("search"))
        view_menu.add_command(label="Source Control", command=lambda:
                              self.show_sidebar_view("git"))
        view_menu.add_command(label="Packages", command=lambda:
                              self.show_sidebar_view("packages"))
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal)
        view_menu.add_command(label="Toggle Sidebar", command=self._toggle_sidebar)
        if self.config.get("agents_enabled"):
            view_menu.add_command(label="Toggle DXN1 Agents",
                                  command=self.toggle_agents_panel)
        view_menu.add_separator()
        view_menu.add_command(
            label=f"Switch to {'Light' if self.theme.is_dark else 'Dark'} Theme",
            command=self.switch_theme)
        bar_defs.append(("View", view_menu))

        tools_menu = tk.Menu(self.root, **menu_opts)
        tools_menu.add_command(label="Run Project", command=self.run_current,
                               accelerator="F5")
        tools_menu.add_command(label="Stop", command=self.stop_run)
        tools_menu.add_separator()
        tools_menu.add_command(label="Manage Packages…", command=lambda:
                               self.show_sidebar_view("packages"))
        tools_menu.add_command(label="Search in Files…", command=lambda:
                               self.show_sidebar_view("search"))
        tools_menu.add_command(label="Project Hub…", command=self.open_hub)
        if self.config.get("agents_enabled"):
            tools_menu.add_command(label=f"{AGENTS_NAME} Settings…",
                                   command=lambda: AgentSettingsDialog(self))
            tools_menu.add_command(label=f"Connect a Brain…",
                                   command=lambda: ConnectDialog(self))
        bar_defs.append(("Tools", tools_menu))

        # DS2: the workshop — every pocket-knife window in one menu
        workshop_menu = tk.Menu(self.root, **menu_opts)

        def _ws(module, opener):
            """Defensively open a DS2 tool window at click time."""
            def _go():
                try:
                    mod = __import__(f"dxn1_studio.{module}",
                                     fromlist=[opener])
                    getattr(mod, opener)(self.root, self.theme)
                except Exception:  # pragma: no cover — menu stays alive
                    pass
            return _go

        def _open_focus_menu():
            try:
                from .focus import open_focus
                open_focus(self.root, self.theme)
            except Exception:  # pragma: no cover — menu stays alive
                pass

        def _open_hash_menu():
            try:
                from .hasher import open_hasher
                open_hasher(self.root, self.theme,
                            initial=self.project_dir or "",
                            workspace=self.project_dir or "")
            except Exception:  # pragma: no cover — menu stays alive
                pass

        def _open_tree_menu():
            try:
                from .treeexport import open_treeexport
                open_treeexport(self.root, self.theme,
                                initial=self.project_dir or "",
                                workspace=self.project_dir or "")
            except Exception:  # pragma: no cover — menu stays alive
                pass

        def _open_sqlite_menu():
            try:
                from .sqlitelab import open_sqlitelab
                open_sqlitelab(self.root, self.theme,
                               workspace=self.project_dir or "")
            except Exception:  # pragma: no cover — menu stays alive
                pass

        def _open_readability_menu():
            try:
                from .readability import open_readability
                open_readability(
                    self.root, self.theme,
                    text=self.editor.text.get("1.0", "end-1c"),
                    name=os.path.basename(
                        getattr(self, "current_path", "")
                        or getattr(self.editor, "path", "") or "file"))
            except Exception:  # pragma: no cover — menu stays alive
                pass

        def _open_usage_menu():
            try:
                from .usagedash import open_dashboard
                open_dashboard(self, self.theme,
                               workspace=getattr(self, "project_dir", ""),
                               on_log=lambda msg: self.terminal.log(msg))
            except Exception:  # pragma: no cover — menu stays alive
                pass

        workshop_menu.add_command(
            label="Developer Tools…",
            command=_ws("devtools", "open_devtools"))
        workshop_menu.add_separator()
        workshop_menu.add_command(
            label="Cron Explainer…",
            command=_ws("cronexp", "open_cron"))
        workshop_menu.add_command(
            label="Readability Report…",
            command=_open_readability_menu)
        workshop_menu.add_command(
            label="JWT Decoder…",
            command=_ws("jwt", "open_jwt"))
        workshop_menu.add_command(
            label=".env Lint & Mask…",
            command=_ws("envcheck", "open_envlint"))
        workshop_menu.add_command(
            label="Data Generator…",
            command=_ws("gen", "open_generator"))
        workshop_menu.add_command(
            label="SQLite Browser…",
            command=_open_sqlite_menu)
        workshop_menu.add_command(
            label="Directory Tree Export…",
            command=_open_tree_menu)
        workshop_menu.add_command(
            label="Hasher — checksums…",
            command=_open_hash_menu)
        workshop_menu.add_command(
            label="Focus Timer…",
            command=_open_focus_menu)
        # DS2: markdown preview (defensive)
        def _open_md_menu():
            self.open_markdown_preview()
        try:
            workshop_menu.add_command(
                label="Markdown Preview…",
                command=_open_md_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: color kit (defensive)
        def _open_color_menu():
            self.open_colorkit()
        try:
            workshop_menu.add_command(
                label="Color Kit — convert & contrast…",
                command=_open_color_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: REST bench (defensive)
        def _open_rest_menu():
            self.open_restbench()
        try:
            workshop_menu.add_command(
                label="REST Bench — fire HTTP requests…",
                command=_open_rest_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: chart studio (defensive)
        def _open_chart_menu():
            self.open_chart_studio()
        try:
            workshop_menu.add_command(
                label="Chart Studio — paste numbers, see them…",
                command=_open_chart_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: unit converter (defensive)
        def _open_unit_menu():
            self.open_unit_converter()
        try:
            workshop_menu.add_command(
                label="Unit Converter — length/mass/data…",
                command=_open_unit_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: character map (defensive)
        def _open_charmap_menu():
            self.open_charmap()
        try:
            workshop_menu.add_command(
                label="Character Map — browse & copy Unicode…",
                command=_open_charmap_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: textcase (defensive)
        def _open_textcase_menu():
            self.open_textcase()
        try:
            workshop_menu.add_command(
                label="TextCase — snake/camel/kebab/… converter",
                command=_open_textcase_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: passforge (defensive)
        def _open_passforge_menu():
            self.open_passforge()
        try:
            workshop_menu.add_command(
                label="PassForge — strong passwords + entropy…",
                command=_open_passforge_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: numbase (defensive)
        def _open_numbase_menu():
            self.open_numbase()
        try:
            workshop_menu.add_command(
                label="NumBase — bin/oct/dec/hex + bases 2-36…",
                command=_open_numbase_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: csv lab (defensive)
        def _open_csv_menu():
            self.open_csv_lab()
        try:
            workshop_menu.add_command(
                label="CSV Lab — paste & peek tables…",
                command=_open_csv_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: mathpad (defensive)
        def _open_math_menu():
            self.open_mathpad()
        try:
            workshop_menu.add_command(
                label="MathPad — safe expression calculator…",
                command=_open_math_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: bytesnoop (defensive)
        def _open_hex_menu():
            self.open_bytesnoop()
        try:
            workshop_menu.add_command(
                label="ByteSnoop — hexdump & byte inspector…",
                command=_open_hex_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: textdiff (defensive)
        def _open_textdiff_menu():
            self.open_textdiff()
        try:
            workshop_menu.add_command(
                label="Paste Diff — compare two texts…",
                command=_open_textdiff_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: xmlbench (defensive)
        def _open_xml_menu():
            self.open_xmlbench()
        try:
            workshop_menu.add_command(
                label="Markup Bench — pretty & inspect XML…",
                command=_open_xml_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: contrast auditor (defensive)
        def _open_contrast_menu():
            self.open_contrast()
        try:
            workshop_menu.add_command(
                label="Contrast Auditor — WCAG grades for themes…",
                command=_open_contrast_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: cheat sheet exporter (defensive)
        def _open_cheatsheet_menu():
            self.open_cheatsheet()
        try:
            workshop_menu.add_command(
                label="Cheat Sheet — printable HTML export…",
                command=_open_cheatsheet_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: colorblind lab (defensive)
        def _open_cvd_menu():
            self.open_cvdlab()
        try:
            workshop_menu.add_command(
                label="Colorblind Lab — CVD preview of themes…",
                command=_open_cvd_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2: session restore (defensive)
        def _open_session_menu():
            self.open_session_restore()
        try:
            workshop_menu.add_command(
                label="Session Restore — pick up where you left off…",
                command=_open_session_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2 v2.34: save session now (defensive)
        def _save_session_menu():
            self.save_session_now()
        try:
            workshop_menu.add_command(
                label="Save Session Now — snapshot tabs + cursors",
                command=_save_session_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2 v2.37: dependency check (defensive)
        def _deps_menu():
            self._run_depcheck()
        try:
            workshop_menu.add_command(
                label="Dependency Check — imports vs requirements…",
                command=_deps_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        # DS2 v2.39: terminal verbs browser (defensive)
        def _verbs_menu():
            self.open_verbs_window()
        try:
            workshop_menu.add_command(
                label="Terminal Verbs — every command, browsable…",
                command=_verbs_menu)
        except Exception:  # pragma: no cover — menu stays alive
            pass
        workshop_menu.add_separator()
        workshop_menu.add_command(label="Token Usage Dashboard…",
                                  command=_open_usage_menu)
        bar_defs.append(("Workshop", workshop_menu))

        help_menu = tk.Menu(self.root, **menu_opts)
        help_menu.add_command(label="Check for Updates…",
                              command=lambda: self.check_for_updates(manual=True))
        help_menu.add_command(label="Keyboard Shortcuts",
                              command=self.show_shortcuts)
        # DS2: the full cheat sheet — what this studio can do, grouped
        def _open_cheatsheet():
            from .cheatsheet import open_cheatsheet
            open_cheatsheet(self.root, self.theme)
        help_menu.add_command(label="DS2 Cheat Sheet…",
                              command=_open_cheatsheet)
        # DS2: the developer pocket knife — regex, JSON, text, time
        def _open_devtools():
            from .devtools import open_devtools
            open_devtools(self.root, self.theme)
        help_menu.add_command(label="Developer Tools…",
                              command=_open_devtools)
        # DS2: the release notes, rendered (also auto-opens once per tag)
        def _open_whatsnew():
            from .whatsnew import open_whatsnew
            open_whatsnew(self.root, self.theme,
                          on_log=lambda m: self.terminal.log(m))
        help_menu.add_command(label="What's New…", command=_open_whatsnew)
        help_menu.add_command(label="Replay Welcome & Tour",
                              command=self.start_wizard)
        help_menu.add_separator()
        help_menu.add_command(label="About DXN1 STUDIO", command=self.show_about)
        bar_defs.append(("Help", help_menu))

        self._render_menu_bar(bar_defs)

    def _render_menu_bar(self, bar_defs):
        """Paint the themed top bar: brand mark + one Menubutton per menu."""
        t = self.theme
        for child in self.menu_bar.winfo_children():
            # DS2 fix: menus are built as children of the bar but must
            # NEVER be cleared here — the Menubuttons below rebind to
            # them. Destroying them left every menu dead (a real bug
            # caught by the v2.8.0 boot QA: File/Edit/View/Tools/Help
            # all pointed at destroyed Tcl commands).
            if isinstance(child, tk.Menu):
                continue
            child.destroy()
        tk.Label(self.menu_bar, text="◆", bg=t["header"], fg=t.accent,
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=(12, 6))
        tk.Label(self.menu_bar, text="DXN1 STUDIO", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9, "bold")
                 ).pack(side=tk.LEFT)
        tk.Label(self.menu_bar, text=f"v{APP_VERSION}-{APP_CHANNEL}",
                 bg=t["header"], fg=t["text_muted"], font=(FONT_MONO, 8)
                 ).pack(side=tk.LEFT, padx=(8, 0))
        for label, menu in bar_defs:
            btn = tk.Menubutton(self.menu_bar, text=label, menu=menu,
                                bg=t["header"], fg=t["text_secondary"],
                                activebackground=t["hover"],
                                activeforeground=t["text"],
                                font=(FONT_UI, 9), padx=10, pady=6, bd=0,
                                cursor="hand2")
            btn.pack(side=tk.LEFT)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=t["hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=t["header"]))

    def setup_bindings(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-y>", lambda e:
                       self.editor.text.event_generate("<<Redo>>"))
        self.root.bind("<F5>", lambda e: self.run_current())
        self.root.bind("<Control-comma>", lambda e: self.open_settings())
        self.root.bind("<Control-k>", lambda e: self.open_palette())
        self.root.bind("<Control-K>", lambda e: self.editor.delete_line())
        self.root.bind("<Control-D>", lambda e: self.editor.duplicate_line())
        self.root.bind("<Control-slash>", lambda e: self.editor.toggle_comment())
        # DS2: line tools shortcuts
        self.root.bind("<Control-Alt-s>", lambda e: self.apply_line_tool("az"))
        self.root.bind("<Control-Alt-d>", lambda e:
                       self.apply_line_tool("dedupe"))
        self.root.bind("<Control-Alt-h>", lambda e:
                       self.apply_line_tool("shuffle"))
        self.root.bind("<Control-Alt-r>", lambda e:
                       self.apply_line_tool("reverse"))
        self.root.bind("<Control-Shift-V>", lambda e:
                       self.paste_from_history())
        self.root.bind("<Control-g>", lambda e: self.goto_line_dialog())
        self.root.bind("<Alt-Up>", lambda e: self.editor.move_line(-1))
        self.root.bind("<Alt-Down>", lambda e: self.editor.move_line(1))
        self.root.bind("<Control-backslash>", lambda e: self.toggle_split())
        self.root.bind("<Control-Alt-z>", lambda e: self.toggle_zen())
        # DS2 v2.53: the chip menus come to the keyboard — real
        # accelerators for the four statusbar menus (the palette rows
        # advertise them; the v2.47 honest-keys audit polices them)
        self.root.bind("<Control-Alt-g>", lambda e:
                       self._open_chip_menu_keyboard("git"))
        self.root.bind("<Control-Alt-e>", lambda e:
                       self._open_chip_menu_keyboard("deps"))
        self.root.bind("<Control-Alt-w>", lambda e:
                       self._open_chip_menu_keyboard("scribe"))
        self.root.bind("<Control-Alt-a>", lambda e:
                       self._open_chip_menu_keyboard("sesave"))
        self.root.bind("<Control-p>", lambda e: self.open_quick_open())
        self.root.bind("<Control-P>", lambda e: self.open_quick_open())
        self.root.bind("<Control-f>", lambda e: self.toggle_find())
        # Ctrl+H: the Text class binding maps it to backspace, so the
        # editor widget itself gets a break-binding to swallow that, and
        # the toplevel binding covers every other focus target
        self.editor.text.bind("<Control-h>",
                              lambda e: (self.open_replace(), "break")[1])
        self.root.bind("<Control-h>", lambda e: self.open_replace())
        self.root.bind("<Control-w>", lambda e: self.close_active_tab())
        self.root.bind("<Control-Tab>", lambda e: self.cycle_tab(1))
        self.root.bind("<Control-plus>", lambda e: self.change_font_size(1))
        self.root.bind("<Control-equal>", lambda e: self.change_font_size(1))
        self.root.bind("<Control-minus>", lambda e: self.change_font_size(-1))
        # bookmarks: Ctrl+F2 toggle · F2 next · Shift+F2 previous
        self.root.bind("<Control-F2>", lambda e: self.editor.toggle_bookmark())
        self.root.bind("<F2>", lambda e: self.editor.next_bookmark())
        self.root.bind("<Shift-F2>", lambda e: self.editor.prev_bookmark())
        # DS2: Ctrl+R — recent-files fuzzy picker
        self.root.bind("<Control-r>", lambda e: self.open_recent_picker())
        self.root.bind("<Escape>", self._on_escape)

    def open_recent_picker(self):
        """DS2: Quick-Open-style popup over the recent-files list."""
        try:
            from .recents import open_recents
            open_recents(
                self.root, self.theme, self.config,
                on_open=self.open_file,
                root=getattr(self, "project_dir", "") or None,
                on_log=lambda m: self.terminal.log(m))
        except Exception:           # noqa: BLE001 — binding stays safe
            self.terminal.log("recent files: picker unavailable")

    def _on_escape(self, event=None):
        if self.findbar.winfo_ismapped():
            self.toggle_find(show=False)
            return "break"

    def _update_cursor_pos(self, event=None):
        try:
            t = self.editor.text
            line, col = t.index("insert").split(".")
            info = f"Ln {line}, Col {int(col) + 1}"
            sel = t.tag_ranges("sel")
            if sel:
                chars = len(t.get(sel[0], sel[1]))
                lines = t.get(sel[0], sel[1]).count("\n") + 1
                info += f"  ·  {chars} chars selected"
                if lines > 1:
                    info += f" ({lines} lines)"
            total = int(t.index("end-1c").split(".")[0])
            info += f"  ·  {total} lines"
            if self.editor.file_path:
                words = len(t.get("1.0", "end-1c").split())
                if words:
                    info += f"  ·  {words} words"
            self.status_pos.config(text=info)
            self._update_enc_chip()   # DS2 v2.6: encoding + EOL chip
            self._scribe_feed()       # DS2: scribe mini chip
        except Exception:
            pass

    # ---------------------------------------------------- DS2 scribe chip
    def _scribe_feed(self, event=None):
        """DS2: feed the scribe chip (throttled at both layers)."""
        chip = getattr(self, "scribe_chip", None)
        if chip is None:
            return
        try:
            import time as _time
            now = _time.time()
            last = getattr(self, "_scribe_last_try", 0.0)
            if now - last < 2.0:
                return
            self._scribe_last_try = now
            words = len(self.editor.text.get("1.0", "end-1c").split())
            chip.observe(words, now=now)
            self.status_scribe.configure(text=chip.text())
        except Exception:  # noqa: BLE001 — a chip must never kill UI
            pass

    def _scribe_click(self, _event=None):
        """DS2: click the scribe chip for a session summary toast."""
        try:
            chip = self.scribe_chip
            if chip is None:
                return
            from .scribe import format_count
            msg = ("Writing session: %s words · current %d wpm · "
                   "peak %d wpm · %.0f min"
                   % (format_count(chip.words()), round(chip.wpm()),
                      round(chip.peak_wpm()), chip.elapsed_min()))
            if chip.goal_words > 0:
                msg += " · goal %d%%" % chip.goal_pct()
            self.toast(msg, "info")
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------- DS2 v2.6 encoding
    def _update_enc_chip(self):
        """Encoding + line-endings chip on the right of the statusbar.

        Encoding is sniffed once per open (cached in ``_file_encoding``);
        the EOL part is derived cheaply from the widget's first line on
        every cursor update. Never raises.
        """
        try:
            enc = getattr(self, "_file_encoding", "") or "UTF-8"
            t = self.editor.text
            head = t.get("1.0", "2.0 lineend")
            if "\r\n" in head:
                eol = "CRLF"
            elif "\r" in head:
                eol = "CR"
            else:
                eol = "LF"
            text = f"{enc} · {eol}"
            if self.status_enc.cget("text") != text:
                self.status_enc.config(text=text)
        except Exception:  # noqa: BLE001 — a chip must never break typing
            pass

    @staticmethod
    def _sniff_encoding(path):
        """Best-effort encoding label for a file ('UTF-8' as fallback)."""
        try:
            with open(path, "rb") as fh:
                head = fh.read(4)
            if head.startswith(b"\xef\xbb\xbf"):
                return "UTF-8 BOM"
            if head.startswith((b"\xff\xfe", b"\xfe\xff")):
                return "UTF-16"
            with open(path, "rb") as fh:
                fh.read(200_000).decode("utf-8")
            return "UTF-8"
        except UnicodeDecodeError:
            return "non-UTF8"
        except OSError:
            return ""

    def _on_editor_key(self, event=None):
        """App-level hook for editor keystrokes (cursor pos + dirty tab)."""
        self._update_cursor_pos()
        self._mark_dirty()

    # ------------------------------------------------------------ toolbar
    def _chip(self, parent, text, fg=None, accent=False, cmd=None):
        lbl = tk.Label(parent, text=text,
                       bg=self.theme.accent if accent else self.theme["header"],
                       fg="#ffffff" if accent else (fg or
                                                    self.theme["text_secondary"]),
                       font=(FONT_UI, 9, "bold" if accent else "normal"),
                       cursor="hand2", padx=10, pady=6)
        lbl.pack(side=tk.LEFT, padx=(0, 6), pady=4)
        if cmd:
            default_bg = lbl.cget("bg")
            lbl.bind("<Button-1>", lambda e: cmd())
            lbl.bind("<Enter>", lambda e: lbl.config(
                bg=self.theme["hover"] if not accent else self.theme.accent))
            lbl.bind("<Leave>", lambda e: lbl.config(bg=default_bg))
        return lbl

    def _build_toolbar(self):
        t = self.theme
        for child in self.toolbar.winfo_children():
            child.destroy()
        # right-side chip packed FIRST so it never gets squeezed out
        if self.config.get("agents_enabled"):
            self._agents_chip = tk.Label(
                self.toolbar, text="◆ Agents", bg=t["header"],
                fg=t.accent, font=(FONT_UI, 9, "bold"), cursor="hand2",
                padx=10, pady=6)
            self._agents_chip.pack(side=tk.RIGHT, padx=(6, 12), pady=4)
            self._agents_chip.bind("<Button-1>",
                                   lambda e: self.toggle_agents_panel())
        self._chip(self.toolbar, "+ New", cmd=self.new_file)
        self._chip(self.toolbar, "Open", cmd=self.open_file_dialog)
        self._chip(self.toolbar, "Save", cmd=self.save_file)
        tk.Frame(self.toolbar, bg=t["border"], width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=8)
        self._chip(self.toolbar, "▶ Run", accent=True, cmd=self.run_current)
        self._chip(self.toolbar, "■ Stop", fg=t["text_muted"],
                   cmd=self.stop_run)
        tk.Frame(self.toolbar, bg=t["border"], width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=8)
        self._chip(self.toolbar, "Search", cmd=lambda:
                   self.show_sidebar_view("search"))
        self._chip(self.toolbar, "Git", cmd=lambda:
                   self.show_sidebar_view("git"))
        self._chip(self.toolbar, "Packages", cmd=lambda:
                   self.show_sidebar_view("packages"))
        self._chip(self.toolbar, "Export ZIP", cmd=self.export_project_zip)
        self._chip(self.toolbar, "Hub", cmd=self.open_hub)

    # legacy alias — some callers still say toggle_sidebar
    def toggle_sidebar(self):
        self._toggle_sidebar()

    def show_settings_saved(self):
        self.terminal.log("Settings saved.")

    # ------------------------------------------------------------- session
    def _greet(self):
        name = self.config.get("name") or "developer"
        back = not self.first_launch
        self.terminal.log(f"{APP_NAME} v{APP_VERSION}-{APP_CHANNEL} — "
                          f"{APP_TAGLINE}")
        self.terminal.log(f"{'Welcome back' if back else 'Welcome'}, {name}!")
        self.terminal.log("Type 'help' for studio commands — or press Ctrl+K "
                          "for the command palette.")
        if not self.config.get("onboarded"):
            self.terminal.log("First run detected — starting setup…")

    # ------------------------------------------------------------ boot flow
    def run(self):
        self.root.withdraw()
        if self.smoke_test:
            self._after_splash()
            self._schedule_smoke_test()
        elif self.no_splash or not self.config.get("splash_enabled", True):
            self._after_splash()
        else:
            self._splash_active = True
            try:
                Splash(self.root, accent=self.theme.accent, duration_ms=2000,
                       on_done=self._after_splash)
            except Exception:            # noqa: BLE001 — boot must survive
                # the splash is cosmetic; a broken one may never stop the
                # studio from opening (v1.1.6 hotfix — see CHANGELOG)
                import traceback
                traceback.print_exc()
                self._splash_active = False
                self._after_splash()
        self.root.mainloop()

    def _after_splash(self):
        self._splash_active = False
        if self.smoke_test:
            return
        if self.config.needs_onboarding:
            self.start_wizard()
            return
        if self.pending_project:
            path = self.pending_project
            self.pending_project = None
            self._show_main(path)
            return
        if self.config.get("hub_on_startup", True):
            self.open_hub()
        else:
            last = self.config.get("last_project") or ""
            self._show_main(last if os.path.isdir(last) else None)

    def _show_main(self, project_path=None):
        """Deiconify the IDE; optionally dive straight into a workspace."""
        kind = "empty"
        if project_path and os.path.isdir(project_path):
            meta = projects.read_project_meta(project_path)
            kind = meta["kind"]
            self._set_workspace(project_path, kind)
            self._restore_session_tabs(project_path)
        self.root.deiconify()
        if not self.config.get("tour_done"):
            self.root.after(800, self.start_tour)
        self.root.after(1600, self._maybe_show_whatsnew)   # DS2: once/tag
        self.root.after(2500, self._clip_poll)   # DS2: clipboard history
        self.root.after(60000, self._autosave_session)   # DS2 v2.32
        self.root.after(9000, self._deps_watch_poll)   # DS2 v2.39 drift
        self._update_depswatch()                       #   chip first draw
        self._update_gitchip()                         # DS2 v2.40 git chip

    def _clip_poll(self):
        """DS2: background clipboard watcher (never raises)."""
        try:
            if self.clip_ring is None:
                from .clipboard import ClipRing
                self.clip_ring = ClipRing()
            clip = self.root.clipboard_get()
            if clip:
                self.clip_ring.add(clip)
        except Exception:  # noqa: BLE001 — poller stays alive
            pass
        try:
            self.root.after(1500, self._clip_poll)
        except Exception:  # noqa: BLE001 — dying root is fine
            pass

    def paste_from_history(self):
        """DS2: open the clipboard history window."""
        try:
            from .clipboard import open_cliphistory

            def _paste(text):
                try:
                    self.editor.text.insert("insert", text)
                    self.editor.modified = True
                    self.editor.update_line_numbers()
                    self.editor.highlighter.schedule()
                    self._mark_dirty()
                except Exception:  # noqa: BLE001
                    pass

            open_cliphistory(self.root, self.theme,
                             paste_callback=_paste,
                             ring=self.clip_ring)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_markdown_preview(self):
        """DS2: live markdown preview of the current buffer."""
        try:
            from .markprev import open_markdown_preview
            try:
                text = self.editor.text.get("1.0", "end-1c")
            except Exception:  # noqa: BLE001
                text = ""
            path = (getattr(self, "current_path", "")
                    or getattr(self.editor, "path", "") or "")
            open_markdown_preview(self.root, self.theme,
                                  text=text, path=path)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_colorkit(self):
        """DS2: color conversion / contrast workbench."""
        try:
            from .colorkit import open_colorkit
            open_colorkit(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_restbench(self):
        """DS2: HTTP request workbench."""
        try:
            from .restbench import open_restbench
            open_restbench(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_chart_studio(self):
        """DS2: paste-numbers charting window."""
        try:
            from .charts import open_chart_studio
            open_chart_studio(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_unit_converter(self):
        """DS2: unit conversion window."""
        try:
            from .unitconv import open_unit_converter
            open_unit_converter(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_charmap(self):
        """DS2: Unicode character browser."""
        try:
            from .charmap import open_charmap
            open_charmap(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_textcase(self):
        """DS2: identifier case converter."""
        try:
            from .textcase import open_textcase
            open_textcase(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_passforge(self):
        """DS2: password generator window."""
        try:
            from .pwdgen import open_passforge
            open_passforge(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_numbase(self):
        """DS2: number base workbench."""
        try:
            from .numbase import open_numbase
            open_numbase(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_csv_lab(self):
        """DS2: CSV table peeker."""
        try:
            from .csvkit import open_csv_lab
            open_csv_lab(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_mathpad(self):
        """DS2: safe expression calculator."""
        try:
            from .mathpad import open_mathpad
            open_mathpad(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_bytesnoop(self):
        """DS2: hexdump & byte inspector."""
        try:
            from .hexdump import open_bytesnoop
            open_bytesnoop(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_textdiff(self):
        """DS2: compare two pasted texts."""
        try:
            from .textdiff import open_textdiff
            open_textdiff(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_xmlbench(self):
        """DS2: XML pretty/minify/validate bench."""
        try:
            from .xmlbench import open_xmlbench
            open_xmlbench(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_contrast(self):
        """DS2: WCAG contrast auditor for every theme."""
        try:
            from .contrast import open_contrast
            open_contrast(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_cheatsheet(self):
        """DS2: printable HTML cheat sheet of every command."""
        try:
            from .cheatsheet import open_cheatsheet
            open_cheatsheet(self.root, self.theme,
                            commands=TERMINAL_HELP)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_cvdlab(self):
        """DS2: colorblind preview of the current theme."""
        try:
            from .cvdlab import open_cvdlab
            open_cvdlab(self.root, self.theme)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def open_session_restore(self):
        """DS2: browse and restore saved workspace sessions."""
        try:
            from .session import open_session_restore
            open_session_restore(self.root, self.theme, app=self)
        except Exception:  # noqa: BLE001 — menu stays alive
            pass

    def _maybe_show_whatsnew(self):
        """DS2: announce each new version exactly once after an upgrade."""
        try:
            if self.smoke_test or self.config.needs_onboarding:
                return
            from . import whatsnew
            if whatsnew.find_changelog() == "":
                return
            last_seen = self.config.get("last_seen_version") or ""
            from . import APP_VERSION as _ver
            if last_seen == _ver:
                return
            entries = whatsnew.load_entries()
            if whatsnew.new_entries(entries, last_seen):
                whatsnew.open_whatsnew(
                    self.root, self.theme,
                    highlight=entries[0]["version"] if entries else _ver,
                    on_log=lambda m: self.terminal.log(m))
            self.config.set("last_seen_version", _ver)
        except Exception:           # noqa: BLE001 — boot flow must survive
            pass

    def _restore_session_tabs(self, project_path):
        """Reopen the tabs (and active file) saved for this workspace.

        DS2 v2.35: the engine snapshot is tried FIRST — every clean
        exit refreshes it and the 60s autosave keeps it warm in
        between, so a hard crash costs one minute of tabs instead of
        resurrecting a week-old clean-exit record. The legacy
        ``session_tabs`` config entry stays as the fallback for
        pre-v2.30 installs."""
        if not self.config.get("restore_session", True):
            return
        if self._restore_engine_session(project_path):
            return
        sessions = self.config.get("session_tabs") or {}
        data = sessions.get(os.path.abspath(project_path))
        if not data:
            return
        for path in data.get("tabs", []):
            if os.path.isfile(path) and path != self.editor.file_path:
                try:
                    self.open_file(path)
                except Exception:
                    pass
        active = data.get("active")
        if active and os.path.isfile(active):
            try:
                self.open_file(active)
            except Exception:
                pass

    # ------------------------------------------------------------- hub flow
    def open_hub(self):
        if self._hub is not None and self._hub.winfo_exists():
            self._hub.lift()
            return
        preselect = ""
        if self._wizard is None:
            preselect = self.config.get("wizard_first_kind", "")
        self._hub = ProjectHub(self.root, self.config, self.theme,
                               on_open=self._on_hub_open,
                               on_explore=self._on_hub_explore,
                               preselect_kind=preselect)
        if preselect:
            self.config.set("wizard_first_kind", "")

    def _on_hub_open(self, path, kind):
        self._hub = None
        if not self.root.winfo_ismapped():
            self._show_main(path)
        else:
            self._set_workspace(path, kind)
            self.root.deiconify()

    def _on_hub_explore(self):
        self._hub = None
        if not self.root.winfo_ismapped():
            self._show_main(None)
        else:
            self.root.deiconify()

    def open_workspace_dialog(self):
        path = filedialog.askdirectory(title="Open Workspace",
                                       initialdir=self.project_dir
                                       or projects.ensure_projects_root())
        if path:
            self._set_workspace(path,
                                projects.read_project_meta(path)["kind"])

    def _set_workspace(self, path, kind):
        self._ds2_tick("open")
        self.project_dir = os.path.abspath(path)
        self.project_kind = kind
        meta = projects.read_project_meta(path)
        name = meta["name"]
        projects.touch_recent(self.config, path, kind)
        self.sidebar.load_directory(self.project_dir)
        self.search_view.set_workspace(self.project_dir)
        self.status_ws.config(text=f"◆ {name}")
        self.status_branch.config(
            text=f"⎇ {self._git_branch()}" if self._git_branch() else "")
        self.root.title(f"{name} — {APP_NAME} · v{APP_VERSION}-{APP_CHANNEL}")
        self.terminal.log(f"Workspace: {name} ({kind}) — {self.project_dir}")
        # bind the agent to this workspace (fresh jail + conversation)
        if self.agent_panel is not None:
            self.agent_panel.set_workspace(self.project_dir)
        # auto-open the most interesting entry file
        if not self.editor.file_path:
            for cand in ("app.py", "main.py"):
                p = os.path.join(self.project_dir, cand)
                if os.path.isfile(p):
                    self.open_file(p)
                    break

    def _git_branch(self):
        if not self.project_dir:
            return ""
        head = os.path.join(self.project_dir, ".git", "HEAD")
        try:
            with open(head, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read().strip()
            return data.rsplit("/", 1)[-1] if data.startswith("ref:") \
                else "detached"
        except OSError:
            return ""

    def refresh_explorer(self):
        self.sidebar.load_directory(self.project_dir or os.path.expanduser("~"))

    # ---------------------------------------------------------- onboarding
    def start_wizard(self):
        if self._wizard is not None and self._wizard.win.winfo_exists():
            return
        self._tour_done_cleanup()
        self._wizard = WelcomeWizard(self.root, self.config,
                                     on_complete=self._on_wizard_complete)

    def _on_wizard_complete(self, config):
        self._wizard = None
        # if the wizard changed look-and-feel, restart into the new theme
        if config.get("theme") != self.theme.mode or \
                config.get("accent") != self.theme.accent_name:
            self.restart_requested = True
            self.root.after(150, self.root.destroy)
            return
        # honour a mid-wizard opt-in (or opt-out) without a restart
        self.apply_agents_visibility()
        self.editor.set_font_size(config.get("editor_font_size", 11))
        self.terminal.log(f"Setup complete — welcome aboard, "
                          f"{config.get('name') or 'developer'}!")
        self.open_hub()

    def start_tour(self):
        if self._tour is not None:
            return
        self._tour = InteractiveTour(self, self.config)
        self.root.after(350, lambda: self._tour.start()
                        if not self._tour.done else None)

    def _tour_done_cleanup(self):
        if self._tour is not None and not self._tour.done:
            self._tour.finish(skipped=True)
        self._tour = None

    # -------------------------------------------------------------- actions
    # DS2: persistent bookmarks — store + bridges (all defensive)
    def _bookmark_store(self):
        """Lazily-built BookmarkStore for the current workspace."""
        from .bookmarks import BookmarkStore
        ws = getattr(self, "project_dir", "") or None
        store = getattr(self, "_bm_store", None)
        if store is None or store.workspace != (os.path.abspath(ws)
                                                if ws else None):
            store = BookmarkStore(ws)
            self._bm_store = store
        return store

    def _install_bookmark_bridge(self, editor):
        """Persist bookmarks whenever the editor toggles one."""
        try:
            original = editor.toggle_bookmark

            def _toggled(line=None):
                added = original(line)
                try:
                    self._persist_bookmarks()
                except Exception:   # noqa: BLE001 — gutter never breaks
                    pass
                return added

            editor.toggle_bookmark = _toggled
        except Exception:           # noqa: BLE001 — editor stays usable
            pass

    def _persist_bookmarks(self):
        """Write the active editor's bookmarks to the workspace store."""
        from .bookmarks import key_for as _bm_key
        editor = self.editor
        path = getattr(editor, "file_path", "") if editor is not None else ""
        if not path:
            return
        store = self._bookmark_store()
        store.set(_bm_key(path, store.workspace),
                  sorted(getattr(editor, "bookmarks", []) or []))
        store.save()

    def _restore_bookmarks(self, filepath):
        """Load persisted bookmarks for ``filepath`` into the editor."""
        if not filepath:
            if self.editor is not None:
                self.editor.bookmarks = set()
                self.editor.update_line_numbers()
            return
        try:
            from .bookmarks import key_for as _bm_key
            store = self._bookmark_store()
            lines = store.get(_bm_key(filepath, store.workspace))
            self.editor.bookmarks = set(lines)
            self.editor.update_line_numbers()
        except Exception:           # noqa: BLE001 — opening stays safe
            pass

    def new_file(self):
        self.editor.set_content("")
        self.editor.file_path = None
        self.editor.highlighter.set_language(None)
        self.editor.bookmarks = set()   # DS2: untitled starts clean
        self._file_encoding = "UTF-8"   # DS2 v2.6: fresh buffer is UTF-8
        try:
            self.editor.update_line_numbers()
        except Exception:  # noqa: BLE001
            pass
        self.status_file.config(text="Untitled")
        self.terminal.log("Created new file")

    def open_file_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Open File",
            filetypes=[("All Files", "*.*"), ("Python", "*.py"),
                       ("JavaScript", "*.js"), ("HTML", "*.html"),
                       ("CSS", "*.css"), ("Text", "*.txt")])
        if filepath:
            self.open_file(filepath)

    def _remember_cursor(self):
        """DS2 v2.31: stash the current file's insert mark so switching
        buffers (tab click OR opening another file) comes back exactly
        where you left off. Best effort by design — never blocks opens."""
        try:
            if self.editor.file_path:
                self._buffer_cursors[self.editor.file_path] = \
                    str(self.editor.text.index("insert"))
        except Exception:  # noqa: BLE001
            pass

    def open_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8",
                      errors="replace") as fh:
                content = fh.read()
        except Exception as e:
            errors.log_exception(f"open {filepath}")
            messagebox.showerror("Error", f"Failed to open file:\n{e}")
            return
        if filepath != self.editor.file_path:
            self._remember_cursor()   # DS2 v2.31: outgoing buffer cursor
        self._buffers[filepath] = {"content": content, "dirty": False}
        try:  # DS2: keep the outgoing file's bookmarks before swapping
            if self.editor.file_path:
                self._persist_bookmarks()
        except Exception:  # noqa: BLE001 — open never breaks on bookmarks
            pass
        self.editor.set_content(content, path=filepath)
        self._sync_split(content, filepath)
        self._restore_bookmarks(filepath)   # DS2: persistent bookmarks
        self._file_encoding = self._sniff_encoding(filepath)   # DS2 v2.6
        self.status_file.config(text=filepath)
        self._update_cursor_pos()
        self._record_recent_file(filepath)
        self.terminal.log(f"Opened: {filepath}")
        self.add_tab(os.path.basename(filepath), filepath)
        try:  # DS2: plugin on_open hook — broken plugins never break opens
            from . import plugins as _plugins
            _plugins.get_registry().fire_open(
                filepath, content, workspace=self.project_dir)
        except Exception:
            pass

    def open_search_match(self, path, line, col):
        self.open_file(path)
        target = f"{int(line)}.{int(col)}"
        try:
            self.editor.text.mark_set("insert", target)
            self.editor.text.see(target)
            self.editor.text.focus_set()
            self._update_cursor_pos()
        except tk.TclError:
            pass

    def _record_recent_file(self, filepath):
        recents = list(self.config.get("recent_files") or [])
        filepath = os.path.abspath(filepath)
        recents = [r for r in recents if r != filepath]
        recents.insert(0, filepath)
        self.config.set("recent_files", recents[:12])

    def open_quick_open(self):
        if self._quick_open is not None:
            try:
                self._quick_open.destroy()
            except tk.TclError:
                pass
        self._quick_open = QuickOpen(self)

    # ------------------------------------------------------------ split view
    def toggle_split(self):
        t = self.theme
        if self._split is not None:
            try:
                self._split.pack_forget()
            except tk.TclError:
                pass
            self._split.destroy()
            self._split = None
            try:
                self.editor.pack_forget()
                self.editor.pack(fill=tk.BOTH, expand=True)
            except tk.TclError:
                pass
            self.terminal.log("Split view closed.")
            return
        self._split = CodeEditor(self.editor.master, t)
        self._split.set_font_size(
            int(self.config.get("editor_font_size", 11)))
        self._split.set_wrap(bool(self.config.get("word_wrap", False)))
        self._install_bookmark_bridge(self._split)   # DS2: persistence
        self._split.text.bind("<KeyRelease>", self._on_editor_key)
        self._split.text.bind("<ButtonRelease-1>", self._update_cursor_pos)
        self._split.text.bind("<FocusIn>",
                              lambda e: self._focus_split_side())
        if self.editor.file_path and \
                self.editor.file_path in self._buffers:
            self._split.set_content(self.editor.get_content(),
                                    path=self.editor.file_path)
        else:
            self._split.set_content("")
        self.editor.pack_forget()
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                         padx=(0, 3))
        self._split.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.terminal.log("Split view — same buffer, edit on either side.")

    def _focus_split_side(self):
        """Clicked into the split editor — make it the active editor."""
        if self._split is None or self.editor is self._split:
            return
        old, self.editor = self.editor, self._split
        # push the other side's content into the shared buffer, then load
        path = self.editor.file_path
        if path:
            self._buffers[path] = {"content": old.get_content(),
                                   "dirty": True}
            try:  # DS2: swap bookmark sets along with the buffer
                self._persist_bookmarks()
            except Exception:  # noqa: BLE001
                pass
            self.editor.set_content(old.get_content(), path=path)
            self._restore_bookmarks(path)
        self._update_cursor_pos()

    def _sync_split(self, content, path=None):
        """Mirror the active buffer into the split editor (when visible)."""
        if self._split is None or self.editor is self._split:
            return
        try:
            self._split.set_content(content, path=path)
        except tk.TclError:
            pass

    # -------------------------------------------------------------- zen mode
    def toggle_zen(self):
        if not self.zen_mode:
            self._zen_state = (self.sidebar_visible, self.terminal_visible,
                               self.agents_visible,
                               self.findbar.winfo_ismapped())
            if self.sidebar_visible:
                self._toggle_sidebar()
            if self.terminal_visible:
                self.toggle_terminal()
            if self.agents_visible:
                self.toggle_agents_panel()
            if self._zen_state[3]:
                self.toggle_find(show=False)
            self.zen_mode = True
            self.toast("Zen mode — Ctrl+Alt+Z to exit", "info")
        else:
            if self._zen_state:
                side, term, agents, find = self._zen_state
                if side and not self.sidebar_visible:
                    self._toggle_sidebar()
                if term and not self.terminal_visible:
                    self.toggle_terminal()
                if agents and self.agent_panel is not None \
                        and not self.agents_visible:
                    self.toggle_agents_panel()
            self.zen_mode = False
            self.toast("Zen mode off", "info")

    def save_file(self, silent=False):
        if self.editor.file_path:
            try:
                with open(self.editor.file_path, "w", encoding="utf-8") as fh:
                    fh.write(self.editor.get_content())
                if self.editor.file_path in self._buffers:
                    self._buffers[self.editor.file_path] = \
                        {"content": self.editor.get_content(),
                         "dirty": False}
                self._paint_tab_dirty(self.editor.file_path)
                self._sync_split(self.editor.get_content(),
                                 self.editor.file_path)
                self.terminal.log(f"Saved: {self.editor.file_path}")
                try:  # DS2: plugin on_save hook — best effort
                    from . import plugins as _plugins
                    _plugins.get_registry().fire_save(
                        self.editor.file_path, self.editor.get_content(),
                        workspace=self.project_dir)
                except Exception:
                    pass
                if not silent:
                    self.toast("Saved", "success")
                # DS2 v2.39: a saved file is the classic deps drift —
                # the throttle keeps this free for rapid saves
                self._update_depswatch()
                # DS2 v2.40: a saved file is also a git event —
                # the branch chip notices within its throttle
                self._update_gitchip()
            except Exception as e:
                errors.log_exception(f"save {self.editor.file_path}")
                messagebox.showerror("Error", f"Failed to save file:\n{e}")
        else:
            self.save_file_as()

    def save_file_as(self):
        filepath = filedialog.asksaveasfilename(title="Save As",
                                                defaultextension=".txt")
        if filepath:
            self.editor.file_path = filepath
            self._buffers[filepath] = {"content":
                                       self.editor.get_content(),
                                       "dirty": False}
            self.status_file.config(text=filepath)
            self.save_file(silent=True)

    # ---------------------------------------------------------------- tabs
    def add_tab(self, filename, filepath=None):
        filepath = filepath or self.editor.file_path or filename
        if filepath not in self._tab_frames:
            t = self.theme
            tab = tk.Frame(self.tabs_frame, bg=t["header"], cursor="hand2")
            label = tk.Label(tab, text=filename, bg=t["header"], fg=t["text"],
                             font=(FONT_UI, 9))
            label.pack(side=tk.LEFT, padx=10, pady=8)
            close = tk.Label(tab, text="✕", bg=t["header"],
                             fg=t["text_muted"], font=(FONT_UI, 9),
                             cursor="hand2")
            close.pack(side=tk.RIGHT, padx=8)
            bar = tk.Frame(tab, bg=t["header"], height=2)
            bar.pack(side=tk.BOTTOM, fill=tk.X)
            tab.pack(side=tk.LEFT)
            close.bind("<Button-1>", lambda e, p=filepath: self.close_tab(p))
            tab.bind("<Button-2>", lambda e, p=filepath: self.close_tab(p))
            tab.bind("<Button-3>", lambda e, p=filepath, w=tab:
                     self._tab_menu(p, w, e))
            self._tab_frames[filepath] = {"frame": tab, "label": label,
                                          "close": close, "bar": bar}
        self._activate_tab(filepath)

    def _tab_menu(self, filepath, widget, event):
        """Right-click on a tab: close options, copy path, reveal."""
        t = self.theme
        menu = tk.Menu(self.root, tearoff=0, bg=t["sidebar"], fg=t["text"],
                       activebackground=t["hover"],
                       activeforeground=t["text"], font=(FONT_UI, 9))
        menu.add_command(label="Close", accelerator="Ctrl+W",
                         command=lambda: self.close_tab(filepath))
        menu.add_command(label="Close others", command=lambda:
                         self._close_other_tabs(filepath))
        menu.add_command(label="Close all", command=self._close_all_tabs)
        menu.add_separator()
        menu.add_command(label="Copy path", command=lambda:
                         self._copy_path(filepath))
        menu.add_command(label="Reveal in file manager", command=lambda:
                         self.reveal_in_file_manager(filepath))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _close_other_tabs(self, keep):
        for path in list(self._tab_frames):
            if path != keep:
                self.close_tab(path)

    def _close_all_tabs(self):
        for path in list(self._tab_frames):
            self.close_tab(path)

    def reveal_in_file_manager(self, path):
        """Open the OS file manager with the item selected."""
        path = os.path.abspath(path)
        if not os.path.exists(path):
            self.toast("Path no longer exists", "error")
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open",
                                  os.path.dirname(path) or "/"])
        except Exception as exc:  # noqa: BLE001
            self.toast(f"Couldn't open file manager: {exc}", "error")

    def _activate_tab(self, filepath):
        t = self.theme
        for path, w in self._tab_frames.items():
            active = path == filepath
            bg = t["editor"] if active else t["header"]
            w["frame"].config(bg=bg)
            w["label"].config(bg=bg,
                              fg=t["text"] if active else t["text_secondary"])
            w["close"].config(bg=bg)
            w["bar"].config(bg=t.accent if active else bg)
        if filepath and filepath != self.editor.file_path and \
                filepath in self._buffers:
            self._remember_cursor()   # DS2 v2.31: outgoing buffer cursor
            content = self._buffers[filepath]["content"]
            self.editor.set_content(content, path=filepath)
            self._sync_split(content, filepath)
            try:
                pos = self._buffer_cursors.get(filepath)
                if pos:
                    self.editor.text.mark_set("insert", pos)
                    self.editor.text.see("insert")
            except Exception:  # noqa: BLE001
                pass
            self.status_file.config(text=filepath)
            self._update_cursor_pos()

    def _mark_dirty(self, event=None):
        path = self.editor.file_path
        if path and path in self._buffers:
            if not self._buffers[path]["dirty"]:
                self._buffers[path]["dirty"] = True
                self._paint_tab_dirty(path)
        if self.config.get("auto_save", False):
            if self._autosave_job is not None:
                try:
                    self.root.after_cancel(self._autosave_job)
                except Exception:
                    pass
            self._autosave_job = self.root.after(1600,
                                                 lambda: self.save_file(
                                                     silent=True))

    def _paint_tab_dirty(self, path):
        entry = self._tab_frames.get(path)
        if entry is None:
            return
        t = self.theme
        dirty = self._buffers.get(path, {}).get("dirty", False)
        active = path == self.editor.file_path
        bg = t["editor"] if active else t["header"]
        name = os.path.basename(path)
        entry["label"].config(text=f"{'● ' if dirty else ''}{name}", bg=bg)

    def close_active_tab(self):
        if self.editor.file_path:
            self.close_tab(self.editor.file_path)

    def cycle_tab(self, delta):
        paths = list(self._tab_frames)
        if len(paths) < 2:
            return
        try:
            i = paths.index(self.editor.file_path)
        except ValueError:
            i = 0
        self.open_file(paths[(i + delta) % len(paths)]) \
            if paths[(i + delta) % len(paths)] != self.editor.file_path else \
            self._activate_tab(paths[(i + delta) % len(paths)])

    def close_tab(self, filepath):
        entry = self._tab_frames.pop(filepath, None)
        if entry is None:
            return
        entry["frame"].destroy()
        self._buffers.pop(filepath, None)
        self.terminal.log(f"Closed: {os.path.basename(filepath)}")
        if self.editor.file_path == filepath:
            if self._tab_frames:
                last = list(self._tab_frames)[-1]
                self.editor.file_path = None
                self._activate_tab(last)
            else:
                self.editor.set_content("")
                self.editor.file_path = None
                self.editor.highlighter.set_language(None)
                self.status_file.config(text="No file open")
                self.status_pos.config(text="")

    # ------------------------------------------------------------- find bar
    def _build_findbar(self, parent):
        t = self.theme
        bar = tk.Frame(parent, bg=t["header"])
        row = tk.Frame(bar, bg=t["header"])
        row.pack(fill=tk.X, padx=10, pady=6)
        self._find_row = row
        tk.Label(row, text="⌕", bg=t["header"], fg=t.accent,
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT)
        self.find_var = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.find_var, bg=t["editor"],
                         fg=t["text"], insertbackground=t["text"],
                         relief=tk.FLAT, font=(FONT_MONO, 10),
                         highlightthickness=1, highlightbackground=t["border"],
                         highlightcolor=t.accent, width=28)
        entry.pack(side=tk.LEFT, padx=(8, 6), ipady=4)
        entry.bind("<Return>", lambda e: self._find_next(1))
        entry.bind("<KeyRelease>", self._find_live)
        self.find_count = tk.Label(row, text="", bg=t["header"],
                                   fg=t["text_muted"], font=(FONT_UI, 9),
                                   width=10)
        self.find_count.pack(side=tk.LEFT)
        for label, delta in (("↑", -1), ("↓", 1)):
            btn = tk.Label(row, text=label, bg=t["header"],
                           fg=t["text_secondary"], font=(FONT_UI, 10, "bold"),
                           cursor="hand2", padx=8)
            btn.pack(side=tk.LEFT)
            btn.bind("<Button-1>", lambda e, d=delta: self._find_next(d))
        self.find_regex = False
        self.regex_btn = tk.Label(row, text=".*", bg=t["header"],
                                  fg=t["text_muted"],
                                  font=(FONT_MONO, 9, "bold"),
                                  cursor="hand2", padx=7)
        self.regex_btn.pack(side=tk.LEFT)
        self.regex_btn.bind("<Button-1>",
                            lambda e: self._toggle_find_regex())
        self.replace_chevron = tk.Label(row, text="⌄ replace", bg=t["header"],
                                        fg=t["text_secondary"],
                                        font=(FONT_UI, 9), cursor="hand2",
                                        padx=8)
        self.replace_chevron.pack(side=tk.LEFT)
        self.replace_chevron.bind("<Button-1>",
                                  lambda e: self.toggle_replace())
        x = tk.Label(row, text="✕", bg=t["header"], fg=t["text_muted"],
                     font=(FONT_UI, 10), cursor="hand2", padx=8)
        x.pack(side=tk.RIGHT)
        x.bind("<Button-1>", lambda e: self.toggle_find(show=False))

        # ---- replace row (hidden until the chevron or Ctrl+H) ----
        self.replace_row = tk.Frame(bar, bg=t["header"])
        tk.Label(self.replace_row, text="→", bg=t["header"],
                 fg=t["text_muted"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT)
        self.replace_var = tk.StringVar()
        rentry = tk.Entry(self.replace_row, textvariable=self.replace_var,
                          bg=t["editor"], fg=t["text"],
                          insertbackground=t["text"], relief=tk.FLAT,
                          font=(FONT_MONO, 10), highlightthickness=1,
                          highlightbackground=t["border"],
                          highlightcolor=t.accent, width=28)
        rentry.pack(side=tk.LEFT, padx=(8, 6), ipady=4)
        rentry.bind("<Return>", lambda e: self._replace_current())
        rbtn = tk.Label(self.replace_row, text="Replace", bg=t["card"],
                        fg=t["text"], font=(FONT_UI, 9, "bold"),
                        cursor="hand2", padx=9, pady=3)
        rbtn.pack(side=tk.LEFT, padx=2)
        rbtn.bind("<Button-1>", lambda e: self._replace_current())
        rabtn = tk.Label(self.replace_row, text="Replace all", bg=t["card"],
                         fg=t["text"], font=(FONT_UI, 9, "bold"),
                         cursor="hand2", padx=9, pady=3)
        rabtn.pack(side=tk.LEFT, padx=2)
        rabtn.bind("<Button-1>", lambda e: self._replace_all())
        self.replace_status = tk.Label(self.replace_row, text="", bg=t["header"],
                                       fg=t["text_muted"], font=(FONT_UI, 9))
        self.replace_status.pack(side=tk.LEFT, padx=6)
        return bar

    def toggle_replace(self, show=None):
        """Show/hide the replace row under the find bar."""
        visible = self.replace_row.winfo_ismapped()
        if show is None:
            show = not visible
        if show and not visible:
            self.replace_row.pack(fill=tk.X, padx=10, pady=(0, 6),
                                  after=self._find_row)
            self.replace_chevron.config(text="⌃ replace")
        elif not show and visible:
            self.replace_row.pack_forget()
            self.replace_chevron.config(text="⌄ replace")
            self.replace_status.config(text="")

    def open_replace(self):
        """Ctrl+H — find bar with the replace row visible."""
        if not self.findbar.winfo_ismapped():
            self.toggle_find(show=True)
        self.toggle_replace(show=True)
        for w in self.replace_row.winfo_children():
            if isinstance(w, tk.Entry):
                w.focus_set()
                break

    def _replace_current(self):
        needle, repl = self.find_var.get(), self.replace_var.get()
        if not needle:
            return
        if self.editor.replace_current(needle, repl,
                                       regex=self.find_regex):
            self.replace_status.config(text="replaced 1",
                                       fg=self.theme.accent)
        else:
            self.replace_status.config(text="no selection — pick a hit first",
                                       fg=self.theme["text_muted"])
        self._find_live()

    def _replace_all(self):
        needle, repl = self.find_var.get(), self.replace_var.get()
        if not needle:
            return
        count = self.editor.replace_all(needle, repl,
                                        regex=self.find_regex)
        if count < 0:
            self.replace_status.config(text="bad regex", fg="#f87171")
            return
        self.replace_status.config(
            text=(f"replaced {count}" if count else "no hits"),
            fg=(self.theme.accent if count else self.theme["text_muted"]))
        self._find_live()

    def toggle_find(self, show=None):
        visible = self.findbar.winfo_ismapped()
        if show is None:
            show = not visible
        if show and not visible:
            self.findbar.pack(fill=tk.X, before=self.editor)
            self.find_var.set("")
            self.find_count.config(text="")
            for w in self.findbar.winfo_children():
                for c in w.winfo_children():
                    if isinstance(c, tk.Entry):
                        c.focus_set()
                        break
        elif not show and visible:
            self.editor.clear_find()
            self.replace_row.pack_forget()
            self.replace_chevron.config(text="⌄ replace")
            self.findbar.pack_forget()
            self.editor.text.focus_set()

    def _toggle_find_regex(self):
        """Flip the find bar into regex mode (.*) and re-run live."""
        self.find_regex = not self.find_regex
        self.regex_btn.config(
            fg=self.theme.accent if self.find_regex
            else self.theme["text_muted"])
        self._find_live()

    def _find_live(self, event=None):
        if event and event.keysym in ("Return", "Escape", "Up", "Down"):
            return
        needle = self.find_var.get()
        if not needle:
            self.editor.clear_find()
            self.find_count.config(text="")
            return
        count = self.editor.find(needle, regex=self.find_regex)
        if count < 0:
            self.find_count.config(text="bad regex", fg="#f87171")
            return
        self.find_count.config(
            text=f"{count} hit{'s' if count != 1 else ''}"
            if count else "no hits",
            fg=self.theme["text_muted"])

    def _find_next(self, delta):
        needle = self.find_var.get()
        if needle:
            self.editor.find(needle, backwards=delta < 0,
                             regex=self.find_regex)

    # ------------------------------------------------------------- packages
    def open_packages(self, autostart=None):
        self.show_sidebar_view("packages")
        if autostart:
            self.packages_view.install_packages(autostart)
        return self.packages_view

    # -------------------------------------------------------------- export
    def export_project_zip(self):
        src = self.project_dir
        if not src:
            src = filedialog.askdirectory(title="Choose a workspace to export")
            if not src:
                return
        if self.project_kind == "flask":
            export.ensure_requirements(src, "flask")
        dest = filedialog.asksaveasfilename(
            title="Export Project as ZIP", defaultextension=".zip",
            initialfile=export.default_zip_name(src))
        if not dest:
            return
        try:
            path, count = export.export_project_zip(src, dest)
        except Exception as e:
            errors.log_exception("export zip")
            messagebox.showerror("Export", f"Export failed:\n{e}")
            return
        self.terminal.log(f"Exported {count} files → {path}")
        self.toast(f"Exported {count} files", "success")

    def export_current_file(self):
        if not self.editor.file_path:
            self.save_file_as()
            if not self.editor.file_path:
                return
        self.save_file(silent=True)
        dest = filedialog.asksaveasfilename(
            title="Export Current File As",
            initialfile=os.path.basename(self.editor.file_path))
        if not dest:
            return
        try:
            export.export_file_bytes(self.editor.get_content(), dest)
        except Exception as e:
            errors.log_exception("export file")
            messagebox.showerror("Export", f"Export failed:\n{e}")
            return
        self.terminal.log(f"Exported current file → {dest}")

    # ------------------------------------------------------------- run/stop
    def run_current(self):
        """F5 — run the active file, or the workspace entry script."""
        self._ds2_tick("run")
        target = None
        if self.editor.file_path and self.editor.file_path.endswith(".py"):
            target = self.editor.file_path
        elif self.project_dir:
            for cand in ("app.py", "main.py"):
                p = os.path.join(self.project_dir, cand)
                if os.path.isfile(p):
                    target = p
                    break
        if not target:
            self.terminal.log("Nothing to run — open a Python file first.")
            self.toast("Nothing to run", "error")
            return
        self.run_file(target)

    def run_file(self, path):
        path = os.path.abspath(path)
        if path == self.editor.file_path:
            self.save_file(silent=True)
        self._start_process([sys.executable, path], shell=False,
                            cwd=os.path.dirname(path))

    def run_command(self, cmd):
        self._start_process(cmd, shell=True,
                            cwd=self.project_dir or os.path.expanduser("~"))

    def _start_process(self, cmd, shell=False, cwd=None):
        self.stop_run(silent=True)
        self.terminal.log(f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
        self.terminal.log_raw("")
        try:
            self.proc = subprocess.Popen(
                cmd, shell=shell, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
        except Exception as e:
            self.terminal.log(f"failed to start: {e}")
            return
        self.status_ready.config(text="● Running", fg=self.theme.accent)

        def pump():
            try:
                for line in self.proc.stdout:
                    self._proc_q.put(line)
                code = self.proc.wait()
            except Exception as exc:  # noqa: BLE001
                self._proc_q.put(f"[process error: {exc}]\n")
                code = 1
            self._proc_q.put(("exit", code))
        threading.Thread(target=pump, daemon=True).start()
        self._poll_process()

    def _poll_process(self):
        done = False
        try:
            while True:
                item = self._proc_q.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "exit":
                    code = item[1]
                    self.terminal.log_raw("")
                    self.terminal.log(f"Process finished with exit code {code}")
                    self.status_ready.config(text="● Ready",
                                             fg=self.theme["success"])
                    # DS2: a crash is a question — offer the answer
                    if code != 0 and self._last_error_text():
                        self.terminal.log(
                            "stuck? type \u0060explain\u0060 and the agent "
                            "will walk through that traceback")
                    done = True
                    continue
                self.terminal.log_raw(item.rstrip("\n"))
        except queue.Empty:
            pass
        if not done:
            self.root.after(120, self._poll_process)

    def _last_error_text(self, max_lines=60):
        """The most recent traceback/pytest/unittest error block, or ''."""
        try:
            text = self.terminal.output.get("end-%dc" % 20000, "end-1c")
        except Exception:           # noqa: BLE001 — terminal stays alive
            return ""
        return extract_error_block(text, max_lines=max_lines)

    def explain_last_error(self):
        """DS2: hand the last traceback to the agent chat (or clipboard)."""
        err = self._last_error_text()
        if not err:
            self.terminal.log("no recent error found in the terminal")
            return
        prompt = ("This traceback just happened in my terminal. Explain "
                  "the root cause in plain words, point at the exact "
                  "line to change, and give a minimal fix:\n\n" + err)
        try:
            from .prompts import insert_into_agent
            if self.agent_panel is not None and \
                    insert_into_agent(self.agent_panel, prompt):
                self.terminal.log(
                    "traceback sent to the agent — press Enter to ask")
                return
        except Exception:           # noqa: BLE001 — fall through
            pass
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(prompt)
            self.terminal.log(
                "no agent panel open — explain-prompt copied to clipboard")
        except Exception:           # noqa: BLE001
            pass

    def stop_run(self, silent=False):
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            if not silent:
                self.terminal.log("Stopped.")
        elif not silent:
            self.terminal.log("Nothing is running.")

    # ------------------------------------------------------- agent callbacks
    def agent_execute_command(self, cmd):
        """Run an agent-proposed command inside the workspace jail.

        Called from the agent's worker thread; UI updates are marshalled
        back through ``root.after``. Returns (exit_code, combined_output).
        """
        cwd = self.project_dir or os.path.expanduser("~")
        self.root.after(0, lambda: self.terminal.log(f"$ {cmd}"))
        try:
            proc = subprocess.run(cmd, shell=True, cwd=cwd,
                                  capture_output=True, text=True, timeout=60)
            out = ((proc.stdout or "") + (proc.stderr or "")).strip()
            code = proc.returncode
        except subprocess.TimeoutExpired:
            out, code = "(timed out after 60s)", 124
        except Exception as exc:  # noqa: BLE001
            out, code = f"(failed to start: {exc})", 1
        tail = out[-4000:]
        self.root.after(0, lambda: self.terminal.log_raw(
            tail if tail else f"(exit {code}, no output)"))
        return code, out

    def chat_code_to_editor(self, code):
        """Drop an agent code block into a fresh untitled editor tab."""
        self.new_file()
        if code:
            self.editor.set_content(code if code.endswith("\n")
                                    else code + "\n")
            self._update_cursor_pos()

    def agent_on_written(self, path):
        """Agent touched a file — refresh explorer, reload if it's open."""
        def ui():
            try:
                if os.path.isdir(self.project_dir or ""):
                    self.sidebar.load_directory(self.project_dir)
                self.terminal.log(f"Agents wrote: {os.path.basename(path)}")
                if self.editor.file_path and \
                        os.path.abspath(self.editor.file_path) == \
                        os.path.abspath(path):
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as fh:
                        self.editor.set_content(fh.read())
            except Exception:
                errors.log_exception("agent_on_written", quiet=True)
        self.root.after(0, ui)

    # --------------------------------------------------- terminal commands
    def handle_terminal_command(self, text):
        low = text.strip().lower()
        if re.fullmatch(r"dxn1[\s_-]*studio", low):
            self.relaunch_with_splash()
            return
        if low in ("help", "?"):
            self.terminal.log("Studio commands:")
            for cmd, desc in TERMINAL_HELP:
                self.terminal.log(f"  {cmd:<18} — {desc}")
            return
        if low.startswith("help "):
            # DS2 v2.37/2.38: help for one verb — `help deps` — with a
            # fallback into the palette's own command registry
            rows = matching_help_rows(text[5:])
            if not rows:
                prow = matching_help_rows(
                    text[5:], rows=palette_help_rows(self))
                rows = [("palette: " + c, d or "palette command")
                        for c, d in prow]
            if rows:
                for cmd, desc in rows:
                    self.terminal.log(f"  {cmd:<18} — {desc}")
            else:
                self.terminal.log(f"No help for '{text[5:].strip()}' — "
                                  "type `help` for the full list")
            return
        if low == "clear":
            self.terminal.clear()
            return
        if low == "run":
            self.run_current()
            return
        if low == "stop":
            self.stop_run()
            return
        if low in ("packages", "pkg"):
            self.open_packages()
            return
        if low == "todo":
            self.scan_todos()
            return
        if low == "split":
            self.toggle_split()
            return
        if low == "zen":
            self.toggle_zen()
            return
        if low == "recent":
            recents = [r for r in (self.config.get("recent_files") or [])
                       if os.path.isfile(r)][:8]
            if not recents:
                self.terminal.log("No recent files yet.")
            for i, r in enumerate(recents, 1):
                self.terminal.log(f"  {i}. {r}")
            return
        if low == "explain":
            # DS2: hand the last traceback to the agent chat
            self.explain_last_error()
            return
        if low == "stats":
            # DS2: one-line file summary in the terminal, window via palette
            try:
                from .filestats import scan_workspace, summary_lines
                line1, line2 = summary_lines(scan_workspace(
                    getattr(self, "project_dir", "") or os.getcwd()))
                self.terminal.log(f"File statistics — {line1}")
                self.terminal.log(f"  {line2}")
                self.terminal.log("  full report: palette → File statistics")
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"stats failed: {exc}")
            return
        if low in ("tools", "devtools", "regex"):
            # DS2: open the developer tools window (regex/JSON/text/time)
            try:
                from .devtools import open_devtools
                win = open_devtools(self.root, self.theme)
                sel = self.editor.text.get("sel.first", "sel.last") if low == "regex" else ""
                if sel:
                    win.rx_pattern_var.set(sel.strip())
                self.terminal.log("Developer tools opened — regex, JSON, "
                                  "text, time")
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"tools failed: {exc}")
            return
        if low == "cron" or low.startswith("cron "):
            # DS2: decode a cron expression (or open the explainer empty)
            try:
                from .cronexp import open_cron
                arg = text[4:].strip() if len(text) > 4 else ""
                open_cron(self.root, self.theme, initial=arg)
                self.terminal.log("Cron explainer opened" +
                                  (f" — {arg}" if arg else ""))
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"cron failed: {exc}")
            return
        if low in ("readability", "prose"):
            # DS2: how hard is the current file to read?
            try:
                from .readability import open_readability
                open_readability(self.root, self.theme,
                                 text=self.editor.text.get("1.0", "end-1c"),
                                 name=os.path.basename(
                                     getattr(self, "current_path", "")
                                     or getattr(self.editor, "path", "")
                                     or "file"))
                self.terminal.log("Readability report opened")
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"readability failed: {exc}")
            return
        if low == "jwt" or low.startswith("jwt "):
            # DS2: decode a JWT from the terminal (or selection)
            try:
                from .jwt import open_jwt
                arg = text[3:].strip() if len(text) > 3 else ""
                if not arg:
                    arg = self.editor.text.get("sel.first", "sel.last") \
                        .strip()
                open_jwt(self.root, self.theme, initial=arg)
                self.terminal.log("JWT decoder opened" +
                                  (f" — {arg[:24]}…" if arg else ""))
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"jwt failed: {exc}")
            return
        if low in ("env", "envlint", "dotenv"):
            # DS2: lint the workspace .env and produce a masked copy
            try:
                from .envcheck import open_envlint
                win = open_envlint(self.root, self.theme)
                win._load_file()
                self.terminal.log(".env lint opened — loaded the "
                                  "workspace .env if present")
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"env failed: {exc}")
            return
        if low in ("gen", "generate", "uuid"):
            # DS2: test data & ID generator
            try:
                from .gen import open_generator
                open_generator(self.root, self.theme)
                self.terminal.log("Data generator opened — UUIDs, ULIDs, "
                                  "nanoids, passwords, fake users")
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"gen failed: {exc}")
            return
        if low in ("db", "sqlite") or low.startswith("db "):
            # DS2: SQLite Lab — browse tables, schema, run queries
            try:
                from .sqlitelab import open_sqlitelab, find_databases
                arg = text[3:].strip() if len(text) > 3 else ""
                if arg and not os.path.isfile(arg):
                    cand = os.path.join(self.project_dir or "", arg)
                    arg = cand if os.path.isfile(cand) else arg
                if arg and not os.path.isfile(arg):
                    self.terminal.log(f"no such database: {arg}")
                    arg = ""
                hits = find_databases(self.project_dir or "")
                open_sqlitelab(self.root, self.theme, initial=arg,
                               workspace=self.project_dir or "")
                if arg:
                    self.terminal.log(f"SQLite Lab opened — {arg}")
                elif hits:
                    self.terminal.log(
                        f"SQLite Lab opened — {len(hits)} database(s) "
                        f"in workspace (try: {os.path.basename(hits[0])})")
                else:
                    self.terminal.log("SQLite Lab opened — no .db files "
                                      "in the workspace, use Open…")
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"db failed: {exc}")
            return
        if low == "tree" or low.startswith("tree "):
            # DS2: directory tree export (optional path argument)
            try:
                from .treeexport import open_treeexport
                arg = text[5:].strip() if len(text) > 5 else ""
                if arg and not os.path.isdir(arg):
                    cand = os.path.join(self.project_dir or "", arg)
                    arg = cand if os.path.isdir(cand) else ""
                if arg and not os.path.isdir(arg):
                    self.terminal.log(f"no such directory: {arg}")
                    arg = ""
                open_treeexport(self.root, self.theme, initial=arg,
                                workspace=self.project_dir or "")
                self.terminal.log("Tree export opened" +
                                  (f" — {arg}" if arg else " — workspace"))
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"tree failed: {exc}")
            return
        if low == "hash" or low.startswith("hash "):
            # DS2: hasher lab (optional file/folder argument)
            try:
                from .hasher import open_hasher
                arg = text[5:].strip() if len(text) > 5 else ""
                if arg and not os.path.exists(arg):
                    cand = os.path.join(self.project_dir or "", arg)
                    arg = cand if os.path.exists(cand) else ""
                if arg and not os.path.exists(arg):
                    self.terminal.log(f"no such file or folder: {arg}")
                    arg = ""
                open_hasher(self.root, self.theme, initial=arg,
                            workspace=self.project_dir or "")
                self.terminal.log("Hasher opened" +
                                  (f" — {arg}" if arg else ""))
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"hash failed: {exc}")
            return
        if low == "focus" or low.startswith("focus "):
            # DS2: pomodoro focus timer (optional minutes argument)
            try:
                from .focus import open_focus
                arg = text[6:].strip() if len(text) > 6 else ""
                if arg and not arg.isdigit():
                    arg = ""
                open_focus(self.root, self.theme, initial=arg)
                self.terminal.log("Focus timer opened" +
                                  (f" — {arg} minute blocks" if arg
                                   else " — 25/5 cycles"))
            except Exception as exc:  # noqa: BLE001 — terminal stays alive
                self.terminal.log(f"focus failed: {exc}")
            return
        if low.startswith("sort"):
            # DS2: line tools on the current selection or buffer
            mode = text[5:].strip() if len(text) > 5 else "az"
            aliases = {"a-z": "az", "up": "az", "down": "za", "z-a": "za",
                       "unique": "dedupe", "random": "shuffle",
                       "rev": "reverse", "reverse": "reverse",
                       "trim": "trim", "len": "len", "az": "az",
                       "za": "za", "dedupe": "dedupe", "shuffle":
                       "shuffle"}
            mode = aliases.get(mode)
            if not mode:
                self.terminal.log("usage: sort az|za|len|dedupe|"
                                  "shuffle|reverse|trim")
                return
            self.apply_line_tool(mode)
            self.terminal.log(f"lines: {mode} applied" +
                              (" (selection)" if
                               self.editor.text.tag_ranges("sel")
                               else " (whole file)"))
            return
        if low == "clip":
            # DS2: clipboard history window
            self.paste_from_history()
            self.terminal.log("Clipboard history opened")
            return
        if low in ("md", "preview", "markdown"):
            # DS2: markdown preview window
            self.open_markdown_preview()
            self.terminal.log("Markdown preview opened — edit left, "
                              "render right, F5 re-renders")
            return
        if low in ("color", "colorkit", "color kit"):
            # DS2: color conversion workbench
            self.open_colorkit()
            self.terminal.log("Color Kit opened — paste a hex, get "
                              "rgb/hsl/contrast/ramps")
            return
        if low in ("rest", "http", "restbench"):
            # DS2: HTTP request workbench
            self.open_restbench()
            self.terminal.log("REST Bench opened — Ctrl+Enter sends, "
                              "responses pretty-print JSON")
            return
        if low in ("chart", "charts", "plot"):
            # DS2: chart studio window
            self.open_chart_studio()
            self.terminal.log("Chart Studio opened — paste numbers on "
                              "the left, charts redraw live")
            return
        if low in ("unit", "units", "convert"):
            # DS2: unit converter window
            self.open_unit_converter()
            self.terminal.log("Unit Converter opened — length/mass/"
                              "temperature/data/time/speed, offline")
            return
        if low in ("charmap", "char", "unicode"):
            # DS2: character map window
            self.open_charmap()
            self.terminal.log("Character Map opened — click a glyph "
                              "to copy it; search by block or U+code")
            return
        if low in ("case", "textcase"):
            # DS2: identifier case converter window
            self.open_textcase()
            self.terminal.log("TextCase opened — snake/camel/pascal/"
                              "kebab/constant/title/dot/flat, click "
                              "a row to copy")
            return
        if low in ("passgen", "password", "passforge"):
            # DS2: password generator window
            self.open_passforge()
            self.terminal.log("PassForge opened — secrets CSPRNG, "
                              "entropy meter, click generate")
            return
        if low in ("base", "numbase", "hex"):
            # DS2: number base workbench
            self.open_numbase()
            self.terminal.log("NumBase opened — type a number, read "
                              "every base + bit inspector")
            return
        if low in ("csv", "csvlab", "tsv"):
            # DS2: csv table peeker
            self.open_csv_lab()
            self.terminal.log("CSV Lab opened — paste csv/tsv, the "
                              "table renders; copy back as TSV")
            return
        if low in ("calc", "math", "mathpad"):
            # DS2: safe expression calculator
            self.open_mathpad()
            self.terminal.log("MathPad opened — type 2+2*10, assign x "
                              "= 5, use _ for the last answer")
            return
        if low in ("hexdump", "bytesnoop", "bytes"):
            # DS2: hexdump & byte inspector
            self.open_bytesnoop()
            self.terminal.log("ByteSnoop opened — paste text or hex, "
                              "read the bytes with a stats line")
            return
        if low in ("textdiff", "diff2", "pastediff"):
            # DS2: compare two pasted texts
            self.open_textdiff()
            self.terminal.log("Paste Diff opened — old vs new, word/"
                              "char/line modes, [-…-] {+…+} marks")
            return
        if low in ("xml", "xmlbench", "markup"):
            # DS2: XML pretty/minify/validate bench
            self.open_xmlbench()
            self.terminal.log("Markup Bench opened — paste XML, "
                              "pretty/minify it, live validation")
            return
        if low in ("contrast", "a11y", "wcag", "audit"):
            # DS2: WCAG contrast auditor over all themes
            self.open_contrast()
            self.terminal.log("Contrast Auditor opened — 13 text "
                              "pairs graded per theme, fixes "
                              "suggested below AA")
            return
        if low in ("cheat", "cheatsheet", "man"):
            # DS2: printable HTML cheat sheet export
            self.open_cheatsheet()
            self.terminal.log("Cheat Sheet opened — preview here, "
                              "save a print-ready HTML copy from "
                              "the button")
            return
        if low in ("cvd", "colorblind", "vision"):
            # DS2: colorblind preview of the current theme
            self.open_cvdlab()
            self.terminal.log("Colorblind Lab opened — deuteranopia, "
                              "protanopia, tritanopia, achromatopsia "
                              "previews with contrast verdicts")
            return
        if low in ("session save", "save session", "ssave"):
            # DS2 v2.33: snapshot the session on demand
            self.save_session_now()
            return
        if low in ("session", "sessions", "resume"):
            # DS2: session restore — manager window over saved sessions
            try:
                from . import session as _ds2_session
                _n = len(_ds2_session.list_sessions())
            except Exception:
                _n = 0
            self.open_session_restore()
            self.terminal.log(f"Session Restore opened — {_n} saved "
                              "workspace(s) on disk")
            return
        if low == "lang" or low.startswith("lang "):
            # DS2: switch the UI language pack (i18n activation)
            from . import i18n as _i18n
            arg = text[4:].strip()
            if arg == "edit" or arg.startswith("edit "):
                # DS2 v2.55 — the translation desk: edit any pack
                # beside its English source and save a user pack
                # that overrides built-ins. No code names the
                # chooser; a code opens that desk directly.
                rest = arg[4:].strip().lower()
                if not rest:
                    self._open_lang_desk()
                    return
                import re as _re
                if not _re.match(r"^[a-z0-9][a-z0-9_-]{0,15}$", rest):
                    self.terminal.log(
                        "'%s' is not a pack code — lowercase letters, "
                        "digits, _ or - (e.g. es, pt_br)" % rest)
                    return
                if rest == "en":
                    self.terminal.log(
                        "English is the source of truth — it is "
                        "translated FROM, not edited")
                    return
                self._open_lang_desk(rest)
                return
            if arg == "diff" or arg.startswith("diff "):
                # DS2 v2.56 — the honest ledger: coverage can flatter
                # (a pack seeded from English and never edited shows
                # 100% while every string still reads English); the
                # diff splits real translations from untouched seeds
                from . import langedit as _le
                rest = arg[4:].strip().lower()
                code = rest or _i18n.current()
                if code == "en":
                    self.terminal.log(
                        "English is the source of truth — it does not "
                        "differ from itself; name a pack (lang diff "
                        "<code> — available: %s)"
                        % ", ".join(c for c in _i18n.available()
                                    if c != "en"))
                    return
                if code not in _i18n.available():
                    self.terminal.log(
                        "unknown language '%s' — available: %s"
                        % (code, ", ".join(_i18n.available())))
                    return
                try:
                    d = _le.pack_diff(code)
                except Exception:  # noqa: BLE001 — a verb never raises
                    d = None
                if not d:
                    self.terminal.log("lang diff unavailable here")
                    return
                self.terminal.log(
                    "lang diff %s — %s [%s]: %d real translation%s, "
                    "%d untouched seed%s, %d missing, %d stale · "
                    "%d%% real"
                    % (code, d["name"],
                       "user" if os.path.exists(
                           os.path.join(_i18n.LANG_DIR,
                                        code + ".json"))
                       else ("built-in" if code in _i18n.PACKS
                             else "new"),
                       len(d["real"]),
                       "" if len(d["real"]) == 1 else "s",
                       len(d["seeds"]),
                       "" if len(d["seeds"]) == 1 else "s",
                       len(d["missing"]), len(d["stale"]),
                       d["real_pct"]))
                if d["seeds"]:
                    sample = ", ".join(d["seeds"][:8])
                    if len(d["seeds"]) > 8:
                        sample += ", …"
                    self.terminal.log(
                        "  untouched (byte-identical to English — "
                        "seeded, maybe, but not translated): " + sample)
                if d["unsafe"]:
                    self.terminal.log(
                        "  NOT highlight-safe: "
                        + ", ".join(d["unsafe"][:8]))
                if d["stale"]:
                    self.terminal.log(
                        "  stale (the source dropped these): "
                        + ", ".join(d["stale"][:8]))
                self.terminal.log(
                    "real_pct cannot lie: translations that differ "
                    "from English, over the English total — edit the "
                    "untouched ones in `lang edit %s`" % code)
                return
            if arg == "check" or arg.startswith("check "):
                # DS2 v2.58 — the pack gets a checkup: a pre-flight
                # before sharing or importing. A code reviews the
                # installed pack (built-ins + the user pack on disk —
                # what the runtime speaks); a path to a .json file
                # reviews the file itself, unreadable ones included.
                # The checkup reads the way an import WOULD and
                # reports before anything moves.
                from . import langedit as _le
                rest = arg[5:].strip()
                if not rest:
                    cur = _i18n.current()
                    if cur == "en":
                        self.terminal.log(
                            "bare lang check reviews the current "
                            "language — English is the source and has "
                            "nothing to check; name a pack or a .json "
                            "file (lang check <code|file>)")
                        return
                    rest = cur
                code = rest.lower()
                if code in _i18n.available():
                    try:
                        rep = _le.check_pack(code)
                    except Exception:  # noqa: BLE001 — a verb never raises
                        rep = None
                    if not rep:
                        self.terminal.log("lang check unavailable here")
                        return
                    kind = ("user" if os.path.exists(
                        os.path.join(_i18n.LANG_DIR,
                                     code + ".json"))
                        else ("built-in" if code in _i18n.PACKS
                              else "new"))
                    self._emit_checkup(
                        "lang check %s — %s [%s]" % (
                            code, rep["name"], kind), rep,
                        "share it with lang pack %s, or edit the "
                        "findings in the desk (lang edit %s)"
                        % (code, code),
                        diff_code=code)
                    return
                path = os.path.expanduser(rest)
                if os.path.isfile(path):
                    try:
                        frep = _le.check_pack_file(path)
                    except Exception:  # noqa: BLE001
                        frep = None
                    if not frep:
                        self.terminal.log("lang check unavailable here")
                        return
                    if not frep.get("ok"):
                        self.terminal.log(
                            "lang check %s — unreadable (%s) — there "
                            "is nothing to import from a file that "
                            "will not open"
                            % (rest, frep.get("error")))
                        return
                    self._emit_checkup(
                        "lang check %s" % rest, frep,
                        "import it from the desk (lang edit → Import "
                        "pack), or fix the file first")
                    return
                self.terminal.log(
                    "unknown language '%s' and no such file — "
                    "available: %s (a path to a .json pack file "
                    "checks too)"
                    % (rest, ", ".join(_i18n.available())))
                return
            if arg == "pack" or arg.startswith("pack "):
                # DS2 v2.58 — the terminal door for sharing: write a
                # pack's own strings as a user-pack-shaped JSON file
                # (what the desk imports back, and set_language would
                # layer over built-ins untouched). Never overwrites —
                # sharing should not destroy.
                import re as _re2
                from . import langedit as _le
                rest = arg[4:].strip()
                parts = rest.split(None, 1)
                code = parts[0].lower() if parts else ""
                dest = parts[1].strip() if len(parts) > 1 else ""
                if not code:
                    self.terminal.log(
                        "usage: lang pack <code> [dest] — write a "
                        "pack's own strings as a shareable .json "
                        "(default: ./<code>.json); available: %s"
                        % ", ".join(c for c in _i18n.available()
                                    if c != "en"))
                    return
                if not _re2.match(r"^[a-z0-9][a-z0-9_-]{0,15}$", code):
                    self.terminal.log(
                        "'%s' is not a pack code — lowercase letters, "
                        "digits, _ or - (e.g. es, pt_br)" % code)
                    return
                if code == "en":
                    self.terminal.log(
                        "English is the source of truth — there is "
                        "nothing to share; name a pack (available: %s)"
                        % ", ".join(c for c in _i18n.available()
                                    if c != "en"))
                    return
                if code not in _i18n.available():
                    self.terminal.log(
                        "unknown language '%s' — available: %s"
                        % (code, ", ".join(_i18n.available())))
                    return
                if not dest:
                    dest = os.path.join(os.getcwd(), code + ".json")
                else:
                    if len(dest) >= 2 and dest[0] == dest[-1] \
                            and dest[0] in "\"'":
                        dest = dest[1:-1]
                    dest = os.path.expanduser(dest)
                    if os.path.isdir(dest):
                        dest = os.path.join(dest, code + ".json")
                if os.path.exists(dest):
                    self.terminal.log(
                        "%s already exists — not overwriting (name "
                        "another path: lang pack %s <dest>)"
                        % (dest, code))
                    return
                try:
                    n = _le.export_pack(code, dest)
                except OSError as exc:
                    self.terminal.log(
                        "could not write %s (%s) — nothing written"
                        % (dest, exc.__class__.__name__))
                    return
                except Exception:  # noqa: BLE001 — a verb never raises
                    self.terminal.log("could not write %s — nothing "
                                      "written" % dest)
                    return
                self.terminal.log(
                    "lang pack %s — wrote %d string%s to %s — the "
                    "desk imports it back (lang edit → Import pack), "
                    "and `lang check` on the file says what an "
                    "import would meet"
                    % (code, n, "" if n == 1 else "s", dest))
                return
            if arg == "audit":
                # DS2 v2.54 — every pack answers for itself: coverage,
                # stale keys, and whether its strings keep the length
                # .lower() assumes, so fuzzy highlights stay honest
                try:
                    stats = _i18n.pack_stats()
                except Exception:  # noqa: BLE001 — a verb never raises
                    stats = []
                self.terminal.log(
                    "language packs: %d keys in the English source"
                    % (stats[0]["total"] if stats else 0))
                # DS2 v2.57 — one audit, every number: the honest
                # ledger's real_pct rides along (skipped for en, the
                # source that does not differ from itself, and for
                # packs that could not be read at all)
                try:
                    from . import langedit as _le
                except Exception:  # noqa: BLE001 — audit degrades
                    _le = None
                for s in stats:
                    line = ("  %s  %s  [%s]  %d%% — %d missing, "
                            "%d stale"
                            % (s["code"], s["name"],
                               "user" if s["user"] else "built-in",
                               s["pct"], s["missing"], s["stale"]))
                    if s["error"]:
                        line += " · unreadable (%s)" % s["error"]
                    else:
                        if _le is not None and s["code"] != "en":
                            try:
                                line += (" · %d%% real"
                                         % _le.pack_diff(
                                             s["code"])["real_pct"])
                            except Exception:  # noqa: BLE001
                                pass
                        if not s["index_safe"]:
                            line += " · NOT highlight-safe (%s)"
                            line = line % ", ".join(s["risk_keys"][:3])
                    self.terminal.log(line)
                self.terminal.log(
                    "highlight-safe = every string keeps its length "
                    "under .lower(), so fuzzy-match positions stay "
                    "on the characters they matched")
                self.terminal.log(
                    "real = strings that differ from the English "
                    "source — coverage can flatter a seeded pack "
                    "(lang diff <code> names the seeds)")
                return
            codes = _i18n.available()
            if not arg:
                self.terminal.log("languages: " + ", ".join(codes))
                self.terminal.log("current: %s (usage: lang <code>)"
                                  % _i18n.current())
                return
            pick = arg.lower()
            if pick not in codes:
                self.terminal.log("unknown language '%s' — available: %s"
                                  % (pick, ", ".join(codes)))
                return
            _i18n.set_language(pick)
            try:
                self.config.set("language", pick)
            except Exception:
                pass
            name = _i18n.LANG_NAMES.get(pick, pick)
            self.terminal.log("language set to %s — %d strings live "
                              "(new windows pick it up; tr() plumbing "
                              "arrives window by window)"
                              % (name, len(_i18n._active["pack"])))
            return
        if low == "scribe" or low.startswith("scribe "):
            # DS2: writing-meter goal / status
            arg = text[6:].strip()
            chip = getattr(self, "scribe_chip", None)
            if chip is None:
                self.terminal.log("scribe chip unavailable")
                return
            if arg.isdigit() and int(arg) >= 0:
                chip.set_goal(int(arg))
                try:
                    self.config.set("scribe_goal_words", int(arg))
                except Exception:  # noqa: BLE001
                    pass
                self._scribe_feed()
                self.terminal.log("scribe goal set to %s words — "
                                  "click the ✎ chip for session "
                                  "details" % arg)
            else:
                self.terminal.log(
                    "scribe: %s — peak %d wpm, session %.0f min, "
                    "goal %s%%"
                    % (chip.text(), round(chip.peak_wpm()),
                       chip.elapsed_min(), chip.goal_pct()))
            return
        if low.startswith("goto "):
            num = text[5:].strip()
            if num.isdigit():
                self.editor.goto_line(int(num))
                self._update_cursor_pos()
            return
        if low == "update":
            self.check_for_updates(manual=True)
            return
        if low in ("whatsnew", "whats new", "changelog"):
            self.show_whatsnew()
            return
        if low == "notifications" or low == "activity" \
                or low.startswith("activity "):
            # DS2 v2.46 — the verb grew hands: copy the receipts to
            # the clipboard or write them to a file, not just look
            rest = text[8:].strip() if low.startswith("activity") else ""
            if not rest:
                self._activity_open()
                return
            if rest == "copy":
                self._activity_copy_all()
                return
            if rest == "export" or rest.startswith("export "):
                args = rest[6:].split()
                fmt = None
                path = None
                if args and args[0] in ("json", "csv"):
                    fmt = args[0]
                    path = " ".join(args[1:]) or None
                else:
                    path = rest[6:].strip() or None
                self._activity_export_to(path, fmt=fmt)
                return
            if rest == "snap":
                # DS2 v2.51 — snapshot now, gate or no gate
                self._activity_autosnap_check(force=True)
                return
            if rest.startswith("auto"):
                # DS2 v2.51 — the nightly gate, from the terminal
                arg = rest[4:].strip().lower()
                if arg in ("on", "off"):
                    self.config.set("activity_autosnap", arg == "on",
                                    save=True)
                    self.toast("Nightly receipts snapshots %s"
                               % ("on" if arg == "on" else "off"),
                               "success")
                else:
                    try:   # DS2 v2.52 — the report names the interval
                        _rep_h = int(float(self.config.get(
                            "activity_autosnap_hours", 24)))
                        _rep_h = max(1, min(168, _rep_h))
                    except Exception:  # noqa: BLE001
                        _rep_h = 24
                    self.terminal.log(
                        "nightly snapshots are %s — every %dh — try: "
                        "activity auto on|off"
                        % ("on" if self.config.get(
                            "activity_autosnap", False) else "off",
                           _rep_h))
                return
            self.terminal.log("try: activity · activity copy · "
                              "activity export [json|csv] [path] · "
                              "activity snap · activity auto on|off")
            return
        if low == "deps" or low.startswith("deps "):
            rest = text[4:].strip().lower()
            if rest.startswith("watch"):
                self._deps_watch_toggle(rest[5:].strip())
                return
            self._run_depcheck(
                fix=(low == "deps fix" or low.startswith("deps fix ")),
                force=(low == "deps fresh"
                       or low.startswith("deps fresh ")))
            return
        if low == "commands" or low.startswith("commands "):
            self._list_palette_commands(text[8:].strip())
            return
        if low in ("hub", "project hub"):
            self.open_hub()
            return
        if low == "palette":
            self.open_palette()
            return
        if low == "chip" or low.startswith("chip "):
            # DS2 v2.53 — the statusbar chip menus, from the terminal
            arg = text[4:].strip().lower()
            if not arg:
                self.terminal.log("chips: branch · deps · scribe · "
                                  "autosave — try: chip branch")
                return
            kind = self._CHIP_MENU_ALIASES.get(arg)
            if kind is None:
                self.terminal.log("unknown chip '%s' — chips: branch · "
                                  "deps · scribe · autosave" % arg)
                return
            self._open_chip_menu_keyboard(kind)
            self.terminal.log("%s chip menu opened — Enter runs the "
                              "highlighted row, Esc puts it away" % arg)
            return
        if low in ("verbs", "verb"):
            self.open_verbs_window()
            return
        if low.startswith("search "):
            self.show_sidebar_view("search")
            self.search_view.entry.delete(0, tk.END)
            self.search_view.entry.insert(0, text[7:].strip())
            self.search_view.start_search()
            return
        if low.startswith("find "):
            self.toggle_find(show=True)
            self.find_var.set(text[5:].strip())
            self._find_live()
            return
        if low.startswith("export"):
            self.export_project_zip()
            return
        if low.startswith("git watch"):
            self._git_watch_toggle(text[9:].strip())
            return
        if low.startswith("git ") or low == "git":
            self.run_command(text.strip())
            return
        if low.startswith("agent "):
            if self.agent_panel is not None:
                self.agent_panel.route(text[6:].strip())
            else:
                self.terminal.log("DXN1 Agents is disabled — enable it in "
                                  "Settings → DXN1 Agents.")
            return
        if low in ("settings",):
            self.open_settings()
            return
        self.terminal.log("Unknown command — try 'help'.")

    def relaunch_with_splash(self):
        """The 'dxn1 studio' moment: hide, show the logo card, come back."""
        if self._splash_active:
            return
        self._splash_active = True
        self.root.withdraw()
        Splash(self.root, accent=self.theme.accent, duration_ms=2000,
               on_done=lambda: (setattr(self, "_splash_active", False),
                                self.root.deiconify()))
        self.terminal.log("Booting DXN1 STUDIO…")

    # ------------------------------------------------------------- palette
    def apply_line_tool(self, mode):
        """DS2: sort/dedupe/shuffle/reverse/trim lines.

        Acts on the selected lines when a selection exists, else the
        whole buffer. Defensive: any failure is a no-op.
        """
        try:
            from .linesort import transform_lines, MODES
            if mode not in MODES:
                return
            txt = self.editor.text
            if txt.tag_ranges("sel"):
                start = txt.index("sel.first linestart")
                end = txt.index("sel.last lineend+1c")
                block = txt.get(start, end)
                new = transform_lines(block, mode)
                if new != block:
                    txt.replace(start, end, new)
            else:
                whole = txt.get("1.0", "end-1c")
                new = transform_lines(whole, mode)
                if new != whole:
                    pos = txt.index("insert")
                    txt.delete("1.0", "end")
                    txt.insert("1.0", new)
                    txt.mark_set("insert", pos)
                    self.editor.modified = True
                    self.editor.update_line_numbers()
                    self.editor.highlighter.schedule()
                    self._mark_dirty()
            self._update_cursor_pos()
        except Exception:  # noqa: BLE001 — editor stays alive
            pass

    def open_palette(self):
        self._ds2_tick("palette")
        if self._palette is not None:
            try:
                self._palette.destroy()
            except tk.TclError:
                pass
            self._palette = None
        self._palette = CommandPalette(self)

    def palette_commands(self):
        cmds = [
            ("Run project (F5)", "F5", self.run_current),
            ("Stop process", "", self.stop_run),
            ("Save file", "Ctrl+S", lambda: self.save_file()),
            ("New file", "Ctrl+N", self.new_file),
            ("Open file…", "Ctrl+O", self.open_file_dialog),
            ("Find in file", "Ctrl+F", self.toggle_find),
            ("Quick open a file", "Ctrl+P", self.open_quick_open),
            ("Go to line…", "Ctrl+G", self.goto_line_dialog),
            ("Toggle comment", "Ctrl+/", self.editor.toggle_comment),
            ("Duplicate line", "Ctrl+Shift+D", self.editor.duplicate_line),
            ("Delete line", "Ctrl+Shift+K", self.editor.delete_line),
            ("Move line up", "Alt+Up", lambda: self.editor.move_line(-1)),
            ("Move line down", "Alt+Down", lambda: self.editor.move_line(1)),
            ("Split editor", "Ctrl+\\", self.toggle_split),
            ("Source control panel", "", lambda:
             self.show_sidebar_view("git")),
            ("Toggle bookmark on this line", "Ctrl+F2",
             lambda: self.editor.toggle_bookmark()),
            ("Next bookmark", "F2", self.editor.next_bookmark),
            ("Zen mode", "Ctrl+Alt+Z", self.toggle_zen),
            ("Scan for TODOs / FIXMEs", "", self.scan_todos),
            ("Go to symbol…  (type @)", "", self.open_palette),
            ("Check for updates…", "",
             lambda: self.check_for_updates(manual=True)),
            ("Keyboard shortcuts", "", self.show_shortcuts),
            ("Search in files", "", lambda: self.show_sidebar_view("search")),
            ("Explorer", "", lambda: self.show_sidebar_view("explorer")),
            ("Packages", "", lambda: self.show_sidebar_view("packages")),
            ("Toggle terminal", "", self.toggle_terminal),
            ("Toggle sidebar", "", self._toggle_sidebar),
            ("Export workspace as ZIP…", "", self.export_project_zip),
            ("Project Hub…", "", self.open_hub),
            ("Open workspace…", "", self.open_workspace_dialog),
            ("Settings…", "Ctrl+,", self.open_settings),
            (f"Switch to {'light' if self.theme.is_dark else 'dark'} theme", "",
             self.switch_theme),
            ("Word wrap on/off", "", self.toggle_word_wrap),
            ("Bigger editor text", "Ctrl++", lambda: self.change_font_size(1)),
            ("Smaller editor text", "Ctrl+-", lambda: self.change_font_size(-1)),
            ("Replay welcome & tour", "", self.start_wizard),
        ]
        # ---- DS2 visual git suite (defensive: never break the palette)
        try:
            from . import gitgraph as _gg
            from . import branches as _br
            from . import diffview as _dv
            cmds += [
                ("Commit graph (all branches)", "",
                 lambda: _gg.open_graph(self.root, self.theme,
                                        self.project_dir,
                                        on_log=lambda m: None)),
                ("Branch manager — create / merge / cleanup", "",
                 lambda: _br.open_branches(self.root, self.theme,
                                           self.project_dir,
                                           on_log=lambda m: None)),
                ("Diff workspace vs HEAD", "",
                 lambda: _dv.show_diff(
                     self.root, self.theme,
                     *self._worktree_texts())),
            ]
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 intelligence: memory + usage (defensive)
        try:
            from . import memory as _mem
            from . import usagedash as _ud
            cmds += [
                ("Agent memory — what the assistant remembers", "",
                 lambda: _mem.open_memory(self.root, self.theme,
                                          self.project_dir,
                                          on_log=lambda m: None)),
                ("Token usage dashboard", "",
                 lambda: _ud.open_dashboard(self.root, self.theme,
                                            self.project_dir)),
            ]
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 hub: template gallery (defensive)
        try:
            from .gallery import open_gallery as _open_gallery

            def _gallery_cmd():
                def _picked(kind):
                    # reuse the hub's create flow (name + folder picker)
                    self.open_hub()
                    hub = getattr(self, "_hub", None)
                    if hub is not None and hub.winfo_exists():
                        hub.create_workspace(kind)

                _open_gallery(self.root, self.config,
                              getattr(self.theme, "accent", "#7c3aed"),
                              on_pick=_picked)

            cmds.append(("Template gallery — browse every scaffold", "",
                         _gallery_cmd))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 diagnostics: environment doctor (defensive)
        try:
            from .doctor import open_doctor as _open_doctor
            cmds.append(
                ("Doctor — check my environment", "",
                 lambda: _open_doctor(
                     self.root, self.theme, self.config,
                     workspace=self.project_dir,
                     on_log=lambda m: self.terminal.log(m))),
            )
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 platform: plugins (defensive)
        try:
            from . import plugins as _plugins
            _reg = _plugins.get_registry(
                self.config, log=lambda m: self.terminal.log(m))
            try:  # ship the sample pack into the global plugin dir once
                _plugins.write_sample_plugins(_plugins.GLOBAL_PLUGIN_DIR)
            except Exception:
                pass

            def _open_plugins():
                _plugins.open_manager(
                    self.root, self.theme, self.config,
                    workspace=self.project_dir,
                    on_log=lambda m: self.terminal.log(m),
                    on_commands_changed=None)

            cmds.append(("Plugin manager — extend the studio", "",
                         _open_plugins))
            for _c in _reg.commands:
                cmds.append((f"{_c['label']} · plugin:{_c['plugin']}", "",
                             lambda c=_c: self._run_plugin_command(c)))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 tasks: task runner (defensive)
        try:
            from .term import open_runner as _open_runner
            cmds.append(
                ("Task runner — run project tasks", "",
                 lambda: _open_runner(
                     self.root, self.theme, self.config,
                     workspace=self.project_dir, kind=self.project_kind,
                     on_log=lambda m: self.terminal.log(m))),
            )
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 safety: workspace snapshots (defensive)
        try:
            from .backup import open_snapshots as _open_snaps, \
                create_snapshot as _snap

            def _quick_snapshot():
                if not self.project_dir:
                    self.terminal.log("snapshot: open a workspace first")
                    return
                path, stats = _snap(self.project_dir,
                                    label="manual")
                self.terminal.log(
                    f"snapshot: {os.path.basename(path)} "
                    f"({stats['zipped']} files)")
                self.toast("Snapshot saved", "success")

            cmds += [
                ("Snapshot — back up this workspace now", "",
                 _quick_snapshot),
                ("Browse snapshots…", "",
                 lambda: _open_snaps(
                     self.root, self.theme, self.config,
                     workspace=self.project_dir,
                     on_log=lambda m: self.terminal.log(m))),
            ]
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 navigation: symbol outline (defensive)
        try:
            from .outline import open_outline as _open_outline

            def _goto_line(line):
                target = f"{int(line)}.0"
                try:
                    self.editor.text.mark_set("insert", target)
                    self.editor.text.see(target)
                    self.editor.text.focus_set()
                    self._update_cursor_pos()
                except Exception:  # noqa: BLE001 — best-effort jump
                    pass

            cmds.append(
                ("Go to symbol in file…", "",
                 lambda: _open_outline(
                     self.root, self.theme,
                     get_text=lambda: self.editor.get_content(),
                     on_jump=_goto_line,
                     path=getattr(self.editor, "file_path", "") or "",
                     on_log=lambda m: self.terminal.log(m))),
            )
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2 notes: scratchpad (defensive)
        try:
            from .scratch import open_scratchpad as _open_scratch
            cmds.append(
                ("Scratchpad — jot something down", "",
                 lambda: _open_scratch(
                     self.root, self.theme, self.config,
                     workspace=self.project_dir,
                     on_log=lambda m: self.terminal.log(m))),
            )
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2: file statistics explorer (defensive)
        try:
            from .filestats import open_stats as _open_filestats
            cmds.append(
                ("File statistics — what's in this workspace…", "DS2",
                 lambda: _open_filestats(
                     self.root, self.theme,
                     workspace=getattr(self, "project_dir", "") or
                     os.getcwd(),
                     on_log=lambda m: self.terminal.log(m))),
            )
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2: recent-files fuzzy picker (defensive)
        try:
            cmds.append(("Recent files…", "DS2", self.open_recent_picker))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2: prompt library (defensive)
        try:
            from .prompts import open_picker as _open_prompts
            from .prompts import insert_into_agent as _prompt_to_agent

            def _explain_error_cmd():
                self.explain_last_error()

            cmds.append(("Explain the last error with the agent…", "DS2",
                         _explain_error_cmd))

            def _prompt_ctx():
                try:
                    t = self.editor.text
                    sel = t.tag_ranges("sel")
                    selection = t.get(sel[0], sel[1]) if sel else ""
                except Exception:   # noqa: BLE001
                    selection = ""
                return {
                    "file_path": getattr(self.editor, "file_path", "") or "",
                    "workspace": getattr(self, "project_dir", "") or "",
                    "selection": selection,
                }

            def _use_prompt(rendered):
                if self.agent_panel is not None:
                    _prompt_to_agent(self.agent_panel, rendered)
                else:
                    self.terminal.log(
                        "prompt copied — open the Agents panel to chat")

            cmds.append(
                ("Prompt library — saved asks for the agent…", "DS2",
                 lambda: _open_prompts(
                     self.root, self.theme,
                     workspace=getattr(self, "project_dir", "") or None,
                     on_use=_use_prompt, context=_prompt_ctx,
                     on_log=lambda m: self.terminal.log(m))),
            )
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # ---- DS2: persistent bookmarks browser (defensive)
        try:
            from .bookmarks import open_browser as _open_bookmarks

            def _bookmark_jump(abspath, line):
                self.open_file(abspath)
                self.editor.goto_line(line)

            cmds.append(
                ("Bookmarks — browse all in this workspace…", "DS2",
                 lambda: _open_bookmarks(
                     self.root, self.theme,
                     workspace=getattr(self, "project_dir", "") or None,
                     on_jump=_bookmark_jump,
                     on_log=lambda m: self.terminal.log(m))),
            )
        except Exception:  # pragma: no cover — palette stays alive
            pass
        if self.config.get("agents_enabled"):
            cmds += [
                ("Toggle DXN1 Agents panel", "", self.toggle_agents_panel),
                ("DXN1 Agents settings…", "",
                 lambda: AgentSettingsDialog(self)),
                ("Connect a brain…", "", lambda: ConnectDialog(self)),
            ]
        # DS2 additions — usage metering + workspace memory (defensive)
        def _open_usage():
            from .usagedash import open_dashboard
            open_dashboard(self, self.theme,
                           workspace=getattr(self, "project_dir", ""),
                           on_log=lambda msg: self.terminal.log(msg))

        def _open_memory():
            from .memory import open_memory_editor
            open_memory_editor(self, self.theme,
                               workspace=getattr(self, "project_dir", ""),
                               on_log=lambda msg: self.terminal.log(msg))

        cmds += [
            ("Token usage dashboard…", "DS2", _open_usage),
            ("Agent memory (this workspace)…", "DS2", _open_memory),
        ]
        # DS2: AI quick actions on the selection (defensive) — the
        # module exposes its own palette-ready command tuples
        try:
            from . import quick_actions as _qa
            cmds += _qa.palette_commands(self)
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.55: the translation desk (defensive) — one row, the
        # chooser decides which pack gets the desk
        try:
            from . import langedit as _langedit
            cmds += _langedit.palette_commands(self)
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: AI review (gutter eyes) + pair mode (defensive)
        def _open_pair():
            from .pair import open_pair
            panel = getattr(self, "agent_panel", None)
            open_pair(self, getattr(panel, "sandbox", None),
                      on_log=lambda m: self.terminal.log(m))
        try:
            from . import ai_lint as _lint
            cmds.append(_lint.palette_command(self))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        try:
            cmds.append(("Pair mode — plan, agree, build…", "DS2",
                         _open_pair))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: theme gallery (defensive)
        def _open_themes():
            from .community_themes import open_gallery
            open_gallery(self.root, self.theme, self.config,
                         on_log=lambda m: self.terminal.log(m),
                         restart=self._ds2_restart)
        try:
            cmds.append(("Theme gallery — 12 community palettes…", "DS2",
                         _open_themes))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: task runner + editor minimap (defensive)
        def _open_tasks():
            from .term import open_tasks
            open_tasks(self.root, self.theme, self.project_dir,
                       on_run=self.run_command,
                       on_log=lambda m: self.terminal.log(m))

        def _toggle_minimap():
            if getattr(self, "_minimap", None) is not None:
                self._minimap.pack_forget()
                self._minimap = None
                return
            from .minimap import Minimap
            self._minimap = Minimap(self.editor.text_frame, self.theme,
                                    self.editor.text)
            self._minimap.pack(side=tk.RIGHT, fill=tk.Y)

        try:
            cmds += [
                ("Task runner — project commands…", "DS2", _open_tasks),
                ("Editor minimap on/off", "DS2", _toggle_minimap),
            ]
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: developer pocket knife (defensive)
        def _open_devtools_palette():
            from .devtools import open_devtools
            open_devtools(self.root, self.theme)
        try:
            cmds.append(("Developer tools — regex, JSON, text, time…",
                         "DS2", _open_devtools_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: cron decoder ring (defensive)
        def _open_cron():
            from .cronexp import open_cron
            open_cron(self.root, self.theme,
                      initial=self.editor.text.get("sel.first", "sel.last")
                      .strip())
        try:
            cmds.append(("Cron explainer — decode schedule strings…",
                         "DS2", _open_cron))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: readability report for the current file (defensive)
        def _open_readability():
            from .readability import open_readability
            open_readability(self.root, self.theme,
                             text=self.editor.text.get("1.0", "end-1c"),
                             name=os.path.basename(
                                 getattr(self, "current_path", "")
                                 or getattr(self.editor, "path", "")
                                 or "file"))
        try:
            cmds.append(("Readability report for this file…",
                         "DS2", _open_readability))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: JWT decoder (defensive)
        def _open_jwt():
            from .jwt import open_jwt
            open_jwt(self.root, self.theme,
                     initial=self.editor.text.get("sel.first", "sel.last")
                     .strip())
        try:
            cmds.append(("JWT decoder — inspect a token…",
                         "DS2", _open_jwt))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: .env lint & mask (defensive)
        def _open_env():
            from .envcheck import open_envlint
            open_envlint(self.root, self.theme)
        try:
            cmds.append((".env lint & mask — keep secrets safe…",
                         "DS2", _open_env))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: test data & ID generator (defensive)
        def _open_gen():
            from .gen import open_generator
            open_generator(self.root, self.theme)
        try:
            cmds.append(("Data generator — UUIDs, nanoids, fake users…",
                         "DS2", _open_gen))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: SQLite Lab (defensive)
        def _open_db():
            from .sqlitelab import open_sqlitelab
            open_sqlitelab(self.root, self.theme,
                           workspace=getattr(self, "project_dir", "") or "")
        try:
            cmds.append(("SQLite browser — tables, schema, queries…",
                         "DS2", _open_db))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: directory tree export (defensive)
        def _open_tree():
            from .treeexport import open_treeexport
            open_treeexport(self.root, self.theme,
                            initial=getattr(self, "project_dir", "") or "",
                            workspace=getattr(self, "project_dir", "") or "")
        try:
            cmds.append(("Directory tree export — README-ready ASCII…",
                         "DS2", _open_tree))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: hasher (defensive)
        def _open_hash():
            from .hasher import open_hasher
            open_hasher(self.root, self.theme,
                        initial=getattr(self, "project_dir", "") or "",
                        workspace=getattr(self, "project_dir", "") or "")
        try:
            cmds.append(("Hasher — checksums & manifest verify…",
                         "DS2", _open_hash))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: line tools (defensive)
        for _lbl, _mode in (("Sort lines A→Z", "az"),
                            ("Sort lines Z→A", "za"),
                            ("Sort lines by length", "len"),
                            ("Dedupe lines", "dedupe"),
                            ("Shuffle lines", "shuffle"),
                            ("Reverse lines", "reverse"),
                            ("Trim trailing whitespace", "trim")):
            try:
                cmds.append((_lbl, "DS2",
                             lambda m=_mode: self.apply_line_tool(m)))
            except Exception:  # pragma: no cover — palette stays alive
                pass
        # DS2: clipboard history (defensive)
        def _open_clip():
            self.paste_from_history()
        try:
            cmds.append(("Clipboard history — paste earlier copies…",
                         "DS2", _open_clip))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: markdown preview (defensive)
        def _open_md_palette():
            self.open_markdown_preview()
        try:
            cmds.append(("Markdown preview — live dual-pane render…",
                         "DS2", _open_md_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: color kit (defensive)
        def _open_color_palette():
            self.open_colorkit()
        try:
            cmds.append(("Color Kit — hex/rgb/hsl + contrast…",
                         "DS2", _open_color_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: REST bench (defensive)
        def _open_rest_palette():
            self.open_restbench()
        try:
            cmds.append(("REST Bench — send HTTP requests…",
                         "DS2", _open_rest_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: chart studio (defensive)
        def _open_chart_palette():
            self.open_chart_studio()
        try:
            cmds.append(("Chart Studio — paste numbers, see them…",
                         "DS2", _open_chart_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: unit converter (defensive)
        def _open_unit_palette():
            self.open_unit_converter()
        try:
            cmds.append(("Unit Converter — length/mass/data…",
                         "DS2", _open_unit_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: character map (defensive)
        def _open_charmap_palette():
            self.open_charmap()
        try:
            cmds.append(("Character Map — browse & copy Unicode…",
                         "DS2", _open_charmap_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: textcase (defensive)
        def _open_textcase_palette():
            self.open_textcase()
        try:
            cmds.append(("TextCase — snake/camel/kebab/… converter",
                         "DS2", _open_textcase_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: passforge (defensive)
        def _open_passforge_palette():
            self.open_passforge()
        try:
            cmds.append(("PassForge — strong passwords + entropy…",
                         "DS2", _open_passforge_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: numbase (defensive)
        def _open_numbase_palette():
            self.open_numbase()
        try:
            cmds.append(("NumBase — bin/oct/dec/hex + bases 2-36…",
                         "DS2", _open_numbase_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: csv lab (defensive)
        def _open_csv_palette():
            self.open_csv_lab()
        try:
            cmds.append(("CSV Lab — paste & peek tables…",
                         "DS2", _open_csv_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: mathpad (defensive)
        def _open_math_palette():
            self.open_mathpad()
        try:
            cmds.append(("MathPad — safe expression calculator…",
                         "DS2", _open_math_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: bytesnoop (defensive)
        def _open_hex_palette():
            self.open_bytesnoop()
        try:
            cmds.append(("ByteSnoop — hexdump & byte inspector…",
                         "DS2", _open_hex_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: textdiff (defensive)
        def _open_textdiff_palette():
            self.open_textdiff()
        try:
            cmds.append(("Paste Diff — compare two texts…",
                         "DS2", _open_textdiff_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: xmlbench (defensive)
        def _open_xml_palette():
            self.open_xmlbench()
        try:
            cmds.append(("Markup Bench — pretty & inspect XML…",
                         "DS2", _open_xml_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: contrast auditor (defensive)
        def _open_contrast_palette():
            self.open_contrast()
        try:
            cmds.append(("Contrast Auditor — WCAG grades for themes…",
                         "DS2", _open_contrast_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: cheat sheet exporter (defensive)
        def _open_cheatsheet_palette():
            self.open_cheatsheet()
        try:
            cmds.append(("Cheat Sheet — printable HTML export…",
                         "DS2", _open_cheatsheet_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: colorblind lab (defensive)
        def _open_cvd_palette():
            self.open_cvdlab()
        try:
            cmds.append(("Colorblind Lab — CVD preview of themes…",
                         "DS2", _open_cvd_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: session restore (defensive)
        def _open_session_palette():
            self.open_session_restore()
        try:
            cmds.append(("Session Restore — pick up where you left "
                         "off…", "DS2", _open_session_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.33: save session now (defensive)
        def _save_session_palette():
            self.save_session_now()
        try:
            cmds.append(("Save Session Now — snapshot tabs + "
                         "cursors…", "DS2", _save_session_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.36: dependency check (defensive)
        def _deps_palette():
            self._run_depcheck()
        try:
            cmds.append(("Dependency Check — imports vs "
                         "requirements…", "DS2", _deps_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.39: dependency watch chip toggle (defensive)
        def _deps_watch_palette():
            self._deps_watch_toggle()
        try:
            cmds.append(("Dependency watch on/off — statusbar drift "
                         "chip…", "DS2", _deps_watch_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.39: terminal verbs browser (defensive)
        def _verbs_palette():
            self.open_verbs_window()
        try:
            cmds.append(("Terminal verbs — every command, "
                         "browsable…", "DS2", _verbs_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.40: git lane chip toggle (defensive)
        def _git_watch_palette():
            self._git_watch_toggle()
        try:
            cmds.append(("Source control watch on/off — statusbar "
                         "branch chip…", "DS2", _git_watch_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.36: what's new on demand (defensive)
        def _whatsnew_palette():
            self.show_whatsnew()
        try:
            cmds.append(("What's New — release notes digest…",
                         "DS2", _whatsnew_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: scribe goal (defensive)
        def _scribe_goal_palette():
            self._scribe_click()
        try:
            cmds.append(("Scribe meter — writing session details…",
                         "DS2", _scribe_goal_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2 v2.43: chip-family rows (defensive)
        def _sesave_snapshot_palette():
            self.save_session_now()
        try:
            cmds.append(("Session — snapshot tabs now…",
                         "DS2", _sesave_snapshot_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass

        # DS2 v2.53: the chip menus themselves join the palette — the
        # keyboard's path to the statusbar's right-click world. The
        # accelerators are REAL root binds (the honest-keys audit,
        # v2.47, polices every one of these claims).
        for _kind, _label, _accel in (
                ("git", "Branch chip menu — commit, push, pull, "
                 "graph…", "Ctrl+Alt+G"),
                ("deps", "Deps chip menu — rescan, repair, watch…",
                 "Ctrl+Alt+E"),
                ("scribe", "Scribe chip menu — summary, goal, "
                 "reset…", "Ctrl+Alt+W"),
                ("sesave", "Autosave chip menu — snapshot, browse, "
                 "toggle…", "Ctrl+Alt+A")):
            def _chip_opener(kind=_kind):
                self._open_chip_menu_keyboard(kind)
            try:
                cmds.append((_label, _accel, _chip_opener))
            except Exception:  # pragma: no cover — palette stays alive
                pass

        def _scribe_reset_palette():
            self._scribe_reset_from_menu()
        try:
            cmds.append(("Scribe — reset the writing meter…",
                         "DS2", _scribe_reset_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass

        def _activity_palette():
            self._activity_open()
        try:
            cmds.append(("Activity — recent notifications…",
                         "DS2", _activity_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass

        def _activity_export_palette():
            self._activity_export_to()
        try:
            cmds.append(("Activity — export receipts to a file…",
                         "DS2", _activity_export_palette))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        # DS2: focus timer (defensive)
        def _open_focus():
            from .focus import open_focus
            open_focus(self.root, self.theme)
        try:
            cmds.append(("Focus timer — pomodoro work/break cycles…",
                         "DS2", _open_focus))
        except Exception:  # pragma: no cover — palette stays alive
            pass
        return cmds

    def _ds2_restart(self):
        """DS2: restart into a new theme — mirrors switch_theme."""
        self.restart_requested = True
        self.root.after(120, self.root.destroy)

    def _ds2_tick(self, step_id):
        """DS2: tick a first-run checklist step (defensive, idempotent)."""
        try:
            from .checklist import mark
            if mark(self.config, step_id):
                card = getattr(self, "checklist", None)
                if card is not None:
                    card.refresh()
        except Exception:
            pass

    def _worktree_texts(self):
        """(HEAD text, working text) for the open file — diff support."""
        import subprocess as _sp
        path = getattr(self, "current_path", None) or \
            getattr(self.editor, "path", None)
        if not path:
            return "", ""
        try:
            rel = os.path.relpath(path, self.project_dir).replace(os.sep,
                                                                  "/")
        except ValueError:
            rel = path
        try:
            proc = _sp.run(["git", "show", f"HEAD:{rel}"],
                           cwd=self.project_dir, capture_output=True,
                           text=True, timeout=10)
            old = proc.stdout if proc.returncode == 0 else ""
        except Exception:  # pragma: no cover — diff is best-effort
            old = ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                new = fh.read()
        except OSError:
            new = ""
        return old, new

    def _plugin_context(self):
        """Context dict handed to plugin commands (fail-soft fields)."""
        ctx = {"path": "", "text": "", "selection": "",
               "workspace": getattr(self, "project_dir", "") or ""}
        try:
            ctx["path"] = getattr(self.editor, "file_path", "") or \
                getattr(self.editor, "path", "") or ""
            if ctx["path"]:
                ctx["text"] = self.editor.get_content()
            ctx["selection"] = self.editor.text.get("sel.first", "sel.last")
        except Exception:  # noqa: BLE001 — context is best-effort
            pass
        return ctx

    def _run_plugin_command(self, command):
        """Run one plugin command; string results insert at the cursor."""
        result = None
        try:
            result = command["fn"](self._plugin_context())
        except Exception as exc:  # noqa: BLE001
            self.terminal.log(f"plugin command failed: {exc}")
            self.toast("Plugin error", "error")
            return
        if isinstance(result, str) and result:
            try:
                self.editor.text.insert("insert", result)
                self.terminal.log(
                    f"plugin inserted {len(result)} chars")
            except Exception:  # noqa: BLE001
                self.terminal.log(result)
        elif result is not None:
            self.terminal.log(str(result))

    # --------------------------------------------------------------- toast
    def toast(self, message, kind="info"):
        """Small notification card above the status bar; auto-dismisses."""
        # DS2 v2.44: archive the whisper — toasts vanish, the log stays
        # (v2.45: the ring persists to disk atomically on every add)
        log = getattr(self, "activity_log", None)
        if log is not None:
            try:
                log.add(message, kind)
                from .activity import save_json
                save_json(log, self._activity_path())
            except Exception:  # noqa: BLE001 — never break the toast
                pass
        # DS2 v2.47 — a muted kind keeps its receipt but skips the
        # card: the Activity log remembers, the screen stays quiet
        try:
            if not self.config.get("toast_show_%s" % kind, True):
                return
        except Exception:  # noqa: BLE001 — a broken setting whispers on
            pass
        t = self.theme
        colors = {"success": t["success"], "error": "#f85149",
                  "info": t.accent}
        frame = tk.Frame(self.toast_layer, bg=t["card"], highlightthickness=1,
                         highlightbackground=t["card_border"])
        frame.pack(fill=tk.X, pady=3, padx=2)
        tk.Frame(frame, bg=colors.get(kind, t.accent), width=3).pack(
            side=tk.LEFT, fill=tk.Y)
        tk.Label(frame, text=message, bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 9), padx=10, pady=6).pack(side=tk.LEFT)
        self.root.after(3400, frame.destroy)

    # ------------------------------------------------------------ settings
    def _open_lang_desk(self, code=None):
        """DS2 v2.55 — open the translation desk (the chooser when no
        code is named, that pack's desk when one is). Best-effort by
        contract: a desk that cannot open here logs honestly and the
        studio keeps typing."""
        try:
            from . import langedit as _langedit
            win = _langedit.open_pack_editor(
                self, code, on_log=lambda m: self.terminal.log(m))
            if win is not None:
                self.terminal.log(
                    "translation desk open%s — saved strings become a "
                    "user pack that overrides built-ins"
                    % (" for '%s'" % code if code else ""))
            else:
                self.terminal.log("translation desk unavailable here")
            return win
        except Exception as exc:  # noqa: BLE001 — garnish must not bite
            try:
                self.terminal.log("translation desk unavailable (%s)"
                                  % exc)
            except Exception:  # noqa: BLE001
                pass
            return None

    def _emit_checkup(self, head, rep, hint, diff_code=None):
        """DS2 v2.58 — one checkup, printed: the ledger line first
        (what the thing in hand WOULD do), then every finding by
        name, then the verdict and the way out. Shared by both doors
        of `lang check` — installed packs and pack files answer
        alike."""
        def _list(vals):
            sample = ", ".join(vals[:8])
            return sample + ", …" if len(vals) > 8 else sample
        log = self.terminal.log
        log(head)
        log("  %d pair%s read · %d real, %d still English · "
            "coverage %d%% · %d%% real"
            % (rep["pairs"], "" if rep["pairs"] == 1 else "s",
               rep["real"], rep["seeds"], rep["covered_pct"],
               rep["real_pct"]))
        findings = (rep["junk"] + len(rep["empty"])
                    + len(rep["unknown"]) + len(rep["unsafe"]))
        if rep["junk"]:
            log("  %d non-string pair%s — an import skips %s"
                % (rep["junk"], "" if rep["junk"] == 1 else "s",
                   "it" if rep["junk"] == 1 else "them"))
        if rep["empty"]:
            log("  %d empty value%s — an import drops %s back to "
                "English: %s"
                % (len(rep["empty"]),
                   "" if len(rep["empty"]) == 1 else "s",
                   "it" if len(rep["empty"]) == 1 else "them",
                   _list(rep["empty"])))
        if rep["unknown"]:
            log("  %d unknown key%s — the source never names %s; "
                "dead weight that ages into stale: %s"
                % (len(rep["unknown"]),
                   "" if len(rep["unknown"]) == 1 else "s",
                   "it" if len(rep["unknown"]) == 1 else "them",
                   _list(rep["unknown"])))
        if rep["unsafe"]:
            log("  %d NOT highlight-safe — length changes under "
                ".lower(): %s"
                % (len(rep["unsafe"]), _list(rep["unsafe"])))
        if findings:
            log("verdict: %d finding%s — an import survives them, "
                "but a pack worth sharing is worth fixing"
                % (findings, "" if findings == 1 else "s"))
        else:
            log("verdict: clean — nothing blocks an import")
        if diff_code and rep["seeds"]:
            log("  though %d string%s still read English — lang diff "
                "%s name%s %s"
                % (rep["seeds"], "" if rep["seeds"] == 1 else "s",
                   diff_code, "s" if rep["seeds"] != 1 else "",
                   "it" if rep["seeds"] == 1 else "them"))
        log(hint)

    def open_settings(self):
        SettingsDialog(self)

    def toggle_terminal(self):
        if self.terminal_visible:
            self.right_panel.forget(self.terminal)
        else:
            self.right_panel.forget(self.editor.master)
            self.right_panel.add(self.editor.master, minsize=200)
            self.right_panel.add(self.terminal, height=200, minsize=80)
            self._sash_user = False
            self._pin_sash()
        self.terminal_visible = not self.terminal_visible

    def switch_theme(self):
        self._ds2_tick("theme")
        self.config.set("theme", "light" if self.theme.is_dark else "dark")
        self.restart_requested = True
        self.root.after(120, self.root.destroy)

    def change_font_size(self, delta):
        current = int(self.config.get("editor_font_size", 11))
        new = max(8, min(20, current + delta))
        if new == current:
            return
        self.config.set("editor_font_size", new)
        self.editor.set_font_size(new)
        self.toast(f"Editor text: {new}px", "info")

    def toggle_word_wrap(self):
        new = not bool(self.config.get("word_wrap", False))
        self.config.set("word_wrap", new)
        self.editor.set_wrap(new)
        self.toast(f"Word wrap {'on' if new else 'off'}", "info")

    def show_about(self):
        t = self.theme
        win = tk.Toplevel(self.root)
        win.title("About")
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        box = tk.Frame(win, bg=t["bg"])
        box.pack(padx=34, pady=26)
        from .onboarding import load_scaled
        import os as _os
        logo_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "assets", "logo.png")
        logo = load_scaled(logo_path, 84, 84)
        if logo:
            self._about_logo_ref = logo
            tk.Label(box, image=logo, bg=t["bg"]).pack()
        tk.Label(box, text=f"{APP_NAME}  v{APP_VERSION}-{APP_CHANNEL}",
                 bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 14, "bold")).pack(pady=(10, 0))
        tk.Label(box, text=APP_TAGLINE, bg=t["bg"],
                 fg=t["text_secondary"], font=(FONT_UI, 10)).pack()
        tk.Label(box, text="Pure Python + Tkinter. No Electron, no "
                           "frameworks, no bloat.",
                 bg=t["bg"], fg=t["text_muted"], font=(FONT_UI, 9)
                 ).pack(pady=(12, 0))
        link = tk.Label(box, text=REPO_URL, bg=t["bg"], fg=t.accent,
                        font=(FONT_UI, 9, "underline"), cursor="hand2")
        link.pack(pady=(4, 0))
        link.bind("<Button-1>",
                  lambda e: webbrowser.open(REPO_URL))
        tk.Label(box, text="MIT License · © 2026 DXN1", bg=t["bg"],
                 fg=t["text_muted"], font=(FONT_UI, 8)).pack(pady=(10, 0))
        upd = tk.Label(box, text="Check for updates…", bg=t["bg"],
                       fg=t.accent, font=(FONT_UI, 9, "bold"),
                       cursor="hand2")
        upd.pack(pady=(8, 0))
        upd.bind("<Button-1>",
                 lambda e: self.check_for_updates(manual=True))
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + \
            max(0, (self.root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = self.root.winfo_rooty() + 110
        win.geometry(f"+{x}+{y}")

    # ------------------------------------------------------ explorer menu
    def _explorer_menu(self, path, is_dir, x, y):
        t = self.theme
        menu = tk.Menu(self.root, tearoff=0, bg=t["sidebar"], fg=t["text"],
                       activebackground=t["hover"],
                       activeforeground=t["text"], font=(FONT_UI, 9))
        if is_dir:
            menu.add_command(label="New File…", command=lambda:
                             self._explorer_new(path, file=True))
            menu.add_command(label="New Folder…", command=lambda:
                             self._explorer_new(path, file=False))
            menu.add_separator()
            menu.add_command(label="Rename…", command=lambda:
                             self._explorer_rename(path))
            menu.add_command(label="Copy Path", command=lambda:
                             self._copy_path(path))
            menu.add_command(label="Reveal in File Manager", command=lambda:
                             self.reveal_in_file_manager(path))
            menu.add_separator()
            menu.add_command(label="Refresh", command=self.refresh_explorer)
            menu.add_command(label="Delete", command=lambda:
                             self._explorer_delete(path))
        else:
            menu.add_command(label="Open", command=lambda:
                             self.open_file(path))
            menu.add_command(label="Open in Split View", command=lambda:
                             (self.open_file(path),
                              self.toggle_split() if self._split is None
                              else None))
            if path.endswith(".py"):
                menu.add_command(label="Run This File", command=lambda:
                                 self.run_file(path))
            menu.add_separator()
            menu.add_command(label="Duplicate", command=lambda:
                             self._explorer_duplicate(path))
            menu.add_command(label="Rename…", command=lambda:
                             self._explorer_rename(path))
            menu.add_command(label="Copy Path", command=lambda:
                             self._copy_path(path))
            menu.add_command(label="Reveal in File Manager", command=lambda:
                             self.reveal_in_file_manager(path))
            menu.add_separator()
            menu.add_command(label="Delete", command=lambda:
                             self._explorer_delete(path))
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _explorer_new(self, parent, file=True):
        name = ""
        if file:
            name = self._ask("New File", "File name (e.g. utils.py):")
        else:
            name = self._ask("New Folder", "Folder name:")
        if not name:
            return
        target = os.path.join(parent, name)
        try:
            if file:
                os.makedirs(os.path.dirname(target) or parent, exist_ok=True)
                with open(target, "w", encoding="utf-8") as fh:
                    fh.write("")
            else:
                os.makedirs(target, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("New", f"Couldn't create {name}:\n{exc}")
            return
        self.refresh_explorer()
        if file:
            self.open_file(target)
        self.toast(f"Created {name}", "success")

    def _explorer_rename(self, path):
        new = self._ask("Rename", "New name:",
                        initial=os.path.basename(path))
        if not new or new == os.path.basename(path):
            return
        target = os.path.join(os.path.dirname(path), new)
        try:
            os.rename(path, target)
        except OSError as exc:
            messagebox.showerror("Rename", f"Couldn't rename:\n{exc}")
            return
        # migrate any open tab
        if path in self._tab_frames:
            self._buffers[target] = self._buffers.pop(path)
            entry = self._tab_frames.pop(path)
            self._tab_frames[target] = entry
            if self.editor.file_path == path:
                self.editor.file_path = target
                self.editor.set_content(self._buffers[target]["content"],
                                        path=target)
        self.refresh_explorer()
        self.toast(f"Renamed to {new}", "success")

    def _explorer_duplicate(self, path):
        base, ext = os.path.splitext(path)
        target = f"{base} copy{ext}"
        n = 2
        while os.path.exists(target):
            target = f"{base} copy {n}{ext}"
            n += 1
        try:
            import shutil
            shutil.copy2(path, target)
        except OSError as exc:
            messagebox.showerror("Duplicate", f"Couldn't copy:\n{exc}")
            return
        self.refresh_explorer()
        self.open_file(target)

    def _explorer_delete(self, path):
        kind = "folder" if os.path.isdir(path) else "file"
        if not messagebox.askyesno(
                "Delete",
                f"Delete the {kind} '{os.path.basename(path)}'?\n\n"
                f"{path}\n\nThis cannot be undone."):
            return
        try:
            import shutil
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as exc:
            messagebox.showerror("Delete", f"Couldn't delete:\n{exc}")
            return
        if path in self._tab_frames:
            self.close_tab(path)
        self.refresh_explorer()
        self.toast(f"Deleted {os.path.basename(path)}", "info")

    def _copy_path(self, path):
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.toast("Path copied", "info")

    def _ask(self, title, prompt, initial=""):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=self.theme["card"])
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        tk.Label(dlg, text=prompt, bg=self.theme["card"],
                 fg=self.theme["text"], font=(FONT_UI, 10)
                 ).pack(padx=18, pady=(16, 8))
        var = tk.StringVar(value=initial)
        entry = tk.Entry(dlg, textvariable=var, bg=self.theme["editor"],
                         fg=self.theme["text"], relief=tk.FLAT,
                         insertbackground=self.theme["text"],
                         font=(FONT_MONO, 10), width=34,
                         highlightthickness=1,
                         highlightbackground=self.theme["border"],
                         highlightcolor=self.theme.accent)
        entry.pack(padx=18, ipady=5)
        entry.selection_range(0, tk.END)
        entry.focus_set()
        result = {"value": ""}

        def ok(event=None):
            result["value"] = var.get().strip()
            dlg.destroy()

        entry.bind("<Return>", ok)
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        row = tk.Frame(dlg, bg=self.theme["card"])
        row.pack(fill=tk.X, pady=14)
        cancel = tk.Label(row, text="Cancel", bg=self.theme["card"],
                          fg=self.theme["text_secondary"], cursor="hand2",
                          font=(FONT_UI, 10), padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: dlg.destroy())
        confirm = tk.Label(row, text="OK", bg=self.theme.accent, fg="#ffffff",
                           cursor="hand2", font=(FONT_UI, 10, "bold"),
                           padx=16, pady=4)
        confirm.pack(side=tk.RIGHT, padx=(0, 14))
        confirm.bind("<Button-1>", ok)
        dlg.update_idletasks()
        x = self.root.winfo_rootx() + \
            max(0, (self.root.winfo_width() - dlg.winfo_reqwidth()) // 2)
        y = self.root.winfo_rooty() + 140
        dlg.geometry(f"+{x}+{y}")
        self.root.wait_window(dlg)
        return result["value"]

    # ---------------------------------------------------------- TODO scan
    def scan_todos(self):
        """Workspace-wide TODO / FIXME hunt → clickable results window."""
        if not self.project_dir:
            self.toast("Open a workspace first", "error")
            return
        base = self.project_dir
        self.terminal.log("Scanning for TODO / FIXME…")
        hits = []
        pattern = re.compile(r"(?i)\b(TODO|FIXME)\b[:\s]?(.{0,90})")
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in TREE_SKIP]
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext and ext not in TEXT_EXTS:
                    continue
                full = os.path.join(dirpath, name)
                try:
                    with open(full, "r", encoding="utf-8",
                              errors="replace") as fh:
                        for lineno, line in enumerate(fh, 1):
                            m = pattern.search(line)
                            if m:
                                hits.append((full, lineno, line.strip()[:120]))
                            if len(hits) >= 200:
                                break
                except OSError:
                    continue
                if len(hits) >= 200:
                    break
            if len(hits) >= 200:
                break
        self._show_todo_results(hits)
        self.terminal.log(f"Found {len(hits)} TODO/FIXME markers.")

    def _show_todo_results(self, hits):
        t = self.theme
        win = tk.Toplevel(self.root)
        win.title("TODO / FIXME")
        win.configure(bg=t["bg"])
        win.geometry("720x420")
        tk.Label(win, text=f"{len(hits)} markers in this workspace",
                 bg=t["bg"], fg=t["text"], font=(FONT_UI, 12, "bold")
                 ).pack(anchor="w", padx=16, pady=(14, 6))
        if not hits:
            tk.Label(win, text="Nothing to do — you're actually done. 🎉",
                     bg=t["bg"], fg=t["text_secondary"], font=(FONT_UI, 10)
                     ).pack(pady=30)
        box = tk.Frame(win, bg=t["bg"])
        box.pack(fill=tk.BOTH, expand=True, padx=10)
        canvas = tk.Canvas(box, bg=t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=canvas.yview)
        rows = tk.Frame(canvas, bg=t["bg"])
        rows.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=rows, anchor="nw", width=690)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(cw, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        for path, lineno, text in hits[:200]:
            row = tk.Frame(rows, bg=t["card"], highlightthickness=1,
                           highlightbackground=t["card_border"])
            row.pack(fill=tk.X, pady=2, padx=2)
            head = tk.Label(row, anchor="w", justify=tk.LEFT, wraplength=640,
                            text=f"{os.path.basename(path)}  ·  line {lineno}",
                            bg=t["card"], fg=t.accent,
                            font=(FONT_UI, 9, "bold"), cursor="hand2")
            head.pack(anchor="w", padx=10, pady=(6, 0))
            body = tk.Label(row, anchor="w", justify=tk.LEFT, wraplength=640,
                            text=text, bg=t["card"], fg=t["text_secondary"],
                            font=(FONT_MONO, 8))
            body.pack(anchor="w", padx=10, pady=(0, 6))
            for w in (head, body):
                w.bind("<Button-1>", lambda e, p=path, l=lineno:
                       self.open_search_match(p, l, 0))

    def goto_line_dialog(self):
        if not self.editor.file_path and not self.editor.get_content():
            return
        value = self._ask("Go to Line", "Line number:")
        if value and value.isdigit():
            if self.editor.goto_line(int(value)):
                self._update_cursor_pos()
            else:
                self.toast("No such line", "error")

    # ------------------------------------------------------------- updater
    def check_for_updates(self, manual=False):
        """GitHub releases check — stdlib only, never blocks the UI."""
        if self._updater_shown or self.smoke_test:
            if manual and self.smoke_test:
                self.toast("Update checks are off in smoke-test mode", "info")
            return

        def worker():
            result = {"state": "error", "latest": "", "url": "",
                      "notes": []}
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/DXN1-termux/DXN1-STUDIO/"
                    "releases/latest",
                    headers={"User-Agent": f"DXN1-Studio/{APP_VERSION}",
                             "Accept": "application/vnd.github+json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8", "replace"))
                tag = (data.get("tag_name") or "").lstrip("v")
                lines = [ln.lstrip("-* ").strip() for ln in
                         (data.get("body") or "").splitlines()
                         if ln.strip().startswith(("-", "*"))][:3]
                result = {"state": "ok", "latest": tag, "notes": lines,
                          "url": data.get("html_url") or REPO_URL}
            except Exception:
                pass

            def finish():
                self._updater_shown = False
                if result["state"] != "ok":
                    if manual:
                        self.toast("Couldn't reach GitHub — try later",
                                   "error")
                    return
                try:
                    newer = updater.is_newer(result["latest"], APP_VERSION)
                except ValueError:
                    newer = False
                if newer:
                    if self._update_should_nag(result["latest"], manual):
                        # the full-screen Update Portal — no sneaky toasts
                        updater.UpdatePortal(self, result["latest"],
                                             result["url"], result["notes"])
                        self.terminal.log(f"Update available: v{APP_VERSION} → "
                                          f"v{result['latest']} — {result['url']}")
                    else:
                        # DS2 v2.35: the polite updater — you declined this
                        # exact version, so the boot check stays quiet.
                        self.terminal.log(
                            f"Update v{result['latest']} is out — you asked "
                            "to skip it. Run `update` any time to reconsider.")
                elif manual:
                    self.toast(f"You're on the latest "
                               f"(v{APP_VERSION})", "success")

            self.root.after(0, finish)

        self._updater_shown = True
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _ver_tuple(version):
        parts = re.findall(r"\d+", version or "")
        if not parts:
            raise ValueError(version)
        return tuple(int(p) for p in parts[:3]) + (0,) * (3 - len(parts[:3]))

    def _update_should_nag(self, latest, manual=False):
        """DS2 v2.35: the polite updater — honour "I'll stay on this
        version". Manual checks (palette / menu / terminal ``update``)
        always show the portal; the automatic boot check stays quiet
        for a version you already declined. A newer release than the
        skipped one nags again, as it should."""
        if manual:
            return True
        try:
            skipped = str(self.config.get("updater_skip_version", "") or "")
            return skipped != str(latest or "")
        except Exception:  # noqa: BLE001 — default is to speak up
            return True

    def _schedule_update_check(self):
        """DS2 v2.36: the update heartbeat — boot check + slow re-check.

        One ``after`` loop drives both: the first tick (4s after boot)
        is the classic boot check, every later tick waits
        ``update_check_secs`` (clamped 15 min..6 h). Gated by the
        ``check_updates`` master switch; the polite skip memory
        applies like everywhere else. Always reschedules while the
        root lives."""
        try:
            if not self.smoke_test and \
                    self.config.get("check_updates", True):
                self.check_for_updates(manual=False)
        except Exception:
            errors.log_exception("update heartbeat", quiet=True)
        try:
            _secs = int(self.config.get("update_check_secs", 3600)
                        or 3600)
            _secs = max(900, min(21600, _secs))
            self._update_check_job = self.root.after(
                _secs * 1000, self._schedule_update_check)
        except Exception:  # noqa: BLE001 — dying root is fine
            pass

    # ------------------------------------------------- DS2 v2.39 deps watch
    def _deps_watch_state(self):
        """Honest state for the watch chip, computed cheaply (no scan):
        off — the watcher is disabled in settings
        nows — no workspace open
        absent — never scanned here (no usable cached report)
        cached — the stored deps report matches the workspace
        stale — the workspace moved since the report was stored
        Returns ``(state, missing_n)`` — v2.40 severity: the stored
        report's missing-import count rides along for the cached
        state so the chip can turn red, not just amber."""
        if not self.config.get("deps_watch", True):
            return ("off", 0)
        if not self.project_dir:
            return ("nows", 0)
        try:
            from . import depcheck as _dc
            st = _dc.cache_state(self.project_dir)
            return (st.get("state", "absent"),
                    len(st.get("missing") or []))
        except Exception:  # noqa: BLE001 — the chip never raises
            return ("absent", 0)

    def _update_depswatch(self, force=False):
        """Redraw the dependency watch chip for the current state.

        The probe stats every scanned file, so it is throttled to one
        pass per 3 seconds unless ``force`` (a deps run or a click —
        both just changed the world themselves). v2.40 severity:
        amber for drift, red for missing imports, muted when happy.
        Never raises."""
        import time as _time
        try:
            now = _time.time()
            if not force and (now - self._deps_probed_at) < 3.0:
                return
            self._deps_probed_at = now
            state, missing_n = self._deps_watch_state()
            sig = "%s:%d" % (state, missing_n)
            if sig == self._deps_sig_state:
                return
            self._deps_sig_state = sig
            chip = self.status_deps
            t = self.theme
            if state == "stale":
                chip.config(text="● deps drift", fg="#f59e0b",
                            font=(FONT_UI, 9, "bold"))
            elif state == "cached" and missing_n:
                chip.config(text="● deps %d missing" % missing_n,
                            fg="#f85149",
                            font=(FONT_UI, 9, "bold"))
            elif state == "cached":
                chip.config(text="deps ok", fg=t["text_muted"],
                            font=(FONT_UI, 9))
            elif state == "absent":
                chip.config(text="deps —", fg=t["text_muted"],
                            font=(FONT_UI, 9))
            else:  # off / nows — quietly empty
                chip.config(text="", fg=t["text_muted"],
                            font=(FONT_UI, 9))
        except Exception:  # noqa: BLE001 — a chip must never break typing
            pass

    def _deps_chip_click(self):
        """Click the drift chip: rescan deps and redraw. v2.41 one-
        gesture repair: when the chip is RED (the last report found
        imports missing from requirements) the click also drops
        ``deps fix`` into the terminal input — Enter runs it, the
        user stays in charge."""
        red = False
        try:
            state, missing_n = self._deps_watch_state()
            red = state == "cached" and missing_n > 0
        except Exception:  # noqa: BLE001 — the chip never raises
            red = False
        self._run_depcheck()
        self._update_depswatch(force=True)
        if red:
            self._prefill_terminal("deps fix")
            self.terminal.log("deps fix is queued in the input — "
                              "press Enter to pin the missing "
                              "imports")

    def _deps_queue_fix(self):
        """DS2 v2.42 — the menu's repair row: same one-gesture flow
        as the red chip click (queue ``deps fix``, Enter runs it —
        nothing fires by accident)."""
        self._prefill_terminal("deps fix")
        self.terminal.log("deps fix is queued in the input — "
                          "press Enter to pin the missing imports")

    def _deps_menu_entries(self):
        """DS2 v2.42 — the deps-chip context menu's rows as
        ``(label, command)`` pairs (``("---", None)`` = separator).
        The repair row appears only when the last report actually
        found missing imports — honest per state, same contract as
        the branch chip's menu. v2.51 — the rows wear the chip's
        severity: red repair/rescan when imports are missing, amber
        rescans when the cache drifted. Pure data, rendered by
        `_deps_chip_menu`."""
        state, missing_n = "absent", 0
        try:
            state, missing_n = self._deps_watch_state()
        except Exception:  # noqa: BLE001 — menu still opens
            pass
        red = state == "cached" and missing_n > 0
        amber = state == "stale"
        err_c, amber_c = "#f85149", "#f59e0b"   # the chip's own palette
        entries = [("Rescan deps",
                    lambda: (self._run_depcheck(),
                             self._update_depswatch(force=True)),
                    "", amber_c if amber and not red else None)]
        if red:
            entries.append(("Queue deps fix (%d missing)" % missing_n,
                            self._deps_queue_fix, "", err_c))
            # DS2 v2.53 — the repair row's quiet helper: a ready
            # ``pip install`` line for every missing import, pins via
            # depcheck.suggested_pins (PIL becomes pillow). A menu row
            # that hands you the fix, not just the diagnosis.
            entries.append(("Copy pip install command",
                            self._deps_copy_install))
        entries.append(("Fresh rescan (bypass cache)",
                        lambda: (self._run_depcheck(force=True),
                                 self._update_depswatch(force=True)),
                        "", err_c if red else
                        (amber_c if amber else None)))
        entries.append(("---", None))
        entries.append(("Deps watch on/off", self._deps_watch_toggle))
        entries.append(("Rescan chip",
                        lambda: self._update_depswatch(force=True)))
        return entries

    def _deps_chip_menu(self, event=None):
        """DS2 v2.42 — right-click the drift chip: the lane's actions
        in one themed menu (rescan, the repair row when the chip is
        red, a cache-bypassing fresh scan, the watch toggle). Never
        raises."""
        self._render_chip_menu(self._deps_menu_entries(), event)

    def _deps_copy_install(self):
        """DS2 v2.53 — the deps menu's copy row: a ready ``pip install``
        line for every missing import, straight onto the clipboard.
        The pins come from ``depcheck.suggested_pins`` over the stored
        report's missing list (PIL → pillow, yaml → pyyaml). Honest
        when nothing is missing; never raises."""
        try:
            pins = []
            try:
                from . import depcheck as _dc
                if self.project_dir:
                    st = _dc.cache_state(self.project_dir)
                    pins = _dc.suggested_pins(st.get("missing") or [])
            except Exception:  # noqa: BLE001 — no report, no pins
                pins = []
            if not pins:
                self.toast("No missing imports to install", "info")
                return
            cmd = "pip install " + " ".join(pins)
            self.root.clipboard_clear()
            self.root.clipboard_append(cmd)
            self.toast("Copied: %s" % cmd, "success")
            try:
                self.terminal.log("deps: %s" % cmd)
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001 — a menu row must never raise
            pass

    # ------------------------------------------- DS2 v2.53 keyboard reach
    _CHIP_MENU_ALIASES = {
        "git": "git", "branch": "git", "source control": "git",
        "deps": "deps", "env": "deps", "dependencies": "deps",
        "scribe": "scribe", "writing": "scribe",
        "sesave": "sesave", "autosave": "sesave", "session": "sesave",
    }

    def _chip_menu_registry(self):
        """DS2 v2.53 — the four chip menus the keyboard can reach, as
        ``kind → (entries_fn, chip_widget, human name)``. Resolved at
        call time so late-built widgets and rebound methods are always
        current. Never raises."""
        return {
            "git": (self._git_menu_entries, self.status_git, "branch"),
            "deps": (self._deps_menu_entries, self.status_deps, "deps"),
            "scribe": (self._scribe_menu_entries, self.status_scribe,
                       "scribe"),
            "sesave": (self._sesave_menu_entries, self.status_sesave,
                       "autosave"),
        }

    def _open_chip_menu_keyboard(self, kind):
        """DS2 v2.53 — the keyboard's door into a chip menu. Opens the
        named chip's menu anchored just above its statusbar chip, in
        "keyboard" mode: the grab is kept (a palette row, an
        accelerator or this verb is a REAL user gesture — the posted
        menu hears Enter/arrows/digits immediately) and the usual
        unpost poller releases it the moment the menu closes. Unknown
        or unavailable kinds answer honestly with ``False``; a menu
        must never break typing, so this never raises."""
        try:
            key = str(kind or "").strip().lower()
            key = self._CHIP_MENU_ALIASES.get(key, "")
            reg = self._chip_menu_registry()
            if key not in reg:
                return False
            entries_fn, chip, _name = reg[key]
            x = y = 0
            try:
                x = chip.winfo_rootx() + 2
                y = chip.winfo_rooty() - 6
            except Exception:  # noqa: BLE001 — geometry is garnish
                pass
            self._render_chip_menu(entries_fn(), None, mode="keyboard",
                                   at=(x, y))
            return True
        except Exception:  # noqa: BLE001 — never break typing
            return False

    # --------------------------------------------- DS2 v2.43 scribe chip menu
    def _scribe_menu_entries(self):
        """DS2 v2.43 — the scribe chip's context menu rows as
        ``(label, command)`` pairs: the session summary toast, the
        writing-goal flow and a meter reset. Pure data, rendered by
        the shared `_render_chip_menu`."""
        return [("Session summary", self._scribe_click),
                ("Set writing goal…", self._scribe_goal_from_menu),
                ("Reset session meter", self._scribe_reset_from_menu)]

    def _scribe_goal_from_menu(self):
        """DS2 v2.44 — a themed goal dialog: type the count, Set or
        Enter — nothing changes until then (an explicit gesture
        commits it, stricter than the old terminal prefill)."""
        chip = self.scribe_chip
        if chip is None:
            self.terminal.log("scribe chip unavailable")
            return
        try:
            from .scribe import open_goal_dialog

            def _apply(goal):
                chip.set_goal(int(goal))
                try:
                    self.config.set("scribe_goal_words", int(goal))
                except Exception:  # noqa: BLE001
                    pass
                try:
                    self.status_scribe.configure(text=chip.text())
                except Exception:  # noqa: BLE001
                    pass
                self.toast("Writing goal set to %d words" % int(goal),
                           "success")
                self.terminal.log("scribe goal set to %d words"
                                  % int(goal))

            open_goal_dialog(self.root, self.theme,
                             int(chip.goal_words or 0), on_set=_apply)
        except Exception:  # noqa: BLE001 — a menu row must never raise
            self.terminal.log("scribe goal dialog unavailable here")

    def _scribe_reset_from_menu(self):
        """DS2 v2.43 — zero the writing meter: words, wpm and the
        elapsed clock restart from now (the goal is preserved).
        Never raises."""
        try:
            chip = self.scribe_chip
            if chip is None:
                self.terminal.log("scribe chip unavailable")
                return
            chip.reset()
            self.status_scribe.configure(text=chip.text())
            self.toast("Scribe meter reset — fresh counts from now",
                       "info")
        except Exception:  # noqa: BLE001 — a menu row must never raise
            pass

    def _scribe_chip_menu(self, event=None):
        """DS2 v2.43 — right-click the scribe chip: summary, goal and
        reset in one themed menu. Never raises."""
        self._render_chip_menu(self._scribe_menu_entries(), event)

    # --------------------------------------------- DS2 v2.43 sesave chip menu
    def _sesave_menu_entries(self):
        """DS2 v2.43 — the session-autosave chip's context menu rows:
        snapshot now, the snapshot browser, and the autosave switch
        (the row reads the live config when clicked — honest). Pure
        data, rendered by the shared `_render_chip_menu`."""
        return [("Snapshot session now", self.save_session_now),
                ("Browse snapshots…", self.open_session_restore),
                ("---", None),
                ("Autosave on/off", self._sesave_autosave_toggle)]

    def _sesave_autosave_toggle(self):
        """DS2 v2.43 — flip ``session_autosave`` live: the 60s loop
        reads the config every tick, so the switch lands on the next
        beat. Honest feedback either way. Never raises."""
        try:
            cur = bool(self.config.get("session_autosave", True))
            self.config.set("session_autosave", not cur)
            state = "off" if cur else "on"
            self.toast("Session autosave %s" % state, "info")
            try:
                self.terminal.log("session autosave is now %s — the "
                                  "60s loop picks it up on its next "
                                  "beat" % state)
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001 — a menu row must never raise
            pass

    def _sesave_chip_menu(self, event=None):
        """DS2 v2.43 — right-click the autosave chip: snapshot,
        browse, toggle in one themed menu. Never raises."""
        self._render_chip_menu(self._sesave_menu_entries(), event)

    # ---------------------------------------------------- DS2 v2.44 activity window
    def _activity_path(self):
        """DS2 v2.45 — where the activity ring persists: beside
        config.json in the studio's config dir. Resolved at call
        time so tests can redirect CONFIG_DIR. Never raises."""
        try:
            from . import config as _cfgmod
            return os.path.join(_cfgmod.CONFIG_DIR, "activity.json")
        except Exception:  # noqa: BLE001 — a sane fallback
            return os.path.join(os.path.expanduser("~"),
                                ".dxn1-studio", "activity.json")

    def _activity_open(self):
        """DS2 v2.44 — the Activity window: every notification the
        studio has whispered, live-filtered, click a row to copy it.
        v2.46 — the window can also send the receipts somewhere:
        export_dir seeds its Save-as dialog, on_export gets the path
        for honest feedback. Never raises."""
        log = getattr(self, "activity_log", None)
        if log is None:
            self.terminal.log("activity log unavailable here")
            return
        try:
            from .activity import open_activity, save_json
            open_activity(self.root, self.theme, log,
                          on_copy=lambda m: self.toast(
                              ("Copied: %s" % m) if len(m) <= 48
                              else "Copied %d characters" % len(m),
                              "info"),
                          on_change=lambda: save_json(
                              log, self._activity_path()),
                          export_dir=os.path.dirname(
                              self._activity_path()),
                          on_export=self._activity_exported)
        except Exception:  # noqa: BLE001 — best-effort window
            self.terminal.log("activity log unavailable here")

    def _activity_exported(self, path):
        """DS2 v2.46 — the receipts file was written; the app
        acknowledges it the usual way, naming the format it chose
        (v2.47: the extension decides). Never raises."""
        try:
            ext = os.path.splitext(str(path))[1].lower()
            fmt = ("json" if ext == ".json"
                   else "csv" if ext == ".csv" else "text")
            self.toast("Receipts saved as %s → %s" % (fmt, path),
                       "success")
        except Exception:  # noqa: BLE001
            pass
        try:
            self.terminal.log("activity receipts written to %s" % path)
        except Exception:  # noqa: BLE001
            pass

    def _activity_copy_all(self):
        """DS2 v2.46 — every receipt to the clipboard, oldest first.
        An empty ring is told honestly. Never raises."""
        log = getattr(self, "activity_log", None)
        if log is None:
            self.terminal.log("activity log unavailable here")
            return
        try:
            from .activity import export_text
            text = export_text(log.entries())
            if not text:
                self.toast("No receipts to copy yet", "info")
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            n = log.count()
            self.toast("Copied %d receipt%s to the clipboard"
                       % (n, "" if n == 1 else "s"), "success")
        except Exception:  # noqa: BLE001 — a verb must never raise
            self.terminal.log("activity copy unavailable here")

    def _activity_export_to(self, path=None, fmt=None):
        """DS2 v2.46 — every receipt to a file: the given path, or a
        timestamped one beside activity.json. v2.47 — the format
        follows the extension, or the explicit ``json``/``csv``
        argument names the default file's extension too. Never
        raises."""
        log = getattr(self, "activity_log", None)
        if log is None:
            self.terminal.log("activity log unavailable here")
            return
        try:
            import time as _time_mod
            from .activity import export_to
            p = str(path or "").strip()
            if not p:
                f = fmt if fmt in ("json", "csv") else "txt"
                p = os.path.join(
                    os.path.dirname(self._activity_path()),
                    "activity-export-%s.%s"
                    % (_time_mod.strftime("%Y%m%d-%H%M%S"), f))
            got = export_to(log, p, fmt=fmt)
            if got:
                self._activity_exported(got)
            else:
                self.toast("Could not write the receipts file", "error")
        except Exception:  # noqa: BLE001 — a verb must never raise
            self.terminal.log("activity export unavailable here")

    def _activity_autosnap_check(self, force=False):
        """DS2 v2.51 — the diary writes itself: when the gate is on
        and the clock says due, write the chronological JSON snapshot
        into exports/, prune the old ones, and acknowledge with a
        receipt of its own. Polite: checked 8s after boot (the toast
        layer is alive by then) and re-armed every half hour after;
        a full disk is a silent non-event. Never raises."""
        path = None
        pruned = 0
        try:
            log = getattr(self, "activity_log", None)
            if log is not None:
                from .activity import autosnap
                path, pruned = autosnap(self.activity_log, self.config,
                                        force=force)
                if path:
                    msg = ("Nightly receipts snapshot → %s" % path)
                    if pruned:
                        msg += " (%d old pruned)" % pruned
                    self.toast(msg, "success")
                    try:
                        self.terminal.log(msg)
                    except Exception:  # noqa: BLE001
                        pass
        except Exception:  # noqa: BLE001 — a snapshot must never raise
            pass
        finally:
            try:
                if self.root.winfo_exists():
                    self.root.after(30 * 60 * 1000,
                                    self._activity_autosnap_check)
            except Exception:  # noqa: BLE001 — dying quietly
                pass

    def _git_menu_entries(self):
        """DS2 v2.41 — the branch-chip context menu's rows, as
        ``(label, command)`` pairs (``("---", None)`` = separator).
        Repo actions appear only when the chip is actually watching
        a repository. Pure data — trivially testable, rendered by
        `_git_chip_menu`."""
        entries = [("Open Source Control",
                    lambda: self.show_sidebar_view("git"))]
        st = None
        try:
            st = self._git_watch_state()
        except Exception:  # noqa: BLE001 — menu still opens
            st = None
        if st and st.get("repo"):
            entries.append(("Commit graph", self._open_git_graph_chip))
            entries.append(("Stage all changes",
                            lambda: self.run_command("git add -A")))
            entries.append(("Commit staged…",
                            self._commit_staged_from_chip,
                            "Enter"))
            entries.append(("Draft AI commit message",
                            self._ai_commit_from_chip))
            # DS2 v2.52 — the sync rows wear the branch's divergence,
            # the same severity language the deps menu learned in
            # v2.51: red when the branch diverged (push/pull blind is
            # how commits get lost), amber when one plain push or
            # pull would settle it, silent when already in sync.
            try:
                ahead = int(st.get("ahead") or 0)
                behind = int(st.get("behind") or 0)
            except Exception:  # noqa: BLE001 — junk counts stay quiet
                ahead = behind = 0
            diverged = ahead > 0 and behind > 0
            sync_c = "#f85149" if diverged else \
                ("#f59e0b" if (ahead or behind) else None)
            entries.append(("Push to origin",
                            lambda: self.run_command("git push"),
                            "", sync_c if ahead else None))
            entries.append(("Pull from upstream",
                            lambda: self.run_command("git pull"),
                            "", sync_c if behind else None))
            # DS2 v2.54 — the copy sibling, state-aware like the deps
            # menu's pip row: diverged offers the recovery line, one
            # move from sync offers the plain command, in sync stays
            # silent (a row must earn its place).
            if diverged:
                entries.append(("Copy recovery command",
                                lambda: self._git_copy_command(
                                    "recovery")))
            elif ahead:
                entries.append(("Copy push command",
                                lambda: self._git_copy_command("push")))
            elif behind:
                entries.append(("Copy pull command",
                                lambda: self._git_copy_command("pull")))
            branch = str(st.get("branch") or "")
            if branch:
                entries.append(("Copy branch name",
                                lambda: self._copy_branch_name(branch)))
        entries.append(("---", None))
        entries.append(("Rescan",
                        lambda: self._update_gitchip(force=True)))
        return entries

    def _render_chip_menu(self, entries, event=None, mode=None, at=None):
        """DS2 v2.42 — one themed popup renderer for every statusbar
        chip menu (git, deps, …): ``(label, command)`` rows,
        ``("---", None)`` = separator, popped at the cursor.
        v2.47 — a row may be ``(label, command, accel)`` and the
        accelerator is advertised right-aligned, but ONLY where a
        real keybinding exists (the git menu's Enter-to-commit).
        v2.51 — a row may be ``(label, command, accel, color)`` and
        the label takes that foreground: the deps menu paints its
        repair rows with the same severity the chip itself wears.
        v2.52 — the menu learns the keyboard. The X grab Tk takes at
        post time is now KEPT while the menu is up (the old
        release-immediately left the posted menu deaf: every key
        kept flowing to the editor), and an unpost poller releases
        the grab the moment the menu closes and hands the focus
        back. The first activatable row wakes up active so Enter
        takes it straight away; Up/Down/Return/Escape/first-letter
        stay Tk's own menu traversal; Home/End and digits 1-9 are
        wired on top. Introspectable: the posted menu carries
        ``_ds2_rows`` and the app keeps ``self._last_chip_menu``.
        v2.53 — the menus come to you: ``mode`` names how the menu
        was opened — "gesture" (a real pointer event; the default
        when ``event`` is given), "program" (no event, no gesture —
        the tests' way in, grab released at once, exactly the v2.52
        seam) and "keyboard" (opened by a REAL user gesture that
        wasn't a pointer — a palette row, an accelerator, a verb:
        the grab is kept so the posted menu hears Enter/arrows
        immediately, and ``at`` anchors it just above its chip
        instead of at a cursor that isn't there). Same poller, same
        cleanup contract in every mode. The popup itself is
        best-effort — a menu must never break typing."""
        effective = mode or ("gesture" if event is not None
                             else "program")
        try:
            t = self.theme
            menu = tk.Menu(self.root, tearoff=0, bg=t["sidebar"],
                           fg=t["text"], activebackground=t["hover"],
                           activeforeground=t["text"],
                           font=(FONT_UI, 9))
            for entry in entries:
                label, cmd = entry[0], entry[1]
                accel = str(entry[2]) if len(entry) > 2 else ""
                color = entry[3] if len(entry) > 3 else None
                if label == "---":
                    menu.add_separator()
                elif accel or color:
                    kw = {}
                    if accel:
                        kw["accelerator"] = accel
                    if color:
                        kw["foreground"] = color
                    menu.add_command(label=label, command=cmd, **kw)
                else:
                    menu.add_command(label=label, command=cmd)
            self._wire_menu_keys(menu)
            try:
                prev_focus = self.root.focus_get()
            except Exception:  # noqa: BLE001 — focus is garnish
                prev_focus = None
            try:
                x = getattr(event, "x_root", 0) or 0
                y = getattr(event, "y_root", 0) or 0
                if event is None and at:
                    try:            # v2.53 — an explicit anchor (the chip)
                        x, y = int(at[0]), int(at[1])
                    except Exception:  # noqa: BLE001 — junk anchor → 0,0
                        pass
                if effective == "keyboard" and event is None:
                    try:            # float just ABOVE the chip, not on it
                        h = int(menu.winfo_reqheight())
                        if h > 0:
                            y = max(0, y - h - 6)
                    except Exception:  # noqa: BLE001 — garnish geometry
                        pass
                menu.tk_popup(x, y)
            finally:
                # v2.52 — a menu opened by a REAL gesture keeps Tk's
                # grab while it is up: that grab is exactly what routes
                # keys to the posted menu, and the unpost poller below
                # releases it the moment the menu closes. v2.53 — a
                # keyboard open (palette row / accelerator / verb) is
                # just as real a gesture, so "keyboard" keeps the grab
                # too. A programmatic open (event=None, no mode — the
                # tests' way in) has no gesture to serve and releases
                # at once, so nothing outlives the call: Tk's grab
                # state is per-DISPLAY and process-wide, and a grab
                # left held at teardown keeps swallowing pointer
                # events from whatever runs next (found by the pytest
                # interps).
                if effective == "program":
                    menu.grab_release()
            try:
                menu._ds2_rows = [tuple(e) for e in entries]
            except Exception:  # noqa: BLE001 — introspection is garnish
                pass
            try:
                rows = self._menu_command_rows(menu)
                if rows:
                    menu.activate(rows[0])
            except Exception:  # noqa: BLE001 — best-effort wake-up
                pass
            self._last_chip_menu = menu
            self._arm_menu_unpost_poll(menu, prev_focus)
        except Exception:  # noqa: BLE001 — a menu must never break typing
            pass

    @staticmethod
    def _menu_command_rows(menu):
        """DS2 v2.52 — the menu-entry indexes of every activatable
        row (``type(i) == "command"``): Home/End/digits count in
        THIS space, so separators never count and a row's number is
        the number it is invoked by. Empty menus answer honestly:
        ``[]``. Never raises."""
        rows = []
        try:
            end = menu.index("end")
            if end is None:
                return rows
            for i in range(end + 1):
                try:
                    if menu.type(i) == "command":
                        rows.append(i)
                except Exception:  # noqa: BLE001 — one bad row
                    pass
        except Exception:  # noqa: BLE001 — a dead menu owns nothing
            pass
        return rows

    def _wire_menu_keys(self, menu):
        """DS2 v2.52 — the chip menu's extra keys, bound on the menu
        itself: Home/End jump to the first/last activatable row and
        digits 1-9 run the Nth one (the same trick the AI
        quick-actions launcher learned in v2.50). Up/Down/Return/
        Escape/first-letter stay Tk's own menu traversal, which the
        kept grab now feeds again. The handlers are kept on the
        menu as ``_ds2_keys`` so tests drive them without scraping
        labels. Never raises."""
        try:
            def _home(_event=None):
                try:
                    rows = self._menu_command_rows(menu)
                    if rows:
                        menu.activate(rows[0])
                except Exception:  # noqa: BLE001
                    pass
                return "break"

            def _end(_event=None):
                try:
                    rows = self._menu_command_rows(menu)
                    if rows:
                        menu.activate(rows[-1])
                except Exception:  # noqa: BLE001
                    pass
                return "break"

            def _run_nth(n):
                def _go(_event=None):
                    try:
                        rows = self._menu_command_rows(menu)
                        if 1 <= n <= len(rows):
                            idx = rows[n - 1]
                            menu.activate(idx)
                            menu.invoke(idx)
                    except Exception:  # noqa: BLE001
                        pass
                    return "break"
                return _go

            menu.bind("<Key-Home>", _home)
            menu.bind("<Key-End>", _end)
            for d in range(1, 10):
                menu.bind("<Key-%d>" % d, _run_nth(d))
            try:
                menu._ds2_keys = {"home": _home, "end": _end,
                                  "nth": _run_nth}
            except Exception:  # noqa: BLE001 — introspection is garnish
                pass
        except Exception:  # noqa: BLE001 — a menu must never break typing
            pass

    def _arm_menu_unpost_poll(self, menu, prev_focus,
                              every_ms=40, attempts=1500):
        """DS2 v2.52 — the other half of the keyboard fix. Tk's grab
        stays on the posted menu (that is exactly what routes key
        events to it while it is up); this poller watches for the
        unpost and THEN releases the grab and hands the focus back
        to wherever it was — the old code released before the menu
        was even on screen, so the menu heard keys but the editor
        kept them. Bounded (about a minute), idempotent, and it
        dies quietly with its menu. Never raises. Exposed on the
        menu as ``_ds2_poll`` so tests can drive it without a
        sleep."""
        try:
            def poll(left):
                try:
                    try:
                        alive = menu.winfo_exists()
                    except Exception:  # noqa: BLE001
                        alive = False
                    if not alive:
                        return
                    try:
                        mapped = menu.winfo_ismapped()
                    except Exception:  # noqa: BLE001
                        mapped = False
                    if not mapped or left <= 0:
                        try:
                            menu.grab_release()
                        except Exception:  # noqa: BLE001
                            pass
                        try:
                            menu._ds2_focus_back = prev_focus
                        except Exception:  # noqa: BLE001
                            pass
                        try:
                            if (prev_focus is not None
                                    and prev_focus.winfo_exists()):
                                prev_focus.focus_set()
                        except Exception:  # noqa: BLE001
                            pass
                        return
                    menu.after(every_ms, lambda: poll(left - 1))
                except Exception:  # noqa: BLE001 — polling stays quiet
                    pass

            try:
                menu._ds2_poll = lambda: poll(attempts)
            except Exception:  # noqa: BLE001 — introspection is garnish
                pass
            menu.after(every_ms, lambda: poll(attempts))
        except Exception:  # noqa: BLE001 — a menu must never break typing
            pass

    def _git_chip_menu(self, event=None):
        """DS2 v2.41 — right-click the branch chip: the lane's actions
        in one themed menu (open Source Control, commit graph, stage
        everything, AI commit draft, push/pull, copy the branch name,
        rescan). Never raises."""
        self._render_chip_menu(self._git_menu_entries(), event)

    def _ai_commit_from_chip(self):
        """DS2 v2.42 — the branch chip menu's AI entry: bring the
        Source Control panel forward and fire its ✨ AI message flow
        (the panel guards repo/brain state itself — the menu only
        opens the door). Never raises."""
        try:
            self.show_sidebar_view("git")
        except Exception:  # noqa: BLE001 — the panel may be absent
            pass
        try:
            self.git_view.ai_message()
        except Exception:  # noqa: BLE001 — best-effort draft
            self.terminal.log("git: AI message unavailable here")

    def _commit_staged_from_chip(self):
        """DS2 v2.43 — the branch chip menu's commit entry: bring the
        Source Control panel forward and put the cursor in the
        commit message box (the panel guards repo state itself —
        the menu only opens the door). Never raises."""
        try:
            self.show_sidebar_view("git")
        except Exception:  # noqa: BLE001 — the panel may be absent
            pass
        try:
            self.git_view.focus_message()
        except Exception:  # noqa: BLE001 — best-effort focus
            self.terminal.log("git: commit box unavailable here")

    def _open_git_graph_chip(self):
        """Commit graph from the chip menu — same window the palette
        and the Source Control panel open. Never raises."""
        try:
            from . import gitgraph as _gg
            _gg.open_graph(self.root, self.theme, self.project_dir,
                           on_log=lambda m: None)
        except Exception:  # noqa: BLE001 — best-effort window
            self.terminal.log("git graph unavailable here")

    def _git_copy_command(self, kind):
        """DS2 v2.54 — the branch menu's copy sibling: a ready-to-run
        git line for the branch's state — ``git pull --rebase && git
        push`` when diverged, the plain push/pull when one move would
        settle it — straight onto the clipboard, toast + terminal
        receipt confirming. Junk kinds are ignored. Never raises."""
        try:
            cmd = {"recovery": "git pull --rebase && git push",
                   "push": "git push",
                   "pull": "git pull"}.get(str(kind or ""))
            if not cmd:
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(cmd)
            self.toast("Copied: %s" % cmd, "success")
            try:
                self.terminal.log("git: %s (copied — run it anywhere)"
                                  % cmd)
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001 — a menu row must never raise
            pass

    def _copy_branch_name(self, branch):
        """Copy the branch name to the clipboard + a quiet toast."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(branch)
            self.toast("Copied: %s" % branch, "info")
        except Exception:  # noqa: BLE001 — clipboard is garnish
            pass

    def _deps_watch_toggle(self, arg=""):
        """``deps watch [on|off]`` — the statusbar drift chip, and the
        30s probe behind it. Bare ``deps watch`` flips the switch."""
        arg = str(arg or "").strip().lower()
        cur = bool(self.config.get("deps_watch", True))
        if arg in ("on", "1", "true"):
            new = True
        elif arg in ("off", "0", "false"):
            new = False
        elif arg == "":
            new = not cur
        else:
            self.terminal.log("usage: deps watch [on|off] — amber when "
                              "imports drift, red when they are missing "
                              "from requirements")
            return
        self.config.set("deps_watch", new)
        self._deps_sig_state = ""      # force a redraw
        self._update_depswatch(force=True)
        self.terminal.log(
            "deps watch %s — %s" % (
                "on" if new else "off",
                "the chip turns amber when the workspace drifts and "
                "red when imports are missing from requirements"
                if new else "the drift chip is hidden; `deps` still "
                            "works exactly as before"))

    def _deps_watch_poll(self):
        """Every 30s: notice silent drift (files changed outside the
        studio) and light the deps chip, then give the git lane chip
        the same courtesy (v2.40 — one poll, both lanes). Never
        raises, never stacks."""
        try:
            self._update_depswatch()
        except Exception:  # noqa: BLE001 — polling must stay quiet
            pass
        try:
            self._update_gitchip()
        except Exception:  # noqa: BLE001 — polling must stay quiet
            pass
        try:
            self.root.after(30000, self._deps_watch_poll)
        except Exception:  # noqa: BLE001 — dying root is fine
            pass

    # ----------------------------------------------- DS2 v2.40 git chip
    def _git_watch_state(self):
        """Honest state for the git lane chip (one cheap `git status`
        call, throttled by the caller): ``None`` when the chip should
        sit quiet (watcher off, no workspace, or the folder is not a
        repository — plain folders deserve no nagging), else the
        ``repo_state`` dict."""
        if not self.config.get("git_watch", True):
            return None
        if not self.project_dir:
            return None
        try:
            from .gitpanel import repo_state
            st = repo_state(self.project_dir)
            return st if st.get("repo") else None
        except Exception:  # noqa: BLE001 — the chip never raises
            return None

    def _update_gitchip(self, force=False):
        """Redraw the git lane chip: the branch name in muted text when
        everything is committed and in sync, amber ``branch ●N`` when
        N files wait to be committed (plus ↑/↓ arrows when the branch
        diverges from upstream), amber arrows alone when the branch is
        clean but ahead/behind. One git subprocess max per 3 seconds
        unless ``force``. Never raises."""
        import time as _time
        try:
            now = _time.time()
            if not force and (now - self._git_probed_at) < 3.0:
                return
            self._git_probed_at = now
            st = self._git_watch_state()
            sig = ("", 0, 0, 0) if st is None else (
                st.get("branch", ""), st.get("dirty", 0),
                st.get("ahead", 0), st.get("behind", 0))
            if sig == self._git_sig_state:
                return
            self._git_sig_state = sig
            chip = self.status_git
            t = self.theme
            if st is None:
                chip.config(text="", fg=t["text_muted"],
                            font=(FONT_UI, 9))
                return
            branch = st.get("branch") or "(detached)"
            dirty, ahead, behind = (st.get("dirty", 0),
                                    st.get("ahead", 0),
                                    st.get("behind", 0))
            arrows = (" ↑%d" % ahead if ahead else "") + \
                     (" ↓%d" % behind if behind else "")
            if dirty:
                chip.config(text="%s ●%d%s" % (branch, dirty, arrows),
                            fg="#f59e0b", font=(FONT_UI, 9, "bold"))
            elif ahead or behind:
                chip.config(text="%s%s" % (branch, arrows),
                            fg="#f59e0b", font=(FONT_UI, 9))
            else:
                chip.config(text=branch, fg=t["text_muted"],
                            font=(FONT_UI, 9))
        except Exception:  # noqa: BLE001 — a chip must never break typing
            pass

    def _git_chip_click(self):
        """Click the git chip: open Source Control (the actionable
        surface for whatever the chip is pointing at) and redraw."""
        try:
            self.show_sidebar_view("git")
        except Exception:  # noqa: BLE001 — the panel may be absent
            pass
        self._update_gitchip(force=True)

    def _git_watch_toggle(self, arg=""):
        """``git watch [on|off]`` — the statusbar branch chip and its
        30s probe. Bare ``git watch`` flips the switch."""
        arg = str(arg or "").strip().lower()
        cur = bool(self.config.get("git_watch", True))
        if arg in ("on", "1", "true"):
            new = True
        elif arg in ("off", "0", "false"):
            new = False
        elif arg == "":
            new = not cur
        else:
            self.terminal.log("usage: git watch [on|off] — the chip "
                              "shows the branch, turns amber when "
                              "files wait to be committed")
            return
        self.config.set("git_watch", new)
        self._git_sig_state = ""      # force a redraw
        self._update_gitchip(force=True)
        self.terminal.log(
            "git watch %s — %s" % (
                "on" if new else "off",
                "the statusbar chip shows the branch, amber with ●N "
                "when files wait to be committed, ↑/↓ when the "
                "branch diverges"
                if new else "the branch chip is hidden; the Source "
                            "Control panel still works as always"))

    def _chip_tip(self, widget, text):
        """DS2 v2.40 polish — a quiet tooltip for statusbar chips:
        hover explains what the chip is and what clicking it does.
        Best-effort, never raises."""
        try:
            tip = {"win": None}

            def enter(_e):
                if tip["win"] is not None:
                    return
                x = widget.winfo_rootx() + 8
                y = widget.winfo_rooty() - 30
                tw = tk.Toplevel(widget)
                tw.wm_overrideredirect(True)
                try:
                    tw.attributes("-topmost", True)
                except Exception:  # noqa: BLE001 — X11 quirk tolerance
                    pass
                tw.wm_geometry("+%d+%d" % (x, y))
                tk.Label(tw, text=text, bg=self.theme["header"],
                         fg=self.theme["text"],
                         font=(FONT_UI, 8), padx=8,
                         pady=3).pack()
                tip["win"] = tw

            def leave(_e):
                if tip["win"] is not None:
                    try:
                        tip["win"].destroy()
                    except Exception:  # noqa: BLE001 — already gone
                        pass
                    tip["win"] = None

            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)
        except Exception:  # noqa: BLE001 — tooltips are garnish
            pass

    # ------------------------------------------------- DS2 v2.39 verbs win
    def _prefill_terminal(self, verb):
        """Drop a verb into the terminal input (from the verbs
        browser) — Enter still runs it, the user stays in charge."""
        try:
            ent = self.terminal.input
            ent.delete(0, tk.END)
            ent.insert(0, str(verb))
            ent.focus_set()
        except Exception:  # noqa: BLE001 — best-effort prefill
            pass

    def open_verbs_window(self):
        """The terminal-verbs browser — every verb the studio speaks,
        searchable, one click from running."""
        try:
            from .verbs import open_verbs
            open_verbs(self.root, self.theme,
                       on_insert=self._prefill_terminal)
        except Exception:
            errors.log_exception("verbs window", quiet=True)
            self.terminal.log("verbs: window unavailable — try `help`")

    def _run_depcheck(self, fix=False, force=False):
        """DS2 v2.36–v2.38: ``deps`` — imports vs requirements, in the
        terminal. Pure static analysis, never executes project code.
        The report is cached per workspace (``.dxn1``) and only
        rescanned when a fingerprint changes; ``deps fresh`` bypasses
        the cache and ``deps fix`` always works from a fresh scan. With
        ``fix``, missing imports are appended to the requirements file
        as canonical pins — atomically, deduped."""
        try:
            if not self.project_dir:
                self.toast("No workspace open — deps needs one",
                           kind="info")
                return
            from . import depcheck as _dc
            rep = _dc.check_cached(self.project_dir,
                                   use_cache=not (force or fix))
            text = _dc.describe(rep)
            if not text:
                self.toast("deps: no Python files in this workspace",
                           kind="info")
                return
            for ln in text.splitlines():
                self.terminal.log(ln)
            if rep.get("cached"):
                self.terminal.log("deps: served from cache (workspace "
                                  "unchanged) — `deps fresh` rescans")
            # v2.39: any deps run re-anchors the watch chip
            self._deps_sig_state = ""
            self._update_depswatch(force=True)
            if not fix:
                return
            pins = _dc.suggested_pins(rep.get("missing") or [])
            if not pins:
                self.terminal.log("deps fix: nothing to add — imports "
                                  "and requirements agree")
                return
            res = _dc.fix_requirements(self.project_dir, pins)
            if res.get("ok") and res.get("added"):
                self.terminal.log(
                    f"deps fix: added {len(res['added'])} pin(s) to "
                    f"{os.path.basename(res.get('target') or '')}: "
                    + ", ".join(res["added"]))
                # v2.41: the repaired workspace is the new truth —
                # rescan + re-store so the cache and the watch chip
                # never lie about a workspace we just fixed
                rep2 = _dc.check_cached(self.project_dir,
                                        use_cache=False)
                self._deps_sig_state = ""
                self._update_depswatch(force=True)
                if rep2.get("missing"):
                    self.terminal.log(
                        "deps fix: still missing after the pin — "
                        + ", ".join(str(n) for n in rep2["missing"][:6]))
            elif res.get("ok"):
                self.terminal.log("deps fix: requirements already "
                                  "cover every import")
            else:
                self.terminal.log(f"deps fix failed: {res.get('error', '')}")
        except Exception:
            errors.log_exception("deps check", quiet=True)

    def _list_palette_commands(self, flt=""):
        """DS2 v2.38: ``commands [filter]`` — every command the
        Ctrl+K palette offers, listed in the terminal. A filter tail
        narrows the list: substring first, then the closest fuzzy
        hits. Never raises."""
        try:
            rows = palette_help_rows(self)
            if not rows:
                self.terminal.log("commands: palette unavailable right "
                                  "now — try `palette` (Ctrl+K)")
                return
            total = len(rows)
            q = str(flt or "").strip().lower()
            if q:
                sub = [r for r in rows
                       if q in r[0].lower() or q in r[1].lower()]
                if not sub:
                    try:
                        from . import fuzzy as _fz
                        scored = sorted(
                            ((_fz.score(q, r[0]), r) for r in rows),
                            key=lambda t: t[0], reverse=True)
                        sub = [r for s, r in scored[:8] if s > 0]
                    except Exception:  # noqa: BLE001
                        sub = []
                rows = sub
            if not rows:
                self.terminal.log(f"commands: nothing matches "
                                  f"'{flt.strip()}'")
                return
            head = (f"commands: {len(rows)} of {total} palette command"
                    f"{'s' if total != 1 else ''}"
                    + (f" matching '{flt.strip()}'" if q else "")
                    + " — fire any via `palette` (Ctrl+K):")
            self.terminal.log(head)
            shown = rows[:24]
            for lab, key in shown:
                self.terminal.log(f"  {lab}" + (f"  [{key}]" if key else ""))
            if len(rows) > len(shown):
                self.terminal.log(f"  … +{len(rows) - len(shown)} more — "
                                  "narrow the filter")
        except Exception:
            errors.log_exception("commands", quiet=True)

    def show_whatsnew(self):
        """DS2 v2.36: open the What's New viewer on demand (terminal
        ``whatsnew`` / palette)."""
        try:
            from . import whatsnew as _wn
            entries = _wn.load_entries()
            _wn.open_whatsnew(
                self.root, self.theme,
                highlight=entries[0]["version"] if entries else "",
                on_log=lambda m: self.terminal.log(m))
        except Exception:
            errors.log_exception("whatsnew", quiet=True)

    # ----------------------------------------------------------- shortcuts
    def show_shortcuts(self):
        t = self.theme
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        rows = (
            ("Ctrl+N / Ctrl+O / Ctrl+S", "new / open / save"),
            ("Ctrl+P", "quick open a file"),
            ("Ctrl+K", "command palette — type @ for symbols"),
            ("Ctrl+F", "find in file"),
            ("Ctrl+G", "go to line"),
            ("Ctrl+/", "toggle comment"),
            ("Ctrl+Shift+D", "duplicate line"),
            ("Ctrl+Shift+K", "delete line"),
            ("Alt+Up / Alt+Down", "move line up / down"),
            ("Tab", "expand snippet (ifmain · pdb · smain)"),
            ("Ctrl+F2 / F2 / Shift+F2", "bookmark line · next · previous"),
            ("Ctrl+\\", "split editor"),
            ("Ctrl+Alt+Z", "zen mode"),
            ("Ctrl+W · Ctrl+Tab", "close tab · cycle tabs"),
            ("F5", "run project"),
            ("Ctrl+,", "settings"),
        )
        box = tk.Frame(win, bg=t["bg"])
        box.pack(padx=24, pady=18)
        tk.Label(box, text="Keyboard shortcuts", bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 13, "bold")).pack(anchor="w", pady=(0, 10))
        for keys, action in rows:
            row = tk.Frame(box, bg=t["bg"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=keys, bg=t["bg"], fg=t.accent, width=22,
                     anchor="w", font=(FONT_MONO, 9, "bold")).pack(
                side=tk.LEFT)
            tk.Label(row, text=action, bg=t["bg"], fg=t["text_secondary"],
                     font=(FONT_UI, 9)).pack(side=tk.LEFT, padx=12)
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + \
            max(0, (self.root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = self.root.winfo_rooty() + 120
        win.geometry(f"+{x}+{y}")

    # ------------------------------------------------ DS2 v2.32: autosave
    def _save_session_snapshot(self):
        """Write the rich session snapshot (tabs + active + cursors).

        Shared by the close hook and the periodic autosave — identical
        data, same file, so a hard crash costs at most one interval of
        workspace state. Never raises."""
        try:
            from . import session as _ds2_session
            _cur = {}
            try:  # DS2 v2.31: merge per-tab cursors, current wins
                for _p, _pos in getattr(self, "_buffer_cursors",
                                        {}).items():
                    _parts = str(_pos).split(".")
                    _cur[_p] = (int(_parts[0]), int(_parts[1]))
                _ins = str(self.editor.text.index("insert")).split(".")
                if self.editor.file_path:
                    _cur[self.editor.file_path] = (int(_ins[0]),
                                                   int(_ins[1]))
            except Exception:
                pass
            _ws = self.project_dir or ""
            _ds2_session.save(_ws, _ds2_session.snapshot(
                list(self._tab_frames) if hasattr(self, "_tab_frames")
                else [], active=self.editor.file_path or "",
                cursor=_cur, workspace=_ws))
        except Exception:
            errors.log_exception("session snapshot", quiet=True)

    def _autosave_session(self):
        """DS2 v2.32: crash-safe session autosave (default every 60s).

        Until now the session snapshot was only written on a clean
        close — a crash or battery death lost everything since the
        last exit. Autosave writes the same snapshot once a minute,
        silently. Respects both the autosave and the restore switches;
        always reschedules while the root is alive."""
        try:
            if self.config.get("session_autosave", True) and \
                    self.config.get("restore_session", True) and \
                    self.project_dir:
                self._save_session_snapshot()
                self._session_chip_feedback()
        except Exception:
            errors.log_exception("session autosave", quiet=True)
        try:
            _secs = int(self.config.get("session_autosave_secs", 60)
                        or 60)
            _secs = max(15, min(600, _secs))
            self._session_autosave_job = self.root.after(
                _secs * 1000, self._autosave_session)
        except Exception:  # noqa: BLE001 — dying root is fine
            pass

    def _restore_engine_session(self, project_path):
        """DS2 v2.32/v2.35: reopen tabs from the engine snapshot.

        The first choice at boot — the snapshot is refreshed by every
        clean exit and by the 60s autosave, cursors included, so it is
        always at least as fresh as the legacy clean-exit record.
        Returns True when something was (re)opened, False when no
        usable snapshot exists. Best effort, never raises."""
        try:
            from . import session as _ds2_session
            _ws = os.path.abspath(project_path)
            tabs, active, cursor = _ds2_session.restore_plan(
                _ds2_session.load(_ws))
            if not tabs and not active:
                return False
            for path in tabs:
                if path != self.editor.file_path:
                    try:
                        self.open_file(path)
                    except Exception:
                        pass
            if active and os.path.isfile(active):
                try:
                    self.open_file(active)
                except Exception:
                    pass
            if cursor and active == self.editor.file_path:
                try:
                    self.editor.text.mark_set(
                        "insert", f"{int(cursor[0])}.{int(cursor[1])}")
                    self.editor.text.see("insert")
                except Exception:
                    pass
            try:  # seed the per-buffer map so tab switches keep spots
                data = _ds2_session.load(_ws)
                for _p, _c in (data.get("cursor") or {}).items():
                    self._buffer_cursors[_p] = \
                        f"{int(_c.get('line', 1))}.{int(_c.get('col', 0))}"
            except Exception:
                pass
            return True
        except Exception:
            errors.log_exception("engine session restore", quiet=True)
            return False

    # ------------------------------------------------ DS2 v2.33: save now
    def save_session_now(self):
        """DS2 v2.33: snapshot the session immediately on demand.

        Same file and data as the close hook and the periodic
        autosave — but user-invoked (palette, terminal ``session
        save``, or a click on the statusbar chip), with visible
        feedback. Never raises."""
        try:
            if not self.project_dir:
                try:
                    self.toast("No workspace open — nothing to "
                               "snapshot", kind="info")
                except Exception:
                    pass
                return
            self._save_session_snapshot()
            self._session_chip_feedback()
            try:
                self.terminal.log("Session snapshot saved — tabs and "
                                  "cursor spots are on disk")
            except Exception:
                pass
        except Exception:
            errors.log_exception("save session now", quiet=True)

    def _session_chip_feedback(self):
        """DS2 v2.33: paint the statusbar 'session saved' chip.

        Accent for a moment, then fades back to muted — quiet polish
        that tells you the autosave is alive without ever shouting."""
        try:
            import time as _time
            self.status_sesave.config(
                text="◐ session saved " + _time.strftime("%H:%M"),
                fg=self.theme.accent)
            if getattr(self, "_sesave_job", None):
                try:
                    self.root.after_cancel(self._sesave_job)
                except Exception:
                    pass
            self._sesave_job = self.root.after(
                2500, self._session_chip_muted)
        except Exception:  # noqa: BLE001 — chip is optional polish
            pass

    def _session_chip_muted(self):
        """DS2 v2.33: fade the session chip back to muted ink."""
        try:
            self.status_sesave.config(fg=self.theme["text_muted"])
        except Exception:  # noqa: BLE001 — dying root is fine
            pass

    # ------------------------------------------------------------------ run
    def _dismiss_chip_menu(self):
        """DS2 v2.52 — put every posted chip menu away BEFORE the app
        goes down: unpost the last one, release the grab it holds.
        Tk's grab state is per-DISPLAY and process-wide, so a menu
        left posted at teardown would keep swallowing pointer events
        from whatever runs next (found by the pytest interps). Never
        raises."""
        try:
            menu = self._last_chip_menu
            if menu is not None:
                try:
                    menu.unpost()
                except Exception:  # noqa: BLE001 — already gone
                    pass
                try:
                    menu.grab_release()
                except Exception:  # noqa: BLE001 — already gone
                    pass
        except Exception:  # noqa: BLE001 — exit must never block
            pass
        self._last_chip_menu = None

    def _on_close(self):
        """WM_DELETE_WINDOW — save session, then quit cleanly."""
        # DS2 v2.52: the chip menu goes first (see its docstring)
        self._dismiss_chip_menu()
        try:
            self.stop_run(silent=True)
            if self.config.get("restore_session", True) and \
                    self.project_dir:
                sessions = dict(self.config.get("session_tabs") or {})
                sessions[os.path.abspath(self.project_dir)] = {
                    "tabs": list(self._tab_frames),
                    "active": self.editor.file_path or "",
                }
                # keep sessions for workspaces that still exist, max 20
                kept = {p: v for p, v in sessions.items()
                        if os.path.isdir(p)}
                self.config.set(
                    "session_tabs",
                    dict(list(kept.items())[-20:]))
        except Exception:
            errors.log_exception("save session", quiet=True)
        # DS2 v2.30/v2.32: richer session snapshot with cursor position
        # (shared with the periodic autosave — same data, same file)
        self._save_session_snapshot()
        # DS2: remember window geometry for this screen shape
        try:
            from .geom import remember_root
            remember_root(self.root, self.config)
        except Exception:  # noqa: BLE001 — exit must never block
            pass
        self.root.destroy()

    def _schedule_smoke_test(self):
        """Headless self-check exercising the whole v1.1 surface."""
        self.root.after(60000, self.root.destroy)  # watchdog: never hang CI
        tmp = tempfile.mkdtemp(prefix="dxn1-smoke-")

        def bail(err):
            import traceback
            traceback.print_exc()
            print(f"SMOKE-FAIL: {err}", flush=True)
            self.root.destroy()

        def step1():
            try:
                if self.config.needs_onboarding:
                    self.start_wizard()
                self.root.after(1200, step2)
            except Exception:
                bail("step1-wizard")

        def step2():
            try:
                if self._wizard is not None and self._wizard.win.winfo_exists():
                    self._wizard.choose_agents(True)   # opt-in path
                    if hasattr(self._wizard, "choose_brain"):
                        self._wizard.choose_brain("free")
                    self._wizard.finish()
                self.root.after(1400, step3)
            except Exception:
                bail("step2-wizard-finish")

        def step3():
            try:
                if self._hub is not None and self._hub.winfo_exists():
                    self._hub._finish_explore()        # 'Just explore'
                self.root.after(1200, step4)
            except Exception:
                bail("step3-hub")

        def step4():
            try:
                self._tour_done_cleanup()
                self.start_tour()
                self.root.after(1300, step5)
            except Exception:
                bail("step4-tour")

        def step5():
            try:
                if self._tour is not None:
                    self._tour.finish()
                # scaffold a python workspace + open it
                path, kind = projects.scaffold("python", tmp, "Smoke Script")
                self._set_workspace(path, kind)
                self.root.after(900, step6)
            except Exception:
                bail("step5-scaffold")

        def step6():
            try:
                # full-access agent writes a file with zero prompts
                self.config.set("agents_enabled", True)
                self.config.set("agents_ask_edits", False)
                self.apply_agents_visibility()
                self.agent_panel.handle("create file agent_demo.py")
                made = os.path.join(self.project_dir, "agent_demo.py")
                assert os.path.isfile(made), "agent did not write file"
                self.root.after(600, step6b)
            except Exception:
                bail("step6-agent")

        def step6b():
            try:
                # engine + sandbox + parser, fully offline
                from .sandbox import parse_tools
                sb = WorkspaceSandbox(self.project_dir)
                eng = AgentEngine(
                    FakeBackend([
                        '<tool name="write_file">'
                        '{"path": "engine_demo.py", '
                        '"content": "print(42)\\n"}'
                        '</tool>Wrote the file. <done>done</done>'
                    ]),
                    sb, self.config, name="Smoke",
                    emit=lambda *a, **k: None, approve=lambda *a, **k: True,
                    execute_command=lambda c: (0, "ok"),
                    on_written=lambda p: None)
                eng.run("write engine_demo.py")
                assert os.path.isfile(
                    os.path.join(self.project_dir, "engine_demo.py")), \
                    "engine did not write file"
                try:
                    sb.resolve("../escape.py")
                    raise AssertionError("sandbox escape allowed")
                except SandboxError:
                    pass
                clean, tools = parse_tools(
                    'hi <tool name="read_file">{"path": "a.py"}</tool>')
                assert tools and tools[0][0] == "read_file" and clean == "hi"
                self.terminal.log("Engine + sandbox checks passed")
                self.root.after(500, step7)
            except Exception:
                bail("step6b-engine")

        def step7():
            try:
                self.run_file(os.path.join(self.project_dir, "main.py"))
                self.root.after(2500, step8)
            except Exception:
                bail("step7-run")

        def step8():
            try:
                self.stop_run(silent=True)
                out = os.path.join(tmp, "export.zip")
                path, count = export.export_project_zip(self.project_dir, out)
                assert os.path.isfile(path) and count >= 2, "export failed"
                self.open_packages()
                self.root.after(900, step9)
            except Exception:
                bail("step8-export-packages")

        def step9():
            try:
                # search view end-to-end (synchronous scan via thread + wait)
                self.show_sidebar_view("search")
                self.search_view.entry.insert(0, "Hello")
                self.search_view.start_search()
                self.root.after(900, step9b)
            except Exception:
                bail("step9-search")

        def step9b():
            try:
                assert self.search_view._hits, "search found nothing"
                # palette open + close
                self.open_palette()
                self.root.after(400, step9c)
            except Exception:
                bail("step9b-palette")

        def step9c():
            try:
                assert self._palette is not None
                self._palette.close()
                self._palette = None
                # find bar + toast
                self.toggle_find(show=True)
                self.find_var.set("Hello")
                self._find_live()
                self.toast("smoke toast", "info")
                self.root.after(500, step9d)
            except Exception:
                bail("step9c-find-toast")

        def step9d():
            try:
                self.toggle_find(show=False)
                # quick open
                self.open_quick_open()
                self.root.after(300, self._quick_open.close)
                self.root.after(500, step9e)
            except Exception:
                bail("step9d-quickopen")

        def step9e():
            try:
                # split view + edit on both sides
                self.toggle_split()
                assert self._split is not None, "split view missing"
                self.toggle_split()
                assert self._split is None, "split view won't close"
                # zen round-trip
                self.toggle_zen()
                self.toggle_zen()
                # comment toggle on main.py
                self.open_file(os.path.join(self.project_dir, "main.py"))
                self.editor.text.mark_set("insert", "1.0")
                self.editor.toggle_comment()
                assert self.editor.get_content().lstrip().startswith("#"), \
                    "comment toggle failed"
                self.editor.toggle_comment()
                # auto-indent sanity via editor internals
                self.editor.auto_indent = True
                self.editor.auto_close = True
                # goto line
                assert self.editor.goto_line(1), "goto failed"
                self.root.after(400, step9f)
            except Exception:
                bail("step9e-split-zen-comment")

        def step9f():
            try:
                # --- git panel: init, stage, commit on a scratch repo
                self.show_sidebar_view("git")
                self.git_view.set_workspace(self.project_dir)
                self.root.after(400, step9g)
            except Exception:
                bail("step9f-git-view")

        def step9g():
            try:
                g = self.git_view
                if not g._is_repo:
                    g._init_repo()
                assert g._is_repo, "git panel did not detect/init repo"
                from .gitpanel import _run_git
                _run_git(self.project_dir, "config", "user.name", "Smoke")
                _run_git(self.project_dir, "config", "user.email",
                         "smoke@test.local")
                g.msg.delete(0, tk.END)
                g.msg.insert(0, "smoke: first commit")
                g.commit()
                self.root.after(500, step9h)
            except Exception:
                bail("step9g-git-commit")

        def step9h():
            try:
                from .gitpanel import _run_git
                ok, out, _ = _run_git(self.project_dir, "log",
                                      "--oneline", "-1")
                assert ok and "smoke: first commit" in out, \
                    "commit didn't land"
                self.terminal.log("Git panel checks passed")
                self.root.after(300, step9i)
            except Exception:
                bail("step9h-git-log")

        def step9i():
            try:
                # --- palette @symbols
                self.open_palette()
                self._palette.entry.insert(0, "@")
                self._palette._on_type()
                assert self._palette.filtered, "no symbols found"
                self._palette.close()
                self._palette = None
                # --- bookmarks
                self.editor.toggle_bookmark(2)
                assert 2 in self.editor.bookmarks, "bookmark add failed"
                self.editor.goto_line(1)
                self.editor.next_bookmark()
                assert str(self.editor.text.index(
                    "insert").split(".")[0]) == "2", "bookmark jump failed"
                self.editor.prev_bookmark()
                self.editor.toggle_bookmark(2)
                assert 2 not in self.editor.bookmarks, "bookmark del failed"
                # --- snippet expansion
                self.editor.set_content("ifmain",
                                        path=self.editor.file_path)
                self.editor.text.mark_set("insert", "end-1c")
                self.editor._on_tab()
                assert '__name__' in self.editor.get_content(), \
                    "snippet didn't expand"
                # --- settings search filter
                dlg = SettingsDialog(self)
                dlg._filter_settings("wrap")
                dlg.destroy()
                self.terminal.log("Symbols + bookmarks + snippets passed")
                self.root.after(400, step9j)
            except Exception:
                bail("step9i-symbols-bookmarks-snippets")

        def step9j():
            try:
                # --- v1.1.4: replace bar (open_replace + replace_all UI)
                self.open_replace()
                self.root.update()
                assert self.replace_row.winfo_ismapped(), \
                    "replace row missing"
                self.find_var.set("__name__")
                self.replace_var.set("__core__")
                self._find_live()
                self._replace_all()
                assert "__core__" in self.editor.get_content(), \
                    "replace_all UI failed"
                self.toggle_replace(show=False)
                self.toggle_find(show=False)
                # --- v1.1.4: C-family symbols via the palette
                go_path = os.path.join(self.project_dir, "notes.go")
                with open(go_path, "w", encoding="utf-8") as fh:
                    fh.write("package main\n\nfunc main() {\n}\n\n"
                             "func Add(a int, b int) int {\n\treturn a\n}\n")
                self.open_file(go_path)
                syms = self.editor.symbols()
                names = [n for _, _, n in syms]
                assert "main" in names and "Add" in names, syms
                # --- v1.1.4: game template scaffolds + compiles
                import py_compile
                gpath, gkind = projects.scaffold(
                    "game", tmp, "Smoke Game")
                assert gkind == "game"
                py_compile.compile(os.path.join(gpath, "main.py"),
                                       doraise=True)
                # --- v1.1.4: free-brain guard stays honest
                from .llm import _looks_like_provider_error
                assert _looks_like_provider_error(
                    "The API key used for this request has reached its "
                    "budget. Please [raise ...]"), "guard missed budget"
                assert not _looks_like_provider_error(
                    "def fix(): return rate_limit_explained"), \
                    "guard false positive"
                from .llm import PollinationsBackend
                pb = PollinationsBackend(self.config)
                self.terminal.log("v1.1.4 checks passed")
                self.root.after(400, step9k)
            except Exception:
                bail("step9j-v114")

        def step9k():
            # --- v1.1.5: agents 2.0 — markdown chat, personas, sessions
            try:
                from .agent import (parse_chat_blocks, SessionStore,
                                    PERSONAS, SLASH_COMMANDS)
                blocks = parse_chat_blocks(
                    "# Plan\n- one\n- two\n\nPlain para.\n"
                    "```python\nprint('hi')\n```\ntail line")
                kinds = [k for k, _ in blocks]
                assert kinds[0] == "h" and kinds[1] == "li", kinds
                assert ("code", ) == (kinds[4],), kinds
                assert blocks[4][1][0] == "python", blocks[4]
                ap = self.agent_panel
                assert ap is not None, "agents panel missing"
                ap.set_persona("senior")
                assert ap._persona()[0] == "senior", "persona switch failed"
                ap.set_persona("default")
                assert len(PERSONAS) >= 6 and len(SLASH_COMMANDS) >= 12
                store = SessionStore()
                store.save(self.project_dir, "smoke-1", "Smoke chat",
                           [{"role": "user", "text": "hi"},
                            {"role": "agent", "text": "hello"}], stats="3 tok")
                got = store.load(self.project_dir, "smoke-1")
                assert got and got["messages"][-1]["text"] == "hello"
                # slash dispatch must not crash offline (local quickies only)
                ap.route("/help")
                self.root.update()
                # search_code tool through the engine's tool host
                sb = WorkspaceSandbox(self.project_dir)
                eng = AgentEngine(
                    FakeBackend(["ok <done>done</done>"]),
                    sb, self.config, name="Smoke",
                    emit=lambda *a, **k: None, approve=lambda *a, **k: True,
                    execute_command=lambda c: (0, "ok"),
                    on_written=lambda p: None)
                res = eng._exec_tool("search_code",
                                     {"pattern": "SMOKE", "max": 5})
                assert isinstance(res, str) and "error" not in res[:20], res
                self.terminal.log("v1.1.5 agents checks passed")
                self.root.after(400, step9l)
            except Exception:
                bail("step9k-agents2")

        def step9l():
            # --- v1.1.5: update portal — logic + every phase paints
            try:
                from .updater import (ver_tuple, is_newer, UpdatePortal,
                                      MIN_SHOW_SECONDS)
                assert ver_tuple("1.1.5") == (1, 1, 5)
                assert is_newer("1.1.5", "1.1.4") and not is_newer(
                    "1.1.4", "1.1.4")
                assert MIN_SHOW_SECONDS >= 3
                portal = UpdatePortal(self, "9.9.9",
                                      notes=["smoke note one",
                                             "smoke note two"])
                self.root.update()
                assert portal._phase == "offer"
                portal._paint()                      # offer phase renders
                portal.decline()                     # security goodbye screen
                self.root.update()
                assert portal._phase == "declined"
                portal._draw_progress(self.root.winfo_width(),
                                      self.root.winfo_height())
                portal._draw_restarting(self.root.winfo_width(),
                                        self.root.winfo_height())
                portal._target = 0.42
                portal._animate()
                self.root.update()
                portal.after_cancel(portal._restart_job) \
                    if portal._restart_job else None
                portal.grab_release()
                portal.destroy()
                self._updater_shown = False
                self.terminal.log("v1.1.5 update portal checks passed")
                self.root.after(400, step9m)
            except Exception:
                bail("step9l-updater")

        def step9m():
            # --- v1.1.5: editor pro — indent, regex find/replace, word hl
            try:
                from .widgets import language_for, LANG_RULES
                ed = self.editor
                # block indent / outdent over a selection
                ed.set_content("alpha bravo\ngamma delta\n", "pro.py")
                ed.text.tag_add("sel", "1.0", "end")
                ed._on_tab()
                assert ed.text.get("1.0", "1.end").startswith("    alpha"), \
                    ed.text.get("1.0", "1.end")
                ed._on_outdent()
                assert not ed.text.get("1.0", "1.end").startswith(" "), \
                    "outdent failed"
                # regex find: both two-word pairs light up
                n = ed.find(r"(\w+) (\w+)", regex=True)
                assert n == 2, n
                # regex replace_all with template expansion
                n = ed.replace_all(r"(\w+) (\w+)", r"\2-\1", regex=True)
                assert n == 2, n
                body = ed.get_content()
                assert "bravo-alpha" in body and "delta-gamma" in body, body
                # bad regex is surfaced, never crashes
                assert ed.find("([unclosed", regex=True) == -1
                assert ed.replace_all("([bad", "x", regex=True) == -1
                # word-under-cursor highlight: two "needle" occurrences
                ed.set_content("needle here\nneedle there\n", "pro2.py")
                ed.text.mark_set("insert", "1.2")
                ed._word_hl()
                tags = ed.text.tag_ranges("word_hl")
                assert tags and len(tags) == 4, tags
                # new language rules are live
                assert language_for("main.go") is LANG_RULES[".go"]
                assert language_for("lib.rs") is LANG_RULES[".rs"]
                assert language_for("App.java") is LANG_RULES[".java"]
                assert language_for("run.sh") is LANG_RULES[".sh"]
                self.terminal.log("v1.1.5 editor pro checks passed")
                self.root.after(400, step10)
            except Exception:
                bail("step9m-editorpro")

        def step10():
            try:
                self.handle_terminal_command("help")
                self.scan_todos()
                self.handle_terminal_command("dxn1 studio")  # splash replay
                self.root.after(2600, step11)
            except Exception:
                bail("step10-commands")

        def step11():
            try:
                assert self.root.winfo_ismapped() or \
                    self.root.state() == "normal", "splash did not restore"
                self.terminal.log("Smoke test passed ✔")
                print("SMOKE-PASS", flush=True)
                self.root.after(400, self.root.destroy)
            except Exception:
                bail("step11-final")

        self.root.after(300, step1)


class SettingsDialog(tk.Toplevel):
    """Studio preferences: look & feel, editor, boot behaviour, agents."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        t = app.theme
        self.t = t
        cfg = app.config
        self.title("DXN1 STUDIO — Settings")
        self.configure(bg=t["bg"])
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        self.theme_v = tk.StringVar(value=cfg.get("theme", "dark"))
        self.accent_v = tk.StringVar(value=cfg.get("accent", "violet"))
        self.size_v = tk.StringVar(value=str(cfg.get("editor_font_size", 11)))
        self.wrap_v = tk.BooleanVar(value=bool(cfg.get("word_wrap", False)))
        self.autosave_v = tk.BooleanVar(value=bool(cfg.get("auto_save", False)))
        self.autoindent_v = tk.BooleanVar(
            value=bool(cfg.get("editor_auto_indent", True)))
        self.autoclose_v = tk.BooleanVar(
            value=bool(cfg.get("editor_auto_close", True)))
        self.splash_v = tk.BooleanVar(value=bool(cfg.get("splash_enabled", True)))
        self.hub_v = tk.BooleanVar(value=bool(cfg.get("hub_on_startup", True)))
        self.session_v = tk.BooleanVar(
            value=bool(cfg.get("restore_session", True)))
        self.sesauto_v = tk.BooleanVar(
            value=bool(cfg.get("session_autosave", True)))
        self.updates_v = tk.BooleanVar(
            value=bool(cfg.get("check_updates", True)))
        # DS2 v2.41: the statusbar watch chips live here too
        self.depswatch_v = tk.BooleanVar(
            value=bool(cfg.get("deps_watch", True)))
        self.gitwatch_v = tk.BooleanVar(
            value=bool(cfg.get("git_watch", True)))
        # DS2 v2.47: per-kind toast cards (muted kinds still archive)
        self.toastinfo_v = tk.BooleanVar(
            value=bool(cfg.get("toast_show_info", True)))
        self.toastsuccess_v = tk.BooleanVar(
            value=bool(cfg.get("toast_show_success", True)))
        self.toasterror_v = tk.BooleanVar(
            value=bool(cfg.get("toast_show_error", True)))
        # DS2 v2.51: the diary writes itself (nightly snapshots)
        self.activity_autosnap_v = tk.BooleanVar(
            value=bool(cfg.get("activity_autosnap", False)))
        try:   # DS2 v2.52: the snapshot interval, hours, clamped
            _snap_h = int(float(cfg.get("activity_autosnap_hours",
                                        24)))
            _snap_h = max(1, min(168, _snap_h))
        except Exception:
            _snap_h = 24
        self.activity_hours_v = tk.StringVar(value=str(_snap_h))
        try:   # DS2 v2.36: update heartbeat interval, minutes
            _upd_min = max(15, min(360, int(
                cfg.get("update_check_secs", 3600)) // 60))
        except Exception:
            _upd_min = 60
        self.updint_v = tk.IntVar(value=_upd_min)

        box = tk.Frame(self, bg=t["bg"])
        box.pack(padx=26, pady=20)

        tk.Label(box, text="Settings", bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 14, "bold")).pack(anchor="w")

        # searchable — type to filter rows across every section
        srow = tk.Frame(box, bg=t["bg"])
        srow.pack(fill=tk.X, pady=(8, 0))
        self.search_var = tk.StringVar()
        s_ent = tk.Entry(srow, textvariable=self.search_var, bg=t["editor"],
                         fg=t["text"], insertbackground=t["text"],
                         relief=tk.FLAT, font=(FONT_UI, 10),
                         highlightthickness=1, highlightbackground=t["border"],
                         highlightcolor=t.accent)
        s_ent.pack(fill=tk.X, ipady=5)
        s_ent.insert(0, "Search settings…")
        s_ent.config(fg=t["text_muted"])
        s_ent.bind("<FocusIn>", lambda e: (
            s_ent.delete(0, tk.END), s_ent.config(fg=t["text"])))
        s_ent.bind("<FocusOut>", lambda e: (
            self._filter_settings(self.search_var.get()), None))
        s_ent.bind("<KeyRelease>", lambda e: self._filter_settings(
            self.search_var.get()))
        self._settings_search = s_ent

        self._sections = []

        # --- look & feel
        sec1 = self._section(box, "Look & feel")
        row = tk.Frame(sec1, bg=t["card"])
        row.pack(fill=tk.X, pady=(0, 6))
        for mode, label in (("dark", "Dark"), ("light", "Light")):
            tk.Radiobutton(row, text=label, variable=self.theme_v, value=mode,
                           bg=t["card"], fg=t["text"],
                           activebackground=t["card"], activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0, bd=0
                           ).pack(side=tk.LEFT, padx=12)
        row2 = tk.Frame(sec1, bg=t["card"])
        row2.pack(fill=tk.X)
        for name, spec in sorted(ACCENTS.items()):
            tk.Radiobutton(row2, text=spec["label"], variable=self.accent_v,
                           value=name,
                           bg=t["card"], fg=t["text"],
                           activebackground=t["card"], activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0, bd=0
                           ).pack(side=tk.LEFT, padx=8)

        # DS2 v2.55: the translation desk is one click from Settings —
        # languages travel on the sync bundle, now they are editable too
        lrow = tk.Frame(sec1, bg=t["card"])
        lrow.pack(fill=tk.X, pady=(6, 0))
        tk.Label(lrow, text="UI language:", bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 9)).pack(side=tk.LEFT)
        lang_btn = tk.Label(lrow, text="Edit a language pack…",
                            bg=t["card"], fg=t.accent, cursor="hand2",
                            font=(FONT_UI, 9, "underline"))
        lang_btn.pack(side=tk.LEFT, padx=(6, 0))
        lang_btn.bind("<Button-1>",
                      lambda e: self._open_lang_desk())

        # --- editor
        secE = self._section(box, "Editor")
        srow = tk.Frame(secE, bg=t["card"])
        srow.pack(fill=tk.X, pady=(0, 6))
        tk.Label(srow, text="Text size:", bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 9)).pack(side=tk.LEFT)
        for label, px in (("Small · 10", 10), ("Medium · 11", 11),
                          ("Large · 13", 13)):
            tk.Radiobutton(srow, text=label, variable=self.size_v,
                           value=str(px), bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"],
                           selectcolor=t["editor"], highlightthickness=0,
                           bd=0).pack(side=tk.LEFT, padx=8)
        for var, label, sub in (
                (self.wrap_v, "Word wrap",
                 "Soft-wrap long lines instead of horizontal scroll."),
                (self.autosave_v, "Auto-save",
                 "Save the active file shortly after you stop typing."),
                (self.autoindent_v, "Auto-indent",
                 "Keep indentation on Enter; deeper after ':' and '{'."),
                (self.autoclose_v, "Auto-close brackets",
                 "Typing ( [ { closes the pair; type-over included.")):
            crow = tk.Frame(secE, bg=t["card"])
            crow.pack(fill=tk.X, pady=2, ipady=2)
            tk.Checkbutton(crow, variable=var, bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"], selectcolor=t["editor"],
                           highlightthickness=0, bd=0).pack(side=tk.LEFT,
                                                            padx=(12, 4))
            tk.Label(crow, text=label, bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(crow, text=f"  ·  {sub}", bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT)

        # --- boot behaviour
        sec2 = self._section(box, "Boot behaviour")
        for var, label, sub in (
                (self.splash_v, "Show the boot splash",
                 "The branded card with the shimmer bar on launch."),
                (self.hub_v, "Start at the Project Hub",
                 "Create or reopen a workspace every launch."),
                (self.session_v, "Restore last session",
                 "Reopen your tabs when you dive back into a workspace."),
                (self.sesauto_v, "Autosave the session",
                 "Snapshots tabs and cursor spots every minute, so even "
                 "a crash comes back."),
                (self.updates_v, "Check for updates",
                 "Quietly ask GitHub on boot and on a slow heartbeat; "
                 "a release you skipped stays silent.")):
            row = tk.Frame(sec2, bg=t["card"])
            row.pack(fill=tk.X, pady=3, ipady=4)
            tk.Checkbutton(row, variable=var, bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"], selectcolor=t["editor"],
                           highlightthickness=0, bd=0).pack(side=tk.LEFT,
                                                            padx=(12, 4))
            tk.Label(row, text=label, bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(row, text=f"  ·  {sub}", bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT)

        # DS2 v2.36: update heartbeat interval (minutes)
        row = tk.Frame(sec2, bg=t["card"])
        row.pack(fill=tk.X, pady=3, ipady=4)
        tk.Label(row, text="Update heartbeat", bg=t["card"],
                 fg=t["text"], font=(FONT_UI, 10, "bold")
                 ).pack(side=tk.LEFT, padx=(12, 4))
        tk.Spinbox(row, from_=15, to=360, increment=15,
                   textvariable=self.updint_v, width=5, bg=t["editor"],
                   fg=t["text"], buttonbackground=t["card"],
                   relief=tk.FLAT, insertbackground=t["text"],
                   highlightthickness=0).pack(side=tk.LEFT)
        tk.Label(row, text="  ·  minutes between quiet GitHub checks "
                           "while the studio runs (15–360)",
                 bg=t["card"], fg=t["text_secondary"],
                 font=(FONT_UI, 8)).pack(side=tk.LEFT)

        # --- statusbar watch chips (DS2 v2.41)
        secW = self._section(box, "Statusbar watch chips")
        for var, label, sub in (
                (self.depswatch_v, "Dependency watch",
                 "Amber when the workspace drifts from the last deps "
                 "report, red when imports are missing from "
                 "requirements."),
                (self.gitwatch_v, "Source control watch",
                 "Shows the branch; amber with ●N when files wait to "
                 "be committed, ↑/↓ when the branch diverges.")):
            wrow = tk.Frame(secW, bg=t["card"])
            wrow.pack(fill=tk.X, pady=3, ipady=4)
            tk.Checkbutton(wrow, variable=var, bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"],
                           selectcolor=t["editor"],
                           highlightthickness=0, bd=0).pack(
                side=tk.LEFT, padx=(12, 4))
            tk.Label(wrow, text=label, bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(wrow, text=f"  ·  {sub}", bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT)

        # --- toasts (DS2 v2.47): per-kind cards; the log keeps everything
        secT = self._section(box, "Toasts")
        for var, label, sub in (
                (self.toastinfo_v, "Info cards",
                 "Quiet confirmations and hints from every lane."),
                (self.toastsuccess_v, "Success cards",
                 "Saved, exported, committed — the happy footsteps."),
                (self.toasterror_v, "Error cards",
                 "Failures worth seeing the moment they happen.")):
            trow = tk.Frame(secT, bg=t["card"])
            trow.pack(fill=tk.X, pady=3, ipady=4)
            tk.Checkbutton(trow, variable=var, bg=t["card"], fg=t["text"],
                           activebackground=t["card"],
                           activeforeground=t["text"],
                           selectcolor=t["editor"],
                           highlightthickness=0, bd=0).pack(
                side=tk.LEFT, padx=(12, 4))
            tk.Label(trow, text=label, bg=t["card"], fg=t["text"],
                     font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
            tk.Label(trow, text=f"  ·  {sub}", bg=t["card"],
                     fg=t["text_secondary"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT)
        tk.Label(secT, text="A muted kind still lands in the Activity log "
                            "— the log remembers, the screen stays quiet.",
                 bg=t["card"], fg=t["text_secondary"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=10, pady=(0, 6))

        # --- activity (DS2 v2.51): the nightly auto-snapshot gate
        secA = self._section(box, "Activity")
        arow = tk.Frame(secA, bg=t["card"])
        arow.pack(fill=tk.X, pady=3, ipady=4)
        tk.Checkbutton(arow, variable=self.activity_autosnap_v,
                       bg=t["card"], fg=t["text"],
                       activebackground=t["card"],
                       activeforeground=t["text"],
                       selectcolor=t["editor"],
                       highlightthickness=0, bd=0).pack(
            side=tk.LEFT, padx=(12, 4))
        tk.Label(arow, text="Nightly receipts snapshot",
                 bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
        tk.Label(arow, text="  ·  on the clock, the whole diary lands "
                            "in exports/ as JSON — the last 14 are kept",
                 bg=t["card"], fg=t["text_secondary"],
                 font=(FONT_UI, 8)).pack(side=tk.LEFT)
        hrow = tk.Frame(secA, bg=t["card"])
        hrow.pack(fill=tk.X, pady=3, ipady=2)
        tk.Label(hrow, text="      Hours between snapshots",
                 bg=t["card"], fg=t["text"],
                 font=(FONT_UI, 10, "bold")).pack(side=tk.LEFT)
        try:   # DS2 v2.52: the interval picker, in the house style
            sp = tk.Spinbox(hrow, from_=1, to=168, width=4,
                            textvariable=self.activity_hours_v,
                            bg=t["editor"], fg=t["text"],
                            buttonbackground=t["card"],
                            insertbackground=t["text"],
                            relief="flat", highlightthickness=1,
                            highlightbackground=t["card_border"],
                            highlightcolor=t.accent)
        except Exception:  # noqa: BLE001 — a plain spinner still spins
            sp = tk.Spinbox(hrow, from_=1, to=168, width=4,
                            textvariable=self.activity_hours_v)
        sp.pack(side=tk.LEFT, padx=8)
        tk.Label(hrow, text="1–168 · the clock reads it every half "
                            "hour",
                 bg=t["card"], fg=t["text_secondary"],
                 font=(FONT_UI, 8)).pack(side=tk.LEFT)
        tk.Label(secA, text="`activity snap` writes one now · "
                            "`activity auto on|off` flips the gate from "
                            "the terminal.",
                 bg=t["card"], fg=t["text_secondary"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=10, pady=(0, 6))

        # --- agents
        sec3 = self._section(box, "DXN1 Agents")
        btn = tk.Label(sec3, text="Open agent settings…", bg=t["card"],
                       fg=t.accent, font=(FONT_UI, 10, "bold"),
                       cursor="hand2", padx=10, pady=8)
        btn.pack(fill=tk.X)
        btn.bind("<Button-1>", lambda e: AgentSettingsDialog(app))
        btn2 = tk.Label(sec3, text="Connect a brain (Kilo · OpenRouter · "
                                   "GitHub)…", bg=t["card"], fg=t.accent,
                        font=(FONT_UI, 10, "bold"), cursor="hand2",
                        padx=10, pady=8)
        btn2.pack(fill=tk.X)
        btn2.bind("<Button-1>", lambda e: ConnectDialog(app))
        tk.Label(sec3, text="Permission gates (ask vs full access) live in "
                            "agent settings. The workspace sandbox is always on.",
                 bg=t["card"], fg=t["text_secondary"], font=(FONT_UI, 8)
                 ).pack(anchor="w", padx=10, pady=(0, 6))

        # --- buttons
        self._finalize_sections()
        row = tk.Frame(box, bg=t["bg"])
        row.pack(fill=tk.X, pady=(16, 0))
        cancel = tk.Label(row, text="Cancel", bg=t["bg"],
                          fg=t["text_secondary"],
                          font=(FONT_UI, 10), cursor="hand2", padx=10)
        cancel.pack(side=tk.RIGHT)
        cancel.bind("<Button-1>", lambda e: self.destroy())
        save = tk.Label(row, text="Save", bg=t.accent, fg="#ffffff",
                        font=(FONT_UI, 10, "bold"), cursor="hand2",
                        padx=18, pady=6)
        save.pack(side=tk.RIGHT)
        save.bind("<Button-1>", lambda e: self._save())

        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=self.t["bg"],
                 fg=self.t["text_secondary"],
                 font=(FONT_UI, 9, "bold")).pack(anchor="w", pady=(14, 4))
        frame = tk.Frame(parent, bg=self.t["card"], highlightthickness=1,
                         highlightbackground=self.t["card_border"])
        frame.pack(fill=tk.X, ipady=8, ipadx=4)
        inner = tk.Frame(frame, bg=self.t["card"])
        inner.pack(fill=tk.X, padx=10)
        self._sections.append({"title": title, "parent": parent,
                               "inner": inner, "rows": []})
        return inner

    def _texts_of(self, widget):
        """Widget text + its children's text, for settings filtering."""
        out = []
        try:
            out.append(str(widget.cget("text")))
        except (tk.TclError, KeyError):
            pass
        try:
            for child in widget.winfo_children():
                out.append(self._texts_of(child))
        except tk.TclError:
            pass
        return " ".join(out)

    def _finalize_sections(self):
        """Snapshot each row's pack options so filtering can restore them."""
        for sec in self._sections:
            sec["rows"] = [(w, w.pack_info())
                           for w in sec["inner"].winfo_children()]
            sec["card"] = sec["inner"].master

    def _filter_settings(self, query):
        """Type-to-filter: keep rows whose text matches, drop empty cards."""
        q = (query or "").strip().lower()
        if not q and self._settings_search.get() == "Search settings…":
            q = ""
        for sec in self._sections:
            visible = 0
            for w, info in sec["rows"]:
                hit = (not q) or q in self._texts_of(w).lower() \
                    or q in sec["title"].lower()
                try:
                    if hit:
                        w.pack(**info)
                        visible += 1
                    else:
                        w.pack_forget()
                except tk.TclError:
                    pass
            header = None
            for w in sec["parent"].winfo_children():
                if isinstance(w, tk.Label) and \
                        w.cget("text") == sec["title"]:
                    header = w
                    break
            try:
                if visible:
                    if header is not None:
                        header.pack(anchor="w", pady=(14, 4))
                    sec["card"].pack(fill=tk.X, ipady=8, ipadx=4)
                else:
                    if header is not None:
                        header.pack_forget()
                    sec["card"].pack_forget()
            except tk.TclError:
                pass

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.master.winfo_rootx() + \
            max(0, (self.master.winfo_width() - w) // 2)
        y = self.master.winfo_rooty() + \
            max(0, (self.master.winfo_height() - h) // 3)
        self.geometry(f"+{x}+{y}")

    def _save(self):
        cfg = self.app.config
        cfg.set("theme", self.theme_v.get())
        cfg.set("accent", self.accent_v.get())
        try:
            cfg.set("editor_font_size", max(8, min(20,
                                                   int(self.size_v.get()))))
        except ValueError:
            pass
        cfg.set("word_wrap", bool(self.wrap_v.get()))
        cfg.set("auto_save", bool(self.autosave_v.get()))
        cfg.set("editor_auto_indent", bool(self.autoindent_v.get()))
        cfg.set("editor_auto_close", bool(self.autoclose_v.get()))
        cfg.set("splash_enabled", bool(self.splash_v.get()))
        cfg.set("hub_on_startup", bool(self.hub_v.get()))
        cfg.set("restore_session", bool(self.session_v.get()))
        cfg.set("session_autosave", bool(self.sesauto_v.get()))
        cfg.set("check_updates", bool(self.updates_v.get()))
        # DS2 v2.41: watch chips — persist and redraw live
        cfg.set("deps_watch", bool(self.depswatch_v.get()))
        cfg.set("git_watch", bool(self.gitwatch_v.get()))
        # DS2 v2.47: per-kind toast cards
        cfg.set("toast_show_info", bool(self.toastinfo_v.get()))
        cfg.set("toast_show_success", bool(self.toastsuccess_v.get()))
        cfg.set("toast_show_error", bool(self.toasterror_v.get()))
        # DS2 v2.51: nightly receipts snapshots
        cfg.set("activity_autosnap",
                bool(self.activity_autosnap_v.get()))
        try:   # DS2 v2.52: the interval — clamped, junk-proof
            _snap_h = max(1, min(168, int(float(
                self.activity_hours_v.get()))))
        except Exception:
            _snap_h = 24
        cfg.set("activity_autosnap_hours", _snap_h)
        self.app._deps_sig_state = ""
        self.app._deps_probed_at = 0.0
        self.app._update_depswatch(force=True)
        self.app._git_sig_state = ""
        self.app._git_probed_at = 0.0
        self.app._update_gitchip(force=True)
        try:   # DS2 v2.36: heartbeat minutes -> clamped seconds
            _upd_secs = max(900, min(21600,
                                     int(self.updint_v.get()) * 60))
        except Exception:
            _upd_secs = 3600
        cfg.set("update_check_secs", _upd_secs)
        # editor changes apply live; colours need the rebuild
        self.app.editor.set_font_size(cfg.get("editor_font_size", 11))
        self.app.editor.set_wrap(bool(cfg.get("word_wrap", False)))
        self.app.editor.auto_indent = \
            bool(cfg.get("editor_auto_indent", True))
        self.app.editor.auto_close = \
            bool(cfg.get("editor_auto_close", True))
        if self.app._split is not None:
            self.app._split.auto_indent = self.app.editor.auto_indent
            self.app._split.auto_close = self.app.editor.auto_close
        look_changed = self.theme_v.get() != self.app.theme.mode or \
            self.accent_v.get() != self.app.theme.accent_name
        self.app.terminal.log("Settings saved."
                              + (" Restarting to apply the new look…"
                                 if look_changed else ""))
        if look_changed:
            self.app.restart_requested = True
            self.app.root.after(400, self.app.root.destroy)
        self.grab_release()
        self.destroy()


def main():
    from .config import Config
    import dxn1_studio.config as cfgmod

    args = sys.argv[1:]

    # --smoke-test must never touch the real user config
    smoke = "--smoke-test" in args
    if smoke:
        tmp_cfg = tempfile.mkdtemp(prefix="dxn1-smoke-cfg-")
        cfgmod.CONFIG_DIR = tmp_cfg
        cfgmod.CONFIG_PATH = os.path.join(tmp_cfg, "config.json")

    config = Config()
    if "--reset-config" in args:
        config.reset()

    # inline args
    filtered = []
    project = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project" and i + 1 < len(args):
            project = args[i + 1]
            i += 2
            continue
        if a in ("--smoke-test", "--reset-config", "--no-splash"):
            i += 1
            continue
        # bare path convenience: dxn1 studio ~/my-app
        if os.path.isdir(a) and project is None:
            project = a
            i += 1
            continue
        filtered.append(a)
        i += 1

    while True:
        app = DXN1Studio(config, smoke_test=smoke,
                         no_splash="--no-splash" in args)
        app.pending_project = project
        app.run()
        if not app.restart_requested:
            break



