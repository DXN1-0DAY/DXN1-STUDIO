// edit.hpp — the IDE's editor heart: the document, the cursor, the
// second chance (undo/redo), the searchlight (find) and pairs that
// carry their own closers. Header-only so main.cpp and the selftest
// share one truth about what a keystroke means.
//
// Undo groups like real editors: a burst of typing or backspacing
// coalesces while the hand is quick (idle < 0.8s — the same timer that
// drives the live auto-run), while enter, forward-delete, duplicate
// and template loads are always their own restore point. undo/redo
// restore the whole document AND the cursor, so the second chance
// lands you exactly where you were standing.
#pragma once
#include <algorithm>
#include <array>
#include <cctype>
#include <cstring>
#include <functional>
#include <optional>
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
  bool tab = false;                            // IDE: tab — snippet trigger,
                                               // block indent, or 4 spaces
  bool backTab = false;                        // IDE: shift+tab — dedent
  bool braille = false;                        // b — toggle the dot renderer
  bool ctrlN = false;                          // IDE: next template
  bool pageUp = false, pageDn = false;         // IDE: page through the file
  bool del = false;                            // IDE: forward delete
  bool home = false, end = false;              // IDE: line ends
  bool ctrlG = false;                          // IDE: jump to the error line
  bool ctrlZ = false, ctrlY = false;           // IDE: undo / redo
  bool ctrlL = false;                          // IDE: clear the console
  bool ctrlF = false;                          // IDE: find in the file
  bool ctrlD = false;                          // IDE: duplicate this line
  bool delWord = false;                        // IDE: ctrl+w — eat the word behind the cursor
  bool wLeft = false, wRight = false;          // IDE: ctrl+←/→ — hop word by word
  bool delWordFwd = false;                     // IDE: ctrl+del — eat the word ahead
  bool comment = false;                        // IDE: ctrl+/ — toggle the line's comment
  bool docHome = false, docEnd = false;        // IDE: ctrl+home/end — the edges
  bool sUp = false, sDown = false;             // IDE: shift+↑/↓ — extend the selection
  bool sLeft = false, sRight = false;          // IDE: shift+←/→ — extend the selection
  bool sWLeft = false, sWRight = false;        // IDE: shift+ctrl+←/→ — select
                                               // word by word
  bool ctrlC = false, ctrlX = false, ctrlV = false;  // IDE: copy / cut / paste
  bool leap = false;                           // IDE: ctrl+\ — jump to the
                                               // partner bracket
  bool markToggle = false;                     // IDE: ctrl+F2 — plant/pull a pin
  bool markNext = false, markPrev = false;     // IDE: F2 / shift+F2 — leap
                                               // between pins
  int clickR = -1, clickC = -1;                // mouse press (IDE): doc cell,
                                               // (-1,-1) = no click this frame
  bool clickShift = false;                     // shift+click extends
  int dragR = -1, dragC = -1;                  // motion with button held: the
                                               // drag's live end
  bool clickRelease = false;                   // left button released
  std::string typed;                           // printable chars this frame
};

// a restore point: the whole document plus where you were standing —
// and WHAT the edit that follows was (typing, paste, comment, …) so the
// undo receipt can name it instead of counting blind steps
struct IdeSnap {
  std::vector<std::string> lines;
  int curR = 0, curC = 0;
  std::vector<int> marks;                      // the pins ride the restore
  std::string what;                            // the edit this step precedes
  bool operator==(const IdeSnap& o) const = default;
};

struct IdeState {
  bool open = false;
  std::vector<std::string> lines{""};       // a new file starts truly empty
  int curR = 0, curC = 0, top = 0;
  int hcol = 0;                                // horizontal scroll: first visible col
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
  // the searchlight: find lives in the same heart so the selftest can
  // drive it with keystrokes, exactly like the editor does
  bool findOpen = false;
  std::string findQ;                           // the live query
  bool findCase = false;                       // false: the beginner way
                                               // — "hello" finds HELLO;
                                               // :cases flips it strict
  std::vector<std::pair<int, int>> findHits;   // (row, col), in file order
  int findSel = -1;                            // the hit you're standing on
  bool ruler = true;                           // the 79/99 column guides
  int anchorR = -1, anchorC = -1;              // selection anchor (-1 = none)
  // the clipboard: the last copy or cut, as the document speaks it. A
  // line-wise clip (a copy with no selection, or ANY cut of a bare
  // line) pastes as whole lines above the cursor; a character-wise
  // clip splices in at the cursor, tail text riding behind it.
  std::vector<std::string> clip;
  bool clipLines = false;
  // the drag: where the left button went DOWN (−1 = up). Motion while
  // it is set drags the selection from the press to the hand.
  int pressR = -1, pressC = -1;
  // the drag's edge: the hand parked on the viewport's top (−1) or
  // bottom (+1) row while the button is held — the view pulls toward
  // the unseen lines, one notch at a time (dragAcc meters the pull).
  // dragHold is how long the pull has been SUSTAINED — a long hold
  // earns the second wind: the notches come twice as fast.
  int dragEdge = 0;
  double dragAcc = 0;
  double dragHold = 0;
  // the ledger: the files this studio had open, most recent first —
  // :recent lists and reopens them
  std::vector<std::string> recent;
  // the pins: bookmarks — lines you mark so the hand can leap back
  // (:mark plants, F2 leaps). Sorted, unique line positions that follow
  // insertions and cuts; a pin dies with its line.
  std::vector<int> marks;
  // the minimap: a compressed map of the whole document riding the
  // editor pane's right edge (drawn only when the terminal has room;
  // :minimap toggles it)
  bool minimap = true;
  // zen: the console rail hides and the body breathes — two more rows
  // of code. The searchlight still gets its row when it is up; receipts
  // gather silently until the quiet ends. :zen toggles.
  bool zen = false;
};

// ── the selection: anchor ↔ cursor, honestly ordered ────────────────
// The anchor is where the selection was BORN (shift+arrow sets it on
// first extension); the cursor is its live end. An empty range (anchor
// == cursor) is no selection at all.
using SelRange = std::array<int, 4>;           // r0, c0, r1, c1 (inclusive start/end)

inline std::optional<SelRange> ideSelRange(const IdeState& s) {
  if (s.anchorR < 0) return std::nullopt;
  if (s.anchorR == s.curR && s.anchorC == s.curC) return std::nullopt;
  if (s.anchorR < s.curR || (s.anchorR == s.curR && s.anchorC < s.curC))
    return SelRange{s.anchorR, s.anchorC, s.curR, s.curC};
  return SelRange{s.curR, s.curC, s.anchorR, s.anchorC};
}

inline void ideSelClear(IdeState& s) { s.anchorR = -1; s.anchorC = -1; }

// the selection's honest size in characters — the header speaks it
// ("sel N") so a drag always says how much it holds, live.
inline int ideSelCount(const IdeState& s) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  int n = 0;
  for (int r = r0; r <= r1; ++r) {
    const int last = static_cast<int>(s.lines[static_cast<size_t>(r)].size());
    n += ((r == r1) ? std::min(c1, last) : last) -
         ((r == r0) ? c0 : 0) + (r < r1 ? 1 : 0);   // the newline counts
  }
  return n;
}

// ── the pins: bookmarks — lines you mark so the hand can leap back ──
// Sorted, unique line positions. A look, never an edit: planting or
// leaping never dirties the document, never takes an undo step. The
// pins FOLLOW the document: lines landing above slide them down, lines
// cut beneath them take the pin along; a pin inside a cut dies with
// its line, and undo/redo prune pins the restored document never had.
inline bool ideMarkHas(const IdeState& s, int line) {
  return std::binary_search(s.marks.begin(), s.marks.end(), line);
}

// plant or pull; true when a pin NOW rides the line
inline bool ideMarkToggle(IdeState& s, int line) {
  if (line < 0) return false;
  const auto it = std::lower_bound(s.marks.begin(), s.marks.end(), line);
  if (it != s.marks.end() && *it == line) {
    s.marks.erase(it);
    return false;
  }
  s.marks.insert(it, line);
  return true;
}

// the next pin strictly BELOW `from`, wrapping to the first — the
// pinless file refuses with −1
inline int ideMarkNext(const IdeState& s, int from) {
  if (s.marks.empty()) return -1;
  for (const int m : s.marks)
    if (m > from) return m;
  return s.marks.front();                    // the wrap
}

// the pin strictly ABOVE `from`, wrapping to the last
inline int ideMarkPrev(const IdeState& s, int from) {
  if (s.marks.empty()) return -1;
  for (auto it = s.marks.rbegin(); it != s.marks.rend(); ++it)
    if (*it < from) return *it;
  return s.marks.back();                     // the wrap
}

// `count` lines land AT index `at`: pins beneath the landing slide down
inline void ideMarkShift(IdeState& s, int at, int count) {
  if (count <= 0) return;
  for (int& m : s.marks)
    if (m >= at) m += count;
}

// `count` lines leave at `at`: a pin inside the cut dies with its line,
// pins above the cut slide up
inline void ideMarkErase(IdeState& s, int at, int count) {
  if (count <= 0) return;
  const int end = at + count;
  s.marks.erase(std::remove_if(s.marks.begin(), s.marks.end(),
                               [&](int m) { return m >= at && m < end; }),
                s.marks.end());
  for (int& m : s.marks)
    if (m >= end) m -= count;
}

// out-of-range pins go — undo/redo restore documents the pins never saw
inline void ideMarkClamp(IdeState& s) {
  const int n = static_cast<int>(s.lines.size());
  s.marks.erase(std::remove_if(s.marks.begin(), s.marks.end(),
                               [&](int m) { return m < 0 || m >= n; }),
                s.marks.end());
}

inline void ideMarkClear(IdeState& s) { s.marks.clear(); }

// the selection goes first: the range is cut, the cursor collapses to
// its start, the anchor clears. False when there was nothing selected.
inline bool ideSelDelete(IdeState& s) {
  const auto sel = ideSelRange(s);
  if (!sel) return false;
  const auto [r0, c0, r1, c1] = *sel;
  if (r0 == r1) {
    std::string& l = s.lines[static_cast<size_t>(r0)];
    l.erase(static_cast<size_t>(c0), static_cast<size_t>(c1 - c0));
  } else {
    std::string& first = s.lines[static_cast<size_t>(r0)];
    const std::string tail = s.lines[static_cast<size_t>(r1)].substr(static_cast<size_t>(c1));
    first.resize(static_cast<size_t>(c0));
    first += tail;
    s.lines.erase(s.lines.begin() + r0 + 1, s.lines.begin() + r1 + 1);
    ideMarkErase(s, r0 + 1, r1 - r0);          // the cut's pins ride out
  }
  s.curR = r0;
  s.curC = c0;
  ideSelClear(s);
  return true;
}

// a word character for delete-word and word-hop purposes: letters,
// digits, snake_case
inline bool ideWordChar(char c) {
  return std::isalnum(static_cast<unsigned char>(c)) || c == '_';
}

// the cursor clamps to whatever document it lands on
inline void ideClamp(IdeState& s) {
  s.curR = std::clamp(s.curR, 0, static_cast<int>(s.lines.size()) - 1);
  s.curC = std::clamp(s.curC, 0,
                      static_cast<int>(s.lines[static_cast<size_t>(s.curR)].size()));
  if (s.anchorR >= 0) {                        // the anchor clamps too — a
    if (s.anchorR >= static_cast<int>(s.lines.size()))   // shrunken doc keeps
      s.anchorR = static_cast<int>(s.lines.size()) - 1;  // its selection honest
    s.anchorC = std::clamp(s.anchorC, 0,
                           static_cast<int>(s.lines[static_cast<size_t>(s.anchorR)].size()));
  }
}

