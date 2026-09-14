"""DXN1 STUDIO — Prompt library (DS2).

Good assistant answers start with good asks. This module gives every
workspace a small library of reusable prompts — editable, searchable,
with placeholders that fill themselves in at insert time:

    {file}       basename of the open file      (main.py)
    {path}       full path of the open file
    {workspace}  workspace folder name
    {selection}  current selection (capped) or "the file"
    {lang}       file extension without the dot (py, js…)
    {date}       today (YYYY-MM-DD)

Prompts live in ``<ws>/.dxn1/prompts.json`` (global:
``~/.dxn1-studio/prompts.json``) and are merged — workspace wins on
name clashes. Ships with six starter prompts so the picker is never
empty. Inserting drops the rendered text into the agent chat input
(or the clipboard when the panel is closed).

Engine is UI-free and testable; ``open_picker`` is the thin shell.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date

from . import APP_NAME

WS_STORE = os.path.join(".dxn1", "prompts.json")
GLOBAL_STORE = os.path.join(os.path.expanduser("~"), ".dxn1-studio",
                            "prompts.json")
PLACEHOLDER = re.compile(r"\{(\w+)\}")
MAX_PROMPTS = 200
SELECTION_CAP = 400          # chars of {selection} pasted into chat

STARTERS = [
    {"name": "Explain this file",
     "template": "Explain what {file} does, its main building blocks, "
                 "and anything surprising. Be concrete and brief.",
     "description": "a guided tour of the open file"},
    {"name": "Review for bugs",
     "template": "Review {file} for bugs, edge cases and unsafe "
                 "assumptions. Rank findings by severity and show "
                 "minimal fixes.",
     "description": "severity-ranked bug hunt"},
    {"name": "Write tests",
     "template": "Write focused unit tests for {file} in the same "
                 "language ({lang}). Cover the happy path first, then "
                 "edge cases. Use the project's existing test style.",
     "description": "unit tests for the current file"},
    {"name": "Refactor for clarity",
     "template": "Refactor the following code for readability without "
                 "changing behaviour. Keep the public API identical:\n\n"
                 "{selection}",
     "description": "clarity pass on the selection"},
    {"name": "Add docstrings",
     "template": "Add concise docstrings/comments to every public "
                 "function and class in {file}. Match the existing "
                 "style; do not change any code.",
     "description": "document the open file"},
    {"name": "Commit message",
     "template": "Write a conventional-commit message for the staged "
                 "changes in {workspace}. Subject under 72 chars, "
                 "then a short body explaining the why.",
     "description": "conventional commit from staged work"},
]


def store_path(workspace=None):
    """Library location: workspace store, else the global one."""
    if workspace:
        return os.path.join(workspace, WS_STORE)
    return GLOBAL_STORE


def _read_file(path):
    """List of prompt dicts from one JSON file (defensive)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        template = str(item.get("template", ""))
        if not name or not template.strip():
            continue
        out.append({"name": name[:80], "template": template[:8000],
                    "description": str(item.get("description", ""))[:200]})
    return out[:MAX_PROMPTS]


def load_prompts(workspace=None, starters=True):
    """Merged library: starters + global + workspace (last wins)."""
    merged = {}
    order = []
    if starters:
        for p in STARTERS:
            merged[p["name"]] = p
            order.append(p["name"])
    for path in (None if workspace else GLOBAL_STORE,
                 store_path(workspace) if workspace else None):
        if not path:
            continue
        for p in _read_file(path):
            if p["name"] not in merged:
                order.append(p["name"])
            merged[p["name"]] = p
    return [merged[n] for n in order if n in merged]


def save_user_prompt(workspace, name, template, description=""):
    """Append/replace one prompt in the workspace library."""
    name = str(name or "").strip()[:80]
    template = str(template or "")[:8000]
    if not name or not template.strip():
        return False, "name and template are required"
    prompts = [p for p in _read_file(store_path(workspace))
               if p["name"] != name]
    prompts.append({"name": name, "template": template,
                    "description": description[:200]})
    try:
        os.makedirs(os.path.dirname(store_path(workspace)), exist_ok=True)
        tmp = store_path(workspace) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(prompts[:MAX_PROMPTS], fh, indent=1)
        os.replace(tmp, store_path(workspace))
        return True, name
    except OSError as exc:
        return False, str(exc)


def delete_user_prompt(workspace, name):
    """Remove one prompt from the workspace library (starters survive)."""
    path = store_path(workspace)
    prompts = [p for p in _read_file(path) if p["name"] != name]
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(prompts, fh, indent=1)
        return True
    except OSError:
        return False


