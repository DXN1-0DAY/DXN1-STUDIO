// dxn3 native — the ScriptHost: your code, our engine.
//
// A user game is a CHILD PROCESS in ANY language (python, node, a compiled
// C++ game, ruby, anything that reads stdin and writes stdout) speaking
// one honest line-JSON protocol:
//
//   engine -> child : {"t":"hello","w":<cols*px>,"h":<rows*px>}
//   child  -> engine: {"t":"scene", ...full scene, .dxn1.json entity fields}
//   engine -> child : {"t":"tick","dt":<s>,"keys":{"left":b,"right":b,
//                       "jump":b,"space":b},"chars":"<typed letters>"}
//   child  -> engine: {"t":"frame","set":[{name,x,y,w,h,color,rot,spin,
//                       text,shape,tag,visible}],"del":[names],
//                       "vars":{"score":42},"say":"...","win":"..."}
//   child  -> engine: {"t":"print","m":"goes to the console rail"}
//
// One persistent child: the game state belongs to the user's code, in the
// user's language. Unparsable child output (printf, logs, tracebacks) is
// not an error — it is the console. The engine never crashes because a
// game did; a dead child is a stale frame plus an honest exit line.
#pragma once

#include "json.hpp"
#include "spark.hpp"

#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <charconv>
#include <cstdlib>
#include <string>
#include <vector>

namespace dxn3 {

struct HostFrame {
  bool frame = false;                 // a "frame" packet arrived this tick
  bool exited = false;                // the child died this tick
  int exitCode = -1;
  json::Value set;                    // array of entity patches (by name)
  json::Value del;                    // array of names to remove
  json::Value vars;                   // object of game vars (score, …)
  json::Value camera;                 // optional {x,y,zoom}
  std::string say;                    // transient HUD message
  std::string banner;                 // "win"-style banner (persists a beat)
  std::vector<std::string> console;   // prints + unparsable child output
};

class ScriptHost {
public:
  ~ScriptHost() { stop(); }

  // spawn the game: argv[0] is the interpreter/binary, argv[1..] its args.
  // w/h feed the hello packet (world size in px). Environment is inherited
  // plus PYTHONPATH=<dir> so `from dxn3 import *` just works.
  bool start(const std::vector<std::string>& argv, int w, int h,
             const std::string& sdkDir, std::string* err) {
    stop();
    ::signal(SIGPIPE, SIG_IGN);   // a dead child's pipe must never kill
                                  // the studio — write() reports EPIPE instead
    int inPipe[2], outPipe[2];
    if (::pipe(inPipe) != 0 || ::pipe(outPipe) != 0) {
      if (err) *err = "pipe() failed — cannot host a game here";
      return false;
    }
    if (!sdkDir.empty()) {
      ::setenv("PYTHONPATH", sdkDir.c_str(), 1);   // `from dxn3 import *`
      ::setenv("NODE_PATH", sdkDir.c_str(), 1);    // require('dxn3')
    }
    argv_ = argv;
    pid_ = ::fork();
    if (pid_ < 0) {
      if (err) *err = "fork() failed";
      return false;
    }
    if (pid_ == 0) {                                  // the child = the game
      ::dup2(inPipe[0], STDIN_FILENO);
      ::dup2(outPipe[1], STDOUT_FILENO);
      ::dup2(outPipe[1], STDERR_FILENO);              // logs -> console
      ::close(inPipe[0]); ::close(inPipe[1]);
      ::close(outPipe[0]); ::close(outPipe[1]);
      std::vector<char*> av;
      for (const auto& a : argv_) av.push_back(const_cast<char*>(a.c_str()));
      av.push_back(nullptr);
      ::execvp(av[0], av.data());
      ::_exit(127);                                   // exec failed — honest
    }
    ::close(inPipe[0]);
    ::close(outPipe[1]);
    inFd_ = inPipe[1];
    outFd_ = outPipe[0];
    ::fcntl(outFd_, F_SETFL, ::fcntl(outFd_, F_GETFL) | O_NONBLOCK);
    exited_ = false;
    exitCode_ = -1;
    buf_.clear();
    sendLine("{\"t\":\"hello\",\"w\":" + std::to_string(w) +
             ",\"h\":" + std::to_string(h) + "}");
    return true;
  }

  bool running() const { return pid_ > 0 && !exited_; }

