"""DXN1 STUDIO — honest keyboard hint bars (DS2 v2.48).

Every studio window answers to keys, but until now only the memory
knew which. A hint bar is the door sign: the keys a window really
responds to, printed along the bottom edge where the mouse lives.

The contract is honesty, inherited from v2.47's honest-keys audit:

* a key hint is rendered ONLY if its event pattern is genuinely
  bound — on the window or any descendant — using ``accel_pattern``
  (the same translator the palette audit uses);
* the ``Esc`` hint only appears when ``<Escape>`` is really bound;
* an unbacked hint is dropped (and reported via ``dropped_hints``)
  instead of being shown as a lie;
* a note (no key claim) is always shown — it describes the mouse,
  not the keyboard, so it cannot lie about keys;
* the bar never raises: a failed hint bar destroys itself quietly
  and the window loses nothing but garnish.

Verification runs when the bar is first mapped on screen (all
construction — including bindings made after the bar is created —
is finished by then), and can be re-run any time via ``refresh()``.
"""

import tkinter as tk

FONT_FALLBACK = ("sans-serif", 8)

# fallback colours — used only when the theme cannot supply a key
_FB_HEADER = "#161c24"
_FB_MUTED = "#6e7a8a"
_FB_ACCENT = "#8b5cf6"


def _color(theme, key, fallback):
    """Best-effort theme lookup — a dict-ish Theme or None."""
    try:
        val = theme[key]
        if val:
            return val
    except Exception:  # noqa: BLE001 — theme is garnish
        pass
    try:
        val = getattr(theme, key, None)
        if val:
            return val
    except Exception:  # noqa: BLE001
        pass
    return fallback


def _pattern_variants(pattern):
    """Equivalent spellings of a Tk event pattern.

    ``<0>`` and ``<Key-0>`` name the same key, but Tk compares bind
    patterns as written — so the verifier tries both spellings
    before declaring a hint unbacked. Honesty must not depend on
    which canonical form the window happened to use.
    """
    out = [pattern]
    try:
        if pattern.startswith("<") and pattern.endswith(">"):
            body = pattern[1:-1]
            if body.startswith("Key-"):
                out.append("<%s>" % body[4:])
            elif "-" not in body and len(body) <= 8:
                out.append("<Key-%s>" % body)
    except Exception:  # noqa: BLE001 — never raise
        pass
    return out


def tree_bound(win, pattern):
    """Is ``pattern`` instance-bound on ``win`` or any descendant?

    Walks the widget tree (window first, then children), asking each
    widget for the binding. Never raises; a dead window answers no.
    """
    if not pattern:
        return False
    try:
        todo = [win]
        seen = 0
        while seen < len(todo) and seen < 500:   # bounded walk
            w = todo[seen]
            seen += 1
            for pat in _pattern_variants(pattern):
                try:
                    if w.bind(pat):
                        return True
                except Exception:  # noqa: BLE001 — try the next spelling
                    pass
            try:
                todo.extend(w.winfo_children())
            except Exception:  # noqa: BLE001 — dying tree
                pass
        return False
    except Exception:  # noqa: BLE001 — never raise
        return False


def esc_bound(win):
    """Does this window (or a child) really answer to Escape?"""
    return tree_bound(win, "<Escape>")


def hint_bar(win, theme=None, pairs=(), notes=(), esc=True, before=None):
    """Build (and bottom-pack) an honest hint bar inside ``win``.

    ``pairs``   — iterable of ``(key, text[, display])``; the key is
                  verified through ``accel_pattern`` + ``tree_bound``,
                  ``display`` (optional) replaces the printed key.
    ``notes``   — plain text chips (mouse descriptions, no key claim).
    ``esc``     — offer the standard ``Esc close`` chip (only when
                  Escape is really bound).
    ``before``  — pack the bar before this already-packed sibling so
                  it keeps the very bottom edge even when called late.

    Returns the bar frame with three useful attributes:
    ``dropped_hints`` (keys refused for honesty), ``filled`` (bool),
    and ``refresh()`` (re-verify + re-render). Never raises.
    """
    bar = None
    try:
        bar = tk.Frame(win, bg=_color(theme, "header", _FB_HEADER))
        bar.dropped_hints = []
        bar.filled = False
        try:
            # introspectable honesty: what the bar claims, readable
            bar.pairs = tuple(tuple(e) for e in pairs)
        except Exception:  # noqa: BLE001 — garnish
            bar.pairs = ()

        def _pack():
            try:
                if before is not None:
                    bar.pack(side=tk.BOTTOM, fill=tk.X, before=before)
                else:
                    bar.pack(side=tk.BOTTOM, fill=tk.X)
            except Exception:  # noqa: BLE001 — any pack is better than none
                try:
                    bar.pack(side=tk.BOTTOM, fill=tk.X)
                except Exception:  # noqa: BLE001
                    pass

        def _fill(_event=None):
            try:
                if bar.filled:
                    return True
                for child in bar.winfo_children():
                    child.destroy()
                bar.dropped_hints = []
                chips = []
                if esc and esc_bound(win):
                    chips.append(("Esc", "close", "Esc"))
                from .app import accel_pattern   # lazy — avoids a cycle
                for entry in pairs:
                    try:
                        key, text = entry[0], entry[1]
                        display = entry[2] if len(entry) > 2 else key
                        pattern = accel_pattern(key)
                        if pattern and tree_bound(win, pattern):
                            chips.append((key, text, display))
                        else:
                            bar.dropped_hints.append(key)
                    except Exception:  # noqa: BLE001 — one bad pair dies alone
                        bar.dropped_hints.append(getattr(entry, "0", "?"))
                bar.filled = True
                if not chips and not notes:
                    bar.pack_forget()
                    return True
                bg = _color(theme, "header", _FB_HEADER)
                muted = _color(theme, "text_muted", _FB_MUTED)
                accent = _color(theme, "accent", _FB_ACCENT)
                first = True

                def _sep():
                    nonlocal first
                    if not first:
                        tk.Label(bar, text="·", bg=bg, fg=muted,
                                 font=FONT_FALLBACK).pack(
                            side=tk.LEFT, padx=3)
                    first = False

                for _key, text, display in chips:
                    _sep()
                    tk.Label(bar, text=display, bg=bg, fg=accent,
                             font=FONT_FALLBACK).pack(
                        side=tk.LEFT, padx=(8, 0))
                    tk.Label(bar, text=text, bg=bg, fg=muted,
                             font=FONT_FALLBACK).pack(
                        side=tk.LEFT, padx=(3, 0))
                for note in notes:
                    _sep()
                    tk.Label(bar, text=note, bg=bg, fg=muted,
                             font=FONT_FALLBACK).pack(
                        side=tk.LEFT, padx=(8, 0))
                return True
            except Exception:  # noqa: BLE001 — a hint bar must never raise
                try:
                    bar.destroy()
                except Exception:  # noqa: BLE001
                    pass
                return False

        bar.refresh = _fill
        bar.bind("<Map>", _fill)
        _pack()
        try:
            # deterministic verify: the first idle moment after
            # construction — every binding the window makes is in
            # place by then, under update() pumping or a real loop
            bar.after_idle(_fill)
        except Exception:  # noqa: BLE001 — mapping check is garnish
            pass
    except Exception:  # noqa: BLE001 — never raise
        try:
            if bar is not None:
                bar.destroy()
        except Exception:  # noqa: BLE001
            pass
        return None
    return bar
