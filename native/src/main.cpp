// dxn3 native — the studio shell (C++23).
// A truecolor terminal studio: PLAY mode runs the Spark engine core;
// INSPECT mode (Tab) pauses and shows the entity table. Raw-mode input,
// fixed-timestep loop, goal transitions chain scenes like the JS runtime.
#include <algorithm>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstring>
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

// drain stdin; return the keys seen this frame
struct Keys {
  bool left = false, right = false, jump = false;
  bool reset = false, fit = false, zoomIn = false, zoomOut = false;
  bool inspect = false, quit = false;
  bool esc = false;                            // bare ESC (mode-dependent)
  bool viewFile = false;                       // e — open the scene source
  int scroll = 0;                              // file view: ±1 lines (arrows ±10)
  bool slash = false;                          // / — start a search
  bool enter = false, back = false;
  std::string typed;                           // printable chars this frame
};

Keys pollKeys(bool inFile) {
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
        if (i + 2 < n && buf[i + 1] == '[') {
          switch (buf[i + 2]) {
            case 'A': if (inFile) k.scroll -= 1; else k.jump = true; break;
            case 'B': if (inFile) k.scroll += 1; break;
            case 'C': if (inFile) k.scroll += 10; else k.right = true; break;
            case 'D': if (inFile) k.scroll -= 10; else k.left = true; break;
          }
          i += 2;
        } else {
          k.esc = true;                     // bare ESC
          if (!inFile) k.quit = true;       // …which quits in play/inspect
        }
        continue;
      }
      if (inFile) {                          // FILE VIEW: every letter is text
        if (c == '\r' || c == '\n') k.enter = true;
        else if (c == '\t') { /* inert */ }
        else if (c == 0x7f || c == '\b') k.back = true;
        else if (c == 'j' || c == 'J') k.scroll += 1;
        else if (c == 'k' || c == 'K') k.scroll -= 1;
        else if (c == '/') k.slash = true;
        else if (c == 'q' || c == 'Q') k.quit = true;
        else if (static_cast<unsigned char>(c) >= 0x20) k.typed += c;
      } else {                               // PLAY / INSPECT keys
        if (c == 'a' || c == 'A') k.left = true;
        else if (c == 'd' || c == 'D') k.right = true;
        else if (c == 'w' || c == 'W' || c == ' ') k.jump = true;
        else if (c == 'r' || c == 'R') k.reset = true;
        else if (c == 'f' || c == 'F') k.fit = true;
        else if (c == '+' || c == '=') k.zoomIn = true;
        else if (c == '-' || c == '_') k.zoomOut = true;
        else if (c == '\t') k.inspect = true;
        else if (c == 'e' || c == 'E') k.viewFile = true;
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
              int top, int cur, const std::string& query) {
  scr.clear(dxn3::rgb(9, 10, 18));
  const RGB accent = dxn3::rgb(167, 139, 250);
  const RGB dim = dxn3::rgb(110, 118, 140);
  const RGB txt = dxn3::rgb(220, 222, 232);
  const RGB hit = dxn3::rgb(250, 204, 21);
  char head[96];
  std::snprintf(head, sizeof head, " FILE — %d/%d lines — /%s (%s to run)",
                cur + 1, static_cast<int>(lines.size()), query.c_str(),
                query.empty() ? "type / first" : "enter");
  scr.text(0, 0, head, accent);
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

  for (const auto& e : sc.entities) {
    if (!e.alive) continue;
    const float x0 = sx(e.x), y0 = sy(e.y);
    const float x1 = x0 + e.w * z - 1, y1 = y0 + e.h * z - 1;
    const RGB c1 = dxn3::parseHex(e.color, dxn3::rgb(139, 92, 246));
    const bool off = x1 < 0 || x0 > cols || y1 < 0 || y0 > hr;

    if (e.tag == "sign") {                                // text plaque
      if (!off && !e.text.empty()) {
        const int col = static_cast<int>(x0);
        const int row = static_cast<int>(y0) / 2;
        scr.text(col, row, e.text, c1);
      }
      continue;
    }
    if (e.tag == "coin") {                                // gem: inset + shine
      if (off) continue;
      const float inx = e.w * 0.22f, iny = e.h * 0.22f;
      scr.rectGradient(x0 + inx, y0 + iny, x1 - inx, y1 - iny,
                       dxn3::lerpColor(c1, 0xFFFFFF, 0.35f), c1);
      continue;
    }
    if (e.tag == "spike") {                               // triangle profile
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
    if (e.tag == "player") {                              // visor line
      const RGB dark = dxn3::lerpColor(c1, 0, 0.55f);
      scr.rect(x0 + 1, y0 + (y1 - y0) * 0.25f, x1 - 1, y0 + (y1 - y0) * 0.4f, dark);
    }
  }
  if (g.flash > 0.02f)
    scr.rect(0, 0, cols - 1, hr - 1,
             dxn3::rgb(255, 255, static_cast<std::uint8_t>(255 * g.flash)));
  // dead-simple overlay: dim the whole playfield by drawing bg-colored
  // frame when flash just ended is unnecessary — keep it honest instead.

  char tbuf[96];
  std::snprintf(tbuf, sizeof tbuf, "%s", fmtTime(g.time).c_str());
  scr.hud(g.score, tbuf, g.msgT > 0 ? g.msg : "");
}

void drawInspect(dxn3::Screen& scr, const dxn3::Game& g) {
  const RGB bg = dxn3::rgb(9, 10, 18);
  scr.clear(bg);
  const RGB accent = dxn3::rgb(167, 139, 250);
  const RGB dim = dxn3::rgb(110, 118, 140);
  const RGB txt = dxn3::rgb(220, 222, 232);

  scr.text(1, 0, " INSPECT — " + g.scene.name +
           "  (Tab to resume, game is paused)", accent);
  scr.text(1, 2, "ENTITY         TAG         X      Y      W    H    COLOR", dim);
  int row = 3;
  char line[96];
  for (const auto& e : g.scene.entities) {
    if (row >= scr.rows - 1) { scr.text(1, row, "…", dim); break; }
    std::snprintf(line, sizeof line, "%-14s %-11s %6.0f %6.0f %4.0f %4.0f  %s%s",
                  e.name.c_str(), e.tag.c_str(), e.x, e.y, e.w, e.h,
                  e.color.c_str(), e.alive ? "" : "  (gone)");
    scr.text(1, row++, line, e.alive ? txt : dim);
  }
  char meta[96];
  std::snprintf(meta, sizeof meta,
                "gravity %.0f  magnet %.0fpx  zoom %.2f  next %s",
                g.scene.gravity, g.scene.magnet, g.scene.camera.zoom,
                g.scene.next.empty() ? "—" : g.scene.next.c_str());
  scr.text(1, scr.rows - 2, meta, accent);
}

} // namespace