inline void idePushUndo(IdeState& s, std::string what = "edit") {
  s.undo.push_back({s.lines, s.curR, s.curC, s.marks, std::move(what)});
  if (s.undo.size() > IdeState::kUndoMax)
    s.undo.erase(s.undo.begin(),
                 s.undo.begin() + static_cast<long>(s.undo.size() - IdeState::kUndoMax));
  s.redo.clear();                    // a fresh edit cuts the redo branch
  s.lastTyping = s.lastBack = false;
}

// the run of word characters ending AT the cursor — the tab trigger's
// fuel: type a shelf name and reach for tab, the word becomes the
// boilerplate. Nothing wordy behind the hand: an empty string.
inline std::string ideWordBehind(const IdeState& s) {
  const std::string& l = s.lines[static_cast<size_t>(s.curR)];
  const int c = std::min(s.curC, static_cast<int>(l.size()));
  int a = c;
  while (a > 0 && ideWordChar(l[static_cast<size_t>(a) - 1])) --a;
  return l.substr(static_cast<size_t>(a), static_cast<size_t>(c - a));
}

// ── the clipboard: copy, cut, paste — the way every editor speaks it ──
// Copy takes the selection (character-wise) or, with none live, the
// whole cursor line (line-wise). Cut is the copy plus the deletion —
// one honest restore point. Paste splices character-wise clips at the
// cursor and drops line-wise clips in above the cursor line; a live
// selection is the paste's bed and dies in the same undo step.
inline void ideClipCopy(IdeState& s) {
  const auto sel = ideSelRange(s);
  if (!sel) {                      // no selection: the cursor line rides
    s.clip.assign(1, s.lines[static_cast<size_t>(s.curR)]);
    s.clipLines = true;
    return;
  }
  const auto [r0, c0, r1, c1] = *sel;
  s.clip.clear();
  s.clipLines = false;
  if (r0 == r1) {
    const std::string& l = s.lines[static_cast<size_t>(r0)];
    s.clip.push_back(l.substr(static_cast<size_t>(c0),
                              static_cast<size_t>(c1 - c0)));
  } else {
    s.clip.push_back(
        s.lines[static_cast<size_t>(r0)].substr(static_cast<size_t>(c0)));
    for (int r = r0 + 1; r < r1; ++r)
      s.clip.push_back(s.lines[static_cast<size_t>(r)]);
    s.clip.push_back(
        s.lines[static_cast<size_t>(r1)].substr(0, static_cast<size_t>(c1)));
  }
}

// cut: the copy, then the deletion — one restore point. With no
// selection the whole line lifts out (the clip turns line-wise, so the
// paste puts it back as a line), the way every real editor cuts.
inline void ideClipCut(IdeState& s) {
  const bool had = ideSelRange(s).has_value();
  ideClipCopy(s);
  idePushUndo(s, "cut");
  if (!had) {
    s.lines.erase(s.lines.begin() + s.curR);
    if (s.lines.empty()) s.lines.emplace_back("");   // the doc never dies
    ideMarkErase(s, s.curR, 1);                // the line's pin rides out
    s.curC = 0;
  } else {
    ideSelDelete(s);
  }
  s.lastTyping = s.lastBack = false;
  s.dirty = true;
  s.idle = 0;
}

// the clip as one string, lines joined with '\n' — the OSC 52
// bridge's payload: the system clipboard speaks text, not lines
inline std::string ideClipText(const IdeState& s) {
  std::string out;
  for (size_t i = 0; i < s.clip.size(); ++i) {
    if (i) out += '\n';
    out += s.clip[i];
  }
  return out;
}

// RFC 4648 base64, honestly — the bridge's encoding
inline std::string ideBase64(const std::string& in) {
  static const char* tab =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string out;
  size_t i = 0;
  while (i + 3 <= in.size()) {
    const unsigned n = (static_cast<unsigned char>(in[i]) << 16) |
                       (static_cast<unsigned char>(in[i + 1]) << 8) |
                       static_cast<unsigned char>(in[i + 2]);
    out += tab[(n >> 18) & 63];
    out += tab[(n >> 12) & 63];
    out += tab[(n >> 6) & 63];
    out += tab[n & 63];
    i += 3;
  }
  const size_t rest = in.size() - i;
  if (rest == 1) {
    const unsigned n = static_cast<unsigned char>(in[i]) << 16;
    out += tab[(n >> 18) & 63];
    out += tab[(n >> 12) & 63];
    out += "==";
  } else if (rest == 2) {
    const unsigned n = (static_cast<unsigned char>(in[i]) << 16) |
                       (static_cast<unsigned char>(in[i + 1]) << 8);
    out += tab[(n >> 18) & 63];
    out += tab[(n >> 12) & 63];
    out += tab[(n >> 6) & 63];
    out += '=';
  }
  return out;
}

inline void ideClipPaste(IdeState& s) {
  if (s.clip.empty()) {
    s.console.push_back("engine: the clipboard is empty — ctrl+c first");
    return;
  }
  idePushUndo(s, "paste");
  ideSelDelete(s);                 // a live selection is the paste's bed
  auto& L = s.lines;
  if (s.clipLines) {
    // whole lines land ABOVE the cursor line; the cursor rests at the
    // end of what arrived
    const int at = s.curR;
    L.insert(L.begin() + at, s.clip.begin(), s.clip.end());
    ideMarkShift(s, at, static_cast<int>(s.clip.size()));
    s.curR += static_cast<int>(s.clip.size()) - 1;
    s.curC = static_cast<int>(L[static_cast<size_t>(s.curR)].size());
  } else {
    std::string& cur = L[static_cast<size_t>(s.curR)];
    const int at = std::min(s.curC, static_cast<int>(cur.size()));
    const std::string tail = cur.substr(static_cast<size_t>(at));
    cur.resize(static_cast<size_t>(at));
    cur += s.clip.front();
    // NOTE: L grows below — `cur` is not touched past this point
    if (s.clip.size() > 1)                     // pins beneath the splice
      ideMarkShift(s, s.curR + 1,              // slide down with the lines
                   static_cast<int>(s.clip.size()) - 1);
    for (size_t i = 1; i < s.clip.size(); ++i)
      L.insert(L.begin() + s.curR + static_cast<long>(i), s.clip[i]);
    L[static_cast<size_t>(s.curR) + s.clip.size() - 1] += tail;
    s.curR += static_cast<int>(s.clip.size()) - 1;
    s.curC = static_cast<int>(L[static_cast<size_t>(s.curR)].size()) -
             static_cast<int>(tail.size());
  }
  ideSelClear(s);
  s.lastTyping = s.lastBack = false;
  s.dirty = true;
  s.idle = 0;
}

// ── snippets: boilerplate that speaks the file's own language ───────
// The studio hosts three dialects (py, js, cpp) and the snippets do
// too — a "tick" snippet in game.py is `def on_tick(dt):`, in game.js
// it's `on.tick(() => { … })`, in game.cpp it's `g.onTick = …`. Every
// template here is checked against the real sdk/ contracts.
struct Snip {
  const char* name;
  const char* text;                            // \n-separated lines
};

inline const char* ideSnippetFamily(const std::string& path) {
  static const struct {
    const char* ext;
    const char* fam;
  } table[] = {{".js", "js"},   {".mjs", "js"},   {".ts", "js"},
               {".cpp", "cpp"}, {".cc", "cpp"},   {".cxx", "cpp"}};
  const size_t dot = path.rfind('.');
  if (dot == std::string::npos || dot + 1 == path.size()) return "py";
  const std::string ext = path.substr(dot);
  for (const auto& t : table)
    if (ext == t.ext) return t.fam;
  return "py";
}

inline const Snip* ideSnippetTable(const char* fam) {
  static const Snip py[] = {
      {"fn", "def name(arg):\n    pass"},
      {"tick", "def on_tick(dt):\n    pass"},
      {"key", "def on_key(k):\n    pass"},
      {"hit", "def on_hit(a, b):\n    pass"},
      {"start", "def on_start():\n    pass"},
      {"loop", "for i in range(10):\n    print(i)"},
      {"ifelse", "if cond:\n    pass\nelse:\n    pass"},
      {"class", "class Name:\n    def __init__(self):\n        pass"},
      {"try", "try:\n    pass\nexcept Exception as e:\n    print(e)"},
      {"imports", "from dxn3 import *\nimport random"},
      {"main",
       "from dxn3 import *\n\nplayer = rect(\"player\", W // 2, H // 2, 12, 5, "
       "\"#8b5cf6\")\nplayer.tag = \"player\"\n\ndef on_key(k):\n    if k == "
       "\"left\":  player.x = player.x - 2\n    if k == \"right\": player.x = "
       "player.x + 2\n\nrun()"},
      {nullptr, nullptr}};
  static const Snip js[] = {
      {"fn", "function name(arg) {\n  return arg;\n}"},
      {"tick", "on.tick(() => {\n});"},
      {"key", "on.key((k) => {\n});"},
      {"hit", "on.hit((a, b) => {\n});"},
      {"loop", "for (let i = 0; i < 10; ++i) {\n  console.log(i);\n}"},
      {"ifelse", "if (cond) {\n} else {\n}"},
      {"class", "class Name {\n  constructor() {\n  }\n}"},
      {nullptr, nullptr}};
  static const Snip cpp[] = {
      {"fn", "void name() {\n}"},
      {"tick", "g.onTick = [&](float dt) {\n};"},
      {"key", "g.onKey = [&](const std::string& k) {\n};"},
      {"hit", "g.onHit = [&](dxn3::Ent& a, dxn3::Ent& b) {\n};"},
      {"loop", "for (int i = 0; i < 10; ++i) {\n}"},
      {nullptr, nullptr}};
  if (fam[0] == 'j') return js;
  if (fam[0] == 'c') return cpp;
  return py;
}

// the snippet names this file's language speaks, in shelf order
inline std::vector<std::string> ideSnippetNames(const std::string& path) {
  std::vector<std::string> out;
  for (const Snip* t = ideSnippetTable(ideSnippetFamily(path)); t->name; ++t)
    out.push_back(t->name);
  return out;
}

// the shelf's one-line descriptions: what each snippet IS, in the
// bar's own words — the same words for every dialect (a "tick" is
// the every-frame hook whether the file speaks py, js or cpp). An
// unknown name describes nothing.
inline std::string ideSnippetDescribe(const std::string& name) {
  static const struct {
    const char* name;
    const char* what;
  } table[] = {
      {"fn", "a named function"},       {"tick", "the every-frame hook"},
      {"key", "the keypress hook"},     {"hit", "the collision hook"},
      {"start", "the once-at-boot hook"},
      {"loop", "a counted loop"},       {"ifelse", "a branch"},
      {"class", "a class"},             {"try", "a guarded block"},
      {"imports", "the studio's imports"},
      {"main", "a whole playable scene"},
      {nullptr, nullptr}};
  for (const auto* t = table; t->name; ++t)
    if (name == t->name) return t->what;
  return "";
}

// the shelf whispers with its descriptions: "fn — a named function",
// the typed prefix narrowing by NAME (the verb's own resolution law),
// the ledger's clipping law — the first entry that does not fit ends
// the line, never a cut word, never a half description.
inline std::string ideSnippetShelfWhisper(const std::string& path,
                                          const std::string& part,
                                          size_t maxW) {
  std::string w;
  for (const auto& nm : ideSnippetNames(path)) {
    if (nm.rfind(part, 0) != 0) continue;
    std::string entry = nm;
    const std::string what = ideSnippetDescribe(nm);
    if (!what.empty()) entry += " — " + what;
    const size_t need =
        w.empty() ? entry.size() : w.size() + 3 + entry.size();
    if (need > maxW) break;
    w += w.empty() ? entry : " · " + entry;
  }
  return w;
}

