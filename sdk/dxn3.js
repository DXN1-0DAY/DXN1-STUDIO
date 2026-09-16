/**
 * dxn3 SDK — write a game in JavaScript (node), the studio renders it.
 *
 *   const { rect, label, on, run, dt } = require("dxn3");  // NODE_PATH=sdk
 *
 *   const ship = rect("ship", W >> 1, H - 12, 12, 5, "#8b5cf6");
 *   ship.tag = "ship";
 *
 *   on.key(k => { if (k === "left") ship.x -= 340 * dt; });
 *   on.tick(() => { ... });            // every frame — read dt live
 *   on.hit((a, b) => { ... });         // two tagged entities just overlapped
 *   run();
 *
 * The engine owns rendering, input and collision; this module speaks the
 * line-JSON protocol on stdio. console.log goes to the studio's console.
 * (plain CJS on purpose — the studio's gates keep package.json out of the
 *  tree, and NODE_PATH makes `require('dxn3')` work from anywhere.)
 */
"use strict";

const fs = require("fs");

function _readLineSync() {
  const buf = Buffer.alloc(1);
  let out = "";
  for (;;) {
    const n = fs.readSync(0, buf, 0, 1, null);
    if (n === 0) return out.length ? out : null;   // EOF — the engine left
    if (buf[0] === 0x0a) return out;
    out += String.fromCharCode(buf[0]);
  }
}

// the engine says hello before your module finishes — W and H are ready
// for your very first line of code
const _hello = _readLineSync();
if (_hello === null) {
  console.log("run me from the studio:  dxn3 mygame.js   (not directly)");
  process.exit(1);
}
let W = 100, H = 46;
try { const h = JSON.parse(_hello); W = h.w | 0 || 100; H = h.h | 0 || 46; }
catch { /* defaults hold */ }

let dt = 0.0;                                    // read dt live, every frame
const E = new Map();                             // name -> entity object
const _scene = { t: "scene", name: "game", bg: "#0b0e1a", gravity: 0, entities: [] };
let _dels = [];
let _vars = {};
let _cam = {};
const _cb = { tick: [], key: [], hit: [], start: [] };

function _send(o) { process.stdout.write(JSON.stringify(o) + "\n"); }

function _mk(name, d) {
  d.visible = 1;
  if (E.has(name)) {
    // same name again = a redraw: replace the body in place
    const i = _scene.entities.findIndex((e) => e.name === name);
    if (i >= 0) _scene.entities[i] = d;
  } else {
    _scene.entities.push(d);
  }
  E.set(name, d);
  return d;
}
function rect(name, x, y, w, h, color = "#8b5cf6") {
  return _mk(name, { name, shape: "rect", x, y, w, h, color });
}
function circle(name, x, y, w, h, color = "#facc15") {
  return _mk(name, { name, shape: "circle", x, y, w, h, color });
}
function tri(name, x, y, w, h, color = "#ef4444") {
  return _mk(name, { name, shape: "tri", x, y, w, h, color });
}
function label(name, x, y, text, color = "#e9e5ff") {
  return _mk(name, { name, shape: "text", x, y,
                     w: Math.max(1, String(text).length), h: 2,
                     text: String(text), color });
}
function destroy(name) { if (E.has(name)) { E.delete(name); _dels.push(name); } }
function find(name) { return E.get(name); }
function background(c) { _scene.bg = c; }
function gravity(g) { _scene.gravity = g; }
function magnet(m) { _scene.magnet = m; }
function camera(x, y, zoom = 1) { _cam = { x, y, zoom }; }
function vars(kv) { Object.assign(_vars, kv); }
const on = {
  tick: fn => _cb.tick.push(fn),
  key: fn => _cb.key.push(fn),
  hit: fn => _cb.hit.push(fn),
  start: fn => _cb.start.push(fn),
};

function run() {
  _send(_scene);
  let started = false;
  let pairs = new Set();                 // overlap pairs already reported
  for (;;) {
    const line = _readLineSync();
    if (line === null) break;            // the studio closed the pipe
    let pkt;
    try { pkt = JSON.parse(line); }
    catch { console.log(line.slice(0, 200)); continue; }  // chatter -> console
    if (pkt.t !== "tick") continue;
    dt = +pkt.dt || 0;
    const keys = pkt.keys || {};
    if (!started) { _cb.start.forEach(f => f()); started = true; }
    for (const e of E.values()) {        // physics-lite
      if (e.vx) e.x += e.vx * dt;
      if (e.vy) e.y += e.vy * dt;
    }
    _cb.tick.forEach(f => f(dt));
    const held = ["left", "right", "jump", "space"].filter(k => keys[k]);
    held.push(...String(pkt.chars || "").split("").filter(c => c.trim()));
    for (const k of held) _cb.key.forEach(f => f(k));
    // hits arrive flat: [nameA, nameB, …]. fire on ENTER only — a pair
    // that separates may fire again; a held overlap never spams
    const hs = Array.isArray(pkt.hits) ? pkt.hits : [];
    const seen = new Set();
    for (let i = 0; i + 1 < hs.length; i += 2) {
      const na = String(hs[i]), nb = String(hs[i + 1]);
      const pair = na <= nb ? na + "\u0000" + nb : nb + "\u0000" + na;
      seen.add(pair);
      if (pairs.has(pair)) continue;
      const a = E.get(na), b = E.get(nb);
      if (a && b) _cb.hit.forEach(f => f(a, b));
    }
    pairs = seen;
    _send({ t: "frame", set: [...E.values()], del: _dels,
            vars: _vars, camera: _cam });
    _dels = []; _vars = {};
  }
}

module.exports = { W, H, get dt() { return dt; },
                   rect, circle, tri, label, destroy, find,
                   background, gravity, magnet, camera, vars, on, run };
