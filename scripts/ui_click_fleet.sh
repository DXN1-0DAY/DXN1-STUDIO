#!/bin/bash
# DS2 hour-3 audit: click-sweep the whole palette fleet in batches.
# Usage: ui_click_fleet.sh <start> <end> <outfile>
cd /home/z/dxn1-studio-original || exit 1
START=${1:-0}
END=${2:-120}
OUT=${3:-/tmp/click_fleet.log}
: > "$OUT"
for i in $(seq "$START" "$END"); do
  DISPLAY=:99 timeout 25 /home/z/.venv/bin/python3 scripts/ui_click_sweep.py "$i" >> "$OUT" 2>> /tmp/click_err.log
done
echo "=== SUMMARY ==="
echo "raised: $(grep -c 'RAISED' "$OUT")"
echo "dead>0: $(grep -c 'dead=[1-9]' "$OUT")"
echo "scanned: $(grep -c '|' "$OUT")"
grep 'RAISED' "$OUT" | head -40
grep 'dead=[1-9]' "$OUT" | head -40
