// dxn3.hpp — the C++ SDK: write a game in C++, the studio renders it.
//
//     #include "dxn3.hpp"        // compile: g++ -std=c++23 -O2 game.cpp
//     int main() {
//         dxn3::Game g;          // the engine says hello on construction
//         auto* ship = g.rect("ship", dxn3::W / 2 - 21, dxn3::H - 60, 42, 30, "#8b5cf6");
//         ship->tag = "ship";
//         g.onKey = [&](const std::string& k) {
//             if (k == "left")  ship->x -= 340 * dxn3::dt;
//             if (k == "right") ship->x += 340 * dxn3::dt;
//         };
//         g.onTick = [&](float) { g.hud()->text = "SCORE " + std::to_string(g.score()); };
//         g.run();               // hands the loop to the studio
//     }
//
// The engine owns rendering, input and collision; this header speaks the
// line-JSON protocol on stdio. printf goes to the studio's console.
// The wire contract lives in sdk/PROTOCOL.md — this file is one honest
// implementation of it, no dependencies beyond libstdc++.
#pragma once

#include <map>
#include <charconv>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <functional>
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

namespace dxn3 {

inline int W = 100, H = 46;        // the world size, set by the hello packet
inline float dt = 0.f;             // seconds since the last tick (read live)

struct Ent {
  std::string name, tag, color = "#8b5cf6", shape = "rect", text,
              fill = "solid", color2;
  float x = 0, y = 0, w = 32, h = 32, vx = 0, vy = 0, rot = 0, spin = 0,
        tsize = 20;
  // the engine's light, since v3.1.46 — the same three fields the JS
  // and Python SDKs speak: a halo (glow), a hit-bleach the host decays
  // (flash), and a ghost-thin body (alpha). Zero-cost until used: the
  // frame only carries them when they differ from the defaults.
  float glow = 0, flash = 0, alpha = 1;
  int visible = 1;
};

inline std::string jesc(const std::string& s) {
  std::string out;
  for (const char c : s) {
    if (c == '"' || c == '\\') out += '\\';
    if (static_cast<unsigned char>(c) < 0x20) continue;
    out += c;
  }
  return out;
}

class Game {
public:
  std::function<void(float)> onTick;                       // every frame
  std::function<void(const std::string&)> onKey;           // held keys/chars
  std::function<void(Ent&, Ent&)> onHit;                   // pair ENTERS
  std::function<void()> onStart;                           // first tick

  // the frame's two words: a transient HUD line and the banner + flash.
  // they ride ONE frame and are cleared the moment it is sent.
  void say(const std::string& m) { say_ = m; }
  void win(const std::string& b) { win_ = b; }

  Game() {
    std::string line;
    if (!std::getline(std::cin, line)) {                   // the hello packet
      std::cout << "run me from the studio:  dxn3 mygame   (not directly)\n";
      std::exit(1);
    }
    auto num = [&](const std::string& key, int fallback) {
      const size_t p = line.find("\"" + key + "\":");
      if (p == std::string::npos) return fallback;
      return std::atoi(line.c_str() + p + key.size() + 3);
    };
    W = num("w", 100);
    H = num("h", 46);
  }

  Ent* rect(const std::string& name, float x, float y, float w, float h,
            const std::string& color = "#8b5cf6") {
    return mk(name, "rect", x, y, w, h, color);
  }
  Ent* circle(const std::string& name, float x, float y, float w, float h,
              const std::string& color = "#facc15") {
    return mk(name, "circle", x, y, w, h, color);
  }
  Ent* tri(const std::string& name, float x, float y, float w, float h,
           const std::string& color = "#ef4444") {
    return mk(name, "tri", x, y, w, h, color);
  }
  Ent* label(const std::string& name, float x, float y,
             const std::string& text, const std::string& color = "#e9e5ff") {
    Ent* e = mk(name, "text", x, y,
                static_cast<float>(std::max<size_t>(1, text.size())), 2, color);
    e->text = text;
    return e;
  }
  Ent* find(const std::string& name) {
    for (auto& e : ents_) if (e.name == name) return &e;
    return nullptr;
  }
  void destroy(const std::string& name) {
    for (auto& e : ents_)
      if (e.name == name) { e.visible = 0; dels_.push_back(name); }
  }
  void background(const std::string& hex) { bg_ = hex; }
  void gravity(float g) { gravity_ = g; }
  void camera(float x, float y, float zoom = 1) { cam_ = {x, y, zoom}; }
  void var(const std::string& key, double value) { vars_[key] = value; }
  Ent* hud() { return find("hud"); }

