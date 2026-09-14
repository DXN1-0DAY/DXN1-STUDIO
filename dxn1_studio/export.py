"""DXN1 STUDIO — project export.

Two export shapes:

* **Project ZIP** — the whole workspace (skipping caches/venvs) with a
  guaranteed ``requirements.txt`` for Flask projects, ready to share.
* **Standalone file** — the current editor buffer written anywhere.
"""

import os
import time
import zipfile

# directories that never belong in an export
SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules",
             ".dxn1", ".pytest_cache", ".mypy_cache", "dist", "build"}
SKIP_EXT = {".pyc", ".pyo", ".log"}


def default_zip_name(project_dir):
    name = os.path.basename(os.path.normpath(project_dir or "workspace"))
    stamp = time.strftime("%Y%m%d-%H%M")
    return f"{name}-{stamp}.zip"


def ensure_requirements(project_dir, kind):
    """Flask workspaces always ship a requirements.txt in exports."""
    req = os.path.join(project_dir, "requirements.txt")
    if kind == "flask" and not os.path.exists(req):
        try:
            with open(req, "w", encoding="utf-8") as fh:
                fh.write("flask>=3.0\n")
        except OSError:
            pass
    return req


def export_project_zip(project_dir, dest_zip):
    """Zip up a workspace. Returns (dest_zip, file_count) or raises."""
    project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(project_dir):
        raise NotADirectoryError(project_dir)

    dest_zip = os.path.abspath(dest_zip)
    parent = os.path.dirname(dest_zip)
    if parent:
        os.makedirs(parent, exist_ok=True)

    count = 0
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        root_name = os.path.basename(project_dir)
        for dirpath, dirnames, filenames in os.walk(project_dir):
            dirnames[:] = [d for d in sorted(dirnames)
                           if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, project_dir)
                arcname = os.path.join(root_name, rel)
                try:
                    zf.write(full, arcname)
                    count += 1
                except OSError:
                    continue  # unreadable file — skip, keep exporting
    return dest_zip, count


def export_file_bytes(content, dest_path):
    """Write arbitrary text content to a destination. Returns dest_path."""
    dest_path = os.path.abspath(dest_path)
    parent = os.path.dirname(dest_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return dest_path
