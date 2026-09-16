// dxn3 native — the studio shell (C++23).
// A truecolor terminal studio: PLAY mode runs the Spark engine core;
// INSPECT mode (Tab) pauses and shows the entity table. Raw-mode input,
// fixed-timestep loop, goal transitions chain scenes like the JS runtime.
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <poll.h>
#include <print>
#include <string>
#include <vector>
#include <termios.h>
#include <unistd.h>
#include <sys/ioctl.h>

#include "spark.hpp"
#include "tui.hpp"
#include "version.hpp"
#include "fx.hpp"
#include "png.hpp"
#include "cmd.hpp"
#include "shot.hpp"
#include "logo32.hpp"
#include "host.hpp"

#include <sstream>

using dxn3::RGB;

namespace {

std::atomic<bool> g_stop{false};
termios g_orig{};
bool g_raw = false;

void restoreTerminal() {
  if (g_raw) {
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &g_orig);
    std::fputs("\x1b[0m\x1b[?25h\x1b[?1049l", stdout);
    std::fflush(stdout);
    g_raw = false;
  }
}

void onSignal(int) { g_stop = true; }

void enterScreen() {
  std::fputs("\x1b[?1049h\x1b[2J", stdout);
  std::fflush(stdout);
}

bool termSize(int& cols, int& rows) {
  winsize ws{};
  if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) != 0 || ws.ws_col == 0) {
    cols = 80; rows = 24;
    return false;
  }
  cols = ws.ws_col; rows = ws.ws_row;
  return true;
}

// which key grammar is live this frame
enum class Mode { Play, File, Cmd, Ide };

// drain stdin; return the keys seen this frame
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
  bool toPlay = false;                         // IDE: tab — play your game
  bool braille = false;                        // b — toggle the dot renderer
  std::string typed;                           // printable chars this frame
};

Keys pollKeys(Mode mode) {
  Keys k;
  char buf[256];
  while (true) {
    // 0-timeout poll: never block the loop between keystrokes (raw mode
    // read() with VMIN=1 would otherwise freeze the game mid-air)
    pollfd pfd{STDIN_FILENO, POLLIN, 0};
    if (::poll(&pfd, 1, 0) <= 0 || !(pfd.revents & POLLIN)) break;
    ssize_t n = ::read(STDIN_FILENO, buf, sizeof buf);
    if (n <= 0) break;                    // EOF or fd trouble
    for (ssize_t i = 0; i < n; ++i) {
      const char c = buf[i];
      if (c == '\x1b') {
        // arrow keys arrive as ESC [ A/B/C/D in one read, usually
        if (i + 2 < n && buf[i + 1] == '[' && mode != Mode::Cmd) {
          switch (buf[i + 2]) {
            case 'A':
              if (mode == Mode::Ide) k.up = true;
              else if (mode == Mode::File) k.scroll -= 1;
              else k.jump = true;
              break;
            case 'B':
              if (mode == Mode::Ide) k.down = true;
              else if (mode == Mode::File) k.scroll += 1;
              break;
            case 'C':
              if (mode == Mode::Ide) k.aRight = true;
              else if (mode == Mode::File) k.scroll += 10;
              else k.right = true;
              break;
            case 'D':
              if (mode == Mode::Ide) k.aLeft = true;
              else if (mode == Mode::File) k.scroll -= 10;
              else k.left = true;
              break;
          }
          i += 2;
        } else {
          k.esc = true;                     // bare ESC
          if (mode == Mode::Play) k.quit = true;   // …which quits in play/inspect
        }
        continue;
      }
      if (mode == Mode::Ide) {               // IDE: the editor owns typing
        if (c == '\r' || c == '\n') k.enter = true;
        else if (c == '\t') { k.typed += "    "; }        // tab = 4 spaces
        else if (c == 0x7f || c == '\b') k.back = true;
        else if (c == 0x13) k.ctrlS = true;               // Ctrl+S — save+run
        else if (c == 0x12) k.ctrlR = true;               // Ctrl+R — run
        else if (static_cast<unsigned char>(c) >= 0x20) k.typed += c;
      } else if (mode == Mode::File) {       // FILE VIEW: every letter is text
        if (c == '\r' || c == '\n') k.enter = true;
        else if (c == '\t') { /* inert */ }
        else if (c == 0x7f || c == '\b') k.back = true;
        else if (c == 'j' || c == 'J') k.scroll += 1;
        else if (c == 'k' || c == 'K') k.scroll -= 1;
        else if (c == '/') k.slash = true;
        else if (c == 'q' || c == 'Q') k.quit = true;
        else if (static_cast<unsigned char>(c) >= 0x20) k.typed += c;
      } else if (mode == Mode::Cmd) {        // command bar: typing is typing
        if (c == '\r' || c == '\n') k.enter = true;
        else if (c == 0x7f || c == '\b') k.back = true;
        else if (static_cast<unsigned char>(c) >= 0x20) k.typed += c;
      } else {                               // PLAY / INSPECT keys
        if (c == 0x13) k.ctrlS = true;
        else if (c == 0x12) k.ctrlR = true;
        else if (c == 'a' || c == 'A') k.left = true;
        else if (c == 'd' || c == 'D') k.right = true;
        else if (c == 'w' || c == 'W' || c == ' ') k.jump = true;
        else if (c == 'r' || c == 'R') k.reset = true;
        else if (c == 'f' || c == 'F') k.fit = true;
        else if (c == '+' || c == '=') k.zoomIn = true;
        else if (c == '-' || c == '_') k.zoomOut = true;
        else if (c == '\t') k.inspect = true;
        else if (c == 'e' || c == 'E') k.viewFile = true;
        else if (c == 'b' || c == 'B') k.braille = true;
        else if (c == ':') k.cmd = true;
        else if (c == 'p' || c == 'P') k.shot = true;
        else if (c == 'q' || c == 'Q') k.quit = true;
      }
    }
  }
  return k;
}

std::string fmtTime(float t) {
  char buf[32];
  const int total = static_cast<int>(t);
  std::snprintf(buf, sizeof buf, "%d:%04.1f", total / 60, t - (total / 60) * 60);
  return buf;
}

// ---- FILE VIEW: the loaded scene's source, line numbers, / search

void drawFile(dxn3::Screen& scr, const std::vector<std::string>& lines,
              int top, const std::string& query, const std::string& path) {
  scr.clear(dxn3::rgb(9, 10, 18));
  const RGB dim = dxn3::rgb(110, 118, 140);
  const RGB txt = dxn3::rgb(220, 222, 232);
  const RGB hit = dxn3::rgb(250, 204, 21);
  scr.railBg(0, dxn3::rgb(22, 12, 36));
  scr.railBg(scr.rows - 1, dxn3::rgb(13, 8, 23));
  scr.textBg(0, 0, " FILE ", dxn3::rgb(233, 213, 255), dxn3::rgb(88, 28, 135));
  {
    std::string head = " " + path + " — " +
                       std::to_string(static_cast<int>(lines.size())) + " lines";
    if (scr.cols > static_cast<int>(head.size()) + 16)
      scr.text(7, 0, head, dxn3::rgb(196, 181, 253));
  }
  const std::string search = query.empty() ? " / to search"
                                           : " /" + query + "  (enter to run)";
  if (scr.cols > 40)
    scr.text(scr.cols - static_cast<int>(search.size()), 0, search,
             query.empty() ? dim : hit);
  const int maxRow = scr.rows - 1;
  for (int row = 1; row < maxRow; ++row) {
    const int li = top + row - 1;
    if (li >= static_cast<int>(lines.size())) break;
    char num[16];
    std::snprintf(num, sizeof num, "%4d ", li + 1);
    scr.text(0, row, num, dim);
    scr.text(5, row, lines[li],
             (!query.empty() && lines[li].find(query) != std::string::npos)
                 ? hit : txt);
  }
}


