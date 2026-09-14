"""DXN1 STUDIO — cheat sheet exporter (DS2 v2.27).

One printable HTML page with every terminal command and keyboard
shortcut the studio knows. The command list is the live
``TERMINAL_HELP`` tuple shared with the terminal's own ``help``
output — zero drift by construction; shortcuts are curated from the
real ``setup_bindings`` table. The engine renders inline-CSS HTML
with @media print rules (open the file in any browser, hit Ctrl+P),
and every function is junk-tolerant: no data, no file permissions —
honest error strings, never exceptions.
"""

import datetime
import os
import tkinter as tk
from tkinter import filedialog

from . import APP_NAME, APP_VERSION, APP_TAGLINE
from .i18n import tr

# ----------------------------------------------------------------- data

# curated from app.setup_bindings() — the real table, shortcuts only
SHORTCUTS = (
    ("F5", "run the current file / project"),
    ("Ctrl+S", "save the current file"),
    ("Ctrl+N / Ctrl+O", "new file / open file"),
    ("Ctrl+W", "close the active tab"),
    ("Ctrl+Tab", "cycle to the next tab"),
    ("Ctrl+K", "command palette — every feature, one keystroke"),
    ("Ctrl+P", "quick open — jump to a file by name"),
    ("Ctrl+F", "find in the current file"),
    ("Ctrl+H", "find and replace"),
    ("Ctrl+G", "jump to a line"),
    ("Ctrl+/", "toggle comment on the selection"),
    ("Ctrl+K (on a line)", "delete the whole line"),
    ("Ctrl+D", "duplicate the current line"),
    ("Alt+Up / Alt+Down", "move the current line up / down"),
    ("Ctrl+Alt+S / D / H / R", "sort A-Z / dedupe / shuffle / reverse lines"),
    ("Ctrl+\\", "toggle split editor view"),
    ("Ctrl+Alt+Z", "toggle zen mode"),
    ("Ctrl+Shift+V", "paste from clipboard history"),
    ("Ctrl+,", "open studio settings"),
    ("Ctrl+= / Ctrl+-", "bigger / smaller editor font"),
)

TIPS = (
    ("palette first", "Ctrl+K opens the command palette — it can reach "
     "every window and command in this sheet by friendly name."),
    ("help in the terminal", "typing `help` (or `?`) prints the same "
     "command list this sheet was generated from."),
    ("print me", "save the HTML and open it in any browser — Ctrl+P "
     "gives a clean two-page reference with zero chrome."),
    ("stay current", "the command list is generated from the running "
     "build, so new sprint features show up automatically."),
)


def default_sections(commands=None):
    """(heading, [(key, description), ...]) — the cheat sheet body.
    ``commands`` overrides the live TERMINAL_HELP (tests, offline)."""
    if commands is None:
        try:
            from .app import TERMINAL_HELP
            commands = TERMINAL_HELP
        except Exception:  # noqa: BLE001 — headless / partial install
            commands = (("help", "print studio commands"),)
    return [
        ("Terminal commands", tuple(commands or ())),
        ("Keyboard shortcuts", SHORTCUTS),
        ("Tips", TIPS),
    ]


def render_text(sections):
    """Plain-text preview for the window and terminal — same content
    as the HTML, readable without a browser. Never raises."""
    out = []
    for heading, rows in (sections or default_sections()):
        out.append("")
        out.append(heading.upper())
        out.append("-" * max(8, len(heading)))
        for key, desc in rows or ():
            out.append("  %-24s %s" % (str(key or "")[:24],
                                       str(desc or "")))
    return "\n".join(out)


# ----------------------------------------------------------------- html

_HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{ --accent: #7c3aed; --ink: #1f2328; --muted: #57606a;
          --line: #d8dee4; --chip-bg: #f6f8fa; }}
  * {{ box-sizing: border-box; }}
  body {{ font: 14px/1.55 -apple-system, "Segoe UI", Roboto, sans-serif;
         color: var(--ink); max-width: 860px; margin: 24px auto;
         padding: 0 20px; }}
  header {{ border-bottom: 3px solid var(--accent); padding-bottom: 12px;
           margin-bottom: 20px; }}
  h1 {{ margin: 0; font-size: 26px; letter-spacing: -0.5px; }}
  h1 span {{ color: var(--accent); }}
  .meta {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
  h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: 1px;
       color: var(--accent); border-bottom: 1px solid var(--line);
       padding-bottom: 4px; margin: 26px 0 8px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid var(--line);
       vertical-align: top; }}
  td.k {{ white-space: nowrap; width: 1%; }}
  kbd {{ font: 12px/1.4 "SFMono-Regular", Consolas, monospace;
        background: var(--chip-bg); border: 1px solid var(--line);
        border-bottom-width: 2px; border-radius: 4px; padding: 1px 6px;
        white-space: nowrap; }}
  footer {{ margin-top: 28px; color: var(--muted); font-size: 11px;
           border-top: 1px solid var(--line); padding-top: 8px; }}
  @media print {{
    body {{ margin: 0; font-size: 11px; max-width: none; }}
    h2 {{ margin-top: 14px; }}
    a {{ text-decoration: none; color: inherit; }}
  }}
</style>
</head>
<body>
<header>
  <h1>{app} <span>cheat sheet</span></h1>
  <div class="meta">{meta}</div>
