"""DXN1 STUDIO — fuzzy launcher scoring (DS2 v2.29).

The brain behind the command palette and Quick Open: type a few
letters and the best candidates surface first — even when your letters
are not a substring of the target. ``cmpr`` finds "compare themes",
``qst`` finds "Quick Open", ``@init`` finds ``__init__`` in symbol
mode. Substring hits still win; they simply score highest because
contiguity is rewarded.

Scoring is deterministic and documented so tests can pin exact
behaviour. For every matched character (case-insensitive subsequence
walk):

    +2   base, per matched character
    +6   prefix anchor — the first query char matches index 0
    +8   word-boundary start — match at a space, ``_ - . / (`` boundary
         or at the very start of the text
    +5   camel hump — matched char is uppercase right after a lowercase
    +4   contiguity — each char matched directly after the previous one
    -1   gap penalty — every character skipped *between* matches
    floor 0 — if it matches at all, it scores >= 0

Pure functions, junk-tolerant: ``None`` never matches, anything else is
coerced with ``str()`` and the walk never raises.
"""

# boundary characters that start a new "word" inside a path or label
_SEPARATORS = " _-./(\\:>"

# weights (exposed for tests and future tuning)
W_BASE = 2
W_ANCHOR = 6
W_WORD = 8
W_HUMP = 5
W_CONTIG = 4
W_GAP = -1


def match(query, text):
    """Return ``(score, positions)`` or ``(-1, ())`` when nothing matches.

    ``positions`` are indices into ``text`` for the matched characters,
    in query order — usable for underline/bold rendering later. Empty
    query matches everything with score 0 and no positions.
    """
    if query is None or text is None:
        return -1, ()
    try:
        q = str(query).lower()
        t = str(text).lower()
    except Exception:  # noqa: BLE001 — exotic objects never crash scoring
        return -1, ()
    if not q:
        return 0, ()
    if not t:
        return -1, ()
    raw = str(text)
    total, positions, prev_idx, search_from = 0, [], -2, 0
    for i, ch in enumerate(q):
        idx = t.find(ch, search_from)
        if idx < 0:
            return -1, ()
        gained = W_BASE
        if idx == 0:
            gained += W_ANCHOR
            if ch == raw[0]:
                pass  # anchor already counted; case-equal is the norm
        if idx == 0 or (idx > 0 and t[idx - 1] in _SEPARATORS):
            gained += W_WORD
        elif idx > 0 and raw[idx].isupper() and raw[idx - 1].islower():
            gained += W_HUMP
        if prev_idx == idx - 1:
            gained += W_CONTIG
        elif prev_idx >= 0:
            gained += W_GAP * (idx - prev_idx - 1)
        total += gained
        positions.append(idx)
        prev_idx, search_from = idx, idx + 1
    return max(0, total), tuple(positions)


def score(query, text):
    """Convenience wrapper — just the integer score (``-1`` = no match)."""
    return match(query, text)[0]


def ranked(query, texts):
    """Rank texts: ``[(index, score, positions), ...]`` for matches only.

    Sorted by descending score, ties keep the input order (stable).
    Empty query returns every index with score 0, original order.
    """
    hits = []
    for i, text in enumerate(texts):
        s, pos = match(query, text)
        if s >= 0:
            hits.append((i, s, pos))
    hits.sort(key=lambda h: (-h[1], h[0]))
    return hits


def filter_ranked(query, items, key=None):
    """Re-order ``items`` by fuzzy relevance of ``key(item)`` (or item).

    The default palette/Quick Open entry point: empty query returns the
    items unchanged; otherwise matching items come back best-first and
    non-matching items are dropped. Junk keys coerce via ``str()`` and
    failing keys fall back to ``str(item)`` — this can never raise.
    """
    if not query:
        return list(items)
    scored = []
    for i, item in enumerate(items):
        try:
            text = key(item) if key is not None else item
        except Exception:  # noqa: BLE001 — a broken key falls back
            text = item
        s, _pos = match(query, text)
        if s >= 0:
            scored.append((-s, i, item))
    scored.sort(key=lambda h: (h[0], h[1]))
    return [item for _s, _i, item in scored]


def path_score(query, path, bonus=3):
    """Score a path for Quick Open — basename hits get a boost.

    A match fully inside the basename (after the last ``/``) outranks
    the same match in a deep directory: files beat folders. Returns the
    winning score (``-1`` = no match); ``bonus`` is the basename edge.
    """
    s, _pos = match(query, path)
    base = str(path).rsplit("/", 1)[-1] if path is not None else ""
    sb, _posb = match(query, base)
    if sb < 0:
        return s
    return max(s, sb + bonus)


# ---------------------------------------------------------------- self-test
if __name__ == "__main__":
    assert match("", "anything") == (0, ())
    assert match(None, "x") == (-1, ())
    assert match("a", None) == (-1, ())
    assert score("abc", "xabcx") > score("abc", "xaxbxcx")  # tight > spread
    assert score("abc", "abc") >= score("abc", "xabc")
    assert score("qo", "quick open") > 0          # not a substring
    assert score("cmpr", "compare themes") > 0    # subsequence with gaps
    assert score("zx", "quick open") == -1
    assert score("ABC", "xabc") > 0               # case-insensitive
    hits = ranked("st", ["stop", "settings", "zzz"])
    assert [h[0] for h in hits] == [0, 1] and len(hits) == 2
    assert filter_ranked("", ["b", "a"]) == ["b", "a"]  # empty keeps order
    assert filter_ranked("sv", ["save all", "scratch", "zen"],
                         key=str.upper) == ["save all"]
    assert path_score("app", "dxn1_studio/app.py") > \
        path_score("app", "d/a/p/p/x")            # basename boost
    assert filter_ranked(None, [1, 2]) == [1, 2]  # None query = no-op
    assert path_score("zz", "nope.py") == -1
    assert score(5, "port 5") > 0                  # coerced to str
    assert filter_ranked("x", [1, "ax"], key=None) == ["ax"]
    print("fuzzy.py self-test OK")


def split_runs(text, positions):
    """Split text into ``(chunk, is_matched)`` runs for rendering.

    Contiguous matched indices merge into one run, so highlighting a
    substring costs one extra widget, not one per character. Round-trip
    guarantee: ``"".join(c for c, _m in split_runs(t, p)) == t``.
    Junk positions (negative, out of range, unhashable) are ignored.
    """
    if text is None:
        return []
    try:
        text = str(text)
    except Exception:  # noqa: BLE001
        return []
    good = set()
    for p in (positions or ()):
        try:
            if 0 <= int(p) < len(text):
                good.add(int(p))
        except Exception:  # noqa: BLE001
            continue
    if not good:
        return [(text, False)] if text else []
    runs, cur, matched = [], "", False
    for i, ch in enumerate(text):
        m = i in good
        if m == matched:
            cur += ch
        else:
            if cur:
                runs.append((cur, matched))
            cur, matched = ch, m
    if cur:
        runs.append((cur, matched))
    return runs
