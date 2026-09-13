# DXN1 STUDIO

Custom IDE GUI built from scratch with Python & Tkinter.

## Installation

Install globally with a single curl command:

```bash
curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/main/install.sh | bash
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

## Features

- Dark theme interface
- File explorer sidebar
- Tab system for multiple files
- Basic code editor with line numbers
- Terminal/output panel
- Menu bar with File, Edit, View, Help

## Requirements

- Python 3.8+
- Tkinter (usually included with Python)

## Project Structure

```
DXN1-STUDIO/
├── dxn1-studio      # Main Python GUI application
├── install.sh       # Curl-based installer
└── README.md        # Documentation
```

## License

MIT
