#!/bin/bash
# DXN1 STUDIO Installer v2.0.0
# Usage: curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash

set -e

INSTALL_DIR="$HOME/.local/share/dxn1-studio"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/DXN1-STUDIO"
REPO="https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   DXN1 STUDIO Installer v2.0.0 (beta)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not found."
    echo "Please install Python 3.8+ from your package manager."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Found Python $PYTHON_VERSION"

# Check for Tkinter
if ! python3 -c 'import tkinter' &> /dev/null; then
    echo "ERROR: Tkinter is required but not found."
    echo "Install it with:  apt install python3-tk   (Debian/Ubuntu/Termux)"
    echo "                   dnf install python3-tkinter  (Fedora)"
    exit 1
fi
echo "✓ Found Tkinter"

# Create directories
mkdir -p "$INSTALL_DIR/dxn1_studio"
mkdir -p "$INSTALL_DIR/assets"
mkdir -p "$BIN_DIR"

echo "✓ Created installation directories"

# Download application files
echo "↓ Downloading DXN1 STUDIO..."

download() {
    local dest="$1"; shift
    local rel="$1"; shift
    local optional="$1"; shift
    if curl -fsSL "$REPO/$rel" -o "$dest"; then
        echo "  ✓ $rel"
    else
        if [ "$optional" = "optional" ]; then
            echo "  ⚠ skipped optional asset: $rel"
        else
            echo "ERROR: failed to download $rel"
            exit 1
        fi
    fi
}

download "$INSTALL_DIR/dxn1-studio" "dxn1-studio" required
download "$INSTALL_DIR/README.md" "README.md" required
for f in __init__.py app.py config.py theme.py widgets.py onboarding.py tour.py; do
    download "$INSTALL_DIR/dxn1_studio/$f" "dxn1_studio/$f" required
done
for f in logo.png welcome_hero.png; do
    download "$INSTALL_DIR/assets/$f" "assets/$f" optional
done

chmod +x "$INSTALL_DIR/dxn1-studio"

echo "✓ Downloaded application files"

# Create launcher script
cat > "$LAUNCHER" << 'LAUNCHEREOF'
#!/bin/bash
# DXN1 STUDIO Launcher

INSTALL_DIR="$HOME/.local/share/dxn1-studio"

if [ ! -f "$INSTALL_DIR/dxn1-studio" ]; then
    echo "ERROR: DXN1 STUDIO is not installed."
    echo "Run: curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash"
    exit 1
fi

exec python3 "$INSTALL_DIR/dxn1-studio" "$@"
LAUNCHEREOF

chmod +x "$LAUNCHER"

echo "✓ Created launcher: $LAUNCHER"

# Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠ $BIN_DIR is not in your PATH"
    echo "  Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To launch DXN1 STUDIO:"
echo "  DXN1-STUDIO"
echo ""
echo "Or run directly:"
echo "  python3 $INSTALL_DIR/dxn1-studio"
echo ""
echo "First launch opens the welcome wizard — pick your theme and accent"
echo "colour, then take the guided tour. Enjoy!"
echo ""
