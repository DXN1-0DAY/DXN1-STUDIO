#!/usr/bin/env python3
"""release notes for a tag — the honest-words chain.

The contract (pinned by probes/release_notes_probe.py, gate 8):
  - bare invocation          -> "Usage: ..." on stdout, exit 2 (a doc, not a crash)
  - a tag that never existed -> exit 1, stdout EMPTY (notes are never invented)
  - a real tag               -> exit 0, notes on stdout, by priority:
       1. the tag's own section in CHANGELOG.md (`## vX.Y.Z ...` until the
          next `## ` heading) — trimmed of trailing blanks;
       2. the annotated tag's message;
       3. the tagged commit's subject line, framed under the tag's name.

Usage: release_notes.py vX.Y.Z   (prints markdown to stdout)
"""
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def tag_exists(tag: str) -> bool:
    r = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}"],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def changelog_section(tag: str) -> str:
    try:
        lines = open("CHANGELOG.md", encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        return ""
    out, hot = [], False
    for ln in lines:
        if ln.startswith("## "):
            head = ln.split()[1] if len(ln.split()) > 1 else ""
            if hot:
                break
            hot = head == tag
            if hot:
                out.append(ln)
        elif hot:
            out.append(ln)
    return "\n".join(out).strip()


def tag_message(tag: str) -> str:
    return git("tag", "-l", "--format=%(contents)", tag).strip()


def commit_subject(tag: str) -> str:
    sha = git("rev-list", "-1", tag).strip()
    return git("log", "-1", "--format=%s", sha).strip() if sha else ""


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: release_notes.py vX.Y.Z")
        print("  prints the tag's release notes: its CHANGELOG section,")
        print("  else the tag's message, else the commit's subject.")
        return 2
    arg = sys.argv[1]
    tag = arg if arg.startswith("v") else "v" + arg
    if not tag_exists(tag):
        print(f"release_notes: no such tag: {tag}", file=sys.stderr)
        return 1
    notes = changelog_section(tag) or tag_message(tag)
    if notes:
        print(notes)
        return 0
    subject = commit_subject(tag)
    print(f"DXN1 STUDIO {tag}\n")
    print(subject if subject else tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
