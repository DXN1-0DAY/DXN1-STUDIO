"""DS2 v2.54.0 UI smoke — every pack answers for itself: fuzzy-match
positions stay index-aligned with the raw text even when str.lower()
changes the length (İ lowercases to two code points — the one way a
palette highlight could light the wrong letters), i18n.pack_stats()
audits every built-in and user pack for coverage / stale keys /
highlight-safety (unreadable packs report instead of vanishing), the
`lang audit` verb prints the audit through the real dispatcher, and
the branch chip menu gains its state-aware copy sibling — the
recovery line when diverged, plain push/pull one move from sync,
silence when in sync.

Run under Xvfb:
    Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v540.py

Never touches the real user config: HOME is redirected to a temp dir
before any dxn1_studio import, and everything is cleaned up at exit.
"""
import json
import os
import shutil
import sys
import tempfile

HOME = tempfile.mkdtemp(prefix="ds2-home-")
os.environ["HOME"] = HOME            # before imports: config + i18n dir
sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk  # noqa: E402

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


# ------------------------------------- seed a quiet boot
_cfg_dir = os.path.join(HOME, ".dxn1-studio")
os.makedirs(_cfg_dir, exist_ok=True)
with open(os.path.join(_cfg_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"onboarded": True, "hub_on_startup": False,
               "check_updates": False}, fh)

_real_mainloop = tk.Tk.mainloop
tk.Tk.mainloop = lambda self, *a, **k: None   # probes drive update() instead

from dxn1_studio.config import Config  # noqa: E402
from dxn1_studio.app import DXN1Studio  # noqa: E402
from dxn1_studio import fuzzy as fz  # noqa: E402
from dxn1_studio import i18n as i18nmod  # noqa: E402

app = DXN1Studio(Config(), no_splash=True)
root = app.root
root.update()
if getattr(app, "_hub", None) is not None and app._hub.winfo_exists():
    app._on_hub_explore()
root.update()
check("studio booted headless", root.winfo_exists())

# ------------------------------------- the fuzzy fix, e2e
_text = "İstanbul"
_s, _pos = fz.match("ist", _text)
check("fuzzy: İ positions index the raw text",
      _s >= 0 and tuple(_pos) == (0, 1, 2)
      and [_text[p] for p in _pos] == ["İ", "s", "t"])
_runs = fz.split_runs(_text, _pos)
check("fuzzy: highlight runs light the right letters",
      _runs and _runs[0] == ("İst", True)
      and "".join(c for c, _m in _runs) == _text)
check("fuzzy: two İ's never double-drift",
      fz.match("ii", "İxİz")[1] == (0, 2))
check("fuzzy: ASCII path byte-for-byte unchanged",
      fz.match("set", "Settings")[1] == (0, 1, 2)
      and fz.match("", "anything") == (0, ())
      and fz.match("zz", "nothing-here")[0] == -1)
check("fuzzy: ranked keeps the aligned positions",
      [h[2] for h in fz.ranked("ist", ["İstanbul", "istanbul"])]
      == [(0, 1, 2), (0, 1, 2)])

# ------------------------------------- pack_stats through the real module
_stats = i18nmod.pack_stats()
_codes = [s["code"] for s in _stats]
check("packs: en first and complete",
      _codes[0] == "en" and _stats[0]["pct"] == 100)
check("packs: all seven built-ins report",
      {"es", "fr", "de", "pt", "zh", "hi", "ja"} <= set(_codes))
check("packs: every pack answers with sane numbers",
      all(0 <= s["pct"] <= 100 and s["missing"] >= 0
          and s["stale"] >= 0 and isinstance(s["index_safe"], bool)
          for s in _stats))
check("packs: the shipped packs are highlight-safe",
      all(s["index_safe"] for s in _stats if not s["user"]))

# ------------------------------------- the lang audit verb
_logs = []
_old_log = app.terminal.log
app.terminal.log = lambda m, *a, **k: _logs.append(str(m))
try:
    app.handle_terminal_command("lang audit")
finally:
    app.terminal.log = _old_log