// exact-name lookup: the snippet's lines, or nothing when unknown
inline std::optional<std::vector<std::string>> ideSnippetFor(
    const std::string& name, const std::string& path) {
  for (const Snip* t = ideSnippetTable(ideSnippetFamily(path)); t->name; ++t)
    if (name == t->name) {
      std::vector<std::string> lines;
      std::string_view s = t->text;
      size_t pos;
      while ((pos = s.find('\n')) != std::string_view::npos) {
        lines.emplace_back(s.substr(0, pos));
        s.remove_prefix(pos + 1);
      }
      lines.emplace_back(s);
      return lines;
    }
  return std::nullopt;
}

// step back through time; false when there is nothing to undo. The
// step's edit label rides along, so redo can re-apply it by name.
inline bool ideUndo(IdeState& s) {
  if (s.undo.empty()) return false;
  s.redo.push_back({s.lines, s.curR, s.curC, s.marks, s.undo.back().what});
  s.lines = std::move(s.undo.back().lines);
  s.curR = s.undo.back().curR;
  s.curC = s.undo.back().curC;
  s.marks = s.undo.back().marks;               // the pins walk back too
  s.undo.pop_back();
  s.lastTyping = s.lastBack = false;
  ideSelClear(s);                    // the second chance drops the selection
  ideClamp(s);
  ideMarkClamp(s);                   // pins the restored document never had go
  return true;
}

// step forward again; false when there is nothing to redo
inline bool ideRedo(IdeState& s) {
  if (s.redo.empty()) return false;
  s.undo.push_back({s.lines, s.curR, s.curC, s.marks, s.redo.back().what});
  s.lines = std::move(s.redo.back().lines);
  s.curR = s.redo.back().curR;
  s.curC = s.redo.back().curC;
  s.marks = s.redo.back().marks;               // the pins step forward too
  s.redo.pop_back();
  s.lastTyping = s.lastBack = false;
  ideSelClear(s);
  ideClamp(s);
  ideMarkClamp(s);                   // pins the restored document never had go
  return true;
}

// the receipts name WHAT moved: "typing", "paste", "comment"… — never
// a blind count again
inline std::string ideUndoReceipt(const IdeState& s) {
  return "engine: undo — " +
         (s.undo.empty() ? std::string("edit") : s.undo.back().what) + " · " +
         std::to_string(s.undo.size()) + " step" +
         (s.undo.size() == 1 ? "" : "s") + " left";
}
inline std::string ideRedoReceipt(const IdeState& s) {
  return "engine: redo — " +
         (s.redo.empty() ? std::string("edit") : s.redo.back().what);
}

// ── the searchlight ─────────────────────────────────────────────────
// every match of the query, in file order. The beginner way (the
// default) is case-insensitive — "hello" finds HELLO; :cases turns
// the light strict and only the honest exact casing answers.
inline std::vector<std::pair<int, int>> ideFindAll(const IdeState& s,
                                                   const std::string& q) {
  std::vector<std::pair<int, int>> hits;
  if (q.empty()) return hits;
  auto lower = [](std::string x) {
    for (char& c : x)
      c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return x;
  };
  const std::string needle = s.findCase ? q : lower(q);
  for (int r = 0; r < static_cast<int>(s.lines.size()); ++r) {
    const std::string hay =
        s.findCase ? s.lines[static_cast<size_t>(r)]
                   : lower(s.lines[static_cast<size_t>(r)]);
    size_t at = 0;
    while ((at = hay.find(needle, at)) != std::string::npos) {
      hits.emplace_back(r, static_cast<int>(at));
      at += needle.size();          // non-overlapping, like every editor
    }
  }
  return hits;
}

// recompute the hits and aim at the first one at or after the cursor —
// find always moves you FORWARD from where you stand, never backward.
inline void ideFindRefresh(IdeState& s) {
  s.findHits = ideFindAll(s, s.findQ);
  s.findSel = -1;
  if (s.findHits.empty()) return;
  for (size_t i = 0; i < s.findHits.size(); ++i) {
    const auto& [r, c] = s.findHits[i];
    if (r > s.curR || (r == s.curR && c >= s.curC)) {
      s.findSel = static_cast<int>(i);
      return;
    }
  }
  s.findSel = 0;                    // everything is behind you: wrap to 0
}

// step to the next hit (enter), wrapping; false when there is nothing
inline bool ideFindNext(IdeState& s) {
  if (s.findHits.empty()) return false;
  s.findSel = (s.findSel + 1) % static_cast<int>(s.findHits.size());
  const auto& [r, c] = s.findHits[static_cast<size_t>(s.findSel)];
  s.curR = r;
  s.curC = c;
  ideSelClear(s);                    // the walk abandons any selection
  return true;
}

// ── pairs that carry their own closers ──────────────────────────────
inline char ideCloserFor(char open) {
  switch (open) {
    case '(': return ')';
    case '[': return ']';
    case '{': return '}';
    case '"': return '"';
    case '\'': return '\'';
    default: return 0;
  }
}
inline bool ideIsCloser(char c) {
  return c == ')' || c == ']' || c == '}' || c == '"' || c == '\'';
}

// the comment prefix this FILE speaks — by extension, honestly. A file
// with no name is shell-ish; every hosted language lands somewhere.
inline const char* ideCommentFor(const std::string& path) {
  static const struct {
    const char* ext;
    const char* prefix;
  } table[] = {{".py", "# "},   {".rb", "# "},   {".sh", "# "},
               {".yml", "# "},  {".yaml", "# "}, {".toml", "# "},
               {".ini", "# "},  {".js", "// "},  {".mjs", "// "},
               {".ts", "// "},  {".cpp", "// "}, {".cc", "// "},
               {".cxx", "// "}, {".cs", "// "},  {".java", "// "},
               {".json", "// "}, {".lua", "-- "}, {".hs", "-- "}};
  const size_t dot = path.rfind('.');
  if (dot == std::string::npos || dot + 1 == path.size()) return "# ";
  const std::string ext = path.substr(dot);
  for (const auto& t : table)
    if (ext == t.ext) return t.prefix;
  return "# ";
}

// ── word-wise hops (ctrl+left / ctrl+right) ─────────────────────────
// The same classification the ctrl+w bite uses: whitespace is a gap,
// and a run of word characters or a run of punctuation is ONE hop.
// Forward hops land at a run's END, backward hops at its START — the
// classic editor split, so words feel the same size both ways. Hops
// cross line edges: an empty line is just a wider gap.
inline void ideWordFwd(IdeState& s) {
  const int R = static_cast<int>(s.lines.size());
  if (R == 0) return;
  auto cls = [&s, R](int r, int c) -> int {  // 1 gap (or EOL), 2 word, 3 punct
    if (r < 0 || r >= R ||
        c >= static_cast<int>(s.lines[static_cast<size_t>(r)].size()))
      return 1;
    const char ch = s.lines[static_cast<size_t>(r)][static_cast<size_t>(c)];
    if (ch == ' ' || ch == '\t') return 1;
    return ideWordChar(ch) ? 2 : 3;
  };
  auto step = [&s, R](int& r, int& c) {      // advance one char, across EOLs
    ++c;
    while (r < R &&
           c >= static_cast<int>(s.lines[static_cast<size_t>(r)].size())) {
      ++r;
      c = 0;
    }
  };
  auto ride = [&](int& r, int& c, int run) { // to a run's END, never past the
    while (r < R && cls(r, c) == run) {      // line — only gaps may cross edges
      if (c + 1 >= static_cast<int>(s.lines[static_cast<size_t>(r)].size())) {
        ++c;                                 // rest at the line's end
        break;
      }
      step(r, c);
    }
  };
  int r = s.curR, c = s.curC;
  const int k = cls(r, c);
  if (k >= 2) {                       // a run is under you: ride it to the end
    ride(r, c, k);
  } else {                            // in the gap: to the END of the next run
    while (r < R && cls(r, c) == 1) step(r, c);
    if (r < R) ride(r, c, cls(r, c));
  }
  if (r >= R) {                       // walked off the end: rest at doc end
    r = R - 1;
    c = static_cast<int>(s.lines[static_cast<size_t>(r)].size());
  }
  s.curR = r;
  s.curC = c;
  ideClamp(s);
}

inline void ideWordBack(IdeState& s) {
  const int R = static_cast<int>(s.lines.size());
  if (R == 0) return;
  auto cls = [&s, R](int r, int c) -> int {
    if (r < 0 || r >= R || c < 0 ||
        c >= static_cast<int>(s.lines[static_cast<size_t>(r)].size()))
      return 1;                   // before the doc / EOL / line start: gap
    const char ch = s.lines[static_cast<size_t>(r)][static_cast<size_t>(c)];
    if (ch == ' ' || ch == '\t') return 1;
    return ideWordChar(ch) ? 2 : 3;
  };
  auto step = [&s](int& r, int& c) {         // retreat one char, across lines
    --c;
    while (r >= 0 && c < 0) {
      --r;
      c = r >= 0
              ? static_cast<int>(s.lines[static_cast<size_t>(r)].size())
              : 0;
    }
    return r >= 0;
  };
  int r = s.curR, c = s.curC;
  int pr = r, pc = c;
  if (!step(pr, pc)) return;                 // at the very start: honest no-op
  const int behind = cls(pr, pc);            // the char BEHIND owns the hop
  if (behind >= 2) {                  // a run is behind you: ride to its start
    r = pr;
    c = pc;
    while (true) {
      int qr = r, qc = c;
      if (!step(qr, qc) || cls(qr, qc) != behind) break;
      r = qr;
      c = qc;
    }
  } else {                       // in the gap: to the START of the run before it
    r = pr;
    c = pc;
    while (r >= 0 && cls(r, c) == 1) {
      int qr = r, qc = c;
      if (!step(qr, qc)) { r = -1; break; }
      r = qr;
      c = qc;
    }
    if (r >= 0) {
      const int run = cls(r, c);
      while (true) {
        int qr = r, qc = c;
        if (!step(qr, qc) || cls(qr, qc) != run) break;
        r = qr;
        c = qc;
      }
    }
  }
  if (r < 0) {
    r = 0;
    c = 0;
  }
  s.curR = r;
  s.curC = c;
  ideClamp(s);
}

// ── bracket match: the partner, across lines ────────────────────────
// The cell AT the cursor is probed first, then the one BEHIND it (both
// conventions exist in the wild). Quotes are honestly out — a lone
// quote inside a string would fake a match; only ( [ { get partners.
inline bool ideMatchBracket(const IdeState& s, int& mr, int& mc) {
  auto face = [](char ch) -> int {           // +1 opener, -1 closer, 0 neither
    if (ch == '(' || ch == '[' || ch == '{') return 1;
    if (ch == ')' || ch == ']' || ch == '}') return -1;
    return 0;
  };
  auto partnerOf = [](char ch) -> char {
    switch (ch) {
      case '(': return ')';
      case '[': return ']';
      case '{': return '}';
      case ')': return '(';
      case ']': return '[';
      case '}': return '{';
    }
    return 0;
  };
  const int R = static_cast<int>(s.lines.size());
  auto probe = [&](int r, int c) -> bool {
    if (r < 0 || r >= R || c < 0 ||
        c >= static_cast<int>(s.lines[static_cast<size_t>(r)].size()))
      return false;
    const char origin =
        s.lines[static_cast<size_t>(r)][static_cast<size_t>(c)];
    const int dir = face(origin);
    if (dir == 0) return false;
    const char want = partnerOf(origin);
    int depth = 0;
    int r2 = r, c2 = c;
    for (int guard = 0; guard < 200000; ++guard) {
      if (dir > 0) {                         // forward, wrapping line ends
        ++c2;
        while (r2 < R &&
               c2 >= static_cast<int>(s.lines[static_cast<size_t>(r2)].size())) {
          ++r2;
          c2 = 0;
        }
        if (r2 >= R) return false;           // the file ends before the pair does
      } else {                               // backward, wrapping line starts
        --c2;
        while (r2 >= 0 && c2 < 0) {
          --r2;
          c2 = r2 >= 0
                  ? static_cast<int>(s.lines[static_cast<size_t>(r2)].size()) - 1
                  : -1;
        }
        if (r2 < 0) return false;
      }
      const char h = s.lines[static_cast<size_t>(r2)][static_cast<size_t>(c2)];
      if (h == origin) ++depth;              // a twin of the bracket we hold
      else if (h == want) {
        if (depth == 0) {
          mr = r2;
          mc = c2;
          return true;
        }
        --depth;
      }
    }
    return false;                            // guard rail for pathological files
  };
  if (probe(s.curR, s.curC)) return true;
  return probe(s.curR, s.curC - 1);
}

