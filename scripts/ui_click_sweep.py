#!/usr/bin/env python3
"""Click EVERY button/menu item in a window subtree — dead controls
must be impossible. Usage: invoked per-dialog like ui_dialog_sweep."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def click_all(widget, root, out, depth=0):
    import tkinter as tk
    from tkinter import ttk
    try:
        children = widget.winfo_children()
    except Exception:  # noqa: BLE001 — widget destroyed mid-walk
        return
    for w in children:
        click_all(w, root, out, depth + 1)
    try:
        cls = widget.winfo_class()
    except Exception:  # noqa: BLE001 — destroyed by an earlier click
        return
    name = str(widget).replace(str(root), "", 1) or root
    try:
        if cls == "TButton" or cls == "TLabel":
            cmd = None
        elif isinstance(widget, tk.Button):
            cmd = widget.cget("command")
            if callable(cmd):
                cmd()
                out.append(("click", name))
            elif cmd in ("", None):
                out.append(("noop", name))
        elif isinstance(widget, ttk.Button):
            cmd = str(widget.cget("command"))
            out.append(("ttk-skip", name))
        elif isinstance(widget, tk.Label):
            if str(widget.cget("cursor")) == "hand2":
                binds = widget.bind()
                clicked = False
                for b in binds:
                    if "Button-1" in str(b):
                        widget.event_generate("<Button-1>")
                        clicked = True
                out.append(("label-click" if clicked else "dead-label",
                            name))
        elif isinstance(widget, tk.Checkbutton):
            try:  # invoke flips the state and runs the command
                widget.invoke()
                out.append(("check", name))
            except Exception as e:  # noqa: BLE001
                out.append(("RAISED", name,
                            "%s: %s" % (type(e).__name__, e)))
        elif isinstance(widget, tk.Radiobutton):
            pass  # selecting every radio mutates shared vars; skip
    except Exception as e:  # noqa: BLE001
        out.append(("RAISED", name, "%s: %s" % (type(e).__name__, e)))


def main():
    idx = int(sys.argv[1])
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
    from dxn1_studio.app import DXN1Studio
    from dxn1_studio.config import Config

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
        print(f"{idx}|{label}|OPEN-RAISED|{type(e).__name__}")
        app.root.destroy()
        return
    for _ in range(3):
        root.update_idletasks(); root.update()
    import time
    time.sleep(0.08)
    for _ in range(2):
        root.update_idletasks(); root.update()
    new = [w for w in toplevels() if str(w) not in before]
    raised = 0
    dead = 0
    clicked = 0
    for w in new:
        out = []
        click_all(w, w, out)
        for item in out:
            kind = item[0]
            if kind == "RAISED":
                raised += 1
                print(f"{idx}|{label}|RAISED|{item[1]}|{item[2]}",
                      file=sys.stderr)
            elif kind in ("noop", "dead-label"):
                dead += 1
            elif kind in ("click", "label-click", "check"):
                clicked += 1
    print(f"{idx}|{label}|clicked={clicked}|dead={dead}|raised={raised}")
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
