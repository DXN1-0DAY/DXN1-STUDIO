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

  // 4b. the saw (hazard tag) kills too — the levels promise it, the
  // engine delivers it now (a saw that cannot saw lied for six scenes)
  {
    Scene s;
    s.entities.push_back(mk("player", 100, 100, 34, 44));
    Entity& saw = s.entities.emplace_back(mk("deck-guard", 110, 110, 38, 38,
                                             "#fb7185"));
    saw.tag = "hazard";
    Game g(std::move(s));
    g.update(1.f / 60.f, {});
    ok(g.player()->x == g.spawn().x && g.player()->y == g.spawn().y,
       "the saw respawns the player like any fang");
    ok(g.msg.find("saw") != std::string::npos, "the saw speaks its own name");
    // and the saw is harmless while it stands elsewhere
    Scene s2;
    s2.entities.push_back(mk("player", 100, 100, 34, 44));
    Entity& far = s2.entities.emplace_back(mk("saw-far", 600, 500, 38, 38,
                                              "#fb7185"));
    far.tag = "hazard";
    Game g2(std::move(s2));
    g2.update(1.f / 60.f, {});
    ok(g2.msg.find("ouch") == std::string::npos,
       "a saw across the room never bites");
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

  // 9. the version quad rides in the binary too — and the binary's
  // word agrees with the release FILE, read at runtime instead of
  // hardcoded here: a bump can no longer forget to teach this pin
  {
    std::ifstream vf(repoPath("VERSION"));
    std::string rel;
    std::getline(vf, rel);
    while (!rel.empty() && (rel.back() == '\r' || rel.back() == ' '))
      rel.pop_back();
    ok(!rel.empty() && std::string(dxn3::DXN3_VERSION) == rel,
       "native version constant matches the release (" +
           std::string(dxn3::DXN3_VERSION) + ")");
  }

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
    ok(dxn3::parseCommand(":git").ok(), ":git is well-formed bare");
    ok(dxn3::parseCommand(":git log").ok() &&
           dxn3::parseCommand(":git log").num == 3.f,
       ":git log walks three by default");
    ok(dxn3::parseCommand(":git log 5").ok() &&
           dxn3::parseCommand(":git log 5").num == 5.f,
       ":git log 5 walks five");
    ok(!dxn3::parseCommand(":git log banana").ok(),
       ":git log with junk is refused");
    ok(!dxn3::parseCommand(":git log 9").ok(),
       ":git log 9 is refused — the cap is eight");
    ok(!dxn3::parseCommand(":git push").ok(),
       ":git refuses to write — the verb is read-only");
    ok(dxn3::parseCommand(":git branch").ok(),
       ":git branch is well-formed bare");
    ok(!dxn3::parseCommand(":git branch x").ok(),
       ":git branch takes no argument");
    ok(dxn3::parseCommand(":git tag").ok(), ":git tag is well-formed bare");
    ok(!dxn3::parseCommand(":git tag v9").ok(),
       ":git tag takes no argument");
    ok(dxn3::usageHintFor(":git").find("branch") != std::string::npos,
       "the git whisper names what it speaks");
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

  // 49. the fresh slate: ctrl+l wipes the console's noise without
  // dirtying the document
  {
    IdeState f1;
    f1.lines = {"x = 1"};
    f1.console = {"game: tick", "engine: hosting python3", "game: tick"};
    f1.dirty = false;
    Keys cl;
    cl.ctrlL = true;
    dxn3::ideKey(f1, cl);
    ok(f1.console.size() == 1 &&
           f1.console[0].find("the console is fresh") != std::string::npos,
       "the slate is wiped, and the fresh console says so");
    ok(!f1.dirty && f1.undo.empty(),
       "the wipe never dirties the doc, never takes an undo step");
    ok(f1.lines[0] == "x = 1", "the document never hears about it");

    Keys cl2;                          // a second wipe stays honest
    cl2.ctrlL = true;
    dxn3::ideKey(f1, cl2);
    ok(f1.console.size() == 1,
       "clearing a fresh console stays one honest line");
  }

  // 50. the pins: bookmarks you plant so the hand can leap back — a
  // look, never an edit: nothing dirties, nothing undoes, and the pins
  // FOLLOW the document (inserts slide them, cuts take them along)
  {
    IdeState p1;
    p1.lines = {"a", "b", "c", "d", "e"};
    ok(dxn3::ideMarkToggle(p1, 3), "a pin plants");
    ok(dxn3::ideMarkHas(p1, 3) && !dxn3::ideMarkHas(p1, 0),
       "has() speaks the truth");
    ok(!dxn3::ideMarkToggle(p1, 3) && !dxn3::ideMarkHas(p1, 3),
       "a second toggle pulls the pin back out");
    dxn3::ideMarkToggle(p1, 2);        // out of order on purpose: the
    dxn3::ideMarkToggle(p1, 0);        // ledger must stay sorted+unique
    dxn3::ideMarkToggle(p1, 4);
    ok(p1.marks.size() == 3 && p1.marks[0] == 0 && p1.marks[1] == 2 &&
           p1.marks[2] == 4,
       "out-of-order planting keeps the ledger sorted and deduped");
    ok(dxn3::ideMarkNext(p1, 0) == 2, "next finds the pin ahead");
    ok(dxn3::ideMarkNext(p1, 4) == 0, "next wraps past the last pin");
    ok(dxn3::ideMarkPrev(p1, 1) == 0, "prev finds the pin behind");
    ok(dxn3::ideMarkPrev(p1, 0) == 4, "prev wraps before the first pin");
    IdeState p2;                       // pinless: honest refusals
    p2.lines = {"solo"};
    ok(dxn3::ideMarkNext(p2, 0) == -1 && dxn3::ideMarkPrev(p2, 0) == -1,
       "a pinless file refuses to leap");

    IdeState p3;                       // the pins follow the document
    p3.lines = {"a", "b", "c", "d", "e"};
    dxn3::ideMarkToggle(p3, 1);
    dxn3::ideMarkToggle(p3, 3);
    dxn3::ideMarkShift(p3, 2, 2);      // two lines land at row 2
    ok(p3.marks == std::vector<int>({1, 5}),
       "pins beneath an insert slide down with the lines");
    dxn3::ideMarkErase(p3, 0, 1);      // row 0 leaves
    ok(p3.marks == std::vector<int>({0, 4}),
       "pins above a cut slide up");
    dxn3::ideMarkErase(p3, 3, 2);      // rows 3-4 leave — pin 4 inside
    ok(p3.marks == std::vector<int>({0}),
       "a pin inside the cut dies with its line");
    dxn3::ideMarkClamp(p3);            // nothing out of range here: no-op
    ok(p3.marks == std::vector<int>({0}), "the clamp prunes only the stale");
    p3.marks.push_back(99);            // a ghost from a shrunken document
    dxn3::ideMarkClamp(p3);
    ok(p3.marks == std::vector<int>({0}),
       "the clamp prunes the ghosts undo left behind");
    dxn3::ideMarkClear(p3);
    ok(p3.marks.empty(), "the clear wipes the ledger");

    IdeState p4;                       // the keyboard: F2 leaps, ctrl+F2 pulls
    p4.lines = {"one", "two", "three"};
    dxn3::ideMarkToggle(p4, 2);
    p4.curR = 0;
    p4.dirty = false;
    Keys f2;
    f2.markNext = true;
    dxn3::ideKey(p4, f2);
    ok(p4.curR == 2 && p4.curC == 0 && !p4.dirty && p4.undo.empty(),
       "F2 leaps the hand to the pin — a look, never an edit");
    ok(!p4.console.empty() &&
           p4.console.back().find("pin at line 3") != std::string::npos,
       "the leap speaks its landing");
    Keys f2t;                          // ctrl+F2 pulls the pin it stands on
    f2t.markToggle = true;
    dxn3::ideKey(p4, f2t);
    ok(!dxn3::ideMarkHas(p4, 2) && !p4.dirty,
       "ctrl+F2 pulls the pin, still never an edit");
    Keys f2e;                          // pinless leap says so
    f2e.markNext = true;
    dxn3::ideKey(p4, f2e);
    ok(p4.curR == 2 &&
           p4.console.back().find("no pins yet") != std::string::npos,
       "a pinless leap refuses with the way out");

    IdeState p5;                       // shift+F2 walks back
    p5.lines = {"one", "two", "three", "four"};
    dxn3::ideMarkToggle(p5, 0);
    dxn3::ideMarkToggle(p5, 2);
    p5.curR = 3;
    Keys f2s;
    f2s.markPrev = true;
    dxn3::ideKey(p5, f2s);
    ok(p5.curR == 2, "shift+F2 walks back to the pin above");
  }

  // 51. the quiet: :zen — the console rail hides, the body breathes.
  // The flag is honest furniture: the geometry it moves is the draw's
  // and the pointer's law (the smoke walks that), the grammar is here.
  {
    IdeState z0;                       // the studio boots loud
    ok(!z0.zen, "zen defaults off — the rail is up on boot");
    ok(!z0.minimap == false, "zen touches nothing else's defaults");

    const auto z1 = dxn3::parseCommand(":zen");
    ok(z1.ok() && z1.verb == "zen",
       "parseCommand reads :zen — the quiet is a verb");
    const auto z2 = dxn3::parseCommand(":zen please");
    ok(!z2.ok() && z2.error.find("takes no argument") != std::string::npos,
       ":zen with an argument is refused — the quiet takes none");
    ok(dxn3::usageHintFor(":zen").find("zen") != std::string::npos &&
           dxn3::usageHintFor(":zen").find("zen wakes it") != std::string::npos,
       "the bar whispers the way back: :zen wakes it");
    ok(dxn3::usageHintFor(":zen").find("rail") != std::string::npos,
       "the hint names what rests — the rail");
  }

  // 52. the ordering, descending: :rsort is the sort's mirror - the
  // same bed, the same refusals, the lines land Z before A
  {
    IdeState r1s;
    r1s.lines = {"zebra", "mango", "apple", "kiwi", "end"};
    r1s.curR = 1;
    r1s.curC = 2;                      // anchor inside the block
    r1s.anchorR = 3;
    r1s.anchorC = 1;
    const int ordered = dxn3::ideRsortSel(r1s);
    ok(ordered == 3, "rsort counts the selected lines too");
    ok(r1s.lines[0] == "zebra" && r1s.lines[1] == "mango" &&
           r1s.lines[2] == "kiwi" && r1s.lines[3] == "apple" &&
           r1s.lines[4] == "end",
       "the selected range lands Z before A, the world outside rests");
    ok(r1s.curR == 1 && r1s.curC == 0,
       "the hand rests at the head of the rsorted block");
    ok(!r1s.undo.empty() && r1s.undo.back().what == "rsort" && r1s.dirty,
       "the descending order is one restore point, named rsort");
    ok(dxn3::ideUndo(r1s) && r1s.lines[1] == "mango" &&
           r1s.lines[3] == "kiwi",
       "undo unorders the rsort, exactly as it stood");
    ok(!dxn3::ideSelRange(r1s),
       "the selection lets go when the lines land");

    const auto rc = dxn3::parseCommand(":rsort");
    ok(rc.ok() && rc.verb == "rsort",
       "parseCommand reads :rsort - the mirror is a verb");
    ok(!dxn3::parseCommand(":rsort now").ok(),
       ":rsort with an argument is refused - the bed is the selection");
    ok(dxn3::usageHintFor(":rsort").find("Z before A") != std::string::npos,
       "the bar whispers the descending law");
  }

  // 54. the case: :lower/:upper/:title change the selection's voice -
  // one restore point per verb, no phantom step on nothing-to-change,
  // the hand at the selection's head, the selection let go
  {
    IdeState c1;
    c1.lines = {"from dxn3 import *", "SCORE = 0"};
    c1.curR = 0;
    c1.curC = 5;
    c1.anchorR = 0;
    c1.anchorC = 9;                    // "dxn3" is the bed
    ok(dxn3::ideCaseSel(c1, 1) == 3, "three letters shout (the 3 stays)");
    ok(c1.lines[0] == "from DXN3 import *",
       "the selection shouts, the world outside rests");
    ok(!c1.undo.empty() && c1.undo.back().what == "upper" && c1.dirty,
       "the shout is one restore point, named upper");
    ok(dxn3::ideUndo(c1) && c1.lines[0] == "from dxn3 import *",
       "undo quiets the shout, exactly as it stood");

    IdeState c2;
    c2.lines = {"HELLO", "WORLD"};
    c2.curR = 0;
    c2.curC = 1;                       // anchor inside HELLO, cursor at
    c2.anchorR = 1;                    // W's second letter of WORLD:
    c2.anchorC = 2;                    // a two-line bed
    ok(dxn3::ideCaseSel(c2, 0) == 6,
       "a selection across lines counts every letter it moves");
    ok(c2.lines[0] == "Hello" && c2.lines[1] == "woRLD",
       "only the range's letters whisper; the edges hold");
    ok(c2.curR == 0 && c2.curC == 1,
       "the hand rests at the selection's head");
    ok(!dxn3::ideSelRange(c2),
       "the selection lets go when the letters land");

    IdeState c3;
    c3.lines = {"hello world foo_bar 9lives"};
    c3.curR = 0;
    c3.curC = 0;
    c3.anchorR = 0;
    c3.anchorC = static_cast<int>(c3.lines[0].size());
    ok(dxn3::ideCaseSel(c3, 2) == 5,
       "title stands five word-starts up (underscore and 9 start words)");
    ok(c3.lines[0] == "Hello World Foo_Bar 9Lives",
       "title's law: first letters stand, the rest quiet down");

    IdeState c4;                       // nothing to change: no phantom
    c4.lines = {"1234"};
    c4.curR = 0;
    c4.curC = 0;
    c4.anchorR = 0;
    c4.anchorC = 4;
    ok(dxn3::ideCaseSel(c4, 1) == 0 && c4.undo.empty(),
       "a letterless selection takes no phantom step");

    IdeState c5;                       // no selection at all
    c5.lines = {"quiet"};
    c5.curR = 0;
    c5.curC = 0;
    ok(dxn3::ideCaseSel(c5, 0) == 0 && c5.undo.empty(),
       "no selection, no voice, no phantom step");

    const auto cu = dxn3::parseCommand(":upper");
    const auto cl = dxn3::parseCommand(":lower");
    const auto ct = dxn3::parseCommand(":title");
    ok(cu.ok() && cl.ok() && ct.ok() && cu.verb == "upper" &&
           cl.verb == "lower" && ct.verb == "title",
       "the three voices are verbs");
    ok(!dxn3::parseCommand(":upper now").ok(),
       ":upper with an argument is refused - the bed is the selection");
    ok(dxn3::usageHintFor(":title").find("word") != std::string::npos,
       "the bar whispers the title law");
  }

  // 55. the collapse: :uniq - lines that repeat back-to-back say it
  // once; no selection means the whole document; the pins follow the
  // lines down; a clean bed takes no phantom step
  {
    IdeState u1;                       // whole-document law (no selection)
    u1.lines = {"a", "a", "a", "b", "a", "b", "b", "c"};
    const int gone = dxn3::ideUniqSel(u1);
    ok(gone == 3, "three duplicates fall (aaa, bb - but aba stays)");
    ok(u1.lines == std::vector<std::string>({"a", "b", "a", "b", "c"}),
       "only BACK-TO-BACK repeats collapse; interleaved lines rest");
    ok(!u1.undo.empty() && u1.undo.back().what == "uniq" && u1.dirty,
       "the collapse is one restore point, named uniq");
    ok(dxn3::ideUndo(u1) &&
           u1.lines == std::vector<std::string>(
                           {"a", "a", "a", "b", "a", "b", "b", "c"}),
       "undo restores every fallen line");

    IdeState u2;                       // a selection is the bed
    u2.lines = {"x", "dup", "dup", "dup", "y"};
    u2.curR = 1;
    u2.curC = 0;
    u2.anchorR = 3;
    u2.anchorC = 2;
    ok(dxn3::ideUniqSel(u2) == 2 && u2.lines[2] == "y" &&
           u2.lines[0] == "x",
       "the world outside the selection never collapses");
    ok(u2.curR == 2,
       "the hand rests where the first line fell");

    IdeState u3;                       // the pins follow the lines down
    u3.lines = {"a", "b", "b", "c", "d", "e"};
    dxn3::ideMarkToggle(u3, 4);        // a pin on "e" (line 4)
    dxn3::ideMarkToggle(u3, 2);        // a pin inside the collapse
    u3.curR = 0;
    ok(dxn3::ideUniqSel(u3) == 1 &&
           u3.lines == std::vector<std::string>({"a", "b", "c", "d", "e"}),
       "one b falls");
    ok(u3.marks == std::vector<int>({3}),
       "the pin inside the collapse dies, the pin beneath slides up");

    IdeState u4;                       // nothing back-to-back
    u4.lines = {"a", "b", "a"};
    u4.curR = 0;
    ok(dxn3::ideUniqSel(u4) == 0 && u4.undo.empty(),
       "a clean bed takes no phantom step");

    IdeState u5;                       // one line cannot repeat itself
    u5.lines = {"solo"};
    u5.curR = 0;
    u5.anchorR = 0;
    u5.anchorC = 3;
    ok(dxn3::ideUniqSel(u5) == 0 && u5.undo.empty(),
       "a single line is refused too");

    const auto uq = dxn3::parseCommand(":uniq");
    ok(uq.ok() && uq.verb == "uniq",
       "parseCommand reads :uniq - the collapse is a verb");
    ok(!dxn3::parseCommand(":uniq now").ok(),
       ":uniq with an argument is refused - the bed is the document");
    ok(dxn3::usageHintFor(":uniq").find("back-to-back") != std::string::npos,
       "the bar whispers the collapse law");
  }

  // 56. the flip: :rev reorders without judging - the bed's first
  // line lands last, the pins ride to their mirrors, and the ledger
  // is re-sorted (a flip is the one move that can unsort it)
  {
    IdeState f1;
    f1.lines = {"one", "two", "three", "four", "end"};
    dxn3::ideMarkToggle(f1, 1);        // a pin on "two"
    dxn3::ideMarkToggle(f1, 3);        // a pin on "four"
    f1.curR = 0;
    f1.curC = 1;
    f1.anchorR = 3;
    f1.anchorC = 0;
    ok(dxn3::ideRevSel(f1) == 4, "four lines flip");
    ok(f1.lines == std::vector<std::string>(
                        {"four", "three", "two", "one", "end"}),
       "the bed walks end for end, the world outside rests");
    ok(f1.marks == std::vector<int>({0, 2}),
       "the pins ride the flip to their mirrors - sorted, unique");
    ok(f1.lines[1] == "three" && f1.lines[3] == "one" &&
           !f1.marks.empty(),
       "each pin still points at its own line's content");
    ok(!f1.undo.empty() && f1.undo.back().what == "rev" && f1.dirty,
       "the flip is one restore point, named rev");
    ok(f1.curR == 0 && f1.curC == 0 && !dxn3::ideSelRange(f1),
       "the hand rests at the block's head, the selection let go");
    ok(dxn3::ideUndo(f1) && f1.lines[0] == "one" && f1.lines[3] == "four",
       "undo walks the bed back - and lands the hand where it stood");

    IdeState f2;                       // refusals, the family's law
    f2.lines = {"a", "b"};
    f2.curR = 0;
    f2.curC = 0;
    ok(dxn3::ideRevSel(f2) == 0 && f2.undo.empty(),
       "no selection, no flip, no phantom step");
    f2.anchorR = 0;
    f2.anchorC = 1;
    ok(dxn3::ideRevSel(f2) == 0 && f2.undo.empty(),
       "a same-line bed has nothing to flip");

    const auto rv = dxn3::parseCommand(":rev");
    ok(rv.ok() && rv.verb == "rev",
       "parseCommand reads :rev - the flip is a verb");
    ok(dxn3::usageHintFor(":rev").find("flip") != std::string::npos,
       "the bar whispers the flip law");
  }




  // 57. the breath: ":indent"/":dedent" — the selection's lines step
  // right, or back, one level at a time; pure air keeps its silence,
  // a bed with no work takes no phantom step, the pins hold their
  // lines, the hand rests at the bed's head riding the shift
  {
    IdeState b1;
    b1.lines = {"def f():", "", "    return 1", "return 2"};
    b1.anchorR = 0;
    b1.anchorC = 0;
    b1.curR = 3;
    b1.curC = 5;                     // a four-line bed, hand mid-text
    ok(dxn3::ideDentSel(b1, false) == 3,
       "three live lines breathe - pure air is never counted");
    ok(b1.lines[0] == "    def f():",
       "the head takes four honest spaces");
    ok(b1.lines[1].empty(), "a line of pure air keeps its silence");
    ok(b1.lines[2] == "        return 1",
       "the nested line breathes a level too");
    ok(b1.anchorR < 0, "the selection lets go");
    ok(b1.curR == 0 && b1.curC == 4,
       "the hand rests at the bed's head, riding the shift");
    ok(!b1.undo.empty() && b1.undo.back().what == "indent",
       "one honest restore point named indent");
    ok(dxn3::ideUndo(b1) && b1.lines[0] == "def f():" &&
       b1.lines[1].empty() && b1.lines[3] == "return 2",
       "undo breathes the bed back out");
    ok(b1.curR == 3 && b1.curC == 5,
       "undo lands the hand where it stood");

    IdeState b2;                     // the breath's mirror: :dedent
    b2.lines = {"        deep()", "    mid()", "shallow", ""};
    b2.anchorR = 0;
    b2.anchorC = 0;
    b2.curR = 3;
    b2.curC = 0;
    ok(dxn3::ideDentSel(b2, true) == 2,
       "two lines step back - the shallow and the air give nothing");
    ok(b2.lines[0] == "    deep()" && b2.lines[1] == "mid()",
       "each line gives up to four spaces, never more");
    ok(b2.curC == 0,
       "the hand rides the head's cut, clamped honest");
    ok(!b2.undo.empty() && b2.undo.back().what == "dedent",
       "one honest restore point named dedent");

    IdeState b3;                     // refusals, the family's law
    b3.lines = {"    a", "b"};
    b3.curR = 0;
    b3.curC = 0;
    ok(dxn3::ideDentSel(b3, false) == 0 && b3.undo.empty(),
       "no selection, no breath, no phantom step");
    b3.anchorR = 0;
    b3.anchorC = 2;                  // a same-line bed counts
    b3.curR = 0;
    b3.curC = 5;
    ok(dxn3::ideDentSel(b3, false) == 1 && b3.lines[0] == "        a",
       "one line is a fine bed for a breath");
    IdeState b4;
    b4.lines = {"a", "\tb"};
    b4.anchorR = 0;
    b4.anchorC = 0;
    b4.curR = 1;
    b4.curC = 2;
    ok(dxn3::ideDentSel(b4, true) == 0 && b4.undo.empty(),
       "no leading air, nothing to give - no phantom step");

    IdeState b5;                     // the pins hold their lines
    b5.lines = {"one", "two", "three"};
    dxn3::ideMarkToggle(b5, 1);
    b5.anchorR = 0;
    b5.anchorC = 0;
    b5.curR = 2;
    b5.curC = 1;
    ok(dxn3::ideDentSel(b5, false) == 3 &&
       b5.marks.size() == 1 && b5.marks[0] == 1,
       "a breath moves no line - the pin holds");

    const auto bi = dxn3::parseCommand(":indent");
    const auto bd = dxn3::parseCommand(":dedent");
    ok(bi.ok() && bi.verb == "indent" && bd.ok() && bd.verb == "dedent",
       "parseCommand reads the breath pair");
    ok(dxn3::usageHintFor(":indent").find("step right") != std::string::npos &&
       dxn3::usageHintFor(":dedent").find("back") != std::string::npos,
       "the bar whispers the breath's law");
  }

  // 58. the shelf speaks: ":snip " whispers every name with its
  // one-line description, the typed prefix narrows by NAME, the
  // clipping law ends the line before a cut word, an unknown name
  // describes nothing, and the shelf is the file's own dialect
  {
    using std::string;
    ok(dxn3::ideSnippetDescribe("tick") == "the every-frame hook" &&
           dxn3::ideSnippetDescribe("main") == "a whole playable scene",
       "the shelf's words: tick is the every-frame hook");
    ok(dxn3::ideSnippetDescribe("nope").empty(),
       "an unknown name describes nothing");

    const string full = dxn3::ideSnippetShelfWhisper("game.py", "", 400);
    ok(full.rfind("fn — a named function · tick — the every-frame hook",
                  0) == 0,
       "a bare :snip whispers the shelf, name then description");
    ok(full.find("main — a whole playable scene") != string::npos,
       "the shelf's last word is the whole playable scene");

    const string narrow = dxn3::ideSnippetShelfWhisper("game.py", "ke", 400);
    ok(narrow == "key — the keypress hook",
       "a typed prefix narrows by NAME, description riding along");

    const size_t one = string("fn — a named function").size();
    ok(dxn3::ideSnippetShelfWhisper("game.py", "", one) ==
           "fn — a named function",
       "an entry that exactly fits still speaks");
    ok(dxn3::ideSnippetShelfWhisper("game.py", "", one - 1).empty(),
       "a bar too narrow for even one entry holds its tongue");
    const size_t two = one + 3 +
                       string("tick — the every-frame hook").size();
    ok(dxn3::ideSnippetShelfWhisper("game.py", "", two) ==
           "fn — a named function · tick — the every-frame hook",
       "two entries fit when the bar honestly holds both");
    ok(dxn3::ideSnippetShelfWhisper("game.py", "", two - 1) ==
           "fn — a named function",
       "the first entry that does not fit ends the line - whole words only");

    ok(dxn3::ideSnippetShelfWhisper("game.cpp", "", 400)
               .find("class") == string::npos &&
           dxn3::ideSnippetShelfWhisper("game.cpp", "", 400)
               .find("fn — a named function") == 0,
       "the shelf is the file's own dialect - cpp speaks five");
  }

  // 59. the ride: ":lift"/":drop" — the selection's lines step one
  // line up or down, the pins riding their lines, the displaced
  // neighbor's pin landing where the neighbor went, the hand riding
  // the block's head, a bed pressed against the edge refused
  {
    IdeState m1;
    m1.lines = {"a", "b", "c", "d"};
    m1.curR = 2;
    m1.curC = 0;                     // the hand's line: "c"
    ok(dxn3::ideMoveSel(m1, false) == 1,
       "the hand's line lifts, a one-line bed with no selection");
    ok(m1.lines[1] == "c" && m1.lines[2] == "b",
       "the line slides up, the neighbor walks around it");
    ok(m1.curR == 1 && m1.curC == 0, "the hand rides its line");
    ok(!m1.undo.empty() && m1.undo.back().what == "lift",
       "one honest restore point named lift");

    IdeState m2;                     // a block lift with pins aboard
    m2.lines = {"a", "b", "c", "d"};
    dxn3::ideMarkToggle(m2, 0);      // a pin on the displaced neighbor
    dxn3::ideMarkToggle(m2, 2);      // a pin inside the bed
    m2.anchorR = 1;
    m2.anchorC = 0;
    m2.curR = 2;
    m2.curC = 1;
    ok(dxn3::ideMoveSel(m2, false) == 2, "the block lifts as one");
    ok(m2.lines == std::vector<std::string>({"b", "c", "a", "d"}),
       "the neighbor lands at the block's tail");
    ok(m2.marks == std::vector<int>({1, 2}),
       "the pins ride - and the ledger stays sorted");
    ok(m2.curR == 0 && !dxn3::ideSelRange(m2),
       "the hand rides the block's head, the selection let go");
    ok(dxn3::ideUndo(m2) && m2.lines[0] == "a" && m2.marks[0] == 0 &&
       m2.curR == 2,
       "undo walks the ride back, hand and pins where they stood");

    IdeState m3;                     // the edge refuses, honestly
    m3.lines = {"a", "b"};
    m3.curR = 0;
    m3.curC = 0;
    ok(dxn3::ideMoveSel(m3, false) == 0 && m3.undo.empty(),
       "nothing above to lift into - no phantom step");
    m3.curR = 1;
    ok(dxn3::ideMoveSel(m3, true) == 0 && m3.undo.empty(),
       "nothing below to drop into - no phantom step");

    IdeState m4;                     // the drop, and its pin law
    m4.lines = {"a", "b", "c"};
    dxn3::ideMarkToggle(m4, 1);
    m4.curR = 1;
    m4.curC = 0;
    ok(dxn3::ideMoveSel(m4, true) == 1, "the hand's line drops");
    ok(m4.lines[1] == "c" && m4.lines[2] == "b",
       "the neighbor below slides up to fill the gap");
    ok(m4.marks == std::vector<int>({2}), "the pin rides down");
    ok(!m4.undo.empty() && m4.undo.back().what == "drop",
       "one honest restore point named drop");

    const auto pl = dxn3::parseCommand(":lift");
    const auto pd = dxn3::parseCommand(":drop");
    ok(pl.ok() && pl.verb == "lift" && pd.ok() && pd.verb == "drop",
       "parseCommand reads the ride pair");
    ok(dxn3::usageHintFor(":lift").find("up") != std::string::npos &&
       dxn3::usageHintFor(":drop").find("down") != std::string::npos,
       "the bar whispers the ride's law");
  }

  // 60. the echo: ":dup" — the selection's lines say it twice, the
  // copies sitting below, the originals keeping their pins, the world
  // beneath sliding down, the hand landing on the copy's head
  {
    IdeState e1;
    e1.lines = {"a", "b", "c"};
    dxn3::ideMarkToggle(e1, 1);      // a pin inside the bed
    dxn3::ideMarkToggle(e1, 2);      // a pin beneath the bed
    e1.curR = 1;
    e1.curC = 0;                     // the hand's line: "b"
    ok(dxn3::ideDupSel(e1) == 1,
       "the hand's line echoes, a one-line bed with no selection");
    ok(e1.lines == std::vector<std::string>({"a", "b", "b", "c"}),
       "the copy sits directly below the original");
    ok(e1.marks == std::vector<int>({1, 3}),
       "the original keeps its pin, the world beneath slides down");
    ok(e1.curR == 2, "the hand lands on the copy's head");
    ok(!e1.undo.empty() && e1.undo.back().what == "dup",
       "one honest restore point named dup");
    ok(dxn3::ideUndo(e1) && e1.lines.size() == 3 &&
       e1.marks == std::vector<int>({1, 2}) && e1.curR == 1,
       "undo folds the echo away, pins and hand walking back");

    IdeState e2;                     // a block echo
    e2.lines = {"a", "b", "c", "d"};
    e2.anchorR = 1;
    e2.anchorC = 0;
    e2.curR = 2;
    e2.curC = 1;
    ok(dxn3::ideDupSel(e2) == 2, "the block echoes as one");
    ok(e2.lines == std::vector<std::string>(
                       {"a", "b", "c", "b", "c", "d"}),
       "the copies land in order beneath the bed");
    ok(e2.curR == 3 && !dxn3::ideSelRange(e2),
       "the hand rides the copy's head, the selection let go");

    const auto du = dxn3::parseCommand(":dup");
    ok(du.ok() && du.verb == "dup" &&
       dxn3::parseCommand(":dup now").error.find("takes no argument") !=
           std::string::npos,
       "parseCommand reads :dup and refuses it an argument");
    ok(dxn3::usageHintFor(":dup").find("copies") != std::string::npos,
       "the bar whispers the echo's law");
  }

  // 61. the fold: ":join" — the bed's lines say it once in one
  // breath, vim's J law for the hand's line, the seam for the hand,
  // the uniq's pin law for the folded lines, the edges refusing
  {
    IdeState j1;
    j1.lines = {"a", "b", "c"};
    dxn3::ideMarkToggle(j1, 1);      // a pin on a folded line: dies
    dxn3::ideMarkToggle(j1, 2);      // a pin beneath the bed: slides up
    j1.curR = 1;
    j1.curC = 0;                     // the hand's line "b" folds with "c"
    ok(dxn3::ideJoinSel(j1) == 2,
       "the hand's line folds with the one below, a two-line breath");
    ok(j1.lines == std::vector<std::string>({"a", "b c"}),
       "the fold speaks one space between the pieces");
    ok(j1.marks == std::vector<int>({1}),
       "a folded line's pin dies, the world beneath slides up");
    ok(j1.curR == 1 && j1.curC == 2,
       "the hand rests at the seam, where the first fold landed");
    ok(!j1.undo.empty() && j1.undo.back().what == "join",
       "one honest restore point named join");
    ok(dxn3::ideUndo(j1) && j1.lines.size() == 3 &&
       j1.marks == std::vector<int>({1, 2}),
       "undo unfolds the breath, the pins walking back");

    IdeState j2;                     // pure air contributes nothing
    j2.lines = {"x", "", "  y  "};
    j2.anchorR = 0;
    j2.anchorC = 0;
    j2.curR = 2;
    j2.curC = 1;
    ok(dxn3::ideJoinSel(j2) == 3, "the whole bed folds, air and all");
    ok(j2.lines == std::vector<std::string>({"x y"}),
       "pure air stays air, the pieces trimmed to their words");
    ok(j2.curC == 2, "the seam rides past the space");

    IdeState j3;                     // the edges refuse, honestly
    j3.lines = {"a", "b"};
    j3.curR = 1;
    j3.curC = 0;
    ok(dxn3::ideJoinSel(j3) == 0 && j3.undo.empty(),
       "nothing below to fold into - no phantom step");
    j3.curR = 0;
    j3.anchorR = 0;
    j3.anchorC = 0;
    j3.curC = 1;
    ok(dxn3::ideJoinSel(j3) == 0 && j3.undo.empty(),
       "a same-line bed folds nothing");

    const auto jo = dxn3::parseCommand(":join");
    ok(jo.ok() && jo.verb == "join" &&
       dxn3::parseCommand(":join up").error.find("takes no argument") !=
           std::string::npos,
       "parseCommand reads :join and refuses it an argument");
    ok(dxn3::usageHintFor(":join").find("fold") != std::string::npos,
       "the bar whispers the fold's law");
  }

  // 62. the jump: ":goto +N/-N" — the numbers ride from the hand, the
  // absolute form stays 1-based, both clamp to the document, zero and
  // garbage are refused
  {
    const auto g1 = dxn3::parseCommand(":goto +5");
    ok(g1.ok() && g1.rel && g1.num == 5.f,
       ":+5 rides down, and says so");
    const auto g2 = dxn3::parseCommand(":goto -3");
    ok(g2.ok() && g2.rel && g2.num == -3.f,
       ":-3 rides up, and says so");
    const auto g3 = dxn3::parseCommand(":goto 42");
    ok(g3.ok() && !g3.rel && g3.num == 42.f,
       "a bare number stays the absolute line");
    ok(!dxn3::parseCommand(":goto +0").ok() &&
       !dxn3::parseCommand(":goto -").ok() &&
       !dxn3::parseCommand(":goto +x").ok(),
       "zero rides nothing, and garbage is refused");

    IdeState s1;
    s1.lines = {"1", "2", "3", "4", "5"};
    s1.curR = 1;
    ok(dxn3::ideGotoTarget(s1, 5.f, false) == 4,
       "the absolute form is 1-based: line 5 is the doc's tail");
    ok(dxn3::ideGotoTarget(s1, 3.f, true) == 4,
       "+3 from the hand rides three lines down");
    ok(dxn3::ideGotoTarget(s1, -99.f, true) == 0,
       "a ride past the top clamps to the first line");
    ok(dxn3::ideGotoTarget(s1, 99.f, true) == 4 &&
       dxn3::ideGotoTarget(s1, 99.f, false) == 4,
       "a ride past the bottom clamps to the last line");

    ok(dxn3::usageHintFor(":goto").find("+N") != std::string::npos,
       "the bar whispers the ride's form");
  }

  // 53. the pins whisper: ":bm" completes itself as you type - the
  // ledger speaks "N) Ln L", the typed number narrows the choir, the
  // bar's width ends the line, an empty ledger stays silent
  {
    IdeState w1;
    w1.lines = {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"};
    dxn3::ideMarkToggle(w1, 3);        // 1) Ln 4
    dxn3::ideMarkToggle(w1, 8);        // 2) Ln 9
    ok(dxn3::ideMarkWhisper(w1, "", 200) == "1) Ln 4 · 2) Ln 9",
       "a bare :bm whispers every pin, the :marks order");
    ok(dxn3::ideMarkWhisper(w1, "2", 200) == "2) Ln 9",
       "a typed number narrows the choir to the pins it names");
    ok(dxn3::ideMarkWhisper(w1, "1", 200) == "1) Ln 4",
       "a prefix matches by the entry's head, nothing else");
    ok(dxn3::ideMarkWhisper(w1, "9", 200) == "",
       "a prefix no pin speaks stays silent");
    ok(dxn3::ideMarkWhisper(w1, "", 6) == "",
       "a bar too narrow for even one pin holds its tongue");
    ok(dxn3::ideMarkWhisper(w1, "", 12) == "1) Ln 4",
       "one honest entry fits a small bar - the next would not");
    IdeState w2;                       // the pinless ledger is quiet
    w2.lines = {"solo"};
    ok(dxn3::ideMarkWhisper(w2, "", 200) == "",
       "an empty ledger whispers nothing - bare :bm refuses instead");
  }

  // 63. the hunt: F3 / shift+F3 walk the last query's hits after the
  // searchlight rests — the STRICT law (a hand on a hit walks to the
  // next one, a hand between hits lands on its next one), the wrap,
  // the live recompute, the receipt, and the look that never dirties
  {
    IdeState h;
    h.lines = {"hello world", "say hello again", "", "hello"};
    h.findQ = "hello";
    dxn3::ideFindRefresh(h);
    h.findOpen = false;              // the searchlight rests — the hunt goes on
    Keys f3;
    f3.findJump = true;
    dxn3::ideKey(h, f3);
    ok(h.curR == 1 && h.curC == 4,
       "the first F3 lands on the first hit after the hand");
    ok(h.findSel == 1, "the walk aims the counter at the landed hit");
    ok(h.console.back().find("hit 2/3") != std::string::npos,
       "the receipt speaks the walk's count");
    dxn3::ideKey(h, f3);
    ok(h.curR == 3 && h.curC == 0, "F3 keeps walking — the tail's hello");
    dxn3::ideKey(h, f3);
    ok(h.curR == 0 && h.curC == 0, "F3 wraps around the file's head");
    ok(!h.findOpen, "the searchlight stays resting while the hunt walks");
    Keys sf3;
    sf3.findBack = true;
    dxn3::ideKey(h, sf3);
    ok(h.curR == 3 && h.curC == 0,
       "shift+F3 from the head wraps to the file's tail");
    dxn3::ideKey(h, sf3);
    ok(h.curR == 1 && h.curC == 4, "shift+F3 walks back hit by hit");

    IdeState h2;                     // the heart of the strict law:
    h2.lines = {"hello world", "say hello again", "", "hello"};
    h2.curR = 2;                     // the hand stands BETWEEN hits
    h2.curC = 0;
    h2.findQ = "hello";
    dxn3::ideFindRefresh(h2);
    h2.findOpen = false;
    Keys f3b;
    f3b.findJump = true;
    dxn3::ideKey(h2, f3b);
    ok(h2.curR == 3 && h2.curC == 0,
       "a hand between hits lands on its NEXT hit (the old law skipped it)");

    IdeState h3;                     // enter under the light, same law
    h3.lines = {"hello world", "say hello again", "", "hello"};
    h3.curR = 2;
    h3.curC = 0;
    Keys cf;
    cf.ctrlF = true;
    dxn3::ideKey(h3, cf);
    Keys ty;
    ty.typed = "hello";
    dxn3::ideKey(h3, ty);
    Keys en;
    en.enter = true;
    dxn3::ideKey(h3, en);
    ok(h3.curR == 3 && h3.curC == 0,
       "enter under the light obeys the strict law too");

    IdeState h4;                     // the doc moved since the light rested
    h4.lines = {"hello world", "say hello again", "", "hello"};
    h4.curR = 0;
    h4.curC = 0;
    h4.findQ = "hello";
    h4.findHits = {{0, 0}};          // stale hits — a lie the walk won't keep
    h4.findOpen = false;
    dxn3::ideKey(h4, f3);
    ok(h4.findHits.size() == 3 && h4.curR == 1 && h4.curC == 4,
       "the hunt recomputes the hits live before it walks");

    IdeState h5;                     // nothing to hunt
    h5.lines = {"hello"};
    h5.findOpen = false;
    const int cr5 = h5.curR;
    dxn3::ideKey(h5, f3);
    ok(h5.curR == cr5 && h5.console.empty(),
       "an empty query has nothing to hunt — silence, no move");

    IdeState h6;                     // the look that never edits
    h6.lines = {"hello world", "plain", "hello again"};
    h6.curR = 0;
    h6.curC = 0;
    h6.dirty = false;                // the contract: the hunt never dirties
    h6.findQ = "hello";
    dxn3::ideFindRefresh(h6);
    h6.findOpen = false;
    h6.anchorR = 0;
    h6.anchorC = 0;
    h6.curC = 4;                     // a selection lives
    dxn3::ideKey(h6, f3);
    ok(!h6.dirty, "the hunt is a look — it never dirties the doc");
    ok(h6.anchorR < 0, "the walk abandons the selection, like every hop");
    ok(h6.undo.empty() && h6.redo.empty(),
       "nothing to undo — nothing happened");
  }

  // 64. the ride in the hands: alt+↑/↓ — :lift/:drop without the
  // bar, the same bed law (selection or the hand's line), the pins
  // ride, the edges refuse without a phantom step, one undo each
  {
    IdeState r1;
    r1.lines = {"a", "b", "c", "d"};
    r1.curR = 1;
    Keys ad;
    ad.altDown = true;
    dxn3::ideKey(r1, ad);
    ok(r1.lines[1] == "c" && r1.lines[2] == "b",
       "alt+down drops the hand's line below its neighbor");
    ok(r1.curR == 2, "the hand rides the block's head");
    ok(r1.undo.size() == 1 && r1.undo.back().what == "drop",
       "the drop is ONE undo step named drop");
    ok(r1.dirty, "the ride dirties — the auto-run will host it");
    Keys au;
    au.altUp = true;
    dxn3::ideKey(r1, au);
    ok(r1.lines[1] == "b" && r1.lines[2] == "c" && r1.curR == 1,
       "alt+up brings the line home");

    IdeState r2;                     // the edge refuses
    r2.lines = {"a", "b"};
    r2.curR = 1;
    r2.dirty = false;
    dxn3::ideKey(r2, ad);
    ok(r2.lines.size() == 2 && r2.lines[1] == "b" && r2.undo.empty() &&
       !r2.dirty,
       "nothing below to drop into — no phantom step, no undo");
    ok(r2.console.back().find("nothing below") != std::string::npos,
       "the refusal speaks its edge");

    IdeState r3;                     // the pins ride
    r3.lines = {"a", "b", "c"};
    r3.curR = 0;
    dxn3::ideMarkToggle(r3, 0);      // a pin on the bed
    dxn3::ideMarkToggle(r3, 2);      // a pin far below, unmoved
    dxn3::ideKey(r3, ad);
    ok(r3.marks[0] == 1 && r3.marks[1] == 2,
       "the bed's pin rides down, the far pin stays");

    IdeState r4;                     // a selection bed rides whole
    r4.lines = {"a", "b", "c", "d"};
    r4.anchorR = 0;
    r4.anchorC = 0;
    r4.curR = 1;
    r4.curC = 1;                     // the bed: lines 0-1
    dxn3::ideKey(r4, ad);
    ok(r4.lines[0] == "c" && r4.lines[1] == "a" && r4.lines[2] == "b" &&
           r4.lines[3] == "d",
       "a selected bed drops as one block (the neighbor slides up)");
    ok(r4.undo.back().what == "drop", "the block's ride is one step too");
    ok(dxn3::usageHintFor(":lift").find("one line up") != std::string::npos,
       "the bar's whisper still names the ride the keys now speak");
  }

  // 65. the pen: :w/:wq — the doc's save law lives in main (the disk
  // is the smoke's witness), but the bar's grammar and its whisper
  // are shared law, selftested here
  {
    ok(dxn3::usageHintFor(":w").find(".bak") != std::string::npos,
       "the bar whispers the .bak law to every save");
    const auto w1 = dxn3::parseCommand(":w");
    const auto w2 = dxn3::parseCommand(":w smoke-saved.py");
    const auto w3 = dxn3::parseCommand(":wq");
    ok(w1.ok() && w2.ok() && w2.arg == "smoke-saved.py" && w3.ok(),
       "the pen's names are optional, the verbs well-formed");
  }

  // 66. the ledger, listed: :hist — the undo names newest first, the
  // depth honest, the redo's head riding after the divider, the cap
  // speaking the deeper truth, the empty ledger silent
  {
    IdeState h0;
    ok(dxn3::ideHistWhisper(h0) == "",
       "an untouched doc has no ledger to list");
    h0.lines = {"a"};
    dxn3::idePushUndo(h0, "typing");
    dxn3::idePushUndo(h0, "drop");
    dxn3::idePushUndo(h0, "paste");
    const std::string h = dxn3::ideHistWhisper(h0);
    ok(h.find("[3 steps back] paste · drop · typing") == 0,
       "the depth leads, the names follow NEWEST first");
    ok(h.find("[3 steps back]") != std::string::npos,
       "the depth speaks in steps");
    ok(dxn3::ideHistWhisper(h0, 2).find("… +1 deeper") != std::string::npos,
       "a capped list confesses the deeper truth");
    dxn3::ideUndo(h0);
    ok(dxn3::ideHistWhisper(h0).find("redo: paste") != std::string::npos,
       "the redo's head rides after the divider");
    const auto c1 = dxn3::parseCommand(":hist");
    ok(c1.ok() &&
       dxn3::parseCommand(":hist now").error.find("takes no argument") !=
           std::string::npos,
       ":hist takes no argument, honestly");
    ok(dxn3::usageHintFor(":hist").find("ledger") != std::string::npos,
       "the bar whispers the ledger's law");
  }

  // 67. the counting sort: :sort/:rsort grow numeric awareness — a bed
  // whose every line opens with a number orders the way humans count
  // (2 before 10); one mixed line and the bytes rule as always
  {
    double v = 0;
    ok(dxn3::ideLeadingNumber("42 the answer", v) && v == 42,
       "a line that opens with a number speaks it");
    ok(dxn3::ideLeadingNumber("  7 lean", v) && v == 7,
       "leading air never hides the number");
    ok(dxn3::ideLeadingNumber("3.5 half", v) && v == 3.5,
       "decimals count");
    ok(!dxn3::ideLeadingNumber("abc", v) &&
       !dxn3::ideLeadingNumber("", v),
       "letters and air are no numbers");

    IdeState n1;                     // the classic byte-sort shame, fixed
    n1.lines = {"10 ten", "2 two", "1 one"};
    n1.anchorR = 0;
    n1.anchorC = 0;
    n1.curR = 2;
    n1.curC = 5;
    bool byNum = false;
    ok(dxn3::ideSortSel(n1, &byNum) == 3 && byNum,
       "an all-number bed sorts and says so");
    ok(n1.lines[0] == "1 one" && n1.lines[1] == "2 two" &&
           n1.lines[2] == "10 ten",
       "2 sorts before 10 — the way humans count");
    ok(n1.undo.size() == 1 && n1.undo.back().what == "sort",
       "one honest restore point named sort");

    IdeState n2;                     // decimals keep their truth
    n2.lines = {"1.5 a", "1.10 b", "1.2 c"};
    n2.anchorR = 0;
    n2.anchorC = 0;
    n2.curR = 2;
    n2.curC = 5;
    ok(dxn3::ideSortSel(n2, &byNum) == 3 && byNum &&
           n2.lines[0] == "1.10 b" && n2.lines[1] == "1.2 c" &&
           n2.lines[2] == "1.5 a",
       "decimals count too (1.10 is 1.1, under 1.2)");

    IdeState n3;                     // one mixed line: the bytes rule
    n3.lines = {"10 ten", "2 two", "abc"};
    n3.anchorR = 0;
    n3.anchorC = 0;
    n3.curR = 2;
    n3.curC = 3;
    ok(dxn3::ideSortSel(n3, &byNum) == 3 && !byNum &&
           n3.lines[0] == "10 ten" && n3.lines[1] == "2 two" &&
           n3.lines[2] == "abc",
       "one mixed line keeps the byte-honest sort");

    IdeState n4;                     // ties keep the byte order
    n4.lines = {"2 b", "2 a", "1 x"};
    n4.anchorR = 0;
    n4.anchorC = 0;
    n4.curR = 2;
    n4.curC = 3;
    ok(dxn3::ideSortSel(n4, &byNum) == 3 &&
           n4.lines[1] == "2 a" && n4.lines[2] == "2 b",
       "equal numbers fall back to the byte order");

    IdeState n5;                     // the mirror: numbers land biggest first
    n5.lines = {"1 one", "10 ten", "2 two"};
    n5.anchorR = 0;
    n5.anchorC = 0;
    n5.curR = 2;
    n5.curC = 5;
    ok(dxn3::ideRsortSel(n5, &byNum) == 3 && byNum &&
           n5.lines[0] == "10 ten" && n5.lines[1] == "2 two" &&
           n5.lines[2] == "1 one" && n5.undo.back().what == "rsort",
       "the numeric rsort lands biggest first");

    IdeState n6;                     // negative numbers count too
    n6.lines = {"5 above", "-1 below"};
    n6.anchorR = 0;
    n6.anchorC = 0;
    n6.curR = 1;
    n6.curC = 8;
    ok(dxn3::ideSortSel(n6, &byNum) == 2 &&
           n6.lines[0] == "-1 below",
       "a negative opens a number honestly");

    ok(dxn3::usageHintFor(":sort").find("number") != std::string::npos,
       "the bar whispers the counting law");
  }

  // 68. the whisper's clip law, once: whisperOffer joins with " · "
  // and ends the line at the first entry that does not fit
  {
    std::string w;
    ok(dxn3::whisperOffer(w, "abc", 3) && w == "abc",
       "the first entry fits at its own width");
    ok(dxn3::whisperOffer(w, "de", 8) && w == "abc · de",
       "the next entry joins with the separator");
    ok(!dxn3::whisperOffer(w, "f", 8) && w == "abc · de",
       "the first entry that does not fit ends the line, untouched");
    std::string w2;
    ok(!dxn3::whisperOffer(w2, "xy", 1) && w2.empty(),
       "a bar too narrow for even one entry holds its tongue");
    ok(dxn3::whisperOffer(w2, "xy", 2) && w2 == "xy",
       "an entry fits a bar of exactly its width");
  }

  // 69. :undo/:redo — the second chance, spoken from the bar: the
  // grammar knows the twins, the walk they name is real, the future
  // ends where it ended
  {
    Cmd u = dxn3::parseCommand(":undo");
    ok(u.ok() && u.verb == "undo",
       ":undo is well-formed, no argument needed");
    Cmd r = dxn3::parseCommand(":redo");
    ok(r.ok() && r.verb == "redo",
       ":redo is well-formed, no argument needed");
    Cmd rj = dxn3::parseCommand(":redo now");
    ok(!rj.ok() && rj.error.find("takes no argument") != std::string::npos,
       ":redo refuses arguments with the family's honest usage");
    ok(dxn3::usageHintFor(":undo").find("ctrl+z") != std::string::npos &&
           dxn3::usageHintFor(":redo").find("ctrl+y") != std::string::npos,
       "the bar whispers the twins it twins");

    IdeState s;                      // the walk the verbs name is REAL
    s.lines = {"alpha"};
    s.curR = 0;
    s.curC = 5;
    Keys t;
    t.typed = "beta";
    dxn3::ideKey(s, t);
    ok(s.lines[0] == "alphabeta" && !s.undo.empty(),
       "an edit lands in the ledger");
    ok(dxn3::ideUndo(s) && s.lines[0] == "alpha",
       "the walk back restores the past");
    ok(dxn3::ideRedo(s) && s.lines[0] == "alphabeta",
       "the walk forward restores the future");
    ok(!dxn3::ideRedo(s),
       "the future ends where it ended — a second :redo says no");
    ok(dxn3::ideUndoReceipt(s).find("engine: undo — ") == 0 &&
           dxn3::ideRedoReceipt(s).find("engine: redo — ") == 0,
       "the receipts the bar speaks are the keys' receipts, byte for byte");
  }

  // 70. :words — the census: case forgiven, the edges stripped, the
  // inside kept whole, ties taking the alphabet, the tail counted
  {
    IdeState s;
    s.lines = {"The the the spawn",
               "\"spawn\" (spawn) gem-1",
               "SPAWN gem-1 gem-1"};
    const std::string w = dxn3::ideWordsWhisper(s, 6);
    ok(w.rfind("spawn×4", 0) == 0,
       "case and edges forgiven — four spawns lead the census");
    ok(w.find("gem-1×3") != std::string::npos &&
           w.find("the×3") != std::string::npos &&
           w.find("gem-1×3") < w.find("the×3"),
       "the inside stays whole and ties take the alphabet");
    ok(w == "spawn×4 · gem-1×3 · the×3",
       "the census line is exactly the ranked truth");

    IdeState big;
    big.lines = {"a b c d e f g"};
    const std::string w2 = dxn3::ideWordsWhisper(big, 5);
    ok(w2.find("… +2 more words") != std::string::npos,
       "the cap counts the words it hides");

    IdeState punct;
    punct.lines = {"! ? ... ()", "on_hit stays"};
    const std::string w3 = dxn3::ideWordsWhisper(punct, 6);
    ok(w3.rfind("on_hit×1", 0) == 0 && w3.find("stays×1") != std::string::npos,
       "pure punctuation says nothing; the underscore inside survives");

    IdeState e;
    e.lines = {""};
    ok(dxn3::ideWordsWhisper(e).empty(),
       "an empty document holds no census");
    ok(dxn3::usageHintFor(":words").find("census") != std::string::npos,
       "the bar whispers the census");
  }

  // 71. :todo — the marker hunt: the honest uppercase markers, the
  // line number leading, the tail honest, lowercase prose ignored
  {
    IdeState s;
    s.lines = {"# the plan",
               "jump()  # TODO make it fair",
               "# a todo in prose is not a promise",
               "if x: pass  # FIXME the wall",
               "",
               "reach the gem  # XXX trust it"};
    const std::string t = dxn3::ideTodoWhisper(s, 6);
    ok(t.rfind("2: ", 0) == 0, "the line number leads the entry");
    ok(t.find("TODO make it fair") != std::string::npos &&
           t.find("FIXME the wall") != std::string::npos &&
           t.find("XXX trust it") != std::string::npos,
       "the three markers are named with their words");
    ok(t.find("4: ") != std::string::npos && t.find("6: ") != std::string::npos,
       "the numbers are the true 1-based lines");
    ok(t.find("todo in prose") == std::string::npos,
       "lowercase prose is not a promise");

    IdeState many;
    many.lines = {"TODO a", "TODO b", "TODO c", "TODO d",
                  "TODO e", "TODO f", "TODO g"};
    const std::string t2 = dxn3::ideTodoWhisper(many, 6);
    ok(t2.find("… +1 deeper in the file") != std::string::npos,
       "the cap counts the markers it hides");

    IdeState none;
    none.lines = {"clean as water", ""};
    ok(dxn3::ideTodoWhisper(none).empty(),
       "a clean file holds no debts");
    ok(dxn3::usageHintFor(":todo").find("marker") != std::string::npos,
       "the bar whispers the hunt");
  }

  // 72. the selection's own census: the honest slice, counted like
  // the document — first line from c0, last line to c1, middle whole
  {
    IdeState s;
    s.lines = {"alpha beta gamma",
               "delta epsilon",
               "zeta",
               "eta theta"};
    // a partial slice: "beta gamma" + "delta epsil"
    dxn3::IdeSelStats st =
        dxn3::ideSelStats(s, {0, 6, 1, 10});
    ok(st.lines == 2 && st.words == 4 && st.chars == 21,
       "the slice spans lines and keeps its edges honest");
    // a whole-line selection: the middle stays whole
    dxn3::IdeSelStats whole = dxn3::ideSelStats(s, {1, 0, 2, 3});
    ok(whole.lines == 2 && whole.words == 3 && whole.chars == 17,
       "a whole-line range counts the full lines");
  }

  // 73. the quiet's ledger: :zen wakes and replays what it gathered —
  // the entering line counts (it was never shown either), the newest
  // three ride the digest oldest-first, the cap counts its hidden
  {
    IdeState s;
    s.console = {"engine: boot noise"};
    s.zenSince = s.console.size();
    s.console.push_back("engine: zen — the rail rests");
    s.console.push_back("engine: trimmed 3 lines of trailing air");
    s.console.push_back("engine: opened scenes/level-1");
    size_t kept = 999;
    const std::string d =
        dxn3::ideZenDigest(s.console, s.zenSince, &kept);
    ok(kept == 3, "everything from zenSince counts — even the entering line");
    ok(d.find("zen — the rail rests") < d.find("trimmed 3 lines") &&
           d.find("trimmed 3 lines") < d.find("opened scenes/level-1"),
       "the ledger reads chronologically (oldest first)");

    // the cap: five receipts, the newest three ride, the count is honest
    IdeState m;
    m.console = {"engine: boot noise"};
    m.zenSince = m.console.size();
    m.console.push_back("engine: r1");
    m.console.push_back("engine: r2");
    m.console.push_back("engine: r3");
    m.console.push_back("engine: r4");
    m.console.push_back("engine: r5");
    size_t kept2 = 0;
    const std::string d2 =
        dxn3::ideZenDigest(m.console, m.zenSince, &kept2);
    ok(kept2 == 5, "five receipts, five counted");
    ok(d2.find("r3") != std::string::npos && d2.find("r4") != std::string::npos &&
           d2.find("r5") != std::string::npos && d2.find("r1") == std::string::npos &&
           d2.find("r2") == std::string::npos,
       "the digest carries the NEWEST three");
    ok(d2.find("… +2 more in the console") != std::string::npos,
       "the cap counts what it hides");

    // the trim: a long receipt keeps its head, honestly cut — the
    // short-quiet law stays out of the way (three receipts ride)
    IdeState long_;
    long_.console = {"engine: boot"};
    long_.zenSince = long_.console.size();
    long_.console.push_back("engine: r1");
    long_.console.push_back("engine: r2");
    long_.console.push_back(std::string(60, 'x'));
    const std::string d3 =
        dxn3::ideZenDigest(long_.console, long_.zenSince, nullptr);
    const std::string tail = d3.substr(d3.size() - 50);
    ok(d3.rfind("engine: r2 · ") != std::string::npos &&
           d3.rfind("engine: r2 · ") + std::string("engine: r2 · ").size() ==
               d3.size() - 50,
       "the long receipt rides last, after the ledger's " " · ");
    ok(tail[0] == 'x' && tail[46] == 'x' && tail[47] == '\xe2' &&
           tail[48] == '\x80' && tail[49] == '\xa6',
       "a receipt too long is trimmed to 47 bytes + the … tail");

    // a short quiet leaves the window's work where it lies
    IdeState small;
    small.console = {"engine: boot"};
    small.zenSince = small.console.size();
    small.console.push_back("engine: zen — the rail rests");
    size_t kept3 = 0;
    ok(dxn3::ideZenDigest(small.console, small.zenSince, &kept3).empty() &&
           kept3 == 1,
       "one gathered receipt needs no digest — the window shows it");
    ok(dxn3::usageHintFor(":zen").find("replays") != std::string::npos,
       "the bar whispers the wake's replay");
  }

  // 74. the welcome back: the hand returns where it left — planted on
  // the way out, looked up on the way in, LANDED honest (clamped to
  // the document as it is NOW, never off the page, an empty page
  // indexes nothing)
  {
    std::map<std::string, dxn3::DocCur> m;
    dxn3::ideDocCurRemember(m, "game.py", 6, 0);
    ok(m.size() == 1, "the hand is planted under the file's name");
    dxn3::ideDocCurRemember(m, "", 3, 3);
    ok(m.size() == 1,
       "a nameless file plants nothing (no name, no memory)");
    const auto hand = dxn3::ideDocCurLookup(m, "game.py");
    ok(hand && hand->first == 6 && hand->second == 0,
       "the lookup returns the planted hand");
    ok(!dxn3::ideDocCurLookup(m, "other.py"),
       "an unknown file has no past");
    dxn3::ideDocCurRemember(m, "game.py", 2, 4);
    ok(m.size() == 1 && m["game.py"].first == 2,
       "a new visit replaces the old hand — one memory per file");

    const std::vector<std::string> doc = {"alpha", "beta", "gamma"};
    const auto home = dxn3::ideDocCurLand(doc, dxn3::DocCur{1, 2});
    ok(home.first == 1 && home.second == 2,
       "a hand inside the doc lands where it stood");
    const auto deep = dxn3::ideDocCurLand(doc, dxn3::DocCur{40, 0});
    ok(deep.first == 2,
       "a file that shrank keeps the hand on its last line");
    const auto wide = dxn3::ideDocCurLand(doc, dxn3::DocCur{0, 99});
    ok(wide.second == 5, "the column clamps to the line it lands in");
    const auto wild = dxn3::ideDocCurLand(doc, dxn3::DocCur{-3, -2});
    ok(wild.first == 0 && wild.second == 0,
       "a wild hand still lands inside the page");
    const std::vector<std::string> none;
    const auto bare = dxn3::ideDocCurLand(none, dxn3::DocCur{5, 5});
    ok(bare.first == 0 && bare.second == 0,
       "a file vanished to zero bytes holds the hand at the top");
    ok(dxn3::usageHintFor(":open").find("returns") != std::string::npos &&
           dxn3::usageHintFor(":recent").find("returns") !=
               std::string::npos,
       "the bar whispers the welcome back on both doors");
  }

  // 75. the jumps: the lines the hand LEAPT to — a change of line
  // plants (goto, the pins' F2, the welcome back's landing), a stand
  // plants nothing; the ledger is capped, cleared with the document,
  // and :jumps reads it newest-first with the "now" leading
  {
    std::vector<int> j;
    dxn3::ideJumpPush(j, 6);
    dxn3::ideJumpPush(j, 29);
    ok(j.size() == 2 && j.back() == 29,
       "a change of line plants the leap, newest at the back");
    dxn3::ideJumpPush(j, 29);
    ok(j.size() == 2, "a stand on the ledger's own head plants nothing");
    dxn3::ideJumpPush(j, -4);
    ok(j.size() == 2, "a wild line is refused — no negative leaps");
    dxn3::ideJumpPush(j, 6);
    ok(j.size() == 3 && j[0] == 6 && j[2] == 6,
       "returning to an old line is an honest leap, remembered twice");
    for (int i = 0; i < 34; ++i) dxn3::ideJumpPush(j, 100 + i);
    ok(j.size() == 32 && j.front() == 102,
       "the ledger caps at 32 — the oldest leap falls off");
    ok(dxn3::ideJumpsWhisper(j).find("now 134") != std::string::npos &&
           dxn3::ideJumpsWhisper(j).find("… +24 deeper") !=
               std::string::npos,
       "the whisper caps at 8 and counts what it hides");

    const std::vector<int> walk = {6, 29, 54};
    ok(dxn3::ideJumpsWhisper(walk) == "now 55 · 30 · 7",
       "the whisper reads newest first, the now leading, 1-based names");
    ok(dxn3::ideJumpsWhisper({}).empty(),
       "an empty ledger says nothing — the caller refuses honestly");

    IdeState fz;
    fz.lines = {"a", "b", "c", "d"};
    dxn3::ideMarkToggle(fz, 3);            // a pin on line 4
    dxn3::Keys mk;
    mk.markNext = true;                    // F2: the leap
    dxn3::ideKey(fz, mk);
    ok(fz.curR == 3 && fz.jumps.size() == 1 && fz.jumps.back() == 3,
       "F2's leap plants the jump — the pins' keyboard rides the ledger");
    dxn3::ideKey(fz, mk);                  // the only pin IS the hand's line
    ok(fz.jumps.size() == 1,
       "a leap that lands where you stand is a stand — nothing plants");

    const auto jc = dxn3::parseCommand(":jumps");
    ok(jc.ok() && jc.verb == "jumps",
       "parseCommand reads :jumps — the leaps are a verb");
    const auto jb = dxn3::parseCommand(":jumps 3");
    ok(!jb.ok() && jb.error.find("takes no argument") != std::string::npos,
       ":jumps with an argument is refused — the ledger needs none");
    ok(dxn3::usageHintFor(":jumps").find("newest first") !=
           std::string::npos,
       "the bar whispers the listing's order");
  }

  // 76. :fresh — the disk's truth wins the page back. The grammar is
  // here; the walk itself is openScript's (the smoke drives it on a
  // real studio) — the law: no argument, an honest whisper, and a
  // page that was never written is refused with the way out.
  {
    const auto fc = dxn3::parseCommand(":fresh");
    ok(fc.ok() && fc.verb == "fresh",
       "parseCommand reads :fresh — the reload is a verb");
    const auto fb = dxn3::parseCommand(":fresh now");
    ok(!fb.ok() && fb.error.find("takes no argument") != std::string::npos,
       ":fresh with an argument is refused — the disk needs no hint");
    ok(dxn3::usageHintFor(":fresh").find("disk") != std::string::npos,
       "the bar whispers whose truth wins — the disk's");
  }

  // 77. the walker: ctrl+o / alt+← step into the ledger's past, alt+→
  // steps back out. Walking is NOT leaping — nothing plants, only the
  // bookmark moves; a real leap kills the bookmark; the edges refuse.
  {
    IdeState w;
    ok(dxn3::ideJumpWalkBack(w) == -1,
       "an empty ledger refuses the walk");
    dxn3::ideJumpPush(w, 6);
    dxn3::ideJumpPush(w, 29);
    dxn3::ideJumpPush(w, 54);
    ok(w.jumps.size() == 3 && w.jumpIx == -1,
       "leaps put the walker at now — no bookmark until it walks");
    ok(dxn3::ideJumpWalkBack(w) == 29 && w.jumpIx == 1,
       "the first step back lands on the leap before the newest");
    ok(dxn3::ideJumpWalkBack(w) == 6 && w.jumpIx == 0,
       "the second step reaches the ledger's oldest");
    ok(dxn3::ideJumpWalkBack(w) == -1,
       "the first jump refuses — nothing behind it");
    ok(dxn3::ideJumpWalkFwd(w) == 29 && w.jumpIx == 1,
       "the walk forward climbs back out");
    ok(dxn3::ideJumpWalkFwd(w) == 54 && w.jumpIx == 2,
       "and lands on the newest again");
    ok(dxn3::ideJumpWalkFwd(w) == -1,
       "the newest leap is the edge — nothing ahead");
    dxn3::ideJumpPush(w, 100);
    ok(w.jumpIx == -1 && w.jumps.back() == 100,
       "a real leap kills the bookmark — the walker is at now");
    ok(w.jumps.size() == 4,
       "the walk never planted — the ledger kept its truth");

    const std::vector<int> led = {6, 29, 54, 100};
    ok(dxn3::ideJumpsWhisper(led, 2) == "now 101 · >55 · 30 · 7",
       "the walked entry wears the > marker in its place");
    ok(dxn3::ideJumpsWhisper(led, -1) == "now 101 · 55 · 30 · 7",
       "no bookmark, no marker — the plain listing");
    ok(dxn3::ideJumpsWhisper(led, 9) == "now 101 · 55 · 30 · 7",
       "a wild bookmark is ignored");
    ok(dxn3::ideJumpsWhisper(led, 3) == "now 101 · 55 · 30 · 7",
       "a bookmark on the newest is the plain listing — now needs no mark");
    ok(dxn3::ideJumpsWhisper(led, 0) == "now 101 · 55 · 30 · >7",
       "the marker rides the ledger's tail too");

    IdeState fz;
    fz.lines = {"a", "b", "c", "d", "e"};
    dxn3::ideJumpPush(fz, 1);
    dxn3::ideJumpPush(fz, 3);
    dxn3::Keys ob;
    ob.jumpBack = true;                    // ctrl+o / alt+←
    dxn3::ideKey(fz, ob);
    ok(fz.curR == 1 && fz.jumpIx == 0 && fz.jumps.size() == 2,
       "the key's walk lands the hand and moves only the bookmark");
    ok(fz.console.back().find("walks back to line 2") != std::string::npos,
       "the walk speaks its landing");
    dxn3::Keys of;
    of.jumpFwd = true;                     // alt+→
    dxn3::ideKey(fz, of);
    ok(fz.curR == 3 && fz.jumpIx == 1 &&
           fz.console.back().find("walks forward to line 4") !=
               std::string::npos,
       "the walk out speaks its landing too");
    dxn3::ideKey(fz, of);
    ok(fz.console.back().find("nothing ahead") != std::string::npos,
       "the newest leap is the edge, spoken honestly");
  }

  // 78. the census: :changes — every line the hand CHANGED since the
  // page opened. The pins' structural law speaks: a landing above
  // slides a touch down, a cut carries its touches out (a touched line
  // dies WITH its line); undo does NOT un-touch, it clamps.
  {
    IdeState c;
    c.lines = {"alpha", "beta", "gamma", "delta", "epsilon"};
    ok(c.touched.empty() && dxn3::ideTouchWhisper(c).empty(),
       "a fresh page's census is empty");
    dxn3::ideTouch(c, 2);
    dxn3::ideTouch(c, 0);
    dxn3::ideTouch(c, 2);                      // a second touch is a stand
    ok(c.touched.size() == 2 && c.touched[0] == 0 && c.touched[1] == 2,
       "touches record sorted and unique");
    dxn3::ideTouch(c, 99);
    ok(c.touched.size() == 2,
       "a touch beyond the document is refused");
    ok(dxn3::ideTouchWhisper(c) == "1 · 3",
       "the whisper speaks 1-based, ascending, dot-joined");

    // the structural laws
    dxn3::ideTouchShift(c, 1, 2);              // two lines land at index 1
    ok(c.touched[0] == 0 && c.touched[1] == 4,
       "a landing above slides the touches down (the pins' shift law)");
    dxn3::ideTouchErase(c, 0, 1);              // line 0 leaves
    ok(c.touched.size() == 1 && c.touched[0] == 3,
       "a touch above the cut slides up, none dies (the pins' erase law)");
    dxn3::ideTouchErase(c, 2, 2);              // the touched line dies
    ok(c.touched.empty(),
       "a touched line cut away dies WITH its line");
    c.lines.resize(2);
    dxn3::ideTouch(c, 0);
    dxn3::ideTouch(c, 1);
    c.lines.resize(1);
    dxn3::ideTouchClamp(c);
    ok(c.touched.size() == 1 && c.touched[0] == 0,
       "the clamp keeps only the touches the restored document can hold");

    // the whisper's cap
    IdeState cw;
    for (int i = 0; i < 11; ++i) cw.lines.push_back("l");
    for (int i = 0; i < 11; ++i) dxn3::ideTouch(cw, i);
    ok(dxn3::ideTouchWhisper(cw, 8) == "1 · 2 · 3 · 4 · 5 · 6 · 7 · 8 … +3 deeper",
       "the whisper caps at eight and names the deeper count");

    // the funnel: typing touches the hand's line
    IdeState t;
    t.lines = {"", "", ""};
    dxn3::Keys ty;
    ty.typed = "x";
    dxn3::ideKey(t, ty);
    ok(t.touched.size() == 1 && t.touched[0] == 0,
       "typing touches the hand's line");
    dxn3::Keys en;
    en.enter = true;                           // split line 0: two touched
    dxn3::ideKey(t, en);
    ok(t.touched.size() == 2 && t.touched[0] == 0 && t.touched[1] == 1,
       "enter touches the head it cut and the tail it made");
    dxn3::Keys ba;
    ba.back = true;                            // join them back: line 1 dies
    dxn3::ideKey(t, ba);
    ok(t.touched.size() == 1 && t.touched[0] == 0,
       "backspace's join kills the folded line's touch, the seam keeps both");

    // the census rides undo: clamped, never un-touched. The join had
    // its own restore point (an enter push breaks the coalescing), so
    // one ctrlZ walks back to the post-split page — the fold undone,
    // the line it folded away EXISTING again, and its touch NOT coming
    // back: the erase was a session fact too. The typing's touch
    // survives the rewind untouched. The document is what came back;
    // the census is what the session wrote.
    dxn3::Keys uz;
    uz.ctrlZ = true;
    const bool stepped = dxn3::ideUndo(t);
    ok(stepped && t.lines.size() == 4 && t.touched.size() == 1 &&
           t.touched[0] == 0,
       "undo restores the document but never un-touches the session");

    // the paste's bed, the cut's ride-out
    IdeState p;
    p.lines = {"one", "two", "three"};
    p.clip = {"a", "b"};
    p.clipLines = true;
    dxn3::ideClipPaste(p);
    ok(p.touched.size() == 2 && p.touched[0] == 0 && p.touched[1] == 1,
       "a line paste touches the bed it landed on");
    dxn3::Keys ct;
    ct.ctrlX = true;
    dxn3::ideKey(p, ct);                       // bare cut lifts line 0 away
    ok(p.touched.size() == 1 && p.touched[0] == 0,
       "a bare cut carries its touched line out and slides the rest up");

    // the sort's bed, the trim's honesty
    IdeState so;
    so.lines = {"c", "a", "b", "d"};
    so.anchorR = 0; so.anchorC = 0;
    so.curR = 2; so.curC = 1;
    dxn3::ideSortSel(so);
    ok(so.touched.size() == 3 && so.touched[0] == 0 && so.touched[2] == 2,
       "a sort touches every line it reordered");
    IdeState tr;
    tr.lines = {"keep   ", "clean", "tail  "};
    dxn3::ideTrimTrailing(tr);
    ok(tr.touched.size() == 2 && tr.touched[0] == 0 && tr.touched[1] == 2,
       "a trim touches only the lines that lost air");

    // openScript's half is smoke's drive — the clear law, pure:
    dxn3::ideTouchClear(tr);
    ok(tr.touched.empty(),
       "a page just opened is a clean page — the census restarts");
  }

  // 79. the cross-marks and the census's leap: :jumps wears the pin's
  // diamond on a leapt line (">" prefixes the walker's entry, "◆"
  // suffixes every pinned one — both can ride one entry), and
  // :changes <n> leaps to the Nth touched line — a REAL leap, planted.
  {
    const std::vector<int> led = {6, 29, 54};
    const std::vector<int> pins = {29};        // line 30 (0-based 29)
    ok(dxn3::ideJumpsWhisper(led, -1, pins) == "now 55 · 30◆ · 7",
       "a pin in the ledger wears the diamond in the listing");
    ok(dxn3::ideJumpsWhisper(led, 1, pins) == "now 55 · >30◆ · 7",
       "the walker's bookmark and the pin ride ONE entry together");
    ok(dxn3::ideJumpsWhisper(led, -1, {}) == "now 55 · 30 · 7",
       "no pins, no diamonds — the plain listing");
    ok(dxn3::ideJumpsWhisper(led, 1, {6, 54}) ==
           "now 55◆ · >30 · 7◆",
       "every pinned entry wears its diamond, wherever it stands");
    const std::vector<int> deep = {1,  2,  3,  4,  5,  6,  7,  8, 9};
    ok(dxn3::ideJumpsWhisper(deep, -1, {1, 8}) ==
           "now 10 · 9◆ · 8 · 7 · 6 · 5 · 4 · 3 … +1 deeper",
       "the visible pin wears its diamond; the pin hidden beyond the "
       "cap stays unseen");

    // the cross-marked census: a touched line that is also a pin
    // wears the diamond — one marking law for both listings
    IdeState cm;
    cm.lines = {"x", "y", "z"};
    dxn3::ideTouch(cm, 0);
    dxn3::ideTouch(cm, 2);
    dxn3::ideMarkToggle(cm, 2);
    ok(dxn3::ideTouchWhisper(cm, cm.marks) == "1 · 3◆",
       "a touched pin wears the diamond in the census");
    ok(dxn3::ideTouchWhisper(cm) == "1 · 3",
       "the plain whisper stays plain — the caller chooses the law");

    // :changes <n> — the leap. The verb's walk lives in main (smoke's
    // pty drive lands the hand); here the LAWS it obeys: the leap is
    // planted in the ledger, the census order is ascending, and a wild
    // index is the caller's refusal. Drive ideJumpPush as the handler
    // does and check the ledger grew by the leap.
    IdeState cl;
    cl.lines = {"a", "b", "c", "d", "e"};
    dxn3::ideTouch(cl, 3);
    dxn3::ideTouch(cl, 1);
    const int to = cl.touched[static_cast<size_t>(1 - 1)];  // :changes 1
    ok(to == 1, "the census's first line is its smallest");
    dxn3::ideJumpPush(cl, to);
    ok(cl.jumps.size() == 1 && cl.jumps.back() == 1 && cl.jumpIx == -1,
       "the census's leap is a real leap — planted, the walker at now");
  }

  // 80. the dice: :shuffle deals the bed into random order — a seed
  // replays the deal EXACTLY, the bed's multiset survives, the pins
  // ride their CONTENT (the flip's law told by a permutation), the
  // census touches the whole bed, one undo step takes it back.
  {
    IdeState d;
    d.lines = {"one", "two", "three", "four", "five", "six"};
    d.anchorR = 1; d.anchorC = 0;              // bed: lines 2..5
    d.curR = 4; d.curC = 3;
    IdeState e = d;                            // the twin for the replay law
    unsigned s1 = 0, s2 = 0;
    const int dealt1 = dxn3::ideShuffleSel(d, 7, true, &s1);
    ok(dealt1 == 4 && s1 == 7,
       "a seeded shuffle deals the whole bed and speaks the seed");
    const int dealt2 = dxn3::ideShuffleSel(e, 7, true, &s2);
    ok(dealt2 == 4 && d.lines == e.lines,
       "the same seed deals the same order (the replay law)");

    // the multiset survives: the bed's lines are the same words
    std::vector<std::string> got(d.lines.begin() + 1, d.lines.begin() + 5);
    std::sort(got.begin(), got.end());
    const std::vector<std::string> want = {"five", "four", "three", "two"};
    ok(got == want, "the deal preserves the bed's words — none lost, none made");

    // a different seed (almost surely) deals differently — deterministic
    IdeState f = d;
    f.anchorR = 1; f.anchorC = 0; f.curR = 4; f.curC = 3;
    dxn3::ideShuffleSel(f, 8, true, nullptr);
    ok(f.lines != d.lines || dealt1 == 0,
       "a different seed deals a different order (deterministic per seed)");

    // the pins follow their content, the census covers the bed
    IdeState p;
    p.lines = {"a", "b", "c", "d"};
    dxn3::ideMarkToggle(p, 2);                 // a pin on line 3 ("c")
    p.anchorR = 0; p.anchorC = 0;
    p.curR = 3; p.curC = 1;
    dxn3::ideShuffleSel(p, 7, true, nullptr);
    ok(p.touched.size() == 4,
       "the deal touches every line it rewrote");
    bool pinRides = false;
    for (int r = 0; r < 4; ++r)                // the pin sits where "c" landed
      if (p.lines[static_cast<size_t>(r)] == "c" &&
          dxn3::ideMarkHas(p, r)) pinRides = true;
    ok(pinRides, "the pin rides its content to its new home");
    ok(std::is_sorted(p.marks.begin(), p.marks.end()),
       "the pins stay sorted after the deal");

    // the second chance takes it all back
    dxn3::Keys uz;
    uz.ctrlZ = true;
    const bool stepped = dxn3::ideUndo(p);
    ok(stepped && p.lines ==
           std::vector<std::string>{"a", "b", "c", "d"},
       "one undo step deals the old order back");

    // the honest refusals: no bed, no dice, no snapshot
    IdeState r;
    r.lines = {"solo"};
    ok(dxn3::ideShuffleSel(r, 7, true, nullptr) == 0 && r.undo.empty(),
       "a bed of one refuses — one line has no other order");
  }

  // 81. :help <verb> — the bar's typing whisper, promoted to the
  // console where it can be read slowly. The parse takes one verb;
  // the hint router is the SAME table the bar speaks.
  {
    const auto h1 = dxn3::parseCommand(":help sort");
    ok(h1.ok() && h1.arg == "sort", ":help takes a verb to teach");
    const auto h2 = dxn3::parseCommand(":help");
    ok(h2.ok() && h2.arg.empty(), "a bare :help still lists the verbs");
    const auto h3 = dxn3::parseCommand(":help sort uniq");
    ok(!h3.ok() && h3.error.find("one verb") != std::string::npos,
       ":help takes ONE verb at a time");
    ok(dxn3::usageHintFor("sort").find("selected lines") != std::string::npos,
       "the verb's hint is the bar's own law, spoken in full");
    ok(dxn3::usageHintFor("nosuchverb").empty(),
       "an unknown verb whispers nothing — the caller refuses");
  }

  // 82. the macro register: the recorder and the replay are verbs with
  // the no-arg law; the register itself is session state (the engine's
  // walk is main's — the smoke drives it through the pty).
  {
    const auto m1 = dxn3::parseCommand(":record");
    ok(m1.ok() && m1.arg.empty(), ":record takes no argument");
    const auto m2 = dxn3::parseCommand(":macro");
    ok(m2.ok() && m2.arg.empty(), ":macro takes no argument");
    const auto m3 = dxn3::parseCommand(":macro 3");
    ok(m3.ok() && m3.num == 3.f,
       ":macro N takes a run count — the take, N times");
    const auto m4 = dxn3::parseCommand(":macro 100");
    ok(!m4.ok(), "a wild run count is refused (1..99)");
    const auto m5 = dxn3::parseCommand(":record now");
    ok(!m5.ok(), ":record still takes no argument — the take is the typing");
    ok(dxn3::usageHintFor("record").find("recorder") != std::string::npos,
       "the recorder's law whispers as you type");
  }

  // 83. the rebalance: :center — the hand rides the viewport's middle,
  // clamped to the doc's honest edges; a look, never an edit.
  {
    IdeState c;
    c.lines.clear();                       // the default doc has one empty line
    for (int i = 0; i < 100; ++i) c.lines.push_back("l" + std::to_string(i));
    c.page = 20;                           // the viewport's rows
    c.curR = 50;
    dxn3::ideCenter(c);
    ok(c.top == 40, "the middle is the preference — 50 rides at 40");
    ok(c.curR == 50 && c.lines.size() == 100,
       "the hand and the document are untouched (a look, never an edit)");
    c.curR = 3;
    dxn3::ideCenter(c);
    ok(c.top == 0, "a hand near the top keeps the top (clamped)");
    c.curR = 97;
    dxn3::ideCenter(c);
    ok(c.top == 80, "a hand near the bottom keeps the bottom (maxTop wins)");
    const auto cz = dxn3::parseCommand(":center");
    ok(cz.ok() && cz.arg.empty(), ":center takes no argument");
  }

  // 84. the swap: :s/old/new — every byte-exact occurrence traded on
  // the bed; the match is EXACT (the searchlight forgives, the swap
  // does not); only changed lines are touched; one undo step; a clean
  // bed takes no snapshot.
  {
    IdeState r;
    r.lines = {"aa bb aa", "cc aa", "dd"};
    r.anchorR = 0; r.anchorC = 0;
    r.curR = 1; r.curC = 2;                // the bed: lines 1..2
    int touched = 0;
    const int made = dxn3::ideReplaceSel(r, "aa", "XX", &touched);
    ok(made == 3 && touched == 2,
       "every occurrence traded — three on two lines");
    ok(r.lines[0] == "XX bb XX" && r.lines[1] == "cc XX" &&
           r.lines[2] == "dd",
       "the bed traded exactly; the line below it untouched");
    ok(r.touched.size() == 2 && r.touched[0] == 0 && r.touched[1] == 1,
       "only the lines that changed carry a touch");
    ok(r.marks.empty() && r.lines.size() == 3,
       "the bed never grows — the pins could not move");

    dxn3::Keys uz;
    uz.ctrlZ = true;
    ok(dxn3::ideUndo(r) &&
           r.lines == std::vector<std::string>{"aa bb aa", "cc aa", "dd"},
       "one undo step restores the old bytes");

    // the empty new is a deletion; the case is exact
    IdeState d;
    d.lines = {"Delete me, delete ME."};
    dxn3::ideReplaceSel(d, "delete", "", &touched);
    ok(d.lines[0] == "Delete me,  ME.",
       "an empty new deletes in place (the space after survives — "
       "byte-exact work, byte-honest gaps)");

    // a clean bed: no snapshot, no touch, honest zero
    IdeState n;
    n.lines = {"nothing here"};
    const int none = dxn3::ideReplaceSel(n, "zz", "yy", &touched);
    ok(none == 0 && n.undo.empty() && n.touched.empty() &&
           n.lines[0] == "nothing here",
       "no match, no snapshot — the clean bed stays clean");

    // no selection: the hand's line is the bed
    IdeState h;
    h.lines = {"one", "two one", "three"};
    h.curR = 1; h.curC = 0;
    dxn3::ideReplaceSel(h, "one", "1", &touched);
    ok(h.lines[0] == "one" && h.lines[1] == "two 1" && h.lines[2] == "three",
       "no selection: the hand's line trades alone");

    // the refusals: an empty old, a newline in the new
    IdeState x;
    x.lines = {"a"};
    ok(dxn3::ideReplaceSel(x, "", "b", nullptr) == 0 && x.undo.empty(),
       "an empty old refuses — it matches everywhere and nothing");
    ok(dxn3::ideReplaceSel(x, "a", "b\nc", nullptr) == 0 && x.undo.empty(),
       "a newline in the new refuses — the bed never grows");
    const auto p1 = dxn3::parseCommand(":s/old/new");
    ok(p1.ok() && p1.verb == "s" && p1.arg == "old/new",
       ":s/old/new parses — the slash makes the verb token");
    const auto p2 = dxn3::parseCommand(":s no slash");
    ok(!p2.ok() && p2.error.find("no such command") != std::string::npos,
       "a verb s WITHOUT its slashes is no verb at all");
  }

  // 85. the swap's other face + vim's bare number: :sa/old/new makes
  // the WHOLE document the bed (one undo step holds the take); :42 is
  // the goto's absolute form, spelled the way the hand thinks it.
  {
    IdeState a;
    a.lines = {"x one", "mid", "two one x"};
    int touched = 0;
    const int made = dxn3::ideReplaceAll(a, "one", "1", &touched);
    ok(made == 2 && touched == 2,
       "the whole document trades — two on two lines");
    ok(a.lines == std::vector<std::string>{"x 1", "mid", "two 1 x"},
       "every line the bed holds was offered");
    ok(a.touched.size() == 2, "the census covers the document's trade");
    dxn3::Keys uz;
    uz.ctrlZ = true;
    ok(dxn3::ideUndo(a), "one undo holds the whole take");
    IdeState n;
    n.lines = {"nothing"};
    const int none = dxn3::ideReplaceAll(n, "zz", "yy", &touched);
    ok(none == 0 && n.lines[0] == "nothing",
       "a clean document refuses, the words stand");

    const auto g1 = dxn3::parseCommand(":42");
    ok(g1.ok() && g1.verb == "goto" && g1.num == 42.f && !g1.rel,
       "a bare number IS a goto — the vim law");
    const auto g2 = dxn3::parseCommand(":1");
    ok(g2.ok() && g2.num == 1.f, ":1 jumps to the very top");
    const auto g3 = dxn3::parseCommand(":99999");
    ok(g3.ok() || g3.error.find("1..99999") != std::string::npos,
       "the range law holds either way");
    const auto g4 = dxn3::parseCommand(":12x");
    ok(!g4.ok(), "a number with letters is not a line");
    const auto s1 = dxn3::parseCommand(":sa/a/b");
    ok(s1.ok() && s1.verb == "sa" && s1.arg == "a/b",
       ":sa/old/new parses — the other face's token");
    const auto o1 = dxn3::parseCommand(":o game.py");
    ok(o1.ok() && o1.verb == "o" && o1.arg == "game.py",
       ":o is :open in the vim tongue (a file rides)");
    const auto e1 = dxn3::parseCommand(":e");
    ok(e1.ok() && e1.verb == "e" && e1.arg.empty(),
       "a bare :e reopens the ledger's head");
    ok(dxn3::usageHintFor("o").find("vim tongue") != std::string::npos,
       ":o whispers its vim law as you type");
  }

  // 83b. the macro register's session law, restated in the pure world:
  // a restart empties the register (main clears on start)
  {
    IdeState mr;
    mr.macro = {":trim", ":stats"};
    mr.recording = true;
    mr.recording = false;
    mr.recording = true;
    mr.macro.clear();
    ok(mr.recording && mr.macro.empty(),
       "a fresh recording starts from an empty register");
  }

  // 86. the soft wrap: the fold's layout laws (:wrap)
  {
    IdeState ws;                              // the fold OFF: the identity
    ws.lines = {"short", "a longer line of code", ""};
    const dxn3::IdeWrap id = dxn3::ideWrapBuild(ws, 20);
    ok(id.rows == 3 && id.lineFirst[2] == 2 && id.rowOff[1] == 0 &&
           id.rowLine[1] == 1,
       "the fold off is the identity: one line, one row");
    ws.wrap = true;
    ws.lines = {"short", "a longer line", ""};   // every line fits now
    const dxn3::IdeWrap w1 = dxn3::ideWrapBuild(ws, 20);
    ok(w1.rows == 3, "every line that fits paints exactly one row");
    ok(w1.rowLine[2] == 2 && w1.rowOff[2] == 0,
       "the empty line keeps its row (nothing is ever lost)");
    ok(dxn3::ideWrapRowOf(w1, 1, 7) == w1.lineFirst[1],
       "a fitting line's hand rides its only row");
    ws.lines = {"alpha beta gamma"};          // 16 bytes, the fold at 10
    const dxn3::IdeWrap w2 = dxn3::ideWrapBuild(ws, 10);
    ok(w2.rows == 2 && w2.rowOff[1] == 6,
       "the fold breaks after the last space the row can hold");
    ok(dxn3::ideWrapRowOf(w2, 0, 16) == 1 &&
           dxn3::ideWrapRowOf(w2, 0, 0) == 0,
       "rowOf lands the tail on the last row, the head on the first");
    ws.lines = {"aaaaaaaaaaaa"};              // no space in sight
    const dxn3::IdeWrap w3 = dxn3::ideWrapBuild(ws, 8);
    ok(w3.rows == 2 && w3.rowOff[1] == 8,
       "a word longer than the pane takes the honest hard cut");
    ws.lines = {"one two three four five six"};
    const dxn3::IdeWrap w4 = dxn3::ideWrapBuild(ws, 9);
    ok(w4.rows == 4 && w4.rowOff[1] == 8 && w4.rowOff[3] == 19,
       "a long line folds into exactly the rows it needs");
    const dxn3::IdeWrap wf = dxn3::ideWrapBuild(ws, 4);   // the sliver law
    ok(wf.rows == 1 && wf.rowLine[0] == 0,
       "a sliver of a pane keeps the identity (the fold refuses)");
    IdeState hs;                              // the slide sleeps under the fold
    hs.wrap = true;
    hs.lines = {"a line definitely longer than the pane's width"};
    hs.curC = 30;
    dxn3::ideHscroll(hs, 20);
    ok(hs.hcol == 0,
       "the fold sleeps the slide — hcol rests at zero");
    // the ride: a wheel notch under the fold keeps the hand in sight
    IdeState rs;
    rs.wrap = true;
    rs.page = 3;
    for (int i = 0; i < 40; ++i) rs.lines.push_back("word word word word word");
    const dxn3::IdeWrap rw = dxn3::ideWrapBuild(rs, 12);
    rs.top = 0;
    dxn3::ideScroll(rs, 10, &rw);
    ok(rs.top == 10 && rs.curR == rw.rowLine[10],
       "the wheel's ride lands the hand on the view's top row");
  }

  // 87. the hyphen's law + the longest line (the fold's companions)
  {
    IdeState hs;                              // compound names part at the dash
    hs.wrap = true;
    hs.lines = {"left-right-left-right"};     // 21 bytes, the fold at 10
    const dxn3::IdeWrap h1 = dxn3::ideWrapBuild(hs, 10);
    ok(h1.rows == 3 && h1.rowOff[1] == 5,
       "the hyphen breaks the row — compound names part honestly");
    hs.lines = {"just-one"};                  // 8 bytes fits whole at 10
    const dxn3::IdeWrap h2 = dxn3::ideWrapBuild(hs, 10);
    ok(h2.rows == 1,
       "a compound that fits never breaks");
    IdeState ls;                              // the longest line's census
    ls.lines = {"ab", "abcdef", ""};
    ok(dxn3::ideLongestLine(ls) == 6,
       "the longest line speaks the worst offender's length");
    ls.lines = {"", "", ""};
    ok(dxn3::ideLongestLine(ls) == 0,
       "a document of empty lines offends by zero");
  }

  // 88. the eye's walk: visual up/down under the fold
  {
    IdeState es;
    es.wrap = true;
    es.lastTextW = 10;
    es.lines = {"short", "alpha beta gamma", "tail"};
    es.curR = 0;
    es.curC = 3;                          // "sh|ort" — the eye at col 3
    ok(dxn3::ideVisualMove(es, +1) && es.curR == 1 && es.curC == 3,
       "down keeps the eye's column on the row below");
    es.curR = 1;
    es.curC = 16;                         // the folded line's tail row
    ok(dxn3::ideVisualMove(es, -1) && es.curR == 1 && es.curC == 5,
       "up from the tail row keeps the line, the eye clamped to the row's end");
    es.curR = 1;
    es.curC = 6;                          // the continuation's own head
    ok(dxn3::ideVisualMove(es, -1) && es.curR == 1 && es.curC == 0,
       "up from a continuation lands on the line's OWN head");
    es.wrap = false;
    ok(!dxn3::ideVisualMove(es, +1),
       "the fold asleep hands the move to the caller's law");
    es.wrap = true;
    es.curR = 0;
    es.curC = 0;
    ok(!dxn3::ideVisualMove(es, -1),
       "a walk off the document's head is the caller's law too");
  }


  // 89. the crew: many hands, one breath (:crew, the four verbs)
  {
    // the plant: n hands below, same column, clamped honest
    IdeState cs;
    cs.lines = {"alpha", "beta", "gamma delta", "eps"};
    cs.curR = 0;
    cs.curC = 2;
    ok(dxn3::ideCrewPlant(cs, 2) == 2 && cs.crew.size() == 2,
       "planting two hands adds two seats");
    ok(cs.crew[0] == std::pair<int, int>{1, 2} &&
           cs.crew[1] == std::pair<int, int>{2, 2},
       "each hand stands one line below, the eye's column kept");
    ok(dxn3::ideCrewHands(cs) == 3, "the census counts the primary too");
    ok(dxn3::ideCrewPlant(cs, 5) == 1 && dxn3::ideCrewHands(cs) == 4,
       "the document's edge refuses honestly — one line, one hand left");
    // the clamp: a hand past the line's end lands on the honest end
    IdeState ce;
    ce.lines = {"long line", "hi"};
    ce.curR = 0;
    ce.curC = 9;
    ce.crew = {{1, 9}};
    dxn3::ideCrewClamp(ce);
    ok(ce.crew.size() == 1 && ce.crew[0].second == 2,
       "a hand beyond the line's end clamps to the line's end");
    // typing speaks through every hand
    IdeState ts;
    ts.lines = {"aa", "bb"};
    ts.curR = 0;
    ts.curC = 1;
    ts.crew = {{1, 1}};
    dxn3::Keys tk;
    tk.typed = "X";
    dxn3::ideCrewFrame(ts, tk);
    ok(ts.lines[0] == "aXa" && ts.lines[1] == "bXb",
       "typed once, every hand writes");
    ok(ts.curR == 0 && ts.curC == 2 &&
           ts.crew == std::vector<std::pair<int, int>>{{1, 2}},
       "every hand advanced past what it wrote");
    ok(ts.undo.size() == 1 && ts.undo.back().what == "the crew's typing",
       "one restore point, named after the verb");
    // the pair law rides through every hand
    IdeState ps;
    ps.lines = {"()", ""};
    ps.curR = 0;
    ps.curC = 1;
    ps.crew = {{1, 0}};
    dxn3::Keys pk;
    pk.typed = "(";
    dxn3::ideCrewFrame(ps, pk);
    ok(ps.lines[0] == "(())" && ps.lines[1] == "()",
       "an opener carries its closer through every hand");
    // the bite and the join in one breath — independent hands
    IdeState bs;
    bs.lines = {"head", "one", "two", "tail"};
    bs.curR = 1;
    bs.curC = 3;
    bs.crew = {{3, 0}};
    dxn3::Keys bk;
    bk.back = true;
    dxn3::ideCrewFrame(bs, bk);
    ok(bs.lines[0] == "head" && bs.lines[1] == "on" &&
           bs.lines[2] == "twotail",
       "backspace bites one hand while the other joins the tail");
    ok(bs.curR == 1 && bs.curC == 2 &&
           bs.crew == std::vector<std::pair<int, int>>{{2, 3}},
       "the joiner's hand stands at the seam, the biter behind its bite");
    // the seam's remap: a hand landed on a row another hand's join
    // erases rides the seam — row AND column remapped honestly
    IdeState rs;
    rs.lines = {"KK", "abcd"};
    rs.curR = 1;
    rs.curC = 0;
    rs.crew = {{1, 3}};
    dxn3::Keys rk;
    rk.back = true;
    dxn3::ideCrewFrame(rs, rk);
    ok(rs.lines.size() == 1 && rs.lines[0] == "KKabd" &&
           rs.crew == std::vector<std::pair<int, int>>{{0, 4}},
       "a hand landed on the merged row rides the seam");
    // enter through hands — the second split shifts the first's landing
    IdeState es;
    es.lines = {"ab", "cd"};
    es.curR = 0;
    es.curC = 2;
    es.crew = {{1, 2}};
    dxn3::Keys ek;
    ek.enter = true;
    dxn3::ideCrewFrame(es, ek);
    ok(es.lines.size() == 4 && es.lines[0] == "ab" && es.lines[1] == "" &&
           es.lines[2] == "cd" && es.lines[3] == "",
       "enter splits through every hand, highest first");
    ok(es.curR == 1 && es.curC == 0 &&
           es.crew == std::vector<std::pair<int, int>>{{3, 0}},
       "every hand takes its own new line, shifts honestly ridden");
    // undo brings the hands AND the document back
    IdeState us;
    us.lines = {"aa", "bb"};
    us.curR = 0;
    us.curC = 1;
    us.crew = {{1, 1}};
    dxn3::Keys uk;
    uk.typed = "X";
    dxn3::ideCrewFrame(us, uk);
    ok(dxn3::ideUndo(us) && us.lines[0] == "aa" && us.lines[1] == "bb" &&
           us.crew == std::vector<std::pair<int, int>>{{1, 1}},
       "undo restores the document AND the crew");
    // the dissolve: movement and esc bow the crew out
    IdeState ds;
    ds.lines = {"a", "b"};
    ds.curR = 0;
    ds.curC = 0;
    ds.crew = {{1, 0}};
    dxn3::Keys mk;
    mk.aRight = true;
    dxn3::ideKey(ds, mk);
    ok(ds.crew.empty(), "a movement frame dissolves the crew");
    IdeState qs;
    qs.lines = {"a", "b"};
    qs.curR = 0;
    qs.curC = 0;
    qs.crew = {{1, 0}};
    dxn3::Keys qk;
    qk.esc = true;
    dxn3::ideKey(qs, qk);
    ok(qs.crew.empty(), "esc bows the crew out");
    // the engine's empty breaths never dissolve — the crew lives
    // between keystrokes
    IdeState vs;
    vs.lines = {"a", "b"};
    vs.curR = 0;
    vs.curC = 0;
    vs.crew = {{1, 0}};
    dxn3::Keys vk;                          // no key at all this frame
    dxn3::ideKey(vs, vk);
    ok(dxn3::ideCrewHands(vs) == 2,
       "an empty frame — the engine's breath — never dissolves the crew");
  }


  // 90. the transpose: ctrl+T — the two neighbors trade places
  {
    IdeState ts;
    ts.lines = {"teh"};
    ts.curR = 0;
    ts.curC = 3;                          // the hand after the typo
    ok(dxn3::ideTranspose(ts) && ts.lines[0] == "the" && ts.curC == 3,
       "the hand at the tail: the last two trade, the hand stays past them");
    ts.curC = 1;                          // the hand ON the 'h'
    ok(dxn3::ideTranspose(ts) && ts.lines[0] == "teh",
       "the hand on a char swaps it with the one ahead");
    ok(ts.curC == 3, "the hand lands after the transposed pair");
    ts.curC = 0;                          // the head: the first pair trades
    ok(dxn3::ideTranspose(ts) && ts.lines[0] == "eth",
       "the hand at the head swaps the first pair");
    IdeState rs;
    rs.lines = {"x"};
    rs.curR = 0;
    rs.curC = 0;
    ok(!dxn3::ideTranspose(rs) && rs.lines[0] == "x",
       "a line too short to hold a pair refuses honestly");
    IdeState us;
    us.lines = {"teh"};
    us.curR = 0;
    us.curC = 3;
    dxn3::Keys uk;
    uk.transpose = true;
    dxn3::ideKey(us, uk);
    ok(us.lines[0] == "the" && !us.undo.empty() &&
           us.undo.back().what == "transpose",
       "the trade rides one honest undo step, named");
    ok(dxn3::ideUndo(us) && us.lines[0] == "teh",
       "undo restores the untraded line");
  }


  // 91. the honest home: home toggles the first non-blank and the head
  {
    IdeState hs;
    hs.lines = {"    hello there"};
    hs.curR = 0;
    hs.curC = 9;
    dxn3::Keys h1;
    h1.home = true;
    dxn3::ideKey(hs, h1);
    ok(hs.curC == 4, "home lands the hand on the line's first non-blank");
    dxn3::Keys h2;
    h2.home = true;
    dxn3::ideKey(hs, h2);
    ok(hs.curC == 0, "already there, the head");
    dxn3::Keys h3;
    h3.home = true;
    dxn3::ideKey(hs, h3);
    ok(hs.curC == 4, "at the head, back to the first non-blank");
    IdeState bs;
    bs.lines = {"   "};
    bs.curR = 0;
    bs.curC = 0;
    dxn3::Keys h4;
    h4.home = true;
    dxn3::ideKey(bs, h4);
    ok(bs.curC == 0, "a blank line's home is the head, honestly");
  }


  // 92. the census: :count speaks the find's own law
  {
    IdeState cs;
    cs.lines = {"abab", "ba"};
    cs.findCase = false;
    ok(static_cast<int>(dxn3::ideFindAll(cs, "ab").size()) == 2,
       "the census counts non-overlapping, like every editor");
    cs.findCase = true;
    ok(static_cast<int>(dxn3::ideFindAll(cs, "AB").size()) == 0,
       "case-honest: the shout finds nothing the page never shouted");
    cs.findCase = false;
    ok(static_cast<int>(dxn3::ideFindAll(cs, "AB").size()) == 2,
       "case sleeps: the shout finds the whisper's work");
  }


  // 93. the case cycle: ctrl+U — the word's coat, one breath apart
  {
    IdeState cs;
    cs.lines = {"hello"};
    cs.curR = 0;
    cs.curC = 1;                          // the hand ON the word
    ok(dxn3::ideCycleCase(cs) && cs.lines[0] == "HELLO",
       "the whisper shouts: hello becomes HELLO");
    ok(cs.curC == 1, "the coat never moves a letter — the hand keeps its seat");
    ok(dxn3::ideCycleCase(cs) && cs.lines[0] == "Hello",
       "the shout titles: HELLO becomes Hello");
    ok(dxn3::ideCycleCase(cs) && cs.lines[0] == "hello",
       "the title whispers: Hello becomes hello — the wheel closes");
    IdeState bs;                          // the word BEHIND the hand
    bs.lines = {"foo bar"};
    bs.curR = 0;
    bs.curC = 7;                          // the hand past the tail
    ok(dxn3::ideCycleCase(bs) && bs.lines[0] == "foo BAR",
       "the hand in the open cycles the word behind it");
    IdeState as_;                         // the word AHEAD of the hand
    as_.lines = {"  hi"};
    as_.curR = 0;
    as_.curC = 0;
    ok(dxn3::ideCycleCase(as_) && as_.lines[0] == "  HI",
       "a hand before the words cycles the word ahead");
    IdeState vs;                          // the two-coat life: V2
    vs.lines = {"v2"};
    vs.curR = 0;
    vs.curC = 0;
    ok(dxn3::ideCycleCase(vs) && vs.lines[0] == "V2",
       "the whisper shouts through the digit: v2 becomes V2");
    ok(dxn3::ideCycleCase(vs) && vs.lines[0] == "v2",
       "a coat that paints nothing bows out — V2 lands back at v2");
    IdeState ns;                          // digits and nails wear no coat
    ns.lines = {"123"};
    ns.curR = 0;
    ns.curC = 1;
    ok(!dxn3::ideCycleCase(ns) && ns.lines[0] == "123" && ns.undo.empty(),
       "a word with no letter refuses honestly — no undo, no dirt");
    IdeState es;                          // the empty line refuses
    es.lines = {"", "x"};
    es.curR = 0;
    es.curC = 0;
    ok(!dxn3::ideCycleCase(es) && es.undo.empty(),
       "an empty line refuses honestly too");
    IdeState us;                          // the named undo step
    us.lines = {"hello"};
    us.curR = 0;
    us.curC = 0;
    dxn3::Keys uk;
    uk.caseCycle = true;
    dxn3::ideKey(us, uk);
    ok(us.lines[0] == "HELLO" && !us.undo.empty() &&
           us.undo.back().what == "case cycle",
       "the cycle rides one honest undo step, named");
    ok(dxn3::ideUndo(us) && us.lines[0] == "hello" && us.curC == 0,
       "undo restores the uncoated word and the seat");
  }


  // 94. the crew's coats: ctrl+U through every hand
  {
    IdeState cs;
    cs.lines = {"alpha beta", "gamma delta"};
    cs.curR = 0;
    cs.curC = 1;                          // the primary rides "alpha"
    cs.crew = {{1, 2}};                   // one hand below rides "gamma"
    dxn3::Keys ck;
    ck.caseCycle = true;
    dxn3::ideKey(cs, ck);
    ok(cs.lines[0] == "ALPHA beta" && cs.lines[1] == "GAMMA delta",
       "one breath coats every hand's word");
    ok(cs.crew.size() == 1,
       "the crew survives the cycle — it edits through it");
    ok(!cs.undo.empty() && cs.undo.back().what == "case cycle",
       "the crew's coats ride ONE named undo step");
    ok(dxn3::ideUndo(cs) && cs.lines[0] == "alpha beta" &&
           cs.lines[1] == "gamma delta",
       "one undo restores every hand's word");
    IdeState ds;                          // a hand that cannot paint
    ds.lines = {"alpha", "123"};
    ds.curR = 0;
    ds.curC = 0;
    ds.crew = {{1, 1}};                   // riding bare digits
    dxn3::Keys dk;
    dk.caseCycle = true;
    dxn3::ideKey(ds, dk);
    ok(ds.lines[0] == "ALPHA" && ds.lines[1] == "123",
       "a hand that cannot paint refuses alone — the others paint");
    IdeState es;                          // two hands, one word
    es.lines = {"echo"};
    es.curR = 0;
    es.curC = 0;
    es.crew = {{0, 3}};
    dxn3::Keys ek;
    ek.caseCycle = true;
    dxn3::ideKey(es, ek);
    ok(es.lines[0] == "ECHO",
       "two hands on one word take one coat, not two");
  }


  // 95. the selection's coat: ctrl+U over a live span
  {
    IdeState ss;
    ss.lines = {"alpha beta gamma"};
    ss.curR = 0;
    ss.curC = 0;
    ss.anchorR = 0;
    ss.anchorC = 11;                      // the span holds "alpha beta"
    dxn3::Keys sk;
    sk.caseCycle = true;
    dxn3::ideKey(ss, sk);
    ok(ss.lines[0] == "ALPHA BETA gamma",
       "the span coats every word it holds whole");
    ok(ss.anchorR < 0, "the breath drops the selection — the frame's own");
    ok(!ss.undo.empty() && ss.undo.back().what == "case cycle",
       "the span's coats ride ONE named undo step");
    ok(dxn3::ideUndo(ss) && ss.lines[0] == "alpha beta gamma",
       "one undo restores the whole span");
    IdeState cs;                          // a word the span CUTS
    cs.lines = {"alpha beta"};
    cs.curR = 0;
    cs.curC = 0;
    cs.anchorR = 0;
    cs.anchorC = 8;                       // the span holds "alpha be"
    dxn3::Keys ck;
    ck.caseCycle = true;
    dxn3::ideKey(cs, ck);
    ok(cs.lines[0] == "ALPHA beta",
       "a word the span cuts is left honest — only whole words paint");
    IdeState ms;                          // a multi-row span
    ms.lines = {"alpha", "beta", "gamma"};
    ms.curR = 2;
    ms.curC = 5;                          // the hand past "gamma"
    ms.anchorR = 0;
    ms.anchorC = 0;                       // every word of all three rows
    dxn3::Keys mk;
    mk.caseCycle = true;
    dxn3::ideKey(ms, mk);
    ok(ms.lines[0] == "ALPHA" && ms.lines[1] == "BETA" &&
           ms.lines[2] == "GAMMA",
       "a multi-row span coats every row it holds");
    IdeState ds;                          // a span over bare digits
    ds.lines = {"123 456"};
    ds.curR = 0;
    ds.curC = 0;
    ds.anchorR = 0;
    ds.anchorC = 7;
    dxn3::Keys dk;
    dk.caseCycle = true;
    dxn3::ideKey(ds, dk);
    ok(ds.lines[0] == "123 456" && ds.undo.empty() && ds.anchorR < 0,
       "a span with no coatable word refuses honestly — and still drops");
  }


  // 96. the census's question: :changes <word>
  {
    IdeState qs;
    qs.lines = {"alpha here", "beta there", "gamma alpha", "delta"};
    qs.touched = {0, 1, 2};               // three lines carry the census
    qs.findCase = false;                  // the beginner way: case sleeps
    const auto a = dxn3::ideChangesAsk(qs, "alpha");
    ok(a.size() == 2 && a[0] == 0 && a[1] == 2,
       "the question answers with the touched lines that speak the word");
    const auto b = dxn3::ideChangesAsk(qs, "ALPHA");
    ok(b.size() == 2,
       "case sleeps: the shout finds the whisper's touched work");
    qs.findCase = true;
    const auto c = dxn3::ideChangesAsk(qs, "ALPHA");
    ok(c.empty(),
       "case-honest: the shout finds nothing the page never shouted");
    const auto d = dxn3::ideChangesAsk(qs, "delta");
    ok(d.empty(),
       "an untouched line never answers the census's question");
    const auto e = dxn3::ideChangesAsk(qs, "");
    ok(e.empty(), "an empty question refuses honestly");
  }


  // 97. the diff census: the page against the disk
  {
    const std::vector<std::string> disk = {"alpha", "beta", "gamma"};
    const auto same = dxn3::ideDiffCensus(disk, disk);
    ok(same && same->same(), "an honest page agrees with its disk");
    const std::vector<std::string> midAdd = {"alpha", "new", "beta", "gamma"};
    const auto add = dxn3::ideDiffCensus(disk, midAdd);
    ok(add && add->added == 1 && add->changed == 0 && add->removed == 0 &&
           add->addedAt[0] == 2,
       "a page line the disk never held is an addition, at its gutter line");
    const std::vector<std::string> midCut = {"alpha", "gamma"};
    const auto cut = dxn3::ideDiffCensus(disk, midCut);
    ok(cut && cut->removed == 1 && cut->removedAt[0] == 2,
       "a disk line the page let go is a removal, where it once stood");
    const std::vector<std::string> rewrite = {"alpha", "BETA", "gamma"};
    const auto ch = dxn3::ideDiffCensus(disk, rewrite);
    ok(ch && ch->changed == 1 && ch->added == 0 && ch->removed == 0 &&
           ch->changedAt[0] == 2,
       "a rewritten line is one change, not a pair of voices");
    const std::vector<std::string> mix = {"ALPHA", "beta", "delta", "extra"};
    const auto mx = dxn3::ideDiffCensus(disk, mix);
    ok(mx && mx->changed == 2 && mx->added == 1 && mx->removed == 0 &&
           mx->changedAt[0] == 1 && mx->changedAt[1] == 3,
       "an interleaved edit pairs every drop beside its add — two changes");
    const std::vector<std::string> grow = {"beta", "gamma", "zeta"};
    const auto gr = dxn3::ideDiffCensus(disk, grow);
    ok(gr && gr->removed == 1 && gr->added == 1,
       "a block with no pair left speaks the extras honestly");
    const std::vector<std::string> blank;
    const auto born = dxn3::ideDiffCensus(blank, disk);
    ok(born && born->added == 3 && born->removed == 0,
       "a disk that never held the page hears every line as an addition");
    const std::vector<std::string> bigA(2001, "x");
    const std::vector<std::string> bigB(2001, "y");
    ok(!dxn3::ideDiffCensus(bigA, bigB),
       "a bed too big to think refuses honestly");
  }


  // 98. the drift: :diff's memory, worn amber on the rail
  {
    IdeState ds;
    dxn3::IdeDiffReport rep;
    rep.addedAt = {5, 2};                 // unsorted on purpose
    rep.changedAt = {2};                  // line 2 twice: add + change meet
    rep.removedAt = {9};                  // a removal wears no tick
    dxn3::ideDriftStore(ds, rep);
    ok(ds.drift.size() == 2 && ds.drift[0] == 1 && ds.drift[1] == 4,
       "the drift stores the page's lines, sorted and unique, 0-based");
    ok(dxn3::ideDriftHas(ds, 1) && dxn3::ideDriftHas(ds, 4) &&
           !dxn3::ideDriftHas(ds, 0) && !dxn3::ideDriftHas(ds, 8) &&
           !dxn3::ideDriftHas(ds, -1),
       "the rail's ask answers honestly, edges included");
    dxn3::ideDriftClear(ds);
    ok(ds.drift.empty() && !dxn3::ideDriftHas(ds, 1),
       "a save or a fresh page sweeps the amber away");
  }

  // 50. the turn — rot finally renders. The wire carried rot and spin
  // forever while both rasters ignored them: saws span in the data and
  // stood still on the glass. Pin the shared math, then render a body
  // through a real PNG and confirm the poster tells the same story.
  {
    const dxn3::Turn id(0.f, 100.f, 50.f);
    ok(id.toLocalX(107.f, 50.f) == 107.f && id.toLocalY(107.f, 50.f) == 50.f,
       "turn: zero degrees is the honest identity");
    const dxn3::Turn q(90.f, 100.f, 50.f);            // y grows downward
    ok(std::abs(q.toLocalX(110.f, 50.f) - 100.f) < 1e-3f &&
           std::abs(q.toLocalY(110.f, 50.f) - 40.f) < 1e-3f,
       "turn: at 90° the world +x arm asks for the local -y (up on screen)");
    float bx0, by0, bx1, by1;
    q.extent(90.f, 40.f, 110.f, 60.f, bx0, by0, bx1, by1);
    const float w = bx1 - bx0, h = by1 - by0;
    ok(w > 19.9f && w < 20.1f && h > 19.9f && h < 20.1f &&
           std::abs((bx0 + bx1) / 2.f - 100.f) < 0.5f &&
           std::abs((by0 + by1) / 2.f - 50.f) < 0.5f,
       "turn: a square turns onto itself at 90° — same extent, same center");
    const dxn3::Turn d(45.f, 0.f, 0.f);
    d.extent(-10.f, -10.f, 10.f, 10.f, bx0, by0, bx1, by1);
    ok(bx1 - bx0 > 28.f && bx1 - bx0 < 28.3f,
       "turn: 45° grows the extent to the diagonal (√2·20)");
    // end-to-end: a spinning hazard poses for the poster without a lie
    Scene rs;
    rs.entities.push_back(mk("saw", 200, 200, 40, 40, "#fb7185"));
    rs.entities[0].tag = "hazard";
    rs.entities[0].rot = 30.f;
    Game rg(std::move(rs));
    rg.update(0.5f, {});                    // spin? none — rot stays posed
    ok(rg.scene.entities[0].rot == 30.f,
       "turn: a posed rot holds still when nothing spins it");
    rg.scene.entities[0].spin = 100.f;      // 100 deg/s
    rg.scene.entities[0].rot = 0.f;
    for (int i = 0; i < 15; ++i) rg.update(1.f / 60.f, {});   // a quarter
    ok(std::abs(rg.scene.entities[0].rot - 25.f) < 1.f,
       "turn: spin winds rot at degrees per second (15 ticks → 25°)");
    const std::string png = "/tmp/dxn3_turn_pin.png";
    const std::string err = dxn3::shootPNG(png, rg);
    ok(err.empty() && std::filesystem::file_size(png) > 1000,
       "turn: the poster renders a turned body as a real PNG");
  }


  // 51. the whitespace hygiene: :squeeze, :retab and :ws — the
  // margin's honest tools. Shape laws, pin laws, undo laws.
  {
    IdeState h2;
    h2.lines = {"a", "", " ", "", "", "b", "", "", "", "c"};
    const int fell = dxn3::ideSqueezeSel(h2);
    ok(fell == 5, "squeeze fells five of seven blanks (two runs keep two)");
    ok(h2.lines.size() == 5 && h2.lines[1].empty() &&
           h2.lines[2] == "b" && h2.lines[3].empty() && h2.lines[4] == "c",
       "each run of blanks breathes down to exactly one");
    ok(!h2.undo.empty() && h2.undo.back().what == "squeeze",
       "the breathe-down is one restore point, named squeeze");
    // the pin law: mark 1 rides home, mark 4 (on a fallen blank) DIES,
    // mark 9 (inside the range, on kept ink) maps to its new home
    IdeState h4;
    h4.lines = {"a", "", " ", "", "", "b", "", "", "", "c"};
    h4.marks = {0, 1, 4, 9};
    dxn3::ideSqueezeSel(h4);
    ok(h4.marks.size() == 3 && h4.marks[0] == 0 && h4.marks[1] == 1 &&
           h4.marks[2] == 4,
       "the pins speak uniq's law: ride home, or die with the fallen");

    IdeState h5;
    h5.lines = {"\tone", "  \ttwo", "\t\tthree", "clean", "mid\ttab"};
    const int widened = dxn3::ideRetabSel(h5);
    ok(widened == 3, "retab widens three indents (the mid-line tab rests)");
    ok(h5.lines[0] == "    one" && h5.lines[1] == "      two" &&
           h5.lines[2] == "        three",
       "every leading tab is four spaces; mixed indents keep their cols");
    ok(h5.lines[3] == "clean" && h5.lines[4] == "mid\ttab",
       "ink after the indent is untouched");

    IdeState h6;
    h6.lines = {"x  ", "\ty", std::string(90, 'q'), "ok"};
    const auto c = dxn3::ideWsCensus(h6);
    ok(c.trailing == 1 && c.tabs == 1 && c.long_ == 1,
       "the census counts trailing, tabs and the 80-column law");
    ok(h6.lines[0] == "x  ", "the census is a mirror — it changes nothing");

    // 52. the bracket's twin — :match walks to the other half,
    // quote-honest, cross-line, and honest about never finding one
    {
      IdeState m1;
      m1.lines = {"f(a(b))"};
      m1.curR = 0;
      m1.curC = 1;
      const auto t1 = dxn3::ideMatchBracket(m1);
      ok(t1.found && t1.row == 0 && t1.col == 6,
         "match: the opener's twin is the outer closer");
      m1.curC = 6;
      const auto t2 = dxn3::ideMatchBracket(m1);
      ok(t2.found && t2.row == 0 && t2.col == 1,
         "match: the closer walks back the same road");
      IdeState m2;
      m2.lines = {"x = (\"(\", 1)"};      // the '(' in the string is ink
      m2.curR = 0;
      m2.curC = 4;
      const auto t3 = dxn3::ideMatchBracket(m2);
      ok(t3.found && t3.col == 11,
         "match: a bracket inside a string literal is ink, not structure");
      IdeState m3;
      m3.lines = {"g = (1 +", "    2)"};
      m3.curR = 0;
      m3.curC = 4;
      const auto t4 = dxn3::ideMatchBracket(m3);
      ok(t4.found && t4.row == 1 && t4.col == 5,
         "match: the walk crosses lines without flinching");
      IdeState m4;
      m4.lines = {"(o"};
      m4.curR = 0;
      m4.curC = 0;
      const auto t5 = dxn3::ideMatchBracket(m4);
      ok(!t5.found, "match: an unclosed bracket says so honestly");
      IdeState m5;
      m5.lines = {"quiet"};
      m5.curR = 0;
      m5.curC = 0;
      ok(!dxn3::ideMatchBracket(m5).found,
         "match: no bracket ahead is honest silence too");
    }
  }

  // 99. the glow: an author's halo — parsed, patched, round-tripped
  {
    Scene s = dxn3::Game::fromJson(
        R"({"name":"glow","entities":[{"name":"gem","shape":"circle","x":10,"y":20,"w":22,"h":22,"color":"#facc15","glow":7}]})");
    ok(!s.entities.empty() && s.entities[0].glow == 7.f,
       "fromJson reads a glow halo");
    Scene s0 = dxn3::Game::fromJson(
        R"({"name":"plain","entities":[{"name":"p","x":0,"y":0}]})");
    ok(s0.entities.empty() || s0.entities[0].glow == 0.f,
       "no glow field means no halo");
    ok(dxn3::Game::toJson(s).find("\"glow\": 7") != std::string::npos,
       "toJson writes the glow back");
    Game g(s);
    HostFrame f;
    f.frame = true;
    f.set = dxn3::json::parse(R"([{"name":"gem","glow":3}])").value();
    dxn3::applyFrame(g, f);
    ok(g.scene.entities[0].glow == 3.f,
       "a wire patch moves the glow (a pulse is a patch)");
    ok(dxn3::shootPNG("/tmp/dxn3_glow_a.png", g).empty(),
       "a glowing scene renders");
    dxn3::shootPNG("/tmp/dxn3_glow_b.png", g);
    auto slurp = [](const char* p) {
      std::FILE* fp = std::fopen(p, "rb");
      std::string b;
      char buf[8192];
      size_t r;
      if (fp) {
        while ((r = std::fread(buf, 1, sizeof buf, fp)) > 0) b.append(buf, r);
        std::fclose(fp);
      }
      return b;
    };
    ok(slurp("/tmp/dxn3_glow_a.png") == slurp("/tmp/dxn3_glow_b.png"),
       "the halo is a pure function of state (byte-identical)");
  }

  if (fails == 0) {
    std::println("native selftest: all green ({} assertion groups)", n);
    return 0;
  }
  std::println(stderr, "native selftest: {} of {} FAILED", fails, n);
  return 1;
}
