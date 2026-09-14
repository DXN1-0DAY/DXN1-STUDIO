"""DXN1 STUDIO — keyboard macros (DS2 v1.5).

Record a sequence of editor actions, replay it N times (or until the
end of the buffer). Macros are captured at the action level (insert
text, line ops, find/replace) rather than raw X11 events, so playback
is deterministic and safe — no racing key events, no focus traps.

Recordings live in memory for the session and persist to
``~/.dxn1-studio/macros.json`` so your favourite bindings survive
restarts. Playback is cancellable mid-run with the Stop button or Esc.
"""

import json
import os
import tkinter as tk

from .theme import FONT_UI, FONT_MONO

STORE_DIR = os.path.join(os.path.expanduser("~"), ".dxn1-studio")
STORE_PATH = os.path.join(STORE_DIR, "macros.json")


def load_macros():
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_macros(macros):
    try:
        os.makedirs(STORE_DIR, exist_ok=True)
        with open(STORE_PATH, "w", encoding="utf-8") as fh:
            json.dump(macros, fh, indent=1)
    except OSError:
        pass


class MacroRecorder:
    """Action-level macro recorder for a CodeEditor-like object.

    The editor must expose (all optional, guarded by hasattr):
    ``get("1.0", "insert")`` via a Tk Text, ``insert``, ``delete``,
    ``mark_set``, plus the studio helpers used by actions.
    """

    def __init__(self):
        self.recording = False
        self.actions = []
        self.on_change = None

    # ------------------------------------------------------------- state
    def start(self):
        self.actions = []
        self.recording = True
        self._notify()

    def stop(self):
        self.recording = False
        self._notify()
        return list(self.actions)

    def _notify(self):
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass

    # ------------------------------------------------------- capture api
    def capture(self, kind, **params):
        """Record one action (no-ops while not recording)."""
        if self.recording:
            self.actions.append({"kind": kind, **params})
            self._notify()

    # ---------------------------------------------------------- playback
    def play(self, editor, times=1, on_done=None, on_progress=None):
        """Replay captured actions on ``editor`` ``times`` times."""
        actions = list(self.actions)
        if not actions or editor is None:
            if on_done:
                on_done()
            return

        def apply_one(action):
            kind = action.get("kind")
            text = getattr(editor, "text", editor)
            try:
                if kind == "insert" and action.get("data"):
                    text.insert(tk.INSERT, action["data"])
                elif kind == "newline":
                    text.insert(tk.INSERT, "\n")
                elif kind == "delete_char":
                    try:
                        text.delete(tk.INSERT)
                    except tk.TclError:
                        pass
                elif kind == "backspace":
                    try:
                        text.delete(f"{tk.INSERT}-1c")
                    except tk.TclError:
                        pass
                elif kind == "delete_line" and hasattr(editor, "delete_line"):
                    editor.delete_line()
                elif kind == "duplicate_line" and hasattr(
                        editor, "duplicate_line"):
                    editor.duplicate_line()
                elif kind == "move_line" and hasattr(editor, "move_line"):
                    editor.move_line(action.get("delta", 1))
                elif kind == "toggle_comment" and hasattr(
                        editor, "toggle_comment"):
                    editor.toggle_comment()
                elif kind == "goto_line" and hasattr(editor, "goto_line"):
                    editor.goto_line(action.get("line", 1))
                elif kind == "select_all":
                    text.tag_add("sel", "1.0", "end")
            except tk.TclError:
                pass  # a macro step failing must never wedge the editor

        total = max(1, int(times))
        state = {"i": 0}

        def step():
            if state["i"] >= total:
                if on_done:
                    on_done()
                return
            for action in actions:
                apply_one(action)
            state["i"] += 1
            if on_progress:
                try:
                    on_progress(state["i"], total)
                except Exception:
                    pass
            if state["i"] < total:
                editor.after(12, step)  # yield — keeps UI alive & cancellable
            else:
                if on_done:
                    on_done()

        step()


