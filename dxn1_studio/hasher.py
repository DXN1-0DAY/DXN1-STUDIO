"""DS2 Hasher — checksums, integrity manifests and quick verification.

Chunked hashing (never loads a whole file), recursive folder manifests
in `sha256sum -c`-compatible format, paste-a-hash verification, and a
results grid you can copy. Engine is pure and unit-tested.

Open with: palette, Workshop menu, terminal ``hash <file>`` / ``hash``.
"""

import hashlib
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

__all__ = [
    "ALGOS", "hash_file", "hash_bytes", "hash_dir", "manifest_line",
    "verify_line", "HasherWindow", "open_hasher",
]

ALGOS = ("md5", "sha1", "sha256", "sha512")
CHUNK = 1 << 20          # 1 MiB chunks
DIR_CAP = 5000           # files per manifest walk


def hash_bytes(data, algo="sha256"):
    """Digest of a bytes object (lowercase hex). Raises on bad algo."""
    return hashlib.new(algo, data).hexdigest()


def hash_file(path, algo="sha256", _progress=None):
    """Chunked file digest → (hexdigest, size_bytes). Raises OSError /
    ValueError(bad algo)."""
    h = hashlib.new(algo)
    size = 0
    with open(path, "rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h.update(block)
            size += len(block)
            if _progress:
                _progress(size)
    return h.hexdigest(), size


def hash_dir(root, algo="sha256", skip_hidden=True, cap=DIR_CAP):
    """Recursive manifest → list of (algo, digest, size, relpath).

    Rows sorted by relpath; symlinks to dirs not followed; files that
    fail to read are skipped silently. Never raises.
    """
    root = os.path.abspath(root)
    out = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        if skip_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        dirnames.sort()
        for name in sorted(filenames):
            if skip_hidden and name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            try:
                digest, size = hash_file(full, algo)
            except OSError:
                continue
            out.append((algo, digest, size, rel))
            if len(out) >= cap:
                return out
    return out


def manifest_line(algo, digest, _size, relpath):
    """`<digest>  <relpath>` — sha256sum -c compatible (two spaces)."""
    return f"{digest}  {relpath}"


def verify_line(line):
    """Parse one manifest line → (digest, path, error).

    Success: (hexdigest, path, ""); failure: (None, "", reason).
    Accepts the canonical two-space form (and ` *` binary marker),
    ignores blank lines and # comments.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None, "", ""
    for sep in ("  ", " *", " "):
        if sep in line:
            digest, _, path = line.partition(sep)
            digest = digest.strip().lower()
            path = path.strip()
            if digest and path and len(digest) >= 8:
                return digest, path, ""
            return None, "", "malformed line"
    return None, "", "malformed line"


class HasherWindow(tk.Toplevel):
    """Checksum lab: file/folder hashing + paste-hash verification."""

    def __init__(self, parent, theme, initial="", workspace=""):
        super().__init__(parent)
        self.theme = theme or {}
        self.workspace = workspace
        self.target = tk.StringVar(
            value=initial or workspace or os.path.expanduser("~"))
        self.algo = tk.StringVar(value="sha256")

        t = self.theme
        self.title("Hasher — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("860x560")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 860x560 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 860, 560))
        self.minsize(640, 420)
        try:
            self.transient(parent)
        except Exception:
            pass

        self._build_toolbar()
        self._build_body()
        self._build_statusbar()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<F5>", lambda _e: self.run_hash())

    # ------------------------------------------------------------ UI
    def _build_toolbar(self):
        t = self.theme
        bar = tk.Frame(self, bg=t.get("header", "#242432"))
        bar.pack(fill=tk.X)
        tk.Label(bar, text="target", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(
            side=tk.LEFT, padx=(10, 4), pady=6)
        tk.Entry(bar, textvariable=self.target, width=40, relief="flat",
                 bg=t.get("editor", "#1b1b24"),
                 fg=t.get("text", "#e8e8f0"),
                 insertbackground=t.get("text", "#e8e8f0")).pack(
            side=tk.LEFT, padx=2)

        def _btn(text, cmd):
            return tk.Button(
                bar, text=text, command=cmd, relief="flat", bd=0,
                bg=t.get("hover", "#2c2c3e"), fg=t.get("text", "#e8e8f0"),
                activebackground=t.get("border", "#3a3a4e"),
                activeforeground=t.get("text", "#e8e8f0"),
                padx=10, pady=2, cursor="hand2")

        _btn("File…", self.pick_file).pack(side=tk.LEFT, padx=3)
        _btn("Folder…", self.pick_folder).pack(side=tk.LEFT, padx=3)
        _btn("Hash (F5)", self.run_hash).pack(side=tk.LEFT, padx=8)
        for a in ALGOS:
            tk.Radiobutton(
                bar, text=a, value=a, variable=self.algo,
                command=self.run_hash,
                bg=t.get("header", "#242432"),
                fg=t.get("text_muted", "#8a8a9a"),
                activebackground=t.get("header", "#242432"),
                activeforeground=t.get("text", "#e8e8f0"),
                selectcolor=t.get("editor", "#1b1b24")).pack(
                side=tk.RIGHT, padx=3)

    def _build_body(self):
        t = self.theme
        panes = tk.Frame(self, bg=t.get("bg", "#16161e"))
        panes.pack(fill=tk.BOTH, expand=True)

        # results grid
        left = tk.Frame(panes, bg=t.get("bg", "#16161e"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4),
                  pady=6)
        self.grid = ttk.Treeview(left, show="headings", height=16)
        self.grid["columns"] = ("digest", "size", "path")
        for col, w, anch in (("digest", 300, "w"), ("size", 70, "e"),
                             ("path", 320, "w")):
            self.grid.heading(col, text=col)
            self.grid.column(col, width=w, anchor=anch)
        from .theme import make_scrollbar
        _gsb = make_scrollbar(left, t, "vertical", command=self.grid.yview)
        self.grid.configure(yscrollcommand=_gsb.set)
        _gsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.grid.pack(fill=tk.BOTH, expand=True)
        gbar = tk.Frame(left, bg=t.get("bg", "#16161e"))
        gbar.pack(fill=tk.X)
        self._btn2(gbar, "Copy manifest", self.copy_manifest).pack(
            side=tk.LEFT, padx=2, pady=4)
        self._btn2(gbar, "Save manifest…", self.save_manifest).pack(
            side=tk.LEFT, padx=2)
        self._btn2(gbar, "Copy selected digest", self.copy_digest).pack(
            side=tk.LEFT, padx=2)

        # verify panel
        right = tk.Frame(panes, bg=t.get("bg", "#16161e"))
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 8), pady=6)
        tk.Label(right, text="VERIFY A HASH", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
        tk.Label(right, text="paste an expected digest:", wraplength=180,
                 justify="left", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.expect = tk.Text(right, height=3, width=24, wrap="char",
                              relief="flat",
                              bg=t.get("editor", "#1b1b24"),
                              fg=t.get("text", "#e8e8f0"),
                              insertbackground=t.get("text", "#e8e8f0"))
        _esb = make_scrollbar(right, t, "vertical",
                              command=self.expect.yview)
        self.expect.configure(yscrollcommand=_esb.set)
        _esb.pack(side=tk.RIGHT, fill=tk.Y)
        self.expect.pack(fill=tk.X, pady=4)
        self._btn2(right, "Verify first row", self.verify_first).pack(
            anchor="w", pady=2)
        self._btn2(right, "Verify ALL rows", self.verify_all).pack(
            anchor="w", pady=2)
        self.verdict = tk.Label(right, text="—", wraplength=190,
                                justify="left",
                                bg=t.get("bg", "#16161e"),
                                fg=t.get("text_muted", "#8a8a9a"),
                                font=("TkDefaultFont", 10, "bold"))
        self.verdict.pack(anchor="w", pady=(8, 0))

    def _build_statusbar(self):
        t = self.theme
        self.status = tk.Label(
            self, text="pick a file or folder, choose an algo, press F5",
            anchor="w", bg=t.get("header", "#242432"),
            fg=t.get("text_muted", "#8a8a9a"), padx=10, pady=3)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _btn2(self, parent, text, cmd):
        t = self.theme
        return tk.Button(
            parent, text=text, command=cmd, relief="flat", bd=0,
            bg=t.get("hover", "#2c2c3e"), fg=t.get("text", "#e8e8f0"),
            activebackground=t.get("border", "#3a3a4e"),
            activeforeground=t.get("text", "#e8e8f0"),
            padx=8, pady=2, cursor="hand2")

    # -------------------------------------------------------- actions
    def pick_file(self):
        path = filedialog.askopenfilename(parent=self,
                                          title="Hash a file")
        if path:
            self.target.set(path)
            self.run_hash()

    def pick_folder(self):
        path = filedialog.askdirectory(parent=self,
                                       title="Hash a folder")
        if path:
            self.target.set(path)
            self.run_hash()

    def run_hash(self):
        target = self.target.get().strip()
        algo = self.algo.get()
        if not target:
            self._status("pick a target first", error=True)
            return
        t0 = time.perf_counter()
        rows = []
        try:
            if os.path.isfile(target):
                digest, size = hash_file(target, algo)
                rows.append((algo, digest, size,
                             os.path.basename(target)))
            elif os.path.isdir(target):
                rows = [(a, d, s, r) for (a, d, s, r)
                        in hash_dir(target, algo)]
            else:
                self._status(f"no such file or folder: {target}",
                             error=True)
                return
        except (OSError, ValueError) as exc:
            self._status(f"hash failed: {exc}", error=True)
            return
        ms = (time.perf_counter() - t0) * 1000.0
        self.grid.delete(*self.grid.get_children())
        for a, digest, size, rel in rows:
            self.grid.insert("", "end", values=(digest,
                                                human_size(size), rel))
        self._set_rows(rows)
        self._status(f"{len(rows)} item(s) hashed in {ms:.0f} ms "
                     f"({algo})", ok=True)

    def _set_rows(self, rows):
        self._rows = rows

    def copy_digest(self):
        sel = self.grid.selection()
        if not sel:
            self._status("select a row first", error=True)
            return
        digest = self.grid.set(sel[0], "digest")
        self.clipboard_clear()
        self.clipboard_append(digest)
        self._status("digest copied ✓", ok=True)

    def copy_manifest(self):
        rows = getattr(self, "_rows", [])
        if not rows:
            self._status("hash something first", error=True)
            return
        text = "\n".join(manifest_line(*r) for r in rows)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status(f"manifest copied ({len(rows)} lines) ✓", ok=True)

    def save_manifest(self):
        rows = getattr(self, "_rows", [])
        if not rows:
            self._status("hash something first", error=True)
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".txt",
            initialfile=f"{self.algo.get()}sums.txt",
            filetypes=[("Checksums", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(manifest_line(*r) for r in rows)
                         + "\n")
        except OSError as exc:
            messagebox.showerror("Hasher", str(exc), parent=self)
            return
        self._status(f"manifest saved → {path}", ok=True)

    def _expected(self):
        text = self.expect.get("1.0", "end-1c").strip().lower()
        return text.split()[0] if text else ""

    def verify_first(self):
        rows = getattr(self, "_rows", [])
        if not rows:
            self._status("hash something first", error=True)
            return
        expected = self._expected()
        if not expected:
            self._set_verdict("paste a digest first", error=True)
            return
        digest, _size, rel = rows[0][1], rows[0][2], rows[0][3]
        if digest.lower() == expected:
            self._set_verdict(f"MATCH — {rel} is intact ✓", ok=True)
        else:
            self._set_verdict(f"MISMATCH — {rel} differs!", error=True)

    def verify_all(self):
        rows = getattr(self, "_rows", [])
        text = self.expect.get("1.0", "end-1c")
        if not rows or not text.strip():
            self._set_verdict("hash + paste a manifest first",
                              error=True)
            return
        expected = {}
        for line in text.splitlines():
            digest, path, _err = verify_line(line)
            if digest and path:
                expected[path] = digest
        if not expected:
            self._set_verdict("no parsable manifest lines", error=True)
            return
        ok = bad = missing = 0
        for _a, digest, _s, rel in rows:
            want = expected.get(rel)
            if want is None:
                missing += 1
            elif want == digest.lower():
                ok += 1
            else:
                bad += 1
        parts = [f"{ok} ok"]
        if bad:
            parts.append(f"{bad} MISMATCH")
        if missing:
            parts.append(f"{missing} not in pasted manifest")
        self._set_verdict(" · ".join(parts), ok=bad == 0)

    def _set_verdict(self, text, ok=False, error=False):
        t = self.theme
        self.verdict.config(
            text=text,
            fg=t.get("success", "#5ad19c") if ok else
            (t.get("error", "#ff7a7a") if error else
             t.get("text_muted", "#8a8a9a")))

    def _status(self, text, ok=False, error=False):
        t = self.theme
        self.status.config(
            text=text,
            fg=t.get("success", "#5ad19c") if ok else
            (t.get("error", "#ff7a7a") if error else
             t.get("text_muted", "#8a8a9a")))


def human_size(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{int(n)} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def open_hasher(parent, theme, initial="", workspace=""):
    """Public opener — palette / menu / terminal entry point."""
    return HasherWindow(parent, theme, initial=initial,
                        workspace=workspace)
