"""DXN1 STUDIO — the translation desk (DS2 v2.56).

A real desk for pack translators. Until now a community pack meant
hand-writing JSON against a key list you had to scrape out of the
audit; the desk shows every English key beside its translation,
marks what is missing, stale or highlight-unsafe, and saves a user
pack to ``~/.dxn1-studio/lang/<code>.json`` — the file
``i18n.set_language`` already layers over the built-ins, so saved
strings go live the moment their pack is active.

v2.56 gave the desk eyes and a conscience: a live **preview**
renders a slice of the studio UI in the pack you are editing (it
keeps up as you type, so you see Menu ▸ Settings… become Ajustes…
in context before saving), an **Untouched** filter reviews the
strings that still read English byte-for-byte, and ``pack_diff`` /
``lang diff`` print the honest ledger — real translations versus
seeds — because a coverage meter can flatter a pack that was seeded
and never edited.

v2.57 made packs travel light: **Export** writes the working copy
as a JSON file shaped exactly like a user pack (what the desk
exports the desk imports, and ``set_language`` would layer it over
built-ins untouched), **Import** overlays such a file onto the
working copy — the desk's own exports, user packs and
``export_template`` files alike, with junk skipped and counted and
nothing written to the pack until Save.

The model is the audit's (v2.54), restated as editing:

- **translated** — the pack carries its own string for the key;
- **missing** — the pack says nothing; the studio falls back to
  English at runtime (shown as English in the desk, marked ○);
- **stale** — the pack carries a key the English source no longer
  names (kept on save: the desk edits, it does not silently drop);
- **unsafe** — the string changes length under ``str.lower()``
  (İ lowercases to two code points), which is exactly the property
  fuzzy-match highlight positions assume — typed live, flagged
  live, counted in the header.

Never raises: every callback is guarded, because a desk that breaks
typing is worse than no desk.
"""

import json
import os
import re
import tkinter as tk

from . import i18n as _i18n
from .theme import FONT_UI, FONT_MONO

# pack codes name a JSON file on disk — keep them filename-honest
CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,15}$")

# listbox markers — one glyph, read at a glance
_M_TRANSLATED = "●"   # the pack speaks for itself
_M_MISSING = "○"      # English shows through
_M_STALE = "✕"        # the source dropped this key
_M_UNSAFE = "⚠"       # translated, and NOT highlight-safe


# ---------------------------------------------------------------- data
def own_translations(code):
    """The pack's OWN strings, no English fill: built-in values with
    the user pack on disk layered over — exactly what
    ``i18n.set_language`` layers on top of EN. A fresh (or junk)
    code answers ``{}``. Never raises."""
    try:
        code = (code or "").lower()
    except Exception:  # noqa: BLE001 — junk code, empty pack
        return {}
    own = {}
    if code and code != "en" and code in _i18n.PACKS:
        own.update(_i18n.PACKS[code])
    own.update(_read_user_pack(code))
    return own


def pack_working(code):
    """The effective runtime dict for a code — EN with the pack's
    own strings on top (what ``tr()`` answers from). Never the live
    pack object: a copy, safe to mutate."""
    working = dict(_i18n.EN)
    working.update(own_translations(code))
    return working


def _user_pack_path(code):
    return os.path.join(_i18n.LANG_DIR, "%s.json" % code)


def _read_user_pack(code):
    """Strings from ``~/.dxn1-studio/lang/<code>.json``, or ``{}``."""
    try:
        with open(_user_pack_path(code), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()
                    if isinstance(k, str) and isinstance(v, str)}
    except (OSError, ValueError, TypeError):
        pass
    return {}


def is_unsafe(text):
    """v2.54's highlight contract, as a predicate: does this string
    change length under ``str.lower()``? (İ → 'i̇' is the classic.)
    Empty strings are safe by definition — there is nothing to
    highlight."""
    try:
        return bool(text) and len(text.lower()) != len(text)
    except Exception:  # noqa: BLE001 — junk is not a crash
        return False


