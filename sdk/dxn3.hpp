// dxn3 SDK — write a game in C++23, the studio renders it.
//
//   #include "dxn3.hpp"
//
//   int main() {
//     dxn3::Game game;                       // speaks the stdio protocol
//     auto ship = game.rect("ship", dxn3::W/2-6, dxn3::H-12, 12, 5, "#8b5cf6");
//     ship->tag = "ship";
//     game.on_key = [&](const std::string& k) { if (k == "left") ship->x -= 1; };
//     game.on_tick = [&](float dt) { ... };
//     game.on_hit = [&](dxn3::Ent a, dxn3::Ent b) { ... };
//     game.run();                            // hands the loop to the studio
//   }
//
// compile:  g++ -std=c++23 -O2 game.cpp -o game     (the engine hosts ./game)
// The engine owns rendering, input and collision; this header speaks the
// line-JSON protocol on stdio.
#pragma once

#include <functional>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace dxn3 {

inline int W = 100, H = 46;
inline double DT = 0.0;

struct Ent {
  std::map<std::string, std::string> s;   // string fields
  std::map<std::string, double> n;        // numeric fields
  double& x = n["x"]; double& y = n["y"];
  double& w = n["w"]; double& h = n["h"];
  double& vx = n["vx"]; double& vy = n["vy"];
  std::string& name = s["name"];
  std::string& tag = s["tag"];
  std::string& shape = s["shape"];
  std::string& color = s["color"];
  std::string& text = s["text"];
  std::string json() const {
    std::string o = "{";
    auto put = [](const std::string& k, const std::string& v) {
      std::string out = "\"" + k + "\":";
      bool num = v.find_first_not_of("-.0123456789") == std::string::npos && !v.empty();
      out += num ? v : "\"" + v + "\"";
      return out;
    };
    bool first = true;
    for (const auto& [k, v] : n) { if (!first) o += ","; o += put(k, std::to_string(v).erase(std::to_string(v).find_last_not_of('0') + 1, std::string::npos)); first = false; }
    for (const auto& [k, v] : s) { if (!first) o += ","; o += put(k, v); first = false; }
    return o + ",\"visible\":1}";
  }
};

class Game {
public:
  std::function<void(const std::string&)> on_key;
  std::function<void(float)> on_tick;
  std::function<void(Ent, Ent)> on_hit;
  std::function<void()> on_start;

  Ent& rect(const std::string& name, double x, double y, double w, double h,
            const std::string& color = "#8b5cf6") { return mk(name, "rect", x, y, w, h, color); }
  Ent& circle(const std::string& name, double x, double y, double w, double h,
              const std::string& color = "#facc15") { return mk(name, "circle", x, y, w, h, color); }
  Ent& label(const std::string& name, double x, double y, const std::string& text,
             const std::string& color = "#e9e5ff") {
    auto& e = mk(name, "text", x, y, static_cast<double>(text.size()), 2, color);
    e.text = text;
    return e;
  }
  void destroy(const std::string& name) {
    if (ents_.count(name)) { ents_.erase(name); dels_.push_back(name); }
  }
  void background(const std::string& hex) { bg_ = hex; }
  void gravity(double g) { gravity_ = g; }
  void vars(const std::map<std::string, double>& kv) { for (auto& [k, v] : kv) vars_[k] = v; }

  void run() {
    std::string line;
    std::getline(std::cin, line);                 // hello
    parseHello(line);
    std::cout << "{\"t\":\"scene\",\"name\":\"game\",\"bg\":\"" << bg_
              << "\",\"gravity\":" << gravity_ << ",\"entities\":[";
    bool first = true;
    for (auto& [_, e] : ents_) { if (!first) std::cout << ","; std::cout << e.json(); first = false; }
    std::cout << "]}" << std::endl;
    bool started = false;
    while (std::getline(std::cin, line)) {
      if (line.find("\"tick\"") == std::string::npos) continue;
      DT = numField(line, "dt");
      if (!started) { if (on_start) on_start(); started = true; }
      for (auto& [_, e] : ents_) {
        if (e.vx) e.x += e.vx * DT;
        if (e.vy) e.y += e.vy * DT;
      }
      if (on_tick) on_tick(DT);
      if (on_key) for (const auto& k : heldKeys(line)) on_key(k);
      if (on_hit) for (const auto& p : hits(line)) {
        if (ents_.count(p.first) && ents_.count(p.second)) on_hit(ents_[p.first], ents_[p.second]);
      }
      std::cout << "{\"t\":\"frame\",\"set\":[";
      first = true;
      for (auto& [_, e] : ents_) { if (!first) std::cout << ","; std::cout << e.json(); first = false; }
      std::cout << "],\"del\":[";
      first = true;
      for (auto& d : dels_) { if (!first) std::cout << ","; std::cout << "\"" << d << "\""; first = false; }
      std::cout << "],\"vars\":{";
      first = true;
      for (auto& [k, v] : vars_) { if (!first) std::cout << ","; std::cout << "\"" << k << "\":" << v; first = false; }
      std::cout << "}}" << std::endl;
      dels_.clear();
    }
  }

private:
  std::map<std::string, Ent> ents_;
  std::vector<std::string> dels_;
  std::map<std::string, double> vars_;
  std::string bg_ = "#0b0e1a";
  double gravity_ = 0;

  Ent& mk(const std::string& name, const std::string& shape, double x, double y,
          double w, double h, const std::string& color) {
    Ent e;
    e.name = name; e.shape = shape; e.color = color;
    e.x = x; e.y = y; e.w = w; e.h = e.h = h;
    return ents_.emplace(name, std::move(e)).first->second;
  }
  static double numField(const std::string& line, const std::string& key) {
    const std::string pat = "\"" + key + "\":";
    const auto at = line.find(pat);
    if (at == std::string::npos) return 0;
    try { return std::stod(line.substr(at + pat.size())); } catch (...) { return 0; }
  }
  static std::vector<std::string> heldKeys(const std::string& line) {
    std::vector<std::string> out;
    for (const char* k : {"left", "right", "jump", "space"})
      if (line.find("\"" + std::string(k) + "\":true") != std::string::npos) out.push_back(k);
    return out;
  }
  static std::vector<std::pair<std::string, std::string>> hits(const std::string& line) {
    std::vector<std::pair<std::string, std::string>> out;
    const auto at = line.find("\"hits\":[");
    if (at == std::string::npos) return out;
    std::string body = line.substr(at + 8, line.find("]", at) - at - 8);
    for (size_t i = 0; i + 1 < body.size(); ++i) {
      if (body[i] == '"') {
        const auto q1 = body.find('"', i + 1);
        const std::string a = body.substr(i + 1, q1 - i - 1);
        size_t j = body.find('"', q1 + 1);
        if (j == std::string::npos) break;
        const auto q2 = body.find('"', j + 1);
        out.emplace_back(a, body.substr(j + 1, q2 - j - 1));
        i = q2;
      }
    }
    return out;
  }
  void parseHello(const std::string& line) {
    const auto w = line.find("\"w\":");
    const auto h = line.find("\"h\":");
    if (w != std::string::npos) try { W = std::stoi(line.substr(w + 4)); } catch (...) {}
    if (h != std::string::npos) try { H = std::stoi(line.substr(h + 4)); } catch (...) {}
  }
};

} // namespace dxn3