  void run() {
    // the scene packet: everything visible at t=0
    std::cout << "{\"t\":\"scene\",\"name\":\"game\",\"bg\":\"" << jesc(bg_)
              << "\",\"gravity\":" << (int)gravity_ << ",\"entities\":[";
    bool first = true;
    for (const auto& e : ents_) {
      if (!first) std::cout << ",";
      first = false;
      std::cout << entJson(e);
    }
    std::cout << "]}\n" << std::flush;

    int started = 0;
    std::string lastLine;
    std::vector<std::string> pairs;                       // already reported
    while (std::getline(std::cin, lastLine)) {
      if (lastLine.find("\"tick\"") == std::string::npos) continue;
      dt = numField(lastLine, "dt");
      if (!started && onStart) { onStart(); started = 1; }
      for (auto& e : ents_) {                             // physics-lite
        if (e.visible && e.vx) e.x += e.vx * dt;
        if (e.visible && e.vy) e.y += e.vy * dt;
      }
      if (onTick) onTick(dt);
      // keys: "left"/"right"/"jump"/"space" booleans + chars substring
      for (const char* k : {"left", "right", "jump", "space"}) {
        if (lastLine.find(std::string("\"" ) + k + "\":true") !=
            std::string::npos && onKey) onKey(k);
      }
      const size_t ch = lastLine.find("\"chars\":\"");
      if (ch != std::string::npos && onKey) {
        size_t i = ch + 9;
        while (i < lastLine.size() && lastLine[i] != '"') {
          if (lastLine[i] != ' ') onKey(std::string(1, lastLine[i]));
          ++i;
        }
      }
      // hits arrive flat: ["a","b",…] — fire on ENTER only
      const size_t hi = lastLine.find("\"hits\":[");
      if (hi != std::string::npos && onHit) {
        std::vector<std::string> names;
        for (size_t i = hi + 8; i < lastLine.size() && lastLine[i] != ']';) {
          if (lastLine[i] == '"') {
            size_t j = i + 1;
            while (j < lastLine.size() && lastLine[j] != '"') ++j;
            names.push_back(lastLine.substr(i + 1, j - i - 1));
            i = j + 1;
          } else ++i;
        }
        std::vector<std::string> seen;
        for (size_t i = 0; i + 1 < names.size(); i += 2) {
          std::string key = names[i] < names[i + 1]
                                ? names[i] + "|" + names[i + 1]
                                : names[i + 1] + "|" + names[i];
          seen.push_back(key);
          bool fresh = true;
          for (const auto& p : pairs) if (p == key) fresh = false;
          if (!fresh) continue;
          Ent* a = find(names[i]);
          Ent* b = find(names[i + 1]);
          if (a && b) onHit(*a, *b);
        }
        pairs = seen;
      }
      // the frame: a full patch of every live entity
      std::cout << "{\"t\":\"frame\",\"set\":[";
      first = true;
      for (const auto& e : ents_) {
        if (!e.visible) continue;
        if (!first) std::cout << ",";
        first = false;
        std::cout << entJson(e);
      }
      std::cout << "],\"del\":[";
      for (size_t i = 0; i < dels_.size(); ++i)
        std::cout << (i ? "," : "") << "\"" << jesc(dels_[i]) << "\"";
      std::cout << "],\"vars\":{";
      first = true;
      for (const auto& [k, v] : vars_) {
        if (!first) std::cout << ",";
        first = false;
        std::cout << "\"" << jesc(k) << "\":" << v;   // numbers stay numbers
      }
      std::cout << "},\"camera\":{},\"say\":\"" << jesc(say_)
                << "\",\"win\":\"" << jesc(win_) << "\"}\n" << std::flush;
      dels_.clear(); vars_.clear(); say_.clear(); win_.clear();
    }
  }

private:
  std::string say_, win_;

  // deque on purpose: games hold Ent* across frames (pad, ball, …) and
  // push_back must NEVER invalidate them — vector would silently dangle
  std::deque<Ent> ents_;
  std::vector<std::string> dels_;
  std::map<std::string, double> vars_;
  std::string bg_ = "#0b0e1a";
  float gravity_ = 0;
  struct { float x = 0, y = 0, zoom = 1; } cam_;

  static std::string fmtNum(float f) {
    char b[32];
    auto [p, ec] = std::to_chars(b, b + sizeof b, f);
    (void)ec;
    return std::string(b, p);
  }

  static float numField(const std::string& line, const std::string& key) {
    const size_t p = line.find("\"" + key + "\":");
    if (p == std::string::npos) return 0.f;
    return strtof(line.c_str() + p + key.size() + 3, nullptr);
  }
  Ent* mk(const std::string& name, const char* shape, float x, float y,
          float w, float h, const std::string& color) {
    for (auto& e : ents_)
      if (e.name == name) {                       // redraw replaces in place
        e.shape = shape; e.x = x; e.y = y; e.w = w; e.h = h; e.color = color;
        e.visible = 1;
        return &e;
      }
    // designated initializers on purpose: positional aggregate init
    // silently SHIFTED when the light fields joined the struct (the
    // ladder probe's lean-pin caught glow arriving as 1) — named
    // members can't lie, and future additions stay safe
    ents_.push_back(Ent{.name = name, .color = color, .shape = shape,
                        .fill = "solid", .x = x, .y = y, .w = w, .h = h,
                        .tsize = 20, .alpha = 1, .visible = 1});
    return &ents_.back();
  }
  static std::string entJson(const Ent& e) {
    std::string o = "{\"name\":\"" + jesc(e.name) + "\"";
    auto putS = [&](const char* k, const std::string& v) {
      o += ",\"" + std::string(k) + "\":\"" + jesc(v) + "\"";
    };
    auto putN = [&](const char* k, float f) {
      o += std::string(",\"") + k + "\":" + fmtNum(f);
    };
    putS("tag", e.tag);
    putS("color", e.color);
    putS("shape", e.shape);
    putS("text", e.text);
    putS("fill", e.fill);
    putS("color2", e.color2);
    putN("x", e.x); putN("y", e.y); putN("w", e.w); putN("h", e.h);
    putN("vx", e.vx); putN("vy", e.vy); putN("rot", e.rot);
    putN("spin", e.spin); putN("tsize", e.tsize);
    if (e.glow != 0) putN("glow", e.glow);
    if (e.flash != 0) putN("flash", e.flash);
    if (e.alpha != 1) putN("alpha", e.alpha);
    o += ",\"visible\":" + std::to_string(e.visible);
    return o + "}";
  }
};

} // namespace dxn3
