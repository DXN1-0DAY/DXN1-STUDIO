"""DS2 Tree Export — turn any directory into a clean ASCII/Unicode tree.

Built for READMEs and docs: skip rules (junk dirs, hidden folders),
depth cap, entry cap, file sizes, dir-first sorting, markdown-ready
output. Engine is pure and unit-tested; the window regenerates live.

Open with: palette, Workshop menu, terminal ``tree`` / ``tree <path>``.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .widgets import TREE_SKIP

__all__ = [
    "build_tree", "render_tree", "human_size", "TreeExport",
    "open_treeexport",
]

EXTRA_SKIP = {"__pycache__", "node_modules", ".venv", "venv",
              ".mypy_cache", ".pytest_cache", ".tox", "dist",
              "build", ".git", ".hg", ".svn", ".idea", ".vscode",
              ".dx1", "site-packages", ".terraform", "__MACOSX"}
SKIP = set(TREE_SKIP or ()) | EXTRA_SKIP

TEE = "├── "
LAST = "└── "
PIPE = "│   "
SPACE = "    "


def human_size(n):
    """12345 -> '12.1 KB' (decimal units)."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{int(n)} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def build_tree(root, max_depth=4, max_entries=2000, show_hidden=False,
               show_sizes=True):
    """Walk *root* → (lines, stats) where lines carry (prefix, name,
    is_dir, size). Pure: never follows symlinked dirs, never raises.

    stats: {"dirs": int, "files": int, "bytes": int, "truncated": bool,
    "skipped": int}
    """
    stats = {"dirs": 0, "files": 0, "bytes": 0, "truncated": False,
             "skipped": 0}
    lines = []

    def entries_of(path):
        try:
            names = os.listdir(path)
        except OSError:
            return []
        out = []
        for n in names:
            if not show_hidden and n.startswith("."):
                continue
            full = os.path.join(path, n)
            if os.path.isdir(full) and not os.path.islink(full):
                if n in SKIP:
                    stats["skipped"] += 1
                    continue
                out.append((n, True))
            elif os.path.isfile(full):
                out.append((n, False))
        out.sort(key=lambda t: (not t[1], t[0].lower()))
        return out

    def walk(path, prefix, depth):
        if depth > max_depth:
            stats["truncated"] = stats["truncated"] or bool(entries_of(path))
            return
        kids = entries_of(path)
        if len(kids) > max_entries - len(lines):
            stats["truncated"] = True
            kids = kids[: max(0, max_entries - len(lines))]
        for i, (name, is_dir) in enumerate(kids):
            last = i == len(kids) - 1
            full = os.path.join(path, name)
            size = 0
            if not is_dir:
                try:
                    size = os.path.getsize(full)
                    stats["files"] += 1
                    stats["bytes"] += size
                except OSError:
                    size = -1
            else:
                stats["dirs"] += 1
            lines.append((prefix + (LAST if last else TEE), name,
                          is_dir, size))
            if is_dir:
                walk(full, prefix + (SPACE if last else PIPE), depth + 1)

    root = os.path.abspath(root)
    if os.path.isdir(root):
        walk(root, "", 1)
    return lines, stats


def render_tree(root, lines, stats, show_sizes=True):
    """(lines, stats) from build_tree → display text."""
    head = os.path.basename(root) or root
    out = [head + "/"]
    for prefix, name, is_dir, size in lines:
        label = name + ("/" if is_dir else "")
        if show_sizes and not is_dir and size >= 0:
            label += f"  ({human_size(size)})"
        out.append(prefix + label)
    tail = (f"{stats['dirs']} directories, {stats['files']} files, "
            f"{human_size(stats['bytes'])}")
    if stats["skipped"]:
        tail += f" · {stats['skipped']} junk dirs skipped"
    if stats["truncated"]:
        tail += " · output truncated"
    out.append("")
    out.append(tail)
    return "\n".join(out)


