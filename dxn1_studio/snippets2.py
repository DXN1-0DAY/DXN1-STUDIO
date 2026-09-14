"""DXN1 STUDIO — snippet engine v2 (DS2 v1.5).

Type ``def`` + Tab, get a full function skeleton with the cursor
waiting at the first ``$1`` tabstop. Snippets support:

- positional tabstops ``$1 $2 $3…`` (Tab cycles forward, Shift+Tab back)
- named variables with defaults ``${name:default}``
- builtin variables ``$FILENAME``, ``$CLIPBOARD``, ``$DATE``, ``$TIME``
- per-language packs (python, javascript, html…) plus user snippets
  stored in ``~/.dxn1-studio/snippets.json``
- import/export as JSON so snippet packs can be shared

The expansion happens inside the editor's own undo cycle (one insert),
so a mistyped snippet is a single Ctrl+Z away.
"""

import json
import os
import re
import time
import tkinter as tk

from .theme import FONT_UI, FONT_MONO

STORE_DIR = os.path.join(os.path.expanduser("~"), ".dxn1-studio")
STORE_PATH = os.path.join(STORE_DIR, "snippets.json")

TOKEN_RE = re.compile(
    r"\$\{(?P<name>[A-Za-z_]\w*)(?::(?P<default>[^}]*))?\}"
    r"|\$\{(?P<pos>\d+)\}"
    r"|\$(?P<pos2>\d+)"
    r"|\$(?P<builtin>FILENAME|DATE|TIME|CLIPBOARD)")


def builtin_value(name, text_widget=None):
    now = time.localtime()
    if name == "FILENAME":
        try:
            return os.path.basename(
                text_widget.winfo_toplevel().title().split("—")[-1].strip()
                or "untitled")
        except Exception:
            return "untitled"
    if name == "DATE":
        return time.strftime("%Y-%m-%d", now)
    if name == "TIME":
        return time.strftime("%H:%M", now)
    if name == "CLIPBOARD":
        try:
            return text_widget.clipboard_get()
        except (tk.TclError, Exception):
            return ""
    return ""


def parse_snippet(body):
    """Split a snippet body into (segments, tabstops).

    ``segments`` is a list of ``(literal_text,)`` /
    ``("<var>", value)`` / ``("<stop>", index)`` tuples, and
    ``tabstops`` maps stop number → (segment_index, offset) for the
    first occurrence, so the cursor can hop through them.
    """
    segments = []
    tabstops = {}
    pos = 0
    for match in TOKEN_RE.finditer(body):
        if match.start() > pos:
            segments.append((body[pos:match.start()],))
        if match.group("builtin"):
            segments.append(("<var>", match.group("builtin")))
        elif match.group("pos") or match.group("pos2"):
            stop = int(match.group("pos") or match.group("pos2"))
            tabstops.setdefault(stop, len(segments))
            segments.append(("<stop>", stop))
        else:
            name = match.group("name")
            default = match.group("default") or ""
            segments.append(("<var>", default if default else name))
        pos = match.end()
    if pos < len(body):
        segments.append((body[pos:],))
    return segments, tabstops


def render_snippet(body, text_widget=None):
    """Expand a snippet body → (final_text, first_stop_char_offset).

    Named variables render as their default text; only true builtins
    (FILENAME, DATE, TIME, CLIPBOARD) are resolved dynamically.
    """
    segments, tabstops = parse_snippet(body)
    out = []
    offset = 0
    first_stop_offset = None
    builtins = {"FILENAME", "DATE", "TIME", "CLIPBOARD"}
    for i, seg in enumerate(segments):
        if seg[0] == "<var>":
            value = builtin_value(seg[1], text_widget) \
                if seg[1] in builtins else seg[1]
        elif seg[0] == "<stop>":
            value = ""
            if seg[1] == 1 and first_stop_offset is None:
                first_stop_offset = offset
        else:
            value = seg[0]
        out.append(value)
        offset += len(value)
    return "".join(out), first_stop_offset or 0