// ── the gutter: wide enough for the document's honest line numbers ──
// Three columns carry 999 lines; a bigger document EARNS its extra
// digit, one notch at a time (1000+, then 10000+). Everything that
// speaks the body's geometry — the draw, the pointer translation, the
// ruler, the glows — reads this SAME rule, so no zone ever disagrees
// about where the code begins.
inline int ideGutterWidth(int lineCount) {
  int w = 4;                       // "%3d " — honest to 999
  if (lineCount > 999) ++w;        // "%4d " — to 9 999
  if (lineCount > 9999) ++w;       // "%5d " — beyond
  return w;
}

// ── horizontal scroll: the cursor is always on screen ───────────────
// Long lines slide under the cursor instead of being chopped off at
// the pane's edge. hcol is the first visible column; it follows the
// cursor with a small margin and rests at 0 whenever the line fits.
inline void ideHscroll(IdeState& s, int textW) {
  if (textW < 8) return;                     // a sliver of a pane: leave it be
  const int len =
      static_cast<int>(s.lines[static_cast<size_t>(s.curR)].size());
  if (len <= textW) {
    s.hcol = 0;                              // the whole line fits: rest
    return;
  }
  if (s.curC - s.hcol >= textW) s.hcol = s.curC - textW + 4;  // off the right
  if (s.curC - s.hcol < 0) s.hcol = s.curC - 3;               // off the left
  s.hcol = std::clamp(s.hcol, 0, len - textW + 1);  // never past the honest end
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

// ── the wheel and the nudge: the view slides, the hand rides ────────
// ctrl+↑/↓ nudge one line, the mouse wheel slides three; either way
// the honest pager contract holds — the hand is never lost out of
// sight. The view moves first; a hand that would fall off the edge
// rides along with it. Looking around never dirties the doc.
inline void ideScroll(IdeState& s, int delta) {
  if (delta == 0) return;
  const int page = s.page > 0 ? s.page : 1;
  // the SAME max the draw clamps to (a full last page) — a disagreeing
  // max here made the top oscillate and the wheel die after one notch
  const int maxTop = std::max(0, static_cast<int>(s.lines.size()) - page);
  s.top = std::clamp(s.top + delta, 0, maxTop);
  if (s.curR < s.top) s.curR = s.top;                    // rode past the top
  if (s.curR >= s.top + page) s.curR = s.top + page - 1; // …or the bottom
  ideClamp(s);
  s.idle = 0;
}

// ── the autoscroll: a hand parked at the viewport's edge pulls the ───
// view toward the unseen lines — the drag's other half. While the
// button is down AND a real drag is under way (an anchor exists — a
// stationary press never scrolls), each ~0.07s notch slides one line
// with the SAME ride contract as the wheel: the hand never leaves
// sight, the doc never dirties. A long gap (the hand was away, the
// app stalled) is an honest reset, never a catch-up jump. And a pull
// sustained past 1.2s earns the SECOND WIND: the meter halves and the
// notches come twice as fast — long documents are reached at speed,
// short ones never skipped past.
inline void ideDragAutoScroll(IdeState& s, int edge, double dt) {
  if (edge == 0 || s.pressR < 0 || s.anchorR < 0 || dt < 0 || dt > 0.5) {
    s.dragAcc = 0;
    s.dragHold = 0;              // the hold is spent with the meter
    return;
  }
  s.dragHold += dt;
  s.dragAcc += dt;
  constexpr double PERIOD = 0.07;              // one notch every 70ms
  const double period = s.dragHold > 1.2 ? PERIOD / 2 : PERIOD;
  int steps = 0;
  while (s.dragAcc >= period) {
    s.dragAcc -= period;
    ++steps;
  }
  if (steps == 0) return;
  ideScroll(s, edge * steps);                  // the ride contract applies
  // the hand IS the edge: parked on the bottom row it takes each line
  // the slide reveals — the selection grows from the anchor, exactly
  // like every desktop editor's autoscroll
  const int page = s.page > 0 ? s.page : 1;
  s.curR = edge > 0 ? s.top + page - 1 : s.top;
  ideClamp(s);
}

// ── the ledger: the files you had open, most recent first ───────────
// The studio remembers so you don't have to: :recent lists them,
// :recent <prefix> reopens. A path seen again moves to the front;
// the ledger keeps twelve names, no more.
inline void ideRecentPush(std::vector<std::string>& recent,
                          const std::string& path) {
  if (path.empty()) return;
  for (size_t i = 0; i < recent.size(); ++i)
    if (recent[i] == path) {
      recent.erase(recent.begin() + static_cast<long>(i));
      break;
    }
  recent.insert(recent.begin(), path);
  if (recent.size() > 12) recent.resize(12);
}

// the ledger whispers: what ":recent <part>" is about to resolve to,
// spoken while you type — full paths whose path OR basename carries
// the prefix, ledger order, joined with " · ", clipped to the bar's
// honest width. An empty ledger says so; a ghost stays silent (enter
// will refuse it, honestly).
inline std::string ideRecentWhisper(const std::vector<std::string>& recent,
                                    const std::string& part, size_t maxW) {
  if (recent.empty()) return "(the ledger is empty)";
  std::string w;
  for (const auto& p : recent) {
    const size_t slash = p.find_last_of('/');
    const std::string base =
        slash == std::string::npos ? p : p.substr(slash + 1);
    if (p.rfind(part, 0) != 0 && base.rfind(part, 0) != 0) continue;
    const size_t need = w.empty() ? p.size() : w.size() + 3 + p.size();
    if (need > maxW) break;
    w += w.empty() ? p : " · " + p;
  }
  return w;
}

// the pins whisper in the bar: ":bm" completes itself as you type.
// The ledger's entries speak "N) Ln L" — the :marks order, top of the
// file first — only the pins whose NUMBER carries the typed prefix,
// only as many as the bar honestly holds (the SAME clipping law as
// the ledger's whisper: the first entry that does not fit ends the
// line). An empty ledger stays silent — bare :bm already refuses
// with the way out, so the quiet is the honest answer.
inline std::string ideMarkWhisper(const IdeState& s, const std::string& part,
                                  size_t maxW) {
  if (s.marks.empty()) return "";
  std::string w;
  for (size_t i = 0; i < s.marks.size(); ++i) {
    const std::string entry =
        std::to_string(i + 1) + ") Ln " + std::to_string(s.marks[i] + 1);
    if (!part.empty() && entry.rfind(part, 0) != 0) continue;
    const size_t need =
        w.empty() ? entry.size() : w.size() + 3 + entry.size();
    if (need > maxW) break;
    w += w.empty() ? entry : " · " + entry;
  }
  return w;
}

// what ":recent <arg>" meant: an exact name wins, a UNIQUE prefix
// resolves, an ambiguous prefix returns "" (the caller lists the
// matches), and a ghost passes through unchanged — refused upstream,
// honestly.
inline std::string ideRecentResolve(const std::vector<std::string>& recent,
                                    const std::string& arg) {
  for (const auto& p : recent)
    if (p == arg) return p;
  auto basename = [](const std::string& p) {
    const size_t slash = p.find_last_of('/');
    return slash == std::string::npos ? p : p.substr(slash + 1);
  };
  std::string hit;
  int hits = 0;
  for (const auto& p : recent) {
    // the hand thinks in file names: the full path OR its basename
    // may carry the prefix
    if (p.rfind(arg, 0) == 0 || basename(p).rfind(arg, 0) == 0) {
      hit = p;
      ++hits;
    }
  }
  if (hits == 1) return hit;
  if (hits > 1) return "";
  return arg;
}

// the :open whisper: what ":open <part>" is about to load, spoken
// while you type. The LEDGER speaks first — files you had open, by
// path or basename — then the filesystem's candidates fill in behind,
// deduped, one rule of order: your files before the world's. Clipped
// to the bar's honest width, never past a separator.
inline std::string ideOpenWhisper(const std::vector<std::string>& recent,
                                  const std::string& part,
                                  const std::vector<std::string>& files,
                                  size_t maxW) {
  auto basename = [](const std::string& p) {
    const size_t slash = p.find_last_of('/');
    return slash == std::string::npos ? p : p.substr(slash + 1);
  };
  auto matches = [&part, &basename](const std::string& p) {
    return p.rfind(part, 0) == 0 || basename(p).rfind(part, 0) == 0;
  };
  std::string w;
  std::vector<std::string> seen;        // the ledger's word is final:
  bool full = false;                    // a path never speaks twice
  auto offer = [&](const std::string& p) {
    if (full || !matches(p)) return;
    for (const auto& s : seen)
      if (s == p) return;
    seen.push_back(p);
    const size_t need = w.empty() ? p.size() : w.size() + 3 + p.size();
    if (need > maxW) {
      full = true;                      // the FIRST name that does not
      return;                           // fit ends the whisper — the
    }                                   // same honest law as :recent's
    w += w.empty() ? p : " \xc2\xb7 " + p;
  };
  for (const auto& p : recent) offer(p);
  for (const auto& p : files) offer(p);
  return w;
}

// ── the minimap: the whole document, compressed, at a glance ────────
// One doc line becomes one map row; leading whitespace compresses 2:1
// (deep nests stay inside six columns) and a run of text compresses to
// half its honest length, rounding UP so one character still shows.
// The map slides to keep the cursor centered once the document outgrows
// the pane, and every row remembers whether it is a comment, a find
// hit, or inside the editor's viewport — main.cpp only paints.
struct IdeMiniRow {
  int start = 0, len = 0;                      // the bar: cols [start, start+len)
  bool blank = false;                          // nothing but air: a dim dot
  bool comment = false;                        // the line talks
  bool hit = false;                            // the searchlight found it
  bool mark = false;                           // a pin rides this line
  bool inView = false;                         // the editor shows it right now
};

struct IdeMini {
  int top = 0;                                 // the map's first doc line
  std::vector<IdeMiniRow> rows;
};

inline IdeMini ideMiniMap(const IdeState& s, int mapW, int bodyRows) {
  IdeMini m;
  const int N = static_cast<int>(s.lines.size());
  if (mapW <= 0 || bodyRows <= 0 || N == 0) return m;
  // centered follow: the cursor's line rides the map's middle (whole
  // doc fits: the map rests at the top — the honest overview)
  m.top = N <= bodyRows
              ? 0
              : std::clamp(s.curR - bodyRows / 2, 0, N - bodyRows);
  const char* preC = ideCommentFor(s.path);
  const std::string bare(preC, std::strlen(preC) - 1);      // "#" or "//" or "--"
  for (int li = m.top; li < N && li < m.top + bodyRows; ++li) {
    IdeMiniRow row;
    const std::string& ln = s.lines[static_cast<size_t>(li)];
    int indent = 0;
    for (const char ch : ln) {
      if (ch == ' ') ++indent;
      else if (ch == '\t') indent += 4;
      else break;
    }
    const int visLen =
        std::max(0, static_cast<int>(ln.size()) - indent);
    if (visLen == 0) {
      row.blank = true;
      row.len = 1;                           // a dot keeps the row anchored
    } else {
      row.start = std::min(mapW - 1, indent / 2);
      row.len = std::min(mapW - row.start, (visLen + 1) / 2);
    }
    const size_t first = ln.find_first_not_of(" \t");
    row.comment = first != std::string::npos &&
                  ln.compare(first, bare.size(), bare) == 0;
    for (const auto& [hr, hc] : s.findHits)
      if (hr == li) { row.hit = true; break; }
    row.mark = ideMarkHas(s, li);
    row.inView = li >= s.top && li < s.top + bodyRows;
    m.rows.push_back(row);
  }
  return m;
}

// ── the snippet whisper: the word under the hand names the shelf ────
// A shelf word ending at the cursor speaks up in the rail — "tab
// expands 'tick'" — so the trigger is discoverable before you know it.
// Non-words and ghost names stay silent; the editor is not a barker.
inline std::string ideSnippetWhisper(const IdeState& s) {
  const std::string w = ideWordBehind(s);
  if (w.empty() || !ideSnippetFor(w, s.path)) return "";
  return "tab expands '" + w + "'";
}

// ── the ordering: the selection's lines sort, A before B ────────────
// A multi-line selection is the bed: its whole lines sort
// lexicographically, byte-honest, the way every editor's sort-line
// command speaks. ONE honest restore point named "sort"; the hand
// rests at the head of the ordered block and the selection lets go.
// 0 when there is no bed (no selection, or a same-line one — a single
// line is always already in order); else the count of lines ordered.
inline int ideSortSel(IdeState& s) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  if (r1 <= r0) return 0;
  idePushUndo(s, "sort");
  std::sort(s.lines.begin() + r0, s.lines.begin() + r1 + 1);
  ideSelClear(s);
  s.curR = r0;
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  return r1 - r0 + 1;
}

