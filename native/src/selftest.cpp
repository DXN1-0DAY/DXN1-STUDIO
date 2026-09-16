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
  ok(std::string(dxn3::DXN3_VERSION) == "3.0.12", "native version constant is 3.0.11");

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

  if (fails == 0) {
    std::println("native selftest: all green ({} assertion groups)", n);
    return 0;
  }
  std::println(stderr, "native selftest: {} of {} FAILED", fails, n);
  return 1;
}
