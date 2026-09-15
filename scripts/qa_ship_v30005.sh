#!/usr/bin/env bash
# ============================================================
# DS3 v3.0.05 ship QA — headless chromium battery.
# Verifies the hour-5 drop live: welcome cards, coin magnetism,
# camera shake (direct + hazard), word autocomplete, breadcrumbs,
# grouped search, terminal status/log verbs, zero page errors.
# Usage: bash scripts/qa_ship_v30005.sh
# ============================================================
set -u
PORT=8035
BASE="http://127.0.0.1:$PORT"
PASS=0; FAIL=0
chk() { # chk <name> <haystack> <needle>
  if printf '%s' "$2" | grep -qF -- "$3"; then
    PASS=$((PASS+1)); echo "   ok  $1"
  else
    FAIL=$((FAIL+1)); echo "   FAIL $1"; echo "        wanted: $3"; echo "        got:    ${2:0:220}"
  fi
}

node scripts/webserve.js $PORT > /tmp/qa_ws_$$.log 2>&1 &
WS=$!
trap 'kill $WS 2>/dev/null; agent-browser close 2>/dev/null' EXIT
sleep 1.2

agent-browser set viewport 1440 900 > /dev/null
agent-browser open $BASE/ > /dev/null
agent-browser wait --load networkidle > /dev/null

# 1. welcome cards present
chk "hero play card"      "$(agent-browser eval "document.getElementById('hero-play') ? 'yes' : 'no'")"  yes
chk "hero level-2 card"   "$(agent-browser eval "document.getElementById('hero-play2') ? 'yes' : 'no'")" yes

# 2. hero-play2 opens level-2 and plays
agent-browser eval "document.getElementById('hero-play2').click()" > /dev/null; sleep 1.1
chk "level-2 opens from welcome" "$(agent-browser eval "document.getElementById('scene-name').textContent")" level-2
chk "crumbs show scene path"     "$(agent-browser eval "document.getElementById('crumbs').textContent")"    "scenes"
chk "game running"               "$(agent-browser eval "GAME.running")"                                     true
chk "level-2 magnetized"         "$(agent-browser eval "String(GAME.scene.magnet)")"                        140

# 3. magnetism end-to-end, deterministic: freeze gravity (no fall, no
#    respawn race), boost the magnet, park the coin 60px from the player.
#    Eval returns stay quote-free — agent-browser JSON-quotes strings and
#    quoted needles never match (see worklog QA lessons).
agent-browser eval "(function(){var p=GAME.scene.entities.find(function(e){return e.tag==='player';});var c=GAME.scene.entities.find(function(e){return e.tag==='coin';});GAME.scene.gravity=0;GAME.scene.magnet=2000;p.x=200;p.y=400;p.vx=0;p.vy=0;c.x=260;c.y=410;c.alive=true;return 1;})()" > /dev/null
sleep 0.8
MAG=$(agent-browser eval "GAME.score + '|' + GAME.scene.entities.find(function(e){return e.tag==='coin';}).alive")
chk "magnet pulls coin (score+10)" "$MAG" "10|"
chk "magnet collects coin"         "$MAG" "|false"
agent-browser eval "GAME.scene.magnet=140;GAME.scene.gravity=1500;1" > /dev/null

# 4. shake: direct call sets timer, decays to zero
S1=$(agent-browser eval "GAME.shake(12,0.4); String(+GAME._shakeT.toFixed(2))")
chk "shake arms timer" "$S1" 0.4
sleep 0.7
chk "shake decays"     "$(agent-browser eval "String(GAME._shakeT)")" 0

# 5. hazard hit fires shake + respawn
agent-browser eval "(function(){var p=GAME.scene.entities.find(function(e){return e.tag==='player';});var s=GAME.scene.entities.find(function(e){return e.tag==='hazard';});p.x=s.x+2;p.y=s.y-40;p.vy=0;return 'ok';})()" > /dev/null
chk "hazard fires shake" "$(agent-browser eval "String(GAME._shakeT > 0)")" true

# 6. autocomplete: open -> accept -> escape
agent-browser eval "openPath('README.md')" > /dev/null; sleep 0.6
AC=$(agent-browser eval "(function(){var ta=document.getElementById('editor');ta.focus();ta.value='alpha beta gamma\\nalp';ta.setSelectionRange(ta.value.length,ta.value.length);ta.dispatchEvent(new KeyboardEvent('keydown',{key:' ',code:'Space',ctrlKey:true,bubbles:true}));return String(AC.open)+'|'+AC.items.join(',');})()")
chk "ctrl+space opens popup" "$AC" "true|alpha"
chk "word candidates"        "$AC" "|alpha"
AC2=$(agent-browser eval "(function(){var ta=document.getElementById('editor');ta.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return ta.value.replace('\\n','|')+'|'+String(document.getElementById('ac-pop').classList.contains('hidden'));})()")
chk "enter accepts word"     "$AC2" "alpha beta gamma|alpha|true"
AC3=$(agent-browser eval "(function(){var ta=document.getElementById('editor');var i=ta.value.indexOf('alp');ta.setSelectionRange(i+3,i+3);ta.dispatchEvent(new KeyboardEvent('keydown',{key:' ',code:'Space',ctrlKey:true,bubbles:true}));var o=String(AC.open);ta.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));return 'reopened='+o+' escClosed='+String(!AC.open);})()")
chk "escape closes popup"    "$AC3" "escClosed=true"

# 7. terminal status + log verbs
agent-browser eval "(function(){document.getElementById('term-in').value='status';document.getElementById('term-in').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 1;})()" > /dev/null
sleep 0.5
chk "terminal status verb" "$(agent-browser eval "document.getElementById('term-out').textContent.slice(-120)")" "working tree clean"
agent-browser eval "(function(){document.getElementById('term-in').value='log';document.getElementById('term-in').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 1;})()" > /dev/null
sleep 0.5
chk "terminal log verb"    "$(agent-browser eval "document.getElementById('term-out').textContent.slice(-160)")" "import playground"

# 8. grouped search
agent-browser eval "switchPanel('search');document.getElementById('search-input').value='spark';document.getElementById('search-input').dispatchEvent(new Event('input',{bubbles:true}));1" > /dev/null
sleep 1.2
chk "search groups by file" "$(agent-browser eval "document.querySelectorAll('.sr-file').length + '|' + document.querySelectorAll('.sr-count').length")" "1|1"

# 9. crumbs click echoes path
chk "crumb click echoes path" "$(agent-browser eval "(function(){document.querySelector('.crumb').click();return document.getElementById('st-msg').textContent;})()")" "README.md"

# 10. no page errors (empty output must still yield one grep-able line)
ERRS=$(agent-browser errors 2>&1 || true)
chk "zero page errors" "${ERRS:-CLEAN-NO-ERRORS}" "CLEAN-NO-ERRORS"

# 11. native C++23 core — builds clean and stays green
chk "native selftest green" "$(make -s -C native >/dev/null 2>&1 && ./native/build/dxn3-selftest 2>&1 | tail -1)" "all green (29 assertion groups)"
chk "native binary present" "$([ -x native/build/dxn3-native ] && echo yes)" "yes"
chk "native smoke frame" "$(timeout 5 ./native/build/dxn3-native scenes/playground.dxn1.json </dev/null 2>/dev/null | tail -1)" "frame rendered: score=0 time=0 entities=16"

echo
echo "QA: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
