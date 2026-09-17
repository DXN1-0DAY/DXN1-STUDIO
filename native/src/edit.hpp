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
#include <map>
#include <optional>
#include <charconv>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <random>
#include <sstream>
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
  bool jumpBack = false, jumpFwd = false;      // IDE: the jumps' walker —
                                // ctrl+o / alt+← into the past, alt+→ out
  bool ctrlL = false;                          // IDE: clear the console
  bool ctrlF = false;                          // IDE: find in the file
  bool ctrlD = false;                          // IDE: duplicate this line
  bool delWord = false;                        // IDE: ctrl+w — eat the word behind the cursor
  bool wLeft = false, wRight = false;          // IDE: ctrl+←/→ — hop word by word
  bool delWordFwd = false;                     // IDE: ctrl+del — eat the word ahead
  bool comment = false;                        // IDE: ctrl+/ — toggle the line's comment
  bool transpose = false;                      // IDE: ctrl+T — the two
                                               // neighbors trade places
  bool caseCycle = false;                      // IDE: ctrl+U — the word's
                                               // coat: whisper → SHOUT → Title
  bool docHome = false, docEnd = false;        // IDE: ctrl+home/end — the edges
  bool sUp = false, sDown = false;             // IDE: shift+↑/↓ — extend the selection
  bool altUp = false, altDown = false;         // IDE: alt+↑/↓ — the ride:
                                               // lift/drop without the bar
  bool sLeft = false, sRight = false;          // IDE: shift+←/→ — extend the selection
  bool sWLeft = false, sWRight = false;        // IDE: shift+ctrl+←/→ — select
                                               // word by word
  bool ctrlC = false, ctrlX = false, ctrlV = false;  // IDE: copy / cut / paste
  bool leap = false;                           // IDE: ctrl+\ — jump to the
                                               // partner bracket
  bool markToggle = false;                     // IDE: ctrl+F2 — plant/pull a pin
  bool markNext = false, markPrev = false;     // IDE: F2 / shift+F2 — leap
                                               // between pins
  bool findJump = false, findBack = false;     // IDE: F3 / shift+F3 — walk
                                               // the last query's hits
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
  std::vector<std::pair<int, int>> crew;       // the hands ride the restore
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
  // the welcome back: each file's last hand (row, col), remembered
  // when you leave it, restored when :open/:recent bring you back —
  // a reopen is a continuation, not a rewind.
  std::map<std::string, std::pair<int, int>> docCur;
  // the jumps ledger: the lines the hand LEAPT to — :goto, the pins'
  // F2 leap, the welcome back's landing. Standing is not jumping:
  // only a change of line plants. Cleared with the document (a jump
  // belongs to the doc it leapt in), capped, newest at the back.
  std::vector<int> jumps;
  // the walker's bookmark: where ctrl+o/alt+arrows stand in the
  // ledger — -1 means "now", wherever the last real leap left the
  // hand. A real leap kills the bookmark; walking only moves it.
  int jumpIx = -1;
  // the pins: bookmarks — lines you mark so the hand can leap back
  // (:mark plants, F2 leaps). Sorted, unique line positions that follow
  // insertions and cuts; a pin dies with its line.
  std::vector<int> marks;
  // the touched lines: every line the hand CHANGED since the page was
  // opened — :changes reads the census. Sorted, unique line positions
  // that follow the document's structure exactly the way the pins do
  // (a landing above slides a touch down, a cut carries its touches
  // out, a touched line dies with its line); undo does NOT un-touch —
  // the session's history is a fact — but it clamps the survivors to
  // the restored document. Cleared when the page opens (a fresh read
  // is a clean page) — including :fresh, whose truth is the disk's.
  std::vector<int> touched;
  // the drift: the page lines the last :diff heard disagreeing with
  // the disk — sorted, unique, 0-based. The map rail wears them amber
  // until :w speaks them to the disk (or the page reopens). The
  // census's own memory, never edited by it.
  std::vector<int> drift;
  // the crew: extra hands — every one stands where a cursor stands, and
  // the four edit verbs (typing, backspace, enter, forward delete) speak
  // through EVERY hand at once. Sorted, unique, the primary hand
  // (curR, curC) never listed. A transient crew: any frame that is not
  // one of the four verbs (movement, a click, esc, a command) dissolves
  // it back to the single hand; :crew plants it, a bare :crew bows out.
  std::vector<std::pair<int, int>> crew;
  // the minimap: a compressed map of the whole document riding the
  // editor pane's right edge (drawn only when the terminal has room;
  // :minimap toggles it)
  bool minimap = true;
  // zen: the console rail hides and the body breathes — two more rows
  // of code. The searchlight still gets its row when it is up; receipts
  // gather silently until the quiet ends. :zen toggles.
  bool zen = false;
  // where the quiet began: the console's size when zen entered, so the
  // wake can count (and replay) everything gathered in the dark. The
  // entering line itself counts — it was never shown either.
  size_t zenSince = 0;
  // relative line numbers: the gutter counts the distance from the
  // hand (the vim way) and the hand's own line keeps its true name.
  // :relnum toggles; the absolutes always come back.
  bool relnum = false;
  // the fold: soft-wrap — a long line breaks into the pane's width at
  // the last space or hyphen that fits (a word longer than the pane
  // takes the honest cut; code's compound names part at the dash).
  // :wrap toggles. While the fold speaks, the horizontal slide sleeps
  // (nothing is left to slide past) and `top` counts VISUAL rows
  // through the wrap's layout — built fresh every draw, O(the
  // document's bytes), no stamps, no stale caches.
  bool wrap = false;
  // the pane's width the last draw built the fold's layout for (0 =
  // never drawn) — the eye's walk (visual ↑/↓) rebuilds the layout
  // from it, one frame stale at worst, so the keys speak the SAME
  // geometry the paint just spoke.
  int lastTextW = 0;
  // the macro register: the verb lines recorded this session (:record
  // toggles the recorder, :macro replays the register through the SAME
  // dispatch the bar speaks). A session fact like the census — the
  // register survives opens and reloads; :record's start clears it.
  std::vector<std::string> macro;
  bool recording = false;
  // the wardrobe: which coat the editor wears — an index into
  // ideThemes(). :theme switches (and remembers, via
  // ideThemeStore/ideThemeRecall); 0 is the house coat, dxn.
  int themeIx = 0;
};

// ── the wardrobe: the editor's coats ─────────────────────────────────
// A theme is four code voices (base, comment, string, keyword — the
// voices drawCodeLine speaks) plus the two chrome washes (pane, sel).
// Six ship inside; :theme wears one by name, unique prefix or 1-based
// index, and the choice survives the night in $HOME/.dxn3-theme.
struct Theme {
  std::string name;                    // 2.0: user coats need owning names
  RGB base, comment, str, kw;
  RGB paneBg, selBg;
};

inline std::vector<Theme>& ideThemes() {   // mutable: :theme 2.0 appends
  static std::vector<Theme> kThemes = {    // your coats from .dxn3-themes
      {"dxn",         rgb(226, 232, 240), rgb(96, 104, 126),  rgb(250, 204, 21),
       rgb(167, 139, 250), rgb(16, 12, 30),    rgb(30, 22, 52)},
      {"dracula",     rgb(248, 248, 242), rgb(98, 114, 164),  rgb(241, 250, 140),
       rgb(255, 121, 198), rgb(40, 42, 54),    rgb(68, 69, 90)},
      {"gruvbox",     rgb(235, 219, 178), rgb(146, 131, 116), rgb(184, 187, 38),
       rgb(251, 73, 52),   rgb(40, 40, 40),    rgb(60, 56, 54)},
      {"nord",        rgb(236, 239, 244), rgb(97, 110, 136),  rgb(163, 190, 140),
       rgb(136, 192, 208), rgb(46, 52, 64),    rgb(59, 66, 82)},
      {"solar-dark",  rgb(147, 161, 161), rgb(88, 110, 117),  rgb(181, 137, 0),
       rgb(38, 139, 210),  rgb(0, 43, 54),     rgb(7, 54, 66)},
      {"solar-light", rgb(101, 123, 131), rgb(147, 161, 161), rgb(181, 137, 0),
       rgb(38, 139, 210),  rgb(253, 246, 227), rgb(238, 232, 213)},
  };
  return kThemes;
}

constexpr size_t kThemeBuiltinCount = 6;    // the house's coats, untouchable

// ── the wardrobe 2.0: YOUR coats ────────────────────────────────────
// A themes file lists one coat per line, seven ':'-joined fields:
//   name:base:comment:string:keyword:pane:sel
// Each color speaks decimal ("226,232,240") or hex ("#e2e8f0" or
// "e2e8f0"). Blank lines and #comments skip. A coat wearing a SHIPPED
// name is refused (the six built-ins are the house's, not yours);
// redefining one of YOUR earlier coats replaces it in place.
inline bool ideThemeParseRGB(const std::string& s, RGB& out) {
  std::string t = s;
  if (!t.empty() && t.front() == '#') t.erase(0, 1);
  if (t.empty()) return false;
  auto hexv = [](char c) -> int {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
  };
  if (t.size() == 6 &&
      t.find_first_not_of("0123456789abcdefABCDEF") == std::string::npos) {
    RGB v = 0;
    for (char c : t) v = (v << 4) | RGB(hexv(c));
    out = v;
    return true;
  }
  int comp[3];
  int got = 0;
  size_t pos = 0;
  while (got < 3) {
    const size_t comma = t.find(',', pos);
    std::string part = (comma == std::string::npos)
                           ? t.substr(pos)
                           : t.substr(pos, comma - pos);
    // spaces hide inside components too — " 30, 41, 59 " is one color
    const size_t pa = part.find_first_not_of(" \t");
    if (pa == std::string::npos) return false;
    part = part.substr(pa, part.find_last_not_of(" \t") - pa + 1);
    if (part.empty() ||
        part.find_first_not_of("0123456789") != std::string::npos)
      return false;
    const long v = std::strtol(part.c_str(), nullptr, 10);
    if (v < 0 || v > 255) return false;
    comp[got++] = static_cast<int>(v);
    if (comma == std::string::npos) break;
    pos = comma + 1;
  }
  if (got != 3) return false;
  out = rgb(static_cast<std::uint8_t>(comp[0]),
            static_cast<std::uint8_t>(comp[1]),
            static_cast<std::uint8_t>(comp[2]));
  return true;
}

// adopt one coat from seven parsed fields; returns nullptr on refusal
// (bad colors, an empty name, or a SHIPPED name). A name you already
// own is replaced in place — a wardrobe can correct itself.
inline const Theme* ideThemeAdopt1(const std::string (&f)[7]) {
  auto& ts = ideThemes();
  Theme t;
  t.name = f[0];
  RGB* slots[6] = {&t.base, &t.comment, &t.str, &t.kw, &t.paneBg, &t.selBg};
  for (int i = 0; i < 6; ++i)
    if (!ideThemeParseRGB(f[1 + i], *slots[i])) return nullptr;
  for (size_t i = 0; i < kThemeBuiltinCount && i < ts.size(); ++i)
    if (ts[i].name == t.name) return nullptr;      // the house's, not yours
  for (size_t i = kThemeBuiltinCount; i < ts.size(); ++i) {
    if (ts[i].name == t.name) {                    // re-tailoring your own
      ts[i] = std::move(t);
      return &ts[i];
    }
  }
  ts.push_back(std::move(t));
  return &ts.back();
}