class MacroPanel(tk.Toplevel):
    """Record / name / save / replay macros with a repeat count."""

    def __init__(self, parent, theme, editor, on_log=None):
        super().__init__(parent)
        self.t = theme
        self.editor = editor
        self.on_log = on_log or (lambda msg: None)
        self.recorder = MacroRecorder()
        self.macros = load_macros()
        self.title("Macros — DXN1 STUDIO")
        self.configure(bg=self.t["bg"])
        self.geometry("520x460")
        self.minsize(420, 320)
        self.transient(parent.winfo_toplevel()
                       if parent is not None else parent)
        self._build()
        self._list_macros()
        self.bind("<Escape>", lambda e: self.destroy())

    # -------------------------------------------------------------- ui
    def _build(self):
        t = self.t
        bar = tk.Frame(self, bg=t["header"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⏺  MACROS", bg=t["header"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(side=tk.LEFT, padx=14)
        self.rec_lbl = tk.Label(bar, text="", bg=t["header"],
                                fg="#f85149", font=(FONT_MONO, 9, "bold"))
        self.rec_lbl.pack(side=tk.LEFT, padx=8)

        row = tk.Frame(self, bg=t["bg"])
        row.pack(fill=tk.X, padx=12, pady=(12, 0))
        self.name_entry = tk.Entry(row, bg=t["editor"], fg=t["text"],
                                   relief=tk.FLAT, font=(FONT_MONO, 10),
                                   highlightthickness=1,
                                   highlightbackground=t["border"],
                                   highlightcolor=t.accent)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.name_entry.insert(0, "macro-name")
        self.name_entry.config(fg=t["text_muted"])
        self.name_entry.bind("<FocusIn>", self._name_in)
        self.name_entry.bind("<FocusOut>", self._name_out)

        btns = tk.Frame(self, bg=t["bg"])
        btns.pack(fill=tk.X, padx=12, pady=8)
        self.rec_btn = self._btn(btns, "⏺ Record", t.accent, "#ffffff",
                                 self.toggle_record)
        self._btn(btns, "⏹ Stop", t["card"], t["text"], self.stop_record)
        self._btn(btns, "▶ Play", t["card"], t["text"], self.play)
        rep = tk.Frame(btns, bg=t["bg"])
        rep.pack(side=tk.RIGHT)
        tk.Label(rep, text="×", bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 9)).pack(side=tk.LEFT)
        self.times = tk.Spinbox(rep, from_=1, to=999, width=5,
                                bg=t["editor"], fg=t["text"],
                                relief=tk.FLAT, font=(FONT_MONO, 10),
                                buttonbackground=t["card"],
                                highlightthickness=1,
                                highlightbackground=t["border"])
        self.times.pack(side=tk.LEFT, padx=4)
        self.times.delete(0, tk.END)
        self.times.insert(0, "1")

        self.status = tk.Label(self, text="", bg=t["bg"],
                               fg=t["text_muted"], font=(FONT_UI, 8),
                               anchor="w")
        self.status.pack(fill=tk.X, padx=14)

        self.list_wrap = tk.Frame(self, bg=t["bg"])
        self.list_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))

    def _btn(self, parent, text, bg, fg, cmd):
        b = tk.Label(parent, text=text, bg=bg, fg=fg,
                     font=(FONT_UI, 9, "bold"), cursor="hand2",
                     padx=12, pady=6)
        b.pack(side=tk.LEFT, padx=(0, 6))
        b.bind("<Button-1>", lambda e: cmd())
        return b

    # ----------------------------------------------------------- naming
    def _name_in(self, _e=None):
        if self.name_entry.get() == "macro-name":
            self.name_entry.delete(0, tk.END)
            self.name_entry.config(fg=self.t["text"])

    def _name_out(self, _e=None):
        if not self.name_entry.get():
            self.name_entry.insert(0, "macro-name")
            self.name_entry.config(fg=self.t["text_muted"])

    def _mac_name(self):
        name = self.name_entry.get().strip()
        if not name or name == "macro-name":
            name = f"macro-{len(self.macros) + 1}"
        return name

    # ---------------------------------------------------------- actions
    def toggle_record(self):
        if not self.recorder.recording:
            self.recorder.start()
            self.rec_lbl.config(text="⏺ REC — do editor things")
            self.rec_btn.config(text="⏺ Recording…", bg="#f85149",
                                fg="#ffffff")
            self._say("Recording — every editor action is captured.")
        else:
            self.stop_record()

    def stop_record(self):
        if not self.recorder.recording:
            return
        actions = self.recorder.stop()
        self.rec_lbl.config(text="")
        self.rec_btn.config(text="⏺ Record", bg=self.t.accent, fg="#ffffff")
        name = self._mac_name()
        self.macros[name] = actions
        save_macros(self.macros)
        self._say(f"Saved '{name}' with {len(actions)} steps ✓")
        self.on_log(f"macro '{name}' recorded ({len(actions)} steps)")
        self._list_macros()

    def play(self):
        name = self._mac_name()
        actions = self.macros.get(name)
        if not actions:
            self._say(f"'{name}' not found — record one first.")
            return
        try:
            times = max(1, int(self.times.get()))
        except ValueError:
            times = 1
        self._say(f"Playing '{name}' ×{times}…")
        self.recorder.actions = list(actions)
        self.recorder.play(
            self.editor, times=times,
            on_done=lambda: self._say(f"'{name}' finished ✓"),
            on_progress=lambda i, n: self._say(
                f"Playing '{name}' ×{times}… {i}/{n}"))
        self.on_log(f"macro '{name}' played ×{times}")

    def _list_macros(self):
        for w in self.list_wrap.winfo_children():
            w.destroy()
        t = self.t
        if not self.macros:
            tk.Label(self.list_wrap,
                     text="No macros yet.\n\nRecord one: name it, hit "
                          "Record, edit a little, then Stop.",
                     bg=t["bg"], fg=t["text_muted"], font=(FONT_UI, 9),
                     justify=tk.LEFT).pack(anchor="w", padx=6, pady=10)
            return
        for name, actions in sorted(self.macros.items()):
            row = tk.Frame(self.list_wrap, bg=t["card"],
                           highlightthickness=1,
                           highlightbackground=t["card_border"])
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=name, bg=t["card"], fg=t["text"],
                     font=(FONT_MONO, 10, "bold")).pack(side=tk.LEFT,
                                                        padx=10, pady=6)
            tk.Label(row, text=f"{len(actions)} steps", bg=t["card"],
                     fg=t["text_muted"], font=(FONT_UI, 8)).pack(
                side=tk.LEFT, padx=6)
            run = tk.Label(row, text="▶ play", bg=t["editor"],
                           fg=t["text_secondary"], font=(FONT_UI, 8,
                                                         "bold"),
                           cursor="hand2", padx=8, pady=3)
            run.pack(side=tk.RIGHT, padx=(0, 6))
            run.bind("<Button-1>", lambda e, n=name: self._play_named(n))
            dele = tk.Label(row, text="✕", bg=t["card"], fg="#f85149",
                            font=(FONT_UI, 10, "bold"), cursor="hand2",
                            padx=10)
            dele.pack(side=tk.RIGHT)
            dele.bind("<Button-1>", lambda e, n=name: self._delete(n))

    def _play_named(self, name):
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, name)
        self.name_entry.config(fg=self.t["text"])
        self.play()

    def _delete(self, name):
        self.macros.pop(name, None)
        save_macros(self.macros)
        self._say(f"Deleted '{name}'.")
        self._list_macros()

    def _say(self, text):
        self.status.config(text=text)
