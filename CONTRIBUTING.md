# Contributing to DXN1 STUDIO

First off — thanks for wanting to make the studio better. Contributions are
welcome from everyone, whether it's a one-line typo fix or a whole new panel.
This project is a from-scratch, zero-framework Tkinter IDE, so the barriers
to entry are refreshingly low: if you can read Python, you can hack on it.

## The ground rules

- **Standard library first.** Every feature must work with Python 3.8+ and
  Tkinter alone. `Pillow` is the only soft dependency and it must degrade
  gracefully when missing. Network calls go through `urllib` — no SDKs, no
  helper processes, no Node.
- **Sandbox stays sacred.** Anything touching `sandbox.py` needs extra care:
  the agent jail must never leak paths outside the active workspace, and
  catastrophic commands must always require explicit human Accept — even in
  full-access mode. If your PR weakens this, it will be rejected.
- **Lightweight by default.** Heavy stuff (Flask, NumPy, …) belongs in the
  opt-in Packages view, never in the core.
- **Match the vibe.** Flat, minimal, theme-aware UI. No hardcoded colours —
  pull from `theme.py` so dark and light both look right.

## Getting set up

```bash
git clone https://github.com/DXN1-termux/DXN1-STUDIO.git
cd DXN1-STUDIO
python3 dxn1-studio --smoke-test     # headless self-check
python3 dxn1-studio                  # or the real thing
```

Run the headless smoke test before every push — CI does the same on
Python 3.10 and 3.12 with Xvfb.

## Pull requests

1. Fork → branch off `master` (`feat/…`, `fix/…`).
2. Keep diffs focused; one feature or fix per PR.
3. Test on both dark and light themes.
4. Describe *what* and *why* — screenshots welcome for UI changes.

## Reporting bugs

Open an issue with the bug template: Python/Tk versions (`python3 -c "import tkinter; print(tkinter.TkVersion)"`), OS, steps to reproduce, and the log
at `~/.dxn1-studio/logs/studio.log` if one exists.

## Feature ideas

Check the roadmap in the README and open a feature-request issue first for
anything big, so we can align on the standard-library-only constraint before
you write a thousand lines.
