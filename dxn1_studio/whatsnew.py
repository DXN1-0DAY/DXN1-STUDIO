"""DXN1 STUDIO — What's New (DS2).

Seven hours of sprinting produces a lot of changelog. This window
turns ``CHANGELOG.md`` into something a human actually reads: a
version rail on the left, rendered release notes on the right, with
section headings (Added / Fixed / Changed…) painted in theme colours.

It doubles as an onboarding touch: after an upgrade the studio opens
"What's New" once (``last_seen_version`` in the config guards it), so
every new tag announces itself exactly one time.

Engine is UI-free and testable: ``parse_changelog`` handles the real
Keep-a-Changelog file as well as mangled/partial ones.
"""

from __future__ import annotations

import os
import re

from . import APP_NAME, APP_VERSION

CHANGELOG_CANDIDATES = (
    "CHANGELOG.md",
    os.path.join("docs", "CHANGELOG.md"),
)

_HEADER = re.compile(r"^##\s+\[?([0-9][0-9A-Za-z.\-]*)\]?\s*[-—–]?\s*(.*)$")
_SECTION = re.compile(r"^###\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*]\s+")


def find_changelog(root=None):
    """Path of the changelog shipped next to the package, or ''."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root:
        base = root
    for cand in CHANGELOG_CANDIDATES:
        path = os.path.join(base, cand)
        if os.path.isfile(path):
            return path
    return ""


def parse_changelog(text):
    """``[{version, tag, sections: [{title, items}]}]`` — newest first.

    Bullets keep their ``**bold`` markers for the GUI to colour; the
    plain-text helpers strip them. Unparsable input yields whatever
    headings were found (never raises).
    """
    entries = []
    current = None
    section = None
    for raw in (text or "").split("\n"):
        line = raw.rstrip()
        head = _HEADER.match(line)
        if head:
            current = {"version": head.group(1), "tag": head.group(2).strip(),
                       "sections": []}
            entries.append(current)
            section = None
            continue
        if current is None:
            continue
        sect = _SECTION.match(line)
        if sect:
            section = {"title": sect.group(1).strip(), "items": []}
            current["sections"].append(section)
            continue
        if _BULLET.match(line):
            item = _BULLET.sub("", line).strip()
            if section is None:
                section = {"title": "Notes", "items": []}
                current["sections"].append(section)
            if item:
                section["items"].append(item)
            continue
        # continuation lines for wrapped bullets
        if section and section["items"] and line.startswith("  ") \
                and line.strip():
            section["items"][-1] += " " + line.strip()
    return entries


def load_entries(root=None):
    """Parsed changelog entries from disk; [] when none found."""
    path = find_changelog(root)
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return parse_changelog(fh.read())
    except OSError:
        return []


def plain_bullet(item):
    """Strip markdown emphasis for plain-text contexts."""
    return item.replace("**", "").replace("`", "")


def new_entries(entries, last_seen_version):
    """Entries strictly newer than ``last_seen_version`` (semver-ish)."""

    def key(v):
        try:
            return tuple(int(p) for p in str(v).split("."))
        except ValueError:
            return (0, 0, 0)

    if not last_seen_version:
        return entries[:1]
    limit = key(last_seen_version)
    return [e for e in entries if key(e["version"]) > limit]


# ------------------------------------------------------------------ GUI
_C = {}


def open_whatsnew(master, theme, root_dir=None, highlight=None,
                  on_log=None):
    """Open the What's New window. ``highlight`` marks the freshest tag."""
    import tkinter as tk
    from tkinter import ttk

    log = on_log or (lambda m: None)
    entries = load_entries(root_dir)
    accent = getattr(theme, "accent", "#7c3aed")
    font = getattr(theme, "font", lambda s=10, w="normal": ("sans-serif", s, w))
    mono = getattr(theme, "mono", lambda s=10, w="normal": ("monospace", s, w))

    for key, val in (
            ("bg", theme["bg"]), ("card", theme["card"]),
            ("header", theme["header"]), ("border", theme["border"]),
            ("text", theme["text"]), ("muted", theme["text_muted"]),
            ("hover", theme["hover"]),
            ("statusbar", theme["statusbar"])):
        _C[key] = val

    win = tk.Toplevel(master)
    win.title("What's New — DS2")
    win.configure(bg=_C["bg"])
    win.transient(master)
    win.geometry("780x560")

    head = tk.Frame(win, bg=_C["header"])
    head.pack(fill=tk.X)
    tk.Label(head, text="WHAT'S NEW", bg=_C["header"], fg=_C["text"],
             font=font(13, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
    tk.Label(head, text="every tag, every feature — straight from the "
                        "changelog", bg=_C["header"], fg=_C["muted"],
             font=font(9)).pack(anchor="w", padx=16, pady=(0, 10))

    body = tk.Frame(win, bg=_C["bg"])
    body.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

    # left rail — versions
    rail = tk.Frame(body, bg=_C["card"], highlightthickness=1,
                    highlightbackground=_C["border"], width=150)
    rail.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
    rail.pack_propagate(False)

    # right pane — rendered notes
    pane = tk.Frame(body, bg=_C["card"], highlightthickness=1,
                    highlightbackground=_C["border"])
    pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    text = tk.Text(pane, bg=_C["card"], fg=_C["text"], relief=tk.FLAT,
                   bd=0, wrap="word", font=font(10), state="disabled",
                   padx=16, pady=12, highlightthickness=0)
    vsb = ttk.Scrollbar(pane, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    text.tag_configure("h1", font=font(14, "bold"), foreground=_C["text"],
                       spacing1=2, spacing3=6)
    text.tag_configure("tag", font=font(9), foreground=accent,
                       spacing3=10)
    text.tag_configure("sect", font=font(10, "bold"), foreground=accent,
                       spacing1=10, spacing3=2)
    text.tag_configure("item", font=font(10), foreground=_C["text"],
                       lmargin2=18, spacing1=2)
    text.tag_configure("muted", font=font(9), foreground=_C["muted"])

    rail_rows = []

    def _show(entry):
        text.config(state="normal")
        text.delete("1.0", "end")
        text.insert("end", "Version %s\n" % entry["version"], "h1")
        text.insert("end", (entry["tag"] or "release") + "\n", "tag")
        for sect in entry["sections"]:
            text.insert("end", sect["title"].upper() + "\n", "sect")
            for item in sect["items"]:
                text.insert("end", "•  " + plain_bullet(item) + "\n", "item")
            text.insert("end", "\n", "muted")
        text.insert("end", "— the DXN1 STUDIO team", "muted")
        text.config(state="disabled")

    def _pick(idx):
        for i, row in enumerate(rail_rows):
            row.config(bg=_C["hover"] if i == idx else _C["card"])
        _show(entries[idx])

    if not entries:
        tk.Label(rail, text="changelog not found", bg=_C["card"],
                 fg=_C["muted"], font=font(9)).pack(padx=10, pady=10)
        text.config(state="normal")
        text.insert("end", "No changelog found next to the app.\n", "h1")
        text.config(state="disabled")
    else:
        for i, entry in enumerate(entries):
            label = "v" + entry["version"]
            if entry["version"] == (highlight or APP_VERSION):
                label += "  ★"
            row = tk.Label(rail, text=label,
                           bg=_C["card"],
                           fg=accent if i == 0 else _C["text"],
                           font=mono(10, "bold" if i == 0 else "normal"),
                           anchor="w", padx=12, pady=4)
            row.pack(fill=tk.X)
            row.bind("<Button-1>", lambda e, idx=i: _pick(idx))
            rail_rows.append(row)
        _pick(0)

    foot = tk.Frame(win, bg=_C["statusbar"])
    foot.pack(fill=tk.X, side=tk.BOTTOM)
    tk.Label(foot, text="%d releases shipped" % len(entries),
             bg=_C["statusbar"], fg=accent, font=font(9)
             ).pack(side=tk.LEFT, padx=12)
    win.bind("<Escape>", lambda e: win.destroy())
    log("what's new: %d releases" % len(entries))
    return win
