"""DXN1 STUDIO — Template Gallery.

A searchable, category-filtered, favouritable browse-everything view of
every project template the studio can scaffold. Built for the Project
Hub (DS2 v1.8.0) but openable from the command palette at any time.

Two template sources are merged here:

* the built-in scaffolds from :mod:`dxn1_studio.projects` (Python, Flask,
  FastAPI, Tkinter, Rust, Go, …), and
* the **DS2 extra pack** declared in ``EXTRA_TEMPLATES`` below — data
  science, web scraping, pytest, discord bots and a complete todo app —
  which are scaffolded by :func:`scaffold_any` without touching the
  core projects module.

The gallery also owns two small config-backed registries used by the
Hub's recents list:

* ``template_favorites`` — kinds the developer starred,
* ``pinned_projects``    — recent workspaces pinned to the top.
"""

import json
import os
import time
import tkinter as tk
from tkinter import messagebox

from . import APP_NAME
from . import projects
from .theme import FONT_UI, FONT_MONO

# ------------------------------------------------------------------ extras
# kind -> (label, pitch, badge, category, files-factory)
# The factory mirrors projects.template_files(): rel-path -> content.
EXTRA_TEMPLATES = {}

_CATEGORIES = (
    "All", "Python", "Web", "Desktop", "Data", "CLI",
    "Systems", "Bots", "Tests", "More",
)


def extra_template(kind, name):
    """Return file dict for a DS2 extra template ({} when unknown)."""
    entry = EXTRA_TEMPLATES.get(kind)
    return entry[4](name) if entry else {}


def _reg(kind, label, pitch, badge, category):
    def deco(factory):
        EXTRA_TEMPLATES[kind] = (label, pitch, badge, category, factory)
        return factory
    return deco


@_reg("data", "Data Explorer",
      "pandas + matplotlib starter — load a CSV, chart it.",
      "data", "Data")