</header>
"""


def build_html(sections, title=None, meta_extra=""):
    """Render the cheat sheet as standalone print-friendly HTML.
    Inline CSS only — one file, no dependencies, junk-tolerant."""
    title = str(title or ("%s cheat sheet" % APP_NAME))
    today = ""
    try:
        today = datetime.date.today().isoformat()
    except Exception:
        pass
    meta = "v%s · %s · generated %s" % (APP_VERSION, APP_TAGLINE, today)
    if meta_extra:
        meta += " · " + str(meta_extra)
    parts = [_HTML_HEAD.format(title=_esc(title), app=_esc(APP_NAME),
                               meta=_esc(meta))]
    for heading, rows in (sections or default_sections()):
        parts.append("<h2>%s</h2>\n<table>" % _esc(str(heading)))
        for key, desc in rows or ():
            parts.append('<tr><td class="k"><kbd>%s</kbd></td>'
                         '<td>%s</td></tr>'
                         % (_esc(str(key or "")),
                            _esc(str(desc or ""))))
        parts.append("</table>")
    parts.append('<footer>%s · printed from the cheat sheet '
                 'exporter</footer>\n</body>\n</html>\n' % _esc(APP_NAME))
    return "\n".join(parts)


def _esc(text):
    """Minimal HTML escaping — & < > only; never raises."""
    return (str(text or "").replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def save_html(html, path):
    """Write the HTML to ``path``; returns (path, error). Junk paths
    and unwritable targets give an honest error, never an exception."""
    try:
        if not path or not str(path).strip():
            return None, "no path given"
        path = os.path.abspath(os.path.expanduser(str(path)))
        if os.path.isdir(path):
            return None, "path is a directory: %s" % path
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            return None, "folder does not exist: %s" % d
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        return path, None
    except Exception as exc:  # noqa: BLE001 — honest error string
        return None, str(exc) or "write failed"


# ----------------------------------------------------------------- window

class CheatSheet(tk.Toplevel):
    """Cheat sheet window: preview, save HTML, open in browser."""

    def __init__(self, parent, theme, initial="", commands=None):
        super().__init__(parent)
        self.theme = theme or {}
        t = self.theme
        self.commands = commands
        self.last_path = initial or ""

        self.title("Cheat Sheet — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("720x520")
        self.minsize(560, 400)
        try:
            self.transient(parent)
        except Exception:
            pass

        top = tk.Frame(self, bg=t.get("header", "#242432"))
        top.pack(fill=tk.X)
        tk.Label(top, text="cheat sheet — every command & shortcut, "
                           "print-ready",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 11, "bold")).pack(
            side=tk.LEFT, padx=10, pady=8)

        self.preview = tk.Text(self, wrap="word", relief=tk.FLAT,
                               bg=t.get("editor_bg", "#1a1a24"),
                               fg=t.get("text", "#e8e8f0"),
                               insertbackground=t.get("text", "#fff"),
                               padx=10, pady=8)
        self.preview.pack(fill=tk.BOTH, expand=True,
                          padx=10, pady=(10, 0))
        self.preview.insert("1.0", render_text(default_sections(
            self.commands)))
        self.preview.configure(state=tk.DISABLED)

        bottom = tk.Frame(self, bg=t.get("bg", "#16161e"))
        bottom.pack(fill=tk.X)
        self.status = tk.Label(
            bottom, text=tr("cheatsheet.save_hint"), anchor="w",
            bg=t.get("bg", "#16161e"),
            fg=t.get("text_muted", "#8a8a9a"))
        self.status.pack(side=tk.LEFT, padx=10, pady=6)
        for label, cmd in ((tr("cheatsheet.save_html"), self._save_as),
                           (tr("cheatsheet.open_browser"),
                            self._open_browser),
                           (tr("cheatsheet.copy_html"), self._copy_html)):
            tk.Button(bottom, text=label, relief=tk.FLAT,
                      bg=t.get("button", "#2a2a3a"),
                      fg=t.get("text", "#e8e8f0"),
                      activebackground=t.get("button_hover", "#33334a"),
                      command=cmd).pack(side=tk.RIGHT, padx=(0, 6),
                                        pady=4)

        # v2.49 — real keys + the honest door sign
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-C>", lambda e: self._copy_html())
        self.bind("<Control-s>", lambda e: self._save_as())
        from . import hints
        self.hintbar = hints.hint_bar(
            self, self.theme,
            pairs=(("Ctrl+Shift+C", "copy HTML"),
                   ("Ctrl+S", "save HTML")),
            notes=("print-ready — opens in any browser"))

    # ------------------------------------------------------------ actions
    def _html(self):
        return build_html(default_sections(self.commands))

    def _write_to(self, path):
        """Save through the engine and report honestly in the status."""
        path, err = save_html(self._html(), path)
        if err:
            self.status.configure(text="save failed — %s" % err,
                                  fg=self.theme.get("error", "#f85149"))
            return None
        self.last_path = path
        self.status.configure(
            text="saved — %s" % path,
            fg=self.theme.get("success", "#3fb950"))
        return path

    def _save_as(self):
        try:
            path = filedialog.asksaveasfilename(
                parent=self, title="Save cheat sheet",
                defaultextension=".html",
                initialfile="dxn1-studio-cheatsheet.html",
                filetypes=[("HTML", "*.html"), ("All files", "*")])
        except Exception:  # noqa: BLE001 — dialog optional
            path = None
        if path:
            self._write_to(path)

    def _open_browser(self):
        import webbrowser
        path = self.last_path
        if not path or not os.path.isfile(path):
            import tempfile
            try:
                fd, tmp = tempfile.mkstemp(
                    prefix="dxn1-cheatsheet-", suffix=".html")
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(self._html())
            except Exception as exc:  # noqa: BLE001
                self.status.configure(text="open failed — %s" % exc)
                return
            path = tmp
            self.last_path = tmp
        try:
            webbrowser.open("file://%s" % path)
            self.status.configure(text="opened in browser — %s" % path)
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text="open failed — %s" % exc)

    def _copy_html(self):
        try:
            html = self._html()
            self.clipboard_clear()
            self.clipboard_append(html)
            self.status.configure(text="HTML copied — %d lines"
                                       % len(html.splitlines()))
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text="copy failed — %s" % exc)

    def refresh(self):
        self.preview.configure(state=tk.NORMAL)
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", render_text(
            default_sections(self.commands)))
        self.preview.configure(state=tk.DISABLED)


def open_cheatsheet(parent, theme, initial="", commands=None):
    """Public entry — open the cheat sheet window."""
    return CheatSheet(parent, theme, initial=initial, commands=commands)
