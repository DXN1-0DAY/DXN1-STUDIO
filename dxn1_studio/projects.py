"""DXN1 STUDIO — workspaces & project scaffolding.

A "workspace" is any folder the studio keeps track of, optionally stamped
with a ``.dxn1-project.json`` metadata file. The Project Hub uses the
templates below to scaffold a new Python script, Flask web app, Tkinter
app or an empty workspace in seconds.

The recent-workspaces registry lives in the user's config JSON so the Hub
can greet returning users with their latest work.
"""

import json
import os
import re
import time


# ------------------------------------------------------------------ metadata
PROJECT_FILE = ".dxn1-project.json"
DEFAULT_PROJECTS_ROOT = os.path.join(os.path.expanduser("~"), "DXN1")

# kind -> (label, one-line pitch, font-safe badge shown on hub cards)
TEMPLATE_INFO = {
    "python":  ("Python Script", "Ready-to-run main.py — zero dependencies.", "main.py"),
    "flask":   ("Flask Web App",  "app.py + template — run it, get a website.", "app.py"),
    "fastapi": ("FastAPI App",    "JSON route + requirements — API in seconds.", "api"),
    "requests": ("Requests Quickstart", "API script — install requests, hit F5.", "GET"),
    "tkinter": ("Tkinter Desktop App", "Native window demo, grow it into a GUI tool.", "window"),
    "package": ("Python Package", "Module + tests + pyproject — pip-installable.", "pkg"),
    "cli":     ("CLI Tool",       "argparse app — flags, help, subcommands.", "cli"),
    "static":  ("Static Website", "HTML + CSS + JS — no build step, no deps.", "web"),
    "game":    ("Canvas Game",     "Tkinter game loop — keys, score, restart. F5 to play.", "game"),
    "rust":    ("Rust Project",   "Cargo.toml + hello main.rs — cargo run ready.", "rust"),
    "nextjs":  ("Next.js App",    "pages + API route — the React framework, no npx.", "next"),
    "svelte":  ("Svelte Kit",     "App.svelte + vite — runes-ready starter.", "svelte"),
    "go":      ("Go Module",      "go.mod + main.go — idiomatic hello server.", "go"),
    "empty":   ("Empty Workspace", "A clean folder for your own ideas.", "folder"),
}

KIND_ORDER = ("python", "flask", "fastapi", "requests",
              "tkinter", "package", "cli", "static", "game",
              "rust", "go", "nextjs", "svelte", "empty")


def slugify(name):
    """'My Cool App!' -> 'My-Cool-App' (safe as a folder name)."""
    slug = re.sub(r"[^\w\s-]", "", str(name)).strip()
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug or "workspace"


def ensure_projects_root():
    os.makedirs(DEFAULT_PROJECTS_ROOT, exist_ok=True)
    return DEFAULT_PROJECTS_ROOT


# ------------------------------------------------------------------ templates
_FLASK_APP = '''"""{name} — Flask web app, scaffolded by DXN1 STUDIO."""
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", name={name!r})


if __name__ == "__main__":
    # dev server — visit http://127.0.0.1:5000
    app.run(debug=True)
'''

