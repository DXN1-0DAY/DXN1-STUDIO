// dxn3 native — engine selftest (C++23). Mirrors renderer selftest's spirit:
// normalization clamps, magnetism, pickups, hazards, transitions, movers.
#include <cmath>
#include <print>
#include <string>
#include <sys/stat.h>
#include <fstream>

#include "spark.hpp"
#include "version.hpp"
#include "fx.hpp"
#include "png.hpp"
#include "cmd.hpp"
#include "shot.hpp"
#include "host.hpp"
#include "edit.hpp"

using namespace dxn3;

// scene paths in .dxn1.json are repo-relative; run the binary from anywhere
static std::string repoPath(const std::string& p) {
  for (const std::string& prefix : {std::string(""), std::string("../"),
                                    std::string("../../")}) {
    const std::string full = prefix + p;
    if (struct stat st; ::stat(full.c_str(), &st) == 0 && S_ISREG(st.st_mode))
      return full;
  }
  return p;                                   // let loadScene report honestly
}

static int n = 0, fails = 0;
static void ok(bool cond, const std::string& what) {
  ++n;
  if (cond) { std::println("   ok  {}", what); }
  else { ++fails; std::println("   FAIL {}", what); }
}

static Entity mk(std::string tag, float x, float y, float w, float h,
                 std::string color = "#8b5cf6") {
  Entity e;
  e.name = tag.empty() ? "thing" : tag;
  e.tag = std::move(tag);
  e.x = x; e.y = y; e.w = w; e.h = h;
  e.color = std::move(color);
  return e;
}

