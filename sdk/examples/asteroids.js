// ASTEROIDS in the DXN1 STUDIO — the classic, on the engine's wire.
// run:  dxn3 sdk/examples/asteroids.js
// left/right turn · w (or jump) thrusts · space fires · the discs drift.
// The ship's facing is honest geometry: a nose dot orbiting the core.
const dxn3 = require("dxn3");
const { circle, label, destroy, background, vars, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#050814");

const hud = label("hud", 2, 2, "ASTEROIDS  ·  turn w/space  ·  lives 3");
const ship = circle("ship", W / 2, H / 2, 9, 9, "#8b5cf6");
ship.tag = "ship";
const nose = circle("nose", W / 2 + 7, H / 2, 3, 3, "#e9e5ff"); // untagged:
                                                                // the nose
                                                                // looks, the
                                                                // core is hit
let rot = 0, vx = 0, vy = 0, nowDt = 0, safe = 0, gunCool = 0;
let lives = 3, score = 0, gen = 0, uid = 0;
const rocks = new Map();                 // name -> { size }
const bullets = new Map();               // name -> seconds left to live
const lastX = {}, lastY = {};            // where every rock last stood
const SPEED = { 13: 20, 8: 55, 5: 90 };  // smaller rocks fly faster

const clampX = (x) => Math.max(2, Math.min(W - 8, x));
const clampY = (y) => Math.max(2, Math.min(H - 8, y));

function wrap(e, m) {
  if (e.x < -m) e.x = W + m - 1;
  if (e.x > W + m) e.x = -m + 1;
  if (e.y < -m) e.y = H + m - 1;
  if (e.y > H + m) e.y = -m + 1;
}

function spawnRock(name, x, y, size) {
  const r = circle(name, clampX(x), clampY(y), size, size, "#94a3b8");
  r.tag = "rock";
  const a = Math.random() * Math.PI * 2;
  const sp = SPEED[size] || 30;
  r.vx = Math.cos(a) * sp;
  r.vy = Math.sin(a) * sp;
  rocks.set(name, { size });
  return r;
}

function buildRocks() {
  const corners = [[8, 8], [W - 21, 8], [8, H - 21], [W - 21, H - 21]];
  corners.forEach(([cx, cy], i) => {
    spawnRock(`rock${gen}_${i}`, cx + Math.random() * 8, cy + Math.random() * 8, 13);
  });
}

function split(name) {
  // the rock goes; its children spawn where it LAST stood (the entity is
  // already gone by the time the children are named — the ledger remembers)
  const info = rocks.get(name);
  rocks.delete(name);
  destroy(name);
  if (!info) return 0;
  const size = info.size;
  const pts = size === 13 ? 20 : size === 8 ? 50 : 100;
  if (size > 5) {
    spawnRock(`rock${gen}_${++uid}a`, lastX[name] - size, lastY[name], size - 5);
    spawnRock(`rock${gen}_${++uid}b`, lastX[name] + size, lastY[name], size - 5);
  }
  return pts;
}

function resetShip() {
  ship.x = W / 2; ship.y = H / 2; vx = 0; vy = 0; rot = 0; safe = 2.2;
}

on.tick((d) => {
  nowDt = d;
  gunCool = Math.max(0, gunCool - d);
  if (safe > 0) {
    safe -= d;
    ship.visible = Math.floor(safe * 10) % 2 === 0 ? 1 : 0;  // the blink
    nose.visible = ship.visible;
    if (safe <= 0) { ship.visible = 1; nose.visible = 1; }
  }
  // friction — space is thick with it
  vx *= 1 - Math.min(0.9, 0.55 * d);
  vy *= 1 - Math.min(0.9, 0.55 * d);
  // the nose orbits: facing you can SEE
  nose.x = ship.x + Math.sin(rot * Math.PI / 180) * 8 - 2;
  nose.y = ship.y - Math.cos(rot * Math.PI / 180) * 8 - 2;
  lastX.ship = ship.x; lastY.ship = ship.y;
  for (const [name, info] of rocks) {
    const e = dxn3.find(name);
    if (!e) { rocks.delete(name); continue; }
    lastX[name] = e.x; lastY[name] = e.y;
    wrap(e, info.size);
  }
  for (const [name, left] of [...bullets]) {
    const b = dxn3.find(name);
    if (!b) { bullets.delete(name); continue; }
    wrap(b, 2);
    const fresh = left - d;
    if (fresh <= 0) { bullets.delete(name); destroy(name); }
    else bullets.set(name, fresh);
  }
  wrap(ship, 6);
});

on.key((k) => {
  const turn = 210 * nowDt;
  if (k === "left" || k === "a") rot -= turn;
  if (k === "right" || k === "d") rot += turn;
  if (k === "jump" || k === "w") {
    vx += Math.sin(rot * Math.PI / 180) * 190 * nowDt;
    vy += -Math.cos(rot * Math.PI / 180) * 190 * nowDt;
  }
  if (k === "space" && gunCool <= 0 && bullets.size < 8) {
    gunCool = 0.16;
    const name = `bul${gen}_${++uid}`;
    const b = circle(name, nose.x + 1, nose.y + 1, 3, 3, "#facc15");
    b.vx = Math.sin(rot * Math.PI / 180) * 230 + vx * 0.5;
    b.vy = -Math.cos(rot * Math.PI / 180) * 230 + vy * 0.5;
    bullets.set(name, 0.9);
  }
});

on.hit((a, b) => {
  const names = [a.name, b.name];
  const rockName = names.find((n) => rocks.has(n));
  if (!rockName) return;
  if (names.includes("ship")) {
    if (safe > 0) return;
    lives -= 1;
    split(rockName);
    if (lives <= 0) {
      console.log(`game over — score ${score}`);
      score = 0; lives = 3; gen += 1;
      for (const name of [...rocks.keys()]) { rocks.delete(name); destroy(name); }
      buildRocks();
      hud.text = "ASTEROIDS  ·  turn w/space  ·  lives 3";
      vars({ score });
    } else {
      console.log(`hull hit — ${lives} left`);
    }
    hud.text = `ASTEROIDS  ·  turn w/space  ·  lives ${lives}`;
    resetShip();
    return;
  }
  const shot = names.find((n) => bullets.has(n));
  if (!shot) return;
  bullets.delete(shot);
  destroy(shot);
  score += split(rockName);
  hud.text = `ASTEROIDS  ·  turn w/space  ·  lives ${lives}`;
  vars({ score });
  if (rocks.size === 0) {
    gen += 1;
    console.log(`field cleared — score ${score} — a new ring drifts in`);
    buildRocks();
  }
});

buildRocks();
run();