// ── the ordering, descending: the selection's lines sort, Z before A ─
// The sort's mirror: the SAME bed (a multi-line selection), the SAME
// honest refusals, ONE restore point named "rsort", the hand at the
// block's head, the selection let go — the lines land biggest first.
// 0 when there is no bed; else the count of lines ordered.
inline int ideRsortSel(IdeState& s) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  if (r1 <= r0) return 0;
  idePushUndo(s, "rsort");
  std::sort(s.lines.begin() + r0, s.lines.begin() + r1 + 1,
            std::greater<std::string>());
  ideSelClear(s);
  s.curR = r0;
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  return r1 - r0 + 1;
}

// ── the case: the selection's letters change their voice ──────────
// :lower, :upper and :title speak one law: a selection is the bed (a
// same-line one counts — case is an in-line edit), ONE honest restore
// point named for the verb, the hand resting at the selection's head,
// the selection let go. Title capitals each line's word-starts and
// quiets the rest. The trim's law applies: what would not change is
// counted BEFORE the snapshot, so a selection with no letters takes
// no phantom undo step. 0 with no selection or nothing to change;
// else the count of letters that moved.
inline int ideCaseSel(IdeState& s, int mode) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  auto goal_for = [&](unsigned char ch, bool wordStart) -> char {
    const unsigned char low = static_cast<unsigned char>(std::tolower(ch));
    const bool cap = mode == 1 || (mode == 2 && wordStart);
    return static_cast<char>(cap ? std::toupper(low) : low);
  };
  int would = 0;                       // count BEFORE the snapshot
  {
    bool wordStart = true;
    for (int r = r0; r <= r1; ++r) {
      const std::string& l = s.lines[static_cast<size_t>(r)];
      const int from = (r == r0) ? c0 : 0;
      const int to = (r == r1)
                         ? std::min<int>(c1, static_cast<int>(l.size()))
                         : static_cast<int>(l.size());
      if (r > r0) wordStart = true;    // each line's head starts a word
      for (int c = from; c < to; ++c) {
        const unsigned char ch = static_cast<unsigned char>(l[static_cast<size_t>(c)]);
        if (!std::isalpha(ch)) { wordStart = true; continue; }
        if (l[static_cast<size_t>(c)] != goal_for(ch, wordStart)) ++would;
        wordStart = false;
      }
    }
  }
  if (would == 0) return 0;
  idePushUndo(s, mode == 0 ? "lower" : mode == 1 ? "upper" : "title");
  int changed = 0;
  bool wordStart = true;
  for (int r = r0; r <= r1; ++r) {
    std::string& l = s.lines[static_cast<size_t>(r)];
    const int from = (r == r0) ? c0 : 0;
    const int to = (r == r1)
                       ? std::min<int>(c1, static_cast<int>(l.size()))
                       : static_cast<int>(l.size());
    if (r > r0) wordStart = true;
    for (int c = from; c < to; ++c) {
      const unsigned char ch = static_cast<unsigned char>(l[static_cast<size_t>(c)]);
      if (!std::isalpha(ch)) { wordStart = true; continue; }
      const char goal = goal_for(ch, wordStart);
      wordStart = false;
      if (l[static_cast<size_t>(c)] != goal) {
        l[static_cast<size_t>(c)] = goal;
        ++changed;
      }
    }
  }
  ideSelClear(s);
  s.curR = r0;
  s.curC = std::min(c0, static_cast<int>(s.lines[static_cast<size_t>(r0)].size()));
  s.dirty = true;
  s.idle = 0;
  return changed;
}

// ── the collapse: consecutive duplicates are noise ──────────────
// :uniq speaks the file's own law: lines that say the same thing
// back-to-back say it once. A multi-line selection is the bed; NO
// selection means the whole document (uniq's natural home — its
// difference from the sort family, told out loud). The trim's law:
// nothing to collapse → no snapshot, no phantom step. ONE restore
// point named "uniq"; the pins speak the structural law (pins inside
// the collapse die, pins beneath slide up); the hand rests where the
// first line fell, clamped to the surviving document. Returns the
// count of lines that vanished.
inline int ideUniqSel(IdeState& s) {
  int r0 = 0;
  int r1 = static_cast<int>(s.lines.size()) - 1;
  if (const auto sel = ideSelRange(s)) {
    const auto [a, ca, b, cb] = *sel;
    r0 = a;
    r1 = b;
  }
  if (r1 <= r0) return 0;
  int would = 0;                       // the dry pass: count collapses
  {
    int kept = r0;
    for (int read = r0 + 1; read <= r1; ++read) {
      if (s.lines[static_cast<size_t>(read)] ==
          s.lines[static_cast<size_t>(kept)])
        ++would;
      else
        kept = read;
    }
  }
  if (would == 0) return 0;
  idePushUndo(s, "uniq");
  int kept = r0;                       // the compaction, with a map:
  std::vector<int> newHome(static_cast<size_t>(r1 + 1), -1);
  newHome[static_cast<size_t>(r0)] = r0;
  for (int read = r0 + 1; read <= r1; ++read)
    if (s.lines[static_cast<size_t>(read)] !=
        s.lines[static_cast<size_t>(kept)]) {
      s.lines[static_cast<size_t>(++kept)] = s.lines[static_cast<size_t>(read)];
      newHome[static_cast<size_t>(read)] = kept;
    }
  const int removed = r1 - kept;
  s.lines.erase(s.lines.begin() + kept + 1, s.lines.begin() + r1 + 1);
  // the pins speak the structural law: a pin on a fallen line dies, a
  // pin on a kept line rides the line to its new home, a pin beneath
  // the bed slides up by the count that fell
  {
    std::vector<int> nm;
    nm.reserve(s.marks.size());
    for (const int m : s.marks) {
      if (m < r0) nm.push_back(m);
      else if (m <= r1) {
        const int home = newHome[static_cast<size_t>(m)];
        if (home >= 0) nm.push_back(home);
      } else
        nm.push_back(m - removed);
    }
    s.marks = std::move(nm);
  }
  ideSelClear(s);
  s.curR = std::min(kept + 1, static_cast<int>(s.lines.size()) - 1);
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  return removed;
}

// ── the flip: the selection's lines walk end for end ────────────
// :rev reorders — it does not judge: the bed's first line lands last,
// the last lands first, and no alphabet has a say. The sort family's
// bed and refusals; ONE restore point named "rev"; the hand at the
// block's head; the selection let go. The pins ride the flip to their
// mirror positions (the content-following law), and the ledger is
// re-sorted — a flip is the one move that can unsort it.
inline int ideRevSel(IdeState& s) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  if (r1 <= r0) return 0;
  idePushUndo(s, "rev");
  std::reverse(s.lines.begin() + r0, s.lines.begin() + r1 + 1);
  bool pinsMoved = false;
  for (int& m : s.marks)
    if (m >= r0 && m <= r1) {
      m = r0 + (r1 - m);             // the mirror
      pinsMoved = true;
    }
  if (pinsMoved) std::sort(s.marks.begin(), s.marks.end());
  ideSelClear(s);
  s.curR = r0;
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  return r1 - r0 + 1;
}

// ── the breath: the selection's lines step right — or back ─────────
// :indent and :dedent speak the block's law: every line in the bed
// takes four honest spaces at its head (or gives up to four back).
// The family's bed — a selection names lines, and a same-line one
// counts (one line is a fine bed for a breath; tab and shift+tab
// already own the hand's line, the verbs own the selection's). The
// trim's law honored both ways: a line of pure air keeps its silence
// (no indent gathers on emptiness), a line with no leading air gives
// dedent nothing — and what would not move is counted BEFORE the
// snapshot, so a bed with no work takes no phantom undo step. ONE
// restore point named for the verb; the hand rests at the bed's head
// and rides the shift; the selection lets go. The pins hold their
// lines — a breath moves no line. 0 with no selection or nothing to
// shift; else the count of lines that moved.
inline int ideDentSel(IdeState& s, bool out) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  auto leadingAir = [](const std::string& l) {
    int n = 0;
    while (n < 4 && n < static_cast<int>(l.size()) &&
           l[static_cast<size_t>(n)] == ' ')
      ++n;
    return n;
  };
  auto keepsSilence = [](const std::string& l) {
    return l.find_first_not_of(" \t") == std::string::npos;
  };
  int would = 0;                       // the dry pass: count BEFORE the
  for (int r = r0; r <= r1; ++r) {     // snapshot — no phantom steps
    const std::string& l = s.lines[static_cast<size_t>(r)];
    if (out ? leadingAir(l) > 0 : !keepsSilence(l)) ++would;
  }
  if (would == 0) return 0;
  idePushUndo(s, out ? "dedent" : "indent");
  int moved = 0;
  int headCut = 0;                     // what the head line gave back
  for (int r = r0; r <= r1; ++r) {
    std::string& l = s.lines[static_cast<size_t>(r)];
    if (out) {
      const int cutn = leadingAir(l);
      if (cutn > 0) {
        l.erase(0, static_cast<size_t>(cutn));
        ++moved;
        if (r == r0) headCut = cutn;
      }
    } else if (!keepsSilence(l)) {
      l.insert(0, 4, ' ');
      ++moved;
    }
  }
  ideSelClear(s);
  s.curR = r0;                         // the hand rests at the bed's head
  s.curC = out ? std::max(0, std::min(c0, static_cast<int>(
                                     s.lines[static_cast<size_t>(r0)].size())) -
                            headCut)
               : std::min(c0 + 4, static_cast<int>(
                                      s.lines[static_cast<size_t>(r0)].size()));
  s.dirty = true;
  s.idle = 0;
  return moved;
}

