// ASTEROIDS in the DXN1 STUDIO — the classic, on the engine's wire.
// run:  dxn3 sdk/examples/asteroids.js
// left/right turn · w (or jump) thrusts · space fires · the discs drift.
// The ship IS facing you: a real rotated tri (the engine renders rot
// since v3.1.10 — the nose-dot lie is retired). The nose survives as
// a thrust flame: it speaks only while you burn, and GLOWS while it
// does (the engine's light, spent on honest exhaust).
// v3.1.43 — the field learned the radar law: a rock's alpha is its
// distance to your hull (30 px burns full, 100 px ghosts to a 0.4
// floor), so the danger literally brightens as it closes in. Fresh
// rings DRIFT IN (1.5 s from nothing to the radar's truth), and a
// shot dissolves over its last quarter second instead of winking out.
// v3.1.69 — the wear audit came for the field: a SPLIT is a small
// detonation, so each child rock is BORN with a bloom of glow 2,
// worn by the game's own 3/s staircase (the tetris lock-bloom law,
// ported; the ledger forgets a rock the tick it dies), and the
// thrust flame's light stopped lying — it no longer snaps from 4 to
// 0 the tick the burn dies: the thrust key LIGHTS it whole that very
// frame (the key handler may patch fields — decay-before-spawn is
// not enough when the key arrives after the tick), the burn holds
// it at 4 while it lasts, and release wears it down the burn's own
// linear staircase to dark. Refined: the walk starts at BIRTH —
// glow = 4 * burn / 0.12, an honest spend-down, not a hold-then-cut.
// v3.1.71 — every transient light rides ONE ledger: the SHOT too is
// born with a bloom of glow 2 (the muzzle flash), worn by the same
// 3/s staircase, forgotten the tick the shot dies or dissolves.
// v3.1.86 — THE SHIP WEARS THE LIVES' LOW LIGHT (the cards hand-label
// law, third transplant): the hull's glow is the lives' countdown —
// quiet at three, a faint ring (1) at two, BRIGHT (2) when one hull
// stands between you and the field — the last ship burns, and the
// say says so. A fresh run pours the quiet back.
const dxn3 = require("dxn3");
const { circle, tri, label, destroy, background, vars, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#050814");

const hud = label("hud", 2, 2, "ASTEROIDS  ·  turn w/space  ·  lives 3");
const ship = tri("ship", W / 2 - 4, H / 2 - 5, 9, 11, "#8b5cf6");
ship.tag = "ship";
const nose = circle("nose", W / 2, H / 2, 3, 3, "#fbbf24");  // untagged:
                                                             // the flame
                                                             // shows, the
                                                             // core is hit
let rot = 0, vx = 0, vy = 0, nowDt = 0, safe = 0, gunCool = 0, burn = 0;
let lives = 3, score = 0, gen = 0, uid = 0, ringAge = 9;
const rocks = new Map();                 // name -> { size }
const bullets = new Map();               // name -> seconds left to live
const blooms = new Map();                // name -> transient bloom left
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
  ringAge = 0;                            // the new ring starts ghostly
}

// the radar law: alpha is proximity. Inside 30 px the rock burns at
// full light; by 100 px it has sunk to the 0.4 floor. Danger you can
// SEE closing in — the wear is recomputed every tick.
function radarWear(e) {
  const dx = e.x - (ship.x + 4), dy = e.y - (ship.y + 5);
  const d = Math.sqrt(dx * dx + dy * dy);
  const far = Math.max(0, Math.min(1, (d - 30) / 70));
  e.alpha = (1 - 0.6 * far) * Math.min(1, ringAge / 1.5);
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
    // a split is a small detonation: the children BLOOM (glow 2, worn
    // by the tick's own 3/s staircase) — a fresh ring's rocks do not,
    // they have the drift-in fade for their entrance
    const a = spawnRock(`rock${gen}_${++uid}a`, lastX[name] - size, lastY[name], size - 5);
    a.glow = 2; blooms.set(a.name, 2);
    const b = spawnRock(`rock${gen}_${++uid}b`, lastX[name] + size, lastY[name], size - 5);
    b.glow = 2; blooms.set(b.name, 2);
  }
  return pts;
}

function resetShip() {
  ship.x = W / 2 - 4; ship.y = H / 2 - 5; vx = 0; vy = 0; rot = 0; safe = 2.2;
  // NOTE: no flash reset here — resetShip runs at the END of the hit
  // handler, AFTER the bleach is set; clearing it would kill the very
  // scar the hit just earned. The 3/s decay in on.tick is the wear.
}

