"""DS2 Markup Bench — pretty, minify and inspect XML.

Paste XML and get it re-formatted (2+ space indent), minified,
validated with honest line/column errors, and summarised (element
counts, max depth, attributes). Built on stdlib
``xml.etree.ElementTree`` with two hardening guards for untrusted
input: a 512 KB size cap and a nesting-depth cap — entity-blowup
exotics are refused, not executed. Junk in, honest message out;
the window never raises.

Open with: Workshop menu, palette, terminal ``xml`` / ``markup``.
"""

import re
import tkinter as tk
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from .i18n import tr

__all__ = ["xml_pretty", "xml_minify", "xml_validate", "tag_stats",
           "XmlBench", "open_xmlbench"]

_MAX_BYTES = 512 * 1024
_MAX_DEPTH = 200


def _check_size(text):
    if not isinstance(text, str):
        return "paste some XML first"
    if len(text.encode("utf-8", errors="replace")) > _MAX_BYTES:
        return "too large (limit %d KB)" % (_MAX_BYTES // 1024)
    if "<!ENTITY" in text or "<!DOCTYPE" in text:
        # DTD entities are the billion-laughs vector — refuse flatly
        return "DTD entities refused (safety)"
    return None


def _parse(text):
    """Parse with hardening; returns (root, None) or (None, msg)."""
    guard = _check_size(text)
    if guard:
        return None, guard
    try:
        root = ET.fromstring(text)
    except ParseError as exc:
        m = re.search(r"line (\d+), column (\d+)", str(exc))
        if m:
            return None, "invalid XML — line %s, column %s" % (
                m.group(1), m.group(2))
        return None, "invalid XML"
    except (ValueError, RecursionError, MemoryError):
        return None, "XML refused (too deep or too weird)"
    return root, None


def _depth(elem, cap=_MAX_DEPTH):
    """Deepest path below *elem*; capped so hostile nests can't hang."""
    depth = 0
    level = [elem]
    while level and depth < cap:
        nxt = []
        for e in level:
            nxt.extend(e)
        depth += 1
        level = nxt
    return depth


def xml_pretty(text, indent=2):
    """Re-indent XML. Returns (pretty_text, None) or (None, msg)."""
    root, err = _parse(text)
    if err:
        return None, err
    try:
        ET.indent(root, space=" " * max(1, min(8, int(indent))))
        out = ET.tostring(root, encoding="unicode",
                          xml_declaration=False)
    except (ValueError, RecursionError):
        return None, "could not re-indent (too deep?)"
    return out.rstrip(), None


def xml_minify(text):
    """Strip inter-element whitespace. (min, None) or (None, msg)."""
    root, err = _parse(text)
    if err:
        return None, err
    try:
        for e in root.iter():
            if e.text is not None and not e.text.strip():
                e.text = None
            if e.tail is not None and not e.tail.strip():
                e.tail = None
        out = ET.tostring(root, encoding="unicode")
    except (ValueError, RecursionError):
        return None, "could not minify (too deep?)"
    return re.sub(r">\s+<", "><", out), None


def xml_validate(text):
    """(True, 'valid') or (False, human message). Never raises."""
    if not isinstance(text, str) or not text.strip():
        return False, "paste some XML first"
    _root, err = _parse(text)
    if err:
        return False, err
    return True, "valid XML"


def tag_stats(text):
    """Element census. (stats, None) or (None, msg)."""
    root, err = _parse(text)
    if err:
        return None, err
    counts = {}
    attrs = 0
    texts = 0
    for e in root.iter():
        counts[e.tag] = counts.get(e.tag, 0) + 1
        attrs += len(e.attrib)
        if e.text and e.text.strip():
            texts += 1
    return {"root": root.tag,
            "elements": sum(counts.values()),
            "unique_tags": len(counts),
            "top": sorted(counts.items(), key=lambda kv: -kv[1])[:5],
            "max_depth": _depth(root),
            "attributes": attrs,
            "text_nodes": texts}, None


def stats_line(text):
    """One human line for the window status. Never raises."""
    try:
        stats, err = tag_stats(text)
        if err:
            return err
        top = ", ".join("%s×%d" % (tag, n) for tag, n in stats["top"]
                        [:3])
        return ("%d elements · %d unique tags · depth %d · %d attrs"
                " · top: %s" % (stats["elements"],
                                stats["unique_tags"],
                                stats["max_depth"],
                                stats["attributes"],
                                top or "—"))
    except Exception:  # noqa: BLE001 — status must never die
        return "stats unavailable"


# --------------------------------------------------------------- window

SAMPLE_XML = """<note id="42"><to>DXN1</to><from>DS2</from>\
<body>Sprint bonus rounds rock.</body><tags>\
<tag>sprint</tag><tag>polish</tag></tags></note>"""


class XmlBench(tk.Toplevel):
    """XML workbench window. Never raises on junk input."""

    def __init__(self, parent, theme, initial=""):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme

        self.title("Markup Bench — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("720x480")
        self.minsize(560, 360)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="markup bench — xml pretty · minify · "
                           "validate · inspect",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=10, pady=8)

        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg=t.get("bg", "#16161e"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                  padx=(10, 4), pady=10)
        tk.Label(left, text="paste xml here",
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(anchor="w")
        self.input = tk.Text(left, width=24, wrap="word",
                             bg=t.get("editor_bg", "#1a1a24"),
                             fg=t.get("text", "#e8e8f0"),
                             insertbackground=t.get("text", "#fff"),
                             relief=tk.FLAT, padx=8, pady=6)
        self.input.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.input.insert("1.0", initial or SAMPLE_XML)
        self.input.bind("<KeyRelease>", lambda _e: self._schedule())

        right = tk.Frame(body, bg=t.get("bg", "#16161e"))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                   padx=(4, 10), pady=10)
        row = tk.Frame(right, bg=t.get("bg", "#16161e"))
        row.pack(fill=tk.X)
        tk.Button(row, text="pretty", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._pretty).pack(side=tk.LEFT,
                                             padx=(0, 4), pady=(0, 4))
        tk.Button(row, text="minify", relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._minify).pack(side=tk.LEFT, pady=(0, 4))
        self.output = tk.Text(right, wrap="word",
                              bg=t.get("editor_bg", "#1a1a24"),
                              fg=t.get("text", "#e8e8f0"),
                              relief=tk.FLAT, padx=8, pady=6)
        self.output.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.output.configure(state=tk.DISABLED)

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(bottom, text="ready", anchor="w",
                               bg=t.get("bg", "#16161e"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Button(bottom, text=tr("xml.copy_out"), relief=tk.FLAT,
                  bg=t.get("button", "#2a2a3a"),
                  fg=t.get("text", "#e8e8f0"),
                  activebackground=t.get("button_hover", "#33334a"),
                  command=self._copy_out).pack(side=tk.RIGHT,
                                               padx=8, pady=4)

        self._after_id = None
        self._validate()

    # ---------------------------------------------------- behaviour
    def _schedule(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._after_id = self.after(300, self._validate)
        except Exception:
            pass

    def _text(self):
        try:
            return self.input.get("1.0", "end").rstrip("\n")
        except Exception:
            return ""

    def _validate(self):
        """Live validation + stats. Junk-tolerant — never raises."""
        try:
            ok, msg = xml_validate(self._text())
            if ok:
                shown, color = msg, self.theme.get("ok", "#7ee787")
            elif msg.startswith("invalid"):
                shown, color = msg, self.theme.get("error",
                                                   "#ff6b6b")
            else:
                shown = msg if msg != "paste some XML first" \
                    else tr("xml.paste_hint")
                color = self.theme.get("text_muted", "#8a8a9a")
            self.status.config(text=shown, fg=color)
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _render(self, result):
        """Put an engine result (text, err) into the output pane."""
        try:
            out, err = result
            self.output.configure(state=tk.NORMAL)
            self.output.delete("1.0", "end")
            if err:
                self.output.insert("end", "⚠ %s" % err)
                self.status.config(
                    text=err,
                    fg=self.theme.get("error", "#ff6b6b"))
            else:
                self.output.insert("end", out)
                self.status.config(text=stats_line(self._text()),
                                   fg=self.theme.get(
                                       "text_muted", "#8a8a9a"))
            self.output.configure(state=tk.DISABLED)
        except Exception:  # noqa: BLE001 — the window must not die
            self.status.config(text="hiccup (input kept)")

    def _pretty(self):
        self._render(xml_pretty(self._text()))

    def _minify(self):
        self._render(xml_minify(self._text()))

    def _copy_out(self):
        try:
            text = self.output.get("1.0", "end").rstrip("\n")
            if not text:
                self.status.config(text="nothing to copy")
                return
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text="copied")
        except Exception:
            pass


def open_xmlbench(parent, theme, initial=""):
    """Public entry: open the Markup Bench window. Never raises."""
    try:
        win = XmlBench(parent, theme, initial=initial)
        try:
            win.focus_set()
        except Exception:
            pass
        return win
    except Exception:  # noqa: BLE001
        return None
