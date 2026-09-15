// dxn3 native — zero-dependency PNG screenshot writer (C++23).
// Encodes 0xRRGGBB frames as a truecolor PNG by hand: crc32 + adler32
// checksums, zlib stream with stored (uncompressed) deflate blocks.
// No libpng, no zlib — every byte on purpose, every byte testable.
#pragma once

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

namespace dxn3 {

// ---- checksums (with well-known test vectors in the selftest) ----

inline std::uint32_t crc32(std::string_view data) {
  std::uint32_t c = 0xFFFFFFFFu;
  for (unsigned char b : data) {
    c ^= b;
    for (int k = 0; k < 8; ++k)
      c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1)));
  }
  return ~c;
}

inline std::uint32_t adler32(std::string_view data) {
  std::uint32_t a = 1, b = 0;
  for (unsigned char ch : data) {
    a = (a + ch) % 65521u;
    b = (b + a) % 65521u;
  }
  return (b << 16) | a;
}

namespace png_detail {

inline void be32(std::string& out, std::uint32_t v) {
  out += char(v >> 24); out += char(v >> 16); out += char(v >> 8); out += char(v);
}

inline void le16(std::string& out, std::uint32_t v) {
  out += char(v & 0xFF); out += char((v >> 8) & 0xFF);
}

inline void chunk(std::string& out, const char* type, const std::string& data) {
  be32(out, static_cast<std::uint32_t>(data.size()));
  const std::string body = std::string(type) + data;
  out += body;
  be32(out, crc32(body));
}

} // namespace png_detail

// Writes a truecolor (8-bit RGB) PNG. Returns "" on success, else an
// honest error detail. px is row-major, size w*h, values 0xRRGGBB.
inline std::string writePng(const std::string& path, int w, int h,
                            const std::vector<std::uint32_t>& px) {
  if (w <= 0 || h <= 0) return "png: bad dimensions";
  if (px.size() != static_cast<size_t>(w) * h)
    return "png: pixel buffer is " + std::to_string(px.size()) +
           ", expected " + std::to_string(size_t(w) * h);

  // raw scanlines: one filter byte (0 = none) per row, 3 bytes per pixel
  std::string raw;
  raw.reserve(static_cast<size_t>(h) * (1 + 3 * w));
  for (int y = 0; y < h; ++y) {
    raw += '\0';
    for (int x = 0; x < w; ++x) {
      const std::uint32_t c = px[static_cast<size_t>(y) * w + x];
      raw += char((c >> 16) & 0xFF);
      raw += char((c >> 8) & 0xFF);
      raw += char(c & 0xFF);
    }
  }

  // zlib stream: header + stored deflate blocks (max 65535 bytes each)
  std::string idat;
  idat += '\x78'; idat += '\x01';                     // CM=8 CINFO=7, fastest
  const size_t n = raw.size();
  for (size_t off = 0; off < n || off == 0; off += 65535) {
    const size_t len = std::min<size_t>(65535, n - off);
    const bool last = (off + len >= n);
    idat += last ? '\x01' : '\x00';                   // BFINAL + BTYPE=00
    png_detail::le16(idat, static_cast<std::uint32_t>(len));
    png_detail::le16(idat, static_cast<std::uint32_t>(0xFFFF - len));  // NLEN
    idat += raw.substr(off, len);
    if (last) break;
  }
  png_detail::be32(idat, adler32(raw));

  std::string out;
  out += '\x89'; out += 'P'; out += 'N'; out += 'G';
  out += '\x0d'; out += '\x0a'; out += '\x1a'; out += '\x0a';
  std::string ihdr;
  png_detail::be32(ihdr, static_cast<std::uint32_t>(w));
  png_detail::be32(ihdr, static_cast<std::uint32_t>(h));
  ihdr += '\x08';                                     // bit depth
  ihdr += '\x02';                                     // color type: truecolor
  ihdr += '\0'; ihdr += '\0'; ihdr += '\0';           // compression/filter/interlace
  png_detail::chunk(out, "IHDR", ihdr);
  png_detail::chunk(out, "IDAT", idat);
  png_detail::chunk(out, "IEND", "");

  std::FILE* f = std::fopen(path.c_str(), "wb");
  if (!f) return "png: cannot open " + path + " for writing";
  const size_t wrote = std::fwrite(out.data(), 1, out.size(), f);
  std::fclose(f);
  if (wrote != out.size()) return "png: short write for " + path;
  return "";
}

} // namespace dxn3
