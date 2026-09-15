#!/usr/bin/env bash
# DXN1 STUDIO 3 — quality gates. Everything must stay green, always.
set -u
cd "$(dirname "$0")/.."
FAIL=0

echo "── gate 1: node --check (every JS file)"
for f in electron/*.js renderer/*.js; do
  if node --check "$f" 2>&1; then echo "   ok  $f"; else echo "   FAIL $f"; FAIL=1; fi
done

echo "── gate 2: python compileall (the brain)"
if python3 -m compileall -q engine; then echo "   ok  engine"; else echo "   FAIL engine"; FAIL=1; fi

echo "── gate 3: engine unit tests"
if /home/z/.venv/bin/python3 -m pytest tests/ -q 2>/dev/null || python3 -m pytest tests/ -q; then
  echo "   ok  pytest"; else echo "   FAIL pytest"; FAIL=1; fi

echo "── gate 4: version trio"
V=$(cat VERSION)
PKG=$(python3 -c "import json;print(json.load(open('package.json'))['version'])")
APP=$(grep -o 'const VERSION = "[^"]*"' renderer/app.js | cut -d'"' -f2)
HTML=$(grep -o 'id="st-version" class="chip">v[^<]*' renderer/index.html | sed 's/.*>v//')
# package.json carries the semver-nearest form (3.0.02 -> 3.0.2: semver
# cannot express leading zeros); everything else is canonical.
PKGN=$(python3 -c "print('.'.join(str(int(p)) for p in '$PKG'.split('.')))")
VN=$(python3 -c "print('.'.join(str(int(p)) for p in '$V'.split('.')))")
echo "   VERSION=$V package.json=$PKG app.js=$APP index.html=$HTML"
if [ "$V" = "$APP" ] && [ "$APP" = "$HTML" ] && [ "$PKGN" = "$VN" ]; then
  echo "   ok  trio consistent"
else echo "   FAIL trio mismatch"; FAIL=1; fi

echo "── gate 5: scene JSON validity"
python3 - <<'EOF'
import json, glob, sys
bad = 0
for p in glob.glob("scenes/*.json"):
    try:
        s = json.load(open(p))
        assert isinstance(s.get("entities"), list)
    except Exception as e:
        print(f"   FAIL {p}: {e}"); bad = 1
    else:
        print(f"   ok  {p} ({len(s['entities'])} entities)")
sys.exit(bad)
EOF
[ $? -ne 0 ] && FAIL=1

echo "── gate 6: renderer selftest (highlighter + Spark schema)"
if node scripts/selftest.js; then echo "   ok  selftest"; else echo "   FAIL selftest"; FAIL=1; fi

echo
if [ $FAIL -eq 0 ]; then echo "ALL GATES GREEN"; else echo "GATES RED"; exit 1; fi