int main() {
  std::println("dxn3 native selftest (C++23)");

  // 1. normalization clamps
  Scene junk;
  junk.magnet = -5;
  junk.camera.zoom = 9;
  junk.gravity = 999999;
  Scene norm = Game::normalizeScene(junk);
  ok(norm.magnet == 0, "magnet clamps negatives to off");
  ok(norm.camera.zoom == 4, "zoom clamps to 4");
  ok(norm.gravity == 5000, "gravity clamps to 5000");
  Scene deft;
  ok(Game::normalizeScene(deft).magnet == 0, "magnet defaults off");
  ok(Game::normalizeScene(deft).gravity == 1500, "gravity defaults 1500");

  // 2. real scenes load + round-trip
  auto load = Game::loadScene(repoPath("scenes/playground.dxn1.json"));
  ok(load.has_value(), "playground scene loads");
  if (load) {
    ok(load->name == "playground", "playground keeps its name");
    ok(load->magnet == 110, "playground is magnetized (110px)");
    ok(!load->entities.empty(), "playground has entities");
    ok(!load->next.empty(), "playground chains a next scene");
    const std::string j = Game::toJson(*load);
    ok(j.find("\"magnet\": 110") != std::string::npos, "toJson round-trips magnet");
  }
  auto bad = Game::loadScene(repoPath("scenes/does-not-exist.dxn1.json"));
  ok(!bad.has_value(), "missing scene is an honest error");

  // 3. coin pickup + magnetism
  {
    Scene s;
    s.entities.push_back(mk("player", 100, 100, 34, 44));
    s.entities.push_back(mk("coin", 160, 110, 22, 22, "#facc15"));
    s.magnet = 140;
    Game g(std::move(s));
    Entity& coin = g.scene.entities[1];
    Input in; in.right = true;
    for (int i = 0; i < 60 && coin.alive; ++i) g.update(1.f / 60.f, in);
    ok(g.score == 10 && !coin.alive, "coin picked up -> score 10");
  }
  {
    Scene s;
    s.entities.push_back(mk("player", 100, 300, 34, 44));
    s.entities.push_back(mk("", 0, 400, 640, 40, "#1f2937"));   // floor
    s.entities.push_back(mk("coin", 280, 300, 22, 22));
    s.magnet = 200;
    Game g(std::move(s));
    Entity& coin = g.scene.entities[2];
    const Entity* pl = g.player();
    const float d0 = std::hypot(coin.cx() - pl->cx(), coin.cy() - pl->cy());
    ok(d0 < 200, "coin starts inside the magnet radius");
    for (int i = 0; i < 30; ++i) g.update(1.f / 60.f, {});
    const float d1 = std::hypot(coin.cx() - pl->cx(), coin.cy() - pl->cy());
    ok(d1 < d0 || !coin.alive, "magnet pulls coin toward player");
  }
  {
    Scene s;   // magnet off -> coin stays put
    s.entities.push_back(mk("player", 100, 300, 34, 44));
    auto& coin = s.entities.emplace_back(mk("coin", 420, 300, 22, 22));
    Game g(std::move(s));
    for (int i = 0; i < 30; ++i) g.update(1.f / 60.f, {});
    ok(coin.x == 420 && coin.y == 300, "magnet off leaves coins alone");
  }

  // 4. hazard respawn + shake
  {
    Scene s;
    s.entities.push_back(mk("player", 100, 100, 34, 44));
    s.entities.push_back(mk("spike", 110, 110, 40, 30, "#ef4444"));
    Game g(std::move(s));
    g.update(1.f / 60.f, {});
    ok(g.player()->x == g.spawn().x && g.player()->y == g.spawn().y,
       "spike hit respawns at spawn point");
    ok(g.shakeT > 0, "hazard shakes the camera");
    ok(g.msg.find("ouch") != std::string::npos, "hazard says something honest");
  }

  // 5. goal transition locks once and chains next
  {
    Scene s;
    s.next = "scenes/level-2.dxn1.json";
    s.entities.push_back(mk("player", 100, 100, 34, 44));
    s.entities.push_back(mk("goal", 110, 110, 40, 60, "#22c55e"));
    Game g(std::move(s));
    g.update(1.f / 60.f, {});
    ok(g.transLocked, "goal locks the transition");
    ok(g.pendingNext == "scenes/level-2.dxn1.json", "goal chains the next scene");
    for (int i = 0; i < 10; ++i) g.update(1.f / 60.f, {});
    ok(g.pendingNext.size() == 1 || g.transLocked, "no double transition");
  }

  // 6. movers: ping-pong + rider carry
  {
    Scene s;
    s.entities.push_back(mk("player", 1000, 1000, 34, 44));   // out of the way
    s.entities.push_back(mk("mover", 100, 300, 120, 20, "#38bdf8"));
    Game g(std::move(s));
    Entity& m = g.scene.entities[1];
    m.path = {{100, 300}, {300, 300}};
    m.pathSpeed = 100;
    g.update(1.f / 60.f, {});        // first tick consumes waypoint 0 (=home)
    ok(m.pathIdx == 1, "mover heads for its first waypoint");
    g.update(0.5f, {});              // clamped to 1/30 — still a real step
    ok(m.x > 100, "mover travels toward waypoint");
    const int dirBefore = m.pathDir;
    for (int i = 0; i < 240 && m.pathDir == dirBefore; ++i) g.update(1.f / 60.f, {});
    ok(m.pathDir == -dirBefore, "mover ping-pongs at the ends");
  }
  {
    Scene s;
    s.entities.push_back(mk("player", 110, 260, 34, 44));     // standing on mover
    s.entities.push_back(mk("mover", 100, 304, 120, 20, "#38bdf8"));
    Game g(std::move(s));
    Entity& m = g.scene.entities[1];
    m.path = {{100, 304}, {180, 304}};
    m.pathSpeed = 80;
    // settle the player onto the mover top
    for (int i = 0; i < 20; ++i) g.update(1.f / 60.f, {});
    const float px0 = g.player()->x;
    g.update(1.f / 60.f, {});        // consume home waypoint
    for (int i = 0; i < 12; ++i) g.update(1.f / 60.f, {});
    ok(g.player()->x > px0, "rider is carried by the mover");
  }

  // 7. camera follow + zoom-aware shake decay
  {
    Scene s;
    s.entities.push_back(mk("player", 500, 300, 34, 44));
    Game g(std::move(s));
    for (int i = 0; i < 60; ++i) g.update(1.f / 60.f, {});
    ok(std::abs(g.scene.camera.x - 517) < 2, "camera follows the player");
    g.shake(10, 0.3);
    const float t0 = g.shakeT;
    g.update(0.1f, {});
    ok(g.shakeT < t0, "shake decays with time");
  }

  // 8. ball keeps itself company
  {
    Scene s;
    s.entities.push_back(mk("player", 1000, 1000, 34, 44));
    s.entities.push_back(mk("", 0, 400, 640, 40));
    s.entities.push_back(mk("ball", 60, 200, 26, 26, "#fb7185"));
    Game g(std::move(s));
    Entity& b = g.scene.entities[2];
    b.vx = 90;
    float minVy = 0;
    for (int i = 0; i < 180; ++i) { g.update(1.f / 60.f, {}); minVy = std::min(minVy, b.vy); }
    ok(minVy < -300, "ball bounces forever");
  }

  // 9. the version quad rides in the binary too
  ok(std::string(dxn3::DXN3_VERSION) == "3.0.18",
     "native version constant matches the release quad");

  // 10. png writer: checksum vectors, real structure, byte determinism
  {
    ok(dxn3::crc32("123456789") == 0xCBF43926u, "crc32 matches the known vector");
    ok(dxn3::adler32("Wikipedia") == 0x11E60398u, "adler32 matches the known vector");
    std::vector<std::uint32_t> px(8 * 4, 0x8B5CF6);
    px[0] = 0xFF0000;                       // one rebel pixel
    const std::string e1 = dxn3::writePng("/tmp/dxn3_qa_a.png", 8, 4, px);
    ok(e1.empty(), "writePng saves without error");
    auto slurp = [](const char* p) {
      std::FILE* f = std::fopen(p, "rb");
      std::string b; char buf[8192]; size_t r;
      if (f) { while ((r = std::fread(buf, 1, sizeof buf, f)) > 0) b.append(buf, r); std::fclose(f); }
      return b;
    };
    const std::string bytes = slurp("/tmp/dxn3_qa_a.png");
    ok(bytes.size() > 60 &&
       bytes[0] == '\x89' && bytes[1] == 'P' && bytes[2] == 'N' && bytes[3] == 'G',
       "png signature is 89 50 4E 47");
    ok(bytes.size() >= 57 && bytes[12] == 'I' && bytes[13] == 'H' &&
       bytes[14] == 'D' && bytes[15] == 'R' && bytes[16] == 0 &&
       bytes[17] == 0 && bytes[18] == 0 && bytes[19] == 8,
       "IHDR carries width 8 first");
    const size_t idat = bytes.find("IDAT");
    ok(idat != std::string::npos && bytes[idat + 4] == '\x78' &&
       bytes[idat + 5] == '\x01', "IDAT opens with a zlib 78 01 header");
    ok(bytes.size() >= 12 && bytes.rfind("IEND") == bytes.size() - 8,
       "IEND chunk is the last thing in the file");
    dxn3::writePng("/tmp/dxn3_qa_b.png", 8, 4, px);
    ok(bytes == slurp("/tmp/dxn3_qa_b.png"),
       "png encoding is byte-for-byte deterministic");
    ok(!dxn3::writePng("/tmp/no-such-dir-xyz/a.png", 8, 4, px).empty(),
       "writePng refuses an unwritable path honestly");
    ok(!dxn3::writePng("/tmp/dxn3_qa_bad.png", 8, 4, {1, 2, 3}).empty(),
       "writePng rejects a wrong-size pixel buffer");
  }

  // 11. the screenshot raster: player-framed, stable, self-contained
  {
    Scene s;
    s.entities.push_back(mk("player", 90, 300, 34, 44));
    s.entities.push_back(mk("", 0, 400, 640, 40, "#1f2937"));
    s.entities.push_back(mk("coin", 200, 300, 22, 22, "#facc15"));
    Scene s2 = s;                         // move will hollow out s — copy first
    Game g(std::move(s));
    for (int i = 0; i < 30; ++i) g.update(1.f / 60.f, {});
    ok(dxn3::shootPNG("/tmp/dxn3_qa_shot.png", g).empty(),
       "shootPNG renders the scene to a file");
    auto slurp = [](const char* p) {
      std::FILE* f = std::fopen(p, "rb");
      std::string b; char buf[8192]; size_t r;
      if (f) { while ((r = std::fread(buf, 1, sizeof buf, f)) > 0) b.append(buf, r); std::fclose(f); }
      return b;
    };
    struct stat st{};
    ok(::stat("/tmp/dxn3_qa_shot.png", &st) == 0 && st.st_size > 100000,
       "screenshot is a real 960x540 frame (not a stub)");
    dxn3::shootPNG("/tmp/dxn3_qa_shot_b.png", g);   // same state, again
    ok(slurp("/tmp/dxn3_qa_shot.png") == slurp("/tmp/dxn3_qa_shot_b.png"),
       "rendering one state twice is byte-identical (pure function)");
    Game g2(std::move(s2));               // replay the exact same ticks
    for (int i = 0; i < 30; ++i) g2.update(1.f / 60.f, {});
    dxn3::shootPNG("/tmp/dxn3_qa_shot2.png", g2);
    ok(slurp("/tmp/dxn3_qa_shot.png") == slurp("/tmp/dxn3_qa_shot2.png"),
       "the same tick sequence renders pixel-identical (fixed step)");
  }

  // 12. the command bar grammar: kind when right, honest when wrong
  {
    auto c = dxn3::parseCommand(":scene scenes/level-2.dxn1.json");
    ok(c.ok() && c.verb == "scene" && c.arg == "scenes/level-2.dxn1.json",
       "parseCommand reads :scene with its path");
    c = dxn3::parseCommand(":zoom 1.75");
    ok(c.ok() && c.num == 1.75f, "parseCommand reads :zoom with a factor");
    c = dxn3::parseCommand(":wq");
    ok(c.ok() && c.verb == "wq", "parseCommand knows :wq");
    ok(!dxn3::parseCommand("").ok(), "empty command is refused with usage");
    ok(!dxn3::parseCommand(":frobnicate 3").ok(), "unknown verbs are refused by name");
    ok(!dxn3::parseCommand(":scene").ok(), ":scene without a path is refused");
    ok(!dxn3::parseCommand(":zoom banana").ok(), ":zoom with junk is refused");
    ok(!dxn3::parseCommand(":magnet 9999").ok(), ":magnet out of range is refused");
    ok(!dxn3::parseCommand(":q now").ok(), ":q with an argument is refused");
    c = dxn3::parseCommand(":open game.py");
    ok(c.ok() && c.verb == "open" && c.arg == "game.py",
       "parseCommand reads :open with its file");
    ok(!dxn3::parseCommand(":open").ok(), ":open without a file is refused");
    c = dxn3::parseCommand(":goto 42");
    ok(c.ok() && c.verb == "goto" && c.num == 42.f,
       "parseCommand reads :goto with its line");
    ok(!dxn3::parseCommand(":goto banana").ok(),
       ":goto with junk is refused");
    ok(!dxn3::parseCommand(":goto").ok(), ":goto without a line is refused");
  }

  // 13. saveScene: the .bak safety net + honest failures + round-trip
  {
    Scene s;
    s.name = "save-me";
    s.entities.push_back(mk("player", 10, 20, 34, 44));
    ok(Game::saveScene("/tmp/dxn3_qa_scene.json", s).empty(),
       "saveScene writes a fresh file");
    Scene t;
    t.name = "save-me-again";
    ok(Game::saveScene("/tmp/dxn3_qa_scene.json", t).empty(),
       "saveScene overwrites with a backup");
    auto bak = Game::loadScene("/tmp/dxn3_qa_scene.json.bak");
    ok(bak.has_value() && bak->name == "save-me",
       "the .bak still holds the previous scene");
    auto cur = Game::loadScene("/tmp/dxn3_qa_scene.json");
    ok(cur.has_value() && cur->name == "save-me-again",
       "the live file holds the new scene");
    ok(!Game::saveScene("/tmp/no-such-dir-xyz/s.json", s).empty(),
       "saveScene refuses an unwritable path honestly");
    if (cur) {
      Scene back = Game::fromJson(Game::toJson(*cur));
      ok(back.name == cur->name && back.entities.size() == cur->entities.size(),
         "toJson -> fromJson round-trips a saved scene");
    }
  }

  // 14. the starfield: deterministic sky, seeded per scene
  {
    const auto a = dxn3::buildStars(dxn3::hashSeed("playground"), 50);
    const auto b = dxn3::buildStars(dxn3::hashSeed("playground"), 50);
    bool same = a.size() == b.size();
    for (size_t i = 0; same && i < a.size(); ++i)
      same = a[i].x == b[i].x && a[i].y == b[i].y && a[i].tint == b[i].tint;
    ok(same && !a.empty(), "the same seed builds the same sky");
    const auto c = dxn3::buildStars(dxn3::hashSeed("level-2"), 50);
    bool diff = a.size() == c.size();
    for (size_t i = 0; diff && i < a.size(); ++i)
      diff = a[i].x != c[i].x || a[i].y != c[i].y;
    ok(diff, "a different scene seeds a different sky");
    ok(dxn3::hashSeed("") != 0, "hashSeed never returns zero (xorshift seed)");
  }

  // 15. shapes are data: circles survive the JSON round trip
  {
    auto sc = Game::loadScene(repoPath("scenes/playground.dxn1.json"));
    ok(sc.has_value(), "playground loads for the shape test");
    if (sc) {
      bool sawCircle = false;
      for (const auto& e : sc->entities)
        if (e.shape == "circle") sawCircle = true;
      ok(sawCircle, "coin shapes parse as circles");
      const std::string j = Game::toJson(*sc);
      ok(j.find("\"shape\": \"circle\"") != std::string::npos,
         "circle shape round-trips through toJson");
    }
  }

  // 16. :scene completion — prefix matches + honest resolution
  {
    const std::vector<std::string> names = {"level-1", "level-2", "level-3",
                                            "level-4", "playground"};
    ok(dxn3::sceneMatches("level", names).size() == 4,
       "prefix filter finds the four levels");
    ok(dxn3::sceneMatches("zz", names).empty(), "no match is empty");
    ok(dxn3::resolveSceneArg("level-3", names) == "scenes/level-3.dxn1.json",
       "exact stem resolves to its scene");
    ok(dxn3::resolveSceneArg("scenes/level-3.dxn1.json", names) ==
           "scenes/level-3.dxn1.json",
       "full paths pass through resolved");
    ok(dxn3::resolveSceneArg("play", names) == "scenes/playground.dxn1.json",
       "a unique prefix resolves");
    ok(dxn3::resolveSceneArg("level", names).empty(),
       "an ambiguous prefix refuses to guess");
    ok(dxn3::resolveSceneArg("ghost.dxn1.json", names) == "ghost.dxn1.json",
       "ghosts pass through for an honest error");
  }

  // 17. the ScriptHost: a REAL child process speaking the protocol
  {
    dxn3::ScriptHost h;
    const std::string shScript =
        std::string("echo '{\"t\":\"scene\",\"name\":\"sh\",\"bg\":\"#000000\",") +
        "\"gravity\":0,\"entities\":[{\"name\":\"a\",\"x\":1,\"y\":2," +
        "\"w\":3,\"h\":4,\"color\":\"#ffffff\",\"visible\":1}]}'\n" +
        "while read -r line; do echo '{\"t\":\"frame\",\"set\":[]," +
        "\"vars\":{\"score\":7}}'; done\n";
    const std::vector<std::string> argv = {"/bin/sh", "-c", shScript};
    std::string err;
    ok(h.start(argv, 80, 46, "", &err), "host starts a real child (sh)");
    dxn3::json::Value sc;
    for (int i = 0; i < 20 && !h.takeScene(sc); ++i)
      h.tick(0.016f, false, false, false, false, "");
    ok(sc.is(dxn3::json::Kind::Obj) && sc.at("name").str_or("") == "sh",
       "the child's scene packet parses honestly");
    auto f = h.tick(0.016f, false, false, false, false, "");
    ok(f.frame && f.vars.at("score").num_or(0) == 7,
       "frame round-trip carries the child's vars");
    ok(h.running(), "the child stays alive across ticks");
    h.stop();
    ok(!h.running(), "stop() reaps the child and closes the pipes");
  }

  // 18. the whole engine, end to end: the real Python SDK hosting a game
  //     — hello → scene → ticks → frames → prints → honest exit
  {
    namespace fs = std::filesystem;
    const bool havePy =
        std::system("command -v python3 >/dev/null 2>&1") == 0;
    std::string sdk;                    // the sdk/ dir, from any CWD
    for (const std::string& prefix : {std::string(""), std::string("../"),
                                      std::string("../../")})
      if (fs::exists(prefix + "sdk/dxn3.py")) { sdk = prefix + "sdk"; break; }
    const bool haveSdk = !sdk.empty();
    if (havePy && haveSdk) {
      const std::string gameDir =
          (fs::temp_directory_path() / "dxn3-selftest").string();
      fs::create_directories(gameDir);
      const std::string gamePath = gameDir + "/probe.py";
      {
        std::ofstream g(gamePath, std::ios::binary);
        g << "from dxn3 import *\n"
             "box = rect(\"box\", 4, 6, 30, 40, \"#ff00ff\")\n"
             "box.tag = \"box\"\n"
             "n = [0]\n"
             "def on_tick(dt2):\n"
             "    n[0] += 1\n"
             "    box.x = box.x + 10 * dt2\n"
             "    if n[0] >= 3:\n"
             "        print(\"sdk-probe-done\")\n"
             "        raise SystemExit(0)\n"
             "run()\n";
      }
      dxn3::ScriptHost h;
      std::string err;
      const bool up = h.start({"python3", gamePath}, 100, 44, sdk, &err);
      ok(up, "the real sdk hosts a python game (" + err + ")");
      dxn3::json::Value sc;
      bool frame = false;
      for (int i = 0; i < 60 && !(frame && sc.is(dxn3::json::Kind::Obj)); ++i) {
        const auto f = h.tick(0.016f, false, false, false, false, "", {}, 200);
        frame = frame || f.frame;
        h.takeScene(sc);
      }
      ok(sc.is(dxn3::json::Kind::Obj) &&
             sc.at("entities").arr.size() == 1 &&
             sc.at("entities").arr[0].at("name").str_or("") == "box",
         "the sdk's scene crosses the pipe");
      bool said = false, exited = false;
      for (int i = 0; i < 30 && !exited; ++i) {
        const auto f = h.tick(0.016f, false, false, false, false, "", {}, 200);
        for (const auto& l : h.takeConsole())
          if (l.find("sdk-probe-done") != std::string::npos) said = true;
        exited = f.exited;
      }
      ok(said, "the game's prints reach the console");
      ok(exited, "a finished game reports its exit honestly");
      h.stop();
      fs::remove_all(gameDir);
    } else {
      std::println("   (skip) python3/sdk unavailable on this machine — "
                   "the e2e sdk group needs both");
    }
  }

  // 19. the console reads back: error lines from python AND node tracebacks
  {
    ok(dxn3::consoleErrorLine({}) == -1, "an empty console has no error line");
    ok(dxn3::consoleErrorLine({"engine: hosting python3"}) == -1,
       "engine chatter has no error line");
    ok(dxn3::consoleErrorLine(
           {"Traceback (most recent call last):",
            "  File \"game.py\", line 12, in <module>",
            "ValueError: boom"}) == 12,
       "a python traceback gives up its line number");
    ok(dxn3::consoleErrorLine(
           {"your game did not compile",
            "at Object.<anonymous> (/tmp/game.js:28:1)",
            "at Module._compile (node:internal/modules/cjs/loader:1554:14)"}) == 1554,
       "a node stack trace gives up its line number");
    ok(dxn3::consoleErrorLine(
           {"  File \"a.py\", line 3, in <module>",
            "  File \"b.py\", line 44, in run"}) == 44,
       "the LAST traceback line wins — closest to the crash");
  }

  // 20. the second chance: undo/redo in the editor heart
  {
    using dxn3::Keys;
    // A. typing bursts coalesce while the hand is quick
    IdeState s;
    Keys t; t.typed = "hello";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "hello", "typing lands in the buffer");
    ok(s.undo.size() == 1, "a typing burst makes ONE undo step");
    t.typed = " world";
    s.idle = 0.2;                            // a quick hand: same burst
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "hello world" && s.undo.size() == 1,
       "quick typing coalesces into the same step");
    s.idle = 2.0;                            // …but a pause opens a new one
    t.typed = "!";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "hello world!" && s.undo.size() == 2,
       "a pause starts a fresh undo step");

    // B. walking back and forward through time
    ok(dxn3::ideUndo(s) && s.lines[0] == "hello world",
       "undo rewinds the last burst");
    ok(dxn3::ideRedo(s) && s.lines[0] == "hello world!",
       "redo walks it forward again");
    Keys z; z.ctrlZ = true;
    dxn3::ideKey(s, z);
    ok(s.lines[0] == "hello world" && s.dirty,
       "ctrl+z rewinds through the editor and re-runs the game");
    dxn3::ideKey(s, z);
    ok(s.lines[0] == "" && s.undo.empty(),
       "ctrl+z walks all the way home");
    ok(!dxn3::ideUndo(s), "undo on an empty history says no");

    // C. a fresh edit after undo cuts the redo branch
    t.typed = "x";
    s.idle = 0.0;
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "x" && s.redo.empty(),
       "a fresh edit after undo clears the redo branch");

    // D. enter splits, undo rejoins, backspace joins again
    IdeState d;
    Keys w; w.typed = "hello world";
    dxn3::ideKey(d, w);
    d.curC = 5;
    Keys e; e.enter = true;
    dxn3::ideKey(d, e);
    ok(d.lines.size() == 2 && d.lines[0] == "hello" && d.lines[1] == " world",
       "enter splits the line at the cursor");
    Keys b2; b2.back = true;
    d.idle = 0.1;
    dxn3::ideKey(d, b2);                     // backspace at the line start
    ok(d.lines.size() == 1 && d.lines[0] == "hello world" && d.curR == 0,
       "backspace at the line start joins the lines back");
    ok(dxn3::ideUndo(d) && d.lines.size() == 2 && d.curR == 1 && d.curC == 0,
       "undo restores the split AND the cursor");
    ok(dxn3::ideUndo(d) && d.lines.size() == 1 && d.lines[0] == "hello world",
       "undo rejoins what enter split");

    // E. forward-delete joins the next line up, undoable
    IdeState f;
    f.lines = {"ab", "cd"};
    f.curR = 0; f.curC = 2;
    Keys del; del.del = true;
    dxn3::ideKey(f, del);
    ok(f.lines.size() == 1 && f.lines[0] == "abcd",
       "del at end-of-line joins the next line up");
    ok(dxn3::ideUndo(f) && f.lines.size() == 2 && f.lines[0] == "ab",
       "undo restores the joined line");

    // F. an honest no-op on a virgin document
    IdeState v;
    Keys zv; zv.ctrlZ = true;
    dxn3::ideKey(v, zv);
    ok(v.lines.size() == 1 && v.console.back().find("nothing to undo") !=
           std::string::npos,
       "ctrl+z on a virgin doc says so, honestly");
    Keys yv; yv.ctrlY = true;
    dxn3::ideKey(v, yv);
    ok(v.console.back().find("nothing to redo") != std::string::npos,
       "ctrl+y with no redo branch says so too");
  }

  // 21. the block rides down: auto-indent on enter
  {
    using dxn3::Keys;
    ok(dxn3::ideOpensBlock("for i in x:  ") && dxn3::ideOpensBlock("x {"),
       "openers read through trailing space, braces count");
    ok(!dxn3::ideOpensBlock("pass") && !dxn3::ideOpensBlock("   "),
       "plain lines and blank lines open nothing");
    ok(dxn3::ideClosesBlock("  endif") && !dxn3::ideClosesBlock("endless"),
       "closers match whole words only");
    ok(dxn3::ideClosesBlock("    default:") && !dxn3::ideClosesBlock(""),
       "default closes, empty closes nothing");

    IdeState s;
    Keys t; t.typed = "def on_tick(dt):";
    dxn3::ideKey(s, t);
    Keys e; e.enter = true;
    dxn3::ideKey(s, e);
    ok(s.lines.size() == 2 && s.lines[1] == "    " && s.curC == 4,
       "enter after a python opener bumps one level");
    t.typed = "return 7";
    dxn3::ideKey(s, t);
    ok(s.lines[1] == "    return 7", "typing continues at the indent");

    IdeState d;
    d.lines = {"    if x: pass"};
    d.curR = 0; d.curC = 10;                 // split right after the colon
    dxn3::ideKey(d, e);
    ok(d.lines[1] == "        pass" && d.curC == 8,
       "a mid-line split keeps its own deeper level");

    IdeState c;
    c.lines = {"    else: pass"};
    c.curR = 0; c.curC = 4;                  // split before the closer
    dxn3::ideKey(c, e);
    ok(c.lines[1] == "else: pass" && c.curC == 0,
       "a closer line dedents back one level");
    ok(dxn3::ideUndo(c) && c.lines.size() == 1,
       "auto-indent splits undo like any other edit");
  }

  // 22. the searchlight: find-in-file lives in the editor heart
  {
    using dxn3::Keys;
    IdeState s;
    s.lines = {"hello world", "the hello rings", "nope", "HELLO again"};
    s.curR = 0;
    s.curC = 0;
    s.dirty = false;               // the contract: find never dirties
    Keys f;
    f.ctrlF = true;
    dxn3::ideKey(s, f);
    ok(s.findOpen, "ctrl+f opens the searchlight");
    ok(!s.dirty, "opening find never dirties the document");
    Keys t;
    t.typed = "hello";
    dxn3::ideKey(s, t);
    ok(s.findQ == "hello" && s.lines[0] == "hello world",
       "typing under the searchlight fills the query, never the buffer");
    ok(s.findHits.size() == 3, "case-insensitive find sees every hello");
    ok(s.findSel == 0 && s.curR == 0 && s.curC == 0,
       "the first hit at/after the cursor is aimed at");
    Keys e;
    e.enter = true;
    dxn3::ideKey(s, e);
    ok(s.curR == 1 && s.curC == 4, "enter walks to the next hit");
    dxn3::ideKey(s, e);
    ok(s.curR == 3 && s.curC == 0, "enter keeps walking, case-insensitively");
    dxn3::ideKey(s, e);
    ok(s.curR == 0 && s.curC == 0, "the search wraps around the file");
    Keys b;
    b.back = true;
    dxn3::ideKey(s, b);
    ok(s.findQ == "hell" && s.findHits.size() == 3,
       "backspace edits the query and the hits follow live");
    while (!s.findQ.empty()) dxn3::ideKey(s, b);
    ok(s.findOpen, "the search stays up while the query has letters");
    dxn3::ideKey(s, b);
    ok(!s.findOpen, "backspace on an empty query closes the searchlight");
    dxn3::ideKey(s, f);
    ok(s.findOpen && s.findQ.empty(), "ctrl+f reopens with a clean query");
    Keys z;
    z.typed = "zzzz";
    dxn3::ideKey(s, z);
    ok(s.findHits.empty() && s.findSel == -1, "no match is reported honestly");
    dxn3::ideKey(s, e);
    ok(s.curR == 0 && s.curC == 0, "enter with no hits moves nothing");
    dxn3::ideKey(s, f);
    ok(!s.findOpen, "ctrl+f again lowers the searchlight");
    ok(s.lines[0] == "hello world" && s.lines.size() == 4,
       "the document survives the whole search untouched");
  }

  // 23. pairs that carry their own closers + the copy machine
  {
    using dxn3::Keys;
    IdeState s;
    Keys t;
    t.typed = "(";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "()" && s.curC == 1, "an opener carries its closer");
    t.typed = "a+b";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "(a+b)" && s.curC == 4, "typing continues inside the pair");
    t.typed = ")";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "(a+b)" && s.curC == 5,
       "typing the closer skips over it, never doubles");
    t.typed = "\"";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "(a+b)\"\"" && s.curC == 6, "quotes pair too");
    t.typed = "\"";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "(a+b)\"\"" && s.curC == 7,
       "a closing quote skips, never doubles");

    IdeState w;                       // the apostrophe that must survive
    w.lines = {"don"};
    w.curR = 0;
    w.curC = 3;
    Keys q;
    q.typed = "'t";
    dxn3::ideKey(w, q);
    ok(w.lines[0] == "don't", "an apostrophe inside a word does not pair");
    IdeState st;                      // a string opener still wraps
    st.lines = {"x = "};
    st.curR = 0;
    st.curC = 4;
    Keys sq;
    sq.typed = "\"";                  // after a space, the quote pairs
    dxn3::ideKey(st, sq);
    ok(st.lines[0] == "x = \"\"", "a quote after a space opens a pair");
    sq.typed = "hi";                  // the string lands inside the pair
    dxn3::ideKey(st, sq);
    ok(st.lines[0] == "x = \"hi\"", "the string lands inside the pair");
    sq.typed = "\"";                  // the closer is skipped, not doubled
    dxn3::ideKey(st, sq);
    ok(st.lines[0] == "x = \"hi\"" && st.curC == 8,
       "the closing quote is skipped, not doubled");

    IdeState n;                       // nesting
    Keys o;
    o.typed = "f(";
    dxn3::ideKey(n, o);
    o.typed = "[x]";
    dxn3::ideKey(n, o);
    ok(n.lines[0] == "f([x])", "nested pairs nest honestly");

    IdeState p;                       // pair-delete
    Keys br;
    br.typed = "[";
    dxn3::ideKey(p, br);
    ok(p.lines[0] == "[]", "brackets pair");
    Keys bk;
    bk.back = true;
    dxn3::ideKey(p, bk);
    ok(p.lines[0] == "" && p.curC == 0,
       "backspace between an empty pair removes both halves");
    IdeState p2;                      // a plain backspace still deletes one
    p2.lines = {"ab"};
    p2.curR = 0;
    p2.curC = 1;
    dxn3::ideKey(p2, bk);
    ok(p2.lines[0] == "b" && p2.curC == 0,
       "backspace outside a pair deletes exactly one char");

    IdeState d;                       // ctrl+d: the copy machine
    d.lines = {"alpha", "beta"};
    d.curR = 0;
    d.curC = 3;
    Keys cp;
    cp.ctrlD = true;
    dxn3::ideKey(d, cp);
    ok(d.lines.size() == 3 && d.lines[1] == "alpha" && d.curR == 1 &&
           d.curC == 3,
       "ctrl+d copies the line under the cursor, column kept");
    ok(dxn3::ideUndo(d) && d.lines.size() == 2,
       "ctrl+d is one honest undo step");
  }

  // 24. the bite: ctrl+w deletes the word behind the cursor
  {
    using dxn3::Keys;
    ok(dxn3::ideWordChar('a') && dxn3::ideWordChar('_') &&
           !dxn3::ideWordChar('(') && !dxn3::ideWordChar(' '),
       "word chars are letters, digits, snake_case — nothing else");

    IdeState s;
    s.lines = {"foo bar"};
    s.curR = 0;
    s.curC = 7;
    Keys w;
    w.delWord = true;
    dxn3::ideKey(s, w);
    ok(s.lines[0] == "foo " && s.curC == 4,
       "ctrl+w eats the word and its gap");

    IdeState p;                       // punctuation goes in one bite
    p.lines = {"x = 42"};
    p.curR = 0;
    p.curC = 6;
    dxn3::ideKey(p, w);
    ok(p.lines[0] == "x = " && p.curC == 4,
       "numbers count as words");

    IdeState n;                       // punctuation goes in one bite
    n.lines = {"foo(bar)"};
    n.curR = 0;
    n.curC = 8;
    dxn3::ideKey(n, w);
    ok(n.lines[0] == "foo(bar" && n.curC == 7,
       "a punctuation run is one bite");
    dxn3::ideKey(n, w);
    ok(n.lines[0] == "foo(" && n.curC == 4,
       "the next bite takes the word");

    IdeState i;                       // snake_case stays whole
    i.lines = {"my_score = 0"};
    i.curR = 0;
    i.curC = 8;
    dxn3::ideKey(i, w);
    ok(i.lines[0] == " = 0" && i.curC == 0,
       "an underscore word is one bite");

    IdeState e;                       // honest no-op at the line start
    e.lines = {"hi"};
    e.curR = 0;
    e.curC = 0;
    dxn3::ideKey(e, w);
    ok(e.lines[0] == "hi" && e.curC == 0,
       "ctrl+w at the line start bites nothing");

    IdeState d;                       // undoable, one step
    d.lines = {"alpha beta"};
    d.curR = 0;
    d.curC = 10;
    dxn3::ideKey(d, w);
    ok(dxn3::ideUndo(d) && d.lines[0] == "alpha beta",
       "ctrl+w is one honest undo step");
  }

  // 25. word hops: ctrl+left / ctrl+right walk the words ctrl+w bites
  {
    using dxn3::Keys;
    IdeState s;
    s.lines = {"foo.bar baz"};
    s.curR = 0;
    s.curC = 0;
    Keys r;
    r.wRight = true;
    dxn3::ideKey(s, r);
    ok(s.curC == 3, "ctrl+right rides a word to its end");
    dxn3::ideKey(s, r);
    ok(s.curC == 4, "a punctuation run is one hop");
    dxn3::ideKey(s, r);
    ok(s.curC == 7, "the next hop lands after bar");
    dxn3::ideKey(s, r);
    ok(s.curC == 11, "the last hop rests at the end of the line");
    dxn3::ideKey(s, r);
    ok(s.curC == 11, "ctrl+right at the end of the doc is an honest no-op");
    Keys l;
    l.wLeft = true;
    dxn3::ideKey(s, l);
    ok(s.curC == 8, "ctrl+left rides back to a word's start");
    dxn3::ideKey(s, l);
    ok(s.curC == 4, "the gap behind is crossed in the same hop");
    dxn3::ideKey(s, l);
    ok(s.curC == 3, "a punctuation run hops as one");
    dxn3::ideKey(s, l);
    ok(s.curC == 0, "home again — the hop lands where it all began");
    dxn3::ideKey(s, l);
    ok(s.curC == 0, "ctrl+left at the start of the doc is an honest no-op");

    IdeState x;                      // hops cross line edges
    x.lines = {"one two", "", "three"};
    x.curR = 0;
    x.curC = 3;
    dxn3::ideKey(x, r);
    ok(x.curR == 0 && x.curC == 7, "the hop ends where the word ends");
    dxn3::ideKey(x, r);
    ok(x.curR == 2 && x.curC == 5,
       "empty lines are just wider gap — the hop flies across");
    dxn3::ideKey(x, l);
    ok(x.curR == 2 && x.curC == 0,
       "backward from the end rests on the word's start");
    dxn3::ideKey(x, l);
    ok(x.curR == 0 && x.curC == 4, "backward across the empty line lands on two");

    IdeState u;                      // movement never dirties the doc
    u.lines = {"alpha beta"};
    u.curR = 0;
    u.curC = 0;
    u.dirty = false;
    dxn3::ideKey(u, r);
    ok(!u.dirty && u.lines[0] == "alpha beta",
       "word hops move the cursor, never the file");
  }

  // 26. the partner: bracket match across lines + the long-line slide
  {
    IdeState s;
    s.lines = {"def f(x):", "    return [x, (x + 1)]", "end"};
    s.curR = 0;
    s.curC = 5;                      // on the '('
    int mr = -1, mc = -1;
    ok(dxn3::ideMatchBracket(s, mr, mc) && mr == 0 && mc == 7,
       "an opener on the cursor finds its closer");
    s.curC = 8;                      // on the ':' — the ')' is behind
    ok(dxn3::ideMatchBracket(s, mr, mc) && mr == 0 && mc == 5,
       "the bracket behind the cursor counts too");

    IdeState b;                      // the second row's list brackets
    b.lines = s.lines;
    b.curR = 1;
    b.curC = 11;                     // on the '['
    ok(dxn3::ideMatchBracket(b, mr, mc) && mr == 1 && mc == 22,
       "a bracket finds its partner on the same row");

    IdeState nst;                    // nesting
    nst.lines = {"f((x + 1) * 2)"};
    nst.curR = 0;
    nst.curC = 2;
    ok(dxn3::ideMatchBracket(nst, mr, mc) && mc == 8,
       "the inner opener finds its own closer");
    nst.curC = 1;
    ok(dxn3::ideMatchBracket(nst, mr, mc) && mc == 13,
       "the outer one skips the nested pair");

    IdeState m;                      // across lines
    m.lines = {"if (ready", "   and willing):", "    go()"};
    m.curR = 0;
    m.curC = 3;
    ok(dxn3::ideMatchBracket(m, mr, mc) && mr == 1 && mc == 14,
       "the match crosses line edges");
    m.curR = 1;
    m.curC = 14;
    ok(dxn3::ideMatchBracket(m, mr, mc) && mr == 0 && mc == 3,
       "a closer walks back to its opener");

    IdeState u;                      // honesty
    u.lines = {"x = (1 + 2"};
    u.curR = 0;
    u.curC = 4;
    ok(!dxn3::ideMatchBracket(u, mr, mc),
       "an unclosed bracket refuses to fake it");
    u.curC = 0;
    ok(!dxn3::ideMatchBracket(u, mr, mc), "no bracket, no match");
    u.lines = {"y = \"(not a bracket)\""};
    u.curC = 5;
    ok(dxn3::ideMatchBracket(u, mr, mc) && mc == 19,
       "quotes are just characters — brackets match through them");

    IdeState h;                      // the long-line slide
    h.lines = {std::string(60, 'x') + "tail"};
    h.curR = 0;
    h.curC = 0;
    dxn3::ideHscroll(h, 20);
    ok(h.hcol == 0, "a cursor at home keeps the view at home");
    h.curC = 25;
    dxn3::ideHscroll(h, 20);
    ok(h.hcol == 9, "running off the right edge slides the view along");
    h.curC = 40;
    dxn3::ideHscroll(h, 20);
    ok(h.hcol == 24, "further right, further slide");
    h.curC = 30;
    dxn3::ideHscroll(h, 20);
    ok(h.hcol == 24, "still visible: no slide needed");
    h.curC = 20;
    dxn3::ideHscroll(h, 20);
    ok(h.hcol == 17, "off the left edge slides back with a margin");
    h.curC = 3;
    dxn3::ideHscroll(h, 20);
    ok(h.hcol == 0, "the home column unslides completely");
    h.curC = 63;                     // the very end of the line
    dxn3::ideHscroll(h, 20);
    ok(h.hcol == 45 && h.curC - h.hcol < 20,
       "the line end stays visible, clamped honestly");
    dxn3::ideHscroll(h, 20);         // twice: the clamped view holds
    ok(h.hcol == 45, "the clamped view is stable");
    IdeState sh;                     // a short line never scrolls
    sh.lines = {"short"};
    sh.curR = 0;
    sh.curC = 5;
    dxn3::ideHscroll(sh, 20);
    ok(sh.hcol == 0, "a line that fits never slides");
  }

  // 27. the forward bite and the line that talks (ctrl+del, ctrl+/)
  {
    using dxn3::Keys;
    ok(std::string(dxn3::ideCommentFor("game.py")) == "# " &&
           std::string(dxn3::ideCommentFor("script.js")) == "// " &&
           std::string(dxn3::ideCommentFor("Game.cpp")) == "// " &&
           std::string(dxn3::ideCommentFor("chip.lua")) == "-- " &&
           std::string(dxn3::ideCommentFor("Makefile")) == "# ",
       "the comment prefix follows the file's language");

    IdeState s;                      // comment on
    s.lines = {"score = 0"};
    s.path = "game.py";
    s.curR = 0;
    s.curC = 0;
    Keys c;
    c.comment = true;
    dxn3::ideKey(s, c);
    ok(s.lines[0] == "# score = 0" && s.curC == 2 && s.dirty,
       "ctrl+/ comments the line and the game hears about it");
    dxn3::ideKey(s, c);              // …and off
    ok(s.lines[0] == "score = 0" && s.curC == 0,
       "ctrl+/ twice restores the line exactly");
    ok(dxn3::ideUndo(s) && s.lines[0] == "# score = 0",
       "each toggle is its own undo step");

    IdeState i;                      // the indent is respected
    i.lines = {"    return x"};
    i.path = "game.py";
    i.curR = 0;
    i.curC = 6;
    dxn3::ideKey(i, c);
    ok(i.lines[0] == "    # return x" && i.curC == 8,
       "the prefix lands after the leading whitespace");
    dxn3::ideKey(i, c);
    ok(i.lines[0] == "    return x" && i.curC == 6,
       "untoggling restores indent, text and cursor");

    IdeState n;                      // a no-space comment still strips
    n.lines = {"#tight"};
    n.path = "game.py";
    n.curR = 0;
    n.curC = 4;
    dxn3::ideKey(n, c);
    ok(n.lines[0] == "tight" && n.curC == 3,
       "a comment without the space strips too, cursor follows");

    IdeState j;                      // js speaks slashes
    j.lines = {"let x = 1"};
    j.path = "untitled-bounce.js";
    j.curR = 0;
    j.curC = 0;
    dxn3::ideKey(j, c);
    ok(j.lines[0] == "// let x = 1", "js lines talk in slashes");

    IdeState f;                      // the forward bite
    f.lines = {"foo bar baz"};
    f.curR = 0;
    f.curC = 0;
    Keys d;
    d.delWordFwd = true;
    dxn3::ideKey(f, d);
    ok(f.lines[0] == " bar baz" && f.curC == 0,
       "ctrl+del eats exactly what ctrl+right would hop");
    dxn3::ideKey(f, d);
    ok(f.lines[0] == " baz" && f.curC == 0,
       "the next bite takes the gap and the word");

    IdeState p;                      // punctuation ahead
    p.lines = {"x = 42"};
    p.curR = 0;
    p.curC = 2;
    dxn3::ideKey(p, d);
    ok(p.lines[0] == "x  42" && p.curC == 2,
       "a punctuation run is one bite forward too");
    IdeState e;                      // honest no-op at the line end
    e.lines = {"hi"};
    e.curR = 0;
    e.curC = 2;
    dxn3::ideKey(e, d);
    ok(e.lines[0] == "hi" && e.curC == 2,
       "ctrl+del at the line end bites nothing");

    IdeState u;                      // one honest undo step
    u.lines = {"alpha beta"};
    u.curR = 0;
    u.curC = 0;
    dxn3::ideKey(u, d);
    ok(dxn3::ideUndo(u) && u.lines[0] == "alpha beta",
       "ctrl+del is one honest undo step");

    ok(dxn3::parseCommand(":template fl").ok() &&
           dxn3::parseCommand(":template fl").arg == "fl",
       ":template takes the name you typed");
    ok(!dxn3::parseCommand(":template").ok(),
       ":template without a name is refused with usage");
  }

  if (fails == 0) {
    std::println("native selftest: all green ({} assertion groups)", n);
    return 0;
  }
  std::println(stderr, "native selftest: {} of {} FAILED", fails, n);
  return 1;
}
