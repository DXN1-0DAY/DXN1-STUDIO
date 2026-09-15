#!/bin/bash
# UI test environment: Xvfb + openbox WM + the given command.
# A window manager makes focus/key-event tests deterministic.
# Usage: bash scripts/ui_env.sh <command...>
export LD_LIBRARY_PATH=/tmp/openbox_x/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export XDG_DATA_DIRS=/tmp/openbox_x/usr/share

pkill -f "Xvfb :99" 2>/dev/null; pkill -f "openbox" 2>/dev/null
sleep 1
Xvfb :99 -screen 0 1600x1000x24 -nolisten tcp > /tmp/xvfb.log 2>&1 &
XVFB_PID=$!
sleep 2
DISPLAY=:99 /tmp/openbox_x/usr/bin/openbox > /tmp/openbox.log 2>&1 &
OB_PID=$!
sleep 2

export DISPLAY=:99
"$@"
RC=$?

kill $OB_PID 2>/dev/null
kill $XVFB_PID 2>/dev/null
exit $RC