def _data_files(name):
    return {
        "main.py": (
            f'"""{name} — data exploration starter, scaffolded by {APP_NAME}.\n'
            '\n'
            'Install deps first (Tools -> Manage Packages):\n'
            '    pandas  ·  matplotlib\n'
            'Then drop a data.csv next to this file and hit F5.\n'
            '"""\n'
            'import os\n'
            '\n'
            'import pandas as pd\n'
            'import matplotlib\n'
            '\n'
            'matplotlib.use("TkAgg")\n'
            'import matplotlib.pyplot as plt\n'
            '\n'
            'CSV = os.path.join(os.path.dirname(__file__), "data.csv")\n'
            '\n'
            '\n'
            'def main():\n'
            '    if not os.path.exists(CSV):\n'
            '        # demo data so the script always runs\n'
            '        pd.DataFrame({\n'
            '            "day": range(1, 31),\n'
            '            "commits": [3, 5, 2, 8, 9, 4, 6] * 4 + [3, 5],\n'
            '        }).to_csv(CSV, index=False)\n'
            '        print("no data.csv found — wrote a 30-day demo set")\n'
            '\n'
            '    df = pd.read_csv(CSV)\n'
            '    print(df.describe())\n'
            '\n'
            '    df.plot(kind="bar", x="day", y="commits",\n'
            '            legend=False, title="Activity")\n'
            '    plt.tight_layout()\n'
            '    plt.show()\n'
            '\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        ),
        "requirements.txt": "pandas>=2.0\nmatplotlib>=3.8\n",
        "README.md": _readme(name, "Data Explorer"),
    }


@_reg("scraper", "Web Scraper",
      "requests + BeautifulSoup — polite scraping starter.",
      "scrape", "Web")
def _scraper_files(name):
    return {
        "main.py": (
            f'"""{name} — web scraping starter, scaffolded by {APP_NAME}.\n'
            '\n'
            'Install deps first: requests · beautifulsoup4\n'
            'Be polite: check robots.txt, rate-limit yourself.\n'
            '"""\n'
            'import time\n'
            '\n'
            'import requests\n'
            'from bs4 import BeautifulSoup\n'
            '\n'
            'URL = "https://quotes.toscrape.com/"   # a site built for practice\n'
            'HEADERS = {"User-Agent": "DXN1-Studio-scrape-tutorial"}\n'
            '\n'
            '\n'
            'def main():\n'
            '    resp = requests.get(URL, headers=HEADERS, timeout=10)\n'
            '    resp.raise_for_status()\n'
            '    soup = BeautifulSoup(resp.text, "html.parser")\n'
            '\n'
            '    quotes = []\n'
            '    for q in soup.select(".quote")[:10]:\n'
            '        text = q.select_one(".text").get_text(strip=True)\n'
            '        author = q.select_one(".author").get_text(strip=True)\n'
            '        quotes.append((author, text))\n'
            '        print(f"{author:>20} — {text[:60]}…")\n'
            '\n'
            '    with open("quotes.json", "w", encoding="utf-8") as fh:\n'
            '        import json\n'
            '        json.dump(quotes, fh, indent=2)\n'
            '    print(f"\\nsaved {len(quotes)} quotes -> quotes.json")\n'
            '    time.sleep(0)   # placeholder for your rate limiting\n'
            '\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        ),
        "requirements.txt": "requests>=2.31\nbeautifulsoup4>=4.12\n",
        "README.md": _readme(name, "Web Scraper"),
    }


@_reg("bot", "Discord Bot",
      "discord.py skeleton — ping command, ready to grow.",
      "bot", "Bots")
def _bot_files(name):
    return {
        "bot.py": (
            f'"""{name} — discord.py bot skeleton, scaffolded by {APP_NAME}.\n'
            '\n'
            'Setup:\n'
            '  1. pip install -U discord.py  (Tools -> Manage Packages)\n'
            '  2. create a bot at discord.com/developers -> Bot -> copy token\n'
            '  3. put the token in a .env file:  DISCORD_TOKEN=xxxx\n'
            '  4. run bot.py (F5)\n'
            '"""\n'
            'import os\n'
            '\n'
            'import discord\n'
            '\n'
            'TOKEN = os.environ.get("DISCORD_TOKEN", "")\n'
            '\n'
            'intents = discord.Intents.default()\n'
            'intents.message_content = True\n'
            '\n'
            'client = discord.Client(intents=intents)\n'
            '\n'
            '\n'
            '@client.event\n'
            'async def on_ready():\n'
            '    print(f"logged in as {client.user} — watching {len(client.guilds)} servers")\n'
            '\n'
            '\n'
            '@client.event\n'
            'async def on_message(message):\n'
            '    if message.author.bot:\n'
            '        return\n'
            '    if message.content.startswith("!ping"):\n'
            '        latency = round(client.latency * 1000)\n'
            '        await message.channel.send(f"pong! ({latency} ms)")\n'
            '    elif message.content.startswith("!hello"):\n'
            '        await message.channel.send(f"hey {message.author.mention}!")\n'
            '\n'
            '\n'
            'if not TOKEN:\n'
            '    raise SystemExit("put your bot token in a .env file or env var DISCORD_TOKEN")\n'
            'client.run(TOKEN)\n'
        ),
        "requirements.txt": "discord.py>=2.3\n",
        ".gitignore": ".env\n__pycache__/\n",
        "README.md": _readme(name, "Discord Bot"),
    }


@_reg("tests", "Test Lab",
      "pytest project — fixtures, parametrize, coverage-ready.",
      "pytest", "Tests")
def _tests_files(name):
    slug = projects.slugify(name).lower().replace("-", "_")
    pkg = slug if slug[:1].isalpha() else f"lab_{slug}"
    return {
        f"{pkg}/__init__.py": f'"""{name} — test-first project, scaffolded by {APP_NAME}."""\n',
        f"{pkg}/temperature.py": (
            '"""Unit-conversion helpers the tests exercise."""\n'
            '\n'
            '\n'
            'def c_to_f(celsius: float) -> float:\n'
            '    return celsius * 9 / 5 + 32\n'
            '\n'
            '\n'
            'def f_to_c(fahrenheit: float) -> float:\n'
            '    return (fahrenheit - 32) * 5 / 9\n'
        ),
        "tests/test_temperature.py": (
            '"""Run with: pytest -q   (install pytest from Manage Packages)"""\n'
            'import pytest\n'
            '\n'
            f'from {pkg}.temperature import c_to_f, f_to_c\n'
            '\n'
            '\n'
            '@pytest.mark.parametrize("c, f", [\n'
            '    (0, 32),\n'
            '    (100, 212),\n'
            '    (-40, -40),      # the famous crossover point\n'
            '    (37, 98.6),\n'
            '])\n'
            'def test_c_to_f(c, f):\n'
            '    assert c_to_f(c) == pytest.approx(f, abs=0.1)\n'
            '\n'
            '\n'
            '@pytest.fixture\n'
            'def body_temp():\n'
            '    return 37.0\n'
            '\n'
            '\n'
            'def test_roundtrip(body_temp):\n'
            '    assert f_to_c(c_to_f(body_temp)) == pytest.approx(body_temp)\n'
        ),
        "pytest.ini": "[pytest]\naddopts = -q --tb=short\ntestpaths = tests\n",
        "README.md": _readme(name, "Test Lab"),
    }


@_reg("todo", "Tkinter Todo App",
      "Complete task manager — add, done, filter, persist.",
      "todo", "Desktop")
def _todo_files(name):
    return {
        "main.py": (
            f'"""{name} — a working todo app, scaffolded by {APP_NAME}.\n'
            '\n'
            'A complete Tkinter task manager in ~90 lines: add tasks, mark\n'
            'done, filter, double-click to delete, tasks persist to JSON.\n'
            '"""\n'
            'import json\n'
            'import os\n'
            'import tkinter as tk\n'
            '\n'
            'STORE = os.path.join(os.path.dirname(__file__), "tasks.json")\n'
            'ACCENT = "#7c3aed"\n'
            '\n'
            '\n'
            'class Todo(tk.Tk):\n'
            '    def __init__(self):\n'
            '        super().__init__()\n'
            '        self.title("{name}")\n'
            '        self.geometry("420x480")\n'
            '        self.configure(bg="#0d1117")\n'
            '        self.tasks = self._load()\n'
            '\n'
            '        top = tk.Frame(self, bg="#0d1117")\n'
            '        top.pack(fill="x", padx=14, pady=(14, 6))\n'
            '        self.entry = tk.Entry(top, bg="#11161d", fg="#e6edf3",\n'
            '                              insertbackground="#e6edf3",\n'
            '                              relief="flat")\n'
            '        self.entry.pack(side="left", fill="x", expand=True, ipady=6)\n'
            '        self.entry.bind("<Return>", lambda e: self.add())\n'
            '        tk.Button(top, text="Add", command=self.add, bg=ACCENT,\n'
            '                  fg="white", relief="flat", padx=14,\n'
            '                  cursor="hand2").pack(side="left", padx=(8, 0))\n'
            '\n'
            '        self.filters = tk.Frame(self, bg="#0d1117")\n'
            '        self.filters.pack(fill="x", padx=14)\n'
            '        self.mode = tk.StringVar(value="all")\n'
            '        for m in ("all", "open", "done"):\n'
            '            tk.Radiobutton(self.filters, text=m.title(), value=m,\n'
            '                           variable=self.mode, command=self.render,\n'
            '                           bg="#0d1117", fg="#9aa7b8",\n'
            '                           selectcolor="#11161d",\n'
            '                           activebackground="#0d1117",\n'
            '                           ).pack(side="left")\n'
            '\n'
            '        self.listbox = tk.Listbox(self, bg="#131a22", fg="#e6edf3",\n'
            '                                  selectbackground=ACCENT,\n'
            '                                  relief="flat", font=("TkDefaultFont", 11))\n'
            '        self.listbox.pack(fill="both", expand=True, padx=14, pady=10)\n'
            '        self.listbox.bind("<Double-Button-1>", self._delete)\n'
            '\n'
            '        tk.Label(self, text="double-click a task to delete it",\n'
            '                 bg="#0d1117", fg="#6e7a8a").pack(pady=(0, 10))\n'
            '        self.render()\n'
            '\n'
            '    def add(self):\n'
            '        text = self.entry.get().strip()\n'
            '        if text:\n'
            '            self.tasks.append({"text": text, "done": False})\n'
            '            self.entry.delete(0, "end")\n'
            '            self._save()\n'
            '            self.render()\n'
            '\n'
            '    def toggle(self):\n'
            '        sel = self.listbox.curselection()\n'
            '        if sel:\n'
            '            i = sel[0]\n'
            '            self.tasks[i]["done"] = not self.tasks[i]["done"]\n'
            '            self._save()\n'
            '            self.render()\n'
            '\n'
            '    def _delete(self, _event):\n'
            '        sel = self.listbox.curselection()\n'
            '        if sel:\n'
            '            del self.tasks[sel[0]]\n'
            '            self._save()\n'
            '            self.render()\n'
            '\n'
            '    def render(self):\n'
            '        mode = self.mode.get()\n'
            '        self.listbox.delete(0, "end")\n'
            '        for t in self.tasks:\n'
            '            if mode == "open" and t["done"]:\n'
            '                continue\n'
            '            if mode == "done" and not t["done"]:\n'
            '                continue\n'
            '            mark = "\\u2713" if t["done"] else "\\u25cb"\n'
            '            self.listbox.insert("end", f" {mark}  {t[\'text\']}")\n'
            '        self.bind("<space>", lambda e: self.toggle())\n'
            '\n'
            '    def _load(self):\n'
            '        try:\n'
            '            with open(STORE, encoding="utf-8") as fh:\n'
            '                return json.load(fh)\n'
            '        except (OSError, ValueError):\n'
            '            return [{"text": "ship something great", "done": False}]\n'
            '\n'
            '    def _save(self):\n'
            '        with open(STORE, "w", encoding="utf-8") as fh:\n'
            '            json.dump(self.tasks, fh, indent=2)\n'
            '\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    Todo().mainloop()\n'
        ),
        "README.md": _readme(name, "Tkinter Todo App"),
    }


def _readme(name, kind_label):
    return (
        f"# {name}\n\n"
        f"A **{kind_label}** workspace created with **{APP_NAME}**.\n\n"
        "## Getting started\n\n"
        "- Open this folder in the studio (`File -> Open Workspace…`)\n"
        "- Press **Run** (F5) on the main file\n"
        "- Optional dependencies live in **Tools -> Manage Packages**\n"
    )


# ------------------------------------------------------------- unified view
def all_templates():
    """kind -> (label, pitch, badge, category) for every known template,
    built-ins first (projects.KIND_ORDER), then DS2 extras."""
    out = {}
    for kind in projects.KIND_ORDER:
        label, pitch, badge = projects.TEMPLATE_INFO[kind]
        out[kind] = (label, pitch, badge, _category_for(kind))
    for kind, (label, pitch, badge, category, _fac) in EXTRA_TEMPLATES.items():
        out.setdefault(kind, (label, pitch, badge, category))
    return out


def _category_for(kind):
    return {
        "python": "Python", "package": "Python",
        "flask": "Web", "fastapi": "Web", "static": "Web",
        "requests": "Web",
        "tkinter": "Desktop", "game": "Desktop", "todo": "Desktop",
        "cli": "CLI",
        "rust": "Systems", "go": "Systems",
        "data": "Data",
        "bot": "Bots",
        "tests": "Tests",
    }.get(kind, "More")


def template_preview_files(kind):
    """File list a scaffold would create (no filesystem writes) — used for
    the 'what you get' preview on gallery cards."""
    try:
        if kind in EXTRA_TEMPLATES:
            files = extra_template(kind, "Sample Project")
        else:
            files = projects.template_files(kind, "Sample Project")
        return sorted(files.keys())
    except Exception:  # noqa: BLE001 — preview must never crash the gallery
        return []


def scaffold_any(kind, parent_dir, name):
    """Scaffold a workspace of any registered kind.

    Built-ins are delegated to :func:`projects.scaffold`; DS2 extras are
    written here with the same metadata stamp. Returns (path, kind).
    """
    if kind not in EXTRA_TEMPLATES:
        return projects.scaffold(kind, parent_dir, name)

    parent = os.path.expanduser(parent_dir or projects.DEFAULT_PROJECTS_ROOT)
    os.makedirs(parent, exist_ok=True)
    base = projects.slugify(name)
    target = os.path.join(parent, base)
    n = 2
    while os.path.exists(target):
        target = os.path.join(parent, f"{base}-{n}")
        n += 1
        if n > 99:
            raise FileExistsError(target)
    os.makedirs(target)
    for rel, content in extra_template(kind, name).items():
        full = os.path.join(target, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
    meta = {
        "name": name, "kind": kind, "studio": APP_NAME,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(target, projects.PROJECT_FILE), "w",
              encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return target, kind


# ---------------------------------------------------------------- favorites
def get_favorites(config):
    """Starred template kinds (list of str)."""
    favs = config.get("template_favorites")
    return [f for f in favs if isinstance(f, str)] if isinstance(favs, list) else []


def toggle_favorite(config, kind):
    favs = get_favorites(config)
    if kind in favs:
        favs.remove(kind)
    else:
        favs.append(kind)
    config.set("template_favorites", favs)
    return kind in favs


# -------------------------------------------------------------------- pins
def get_pins(config):
    """Pinned workspace paths (absolute, list of str)."""
    pins = config.get("pinned_projects")
    return [p for p in pins if isinstance(p, str)] if isinstance(pins, list) else []


def toggle_pin(config, path):
    """Pin/unpin a workspace path. Returns True if now pinned."""
    path = os.path.abspath(path)
    pins = get_pins(config)
    if path in pins:
        pins.remove(path)
        pinned = False
    else:
        pins.insert(0, path)
        pinned = True
    config.set("pinned_projects", pins[:24])
    return pinned


def sort_recents_with_pins(recents, config):
    """Pinned recents first (original order preserved within groups)."""
    pins = set(get_pins(config))
    return ([r for r in recents if r.get("path") in pins]
            + [r for r in recents if r.get("path") not in pins])


# ------------------------------------------------------------------ window
GALLERY_W, GALLERY_H = 900, 700

_GAL_C = {"bg": "#0d1117", "card": "#131a22", "border": "#232c3d",
          "text": "#e6edf3", "secondary": "#9aa7b8", "muted": "#6e7a8a",
          "input": "#11161d", "star": "#e3b341"}


class TemplateGallery(tk.Toplevel):
    """Browsable template gallery: search box, category chips, star
    favourites, file-tree preview. Picking a card calls ``on_pick(kind)``
    (the Hub reuses its own create-workspace flow from there)."""

    def __init__(self, master, config, accent, on_pick):
        super().__init__(master)
        self.config = config
        self.accent = accent
        self.on_pick = on_pick
        self.templates = all_templates()
        self.query = ""
        self.category = "All"

        self.title(f"{APP_NAME} — Template Gallery")
        self.configure(bg=_GAL_C["bg"])
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_header()
        self._build_body()
        self._center()

        self.after(60, self._focus_search)
        self.apply_filter()

    # ------------------------------------------------------------- header
    def _build_header(self):
        head = tk.Frame(self, bg=_GAL_C["bg"])
        head.pack(fill=tk.X, padx=26, pady=(18, 0))
        tk.Label(head, text="Template Gallery", bg=_GAL_C["bg"],
                 fg=_GAL_C["text"], font=(FONT_UI, 17, "bold")
                 ).pack(side=tk.LEFT)
        self.count_lbl = tk.Label(head, text="", bg=_GAL_C["bg"],
                                  fg=_GAL_C["muted"], font=(FONT_UI, 9))
        self.count_lbl.pack(side=tk.LEFT, padx=(12, 0))

        close = tk.Label(head, text="✕", bg=_GAL_C["bg"], fg=_GAL_C["muted"],
                         font=(FONT_UI, 12, "bold"), cursor="hand2")
        close.pack(side=tk.RIGHT)
        close.bind("<Button-1>", lambda e: self.destroy())

        tk.Label(self, text="Every scaffold the studio knows — search, "
                            "filter by category, star favourites to keep "
                            "them on top.",
                 bg=_GAL_C["bg"], fg=_GAL_C["secondary"], font=(FONT_UI, 10)
                 ).pack(anchor="w", padx=26)

        searchrow = tk.Frame(self, bg=_GAL_C["bg"])
        searchrow.pack(fill=tk.X, padx=26, pady=(12, 4))
        self.search = tk.Entry(searchrow, bg=_GAL_C["input"],
                               fg=_GAL_C["text"], insertbackground=_GAL_C["text"],
                               relief=tk.FLAT, font=(FONT_UI, 11),
                               highlightthickness=1,
                               highlightbackground=_GAL_C["border"],
                               highlightcolor=self.accent)
        self.search.pack(fill=tk.X, ipady=7)
        self.search.bind("<KeyRelease>", self._on_search)

        chips = tk.Frame(self, bg=_GAL_C["bg"])
        chips.pack(fill=tk.X, padx=26, pady=(6, 0))
        self.chip_widgets = {}
        present = []
        for cat in _CATEGORIES:
            if cat == "All":
                present.append(cat)
                continue
            if any(info[3] == cat for info in self.templates.values()):
                present.append(cat)
        for cat in present:
            chip = tk.Label(chips, text=cat, bg=_GAL_C["input"],
                            fg=_GAL_C["secondary"], font=(FONT_UI, 9, "bold"),
                            padx=11, pady=4, cursor="hand2")
            chip.pack(side=tk.LEFT, padx=(0, 6))
            chip.bind("<Button-1>", lambda e, c=cat: self.set_category(c))
            self.chip_widgets[cat] = chip
        self._style_chips()

    def _focus_search(self):
        try:
            self.search.focus_set()
        except tk.TclError:
            pass

    def _on_search(self, event=None):
        if event and event.keysym in ("Escape",):
            return
        self.query = self.search.get().strip().lower()
        self.apply_filter()

    def set_category(self, cat):
        self.category = cat
        self._style_chips()
        self.apply_filter()

    def _style_chips(self):
        for cat, chip in self.chip_widgets.items():
            active = cat == self.category
            chip.config(bg=self.accent if active else _GAL_C["input"],
                        fg="#ffffff" if active else _GAL_C["secondary"])

    # --------------------------------------------------------------- body
    def _build_body(self):
        outer = tk.Frame(self, bg=_GAL_C["bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=26, pady=(10, 14))

        self.canvas = tk.Canvas(outer, bg=_GAL_C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(outer, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.grid_frame = tk.Frame(self.canvas, bg=_GAL_C["bg"])
        self.grid_win = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self.grid_win, width=e.width))
        # mouse wheel scrolling (Windows/Linux + mac deltas)
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))

    def _wheel(self, event):
        delta = -1 if getattr(event, "delta", 0) > 0 else 1
        self.canvas.yview_scroll(delta * 2, "units")

    # ------------------------------------------------------------ filtering
    def matches(self, kind, info):
        label, pitch, _badge, category = info
        if self.category != "All" and category != self.category:
            return False
        if not self.query:
            return True
        hay = f"{kind} {label} {pitch} {category}".lower()
        return all(tok in hay for tok in self.query.split())

    def apply_filter(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        favs = get_favorites(self.config)
        kinds = [k for k, info in self.templates.items() if self.matches(k, info)]
        # favourites first, then alphabetical
        kinds.sort(key=lambda k: (k not in favs, k))
        shown = 0
        cols = 3
        for i, kind in enumerate(kinds):
            self._card(self.grid_frame, kind, i // cols, i % cols)
            shown += 1
        if not shown:
            tk.Label(self.grid_frame,
                     text="Nothing matches that search — try another word.",
                     bg=_GAL_C["bg"], fg=_GAL_C["muted"], font=(FONT_UI, 10)
                     ).grid(row=0, column=0, columnspan=cols, pady=28)
            self.grid_frame.grid_columnconfigure(tuple(range(cols)), weight=1)
        total = len(self.templates)
        star_txt = f" · {len(favs)} favourite{'s' if len(favs) != 1 else ''}" if favs else ""
        self.count_lbl.config(
            text=f"{total} templates · {len(_CATEGORIES) - 1} categories{star_txt}")

    # -------------------------------------------------------------- cards
    def _card(self, parent, kind, row, col):
        label, pitch, badge, category = self.templates[kind]
        favs = get_favorites(self.config)
        starred = kind in favs

        card = tk.Frame(parent, bg=_GAL_C["card"], highlightthickness=2,
                        highlightbackground=_GAL_C["border"],
                        highlightcolor=self.accent, cursor="hand2")
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew",
                  ipadx=4, ipady=4)
        parent.grid_columnconfigure(col, weight=1, uniform="galcards")

        head = tk.Frame(card, bg=_GAL_C["card"])
        head.pack(fill=tk.X, padx=12, pady=(9, 0))
        tk.Label(head, text=badge, bg=_GAL_C["card"], fg=self.accent,
                 font=(FONT_MONO, 9, "bold")).pack(side=tk.LEFT)
        cat_lbl = tk.Label(head, text=category, bg=_GAL_C["card"],
                           fg=_GAL_C["muted"], font=(FONT_UI, 7, "bold"))
        cat_lbl.pack(side=tk.RIGHT)
        star = tk.Label(head, text="★" if starred else "☆",
                        bg=_GAL_C["card"],
                        fg=_GAL_C["star"] if starred else _GAL_C["muted"],
                        font=(FONT_UI, 12), cursor="hand2")
        star.pack(side=tk.RIGHT, padx=(0, 8))

        tk.Label(card, text=label, bg=_GAL_C["card"], fg=_GAL_C["text"],
                 font=(FONT_UI, 11, "bold"), wraplength=220,
                 justify=tk.LEFT).pack(padx=12, anchor="w")
        tk.Label(card, text=pitch, bg=_GAL_C["card"], fg=_GAL_C["secondary"],
                 font=(FONT_UI, 8), wraplength=230,
                 justify=tk.LEFT).pack(padx=12, pady=(2, 4), anchor="w")

        files = template_preview_files(kind)
        if files:
            shown = "\n".join("· " + f for f in files[:4])
            if len(files) > 4:
                shown += f"\n· +{len(files) - 4} more"
            tk.Label(card, text=shown, bg=_GAL_C["card"], fg=_GAL_C["muted"],
                     font=(FONT_MONO, 7), justify=tk.LEFT
                     ).pack(padx=12, anchor="w", pady=(0, 4))

        use = tk.Label(card, text="Use template  →", bg=_GAL_C["card"],
                       fg=self.accent, font=(FONT_UI, 9, "bold"),
                       cursor="hand2")
        use.pack(padx=12, pady=(0, 10), anchor="w")

        star.bind("<Button-1>",
                  lambda e, k=kind: self._toggle_star(k))
        for w in (card, use, head, cat_lbl):
            w.bind("<Button-1>", lambda e, k=kind: self._pick(k))
        card.bind("<Enter>", lambda e: card.config(
            highlightbackground=self.accent))
        card.bind("<Leave>", lambda e: card.config(
            highlightbackground=_GAL_C["border"]))

    def _toggle_star(self, kind):
        toggle_favorite(self.config, kind)
        self.apply_filter()          # re-sort + repaint stars

    def _pick(self, kind):
        label = self.templates[kind][0]
        if self.on_pick:
            self.destroy()
            self.on_pick(kind)
        else:
            messagebox.showinfo(
                "Template Gallery",
                f"“{label}” selected — open it from the Project Hub to "
                f"scaffold a workspace.")

    # ------------------------------------------------------------- layout
    def _center(self):
        self.update_idletasks()
        self.geometry(f"{GALLERY_W}x{GALLERY_H}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{GALLERY_W}x{GALLERY_H}"
                      f"+{(sw - GALLERY_W) // 2}+{max(20, (sh - GALLERY_H) // 2 - 20)}")


def open_gallery(master, config, accent, on_pick=None):
    """Open the template gallery. ``on_pick(kind)`` receives the chosen
    template kind (Project Hub passes its create-workspace flow)."""
    return TemplateGallery(master, config, accent, on_pick)
