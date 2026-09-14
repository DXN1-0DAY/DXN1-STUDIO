<!-- DS2 pull-request template — delete sections that don't apply -->

## What does this PR do?

<!-- One or two sentences: the problem and the fix/feature. -->

## Type of change

- [ ] ✨ Feature (new capability)
- [ ] 🐛 Bug fix (no behaviour change beyond the fix)
- [ ] 🔧 Refactor (no behaviour change)
- [ ] 📚 Docs / comments
- [ ] 🎨 Theme / UI polish

## Checklist

- [ ] `python3 -m compileall -q dxn1_studio` passes locally
- [ ] `xvfb-run -a python3 dxn1-studio --smoke-test` passes (or CI does)
- [ ] New user-facing behaviour is reachable from the **Command Palette**
      (Ctrl+Shift+P) or documented in the README
- [ ] Config keys added with defensive `getattr`/default handling so old
      configs keep working
- [ ] CHANGELOG.md gets an entry (or the maintainer will add one at tag time)

## Screenshots

<!-- Drag images here if the change is visible in the UI. -->