  void stop() {
    if (pid_ > 0) {
      if (!exited_) {
        ::kill(pid_, SIGTERM);
        for (int i = 0; i < 30; ++i) {
          if (::waitpid(pid_, nullptr, WNOHANG) == pid_) break;
          ::usleep(10'000);
        }
        ::kill(pid_, SIGKILL);
        int st = 0;
        ::waitpid(pid_, &st, 0);
      }
      pid_ = -1;
    }
    if (inFd_ >= 0) { ::close(inFd_); inFd_ = -1; }
    if (outFd_ >= 0) { ::close(outFd_); outFd_ = -1; }
    buf_.clear();
  }

  void restart(int w, int h, const std::string& sdkDir, std::string* err) {
    const bool ok = start(argv_, w, h, sdkDir, err);   // stop() inside
    (void)ok;
  }

  // one fixed-timestep handshake: send input + hit pairs, gather the
  // child's replies until a frame lands or the deadline (ms) passes.
  // hits is a flat [nameA, nameB, …] list of overlapping tagged pairs.
  HostFrame tick(float dt, bool left, bool right, bool jump, bool space,
                 const std::string& chars,
                 const std::vector<std::string>& hits = {}, int ms = 120) {
    HostFrame f;
    if (!running()) { f.exited = exited_; f.exitCode = exitCode_; return f; }
    std::string hitJson = "[";
    for (size_t i = 0; i < hits.size(); ++i)
      hitJson += (i ? ",\"" : "\"") + esc(hits[i]) + "\"";
    hitJson += "]";
    std::string line = "{\"t\":\"tick\",\"dt\":" + num(dt) +
                       ",\"keys\":{\"left\":" + b(left) + ",\"right\":" +
                       b(right) + ",\"jump\":" + b(jump) + ",\"space\":" +
                       b(space) + "},\"chars\":\"" + esc(chars) + "\"," +
                       "\"hits\":" + hitJson + "}";
    if (!sendLine(line)) {
      reap();
      f.exited = exited_;
      f.exitCode = exitCode_;
      return f;
    }
    const long deadline = ScriptHost::now_ms() + ms;
    while (ScriptHost::now_ms() < deadline) {
      drain(f);                                       // parse what's buffered
      if (f.frame || exited_) break;
      pollfd p{outFd_, POLLIN, 0};
      const int r = ::poll(&p, 1, 8);
      if (r < 0) break;
      if (p.revents & (POLLIN | POLLHUP)) {
        char tmp[4096];
        const ssize_t n = ::read(outFd_, tmp, sizeof tmp);
        if (n > 0) buf_.append(tmp, static_cast<size_t>(n));
        else if (n == 0) { reap(); break; }           // EOF — child gone
      }
    }
    drain(f);                                         // final buffered lines
    return f;
  }

  // a full scene packet from the child, if one arrived (consumed once)
  bool takeScene(json::Value& out) {
    if (!haveScene_) return false;
    out = std::move(scene_);
    scene_ = json::Value{};
    haveScene_ = false;
    return true;
  }

  // drain the console (prints + unparsable child output) — moves out
  std::vector<std::string> takeConsole() {
    std::vector<std::string> out;
    out.swap(console_);
    return out;
  }
  int exitCode() const { return exitCode_; }

private:
  static long now_ms() {
    struct timespec ts;
    ::clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000 + ts.tv_nsec / 1'000'000;
  }
  static std::string num(double d) {
    char buf[32];
    auto [p, ec] = std::to_chars(buf, buf + sizeof buf, d);
    (void)ec;
    return std::string(buf, p);
  }
  static std::string b(bool v) { return v ? "true" : "false"; }
  static std::string esc(std::string_view s) {
    std::string out;
    for (const char c : s) {
      if (c == '"' || c == '\\') out += '\\';
      if (static_cast<unsigned char>(c) < 0x20) out += ' ';
      else out += c;
    }
    return out;
  }

  bool sendLine(const std::string& line) {
    if (inFd_ < 0) return false;
    const std::string pkt = line + "\n";
    size_t off = 0;
    while (off < pkt.size()) {
      const ssize_t n = ::write(inFd_, pkt.data() + off, pkt.size() - off);
      if (n <= 0) return false;
      off += static_cast<size_t>(n);
    }
    return true;
  }

  void reap() {
    if (pid_ > 0 && !exited_) {
      int st = 0;
      if (::waitpid(pid_, &st, WNOHANG) == pid_) {
        exited_ = true;
        exitCode_ = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
      }
    }
  }

  void line(std::string_view raw, HostFrame& f) {
    while (!raw.empty() && (raw.back() == '\n' || raw.back() == '\r'))
      raw.remove_suffix(1);
    if (raw.empty()) return;
    auto v = json::parse(raw);
    if (!v) { console_.emplace_back(raw); return; }   // logs are the console
    const std::string t = v->at("t").str_or("");
    if (t == "scene") { scene_ = std::move(*v); haveScene_ = true; }
    else if (t == "frame") {
      f.frame = true;
      f.set = v->at("set");
      f.del = v->at("del");
      f.vars = v->at("vars");
      f.camera = v->at("camera");
      f.say = v->at("say").str_or("");
      f.banner = v->at("win").str_or("");
    } else if (t == "print") {
      console_.push_back(v->at("m").str_or(""));
    } else {
      console_.emplace_back(raw);                     // unknown — show it
    }
  }

  void drain(HostFrame& f) {
    size_t pos;
    while ((pos = buf_.find('\n')) != std::string::npos) {
      const std::string one = buf_.substr(0, pos);
      buf_.erase(0, pos + 1);
      line(one, f);
    }
    reap();
  }

  std::vector<std::string> argv_;
  pid_t pid_ = -1;
  int inFd_ = -1, outFd_ = -1;
  std::string buf_;
  bool exited_ = false;
  int exitCode_ = -1;
  bool haveScene_ = false;
  json::Value scene_;
  std::vector<std::string> console_;
};

// language pick: extension -> the command that runs a game file honestly.
// Unknown extensions are NOT an error — --host-cmd overrides everything,
// and any interpreter can speak the protocol with raw echo/read.
inline bool hostCommandFor(const std::string& file,
                           std::vector<std::string>& argv,
                           std::string* err) {
  const auto dot = file.rfind('.');
  const std::string ext = dot == std::string::npos ? "" : file.substr(dot);
  auto probe = [](const char* exe) {
    std::string cmd = std::string("command -v ") + exe + " >/dev/null 2>&1";
    return ::system(cmd.c_str()) == 0;
  };
  if (ext == ".py") {
    if (!probe("python3")) { if (err) *err = "python3 not found — install it to run .py games"; return false; }
    argv = {"python3", file};
  } else if (ext == ".js" || ext == ".mjs") {
    if (!probe("node")) { if (err) *err = "node not found — install it to run .js games"; return false; }
    argv = {"node", file};
  } else if (ext == ".cpp" || ext == ".cc" || ext == ".cxx") {
    if (!probe("g++")) { if (err) *err = "g++ not found — install it to compile .cpp games"; return false; }
    const std::string bin = "/tmp/dxn3-game-" +
                            std::to_string(static_cast<long>(::getpid())) + ".bin";
    const std::string cmd = "g++ -std=c++23 -O2 '" + file + "' -o '" + bin +
                            "' 2>/tmp/dxn3-game-build.log";
    if (::system(cmd.c_str()) != 0) {
      if (err) *err = "your game did not compile — the build log is in "
                      "/tmp/dxn3-game-build.log";
      return false;
    }
    argv = {bin};
  } else if (ext == ".cs") {
    if (!probe("dotnet")) { if (err) *err = "dotnet not found — install the .NET SDK to run .cs games (or script it in py/js/cpp)"; return false; }
    argv = {"dotnet", "script", file};
  } else {
    if (err) *err = "don't know how to run '" + file +
                    "' yet — pass --host-cmd '<interpreter> <file>' to host any language";
    return false;
  }
  return true;
}

// ── the child's packets → engine objects ─────────────────────────────
// The protocol IS the API: a scene packet becomes a Scene, a frame packet
// patches one. Shared by the IDE shell and the selftest — one truth.

inline Scene sceneFromHost(const json::Value& v, int worldW, int worldH) {
  Scene s;
  s.name = v.at("name").str_or("game");
  s.bg = v.at("bg").str_or("#0b0e1a");
  s.gravity = static_cast<float>(v.at("gravity").num_or(0));
  s.magnet = static_cast<float>(v.at("magnet").num_or(0));
  const auto& cam = v.at("camera");
  if (cam.is(json::Kind::Obj)) {
    s.camera.x = static_cast<float>(cam.at("x").num_or(worldW / 2.f));
    s.camera.y = static_cast<float>(cam.at("y").num_or(worldH / 2.f));
    s.camera.zoom = static_cast<float>(cam.at("zoom").num_or(1));
  } else {
    s.camera.x = worldW / 2.f;                     // center the world by default
    s.camera.y = worldH / 2.f;
    s.camera.zoom = 1;
  }
  for (const auto& e : v.at("entities").arr) {
    Entity en;
    en.name = e.at("name").str_or("");
    en.tag = e.at("tag").str_or("");
    en.shape = e.at("shape").str_or("rect");
    en.text = e.at("text").str_or("");
    en.x = static_cast<float>(e.at("x").num_or(0));
    en.y = static_cast<float>(e.at("y").num_or(0));
    en.w = static_cast<float>(e.at("w").num_or(32));
    en.h = static_cast<float>(e.at("h").num_or(32));
    en.vx = static_cast<float>(e.at("vx").num_or(0));
    en.vy = static_cast<float>(e.at("vy").num_or(0));
    en.rot = static_cast<float>(e.at("rot").num_or(0));
    en.spin = static_cast<float>(e.at("spin").num_or(0));
    en.tsize = static_cast<float>(e.at("tsize").num_or(20));
    en.color = e.at("color").str_or("#8b5cf6");
    en.alive = e.at("visible").num_or(1) != 0;
    if (!en.name.empty()) s.entities.push_back(en);
  }
  return s;
}

// apply a frame patch: move/resize/recolor by name, spawn new names,
// remove deleted ones, mirror score, take the camera, surface messages
inline void applyFrame(Game& g, const HostFrame& f) {
  if (f.set.is(json::Kind::Arr))
    for (const auto& p : f.set.arr) {
      const std::string name = p.at("name").str_or("");
      if (name.empty()) continue;
      Entity* e = nullptr;
      for (auto& cand : g.scene.entities)
        if (cand.name == name) { e = &cand; break; }
      if (e == nullptr) {
        g.scene.entities.emplace_back();
        e = &g.scene.entities.back();
        e->name = name;
      }
      e->x = static_cast<float>(p.at("x").num_or(e->x));
      e->y = static_cast<float>(p.at("y").num_or(e->y));
      e->w = static_cast<float>(p.at("w").num_or(e->w));
      e->h = static_cast<float>(p.at("h").num_or(e->h));
      e->vx = static_cast<float>(p.at("vx").num_or(e->vx));
      e->vy = static_cast<float>(p.at("vy").num_or(e->vy));
      e->rot = static_cast<float>(p.at("rot").num_or(e->rot));
      e->spin = static_cast<float>(p.at("spin").num_or(e->spin));
      e->tsize = static_cast<float>(p.at("tsize").num_or(e->tsize));
      e->color = p.at("color").str_or(e->color);
      e->shape = p.at("shape").str_or(e->shape);
      e->tag = p.at("tag").str_or(e->tag);
      e->text = p.at("text").str_or(e->text);
      if (p.at("visible").is(json::Kind::Num)) e->alive = p.at("visible").num_or(1) != 0;
    }
  if (f.del.is(json::Kind::Arr))
    for (const auto& d : f.del.arr) {
      const std::string name = d.str_or("");
      for (auto& e : g.scene.entities)
        if (e.name == name) e.alive = false;
    }
  if (f.vars.is(json::Kind::Obj)) {
    const auto* sc = f.vars.find("score");
    if (sc && sc->is(json::Kind::Num)) g.score = static_cast<int>(sc->num);
  }
  if (f.camera.is(json::Kind::Obj)) {
    g.scene.camera.x = static_cast<float>(f.camera.at("x").num_or(g.scene.camera.x));
    g.scene.camera.y = static_cast<float>(f.camera.at("y").num_or(g.scene.camera.y));
    g.scene.camera.zoom = static_cast<float>(f.camera.at("zoom").num_or(g.scene.camera.zoom));
  }
  if (!f.say.empty()) g.say(f.say, 1.6f);
  if (!f.banner.empty()) { g.say(f.banner, 3.f); g.flash = 0.5f; }
}

} // namespace dxn3
