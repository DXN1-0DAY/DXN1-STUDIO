"""DXN1 STUDIO — .env lint & mask (DS2).

Your .env file is load-bearing and invisible.  This lints it —
duplicate keys, keys with invalid characters, spaces around "=",
unquoted values containing spaces or "#" comments glued to values,
empty values, secrets hiding in plain sight — and produces a masked
copy safe to paste into an issue or a screenshot.

Pure engine, unit-tested; window is a thin skin.  Open from the
palette (".env lint & mask…") or terminal `env`.
"""

import re
import tkinter as tk
from tkinter import ttk

from .theme import FONT_UI, FONT_MONO

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_SECRET_HINTS = ("key", "token", "secret", "password", "passwd", "pwd",
                 "credential", "private", "auth", "api")


def parse_env(text):
    """-> list of entry dicts, one per line. Never raises."""
    entries = []
    for i, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        e = {"line": i, "raw": raw, "key": "", "value": "",
             "comment": False, "blank": False, "error": ""}
        if not line:
            e["blank"] = True
        elif line.startswith("#"):
            e["comment"] = True
        elif "=" in line:
            key, _, val = line.partition("=")
            e["key"] = key.strip()
            val = val.strip()
            e["inline_comment"] = ""
            # a quoted value may carry a trailing comment after the
            # closing quote: KEY="hello world"  # note
            if val[:1] in ("'", '"') and len(val) >= 2:
                close = val.find(val[0], 1)
                if close > 0:
                    e["inline_comment"] = val[close + 1:].strip()
                    val = val[:close + 1]
            e["value"] = val
            if key != key.strip():
                e["error"] = "spaces around the key or before '='"
            elif not e["key"]:
                e["error"] = "empty key"
        else:
            e["error"] = "no '=' — not a KEY=value line"
        entries.append(e)
    return entries


def lint_env(text):
    """-> list of findings (line, severity, message). Never raises."""
    findings = []
    seen = {}
    entries = parse_env(text)
    for e in entries:
        n, line_no = e, e["line"]
        if n["blank"] or n["comment"]:
            continue
        if n["error"]:
            findings.append((line_no, "error", n["error"]))
            continue
        key, val = n["key"], n["value"]
        if not _KEY_RE.match(key):
            findings.append((line_no, "error",
                             f"invalid key {key!r} — use letters, digits, "
                             "underscore (not starting with a digit)"))
        if key.lower() in seen:
            findings.append((line_no, "error",
                             f"duplicate key {key} (first defined on "
                             f"line {seen[key.lower()]})"))
        else:
            seen[key.lower()] = line_no
        if not val:
            findings.append((line_no, "warn", f"{key} has an empty value"))
        quoted = (val.startswith(("'", '"'))
                  and val.endswith(("'", '"')) and len(val) >= 2)
        if val and not quoted and " #" in val:
            findings.append((line_no, "warn",
                             f"{key}: unquoted value contains ' #' — "
                             "everything after # is lost; quote it"))
        if " " in val and not quoted:
            findings.append((line_no, "warn",
                             f"{key}: unquoted value contains spaces"))
        if val[:1] != val[-1:] and val[:1] in "'\"":
            findings.append((line_no, "error",
                             f"{key}: quote opened but never closed"))
    if not findings and entries and any(not e["blank"] and
                                        not e["comment"]
                                        for e in entries):
        pass
    if text and not text.endswith("\n"):
        findings.append((len(entries), "info",
                         "no newline at end of file"))
    return findings


def is_secret_key(key):
    k = (key or "").lower()
    return any(h in k for h in _SECRET_HINTS)


def mask_env(text, keep=3):
    """Same file with secret values masked — safe to share.

    Values of keys that smell like secrets become *** (or keep the
    first `keep` chars when the value is long enough to stay useful).
    """
    out = []
    for e in parse_env(text):
        raw = e["raw"]
        if e["blank"] or e["comment"] or e["error"] or not e["key"]:
            out.append(raw)
            continue
        val = e["value"]
        # URL with embedded credentials: postgres://user:pass@host
        if val and "://" in val and "@" in val.split("://", 1)[1]:
            scheme, rest = val.split("://", 1)
            creds, _, host = rest.rpartition("@")
            if ":" in creds:
                user = creds.split(":", 1)[0]
                val = f"{scheme}://{user}:***@{host}"
                lead = raw[:len(raw) - len(raw.lstrip())]
                out.append(f"{lead}{e['key']}={val}")
                continue
        if is_secret_key(e["key"]) and val:
            if len(val) > keep * 2:
                masked = val[:keep] + "…" + "*" * min(8, len(val) - keep)
            else:
                masked = "*" * max(3, len(val))
            lead = raw[:len(raw) - len(raw.lstrip())]
            out.append(f"{lead}{e['key']}={masked}")
        else:
            out.append(raw)
    return "\n".join(out)


def summary(text):
    """-> (keys, secrets, findings_count) quick triple for the CLI."""
    entries = [e for e in parse_env(text)
               if not e["blank"] and not e["comment"] and not e["error"]]
    return (len(entries), sum(1 for e in entries
                              if is_secret_key(e["key"])),
            len(lint_env(text)))


# --------------------------------------------------------------- window

