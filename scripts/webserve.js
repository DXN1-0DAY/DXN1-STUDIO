#!/usr/bin/env node
// ============================================================
// DXN1 STUDIO 3 — zero-dependency web preview server.
// `dxn3` (or node scripts/webserve.js [port]) serves the renderer
// on localhost so the studio runs in any browser, no Electron
// needed. The renderer falls back to its demo filesystem — the UI
// never dies, it just says "demo" honestly in the statusbar.
// ============================================================
"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");
const { exec } = require("child_process");

const ROOT = path.join(__dirname, "..", "renderer");
const PORT = Math.min(65535, Math.max(1024, Number(process.argv[2]) || 8388));
const OPEN = process.argv.includes("--open");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
  ".ico": "image/x-icon", ".woff2": "font/woff2",
};

const server = http.createServer((req, res) => {
  const url = (req.url || "/").split("?")[0];
  let rel = url === "/" ? "index.html" : decodeURIComponent(url).replace(/^\/+/, "");
  const file = path.normalize(path.join(ROOT, rel));
  // the one rule: nobody leaves the renderer folder
  if (!file.startsWith(ROOT + path.sep) && file !== ROOT) {
    res.writeHead(403); res.end("forbidden"); return;
  }
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); res.end("not found"); return; }
    res.writeHead(200, {
      "Content-Type": MIME[path.extname(file).toLowerCase()] || "application/octet-stream",
      "Cache-Control": "no-store",
    });
    res.end(buf);
  });
});

server.listen(PORT, "127.0.0.1", () => {
  const url = `http://127.0.0.1:${PORT}`;
  console.log("");
  console.log("  \u001b[1;36mDXN1 STUDIO 3\u001b[0m — web preview");
  console.log("  \u001b[2mopen:\u001b[0m " + url);
  console.log("  \u001b[2mstop: Ctrl+C\u001b[0m");
  console.log("");
  if (OPEN) {
    const opener = process.platform === "darwin" ? "open"
      : process.platform === "win32" ? "start" : "xdg-open";
    exec(`${opener} ${url}`, () => {});
  }
});
