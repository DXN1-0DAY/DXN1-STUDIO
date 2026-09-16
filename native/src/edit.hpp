// edit.hpp — the IDE's editor heart: the document, the cursor, and the
// second chance (undo/redo). Header-only so main.cpp and the selftest
// share one truth about what a keystroke means.
//
// Undo groups like real editors: a burst of typing or backspacing
// coalesces while the hand is quick (idle < 0.8s — the same timer that
// drives the live auto-run), while enter, forward-delete and template
// loads are always their own restore point. undo/redo restore the whole
// document AND the cursor, so the second chance lands you exactly where
// you were standing.
#pragma once
#include <algorithm>
#include <cctype>
#include <string>
#include <vector>

#include "tui.hpp"

namespace dxn3 {

// one frame of parsed keys — pollKeys() fills it, ideKey() consumes it
struct Keys {
  bool left = false, right = false, jump = false;
  bool reset = false, fit = false, zoomIn = false, zoomOut = false;
  bool inspect = false, quit = false;
  bool esc = false;                            // bare ESC (mode-dependent)
  bool viewFile = false;                       // e — open the scene source
  bool cmd = false;                            // : — open the command bar
  bool shot = false;                           // p — screenshot to exports/
  int scroll = 0;                              // file view: ±1 lines (arrows ±10)
  bool slash = false;                          // / — start a search
  bool enter = false, back = false;
  bool ctrlS = false, ctrlR = false;           // IDE: save / run
  bool up = false, down = false;               // IDE: cursor rows
  bool aLeft = false, aRight = false;          // IDE: cursor cols
  bool toPlay = false;                         // IDE: tab — play your game
  bool braille = false;                        // b — toggle the dot renderer
  bool ctrlN = false;                          // IDE: next template
  bool pageUp = false, pageDn = false;         // IDE: page through the file
  bool del = false;                            // IDE: forward delete
  bool home = false, end = false;              // IDE: line ends
  bool ctrlG = false;                          // IDE: jump to the error line
  bool ctrlZ = false, ctrlY = false;           // IDE: undo / redo
  std::string typed;                           // printable chars this frame
};

// a restore point: the whole document plus where you were standing
struct IdeSnap {
  std::vector<std::string> lines;
  int curR = 0, curC = 0;
  bool operator==(const IdeSnap& o) const = default;
};

struct IdeState {
  bool open = false;
  std::vector<std::string> lines{""};       // a new file starts truly empty
  int curR = 0, curC = 0, top = 0;
  int page = 14;                             // visible rows (drawIDE refreshes)
  std::string path;                          // the script file
  bool dirty = true;                         // needs a (re)run
  double idle = 0;                           // typing pause → auto-run + undo groups
  std::vector<std::string> console;          // engine notes + game prints
  std::string state = "new file — write code, Ctrl+R runs it";
  bool hostUp = false;
  int tpl = -1;                                // Ctrl+N gallery index
  // the second chance
  std::vector<IdeSnap> undo, redo;
  bool lastTyping = false, lastBack = false;   // group coalescing state
  static constexpr size_t kUndoMax = 200;      // deep enough to trust
};

// the cursor clamps to whatever document it lands on
inline void ideClamp(IdeState& s) {
  s.curR = std::clamp(s.curR, 0, static_cast<int>(s.lines.size()) - 1);
  s.curC = std::clamp(s.curC, 0,
                      static_cast<int>(s.lines[static_cast<size_t>(s.curR)].size()));
}

inline void idePushUndo(IdeState& s) {
  s.undo.push_back({s.lines, s.curR, s.curC});
  if (s.undo.size() > IdeState::kUndoMax)
    s.undo.erase(s.undo.begin(),
                 s.undo.begin() + static_cast<long>(s.undo.size() - IdeState::kUndoMax));
  s.redo.clear();                    // a fresh edit cuts the redo branch
  s.lastTyping = s.lastBack = false;
}

// step back through time; false when there is nothing to undo
inline bool ideUndo(IdeState& s) {
  if (s.undo.empty()) return false;
  s.redo.push_back({s.lines, s.curR, s.curC});
  s.lines = std::move(s.undo.back().lines);
  s.curR = s.undo.back().curR;
  s.curC = s.undo.back().curC;
  s.undo.pop_back();
  s.lastTyping = s.lastBack = false;
  ideClamp(s);
  return true;
}

// step forward again; false when there is nothing to redo
inline bool ideRedo(IdeState& s) {
  if (s.redo.empty()) return false;
  s.undo.push_back({s.lines, s.curR, s.curC});
  s.lines = std::move(s.redo.back().lines);
  s.curR = s.redo.back().curR;
  s.curC = s.redo.back().curC;
  s.redo.pop_back();
  s.lastTyping = s.lastBack = false;
  ideClamp(s);
  return true;
}

// does this line OPEN a block (python ':', C-family '{')?
inline bool ideOpensBlock(const std::string& s) {
  const size_t a = s.find_first_not_of(" \t");
  if (a == std::string::npos) return false;
  const size_t b = s.find_last_not_of(" \t");
  const std::string t = s.substr(a, b - a + 1);   // trailing ws tolerated
  return t.back() == ':' || t.back() == '{';
}

// does this line CLOSE one (else / elif / except / finally / case /
// default / end…)? Whole-word check, so "endless" never matches — and
// the end family is spelled out so endif/endwhile/endfor ride along.
inline bool ideClosesBlock(const std::string& s) {
  static const char* kw[] = {"else", "elif", "except", "finally", "case",
                             "default", "end", "endif", "endwhile", "endfor"};
  size_t a = s.find_first_not_of(" \t");
  if (a == std::string::npos) return false;
  const std::string t = s.substr(a);
  for (const char* k : kw) {
    const size_t n = std::char_traits<char>::length(k);
    if (t.rfind(k, 0) == 0 &&
        (t.size() == n || !std::isalnum(static_cast<unsigned char>(t[n]))))
      return true;
  }
  return false;
}

// the editor owns typing: chars land at the cursor, backspace joins
// lines, enter splits them (and carries the indent down), every edit is
// undoable
inline void ideKey(IdeState& ide, const Keys& k) {
  auto& L = ide.lines;
  if (ide.curR >= static_cast<int>(L.size()))
    ide.curR = static_cast<int>(L.size()) - 1;
  std::string& line = L[static_cast<size_t>(ide.curR)];

  // ── the second chance: decide whether this frame's edits continue the
  // previous group (quick hands coalesce) or open a new restore point
  const bool quick = ide.idle < 0.8;
  if (!k.typed.empty()) {
    if (!(ide.lastTyping && quick)) idePushUndo(ide);
    else ide.redo.clear();
    ide.lastTyping = true;
    ide.lastBack = false;
  }
  if (k.back) {
    if (!((ide.lastTyping || ide.lastBack) && quick)) idePushUndo(ide);
    else ide.redo.clear();
    ide.lastBack = true;
    ide.lastTyping = false;
  }
  if (k.enter || k.del) idePushUndo(ide);      // structure changes stand alone

  for (const char ch : k.typed) {
    line.insert(line.begin() + std::min(ide.curC, static_cast<int>(line.size())), ch);
    ++ide.curC;
  }
  if (k.back) {
    if (ide.curC > 0) { line.erase(line.begin() + ide.curC - 1); --ide.curC; }
    else if (ide.curR > 0) {                       // join with previous line
      ide.curC = static_cast<int>(L[static_cast<size_t>(ide.curR - 1)].size());
      L[static_cast<size_t>(ide.curR - 1)] += line;
      L.erase(L.begin() + ide.curR);
      --ide.curR;
    }
  }
  if (k.enter) {
    // re-fetch: back may have joined lines and grown/shrunk L above
    std::string& cur = L[static_cast<size_t>(ide.curR)];
    const int at = std::min(ide.curC, static_cast<int>(cur.size()));
    std::string rest = cur.substr(static_cast<size_t>(at));
    cur.resize(static_cast<size_t>(at));
    // the block rides down: inherit this line's leading whitespace,
    // bump a level after an opener, drop one before a closer
    const size_t ws = cur.find_first_not_of(" \t");
    std::string indent = (ws == std::string::npos) ? cur : cur.substr(0, ws);
    if (ideOpensBlock(cur)) indent += "    ";
    if (ideClosesBlock(rest)) {
      const size_t cut = indent.size() >= 4 ? indent.size() - 4 : 0;
      indent.resize(cut);
    }
    L.insert(L.begin() + ide.curR + 1, indent + rest);
    ++ide.curR;
    ide.curC = static_cast<int>(indent.size());
  }
  if (k.up) --ide.curR;
  if (k.down) ++ide.curR;
  if (k.aLeft) --ide.curC;
  if (k.aRight) ++ide.curC;
  if (k.home) ide.curC = 0;
  if (k.end) ide.curC = static_cast<int>(L[static_cast<size_t>(ide.curR)].size());
  if (k.pageUp) ide.curR -= ide.page;
  if (k.pageDn) ide.curR += ide.page;
  if (k.del) {                               // forward delete
    // re-fetch: enter may have grown L above and reallocated the buffer
    std::string& cur = L[static_cast<size_t>(ide.curR)];
    if (ide.curC < static_cast<int>(cur.size())) {
      cur.erase(cur.begin() + ide.curC);
    } else if (ide.curR + 1 < static_cast<int>(L.size())) {
      cur += L[static_cast<size_t>(ide.curR) + 1];
      L.erase(L.begin() + ide.curR + 1);     // join the next line up
    }
  }

  // ── undo / redo: the second chance, one keystroke away
  if (k.ctrlZ) {
    if (ideUndo(ide)) {
      ide.dirty = true;                      // the game re-runs on the restored code
      ide.idle = 0;
      ide.console.push_back("engine: undo — " +
                            std::to_string(ide.undo.size()) + " step" +
                            (ide.undo.size() == 1 ? "" : "s") + " left");
    } else {
      ide.console.push_back("engine: nothing to undo");
    }
  }
  if (k.ctrlY) {
    if (ideRedo(ide)) {
      ide.dirty = true;
      ide.idle = 0;
      ide.console.push_back("engine: redo");
    } else {
      ide.console.push_back("engine: nothing to redo");
    }
  }

  ideClamp(ide);
}

} // namespace dxn3