// ---- SPLASH: the studio emblem, half-block rendered from logo32.hpp

void drawSplash(dxn3::Screen& scr, const dxn3::Game& g) {
  const RGB bg = dxn3::rgb(8, 6, 14);
  scr.clear(bg);
  const int n = dxn3::kLogoN;
  const int ox = (scr.cols - n) / 2;
  const int oy = std::max(1, (scr.rows - n / 2 - 5) / 2);
  for (int y = 0; y < n / 2; ++y)
    for (int x = 0; x < n; ++x) {
      const RGB top = dxn3::kLogo32[static_cast<size_t>(2 * y) * n + x];
      const RGB bot = dxn3::kLogo32[static_cast<size_t>(2 * y + 1) * n + x];
      if (!top && !bot) continue;           // let the night breathe through
      scr.px(static_cast<float>(ox + x), static_cast<float>((oy + y) * 2),
             top ? top : bg);
      scr.px(static_cast<float>(ox + x), static_cast<float>((oy + y) * 2 + 1),
             bot ? bot : bg);
    }
  const int ty = oy + n / 2 + 1;
  const std::string word = "DXN1 STUDIO ";
  const int wcol = (scr.cols - static_cast<int>(word.size()) - 1) / 2;
  scr.text(wcol, ty, word, dxn3::rgb(240, 238, 250));
  scr.text(wcol + static_cast<int>(word.size()), ty, "3", dxn3::rgb(168, 85, 247));
  const std::string sub =
      std::string("v") + dxn3::DXN3_VERSION + " · native core · c++23 · zero deps";
  scr.text((scr.cols - static_cast<int>(sub.size())) / 2, ty + 1, sub,
           dxn3::rgb(124, 58, 237));
  const std::string meta = "scene '" + g.scene.name + "' — " +
      std::to_string(g.scene.entities.size()) + " entities";
  scr.text((scr.cols - static_cast<int>(meta.size())) / 2, ty + 3, meta,
           dxn3::rgb(110, 118, 140));
  const std::string hint = "press any key to enter the studio";
  scr.text((scr.cols - static_cast<int>(hint.size())) / 2, ty + 4, hint,
           dxn3::rgb(76, 82, 100));
}

// shared status-rail furniture: brand chip + meter left, scene right

void drawRailChrome(dxn3::Screen& scr, const dxn3::Game& g) {
  scr.railBg(0, dxn3::rgb(22, 12, 36));
  scr.railBg(scr.rows - 1, dxn3::rgb(13, 8, 23));
  scr.textBg(0, 0, " DXN1 STUDIO 3 ", dxn3::rgb(10, 7, 16),
             dxn3::rgb(147, 51, 234));
  int coinsGot = 0;
  for (const auto& e : g.scene.entities)
    if (e.tag == "coin" && e.alive) ++coinsGot;
  const int total = g.coinsTotal();
  char meter[72];
  std::snprintf(meter, sizeof meter, " COINS %d/%d · SCORE %d · %s ",
                total - coinsGot, total, g.score, fmtTime(g.time).c_str());
  scr.text(16, 0, meter, dxn3::rgb(233, 229, 255));
  const std::string where = g.scene.name + " ";
  const int wcol = scr.cols - static_cast<int>(where.size());
  if (wcol > 16 + static_cast<int>(std::strlen(meter)) + 2)
    scr.text(wcol, 0, where, dxn3::rgb(196, 181, 253));
  if (g.msgT > 0 && !g.msg.empty()) {
    const int ccol = std::max(0, (scr.cols - static_cast<int>(g.msg.size())) / 2);
    const int mend = 16 + static_cast<int>(std::strlen(meter));
    if (ccol > mend + 1 && ccol < wcol - static_cast<int>(g.msg.size()))
      scr.text(ccol, 0, g.msg, dxn3::rgb(250, 204, 21));
  }
  const std::string tag =
      std::string(" DXN1 STUDIO 3 v") + dxn3::DXN3_VERSION + " ";
  if (scr.cols > 106)
    scr.text(scr.cols - static_cast<int>(tag.size()), scr.rows - 1, tag,
             dxn3::rgb(70, 60, 100));
}