class TreeExport(tk.Toplevel):
    """Directory-tree export window."""

    def __init__(self, parent, theme, root_path="", workspace=""):
        super().__init__(parent)
        self.theme = theme or {}
        self.workspace = workspace or root_path
        self.root_path = tk.StringVar(
            value=root_path or workspace or os.path.expanduser("~"))
        self.show_hidden = tk.BooleanVar(value=False)
        self.show_sizes = tk.BooleanVar(value=True)
        self.depth = tk.StringVar(value="4")

        t = self.theme
        self.title("Tree Export — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("760x600")
        self.minsize(560, 420)
        try:
            self.transient(parent)
        except Exception:
            pass

        self._build_toolbar()
        self._build_output()
        self._build_statusbar()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<F5>", lambda _e: self.regenerate())
        self.regenerate()

    # ------------------------------------------------------------ UI
    def _build_toolbar(self):
        t = self.theme
        bar = tk.Frame(self, bg=t.get("header", "#242432"))
        bar.pack(fill=tk.X)

        def _lbl(text):
            return tk.Label(bar, text=text, bg=t.get("header", "#242432"),
                            fg=t.get("text_muted", "#8a8a9a"))

        _lbl("root").pack(side=tk.LEFT, padx=(10, 4), pady=6)
        tk.Entry(bar, textvariable=self.root_path, width=42, relief="flat",
                 bg=t.get("editor", "#1b1b24"),
                 fg=t.get("text", "#e8e8f0"),
                 insertbackground=t.get("text", "#e8e8f0")).pack(
            side=tk.LEFT, padx=2, pady=6)

        def _btn(text, cmd):
            return tk.Button(
                bar, text=text, command=cmd, relief="flat", bd=0,
                bg=t.get("hover", "#2c2c3e"), fg=t.get("text", "#e8e8f0"),
                activebackground=t.get("border", "#3a3a4e"),
                activeforeground=t.get("text", "#e8e8f0"),
                padx=10, pady=2, cursor="hand2")

        _btn("Browse…", self.pick_root).pack(side=tk.LEFT, padx=4)
        _lbl("depth").pack(side=tk.LEFT, padx=(8, 2))
        tk.Spinbox(bar, values=("1", "2", "3", "4", "5", "6"), width=3,
                   textvariable=self.depth, command=self.regenerate,
                   bg=t.get("editor", "#1b1b24"),
                   fg=t.get("text", "#e8e8f0"),
                   buttonbackground=t.get("hover", "#2c2c3e"),
                   relief="flat",
                   insertbackground=t.get("text", "#e8e8f0")).pack(
            side=tk.LEFT)
        tk.Checkbutton(bar, text="hidden", variable=self.show_hidden,
                       command=self.regenerate,
                       bg=t.get("header", "#242432"),
                       fg=t.get("text_muted", "#8a8a9a"),
                       activebackground=t.get("header", "#242432"),
                       activeforeground=t.get("text", "#e8e8f0"),
                       selectcolor=t.get("editor", "#1b1b24")).pack(
            side=tk.LEFT, padx=6)
        tk.Checkbutton(bar, text="sizes", variable=self.show_sizes,
                       command=self.regenerate,
                       bg=t.get("header", "#242432"),
                       fg=t.get("text_muted", "#8a8a9a"),
                       activebackground=t.get("header", "#242432"),
                       activeforeground=t.get("text", "#e8e8f0"),
                       selectcolor=t.get("editor", "#1b1b24")).pack(
            side=tk.LEFT)
        _btn("Copy", self.copy_tree).pack(side=tk.RIGHT, padx=8)
        _btn("Save…", self.save_tree).pack(side=tk.RIGHT, padx=2)

    def _build_output(self):
        t = self.theme
        wrap = tk.Frame(self, bg=t.get("bg", "#16161e"))
        wrap.pack(fill=tk.BOTH, expand=True)
        self.out = tk.Text(
            wrap, wrap="none", relief="flat", bd=0, undo=False,
            bg=t.get("editor", "#1b1b24"), fg=t.get("text", "#e8e8f0"),
            font=("TkFixedFont", 10), state=tk.DISABLED)
        ysb = ttk.Scrollbar(wrap, orient="vertical", command=self.out.yview)
        self.out.configure(yscrollcommand=ysb.set)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.out.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=6)

    def _build_statusbar(self):
        t = self.theme
        self.status = tk.Label(
            self, text="", anchor="w", bg=t.get("header", "#242432"),
            fg=t.get("text_muted", "#8a8a9a"), padx=10, pady=3)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # -------------------------------------------------------- actions
    def pick_root(self):
        path = filedialog.askdirectory(parent=self,
                                       title="Choose a folder to tree")
        if path:
            self.root_path.set(path)
            self.regenerate()

    def regenerate(self):
        root = self.root_path.get().strip()
        if not os.path.isdir(root):
            self._set_out(f"not a directory: {root}")
            self.status.config(text="pick a valid folder",
                               fg=self.theme.get("error", "#ff7a7a"))
            return
        try:
            depth = max(1, min(6, int(self.depth.get())))
        except ValueError:
            depth = 4
        lines, stats = build_tree(
            root, max_depth=depth, show_hidden=self.show_hidden.get(),
            show_sizes=self.show_sizes.get())
        self._set_out(render_tree(root, lines, stats,
                                  show_sizes=self.show_sizes.get()))
        self.status.config(
            text=f"{stats['dirs']} dirs · {stats['files']} files · "
                 f"{human_size(stats['bytes'])}" +
                 (f" · {stats['skipped']} junk dirs skipped"
                  if stats["skipped"] else "") +
                 (" · truncated" if stats["truncated"] else ""),
            fg=self.theme.get("success", "#5ad19c"))

    def _set_out(self, text):
        self.out.config(state=tk.NORMAL)
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.config(state=tk.DISABLED)

    def copy_tree(self):
        text = self.out.get("1.0", "end-1c")
        if not text.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.config(text="tree copied to clipboard ✓",
                           fg=self.theme.get("success", "#5ad19c"))

    def save_tree(self):
        text = self.out.get("1.0", "end-1c")
        if not text.strip():
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".txt",
            initialfile="directory-tree.txt",
            filetypes=[("Text", "*.txt"), ("Markdown", "*.md")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
        except OSError as exc:
            messagebox.showerror("Tree Export", str(exc), parent=self)
            return
        self.status.config(text=f"saved → {path}",
                           fg=self.theme.get("success", "#5ad19c"))


def open_treeexport(parent, theme, initial="", workspace=""):
    """Public opener — palette / menu / terminal entry point."""
    return TreeExport(parent, theme, root_path=initial,
                      workspace=workspace)
