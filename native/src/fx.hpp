// dxn3 native — the beauty pack (C++23): a deterministic parallax
// starfield, seeded per scene name. Same scene, same sky, every run —
// screenshots and sessions agree because nothing here is random.
#pragma once

#include <string_view>
#include <vector>

#include "tui.hpp"

namespace dxn3 {

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