def save_user_pack(code, mapping):
    """Write a user pack atomically (tmp file + ``os.replace``) and
    return the number of strings written. Empty/whitespace values
    are dropped — an empty translation means "back to English" —
    and non-string pairs are refused. ``LANG_DIR`` is created if
    missing; OSError reaches the caller, which reports it honestly."""
    clean = {str(k): str(v) for k, v in (mapping or {}).items()
             if isinstance(k, str) and isinstance(v, str) and v.strip()}
    directory = _i18n.LANG_DIR
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    path = _user_pack_path(code)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(clean, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return len(clean)


def pack_counts(code):
    """The desk's header numbers for a code, computed the same way
    ``i18n.pack_stats`` computes them: covered, total, missing,
    stale, unsafe — plus v2.56's honest counter, ``untouched``: the
    pack's own strings that are byte-identical to English (seeded,
    maybe, but not yet translated). Never raises."""
    en = _i18n.EN
    own = own_translations(code)
    in_en = set(en)
    covered = len([k for k in own if k in in_en])
    stale = len([k for k in own if k not in in_en])
    unsafe = len([k for k, v in own.items() if is_unsafe(v)])
    untouched = len([k for k in own if k in in_en
                     and own[k] == en[k]])
    total = len(en)
    pct = int(round(covered * 100.0 / total)) if total else 100
    return {"covered": covered, "total": total, "pct": pct,
            "missing": total - covered, "stale": stale,
            "unsafe": unsafe, "untouched": untouched}


def export_pack(code, dest, work=None):
    """DS2 v2.57 — write a pack as a shareable JSON file: the desk's
    working copy when ``work`` is given, the pack's own strings
    otherwise. The shape is exactly a user pack's — ``{key: value}``
    — so what the desk exports the desk imports, and
    ``i18n.set_language`` would layer it over built-ins untouched.
    Empty/whitespace values and non-string pairs are dropped (the
    same rule ``save_user_pack`` applies). Returns the number of
    strings written; OSError reaches the caller, which reports it
    honestly."""
    data = own_translations(code) if work is None else dict(work)
    clean = {str(k): str(v) for k, v in data.items()
             if isinstance(k, str) and isinstance(v, str)
             and v.strip()}
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(clean, fh, ensure_ascii=False, indent=2,
                  sort_keys=True)
        fh.write("\n")
    return len(clean)


def merge_pack_file(path, work):
    """DS2 v2.57 — overlay a pack file onto a working copy dict IN
    PLACE: valid str→str pairs replace, empty/whitespace values drop
    the key (back to English — the desk's own rule, so a pack round-
    trips through disk without changing its mind), everything else
    is skipped and counted. Accepts the desk's own exports, user
    packs, and ``i18n.export_template`` files alike. Returns
    ``(applied, skipped)``; a file that cannot be read or parsed
    answers ``(-1, 0)`` so the caller reports it honestly instead of
    guessing. Never raises on content."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return -1, 0
    if not isinstance(data, dict):
        return -1, 0
    applied = skipped = 0
    for key, val in data.items():
        if not isinstance(key, str) or not isinstance(val, str):
            skipped += 1
            continue
        if val.strip():
            work[key] = val
        else:
            work.pop(key, None)
        applied += 1
    return applied, skipped


def pack_diff(code):
    """DS2 v2.56 — the honest ledger: how a pack REALLY differs from
    the English source. The coverage meter can flatter: a pack
    seeded from English and never edited shows 100% covered while
    every string still reads English. The diff splits the pack's own
    strings into **real** translations (they differ from English —
    the pack speaks for itself) and **seeds** (byte-identical to
    English — wearing the pack, not speaking it), alongside the
    audit's missing / stale / and the highlight-unsafe property.

    ``real_pct`` is the number that cannot lie: real translations
    over the English total. Never raises."""
    en = _i18n.EN
    own = own_translations(code)
    real, seeds, stale = [], [], []
    unsafe = []
    for key, val in own.items():
        if is_unsafe(val):
            unsafe.append(key)
        if key not in en:
            stale.append(key)
        elif val == en[key]:
            seeds.append(key)
        else:
            real.append(key)
    missing = [k for k in en if k not in own]
    total = len(en)
    return {"code": code, "name": _i18n.LANG_NAMES.get(code, code),
            "real": sorted(real), "seeds": sorted(seeds),
            "missing": missing, "stale": sorted(stale),
            "unsafe": sorted(unsafe),
            "real_pct": (int(round(len(real) * 100.0 / total))
                         if total else 100)}


# ---------------------------------------------------------------- desk
class PackEditor(tk.Toplevel):
    """The desk itself: every English key beside its translation,
    filter chips (All / Untouched / Missing / Stale / Unsafe), a
    search box, a live unsafe warning, a live preview of the studio
    in this pack (Ctrl+P) and an atomic Save. Ctrl+S saves, Esc
    closes; selection loads the detail pane; typing commits into the
    working copy at once, so the meter is always honest."""

    def __init__(self, app, code, on_log=None):
        self.app = app
        self.code = (code or "en").lower()
        t = self.theme = app.theme
        self.on_log = on_log
        super().__init__(app.root)
        self.title("Translation desk — %s" % self.code)
        self.configure(bg=t["bg"])
        self.transient(app.root)
        self.resizable(True, True)
        self.minsize(560, 460)
        self.geometry("680x560")

        # working copy: the pack's own strings, edited in place
        self.work = own_translations(self.code)
        self._filter = "all"
        self._current = None          # key shown in the detail pane
        self._preview = None          # the live PackPreview, if open

        self._build_header()
        self._build_filters()
        self._build_lists()
        self._build_detail()

        self.bind("<Escape>", lambda e: self._close())
        self.bind("<Control-s>", lambda e: self._save())
        self.bind("<Control-p>", lambda e: self._open_preview())
        self.bind("<Control-e>", lambda e: self._export_pack())
        self.bind("<Control-i>", lambda e: self._import_pack())
        self.bind("<Destroy>", self._on_destroy, add="+")
        try:
            from . import hints
            self._hintbar = hints.hint_bar(
                self, t,
                pairs=(("Ctrl+S", "save pack"),
                       ("Ctrl+P", "preview this pack"),
                       ("Ctrl+E", "export pack file"),
                       ("Ctrl+I", "import a pack file"),),
                notes=("click a key, type, Ctrl+S writes the pack",
                       "Ctrl+P shows the studio in what you typed",))
        except Exception:  # noqa: BLE001 — garnish
            self._hintbar = None

        self._refresh()
        self._log("translation desk open for '%s' — %s"
                  % (self.code, self._meter_text()))
        try:
            self.listbox.focus_set()
        except Exception:  # noqa: BLE001 — focus is garnish
            pass

    # ---------------------------------------------------------- build
    def _build_header(self):
        t = self.theme
        head = tk.Frame(self, bg=t["bg"])
        head.pack(fill=tk.X, padx=14, pady=(12, 0))
        name = _i18n.LANG_NAMES.get(self.code, self.code)
        kind = ("user pack" if os.path.exists(_user_pack_path(self.code))
                else ("built-in pack"
                      if self.code in _i18n.PACKS else "new pack"))
        tk.Label(head, text="TRANSLATION DESK",
                 bg=t["bg"], fg=t["text"],
                 font=(FONT_UI, 11, "bold")).pack(anchor="w")
        tk.Label(head, text="%s · %s · %s"
                 % (self.code, name, kind),
                 bg=t["bg"], fg=t["text_muted"],
                 font=(FONT_UI, 9)).pack(anchor="w")
        self.meter = tk.Label(head, text="", bg=t["bg"],
                              fg=t["text_secondary"],
                              font=(FONT_UI, 9))
        self.meter.pack(anchor="w", pady=(2, 4))

    def _build_filters(self):
        t = self.theme
        row = tk.Frame(self, bg=t["bg"])
        row.pack(fill=tk.X, padx=14)
        self._chips = {}
        for key, label in (("all", "All"),
                           ("untouched", "Untouched"),
                           ("missing", "Missing"),
                           ("stale", "Stale"), ("unsafe", "Unsafe")):
            chip = tk.Label(row, text=label, bg=t["card"],
                            fg=t["text"], cursor="hand2",
                            font=(FONT_UI, 9), padx=10, pady=3)
            chip.pack(side=tk.LEFT, padx=(0, 6))
            chip.bind("<Button-1>",
                      lambda e, k=key: self._set_filter(k))
            self._chips[key] = chip
        self.search_var = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.search_var,
                         bg=t["editor"], fg=t["text"],
                         insertbackground=t["text"], relief=tk.FLAT,
                         font=(FONT_MONO, 9), highlightthickness=1,
                         highlightbackground=t["border"],
                         highlightcolor=t.accent, width=18)
        entry.pack(side=tk.RIGHT)
        entry.bind("<KeyRelease>", lambda e: self._refresh_rows())
        self.search_entry = entry
        self._paint_chips()

    def _build_lists(self):
        t = self.theme
        wrap = tk.Frame(self, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=14, pady=(8, 6))
        bar = tk.Scrollbar(wrap, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(
            wrap, yscrollcommand=bar.set, bg=t["editor"], fg=t["text"],
            selectbackground=t.accent, selectforeground="#ffffff",
            relief=tk.FLAT, font=(FONT_MONO, 9), activestyle="none",
            exportselection=False)
        bar.config(command=self.listbox.yview)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

    def _build_detail(self):
        t = self.theme
        pane = tk.Frame(self, bg=t["bg"])
        pane.pack(fill=tk.X, padx=14, pady=(0, 6))
        tk.Label(pane, text="EN SOURCE", bg=t["bg"],
                 fg=t["text_muted"],
                 font=(FONT_UI, 8, "bold")).pack(anchor="w")
        self.source = tk.Text(pane, height=2, wrap=tk.WORD,
                              bg=t["editor"], fg=t["text_secondary"],
                              relief=tk.FLAT, font=(FONT_MONO, 9),
                              highlightthickness=1,
                              highlightbackground=t["border"],
                              state=tk.DISABLED)
        self.source.pack(fill=tk.X, pady=(2, 6))
        tk.Label(pane, text="TRANSLATION", bg=t["bg"],
                 fg=t["text_muted"],
                 font=(FONT_UI, 8, "bold")).pack(anchor="w")
        self.edit = tk.Text(pane, height=3, wrap=tk.WORD,
                            bg=t["editor"], fg=t["text"],
                            insertbackground=t["text"],
                            relief=tk.FLAT, font=(FONT_MONO, 10),
                            highlightthickness=1,
                            highlightbackground=t["border"],
                            highlightcolor=t.accent)
        self.edit.pack(fill=tk.X, pady=(2, 2))
        self.edit.bind("<KeyRelease>", lambda e: self._flush_edit())
        self.warn = tk.Label(pane, text="", bg=t["bg"], fg="#f85149",
                             font=(FONT_UI, 8), anchor="w",
                             wraplength=600, justify="left")
        self.warn.pack(anchor="w")

        btns = tk.Frame(pane, bg=t["bg"])
        btns.pack(fill=tk.X, pady=(4, 0))
        clear = tk.Label(btns, text="Clear key", bg=t["card"],
                         fg=t["text"], cursor="hand2",
                         font=(FONT_UI, 9), padx=10, pady=4)
        clear.pack(side=tk.LEFT)
        clear.bind("<Button-1>", lambda e: self._clear_key())
        seed = tk.Label(btns, text="Seed missing from English",
                        bg=t["card"], fg=t["text"], cursor="hand2",
                        font=(FONT_UI, 9), padx=10, pady=4)
        seed.pack(side=tk.LEFT, padx=(8, 0))
        seed.bind("<Button-1>", lambda e: self._seed_from_en())
        prev = tk.Label(btns, text="Preview the studio",
                        bg=t["card"], fg=t["text"], cursor="hand2",
                        font=(FONT_UI, 9), padx=10, pady=4)
        prev.pack(side=tk.LEFT, padx=(8, 0))
        prev.bind("<Button-1>", lambda e: self._open_preview())
        self.preview_btn = prev
        expo = tk.Label(btns, text="Export pack",
                        bg=t["card"], fg=t["text"], cursor="hand2",
                        font=(FONT_UI, 9), padx=10, pady=4)
        expo.pack(side=tk.LEFT, padx=(8, 0))
        expo.bind("<Button-1>", lambda e: self._export_pack())
        self.export_btn = expo
        impo = tk.Label(btns, text="Import pack",
                        bg=t["card"], fg=t["text"], cursor="hand2",
                        font=(FONT_UI, 9), padx=10, pady=4)
        impo.pack(side=tk.LEFT, padx=(8, 0))
        impo.bind("<Button-1>", lambda e: self._import_pack())
        self.import_btn = impo
        self.save_btn = tk.Label(btns, text="Save pack", bg=t.accent,
                                 fg="#ffffff", cursor="hand2",
                                 font=(FONT_UI, 9, "bold"),
                                 padx=14, pady=4)
        self.save_btn.pack(side=tk.RIGHT)
        self.save_btn.bind("<Button-1>", lambda e: self._save())
        self.status = tk.Label(btns, text="", bg=t["bg"],
                               fg=t["text_muted"],
                               font=(FONT_UI, 8), anchor="e")
        self.status.pack(side=tk.RIGHT, padx=(0, 10))

    # ---------------------------------------------------------- state
    def _rows(self):
        """The keys the list should show under the current filter and
        search, in stable order: EN source order, then stale keys."""
        q = ""
        try:
            q = self.search_var.get().strip().lower()
        except Exception:  # noqa: BLE001 — no search yet
            pass
        en = _i18n.EN
        out = []
        for key in en:
            val = self.work.get(key)
            state = self._state_of(key, val)
            if not self._filter_ok(key, val, state):
                continue
            if q and q not in key.lower() \
                    and q not in str(val or "").lower() \
                    and q not in str(en[key]).lower():
                continue
            out.append(key)
        for key in sorted(k for k in self.work if k not in en):
            val = self.work.get(key)
            state = self._state_of(key, val)
            if not self._filter_ok(key, val, state):
                continue
            if q and q not in key.lower() \
                    and q not in str(val or "").lower():
                continue
            out.append(key)
        return out

    @staticmethod
    def _state_of(key, val):
        """One of translated / missing / stale / unsafe — unsafe wins
        as the marker (it is the thing to fix first)."""
        if val is None:
            return "missing" if key in _i18n.EN else "hidden"
        if is_unsafe(val):
            return "unsafe"
        if key not in _i18n.EN:
            return "stale"
        return "translated"

    def _filter_ok(self, key, val, state):
        f = self._filter
        if f == "all":
            return state != "hidden"
        if f == "untouched":
            # v2.56 — the pack's own string, byte-identical to the
            # English source: seeded, maybe, but not yet translated
            return (state == "translated"
                    and val == _i18n.EN.get(key))
        if f == "missing":
            return state == "missing"
        if f == "stale":
            return state == "stale"
        if f == "unsafe":
            return state == "unsafe"
        return state != "hidden"

    def _marker(self, state):
        return {"translated": _M_TRANSLATED, "missing": _M_MISSING,
                "stale": _M_STALE, "unsafe": _M_UNSAFE}.get(state, "○")

    def _meter_text(self):
        c = pack_counts(self.code)
        return ("%d/%d keys · %d%% · %d missing · %d stale · "
                "%d unsafe · %d untouched"
                % (c["covered"], c["total"], c["pct"],
                   c["missing"], c["stale"], c["unsafe"],
                   c["untouched"]))

    # -------------------------------------------------------- actions
    def _set_filter(self, key):
        self._filter = key
        self._paint_chips()
        self._refresh_rows()

    def _paint_chips(self):
        t = self.theme
        for key, chip in self._chips.items():
            active = key == self._filter
            try:
                chip.config(bg=t.accent if active else t["card"],
                            fg="#ffffff" if active else t["text"])
            except Exception:  # noqa: BLE001 — a dying chip is fine
                pass

    def _refresh(self):
        """Recompute meter + rows + detail from the working copy."""
        try:
            self.meter.config(text=self._meter_text())
        except Exception:  # noqa: BLE001 — a dying window is fine
            pass
        self._refresh_rows()
        self._refresh_preview()

    def _refresh_rows(self):
        try:
            rows = self._rows()
            self.listbox.delete(0, tk.END)
            for key in rows:
                state = self._state_of(key, self.work.get(key))
                self.listbox.insert(tk.END,
                                    "%s  %s" % (self._marker(state), key))
            self._row_keys = rows
            if rows:
                if self._current not in rows:
                    self._select_index(0)
                else:
                    self._select_index(rows.index(self._current),
                                        quiet=True)
            else:
                self._current = None
                self._load_detail(None)
        except Exception:  # noqa: BLE001 — the desk never raises
            pass

    def _select_index(self, idx, quiet=False):
        try:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
            if not quiet:
                self._on_select()
        except Exception:  # noqa: BLE001
            pass

    def _on_select(self, _event=None):
        try:
            sel = self.listbox.curselection()
            key = self._row_keys[sel[0]] if sel else None
            self._load_detail(key)
        except Exception:  # noqa: BLE001 — the desk never raises
            pass

    def _load_detail(self, key):
        """Put a key's EN source and working translation in the detail
        pane (empty translation box for missing keys — the translator
        starts from nothing, not from English)."""
        self._current = key
        try:
            self.source.config(state=tk.NORMAL)
            self.source.delete("1.0", tk.END)
            self.source.insert("1.0", _i18n.EN.get(key, "")
                               if key in _i18n.EN
                               else "(not in the English source — stale)")
            self.source.config(state=tk.DISABLED)
            self.edit.delete("1.0", tk.END)
            self.edit.insert("1.0", self.work.get(key, ""))
            self._warn_check()
        except Exception:  # noqa: BLE001
            pass

    def _flush_edit(self):
        """Commit the translation box into the working copy — live,
        on every keystroke; an empty box means the key goes missing
        again. Newlines flatten to spaces (packs are single-line
        strings). Then the meter and markers stay honest."""
        key = self._current
        if key is None:
            return
        try:
            raw = self.edit.get("1.0", "end-1c")
            val = " ".join(raw.split("\n")).strip()
            if val:
                self.work[key] = val
            else:
                self.work.pop(key, None)
            self._warn_check()
            self._refresh_rows()
            self.meter.config(text=self._meter_text())
            self._refresh_preview()
        except Exception:  # noqa: BLE001 — the desk never raises
            pass

    def _warn_check(self):
        """The live unsafe flag: this string changes length under
        .lower() and would shift fuzzy highlights after it."""
        try:
            key = self._current
            val = self.work.get(key) if key else None
            if key and val and is_unsafe(val):
                self.warn.config(
                    text="⚠ NOT highlight-safe — this string changes "
                         "length under .lower() (like İstanbul), so "
                         "every fuzzy highlight after it would shift")
            else:
                self.warn.config(text="")
        except Exception:  # noqa: BLE001
            pass

    def _clear_key(self):
        """Drop the selected key from the working copy — the pack
        stops speaking for it and English shows through again."""
        key = self._current
        if not key:
            return
        try:
            self.work.pop(key, None)
            self._refresh()
            self._load_detail(key)
            self._log("cleared '%s' — English shows through again"
                      % key)
        except Exception:  # noqa: BLE001
            pass

    def _seed_from_en(self):
        """Fill every missing key with the English string — a starting
        point to edit down, the desk's version of export_template.
        Nothing is written until Save."""
        try:
            seeded = 0
            for key, val in _i18n.EN.items():
                if key not in self.work:
                    self.work[key] = val
                    seeded += 1
            self._refresh()
            self._log("seeded %d missing key(s) from English — edit "
                      "them down and Ctrl+S" % seeded)
            try:
                self.status.config(
                    text="seeded %d" % seeded)
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001 — the desk never raises
            pass

    def _save(self, _event=None):
        """Write the working copy as a user pack (atomic). If this
        pack is the active language it re-activates at once, so
        saved strings go live immediately."""
        try:
            count = save_user_pack(self.code, self.work)
            if _i18n.current() == self.code:
                _i18n.set_language(self.code)
            try:
                self.status.config(text="saved %d strings" % count)
            except Exception:  # noqa: BLE001
                pass
            self._log("saved %d strings to %s — a user pack that "
                      "overrides built-ins%s"
                      % (count, _user_pack_path(self.code),
                         " (re-activated, live now)"
                         if _i18n.current() == self.code else ""))
            self._refresh()
            return True
        except Exception as exc:  # noqa: BLE001 — report, don't raise
            try:
                self.status.config(text="save failed")
            except Exception:  # noqa: BLE001
                pass
            self._log("save failed: %s" % exc)
            return False

    def _log(self, message):
        try:
            if self.on_log:
                self.on_log(message)
        except Exception:  # noqa: BLE001 — logging is garnish
            pass

    def _close(self):
        try:
            self.destroy()
        except Exception:  # noqa: BLE001 — dying root is fine
            pass

    def _open_preview(self, _event=None):
        """v2.56 — the desk grows eyes: open the live preview (or
        refresh + raise the one already open). Ctrl+P or the button.
        Returns the window or None — never raises."""
        try:
            if self._preview is not None \
                    and self._preview.winfo_exists():
                self._preview.refresh()
                try:
                    self._preview.lift()
                except Exception:  # noqa: BLE001
                    pass
                return self._preview
            self._preview = PackPreview(self)
            return self._preview
        except Exception:  # noqa: BLE001 — the desk never raises
            return None

    def _refresh_preview(self):
        """Keep the preview honest on every keystroke — it renders
        the working copy, so it must keep up while typing."""
        try:
            p = self._preview
            if p is not None and p.winfo_exists():
                p.refresh()
        except Exception:  # noqa: BLE001 — garnish must not bite
            pass

    def _export_pack(self, _event=None):
        """v2.57 — write the working copy to a JSON file shaped
        exactly like a user pack: what the desk exports the desk
        imports, and ``set_language`` would layer it over built-ins
        untouched. Ctrl+E. Cancelled dialogs change nothing."""
        try:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                parent=self, title="Export pack as JSON",
                defaultextension=".json",
                initialfile="%s.json" % self.code,
                filetypes=[("Language packs", "*.json"),
                           ("All files", "*.*")])
            if not path:
                return False
            count = export_pack(self.code, path, work=self.work)
            try:
                self.status.config(text="exported %d" % count)
            except Exception:  # noqa: BLE001
                pass
            self._log("exported %d strings to %s — a file the desk "
                      "imports again and set_language would layer "
                      "over built-ins" % (count, path))
            return True
        except Exception as exc:  # noqa: BLE001 — report, don't raise
            self._log("export failed: %s" % exc)
            return False

    def _import_pack(self, _event=None):
        """v2.57 — overlay a pack file onto the working copy: the
        desk's own exports, user packs, export_template files alike.
        Valid pairs replace, empty values drop the key back to
        English, junk is skipped and counted; nothing reaches the
        pack file until Save. Ctrl+I."""
        try:
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                parent=self, title="Import a pack file",
                filetypes=[("Language packs", "*.json"),
                           ("All files", "*.*")])
            if not path:
                return False
            applied, skipped = merge_pack_file(path, self.work)
            if applied < 0:
                try:
                    self.status.config(text="import failed")
                except Exception:  # noqa: BLE001
                    pass
                self._log("import failed: %s is not a pack file "
                          "the desk can read" % path)
                return False
            self._refresh()
            try:
                self.status.config(
                    text="imported %d%s" % (applied,
                                            " (%d skipped)" % skipped
                                            if skipped else ""))
            except Exception:  # noqa: BLE001
                pass
            self._log("imported %d string%s%s from %s — the working "
                      "copy changed, the pack file did not (Ctrl+S "
                      "writes it)"
                      % (applied, "" if applied == 1 else "s",
                         ", %d skipped" % skipped if skipped else "",
                         path))
            return True
        except Exception as exc:  # noqa: BLE001 — report, don't raise
            self._log("import failed: %s" % exc)
            return False

    def _on_destroy(self, _event=None):
        # closing the desk closes its preview — no orphaned eyes
        try:
            p = self._preview
            self._preview = None
            if p is not None and p.winfo_exists():
                p.destroy()
        except Exception:  # noqa: BLE001 — teardown is best-effort
            pass


# ------------------------------------------------------------- preview
class PackPreview(tk.Toplevel):
    """The desk grows eyes: a slice of the studio UI rendered in the
    pack being edited, live — type in the desk and the preview keeps
    up, so Menu ▸ Settings… becomes Ajustes… in context BEFORE the
    pack is saved. A string the pack does not speak shows English
    (exactly what ``tr()`` would answer), in the muted color; a
    string the pack DOES carry wears the accent. Never raises;
    closing the desk closes it."""

    # the slices, in studio anatomy order: (caption, keys)
    SLICES = (
        ("title bar", ("app.tagline",)),
        ("menu bar", ("menu.file", "menu.edit", "menu.view",
                      "menu.tools", "menu.help")),
        ("toolbar", ("menu.new_file", "menu.open_file",
                     "menu.save", "menu.run", "menu.stop")),
        ("sidebar", ("panel.explorer", "panel.search",
                     "panel.git", "panel.packages")),
        ("find bar", ("menu.find", "menu.replace")),
        ("buttons", ("common.cancel", "common.copy",
                     "common.export", "common.import",
                     "common.refresh", "common.close")),
    )

    def __init__(self, desk):
        self.desk = desk
        t = self.theme = desk.theme
        super().__init__(desk)
        self.title("Pack preview — %s" % desk.code)
        self.configure(bg=t["bg"])
        self.transient(desk)
        self.resizable(True, True)
        self.minsize(340, 300)
        self.geometry("440x380")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda e: self._close())
        self._build()
        self.refresh()
        try:
            from . import hints
            self._hintbar = hints.hint_bar(self, t)
        except Exception:  # noqa: BLE001 — garnish
            self._hintbar = None

    def _build(self):
        t = self.theme
        head = tk.Frame(self, bg=t["bg"])
        head.pack(fill=tk.X, padx=14, pady=(12, 0))
        tk.Label(head, text="PACK PREVIEW", bg=t["bg"],
                 fg=t["text"], font=(FONT_UI, 11,
                                     "bold")).pack(anchor="w")
        tk.Label(head, text="a slice of the studio in '%s' — live: "
                            "it keeps up as you type in the desk"
                            % self.desk.code,
                 bg=t["bg"], fg=t["text_muted"], font=(FONT_UI, 9),
                 wraplength=400, justify="left",
                 anchor="w").pack(anchor="w", pady=(2, 1))
        tk.Label(head, text="accent = the pack speaks for it · "
                            "grey = English shows through",
                 bg=t["bg"], fg=t["text_secondary"],
                 font=(FONT_UI, 8), wraplength=400,
                 justify="left", anchor="w").pack(anchor="w",
                                                  pady=(0, 4))
        self.body = tk.Frame(self, bg=t["bg"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=14,
                       pady=(4, 8))

    def working(self):
        """The dict the preview renders: EN with the desk's live
        working copy on top — what ``tr()`` would answer the moment
        this pack is saved and activated."""
        d = dict(_i18n.EN)
        try:
            d.update(self.desk.work)
        except Exception:  # noqa: BLE001 — a dying desk previews EN
            pass
        return d

    def refresh(self):
        """Re-render every slice from the live working copy."""
        try:
            for w in self.body.winfo_children():
                w.destroy()
            t = self.theme
            pack = self.working()
            spoken = set(getattr(self.desk, "work", {}) or {})
            for caption, keys in self.SLICES:
                tk.Label(self.body, text=caption.upper(),
                         bg=t["bg"], fg=t["text_muted"],
                         font=(FONT_UI, 7, "bold")).pack(
                    anchor="w", pady=(6, 1))
                strip = tk.Frame(self.body, bg=t["card"],
                                 highlightthickness=1,
                                 highlightbackground=t["card_border"])
                strip.pack(fill=tk.X)
                for key in keys:
                    val = pack.get(key) or key
                    from_pack = key in spoken
                    lab = tk.Label(strip, text=val,
                                   bg=t["card"],
                                   fg=t.accent if from_pack
                                   else t["text_secondary"],
                                   font=(FONT_UI, 9), padx=8, pady=3)
                    lab.pack(side=tk.LEFT)
        except Exception:  # noqa: BLE001 — a preview never bites
            pass

    def _close(self):
        try:
            self.desk._preview = None
        except Exception:  # noqa: BLE001 — the desk may be gone
            pass
        try:
            self.destroy()
        except Exception:  # noqa: BLE001 — dying windows are fine
            pass


# ------------------------------------------------------------- chooser
class PackChooser(tk.Toplevel):
    """The desk's door: pick an existing pack to edit (built-ins and
    user packs, with live coverage from pack_stats), or name a new
    code and start from a clean slate. Esc closes; a junk code gets
    an honest inline error."""

    def __init__(self, app, on_log=None):
        self.app = app
        t = self.theme = app.theme
        self.on_log = on_log
        super().__init__(app.root)
        self.title("Translation desk — choose a pack")
        self.configure(bg=t["card"])
        self.transient(app.root)
        self.resizable(False, False)

        wrap = tk.Frame(self, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["card_border"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        tk.Label(wrap, text="TRANSLATION DESK", bg=t["card"],
                 fg=t["text"], font=(FONT_UI, 11,
                                     "bold")).pack(anchor="w",
                                                   padx=16,
                                                   pady=(14, 2))
        tk.Label(wrap, text="Pick a pack to edit, or name a new code. "
                            "Saved strings become a user pack that "
                            "overrides built-ins.",
                 bg=t["card"], fg=t["text_muted"], font=(FONT_UI, 8),
                 wraplength=320, justify="left",
                 anchor="w").pack(anchor="w", padx=16, pady=(0, 8))

        self._rows_frame = tk.Frame(wrap, bg=t["card"])
        self._rows_frame.pack(fill=tk.X, padx=16)
        self._paint_packs()

        sep = tk.Frame(wrap, bg=t["card_border"], height=1)
        sep.pack(fill=tk.X, padx=16, pady=8)

        newrow = tk.Frame(wrap, bg=t["card"])
        newrow.pack(fill=tk.X, padx=16, pady=(0, 4))
        tk.Label(newrow, text="New pack code:", bg=t["card"],
                 fg=t["text"], font=(FONT_UI, 9)).pack(side=tk.LEFT)
        self.code_var = tk.StringVar()
        self.entry = tk.Entry(newrow, textvariable=self.code_var,
                              bg=t["editor"], fg=t["text"],
                              insertbackground=t["text"],
                              relief=tk.FLAT, font=(FONT_MONO, 10),
                              highlightthickness=1,
                              highlightbackground=t["border"],
                              highlightcolor=t.accent, width=12)
        self.entry.pack(side=tk.LEFT, padx=(8, 0), ipady=3)
        go = tk.Label(newrow, text="Open desk", bg=t.accent,
                      fg="#ffffff", cursor="hand2",
                      font=(FONT_UI, 9, "bold"), padx=12, pady=4)
        go.pack(side=tk.LEFT, padx=(8, 0))
        go.bind("<Button-1>", lambda e: self._open_new())
        self.err = tk.Label(wrap, text="", bg=t["card"], fg="#f85149",
                            font=(FONT_UI, 8), anchor="w",
                            wraplength=320, justify="left")
        self.err.pack(anchor="w", padx=16, pady=(2, 10))

        self.bind("<Escape>", lambda e: self._close())
        self.bind("<Return>", lambda e: self._open_new())
        try:
            from . import hints
            self._hintbar = hints.hint_bar(self, t,
                                           pairs=(("Return",
                                                   "open desk"),))
        except Exception:  # noqa: BLE001 — garnish
            self._hintbar = None
        try:
            self.entry.focus_set()
        except Exception:  # noqa: BLE001 — focus is garnish
            pass

    def _paint_packs(self):
        """One honest row per pack (English excluded — the source of
        truth is not edited, it is translated FROM)."""
        try:
            for w in self._rows_frame.winfo_children():
                w.destroy()
            t = self.theme
            stats = [s for s in _i18n.pack_stats() if s["code"] != "en"]
            for s in stats:
                kind = "user" if s["user"] else "built-in"
                label = ("%s · %s · %s · %d%%"
                         % (s["code"], s["name"], kind, s["pct"]))
                if s["error"]:
                    label += " · unreadable"
                row = tk.Label(self._rows_frame, text=label,
                               bg=t["card"], fg=t["text"],
                               cursor="hand2", font=(FONT_UI, 9),
                               anchor="w", padx=8, pady=4)
                row.pack(fill=tk.X, pady=1)
                row.bind("<Enter>", lambda e, w=row:
                         w.config(bg=t.accent))
                row.bind("<Leave>", lambda e, w=row:
                         w.config(bg=t["card"]))
                row.bind("<Button-1>", lambda e, c=s["code"]:
                         self._open(c))
        except Exception:  # noqa: BLE001 — the door never jams
            pass

    def _open(self, code):
        try:
            PackEditor(self.app, code, on_log=self.on_log)
            self._close()
            return True
        except Exception:  # noqa: BLE001 — a desk that won't open
            try:
                self.err.config(text="could not open the desk for '%s'"
                                     % code)
            except Exception:  # noqa: BLE001
                pass
            return False

    def _open_new(self, _event=None):
        """Validate the typed code honestly: lowercase letters,
        digits, _ or - (it becomes a filename). An existing code
        just opens that pack — the desk edits, it does not clobber."""
        try:
            code = self.code_var.get().strip().lower()
            if not code:
                self.err.config(text="name a code first — lowercase "
                                     "letters, digits, _ or -")
                return False
            if not CODE_RE.match(code):
                self.err.config(text="'%s' is not a pack code — "
                                     "lowercase letters, digits, _ or "
                                     "- (e.g. ca, pt_br)" % code)
                return False
            if code == "en":
                self.err.config(text="English is the source of truth — "
                                     "it is translated FROM, not edited")
                return False
            return self._open(code)
        except Exception:  # noqa: BLE001 — the door never jams
            return False

    def _close(self):
        try:
            self.destroy()
        except Exception:  # noqa: BLE001 — dying root is fine
            pass


# ---------------------------------------------------------------- open
def open_pack_editor(app, code=None, on_log=None):
    """Open the translation desk: with ``code`` the editor at once,
    without it the chooser first. Returns the Toplevel (chooser or
    editor) or None. Never raises — callers can fire-and-forget."""
    try:
        if code is None:
            return PackChooser(app, on_log=on_log)
        return PackEditor(app, code, on_log=on_log)
    except Exception:  # noqa: BLE001 — the desk must never break typing
        return None


def palette_commands(app):
    """Palette-ready command tuples (the quick_actions convention)."""
    return [("Edit a language pack…", "DS2",
             lambda: open_pack_editor(
                 app, on_log=lambda m: _log_to(app, m)))]


def _log_to(app, message):
    try:
        app.terminal.log(message)
    except Exception:  # noqa: BLE001 — logging is garnish
        pass
