/**
 * dxn3 SDK — write a game in JavaScript (node), the studio renders it.
 *
 *   const { rect, label, vars, on, run } = require("./sdk/dxn3.js");
 *
 *   const ship = rect("ship", W >> 1, H - 12, 12, 5, "#8b5cf6");
 *   ship.tag = "ship";
 *
 *   on.key(k => { if (k === "left") ship.x -= 1; });
 *   on.tick(dt => { ... });
 *   on.hit((a, b) => { ... });
 *   run();
 *
 * The engine owns rendering, input and collision; this module speaks the
 * line-JSON protocol on stdio. console.log goes to the studio's console.
 */
const readline = require("readline");

const _hello = JSON.parse(require("fs").readFileSync(0, "utf8").split("\n")[0] || "{}");
var W = _hello.w | 0 || 100;
var H = _hello.h | 0 || 46;

let dt = 0.0;
const E = new Map();
const _scene = { t: "scene", name: "game", bg: "#0b0e1a", gravity: 0, entities: [] };
let _dels = [];
let _vars = {};
let _cam = {};
const _cb = { tick: [], key: [], hit: [], start: [] };

function _send(o) { process.stdout.write(JSON.stringify(o) + "\n"); }

function _mk(name, d) {
  if (E.has(name)) throw new Error("duplicate entity name: " + name);
  d.visible = 1;
  E.set(name, d);
  _scene.entities.push(d);
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
  return _mk(name, { name, shape: "text", x, y, w: Math.max(1, String(text).length), h: 2, text: String(text), color });
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
  const rl = readline.createInterface({ input: process.stdin, terminal: false });
  rl.on("line", line => {
    let pkt;
    try { pkt = JSON.parse(line); } catch { console.log(line.slice(0, 200)); return; }
    if (pkt.t !== "tick") return;
    dt = +pkt.dt || 0;
    const keys = pkt.keys || {};
    if (!started) { _cb.start.forEach(f => f()); started = true; }
    for (const e of E.values()) {           // physics-lite
      if (e.vx) e.x += e.vx * dt;
      if (e.vy) e.y += e.vy * dt;
    }
    _cb.tick.forEach(f => f(dt));
    const held = ["left", "right", "jump", "space"].filter(k => keys[k]);
    held.push(...String(pkt.chars || "").split("").filter(c => c.trim()));
    for (const k of held) _cb.key.forEach(f => f(k));
    for (const pair of pkt.hits || []) {
      const a = E.get(pair[0]), b = E.get(pair[1]);
      if (a && b) _cb.hit.forEach(f => f(a, b));
    }
    _send({ t: "frame", set: [...E.values()], del: _dels, vars: _vars, camera: _cam });
    _dels = [];
    _vars = {};
  });
}

module.exports = { W, H, rect, circle, tri, label, destroy, find,
                   background, gravity, magnet, camera, vars, on, run };