int main(int argc, char** argv) {
  std::signal(SIGINT, onSignal);
  std::signal(SIGTERM, onSignal);
  std::atexit(restoreTerminal);

  std::string scenePath = "scenes/playground.dxn1.json";
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--scene" && i + 1 < argc) scenePath = argv[++i];
    else if (!a.empty() && a[0] != '-') scenePath = a;
    else if (a == "--help" || a == "-h") {
      std::println("usage: dxn3-native [--scene <file.dxn1.json>]\n"
                   "keys: a/d move · w/space jump · r reset · +/- zoom · f fit · tab inspect · q quit");
      return 0;
    }
  }

  auto loaded = dxn3::Game::loadScene(scenePath);
  if (!loaded) {
    std::println(stderr, "dxn3: cannot load '{}': {}", scenePath, loaded.error().detail);
    return 1;
  }

  dxn3::Game game(std::move(*loaded));
  bool inspect = false;

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

  std::println("dxn3 native (C++23) — scene '{}' — {} entities — magnet {}px",
               game.scene.name, game.scene.entities.size(),
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

  while (!g_stop) {
    const auto now = clock::now();
    const double dt = std::chrono::duration<double>(now - last).count();
    last = now;
    acc += dt;

    const Keys keys = pollKeys(fileView);
    if (!fileView) {
      if (keys.quit || keys.esc) break;
      if (keys.inspect) inspect = !inspect;
      if (keys.viewFile) {
        fileView = true; searching = false; query.clear(); fileTop = 0;
      }
      if (keys.reset) game.reset();
      if (keys.zoomIn) game.scene.camera.zoom = std::clamp(game.scene.camera.zoom * 1.15f, 0.3f, 4.f);
      if (keys.zoomOut) game.scene.camera.zoom = std::clamp(game.scene.camera.zoom / 1.15f, 0.3f, 4.f);
      if (keys.fit) {
        const float ww = std::max(320.f, game.worldRight() + 160);
        const float wh = std::max(240.f, game.worldBottom() + 160);
        const float fz = std::min(cols / ww, (rows - 2) * 2.f / wh);
        game.scene.camera.zoom = std::clamp(fz, 0.3f, 4.f);
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
    if (!inspect && !fileView) {
      while (acc >= STEP) {
        game.update(static_cast<float>(STEP), in);
        acc -= STEP;
        in = {};                      // hold inputs for one step only
      }
      if (!game.pendingNext.empty()) {
        auto next = dxn3::Game::loadScene(game.pendingNext);
        game.pendingNext.clear();
        if (next) {
          const int score = game.score;
          const float time = game.time;
          const std::string name = next->name;
          game = dxn3::Game(std::move(*next));
          game.score = score; game.time = time;
          game.say("welcome to " + name, 1.6);
        } else {
          game.say("next scene missing: " + next.error().detail, 2.5);
          game.transLocked = true;
        }
      }
    } else {
      acc = 0;
    }

    if (g_raw) {
      termSize(cols, rows);
      scr.resize(cols, rows);
      if (fileView) drawFile(scr, fileLines, fileTop, fileTop, query);
      else if (inspect) drawInspect(scr, game);
      else drawWorld(scr, game);
      if (fileView)
        scr.help(" j/k scroll · / find · enter run · esc back · q quit");
      else if (inspect)
        scr.help(" a/d move · w jump · r reset · +/- zoom · f fit · tab inspect · q quit");
      else
        scr.help(" a/d move · w/space jump · r reset · +/- zoom · f fit · tab inspect · e file · q quit");
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
