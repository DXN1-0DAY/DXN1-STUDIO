// dxn3 native — ANSI truecolor terminal renderer (C++23).
// The playfield paints into a half-block grid: one terminal cell renders
// two world pixels vertically (U+2580 UPPER HALF BLOCK, fg=top bg=bottom),
// giving 2x vertical resolution and buttery 24-bit color. Text overlays
// (signs, HUD) are stamped as UTF-8 codepoints so arrows and words stay crisp.
#pragma once
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace dxn3 {

using RGB = std::uint32_t;              // 0xRRGGBB

constexpr RGB rgb(std::uint8_t r, std::uint8_t g, std::uint8_t b) {
  return (RGB(r) << 16) | (RGB(g) << 8) | RGB(b);
}
RGB parseHex(std::string_view hex, RGB fallback);   // "#rrggbb" -> RGB
RGB lerpColor(RGB a, RGB b, float t);               // gradient fills

class Screen {
public:
  struct Span {                         // UTF-8 text stamped onto char grid
    int col = 0, row = 0;
    std::string text;                   // UTF-8, one codepoint per cell
    RGB fg = rgb(255, 255, 255);
  };

  int cols = 80, rows = 24;             // terminal size in cells
  int playRows() const { return rows - 2; }   // HUD row + help row
  int halfRows() const { return playRows() * 2; }

  void resize(int c, int r);
  void clear(RGB bg);                   // fill the whole grid
  void px(float sx, float sy, RGB c);   // plot world pixel (nearest)
  void rect(float x0, float y0, float x1, float y1, RGB c);
  void rectGradient(float x0, float y0, float x1, float y1, RGB top, RGB bottom);
  void frame(float x0, float y0, float x1, float y1, RGB c);  // 1px outline
  void text(int col, int row, std::string_view utf8, RGB fg);
  void hud(int score, std::string_view time, std::string_view msg);
  void help(std::string_view line);
  std::string flush();                  // whole frame as one ANSI string

private:
  std::vector<RGB> grid_;               // cols * halfRows
  std::vector<Span> spans_;
  static void emitColor(std::string& out, RGB fg, RGB bg, RGB& lastFg, RGB& lastBg);
  static std::string codepointAt(std::string_view s, size_t& i);
};

} // namespace dxn3
