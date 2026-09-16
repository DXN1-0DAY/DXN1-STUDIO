// dxn3 native — truecolor renderer implementation (C++23).
// Two compositions from one world buffer:
//   half-block: 1 world px per cell column, 2 per row — the classic face
//   braille:    2×2 dots per world px, composed into U+2800.. cells —
//               four times the dots, smooth edges, no more chunky pixels
// The pure color math (parseHex, lerpColor) lives in tui.hpp so the
// selftest binary shares it without linking the whole Screen.
#include "tui.hpp"

#include <algorithm>
#include <cstdio>
#include <map>

namespace dxn3 {

int Screen::dotX() const { return braille_ ? 2 : 1; }
int Screen::dotY() const { return braille_ ? 2 : 1; }

void Screen::resize(int c, int r) {
  cols = c; rows = r;
  grid_.assign(static_cast<size_t>(cols) * dotX() * halfRows() * dotY(), 0);
  spans_.clear();
}

void Screen::clear(RGB bg) {
  bg_ = bg;
  if (vx1_ >= 0) {                          // view mode: clear only the pane
    const int x0 = vx0_ * dotX(), x1 = (vx1_ + 1) * dotX();
    const int y0 = vy0_ * dotY(), y1 = (vy1_ + 1) * dotY();
    const int bw = cols * dotX();
    for (int y = y0; y < y1 && y < halfRows() * dotY(); ++y) {
      auto* row = &grid_[static_cast<size_t>(y) * bw];
      for (int x = x0; x < x1 && x < bw; ++x) row[x] = bg;
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
  const int wx = static_cast<int>(sx), wy = static_cast<int>(sy);
  if (vx1_ >= 0 && (wx < vx0_ || wx > vx1_ || wy < vy0_ || wy > vy1_)) return;
  const int bw = cols * dotX();
  const int x0 = wx * dotX(), y0 = wy * dotY();
  for (int dy = 0; dy < dotY(); ++dy) {
    const int y = y0 + dy;
    if (y < 0 || y >= halfRows() * dotY()) continue;
    auto* row = &grid_[static_cast<size_t>(y) * bw];
    for (int dx = 0; dx < dotX(); ++dx) {
      const int x = x0 + dx;
      if (x < 0 || x >= bw) continue;
      row[x] = c;
    }
  }
}

void Screen::pxDot(float wx, float wy, RGB c) {
  const int bw = cols * dotX(), bh = halfRows() * dotY();
  const int x = static_cast<int>(wx * dotX());
  const int y = static_cast<int>(wy * dotY());
  if (vx1_ >= 0 && (x / dotX() < vx0_ || x / dotX() > vx1_ ||
                    y / dotY() < vy0_ || y / dotY() > vy1_)) return;
  if (x < 0 || x >= bw || y < 0 || y >= bh) return;
  grid_[static_cast<size_t>(y) * bw + x] = c;
}

RGB Screen::at(int gx, int gy) const {
  const int bw = cols * dotX();
  const int x0 = gx * dotX(), y0 = gy * dotY();
  unsigned r = 0, g = 0, b = 0;
  int n = 0;
  for (int dy = 0; dy < dotY(); ++dy) {
    const int y = y0 + dy;
    if (y < 0 || y >= halfRows() * dotY()) continue;
    for (int dx = 0; dx < dotX(); ++dx) {
      const int x = x0 + dx;
      if (x < 0 || x >= bw) continue;
      const RGB c = grid_[static_cast<size_t>(y) * bw + x];
      r += c >> 16 & 0xFF; g += c >> 8 & 0xFF; b += c & 0xFF;
      ++n;
    }
  }
  if (n == 0) return 0;
  return static_cast<RGB>((r / n) << 16 | (g / n) << 8 | (b / n));
}

void Screen::rect(float x0, float y0, float x1, float y1, RGB c) {
  const int dsx = dotX(), dsy = dotY();
  const int bw = cols * dsx, bh = halfRows() * dsy;
  int ax = std::max(0, static_cast<int>(x0) * dsx);
  int ay = std::max(0, static_cast<int>(y0) * dsy);
  int bx = std::min(bw, (static_cast<int>(x1) + 1) * dsx);
  int by = std::min(bh, (static_cast<int>(y1) + 1) * dsy);
  if (vx1_ >= 0) {                          // clip to the view pane
    ax = std::max(ax, vx0_ * dsx);
    bx = std::min(bx, (vx1_ + 1) * dsx);
    ay = std::max(ay, vy0_ * dsy);
    by = std::min(by, (vy1_ + 1) * dsy);
  }
  for (int y = ay; y < by; ++y) {
    auto* row = &grid_[static_cast<size_t>(y) * bw];
    for (int x = ax; x < bx; ++x) row[x] = c;
  }
}

void Screen::rectGradient(float x0, float y0, float x1, float y1, RGB top, RGB bottom) {
  const int dsx = dotX(), dsy = dotY();
  const int bw = cols * dsx, bh = halfRows() * dsy;
  int ay = std::max(0, static_cast<int>(y0) * dsy);
  int by = std::min(bh, (static_cast<int>(y1) + 1) * dsy);
  if (vx1_ >= 0) {
    ay = std::max(ay, vy0_ * dsy);
    by = std::min(by, (vy1_ + 1) * dsy);
  }
  const float h = std::max(1.f, y1 - y0);
  int ax = std::max(0, static_cast<int>(x0) * dsx);
  int bx = std::min(bw, (static_cast<int>(x1) + 1) * dsx);
  if (vx1_ >= 0) {
    ax = std::max(ax, vx0_ * dsx);
    bx = std::min(bx, (vx1_ + 1) * dsx);
  }
  const float anchor = y0;
  for (int y = ay; y < by; ++y) {
    const float t = (static_cast<float>(y) / dsy - anchor) / h;
    const RGB c = lerpColor(top, bottom, t);
    auto* row = &grid_[static_cast<size_t>(y) * bw];
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
    if (vx1_ >= 0 && (gy < vy0_ || gy > vy1_)) continue;
    const int bw = cols * dotX();
    auto* line = &grid_[static_cast<size_t>(gy * dotY()) * bw];
    const int x0 = (vx1_ >= 0 ? vx0_ : 0) * dotX();
    const int x1 = ((vx1_ >= 0 ? vx1_ : cols - 1) + 1) * dotX();
    for (int x = x0; x < x1 && x < bw; ++x) line[x] = c;
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

  if (braille_) {
    // compose each play cell from its 2×4 dot block. A dot is "on" when
    // it differs from the scene background; the majority on-color is the
    // cell's fg, the quiet color is its bg.
    const int bw = cols * 2;
    static const unsigned char BIT[4][2] = {
        {0x01, 0x08}, {0x02, 0x10}, {0x04, 0x20}, {0x40, 0x80}};
    std::string out = "\x1b[H\x1b[?25l";
    RGB lastFg = 0xFFFFFFFF, lastBg = 0xFFFFFFFF;
    auto near = [](RGB a, RGB b) {
      const int dr = static_cast<int>(a >> 16 & 0xFF) - static_cast<int>(b >> 16 & 0xFF);
      const int dg = static_cast<int>(a >> 8 & 0xFF) - static_cast<int>(b >> 8 & 0xFF);
      const int db = static_cast<int>(a & 0xFF) - static_cast<int>(b & 0xFF);
      return dr * dr + dg * dg + db * db < 900;    // ~30 per channel
    };
    for (int row = 0; row < rows; ++row) {
      if (row > 0) out += "\r\n";
      for (int col = 0; col < cols; ++col) {
        const OCell& o = over[static_cast<size_t>(row) * cols + col];
        if (o.on) {
          emitColor(out, o.fg, o.bgOn ? o.bg : bg_, lastFg, lastBg);
          out += o.ch;
          continue;
        }
        if (row == 0 || row == rows - 1) {         // text rails
          const RGB rail = at(col, std::min(row * 2, halfRows() - 1));
          emitColor(out, rail, rail, lastFg, lastBg);
          out += ' ';
          continue;
        }
        unsigned mask = 0;
        std::map<RGB, int> onColors;
        RGB bgDot = bg_;
        for (int dr = 0; dr < 4; ++dr)
          for (int dc = 0; dc < 2; ++dc) {
            const int x = col * 2 + dc;
            const int y = row * 4 + dr;
            const RGB c = (x < bw && y < halfRows() * 2)
                              ? grid_[static_cast<size_t>(y) * bw + x]
                              : bg_;
            if (near(c, bg_)) { bgDot = c; continue; }
            mask |= BIT[dr][dc];
            ++onColors[c];
          }
        if (mask == 0) {
          emitColor(out, bgDot, bgDot, lastFg, lastBg);
          out += ' ';
          continue;
        }
        RGB fg = bg_;
        int best = 0;
        for (const auto& [c, n] : onColors)
          if (n > best) { best = n; fg = c; }
        emitColor(out, fg, bg_, lastFg, lastBg);
        out += static_cast<char>(0xE2);
        out += static_cast<char>(0xA0 | (mask >> 6));
        out += static_cast<char>(0x80 | (mask & 0x3F));
      }
    }
    out += "\x1b[0m";
    return out;
  }

  static const char* BLOCK = "\xe2\x96\x80";   // U+2580 upper half block
  std::string out = "\x1b[H\x1b[?25l";
  RGB lastFg = 0xFFFFFFFF, lastBg = 0xFFFFFFFF;

  for (int row = 0; row < rows; ++row) {
    if (row > 0) out += "\r\n";
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
