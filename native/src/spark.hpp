// dxn3 native — the Spark engine core in C++23.
// A faithful port of the renderer's spark.js semantics: AABB platformer
// physics, movers with ping-pong paths + rider carry, coins with scene
// magnetism, hazards with respawn+shake, goal -> next-scene transitions,
// camera follow + zoom + decay shake, score/time HUD.
#pragma once
#include <expected>
#include <string>
#include <vector>

namespace dxn3 {

struct Vec2 {
  float x = 0, y = 0;
};

struct Entity {
  std::string name, tag, text;
  float x = 0, y = 0, w = 32, h = 32;
  float vx = 0, vy = 0;
  std::string color = "#8b5cf6";
  std::string color2;                 // gradient end (fill == "gradient")
  std::string fill = "solid";         // solid | gradient
  std::string shape = "rect";         // rect | circle | tri | text
  float rot = 0, spin = 0, tsize = 20;
  float glow = 0;                     // halo radius in px (0 = none);
                                      // circles ring, the rest rect-aura
  float flash = 0;                    // hit-flash: 1 = all white, decays
                                      // 4/s in update; set-patchable
  float alpha = 1;                    // opacity 0..1: blends the body toward
                                      // the scene bg (ghosts, fog, glass)
  std::vector<Vec2> path;             // mover waypoints (world px)
  float pathSpeed = 60;
  bool alive = true;

  // runtime state
  int pathIdx = 0;
  int pathDir = 1;
  Vec2 prev{x, y};                    // position last tick (rider carry delta)
  float cx() const { return x + w / 2; }
  float cy() const { return y + h / 2; }
};

struct Camera {
  float x = 0, y = 0, zoom = 1;
};

struct Scene {
  std::string name = "scene";
  std::string bg = "#0b0e1a";
  std::string next;                   // goal -> load this scene
  float gravity = 1500;
  float magnet = 0;                   // coin magnet radius, px (0 = off)
  Camera camera;
  std::vector<Entity> entities;
};

struct Input {
  bool left = false, right = false, jump = false;
};

struct LoadError {
  std::string path, detail;
};

class Game {
public:
  static constexpr float RUN_MAX = 330;     // px/s
  static constexpr float RUN_ACCEL = 2300;
  static constexpr float GROUND_FRICTION = 1900;
  static constexpr float AIR_FRICTION = 220;
  static constexpr float JUMP_VY = -620;
  static constexpr float MAGNET_PULL = 640; // px/s at zero distance

  Scene scene;
  int score = 0;
  float time = 0;
  std::string msg;                          // transient HUD message
  float msgT = 0;                           // seconds left on the message
  float flash = 0;                          // white flash 0..1
  float shakeT = 0, shakeP = 0, shakeD = 1; // camera shake (decay over D)
  bool transLocked = false;                 // one transition per goal touch
  std::string pendingNext;                  // consumed by the shell on load

  explicit Game(Scene s);

  // fixed-timestep tick; dt in seconds (clamped internally to 1/30)
  void update(float dt, const Input& in);

  void shake(float power = 8, float dur = 0.35);
  void say(std::string m, float secs = 1.6);
  void reset();                             // back to spawn, keep score/time

  Vec2 spawn() const { return spawn_; }
  float worldBottom() const;
  float worldRight() const;
  const Entity* player() const;

  static bool overlap(const Entity& a, const Entity& b) {
    return a.x < b.x + b.w && a.x + a.w > b.x &&
           a.y < b.y + b.h && a.y + a.h > b.y;
  }

  // scene I/O + normalization
  static std::expected<Scene, LoadError> loadScene(const std::string& path);
  static Scene normalizeScene(const Scene& in);
  static Scene fromJson(const std::string& text);   // throws-free: clamps junk
  static std::string toJson(const Scene& s);        // .dxn1.json round-trip
  // atomic-ish save with a git-style safety net: the previous file
  // becomes <path>.bak before the new bytes land. ""-free on success:
  // returns the error detail, or "" when saved.
  static std::string saveScene(const std::string& path, const Scene& s);

  int coinsTotal() const {
    int n = 0;
    for (const auto& e : scene.entities) if (e.tag == "coin") ++n;
    return n;
  }

private:
  Vec2 spawn_{90, 300};
  bool jumpHeld_ = false;

  void stepPlayer(float dt, const Input& in);
  void stepMovers(float dt);
  void stepCoins(float dt);
  void stepTags(float dt);
  void stepCamera(float dt);
  Entity* entity(std::string_view tag);
  void respawn(const char* why);
};

} // namespace dxn3
