#!/usr/bin/env python3
"""One palette command -> audit the Toplevel(s) it opens -> exit.

Usage: python3 scripts/ui_dialog_sweep.py <index>
Prints: INDEX|TITLE|issues (pipe-joined) or INDEX|OK|0
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_fit_audit import audit_size  # noqa: E402


def main():
    idx = int(sys.argv[1])
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
    from dxn1_studio.app import DXN1Studio
    from dxn1_studio.config import Config

    # stub every modal so nothing blocks
    for mod in (filedialog, simpledialog):
        for attr in dir(mod):
            if attr.startswith("ask"):
                setattr(mod, attr, lambda *a, **k: None)
    for attr in dir(messagebox):
        if attr.startswith(("show", "ask")):
            setattr(messagebox, attr, lambda *a, **k: None)

    app = DXN1Studio(Config(), smoke_test=True, no_splash=True)
    root = app.root
    root.geometry("1280x820")
    root.update_idletasks(); root.update()

    cmds = app.palette_commands()
    label, _key, fn = cmds[idx]

    def toplevels():
        return [w for w in root.winfo_children()
                if isinstance(w, tk.Toplevel)]

    before = {str(w) for w in toplevels()}
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        print(f"{idx}|REFUSED|{type(e).__name__}")
        try:
            app.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        return
    for _ in range(3):
        root.update_idletasks(); root.update()
    import time
    time.sleep(0.08)
    for _ in range(2):
        root.update_idletasks(); root.update()
    new = [w for w in toplevels() if str(w) not in before]
    total = 0
    parts = []
    hint_missing = []
    esc_missing = []

    def has_bar(w):
        # a hint bar is any widget carrying the honesty attributes
        if hasattr(w, "filled"):
            return bool(w.filled)
        try:
            return any(has_bar(c) for c in w.winfo_children())
        except Exception:  # noqa: BLE001
            return False

    for w in new:
        try:
            title = w.title() or "untitled"
        except Exception:  # noqa: BLE001
            title = "untitled"
        # hint-bar + Esc coverage (the door-sign contract)
        if not has_bar(w):
            hint_missing.append(title)
        # Tk accepts several spellings (<Escape>, <Key-Escape>) — any
        # sequence containing Escape means the contract is kept
        if not any("Escape" in b for b in w.bind()):
            esc_missing.append(title)
        probs = []
        try:
            w.update_idletasks()
            audit_size(app, f"dialog[{title}]", probs, root=w)
        except Exception as e:  # noqa: BLE001
            probs.append(f"[dialog[{title}]] ? {type(e).__name__}: {e}")
        total += len(probs)
        parts.append(f"{title}:{len(probs)}")
        for p in probs:
            print(f"{idx}|{title}|{p}", file=sys.stderr)
    print(f"{idx}|{label}|{len(new)} windows|{total} issues|"
          f"{'|'.join(parts) if parts else 'no-window'}|"
          f"hint-missing={';'.join(hint_missing) or '-'}|"
          f"esc-missing={';'.join(esc_missing) or '-'}")
    for w in new:
        try:
            w.destroy()
        except Exception:  # noqa: BLE001
            pass
    try:
        app.root.destroy()
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