def render(template, file_path="", workspace="", selection="",
           extra=None):
    """Fill ``{placeholders}``; unknown names stay literal."""
    ctx = {
        "file": os.path.basename(file_path) if file_path else "the file",
        "path": file_path or "",
        "workspace": os.path.basename(
            os.path.abspath(workspace)) if workspace else "the workspace",
        "selection": (selection.strip()[:SELECTION_CAP] or "the file"),
        "lang": (os.path.splitext(file_path or "")[1][1:].lower()
                 or "code"),
        "date": date.today().isoformat(),
    }
    if extra:
        ctx.update({str(k): str(v) for k, v in extra.items()
                    if isinstance(k, str)})

    def _sub(match):
        key = match.group(1)
        return ctx.get(key, match.group(0))

    return PLACEHOLDER.sub(_sub, template)


def filter_prompts(prompts, query):
    """Case-insensitive match on name + description; empty keeps all."""
    q = (query or "").strip().lower()
    if not q:
        return list(prompts)
    out = []
    for p in prompts:
        hay = (p.get("name", "") + " " + p.get("description", "")).lower()
        if q in hay:
            out.append(p)
    return out


# ------------------------------------------------------------------ GUI
_C = {}


def insert_into_agent(panel, text):
    """Drop rendered text into the agent chat input (defensive)."""
    try:
        entry = getattr(panel, "entry", None)
        if entry is None:
            return False
        entry.delete("1.0", "end")
        entry.insert("1.0", text)
        changer = getattr(panel, "_on_entry_change", None)
        if changer:
            changer()
        entry.focus_set()
        return True
    except Exception:               # noqa: BLE001 — chat never breaks
        return False


