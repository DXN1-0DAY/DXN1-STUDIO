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
  bool rel = false;         // the number rides from where you stand (goto +N/-N)
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

  // the swap's family: :s/old/new — the verb is ONE letter, the pair
  // rides after it separated by slashes. The '/' makes the verb token,
  // so the split-by-space rule steps aside for exactly this prefix.
  if (line.rfind("s/", 0) == 0 || line.rfind("sa/", 0) == 0) {
    const bool all = line.rfind("sa/", 0) == 0;
    c.verb = all ? "sa" : "s";
    c.arg = std::string(line.substr(all ? 3 : 2));
    // the old/new pair is validated by its handler (an empty old is a
    // refusal there); here only the delimiter law: at least one '/'
    if (c.arg.find('/') == std::string::npos)
      c.error = all ? "usage: :sa/old/new — the pair rides after slashes"
                    : "usage: :s/old/new — the pair rides after slashes";
    return c;
  }

  // a bare number is vim's law: :42 jumps the editor to line 42 —
  // the goto's absolute form, spelled the way the hand thinks it.
  {
    bool allDigits = !line.empty();
    for (const char ch : line)
      if (ch < '0' || ch > '9') { allDigits = false; break; }
    if (allDigits) {
      c.verb = "goto";
      c.arg = std::string(line);
      double d = 0;
      auto [p2, ec] = std::from_chars(line.data(), line.data() + line.size(), d);
      if (ec == std::errc{} && d >= 1 && d <= 99999) {
        c.num = static_cast<float>(d);
        c.rel = false;
      } else {
        c.error = "usage: :<line> — 1..99999";
      }
      return c;
    }
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
             c.verb == "recent" || c.verb == "open" ||
             c.verb == "o" || c.verb == "e") {
    // optional path argument — a bare :open reopens the ledger's head
  } else if (c.verb == "snip") {
    needsArg("usage: :snip <name> — fn tick key hit start loop ifelse class try imports main");
  } else if (c.verb == "template") {
    needsArg("usage: :template <name> — blank, shooter, cards, background, "
             "flappy, bounce, pong");
  } else if (c.verb == "goto") {
    // a bare number is the absolute line; +N/-N ride from the hand
    if (!c.arg.empty() && (c.arg[0] == '+' || c.arg[0] == '-')) {
      const std::string digits = c.arg.substr(1);
      double d = 0;
      bool good = false;
      if (!digits.empty()) {
        const auto [p, ec] = std::from_chars(digits.data(),
                                             digits.data() + digits.size(),
                                             d);
        good = ec == std::errc{} && p == digits.data() + digits.size() &&
               d > 0.f && d <= 99999.f;
      }
      if (!good)
        c.error = "usage: :goto <line> | :goto +N | :goto -N";
      else {
        c.num = static_cast<float>(c.arg[0] == '-' ? -d : d);
        c.rel = true;
      }
    } else {
      number(1.f, 99999.f, "usage: :goto <line> | :goto +N | :goto -N");
    }
  } else if (c.verb == "bm") {
    // a bare :bm leaps to the next pin; a number takes the Nth
    if (!c.arg.empty())
      number(1.f, 99999.f,
             "usage: :bm <pin number> — a bare :bm leaps to the next pin");
  } else if (c.verb == "changes") {
    // a bare :changes lists the census; a number leaps to the Nth
    // touch; a word asks which touched lines speak it
    if (!c.arg.empty()) {
      const bool numeric =
          std::all_of(c.arg.begin(), c.arg.end(), [](unsigned char ch) {
            return std::isdigit(ch) != 0;
          });
      if (numeric) {
        number(1.f, 99999.f,
               "usage: :changes [n | word] — a bare verb lists the touched "
               "lines; a number leaps to the Nth; a word asks which "
               "touched lines speak it");
      } else if (c.arg.find(' ') != std::string::npos) {
        c.error = "usage: :changes [n | word] — a number leaps, one word "
                  "asks; the word carries no spaces";
      }
    }
  } else if (c.verb == "macro") {
    // a bare :macro plays the take once; :macro N runs it N times
    if (!c.arg.empty())
      number(1.f, 99.f,
             "usage: :macro [n] — a bare :macro plays once; a number "
             "runs the take N times");
  } else if (c.verb == "shuffle") {
    // a bare :shuffle rolls a seed; a number deals the same order always
    if (!c.arg.empty())
      number(0.f, 999999999.f,
             "usage: :shuffle [seed] — a bare :shuffle rolls a seed; "
             "the same seed deals the same order");
  } else if (c.verb == "crew") {
    // a bare :crew dissolves the hands; a number plants that many more
    if (!c.arg.empty())
      number(1.f, 99.f,
             "usage: :crew [n] — a bare :crew bows the hands out; a number "
             "plants that many hands below");
  } else if (c.verb == "drift") {
    // a bare :drift lists the amber census; a number leaps to the Nth
    if (!c.arg.empty())
      number(1.f, 99999.f,
             "usage: :drift [n] — a bare verb lists the drifted lines; "
             "a number leaps to the Nth (:diff asks the disk first)");
  } else if (c.verb == "diff") {
    // a look, never an edit — the page against the disk
  } else if (c.verb == "count") {
    // a bare :count counts the searchlight's query; :count <word> the word
  } else if (c.verb == "help") {
    // a bare :help lists every verb; :help <verb> whispers that verb's law
    if (!c.arg.empty() && c.arg.find(' ') != std::string::npos)
      c.error = "usage: :help [verb] — one verb at a time";
  } else if (c.verb == "q" || c.verb == "wq" || c.verb == "fit" ||
             c.verb == "reset" || c.verb == "new" || c.verb == "diff" ||
             c.verb == "ruler" || c.verb == "stats" || c.verb == "minimap" ||
             c.verb == "trim" || c.verb == "cases" || c.verb == "sort" ||
             c.verb == "rsort" || c.verb == "upper" || c.verb == "lower" ||
             c.verb == "title" || c.verb == "uniq" || c.verb == "rev" ||
             c.verb == "indent" || c.verb == "dedent" ||
             c.verb == "lift" || c.verb == "drop" || c.verb == "dup" ||
             c.verb == "join" ||
             c.verb == "mark" || c.verb == "marks" || c.verb == "zen" ||
             c.verb == "center" ||
             c.verb == "hist" || c.verb == "undo" || c.verb == "redo" ||
             c.verb == "words" || c.verb == "todo" ||
             c.verb == "jumps" || c.verb == "relnum" ||
             c.verb == "wrap" ||
             c.verb == "record" ||
             c.verb == "fresh") {
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
    return " verbs: scene open recent template snip goto zoom fit reset ruler stats minimap w wq q screenshot magnet gravity help crew count";
  const size_t sp = typed.find(' ');
  const std::string verb(sp == std::string_view::npos ? typed
                                                      : typed.substr(0, sp));
  if (verb == "scene") return " :scene <file.dxn1.json>";
  if (verb == "zoom") return " :zoom in | out | <0.3-4>";
  if (verb == "fit") return " :fit — zoom to fit the scene";
  if (verb == "o")
    return " :o [file] — :open in the vim tongue; the ledger whispers";
  if (verb == "e")
    return " :e [file] — :open in the vim tongue (the disk's page)";
  if (verb == "open")
    return " :open [file] — load a script; the hand returns where it left; "
           "a bare :open reopens the ledger's head";
  if (verb == "recent")
    return " :recent [name] — reopen a file you had open; the hand "
           "returns where it left";
  if (verb == "snip")
    return " :snip <name> — fn tick key hit start loop ifelse class try imports main";
  if (verb == "template")
    return " :template <name> — blank shooter cards background flappy bounce pong";
  if (verb == "goto")
    return " :goto <line> — jump the editor to a line; +N/-N ride from the hand";
  if (verb == "mark")
    return " :mark — plant/pull a pin on this line; F2 leaps between pins";
  if (verb == "marks") return " :marks — list every pin in the file";
  if (verb == "bm")
    return " :bm [n] — leap to a pin; a bare :bm takes the next, wrapping";
  if (verb == "reset") return " :reset — back to spawn";
  if (verb == "ruler") return " :ruler — toggle the 79/99 column guides";
  if (verb == "minimap") return " :minimap — toggle the document's map rail";
  if (verb == "zen")
    return " :zen — the rail rests, the body breathes; :zen wakes it and "
           "replays its ledger";
  if (verb == "trim")
    return " :trim — sweep every line's trailing whitespace, one undo step";
  if (verb == "cases")
    return " :cases — find respects case exactly (Aa), or forgives (default)";
  if (verb == "sort")
    return " :sort — order the selected lines; all-number beds count "
           "(2 before 10)";
  if (verb == "rsort")
    return " :rsort — the selected lines land Z before A; all-number beds "
           "count down";
  if (verb == "upper")
    return " :upper — the selection SHOUTS, one undo step";
  if (verb == "lower")
    return " :lower — the selection whispers, one undo step";
  if (verb == "title")
    return " :title — every word's first letter stands up";
  if (verb == "uniq")
    return " :uniq — lines that repeat back-to-back say it once";
  if (verb == "sa")
    return " :sa/old/new — the swap's other face: the WHOLE document "
           "is the bed; :sa//new borrows the searchlight's query";
  if (verb == "s")
    return " :s/old/new — replace every exact old with new on the "
           "selection's lines; an empty old (:s//new) speaks the "
           "searchlight's query";
  if (verb == "rev")
    return " :rev — flip the selection's line order, no alphabet invited";
  if (verb == "shuffle")
    return " :shuffle [seed] — deal the selection's lines into random "
           "order; the seed replays the deal";
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
  if (verb == "join")
    return " :join — fold the selection's lines into one, single spaces between";
  if (verb == "hist")
    return " :hist — the undo ledger, listed (newest first)";
  if (verb == "undo")
    return " :undo — walk the ledger back one step (ctrl+z's twin)";
  if (verb == "redo")
    return " :redo — step forward again (ctrl+y's twin)";
  if (verb == "words")
    return " :words — the census: the document's most-said words, counted "
           "(case forgiven)";
  if (verb == "todo")
    return " :todo — the marker hunt: TODO/FIXME/XXX/HACK, listed with "
           "their lines";
  if (verb == "jumps")
    return " :jumps — the lines the hand leapt to, newest first";
  if (verb == "changes")
    return " :changes [n | word] — the lines this session wrote; a bare "
           "verb lists, a number leaps, a word asks which touched lines "
           "speak it";
  if (verb == "record")
    return " :record — the recorder: start, run verbs, :record again to "
           "end; :macro replays";
  if (verb == "macro")
    return " :macro [n] — replay the register in recorded order; a "
           "number runs the take N times";
  if (verb == "fresh")
    return " :fresh — the disk's truth wins the page back; the hand "
           "returns where it left";
  if (verb == "center")
    return " :center — the view centers on your hand (z.'s law)";
  if (verb == "relnum")
    return " :relnum — the gutter counts from the hand (the vim way); "
           ":relnum wakes the absolutes";
  if (verb == "wrap")
    return " :wrap — the fold: long lines break into the pane at the "
           "last space that fits; a second :wrap wakes the slide";
  if (verb == "crew")
    return " :crew [n] — the crew: a number plants that many hands below "
           "yours; type once and every hand writes; a bare :crew bows "
           "them out";
  if (verb == "count")
    return " :count [word] — the census of a query: a bare :count counts "
           "the searchlight's query everywhere; a word counts itself";
  if (verb == "stats") return " :stats — lines, words, chars, where you stand";
  if (verb == "diff")
    return " :diff — the page against the disk: added, changed, removed — "
           "a look, not a save";
  if (verb == "drift")
    return " :drift [n] — the amber census: a bare verb lists the lines "
           "that disagree with the disk, a number leaps to the Nth";
  if (verb == "w")
    return " :w [file] — save the session's work; a .bak is kept";
  if (verb == "wq") return " :wq — save and quit";
  if (verb == "q") return " :q — quit";
  if (verb == "screenshot") return " :screenshot [file.png]";
  if (verb == "magnet") return " :magnet <0-400> px";
  if (verb == "gravity") return " :gravity <-3000-3000>";
  if (verb == "help") return " :help [verb] — the verbs, or one verb's law";
  return "";
}

} // namespace dxn3
