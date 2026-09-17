// dxn3 native — the screenshot raster (C++23): the scene rendered into
// a real 960x540 pixel framebuffer and hand-encoded as a PNG (zero
// deps). Same starfield, same art rules as the terminal — just more
// pixels. Header-only so the shell and the selftest share one raster.
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "spark.hpp"
#include "tui.hpp"
#include "fx.hpp"
#include "png.hpp"

namespace dxn3 {

inline std::string shootPNG(const std::string& path, const Game& g) {
  namespace fs = std::filesystem;
  const int W = 960, H = 540;
  const auto& sc = g.scene;
  // poster framing: a screenshot is a map — fit the whole scene, not
  // just the hero's neighborhood
  const float ww = std::max(320.f, g.worldRight() + 160);
  const float wh = std::max(240.f, g.worldBottom() + 160);
  const float z = std::clamp(std::min(W / ww, static_cast<float>(H) / wh),
                             0.3f, 4.f);
  const RGB bg = parseHex(sc.bg, rgb(11, 14, 26));
  // frame on the world: a poster centers the map itself, edges and all
  float camX = g.worldRight() / 2.f, camY = g.worldBottom() / 2.f;
  if (g.worldRight() <= 0 || g.worldBottom() <= 0) {
    camX = sc.camera.x; camY = sc.camera.y;
  }

  std::vector<std::uint32_t> px(static_cast<size_t>(W) * H);
  // sky gradient — the top leans into the dark, the bottom breathes
  for (int y = 0; y < H; ++y) {
    const float t = static_cast<float>(y) / H;
    const RGB row = lerpColor(lerpColor(bg, 0x000000, 0.35f),
                              lerpColor(bg, 0xFFFFFF, 0.10f), t);
    auto* line = &px[static_cast<size_t>(y) * W];
    for (int x = 0; x < W; ++x) line[x] = row;
  }

  // the deterministic starfield — parallax on x, twinkle on time
  const auto stars = buildStars(hashSeed(sc.name), 220);
  const float tile = 600.f;
  for (size_t i = 0; i < stars.size(); ++i) {
    const auto& st = stars[i];
    const float depth = (i % 3 == 0) ? 0.5f : 0.22f;
    float sxp = std::fmod(st.x * tile - camX * depth, tile);
    if (sxp < 0) sxp += tile;
    if (sxp >= W) continue;
    const int x0 = static_cast<int>(sxp);
    const int y0 = std::min(H - 1, static_cast<int>(st.y * H * 0.9f));
    const float twk = 0.30f + 0.45f *
        (0.5f + 0.5f * std::sin(g.time * st.tw + static_cast<float>(i) * 1.7f));
    const RGB c = lerpColor(px[static_cast<size_t>(y0) * W + x0], st.tint, twk);
    const int s = static_cast<int>(st.size);
    for (int dy = 0; dy < s; ++dy)
      for (int dx = 0; dx < s; ++dx)
        if (x0 + dx < W && y0 + dy < H)
          px[static_cast<size_t>(y0 + dy) * W + x0 + dx] = c;
  }

  auto sx = [&](float wx) { return (wx - camX) * z + W / 2.f; };
  auto sy = [&](float wy) { return (wy - camY) * z + H / 2.f; };
  auto fillRect = [&](float x0, float y0, float x1, float y1, RGB c) {
    const int ax = std::max(0, static_cast<int>(x0));
    const int ay = std::max(0, static_cast<int>(y0));
    const int bx = std::min(W, static_cast<int>(x1) + 1);
    const int by = std::min(H, static_cast<int>(y1) + 1);
    for (int y = ay; y < by; ++y) {
      auto* line = &px[static_cast<size_t>(y) * W];
      for (int x = ax; x < bx; ++x) line[x] = c;
    }
  };
  auto fillGradient = [&](float x0, float y0, float x1, float y1, RGB top, RGB bot) {
    const int ay = std::max(0, static_cast<int>(y0));
    const int by = std::min(H, static_cast<int>(y1) + 1);
    const float hgt = std::max(1.f, y1 - y0);
    for (int y = ay; y < by; ++y) {
      const RGB c = lerpColor(top, bot, (y - y0) / hgt);
      const int ax = std::max(0, static_cast<int>(x0));
      const int bx = std::min(W, static_cast<int>(x1) + 1);
      auto* line = &px[static_cast<size_t>(y) * W];
      for (int x = ax; x < bx; ++x) line[x] = c;
    }
  };

  for (const auto& e : sc.entities) {
    if (!e.alive) continue;
    const float x0 = sx(e.x), y0 = sy(e.y);
    const float x1 = x0 + e.w * z - 1, y1 = y0 + e.h * z - 1;
    RGB c1 = parseHex(e.color, rgb(139, 92, 246));
    if (e.alpha < 1.f)                   // the ghost the poster shows too
      c1 = lerpColor(bg, c1, std::clamp(e.alpha, 0.f, 1.f));
    if (e.flash > 0)                     // the flash the terminal sees too
      c1 = lerpColor(c1, 0xFFFFFF, std::min(1.f, e.flash));
    if (x1 < 0 || x0 > W || y1 < 0 || y0 > H) continue;
    // frame against the void: dark entities get a lighter edge so the
    // night sky never swallows the level geometry
    const int lum = (c1 >> 16 & 0xFF) * 299 + (c1 >> 8 & 0xFF) * 587 + (c1 & 0xFF) * 114;
    const RGB edge = lum < 90000 ? lerpColor(c1, 0xFFFFFF, 0.28f)
                                 : lerpColor(c1, 0x000000, 0.45f);

    // the glow: the terminal raster's law, kept. A glowing disc breathes
    // a real ring (blended, soft); every other shape wears the coin's
    // rect aura. Painted before the body so the middle is covered —
    // and the shape test matches the terminal's `disc` exactly, so the
    // two rasters never disagree about where the halo goes.
    if (e.glow > 0) {
      const bool ring =
          e.shape == "circle" || e.shape == "ellipse" || e.tag == "coin";
      const RGB lightC = lerpColor(c1, 0xFFFFFF, 0.45f);
      if (ring) {
        const float rw = (x1 - x0) / 2.f + e.glow;
        const float rh = (y1 - y0) / 2.f + e.glow;
        if (rw > 0 && rh > 0) {
          const float cx = (x0 + x1) / 2.f, cy = (y0 + y1) / 2.f;
          const int dxa = std::max(0, static_cast<int>(x0 - e.glow) - 1);
          const int dxb = std::min(W - 1, static_cast<int>(x1 + e.glow) + 1);
          const int dya = std::max(0, static_cast<int>(y0 - e.glow) - 1);
          const int dyb = std::min(H - 1, static_cast<int>(y1 + e.glow) + 1);
          for (int py = dya; py <= dyb; ++py) {
            auto* line = &px[static_cast<size_t>(py) * W];
            const float ty = (py + 0.5f - cy) / rh;
            for (int pxx = dxa; pxx <= dxb; ++pxx) {
              const float tx = (pxx + 0.5f - cx) / rw;
              const float k2 = tx * tx + ty * ty;
              if (k2 > 1.f) continue;
              // radial falloff — the terminal raster's law, kept
              line[pxx] = lerpColor(line[pxx], lightC, 0.5f * (1.f - k2));
            }
          }
        }
      } else {
        // a stepped aura: three nested rects, brighter toward the body,
        // each blended against the pixel it lands on (stars survive)
        const auto base = [&px, W, H](int x, int y) -> RGB {
          return px[std::clamp(y, 0, H - 1) * W + std::clamp(x, 0, W - 1)];
        };
        fillRect(x0 - e.glow, y0 - e.glow, x1 + e.glow, y1 + e.glow,
                 lerpColor(base(static_cast<int>(x0), static_cast<int>(y0)),
                           lightC, 0.14f));
        fillRect(x0 - e.glow * 0.66f, y0 - e.glow * 0.66f,
                 x1 + e.glow * 0.66f, y1 + e.glow * 0.66f,
                 lerpColor(base(static_cast<int>(x0), static_cast<int>(y0)),
                           lightC, 0.22f));
        fillRect(x0 - e.glow * 0.33f, y0 - e.glow * 0.33f,
                 x1 + e.glow * 0.33f, y1 + e.glow * 0.33f,
                 lerpColor(base(static_cast<int>(x0), static_cast<int>(y0)),
                           lightC, 0.32f));
      }
    }

    if (e.tag == "sign") {                                // plaque rails
      fillRect(x0, y0, x1, y0 + 2, edge);
      fillRect(x0, y1 - 2, x1, y1, edge);
      continue;
    }
    if (e.tag == "coin") {                                // halo keeps its glow
      const float glow = 5.f;
      fillRect(x0 - glow, y0 - glow, x1 + glow, y1 + glow,
               lerpColor(px[std::max(0, static_cast<int>(y0)) * W +
                             std::clamp(static_cast<int>(x0), 0, W - 1)], c1, 0.14f));
    }
    const bool disc = e.shape == "circle" || e.shape == "ellipse" ||
                      e.tag == "coin";
    if (disc) {                                           // a real disc, per pixel
      const float rw = (x1 - x0) / 2.f, rh = (y1 - y0) / 2.f;
      if (rw <= 0 || rh <= 0) continue;
      const float cx = (x0 + x1) / 2.f, cy = (y0 + y1) / 2.f;
      const int dxa = std::max(0, static_cast<int>(x0) - 1);
      const int dxb = std::min(W - 1, static_cast<int>(x1) + 1);
      const int dya = std::max(0, static_cast<int>(y0) - 1);
      const int dyb = std::min(H - 1, static_cast<int>(y1) + 1);
      for (int py = dya; py <= dyb; ++py) {
        auto* line = &px[static_cast<size_t>(py) * W];
        const float ty = (py + 0.5f - cy) / rh;
        for (int pxx = dxa; pxx <= dxb; ++pxx) {
          const float tx = (pxx + 0.5f - cx) / rw;
          const float k2 = tx * tx + ty * ty;
          if (k2 > 1.f) continue;
          line[pxx] = k2 > 0.80f ? edge : c1;             // the rim keeps its edge
        }
      }
      continue;
    }
    if (e.tag == "spike") {                               // triangle profile
      if (e.rot != 0) {                                   // a turned spike
        const float cx = (x0 + x1) / 2.f, cy = (y0 + y1) / 2.f;
        const Turn turn(e.rot, cx, cy);
        float bx0, by0, bx1, by1;
        turn.extent(x0, y0, x1, y1, bx0, by0, bx1, by1);
        const int ax = std::max(0, static_cast<int>(bx0) - 1);
        const int ay = std::max(0, static_cast<int>(by0) - 1);
        const int bx = std::min(W - 1, static_cast<int>(bx1) + 1);
        const int by = std::min(H - 1, static_cast<int>(by1) + 1);
        const float rw = x1 - x0, rh = y1 - y0, hw = rw / 2.f;
        for (int py = ay; py <= by; ++py) {
          auto* line = &px[static_cast<size_t>(py) * W];
          for (int pxx = ax; pxx <= bx; ++pxx) {
            const float wx = pxx + 0.5f, wy = py + 0.5f;
            const float lx = turn.toLocalX(wx, wy);
            const float ly = turn.toLocalY(wx, wy);
            const float t = (ly - y0) / rh;               // 0 top → 1 apex
            if (t < -0.01f || t > 1.01f) continue;
            const float half = (1.f - t) * hw;
            const float axl = std::abs(lx - cx);
            if (axl > half + 0.5f) continue;
            line[pxx] = (half - axl < 1.2f || t > 0.92f) ? edge : c1;
          }
        }
        continue;
      }
      const int steps = std::max(2, static_cast<int>(y1 - y0) + 1);
      for (int s = 0; s < steps; ++s) {
        const float t = steps <= 1 ? 0.f : static_cast<float>(s) / (steps - 1);
        const float shrink = t * (e.w * z - 1) / 2.f;
        fillRect(x0 + shrink, y0 + s, x1 - shrink, y0 + s, c1);
      }
      continue;
    }
    if (e.tag == "goal") {                                // striped flag
      const RGB stripe = rgb(250, 204, 21);
      const float band = std::max(1.f, (x1 - x0 + 1) / 4);
      float x = x0;
      int i = 0;
      while (x <= x1) {
        fillRect(x, y0, std::min(x + band - 1, x1), y1, i % 2 ? stripe : c1);
        x += band; ++i;
      }
      continue;
    }
    if (e.rot != 0) {                                     // the body truly turns
      const float cx = (x0 + x1) / 2.f, cy = (y0 + y1) / 2.f;
      const Turn turn(e.rot, cx, cy);
      float bx0, by0, bx1, by1;
      turn.extent(x0, y0, x1, y1, bx0, by0, bx1, by1);
      const int ax = std::max(0, static_cast<int>(bx0) - 1);
      const int ay = std::max(0, static_cast<int>(by0) - 1);
      const int bx = std::min(W - 1, static_cast<int>(bx1) + 1);
      const int by = std::min(H - 1, static_cast<int>(by1) + 1);
      RGB c2 = parseHex(e.color2, c1);
      if (e.alpha < 1.f)                 // the gradient wears the air too
        c2 = lerpColor(bg, c2, std::clamp(e.alpha, 0.f, 1.f));
      if (e.flash > 0)
        c2 = lerpColor(c2, 0xFFFFFF, std::min(1.f, e.flash));
      const float rw = x1 - x0, rh = y1 - y0;
      for (int py = ay; py <= by; ++py) {
        auto* line = &px[static_cast<size_t>(py) * W];
        for (int pxx = ax; pxx <= bx; ++pxx) {
          const float wx = pxx + 0.5f, wy = py + 0.5f;
          const float axl = turn.toLocalX(wx, wy) - x0;
          const float ayl = turn.toLocalY(wx, wy) - y0;
          if (axl < -0.5f || axl > rw + 0.5f ||
              ayl < -0.5f || ayl > rh + 0.5f) continue;
          RGB c = (e.fill == "gradient" && !e.color2.empty())
                      ? lerpColor(c1, c2,
                                  std::clamp(ayl / std::max(1.f, rh), 0.f, 1.f))
                      : c1;
          if (std::min(std::min(axl, rw - axl), std::min(ayl, rh - ayl)) < 1.2f)
            c = edge;
          line[pxx] = c;
        }
      }
      continue;
    }
    if (e.fill == "gradient" && !e.color2.empty())
      fillGradient(x0, y0, x1, y1, c1, parseHex(e.color2, c1));
    else
      fillRect(x0, y0, x1, y1, c1);
    if (e.tag == "player") {                              // visor line
      const RGB visor = lerpColor(c1, 0x000000, 0.55f);
      fillRect(x0 + 1, y0 + (y1 - y0) * 0.25f, x1 - 1, y0 + (y1 - y0) * 0.4f, visor);
    }
    fillRect(x0, y0, x1, y0, edge);                       // crisp 1px frame
    fillRect(x0, y1, x1, y1, edge);
    fillRect(x0, y0, x0, y1, edge);
    fillRect(x1, y0, x1, y1, edge);
  }

  // vignette — the edges fall asleep, the center sings
  for (int y = 0; y < H; ++y) {
    const float dyn = (y - H / 2.f) / (H / 2.f);
    auto* line = &px[static_cast<size_t>(y) * W];
    for (int x = 0; x < W; ++x) {
      const float dxn = (x - W / 2.f) / (W / 2.f);
      const float d = std::sqrt(dxn * dxn + dyn * dyn) / 1.4142f;
      line[x] = lerpColor(0x000000, line[x], 1.f - 0.22f * d * d);
    }
  }

  std::error_code fec;
  const fs::path parent = fs::path(path).parent_path();
  if (!parent.empty() && !fs::exists(parent) &&
      !fs::create_directories(parent, fec))
    return "cannot create " + parent.string() + ": " + fec.message();
  return writePng(path, W, H, px);
}

} // namespace dxn3
