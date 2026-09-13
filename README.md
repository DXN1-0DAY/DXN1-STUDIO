# DXN1 STUDIO

A clean, modern IDE built from scratch with Python & Tkinter. Dark + light themes,
accent colours, and a guided first-launch experience.

## Installation

Install globally with a single curl command:

```bash
curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash
```

After installation, add `~/.local/bin` to your PATH if not already present:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Usage

Launch the IDE from anywhere:

```bash
DXN1-STUDIO
```

Useful flags:

```bash
DXN1-STUDIO --reset-config    # wipe preferences and replay the welcome wizard
DXN1-STUDIO --smoke-test      # run a headless self-check (wizard → tour → exit)
```

## First Launch

The first time DXN1 STUDIO opens, a three-step welcome wizard guides you through:

1. **Welcome** — hero splash and your display name (used for greetings)
2. **Make it yours** — dark or light theme + four accent colours (violet, cyan, green, orange)
3. **Ready** — summary, then a short interactive tour of the real UI

After that the studio just opens and remembers you. Replay the wizard or tour
anytime from the **Help** menu.

## Features

- Modern dark & light themes with 4 accent colours
- Guided first-launch wizard + interactive UI tour
- File explorer sidebar
- Tab system with closable tabs
- Code editor with line numbers and unlimited undo
- Built-in terminal / output panel
- Status bar with live file indicator and version chip
- Working Edit menu (undo/redo/cut/copy/paste) and Ctrl+N/O/S shortcuts

## Requirements

- Python 3.8+
- Tkinter (usually included with Python; on Debian/Ubuntu/Termux: `apt install python3-tk`)
- Pillow (optional — used for crisp image scaling, falls back automatically)

## Project Structure

```
DXN1-STUDIO/
├── dxn1-studio              # Entry point
├── dxn1_studio/
│   ├── app.py               # Main window & session orchestration
│   ├── config.py            # ~/.dxn1-studio/config.json persistence
│   ├── theme.py             # Dark/light palettes + accent colours
│   ├── widgets.py           # File explorer, code editor, terminal
│   ├── onboarding.py        # Welcome wizard (first launch)
│   └── tour.py              # Interactive guided tour
├── assets/                  # Logo & onboarding artwork
├── install.sh               # Curl-based installer
└── README.md
```

## License

MIT
