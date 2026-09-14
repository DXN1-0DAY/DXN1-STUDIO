"""DS2 Clipboard History — never lose a copied snippet again.

A background poller (1.5 s after-loop) watches the system clipboard,
keeps a deduplicated ring of the last N entries, and a compact window
lets you paste any previous entry back at the editor cursor.

Engine (ClipRing) is pure and unit-tested; the poller never raises.

Open with: palette, terminal ``clip`` / ``clip <text>`` stores a
snippet directly.
"""

import tkinter as tk

__all__ = ["ClipRing", "ClipboardHistory", "open_cliphistory",
           "preview_of"]

PREVIEW_CAP = 90


def preview_of(text):
    """One-line, whitespace-collapsed preview for list rows."""
    if not isinstance(text, str):
        return ""
    flat = " ".join(text.split())
    if len(flat) > PREVIEW_CAP:
        return flat[: PREVIEW_CAP - 1] + "…"
    return flat


class ClipRing:
    """Bounded, most-recent-first clipboard memory."""

    def __init__(self, size=25):
        self.size = max(1, int(size))
        self._items = []            # index 0 == newest

    def add(self, text):
        """Store text (returns True when it changed the ring).

        Rules: non-str → False; empty/whitespace-only → False;
        identical to the newest entry → False (no dup spam); older
        duplicate is moved to the front; ring evicts the oldest.
        """
        if not isinstance(text, str) or not text.strip():
            return False
        if self._items and self._items[0] == text:
            return False
        if text in self._items:
            self._items.remove(text)
        self._items.insert(0, text)
        if len(self._items) > self.size:
            self._items[:] = self._items[: self.size]
        return True

    def items(self):
        """Newest-first copy of the ring."""
        return list(self._items)

    def clear(self):
        self._items = []

    def __len__(self):
        return len(self._items)


class ClipboardHistory(tk.Toplevel):
    """List of recent clipboard entries; click to paste at cursor."""

    POLL_MS = 1500

    def __init__(self, parent, theme, paste_callback=None, ring=None):
        super().__init__(parent)
        self.theme = theme or {}
        self.paste_callback = paste_callback
        self.ring = ring if ring is not None else ClipRing()

        t = self.theme
        self.title("Clipboard History — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("640x420")
        self.minsize(420, 300)
        try:
            self.transient(parent)
        except Exception:
            pass

        self._build_toolbar()
        self._build_list()
        self._build_statusbar()
        self.bind("<Escape>", lambda _e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._job = None
        self._last_clip = ""
        self.refresh()
        self._poll()

    # ------------------------------------------------------------ UI
    def _build_toolbar(self):
        t = self.theme
        bar = tk.Frame(self, bg=t.get("header", "#242432"))
        bar.pack(fill=tk.X)
        tk.Label(bar, text="double-click an entry to paste it",
                 bg=t.get("header", "#242432"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(
            side=tk.LEFT, padx=(10, 4), pady=6)

        def _btn(text, cmd):
            return tk.Button(
                bar, text=text, command=cmd, relief="flat", bd=0,
                bg=t.get("hover", "#2c2c3e"), fg=t.get("text", "#e8e8f0"),
                activebackground=t.get("border", "#3a3a4e"),
                activeforeground=t.get("text", "#e8e8f0"),
                padx=10, pady=2, cursor="hand2")

        _btn("Refresh", self.refresh).pack(side=tk.RIGHT, padx=6)
        _btn("Clear", self.clear_history).pack(side=tk.RIGHT, padx=2)
        _btn("Copy selected", self.copy_selected).pack(
            side=tk.RIGHT, padx=2)

    def _build_list(self):
        t = self.theme
        wrap = tk.Frame(self, bg=t.get("bg", "#16161e"))
        wrap.pack(fill=tk.BOTH, expand=True)
        self.tv = tk.Listbox(
            wrap, activestyle="none", relief="flat", bd=0,
            bg=t.get("editor", "#1b1b24"), fg=t.get("text", "#e8e8f0"),
            selectbackground=t.get("hover", "#2c2c3e"),
            selectforeground=t.get("text", "#e8e8f0"),
            font=("TkFixedFont", 10))
        ysb = tk.Scrollbar(wrap, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=ysb.set)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tv.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=6)
        self.tv.bind("<Double-1>", self._on_paste)
        self.tv.bind("<Return>", self._on_paste)

    def _build_statusbar(self):
        t = self.theme
        self.status = tk.Label(
            self, text="0 entries", anchor="w",
            bg=t.get("header", "#242432"),
            fg=t.get("text_muted", "#8a8a9a"), padx=10, pady=3)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # -------------------------------------------------------- actions
    def refresh(self):
        """Snapshot the current clipboard into the ring + redraw."""
        try:
            clip = self.clipboard_get()
        except tk.TclError:
            clip = ""
        self.ring.add(clip)
        self._redraw()

    def _redraw(self):
        self.tv.delete(0, tk.END)
        for text in self.ring.items():
            self.tv.insert(tk.END, preview_of(text))
        self.status.config(
            text=f"{len(self.ring)} entries · newest first")

    def _poll(self):
        """Background clipboard watcher."""
        try:
            clip = self.clipboard_get()
            if clip != self._last_clip:
                self._last_clip = clip
                if self.ring.add(clip):
                    self._redraw()
        except tk.TclError:
            pass
        except Exception:  # noqa: BLE001 — poller never dies
            pass
        self._job = self.after(self.POLL_MS, self._poll)

    def _selected_text(self):
        sel = self.tv.curselection()
        if not sel:
            return None
        items = self.ring.items()
        return items[sel[0]] if sel[0] < len(items) else None

    def _on_paste(self, _e=None):
        text = self._selected_text()
        if text is None:
            return
        if self.paste_callback:
            try:
                self.paste_callback(text)
                self._status_flash("pasted ✓")
                return
            except Exception:  # noqa: BLE001 — fall through to copy
                pass
        # no callback → put it on the clipboard at least
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status_flash("copied back to clipboard ✓")

    def copy_selected(self):
        text = self._selected_text()
        if text is None:
            self._status_flash("select an entry first")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status_flash("copied ✓")

    def clear_history(self):
        self.ring.clear()
        self._redraw()
        self._status_flash("history cleared")

    def _status_flash(self, msg):
        t = self.theme
        self.status.config(text=msg,
                           fg=t.get("success", "#5ad19c"))
        self.after(2000, lambda: self.status.config(
            fg=t.get("text_muted", "#8a8a9a")))

    def _close(self):
        try:
            if self._job:
                self.after_cancel(self._job)
        except Exception:
            pass
        self.destroy()


def open_cliphistory(parent, theme, paste_callback=None, ring=None):
    """Public opener — palette / menu / terminal entry point."""
    return ClipboardHistory(parent, theme, paste_callback=paste_callback,
                            ring=ring)