void drawWorld(dxn3::Screen& scr, const dxn3::Game& g) {
  const auto& sc = g.scene;
  const float z = sc.camera.zoom;
  const int cols = scr.cols, hr = scr.halfRows();
  const RGB bg = dxn3::parseHex(sc.bg, dxn3::rgb(11, 14, 26));
  scr.clear(bg);

  float ox = 0, oy = 0;                                   // shake offset
  if (g.shakeT > 0 && g.shakeD > 0) {
    const float p = g.shakeP * (g.shakeT / g.shakeD);
    ox = ((std::rand() % 201) - 100) / 100.f * p;
    oy = ((std::rand() % 201) - 100) / 100.f * p;
  }
  auto sx = [&](float wx) { return (wx - sc.camera.x + ox) * z + cols / 2.f; };
  auto sy = [&](float wy) { return (wy - sc.camera.y + oy) * z + hr / 2.f; };

  // the sky, poster-grade: the live view gets the same vertical breath
  // as the PNG raster — dark up top, a little air at the bottom
  for (int gy = 0; gy < hr; ++gy) {
    const float t = static_cast<float>(gy) / std::max(1, hr - 1);
    const RGB row = dxn3::lerpColor(dxn3::lerpColor(bg, 0x000000, 0.35f),
                                    dxn3::lerpColor(bg, 0xFFFFFF, 0.10f), t);
    scr.rect(0, static_cast<float>(gy), static_cast<float>(cols - 1),
             static_cast<float>(gy), row);
  }

  // the sky: a deterministic starfield seeded by the scene name — same
  // scene, same sky, forever. Two parallax depths drift with the camera;
  // a slow sine twinkle keeps the sky alive without lying about it.
  const auto stars = dxn3::buildStars(dxn3::hashSeed(sc.name), 220);
  const float tile = 600.f;
  for (size_t i = 0; i < stars.size(); ++i) {
    const auto& st = stars[i];
    const float depth = (i % 3 == 0) ? 0.5f : 0.22f;
    float sxp = std::fmod(st.x * tile - sc.camera.x * depth, tile);
    if (sxp < 0) sxp += tile;
    if (sxp >= cols) continue;
    const float syp = st.y * hr;
    const float twk = 0.30f + 0.45f *
        (0.5f + 0.5f * std::sin(g.time * st.tw + static_cast<float>(i) * 1.7f));
    const RGB c = dxn3::lerpColor(bg, st.tint, twk);
    scr.rect(sxp, syp, sxp + st.size - 1.f, syp, c);
  }
  for (const auto& e : sc.entities) {
    if (!e.alive) continue;
    const float x0 = sx(e.x), y0 = sy(e.y);
    const float x1 = x0 + e.w * z - 1, y1 = y0 + e.h * z - 1;
    const RGB c1 = dxn3::parseHex(e.color, dxn3::rgb(139, 92, 246));
    const bool off = x1 < 0 || x0 > cols || y1 < 0 || y0 > hr;

    // the shape the author asked for — circles are real discs now,
    // triangles are general, text is text; tags layer decorations on top
    const bool disc = e.shape == "circle" || e.tag == "coin";
    const bool tri = e.shape == "tri" || e.shape == "triangle" || e.tag == "spike";
    const bool texty = e.shape == "text" || e.tag == "sign";
    const float cxm = (x0 + x1) / 2.f, cym = (y0 + y1) / 2.f;
    const int lum1 = (c1 >> 16 & 0xFF) * 299 + (c1 >> 8 & 0xFF) * 587 +
                     (c1 & 0xFF) * 114;
    const RGB edgeC = lum1 < 90000 ? dxn3::lerpColor(c1, 0xFFFFFF, 0.28f)
                                   : dxn3::lerpColor(c1, 0x000000, 0.45f);

    if (texty) {                                          // text plaque
      if (!off) {
        scr.rect(x0, y0, x1, y0 + 1, edgeC);              // plaque rails,
        scr.rect(x0, y1 - 1, x1, y1, edgeC);              // like the poster
        if (!e.text.empty()) {
          const int col = static_cast<int>(x0);
          const int row = static_cast<int>(y0) / 2;
          scr.text(col, row, e.text, c1);
        }
      }
      continue;
    }
    if (disc) {                                           // a real disc
      if (off) continue;
      if (e.tag == "coin") {                              // halo keeps its glow
        const float glow = 5.f;
        scr.rect(x0 - glow, y0 - glow, x1 + glow, y1 + glow,
                 dxn3::lerpColor(bg, c1, 0.14f));
      }
      const float rw = (x1 - x0) / 2.f, rh = (y1 - y0) / 2.f;
      if (rw <= 0 || rh <= 0) continue;
      const int ry0 = std::max(0, static_cast<int>(y0) - 1);
      const int ry1 = std::min(hr, static_cast<int>(y1) + 1);
      for (int ry = ry0; ry <= ry1; ++ry) {
        const float t = ((static_cast<float>(ry) + 0.5f) - cym) / rh;
        const float k = 1.f - t * t;
        if (k <= 0) continue;
        const float hw = rw * std::sqrt(k);
        scr.rect(cxm - hw, static_cast<float>(ry), cxm + hw,
                 static_cast<float>(ry), c1);
      }
      // rim light so discs hold their edge against the void
      for (int ry = ry0; ry <= ry1; ++ry) {
        const float t = ((static_cast<float>(ry) + 0.5f) - cym) / rh;
        const float k = 1.f - t * t;
        if (k <= 0.02f) continue;
        const float hw = rw * std::sqrt(k);
        scr.rect(cxm - hw, static_cast<float>(ry), cxm - hw,
                 static_cast<float>(ry), edgeC);
        scr.rect(cxm + hw, static_cast<float>(ry), cxm + hw,
                 static_cast<float>(ry), edgeC);
      }
      continue;
    }
    if (tri) {                                            // triangle profile
      if (off) continue;
      const int steps = std::max(2, static_cast<int>(y1 - y0) + 1);
      for (int s = 0; s < steps; ++s) {
        const float t = steps <= 1 ? 0 : static_cast<float>(s) / (steps - 1);
        const float shrink = t * (e.w * z - 1) / 2.f;
        scr.rect(x0 + shrink, y0 + s, x1 - shrink, y0 + s, c1);
      }
      continue;
    }
    if (e.tag == "goal") {                                // striped flag
      if (off) continue;
      const RGB stripe = dxn3::rgb(250, 204, 21);
      const float band = std::max(1.f, (x1 - x0 + 1) / 4);
      float x = x0;
      int i = 0;
      while (x <= x1) {
        scr.rect(x, y0, std::min(x + band - 1, x1), y1, i % 2 ? stripe : c1);
        x += band; ++i;
      }
      continue;
    }
    if (off) continue;
    if (e.fill == "gradient" && !e.color2.empty())
      scr.rectGradient(x0, y0, x1, y1, c1, dxn3::parseHex(e.color2, c1));
    else
      scr.rect(x0, y0, x1, y1, c1);
    // frame against the void: same rule as the PNG raster — dark
    // entities get a lighter edge so the night sky never eats them
    scr.frame(x0, y0, x1, y1, edgeC);
    if (e.tag == "player") {                              // visor line
      const RGB dark = dxn3::lerpColor(c1, 0, 0.55f);
      scr.rect(x0 + 1, y0 + (y1 - y0) * 0.25f, x1 - 1, y0 + (y1 - y0) * 0.4f, dark);
    }
  }
  // vignette — the edges fall asleep, the center sings (poster parity)
  for (int gy = 0; gy < hr; ++gy) {
    const float dyn = (gy - hr / 2.f) / (hr / 2.f);
    for (int gx = 0; gx < cols; ++gx) {
      const float dxn = (gx - cols / 2.f) / (cols / 2.f);
      const float d = std::sqrt(dxn * dxn + dyn * dyn) / 1.4142f;
      scr.px(static_cast<float>(gx), static_cast<float>(gy),
             dxn3::lerpColor(0x000000, scr.at(gx, gy), 1.f - 0.22f * d * d));
    }
  }
  if (g.flash > 0.02f)
    scr.rect(0, 0, cols - 1, hr - 1,
             dxn3::rgb(255, 255, static_cast<std::uint8_t>(255 * g.flash)));

  drawRailChrome(scr, g);
}

void drawInspect(dxn3::Screen& scr, const dxn3::Game& g) {
  const RGB bg = dxn3::rgb(9, 10, 18);
  scr.clear(bg);
  const RGB accent = dxn3::rgb(167, 139, 250);
  const RGB dim = dxn3::rgb(110, 118, 140);
  const RGB txt = dxn3::rgb(220, 222, 232);
  const RGB alt = dxn3::rgb(184, 182, 202);

  scr.railBg(0, dxn3::rgb(22, 12, 36));
  scr.railBg(scr.rows - 1, dxn3::rgb(13, 8, 23));
  scr.textBg(1, 0, " INSPECT ", dxn3::rgb(233, 213, 255), dxn3::rgb(88, 28, 135));
  scr.text(11, 0, g.scene.name + " — paused  (Tab resumes)", dxn3::rgb(196, 181, 253));
  const std::string vtag =
      std::string("dxn3 v") + dxn3::DXN3_VERSION + " ";
  if (scr.cols > 40)
    scr.text(scr.cols - static_cast<int>(vtag.size()), 0, vtag, dxn3::rgb(96, 84, 128));

  scr.text(1, 2, "ENTITY         TAG         X      Y      W    H    COLOR", dim);
  int row = 3;
  char line[96];
  for (const auto& e : g.scene.entities) {
    if (row >= scr.rows - 1) { scr.text(1, row, "…", dim); break; }
    std::snprintf(line, sizeof line, "%-14s %-11s %6.0f %6.0f %4.0f %4.0f  %s%s",
                  e.name.c_str(), e.tag.c_str(), e.x, e.y, e.w, e.h,
                  e.color.c_str(), e.alive ? "" : "  (gone)");
    scr.text(1, row, line, e.alive ? (row % 2 ? txt : alt) : dim);
    ++row;
  }
  char meta[96];
  std::snprintf(meta, sizeof meta,
                "gravity %.0f  magnet %.0fpx  zoom %.2f  next %s",
                g.scene.gravity, g.scene.magnet, g.scene.camera.zoom,
                g.scene.next.empty() ? "—" : g.scene.next.c_str());
  scr.text(1, scr.rows - 2, meta, accent);
}

} // namespace

