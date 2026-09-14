"""DXN1 STUDIO — AI quick actions (DS2 v1.6).

Select code, get superpowers: Explain, Refactor, Add docstring, Write
tests, Fix bugs, Add type hints, Comment. Each action streams the
agent's answer into a themed result window with Copy / Insert /
Replace-selection buttons — so the answer is one keystroke away from
becoming your code.

Runs on the same brain the studio already has configured (free keyless
cloud, GitHub Models, BYOK…). Everything streams on a worker thread and
is marshalled back to the UI through a queue — the editor never blocks.
"""

import queue
import threading
import tkinter as tk

from .theme import FONT_UI, FONT_MONO
from . import hints
from . import llm

ACTIONS = {
    "explain": {
        "label": "Explain this code",
        "icon": "◈",
        "danger": False,
        "prompt": "Explain what this {lang} code does, step by step. "
                  "Be concrete and concise — no filler. Point out any "
                  "surprising behaviour.",
    },
    "refactor": {
        "label": "Refactor",
        "icon": "⚙",
        "danger": False,
        "prompt": "Refactor this {lang} code for clarity, naming and "
                  "structure. Keep behaviour identical. Return the full "
                  "refactored code in one fenced block, then a short "
                  "bullet list of what changed.",
    },
    "docstring": {
        "label": "Add docstring",
        "icon": "▤",
        "prompt": "Write a high-quality docstring/comment for this "
                  "{lang} code and return the code with it added. "
                  "Explain args, returns and side effects.",
    },
    "tests": {
        "label": "Write tests",
        "icon": "✓",
        "prompt": "Write thorough but focused tests for this {lang} "
                  "code. Cover normal cases, edge cases and failure "
                  "modes. Return one fenced code block with the tests.",
    },
    "fix": {
        "label": "Find & fix bugs",
        "icon": "⚑",
        "prompt": "Find bugs, edge cases and risky patterns in this "
                  "{lang} code. Return the corrected code in one fenced "
                  "block, then briefly list each bug you fixed.",
    },
    "types": {
        "label": "Add type hints",
        "icon": "ƒ",
        "prompt": "Add complete type hints/annotations to this {lang} "
                  "code. Return the fully annotated code in one fenced "
                  "block.",
    },
    "optimize": {
        "label": "Optimize",
        "icon": "⚡",
        "prompt": "Optimize this {lang} code for speed and memory where "
                  "it matters. Return the improved code in one fenced "
                  "block and explain the wins briefly.",
    },
}


def detect_language(filename):
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return {
        "py": "Python", "js": "JavaScript", "ts": "TypeScript",
        "jsx": "React (JSX)", "tsx": "React (TSX)", "html": "HTML",
        "css": "CSS", "go": "Go", "rs": "Rust", "java": "Java",
        "c": "C", "cpp": "C++", "sh": "Shell", "md": "Markdown",
        "json": "JSON", "yaml": "YAML", "yml": "YAML",
    }.get(ext, "")


def build_prompt(action_id, code, filename):
    spec = ACTIONS[action_id]
    lang = detect_language(filename) or "the given"
    return spec["prompt"].format(lang=lang) + (
        f"\n\nFile: {filename}\n\n```\n{code}\n```")


# ------------------------------------------------------------------ stream
class StreamToText:
    """Marshal streamed chunks from a worker thread into a Text widget."""

    def __init__(self, widget, on_done=None, window=None):
        self.widget = widget
        self.window = window
        self.q = queue.Queue()
        self.done = False
        self.on_done = on_done
        self._poll()

    def feed(self, chunk):
        self.q.put(("chunk", chunk))

    def finish(self):
        self.q.put(("done", None))

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "chunk" and payload:
                    self.widget.insert(tk.END, payload)
                    try:
                        self.widget.see(tk.END)
                    except tk.TclError:
                        pass
                elif kind == "done":
                    self.done = True
                    if self.on_done:
                        try:
                            self.on_done()
                        except Exception:
                            pass
                    return
        except queue.Empty:
            pass
        alive = True
        if self.window is not None:
            try:
                alive = bool(self.window.winfo_exists())
            except tk.TclError:
                alive = False
        if alive and not self.done:
            self.widget.after(45, self._poll)


def extract_code_blocks(text):
    """Pull fenced code blocks out of an answer (for Insert/Replace).

    The first line of a fenced block is a language tag only when it is
    a single bare word (``python``, ``js``) — anything else is code.
    """
    blocks = []
    parts = text.split("```")
    for i in range(1, len(parts), 2):
        block = parts[i]
        if "\n" in block:
            first, rest = block.split("\n", 1)
            stripped = first.strip()
            if not stripped:
                block = rest                      # fence had no lang tag
            elif len(stripped.split()) == 1 and "(" not in stripped \
                    and "=" not in stripped and "." not in stripped:
                block = rest                      # bare language word
        if block.strip():
            blocks.append(block.rstrip() + "\n")
    return blocks


