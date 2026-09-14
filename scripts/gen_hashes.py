#!/usr/bin/env python3
"""Regenerate HASHES.txt — sha256 of every file an update touches.

The in-place updater (and the installer's integrity gate) downloads
HASHES.txt first, then fetches only the files whose content actually
changed (or are missing). Run from anywhere after any change that
ships:

    python3 scripts/gen_hashes.py

Format is sha256sum-compatible: ``<64-hex>  <repo-relative-path>``
(sorted, UTF-8, LF). HASHES.txt itself is excluded — a file cannot
contain its own hash.
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANIFEST_NAME = "MANIFEST.txt"
HASHES_NAME = "HASHES.txt"
ENTRY_SCRIPTS = ("dxn1-studio", "dxn1", "DXN1 STUDIO", "README.md")
ASSETS = ("logo.png", "splash_bg.png", "welcome_hero.png", "hub_hero.png",
          "agents_hero.png", "update_hero.png")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_files():
    """Every repo-relative path an update should keep fresh."""
    out = []
    manifest = os.path.join(ROOT, MANIFEST_NAME)
    if not os.path.isfile(manifest):
        sys.exit("ERROR: MANIFEST.txt missing — run from the repo")
    mods = sorted(ln.strip() for ln in open(manifest, encoding="utf-8")
                  if ln.strip())
    out += [f"dxn1_studio/{m}" for m in mods]
    out += list(ENTRY_SCRIPTS)
    out += [f"assets/{a}" for a in ASSETS]
    out.append(MANIFEST_NAME)
    return out


def main():
    lines, missing = [], []
    for rel in rel_files():
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            missing.append(rel)
            continue
        lines.append(f"{sha256(path)}  {rel}")
    if missing:
        sys.exit("ERROR: missing files (fix before hashing): "
                 + ", ".join(missing))
    body = "\n".join(lines) + "\n"
    dest = os.path.join(ROOT, HASHES_NAME)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    print(f"HASHES.txt written — {len(lines)} files covered")


if __name__ == "__main__":
    main()
