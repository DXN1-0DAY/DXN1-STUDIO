#!/bin/bash
# DXN1 STUDIO Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/main/install.sh | bash

set -e

INSTALL_DIR="$HOME/.local/share/dxn1-studio"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/DXN1-STUDIO"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   DXN1 STUDIO Installer v1.0.0"
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

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

echo "✓ Created installation directories"

# Download files from GitHub
echo "↓ Downloading DXN1 STUDIO..."

REPO="https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/main"

curl -fsSL "$REPO/dxn1-studio" -o "$INSTALL_DIR/dxn1-studio"
curl -fsSL "$REPO/README.md" -o "$INSTALL_DIR/README.md"

chmod +x "$INSTALL_DIR/dxn1-studio"

echo "✓ Downloaded application files"

# Create launcher script
cat > "$LAUNCHER" << 'LAUNCHEREOF'
#!/bin/bash
# DXN1 STUDIO Launcher

INSTALL_DIR="$HOME/.local/share/dxn1-studio"

if [ ! -f "$INSTALL_DIR/dxn1-studio" ]; then
    echo "ERROR: DXN1 STUDIO is not installed."
    echo "Run: curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/main/install.sh | bash"
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
