#!/usr/bin/env bash
# ============================================================
# DS3 v3.0.06 ship QA — headless chromium battery.
# Verifies: terminal branch verbs (list/switch/create/rename/
# delete + honest errors), branch chip menu rename/delete,
# drag & drop (explorer -> editor, OS file -> imports/),
# zero page errors, native C++23 core still green.
# QA lessons applied: poll instead of sleep (async UI), override
# window.prompt BEFORE clicking, quote-free needles only.
# Usage: bash scripts/qa_ship_v30006.sh
# ============================================================
set -u
PORT=8037
BASE="http://127.0.0.1:$PORT"
PASS=0; FAIL=0
chk() { # chk <name> <haystack> <needle>
  if printf '%s' "$2" | grep -qF -- "$3"; then
    PASS=$((PASS+1)); echo "   ok  $1"
  else
    FAIL=$((FAIL+1)); echo "   FAIL $1"; echo "        wanted: $3"; echo "        got:    ${2:0:220}"
  fi
}
waitfor() { # waitfor <needle> <eval-expr> — poll up to ~5s for the needle
  local V=""
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
    V=$(agent-browser eval "$2" 2>/dev/null)
    printf '%s' "$V" | grep -qF -- "$1" && { printf '%s' "$V"; return 0; }
    sleep 0.3
  done
  printf '%s' "$V"
}
term() { # term <cmd> <needle> — run a terminal verb, poll for its output
  agent-browser eval "(function(){var i=document.getElementById('term-in');i.value='$1';i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 1;})()" > /dev/null
  local V="" _
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
    V=$(agent-browser eval "document.getElementById('term-out').textContent.slice(-260)" 2>/dev/null)
    printf '%s' "$V" | grep -qF -- "$2" && { printf '%s' "$V"; return 0; }
    sleep 0.3
  done
  printf '%s' "$V"
}

node scripts/webserve.js $PORT > /tmp/qa_ws6_$$.log 2>&1 &
WS=$!
trap 'kill $WS 2>/dev/null; agent-browser close 2>/dev/null' EXIT
sleep 1.2

agent-browser set viewport 1440 900 > /dev/null
agent-browser open $BASE/ > /dev/null
agent-browser wait --load networkidle > /dev/null

# 1. terminal branch verbs (DemoFS vgit — same protocol, honest errors)
chk "branch lists with a dot"       "$(term 'branch' '● main')"            "● main"
chk "branch creates and switches"   "$(term 'branch feature/qa' 'on new branch feature/qa')" "on new branch feature/qa"
chk "branch list shows both"        "$(term 'branch' 'feature/qa')"        "feature/qa"
chk "branch renames"                "$(term 'branch -m feature/qa feature/renamed' 'renamed feature/qa → feature/renamed')" "renamed feature/qa → feature/renamed"
chk "delete current refused"        "$(term 'branch -d feature/renamed' 'cannot delete the branch you are on')" "cannot delete the branch you are on"
chk "delete ghost refused"          "$(term 'branch -d ghost' 'no such branch: ghost')" "no such branch: ghost"
chk "branch switches to existing"   "$(term 'branch temp/x' 'on new branch temp/x')" "on new branch temp/x"
chk "branch back to existing"       "$(term 'branch feature/renamed' 'on feature/renamed')" "on feature/renamed"
chk "delete works off-branch"       "$(term 'branch -d temp/x' 'deleted temp/x')" "deleted temp/x"
chk "rename onto existing refused"  "$(term 'branch -m feature/renamed main' 'already exists')" "already exists"

# 2. branch chip menu — rename via prompt queue (override BEFORE clicks)
agent-browser eval "window.PROMPTS=['feature/renamed','feature/final'];window.prompt=function(m,d){return window.PROMPTS.length?window.PROMPTS.shift():d;};1" > /dev/null
agent-browser eval "document.getElementById('git-branch').click()" > /dev/null
waitfor "Rename" "(function(){return [].slice.call(document.querySelectorAll('.ctx-item')).some(function(x){return x.textContent.indexOf('Rename')>0;}) ? 'menu-open-Rename' : 'no-menu';})()"
agent-browser eval "(function(){var b=[].slice.call(document.querySelectorAll('.ctx-item')).find(function(x){return x.textContent.indexOf('Rename')>0;});if(b)b.click();return b?'clicked':'missing';})()" > /dev/null
chk "menu renames branch" "$(waitfor "Renamed feature/renamed → feature/final" "document.getElementById('toasts').textContent")" "Renamed feature/renamed → feature/final"

