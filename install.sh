#!/bin/bash
# DXN1 STUDIO Installer v2.1.0
# Usage: curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash

set -e

INSTALL_DIR="$HOME/.local/share/dxn1-studio"
BIN_DIR="$HOME/.local/bin"
REPO="https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   DXN1 STUDIO Installer v2.1.0 (beta)"
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

# entry points
download "$INSTALL_DIR/dxn1-studio" "dxn1-studio" required
download "$INSTALL_DIR/dxn1" "dxn1" required
download "$INSTALL_DIR/DXN1 STUDIO" "DXN1%20STUDIO" required
download "$INSTALL_DIR/README.md" "README.md" required

# package modules
for f in __init__.py app.py config.py theme.py widgets.py onboarding.py \
         tour.py projects.py hub.py splash.py packages.py export.py agent.py \
         sandbox.py llm.py; do
    download "$INSTALL_DIR/dxn1_studio/$f" "dxn1_studio/$f" required
done

# art assets (optional — the IDE falls back to geometric art without them)
for f in logo.png welcome_hero.png hub_hero.png agents_hero.png; do
    download "$INSTALL_DIR/assets/$f" "assets/$f" optional
done

chmod +x "$INSTALL_DIR/dxn1-studio" "$INSTALL_DIR/dxn1" "$INSTALL_DIR/DXN1 STUDIO"

echo "✓ Downloaded application files"

# CLI commands in ~/.local/bin
ln -sf "$INSTALL_DIR/dxn1" "$BIN_DIR/dxn1"
ln -sf "$INSTALL_DIR/dxn1" "$BIN_DIR/DXN1"
ln -sf "$INSTALL_DIR/dxn1" "$BIN_DIR/dxn1-studio"
ln -sf "$INSTALL_DIR/dxn1" "$BIN_DIR/DXN1-STUDIO"
cp "$INSTALL_DIR/DXN1 STUDIO" "$BIN_DIR/DXN1 STUDIO"
chmod +x "$BIN_DIR/DXN1 STUDIO"

echo "✓ Installed CLI: dxn1 · DXN1 · dxn1-studio · DXN1-STUDIO · \"DXN1 STUDIO\""

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
echo "To launch DXN1 STUDIO (boot splash, then the studio):"
echo "  dxn1 studio"
echo ""
echo "Feeling dramatic? This also works:"
echo "  \"DXN1 STUDIO\""
echo ""
echo "First launch opens the welcome wizard — pick your theme, meet"
echo "DXN1 Agents, then land in the Project Hub to create a workspace."
echo "Optional dependencies (Flask, requests, …) live in Tools →"
echo "Manage Packages — nothing installs until you ask. Enjoy!"
echo ""
