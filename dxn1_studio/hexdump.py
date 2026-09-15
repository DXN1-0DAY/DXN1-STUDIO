"""DS2 ByteSnoop — hexdump & byte inspector.

Paste text or raw hex and read the bytes. The engine renders a
classic 16-wide hexdump (``00000000  68 65 6c 6c 6f  …  |hello|``),
parses hex back into bytes (spaces, colons, ``0x`` prefixes and
offset columns are all tolerated) and summarises a byte sample
(total, unique, printable %, high-bit %) — pure stdlib, unit-tested,
junk-tolerant. The window never raises on weird input.

Open with: Workshop menu, palette, terminal ``hexdump`` / ``bytes``.
"""

import re
import tkinter as tk

from . import hints
from .i18n import tr

__all__ = ["hexdump", "from_hex", "to_hex", "byte_stats",
           "ByteSnoop", "open_bytesnoop"]

_PRINTABLE = set(range(0x20, 0x7F))


def _as_bytes(data):
    """Coerce str/bytes/bytearray to bytes or raise TypeError."""
    if isinstance(data, str):
        return data.encode("utf-8", errors="replace")
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    raise TypeError("hexdump needs str or bytes, got %r"
                    % type(data).__name__)


def to_hex(data, sep=" "):
    """Bytes → lowercase hex text (``68 65 6c``). Never raises for
    str/bytes; junk types return \"\"."""
    try:
        return sep.join("%02x" % b for b in _as_bytes(data))
    except (TypeError, ValueError):
        return ""


def from_hex(text):
    """Hex text → bytes, or None when unparseable.

    Tolerates spaces, newlines, commas, colons, ``0x`` prefixes,
    and xxd-style offset columns (an address column of hex digits
    at line start followed by ``:`` or two spaces is dropped).
    """
    if not isinstance(text, str):
        return None
    cleaned = []
    for raw in text.splitlines():
        line = raw.strip()
        # drop "00000000:" / "00000000  " offset columns
        line = re.sub(r"^[0-9a-fA-F]{4,16}\s*:\s*", "", line)
        line = re.sub(r"^[0-9a-fA-F]{8}\s{2,}", "", line)
        cleaned.append(line)
    clean = " ".join(cleaned)
    clean = re.sub(r"0[xX]", " ", clean)
    clean = re.sub(r"[^0-9a-fA-F]", " ", clean)
    digits = re.sub(r"\s+", "", clean)
    if not digits or len(digits) % 2:
        return None
    try:
        return bytes.fromhex(digits)
    except ValueError:  # pragma: no cover — guarded by the checks above
        return None


def hexdump(data, width=16):
    """Classic hexdump lines: offset, hex, ascii gutter.

    Accepts str (utf-8 encoded) or bytes. Non-str/bytes → [].
    """
    try:
        buf = _as_bytes(data)
    except TypeError:
        return []
    lines = []
    for off in range(0, len(buf), width):
        chunk = buf[off:off + width]
        hexpart = " ".join("%02x" % b for b in chunk)
        # pad hex column so the ascii gutter always aligns
        hexpart = hexpart.ljust(width * 3 - 1)
        gut = "".join(chr(b) if b in _PRINTABLE else "." for b in chunk)
        lines.append("%08x  %s  |%s|" % (off, hexpart, gut))
    return lines


def byte_stats(data):
    """Summary of a byte sample. Junk types → honest zeros."""
    try:
        buf = _as_bytes(data)
    except TypeError:
        buf = b""
    total = len(buf)
    if not total:
        return {"total": 0, "unique": 0, "printable_pct": 0.0,
                "high_bit_pct": 0.0}
    printable = sum(1 for b in buf if b in _PRINTABLE)
    high_bit = sum(1 for b in buf if b >= 0x80)
    return {"total": total,
            "unique": len(set(buf)),
            "printable_pct": round(100.0 * printable / total, 1),
            "high_bit_pct": round(100.0 * high_bit / total, 1)}


def stats_line(data):
    """One human line for the window status bar. Never raises."""
    try:
        s = byte_stats(data)
    except Exception:  # noqa: BLE001 — status must never die
        return "stats unavailable"
    if not s["total"]:
        return "no bytes yet — paste text or hex on the left"
    return ("%d bytes · %d unique · %.1f%% printable · %.1f%% high-bit"
            % (s["total"], s["unique"], s["printable_pct"],
               s["high_bit_pct"]))