class EnvLintWindow(tk.Toplevel):
    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.t = theme
        self.title(".env lint & mask — DXN1 STUDIO")
        self.configure(bg=theme["bg"])
        self.geometry("840x600")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 840x600 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 840, 600))
        self.minsize(680, 460)
        try:
            self.transient(parent.winfo_toplevel()
                           if parent is not None else parent)
        except Exception:
            pass
        self._build()
        if initial:
            self.inp.insert("1.0", initial)
        self._update()
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 840, 600
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        t = self.t
        row = tk.Frame(self, bg=t["bg"])
        row.pack(fill="x", padx=12, pady=(12, 6))
        self._btn(row, "Lint", lambda: self._update()).pack(side="left")
        self._btn(row, "Copy masked copy",
                  lambda: self._copy(self.masked, "masked copy",
                                     looks_secret=True)).pack(
            side="left", padx=(6, 0))
        self._btn(row, "Load current .env",
                  self._load_file).pack(side="left", padx=(6, 0))
        self.summary = tk.Label(row, text="", bg=t["bg"],
                                fg=t["text_muted"], font=(FONT_UI, 10))
        self.summary.pack(side="left", padx=(12, 0))

        body = tk.Frame(self, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=12)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Env.Treeview", background=t["card"],
                        fieldbackground=t["card"], foreground=t["text"],
                        rowheight=24, borderwidth=0, font=(FONT_MONO, 10))
        style.configure("Env.Treeview.Heading", background=t["header"],
                        foreground=t["text_secondary"], relief="flat",
                        font=(FONT_UI, 9))

        lw = tk.Frame(body, bg=t["border"])
        lw.pack(side="left", fill="both", expand=True)
        tk.Label(lw, text="your .env (paste here)", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9), anchor="w",
                 padx=8).pack(fill="x")
        self.inp = tk.Text(lw, wrap="none", relief="flat", bg=t["editor"],
                           fg=t["text"], insertbackground=t["text"],
                           font=(FONT_MONO, 10), padx=8, pady=6, bd=0,
                           undo=True)
        self.inp.pack(fill="both", expand=True)
        self.inp.bind("<<Modified>>", self._on_modify)

        rw = tk.Frame(body, bg=t["bg"])
        rw.pack(side="left", fill="both", expand=True, padx=(8, 0))
        fw = tk.Frame(rw, bg=t["border"])
        fw.pack(fill="both")
        tk.Label(fw, text="findings", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9), anchor="w",
                 padx=8).pack(fill="x")
        self.find = ttk.Treeview(fw, columns=("l", "s", "m"),
                                 show="headings", height=7,
                                 style="Env.Treeview")
        for cid, label, w in (("l", "line", 46), ("s", "sev", 52),
                              ("m", "message", 330)):
            self.find.heading(cid, text=label)
            self.find.column(cid, width=w, anchor="w")
        self.find.pack(fill="both", expand=True)
        self.find.tag_configure("error", foreground=t["text"])
        self.find.tag_configure("warn", foreground=t["text_secondary"])
        self.find.tag_configure("info", foreground=t["text_muted"])

        mw = tk.Frame(rw, bg=t["border"])
        mw.pack(fill="both", expand=True, pady=(8, 0))
        tk.Label(mw, text="masked copy — safe to share", bg=t["header"],
                 fg=t["text_secondary"], font=(FONT_UI, 9), anchor="w",
                 padx=8).pack(fill="x")
        self.masked = tk.Text(mw, wrap="none", relief="flat",
                              bg=t["editor"], fg=t["text"],
                              font=(FONT_MONO, 10), padx=8, pady=6, bd=0,
                              state="disabled")
        self.masked.pack(fill="both", expand=True)

        self.status = tk.Label(self, text="", bg=t["bg"],
                               fg=t["text_muted"], font=(FONT_UI, 9))
        self.status.pack(anchor="w", padx=12, pady=(6, 12))

    def _btn(self, master, text, cmd):
        t = self.t
        return tk.Button(master, text=text, command=cmd, relief="flat",
                         cursor="hand2", bg=t["header"], fg=t["text"],
                         bd=0, padx=12, pady=5,
                         activebackground=t["hover"],
                         activeforeground=t["text"], font=(FONT_UI, 9))

    def _on_modify(self, event):
        try:
            self.inp.edit_modified(False)
        except tk.TclError:
            pass
        self._update()

    def _load_file(self):
        import os
        candidates = []
        try:
            app = self.master
            ws = getattr(app, "project_dir", None)
            if ws:
                candidates.append(os.path.join(ws, ".env"))
        except Exception:
            pass
        candidates.append(".env")
        for path in candidates:
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as fh:
                    data = fh.read()
            except (OSError, ValueError):
                continue
            self.inp.delete("1.0", "end")
            self.inp.insert("1.0", data)
            self.status.configure(text=f"loaded {path}",
                                  fg=self.t["success"])
            return
        self.status.configure(text="no .env found in the workspace",
                              fg=self.t["text_muted"])

    def _copy(self, widget, what, looks_secret=False):
        try:
            data = widget.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(data)
            note = " (double-check nothing sensitive remains)" \
                if looks_secret else ""
            self.status.configure(text=f"copied {what}{note}",
                                  fg=self.t["success"])
        except tk.TclError:
            pass

    def _update(self):
        src = self.inp.get("1.0", "end-1c")
        findings = lint_env(src)
        try:
            self.find.delete(*self.find.get_children(""))
            for line_no, sev, msg in findings:
                self.find.insert("", "end", values=(line_no, sev, msg),
                                 tags=(sev,))
            self.masked.configure(state="normal")
            self.masked.delete("1.0", "end")
            self.masked.insert("1.0", mask_env(src))
            self.masked.configure(state="disabled")
            keys, secrets, n = summary(src)
            errs = sum(1 for _, s, _ in findings if s == "error")
            self.summary.configure(
                text=f"{keys} keys · {secrets} look like secrets · "
                     f"{errs} error(s)")
        except tk.TclError:
            pass


def open_envlint(parent, theme, initial=""):
    return EnvLintWindow(parent, theme, initial)
