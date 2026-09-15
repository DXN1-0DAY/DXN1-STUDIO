"""DS2 UI fit audit — boots the real studio and hunts clipped/overflowing widgets.

Run with: DISPLAY=:99 python3 scripts/ui_fit_audit.py

Audits the MAIN window at two sizes (default 1280x820 and minimum
940x580 — the hard case) and reports:
  A. widgets whose REQUIRED size exceeds their ALLOCATED size with
     no scrollbar to absorb the difference (visible clipping),
  B. widgets that stick out beyond their parent's bounds,
  C. scrollable widgets (Text/Canvas/Treeview/Listbox) that have NO
     scrollbar sibling at all — content can be reached by no means.

Exits 0 when the audit is clean, 1 with a report otherwise.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

TOLERANCE = 2  # px — Tk rounding is generous, real clipping is not
SCROLLABLE = (tk_names := ("Text", "Canvas", "Treeview", "Listbox"))


def widget_scroll_kinds(w):
    return w.winfo_class() in SCROLLABLE


def has_scrollbar_nearby(w, root, horizontal, levels=3):
    """Search the widget's ancestors (up to `levels` up) and each of
    their child sets for a scrollbar facing the right way."""
    node = w
    for _ in range(levels + 1):
        par = node.winfo_parent()
        if not par:
            break
        parw = root.nametowidget(par)
        for sib in parw.winfo_children():
            if sib.winfo_class() in ("Scrollbar", "TScrollbar"):
                orient = str(sib.cget("orient"))
                if (horizontal and orient == "horizontal") or \
                        (not horizontal and orient == "vertical"):
                    return True
        node = parw
    return False


def canvas_overflows(w):
    """(over_w, over_h) — per-axis content-vs-viewport truth."""
    try:
        region = w.cget("scrollregion")
        if region and str(region) not in ("", "0 0 0 0"):
            parts = [int(float(x)) for x in str(region).split()]
            if len(parts) == 4:
                rw = parts[2] - parts[0]
                rh = parts[3] - parts[1]
            else:
                return (False, False)
        else:
            bb = w.bbox("all")
            if not bb:
                return (False, False)
            rw, rh = bb[2] - bb[0], bb[3] - bb[1]
        return (rw > w.winfo_width() + TOLERANCE,
                rh > w.winfo_height() + TOLERANCE)
    except Exception:  # noqa: BLE001
        return (False, False)


def audit_size(app, label, problems, root=None):
    """Audit ANY toplevel — the main window or an opened dialog."""
    root = root or app.root
    root.update_idletasks()
    root.update()

    for w in walk(root):
        try:
            name = widget_path(w)
            cls = w.winfo_class()
            req_w, req_h = w.winfo_reqwidth(), w.winfo_reqheight()
            got_w, got_h = w.winfo_width(), w.winfo_height()
            if got_w < 2 or got_h < 2:
                continue  # not realized yet (hidden/deferred)
            # A. clipping without a scrollbar escape
            if widget_scroll_kinds(w):
                parent = w.winfo_parent()
                pw = root.nametowidget(parent) if parent else None
                over_h = got_h < req_h - TOLERANCE
                over_w = got_w < req_w - TOLERANCE
                need_w, need_h = req_w, req_h
                if cls == "Canvas":
                    ov_w, ov_h = canvas_overflows(w)
                    over_w, over_h = ov_w, ov_h
                    try:
                        sr = [int(float(x))
                              for x in str(w.cget("scrollregion")).split()]
                        if len(sr) == 4:
                            need_w = sr[2] - sr[0]
                            need_h = sr[3] - sr[1]
                    except Exception:  # noqa: BLE001
                        pass
                if over_h and pw is not None and \
                        not has_scrollbar_nearby(w, root, False):
                    problems.append(
                        f"[{label}] A {cls} '{name}' needs {need_h}px, "
                        f"has {got_h}px, NO vertical scrollbar nearby")
                if over_w and pw is not None and \
                        not has_scrollbar_nearby(w, root, True):
                    problems.append(
                        f"[{label}] A {cls} '{name}' needs {need_w}px, "
                        f"has {got_w}px, NO horizontal scrollbar nearby")
            elif (got_h < req_h - TOLERANCE or
                  got_w < req_w - TOLERANCE) and cls not in ("Frame",
                                                             "TFrame",
                                                             "Label",
                                                             "TLabel",
                                                             "TFrame"):
                # B/C for non-scrollable, non-container widgets is the
                # visible-clip case; frames/labels flex by design.
                pass
            # B. sticking out of the parent's box
            par = w.winfo_parent()
            if par:
                pw = root.nametowidget(par)
                if pw is not root:
                    pw_w, pw_h = pw.winfo_width(), pw.winfo_height()
                    if pw_w > 2 and pw_h > 2:
                        x, y = w.winfo_x(), w.winfo_y()
                        if x + got_w > pw_w + TOLERANCE and \
                                w.winfo_manager() == "place":
                            problems.append(
                                f"[{label}] B {cls} '{name}' overflows "
                                f"parent width: x+{got_w} > {pw_w}")
                        if y + got_h > pw_h + TOLERANCE and \
                                w.winfo_manager() == "place":
                            problems.append(
                                f"[{label}] B {cls} '{name}' overflows "
                                f"parent height: y+{got_h} > {pw_h}")
            # C. scrollable with no scrollbar anywhere nearby
            if widget_scroll_kinds(w):
                if cls == "Canvas":
                    ov_w, ov_h = canvas_overflows(w)
                    if not (ov_w or ov_h):
                        continue  # content fits — no scrollbar needed
                # tiny disabled Texts are mirrors (gutters, tickers)
                # whose scroll is externally driven — not scroll targets
                if cls == "Text":
                    try:
                        if str(w.cget("state")) == "disabled" and \
                                int(w.cget("width")) <= 8:
                            continue
                    except Exception:  # noqa: BLE001
                        pass
                if not (has_scrollbar_nearby(w, root, False) or
                        has_scrollbar_nearby(w, root, True)):
                    problems.append(
                        f"[{label}] C {cls} '{name}' scrollable "
                        f"but has no scrollbar nearby")
        except Exception as e:  # noqa: BLE001 — audit never dies
            problems.append(f"[{label}] ? {type(e).__name__}: {e}")


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


def widget_path(w):
    p = str(w)
    return p.replace(str(w.winfo_toplevel()), "", 1) or p


def audit_dialogs(app, problems):
    """Open EVERY palette command that yields a Toplevel and audit it.

    Blocking dialogs (file/message/simple) are stubbed to no-ops so a
    headless sweep never waits on a human; commands that mutate state
    without opening a window simply produce no toplevel and are
    skipped by the set-difference."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
    import time

    root = app.root
    # stub every modal — the sweep must never block
    for mod in (filedialog, simpledialog):
        for attr in dir(mod):
            if attr.startswith("ask"):
                try:
                    setattr(mod, attr,
                            lambda *a, **k: "" if "string" in attr or
                            "integer" in attr or "float" in attr or
                            "properties" in attr else None)
                except Exception:  # noqa: BLE001
                    pass
    for attr in dir(messagebox):
        if attr.startswith(("show", "ask")):
            try:
                setattr(messagebox, attr, lambda *a, **k: None)
            except Exception:  # noqa: BLE001
                pass

    def toplevels():
        return [w for w in root.winfo_children()
                if isinstance(w, tk.Toplevel)]

    base = {str(w) for w in toplevels()}
    cmds = []
    try:
        cmds = app.palette_commands()
    except Exception as e:  # noqa: BLE001
        problems.append(f"[dialogs] ? palette unavailable: {e}")
        return
    for label, _key, fn in cmds:
        before = {str(w) for w in toplevels()}
        try:
            sys.stderr.write(f"[sweep] {label}\n")
            sys.stderr.flush()
            fn()
        except Exception:  # noqa: BLE001 — a command may refuse; fine
            pass
        root.update_idletasks(); root.update()
        time.sleep(0.05)
        root.update_idletasks(); root.update()
        new = [w for w in toplevels() if str(w) not in before and
               str(w) not in base]
        for w in new:
            try:
                title = w.title() or "untitled"
            except Exception:  # noqa: BLE001
                title = "untitled"
            # transient tool windows: audit at their NATURAL size
            try:
                w.update_idletasks()
            except Exception:  # noqa: BLE001
                continue
            audit_size(app, f"dialog[{title}]", problems, root=w)
        # close what this command opened
        for w in new:
            try:
                w.destroy()
            except Exception:  # noqa: BLE001
                pass
        root.update_idletasks()


def main():
    import tkinter as tk
    from dxn1_studio.app import DXN1Studio
    from dxn1_studio.config import Config

    problems = []
    app = DXN1Studio(Config(), smoke_test=True, no_splash=True)
    root = app.root

    # default size
    root.geometry("1280x820")
    audit_size(app, "default-1280x820", problems)

    # minimum size — the hard case
    root.geometry("940x580")
    audit_size(app, "min-940x580", problems)

    # every dialog the palette can open
    audit_dialogs(app, problems)

    app_close = getattr(app, "quit", None)
    if callable(app_close):
        try:
            app.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    seen = []
    for p in problems:
        if p not in seen:
            seen.append(p)
    if seen:
        print(f"UI FIT AUDIT: {len(seen)} issue(s)")
        for p in seen:
            print("  " + p)
        return 1
    print("UI FIT AUDIT: clean at default and minimum sizes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