// ── the ride: the selection's lines step one line up — or down ─────
// :lift and :drop move lines without an alphabet, without a mirror:
// the bed slides one neighbor over, and the neighbor walks around it.
// The bed is the selection's lines — and with no selection, the
// hand's line (the move's natural home; VSCode's muscle memory, the
// house's verbs). The pins RIDE their lines (the content-following
// law rev speaks) and the displaced neighbor's pin lands where the
// neighbor went — then the ledger is re-sorted, the move being a
// cousin of the flip. ONE restore point named for the verb; the hand
// rides the block's head; the selection lets go. A bed pressed
// against the edge takes no snapshot and no step. Returns the count
// of lines moved.
inline int ideMoveSel(IdeState& s, bool down) {
  int r0, r1, c0;
  if (const auto sel = ideSelRange(s)) {
    const auto [a, ca, b, cb] = *sel;
    r0 = a;
    c0 = ca;
    r1 = b;
  } else {
    r0 = r1 = s.curR;                  // no selection: the hand's line
    c0 = s.curC;
  }
  if (!down) {
    if (r0 == 0) return 0;             // nothing above to lift into
    idePushUndo(s, "lift");
    std::rotate(s.lines.begin() + r0 - 1, s.lines.begin() + r0,
                s.lines.begin() + r1 + 1);
    bool rode = false;
    for (int& m : s.marks) {
      if (m == r0 - 1) { m = r1; rode = true; }       // the neighbor's pin
      else if (m >= r0 && m <= r1) { m -= 1; rode = true; }
    }
    if (rode) std::sort(s.marks.begin(), s.marks.end());
    ideSelClear(s);
    s.curR = r0 - 1;                   // the hand rides the block's head
    s.curC = std::min(c0, static_cast<int>(s.lines[static_cast<size_t>(r0 - 1)].size()));
    s.dirty = true;
    s.idle = 0;
  } else {
    const int N = static_cast<int>(s.lines.size());
    if (r1 == N - 1) return 0;         // nothing below to drop into
    idePushUndo(s, "drop");
    std::rotate(s.lines.begin() + r0, s.lines.begin() + r1 + 1,
                s.lines.begin() + r1 + 2);
    bool rode = false;
    for (int& m : s.marks) {
      if (m == r1 + 1) { m = r0; rode = true; }       // the neighbor's pin
      else if (m >= r0 && m <= r1) { m += 1; rode = true; }
    }
    if (rode) std::sort(s.marks.begin(), s.marks.end());
    ideSelClear(s);
    s.curR = r0 + 1;                   // the hand rides the block's head
    s.curC = std::min(c0, static_cast<int>(s.lines[static_cast<size_t>(r0 + 1)].size()));
    s.dirty = true;
    s.idle = 0;
  }
  return r1 - r0 + 1;
}

// ── the echo: the selection's lines say it twice ───────────────────
// :dup duplicates the bed — the copies land directly below, the
// originals keep their pins (a pin marks a line, not its echo), and
// the lines beneath the bed slide down by the bed's size. With no
// selection the hand's line is the bed (the ride's law — the move's
// natural home is the echo's too). ONE restore point named "dup";
// the hand lands on the COPY's head — the fresh work is the echo.
// Never refuses: the hand's line always says something twice.
inline int ideDupSel(IdeState& s) {
  int r0, r1;
  if (const auto sel = ideSelRange(s)) {
    const auto [a, ca, b, cb] = *sel;
    r0 = a;
    r1 = b;
  } else {
    r0 = r1 = s.curR;                  // no selection: the hand's line
  }
  const int count = r1 - r0 + 1;
  idePushUndo(s, "dup");
  const std::vector<std::string> bed(s.lines.begin() + r0,
                                     s.lines.begin() + r1 + 1);
  s.lines.insert(s.lines.begin() + r1 + 1, bed.begin(), bed.end());
  ideMarkShift(s, r1 + 1, count);      // the world beneath slides down
  ideSelClear(s);
  s.curR = r0 + count;                 // the hand lands on the copy's head
  s.curC = std::min(s.curC, static_cast<int>(s.lines[static_cast<size_t>(s.curR)].size()));
  s.dirty = true;
  s.idle = 0;
  return count;
}

// ── the fold: the selection's lines say it once, in one breath ─────
// :join folds the bed into a single line — each line trimmed, the
// pieces separated by one honest space, pure air contributing
// nothing. The bed is the selection's lines; with NO selection the
// hand's line folds with the one below (vim's J law — the fold's
// natural home). A same-line bed folds nothing, and a bed pressed
// against the document's last line has nothing below to fold into —
// both refuse without a phantom step. ONE restore point named
// "join"; the uniq's pin law speaks (a pin on a folded line dies —
// it marked a line, and the line is gone — the world beneath slides
// up); the hand rests at the SEAM, where the first fold landed.
inline int ideJoinSel(IdeState& s) {
  int r0, r1;
  if (const auto sel = ideSelRange(s)) {
    const auto [a, ca, b, cb] = *sel;
    r0 = a;
    r1 = b;
  } else {
    r0 = s.curR;                       // vim's J law: the hand's line
    r1 = s.curR + 1;                   // folds with the one below
  }
  if (r1 <= r0) return 0;              // a same-line bed folds nothing
  if (r1 >= static_cast<int>(s.lines.size()))
    return 0;                          // nothing below to fold into
  std::vector<std::string> pieces;
  for (int r = r0; r <= r1; ++r) {
    const std::string& l = s.lines[static_cast<size_t>(r)];
    const size_t b0 = l.find_first_not_of(" \t");
    if (b0 == std::string::npos) continue;      // pure air stays air
    const size_t b1 = l.find_last_not_of(" \t");
    pieces.push_back(l.substr(b0, b1 - b0 + 1));
  }
  std::string folded;
  for (size_t i = 0; i < pieces.size(); ++i)
    folded += i ? " " + pieces[i] : pieces[i];
  const int seam =
      pieces.size() >= 2 ? static_cast<int>(pieces[0].size()) + 1 : 0;
  idePushUndo(s, "join");
  s.lines[static_cast<size_t>(r0)] = folded;
  s.lines.erase(s.lines.begin() + r0 + 1, s.lines.begin() + r1 + 1);
  {                                    // the uniq's pin law: a folded
    std::vector<int> nm;               // line's pin dies, the world
    nm.reserve(s.marks.size());        // beneath slides up
    for (const int m : s.marks) {
      if (m > r0 && m <= r1) continue;
      nm.push_back(m > r1 ? m - (r1 - r0) : m);
    }
    s.marks = std::move(nm);
  }
  ideSelClear(s);
  s.curR = r0;                         // the hand rests at the seam
  s.curC = std::min(seam, static_cast<int>(folded.size()));
  s.dirty = true;
  s.idle = 0;
  return r1 - r0 + 1;
}

// ── the sweep: trailing whitespace is noise ─────────────────────────
// Every line's tail spaces and tabs come off; a line of pure air goes
// truly blank. ONE honest restore point named "trim", taken only when
// something would actually move (a clean document is never given a
// phantom step); the count of touched lines rides back so the receipt
// can name the work. The cursor clamps to its line's new honest end.
inline int ideTrimTrailing(IdeState& s) {
  int would = 0;                       // count BEFORE the snapshot: the
  for (const auto& l : s.lines) {      // undo step must hold the air
    const size_t last = l.find_last_not_of(" \t");
    if (last == std::string::npos) {
      if (!l.empty()) ++would;
    } else if (last + 1 < l.size()) {
      ++would;
    }
  }
  if (would == 0) return 0;
  idePushUndo(s, "trim");
  for (auto& l : s.lines) {
    const size_t last = l.find_last_not_of(" \t");
    if (last == std::string::npos)
      l.clear();
    else if (last + 1 < l.size())
      l.resize(last + 1);
  }
  ideClamp(s);
  s.dirty = true;
  s.idle = 0;
  return would;
}

// a snippet lands at the cursor: a blank line is REPLACED (the
// boilerplate takes the empty stage), else the block slides in AFTER the
// cursor line. One undo step; the cursor rests at the end of the block.
inline void ideInsertBlock(IdeState& s, const std::vector<std::string>& block) {
  if (block.empty()) return;
  if (s.curR >= static_cast<int>(s.lines.size()))
    s.curR = static_cast<int>(s.lines.size()) - 1;
  idePushUndo(s, "snippet");
  const bool blank =
      s.lines[static_cast<size_t>(s.curR)].find_first_not_of(" \t") ==
      std::string::npos;
  auto at = s.lines.begin() + (blank ? s.curR : s.curR + 1);
  if (blank) {                               // the empty line steps aside
    at = s.lines.erase(at);
    ideMarkErase(s, s.curR, 1);              // its pin steps aside with it
  }
  s.lines.insert(at, block.begin(), block.end());
  ideMarkShift(s, blank ? s.curR : s.curR + 1,
               static_cast<int>(block.size()));
  s.curR += blank ? static_cast<int>(block.size()) - 1
                  : static_cast<int>(block.size());
  s.curC = static_cast<int>(s.lines[static_cast<size_t>(s.curR)].size());
  s.dirty = true;                            // the game hears about it
  s.idle = 0;
}

// ── the leap: the hand jumps to the partner bracket ───────────────
// ctrl+\ — the keyboard sibling of the partner glow. The SAME match
// rule speaks (the cell at the cursor, then the one behind it); the
// hand lands ON the partner and any selection lets go — a leap is a
// look, never an edit. False when there is no partner to reach.
inline bool ideLeapToPartner(IdeState& s) {
  int mr = -1, mc = -1;
  if (!ideMatchBracket(s, mr, mc)) return false;
  s.curR = mr;
  s.curC = mc;
  ideSelClear(s);
  ideClamp(s);
  s.idle = 0;
  return true;
}

