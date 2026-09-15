#!/bin/bash
# DXN1 STUDIO Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master/install.sh | bash
# Re-run any time to update in place.  Uninstall: install.sh --uninstall
# Check the installer version without installing: install.sh --version

set -e

# Bumped with releases; the app's real version always comes from the
# downloaded dxn1_studio/__init__.py (never stamped over it).
INSTALLER_VERSION="2.67.0"

INSTALL_DIR="$HOME/.local/share/dxn1-studio"
BIN_DIR="$HOME/.local/bin"
REPO="https://raw.githubusercontent.com/DXN1-termux/DXN1-STUDIO/master"

# ---- uninstall ------------------------------------------------------------
if [ "$1" = "--uninstall" ] || [ "$1" = "-u" ]; then
    echo "Uninstalling DXN1 STUDIO..."
    rm -rf "$INSTALL_DIR"
    rm -f "$BIN_DIR/dxn1" "$BIN_DIR/DXN1" "$BIN_DIR/dxn1-studio" \
          "$BIN_DIR/DXN1-STUDIO" "$BIN_DIR/DXN1 STUDIO"
    echo "Removed $INSTALL_DIR and the CLI links."
    echo "(Your settings and projects in ~/.dxn1-studio were kept.)"
    exit 0
fi

# ---- version probe ---------------------------------------------------------
if [ "$1" = "--version" ] || [ "$1" = "-V" ]; then
    echo "dxn1-studio installer $INSTALLER_VERSION"
    exit 0
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   DXN1 STUDIO Installer v$INSTALLER_VERSION"
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

# package modules — manifest-driven, so a new module can never be missed
# (MANIFEST.txt is generated from dxn1_studio/*.py and CI-tested to stay
# in sync; without it we fall back to a minimal core set)
MANIFEST="$INSTALL_DIR/MANIFEST.txt"
if curl -fsSL "$REPO/MANIFEST.txt" -o "$MANIFEST"; then
    echo "  ✓ MANIFEST.txt ($(wc -l < "$MANIFEST" | tr -d ' ') modules)"
else
    echo "  ⚠ manifest fetch failed — using built-in core list"
    printf '%s\n' __init__.py app.py config.py theme.py widgets.py \
        onboarding.py tour.py projects.py hub.py splash.py packages.py \
        export.py agent.py sandbox.py llm.py search.py errors.py \
        gitpanel.py updater.py i18n.py > "$MANIFEST"
fi
# DS2 v2.34: sha256 manifest — lets us verify every downloaded module
# landed byte-perfect (and lets the updater stream only deltas)
HASHES="$INSTALL_DIR/HASHES.txt"
if curl -fsSL "$REPO/HASHES.txt" -o "$HASHES"; then
    echo "  ✓ HASHES.txt ($(wc -l < "$HASHES" | tr -d ' ') checksums)"
else
    echo "  ⚠ HASHES.txt unavailable — integrity gate will be skipped"
    rm -f "$HASHES"
fi
while IFS= read -r f; do
    [ -z "$f" ] && continue
    download "$INSTALL_DIR/dxn1_studio/$f" "dxn1_studio/$f" required
done < "$MANIFEST"

# sanity gate: the app cannot boot unless every manifest module landed
# (DS2 v2.34: plus sha256 verification against HASHES.txt when present —
# a corrupted or truncated download fails the install instead of the app)
python3 - "$MANIFEST" "$INSTALL_DIR" "$HASHES" <<'PYEOF'
import hashlib, os, sys
manifest, root, hashes = sys.argv[1], sys.argv[2], sys.argv[3]
names = [f for f in open(manifest, encoding="utf-8").read().split() if f]
missing = [f for f in names
           if not os.path.isfile(os.path.join(root, "dxn1_studio", f))]
if missing:
    sys.exit("ERROR: missing modules after download: " + ", ".join(missing))
print("  ✓ all " + str(len(names)) + " modules present and accounted for")
want = {}
if os.path.isfile(hashes):
    for ln in open(hashes, encoding="utf-8"):
        parts = ln.strip().split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            want[parts[1].strip()] = parts[0].lower()
if want:
    bad = []
    for f in names:
        path = os.path.join(root, "dxn1_studio", f)
        exp = want.get("dxn1_studio/" + f)
        if not exp:
            continue
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 16), b""):
                h.update(chunk)
        if h.hexdigest() != exp:
            bad.append(f)
    if bad:
        sys.exit("ERROR: sha256 mismatch (corrupt download): "
                 + ", ".join(bad) + " — re-run the installer")
    print("  ✓ sha256 verified against HASHES.txt")
else:
    print("  ⚠ integrity check skipped (no HASHES.txt)")
PYEOF

# art assets (optional — the IDE falls back to geometric art without them;
# splash_bg.png is what powers the animated boot card — v1.1.6 hotfix)
for f in logo.png splash_bg.png welcome_hero.png hub_hero.png agents_hero.png update_hero.png; do
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
echo "First launch opens the welcome wizard — pick your theme, editor size,"
echo "first project and DXN1 Agents brain (free cloud needs no account), then"
echo "land in the Project Hub. Optional dependencies (Flask, requests, …) live"
echo "in the Packages view — nothing installs until you ask. Enjoy!"
echo ""