def open_picker(master, theme, workspace=None, on_use=None, context=None,
                on_log=None):
    """Open the prompt library picker.

    ``context`` is a callable returning the render context dict
    (file/workspace/selection); ``on_use(rendered)`` receives the final
    text.
    """
    import tkinter as tk

    log = on_log or (lambda m: None)
    get_ctx = context or (lambda: {})
    use = on_use or (lambda text: None)

    for key, val in (
            ("bg", theme["bg"]), ("card", theme["card"]),
            ("header", theme["header"]), ("border", theme["border"]),
            ("text", theme["text"]), ("muted", theme["text_muted"]),
            ("hover", theme["hover"]),
            ("input", theme.get("overlay") or theme["card"]),
            ("statusbar", theme["statusbar"])):
        _C[key] = val
    accent = getattr(theme, "accent", "#7c3aed")
    font = getattr(theme, "font", lambda s=10, w="normal": ("sans-serif", s, w))
    mono = getattr(theme, "mono", lambda s=10, w="normal": ("monospace", s, w))

    win = tk.Toplevel(master)
    win.title("Prompt library")
    win.configure(bg=_C["bg"])
    win.transient(master)
    win.resizable(False, False)
    win.bind("<Escape>", lambda e: win.destroy())

    all_prompts = load_prompts(workspace)
    pstate = {"shown": list(all_prompts), "sel": 0,
             "all": list(all_prompts)}

    entry = tk.Entry(win, bg=_C["input"], fg=_C["text"],
                     insertbackground=_C["text"], relief=tk.FLAT,
                     font=mono(11), highlightthickness=1,
                     highlightbackground=_C["border"],
                     highlightcolor=accent)
    entry.pack(fill=tk.X, padx=14, pady=(14, 6), ipady=7)

    list_frame = tk.Frame(win, bg=_C["bg"])
    list_frame.pack(fill=tk.BOTH, expand=True, padx=8)

    foot = tk.Frame(win, bg=_C["statusbar"])
    foot.pack(fill=tk.X, side=tk.BOTTOM)
    info = tk.Label(foot, text="↑↓ choose · Enter use · Del removes a "
                              "saved prompt", bg=_C["statusbar"],
                    fg=accent, font=font(9))
    info.pack(side=tk.LEFT, padx=12)

    def _flash(msg):
        info.config(text=msg)
        win.after(2200, lambda: info.config(
            text="↑↓ choose · Enter use · Del removes a saved prompt"))

    add_row = tk.Frame(win, bg=_C["bg"])
    add_row.pack(fill=tk.X, padx=14, pady=(4, 10))
    tk.Label(add_row, text="save current input as:", bg=_C["bg"],
             fg=_C["muted"], font=font(9)).pack(side=tk.LEFT)
    name_var = tk.StringVar()
    name_entry = tk.Entry(add_row, textvariable=name_var, width=22,
                          bg=_C["input"], fg=_C["text"],
                          insertbackground=_C["text"], relief=tk.FLAT,
                          font=font(9))
    name_entry.pack(side=tk.LEFT, padx=6)

    def _save_current():
        name = name_var.get().strip()
        template = entry.get().strip()
        if not name or not template:
            _flash("give it a name (and a template) first")
            return
        ok, msg = save_user_prompt(workspace, name, template,
                                   "saved from picker")
        _flash(("saved ✓ " + msg) if ok else ("save failed: " + msg))
        if ok:
            pstate["all"] = load_prompts(workspace)
            _apply_filter()

    tk.Button(add_row, text="Save", command=_save_current, bg=_C["card"],
              fg=_C["text"], activebackground=_C["hover"],
              activeforeground=_C["text"], relief=tk.FLAT,
              font=font(9), padx=8).pack(side=tk.LEFT)

    rows = []

    def _paint():
        for row in rows:
            try:
                row.destroy()
            except Exception:       # noqa: BLE001
                pass
        rows.clear()
        shown = pstate["shown"]
        if not shown:
            lbl = tk.Label(list_frame, text="no prompts match",
                           bg=_C["bg"], fg=_C["muted"], font=font(10))
            lbl.pack(anchor="w", padx=10, pady=10)
            rows.append(lbl)
            return
        for i, p in enumerate(shown):
            active = i == pstate["sel"]
            row = tk.Frame(list_frame,
                           bg=_C["hover"] if active else _C["bg"])
            row.pack(fill=tk.X, padx=2, pady=1)
            tk.Label(row, text="›" if active else " ", bg=row["bg"],
                     fg=accent, font=font(11, "bold"), width=2).pack(
                side="left")
            tk.Label(row, text=p["name"], bg=row["bg"], fg=_C["text"],
                     font=font(11, "bold" if active else "normal")
                     ).pack(side="left")
            if p.get("description"):
                tk.Label(row, text="  " + p["description"], bg=row["bg"],
                         fg=_C["muted"], font=font(9)).pack(side="left")
            row.bind("<Button-1>", lambda e, idx=i: _use(idx))
            rows.append(row)

    def _use(idx=None):
        idx = pstate["sel"] if idx is None else idx
        if not (0 <= idx < len(pstate["shown"])):
            return
        p = pstate["shown"][idx]
        rendered = render(p["template"], **(get_ctx() or {}))
        try:
            win.clipboard_clear()
            win.clipboard_append(rendered)   # always copy — cheap fallback
        except Exception:               # noqa: BLE001
            pass
        use(rendered)
        log("prompt library: inserted '%s' (also copied to clipboard)"
            % p["name"])
        win.destroy()

    def _delete_saved(_event=None):
        idx = pstate["sel"]
        if not (0 <= idx < len(pstate["shown"])):
            return
        p = pstate["shown"][idx]
        if delete_user_prompt(workspace, p["name"]):
            pstate["all"] = load_prompts(workspace)
            pstate["sel"] = max(0, pstate["sel"] - 1)
            _apply_filter()
            _flash("removed '%s'" % p["name"])

    def _apply_filter():
        pstate["shown"] = filter_prompts(pstate["all"], entry.get())
        pstate["sel"] = 0
        _paint()

    def _on_type(event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape",
                                      "Delete"):
            return
        _apply_filter()

    def _move(delta):
        if not pstate["shown"]:
            return
        pstate["sel"] = (pstate["sel"] + delta) % len(pstate["shown"])
        _paint()

    entry.bind("<KeyRelease>", _on_type)
    entry.bind("<Down>", lambda e: _move(1))
    entry.bind("<Up>", lambda e: _move(-1))
    entry.bind("<Return>", lambda e: _use())
    entry.bind("<Escape>", lambda e: win.destroy())
    entry.bind("<Delete>", _delete_saved)
    _paint()

    win.update_idletasks()
    w, h = 620, min(520, max(240, win.winfo_reqheight()))
    try:
        x = win.master.winfo_rootx() + \
            (win.master.winfo_width() - w) // 2
        y = win.master.winfo_rooty() + 90
    except Exception:               # noqa: BLE001
        x = y = 60
    win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
    entry.focus_set()
    # expose internals — tests and plugins may drive the picker
    win.pstate = pstate
    win.entry = entry
    win._apply_filter = _apply_filter
    win._use = _use
    win._save_current = _save_current
    return win
