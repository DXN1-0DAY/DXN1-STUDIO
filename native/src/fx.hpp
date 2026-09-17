// dxn3 native — the beauty pack (C++23): a deterministic parallax
// starfield, seeded per scene name. Same scene, same sky, every run —
// screenshots and sessions agree because nothing here is random.
#pragma once

#include <algorithm>
#include <cmath>
#include <string_view>
#include <vector>

#include "tui.hpp"

namespace dxn3 {

// The turn: a body's rotation about its own center, shared by the
// terminal raster and the PNG poster so both rasters always agree.
// rot lives on the wire in degrees (spin is deg/s); radians stay in here.
struct Turn {
  static constexpr float PI = 3.14159265358979f;
  float cs = 1, sn = 0, cx = 0, cy = 0;
  Turn(float deg, float cx_, float cy_)
      : cs(std::cos(deg * PI / 180.f)), sn(std::sin(deg * PI / 180.f)),
        cx(cx_), cy(cy_) {}
  // a screen point, carried back into the body's unrotated frame
  float toLocalX(float wx, float wy) const {
    return cx + (wx - cx) * cs + (wy - cy) * sn;
  }
  float toLocalY(float wx, float wy) const {
    return cy - (wx - cx) * sn + (wy - cy) * cs;
  }
  // the rotated corners' extent — the loop bounds for a raster sweep
  void extent(float x0, float y0, float x1, float y1,
              float& bx0, float& by0, float& bx1, float& by1) const {
    const float hw = (x1 - x0) / 2.f, hh = (y1 - y0) / 2.f;
    bx0 = by0 = 1e9f;
    bx1 = by1 = -1e9f;
    for (int i = 0; i < 4; ++i) {
      const float px = cx + ((i & 1) ? hw : -hw);
      const float py = cy + ((i & 2) ? hh : -hh);
      const float rx = cx + (px - cx) * cs - (py - cy) * sn;
      const float ry = cy + (px - cx) * sn + (py - cy) * cs;
      bx0 = std::min(bx0, rx);
      by0 = std::min(by0, ry);
      bx1 = std::max(bx1, rx);
      by1 = std::max(by1, ry);
    }
  }
};

struct Star {
  float x = 0;        // 0..1 across the sky tile
  float y = 0;        // 0..1 down the viewport
  float size = 1;     // 1..2 px
  float tw = 2;       // twinkle frequency (rad/s)
  RGB tint = rgb(226, 232, 240);
};

// FNV-1a — stable across runs, platforms and compilers.
inline std::uint32_t hashSeed(std::string_view s) {
  std::uint32_t h = 2166136261u;
  for (unsigned char c : s) {
    h ^= c;
    h *= 16777619u;
  }
  return h ? h : 1u;                    // never zero (xorshift seed)
}

inline std::vector<Star> buildStars(std::uint32_t seed, int count) {
  std::uint32_t st = seed ^ 0x9E3779B9u;
  auto next = [&st] {
    st ^= st << 13;
    st ^= st >> 17;
    st ^= st << 5;
    return st;
  };
  static const RGB tints[3] = {
      rgb(226, 232, 240),   // moon white
      rgb(199, 210, 254),   // periwinkle
      rgb(254, 249, 195),   // star gold
  };
  std::vector<Star> out;
  out.reserve(static_cast<size_t>(count));
  for (int i = 0; i < count; ++i) {
    Star s;
    s.x = static_cast<float>(next() % 100000) / 100000.f;
    s.y = static_cast<float>(next() % 100000) / 100000.f;
    s.size = (next() % 4 == 0) ? 2.f : 1.f;
    s.tw = 1.2f + static_cast<float>(next() % 1000) / 1000.f * 2.8f;
    s.tint = tints[next() % 3];
    out.push_back(s);
  }
  return out;
}

} // namespace dxn3