# --------------------------------------------------------------- window

SAMPLE_TEXT = "DXN1 STUDIO — snoop the bytes!"


class ByteSnoop(tk.Toplevel):
    """Hexdump window. Never raises on junk input."""

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("ByteSnoop — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("700x460")
        # DS2 v2.62 — width accounting round four: once the build
        # settles, open no narrower (or shorter) than what it
        # actually packed (the 700x460 default is the floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 700, 460))
        self.minsize(560, 340)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="bytesnoop — hexdump & byte inspector",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=10, pady=8)
        self.mode = tk.StringVar(value="text")
        for label in ("text", "hex"):
            tk.Radiobutton(top, text=label, value=label,
                           variable=self.mode, command=self.refresh,
                           bg=t.get("header", "#242432"),
                           fg=t.get("text", "#e8e8f0"),
                           selectcolor=t.get("editor_bg", "#1a1a24"),
                           activebackground=t.get("header", "#242432"),
                           activeforeground=t.get("text", "#e8e8f0"),
                           highlightthickness=0).pack(side=tk.LEFT,
                                                      padx=2)

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg=t.get("bg", "#16161e"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                  padx=(10, 4), pady=10)
        tk.Label(left, text="paste text or hex here",
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.input = tk.Text(left, width=24, wrap="char",
                             bg=t.get("editor_bg", "#1a1a24"),
                             fg=t.get("text", "#e8e8f0"),
                             insertbackground=t.get("text", "#fff"),
                             relief=tk.FLAT, padx=8, pady=6)
        self.input.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.input.insert("1.0", initial or SAMPLE_TEXT)
        self.input.bind("<KeyRelease>", lambda _e: self._schedule())

        right = tk.Frame(body, bg=t.get("bg", "#16161e"))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                   padx=(4, 10), pady=10)
        tk.Label(right, text=tr("hex.rows_label"),
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.output = tk.Text(right, wrap="none",
                              bg=t.get("editor_bg", "#1a1a24"),
                              fg=t.get("text", "#e8e8f0"),
                              relief=tk.FLAT, padx=8, pady=6)
        self.output.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.output.configure(state=tk.DISABLED)
        try:
            self.output.configure(font=("TkFixedFont", 10))
        except Exception:
            pass

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text="ready", anchor="w",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text=tr("hex.copy_dump"), relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_dump).pack(side=tk.RIGHT, padx=8,
                                                pady=4)

        # keys first advertised by the bar below (v2.50 wave 3)
        self.bind("<Escape>", lambda _e: self.destroy())
        # Ctrl+Shift+C, not Ctrl+C — the input keeps its native copy
        self.bind("<Control-C>", lambda _e: self._copy_dump())
        hints.hint_bar(self, t,
                       pairs=[("Ctrl+Shift+C", "copy dump")],
                       notes=["hex + ascii as you type"])

        self._after_id = None
        self.refresh()

    # ---------------------------------------------------- behaviour
    def _schedule(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._after_id = self.after(300, self.refresh)
        except Exception:
            pass

    def _source(self):
        """Current input as bytes under the active mode (or None)."""
        try:
            text = self.input.get("1.0", "end").rstrip("\n")
        except Exception:
            return None
        if self.mode.get() == "hex":
            return from_hex(text)
        return text.encode("utf-8", errors="replace")

    def refresh(self):
        """Re-render the hexdump. Junk-tolerant — never raises."""
        try:
            data = self._source()
            self.output.configure(state=tk.NORMAL)
            self.output.delete("1.0", "end")
            if data is None:
                self.status.config(
                    text="that hex doesn't parse — check odd digits "
                         "or stray characters")
            elif not data:
                self.status.config(
                    text="no bytes yet — paste text or hex on the "
                         "left")
            else:
                for line in hexdump(data):
                    self.output.insert("end", line + "\n")
                self.status.config(text=stats_line(data))
            self.output.configure(state=tk.DISABLED)
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _copy_dump(self):
        try:
            text = self.output.get("1.0", "end").rstrip("\n")
            if not text:
                self.status.config(text="nothing to copy")
                return
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text="hexdump copied")
        except Exception:
            pass


def open_bytesnoop(parent, theme, initial=""):
    """Public entry: open the ByteSnoop window. Never raises."""
    try:
        win = ByteSnoop(parent, theme, initial=initial)
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