// ═════════════════ the IDE: your code, our canvas ═════════════════
// You start with nothing. You write code — Python, JS, C++, ANY language —
// Ctrl+R runs it, and the viewport refreshes while you type. The engine
// renders, feeds input, detects hits; your code IS the game.

struct IdeState {
  bool open = false;
  std::vector<std::string> lines{" "};
  int curR = 0, curC = 0, top = 0;
  std::string path;                          // the script file
  bool dirty = true;                         // needs a (re)run
  double idle = 0;                           // typing pause → auto-run
  std::vector<std::string> console;          // engine notes + game prints
  std::string state = "new file — write code, Ctrl+R runs it";
  bool hostUp = false;
};

const char* STARTER = R"(# DXN1 STUDIO — your game starts here.
# edit anything — stop typing for a beat and the viewport refreshes LIVE.
# esc plays fullscreen · this starter is a tiny SHOOTER · sdk/ has docs:

from dxn3 import *
import random

ship  = rect("ship",  W // 2 - 6, H - 12, 12, 5, "#8b5cf6")
ship.tag = "ship"
enemy = circle("enemy", W // 3, 6, 10, 10, "#fb7185")
enemy.tag = "enemy"
hud   = label("hud", 2, 2, "SCORE 0")
score, shots = 0, 0

def on_key(k):                       # held keys each frame: left right space…
    global shots
    if k == "left":  ship.x = ship.x - 1
    if k == "right": ship.x = ship.x + 1
    if k == "space":
        shots += 1
        s = circle("shot" + str(shots), ship.x + 5, ship.y - 3, 3, 3, "#facc15")
        s.vy = -2.5
        s.tag = "shot"

def on_tick(dt2):                    # every frame, seconds since the last
    enemy.x = enemy.x + 0.3
    if enemy.x > W - 12: enemy.x = 2
    hud.text = "SCORE " + str(score)

def on_hit(a, b):                    # two tagged entities just overlapped
    global score
    if "shot" in (a.tag, b.tag) and "enemy" in (a.tag, b.tag):
        score += 10
        destroy((a if a.tag == "shot" else b).name)
        enemy.x = random.randint(2, W - 14)
        enemy.y = random.randint(2, H // 2)
        print("hit! score", score)

run()   # hands the loop to the studio — that is the whole engine.
)";

std::vector<std::string> starterLines() {
  std::vector<std::string> out;
  std::string s = STARTER;
  size_t pos;
  while ((pos = s.find('\n')) != std::string::npos) {
    out.push_back(s.substr(0, pos));
    s.erase(0, pos + 1);
  }
  if (!s.empty()) out.push_back(s);
  return out;
}

bool isScriptFile(const std::string& p) {
  static const char* exts[] = {".py", ".js", ".mjs", ".cpp", ".cc", ".cxx",
                               ".cs", ".rb", ".lua", ".pl", ".sh", ".ts"};
  for (const char* e : exts)
    if (p.size() > 4 && p.rfind(e) == p.size() - std::strlen(e)) return true;
  return false;
}

bool ideSave(IdeState& ide, std::string* err) {
  std::ofstream f(ide.path, std::ios::binary);
  if (!f) { if (err) *err = "cannot write " + ide.path; return false; }
  for (size_t i = 0; i < ide.lines.size(); ++i) {
    f << ide.lines[i];
    if (i + 1 < ide.lines.size()) f << '\n';
  }
  return true;
}

void ideKey(IdeState& ide, const Keys& k) {
  auto& L = ide.lines;
  if (ide.curR >= static_cast<int>(L.size())) ide.curR = static_cast<int>(L.size()) - 1;
  std::string& line = L[static_cast<size_t>(ide.curR)];
  for (const char ch : k.typed) {
    line.insert(line.begin() + std::min(ide.curC, static_cast<int>(line.size())), ch);
    ++ide.curC;
  }
  if (k.back) {
    if (ide.curC > 0) { line.erase(line.begin() + ide.curC - 1); --ide.curC; }
    else if (ide.curR > 0) {                       // join with previous line
      ide.curC = static_cast<int>(L[static_cast<size_t>(ide.curR - 1)].size());
      L[static_cast<size_t>(ide.curR - 1)] += line;
      L.erase(L.begin() + ide.curR);
      --ide.curR;
    }
  }
  if (k.enter) {
    std::string rest = line.substr(static_cast<size_t>(std::min(ide.curC, static_cast<int>(line.size()))));
    line.resize(static_cast<size_t>(std::min(ide.curC, static_cast<int>(line.size()))));
    L.insert(L.begin() + ide.curR + 1, rest);
    ++ide.curR;
    ide.curC = 0;
  }
  if (k.up) --ide.curR;
  if (k.down) ++ide.curR;
  if (k.aLeft) --ide.curC;
  if (k.aRight) ++ide.curC;
  ide.curR = std::clamp(ide.curR, 0, static_cast<int>(L.size()) - 1);
  ide.curC = std::clamp(ide.curC, 0, static_cast<int>(L[static_cast<size_t>(ide.curR)].size()));
}

// syntax tint: keywords purple, strings amber, comments gray — stamped
// over the base line so every language looks at home in the studio
void drawCodeLine(dxn3::Screen& scr, int col, int row, const std::string& s,
                  int maxCols) {
  const RGB base = dxn3::rgb(226, 232, 240);
  const RGB gray = dxn3::rgb(96, 104, 126);
  const RGB amber = dxn3::rgb(250, 204, 21);
  const RGB purple = dxn3::rgb(167, 139, 250);
  std::string vis = s.empty() ? " " : s;
  if (static_cast<int>(vis.size()) > maxCols) {
    vis = vis.substr(0, std::max(0, maxCols - 1)) + "…";
  }
  scr.text(col, row, vis, base);
  const std::string t = vis.substr(vis.find_first_not_of(" \t") == std::string::npos ? 0 : vis.find_first_not_of(" \t"));
  if (t.rfind("#", 0) == 0 || t.rfind("//", 0) == 0 || t.rfind("--", 0) == 0) {
    scr.text(col, row, vis, gray);
    return;
  }
  static const char* kws[] = {"def",  "function", "if",   "elif", "else",
                              "end",  "while",    "for",  "in",   "return",
                              "local", "var",    "let",  "and",  "or",
                              "not",  "true",     "false", "None", "null",
                              "nil",  "import",   "from", "class", "pass",
                              "break", "continue", "global", "new", "public",
                              "static", "void",   "int",  "float", "bool"};
  for (const char* kw : kws) {
    const std::string w = kw;
    size_t at = 0;
    while ((at = vis.find(w, at)) != std::string::npos) {
      const bool leftOk = at == 0 || !std::isalnum(static_cast<unsigned char>(vis[at - 1]));
      const size_t r = at + w.size();
      const bool rightOk = r >= vis.size() || !std::isalnum(static_cast<unsigned char>(vis[r]));
      if (leftOk && rightOk) scr.text(col + static_cast<int>(at), row, w, purple);
      at += w.size();
    }
  }
  for (size_t i = 0; i < vis.size(); ++i) {
    if (vis[i] == '"' || vis[i] == '\'') {
      const char q = vis[i];
      size_t j = i + 1;
      while (j < vis.size() && vis[j] != q) ++j;
      const std::string str = vis.substr(i, std::min(j + 1, vis.size()) - i);
      scr.text(col + static_cast<int>(i), row, str, amber);
      i = std::min(j + 1, vis.size() == 0 ? 0 : vis.size() - 1);
      if (j >= vis.size() - 1) break;
    }
  }
}

void drawIDE(dxn3::Screen& scr, IdeState& ide, const dxn3::Game& g, bool hostUp) {
  const int cols = scr.cols, rows = scr.rows;
  const RGB paneBg = dxn3::rgb(16, 12, 30);
  const RGB selBg = dxn3::rgb(30, 22, 52);

  const int consoleRows = 2;
  const int bodyTop = 1;
  const int bodyRows = rows - bodyTop - consoleRows;
  const bool split = cols >= 96;
  const int editW = split ? 46 : cols;

  // the live viewport FIRST: drawWorld clears the whole grid, so it owns
  // the frame — the editor, header and console paint over it after
  if (split) {
    scr.setView(editW, bodyTop, cols - 1, bodyTop + bodyRows - 1);
    drawWorld(scr, g);
    scr.unclip();
  }

  // header: brand + file + run state
  scr.railBg(0, dxn3::rgb(22, 12, 36));
  scr.textBg(0, 0, " DXN1 STUDIO — ENGINE ", dxn3::rgb(10, 7, 16),
             dxn3::rgb(147, 51, 234));
  const std::string file = ide.path + (ide.dirty ? " ●" : "");
  scr.text(24, 0, file, dxn3::rgb(233, 229, 255));
  const std::string st = (hostUp ? "● LIVE  " : "○ idle  ") + ide.state + " ";
  const int scol = cols - static_cast<int>(st.size());
  if (scol > 26) scr.text(scol, 0, st, hostUp ? dxn3::rgb(52, 211, 153) : dxn3::rgb(110, 118, 140));

  // the editor pane
  const int maxTop = std::max(0, static_cast<int>(ide.lines.size()) - bodyRows);
  ide.top = std::clamp(ide.top, 0, maxTop);
  if (ide.curR < ide.top) ide.top = ide.curR;
  if (ide.curR >= ide.top + bodyRows) ide.top = ide.curR - bodyRows + 1;
  scr.rect(0, static_cast<float>(bodyTop * 2),
           static_cast<float>(split ? editW - 1 : cols - 1),
           static_cast<float>((bodyTop + bodyRows) * 2), paneBg);
  for (int r = 0; r < bodyRows; ++r) {
    const int li = ide.top + r;
    if (li >= static_cast<int>(ide.lines.size())) break;
    const bool onCursor = li == ide.curR;
    char gutter[16];
    std::snprintf(gutter, sizeof gutter, "%3d ", li + 1);
    scr.text(0, bodyTop + r, gutter, dxn3::rgb(84, 72, 120));
    if (onCursor) scr.railBg(bodyTop + r, selBg);
    drawCodeLine(scr, 4, bodyTop + r, ide.lines[static_cast<size_t>(li)],
                 editW - 5);
  }
  // the cursor: inverse video on the exact cell
  if (ide.curR >= ide.top && ide.curR < ide.top + bodyRows) {
    const int row = bodyTop + (ide.curR - ide.top);
    const std::string& l = ide.lines[static_cast<size_t>(ide.curR)];
    const char ch = ide.curC < static_cast<int>(l.size()) ? l[static_cast<size_t>(ide.curC)] : ' ';
    scr.textBg(4 + ide.curC, row, std::string(1, ch), paneBg, dxn3::rgb(167, 139, 250));
  }

  // the console rail: the game's prints + engine notes, honestly shown
  const int c0 = rows - consoleRows;
  scr.railBg(c0, dxn3::rgb(10, 7, 18));
  scr.railBg(c0 + 1, dxn3::rgb(10, 7, 18));
  size_t n = ide.console.size();
  const std::string l1 = n >= 1 ? ide.console[n - 1] : "";
  const std::string l2 = n >= 2 ? ide.console[n - 2] : "";
  scr.text(1, c0, l1.substr(0, static_cast<size_t>(cols - 3)), dxn3::rgb(148, 156, 180));
  const std::string hint = " ctrl+r run · ctrl+s save · esc play · :scene <file> loads a demo ";
  scr.text(1, c0 + 1, hint.substr(0, static_cast<size_t>(cols - 3)), dxn3::rgb(84, 72, 120));
  if (!l2.empty())
    scr.text(cols - std::min(cols - 3, static_cast<int>(l2.size())) - 1, c0 + 1,
             l2.substr(0, static_cast<size_t>(std::min(cols - 3, static_cast<int>(l2.size())))),
             dxn3::rgb(84, 72, 120));
}

int main(int argc, char** argv) {
  std::signal(SIGINT, onSignal);
  std::signal(SIGTERM, onSignal);
  std::atexit(restoreTerminal);

  std::string scenePath = "scenes/playground.dxn1.json";
  std::string shotPath;
  bool wantShot = false, wantVersion = false, wantList = false;
  std::vector<std::string> hostOverride;          // --host-cmd: any language
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--scene" && i + 1 < argc) scenePath = argv[++i];
    else if (a == "--host-cmd" && i + 1 < argc) {
      std::istringstream iss(argv[++i]);
      std::string w;
      while (iss >> w) hostOverride.push_back(w);
    }
    else if (a == "--screenshot" && i + 1 < argc) { shotPath = argv[++i]; wantShot = true; }
    else if (a == "--list-scenes") wantList = true;
    else if (a == "--version" || a == "-v") wantVersion = true;
    else if (a == "--help" || a == "-h") {
      std::println("dxn3-native {} — DXN1 STUDIO 3: the engine for code and games\n"
                   "usage: dxn3-native                     the IDE — write a game, Ctrl+R runs it\n"
                   "       dxn3-native game.py             your game, any language (py/js/cpp/cs/…)\n"
                   "       dxn3-native --scene scenes/playground.dxn1.json    the demo campaign\n"
                   "       dxn3-native --host-cmd 'ruby game.rb'   any interpreter you have\n"
                   "       dxn3-native --list-scenes | --screenshot out.png | --version\n"
                   "keys:  ctrl+r run · ctrl+s save · esc play/back · a/d move · w jump\n"
                   "       tab inspect · e file · : commands · p screenshot · q quit\n"
                   "your game is a child process speaking JSON on stdio — see sdk/",
                   dxn3::DXN3_VERSION);
      return 0;
    }
    else if (!a.empty() && a[0] != '-') scenePath = a;
  }
  if (wantVersion) {
    std::println("dxn3-native {} — DXN1 STUDIO 3 (C++23, zero dependencies)",
                 dxn3::DXN3_VERSION);
    return 0;
  }
  if (wantList) {
    // what's installed: every .dxn1.json under scenes/, honestly parsed
    namespace fs = std::filesystem;
    std::println("dxn3 {} — scenes on this machine:", dxn3::DXN3_VERSION);
    std::vector<fs::path> found;
    std::error_code ec;
    for (const auto& dir : {fs::path("scenes"), fs::path(".")}) {
      if (!fs::exists(dir, ec)) continue;
      for (const auto& de : fs::directory_iterator(dir, ec))
        if (de.is_regular_file() &&
            de.path().extension() == ".json" &&
            de.path().string().find(".dxn1.") != std::string::npos)
          found.push_back(de.path());
      if (!found.empty()) break;          // scenes/ wins when it exists
    }
    if (found.empty()) {
      std::println("  (none — run from the repo root, or pass --scene)");
      return found.empty() ? 1 : 0;
    }
    for (const auto& p : found) {
      auto sc = dxn3::Game::loadScene(p.string());
      if (!sc) {
        std::println("  {:32s}  unreadable: {}", p.string(),
                     sc.error().detail);
        continue;
      }
      std::println("  {:32s}  '{}' — {} entities", p.string(),
                   sc->name, sc->entities.size());
    }
    return 0;
  }

  // ─── boot: the engine first. you start with nothing, you code, it runs.
  IdeState ide;
  dxn3::ScriptHost host;
  const std::string sdkDir = (std::filesystem::current_path() / "sdk").string();
  bool ideBoot = false;
  if (isatty(STDIN_FILENO) && !wantShot) {   // interactive? engine first.
    if (argc == 1) {                          // dxn3, no args → the engine IDE
      ideBoot = true;
      ide.path = "untitled.py";
      ide.lines = starterLines();
      ide.console.push_back("engine: you start with nothing — edit, then ctrl+r");
    } else if (!hostOverride.empty() || isScriptFile(scenePath)) {
      ideBoot = true;
      ide.path = scenePath;
      std::ifstream f(scenePath, std::ios::binary);
      if (f.good()) {
        std::string ln;
        while (std::getline(f, ln)) {
          if (!ln.empty() && ln.back() == '\r') ln.pop_back();
          ide.lines.push_back(ln);
        }
        if (ide.lines.empty()) ide.lines.push_back(" ");
        ide.console.push_back("engine: loaded " + scenePath);
      } else {
        ide.lines = starterLines();
        ide.console.push_back("engine: " + scenePath +
                              " is new — starter loaded, ctrl+s writes it");
      }
    }
  }

  dxn3::Scene bootScene;
  if (ideBoot) {
    bootScene.name = "untitled";
    bootScene.gravity = 0;
    bootScene.bg = "#0b0e1a";
  } else {
    auto loaded = dxn3::Game::loadScene(scenePath);
    if (!loaded) {
      std::println(stderr, "dxn3: cannot load '{}': {}", scenePath, loaded.error().detail);
      return 1;
    }
    bootScene = std::move(*loaded);
  }
  dxn3::Game game(std::move(bootScene));

  // headless screenshot: render the loaded scene and exit honestly
  if (wantShot) {
    const std::string err = dxn3::shootPNG(shotPath, game);
    if (!err.empty()) {
      std::println(stderr, "dxn3: {}", err);
      return 1;
    }
    std::println("screenshot → {} (960x540, scene '{}')", shotPath, game.scene.name);
    return 0;
  }

  bool inspect = false;
  int shotSeq = 0;
  bool cmdOpen = false;
  std::string cmdBuf, cmdErr;
  float cmdErrT = 0;
  auto defaultShot = [&]() {
    std::string base = game.scene.name.empty() ? "scene" : game.scene.name;
    for (char& ch : base) if (ch == ' ' || ch == '/') ch = '_';
    return "exports/" + base + "-" + std::to_string(++shotSeq) + ".png";
  };
  auto doShot = [&](std::string path) {
    if (path.empty()) path = defaultShot();
    const std::string err = dxn3::shootPNG(path, game);
    if (err.empty()) game.say("saved " + path, 2.2);
    else { cmdErr = err; cmdErrT = 3.5f; }
  };
  ide.open = ideBoot;
  int cols0 = 100, rows0 = 24;                // world size hint, refined live

  // the scenes on this machine, as bare stems — name resolution fuel
  auto sceneStems = []() {
    std::vector<std::string> stems;
    std::error_code ec;
    for (const auto& de : std::filesystem::directory_iterator("scenes", ec))
      if (de.is_regular_file(ec) && de.path().extension() == ".json" &&
          de.path().string().find(".dxn1.") != std::string::npos)
        stems.push_back(de.path().stem().string());
    std::sort(stems.begin(), stems.end());
    return stems;
  };

  // run the editor's code: save → host it → your game is live
  auto ideRun = [&]() {
    std::string err;
    if (!ideSave(ide, &err)) {
      ide.console.push_back("engine: " + err);
      ide.dirty = false;
      return;
    }
    std::vector<std::string> argv = hostOverride;
    if (argv.empty() && !dxn3::hostCommandFor(ide.path, argv, &err)) {
      ide.console.push_back("engine: " + err);
      ide.state = "cannot run " + ide.path;
      ide.dirty = false;
      return;
    }
    if (host.start(argv, cols0, (rows0 - 2) * 2, sdkDir, &err)) {
      ide.hostUp = true;
      ide.dirty = false;
      ide.state = "running " + ide.path;
      ide.console.push_back("engine: hosting " + argv[0] + " — your code is the game");
    } else {
      host.stop();
      ide.hostUp = false;
      ide.dirty = false;
      ide.console.push_back("engine: " + err);
      ide.state = "host failed";
    }
  };

  // the scene's own source, for FILE VIEW (e)
  std::vector<std::string> fileLines;
  {
    std::ifstream f(scenePath);
    std::string ln;
    while (std::getline(f, ln)) {
      if (!ln.empty() && ln.back() == '\r') ln.pop_back();
      fileLines.push_back(ln);
    }
  }
  bool fileView = false, searching = false;
  int fileTop = 0;
  std::string query;

  std::println("dxn3 native {} (C++23) — scene '{}' — {} entities — magnet {}px",
               dxn3::DXN3_VERSION, game.scene.name, game.scene.entities.size(),
               static_cast<int>(game.scene.magnet));

  termios raw{};
  if (tcgetattr(STDIN_FILENO, &g_orig) == 0 && isatty(STDIN_FILENO)) {
    raw = g_orig;
    cfmakeraw(&raw);
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
    g_raw = true;
    enterScreen();
  } else {
    std::println(stderr, "(not a tty — rendering one frame for the road)");
  }

  using clock = std::chrono::steady_clock;
  auto last = clock::now();
  double acc = 0;
  int cols = 80, rows = 24;
  dxn3::Screen scr;
  auto doFit = [&]() {
    const float ww = std::max(320.f, game.worldRight() + 160);
    const float wh = std::max(240.f, game.worldBottom() + 160);
    const float fz = std::min(cols / ww, (rows - 2) * 2.f / wh);
    game.scene.camera.zoom = std::clamp(fz, 0.3f, 4.f);
  };

  // the launch moment: the emblem, the version, the scene. Any key —
  // or ~1.6 seconds — and the studio takes over.
  termSize(cols, rows);
  scr.setBraille(true);                        // dots, not chunks — b toggles
  if (g_raw && cols >= 44 && rows >= 18) {
    scr.resize(cols, rows);
    drawSplash(scr, game);
    std::fputs(scr.flush().c_str(), stdout);
    std::fflush(stdout);
    for (int i = 0; i < 32 && !g_stop; ++i) {
      pollfd pfd{STDIN_FILENO, POLLIN, 0};
      if (::poll(&pfd, 1, 50) > 0 && (pfd.revents & POLLIN)) {
        char toss[64];
        const ssize_t rn = ::read(STDIN_FILENO, toss, sizeof toss);
        (void)rn;
        break;
      }
    }
  }

  while (!g_stop) {
    const auto now = clock::now();
    const double dt = std::chrono::duration<double>(now - last).count();
    last = now;
    acc += dt;
    if (cmdErrT > 0) cmdErrT -= static_cast<float>(dt);

    const Keys keys = pollKeys(cmdOpen ? Mode::Cmd
                              : ide.open ? Mode::Ide
                              : fileView ? Mode::File : Mode::Play);
    cols0 = cols; rows0 = rows;

    // live refresh: edits settle for a beat, then your code runs again
    if (ide.open) {
      ide.idle += dt;
      if (ide.dirty && ide.idle > 0.6) ideRun();
    }

    if (cmdOpen) {                       // the command bar owns the keyboard
      if (keys.esc) cmdOpen = false;
      else if (keys.back) { if (!cmdBuf.empty()) cmdBuf.pop_back(); }
      else if (keys.enter) {
        const dxn3::Cmd cmd = dxn3::parseCommand(cmdBuf);
        cmdOpen = false;
        cmdBuf.clear();
        if (!cmd.ok()) { cmdErr = cmd.error; cmdErrT = 3.5f; }
        else if (cmd.verb == "scene") {
          // by name, honestly: unique prefix resolves, ambiguity lists,
          // a ghost passes through for loadScene's honest error
          const std::string resolved = dxn3::resolveSceneArg(cmd.arg, sceneStems());
          if (resolved.empty()) {
            std::string list;
            for (const auto& m : dxn3::sceneMatches(cmd.arg, sceneStems())) {
              if (!list.empty()) list += " · ";
              list += m;
            }
            cmdErr = "ambiguous scene '" + cmd.arg + "' — " + list;
            cmdErrT = 4.f;
          } else {
            auto next = dxn3::Game::loadScene(resolved);
            if (next) {
              host.stop();                                 // leave the IDE game
              ide.hostUp = false;
              ide.open = false;
              game = dxn3::Game(std::move(*next));
              scenePath = resolved;
              game.say("scene: " + game.scene.name, 1.6);
            } else { cmdErr = next.error().detail; cmdErrT = 3.5f; }
          }
        } else if (cmd.verb == "zoom") {
          if (cmd.arg == "in") game.scene.camera.zoom = std::clamp(game.scene.camera.zoom * 1.15f, 0.3f, 4.f);
          else if (cmd.arg == "out") game.scene.camera.zoom = std::clamp(game.scene.camera.zoom / 1.15f, 0.3f, 4.f);
          else game.scene.camera.zoom = std::clamp(cmd.num, 0.3f, 4.f);
        } else if (cmd.verb == "fit") {
          doFit();
        } else if (cmd.verb == "reset") {
          game.reset();
        } else if (cmd.verb == "w") {
          const std::string path = cmd.arg.empty() ? scenePath : cmd.arg;
          const std::string err = dxn3::Game::saveScene(path, game.scene);
          if (err.empty()) game.say("saved " + path + "  (.bak kept)", 2.2);
          else { cmdErr = err; cmdErrT = 3.5f; }
        } else if (cmd.verb == "wq") {
          const std::string err = dxn3::Game::saveScene(scenePath, game.scene);
          if (err.empty()) break;
          cmdErr = err; cmdErrT = 3.5f;
        } else if (cmd.verb == "q") {
          break;
        } else if (cmd.verb == "screenshot") {
          doShot(cmd.arg);
        } else if (cmd.verb == "magnet") {
          game.scene.magnet = cmd.num;
          game.say("magnet " + std::to_string(static_cast<int>(cmd.num)) + "px", 1.2);
        } else if (cmd.verb == "gravity") {
          game.scene.gravity = cmd.num;
          game.say("gravity " + std::to_string(static_cast<int>(cmd.num)), 1.2);
        } else if (cmd.verb == "help") {
          game.say(":scene :zoom :fit :reset :w :wq :q :screenshot :magnet :gravity", 4.f);
        }
      } else {
        cmdBuf += keys.typed;
        if (cmdBuf.size() > 120) cmdBuf.resize(120);
      }
    } else if (!fileView) {
      if (keys.quit || (keys.esc && !ide.open)) break;   // esc edits, q quits
      if (keys.cmd) { cmdOpen = true; cmdBuf.clear(); }
      if (keys.inspect) inspect = !inspect;
      if (keys.viewFile) {
        if (ide.hostUp || isScriptFile(ide.path)) ide.open = true;   // e → the IDE
        else { fileView = true; searching = false; query.clear(); fileTop = 0; }
      }
      if (keys.shot) doShot("");
      if (keys.reset) game.reset();
      if (keys.zoomIn) game.scene.camera.zoom = std::clamp(game.scene.camera.zoom * 1.15f, 0.3f, 4.f);
      if (keys.zoomOut) game.scene.camera.zoom = std::clamp(game.scene.camera.zoom / 1.15f, 0.3f, 4.f);
      if (keys.fit) doFit();
      if (keys.braille) {
        scr.setBraille(!scr.braille());
        game.say(scr.braille() ? "braille dots — 4x the pixels" : "half blocks", 1.4);
      }
    } else {
      if (keys.quit) break;                    // q still quits the studio
      if (keys.esc) {                          // ESC leaves the view/search
        if (searching) searching = false;
        else fileView = false;
      }
      if (keys.slash && !searching) { searching = true; query.clear(); }
      if (searching) {
        if (keys.back) { if (!query.empty()) query.pop_back(); }
        else query += keys.typed;
      }
      if (keys.scroll != 0) {
        const int maxTop = std::max(0, static_cast<int>(fileLines.size()) - (rows - 3));
        fileTop = std::clamp(fileTop + keys.scroll, 0, maxTop);
      }
      if (keys.enter && searching && !query.empty()) {
        searching = false;
        for (size_t i = 1; i <= fileLines.size(); ++i) {   // wrap-around find
          const size_t li = (fileTop + i) % fileLines.size();
          if (fileLines[li].find(query) != std::string::npos) {
            const int maxTop = std::max(0, static_cast<int>(fileLines.size()) - (rows - 3));
            fileTop = std::clamp(static_cast<int>(li) - 2, 0, maxTop);
            break;
          }
        }
      }
    }

    dxn3::Input in;
    in.left = keys.left; in.right = keys.right; in.jump = keys.jump;

    constexpr double STEP = 1.0 / 60.0;
    if (ide.hostUp) {              // your code owns the simulation entirely —
      game.time += static_cast<float>(dt);   // the engine renders + feeds input
      acc = 0;
    } else if (!inspect && !fileView && !cmdOpen) {   // the command bar pauses
      while (acc >= STEP) {
        game.update(static_cast<float>(STEP), in);
        acc -= STEP;
        in = {};                      // hold inputs for one step only
      }
      if (!game.pendingNext.empty()) {
        const std::string nextPath = game.pendingNext;
        auto next = dxn3::Game::loadScene(nextPath);
        game.pendingNext.clear();
        if (next) {
          const int score = game.score;
          const float time = game.time;
          const std::string name = next->name;
          game = dxn3::Game(std::move(*next));
          game.score = score; game.time = time;
          scenePath = nextPath;              // :w knows where home is
          game.say("welcome to " + name, 1.6);
        } else {
          game.say("next scene missing: " + next.error().detail, 2.5);
          game.transLocked = true;
        }
      }
    } else {
      acc = 0;
    }

    // the IDE owns its keys: typing is code, ctrl+r/s run and save,
    // esc hands the keyboard to your game
    if (ide.open) {
      ideKey(ide, keys);
      if (!keys.typed.empty() || keys.back || keys.enter) {
        ide.dirty = true;
        ide.idle = 0;
      }
      if (keys.up || keys.down || keys.aLeft || keys.aRight) ide.idle = 0;
      if (keys.ctrlS) {
        std::string err;
        if (ideSave(ide, &err)) ide.console.push_back("engine: saved " + ide.path);
        else ide.console.push_back("engine: " + err);
        ideRun();
        ide.idle = 0;
      } else if (keys.ctrlR) {
        ideRun();
        ide.idle = 0;
      }
      if (keys.esc) ide.open = false;          // esc → play your game
    }

    // the hosted game: your code ticks every frame, even while you edit
    if (ide.hostUp) {
      if (!host.running()) {
        ide.hostUp = false;
        ide.console.push_back("engine: your game exited (code " +
                              std::to_string(host.exitCode()) + ")");
        ide.state = "exited — fix it and ctrl+r";
      } else {
        std::vector<std::string> hits;
        const auto& es = game.scene.entities;
        for (size_t a = 0; a < es.size(); ++a) {
          if (!es[a].alive || es[a].tag.empty()) continue;
          for (size_t b = a + 1; b < es.size(); ++b) {
            if (!es[b].alive || es[b].tag.empty() || es[b].tag == es[a].tag)
              continue;
            if (dxn3::Game::overlap(es[a], es[b])) {
              hits.push_back(es[a].name);
              hits.push_back(es[b].name);
            }
          }
        }
        const dxn3::HostFrame f = host.tick(
            static_cast<float>(dt), !ide.open && in.left, !ide.open && in.right,
            !ide.open && in.jump, !ide.open && keys.jump,
            ide.open ? std::string() : keys.typed, hits);
        dxn3::json::Value sc;
        if (host.takeScene(sc)) {
          dxn3::Scene ns = dxn3::sceneFromHost(sc, cols0, (rows0 - 2) * 2);
          const int ents = static_cast<int>(ns.entities.size());
          game = dxn3::Game(std::move(ns));
          ide.console.push_back("engine: built " + std::to_string(ents) +
                                " entities — your game is live");
        }
        dxn3::applyFrame(game, f);
        for (auto& l : host.takeConsole()) {
          ide.console.push_back(l);
        }
        if (ide.console.size() > 200)
          ide.console.erase(ide.console.begin(),
                            ide.console.begin() + static_cast<long>(ide.console.size() - 200));
        if (f.exited) {
          ide.hostUp = false;
          ide.console.push_back("engine: your game exited (code " +
                                std::to_string(f.exitCode) + ")");
          ide.state = "exited — fix it and ctrl+r";
        }
      }
    }

    if (g_raw) {
      termSize(cols, rows);
      scr.resize(cols, rows);
      if (fileView) drawFile(scr, fileLines, fileTop, query, scenePath);
      else if (ide.open) drawIDE(scr, ide, game, host.running());
      else if (inspect) drawInspect(scr, game);
      else drawWorld(scr, game);
      if (ide.open) {
        // the IDE paints its own rails
      } else if (cmdOpen) {
        scr.text(0, rows - 1, ":" + cmdBuf + "_", dxn3::rgb(250, 204, 21));
        const std::string hint = dxn3::usageHintFor(cmdBuf);
        if (!hint.empty()) {
          const int hcol = 2 + static_cast<int>(cmdBuf.size());
          if (hcol + static_cast<int>(hint.size()) < cols - 1)
            scr.text(hcol, rows - 1, hint, dxn3::rgb(124, 58, 237));
        }
        // :scene completion — the campaign whispers its own names
        if (cmdBuf.rfind(":scene ", 0) == 0 && cmdBuf.size() > 7) {
          const std::string part = cmdBuf.substr(7);
          std::string w;
          for (const auto& m : dxn3::sceneMatches(part, sceneStems())) {
            if (!w.empty()) w += " · ";
            w += m;
          }
          const int hcol = 2 + static_cast<int>(cmdBuf.size());
          if (!w.empty() && hcol + static_cast<int>(w.size()) < cols - 1)
            scr.text(hcol, rows - 1, w, dxn3::rgb(168, 85, 247));
        }
      } else if (cmdErrT > 0) {
        scr.text(0, rows - 1, " dxn3: " + cmdErr, dxn3::rgb(248, 113, 113));
      } else if (fileView) {
        scr.help(" j/k scroll · / find · enter run · esc back · q quit");
      } else if (inspect) {
        scr.help(" a/d move · w jump · r reset · +/- zoom · f fit · b dots · q quit");
      } else {
        scr.help(" a/d move · w jump · r reset · b dots · e file · : cmds · q quit");
      }
      std::fputs(scr.flush().c_str(), stdout);
      std::fflush(stdout);
    } else {
      // non-tty smoke mode: draw once, exit honestly
      scr.resize(80, 24);
      drawWorld(scr, game);
      const std::string frame = scr.flush();
      std::fwrite(frame.data(), 1, frame.size(), stdout);
      std::fflush(stdout);
      std::println(stdout, "\nframe rendered: score={} time={} entities={}",
                   game.score, game.time, game.scene.entities.size());
      return 0;
    }

    timespec ts{0, 6'000'000};        // ~6ms snooze -> ~60fps ceiling
    nanosleep(&ts, nullptr);
  }

  restoreTerminal();
  std::println("dxn3 native — thanks for playing. SCORE {}  TIME {}",
               game.score, fmtTime(game.time));
  return 0;
}
