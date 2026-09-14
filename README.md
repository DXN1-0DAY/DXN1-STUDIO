# DXN1 STUDIO

A clean, modern IDE built from scratch with Python & Tkinter. Boot splash,
Project Hub, workspaces (Python / Flask / Tkinter / empty), one-click Run,
optional dependency manager, project export, and **DXN1 Agents** — the
sandboxed assistant that asks before it touches anything and can run on
your own API key or free model backends.

## Installation

Install globally with a single curl command:

```bash
curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash
```

After installation, add `~/.local/bin` to your PATH if not already present:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Launching

The boot sequence: you get the logo card for ~2 seconds, then the studio
rises. Any of these work:

```bash
dxn1 studio          # the classic way
dxn1                 # also fine
DXN1 STUDIO          # uppercase, unquoted → shell runs DXN1 with arg STUDIO
"DXN1 STUDIO"        # the launcher literally named with a space. Yes.
dxn1 studio ~/my-app # boot straight into a workspace
```

Useful flags:

```bash
dxn1 studio --reset-config    # wipe preferences and replay the welcome wizard
dxn1 studio --no-splash       # skip the boot splash this once
dxn1 studio --smoke-test      # headless self-check (CI-safe, temp config)
```

## First Launch

1. **Boot splash** — the logo card, two seconds, done
2. **Welcome wizard** — hero splash + your display name
3. **Make it yours** — dark/light theme + four accent colours (violet, cyan, green, orange)
4. **DXN1 Agents** *(optional)* — opt in to the built-in assistant
5. **Project Hub** — create your first workspace or explore the studio
6. **Guided tour** — a short spotlight walk across the real UI

Replay the wizard or tour anytime from the **Help** menu.

## Project Hub

Every session starts at the Hub:

- **New Python Script** — ready-to-run `main.py`
- **New Flask Web App** — `app.py` + template + `requirements.txt`
- **New Tkinter App** — native desktop starter
- **Empty Workspace** — a clean folder
- **Recent workspaces** — one click back into your latest work

Workspaces can live anywhere; DXN1 keeps track of them in
`~/.dxn1-studio/config.json`. Reopen the Hub anytime via **File → Project Hub**.

## The IDE

- Modern dark & light themes with 4 accent colours
- File explorer, closable tabs, line numbers, unlimited undo
- **Toolbar**: New · Open · Save · ▶ Run (F5) · ■ Stop · Packages · Export ZIP · Hub
- **Run system** — executes the active file (or your workspace's `app.py`/`main.py`)
  and streams output live into the terminal; status bar flips to “● Running”
- **Interactive terminal** — type `help` for studio commands:
  `run`, `stop`, `clear`, `packages`, `hub`, `export`, `agent <request>`,
  `settings` — and the classic `dxn1 studio` replays the boot splash
- Keyboard: Ctrl+N/O/S, F5 run, Ctrl+, settings

## Optional Packages (lightweight by default)

DXN1 installs **nothing** behind your back. **Tools → Manage Packages** is the
one opt-in page for the heavy stuff: Flask, Requests, httpx, Pillow, NumPy,
Rich, pytest, Black, Ruff — with live `pip` output, version detection and
uninstall. Power users can pip-install anything from the same window.

## Export

- **File → Export Project as ZIP…** — the whole workspace, skipping caches
  and venvs; Flask projects automatically get a `requirements.txt`
- **File → Export Current File As…** — just the file you're editing

## DXN1 Agents

The built-in copilot. Two layers:

**Instant skills (offline, always available)** — no key, no network:

- create files with starter templates (`create file utils.py`)
- scaffold a complete Flask app (`new flask app`)
- run your project (`run`) and install packages (`install flask`)
- open workspace files (`open app.py`), analyze the editor buffer (`explain`)
- propose raw commands (`shell python -V`)

**Model brains (Settings → DXN1 Agents → Brain)** — pick one:

| Brain | What it is | Cost |
|-------|------------|------|
| **Local skills** | The offline rule engine | free, no setup |
| **BYOK** | Your own API key on any OpenAI-compatible provider — OpenRouter, Groq, Google AI Studio, Mistral, OpenAI, Ollama (local), or a custom endpoint | your key; OpenRouter `:free` models cost nothing |
| **GitHub Models** | Free tier tracked via your GitHub login (`gh auth token` if you're signed in, or paste a PAT) | free, rate-limited |
| **Kilo gateway** | Free-model routing through a direct HTTP client built into the studio — deliberately *not* a bundled Kilo instance, so it adds near-zero RAM instead of hundreds of MB | your Kilo token |

The whole backend layer is standard-library `urllib` — no SDKs, no Node,
no helper processes.

**What the brain can do** (tool loop with up to `agents_max_steps` steps
per message): list and read workspace files, create/overwrite files,
surgical find/replace edits, and run commands inside the workspace —
feeding results back to the model until the task is done.

**Sandbox — the hard boundary:**

- only paths that resolve *inside the open workspace* are reachable;
  `..` traversal, absolute escapes and symlink escapes are rejected
- `.git`, `.ssh` and studio internals are off-limits to reads and writes
- commands run with the workspace as working directory
- **catastrophic commands** (`rm -rf /`, `sudo`, pipe-to-shell downloads,
  raw disk writes, forced pushes…) always require an explicit human
  Accept — even in full-access mode

**Permission model** — the whole point:

- **Ask mode** (default): every edit (with a unified diff preview) and
  every command arrives as a card with **Accept / Decline**
- **Full access**: turn both prompts off in the agent settings and it
  stops asking — edits apply and commands run immediately (dangerous
  commands still ask)
- the assistant can be disabled entirely; the panel disappears
- extra **system prompt** field for persona / house style

Find it in **Settings → DXN1 Agents** (or the ⚙ icon on the agent panel).
Keys are stored locally in `~/.dxn1-studio/config.json` only.

## Requirements

- Python 3.8+
- Tkinter (usually included; Debian/Ubuntu/Termux: `apt install python3-tk`)
- Pillow (optional — crisp image scaling, falls back automatically)
- Everything else is opt-in via the Packages page

## Project Structure

```
DXN1-STUDIO/
├── dxn1                     # CLI launcher (dxn1 studio / "DXN1 STUDIO")
├── DXN1 STUDIO              # yes, a launcher with a space
├── dxn1-studio              # classic entry point
├── dxn1_studio/
│   ├── app.py               # Main window, boot flow, run system, settings
│   ├── config.py            # ~/.dxn1-studio/config.json persistence
│   ├── theme.py             # Dark/light palettes + accent colours
│   ├── widgets.py           # File explorer, code editor, interactive terminal
│   ├── onboarding.py        # 4-step welcome wizard (incl. Agents opt-in)
│   ├── tour.py              # Interactive guided tour
│   ├── projects.py          # Workspace scaffolds + recent registry
│   ├── hub.py               # Project Hub start screen
│   ├── splash.py            # Boot splash (logo card)
│   ├── packages.py          # Optional dependency manager
│   ├── export.py            # ZIP / file export
│   ├── agent.py             # DXN1 Agents panel + brain/permission settings
│   ├── sandbox.py           # Workspace jail, tool protocol, agent engine
│   └── llm.py               # Backends: BYOK presets, GitHub Models, Kilo
├── assets/                  # Logo & generated artwork
├── install.sh               # Curl-based installer
└── README.md
```

## License

MIT
