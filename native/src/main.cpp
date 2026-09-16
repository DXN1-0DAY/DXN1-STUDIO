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
#include "edit.hpp"

#include <sstream>

using dxn3::RGB;
using dxn3::Keys;          // the editor heart lives in edit.hpp
using dxn3::IdeState;

namespace {

std::atomic<bool> g_stop{false};
termios g_orig{};
bool g_raw = false;

void restoreTerminal() {
  if (g_raw) {
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &g_orig);
    std::fputs("\x1b[0m\x1b[?1006l\x1b[?1002l\x1b[?1000l\x1b[?25h\x1b[?1049l", stdout);
    std::fflush(stdout);
    g_raw = false;
  }
}

void onSignal(int) { g_stop = true; }

void enterScreen() {
  std::fputs("\x1b[?1049h\x1b[?1000;1002;1006h\x1b[2J", stdout);
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
        // CSI sequences: ESC [ <params: 0-9 ; : < ?> <final: @-~>. Parse
        // the whole sequence in one bite and SWALLOW unknown ones — a
        // sequence that leaks its parameters into the document is
        // corruption (ctrl+arrows used to type "1;5C" into your code).
        // SS3 (ESC O A) is the same idea in the other dialect. The bar
        // parses too: a bare ESC closes it, but an arrow key must never
        // fake an ESC (it used to slam the bar shut mid-thought).
        if (i + 1 < n && (buf[i + 1] == '[' || buf[i + 1] == 'O')) {
          const bool csi = buf[i + 1] == '[';
          if (i + 2 >= n) {
            i = static_cast<int>(n) - 1;   // split read: swallow the fragment
            continue;
          }
          int j = i + 2;
          if (csi) {                       // parameter bytes: 0-9 ; : < ?
            while (j < n && (buf[j] == ';' || buf[j] == ':' ||
                             buf[j] == '<' || buf[j] == '?' ||
                             (buf[j] >= '0' && buf[j] <= '9')))
              ++j;
            if (j >= n) {                  // still no final byte: split read
              i = static_cast<int>(n) - 1;
              continue;
            }
          }
          const char fin = buf[j];
          const std::string params(buf + i + 2, buf + j);
          int mod = 0;                     // xterm modifier digit (5 = ctrl)
          {
            const size_t semi = params.rfind(';');
            const std::string m =
                semi == std::string::npos ? params : params.substr(semi + 1);
            mod = (m.size() == 1 && m[0] >= '2' && m[0] <= '9') ? m[0] - '0' : 0;
          }
          if (!csi) mod = 0;               // SS3 carries no modifiers
          switch (fin) {
            case 'A':
              if (mode == Mode::Ide && mod == 5) k.scroll -= 1;  // nudge the view
              else if (mode == Mode::Ide && mod == 2) k.sUp = true;
              else if (mod == 0) {
                if (mode == Mode::Ide) k.up = true;
                else if (mode == Mode::File) k.scroll -= 1;
                else k.jump = true;
              }
              break;
            case 'B':
              if (mode == Mode::Ide && mod == 5) k.scroll += 1;
              else if (mode == Mode::Ide && mod == 2) k.sDown = true;
              else if (mod == 0) {
                if (mode == Mode::Ide) k.down = true;
                else if (mode == Mode::File) k.scroll += 1;
              }
              break;
            case 'C':
              if (mode == Mode::Ide && mod == 6) k.sWRight = true;  // word select
              else if (mode == Mode::Ide && mod == 5) k.wRight = true;
              else if (mode == Mode::Ide && mod == 2) k.sRight = true;
              else if (mod == 0) {
                if (mode == Mode::Ide) k.aRight = true;
                else if (mode == Mode::File) k.scroll += 10;
                else k.right = true;
              }
              break;
            case 'D':
              if (mode == Mode::Ide && mod == 6) k.sWLeft = true;   // word select
              else if (mode == Mode::Ide && mod == 5) k.wLeft = true;
              else if (mode == Mode::Ide && mod == 2) k.sLeft = true;
              else if (mod == 0) {
                if (mode == Mode::Ide) k.aLeft = true;
                else if (mode == Mode::File) k.scroll -= 10;
                else k.left = true;
              }
              break;
            case 'H':
              if (mode == Mode::Ide) {
                if (mod == 5) k.docHome = true;      // ctrl+home: the top
                else if (mod == 0) k.home = true;
              }
              break;
            case 'F':
              if (mode == Mode::Ide) {
                if (mod == 5) k.docEnd = true;       // ctrl+end: the bottom
                else if (mod == 0) k.end = true;
              }
              break;
            case '~': {
              if (mode != Mode::Ide) break;
              const int p = std::atoi(params.c_str());
              // for '~' the params are the KEY NUMBER; a modifier only
              // exists when a ';' is present (3;5~ = ctrl+delete)
              const size_t semi = params.rfind(';');
              const bool ctrl = semi != std::string::npos &&
                                semi + 1 < params.size() &&
                                params[semi + 1] == '5';
              if (p == 3) {
                if (ctrl) k.delWordFwd = true;
                else k.del = true;
              } else if (!ctrl) {
                if (p == 5) k.pageUp = true;
                else if (p == 6) k.pageDn = true;
                else if (p == 1 || p == 7) k.home = true;
                else if (p == 4 || p == 8) k.end = true;
              }
              break;
            }
            case 'Z':
              if (mode == Mode::Ide) k.backTab = true;   // shift+tab — dedent
              break;
            case 'M': {
              // SGR mouse report: ESC[<b;x;yM — button 0 is the left
              // click (+4 with shift), 64/65 are the wheel up/down.
              // Releases ('m') and every other button stay silent; the
              // terminal counts cells from 1, the studio from 0.
              if (params.empty() || params[0] != '<') break;
              int nums[3] = {0, 0, 0};
              size_t p = 1;
              bool okNums = true;
              for (int ni = 0; ni < 3; ++ni) {
                const size_t semi = params.find(';', p);
                const std::string part = params.substr(
                    p, semi == std::string::npos ? std::string::npos
                                                 : semi - p);
                if (part.empty() ||
                    part.find_first_not_of("0123456789") != std::string::npos) {
                  okNums = false;
                  break;
                }
                nums[ni] = std::atoi(part.c_str());
                if (semi == std::string::npos) {
                  if (ni < 2) okNums = false;
                  break;
                }
                p = semi + 1;
              }
              if (okNums && nums[1] > 0 && nums[2] > 0) {
                if (nums[0] == 0 || nums[0] == 4) {      // left press
                  if (mode == Mode::Ide) {
                    k.clickC = nums[1] - 1;
                    k.clickR = nums[2] - 1;
                    k.clickShift = nums[0] == 4;
                  }
                } else if (nums[0] == 32 || nums[0] == 36) {   // motion
                  if (mode == Mode::Ide) {                 // with the button
                    k.dragC = nums[1] - 1;                 // held: the drag
                    k.dragR = nums[2] - 1;
                    k.clickShift = nums[0] == 36;
                  }
                } else if (nums[0] == 64 || nums[0] == 65) {   // the wheel
                  if (mode == Mode::Ide || mode == Mode::File)
                    k.scroll += nums[0] == 64 ? -3 : 3;
                }
              }
              break;
            }
            case 'm': {                                    // button release
              if (params.empty() || params[0] != '<') break;
              if (mode == Mode::Ide) k.clickRelease = true;
              break;
            }
            default:
              break;     // mouse reports, DSR answers, F-keys: swallowed whole
          }
          i = j;           // the for's ++i consumes the final byte
        } else {
          k.esc = true;                     // bare ESC
          if (mode == Mode::Play) k.quit = true;   // …which quits in play/inspect
        }
        continue;
      }
      if (mode == Mode::Ide) {               // IDE: the editor owns typing
        if (c == '\r' || c == '\n') k.enter = true;
        else if (c == '\t') k.tab = true;                 // tab: snippet or block
        else if (c == 0x7f || c == '\b') k.back = true;
        else if (c == 0x13) k.ctrlS = true;               // Ctrl+S — save+run
        else if (c == 0x12) k.ctrlR = true;               // Ctrl+R — run
        else if (c == 0x0e) k.ctrlN = true;               // Ctrl+N — template
        else if (c == 0x07) k.ctrlG = true;               // Ctrl+G — error line
        else if (c == 0x1a) k.ctrlZ = true;               // Ctrl+Z — undo
        else if (c == 0x19) k.ctrlY = true;               // Ctrl+Y — redo
        else if (c == 0x06) k.ctrlF = true;               // Ctrl+F — find
        else if (c == 0x04) k.ctrlD = true;               // Ctrl+D — dup lines
        else if (c == 0x17) k.delWord = true;             // Ctrl+W — delete word
        else if (c == 0x1f) k.comment = true;             // Ctrl+/ — toggle comment
        else if (c == 0x10) k.shot = true;                // Ctrl+P — screenshot
        else if (c == 0x03) k.ctrlC = true;               // Ctrl+C — copy
        else if (c == 0x18) k.ctrlX = true;               // Ctrl+X — cut
        else if (c == 0x16) k.ctrlV = true;               // Ctrl+V — paste
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
      // per-DOT circle test: in braille mode every dot is its own pixel,
      // so discs are genuinely round instead of stair-stepped
      const int dx0 = std::max(0, static_cast<int>(x0 * 2.f) - 1);
      const int dx1 = std::min(cols * 2 - 1, static_cast<int>(x1 * 2.f) + 1);
      const int dy0 = std::max(0, static_cast<int>(y0 * 2.f) - 1);
      const int dy1 = std::min(hr * 2 - 1, static_cast<int>(y1 * 2.f) + 1);
      for (int dy = dy0; dy <= dy1; ++dy) {
        const float wy = dy * 0.5f + 0.25f;
        const float ty = (wy - cym) / rh;
        for (int dx = dx0; dx <= dx1; ++dx) {
          const float wx = dx * 0.5f + 0.25f;
          const float tx = (wx - cxm) / rw;
          const float k2 = tx * tx + ty * ty;
          if (k2 > 1.f) continue;
          scr.pxDot(wx, wy, k2 > 0.80f ? edgeC : c1);
        }
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

// the Ctrl+N gallery: cycle real, working starting points
const char* TPL_BLANK =
    "# blank canvas — W and H are the world size.\n"
    "# make anything: rect(), circle(), label(), on_key, on_tick, run()\n\n"
    "from dxn3 import *\n\n"
    "ball = circle(\"ball\", W // 2, H // 2, 6, 6, \"#facc15\")\n"
    "ball.vx = 3\n"
    "ball.vy = 2\n\n"
    "def on_tick(dt):\n"
    "    if ball.x < 0 or ball.x > W - 6: ball.vx = -ball.vx\n"
    "    if ball.y < 0 or ball.y > H - 6: ball.vy = -ball.vy\n\n"
    "run()\n";

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
  for (const auto& l : ide.lines) f << l << '\n';   // POSIX: files end in \n
  return f.good();
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
  ide.page = bodyRows;                       // pgup/pgdn follow the viewport
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
  // where you are, always: the header carries the honest line:col
  const std::string pos = "  Ln " + std::to_string(ide.curR + 1) + " · Col " +
                          std::to_string(ide.curC + 1);
  if (24 + static_cast<int>(file.size() + pos.size()) + 2 < scol)
    scr.text(24 + static_cast<int>(file.size()), 0, pos, dxn3::rgb(110, 118, 140));

  // the editor pane — the minimap rents its rail from the code's right
  // edge when the terminal is wide enough to spare it (six map columns,
  // one gap, one divider); :minimap can always send it home
  const bool mapOn = ide.minimap && split && cols >= 110;
  const int mapW = 6;
  const int mapX = editW - 1 - mapW;         // map cols [mapX, mapX + mapW)
  const int textW = editW - 5 - (mapOn ? mapW + 1 : 0);   // code after gutter
  const int maxTop = std::max(0, static_cast<int>(ide.lines.size()) - bodyRows);
  ide.top = std::clamp(ide.top, 0, maxTop);
  if (ide.curR < ide.top) ide.top = ide.curR;
  if (ide.curR >= ide.top + bodyRows) ide.top = ide.curR - bodyRows + 1;
  ideHscroll(ide, textW);              // long lines slide under the cursor
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
    // long lines slide: every row shows the window [hcol, hcol + textW)
    const std::string& ln = ide.lines[static_cast<size_t>(li)];
    if (ide.hcol > 0) scr.text(3, bodyTop + r, "…", dxn3::rgb(96, 104, 126));
    const std::string slice =
        ide.hcol > 0 && static_cast<int>(ln.size()) > ide.hcol
            ? ln.substr(static_cast<size_t>(ide.hcol))
            : std::string();
    drawCodeLine(scr, 4, bodyTop + r, ide.hcol > 0 ? slice : ln, textW);
  }
  // the ruler: honest guides at 79 and 99 — a dim dot only where the
  // cell is blank, so the guide never paints over your code
  if (ide.ruler) {
    const RGB rulerC = dxn3::rgb(64, 54, 104);
    for (int rc : {79, 99}) {
      const int scol = 4 + rc - ide.hcol;
      if (scol < 4 || scol >= 4 + textW) continue;   // out of the pane
      for (int r = 0; r < bodyRows; ++r) {
        const int li = ide.top + r;
        if (li >= static_cast<int>(ide.lines.size())) break;
        const std::string& ln = ide.lines[static_cast<size_t>(li)];
        if (rc < static_cast<int>(ln.size()) &&
            ln[static_cast<size_t>(rc)] != ' ' &&
            ln[static_cast<size_t>(rc)] != '\t')
          continue;                                  // code owns the cell
        scr.text(scol, bodyTop + r, "·", rulerC);
      }
    }
  }
  // the selection glows: every cell of the anchor↔cursor range burns
  // softly (drawn before the cursor, after the code)
  if (const auto sel = dxn3::ideSelRange(ide)) {
    const auto [r0, c0, r1, c1] = *sel;
    const RGB selGlow = dxn3::rgb(56, 42, 98);
    for (int r = r0; r <= r1; ++r) {
      if (r < ide.top || r >= ide.top + bodyRows) continue;
      const std::string& l = ide.lines[static_cast<size_t>(r)];
      const int from = (r == r0) ? c0 : 0;
      const int to = (r == r1) ? std::min<int>(c1, static_cast<int>(l.size()))
                               : static_cast<int>(l.size());
      for (int c = from; c < to; ++c) {
        const int col = 4 + c - ide.hcol;
        if (col < 4 || col >= 4 + textW) continue;    // out of the pane
        scr.textBg(col, bodyTop + (r - ide.top),
                   std::string(1, l[static_cast<size_t>(c)]), paneBg, selGlow);
      }
    }
  }
  // the cursor: inverse video on the exact cell
  if (ide.curR >= ide.top && ide.curR < ide.top + bodyRows) {
    const int row = bodyTop + (ide.curR - ide.top);
    const std::string& l = ide.lines[static_cast<size_t>(ide.curR)];
    const char ch = ide.curC < static_cast<int>(l.size()) ? l[static_cast<size_t>(ide.curC)] : ' ';
    scr.textBg(4 + ide.curC - ide.hcol, row, std::string(1, ch), paneBg, dxn3::rgb(167, 139, 250));
  }
  // the bracket's partner glows across the file — the cursor's own cell
  // already burns inverse video, so the glow lands on the partner (and
  // on the anchor behind the cursor when that is the bracket held)
  {
    int br = -1, bc = -1;
    if (ideMatchBracket(ide, br, bc)) {
      const RGB glowBg = dxn3::rgb(52, 40, 92);
      auto glow = [&](int r2, int c2) {
        if (r2 < ide.top || r2 >= ide.top + bodyRows) return;
        const std::string& l2 = ide.lines[static_cast<size_t>(r2)];
        if (c2 < 0 || c2 >= static_cast<int>(l2.size())) return;
        const int col = 4 + c2 - ide.hcol;
        if (col < 4 || col >= 4 + textW) return;    // scrolled out of the pane
        scr.textBg(col, bodyTop + (r2 - ide.top),
                   std::string(1, l2[static_cast<size_t>(c2)]), paneBg, glowBg);
      };
      glow(br, bc);
      const std::string& cl = ide.lines[static_cast<size_t>(ide.curR)];
      const char atCur = ide.curC < static_cast<int>(cl.size())
                             ? cl[static_cast<size_t>(ide.curC)] : '\0';
      if (atCur != '(' && atCur != '[' && atCur != '{' && atCur != ')' &&
          atCur != ']' && atCur != '}' && ide.curC > 0)
        glow(ide.curR, ide.curC - 1);              // the anchor sits behind
    }
  }
  // the searchlight's wake: every match glows, the current one burns
  if (ide.findOpen && !ide.findHits.empty() && !ide.findQ.empty()) {
    const int maxW = mapOn ? 4 + textW : (split ? editW - 1 : cols);
    size_t hi = 0;
    for (int r = 0; r < bodyRows; ++r) {
      const int li = ide.top + r;
      if (li >= static_cast<int>(ide.lines.size())) break;
      while (hi < ide.findHits.size() && ide.findHits[hi].first < li) ++hi;
      for (size_t i = hi; i < ide.findHits.size() &&
                          ide.findHits[i].first == li; ++i) {
        const int hitC = ide.findHits[i].second;           // the real column
        const int c = hitC - ide.hcol;                     // the slide applies
        const int room = maxW - 4 - c;
        if (room <= 0 || c < 0) continue;   // past either edge of the pane
        std::string slice = ide.lines[static_cast<size_t>(li)].substr(
            static_cast<size_t>(hitC),
            std::min<size_t>(ide.findQ.size(), static_cast<size_t>(room)));
        scr.textBg(4 + c, bodyTop + r, slice, paneBg,
                   static_cast<int>(i) == ide.findSel ? dxn3::rgb(180, 83, 9)
                                                      : dxn3::rgb(66, 50, 14));
      }
    }
  }

  // the minimap: the whole document compressed into a six-column rail
  // riding the pane's right edge. The viewport's rows carry a soft band
  // and burn brighter; the cursor's row is the brightest bar on the
  // map; comments speak gray, find hits speak amber, blank lines keep
  // one dim dot so the rows stay anchored.
  if (mapOn) {
    const dxn3::IdeMini mini = dxn3::ideMiniMap(ide, mapW, bodyRows);
    const RGB barView = dxn3::rgb(150, 132, 220);
    const RGB barOut = dxn3::rgb(84, 72, 120);
    const RGB barCmt = dxn3::rgb(96, 104, 126);
    const RGB barCur = dxn3::rgb(196, 181, 253);
    const RGB barHit = dxn3::rgb(250, 204, 21);
    const RGB dotC = dxn3::rgb(60, 66, 96);
    const RGB bandBg = dxn3::rgb(30, 22, 52);
    for (int r = 0; r < bodyRows; ++r)
      scr.text(editW - 1, bodyTop + r, "│", dxn3::rgb(58, 50, 94));
    auto bars = [](int n) {
      std::string s;
      for (int i = 0; i < n; ++i) s += "▌";
      return s;
    };
    for (size_t i = 0; i < mini.rows.size(); ++i) {
      const int row = bodyTop + static_cast<int>(i);
      const int li = mini.top + static_cast<int>(i);
      const auto& mr = mini.rows[static_cast<size_t>(i)];
      const bool onCur = li == ide.curR;
      if (mr.inView)                             // the viewport's band
        for (int c = 0; c < mapW; ++c)
          scr.textBg(mapX + c, row, " ", paneBg, bandBg);
      if (mr.blank) {
        scr.text(mapX, row, "·", mr.inView ? dxn3::rgb(96, 104, 126) : dotC);
        continue;
      }
      const RGB fg = onCur ? barCur
                     : mr.hit ? barHit
                     : mr.comment ? barCmt
                     : mr.inView ? barView : barOut;
      if (mr.inView) {                           // bright bars ride the band
        for (int c = 0; c < mr.len; ++c)
          scr.textBg(mapX + mr.start + c, row, "▌", fg, bandBg);
      } else {
        scr.text(mapX + mr.start, row, bars(mr.len), fg);
      }
    }
  }

  // the console rail: the game's prints + engine notes, honestly shown
  const int c0 = rows - consoleRows;
  scr.railBg(c0, dxn3::rgb(10, 7, 18));
  scr.railBg(c0 + 1, dxn3::rgb(10, 7, 18));
  size_t n = ide.console.size();
  const std::string l1 = n >= 1 ? ide.console[n - 1] : "";
  const std::string l2 = n >= 2 ? ide.console[n - 2] : "";
  scr.text(1, c0, l1.substr(0, static_cast<size_t>(cols - 3)), dxn3::rgb(148, 156, 180));
  if (ide.findOpen) {
    // the searchlight has the rail: query, hits, the way out
    std::string fb = " / find: " + ide.findQ + "_ ";
    if (ide.findQ.empty()) fb += "type to search the whole file";
    else if (ide.findHits.empty()) fb += "no matches — esc to close";
    else fb += std::to_string(ide.findSel + 1) + "/" +
               std::to_string(ide.findHits.size()) + " · enter next · esc done";
    scr.text(1, c0 + 1, fb.substr(0, static_cast<size_t>(cols - 3)), dxn3::rgb(250, 204, 21));
  } else {
    // a traceback in the console? offer the one-keystroke jump to the line
    const int errLine = dxn3::consoleErrorLine(ide.console);
    const std::string hint = errLine > 0
        ? " ctrl+g jumps to line " + std::to_string(errLine) +
          " · ctrl+z undo · ctrl+f find · esc play "
        : " ctrl+r run · ctrl+z undo · ctrl+c/x/v clipboard · ctrl+f find · "
          "esc play ";
    const bool errorUp = errLine > 0;
    scr.text(1, c0 + 1, hint.substr(0, static_cast<size_t>(cols - 3)),
             errorUp ? dxn3::rgb(248, 113, 113) : dxn3::rgb(84, 72, 120));
    // the whisper outranks the echo: a shelf word under the hand names
    // its boilerplate, otherwise the console's second-newest line rests
    // in the rail's right seat
    const std::string whisper = dxn3::ideSnippetWhisper(ide);
    const std::string right = whisper.empty() ? l2 : (" ⇥ " + whisper + " ");
    if (!right.empty())
      scr.text(cols - std::min(cols - 3, static_cast<int>(right.size())) - 1, c0 + 1,
               right.substr(0, static_cast<size_t>(std::min(cols - 3, static_cast<int>(right.size())))),
               whisper.empty() ? dxn3::rgb(84, 72, 120)
                               : dxn3::rgb(250, 204, 21));
  }
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
                   "keys:  ctrl+r run · ctrl+s save · ctrl+z undo · ctrl+y redo\n"
                   "       ctrl+c/x/v copy · cut · paste (a bare cut lifts the line)\n"
                   "       ctrl+f find · enter next hit · ctrl+d duplicate lines\n"
                   "       tab snippet/indent · shift+tab dedent · ctrl+/ comment\n"
                   "       shift+arrows select · shift+ctrl+←/→ select words\n"
                   "       ctrl+n template · ctrl+g error line · ctrl+p screenshot\n"
                   "       :minimap the document's map rail · :ruler guides · :stats\n"
                   "       esc play/back · a/d move · w jump\n"
                   "       mouse: click to move · drag to select · wheel rolls\n"
                   "       tab inspect · e file · : commands (:open loads any script) · q quit\n"
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
        if (ide.lines.empty()) ide.lines.push_back("");
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
    if (err.empty()) {
      game.say("saved " + path, 2.2);
      ide.console.push_back("engine: saved " + path +
                            " — a real PNG of your frame");   // the receipt stays
    } else { cmdErr = err; cmdErrT = 3.5f; }
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

  // the scripts on this machine — :open's completion fuel. Your own
  // games first, then the gallery's examples (read them, remix them).
  auto scriptCandidates = []() {
    std::vector<std::string> out;
    std::error_code ec;
    static const char* exts[] = {".py", ".js", ".mjs", ".cpp",
                                 ".cc", ".cxx", ".cs", ".rb", ".lua", ".sh"};
    for (const auto& de : std::filesystem::directory_iterator(".", ec))
      if (de.is_regular_file(ec)) {
        const std::string p = de.path().filename().string();
        for (const char* e : exts)
          if (p.size() > std::strlen(e) &&
              p.compare(p.size() - std::strlen(e), std::strlen(e), e) == 0) {
            out.push_back(p);
            break;
          }
      }
    for (const auto& de : std::filesystem::directory_iterator("sdk/examples", ec))
      if (de.is_regular_file(ec))
        out.push_back("sdk/examples/" + de.path().filename().string());
    std::sort(out.begin(), out.end());
    return out;
  };

  // the shots already in exports/ — :screenshot's completion fuel
  auto shotCandidates = []() {
    std::vector<std::string> out;
    std::error_code ec;
    for (const auto& de : std::filesystem::directory_iterator("exports", ec))
      if (de.is_regular_file(ec))
        out.push_back("exports/" + de.path().filename().string());
    std::sort(out.begin(), out.end());
    return out;
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

  // the template gallery: ctrl+n or :new — cycle real, working starts
  // across every language the studio hosts (py, js, compiled cpp)
  struct Tpl { const char* name; const char* ext; };
  static constexpr Tpl tpls[] = {{"blank", "py"},      {"shooter", "py"},
                                 {"cards", "py"},      {"background", "py"},
                                 {"flappy", "py"},     {"bounce", "js"},
                                 {"pong", "cpp"}};
  constexpr int nTpl = static_cast<int>(sizeof tpls / sizeof tpls[0]);
  auto loadTemplate = [&](int idx) {
    const std::string name = tpls[idx].name;
    if (name == "blank") {
      std::string ss = TPL_BLANK;
      ide.lines.clear();
      size_t pos;
      while ((pos = ss.find('\n')) != std::string::npos) {
        ide.lines.push_back(ss.substr(0, pos));
        ss.erase(0, pos + 1);
      }
      if (!ss.empty()) ide.lines.push_back(ss);
      ide.path = "untitled.py";
    } else {
      std::ifstream f(std::string("sdk/examples/") + name + "." +
                      tpls[idx].ext);
      ide.lines.clear();
      std::string ln;
      while (std::getline(f, ln)) {
        if (!ln.empty() && ln.back() == '\r') ln.pop_back();
        ide.lines.push_back(ln);
      }
      if (ide.lines.empty()) {
        ide.lines.push_back("");
        ide.console.push_back("engine: template " + name +
                              " not found on this machine");
      }
      ide.path = std::string("untitled-") + name + "." + tpls[idx].ext;
    }
    ide.undo.clear();                          // a new document, a fresh history
    ide.redo.clear();
    ide.lastTyping = ide.lastBack = false;
    ide.curR = ide.curC = ide.top = 0;
    ide.hcol = 0;                              // a fresh page, an unslid view
    dxn3::ideSelClear(ide);                    // and no stale selection
    ide.dirty = true;
    ide.idle = 0;
    ide.console.push_back("engine: template — " + name + " (" +
                          tpls[idx].ext + ", ctrl+n again to cycle)");
  };
  auto nextTemplate = [&]() {
    ide.tpl = (ide.tpl + 1) % nTpl;
    loadTemplate(ide.tpl);
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

    Keys keys = pollKeys(cmdOpen ? Mode::Cmd
                              : ide.open ? Mode::Ide
                              : fileView ? Mode::File : Mode::Play);
    const bool barOwned = cmdOpen;   // the bar polled this frame — its keys
                                     // belong to it, never to the IDE
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
        cmdBuf += keys.typed;      // a paste that lands with enter counts
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
        } else if (cmd.verb == "new") {
          if (!ide.open) ide.open = true;          // :new opens the studio
          nextTemplate();
        } else if (cmd.verb == "template") {
          // direct load: an exact name wins, a unique prefix resolves,
          // an ambiguous prefix lists, a ghost is refused — like :scene
          const std::string arg = cmd.arg;
          int hit = -1, hits = 0;
          for (int i = 0; i < nTpl; ++i)
            if (arg == tpls[i].name) { hit = i; hits = 1; break; }
          if (hit < 0)
            for (int i = 0; i < nTpl; ++i)
              if (std::string_view(tpls[i].name).rfind(arg, 0) == 0) {
                hit = i;
                ++hits;
              }
          if (hits == 0) {
            cmdErr = "no such template: " + arg + " — try blank, shooter, "
                     "cards, background, flappy, bounce, pong";
            cmdErrT = 4.f;
          } else if (hits > 1) {
            std::string list;
            for (const auto& t : tpls)
              if (std::string_view(t.name).rfind(arg, 0) == 0) {
                if (!list.empty()) list += " · ";
                list += t.name;
              }
            cmdErr = "ambiguous template '" + arg + "' — " + list;
            cmdErrT = 4.f;
          } else {
            ide.open = true;                       // the studio takes the stage
            ide.tpl = hit;
            loadTemplate(hit);
          }
        } else if (cmd.verb == "open") {
          // any script on this machine becomes the live document
          std::ifstream f(cmd.arg, std::ios::binary);
          if (!f.good()) {
            cmdErr = "no such file: " + cmd.arg;
            cmdErrT = 3.5f;
          } else {
            host.stop();                     // a new document owns the stage
            ide.hostUp = false;
            ide.lines.clear();
            std::string ln;
            while (std::getline(f, ln)) {
              if (!ln.empty() && ln.back() == '\r') ln.pop_back();
              ide.lines.push_back(ln);
            }
            if (ide.lines.empty()) ide.lines.push_back("");
            ide.path = cmd.arg;
            ide.undo.clear();                // a new document, a fresh history
            ide.redo.clear();
            ide.lastTyping = ide.lastBack = false;
            ide.curR = ide.curC = ide.top = 0;
            dxn3::ideSelClear(ide);          // no stale selection rides along
            ide.hcol = 0;
            ide.tpl = -1;
            ide.findOpen = false;            // the searchlight rests
            ide.findQ.clear();
            ide.findHits.clear();
            ide.findSel = -1;
            ide.open = true;                 // the studio takes the stage
            ide.dirty = true;
            ide.idle = 0;
            game.say("open " + cmd.arg, 1.6);
          }
        } else if (cmd.verb == "goto") {
          // jump the editor to a line — ctrl+g's sibling for lines
          // without a traceback. The studio takes the stage.
          if (!ide.open) ide.open = true;
          ide.findOpen = false;
          ide.curR = std::clamp(static_cast<int>(cmd.num) - 1, 0,
                                static_cast<int>(ide.lines.size()) - 1);
          ide.curC = 0;
          ide.top = std::max(0, ide.curR - 4);   // the jump lands mid-screen
          ide.lastTyping = ide.lastBack = false;
          dxn3::ideSelClear(ide);                // the jump drops the selection
          ide.console.push_back("engine: jumped to line " +
                                std::to_string(ide.curR + 1));
        } else if (cmd.verb == "snip") {
          // boilerplate from the shelf: an exact name wins, a unique
          // prefix resolves, an ambiguous prefix lists — like :template
          const std::string arg = cmd.arg;
          const auto names = dxn3::ideSnippetNames(ide.path);
          std::string hit;
          int hits = 0;
          for (const auto& nm : names)
            if (nm == arg) { hit = nm; hits = 1; break; }
          if (hit.empty())
            for (const auto& nm : names)
              if (nm.rfind(arg, 0) == 0) { hit = nm; ++hits; }
          if (hits == 0) {
            std::string list;
            for (const auto& nm : names) list += (list.empty() ? "" : " ") + nm;
            cmdErr = "no such snippet: " + arg + " — try " + list;
            cmdErrT = 4.f;
          } else if (hits > 1) {
            std::string list;
            for (const auto& nm : names)
              if (nm.rfind(arg, 0) == 0)
                list += (list.empty() ? "" : " · ") + nm;
            cmdErr = "ambiguous snippet '" + arg + "' — " + list;
            cmdErrT = 4.f;
          } else {
            const auto block = dxn3::ideSnippetFor(hit, ide.path);
            if (block) {
              if (!ide.open) ide.open = true;    // the studio takes the stage
              dxn3::ideInsertBlock(ide, *block);
              ide.console.push_back("engine: snippet " + hit + " — " +
                                    std::to_string(block->size()) +
                                    " lines landed");
            }
          }
        } else if (cmd.verb == "ruler") {
          if (!ide.open) ide.open = true;      // the studio takes the stage
          ide.ruler = !ide.ruler;
          ide.console.push_back(ide.ruler
                                    ? "engine: ruler on — guides at 79 and 99"
                                    : "engine: ruler off");
        } else if (cmd.verb == "minimap") {
          if (!ide.open) ide.open = true;      // the studio takes the stage
          ide.minimap = !ide.minimap;
          ide.console.push_back(
              ide.minimap ? "engine: minimap on — the document rides the "
                            "pane's right edge"
                          : "engine: minimap off");
        } else if (cmd.verb == "stats") {
          if (!ide.open) ide.open = true;      // the studio takes the stage
          size_t words = 0, chars = 0;
          for (const auto& l : ide.lines) {
            chars += l.size() + 1;
            bool inWord = false;
            for (char ch : l) {
              if (std::isspace(static_cast<unsigned char>(ch))) inWord = false;
              else { if (!inWord) ++words; inWord = true; }
            }
          }
          ide.console.push_back(
              "engine: " + std::to_string(ide.lines.size()) + " lines · " +
              std::to_string(words) + " words · " + std::to_string(chars) +
              " chars");
          ide.console.push_back(
              "engine: at Ln " + std::to_string(ide.curR + 1) + " · Col " +
              std::to_string(ide.curC + 1) + " · " +
              std::string(dxn3::ideSnippetFamily(ide.path)) + " dialect · " +
              (ide.hostUp ? "host live" : "host idle"));
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
          game.say(":scene :open :template :snip :goto :ruler :minimap :stats :zoom "
                    ":fit :reset :new :w :wq :q :screenshot :magnet :gravity", 4.f);
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
    // esc hands the keyboard to your game (or closes the searchlight) —
    // but a frame the command bar polled is the bar's alone (:open and
    // :new hand the stage over; the same frame's text must not leak in)
    if (ide.open && !barOwned) {
      // the pointer: translate press/drag cells into document coords
      // before the editor hears them — main owns the map rail's
      // geometry. A map-rail press jumps to the doc line under the
      // hand; a code press lands at the cell (hscroll included); a
      // gutter press takes the line start; presses in the viewport,
      // console, header or divider are nobody's — swallowed whole.
      auto translateCell = [&](int& r, int& c) {
        const int bodyRowsC = rows0 - 3;
        const bool splitC = cols0 >= 96;
        const int editWC = splitC ? 46 : cols0;
        const bool mapOnC = ide.minimap && splitC && cols0 >= 110;
        const int textWC = editWC - 5 - (mapOnC ? 7 : 0);
        const int row = r - 1;                     // screen row -> body row
                                                   // (bodyTop is 1)
        const int col = c;
        int li = -1, ci = 0;
        if (row >= 0 && row < bodyRowsC) {
          if (mapOnC && col >= editWC - 7 && col < editWC - 1) {
            const dxn3::IdeMini mini =
                dxn3::ideMiniMap(ide, 6, bodyRowsC);
            if (row < static_cast<int>(mini.rows.size())) {
              li = mini.top + row;                 // the map jumps whole lines
              ci = 0;
            }
          } else if (col >= 4 && (!mapOnC || col < 4 + textWC)) {
            li = ide.top + row;
            ci = col - 4 + ide.hcol;
          } else if (col < 4) {
            li = ide.top + row;                    // the gutter: line start
            ci = 0;
          }
        }
        if (li < 0) {
          r = -1;                                  // not ours — swallow
        } else {
          r = li;
          c = ci;
        }
      };
      if (keys.clickR >= 0) translateCell(keys.clickR, keys.clickC);
      if (keys.dragR >= 0) translateCell(keys.dragR, keys.dragC);
      ideKey(ide, keys);
      // the bridge: copy and cut also ride out to the system clipboard
      // (OSC 52) — terminals that honor it keep the OS's clip in sync
      // with the studio's; the internal ring stays the paste truth
      if (keys.ctrlC || keys.ctrlX) {
        const std::string text = dxn3::ideClipText(ide);
        if (!text.empty() && text.size() < 100000) {
          const std::string osc =
              "\x1b]52;c;" + dxn3::ideBase64(text) + "\x1b\\";
          std::fputs(osc.c_str(), stdout);
          std::fflush(stdout);
        }
      }
      // find-mode keystrokes feed the query — never the document
      if (!ide.findOpen &&
          (!keys.typed.empty() || keys.back || keys.enter || keys.del ||
           keys.ctrlD || keys.delWord || keys.delWordFwd || keys.comment ||
           keys.tab || keys.backTab || keys.ctrlX ||
           (keys.ctrlV && !ide.clip.empty()))) {
        ide.dirty = true;
        ide.idle = 0;
      }
      if (keys.up || keys.down || keys.aLeft || keys.aRight ||
          keys.wLeft || keys.wRight || keys.docHome || keys.docEnd ||
          keys.sUp || keys.sDown || keys.sLeft || keys.sRight ||
          keys.sWLeft || keys.sWRight)
        ide.idle = 0;
      if (keys.scroll != 0) { dxn3::ideScroll(ide, keys.scroll); fprintf(stderr, "[AFTER top=%d cur=%d open=%d]", ide.top, ide.curR, ide.open ? 1 : 0); }   // the wheel
                                                // and the ctrl+↑/↓ nudge
      if (keys.ctrlS) {
        std::string err;
        if (ideSave(ide, &err)) ide.console.push_back("engine: saved " + ide.path);
        else ide.console.push_back("engine: " + err);
        ideRun();
        ide.idle = 0;
      } else if (keys.ctrlR) {
        ideRun();
        ide.idle = 0;
      } else if (keys.ctrlN) {
        nextTemplate();
      } else if (keys.ctrlG) {
        const int errLine = dxn3::consoleErrorLine(ide.console);
        if (errLine > 0 && ide.lines.size() > 1) {
          ide.curR = std::clamp(errLine - 1, 0,
                                static_cast<int>(ide.lines.size()) - 1);
          ide.curC = 0;
          ide.console.push_back("engine: jumped to line " +
                                std::to_string(ide.curR + 1));
        } else {
          ide.console.push_back("engine: no error line in the console yet");
        }
      }
      if (keys.esc) {
        if (ide.findOpen) ide.findOpen = false;  // esc leaves the search
        else ide.open = false;                   // esc → play your game
      }
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
        // command-bar whispers: scenes, scripts, screenshots, :w scene
        // targets and snippet names complete themselves as you type —
        // the campaign, the cwd and the exports dir speak up.
        // (cmdBuf never carries the leading ':' — the bar paints that.)
        const struct {
          const char* pre;
          size_t len;
          bool bare;             // whispers even with nothing typed after it
        } qs[] = {{"scene ", 6, false},      {"open ", 5, false},
                  {"screenshot ", 11, true}, {"w ", 2, false},
                  {"snip ", 5, false}};
        for (const auto& q : qs) {
          if (cmdBuf.rfind(q.pre, 0) != 0 ||
              cmdBuf.size() < q.len + (q.bare ? 0 : 1))
            continue;
          const std::string part = cmdBuf.substr(q.len);
          std::string w;
          if (std::strcmp(q.pre, "scene ") == 0) {
            for (const auto& m : dxn3::sceneMatches(part, sceneStems())) {
              if (!w.empty()) w += " · ";
              w += m;
            }
          } else if (std::strcmp(q.pre, "open ") == 0) {
            // scripts match on their FILE name, but whisper the full
            // path — "f" finds sdk/examples/flappy.py
            for (const auto& p : scriptCandidates()) {
              const std::string base =
                  std::filesystem::path(p).filename().string();
              if (base.rfind(part, 0) != 0) continue;
              if (!w.empty()) w += " · ";
              w += p;
            }
          } else if (std::strcmp(q.pre, "screenshot ") == 0) {
            if (part.empty()) {
              // exports/ silent and no name typed: the default speaks —
              // what enter WILL write, before it writes it
              std::string base =
                  game.scene.name.empty() ? "scene" : game.scene.name;
              for (char& ch : base)
                if (ch == ' ' || ch == '/') ch = '_';
              w = "exports/" + base + "-" + std::to_string(shotSeq + 1) +
                  ".png — the default";
            } else {
              // the exports dir speaks: existing shots complete by name
              for (const auto& p : shotCandidates()) {
                const std::string base =
                    std::filesystem::path(p).filename().string();
                if (base.rfind(part, 0) != 0) continue;
                if (!w.empty()) w += " · ";
                w += p;
              }
            }
          } else if (std::strcmp(q.pre, "w ") == 0) {
            // :w writes scene json — the campaign's stems whisper
            for (const auto& m : dxn3::sceneMatches(part, sceneStems())) {
              if (!w.empty()) w += " · ";
              w += "scenes/" + m + ".dxn1.json";
            }
          } else {                           // "snip " — the shelf whispers
            for (const auto& nm : dxn3::ideSnippetNames(ide.path)) {
              if (nm.rfind(part, 0) != 0) continue;
              if (!w.empty()) w += " · ";
              w += nm;
            }
          }
          const int hcol = 2 + static_cast<int>(cmdBuf.size());
          if (!w.empty() && hcol + static_cast<int>(w.size()) < cols - 1)
            scr.text(hcol, rows - 1, w, dxn3::rgb(168, 85, 247));
          break;                 // one whisper per frame — first match wins
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
