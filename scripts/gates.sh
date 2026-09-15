#!/usr/bin/env bash
# DXN1 STUDIO 3 — quality gates. Everything must stay green, always.
# Fully native: the only requirements are a C++23 compiler, git and coreutils.
set -u
cd "$(dirname "$0")/.."
FAIL=0

echo "── gate 1: native build (g++ -std=c++23, zero-warning policy)"
if make -s -C native >/tmp/dxn3_native_build.log 2>&1 \
   && [ -x native/build/dxn3-native ] && [ -x native/build/dxn3-selftest ]; then
  echo "   ok  build"
else
  echo "   FAIL native — build log:"
  tail -15 /tmp/dxn3_native_build.log 2>/dev/null
  FAIL=1
fi

echo "── gate 2: engine selftest"
if native/build/dxn3-selftest >/tmp/dxn3_native_selftest.log 2>&1; then
  echo "   ok  $(tail -1 /tmp/dxn3_native_selftest.log)"
else
  echo "   FAIL selftest — log:"
  tail -8 /tmp/dxn3_native_selftest.log 2>/dev/null
  FAIL=1
fi

echo "── gate 3: every scene renders one real headless frame"
for s in scenes/*.dxn1.json; do
  if OUT=$(native/build/dxn3-native --scene "$s" </dev/null 2>&1) \
     && printf '%s' "$OUT" | grep -q "frame rendered"; then
    echo "   ok  $s  ($(printf '%s' "$OUT" | grep -o 'entities=[0-9]*' | head -1))"
  else
    echo "   FAIL $s"
    printf '%s\n' "$OUT" | tail -3
    FAIL=1
  fi
done

echo "── gate 3b: the campaign chain resolves (every next is a real scene)"
for s in scenes/*.dxn1.json; do
  NXT=$(grep -o '"next": "[^"]*"' "$s" | head -1 | cut -d'"' -f4)
  if [ -z "$NXT" ]; then
    echo "   ok  $s  (no next — standalone)"
  elif [ -f "$NXT" ]; then
    echo "   ok  $s  → $NXT"
  else
    echo "   FAIL $s chains a ghost: $NXT (file does not exist)"
    FAIL=1
  fi
done

echo "── gate 4: the Electron farewell is complete (zero remnants)"
LE=$(git ls-files | grep -icE 'electron|renderer/|webserve|server\.py|selftest\.js|package\.json' || true)
if [ "$LE" -eq 0 ]; then
  echo "   ok  no electron-era files tracked"
else
  echo "   FAIL $LE electron-era file(s) still tracked:"
  git ls-files | grep -iE 'electron|renderer/|webserve|server\.py|selftest\.js|package\.json' | head -5
  FAIL=1
fi

echo "── gate 5: VERSION ↔ CHANGELOG consistency"
V=$(cat VERSION)
if head -4 CHANGELOG.md | grep -q "$V"; then
  echo "   ok  VERSION=$V is the top CHANGELOG entry"
else
  echo "   FAIL VERSION=$V not found at the top of CHANGELOG.md"
  FAIL=1
fi

echo
if [ $FAIL -eq 0 ]; then echo "ALL GATES GREEN"; else echo "GATES RED"; exit 1; fi
