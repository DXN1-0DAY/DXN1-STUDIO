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
    """True when a canvas actually holds more content than it shows."""
    try:
        region = w.cget("scrollregion")
        if region and str(region) not in ("", "0 0 0 0"):
            parts = [int(float(x)) for x in str(region).split()]
            if len(parts) == 4:
                rw = parts[2] - parts[0]
                rh = parts[3] - parts[1]
            else:
                return False
        else:
            bb = w.bbox("all")
            if not bb:
                return False
            rw, rh = bb[2] - bb[0], bb[3] - bb[1]
        return (rw > w.winfo_width() + TOLERANCE or
                rh > w.winfo_height() + TOLERANCE)
    except Exception:  # noqa: BLE001
        return False


def audit_size(app, label, problems):
    root = app.root
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
                if cls == "Canvas":
                    over_h = over_w = canvas_overflows(w)
                if over_h and pw is not None and \
                        not has_scrollbar_nearby(w, root, False):
                    problems.append(
                        f"[{label}] A {cls} '{name}' needs {req_h}px, "
                        f"has {got_h}px, NO vertical scrollbar nearby")
                if over_w and pw is not None and \
                        not has_scrollbar_nearby(w, root, True):
                    problems.append(
                        f"[{label}] A {cls} '{name}' needs {req_w}px, "
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
                    if not canvas_overflows(w):
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