def default_pack(lang):
    """Built-in starter snippets per language (always available)."""
    packs = {
        "python": {
            "def": "def ${name:func}(${args}):\n    ${pass:pass}\n",
            "class": "class ${Name:MyClass}:\n"
                     "    def __init__(self${args}):\n"
                     "        ${pass:pass}\n",
            "main": 'if __name__ == "__main__":\n    ${main}\n',
            "for": "for ${i} in ${iter:range(n)}:\n    ${body}\n",
            "try": "try:\n    ${body}\nexcept ${Exc:Exception} as e:\n"
                   "    ${print:print(e)}\n",
            "with": "with open(${path}) as f:\n    ${body}\n",
        },
        "javascript": {
            "fn": "function ${name:fn}(${args}) {\n    ${body}\n}\n",
            "arrow": "const ${name:fn} = (${args}) => {\n    ${body}\n};\n",
            "log": "console.log(${msg});\n",
            "forof": "for (const ${item} of ${coll}) {\n    ${body}\n}\n",
            "fetch": "fetch(${url})\n"
                     "  .then(r => r.json())\n"
                     "  .then(${data} => ${body})\n"
                     "  .catch(console.error);\n",
        },
        "html": {
            "div": '<div class="${cls}">\n    ${body}\n</div>\n',
            "link": '<link rel="stylesheet" href="${href}">\n',
            "script": '<script src="${src}"></script>\n',
            "img": '<img src="${src}" alt="${alt}">\n',
        },
        "markdown": {
            "code": "```${lang}\n${body}\n```\n",
            "table": "| ${h1} | ${h2} |\n|---|---|\n| ${a} | ${b} |\n",
            "todo": "- [ ] ${task}\n",
        },
    }
    return packs.get(lang, {})


class SnippetEngine:
    """Language-aware snippet store + Tab expansion for a Tk Text."""

    def __init__(self, text_widget, language_for=None):
        self.text = text_widget
        self.language_for = language_for or (lambda path: "")
        self.user = self._load_user()

    # ------------------------------------------------------------ store
    @staticmethod
    def _load_user():
        try:
            with open(STORE_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_user(user):
        try:
            os.makedirs(STORE_DIR, exist_ok=True)
            with open(STORE_PATH, "w", encoding="utf-8") as fh:
                json.dump(user, fh, indent=1)
        except OSError:
            pass

    def pack_for(self, lang):
        pack = dict(default_pack(lang))
        pack.update(self.user.get(lang, {}))
        return pack

    def add(self, lang, prefix, body):
        user = self.user
        user.setdefault(lang, {})[prefix] = body
        self.save_user(user)

    def export_json(self, dest):
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(self.user, fh, indent=1)

    def import_json(self, src):
        with open(src, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            for lang, pack in data.items():
                if isinstance(pack, dict):
                    self.user.setdefault(lang, {}).update(pack)
            self.save_user(self.user)

    # -------------------------------------------------------- expansion
    def candidate(self):
        """Snippet matching the word before the cursor, or None."""
        try:
            insert = self.text.index(tk.INSERT)
            line = insert.split(".")[0]
            line_text = self.text.get(f"{line}.0", insert)
            match = re.search(r"(\w+)$", line_text)
            if not match:
                return None
            prefix = match.group(1)
            lang = self.language_for(
                getattr(self.text, "_ds2_path", "") or "")
            pack = self.pack_for(lang)
            body = pack.get(prefix)
            if body:
                return prefix, body
        except tk.TclError:
            pass
        return None

    def expand(self):
        """Expand the snippet under the cursor. Returns True on success."""
        cand = self.candidate()
        if not cand:
            return False
        prefix, body = cand
        rendered, stop_offset = render_snippet(body, self.text)
        insert = self.text.index(tk.INSERT)
        start = f"{insert.split('.')[0]}.{max(0, int(insert.split('.')[1]) - len(prefix))}"
        try:
            self.text.delete(start, insert)
            self.text.insert(tk.INSERT, rendered)
            if stop_offset:
                self.text.mark_set(tk.INSERT, f"{start}+{stop_offset}c")
            try:
                self.text.see(tk.INSERT)
            except tk.TclError:
                pass
            return True
        except tk.TclError:
            return False


def language_of(path):
    """Tiny language mapper — mirrors the editor's highlighter needs."""
    ext = os.path.splitext(path or "")[1].lower()
    return {".py": "python", ".js": "javascript", ".mjs": "javascript",
            ".ts": "javascript", ".jsx": "javascript", ".tsx": "javascript",
            ".html": "html", ".htm": "html", ".md": "markdown",
            ".css": "css", ".json": "json"}.get(ext, "")