_FLASK_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ name }}</title>
  <style>
    :root {{ --violet: #7c3aed; }}
    * {{ box-sizing: border-box; margin: 0; }}
    body {{
      min-height: 100vh; display: grid; place-items: center;
      background: #0d1117; color: #e6edf3;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    }}
    .card {{
      background: #131a22; border: 1px solid #232c3d; border-radius: 14px;
      padding: 48px 56px; text-align: center; max-width: 560px;
    }}
    h1 {{ font-size: 2rem; margin-bottom: 8px; }}
    h1 span {{ color: var(--violet); }}
    p {{ color: #9aa7b8; line-height: 1.6; }}
    code {{ background: #0d1117; padding: 2px 8px; border-radius: 6px;
           color: #c4b5fd; font-size: 0.9em; }}
  </style>
</head>
<body>
  <main class="card">
    <h1>It works — <span>{{ name }}</span> is live.</h1>
    <p>Your Flask app is being served. Edit <code>templates/index.html</code>
       and refresh to see changes.</p>
  </main>
</body>
</html>
'''

_PY_SCRIPT = '''"""{name} — created with DXN1 STUDIO."""


def main():
    print("Hello from {name}!")
    print("Hit the Run button (or F5) in DXN1 STUDIO to see this output.")


if __name__ == "__main__":
    main()
'''

_CLI_APP = '''"""{name} — a command-line tool scaffolded by DXN1 STUDIO.

Try it:  python {slug}.py greet --name Ada
         python {slug}.py roll --sides 20
"""
import argparse
import random


def greet(args):
    print(f"Hello, {{args.name or 'world'}}! Welcome to {name}.")


def roll(args):
    value = random.randint(1, args.sides)
    print(f"d{{args.sides}} -> {{value}}"
          + ("  (critical!)" if value == args.sides else ""))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="{slug}",
        description="{name} — small, sharp, does exactly what it says.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_greet = sub.add_parser("greet", help="say hello")
    p_greet.add_argument("--name", default="", help="who to greet")
    p_greet.set_defaults(func=greet)

    p_roll = sub.add_parser("roll", help="roll a die")
    p_roll.add_argument("--sides", type=int, default=6,
                        help="how many sides")
    p_roll.set_defaults(func=roll)
    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
'''

_GAME_APP = '''"""{name} — a Canvas game, scaffolded by DXN1 STUDIO.

A complete mini game in one file: arrow keys / WASD to move, catch the
purple orbs, dodge the red ones. Three lives, score ramps up, R to
restart. Built on a plain Tkinter Canvas + after() loop — no deps.
"""

import random
import tkinter as tk

W, H = 640, 420
PLAYER_SPEED = 6
SPAWN_MS = 900               # new falling block every …
TICK_MS = 16                 # ~60 fps

GOOD, BAD = "#7c3aed", "#e5484d"


class Game:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=W, height=H, bg="#0d0b14",
                                highlightthickness=0)
        self.canvas.pack()
        root.title("{name}")
        root.bind("<KeyPress>", self.on_key)
        root.bind("<KeyRelease>", self.on_keyup)
        self.reset()
        self.loop()

    # ------------------------------------------------------------- state
    def reset(self):
        self.px = W // 2                 # player x (paddle near the bottom)
        self.keys = set()
        self.blocks = []                 # [x, y, speed, good]
        self.score = 0
        self.lives = 3
        self.over = False
        self.root.after(SPAWN_MS, self.spawn)

    # ------------------------------------------------------------ helpers
    def spawn(self):
        if not self.over:
            good = random.random() < 0.7          # 70% goodies
            self.blocks.append([random.randint(16, W - 16), -16,
                                random.uniform(2.2, 4.6), good])
        self.root.after(max(280, SPAWN_MS - self.score * 6), self.spawn)

    def on_key(self, event):
        key = event.keysym.lower()
        if key in ("left", "a"):
            self.keys.add("L")
        elif key in ("right", "d"):
            self.keys.add("R")
        elif key == "r" and self.over:
            self.over = False
            self.reset()

    def on_keyup(self, event):
        key = event.keysym.lower()
        if key in ("left", "a"):
            self.keys.discard("L")
        elif key in ("right", "d"):
            self.keys.discard("R")

    # --------------------------------------------------------------- loop
    def loop(self):
        c = self.canvas
        c.delete("all")
        if not self.over:
            if "L" in self.keys:
                self.px = max(28, self.px - PLAYER_SPEED)
            if "R" in self.keys:
                self.px = min(W - 28, self.px + PLAYER_SPEED)
            alive = []
            for b in self.blocks:
                b[1] += b[2]
                caught = abs(b[0] - self.px) < 42 and 6 < b[1] < 34
                if caught:
                    if b[3]:
                        self.score += 1
                    else:
                        self.lives -= 1
                        if self.lives <= 0:
                            self.over = True
                    continue
                if b[1] < H + 20:
                    alive.append(b)
            self.blocks = alive
        # ---- draw
        c.create_rectangle(self.px - 40, H - 26, self.px + 40, H - 12,
                           fill="#ffffff", outline="")
        for x, y, _, good in self.blocks:
            c.create_oval(x - 9, y - 9, x + 9, y + 9,
                          fill=GOOD if good else BAD, outline="")
        c.create_text(14, 12, anchor="nw", fill="#c9c2e8", font=(
            "TkFixedFont", 11), text=f"score {{self.score}}   "
                                     f"lives {{'●' * max(0, self.lives)}}")
        if self.over:
            c.create_rectangle(0, H // 2 - 44, W, H // 2 + 44,
                               fill="#0d0b14", stipple="gray50")
            c.create_text(W // 2, H // 2 - 12, fill="#ffffff",
                          font=("TkDefaultFont", 18, "bold"),
                          text=f"Game over — score {{self.score}}")
            c.create_text(W // 2, H // 2 + 16, fill="#c9c2e8",
                          font=("TkFixedFont", 11),
                          text="press R to restart")
        self.root.after(TICK_MS, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()
'''

_STATIC_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main>
    <h1>{name}</h1>
    <p>A static site — open it in any browser, no build step needed.</p>
    <button id="magic">Click me</button>
    <p id="out"></p>
  </main>
  <script src="script.js"></script>
</body>
</html>
'''

_STATIC_CSS = '''/* {name} — styles */
:root {{ --accent: #7c3aed; }}
* {{ box-sizing: border-box; margin: 0; }}
body {{
  min-height: 100vh; display: grid; place-items: center;
  background: #0d1117; color: #e6edf3;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}}
main {{ max-width: 560px; text-align: center; padding: 32px; }}
h1 {{ font-size: 2rem; margin-bottom: 12px; }}
h1::after {{ content: ""; display: block; width: 64px; height: 4px;
  background: var(--accent); border-radius: 2px; margin: 12px auto 0; }}
p {{ color: #9aa7b8; line-height: 1.6; margin: 12px 0; }}
button {{
  background: var(--accent); color: white; border: 0; cursor: pointer;
  padding: 10px 22px; border-radius: 10px; font-size: 1rem;
}}
button:hover {{ filter: brightness(1.15); }}
#out {{ color: #c4b5fd; min-height: 1.4em; }}
'''

_STATIC_JS = '''// {name} — scripts
document.getElementById("magic").addEventListener("click", () => {{
  const lines = [
    "It works!", "Edit script.js and refresh.",
    "DXN1 STUDIO — built for flow.",
  ];
  const out = document.getElementById("out");
  out.textContent = lines[Math.floor(Math.random() * lines.length)];
}});
'''


_TK_APP = '''"""{name} — Tkinter desktop app, scaffolded by DXN1 STUDIO."""
import tkinter as tk


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("{name}")
        self.geometry("420x260")
        self.configure(bg="#0d1117")

        tk.Label(self, text="{name}", bg="#0d1117", fg="#e6edf3",
                 font=("Segoe UI", 18, "bold")).pack(pady=(48, 6))
        tk.Label(self, text="A native desktop app — no dependencies needed.",
                 bg="#0d1117", fg="#9aa7b8", font=("Segoe UI", 10)).pack()
        tk.Button(self, text="Click me", command=self.poke,
                  bg="#7c3aed", fg="white", relief="flat",
                  padx=18, pady=6, cursor="hand2").pack(pady=24)
        self.clicks = 0

    def poke(self):
        self.clicks += 1
        print(f"clicked {{self.clicks}}x")


if __name__ == "__main__":
    App().mainloop()
'''

_FASTAPI_APP = '''"""{name} — FastAPI app, scaffolded by DXN1 STUDIO.

Install the deps first (Tools → Manage Packages, or pip):
    fastapi  ·  uvicorn
Then run:  uvicorn main:app --reload
And open:  http://127.0.0.1:8000  ·  docs at /docs
"""
from fastapi import FastAPI

app = FastAPI(title={name!r})


@app.get("/")
def index():
    return {{"app": {name!r}, "status": "running", "studio": "DXN1 STUDIO"}}


@app.get("/hello/{{who}}")
def hello(who: str):
    return {{"message": f"Hello, {{who}}!"}}
'''

_REQUESTS_SCRIPT = '''"""{name} — requests quickstart, scaffolded by DXN1 STUDIO.

Install the dependency first: Tools → Manage Packages → requests
(or: pip install requests), then hit F5.
"""
import requests

API = "https://api.github.com/repos/DXN1-termux/DXN1-STUDIO"


def main():
    try:
        resp = requests.get(API, timeout=10,
                            headers={{"User-Agent": "DXN1-Studio"}})
        resp.raise_for_status()
        data = resp.json()
        print(f"{{data['full_name']}} — {{data['stargazers_count']}} stars "
              f"and {{data['open_issues_count']}} open issues")
    except requests.RequestException as exc:
        print(f"request failed: {{exc}}")
        return 1
    print("Now edit this script and press F5 to make it yours.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

_PKG_CORE = '''"""Core helpers for {pkg}."""


def greet(target: str = "world") -> str:
    return f"Hello, {{target}}! From {{__name__.split('.')[0]}}."
'''

_PKG_TEST = '''"""Tests for {pkg} — run with pytest (install it from Packages)."""
from {pkg}.core import greet


def test_greet_default():
    assert greet() == "Hello, world! From {pkg}."


def test_greet_custom():
    assert greet("DXN1") == "Hello, DXN1! From {pkg}."
'''

_PKG_PYPROJECT = '''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{slug}"
version = "0.1.0"
description = "{name} — built with DXN1 STUDIO"
requires-python = ">=3.8"
'''

_README_MD = """# {name}

Created with **DXN1 STUDIO**.

## Getting started

- Open this folder in DXN1 STUDIO (`File -> Open Workspace…`)
- Press **Run** (F5) to execute the active file
- Optional extras (Flask, requests, …) live in **Tools -> Manage Packages**
"""


def template_files(kind, name):
    """Relative-path -> content mapping for a scaffold, with the project
    name rendered in. Returns {} for an empty workspace."""
    if kind == "python":
        return {"main.py": _PY_SCRIPT.format(name=name)}
    if kind == "flask":
        return {
            "app.py": _FLASK_APP.format(name=name),
            "templates/index.html": _FLASK_HTML,
            "requirements.txt": "flask>=3.0\n",
        }
    if kind == "fastapi":
        return {
            "main.py": _FASTAPI_APP.format(name=name),
            "requirements.txt": "fastapi>=0.110\nuvicorn>=0.29\n",
        }
    if kind == "requests":
        return {
            "main.py": _REQUESTS_SCRIPT.format(name=name),
            "requirements.txt": "requests>=2.31\n",
        }
    if kind == "package":
        slug = slugify(name).lower().replace("-", "_")
        pkg = slug if slug[:1].isalpha() else f"pkg_{slug}"
        return {
            f"{pkg}/__init__.py":
                f'"""{name} — a Python package scaffolded by '
                f'DXN1 STUDIO."""\n\n__version__ = "0.1.0"\n',
            f"{pkg}/core.py": _PKG_CORE.format(pkg=pkg),
            f"tests/test_core.py": _PKG_TEST.format(pkg=pkg),
            "pyproject.toml": _PKG_PYPROJECT.format(
                slug=pkg, name=name),
            "README.md": _README_MD.format(name=name),
        }
    if kind == "tkinter":
        return {"main.py": _TK_APP.format(name=name)}
    if kind == "cli":
        slug = slugify(name).lower().replace("-", "_")
        return {
            f"{slug}.py": _CLI_APP.format(name=name, slug=slug),
            "README.md": _README_MD.format(name=name),
        }
    if kind == "static":
        return {
            "index.html": _STATIC_HTML.format(name=name),
            "style.css": _STATIC_CSS.format(name=name),
            "script.js": _STATIC_JS.format(name=name),
        }
    if kind == "game":
        return {"main.py": _GAME_APP.format(name=name)}
    if kind == "rust":
        slug = slugify(name).replace("-", "_")
        pkg = slug if slug[:1].isalpha() else f"app_{slug}"
        return {
            "Cargo.toml":
                '[package]\nname = "' + pkg + '"\nversion = "0.1.0"\n'
                'edition = "2021"\n',
            "src/main.rs":
                '// ' + name + ' — scaffolded by DXN1 STUDIO\n'
                'fn main() {\n'
                '    println!("Hello from ' + name + '!");\n'
                '}\n',
            "README.md": _README_MD.format(name=name),
        }
    if kind == "go":
        slug = slugify(name).lower().replace("-", "_")
        mod = slug if slug[:1].isalpha() else f"app{slug}"
        return {
            "go.mod": "module " + mod + "\n\ngo 1.22\n",
            "main.go":
                '// ' + name + ' — scaffolded by DXN1 STUDIO\n'
                'package main\n\n'
                'import "fmt"\n\n'
                'func main() {\n'
                '    fmt.Println("Hello from ' + name + '!")\n'
                '}\n',
            "README.md": _README_MD.format(name=name),
        }
    if kind == "nextjs":
        return {
            "package.json":
                '{\n  "name": "' + slugify(name).lower() + '",\n'
                '  "scripts": {\n    "dev": "next dev",\n'
                '    "build": "next build",\n    "start": "next start"\n  },\n'
                '  "dependencies": {\n    "next": "^14.0.0",\n'
                '    "react": "^18.0.0",\n    "react-dom": "^18.0.0"\n  }\n}\n',
            "pages/index.js":
                '// ' + name + ' — scaffolded by DXN1 STUDIO\n'
                'export default function Home() {\n'
                '  return (\n    <main>\n'
                '      <h1>Hello from ' + name + '!</h1>\n'
                '    </main>\n  )\n}\n',
            "pages/api/hello.js":
                'export default function handler(req, res) {\n'
                '  res.status(200).json({ hello: "world" })\n}\n',
            "README.md": _README_MD.format(name=name),
        }
    if kind == "svelte":
        return {
            "package.json":
                '{\n  "name": "' + slugify(name).lower() + '",\n'
                '  "type": "module",\n'
                '  "scripts": {\n    "dev": "vite",\n    "build": "vite build"\n  },\n'
                '  "devDependencies": {\n    "svelte": "^4.0.0",\n'
                '    "vite": "^5.0.0",\n    "@sveltejs/vite-plugin-svelte": "^3.0.0"\n  }\n}\n',
            "App.svelte":
                '<!-- ' + name + ' — scaffolded by DXN1 STUDIO -->\n'
                '<script>\n  let count = 0\n</script>\n\n'
                '<main>\n  <h1>Hello from ' + name + '!</h1>\n'
                '  <button on:click={() => count++}>count is {count}</button>\n'
                '</main>\n',
            "index.html":
                '<!doctype html>\n<html>\n  <body>\n'
                '    <div id="app"></div>\n'
                '    <script type="module" src="/src/main.js"></script>\n'
                '  </body>\n</html>\n',
            "src/main.js":
                "import App from '../App.svelte'\n"
                "import { mount } from 'svelte'\n\n"
                "const app = mount(App, { target: document.getElementById('app') })\n"
                '\nexport default app\n',
            "README.md": _README_MD.format(name=name),
        }
    if kind == "empty":
        return {"README.md": _README_MD.format(name=name)}
    return {}


def scaffold(kind, parent_dir, name):
    """Create a new workspace folder + starter files.

    Returns (path, kind). Raises FileExistsError only if every uniqueness
    attempt collides, which is practically impossible.
    """
    kind = kind if kind in TEMPLATE_INFO else "empty"
    parent = os.path.expanduser(parent_dir or DEFAULT_PROJECTS_ROOT)
    os.makedirs(parent, exist_ok=True)

    base = slugify(name)
    target = os.path.join(parent, base)
    n = 2
    while os.path.exists(target):
        target = os.path.join(parent, f"{base}-{n}")
        n += 1
        if n > 99:
            raise FileExistsError(target)

    os.makedirs(target)
    for rel, content in template_files(kind, name).items():
        full = os.path.join(target, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)

    meta = {
        "name": name,
        "kind": kind,
        "studio": "DXN1 STUDIO",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(target, PROJECT_FILE), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return target, kind


def read_project_meta(path):
    """Return {'name':…, 'kind':…} for a workspace folder (or None)."""
    meta_path = os.path.join(path, PROJECT_FILE)
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return {
                    "name": data.get("name") or os.path.basename(path),
                    "kind": data.get("kind") if data.get("kind") in TEMPLATE_INFO
                            else "empty",
                }
        except (OSError, json.JSONDecodeError):
            pass
    # infer from layout — keeps older/foreign folders first-class citizens
    if os.path.isfile(os.path.join(path, "app.py")) and \
            os.path.isdir(os.path.join(path, "templates")):
        return {"name": os.path.basename(path), "kind": "flask"}
    if os.path.isfile(os.path.join(path, "main.py")):
        return {"name": os.path.basename(path), "kind": "python"}
    return {"name": os.path.basename(path), "kind": "empty"}


# ------------------------------------------------------------- recent list
def touch_recent(config, path, kind):
    """Move a workspace to the top of the recent list (deduped, capped 8)."""
    recents = list(config.get("recent_projects") or [])
    path = os.path.abspath(path)
    recents = [r for r in recents if r.get("path") != path]
    recents.insert(0, {"path": path, "kind": kind,
                       "opened": time.strftime("%Y-%m-%d %H:%M")})
    config.set("recent_projects", recents[:8])
    config.set("last_project", path)


def list_recent(config):
    """Recent workspaces that still exist on disk (oldest dropped silently)."""
    out = []
    for r in config.get("recent_projects") or []:
        p = r.get("path", "")
        if p and os.path.isdir(p):
            meta = read_project_meta(p)
            out.append({"path": p, "kind": meta["kind"],
                        "name": meta["name"], "opened": r.get("opened", "")})
    return out[:8]


def clear_recent(config):
    config.set("recent_projects", [])
    config.set("last_project", "")
