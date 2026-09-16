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
  ok(std::string(dxn3::DXN3_VERSION) == "3.0.37",
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
    const auto openBare = dxn3::parseCommand(":open");
    ok(openBare.ok(), "a bare :open is legal — the ledger's head answers");
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

  // 28. the snippet shelf: boilerplate that speaks the file's language
  {
    std::vector<std::string> block;
    auto get = [&](const char* nm, const char* path) {
      auto b = dxn3::ideSnippetFor(nm, path);
      if (b) block = *b;
      return b.has_value();
    };
    ok(get("fn", "game.py") && block[0] == "def name(arg):",
       "a py file speaks def-style snippets");
    ok(get("tick", "game.py") && block[0] == "def on_tick(dt):" &&
           block.size() == 2,
       "the tick snippet is the engine's own contract");
    ok(get("tick", "game.js") && block[0] == "on.tick(() => {" &&
           block.back() == "});",
       "a js file speaks on.tick snippets");
    ok(get("tick", "game.cpp") && block[0].rfind("g.onTick", 0) == 0,
       "a cpp file speaks g.onTick snippets");
    ok(!dxn3::ideSnippetFor("nope", "game.py").has_value(),
       "a ghost snippet is refused honestly");
    const auto names = dxn3::ideSnippetNames("game.py");
    ok(names.size() >= 8, "the py shelf is stocked");
    ok(dxn3::ideSnippetNames("game.js").size() >= 5 &&
           dxn3::ideSnippetNames("game.cpp").size() >= 4,
       "the js and cpp shelves are stocked too");
    ok(dxn3::ideSnippetFamily("Makefile") == std::string("py"),
       "an extensionless file defaults to the py shelf");

    IdeState s;                      // a blank line is the stage
    s.lines = {""};
    s.path = "game.py";
    s.curR = 0;
    s.curC = 0;
    block = *dxn3::ideSnippetFor("key", "game.py");
    dxn3::ideInsertBlock(s, block);
    ok(s.lines.size() == 2 && s.lines[0] == "def on_key(k):" &&
           s.lines[1] == "    pass" && s.curR == 1 && s.curC == 8 && s.dirty,
       "a snippet replaces the blank line, cursor rests at its end");
    ok(dxn3::ideUndo(s) && s.lines.size() == 1 && s.lines[0] == "",
       "a snippet insert is one honest undo step");

    IdeState n;                      // code below: the block slides after
    n.lines = {"score = 0", "run()"};
    n.path = "game.py";
    n.curR = 0;
    n.curC = 9;
    block = *dxn3::ideSnippetFor("loop", "game.py");
    dxn3::ideInsertBlock(n, block);
    ok(n.lines.size() == 4 && n.lines[1] == "for i in range(10):" &&
           n.lines[2] == "    print(i)" && n.curR == 2 && n.curC == 12,
       "a snippet slides in after the cursor line");
    ok(dxn3::ideUndo(n) && n.lines.size() == 2,
       "the slide-in undoes whole");
  }

  // 29. the edges: ctrl+home / ctrl+end, and the new verbs' grammar
  {
    using dxn3::Keys;
    IdeState s;
    s.lines = {"first", "second line here", "last"};
    s.curR = 1;
    s.curC = 5;
    s.dirty = false;                 // a settled doc: jumps must keep it so
    Keys h;
    h.docHome = true;
    dxn3::ideKey(s, h);
    ok(s.curR == 0 && s.curC == 0, "ctrl+home jumps to the very top");
    Keys e;
    e.docEnd = true;
    dxn3::ideKey(s, e);
    ok(s.curR == 2 && s.curC == 4, "ctrl+end jumps to the very bottom");
    ok(!s.dirty, "jumping the edges never dirties the doc");

    ok(dxn3::parseCommand(":snip fn").ok() &&
           dxn3::parseCommand(":snip fn").arg == "fn",
       ":snip takes a name");
    ok(!dxn3::parseCommand(":snip").ok(),
       ":snip without a name is refused with usage");
    ok(dxn3::parseCommand(":ruler").ok(), ":ruler is well-formed bare");
    ok(!dxn3::parseCommand(":ruler 80").ok(),
       ":ruler with an argument is refused");
    ok(dxn3::parseCommand(":stats").ok(), ":stats is well-formed");
    ok(dxn3::usageHintFor(":snip").find("fn tick") != std::string::npos,
       "the snip whisper names the shelf");
    ok(dxn3::usageHintFor(":ruler").find("79") != std::string::npos,
       "the ruler whisper tells you what it does");
    ok(dxn3::usageHintFor(":stats").find("words") != std::string::npos,
       "the stats whisper tells you what it counts");
  }

  // 30. the selection: shift extends, edits replace, comments span
  {
    using dxn3::Keys;
    IdeState s;
    s.lines = {"hello world", "second line", "third"};
    s.curR = 0;
    s.curC = 0;
    s.dirty = false;
    Keys sr;
    sr.sRight = true;
    for (int i = 0; i < 5; ++i) dxn3::ideKey(s, sr);
    ok(s.anchorR == 0 && s.anchorC == 0 && s.curC == 5,
       "shift+right extends from a born anchor");
    auto sel = dxn3::ideSelRange(s);
    ok(sel.has_value() && (*sel)[0] == 0 && (*sel)[1] == 0 &&
           (*sel)[2] == 0 && (*sel)[3] == 5,
       "the range orders anchor before cursor");
    Keys t;
    t.typed = "X";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "X world" && s.curR == 0 && s.curC == 1 &&
           s.anchorR < 0,
       "typing replaces the selection and clears the anchor");
    ok(dxn3::ideUndo(s) && s.lines[0] == "hello world",
       "a selection replacement is one honest undo step");

    IdeState m;                      // shift+down spans lines
    m.lines = {"# one", "# two", "three"};
    m.path = "game.py";
    m.curR = 0;
    m.curC = 0;
    Keys sd;
    sd.sDown = true;
    dxn3::ideKey(m, sd);
    auto ms = dxn3::ideSelRange(m);
    ok(ms.has_value() && (*ms)[0] == 0 && (*ms)[2] == 1,
       "shift+down spans lines");
    Keys c;
    c.comment = true;
    dxn3::ideKey(m, c);
    ok(m.lines[0] == "one" && m.lines[1] == "two" && m.lines[2] == "three" &&
           m.anchorR < 0,
       "a multi-line toggle strips every comment line the selection touches");
    ok(dxn3::ideUndo(m) && m.lines[0] == "# one" && m.lines[1] == "# two",
       "the multi-line toggle is one honest undo step");

    IdeState p;                      // a plain move drops the selection
    p.lines = {"abc", "def"};
    p.curR = 0;
    p.curC = 0;
    Keys sr2;
    sr2.sRight = true;
    dxn3::ideKey(p, sr2);
    ok(dxn3::ideSelRange(p).has_value(), "a selection exists after shift");
    Keys down;
    down.down = true;
    dxn3::ideKey(p, down);
    ok(!dxn3::ideSelRange(p).has_value() && p.curR == 1,
       "a plain move drops the selection");

    IdeState b;                      // backspace eats only the range
    b.lines = {"hello world"};
    b.curR = 0;
    b.curC = 0;
    Keys sr3;
    sr3.sRight = true;
    for (int i = 0; i < 5; ++i) dxn3::ideKey(b, sr3);
    Keys bs;
    bs.back = true;
    dxn3::ideKey(b, bs);
    ok(b.lines[0] == " world" && b.curC == 0 &&
           !dxn3::ideSelRange(b).has_value(),
       "backspace with a selection eats only the range");

    IdeState j;                      // a spanning cut joins the lines
    j.lines = {"first half", "second half"};
    j.curR = 0;
    j.curC = 6;
    j.anchorR = 1;
    j.anchorC = 6;
    ok(dxn3::ideSelDelete(j) && j.lines.size() == 1 &&
           j.lines[0] == "first  half" && j.curC == 6 && j.anchorR < 0,
       "a spanning cut joins the lines at the range");

    IdeState e2;                     // anchor == cursor: no selection at all
    e2.lines = {"x"};
    e2.curR = 0;
    e2.curC = 0;
    e2.anchorR = 0;
    e2.anchorC = 0;
    ok(!dxn3::ideSelRange(e2).has_value() && !dxn3::ideSelDelete(e2),
       "anchor == cursor is no selection at all");
  }

  // 31. the clipboard: copy, cut, paste — the way every editor speaks it
  {
    using dxn3::Keys;
    IdeState s;
    s.lines = {"hello world", "second line", "third"};
    s.curR = 0;
    s.curC = 0;
    Keys sr;
    sr.sRight = true;
    for (int i = 0; i < 5; ++i) dxn3::ideKey(s, sr);
    Keys cc;
    cc.ctrlC = true;
    dxn3::ideKey(s, cc);
    ok(s.clip.size() == 1 && s.clip[0] == "hello" && !s.clipLines,
       "copy takes the exact selection");
    ok(s.lines[0] == "hello world" && dxn3::ideSelRange(s).has_value(),
       "copy keeps the document and the selection");

    Keys hm;                        // home (a plain move) drops the range
    hm.docHome = true;
    dxn3::ideKey(s, hm);
    Keys cv;
    cv.ctrlV = true;                // splice at the hand: hello + hello world
    dxn3::ideKey(s, cv);
    ok(s.lines[0] == "hellohello world" && s.curC == 5 && s.anchorR < 0,
       "paste splices at the cursor and lands at the clip's end");
    ok(dxn3::ideUndo(s) && s.lines[0] == "hello world",
       "a paste is one honest undo step");

    for (int i = 0; i < 5; ++i) dxn3::ideKey(s, sr);   // re-select "hello"
    Keys cx;                        // cut the range back out
    cx.ctrlX = true;
    dxn3::ideKey(s, cx);
    ok(s.lines[0] == " world" && s.clip[0] == "hello" && s.curC == 0,
       "cut removes the range and keeps it in the clip");
    ok(dxn3::ideUndo(s) && s.lines[0] == "hello world",
       "a cut is one honest undo step");

    IdeState ln;                    // a bare copy lifts the whole line
    ln.lines = {"alpha", "beta"};
    ln.curR = 0;
    ln.curC = 3;
    Keys cc2;
    cc2.ctrlC = true;
    dxn3::ideKey(ln, cc2);
    ok(ln.clip.size() == 1 && ln.clip[0] == "alpha" && ln.clipLines,
       "a copy with no selection lifts the whole cursor line");
    Keys cv2;
    cv2.ctrlV = true;               // line-wise: lands ABOVE the cursor line
    ln.curR = 1;
    dxn3::ideKey(ln, cv2);
    ok(ln.lines.size() == 3 && ln.lines[1] == "alpha" && ln.lines[2] == "beta",
       "a line-wise paste lands above the cursor line");
    ok(dxn3::ideUndo(ln) && ln.lines.size() == 2,
       "the line paste undoes whole");

    IdeState cl;                    // a bare cut lifts the line out
    cl.lines = {"alpha", "beta"};
    cl.curR = 1;
    cl.curC = 1;
    Keys cx2;
    cx2.ctrlX = true;
    dxn3::ideKey(cl, cx2);
    ok(cl.lines.size() == 1 && cl.lines[0] == "alpha" && cl.clipLines &&
           cl.clip[0] == "beta" && cl.curC == 0,
       "a bare cut lifts the whole line out");
    Keys cv3;
    cv3.ctrlV = true;
    dxn3::ideKey(cl, cv3);          // the line returns above line 1
    ok(cl.lines.size() == 2 && cl.lines[0] == "beta" && cl.lines[1] == "alpha",
       "the lifted line pastes back as a line");
    ok(dxn3::ideUndo(cl) && cl.lines.size() == 1,
       "the line cut undoes whole");

    IdeState last;                  // cutting the only line never kills the doc
    last.lines = {"only"};
    last.curR = 0;
    Keys cx3;
    cx3.ctrlX = true;
    dxn3::ideKey(last, cx3);
    ok(last.lines.size() == 1 && last.lines[0].empty(),
       "cutting the only line leaves one honest empty line");
    ok(dxn3::ideUndo(last) && last.lines[0] == "only",
       "the lone-line cut undoes whole");

    IdeState sel;                   // paste over a live selection: one step
    sel.lines = {"keep this"};
    sel.curR = 0;
    sel.curC = 0;
    sel.anchorR = 0;
    sel.anchorC = 4;                // "keep" selected
    sel.clip = {"NEW"};             // the clip rides in from an earlier copy
    sel.clipLines = false;
    Keys cv4;
    cv4.ctrlV = true;
    dxn3::ideKey(sel, cv4);
    ok(sel.lines[0] == "NEW this" && sel.curC == 3 && sel.anchorR < 0,
       "pasting over a selection replaces it with the clip");
    ok(dxn3::ideUndo(sel) && sel.lines[0] == "keep this",
       "the selection paste is one honest step (doc restored)");
  }

  // 32. word select, the pair ceremony, multi-dup, and the tab trigger
  {
    using dxn3::Keys;
    IdeState s;                     // shift+ctrl+right selects word by word
    s.lines = {"# FLAPPY in the sky"};
    s.curR = 0;
    s.curC = 0;
    Keys sw;
    sw.sWRight = true;
    dxn3::ideKey(s, sw);
    ok(s.curC == 1 && s.anchorR == 0 && s.anchorC == 0,
       "shift+ctrl+right hops word-wise with the anchor riding");
    auto sel = dxn3::ideSelRange(s);
    ok(sel.has_value() && (*sel)[0] == 0 && (*sel)[1] == 0 &&
           (*sel)[2] == 0 && (*sel)[3] == 1,
       "the word hop's range is honest");
    Keys sw2;
    sw2.sWRight = true;
    dxn3::ideKey(s, sw2);
    ok(s.curC == 8, "the next hop rides FLAPPY to its end");
    Keys sw3;
    sw3.sWLeft = true;
    dxn3::ideKey(s, sw3);
    ok(s.curC == 2, "shift+ctrl+left rides back to the word's start");
    Keys pl;
    pl.down = true;
    dxn3::ideKey(s, pl);
    ok(!dxn3::ideSelRange(s).has_value(),
       "a plain move still drops the word selection");

    IdeState p;                     // enter between a pair: the ceremony
    p.lines = {"f()"};
    p.curR = 0;
    p.curC = 2;                     // between ( and )
    Keys en;
    en.enter = true;
    dxn3::ideKey(p, en);
    ok(p.lines.size() == 3 && p.lines[0] == "f(" && p.lines[1].empty() &&
           p.lines[2] == ")",
       "enter between ( ) splits into the three-line ceremony");
    ok(p.curR == 1 && p.curC == 0,
       "the cursor rests on the naked middle line");
    ok(dxn3::ideUndo(p) && p.lines.size() == 1 && p.lines[0] == "f()",
       "the pair split is one honest undo step");

    IdeState br;                    // a brace pair bumps the middle line
    br.lines = {"if (x) {}"};
    br.curR = 0;
    br.curC = 8;                    // between { and }
    Keys en2;
    en2.enter = true;
    dxn3::ideKey(br, en2);
    ok(br.lines.size() == 3 && br.lines[1] == "    " && br.lines[2] == "}",
       "enter between { } keeps the closer at the base indent");

    IdeState q;                     // quotes are honestly out
    q.lines = {"say \"\""};
    q.curR = 0;
    q.curC = 5;                     // between the two quote chars
    Keys en3;
    en3.enter = true;
    dxn3::ideKey(q, en3);
    ok(q.lines.size() == 2 && q.lines[0] == "say \"" && q.lines[1] == "\"",
       "enter between quotes is just a plain split — no ceremony");

    IdeState d;                     // ctrl+d duplicates the SELECTED lines
    d.lines = {"# one", "# two", "three"};
    d.curR = 0;
    d.curC = 0;
    Keys sd;
    sd.sDown = true;
    dxn3::ideKey(d, sd);
    Keys dd;
    dd.ctrlD = true;
    dxn3::ideKey(d, dd);
    ok(d.lines.size() == 5 && d.lines[2] == "# one" && d.lines[3] == "# two",
       "ctrl+d with a multi-line selection duplicates every touched line");
    ok(d.curR == 3 && d.anchorR == 2,
       "the copy carries the cursor and the anchor with it");
    ok(dxn3::ideUndo(d) && d.lines.size() == 3,
       "the multi-duplicate is one honest undo step");

    IdeState t;                     // the tab trigger: a shelf word becomes
    t.lines = {"tick", "rest"};     // the boilerplate, tail riding behind
    t.path = "game.py";
    t.curR = 0;
    t.curC = 4;
    Keys tb;
    tb.tab = true;
    dxn3::ideKey(t, tb);
    ok(t.lines.size() == 3 && t.lines[0] == "def on_tick(dt):" &&
           t.lines[1] == "    pass" && t.lines[2] == "rest",
       "tab on a shelf name expands the snippet in place");
    ok(t.curR == 1 && t.curC == 8, "the cursor rests at the block's end");
    ok(dxn3::ideUndo(t) && t.lines.size() == 2 && t.lines[0] == "tick",
       "the tab trigger is one honest undo step");

    IdeState tl;                    // tail text rides behind the expansion
    tl.lines = {"tick"};
    tl.path = "game.py";
    tl.curR = 0;
    tl.curC = 4;
    Keys tb2;
    tb2.tab = true;
    dxn3::ideKey(tl, tb2);
    ok(tl.lines.size() == 2 && tl.lines[0] == "def on_tick(dt):",
       "the expansion takes the whole line when nothing follows");
    ok(dxn3::ideUndo(tl) && tl.lines[0] == "tick", "and undoes whole");

    IdeState tw;                    // tail text after the trigger word
    tw.lines = {"x tick y"};
    tw.path = "game.py";
    tw.curR = 0;
    tw.curC = 6;                    // right after "tick"
    Keys tb3;
    tb3.tab = true;
    dxn3::ideKey(tw, tb3);
    ok(tw.lines.size() == 2 && tw.lines[0] == "x def on_tick(dt):" &&
           tw.lines[1] == "    pass y",
       "tail text after the trigger rides behind the block");
    ok(tw.curR == 1 && tw.curC == 8,
       "the cursor lands at the block's end, before the tail");

    IdeState tn;                    // a non-shelf word: four honest spaces
    tn.lines = {"hello"};
    tn.curR = 0;
    tn.curC = 5;
    Keys tb4;
    tb4.tab = true;
    dxn3::ideKey(tn, tb4);
    ok(tn.lines[0] == "hello    " && tn.curC == 9,
       "tab on a non-shelf word still gives four honest spaces");
    ok(dxn3::ideUndo(tn) && tn.lines[0] == "hello",
       "and the spaces undo whole");

    IdeState bi;                    // tab with a block: every line indents
    bi.lines = {"one", "two", "three"};
    bi.curR = 0;
    bi.curC = 0;
    bi.anchorR = 1;
    bi.anchorC = 0;                 // lines 1-2 selected
    Keys tb5;
    tb5.tab = true;
    dxn3::ideKey(bi, tb5);
    ok(bi.lines[0] == "    one" && bi.lines[1] == "    two" &&
           bi.lines[2] == "three",
       "tab with a block indents every touched line");
    ok(dxn3::ideSelRange(bi).has_value(),
       "the block selection survives the indent");
    Keys bt;                        // shift+tab walks it back
    bt.backTab = true;
    dxn3::ideKey(bi, bt);
    ok(bi.lines[0] == "one" && bi.lines[1] == "two",
       "shift+tab dedents every touched line");

    IdeState bl;                    // shift+tab alone: this line steps back
    bl.lines = {"    deep"};
    bl.curR = 0;
    bl.curC = 7;
    Keys bt2;
    bt2.backTab = true;
    dxn3::ideKey(bl, bt2);
    ok(bl.lines[0] == "deep" && bl.curC == 3,
       "shift+tab alone lifts the hand's line back a level");
    ok(dxn3::ideUndo(bl) && bl.lines[0] == "    deep",
       "and the dedent undoes whole");
  }

  // 33. the bridge: the clip speaks text, base64 speaks bytes, and an
  // empty paste speaks up instead of pretending
  {
    using dxn3::Keys;
    IdeState s;
    s.lines = {"alpha", "beta"};
    s.curR = 0;
    s.curC = 2;
    Keys cc;
    cc.ctrlC = true;
    dxn3::ideKey(s, cc);
    ok(dxn3::ideClipText(s) == "alpha",
       "a line-wise clip reads as its text");

    IdeState m;
    m.lines = {"one", "two", "three"};
    m.curR = 0;
    m.curC = 0;
    m.anchorR = 1;
    m.anchorC = 3;                  // spanning: "one" + "two"
    Keys cc2;
    cc2.ctrlC = true;
    dxn3::ideKey(m, cc2);
    ok(dxn3::ideClipText(m) == "one\ntwo",
       "a spanning clip joins its lines with newlines");

    ok(dxn3::ideBase64("") == "", "base64 of nothing is nothing");
    ok(dxn3::ideBase64("f") == "Zg==", "base64 pads one byte honestly");
    ok(dxn3::ideBase64("fo") == "Zm8=", "base64 pads two bytes honestly");
    ok(dxn3::ideBase64("foo") == "Zm9v", "base64 encodes a clean triple");
    ok(dxn3::ideBase64("foobar") == "Zm9vYmFy", "base64 chains triples");

    IdeState e;
    e.lines = {"x"};
    e.curR = 0;
    e.curC = 0;
    Keys cv;
    cv.ctrlV = true;
    dxn3::ideKey(e, cv);
    ok(e.lines[0] == "x" && !e.console.empty() &&
           e.console.back().find("clipboard is empty") != std::string::npos,
       "pasting an empty clip speaks up instead of pretending");
  }

  // 34. the minimap: the whole document compressed, honest bar math
  {
    IdeState mm;
    mm.path = "game.py";
    mm.lines = {"top", "", "        deep", "x", "# note", "// not a comment"};
    mm.findHits = {{4, 2}};              // the searchlight stood on row 4
    const dxn3::IdeMini mini = dxn3::ideMiniMap(mm, 6, 10);
    ok(mini.top == 0 && static_cast<int>(mini.rows.size()) == 6,
       "a doc that fits rests at the top, every line a row");
    ok(mini.rows[0].start == 0 && mini.rows[0].len == 2 && !mini.rows[0].blank,
       "'top' compresses to a two-cell bar at the margin");
    ok(mini.rows[1].blank && mini.rows[1].len == 1,
       "a blank line is one dot, anchored");
    ok(mini.rows[2].start == 4 && mini.rows[2].len == 2,
       "eight spaces of indent compress 2:1 into the map");
    ok(mini.rows[4].comment && mini.rows[4].hit,
       "the comment line speaks gray and glows for the searchlight");
    ok(!mini.rows[5].comment,
       "'//' is not this file's comment prefix — python talks with #");
    ok(mini.rows[0].inView && mini.rows[5].inView,
       "when the editor shows everything, the map knows it");

    IdeState big;                        // a doc the map cannot fit at once
    big.lines.clear();                   // the fresh-doc empty line steps aside
    for (int i = 0; i < 100; ++i) big.lines.push_back("line " + std::to_string(i));
    big.curR = 50;
    big.top = 48;                        // the editor's own viewport
    const dxn3::IdeMini slide = dxn3::ideMiniMap(big, 6, 10);
    ok(slide.top == 45 && static_cast<int>(slide.rows.size()) == 10,
       "a long doc slides so the cursor rides the map's middle");
    ok(!slide.rows[0].inView && !slide.rows[2].inView &&
           slide.rows[3].inView && slide.rows[9].inView,
       "the viewport's band lands on exactly the shown rows");
    big.curR = 99;
    ok(dxn3::ideMiniMap(big, 6, 10).top == 90,
       "the map never slides past the document's end");
    big.curR = 0;
    ok(dxn3::ideMiniMap(big, 6, 10).top == 0,
       "nor before its start");
    ok(dxn3::ideMiniMap(mm, 0, 10).rows.empty(),
       "a zero-wide map draws nothing at all");
  }

  // 35. the receipts name WHAT moved, and the word under the hand
  // whispers its snippet
  {
    using dxn3::Keys;
    IdeState t;                          // typing names itself
    t.lines = {"a"};
    t.idle = 1.0;                        // a cold hand: no coalescing
    Keys tk;
    tk.typed = "b";
    dxn3::ideKey(t, tk);
    ok(!t.undo.empty() && t.undo.back().what == "typing",
       "a typed burst is remembered as 'typing'");
    ok(dxn3::ideUndoReceipt(t) == "engine: undo — typing · 1 step left",
       "the undo receipt names the move and the steps left");
    ok(dxn3::ideUndo(t) && t.redo.back().what == "typing",
       "the label rides the redo branch too");
    ok(dxn3::ideRedoReceipt(t) == "engine: redo — typing",
       "the redo receipt speaks the same name");
    ok(dxn3::ideRedo(t) && t.undo.back().what == "typing",
       "and the label comes home through redo");

    IdeState p;                          // paste names itself
    p.lines = {"x"};
    p.clip = {"line"};
    p.clipLines = true;
    Keys pk;
    pk.ctrlV = true;
    dxn3::ideKey(p, pk);
    ok(!p.undo.empty() && p.undo.back().what == "paste",
       "a paste is remembered as 'paste'");

    IdeState c;                          // comment, enter, cut, snippet
    c.lines = {"code"};
    Keys ck;
    ck.comment = true;
    dxn3::ideKey(c, ck);
    ok(!c.undo.empty() && c.undo.back().what == "comment",
       "a comment toggle is remembered as 'comment'");

    IdeState en;
    en.lines = {"ab"};
    en.curC = 1;
    Keys ek;
    ek.enter = true;
    dxn3::ideKey(en, ek);
    ok(!en.undo.empty() && en.undo.back().what == "enter",
       "an enter is remembered as 'enter'");

    IdeState cut;
    cut.lines = {"one", "two"};
    Keys xk;
    xk.ctrlX = true;
    dxn3::ideKey(cut, xk);
    ok(!cut.undo.empty() && cut.undo.back().what == "cut",
       "a bare cut is remembered as 'cut'");

    IdeState sn;
    sn.lines = {"tick"};
    sn.path = "game.py";
    sn.curC = 4;
    Keys sk;
    sk.tab = true;
    dxn3::ideKey(sn, sk);
    ok(!sn.undo.empty() && sn.undo.back().what == "snippet",
       "a tab trigger is remembered as 'snippet'");

    IdeState w;                          // the whisper: the shelf speaks
    w.lines = {"x tick y"};
    w.path = "game.py";
    w.curC = 6;
    ok(dxn3::ideSnippetWhisper(w) == "tab expands 'tick'",
       "a shelf word under the hand names its boilerplate");
    w.curC = 2;                          // behind the hand: 'x ' only
    ok(dxn3::ideSnippetWhisper(w).empty(),
       "no word behind the hand, no whisper");
    w.lines = {"zzz"};
    w.curC = 3;
    ok(dxn3::ideSnippetWhisper(w).empty(),
       "a ghost name never whispers");
  }

  // 36. the pointer: a click lands the hand, shift+click extends,
  // looking around never dirties the doc
  {
    using dxn3::Keys;
    IdeState c1;
    c1.lines = {"first", "second line here", "third"};
    c1.dirty = false;
    Keys ck1;
    ck1.clickR = 1;
    ck1.clickC = 7;                    // the 'l' of 'line'
    dxn3::ideKey(c1, ck1);
    ok(c1.curR == 1 && c1.curC == 7,
       "a click lands the hand on the clicked cell");
    ok(!c1.dirty,
       "looking around never dirties the doc");

    IdeState c2;                       // clicks clamp both ways
    c2.lines = {"tiny"};
    Keys ck2;
    ck2.clickR = 99;
    ck2.clickC = 99;
    dxn3::ideKey(c2, ck2);
    ok(c2.curR == 0 && c2.curC == 4,
       "a wild click clamps to the honest end of the doc");

    IdeState c3;                       // a bare click lets the selection go
    c3.lines = {"one", "two"};
    c3.curR = 0;
    c3.curC = 0;
    c3.anchorR = 1;
    c3.anchorC = 2;
    Keys ck3;
    ck3.clickR = 0;
    ck3.clickC = 1;
    dxn3::ideKey(c3, ck3);
    ok(c3.curR == 0 && c3.curC == 1 && !dxn3::ideSelRange(c3).has_value(),
       "a bare click drops the selection (click to deselect)");

    IdeState c4;                       // shift+click extends, like the arrows
    c4.lines = {"one", "two", "three"};
    c4.curR = 0;
    c4.curC = 0;
    Keys ck4;
    ck4.clickR = 2;
    ck4.clickC = 3;
    ck4.clickShift = true;
    dxn3::ideKey(c4, ck4);
    const auto sel4 = dxn3::ideSelRange(c4);
    ok(sel4 && (*sel4)[0] == 0 && (*sel4)[1] == 0 && (*sel4)[2] == 2 &&
           (*sel4)[3] == 3,
       "shift+click extends the selection from the old hand");

    IdeState c5;                       // no click, no move
    c5.lines = {"stay"};
    c5.curR = 0;
    c5.curC = 2;
    Keys ck5;
    dxn3::ideKey(c5, ck5);
    ok(c5.curR == 0 && c5.curC == 2,
       "a frame without a click leaves the hand alone");
  }

  // 37. the wheel and the nudge: the view slides, the hand rides the
  // edge — the honest pager contract
  {
    IdeState sc;
    sc.lines.clear();                  // the fresh-doc empty line steps aside
    for (int i = 0; i < 100; ++i) sc.lines.push_back("line " + std::to_string(i));
    sc.page = 10;                      // the viewport the draw paints
    sc.dirty = false;                  // the wheel must never flip this
    dxn3::ideScroll(sc, 30);           // a deep wheel down
    ok(sc.top == 30 && sc.curR == 30,
       "a scroll past the hand carries it on the top edge");
    ok(!sc.dirty,
       "the wheel never dirties the doc");
    dxn3::ideScroll(sc, -50);          // and back up past it
    ok(sc.top == 0 && sc.curR == 9,
       "riding home lands the hand on the viewport's bottom edge");
    dxn3::ideScroll(sc, 1000);         // the wheel to the void
    ok(sc.top == 90 && sc.curR == 90,
       "the view clamps at the last full page, the hand with it");
    dxn3::ideScroll(sc, -1000);
    ok(sc.top == 0 && sc.curR == 9,
       "and coming home, the hand rides the bottom edge");
    const int rBefore = sc.curR, tBefore = sc.top;
    dxn3::ideScroll(sc, 0);
    ok(sc.curR == rBefore && sc.top == tBefore,
       "a zero slide is a no-op");

    IdeState mid;                      // a hand mid-view is untouched
    mid.lines.clear();
    for (int i = 0; i < 100; ++i) mid.lines.push_back("line " + std::to_string(i));
    mid.page = 10;
    mid.top = 5;
    mid.curR = 8;
    dxn3::ideScroll(mid, 2);
    ok(mid.top == 7 && mid.curR == 8,
       "a nudge that keeps the hand in view leaves it alone");
  }

  // 38. the drag: press, motion, release — the selection follows the
  // hand while the button is down, and stays when it comes up
  {
    using dxn3::Keys;
    IdeState d1;
    d1.lines = {"alpha", "beta", "gamma"};
    d1.dirty = false;
    Keys pk;                           // the press lands the hand
    pk.clickR = 0;
    pk.clickC = 1;
    dxn3::ideKey(d1, pk);
    ok(d1.curR == 0 && d1.curC == 1 && d1.pressR == 0 && d1.pressC == 1,
       "a press remembers where the button went down");

    Keys dk;                           // motion with the button held
    dk.dragR = 2;
    dk.dragC = 3;
    dxn3::ideKey(d1, dk);
    const auto sel1 = dxn3::ideSelRange(d1);
    ok(sel1 && (*sel1)[0] == 0 && (*sel1)[1] == 1 && (*sel1)[2] == 2 &&
           (*sel1)[3] == 3,
       "a drag selects from the press to the hand");
    ok(d1.curR == 2 && d1.curC == 3 && !d1.dirty,
       "the drag ends at the hand and never dirties the doc");

    Keys rk;                           // the button comes up
    rk.clickRelease = true;
    dxn3::ideKey(d1, rk);
    ok(d1.pressR == -1 && dxn3::ideSelRange(d1).has_value(),
       "a release ends the drag but keeps the selection");

    Keys dk2;                          // motion with the button up: hover
    dk2.dragR = 0;
    dk2.dragC = 0;
    dxn3::ideKey(d1, dk2);
    ok(d1.curR == 2 && d1.curC == 3,
       "hover motion without a press moves nothing");

    IdeState d2;                       // a press followed by release: a
    d2.lines = {"one"};               // plain click never selects
    d2.dirty = false;
    Keys pk2;
    pk2.clickR = 0;
    pk2.clickC = 0;
    dxn3::ideKey(d2, pk2);
    Keys rk2;
    rk2.clickRelease = true;
    dxn3::ideKey(d2, rk2);
    ok(!dxn3::ideSelRange(d2).has_value() && d2.pressR == -1,
       "click-press-release selects nothing (standard)");
  }

  // 39. the ledger: the studio remembers what you had open
  {
    std::vector<std::string> r;
    dxn3::ideRecentPush(r, "a.py");
    dxn3::ideRecentPush(r, "b.js");
    dxn3::ideRecentPush(r, "c.cpp");
    ok(r.size() == 3 && r[0] == "c.cpp" && r[2] == "a.py",
       "the ledger is most-recent-first");
    dxn3::ideRecentPush(r, "a.py");          // seen again: to the front
    ok(r.size() == 3 && r[0] == "a.py" && r[2] == "b.js",
       "a path seen again moves to the front, no duplicate");
    for (int i = 0; i < 15; ++i)
      dxn3::ideRecentPush(r, "file" + std::to_string(i) + ".py");
    ok(r.size() == 12 && r[0] == "file14.py",
       "the ledger keeps twelve names, no more");
    dxn3::ideRecentPush(r, "");              // an empty path is ignored
    ok(r.size() == 12, "an empty path never enters the ledger");

    std::vector<std::string> small{"untitled-flappy.py", "game.js",
                                   "untitled.py"};
    ok(dxn3::ideRecentResolve(small, "game.js") == "game.js",
       "an exact name resolves to itself");
    ok(dxn3::ideRecentResolve(small, "game") == "game.js",
       "a unique basename prefix resolves whole");
    ok(dxn3::ideRecentResolve(small, "untitled") == "",
       "an ambiguous prefix is refused (two untitled files)");
    ok(dxn3::ideRecentResolve(small, "ghost.py") == "ghost.py",
       "a ghost passes through for the honest refusal upstream");
  }

  // 40. the autoscroll: a drag parked at the viewport's edge pulls the
  // view toward the unseen lines — the wheel's ride contract, metered
  {
    IdeState a1;
    a1.lines.clear();
    for (int i = 0; i < 100; ++i) a1.lines.push_back("line " + std::to_string(i));
    a1.page = 10;
    a1.dirty = false;
    a1.pressR = 2;                       // the button is down…
    a1.anchorR = 2;                      // …and a real drag is under way:
    a1.curR = 9;                         // the hand parked on the bottom row
    dxn3::ideDragAutoScroll(a1, 1, 0.08);   // one notch's worth of pull
    ok(a1.top == 1 && a1.curR == 10,
       "a parked hand at the bottom edge pulls the view down one notch");
    ok(!a1.dirty, "the autoscroll never dirties the doc");
    dxn3::ideDragAutoScroll(a1, 1, 0.30);   // ~4 more notches accumulate
    ok(a1.top == 5 && a1.curR == 14,
       "the pull meters evenly, the hand riding the bottom edge");

    IdeState a2;                        // a bare press (no anchor) never scrolls
    a2.lines.clear();
    for (int i = 0; i < 100; ++i) a2.lines.push_back("line " + std::to_string(i));
    a2.page = 10;
    a2.pressR = 0;                      // button down, but…
    a2.curR = 0;
    dxn3::ideDragAutoScroll(a2, 1, 0.50);
    ok(a2.top == 0 && a2.curR == 0 && a2.dragAcc == 0,
       "a stationary press at the edge does not pull the view");

    IdeState a3;                        // the stall law
    a3.lines.clear();
    for (int i = 0; i < 100; ++i) a3.lines.push_back("line " + std::to_string(i));
    a3.page = 10;
    a3.pressR = 2;
    a3.anchorR = 2;
    a3.curR = 9;
    dxn3::ideDragAutoScroll(a3, 1, 0.06);   // an almost-notch: saved up
    ok(a3.top == 0, "less than a notch pulls nothing yet");
    dxn3::ideDragAutoScroll(a3, 1, 2.0);    // the hand was away — a stall
    ok(a3.top == 0 && a3.dragAcc == 0,
       "a long gap resets the meter honestly, no catch-up jump");

    IdeState a4;                        // the ride home, upward
    a4.lines.clear();
    for (int i = 0; i < 100; ++i) a4.lines.push_back("line " + std::to_string(i));
    a4.page = 10;
    a4.pressR = 20;
    a4.anchorR = 20;
    a4.curR = 20;                        // the hand parked on the top row
    a4.top = 20;
    dxn3::ideDragAutoScroll(a4, -1, 0.35);  // ~4 notches up (float-honest)
    ok(a4.top == 16 && a4.curR == 16,
       "a hand parked at the top edge pulls the view up, riding it");

    IdeState a5;                        // the void clamp still holds
    a5.lines.clear();
    for (int i = 0; i < 20; ++i) a5.lines.push_back("line " + std::to_string(i));
    a5.page = 10;
    a5.pressR = 9;
    a5.anchorR = 9;
    a5.curR = 9;                         // parked on the bottom row
    dxn3::ideDragAutoScroll(a5, 1, 0.42);        // six notches in
    dxn3::ideDragAutoScroll(a5, 1, 0.35);        // five more: the void
    ok(a5.top == 10 && a5.curR == 19,
       "the pull clamps at the last full page — the void is honest");

    // the header's honest counter: the selection says how much it holds
    IdeState c1;
    c1.lines = {"alpha", "beta", "gamma"};
    c1.curR = 1;
    c1.curC = 2;
    ok(dxn3::ideSelCount(c1) == 0, "no anchor, no count");
    c1.anchorR = 0;
    c1.anchorC = 2;                     // (0,2) → (1,2): 3 + newline + 2
    ok(dxn3::ideSelCount(c1) == 6,
       "a two-line selection counts its characters and its newline");
    c1.curR = 0;
    c1.curC = 2;                        // an empty range is no selection
    ok(dxn3::ideSelCount(c1) == 0, "an empty range counts nothing");
  }

  // 41. the ledger's whisper: ":recent" completes itself as you type
  {
    const std::vector<std::string> ledger{
        "sdk/examples/shooter.py", "sdk/examples/bounce.js", "untitled.py"};
    using dxn3::ideRecentWhisper;
    ok(ideRecentWhisper(ledger, "bo", 200) == "sdk/examples/bounce.js",
       "a basename prefix whispers the whole path");
    ok(ideRecentWhisper(ledger, "sdk/examples/s", 200) ==
           "sdk/examples/shooter.py",
       "a full-path prefix whispers too");
    ok(ideRecentWhisper(ledger, "", 400) ==
           "sdk/examples/shooter.py \xc2\xb7 sdk/examples/bounce.js "
           "\xc2\xb7 untitled.py",
       "an empty part speaks the whole ledger in order");
    ok(ideRecentWhisper(ledger, "un", 200) == "untitled.py",
       "the ledger's tail whispers like its head");
    ok(ideRecentWhisper(ledger, "zz", 200).empty(),
       "a ghost stays silent — enter will refuse it honestly");
    ok(ideRecentWhisper({}, "", 200) == "(the ledger is empty)",
       "an empty ledger says so instead of nothing");
    ok(ideRecentWhisper(ledger, "", 30) == "sdk/examples/shooter.py",
       "a narrow bar carries one name and stops before the separator");
    ok(ideRecentWhisper(ledger, "s", 20) == "",
       "a name wider than the bar is not whispered at all");
  }

  // 42. the leap: ctrl+\ — the hand jumps to the partner bracket, a
  // look that never edits
  {
    IdeState l1;
    l1.lines = {"bird = circle(\"x\", 6)",
                "hud = label(\"hud\", 2)",
                "tip = label(\"tip\", 4)"};
    l1.curR = 0;
    l1.curC = 13;                      // ON the '(' of circle(
    l1.dirty = false;
    l1.anchorR = 0;                    // a selection rides along — for now
    l1.anchorC = 5;
    ok(dxn3::ideLeapToPartner(l1) && l1.curR == 0 && l1.curC == 20,
       "a leap from an opener lands on its closer");
    ok(l1.anchorR < 0, "the leap lets the selection go");
    ok(!l1.dirty, "the leap never dirties the doc");

    ok(dxn3::ideLeapToPartner(l1) && l1.curR == 0 && l1.curC == 13,
       "a leap from the closer returns to its opener");

    IdeState l2;                       // across lines: the pair spans three
    l2.lines = {"def f():", "    g(", "        pass", "    )", ""};
    l2.curR = 1;
    l2.curC = 5;                       // the g( opener
    ok(dxn3::ideLeapToPartner(l2) && l2.curR == 3 && l2.curC == 4,
       "a leap crosses lines to reach its partner");

    IdeState l3;                       // the cell BEHIND the cursor speaks too
    l3.lines = {"x = (1 + 2)"};
    l3.curR = 0;
    l3.curC = 11;                      // just past the ')' (line end)
    ok(dxn3::ideLeapToPartner(l3) && l3.curC == 4,
       "a leap probes the cell behind the hand");

    IdeState l4;                       // no partner: an honest refusal
    l4.lines = {"broken = (1 + 2"};
    l4.curR = 0;
    l4.curC = 9;                       // on the lonely '('
    const int stayR = l4.curR, stayC = l4.curC;
    ok(!dxn3::ideLeapToPartner(l4) && l4.curR == stayR && l4.curC == stayC,
       "a bracket with no partner refuses the leap, hand unmoved");

    IdeState l5;                       // no bracket at all
    l5.lines = {"plain text only"};
    l5.curR = 0;
    l5.curC = 3;
    ok(!dxn3::ideLeapToPartner(l5) && l5.curC == 3,
       "a hand off any bracket stays put");
  }

  // 43. the gutter earns its width: four columns carry 999 honest
  // line numbers; a bigger document earns its digit, one notch at a
  // time — the ONE rule the draw, the pointer, the ruler and the
  // glows all speak
  {
    using dxn3::ideGutterWidth;
    ok(ideGutterWidth(1) == 4 && ideGutterWidth(999) == 4,
       "a small document keeps the classic four-column gutter");
    ok(ideGutterWidth(1000) == 5, "line 1000 earns the fifth column");
    ok(ideGutterWidth(9999) == 5, "9 999 lines still fit five");
    ok(ideGutterWidth(10000) == 6, "line 10000 earns the sixth");
    ok(ideGutterWidth(0) == 4 && ideGutterWidth(-3) == 4,
       "an empty or negative count stays honest (four)");
    IdeState g1;                       // the pane's code window pays for it
    for (int i = 0; i < 1200; ++i) g1.lines.push_back("x = " + std::to_string(i));
    const int G = dxn3::ideGutterWidth(static_cast<int>(g1.lines.size()));
    const bool split = true;
    const int editW = split ? 46 : 0;
    const int textW = editW - 1 - G;   // no map: code runs to the divider
    ok(G == 5 && textW == 40,
       "a 1000-line doc's pane is one column narrower, honestly");
  }

  // 44. :open learned the ledger: a bare :open reopens the head, and
  // the whisper speaks YOUR files before the filesystem's
  {
    const auto c1 = dxn3::parseCommand(":open");
    ok(c1.ok() && c1.verb == "open" && c1.arg.empty(),
       "a bare :open parses — the argument is optional now");
    const std::vector<std::string> ledger{
        "games/mygame.py", "sdk/examples/bounce.js", "untitled.py"};
    const std::vector<std::string> files{
        "untitled.py", "sdk/examples/flappy.py", "pong.cpp"};
    using dxn3::ideOpenWhisper;
    ok(ideOpenWhisper(ledger, "", files, 400) ==
           "games/mygame.py \xc2\xb7 sdk/examples/bounce.js \xc2\xb7 "
           "untitled.py \xc2\xb7 sdk/examples/flappy.py \xc2\xb7 pong.cpp",
       "the ledger speaks first, the filesystem fills in behind");
    ok(ideOpenWhisper(ledger, "un", files, 400) == "untitled.py",
       "a path both zones speak is never whispered twice");
    ok(ideOpenWhisper(ledger, "my", files, 400) == "games/mygame.py",
       "a ledger-only path (gone from disk) still whispers");
    ok(ideOpenWhisper(ledger, "fl", files, 400) == "sdk/examples/flappy.py",
       "a disk-only file whispers by its basename");
    ok(ideOpenWhisper(ledger, "zz", files, 400).empty(),
       "a ghost stays silent — enter will refuse it honestly");
    ok(ideOpenWhisper(ledger, "", files, 24) == "games/mygame.py",
       "a narrow bar carries the head and stops before the separator");
    ok(ideOpenWhisper({}, "un", files, 400) == "untitled.py",
       "an empty ledger leaves the floor to the filesystem");
  }

  // 45. the second wind: a pull sustained past 1.2s doubles its pace;
  // release, stall, or leaving the edge spends the wind honestly
  {
    IdeState w1;                       // 200 lines, page 10, hand at bottom
    for (int i = 0; i < 200; ++i) w1.lines.push_back("row " + std::to_string(i));
    w1.page = 10;
    w1.pressR = 9;
    w1.anchorR = 9;
    w1.curR = 9;
    for (int f = 0; f < 24; ++f)       // 24 frames of exactly one slow
      dxn3::ideDragAutoScroll(w1, 1, 0.07);   // period: 17 slow notches,
                                             // then hold > 1.2 → double
    ok(w1.top == 31 && w1.curR == 40,
       "a pull sustained past 1.2s earns the second wind (17 + 14 notches)");

    Keys rel;                          // the button comes up: the wind dies
    rel.clickRelease = true;
    dxn3::ideKey(w1, rel);
    ok(w1.dragHold == 0 && w1.dragAcc == 0,
       "a release spends the wind — hold and meter both rest");
    w1.pressR = 40;                    // a NEW press parks at the edge —
    w1.anchorR = 40;                   // the drag's own honest ceremony
    w1.curR = 40;
    for (int f = 0; f < 5; ++f)        // five slow frames, NOT accelerated
      dxn3::ideDragAutoScroll(w1, 1, 0.07);
    ok(w1.top == 36,
       "a fresh pull walks at the slow pace again (5 notches, not 10)");

    IdeState w2;                       // a stalled app is an honest reset
    for (int i = 0; i < 200; ++i) w2.lines.push_back("row " + std::to_string(i));
    w2.page = 10;
    w2.pressR = 9;
    w2.anchorR = 9;
    w2.curR = 9;
    for (int f = 0; f < 20; ++f) dxn3::ideDragAutoScroll(w2, 1, 0.07);
    dxn3::ideDragAutoScroll(w2, 1, 0.6);   // the stall: dt past the guard
    ok(w2.dragHold == 0, "a stalled frame spends the wind too");
    for (int f = 0; f < 17; ++f) dxn3::ideDragAutoScroll(w2, 1, 0.07);
    ok(w2.top == 23 + 17,
       "after a stall the cadence restarts slow (23 + 17, not doubled)");

    IdeState w3;                       // mid-body: no edge, no hold
    for (int i = 0; i < 200; ++i) w3.lines.push_back("row " + std::to_string(i));
    w3.page = 10;
    w3.pressR = 9;
    w3.anchorR = 9;
    w3.curR = 9;
    for (int f = 0; f < 20; ++f) dxn3::ideDragAutoScroll(w3, 1, 0.07);
    dxn3::ideDragAutoScroll(w3, 0, 0.07);  // the hand left the edge
    ok(w3.dragHold == 0, "leaving the edge spends the wind");
  }

  // 46. the sweep: :trim takes every line's trailing air in one honest
  // undo step — and refuses to touch a clean document
  {
    IdeState t1;
    t1.lines = {"x = 1   ", "  ", "", "y = 2\t\t", "z = 3"};
    t1.curR = 0;
    t1.curC = 8;                       // parked past where the line ends
    const int swept = dxn3::ideTrimTrailing(t1);
    ok(swept == 3, "three dirty lines are counted honestly");
    ok(t1.lines[0] == "x = 1" && t1.lines[1] == "" &&
           t1.lines[3] == "y = 2" && t1.lines[4] == "z = 3",
       "tails come off, pure air goes blank, clean lines rest");
    ok(t1.dirty && !t1.undo.empty() && t1.undo.back().what == "trim",
       "the sweep is one restore point, named trim");
    ok(t1.curC == 5, "the cursor clamps to its line's new honest end");

    const int again = dxn3::ideTrimTrailing(t1);
    ok(again == 0 && t1.undo.size() == 1,
       "a clean document refuses the sweep — no phantom restore point");
    ok(dxn3::ideUndo(t1) && t1.lines[0] == "x = 1   " &&
           t1.lines[1] == "  " && t1.lines[3] == "y = 2\t\t",
       "undo puts the air back, exactly as it stood");
  }

  // 47. the honest case: :cases flips the searchlight's sensitivity
  // and the hits re-aim the instant it turns
  {
    IdeState s1;
    s1.lines = {"Hello world", "hello there", "HELLO AGAIN", "hi"};
    s1.curR = 0;
    s1.curC = 0;
    s1.findOpen = true;
    s1.findQ = "hello";
    dxn3::ideFindRefresh(s1);
    ok(s1.findHits.size() == 3,
       "the beginner way: a lowercase query greets every casing");
    ok(s1.findSel == 0 && s1.findHits[0].first == 0,
       "the first hit aims forward from the cursor");
    s1.findCase = true;
    dxn3::ideFindRefresh(s1);
    ok(s1.findHits.size() == 1 && s1.findHits[0].first == 1 &&
           s1.findHits[0].second == 0,
       "case-sensitive: only the honest exact casing answers");
    s1.findCase = false;
    dxn3::ideFindRefresh(s1);
    ok(s1.findHits.size() == 3, "flipping back reopens the wide net");
    s1.findQ = "HELLO";
    dxn3::ideFindRefresh(s1);
    ok(s1.findHits.size() == 3,
       "the forgiving light is deaf to casing in BOTH directions");
  }

  // 48. the ordering: :sort orders the selection's whole lines, one
  // honest undo step, and refuses without a real bed
  {
    IdeState o1;
    o1.lines = {"zebra", "mango", "apple", "kiwi", "end"};
    o1.curR = 1;
    o1.curC = 2;                       // anchor inside the block
    o1.anchorR = 3;
    o1.anchorC = 1;
    const int ordered = dxn3::ideSortSel(o1);
    ok(ordered == 3, "three selected lines are counted");
    ok(o1.lines[0] == "zebra" && o1.lines[1] == "apple" &&
           o1.lines[2] == "kiwi" && o1.lines[3] == "mango" &&
           o1.lines[4] == "end",
       "the selected range orders, the world outside rests");
    ok(o1.curR == 1 && o1.curC == 0,
       "the hand rests at the head of the ordered block");
    ok(!o1.undo.empty() && o1.undo.back().what == "sort" && o1.dirty,
       "the ordering is one restore point, named sort");
    ok(dxn3::ideUndo(o1) && o1.lines[1] == "mango" &&
           o1.lines[3] == "kiwi",
       "undo unorders, exactly as it stood");

    IdeState o2;                       // no selection: an honest refusal
    o2.lines = {"b", "a"};
    o2.curR = 0;
    o2.curC = 0;
    ok(dxn3::ideSortSel(o2) == 0 && o2.lines[0] == "b" &&
           o2.undo.empty(),
       "no selection, no ordering, no phantom step");
    IdeState o3;                       // one line selected: already order
    o3.lines = {"b", "a"};
    o3.curR = 0;
    o3.curC = 0;
    o3.anchorR = 0;
    o3.anchorC = 1;
    ok(dxn3::ideSortSel(o3) == 0 && o3.undo.empty(),
       "a same-line selection is refused too");
  }

  if (fails == 0) {
    std::println("native selftest: all green ({} assertion groups)", n);
    return 0;
  }
  std::println(stderr, "native selftest: {} of {} FAILED", fails, n);
  return 1;
}
