"""DS2 Line Tools — sort, dedupe, reverse, shuffle and tidy lines.

Pure engine over plain text (deterministic when given a seeded rng),
so the editor can hand it a selection or the whole buffer and get
predictable, testable results.

Used by: Edit menu → *Line Tools*, palette, terminal
``sort az|za|len|dedupe|shuffle|reverse|trim``, and the Ctrl+Alt
shortcuts (S sort, D dedupe, H shuffle, R reverse).
"""

import random

__all__ = ["MODES", "transform_lines", "expand_range"]

MODES = ("az", "za", "len", "dedupe", "shuffle", "reverse", "trim")


def expand_range(text, start_line=1, end_line=None):
    """Clamp a 1-based inclusive line range to the buffer.

    end_line=None → last *real* line (a trailing newline does not
    count as an extra empty line). Returns (start, end) with
    1 <= start <= end <= number of lines (empty text → (1, 1)).
    """
    lines = text.split("\n")
    if lines and lines[-1] == "" and text.endswith("\n"):
        lines.pop()                     # phantom line after final \n
    n = len(lines)
    if n == 0:
        return 1, 1
    start = max(1, int(start_line or 1))
    end = n if end_line is None else max(1, int(end_line))
    return min(start, n), min(max(start, end), n)


def transform_lines(text, mode, start_line=1, end_line=None, rng=None):
    """Transform lines [start_line, end_line] of *text* by *mode*.

    Modes:
      az       ascending sort (case-insensitive, stable)
      za       descending sort
      len      shortest line first (stable)
      dedupe   drop repeated lines, keeping first occurrences
      shuffle  random order (rng injectable for tests)
      reverse  reverse order
      trim     strip trailing whitespace per line

    The text before/after the range is preserved byte-for-byte.
    Unknown mode or non-text input returns the text unchanged.
    """
    if not isinstance(text, str) or mode not in MODES:
        return text
    try:
        start, end = expand_range(text, start_line, end_line)
    except (TypeError, ValueError):
        return text
    trailing = text.endswith("\n")
    lines = text.split("\n")
    if trailing and lines and lines[-1] == "":
        lines.pop()                     # never sort the phantom line
    if not lines:
        return text
    block = lines[start - 1:end]

    if mode == "az":
        block = sorted(block, key=lambda s: s.lower())
    elif mode == "za":
        block = sorted(block, key=lambda s: s.lower(), reverse=True)
    elif mode == "len":
        block = sorted(block, key=len)
    elif mode == "dedupe":
        seen = set()
        out = []
        for s in block:
            k = s.strip().lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(s)
        block = out
    elif mode == "shuffle":
        block = list(block)
        (rng or random).shuffle(block)
    elif mode == "reverse":
        block = list(reversed(block))
    elif mode == "trim":
        block = [s.rstrip() for s in block]

    lines[start - 1:end] = block
    out = "\n".join(lines)
    return out + "\n" if trailing else out
