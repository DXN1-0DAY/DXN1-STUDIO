// dxn3 native — ANSI truecolor terminal renderer (C++23).
// The playfield paints into a half-block grid: one terminal cell renders
// two world pixels vertically (U+2580 UPPER HALF BLOCK, fg=top bg=bottom),
// giving 2x vertical resolution and buttery 24-bit color. Text overlays
// (signs, HUD) are stamped as UTF-8 codepoints so arrows and words stay crisp.
#pragma once
#include <charconv>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace dxn3 {

using RGB = std::uint32_t;              // 0xRRGGBB

constexpr RGB rgb(std::uint8_t r, std::uint8_t g, std::uint8_t b) {
  return (RGB(r) << 16) | (RGB(g) << 8) | RGB(b);
}

// pure color math — header-only so every binary shares one truth
inline RGB parseHex(std::string_view hex, RGB fallback) {
  if (hex.size() < 7 || hex[0] != '#') return fallback;
  unsigned v = 0;
  auto [p, ec] = std::from_chars(hex.data() + 1, hex.data() + 7, v, 16);
  if (ec != std::errc{}) return fallback;
  return v & 0xFFFFFF;
}

inline RGB lerpColor(RGB a, RGB b, float t) {
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  const int ar = a >> 16 & 0xFF, ag = a >> 8 & 0xFF, ab = a & 0xFF;
  const int br = b >> 16 & 0xFF, bg = b >> 8 & 0xFF, bb = b & 0xFF;
  return rgb(static_cast<std::uint8_t>(ar + (br - ar) * t),
             static_cast<std::uint8_t>(ag + (bg - ag) * t),
             static_cast<std::uint8_t>(ab + (bb - ab) * t));
}

class Screen {
public:
  struct Span {                         // UTF-8 text stamped onto char grid
    int col = 0, row = 0;
    std::string text;                   // UTF-8, one codepoint per cell
    RGB fg = rgb(255, 255, 255);
    RGB bg = 0;                         // when bgOn, text paints its own rail
    bool bgOn = false;
  };

  int cols = 80, rows = 24;             // terminal size in cells
  int playRows() const { return rows - 2; }   // HUD row + help row
  int halfRows() const { return playRows() * 2; }

  void resize(int c, int r);
  void clear(RGB bg);                   // fill the whole grid
  // braille mode: the world renders at 2×2 dots per half-block pixel and
  // flush() composes U+2800.. braille cells — 4× the dots, smooth edges
  void setBraille(bool on) {
    if (braille_ == on) return;
    braille_ = on;
    resize(cols, rows);                 // re-derive the buffer
  }
  bool braille() const { return braille_; }
  // render INTO a sub-region: all px/rect/text writes translate and clamp
  // to the pane — the IDE hosts the live game view beside the editor.
  void setView(int x0, int y0, int x1, int y1) {  // x in cols; y in text rows
    vx0_ = x0; vx1_ = x1;
    vy0_ = y0 * 2;                                // grid pixels: 2 per row
    vy1_ = (y1 + 1) * 2 - 1;
  }
  void unclip() { vx0_ = 0; vy0_ = 0; vx1_ = -1; vy1_ = -1; }
  void px(float sx, float sy, RGB c);   // plot world pixel (nearest)
  void pxDot(float wx, float wy, RGB c);// plot ONE dot (braille sub-px)
  RGB at(int gx, int gy) const;         // read a grid pixel (0 outside)
  void rect(float x0, float y0, float x1, float y1, RGB c);
  void rectGradient(float x0, float y0, float x1, float y1, RGB top, RGB bottom);
  void frame(float x0, float y0, float x1, float y1, RGB c);  // 1px outline
  void text(int col, int row, std::string_view utf8, RGB fg);
  void textBg(int col, int row, std::string_view utf8, RGB fg, RGB bg);  // chip text
  void railBg(int row, RGB c);          // paint a full text-rail background
  void hud(int score, std::string_view time, std::string_view msg);
  void help(std::string_view line);
  std::string flush();                  // whole frame as one ANSI string

private:
  std::vector<RGB> grid_;               // cols*dots × halfRows*dots
  std::vector<Span> spans_;
  bool braille_ = false;
  RGB bg_ = 0;                          // the last cleared background
  int vx0_ = 0, vy0_ = 0, vx1_ = -1, vy1_ = -1;   // view region (off = full)
  int dotX() const;                     // dots per world px (braille: 2)
  int dotY() const;
  static void emitColor(std::string& out, RGB fg, RGB bg, RGB& lastFg, RGB& lastBg);
  static std::string codepointAt(std::string_view s, size_t& i);
};

} // namespace dxn3