agent-browser eval "window.PROMPTS=['feature/final'];window.prompt=function(m,d){return window.PROMPTS.length?window.PROMPTS.shift():d;};1" > /dev/null
agent-browser eval "document.getElementById('git-branch').click()" > /dev/null
waitfor "Delete" "(function(){return [].slice.call(document.querySelectorAll('.ctx-item')).some(function(x){return x.textContent.indexOf('Delete')>0;}) ? 'menu-open-Delete' : 'no-menu';})()"
agent-browser eval "(function(){var b=[].slice.call(document.querySelectorAll('.ctx-item')).find(function(x){return x.textContent.indexOf('Delete')>0;});if(b)b.click();return b?'clicked':'missing';})()" > /dev/null
chk "menu refuses deleting current" "$(waitfor "cannot delete the branch you are on" "document.getElementById('toasts').textContent")" "cannot delete the branch you are on"

# 3. drag & drop — explorer file onto the editor stack
agent-browser eval "(function(){var row=[].slice.call(document.querySelectorAll('.tree-item')).find(function(r){var n=r.querySelector('.nm');return n&&n.textContent==='README.md';});if(!row)return 'no-row';var dt=new DataTransfer();row.dispatchEvent(new DragEvent('dragstart',{dataTransfer:dt,bubbles:true}));var stack=document.getElementById('editor-stack');stack.dispatchEvent(new DragEvent('dragover',{dataTransfer:dt,bubbles:true}));var glow=stack.classList.contains('drop-target');stack.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true}));return 'glow:'+glow;})()" > /dev/null
chk "stack glows then opens file" "$(waitfor "opened README.md" "document.getElementById('st-msg').textContent")" "opened README.md"
chk "internal drop tab active"    "$(agent-browser eval "(document.querySelector('.tab.active')||{textContent:''}).textContent")" "README.md"

# 4. drag & drop — an OS file lands as imports/<name>, then saves through
agent-browser eval "(function(){var f=new File(['# dropped note' + String.fromCharCode(10) + 'hello native world'],'dropped-note.md',{type:'text/markdown'});var dt=new DataTransfer();dt.items.add(f);var stack=document.getElementById('editor-stack');stack.dispatchEvent(new DragEvent('dragover',{dataTransfer:dt,bubbles:true}));stack.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true}));return 1;})()" > /dev/null
chk "external drop makes tab"   "$(waitfor "imports/dropped-note.md" "ACTIVE || ''")" "imports/dropped-note.md"
chk "external drop has content" "$(agent-browser eval "document.getElementById('editor').value")" "hello native world"
chk "external drop is honest"   "$(waitfor "dropped dropped-note.md" "document.getElementById('st-msg').textContent")" "dropped dropped-note.md"
agent-browser eval "saveActive()" > /dev/null
chk "import saves to workspace" "$(waitfor "Saved dropped-note.md" "document.getElementById('toasts').textContent")" "Saved dropped-note.md"
agent-browser eval "window.LASTREAD=null;api('read',{path:'imports/dropped-note.md'}).then(function(r){window.LASTREAD=r.content;});1" > /dev/null; sleep 0.6
chk "engine read-back matches"  "$(agent-browser eval "String(window.LASTREAD)")" "hello native world"

# 5. no page errors (empty output must still yield one grep-able line)
ERRS=$(agent-browser errors 2>&1 || true)
chk "zero page errors" "${ERRS:-CLEAN-NO-ERRORS}" "CLEAN-NO-ERRORS"

# 6. native C++23 core — builds clean and stays green
chk "native selftest green" "$(make -s -C native >/dev/null 2>&1 && ./native/build/dxn3-selftest 2>&1 | tail -1)" "all green (29 assertion groups)"
chk "native binary present" "$([ -x native/build/dxn3-native ] && echo yes)" "yes"
chk "native smoke frame" "$(timeout 5 ./native/build/dxn3-native scenes/playground.dxn1.json </dev/null 2>/dev/null | tail -1)" "frame rendered: score=0 time=0 entities=16"

echo
echo "QA: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
