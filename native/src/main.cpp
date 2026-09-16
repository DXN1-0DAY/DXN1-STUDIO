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
              else if (mode == Mode::Ide && mod == 3) k.altUp = true;  // the ride
              else if (mod == 0) {
                if (mode == Mode::Ide) k.up = true;
                else if (mode == Mode::File) k.scroll -= 1;
                else k.jump = true;
              }
              break;
            case 'B':
              if (mode == Mode::Ide && mod == 5) k.scroll += 1;
              else if (mode == Mode::Ide && mod == 2) k.sDown = true;
              else if (mode == Mode::Ide && mod == 3) k.altDown = true;
              else if (mod == 0) {
                if (mode == Mode::Ide) k.down = true;
                else if (mode == Mode::File) k.scroll += 1;
              }
              break;
            case 'C':
              if (mode == Mode::Ide && mod == 6) k.sWRight = true;  // word select
              else if (mode == Mode::Ide && mod == 3) k.jumpFwd = true;  // alt+→
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
              else if (mode == Mode::Ide && mod == 3) k.jumpBack = true; // alt+←
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
              const int p = std::atoi(params.c_str());
              if (p == 16) {                 // F3: the hunt — the IDE AND the
                const size_t s16 =          // file view both walk it
                    params.rfind(';');
                const bool shift = s16 != std::string::npos &&
                                   s16 + 1 < params.size() &&
                                   params[s16 + 1] == '2';
                if (shift) k.findBack = true;
                else k.findJump = true;
                break;
              }
              if (mode != Mode::Ide) break;
              // for '~' the params are the KEY NUMBER; a modifier only
              // exists when a ';' is present (3;5~ = ctrl+delete)
              const size_t semi = params.rfind(';');
              const bool ctrl = semi != std::string::npos &&
                                semi + 1 < params.size() &&
                                params[semi + 1] == '5';
              if (p == 3) {
                if (ctrl) k.delWordFwd = true;
                else k.del = true;
              } else if (p == 15) {            // F2: the pins' keyboard —
                const bool shift =             // ctrl plants/pulls, shift
                    semi != std::string::npos &&   // walks back, bare leaps
                    semi + 1 < params.size() &&
                    params[semi + 1] == '2';
                if (ctrl) k.markToggle = true;
                else if (shift) k.markPrev = true;
                else k.markNext = true;
              } else if (p == 16) {            // F3: the hunt — the last
                const bool shift =             // query walks hit to hit,
                    semi != std::string::npos &&   // shift walks back
                    semi + 1 < params.size() &&
                    params[semi + 1] == '2';
                if (shift) k.findBack = true;
                else k.findJump = true;
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
            case 'R':
              // SS3 R (ESC O R) is F3 in the xterm dialect — the same
              // hunt, the other keyboard grammar. A CSI 'R' is a cursor
              // position report; !csi keeps the report silent.
              if (!csi && (mode == Mode::Ide || mode == Mode::File))
                k.findJump = true;
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
        else if (c == 0x1c) k.leap = true;                // Ctrl+\ — to the partner
        else if (c == 0x1a) k.ctrlZ = true;               // Ctrl+Z — undo
        else if (c == 0x19) k.ctrlY = true;               // Ctrl+Y — redo
        else if (c == 0x0f) k.jumpBack = true;            // Ctrl+O — the
                              // jumps' walker, one step into the past
        else if (c == 0x0c) k.ctrlL = true;               // Ctrl+L — fresh console
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
              int top, const std::string& query, const std::string& path,
              int sel, const std::string& status) {
  scr.clear(dxn3::rgb(9, 10, 18));
  const RGB dim = dxn3::rgb(110, 118, 140);
  const RGB txt = dxn3::rgb(220, 222, 232);
  const RGB hit = dxn3::rgb(250, 204, 21);
  const RGB landBg = dxn3::rgb(58, 44, 8);   // the landing's dark amber bed
  scr.railBg(0, dxn3::rgb(22, 12, 36));
  scr.railBg(scr.rows - 1, dxn3::rgb(13, 8, 23));
  scr.textBg(0, 0, " FILE ", dxn3::rgb(233, 213, 255), dxn3::rgb(88, 28, 135));
  {
    std::string head = " " + path + " — " +
                       std::to_string(static_cast<int>(lines.size())) + " lines";
    if (scr.cols > static_cast<int>(head.size()) + 16)
      scr.text(7, 0, head, dxn3::rgb(196, 181, 253));
  }
  if (scr.cols > 40)
    scr.text(scr.cols - static_cast<int>(status.size()), 0, status,
             status == " / to search" ? dim : hit);
  const int maxRow = scr.rows - 1;
  for (int row = 1; row < maxRow; ++row) {
    const int li = top + row - 1;
    if (li >= static_cast<int>(lines.size())) break;
    char num[16];
    std::snprintf(num, sizeof num, "%4d ", li + 1);
    const bool landed = li == sel;
    scr.text(0, row, num, landed ? hit : dim);
    const RGB fg =
        (!query.empty() &&
         lines[li].find(query) != std::string::npos) ? hit : txt;
    if (landed) scr.textBg(5, row, lines[li], fg, landBg);
    else scr.text(5, row, lines[li], fg);
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

bool ideSave(IdeState& ide, std::string* err, bool* bakKept = nullptr) {
  // the pen's second copy: the file that exists becomes <path>.bak the
  // moment this save starts — the scene's law (.bak kept), now every
  // document's. A first save has no past to keep; a failed copy is a
  // note, never a refusal — the save goes on.
  std::error_code ec;
  bool bak = false;
  if (std::filesystem::exists(ide.path, ec)) {
    std::filesystem::copy_file(
        ide.path, ide.path + ".bak",
        std::filesystem::copy_options::overwrite_existing, ec);
    bak = !ec;
  }
  if (bakKept) *bakKept = bak;
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

  // zen: the console rail hides and the body breathes — two more rows
  // of code on every screen. The searchlight still gets its row when
  // it is up (a query you cannot see is a query that cannot end).
  const int consoleRows = ide.zen ? 0 : 2;
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
  // where you are, always: the header carries the honest line:col —
  // and when a selection rides with the hand, how much it holds
  std::string pos = "  Ln " + std::to_string(ide.curR + 1) + " · Col " +
                    std::to_string(ide.curC + 1);
  if (ide.zen) pos += " · zen";               // the quiet says its name
  if (ide.wrap) pos += " · wrap";             // the fold says its name
  if (!ide.marks.empty())
    pos += " · pins " + std::to_string(ide.marks.size());  // the pins count,
                                                // at a glance in big files
  if (const int selN = dxn3::ideSelCount(ide); selN > 0)
    pos += " · sel " + std::to_string(selN);
  if (!ide.touched.empty())
    pos += " · " + std::to_string(ide.touched.size()) +
           " changed";               // the census at a glance — LAST in the
                                     // line, so a crowded header sheds it
                                     // first and keeps the older truths
  // the header's pos speaks in dot-joined segments; a crowded row sheds
  // WHOLE segments from the tail — never a half-truth, never a mangled
  // number. The pins survive where a naive all-or-nothing guard would
  // have silenced the whole line.
  while (!pos.empty() &&
         24 + static_cast<int>(file.size() + pos.size()) + 2 >= scol) {
    const auto cut = pos.rfind(" · ");
    if (cut == std::string::npos) { pos.clear(); break; }
    pos.resize(cut);
  }
  if (!pos.empty())
    scr.text(24 + static_cast<int>(file.size()), 0, pos, dxn3::rgb(110, 118, 140));

  // the editor pane — the minimap rents its rail from the code's right
  // edge when the terminal is wide enough to spare it (six map columns,
  // one gap, one divider); :minimap can always send it home. The gutter
  // earns a column per extra digit — the SAME rule the pointer's
  // translation speaks, so a click and a pixel always agree.
  const bool mapOn = ide.minimap && split && cols >= 110;
  const int mapW = 6;
  const int G = dxn3::ideGutterWidth(static_cast<int>(ide.lines.size()));
  const int mapX = editW - 1 - mapW;         // map cols [mapX, mapX + mapW)
  const int textW = editW - 1 - G - (mapOn ? mapW + 1 : 0);   // code after gutter
  ide.lastTextW = textW;               // the eye's walk speaks this width
  // the fold's layout: built fresh EVERY draw — rows, owners, offsets
  // — O(the document's bytes), no stamps, no stale caches. Wrap OFF
  // builds the identity (one line, one row), so every geometry law
  // below speaks ONE table either way. hcol only slides when the fold
  // sleeps (a folded line has nothing left to slide past).
  const dxn3::IdeWrap wrap = dxn3::ideWrapBuild(ide, textW);
  const int curV = dxn3::ideWrapRowOf(wrap, ide.curR, ide.curC);
  const int maxTop = std::max(0, wrap.rows - bodyRows);
  ide.top = std::clamp(ide.top, 0, maxTop);
  if (curV < ide.top) ide.top = curV;
  if (curV >= ide.top + bodyRows) ide.top = curV - bodyRows + 1;
  ideHscroll(ide, textW);              // long lines slide (asleep under wrap)
  scr.rect(0, static_cast<float>(bodyTop * 2),
           static_cast<float>(split ? editW - 1 : cols - 1),
           static_cast<float>((bodyTop + bodyRows) * 2), paneBg);
  for (int r = 0; r < bodyRows; ++r) {
    const int v = ide.top + r;                   // a VISUAL row
    if (v >= wrap.rows) break;
    const int li = wrap.rowLine[static_cast<size_t>(v)];
    const int off = wrap.rowOff[static_cast<size_t>(v)];
    const bool firstRow = off == 0;              // the line's naming row
    const bool onCursor = v == curV;
    const bool pinned = dxn3::ideMarkHas(ide, li);
    std::string gutter;
    if (firstRow) {
      const int shown = ide.relnum ? [&] {
        int d = li - ide.curR;             // the vim way: the gutter
        if (d < 0) d = -d;                 // counts from the hand, and the
        return d == 0 ? li + 1 : d;        // hand's line keeps its name
      }() : li + 1;
      const std::string num = std::to_string(shown);
      const int pad = G - 1 - static_cast<int>(num.size());
      gutter = (pad > 0 ? std::string(static_cast<size_t>(pad), ' ')
                        : std::string()) +
               num + " ";
    } else {
      // the fold's continuation: a dim ellipsis where the number was —
      // the line's name sits on its first row only
      gutter = std::string(static_cast<size_t>(std::max(0, G - 2)), ' ') + "…";
    }
    scr.text(0, bodyTop + r, gutter,
             pinned ? dxn3::rgb(250, 204, 21)
                    : (onCursor ? dxn3::rgb(196, 181, 253)
                                : dxn3::rgb(84, 72, 120)));
    if (onCursor) scr.railBg(bodyTop + r, selBg);
    // the slide (fold off): every row shows [hcol, hcol + textW);
    // the fold (wrap on): every row shows its own [off, off + textW)
    const std::string& ln = ide.lines[static_cast<size_t>(li)];
    if (!ide.wrap && ide.hcol > 0)
      scr.text(G - 1, bodyTop + r, "…", dxn3::rgb(96, 104, 126));
    if (pinned) scr.text(G - 1, bodyTop + r, "◆",
                         dxn3::rgb(250, 204, 21));  // the pin owns the gutter's
                                                    // edge — the … waits
    std::string slice;
    if (ide.wrap) {
      const size_t take = std::min<size_t>(
          static_cast<size_t>(textW), ln.size() - static_cast<size_t>(off));
      slice = ln.substr(static_cast<size_t>(off), take);
    } else if (ide.hcol > 0) {
      slice = static_cast<int>(ln.size()) > ide.hcol
                  ? ln.substr(static_cast<size_t>(ide.hcol))
                  : std::string();
    } else {
      slice = ln;
    }
    drawCodeLine(scr, G, bodyTop + r, slice, textW);
  }
  // the ruler: honest guides at 79 and 99 — a dim dot only where the
  // cell is blank, so the guide never paints over your code. The fold
  // sleeps the guides: a wrapped line has no honest column to name.
  if (ide.ruler && !ide.wrap) {
    const RGB rulerC = dxn3::rgb(64, 54, 104);
    for (int rc : {79, 99}) {
      const int scol = G + rc - ide.hcol;
      if (scol < G || scol >= G + textW) continue;   // out of the pane
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
    for (int v = std::max(ide.top, wrap.lineFirst[static_cast<size_t>(r0)]);
         v < std::min(ide.top + bodyRows,
                      wrap.lineFirst[static_cast<size_t>(r1) + 1]); ++v) {
      const int li = wrap.rowLine[static_cast<size_t>(v)];
      const int off = wrap.rowOff[static_cast<size_t>(v)];
      const std::string& l = ide.lines[static_cast<size_t>(li)];
      const int a = (li == r0) ? c0 : 0;
      const int b = (li == r1) ? std::min<int>(c1, static_cast<int>(l.size()))
                               : static_cast<int>(l.size());
      const int cLo = off + (ide.wrap ? 0 : ide.hcol);   // the row's first cell
      for (int c = std::max(a, cLo); c < std::min(b, cLo + textW); ++c)
        scr.textBg(G + c - cLo, bodyTop + (v - ide.top),
                   std::string(1, l[static_cast<size_t>(c)]), paneBg, selGlow);
    }
  }
  // the cursor: inverse video on the exact cell — its VISUAL row under
  // the fold, its line's row under the identity; the same formula speaks
  if (curV >= ide.top && curV < ide.top + bodyRows) {
    const int row = bodyTop + (curV - ide.top);
    const std::string& l = ide.lines[static_cast<size_t>(ide.curR)];
    const char ch = ide.curC < static_cast<int>(l.size()) ? l[static_cast<size_t>(ide.curC)] : ' ';
    scr.textBg(G + ide.curC - ide.hcol -
                   wrap.rowOff[static_cast<size_t>(curV)],
               row, std::string(1, ch), paneBg, dxn3::rgb(167, 139, 250));
  }
  // the bracket's partner glows across the file — the cursor's own cell
  // already burns inverse video, so the glow lands on the partner (and
  // on the anchor behind the cursor when that is the bracket held)
  {
    int br = -1, bc = -1;
    if (ideMatchBracket(ide, br, bc)) {
      const RGB glowBg = dxn3::rgb(52, 40, 92);
      auto glow = [&](int r2, int c2) {
        if (r2 < 0 || r2 >= static_cast<int>(ide.lines.size())) return;
        const int v2 = dxn3::ideWrapRowOf(wrap, r2, c2);
        if (v2 < ide.top || v2 >= ide.top + bodyRows) return;
        const std::string& l2 = ide.lines[static_cast<size_t>(r2)];
        if (c2 < 0 || c2 >= static_cast<int>(l2.size())) return;
        const int col = G + c2 - ide.hcol -
                        wrap.rowOff[static_cast<size_t>(v2)];
        if (col < G || col >= G + textW) return;    // out of the pane
        scr.textBg(col, bodyTop + (v2 - ide.top),
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
    size_t hi = 0;
    for (int r = 0; r < bodyRows; ++r) {
      const int v = ide.top + r;
      if (v >= wrap.rows) break;
      const int li = wrap.rowLine[static_cast<size_t>(v)];
      const int off = wrap.rowOff[static_cast<size_t>(v)];
      while (hi < ide.findHits.size() && ide.findHits[hi].first < li) ++hi;
      for (size_t i = hi; i < ide.findHits.size() &&
                          ide.findHits[i].first == li; ++i) {
        const int hitC = ide.findHits[i].second;           // the real column
        const int c = hitC - off - ide.hcol;               // fold or slide
        const int room = textW - c;
        if (room <= 0 || c < 0) continue;   // past either edge of the row
        std::string slice = ide.lines[static_cast<size_t>(li)].substr(
            static_cast<size_t>(hitC),
            std::min<size_t>(ide.findQ.size(), static_cast<size_t>(room)));
        scr.textBg(G + c, bodyTop + r, slice, paneBg,
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
    const dxn3::IdeMini mini = dxn3::ideMiniMap(ide, mapW, bodyRows, &wrap);
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
      if (mr.mark)                             // the pin: an amber bar at the
        scr.text(mapX, row, "▌",               // map's edge, drawn last so it
                 dxn3::rgb(250, 204, 21));     // never drowns in the bars
      else if (dxn3::ideTouchHas(ide, li))     // the session's hand: an
        scr.text(mapX, row, "·",               // emerald tick on the map's
                 dxn3::rgb(52, 211, 153));     // edge — see where you wrote
    }
  }

  // the console rail: the game's prints + engine notes, honestly shown —
  // unless zen keeps the quiet: the rail hides, receipts gather silently,
  // and only the searchlight still claims its row while it is up.
  const int c0 = rows - consoleRows;
  auto paintFind = [&](int row) {
    // the searchlight has the rail: query, hits, the way out
    std::string fb = ide.findCase ? " / find(Aa): " : " / find: ";
    fb += ide.findQ + "_ ";
    if (ide.findQ.empty()) fb += "type to search the whole file";
    else if (ide.findHits.empty()) fb += "no matches — esc to close";
    else fb += std::to_string(ide.findSel + 1) + "/" +
               std::to_string(ide.findHits.size()) +
               " · enter/F3 next · esc done";
    scr.text(1, row, fb.substr(0, static_cast<size_t>(cols - 3)), dxn3::rgb(250, 204, 21));
  };
  if (ide.zen && ide.findOpen) {
    scr.railBg(rows - 1, dxn3::rgb(10, 7, 18));
    paintFind(rows - 1);
  } else if (!ide.zen) {
    scr.railBg(c0, dxn3::rgb(10, 7, 18));
    scr.railBg(c0 + 1, dxn3::rgb(10, 7, 18));
    size_t n = ide.console.size();
    const std::string l1 = n >= 1 ? ide.console[n - 1] : "";
    const std::string l2 = n >= 2 ? ide.console[n - 2] : "";
    scr.text(1, c0, l1.substr(0, static_cast<size_t>(cols - 3)), dxn3::rgb(148, 156, 180));
    if (ide.findOpen) {
      paintFind(c0 + 1);
    } else {
      // a traceback in the console? offer the one-keystroke jump to the line
      const int errLine = dxn3::consoleErrorLine(ide.console);
      const bool errorUp = errLine > 0;
      // the walker owns the hint while it stands in the PAST: where it
      // is in the ledger (1-based, oldest first — the same order the
      // ">" bookmark counts in), and the two ways home. Context that
      // teaches the mode you are IN. A bookmark on the newest entry is
      // the walker at now — the plain hints come back, the same law
      // the :jumps listing's ">" speaks.
      const int ledgerN = static_cast<int>(ide.jumps.size());
      const bool walking =
          ide.jumpIx >= 0 && ide.jumpIx < ledgerN - 1;
      const std::string hint =
          walking
              ? " walk " + std::to_string(ide.jumpIx + 1) + "/" +
                std::to_string(ledgerN) +
                " of the ledger · alt+→ climbs out · ctrl+o deeper "
              : (errorUp
                     ? " ctrl+g jumps to line " + std::to_string(errLine) +
                       " · ctrl+z undo · ctrl+f find · esc play "
                     : " ctrl+r run · ctrl+z undo · ctrl+f find · ctrl+\\ leap · F2 pins · "
                       "ctrl+c/x/v clipboard · esc play ");
      scr.text(1, c0 + 1, hint.substr(0, static_cast<size_t>(cols - 3)),
               errorUp && !walking ? dxn3::rgb(248, 113, 113)
                                   : dxn3::rgb(84, 72, 120));
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
                   "       ctrl+f find · enter next hit · F3/shift+F3 walk the hits\n"
                   "       ctrl+d duplicate lines · ctrl+\\ leap to the partner bracket\n"
                   "       tab snippet/indent\n"
                   "       shift+tab dedent · ctrl+/ comment\n"
                   "       shift+arrows select · shift+ctrl+←/→ select words\n"
                   "       ctrl+o / alt+← walk the jumps back · alt+→ walks out\n"
                   "       ctrl+l clear the console · ctrl+n template · ctrl+g error line · ctrl+p screenshot\n"
                   "       F2 next pin · shift+F2 previous pin · ctrl+F2 plant/pull a pin\n"
                   "       :minimap the document's map rail · :ruler guides · :stats · :zen the quiet\n"
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
  // the sdk lives beside the BINARY — the studio's own installation —
  // not beside the user's cwd: a studio launched from anywhere hosts
  // games the same way. (<repo>/native/build/dxn3-native → <repo>/sdk;
  // a flat install keeps the old "sdk beside the cwd" answer.)
  std::filesystem::path sdkPath = std::filesystem::current_path() / "sdk";
  {
    std::error_code ec;
    const auto exe = std::filesystem::read_symlink("/proc/self/exe", ec);
    if (!ec) {
      const auto beside = exe.parent_path().parent_path().parent_path() / "sdk";
      if (std::filesystem::exists(beside, ec)) sdkPath = beside;
    }
  }
  const std::string sdkDir = sdkPath.string();
  bool ideBoot = false;
  if (isatty(STDIN_FILENO) && !wantShot) {   // interactive? engine first.
    if (argc == 1) {                          // dxn3, no args → the engine IDE
      ideBoot = true;
      ide.path = "untitled.py";
      ide.lines = starterLines();
      ide.console.push_back("engine: you start with nothing — edit, then ctrl+r");
      dxn3::ideRecentPush(ide.recent, ide.path);
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
    dxn3::ideRecentPush(ide.recent, ide.path);   // the boot doc, remembered
  }

  // the session's stage of work: the pen (:w/:wq) follows it. The
  // studio IS the boot stage for interactive runs; every verb or key
  // that takes the stage renews the claim. A play-only session (a
  // scene argument, no studio yet) keeps :w pointed at the scene.
  bool ideEver = ideBoot;
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
  bool macroPlaying = false;             // the register's playback is live
  size_t macroIx = 0;                    // the register's walk
  int macroRuns = 1;                     // :macro N — the take N times
  int playedRuns = 1;                    // how many runs the receipt names
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
    ide.marks.clear();  // pins belong to the document they were planted in
    ide.dirty = true;
    ide.idle = 0;
    ide.console.push_back("engine: template — " + name + " (" +
                          tpls[idx].ext + ", ctrl+n again to cycle)");
    dxn3::ideRecentPush(ide.recent, ide.path);
  };

  // any script becomes the live document — :open and :recent share one
  // honest path: read it, take the stage, remember it in the ledger
  auto takeStage = [&]() {
    if (!ide.open) ide.open = true;
    ideEver = true;
  };
  auto openScript = [&](const std::string& path,
                        bool keepJumps = false) -> std::string {
    std::ifstream f(path, std::ios::binary);
    if (!f.good()) return "no such file: " + path;
    host.stop();                     // a new document owns the stage
    ide.hostUp = false;
    // the welcome back, first half: leaving a file plants its hand —
    // where the cursor stood the moment you walked away
    if (!ide.path.empty())
      dxn3::ideDocCurRemember(ide.docCur, ide.path, ide.curR, ide.curC);
    ide.lines.clear();
    std::string ln;
    while (std::getline(f, ln)) {
      if (!ln.empty() && ln.back() == '\r') ln.pop_back();
      ide.lines.push_back(ln);
    }
    if (ide.lines.empty()) ide.lines.push_back("");
    ide.path = path;
    ide.undo.clear();                // a new document, a fresh history
    ide.redo.clear();
    // a jump belongs to the doc it leapt in — but a :fresh reload is
    // the SAME document re-read: the session's history doesn't lie,
    // so the walker keeps its ledger when the caller says so.
    if (!keepJumps) ide.jumps.clear();
    dxn3::ideTouchClear(ide);        // a page just opened is a clean page —
                                     // the census counts THIS session's hand
    ide.lastTyping = ide.lastBack = false;
    ide.curR = ide.curC = ide.top = 0;
    dxn3::ideSelClear(ide);          // no stale selection rides along
    ide.marks.clear();  // pins belong to the document they were planted in
    ide.hcol = 0;
    ide.tpl = -1;
    ide.findOpen = false;            // the searchlight rests
    ide.findQ.clear();
    ide.findHits.clear();
    ide.findSel = -1;
    // the welcome back, second half: a reopen is a continuation, not a
    // rewind — the remembered hand lands (clamped to what the file is
    // NOW, honest if it shrank) and the view jumps with it
    bool resumed = false;
    if (const auto hand = dxn3::ideDocCurLookup(ide.docCur, path)) {
      const auto [r, c] = dxn3::ideDocCurLand(ide.lines, *hand);
      ide.curR = r;
      ide.curC = c;
      ide.hcol = c;
      ide.top = std::max(0, r - 4);  // the landing stays mid-screen
      dxn3::ideJumpPush(ide, r);         // the welcome back IS a leap
      resumed = true;
    }
    takeStage();
    ide.dirty = true;
    ide.idle = 0;
    dxn3::ideRecentPush(ide.recent, path);
    ide.console.push_back(
        resumed ? "engine: opened " + path + " — the hand returns to line " +
                      std::to_string(ide.curR + 1)
                : "engine: opened " + path);
    game.say("open " + path, 1.6);
    return "";
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
  int fileSel = -1;                 // the hunt's landing: the hit the view
                                    // stands on (-1 = never landed)
  std::string fileQ;                // the committed query — it survives the
                                    // enter, so F3/shift+F3 can walk its hits
  const int fileN = static_cast<int>(fileLines.size());   // hoisted so the
                                    // hunt's law and its rail read one truth
  const auto fileMatch = [&](int li) {
    return li >= 0 && li < fileN &&
           fileLines[static_cast<size_t>(li)].find(fileQ) !=
               std::string::npos;
  };

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
    // the pane's honest text width — the draw's SAME rule, spoken
    // wherever a click, a wheel notch, an edge pull or :center needs
    // the fold's map without rebuilding the draw's whole geometry
    auto paneTextW = [&]() {
      const bool sp = cols0 >= 96;
      const int ew = sp ? 46 : cols0;
      const bool mo = ide.minimap && sp && cols0 >= 110;
      return ew - 1 -
             dxn3::ideGutterWidth(static_cast<int>(ide.lines.size())) -
             (mo ? 7 : 0);
    };

  // the verb dispatch: ONE law for the bar's enter and the macro's
  // playback — parse the line, walk the chain, take the stage. Returns
  // true when the verb asks the studio to quit (:q, :wq).
  auto runCommand = [&](const std::string& line) -> bool {
    const dxn3::Cmd cmd = dxn3::parseCommand(line);
    if (cmd.ok() && ide.recording && cmd.verb != "record" &&
        cmd.verb != "macro")
      ide.macro.push_back(line);         // the recorder keeps the raw line
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
          takeStage();
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
            takeStage();
            ide.tpl = hit;
            loadTemplate(hit);
          }
        } else if (cmd.verb == "o" || cmd.verb == "e") {
          // the vim tongue: :o and :e ARE :open — one law, two other
          // names the hands already know. A bare verb reopens the
          // ledger's head; a tail resolves through the ledger first
          // (the same courtesy :recent speaks), then opens honestly.
          takeStage();
          const std::string want = cmd.arg;
          if (want.empty()) {
            if (ide.recent.empty())
              cmdErr = "the ledger is empty — :open a file first";
            else
              cmdErr = openScript(ide.recent.front());   // the head
          } else {
            std::string resolved = want;
            if (!ide.recent.empty()) {
              for (const auto& r : ide.recent) {
                const std::string base =
                    std::filesystem::path(r).filename().string();
                if (r.rfind(want, 0) == 0 || base.rfind(want, 0) == 0) {
                  resolved = r;          // the ledger resolves the tail
                  break;
                }
              }
            }
            cmdErr = openScript(resolved);
          }
        } else if (cmd.verb == "open") {
          if (cmd.arg.empty()) {
            // a bare :open: the ledger's head — what you had last, one
            // word away; an empty ledger refuses with the way out
            if (ide.recent.empty()) {
              cmdErr = "open what? — name a path (:recent lists the ledger)";
              cmdErrT = 3.5f;
            } else {
              const std::string err = openScript(ide.recent.front());
              if (!err.empty()) { cmdErr = err; cmdErrT = 3.5f; }
            }
          } else {
            const std::string err = openScript(cmd.arg);
            if (!err.empty()) { cmdErr = err; cmdErrT = 3.5f; }
          }
        } else if (cmd.verb == "recent") {
          if (cmd.arg.empty()) {
            takeStage();
            // the ledger, read aloud: most recent first, six deep
            if (ide.recent.empty()) {
              ide.console.push_back(
                  "engine: the ledger is empty — :open something first");
            } else {
              std::string list = "engine: recent —";
              for (size_t i = 0; i < ide.recent.size() && i < 6; ++i)
                list += " " + std::to_string(i + 1) + ") " + ide.recent[i];
              ide.console.push_back(list);
            }
          } else {
            const std::string resolved =
                dxn3::ideRecentResolve(ide.recent, cmd.arg);
            if (resolved.empty()) {
              std::string list;
              for (const auto& p : ide.recent)
                if (p.rfind(cmd.arg, 0) == 0)
                  list += (list.empty() ? "" : " · ") + p;
              cmdErr = "ambiguous recent '" + cmd.arg + "' — " + list;
              cmdErrT = 4.f;
            } else if (std::find(ide.recent.begin(), ide.recent.end(),
                                 resolved) == ide.recent.end()) {
              cmdErr = "no such recent file: " + cmd.arg;
              cmdErrT = 3.5f;
            } else {
              const std::string err = openScript(resolved);
              if (!err.empty()) { cmdErr = err; cmdErrT = 3.5f; }
            }
          }
        } else if (cmd.verb == "goto") {
          // jump the editor to a line — ctrl+g's sibling for lines
          // without a traceback. +N/-N ride from where the hand stands.
          // The studio takes the stage.
          takeStage();
          ide.findOpen = false;
          const int target = dxn3::ideGotoTarget(
              ide, cmd.num, cmd.rel);
          const int step = static_cast<int>(cmd.num);
          const int from = ide.curR;     // the jump's law: a CHANGE of
          ide.curR = target;             // line plants — a stand does not
          if (target != from) dxn3::ideJumpPush(ide, target);
          ide.curC = 0;
          ide.top = std::max(0, ide.curR - 4);   // the jump lands mid-screen
          ide.lastTyping = ide.lastBack = false;
          dxn3::ideSelClear(ide);                // the jump drops the selection
          ide.console.push_back(
              cmd.rel ? "engine: jumped " +
                            std::string(step >= 0 ? "down " : "up ") +
                            std::to_string(std::abs(step)) +
                            " — now at line " +
                            std::to_string(ide.curR + 1)
                      : "engine: jumped to line " +
                            std::to_string(ide.curR + 1));
        } else if (cmd.verb == "mark") {
          // plant or pull a pin on the hand's line — a bookmark, not an
          // edit: F2 leaps between pins, :marks lists them
          takeStage();
          const bool on = dxn3::ideMarkToggle(ide, ide.curR);
          ide.console.push_back(
              on ? "engine: pin planted on line " +
                       std::to_string(ide.curR + 1) +
                       " — F2 leaps, :marks lists"
                 : "engine: pin pulled from line " +
                       std::to_string(ide.curR + 1));
        } else if (cmd.verb == "marks") {
          takeStage();
          if (ide.marks.empty()) {
            ide.console.push_back(
                "engine: no pins — :mark plants one on the hand's line");
          } else {
            std::string list = "engine: pins —";
            for (size_t i = 0; i < ide.marks.size(); ++i)
              list += " " + std::to_string(i + 1) + ") Ln " +
                      std::to_string(ide.marks[i] + 1);
            ide.console.push_back(list);
          }
        } else if (cmd.verb == "bm") {
          // leap to a pin: a bare :bm takes the next (wrapping), :bm N
          // takes the Nth — the :marks order, top of the file first
          takeStage();
          int to = -1;
          if (cmd.arg.empty()) {
            to = dxn3::ideMarkNext(ide, ide.curR);
          } else if (static_cast<int>(cmd.num) >= 1 &&
                     static_cast<int>(cmd.num) <=
                         static_cast<int>(ide.marks.size())) {
            to = ide.marks[static_cast<size_t>(
                static_cast<int>(cmd.num) - 1)];
          }
          if (to < 0) {
            ide.console.push_back(
                ide.marks.empty()
                    ? "engine: no pins yet — :mark plants one on this line"
                    : "engine: no such pin — :marks lists " +
                          std::to_string(ide.marks.size()));
          } else {
            ide.findOpen = false;              // the searchlight rests
            ide.curR = to;
            ide.curC = 0;
            ide.top = std::max(0, ide.curR - 4);   // the leap lands mid-screen
            dxn3::ideSelClear(ide);                // the leap drops the selection
            ide.console.push_back("engine: the hand leaps to the pin at line " +
                                  std::to_string(to + 1));
          }
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
              takeStage();
              dxn3::ideInsertBlock(ide, *block);
              ide.console.push_back("engine: snippet " + hit + " — " +
                                    std::to_string(block->size()) +
                                    " lines landed");
            }
          }
        } else if (cmd.verb == "zen") {
          // the quiet: the console rail hides, the body gains its two
          // rows; the searchlight still shows when it is up. Receipts
          // gather silently until the quiet ends — and the wake speaks
          // its ledger: what gathered in the dark, replayed newest
          // last, so the two-row window never buries the quiet's work.
          takeStage();
          ide.zen = !ide.zen;
          if (ide.zen) {
            ide.zenSince = ide.console.size();  // the ledger's first page
            ide.console.push_back(
                "engine: zen — the rail rests, the body breathes "
                "(:zen wakes it)");
          } else {
            size_t kept = 0;
            const std::string digest =
                dxn3::ideZenDigest(ide.console, ide.zenSince, &kept);
            ide.console.push_back(
                kept == 0
                    ? "engine: the rail is back — the quiet gathered "
                      "nothing"
                    : "engine: the rail is back — zen kept " +
                          std::to_string(kept) +
                          (kept == 1 ? " receipt" : " receipts"));
            if (!digest.empty())
              ide.console.push_back("engine: zen's ledger — " + digest);
          }
        } else if (cmd.verb == "ruler") {
          takeStage();
          ide.ruler = !ide.ruler;
          ide.console.push_back(ide.ruler
                                    ? "engine: ruler on — guides at 79 and 99"
                                    : "engine: ruler off");
        } else if (cmd.verb == "minimap") {
          takeStage();
          ide.minimap = !ide.minimap;
          ide.console.push_back(
              ide.minimap ? "engine: minimap on — the document rides the "
                            "pane's right edge"
                          : "engine: minimap off");
        } else if (cmd.verb == "trim") {
          takeStage();
          const int swept = dxn3::ideTrimTrailing(ide);
          ide.console.push_back(
              swept > 0
                  ? "engine: trimmed " + std::to_string(swept) + " line" +
                        (swept == 1 ? "" : "s") + " of trailing air"
                  : "engine: nothing to trim — the doc is already clean");
        } else if (cmd.verb == "cases") {
          takeStage();
          ide.findCase = !ide.findCase;
          if (ide.findOpen) dxn3::ideFindRefresh(ide);   // re-aim the light
          ide.console.push_back(
              ide.findCase
                  ? "engine: find is case-SENSITIVE — Hello only greets Hello"
                  : "engine: find forgives case — hello finds HELLO");
        } else if (cmd.verb == "sort") {
          takeStage();
          bool byNum = false;
          const int ordered = dxn3::ideSortSel(ide, &byNum);
          ide.console.push_back(
              ordered > 0
                  ? "engine: sorted " + std::to_string(ordered) +
                        " line" + (ordered == 1 ? "" : "s") +
                        (byNum ? " by their numbers — 2 before 10"
                               : " — A before B") +
                        ", one undo step takes it back"
                  : "engine: select the lines to sort first "
                    "(shift+arrows, or drag)");
        } else if (cmd.verb == "rsort") {
          takeStage();
          bool byNum = false;
          const int ordered = dxn3::ideRsortSel(ide, &byNum);
          ide.console.push_back(
              ordered > 0
                  ? "engine: sorted " + std::to_string(ordered) +
                        " line" + (ordered == 1 ? "" : "s") +
                        (byNum ? " by their numbers, biggest first"
                               : " land-ward — Z before A") +
                        ", one undo step"
                  : "engine: select the lines to rsort first "
                    "(shift+arrows, or drag)");
        } else if (cmd.verb == "upper" || cmd.verb == "lower" ||
                   cmd.verb == "title") {
          takeStage();
          const int mode =
              cmd.verb == "upper" ? 1 : cmd.verb == "lower" ? 0 : 2;
          const int moved = dxn3::ideCaseSel(ide, mode);
          ide.console.push_back(
              moved > 0
                  ? "engine: " + std::to_string(moved) + " letter" +
                        (moved == 1 ? "" : "s") + " " +
                        (mode == 1 ? "shouted"
                                   : mode == 0 ? "whispered" : "stood up") +
                        " — one undo step takes it back"
                  : "engine: select text first (shift+arrows, or drag)");
        } else if (cmd.verb == "uniq") {
          takeStage();
          const int gone = dxn3::ideUniqSel(ide);
          ide.console.push_back(
              gone > 0
                  ? "engine: " + std::to_string(gone) + " duplicate line" +
                        (gone == 1 ? "" : "s") +
                        " collapsed — one undo step takes it back"
                  : "engine: nothing to collapse — no line repeats "
                    "back-to-back");
        } else if (cmd.verb == "s") {
          // the swap: :s/old/new — every byte-exact occurrence traded
          // on the selection's lines (or the hand's line). The parse
          // guaranteed one '/'; the handler splits on the FIRST (new
          // may carry more, old may not — old ends at the first '/').
          takeStage();
          const size_t cut = cmd.arg.find('/');
          std::string oldStr = cmd.arg.substr(0, cut);
          const std::string newStr = cmd.arg.substr(cut + 1);
          // the query's tongue: an EMPTY old that still carries the
          // slash speaks the searchlight's live query as the old — the
          // find and the swap share one bed law (a bare :s with no
          // slash refuses as always; nothing is guessed)
          bool borrowed = false;
          if (oldStr.empty() && cut != std::string::npos &&
              !ide.findQ.empty()) {
            oldStr = ide.findQ;
            borrowed = true;
          }
          if (oldStr.empty()) {
            cmdErr = "usage: :s/old/new — an empty old replaces nothing";
            cmdErrT = 3.5f;
          } else {
            int linesTouched = 0;
            const int made = dxn3::ideReplaceSel(ide, oldStr, newStr,
                                                 &linesTouched);
            ide.console.push_back(
                made > 0
                    ? "engine: " +
                          std::string(borrowed ? "the query's old — "
                                               : "") +
                          std::to_string(made) + " replaced on " +
                          std::to_string(linesTouched) + " line" +
                          (linesTouched == 1 ? "" : "s") + " — one undo "
                          "step takes it back"
                    : "engine: '" + oldStr +
                          "' is not on this bed — nothing replaced");
          }
        } else if (cmd.verb == "sa") {
          // the swap's other face: the WHOLE document is the bed —
          // the same exact-match law, ideReplaceAll speaks it.
          takeStage();
          const size_t cutA = cmd.arg.find('/');
          std::string oldStrA = cmd.arg.substr(0, cutA);
          const std::string newStrA = cmd.arg.substr(cutA + 1);
          // the query's tongue, the whole bed's face — the same borrow
          bool borrowedA = false;
          if (oldStrA.empty() && cutA != std::string::npos &&
              !ide.findQ.empty()) {
            oldStrA = ide.findQ;
            borrowedA = true;
          }
          if (oldStrA.empty()) {
            cmdErr = "usage: :sa/old/new — an empty old replaces nothing";
            cmdErrT = 3.5f;
          } else {
            int linesTouched = 0;
            const int made = dxn3::ideReplaceAll(ide, oldStrA, newStrA,
                                                 &linesTouched);
            ide.console.push_back(
                made > 0
                    ? "engine: " +
                          std::string(borrowedA ? "the query's old — "
                                                : "") +
                          std::to_string(made) + " replaced on " +
                          std::to_string(linesTouched) + " line" +
                          (linesTouched == 1 ? "" : "s") +
                          " across the document — one undo step"
                    : "engine: '" + oldStrA +
                          "' is not in this document — nothing replaced");
          }
        } else if (cmd.verb == "rev") {
          takeStage();
          const int flipped = dxn3::ideRevSel(ide);
          ide.console.push_back(
              flipped > 0
                  ? "engine: " + std::to_string(flipped) + " line" +
                        (flipped == 1 ? "" : "s") +
                        " flipped — one undo step takes it back"
                  : "engine: select the lines to flip first "
                    "(shift+arrows, or drag)");
        } else if (cmd.verb == "shuffle") {
          // the dice: the bed deals into random order — a seed replays
          // the deal exactly, a bare verb rolls one and names it. The
          // sort family's laws, one undo step, the pins riding their
          // content.
          takeStage();
          unsigned used = 0;
          const int dealt = dxn3::ideShuffleSel(
              ide, static_cast<unsigned>(cmd.num), !cmd.arg.empty(), &used);
          ide.console.push_back(
              dealt > 0
                  ? "engine: " + std::to_string(dealt) + " line" +
                        (dealt == 1 ? "" : "s") + " shuffled (seed " +
                        std::to_string(used) + ")" +
                        (cmd.arg.empty()
                             ? " — :shuffle " + std::to_string(used) +
                                   " replays the deal, one undo takes it back"
                             : " — the same seed deals the same order") +
                        ""
                  : "engine: select the lines to shuffle first "
                    "(shift+arrows, or drag)");
        } else if (cmd.verb == "indent" || cmd.verb == "dedent") {
          takeStage();
          const bool out = cmd.verb == "dedent";
          const int moved = dxn3::ideDentSel(ide, out);
          ide.console.push_back(
              moved > 0
                  ? "engine: " + std::to_string(moved) + " line" +
                        (moved == 1 ? "" : "s") +
                        (out ? " stepped back left — one undo step takes "
                              "it there again"
                             : " stepped right — one undo step takes it back")
                  : out ? "engine: select the lines to dedent first "
                          "(shift+arrows, or drag)"
                        : "engine: select the lines to indent first "
                          "(shift+arrows, or drag)");
        } else if (cmd.verb == "lift" || cmd.verb == "drop") {
          takeStage();
          const bool down = cmd.verb == "drop";
          const int rode = dxn3::ideMoveSel(ide, down);
          ide.console.push_back(
              rode > 0
                  ? "engine: " + std::to_string(rode) + " line" +
                        (rode == 1 ? "" : "s") +
                        (down ? " dropped one line — the pins rode along"
                              : " lifted one line — the pins rode along")
                  : down ? "engine: nothing below to drop into"
                         : "engine: nothing above to lift into");
        } else if (cmd.verb == "dup") {
          takeStage();
          const int echoed = dxn3::ideDupSel(ide);
          ide.console.push_back(
              "engine: duplicated " + std::to_string(echoed) + " line" +
              (echoed == 1 ? "" : "s") + " — the copies sit below");
        } else if (cmd.verb == "join") {
          takeStage();
          const int folded = dxn3::ideJoinSel(ide);
          ide.console.push_back(
              folded > 0
                  ? "engine: folded " + std::to_string(folded) +
                        " lines into one — one undo step takes it back"
                  : "engine: nothing to fold — select the lines, or stand "
                    "on a line with one below");
        } else if (cmd.verb == "hist") {
          // the second chance, listed: the ledger's names, newest
          // first, the depth honest, the redo's head riding after
          takeStage();
          const std::string h = dxn3::ideHistWhisper(ide);
          ide.console.push_back(
              h.empty()
                  ? "engine: the ledger is empty — every edit you make "
                    "lands here (ctrl+z walks it back)"
                  : "engine: the ledger, newest first — " + h);
        } else if (cmd.verb == "undo") {
          // the second chance, spoken from the bar — the keys' walk,
          // ONE law: the same step, the same receipt, the same refusal
          takeStage();
          if (dxn3::ideUndo(ide)) {
            ide.dirty = true;          // the game re-runs on the restored code
            ide.idle = 0;
            ide.console.push_back(dxn3::ideUndoReceipt(ide));
          } else {
            ide.console.push_back("engine: nothing to undo");
          }
        } else if (cmd.verb == "redo") {
          takeStage();
          if (dxn3::ideRedo(ide)) {
            ide.dirty = true;
            ide.idle = 0;
            ide.console.push_back(dxn3::ideRedoReceipt(ide));
          } else {
            ide.console.push_back("engine: nothing to redo");
          }
        } else if (cmd.verb == "words") {
          // the census: what the document says most, ranked and capped,
          // the case forgiven — a mirror for the code you are writing
          takeStage();
          const std::string w = dxn3::ideWordsWhisper(ide);
          ide.console.push_back(
              w.empty()
                  ? "engine: the census is empty — the document has no "
                    "words yet"
                  : "engine: the census, most-said first — " + w);
        } else if (cmd.verb == "todo") {
          // the marker hunt: the debts the document owes, line-led
          takeStage();
          const std::string t = dxn3::ideTodoWhisper(ide);
          ide.console.push_back(
              t.empty()
                  ? "engine: no markers in the file — TODO/FIXME/XXX/HACK "
                    "would land here"
                  : "engine: the markers, line-led — " + t);
        } else if (cmd.verb == "jumps") {
          // the leaps, listed: the lines the hand changed by LEAPING —
          // :goto, the pins' F2, the welcome back — newest first, the
          // "now" leading, a leap that is ALSO a pin wearing the pin's
          // diamond. A memory of where you have been — and which of
          // those places you nailed down.
          takeStage();
          const std::string j =
              dxn3::ideJumpsWhisper(ide.jumps, ide.jumpIx, ide.marks);
          ide.console.push_back(
              j.empty()
                  ? "engine: no jumps yet — :goto, F2 and the welcome "
                    "back plant them"
                  : "engine: the jumps, newest first — " + j);
        } else if (cmd.verb == "changes") {
          // the census: a bare :changes LISTS the touched lines; a
          // number LEAPS to the Nth — the census is not just a mirror,
          // it is a set of addresses. The leap is a real one: planted
          // in the ledger, the selection dropped, the landing
          // mid-screen — the same laws the pins' :bm obeys.
          takeStage();
          if (ide.touched.empty()) {
            ide.console.push_back(
                "engine: a clean page — nothing touched since it opened");
          } else if (cmd.arg.empty()) {
            const std::string t =
                dxn3::ideTouchWhisper(ide, ide.marks);
            ide.console.push_back(
                "engine: " + std::to_string(ide.touched.size()) +
                " line" + (ide.touched.size() == 1 ? "" : "s") +
                " touched since the page opened — " + t);
          } else if (static_cast<int>(cmd.num) >= 1 &&
                     static_cast<int>(cmd.num) <=
                         static_cast<int>(ide.touched.size())) {
            const int to = ide.touched[static_cast<size_t>(
                static_cast<int>(cmd.num) - 1)];
            ide.findOpen = false;              // the searchlight rests
            ide.curR = to;
            ide.curC = 0;
            ide.top = std::max(0, ide.curR - 4);   // the leap lands mid-screen
            dxn3::ideSelClear(ide);                // the leap drops the selection
            dxn3::ideJumpPush(ide, to);            // a real leap, planted
            ide.console.push_back(
                "engine: the hand leaps to the census's line " +
                std::to_string(static_cast<int>(cmd.num)) + " — line " +
                std::to_string(to + 1));
          } else {
            ide.console.push_back(
                "engine: no such touch — :changes lists " +
                std::to_string(ide.touched.size()));
          }
        } else if (cmd.verb == "record") {
          // the recorder: :record starts (the register empties), every
          // well-formed verb joins, :record ends it. A session fact —
          // the register survives opens and reloads.
          takeStage();
          ide.recording = !ide.recording;
          if (ide.recording) {
            ide.macro.clear();
            ide.console.push_back(
                "engine: recording — every verb you run joins the macro "
                "(:record ends it)");
          } else if (ide.macro.empty()) {
            ide.console.push_back(
                "engine: the recorder rests — an empty macro");
          } else {
            // the take, listed: the register's lines in order, capped —
            // the receipt answers "what did I just record" at a glance
            std::string list;
            size_t shown = 0;
            for (const auto& l : ide.macro) {
              if (shown == 4) break;
              list += (shown == 0 ? "" : " · ") + l;
              ++shown;
            }
            if (ide.macro.size() > 4)
              list += " … +" + std::to_string(ide.macro.size() - 4) +
                      " deeper";
            ide.console.push_back(
                "engine: the recorder rests — " +
                std::to_string(ide.macro.size()) + " verb" +
                (ide.macro.size() == 1 ? "" : "s") + " in the macro (" +
                list + ") — :macro plays it");
          }
        } else if (cmd.verb == "macro") {
          // the replay: the register's lines walk through the SAME
          // dispatch, one per frame, in the order they were recorded.
          // :macro N runs the whole take N times — choreography, not
          // just a sequence.
          takeStage();
          const int times = cmd.arg.empty() ? 1 : static_cast<int>(cmd.num);
          if (ide.recording) {
            cmdErr = "the recorder is live — :record ends it first";
            cmdErrT = 3.5f;
          } else if (ide.macro.empty()) {
            ide.console.push_back(
                "engine: nothing recorded — :record starts a macro");
          } else if (macroPlaying) {
            cmdErr = "the macro is already playing";
            cmdErrT = 3.5f;
          } else {
            macroPlaying = true;
            macroIx = 0;
            macroRuns = times;
            playedRuns = times;
            ide.console.push_back(
                "engine: playing " + std::to_string(ide.macro.size()) +
                " verb" + (ide.macro.size() == 1 ? "" : "s") +
                (times == 1 ? "" : " × " + std::to_string(times)) +
                " — the register runs in the order it was recorded");
          }
        } else if (cmd.verb == "fresh") {
          // the disk's truth wins the page back — :e!'s twin. A reload
          // is a REOPEN: it walks the one openScript path, so the
          // welcome back keeps the hand, the history starts fresh, and
          // the receipts stay honest. A page that was never written
          // has no truth to win — refused, with the way out.
          takeStage();
          if (ide.path.empty()) {
            cmdErr = "nothing to reload — the page has no file";
          } else {
            std::error_code ec;
            if (!std::filesystem::exists(ide.path, ec))
              cmdErr = "nothing on disk to reload — :w writes the "
                       "page first";
            else
              cmdErr = openScript(ide.path, /*keepJumps=*/true);
          }
        } else if (cmd.verb == "center") {
          // the view rebalances: the hand rides the viewport's middle,
          // clamped to the doc's edges. A look, never an edit.
          takeStage();
          {
            const dxn3::IdeWrap wrapZ =
                dxn3::ideWrapBuild(ide, paneTextW());
            dxn3::ideCenter(ide, &wrapZ);    // the hand rides the middle —
                                             // in rows under the fold
          }
          ide.console.push_back(
              "engine: the view centers on line " +
              std::to_string(ide.curR + 1) +
              " — the hand rides the middle");
        } else if (cmd.verb == "relnum") {
          // the vim way: the gutter counts from the hand — the hand's
          // own line keeps its true name, and the toggles always come back
          takeStage();
          ide.relnum = !ide.relnum;
          ide.console.push_back(
              ide.relnum
                  ? "engine: the gutter counts from your hand — the "
                    "hand's line keeps its name"
                  : "engine: the absolutes return — every line wears its "
                    "own number");
        } else if (cmd.verb == "wrap") {
          // the long line's courtesy: the pane folds what the slide used
          // to chop — and a second :wrap wakes the slide again
          takeStage();
          ide.wrap = !ide.wrap;
          ide.console.push_back(
              ide.wrap
                  ? "engine: long lines fold into the pane — the slide "
                    "sleeps while the fold speaks"
                  : "engine: the slide returns — long lines run past the "
                    "pane again");
        } else if (cmd.verb == "stats") {
          takeStage();
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
              " chars · longest " +
              std::to_string(dxn3::ideLongestLine(ide)) +
              (ide.touched.empty()
                   ? ""
                   : " · " + std::to_string(ide.touched.size()) +
                         " changed this session"));
          ide.console.push_back(
              "engine: at Ln " + std::to_string(ide.curR + 1) + " · Col " +
              std::to_string(ide.curC + 1) + " · " +
              std::string(dxn3::ideSnippetFamily(ide.path)) + " dialect · " +
              (ide.hostUp ? "host live" : "host idle"));
          if (const auto sel = dxn3::ideSelRange(ide)) {
            // the selection's own census — spoken LAST so the console's
            // two-row window shows the most specific truth newest
            const dxn3::IdeSelStats ss = dxn3::ideSelStats(ide, *sel);
            ide.console.push_back(
                "engine: the selection — " + std::to_string(ss.lines) +
                " line" + (ss.lines == 1 ? "" : "s") + " · " +
                std::to_string(ss.words) + " word" +
                (ss.words == 1 ? "" : "s") + " · " +
                std::to_string(ss.chars) + " char" +
                (ss.chars == 1 ? "" : "s"));
          }
        } else if (cmd.verb == "w") {
          if (ideEver) {
            takeStage();             // the save's receipt speaks in the
                                     // studio's console
            // the studio is the stage: :w is the SCRIPT's pen — bare
            // it saves the doc in place (a .bak keeps the past), a
            // name saves AS that name and the ledger remembers it.
            // The scene's :w belongs to play, where the viewport is
            // the document.
            std::string err;
            bool bak = false;
            if (!cmd.arg.empty()) {
              const std::string old = ide.path;
              ide.path = cmd.arg;
              if (ideSave(ide, &err, &bak)) {
                dxn3::ideRecentPush(ide.recent, ide.path);
                ide.console.push_back("engine: saved as " + ide.path +
                                      (bak ? "  (.bak kept)" : ""));
                ideRun();
                ide.idle = 0;
              } else {
                ide.path = old;    // the name was refused: the doc
                cmdErr = err;      // keeps its own
                cmdErrT = 3.5f;
              }
            } else if (ideSave(ide, &err, &bak)) {
              ide.console.push_back("engine: saved " + ide.path +
                                    (bak ? "  (.bak kept)" : ""));
            } else { cmdErr = err; cmdErrT = 3.5f; }
          } else {
            const std::string path = cmd.arg.empty() ? scenePath : cmd.arg;
            const std::string err = dxn3::Game::saveScene(path, game.scene);
            if (err.empty()) game.say("saved " + path + "  (.bak kept)", 2.2);
            else { cmdErr = err; cmdErrT = 3.5f; }
          }
        } else if (cmd.verb == "wq") {
          if (ideEver) {
            std::string err;
            if (ideSave(ide, &err)) return true;   // the save is the sleep
            cmdErr = err; cmdErrT = 3.5f;    // a failed pen never quits
          } else {
            const std::string err = dxn3::Game::saveScene(scenePath, game.scene);
            if (err.empty()) return true;
            cmdErr = err; cmdErrT = 3.5f;
          }
        } else if (cmd.verb == "q") {
          return true;
        } else if (cmd.verb == "screenshot") {
          doShot(cmd.arg);
        } else if (cmd.verb == "magnet") {
          game.scene.magnet = cmd.num;
          game.say("magnet " + std::to_string(static_cast<int>(cmd.num)) + "px", 1.2);
        } else if (cmd.verb == "gravity") {
          game.scene.gravity = cmd.num;
          game.say("gravity " + std::to_string(static_cast<int>(cmd.num)), 1.2);
        } else if (cmd.verb == "help") {
          takeStage();                         // every verb takes the stage —
                                               // a law, not a suggestion
          if (cmd.arg.empty()) {
            game.say(":scene :open :recent :template :snip :goto :jumps :changes :fresh :mark :marks :bm :ruler :minimap :zen :wrap :center :relnum :s :sa :o :e :trim :cases :sort :rsort :rev :uniq :shuffle :indent :dedent :lift :drop :dup :join :upper :lower :title :hist :undo :redo :words :todo :stats "
                     ":record :macro :zoom :fit :reset :new :w :wq :q :screenshot :magnet :gravity — or :help <verb>",
                     4.f);
          } else {
            // one verb's law: the SAME whisper the bar speaks while you
            // type, promoted to the console where it can be read slowly
            const std::string hint = dxn3::usageHintFor(cmd.arg);
            if (hint.empty())
              cmdErr = "no such command: " + cmd.arg +
                       " — :help lists them";
            else
              ide.console.push_back("engine:" + hint);
          }
        }

    return false;
  };

    // live refresh: edits settle for a beat, then your code runs again
    if (ide.open) {
      ide.idle += dt;
      if (ide.dirty && ide.idle > 0.6) ideRun();
    }

    // the macro's playback: one verb per frame, the register walked in
    // order, each line through the SAME dispatch the bar speaks. The
    // frame paces the deal.
    if (macroPlaying && !cmdOpen) {
      if (macroIx >= ide.macro.size()) {
        if (macroRuns > 1) {                   // the take again: :macro N
          macroRuns -= 1;
          macroIx = 0;
        } else {
          macroPlaying = false;
          ide.console.push_back(
              "engine: the macro ran — " +
              std::to_string(ide.macro.size()) + " verb" +
              (ide.macro.size() == 1 ? "" : "s") +
              (playedRuns > 1 ? " × " + std::to_string(playedRuns) : "") +
              ", done");
        }
      } else {
        const std::string line = ide.macro[macroIx++];
        if (runCommand(line)) break;
      }
    }

    if (cmdOpen) {                       // the command bar owns the keyboard
      if (keys.esc) cmdOpen = false;
      else if (keys.back) { if (!cmdBuf.empty()) cmdBuf.pop_back(); }
      else if (keys.enter) {
        cmdBuf += keys.typed;      // a paste that lands with enter counts
        cmdOpen = false;
        const std::string line = cmdBuf;   // the clear must not eat the verb
        cmdBuf.clear();
        if (runCommand(line)) break;
      } else {
        cmdBuf += keys.typed;
        if (cmdBuf.size() > 120) cmdBuf.resize(120);
      }
    } else if (!fileView) {
      if (keys.quit || (keys.esc && !ide.open)) break;   // esc edits, q quits
      if (keys.cmd) { cmdOpen = true; cmdBuf.clear(); }
      if (keys.inspect) inspect = !inspect;
      if (keys.viewFile) {
        if (ide.hostUp || isScriptFile(ide.path)) takeStage();   // e → the IDE
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
      if (keys.slash && !searching) {
        searching = true;
        query = fileQ;         // the question survives: / reopens it, back edits
      }
      if (searching) {
        if (keys.back) { if (!query.empty()) query.pop_back(); }
        else query += keys.typed;
      }
      if (keys.scroll != 0) {
        const int maxTop = std::max(0, static_cast<int>(fileLines.size()) - (rows - 3));
        fileTop = std::clamp(fileTop + keys.scroll, 0, maxTop);
      }
      // the hunt, one law with the IDE's F3: strictly after the hand
      // going down, strictly before going up, the full cycle IS the
      // wrap, an empty question silent, a landing paints its line.
      auto fileLand = [&](int pick) {
        fileSel = pick;
        const int maxTop = std::max(0, fileN - (rows - 3));
        fileTop = std::clamp(pick - 2, 0, maxTop);
      };
      if (keys.enter && searching && !query.empty()) {
        searching = false;
        const bool fresh = query != fileQ || fileSel < 0;
        fileQ = query;
        if (fileN > 0) {
          // the strict law: the SAME question walks from its last
          // landing (it never re-lands the hit you stand on); a fresh
          // question starts from the viewport's head
          const int hand = fresh ? fileTop : fileSel;
          for (int i = 1; i <= fileN; ++i) {
            const int li = (hand + i) % fileN;
            if (fileMatch(li)) { fileLand(li); break; }
          }
        }
      }
      if ((keys.findJump || keys.findBack) && !fileQ.empty() && fileN > 0) {
        const int hand = fileSel >= 0 ? fileSel : fileTop;
        for (int i = 1; i <= fileN; ++i) {
          const int li = keys.findJump ? (hand + i) % fileN
                                       : ((hand - i) % fileN + fileN) % fileN;
          if (fileMatch(li)) { fileLand(li); break; }
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
        const int bodyRowsC = rows0 - 3 + (ide.zen ? 2 : 0);   // zen: the
                                                               // rail's rows
                                                               // join the body
        const bool splitC = cols0 >= 96;
        const int editWC = splitC ? 46 : cols0;
        const bool mapOnC = ide.minimap && splitC && cols0 >= 110;
        const int GC = dxn3::ideGutterWidth(
            static_cast<int>(ide.lines.size()));   // the draw's SAME rule
        const int textWC = editWC - 1 - GC - (mapOnC ? 7 : 0);
        const int row = r - 1;                     // screen row -> body row
                                                   // (bodyTop is 1)
        const int col = c;
        int li = -1, ci = 0;
        if (row >= 0 && row < bodyRowsC) {
          // the fold speaks rows: the pressed screen row names its line
          // through the layout — the identity when the fold sleeps, so
          // the old law is the same law
          const dxn3::IdeWrap wrapC =
              dxn3::ideWrapBuild(ide, paneTextW());
          const int vC = ide.top + row;
          const bool inDoc = vC >= 0 && vC < wrapC.rows;
          if (mapOnC && col >= editWC - 7 && col < editWC - 1) {
            const dxn3::IdeMini mini =
                dxn3::ideMiniMap(ide, 6, bodyRowsC);
            if (row < static_cast<int>(mini.rows.size())) {
              li = mini.top + row;                 // the map jumps whole lines
              ci = 0;
            }
          } else if (col >= GC && (!mapOnC || col < GC + textWC)) {
            if (inDoc) {
              li = wrapC.rowLine[static_cast<size_t>(vC)];
              ci = col - GC + ide.hcol +
                   wrapC.rowOff[static_cast<size_t>(vC)];
            }
          } else if (col < GC) {
            if (inDoc) {
              li = wrapC.rowLine[static_cast<size_t>(vC)];  // the gutter: the
              ci = 0;                              // row's line, its start
            }
          }
        }
        if (li < 0) {
          r = -1;                                  // not ours — swallow
        } else {
          r = li;
          c = ci;
        }
      };
      if (keys.clickR >= 0) {
        // the pin's diamond is a BUTTON: a plain click on the gutter's
        // edge of a pinned line pulls that pin — a look, never an edit
        // (the hand stays put, the ledger speaks). A click anywhere
        // else in the gutter keeps its old law: the line start.
        const int GC =
            dxn3::ideGutterWidth(static_cast<int>(ide.lines.size()));
        const int bodyRowsB = rows0 - 3 + (ide.zen ? 2 : 0);
        const int brow = keys.clickR - 1;
        if (!keys.clickShift && brow >= 0 && brow < bodyRowsB &&
            keys.clickC == GC - 1) {
          const dxn3::IdeWrap wrapB =
              dxn3::ideWrapBuild(ide, paneTextW());
          const int vB = ide.top + brow;
          const int li = vB >= 0 && vB < wrapB.rows
                             ? wrapB.rowLine[static_cast<size_t>(vB)]
                             : -1;
          if (li >= 0 && li < static_cast<int>(ide.lines.size()) &&
              dxn3::ideMarkHas(ide, li)) {
            const bool on = dxn3::ideMarkToggle(ide, li);
            ide.console.push_back(
                on ? "engine: pin planted on line " +
                         std::to_string(li + 1) +
                         " — F2 leaps, :marks lists"
                   : "engine: pin pulled from line " +
                         std::to_string(li + 1));
            keys.clickR = -1;              // the click is spent on the pin
            keys.clickC = -1;              // the hand never moves
          }
        }
        if (keys.clickR >= 0) translateCell(keys.clickR, keys.clickC);
      }
      if (keys.dragR >= 0) {
        // the autoscroll's edge sensor: a drag parked on the viewport's
        // top or bottom row pulls the view toward the unseen lines —
        // decided on the raw body row, before any zone mapping (a
        // map-rail or gutter drag speaks the same edge law). A hand
        // outside the body (header, rails) is no edge at all.
        const int rawRow = keys.dragR - 1;                 // body row
        const int bodyRowsC = rows0 - 3 + (ide.zen ? 2 : 0);
        ide.dragEdge =
            rawRow < 0 || rawRow >= bodyRowsC
                ? 0
                : rawRow == 0 ? -1
                  : rawRow == bodyRowsC - 1 ? 1 : 0;
        translateCell(keys.dragR, keys.dragC);
      }
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
      if (keys.scroll != 0) {                    // the wheel and the
        const dxn3::IdeWrap wrapS =              // ctrl+↑/↓ nudge — the
            dxn3::ideWrapBuild(ide, paneTextW());// ride speaks the fold's
        dxn3::ideScroll(ide, keys.scroll, &wrapS);   // rows when it speaks
      }
      {
        const dxn3::IdeWrap wrapD =              // the drag parked at an
            dxn3::ideWrapBuild(ide, paneTextW());// edge pulls — the same
        dxn3::ideDragAutoScroll(ide, ide.dragEdge, dt, &wrapD);  // rows law
      }
      if (keys.ctrlS) {
        std::string err;
        bool bak = false;
        if (ideSave(ide, &err, &bak))
          ide.console.push_back("engine: saved " + ide.path +
                                (bak ? "  (.bak kept)" : ""));
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
      if (fileView) {
        // the hunt's rail: the question, the landing's ordinal among
        // the hits, the honest "no hits" — words computed where the
        // state lives, so the law and the sentence cannot diverge
        std::string st = " / to search";
        if (searching) {
          if (!query.empty()) st = " /" + query + "  (enter to run)";
        } else if (!fileQ.empty()) {
          int m = 0, ord = 0;
          for (int li = 0; li < fileN; ++li) {
            if (!fileMatch(li)) continue;
            ++m;
            if (li == fileSel) ord = m;
          }
          st = m == 0 ? " /" + fileQ + "  no hits — / reasks"
                      : " /" + fileQ + "  hit " + std::to_string(ord) + "/" +
                            std::to_string(m) + " — F3 walks";
        }
        drawFile(scr, fileLines, fileTop, searching ? query : fileQ,
                 scenePath, fileSel, st);
      }
      else if (ide.open) drawIDE(scr, ide, game, host.running());
      else if (inspect) drawInspect(scr, game);
      else drawWorld(scr, game);
      if (ide.open) {
        // the IDE paints its own rails
      } else if (cmdOpen) {
        scr.text(0, rows - 1, ":" + cmdBuf + "_", dxn3::rgb(250, 204, 21));
        // command-bar whispers: scenes, scripts, screenshots, :w scene
        // targets, snippet names and the ledger complete themselves as
        // you type — the campaign, the cwd, the exports dir and the
        // recent files speak up. The usage hint yields: a whisper that
        // paints must not have the hint bleeding through its tail.
        // (cmdBuf never carries the leading ':' — the bar paints that.)
        std::string whisper;               // the winner, painted once below
        const struct {
          const char* pre;
          size_t len;
          bool bare;             // whispers even with nothing typed after it
        } qs[] = {{"scene ", 6, false},      {"open ", 5, true},
                  {"screenshot ", 11, true}, {"w ", 2, false},
                  {"snip ", 5, true},        {"recent ", 7, true},
                  {"bm ", 3, true},          {"template ", 9, true}};
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
            if (part.empty()) {
              // bare :open: what enter WILL open — the ledger's head,
              // or the honest nothing when the ledger is empty
              if (ide.recent.empty())
                w = "(the ledger is empty — name a path)";
              else
                w = ide.recent.front() + " — the ledger's head";
            } else {
              // the LEDGER speaks first — files you had open, by path
              // or basename — then the cwd's scripts and the gallery's
              // examples fill in behind, deduped, in that order
              const int hcolW = 2 + static_cast<int>(cmdBuf.size());
              w = dxn3::ideOpenWhisper(
                  ide.recent, part, scriptCandidates(),
                  static_cast<size_t>(std::max(0, cols - 1 - hcolW)));
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
          } else if (std::strcmp(q.pre, "recent ") == 0) {
            // the ledger whispers: what enter WILL open, before it
            // opens it — full paths, the head of the list first, only
            // as many as the bar honestly holds
            const int hcolW = 2 + static_cast<int>(cmdBuf.size());
            w = dxn3::ideRecentWhisper(
                ide.recent, part,
                static_cast<size_t>(std::max(0, cols - 1 - hcolW)));
          } else if (std::strcmp(q.pre, "bm ") == 0) {
            // the pins whisper: the :marks order speaks its lines, the
            // typed number narrows the choir, the bar's width ends it
            const int hcolW = 2 + static_cast<int>(cmdBuf.size());
            w = dxn3::ideMarkWhisper(
                ide, part,
                static_cast<size_t>(std::max(0, cols - 1 - hcolW)));
          } else if (std::strcmp(q.pre, "template ") == 0) {
            // the gallery whispers: every starter's name, the typed
            // prefix narrowing — the SAME law the verb's resolution
            // speaks, one row earlier in the story
            for (int i = 0; i < nTpl; ++i) {
              if (std::string_view(tpls[i].name).rfind(part, 0) != 0)
                continue;
              if (!w.empty()) w += " · ";
              w += tpls[i].name;
            }
          } else {                           // "snip " — the shelf whispers,
                                             // every name carrying its
                                             // one-line description
            const int hcolW = 2 + static_cast<int>(cmdBuf.size());
            w = dxn3::ideSnippetShelfWhisper(
                ide.path, part,
                static_cast<size_t>(std::max(0, cols - 1 - hcolW)));
          }
          const int hcol = 2 + static_cast<int>(cmdBuf.size());
          if (!w.empty() && hcol + static_cast<int>(w.size()) < cols - 1)
            whisper = w;         // remembered — painted once, hint yields
          break;                 // one whisper per frame — first match wins
        }
        if (!whisper.empty()) {
          const int hcol = 2 + static_cast<int>(cmdBuf.size());
          scr.text(hcol, rows - 1, whisper, dxn3::rgb(168, 85, 247));
        } else {                 // silent bar: the usage speaks instead
          const std::string hint = dxn3::usageHintFor(cmdBuf);
          if (!hint.empty()) {
            const int hcol = 2 + static_cast<int>(cmdBuf.size());
            if (hcol + static_cast<int>(hint.size()) < cols - 1)
              scr.text(hcol, rows - 1, hint, dxn3::rgb(124, 58, 237));
          }
        }
      } else if (cmdErrT > 0) {
        scr.text(0, rows - 1, " dxn3: " + cmdErr, dxn3::rgb(248, 113, 113));
      } else if (fileView) {
        scr.help(" j/k scroll · / find · enter/F3 walk · shift+F3 back · esc · q");
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
