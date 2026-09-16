// dxn3 native — the command bar parser (C++23), vim-style: `:verb arg`.
// Header-only so the shell and the selftest share one honest grammar:
// unknown verbs, junk numbers and out-of-range values are refused with
// usage, never silently accepted.
#pragma once

#include <charconv>
#include <cmath>
#include <string>
#include <string_view>
#include <vector>

namespace dxn3 {

struct Cmd {
  std::string verb;         // "scene", "zoom", "w", …
  std::string arg;          // raw argument ("" if none)
  float num = 0;            // parsed number for numeric verbs
  std::string error;        // "" = the command is well-formed

  bool ok() const { return error.empty(); }
};

inline Cmd parseCommand(std::string_view line) {
  Cmd c;
  if (!line.empty() && line.front() == ':') line.remove_prefix(1);
  while (!line.empty() && (line.front() == ' ' || line.front() == '\t'))
    line.remove_prefix(1);
  while (!line.empty() && (line.back() == ' ' || line.back() == '\t' ||
                           line.back() == '\r' || line.back() == '\n'))
    line.remove_suffix(1);
  if (line.empty()) {
    c.error = "empty command — try :help";
    return c;
  }

  const size_t sp = line.find(' ');
  if (sp == std::string_view::npos) {
    c.verb = std::string(line);
  } else {
    c.verb = std::string(line.substr(0, sp));
    c.arg = std::string(line.substr(sp + 1));
    while (!c.arg.empty() && (c.arg.back() == ' ' || c.arg.back() == '\t'))
      c.arg.pop_back();
  }

  auto needsArg = [&](const char* usage) {
    if (c.arg.empty()) c.error = usage;
  };
  auto number = [&](float lo, float hi, const char* usage) {
    const std::string& s = c.arg;
    if (s.empty()) { c.error = usage; return; }
    const double v = [&] {
      // try double first so "1.5" and "1500" both work everywhere
      double d = 0;
      auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), d);
      if (ec != std::errc{} || p != s.data() + s.size()) return 0.0 / 0.0; // NaN
      return d;
    }();
    if (std::isnan(v)) { c.error = usage; return; }
    if (v < lo || v > hi) {
      c.error = std::string(usage) + "  (allowed range " +
                std::to_string(static_cast<int>(lo)) + " .. " +
                std::to_string(static_cast<int>(hi)) + ")";
      return;
    }
    c.num = static_cast<float>(v);
  };

  if (c.verb == "scene") {
    needsArg("usage: :scene <file.dxn1.json>");
  } else if (c.verb == "zoom") {
    if (c.arg == "in" || c.arg == "out") return c;
    number(0.3f, 4.f, "usage: :zoom in|out|<factor 0.3..4>");
  } else if (c.verb == "magnet") {
    number(0.f, 400.f, "usage: :magnet <pixels 0..400>");
  } else if (c.verb == "gravity") {
    number(-5000.f, 5000.f, "usage: :gravity <force -5000..5000>");
  } else if (c.verb == "w" || c.verb == "screenshot" ||
             c.verb == "recent" || c.verb == "open") {
    // optional path argument — a bare :open reopens the ledger's head
  } else if (c.verb == "snip") {
    needsArg("usage: :snip <name> — fn tick key hit start loop ifelse class try imports main");
  } else if (c.verb == "template") {
    needsArg("usage: :template <name> — blank, shooter, cards, background, "
             "flappy, bounce, pong");
  } else if (c.verb == "goto") {
    number(1.f, 99999.f, "usage: :goto <line number>");
  } else if (c.verb == "bm") {
    // a bare :bm leaps to the next pin; a number takes the Nth
    if (!c.arg.empty())
      number(1.f, 99999.f,
             "usage: :bm <pin number> — a bare :bm leaps to the next pin");
  } else if (c.verb == "q" || c.verb == "wq" || c.verb == "fit" ||
             c.verb == "reset" || c.verb == "help" || c.verb == "new" ||
             c.verb == "ruler" || c.verb == "stats" || c.verb == "minimap" ||
             c.verb == "trim" || c.verb == "cases" || c.verb == "sort" ||
             c.verb == "rsort" || c.verb == "upper" || c.verb == "lower" ||
             c.verb == "title" || c.verb == "uniq" || c.verb == "rev" ||
             c.verb == "indent" || c.verb == "dedent" ||
             c.verb == "lift" || c.verb == "drop" || c.verb == "dup" ||
             c.verb == "mark" || c.verb == "marks" || c.verb == "zen") {
    if (!c.arg.empty())
      c.error = ":" + c.verb + " takes no argument";
  } else {
    c.error = "no such command: " + c.verb + " — :help lists them";
  }
  return c;
}

// prefix filter for scene names — the completion core, pure and
// selftestable: candidates whose stem starts with `partial`, in order.
inline std::vector<std::string> sceneMatches(std::string_view partial,
                                             const std::vector<std::string>& names) {
  std::vector<std::string> out;
  for (const auto& n : names)
    if (n.rfind(partial, 0) == 0) out.push_back(n);
  return out;
}