on.tick((d) => {
  nowDt = d;
  gunCool = Math.max(0, gunCool - d);
  ringAge += d;                           // a fresh ring fades up to full
  if (safe > 0) {
    safe -= d;
    ship.visible = Math.floor(safe * 10) % 2 === 0 ? 1 : 0;  // the blink
    nose.visible = ship.visible;
    if (safe <= 0) { ship.visible = 1; nose.visible = 1; }
  }
  // friction — space is thick with it
  vx *= 1 - Math.min(0.9, 0.55 * d);
  vy *= 1 - Math.min(0.9, 0.55 * d);
  // the hull turns for real now — the tri's apex rides the heading,
  // and the flame answers one honest question: burning, or coasting?
  ship.rot = rot + 180;
  burn = Math.max(0, burn - d);
  nose.visible = burn > 0 ? 1 : 0;
  // the flame's light WEARS with the burn's own age — born whole at
  // the thrust (burn 0.12), an honest linear walk down to dark. The
  // old law here snapped 4 -> 0 the tick the burn died: a hard cut
  // is not the house's staircase.
  nose.glow = 4 * Math.min(1, burn / 0.12);
  // the split blooms wear at the house's 3/s — and the ledger
  // forgets a rock the tick it dies (what leaves the stage takes
  // its light with it)
  for (const [nm, g] of blooms) {
    const e = dxn3.find(nm);
    const ng = Math.max(0, g - 3 * d);
    if (!e || ng === 0) { blooms.delete(nm); if (e) e.glow = 0; }
    else { blooms.set(nm, ng); e.glow = Math.round(ng * 1000) / 1000; }
  }
  // the hit's bleach WEARS OFF — 3/s, the honest staircase. The old
  // comment here claimed "the engine does the fading": a lie the
  // cards/snake rounds buried. The studio keeps the last light a
  // wire game sent; a flash with no decay is a bleach FOREVER.
  if (ship.flash > 0) ship.flash = Math.max(0, Math.round((ship.flash - 3 * d) * 1000) / 1000);
  if (nose.flash > 0) nose.flash = Math.max(0, Math.round((nose.flash - 3 * d) * 1000) / 1000);
  nose.x = ship.x + Math.sin(rot * Math.PI / 180) * 7 - 1;
  nose.y = ship.y - Math.cos(rot * Math.PI / 180) * 7 - 1;
  lastX.ship = ship.x; lastY.ship = ship.y;
  for (const [name, info] of rocks) {
    const e = dxn3.find(name);
    if (!e) { rocks.delete(name); continue; }
    lastX[name] = e.x; lastY[name] = e.y;
    wrap(e, info.size);
    radarWear(e);                         // the radar never sleeps
  }
  for (const [name, left] of [...bullets]) {
    const b = dxn3.find(name);
    if (!b) { bullets.delete(name); continue; }
    wrap(b, 2);
    const fresh = left - d;
    if (fresh <= 0) { bullets.delete(name); destroy(name); }
    else {
      bullets.set(name, fresh);
      b.alpha = Math.max(0, Math.min(1, fresh / 0.25));  // dissolve, don't wink
    }
  }
  wrap(ship, 6);
});

on.key((k) => {
  const turn = 210 * nowDt;
  if (k === "left" || k === "a") rot -= turn;
  if (k === "right" || k === "d") rot += turn;
  if (k === "jump" || k === "w") {
    burn = 0.12;                       // the flame lives while the burn does
    nose.glow = 4;                     // LIT WHOLE the very frame the key
                                       // arrives — the key handler runs
                                       // after the tick, so a glow left to
                                       // the tick would render already faded
    nose.visible = 1;
    vx += Math.sin(rot * Math.PI / 180) * 190 * nowDt;
    vy += -Math.cos(rot * Math.PI / 180) * 190 * nowDt;
  }
  if (k === "space" && gunCool <= 0 && bullets.size < 8) {
    gunCool = 0.16;
    const name = `bul${gen}_${++uid}`;
    const b = circle(name, nose.x + 1, nose.y + 1, 3, 3, "#facc15");
    b.vx = Math.sin(rot * Math.PI / 180) * 230 + vx * 0.5;
    b.vy = -Math.cos(rot * Math.PI / 180) * 230 + vy * 0.5;
    b.glow = 2;                          // the muzzle flash: BORN WHOLE
    blooms.set(name, 2);                 // (one ledger for every
    bullets.set(name, 0.9);              // transient light), worn 3/s
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
    ship.flash = 1;                     // the hit BLEACHES — and the
    nose.flash = 1;                     // wire game owns the decay
                                        // (3/s in on.tick; the studio
                                        // keeps the last light sent)
    if (lives <= 0) {
      win("game over — the field claims another hull");
      console.log(`game over — score ${score}`);
      score = 0; lives = 3; gen += 1;
      ship.glow = 0;                    // a fresh run pours the quiet back
      for (const name of [...rocks.keys()]) { rocks.delete(name); destroy(name); }
      buildRocks();
      hud.text = "ASTEROIDS  ·  turn w/space  ·  lives 3";
      vars({ score });
    } else {
      say(lives === 1
        ? "hull hit — 1 left — the last ship burns"
        : `hull hit — ${lives} left`);
      console.log(lives === 1
        ? "hull hit — 1 left — the last ship burns"
        : `hull hit — ${lives} left`);
    }
    ship.glow = Math.max(0, Math.min(2, 3 - lives));   // the lives' low
                                                       // light: 3 quiet,
                                                       // 2 a ring, 1 burns
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
