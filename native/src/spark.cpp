// dxn3 native — Spark engine core implementation (C++23).
#include "spark.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <ranges>
#include <sstream>

#include "json.hpp"

namespace dxn3 {

using json::Value;

static float clampf(float v, float lo, float hi) {
  return std::min(hi, std::max(lo, v));
}

static std::string hex_or(const std::string& c, const char* fallback) {
  return (c.size() >= 7 && c[0] == '#') ? c : fallback;
}

// ---------------------------------------------------------------- scene I/O

Scene Game::fromJson(const std::string& text) {
  Scene s;
  auto root = json::parse(text);
  if (!root) return s;                       // honest junk-in -> normalized defaults
  const Value& r = *root;
  if (!r.is(json::Kind::Obj)) return s;

  s.name = r.at("name").str_or(s.name);
  s.bg = hex_or(r.at("bg").str_or(s.bg), "#0b0e1a");
  s.next = r.at("next").str_or("");
  s.gravity = static_cast<float>(r.at("gravity").num_or(1500));
  s.magnet = static_cast<float>(r.at("magnet").num_or(0));

  const Value& cam = r.at("camera");
  if (cam.is(json::Kind::Obj)) {
    s.camera.x = static_cast<float>(cam.at("x").num_or(0));
    s.camera.y = static_cast<float>(cam.at("y").num_or(0));
    s.camera.zoom = static_cast<float>(cam.at("zoom").num_or(1));
  }

  const Value& ents = r.at("entities");
  if (ents.is(json::Kind::Arr)) {
    for (const Value& e : ents.arr) {
      if (!e.is(json::Kind::Obj)) continue;
      Entity en;
      en.name = e.at("name").str_or("");
      en.tag = e.at("tag").str_or("");
      en.text = e.at("text").str_or("");
      en.x = static_cast<float>(e.at("x").num_or(0));
      en.y = static_cast<float>(e.at("y").num_or(0));
      en.w = static_cast<float>(e.at("w").num_or(32));
      en.h = static_cast<float>(e.at("h").num_or(32));
      en.color = hex_or(e.at("color").str_or("#8b5cf6"), "#8b5cf6");
      const std::string c2 = e.at("color2").str_or("");
      if (c2.size() >= 7 && c2[0] == '#') { en.color2 = c2; en.fill = "gradient"; }
      en.fill = e.at("fill").str_or(en.fill);
      en.shape = e.at("shape").str_or(en.shape);
      en.rot = static_cast<float>(e.at("rot").num_or(0));
      en.spin = static_cast<float>(e.at("spin").num_or(0));
      en.tsize = static_cast<float>(e.at("tsize").num_or(20));
      en.glow = static_cast<float>(e.at("glow").num_or(0));
      en.flash = static_cast<float>(e.at("flash").num_or(0));
      en.alpha = static_cast<float>(e.at("alpha").num_or(1));
      en.pathSpeed = static_cast<float>(e.at("pspeed").num_or(60));
      const Value& path = e.at("path");
      if (path.is(json::Kind::Arr)) {
        for (const Value& p : path.arr) {
          if (!p.is(json::Kind::Obj)) continue;
          en.path.push_back({static_cast<float>(p.at("x").num_or(en.x)),
                             static_cast<float>(p.at("y").num_or(en.y))});
        }
      }
      if (e.at("alive").is(json::Kind::Bool)) en.alive = e.at("alive").b;
      s.entities.push_back(std::move(en));
    }
  }
  return s;
}

std::string Game::toJson(const Scene& s) {
  auto esc = [](const std::string& in) {
    std::string out;
    for (char ch : in) {
      switch (ch) {
        case '"': out += "\\\""; break;
        case '\\': out += "\\\\"; break;
        case '\n': out += "\\n"; break;
        default: out += ch;
      }
    }
    return out;
  };
  std::ostringstream o;
  o << "{\n  \"name\": \"" << esc(s.name) << "\",\n";
  o << "  \"bg\": \"" << esc(s.bg) << "\",\n";
  o << "  \"gravity\": " << static_cast<int>(s.gravity) << ",\n";
  if (s.magnet > 0) o << "  \"magnet\": " << static_cast<int>(s.magnet) << ",\n";
  if (!s.next.empty()) o << "  \"next\": \"" << esc(s.next) << "\",\n";
  o << "  \"camera\": { \"x\": " << static_cast<int>(s.camera.x)
    << ", \"y\": " << static_cast<int>(s.camera.y)
    << ", \"zoom\": " << s.camera.zoom << " },\n";
  o << "  \"entities\": [\n";
  for (size_t i = 0; i < s.entities.size(); ++i) {
    const Entity& e = s.entities[i];
    o << "    { \"name\": \"" << esc(e.name) << "\"";
    if (!e.tag.empty()) o << ", \"tag\": \"" << esc(e.tag) << "\"";
    o << ", \"x\": " << static_cast<int>(e.x) << ", \"y\": " << static_cast<int>(e.y)
      << ", \"w\": " << static_cast<int>(e.w) << ", \"h\": " << static_cast<int>(e.h);
    o << ", \"color\": \"" << esc(e.color) << "\"";
    if (e.fill == "gradient" && !e.color2.empty())
      o << ", \"color2\": \"" << esc(e.color2) << "\", \"fill\": \"gradient\"";
    if (e.shape != "rect") o << ", \"shape\": \"" << esc(e.shape) << "\"";
    if (!e.text.empty()) o << ", \"text\": \"" << esc(e.text) << "\", \"tsize\": "
                           << static_cast<int>(e.tsize);
    if (e.rot != 0) o << ", \"rot\": " << e.rot;
    if (e.spin != 0) o << ", \"spin\": " << e.spin;
    if (e.glow > 0) o << ", \"glow\": " << e.glow;
    if (e.flash > 0) o << ", \"flash\": " << e.flash;
    if (e.alpha < 1) o << ", \"alpha\": " << e.alpha;
    if (!e.path.empty()) {
      o << ", \"path\": [";
      for (size_t j = 0; j < e.path.size(); ++j) {
        o << "{ \"x\": " << static_cast<int>(e.path[j].x)
          << ", \"y\": " << static_cast<int>(e.path[j].y) << "}"
          << (j + 1 < e.path.size() ? ", " : "");
      }
      o << "], \"pspeed\": " << static_cast<int>(e.pathSpeed);
    }
    o << " }" << (i + 1 < s.entities.size() ? "," : "") << "\n";
  }
  o << "  ]\n}\n";
  return o.str();
}

std::string Game::saveScene(const std::string& path, const Scene& s) {
  namespace fs = std::filesystem;
  const std::string body = toJson(s);
  std::error_code ec;
  if (fs::exists(path, ec)) {
    fs::rename(path, path + ".bak", ec);          // the old bytes survive
    if (ec) return "cannot back up " + path + ": " + ec.message();
  } else if (ec) {
    return "cannot inspect " + path + ": " + ec.message();
  }
  std::ofstream f(path, std::ios::binary | std::ios::trunc);
  if (!f) return "cannot write " + path;
  f << body;
  f.close();
  if (!f) return "write failed for " + path;
  return "";
}

std::expected<Scene, LoadError> Game::loadScene(const std::string& path) {
  std::ifstream f(path, std::ios::binary);
  if (!f) return std::unexpected(LoadError{path, "no such file"});
  std::ostringstream buf;
  buf << f.rdbuf();
  auto root = json::parse(buf.str());
  if (!root)
    return std::unexpected(LoadError{path, root.error()});
  if (!root->is(json::Kind::Obj))
    return std::unexpected(LoadError{path, "top-level value is not an object"});
  return fromJson(buf.str());
}

Scene Game::normalizeScene(const Scene& in) {
  Scene s = in;
  s.name = s.name.empty() ? "scene" : s.name;
  s.bg = hex_or(s.bg, "#0b0e1a");
  s.gravity = clampf(s.gravity, -5000, 5000);
  s.magnet = std::max(0.f, s.magnet);
  s.camera.zoom = clampf(s.camera.zoom, 0.3f, 4.f);
  for (auto& e : s.entities) {
    e.color = hex_or(e.color, "#8b5cf6");
    if (e.fill != "gradient") e.color2.clear();
    e.w = std::max(1.f, e.w);
    e.h = std::max(1.f, e.h);
  }
  return s;
}

// ------------------------------------------------------------------- Game

Game::Game(Scene s) : scene(normalizeScene(std::move(s))) {
  if (const Entity* p = player()) spawn_ = {p->x, p->y};
}

const Entity* Game::player() const {
  for (const auto& e : scene.entities)
    if (e.tag == "player") return &e;
  return nullptr;
}

Entity* Game::entity(std::string_view tag) {
  for (auto& e : scene.entities)
    if (e.tag == tag) return &e;
  return nullptr;
}

float Game::worldBottom() const {
  float b = 0;
  for (const auto& e : scene.entities) b = std::max(b, e.y + e.h);
  return b;
}

float Game::worldRight() const {
  float r = 0;
  for (const auto& e : scene.entities) r = std::max(r, e.x + e.w);
  return r;
}

void Game::shake(float power, float dur) {
  shakeP = clampf(power, 0, 40);
  shakeD = std::max(0.05f, dur);
  shakeT = shakeD;
}

void Game::say(std::string m, float secs) {
  msg = std::move(m);
  msgT = secs;
}

void Game::reset() {
  if (Entity* p = entity("player")) {
    p->x = spawn_.x; p->y = spawn_.y;
    p->vx = p->vy = 0;
  }
  for (auto& e : scene.entities)
    if (e.tag == "coin") e.alive = true;
  transLocked = false;
  pendingNext.clear();
  say("reset", 0.9);
}

void Game::respawn(const char* why) {
  if (Entity* p = entity("player")) {
    p->x = spawn_.x; p->y = spawn_.y;
    p->vx = p->vy = 0;
  }
  say(why, 1.6);
  flash = 0.9;
  shake(6, 0.3);
}

// ---- player: run + jump + AABB resolve against solid (tagless) entities

void Game::stepPlayer(float dt, const Input& in) {
  Entity* p = entity("player");
  if (!p) return;

  const float dir = (in.right ? 1.f : 0.f) - (in.left ? 1.f : 0.f);
  if (dir != 0) {
    p->vx += dir * RUN_ACCEL * dt;
    p->vx = clampf(p->vx, -RUN_MAX, RUN_MAX);
  } else {
    const float fr = (p->vy == 0 ? GROUND_FRICTION : AIR_FRICTION) * dt;
    if (std::abs(p->vx) <= fr) p->vx = 0; else p->vx -= (p->vx > 0 ? fr : -fr);
  }

  if (in.jump && !jumpHeld_ && p->vy == 0) p->vy = JUMP_VY;   // edge-triggered
  jumpHeld_ = in.jump;

  p->vy += scene.gravity * dt;
  p->vy = clampf(p->vy, -2000, 2000);

  // horizontal move + resolve
  p->x += p->vx * dt;
  for (auto& s : scene.entities) {
    if (&s == p || !s.alive || !s.tag.empty()) continue;    // tagless = solid
    if (!overlap(*p, s)) continue;
    if (p->vx > 0) p->x = s.x - p->w; else if (p->vx < 0) p->x = s.x + s.w;
    p->vx = 0;
  }

  // vertical move + resolve (movers are solid too)
  p->y += p->vy * dt;
  for (auto& s : scene.entities) {
    if (&s == p || !s.alive) continue;
    if (!s.tag.empty() && s.tag != "mover") continue;
    if (!overlap(*p, s)) continue;
    if (p->vy > 0) { p->y = s.y - p->h; p->vy = 0; }
    else if (p->vy < 0) { p->y = s.y + s.h; p->vy = 0; }
  }

  if (p->y > worldBottom() + 400) respawn("ouch — respawned");
}

// ---- movers: ping-pong along waypoints, carrying whoever stands on top

void Game::stepMovers(float dt) {
  for (size_t mi = 0; mi < scene.entities.size(); ++mi) {
    Entity& m = scene.entities[mi];
    if (m.tag != "mover" || m.path.size() < 2 || !m.alive) continue;

    m.prev = {m.x, m.y};
    if (m.pathIdx >= static_cast<int>(m.path.size())) m.pathIdx = 0;
    Vec2 target = m.path[m.pathIdx];
    float dx = target.x - m.x, dy = target.y - m.y;
    const float dist = std::hypot(dx, dy);
    const float step = m.pathSpeed * dt;
    if (dist <= step || dist < 0.5f) {
      m.x = target.x; m.y = target.y;
      m.pathIdx += m.pathDir;
      if (m.pathIdx >= static_cast<int>(m.path.size())) {
        m.pathIdx = static_cast<int>(m.path.size()) - 2;
        m.pathDir = -1;
      } else if (m.pathIdx < 0) {
        m.pathIdx = 1;
        m.pathDir = 1;
      }
    } else {
      m.x += dx / dist * step;
      m.y += dy / dist * step;
    }

    const float mdx = m.x - m.prev.x, mdy = m.y - m.prev.y;
    if (mdx == 0 && mdy == 0) continue;
    for (auto& r : scene.entities) {           // rider carry
      if (r.tag == "player" || r.tag == "ball") {
        const float feet = r.y + r.h;
        if (feet >= m.prev.y - 2 && feet <= m.y + m.h + 2 &&
            r.x + r.w > m.x && r.x < m.x + m.w) {
          r.x += mdx;
          r.y += mdy;
        }
      }
    }
  }
}

// ---- coins: magnetism + pickup

void Game::stepCoins(float dt) {
  Entity* p = entity("player");
  const float mag = scene.magnet;
  for (auto& c : scene.entities) {
    if (c.tag != "coin" || !c.alive) continue;
    if (mag > 0 && p) {
      const float dx = p->cx() - c.cx(), dy = p->cy() - c.cy();
      const float d = std::hypot(dx, dy);
      if (d < mag && d > 1) {
        const float pull = MAGNET_PULL * (1 - d / mag) + 40;
        c.x += dx / d * pull * dt;
        c.y += dy / d * pull * dt;
      }
    }
    if (p && overlap(*p, c)) {
      c.alive = false;
      score += 10;
      say("+10", 0.5);
    }
  }
}

// ---- hazards, goals, balls, timers, camera

void Game::stepTags(float dt) {
  Entity* p = entity("player");

  for (auto& e : scene.entities) {
    if (e.spin != 0) e.rot += e.spin * dt;

    if (e.tag == "ball") {                     // perpetual demo bounce
      e.vy += scene.gravity * dt;
      e.x += e.vx * dt;
      e.y += e.vy * dt;
      for (auto& s : scene.entities) {
        if (&s == &e || !s.alive || (!s.tag.empty() && s.tag != "mover")) continue;
        if (!overlap(e, s)) continue;
        if (e.vy > 0 && e.y + e.h - e.vy * dt <= s.y + 2) {
          e.y = s.y - e.h;
          e.vy = -std::abs(e.vy) * 0.72f;
          if (std::abs(e.vy) < 120) e.vy = -520;   // keep the demo alive
        } else if (e.vx > 0) {
          e.x = s.x - e.w; e.vx = -std::abs(e.vx);
        } else if (e.vx < 0) {
          e.x = s.x + s.w; e.vx = std::abs(e.vx);
        }
      }
    }

    if (!p || &e == p) continue;
    // the killing tags: the fang (spike) and the saw (hazard) — the
    // campaign's levels wear both, and a saw that cannot saw lies
    if (e.alive && overlap(*p, e)) {
      if (e.tag == "spike") respawn("ouch — spike!");
      else if (e.tag == "hazard") respawn("ouch — the saw!");
    }
    if (e.tag == "goal" && !transLocked && overlap(*p, e)) {
      transLocked = true;
      flash = 1;
      say(scene.next.empty() ? "goal! (the end)" : "goal!", 1.4);
      if (!scene.next.empty()) pendingNext = scene.next;
      shake(4, 0.25);
    }
  }

  if (msgT > 0) msgT -= dt;
  if (flash > 0) flash = std::max(0.f, flash - dt * 2.2f);
  if (shakeT > 0) shakeT = std::max(0.f, shakeT - dt);
}

void Game::stepCamera(float dt) {
  const Entity* p = player();
  if (!p) return;
  // zoom-aware follow: keep the player centered (renderer supplies viewport)
  const float tx = p->cx(), ty = p->cy();
  const float k = std::min(1.f, dt * 8);
  scene.camera.x += (tx - scene.camera.x) * k;
  scene.camera.y += (ty - scene.camera.y) * k;
}

void Game::update(float dt, const Input& in) {
  dt = std::min(dt, 1.f / 30.f);
  time += dt;
  stepPlayer(dt, in);
  stepMovers(dt);
  stepCoins(dt);
  stepTags(dt);
  stepCamera(dt);
  for (auto& e : scene.entities)           // the hit-flash decays fast:
    if (e.flash > 0) e.flash = std::max(0.f, e.flash - dt * 4.f);
}

} // namespace dxn3
