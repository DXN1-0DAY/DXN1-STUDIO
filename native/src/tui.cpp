// dxn3 native — truecolor renderer implementation (C++23).
// The pure color math (parseHex, lerpColor) lives in tui.hpp so the
// selftest binary shares it without linking the whole Screen.
#include "tui.hpp"

#include <algorithm>
#include <cstdio>

namespace dxn3 {

void Screen::resize(int c, int r) {
  cols = c; rows = r;
  grid_.assign(static_cast<size_t>(cols) * halfRows(), 0);
  spans_.clear();
}

void Screen::clear(RGB bg) {
  if (vx1_ >= 0) {                          // view mode: clear only the pane
    for (int y = vy0_; y <= vy1_ && y < halfRows(); ++y) {
      auto* row = &grid_[static_cast<size_t>(y) * cols];
      for (int x = vx0_; x <= vx1_ && x < cols; ++x) row[x] = bg;
    }
    // drop only the spans INSIDE the pane — the editor's text, drawn
    // earlier this frame outside the view, must survive the game's clear
    spans_.erase(std::remove_if(spans_.begin(), spans_.end(),
                                [this](const Span& s) {
                                  const int gy0 = s.row * 2, gy1 = gy0 + 1;
                                  const int gx0 = s.col;
                                  const int gx1 = s.col +
                                      static_cast<int>(s.text.size()) - 1;
                                  return gx1 >= vx0_ && gx0 <= vx1_ &&
                                         gy1 >= vy0_ && gy0 <= vy1_;
                                }),
                 spans_.end());
    return;
  }
  std::fill(grid_.begin(), grid_.end(), bg);
  spans_.clear();
}

void Screen::px(float sx, float sy, RGB c) {
  const int x = static_cast<int>(sx), y = static_cast<int>(sy);
  if (vx1_ >= 0 && (x < vx0_ || x > vx1_ || y < vy0_ || y > vy1_)) return;
  if (x < 0 || x >= cols || y < 0 || y >= halfRows()) return;
  grid_[static_cast<size_t>(y) * cols + x] = c;
}

RGB Screen::at(int gx, int gy) const {
  if (gx < 0 || gx >= cols || gy < 0 || gy >= halfRows()) return 0;
  return grid_[static_cast<size_t>(gy) * cols + gx];
}

void Screen::rect(float x0, float y0, float x1, float y1, RGB c) {
  int ax = std::max(0, static_cast<int>(x0));
  int ay = std::max(0, static_cast<int>(y0));
  int bx = std::min(vx1_ >= 0 ? vx1_ + 1 : cols, static_cast<int>(x1) + 1);
  int by = std::min(vy1_ >= 0 ? vy1_ + 1 : halfRows(), static_cast<int>(y1) + 1);
  ax = std::min(ax, cols); ay = std::min(ay, halfRows());
  bx = std::min(bx, cols); by = std::min(by, halfRows());
  for (int y = ay; y < by; ++y) {
    auto* row = &grid_[static_cast<size_t>(y) * cols];
    for (int x = ax; x < bx; ++x) row[x] = c;
  }
}

void Screen::rectGradient(float x0, float y0, float x1, float y1, RGB top, RGB bottom) {
  const int ay = std::max(0, static_cast<int>(y0));
  const int by = std::min(vy1_ >= 0 ? vy1_ + 1 : halfRows(), static_cast<int>(y1) + 1);
  const float h = std::max(1.f, y1 - y0);
  const int ax = std::max(0, static_cast<int>(x0));
  const int bx = std::min(vx1_ >= 0 ? vx1_ + 1 : cols, static_cast<int>(x1) + 1);
  const float anchor = static_cast<float>(static_cast<int>(y0));
  for (int y = ay; y < by; ++y) {
    const float t = (static_cast<float>(y) - anchor) / h;
    const RGB c = lerpColor(top, bottom, t);
    auto* row = &grid_[static_cast<size_t>(y) * cols];
    for (int x = ax; x < bx; ++x) row[x] = c;
  }
}

void Screen::frame(float x0, float y0, float x1, float y1, RGB c) {
  rect(x0, y0, x1, y0, c);
  rect(x0, y1, x1, y1, c);
  rect(x0, y0, x0, y1, c);
  rect(x1, y0, x1, y1, c);
}

std::string Screen::codepointAt(std::string_view s, size_t& i) {
  const size_t start = i;
  ++i;                                   // first byte always counts
  while (i < s.size() && (s[i] & 0xC0) == 0x80) ++i;   // continuation bytes
  return std::string(s.substr(start, i - start));
}

void Screen::text(int col, int row, std::string_view utf8, RGB fg) {
  if (row < 0 || row >= rows) return;
  int c = col;
  const int r = row;
  if (r < 0 || r >= rows) return;
  for (size_t i = 0; i < utf8.size() && c < cols;) {
    if (vx1_ < 0 || (c >= vx0_ && c <= vx1_))
      spans_.push_back({c, r, codepointAt(utf8, i), fg, 0, false});
    else codepointAt(utf8, i);          // clipped cell: still consume UTF-8
    ++c;
  }
}

void Screen::textBg(int col, int row, std::string_view utf8, RGB fg, RGB bg) {
  if (row < 0 || row >= rows) return;
  int c = col;
  const int r = row;
  if (r < 0 || r >= rows) return;
  for (size_t i = 0; i < utf8.size() && c < cols;) {
    if (vx1_ < 0 || (c >= vx0_ && c <= vx1_))
      spans_.push_back({c, r, codepointAt(utf8, i), fg, bg, true});
    ++c;
  }
}

void Screen::railBg(int row, RGB c) {
  if (row < 0 || row >= rows) return;
  for (int sub = 0; sub < 2; ++sub) {
    const int gy = row * 2 + sub;
    if (gy >= halfRows()) break;
    if (vy1_ >= 0 && (gy < vy0_ || gy > vy1_)) continue;
    auto* line = &grid_[static_cast<size_t>(gy) * cols];
    const int x0 = vx1_ >= 0 ? vx0_ : 0;
    const int x1 = vx1_ >= 0 ? vx1_ : cols - 1;
    for (int x = x0; x <= x1; ++x) line[x] = c;
  }
}

void Screen::hud(int score, std::string_view time, std::string_view msg) {
  char buf[64];
  std::snprintf(buf, sizeof buf, " SCORE %d", score);
  std::string line = buf;
  line += "   TIME ";
  line += time;
  text(0, 0, line, rgb(167, 139, 250));
  if (!msg.empty()) {
    const int col = std::max(0, cols - static_cast<int>(msg.size()) - 1);
    text(col, 0, msg, rgb(250, 204, 21));
  }
}

void Screen::help(std::string_view line) {
  text(0, rows - 1, line, rgb(110, 118, 140));
}

std::string Screen::flush() {
  // overlay lookup per char-cell
  struct OCell { std::string ch; RGB fg; RGB bg = 0; bool bgOn = false; bool on = false; };
  std::vector<OCell> over(static_cast<size_t>(cols) * rows);
  for (const auto& s : spans_) {
    if (s.row < 0 || s.row >= rows || s.col < 0 || s.col >= cols) continue;
    over[static_cast<size_t>(s.row) * cols + s.col] = {s.text, s.fg, s.bg, s.bgOn, true};
  }

  static const char* BLOCK = "\xe2\x96\x80";   // U+2580 upper half block
  std::string out = "\x1b[H\x1b[?25l";
  RGB lastFg = 0xFFFFFFFF, lastBg = 0xFFFFFFFF;

  for (int row = 0; row < rows; ++row) {
    if (row > 0) out += "\r\n";
    // HUD row and help row are plain text rows (grid rows 0 and last stay bg)
    for (int col = 0; col < cols; ++col) {
      const OCell& o = over[static_cast<size_t>(row) * cols + col];
      const size_t gi = static_cast<size_t>(row) * 2 * cols + col;
      const size_t gb = gi + static_cast<size_t>(cols);
      const RGB top = row * 2 < halfRows() ? grid_[gi] : 0;
      const RGB bot = row * 2 + 1 < halfRows() ? grid_[gb] : 0;
      if (o.on) {
        emitColor(out, o.fg, o.bgOn ? o.bg : bot, lastFg, lastBg);
        out += o.ch;
        continue;
      }
      if (row == 0 || row == rows - 1) {       // text rails: bg color only
        emitColor(out, bot, bot, lastFg, lastBg);
        out += ' ';
        continue;
      }
      if (top == bot) {
        emitColor(out, top, top, lastFg, lastBg);
        out += ' ';
      } else {
        emitColor(out, top, bot, lastFg, lastBg);
        out += BLOCK;
      }
    }
  }
  out += "\x1b[0m";
  return out;
}

void Screen::emitColor(std::string& out, RGB fg, RGB bg, RGB& lastFg, RGB& lastBg) {
  if (fg == lastFg && bg == lastBg) return;
  char buf[48];
  if (fg != lastFg) {
    std::snprintf(buf, sizeof buf, "\x1b[38;2;%u;%u;%um",
                  fg >> 16 & 0xFF, fg >> 8 & 0xFF, fg & 0xFF);
    out += buf;
    lastFg = fg;
  }
  if (bg != lastBg) {
    std::snprintf(buf, sizeof buf, "\x1b[48;2;%u;%u;%um",
                  bg >> 16 & 0xFF, bg >> 8 & 0xFF, bg & 0xFF);
    out += buf;
    lastBg = bg;
  }
}

} // namespace dxn3
