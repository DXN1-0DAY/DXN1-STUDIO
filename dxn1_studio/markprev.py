"""DS2 Markdown Preview — write docs with a live, styled preview.

A zero-dependency markdown renderer (headings, bold/italic/strike,
inline code, fenced code blocks with language, blockquotes, ordered /
unordered lists, pipe tables, links, horizontal rules) plus a
dual-pane window: edit the source on the left, watch the rendered
result on the right with a debounced live re-render.

Engine (parse_blocks / inline_spans / markdown_to_html) is pure and
unit-tested; the window never raises on weird input.

Open with: Workshop menu, palette, terminal ``md`` / ``preview``.
"""

import re
import tkinter as tk
import tkinter.font as tkfont

from .i18n import tr

__all__ = ["parse_blocks", "inline_spans", "markdown_to_html",
           "MarkdownPreview", "open_markdown_preview"]

# --------------------------------------------------------------- engine

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
_ULIST_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_OLIST_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")

_TOKEN_RE = re.compile(
    r"`([^`\n]+)`"                    # 1: inline code
    r"|\*\*([^*\n]+)\*\*"             # 2: bold
    r"|~~([^~\n]+)~~"                 # 3: strikethrough
    r"|\*([^*\n]+)\*"                 # 4: italic
    r"|\[([^\]\n]+)\]\(([^)\n]+)\)"   # 5: text, 6: url
)
_T_CODE, _T_BOLD, _T_STRIKE, _T_ITALIC, _T_LINK = 1, 2, 3, 4, 5


def inline_spans(text):
    """Split ``text`` into (kind, value) spans.

    kind ∈ {"plain", "code", "bold", "italic", "strike", "link"};
    for links, value is the ``(text, url)`` tuple. Unknown markup is
    left as plain text — the renderer never loses characters.
    """
    spans = []
    pos = 0
    for m in _TOKEN_RE.finditer(text or ""):
        if m.start() > pos:
            spans.append(("plain", text[pos:m.start()]))
        if m.group(_T_CODE) is not None:
            spans.append(("code", m.group(_T_CODE)))
        elif m.group(_T_BOLD) is not None:
            spans.append(("bold", m.group(_T_BOLD)))
        elif m.group(_T_STRIKE) is not None:
            spans.append(("strike", m.group(_T_STRIKE)))
        elif m.group(_T_ITALIC) is not None:
            spans.append(("italic", m.group(_T_ITALIC)))
        else:
            spans.append(("link", (m.group(5), m.group(6))))
        pos = m.end()
    if pos < len(text):
        spans.append(("plain", text[pos:]))
    return spans


def _para_break(line):
    """True when ``line`` starts a new block (ends a paragraph)."""
    s = line.strip()
    if not s:
        return True
    if s.startswith(("#", "```", ">")):
        return True
    if _HR_RE.match(s):
        return True
    if _ULIST_RE.match(s) or _OLIST_RE.match(s):
        return True
    return False