root.update()
check("verb: the audit prints its header",
      any("language packs:" in m for m in _logs))
check("verb: every built-in pack gets a line",
      sum(1 for m in _logs if "[built-in]" in m) >= 8)
check("verb: the audit explains itself",
      any("highlight-safe = every string" in m for m in _logs))

# ------------------------------------- the branch menu's copy sibling
def _clipboard():
    try:
        return root.clipboard_get()
    except tk.TclError:
        return ""


root.clipboard_clear()
app._git_watch_state = lambda: {"repo": True, "branch": "m",
                                "dirty": 0, "ahead": 2, "behind": 1}
_e = app._git_menu_entries()
_rec = [x for x in _e if x[0] == "Copy recovery command"]
check("git menu: diverged offers the recovery line", bool(_rec))
if _rec:
    _rec[0][1]()
    root.update()
    check("git menu: recovery clipboard truth",
          _clipboard() == "git pull --rebase && git push")

app._git_watch_state = lambda: {"repo": True, "branch": "m",
                                "dirty": 0, "ahead": 3, "behind": 0}
_e = app._git_menu_entries()
_push = [x for x in _e if x[0] == "Copy push command"]
check("git menu: ahead-only offers the plain push",
      bool(_push) and not [x for x in _e
                           if x[0] == "Copy recovery command"])
if _push:
    _push[0][1]()
    root.update()
    check("git menu: push clipboard truth", _clipboard() == "git push")

app._git_watch_state = lambda: {"repo": True, "branch": "m",
                                "dirty": 0, "ahead": 0, "behind": 1}
check("git menu: behind-only offers the plain pull",
      bool([x for x in app._git_menu_entries()
            if x[0] == "Copy pull command"]))

app._git_watch_state = lambda: {"repo": True, "branch": "m",
                                "dirty": 0, "ahead": 0, "behind": 0}
_labs = [x[0] for x in app._git_menu_entries()]
check("git menu: in sync stays silent",
      not any(l.startswith("Copy ") and l != "Copy branch name"
              for l in _labs))
app._git_watch_state = lambda: None
check("git menu: no repo, no git rows at all",
      not [x for x in app._git_menu_entries()
           if x[0].startswith(("Push", "Pull", "Copy recovery",
                               "Copy push", "Copy pull"))])
app._git_copy_command("nonsense")
root.update()
check("git menu: a junk kind is ignored honestly", True)

# ------------------------------------- the help table knows the rows
from dxn1_studio.app import TERMINAL_HELP  # noqa: E402

_vl = [r[0] for r in TERMINAL_HELP]
check("help: lang and lang audit are first-class verbs",
      "lang" in _vl and "lang audit" in _vl)

# ------------------------------------- docs agree
with open(os.path.join("dxn1_studio", "fuzzy.py"),
          encoding="utf-8") as fh:
    _fz = fh.read()
with open(os.path.join("dxn1_studio", "i18n.py"),
          encoding="utf-8") as fh:
    _in = fh.read()
with open(os.path.join("dxn1_studio", "app.py"),
          encoding="utf-8") as fh:
    _ap = fh.read()
check("source: the alignment fix lives in match()",
      '"".join(c.lower()[:1] for c in raw)' in _fz)
check("source: pack_stats audits length and staleness",
      "def pack_stats" in _in and '"index_safe": not risk' in _in
      and '"stale": stale' in _in)
check("source: the verb and the copy sibling are wired",
      'arg == "audit"' in _ap
      and '"Copy recovery command"' in _ap
      and "git pull --rebase && git push" in _ap)

with open(os.path.join("docs", "FEATURES.md"), encoding="utf-8") as fh:
    _ft = fh.read()
check("FEATURES.md: the round is written down",
      "The Packs Answer for Themselves" in _ft and "lang audit" in _ft)

# ------------------------------------- cleanup
app._dismiss_chip_menu()
shutil.rmtree(HOME, ignore_errors=True)

failed = FAIL
print(f"\n{len(PASS)}/{len(PASS) + len(failed)} passed")
sys.exit(1 if failed else 0)
