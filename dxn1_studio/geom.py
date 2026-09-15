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
           "remember_root", "restore_root", "fit_to_content",
           "cascade_positions", "tile_rects",
           "parse_alpha", "focused_toplevel", "MIN_ALPHA"]

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


def cascade_positions(n, sw, sh, x0=60, y0=60, step_x=28, step_y=28,
                      win_w=400, win_h=300, margin=8):
    """DS2 v2.65 — the cascade layout, pure math: ``n`` windows
    stacked from ``(x0, y0)``, each offset by ``(step_x, step_y)``
    so every title bar stays grabbable, wrapping back toward the
    origin when the stack would march a window's title off-screen.
    Every position is clamped so the window (assumed ``win_w`` x
    ``win_h`` when the caller has nothing better) always keeps its
    title bar inside the ``sw`` x ``sh`` screen. Returns a list of
    ``(x, y)`` ints, len == n; ``n <= 0`` → ``[]``. Never raises."""
    try:
        n = int(n)
        if n <= 0:
            return []
        sw, sh = int(sw), int(sh)
        x0, y0 = int(x0), int(y0)
        step_x, step_y = int(step_x), int(step_y)
        win_w, win_h = int(win_w), int(win_h)
        margin = max(0, int(margin))
        # the furthest offset before a title bar would leave the
        # screen's right/bottom edge (keep at least the title bar
        # height worth of window visible)
        max_off_x = max(0, sw - x0 - min(win_w, 120) - margin)
        max_off_y = max(0, sh - y0 - min(win_h, 40) - margin)
        # how many offsets fit before the wrap: k = i*step must stay
        # <= max_off, so the span is floor(max_off/step)+1 (1 when
        # the screen is too small for even one step)
        span_x = max(1, max_off_x // step_x + 1) if step_x > 0 else 1
        span_y = max(1, max_off_y // step_y + 1) if step_y > 0 else 1
        out = []
        for i in range(n):
            kx = i % span_x
            ky = i % span_y
            x = min(x0 + kx * step_x, max(0, sw - min(win_w, 120)
                                          - margin))
            y = min(y0 + ky * step_y, max(0, sh - min(win_h, 40)
                                          - margin))
            out.append((max(0, x), max(0, y)))
        return out
    except Exception:  # noqa: BLE001 — layout must never raise
        return []


def tile_rects(n, sw, sh, margin=8, gap=6, min_w=240, min_h=160):
    """DS2 v2.65 — the tile layout, pure math: ``n`` windows in a
    cols x rows grid (``cols = ceil(sqrt(n))``) covering the screen
    inside ``margin``, cells separated by ``gap``. Cells never
    shrink below ``min_w`` x ``min_h`` unless the screen itself is
    smaller, and every rect stays on-screen. Returns a list of
    ``(x, y, w, h)`` ints, len == n, row-major order; ``n <= 0`` →
    ``[]``. Never raises."""
    try:
        import math
        n = int(n)
        if n <= 0:
            return []
        sw, sh = int(sw), int(sh)
        margin = max(0, int(margin))
        gap = max(0, int(gap))
        min_w, min_h = int(min_w), int(min_h)
        cols = max(1, int(math.ceil(math.sqrt(n))))
        rows = max(1, int(math.ceil(n / float(cols))))
        avail_w = max(0, sw - 2 * margin - (cols - 1) * gap)
        avail_h = max(0, sh - 2 * margin - (rows - 1) * gap)
        # the designed cell is the floored share; on a screen too
        # small for the floor, the SCREEN wins (a window past the
        # edge is invisible, a cramped one is merely small)
        def _cell(floor, avail_total, edge, parts):
            floored = max(floor, avail_total // parts)
            grid = parts * floored + (parts - 1) * gap
            if grid + margin <= edge:
                return floored
            return max(1, (edge - margin - (parts - 1) * gap) // parts)
        cell_w = _cell(min_w, avail_w, sw, cols)
        cell_h = _cell(min_h, avail_h, sh, rows)
        grid_w = cols * cell_w + (cols - 1) * gap
        grid_h = rows * cell_h + (rows - 1) * gap
        ox = margin if grid_w + margin <= sw else max(0, sw - grid_w)
        oy = margin if grid_h + margin <= sh else max(0, sh - grid_h)
        out = []
        for i in range(n):
            r, c = divmod(i, cols)
            out.append((ox + c * (cell_w + gap),
                        oy + r * (cell_h + gap),
                        cell_w, cell_h))
        return out
    except Exception:  # noqa: BLE001 — layout must never raise
        return []


LAYOUTS_KEY = "tool_window_layouts"
LAYOUT_CAP = 12          # remembered layouts (LRU by save time)
LAYOUT_WINDOW_CAP = 40   # windows per layout (a desk, not a museum)


def window_layer(win):
    """DS2 v2.68 — how a window is LAYERED, read honestly, pure
    decision-making: ``(alpha, topmost)`` straight from the window
    manager, with the honest defaults ``(1.0, False)`` when the
    window refuses to say (a dead window, a headless quirk, an
    exotic embedding). A window that will not answer is assumed
    ordinary — never raises."""
    try:
        a = float(win.attributes("-alpha"))
        if a != a or a < 0.0:        # NaN and negatives are junk
            a = 1.0
        a = round(min(1.0, max(0.0, a)), 3)
    except Exception:  # noqa: BLE001 — no alpha here
        a = 1.0
    try:
        t = win.attributes("-topmost")
        # a real WM says True/False or 1/0; anything else (a stray
        # string, a banana) is no crown at all
        if isinstance(t, bool):
            top = t
        elif isinstance(t, int):
            top = bool(t)
        else:
            top = False
    except Exception:  # noqa: BLE001 — no crown here
        top = False
    return a, top


def capture_layout(windows):
    """DS2 v2.66 — one layout snapshot, pure: a list of live
    Toplevels becomes ``[{"title", "geometry", "transient"}...]``
    in window order. Dead windows are skipped silently, a window
    that refuses its title or geometry is recorded as best-effort
    with honest empties. Never raises.
    DS2 v2.68 — the snapshot remembers the LAYERS too: each entry
    gains ``alpha`` (the ghost level, 1.0 = solid) and ``topmost``
    (the pin), so a desk arranged once comes back exactly as it
    was — geometry AND skin."""
    try:
        out = []
        for w in list(windows)[:LAYOUT_WINDOW_CAP]:
            try:
                alpha, top = window_layer(w)
                out.append({
                    "title": str(w.title()),
                    "geometry": str(w.winfo_geometry()),
                    "transient": bool(w.transient()),
                    "alpha": alpha,
                    "topmost": top,
                })
            except Exception:  # noqa: BLE001 — one dead window
                out.append({"title": "", "geometry": "",
                            "transient": True,
                            "alpha": 1.0, "topmost": False})
        return out
    except Exception:  # noqa: BLE001 — a snapshot never raises
        return []


def store_layout(store, name, snapshot, cap=LAYOUT_CAP):
    """DS2 v2.66 — put one named snapshot into the layouts store
    (a plain dict as read from config). Same name overwrites —
    arranging the desk twice is an update, not an error. Oldest
    layouts fall off past ``cap``. Returns True when stored.
    Never raises."""
    try:
        name = str(name or "").strip()
        if not name or not isinstance(snapshot, list):
            return False
        layouts = dict(store if isinstance(store, dict) else {})
        layouts.pop(name, None)
        layouts[name] = [dict(e) if isinstance(e, dict) else
                         {"title": "", "geometry": "",
                          "transient": True,
                          "alpha": 1.0, "topmost": False}
                         for e in snapshot[:LAYOUT_WINDOW_CAP]]
        while len(layouts) > cap:
            oldest = next(iter(layouts))
            layouts.pop(oldest, None)
        store.clear()
        store.update(layouts)
        return True
    except Exception:  # noqa: BLE001 — storage must never raise
        return False


def apply_layout(snapshot, windows, min_w=40, min_h=20):
    """DS2 v2.66 — restore one snapshot onto the live windows, pure
    decision-making: each saved entry is matched case-insensitively
    by exact title first, then by title substring; a match gets the
    saved geometry handed back. Returns ``(restored, missing)``
    where restored is ``[(title, geometry)]`` and missing is the
    titles with no live window — layouts arrange what EXISTS; the
    verb tells the user what to reopen. Never raises.
    DS2 v2.68 — restored entries grow into four-tuples
    ``(title, geometry, alpha, topmost)``: the layering rides
    along so the verb can re-ghost and re-pin what it puts back.
    A snapshot that DOESN'T say — saved before the layers were
    remembered, or carrying junk — yields ``None`` for that
    layer, and None means DON'T TOUCH: an old layout keeps
    meaning what it always meant, and junk is never a license to
    repaint a window."""
    try:
        restored, missing = [], []
        live = []
        for w in list(windows):
            try:
                live.append((str(w.title()).lower(), w))
            except Exception:  # noqa: BLE001 — dead window
                pass
        used = set()
        for entry in snapshot[:LAYOUT_WINDOW_CAP]:
            title = str((entry or {}).get("title") or "").strip()
            geo = str((entry or {}).get("geometry") or "").strip()
            if not title:
                continue
            hit = None
            for lt, w in live:
                if lt == title.lower() and id(w) not in used:
                    hit = w
                    break
            if hit is None:
                for lt, w in live:
                    if title.lower() in lt and id(w) not in used:
                        hit = w
                        break
            if hit is None:
                missing.append(title)
                continue
            used.add(id(hit))
            if geo and parse_geometry(geo):
                # v2.68 — the layering rides along; a layer the
                # snapshot does not state (absent or junk) comes
                # back None and the verb touches nothing
                raw_a = (entry or {}).get("alpha", None)
                alpha = None
                if isinstance(raw_a, (int, float)) \
                        and not isinstance(raw_a, bool):
                    f = float(raw_a)
                    if f == f and 0.0 <= f <= 1.0:
                        alpha = round(f, 3)
                raw_t = (entry or {}).get("topmost", None)
                top = raw_t if isinstance(raw_t, bool) else None
                restored.append((title, geo, alpha, top))
            else:
                missing.append(title)
        return restored, missing
    except Exception:  # noqa: BLE001 — a restore never raises
        return [], []


def layer_counts(snapshot):
    """DS2 v2.68 — how much layering a snapshot carries, pure:
    ``(ghosted, pinned)`` — the windows saved below full opacity
    and the windows saved with the crown. Entries that do not
    state a layer (junk, wrong type) count as neither — a count
    is only ever earned, never guessed. The save report, the
    list marker and the show verb all speak from this one body.
    Never raises."""
    try:
        ghosted = pinned = 0
        for entry in list(snapshot or [])[:LAYOUT_WINDOW_CAP]:
            try:
                raw_a = (entry or {}).get("alpha", None)
                if isinstance(raw_a, (int, float)) \
                        and not isinstance(raw_a, bool) \
                        and 0.0 <= float(raw_a) < 0.995:
                    ghosted += 1
            except Exception:  # noqa: BLE001 — junk alpha
                pass
            try:
                if (entry or {}).get("topmost", None) is True:
                    pinned += 1
            except Exception:  # noqa: BLE001 — junk pin
                pass
        return ghosted, pinned
    except Exception:  # noqa: BLE001 — a count never raises
        return 0, 0


# ------------------------------------------------- v2.67.0 window layering

MIN_ALPHA = 0.10         # a window ghosted below this is simply lost


def parse_alpha(text):
    """DS2 v2.67 — one ghost level, parsed honestly, pure. ``60`` and
    ``60%`` and ``0.6`` all mean 60%; ``off`` / ``solid`` / ``full``
    / ``1`` mean 100%; anything past the ends clamps into
    ``[MIN_ALPHA, 1.0]`` (a window you cannot see is a window you
    cannot close). Junk — empty, words, None — is None, and the
    caller answers usage. Never raises."""
    try:
        if text is None:
            return None
        s = str(text).strip().lower()
        if not s:
            return None
        if s in ("off", "solid", "full", "none", "1", "1.0", "1.00",
                 "100", "100%"):
            return 1.0
        had_pct = s.endswith("%")
        if had_pct:
            s = s[:-1].strip()
        val = float(s)
        if val < 0:                  # a negative ghost is nonsense
            return None
        if had_pct or (val > 1.0 and float(val).is_integer()):
            val = val / 100.0        # 60 and 60% are percents; a
                                     # decimal like 1.5 is a fraction
                                     # that clamps solid, not 1.5%
        return round(min(1.0, max(MIN_ALPHA, val)), 3)
    except Exception:  # noqa: BLE001 — junk in, None out
        return None


def focused_toplevel(widget, windows):
    """DS2 v2.67 — which of ``windows`` holds the focus, pure
    decision-making: the focused widget's toplevel ancestor is
    identity-matched against the live windows. No focus (the desktop
    has it), a widget outside the list, or junk → None. Never
    raises."""
    try:
        if widget is None:
            return None
        top = widget.winfo_toplevel()
        for w in list(windows):
            if w is top or w is widget:
                return w
        return None
    except Exception:  # noqa: BLE001 — a mark never raises
        return None