def parse_blocks(md):
    """Parse markdown into a list of block dicts.

    Block types: heading(level, text), para(text), code(lang, text),
    quote(text), ulist(items), olist(items), table(header, rows), hr.
    """
    lines = (md or "").splitlines()
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        m = _HEADING_RE.match(s)
        if m:
            blocks.append({"type": "heading",
                           "level": len(m.group(1)),
                           "text": m.group(2).strip()})
            i += 1
            continue
        if _HR_RE.match(s):
            blocks.append({"type": "hr"})
            i += 1
            continue
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            if i < n:
                i += 1          # consume closing fence
            blocks.append({"type": "code", "lang": lang,
                           "text": "\n".join(buf)})
            continue
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                piece = lines[i].strip()[1:].strip()
                if piece:
                    buf.append(piece)
                i += 1
            blocks.append({"type": "quote", "text": " ".join(buf)})
            continue
        # pipe table: current row + a separator row of |, :, - below it
        if "|" in s and i + 1 < n and "-" in lines[i + 1] \
                and _TABLE_SEP_RE.match(lines[i + 1]) \
                and "|" in lines[i + 1]:
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in
                             lines[i].strip().strip("|").split("|")])
                i += 1
            blocks.append({"type": "table", "header": header,
                           "rows": rows})
            continue
        m = _ULIST_RE.match(line)
        if m and not _TABLE_SEP_RE.match(line):
            items = []
            while i < n:
                mm = _ULIST_RE.match(lines[i])
                if not mm:
                    break
                items.append(mm.group(1).strip())
                i += 1
            blocks.append({"type": "ulist", "items": items})
            continue
        m = _OLIST_RE.match(line)
        if m:
            items = []
            while i < n:
                mm = _OLIST_RE.match(lines[i])
                if not mm:
                    break
                items.append(mm.group(1).strip())
                i += 1
            blocks.append({"type": "olist", "items": items})
            continue
        # paragraph — gather until a blank line / new block starter
        buf = [s]
        i += 1
        while i < n and not _para_break(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        blocks.append({"type": "para", "text": " ".join(buf)})
    return blocks


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _spans_html(text):
    out = []
    for kind, val in inline_spans(text):
        if kind == "plain":
            out.append(_esc(val))
        elif kind == "code":
            out.append("<code>%s</code>" % _esc(val))
        elif kind == "bold":
            out.append("<strong>%s</strong>" % _esc(val))
        elif kind == "italic":
            out.append("<em>%s</em>" % _esc(val))
        elif kind == "strike":
            out.append("<del>%s</del>" % _esc(val))
        else:
            label, url = val
            out.append('<a href="%s">%s</a>' % (_esc(url), _esc(label)))
    return "".join(out)


_HTML_TMPL = """<!doctype html>
<html><head><meta charset="utf-8">
<title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;
padding:0 1rem;line-height:1.55;color:#222}}
h1,h2,h3,h4{{line-height:1.2}} code,pre{{background:#f4f4f6;
border-radius:4px}} code{{padding:.1em .35em}}
pre{{padding:.8em;overflow-x:auto}} blockquote{{border-left:4px solid
#bbb;margin:0;padding:.2em 1em;color:#555}}
table{{border-collapse:collapse}} th,td{{border:1px solid #ccc;
padding:.35em .7em}} th{{background:#f0f0f4}}
hr{{border:0;border-top:2px solid #ddd;margin:1.4em 0}}
</style></head><body>
{body}
</body></html>
"""


def markdown_to_html(md, title="Document"):
    """Full standalone HTML export of the markdown text."""
    parts = []
    for b in parse_blocks(md):
        k = b["type"]
        if k == "heading":
            lvl = max(1, min(6, int(b.get("level", 1))))
            parts.append("<h%d>%s</h%d>"
                         % (lvl, _spans_html(b["text"]), lvl))
        elif k == "para":
            parts.append("<p>%s</p>" % _spans_html(b["text"]))
        elif k == "code":
            lang = b.get("lang") or ""
            cls = ' class="language-%s"' % _esc(lang) if lang else ""
            parts.append("<pre><code%s>%s</code></pre>"
                         % (cls, _esc(b.get("text", ""))))
        elif k == "quote":
            parts.append("<blockquote><p>%s</p></blockquote>"
                         % _spans_html(b.get("text", "")))
        elif k in ("ulist", "olist"):
            tag = "ul" if k == "ulist" else "ol"
            items = "".join("<li>%s</li>" % _spans_html(it)
                            for it in b.get("items", []))
            parts.append("<%s>%s</%s>" % (tag, items, tag))
        elif k == "table":
            head = "".join("<th>%s</th>" % _spans_html(c)
                           for c in b.get("header", []))
            body_rows = "".join(
                "<tr>%s</tr>" % "".join("<td>%s</td>" % _spans_html(c)
                                        for c in row)
                for row in b.get("rows", []))
            parts.append("<table><thead><tr>%s</tr></thead>"
                         "<tbody>%s</tbody></table>" % (head, body_rows))
        elif k == "hr":
            parts.append("<hr>")
    return _HTML_TMPL.format(title=_esc(title or "Document"),
                             body="\n".join(parts))


SAMPLE_DOC = """# DS2 Markdown Preview

Type markdown on the **left**, see it rendered on the *right* —
live, with a ~~tiny~~ debounced re-render. Everything is a
zero-dependency engine: `parse_blocks` + `inline_spans`.

## What renders?

- ATX headings `#` through `######`
- **bold**, *italic*, ~~strikethrough~~, `` `inline code` ``
- fenced code blocks with a language label
- blockquotes, ordered + unordered lists
- pipe tables and [links](https://github.com/DXN1-termux)

> Everything that can be simplified should be simplified —
> but not simpler.

1. Write
2. Preview
3. Export the HTML

| key | action |
| --- | ------ |
| F5  | re-render now |
| Ctrl+E | export HTML |

```python
def hello(name):
    return f"Hello, {name}!"
```

---

Happy writing!
"""


class MarkdownPreview(tk.Toplevel):
    """Dual-pane markdown editor + live rendered preview."""

    def __init__(self, parent, theme, text="", path=""):
        super().__init__(parent)
        self.theme = theme or {}
        self.path = path or ""
        self._render_job = None
        self._render_ms = 0

        t = self.theme
        self.title("Markdown Preview — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("980x640")
        # DS2 v2.63 — width accounting round five: once the
        # build settles, open no narrower (or shorter) than
        # what it actually packed (the 980x640 default is the
        # floor)
        from . import geom as _geom
        self.after_idle(lambda: _geom.fit_to_content(
            self, 980, 640))
        self.minsize(640, 420)
        try:
            self.transient(parent)
        except Exception:
            pass

        self._build_toolbar()
        self._build_panes()
        self._build_statusbar()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<F5>", lambda _e: self.render_now())

        self.src.insert("1.0", text or "")
        self.render_now()

    # ------------------------------------------------------------ UI
    def _build_toolbar(self):
        t = self.theme
        bar = tk.Frame(self, bg=t.get("header", "#242432"))
        bar.pack(fill=tk.X)

        def _btn(label, cmd):
            return tk.Button(bar, text=label, command=cmd,
                             bg=t.get("button_bg", "#2c2c3c"),
                             fg=t.get("text", "#e8e8f0"),
                             activebackground=t.get("select", "#31445c"),
                             activeforeground=t.get("text", "#e8e8f0"),
                             relief=tk.FLAT, padx=10, pady=3,
                             cursor="hand2")

        _btn("Load file…", self.load_file).pack(
            side=tk.LEFT, padx=(10, 4), pady=6)
        _btn("Sample", self.load_sample).pack(
            side=tk.LEFT, padx=4, pady=6)
        _btn("Re-render (F5)", self.render_now).pack(
            side=tk.LEFT, padx=4, pady=6)
        tk.Label(bar, text="│", bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#555")).pack(side=tk.LEFT,
                                                      padx=2)
        _btn(tr("markprev.copy_html"), self.copy_html).pack(
            side=tk.LEFT, padx=4, pady=6)
        _btn(tr("markprev.export_html"), self.export_html).pack(
            side=tk.LEFT, padx=4, pady=6)

    def _build_panes(self):
        t = self.theme
        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True)

        self.src = tk.Text(body, wrap="word", undo=True,
                           bg=t.get("editor_bg", "#1a1a24"),
                           fg=t.get("editor_fg", "#e8e8f0"),
                           insertbackground=t.get("text", "#e8e8f0"),
                           relief=tk.FLAT, padx=10, pady=8,
                           font=("Courier", 11))
        self.view = tk.Text(body, wrap="word", state=tk.DISABLED,
                            bg=t.get("bg", "#16161e"),
                            fg=t.get("text", "#e8e8f0"),
                            relief=tk.FLAT, padx=14, pady=10)
        self.src.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        try:
            base = tkfont.nametofont("TkDefaultFont").copy()
        except Exception:
            base = None

        def _mk(tag, **kw):
            try:
                self.view.tag_configure(tag, **kw)
            except Exception:
                pass

        _mk("h1", font=(base.actual("family") if base else "TkDefaultFont",
                        20, "bold"), spacing1=8, spacing3=8)
        _mk("h2", font=(base.actual("family") if base else "TkDefaultFont",
                        16, "bold"), spacing1=8, spacing3=6)
        _mk("h3", font=(base.actual("family") if base else "TkDefaultFont",
                        13, "bold"), spacing1=6, spacing3=4)
        _mk("h4", font=(base.actual("family") if base else "TkDefaultFont",
                        12, "bold", "italic"), spacing1=4, spacing3=3)
        _mk("h5", font=(base.actual("family") if base else "TkDefaultFont",
                        11, "bold"), foreground=t.get("text_muted", "#999"))
        _mk("h6", font=(base.actual("family") if base else "TkDefaultFont",
                        10, "bold"), foreground=t.get("text_muted", "#777"))
        _mk("bold", font=("TkDefaultFont", 10, "bold"))
        _mk("italic", font=("TkDefaultFont", 10, "italic"))
        _mk("strike", overstrike=True)
        _mk("icode", font=("Courier", 10),
            background=t.get("select", "#2c2c3c"))
        _mk("link", foreground=t.get("cyan", "#56b6c2"), underline=True)
        _mk("quote", foreground=t.get("text_muted", "#9aa"),
            lmargin1=16, lmargin2=16, spacing1=4, spacing3=4)
        _mk("code", font=("Courier", 10),
            background=t.get("editor_bg", "#1a1a24"),
            foreground=t.get("green", "#98c379"),
            lmargin1=12, lmargin2=12, spacing1=2)
        _mk("lang", font=("Courier", 9, "italic"),
            foreground=t.get("text_muted", "#777"))
        _mk("li", lmargin1=18, lmargin2=18)
        _mk("hr", foreground=t.get("text_muted", "#555"),
            justify="center", spacing1=8, spacing3=8)
        _mk("th", font=("TkDefaultFont", 10, "bold"))

        self.src.bind("<KeyRelease>", self._schedule_render)

    def _build_statusbar(self):
        t = self.theme
        self.status = tk.Label(self, anchor="w",
                               bg=t.get("header", "#242432"),
                               fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------- actions
    def load_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self, title="Open markdown file",
            filetypes=[("Markdown", "*.md *.markdown *.mkd *.rst"),
                       ("Text", "*.txt"), ("All", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as exc:  # noqa: BLE001
            self._flash("cannot read %s — %s" % (path, exc))
            return
        self.path = path
        self.src.delete("1.0", "end")
        self.src.insert("1.0", text)
        self.render_now()

    def load_sample(self):
        self.src.delete("1.0", "end")
        self.src.insert("1.0", SAMPLE_DOC)
        self.render_now()

    def copy_html(self):
        html = markdown_to_html(self.src.get("1.0", "end-1c"),
                                title=self._title())
        try:
            self.clipboard_clear()
            self.clipboard_append(html)
            self._flash("HTML copied — %d chars" % len(html))
        except Exception:  # noqa: BLE001
            self._flash("clipboard unavailable")

    def export_html(self):
        from tkinter import filedialog
        html = markdown_to_html(self.src.get("1.0", "end-1c"),
                                title=self._title())
        name = (self.path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                if self.path else "document")
        stem = name.rsplit(".", 1)[0] or "document"
        path = filedialog.asksaveasfilename(
            parent=self, title="Export HTML",
            defaultextension=".html",
            initialfile=stem + ".html",
            filetypes=[("HTML", "*.html"), ("All", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self._flash("exported %s" % path)
        except Exception as exc:  # noqa: BLE001
            self._flash("export failed — %s" % exc)

    def render_now(self):
        """Render the full preview (called by hand or after debounce)."""
        import time
        t0 = time.perf_counter()
        md = self.src.get("1.0", "end-1c")
        self.view.configure(state=tk.NORMAL)
        self.view.delete("1.0", "end")
        for b in parse_blocks(md):
            self._insert_block(b)
        self.view.configure(state=tk.DISABLED)
        self._render_ms = (time.perf_counter() - t0) * 1000.0
        words = len(md.split())
        lines = md.count("\n") + 1 if md else 0
        blocks = len(parse_blocks(md))
        self._flash("%d words · %d lines · %d blocks · render %.1f ms"
                    % (words, lines, blocks, self._render_ms))

    # ------------------------------------------------------- helpers
    def _insert_block(self, b):
        view = self.view
        k = b["type"]
        if k == "heading":
            lvl = max(1, min(6, int(b.get("level", 1))))
            view.insert("end", b["text"] + "\n", "h%d" % lvl)
        elif k == "para":
            self._insert_spans(b["text"], base_tags=())
            view.insert("end", "\n")
        elif k == "code":
            if b.get("lang"):
                view.insert("end", "▸ %s\n" % b["lang"], ("lang", "code"))
            view.insert("end", b.get("text", "") + "\n", "code")
        elif k == "quote":
            view.insert("end", "▏ " + b.get("text", "") + "\n",
                        ("quote", "italic"))
        elif k in ("ulist", "olist"):
            bullet = "•" if k == "ulist" else None
            for n, item in enumerate(b.get("items", []), 1):
                mark = ("%d." % n) if bullet is None else bullet
                view.insert("end", "  %s  " % mark, "li")
                self._insert_spans(item, base_tags=("li",))
                view.insert("end", "\n")
            view.insert("end", "\n")
        elif k == "table":
            header = b.get("header", [])
            rows = b.get("rows", [])
            widths = [len(c) for c in header] or [1]
            for row in rows:
                for ci, cell in enumerate(row):
                    if ci < len(widths):
                        widths[ci] = max(widths[ci], len(cell))
            line_h = "  ".join(c.ljust(widths[i])
                               for i, c in enumerate(header))
            view.insert("end", line_h + "\n", "th")
            view.insert("end", "─" * min(78, max(12, len(line_h))) + "\n",
                        "hr")
            for row in rows:
                line_r = "  ".join(
                    (row[i] if i < len(row) else "").ljust(widths[i])
                    for i in range(len(widths)))
                view.insert("end", line_r + "\n")
            view.insert("end", "\n")
        elif k == "hr":
            view.insert("end", "─" * 60 + "\n", "hr")

    def _insert_spans(self, text, base_tags=()):
        view = self.view
        for kind, val in inline_spans(text):
            tags = base_tags
            if kind == "plain":
                view.insert("end", val, tags)
            elif kind == "code":
                view.insert("end", val, tags + ("icode",))
            elif kind == "bold":
                view.insert("end", val, tags + ("bold",))
            elif kind == "italic":
                view.insert("end", val, tags + ("italic",))
            elif kind == "strike":
                view.insert("end", val, tags + ("strike",))
            else:
                label, url = val
                view.insert("end", label, tags + ("link",))
                view.insert("end", " (%s)" % url, tags + ("lang",))

    def _title(self):
        name = self.path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return name or "Document"

    def _schedule_render(self, _event=None):
        if self._render_job is not None:
            try:
                self.after_cancel(self._render_job)
            except Exception:  # noqa: BLE001
                pass
        self._render_job = self.after(300, self._debounced)

    def _debounced(self):
        self._render_job = None
        try:
            self.render_now()
        except Exception:  # noqa: BLE001 — preview never kills the app
            pass

    def _flash(self, msg):
        try:
            self.status.configure(text=msg)
        except Exception:  # noqa: BLE001
            pass


def open_markdown_preview(parent, theme, text="", path=""):
    """Public opener — palette / menu / terminal entry point."""
    return MarkdownPreview(parent, theme, text=text, path=path)
