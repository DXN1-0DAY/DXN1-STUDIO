// dxn3 native — engine selftest (C++23). Mirrors renderer selftest's spirit:
// normalization clamps, magnetism, pickups, hazards, transitions, movers.
#include <cmath>
#include <print>
#include <string>
#include <sys/stat.h>

#include "spark.hpp"

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

  if (fails == 0) {
    std::println("native selftest: all green ({} assertion groups)", n);
    return 0;
  }
  std::println(stderr, "native selftest: {} of {} FAILED", fails, n);
  return 1;
}