# ------------------------------------------------------------------- view
class ResultWindow(tk.Toplevel):
    """Streaming answer window with code-aware actions."""

    def __init__(self, parent, theme, title, action_label, app=None,
                 code=None, on_log=None):
        super().__init__(parent)
        self.t = theme
        self.app = app
        self.code = code
        self.on_log = on_log or (lambda msg: None)
        self.title(title)
        self.configure(bg=self.t["bg"])
        self.geometry("760x560")
        self.minsize(480, 340)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build(action_label)
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            w, h = 760, 560
            x = max(0, (self.winfo_screenwidth() - w) // 2)
            y = max(0, (self.winfo_screenheight() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self, action_label):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text=f"⚡ {action_label}", bg=t["header"],
                 fg=t["text"], font=(FONT_UI, 11, "bold")).pack(
            side=tk.LEFT, padx=14)
        self.model_lbl = tk.Label(bar, text="", bg=t["header"],
                                  fg=t["text_muted"], font=(FONT_MONO, 8))
        self.model_lbl.pack(side=tk.LEFT, padx=8)
        wrap = tk.Frame(self, bg=t["bg"])
        wrap.pack(fill=tk.BOTH, expand=True)
        self.text = tk.Text(wrap, bg=t["editor"], fg=t["text"],
                            insertbackground=t["text"], relief=tk.FLAT,
                            font=(FONT_MONO, 10), wrap=tk.WORD,
                            highlightthickness=0, padx=14, pady=12,
                            spacing1=2, spacing3=2)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(wrap, command=self.text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=sb.set)
        self.text.tag_configure("muted", foreground=t["text_muted"])

        btns = tk.Frame(self, bg=t["statusbar"], height=46)
        btns.pack(fill=tk.X, side=tk.BOTTOM)
        btns.pack_propagate(False)
        self._btn(btns, "⧉ Copy", self._copy)
        if self.code is not None:
            self._btn(btns, "↤ Replace selection", self._replace_sel)
            self._btn(btns, "↧ Insert below", self._insert_below)
        self._btn(btns, "Close", self.destroy)
        self.status = tk.Label(btns, text="streaming…", bg=t["statusbar"],
                               fg=t["text_muted"], font=(FONT_UI, 8))
        self.status.pack(side=tk.RIGHT, padx=12)

        # keys first advertised by the bar below (v2.50 wave 3)
        self.bind("<Control-C>", lambda _e: self._copy())
        pairs = [("Ctrl+Shift+C", "copy answer")]
        if self.code is not None:
            self.bind("<Control-r>", lambda _e: self._replace_sel())
            self.bind("<Control-I>", lambda _e: self._insert_below())
            pairs += [("Ctrl+R", "replace selection"),
                      ("Ctrl+Shift+I", "insert below")]
        hints.hint_bar(self, t, pairs=pairs, before=btns)

    def _btn(self, parent, text, cmd):
        b = tk.Label(parent, text=text, bg=self.t["card"],
                     fg=self.t["text"], font=(FONT_UI, 9, "bold"),
                     cursor="hand2", padx=12, pady=6)
        b.pack(side=tk.LEFT, padx=(10, 0), pady=6)
        b.bind("<Button-1>", lambda e: cmd())

    def attach_stream(self, backend, messages, should_stop=None):
        self.stream = StreamToText(self.text, on_done=self._done,
                                   window=self)

        def worker():
            try:
                backend.chat_stream(messages, self.stream.feed,
                                    should_stop=should_stop)
            except Exception as exc:  # streaming refused — plain call
                try:
                    answer = backend.chat(messages)
                    self.stream.feed(answer)
                except Exception as exc2:
                    self.stream.feed(f"\n\n[brain trouble: {exc2}]")
            finally:
                self.stream.finish()

        threading.Thread(target=worker, daemon=True).start()
        try:
            self.model_lbl.config(text=str(getattr(backend, "display",
                                                   "") or ""))
        except Exception:
            pass

    def _full_text(self):
        try:
            return self.text.get("1.0", "end-1c")
        except tk.TclError:
            return ""

    def _done(self):
        self.status.config(text="done ✓")
        self.on_log(f"quick action finished ({len(self._full_text())} chars)")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self._full_text())
        self.status.config(text="copied ✓")

    def _last_code_block(self):
        blocks = extract_code_blocks(self._full_text())
        return blocks[-1] if blocks else None

    def _replace_sel(self):
        block = self._last_code_block()
        if not block or self.app is None or self.code is None:
            self.status.config(text="no code block to insert")
            return
        try:
            text = self.app.editor.text
            try:
                text.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            text.insert(tk.INSERT, block)
            self.status.config(text="replaced ✓")
            self.on_log("quick action: replaced selection")
        except tk.TclError:
            self.status.config(text="editor unavailable")

    def _insert_below(self):
        block = self._last_code_block()
        if not block or self.app is None:
            self.status.config(text="no code block to insert")
            return
        try:
            text = self.app.editor.text
            text.insert(tk.INSERT, "\n" + block)
            self.status.config(text="inserted ✓")
            self.on_log("quick action: inserted code")
        except tk.TclError:
            self.status.config(text="editor unavailable")