// adopt every coat in a themes FILE. Missing file: silent zero — an
// empty wardrobe hook is not an error. Returns the adopted count.
inline int ideThemeLoadUserFile(const std::string& path) {
  std::ifstream f(path, std::ios::binary);
  if (!f) return 0;
  int n = 0;
  std::string line;
  while (std::getline(f, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    const size_t s0 = line.find_first_not_of(" \t");
    if (s0 == std::string::npos || line[s0] == '#') continue;
    std::string fld[7];
    size_t pos = 0;
    bool bad = false;
    for (int i = 0; i < 7; ++i) {
      const size_t c = line.find(':', pos);
      if (i < 6 && c == std::string::npos) { bad = true; break; }
      fld[i] = (i == 6) ? line.substr(pos)
                        : line.substr(pos, (c == std::string::npos ? line.size() : c) - pos);
      if (c == std::string::npos) break;
      pos = c + 1;
    }
    if (bad) continue;
    for (auto& x : fld) {
      const size_t a = x.find_first_not_of(" \t");
      const size_t b = x.find_last_not_of(" \t");
      x = (a == std::string::npos) ? "" : x.substr(a, b - a + 1);
    }
    if (fld[0].empty()) continue;
    if (ideThemeAdopt1(fld) != nullptr) ++n;
  }
  return n;
}

// :theme — wear a coat by name, unique prefix or 1-based index; no
// argument lists the wardrobe with the worn one marked (your coats
// say [user]). Returns the receipt line either way; a bad or
// ambiguous name reports through *err instead and the coat does not
// change.
inline std::string ideThemeSet(IdeState& ide, const std::string& arg,
                               std::string* err = nullptr) {
  const auto& ts = ideThemes();
  if (arg.empty()) {
    std::string list;
    for (size_t i = 0; i < ts.size(); ++i) {
      if (!list.empty()) list += " · ";
      list += ts[i].name;
      if (static_cast<int>(i) == ide.themeIx) list += " [worn]";
      if (i >= kThemeBuiltinCount) list += " [user]";
    }
    return list;
  }
  int pick = -1;
  if (arg.find_first_not_of("0123456789") == std::string::npos) {
    const int n = std::atoi(arg.c_str());
    if (n >= 1 && n <= static_cast<int>(ts.size())) pick = n - 1;
  } else {
    for (size_t i = 0; i < ts.size(); ++i)
      if (arg == ts[i].name) { pick = static_cast<int>(i); break; }
    if (pick < 0) {
      int hits = 0;
      for (size_t i = 0; i < ts.size(); ++i)
        if (arg == ts[i].name ||
            std::string_view(ts[i].name).rfind(arg, 0) == 0) {
          pick = static_cast<int>(i);
          ++hits;
        }
      if (hits > 1) {
        if (err) *err = "ambiguous theme '" + arg + "' — :theme lists them";
        return {};
      }
    }
  }
  if (pick < 0) {
    if (err) *err = "no such theme: " + arg + " — :theme lists them";
    return {};
  }
  ide.themeIx = pick;
  return "theme " + std::string(ts[pick].name) + " — the editor wears it";
}

// persistence — one line, the theme's name. An empty override means
// the default ($HOME/.dxn3-theme); a missing $HOME or an unwritable
// file is a silent no (a coat that will not keep is worn for the
// session only). Recall keeps the current coat on any silence.
inline std::string ideThemePath(const std::string& over = "") {
  if (!over.empty()) return over;
  const char* home = std::getenv("HOME");
  if (!home || !*home) return {};
  return std::string(home) + "/.dxn3-theme";
}

inline void ideThemeStore(const IdeState& ide, const std::string& over = "") {
  const std::string p = ideThemePath(over);
  if (p.empty()) return;
  std::ofstream f(p, std::ios::binary | std::ios::trunc);
  if (!f) return;
  f << ideThemes()[static_cast<size_t>(ide.themeIx) % ideThemes().size()].name
    << '\n';
}

inline void ideThemeRecall(IdeState& ide, const std::string& over = "") {
  const std::string p = ideThemePath(over);
  if (p.empty()) return;
  std::ifstream f(p, std::ios::binary);
  if (!f) return;
  std::string line;
  if (!std::getline(f, line)) return;
  while (!line.empty() && (line.back() == '\n' || line.back() == '\r'))
    line.pop_back();
  std::string err;
  ideThemeSet(ide, line, &err);            // silence on garbage: keep dxn
}

// ── the keepsake: the editor's habits survive the night ────────────
// One line in $HOME/.dxn3-settings — "ruler=1 minimap=0 zen=0
// relnum=1 wrap=0" — the five toggles as you left them. Toggling any
// of :ruler :minimap :zen :relnum :wrap saves the whole set; boot
// recalls it. Garbage on the line (or a missing file) changes
// nothing: the defaults stand, and a half-known line only wears the
// switches it actually names.
inline std::string ideSettingsPath(const std::string& over = "") {
  if (!over.empty()) return over;
  const char* home = std::getenv("HOME");
  if (!home || !*home) return {};
  return std::string(home) + "/.dxn3-settings";
}

inline void ideSettingsStore(const IdeState& ide, const std::string& over = "") {
  const std::string p = ideSettingsPath(over);
  if (p.empty()) return;
  std::ofstream f(p, std::ios::binary | std::ios::trunc);
  if (!f) return;
  f << "ruler=" << (ide.ruler ? 1 : 0) << " minimap=" << (ide.minimap ? 1 : 0)
    << " zen=" << (ide.zen ? 1 : 0) << " relnum=" << (ide.relnum ? 1 : 0)
    << " wrap=" << (ide.wrap ? 1 : 0) << '\n';
}

inline void ideSettingsRecall(IdeState& ide, const std::string& over = "") {
  const std::string p = ideSettingsPath(over);
  if (p.empty()) return;
  std::ifstream f(p, std::ios::binary);
  if (!f) return;
  std::string line;
  if (!std::getline(f, line)) return;
  std::istringstream in(line);
  std::string tok;
  while (in >> tok) {
    const size_t eq = tok.find('=');
    if (eq == std::string::npos || eq == 0 || eq + 1 >= tok.size()) continue;
    const std::string key = tok.substr(0, eq);
    const std::string val = tok.substr(eq + 1);
    if (val != "0" && val != "1") continue;      // honesty over guessing
    const bool on = (val == "1");
    if (key == "ruler") ide.ruler = on;
    else if (key == "minimap") ide.minimap = on;
    else if (key == "zen") ide.zen = on;
    else if (key == "relnum") ide.relnum = on;
    else if (key == "wrap") ide.wrap = on;
    // an unknown key is not a crime — it just changes nothing
  }
}

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

// ── the touched lines: where the hand has written ───────────────────
// The census :changes reads. The pins' structural law speaks here too:
// a landing above slides a touch down, a cut carries the touches it
// holds out (a touched line dies WITH its line), the world beneath a
// cut slides up, and a restored document clamps the survivors. A touch
// is a session fact — undo rewinds the document, never the record.
inline void ideTouch(IdeState& s, int line) {
  if (line < 0 || line >= static_cast<int>(s.lines.size())) return;
  const auto it = std::lower_bound(s.touched.begin(), s.touched.end(), line);
  if (it == s.touched.end() || *it != line) s.touched.insert(it, line);
}

// `count` lines land AT index `at`: touches beneath the landing slide
// down (the pins' shift law, verbatim)
inline void ideTouchShift(IdeState& s, int at, int count) {
  if (count <= 0) return;
  for (int& t : s.touched)
    if (t >= at) t += count;
}

// `count` lines leave at `at`: a touch inside the cut dies with its
// line, touches above the cut slide up (the pins' erase law, verbatim)
inline void ideTouchErase(IdeState& s, int at, int count) {
  if (count <= 0) return;
  const int end = at + count;
  s.touched.erase(std::remove_if(s.touched.begin(), s.touched.end(),
                                 [&](int t) { return t >= at && t < end; }),
                  s.touched.end());
  for (int& t : s.touched)
    if (t >= end) t -= count;
}

// out-of-range touches go — the restored document is the truth the
// census measures against
inline void ideTouchClamp(IdeState& s) {
  const int n = static_cast<int>(s.lines.size());
  s.touched.erase(std::remove_if(s.touched.begin(), s.touched.end(),
                                 [&](int t) { return t < 0 || t >= n; }),
                  s.touched.end());
}

inline void ideTouchClear(IdeState& s) { s.touched.clear(); }

// a look, never an edit: does a touch ride this line? The map rail's
// emerald tick asks this per row, the same way the pin's amber asks.
inline bool ideTouchHas(const IdeState& s, int line) {
  return line >= 0 &&
         std::binary_search(s.touched.begin(), s.touched.end(), line);
}

// the census, spoken: the touched lines ascending, capped, the deep
// count named when the cap hides some — "3 · 7 · 12 … 41", and the
// caller owns the prefix and the total. An empty page says nothing
// (the caller refuses kindly instead).
inline std::string ideTouchWhisper(const IdeState& s, size_t maxShow = 8) {
  if (s.touched.empty()) return "";
  std::string out;
  size_t shown = 0;
  for (const int t : s.touched) {
    if (shown == maxShow) break;
    out += (shown == 0 ? "" : " · ") + std::to_string(t + 1);
    ++shown;
  }
  if (s.touched.size() > maxShow)
    out += " … +" + std::to_string(s.touched.size() - maxShow) + " deeper";
  return out;
}

// the cross-marked census: a touched line that is ALSO a pin wears the
// pin's diamond — :changes and :jumps speak one marking law, so a line
// you wrote AND nailed down reads "7◆" in both listings. `marks` rides
// the pins' own invariant (sorted, unique — ide.marks always is).
inline std::string ideTouchWhisper(const IdeState& s,
                                   const std::vector<int>& marks,
                                   size_t maxShow = 8) {
  if (s.touched.empty()) return "";
  const auto pinned = [&](int line) {
    return std::binary_search(marks.begin(), marks.end(), line);
  };
  std::string out;
  size_t shown = 0;
  for (const int t : s.touched) {
    if (shown == maxShow) break;
    out += (shown == 0 ? "" : " · ") + std::to_string(t + 1);
    if (pinned(t)) out += "◆";
    ++shown;
  }
  if (s.touched.size() > maxShow)
    out += " … +" + std::to_string(s.touched.size() - maxShow) + " deeper";
  return out;
}

// the census's question: WHICH touched lines speak the word? The
// find's case law answers — case-honest when the searchlight is
// strict, the beginner way (case sleeps) when not. One law, two
// windows: the counting is the query's, the SET is the census's.
// A look, never an edit.
inline std::vector<int> ideChangesAsk(const IdeState& s,
                                      const std::string& w) {
  std::vector<int> matches;
  if (w.empty()) return matches;
  auto lower = [](std::string x) {
    for (char& c : x)
      c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return x;
  };
  const std::string needle = s.findCase ? w : lower(w);
  for (const int t : s.touched) {
    const std::string hay = s.findCase
                                ? s.lines[static_cast<size_t>(t)]
                                : lower(s.lines[static_cast<size_t>(t)]);
    if (hay.find(needle) != std::string::npos) matches.push_back(t);
  }
  return matches;
}

// ── the diff census: the page against the disk, one law ────────────
// A look, never an edit. The classic LCS speaks an edit script in
// three voices — lines the page ADDS, lines the page REMOVES, and a
// removal standing beside an addition in the same breath, which is
// one honest CHANGE. Line numbers speak as the gutter does (1-based):
// additions and changes point at the PAGE's lines, a removal at
// where the line once stood on the DISK. A bed too big to think
// refuses honestly.
struct IdeDiffReport {
  int added = 0, changed = 0, removed = 0;
  std::vector<int> addedAt, changedAt, removedAt;
  bool same() const { return added == 0 && changed == 0 && removed == 0; }
};

inline std::optional<IdeDiffReport>
ideDiffCensus(const std::vector<std::string>& disk,
              const std::vector<std::string>& page) {
  const int n = static_cast<int>(disk.size());
  const int m = static_cast<int>(page.size());
  if (static_cast<long long>(n) * static_cast<long long>(m) > 4000000LL)
    return std::nullopt;                     // a bed too big: refuse
  std::vector<std::vector<int>> lcs(
      static_cast<size_t>(n) + 1,
      std::vector<int>(static_cast<size_t>(m) + 1, 0));
  for (int i = n - 1; i >= 0; --i)
    for (int j = m - 1; j >= 0; --j)
      lcs[static_cast<size_t>(i)][static_cast<size_t>(j)] =
          disk[static_cast<size_t>(i)] == page[static_cast<size_t>(j)]
              ? lcs[static_cast<size_t>(i + 1)][static_cast<size_t>(j + 1)] + 1
              : std::max(lcs[static_cast<size_t>(i + 1)][static_cast<size_t>(j)],
                         lcs[static_cast<size_t>(i)][static_cast<size_t>(j + 1)]);
  struct Op { char kind; int a, b; };        // 'k'eep, 'a'dd, 'd'rop
  std::vector<Op> script;
  int i = 0, j = 0;
  while (i < n && j < m) {
    if (disk[static_cast<size_t>(i)] == page[static_cast<size_t>(j)]) {
      script.push_back({'k', i, j});
      ++i;
      ++j;
    } else if (lcs[static_cast<size_t>(i + 1)][static_cast<size_t>(j)] >=
               lcs[static_cast<size_t>(i)][static_cast<size_t>(j + 1)]) {
      script.push_back({'d', i, j});
      ++i;
    } else {
      script.push_back({'a', i, j});
      ++j;
    }
  }
  while (i < n) { script.push_back({'d', i, j}); ++i; }
  while (j < m) { script.push_back({'a', i, j}); ++j; }
  IdeDiffReport rep;
  size_t k = 0;
  while (k < script.size()) {
    if (script[k].kind == 'k') { ++k; continue; }
    const size_t b0 = k;                     // a mixed block: adds and
    while (k < script.size() && script[k].kind != 'k') ++k;  // drops in
                                             // any order, no keep between
    std::vector<int> aPages, dDisks;
    for (size_t t = b0; t < k; ++t) {
      if (script[t].kind == 'a') aPages.push_back(script[t].b + 1);
      else dDisks.push_back(script[t].a + 1);
    }
    const int pairs = static_cast<int>(
        std::min(aPages.size(), dDisks.size()));
    for (int p = 0; p < pairs; ++p)          // a drop beside an add is a
      rep.changedAt.push_back(aPages[static_cast<size_t>(p)]);  // change
    for (size_t p = static_cast<size_t>(pairs); p < dDisks.size(); ++p)
      rep.removedAt.push_back(dDisks[p]);
    for (size_t p = static_cast<size_t>(pairs); p < aPages.size(); ++p)
      rep.addedAt.push_back(aPages[p]);
  }
  rep.added = static_cast<int>(rep.addedAt.size());
  rep.changed = static_cast<int>(rep.changedAt.size());
  rep.removed = static_cast<int>(rep.removedAt.size());
  return rep;
}

// the drift's law: :diff stores what it heard (the page lines that
// disagree — additions and changes; a removal no longer stands on the
// page, so it cannot wear a tick), :w clears it (the disk heard), a
// fresh page clears it. Sorted, unique — the rail's per-row ask is a
// binary search, the same as the touch's.
inline void ideDriftStore(IdeState& s, const IdeDiffReport& rep) {
  s.drift.clear();
  for (const int t : rep.addedAt) s.drift.push_back(t - 1);
  for (const int t : rep.changedAt) s.drift.push_back(t - 1);
  std::sort(s.drift.begin(), s.drift.end());
  s.drift.erase(std::unique(s.drift.begin(), s.drift.end()), s.drift.end());
}
inline void ideDriftClear(IdeState& s) { s.drift.clear(); }
inline bool ideDriftHas(const IdeState& s, int line) {
  return line >= 0 &&
         std::binary_search(s.drift.begin(), s.drift.end(), line);
}

// the selection goes first: the range is cut, the cursor collapses to
// its start, the anchor clears. False when there was nothing selected.
inline bool ideSelDelete(IdeState& s) {
  const auto sel = ideSelRange(s);
  if (!sel) return false;
  const auto [r0, c0, r1, c1] = *sel;
  ideTouch(s, r0);                           // the seam line is touched —
                                             // it kept (or received) the tail
  if (r0 == r1) {
    std::string& l = s.lines[static_cast<size_t>(r0)];
    l.erase(static_cast<size_t>(c0), static_cast<size_t>(c1 - c0));
  } else {
    std::string& first = s.lines[static_cast<size_t>(r0)];
    const std::string tail = s.lines[static_cast<size_t>(r1)].substr(static_cast<size_t>(c1));
    first.resize(static_cast<size_t>(c0));
    first += tail;
    s.lines.erase(s.lines.begin() + r0 + 1, s.lines.begin() + r1 + 1);
    ideMarkErase(s, r0 + 1, r1 - r0);        // the cut's pins ride out
    ideTouchErase(s, r0 + 1, r1 - r0);       // so do the cut's touches
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
  s.undo.push_back({s.lines, s.curR, s.curC, s.marks, s.crew, std::move(what)});
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
    ideTouchErase(s, s.curR, 1);               // its touch dies with it
    s.curC = 0;
  } else {
    ideSelDelete(s);                           // the bed's touches speak there
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
    ideTouchShift(s, at, static_cast<int>(s.clip.size()));
    for (int r = at;
         r < at + static_cast<int>(s.clip.size()); ++r)
      ideTouch(s, r);                          // the paste's bed is touched
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
    if (s.clip.size() > 1)                     // the census rides the splice
      ideTouchShift(s, s.curR + 1,
                    static_cast<int>(s.clip.size()) - 1);
    for (size_t i = 1; i < s.clip.size(); ++i)
      L.insert(L.begin() + s.curR + static_cast<long>(i), s.clip[i]);
    L[static_cast<size_t>(s.curR) + s.clip.size() - 1] += tail;
    for (size_t i = 0; i < s.clip.size(); ++i)
      ideTouch(s, s.curR + static_cast<int>(i));  // every fed line touched
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

// ── the whisper's clip law, ONE law for every completion ────────────
// recent, bm, the shelf and :open all join their entries with " · "
// and all end the line at the FIRST entry that does not fit the bar's
// honest width — never a cut word, never a half description. This is
// that law, once: returns true when the entry fit (and joins it),
// false when the whisper is full (and leaves it untouched).
inline bool whisperOffer(std::string& w, const std::string& entry,
                         size_t maxW) {
  const size_t need =
      w.empty() ? entry.size() : w.size() + 3 + entry.size();
  if (need > maxW) return false;
  w += w.empty() ? entry : " · " + entry;
  return true;
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
    if (!whisperOffer(w, entry, maxW)) break;
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
  s.redo.push_back({s.lines, s.curR, s.curC, s.marks, s.crew, s.undo.back().what});
  s.lines = std::move(s.undo.back().lines);
  s.curR = s.undo.back().curR;
  s.curC = s.undo.back().curC;
  s.marks = s.undo.back().marks;               // the pins walk back too
  s.crew = s.undo.back().crew;                 // the hands walk back too
  s.undo.pop_back();
  s.lastTyping = s.lastBack = false;
  ideSelClear(s);                    // the second chance drops the selection
  ideClamp(s);
  ideMarkClamp(s);                   // pins the restored document never had go
  ideTouchClamp(s);                  // touches survive the rewind — the
                                     // session's history is a fact — but
                                     // clamp to the restored page
  return true;
}

// step forward again; false when there is nothing to redo
inline bool ideRedo(IdeState& s) {
  if (s.redo.empty()) return false;
  s.undo.push_back({s.lines, s.curR, s.curC, s.marks, s.crew, s.redo.back().what});
  s.lines = std::move(s.redo.back().lines);
  s.curR = s.redo.back().curR;
  s.curC = s.redo.back().curC;
  s.marks = s.redo.back().marks;               // the pins step forward too
  s.crew = s.redo.back().crew;                 // the hands step forward too
  s.redo.pop_back();
  s.lastTyping = s.lastBack = false;
  ideSelClear(s);
  ideClamp(s);
  ideMarkClamp(s);                   // pins the restored document never had go
  ideTouchClamp(s);                  // the census measures the restored page
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

// step to the next hit (enter / F3): the first hit STRICTLY after the
// hand, wrapping to the file's head; false when there is nothing. The
// strict law is one law for both stances — a hand standing ON a hit
// walks to the following one, and a hand standing BETWEEN hits lands
// on its next one (the old aim-then-step law skipped that first hit:
// the searchlight aimed at it, then enter stepped PAST it).
inline bool ideFindNext(IdeState& s) {
  if (s.findHits.empty()) return false;
  const int n = static_cast<int>(s.findHits.size());
  int pick = 0;                      // the wrap: the file's head
  for (int i = 0; i < n; ++i) {
    const auto& [r, c] = s.findHits[static_cast<size_t>(i)];
    if (r > s.curR || (r == s.curR && c > s.curC)) { pick = i; break; }
  }
  s.findSel = pick;
  const auto& [r, c] = s.findHits[static_cast<size_t>(pick)];
  s.curR = r;
  s.curC = c;
  ideSelClear(s);                    // the walk abandons any selection
  return true;
}

// step to the previous hit (shift+F3): the last hit STRICTLY before
// the hand, wrapping to the file's tail — the next's mirror, so the
// hunt walks honestly in both directions.
inline bool ideFindPrev(IdeState& s) {
  if (s.findHits.empty()) return false;
  const int n = static_cast<int>(s.findHits.size());
  int pick = n - 1;                  // the wrap: the file's tail
  for (int i = n - 1; i >= 0; --i) {
    const auto& [r, c] = s.findHits[static_cast<size_t>(i)];
    if (r < s.curR || (r == s.curR && c < s.curC)) { pick = i; break; }
  }
  s.findSel = pick;
  const auto& [r, c] = s.findHits[static_cast<size_t>(pick)];
  s.curR = r;
  s.curC = c;
  ideSelClear(s);
  return true;
}

// ── the second chance, listed (:hist) ───────────────────────────────
// one honest line: the undo ledger's names, NEWEST first, capped at
// maxNames with the true depth in the tail; the redo's head rides
// after the divider. Pure and selftested — the bar prints it.
inline std::string ideHistWhisper(const IdeState& s, size_t maxNames = 8) {
  if (s.undo.empty() && s.redo.empty()) return "";
  const size_t n = s.undo.size();
  // the depth LEADS — a long ledger clips from the right, and the
  // depth is the one truth that must survive the clip
  std::string out = "[" + std::to_string(n) + " step" +
                    (n == 1 ? "" : "s") + " back";
  if (!s.redo.empty()) out += " · redo: " + s.redo.back().what;
  out += "] ";
  for (size_t i = 0; i < n && i < maxNames; ++i) {
    if (i > 0) out += " · ";
    out += s.undo[n - 1 - i].what;
  }
  if (n > maxNames)
    out += " · … +" + std::to_string(n - maxNames) + " deeper";
  return out;
}

// ── the census, listed (:words) ─────────────────────────────────────
// the document's most-said words, counted and ranked. The laws:
// case is FORGIVEN (the beginner law — "The" and "the" are one word),
// punctuation is stripped from the EDGES only ("spawn", (spawn),
// spawn, and spawn, all count as spawn), the INSIDE is kept whole
// (gem-1 stays gem-1, on_hit stays on_hit), and ties take the
// alphabet so the order never wobbles. Pure and selftested — the bar
// prints it, capped at maxWords with the true tail.
inline std::string ideWordsWhisper(const IdeState& s, size_t maxWords = 6) {
  std::map<std::string, int> counts;
  auto stripEdges = [](const std::string& w) {
    size_t a = 0, b = w.size();
    while (a < b && std::ispunct(static_cast<unsigned char>(w[a]))) ++a;
    while (b > a && std::ispunct(static_cast<unsigned char>(w[b - 1]))) --b;
    return w.substr(a, b - a);
  };
  for (const auto& l : s.lines) {
    size_t i = 0;
    while (i < l.size()) {
      while (i < l.size() &&
             std::isspace(static_cast<unsigned char>(l[i]))) ++i;
      const size_t a = i;
      while (i < l.size() &&
             !std::isspace(static_cast<unsigned char>(l[i]))) ++i;
      if (i <= a) continue;
      std::string w = stripEdges(l.substr(a, i - a));
      if (w.empty()) continue;            // a pure-punctuation token says nothing
      for (char& c : w)
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
      ++counts[w];
    }
  }
  if (counts.empty()) return "";
  std::vector<std::pair<std::string, int>> ranked(counts.begin(), counts.end());
  std::sort(ranked.begin(), ranked.end(),
            [](const auto& x, const auto& y) {
              if (x.second != y.second) return x.second > y.second;
              return x.first < y.first;   // ties take the alphabet
            });
  std::string out;
  const size_t total = ranked.size();
  for (size_t i = 0; i < total && i < maxWords + 1; ++i) {
    if (i == maxWords) {
      out += " · … +" + std::to_string(total - maxWords) + " more word" +
             (total - maxWords == 1 ? "" : "s");
      break;
    }
    if (i > 0) out += " · ";
    out += ranked[i].first + "×" + std::to_string(ranked[i].second);
  }
  return out;
}

// ── the marker hunt, listed (:todo) ─────────────────────────────────
// the debts the document owes, named where they live: every line
// carrying TODO, FIXME, XXX or HACK (the honest uppercase markers —
// lowercase prose is not a promise), listed LINE-LED because a long
// census clips from the right and the line number is the one truth
// that must survive. Pure and selftested — the bar prints it.
inline std::string ideTodoWhisper(const IdeState& s, size_t maxTodos = 6) {
  static const char* markers[] = {"TODO", "FIXME", "XXX", "HACK"};
  auto trimmed = [](const std::string& l) {
    size_t a = 0, b = l.size();
    while (a < b && std::isspace(static_cast<unsigned char>(l[a]))) ++a;
    while (b > a && std::isspace(static_cast<unsigned char>(l[b - 1]))) --b;
    return l.substr(a, b - a);
  };
  std::vector<std::string> hits;
  for (int r = 0; r < static_cast<int>(s.lines.size()); ++r) {
    const std::string& l = s.lines[static_cast<size_t>(r)];
    bool marked = false;
    for (const char* m : markers)
      if (l.find(m) != std::string::npos) { marked = true; break; }
    if (!marked) continue;
    std::string what = trimmed(l);
    if (what.size() > 32) what = what.substr(0, 31) + "…";
    hits.push_back(std::to_string(r + 1) + ": " + what);
  }
  if (hits.empty()) return "";
  std::string out;
  for (size_t i = 0; i < hits.size() && i < maxTodos; ++i) {
    if (i > 0) out += " · ";
    out += hits[i];
  }
  if (hits.size() > maxTodos)
    out += " · … +" + std::to_string(hits.size() - maxTodos) +
           " deeper in the file";
  return out;
}

// ── the quiet's ledger: what zen gathered while the rail rested ─────
// When zen wakes, its gathered receipts deserve one honest word. The
// digest walks the console slice from `since` (where zen entered —
// the entering line counts, it was never shown either), trims each
// receipt, and joins the NEWEST three with " · " oldest first so the
// ledger reads chronologically. Kept is reported back; a quiet that
// gathered two or fewer leaves them where they lie (the two-row
// window already shows them). Pure and selftested.
inline std::string ideZenDigest(const std::vector<std::string>& console,
                                size_t since, size_t* keptOut = nullptr) {
  if (keptOut) *keptOut = 0;
  if (since >= console.size()) return "";
  const size_t kept = console.size() - since;
  if (keptOut) *keptOut = kept;
  if (kept <= 2) return "";    // the two-row window already shows them
  constexpr size_t kMaxShown = 3;
  auto trimmed = [](const std::string& l) {
    size_t a = 0, b = l.size();
    while (a < b && std::isspace(static_cast<unsigned char>(l[a]))) ++a;
    while (b > a && std::isspace(static_cast<unsigned char>(l[b - 1]))) --b;
    std::string out = l.substr(a, b - a);
    if (out.size() > 48) out = out.substr(0, 47) + "…";
    return out;
  };
  std::string out;
  size_t taken = 0;
  for (size_t i = console.size(); i-- > since;) {
    if (taken == kMaxShown) break;
    const std::string r = trimmed(console[i]);
    out = out.empty() ? r : (r + " · " + out);   // the older rides ahead
    ++taken;
  }
  if (kept > kMaxShown)
    out += " · … +" + std::to_string(kept - kMaxShown) +
           " more in the console";
  return out;
}

// ── the selection's own census ──────────────────────────────────────
// :stats on a selection speaks the SELECTION's truth first: the
// honest slice (the first line from c0, the last line to c1, the
// middle whole) counted the same way the document is. Pure and
// selftested.
struct IdeSelStats {
  int lines = 0;
  size_t words = 0, chars = 0;
};

inline IdeSelStats ideSelStats(const IdeState& s, const SelRange& sel) {
  const auto [r0, c0, r1, c1] = sel;
  IdeSelStats st;
  st.lines = r1 - r0 + 1;
  for (int r = r0; r <= r1 && r < static_cast<int>(s.lines.size()); ++r) {
    const std::string& l = s.lines[static_cast<size_t>(r)];
    const size_t a = (r == r0) ? static_cast<size_t>(std::max(0, c0)) : 0;
    const size_t b =
        (r == r1) ? static_cast<size_t>(std::min<int>(c1 + 1, l.size()))
                  : l.size();
    if (a >= b) continue;
    const std::string part = l.substr(a, b - a);
    st.chars += part.size();
    bool inWord = false;
    for (char c : part) {
      if (std::isspace(static_cast<unsigned char>(c))) inWord = false;
      else { if (!inWord) ++st.words; inWord = true; }
    }
  }
  return st;
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

// ── the soft wrap: the fold's one geometry table ────────────────────
// The editor's world is logical lines; the PANE paints visual rows.
// With the fold on, one logical line becomes one or more rows, broken
// at the last space or hyphen that fits; the fold OFF builds the
// identity — one line, one row — so every geometry law (the pager, the
// pointer, the wheel, the glows) speaks this ONE table in both worlds
// and no two laws ever disagree about where a byte lands.
struct IdeWrap {
  int rows = 0;                    // visual rows in the whole document
  std::vector<int> lineFirst;      // lineFirst[li] = the first visual
                                   // row of line li (size N + 1)
  std::vector<int> rowLine;        // rowLine[v] = the line row v belongs to
  std::vector<int> rowOff;         // rowOff[v] = the byte offset row v starts at
};

inline IdeWrap ideWrapBuild(const IdeState& s, int textW) {
  IdeWrap w;
  const int N = static_cast<int>(s.lines.size());
  w.lineFirst.assign(static_cast<size_t>(N) + 1, 0);
  const bool fold = s.wrap && textW >= 8;   // a sliver of a pane: identity
  for (int li = 0; li < N; ++li) {
    w.lineFirst[static_cast<size_t>(li)] =
        static_cast<int>(w.rowLine.size());
    const std::string& ln = s.lines[static_cast<size_t>(li)];
    const int len = static_cast<int>(ln.size());
    if (!fold || len <= textW) {
      w.rowLine.push_back(li);
      w.rowOff.push_back(0);
      continue;                              // the line paints one row
    }
    int off = 0;
    while (true) {
      w.rowLine.push_back(li);
      w.rowOff.push_back(off);
      if (off + textW >= len) break;         // the tail fits: last row
      int next = off + textW;                // the hard cut is the default
      for (int c = off + textW; c > off + 1; --c)
        if (ln[static_cast<size_t>(c) - 1] == ' ' ||
            ln[static_cast<size_t>(c) - 1] == '-') {
          next = c;                          // break AFTER the space or dash
          break;
        }
      off = next;
    }
  }
  w.lineFirst[static_cast<size_t>(N)] =
      static_cast<int>(w.rowLine.size());
  w.rows = static_cast<int>(w.rowLine.size());
  return w;
}

// the visual row that holds (li, col): the line's first row plus the
// segment that owns the byte — a binary search, no linear walks. The
// tail byte lands on the last row, a segment start lands on its own row.
inline int ideWrapRowOf(const IdeWrap& w, int li, int col) {
  const int n = static_cast<int>(w.lineFirst.size()) - 1;
  if (n <= 0) return 0;
  li = std::clamp(li, 0, n - 1);
  const int first = w.lineFirst[static_cast<size_t>(li)];
  const int last = w.lineFirst[static_cast<size_t>(li) + 1] - 1;
  if (first >= last) return first;           // one row: done
  int lo = first, hi = last;                 // the last row starting ≤ col
  while (lo < hi) {
    const int mid = (lo + hi + 1) / 2;
    if (w.rowOff[static_cast<size_t>(mid)] <= col) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

// ── the longest line: the fold's companion census ───────────────────
// :stats speaks it so a hand can see, before the fold even speaks,
// whether anything will fold (longest > the pane's width) — and by
// how much the document's worst offender offends. 0 for a document
// of empty lines; the length is BYTES, the same coin the fold spends.
inline int ideLongestLine(const IdeState& s) {
  int best = 0;
  for (const auto& l : s.lines)
    best = std::max(best, static_cast<int>(l.size()));
  return best;
}

// ── the eye's walk: visual ↑/↓ under the fold ───────────────────────
// With the fold speaking, up/down walk VISUAL rows — from a line's
// continuation row, up lands on the line's OWN head, not the line
// above — and the eye's column is kept, clamped to the landing row's
// honest width. Returns true when the visual law took the hand;
// false hands the move back to the caller's logical law (the fold
// asleep, a sliver of a pane, or a walk that would leave the
// document — the clamp rides the caller as always).
inline bool ideVisualMove(IdeState& s, int delta) {
  if (delta == 0 || !s.wrap || s.lastTextW < 8) return false;
  const IdeWrap w = ideWrapBuild(s, s.lastTextW);
  const int v = ideWrapRowOf(w, s.curR, s.curC);
  const int target = v + delta;
  if (target < 0 || target >= w.rows) return false;
  const int li = w.rowLine[static_cast<size_t>(target)];
  const int off = w.rowOff[static_cast<size_t>(target)];
  const int lineLen =
      static_cast<int>(s.lines[static_cast<size_t>(li)].size());
  const int lineLast = w.lineFirst[static_cast<size_t>(li) + 1] - 1;
  const int rowEnd = target < lineLast
                         ? w.rowOff[static_cast<size_t>(target) + 1]
                         : lineLen;          // the row's end (exclusive)
  const int maxCol = rowEnd >= lineLen ? lineLen : rowEnd - 1;
  const int want = off + (s.curC - w.rowOff[static_cast<size_t>(v)]);
  s.curR = li;
  s.curC = std::clamp(want, off, std::max(off, maxCol));
  return true;
}

// ── horizontal scroll: the cursor is always on screen ───────────────
// Long lines slide under the cursor instead of being chopped off at
// the pane's edge. hcol is the first visible column; it follows the
// cursor with a small margin and rests at 0 whenever the line fits.
inline void ideHscroll(IdeState& s, int textW) {
  if (s.wrap) {                              // the fold owns the width:
    s.hcol = 0;                              // nothing is left to slide
    return;                                  // past — the slide sleeps
  }
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
inline void ideScroll(IdeState& s, int delta, const IdeWrap* w = nullptr) {
  if (delta == 0) return;
  const int page = s.page > 0 ? s.page : 1;
  // the SAME max the draw clamps to (a full last page) — a disagreeing
  // max here made the top oscillate and the wheel die after one notch.
  // The fold's layout, when the caller hands it over, counts VISUAL
  // rows; the identity counts lines — one honest max either way.
  const int rows = w ? w->rows : static_cast<int>(s.lines.size());
  const int maxTop = std::max(0, rows - page);
  s.top = std::clamp(s.top + delta, 0, maxTop);
  if (w) {
    // the ride, in rows: a hand that would fall off the edge lands on
    // the line the view's edge now shows — the column is kept, the
    // clamp trims it honestly
    const int curV = ideWrapRowOf(*w, s.curR, s.curC);
    if (curV < s.top)
      s.curR = w->rowLine[static_cast<size_t>(s.top)];
    else if (curV >= s.top + page)
      s.curR = w->rowLine[static_cast<size_t>(s.top + page - 1)];
  } else {
    if (s.curR < s.top) s.curR = s.top;                    // rode past the top
    if (s.curR >= s.top + page) s.curR = s.top + page - 1; // …or the bottom
  }
  ideClamp(s);
  s.idle = 0;
}

// ── the swap: :s/old/new — the bed's bytes trade places ───────────
// Find & replace, the house way: EVERY byte-exact occurrence of old
// becomes new, on the selection's lines (or the hand's line alone —
// the sort family's bed law). The match is EXACT — the searchlight
// forgives case, the swap does not (a replace that guesses case
// rewrites what it was not asked to touch). new may be empty (a
// deletion) and may not carry a newline (one line at a time — the
// bed never grows). Only the lines that actually changed are
// touched; ONE restore point named "replace", taken only when
// something matched (a clean bed takes no phantom step); the hand
// rests at the bed's head; the selection lets go. Returns the count
// of replacements; 0 with no matches (or no bed).
inline int ideReplaceSel(IdeState& s, const std::string& oldStr,
                         const std::string& newStr, int* linesTouched) {
  if (oldStr.empty() || newStr.find('\n') != std::string::npos) return 0;
  int r0, r1;
  if (const auto sel = ideSelRange(s)) {
    r0 = (*sel)[0];
    r1 = (*sel)[2];
  } else {
    r0 = r1 = s.curR;                    // no selection: the hand's line
  }
  if (r1 < r0) return 0;
  // the dry pass: count BEFORE the snapshot — a clean bed takes no
  // phantom step (the trim's law)
  int made = 0, touchedLines = 0;
  for (int r = r0; r <= r1; ++r) {
    const std::string& l = s.lines[static_cast<size_t>(r)];
    for (size_t pos = 0;
         (pos = l.find(oldStr, pos)) != std::string::npos;
         pos += oldStr.size())
      ++made;
    if (l.find(oldStr) != std::string::npos) ++touchedLines;
  }
  if (made == 0) {
    if (linesTouched) *linesTouched = 0;
    return 0;                            // nothing matched, nothing moved
  }
  idePushUndo(s, "replace");             // the snapshot holds the old bytes
  for (int r = r0; r <= r1; ++r) {
    std::string& l = s.lines[static_cast<size_t>(r)];
    if (l.find(oldStr) == std::string::npos) continue;
    std::string out;
    out.reserve(l.size());
    size_t pos = 0;
    while (pos <= l.size()) {
      const size_t hit = l.find(oldStr, pos);
      if (hit == std::string::npos) {
        out += l.substr(pos);
        break;
      }
      out += l.substr(pos, hit - pos);
      out += newStr;
      pos = hit + oldStr.size();
    }
    l = std::move(out);
    ideTouch(s, r);                      // only the lines that changed
  }
  ideSelClear(s);
  s.curR = r0;                           // the hand rests at the bed's head
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  if (linesTouched) *linesTouched = touchedLines;
  return made;
}

// the swap's other face: :sa/old/new — the WHOLE document is the bed.
// The same exact-match law, spoken by the same ideReplaceSel: the bed
// is simply the biggest selection a document can hold. One undo step
// holds the whole take.
inline int ideReplaceAll(IdeState& s, const std::string& oldStr,
                         const std::string& newStr, int* linesTouched) {
  if (s.lines.empty()) return 0;
  const int keepR = s.curR, keepC = s.curC;
  const int keepA = s.anchorR, keepAC = s.anchorC;
  s.anchorR = 0;
  s.anchorC = 0;
  s.curR = static_cast<int>(s.lines.size()) - 1;
  s.curC = static_cast<int>(s.lines.back().size());
  const int made = ideReplaceSel(s, oldStr, newStr, linesTouched);
  if (made == 0) {                         // a clean bed: nothing moved,
    s.curR = keepR;                        // the hand goes home untouched
    s.curC = keepC;
    s.anchorR = keepA;
    s.anchorC = keepAC;
  }
  return made;
}

// ── the rebalance: the view centers on the hand ────────────────────
// :center — z. in vim's tongue. The hand rides the viewport's middle
// (the SAME page the draw and the wheel use), clamped to the doc's
// honest edges: a hand near the top keeps the top, a hand near the
// bottom keeps the bottom — the middle is a preference, the document
// is the law. A look, never an edit: nothing dirties, nothing undoes.
inline void ideCenter(IdeState& s, const IdeWrap* w = nullptr) {
  const int page = s.page > 0 ? s.page : 1;
  // the hand rides the middle of the VISUAL rows under the fold (its
  // own row, not its line's first) — the identity keeps the line law
  const int rows = w ? w->rows : static_cast<int>(s.lines.size());
  const int hand = w ? ideWrapRowOf(*w, s.curR, s.curC) : s.curR;
  const int maxTop = std::max(0, rows - page);
  s.top = std::clamp(hand - page / 2, 0, maxTop);
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
inline void ideDragAutoScroll(IdeState& s, int edge, double dt,
                              const IdeWrap* w = nullptr) {
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
  ideScroll(s, edge * steps, w);               // the ride contract applies
  // the hand IS the edge: parked on the bottom row it takes each line
  // the slide reveals — the selection grows from the anchor, exactly
  // like every desktop editor's autoscroll. The fold speaks rows: the
  // edge's visual row names its line, the column kept.
  const int page = s.page > 0 ? s.page : 1;
  if (w) {
    const int v = std::clamp(edge > 0 ? s.top + page - 1 : s.top,
                             0, std::max(0, w->rows - 1));
    s.curR = w->rowLine[static_cast<size_t>(v)];
  } else {
    s.curR = edge > 0 ? s.top + page - 1 : s.top;
  }
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

// ── the welcome back: where the hand last stood in a document ───────
// Leaving a file plants its hand in the map; :open/:recent look it up
// on the way in. The LANDING law clamps the remembered hand to the
// document it lands in — a file that shrank since the last visit
// keeps the hand inside (the row into the last line, the column into
// that line's width), never off the page, and a file that vanished
// to zero bytes holds the hand at the top (an empty page indexes
// nothing). Pure and selftested.
using DocCur = std::pair<int, int>;            // (row, col), 0-based

inline void ideDocCurRemember(std::map<std::string, DocCur>& m,
                              const std::string& path, int r, int c) {
  if (path.empty()) return;                    // no name, no memory
  m[path] = DocCur{r, c};
}

inline std::optional<DocCur> ideDocCurLookup(
    const std::map<std::string, DocCur>& m, const std::string& path) {
  const auto it = m.find(path);
  if (it == m.end()) return std::nullopt;
  return it->second;
}

inline DocCur ideDocCurLand(const std::vector<std::string>& lines,
                            const DocCur& hand) {
  if (lines.empty()) return DocCur{0, 0};      // an empty page holds the top
  const int r =
      std::max(0, std::min(hand.first,
                           static_cast<int>(lines.size()) - 1));
  const int c = std::max(
      0, std::min(hand.second,
                  static_cast<int>(lines[static_cast<size_t>(r)].size())));
  return DocCur{r, c};
}

// ── the jumps ledger: where the hand has leapt ──────────────────────
// A jump is a CHANGE of line (:goto, the pins' F2 leap, the welcome
// back's landing) — standing on the line you already stand on plants
// nothing. Newest at the back, capped at 32: the oldest leap falls
// off so the ledger stays a memory, not an archive. Pure, selftested.
inline void ideJumpPush(std::vector<int>& jumps, int line) {
  if (line < 0) return;                        // no wild lines
  if (!jumps.empty() && jumps.back() == line) return;  // a stand, not a leap
  jumps.push_back(line);
  if (jumps.size() > 32) jumps.erase(jumps.begin());
}

// the stateful plant: a real leap puts the walker back at "now" —
// the bookmark dies with the leap that made it.
inline void ideJumpPush(IdeState& s, int line) {
  ideJumpPush(s.jumps, line);
  s.jumpIx = -1;
}

// the walker: one step into the ledger's past (or back out of it).
// Walking is NOT leaping — nothing plants, the ledger only moves its
// bookmark. Returns the 0-based line to land on, -1 when the edge
// refuses (an empty ledger, the first jump, or the newest already
// under the hand). Pure, selftested.
inline int ideJumpWalkBack(IdeState& s) {
  if (s.jumps.empty()) return -1;
  int ix = s.jumpIx < 0 ? static_cast<int>(s.jumps.size()) - 1 : s.jumpIx;
  if (ix <= 0) return -1;              // the first jump — nothing behind
  s.jumpIx = ix - 1;
  return s.jumps[s.jumpIx];
}

inline int ideJumpWalkFwd(IdeState& s) {
  if (s.jumps.empty() || s.jumpIx < 0) return -1;  // at now — nothing ahead
  if (s.jumpIx >= static_cast<int>(s.jumps.size()) - 1) return -1;
  s.jumpIx += 1;
  return s.jumps[s.jumpIx];
}

// the ledger whispers: the leaps, NEWEST first, the freshest named
// "now" (it answers "where have I been?"), the lines in their
// 1-based names, capped at 8 with "… +N deeper". Empty says nothing —
// the caller refuses honestly.
inline std::string ideJumpsWhisper(const std::vector<int>& jumps) {
  if (jumps.empty()) return "";
  constexpr size_t kCap = 8;
  std::string out;
  size_t shown = 0;
  for (size_t i = jumps.size(); i-- > 0 && shown < kCap;) {
    out += (shown == 0 ? "now " : " · ") + std::to_string(jumps[i] + 1);
    ++shown;
  }
  if (jumps.size() > kCap)
    out += " … +" + std::to_string(jumps.size() - kCap) + " deeper";
  return out;
}

// the cross-marked listing: a leap that lands on a PIN wears the pin's
// diamond — the ledger and the pins are two ledgers over one document,
// and :jumps answers "where have I been" AND "which of those places
// did I nail down" in one breath. The walker's ">" prefixes its entry;
// the pin's "◆" suffixes every pinned one — both can ride one entry
// (">30◆": you are walking on a pinned leap). `marks` rides the pins'
// own invariant: sorted, unique — ide.marks always is.
inline std::string ideJumpsWhisper(const std::vector<int>& jumps,
                                   int walkIx,
                                   const std::vector<int>& marks) {
  if (jumps.empty()) return "";
  const auto pinned = [&](int line) {
    return std::binary_search(marks.begin(), marks.end(), line);
  };
  constexpr size_t kCap = 8;
  std::string out;
  size_t shown = 0;
  const size_t n = jumps.size();
  const size_t markAt =
      (walkIx >= 0 && static_cast<size_t>(walkIx) < n &&
       static_cast<size_t>(walkIx) != n - 1)
          ? n - 1 - static_cast<size_t>(walkIx)
          : static_cast<size_t>(-1);         // a bookmark at "now" marks
                                             // nothing — the plain listing
  for (size_t i = n; i-- > 0 && shown < kCap;) {
    if (shown == 0)
      out += "now " + std::to_string(jumps[i] + 1);
    else if (shown == markAt)
      out += " · >" + std::to_string(jumps[i] + 1);
    else
      out += " · " + std::to_string(jumps[i] + 1);
    if (pinned(jumps[i])) out += "◆";
    ++shown;
  }
  if (n > kCap) out += " … +" + std::to_string(n - kCap) + " deeper";
  return out;
}

// the whisper with the walker's bookmark worn (no pins to cross-mark):
// the entry the hand walks on carries ">" so the listing answers BOTH
// questions — where the leaps went AND where the walker stands. No
// bookmark, a wild one, or one sitting on "now": the plain listing. A
// bookmark hidden beyond the cap simply stays unseen (honest).
inline std::string ideJumpsWhisper(const std::vector<int>& jumps,
                                   int walkIx) {
  static const std::vector<int> noPins;
  return ideJumpsWhisper(jumps, walkIx, noPins);
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
    if (!whisperOffer(w, p, maxW)) break;
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
    if (!whisperOffer(w, entry, maxW)) break;
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
    if (!whisperOffer(w, p, maxW))
      full = true;                      // the FIRST name that does not
  };                                    // fit ends the whisper — one
                                        // law for every completion

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

inline IdeMini ideMiniMap(const IdeState& s, int mapW, int bodyRows,
                          const IdeWrap* w = nullptr) {
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
    // under the fold a line is "in view" when ANY of its visual rows
    // is — the identity keeps the row law (one line, one row)
    row.inView =
        w ? (w->lineFirst[static_cast<size_t>(li) + 1] > s.top &&
             w->lineFirst[static_cast<size_t>(li)] < s.top + bodyRows)
          : (li >= s.top && li < s.top + bodyRows);
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
// a line "opens with a number" when digits lead it (air may precede):
// "42 the answer", "  7 lean", "-1 below", "3.5 half". The numeric
// sort's fuel — from_chars does the honest parsing, no std::stod
// throwing.
inline bool ideLeadingNumber(const std::string& s, double& out) {
  size_t i = 0;
  while (i < s.size() && (s[i] == ' ' || s[i] == '\t')) ++i;
  const auto [p, ec] =
      std::from_chars(s.data() + i, s.data() + s.size(), out);
  return ec == std::errc{} && p != s.data() + i;
}

inline int ideSortSel(IdeState& s, bool* numeric = nullptr) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  if (r1 <= r0) return 0;
  // numeric awareness: when EVERY line of the bed opens with a
  // number, the order is by that number — "2" before "10", the way a
  // human counts, not the way bytes land. One mixed line and the
  // whole bed stays byte-honest: the classic sort, no surprises.
  bool allNum = true;
  for (int r = r0; r <= r1 && allNum; ++r) {
    double v;
    if (!ideLeadingNumber(s.lines[r], v)) allNum = false;
  }
  idePushUndo(s, "sort");
  if (allNum) {
    std::sort(s.lines.begin() + r0, s.lines.begin() + r1 + 1,
              [](const std::string& a, const std::string& b) {
                double va = 0, vb = 0;
                const bool na = ideLeadingNumber(a, va);
                const bool nb = ideLeadingNumber(b, vb);
                if (na && nb && va != vb) return va < vb;
                return a < b;               // ties keep the byte order
              });
  } else {
    std::sort(s.lines.begin() + r0, s.lines.begin() + r1 + 1);
  }
  if (numeric) *numeric = allNum;
  for (int r = r0; r <= r1; ++r)
    ideTouch(s, r);                    // the census: the bed's lines were
                                       // reordered — every one was written
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
inline int ideRsortSel(IdeState& s, bool* numeric = nullptr) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  if (r1 <= r0) return 0;
  // the sort's mirror law, numbers included: an all-number bed lands
  // biggest first; one mixed line and the bytes rule (Z before A).
  bool allNum = true;
  for (int r = r0; r <= r1 && allNum; ++r) {
    double v;
    if (!ideLeadingNumber(s.lines[r], v)) allNum = false;
  }
  idePushUndo(s, "rsort");
  if (allNum) {
    std::sort(s.lines.begin() + r0, s.lines.begin() + r1 + 1,
              [](const std::string& a, const std::string& b) {
                double va = 0, vb = 0;
                const bool na = ideLeadingNumber(a, va);
                const bool nb = ideLeadingNumber(b, vb);
                if (na && nb && va != vb) return va > vb;
                return a > b;
              });
  } else {
    std::sort(s.lines.begin() + r0, s.lines.begin() + r1 + 1,
              std::greater<std::string>());
  }
  if (numeric) *numeric = allNum;
  for (int r = r0; r <= r1; ++r)
    ideTouch(s, r);                    // the census rides the reorder
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
    bool lineChanged = false;
    for (int c = from; c < to; ++c) {
      const unsigned char ch = static_cast<unsigned char>(l[static_cast<size_t>(c)]);
      if (!std::isalpha(ch)) { wordStart = true; continue; }
      const char goal = goal_for(ch, wordStart);
      wordStart = false;
      if (l[static_cast<size_t>(c)] != goal) {
        l[static_cast<size_t>(c)] = goal;
        ++changed;
        lineChanged = true;
      }
    }
    if (lineChanged) ideTouch(s, r);   // only the lines that changed voice
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
  {   // the census speaks the SAME law: a touch on a fallen line dies,
      // a touch on a kept line rides it home, one beneath slides up
    std::vector<int> nt;
    nt.reserve(s.touched.size());
    for (const int t : s.touched) {
      if (t < r0) nt.push_back(t);
      else if (t <= r1) {
        const int home = newHome[static_cast<size_t>(t)];
        if (home >= 0) nt.push_back(home);
      } else
        nt.push_back(t - removed);
    }
    std::sort(nt.begin(), nt.end());
    nt.erase(std::unique(nt.begin(), nt.end()), nt.end());
    s.touched = std::move(nt);
  }
  for (int r = r0; r <= kept; ++r)
    ideTouch(s, r);                    // the bed was rewritten by the fold
  ideSelClear(s);
  s.curR = std::min(kept + 1, static_cast<int>(s.lines.size()) - 1);
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  return removed;
}

// ── the squeeze: a run of blank lines becomes one ────────────────
// :squeeze breathes through the bed: wherever two or more empty
// lines stand together inside the selection, all but the first of
// the run fall. The structural law is uniq's law — a pin ON a
// fallen line dies, a pin on a kept line rides it home, a pin
// beneath the bed slides up by the count that fell.
inline int ideSqueezeSel(IdeState& s) {
  int r0 = 0;
  int r1 = static_cast<int>(s.lines.size()) - 1;
  if (const auto sel = ideSelRange(s)) {
    const auto [a, ca, b, cb] = *sel;
    r0 = a;
    r1 = b;
  }
  if (r1 <= r0) return 0;
  auto blank = [](const std::string& l) {
    return l.find_first_not_of(" \t") == std::string::npos;
  };
  int would = 0;                       // the dry pass: count the falls
  bool prevBlank = false;
  for (int r = r0; r <= r1; ++r) {
    const bool b = blank(s.lines[static_cast<size_t>(r)]);
    if (b && prevBlank) ++would;
    prevBlank = b;
  }
  if (would == 0) return 0;
  idePushUndo(s, "squeeze");
  std::vector<int> newHome(static_cast<size_t>(r1 + 1), -1);
  int kept = r0 - 1;                   // the compaction, run-aware
  bool runBlank = false;
  for (int read = r0; read <= r1; ++read) {
    const bool b = blank(s.lines[static_cast<size_t>(read)]);
    if (b && runBlank) continue;       // a second blank in a run falls
    runBlank = b;
    s.lines[static_cast<size_t>(++kept)] = s.lines[static_cast<size_t>(read)];
    newHome[static_cast<size_t>(read)] = kept;
  }
  const int removed = r1 - kept;
  s.lines.erase(s.lines.begin() + kept + 1, s.lines.begin() + r1 + 1);
  {   // uniq's pin law, word for word
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
  {
    std::vector<int> nt;
    nt.reserve(s.touched.size());
    for (const int t : s.touched) {
      if (t < r0) nt.push_back(t);
      else if (t <= r1) {
        const int home = newHome[static_cast<size_t>(t)];
        if (home >= 0) nt.push_back(home);
      } else
        nt.push_back(t - removed);
    }
    std::sort(nt.begin(), nt.end());
    nt.erase(std::unique(nt.begin(), nt.end()), nt.end());
    s.touched = std::move(nt);
  }
  for (int r = r0; r <= kept; ++r)
    ideTouch(s, r);
  ideSelClear(s);
  s.curR = std::min(kept + 1, static_cast<int>(s.lines.size()) - 1);
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  return removed;
}

// ── the retab: leading tabs become honest spaces ─────────────────
// :retab walks each selected line's INDENT — every tab at the head
// of a line widens to four spaces (the editor's tab law). Ink after
// the indent is untouched: a tab inside a string literal keeps its
// meaning. Shape never changes, so the pins stay put. The return is
// the count of lines whose indent was widened.
inline int ideRetabSel(IdeState& s) {
  int r0 = 0;
  int r1 = static_cast<int>(s.lines.size()) - 1;
  if (const auto sel = ideSelRange(s)) {
    const auto [a, ca, b, cb] = *sel;
    r0 = a;
    r1 = b;
  }
  if (r1 < r0) return 0;
  int would = 0;                       // the dry pass: count the widens
  for (int r = r0; r <= r1; ++r) {
    const std::string& l = s.lines[static_cast<size_t>(r)];
    if (l.find('\t') != std::string::npos &&
        l.find('\t') < l.find_first_not_of(" \t"))
      ++would;
  }
  if (would == 0) return 0;
  idePushUndo(s, "retab");
  for (int r = r0; r <= r1; ++r) {
    std::string& l = s.lines[static_cast<size_t>(r)];
    const size_t ink = l.find_first_not_of(" \t");
    if (ink == std::string::npos || l.find('\t') >= ink) continue;
    std::string indent;
    for (const char c : l.substr(0, ink))
      indent += c == '\t' ? "    " : std::string(1, c);
    s.lines[static_cast<size_t>(r)] = indent + l.substr(ink);
  }
  for (int r = r0; r <= r1; ++r) ideTouch(s, r);
  ideSelClear(s);
  s.dirty = true;
  s.idle = 0;
  return would;
}

// ── the whitespace census: the margin's honest mirror ────────────
// :ws changes nothing — it counts. Three honest numbers for the
// selection (or the whole bed): lines wearing trailing whitespace,
// lines indented with tabs, and lines longer than the 80-column
// law. A census is a mirror: it reports, it does not judge.
struct WsCensus {
  int trailing = 0;
  int tabs = 0;
  int long_ = 0;
};
inline WsCensus ideWsCensus(const IdeState& s) {
  int r0 = 0;
  int r1 = static_cast<int>(s.lines.size()) - 1;
  if (const auto sel = ideSelRange(s)) {
    const auto [a, ca, b, cb] = *sel;
    r0 = a;
    r1 = b;
  }
  WsCensus c;
  for (int r = r0; r <= r1; ++r) {
    const std::string& l = s.lines[static_cast<size_t>(r)];
    const size_t ink = l.find_first_not_of(" \t");
    if (l.find_first_not_of(" \t") != std::string::npos) {
      if (ink != 0 && l[ink - 1] == '\t') ++c.tabs;
    }
    const size_t last = l.find_last_not_of(" \t");
    if (last == std::string::npos ? !l.empty() : last + 1 != l.size())
      ++c.trailing;
    if (static_cast<int>(l.size()) > 80) ++c.long_;
  }
  return c;
}

// ── the bracket's twin: :match walks to the other half ───────────
// From the hand (the cursor), find the nearest bracket at or after
// it — an opener scans forward for its twin, a closer scans back.
// The walk is QUOTE-HONEST: a bracket inside a string literal is
// ink, not structure (single or double quotes, backslash escapes,
// and the quote's law ends at its own line's edge). The return is
// the twin's seat, or silence (an unmatched bracket says so).
struct BracketTwin {
  bool found = false;
  int row = 0;
  int col = 0;
};
inline BracketTwin ideMatchBracket(const IdeState& s) {
  static const std::string openers = "([{";
  static const std::string closers = ")]}";
  auto kind = [](char c, const std::string& set) -> int {
    const size_t k = set.find(c);
    return k == std::string::npos ? -1 : static_cast<int>(k);
  };
  auto charAt = [&](int r, int c) -> char {
    if (r < 0 || r >= static_cast<int>(s.lines.size())) return '\0';
    const std::string& l = s.lines[static_cast<size_t>(r)];
    return c >= 0 && c < static_cast<int>(l.size()) ? l[static_cast<size_t>(c)]
                                                    : '\0';
  };
  // quote honesty per line: is this column inside a string literal?
  auto inString = [&](int r, int col) -> bool {
    if (r < 0 || r >= static_cast<int>(s.lines.size())) return false;
    const std::string& l = s.lines[static_cast<size_t>(r)];
    bool inS = false, inD = false;
    for (int i = 0; i < col && i < static_cast<int>(l.size()); ++i) {
      const char c = l[static_cast<size_t>(i)];
      if (c == '\\' && (inS || inD)) { ++i; continue; }
      if (c == '\'' && !inD) inS = !inS;
      else if (c == '"' && !inS) inD = !inD;
    }
    return inS || inD;
  };

  // step one: the nearest live bracket at or after the hand
  int r = s.curR, c = s.curC;
  char start = '\0';
  int sk = -1, dir = 0;
  for (; r < static_cast<int>(s.lines.size()); ++r, c = 0) {
    for (; c < static_cast<int>(s.lines[static_cast<size_t>(r)].size()); ++c) {
      const char ch = charAt(r, c);
      if ((kind(ch, openers) >= 0 || kind(ch, closers) >= 0) &&
          !inString(r, c)) {
        start = ch;
        sk = kind(ch, openers);
        dir = sk >= 0 ? 1 : -1;
        if (sk < 0) sk = kind(ch, closers);
        break;
      }
    }
    if (start != '\0') break;
  }
  if (start == '\0') return {};          // no bracket ahead — honest silence

  // step two: walk the depth in the bracket's own direction, across
  // the whole bed — cross-line twins land honestly. The starting
  // bracket is consumed (depth 1); a same-kind bracket nests, the
  // twin closes, and zero is the landing.
  int depth = 1;
  const std::string& twinSet = dir > 0 ? closers : openers;
  for (int rr = r;
       rr >= 0 && rr < static_cast<int>(s.lines.size()); rr += dir) {
    const std::string& l = s.lines[static_cast<size_t>(rr)];
    const int last = static_cast<int>(l.size()) - 1;
    // the first row continues from just past the bracket; the rest
    // sweeps the whole line in the walk's direction
    for (int cc = (rr == r ? c + dir : (dir > 0 ? 0 : last));
         cc >= 0 && cc <= last; cc += dir) {
      const char ch = l[static_cast<size_t>(cc)];
      if (inString(rr, cc)) continue;
      if (ch == start) ++depth;
      else if (kind(ch, twinSet) == sk && --depth == 0)
        return BracketTwin{true, rr, cc};
    }
  }
  return {};                             // the twin never came — say so
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
  bool touchesMoved = false;
  for (int& t : s.touched)
    if (t >= r0 && t <= r1) {
      t = r0 + (r1 - t);             // the census rides the flip too
      touchesMoved = true;
    }
  if (touchesMoved) std::sort(s.touched.begin(), s.touched.end());
  for (int r = r0; r <= r1; ++r)
    ideTouch(s, r);                    // every flipped line was rewritten
  ideSelClear(s);
  s.curR = r0;
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  return r1 - r0 + 1;
}

// ── the dice: the selection's lines walk to random homes ───────────
// :shuffle deals the bed like cards — Fisher-Yates, honest coins, no
// alphabet, no mirror. The seed is the law's anchor: a seeded
// :shuffle deals EXACTLY the same order every time (the receipt
// speaks the seed, so a lucky deal can be replayed or shared), a
// bare :shuffle rolls one from the clock and names it. The sort
// family's bed and refusals; ONE restore point named "shuffle"; the
// pins ride their CONTENT to its new home (the flip's law, told by a
// permutation), the census touches the whole bed (every line was
// rewritten), the hand rests at the bed's head, the selection lets
// go. 0 with no bed; else the count of lines dealt.
inline int ideShuffleSel(IdeState& s, unsigned seed, bool seeded,
                         unsigned* usedSeed) {
  const auto sel = ideSelRange(s);
  if (!sel) return 0;
  const auto [r0, c0, r1, c1] = *sel;
  if (r1 <= r0) return 0;                      // a same-line bed: no dice
  const int count = r1 - r0 + 1;
  const unsigned rolled =
      seeded ? seed
             : static_cast<unsigned>(
                 std::chrono::steady_clock::now().time_since_epoch().count() &
                 0x7fffffffu);
  std::mt19937 rng(rolled);
  std::vector<int> deal(static_cast<size_t>(count));  // pos k reads old a[k]
  for (int k = 0; k < count; ++k) deal[static_cast<size_t>(k)] = k;
  for (int k = count - 1; k > 0; --k) {
    std::uniform_int_distribution<int> die(0, k);
    std::swap(deal[static_cast<size_t>(k)], deal[static_cast<size_t>(die(rng))]);
  }
  std::vector<int> home(static_cast<size_t>(count));  // old offset -> new home
  for (int k = 0; k < count; ++k)
    home[static_cast<size_t>(deal[static_cast<size_t>(k)])] = k;
  idePushUndo(s, "shuffle");
  const std::vector<std::string> bed(s.lines.begin() + r0,
                                     s.lines.begin() + r1 + 1);
  for (int k = 0; k < count; ++k)
    s.lines[static_cast<size_t>(r0 + k)] =
        bed[static_cast<size_t>(deal[static_cast<size_t>(k)])];
  {                                            // the pins follow their words
    for (int& m : s.marks)
      if (m >= r0 && m <= r1) m = r0 + home[static_cast<size_t>(m - r0)];
    std::sort(s.marks.begin(), s.marks.end());
  }
  {                                            // the census rides its lines
    for (int& t : s.touched)
      if (t >= r0 && t <= r1) t = r0 + home[static_cast<size_t>(t - r0)];
    std::sort(s.touched.begin(), s.touched.end());
    s.touched.erase(std::unique(s.touched.begin(), s.touched.end()),
                    s.touched.end());
  }
  for (int r = r0; r <= r1; ++r)
    ideTouch(s, r);                            // the whole bed was rewritten
  ideSelClear(s);
  s.curR = r0;                                 // the hand rests at the head
  s.curC = 0;
  s.dirty = true;
  s.idle = 0;
  if (usedSeed) *usedSeed = rolled;
  return count;
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
        ideTouch(s, r);                // the census: only the lines that
        if (r == r0) headCut = cutn;   // actually stepped
      }
    } else if (!keepsSilence(l)) {
      l.insert(0, 4, ' ');
      ++moved;
      ideTouch(s, r);
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
    for (int& t : s.touched) {
      if (t == r0 - 1) t = r1;           // the neighbor's touch rides too
      else if (t >= r0 && t <= r1) t -= 1;
    }
    for (int r = r0 - 1; r <= r1; ++r)
      ideTouch(s, r);                    // the lift rewrote the whole span
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
    for (int& t : s.touched) {
      if (t == r1 + 1) t = r0;           // the neighbor's touch rides too
      else if (t >= r0 && t <= r1) t += 1;
    }
    for (int r = r0; r <= r1 + 1; ++r)
      ideTouch(s, r);                    // the drop rewrote the whole span
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
  ideTouchShift(s, r1 + 1, count);     // the census rides it too
  for (int r = r1 + 1; r <= r1 + count; ++r)
    ideTouch(s, r);                    // the copies are the fresh work
  ideSelClear(s);
  s.curR = r0 + count;                 // the hand lands on the copy's head
  s.curC = std::min(s.curC, static_cast<int>(s.lines[static_cast<size_t>(s.curR)].size()));
  s.dirty = true;
  s.idle = 0;
  return count;
}

// the jump's honest target: an absolute number is the line (1-based),
// a relative one rides from where the hand stands; both clamp to the
// document — a jump never lands outside the world
inline int ideGotoTarget(const IdeState& s, float num, bool rel) {
  const int N = static_cast<int>(s.lines.size());
  const int goal = rel ? s.curR + static_cast<int>(num)
                       : static_cast<int>(num) - 1;
  return std::clamp(goal, 0, std::max(0, N - 1));
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
  {   // the census speaks the same law: a touch on a folded line dies
    std::vector<int> nt;
    nt.reserve(s.touched.size());
    for (const int t : s.touched) {
      if (t > r0 && t <= r1) continue;
      nt.push_back(t > r1 ? t - (r1 - r0) : t);
    }
    s.touched = std::move(nt);
  }
  ideTouch(s, r0);                     // the seam holds the fold's words
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
  for (size_t li = 0; li < s.lines.size(); ++li) {
    std::string& l = s.lines[li];
    const size_t last = l.find_last_not_of(" \t");
    if (last == std::string::npos) {
      if (!l.empty()) { l.clear(); ideTouch(s, static_cast<int>(li)); }
    } else if (last + 1 < l.size()) {
      l.resize(last + 1);
      ideTouch(s, static_cast<int>(li));  // only the lines that lost air
    }
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
    ideTouchErase(s, s.curR, 1);             // its touch too
  }
  s.lines.insert(at, block.begin(), block.end());
  ideMarkShift(s, blank ? s.curR : s.curR + 1,
               static_cast<int>(block.size()));
  ideTouchShift(s, blank ? s.curR : s.curR + 1,
                static_cast<int>(block.size()));
  const int bedAt = blank ? s.curR : s.curR + 1;
  for (int r = bedAt; r < bedAt + static_cast<int>(block.size()); ++r)
    ideTouch(s, r);                          // the boilerplate's landing
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
// ── the crew: many hands, one breath ────────────────────────────────
// The four edit verbs (typed, backspace, enter, forward delete) speak
// through EVERY hand. Each verb below is the single hand's law pulled
// out whole — the same bytes, the same pair rules, the same pins and
// census rides — speaking at an (r, c) the caller names, so the single
// hand and the crew can never drift apart: ONE law, many mouths.

// one printable character typed at (r, c) — the closer you already
// have is skipped, an opener carries its closer (quotes only when
// neither neighbor is wordy). Returns the hand's new column.
inline int ideTypeCharAt(std::vector<std::string>& L, int r, int c, char ch) {
  std::string& line = L[static_cast<size_t>(r)];
  if (ideIsCloser(ch) && c < static_cast<int>(line.size()) &&
      line[static_cast<size_t>(c)] == ch)
    return c + 1;                          // skipped over, never doubled
  line.insert(line.begin() + std::min(c, static_cast<int>(line.size())), ch);
  ++c;
  const char closer = ideCloserFor(ch);
  if (closer) {
    const bool quote = ch == '"' || ch == '\'';
    bool pair = true;
    if (quote) {
      const bool prevWord =
          c >= 2 && (std::isalnum(static_cast<unsigned char>(
                        line[static_cast<size_t>(c) - 2])) ||
                     line[static_cast<size_t>(c) - 2] == '_');
      const bool nextWord =
          c < static_cast<int>(line.size()) &&
          (std::isalnum(static_cast<unsigned char>(line[static_cast<size_t>(c)])) ||
           line[static_cast<size_t>(c)] == '_');
      pair = !prevWord && !nextWord;
    }
    if (pair)
      line.insert(line.begin() + std::min(c, static_cast<int>(line.size())),
                  closer);
  }
  return c;
}

// one backspace at (r, c) — the pair dies together, the char dies
// alone, the line joins the one above. Returns the hand's new seat.
inline std::pair<int, int> ideBackAt(IdeState& s, int r, int c) {
  std::string& line = s.lines[static_cast<size_t>(r)];
  if (c > 0 && c < static_cast<int>(line.size()) &&
      ideCloserFor(line[static_cast<size_t>(c) - 1]) ==
          line[static_cast<size_t>(c)]) {
    line.erase(line.begin() + c);
    line.erase(line.begin() + (c - 1));
    ideTouch(s, r);
    return {r, c - 1};
  }
  if (c > 0) {
    line.erase(line.begin() + c - 1);
    ideTouch(s, r);
    return {r, c - 1};
  }
  if (r > 0) {                             // join with the line above
    const int seam = static_cast<int>(s.lines[static_cast<size_t>(r - 1)].size());
    s.lines[static_cast<size_t>(r - 1)] += line;
    s.lines.erase(s.lines.begin() + r);
    ideMarkErase(s, r, 1);                 // the joined line's pin goes
    ideTouchErase(s, r, 1);                // its touch goes with it
    ideTouch(s, r - 1);                    // the seam holds both lives
    return {r - 1, seam};
  }
  return {r, c};                           // the document's head: nothing
}

// one forward delete at (r, c) — the char ahead dies alone, the line
// at its end joins the one below. Returns the hand's new seat.
inline std::pair<int, int> ideDelAt(IdeState& s, int r, int c) {
  std::string& cur = s.lines[static_cast<size_t>(r)];
  if (c < static_cast<int>(cur.size())) {
    cur.erase(cur.begin() + c);
    ideTouch(s, r);
    return {r, c};
  }
  if (r + 1 < static_cast<int>(s.lines.size())) {
    cur += s.lines[static_cast<size_t>(r) + 1];
    s.lines.erase(s.lines.begin() + r + 1);
    ideMarkErase(s, r + 1, 1);             // the joined line's pin rides out
    ideTouchErase(s, r + 1, 1);            // its touch rides out too
    ideTouch(s, r);                        // the seam holds both lives
  }
  return {r, c};
}

// one enter at (r, c) — the whole ceremony: the bracket's three-line
// split, the indent inherited, the opener's bump, the closer's drop,
// the pins and the census riding down. Returns the hand's new seat.
inline std::pair<int, int> ideEnterAt(IdeState& s, int r, int c) {
  std::string& cur = s.lines[static_cast<size_t>(r)];
  const int at = std::min(c, static_cast<int>(cur.size()));
  const bool pairSplit =
      at > 0 && at < static_cast<int>(cur.size()) &&
      ((cur[static_cast<size_t>(at) - 1] == '(' && cur[at] == ')') ||
       (cur[static_cast<size_t>(at) - 1] == '[' && cur[at] == ']') ||
       (cur[static_cast<size_t>(at) - 1] == '{' && cur[at] == '}'));
  std::string rest = cur.substr(static_cast<size_t>(at));
  cur.resize(static_cast<size_t>(at));
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
    s.lines.insert(s.lines.begin() + r + 1, indent);
    s.lines.insert(s.lines.begin() + r + 2, base + rest);
    ideMarkShift(s, r + 1, 2);
    ideTouchShift(s, r + 1, 2);
    ideTouch(s, r);
    ideTouch(s, r + 1);
    ideTouch(s, r + 2);
  } else {
    s.lines.insert(s.lines.begin() + r + 1, indent + rest);
    ideMarkShift(s, r + 1, 1);
    ideTouchShift(s, r + 1, 1);
    ideTouch(s, r);
    ideTouch(s, r + 1);
  }
  return {r + 1, static_cast<int>(indent.size())};
}

// the crew's census: the primary hand plus every extra
inline int ideCrewHands(const IdeState& s) {
  return 1 + static_cast<int>(s.crew.size());
}

// add one hand at (r, c); refuses the primary's own seat and any seat
// a hand already holds. Keeps the crew sorted. True when it took.
inline bool ideCrewAdd(IdeState& s, int r, int c) {
  if (r == s.curR && c == s.curC) return false;
  const auto it = std::lower_bound(s.crew.begin(), s.crew.end(),
                                   std::pair<int, int>{r, c});
  if (it != s.crew.end() && *it == std::pair<int, int>{r, c}) return false;
  s.crew.insert(it, {r, c});
  return true;
}

// plant `n` more hands BELOW the lowest hand, each on the next line at
// the same column (clamped to that line's honest end). The document's
// edge refuses honestly. Returns how many hands were planted.
inline int ideCrewPlant(IdeState& s, int n) {
  const std::pair<int, int> seed =
      s.crew.empty() ? std::pair<int, int>{s.curR, s.curC} : s.crew.back();
  int planted = 0;
  for (int r = seed.first; planted < n; ++planted) {
    ++r;
    if (r >= static_cast<int>(s.lines.size())) break;
    const int c = std::clamp(seed.second, 0,
                             static_cast<int>(s.lines[static_cast<size_t>(r)].size()));
    if (!ideCrewAdd(s, r, c)) break;       // a refused seat ends the walk
  }
  return planted;
}

// every hand clamped to the document it stands on — after an undo, an
// open, any reshape. Hands that land on the primary's seat dissolve.
inline void ideCrewClamp(IdeState& s) {
  if (s.crew.empty()) return;
  std::vector<std::pair<int, int>> keep;
  for (auto [r, c] : s.crew) {
    r = std::clamp(r, 0, static_cast<int>(s.lines.size()) - 1);
    c = std::clamp(c, 0, static_cast<int>(s.lines[static_cast<size_t>(r)].size()));
    if (r == s.curR && c == s.curC) continue;
    if (!keep.empty() && keep.back() == std::pair<int, int>{r, c}) continue;
    keep.push_back({r, c});
  }
  s.crew = std::move(keep);
}

// one frame through every hand: the four verbs, highest hand first so
// no hand's edit shifts another's ground. ONE restore point per frame
// (the same quick-hands coalescing the single hand obeys). Hands that
// land together merge; the primary keeps its identity.
inline void ideCrewFrame(IdeState& s, const Keys& k) {
  const bool typing = !k.typed.empty();
  const bool quick = s.idle < 0.8;
  const bool cont = typing ? (s.lastTyping && quick)
                  : k.back ? ((s.lastTyping || s.lastBack) && quick)
                           : false;
  if (!cont)
    idePushUndo(s, typing       ? "the crew's typing"
                 : k.back       ? "the crew's backspace"
                 : k.enter      ? "the crew's enter"
                                : "the crew's delete");
  else
    s.redo.clear();
  s.lastTyping = typing;
  s.lastBack = k.back && !typing;

  // the hands, highest seat first; the primary rides along — its seat
  // is remembered and FOUND after the sort (sorting moves every entry)
  std::vector<std::pair<int, int>> hands = s.crew;
  hands.push_back({s.curR, s.curC});
  const std::pair<int, int> primarySeat = {s.curR, s.curC};
  std::sort(hands.begin(), hands.end(), std::greater<>{});
  const int primaryIx = static_cast<int>(
      std::find(hands.begin(), hands.end(), primarySeat) - hands.begin());

  std::vector<std::pair<int, int>> landed(hands.size());
  for (size_t i = 0; i < hands.size(); ++i) {
    auto [r, c] = hands[i];
    r = std::clamp(r, 0, static_cast<int>(s.lines.size()) - 1);
    c = std::clamp(c, 0, static_cast<int>(s.lines[static_cast<size_t>(r)].size()));
    if (typing) {
      for (const char ch : k.typed)
        c = ideTypeCharAt(s.lines, r, c, ch);
      ideTouch(s, r);
      landed[i] = {r, c};
    } else if (k.back) {
      const bool join = c == 0 && r > 0;     // the seam's law: a hand that
      const int seamLen =                    // landed on the row being
          join ? static_cast<int>(s.lines[static_cast<size_t>(r - 1)].size()) : 0;
      landed[i] = ideBackAt(s, r, c);
      if (join)
        for (size_t j = 0; j < i; ++j) {     // merged into the row above
          if (landed[j].first == r)
            landed[j] = {r - 1, seamLen + landed[j].second};
          else if (landed[j].first > r)
            --landed[j].first;               // rows below the seam slide up
        }
    } else if (k.enter) {
      landed[i] = ideEnterAt(s, r, c);
      // the split pushed every seat below the seam down one — hands
      // already landed ride the shift too
      for (size_t j = 0; j < i; ++j)
        if (landed[j].first > r) ++landed[j].first;
    } else if (k.del) {
      const bool join = c >= static_cast<int>(s.lines[static_cast<size_t>(r)].size()) &&
                        r + 1 < static_cast<int>(s.lines.size());
      landed[i] = ideDelAt(s, r, c);
      if (join)
        for (size_t j = 0; j < i; ++j) {     // merged into the row above
          if (landed[j].first == r + 1)
            landed[j] = {r, c + landed[j].second};
          else if (landed[j].first > r + 1)
            --landed[j].first;               // rows below the seam slide up
        }
    }
  }

  // the primary keeps its seat; the crew re-forms around it, unique
  s.curR = landed[static_cast<size_t>(primaryIx)].first;
  s.curC = landed[static_cast<size_t>(primaryIx)].second;
  s.crew.clear();
  for (size_t i = 0; i < landed.size(); ++i) {
    if (static_cast<int>(i) == primaryIx) continue;
    if (landed[i] == std::pair<int, int>{s.curR, s.curC}) continue;
    if (!s.crew.empty() && s.crew.back() == landed[i]) continue;
    s.crew.push_back(landed[i]);
  }
  std::sort(s.crew.begin(), s.crew.end());
}

// the transpose: the two neighbors trade places — the vim xp law.
// The hand ON a char (or between chars) swaps it with the one ahead;
// at the line's tail (the hand ON or AFTER the last char) the LAST two
// trade. The hand lands after the transposed pair. A line too short to
// hold a pair refuses honestly. Returns true when it traded.
inline bool ideTranspose(IdeState& s) {
  std::string& l = s.lines[static_cast<size_t>(s.curR)];
  const int len = static_cast<int>(l.size());
  if (len < 2) return false;
  const int a = s.curC <= len - 2 ? s.curC : len - 2;
  const int b = a + 1;
  std::swap(l[static_cast<size_t>(a)], l[static_cast<size_t>(b)]);
  s.curC = b + 1;                          // after the transposed pair
  ideTouch(s, s.curR);
  return true;
}

// ── the case cycle: the word's three coats, one breath apart ────────
// A word wears a coat: the whisper (no upper letter), the SHOUT (no
// lower letter), or the Title (its first letter raised, the rest
// hushed) — anything between (camelCase, the shouts with a digit's
// tail) is the mixed coat. ctrl+U walks the wheel: whisper → SHOUT →
// Title → whisper. A coat that would change nothing bows out and the
// walk takes the next — a one-letter word (V2, A) honestly lives a
// two-coat life. Digits and underscores ride along untouched.
inline std::string ideCaseWhisper(const std::string& w) {
  std::string r = w;
  for (char& ch : r)
    if (std::isalpha(static_cast<unsigned char>(ch)))
      ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
  return r;
}
inline std::string ideCaseShout(const std::string& w) {
  std::string r = w;
  for (char& ch : r)
    if (std::isalpha(static_cast<unsigned char>(ch)))
      ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
  return r;
}
inline std::string ideCaseTitle(const std::string& w) {
  std::string r = w;
  bool first = true;
  for (char& ch : r)
    if (std::isalpha(static_cast<unsigned char>(ch))) {
      ch = first
               ? static_cast<char>(std::toupper(static_cast<unsigned char>(ch)))
               : static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
      first = false;
    }
  return r;
}

// The word the hand rides: ON a word char, that word; on a gap, the
// word BEHIND the hand; in the open (no word behind either), the word
// AHEAD on the line. The coat never moves a letter, so the hand keeps
// its seat — press again and the same word takes its next coat.
// The plan is the cycle's thought, the apply is its paint: split so a
// CREW can think for every hand first, then paint all of them behind
// one shared undo step.
struct IdeCasePlan {
  int a = -1, b = -1;                      // [a, b) the word's span
  std::string next;                        // the word's next coat
};

// the coat walk: the word's next coat, or nullopt when no coat can
// paint (bare digits) — shared by the hand law, the crew, and the
// selection
inline std::optional<std::string> ideCaseNext(const std::string& w) {
  bool anyUpper = false, anyLower = false;
  for (const char ch : w) {
    if (std::isupper(static_cast<unsigned char>(ch))) anyUpper = true;
    if (std::islower(static_cast<unsigned char>(ch))) anyLower = true;
  }
  if (!anyUpper && !anyLower) return std::nullopt;  // digits wear no coat
  int coat = !anyUpper ? 0 : (!anyLower ? 1 : 2);  // 0 whisper 1 shout 2 title
  static constexpr int NEXT[3] = {1, 2, 0};
  for (int step = 0; step < 3; ++step) {   // a coat that changes nothing
    coat = NEXT[coat];                     // bows out; the walk carries on
    const std::string cand = coat == 0 ? ideCaseWhisper(w)
                             : coat == 1 ? ideCaseShout(w)
                                         : ideCaseTitle(w);
    if (cand != w) return cand;
  }
  return std::nullopt;                     // armored: never paint the same
}

inline std::optional<IdeCasePlan>
ideCasePlanAt(const IdeState& s, int r, int c) {
  if (r < 0 || r >= static_cast<int>(s.lines.size())) return std::nullopt;
  const std::string& l = s.lines[static_cast<size_t>(r)];
  const int len = static_cast<int>(l.size());
  const auto wc = [&](int i) {
    return i >= 0 && i < len &&
           ideWordChar(l[static_cast<size_t>(i)]);
  };
  int a = -1, b = -1;                      // [a, b) the word's span
  if (wc(c)) {
    a = c;
    while (a > 0 && wc(a - 1)) --a;
    b = c;
    while (b < len && wc(b)) ++b;
  } else if (wc(c - 1)) {
    b = c;
    a = b;
    while (a > 0 && wc(a - 1)) --a;
  } else {
    a = c;
    while (a < len && !wc(a)) ++a;
    b = a;
    while (b < len && wc(b)) ++b;
  }
  if (a < 0 || b <= a) return std::nullopt;  // no word: the refusal is honest
  const std::string w = l.substr(static_cast<size_t>(a),
                                 static_cast<size_t>(b - a));
  const auto next = ideCaseNext(w);
  if (!next) return std::nullopt;
  return IdeCasePlan{a, b, *next};
}

// The selection's coat: every word FULLY inside the span cycles its
// own coat — the selection never edits what it doesn't hold whole (a
// word the span cuts is left honest, teaching a clean drag). Rows
// ride their own windows: the first row from c0, the last to c1, the
// middle rows whole.
inline std::vector<std::pair<int, IdeCasePlan>>
ideCasePlanSelection(const IdeState& s, const SelRange& sel) {
  std::vector<std::pair<int, IdeCasePlan>> plans;
  const auto [r0, c0, r1, c1] = sel;       // r0/c0 the span's head
  for (int r = r0; r <= r1; ++r) {
    if (r < 0 || r >= static_cast<int>(s.lines.size())) continue;
    const std::string& l = s.lines[static_cast<size_t>(r)];
    const int len = static_cast<int>(l.size());
    const int lo = (r == r0) ? c0 : 0;
    const int hi = (r == r1) ? std::min(c1, len) : len;
    int i = lo;
    while (i < hi) {
      if (ideWordChar(l[static_cast<size_t>(i)])) {
        const bool cutLeft = i == lo && i > 0 &&
                             ideWordChar(l[static_cast<size_t>(i) - 1]);
        int b = i;
        while (b < len && ideWordChar(l[static_cast<size_t>(b)])) ++b;
        if (!cutLeft && b <= hi) {           // the word sits whole inside
          const std::string w = l.substr(static_cast<size_t>(i),
                                         static_cast<size_t>(b - i));
          if (const auto next = ideCaseNext(w))
            plans.emplace_back(r, IdeCasePlan{i, b, *next});
        }
        i = b;
      } else ++i;
    }
  }
  return plans;
}

inline bool ideCaseApply(IdeState& s, int r, const IdeCasePlan& p) {
  std::string& l = s.lines[static_cast<size_t>(r)];
  l.replace(static_cast<size_t>(p.a), static_cast<size_t>(p.b - p.a), p.next);
  ideTouch(s, r);                          // the census hears about it
  return true;
}

inline bool ideCycleCase(IdeState& s) {
  const auto p = ideCasePlanAt(s, s.curR, s.curC);
  if (!p) return false;
  idePushUndo(s, "case cycle");            // the step back, before the paint
  return ideCaseApply(s, s.curR, *p);
}

inline void ideKey(IdeState& ide, const Keys& k) {
  // ── esc owns its frame. A bare ESC is a MODE key — play, search,
  // escape — and when a pty delivers it coalesced with typing (the
  // app stalled past a keypress burst), the text belongs to the NEXT
  // frame, never to this one. The smoke once typed ":recent" into a
  // live document exactly this way; the gate caught it. Nothing that
  // follows an ESC in the same breath may touch the document.
  if (k.esc) {
    ide.crew.clear();                       // esc: the crew bows out too
    ide.idle = 0;
    return;
  }
  // the crew is transient: a frame that CARRIES a key yet speaks none
  // of the four edit verbs dissolves it — movement, a click, esc, a
  // command. The engine's empty breaths (a frame with no keys at all)
  // never dissolve anything — the crew lives between keystrokes too.
  if (!ide.crew.empty()) {
    const bool editVerb =
        !k.typed.empty() || k.back || k.del || k.enter;
    const bool carriesKey =
        k.left || k.right || k.jump || k.reset || k.fit || k.zoomIn ||
        k.zoomOut || k.inspect || k.quit || k.esc || k.viewFile ||
        k.cmd || k.shot || k.scroll != 0 || k.slash || k.enter ||
        k.back || k.ctrlS || k.ctrlR || k.up || k.down || k.aLeft ||
        k.aRight || k.tab || k.backTab || k.braille || k.ctrlN ||
        k.pageUp || k.pageDn || k.del || k.home || k.end || k.ctrlG ||
        k.ctrlZ || k.ctrlY || k.jumpBack || k.jumpFwd || k.ctrlL ||
        k.ctrlF || k.ctrlD || k.delWord || k.wLeft || k.wRight ||
        k.delWordFwd || k.comment || k.docHome || k.docEnd || k.sUp ||
        k.sDown || k.altUp || k.altDown || k.sLeft || k.sRight ||
        k.sWLeft || k.sWRight || k.ctrlC || k.ctrlX || k.ctrlV ||
        k.leap || k.markToggle || k.markNext || k.markPrev ||
        k.findJump || k.findBack || k.clickR >= 0 || k.dragR >= 0 ||
        k.clickRelease;
    if (carriesKey && !editVerb) ide.crew.clear();
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
    if (k.enter) ideFindNext(ide);             // to the next hit
    if (k.findJump) ideFindNext(ide);          // F3 walks too, bar up or down
    if (k.findBack) ideFindPrev(ide);          // shift+F3 walks back
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

  // ── the hunt continues: F3 / shift+F3 walk the last query's hits
  // even after the searchlight has rested. The hits are recomputed
  // live (the doc may have moved since the bar was up), the hand hops
  // hit to hit, and the console speaks the count — with the bar down
  // there is no counter, so the receipt is the walk's witness. A look,
  // never an edit: nothing dirties, nothing undoes. An empty query has
  // nothing to hunt; the frame is consumed either way.
  if (k.findJump || k.findBack) {
    if (!ide.findQ.empty()) {
      ideFindRefresh(ide);
      const bool walked = k.findJump ? ideFindNext(ide) : ideFindPrev(ide);
      if (walked)
        ide.console.push_back(
            "engine: hit " + std::to_string(ide.findSel + 1) + "/" +
            std::to_string(ide.findHits.size()) + " — line " +
            std::to_string(ide.curR + 1));
      else
        ide.console.push_back("engine: no matches for '" + ide.findQ +
                              "' — ctrl+f opens the searchlight");
    }
    ide.lastTyping = ide.lastBack = false;
    ide.idle = 0;
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

  // ── the ride in the hands: alt+↑/↓ — :lift/:drop without opening
  // the bar. The bed is the selection's lines, or the hand's line;
  // the pins ride along; ONE undo step each ("lift"/"drop"); the
  // edges refuse with the honest receipt, never a phantom step.
  if (k.altUp || k.altDown) {
    const bool down = k.altDown;
    const int rode = ideMoveSel(ide, down);
    if (rode > 0)
      ide.console.push_back(
          "engine: " + std::to_string(rode) + " line" +
          (rode == 1 ? "" : "s") +
          (down ? " dropped one line — the pins rode along"
                : " lifted one line — the pins rode along"));
    else
      ide.console.push_back(down ? "engine: nothing below to drop into"
                                 : "engine: nothing above to lift into");
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
        const int from = ide.curR;     // the leap's law: a CHANGE of line
        ide.curR = to;                 // plants the jump — a stand does not
        ide.curC = 0;
        if (to != from) ideJumpPush(ide, to);
        ideSelClear(ide);
        ide.console.push_back("engine: the hand leaps to the pin at line " +
                              std::to_string(to + 1));
      }
    }
    ide.lastTyping = ide.lastBack = false;
    ide.idle = 0;
    return;
  }

  // ── the jumps' walker: ctrl+o / alt+← into the ledger's past,
  // alt+→ back out. A look, never an edit: nothing plants, the
  // ledger only moves its bookmark — the draw keeps the hand on
  // screen the way the pins' leap trusts it to.
  if (k.jumpBack || k.jumpFwd) {
    const int to =
        k.jumpBack ? ideJumpWalkBack(ide) : ideJumpWalkFwd(ide);
    if (to < 0) {
      ide.console.push_back(
          k.jumpBack
              ? (ide.jumps.empty()
                     ? "engine: no jumps to walk — :goto, F2 and the "
                       "welcome back plant them"
                     : "engine: the ledger's first jump — nothing "
                       "behind it")
              : "engine: nothing ahead — you stand on the newest leap");
    } else {
      ide.curR = to;
      ide.curC = 0;
      ide.hcol = 0;
      ideSelClear(ide);
      ide.console.push_back(
          k.jumpBack
              ? "engine: the hand walks back to line " +
                    std::to_string(to + 1)
              : "engine: the hand walks forward to line " +
                    std::to_string(to + 1));
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

  // ── the crew's frame: many hands, one breath. When hands are many
  // the four edit verbs speak through every hand at once and the crew's
  // own law IS the frame's whole edit — the single-hand path below
  // sleeps. One restore point per frame, named after the verb.
  if (!ide.crew.empty() &&
      (!k.typed.empty() || k.back || k.del || k.enter)) {
    ideSelClear(ide);                       // the crew's breath is its own
    ideCrewFrame(ide, k);
    ide.dirty = true;                       // the game hears about it
    ide.idle = 0;
    ideClamp(ide);
    ideCrewClamp(ide);
    return;
  }

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

  // the single hand's typing and backspace speak the SAME laws the crew
  // speaks — one law, many mouths (see ideTypeCharAt / ideBackAt above)
  for (const char ch : k.typed)
    ide.curC = ideTypeCharAt(L, ide.curR, ide.curC, ch);
  if (!k.typed.empty()) ideTouch(ide, ide.curR);   // the hand wrote here
  if (k.back && !selEdit) {
    const auto [br, bc] = ideBackAt(ide, ide.curR, ide.curC);
    ide.curR = br;
    ide.curC = bc;
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
          ideTouch(ide, r);
        } else {
          int cutn = 0;                        // up to four honest spaces
          while (cutn < 4 && cutn < static_cast<int>(l.size()) &&
                 l[static_cast<size_t>(cutn)] == ' ')
            ++cutn;
          if (cutn > 0) { l.erase(0, static_cast<size_t>(cutn)); ideTouch(ide, r); }
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
        ideTouch(ide, ide.curR);
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
        if (block->size() > 1)                   // the census rides the boiler
          ideTouchShift(ide, ide.curR + 1,
                        static_cast<int>(block->size()) - 1);
        for (size_t i = 1; i < block->size(); ++i)
          L.insert(L.begin() + ide.curR + static_cast<long>(i), (*block)[i]);
        L[static_cast<size_t>(ide.curR) + block->size() - 1] += tail;
        for (size_t i = 0; i < block->size(); ++i)
          ideTouch(ide, ide.curR + static_cast<int>(i));  // the boiler touched
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
          ideTouch(ide, ide.curR);
        } else {
          if (!(ide.lastTyping && quick)) idePushUndo(ide, "tab");
          else ide.redo.clear();
          std::string& cur2 = L[static_cast<size_t>(ide.curR)];
          cur2.insert(static_cast<size_t>(std::min(ide.curC, static_cast<int>(cur2.size()))),
                      4, ' ');
          ide.curC += 4;
          ideTouch(ide, ide.curR);
          ide.lastTyping = true;
          ide.lastBack = false;
        }
      }
    }
  }
  if (k.enter) {
    // the single hand's split speaks the SAME law the crew speaks
    const auto [er, ec] = ideEnterAt(ide, ide.curR, ide.curC);
    ide.curR = er;
    ide.curC = ec;
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
  if (k.up || k.sUp) {
    // the fold walks rows (the eye's law); the identity walks lines
    if (!ideVisualMove(ide, -1)) --ide.curR;
  }
  if (k.down || k.sDown) {
    if (!ideVisualMove(ide, +1)) ++ide.curR;
  }
  if (k.aLeft || k.sLeft) --ide.curC;
  if (k.aRight || k.sRight) ++ide.curC;
  if (k.wLeft) ideWordBack(ide);             // word hops move the cursor only —
  if (k.wRight) ideWordFwd(ide);             // the document never hears about it
  if (k.sWLeft) ideWordBack(ide);            // the word hops with the anchor
  if (k.sWRight) ideWordFwd(ide);            // riding — the selection grows
  if (k.home) {
    // the honest home: the hand's first breath lands on the line's
    // first non-blank; already there, the head; already there, back —
    // the three-way toggle the honest editors speak
    const std::string& hl = L[static_cast<size_t>(ide.curR)];
    const size_t first = hl.find_first_not_of(" \t");
    const int fnb = first == std::string::npos
                        ? 0
                        : static_cast<int>(first);
    ide.curC = ide.curC == fnb ? 0 : fnb;
  }
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
    // the single hand's delete speaks the SAME law the crew speaks
    const auto [dr, dc] = ideDelAt(ide, ide.curR, ide.curC);
    ide.curR = dr;
    ide.curC = dc;
  }
  if (k.transpose) {                         // ctrl+T: the two neighbors
                                             // trade places — the typo's
                                             // honest fix
    ideSelClear(ide);                        // the trade is the frame's own
    if (ide.lines[static_cast<size_t>(ide.curR)].size() >= 2) {
      idePushUndo(ide, "transpose");         // one honest step back
      ideTranspose(ide);
      ide.dirty = true;                      // the game hears about it
      ide.idle = 0;
    }
  }
  if (k.caseCycle) {                         // ctrl+U: the word's coat —
                                             // whisper, SHOUT, Title. The
                                             // seat never moves; press
                                             // again for the next coat.
    if (const auto sel = ideSelRange(ide)) { // a live span: EVERY word
                                             // held whole takes its coat
      const auto plans = ideCasePlanSelection(ide, *sel);
      if (!plans.empty()) {
        idePushUndo(ide, "case cycle");      // one step back for the span
        for (const auto& [r, p] : plans) ideCaseApply(ide, r, p);
        ide.dirty = true;
        ide.idle = 0;
      }
      ideSelClear(ide);                      // the breath is the frame's own
    } else if (ide.crew.empty()) {
      if (ideCycleCase(ide)) {
        ide.dirty = true;                    // the game hears about it
        ide.idle = 0;
      }
    } else {
      // many hands, one breath: every hand thinks its own coat first,
      // then all the paints land behind ONE shared undo step. Two
      // hands on one word think from the SAME text, so the word takes
      // one coat, not two — replace is its own idempotence.
      std::vector<std::pair<int, IdeCasePlan>> plans;
      if (const auto p = ideCasePlanAt(ide, ide.curR, ide.curC))
        plans.emplace_back(ide.curR, *p);
      for (const auto& [r, c] : ide.crew)
        if (const auto p = ideCasePlanAt(ide, r, c))
          plans.emplace_back(r, *p);
      if (!plans.empty()) {
        idePushUndo(ide, "case cycle");      // one step back for the crew
        for (const auto& [r, p] : plans) ideCaseApply(ide, r, p);
        ide.dirty = true;
        ide.idle = 0;
      }
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
      ideTouchShift(ide, r1 + 1, count);     // the census rides them
      for (int r = r1 + 1; r <= r1 + count; ++r)
        ideTouch(ide, r);                    // the copies are the fresh work
      ide.curR += count;
      if (ide.anchorR >= 0) ide.anchorR += count;   // the selection rides
    } else {
      // copy BEFORE inserting: the insert may reallocate the buffer
      const std::string cur = L[static_cast<size_t>(ide.curR)];
      L.insert(L.begin() + ide.curR + 1, cur);
      ideMarkShift(ide, ide.curR + 1, 1);    // pins beneath the copy slide
      ideTouchShift(ide, ide.curR + 1, 1);   // the census rides them
      ++ide.curR;                            // the copy takes your place
      ideTouch(ide, ide.curR);               // and it is the fresh work
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
      ideTouch(ide, ide.curR);               // the bite is a touch
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
    if (to > ide.curC) {
      cur.erase(static_cast<size_t>(ide.curC),
                static_cast<size_t>(to - ide.curC));
      ideTouch(ide, ide.curR);               // the bite is a touch
    }
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
          ideTouch(ide, r);
        } else {
          const size_t at = first == std::string::npos ? l.size() : first;
          l.insert(l.begin() + static_cast<long>(at), pre.begin(), pre.end());
          ideTouch(ide, r);
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
        ideTouch(ide, ide.curR);
      } else {
        // plain code: the prefix lands after the leading whitespace
        const size_t at = first == std::string::npos ? cur.size() : first;
        cur.insert(cur.begin() + static_cast<long>(at), pre.begin(), pre.end());
        ide.curC += static_cast<int>(pre.size());
        ideTouch(ide, ide.curR);
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
