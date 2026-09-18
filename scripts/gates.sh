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

echo "── gate 3c: every scene speaks the list dialect (the frozen-ferries law)"
if command -v python3 >/dev/null 2>&1; then
  if python3 - <<'PYEOF'
import json, glob, sys
bad = []
for p in sorted(glob.glob("scenes/*.dxn1.json")):
    d = json.load(open(p))
    for e in d.get("entities", []):
        if not isinstance(e, dict) or "path" not in e:
            continue
        path = e["path"]
        if not isinstance(path, list) or not path or \
           not all(isinstance(w, dict) and "x" in w and "y" in w for w in path):
            bad.append(f"{p}: {e.get('name','?')} path is not a list of waypoints "
                       f"(the loader hears lists only — a dict path is a frozen ferry)")
            continue
        if e.get("pspeed", 0) <= 0:
            bad.append(f"{p}: {e.get('name','?')} has a path but no pspeed")
for b in bad:
    print("   " + b)
sys.exit(1 if bad else 0)
PYEOF
  then
    echo "   ok  every path is a real waypoint list with a pspeed"
  else
    echo "   FAIL scene dialect violation(s) above — a silent path is a frozen ferry"
    FAIL=1
  fi
else
  echo "   (skip) python3 not on this machine — the dialect gate runs in CI"
fi

echo "── gate 3d: every scene is walkable on paper (one spawn, a door ahead)"
if command -v python3 >/dev/null 2>&1; then
  if python3 - <<'PYEOF'
import json, glob, sys
bad = []
for p in sorted(glob.glob("scenes/*.dxn1.json")):
    d = json.load(open(p))
    ents = [e for e in d.get("entities", []) if isinstance(e, dict)]
    players = [e for e in ents if e.get("tag") == "player"]
    goals = [e for e in ents if e.get("tag") == "goal"]
    if len(players) != 1:
        bad.append(f"{p}: {len(players)} player spawns (exactly one is the law)")
    elif players[0].get("x") is None or players[0].get("y") is None:
        bad.append(f"{p}: the player spawn has no coordinates")
    if d.get("next") and not goals:
        bad.append(f"{p}: chains to {d['next']} but has no goal door")
for b in bad:
    print("   " + b)
sys.exit(1 if bad else 0)
PYEOF
  then
    echo "   ok  every scene has one spawn and a door where it promised"
  else
    echo "   FAIL scene structure violation(s) above — a scene without a spawn is a rumor"
    FAIL=1
  fi
else
  echo "   (skip) python3 not on this machine — the structure gate runs in CI"
fi

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

echo "── gate 6: every shipped example speaks the protocol"
if command -v python3 >/dev/null 2>&1; then
  if python3 scripts/sdk_conformance.py; then
    :
  else
    echo "   FAIL an example failed the wire contract"
    FAIL=1
  fi
else
  echo "   (skip) python3 not on this machine — the wire contract runs in CI"
fi

echo "── gate 7: the README never promises a ghost"
if command -v python3 >/dev/null 2>&1; then
  if python3 - << 'PY7'
import re, pathlib

readme = pathlib.Path("README.md").read_text()
ghosts = []
for m in sorted(set(re.findall(r"docs/img/[A-Za-z0-9_\-\.]+\.png", readme))):
    if not pathlib.Path(m).exists():
        ghosts.append(m)
for m in sorted(set(re.findall(r"sdk/examples/[A-Za-z0-9_\-\.]+", readme))):
    if not pathlib.Path(m).exists():
        ghosts.append(m)
badge = re.search(r"version-([\d\.]+)-", readme)
ver = pathlib.Path("VERSION").read_text().strip()
if not badge or badge.group(1) != ver:
    ghosts.append(f"README version badge {badge.group(1) if badge else '?'} != VERSION {ver}")
if ghosts:
    for g in ghosts:
        print(f"   FAIL ghost: {g}")
    raise SystemExit(1)
print(f"   ok  every image, example and the badge ({ver}) are real")
PY7
  then
    :
  else
    echo "   FAIL the README promised something that is not there"
    FAIL=1
  fi
else
  echo "   (skip) python3 not on this machine — the README gate runs in CI"
fi

echo "── gate 8: the probes walk (the law pins live in the repo now)"
if command -v python3 >/dev/null 2>&1; then
  probe_fail=0
  probe_n=0
  for f in probes/*_probe.py; do
    [ -e "$f" ] || continue
    probe_n=$((probe_n + 1))
    if timeout 180 python3 "$f" > /tmp/dxn1_probe_$$.log 2>&1; then
      echo "   ok   $f"
    else
      echo "   FAIL $f"
      tail -6 /tmp/dxn1_probe_$$.log
      probe_fail=1
    fi
  done
  rm -f /tmp/dxn1_probe_$$.log
  if [ $probe_n -eq 0 ]; then
    echo "   FAIL no probes found in probes/ — a law without its pin is a rumor"
    FAIL=1
  elif [ $probe_fail -eq 1 ]; then
    FAIL=1
  else
    echo "   ok   $probe_n probe(s) walked, every pin green"
  fi
else
  echo "   (skip) python3 not on this machine — the probes run in CI"
fi

echo
if [ $FAIL -eq 0 ]; then echo "ALL GATES GREEN"; else echo "GATES RED"; exit 1; fi