# ------------------------------------------------------------------- api
def run_action(app, action_id, on_log=None):
    """Run a quick action on the current editor selection.

    Safe to call from the palette / menus / keybindings: shows a toast
    when there is nothing selected and never raises.
    """
    spec = ACTIONS.get(action_id)
    if spec is None:
        return
    on_log = on_log or (lambda msg: None)
    try:
        text = app.editor.text
        try:
            code = text.get("sel.first", "sel.last")
        except tk.TclError:
            code = ""
        if not code.strip():
            try:
                app.toast("Select some code first — then run the action.")
            except Exception:
                pass
            return
        filename = getattr(app.editor, "path", "") or "untitled"
        window = ResultWindow(app.root, app.theme,
                              f"{spec['icon']} {spec['label']}",
                              spec["label"], app=app, code=code,
                              on_log=on_log)
        messages = [
            {"role": "system", "content":
             "You are DXN1 Agents, the built-in assistant of DXN1 STUDIO. "
             "Answer with markdown; put rewritten code in fenced blocks."},
            {"role": "user", "content":
             build_prompt(action_id, code, filename)},
        ]
        backend = llm.build_backend(app.config)
        if backend is None:
            window.text.insert(
                tk.END, "No AI brain configured.\n\n"
                        "Settings → DXN1 Agents lets you connect the free "
                        "cloud brain (no account needed) in about a minute.")
            window.status.config(text="no backend")
            return
        window.attach_stream(backend, messages)
        on_log(f"quick action '{action_id}' started")
    except Exception as exc:  # never let a quick action break the studio
        try:
            app.toast(f"quick action failed: {exc}", "error")
        except Exception:
            pass


class ActionsMenu(tk.Toplevel):
    """Tiny launcher menu for the quick actions (one entry, all powers)."""

    WIDTH = 300

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("AI quick actions")
        self.configure(bg=self.app.theme["card"])
        self.transient(app.root)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        tk.Label(self, text="⚡  AI QUICK ACTIONS", bg=self.app.theme["card"],
                 fg=self.app.theme["text_muted"],
                 font=(FONT_UI, 8, "bold")).pack(fill=tk.X, padx=14,
                                                 pady=(12, 6))
        for i, (action_id, spec) in enumerate(ACTIONS.items(), 1):
            row = tk.Label(self, text=f"  {spec['icon']}  {spec['label']}",
                           bg=self.app.theme["card"],
                           fg=self.app.theme["text"],
                           font=(FONT_UI, 10), anchor="w", padx=8, pady=6)
            row.pack(fill=tk.X, padx=8, pady=1)
            row.bind("<Enter>", lambda e, w=row: w.config(
                bg=self.app.theme.accent))
            row.bind("<Leave>", lambda e, w=row: w.config(
                bg=self.app.theme["card"]))
            row.bind("<Button-1>",
                     lambda e, a=action_id: self._pick(a))
            # number keys run the action straight from the menu
            self.bind(f"<Key-{i}>", lambda e, a=action_id: self._pick(a))
        tk.Label(self, text="works on the current selection",
                 bg=self.app.theme["card"], fg=self.app.theme["text_muted"],
                 font=(FONT_UI, 8)).pack(pady=(4, 10))
        self.bind("<Escape>", lambda e: self.destroy())
        hints.hint_bar(self, self.app.theme,
                       pairs=[(str(n), spec["label"].lower())
                              for n, (_aid, spec)
                              in enumerate(ACTIONS.items(), 1)])
        self._center()

    def _center(self):
        try:
            self.update_idletasks()
            x = self.app.root.winfo_rootx() + 80
            y = self.app.root.winfo_rooty() + 120
            self.geometry(f"{self.WIDTH}x{self.winfo_reqheight()}+{x}+{y}")
        except tk.TclError:
            pass

    def _pick(self, action_id):
        self.destroy()
        run_action(self.app, action_id)


def open_actions_menu(app):
    """Show the one-entry launcher menu for all quick actions."""
    try:
        return ActionsMenu(app)
    except Exception:
        return None


def palette_commands(app):
    """Palette entries for every quick action."""
    cmds = [("AI: run a quick action on selection…", "DS2",
             lambda: open_actions_menu(app))]
    for action_id, spec in ACTIONS.items():
        cmds.append((f"AI: {spec['label'].lower()} (selection)", "DS2",
                     lambda a=action_id: run_action(app, a)))
    return cmds
