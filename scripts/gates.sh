#!/bin/bash
# DS2 gate sequence — run ALL gates; any failure aborts with nonzero.
# Usage: bash scripts/gates.sh
set -o pipefail
cd "$(dirname "$0")/.." || exit 1
PY=/home/z/.venv/bin/python3
FAIL=0

echo "== compileall =="
python3 -m compileall -q dxn1_studio || FAIL=1

echo "== pytest =="
DISPLAY=:99 $PY -m pytest tests/ -q 2>&1 | tail -1 || FAIL=1

echo "== boot_qa =="
DISPLAY=:99 timeout 120 $PY scripts/boot_qa.py 2>&1 | tail -1 || FAIL=1

echo "== bash -n install.sh =="
bash -n install.sh || FAIL=1

if [ "$FAIL" -ne 0 ]; then
  echo "GATES: FAIL"
  exit 1
fi
echo "GATES: PASS"
