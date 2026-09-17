// INVADERS in the DXN1 STUDIO — the classic march, on the engine's wire.
// run:  dxn3 sdk/examples/invaders.js
// left/right steer · space fires · the grid steps, drops and speeds up
// as it thins · parked bullets live off-screen until their gun needs them.
const dxn3 = require("dxn3");
const { rect, label, destroy, find, background, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#050814");

const hud = label("hud", 2, 1, "INVADERS  ·  left/right space  ·  score 0");
const player = rect("player", W >> 1, H - 4, 10, 4, "#8b5cf6");
player.tag = "player";

const ROWS_N = 3, COLS_N = 5;            // the marching order
const POINTS = [30, 20, 10];             // top rows pay best
const aliens = [];                       // 15 named seats, refilled per wave
for (let r = 0; r < ROWS_N; ++r)
  for (let c = 0; c < COLS_N; ++c) {
    const a = rect(`alien-${r}-${c}`, 0, 0, 7, 5, r === 0 ? "#f472b6" : "#fb7185");
    a.tag = "alien";
    a.row = r;
    aliens.push(a);
  }

// the guns' bullets are POOLS: parked at x -999 until fired — the wire
// only moves what changed, so a parked bullet costs nothing to keep
const shots = [];                        // the player's three
for (let i = 0; i < 3; ++i) {
  const s = rect(`shot-${i}`, -999, -999, 2, 4, "#facc15");
  s.tag = "pshot";
  shots.push(s);
}
const bombs = [];                        // the grid's three
for (let i = 0; i < 3; ++i) {
  const b = rect(`bomb-${i}`, -999, -999, 2, 4, "#34d399");
  b.tag = "abomb";
  bombs.push(b);
}

let wave = 1, score = 0, lives = 3, alive = 15;
let dir = 1, stepT = 0, stepEvery = 0.8, fireT = 1.5, gunCool = 0, over = false;
const SPEEDS = { 15: 0.8, 10: 0.55, 5: 0.35, 1: 0.2 };   // thinner = faster

function deploy() {
  alive = ROWS_N * COLS_N;
  stepEvery = SPEEDS[alive] || 0.2;
  dir = 1;
  const left = 8 + Math.min(4, wave - 1) * 2;   // each wave starts lower
  aliens.forEach((a, i) => {
    const r = Math.floor(i / COLS_N), c = i % COLS_N;
    a.x = left + c * 9;
    a.y = 5 + r * 6 + Math.min(3, wave - 1);
    a.visible = 1;
  });
}

function grab(pool) {                    // a parked bullet, or none
  return pool.find((b) => b.x < -100) || null;
}

function fire() {
  const s = grab(shots);
  if (!s || gunCool > 0) return;
  s.x = player.x + 4;
  s.y = player.y - 4;
  gunCool = 0.3;
}

function alienFire() {
  const gunners = aliens.filter((a) => a.visible);
  if (!gunners.length) return;
  const b = grab(bombs);
  if (!b) return;
  const g = gunners[Math.floor(Math.random() * gunners.length)];
  b.x = g.x + 2;
  b.y = g.y + 5;
}

function rebuild(msg) {                  // the wave is spent — the next lands
  say(msg);
  wave += 1;
  if (wave > 3) {
    win("EARTH HOLDS");
    wave = 1;
    score = 0;
    lives = 3;
  }
  deploy();
}

on.key((k) => {                       // held keys fire per frame —
  if (k === "left") player.x = Math.max(1, player.x - 1);
  else if (k === "right") player.x = Math.min(W - 11, player.x + 1);
  else if (k === "space") fire();
});

on.tick((dt) => {
  if (over) return;
  gunCool = Math.max(0, gunCool - dt);
  // the march: a discrete step, faster as the grid thins
  stepT += dt;
  if (stepT >= stepEvery) {
    stepT = 0;
    const living = aliens.filter((a) => a.visible);
    const xs = living.map((a) => a.x);
    const edge = dir > 0 ? Math.max(...xs, 0) : Math.min(...xs, W);
    if ((dir > 0 && edge > W - 12) || (dir < 0 && edge < 2)) {
      dir = -dir;
      living.forEach((a) => { a.y += 2; });          // the drop
    } else {
      living.forEach((a) => { a.x += 2 * dir; });
    }
    stepEvery = SPEEDS[living.length] || 0.2;
    if (living.some((a) => a.y > H - 9)) {           // the grid lands — invasion
      lives -= 1;
      hud.text = `INVADERS  ·  score ${score}  ·  lives ${lives}`;
      if (lives <= 0) { over = true; win("EARTH FALLS"); return; }
      deploy();
      return;
    }
  }
  fireT -= dt;
  if (fireT <= 0) { fireT = 0.7 + Math.random() * 1.6; alienFire(); }
  // the bullets fly; parked ones sleep off-screen
  shots.forEach((s) => { if (s.x > -100) { s.y -= 40 * dt; if (s.y < 0) s.x = -999; } });
  bombs.forEach((b) => { if (b.x > -100) { b.y += 22 * dt; if (b.y > H) b.x = -999; } });
});

on.hit((a, b) => {
  if (over) return;
  const pair = [a.tag, b.tag].sort().join("|");
  if (pair === "alien|pshot") {
    const alien = a.tag === "alien" ? a : b;
    const shot = a.tag === "alien" ? b : a;
    score += POINTS[alien.row] || 10;
    alien.visible = 0;                 // the seat stays, the body is gone
    alien.y = -50;
    shot.x = -999;
    alive -= 1;
    hud.text = `INVADERS  ·  score ${score}  ·  lives ${lives}`;
    if (alive === 0) rebuild(`wave ${wave} cleared — the sky fills again`);
  } else if (pair === "abomb|player") {
    const bomb = a.tag === "abomb" ? a : b;
    bomb.x = -999;
    lives -= 1;
    say("ouch — the cannon took one");
    hud.text = `INVADERS  ·  score ${score}  ·  lives ${lives}`;
    if (lives <= 0) { over = true; win("EARTH FALLS"); }
  } else if (pair === "alien|player") {
    lives = 0;
    over = true;
    win("EARTH FALLS");
  }
});

on.start(() => {
  deploy();
  hud.text = "INVADERS  ·  left/right space  ·  score 0";
});

run();
