// dxn3 native — minimal JSON for .dxn1.json scenes (C++23)
// Recursive-descent parser: objects (order-preserving), arrays, strings
// with \uXXXX -> UTF-8, numbers, bools, null. Honest errors via expected.
#pragma once
#include <charconv>
#include <concepts>
#include <cctype>
#include <expected>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace dxn3::json {

class Value;
using Obj = std::vector<std::pair<std::string, Value>>;
using Arr = std::vector<Value>;

enum class Kind { Null, Bool, Num, Str, Arr, Obj };

class Value {
public:
  Kind kind = Kind::Null;
  bool b = false;
  double num = 0;
  std::string str;
  Arr arr;
  Obj obj;

  bool is(Kind k) const { return kind == k; }
  const Value* find(std::string_view key) const {
    for (const auto& [k, v] : obj)
      if (k == key) return &v;
    return nullptr;
  }
  const Value& at(std::string_view key) const {           // Null on miss
    static const Value nil;
    const Value* v = find(key);
    return v ? *v : nil;
  }
  double num_or(double d) const { return kind == Kind::Num ? num : d; }
  std::string str_or(std::string_view d) const {
    return kind == Kind::Str ? str : std::string(d);
  }
};

inline void skip_ws(std::string_view s, size_t& i) {
  while (i < s.size() && std::isspace(static_cast<unsigned char>(s[i]))) ++i;
}

inline std::expected<Value, std::string> parse(std::string_view s);

inline std::expected<Value, std::string> parse_value(std::string_view s, size_t& i) {
  skip_ws(s, i);
  if (i >= s.size()) return std::unexpected("unexpected end of input");
  const char c = s[i];
  if (c == '{') {
    Value v; v.kind = Kind::Obj;
    ++i; skip_ws(s, i);
    if (i < s.size() && s[i] == '}') { ++i; return v; }
    while (true) {
      skip_ws(s, i);
      if (i >= s.size() || s[i] != '"')
        return std::unexpected("expected object key");
      auto key = parse_value(s, i);
      if (!key) return key;
      skip_ws(s, i);
      if (i >= s.size() || s[i] != ':') return std::unexpected("expected ':'");
      ++i;
      auto val = parse_value(s, i);
      if (!val) return val;
      v.obj.emplace_back(key->str, std::move(*val));
      skip_ws(s, i);
      if (i < s.size() && s[i] == ',') { ++i; continue; }
      if (i < s.size() && s[i] == '}') { ++i; return v; }
      return std::unexpected("expected ',' or '}'");
    }
  }
  if (c == '[') {
    Value v; v.kind = Kind::Arr;
    ++i; skip_ws(s, i);
    if (i < s.size() && s[i] == ']') { ++i; return v; }
    while (true) {
      auto val = parse_value(s, i);
      if (!val) return val;
      v.arr.push_back(std::move(*val));
      skip_ws(s, i);
      if (i < s.size() && s[i] == ',') { ++i; continue; }
      if (i < s.size() && s[i] == ']') { ++i; return v; }
      return std::unexpected("expected ',' or ']'");
    }
  }
  if (c == '"') {
    ++i;
    Value v; v.kind = Kind::Str;
    while (i < s.size() && s[i] != '"') {
      if (s[i] == '\\' && i + 1 < s.size()) {
        const char e = s[++i];
        switch (e) {
          case '"': v.str += '"'; break;
          case '\\': v.str += '\\'; break;
          case '/': v.str += '/'; break;
          case 'b': v.str += '\b'; break;
          case 'f': v.str += '\f'; break;
          case 'n': v.str += '\n'; break;
          case 'r': v.str += '\r'; break;
          case 't': v.str += '\t'; break;
          case 'u': {
            if (i + 4 >= s.size()) return std::unexpected("bad \\u escape");
            unsigned cp = 0;
            auto [p, ec] = std::from_chars(s.data() + i + 1, s.data() + i + 5, cp, 16);
            if (ec != std::errc{}) return std::unexpected("bad \\u hex");
            i += 4;
            // UTF-8 encode the codepoint
            if (cp < 0x80) v.str += static_cast<char>(cp);
            else if (cp < 0x800) {
              v.str += static_cast<char>(0xC0 | (cp >> 6));
              v.str += static_cast<char>(0x80 | (cp & 0x3F));
            } else {
              v.str += static_cast<char>(0xE0 | (cp >> 12));
              v.str += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
              v.str += static_cast<char>(0x80 | (cp & 0x3F));
            }
            break;
          }
          default: return std::unexpected("bad escape");
        }
        ++i;
      } else {
        v.str += s[i++];
      }
    }
    if (i >= s.size()) return std::unexpected("unterminated string");
    ++i; // closing quote
    return v;
  }
  if (s.compare(i, 4, "true") == 0) { i += 4; Value v; v.kind = Kind::Bool; v.b = true; return v; }
  if (s.compare(i, 5, "false") == 0) { i += 5; Value v; v.kind = Kind::Bool; v.b = false; return v; }
  if (s.compare(i, 4, "null") == 0) { i += 4; return Value{}; }
  // number
  {
    double d = 0;
    auto [p, ec] = std::from_chars(s.data() + i, s.data() + s.size(), d);
    if (ec != std::errc{}) return std::unexpected("bad value");
    i = static_cast<size_t>(p - s.data());
    Value v; v.kind = Kind::Num; v.num = d; return v;
  }
}

inline std::expected<Value, std::string> parse(std::string_view s) {
  size_t i = 0;
  auto v = parse_value(s, i);
  if (!v) return v;
  skip_ws(s, i);
  if (i != s.size()) return std::unexpected("trailing characters after JSON");
  return v;
}

} // namespace dxn3::json
