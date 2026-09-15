// dxn3 native — truecolor renderer implementation (C++23).
// The pure color math (parseHex, lerpColor) lives in tui.hpp so the
// selftest binary shares it without linking the whole Screen.
#include "tui.hpp"

#include <cstdio>

namespace dxn3 {

void Screen::resize(int c, int r) {
  cols = c; rows = r;
  grid_.assign(static_cast<size_t>(cols) * halfRows(), 0);
  spans_.clear();
}

void Screen::clear(RGB bg) {
  std::fill(grid_.begin(), grid_.end(), bg);
  spans_.clear();
}

void Screen::px(float sx, float sy, RGB c) {
  const int x = static_cast<int>(sx), y = static_cast<int>(sy);
  if (x < 0 || x >= cols || y < 0 || y >= halfRows()) return;
  grid_[static_cast<size_t>(y) * cols + x] = c;
}

RGB Screen::at(int gx, int gy) const {
  if (gx < 0 || gx >= cols || gy < 0 || gy >= halfRows()) return 0;
  return grid_[static_cast<size_t>(gy) * cols + gx];
}

void Screen::rect(float x0, float y0, float x1, float y1, RGB c) {
  const int ax = std::max(0, static_cast<int>(x0));
  const int ay = std::max(0, static_cast<int>(y0));
  const int bx = std::min(cols, static_cast<int>(x1) + 1);
  const int by = std::min(halfRows(), static_cast<int>(y1) + 1);
  for (int y = ay; y < by; ++y) {
    auto* row = &grid_[static_cast<size_t>(y) * cols];
    for (int x = ax; x < bx; ++x) row[x] = c;
  }
}

void Screen::rectGradient(float x0, float y0, float x1, float y1, RGB top, RGB bottom) {
  const int ay = std::max(0, static_cast<int>(y0));
  const int by = std::min(halfRows(), static_cast<int>(y1) + 1);
  const float h = std::max(1.f, y1 - y0);
  for (int y = ay; y < by; ++y) {
    const float t = (y - y0) / h;
    const RGB c = lerpColor(top, bottom, t);
    const int ax = std::max(0, static_cast<int>(x0));
    const int bx = std::min(cols, static_cast<int>(x1) + 1);
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
  for (size_t i = 0; i < utf8.size() && c < cols;) {
    spans_.push_back({c, row, codepointAt(utf8, i), fg, 0, false});
    ++c;
  }
}

void Screen::textBg(int col, int row, std::string_view utf8, RGB fg, RGB bg) {
  if (row < 0 || row >= rows) return;
  int c = col;
  for (size_t i = 0; i < utf8.size() && c < cols;) {
    spans_.push_back({c, row, codepointAt(utf8, i), fg, bg, true});
    ++c;
  }
}

void Screen::railBg(int row, RGB c) {
  if (row < 0 || row >= rows) return;
  for (int sub = 0; sub < 2; ++sub) {
    const int gy = row * 2 + sub;
    if (gy >= halfRows()) break;
    auto* line = &grid_[static_cast<size_t>(gy) * cols];
    for (int x = 0; x < cols; ++x) line[x] = c;
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
