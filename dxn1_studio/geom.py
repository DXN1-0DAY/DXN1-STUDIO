"""DS2 Window Geometry — remembers size & position per screen shape.

Dock the laptop at a 4K monitor, arrange the studio, undock tomorrow
on the 1080p panel: each screen shape gets its own remembered
geometry, and every restore is clamped so the window can never open
off-screen or bigger than the display.

Engine is pure (parse/make/clamp/store) and unit-tested; the app.py
integration is two defensive patches — save on close, restore on
boot. Uses the app config store, no extra files.
"""

import re

__all__ = ["parse_geometry", "make_geometry", "screen_signature",
           "clamp_geometry", "remember", "recall",
           "remember_root", "restore_root", "fit_to_content"]

GEOMETRY_KEY = "window_geometry_by_screen"
_GEOM_RE = re.compile(
    r"^(\d+)x(\d+)(?:([+-]\d+)([+-]\d+))?$")


def parse_geometry(text):
    """``1280x820+40+30`` → (w, h, x, y) ints; offset-less forms get
    0,0; junk → None (never raises)."""
    if not isinstance(text, str):
        return None
    m = _GEOM_RE.match(text.strip())
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    x = int(m.group(3)) if m.group(3) is not None else 0
    y = int(m.group(4)) if m.group(4) is not None else 0
    return (w, h, x, y)


def make_geometry(w, h, x=0, y=0):
    """Inverse of parse_geometry (ints coerced)."""
    return "%dx%d%+d%+d" % (int(w), int(h), int(x), int(y))


def screen_signature(sw, sh):
    """A stable key for a screen shape: ``1280x1024``."""
    return "%dx%d" % (int(sw), int(sh))


def clamp_geometry(w, h, x, y, sw, sh, min_w=200, min_h=150):
    """Keep the window on-screen and display-sized.

    - w/h are capped to the screen and floored to the minimums
    - x/y are pulled back inside the display (a window dragged onto
      a since-disconnected monitor re-enters at the left/top edge)
    """
    w = max(int(min_w), min(int(w), int(sw)))
    h = max(int(min_h), min(int(h), int(sh)))
    x = max(0, min(int(x), int(sw) - int(min_w)))
    y = max(0, min(int(y), int(sh) - int(min_h)))
    return (w, h, x, y)


def remember(config, geometry, sw, sh, cap=8):
    """Store one geometry under its screen signature (LRU cap)."""
    parsed = parse_geometry(geometry)
    if not parsed or not hasattr(config, "set"):
        return False
    store = dict(config.get(GEOMETRY_KEY) or {})
    sig = screen_signature(sw, sh)
    store.pop(sig, None)
    store[sig] = make_geometry(*parsed)
    while len(store) > cap:                  # drop oldest shapes
        oldest = next(iter(store))
        store.pop(oldest, None)
    config.set(GEOMETRY_KEY, store)
    return True


def recall(config, sw, sh, min_w=200, min_h=150):
    """A clamped geometry string for this screen, or '' when none."""
    if not hasattr(config, "get"):
        return ""
    raw = (config.get(GEOMETRY_KEY) or {}).get(
        screen_signature(sw, sh), "")
    parsed = parse_geometry(raw)
    if not parsed:
        return ""
    w, h, x, y = clamp_geometry(*parsed, int(sw), int(sh),
                                min_w=min_w, min_h=min_h)
    return make_geometry(w, h, x, y)


def remember_root(root, config):
    """Snapshot the current Tk root geometry (defensive, no-ops on
    maximized/fullscreen — those are window-manager states)."""
    try:
        if root.state() in ("zoomed", "fullscreen"):
            return False
    except Exception:  # noqa: BLE001
        pass
    try:
        root.update_idletasks()
        return remember(config, root.geometry(),
                        root.winfo_screenwidth(),
                        root.winfo_screenheight())
    except Exception:  # noqa: BLE001 — saving must never block exit
        return False


def restore_root(root, config, min_w=940, min_h=580):
    """Apply the remembered geometry for this screen (clamped).

    Returns the applied string, or '' when nothing was stored.
    """
    try:
        geom = recall(config, root.winfo_screenwidth(),
                      root.winfo_screenheight(), min_w=min_w,
                      min_h=min_h)
        if geom:
            root.geometry(geom)
            return geom
    except Exception:  # noqa: BLE001 — boot must never die here
        pass
    return ""


def fit_to_content(win, min_w, min_h=None, ratchet=False):
    """DS2 v2.61 — the v2.55 width pattern, one helper for every
    window: after building, a window opens no narrower (or shorter)
    than what it actually packed. ``min_w`` / ``min_h`` are the
    designed defaults (the old fixed geometry becomes the floor);
    the real request wins when it is bigger, so long rows, long
    translated headers and full hint bars never clip at the right
    edge. With ``ratchet=True`` the window also records its
    high-water mark (``win._fit_size``) and never shrinks back —
    for windows that re-measure on every refresh, where a manual
    resize must never be fought. Call it at the END of the build,
    after every widget is packed. Returns the applied "WxH" string,
    or "" — never raises."""
    try:
        win.update_idletasks()
        floor_w = int(min_w)
        floor_h = int(min_h) if min_h is not None else 0
        if ratchet:
            prev_w, prev_h = getattr(win, "_fit_size", (0, 0))
            try:
                cur_w = win.winfo_width()
                cur_h = win.winfo_height()
            except Exception:  # noqa: BLE001 — unmapped yet
                cur_w = cur_h = 0
            w = max(floor_w, win.winfo_reqwidth(), prev_w, cur_w)
            h = max(floor_h, win.winfo_reqheight(), prev_h, cur_h)
            win._fit_size = (w, h)
        else:
            w = max(floor_w, win.winfo_reqwidth())
            h = max(floor_h, win.winfo_reqheight())
        win.geometry("%dx%d" % (w, h))
        return "%dx%d" % (w, h)
    except Exception:  # noqa: BLE001 — garnish must never bite
        return ""