// the editor owns typing: chars land at the cursor, backspace joins
// lines, enter splits them (and carries the indent down), every edit is
// undoable
inline void ideKey(IdeState& ide, const Keys& k) {
  // ── esc owns its frame. A bare ESC is a MODE key — play, search,
  // escape — and when a pty delivers it coalesced with typing (the
  // app stalled past a keypress burst), the text belongs to the NEXT
  // frame, never to this one. The smoke once typed ":recent" into a
  // live document exactly this way; the gate caught it. Nothing that
  // follows an ESC in the same breath may touch the document.
  if (k.esc) {
    ide.idle = 0;
    return;
  }
  // ── the searchlight is up: the query owns the keyboard, the buffer
  // never changes while you search
  if (ide.findOpen) {
    if (k.ctrlF) { ide.findOpen = false; return; }        // toggle off
    if (!k.typed.empty()) ide.findQ += k.typed;
    if (k.back) {
      if (!ide.findQ.empty()) ide.findQ.pop_back();
      else { ide.findOpen = false; return; }   // back on empty: done looking
    }
    if (k.enter) ideFindNext(ide);             // to the next hit, wrapping
    if (!k.typed.empty() || k.back) ideFindRefresh(ide);
    return;
  }
  // ctrl+f raises the searchlight with a clean query
  if (k.ctrlF) {
    ide.findOpen = true;
    ide.findQ.clear();
    ide.findHits.clear();
    ide.findSel = -1;
    ide.lastTyping = ide.lastBack = false;
    return;
  }

  auto& L = ide.lines;
  if (ide.curR >= static_cast<int>(L.size()))
    ide.curR = static_cast<int>(L.size()) - 1;

  // ── the pointer: a click lands the hand where you pointed. main
  // translated the cell into document coords (it owns the map rail's
  // geometry); here every click is an honest cursor move — clamped,
  // selection-dropping (or extending with shift), never dirtying the
  // doc: the game has no reason to re-run because you looked around.
  if (k.clickR >= 0) {
    const int oldR = ide.curR, oldC = ide.curC;
    ide.curR = std::clamp(k.clickR, 0, static_cast<int>(L.size()) - 1);
    ide.curC = std::clamp(k.clickC, 0,
                          static_cast<int>(L[static_cast<size_t>(ide.curR)].size()));
    if (k.clickShift) {                        // shift+click: extend, like
      if (ide.anchorR < 0) {                   // the shift+arrows do
        ide.anchorR = oldR;
        ide.anchorC = oldC;
      }
    } else {
      ideSelClear(ide);                        // a bare click lets the
    }                                          // selection go — standard
    if (!k.clickShift) {                       // a bare press is where a
      ide.pressR = ide.curR;                   // drag would start
      ide.pressC = ide.curC;
    }
    ide.lastTyping = ide.lastBack = false;
    ide.idle = 0;
  }
  if (k.clickRelease) {
    ide.pressR = -1;                           // the button came up: the
    ide.pressC = -1;                           // drag is over, the selection
    ide.dragEdge = 0;                          // it made simply stays — and
    ide.dragAcc = 0;                           // the edge pull is spent, its
    ide.dragHold = 0;                          // wind with it
  }
  if (k.dragR >= 0 && ide.pressR >= 0) {       // motion with the button
                                                // held: drag the selection
    ide.anchorR = ide.pressR;                  // from the press…
    ide.anchorC = ide.pressC;
    ide.curR = std::clamp(k.dragR, 0, static_cast<int>(L.size()) - 1);
    ide.curC = std::clamp(k.dragC, 0,
                          static_cast<int>(L[static_cast<size_t>(ide.curR)].size()));
    ide.lastTyping = ide.lastBack = false;
    ide.idle = 0;
  }

  // ── the leap: ctrl+\ — the hand jumps to the partner bracket. A
  // look, never an edit: nothing dirties, nothing undoes, the frame
  // is the leap's alone.
  if (k.leap) {
    ideLeapToPartner(ide);
    ide.lastTyping = ide.lastBack = false;
    ide.idle = 0;
    return;
  }

  // ── the pins: F2 leaps between bookmarks, ctrl+F2 plants/pulls. A
  // look, never an edit: nothing dirties, nothing undoes, the frame is
  // the pin's alone.
  if (k.markToggle || k.markNext || k.markPrev) {
    if (k.markToggle) {
      const bool on = ideMarkToggle(ide, ide.curR);
      ide.console.push_back(
          on ? "engine: pin planted on line " +
                   std::to_string(ide.curR + 1) + " — F2 leaps, :marks lists"
             : "engine: pin pulled from line " +
                   std::to_string(ide.curR + 1));
    } else {
      const int to = k.markNext ? ideMarkNext(ide, ide.curR)
                                : ideMarkPrev(ide, ide.curR);
      if (to < 0) {
        ide.console.push_back(
            "engine: no pins yet — :mark plants one on this line");
      } else {
        ide.curR = to;
        ide.curC = 0;
        ideSelClear(ide);
        ide.console.push_back("engine: the hand leaps to the pin at line " +
                              std::to_string(to + 1));
      }
    }
    ide.lastTyping = ide.lastBack = false;
    ide.idle = 0;
    return;
  }

  // ── the clipboard: when one of these fires it is the frame's whole
  // edit — copy never dirties, cut and paste are one honest step each.
  if (k.ctrlC) { ideClipCopy(ide); return; }
  if (k.ctrlX) { ideClipCut(ide); ideClamp(ide); return; }
  if (k.ctrlV) { ideClipPaste(ide); ideClamp(ide); return; }

  // ── the selection and the edit keys: a typed char, backspace,
  // forward-delete or enter with a selection live REPLACES the range —
  // and that replacement is always its own restore point. NOTE: the
  // range cut may reallocate L, so `line` is fetched AFTER this block.
  const bool editOp = !k.typed.empty() || k.back || k.del || k.enter;
  const bool selEdit = editOp && ideSelRange(ide).has_value();
  if (selEdit) {
    idePushUndo(ide, "selection");
    ideSelDelete(ide);
    ide.lastTyping = ide.lastBack = false;
  }

  // ── the second chance: decide whether this frame's edits continue the
  // previous group (quick hands coalesce) or open a new restore point
  const bool quick = ide.idle < 0.8;
  if (!k.typed.empty()) {
    if (!selEdit) {
      if (!(ide.lastTyping && quick)) idePushUndo(ide, "typing");
      else ide.redo.clear();
    }
    ide.lastTyping = true;
    ide.lastBack = false;
  }
  if (k.back && !selEdit) {
    if (!((ide.lastTyping || ide.lastBack) && quick)) idePushUndo(ide, "backspace");
    else ide.redo.clear();
    ide.lastBack = true;
    ide.lastTyping = false;
  }
  if (k.enter && !selEdit) idePushUndo(ide, "enter");
  if (k.del && !selEdit) idePushUndo(ide, "delete");
  if (k.ctrlD && !selEdit) idePushUndo(ide, "duplicate");
  if (k.delWord && !selEdit) idePushUndo(ide, "word bite");
  if (k.delWordFwd && !selEdit) idePushUndo(ide, "forward bite");
  if (k.comment && !selEdit) idePushUndo(ide, "comment");   // structure stands
                                  // alone — a selection replacement pushed
                                  // once above already

  std::string& line = L[static_cast<size_t>(ide.curR)];   // AFTER any range cut

  for (const char ch : k.typed) {
    // a closer you already have is skipped over, never doubled
    if (ideIsCloser(ch) && ide.curC < static_cast<int>(line.size()) &&
        line[static_cast<size_t>(ide.curC)] == ch) {
      ++ide.curC;
      continue;
    }
    line.insert(line.begin() + std::min(ide.curC, static_cast<int>(line.size())), ch);
    ++ide.curC;
    // an opener carries its closer — brackets always pair; quotes pair
    // only when NEITHER neighbor is a word character, so "don't" keeps
    // its honest apostrophe while `x = "hello"` still wraps
    const char closer = ideCloserFor(ch);
    if (closer) {
      const bool quote = ch == '"' || ch == '\'';
      bool pair = true;
      if (quote) {
        const bool prevWord =
            ide.curC >= 2 &&
            (std::isalnum(static_cast<unsigned char>(line[static_cast<size_t>(ide.curC) - 2])) ||
             line[static_cast<size_t>(ide.curC) - 2] == '_');
        const bool nextWord =
            ide.curC < static_cast<int>(line.size()) &&
            (std::isalnum(static_cast<unsigned char>(line[static_cast<size_t>(ide.curC)])) ||
             line[static_cast<size_t>(ide.curC)] == '_');
        pair = !prevWord && !nextWord;
      }
      if (pair)
        line.insert(line.begin() + std::min(ide.curC, static_cast<int>(line.size())),
                    closer);
    }
  }
  if (k.back && !selEdit) {
    // backspace between an empty pair removes BOTH halves — the pair
    // was born together, it dies together
    if (ide.curC > 0 && ide.curC < static_cast<int>(line.size()) &&
        ideCloserFor(line[static_cast<size_t>(ide.curC) - 1]) ==
            line[static_cast<size_t>(ide.curC)]) {
      line.erase(line.begin() + ide.curC);
      line.erase(line.begin() + (ide.curC - 1));
      --ide.curC;
    }
    else if (ide.curC > 0) { line.erase(line.begin() + ide.curC - 1); --ide.curC; }
    else if (ide.curR > 0) {                       // join with previous line
      ide.curC = static_cast<int>(L[static_cast<size_t>(ide.curR - 1)].size());
      L[static_cast<size_t>(ide.curR - 1)] += line;
      L.erase(L.begin() + ide.curR);
      ideMarkErase(ide, ide.curR, 1);              // the joined line's pin goes
      --ide.curR;
    }
  }
  if (k.tab || k.backTab) {                    // tab and shift+tab: the
                                               // shelf answers, or the
                                               // block breathes
    const auto selT = ideSelRange(ide);
    if (selT && (*selT)[2] > (*selT)[0]) {     // a block under the hand:
      idePushUndo(ide, "indent");              // every touched line steps
      for (int r = (*selT)[0]; r <= (*selT)[2]; ++r) {   // left or right
        std::string& l = L[static_cast<size_t>(r)];
        if (k.tab) {
          l.insert(0, 4, ' ');
        } else {
          int cutn = 0;                        // up to four honest spaces
          while (cutn < 4 && cutn < static_cast<int>(l.size()) &&
                 l[static_cast<size_t>(cutn)] == ' ')
            ++cutn;
          if (cutn > 0) l.erase(0, static_cast<size_t>(cutn));
        }
      }
      ide.dirty = true;                        // the game hears about it
      ide.idle = 0;
    } else if (k.backTab) {                    // shift+tab alone: this line
      std::string& cur = L[static_cast<size_t>(ide.curR)];   // steps back
      int cutn = 0;
      while (cutn < 4 && cutn < static_cast<int>(cur.size()) &&
             cur[static_cast<size_t>(cutn)] == ' ')
        ++cutn;
      if (cutn > 0) {
        idePushUndo(ide, "dedent");
        cur.erase(0, static_cast<size_t>(cutn));
        ide.curC = std::max(0, ide.curC - cutn);
        ide.dirty = true;
        ide.idle = 0;
      }
    } else {                                   // plain tab: a shelf name
                                               // under the hand becomes the
                                               // boilerplate, else 4 spaces
      std::string& cur = L[static_cast<size_t>(ide.curR)];   // fresh: edits above
      const std::string w = ideWordBehind(ide);
      const auto block = ideSnippetFor(w, ide.path);
      if (block) {
        idePushUndo(ide, "snippet");           // the word becomes the snippet
        const int c = std::min(ide.curC, static_cast<int>(cur.size()));
        int a = c;
        while (a > 0 && ideWordChar(cur[static_cast<size_t>(a) - 1])) --a;
        const std::string tail = cur.substr(static_cast<size_t>(c));
        cur.resize(static_cast<size_t>(a));
        cur += (*block)[0];
        // NOTE: L grows below — `cur` is not touched past this point
        if (block->size() > 1)                   // pins beneath the boiler
          ideMarkShift(ide, ide.curR + 1,        // plate slide down with it
                       static_cast<int>(block->size()) - 1);
        for (size_t i = 1; i < block->size(); ++i)
          L.insert(L.begin() + ide.curR + static_cast<long>(i), (*block)[i]);
        L[static_cast<size_t>(ide.curR) + block->size() - 1] += tail;
        ide.curR += static_cast<int>(block->size()) - 1;
        ide.curC = static_cast<int>(L[static_cast<size_t>(ide.curR)].size()) -
                   static_cast<int>(tail.size());
        ide.dirty = true;
        ide.idle = 0;
      } else {
        if (selT) {                            // a same-line selection is
          idePushUndo(ide, "indent");          // the tab's bed: replaced
          ideSelDelete(ide);
          std::string& cur2 = L[static_cast<size_t>(ide.curR)];
          cur2.insert(static_cast<size_t>(std::min(ide.curC, static_cast<int>(cur2.size()))),
                      4, ' ');
          ide.curC += 4;
        } else {
          if (!(ide.lastTyping && quick)) idePushUndo(ide, "tab");
          else ide.redo.clear();
          std::string& cur2 = L[static_cast<size_t>(ide.curR)];
          cur2.insert(static_cast<size_t>(std::min(ide.curC, static_cast<int>(cur2.size()))),
                      4, ' ');
          ide.curC += 4;
          ide.lastTyping = true;
          ide.lastBack = false;
        }
      }
    }
  }
  if (k.enter) {
    // re-fetch: back may have joined lines and grown/shrunk L above
    std::string& cur = L[static_cast<size_t>(ide.curR)];
    const int at = std::min(ide.curC, static_cast<int>(cur.size()));
    // enter between a bracket pair: the closer keeps its ground on a
    // line of its own — `f(|)` becomes the three-line ceremony. Quotes
    // stay out: breaking a string literal is just a split.
    const bool pairSplit =
        at > 0 && at < static_cast<int>(cur.size()) &&
        ((cur[static_cast<size_t>(at) - 1] == '(' && cur[at] == ')') ||
         (cur[static_cast<size_t>(at) - 1] == '[' && cur[at] == ']') ||
         (cur[static_cast<size_t>(at) - 1] == '{' && cur[at] == '}'));
    std::string rest = cur.substr(static_cast<size_t>(at));
    cur.resize(static_cast<size_t>(at));
    // the block rides down: inherit this line's leading whitespace,
    // bump a level after an opener, drop one before a closer
    const size_t ws = cur.find_first_not_of(" \t");
    const std::string base = (ws == std::string::npos) ? cur : cur.substr(0, ws);
    std::string indent = base;
    if (ideOpensBlock(cur) || (pairSplit && cur[static_cast<size_t>(at) - 1] == '{'))
      indent += "    ";
    if (ideClosesBlock(rest) && !pairSplit) {
      const size_t cut = indent.size() >= 4 ? indent.size() - 4 : 0;
      indent.resize(cut);
    }
    if (pairSplit) {
      L.insert(L.begin() + ide.curR + 1, indent);      // the naked middle line
      L.insert(L.begin() + ide.curR + 2, base + rest); // the closer keeps its
                                                       // ground at the base
      ideMarkShift(ide, ide.curR + 1, 2);              // pins slide down
      ++ide.curR;                              // the cursor takes the middle
    } else {
      L.insert(L.begin() + ide.curR + 1, indent + rest);
      ideMarkShift(ide, ide.curR + 1, 1);
      ++ide.curR;
    }
    ide.curC = static_cast<int>(indent.size());
  }
  // ── movement: shift extends the selection, plain moves drop it.
  // The anchor is born at the cursor on the FIRST shift-extension —
  // arrows, or the word hops (shift+ctrl+←/→ select word by word).
  const bool shiftMove = k.sUp || k.sDown || k.sLeft || k.sRight ||
                         k.sWLeft || k.sWRight;
  const bool plainMove = k.up || k.down || k.aLeft || k.aRight || k.home ||
                         k.end || k.pageUp || k.pageDn || k.docHome ||
                         k.docEnd || k.wLeft || k.wRight;
  if (shiftMove && ide.anchorR < 0) {
    ide.anchorR = ide.curR;
    ide.anchorC = ide.curC;
  }
  if (plainMove && !shiftMove) ideSelClear(ide);
  if (k.up || k.sUp) --ide.curR;
  if (k.down || k.sDown) ++ide.curR;
  if (k.aLeft || k.sLeft) --ide.curC;
  if (k.aRight || k.sRight) ++ide.curC;
  if (k.wLeft) ideWordBack(ide);             // word hops move the cursor only —
  if (k.wRight) ideWordFwd(ide);             // the document never hears about it
  if (k.sWLeft) ideWordBack(ide);            // the word hops with the anchor
  if (k.sWRight) ideWordFwd(ide);            // riding — the selection grows
  if (k.home) ide.curC = 0;
  if (k.end) ide.curC = static_cast<int>(L[static_cast<size_t>(ide.curR)].size());
  if (k.docHome) {                           // ctrl+home: the very top
    ide.curR = 0;
    ide.curC = 0;
  }
  if (k.docEnd) {                            // ctrl+end: the very bottom
    ide.curR = static_cast<int>(L.size()) - 1;
    ide.curC = static_cast<int>(L.back().size());
  }
  if (k.pageUp) ide.curR -= ide.page;
  if (k.pageDn) ide.curR += ide.page;
  if (k.del && !selEdit) {                   // forward delete — with a
                                             // selection the cut already ran
    // re-fetch: enter may have grown L above and reallocated the buffer
    std::string& cur = L[static_cast<size_t>(ide.curR)];
    if (ide.curC < static_cast<int>(cur.size())) {
      cur.erase(cur.begin() + ide.curC);
    } else if (ide.curR + 1 < static_cast<int>(L.size())) {
      cur += L[static_cast<size_t>(ide.curR) + 1];
      L.erase(L.begin() + ide.curR + 1);     // join the next line up
      ideMarkErase(ide, ide.curR + 1, 1);    // its pin rides out
    }
  }
  if (k.ctrlD) {                             // duplicate — the cursor line
                                             // alone, or EVERY line the
                                             // selection spans (the copy
                                             // carries the selection with it)
    const auto selD = ideSelRange(ide);
    if (selD && (*selD)[2] > (*selD)[0]) {
      const int r0 = (*selD)[0], r1 = (*selD)[2];
      const int count = r1 - r0 + 1;
      const std::vector<std::string> copy(L.begin() + r0, L.begin() + r1 + 1);
      L.insert(L.begin() + r1 + 1, copy.begin(), copy.end());
      ideMarkShift(ide, r1 + 1, count);      // pins beneath the copy slide
      ide.curR += count;
      if (ide.anchorR >= 0) ide.anchorR += count;   // the selection rides
    } else {
      // copy BEFORE inserting: the insert may reallocate the buffer
      const std::string cur = L[static_cast<size_t>(ide.curR)];
      L.insert(L.begin() + ide.curR + 1, cur);
      ideMarkShift(ide, ide.curR + 1, 1);    // pins beneath the copy slide
      ++ide.curR;                            // the copy takes your place
    }
  }
  if (k.delWord) {                           // ctrl+w: eat the word behind you
    std::string& cur = L[static_cast<size_t>(ide.curR)];
    int from = ide.curC;
    while (from > 0 && (cur[static_cast<size_t>(from) - 1] == ' ' ||
                        cur[static_cast<size_t>(from) - 1] == '\t'))
      --from;                                // the gap counts as part of it
    if (from > 0 && !ideWordChar(cur[static_cast<size_t>(from) - 1]))
      while (from > 0 && !ideWordChar(cur[static_cast<size_t>(from) - 1]) &&
             cur[static_cast<size_t>(from) - 1] != ' ' &&
             cur[static_cast<size_t>(from) - 1] != '\t')
        --from;                              // punctuation runs as one bite
    else
      while (from > 0 && ideWordChar(cur[static_cast<size_t>(from) - 1])) --from;
    if (from < ide.curC) {
      cur.erase(static_cast<size_t>(from),
                static_cast<size_t>(ide.curC - from));
      ide.curC = from;
    }
  }
  if (k.delWordFwd) {                        // ctrl+del: eat the word ahead
    // re-fetch: earlier edits may have reallocated the buffer
    std::string& cur = L[static_cast<size_t>(ide.curR)];
    int to = ide.curC;
    while (to < static_cast<int>(cur.size()) &&
           (cur[static_cast<size_t>(to)] == ' ' ||
            cur[static_cast<size_t>(to)] == '\t'))
      ++to;                                  // the gap counts as part of it
    if (to < static_cast<int>(cur.size()) &&
        !ideWordChar(cur[static_cast<size_t>(to)]))
      while (to < static_cast<int>(cur.size()) &&
             !ideWordChar(cur[static_cast<size_t>(to)]) &&
             cur[static_cast<size_t>(to)] != ' ' &&
             cur[static_cast<size_t>(to)] != '\t')
        ++to;                                // a punctuation run as one bite
    else
      while (to < static_cast<int>(cur.size()) &&
             ideWordChar(cur[static_cast<size_t>(to)]))
        ++to;
    if (to > ide.curC)
      cur.erase(static_cast<size_t>(ide.curC),
                static_cast<size_t>(to - ide.curC));
  }
  if (k.comment) {                           // ctrl+/: the line talks or hushes
                                             // — across a selection, EVERY
                                             // touched line talks at once
    const auto sel = ideSelRange(ide);
    if (sel && (*sel)[2] > (*sel)[0]) {
      const int r0 = (*sel)[0], r1 = (*sel)[2];
      const std::string pre = ideCommentFor(ide.path);
      const std::string bare = pre.substr(0, pre.size() - 1);
      bool strip = false;                    // the first talking line decides:
      for (int r = r0; r <= r1 && !strip; ++r) {
        const size_t first = L[static_cast<size_t>(r)].find_first_not_of(" \t");
        if (first == std::string::npos) continue;
        strip = L[static_cast<size_t>(r)].compare(first, bare.size(), bare) == 0;
        break;
      }
      for (int r = r0; r <= r1; ++r) {
        std::string& l = L[static_cast<size_t>(r)];
        const size_t first = l.find_first_not_of(" \t");
        if (strip) {
          if (first == std::string::npos ||
              l.compare(first, bare.size(), bare) != 0)
            continue;                        // only real comments strip
          size_t cut = first + bare.size();
          if (cut < l.size() && l[cut] == ' ') ++cut;
          l.erase(first, cut - first);
        } else {
          const size_t at = first == std::string::npos ? l.size() : first;
          l.insert(l.begin() + static_cast<long>(at), pre.begin(), pre.end());
        }
      }
      ide.curR = (*sel)[2];                  // rest at the range's end
      ide.curC = static_cast<int>(L[static_cast<size_t>(ide.curR)].size());
      ideSelClear(ide);
    } else {
      ideSelClear(ide);
      // re-fetch: earlier edits may have reallocated the buffer
      std::string& cur = L[static_cast<size_t>(ide.curR)];
      const std::string pre = ideCommentFor(ide.path);   // e.g. "# " or "// "
      const std::string bare = pre.substr(0, pre.size() - 1);   // "#"
      const size_t first = cur.find_first_not_of(" \t");
      if (first != std::string::npos &&
          cur.compare(first, bare.size(), bare) == 0) {
        // already a comment: strip the bare prefix and one space if it follows
        size_t cut = first + bare.size();
        if (cut < cur.size() && cur[cut] == ' ') ++cut;
        const int removed = static_cast<int>(cut - first);
        cur.erase(first, removed);
        if (ide.curC > static_cast<int>(first))
          ide.curC = std::max(static_cast<int>(first), ide.curC - removed);
      } else {
        // plain code: the prefix lands after the leading whitespace
        const size_t at = first == std::string::npos ? cur.size() : first;
        cur.insert(cur.begin() + static_cast<long>(at), pre.begin(), pre.end());
        ide.curC += static_cast<int>(pre.size());
      }
    }
    ide.dirty = true;                        // the game hears about it
    ide.idle = 0;
  }

  // ── the fresh slate: ctrl+l wipes the console's noise — game spam,
  // stale engine notes — so the next traceback can be read at a
  // glance. A look at the console's furniture, never an edit: the
  // document never hears about it, nothing dirties, nothing undoes.
  if (k.ctrlL) {
    ide.console.clear();
    ide.console.push_back(
        "engine: the console is fresh — ctrl+r replays your game");
  }

  // ── undo / redo: the second chance, one keystroke away — and the
  // receipt names WHAT moved, never a blind count
  if (k.ctrlZ) {
    if (ideUndo(ide)) {
      ide.dirty = true;                      // the game re-runs on the restored code
      ide.idle = 0;
      ide.console.push_back(ideUndoReceipt(ide));
    } else {
      ide.console.push_back("engine: nothing to undo");
    }
  }
  if (k.ctrlY) {
    if (ideRedo(ide)) {
      ide.dirty = true;
      ide.idle = 0;
      ide.console.push_back(ideRedoReceipt(ide));
    } else {
      ide.console.push_back("engine: nothing to redo");
    }
  }

  ideClamp(ide);
}

} // namespace dxn3