// scene-name resolution — the campaign by name, honestly.
// `names` are the bare scene stems ("level-1", …, "playground") as
// enumerated from scenes/. Given what the user typed, return the scene
// file path that should load:
//   - a full path or anything that matches no stem passes through
//     unchanged (loadScene reports ghosts honestly),
//   - an exact stem (with or without "scenes/" or ".dxn1.json") and a
//     UNIQUE prefix of a stem resolve to "scenes/<stem>.dxn1.json",
//   - an AMBIGUOUS prefix returns "" — the caller lists the matches.
inline std::string resolveSceneArg(const std::string& arg,
                                   const std::vector<std::string>& names) {
  std::string stem = arg;
  if (stem.rfind("scenes/", 0) == 0) stem.erase(0, 7);
  const std::string ext = ".dxn1.json";
  if (stem.size() > ext.size() &&
      stem.compare(stem.size() - ext.size(), ext.size(), ext) == 0)
    stem.resize(stem.size() - ext.size());
  if (stem.empty()) return arg;
  const auto matches = sceneMatches(stem, names);
  if (matches.size() == 1) return "scenes/" + matches[0] + ext;
  if (matches.empty()) return arg;      // a path, or a ghost — both honest
  return "";                            // ambiguous — list, don't guess
}

// the whisper: what the bar shows while you type, so the usage is
// visible BEFORE enter. Exact-verb match only — a partial verb gets
// the command list, and unknown verbs get silence (the honest error
// speaks on enter).
inline std::string usageHintFor(std::string_view typed) {
  if (!typed.empty() && typed.front() == ':') typed.remove_prefix(1);
  while (!typed.empty() && typed.front() == ' ') typed.remove_prefix(1);
  if (typed.empty())
    return " verbs: scene open recent template snip goto zoom fit reset ruler stats minimap w wq q screenshot magnet gravity help";
  const size_t sp = typed.find(' ');
  const std::string verb(sp == std::string_view::npos ? typed
                                                      : typed.substr(0, sp));
  if (verb == "scene") return " :scene <file.dxn1.json>";
  if (verb == "zoom") return " :zoom in | out | <0.3-4>";
  if (verb == "fit") return " :fit — zoom to fit the scene";
  if (verb == "open")
    return " :open [file] — load a script; a bare :open reopens the ledger's head";
  if (verb == "recent") return " :recent [name] — reopen a file you had open";
  if (verb == "snip")
    return " :snip <name> — fn tick key hit start loop ifelse class try imports main";
  if (verb == "template")
    return " :template <name> — blank shooter cards background flappy bounce pong";
  if (verb == "goto") return " :goto <line> — jump the editor to a line";
  if (verb == "mark")
    return " :mark — plant/pull a pin on this line; F2 leaps between pins";
  if (verb == "marks") return " :marks — list every pin in the file";
  if (verb == "bm")
    return " :bm [n] — leap to a pin; a bare :bm takes the next, wrapping";
  if (verb == "reset") return " :reset — back to spawn";
  if (verb == "ruler") return " :ruler — toggle the 79/99 column guides";
  if (verb == "minimap") return " :minimap — toggle the document's map rail";
  if (verb == "zen")
    return " :zen — the rail rests, the body breathes; :zen wakes it";
  if (verb == "trim")
    return " :trim — sweep every line's trailing whitespace, one undo step";
  if (verb == "cases")
    return " :cases — find respects case exactly (Aa), or forgives (default)";
  if (verb == "sort")
    return " :sort — order the selected lines, A before B, one undo step";
  if (verb == "rsort")
    return " :rsort — the selected lines land Z before A, one undo step";
  if (verb == "upper")
    return " :upper — the selection SHOUTS, one undo step";
  if (verb == "lower")
    return " :lower — the selection whispers, one undo step";
  if (verb == "title")
    return " :title — every word's first letter stands up";
  if (verb == "uniq")
    return " :uniq — lines that repeat back-to-back say it once";
  if (verb == "rev")
    return " :rev — flip the selection's line order, no alphabet invited";
  if (verb == "indent")
    return " :indent — the selected lines step right, one undo step";
  if (verb == "dedent")
    return " :dedent — the selected lines step back left, one undo step";
  if (verb == "lift")
    return " :lift — the selection's lines step one line up, one undo step";
  if (verb == "drop")
    return " :drop — the selection's lines step one line down, one undo step";
  if (verb == "dup")
    return " :dup — duplicate the selection's lines, the copies sit below";
  if (verb == "stats") return " :stats — lines, words, chars, where you stand";
  if (verb == "w") return " :w [file] — save, a .bak is kept";
  if (verb == "wq") return " :wq — save and quit";
  if (verb == "q") return " :q — quit";
  if (verb == "screenshot") return " :screenshot [file.png]";
  if (verb == "magnet") return " :magnet <0-400> px";
  if (verb == "gravity") return " :gravity <-3000-3000>";
  if (verb == "help") return " :help — list commands";
  return "";
}

} // namespace dxn3
