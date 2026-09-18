#!/usr/bin/env python3
"""DS3 probe: the release ledger speaks — scripts/release_notes.py
extracts a real historical tag's CHANGELOG section (v3.1.114), refuses
to invent notes for a tag that never existed (exit 1, no fabrication),
and the CHANGELOG itself is an honest ledger of the version line.
Pure-python pins, no engine — the fastest walker in gate 8's yard."""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = os.path.join(REPO, "scripts", "release_notes.py")
CHANGELOG = os.path.join(REPO, "CHANGELOG.md")

pins = []
t0 = __import__("time").time()


def pin(name, ok, detail=""):
    pins.append((name, bool(ok)))
    print(f"  {'ok ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail and not ok else ""))


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=30, cwd=REPO)


# pin 1 — a real historical tag yields its changelog section, exit 0
r = run("python3", NOTES, "v3.1.114")
pin("release_notes v3.1.114 exits 0", r.returncode == 0)
pin("v3.1.114's section is non-empty markdown", r.returncode == 0 and
    r.stdout.strip().startswith("## v3.1.114"), r.stdout[:120])

# pin 2 — a tag that never existed is refused, never invented
r2 = run("python3", NOTES, "v0.0.0-no-such-tag")
pin("the nonexistent tag is refused (exit 1)", r2.returncode == 1)
pin("the refusal fabricates nothing", r2.stdout.strip() == "", r2.stdout[:120])

# pin 3 — the changelog ledger holds the version line
try:
    text = open(CHANGELOG, encoding="utf-8").read()
    sections = re.findall(r"^##\s+(v[\d.]+)", text, re.M)
    ok = len(sections) >= 20
except OSError:
    sections, ok = [], False
pin("the changelog wears 20+ version sections", ok, f"{len(sections)} found")

# pin 4 — usage without args is a doc, not a crash
r4 = run("python3", NOTES)
pin("bare invocation prints usage (exit 2)", r4.returncode == 2 and "Usage" in r4.stdout)

fails = [n for n, okk in pins if not okk]
print(f"\nrelease_notes_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {__import__('time').time()-t0:.1f}s")
sys.exit(1 if fails else 0)
